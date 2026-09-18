"""결과 화면(template.html)의 **분류·시간 모델을 실제로 실행**해 본다 — 문자열 검사(test_template_contract.py)와 다르다.

`dev/tests/js_harness.js` 가 template 의 스크립트를 Node 의 vm 에서 돌려 build()·dayMetrics()·자재 이력 결과를 JSON 으로 낸다.
DOM 은 대역(stub)이고 네트워크·파일 쓰기는 없다. Node 가 없는 환경에서는 이 파일만 skip 된다(화면 실측은 Chromium 으로 따로 — 진행상황.md).

모든 사례는 **합성 fixture** 다(사용자 확정 요구 U01·U03 과 인계 프롬프트의 T01~T25 를 옮겼다). 실제 첨부에서 볼 수 없는
8호기→9호기 이동·겹침·시계 역전·식별 충돌을 여기서 만든다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "dev" / "tests" / "js_harness.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="node 가 없는 환경 — 화면 모델 실행 테스트는 건너뛴다")

DAY = "2026-09-15"
FAR = "2026-12-31"   # '오늘' 이 데이터에 없게 — 분모가 24시간으로 고정된다


def run(rows, today=FAR):
    out = subprocess.run([NODE, str(HARNESS)], input=json.dumps({"rows": rows, "today": today}),
                         capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def w(dev, wafer, s, e, lot="LOT-A", status="Pass", recipe="R1", report=None, day=DAY, job="J1", **k):
    """Wafer 행 하나 — 시각은 그날 HH:MM[:SS]. Job 은 기본 J1(같은 공정) — D36 은 Job 원문이 같을 때만 반복을 잇는다."""
    iso = lambda t: f"{day}T{t if t.count(':') == 2 else t + ':00'}"
    return {"device": dev, "lot": lot, "wafer_id": wafer, "status": status, "recipe": recipe, "job": job,
            "wafer_start_time": iso(s), "wafer_end_time": iso(e), "batch_start": iso(s), "batch_end": iso(e),
            "report": report or f"{dev}_{lot}_{s}_BatchReport.htm", **k}


def att(res, dev, wafer, report=None):
    for a in res["attempts"]:
        if a["dev"] == dev and a["wafer"] == wafer and (report is None or a["report"] == report):
            return a
    raise AssertionError(f"attempt {dev}/{wafer} 없음")


# ── T01 · U01: 같은 장비에서 이어서 다시 스캔 = 중복스캔, 시간은 둘 다 ─────────────────────────
def test_t01_same_device_repeat_is_duplicate_scan_and_both_times_count():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-8", "W1", "09:06", "09:11")])
    m = res["per"]["AOI-8"][DAY]
    assert m["run"] == 600 and m["dup"] == 300 and m["nDup"] == 1
    a1, a2 = sorted([a for a in res["attempts"]], key=lambda a: a["s"])
    assert a1["rel"] == "FIRST_OBSERVED" and a1["disp"] == "RUN"          # 첫 시도는 소급해서 바꾸지 않는다
    assert a2["rel"] == "SAME_DEVICE_REPEAT" and a2["disp"] == "DUP" and a2["conf"] == "confirmed"
    assert a2["no"] == 2 and a2["of"] == 2
    assert m["off"] == 86400 - 600                                        # 60초 공백은 가동이 아니다


# ── T02: 같은 원본 행이 두 번 → 한 번 ────────────────────────────────────────────────────────
def test_t02_same_raw_record_twice_counts_once():
    r = w("AOI-8", "W1", "09:00", "09:05")
    res = run([r, dict(r)])
    m = res["per"]["AOI-8"][DAY]
    assert m["run"] == 300 and m["nWafer"] == 1 and m["dup"] == 0
    assert len(res["attempts"]) == 1 and res["attempts"][0]["rawDups"] == 2


# ── T03: Report 두 개가 같은 INI 시각을 참조 → 시간 한 번, 이력 보존, 재스캔 단정 금지 ───────
def test_t03_two_reports_same_timing_reference_counts_once_and_is_not_a_rescan():
    res = run([w("AOI-8", "W1", "09:00", "09:05", report="rep1.htm"), w("AOI-8", "W1", "09:00", "09:05", report="rep2.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["run"] == 300 and m["dup"] == 0 and m["rescan"] == 0
    a = res["attempts"][0]
    assert len(res["attempts"]) == 1 and a["refs"] == 2 and a["disp"] == "RUN"


# ── T04·T05·T06 · U03: 8호기 → 9호기 ─────────────────────────────────────────────────────────
def test_t04_cross_device_after_pass_is_rescan_on_the_second_device_only():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-9", "W1", "10:00", "10:05")])
    assert res["per"]["AOI-8"][DAY]["run"] == 300 and res["per"]["AOI-8"][DAY]["rescan"] == 0
    assert res["per"]["AOI-9"][DAY]["run"] == 300 and res["per"]["AOI-9"][DAY]["rescan"] == 300
    a = att(res, "AOI-9", "W1")
    assert a["rel"] == "CROSS_DEVICE_RESCAN" and a["disp"] == "RESCAN" and a["prior"]["dev"] == "AOI-8"
    assert att(res, "AOI-8", "W1")["disp"] == "RUN"


def test_t05_cross_device_after_error_keeps_the_error_and_does_not_use_it_as_recovery():
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Scan Error."), w("AOI-8", "W2", "12:00", "12:05"),
               w("AOI-9", "W1", "10:00", "10:05")])
    m8 = res["per"]["AOI-8"][DAY]
    assert m8["nErr"] == 1 and m8["err"] == 300
    assert m8["stop"] == (12 * 3600) - (9 * 3600 + 300)     # 정지(추정)는 **같은 장비**의 다음 Wafer(12:00)까지 — 9호기 시각으로 끊지 않는다
    assert res["per"]["AOI-9"][DAY]["rescan"] == 300
    assert att(res, "AOI-9", "W1")["rel"] == "CROSS_DEVICE_RESCAN"


def test_t06_cross_device_error_after_error_is_still_an_error():
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Scan Error."), w("AOI-9", "W1", "10:00", "10:05", status="Alignment Error.")])
    a = att(res, "AOI-9", "W1")
    assert a["disp"] == "ERROR" and a["rel"] == "CROSS_DEVICE_RESCAN"     # 대표는 Error, 관계는 보조로
    assert res["per"]["AOI-9"][DAY]["run"] == 0 and res["per"]["AOI-9"][DAY]["nErr"] == 1


# ── T07: 같은 장비 Error 뒤 복구 = 재스캔(중복스캔과 구분) ────────────────────────────────────
def test_t07_same_device_recovery_after_error_is_rescan_not_duplicate():
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Scan Error."), w("AOI-8", "W1", "09:10", "09:15")])
    a = att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:10_BatchReport.htm")
    assert a["rel"] == "SAME_DEVICE_RESCAN" and a["disp"] == "RESCAN"
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 1 and m["err"] == 300 and m["rescan"] == 300 and m["dup"] == 0


# ── T08: 60초 안의 경계도 시도 구분 유지(LOT_GAP_SEC 는 반복 판정 기준이 아니다) ──────────────
def test_t08_repeat_within_60_seconds_is_still_a_separate_attempt():
    res = run([w("AOI-8", "W1", "09:00:00", "09:05:00"), w("AOI-8", "W1", "09:05:10", "09:10:00")])
    assert att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:05:10_BatchReport.htm")["disp"] == "DUP"
    assert res["per"]["AOI-8"][DAY]["run"] == 590


# ── T09·T10: Wafer ID 만 같음 / Lot 만 같음 → 연결하지 않는다 ────────────────────────────────
def test_t09_same_wafer_id_but_different_lot_is_not_linked():
    res = run([w("AOI-8", "W1", "09:00", "09:05", lot="LOT-A"), w("AOI-9", "W1", "10:00", "10:05", lot="LOT-B")])
    assert att(res, "AOI-9", "W1")["rel"] == "FIRST_OBSERVED" and res["per"]["AOI-9"][DAY]["rescan"] == 0


def test_t10_same_lot_but_different_wafer_is_not_linked():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-8", "W2", "09:06", "09:11")])
    assert res["per"]["AOI-8"][DAY]["dup"] == 0 and all(a["rel"] == "FIRST_OBSERVED" for a in res["attempts"])


# ── T11: 자리표시·batch 행은 자재 후보가 아니다(실패 배치 1건 집계는 유지) ───────────────────
def test_t11_placeholders_and_batch_rows_are_not_material_candidates():
    rows = [w("AOI-8", "Slot 3", "09:00", "09:05", lot="LoadPort A", status="Skipped.", ini_match="NO_WAFER_ID"),
            w("AOI-8", "Slot 3", "10:00", "10:05", lot="LoadPort A", status="Skipped.", ini_match="NO_WAFER_ID"),
            w("AOI-8", "", "11:00", "11:02", lot="LOT-A", status="Alignment Error.", kind="batch", ini_match="BATCH")]
    res = run(rows)
    assert res["attempts"] == []
    assert res["per"]["AOI-8"][DAY]["nErr"] == 1                       # 배치 1건


# ── T12·T13: 앞선 시도가 STALE(시간 없음) — 관계는 붙이되 시간은 지어내지 않는다 ─────────────
def test_t12_stale_prior_gives_relation_but_no_time():
    stale = {"device": "AOI-8", "lot": "LOT-A", "wafer_id": "W1", "status": "Pass", "recipe": "R1", "job": "J1", "wafer_start_time": "", "wafer_end_time": "",
             "batch_start": f"{DAY}T08:00:00", "batch_end": f"{DAY}T08:30:00", "report": "old.htm", "ini_match": "STALE"}
    res = run([stale, w("AOI-9", "W1", "10:00", "10:05")])
    a = att(res, "AOI-9", "W1")
    assert a["rel"] == "CROSS_DEVICE_RESCAN" and a["prior"]["dev"] == "AOI-8"
    assert "시각 미확인" in a["why"]
    assert res["per"]["AOI-8"][DAY]["run"] == 0 and res["per"]["AOI-8"][DAY]["hasData"] is False   # Batch 구간을 가동으로 더하지 않는다


# ── T14: 겹침·같은 시작 → 보류 ───────────────────────────────────────────────────────────────
def test_t14_overlapping_or_same_start_attempts_are_unresolved():
    res = run([w("AOI-8", "W1", "09:00", "09:10"), w("AOI-9", "W1", "09:05", "09:15")])
    a = att(res, "AOI-9", "W1")
    assert a["rel"] == "UNRESOLVED" and a["conf"] == "unresolved" and a["disp"] == "RUN"
    assert res["index"]["unresolved"] == 1 and res["per"]["AOI-9"][DAY]["rescan"] == 0
    res2 = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-9", "W1", "09:00", "09:05")])
    assert sum(1 for a in res2["attempts"] if a["rel"] == "UNRESOLVED") == 1


# ── T15: 날짜 경계를 넘는 전역 이력 ─────────────────────────────────────────────────────────
def test_t15_relation_crosses_midnight_and_days_split_time_only():
    res = run([w("AOI-8", "W1", "23:50", "23:59", day="2026-09-14"), w("AOI-9", "W1", "00:10", "00:15", day="2026-09-15")])
    assert att(res, "AOI-9", "W1")["rel"] == "CROSS_DEVICE_RESCAN"
    assert res["per"]["AOI-8"]["2026-09-14"]["run"] == 540 and res["per"]["AOI-9"]["2026-09-15"]["rescan"] == 300


# ── T16·T37: 입력 순서를 바꿔도 같은 판정 ───────────────────────────────────────────────────
def test_t37_row_order_does_not_change_classification():
    rows = [w("AOI-8", "W1", "09:00", "09:05", status="Scan Error."), w("AOI-9", "W1", "10:00", "10:05"),
            w("AOI-8", "W2", "11:00", "11:05"), w("AOI-8", "W2", "11:06", "11:11"), w("AOI-8", "W3", "12:00", "12:05", lot="LOT-A TEST")]
    a = run(rows); b = run(list(reversed(rows)))
    key = lambda r: {(x["dev"], x["wafer"], x["report"]): (x["rel"], x["disp"], x["conf"]) for x in r["attempts"]}
    assert key(a) == key(b)
    assert a["per"] == b["per"]


# ── T17: 첫 기록은 '확인된 첫 기록' — 최초라고 단정하지 않는다 ───────────────────────────────
def test_t17_first_record_is_labelled_as_first_observed():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-8", "W1", "10:00", "10:05")])
    assert att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:00_BatchReport.htm")["why"] == "이 자재의 확인된 첫 기록"


# ── T18: 토큰 경계 — TEST 는 분모 포함·분자 제외, RE 표기는 재스캔, RETURN/TESTER 는 정상 ──────
def test_t18_tokens_keep_exact_boundaries_and_test_is_out_of_the_numerator():
    res = run([w("AOI-8", "W1", "09:00", "09:05", lot="LOT-A TEST", scan_type="TEST"),
               w("AOI-8", "W2", "10:00", "10:05", lot="LOT-A RETURN"), w("AOI-8", "W3", "11:00", "11:05", lot="TESTER-1"),
               w("AOI-8", "W4", "12:00", "12:05", lot="LOT-A RE", scan_type="RESCAN")])
    m = res["per"]["AOI-8"][DAY]
    assert m["test"] == 300 and m["run"] == 900 and m["denom"] == 86400 and m["nTest"] == 1
    assert att(res, "AOI-8", "W4")["rel"] == "TOKEN_RESCAN" and att(res, "AOI-8", "W4")["disp"] == "RESCAN"
    assert att(res, "AOI-8", "W2")["disp"] == "RUN" and att(res, "AOI-8", "W3")["disp"] == "RUN"


# ── T19: Rework + 다른 장비 재스캔 → 대표 재스캔, 시간 한 번 ───────────────────────────────
def test_t19_rework_that_is_also_a_cross_device_rescan_counts_once():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-9", "W1", "10:00", "10:05", lot="LOT-A REWORK", scan_type="REWORK")])
    m = res["per"]["AOI-9"][DAY]
    assert att(res, "AOI-9", "W1")["disp"] == "RESCAN"
    assert m["rescan"] == 300 and m["rework"] == 0 and m["run"] == 300


# ── T20·T21: 겹치는 구간은 합집합, 충돌은 숨기지 않는다 ──────────────────────────────────────
def test_t20_overlapping_intervals_on_one_device_are_unioned():
    res = run([w("AOI-8", "W1", "09:00", "09:10"), w("AOI-8", "W2", "09:05", "09:15")])
    m = res["per"]["AOI-8"][DAY]
    assert m["run"] == 900 and m["overlap"] == 300 and m["off"] == 86400 - 900
    assert abs(m["run"] + m["err"] + m["stop"] + m["test"] + m["off"] - m["denom"]) < 1e-6


def test_t21_error_and_run_conflict_is_assigned_once_by_priority():
    res = run([w("AOI-8", "W1", "09:00", "09:10", status="Scan Error."), w("AOI-8", "W2", "09:05", "09:15")])
    m = res["per"]["AOI-8"][DAY]
    assert m["err"] == 600 and m["run"] == 300 and m["overlap"] == 300 and m["stop"] == 0
    assert m["run"] + m["err"] + m["stop"] + m["off"] == m["denom"]


# ── T22: 자정을 넘는 Error — 시간은 나누고 건수는 시작일 한 번 ──────────────────────────────
def test_t22_error_over_midnight_is_counted_once_on_its_start_day():
    rows = [{**w("AOI-8", "W1", "23:50", "23:55", status="Scan Error.", day="2026-09-14"), "wafer_end_time": "2026-09-15T00:05:00"},
            w("AOI-8", "W2", "01:00", "01:05", day="2026-09-15")]
    res = run(rows)
    d1, d2 = res["per"]["AOI-8"]["2026-09-14"], res["per"]["AOI-8"]["2026-09-15"]
    assert d1["nErr"] == 1 and d2["nErr"] == 0
    assert d1["err"] == 600 and d2["err"] == 300
    assert d2["stop"] == 55 * 60                                          # 00:05 → 01:00


# ── T23: 복구 기록 없는 마지막 Error — 관측 종료까지만 추정 ─────────────────────────────────
def test_t23_open_ended_stop_runs_only_to_the_observation_end():
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Scan Error."), w("AOI-9", "W9", "10:00", "10:30")])
    m = res["per"]["AOI-8"][DAY]
    assert m["stop"] == (10 * 3600 + 1800) - (9 * 3600 + 300)             # 09:05 → 10:30(다른 장비까지 포함한 마지막 기록)
    assert "2026-09-16" not in res["per"]["AOI-8"]                          # 다음 날로 정지를 늘리지 않는다


# ── T24: 오늘 — 장비마다 분모가 달라도 평균 기준 %p 합 = 100 − 평균 ─────────────────────────
def test_t24_loss_pp_sum_equals_100_minus_average_even_when_denominators_differ():
    res = run([w("AOI-8", "W1", "09:00", "10:00"), w("AOI-9", "W2", "08:00", "08:30"), w("AOI-9", "W2", "08:40", "08:45", status="Scan Error.")], today=DAY)
    L = res["loss"][0]
    assert abs(L["ppSum"] + L["util"] - 100) < 1e-6
    assert res["per"]["AOI-8"][DAY]["denom"] == 10 * 3600 and res["per"]["AOI-9"][DAY]["denom"] == 8 * 3600 + 45 * 60
    assert res["fleet"]["util"] != res["fleet"]["sumUtil"]                 # 산술평균과 합산 시간 기준은 다르다


# ── T25: 가동 없는 날·Test 만 있는 날·분모 0 — NaN/Infinity 없음 ────────────────────────────
def test_t25_no_nan_for_test_only_days_and_empty_devices():
    res = run([w("AOI-8", "W1", "09:00", "09:05", lot="X TEST", scan_type="TEST"), w("AOI-9", "W2", "09:00", "09:05", status="Alignment Error.", kind="batch", ini_match="BATCH")])
    m8, m9 = res["per"]["AOI-8"][DAY], res["per"]["AOI-9"][DAY]
    assert m8["hasData"] is True and m8["util"] == 0 and m8["test"] == 300
    assert m9["nErr"] == 1 and m9["util"] == 0
    assert json.dumps(res).count("NaN") == 0 and "Infinity" not in json.dumps(res)


# ── 실물 근거(AOI-3 `BS` / AOI-16 `BS_1`): Job 이 같으면 Recipe 가 달라도 같은 공정 — 검토 배지만(D36) ──
def test_recipe_mismatch_with_the_same_job_is_confirmed_with_a_review_badge():
    res = run([w("AOI-3", "GX1", "09:00", "09:05", lot="PHF", recipe="BS"), w("AOI-16", "GX1", "10:00", "10:05", lot="PHF", recipe="BS_1")])
    a = att(res, "AOI-16", "GX1")
    assert a["rel"] == "CROSS_DEVICE_RESCAN" and a["conf"] == "confirmed" and a["disp"] == "RESCAN" and a["recipeDiff"] is True


# ── 라벨만 바뀌어도 총 가동시간은 불변(중복스캔·재스캔은 가동의 부분집합) ───────────────────
def test_repeat_time_is_a_subset_of_run_time_and_never_a_loss():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-8", "W1", "09:06", "09:11"), w("AOI-9", "W1", "12:00", "12:05")])
    for dev in ("AOI-8", "AOI-9"):
        m = res["per"][dev][DAY]
        assert m["dup"] + m["rescan"] + m["rework"] <= m["run"]
        assert m["run"] + m["err"] + m["stop"] + m["test"] + m["off"] == m["denom"]
    L = res["loss"][0]
    assert [r[0] for r in L["rows"]] == ["err", "stop", "testRun", "off"]   # 반복 가동·가동 중단은 저하 사유가 아니다


# ── 중단(Abort) — 사용자 확정 D41(D35 개정): 같은 Report 에 정상 스캔이 없을 때만 Error ────────────
def test_abort_in_a_report_without_any_pass_is_an_error_like_any_other():
    """`Aborted.` 인데 그 Report 에 PASS 가 하나도 없다 → Error 와 똑같이: 건수 · 빨간 막대 · 그 뒤 정지(추정)."""
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Aborted.", report="a.htm"), w("AOI-8", "W2", "12:00", "12:05", report="b.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 1 and m["err"] == 300 and m["nAbort"] == 1 and m["nAbortErr"] == 1
    assert m["stop"] == (12 * 3600) - (9 * 3600 + 300)                  # 그 뒤 공백은 정지(추정)
    assert m["run"] == 300 and m["abort"] == 0
    assert m["run"] + m["err"] + m["stop"] + m["test"] + m["off"] == m["denom"]
    assert att(res, "AOI-8", "W1")["disp"] == "ERROR"


def test_abort_in_a_report_with_a_pass_counts_as_running_time():
    """정상 스캔 뒤의 중단은 정상 스캔 시간으로(사용자: '정상 스캔 뒤에 aborted 는 정상 스캔 시간으로 두자')."""
    res = run([w("AOI-8", "W1", "09:00", "09:05", report="a.htm"), w("AOI-8", "W2", "09:06", "09:11", status="Aborted.", report="a.htm"),
               w("AOI-8", "W3", "12:00", "12:05", report="b.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 0 and m["err"] == 0 and m["stop"] == 0
    assert m["nAbort"] == 1 and m["nAbortErr"] == 0 and m["abort"] == 300      # 가동 중단 — run 의 부분집합
    assert m["run"] == 900 and m["off"] == 86400 - 900
    assert att(res, "AOI-8", "W2")["disp"] == "ABORT"                          # 이름·색은 남는다


def test_report_pass_context_ignores_time_validity_and_row_order():
    """PASS 인데 시각이 없어도(STALE) PASS 다 — Report 문맥은 필터·시간 유효성 전 원천 전체에서 본다. 순서도 무관."""
    stale = {"device": "AOI-8", "lot": "LOT-A", "wafer_id": "W9", "status": "Pass", "recipe": "R1", "wafer_start_time": "", "wafer_end_time": "",
             "batch_start": f"{DAY}T08:00:00", "batch_end": f"{DAY}T08:30:00", "report": "a.htm", "ini_match": "STALE"}
    ab = w("AOI-8", "W1", "09:00", "09:05", status="Aborted.", report="a.htm")
    for rows in ([ab, stale], [stale, ab]):
        m = run(rows)["per"]["AOI-8"][DAY]
        assert m["nErr"] == 0 and m["abort"] == 300 and m["run"] == 300


def test_technical_cause_plus_abort_is_one_error_regardless_of_pass():
    res = run([w("AOI-8", "W1", "09:00", "09:05", report="a.htm"), w("AOI-8", "W2", "09:06", "09:11", status="Focus Mapping Error. Batch Aborted.", report="a.htm"),
               w("AOI-8", "W3", "09:12", "09:17", status="Failed to move wafer to station. Batch Aborted. Skipped.", report="a.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 2 and m["err"] == 600 and m["nAbort"] == 1 and m["nAbortErr"] == 1   # Focus Mapping 은 중단 결과 + 원인 → Error 한 번
    assert m["run"] == 300


def test_cancelled_and_dash_are_unclassified_not_error_not_running():
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Cancelled", report="a.htm"), w("AOI-8", "W2", "10:00", "10:05", status="-", report="a.htm"),
               w("AOI-8", "W3", "11:00", "11:05", status="Skipped.", report="b.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 0 and m["nAbort"] == 0 and m["run"] == 0 and m["nUnk"] == 3 and m["unk"] == 900
    assert m["off"] == 86400 and m["hasData"] is True                      # 미가동(사유 미확인)에 남고, 기록이 없는 날은 아니다
    assert m["run"] + m["err"] + m["stop"] + m["test"] + m["off"] == m["denom"]
    assert all(a["disp"] == "UNK" for a in res["attempts"])


def test_user_abort_follows_the_same_rule_and_wafer_lost_is_always_an_error():
    """★ 반송 실패는 문구가 `… Batch Aborted. Skipped.` 로 끝난다 — 원인이 있어 PASS 유무와 무관하게 Error."""
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Aborted. Wafer aborted by user.", report="a.htm"),
               w("AOI-8", "W2", "10:00", "10:05", status="Failed to move wafer to station. Batch Aborted. Skipped.", report="b.htm"),
               w("AOI-8", "W3", "10:10", "10:15", report="b.htm")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 2 and m["nAbort"] == 1 and m["nAbortErr"] == 1     # 사용자 중단(PASS 없는 Report) 1 + 반송 실패 1


def test_an_attempt_after_an_abort_is_a_rescan_not_a_duplicate():
    """앞선 시도가 끝나지 못했으면(Error 또는 중단) 다시 돌린 것은 중복스캔이 아니라 재스캔이다."""
    res = run([w("AOI-8", "W1", "09:00", "09:05", status="Aborted."), w("AOI-8", "W1", "09:10", "09:15")])
    a = att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:10_BatchReport.htm")
    assert a["rel"] == "SAME_DEVICE_RESCAN" and a["disp"] == "RESCAN"
    assert res["per"]["AOI-8"][DAY]["rescan"] == 300


def test_abort_is_a_loss_reason_only_when_it_is_an_error():
    L = run([w("AOI-8", "W1", "09:00", "09:05", status="Aborted.")])["loss"][0]
    assert [r[0] for r in L["rows"]] == ["err", "stop", "testRun", "off"]       # 가동 중단은 저하 사유가 아니다(부분집합)
    assert dict((r[0], r[1]) for r in L["rows"])["err"] == 300
    assert abs(L["ppSum"] + L["util"] - 100) < 1e-6                              # 사유 %p 합은 여전히 100 − 평균


def test_batch_level_abort_is_an_error_with_batch_time():
    """통째로 중단된 배치(kind=batch)에는 정상 스캔이 없으므로 Error 다(D05 의 '시간은 세고 분자에서 제외' 그대로)."""
    res = run([w("AOI-8", "", "11:00", "11:02", lot="LOT-A", status="Aborted.", kind="batch", ini_match="BATCH")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 1 and m["err"] == 120 and m["nAbort"] == 1 and m["nAbortErr"] == 1 and m["run"] == 0


# ── D37: 같은 INI 시각을 두 Report 가 참조 — 시간의 주인은 엄격히 포함하는 Report 하나 ─────────
def _pair(order="err_first"):
    """실물(AOI-1 LVG/GWAYS13-C7 9/16)을 본뜬 fixture: Error Report 의 Batch 23:05~23:15 는 INI 시각(23:20~23:24)을 담지 않고(±10분 여유로만),
    뒤의 Pass Report 의 Batch 23:19~23:24 가 엄격히 담는다."""
    err = {"device": "AOI-1", "lot": "LVG", "wafer_id": "GWAYS13-C7", "status": "Alignment Error.", "recipe": "R1", "job": "J1", "report": "err.htm",
           "wafer_start_time": f"{DAY}T23:20:16", "wafer_end_time": f"{DAY}T23:24:12", "batch_start": f"{DAY}T23:05:20", "batch_end": f"{DAY}T23:15:38", "ini_match": "EXACT"}
    ok = {"device": "AOI-1", "lot": "LVG", "wafer_id": "GWAYS13-C7", "status": "Pass", "recipe": "R1", "job": "J1", "report": "pass.htm",
          "wafer_start_time": f"{DAY}T23:20:16", "wafer_end_time": f"{DAY}T23:24:12", "batch_start": f"{DAY}T23:19:27", "batch_end": f"{DAY}T23:24:37", "ini_match": "EXACT"}
    later = w("AOI-1", "OTHER", "23:40", "23:45", lot="LVG", report="later.htm")
    return [err, ok, later] if order == "err_first" else [later, ok, err]


@pytest.mark.parametrize("order", ["err_first", "pass_first"])
def test_strict_container_owns_the_time_and_the_error_stays_as_an_untimed_event(order):
    res = run(_pair(order))
    m = res["per"]["AOI-1"][DAY]
    assert m["run"] == 236 + 300                                              # 23:20:16→23:24:12 = 236초 가동 + 23:40→23:45
    assert m["err"] == 0 and m["stop"] == 0                                   # Error 구간·정지(추정)로 칠하지 않는다
    assert m["nErr"] == 1                                                     # Error 는 건수로 남는다(시간 미확인)
    a_ok = att(res, "AOI-1", "GWAYS13-C7", "pass.htm"); a_err = att(res, "AOI-1", "GWAYS13-C7", "err.htm")
    assert a_ok["timed"] and a_ok["own"] == "OWNED" and a_ok["basis"] == "STRICT_IN_BATCH"
    assert not a_err["timed"] and a_err["own"] == "NOT_OWNER" and a_err["basis"] == "TOLERANCE_ONLY"
    assert a_ok["rel"] == "SAME_DEVICE_RESCAN" and a_ok["disp"] == "RESCAN"    # 같은 장비 Error 뒤 복구 = 재스캔 (앞선 시도는 Batch 근거)
    assert a_err["s"] < a_ok["s"]


def test_ownership_result_does_not_depend_on_row_order():
    a, b = run(_pair("err_first")), run(_pair("pass_first"))
    assert a["per"] == b["per"]
    key = lambda r: {(x["dev"], x["wafer"], x["report"]): (x["rel"], x["disp"], x["own"], x["timed"]) for x in r["attempts"]}
    assert key(a) == key(b)


def test_zero_or_two_strict_containers_keeps_the_old_merge_and_marks_it_ambiguous():
    """엄격 포함 Report 가 하나가 아니면 소유권 보류 — 예전처럼 시간을 한 번만 세고 대표 행은 결정적으로(Error 먼저)."""
    both = [w("AOI-8", "W1", "09:00", "09:05", report="a.htm"), w("AOI-8", "W1", "09:00", "09:05", status="Scan Error.", report="b.htm")]
    for rows in (both, list(reversed(both))):
        res = run(rows)
        m = res["per"]["AOI-8"][DAY]
        assert m["err"] == 300 and m["run"] == 0 and m["nErr"] == 1 and len(res["attempts"]) == 1
        assert res["attempts"][0]["refs"] == 2 and res["attempts"][0]["own"] == "AMBIGUOUS" and res["attempts"][0]["status"] == "Scan Error."
    assert res["quality"]["ambiguous"] == 1 and res["quality"]["notOwner"] == 0


def test_duplicate_rows_inside_the_owner_report_still_give_one_owner():
    rows = _pair("err_first"); rows.insert(2, dict(rows[1]))                  # Pass Report 의 같은 행이 두 번
    res = run(rows)
    a_ok = att(res, "AOI-1", "GWAYS13-C7", "pass.htm")
    assert a_ok["own"] == "OWNED" and a_ok["rawDups"] == 2 and res["per"]["AOI-1"][DAY]["run"] == 236 + 300
    assert res["quality"]["notOwner"] == 1


def test_single_report_with_tolerance_only_time_still_uses_the_time():
    """경쟁 Report 가 없으면 여유 안의 시각은 지금처럼 쓴다(BATCH_WINDOW_MARGIN_SEC 는 그대로 600)."""
    r = _pair("err_first")[0]
    res = run([r])
    assert res["per"]["AOI-1"][DAY]["err"] == 236 and att(res, "AOI-1", "GWAYS13-C7")["basis"] == "TOLERANCE_ONLY"


# ── D38: 일부 성공한 배치의 Slot Error — 옛 payload 도 화면이 같은 규칙으로 합성한다 ──────────
def _slot_rows():
    ph = lambda wid, st: {"device": "AOI-8", "lot": "LoadPort A", "wafer_id": wid, "status": st, "recipe": "R1", "report": "p.htm",
                          "wafer_start_time": "", "wafer_end_time": "", "batch_start": f"{DAY}T09:00:00", "batch_end": f"{DAY}T09:30:00", "ini_match": "NO_WAFER_ID"}
    return [w("AOI-8", "W1", "09:05", "09:10", report="p.htm"), ph("Slot 2", "Failed to read wafer id on PAL"), ph("Slot 3", "Failed to read wafer id on PAL"),
            ph("Slot 3", "Failed to read wafer id on PAL"), ph("Slot 4", "Skipped."), w("AOI-8", "W5", "12:00", "12:05", report="q.htm")]


def test_slot_errors_in_a_partial_batch_are_one_untimed_event_not_per_row():
    res = run(_slot_rows())
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 1 and m["err"] == 0 and m["stop"] == 0        # Report 당 1건 · 시간 0 기여 · 정지(추정) 없음
    assert m["run"] == 600 and m["nWafer"] == 2                        # Wafer 시도 수에는 들어가지 않는다(자리표시)
    assert res["quality"] is not None


def test_slot_synthesis_is_idempotent_and_order_independent():
    rows = _slot_rows()
    a = run(rows); b = run(list(reversed(rows)))
    assert a["per"] == b["per"]
    existing = dict(rows[1]); existing.update({"kind": "slot", "lot": "LOT-A", "wafer_id": "", "ini_match": "BATCH_SLOT", "slots": "2"})
    c = run(rows + [existing])                                          # 이미 slot 행이 있는 새 payload → 지우고 다시 만들어 1건
    assert c["per"]["AOI-8"][DAY]["nErr"] == 1


def test_legacy_payload_without_batch_row_gets_one_from_the_same_rule():
    """D43 전 규칙으로는 '건너뜀' 뿐이라 batch 행이 없던 Report(ID 읽기 실패 후 Skipped) — 화면이 배치 1건으로 합성한다."""
    mk = lambda wid, st: {"device": "AOI-8", "lot": "LOT-A", "wafer_id": wid, "status": st, "recipe": "R1", "report": "old.htm",
                          "wafer_start_time": "", "wafer_end_time": "", "batch_start": f"{DAY}T09:00:00", "batch_end": f"{DAY}T09:30:00", "ini_match": "NOT_FOUND", "norm_status": "SKIPPED"}
    res = run([mk("W1", "Failed to read wafer id. Reading error = **. Wafer Skipped."), mk("W2", "Skipped.")])
    m = res["per"]["AOI-8"][DAY]
    assert m["nErr"] == 1 and m["err"] == 1800 and m["run"] == 0       # 배치 시각(D05)으로 Error 1건
    assert res["attempts"] == []                                        # 실패 배치의 자식 행은 자재 후보가 아니다


def test_no_slot_event_when_a_batch_row_exists():
    rows = [w("AOI-8", "", "11:00", "11:02", lot="LOT-A", status="Aborted.", kind="batch", ini_match="BATCH", report="b.htm"),
            {"device": "AOI-8", "lot": "LoadPort A", "wafer_id": "Slot 2", "status": "Failed to read wafer id on PAL", "recipe": "R1", "report": "b.htm",
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": f"{DAY}T11:00:00", "batch_end": f"{DAY}T11:02:00", "ini_match": "BATCH_FAILED"}]
    assert run(rows)["per"]["AOI-8"][DAY]["nErr"] == 1


# ── D36 · D39 · D42: 자재 키 정규화 · Job 원문 = 공정 · Rework+재스캔 · 사용자 override ─────────
def test_material_key_ignores_separators_and_case_but_keeps_digits_and_leading_zeros():
    res = run([w("AOI-8", "GX1", "09:00", "09:05", lot="SHX"), w("AOI-9", "gx-1", "10:00", "10:05", lot="SHX-RE", scan_type="RESCAN"),
               w("AOI-8", "W2", "11:00", "11:05", lot="GUH-SPT2"), w("AOI-9", "W2", "12:00", "12:05", lot="GUH_SPT2"),
               w("AOI-8", "W3", "13:00", "13:05", lot="FHP-PI3 ENHANCED"), w("AOI-9", "W3", "14:00", "14:05", lot="FHP-PI3 Enhanced"),
               w("AOI-8", "0831", "15:00", "15:05", lot="KDG-Rework-0831", scan_type="REWORK"), w("AOI-8", "831", "16:00", "16:05", lot="KDG")])
    assert att(res, "AOI-9", "gx-1")["rel"] == "CROSS_DEVICE_RESCAN"           # SHX · SHX-RE, GX1 · gx-1
    assert att(res, "AOI-9", "W2")["rel"] == "CROSS_DEVICE_RESCAN"             # GUH-SPT2 · GUH_SPT2
    assert att(res, "AOI-9", "W3")["rel"] == "CROSS_DEVICE_RESCAN"             # 대소문자
    assert att(res, "AOI-8", "0831")["rel"] == "FIRST_OBSERVED" and att(res, "AOI-8", "831")["rel"] == "FIRST_OBSERVED"   # 0831 은 남고 0831≠831
    assert att(res, "AOI-8", "0831")["mk"] == '["KDG0831","0831"]'


def test_process_identity_is_the_raw_job_and_a_b_a_compares_with_the_earlier_a():
    rows = [w("AOI-8", "W1", "09:00", "09:05", job="INCI-(6000)"), w("AOI-9", "W1", "10:00", "10:05", job="2D@RE-(6412)"),
            w("AOI-8", "W1", "11:00", "11:05", job="INCI-(6000)", report="a2.htm")]
    res = run(rows)
    assert att(res, "AOI-9", "W1")["rel"] == "FIRST_OBSERVED"                  # 다른 Job = 다음 공정 단계, 재스캔이 아니다
    a3 = att(res, "AOI-8", "W1", "a2.htm")
    assert a3["rel"] == "SAME_DEVICE_REPEAT" and a3["prior"]["s"] == att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:00_BatchReport.htm")["s"]   # A→B→A
    assert att(res, "AOI-9", "W1")["of"] == 3                                  # 자재 이력에는 세 시도가 전부 남는다


def test_job_names_are_compared_verbatim_and_empty_jobs_never_link():
    res = run([w("AOI-8", "W1", "09:00", "09:05", job="Job A"), w("AOI-8", "W1", "10:00", "10:05", job="job a"), w("AOI-8", "W1", "11:00", "11:05", job="Job A ")])
    assert all(a["rel"] == "FIRST_OBSERVED" for a in res["attempts"])          # 대소문자·공백이 다르면 다른 공정(자동 병합 없음)
    res2 = run([w("AOI-8", "W1", "09:00", "09:05", job=""), w("AOI-8", "W1", "10:00", "10:05", job="")])
    assert all(a["rel"] == "FIRST_OBSERVED" for a in res2["attempts"]) and res2["index"]["noJob"] == 1


def test_five_day_gap_and_intervening_other_job_do_not_break_a_repeat():
    res = run([w("AOI-8", "W1", "09:00", "09:05", day="2026-09-10"), w("AOI-8", "W1", "12:00", "12:05", day="2026-09-12", job="OTHER"),
               w("AOI-8", "W1", "09:00", "09:05", day="2026-09-15")])
    assert att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:00_BatchReport.htm")["rel"] in ("FIRST_OBSERVED", "SAME_DEVICE_REPEAT")
    reps = [a for a in res["attempts"] if a["rel"] == "SAME_DEVICE_REPEAT"]
    assert len(reps) == 1 and reps[0]["s"] > att(res, "AOI-8", "W1", "AOI-8_LOT-A_12:00_BatchReport.htm")["s"]


def test_rework_rescan_shows_rescan_colour_with_rework_badge_and_different_wafers_stay_rework():
    res = run([w("AOI-8", "W1", "09:00", "09:05"), w("AOI-9", "W1", "10:00", "10:05", lot="LOT-A REWORK", scan_type="REWORK"),
               w("AOI-9", "W2", "11:00", "11:05", lot="LOT-A REWORK", scan_type="REWORK")])
    assert att(res, "AOI-9", "W1")["disp"] == "RESCAN" and att(res, "AOI-9", "W1")["rel"] == "CROSS_DEVICE_RESCAN"
    assert att(res, "AOI-9", "W2")["disp"] == "REWORK" and att(res, "AOI-9", "W2")["rel"] == "FIRST_OBSERVED"
    m = res["per"]["AOI-9"][DAY]
    assert m["rescan"] == 300 and m["rework"] == 300 and m["run"] == 600


def test_user_override_applies_only_to_the_exact_pair_and_moves_no_time():
    F = {"device": "AOI-11", "job": "2D@R2-W97253Z6B1K16_0860752PD-0A", "lot": "YCG-EDGE", "wafer_id": "GWM5K09-F4", "status": "Aborted.", "recipe": "2D_EDGE",
         "wafer_start_time": "25-Aug-26 12:13:54 PM", "wafer_end_time": "25-Aug-26 12:21:46 PM", "batch_start": "25-Aug-26 12:13:00 PM", "batch_end": "25-Aug-26 12:22:06 PM",
         "report": "2D@R2-W97253Z6B1K16_0860752PD-0A_6321_YCG-EDGE_26-Aug-25_(12.22.06)_BatchReport.htm", "ini_match": "EXACT"}
    T = {"device": "AOI-9", "job": "2D@R3-W97253Z6B1K16_0860752PD-0A", "lot": "YCG-EDGE", "wafer_id": "GWM5K09-F4", "status": "Aborted.", "recipe": "2D_EDGE",
         "wafer_start_time": "25-Aug-26 12:19:31 PM", "wafer_end_time": "25-Aug-26 12:23:26 PM", "batch_start": "25-Aug-26 12:19:00 PM", "batch_end": "25-Aug-26 12:24:29 PM",
         "report": "2D@R3-W97253Z6B1K16_0860752PD-0A_6322_YCG-EDGE_26-Aug-25_(12.24.29)_BatchReport.htm", "ini_match": "EXACT"}
    other = dict(T, wafer_id="GWM5K08-D1", report="x.htm")                      # 같은 날 다른 시도(보류 대상) — 번지지 않는다
    res = run([F, T, other])
    a = att(res, "AOI-9", "GWM5K09-F4")
    assert a["rel"] == "CROSS_DEVICE_RESCAN" and a["conf"] == "user_confirmed" and a["override"] == "D36-override-1" and a["prior"]["dev"] == "AOI-11"
    assert "시각 충돌 135초" in a["why"]
    assert att(res, "AOI-9", "GWM5K08-D1")["rel"] == "FIRST_OBSERVED"
    assert res["index"]["overrides"] == [{"id": "D36-override-1", "applied": True}]
    d = "2026-08-25"
    m9 = res["per"]["AOI-9"][d]
    assert res["per"]["AOI-11"][d]["err"] == 472 and m9["err"] == 235 and m9["overlap"] == 235   # 원시 시각·시간은 그대로(같은 시각의 두 Error 는 한 번, 충돌은 overlap 에)
    res2 = run([F, dict(T, wafer_start_time="25-Aug-26 12:19:32 PM")])         # 한 글자라도 다르면 미적용(경고만)
    assert res2["index"]["overrides"][0]["applied"] is False and att(res2, "AOI-9", "GWM5K09-F4")["rel"] == "FIRST_OBSERVED"


def test_lot_bars_and_time_ownership_are_unchanged_by_material_normalisation():
    """정규화는 이력 연결에만 쓴다 — Lot 막대(원문)·시간은 그대로다."""
    res = run([w("AOI-8", "W1", "09:00", "09:05", lot="TTP DIA"), w("AOI-8", "W1", "09:06", "09:11", lot="TTP-DIA")])
    m = res["per"]["AOI-8"][DAY]
    assert m["run"] == 600 and att(res, "AOI-8", "W1", "AOI-8_LOT-A_09:06_BatchReport.htm".replace("LOT-A", "TTP-DIA"))["rel"] == "SAME_DEVICE_REPEAT"
    assert len({i["lot"] for i in m["items"]}) == 2                             # 막대(원문 Lot)는 둘


def test_material_normalisation_matches_python_fixture():
    from aoi_capacity import collect
    cases = [("SHX-RE", "GX1"), ("GUH_SPT2", "gx-1"), ("GPT 3D", "00NSP049XYG7"), ("KDG-Rework-0831", "0831"), ("LVT RETURN 3D FVI MERGE", "W"),
             ("REX", "W"), ("TESTER-1", "W"), ("UHV RW 0911 #01", "W"), ("GAS-RE#1", "W"), ("자재-RE", "웨이퍼 1"), ("", ""), ("A+B,C'D%E.F~G", "x_y-z")]
    out = subprocess.run([NODE, str(HARNESS)], input=json.dumps({"material": [{"lot": l, "wafer_id": w_} for l, w_ in cases]}),
                         capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    for (l, w_), j in zip(cases, json.loads(out.stdout)):
        assert j["key"] == collect.material_key(l, w_), (l, w_)
        assert j["lot_norm"] == collect.norm_lot(l) and j["wafer_norm"] == collect.norm_wafer(w_)
        assert j["scan_type"] == collect.scan_type(l), l


# ── D40: 화면의 '오늘' 은 수집 시각 — 열람 날짜·시간대를 바꿔도 같은 집계 ───────────────────────
def run_meta(rows, meta, viewer_now, tz="Asia/Seoul"):
    import os
    out = subprocess.run([NODE, str(HARNESS)], input=json.dumps({"rows": rows, "meta": meta, "viewer_now": viewer_now}),
                         capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=dict(os.environ, TZ=tz))
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_metrics_reference_is_the_collection_time_not_the_viewer_clock():
    rows = [w("AOI-8", "W1", "09:00", "10:00"), w("AOI-9", "W2", "08:00", "08:30")]
    meta = {"generated_iso": f"{DAY}T12:59:17", "mode": "gui"}
    a = run_meta(rows, meta, f"{DAY}T13:00:00")                                # 수집 직후
    b = run_meta(rows, meta, "2026-09-25T09:00:00")                            # 일주일 뒤에 열어도
    c = run_meta(rows, meta, "2026-09-25T09:00:00", tz="UTC")                  # 다른 시간대의 PC 에서도
    strip = lambda res: {d: {k: {x: v for x, v in m.items() if x != "items"} for k, m in days.items()} for d, days in res["per"].items()}   # items 의 epoch ms 는 시간대마다 다르다(같은 민간시각)
    assert a["today"] == DAY and strip(a) == strip(b) == strip(c) and a["fleet"] == b["fleet"] == c["fleet"]
    assert a["per"]["AOI-8"][DAY]["denom"] == 10 * 3600 and a["per"]["AOI-9"][DAY]["denom"] == 8 * 3600 + 1800   # 오늘 = 수집일: 마지막 스캔까지


def test_without_generated_iso_the_viewer_clock_is_the_fallback():
    rows = [w("AOI-8", "W1", "09:00", "10:00")]
    a = run_meta(rows, {"mode": "saved"}, f"{DAY}T12:00:00")
    b = run_meta(rows, {"mode": "saved"}, "2026-09-25T09:00:00")
    assert a["today"] == DAY and a["per"]["AOI-8"][DAY]["denom"] == 10 * 3600
    assert b["today"] == "2026-09-25" and b["per"]["AOI-8"][DAY]["denom"] == 86400   # 옛 파일은 예전처럼(비고정 배지)
