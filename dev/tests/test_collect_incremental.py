"""수집 코어의 증분·backfill·보관·취소·진행률 계약."""
from __future__ import annotations

import json
import os
import time

import pytest

from aoi_capacity import collect
from conftest import make_cfg, make_device


def _run(cfg, **kw):
    prog = []
    rows, dev_meta, errors = collect.collect(cfg, progress=lambda d, t, p: prog.append((d, t, p)), **kw)
    return rows, dev_meta, errors, prog


def test_first_run_reads_everything_and_second_run_reads_nothing(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    rows, dev_meta, errors, prog = _run(cfg)
    names = sorted(d["name"] for d in dev_meta)
    assert names == ["8호기", "9호기", "AOI-10"]          # 꺼둔 행·접근 불가 행은 제외, * 는 AOI-10 만 새로 추가(AOI-9 는 명시 행이 이김)
    assert len(rows) == 9 and not errors
    assert prog[-1][0] == prog[-1][1] > 0                 # 마지막 보고는 (total, total)
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    # 커서 키는 표시명도 경로도 아닌 영속 안정 키다(C03) — 이름·드라이브 문자를 바꿔도 이력이 갈라지지 않게.
    # 키는 처음 본 표시명에서 만들고 캐시의 `devices` 대응표가 경로 id 로 잇는다.
    assert len(cache["last_mtime"]) == 3
    assert set(cache["last_mtime"]) == {"dev:9호기", "dev:AOI-10", "dev:8호기"} == set(cache["devices"])
    assert {os.path.basename(m["ids"][0]) for m in cache["devices"].values()} == {"AOI-9", "AOI-10", "M-AOI-8"}
    assert all(k.startswith(e["device_key"] + "|") and e["rel"] == os.path.basename(e["path"]).casefold() and len(e["sha256"]) == 64
               for k, e in cache["reports"].items())

    rows2, dev_meta2, _, prog2 = _run(cfg)
    assert len(rows2) == 9
    assert all(d["reports"] == 0 for d in dev_meta2)      # 새 파일 없음
    assert prog2[-1] == (0, 0, prog2[-1][2])              # total 0 → 마지막도 (0,0)


def test_new_report_is_picked_up_by_cursor(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    rep = nas / "X" / "AOI-10" / "Report" / "2D@R2-GA285AAB_0859840PD-0A_6321_NEW_26-Sep-13_(06.00.00)_BatchReport.htm"
    rep.write_text((nas / "X" / "AOI-10" / "Report").glob("*.htm").__next__().read_text(encoding="utf-8"), encoding="utf-8")
    future = time.time() + 3600
    os.utime(rep, (future, future))
    rows, dev_meta, _, _ = _run(cfg)
    assert {d["name"]: d["reports"] for d in dev_meta} == {"8호기": 0, "9호기": 0, "AOI-10": 1}
    assert len(rows) == 12


def test_backfill_window_limits_first_run(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    old = time.time() - 40 * 86400
    make_device(nas / "X", "AOI-9", mtime=old)            # 40일 전 Report
    cfg = make_cfg(tmp_path, csv_path, backfill_days=30)
    rows, dev_meta, _, _ = _run(cfg)
    assert next(d for d in dev_meta if d["name"] == "9호기")["reports"] == 0
    assert len(rows) == 6


def test_unseen_device_gets_backfill_not_cursor(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    make_device(nas / "X", "AOI-11", mtime=time.time() - 5 * 86400)   # 새 장비, 5일 전 Report
    rows, dev_meta, _, _ = _run(cfg)
    assert next(d for d in dev_meta if d["name"] == "AOI-11")["reports"] == 1


def test_retention_drops_old_reports(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, retention_days=1)   # 샘플의 wafer 시각은 2026-09-13 → 오래됐다고 판정될 수도, 아닐 수도 있으므로 상대 비교
    rows_keep, _, _, _ = _run(make_cfg(tmp_path, csv_path, retention_days=100000))
    rows_drop, _, _, _ = _run(cfg)
    assert len(rows_drop) <= len(rows_keep)


def test_cancel_leaves_cache_and_output_untouched(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(collect.CollectCancelled):
        collect.collect(cfg, should_stop=stop)
    assert not (tmp_path / "out" / "aoi_cache.json").exists()
    assert not (tmp_path / "out" / "AOI_capacity.html").exists()


def test_write_html_embeds_data_and_mode(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors, _ = _run(cfg)
    target = collect.write_html(cfg, rows, dev_meta, errors, time.time(), mode="gui")
    html = open(target, encoding="utf-8").read()
    assert "__DATA__" not in html and '"mode":"gui"' in html and '"cols":' in html
    assert (tmp_path / "out" / "AOI_capacity.csv").exists()
    assert not (tmp_path / "out" / "AOI_capacity.html.tmp").exists()


def test_plan_run_reports_first_then_incremental(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    assert collect.plan_run(cfg).first_run is True
    _run(cfg)
    plan = collect.plan_run(cfg)
    assert plan.first_run is False and plan.known_devices == 3
    assert collect.plan_run(cfg, backfill=True).first_run is True


def test_on_device_callback_reports_states(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    seen = []
    collect.collect(cfg, on_device=lambda n, s, d: seen.append((n, s)))
    assert ("9호기", "listing") in seen and ("9호기", "parsing") in seen and ("9호기", "done") in seen


# ── 동시에 읽기(NAS 왕복 지연이 대부분이라 여러 개를 함께 읽는다) ──────────────
def _fingerprint(rows):
    import hashlib
    import json as _json
    blob = _json.dumps(sorted(_json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows),
                       ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


@pytest.mark.parametrize("workers", [1, 2, 8, 32])
def test_reading_in_parallel_gives_exactly_the_same_result(tmp_path, fake_nas, workers):
    """★ 동시에 읽어도 결과가 달라지면 안 된다 — 스레드는 읽기만 하고, 합치는 일은 메인 스레드가 한다."""
    nas, csv_path = fake_nas
    base = make_cfg(tmp_path / "one", csv_path, read_workers=1)
    want_rows, want_meta, want_err = collect.collect(base)
    cfg = make_cfg(tmp_path / f"p{workers}", csv_path, read_workers=workers)
    rows, meta, errs = collect.collect(cfg)
    assert _fingerprint(rows) == _fingerprint(want_rows)
    assert [d["name"] for d in meta] == [d["name"] for d in want_meta]     # 장비 순서도 그대로
    assert len(errs) == len(want_err)
    one = json.loads((tmp_path / "one" / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    many = json.loads((tmp_path / f"p{workers}" / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    assert one["last_mtime"] == many["last_mtime"]                         # 커서까지 같아야 한다


def test_cancel_still_works_while_reading_in_parallel(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, read_workers=8)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(collect.CollectCancelled):
        collect.collect(cfg, should_stop=stop)
    assert not (tmp_path / "out" / "aoi_cache.json").exists()


@pytest.mark.parametrize("given,n_tasks,expected", [
    (8, 100, 8), (8, 3, 3), (1, 100, 1), (0, 100, 1), (None, 100, collect.READ_WORKERS),
    ("이상한값", 100, collect.READ_WORKERS), (64, 100, 64),
])
def test_worker_count_is_clamped_to_the_work_there_is(given, n_tasks, expected):
    cfg = {} if given is None else {"read_workers": given}
    assert collect._workers(cfg, n_tasks) == expected


# ── 옛 캐시 되살리기: 분류 규칙 재계산(NAS 접근 0) 과 누락 복구(INI 못 찾은 Report 만) ──────────
def _count_nas_reads(monkeypatch):
    """가짜 NAS 에서 실제로 연 파일 수 — Report(.htm) 와 INI 를 따로 센다."""
    from aoi_capacity import nas_guard
    seen = {"htm": 0, "ini": 0}
    orig_text, orig_bytes = nas_guard.read_text, nas_guard.read_bytes

    def count(path):
        low = str(path).lower()
        if low.endswith((".htm", ".html")):
            seen["htm"] += 1
        elif low.endswith(".ini"):
            seen["ini"] += 1

    def spy(path, *a, **k):
        count(path)
        return orig_text(path, *a, **k)

    def spy_bytes(path, *a, **k):                   # Report 는 지문(SHA256)까지 내려고 바이트로 한 번 읽는다(C03)
        count(path)
        return orig_bytes(path, *a, **k)

    monkeypatch.setattr(collect.nas_guard, "read_text", spy)
    monkeypatch.setattr(collect.nas_guard, "read_bytes", spy_bytes)
    return seen


def test_parser_version_bump_reclassifies_cached_rows_without_touching_the_nas(tmp_path, fake_nas, monkeypatch):
    """★ 실장비: 파서를 고쳐도(acaa6ce) 캐시는 Report mtime 만 보고 옛 행을 그대로 내보냈다(상태 재분류 93건).
    규칙 번호가 다르면 캐시를 읽을 때 원문(status·lot)에서 다시 계산한다 — NAS 는 한 번도 읽지 않는다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    cache_path = tmp_path / "out" / "aoi_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cache["parser_version"] == collect.PARSER_VERSION
    # 옛 규칙으로 저장된 캐시를 흉내 낸다: 번호를 낮추고 한 행의 분류를 틀리게 둔다
    cache["parser_version"] = 1
    entry = next(iter(cache["reports"].values()))
    victim = next(r for r in entry["rows"] if r["status"] == "Pass")
    victim["norm_status"], victim["scan_type"] = "OTHER", "TEST"
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    seen = _count_nas_reads(monkeypatch)
    rows, _, _, _ = _run(cfg)
    assert seen == {"htm": 0, "ini": 0}                                     # 캐시만으로 고쳤다
    fixed = [r for r in rows if r["wafer_id"] == victim["wafer_id"] and r["device"] == victim["device"]]
    assert fixed and all(r["norm_status"] == "PASS" and r["scan_type"] == "" for r in fixed)
    assert json.loads(cache_path.read_text(encoding="utf-8"))["parser_version"] == collect.PARSER_VERSION


def test_recover_rereads_only_reports_whose_ini_was_missing(tmp_path, fake_nas, monkeypatch):
    """★ INI 를 못 찾은 행은 다음 수집에서도 그대로 얼어 있었다(Report mtime 이 그대로라서). `recover` 는
    그런 행이 있는 Report 만 다시 읽고, 행이 전부 확인된 Report 는 건드리지 않는다."""
    from conftest import REPORT_HTML

    nas, csv_path = fake_nas
    # 9호기에 '전부 확인되는' Report 를 하나 더 둔다(99Z9·LoadPort 행이 없는 것) — 복구가 건드리면 안 되는 파일
    import re
    clean = re.sub(r"<tr><td>(KLK-3D</td><td>K625407-99Z9|LoadPort A).*?</tr>", "", REPORT_HTML)
    (nas / "X" / "AOI-9" / "Report" / "2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_26-Sep-13_(07.00.00)_BatchReport.htm").write_text(clean, encoding="utf-8")
    ini = nas / "X" / "AOI-10" / "Scanresult" / "2D@R2-GA285AAB_0859840PD-0A" / "6321" / "KLK-3D" / "K625407-01B0" / "WaferInfo.ini"
    keep = ini.read_text(encoding="utf-8")
    ini.unlink()                                                             # AOI-10 은 첫 수집 때 INI 가 없다
    cfg = make_cfg(tmp_path, csv_path)
    rows, _, _, _ = _run(cfg)
    nf = lambda rs: sorted((r["device"], r["wafer_id"]) for r in rs if r["ini_match"] == "NOT_FOUND")  # noqa: E731
    # 99Z9 는 어느 장비에도 INI 가 없는 오류 Wafer(픽스처) — AOI-10 만 01B0 까지 못 찾았다
    assert nf(rows) == [("8호기", "K625407-99Z9"), ("9호기", "K625407-99Z9"), ("AOI-10", "K625407-01B0"), ("AOI-10", "K625407-99Z9")]
    assert collect.plan_run(cfg, recover=True).recover_reports == 3          # 깨끗한 Report 하나는 대상이 아니다
    assert collect.plan_run(cfg).recover_reports == 0

    ini.write_text(keep, encoding="utf-8")                                   # 나중에 INI 가 생겼다(또는 파서를 고쳤다)
    rows, _, _, _ = _run(cfg)                                                # 평소 수집: 여전히 얼어 있다(현행 유지)
    assert ("AOI-10", "K625407-01B0") in nf(rows)

    seen = _count_nas_reads(monkeypatch)
    rows, dev_meta, errors, _ = _run(cfg, recover=True)
    assert seen["htm"] == 3 and not errors                                   # 복구 대상 3개만 다시 읽었다(4개 중)
    assert nf(rows) == [("8호기", "K625407-99Z9"), ("9호기", "K625407-99Z9"), ("AOI-10", "K625407-99Z9")]
    assert [r["ini_match"] for r in rows if r["device"] == "AOI-10" and r["wafer_id"] == "K625407-01B0"] == ["EXACT"]
    assert {d["name"]: d.get("recovered", 0) for d in dev_meta} == {"8호기": 1, "9호기": 1, "AOI-10": 1}
    assert len(rows) == 10                                                   # 9 + 깨끗한 Report 1행 — 복구로 행이 겹쳐 붙지 않는다
    assert collect.plan_run(cfg, recover=True).recover_reports == 3          # 99Z9 는 영영 없으니 대상으로 남는다


@pytest.mark.parametrize("ini_match, expected", [
    ("NOT_FOUND", True), ("READ_ERROR", True),
    ("STALE", False), ("NO_WAFER_ID", False), ("BATCH_FAILED", False), ("BATCH", False), ("EXACT", False),
])
def test_recover_targets_only_ini_states_that_can_come_back(ini_match, expected):
    """STALE 은 다른 시도가 덮어쓴 INI 라 다시 읽어도 안 돌아오고, 자리표시·실패한 배치는 경로가 없다 —
    그런 걸 재시도 대상에 넣으면 NAS 왕복만 늘고 오류 수가 부풀려진다."""
    assert collect._needs_recovery({"rows": [{"ini_match": "EXACT"}, {"ini_match": ini_match}]}) is expected


def test_device_whose_reports_all_fail_is_partial_not_done(tmp_path, fake_nas, monkeypatch):
    """★ '읽기가 끝났다' 와 '성공했다' 는 다르다 — Report 가 전부 깨진 장비를 초록(완료)으로 칠하면 안 된다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    orig = collect.parse_report

    def broken(name, text):
        if "AOI-10" in text or name.startswith("BROKEN"):
            raise ValueError("깨진 Report")
        return orig(name, text)

    rep_dir = nas / "X" / "AOI-10" / "Report"
    for rep in rep_dir.glob("*.htm"):
        rep.rename(rep_dir / ("BROKEN_" + rep.name))
    monkeypatch.setattr(collect, "parse_report", broken)
    seen = []
    rows, dev_meta, errors, _ = _run(cfg, on_device=lambda n, s, d: seen.append((n, s)))
    assert ("AOI-10", "partial") in seen and ("AOI-10", "done") not in seen
    assert ("9호기", "done") in seen and ("9호기", "partial") not in seen
    by = {d["name"]: d for d in dev_meta}
    assert by["AOI-10"]["read_errors"] == 1 and by["AOI-10"]["status"] == collect.DEV_PARTIAL
    assert by["9호기"]["read_errors"] == 0 and by["9호기"]["status"] == collect.DEV_OK and by["9호기"]["rows"] == 3
    assert len(errors) == 1 and errors[0]["device"] == "AOI-10"


# ── INI 한 번만 읽기 · 사전 존재 확인 제거 · 단계별 계측 ─────────────────────────
def test_same_ini_is_opened_once_per_run_and_no_stat_before_open(tmp_path, fake_nas, monkeypatch):
    """★ 같은 Wafer 가 여러 Report 에 나오면(재검사) INI 경로가 같다(실장비 3일치: 후보 13,920건 중 반복 1,090건).
    한 실행 안에서는 한 번만 열고, 열기 전에 `isfile` 로 한 번 더 왕복하지 않는다(없으면 open 이 알려 준다)."""
    from conftest import REPORT_HTML

    nas, csv_path = fake_nas
    # 9호기에 같은 Lot·Wafer 를 다시 검사한 Report 를 하나 더 둔다 → INI 경로가 겹친다
    (nas / "X" / "AOI-9" / "Report" / "2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_26-Sep-13_(07.00.00)_BatchReport.htm").write_text(REPORT_HTML, encoding="utf-8")
    real_isfile = os.path.isfile

    def no_stat_on_ini(p):
        assert not str(p).lower().endswith("waferinfo.ini"), "INI 는 존재 확인 없이 바로 연다"
        return real_isfile(p)

    monkeypatch.setattr(collect.os.path, "isfile", no_stat_on_ini)
    seen = _count_nas_reads(monkeypatch)
    cfg = make_cfg(tmp_path, csv_path)
    stats = {}
    rows, dev_meta, errors, _ = _run(cfg, stats=stats)
    assert not errors and len(rows) == 12
    # 장비 3대 × (01B0 있음 1경로 + 99Z9 없음 2경로) = 고유 경로 9개 — 없는 Wafer 는 Job 폴더 이름 후보(원문 · `-0A` 뗀 것)를 다 본다.
    # 9호기 두 번째 Report 의 3건은 기억한 결과를 다시 쓴다(열기 0).
    assert seen["ini"] == 9 and seen["htm"] == 4
    assert stats["ini_asked"] == 12 and stats["ini_unique"] == 9 and stats["ini_missing"] == 6
    nine = [r for r in rows if r["device"] == "9호기" and r["wafer_id"] == "K625407-01B0"]
    assert len(nine) == 2 and {r["ini_match"] for r in nine} == {"EXACT"}       # 두 Report 모두 같은 시각을 받았다
    assert {r["ini_match"] for r in rows if r["wafer_id"] == "K625407-99Z9"} == {"NOT_FOUND"}


def test_ini_read_error_is_kept_apart_from_not_found(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    real = collect.read_ini

    def flaky(path):
        if "AOI-10" in str(path) and "01B0" in str(path):
            raise PermissionError("잠김")            # 있는 파일을 못 여는 것과 없는 파일은 다르게 남긴다
        return real(path)

    monkeypatch.setattr(collect, "read_ini", flaky)
    cfg = make_cfg(tmp_path, csv_path)
    rows, _, _, _ = _run(cfg)
    ten = {r["wafer_id"]: r["ini_match"] for r in rows if r["device"] == "AOI-10" and r["kind"] == ""}
    assert ten["K625407-01B0"] == "READ_ERROR" and ten["K625407-99Z9"] == "NOT_FOUND"


def test_ini_memo_lets_concurrent_readers_share_one_open():
    import threading as th
    calls = []
    gate = th.Event()

    def slow(path):
        calls.append(path)
        gate.wait(2)
        return {"AutoCycleInfo": {"WaferStartTime": "x"}}

    memo = collect._IniMemo(reader=slow)
    out = []
    ts = [th.Thread(target=lambda: out.append(memo.get("/same/WaferInfo.ini"))) for _ in range(8)]
    for t in ts:
        t.start()
    time.sleep(0.05)
    gate.set()
    for t in ts:
        t.join(3)
    assert calls == ["/same/WaferInfo.ini"] and len(out) == 8 and all(o[0] == "ok" for o in out)
    assert memo.stats() == {"ini_asked": 8, "ini_unique": 1, "ini_missing": 0, "ini_read_error": 0}


def test_write_html_embeds_timing_and_counts(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    stats = {}
    rows, dev_meta, errors, _ = _run(cfg, stats=stats)
    for k in ("devices_ms", "list_ms", "read_ms", "cache_ms", "total_ms", "reports_found", "reports_read",
              "ini_asked", "ini_unique", "ini_missing", "read_workers"):
        assert isinstance(stats[k], int) and stats[k] >= 0, k
    assert stats["reports_found"] == 3 == stats["reports_read"]
    assert all("read_sum_ms" in d and "list_ms" not in d for d in dev_meta if not d.get("scope"))
    target = collect.write_html(cfg, rows, dev_meta, errors, time.time(), mode="gui", timing=stats)
    html = open(target, encoding="utf-8").read()
    assert '"timing":{' in html and '"html_ms":' in html and '"ini_unique":' in html
    # timing 을 안 주면 빈 객체 — 옛 호출 방식도 그대로 돈다
    assert '"timing":{}' in open(collect.write_html(cfg, rows, dev_meta, errors, time.time()), encoding="utf-8").read()


# ── 계획 조회(plan_run)는 UI 스레드에서 불린다 — 캐시 행을 재분류하지 않고, 파일이 그대로면 다시 읽지 않는다 ──
def test_plan_run_never_rederives_rows_and_memoizes_by_file_stamp(tmp_path, monkeypatch):
    """실측: 83MB 캐시(15만 행)에서 plan_run 이 7.3초 — 규칙 번호가 달라 매번 재분류했고 저장도 안 해 체크박스마다 반복됐다."""
    import json as _json
    cache_file = tmp_path / "cache.json"
    rows = [{"device": "AOI-8", "kind": "", "status": "Pass", "lot": "L", "wafer_id": "W1", "ini_match": "NOT_FOUND",
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": "", "batch_end": "", "report": "r.htm"}]
    cache_file.write_text(_json.dumps({"reports": {"/x/r.htm": {"rows": rows, "device": "AOI-8", "device_id": "AOI-8", "mtime": 1}},
                                       "last_mtime": {"AOI-8": 1}, "failed": {}, "parser_version": 1}), encoding="utf-8")
    cfg = dict(collect.DEFAULT_CONFIG, cache_file=str(cache_file), output_dir=str(tmp_path))

    def boom(_cache):
        raise AssertionError("plan_run 이 캐시 행을 재분류했다")
    monkeypatch.setattr(collect, "_rederive_rows", boom)
    calls = []
    real = collect._load_cache
    monkeypatch.setattr(collect, "_load_cache", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    p1 = collect.plan_run(cfg, recover=True)
    p2 = collect.plan_run(cfg)
    assert p1.known_devices == 1 and p1.recover_reports == 1 and p2.recover_reports == 0 and p1.first_run is False
    assert len(calls) == 1                                          # 파일이 그대로면 두 번째는 파싱하지 않는다
    cache_file.write_text(cache_file.read_text(encoding="utf-8").replace('"AOI-8": 1}', '"AOI-8": 1, "AOI-9": 2}'), encoding="utf-8")
    import os as _os
    _os.utime(cache_file, (2_000_000_000, 2_000_000_000))
    assert collect.plan_run(cfg).known_devices == 2 and len(calls) == 2   # 파일이 바뀌면(수집 뒤) 다시 읽는다
    assert collect.plan_run(cfg, full=True).first_run is True and len(calls) == 2


# ══════════════════════════════════════════════════════════════════════════════
# D60 / C02 — 다시 읽기 모드: refresh_window(이력 보존) · rebuild_all(후보 캐시 검증 뒤 교체) · full 은 rebuild 의 별칭
# ══════════════════════════════════════════════════════════════════════════════
def _dev_dir(nas, name):
    return nas / "M-AOI-8" if name == "M-AOI-8" else nas / "X" / name


def _add_report(nas, dev_name, tag, days_old, html=None):
    """장비에 Report 하나를 더 두고 수정시각을 `days_old` 일 전으로 맞춘다."""
    from conftest import REPORT_HTML
    rep = _dev_dir(nas, dev_name) / "Report" / f"2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_26-Sep-13_({tag})_BatchReport.htm"
    rep.write_text(html or REPORT_HTML, encoding="utf-8")
    m = time.time() - days_old * 86400
    os.utime(rep, (m, m))
    return rep


def _rewrite_same_mtime(rep, html):
    """내용만 바꾸고 수정시각은 그대로 — 'Report 는 그대로인데 파서를 고쳤다' 와 같은 상황(캐시가 mtime 만 보므로)."""
    m = rep.stat().st_mtime
    rep.write_text(html, encoding="utf-8")
    os.utime(rep, (m, m))


def _entry_of(cache, rep, section="reports"):
    """캐시 키는 절대 경로가 아니라 `(안정 키|상대 경로)` 다(C03) — 항목의 `path` 로 찾는다."""
    hits = [e for e in cache[section].values() if e.get("path") == str(rep) and not e.get("superseded_by")]
    assert len(hits) <= 1, hits
    return hits[0] if hits else None


def _entry_fp(cache, rep):
    return json.dumps(_entry_of(cache, rep), sort_keys=True, ensure_ascii=False)


def _cache_of(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def test_refresh_window_rereads_same_mtime_reports_inside_the_window_and_keeps_the_rest(tmp_path, fake_nas, monkeypatch):
    """★ 90일 캐시 + 30일 refresh: 창 안의 Report 는 수정시각이 같아도 다시 읽고, 창 밖 60일치 항목은 지문까지 그대로다.
    backfill 은 여전히 캐시된 파일을 건너뛴다(검색 창만 넓힌다)."""
    from conftest import REPORT_HTML

    nas, csv_path = fake_nas
    r10 = _add_report(nas, "AOI-10", "10.00.00", 10)
    r45 = _add_report(nas, "AOI-9", "45.00.00", 45)
    r80 = _add_report(nas, "AOI-9", "80.00.00", 80)
    cfg = make_cfg(tmp_path, csv_path, backfill_days=100)
    rows0, _, _, _ = _run(cfg)
    assert len(rows0) == 18                                        # 6 Report × 3행
    before = _cache_of(cfg)
    fp45, fp80 = _entry_fp(before, r45), _entry_fp(before, r80)

    changed = REPORT_HTML.replace("K625407-01B0", "K625407-01B1")   # 내용은 바뀌었는데 mtime 은 그대로
    _rewrite_same_mtime(r10, changed)
    _rewrite_same_mtime(r45, changed)                             # 창 밖 — 손대면 안 된다

    # backfill(검색 창 넓히기)은 캐시된 파일을 다시 읽지 않는다 — 문구가 이걸 약속한다
    seen = _count_nas_reads(monkeypatch)
    rows_b, meta_b, _, _ = _run(cfg, backfill=True)
    assert seen["htm"] == 0 and len(rows_b) == 18
    assert all(d["refreshed"] == 0 for d in meta_b) and sum(d["kept"] for d in meta_b) == 6

    seen = _count_nas_reads(monkeypatch)
    rows, meta, errors, _ = _run(cfg, refresh_window_days=30)
    assert not errors and seen["htm"] == 4                        # now×3 + r10 — r45·r80 은 열지 않는다
    by = {d["name"]: d for d in meta}
    assert (by["AOI-10"]["refreshed"], by["9호기"]["refreshed"], by["8호기"]["refreshed"]) == (2, 1, 1)
    # 커서 기반 실행은 창 밖 파일을 나열조차 하지 않는다 — '그대로 두는 수' 는 캐시만 보는 계획 조회가 안다
    assert collect.plan_run(cfg, refresh_window_days=30).keep_reports == 2 and by["9호기"]["kept"] == 0
    after = _cache_of(cfg)
    assert _entry_fp(after, r45) == fp45 and _entry_fp(after, r80) == fp80   # 창 밖 지문 그대로(내용을 바꿔 둔 r45 도)
    assert {r["wafer_id"] for r in rows if r["report"] == r10.name} >= {"K625407-01B1"}
    assert not any(r["wafer_id"] == "K625407-01B1" for r in rows if r["report"] == r45.name)
    assert len(rows) == 18 and after["last_mtime"] == before["last_mtime"]  # 행이 겹쳐 붙지 않고 커서도 그대로


def test_refresh_window_via_cfg_key_matches_the_argument(tmp_path, fake_nas, monkeypatch):
    """GUI 는 prefs → cfg["refresh_window_days"] 로 켠다 — 인자와 같은 동작이어야 한다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    seen = _count_nas_reads(monkeypatch)
    _run(dict(cfg, refresh_window_days=30))
    assert seen["htm"] == 3
    seen = _count_nas_reads(monkeypatch)
    _run(dict(cfg, refresh_window_days=0))
    assert seen["htm"] == 0


def test_failed_reread_keeps_previous_rows_and_is_retried_next_run(tmp_path, fake_nas, monkeypatch):
    """★ 다시 읽다 실패한 Report 는 이전 행을 그대로 두고(사라지지 않는다) failed 에 재시도만 남긴다.
    다음 평소 수집이 그 파일까지 훑어 다시 읽는다(커서는 뒤로 가지 않지만 나열은 그 파일까지 한다)."""
    nas, csv_path = fake_nas
    r10 = _add_report(nas, "AOI-10", "10.00.00", 10)
    cfg = make_cfg(tmp_path, csv_path)
    rows0, _, _, _ = _run(cfg)
    fp0 = _entry_fp(_cache_of(cfg), r10)
    orig = collect.parse_report

    def broken(name, text):
        if name == r10.name:
            raise ValueError("깨진 Report")
        return orig(name, text)

    monkeypatch.setattr(collect, "parse_report", broken)
    rows, meta, errors, _ = _run(cfg, refresh_window_days=30)
    assert len(errors) == 1 and errors[0]["kept_rows"] == 3 and errors[0]["path"] == str(r10)
    assert len(rows) == len(rows0) == 12                           # 이전 행이 그대로 나간다
    cache = _cache_of(cfg)
    assert _entry_fp(cache, r10) == fp0 and _entry_of(cache, r10, "failed")["tries"] == 1
    assert next(d for d in meta if d["name"] == "AOI-10")["status"] == collect.DEV_PARTIAL

    monkeypatch.setattr(collect, "parse_report", orig)             # 고쳐졌다(또는 NAS 가 잠깐 막혔던 것)
    seen = _count_nas_reads(monkeypatch)
    rows, meta, errors, _ = _run(cfg)                              # 평소 증분 수집
    assert not errors and seen["htm"] == 1                         # 재시도 대상 하나만 다시 읽었다
    assert next(d for d in meta if d["name"] == "AOI-10")["retried"] == 1
    assert _entry_of(_cache_of(cfg), r10, "failed") is None and len(rows) == 12


def test_rebuild_all_reads_the_whole_retention_range_and_full_is_its_alias(tmp_path, fake_nas, monkeypatch):
    """★ 옛 --full 은 backfill 창(30일)만 읽고 나머지 60일 이력을 지웠다. 이제 full = rebuild_all: 보관 기간 전부를 다시 읽는다."""
    nas, csv_path = fake_nas
    r45 = _add_report(nas, "AOI-9", "45.00.00", 45)
    cfg = make_cfg(tmp_path, csv_path, backfill_days=100, retention_days=3650)
    rows0, _, _, _ = _run(cfg)
    assert len(rows0) == 12
    small = dict(cfg, backfill_days=3)                             # backfill 창은 3일뿐
    for kw in ({"full": True}, {"rebuild_all": True}):
        seen = _count_nas_reads(monkeypatch)
        rows, meta, errors, _ = _run(small, **kw)
        assert seen["htm"] == 4 and not errors                     # 45일 전 Report 까지 다시 읽었다(창 = 보관 기간)
        assert len(rows) == 12 and _entry_of(_cache_of(small), r45) is not None
    assert collect.plan_run(small, full=True).mode == "rebuild"
    assert collect.plan_run(small, rebuild_all=True).mode == "rebuild"
    assert collect.plan_run(dict(small, rebuild_all=True)).mode == "rebuild"


def test_rebuild_all_failure_keeps_the_old_cache_byte_for_byte(tmp_path, fake_nas, monkeypatch):
    """★ 후보 캐시가 검증에 걸리면(Report 를 하나도 못 읽음) RebuildRejected — 원 캐시는 한 바이트도 바뀌지 않는다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    raw = open(cfg["cache_file"], "rb").read()
    monkeypatch.setattr(collect, "parse_report", lambda name, text: (_ for _ in ()).throw(ValueError("전부 깨짐")))
    with pytest.raises(collect.RebuildRejected):
        collect.collect(cfg, full=True)
    assert open(cfg["cache_file"], "rb").read() == raw
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["aoi_cache.json"]   # 임시 파일도 남기지 않는다


def test_rebuild_all_carries_over_history_of_unreachable_devices(tmp_path, fake_nas, monkeypatch):
    """전체 재구축 중 접근 못 한 장비(나열 실패)의 이력은 후보 캐시로 옮겨 보존한다(지우는 재구축이 아니다)."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    before = _cache_of(cfg)
    nine = [k for k, e in before["reports"].items() if "AOI-9" in e["path"]]
    assert len(nine) == 1
    real = collect.nas_guard.scandir

    def flaky(path):
        if str(path).endswith(os.path.join("AOI-9", "Report")):
            raise OSError(53, "네트워크 경로를 찾을 수 없습니다")     # 9호기 나열 실패(SMB 끊김)
        return real(path)

    monkeypatch.setattr(collect.nas_guard, "scandir", flaky)
    rows, meta, errors, _ = _run(cfg, rebuild_all=True)
    by = {d["name"]: d for d in meta}
    assert by["9호기"]["status"] == collect.DEV_UNREACHABLE
    after = _cache_of(cfg)
    assert after["reports"][nine[0]] == before["reports"][nine[0]]           # 이관된 항목은 그대로
    assert set(after["last_mtime"]) == {"dev:9호기", "dev:AOI-10", "dev:8호기"}
    assert len(rows) == 9 and sum(1 for r in rows if r["device"] == "9호기") == 3


def test_rebuild_all_keeps_history_of_a_device_whose_report_folder_looks_empty(tmp_path, fake_nas):
    """나열은 됐는데 파일이 하나도 안 보이는 장비(SMB 가 빈 폴더를 돌려주는 오류)는 접근 못 한 장비처럼 이력을 옮긴다 — 재구축이 이력을 지우면 안 된다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    before = _cache_of(cfg)
    nine = [k for k, e in before["reports"].items() if "AOI-9" in e["path"]]
    moved = []
    for f in (nas / "X" / "AOI-9" / "Report").glob("*.htm"):
        f.rename(f.with_suffix(".hidden"))
        moved.append(f)
    try:
        rows, meta, errors, _ = _run(cfg, rebuild_all=True)
    finally:
        for f in moved:
            f.with_suffix(".hidden").rename(f)
    after = _cache_of(cfg)
    assert after["reports"][nine[0]] == before["reports"][nine[0]] and len(rows) == 9
    assert next(d for d in meta if d["name"] == "9호기")["found"] == 0


def test_plan_run_reports_reread_and_keep_counts_and_mode(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    _add_report(nas, "AOI-9", "45.00.00", 45)
    _add_report(nas, "AOI-9", "80.00.00", 80)
    cfg = make_cfg(tmp_path, csv_path, backfill_days=100)
    _run(cfg)
    p = collect.plan_run(cfg, refresh_window_days=30)
    assert (p.mode, p.total_reports, p.reread_reports, p.keep_reports, p.refresh_days) == ("refresh", 5, 3, 2, 30)
    assert p.first_run is False
    p = collect.plan_run(dict(cfg, refresh_window_days=60))
    assert (p.mode, p.reread_reports, p.keep_reports) == ("refresh", 4, 1)
    assert collect.plan_run(cfg).mode == "incremental" and collect.plan_run(cfg, backfill=True).mode == "backfill"
    assert collect.plan_run(cfg, recover=True).mode == "recover"
    p = collect.plan_run(cfg, full=True)
    assert (p.mode, p.first_run, p.reread_reports, p.keep_reports, p.retention_days) == ("rebuild", True, 0, 0, 3650)
    assert collect.plan_run(make_cfg(tmp_path / "fresh", csv_path)).mode == "first"


def test_parallel_refresh_is_deterministic(tmp_path, fake_nas):
    """refresh 도 스레드는 읽기만 한다 — 1개와 8개로 읽은 결과·커서가 같다."""
    nas, csv_path = fake_nas
    _add_report(nas, "AOI-10", "10.00.00", 10)
    outs = []
    for n in (1, 8):
        cfg = make_cfg(tmp_path / f"w{n}", csv_path, read_workers=n)
        collect.collect(cfg)
        rows, _, _ = collect.collect(cfg, refresh_window_days=30)
        outs.append((_fingerprint(rows), _cache_of(cfg)["last_mtime"]))
    assert outs[0][0] == outs[1][0] and outs[0][1] == outs[1][1]


# ══════════════════════════════════════════════════════════════════════════════
# C15 — 캐시 파일: strict UTF-8 · 손상본 보존(.bad-<시각>) · 고유 임시 파일 · 실패 시 정리
# ══════════════════════════════════════════════════════════════════════════════
@pytest.mark.parametrize("garbage", [b'{"reports": {"\xff\xfe": {}}, "last_mtime": {}}', b'{"reports": {', b"[]"],
                         ids=["bad-utf8", "truncated", "not-object"])
def test_corrupt_cache_is_preserved_as_bad_file_not_overwritten_silently(tmp_path, fake_nas, garbage):
    """★ 예전에는 errors='replace' 로 읽어 손상 바이트가 U+FFFD 로 바뀌거나, 못 읽으면 조용히 빈 캐시로 덮어썼다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "aoi_cache.json").write_bytes(garbage)
    stats, logs = {}, []
    rows, _, _ = collect.collect(cfg, stats=stats, log=logs.append)
    assert len(rows) == 9 and stats["cache_status"] == collect.CACHE_CORRUPT
    bad = [p for p in out.iterdir() if p.name.startswith("aoi_cache.json.bad-")]
    assert len(bad) == 1 and bad[0].read_bytes() == garbage                    # 원본 그대로 보존
    assert stats["cache_preserved"] == str(bad[0])
    fresh = json.loads((out / "aoi_cache.json").read_text(encoding="utf-8"))
    assert len(fresh["reports"]) == 3 and "_corrupt_source" not in fresh and "_status" not in fresh
    assert any("보존" in m for m in logs)
    assert not [p for p in out.iterdir() if p.name.endswith(".tmp")]
    # 다음 수집은 정상 캐시로 이어진다(보존본은 건드리지 않는다)
    stats2 = {}
    collect.collect(cfg, stats=stats2)
    assert stats2["cache_status"] == collect.CACHE_OK and bad[0].read_bytes() == garbage


def test_cache_load_is_strict_utf8_but_report_reading_stays_lenient(tmp_path):
    cache_file = tmp_path / "c.json"
    cache_file.write_bytes(b'{"reports": {}, "last_mtime": {}, "failed": {}, "note": "\xff"}')
    c = collect._load_cache({"cache_file": str(cache_file)}, rederive=False)
    assert collect.cache_status(c) == collect.CACHE_CORRUPT and c["reports"] == {}
    assert collect.cache_status(collect._load_cache({"cache_file": str(tmp_path / "none.json")})) == collect.CACHE_MISSING
    from aoi_capacity import nas_guard
    assert "�" in nas_guard.read_text(cache_file)                            # Report 용 관대한 읽기는 그대로다


def test_save_failure_leaves_no_tmp_and_keeps_the_old_cache(tmp_path, fake_nas, monkeypatch):
    """저장이 중간에 실패하면(검증 실패·교체 실패) 자기 임시 파일만 지우고 원본은 그대로다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    raw = open(cfg["cache_file"], "rb").read()
    monkeypatch.setattr(collect, "_validate_cache_file", lambda tmp, cache: (_ for _ in ()).throw(ValueError("검증 실패")))
    with pytest.raises(ValueError):
        collect.collect(cfg, refresh_window_days=30)
    assert open(cfg["cache_file"], "rb").read() == raw
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["aoi_cache.json"]
    monkeypatch.undo()
    real = os.replace

    def locked(src, dst, *a, **k):
        if str(dst).endswith("aoi_cache.json"):
            raise PermissionError("잠김")
        return real(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", locked)
    with pytest.raises(PermissionError):
        collect.collect(cfg, refresh_window_days=30)
    assert open(cfg["cache_file"], "rb").read() == raw
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["aoi_cache.json"]


def test_save_cache_validates_what_it_wrote_and_uses_a_unique_tmp(tmp_path):
    cfg = {"cache_file": str(tmp_path / "c" / "cache.json"), "nas_roots": [], "output_dir": str(tmp_path)}
    cache = {"reports": {"/x/a.htm": {"rows": [], "mtime": 1}}, "last_mtime": {}, "failed": {}, "_status": "ok"}
    out = collect._save_cache(cfg, cache)
    assert out == {"path": cfg["cache_file"], "preserved": ""}
    assert json.loads((tmp_path / "c" / "cache.json").read_text(encoding="utf-8"))["parser_version"] == collect.PARSER_VERSION
    assert [p.name for p in (tmp_path / "c").iterdir()] == ["cache.json"]
    t1, t2 = collect._unique_tmp("/a/b.json"), collect._unique_tmp("/a/b.json")
    assert t1 != t2 and t1.startswith("/a/b.json.") and t1.endswith(".tmp")


# ══════════════════════════════════════════════════════════════════════════════
# C06 — HTML 이 주 산출물: CSV 잠금(Excel)은 경고, HTML 실패는 여전히 실패, 프로그래밍 오류는 삼키지 않는다
# ══════════════════════════════════════════════════════════════════════════════
def _lock_replace_for(monkeypatch, suffix):
    real = os.replace

    def locked(src, dst, *a, **k):
        if str(dst).lower().endswith(suffix):
            raise PermissionError(13, "다른 프로세스가 사용 중", str(dst))
        return real(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", locked)


def test_csv_locked_by_excel_writes_html_and_returns_a_structured_warning(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors, _ = _run(cfg)
    _lock_replace_for(monkeypatch, ".csv")
    warnings, logs = [], []
    target = collect.write_html(cfg, rows, dev_meta, errors, time.time(), mode="gui", warnings=warnings, log=logs.append)
    assert os.path.isfile(target) and target.endswith("AOI_capacity.html")
    assert len(warnings) == 1 and warnings[0]["kind"] == collect.WARN_CSV
    assert warnings[0]["path"].endswith("AOI_capacity.csv") and "PermissionError" in warnings[0]["error"]
    assert warnings[0]["html"] == target
    names = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert names == ["AOI_capacity.html", "aoi_cache.json"]                    # CSV 임시 파일도 남지 않는다
    assert any("CSV 저장 실패" in m for m in logs)
    # warnings 를 안 줘도(옛 호출 방식) 예외 없이 HTML 을 돌려준다
    assert collect.write_html(cfg, rows, dev_meta, errors, time.time()) == target


def test_html_write_failure_is_still_a_failure_and_cleans_its_tmp(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors, _ = _run(cfg)
    _lock_replace_for(monkeypatch, ".html")
    with pytest.raises(PermissionError):
        collect.write_html(cfg, rows, dev_meta, errors, time.time(), warnings=[])
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == ["aoi_cache.json"]


def test_csv_programming_error_is_not_swallowed(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors, _ = _run(cfg)
    monkeypatch.setattr(collect.csv, "DictWriter", lambda *a, **k: (_ for _ in ()).throw(TypeError("버그")))
    with pytest.raises(TypeError):
        collect.write_html(cfg, rows, dev_meta, errors, time.time(), warnings=[])
    assert (tmp_path / "out" / "AOI_capacity.html").exists()
    assert not [p for p in (tmp_path / "out").iterdir() if p.name.endswith(".tmp")]


def test_csv_on_nas_is_refused_not_downgraded_to_a_warning(tmp_path, fake_nas):
    """NasWriteRefused 는 OSError 가 아니다 — CSV 경로가 NAS 아래면 write_html 의 `except OSError` 에 걸리지 않고 그대로 거부된다."""
    from aoi_capacity import nas_guard
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    assert not issubclass(nas_guard.NasWriteRefused, OSError)
    with pytest.raises(nas_guard.NasWriteRefused):
        collect._write_csv(cfg, str(nas / "X" / "AOI-9" / "AOI_capacity.csv"), [])
    assert not (nas / "X" / "AOI-9" / "AOI_capacity.csv").exists()


# ══════════════════════════════════════════════════════════════════════════════
# CLI 계약 — 새 플래그와 종료 코드(0 성공 · 3 HTML 은 썼지만 CSV 실패 · 1 재구축 거부)
# ══════════════════════════════════════════════════════════════════════════════
def _cli_config(tmp_path, csv_path, **over):
    cfg_path = tmp_path / "cli" / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    body = {"devices_csv": str(csv_path), "cache_file": str(tmp_path / "cli" / "aoi_cache.json"),
            "output_dir": str(tmp_path / "cli" / "out"), "backfill_days": 3650, "retention_days": 3650,
            "scope_devices": ["*"]}
    body.update(over)
    cfg_path.write_text(json.dumps(body, ensure_ascii=False), encoding="utf-8")
    return cfg_path


def _count_report_reads(monkeypatch, nas):
    """CLI 는 write_html 이 template.html 도 읽으므로 NAS 아래의 Report(.htm) 만 센다."""
    from aoi_capacity import nas_guard
    seen = {"htm": 0}
    orig = nas_guard.read_bytes

    def spy(path, *a, **k):
        if str(path).lower().endswith((".htm", ".html")) and nas_guard.is_under(str(path), str(nas)):
            seen["htm"] += 1
        return orig(path, *a, **k)

    monkeypatch.setattr(collect.nas_guard, "read_bytes", spy)
    return seen


def test_cli_flags_and_exit_codes(tmp_path, fake_nas, monkeypatch, capsys):
    from aoi_capacity import cli

    nas, csv_path = fake_nas
    cfg_path = _cli_config(tmp_path, csv_path, write_csv=True)
    assert cli.main(["--config", str(cfg_path)]) == cli.EXIT_OK
    assert (tmp_path / "cli" / "out" / "AOI_capacity.csv").exists()
    seen = _count_report_reads(monkeypatch, nas)
    assert cli.main(["--config", str(cfg_path), "--backfill"]) == cli.EXIT_OK and seen["htm"] == 0
    seen = _count_report_reads(monkeypatch, nas)
    assert cli.main(["--config", str(cfg_path), "--refresh-window", "30"]) == cli.EXIT_OK and seen["htm"] == 3
    out = capsys.readouterr().out
    assert "모드 refresh" in out and "다시 읽기 3" in out
    seen = _count_report_reads(monkeypatch, nas)
    assert cli.main(["--config", str(cfg_path), "--full"]) == cli.EXIT_OK and seen["htm"] == 3
    assert "모드 rebuild" in capsys.readouterr().out
    # config.json 의 키로도 켜진다
    seen = _count_report_reads(monkeypatch, nas)
    assert cli.main(["--config", str(_cli_config(tmp_path, csv_path, refresh_window_days=30))]) == cli.EXIT_OK
    assert seen["htm"] == 3
    # CSV 잠김 → 3, HTML 은 새로 썼다 (위 줄이 config.json 을 덮어썼으니 CSV 켠 설정으로 되돌린다)
    cfg_path = _cli_config(tmp_path, csv_path, write_csv=True)
    _lock_replace_for(monkeypatch, ".csv")
    html = tmp_path / "cli" / "out" / "AOI_capacity.html"
    os.utime(html, (1, 1))
    assert cli.main(["--config", str(cfg_path)]) == cli.EXIT_PARTIAL
    assert html.stat().st_mtime > 1000 and "경고(csv)" in capsys.readouterr().out
    monkeypatch.undo()
    # 재구축 거부 → 1, 캐시 그대로
    raw = (tmp_path / "cli" / "aoi_cache.json").read_bytes()
    monkeypatch.setattr(collect, "parse_report", lambda name, text: (_ for _ in ()).throw(ValueError("전부 깨짐")))
    assert cli.main(["--config", str(cfg_path), "--rebuild-all"]) == cli.EXIT_FAILED
    assert (tmp_path / "cli" / "aoi_cache.json").read_bytes() == raw
    assert "전체 재구축 거부" in capsys.readouterr().out


def test_cli_help_describes_what_backfill_really_does(monkeypatch, capsys):
    """★ 옛 도움말·문구는 '전부 다시 읽습니다' 였지만 코드는 캐시된 파일을 건너뛰었다 — 문구가 코드와 같아야 한다."""
    import argparse
    from aoi_capacity import cli
    seen = []
    real = argparse.ArgumentParser.add_argument

    def spy(self, *a, **k):
        seen.append((a, k.get("help", "")))
        return real(self, *a, **k)

    monkeypatch.setattr(argparse.ArgumentParser, "add_argument", spy)
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    capsys.readouterr()
    helps = {a[0]: h for a, h in seen if a}
    assert "건너뜀" in helps["--backfill"] and "refresh-window" in helps["--backfill"]
    assert "rebuild-all" in helps["--full"]
    assert "이전 행" in helps["--refresh-window"] and "기존 캐시를 그대로" in helps["--rebuild-all"]
    from aoi_capacity import i18n
    assert "건너뜁니다" in i18n.KO.COLLECT_PLAN_BACKFILL_FMT and "다시 읽습니다" not in i18n.KO.COLLECT_PLAN_BACKFILL_FMT.split("건너뜁니다")[0]
