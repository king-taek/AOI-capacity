"""평소 수집 끝의 빈칸 채우기(11/25, `collect.fill_gaps_budget_into` · cfg `gap_fill_sec`) — 현택: "옛 기간 빈칸 채우기 → 평소 수집 때 왜 자동으로 안 되나".

- 수집이 끝날 때(전체 다시 만들기 · RDL 패치 제외) 남은 옛 빈칸을 **최근 것부터** 정해진 초만큼만, 메모리의 캐시에 넣고 수집 끝의 저장 한 번에 담는다.
- 읽는 곳은 '옛 기간 빈칸 채우기' 와 같다 — Wafer 폴더 안 정확 경로만(Report 다시 읽기 0), 범위 게이트를 지난 장비만.
- 시간이 다 되면 멈추고 다음 수집이 이어 간다, 사용자의 중지는 수집의 중지(`CollectCancelled`).
- 새로 읽은 Report 는 이미 해 봤다는 표시(`FRESH_CHECKED`)가 붙어 다시 열지 않는다."""
from __future__ import annotations

import json

import pytest

from aoi_capacity import collect, nas_guard
from conftest import as_old_cache, make_cfg


def _cache(cfg):
    return json.loads(open(cfg["cache_file"], encoding="utf-8").read())


def _exact(cfg):
    return [r for e in _cache(cfg)["reports"].values() for r in e["rows"] if r.get("ini_match") == "EXACT" and not r.get("kind")]


def _add_slot(nas, slot="07"):
    for ini in nas.rglob("WaferInfo.ini"):
        ini.write_text(ini.read_text(encoding="utf-8").replace("Operator=MAINT\n", f"Operator=MAINT\nActiveSlot={slot}\n"), encoding="utf-8")


def test_fresh_reads_are_marked_checked_so_nothing_is_reopened(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    stats: dict = {}
    collect.collect(cfg, stats=stats)
    assert all(all(e.get(f) for f in collect.FRESH_CHECKED) for e in _cache(cfg)["reports"].values())
    assert stats["gaps"]["targets"] == 0                               # 새로 읽은 것은 이미 해 봤다
    plan = collect.plan_run(cfg)
    assert plan.slot_missing == 0 and plan.sec_missing == 0             # 카드도 '채울 수 있는 빈칸' 만 센다


def test_normal_collect_fills_old_gaps_at_the_end_without_rereading_reports(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    collect.collect(cfg)
    as_old_cache(cfg)                                                   # 업데이트 전에 읽은 캐시 — 슬롯 번호가 비어 있다
    _add_slot(nas)
    assert collect.plan_run(cfg).slot_missing == len(_exact(cfg)) > 0
    opened = []
    real = nas_guard.read_bytes
    monkeypatch.setattr(nas_guard, "read_bytes", lambda p, *a, **k: opened.append(str(p)) or real(p, *a, **k))
    saves = []
    real_save = collect._save_cache
    monkeypatch.setattr(collect, "_save_cache", lambda *a, **k: saves.append(1) or real_save(*a, **k))
    stats: dict = {}
    collect.collect(cfg, stats=stats)
    assert stats["gaps"]["slot"] == len(_exact(cfg)) and not stats["gaps"]["left"] and not stats["gaps"]["timed_out"]
    assert all(r["slot_no"] == "7" for r in _exact(cfg))
    assert not any(p.lower().endswith((".htm", ".html")) for p in opened)    # Report 는 다시 읽지 않는다
    assert len(saves) == 1 and stats["cache_saved"]                     # 저장은 수집 끝의 한 번
    assert collect.plan_run(cfg).slot_missing == 0


def test_gap_fill_off_and_rebuild_do_not_touch_gaps(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    collect.collect(cfg)
    as_old_cache(cfg)
    _add_slot(nas)
    stats: dict = {}
    collect.collect(dict(cfg, gap_fill_sec=0), stats=stats)
    assert stats["gaps"]["targets"] == 0 and all(not r["slot_no"] for r in _exact(cfg))


def test_budget_runs_out_then_the_next_collect_continues(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False, read_workers=1)
    collect.collect(cfg)
    as_old_cache(cfg)
    _add_slot(nas)
    cache = _cache(cfg)
    devs = collect.devices_mod.resolve_devices(cfg, None)
    collect._assign_device_keys(cache, devs, cfg, collect._Dirty(), None)
    st = collect.fill_gaps_budget_into(cfg, cache, devs, 1e-9, None, lambda d, t, p: None, None)
    assert st["timed_out"] == 1 and st["left"] == st["targets"] > 0      # 시간이 없으면 그 자리에서 멈춘다 — 해 보지 않은 Report 에는 표시가 없다
    assert not any(e.get("slot_checked") for e in cache["reports"].values())
    st2 = collect.fill_gaps_budget_into(cfg, cache, devs, 60, None, lambda d, t, p: None, None)
    assert st2["slot"] == st["targets"] and st2["left"] == 0


def test_user_stop_is_the_collect_stop(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False, read_workers=1)
    collect.collect(cfg)
    as_old_cache(cfg)
    _add_slot(nas)
    cache = _cache(cfg)
    devs = collect.devices_mod.resolve_devices(cfg, None)
    collect._assign_device_keys(cache, devs, cfg, collect._Dirty(), None)
    with pytest.raises(collect.CollectCancelled):
        collect.fill_gaps_budget_into(cfg, cache, devs, 60, None, lambda d, t, p: None, lambda: True)


def test_newest_wafers_go_first(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False, read_workers=1)
    collect.collect(cfg)
    as_old_cache(cfg)
    cache = _cache(cfg)
    order = {"AOI-9": "15-Sep-26 05:31:04 PM", "AOI-10": "14-Sep-26 05:31:04 PM"}    # 9 가 가장 최근, 8 은 그대로(13일)
    for e in cache["reports"].values():
        for r in e["rows"]:
            for dev, t in order.items():
                if r.get("ini_match") == "EXACT" and f"{dev}" in str(e.get("path")):
                    r["wafer_start_time"] = t
    devs = collect.devices_mod.resolve_devices(cfg, None)
    collect._assign_device_keys(cache, devs, cfg, collect._Dirty(), None)
    seen = []
    real = collect.read_ini
    monkeypatch.setattr(collect, "read_ini", lambda p: seen.append(str(p)) or real(p))
    collect.fill_gaps_budget_into(cfg, cache, devs, 60, None, lambda d, t, p: None, None)
    devs_in_order = [next((k for k in ("AOI-9", "AOI-10", "M-AOI-8") if k in p), "?") for p in seen]
    assert devs_in_order[0] == "AOI-9" and devs_in_order[-1] == "M-AOI-8"
