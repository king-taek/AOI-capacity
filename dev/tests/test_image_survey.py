"""Review 이미지 순서 조사(10/22, `aoi_capacity/image_survey.py`) — 표본 고르기 · Wafer 폴더 안만 읽기 · 로컬 zip 한 장."""
from __future__ import annotations

import datetime as dt
import os
import zipfile

import pytest

from aoi_capacity import image_survey, nas_guard

NOW = dt.datetime(2026, 10, 22, 12, 0, 0)


def _row(job, lot, wafer, day, **over):
    r = {"kind": "", "ini_match": "EXACT", "job": job, "setup": "S1", "lot": lot, "wafer_id": wafer, "issue_codes": "",
         "batch_start": f"{day:02d}-Oct-26 09:00:00 AM", "batch_end": f"{day:02d}-Oct-26 10:00:00 AM", "report": f"{lot}.htm"}
    r.update(over)
    return r


def test_is_pi_and_clamp():
    assert image_survey.is_pi("R_TB500_LIVE_PI4") and image_survey.is_pi("TB500 PI2 Enhanced")
    assert not image_survey.is_pi("TB500_RDL3 - Multi") and not image_survey.is_pi("SPIKE")
    assert image_survey.clamp_days(0) == 1 and image_survey.clamp_days(999) == 90 and image_survey.clamp_days("x") == 7


def test_pick_samples_prefers_pi_spread_and_stays_in_scope(tmp_path):
    root = tmp_path / "AOI-9"
    reports = {}
    for i, d in enumerate(range(15, 22)):
        reports[f"dev:AOI-9|p{i}.htm"] = {"rows": [_row("R_TB500_LIVE_PI4", f"L{i}", "W1", d)]}
    reports["dev:AOI-9|o.htm"] = {"rows": [_row("TB500_RDL3 - Multi", "LO", "W1", 20)]}
    reports["dev:AOI-9|old.htm"] = {"rows": [_row("R_TB500_LIVE_PI4", "LOLD", "W1", 1)]}          # 기간 밖
    reports["dev:AOI-10|x.htm"] = {"rows": [_row("R_TB500_LIVE_PI4", "LX", "W1", 20)]}             # 다른 장비
    cache = {"reports": reports}
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-9"]}
    devs = [{"name": "AOI-9", "key": "dev:AOI-9", "path": str(root)}, {"name": "AOI-10", "key": "dev:AOI-10", "path": str(tmp_path / "AOI-10")}]
    got = image_survey.pick_samples(cache, cfg, devs, NOW - dt.timedelta(days=7))
    assert sum(g["pi"] for g in got) == 3 and sum(not g["pi"] for g in got) == 1
    assert {g["device"] for g in got} == {"AOI-9"}                          # 범위 밖 AOI-10 은 보지 않는다
    assert all(g["wafer_dir"].startswith(str(root)) for g in got)
    ends = sorted(g["end"] for g in got if g["pi"])
    assert ends[0].day == 16 and ends[-1].day == 21                         # 양 끝 포함해 고르게


def test_survey_wafer_reads_only_inside_and_lists_by_mtime(tmp_path):
    root = tmp_path / "AOI-9"
    w = root / "Scanresult" / "job" / "S1" / "L1" / "W1"
    (w / "Images").mkdir(parents=True)
    (w / "ScanLog.ini").write_text("[General]\nMachine=EagleG5\n", encoding="utf-8")
    (w / "ColorImageGrabingInfo.ini").write_text("[1]\nx=1\n", encoding="utf-8")
    (w / "ScanResultImageList.txt").write_text("a.jpg\nb.jpg\n", encoding="utf-8")
    (w / "Secret.dat").write_bytes(b"\0" * 10)
    for i, (n, t) in enumerate([("c1.jpg", 300), ("s1.jpg", 100), ("s2.jpg", 200)]):
        p = w / "Images" / n
        p.write_bytes(b"x")
        os.utime(p, (1_700_000_000 + t, 1_700_000_000 + t))
    s = {"device": "AOI-9", "root": str(root), "wafer_dir": str(w)}
    res = image_survey.survey_wafer(s, lambda n: True)
    assert set(res["files"]) == {"ScanLog.ini", "ColorImageGrabingInfo.ini", "ScanResultImageList.txt"}      # .dat 은 읽지 않는다
    body = res["listing"].split("# 하위 폴더 Images")[1]
    assert body.index("s1.jpg") < body.index("s2.jpg") < body.index("c1.jpg")                                # 수정 시각 순
    assert res["facts"]["top_jpg"] == 0 and "Images=3" in res["facts"]["subdirs"]
    assert image_survey.survey_wafer(s, lambda n: False)["files"] == {}                                      # 범위 밖 장비
    out = image_survey.survey_wafer({**s, "wafer_dir": str(tmp_path / "elsewhere")}, lambda n: True)
    assert out["files"] == {} and "밖" in out["note"]                                                        # 장비 폴더 밖 경로


def test_write_report_zip_and_refuses_nas(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    g = {"now": NOW, "days": 7, "cutoff": NOW, "probe": {}, "samples": [{
        "device": "AOI-9", "pi": True, "wafer_dir": "X", "row": _row("R_TB500_LIVE_PI4", "L1", "W1", 20),
        "result": {"listing": "# 맨 위\n", "files": {"ScanLog.ini": b"[General]\n"}, "note": "", "facts": {"top_files": 3, "top_jpg": 0, "subdirs": "Images=3"}}}]}
    path = image_survey.write_report(cfg, g, str(tmp_path / "out"))
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert {"요약.txt", "표본.tsv"} <= set(names) and any(n.endswith("/listing.txt") for n in names) and any(n.endswith("/ScanLog.ini") for n in names)
        assert "R_TB500_LIVE_PI4" in z.read("표본.tsv").decode()
    with pytest.raises(nas_guard.NasWriteRefused):
        image_survey.write_report(cfg, g, str(nas / "X"))


# ── 수집 창 카드 ────────────────────────────────────────────────────────────
def test_card_remembers_days_runs_and_blocks_collect(styled_qapp, fake_nas, tmp_path):
    import time

    pytest.importorskip("PyQt6.QtWidgets")
    from aoi_capacity import devices, i18n
    from aoi_capacity.ui.main_window import MainWindow
    from aoi_capacity.utils import paths, prefs
    from test_failures import _pump

    _nas, csv_path = fake_nas
    devices.write_devices_csv(paths.devices_csv_path(), devices.read_devices_csv(csv_path))
    prefs.patch(scope_devices=["*"])
    w = MainWindow()
    w.show()
    _pump(styled_qapp)
    page = w.collect_page
    page.wait_for_plan()
    _pump(styled_qapp, 0.2)
    assert page._is_days.value() == 7 and page._b_is_run.text() == i18n.KO.IMG_SURVEY_RUN
    page._is_days.setValue(14)
    assert prefs.load().image_survey_days == 14
    page._fl_out.setText(str(tmp_path / "is"))
    page._b_is_run.click()
    assert page.wafer_logs_running() and not page._b_is_run.isEnabled() and not page._b_fl_run.isEnabled() and not page._b_run.isEnabled()
    t0 = time.time()
    while page._fl_worker is not None and time.time() - t0 < 30:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.1)
    assert page._b_is_run.isEnabled() and page._b_run.isEnabled() and not page.wafer_logs_running()
    assert list((tmp_path / "is").glob("AOI_review_image_*.zip")), page._is_status.text()
    w.close()
    _pump(styled_qapp)


def test_gather_gives_devices_their_stable_key(tmp_path, fake_nas, monkeypatch):
    """resolve_devices 가 돌려준 장비에는 `key` 가 없다 — 수집과 같이 안정 키를 붙여야 캐시의 Report 와 이어진다(현장 KeyError 'key')."""
    nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    root = nas / "X" / "AOI-9"
    cache = {"reports": {"dev:AOI-9|r.htm": {"rows": [_row("R_TB500_LIVE_PI4", "L1", "W1", 21)]}}, "failed": {}, "devices": {"dev:AOI-9": {"name": "AOI-9", "ids": [str(root)], "aliases": []}},
             "last_mtime": {}, "kla": {}}
    monkeypatch.setattr(image_survey.collect, "_load_cache", lambda *a, **k: cache)
    g = image_survey.gather(cfg, 7, log=lambda m: None, now=NOW,
                            resolver=lambda c, log=None, should_stop=None: [{"name": "AOI-9", "path": str(root), "id": str(root)}])
    assert g["probe"]["ok"][0]["key"] == "dev:AOI-9"
    assert len(g["samples"]) == 1 and g["samples"][0]["pi"]


def test_parse_terms_and_pick_by_terms_ignores_the_day_window(tmp_path):
    assert image_survey.parse_terms("TB500.INT556  FTL,\nTB500.INT808 LNY") == [["tb500.int556", "ftl"], ["tb500.int808", "lny"]]
    assert image_survey.parse_terms("  ") == []
    root = tmp_path / "AOI-9"
    reports = {
        "dev:AOI-9|a.htm": {"rows": [_row("R_TB500_LIVE_PI2", "TB500.INT556 FTL", f"W{i}", 1) for i in range(10)]},   # 기간 밖이어도 찾는다
        "dev:AOI-9|b.htm": {"rows": [_row("R_TB500_LIVE_PI2", "TB500.INT808 LNY", "W1", 20)]},
        "dev:AOI-9|c.htm": {"rows": [_row("R_TB500_LIVE_PI2", "OTHER", "W1", 20)]},
    }
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-9"]}
    devs = [{"name": "AOI-9", "key": "dev:AOI-9", "path": str(root)}]
    got = image_survey.pick_by_terms({"reports": reports}, cfg, devs, image_survey.parse_terms("TB500.INT556 FTL, TB500.INT808 LNY"))
    assert {g["row"]["lot"] for g in got} == {"TB500.INT556 FTL", "TB500.INT808 LNY"}
    assert sum(g["row"]["lot"] == "TB500.INT556 FTL" for g in got) == image_survey.PER_DEVICE_PI * 2     # Report 마다 6장
    assert not image_survey.pick_by_terms({"reports": reports}, {"scan_dir": "Scanresult", "scope_devices": ["AOI-10"]}, devs, [["ftl"]])   # 범위 밖 장비


def test_default_terms_parse_to_the_two_reported_lots():
    assert image_survey.parse_terms(image_survey.DEFAULT_TERMS_TEXT) == [["ftl-pids7"], ["lny-pids7"]]


def test_pixel_survey_reads_only_two_inis_and_names_and_flags_zero(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    assert image_survey.pixel_is_zero("0|0") and not image_survey.pixel_is_zero("0|0.4645") and not image_survey.pixel_is_zero("")
    root = tmp_path / "AOI-9"
    w = root / "Scanresult" / "job" / "S1" / "L1" / "W1"
    w.mkdir(parents=True)
    (w / "RecipesInfo.ini").write_text("[Recipe-1]\nColorPixelSize=0\nVerCam=4\nVerMag=7.5\n[Recipe-2]\nColorPixelSize=0\nVerCam=4\nVerMag=7.5\n", encoding="utf-8")
    (w / "ColorImageGrabingInfo.ini").write_text("[a.c.1.jpeg]\nRecipeNumber=0\n", encoding="utf-8")
    (w / "5.6.c.7.jpeg").write_bytes(b"x")
    (w / "1.2.t.1.jpeg").write_bytes(b"x")
    (w / "Secret.dat").write_bytes(b"\0")
    s = {"device": "AOI-9", "root": str(root), "wafer_dir": str(w)}
    x = image_survey.read_pixel(s, lambda n: True)
    assert x["color_pixel"] == "0|0" and x["ver"] == "4|7.5|4|7.5" and x["cg_recipes"] == "0" and (x["n_scan"], x["n_color"]) == (1, 1)
    assert image_survey.read_pixel(s, lambda n: False)["color_pixel"] == ""                      # 범위 밖 장비
    g = {"now": NOW, "days": 14, "cutoff": NOW, "probe": {}, "samples": [{"device": "AOI-9", "pi": True, "wafer_dir": str(w),
         "row": _row("R_TB500_LIVE_PI2 - Enhanced", "L1", "W1", 20, faults="5"), "result": x}]}
    path = image_survey.write_pixel_report(cfg, g, str(tmp_path / "out"))
    with zipfile.ZipFile(path) as z:
        assert "0 인 것 1장" in z.read("요약.txt").decode() and "Lot L1" in z.read("요약.txt").decode()
        assert "R_TB500_LIVE_PI2 - Enhanced" in z.read("픽셀.tsv").decode()
    with pytest.raises(nas_guard.NasWriteRefused):
        image_survey.write_pixel_report(cfg, g, str(nas / "X"))


def test_pick_pixel_samples_spreads_lots_per_job_and_prefers_defects(tmp_path):
    root = tmp_path / "AOI-9"
    reports = {f"dev:AOI-9|p{i}.htm": {"rows": [_row("JOB_A", f"L{i}", "W0", 15 + i, faults="0", scan_mode="MULTI"), _row("JOB_A", f"L{i}", "W1", 15 + i, faults="3", scan_mode="MULTI")]} for i in range(6)}
    reports["dev:AOI-9|b.htm"] = {"rows": [_row("JOB_B", "LB", "W1", 20, faults="2", scan_mode="MULTI")]}
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-9"]}
    devs = [{"name": "AOI-9", "key": "dev:AOI-9", "path": str(root)}]
    got = image_survey.pick_pixel_samples({"reports": reports}, cfg, devs, NOW - dt.timedelta(days=14))
    assert sum(g["row"]["job"] == "JOB_A" for g in got) == 3 and sum(g["row"]["job"] == "JOB_B" for g in got) == 1
    assert all(g["row"]["wafer_id"] == "W1" for g in got)                                         # Defect 있는 Wafer 우선


def test_pick_pixel_samples_skips_non_multi_and_round_robins_devices(tmp_path):
    reports = {}
    for dn in ("AOI-1", "AOI-2"):
        for i in range(5):
            reports[f"dev:{dn}|p{i}.htm"] = {"rows": [_row(f"R_PI4_{i}", f"L{i}", "W1", 20, faults="3")]}                # Job 이 달라 5그룹 × 장비
        reports[f"dev:{dn}|2d.htm"] = {"rows": [_row("2D@R2-X", "LX", "W1", 20, faults="3")]}                           # 단일 · 2D — 제외
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-1", "AOI-2"]}
    devs = [{"name": n, "key": f"dev:{n}", "path": str(tmp_path / n)} for n in ("AOI-1", "AOI-2")]
    got = image_survey.pick_pixel_samples({"reports": reports}, cfg, devs, NOW - dt.timedelta(days=14), max_total=4)
    assert not any(g["row"]["job"].startswith("2D") for g in got)
    assert {g["device"] for g in got} == {"AOI-1", "AOI-2"} and len(got) == 4                                       # 상한이어도 두 장비 모두
