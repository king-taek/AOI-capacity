"""No image 점검(10/22, `aoi_capacity/no_image.py`) — NO IMAGE 재스캔과 원래 스캔 짝 · Wafer 폴더 안만 읽기 · 8MB 이하 로컬 zip 한 장."""
from __future__ import annotations

import datetime as dt
import os
import zipfile

import pytest

from aoi_capacity import nas_guard, no_image

NOW = dt.datetime(2026, 10, 22, 12, 0, 0)


def _row(job, lot, wafer, day, hour=9, **over):
    r = {"kind": "", "ini_match": "EXACT", "job": job, "setup": "S1", "lot": lot, "wafer_id": wafer, "issue_codes": "", "outcome": "PASS",
         "batch_start": f"{day:02d}-Oct-26 {hour:02d}:00:00 AM", "batch_end": f"{day:02d}-Oct-26 {hour:02d}:30:00 AM", "report": f"{lot}.htm"}
    r.update(over)
    return r


def _env(tmp_path):
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-4", "AOI-11"]}
    devs = [{"name": "AOI-4", "key": "dev:AOI-4", "path": str(tmp_path / "AOI-4")}, {"name": "AOI-11", "key": "dev:AOI-11", "path": str(tmp_path / "AOI-11")}]
    return cfg, devs


def test_is_no_image_and_clamp():
    assert no_image.is_no_image({"lot": "MBV-NO IMAGE"}) and no_image.is_no_image({"lot": "x", "report": "a_FMB_0929N NO_IMAGE_26.htm"})
    assert not no_image.is_no_image({"lot": "MBV-3D", "report": "a.htm"})
    assert no_image.clamp_days(0) == 1 and no_image.clamp_days(999) == 90 and no_image.clamp_days("x") == 60


def test_pick_cases_pairs_rescan_with_latest_earlier_pass_of_same_wafer(tmp_path):
    cfg, devs = _env(tmp_path)
    cache = {"reports": {
        "dev:AOI-11|o1.htm": {"rows": [_row("J", "MBV", "W1", 5)]},
        "dev:AOI-11|o2.htm": {"rows": [_row("J", "MBV", "W1", 15)]},                                   # 더 가까운 원래 스캔
        "dev:AOI-11|fail.htm": {"rows": [_row("J", "MBV", "W1", 18, outcome="ABORTED")]},               # PASS 가 아님
        "dev:AOI-4|ni.htm": {"rows": [_row("J", "MBV-NO IMAGE", "W1", 20), _row("J", "MBV-NO IMAGE", "W2", 20), _row("J", "MBV-NO IMAGE", "W3", 20)]},
        "dev:AOI-4|old.htm": {"rows": [_row("J", "OLD-NO IMAGE", "W9", 1)]},                           # 기간 밖
        "dev:AOI-9|x.htm": {"rows": [_row("J", "ZZZ-NO IMAGE", "W1", 21)]},                             # 범위 밖 장비
    }}
    got = no_image.pick_cases(cache, cfg, devs, NOW - dt.timedelta(days=10))
    assert [c["rescan"]["row"]["wafer_id"] for c in got] == ["W1", "W3"]                                 # 처음 · 끝
    assert got[0]["original"]["device"] == "AOI-11" and got[0]["original"]["row"]["batch_start"].startswith("15-Oct")
    assert got[1]["original"] is None                                                                    # 원래 스캔 없음도 사례로 남는다
    assert all(c["rescan"]["device"] == "AOI-4" for c in got)


def _wafer(root, lot, wafer, extra=None):
    w = root / "Scanresult" / "J" / "S1" / lot / wafer
    (w / "Zones").mkdir(parents=True)
    (w / "ScanLog.ini").write_text("[General]\nMachine=EagleG5\n", encoding="utf-8")
    (w / "Recipe.ini").write_text("[Recipe]\nDieQuota=10\n", encoding="utf-8")
    (w / "Zones" / "z.ini").write_text("[Z]\na=1\n", encoding="utf-8")
    (w / "defect.jpg").write_bytes(b"\xff" * 10)
    (w / "Secret.dat").write_bytes(b"\0" * 10)
    for n, d in (extra or {}).items():
        (w / n).write_bytes(d)
    return w


def test_read_wafer_reads_text_only_inside_scope(tmp_path):
    root = tmp_path / "AOI-4"
    w = _wafer(root, "L1", "W1")
    s = {"device": "AOI-4", "root": str(root), "wafer_dir": str(w)}
    res = no_image.read_wafer(s, lambda n: True)
    assert set(res["files"]) == {"ScanLog.ini", "Recipe.ini", "Zones/z.ini"} and "defect.jpg" in res["listing"]
    assert no_image.read_wafer(s, lambda n: False)["files"] == {}
    out = no_image.read_wafer({**s, "wafer_dir": str(tmp_path / "elsewhere")}, lambda n: True)
    assert out["files"] == {} and "밖" in out["note"]


def _case(root, n, size=0):
    w = _wafer(root, f"L{n}", "W1", {"big.txt": os.urandom(size)} if size else None)
    row = _row("J", f"L{n}-NO IMAGE", f"W{n}", 20)
    s = {"device": "AOI-4", "root": str(root), "wafer_dir": str(w), "row": row}
    s["result"] = no_image.read_wafer(s, lambda n: True)
    return {"rescan": s, "original": dict(s)}


def test_write_report_zip_stays_under_8mb_and_refuses_nas(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    root = tmp_path / "AOI-4"
    # 압축이 안 되는 무작위 256KB 파일을 사례마다 둬서 상한(8MB)을 확실히 넘긴다
    g = {"now": NOW, "days": 60, "cutoff": NOW, "probe": {}, "cases": [_case(root, n, 256 * 1024) for n in range(1, 21)]}
    path, dropped = no_image.write_report(cfg, g, str(tmp_path / "out"))
    assert os.path.getsize(path) <= no_image.MAX_ZIP_BYTES and dropped > 0
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert {"요약.txt", "사례.tsv"} <= set(names) and any(n.endswith("/rescan/Recipe.ini") for n in names)
        assert not any(n.endswith(".dat") or n.endswith(".jpg") for n in names)
        assert "NO IMAGE" in z.read("사례.tsv").decode()
    with pytest.raises(nas_guard.NasWriteRefused):
        no_image.write_report(cfg, g, str(nas / "X"))


def test_small_report_has_no_dropped_files(tmp_path, fake_nas):
    _nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    g = {"now": NOW, "days": 60, "cutoff": NOW, "probe": {}, "cases": [_case(tmp_path / "AOI-4", 1)]}
    path, dropped = no_image.write_report(cfg, g, str(tmp_path / "out"))
    assert dropped == 0 and os.path.getsize(path) < 100_000


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
    assert page._ni_days.value() == 60 and page._b_ni_run.text() == i18n.KO.NO_IMAGE_RUN
    page._ni_days.setValue(30)
    assert prefs.load().no_image_days == 30
    page._fl_out.setText(str(tmp_path / "ni"))
    page._b_ni_run.click()
    assert page.wafer_logs_running() and not page._b_ni_run.isEnabled() and not page._b_is_run.isEnabled() and not page._b_run.isEnabled()
    t0 = time.time()
    while page._fl_worker is not None and time.time() - t0 < 30:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.1)
    assert page._b_ni_run.isEnabled() and page._b_run.isEnabled() and not page.wafer_logs_running()
    assert list((tmp_path / "ni").glob("AOI_no_image_*.zip")), page._ni_status.text()
    w.close()
    _pump(styled_qapp)


def test_gather_gives_resolved_devices_their_stable_keys(tmp_path, fake_nas):
    """장비 확인이 돌려준 dict 에는 `key` 가 없다 — 수집과 같은 `_assign_device_keys` 로 붙여야 캐시의 `dev:<이름>|…` 키와 맞는다."""
    _nas, csv_path = fake_nas
    from conftest import make_cfg
    cfg = make_cfg(tmp_path, csv_path)
    devs = [{"name": "AOI-4", "id": str(tmp_path / "AOI-4"), "path": str(tmp_path / "AOI-4")}]
    cache = {"reports": {"dev:AOI-4|ni.htm": {"rows": [_row("J", "MBV-NO IMAGE", "W1", 20)]}}, "devices": {}, "last_mtime": {}}
    from aoi_capacity import collect
    collect._assign_device_keys(cache, devs, cfg, collect._Dirty())
    assert devs[0]["key"] == "dev:AOI-4"
    cfg = {"scan_dir": "Scanresult", "scope_devices": ["AOI-4"]}
    assert len(no_image.pick_cases(cache, cfg, devs, NOW - dt.timedelta(days=10))) == 1
