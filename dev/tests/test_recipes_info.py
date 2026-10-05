"""멀티 스캔 레시피(10/5) — Report 표의 Recipe 칸은 멀티(x20+x5)여도 `x20` 만 찍힌다(실물 GVB-RDL3 등).
실제로 돈 레시피는 Wafer 폴더에서 읽는다: 멀티면 `RecipesInfo.ini` 의 `[Recipe-n] Name` 전부(→ `x20|x5`),
단일이면 `WaferInfo.ini` 의 `[Recipe] Name`. 덮어써진(STALE) INI 의 것은 쓰지 않고, 정확 경로 하나만 연다."""
from __future__ import annotations

from aoi_capacity import collect
from conftest import make_cfg

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


def test_single_scan_takes_the_waferinfo_recipe_over_the_report_column(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    ini = _wafer_dir(nas) / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("Name=Default", "Name=x20"), encoding="utf-8")
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "EXACT" and r["recipe"] == "x20" and r["scan_mode"] == "SINGLE"   # Report 요약은 Default


def test_multi_scan_reads_every_recipe_from_recipesinfo(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    stats: dict = {}
    rows, _m, _e = collect.collect(make_cfg(tmp_path, csv_path), stats=stats)
    [r] = [x for x in rows if x["device"] == "9호기" and x["wafer_id"] == "K625407-01B0"]
    assert r["recipe"] == "x20|x5" and r["scan_mode"] == "MULTI"
    assert stats["recipes_info_found"] == 1 and stats["log"]["counts"]["recipes_info_found"] == 1


def test_stale_ini_does_not_lend_its_recipe(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    d = _wafer_dir(nas)
    (d / "RecipesInfo.ini").write_text(RECIPES_INFO, encoding="utf-8")
    ini = d / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("13-Sep-26 05:31:04 PM", "20-Sep-26 05:31:04 PM")
                   .replace("13-Sep-26 05:32:02 PM", "20-Sep-26 05:32:02 PM"), encoding="utf-8")
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "STALE" and r["recipe"] == "Default" and r["scan_mode"] == ""       # 다른 시도의 INI — Report 값 그대로


def test_recipesinfo_is_only_opened_at_the_exact_wafer_folder(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    opened = []
    real = collect.read_recipes_info
    monkeypatch.setattr(collect, "read_recipes_info", lambda p: opened.append(p) or real(p))
    _rows(tmp_path, csv_path)
    want = str(_wafer_dir(nas) / "RecipesInfo.ini")
    assert want in opened and len(opened) == len(set(opened)) == 3       # 장비 3대, INI 를 찾은 Wafer 폴더마다 한 번 · 나열 없음
    assert all(p.endswith(want[len(str(nas / "X" / "AOI-9")):]) for p in opened)


def test_multi_ignores_the_waferinfo_name_and_report_only_rows_stay_unknown(tmp_path, fake_nas):
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
