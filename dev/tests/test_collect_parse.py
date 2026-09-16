"""수집 코어의 순수 파싱 함수들."""
from __future__ import annotations

import datetime as dt

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
    ("Failed to read wafer id. Reading error = **********. Wafer Skipped.", "SKIPPED"),
    ("Wafer aborted by user.", "USER_ABORT"),
])
def test_norm_status_covers_every_wording_seen_on_30_machines(raw, expected):
    assert collect.norm_status(raw) == expected


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
