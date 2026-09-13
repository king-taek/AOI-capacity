"""테스트 공통 픽스처.

- 모든 테스트는 임시 HOME/LOCALAPPDATA 아래에서 돈다 → 개발자의 실제 설정·캐시를 건드리지 않는다.
  (`ntpath.expanduser` 는 HOME 이 아니라 USERPROFILE 을 보므로 둘 다 바꾼다.)
- 환경변수 AOI_DATA_HOME / AOI_APP_HOME 은 지운다(테스트가 명시적으로 넣을 때만).
- Qt 가 필요한 테스트는 `qapp` 픽스처를 쓰며 conftest 가 `ui` 마커를 자동으로 붙인다.
  PyQt6 가 없는 환경에서는 그 테스트만 skip 된다.
- MainWindow 의 시작 부수효과(업데이트 확인 스레드)는 클래스 수준에서 막는다 — 테스트가
  네트워크를 타거나 시트 팝업의 중첩 이벤트 루프에 갇히는 사고 방지.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AOI_NO_WEBENGINE", "1")

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def set_home(monkeypatch, path: Path) -> None:
    monkeypatch.setenv("HOME", str(path))
    monkeypatch.setenv("USERPROFILE", str(path))
    monkeypatch.setenv("LOCALAPPDATA", str(path / "AppData" / "Local"))


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    """모든 테스트를 임시 홈에서 돌린다. 반환값은 그 홈 경로."""
    home = tmp_path / "home"
    home.mkdir()
    set_home(monkeypatch, home)
    monkeypatch.delenv("AOI_DATA_HOME", raising=False)
    monkeypatch.delenv("AOI_APP_HOME", raising=False)
    try:
        from aoi_capacity.utils import paths, prefs
        paths._MADE_DIRS.clear()
        prefs._cached = None
    except Exception:  # noqa: BLE001 - 아직 모듈이 없을 수 있다(M0 단계)
        pass
    return home


@pytest.fixture(autouse=True)
def _no_startup_side_effects(monkeypatch):
    try:
        from aoi_capacity.ui import main_window as mw
    except Exception:  # noqa: BLE001
        return

    def _suppressed(self, *_a, **_k):
        calls = getattr(self, "_suppressed_startup_calls", [])
        calls.append("_check_for_update_async")
        self._suppressed_startup_calls = calls

    monkeypatch.setattr(mw.MainWindow, "_check_for_update_async", _suppressed)


@pytest.fixture(scope="session")
def _qt_app():
    pytest.importorskip("PyQt6.QtWidgets")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture
def qapp(_qt_app):
    return _qt_app


@pytest.fixture
def styled_qapp(_qt_app):
    from aoi_capacity.ui import theme
    theme.apply_to_app(_qt_app)
    return _qt_app


def pytest_collection_modifyitems(config, items):
    for item in items:
        if {"qapp", "styled_qapp"} & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.ui)
