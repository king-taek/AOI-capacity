"""수집 코어의 순수 파싱 함수들."""
from __future__ import annotations

import datetime as dt

import pytest

from aoi_capacity import collect
from conftest import REPORT_HTML, REPORT_NAME, WAFER_INI, make_device


def test_parse_dt_three_formats():
    assert collect.parse_dt("13-Sep-26 05:31:04 PM") == dt.datetime(2026, 9, 13, 17, 31, 4)
    assert collect.parse_dt("09/13/2026 17:25:14") == dt.datetime(2026, 9, 13, 17, 25, 14)
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
    ("Something new", "OTHER"),
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
    assert b["norm_status"] == "ABORTED" and b["wafer_id"] == "" and b["lot"] == "FUK-RDL2"
    # 나머지 행(자리표시 Slot 포함)은 배치 한 건으로 묶여 따로 세지 않는다
    assert all(r["ini_match"] == "BATCH_FAILED" for r in rows if r["kind"] != "batch")


def test_normal_batch_makes_no_batch_row(tmp_path):
    _live_ini(tmp_path, "15-Sep-26 07:30:00 PM", "15-Sep-26 07:44:00 PM")
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    assert not [r for r in collect.rows_for_report("AOI-25", rep, str(tmp_path / "Scanresult"))
                if r["kind"] == "batch"]


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
