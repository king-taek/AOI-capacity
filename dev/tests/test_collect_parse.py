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
