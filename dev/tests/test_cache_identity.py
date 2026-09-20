"""캐시 정체성·저장 규칙(P3-A · C03 · C04 · C09 · C07).

- C03: Report 키 = `(장비 안정 키 | Report 폴더 아래 상대 경로)`. X: → UNC → M: 처럼 **검증·승인된** 표기 변경은 한 Report,
  서로 다른 장비의 같은 파일 이름은 각각, 폴더 이름·표시명이 같다는 이유로는 합치지 않는다(충돌로 기록). 옛 절대 경로 캐시 이관은
  멱등이고 rows 를 지우지 않는다(같은 키로 모인 옛 판은 `superseded_by` 로 보존).
- C04: 아무것도 안 바뀐 실행은 캐시 파일을 건드리지 않는다(mtime·바이트 동일). rows 0건이어도 커서·재시도·보관·규칙 번호가 바뀌면 저장.
- C09: 장비 색인은 실행마다 한 번 — 안정 키·경로 id 정확 일치가 먼저, 경로 폴백은 id 없는 옛 항목만. 결과는 예전 선형 탐색과 같다.
- C07: HTML 은 앞·데이터·뒤를 차례로 쓴다 — `</script>`·한글·U+2028 이 든 문구도 JSON 으로 그대로 돌아온다.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time

import pytest

from aoi_capacity import collect, devices
from conftest import REPORT_HTML, make_cfg, make_device


def _cache_of(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def _raw(cfg):
    return open(cfg["cache_file"], "rb").read()


def _stamp(cfg):
    st = os.stat(cfg["cache_file"])
    return st.st_mtime_ns, st.st_size


def _count_htm_reads(monkeypatch):
    from aoi_capacity import nas_guard
    seen = {"htm": 0}
    orig = nas_guard.read_bytes

    def spy(path, *a, **k):
        if str(path).lower().endswith((".htm", ".html")):
            seen["htm"] += 1
        return orig(path, *a, **k)

    monkeypatch.setattr(collect.nas_guard, "read_bytes", spy)
    return seen


def _fingerprint(rows):
    import hashlib
    blob = json.dumps(sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def _csv(tmp_path, root, name="", sub="AOI-1"):
    p = tmp_path / f"devices_{os.path.basename(str(root))}.csv"
    p.write_text(f"장비명,NAS경로,폴더,사용,메모\n{name},{root},{sub},Y,\n", encoding="utf-8-sig")
    return p


def _same_mtime(*paths):
    t = time.time() - 3600
    for p in paths:
        os.utime(p, (t, t))


def _to_legacy(cache: dict) -> dict:
    """새 형식 캐시를 P3 이전 형식(절대 경로 키 · 경로 id 커서 · 대응표 없음)으로 되돌린다 — 이관 테스트의 입력."""
    old = {"reports": {}, "last_mtime": {}, "failed": {}, "parser_version": cache["parser_version"]}
    for e in cache["reports"].values():
        old["reports"][e["path"]] = {k: v for k, v in e.items() if k not in ("device_key", "rel", "path", "sha256", "revision")}
    for key, m in cache["devices"].items():
        if key in cache["last_mtime"]:
            old["last_mtime"][m["ids"][0]] = cache["last_mtime"][key]
    return old


# ══════════════════════════════════════════════════════════════════════════════
# C03 — 안정 키 · 승인된 별칭 · 이름만으로는 합치지 않음
# ══════════════════════════════════════════════════════════════════════════════
def test_approved_drive_unc_drive_aliases_of_one_device_are_one_report(tmp_path, monkeypatch):
    """★ X: → UNC → M: — OS 가 알려 준 UNC 동치(검증된 별칭)로 잇는다. Report 는 하나, 다시 읽지 않고, 커서도 그대로다."""
    nas = tmp_path / "nas"
    x, m = make_device(nas / "X", "AOI-1"), make_device(nas / "M", "AOI-1")
    unc = tmp_path / "unc" / "share"
    shutil.copytree(x, unc / "AOI-1")
    _same_mtime(*(d / "Report" / os.listdir(d / "Report")[0] for d in (x, m, unc / "AOI-1")))
    # 드라이브(X:, M:) → UNC 동치. UNC 자신은 드라이브가 아니라 None(실물 WNetGetConnection 과 같다).
    monkeypatch.setattr(devices, "UNC_RESOLVER",
                        lambda p: str(unc / "AOI-1") if str(p).rstrip("/").endswith(("X/AOI-1", "M/AOI-1")) else None)
    cfg = make_cfg(tmp_path, _csv(tmp_path, nas / "X"))
    rows0, _, _ = collect.collect(cfg)
    c0 = _cache_of(cfg)
    assert len(rows0) == 3 and list(c0["devices"]) == ["dev:AOI-1"]
    assert set(c0["devices"]["dev:AOI-1"]["ids"]) == {devices.device_id(x), devices.device_id(unc / "AOI-1")}

    seen = _count_htm_reads(monkeypatch)
    rows1, meta1, _ = collect.collect(dict(cfg, devices_csv=str(_csv(tmp_path, unc / "share" if False else unc, sub="AOI-1"))))
    assert seen["htm"] == 0 and len(rows1) == 3 and meta1[0]["reports"] == 0           # UNC 로 등록해도 같은 장비 — 다시 읽지 않는다
    rows2, meta2, _ = collect.collect(dict(cfg, devices_csv=str(_csv(tmp_path, nas / "M"))))
    assert seen["htm"] == 0 and len(rows2) == 3 and meta2[0]["reports"] == 0           # M: 으로 바꿔도 같은 장비
    c2 = _cache_of(cfg)
    assert len(c2["reports"]) == 1 and list(c2["last_mtime"]) == ["dev:AOI-1"] and c2["last_mtime"] == c0["last_mtime"]
    assert set(c2["devices"]["dev:AOI-1"]["ids"]) == {devices.device_id(p) for p in (x, m, unc / "AOI-1")}
    assert _fingerprint(rows2) == _fingerprint(rows0)


def test_cfg_approved_alias_group_merges_without_os_help(tmp_path, monkeypatch):
    """OS 가 UNC 를 못 알려 주는 곳(다른 PC 로 옮김)에서는 cfg 의 승인 묶음이 같은 역할을 한다."""
    nas = tmp_path / "nas"
    x, m = make_device(nas / "X", "AOI-1"), make_device(nas / "M", "AOI-1")
    _same_mtime(*(d / "Report" / os.listdir(d / "Report")[0] for d in (x, m)))
    monkeypatch.setattr(devices, "UNC_RESOLVER", lambda p: None)
    cfg = make_cfg(tmp_path, _csv(tmp_path, nas / "X"))
    collect.collect(cfg)
    seen = _count_htm_reads(monkeypatch)
    approved = {devices.PATH_ALIASES_CFG: [[str(x), str(m)]]}
    rows, meta, _ = collect.collect(dict(cfg, devices_csv=str(_csv(tmp_path, nas / "M")), **approved))
    assert seen["htm"] == 0 and len(rows) == 3 and meta[0]["reports"] == 0
    assert len(_cache_of(cfg)["reports"]) == 1


def test_same_folder_name_under_another_root_is_not_merged_by_name(tmp_path, monkeypatch):
    """★ 폴더 이름·표시명이 같아도 승인된 별칭이 없으면 다른 장비다 — 새 키(`~2`)를 만들고 충돌로 기록한다. 옛 이력은 지우지 않는다."""
    nas = tmp_path / "nas"
    x, m = make_device(nas / "X", "AOI-1"), make_device(nas / "M", "AOI-1")
    _same_mtime(*(d / "Report" / os.listdir(d / "Report")[0] for d in (x, m)))
    monkeypatch.setattr(devices, "UNC_RESOLVER", lambda p: None)
    cfg = make_cfg(tmp_path, _csv(tmp_path, nas / "X"))
    collect.collect(cfg)
    logs = []
    rows, meta, _ = collect.collect(dict(cfg, devices_csv=str(_csv(tmp_path, nas / "M"))), log=logs.append)
    c = _cache_of(cfg)
    assert set(c["devices"]) == {"dev:AOI-1", "dev:AOI-1~2"} and len(c["reports"]) == 2
    assert meta[0]["reports"] == 1 and meta[0]["key"] == "dev:AOI-1~2"
    assert c["identity"]["conflicts"][0]["kind"] == "name_clash" and c["identity"]["n_conflicts"] == 1
    assert any("이름만으로 합치지 않음" in m for m in logs)
    assert len(rows) == 6                                                              # 두 장비 — 옛 이력(dev:AOI-1)도 그대로 나간다


def test_same_report_name_under_two_devices_is_two_entries(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    rows, _, _ = collect.collect(cfg)
    c = _cache_of(cfg)
    rels = [e["rel"] for e in c["reports"].values()]
    assert len(c["reports"]) == 3 and len(set(rels)) == 1                              # 같은 파일 이름 3개 — 장비마다 한 항목
    assert {k.split("|")[0] for k in c["reports"]} == {"dev:9호기", "dev:AOI-10", "dev:8호기"}
    assert len({e["sha256"] for e in c["reports"].values()}) == 1                    # 내용도 같지만(픽스처) 합치지 않는다


def test_modified_report_is_a_revision_and_a_copy_elsewhere_is_a_different_key(tmp_path, fake_nas, monkeypatch):
    """같은 키에 내용이 달라진 파일 = 수정본(revision 2) · 다른 장비 폴더의 같은 이름 = 다른 키(revision 1)."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    rep = next((nas / "X" / "AOI-10" / "Report").glob("*.htm"))
    key = next(k for k, e in _cache_of(cfg)["reports"].items() if e["path"] == str(rep))
    sha1 = _cache_of(cfg)["reports"][key]["sha256"]
    rep.write_text(REPORT_HTML.replace("K625407-01B0", "K625407-01B1"), encoding="utf-8")
    t = time.time() + 60
    os.utime(rep, (t, t))
    collect.collect(cfg)
    e = _cache_of(cfg)["reports"][key]
    assert e["revision"] == 2 and e["sha256"] != sha1 and len(_cache_of(cfg)["reports"]) == 3
    # 내용은 같은데 다시 읽기만 한 경우(refresh)는 수정본이 아니다
    collect.collect(cfg, refresh_window_days=30)
    assert _cache_of(cfg)["reports"][key]["revision"] == 2
    # 다른 장비에 같은 이름의 사본이 생겨도 그 장비의 키로 따로 들어간다
    shutil.copy2(rep, nas / "X" / "AOI-9" / "Report" / rep.name.replace("KLK-3D", "COPY"))
    collect.collect(cfg)
    copies = [k for k, x in _cache_of(cfg)["reports"].items() if x["sha256"] == e["sha256"]]
    assert len(copies) == 2 and {k.split("|")[0] for k in copies} == {"dev:AOI-10", "dev:9호기"}


# ══════════════════════════════════════════════════════════════════════════════
# 이관 — 옛 절대 경로 키 → 새 키. 멱등 · rows 삭제 0 · 출력 지문 동일 · NAS 읽기 0
# ══════════════════════════════════════════════════════════════════════════════
def test_legacy_cache_migrates_once_with_identical_output_and_no_nas_reads(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    rows_fresh, _, _ = collect.collect(cfg)
    fresh = _cache_of(cfg)
    legacy = _to_legacy(fresh)
    assert not any(k.startswith("dev:") for k in legacy["reports"]) and "devices" not in legacy
    open(cfg["cache_file"], "w", encoding="utf-8").write(json.dumps(legacy, ensure_ascii=False))

    seen = _count_htm_reads(monkeypatch)
    stats, logs = {}, []
    rows, meta, errors = collect.collect(cfg, stats=stats, log=logs.append)
    assert seen["htm"] == 0 and not errors and all(d["reports"] == 0 for d in meta)  # 커서가 살아 있어 재수집 없음
    assert _fingerprint(rows) == _fingerprint(rows_fresh)                                 # 출력 지문 동일
    mig = _cache_of(cfg)
    assert set(mig["reports"]) == set(fresh["reports"]) and mig["last_mtime"] == fresh["last_mtime"]
    assert mig["identity"]["migrated"] == {"reports": 3} and mig["identity"]["n_conflicts"] == 0   # 커서는 _assign_device_keys 가 먼저 옮긴다
    assert all(e["path"] in legacy["reports"] and "sha256" not in e for e in mig["reports"].values())   # 지문은 다음 읽기 때
    assert {"identity", "cursor"} <= set(stats["cache_dirty"]) and stats["cache_saved"] is True
    assert any("캐시 키 이관" in m for m in logs)
    # 멱등: 한 번 더 돌리면 아무것도 바뀌지 않아 저장조차 하지 않는다
    stamp = _stamp(cfg)
    raw = _raw(cfg)
    stats2 = {}
    rows2, _, _ = collect.collect(cfg, stats=stats2)
    assert stats2["cache_saved"] is False and stats2["cache_dirty"] == {} and _stamp(cfg) == stamp and _raw(cfg) == raw
    assert _fingerprint(rows2) == _fingerprint(rows_fresh)


def test_migrate_identity_function_is_idempotent_and_keeps_every_row_on_conflicts(tmp_path):
    """X: 와 UNC 로 같은 파일이 두 번 들어간 옛 캐시(C03 의 증상) — 하나로 모으되 rows 는 하나도 지우지 않는다(옛 판은 superseded 로 보존)."""
    rows_a = [{"device": "AOI-1", "status": "Pass", "lot": "L", "wafer_id": "W1", "report": "r.htm"}]
    rows_b = [{"device": "AOI-1", "status": "Pass", "lot": "L", "wafer_id": "W1", "report": "r.htm"},
              {"device": "AOI-1", "status": "Scan Error.", "lot": "L", "wafer_id": "W2", "report": "r.htm"}]
    legacy = {"reports": {
        r"X:\AOI-1\Report\r.htm": {"mtime": 100.0, "device": "AOI-1", "device_id": r"x:\aoi-1", "rows": rows_a},
        r"\\host\share\AOI-1\Report\r.htm": {"mtime": 200.0, "device": "AOI-1", "device_id": r"\\host\share\aoi-1", "rows": rows_b},
        r"X:\AOI-1\Report\other.htm": {"mtime": 50.0, "device": "AOI-1", "device_id": r"x:\aoi-1", "rows": rows_a},
        r"Y:\AOI-2\Reports\r.htm": {"mtime": 10.0, "device": "AOI-2", "device_id": r"y:\aoi-2", "rows": rows_a},
        "/old/noid/AOI-3/Report/z.htm": {"mtime": 5.0, "device": "AOI-3", "rows": rows_a},
    }, "last_mtime": {r"x:\aoi-1": 100.0, r"\\host\share\aoi-1": 200.0, r"y:\aoi-2": 10.0, r"q:\gone": 1.0},
        "failed": {r"X:\AOI-1\Report\bad.htm": {"mtime": 90.0, "tries": 1, "device_id": r"x:\aoi-1", "error": "x"}},
        "devices": {"dev:AOI-1": {"name": "AOI-1", "ids": [r"x:\aoi-1", r"\\host\share\aoi-1"], "aliases": []}}}
    dev = {"name": "AOI-1", "id": r"x:\aoi-1", "path": r"X:\AOI-1", "key": "dev:AOI-1", "aliases": []}
    n_rows = sum(len(e["rows"]) for e in legacy["reports"].values())

    def migrate(cache):
        d = collect._Dirty()
        collect._migrate_identity(cache, collect._DeviceIndex([dev]), d)
        return d

    once = json.loads(json.dumps(legacy))
    d1 = migrate(once)
    assert d1 and sum(len(e["rows"]) for e in once["reports"].values()) == n_rows            # rows 삭제 0
    cur = once["reports"]["dev:AOI-1|r.htm"]
    assert cur["mtime"] == 200.0 and cur["path"] == r"\\host\share\AOI-1\Report\r.htm" and cur["rows"] == rows_b   # 늦은 수정본이 현재 판
    old = once["reports"]["dev:AOI-1|r.htm#1"]
    assert old["superseded_by"] == "dev:AOI-1|r.htm" and old["rows"] == rows_a
    assert "dev:AOI-1|other.htm" in once["reports"] and "dev:AOI-2|r.htm" in once["reports"]      # Reports/ 폴더 이름과 무관
    assert once["devices"]["dev:AOI-2"]["ids"] == [r"y:\aoi-2"] and once["devices"]["dev:AOI-3"]["ids"] == []
    assert once["last_mtime"] == {"dev:AOI-1": 200.0, "dev:AOI-2": 10.0, r"q:\gone": 1.0}          # 짝 없는 커서는 그대로
    assert list(once["failed"]) == ["dev:AOI-1|bad.htm"] and once["failed"]["dev:AOI-1|bad.htm"]["path"] == r"X:\AOI-1\Report\bad.htm"
    rec = once["identity"]
    assert rec["migrated"] == {"reports": 5, "failed": 1, "cursors": 3, "cursors_unmapped": 1, "no_id": 1, "superseded": 1}
    assert rec["conflicts"] == [{"kind": "revision", "key": "dev:AOI-1|r.htm", "kept": r"\\host\share\AOI-1\Report\r.htm",
                                 "superseded": r"X:\AOI-1\Report\r.htm"}]
    twice = json.loads(json.dumps(once))
    d2 = migrate(twice)
    assert not d2 and json.dumps(twice, sort_keys=True) == json.dumps(once, sort_keys=True)         # 멱등
    # 출력에서는 밀려난 옛 판만 빠진다(캐시에는 남는다)
    stats = {}
    rows, _ = collect._rows_from_cache(once, collect._DeviceIndex([dev]), {"scope_devices": ["*"]}, stats)
    assert stats["cache_superseded_rows"] == 1 and len(rows) == n_rows - 1


@pytest.mark.parametrize("path,root,expected", [
    (r"X:\AOI-1\Report\A_Batch.htm", r"X:\AOI-1", "a_batch.htm"),
    (r"x:\aoi-1\Reports\A.htm", r"X:\AOI-1", "a.htm"),                    # 폴더 이름(Report/Reports)·대소문자와 무관
    (r"\\?\UNC\host\share\AOI-1\Report\sub\A.htm", r"\\host\share\AOI-1", "sub/a.htm"),
    ("/nas/X/AOI-1/Report/A.htm", "/nas/X/AOI-1", "a.htm"),
    (r"X:\AOI-10\Report\A.htm", r"X:\AOI-1", "a.htm"),                    # 다른 장비 아래면 파일 이름만
    (r"X:\AOI-1\Report\A.htm", "", "a.htm"),
])
def test_rel_under_device_is_string_only_and_os_independent(path, root, expected):
    assert collect._rel_under_device(path, root) == expected
    assert collect.report_key("dev:AOI-1", expected) == f"dev:AOI-1|{expected}"


# ══════════════════════════════════════════════════════════════════════════════
# C04 — 저장 이유. 순수 no-op 은 파일을 건드리지 않는다
# ══════════════════════════════════════════════════════════════════════════════
def test_pure_noop_run_leaves_cache_mtime_and_bytes_untouched(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    stats0 = {}
    collect.collect(cfg, stats=stats0)
    assert stats0["cache_saved"] is True and {"created", "reports", "identity", "cursor"} <= set(stats0["cache_dirty"])
    stamp, raw = _stamp(cfg), _raw(cfg)
    time.sleep(0.02)
    for _ in range(2):
        stats = {}
        rows, meta, errors = collect.collect(cfg, stats=stats)
        assert len(rows) == 9 and not errors
        assert stats["cache_saved"] is False and stats["cache_dirty"] == {}
        assert _stamp(cfg) == stamp and _raw(cfg) == raw
    # backfill(검색 창만 넓힘)도 캐시된 파일을 건너뛰므로 no-op 이다
    stats = {}
    collect.collect(cfg, backfill=True, stats=stats)
    assert stats["cache_saved"] is False and _stamp(cfg) == stamp


def test_zero_new_rows_but_state_change_still_saves(tmp_path, fake_nas, monkeypatch):
    """rows 0건이어도 재시도 상태 · 규칙 번호 · 보관 정리 · 커서가 바뀌면 저장한다 — 놓치면 커서·복구 상태를 잃는다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    # (1) 규칙 번호만 다르다 → parser
    c = _cache_of(cfg)
    c["parser_version"] = 1
    open(cfg["cache_file"], "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False))
    stats = {}
    collect.collect(cfg, stats=stats)
    assert stats["cache_saved"] and stats["cache_dirty"] == {"parser": 1} and _cache_of(cfg)["parser_version"] == collect.PARSER_VERSION
    # (2) 새 Report 가 깨졌다 → failed(rows 는 그대로 9)
    bad = nas / "X" / "AOI-10" / "Report" / "BROKEN_x_BatchReport.htm"
    bad.write_text("<html>", encoding="utf-8")
    t = time.time() + 30
    os.utime(bad, (t, t))
    real = collect.parse_report
    monkeypatch.setattr(collect, "parse_report", lambda n, x: (_ for _ in ()).throw(ValueError("x")) if "BROKEN" in n else real(n, x))
    for i in range(1, collect.MAX_READ_RETRY + 1):
        stats = {}
        rows, _, errors = collect.collect(cfg, stats=stats)
        assert len(rows) == 9 and len(errors) == 1 and stats["cache_saved"] and "failed" in stats["cache_dirty"]
    assert "cursor" in stats["cache_dirty"]                     # 마지막 재시도 뒤 커서가 그 파일을 넘어간다(rows 0)
    # 시계 오차 창(CLOCK_SKEW_SEC) 안에 있는 동안은 나열에 다시 걸려 한 번 더 읽힌다 — 더 새 Report 가 커서를 밀면 그 뒤로는 no-op
    make_device(nas / "X", "AOI-10", report_name="2D@R2-GA285AAB_0859840PD-0A_6321_NEWER_26-Sep-13_(09.00.00)_BatchReport.htm", mtime=t + 600)
    stats = {}
    rows, _, _ = collect.collect(cfg, stats=stats)
    assert len(rows) == 12 and stats["cache_dirty"].get("reports") == 1
    stats = {}
    collect.collect(cfg, stats=stats)                           # 더는 붙잡지 않고 창 밖이니 이제 no-op
    assert stats["cache_saved"] is False and stats["cache_dirty"] == {}
    # (3) 보관 정리 → retention(rows 0, 항목 삭제)
    stats = {}
    collect.collect(dict(cfg, retention_days=1, backfill_days=1), stats=stats)   # 설정 검사(C13) 안의 값 — fixture 행(9/13)은 하루 창 밖
    assert stats["cache_saved"] and "retention" in stats["cache_dirty"] and _cache_of(cfg)["reports"] == {}


def test_corrupt_and_missing_cache_are_always_saved(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    (tmp_path / "out").mkdir()
    open(cfg["cache_file"], "wb").write(b"{")
    stats = {}
    collect.collect(cfg, stats=stats)
    assert "corrupt" in stats["cache_dirty"] and stats["cache_saved"] and stats["cache_preserved"]
    os.remove(cfg["cache_file"])
    stats = {}
    collect.collect(cfg, stats=stats)
    assert "created" in stats["cache_dirty"] and os.path.isfile(cfg["cache_file"])


def test_seen_is_not_touched_on_untouched_entries(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    before = {k: e["seen"] for k, e in _cache_of(cfg)["reports"].items()}
    make_device(nas / "X", "AOI-11", mtime=time.time() + 10)
    stats = {}
    collect.collect(cfg, stats=stats)
    after = _cache_of(cfg)["reports"]
    assert stats["cache_dirty"].get("reports") == 1 and len(after) == 4
    assert all(after[k]["seen"] == v for k, v in before.items())


# ══════════════════════════════════════════════════════════════════════════════
# C09 — 장비 색인
# ══════════════════════════════════════════════════════════════════════════════
def test_device_index_exact_hits_and_legacy_path_fallback_agree_with_linear_search(tmp_path):
    devs = [{"name": "25호기", "id": devices.device_id(tmp_path / "X" / "AOI-25"), "path": str(tmp_path / "X" / "AOI-25"), "key": "dev:AOI-25"},
            {"name": "AOI-1", "id": devices.device_id(tmp_path / "X" / "AOI-1"), "path": str(tmp_path / "X" / "AOI-1"), "key": "dev:AOI-1"}]
    idx = collect._DeviceIndex(devs)
    p25 = str(tmp_path / "X" / "AOI-25" / "Report" / "a.htm")
    by_key = {"device_key": "dev:AOI-25", "device_id": "stale-id", "path": str(tmp_path / "X" / "AOI-1" / "Report" / "a.htm")}
    by_id = {"device_id": devs[0]["id"], "path": p25}
    legacy = {"device": "AOI-25"}                                    # id 없는 옛 항목 — 경로로만
    assert idx.find(by_key)["name"] == "25호기"                        # 이름을 바꿔도(25호기) 키가 정답 — 경로는 보지 않는다
    assert idx.find(by_id)["name"] == "25호기"
    assert idx.find(legacy, p25)["name"] == "25호기" and idx.find(legacy, "/elsewhere/a.htm") is None
    assert idx.find({"device_key": "dev:AOI-99"}, p25) is None       # 정확한 키가 있는데 목록에 없다 — 경로 폴백 안 함(범위 밖 장비)
    # 예전 선형 탐색과 같은 답
    from aoi_capacity import nas_guard

    def linear(path, entry):
        for d in devs:
            if entry.get("device_id") and str(d["id"]) == str(entry["device_id"]):
                return d
            if nas_guard.is_under(path, str(d["path"])):
                return d
        return None
    for path, entry in ((p25, by_id), (p25, legacy), ("/elsewhere/a.htm", legacy)):
        assert idx.find(entry, path) is linear(path, entry)


def test_index_is_built_once_per_run(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    built = []
    real = collect._DeviceIndex.__init__

    def spy(self, devs):
        built.append(len(devs))
        real(self, devs)
    monkeypatch.setattr(collect._DeviceIndex, "__init__", spy)
    collect.collect(cfg)
    assert built == [3]


# ══════════════════════════════════════════════════════════════════════════════
# C07 — HTML 을 앞·데이터·뒤로 나눠 쓴다
# ══════════════════════════════════════════════════════════════════════════════
NASTY = "Scan Error: </script><script>alert(1)</script> 한글 상태 \u2028줄바꿈 \u2029 <!-- 끝 --> \\ \" '"


def _row(status):
    return {c: "" for c in collect.OUT_COLS} | {"device": "AOI-1", "status": status, "lot": "L", "wafer_id": "W",
                                                "batch_start": "13-Sep-26 05:25:14 PM", "batch_end": "13-Sep-26 05:32:21 PM",
                                                "report": "r.htm", "ini_match": "NOT_FOUND"}


def test_write_html_streams_and_round_trips_script_tag_korean_and_u2028(tmp_path):
    cfg = dict(collect.DEFAULT_CONFIG, output_dir=str(tmp_path / "out"), output_name="o.html", cache_file=str(tmp_path / "c.json"))
    target = collect.write_html(cfg, [_row(NASTY), _row("Pass")], [], [], time.time(), mode="test")
    raw = open(target, "rb").read()
    text = raw.decode("utf-8", errors="strict")
    head = text.index('id="embedded">') + len('id="embedded">')
    tail = text.index("</script>", head)
    body = text[head:tail]
    assert "</script>" not in body and "<\\/script>" in body and "\u2028" in body and "한글 상태" in body
    emb = json.loads(body)
    from sample_rows import unfold
    rows, meta = unfold(emb)
    assert rows[0]["status"] == NASTY and rows[1]["status"] == "Pass" and meta["mode"] == "test"
    assert text.count("__DATA__") == 0 and text.count('id="embedded"') == 1
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["o.html"]              # 임시 파일 없음
    node = shutil.which("node")
    if node:                                                                          # 브라우저와 같은 JSON.parse 로도 돌아온다
        js = ("const fs=require('fs');const t=fs.readFileSync(process.argv[1],'utf8');"
              "const m='id=\"embedded\">';const a=t.indexOf(m)+m.length;const b=t.indexOf('</script>',a);"
              "const e=JSON.parse(t.slice(a,b));process.stdout.write(e.pool[e.rows[0][e.cols.indexOf('status')]]);")
        out = subprocess.run([node, "-e", js, target], capture_output=True, text=True, timeout=60)
        assert out.returncode == 0 and out.stdout == NASTY


def test_write_html_rejects_template_without_exactly_one_data_slot(tmp_path, monkeypatch):
    cfg = dict(collect.DEFAULT_CONFIG, output_dir=str(tmp_path / "out"), output_name="o.html", cache_file=str(tmp_path / "c.json"))
    from aoi_capacity import nas_guard
    real = nas_guard.read_text
    monkeypatch.setattr(collect.nas_guard, "read_text", lambda p, *a, **k: real(p, *a, **k) + "__DATA__" if str(p).endswith("template.html") else real(p, *a, **k))
    with pytest.raises(RuntimeError, match="2곳"):
        collect.write_html(cfg, [], [], [], time.time())
    assert not (tmp_path / "out").exists() or not list((tmp_path / "out").iterdir())


def test_write_html_failure_keeps_the_previous_html(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    rows, meta, errors = collect.collect(cfg)
    target = collect.write_html(cfg, rows, meta, errors, time.time())
    raw = open(target, "rb").read()
    real = os.replace

    def locked(src, dst, *a, **k):
        if str(dst).endswith(".html"):
            raise PermissionError("잠김")
        return real(src, dst, *a, **k)
    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PermissionError):
        collect.write_html(cfg, rows, meta, errors, time.time())
    assert open(target, "rb").read() == raw
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["AOI_capacity.html", "aoi_cache.json"]
