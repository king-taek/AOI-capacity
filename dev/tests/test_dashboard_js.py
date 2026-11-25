"""결과 화면(template.html)의 모델 `buildModel` 을 Node 에서 **실제로 실행**해 검사한다(dev/tests/js_harness.js).

두 프로필이 있다:
- product(기본, MODEL_VERSION 3): D56(측정 우선 배타 배정 · 배치 창 균등 배분 · Error 담은 Report 끝 뒤가 대기) · D57(수집일 분모 = 모든 장비의 마지막 기록) ·
  D58(시각 없는 Error = 배치 창의 빈 시간) · D63(Rescan = 앞선 PASS 만) · D64(Test Lot 전부 Test) · D04(자정 분할) · D09(엄격 날짜).
- legacy: make_aoi_data.js [원본] 이식 — 네 스위치를 끄면 디자인 스크립트와 같은 출력(slow 가드). 제품 화면은 쓰지 않는다.
네트워크·NAS·쓰기 없음. Node 가 없으면 skip.
"""
from __future__ import annotations

import datetime
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "dev" / "tests" / "js_harness.js"
DESIGN_SCRIPT = ROOT / "docs" / "design" / "dashboard-redesign" / "scripts" / "make_aoi_data.js"
SAMPLE = ROOT / "dev" / "samples" / "AOI_capacity_2026-09-18_30일치.html.gz"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(not NODE, reason="node 가 없는 환경")

DAY = "2026-09-18"
LEGACY_RULES = {"profile": "legacy", "waitToObsEnd": False, "denomToday": False, "abortIsError": False, "estimateFromBatch": False}


def meta(*devs, generated_iso=f"{DAY}T12:59:17", **extra):
    return {"generated": generated_iso[:16].replace("T", " "), "generated_iso": generated_iso,
            "mode": "auto", "scope": {"restricted": True, "devices": ["AOI-1", "AOI-2"]},
            "devices": [{"name": d, "note": f"X:\\{d}", "report_dir": "Report", "status": "ok"} for d in devs] + list(extra.get("more", []))}


def ts(day: str, hhmm: str) -> str:
    """'2026-09-18', '08:00' → '18-Sep-26 08:00:00 AM' (실장비 표기)."""
    y, m, d = day.split("-")
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m) - 1]
    h, mi = map(int, hhmm.split(":"))
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{int(d)}-{mon}-{y[2:]} {h12:02d}:{mi:02d}:00 {ap}"


def w(dev, wafer, s=None, e=None, *, lot="LOT-A", status="Pass", job="J1", report=None, day=DAY, bs=None, be=None, eday=None, setup="6321"):
    """Wafer 행 하나. s/e 는 'HH:MM'(없으면 시각 미확인), bs/be 는 배치 구간, eday 는 종료가 다음 날일 때.
    같은 장비·Job·Lot·날짜의 행은 같은 Report(= 한 배치) — 모델의 Lot 단위가 Report 이기 때문."""
    rep = report or f"{job}_{setup}_{lot}_{int(day[8:])}-Sep-26_(00.00.00)_BatchReport.htm"
    return {"device": dev, "kind": "", "job": job, "setup": setup, "lot": lot, "wafer_id": wafer, "status": status,
            "wafer_start_time": ts(day, s) if s else "", "wafer_end_time": ts(eday or day, e) if e else "",
            "batch_start": ts(day, bs) if bs else (ts(day, s) if s else ""), "batch_end": ts(eday or day, be) if be else (ts(eday or day, e) if e else ""),
            "report": rep, "ini_match": "EXACT" if s else "NOT_FOUND", "scan_type": "", "recipe": "", "data_issue": ""}


def run(rows, mt=None, rules=None):
    payload = {"rows": rows, "meta": mt or meta("AOI-1", "AOI-2")}
    if rules is not None:
        payload["rules"] = rules
    out = subprocess.run([NODE, str(HARNESS)], input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, timeout=120, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


def at(D, dev, day=DAY):
    return D["detail"][day][dev]


def busy(t):
    return t["r"] + t["d"] + t["t"] + t["x"] + t["s"]


# ── 0. legacy 프로필 = 디자인 스크립트 (slow) ───────────────────────────────
@pytest.mark.slow
def test_legacy_profile_equals_the_design_script_on_the_30_day_sample(tmp_path):
    """legacy 프로필(네 스위치 끔)은 make_aoi_data.js 와 장비-일 전부 같아야 한다 — 이식이 규칙을 새지 않았다는 근거. 제품 프로필의 정답이 아니다."""
    import sys
    sys.path.insert(0, str(ROOT / "dev" / "tests"))
    import sample_rows  # noqa: E402

    html = sample_rows.read_bytes(SAMPLE).decode("utf-8")
    emb = sample_rows.embedded(html)
    src = tmp_path / "in.html"
    src.write_text(html, encoding="utf-8")
    ref_path = tmp_path / "ref.json"
    subprocess.run([NODE, str(DESIGN_SCRIPT), str(src), str(ref_path)], check=True, capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    ref = json.loads(ref_path.read_text(encoding="utf-8"))
    mine = json.loads(subprocess.run([NODE, "--max-old-space-size=4096", str(HARNESS)], input=json.dumps({"embedded": emb, "rules": LEGACY_RULES}),
                                     capture_output=True, text=True, timeout=600, cwd=str(ROOT), check=True).stdout)
    assert mine["days"] == ref["days"] and mine["devices"] == ref["devices"]
    assert mine["pool"] == ref["pool"] and mine["jobG"] == ref["jobG"] and mine["jobGroups"] == ref["jobGroups"]
    bad = 0
    for dy, ds in ref["detail"].items():
        for dv, t in ds.items():
            m = dict(mine["detail"][dy][dv])
            m.pop("den", None)
            assert m.pop("we", 0) == 0 and m.pop("ne", 0) == 0
            if m != t:
                bad += 1
    assert bad == 0


# ── 1. 불변식 (30일치, slow) ────────────────────────────────────────────────
@pytest.mark.slow
def test_product_model_invariants_hold_on_the_30_day_sample():
    """★ 장비·날짜마다 Scan+Rescan+Test+Error+대기 ≤ 분모, seg 는 서로 겹치지 않고 1분 단위로 배타적이다(D56)."""
    import sys
    sys.path.insert(0, str(ROOT / "dev" / "tests"))
    import sample_rows  # noqa: E402

    emb = sample_rows.embedded(sample_rows.read_bytes(SAMPLE).decode("utf-8"))
    D = json.loads(subprocess.run([NODE, "--max-old-space-size=4096", str(HARNESS)], input=json.dumps({"embedded": emb}),
                                  capture_output=True, text=True, timeout=600, cwd=str(ROOT), check=True).stdout)
    assert D["badRows"] == 0 and D["days"][0] == "2026-08-19" and D["days"][-1] == "2026-09-18"
    n = 0
    for dy, ds in D["detail"].items():
        for dv, t in ds.items():
            n += 1
            assert busy(t) <= t["den"], (dv, dy, t)
            segs = sorted(t["seg"])
            assert sum(b - a for a, b, _ in segs) == busy(t), (dv, dy)
            for i in range(1, len(segs)):
                assert segs[i][0] >= segs[i - 1][1], (dv, dy, segs[i - 1], segs[i])
            assert t["e"] == sum(1 for L in t["lots"] for c, v in L[9].items() if v[0]), (dv, dy)
    assert n >= 800


# ── 2. D56-① 측정 우선 배타 배정 ────────────────────────────────────────────
def test_overlapping_measured_intervals_are_counted_once_with_error_first():
    rows = [w("AOI-1", "W1", "08:00", "09:00"), w("AOI-1", "W2", "08:10", "08:15", status="Alignment Error."),
            w("AOI-1", "W3", "08:20", "09:20", lot="LOT-B")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["s"]) == (75, 5, 0)                       # 80분 점유: Scan 75 + Error 5, Report 끝 뒤 B 가 이어져 대기 0
    assert sorted(t["seg"]) == [[480, 490, 0], [490, 495, 1], [495, 560, 0]]


def test_estimate_only_fills_minutes_no_measurement_claims():
    """추정(배치 창)은 측정 구간이 남긴 빈 분만 받는다."""
    rows = [w("AOI-1", "W1", bs="08:00", be="09:00"), w("AOI-1", "W2", "08:10", "08:15", status="Alignment Error.", bs="08:00", be="09:00"),
            w("AOI-1", "W3", "08:20", "09:20", lot="LOT-B")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["ne"]) == (75, 5, 1) and busy(t) == 80


# ── 3. D56-② 배치 창 나눠 갖기 · D63 Rescan ────────────────────────────────
def test_untimed_pass_rows_split_the_batch_window_equally_and_only_the_repeated_wafer_is_rescan():
    rep2 = "J1_6321_LOT-A_18-Sep-26_(09.00.00)_BatchReport.htm"
    rows = [w("AOI-1", "W1", "07:00", "07:10"),
            w("AOI-1", "W1", bs="08:00", be="09:00", report=rep2), w("AOI-1", "W2", bs="08:00", be="09:00", report=rep2)]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["d"], t["ne"]) == (40, 30, 2)                      # 10 + 30(W2) Scan · 30(W1) Rescan — 130 이 아니라 70
    assert sorted(t["seg"]) == [[420, 430, 0], [480, 510, 4], [510, 540, 0]]


def test_rescan_requires_the_previous_attempt_to_be_pass():
    rows = [w("AOI-1", "W1", status="Skipped.", bs="08:00", be="08:01"),
            w("AOI-1", "W1", "08:30", "08:40", report="J1_6321_LOT-A_18-Sep-26_(08.41.00)_BatchReport.htm")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["d"]) == (10, 0)                                    # Skipped 뒤 Pass 는 Scan(D63)
    rows2 = [w("AOI-1", "W1", "07:00", "07:10"), w("AOI-1", "W1", "08:30", "08:40", report="J1_6321_LOT-A_18-Sep-26_(08.41.00)_BatchReport.htm")]
    assert at(run(rows2), "AOI-1")["d"] == 10                            # Pass 뒤 Pass 는 Rescan
    rows3 = [w("AOI-2", "W1", "07:00", "07:10"), w("AOI-1", "W1", "08:30", "08:40")]
    assert at(run(rows3), "AOI-1")["d"] == 10                            # 장비 무관


def test_skipped_and_aborted_rows_take_no_time_unless_the_report_has_neither_pass_nor_cause():
    rows = [w("AOI-1", "W1", "08:00", "08:10"), w("AOI-1", "W2", status="Skipped.", bs="08:00", be="09:00"), w("AOI-1", "W3", status="Aborted.", bs="08:00", be="09:00")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["e"]) == (10, 0, 0)
    rows2 = [w("AOI-1", "W1", "08:00", "08:05", status="Aborted."), w("AOI-1", "W2", status="Skipped."), w("AOI-1", "W9", "10:00", "10:10", lot="LOT-B")]
    t2 = at(run(rows2), "AOI-1")
    assert (t2["x"], t2["s"], t2["e"], list(t2["ct"])) == (5, 115, 1, ["ABORTED"])   # D52: 중단만 남은 Report 는 Error + 뒤 대기


# ── 4. D56-③ Error 후 대기 = Error 담은 Report 끝 뒤 ────────────────────────
def test_wait_starts_after_the_error_report_ends_not_inside_it():
    rows = [w("AOI-1", "W1", bs="08:00", be="09:00"), w("AOI-1", "W2", "08:30", "08:33", status="Alignment Error.", bs="08:00", be="09:00"),
            w("AOI-1", "W3", "08:40", "09:00", bs="08:00", be="09:00"), w("AOI-2", "W9", "12:20", "12:30", lot="LOT-B")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["s"], t["den"]) == (57, 3, 210, 750)        # 08:33~08:40 은 스캔, 09:00 → 12:30 이 대기
    assert sorted(t["seg"]) == [[480, 510, 0], [510, 513, 1], [513, 540, 0], [540, 750, 3]] and t["we"] == 750
    assert busy(t) <= t["den"]


def test_wait_stops_at_the_next_activity_and_never_crosses_midnight():
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error."), w("AOI-1", "W2", "14:00", "14:10", lot="LOT-B")]
    assert at(run(rows), "AOI-1")["s"] == 357
    rows2 = [w("AOI-1", "W1", "20:00", "20:03", status="Alignment Error."), w("AOI-2", "W8", "01:00", "01:10", day="2026-09-19")]
    D = run(rows2)
    assert at(D, "AOI-1")["s"] == 237 and "AOI-1" not in D["detail"]["2026-09-19"]   # 자정까지, 다음 날로 늘리지 않음(D44)


# ── 5. D58 시각 없는 Error = 배치 창의 빈 시간 ──────────────────────────────
def test_an_untimed_error_takes_the_uncovered_minutes_of_its_batch_window():
    rows = [w("AOI-1", "W1", "09:00", "09:12", bs="09:00", be="09:40"), w("AOI-1", "W2", status="Scan 2D Error.", bs="09:00", be="09:40"),
            w("AOI-1", "W3", "09:26", "09:39", bs="09:00", be="09:40"), w("AOI-2", "W9", "12:20", "12:30", lot="LOT-B")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["e"]) == (25, 15, 1)                       # 09:12~09:26 + 09:39~09:40 = 15분이 Error, 3분 표식 아님
    assert t["s"] == 170 and t["ct"] == {"SCAN_ERROR": [1, 185]}         # Report 끝 09:40 → 12:30 대기, 유형에 Error+대기 분


def test_untimed_pass_and_error_rows_share_the_free_minutes_equally():
    rows = [w("AOI-1", "W1", bs="08:00", be="09:00"), w("AOI-1", "W2", status="Alignment Error.", bs="08:00", be="09:00"), w("AOI-1", "W3", "10:00", "10:10", lot="LOT-B")]
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["x"], t["s"]) == (40, 30, 60)                       # 창 60분을 30/30 으로 나눔 + LOT-B 10분 · Report 끝 09:00 → 10:00 대기


# ── 6. D64 Test Lot 전부 Test ───────────────────────────────────────────────
def test_test_lot_rows_are_all_test_even_with_a_cause_error():
    rows = [w("AOI-1", "W1", "10:00", "10:12", lot="TEST-GVB"), w("AOI-1", "W2", "10:12", "10:14", lot="TEST-GVB", status="Alignment Error.")]
    t = at(run(rows), "AOI-1")
    assert (t["t"], t["x"], t["e"], t["r"]) == (14, 0, 0, 0) and t["ct"] == {}


# ── 7. D57 수집일 분모 = 모든 장비의 마지막 기록 ────────────────────────────
def test_collection_day_denominator_is_the_last_record_of_all_devices():
    rows = [w("AOI-1", "W1", "00:05", "00:15"), w("AOI-2", "W9", "11:25", "11:35", lot="LOT-B")]
    D = run(rows)
    assert at(D, "AOI-1")["den"] == 695 and at(D, "AOI-2")["den"] == 695
    rows2 = rows + [w("AOI-1", "W2", "07:00", "07:30", day="2026-09-17")]
    assert at(run(rows2), "AOI-1", "2026-09-17")["den"] == 1440


# ── 8. D04 자정 분할 ────────────────────────────────────────────────────────
def test_a_wafer_crossing_midnight_is_split_between_the_two_days_and_counted_once():
    rows = [w("AOI-1", "W1", "23:50", "00:10", day="2026-09-17", eday="2026-09-18"), w("AOI-2", "W9", "01:00", "01:10", lot="LOT-B")]
    D = run(rows)
    a, b = at(D, "AOI-1", "2026-09-17"), at(D, "AOI-1")
    assert (a["r"], b["r"]) == (10, 10) and (a["w"], b["w"]) == (1, 0)     # 시간은 나뉘고 Wafer 수는 시작일에 한 번
    assert a["seg"] == [[1430, 1440, 0]] and b["seg"] == [[0, 10, 0]]


# ── 9. D09 엄격 날짜 ────────────────────────────────────────────────────────
def test_invalid_dates_are_dropped_not_turned_into_nan_days():
    bad = w("AOI-1", "W1", "08:00", "08:10")
    bad["wafer_start_time"] = "18-Sxp-26 08:00:00 AM"
    bad["batch_start"] = "30-Feb-26 08:00:00 AM"
    bad["batch_end"] = "18-Sep-26 25:00:00 AM"
    D = run([bad, w("AOI-2", "W9", "09:00", "09:10")])
    assert D["badRows"] == 1 and all(d.startswith("2026-") for d in D["days"]) and "AOI-1" not in D["detail"][DAY]


# ── 10. D12 lotName (SETUP 파일명) ──────────────────────────────────────────
def test_lot_name_keeps_the_table_lot_when_the_setup_is_not_four_digits():
    rep = "R_TB500_LIVE_PI3_SETUP_AMD Venice_U-Pad Dummy_18-Sep-26_(09.00.00)_BatchReport.htm"
    D = run([w("AOI-1", "W1", "08:00", "08:10", lot="AMD Venice_U-Pad Dummy", job="R_TB500_LIVE_PI3", report=rep)])
    assert D["pool"]["lot"] == ["AMD Venice_U-Pad Dummy"]
    D2 = run([w("AOI-1", "W1", "08:00", "08:10", lot="GVB-DIA", report="R_TB500_LIVE_PI3_6321_GVB-DIA RE_18-Sep-26_(09.00.00)_BatchReport.htm")])
    assert D2["pool"]["lot"] == ["GVB-DIA RE"]                            # R1 규칙(KEEP 꼬리표만 남김)은 그대로


# ── 11. 장비 정렬 · 범위 밖 · 오늘 폴백 ─────────────────────────────────────
def test_devices_follow_devices_sort_key_and_out_of_scope_devices_are_listed_apart():
    mt = meta("AOI-10", "AOI-2", "4F-AOI-01", more=[{"name": "AOI-26", "note": "X:\\AOI-26", "report_dir": "Report", "scope": "out"}])
    D = run([w("AOI-2", "W1", "08:00", "08:10")], mt)
    assert D["devices"] == ["AOI-2", "AOI-10", "4F-AOI-01"]
    assert [s["n"] for s in D["scope"] if s["out"]] == ["AOI-26"]


def test_day_falls_back_to_the_last_data_day_when_the_collection_day_has_no_data():
    D = run([w("AOI-1", "W1", "08:00", "08:10", day="2026-09-16")])
    assert D["today"] == DAY and D["day"] == "2026-09-16" and at(D, "AOI-1", "2026-09-16")["den"] == 1440


def test_job_groups_merge_copies_but_keep_r_prefix_and_step_apart():
    rows = [w("AOI-1", "W1", "08:00", "08:10", job="R_TB500_LIVE_PI3"), w("AOI-1", "W2", "08:20", "08:30", job="R_TB500_LIVE_PI3 AOI-11 Copy", lot="LOT-B"),
            w("AOI-1", "W3", "08:40", "08:50", job="R_TB500_LIVE_PI4", lot="LOT-C"), w("AOI-1", "W4", "09:00", "09:10", job="2D@RE-TB500_LIVE_PI3", lot="LOT-D")]
    D = run(rows)
    g = D["jobG"]
    assert g[0] == g[1] and g[2] != g[0] and g[3] != g[0]


# ── 12. 화면 함수 · 전역 상수 (하네스 screen/globals 모드 — S05 로 글자 검사를 대신한다) ────────────
def run_raw(payload):
    return subprocess.run([NODE, str(HARNESS)], input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True, timeout=120, cwd=str(ROOT))


def globals_(*names):
    out = run_raw({"globals": list(names)})
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


def screen(rows, mt, calls, state=None):
    """init() 과 같은 준비를 한 뒤 전역 함수들을 차례로 부른 반환값 목록."""
    out = run_raw({"screen": {"rows": rows, "meta": mt, "state": state or {}, "calls": calls}})
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout)


def _hhmm(base: str, plus: int) -> str:
    h, m = map(int, base.split(":"))
    t = h * 60 + m + plus
    return f"{t // 60:02d}:{t % 60:02d}"


def test_default_profile_is_product_with_the_four_rules_on_and_constants_match():
    """기본 buildModel 은 product 프로필(네 스위치 켬)이고, 상수(MODEL_VERSION · JOB_ALIAS 21개 · CAUSE_CODES)는 정규식 추출값·디자인 표·파이썬과 같다."""
    import sys
    sys.path.insert(0, str(ROOT / "dev" / "tests"))
    import template_facts  # noqa: E402
    from aoi_capacity import collect

    D = run([w("AOI-1", "W1", "08:00", "08:10")])
    assert D["rules"] == {"profile": "product", "waitToObsEnd": True, "denomToday": True, "abortIsError": True, "estimateFromBatch": True}
    g = globals_("RULES", "MODEL_VERSION", "JOB_ALIAS", "CAUSE_CODES")
    assert g["RULES"] == D["rules"] and D["modelVersion"] == g["MODEL_VERSION"] == template_facts.model_version()
    assert g["CAUSE_CODES"] == [c for c, _ in collect._CAUSE_RULES]
    design_alias = template_facts.job_alias((ROOT / "docs" / "design" / "dashboard-redesign" / "scripts" / "job_alias.js").read_text(encoding="utf-8"))
    assert g["JOB_ALIAS"] == template_facts.job_alias() == design_alias and len(g["JOB_ALIAS"]) == 21


def test_home_lists_devices_in_device_order_with_collect_chips_and_the_no_record_count():
    """홈 목록은 cmpDev 순(AOI-2 → AOI-3 → AOI-10 → 4F, 사전순이 아니다), 수집 상태 칩은 meta.devices[].status 에서, 기록 없는 장비는 '기록 없음 n대' 로 따로(D06)."""
    mt = meta("AOI-10", "AOI-2", "4F-AOI-01", "AOI-3")
    for d in mt["devices"]:
        if d["name"] == "AOI-3":
            d.update(status="unreachable", error="timeout")
        if d["name"] == "AOI-2":
            d.update(status="partial", read_errors=2)
    rows = [w("AOI-10", "W1", "08:00", "08:10"), w("AOI-2", "W2", "09:00", "09:10"), w("4F-AOI-01", "W3", "10:00", "10:10")]
    home, chip_ok, chip_partial, chip_bad = screen(rows, mt, [["homeHtml"], ["collectChip", "AOI-10"], ["collectChip", "AOI-2"], ["collectChip", "AOI-3"]])
    assert re.findall(r'data-fk="dev:([^"]+)"', home) == ["AOI-2", "AOI-3", "AOI-10", "4F-AOI-01"]   # 번호순, 사전순이면 AOI-10 이 AOI-2 앞
    assert chip_ok == "" and "일부 누락" in chip_partial and "수집 실패" in chip_bad
    assert "일부 누락" in home and "수집 실패" in home and "기록 없음 1대" in home
    for term in (">Scan<", ">Rescan<", ">Test<", ">Error<", ">에러 후 대기<", ">대기<"):
        assert term in home, term


def test_foot_shows_only_out_of_scope_devices_from_meta():
    """10/7 사용자: 바닥글의 수집 범위 목록 · 장비/일수/버전 줄 · 가동률 설명 문구는 지웠다 — 수집 안 함(범위 밖 장비)만 남는다."""
    mt = meta("AOI-1", more=[{"name": "AOI-26", "note": "X:\\AOI-26", "report_dir": "Report", "scope": "out"}])
    (foot,) = screen([w("AOI-1", "W1", "08:00", "08:10")], mt, [["footHtml"]])
    assert "수집 범위" not in foot and "정확 경로만 확인" not in foot and "가동률 = (Scan + Rescan)" not in foot
    assert "수집 안 함" in foot and "AOI-26" in foot


def test_report_url_is_built_only_from_meta_for_drive_and_unc_paths():
    mt = meta("AOI-1", "AOI-24")
    mt["devices"][1].update(note="\\\\10.142.80.88\\Camtek24-25\\AOI-24", report_dir="Reports")
    rep = "J1_6321_LOT A_18-Sep-26_(00.00.00)_BatchReport.htm"
    drive, unc, none, unknown = screen([w("AOI-1", "W1", "08:00", "08:10")], mt, [
        ["reportUrl", {"device": "AOI-1", "report": rep}], ["reportUrl", {"device": "AOI-24", "report": rep}],
        ["reportUrl", {"device": "AOI-1", "report": ""}], ["reportUrl", {"device": "AOI-99", "report": rep}]])
    assert drive == "file:///X:/AOI-1/Report/J1_6321_LOT%20A_18-Sep-26_(00.00.00)_BatchReport.htm"
    assert unc == "file://10.142.80.88/Camtek24-25/AOI-24/Reports/J1_6321_LOT%20A_18-Sep-26_(00.00.00)_BatchReport.htm"
    assert none == "" and unknown == ""


def _clean_batches(n_batches):
    """표기명 Job(R_TB500_LIVE_PI3) 의 정상 배치 n개 — 장수 5,6,7… · 배치시간 = 10 + 5×장수 분(완전 적합)."""
    rows = []
    for i in range(n_batches):
        n = 5 + i
        bs = f"{8 + 2 * i:02d}:00"
        be = _hhmm(bs, 10 + 5 * n)
        lot = f"LOT-{i + 1}"
        rep = f"R_TB500_LIVE_PI3_6321_{lot}_18-Sep-26_({bs.replace(':', '.')}.00)_BatchReport.htm"
        for k in range(n):
            rows.append(w("AOI-1", f"W{i}{k}", _hhmm(bs, k + 1), _hhmm(bs, k + 2), lot=lot, job="R_TB500_LIVE_PI3", report=rep, bs=bs, be=be))
    return rows


def test_report_tab_regresses_only_with_five_or_more_clean_batches_and_lists_exclusions():
    """D49·D59: 표본 5개 이상이면 준비·장당 회귀(여기선 10 + 5×장수 완전 적합), 원인 Error 가 있는 배치는 표본에서 뺀다. 4개면 '5개 미만' 으로 생략."""
    rows = _clean_batches(5)
    err_rep = "R_TB500_LIVE_PI3_6321_LOT-E_18-Sep-26_(18.00.00)_BatchReport.htm"
    for k in range(5):
        rows.append(w("AOI-1", f"E{k}", _hhmm("18:00", k + 1), _hhmm("18:00", k + 2), lot="LOT-E", job="R_TB500_LIVE_PI3", report=err_rep, bs="18:00", be="18:30"))
    rows.append(w("AOI-1", "E9", "18:20", "18:22", lot="LOT-E", job="R_TB500_LIVE_PI3", report=err_rep, bs="18:00", be="18:30", status="Alignment Error."))
    (html,) = screen(rows, meta("AOI-1"), [["reportHtml"]], state={"view": "report", "rptDev": "AOI-1"})
    assert "<h1>TB500 · Kendall</h1>" in html and "표기명 21개 Job 만 봅니다" in html
    assert ">PI3</b>" in html and "준비 10분 + 장당 5.0분" in html and "2시간 15분" in html          # 10 + 5×25 = 135분 (25장 환산)
    assert "10.0 ± 0.0분" in html and "5.00 ± 0.00분" in html                                      # 장비 상세의 회귀 값
    assert "5 / 6" in html and "제외 — Error 1 · PASS 5장 미만 0" in html
    assert "data-dh=" in html and "이 장비의 모든 배치 보기 (6개)" in html            # 더블클릭 · 단추 = 모든 배치 팝업(10/19)
    (html4,) = screen(_clean_batches(4), meta("AOI-1"), [["reportHtml"]], state={"view": "report"})
    assert "표본 4개 — 5개 미만" in html4 and "2시간 15분" not in html4


def test_report_tab_leaves_out_a_batch_whose_wafers_were_all_skipped():
    """10/30: 스캔된 장이 없는 배치(6장 모두 Skipped · 배치 1분)가 행 수 6 으로 표본에 들었다. 표본은 PASS 장 수로 센다 — 정상 배치 5개는 그대로,
    모든 배치 팝업에는 '제외 — PASS 5장 미만' 으로 남고 PASS 장수 0 / 행 6 을 보인다."""
    rows = _clean_batches(5)
    rep = "R_TB500_LIVE_PI3_6321_LOT-S_18-Sep-26_(13.49.00)_BatchReport.htm"
    for k in range(6):
        rows.append(w("AOI-1", f"S{k}", status="Wafer Skipped.", lot="LOT-S", job="R_TB500_LIVE_PI3", report=rep, bs="13:49", be="13:50"))
    html, popup = screen(rows, meta("AOI-1"), [["reportHtml"], ["rptDevPopupHtml"]],
                         state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert "5 / 6" in html and "제외 — Error 0 · PASS 5장 미만 1" in html     # 표본 5 · 배치 6, 건너뜀 배치는 '5장 미만' 으로
    assert "10.0 ± 0.0분" in html and "5.00 ± 0.00분" in html                  # 회귀는 정상 5개 그대로
    assert "제외 — PASS 5장 미만" in popup and "PASS 0장" in popup and "/6" in popup


def test_error_popup_shows_each_types_own_phrase_when_one_lot_has_two_types():
    """한 Lot 에 유형이 둘이면(30일치 175 Lot) 줄마다 그 유형의 원문 — 모델의 대표 원문(st) 하나를 두 줄에 붙이지 않는다."""
    rep = "J1_6321_LOT-A_18-Sep-26_(08.00.00)_BatchReport.htm"
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error.", report=rep),
            w("AOI-1", "W2", "08:10", "08:12", status="Scan 2D Error.", report=rep),
            w("AOI-1", "W3", "08:20", "08:30", report=rep), w("AOI-2", "W9", "12:00", "12:10", lot="LOT-B")]
    html, a, s = screen(rows, meta("AOI-1", "AOI-2"), [["errPopupHtml"], ["causeText", "AOI-1", rep, "ALIGN_ERROR"], ["causeText", "AOI-1", rep, "SCAN_ERROR"]],
                        state={"errDev": "AOI-1", "errDayI": 0})
    assert (a, s) == ("Alignment Error.", "Scan 2D Error.")
    assert 'data-dlg="err"' in html and html.count("Alignment Error.") == 1 and html.count("Scan 2D Error.") == 1


def test_lot_key_separates_two_reports_of_the_same_lot_on_the_same_day():
    """D16: Lot 선택 키에 Report 번호(L[8])가 들어간다."""
    L1 = [0, 0, 480, 490, 1, 0, 0, 0, 3, {}, -1, 480, 490]
    L2 = list(L1)
    L2[8] = 4
    k1, k2, k3 = screen([w("AOI-1", "W1", "08:00", "08:10")], meta("AOI-1"), [["lotKey", L1], ["lotKey", L2], ["lotKey", list(L1)]])
    assert k1 == k3 and k1 != k2


def test_attention_concept_is_gone_and_old_dashboard_settings_are_ignored():
    """11/25(사용자): '살펴볼 장비' 개념을 없앴다 — 카드 · 점 · 빨간 숫자 문턱 없음. 옛 HTML 의 meta.dashboard_settings 가 있어도 무시."""
    rows = [w("AOI-1", "W1", "08:00", "08:10")]
    mt = meta("AOI-1")
    mt["dashboard_settings"] = {"attentionUtil": 60, "attentionErr": 1}
    (home,) = screen(rows, mt, [["homeHtml"]])
    assert "살펴볼" not in home and 'class="dot' not in home and "평균 가동률" in home


def test_unfold_rejects_out_of_range_pool_index_and_duplicate_columns():
    """D09 로더: 풀 번호 범위 밖·열 이름 중복은 빈 문자열로 숨기지 않고 예외다(loadDemo 가 오류 패널로 보여 준다)."""
    cols = ["device", "kind", "job", "setup", "lot", "wafer_id", "status", "wafer_start_time", "wafer_end_time", "batch_start", "batch_end", "report", "ini_match", "scan_type"]
    good = {"cols": cols, "pooled": ["device", "status"], "pool": ["AOI-1", "Pass"],
            "rows": [[0, "", "J1", "6321", "LOT-A", "W1", 1, ts(DAY, "08:00"), ts(DAY, "08:10"), ts(DAY, "08:00"), ts(DAY, "08:10"), "r.htm", "EXACT", ""]],
            "meta": meta("AOI-1")}
    ok = run_raw({"embedded": good})
    assert ok.returncode == 0 and at(json.loads(ok.stdout), "AOI-1")["r"] == 10
    bad = dict(good, rows=[[0, "", "J1", "6321", "LOT-A", "W1", 7, ts(DAY, "08:00"), ts(DAY, "08:10"), "", "", "r.htm", "EXACT", ""]])
    r = run_raw({"embedded": bad})
    assert r.returncode != 0 and "풀 번호가 범위 밖" in r.stderr
    dup = dict(good, cols=cols[:-1] + ["device"])
    r2 = run_raw({"embedded": dup})
    assert r2.returncode != 0 and "중복" in r2.stderr


def test_header_has_four_tabs_and_each_popup_renders_an_accessible_dialog():
    """D59 탭 이름 · 사본 저장 버튼 · 장비/Error/유형 팝업이 role=dialog + aria-labelledby 로 그려진다(포커스 이동은 browser 테스트)."""
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error."), w("AOI-1", "W2", "09:00", "09:10", lot="LOT-B")]
    head, dev, err, closed, _, typ = screen(rows, meta("AOI-1"), [
        ["headerHtml", "home"],
        ["devPopupHtml"], ["errPopupHtml"], ["typePopupHtml"],
        ["errorsHtml"], ["typePopupHtml"]],
        state={"modalDev": "AOI-1", "modalDayI": 0, "errDev": "AOI-1", "errDayI": 0})
    assert re.findall(r'data-fk="nav:([a-z]+)"', head) == ["home", "errors", "overkill", "report", "recipe", "lot"]   # 10/5: KLA 탭 · 추이 탭 없음, 10/11 LOT 추적, 10/22 파라미터 탭은 기본 숨김(HIDDEN_TABS), 10/30 Overkill(D99)
    shown, = screen(rows, meta("AOI-1"), [["headerHtml", "home"]], state={"unhid": ["param"]})
    assert re.findall(r'data-fk="nav:([a-z]+)"', shown)[-1] == "param"   # 설정 버튼에서 꺼내면 탭 줄 맨 뒤로 돌아온다
    m_full = dict(meta("AOI-1"), hidden_tabs=["recipe"])           # 전체 배포판(10/30): RDL 단일스캔은 평소 숨기고 설정에서 꺼내 쓴다
    hid_nav, opened, menu = screen(rows, m_full, [["headerHtml", "home"]], state={}), screen(rows, m_full, [["headerHtml", "home"]], state={"unhid": ["recipe"]}), \
        screen(rows, m_full, [["headerHtml", "home"]], state={"devOn": True, "setOpen": True})
    assert re.findall(r'data-fk="nav:([a-z]+)"', hid_nav[0]) == ["home", "errors", "overkill", "report", "lot"]
    assert re.findall(r'data-fk="nav:([a-z]+)"', opened[0]) == ["home", "errors", "overkill", "report", "recipe", "lot"]    # 꺼내면 제자리로 돌아온다
    assert ">RDL 단일스캔<" in menu[0] and ">파라미터<" in menu[0]                                                               # 설정 메뉴에 파라미터와 함께 나온다
    for label in (">가동률<", ">Error<", ">Overkill<", ">TB500 · Kendall<", ">RDL 단일스캔<", ">사본 저장<"):
        assert label in head, label
    assert ">추이<" not in head and ">KLA<" not in head
    assert 'data-dlg="dev"' in dev and 'aria-labelledby="dlg-dev-title"' in dev and 'role="dialog"' in dev
    assert 'data-dlg="err"' in err and 'aria-labelledby="dlg-err-title"' in err
    assert closed == ""                                   # 유형 팝업은 state.modalType 이 없으면 그리지 않는다
    (typ2,) = screen(rows, meta("AOI-1"), [["errorsHtml"], ["typePopupHtml"]], state={"view": "errors", "modalType": "ALIGN_ERROR"})[1:]
    assert 'data-dlg="type"' in typ2 and 'aria-labelledby="dlg-type-title"' in typ2 and "ALIGN_ERROR" in typ2


def test_multi_and_single_scans_are_different_jobs_but_the_same_material():
    """D76(10/5): 같은 Job 이름이라도 멀티 · 단일은 다른 Job — `TB500_RDL4 - Multi` → `TB500_RDL4-Multi` · `-Single`(근거 없으면 `-미구분`).
    원문에 Multi 가 없는 Job 의 단일은 이름 그대로. 자재 키는 원문 — 멀티로 PASS 한 Wafer 를 단일로 다시 보면 Rescan. 표기명도 따라 나뉜다."""
    J = "TB500_RDL4 - Multi"
    rows = [dict(w("AOI-1", "W1", "08:00", "08:20", lot="LOT-A", job=J), scan_mode="MULTI"),
            dict(w("AOI-1", "W1", "09:00", "09:10", lot="LOT-A", job=J, report="r2.htm"), scan_mode="SINGLE"),
            dict(w("AOI-2", "W9", "10:00", "10:10", lot="LOT-C", job=J, report="r9.htm"), scan_mode=""),   # 다른 장비 · 근거 없음 → 미구분
            dict(w("AOI-1", "P1", "11:00", "11:05", lot="LOT-P", job="R_TB500_LIVE_PI2"), scan_mode="SINGLE"),
            dict(w("AOI-1", "P2", "12:00", "12:05", lot="LOT-Q", job="R_TB500_LIVE_PI2"), recipe="PI|PI_Bubble")]
    D = run(rows, meta("AOI-1", "AOI-2"))
    assert set(D["pool"]["job"]) >= {"TB500_RDL4-Multi", "TB500_RDL4-Single", "TB500_RDL4-미구분", "R_TB500_LIVE_PI2", "R_TB500_LIVE_PI2-Multi"}
    assert J not in D["pool"]["job"]
    t = at(D, "AOI-1")
    assert t["d"] == 10                                         # 멀티 PASS 뒤 같은 Wafer 단일 = Rescan(자재 키는 원문 Job)
    rpt, = screen(rows, meta("AOI-1"), [["reportHtml"]])
    assert "TB500 RDL4-Multi" in rpt and "TB500 RDL4-Single" in rpt and "TB500 PI2-Multi" in rpt


def test_floor_and_maker_filters_combine():
    """10/5: 층(전체 · 2층 · 4층)과 장비 종류(전체 · Camtek · KLA)는 따로 고르고 함께 걸린다 — 4층 + KLA 면 4F-K* 만."""
    devs = ("AOI-1", "4F-AOI-01", "K1", "4F-K1")
    rows = [w(d, "W1", "08:00", "08:10") for d in devs]
    four_kla, two_cam, kla = screen(rows, meta(*devs), [["S.devList"], ["S.devList"], ["S.devList"]], state={"floor": "4", "maker": "kla"})[0:1] + \
        screen(rows, meta(*devs), [["S.devList"]], state={"floor": "2", "maker": "cam"}) + \
        screen(rows, meta(*devs), [["S.devList"]], state={"floor": "all", "maker": "kla"})
    assert four_kla == ["4F-K1"] and two_cam == ["AOI-1"] and kla == ["K1", "4F-K1"]
    home, = screen(rows, meta(*devs), [["homeHtml"]])
    assert "전체 층" in home and "전체 장비" in home and ">KLA<" in home


def test_recipe_tab_leaves_kla_out():
    """10/6: 레시피 탭에는 KLA 장비의 행이 들어가지 않는다 — 목록에도, 장비별 표에도."""
    rows = [w("AOI-1", "W1", "08:00", "08:10", job="TB500_RDL4 - Multi"),
            w("K1", "W2", "09:00", "09:10", job="ROOT-HVM-KLA-ONLY-SETUP")]
    html, = screen(rows, meta("AOI-1", "K1"), [["rcpHtml"]])
    assert "ROOT-HVM-KLA-ONLY-SETUP" not in html and ">K1<" not in html and "AOI-1" in html


def test_error_tab_leaves_kla_out():
    """10/6: Error 탭은 KLA 장비를 넣지 않고(장비별 목록에도 없다) 장비 종류 필터는 '전체 장비 · Gen5' 둘뿐(Camtek · KLA 단추 없음, 10/29)."""
    rows = [w("AOI-1", "E1", "08:00", "08:03", status="Alignment Error."), w("K1", "W2", "09:00", "09:10")]
    html, = screen(rows, meta("AOI-1", "K1"), [["errorsHtml"]], state={"pickDay": None})
    assert "dev:AOI-1" in html and "dev:K1" not in html and "전체 층" in html and "Gen5" in html and ">KLA<" not in html and ">Camtek<" not in html
    kla_picked, = screen(rows, meta("AOI-1", "K1"), [["errorsHtml"]], state={"pickDay": None, "maker": "kla"})
    assert "dev:AOI-1" in kla_picked                                   # 가동률 탭에서 KLA 를 골라 두어도 Error 탭은 비지 않는다


def test_unjudged_rows_take_the_mode_of_their_report_or_the_nearest_report():
    """10/6(사용자): INI 가 덮어써져 판정 못 한 장을 '미구분' 으로 두지 않는다 — ① 같은 Report 의 다른 장 판정
    ② Report 전체가 근거 없으면 같은 장비 · 같은 Job 에서 배치 시작이 가장 가까운 판정된 Report(추정). 다른 장비의 Report 는 쓰지 않는다."""
    J = "TB500_RDL4 - Multi"
    rows = [dict(w("AOI-1", "W1", "08:00", "08:20", lot="A", job=J), scan_mode="MULTI"),
            dict(w("AOI-1", "W2", "08:20", "08:40", lot="A", job=J), scan_mode="", ini_match="STALE"),
            dict(w("AOI-1", "W3", "12:00", "12:10", lot="B", job=J), scan_mode="SINGLE"),
            dict(w("AOI-1", "W4", "13:00", "13:10", lot="C", job=J), scan_mode="", ini_match="STALE"),
            dict(w("AOI-2", "W5", "13:00", "13:10", lot="D", job=J), scan_mode="", ini_match="STALE")]
    D = run(rows, meta("AOI-1", "AOI-2"))
    jobs = D["pool"]["job"]
    lots = {D["pool"]["lot"][L[1]]: jobs[L[0]] for dv in ("AOI-1", "AOI-2") for L in at(D, dv)["lots"]}
    assert lots["A"] == "TB500_RDL4-Multi"          # 같은 Report 의 W1 이 멀티
    assert lots["C"] == "TB500_RDL4-Single"         # 가장 가까운 판정 Report(b, 12:00)가 단일
    assert lots["D"] == "TB500_RDL4-미구분"          # AOI-2 에는 근거가 없다


def _rdl(dev, wafer, s, e, lot, mode, **kw):
    return dict(w(dev, wafer, s, e, lot=lot, job="TB500_RDL4 - Multi", **kw), scan_mode=mode)


def test_recipe_verdict_labels_both_comparison_scopes():
    """10/6 handoff C1: '전체 장' 과 '같은 장비' 두 비교를 같은 크기로 — 방향이 반대여도 둘 다 읽힌다.
    AOI-1 은 멀티 10분 · 단일 12분(같은 장비면 멀티가 2분 빠름), AOI-2 는 단일 5분만 → 전체 장끼리는 단일 중앙 8.5 로 단일이 1.5분 빠름."""
    rows = [_rdl("AOI-1", f"M{i}", f"08:{i*10:02d}", f"08:{i*10+10:02d}", "A", "MULTI") for i in range(3)]
    rows += [_rdl("AOI-1", f"S{i}", f"10:{i*12:02d}", f"10:{i*12+12:02d}", "B", "SINGLE") for i in range(3)]
    rows += [_rdl("AOI-2", f"T{i}", f"11:{i*5:02d}", f"11:{i*5+5:02d}", "C", "SINGLE") for i in range(3)]
    html, = screen(rows, meta("AOI-1", "AOI-2"), [["rcpHtml"]])
    assert 'class="vtab"' in html and 'class="verdict-table"' not in html
    # 10/6: 차이가 아니라 두 대상의 실제 값(멀티 중앙 · 단일 중앙)을 보이고 그 밑에 작게 어느 쪽이 빠른지
    assert re.search(r'전체</div><div class="vv num">10\.0<small>분/wafer</small></div><div class="vv num win">8\.5<small>분/wafer</small></div><div class="vn"><span[^>]*>단일 1\.5분/wafer 빠름', html)
    assert re.search(r'같은 장비 <span class="muted">1대</span></span></div><div class="vv num win">10\.0<small>분/wafer</small></div><div class="vv num">12\.0<small>분/wafer</small></div><div class="vn"><span[^>]*>멀티 2\.0분/wafer 빠름', html)
    assert "낮을수록 좋음" not in html                                                   # 10/7: 설명 문구는 지웠다
    only_multi, = screen(rows[:3], meta("AOI-1"), [["rcpHtml"]])
    # 11/25 RDL-09: 한 방식 기록이 아예 없으면 표 네 줄 대신 한 줄, 빈 타일도 '—분/wafer · 표본 0 / 0' 대신 한 줄
    assert "단일 기록이 없어 비교할 수 없습니다 — 멀티 값만 있습니다" in only_multi and 'class="vtab"' not in only_multi
    assert "이 기간 단일 기록 없음" in only_multi and "—<small>" not in only_multi


def test_recipe_device_rows_show_unjudged_values_and_select_only_a_picked_device():
    """11/25 RDL-10: 판정 못 한 wafer 만 있는 장비는 '값 없음' 이 아니라 옅은 회색 점(판정 못 함 값 — 멀티 · 단일에는 섞지 않음).
    RDL-11: 아무도 고르지 않았으면 어느 장비 행도 '선택됨' 이 아니다 — 팝업을 연 장비만. RDL-13: wafer 수 앞에 방식 색 점."""
    rows = [_rdl("AOI-1", f"M{i}", f"08:{i*10:02d}", f"08:{i*10+10:02d}", "A", "MULTI") for i in range(3)]
    rows += [_rdl("AOI-3", f"U{i}", f"10:{i*12:02d}", f"10:{i*12+12:02d}", "B", "") for i in range(3)]
    html, = screen(rows, meta("AOI-1", "AOI-3"), [["rcpHtml"]])
    row3 = next(x for x in html.split('class="dbrow') if 'data-row="dev:AOI-3"' in x)
    assert 'class="dlab U num"' in row3 and "판정 못 함만" in row3 and "값 없음" not in row3
    assert 'class="sw"' in row3.split('class="r num dc"')[1]
    assert re.findall(r'<button type="button" class="dbrow[^"]*"[^>]*aria-pressed="(\w+)"', html) == ["false", "false"]
    picked, = screen(rows, meta("AOI-1", "AOI-3"), [["rcpHtml"]], state={"rcpDevSel": "AOI-3"})
    assert 'class="dbrow on" data-key="slot:1" data-row="dev:AOI-3"' in picked


def test_recipe_wording_distinguishes_ini_and_report_time():
    """10/6 handoff C2: 장당 스캔은 INI + Report 보완 — 출처는 칩 두 개(INI n장 · Report 보완 n장), 'INI 만' 이라고 잘못 부르지 않는다.
    W2 는 INI 가 덮어써져(STALE) 그 Report 배치 창(08:00~08:30)에서 W1 의 10분을 뺀 20분을 받는다."""
    rows = [_rdl("AOI-1", "W1", "08:00", "08:10", "A", "MULTI", bs="08:00", be="08:30"),
            dict(_rdl("AOI-1", "W2", None, None, "A", "", bs="08:00", be="08:30"), ini_match="STALE")]
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]])
    assert "· INI 1 · Report 보완 1" in html and '표본 <b class="num">2</b> / 2 wafer' in html
    for old in ("장당 스캔(INI)", "INI 장당 중앙", "INI 시각 있는 장 없음", "이 칩은 스캔 시간의 출처입니다"):
        assert old not in html


def test_recipe_list_is_limited_to_tb500_rdl_and_pi_and_the_count_line_is_short():
    """10/6 사용자: 레시피는 TB500 RDL(RDL1~4 계열) · TB500 PI(2/3/4, Enhanced 는 따로) 만 — 다른 Job · 복사본 변형은 한 줄로.
    목록 안내는 짧게: 검색 안 하면 '전체 n개', 검색하면 '검색 결과 n개'(40개를 넘을 때만 ' · 40개 표시')."""
    jobs = ["TB500_RDL1 - Multi", "TB500_RDL2 - Multi", "TB500_RDL2 - Multi_COPY", "R_TB500_LIVE_PI3", "R_TB500_LIVE_PI3 AOI-13 Copy_0702",
            "R_TB500_LIVE_PI3 - Enhanced", "R_TB500_LIVE_PI4-x5", "R_KENDALL_A0_PI3", "ROOT-HVM-4DT-TB500-H-M1-RDL2_NEW", "ALPHA00"]
    rows = [w("AOI-1", f"W{i}", f"{8 + i // 6:02d}:{(i % 6) * 10:02d}", f"{8 + i // 6:02d}:{(i % 6) * 10 + 5:02d}", lot=f"L{i}", job=j) for i, j in enumerate(jobs)]
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]])
    names = re.findall(r'data-row="rcp:[^"]*"[^>]*>\s*<span class="rn"[^>]*>([^<]*)</span>', html)
    assert sorted(names) == ["TB500 PI3", "TB500 RDL1", "TB500 RDL2"]   # PI4-x5 · Kendall · ROOT-… · ALPHA 는 이 탭에 없다, 복사본은 한 줄로 · PI3 Enhanced 는 PI3 와 같은 줄(기존 vs Enhanced)
    note = lambda h: re.search(r'data-key="rcp:note">([^<]*)<', h).group(1)
    assert note(html) == "전체 3개" and "레시피 4개" not in html.split('class="rcpgrid"')[0]
    found, = screen(rows, meta("AOI-1"), [["rcpHtml"]], state={"rcpQ": "rdl1"})
    assert note(found) == "검색 결과 1개"
    none, = screen(rows, meta("AOI-1"), [["rcpHtml"]], state={"rcpQ": "zzz"})
    assert "검색 결과 0개" in none and "검색 결과가 없습니다" in none and 'data-fk="rcp:clear"' in none and 'class="panel scanhero"' not in none


def _lot_rows(n, rep="R1.htm", bs="08:00", be="10:00", dev="AOI-1"):
    rows = []
    for i in range(n):
        rows.append(_rdl(dev, f"W{i}", f"08:{i:02d}", f"08:{i + 1:02d}", "LOT-A", "SINGLE", report=rep, bs=bs, be=be))
    return rows


def test_report_lot_time_is_scaled_to_25_wafers_only_for_20_to_24():
    """10/6 사용자: Report 1LOT당 = Batch Start→End. 20~24장이면 ×25÷장수(25장 기준), 25장 이상은 그대로, 19장 이하는 뺀다.
    (120분짜리 Report 로) 26장 → 120.0 · 24장 → 125.0 · 20장 → 150.0 · 19장 → 계산 안 함.
    11/25 RDL-12: LOT당 시간은 'n시간 m분'(TB500 · Kendall 탭과 같은 읽는 법) — 소수 분은 큰 숫자의 title 에."""
    for n, want, big, raw in ((26, "2시간", "2<small>시간</small>", "120.0"), (24, "2시간 5분", "2<small>시간</small> 5<small>분</small>", "125.0"),
                              (20, "2시간 30분", "2<small>시간</small> 30<small>분</small>", "150.0")):
        html, = screen(_lot_rows(n), meta("AOI-1"), [["rcpHtml"]])
        assert f"LOT당 {want} · Defect" in html, (n, want)
        lot, = screen(_lot_rows(n), meta("AOI-1"), [["rcpHtml"]], state={"rcpUnit": "lot"})     # LOT당 보기: 같은 값이 큰 숫자
        assert f'<p class="v num" title="{raw}분">{big}<small>/Lot</small></p>' in lot and '표본 <b class="num">1</b> / 1 Lot' in lot
    html, = screen(_lot_rows(19), meta("AOI-1"), [["rcpHtml"]], state={"rcpHowAll": True})
    assert "LOT당 — · Defect" in html and "PASS 20장 미만 Lot 1개" in html
    lot, = screen(_lot_rows(19), meta("AOI-1"), [["rcpHtml"]], state={"rcpUnit": "lot"})     # RDL-14: LOT 표본이 왜 적은지 타일에서 바로
    assert '제외 1 ⓘ' in lot and "PASS 20장 미만 1" in lot and "LOT 표본 없음 — PASS 20장 미만 1" in lot


def test_recipe_lot_unit_verdict_shows_per_day_throughput_and_hour_labels():
    """10/24 하루당 처리량 · 11/25 RDL-12: LOT당 비교는 'n시간 m분' 과 하루당 Lot, 축은 시간 단위 눈금."""
    rows = _lot_rows(26) + [dict(r, scan_mode="MULTI", wafer_id="M" + r["wafer_id"]) for r in _lot_rows(26, rep="R2.htm", bs="10:00", be="13:00")]
    for r in rows[26:]:
        r["batch_start"], r["batch_end"] = ts(DAY, "10:00"), ts(DAY, "13:00")
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]], state={"rcpUnit": "lot"})
    v = html[html.index('class="mtile verdict"'):]
    assert "3시간" in v and "2시간" in v and "Lot/일" in v and "단일 1시간 빠름" in v
    assert re.search(r'class="sax"><em[^>]*>0</em><em[^>]*>1시간</em>', html)


def test_report_lot_time_skips_reports_with_an_error_but_keeps_abort_only_ones():
    """Error 유형이 있는 Report 는 Report 기준 통계에서 빠지고, 원인 없이 Aborted 만 있는 Report 는 들어간다."""
    err = _lot_rows(22, rep="E.htm") + [w("AOI-1", "E1", "09:00", "09:01", status="Alignment Error.", job="TB500_RDL4 - Multi", report="E.htm", bs="08:00", be="10:00")]
    html, = screen(err, meta("AOI-1"), [["rcpHtml"]], state={"rcpHowAll": True})
    assert "Error 가 있는 Lot 1개" in html and "LOT당 120" not in html
    ab = _lot_rows(22, rep="A.htm") + [w("AOI-1", "A1", None, None, status="Aborted.", job="TB500_RDL4 - Multi", report="A.htm", bs="08:00", be="10:00")]
    html, = screen(ab, meta("AOI-1"), [["rcpHtml"]], state={"rcpHowAll": True})
    assert "LOT당 2시간 16분" in html and "Error 가 있는 Lot" not in html            # 22장 · 120분 → 25장 기준 136.4분(Aborted 만 있는 Report 는 포함)


def test_outliers_beyond_3_sigma_are_dropped_once_and_listed_but_not_for_tiny_samples():
    """3σ 한 번 · 표본 5개 미만이면 제거 안 함 · 제거했으면 값과 이유(평균 ± 3σ 범위)를 ⓘ 에 적는다(시간만 — Defect 는 10/7 부터 빼지 않는다)."""
    rows = [_rdl("AOI-1", f"W{i}", f"08:{i * 2:02d}", f"08:{i * 2 + 1:02d}", "LOT-A", "SINGLE") for i in range(21)]
    rows.append(_rdl("AOI-1", "BIG", "11:00", "13:30", "LOT-A", "SINGLE"))
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]])
    assert "이상치 1개 제외" in html and "150.0분" in html and "3σ" in html and "표본 <b class=\"num\">21</b> / 22 wafer" in html
    tiny = [_rdl("AOI-1", f"T{i}", f"08:{i * 3:02d}", f"08:{i * 3 + 1:02d}", "LOT-A", "SINGLE") for i in range(3)] + [_rdl("AOI-1", "BIG", "11:00", "13:30", "LOT-A", "SINGLE")]
    html, = screen(tiny, meta("AOI-1"), [["rcpHtml"]])
    assert "개 제외" not in html and "표본 <b class=\"num\">4</b> / 4 wafer" in html


def test_single_scan_counts_x20_only_and_pi_compares_existing_vs_enhanced():
    """단일은 x20 만 — x5 · x10 만 쓴 단일은 무시(실수로 돌린 것). PI 는 멀티 vs 단일이 아니라 **기존 vs Enhanced**(PI 는 모두 멀티스캔으로 본다 —
    scan_mode 가 비어 있고 레시피 칸의 '|' 도 믿지 않는다). Enhanced Job 은 같은 PI 줄에 합쳐지고 이름에 Enhanced 가 있으면 Enhanced."""
    rows = [_rdl("AOI-1", f"S{i}", f"08:{i * 2:02d}", f"08:{i * 2 + 1:02d}", "A", "SINGLE") for i in range(3)]
    rows += [dict(_rdl("AOI-1", f"X{i}", f"09:{i * 2:02d}", f"09:{i * 2 + 1:02d}", "B", "SINGLE"), recipe="x5") for i in range(2)]
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]])
    html, = screen(rows, meta("AOI-1"), [["rcpHtml"]], state={"rcpHowAll": True})
    assert "표본 <b class=\"num\">3</b> / 3 wafer" in html and "x5 · x10 단일 2장 제외" in html
    pi = [dict(w("AOI-1", f"P{i}", f"08:{i * 2:02d}", f"08:{i * 2 + 1:02d}", job="R_TB500_LIVE_PI3"), recipe="PI") for i in range(3)]
    pi += [dict(w("AOI-1", f"E{i}", f"10:{i * 2:02d}", f"10:{i * 2 + 1:02d}", job="R_TB500_LIVE_PI3 - Enhanced"), recipe="PI") for i in range(2)]
    html, = screen(pi, meta("AOI-1"), [["rcpHtml"]])
    assert html.count('class="rowbtn rcprow') == 1 and ">40%</b>" in html and 'Enhanced <b class="num">2</b>' in html   # 한 줄(PI3) · 막대 안 Enhanced 비율 · 밑 줄 wafer 수
    assert "</i>기존" in html and "</i>Enhanced" in html and "(x20 + x5)" not in html and "멀티 · 단일을 가릴" not in html
    assert "표본 <b class=\"num\">3</b> / 3 wafer" in html and "표본 <b class=\"num\">2</b> / 2 wafer" in html
    assert "<p class=\"vl\">Wafer당 Defect (중앙)</p>" in html and "Wafer당 스캔 (중앙)" in html     # 타일 맨 위 큰 숫자 둘: 스캔 시간 | Defect('장당' → Wafer당, 10/7)


def test_outliers_are_judged_per_layer_not_per_device_and_defect_is_never_cut():
    """10/7 사용자: 이상치는 장비를 보지 않고 레이어(레시피)만 — 장비 표본은 작다. 시간만 3σ 로 빼고 Defect 는 빼지 않는다(튀는 Defect 도 필요한 데이터).
    AOI-1 은 1분 장 20개 + 150분 한 장, AOI-2 는 1분 장 3개 + 150분 한 장 — AOI-2 표본(4개)은 5개 미만이어도 레이어 판정으로 150분을 뺀다.
    Defect 는 AOI-2 의 한 장만 9000 이어도 그대로 남는다."""
    f = lambda r, v="10": dict(r, faults=v)
    rows = [f(_rdl("AOI-1", f"W{i}", f"08:{i * 2:02d}", f"08:{i * 2 + 1:02d}", "LOT-A", "SINGLE")) for i in range(20)]
    rows.append(f(_rdl("AOI-1", "BIG", "11:00", "13:30", "LOT-A", "SINGLE")))
    rows += [f(_rdl("AOI-2", f"V{i}", f"08:{i * 2:02d}", f"08:{i * 2 + 1:02d}", "LOT-B", "SINGLE"), "9000" if i == 0 else "10") for i in range(3)]
    rows.append(f(_rdl("AOI-2", "BIG2", "12:00", "14:30", "LOT-B", "SINGLE")))
    (agg,) = screen(rows, meta("AOI-1", "AOI-2"), [["""(()=>{const X=rcpIndex(),gs=new Set(X.recs.map(q=>q.g)),A=rcpAgg(gs,D.days[0],D.days[D.days.length-1]);
        return {all:A.all.S.xs.out.length,d1:A.devs["AOI-1"].S.xs.out.length,d2:A.devs["AOI-2"].S.xs.out.length,d2n:A.devs["AOI-2"].S.s.length,
                f:A.all.S.f.length,fo:A.all.nOut.f,d2f:Math.max(...A.devs["AOI-2"].S.f)};})()"""]])
    assert agg["all"] == 2 and agg["d1"] == 1 and agg["d2"] == 1 and agg["d2n"] == 3   # AOI-2 는 장비 표본으로 재면 (4개 < 5) 못 뺀다 — 레이어 판정을 따른다
    assert agg["f"] == 25 and agg["fo"] == 0 and agg["d2f"] == 9000                      # Defect 는 하나도 빼지 않는다


def test_rdl_tab_excludes_user_listed_jobs_and_lists_excluded_recipes_small():
    """10/7 사용자: RDL4 JJ_BU(멀티 · 단일) · RDL4 JJ - SZ - Approved Job · RDL3 _ORG 는 이 탭에서 무시 —
    Swelling · PI4-x5 처럼 뺀 레시피와 함께 **그 레시피의 Job 칩 줄 끝에 '제외 n ▾'** 로 작게 남긴다(제안 D3-C — 올리거나 누르면 펼침)."""
    jobs = ["TB500_RDL4 - Multi", "TB500_RDL4 - Multi - JJ_BU", "TB500_RDL4 - Multi - JJ - SZ - Approved Job - Do Not Touch",
            "TB500_RDL3 - Multi_ORG", "TB500_RDL3 - Multi", "TB500_RDL1 - Multi - Swelling", "R_TB500_LIVE_PI4-x5", "TB500_RDL4 - Multi - JJ - SZ"]
    rows = [w("AOI-1", f"W{i}", f"{8 + i // 6:02d}:{(i % 6) * 10:02d}", f"{8 + i // 6:02d}:{(i % 6) * 10 + 5:02d}", lot=f"L{i}", job=j) for i, j in enumerate(jobs)]
    html, c3, c1, c4 = screen(rows, meta("AOI-1"), [["rcpHtml"], ["rcpExclChip", "TB500 RDL3", DAY, DAY], ["rcpExclChip", "TB500 RDL1", DAY, DAY], ["rcpExclChip", "TB500 PI4", DAY, DAY]])
    tab, excl = html.split('data-key="rcp:excl"')                                           # 첫 화면은 RDL4 — 그 Job 칩 줄 끝
    assert "JJ_BU" not in tab and "Approved Job" not in tab and "Multi_ORG" not in tab and "Swelling" not in tab
    assert 'class="jchip rexh"' in excl and "제외 2" in excl and "제외된 레시피" not in html
    assert jobs[1] in excl and jobs[2] in excl and excl.count("사용자 제외") == 2
    assert "TB500_RDL4 - Multi - JJ - SZ<" not in excl                                  # 'Approved Job' 이 없는 JJ - SZ 는 그대로 쓴다
    assert "제외 1" in c3 and jobs[3] in c3 and "사용자 제외" in c3
    assert "제외 1" in c1 and jobs[5] in c1 and "Swelling" in c1
    assert "제외 1" in c4 and jobs[6] in c4 and "x5 전용" in c4


# ── 10/11 Report 덮어쓰기: 설명만 나누고 분은 옮기지 않는다 ─────────────────────────
def test_overwritten_and_unscanned_rows_are_split_for_the_popup_without_moving_minutes():
    rep1 = "J1_6321_LOT-A_18-Sep-26_(09.00.00)_BatchReport.htm"
    rep2 = "J1_6321_LOT-A_18-Sep-26_(12.00.00)_BatchReport.htm"   # 같은 Lot 이름으로 다시 — 같은 INI 자리를 덮어쓴다
    rows = [w("AOI-1", "W1", bs="08:00", be="09:00", report=rep1) | {"ini_match": "STALE", "wafers_scanned": "2"},
            w("AOI-1", "W2", bs="08:00", be="09:00", report=rep1) | {"wafers_scanned": "2", "avg_scan_time": "00:13:00"},
            w("AOI-1", "W3", status="Wafer Skipped.", bs="08:00", be="09:00", report=rep1) | {"wafers_scanned": "2"},
            w("AOI-1", "W1", "11:00", "11:20", report=rep2) | {"wafers_scanned": "2"},
            w("AOI-1", "W4", status="Aborted.", bs="11:00", be="11:40", report=rep2) | {"wafers_scanned": "2"}]
    D = run(rows)
    t = at(D, "AOI-1")
    plain = at(run([{k: v for k, v in r.items() if k not in ("wafers_scanned", "avg_scan_time")} | {"ini_match": "NOT_FOUND" if not r["wafer_start_time"] else "EXACT"} for r in rows]), "AOI-1")
    assert (t["r"], t["d"], t["ne"]) == (plain["r"], plain["d"], plain["ne"])          # 분 · 추정 장 수는 그대로
    iv = t["iv"]
    assert (iv["ov"], iv["nf"], iv["sk"]) == (1, 1, 1) and iv["km"] == 60            # 덮어씀 1 · INI 없음 1 · 건너뜀 1, 배치 창 60분
    assert iv["s1"] == 1                                                              # 두 번째 Report: Pass 1 인데 Wafers Scanned 2 → 스캔 후 중단
    lot_a = next(L for L in t["lots"] if D["pool"]["rep"][L[8]] == rep1)
    assert lot_a[15] == 1 and lot_a[16] >= 0 and D["pool"]["st"][lot_a[16]].startswith("LOT-A · 09/18 11:00")   # 나중 시도
    assert "Avg. Scan Time 00:13:00" in D["pool"]["st"][lot_a[17]]


# ── D87(10/11): Lot 이름이 바뀐 재검사 · 모니터 Job ─────────────────────────
def test_renamed_lot_reinspection_is_rescan_only_with_same_step_and_recipe():
    A = "J1_6321_0909-XKS_18-Sep-26_(01.00.00)_BatchReport.htm"
    B = "J1_6321_XKS-161_18-Sep-26_(03.00.00)_BatchReport.htm"
    C = "J1_6321_XKS-DIA_18-Sep-26_(05.00.00)_BatchReport.htm"
    WID = "38135F75EWB5"
    rows = [w("AOI-1", WID, "00:10", "00:20", lot="0909-XKS", report=A) | {"recipe": "x20"},
            w("AOI-1", WID, "02:10", "02:30", lot="XKS-161", report=B) | {"recipe": "x20"},     # 이름만 바뀜 → Rescan
            w("AOI-1", WID, "04:10", "04:25", lot="XKS-DIA", report=C) | {"recipe": "x20"}]     # DIA 단계 → 다른 검사
    t = at(run(rows), "AOI-1")
    assert (t["r"], t["d"]) == (10 + 15, 20)
    other_recipe = [rows[0], rows[1] | {"recipe": "x5"}]
    assert at(run(other_recipe), "AOI-1")["d"] == 0                       # 레시피가 다르면 다른 검사
    slot_ids = [r | {"wafer_id": "12"} for r in rows[:2]]
    assert at(run(slot_ids), "AOI-1")["d"] == 0                           # 슬롯 번호 같은 짧은 ID 는 같은 실물로 보지 않는다


def test_no_pattern_jobs_are_test_and_leave_utilization():
    rows = [w("AOI-1", "W1", "08:00", "09:00", job="No Pattern Mon_0901"), w("AOI-1", "W2", "10:00", "10:30")]
    t = at(run(rows), "AOI-1")
    assert (t["t"], t["r"]) == (60, 30)


def _lot_keys(html):
    return re.findall(r'data-key="lp:lot:([^"]+)"', html)


def _lot_screen(rows, pick=None, **st):
    state = {"view": "lot", **st}
    if pick is not None:
        state["lotPick"] = {"k": "lot", "v": pick}
    (out,) = screen(rows, meta("AOI-1", "AOI-2"), [["lotHtml"]], state=state)
    return out


def test_lot_tab_groups_by_wafer_id_not_by_name_and_follows_devices():
    """LOT 추적(10/19 D92): 같은 Wafer ID 를 가진 Report 가 한 Lot — 이름 · 세 글자 코드가 달라도(별칭) 묶고, 장비가 바뀌어도 시간 순으로 잇는다."""
    A = "J1_6321_LPT-PIDS5_18-Sep-26_(01.00.00)_BatchReport.htm"
    B = "J1_6321_LPT-RDL3_18-Sep-26_(03.00.00)_BatchReport.htm"
    rows = [w("AOI-1", "38135F75EWB5", "00:10", "00:20", lot="LPT-PIDS5", report=A) | {"recipe": "x20", "faults": "7"},
            w("AOI-1", "38135F75EWB6", "00:20", "00:30", lot="LPT-PIDS5", report=A, status="Alignment Error."),
            w("AOI-2", "38135F75EWB5", "02:10", "02:30", lot="TYPO-RDL3", report=B) | {"recipe": "x20", "faults": "5"},
            w("AOI-2", "OTHER0WAFER1", "05:00", "05:10", lot="ZZZ-1", report="r9.htm")]
    lst = _lot_screen(rows)
    ks = _lot_keys(lst)
    assert len(ks) == 2                                                    # 이름이 둘이어도 Lot 은 하나 + ZZZ-1
    lot = next(k for k in ks if "LPT-PIDS5" in lst.split(f'lp:lot:{k}"')[1].split("</button>")[0])
    out = _lot_screen(rows, lot)
    assert out.count('class="lotatt"') == 2 and "ZZZ-1" not in out.split("스캔 순서")[1]
    assert "TYPO-RDL3" in out and "ALIGN_ERROR" in out and 'class="gap"' not in out and "+23일" not in out   # 10/25: 시작 밑 '+간격' 은 없앴다
    assert out.count('<b class="same">') == 0 and 'class="lotbox"' in out and "max-height" not in out.split('class="lotbox"')[1][:40]
    assert 'class="ix num">1<' in out and 'class="ix num">2<' in out                       # 스캔 번호 = 격자 열 번호
    assert "확인 필요" not in out and "lotconf" not in out
    (q,) = screen(rows, meta("AOI-1", "AOI-2"), [["lotHtml"]], state={"view": "lot", "lotQ": "ewb6"})
    assert "Wafer 38135F75EWB6" in q


def test_lot_tab_never_merges_past_25_wafers_and_shows_cross_rows():
    """한 Lot 은 25장 이하 — 같은 코드의 다른 Wafer 묶음(TSX 8월 · 9월)이나 겹쳐 합치면 25장을 넘는 Report 는 합치지 않고, 흐린 '다른 LOT 이름' 줄로만 보인다."""
    first = [w("AOI-1", f"AUG{i:06d}X", "00:10", "00:20", lot="TSX-1", report="a.htm") for i in range(25)]
    second = [w("AOI-1", f"SEP{i:06d}X", "02:10", "02:20", lot="TSX-1", report="b.htm") for i in range(25)]
    lst = _lot_screen(first + second)
    assert len(_lot_keys(lst)) == 2                                        # 코드가 같아도 Wafer 가 다르면 다른 Lot
    # 같은 Wafer 25장 + 6장(다른 Report 가 앞 5장 + 새 1장을 같이 가짐) → 합치면 26장이라 합치지 않는다
    third = [w("AOI-1", f"AUG{i:06d}X", "04:10", "04:20", lot="TYPO-9", report="c.htm") for i in range(5)] + \
            [w("AOI-1", "NEWW00000001", "04:10", "04:20", lot="TYPO-9", report="c.htm")]
    rows = first + third
    ks = _lot_keys(_lot_screen(rows))
    assert len(ks) == 2
    big = next(k for k in ks if "25 wafer" in _lot_screen(rows).split(f'lp:lot:{k}"')[1].split("</button>")[0])
    out = _lot_screen(rows, big)
    assert "다른 LOT 과 겹침 1번" in out and ">다른 LOT</span>" in out and 'class="lotatt xo"' in out   # 10/24: '.x'(닫기 단추 32px) 와 겹쳐 줄이 납작해지던 것 — 이름을 xo 로
    assert "다른 LOT 이름" not in out and "스캔 순서 <span" in out and "다른 LOT 1번(흐림)" in out           # 11/25(LOT-03 · LOTE-07 · LOTA-13): 한 낱말 줄기 · 표 제목 숫자


def test_lot_tab_wafer_search_counts_before_cut_and_wafer_mode_shows_results():
    """11/25 점검(LOTA-04 · LOTA-05 · LOTA-06 · LOTA-07 · LOTC-08): Wafer 검색은 자르기 전 개수를 적고 3글자 미만이면 찾지 않는다.
    Wafer 한 장을 고르면 PASS 칸 대신 결과 글자 · 슬롯, 그 Wafer 가 든 LOT 전체로 가는 단추. 재스캔 칸 툴팁은 앞 PASS 스캔을 말하고, 상한 초과 칸은 'Max'."""
    ids = [f"QWE{i:06d}X" for i in range(14)]
    rows = [w("AOI-1", i, "00:10", "00:20", lot="QQ-1", report="a.htm") | {"recipe": "x20", "slot_no": str(n + 1)} for n, i in enumerate(ids)] + \
           [w("AOI-2", i, "02:10", "02:20", lot="QQ-1", report="b.htm") | {"recipe": "x20"} for i in ids[:2]] + \
           [w("AOI-2", ids[2], "02:10", "02:20", lot="QQ-1", report="b.htm", status="Scan 2D - Max Fault Exceeded.")]
    lst = _lot_screen(rows, lotQ="qwe0")
    assert "Wafer 14개 중 12개 표시" in lst and lst.count("Wafer QWE") == 12
    assert "Wafer QWE" not in _lot_screen(rows, lotQ="qw")                       # 3글자 미만은 Wafer 를 찾지 않는다
    assert "와 맞는 LOT · Wafer 가 없습니다" in _lot_screen(rows, lotQ="zzzqq")
    (k,) = _lot_keys(_lot_screen(rows))
    (out,) = screen(rows, meta("AOI-1", "AOI-2"), [["lotHtml"]], state={"view": "lot", "lotPick": {"k": "wid", "v": ids[0]}})
    assert '<b class="rs ok">PASS</b> <small class="muted">#1</small>' in out and "결과 · 슬롯" in out
    assert "LOT QQ-1 · 14 wafer 전체 보기" in out and "LOT 이름 1개" in out and "이 Wafer 스캔 시간" in out
    full = _lot_screen(rows, k)
    # 칸 설명은 올릴 때 만든다(LOTD-07 data-lt → _lotTip) — 구분 한 줄(LOTA-07) · Max 도 그 안에
    _, t_re, t_max, t_no = screen(rows, meta("AOI-1", "AOI-2"),
                                  [["lotHtml"], ["_lotTip", "1|" + ids[0]], ["_lotTip", "1|" + ids[2]], ["_lotTip", "1|" + ids[5]]],
                                  state={"view": "lot", "lotPick": {"k": "lot", "v": k}})
    assert f'data-lt="1|{ids[0]}"' in full and "재스캔 — 스캔 1(" not in full                 # 칸에는 열쇠만
    assert "재스캔 — 스캔 1(" in t_re and "AOI-1) PASS 뒤 다시" in t_re and "스캔 2" in t_re
    assert "Max — Defect 상한 초과" in t_max and t_no.endswith("스캔 2 · 스캔 안 함")
    assert ">Max</i>" in full and "건너뜀·중단" in full and "스캔 안 함" in full


def test_lot_tab_ignores_slot_ids_and_parses_kla_names():
    """SLOT10 같은 자리표시는 Wafer ID 가 아니다(길이가 6이어도). KLA 'TB500.INT764@6322' 는 Lot 이름 TB500.INT764 + 공정 코드 6322."""
    rows = [w("AOI-1", "SLOT10", "00:10", "00:20", lot="A-1", report="a.htm"),
            w("AOI-1", "SLOT10", "01:10", "01:20", lot="B-1", report="b.htm")]
    assert _lot_keys(_lot_screen(rows)) == []
    kla = [w("K1", "KLAWAFER0001", "00:10", "00:20", lot="TB500.INT764@6322", report="KLA:TB500.INT764@6322:1")]
    (lst,) = screen(kla, meta("K1"), [["lotHtml"]], state={"view": "lot"})
    assert "TB500.INT764" in lst and "@6322" in lst


def test_lot_tab_tags_retries_rescans_and_lists_every_wafer():
    """구분: 앞 시도가 PASS 가 아니면 재시도, PASS 였던 같은 검사는 재스캔(이름 바뀜 구분), 첫 검사 · 다른 Job 은 글자를 적지 않는다. Wafer × 검사는 늘 Wafer 마다 한 줄(10/24 '같은 이력 묶기' 삭제)."""
    ids = [f"GRP{i:06d}X" for i in range(4)]
    rows = [w("AOI-1", i, "00:10", "00:20", lot="DBM-1", report="a.htm", status="Alignment Error.") | {"recipe": "x20"} for i in ids] + \
           [w("AOI-1", i, "02:10", "02:20", lot="DBM-1", report="b.htm") | {"recipe": "x20"} for i in ids] + \
           [w("AOI-1", i, "04:10", "04:20", lot="DBM-2", report="c.htm") | {"recipe": "x20"} for i in ids]
    lst = _lot_screen(rows)
    (k,) = _lot_keys(lst)
    out = _lot_screen(rows, k)
    assert "재시도" in out and "재스캔(이름 바뀜)" in out and "재검사" not in out.split("<h1>스캔을 어디에 했니?</h1>")[-1]
    assert "첫 검사" not in out and "다른 Job" not in out and "한 장 = 한 줄" not in out      # 10/25: 첫 검사 · 다른 Job 은 적지 않는다
    assert "같은 이력" not in out and out.count('class="lw mono') == 4


def test_scan_share_counts_only_rows_with_scan_sec_and_keeps_utilization():
    """10/11(D86 Q5): 장비-일 `sc` = [실제 촬영 분, 그 장들의 INI 분] — scan_sec 이 있는 장만. 가동률(r)은 그대로, 팝업 Scan 카드 밑에 '그중 스캔 n%'."""
    rows = [w("AOI-1", "W1", "08:00", "08:20") | {"scan_sec": "900"},       # 20분 중 15분
            w("AOI-1", "W2", "08:20", "08:40") | {"scan_sec": "600"},       # 20분 중 10분
            w("AOI-1", "W3", "08:40", "09:00")]                              # 옛 행 — 분모에도 넣지 않는다
    t = at(run(rows), "AOI-1")
    assert t["sc"] == [25, 40, 2, 3] and t["r"] == 60                     # 10/24: 근거 장 수 — 3장 중 2장
    assert at(run([w("AOI-1", "W3", "08:40", "09:00")]), "AOI-1")["sc"] == [0, 0, 0, 1]   # 옛 행만 — 비율 없음, '채우기 전'
    (pop,) = screen(rows, meta("AOI-1"), [["devPopupHtml"]], state={"modalDev": "AOI-1", "modalDayI": 0})
    assert "그중 스캔 63% · 근거 2/3장" in pop
    (pop,) = screen(rows[:2], meta("AOI-1"), [["devPopupHtml"]], state={"modalDev": "AOI-1", "modalDayI": 0})
    assert "그중 스캔 63%<" in pop and "근거" not in pop                    # 다 채워지면 비율만
    (pop,) = screen(rows[2:], meta("AOI-1"), [["devPopupHtml"]], state={"modalDev": "AOI-1", "modalDayI": 0})
    assert "스캔 비율 없음" in pop and "채우기 전" not in pop   # 11/25 UTIL-20: 문제가 아니라 값이 없을 뿐 — 회색 보통 글씨
    (line,) = screen(rows, meta("AOI-1"), [["scLine", {"sc": [0, 0, 1, 1]}]])   # INI 분이 반올림으로 0 — 'NaN%' 대신 비움(PR #3 리뷰)
    assert line == ""


def test_lot_tab_merges_one_char_ocr_misreads_but_not_other_wafers():
    """10/24(LNF): K1 이 38135G04EWB7 을 48135G04EWB7 로 읽어 합치면 26장 → Lot 이 둘로 갈렸다. 양쪽에만 있는 ID 가 한 글자만 다르면 같은 Wafer 로 묶고
    'ID 판독 차이' 로 남긴다. 두 글자 이상 다르면(다른 Wafer) 여전히 25장 넘게 합치지 않는다."""
    good = [f"38135G{i:02d}EWB7" for i in range(25)]
    typo = ["48135G04EWB7" if x == "38135G04EWB7" else x for x in good]
    rows = [w("K1", x, "00:10", "00:20", lot="TB500.INT795@6412", report="KLA:a") for x in typo] + \
           [w("AOI-20", x, "02:10", "02:20", lot="LNF-PIDS3", report="b.htm") for x in good]
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    assert "ID 판독 차이 1" in out and "48135G04EWB7 → 38135G04EWB7" in out and "25 wafer" in out
    assert out.split("Slot map &amp; 스캔 기록")[1].count('class="lw mono') == 25                    # 한 장은 한 줄
    other = ["99999X04EWB7" if x == "38135G04EWB7" else x for x in good]                  # 세 글자 넘게 다름 → 다른 Wafer
    rows2 = [w("K1", x, "00:10", "00:20", lot="TB500.INT795@6412", report="KLA:a") for x in other] + \
            [w("AOI-20", x, "02:10", "02:20", lot="LNF-PIDS3", report="b.htm") for x in good]
    assert len(_lot_keys(_lot_screen(rows2))) == 2


def test_lot_tab_matrix_cells_show_defect_counts():
    """10/25: Wafer × 검사 칸에 Defect 개수 — 1000 이상은 1.2k, 쉼표가 든 원문도 숫자로 읽는다. 값이 없으면 칸은 비워 둔다(지어내지 않는다)."""
    ids = ["DEF00001X", "DEF00002X", "DEF00003X"]
    rows = [w("AOI-1", ids[0], "00:10", "00:20", lot="DEF-1", report="a.htm") | {"faults": "7"},
            w("AOI-1", ids[1], "00:20", "00:30", lot="DEF-1", report="a.htm") | {"faults": "1,234"},
            w("AOI-1", ids[2], "00:30", "00:40", lot="DEF-1", report="a.htm")]
    (k,) = _lot_keys(_lot_screen(rows))
    mx = _lot_screen(rows, k).split("Slot map &amp; 스캔 기록")[1]
    assert ">7</i>" in mx and ">1.2k</i>" in mx


def _lot_pick(rows, title, mk=None, **st):
    """제목이 `title` 인 Lot 을 골라 그린 화면(목록에서 data-key 로 찾는다)."""
    lst = _lot_screen(rows, **({"lotMk": mk} if mk else {}))
    k = next(k for k in _lot_keys(lst) if f'<b class="mono">{title}<' in lst.split(f'lp:lot:{k}"')[1].split("</button>")[0])
    return _lot_screen(rows, k, **st)


def _att(dev, ids, s, *, lot, report, status=None, day=DAY, **kw):
    """한 Report(시도) — Wafer 마다 1분씩."""
    out = []
    for i, x in enumerate(ids):
        a = _hhmm(s, i)
        out.append(w(dev, x, a, _hhmm(s, i + 1), lot=lot, report=report, status=(status or {}).get(x, "Pass"), bs=s, be=_hhmm(s, len(ids) + 2), day=day) | kw)
    return out


def test_lot_tab_ocr_aliases_never_cycle_and_prefer_the_first_or_camtek_read():
    """11/25(LOTB-01 · 09 · 04): 판독이 장비마다 번갈아 달라도(Camtek X · KLA Y · Camtek X · KLA Y) 별칭은 대표 ID 끼리만 이어 고리가 없다 — 모든 시도가 25장.
    대표는 횟수가 같으면 Camtek 판독, 잘못 읽힌 장도 같은 열쇠라 재스캔이다."""
    full = [f"LNFW{i:02d}X1" for i in range(25)]
    mis = ["LNFV07X1" if x == "LNFW07X1" else x for x in full]
    rows = _att("AOI-1", full, "01:00", lot="LNF", report="a.htm") + _att("K1", mis, "02:00", lot="LNF@6322", report="KLA:b") + \
        _att("AOI-1", full, "03:00", lot="LNF", report="c.htm") + _att("K1", mis, "04:00", lot="LNF@6322", report="KLA:d")
    out = _lot_pick(rows, "LNF")
    assert out.count('class="lotatt"') == 4 and out.count('25<small class="muted">/25</small>') == 4
    assert "LNFV07X1 → LNFW07X1" in out
    re_rows = _att("AOI-1", full, "01:00", lot="LNF", report="a.htm") + _att("AOI-2", mis, "02:00", lot="LNF", report="b.htm")
    out = _lot_pick(re_rows, "LNF")
    assert "같은 Job 다른 단계" not in out and ">재스캔</span>" in out   # 잘못 읽힌 한 장도 재스캔(대표 ID 로 열쇠)


def test_lot_tab_orders_attempts_by_batch_start_and_follows_the_model_rescan_key():
    """11/25(LOTB-02 · 03): 시도의 시각은 Report 의 배치 시작 — Error 뒤 곧 재검사해 앞 Report 행이 뒤 INI 시각을 가져도 순서가 뒤집히지 않는다.
    레시피만 바꾼 재검사(x20|x5 → x20)는 가동률 모델처럼 재스캔이다(다른 단계가 아니다)."""
    a = [w("AOI-1", "DUPW01X1", "10:11", "10:13", lot="D37", report="a.htm", status="Alignment Error.", bs="10:00", be="10:05")]
    b = [w("AOI-1", "DUPW02X1", "10:09", "10:10", lot="D37", report="b.htm", bs="10:08", be="10:40"),
         w("AOI-1", "DUPW01X1", "10:11", "10:13", lot="D37", report="b.htm", bs="10:08", be="10:40")]
    out = _lot_pick(a + b, "D37")
    first, second = out.split('class="lotatt"')[1:3]
    assert "ALIGN_ERROR" in first and "10:00" in first and "10:08" in second and "재시도" in second
    ids = [f"MSAA{i:02d}X1" for i in range(5)]
    rows = _att("AOI-1", ids, "01:00", lot="MS", report="a.htm", recipe="x20|x5") + _att("AOI-2", ids, "03:00", lot="MS", report="b.htm", recipe="x20")
    out = _lot_pick(rows, "MS")
    assert "같은 Job 다른 단계" not in out and ">재스캔<" in out


def test_lot_tab_links_attempts_only_when_most_wafers_overlap():
    """11/25(LOTB-05 · 11, D92 · D95 조건 추가): 그 Lot 의 마지막 스캔에서 7일 넘게 지난 시도는 작은 쪽 Wafer 의 절반 이상이 겹칠 때만 잇는다 —
    ID 한 장만 겹친 두 Lot(몇 주 뒤 다시 쓰인 ID)은 '겹침' 으로 남는다. 가까운 시도(나눠 스캔 · DIA 몇 장)는 겹침이 적어도 잇는다.
    형제 Wafer(한 글자 차이)가 섞인 재검사 카세트는 판독 차이로 짝짓지 않는다."""
    aug = [f"AUGA{i:02d}X1" for i in range(10)]
    octb = [f"OCTB{i:02d}X1" for i in range(9)] + [aug[0]]
    rows = _att("AOI-1", aug, "01:00", lot="TSX", report="a.htm", day="2026-09-01") + _att("AOI-2", octb, "05:00", lot="TSX", report="b.htm")
    assert len(_lot_keys(_lot_screen(rows))) == 2
    near = _att("AOI-1", aug, "01:00", lot="TSX", report="a.htm") + _att("AOI-2", octb, "05:00", lot="TSX", report="b.htm")
    assert len(_lot_keys(_lot_screen(near))) == 1                         # 같은 날 나눠 스캔한 것은 그대로 잇는다
    rescan = _att("AOI-1", aug, "01:00", lot="TSX", report="a.htm", day="2026-09-01") + _att("AOI-2", aug[:3], "05:00", lot="TSX-RE", report="b.htm")
    assert len(_lot_keys(_lot_screen(rescan))) == 1                       # 재검사(전부 겹침)는 멀어도 잇는다
    P = [f"ABC12{i:02d}X" for i in range(1, 26)]
    Q = [f"ABC13{i:02d}X" for i in range(1, 26)]
    mixed = _att("AOI-1", P, "01:00", lot="PPP", report="a.htm") + _att("AOI-2", Q, "03:00", lot="QQQ", report="b.htm") + \
        _att("AOI-3", ["ABC1202X", "ABC1301X"], "06:00", lot="PPP-RE", report="c.htm")
    out = _lot_pick(mixed, "PPP")
    assert "ID 판독 차이" not in out and "25 wafer" in out


def test_lot_tab_counts_rows_it_cannot_group_and_duplicate_ids():
    """11/25(LOTB-06 · 10): Wafer ID 를 못 읽은 행은 묶지 않지만 'ID 없음 n(Error n)' 으로 세고, 행이 하나도 안 남은 Report 도 이름 검색에 나온다.
    한 Report 에 같은 ID 가 두 줄이면 둘 다 센다."""
    ids = ["IDOK01X1", "IDOK02X1", "IDOK03X1", "IDOK04X1"]
    rows = _att("AOI-1", ids + ["Slot 5"], "01:00", lot="SHORT", report="a.htm", status={"Slot 5": "Failed to read wafer id. Wafer Skipped."}) + \
        _att("AOI-1", ["123456", "AB12"], "03:00", lot="WEIRD-1", report="b.htm")
    out = _lot_pick(rows, "SHORT")
    assert "ID 없음 1(Error 1)" in out
    lst = _lot_screen(rows, lotQ="weird 1")
    assert "Wafer ID 없음 — 묶지 않음" in lst and "WEIRD-1" in lst
    dup = _att("AOI-1", [f"DUPR{i:02d}X1" for i in range(4)], "01:00", lot="DR", report="a.htm") + \
        [w("AOI-1", "DUPR01X1", "01:20", "01:21", lot="DR", report="a.htm", status="Alignment Error.", bs="01:00", be="01:30")]
    out = _lot_pick(dup, "DR")
    assert '4<small class="muted">/5</small>' in out and "같은 ID 중복 1" in out


def test_lot_tab_cards_count_distinct_wafers_and_skip_test_errors():
    """11/25(LOT-01 · LOTB-07 · 08): Error · 재스캔 카드는 서로 다른 wafer 수(스캔 횟수는 밑줄), Test 스캔의 Error 는 세지 않는다(D64).
    Camtek+KLA 를 거친 Lot 은 두 필터 모두에 나오고 Defect 는 나눠 적는다."""
    ids = [f"ERRW{i:02d}X1" for i in range(4)]
    bad = {ids[0]: "Alignment Error.", ids[1]: "Alignment Error."}
    rows = _att("AOI-1", ids, "01:00", lot="ERR", report="a.htm", status=bad) + _att("AOI-1", ids, "03:00", lot="ERR", report="b.htm", status=bad)
    out = _lot_pick(rows, "ERR")
    assert '<p class="v num">2 wafer</p><p class="s">스캔 2번에서 4건</p>' in out
    assert 'data-lt="0|ERRW00X1"' in out and "Defect" not in out.split('data-lt=')[1][:80]   # 칸 설명은 올릴 때 만든다(LOTD-07)
    tst = _att("AOI-1", ids, "01:00", lot="ABC_TEST", report="a.htm", status={ids[0]: "Alignment Error."})
    lst = _lot_screen(tst)
    assert 'class="bad e"' not in lst
    mix = _att("AOI-1", ids, "01:00", lot="TB500.INT764", report="a.htm", faults="300") + \
        _att("K2", ids, "03:00", lot="TB500.INT764@6322", report="KLA:b", faults="40")
    for mk in ("cam", "kla"):
        assert len(_lot_keys(_lot_screen(mix, lotMk=mk))) == 1, mk
    assert "1,200 · 160" in _lot_pick(mix, "TB500.INT764")


def test_lot_tab_search_ignores_separators_and_finds_devices():
    """11/25(LOTA-01 · 03): 'vxx 3d' 로도 'VXX-3D EDGE' 를 찾고, 입력이 장비 이름(AOI-2 · aoi2)과 같으면 그 장비에서 스캔한 LOT 을 최근 순으로 맨 위에."""
    ids = [f"VXXA{i:02d}X1" for i in range(3)]
    old = [f"OLDA{i:02d}X1" for i in range(3)]
    rows = _att("AOI-2", old, "01:00", lot="OLD-1", report="a.htm") + _att("AOI-2", ids, "05:00", lot="VXX-3D EDGE", report="b.htm") + \
        _att("AOI-1", [f"ZZZA{i:02d}X1" for i in range(3)], "07:00", lot="AOI2-NAME", report="c.htm")
    for q in ("vxx 3d", "VXX3D", "vxx_3d edge"):
        assert len(_lot_keys(_lot_screen(rows, lotQ=q))) == 1, q
    lst = _lot_screen(rows, lotQ="aoi2")
    assert "장비 AOI-2 에서 스캔한 LOT" in lst
    ks = _lot_keys(lst)
    assert len(ks) == 3                                                     # 장비 묶음 2개 + 이름 결과 1개
    names = [lst.split(f'lp:lot:{k}"')[1].split("</b>")[0].rsplit(">", 1)[-1] for k in ks]
    assert names == ["VXX-3D EDGE", "OLD-1", "AOI2-NAME"]                   # 장비 묶음은 최근 순, 그 아래 이름 결과


def test_kla_tb500_job_names_are_shortened_for_display_only():
    """KLA TB500 SetupID 표기(10/25): 공통 접두와 끝의 장비 표시 _K#(장비 이름) 을 떼고 원문 낱말 순서 그대로 적는다(SEQ 는 TB500 앞). 모르는 모양은 null(원문 유지)."""
    pre = "ROOT-HVM-4DT-TB500-H-M1-"
    want = {
        "RDL3_K2": "TB500 RDL3", "RDL1_K1": "TB500 RDL1", "RDL4_K1_NEW": "TB500 RDL4 NEW", "RDL2_NEW": "TB500 RDL2 NEW",
        "RDL4_AUTO_RBB": "TB500 RDL4 AUTO_RBB",
        "SEQ_TB500_RDL1_K5": "SEQ TB500 RDL1", "SEQ_TB500_RDL1_(M)_K5": "SEQ TB500 RDL1 Multi",
        "SEQ_TB500_RDL1_(MULTI)": "SEQ TB500 RDL1 Multi", "SEQ_TB00_RDL1_(MULTI)_K2": "SEQ TB500 RDL1 Multi",   # TB00 은 원문 오타
        "SEQ_TB500_RDL3_(MULTI)_K2": "SEQ TB500 RDL3 Multi",
    }
    calls = [f"klaJobAlias({json.dumps(pre + k)})" for k in want]
    calls += ['klaJobAlias("ROOT-HVM-KLA-ONLY-SETUP")', 'klaJobAlias("TB500_RDL3 - Multi")', f'klaJobAlias({json.dumps(pre + "PI3")})', 'klaJobAlias("")']
    got = globals_(*calls)
    for k, v in want.items():
        assert got[f"klaJobAlias({json.dumps(pre + k)})"] == v, k
    assert got['klaJobAlias("ROOT-HVM-KLA-ONLY-SETUP")'] is None and got['klaJobAlias("TB500_RDL3 - Multi")'] is None
    assert got[f'klaJobAlias({json.dumps(pre + "PI3")})'] is None and got['klaJobAlias("")'] is None
    # 이 함수는 KLA 표기 전용 — Camtek 표기명(jobAlias)에는 끼지 않는다(TB500 · Kendall 탭이 KLA Job 을 끌어오지 않게)
    html = (ROOT / "aoi_capacity" / "ui" / "assets" / "template.html").read_text(encoding="utf-8")
    assert "function jobAlias(raw){if(JOB_ALIAS[raw])return JOB_ALIAS[raw];const m=" in html and "klaJobAlias" not in html.split("function jobAlias")[1].split("\n")[0]


def test_report_tab_leaves_out_a_batch_whose_time_per_wafer_is_far_from_its_group():
    """10/30(사용자 선택 B): 08/23 7DH-3D RE — 5장 모두 PASS 인데 장당 1.7분(같은 Job 보통 3.9분). 같은 Job 의 장당 시간 중앙(DIA Lot 끼리 · 그 밖끼리)의
    0.5배 미만은 표본에서 뺀다(느린 쪽은 남김). 정상 배치 5개의 회귀는 그대로, DIA Lot 은 자기 무리(느린 쪽 중앙이 아니라)로 잰다."""
    rows = _clean_batches(5)                                    # 5~9장, 배치시간 10 + 5×장수 → 장당 7.0~6.1분
    bs = "20:00"
    rep = "R_TB500_LIVE_PI3_6321_LOT-F_18-Sep-26_(20.00.00)_BatchReport.htm"
    for k in range(5):                                          # 5장 9분 → 장당 1.8분
        rows.append(w("AOI-1", f"F{k}", _hhmm(bs, k + 1), _hhmm(bs, k + 2), lot="LOT-F", job="R_TB500_LIVE_PI3", report=rep, bs=bs, be=_hhmm(bs, 9)))
    rep2 = "R_TB500_LIVE_PI3_6321_LOT-G_18-Sep-26_(17.00.00)_BatchReport.htm"
    for k in range(5):                                          # 5장 150분 → 장당 30분: 느린 쪽은 남긴다(느린 장비의 신호 — 30일치 전수조사에서 AOI-1)
        rows.append(w("AOI-1", f"G{k}", _hhmm("17:00", k + 1), _hhmm("17:00", k + 2), lot="LOT-G", job="R_TB500_LIVE_PI3", report=rep2, bs="17:00", be=_hhmm("17:00", 150)))
    dia = []                                                    # DIA Lot 5개: 장당 2분 — 그 밖 무리 중앙(~6.5분)으로 재면 전부 빠질 값
    for i in range(5):
        lot = f"D{i}-DIA"
        s0 = f"{21 + (i % 2):02d}:{i * 10:02d}"
        r2 = f"R_TB500_LIVE_PI3_6321_{lot}_18-Sep-26_({s0.replace(':', '.')}.00)_BatchReport.htm"
        for k in range(6):
            dia.append(w("AOI-1", f"X{i}{k}", _hhmm(s0, k + 1), _hhmm(s0, k + 2), lot=lot, job="R_TB500_LIVE_PI3", report=r2, bs=s0, be=_hhmm(s0, 12)))
    html, popup = screen(rows + dia, meta("AOI-1"), [["reportHtml"], ["rptDevPopupHtml"]],
                         state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert popup.count('title="제외 — 장당') == 1                      # 빠른 쪽(LOT-F) 하나만 이상치로 뺀다
    assert "제외 — 장당 1.8분, 이 장비 DIA 아닌 Lot 중앙" in popup
    g_row = popup[popup.index("LOT-G"):]
    assert "표본" in g_row[:g_row.index("</div>")]                # 느린 쪽(장당 30분)은 표본으로 남는다


def test_report_tab_judges_time_per_wafer_within_each_device_not_across_the_fleet():
    """10/30 실데이터 점검: Kendall BS 비DIA 중앙이 AOI-1 10.5분 · AOI-15 3.9분이라 장비를 가로질러 중앙을 재면 AOI-15 의 정상 배치 34개 중 31개가 이상치로 빠졌다.
    장당 시간은 그 장비의 같은 종류 중앙으로 잰다 — 느린 장비가 있어도 빠른 장비의 평소 배치는 표본에 남는다."""
    rows = _clean_batches(5)                                    # AOI-1: 장당 6.1~7.0분
    for i in range(5):                                          # AOI-2: 6장 180분 = 장당 30분(AOI-1 의 4배 이상)
        bs = f"{8 + 3 * i:02d}:00"
        lot = f"SLOW-{i + 1}"
        rep = f"R_TB500_LIVE_PI3_6321_{lot}_18-Sep-26_({bs.replace(':', '.')}.00)_BatchReport.htm"
        for k in range(6):
            rows.append(w("AOI-2", f"S{i}{k}", _hhmm(bs, k + 1), _hhmm(bs, k + 2), lot=lot, job="R_TB500_LIVE_PI3", report=rep, bs=bs, be=_hhmm(bs, 180)))
    (popup,) = screen(rows, meta("AOI-1", "AOI-2"), [["rptDevPopupHtml"]],
                      state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert 'title="제외 — 장당' not in popup                           # 전체 중앙(약 18분)의 0.5배 = 9분이어도 AOI-1 의 6~7분 배치는 빠지지 않는다
    assert popup.count("표본") >= 5


def test_report_tab_keeps_batches_apart_when_the_report_name_is_empty():
    """PR #11 리뷰: Report 이름이 빈 행은 풀 번호가 같아도 같은 Report 가 아니다 — 합치면 Lot 이 다른 정상 배치 5개가 한 배치가 되어 회귀 표본이 사라진다."""
    rows = _clean_batches(5)
    for r in rows:
        r["report"] = ""
    (popup,) = screen(rows, meta("AOI-1"), [["rptDevPopupHtml"]],
                      state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert "배치 5개" in popup


def test_report_tab_reads_dia_after_an_underscore():
    """실데이터에는 HWH_DIA · DIA_1023S 처럼 밑줄 이웃의 DIA 가 있다 — 낱말 경계(\\b)는 밑줄을 글자로 봐서 놓쳤다. DIA 무리로 읽어 자기 무리 중앙으로 잰다."""
    rows = []
    for i in range(5):                                          # 장당 2분 — DIA 무리
        bs = f"{8 + 2 * i:02d}:00"
        lot = f"H{i}_DIA"
        rep = f"R_TB500_LIVE_PI3_6321_{lot}_18-Sep-26_({bs.replace(':', '.')}.00)_BatchReport.htm"
        for k in range(6):
            rows.append(w("AOI-1", f"D{i}{k}", _hhmm(bs, k + 1), _hhmm(bs, k + 2), lot=lot, job="R_TB500_LIVE_PI3", report=rep, bs=bs, be=_hhmm(bs, 12)))
    rows += _clean_batches(5)                                   # 일반 Lot: 장당 6~7분 — 한 무리로 섞이면 DIA 가 절반 아래
    (popup,) = screen(rows, meta("AOI-1"), [["rptDevPopupHtml"]],
                      state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert 'title="제외 — 장당' not in popup


def test_report_tab_counts_a_batch_that_crosses_midnight_once():
    """10/30 전수조사: 자정을 걸친 Report 가 하루씩 둘로 잘려 표본에 두 번 들어갔다(30일치 샘플에서 Report 의 6.5%). 한 배치로 합쳐 장수 12 · 시간 3시간 30분."""
    rep = "R_TB500_LIVE_PI3_6321_LOT-M_17-Sep-26_(22.00.00)_BatchReport.htm"
    bs, be = ts("2026-09-17", "22:00"), ts("2026-09-18", "01:30")
    rows = []
    for k in range(6):                                                    # 17일 밤: 6장
        rows.append(w("AOI-1", f"M{k}", _hhmm("22:00", 10 + 25 * k), _hhmm("22:00", 30 + 25 * k), lot="LOT-M", job="R_TB500_LIVE_PI3", report=rep, day="2026-09-17") | {"batch_start": bs, "batch_end": be})
    for k in range(6, 12):                                                # 18일 새벽: 6장
        rows.append(w("AOI-1", f"M{k}", _hhmm("00:00", 5 + 14 * (k - 6)), _hhmm("00:00", 15 + 14 * (k - 6)), lot="LOT-M", job="R_TB500_LIVE_PI3", report=rep, day="2026-09-18") | {"batch_start": bs, "batch_end": be})
    (popup,) = screen(rows, meta("AOI-1"), [["rptDevPopupHtml"]], state={"view": "report", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert popup.count("LOT-M</span>") == 1                                # 두 줄이 아니라 한 줄
    assert "배치 1개" in popup and "12장" in popup and "3시간 30분" in popup and "22:00 – 01:30" in popup
    assert "제외 — PASS 5장 미만" not in popup                              # 조각(6장 · 6장)이 아니라 합친 12장으로 판단


def _batch(dev, lot, bs, n, minutes, job="R_TB500_LIVE_PI3"):
    rep = f"{job}_6321_{lot}_18-Sep-26_({bs.replace(':', '.')}.00)_BatchReport.htm"
    return [w(dev, f"{lot}-{k}", _hhmm(bs, k + 1), _hhmm(bs, k + 2), lot=lot, job=job, report=rep, bs=bs, be=_hhmm(bs, minutes)) for k in range(n)]


def test_report_popup_marks_slow_batches_by_time_per_wafer_not_by_batch_length():
    """11/25 RDL-04: 빨간 시간은 배치 시간이 아니라 장당 시간(÷ PASS 장 수)을 이 장비 표본 중앙과 비교한다 —
    25장 배치(135분, 장당 5.4분)는 길어도 빨강이 아니고, 6장 60분(장당 10분)은 빨강."""
    rows = _clean_batches(5) + _batch("AOI-1", "LOT-BIG", "17:00", 25, 135) + _batch("AOI-1", "LOT-SLOW", "20:00", 6, 60)
    (popup,) = screen(rows, meta("AOI-1"), [["rptDevPopupHtml"]], state={"view": "report", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    row = lambda lot: next(x for x in popup.split('class="rcpdev"') if lot in x)
    assert "font-weight:600;color:" not in row("LOT-BIG</span>")
    assert "font-weight:600;color:" in row("LOT-SLOW</span>") and "장당 10.0분" in row("LOT-SLOW</span>")
    assert "장당 시간 중앙" in popup


def test_report_tab_leaves_test_lot_batches_out_and_lets_uncomputed_devices_open_all_batches():
    """11/25 RDL-18(현택): 시험(Test) Lot 의 배치는 장비 비교 표본에서 뺀다(이유는 팝업에 그대로).
    RDL-05: 계산 못 한 장비 이름은 단추 — 누르면 그 장비의 모든 배치 팝업, 괄호에 제외 내역."""
    rows = _clean_batches(5) + _batch("AOI-1", "X1-TEST", "20:00", 6, 40) + _clean_batches(4)
    for r in rows[-sum(5 + i for i in range(4)):]:
        r["device"] = "AOI-2"
    html, popup = screen(rows, meta("AOI-1", "AOI-2"), [["reportHtml"], ["rptDevPopupHtml"]],
                         state={"view": "report", "rptDev": "AOI-1", "rptAll": {"job": "TB500 PI3", "dev": "AOI-1"}})
    assert "5 / 6" in html and "시험(Test) 1" in html and "10.0 ± 0.0분" in html
    assert "제외 — 시험(Test) Lot" in popup
    bad = html[html.index("계산 못 한 장비 1대"):]
    assert '<button type="button" class="link" data-h=' in bad[:400] and ">AOI-2</button>(표본 4개 · 5개 미만)" in bad


def _okw(dev, wafer, s, faults, **kw):
    r = w(dev, wafer, s, s[:3] + "09", **kw)
    r["faults"] = faults
    return r


def test_overkill_day_counts_pass_and_max_fault_and_lists_only_devices_with_overkill():
    """D99: 400↑ = 오버킬, 1,000↑ · 'Scan 2D - Max Fault Exceeded.' = 심한 오버킬. 분모 = PASS(Defect 있음) + 상한 초과, Error · Test 는 제외. 하루 조회는 난 장비만."""
    rows = [_okw("AOI-1", "W1", "08:00", "100"), _okw("AOI-1", "W2", "08:10", "500"), _okw("AOI-1", "W3", "08:20", "1,500"),
            _okw("AOI-1", "W4", "08:30", "-", status="Scan 2D - Max Fault Exceeded."),
            _okw("AOI-1", "W5", "08:40", "", status="Alignment Error."),
            _okw("AOI-1", "T1", "09:00", "2000", lot="TEST-LOT"),
            _okw("AOI-2", "V1", "10:00", "50", lot="LOT-B")]
    (html,) = screen(rows, meta("AOI-1", "AOI-2"), [["okHtml"]])
    assert ">60%<" in html and "400개 이상 3장 / 5장" in html          # 500 · 1,500 · 상한 초과 / PASS 4(AOI-2 포함) + 상한 초과 1
    assert ">75%<" in html and "오버킬 3 / 4장 · 심한 2" in html        # AOI-1 줄
    assert ">2장<" in html and "상한 초과 1장 포함" in html
    assert "제외 2장" in html                                             # Alignment Error · TEST Lot
    assert 'data-key="okd:AOI-1"' in html and 'data-key="okd:AOI-2"' not in html   # 오버킬이 난 장비만
    assert "상한 초과 1" in html and "1,500" in html                      # LOT 줄: 표 · 최대 Defect(쉼표 원문도 읽음)
    (sev,) = screen(rows, meta("AOI-1", "AOI-2"), [["okHtml"]], state={"okTier": "sev"})
    assert ">50%<" in sev and "심한 오버킬 기준" in sev                  # 심한 단계: 목록 순위·비율이 심한 기준(AOI-1 2 / 4), 카드 1은 늘 400↑


def test_overkill_scope_follows_model_test_rule_own_maker_buttons_and_selected_day():
    """리뷰(PR #9): ① Lot 에 TEST 가 붙어 있으면(TEST_LOT 처럼 밑줄이어도) 모델처럼 Test 로 빼고 ② 다른 탭의 Gen5 를 물려받지 않으며
    ③ 자정을 넘긴 Report 도 고른 날의 장만으로 LOT 줄을 만든다(합계에 오버킬이 있는데 LOT 줄이 없던 것)."""
    prev = (datetime.date.fromisoformat(DAY) - datetime.timedelta(days=1)).isoformat()
    rep = "J1_6321_LOT-N_night_BatchReport.htm"
    rows = [_okw("AOI-1", "N1", "23:50", "10", day=prev, report=rep, lot="LOT-N"),
            _okw("AOI-1", "N2", "00:10", "900", report=rep, lot="LOT-N"),
            _okw("AOI-1", "T1", "09:00", "2000", lot="TEST_LOT")]
    (html,) = screen(rows, meta("AOI-1", "AOI-2"), [["okHtml"]], state={"maker": "g5", "okMk": "cam"})
    assert "400개 이상 1장 / 1장" in html                                  # TEST_LOT 은 분모에도 없다 · 전날 장은 이 날이 아니다
    assert 'data-key="okd:AOI-1"' in html                                  # Gen5 가 아닌 장비도 보인다
    assert f'data-key="okl:AOI-1|{rep}"' in html                           # 자정 넘긴 Report 의 LOT 줄이 이 날에 있다


def test_overkill_period_ranks_jobs_and_defaults_to_camtek():
    """기간 조회는 Job별 순위(오버킬 난 것만) + 고른 Job 의 날짜별 막대 · 장비 · LOT. 장비 종류 기본은 Camtek(KLA 는 단추로)."""
    rows = [_okw("AOI-1", "A1", "08:00", "900", job="TB500_RDL3 - Multi"), _okw("AOI-1", "A2", "08:10", "10", job="TB500_RDL3 - Multi"),
            _okw("AOI-2", "B1", "09:00", "20", job="R_TB500_LIVE_PI3", lot="LOT-B"),
            _okw("K1", "C1", "10:00", "5000", job="ROOT-HVM-4DT-TB500-H-M1-RDL3_K1", lot="KL@6322")]
    mt = meta("AOI-1", "AOI-2", more=[{"name": "K1", "note": "Y:\\", "report_dir": "", "status": "ok", "kind": "kla"}])
    (cam, kla) = screen(rows, mt, [["okHtml"], ["okHtml"]], state={"okMode": "span"})
    assert "TB500_RDL3 - Multi" in cam and "오버킬 난 1개" in cam and "없는 1개 숨김" in cam
    assert "이 Job 을 돈 장비" in cam and "RDL3_K1" not in cam
    (k,) = screen(rows, mt, [["okHtml"]], state={"okMode": "span", "okMk": "kla"})
    assert "TB500 RDL3" in k                                              # KLA Job 은 화면 표기(D96)


def test_device_popup_follows_the_list_order_and_separates_no_record_from_idle():
    """11/25 점검(UTIL-03·04·05·08·11·14 · JS-10 · COPY-14): 팝업 ‹ › 는 목록과 같은 필터 · 정렬, 기록 없는 장비는 대기도 '—' 와 한 줄 설명,
    Error 카드는 '건' 만 크게, 자정 넘긴 배치의 둘째 날 이름표는 '전날부터', 값 있는 장비가 없으면 평균 '—'(0% 아님)."""
    rows = [w("AOI-1", "W1", "08:00", "10:00"), w("AOI-2", "W2", "09:00", "09:30", status="Alignment Error."),
            w("4F-AOI-01", "W3", "10:00", "10:05"),
            w("AOI-1", "N1", "23:00", "23:40", lot="LOT-N", day="2026-09-17"), w("AOI-1", "N2", "23:40", "00:30", lot="LOT-N", day="2026-09-17", eday=DAY)]
    mt = meta("AOI-1", "AOI-2", "AOI-3", "4F-AOI-01")
    st = {"modalDev": "AOI-2", "modalDayI": 1}
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state=st)
    assert "‹ AOI-1" in pop and "AOI-3 ›" in pop and 'data-fk="dev:err"' in pop and "Error 1건 ›" in pop
    assert ">1건<" in pop and "1건 · " not in pop                                    # Error 시간은 카드 아래 작은 줄
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state=st | {"sort": "low"})        # 가동률 낮은 순: 기록 없는 AOI-3 은 맨 뒤
    assert "AOI-3 ›" not in pop
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state={"modalDev": "4F-AOI-01", "modalDayI": 1, "floor": "4"})
    assert "‹ " not in pop and "Error 없음 ›" in pop                                  # 4층만 걸면 앞뒤 장비도 4층 안에서
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state={"modalDev": "AOI-3", "modalDayI": 1})
    assert "이 날 기록이 없습니다 — 장비가 쉬었는지 수집이 안 됐는지" in pop and "24시간" not in pop
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state={"modalDev": "AOI-1", "modalDayI": 1})
    assert "LOT-N · 전날부터" in pop and "· 0장" not in pop
    (pop,) = screen(rows, mt, [["devPopupHtml"]], state={"modalDev": "AOI-1", "modalDayI": 1, "lotFilter": "err"})
    assert "Error 난 Lot 이 없습니다" in pop and "전체 Lot 보기" in pop and "이 날 이 장비의 기록이 없습니다" not in pop
    (home,) = screen(rows, mt, [["homeHtml"]], state={"maker": "kla", "dayI": 1})
    assert "이 조건(층 · 장비 종류)에 맞는 장비가 이 파일에 없습니다" in home and "0.0" not in home
    (home,) = screen(rows, mt, [["homeHtml"]], state={"sort": "low", "dayI": 1})
    assert home.index("기록 없음 1대") < home.index('data-row="dev:AOI-3"') and 'class="nobar"' in home


def _card(html, key):
    m = re.search(r'<p class="k"[^>]*>' + re.escape(key) + r'(?: <span class="ii"[^>]*>ⓘ</span>)?</p><p class="v num"[^>]*>(.*?)</p>', html)
    return re.sub(r"<[^>]+>", "", m.group(1)) if m else None


def test_error_filter_keeps_minutes_carried_past_midnight_and_job_denominator_is_the_same_for_every_metric():
    """11/25 점검(ERR-01 · ERR-02 · ERR-10): ① 유형 필터를 켜도 전날 Error 가 자정을 넘어 이어진 분(그날 건수 0 인 Lot)을 센다 —
    필터 없을 때와 같은 대기 시간 ② Job별 'Lot n개 중' 은 지표와 상관없이 전체 시도(Error 없던 장비-일 포함) ③ 건수 지표에도 Error 난 Job 만."""
    prev = (datetime.date.fromisoformat(DAY) - datetime.timedelta(days=1)).isoformat()
    rows = [w("AOI-1", "E1", "23:30", "00:20", lot="LOT-N", status="Alignment Error.", day=prev, eday=DAY),
            w("AOI-1", "E2", "08:00", "08:10", lot="LOT-B", status="Alignment Error."),
            w("AOI-2", "P1", "09:00", "09:10", lot="LOT-C"),
            w("AOI-1", "Q1", "10:00", "10:10", lot="LOT-D", job="J2")]
    st = {"view": "errors", "pickDay": None, "metric": "min"}
    (plain,) = screen(rows, meta("AOI-1", "AOI-2"), [["errorsHtml"]], state=st)
    (filt,) = screen(rows, meta("AOI-1", "AOI-2"), [["errorsHtml"]], state={**st, "errFType": "ALIGN_ERROR"})
    (cnt_,) = screen(rows, meta("AOI-1", "AOI-2"), [["errorsHtml"]], state={**st, "metric": "n"})
    (prob,) = screen(rows, meta("AOI-1", "AOI-2"), [["errorsHtml"]], state={**st, "metric": "prob"})
    assert _card(plain, "Error 대기") == _card(filt, "Error 대기") == "10시간 30분"   # 예전엔 필터를 켜면 자정 넘은 분이 빠져 줄었다(자정 넘은 분이 빠짐)
    assert 'class="errfbar"' in filt and "모두 해제" not in filt               # 필터 하나면 '모두 해제' 없이 칩만
    for h in (cnt_, prob):
        assert "Lot 4개 중 2개 Error" in h                                      # J1: 장비-일마다 한 시도 — AOI-2 의 PASS 시도도 분모에(예전 건수 지표는 3)
    assert cnt_.count('data-row="job:') == 1                                  # J2(Error 0건, Error 난 장비-일에서 돎)는 건수 지표에도 없다


def test_overkill_bar_draws_severe_first_and_lot_row_marks_rows_lot_tracking_cannot_open():
    """11/25 점검(ERR-05 · ERR-03 · ERR-20): 막대는 심한 칸부터(1,000↑ 기준이면 400~999 칸 없음) · Wafer ID 가 없어 '스캔을 어디에 했니?' 가 묶지 못하는 LOT 은 '열 수 없음'."""
    rows = [_okw("AOI-1", "WAFER0001", "08:00", "500"), _okw("AOI-1", "WAFER0002", "08:10", "1500"),
            _okw("AOI-2", "", "09:00", "800", lot="NOID")]
    (all_, sev) = (screen(rows, meta("AOI-1", "AOI-2"), [["okHtml"]])[0], screen(rows, meta("AOI-1", "AOI-2"), [["okHtml"]], state={"okTier": "sev"})[0])
    assert re.search(r'<span class="okbar"><i class="s"[^>]*></i><i class="o"', all_)
    assert re.search(r'<span class="okbar sev"><i class="s"[^>]*></i></span>', sev)
    assert "심한 1 / 2장 · 오버킬 2" in sev and "오버킬 2 / 2장 · 심한 1" in all_
    assert all_.count("열 수 없음") == 1 and 'class="rowbtn okl na"' in all_
