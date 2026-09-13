"""CollectorWorker — 스레드를 띄우지 않고 run() 을 직접 불러 시그널·취소·실패 경로를 검사한다."""
from __future__ import annotations

import pytest

from conftest import make_cfg

pytest.importorskip("PyQt6.QtCore")


def _collect_signals(worker):
    got = {"progress": [], "device": [], "log": [], "done": [], "failed": [], "cancelled": []}
    s = worker.signals
    s.progress.connect(lambda *a: got["progress"].append(a))
    s.device.connect(lambda *a: got["device"].append(a))
    s.log.connect(lambda *a: got["log"].append(a))
    s.done.connect(lambda *a: got["done"].append(a))
    s.failed.connect(lambda *a: got["failed"].append(a))
    s.cancelled.connect(lambda *a: got["cancelled"].append(a))
    return got


def test_run_emits_done_with_result(qapp, fake_nas, tmp_path):
    from aoi_capacity.workers.collector import CollectorWorker

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    w = CollectorWorker(7, cfg)
    got = _collect_signals(w)
    w.run()
    assert not got["failed"] and not got["cancelled"]
    (tok, res), = got["done"]
    assert tok == 7 and res.rows > 0 and res.devices >= 2
    assert res.html_path.endswith(".html") and res.elapsed >= 0
    assert all(t == 7 for t, *_ in got["progress"])
    assert got["progress"][-1][1] == got["progress"][-1][2]        # 마지막 진행은 (total,total)
    states = {(n, s) for _, n, s, _ in got["device"]}
    assert ("9호기", "done") in states


def test_stop_before_run_emits_cancelled_and_leaves_no_cache(qapp, fake_nas, tmp_path):
    from aoi_capacity.workers.collector import CollectorWorker
    from pathlib import Path

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    w = CollectorWorker(1, cfg)
    got = _collect_signals(w)
    w.stop()
    assert w.is_cancelled()
    w.run()
    assert got["cancelled"] == [(1,)] and not got["done"]
    assert not Path(cfg["cache_file"]).exists()
    assert not Path(cfg["output_dir"], "AOI_capacity.html").exists()


def test_failure_is_reported_not_raised(qapp, fake_nas, tmp_path):
    from aoi_capacity.workers.collector import CollectorWorker

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, cache_file=str(nas / "X" / "AOI-9" / "aoi_cache.json"))  # NAS 아래 → 거부
    w = CollectorWorker(3, cfg)
    got = _collect_signals(w)
    w.run()
    (tok, msg), = got["failed"]
    assert tok == 3 and "NasWriteRefused" in msg
    assert not (nas / "X" / "AOI-9" / "aoi_cache.json").exists()
