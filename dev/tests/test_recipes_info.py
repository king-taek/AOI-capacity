"""멀티 스캔 레시피(10/5) — Report 표의 Recipe 칸은 멀티(x20+x5)여도 `x20` 만 찍힌다(실물 GVB-RDL3 등).
실제로 돈 레시피는 Wafer 폴더에서 읽는다: 멀티면 `RecipesInfo.ini` 의 `[Recipe-n] Name` 전부(→ `x20|x5`),
단일이면 `WaferInfo.ini` 의 `[Recipe] Name`. 덮어써진(STALE) INI 의 것은 쓰지 않고, 정확 경로 하나만 연다."""
from __future__ import annotations

import json
import re

import pytest

from aoi_capacity import collect
from conftest import make_cfg


@pytest.fixture
def rdl_all(monkeypatch):
    """판정 규칙 자체를 보는 테스트 — 가짜 NAS 의 Job(2D@R2-…)도 RDL 로 친다(실제로는 RDL Job 만 RecipesInfo.ini 를 연다, 아래 테스트)."""
    monkeypatch.setattr(collect, "RDL_JOB_RE", re.compile(""))

RECIPES_INFO = """[Recipe-1]
Name=x20
DiePitchX=37247.9
ScanMag=20
[Recipe-2]
Name=x5
DiePitchX=37247.7
ScanMag=5
[Recipes]
Count=2
"""


def _wafer_dir(nas, dev="AOI-9"):
    return nas / "X" / dev / "Scanresult" / "2D@R2-GA285AAB_0859840PD-0A" / "6321" / "KLK-3D" / "K625407-01B0"


def _rows(tmp_path, csv_path):
    rows, _meta, _err = collect.collect(make_cfg(tmp_path, csv_path))
    return [r for r in rows if r["device"] == "9호기" and r["wafer_id"] == "K625407-01B0"]


def test_read_recipes_info_keeps_recipe_order(tmp_path):
    p = tmp_path / "RecipesInfo.ini"
    p.write_text("[Recipes]\nCount=2\n[Recipe-2]\nName=x5\n[Recipe-1]\nName=x20\n", encoding="utf-8")
    assert collect.read_recipes_info(str(p)) == ["x20", "x5"]


def test_single_scan_takes_the_waferinfo_recipe_over_the_report_column(rdl_all, tmp_path, fake_nas):
    nas, csv_path = fake_nas
    ini = _wafer_dir(nas) / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("Name=Default", "Name=x20"), encoding="utf-8")
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "EXACT" and r["recipe"] == "x20" and r["scan_mode"] == "SINGLE"   # Report 요약은 Default


def test_multi_scan_reads_every_recipe_from_recipesinfo(rdl_all, tmp_path, fake_nas):
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    stats: dict = {}
    rows, _m, _e = collect.collect(make_cfg(tmp_path, csv_path), stats=stats)
    [r] = [x for x in rows if x["device"] == "9호기" and x["wafer_id"] == "K625407-01B0"]
    assert r["recipe"] == "x20|x5" and r["scan_mode"] == "MULTI"
    assert stats["recipes_info_found"] == 1 and stats["log"]["counts"]["recipes_info_found"] == 1


def test_stale_ini_does_not_lend_its_recipe(rdl_all, tmp_path, fake_nas):
    nas, csv_path = fake_nas
    d = _wafer_dir(nas)
    (d / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    ini = d / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("13-Sep-26 05:31:04 PM", "20-Sep-26 05:31:04 PM")
                   .replace("13-Sep-26 05:32:02 PM", "20-Sep-26 05:32:02 PM"), encoding="utf-8")
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "STALE" and r["recipe"] == "Default" and r["scan_mode"] == ""       # 다른 시도의 INI — Report 값 그대로


def test_recipesinfo_is_only_opened_at_the_exact_wafer_folder(rdl_all, tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    opened = []
    real = collect.read_recipes_info
    monkeypatch.setattr(collect, "read_recipes_info", lambda p: opened.append(p) or real(p))
    _rows(tmp_path, csv_path)
    want = str(_wafer_dir(nas) / "RecipesInfo.ini")
    assert want in opened and len(opened) == len(set(opened)) == 3       # 장비 3대, INI 를 찾은 Wafer 폴더마다 한 번 · 나열 없음
    assert all(p.endswith(want[len(str(nas / "X" / "AOI-9")):]) for p in opened)


def test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(rdl_all, tmp_path, fake_nas):
    """멀티면 WaferInfo [Recipe] Name 은 스캔 창의 이름일 뿐(사용자 10/5) — RecipesInfo 의 이름만. INI 가 없는 행은 모름."""
    nas, csv_path = fake_nas
    d = _wafer_dir(nas)
    (d / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    ini = d / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("Name=Default", "Name=x5"), encoding="utf-8")
    rows, _m, _e = collect.collect(make_cfg(tmp_path, csv_path))
    nine = [x for x in rows if x["device"] == "9호기"]
    assert {x["wafer_id"]: (x["recipe"], x["scan_mode"]) for x in nine if not x.get("kind")}["K625407-01B0"] == ("x20|x5", "MULTI")
    assert {x["scan_mode"] for x in nine if x["wafer_id"] == "K625407-99Z9"} == {""}


def test_recipesinfo_is_read_only_for_rdl_jobs(tmp_path, fake_nas, monkeypatch):
    """10/5: RecipesInfo.ini 는 RDL Job 만 연다 — 다른 Job 은 파일 열기를 늘리지 않고 scan_mode 는 모름(표에 `|` 가 없으면)."""
    nas, csv_path = fake_nas
    opened = []
    real = collect.read_recipes_info
    monkeypatch.setattr(collect, "read_recipes_info", lambda p: opened.append(p) or real(p))
    rows, _m, _e = collect.collect(make_cfg(tmp_path, csv_path))
    assert opened == [] and {r["scan_mode"] for r in rows if not r.get("kind")} == {""}


def _make_rdl(nas, dev="AOI-9", job="TB500_RDL3 - Multi", lot="GVB-RDL3", wafer="W01", multi=True):
    """RDL Report 하나와 그 Wafer 폴더(WaferInfo · 멀티면 RecipesInfo)."""
    from conftest import REPORT_HTML, WAFER_INI
    name = f"{job}_Setup1_{lot}_26-Sep-13_(05.32.23)_BatchReport.htm"
    html = REPORT_HTML.replace("KLK-3D", lot).replace("K625407-01B0", wafer).replace(
        "<tr><td>Recipe:</td><td>Default</td></tr>", f"<tr><td>Recipe:</td><td>x20</td></tr><tr><td>Job/Setup:</td><td>{job}/Setup1</td></tr>")
    (nas / "X" / dev / "Report" / name).write_text(html, encoding="utf-8")
    d = nas / "X" / dev / "Scanresult" / job / "Setup1" / lot / wafer
    d.mkdir(parents=True, exist_ok=True)
    (d / "WaferInfo.ini").write_text(WAFER_INI.replace("KLK-3D", lot).replace("K625407-01B0", wafer).replace("Name=Default", "Name=x20"),
                                    encoding="utf-8")
    if multi:
        (d / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    return name, d


def test_rdl_patch_rereads_only_rdl_reports_missing_the_mode_on_rdl_devices(tmp_path, fake_nas, monkeypatch):
    """수집 창 'RDL 영역 INI 패치'(10/5): 업데이트 전에 읽어 멀티/단일 판정이 없는 RDL Report 만, 그 Report 가 있는 장비만 다시 읽는다."""
    nas, csv_path = fake_nas
    name, _d = _make_rdl(nas)
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    # 업데이트 전 캐시를 흉내 — RDL 행의 판정을 지운다
    cache = json.loads(open(cfg["cache_file"], encoding="utf-8").read())
    for e in cache["reports"].values():
        for r in e["rows"]:
            r.pop("scan_mode", None)
    collect._save_cache(cfg, cache)
    plan = collect.plan_run(cfg)
    assert (plan.rdl_reports, plan.rdl_devices) == (1, 1)
    listed = []
    real = collect._list_all
    monkeypatch.setattr(collect, "_list_all", lambda p, n: listed.append(n) or real(p, n))
    stats: dict = {}
    rows, meta, errors = collect.collect(cfg, rdl_patch=True, stats=stats)
    assert not errors and listed == ["9호기"] and stats["mode"] == "rdl_patch"     # RDL 이 있는 장비만 나열
    assert {m["name"] for m in meta} >= {"8호기", "9호기", "AOI-10"}                  # 보지 않은 장비도 결과에 남는다
    assert sum(m.get("refreshed", 0) for m in meta) == 1
    rdl = [r for r in rows if r["report"] == name and r["wafer_id"] == "W01"]
    assert rdl and rdl[0]["scan_mode"] == "MULTI" and rdl[0]["recipe"] == "x20|x5"
    assert collect.plan_run(cfg).rdl_reports == 0                                  # 다 채웠으면 대상 없음
