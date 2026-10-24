"""옛 기간 빈칸 채우기(10/24, `collect.fill_gaps`) — 스캔 비율(scan_sec) · 파라미터 · RDL 판정이 빈 옛 행을 Wafer 폴더 안만 읽어 채운다.

Report 는 다시 읽지 않고, ScanLog 의 시작이 그 장의 INI 시각 밖이면(나중 검사로 폴더가 다시 쓰임) 값을 지어내지 않는다."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aoi_capacity import collect, nas_guard
from conftest import make_cfg

SCANLOG = "[General]\nStartScan=9/13/2026 5:31:10 PM\nDuration=30000\n"


def _wafer_dirs(nas: Path):
    return [p for p in nas.rglob("K625407-01B0") if (p / "WaferInfo.ini").is_file()]


def _cache(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def _sec_rows(cfg):
    return [r for e in _cache(cfg)["reports"].values() for r in e["rows"] if r.get("ini_match") == "EXACT" and not r.get("kind")]


def test_fill_gaps_fills_scan_ratio_from_wafer_folder_only_and_marks_reports(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(dict(cfg, collect_params=False))                        # ScanLog 가 없던 때 — 옛 행처럼 scan_sec 이 빈다
    rows = _sec_rows(cfg)
    assert rows and all(not r.get("scan_sec") for r in rows)
    plan = collect.plan_run(cfg)
    assert plan.sec_missing == len(rows) and plan.sec_reports >= 1 and plan.sec_have == 0 and plan.sec_from
    assert plan.etas["sec"][0] is not None
    for w in _wafer_dirs(nas):
        (w / "ScanLog.ini").write_text(SCANLOG, encoding="utf-8")
    opened = []
    real = nas_guard.read_bytes
    monkeypatch.setattr(nas_guard, "read_bytes", lambda p, *a, **k: opened.append(str(p)) or real(p, *a, **k))
    st = collect.fill_gaps(cfg)
    assert not st["stopped"] and st["sec"]["filled"] == len(rows) and st["params"]["targets"] >= 1
    assert not any(p.lower().endswith((".htm", ".html")) for p in opened)    # Report 는 다시 읽지 않는다
    assert all(r["scan_sec"] == "30" for r in _sec_rows(cfg))                 # Duration 30초(장 시간 58초 안)
    after = collect.plan_run(cfg)
    assert after.sec_missing == 0 and after.sec_have == len(rows) and after.params_missing == 0
    opened.clear()
    st2 = collect.fill_gaps(cfg)                                              # 두 번째는 할 일이 없다 — NAS 의 Wafer 폴더를 열지 않는다
    assert st2["sec"]["targets"] == 0 and not [p for p in opened if "Scanresult" in p]
    assert _cache(cfg)["eta"]["sec_fill"][0][0] == len(rows)


def test_fill_gaps_leaves_value_empty_when_folder_was_rewritten_later(tmp_path, fake_nas):
    """ScanLog 의 시작이 장의 INI 시각 밖 = 같은 자리에 나중 검사가 덮어씀 — 값을 쓰지 않고, 해 본 Report 로 표시해 다시 열지 않는다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    collect.collect(cfg)
    for w in _wafer_dirs(nas):
        (w / "ScanLog.ini").write_text(SCANLOG.replace("9/13/2026", "9/20/2026"), encoding="utf-8")
    st = collect.fill_gaps(cfg)
    assert st["sec"]["filled"] == 0 and st["sec"]["empty"] == st["sec"]["targets"] > 0 and "params" not in st
    assert all(not r.get("scan_sec") for r in _sec_rows(cfg))
    assert collect.plan_run(cfg).sec_missing == 0                            # 대상에서 빠진다(sec_checked) — 지어내지도, 계속 다시 열지도 않는다
    assert all(e.get("sec_checked") for e in _cache(cfg)["reports"].values() if any(r.get("ini_match") == "EXACT" for r in e["rows"]))


@pytest.mark.parametrize("chunk", [1, 2000])
def test_fill_gaps_stop_keeps_what_was_read(tmp_path, fake_nas, monkeypatch, chunk):
    """멈추면 이미 읽은 장은 남는다 — 저장 단위(SEC_FILL_CHUNK)보다 작은 실행도(PR #3 리뷰: 덩어리째 버리던 것)."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, read_workers=1, collect_params=False)
    collect.collect(cfg)
    for w in _wafer_dirs(nas):
        (w / "ScanLog.ini").write_text(SCANLOG, encoding="utf-8")
    total = collect.plan_run(cfg).sec_missing
    assert total >= 2
    monkeypatch.setattr(collect, "SEC_FILL_CHUNK", chunk)
    seen = []
    st = collect.fill_gaps(cfg, progress=lambda d, t, p: seen.append(p) if "스캔" in p else None, should_stop=lambda: len(seen) >= 1)
    assert st["stopped"] == 1
    left = collect.plan_run(cfg).sec_missing
    assert 0 < left < total
    assert collect.fill_gaps(cfg)["sec"]["targets"] == left and collect.plan_run(cfg).sec_missing == 0
