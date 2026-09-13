"""경로 해석 — 데이터 폴더 우선순위, 첫 실행 복사, 설치 루트 판정."""
from __future__ import annotations

from pathlib import Path

from aoi_capacity.utils import paths


def test_data_root_priority(monkeypatch, tmp_path):
    paths._MADE_DIRS.clear()
    monkeypatch.setenv("AOI_DATA_HOME", str(tmp_path / "dh"))
    assert paths.data_root() == tmp_path / "dh"
    monkeypatch.delenv("AOI_DATA_HOME")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "la"))
    assert paths.data_root() == tmp_path / "la" / "AOI_Capacity"
    monkeypatch.delenv("LOCALAPPDATA")
    assert paths.data_root() == Path.home() / ".aoi_capacity"
    assert paths.data_root().is_dir()


def test_data_root_is_never_inside_app_tree():
    assert not str(paths.data_root()).startswith(str(paths._project_root()))


def test_ensure_user_files_copies_default_once():
    assert paths.ensure_user_files() is True
    assert paths.devices_csv_path().read_bytes() == paths.default_devices_csv().read_bytes()
    paths.devices_csv_path().write_text("mine", encoding="utf-8")
    assert paths.ensure_user_files() is False
    assert paths.devices_csv_path().read_text(encoding="utf-8") == "mine"       # 사용자 파일은 덮어쓰지 않는다


def test_install_root_env_and_layout_fallback(monkeypatch, tmp_path):
    assert paths.install_root() is None
    monkeypatch.setenv("AOI_APP_HOME", str(tmp_path))
    assert paths.install_root() == tmp_path
    monkeypatch.delenv("AOI_APP_HOME")
    root = paths._project_root().parent
    monkeypatch.setattr(paths, "_project_root", lambda: tmp_path / "app")
    (tmp_path / "app").mkdir()
    (tmp_path / "python").mkdir()
    (tmp_path / paths.EXE_NAME).write_bytes(b"x")
    assert paths.install_root() == tmp_path
    assert root  # 원래 값은 건드리지 않았다


def test_template_and_default_csv_exist():
    assert paths.template_path().is_file()
    assert "__DATA__" in paths.template_path().read_text(encoding="utf-8")
    assert paths.default_devices_csv().is_file()
