"""★ 수집 범위(AOI-25) 격리 회귀 가드.

두 겹으로 지킨다.
1. 기본값: 설정에 아무것도 없어도 수집 허용 장비는 AOI-25 한 대다(collect.DEFAULT_CONFIG · prefs).
2. 동적 트립와이어: 장비 해석·연결 확인·최초 수집·백필·전체 재수집·증분·CLI 어느 경로로 들어가도
   가짜 NAS 안에서 **AOI-25 폴더(그리고 그 상위 폴더) 밖 경로**로는 scandir/stat/isdir/isfile/open 이
   한 번도 불리지 않는다.

또한 범위 밖 장비의 기존 캐시는 **지우지 않고** 출력에서만 빠지는지, 표시명을 바꿔도 같은 장비가
둘로 갈라지지 않는지, 읽기에 실패한 Report 를 커서가 넘어가 버리지 않는지 확인한다.
"""
from __future__ import annotations

import builtins
import json
import os
from pathlib import Path

import pytest

from aoi_capacity import collect, devices, scope
from conftest import make_cfg, make_device


# ── 가짜 NAS: 허용(AOI-25) 한 대 + 건드리면 안 되는 이웃들 ─────────────────
@pytest.fixture
def scoped_nas(tmp_path):
    nas = tmp_path / "nas"
    make_device(nas / "Y", "AOI-25")          # 허용
    make_device(nas / "Y", "AOI-24")          # 같은 공유의 이웃 — 접근 금지
    make_device(nas / "X", "AOI-1")           # 다른 공유 — 접근 금지
    make_device(nas / "I", "AOI-3")           # 4층 자동탐색(*) 대상 — 접근 금지
    csv_path = tmp_path / "devices.csv"
    csv_path.write_text(
        "장비명,NAS경로,폴더,사용,메모\n"
        f"AOI-1,{nas / 'X'},AOI-1,Y,Camtek 1~7\n"
        f"AOI-24,{nas / 'Y'},AOI-24,Y,Camtek 24~25\n"
        f"AOI-25,{nas / 'Y'},AOI-25,Y,Camtek 24~25\n"
        f"4층,{nas / 'I'},*,Y,Camtek 4층 · 폴더 * = 자동 등록\n",
        encoding="utf-8-sig")
    return nas, csv_path


class Tripwire:
    """가짜 NAS 안에서 허용 폴더(그리고 그 상위) 밖을 건드리면 기록한다."""

    def __init__(self, nas: Path, allowed: Path):
        self.nas = os.path.abspath(str(nas))
        self.allowed = os.path.abspath(str(allowed))
        self.hits = []

    def _ok(self, path) -> bool:
        p = os.path.abspath(str(path))
        if not (p == self.nas or p.startswith(self.nas + os.sep)):
            return True                                    # NAS 밖(캐시·출력·임시폴더)은 관심 없음
        if p == self.allowed or p.startswith(self.allowed + os.sep):
            return True                                    # 허용 장비 폴더 안
        return self.allowed.startswith(p + os.sep)         # 허용 장비의 상위 폴더(공유 루트)

    def check(self, api: str, path):
        if not self._ok(path):
            self.hits.append(f"{api}: {path}")


@pytest.fixture
def tripwire(monkeypatch, scoped_nas):
    nas, _ = scoped_nas
    tw = Tripwire(nas, nas / "Y" / "AOI-25")
    real = {"scandir": os.scandir, "stat": os.stat, "isdir": os.path.isdir,
            "isfile": os.path.isfile, "exists": os.path.exists, "open": builtins.open,
            "listdir": os.listdir}

    def wrap(api, fn, argpos=0):
        def inner(*a, **kw):
            if a:
                tw.check(api, a[argpos])
            return fn(*a, **kw)
        return inner

    monkeypatch.setattr(os, "scandir", wrap("scandir", real["scandir"]))
    monkeypatch.setattr(os, "stat", wrap("stat", real["stat"]))
    monkeypatch.setattr(os, "listdir", wrap("listdir", real["listdir"]))
    monkeypatch.setattr(os.path, "isdir", wrap("isdir", real["isdir"]))
    monkeypatch.setattr(os.path, "isfile", wrap("isfile", real["isfile"]))
    monkeypatch.setattr(os.path, "exists", wrap("exists", real["exists"]))
    monkeypatch.setattr(builtins, "open", wrap("open", real["open"]))
    return tw


def _cfg(tmp_path, csv_path, **over):
    cfg = make_cfg(tmp_path, csv_path, **over)
    cfg.pop("scope_devices", None)          # 기본값(AOI-25)을 그대로 쓴다
    return cfg


# ── 1. 기본값 ────────────────────────────────────────────────────────────
def test_default_scope_is_aoi25_everywhere():
    assert collect.DEFAULT_CONFIG["scope_devices"] == ["AOI-25"]
    assert scope.scope_list({}) == ["AOI-25"] and not scope.unrestricted({})
    assert scope.scope_list({"scope_devices": []}) == ["AOI-25"]      # 빈 목록은 '전부 금지' 가 아니다
    from aoi_capacity.utils import prefs
    assert prefs.to_collect_cfg(prefs.Prefs())["scope_devices"] == ["AOI-25"]


@pytest.mark.parametrize("name,expected", [
    ("AOI-25", True), ("aoi 25", True), ("AOI_25", True),
    ("AOI-24", False), ("AOI-2", False), ("AOI-255", False), ("4F-AOI-01", False), ("", False),
])
def test_is_allowed_matches_by_name_only(name, expected):
    assert scope.is_allowed({}, name) is expected


# ── 2. 장비 해석 · 연결 확인 ─────────────────────────────────────────────
def test_resolve_devices_touches_only_aoi25(tmp_path, scoped_nas, tripwire):
    nas, csv_path = scoped_nas
    logs = []
    devs = devices.resolve_devices(_cfg(tmp_path, csv_path), logs.append)
    assert [d["name"] for d in devs] == ["AOI-25"]
    assert not tripwire.hits, tripwire.hits
    assert any("범위 밖" in l and "4층" in l for l in logs)     # * 행은 나열도 하지 않고 건너뛴다


def test_check_rows_reports_out_of_scope_without_touching(tmp_path, scoped_nas, tripwire):
    nas, csv_path = scoped_nas
    rows = devices.read_devices_csv(csv_path)
    st = {r["name"]: r["status"] for r in devices.check_rows(rows, _cfg(tmp_path, csv_path))}
    assert st == {"AOI-1": "out_of_scope", "AOI-24": "out_of_scope", "AOI-25": "ok", "4층": "out_of_scope"}
    assert not tripwire.hits, tripwire.hits


def test_missing_csv_does_not_fall_back_to_scanning_the_nas(tmp_path, scoped_nas, tripwire):
    nas, _ = scoped_nas
    cfg = _cfg(tmp_path, tmp_path / "none.csv", nas_roots=[str(nas / "X"), str(nas / "Y")])
    assert devices.resolve_devices(cfg) == []
    assert not tripwire.hits, tripwire.hits


# ── 3. 수집 진입점 전부 ──────────────────────────────────────────────────
@pytest.mark.parametrize("kw", [{}, {"backfill": True}, {"full": True}])
def test_collect_entry_points_stay_in_scope(tmp_path, scoped_nas, tripwire, kw):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, dev_meta, errors = collect.collect(cfg, **kw)
    assert not tripwire.hits, tripwire.hits
    assert rows and {r["device"] for r in rows} == {"AOI-25"}
    assert [d["name"] for d in dev_meta if d.get("scope") != "out"] == ["AOI-25"]
    assert {d["name"] for d in dev_meta if d.get("scope") == "out"} == {"AOI-1", "AOI-24", "4층"}
    collect.collect(cfg)                                   # 증분 실행도 같은 범위
    assert not tripwire.hits, tripwire.hits


def test_cli_run_stays_in_scope(tmp_path, scoped_nas, tripwire, monkeypatch):
    nas, csv_path = scoped_nas
    from aoi_capacity import cli
    out = tmp_path / "out"
    conf = tmp_path / "config.json"
    conf.write_text(json.dumps({"devices_csv": str(csv_path), "cache_file": str(out / "c.json"),
                                "output_dir": str(out), "backfill_days": 3650}), encoding="utf-8")
    assert cli.main(["--config", str(conf)]) == 0
    assert not tripwire.hits, tripwire.hits
    data = _embedded(out / "AOI_capacity.html")
    assert data["meta"]["scope"]["restricted"] is True
    dev_col = data["cols"].index("device")
    assert {r[dev_col] for r in data["rows"]} == {"AOI-25"}


def _embedded(html_path) -> dict:
    """생성된 HTML 한 장에 박힌 데이터를 그대로 꺼낸다(브라우저 없이)."""
    text = Path(html_path).read_text(encoding="utf-8")
    return json.loads(text.split('id="embedded">')[1].split("</script>")[0])


def test_html_carries_scope_and_skipped_devices(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, dev_meta, errors = collect.collect(cfg)
    target = collect.write_html(cfg, rows, dev_meta, errors, 0.0, mode="gui")
    data = _embedded(target)
    assert data["meta"]["scope"] == {"restricted": True, "devices": ["AOI-25"]}
    assert {d["name"] for d in data["meta"]["devices"] if d.get("scope") == "out"} == {"AOI-1", "AOI-24", "4층"}


# ── 4. 기존 캐시 · 이름 변경 ─────────────────────────────────────────────
def test_other_device_cache_is_kept_but_excluded_from_output(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    wide = make_cfg(tmp_path, csv_path, scope_devices=["*"])
    rows_all, _, _ = collect.collect(wide)                 # 예전(제한 없음) 실행으로 캐시를 만든다
    assert {r["device"] for r in rows_all} == {"AOI-1", "AOI-24", "AOI-25", "4F-AOI-03"}

    rows, _, _ = collect.collect(_cfg(tmp_path, csv_path))
    assert {r["device"] for r in rows} == {"AOI-25"}       # 화면에는 AOI-25 만
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    assert any("AOI-24" in k for k in cache["reports"])    # ★ 다른 장비 캐시는 지우지 않는다
    assert any("AOI-1" in k for k in cache["reports"])


def test_display_rename_keeps_one_device_and_one_cursor(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, _, _ = collect.collect(cfg)
    assert {r["device"] for r in rows} == {"AOI-25"}
    before = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))["last_mtime"]

    csv_path.write_text(csv_path.read_text(encoding="utf-8-sig").replace("AOI-25,", "25호기,", 1), encoding="utf-8-sig")
    rows2, dev_meta2, _ = collect.collect(cfg)
    after = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))["last_mtime"]
    assert list(before) == list(after)                     # 커서 키는 경로라 이름을 바꿔도 그대로
    assert {r["device"] for r in rows2} == {"25호기"}       # 옛 행도 새 표시명으로 나온다(둘로 갈라지지 않음)
    assert all(d["reports"] == 0 for d in dev_meta2 if d.get("scope") != "out")   # 다시 읽지 않는다


def test_legacy_name_cursor_is_migrated_not_duplicated(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    collect.collect(cfg)
    cache_file = tmp_path / "out" / "aoi_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8"))
    cache["last_mtime"] = {"AOI-25": list(cache["last_mtime"].values())[0]}       # 옛 형식(표시명 키)으로 되돌린다
    for entry in cache["reports"].values():
        entry.pop("device_id", None)
    cache_file.write_text(json.dumps(cache), encoding="utf-8")

    rows, dev_meta, _ = collect.collect(cfg)
    migrated = json.loads(cache_file.read_text(encoding="utf-8"))["last_mtime"]
    assert len(migrated) == 1 and "AOI-25" not in migrated                        # 경로 키로 이관
    assert all(d["reports"] == 0 for d in dev_meta if d.get("scope") != "out")     # 커서가 살아 있어 재수집 없음
    assert {r["device"] for r in rows} == {"AOI-25"}


# ── 5. 읽기 실패한 Report 는 커서에 묻히지 않는다 ────────────────────────
def test_failed_report_blocks_cursor_and_is_retried(tmp_path, scoped_nas, monkeypatch):
    nas, csv_path = scoped_nas
    rep_dir = nas / "Y" / "AOI-25" / "Report"
    good = next(rep_dir.glob("*.htm"))
    bad = rep_dir / good.name.replace("KLK-3D", "BROKEN")
    bad.write_text(good.read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(bad, (good.stat().st_mtime - 60, good.stat().st_mtime - 60))   # 실패 파일이 더 오래됐다
    cfg = _cfg(tmp_path, csv_path)

    real_parse = collect.parse_report
    boom = {"on": True}

    def flaky(name, text):
        if boom["on"] and "BROKEN" in name:
            raise ValueError("깨진 Report")
        return real_parse(name, text)

    monkeypatch.setattr(collect, "parse_report", flaky)
    rows, _, errors = collect.collect(cfg)
    assert len(errors) == 1 and errors[0]["tries"] == 1
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    cursors = list(cache["last_mtime"].values())
    # ★ 커서가 실패 파일을 넘어가지 않았다(넘어갔다면 그 Report 는 영영 다시 읽히지 않는다)
    assert not cursors or cursors[0] < bad.stat().st_mtime
    assert any("BROKEN" in k for k in cache["failed"])

    boom["on"] = False                                      # 다음 수집에서 다시 읽힌다
    rows2, dev_meta2, errors2 = collect.collect(cfg)
    assert not errors2 and len(rows2) > len(rows)
    cache2 = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    assert not cache2["failed"] and list(cache2["last_mtime"].values())[0] >= good.stat().st_mtime


def test_permanently_broken_report_stops_blocking_after_retries(tmp_path, scoped_nas, monkeypatch):
    nas, csv_path = scoped_nas
    rep_dir = nas / "Y" / "AOI-25" / "Report"
    good = next(rep_dir.glob("*.htm"))
    bad = rep_dir / good.name.replace("KLK-3D", "BROKEN")
    bad.write_text(good.read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(bad, (good.stat().st_mtime - 60, good.stat().st_mtime - 60))
    cfg = _cfg(tmp_path, csv_path)
    real_parse = collect.parse_report
    monkeypatch.setattr(collect, "parse_report",
                        lambda n, t: (_ for _ in ()).throw(ValueError("x")) if "BROKEN" in n else real_parse(n, t))
    for _ in range(collect.MAX_READ_RETRY):
        _, _, errors = collect.collect(cfg)
        assert len(errors) == 1
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    assert list(cache["last_mtime"].values())[0] >= good.stat().st_mtime   # 커서가 다시 전진한다
    assert cache["failed"][str(bad)]["tries"] == collect.MAX_READ_RETRY    # 오류 기록은 남는다


# ── 6. 표시명 · 정렬 ─────────────────────────────────────────────────────
@pytest.mark.parametrize("folder,hint,expected", [
    ("AOI-1", "", "AOI-1"),
    ("1~7 AOI-1", "", "AOI-1"),
    ("AOI-25", "Camtek 24~25", "AOI-25"),
    ("AOI_07", "", "AOI-7"),
    ("AOI-1", "Camtek 4층", "4F-AOI-01"),
    ("AOI-5", "4F", "4F-AOI-05"),
    ("검사기A", "", "검사기A"),
])
def test_display_name_rules(folder, hint, expected):
    assert devices.display_name(folder, hint) == expected


def test_home_order_is_numeric_then_floor4():
    names = ["4F-AOI-05", "AOI-10", "AOI-2", "4F-AOI-01", "AOI-25", "AOI-1"]
    assert sorted(names, key=devices.sort_key) == ["AOI-1", "AOI-2", "AOI-10", "AOI-25", "4F-AOI-01", "4F-AOI-05"]
