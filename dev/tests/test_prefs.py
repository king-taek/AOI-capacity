"""prefs.json 로드/저장/패치 계약."""
from __future__ import annotations

import json

from aoi_capacity import collect
from aoi_capacity.utils import paths, prefs


def test_defaults_when_missing():
    p = prefs.load()
    assert p.backfill_days == 30 and p.retention_days == 90 and p.color_mode == "light"   # 9/23: 결과 HTML 과 같은 라이트가 기본
    assert p.output_dir == "" and p.last_view == "collect"      # 수집 전용 — 자동 주기 수집 설정은 없다
    assert not hasattr(p, "auto_collect_minutes")


def test_unknown_keys_ignored_and_roundtrip():
    paths.prefs_file().write_text(json.dumps({"backfill_days": 7, "bogus": 1, "extra": {"x": 1}}), encoding="utf-8")
    p = prefs.load()
    assert p.backfill_days == 7 and p.extra == {"x": 1}
    prefs.save(p)
    assert prefs.load().backfill_days == 7
    assert not (paths.data_root() / "prefs.json.tmp").exists()


def test_patch_persists_and_rejects_unknown():
    prefs.patch(threshold_util=55, window_maximized=True)
    p = prefs.load()
    assert p.threshold_util == 55 and p.window_maximized is True
    try:
        prefs.patch(nope=1)
    except AttributeError:
        pass
    else:
        raise AssertionError("모르는 필드는 거부해야 한다")


def test_corrupt_file_falls_back_to_defaults():
    paths.prefs_file().write_text("{not json", encoding="utf-8")
    assert prefs.load().retention_days == 90


def test_to_collect_cfg_fills_every_default_key(tmp_path):
    cfg = prefs.to_collect_cfg(prefs.Prefs(output_dir=str(tmp_path / "o"), write_csv=True))
    assert set(collect.DEFAULT_CONFIG) <= set(cfg)
    assert cfg["devices_csv"] == str(paths.devices_csv_path())
    assert cfg["output_dir"] == str(tmp_path / "o") and cfg["write_csv"] is True
    assert cfg["cache_file"] == str(paths.cache_file())


def test_refresh_window_days_is_off_by_default_and_flows_into_cfg():
    """D60: 수집 페이지 체크박스 → prefs.refresh_window_days → cfg["refresh_window_days"]. rebuild_all 은 설정에 남기지 않는다."""
    p = prefs.load()
    assert p.refresh_window_days == 0
    cfg = prefs.to_collect_cfg(p)
    assert cfg["refresh_window_days"] == 0 and cfg["rebuild_all"] is False
    prefs.patch(refresh_window_days=30)
    assert prefs.to_collect_cfg(prefs.load())["refresh_window_days"] == 30
    assert prefs.to_collect_cfg(prefs.Prefs(refresh_window_days=-5))["refresh_window_days"] == 0
    assert set(collect.DEFAULT_CONFIG) <= set(prefs.to_collect_cfg(prefs.load()))


def test_v4_moves_only_the_old_dark_default_to_light():
    """9/23: 기본 화면이 밝은 화면으로 바뀌었다 — v3 이하의 "dark"(옛 기본값)만 옮기고, v4 뒤에 고른 어두운 화면은 남긴다."""
    old = prefs.migrate(prefs.Prefs.from_dict({"color_mode": "dark", "prefs_version": 3}))
    assert old.color_mode == "light" and old.prefs_version == prefs.PREFS_VERSION
    chosen = prefs.migrate(prefs.Prefs.from_dict({"color_mode": "dark", "prefs_version": 4}))
    assert chosen.color_mode == "dark"
