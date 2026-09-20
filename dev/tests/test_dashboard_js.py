"""결과 화면(template.html)의 모델 `buildModel` 을 Node 에서 **실제로 실행**해 검사한다(dev/tests/js_harness.js).

두 프로필이 있다:
- product(기본, MODEL_VERSION 3): D56(측정 우선 배타 배정 · 배치 창 균등 배분 · Error 담은 Report 끝 뒤가 대기) · D57(수집일 분모 = 모든 장비의 마지막 기록) ·
  D58(시각 없는 Error = 배치 창의 빈 시간) · D63(Rescan = 앞선 PASS 만) · D64(Test Lot 전부 Test) · D04(자정 분할) · D09(엄격 날짜).
- legacy: make_aoi_data.js [원본] 이식 — 네 스위치를 끄면 디자인 스크립트와 같은 출력(slow 가드). 제품 화면은 쓰지 않는다.
네트워크·NAS·쓰기 없음. Node 가 없으면 skip.
"""
from __future__ import annotations

import json
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
