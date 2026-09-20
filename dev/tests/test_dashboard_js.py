"""결과 화면(template.html)의 **모델**을 실제로 실행해 검사한다 — 문자열 검사만으로 '완료' 라고 하지 않는다.

`dev/tests/js_harness.js` 가 template 의 스크립트를 Node 의 vm 에서 돌려 `buildModel(rows, meta, rules)` 결과를 JSON 으로 낸다.
모델은 디자인 세션의 `docs/design/dashboard-redesign/scripts/make_aoi_data.js` [원본] 을 옮긴 것이라(D47), 제품 규칙 두 개(RULES)를 끄면
그 스크립트와 **같은 출력**이어야 한다(slow 테스트가 30일치로 확인). 나머지는 D48 의 각 규칙을 작은 fixture 로 하나씩 본다.
네트워크·파일 쓰기 없음. Node 가 없으면 skip.
"""
from __future__ import annotations

import gzip
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
DESIGN_RULES = {"waitToObsEnd": False, "denomToday": False}


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


def w(dev, wafer, s=None, e=None, *, lot="LOT-A", status="Pass", job="J1", report=None, day=DAY, bs=None, be=None, setup="6321"):
    """Wafer 행 하나. s/e 는 'HH:MM'(없으면 시각 미확인), bs/be 는 배치 구간. report 가 없으면 Lot 이름이 그대로 나오는 파일명을 만든다."""
    # 같은 장비·Job·Lot·날짜의 행은 같은 Report(= 한 배치)로 둔다 — 모델의 Lot 단위가 Report 이기 때문
    rep = report or f"{job}_{setup}_{lot}_{int(day[8:])}-Sep-26_(00.00.00)_BatchReport.htm"
    return {"device": dev, "kind": "", "job": job, "setup": setup, "lot": lot, "wafer_id": wafer, "status": status,
            "wafer_start_time": ts(day, s) if s else "", "wafer_end_time": ts(day, e) if e else "",
            "batch_start": ts(day, bs) if bs else (ts(day, s) if s else ""), "batch_end": ts(day, be) if be else (ts(day, e) if e else ""),
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


# ── 0. 디자인 스크립트와의 동일성 ─────────────────────────────────────────────
@pytest.mark.slow
def test_model_equals_the_design_script_when_the_two_product_rules_are_off(tmp_path):
    """★ 이식의 근거: 30일치 156,109행에서 833 장비-일의 r/x/t/d/s/e/seg/ct/lots/cv/bseg/be 와 pool·jobG·jobGroups 가 전부 같다."""
    import sys
    sys.path.insert(0, str(ROOT / "dev" / "tests"))
    import sample_rows
    html = gzip.decompress(SAMPLE.read_bytes()).decode("utf-8")
    emb = sample_rows.embedded(html)
    src = tmp_path / "in.html"
    src.write_text(html, encoding="utf-8")
    ref_p = tmp_path / "ref.json"
    r = subprocess.run([NODE, "--max-old-space-size=4096", str(DESIGN_SCRIPT), str(src), str(ref_p)], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stderr[-800:]
    ref = json.loads(ref_p.read_text(encoding="utf-8"))
    out = subprocess.run([NODE, "--max-old-space-size=4096", str(HARNESS)], input=json.dumps({"embedded": emb, "rules": DESIGN_RULES}),
                         capture_output=True, text=True, timeout=600, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr[-800:]
    mine = json.loads(out.stdout)
    assert mine["devices"] == ref["devices"] and mine["days"] == ref["days"]
    assert mine["pool"] == ref["pool"] and mine["jobG"] == ref["jobG"] and mine["jobGroups"] == ref["jobGroups"]
    bad = 0
    for dy, ds in ref["detail"].items():
        for dv, t in ds.items():
            m = dict(mine["detail"][dy][dv])
            m.pop("den", None)                       # 제품 쪽에만 있는 분모 열
            assert m.pop("we", 0) == 0               # 마지막 Error 뒤 대기 끝 — 디자인 규칙(cap·다음 기록 없으면 0)에서는 늘 0
            if m != t:
                bad += 1
    assert bad == 0


# ── 1. Error 는 Lot 단위 (D48-②) ────────────────────────────────────────────
def test_error_count_is_per_lot_and_type_not_per_wafer():
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error."),
            w("AOI-1", "W2", "08:05", "08:08", status="Alignment Error."),
            w("AOI-1", "W3", "08:10", "08:13", status="Scan 2D Error."),
            w("AOI-1", "W4", "09:00", "09:10")]
    t = at(run(rows), "AOI-1")
    assert t["e"] == 2                                   # ALIGN 1 + SCAN 1 (같은 Lot 의 같은 유형은 1건)
    assert t["ct"]["ALIGN_ERROR"][0] == 1 and t["ct"]["SCAN_ERROR"][0] == 1
    assert len(t["lots"]) == 1 and t["lots"][0][5] == 2   # Lot 행의 Error 수 = 유형 수


def test_two_different_lots_with_the_same_type_are_two_errors():
    rows = [w("AOI-1", "W1", "08:00", "08:03", lot="AAA", status="Alignment Error."),
            w("AOI-1", "W2", "09:00", "09:03", lot="BBB", status="Alignment Error.")]
    t = at(run(rows), "AOI-1")
    assert t["e"] == 2 and t["ct"]["ALIGN_ERROR"][0] == 2


# ── 2. 재스캔 정의 (D48-③): 앞선 Pass → Rescan(장비 무관), 앞선 Error → 정상 Scan ──
def test_a_second_attempt_after_a_pass_is_a_rescan_on_any_device():
    rows = [w("AOI-1", "W1", "08:00", "08:10"), w("AOI-2", "W1", "12:00", "12:10")]
    D = run(rows)
    a, b = at(D, "AOI-1"), at(D, "AOI-2")
    assert a["r"] == 10 and a["d"] == 0
    assert b["r"] == 0 and b["d"] == 10                  # 두 번째 시도는 Rescan 시간
    assert b["lots"][0][6] == 1                          # Lot 행의 Rescan 장수


def test_a_second_attempt_after_an_error_is_a_normal_scan():
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error."), w("AOI-1", "W1", "12:00", "12:10")]
    t = at(run(rows), "AOI-1")
    assert t["r"] == 10 and t["d"] == 0 and t["x"] == 3


def test_rescan_needs_the_same_job_group_and_lot_and_wafer():
    rows = [w("AOI-1", "W1", "08:00", "08:10", job="R_TB500_LIVE_PI3"),
            w("AOI-1", "W1", "12:00", "12:10", job="R_TB500_LIVE_PI3 AOI-22 Copy_0614"),   # 병합되는 이름 → Rescan
            w("AOI-1", "W1", "14:00", "14:10", job="R_TB500_LIVE_PI2")]                    # 다른 공정 → 첫 기록
    t = at(run(rows), "AOI-1")
    assert t["d"] == 10 and t["r"] == 20


# ── 3. Test Lot 은 분모에만 ─────────────────────────────────────────────────
def test_test_lot_time_is_test_not_scan():
    rows = [w("AOI-1", "W1", "08:00", "08:30", lot="ZZZ TEST", report="J1_6321_ZZZ TEST_18-Sep-26_(08.30.00)_BatchReport.htm")]
    t = at(run(rows), "AOI-1")
    assert t["t"] == 30 and t["r"] == 0 and t["lots"][0][7] == 1


# ── 4. Error 후 대기 (D48 제품 유지 ①): cap 없음 · 마지막 Error 는 관측 종료까지 ──
def test_wait_after_an_error_runs_to_the_next_record_without_a_cap():
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error."), w("AOI-1", "W2", "14:00", "14:10")]
    assert at(run(rows), "AOI-1")["s"] == 357                       # 08:03 → 14:00
    assert at(run(rows, rules=DESIGN_RULES), "AOI-1")["s"] == 240   # 디자인 규칙은 240분 cap


def test_last_error_of_the_day_waits_until_the_observation_end():
    rows = [w("AOI-1", "W1", "20:00", "20:03", status="Alignment Error."), w("AOI-2", "W9", "23:20", "23:30")]
    t = at(run(rows), "AOI-1")
    assert t["s"] == 207 and t["we"] == 1410                        # 20:03 → 23:30 (다른 장비의 마지막 기록 = 관측 종료), we = 그 끝(분)
    assert at(run(rows, rules=DESIGN_RULES), "AOI-1")["s"] == 0      # 디자인 규칙은 다음 기록이 없으면 0
    rows2 = rows + [w("AOI-2", "W8", "01:00", "01:10", day="2026-09-19")]
    assert at(run(rows2), "AOI-1")["s"] == 237                      # 관측이 다음 날까지면 그날 자정까지(다음 날로 늘리지 않는다)


# ── 5. 분모 (D48 제품 유지 ②): 수집한 날만 마지막 기록까지 ───────────────────
def test_denominator_is_1440_except_the_collection_day_which_stops_at_the_last_record():
    rows = [w("AOI-1", "W1", "08:00", "09:00"), w("AOI-1", "W2", "07:00", "07:30", day="2026-09-17")]
    D = run(rows)
    assert at(D, "AOI-1")["den"] == 540 and at(D, "AOI-1", "2026-09-17")["den"] == 1440
    assert D["today"] == DAY and D["day"] == DAY
    assert at(run(rows, rules=DESIGN_RULES), "AOI-1")["den"] == 1440


def test_denominator_counts_batch_end_and_error_wait_of_the_collection_day():
    rows = [w("AOI-1", "W1", "08:00", "08:03", status="Alignment Error.", bs="07:50", be="10:00")]
    assert at(run(rows), "AOI-1")["den"] == 600                      # 배치 종료 10:00 이 마지막 기록
    # ★ 그날 마지막 Error 뒤 대기를 관측 종료(다른 장비 12:30)까지 셌으면 분모도 거기까지다 — 아니면 U+T+E+S 가 분모를 넘는다
    rows2 = rows + [w("AOI-2", "W9", "12:00", "12:30")]
    t = at(run(rows2), "AOI-1")
    assert t["s"] == 267 and t["we"] == 750 and t["den"] == 750        # 08:03 → 12:30
    assert t["r"] + t["d"] + t["t"] + t["x"] + t["s"] <= t["den"]


# ── 6. 추정의 근거 (D48-①): cv · bseg · be ───────────────────────────────────
def test_coverage_and_batch_occupancy_are_computed_per_device_day():
    rows = [w("AOI-1", "W1", "08:00", "08:10", bs="07:55", be="08:40"),
            w("AOI-1", "W2", None, None, bs="07:55", be="08:40"),               # INI 없음 — 시각 미확인
            w("AOI-1", "W3", None, None, lot="LOT-B", bs="09:00", be="09:30")]
    t = at(run(rows), "AOI-1")
    assert t["cv"] == 33 and t["bseg"] == [[475, 520], [540, 570]] and t["be"] == 75
    assert t["r"] == 10 and len(t["lots"]) == 2                     # 배치 구간만 있는 Lot 도 남는다


# ── 7. Lot 이름은 Report 파일명에서 (D48-⑤) ───────────────────────────────────
def test_lot_name_comes_from_the_report_file_name_and_keeps_only_known_tags():
    rows = [w("AOI-1", "W1", "08:00", "08:10", lot="FKC-PIDS5", report="R_TB500_LIVE_PI3_6324_Setup1_FKC-PIDS5_18-Sep-26_(08.10.00)_BatchReport.htm"),
            w("AOI-1", "W2", "09:00", "09:10", lot="TTP DIA", report="J1_6321_TTP DIA_18-Sep-26_(09.10.00)_BatchReport.htm"),
            w("AOI-1", "W3", "10:00", "10:10", lot="AMD Venice_U-Pad Dummy", report="J1_6321_AMD Venice_U-Pad Dummy_18-Sep-26_(10.10.00)_BatchReport.htm")]
    D = run(rows)
    assert set(D["pool"]["lot"]) == {"FKC", "TTP DIA", "AMD Venice_U-Pad Dummy"}


# ── 8. Job 병합 (D48-④): 통계에서만 묶고 표기는 원문 ──────────────────────────
def test_job_groups_merge_copies_but_keep_r_prefix_and_step_apart():
    rows = [w("AOI-1", "W1", "08:00", "08:10", job="R_TB500_LIVE_PI3"),
            w("AOI-1", "W2", "09:00", "09:10", job="R_TB500_LIVE_PI3 AOI-22 Copy_0614"),
            w("AOI-1", "W3", "10:00", "10:10", job="R_TB500_LIVE_PI2"),
            w("AOI-1", "W4", "11:00", "11:10", job="2D@RE-ABC_0858562PD-0A"),
            w("AOI-1", "W5", "12:00", "12:10", job="2D@R2-ABC_0858562PD-0A")]
    D = run(rows)
    g = {D["pool"]["job"][i]: D["jobG"][i] for i in range(len(D["pool"]["job"]))}
    assert g["R_TB500_LIVE_PI3"] == g["R_TB500_LIVE_PI3 AOI-22 Copy_0614"]
    assert g["R_TB500_LIVE_PI3"] != g["R_TB500_LIVE_PI2"] and g["2D@RE-ABC_0858562PD-0A"] != g["2D@R2-ABC_0858562PD-0A"]
    assert "R_TB500_LIVE_PI3 AOI-22 Copy_0614" in D["pool"]["job"]    # 원문 그대로 남는다


# ── 9. 장비 순서 · 범위 밖 · 3분 병합 · 시각 없는 Error ────────────────────────
def test_devices_follow_devices_sort_key_and_out_of_scope_devices_are_listed_apart():
    mt = meta("AOI-10", "4F-AOI-01", "AOI-2", "AOI-1", more=[{"name": "AOI-7", "note": "", "scope": "out", "reports": 0}])
    rows = [w(d, "W1", "08:00", "08:10") for d in ("AOI-10", "4F-AOI-01", "AOI-2", "AOI-1")]
    D = run(rows, mt)
    assert D["devices"] == ["AOI-1", "AOI-2", "AOI-10", "4F-AOI-01"]
    assert [s["n"] for s in D["scope"] if s["out"]] == ["AOI-7"]


def test_gaps_of_three_minutes_or_less_are_merged_into_one_segment():
    near = [w("AOI-1", "W1", "08:00", "08:10"), w("AOI-1", "W2", "08:12", "08:20")]
    far = [w("AOI-1", "W1", "08:00", "08:10"), w("AOI-1", "W2", "08:14", "08:20")]
    assert at(run(near), "AOI-1")["seg"] == [[480, 500, 0]]
    assert at(run(far), "AOI-1")["seg"] == [[480, 490, 0], [494, 500, 0]]


def test_an_error_without_wafer_time_gets_a_three_minute_mark_at_its_batch_start():
    rows = [w("AOI-1", "W1", None, None, status="Alignment Error.", bs="08:00", be="08:30")]
    t = at(run(rows), "AOI-1")
    assert t["seg"] == [[480, 483, 1]] and t["e"] == 1 and t["cv"] == 0


def test_day_falls_back_to_the_last_data_day_when_the_collection_day_has_no_data():
    rows = [w("AOI-1", "W1", "08:00", "08:10", day="2026-09-17")]
    D = run(rows)
    assert D["today"] == DAY and D["day"] == "2026-09-17"
    D2 = run(rows, {**meta("AOI-1"), "generated_iso": ""})
    assert D2["today"] is None and D2["day"] == "2026-09-17"
