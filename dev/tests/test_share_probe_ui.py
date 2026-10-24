"""수집 창의 '공유 폴더 시험' 카드(10/24) — 워커가 scripts/share_probe.py 를 파일 경로로 불러 bat 없이 같은 시험을 하는지.

- 시험 · 교체 시험 · 지우기 세 가지 일. 쓰기는 공유 폴더 안 `_aoi_share_probe` 와 로컬 결과 폴더뿐이다.
- 공유 폴더가 장비 NAS 아래면 아무것도 쓰지 않고 멈춘다. devices.csv 가 없으면 교체 시험도 멈춘다.
- 카드 버튼은 도는 동안 꺼지고, 교체 시험만 '멈춤' 이 보인다.
"""
from __future__ import annotations

import time

import pytest

pytest.importorskip("PyQt6.QtWidgets")


def _csv(tmp_path, nas):
    (nas / "AOI-1").mkdir(parents=True, exist_ok=True)
    csv = tmp_path / "devices.csv"
    csv.write_text(f"장비명,NAS경로,폴더,사용\nAOI-1,{nas},AOI-1,Y\n", encoding="utf-8")
    return csv


def _run(worker):
    got, lines = {}, []
    worker.log.connect(lines.append)
    worker.done.connect(lambda job, r, e: got.update(job=job, result=r, error=e))
    worker.run()                                   # 스레드 없이 — 시그널은 같은 스레드라 바로 불린다
    return got, lines


SMALL = ("--sizes", "0.01", "--gz-raw-mb", "0.01")


def test_probe_then_clean_writes_only_inside_the_probe_folder(tmp_path):
    from aoi_capacity.workers import share_probe

    share = tmp_path / "share"
    share.mkdir()
    (share / "남의 파일.txt").write_text("x", encoding="utf-8")
    csv = _csv(tmp_path, tmp_path / "nas")
    out = tmp_path / "local"
    w = share_probe.ShareProbeWorker({}, "probe", str(share), out_dir=str(out), devices_csv=str(csv), extra_args=SMALL)
    got, lines = _run(w)
    assert got["error"] == "" and got["job"] == "probe"
    assert got["result"]["guide"].endswith("시험_안내.html")
    assert sorted(p.name for p in share.iterdir()) == ["_aoi_share_probe", "남의 파일.txt"]
    assert list(out.glob("공유시험_*.json")) and got["result"]["saved"].startswith(str(out))
    assert any("팀원에게 보낼 경로" in s for s in lines)

    got, _ = _run(share_probe.ShareProbeWorker({}, "clean", str(share), out_dir=str(out), devices_csv=str(csv)))
    assert got["error"] == "" and len(got["result"]["gone"]) == 4
    assert (share / "남의 파일.txt").read_text(encoding="utf-8") == "x"


def test_refuses_a_target_on_the_device_nas(tmp_path):
    from aoi_capacity.workers import share_probe

    nas = tmp_path / "nas"
    csv = _csv(tmp_path, nas)
    w = share_probe.ShareProbeWorker({}, "probe", str(nas / "AOI-1"), out_dir=str(tmp_path / "o"), devices_csv=str(csv), extra_args=SMALL)
    got, _ = _run(w)
    assert got["result"] is None and got["error"].startswith("멈췄습니다")
    assert list((nas / "AOI-1").iterdir()) == []


def test_hammer_needs_devices_csv_and_stops_on_request(tmp_path):
    from aoi_capacity.workers import share_probe

    share = tmp_path / "share"
    share.mkdir()
    got, _ = _run(share_probe.ShareProbeWorker({}, "hammer", str(share), out_dir=str(tmp_path / "o"),
                                               devices_csv=str(tmp_path / "없음.csv")))
    assert got["result"] is None and "devices.csv" in got["error"]
    assert not (share / "_aoi_share_probe").exists()

    csv = _csv(tmp_path, tmp_path / "nas")
    w = share_probe.ShareProbeWorker({}, "hammer", str(share), out_dir=str(tmp_path / "o"), devices_csv=str(csv))
    w.done.connect(lambda *_: None)
    calls = []
    w.log.connect(lambda s: calls.append(s) or (len(calls) >= 2 and w.stop()))   # 첫 교체가 끝나면 멈춤
    t0 = time.time()
    got, _ = _run(w)
    assert time.time() - t0 < 10
    assert got["error"] == "" and len(got["result"]["rounds"]) == 1 and got["result"]["fail"] == 0


def test_empty_target_and_missing_tool_say_why(tmp_path):
    from aoi_capacity.workers import share_probe

    got, _ = _run(share_probe.ShareProbeWorker({}, "probe", "  "))
    assert got["error"] == share_probe.K.SHARE_PROBE_NO_TARGET
    got, _ = _run(share_probe.ShareProbeWorker({}, "probe", str(tmp_path), tool_path=tmp_path / "없음.py"))
    assert "도구 파일이 없습니다" in got["error"]


def test_card_buttons_follow_the_running_job(qapp, tmp_path):
    from aoi_capacity.ui.pages.collect_page import CollectPage
    from aoi_capacity.workers import share_probe

    page = CollectPage()
    assert page._sp_target.text() == share_probe.default_target() != ""
    assert page._b_sp_stop.isHidden()
    page._set_share_probe_running(True, "hammer")
    assert not page._b_sp_run.isEnabled() and not page._b_sp_clean.isEnabled() and not page._b_sp_stop.isHidden()
    page._set_share_probe_running(False, "hammer")
    assert page._b_sp_run.isEnabled() and page._b_sp_stop.isHidden()
    page._set_share_probe_running(True, "probe")
    assert page._b_sp_stop.isHidden()
    page._on_share_probe_done("clean", {"gone": ["a", "b"]}, "")
    assert page._sp_status.text() == share_probe.K.SHARE_PROBE_CLEAN_DONE_FMT.format(n=2)
    page.deleteLater()
