"""Report 요약 두 값 · Clean reference/AutoFocus 설정(ROW_SCHEMA_VERSION 8, 10/11).

- `wafers_scanned` · `avg_scan_time` 은 Report 요약 원문 — 그 Report 의 모든 행(합성 행 포함)에 같은 값. 파일을 더 읽지 않는다.
- `cr_every` · `af_every` 는 RDL 단일스캔 탭 Job(`RECIPE_TAB_JOB_RE`)만, Report 마다 INI 를 찾은 첫 Wafer 폴더의 Recipe.ini 한 장에서.
  다른 Job 은 Recipe.ini 를 열지 않고, 덮어써진(STALE) INI 의 폴더도 쓰지 않는다."""
from __future__ import annotations

import re

import pytest

from aoi_capacity import collect
from conftest import make_cfg
from test_collect_parse import LIVE_HTML, LIVE_NAME
from test_recipes_info import _rows, _wafer_dir

RECIPE_INI = """[AutoCycle]
AutoFocusBeforeAlignment=0
AutoFocusEvery=3 ; Wafer
CleanReferenceEvery=2 ; Lot
UnloadToAnotherCassette=0
NewCleanReferenceOption=1
"""


def test_summary_values_land_on_every_row_of_the_report():
    rep = collect.parse_report(LIVE_NAME, LIVE_HTML)
    rows = collect.rows_for_report("AOI-25", rep, "/nonexistent-scan-root")
    assert rows and all(r["wafers_scanned"] == "24" and r["avg_scan_time"] == "00:13:55" for r in rows)
    assert all(r["cr_every"] == "" and r["af_every"] == "" for r in rows)     # INI 를 못 찾았으면 설정도 없다


def test_read_recipe_settings_takes_the_comment_label_then_the_code_table(tmp_path):
    p = tmp_path / "Recipe.ini"
    p.write_text(RECIPE_INI, encoding="utf-8")
    assert collect.read_recipe_settings(str(p)) == {"cr_every": "Lot", "af_every": "Wafer"}
    p.write_text("[AutoCycle]\nAutoFocusEvery=1\nCleanReferenceEvery=3\n", encoding="utf-8")
    assert collect.read_recipe_settings(str(p)) == {"cr_every": "Wafer", "af_every": "None"}


@pytest.mark.parametrize("job,want", [("TB500_RDL3 - Multi", True), ("R_TB500_LIVE_PI4 - Enhanced", True),
                                      ("R_TB500_LIVE_PI2 AOI-21 Copy _0614", True), ("R_Kendall A0_PI3", False),
                                      ("2D@R2-GA285AAB_0859840PD-0A", False)])
def test_recipe_tab_jobs(job, want):
    assert collect.is_recipe_tab_job(job) is want


def test_settings_are_read_once_per_report_for_recipe_tab_jobs(tmp_path, fake_nas, monkeypatch):
    monkeypatch.setattr(collect, "RECIPE_TAB_JOB_RE", re.compile(""))       # 가짜 NAS 의 Job 도 대상으로
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "Recipe.ini").write_text(RECIPE_INI, encoding="utf-8")
    opened = []
    real = collect.read_recipe_settings
    monkeypatch.setattr(collect, "read_recipe_settings", lambda p: (opened.append(p), real(p))[1])
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "EXACT" and (r["cr_every"], r["af_every"]) == ("Lot", "Wafer")
    assert opened and all(p.endswith("Recipe.ini") and "K625407-01B0" in p for p in opened)


def test_other_jobs_never_open_recipe_ini(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "Recipe.ini").write_text(RECIPE_INI, encoding="utf-8")
    opened = []
    monkeypatch.setattr(collect, "read_recipe_settings", lambda p: opened.append(p) or {})
    [r] = _rows(tmp_path, csv_path)
    assert r["cr_every"] == "" and not opened


def test_stale_ini_folder_does_not_lend_its_settings(tmp_path, fake_nas, monkeypatch):
    monkeypatch.setattr(collect, "RECIPE_TAB_JOB_RE", re.compile(""))
    nas, csv_path = fake_nas
    d = _wafer_dir(nas)
    (d / "Recipe.ini").write_text(RECIPE_INI, encoding="utf-8")
    ini = d / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("13-Sep-26 05:31:04 PM", "20-Sep-26 05:31:04 PM")
                   .replace("13-Sep-26 05:32:02 PM", "20-Sep-26 05:32:02 PM"), encoding="utf-8")
    [r] = _rows(tmp_path, csv_path)
    assert r["ini_match"] == "STALE" and r["cr_every"] == ""


def test_synthetic_rows_carry_the_report_values():
    rows = [{c: "" for c in collect.OUT_COLS} | {"device": "AOI-1", "status": "Alignment Error.", "lot": "L", "wafer_id": "W",
                                                  "report": "r.htm", "batch_start": "15-Sep-26 06:23:14 PM",
                                                  "batch_end": "15-Sep-26 07:00:00 PM", "ini_match": "NOT_FOUND",
                                                  "wafers_scanned": "0", "avg_scan_time": "00:00:00", "cr_every": "Lot"}]
    out = collect.synthesize_rows(rows)
    batch = [r for r in out if r.get("kind") == "batch"]
    assert batch and batch[0]["wafers_scanned"] == "0" and batch[0]["cr_every"] == "Lot"
