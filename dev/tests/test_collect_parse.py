"""수집 코어의 순수 파싱 함수들."""
from __future__ import annotations

import datetime as dt
import json

import pytest

from aoi_capacity import collect
from conftest import REPORT_HTML, REPORT_NAME, WAFER_INI, make_device


def test_parse_dt_every_format_seen_on_real_machines():
    """장비마다 표기가 다르다 — AOI-8·25 는 `13-Sep-26 …`, AOI-1 은 `9/16/2026 1:54:03 PM`."""
    assert collect.parse_dt("13-Sep-26 05:31:04 PM") == dt.datetime(2026, 9, 13, 17, 31, 4)
    assert collect.parse_dt("9/16/2026 1:54:03 PM") == dt.datetime(2026, 9, 16, 13, 54, 3)     # AOI-1
    assert collect.parse_dt("9/16/2026 11:54:03 AM") == dt.datetime(2026, 9, 16, 11, 54, 3)
    assert collect.parse_dt("09/13/2026 17:25:14") == dt.datetime(2026, 9, 13, 17, 25, 14)     # INI BatchStartTime
    assert collect.parse_dt("16-Apr-26 02:00:31") == dt.datetime(2026, 4, 16, 2, 0, 31)
    assert collect.parse_dt("") is None and collect.parse_dt("garbage") is None


@pytest.mark.parametrize("raw,expected", [
    ("Pass", "PASS"),
    ("Skipped.", "SKIPPED"),
    ("Failed to read wafer id. Reading error = . Aborted.", "ID_READ_ERROR"),   # 우선순위: ABORTED 보다 먼저
    ("Scan Error: Scan2d optic is not valid on machine.", "SCAN_ERROR"),
    ("Alignment Error.", "ALIGN_ERROR"),
    ("Aborted. Wafer aborted by user.", "USER_ABORT"),
    ("Aborted.", "ABORTED"),
    ("Something new", "UNKNOWN"),          # 미지원 문구 — 지우지 않고 UNKNOWN(품질 목록)으로 남긴다(D43)
    ("", ""),
])
def test_norm_status(raw, expected):
    assert collect.norm_status(raw) == expected


def test_parse_report_filename_and_tables():
    rep = collect.parse_report(REPORT_NAME, REPORT_HTML)
    assert rep["equipment"] == "2D@R2-GA285AAB_0859840PD-0A"
    assert rep["process_code"] == "6321"
    assert rep["report_lot"] == "KLK-3D"
    assert rep["summary"]["Batch Start"] == "13-Sep-26 05:25:14 PM"
    assert rep["summary"]["Recipe"] == "Default"
    assert [w["wafer_id"] for w in rep["wafers"]] == ["K625407-01B0", "K625407-99Z9", "Slot 3"]
    assert rep["wafers"][2]["lot"] == "LoadPort A"


def test_parse_report_unknown_filename_still_parses_tables():
    rep = collect.parse_report("odd_name.htm", REPORT_HTML)
    assert rep["equipment"] == "" and len(rep["wafers"]) == 3


# ── 실장비(AOI-25) 형식 — 경로의 출처는 파일명이 아니라 Report 안의 Job/Setup ──────────
LIVE_NAME = "TB500_RDL2 - Multi_Setup1_FUK-RDL2_26-Sep-16_(09.18.00)_BatchReport.htm"
LIVE_HTML = """<html><body>
<table><tr><td>Batch Start</td><td>15-Sep-26 06:23:14 PM</td><td>Batch End</td><td>16-Sep-26 09:17:51 AM</td><td>Batch Time</td><td>14:54:37</td></tr>
<tr><td>Wafers Scanned</td><td>24</td><td>Avg. Scan Time</td><td>00:13:55</td><td></td><td></td></tr>
<tr><td>Yield</td><td>90.8</td><td>Job/Setup</td><td>TB500_RDL2 - Multi/Setup1</td><td>User</td><td>MAINT</td></tr></table>
<table><tr><th>Lot</th><th>Wafer ID</th><th>Faults</th><th>Scanned Dice</th><th>Bad Dice</th><th>Good Dice</th><th>Yield</th><th>Pass/Fail</th><th>Recipe(s)</th></tr>
<tr><td>FUK-RDL2</td><td>54265662EWE7</td><td>10</td><td>40</td><td>9</td><td>31</td><td>77.5%</td><td>Pass</td><td>x20</td></tr>
<tr><td>FUK-RDL2</td><td>54265684EWA2</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Alignment Error.</td><td>x20</td></tr></table></body></html>"""


def test_live_format_takes_path_from_job_setup_not_filename():
    """실장비 파일명은 옛 규칙에 맞지 않는다(516개 중 6개만 일치) — Job/Setup 을 써야 한다."""
    assert collect.REPORT_RE.match(LIVE_NAME) is None
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    assert rep["equipment"] == "TB500_RDL2 - Multi"      # = Scanresult 아래 첫 단계
    assert rep["process_code"] == "Setup1"               # = 그 다음 단계
    assert rep["report_lot"] == "FUK-RDL2"               # 파일명이 아니라 표의 Lot 열에서
    assert rep["summary"]["Batch End"] == "16-Sep-26 09:17:51 AM"


def test_job_setup_split_keeps_slashes_in_job():
    assert collect.split_job_setup("TB500_RDL2 - Multi/Setup1") == ("TB500_RDL2 - Multi", "Setup1")
    assert collect.split_job_setup("A/B/Setup2") == ("A/B", "Setup2")
    assert collect.split_job_setup("") == ("", "")


def test_old_format_still_uses_filename_when_no_job_setup():
    rep = collect.parse_report(REPORT_NAME, REPORT_HTML)
    assert "Job/Setup" not in rep["summary"]
    assert (rep["equipment"], rep["process_code"]) == ("2D@R2-GA285AAB_0859840PD-0A", "6321")


def _live_ini(tmp_path, start: str, end: str, wafer: str = "54265662EWE7") -> None:
    d = tmp_path / "Scanresult" / "TB500_RDL2 - Multi" / "Setup1" / "FUK-RDL2" / wafer
    d.mkdir(parents=True, exist_ok=True)
    (d / "WaferInfo.ini").write_text(WAFER_INI.replace("UseLot=KLK-3D", "UseLot=FUK-RDL2")
                                     .replace("UseWaferID=K625407-01B0", f"UseWaferID={wafer}")
                                     .replace("WaferStartTime=13-Sep-26 05:31:04 PM", f"WaferStartTime={start}")
                                     .replace("WaferEndTime=13-Sep-26 05:32:02 PM", f"WaferEndTime={end}"),
                                     encoding="utf-8")


def test_live_format_builds_ini_path_and_reads_times(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")     # 배치 구간 안
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    by = {r["wafer_id"]: r for r in rows}
    assert by["54265662EWE7"]["ini_match"] == "EXACT"
    assert by["54265662EWE7"]["wafer_start_time"] == "15-Sep-26 07:30:00 PM"
    assert by["54265662EWE7"]["batch_end"] == "16-Sep-26 09:17:51 AM"
    assert by["54265684EWA2"]["norm_status"] == "ALIGN_ERROR"     # 실장비에 실제로 있는 상태
    assert not [r for r in rows if r["kind"] == "batch"]          # 검사된 Wafer 가 있으니 배치 실패가 아니다


# ── 덮어써진 INI · 통째로 실패한 배치 (AOI-25 9/14 실물에서 확인한 모습) ──────────
def test_ini_outside_the_batch_window_is_not_used(tmp_path):
    """다시 검사하면 INI 가 덮어써져 옛 Report 행에도 '나중 시각' 이 붙는다 — 그 시간은 쓰지 않는다."""
    _live_ini(tmp_path, "16-Sep-26 02:05:00 PM", "16-Sep-26 02:10:00 PM")     # 배치(~09:17)보다 한참 뒤
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    r = next(x for x in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
             if x["wafer_id"] == "54265662EWE7")
    assert r["ini_match"] in ("STALE", "BATCH_FAILED")
    assert r["wafer_start_time"] == "" and r["wafer_end_time"] == ""
    assert "덮어써짐" in r["data_issue"]


FAILED_BATCH_HTML = LIVE_HTML.replace(
    "<td>77.5%</td><td>Pass</td>", "<td>-</td><td>Aborted.</td>").replace(
    "<tr><td>FUK-RDL2</td><td>54265684EWA2</td>", "<tr><td>LoadPort A</td><td>Slot 3</td>")


def test_failed_batch_becomes_one_row_with_batch_times(tmp_path):
    """검사된 Wafer 가 하나도 없는 시도 — Scanresult 에 흔적이 없어 Batch 시각만이 근거다."""
    rep = collect.parse_report(LIVE_NAME, FAILED_BATCH_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    batch = [r for r in rows if r["kind"] == "batch"]
    assert len(batch) == 1
    b = batch[0]
    assert (b["wafer_start_time"], b["wafer_end_time"]) == ("15-Sep-26 06:23:14 PM", "16-Sep-26 09:17:51 AM")
    # 대표 원인은 하위 행의 명시적 Error(Slot 3 의 Alignment Error.) — 첫 행의 'Aborted.' 에 가려지지 않는다(D43·E04)
    assert b["norm_status"] == "ALIGN_ERROR" and b["cause"] == "ALIGN_ERROR" and b["wafer_id"] == "" and b["lot"] == "FUK-RDL2"
    # 나머지 행(자리표시 Slot 포함)은 배치 한 건으로 묶여 따로 세지 않는다
    assert all(r["ini_match"] == "BATCH_FAILED" for r in rows if r["kind"] != "batch")


def test_normal_batch_makes_no_batch_row(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    assert not [r for r in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
                if r["kind"] == "batch"]


OLD_NAME = "2D@RE-GA276IPB_0858128PD-0C_6412_KFD_26-Sep-16_(03.38.04)_BatchReport.htm"
OLD_HTML = """<html><body>
<table><tr><td>Batch Start</td><td>9/16/2026 1:54:03 PM</td><td>Batch End</td><td>9/16/2026 3:38:47 PM</td></tr>
<tr><td>Wafers Scanned</td><td>1</td><td>User</td><td>MAINT</td></tr></table>
<table><tr><th>Lot</th><th>Wafer ID</th><th>Pass/Fail</th><th>Recipe(s)</th></tr>
<tr><td>KFD</td><td>K617531-25A</td><td>Pass</td><td>2D</td></tr></table></body></html>"""


def test_old_machine_format_without_job_setup_still_works(tmp_path):
    """AOI-1 은 Report 에 Job/Setup 이 없고 시각이 슬래시·12시간제다 — 파일명 규칙으로 끝까지 돌아야 한다."""
    rep = collect.parse_report(OLD_NAME, OLD_HTML)
    assert "Job/Setup" not in rep["summary"]
    assert (rep["equipment"], rep["process_code"]) == ("2D@RE-GA276IPB_0858128PD-0C", "6412")
    ini_dir = tmp_path / "Scanresult" / "2D@RE-GA276IPB_0858128PD-0C" / "6412" / "KFD" / "K617531-25A"
    ini_dir.mkdir(parents=True)
    (ini_dir / "WaferInfo.ini").write_text(WAFER_INI.replace("UseLot=KLK-3D", "UseLot=KFD")
                                           .replace("UseWaferID=K625407-01B0", "UseWaferID=K617531-25A")
                                           .replace("13-Sep-26 05:31:04 PM", "9/16/2026 2:10:00 PM")
                                           .replace("13-Sep-26 05:32:02 PM", "9/16/2026 2:25:00 PM"),
                                           encoding="utf-8")
    r = collect.rows_for_report("AOI-1", rep, str(tmp_path / "Scanresult"))[0]
    assert r["ini_match"] == "EXACT"                      # 배치 구간(13:54~15:38) 안이라 시간을 쓴다
    assert collect.parse_dt(r["wafer_start_time"]) == dt.datetime(2026, 9, 16, 14, 10)
    assert collect.parse_dt(r["batch_end"]) == dt.datetime(2026, 9, 16, 15, 38, 47)


# ── Lot 이름의 작업 표기 (AOI-1 Report 2011개 · AOI-8 4784개 실물 근거) ──────────
@pytest.mark.parametrize("lot,expected", [
    ("MDH-RE", "RESCAN"), ("XXC RE", "RESCAN"), ("XXC 2D 3D RE", "RESCAN"),
    ("TUY FVI MERGE RE 3D", "RESCAN"), ("KFP 3D RESCAN", "RESCAN"), ("KTF-RESCAN", "RESCAN"),
    ("FVC REWORK", "REWORK"), ("KDG-Rework-0831", "REWORK"), ("UVG TPDV REWORK", "REWORK"),
    # 검사 종류는 정상이다(사용자 확정) — SRD·DIA·3D·EDGE·BUMP
    ("EDGE SRD", ""), ("XAC DIA", ""), ("KLN-3D", ""), ("FSV-BUMP", ""), ("UAX 3D DUMMY", ""),
    # 토큰이 통째로 맞을 때만 — 이름 안에 RE 가 들어갔다고 걸리면 안 된다
    ("LVT RETURN 3D FVI MERGE", ""), ("REX", ""), ("KFD", ""), ("", ""),
])
def test_scan_type_reads_lot_marks(lot, expected):
    assert collect.scan_type(lot) == expected


def test_scan_type_prefers_rescan_when_both_marks_appear():
    assert collect.scan_type("XXX REWORK RE") == "RESCAN"


def test_rows_carry_scan_type(tmp_path):
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML.replace("FUK-RDL2", "FUK-RDL2 RE"))
    assert all(r["scan_type"] == "RESCAN" for r in collect.rows_for_report("AOI-8", rep, str(tmp_path)))


def test_read_ini_filters_to_needed_keys(tmp_path):
    p = tmp_path / "WaferInfo.ini"
    p.write_text(WAFER_INI, encoding="utf-8")
    ini = collect.read_ini(p)
    assert ini["AutoCycleInfo"]["WaferStartTime"] == "13-Sep-26 05:31:04 PM"
    assert ini["Recipe"]["Name"] == "Default"
    assert "Rotation" not in ini.get("Robot", {})          # 필요 없는 키는 버린다


def test_rows_for_report_match_states(tmp_path):
    dev = make_device(tmp_path, "AOI-9")
    rep = collect.parse_report(REPORT_NAME, REPORT_HTML)
    rows = collect.rows_for_report("AOI-9", rep, str(dev / "Scanresult"))
    by = {r["wafer_id"]: r for r in rows}
    assert by["K625407-01B0"]["ini_match"] == "EXACT" and by["K625407-01B0"]["data_issue"] == ""
    assert by["K625407-01B0"]["wafer_end_time"] == "13-Sep-26 05:32:02 PM"
    assert by["K625407-99Z9"]["ini_match"] == "NOT_FOUND" and by["K625407-99Z9"]["norm_status"] == "ID_READ_ERROR"
    assert by["Slot 3"]["ini_match"] == "NO_WAFER_ID"
    assert all(r["batch_start"] == "13-Sep-26 05:25:14 PM" for r in rows)


def test_rows_for_report_flags_mismatch_and_reversed_time(tmp_path):
    dev = make_device(tmp_path, "AOI-9")
    ini = dev / "Scanresult" / "2D@R2-GA285AAB_0859840PD-0A" / "6321" / "KLK-3D" / "K625407-01B0" / "WaferInfo.ini"
    ini.write_text(WAFER_INI.replace("UseLot=KLK-3D", "UseLot=OTHER")
                   .replace("WaferEndTime=13-Sep-26 05:32:02 PM", "WaferEndTime=13-Sep-26 05:30:00 PM"), encoding="utf-8")
    rep = collect.parse_report(REPORT_NAME, REPORT_HTML)
    r = next(x for x in collect.rows_for_report("AOI-9", rep, str(dev / "Scanresult")) if x["wafer_id"] == "K625407-01B0")
    assert "역전" in r["data_issue"] and "Lot 불일치" in r["data_issue"]


# ── 30대 전수 샘플(Report 55,717개)에서 새로 드러난 것들 ────────────────────────
ALL_PLACEHOLDER_HTML = LIVE_HTML.replace(
    "<tr><td>FUK-RDL2</td><td>54265662EWE7</td><td>10</td><td>40</td><td>9</td><td>31</td><td>77.5%</td><td>Pass</td>",
    "<tr><td>LoadPort A</td><td>Slot 1</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Aborted.</td>").replace(
    "<tr><td>FUK-RDL2</td><td>54265684EWA2</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Alignment Error.</td>",
    "<tr><td>LoadPort A</td><td>Slot 2</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Aborted.</td>")


def test_batch_row_lot_is_never_the_loadport_placeholder(tmp_path):
    """실물 30대 중 8건이 `LoadPort A` 를 Lot 으로 달고 있었다 — 자리표시는 Lot 이 아니다."""
    rep = collect.parse_report(LIVE_NAME, ALL_PLACEHOLDER_HTML)
    assert rep["report_lot"] == ""                       # 표에 진짜 Lot 이 하나도 없다
    b = next(r for r in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
             if r["kind"] == "batch")
    assert b["lot"] == "" and not b["lot"].lower().startswith("loadport")


def test_empty_lot_never_builds_an_ini_path(tmp_path):
    """Lot 이 비면 경로에서 그 칸이 사라져 **다른 Lot 의 INI** 를 가리킨다 — 아예 만들지 않는다."""
    d = tmp_path / "Scanresult" / "TB500_RDL2 - Multi" / "Setup1" / "54265662EWE7"
    d.mkdir(parents=True)
    (d / "WaferInfo.ini").write_text(WAFER_INI, encoding="utf-8")     # 있어도 쓰면 안 된다
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML.replace("<td>FUK-RDL2</td>", "<td></td>"))
    r = next(x for x in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
             if x["wafer_id"] == "54265662EWE7")
    assert r["ini_match"] == "NO_WAFER_ID" and r["wafer_start_time"] == ""


@pytest.mark.parametrize("raw,expected", [
    # 30대 전수 샘플에서 새로 나온 표기 — 문구 끝의 'Skipped.' 때문에 정상으로 묻히면 안 된다
    ("Failed to move wafer from LoadPort A to End-Effector Error: Robot: The wafer could not be "
     "detected on Hand1 after the GET motion. . Batch Aborted. Skipped.", "WAFER_LOST"),
    ("Camera Hardware Failure. Failed switch to camera IVP_RANGER, Failed to Set Camera. Batch Aborted.", "HW_ERROR"),
    ("FAR Model inside recipe is invalid, Please review active model or disable far model "
     "activation in Global RTP.", "RECIPE_ERROR"),
    ("Wafer Map Import failed.", "RECIPE_ERROR"),
    ("Scan 2D: Illegal Lot Name.", "RECIPE_ERROR"),
    ("Scan 3D Error.", "SCAN_ERROR"),
    ("Scan 2D Error. Reason: Process Scanned Images Failed.", "SCAN_ERROR"),
    ("Failed to read wafer id on PAL", "ID_READ_ERROR"),
    ("Failed to read wafer id. Reading error = **********. Wafer Skipped.", "ID_READ_ERROR"),   # D43: 원인이 결과(건너뜀)보다 먼저
    ("Wafer aborted by user.", "USER_ABORT"),
])
def test_norm_status_covers_every_wording_seen_on_30_machines(raw, expected):
    assert collect.norm_status(raw) == expected


# ── D43: 원인(cause)과 종료 결과(outcome)는 다른 축 ──────────────────────────────────────
@pytest.mark.parametrize("raw,causes,outcome", [
    ("Failed to read wafer id. Reading error = **********. Wafer Skipped.", ["ID_READ_ERROR"], "SKIPPED"),
    ("Focus Mapping Error. Batch Aborted.", ["FOCUS_MAPPING_ERROR"], "ABORTED"),
    ("Aborted.", [], "ABORTED"), ("Aborted", [], "ABORTED"),
    ("Aborted. Wafer aborted by user.", [], "USER_ABORT"),
    ("Failed to read wafer id. Reading error = **********. Wafer aborted by user.", ["ID_READ_ERROR"], "USER_ABORT"),
    ("Skipped. Aborted.", [], "SKIPPED"), ("Aborted. Skipped.", [], "SKIPPED"),       # 복합은 마지막 결과 SKIPPED
    ("Cancelled", [], "USER_CANCELLED"), ("-", [], "UNKNOWN"), ("", [], "UNKNOWN"),
    ("Abort timed-out", ["CONTROL_TIMEOUT"], "ABORTED"),
    ("Wafer Gray Level Average exceeds limits!. Batch Aborted.", ["GRAY_LEVEL_LIMIT"], "ABORTED"),
    ("Auto Focus Error.", ["AUTO_FOCUS_ERROR"], "FAILED"),                              # 원인만 있고 결과 문구 없음
    ("Wafer ID Mask length(11) differs from actual Wafer ID length(10). ID: X Mask: I", ["ID_FORMAT_ERROR"], "FAILED"),
    ("Robot operation failed: Failed on MoveTableToStoredPosAndLock. LastError: Table: Failed on MoveToStoredPos(m_eTableLockPosition) . Batch Aborted.",
     ["HANDLING_ERROR"], "ABORTED"),
    ("Failed to MoveTableToStoredPosAndLock. LastError: Table: Motion failed to get_ContinuousScanStatus(pVal) , Exception: … AcsMotor::get_Position Failed",
     ["MOTION_ERROR", "HANDLING_ERROR"], "FAILED"),
    ("Alignment Error. Robot operation failed: Failed on MoveTableToStoredPosAndLock. LastError: Table: Wafer on chuck is not secured. Chuck remains locked. . Batch Aborted.",
     ["ALIGN_ERROR", "HANDLING_ERROR"], "ABORTED"),
    # 반송 실패는 문구가 `… Batch Aborted. Skipped.` 로 끝난다 — 원인이 먼저라 결과(SKIPPED)에 묻히지 않는다
    ("Failed to move wafer from LoadPort A to End-Effector Error: Robot: The wafer could not be detected on Hand1 after the GET motion. . Batch Aborted. Skipped.",
     ["WAFER_LOST"], "SKIPPED"),
])
def test_cause_and_outcome_are_separate_axes(raw, causes, outcome):
    assert collect.norm_causes(raw) == causes and collect.norm_outcome(raw) == outcome
    assert collect.norm_status(raw) == ("" if not raw else causes[0] if causes else outcome)   # 빈 문구의 호환 필드는 빈 값


def test_unmapped_status_is_kept_as_unknown_not_dropped():
    assert collect.is_unmapped_status("Something new") and collect.norm_outcome("Something new") == "UNKNOWN"
    assert not collect.is_unmapped_status("-") and not collect.is_unmapped_status("") and not collect.is_unmapped_status("Aborted.")


def test_rows_carry_cause_and_outcome_columns(tmp_path):
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    by = {r["wafer_id"]: r for r in rows}
    assert by["54265684EWA2"]["cause"] == "ALIGN_ERROR" and by["54265684EWA2"]["outcome"] == "FAILED"
    assert by["54265662EWE7"]["cause"] == "" and by["54265662EWE7"]["outcome"] == "PASS"
    assert {"cause", "outcome"} <= set(collect.OUT_COLS) and collect.ROW_SCHEMA_VERSION >= 2


def test_batch_lead_is_deterministic_and_keeps_child_causes():
    """★ E04: 부모(첫 행 Aborted) 아래 명시적 Error 가 있으면 대표 원인은 그 Error 다 — 순서를 뒤집어도 같다."""
    mk = lambda st, ini="NOT_FOUND": {"status": st, "ini_match": ini, "recipe": "R"}
    rows = [mk("Aborted."), mk("Alignment Error.", "NO_WAFER_ID"), mk("Scan 2D Error."), mk("Scan 2D Error. Aborted.")]
    lead, union = collect._lead_error_row(rows)
    assert union == ["SCAN_ERROR", "ALIGN_ERROR"]           # 규칙 순서(구체적 원인 순)
    assert lead["status"] == "Scan 2D Error."                # 근거 행이 가장 많은 원인 · 자리표시 아님 · 원문 사전순
    lead2, union2 = collect._lead_error_row(list(reversed(rows)))
    assert lead2["status"] == lead["status"] and union2 == union
    lead3, _ = collect._lead_error_row([mk("Aborted."), mk("Alignment Error.", "NO_WAFER_ID")])
    assert lead3["status"] == "Alignment Error."             # 원인 있는 자리표시 행이 원인 없는 진짜 행보다 먼저


# ── Job name · Report 파일 이름(나중에 쓸 일이 있어 함께 담는다) ───────────────
def test_rows_carry_job_setup_and_report_file_name(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    for r in rows:
        assert (r["job"], r["setup"]) == ("TB500_RDL2 - Multi", "Setup1")   # Report 안의 Job/Setup
        assert r["report"] == LIVE_NAME                                     # Report 를 다시 열 수 있게
    assert {"job", "setup", "report"} <= set(collect.OUT_COLS)


def test_old_format_job_falls_back_to_the_file_name_rule():
    rep = collect.parse_report(REPORT_NAME, REPORT_HTML)
    rows = collect.rows_for_report("AOI-1", rep, "/nowhere")
    assert rows[0]["job"] == "2D@R2-GA285AAB_0859840PD-0A" and rows[0]["setup"] == "6321"
    assert rows[0]["report"] == REPORT_NAME


def test_embedded_rows_are_folded_into_a_string_pool():
    """장비 30대 × 90일이면 행이 십수만 개다 — 되풀이되는 열은 번호로 접어 넣는다."""
    rows = [{"device": "AOI-25", "job": "J", "setup": "S", "report": "r.htm", "lot": "L",
             "wafer_start_time": f"15-Sep-26 07:{i:02d}:00 PM"} for i in range(50)]
    emb = collect._embed_rows(rows)
    assert emb["cols"] == collect.OUT_COLS
    assert "wafer_start_time" not in emb["pooled"]          # 값이 거의 다 달라 접지 않는다
    assert "device" in emb["pooled"] and "report" in emb["pooled"]
    assert emb["pool"].count("AOI-25") == 1                 # 50행이 같은 번호를 가리킨다
    di, ti = collect.OUT_COLS.index("device"), collect.OUT_COLS.index("wafer_start_time")
    assert len({r[di] for r in emb["rows"]}) == 1
    assert emb["rows"][3][ti] == "15-Sep-26 07:03:00 PM"    # 접지 않은 열은 문자열 그대로


# ── 실장비 3일치(15,626행)에서 새로 드러난 것들 ──────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    ("Clean Reference Error.", "CLEAN_REF_ERROR"),                  # 3일치 72건 — 가장 흔한 미분류였다
    ("Nothing to Scan.", "NOTHING_TO_SCAN"),
    ("Manual Alignment Failed.", "ALIGN_ERROR"),
    ("Prealigner failure", "ALIGN_ERROR"),
    ("Scanning Multi recipe error.", "RECIPE_ERROR"),
    ("Wafer Handling Failure (LoadPort A to End-Effector).", "WAFER_LOST"),
    ("Failed on MoveToStation", "WAFER_LOST"),
])
def test_norm_status_covers_the_three_day_field_run(raw, expected):
    assert collect.norm_status(raw) == expected


SETUP_NAME = "R_TB500 TOP D-DIE_0860312PD_SETUP_UDL_26-Sep-14_(01.02.37)_BatchReport.htm"
SETUP_HTML = ("<html><body><table>"
            "<tr><td>Batch Start</td><td>14-Sep-26 01:02:37 AM</td><td>Batch End</td><td>14-Sep-26 02:31:08 AM</td></tr>"
            "</table><table><tr><th>Lot</th><th>Wafer ID</th><th>Pass/Fail</th></tr>"
            "<tr><td>LoadPort A</td><td>Slot 1</td><td>Pass</td></tr>"
            "<tr><td>UDL</td><td>SH75P23-G2</td><td>Pass</td></tr></table></body></html>")


def test_old_report_without_job_setup_recovers_the_path_from_the_table_lot():
    """★ 실물: AOI-10 은 `Job/Setup` 이 없는데 Setup 이 `SETUP`(4자리 아님) 이라 파일명 규칙도 빗나갔다.
    그래서 job 이 비었고 INI 경로가 통째로 어긋나 9/15 하루에만 8.8시간이 '미가동' 으로 보였다."""
    assert collect.REPORT_RE.match(SETUP_NAME) is None            # 옛 규칙으로는 못 읽는다
    rep = collect.parse_report(SETUP_NAME, SETUP_HTML)
    assert (rep["job"], rep["setup"]) == ("R_TB500 TOP D-DIE_0860312PD", "SETUP")
    assert rep["report_lot"] == "UDL"
    r = next(x for x in collect.rows_for_report("AOI-10", rep, "/nowhere") if x["wafer_id"] == "SH75P23-G2")
    assert r["job"] and r["setup"]                              # 이제 경로를 만들 수 있다


@pytest.mark.parametrize("name,lot,expected", [
    (SETUP_NAME, "UDL", ("R_TB500 TOP D-DIE_0860312PD", "SETUP")),
    ("INCI-W97255Z6BK16_0860703PD-0A_2D_YCL_26-Sep-16_(18.07.25)_BatchReport.htm", "YCL",
     ("INCI-W97255Z6BK16_0860703PD-0A", "2D")),
    # Lot 자리가 비어 있는 파일명 — 되찾을 근거가 없으니 지어내지 않는다
    ("INCI-UZ0056B-CB001_0859659PD-0B123_6000__26-Sep-14_(22.53.10)_BatchReport.htm", "TNL", ("", "")),
    ("이상한이름.htm", "AAA", ("", "")),
])
def test_job_setup_by_table_lot(name, lot, expected):
    assert collect._job_setup_by_table_lot(name, [{"lot": lot, "wafer_id": "W1"}]) == expected


# ── D38: 일부만 성공한 배치의 자리표시(Slot) 행 Error — Report 당 1건 ──────────────────────────
PARTIAL_SLOT_HTML = LIVE_HTML.replace(
    "<tr><td>FUK-RDL2</td><td>54265684EWA2</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Alignment Error.</td><td>x20</td></tr>",
    "<tr><td>LoadPort A</td><td>Slot 3</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Failed to read wafer id. Reading error = ****. Wafer Skipped.</td><td>x20</td></tr>"
    "<tr><td>LoadPort A</td><td>Slot 4</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Failed to read wafer id. Reading error = ####. Wafer Skipped.</td><td>x20</td></tr>"
    "<tr><td>LoadPort A</td><td>Slot 4</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Failed to read wafer id. Reading error = ####. Wafer Skipped.</td><td>x20</td></tr>"
    "<tr><td>LoadPort A</td><td>Slot 5</td><td>-</td><td>-</td><td>-</td><td>-</td><td>-</td><td>Skipped.</td><td>x20</td></tr>")


def test_partial_batch_slot_errors_become_one_event_per_report(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")     # 한 장은 정상 스캔
    rep = collect.parse_report(LIVE_NAME, PARTIAL_SLOT_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    slot = [r for r in rows if r["kind"] == "slot"]
    assert len(slot) == 1 and not [r for r in rows if r["kind"] == "batch"]     # 배치 실패가 아니라 Slot 사건 1건
    s = slot[0]
    assert s["slots"] == "2" and s["cause"] == "ID_READ_ERROR" and s["outcome"] == "SKIPPED"   # Slot 3·4 (4 는 중복 행) — 원인 없는 Slot 5 는 세지 않음
    assert s["wafer_start_time"] == "" and s["wafer_end_time"] == "" and s["time_basis"] == "MISSING"   # 시간 미확인 — Batch 시간을 복사하지 않는다
    assert s["batch_start"] == "15-Sep-26 06:23:14 PM" and s["ini_match"] == "BATCH_SLOT" and s["lot"] == "FUK-RDL2" and s["wafer_id"] == ""
    assert "Slot 2개" in s["data_issue"]
    # 자리표시 원천 행은 그대로 남는다(지우지 않는다) — 화면이 따로 세지 않을 뿐
    assert sum(1 for r in rows if r["ini_match"] == "NO_WAFER_ID") == 4


def test_no_slot_event_when_the_batch_failed_as_a_whole(tmp_path):
    rep = collect.parse_report(LIVE_NAME, FAILED_BATCH_HTML)
    rows = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    assert [r["kind"] for r in rows if r["kind"]] == ["batch"]


def test_synthesize_rows_is_deterministic_and_idempotent():
    mk = lambda lot, wid, st, ini="NOT_FOUND", **k: {"device": "AOI-8", "kind": "", "job": "J", "setup": "S", "report": "r.htm", "lot": lot, "wafer_id": wid,
                                                     "status": st, "recipe": "R", "wafer_start_time": "", "wafer_end_time": "",
                                                     "batch_start": "15-Sep-26 09:00:00 AM", "batch_end": "15-Sep-26 09:30:00 AM", "ini_match": ini, **k}
    base = [mk("LOT", "W1", "Pass"), mk("LoadPort A", "Slot 2", "Failed to read wafer id on PAL", "NO_WAFER_ID"),
            mk("LoadPort A", "Slot 3", "Alignment Error.", "NO_WAFER_ID"), mk("LoadPort A", "Slot 4", "Failed to read wafer id on PAL", "NO_WAFER_ID")]
    once = collect.synthesize_rows([dict(r) for r in base])
    twice = collect.synthesize_rows([dict(r) for r in once])
    rev = collect.synthesize_rows([dict(r) for r in reversed(base)])
    slot = [r for r in once if r["kind"] == "slot"]
    assert len(slot) == 1 and slot[0]["slots"] == "3" and slot[0]["norm_status"] == "ID_READ_ERROR" and slot[0]["cause"] == "ID_READ_ERROR;ALIGN_ERROR"
    assert [r for r in twice if r["kind"] == "slot"] == slot                       # 두 번 돌려도 같다
    assert [r for r in rev if r["kind"] == "slot"] == slot                         # 순서를 뒤집어도 같다
    assert len(twice) == len(once) == 5                                            # 원천 4 + slot 1 — 늘지 않는다


def test_rederive_rebuilds_synthetic_rows_from_an_old_cache():
    """옛 캐시(D43 이전 규칙 · slot 행 없음)를 지금 규칙으로 — 22 Report 유형(ID 읽기 실패 후 Skipped 만 있는 배치)이 batch 행을 얻고, 두 번 해도 같다."""
    mk = lambda wid, st, ini="NOT_FOUND": {"device": "AOI-8", "kind": "", "job": "J", "setup": "S", "report": "r.htm", "lot": "LOT", "wafer_id": wid,
                                          "status": st, "norm_status": "SKIPPED", "recipe": "R", "wafer_start_time": "", "wafer_end_time": "",
                                          "batch_start": "15-Sep-26 09:00:00 AM", "batch_end": "15-Sep-26 09:30:00 AM", "ini_match": ini}
    cache = {"reports": {"/x/r.htm": {"rows": [mk("W1", "Failed to read wafer id. Reading error = **. Wafer Skipped."), mk("W2", "Skipped.")]}}, "parser_version": 2}
    n = collect._rederive_rows(cache)
    rows = cache["reports"]["/x/r.htm"]["rows"]
    assert n >= 1 and [r["kind"] for r in rows] == ["", "", "batch"]
    assert rows[2]["cause"] == "ID_READ_ERROR" and all(r["ini_match"] == "BATCH_FAILED" for r in rows[:2])
    again = json.loads(json.dumps(cache))
    assert collect._rederive_rows(again) == 0 and again["reports"]["/x/r.htm"]["rows"] == rows


# ── Scanresult 백업 폴더 조회 (30대 조사: 16대에 백업, 읽을 수 있는 INI 24,050 → 53,069) ──────────
def _backup_ini(tmp_path, folder: str, start: str, end: str, wafer: str = "54265662EWE7") -> None:
    d = tmp_path / folder / "TB500_RDL2 - Multi" / "Setup1" / "FUK-RDL2" / wafer
    d.mkdir(parents=True, exist_ok=True)
    (d / "WaferInfo.ini").write_text(WAFER_INI.replace("UseLot=KLK-3D", "UseLot=FUK-RDL2")
                                     .replace("UseWaferID=K625407-01B0", f"UseWaferID={wafer}")
                                     .replace("WaferStartTime=13-Sep-26 05:31:04 PM", f"WaferStartTime={start}")
                                     .replace("WaferEndTime=13-Sep-26 05:32:02 PM", f"WaferEndTime={end}"),
                                     encoding="utf-8")


def test_ini_roots_start_with_the_backup_whose_cutoff_is_after_the_batch():
    """배치 시작일이 경계보다 이른 **첫** 백업이 1순위, 그다음 지금 폴더, 나머지 백업, 경계 없는 백업은 맨 뒤."""
    live = "X/AOI-5/Scanresult"
    bk = [("X/AOI-5/Scanresult_Backup_250324", dt.date(2025, 3, 24)), ("X/AOI-5/Scanresult_Back up_260607", dt.date(2026, 6, 7)),
          ("X/AOI-5/Scanresult_0901", dt.date(2026, 9, 1)), ("X/AOI-5/Scanresult - 5.9.3", None)]
    b = dt.datetime(2026, 7, 2, 10, 0)
    order = collect.ini_roots_for(b, live, bk)
    assert order[0] == "X/AOI-5/Scanresult_0901"                   # 7/2 < 9/1 경계 → 그 백업에 있다
    assert order[1] == live and order[-1] == "X/AOI-5/Scanresult - 5.9.3" and len(order) == 5
    assert collect.ini_roots_for(dt.datetime(2026, 9, 15), live, bk)[0] == live       # 모든 경계 뒤 → 지금 폴더
    assert collect.ini_roots_for(None, live, bk)[0] == live                          # 배치 시각 모름 → 지금 폴더부터
    assert collect.ini_roots_for(b, live, None) == [live]                            # 백업 없음 → 예전 그대로


def test_ini_is_found_in_the_backup_folder_with_one_lookup(tmp_path):
    """9/15 배치인데 INI 가 `Scanresult_Back up_260918`(9/18 이전을 옮긴 곳)에만 있다 — 첫 확인에 찾고 백업 이름을 남긴다."""
    _backup_ini(tmp_path, "Scanresult_Back up_260918", "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    (tmp_path / "Scanresult").mkdir()
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    memo = collect._IniMemo()
    backups = [(str(tmp_path / "Scanresult_Back up_260918"), dt.date(2026, 9, 18))]
    rows = collect.rows_for_report("AOI-4", rep, str(tmp_path / "Scanresult"), memo, backups)
    r = next(x for x in rows if x["wafer_id"] == "54265662EWE7")
    assert r["ini_match"] == "EXACT" and r["wafer_start_time"] == "15-Sep-26 07:30:00 PM"
    assert "백업 폴더에서 찾음: Scanresult_Back up_260918" in r["data_issue"]
    # 54265662EWE7 은 1순위(백업)에서 바로 찾아 1회, 54265684EWA2 는 없어서 백업 → 지금 폴더 2회 = 3회(확인 횟수는 있는 것엔 예전과 같은 1번)
    assert memo.asked == 3
    r2 = next(x for x in rows if x["wafer_id"] == "54265684EWA2")
    assert r2["ini_match"] == "NOT_FOUND" and "백업 폴더 1개" in r2["data_issue"]


def test_missing_ini_falls_back_to_every_root_and_a_move_flag_means_moved_only(tmp_path):
    """어느 폴더에도 INI 가 없다: 1순위 폴더의 Wafer 자리에 `MoveResultFlag` 만 있으면 '이동만 되고 스캔 안 함'(MOVED_ONLY), 아니면 NOT_FOUND."""
    live = tmp_path / "Scanresult"
    bk = tmp_path / "Scanresult_Backup_260827"
    wafer_dir = bk / "TB500_RDL2 - Multi" / "Setup1" / "FUK-RDL2" / "54265662EWE7"
    wafer_dir.mkdir(parents=True)
    (wafer_dir / "MoveResultFlag").write_text("", encoding="utf-8")
    live.mkdir()
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)      # 배치 9/15 < 경계 8/27 이 아니다 → 1순위는 지금 폴더
    backups = [(str(bk), dt.date(2026, 8, 27))]
    by = {r["wafer_id"]: r for r in collect.rows_for_report("AOI-4", rep, str(live), collect._IniMemo(), backups)}
    assert by["54265662EWE7"]["ini_match"] == "NOT_FOUND"          # 표식은 백업(2순위)에 있고 1순위(지금 폴더)에는 없다
    backups = [(str(bk), dt.date(2026, 9, 30))]                     # 경계가 9/30 이면 백업이 1순위 → 거기 표식이 보인다
    by = {r["wafer_id"]: r for r in collect.rows_for_report("AOI-4", rep, str(live), collect._IniMemo(), backups)}
    assert by["54265662EWE7"]["ini_match"] == "MOVED_ONLY" and "스캔 안 함" in by["54265662EWE7"]["data_issue"]
    assert by["54265662EWE7"]["wafer_start_time"] == "" and by["54265662EWE7"]["time_basis"] == "MISSING"
    assert "MOVED_ONLY" in collect.RECOVERABLE_INI                  # 뒤에 스캔되면 INI 가 생기므로 누락 복구가 다시 본다


def test_rows_without_backups_behave_exactly_as_before(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    a = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
    b = collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"), collect._IniMemo(), [])
    assert a == b and a[0]["ini_match"] == "EXACT" and "백업" not in a[0]["data_issue"]


# ── faults · scanned_dice · yield (ROW_SCHEMA_VERSION 5) ──────────────────────────────
def test_wafer_rows_carry_faults_scanned_dice_and_yield_verbatim(tmp_path):
    """리포트 화면의 '평균 fault' 근거 — Report 표의 값을 원문 그대로 싣는다(`77.5%` 도 그대로). 합성 행은 빈 값."""
    assert collect.ROW_SCHEMA_VERSION == 5 and len(collect.OUT_COLS) == 24
    for c in ("faults", "scanned_dice", "yield"):
        assert c in collect.OUT_COLS and c in collect.POOLED_COLS
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    by = {r["wafer_id"]: r for r in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))}
    assert (by["54265662EWE7"]["faults"], by["54265662EWE7"]["scanned_dice"], by["54265662EWE7"]["yield"]) == ("10", "40", "77.5%")
    assert (by["54265684EWA2"]["faults"], by["54265684EWA2"]["yield"]) == ("-", "-")
    rows = collect.rows_for_report("AOI-25", collect.parse_report(LIVE_NAME, FAILED_BATCH_HTML), str(tmp_path / "Scanresult"))
    batch = next(r for r in rows if r["kind"] == "batch")
    assert (batch["faults"], batch["scanned_dice"], batch["yield"]) == ("", "", "")
    old = collect.parse_report(REPORT_NAME, REPORT_HTML.replace("<th>Faults</th><th>Scanned Dice</th><th>Bad Dice</th><th>Good Dice</th><th>Yield</th>", "")
                               .replace("<td>0</td><td>45</td><td>0</td><td>45</td><td>100%</td>", "")
                               .replace("<td>0</td><td>0</td><td>0</td><td>0</td><td>0%</td>", "")
                               .replace("<td></td><td></td><td></td><td></td><td></td>", ""))
    assert all(w["faults"] == "" and w["yield"] == "" for w in old["wafers"])      # 열이 없는 옛 Report 는 빈 값


# ── 4층 Job 폴더 이름 불일치 (사용자가 NAS 에서 확인, 9/20) ──────────────────────────
@pytest.mark.parametrize("job,expected", [
    ("2D@RE $7781539A-WUP_0858562PD_0A", ["2D@RE $7781539A-WUP_0858562PD_0A", "2D@RE-$7781539A-WUP_0858562PD_0A",
                                          "2D@RE $7781539A-WUP_0858562PD", "2D@RE-$7781539A-WUP_0858562PD"]),
    ("2D@R2-DT-GH10N-BIN1-H-U1_0858092PD_0B", ["2D@R2-DT-GH10N-BIN1-H-U1_0858092PD_0B", "2D@R2-DT-GH10N-BIN1-H-U1_0858092PD"]),
    ("2D@R2-W97113Z6B1K16_0858956PD-0A", ["2D@R2-W97113Z6B1K16_0858956PD-0A", "2D@R2-W97113Z6B1K16_0858956PD"]),   # 2층은 원문이 먼저 맞는다
    ("TB500_RDL2 - Multi", ["TB500_RDL2 - Multi"]),                                                                # 후보 없음 → 원문뿐
    ("", []),
])
def test_job_folder_variants_are_exact_names_in_order(job, expected):
    assert collect.job_folder_variants(job) == expected


def test_ini_is_found_under_the_machines_own_job_folder_name(tmp_path):
    """실물 4F-AOI-01: Report 는 `2D@RE $7781539A-WUP_0858562PD_0A`, 폴더는 `2D@RE-$7781539A-WUP_0858562PD`(공백→하이픈, `_0A` 없음)."""
    name = "2D@RE $7781539A-WUP_0858562PD_0A_6412_XAB_26-Sep-01_(06.08.55)_BatchReport.htm"
    html = LIVE_HTML.replace("TB500_RDL2 - Multi/Setup1", "2D@RE $7781539A-WUP_0858562PD_0A/6412").replace("FUK-RDL2", "XAB")
    d = tmp_path / "Scanresult" / "2D@RE-$7781539A-WUP_0858562PD" / "6412" / "XAB" / "54265662EWE7"
    d.mkdir(parents=True)
    (d / "WaferInfo.ini").write_text(WAFER_INI.replace("UseLot=KLK-3D", "UseLot=XAB").replace("UseWaferID=K625407-01B0", "UseWaferID=54265662EWE7")
                                     .replace("WaferStartTime=13-Sep-26 05:31:04 PM", "WaferStartTime=15-Sep-26 07:30:00 PM")
                                     .replace("WaferEndTime=13-Sep-26 05:32:02 PM", "WaferEndTime=15-Sep-26 07:44:00 PM"), encoding="utf-8")
    rep = collect.parse_report(name, html)
    assert rep["job"] == "2D@RE $7781539A-WUP_0858562PD_0A"          # Report 값은 그대로 둔다(원문)
    memo = collect._IniMemo()
    by = {r["wafer_id"]: r for r in collect.rows_for_report("4F-AOI-01", rep, str(tmp_path / "Scanresult"), memo)}
    r = by["54265662EWE7"]
    assert r["ini_match"] == "EXACT" and r["wafer_start_time"] == "15-Sep-26 07:30:00 PM"
    assert r["job"] == "2D@RE $7781539A-WUP_0858562PD_0A"            # 행의 Job 도 원문 — 폴더 이름은 비고에만
    assert "Job 폴더 이름이 Report 와 다름: 2D@RE-$7781539A-WUP_0858562PD" in r["data_issue"]
    # 원문 → 하이픈 → 접미 뗌 → 둘 다 순으로 4번째에 찾았다. 못 찾은 두 번째 Wafer 는 후보 4개를 다 본다
    assert memo.asked == 4 + 4
    assert by["54265684EWA2"]["ini_match"] == "NOT_FOUND"


def test_two_wafers_that_never_scanned_stay_not_found_when_their_siblings_are_exact(tmp_path):
    """실물 4F-AOI-01 UGK: 폴더가 있는 5장은 EXACT, Error/Aborted 로 스캔되지 않은 2장은 폴더가 없어 NOT_FOUND 가 맞다."""
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    by = {r["wafer_id"]: r for r in collect.rows_for_report("4F-AOI-01", rep, str(tmp_path / "Scanresult"))}
    assert by["54265662EWE7"]["ini_match"] == "EXACT" and by["54265684EWA2"]["ini_match"] == "NOT_FOUND"


def test_report_without_any_job_keeps_its_rows_and_builds_no_ini_path(tmp_path):
    """Job/Setup 도 없고 파일명 규칙에도 표-Lot 규칙에도 안 맞는 Report — 예전엔 jobs_try[0] 에서 IndexError 로 Report 통째로 '읽기 실패'."""
    from aoi_capacity import collect

    rep = {"name": "WEIRD NAME_BatchReport.htm", "equipment": "", "process_code": "", "job": "", "setup": "", "report_lot": "",
           "summary": {"Batch Start": "15-Sep-26 01:00:00 PM", "Batch End": "15-Sep-26 01:10:00 PM"},
           "wafers": [{"lot": "LOT-A", "wafer_id": "W1", "status": "Pass", "recipe": "", "faults": "", "scanned_dice": "", "yield": ""}]}
    rows = collect.rows_for_report("AOI-1", rep, str(tmp_path))
    assert len(rows) == 1 and rows[0]["ini_match"] == "NOT_FOUND" and "Job" in rows[0]["data_issue"]
    assert rows[0]["wafer_start_time"] == ""
