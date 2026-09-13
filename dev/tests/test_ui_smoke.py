"""MainWindow 스모크 — 오프스크린. WebEngine 없이(AOI_NO_WEBENGINE=1) 내비 전환·수집 흐름·시작 부수효과 억제."""
from __future__ import annotations

import time

import pytest

from conftest import make_cfg  # noqa: F401 - fake_nas 가 필요

pytest.importorskip("PyQt6.QtWidgets")


def _pump(app, secs=0.05):
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        time.sleep(0.005)


@pytest.fixture
def window(styled_qapp, fake_nas):
    from aoi_capacity import devices
    from aoi_capacity.utils import paths

    nas, csv_path = fake_nas
    rows = devices.read_devices_csv(csv_path)
    devices.write_devices_csv(paths.devices_csv_path(), rows)
    from aoi_capacity.ui.main_window import MainWindow

    w = MainWindow()
    w.show()
    _pump(styled_qapp)
    yield w
    w.close()
    _pump(styled_qapp)


def test_startup_update_check_is_suppressed_in_tests(window, styled_qapp):
    _pump(styled_qapp, 0.6)
    assert window._suppressed_startup_calls == ["_check_for_update_async"]


def test_nav_switches_pages_and_remembers_last_view(window, styled_qapp):
    from aoi_capacity.utils import prefs

    for key, page in (("devices", window.devices_page), ("collect", window.collect_page),
                      ("settings", window.settings_page), ("trend", window.dashboard), ("home", window.dashboard)):
        window.nav.set_current(key)
        _pump(styled_qapp)
        assert window.stack.currentWidget() is page
        assert prefs.load().last_view == key
    assert window.dashboard._view == "home"


def test_collect_flow_writes_html_and_updates_status(window, styled_qapp):
    from aoi_capacity import i18n
    from aoi_capacity.utils import paths

    window.nav.set_current("collect")
    window._start_collect(False, False)
    assert window.is_collecting() and window.overlay.isVisible()
    t0 = time.time()
    while window.is_collecting() and time.time() - t0 < 20:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.2)
    assert not window.is_collecting()
    assert not window.overlay.isVisible()
    assert paths.output_html("").exists()
    assert window.nav._status.text().startswith(i18n.KO.NAV_LAST_COLLECT_FMT.split("{")[0])
    assert "수집 완료" in window.collect_page._status.text()
    assert window.collect_page._b_run.isEnabled()


def test_collect_refuses_without_devices(window, styled_qapp, monkeypatch):
    from aoi_capacity.ui import main_window as mw
    from aoi_capacity.utils import paths

    paths.devices_csv_path().write_text("name,root,sub,on,memo\n", encoding="utf-8-sig")
    warned = []
    monkeypatch.setattr(mw.sheets, "warn", lambda *a: warned.append(a))
    window._start_collect(False, False)
    assert warned and not window.is_collecting()


def test_stale_token_signals_are_ignored(window, styled_qapp):
    from aoi_capacity.workers.collector import CollectResult

    window.overlay.show_overlay()
    window._on_collect_done(window._collect_token + 99, CollectResult(rows=1, devices=1))
    assert window.overlay.isVisible()          # 옛 토큰은 화면을 바꾸지 못한다
    window.overlay.hide_overlay()


def test_build_url_query(tmp_path):
    from aoi_capacity.ui.pages.dashboard_page import build_url
    from aoi_capacity.utils import prefs

    html = tmp_path / "AOI_capacity.html"
    html.write_text("x", encoding="utf-8")
    p = prefs.Prefs(color_mode="light", threshold_util=55, threshold_err=9)
    q = build_url(html, "compare", p).query()
    assert "gui=1" in q and "theme=light" in q and "view=compare" in q and "th_util=55" in q and "th_err=9" in q
    assert "view=home" in build_url(html, "bogus", p).query()


def test_theme_switch_reapplies_stylesheet(window, styled_qapp):
    from aoi_capacity.ui import theme

    window.settings_page._dark.setChecked(False)
    _pump(styled_qapp)
    assert theme.color_mode() == "light"
    assert styled_qapp.styleSheet() == theme.render_qss("light")
    window.settings_page._dark.setChecked(True)
    _pump(styled_qapp)
    assert theme.color_mode() == "dark"
