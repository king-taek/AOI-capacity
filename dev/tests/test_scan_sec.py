"""실제 촬영 초 `scan_sec`(ROW_SCHEMA_VERSION 9, 10/11 — D86 Q4 · Q5).

- ScanLog.ini `Duration` 은 첫 레시피만 센다(10/10 검증) — 멀티면 두 번째 레시피 시작(ExtendedScanMetaData)부터 장 끝까지를 더하되
  첫 레시피와 겹친 만큼과 마무리 SCAN_TAIL_SEC 는 뺀다. 장 시간을 넘지 않는다.
- EXACT 장만, 정확 경로만 연다. 근거가 맞지 않으면 빈 값(지어내지 않는다)."""
from __future__ import annotations

import datetime as dt

from aoi_capacity import collect
from test_recipes_info import _rows, _wafer_dir

D = dt.datetime


def test_parse_mdy_handles_zero_hour_am_and_pm():
    assert collect.parse_mdy("10/10/2026 0:53:58 AM") == D(2026, 10, 10, 0, 53, 58)
    assert collect.parse_mdy("10/10/2026 12:53:58 AM") == D(2026, 10, 10, 0, 53, 58)
    assert collect.parse_mdy("10/10/2026 1:3:35 PM") == D(2026, 10, 10, 13, 3, 35)
    assert collect.parse_mdy("garbage") is None


def test_single_recipe_is_duration_only():
    st, en = D(2026, 10, 10, 0, 52, 23), D(2026, 10, 10, 1, 10, 8)
    log = {"dur": 834.797, "start": D(2026, 10, 10, 0, 53, 58)}
    assert collect.scan_seconds(st, en, log, None) == 835


def test_second_recipe_adds_only_the_part_after_the_first_and_drops_the_tail():
    st, en = D(2026, 10, 10, 2, 6, 50), D(2026, 10, 10, 2, 21, 35)
    log = {"dur": 600.0, "start": D(2026, 10, 10, 2, 8, 34)}           # x20 02:08:34 ~ 02:18:34
    second = D(2026, 10, 10, 2, 19, 0)                                    # x5 시작(전환 26초는 촬영 아님)
    assert collect.scan_seconds(st, en, log, second) == 600 + (155 - 20)
    overlap = D(2026, 10, 10, 2, 15, 0)                                   # PI 처럼 겹치면 첫 레시피 끝부터만
    assert collect.scan_seconds(st, en, log, overlap) == 600 + (181 - 20)


def test_no_basis_no_number():
    st, en = D(2026, 10, 10, 1, 0, 0), D(2026, 10, 10, 1, 10, 0)
    assert collect.scan_seconds(st, en, None, None) is None
    assert collect.scan_seconds(st, en, {"dur": 100.0, "start": D(2026, 10, 9, 1, 0, 0)}, None) is None   # 다른 장의 ScanLog
    assert collect.scan_seconds(st, en, {"dur": 9999.0, "start": st}, None) == 600                         # 장 시간 상한


def test_collector_fills_scan_sec_from_the_wafer_folder(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    wd = _wafer_dir(nas)
    [r0] = _rows(tmp_path, csv_path)
    st = collect.parse_dt(r0["wafer_start_time"])
    start = (st + dt.timedelta(seconds=5)).strftime("%m/%d/%Y %I:%M:%S %p")
    (wd / "ScanLog.ini").write_text(f"[Version]\nName=10\n[General]\nDuration=30000.0\nStartScan={start}\n[2D]\nDuration=1\n", encoding="utf-8")
    [r] = _rows(tmp_path / "again", csv_path)
    assert r["ini_match"] == "EXACT" and r["scan_sec"] == "30"
