"""prefs.json 로드/저장/패치 계약."""
from __future__ import annotations

import json

from aoi_capacity import collect
from aoi_capacity.utils import paths, prefs


def test_defaults_when_missing():
    p = prefs.load()
    assert p.backfill_days == 30 and p.retention_days == 90 and p.color_mode == "dark"
    assert p.output_dir == "" and p.auto_collect_minutes == 0


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
