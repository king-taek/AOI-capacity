"""★ 수집 범위 격리 회귀 가드 — 지금 허용 목록은 `scope.DEFAULT_SCOPE`(AOI-1 · 8 · 9 · 25) 다.

두 겹으로 지킨다.
1. 기본값: 설정에 아무것도 없어도 허용 목록은 `scope.DEFAULT_SCOPE` 뿐이다(collect.DEFAULT_CONFIG · prefs).
2. 동적 트립와이어: 장비 해석·연결 확인·최초 수집·백필·전체 재수집·증분·CLI 어느 경로로 들어가도
   가짜 NAS 안에서 **허용 장비 폴더(그리고 그 상위 폴더) 밖 경로**로는 scandir/stat/isdir/isfile/open 이
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


#: 현장 테스트 대상 4대(X:\AOI-1 · M:\AOI-8 · M:\AOI-9 · Y:\AOI-25)를 흉내 낸다.
ALLOWED = [("X", "AOI-1"), ("M", "AOI-8"), ("M", "AOI-9"), ("Y", "AOI-25")]
#: 같은 공유에 나란히 있지만 건드리면 안 되는 이웃들
BLOCKED = [("X", "AOI-2"), ("M", "AOI-10"), ("Y", "AOI-24"), ("I", "AOI-3")]


# ── 가짜 NAS: 허용 4대 + 같은 공유의 이웃들 ──────────────────────────────
@pytest.fixture
def scoped_nas(tmp_path):
    nas = tmp_path / "nas"
    for share, name in ALLOWED + BLOCKED:
        make_device(nas / share, name)
    csv_path = tmp_path / "devices.csv"
    csv_path.write_text(
        "장비명,NAS경로,폴더,사용,메모\n"
        + "".join(f"{name},{nas / share},{name},Y,Camtek\n" for share, name in ALLOWED + BLOCKED if name != "AOI-3")
        + f"4층,{nas / 'I'},*,Y,Camtek 4층 · 폴더 * = 자동 등록\n",
        encoding="utf-8-sig")
    return nas, csv_path


class Tripwire:
    """규칙 두 가지를 그대로 지켜본다.

    ① **범위 밖 장비 폴더는 건드리지 않는다** — 그 폴더나 그 아래를 stat/isdir/isfile/open 하면 기록.
    ② **공유를 나열하지 않는다** — 허용 장비 폴더 밖에서 scandir/listdir 을 부르면 기록
       (나열은 '어떤 장비가 있는지' 를 알아내는 일이라 그 자체가 범위 밖 접근이다).
    허용 이름으로 만든 정확 경로(`공유/AOI-9`)를 확인하는 것은 규칙 위반이 아니다 — 만지는 대상이
    허용 장비이기 때문이다. `폴더 *` 행은 그 길로만 동작한다."""

    LISTING = ("scandir", "listdir")

    def __init__(self, nas: Path, allowed, blocked):
        self.nas = os.path.abspath(str(nas))
        self.allowed = [os.path.abspath(str(a)) for a in allowed]
        self.blocked = [os.path.abspath(str(b)) for b in blocked]
        self.hits = []

    def _under(self, p: str, dirs) -> bool:
        return any(p == d or p.startswith(d + os.sep) for d in dirs)

    def _ok(self, api: str, path) -> bool:
        p = os.path.abspath(str(path))
        if not (p == self.nas or p.startswith(self.nas + os.sep)):
            return True                                    # NAS 밖(캐시·출력·임시폴더)은 관심 없음
        if self._under(p, self.blocked):
            return False                                   # ① 범위 밖 장비
        if api in self.LISTING and not self._under(p, self.allowed):
            return False                                   # ② 허용 장비 밖에서의 나열
        return True

    def check(self, api: str, path):
        if not self._ok(api, path):
            self.hits.append(f"{api}: {path}")


@pytest.fixture
def tripwire(monkeypatch, scoped_nas):
    nas, _ = scoped_nas
    tw = Tripwire(nas, [nas / share / name for share, name in ALLOWED],
                  [nas / share / name for share, name in BLOCKED])
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


#: 게이트 자체를 시험하는 목록 — 기본값이 아니라 **직접 지정한 제한**이다.
#: (기본값은 지금 30대 전부라서, 그것으로는 '막히는지' 를 볼 수 없다.)
SCOPE = ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]


def _cfg(tmp_path, csv_path, **over):
    over.setdefault("scope_devices", list(SCOPE))
    return make_cfg(tmp_path, csv_path, **over)


# ── 1. 기본값 ────────────────────────────────────────────────────────────
def test_default_scope_is_every_real_machine():
    """사용자 확정: 4대 현장 테스트를 마치고 30대 전부를 본다. `*`(제한 없음)와는 여전히 다르다."""
    all30 = [f"AOI-{i}" for i in range(1, 26)] + [f"4F-AOI-{i:02d}" for i in range(1, 6)]
    assert scope.DEFAULT_SCOPE == all30
    assert collect.DEFAULT_CONFIG["scope_devices"] == all30
    assert scope.scope_list({}) == all30 and not scope.unrestricted({})
    assert scope.scope_list({"scope_devices": []}) == all30      # 빈 목록은 '전부 금지' 가 아니다
    from aoi_capacity.utils import prefs
    assert prefs.to_collect_cfg(prefs.Prefs())["scope_devices"] == all30
    assert not scope.is_allowed({}, "AOI-26") and not scope.is_allowed({}, "4F-AOI-06")


@pytest.mark.parametrize("old", [["AOI-25"], ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]])
def test_saved_old_default_scope_is_migrated_but_user_choice_is_kept(old):
    """이미 저장된 설정: **옛 기본값 그대로인 것만** 새 목록으로 옮기고, 직접 고른 값은 그대로 둔다."""
    from aoi_capacity.utils import prefs
    moved = prefs.migrate(prefs.Prefs(scope_devices=list(old), prefs_version=1))
    assert moved.scope_devices == list(scope.DEFAULT_SCOPE) and moved.prefs_version == prefs.PREFS_VERSION
    mine = prefs.migrate(prefs.Prefs(scope_devices=["AOI-7"], prefs_version=1))
    assert mine.scope_devices == ["AOI-7"]                    # 사용자가 고른 값은 건드리지 않는다
    wide = prefs.migrate(prefs.Prefs(scope_devices=["*"], prefs_version=1))
    assert wide.scope_devices == ["*"]


@pytest.mark.parametrize("name,expected", [
    ("AOI-25", True), ("aoi 25", True), ("AOI_25", True), ("AOI-1", True), ("AOI-8", True), ("AOI-9", True),
    ("AOI-10", False),          # ★ AOI-1 과 헷갈리면 안 된다
    ("AOI-24", False), ("AOI-2", False), ("AOI-255", False), ("4F-AOI-01", False), ("", False),
])
def test_is_allowed_matches_by_name_only(name, expected):
    assert scope.is_allowed({"scope_devices": list(SCOPE)}, name) is expected


# ── 2. 장비 해석 · 연결 확인 ─────────────────────────────────────────────
def test_resolve_devices_touches_only_allowed_machines(tmp_path, scoped_nas, tripwire):
    nas, csv_path = scoped_nas
    devs = devices.resolve_devices(_cfg(tmp_path, csv_path), lambda m: None)
    assert [d["name"] for d in devs] == ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]   # 번호순
    assert not tripwire.hits, tripwire.hits


def test_auto_row_finds_allowed_machines_without_listing_the_share(tmp_path, scoped_nas, tripwire):
    """★ `폴더 *` 행은 범위 제한 중에도 동작해야 한다 — 실장비에서 4층 5대가 이것 때문에 3일 내내
    한 번도 수집되지 않았다. 다만 공유를 나열하지는 않고 **허용 이름만** 정확 경로로 확인한다."""
    nas, csv_path = scoped_nas
    make_device(nas / "I", "4F-AOI-01")                     # 4층 공유에 허용 장비 하나를 둔다
    cfg = _cfg(tmp_path, csv_path, scope_devices=[*SCOPE, "4F-AOI-01"])
    devs = devices.devices_from_rows(
        [{"name": "4층", "root": str(nas / "I"), "sub": devices.AUTO, "on": True, "memo": "Camtek 4층"}],
        cfg)
    assert [d["name"] for d in devs] == ["4F-AOI-01"]        # 같은 공유의 AOI-3(범위 밖)은 찾지 않는다
    assert not tripwire.hits, tripwire.hits


def test_check_rows_reports_out_of_scope_without_touching(tmp_path, scoped_nas, tripwire):
    nas, csv_path = scoped_nas
    rows = devices.read_devices_csv(csv_path)
    st = {r["name"]: r["status"] for r in devices.check_rows(rows, _cfg(tmp_path, csv_path))}
    assert st == {"AOI-1": "ok", "AOI-8": "ok", "AOI-9": "ok", "AOI-25": "ok",
                  "AOI-2": "out_of_scope", "AOI-10": "out_of_scope", "AOI-24": "out_of_scope",
                  "4층": "no_report"}       # `*` 행은 확인은 하되 허용 장비가 없어 비어 있다
    assert not tripwire.hits, tripwire.hits


def test_missing_csv_falls_back_without_ever_listing_a_share(tmp_path, scoped_nas, tripwire):
    """devices.csv 가 없으면 nas_roots 를 `*` 로 본다 — 그래도 공유를 나열하지 않고 허용 이름만 확인한다."""
    nas, _ = scoped_nas
    cfg = _cfg(tmp_path, tmp_path / "none.csv", nas_roots=[str(nas / "X"), str(nas / "Y"), str(nas / "M")])
    assert [d["name"] for d in devices.resolve_devices(cfg)] == ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]
    assert not tripwire.hits, tripwire.hits


# ── 3. 수집 진입점 전부 ──────────────────────────────────────────────────
@pytest.mark.parametrize("kw", [{}, {"backfill": True}, {"full": True}])
def test_collect_entry_points_stay_in_scope(tmp_path, scoped_nas, tripwire, kw):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, dev_meta, errors = collect.collect(cfg, **kw)
    assert not tripwire.hits, tripwire.hits
    assert rows and {r["device"] for r in rows} == {"AOI-1", "AOI-8", "AOI-9", "AOI-25"}
    assert [d["name"] for d in dev_meta if d.get("scope") != "out"] == ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]
    assert {d["name"] for d in dev_meta if d.get("scope") == "out"} == {"AOI-2", "AOI-10", "AOI-24"}
    collect.collect(cfg)                                   # 증분 실행도 같은 범위
    assert not tripwire.hits, tripwire.hits


@pytest.mark.parametrize("workers", [1, 2, 8, 32])
def test_parallel_device_check_stays_in_scope_and_matches_serial(tmp_path, scoped_nas, tripwire, workers):
    """C08: 장비 확인(devices_from_rows · _attach_dirs · check_rows)을 read_workers 개씩 동시에 해도 범위 밖 접근은 0 이고
    결과·로그 순서는 한 줄로 돌린 것과 같다."""
    nas, csv_path = scoped_nas
    make_device(nas / "I", "4F-AOI-01")
    tripwire.allowed.append(os.path.abspath(str(nas / "I" / "4F-AOI-01")))     # 이번 테스트에서는 허용 장비다(그 안 나열은 규칙 위반이 아니다)
    cfg = _cfg(tmp_path, csv_path, read_workers=workers, scope_devices=[*SCOPE, "4F-AOI-01"])
    logs = []
    devs = devices.resolve_devices(cfg, logs.append)
    checks = devices.check_rows(devices.read_devices_csv(csv_path), cfg)
    assert not tripwire.hits, tripwire.hits
    assert [d["name"] for d in devs] == ["AOI-1", "AOI-8", "AOI-9", "AOI-25", "4F-AOI-01"]
    serial_logs = []
    serial = devices.resolve_devices({**cfg, "read_workers": 1}, serial_logs.append)
    assert devs == serial and logs == serial_logs
    assert checks == devices.check_rows(devices.read_devices_csv(csv_path), {**cfg, "read_workers": 1})
    rows, dev_meta, errors = collect.collect(cfg)
    assert not tripwire.hits, tripwire.hits
    assert {r["device"] for r in rows} == {"AOI-1", "AOI-8", "AOI-9", "AOI-25", "4F-AOI-01"}


def test_cli_run_stays_in_scope(tmp_path, scoped_nas, tripwire, monkeypatch):
    nas, csv_path = scoped_nas
    from aoi_capacity import cli
    out = tmp_path / "out"
    conf = tmp_path / "config.json"
    conf.write_text(json.dumps({"devices_csv": str(csv_path), "cache_file": str(out / "c.json"),
                                "output_dir": str(out), "backfill_days": 3650,
                                "scope_devices": list(SCOPE)}), encoding="utf-8")
    assert cli.main(["--config", str(conf)]) == 0
    assert not tripwire.hits, tripwire.hits
    data = _embedded(out / "AOI_capacity.html")
    assert data["meta"]["scope"]["restricted"] is True
    dev_col = data["cols"].index("device")
    assert {r[dev_col] for r in data["rows"]} == {"AOI-1", "AOI-8", "AOI-9", "AOI-25"}


def _embedded(html_path) -> dict:
    """생성된 HTML 한 장에 박힌 데이터를 꺼낸다(브라우저 없이). 문자열 풀은 되돌려 준다."""
    text = Path(html_path).read_text(encoding="utf-8")
    data = json.loads(text.split('id="embedded">')[1].split("</script>")[0])
    pool, pooled = data.get("pool"), set(data.get("pooled") or [])
    if pool is not None:                              # collect._embed_rows 가 접어 둔 것을 편다
        data["rows"] = [[pool[v] if c in pooled else v for c, v in zip(data["cols"], row)]
                        for row in data["rows"]]
    return data


def test_html_carries_scope_and_skipped_devices(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, dev_meta, errors = collect.collect(cfg)
    target = collect.write_html(cfg, rows, dev_meta, errors, 0.0, mode="gui")
    data = _embedded(target)
    assert data["meta"]["scope"] == {"restricted": True, "devices": SCOPE}
    assert {d["name"] for d in data["meta"]["devices"] if d.get("scope") == "out"} == {"AOI-2", "AOI-10", "AOI-24"}


def _cursor_of(cache: dict, device_folder: str):
    """여러 장비가 범위 안이므로 커서는 장비 경로로 골라 본다 — 커서 키는 안정 키라 `devices` 대응표의 경로 id 로 찾는다(C03)."""
    keys = [k for k, m in cache["devices"].items()
            if any(i.rstrip("\\/").endswith(device_folder.lower()) or device_folder.lower() in i.lower() for i in m["ids"])]
    hits = [cache["last_mtime"][k] for k in keys if k in cache["last_mtime"]]
    return hits[0] if hits else None


# ── 4. 기존 캐시 · 이름 변경 ─────────────────────────────────────────────
def test_other_device_cache_is_kept_but_excluded_from_output(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    wide = make_cfg(tmp_path, csv_path, scope_devices=["*"])
    rows_all, _, _ = collect.collect(wide)                 # 예전(제한 없음) 실행으로 캐시를 만든다
    assert {"AOI-2", "AOI-10", "AOI-24", "4F-AOI-03"} <= {r["device"] for r in rows_all}

    rows, _, _ = collect.collect(_cfg(tmp_path, csv_path))
    assert {r["device"] for r in rows} == {"AOI-1", "AOI-8", "AOI-9", "AOI-25"}   # 범위 밖은 화면에서 빠진다
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    for gone in ("AOI-24", "AOI-2", "AOI-10", "AOI-3"):    # ★ 다른 장비 캐시는 지우지 않는다
        assert any(f"{gone}{os.sep}" in e["path"] for e in cache["reports"].values()), gone


def test_display_rename_keeps_one_device_and_one_cursor(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    rows, _, _ = collect.collect(cfg)
    assert "AOI-25" in {r["device"] for r in rows}
    before = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))["last_mtime"]

    csv_path.write_text(csv_path.read_text(encoding="utf-8-sig").replace("AOI-25,", "25호기,", 1), encoding="utf-8-sig")
    rows2, dev_meta2, _ = collect.collect(cfg)
    after = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))["last_mtime"]
    assert list(before) == list(after)                     # 커서 키는 경로라 이름을 바꿔도 그대로
    names2 = {r["device"] for r in rows2}
    assert "25호기" in names2 and "AOI-25" not in names2    # 옛 행도 새 표시명으로(둘로 갈라지지 않음)
    assert all(d["reports"] == 0 for d in dev_meta2 if d.get("scope") != "out")   # 다시 읽지 않는다


def test_legacy_name_cursor_is_migrated_not_duplicated(tmp_path, scoped_nas):
    nas, csv_path = scoped_nas
    cfg = _cfg(tmp_path, csv_path)
    collect.collect(cfg)
    cache_file = tmp_path / "out" / "aoi_cache.json"
    cache = json.loads(cache_file.read_text(encoding="utf-8"))
    n_before = len(cache["last_mtime"])
    old_key = next(k for k in cache["last_mtime"] if k.rstrip("\\/").lower().endswith("aoi-25"))
    cache["last_mtime"]["AOI-25"] = cache["last_mtime"].pop(old_key)              # 옛 형식(표시명 키)으로 되돌린다
    for entry in cache["reports"].values():
        entry.pop("device_id", None)
    cache_file.write_text(json.dumps(cache), encoding="utf-8")

    rows, dev_meta, _ = collect.collect(cfg)
    migrated = json.loads(cache_file.read_text(encoding="utf-8"))["last_mtime"]
    assert len(migrated) == n_before and "AOI-25" not in migrated                 # 경로 키로 이관(개수 그대로)
    assert all(d["reports"] == 0 for d in dev_meta if d.get("scope") != "out")     # 커서가 살아 있어 재수집 없음
    assert "AOI-25" in {r["device"] for r in rows}


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
    cur = _cursor_of(cache, "AOI-25")
    # ★ 커서가 실패 파일을 넘어가지 않았다(넘어갔다면 그 Report 는 영영 다시 읽히지 않는다)
    assert cur is None or cur < bad.stat().st_mtime
    assert any("BROKEN" in f["path"] for f in cache["failed"].values())   # 실패 목록도 안정 키(대소문자 접음) — 경로는 항목의 path 에

    boom["on"] = False                                      # 다음 수집에서 다시 읽힌다
    rows2, dev_meta2, errors2 = collect.collect(cfg)
    assert not errors2 and len(rows2) > len(rows)
    cache2 = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    assert not cache2["failed"] and _cursor_of(cache2, "AOI-25") >= good.stat().st_mtime


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
    assert _cursor_of(cache, "AOI-25") >= good.stat().st_mtime            # 커서가 다시 전진한다
    assert next(f for f in cache["failed"].values() if f["path"] == str(bad))["tries"] == collect.MAX_READ_RETRY    # 오류 기록은 남는다


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


# ── 5. 기본 장비 목록이 수집 범위와 어긋나면 안 된다 ─────────────────────
def test_default_device_list_is_entirely_inside_the_scope():
    """★ 실제로 겪은 문제: 기본 목록의 `4층 / I:\\ / *` 행은 자동 탐색이라 범위 제한 중 **통째로 건너뛰어**
    4F 장비 5대가 한 번도 수집되지 않았다. 기본 목록의 모든 행은 범위 안이고 `*` 가 아니어야 한다."""
    from aoi_capacity.utils import paths

    rows = devices.read_devices_csv(paths.default_devices_csv())
    assert rows, "기본 장비 목록이 비었다"
    for row in rows:
        assert str(row.get("sub", "")).strip() != devices.AUTO, f"자동 탐색 행이 남아 있다: {row}"
        assert scope.allows_row({}, row), f"기본 목록인데 수집 범위 밖: {row}"
    names = {scope.key(r["name"]) for r in rows}
    assert names == {scope.key(n) for n in scope.DEFAULT_SCOPE}, "기본 목록과 수집 범위가 서로 다르다"
