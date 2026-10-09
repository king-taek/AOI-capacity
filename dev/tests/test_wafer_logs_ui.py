"""수집 창의 'Wafer 폴더 로그 모으기' 카드(10/9) — 워커가 도구 스크립트를 같은 게이트로 부르는지, 카드 버튼이 맞게 켜지고 꺼지는지.

- 장비는 가동률 수집과 같은 `devices.resolve_devices` 를 지난 것만 넘긴다(범위 밖 장비에는 접근하지 않는다).
- 저장 위치가 NAS 아래면 시작하지 않는다. NAS 아래는 실행 전후로 그대로다.
- 로그를 모으는 동안에는 가동률 수집을 시작할 수 없다(NAS 를 함께 읽지 않게).
"""
from __future__ import annotations

import os
import time
import zipfile

import pytest

from conftest import make_cfg

pytest.importorskip("PyQt6.QtWidgets")


def _snapshot(base):
    out = {}
    for d, dirs, files in os.walk(base):
        for n in dirs + files:
            p = os.path.join(d, n)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def _run(worker):
    got = {}
    lines = []
    worker.log.connect(lines.append)
    worker.done.connect(lambda r, e: got.update(result=r, error=e))
    worker.run()                                   # 스레드 없이 — 시그널은 같은 스레드라 바로 불린다
    return got, lines


def test_worker_collects_through_the_scope_gate(tmp_path, fake_nas):
    from aoi_capacity.workers import wafer_logs

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    before = _snapshot(nas)
    out = tmp_path / "wl"
    got, lines = _run(wafer_logs.WaferLogsWorker(cfg, str(out), extra_args=["--days", "100000", "--min-lots", "1"]))
    assert got["error"] == "" and got["result"]["parts"]
    assert _snapshot(nas) == before
    names = []
    for p in got["result"]["parts"]:
        with zipfile.ZipFile(p) as z:
            names += z.namelist()
    assert any(n.endswith("/WaferInfo.ini") for n in names) and "요약.txt" in names
    from aoi_capacity import devices
    gate = {os.path.basename(str(d["path"]).rstrip("/\\")) for d in devices.resolve_devices(cfg)}
    lot_devs = {n.split("/")[0].split("_", 1)[1].rsplit("_", 1)[0] for n in names if "/" in n}
    assert lot_devs and lot_devs <= gate                               # 수집과 같은 게이트를 지난 장비만


def test_worker_reads_nothing_out_of_scope(tmp_path, fake_nas, monkeypatch):
    from aoi_capacity.workers import wafer_logs

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, scope_devices=["AOI-25"])    # 가짜 장비는 전부 범위 밖
    seen = []
    tool = wafer_logs.load_tool()
    monkeypatch.setattr(wafer_logs, "load_tool", lambda *_a, **_k: tool)
    monkeypatch.setattr(tool, "survey_device", lambda *a, **k: seen.append(a) or {})
    got, _ = _run(wafer_logs.WaferLogsWorker(cfg, str(tmp_path / "wl")))
    assert got["result"] is None and got["error"] == wafer_logs.K.WAFER_LOGS_NO_DEVICES and not seen


def test_worker_refuses_output_under_nas(tmp_path, fake_nas):
    from aoi_capacity.workers import wafer_logs

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    before = _snapshot(nas)
    got, _ = _run(wafer_logs.WaferLogsWorker(cfg, str(nas / "X" / "AOI-9" / "out")))
    assert got["result"] is None and got["error"]
    assert _snapshot(nas) == before


def test_worker_reports_missing_tool(tmp_path, fake_nas):
    from aoi_capacity.workers import wafer_logs

    _nas, csv_path = fake_nas
    got, _ = _run(wafer_logs.WaferLogsWorker(make_cfg(tmp_path, csv_path), str(tmp_path / "wl"), tool_path=tmp_path / "없음.py"))
    assert got["result"] is None and "없음.py" in got["error"]


def test_worker_names_an_outdated_tool_file(tmp_path, fake_nas):
    """10/9 현장: 손으로 넣은 첫 판(parse_args 없음)이 새 파일을 덮어 'AttributeError' 만 보였다 — 이제 옛 판이라고 경로와 함께 말한다."""
    from aoi_capacity.workers import wafer_logs

    _nas, csv_path = fake_nas
    old = tmp_path / "collect_wafer_logs.py"
    old.write_text("def run(args):\n    return 0\n\n\ndef main(argv=None):\n    return 0\n", encoding="utf-8")
    got, _ = _run(wafer_logs.WaferLogsWorker(make_cfg(tmp_path, csv_path), str(tmp_path / "wl"), tool_path=old))
    assert got["result"] is None and got["error"] == wafer_logs.K.WAFER_LOGS_OLD_TOOL_FMT.format(path=old)
    assert wafer_logs.load_tool().TOOL_API == wafer_logs.TOOL_API     # 저장소의 도구와 워커는 같은 판


def test_tool_is_shipped_with_updates():
    from aoi_capacity.utils import updater
    from aoi_capacity.workers import wafer_logs

    assert wafer_logs.TOOL_PATH.is_file()
    assert {"collect_wafer_logs.py", "make_wafer_logs.bat"} <= updater._UPDATE_KEEP_ONLY["scripts"]


def _pump(app, secs=0.05):
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        time.sleep(0.005)


def test_card_runs_and_blocks_collect_meanwhile(styled_qapp, fake_nas, tmp_path, monkeypatch):
    from aoi_capacity import devices, i18n
    from aoi_capacity.ui.main_window import MainWindow
    from aoi_capacity.utils import paths, prefs
    from aoi_capacity.workers import wafer_logs

    _nas, csv_path = fake_nas
    devices.write_devices_csv(paths.devices_csv_path(), devices.read_devices_csv(csv_path))
    prefs.patch(scope_devices=["*"])

    class Worker(wafer_logs.WaferLogsWorker):          # 가짜 NAS 의 Report 는 9/13 — 기간을 넓혀 준다
        def __init__(self, cfg, out_dir, parent=None):
            super().__init__(cfg, out_dir, parent, extra_args=["--days", "100000", "--min-lots", "1"])
    monkeypatch.setattr(wafer_logs, "WaferLogsWorker", Worker)

    w = MainWindow()
    w.show()
    _pump(styled_qapp)
    page = w.collect_page
    page.wait_for_plan()
    _pump(styled_qapp, 0.2)
    assert page._b_wl_run.text() == i18n.KO.WAFER_LOGS_RUN and page._wl_out.text()
    page._wl_out.setText(str(tmp_path / "wl"))
    page._b_wl_run.click()
    assert page.wafer_logs_running() and not page._b_run.isEnabled() and not page._b_wl_run.isEnabled()
    assert page._b_wl_stop.isVisibleTo(page)
    from aoi_capacity.ui import main_window as mw
    warned = []
    monkeypatch.setattr(mw.sheets, "warn", lambda *a: warned.append(a))
    w._start_collect(False, False)                      # 로그를 모으는 동안에는 수집이 시작되지 않는다
    assert not w.is_collecting() and warned and warned[0][2] == i18n.KO.WAFER_LOGS_BUSY
    t0 = time.time()
    while page.wafer_logs_running() and time.time() - t0 < 30:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.1)
    assert not page.wafer_logs_running()
    assert page._b_run.isEnabled() and page._b_wl_run.isEnabled() and not page._b_wl_stop.isVisibleTo(page)
    assert page._wl_status.text().startswith(i18n.KO.WAFER_LOGS_DONE_FMT.split("{")[0])
    assert list((tmp_path / "wl").glob("*_part01.zip"))
    w.close()
    _pump(styled_qapp)
