"""prefs.json 로드/저장/패치 계약."""
from __future__ import annotations

import json

from aoi_capacity import collect
from aoi_capacity.utils import paths, prefs


def test_defaults_when_missing():
    p = prefs.load()
    assert p.backfill_days == 30
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
    prefs.patch(backfill_days=55, window_maximized=True)
    p = prefs.load()
    assert p.backfill_days == 55 and p.window_maximized is True
    try:
        prefs.patch(nope=1)
    except AttributeError:
        pass
    else:
        raise AssertionError("모르는 필드는 거부해야 한다")


def test_corrupt_file_falls_back_to_defaults():
    paths.prefs_file().write_text("{not json", encoding="utf-8")
    assert prefs.load().backfill_days == 30


def test_to_collect_cfg_fills_every_default_key(tmp_path):
    cfg = prefs.to_collect_cfg(prefs.Prefs(output_dir=str(tmp_path / "o")))
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


def test_options_removed_on_10_30_are_fixed_and_old_saved_values_are_ignored():
    """10/30 사용자 요청: 주의 장비 기준 · CSV 함께 저장 · 이력 보관 기간 · NAS 동시 읽기 · 어두운 화면 옵션을 없앴다.
    옛 prefs.json 에 값이 남아 있어도 깨지지 않고 무시되며, 고정값이 cfg 로 간다(다음 저장 때 파일에서도 사라진다)."""
    paths.prefs_file().write_text(json.dumps({
        "prefs_version": 8, "backfill_days": 7, "read_workers": 16, "retention_days": 45, "write_csv": False,
        "threshold_util": 55, "threshold_err": 9, "color_mode": "dark"}), encoding="utf-8")
    p = prefs.load()
    assert p.backfill_days == 7 and p.prefs_version == prefs.PREFS_VERSION
    for gone in ("read_workers", "retention_days", "write_csv", "threshold_util", "threshold_err", "color_mode"):
        assert not hasattr(p, gone), gone
    cfg = prefs.to_collect_cfg(p)
    assert cfg["read_workers"] == 4 and cfg["retention_days"] == 0 and cfg["write_csv"] is True
    assert (cfg["attention_util"], cfg["attention_err"]) == (40, 3)
    prefs.save(p)
    saved = json.loads(paths.prefs_file().read_text(encoding="utf-8"))
    assert not {"read_workers", "retention_days", "write_csv", "threshold_util", "threshold_err", "color_mode"} & set(saved)


def test_v9_does_not_expand_an_explicit_scope_saved_at_v8():
    """v9(설정 옵션 삭제)는 수집 범위와 무관 — v8 에서 고른 범위가 옛 기본값과 같아도 넓히지 않는다. v7 이하는 예전처럼 옮긴다."""
    kept = prefs.migrate(prefs.Prefs.from_dict({"scope_devices": ["AOI-25"], "prefs_version": 8}))
    assert kept.scope_devices == ["AOI-25"] and kept.prefs_version == prefs.PREFS_VERSION
    moved = prefs.migrate(prefs.Prefs.from_dict({"scope_devices": ["AOI-25"], "prefs_version": 7}))
    assert moved.scope_devices != ["AOI-25"]


def test_v11_moves_only_the_ip_share_default_publish_folders_back_to_conder_scan():
    """v11(10/30) — 배포 폴더 기본값이 다시 Conder Scan 이다. 한나절 기본값(IP 공유) 그대로인 것만 되돌리고 직접 고른 경로 · 빈 값(배포 끔)은 보존한다."""
    from aoi_capacity import i18n
    K = i18n.KO
    old = prefs.migrate(prefs.Prefs.from_dict({"prefs_version": 10, "publish_dir": K.PUBLISH_DIR_PAST + "\\", "publish_full_dir": K.PUBLISH_FULL_DIR_PAST}))
    assert (old.publish_dir, old.publish_full_dir) == (K.PUBLISH_DIR_DEFAULT, K.PUBLISH_FULL_DIR_DEFAULT)
    assert K.PUBLISH_DIR_DEFAULT.startswith("\\\\k5cifsn2\\") and "10.142.80.167" not in K.PUBLISH_FULL_DIR_DEFAULT
    mine = prefs.migrate(prefs.Prefs.from_dict({"prefs_version": 10, "publish_dir": "D:\\내 폴더", "publish_full_dir": ""}))
    assert (mine.publish_dir, mine.publish_full_dir) == ("D:\\내 폴더", "")
    new = prefs.migrate(prefs.Prefs.from_dict({"prefs_version": 11, "publish_dir": K.PUBLISH_DIR_PAST}))
    assert new.publish_dir == K.PUBLISH_DIR_PAST                 # 이미 v11 인 설정은 다시 옮기지 않는다(사용자가 일부러 IP 공유로 돌린 경우)
