"""수집 가속(9/23) — ① 증분 수집의 Report 목록을 이름의 날짜 패턴으로 NAS 가 거르게 ② 읽기를 NAS 마다 번갈아 배정.

`PATTERN_LISTER`(Windows `FindFirstFileExW`)는 개발·CI(Linux)에 없으므로 여기서는 같은 계약의 가짜(fnmatch)로 바꿔 끼운다.
고르는 규칙은 전체 나열과 같아야 한다 — 받은 목록이 부분집합일 뿐 결과가 달라지면 안 된다."""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import threading
import time

import pytest

from aoi_capacity import collect
from conftest import REPORT_HTML, make_cfg


# ── ② NAS 별 동시 읽기 ───────────────────────────────────────────────────
def test_run_spreads_work_across_nas_groups_and_keeps_input_order():
    """한 NAS 에 몰리지 않는다: NAS 마다 read_workers 개까지, 여러 NAS 는 동시에. 결과는 입력 순서 그대로."""
    tasks = [(g, i) for i in range(8) for g in "AAB"] + [("C", i) for i in range(6)]
    lock, now, peak = threading.Lock(), {}, {"all": 0}
    busy = {"all": 0}

    def fn(t):
        g = t[0]
        with lock:
            now[g] = now.get(g, 0) + 1
            busy["all"] += 1
            peak[g] = max(peak.get(g, 0), now[g])
            peak["all"] = max(peak["all"], busy["all"])
        time.sleep(0.01)
        with lock:
            now[g] -= 1
            busy["all"] -= 1
        return t

    out = collect._run({"read_workers": 2}, tasks, fn, None, group=lambda t: t[0])
    assert out == tasks
    assert peak["A"] <= 2 and peak["B"] <= 2 and peak["C"] <= 2
    assert peak["all"] > 2                                # 셋이 함께 돌았다(예전엔 전체 2개)


def test_run_raises_the_earliest_error_and_stops_taking_new_work():
    seen = []

    def fn(t):
        seen.append(t)
        if t in (3, 5):
            raise collect.CollectCancelled() if t == 3 else ValueError(t)
        return t

    with pytest.raises(collect.CollectCancelled):
        collect._run({"read_workers": 1}, list(range(10)), fn, None, group=lambda t: t % 2)
    with pytest.raises((collect.CollectCancelled, ValueError)):
        collect._run({"read_workers": 4}, list(range(40)), fn, None, group=lambda t: t % 2)


def test_nas_group_reads_only_the_path_text():
    assert collect.nas_group(r"\\10.1.2.3\AOI\AOI-8") == collect.nas_group(r"\\10.1.2.3\other\AOI-9") == "10.1.2.3"
    assert collect.nas_group(r"\\nas-b\AOI\AOI-8") != collect.nas_group(r"\\10.1.2.3\AOI\AOI-8")
    if os.name != "nt":                                   # 연결 정보가 없으면 드라이브 문자 그대로
        assert collect.nas_group(r"x:\AOI-1") == collect.nas_group(r"X:\AOI-7") == "X:"
        assert collect.nas_group(r"V:\AOI-10") == "V:"
    assert collect.nas_group("/tmp/nas/X/AOI-9") == ""


# ── ① 이름의 날짜 패턴 ────────────────────────────────────────────────────
def _ts(y, m, d, hh=12):
    return dt.datetime(y, m, d, hh).timestamp()


def test_patterns_cover_the_day_before_the_cursor_through_tomorrow_in_english():
    pats = collect.report_name_patterns(_ts(2026, 12, 31), _ts(2027, 1, 1))
    assert pats == ["*_26-Dec-30_(*", "*_26-Dec-31_(*", "*_27-Jan-01_(*", "*_27-Jan-02_(*"]
    name = "2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_27-Jan-01_(05.32.23)_BatchReport.htm"
    assert any(fnmatch.fnmatch(name, p) for p in pats)
    assert collect.report_name_patterns(_ts(2026, 9, 1), _ts(2026, 9, 30)) is None     # 너무 오래 쉬면 전체 나열


def _fake_lister(calls):
    def lister(folder, pattern):
        calls.append(pattern)
        return [e for e in os.scandir(folder) if fnmatch.fnmatch(e.name, pattern)]
    return lister


def _name_for(day: dt.date, tag: str) -> str:
    mon = collect._MONTHS[day.month - 1]
    return f"2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_{day.year % 100:02d}-{mon}-{day.day:02d}_({tag})_BatchReport.htm"


def _add(nas, name, mtime):
    rep = nas / "X" / "AOI-9" / "Report" / name
    rep.write_text(REPORT_HTML, encoding="utf-8")
    os.utime(rep, (mtime, mtime))
    return rep


def _cache(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def _reports(cfg):
    """캐시에 든 Report 이름(원래 철자) — 키의 상대 경로는 소문자로 접혀 있어 path 에서 이름을 꺼낸다."""
    return sorted(os.path.basename(v["path"]) for v in _cache(cfg)["reports"].values())


def test_incremental_run_lists_by_name_pattern_and_picks_the_same_files(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    calls: list = []
    monkeypatch.setattr(collect, "PATTERN_LISTER", _fake_lister(calls))
    cfg = make_cfg(tmp_path / "p", csv_path)
    st: dict = {}
    collect.collect(cfg, stats=st)
    assert calls == [] and st["list_pattern"] == 0                          # 첫 수집은 전체 나열
    assert set(_cache(cfg)["full_listed"]) == set(_cache(cfg)["last_mtime"])   # 장비마다 전체 나열 시각
    today = dt.date.today()
    _add(nas, _name_for(today, "10.00.00"), time.time() + 5)
    st = {}
    collect.collect(cfg, stats=st)
    assert st["list_pattern"] >= 1 and f"*_{today.year % 100:02d}-{collect._MONTHS[today.month - 1]}-{today.day:02d}_(*" in calls
    assert _name_for(today, "10.00.00") in _reports(cfg)
    # 같은 NAS 를 전체 나열로만 읽은 결과와 같다
    monkeypatch.setattr(collect, "PATTERN_LISTER", None)
    ref = make_cfg(tmp_path / "f", csv_path)
    collect.collect(ref)
    assert _reports(ref) == _reports(cfg)
    # 아무것도 안 바뀐 패턴 실행은 캐시를 건드리지 않는다(C04)
    monkeypatch.setattr(collect, "PATTERN_LISTER", _fake_lister(calls))
    st = {}
    collect.collect(cfg, stats=st)
    assert st["list_pattern"] >= 1 and st["cache_saved"] is False


def test_name_outside_the_rule_is_caught_by_the_periodic_full_listing(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    monkeypatch.setattr(collect, "PATTERN_LISTER", _fake_lister([]))
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    _add(nas, "EXPORT.htm", time.time() + 5)
    collect.collect(cfg)
    assert "EXPORT.htm" not in _reports(cfg)                                # 패턴 나열에는 안 보인다
    monkeypatch.setattr(collect, "FULL_LIST_EVERY_SEC", 0)                 # 전체 나열할 때가 됐다
    st: dict = {}
    collect.collect(cfg, stats=st)
    assert st["list_pattern"] == 0 and "EXPORT.htm" in _reports(cfg)


def test_pattern_listing_failure_falls_back_to_the_full_listing(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    monkeypatch.setattr(collect, "PATTERN_LISTER", _fake_lister([]))
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)

    def broken(folder, pattern):
        raise OSError("패턴 거부")

    monkeypatch.setattr(collect, "PATTERN_LISTER", broken)
    name = _name_for(dt.date.today(), "11.00.00")
    _add(nas, name, time.time() + 5)
    st: dict = {}
    collect.collect(cfg, stats=st)
    assert st["list_pattern"] == 0 and name in _reports(cfg)


def test_backfill_and_refresh_always_list_everything(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    calls: list = []
    monkeypatch.setattr(collect, "PATTERN_LISTER", _fake_lister(calls))
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(cfg)
    collect.collect(cfg, backfill=True)
    collect.collect(cfg, refresh_window_days=3)
    collect.collect(cfg, recover=True)
    assert calls == []
