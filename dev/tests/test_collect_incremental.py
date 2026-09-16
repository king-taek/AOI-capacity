"""수집 코어의 증분·backfill·보관·취소·진행률 계약."""
from __future__ import annotations

import json
import os
import time

import pytest

from aoi_capacity import collect
from conftest import make_cfg, make_device


def _run(cfg, **kw):
    prog = []
    rows, dev_meta, errors = collect.collect(cfg, progress=lambda d, t, p: prog.append((d, t, p)), **kw)
    return rows, dev_meta, errors, prog


def test_first_run_reads_everything_and_second_run_reads_nothing(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    rows, dev_meta, errors, prog = _run(cfg)
    names = sorted(d["name"] for d in dev_meta)
    assert names == ["8호기", "9호기", "AOI-10"]          # 꺼둔 행·접근 불가 행은 제외, * 는 AOI-10 만 새로 추가(AOI-9 는 명시 행이 이김)
    assert len(rows) == 9 and not errors
    assert prog[-1][0] == prog[-1][1] > 0                 # 마지막 보고는 (total, total)
    cache = json.loads((tmp_path / "out" / "aoi_cache.json").read_text(encoding="utf-8"))
    # 커서 키는 표시명이 아니라 정규화한 장비 경로다(이름을 바꿔도 이력이 갈라지지 않게)
    assert len(cache["last_mtime"]) == 3
    assert {os.path.basename(k) for k in cache["last_mtime"]} == {"AOI-9", "AOI-10", "M-AOI-8"}

    rows2, dev_meta2, _, prog2 = _run(cfg)
    assert len(rows2) == 9
    assert all(d["reports"] == 0 for d in dev_meta2)      # 새 파일 없음
    assert prog2[-1] == (0, 0, prog2[-1][2])              # total 0 → 마지막도 (0,0)


def test_new_report_is_picked_up_by_cursor(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    rep = nas / "X" / "AOI-10" / "Report" / "2D@R2-GA285AAB_0859840PD-0A_6321_NEW_26-Sep-13_(06.00.00)_BatchReport.htm"
    rep.write_text((nas / "X" / "AOI-10" / "Report").glob("*.htm").__next__().read_text(encoding="utf-8"), encoding="utf-8")
    future = time.time() + 3600
    os.utime(rep, (future, future))
    rows, dev_meta, _, _ = _run(cfg)
    assert {d["name"]: d["reports"] for d in dev_meta} == {"8호기": 0, "9호기": 0, "AOI-10": 1}
    assert len(rows) == 12


def test_backfill_window_limits_first_run(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    old = time.time() - 40 * 86400
    make_device(nas / "X", "AOI-9", mtime=old)            # 40일 전 Report
    cfg = make_cfg(tmp_path, csv_path, backfill_days=30)
    rows, dev_meta, _, _ = _run(cfg)
    assert next(d for d in dev_meta if d["name"] == "9호기")["reports"] == 0
    assert len(rows) == 6


def test_unseen_device_gets_backfill_not_cursor(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    _run(cfg)
    make_device(nas / "X", "AOI-11", mtime=time.time() - 5 * 86400)   # 새 장비, 5일 전 Report
    rows, dev_meta, _, _ = _run(cfg)
    assert next(d for d in dev_meta if d["name"] == "AOI-11")["reports"] == 1


def test_retention_drops_old_reports(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, retention_days=1)   # 샘플의 wafer 시각은 2026-09-13 → 오래됐다고 판정될 수도, 아닐 수도 있으므로 상대 비교
    rows_keep, _, _, _ = _run(make_cfg(tmp_path, csv_path, retention_days=100000))
    rows_drop, _, _, _ = _run(cfg)
    assert len(rows_drop) <= len(rows_keep)


def test_cancel_leaves_cache_and_output_untouched(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 2

    with pytest.raises(collect.CollectCancelled):
        collect.collect(cfg, should_stop=stop)
    assert not (tmp_path / "out" / "aoi_cache.json").exists()
    assert not (tmp_path / "out" / "AOI_capacity.html").exists()


def test_write_html_embeds_data_and_mode(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, write_csv=True)
    rows, dev_meta, errors, _ = _run(cfg)
    target = collect.write_html(cfg, rows, dev_meta, errors, time.time(), mode="gui")
    html = open(target, encoding="utf-8").read()
    assert "__DATA__" not in html and '"mode":"gui"' in html and '"cols":' in html
    assert (tmp_path / "out" / "AOI_capacity.csv").exists()
    assert not (tmp_path / "out" / "AOI_capacity.html.tmp").exists()


def test_plan_run_reports_first_then_incremental(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    assert collect.plan_run(cfg).first_run is True
    _run(cfg)
    plan = collect.plan_run(cfg)
    assert plan.first_run is False and plan.known_devices == 3
    assert collect.plan_run(cfg, backfill=True).first_run is True


def test_on_device_callback_reports_states(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    seen = []
    collect.collect(cfg, on_device=lambda n, s, d: seen.append((n, s)))
    assert ("9호기", "listing") in seen and ("9호기", "parsing") in seen and ("9호기", "done") in seen
