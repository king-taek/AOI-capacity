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
    # 커서 키는 표시명이 아니라 정규화한 장비 경로다(이름을 바꿔도 이력이 갈라지지 않게)
    assert len(cache["last_mtime"]) == 3
    assert {os.path.basename(k) for k in cache["last_mtime"]} == {"AOI-9", "AOI-10", "M-AOI-8"}

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
    orig = nas_guard.read_text

    def spy(path, *a, **k):
        low = str(path).lower()
        if low.endswith((".htm", ".html")):
            seen["htm"] += 1
        elif low.endswith(".ini"):
            seen["ini"] += 1
        return orig(path, *a, **k)

    monkeypatch.setattr(collect.nas_guard, "read_text", spy)
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
    # 장비 3대 × (01B0 있음 + 99Z9 없음) = 고유 경로 6개. 9호기 두 번째 Report 의 2건은 기억한 결과를 다시 쓴다.
    assert seen["ini"] == 6 and seen["htm"] == 4
    assert stats["ini_asked"] == 8 and stats["ini_unique"] == 6 and stats["ini_missing"] == 3
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
