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


def test_csv_lock_completes_with_warnings_not_failed(qapp, fake_nas, tmp_path, monkeypatch):
    """★ C06: Excel 이 CSV 를 잡고 있어도 HTML·캐시는 정상 — done 으로 끝내되 상태는 completed_with_warnings, 사유는 ko.py 문구."""
    import os
    from aoi_capacity import i18n
    from aoi_capacity.workers.collector import CollectorWorker, STATE_COMPLETED_WITH_WARNINGS

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    real = os.replace

    def locked(src, dst, *a, **k):
        if str(dst).lower().endswith(".csv"):
            raise PermissionError(13, "다른 프로세스가 사용 중", str(dst))
        return real(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", locked)
    w = CollectorWorker(9, cfg)
    got = _collect_signals(w)
    w.run()
    assert not got["failed"] and not got["cancelled"]
    (tok, res), = got["done"]
    assert tok == 9 and res.state == STATE_COMPLETED_WITH_WARNINGS and res.html_path.endswith(".html")
    assert len(res.warnings) == 1 and res.warnings[0]["kind"] == "csv"
    line = res.warning_lines[0]
    assert line.startswith(i18n.KO.COLLECT_DONE_CSV_FAILED_FMT.split("{")[0]) and "PermissionError" in line
    assert any(line == m for _t, m in got["log"])                    # 로그에도 같은 문장이 남는다
    assert res.cache_status == "missing"                              # 첫 수집(캐시 파일 없음) — 손상(corrupt)이 아니다


def test_html_lock_is_still_reported_as_failure(qapp, fake_nas, tmp_path, monkeypatch):
    import os
    from aoi_capacity.workers.collector import CollectorWorker

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    real = os.replace

    def locked(src, dst, *a, **k):
        if str(dst).lower().endswith(".html"):
            raise PermissionError(13, "잠김", str(dst))
        return real(src, dst, *a, **k)

    monkeypatch.setattr(os, "replace", locked)
    w = CollectorWorker(4, cfg)
    got = _collect_signals(w)
    w.run()
    (tok, msg), = got["failed"]
    assert tok == 4 and "PermissionError" in msg and not got["done"]


def test_worker_passes_refresh_and_rebuild_through(qapp, fake_nas, tmp_path, monkeypatch):
    from aoi_capacity import collect
    from aoi_capacity.workers.collector import CollectorWorker

    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    seen = []
    real = collect.collect

    def spy(cfg_, *a, **k):
        seen.append((k.get("refresh_window_days"), k.get("rebuild_all")))
        return real(cfg_, *a, **k)

    monkeypatch.setattr(collect, "collect", spy)
    for kw in ({}, {"refresh_window_days": 30}, {"rebuild_all": True}):
        w = CollectorWorker(1, cfg, **kw)
        _collect_signals(w)
        w.run()
    assert seen == [(None, None), (30, None), (None, True)]
    assert CollectorWorker(2, cfg, full=True).full is True           # GUI 의 '전체 다시 만들기' 는 full 로 들어온다


def test_publish_result_reaches_the_done_result(qapp, fake_nas, tmp_path):
    """10/30: 수집 끝의 조용한 배포 결과가 CollectResult 로 나온다 — 올렸으면 폴더, 못 올렸으면 경고(수집은 그대로 성공)."""
    from aoi_capacity import i18n
    from aoi_capacity.workers.collector import CollectorWorker

    nas, csv_path = fake_nas
    share = tmp_path / "share"
    cfg = make_cfg(tmp_path, csv_path, publish_dir=str(share))
    w = CollectorWorker(11, cfg)
    got = _collect_signals(w)
    w.run()
    (tok, res), = got["done"]
    assert not got["failed"] and res.published == str(share) and not res.warnings
    assert (share / "AOI_LOT.html").is_file()

    blocker = tmp_path / "not_a_dir"
    blocker.write_text("x")
    cfg2 = make_cfg(tmp_path / "again", csv_path, publish_dir=str(blocker / "sub"))
    w2 = CollectorWorker(12, cfg2)
    got2 = _collect_signals(w2)
    w2.run()
    (tok, res2), = got2["done"]
    assert not got2["failed"] and res2.published == "" and res2.html_path.endswith(".html")      # 수집은 성공
    assert [x["kind"] for x in res2.warnings] == ["publish"] and res2.state == "completed_with_warnings"
    assert res2.warning_lines[0].startswith(i18n.KO.COLLECT_DONE_PUBLISH_FAILED_FMT.split("{")[0])
