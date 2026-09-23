"""MainWindow 스모크 — 오프스크린. 수집 전용 창(수집 · 장비 목록 · 설정)의 내비 전환·수집 흐름·결과 파일 안내."""
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
    from aoi_capacity.utils import paths, prefs

    nas, csv_path = fake_nas
    rows = devices.read_devices_csv(csv_path)
    devices.write_devices_csv(paths.devices_csv_path(), rows)
    # 가짜 NAS 장비는 AOI-25 가 아니다 — 창 동작 자체를 보는 테스트라 범위 제한을 푼다.
    # 기본값(AOI-25)에서 범위 밖 장비만 있을 때의 동작은 test_collect_refuses_out_of_scope_devices 가 본다.
    prefs.patch(scope_devices=["*"])
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

    for key, page in (("devices", window.devices_page), ("settings", window.settings_page),
                      ("collect", window.collect_page)):
        window.nav.set_current(key)
        _pump(styled_qapp)
        assert window.stack.currentWidget() is page
        assert prefs.load().last_view == key


def test_no_embedded_dashboard_viewer(window):
    """★ 결과 화면은 앱 안에 없다 — 생성된 HTML 파일을 사용자가 직접 연다."""
    assert not hasattr(window, "dashboard")
    assert set(window._pages) == {"collect", "devices", "settings"}
    assert [k for k in window.nav.keys()] == ["collect", "devices", "settings"]


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
    # 결과 카드가 방금 만든 HTML 경로를 가리키고 '결과 화면 열기' 가 살아난다
    assert window.collect_page._result.text() == str(paths.output_html(""))
    assert window.collect_page._b_open.isEnabled()


def test_collect_refuses_out_of_scope_devices(window, styled_qapp, monkeypatch):
    """★ 수집 범위 밖 장비뿐이면 조용히 훑지 않고 안내하고 멈춘다(기본 범위 = AOI-25)."""
    from aoi_capacity.ui import main_window as mw
    from aoi_capacity.utils import prefs

    prefs.patch(scope_devices=["AOI-25"])
    warned = []
    monkeypatch.setattr(mw.sheets, "warn", lambda *a: warned.append(a))
    window._start_collect(False, False)
    assert warned and not window.is_collecting()


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


def test_result_card_before_any_collect(window, styled_qapp):
    from aoi_capacity import i18n
    from aoi_capacity.utils import paths

    if paths.output_html("").exists():
        paths.output_html("").unlink()
    window.collect_page.refresh_result()
    _pump(styled_qapp)
    assert window.collect_page._result.text() == i18n.KO.COLLECT_RESULT_NONE
    assert not window.collect_page._b_open.isEnabled()


def test_ensure_html_creates_openable_file_without_collecting(tmp_path):
    from aoi_capacity.utils import results

    path = results.ensure_html()
    assert path.is_file() and "__DATA__" not in path.read_text(encoding="utf-8")


def test_theme_switch_reapplies_stylesheet(window, styled_qapp):
    from aoi_capacity.ui import theme

    window.settings_page._dark.setChecked(False)
    _pump(styled_qapp)
    assert theme.color_mode() == "light"
    assert styled_qapp.styleSheet() == theme.render_qss("light")
    window.settings_page._dark.setChecked(True)
    _pump(styled_qapp)
    assert theme.color_mode() == "dark"


def test_collect_range_is_editable_and_saved(window, styled_qapp):
    """새로 넣은 장비를 며칠치부터 읽을지 — 설정에서 바꿀 수 있어야 한다(30대 확대 후 필요)."""
    from aoi_capacity.utils import prefs

    window.settings_page._backfill.setValue(3)
    _pump(styled_qapp)
    assert prefs.load().backfill_days == 3
    assert prefs.to_collect_cfg(prefs.load())["backfill_days"] == 3
    window.settings_page._retention.setValue(120)
    _pump(styled_qapp)
    assert prefs.load().retention_days == 120


def test_read_concurrency_is_editable_and_saved(window, styled_qapp):
    """NAS 가 동시 읽기를 못 견디면 낮출 수 있어야 한다(1 = 예전처럼 한 줄로)."""
    from aoi_capacity.utils import prefs

    window.settings_page._workers.setValue(4)
    _pump(styled_qapp)
    assert prefs.load().read_workers == 4
    assert prefs.to_collect_cfg(prefs.load())["read_workers"] == 4


def test_split_size_is_editable_and_reaches_the_collect_cfg(window, styled_qapp):
    """결과 HTML 분할 기준(MB) — 설정에서 바꾸면 수집 cfg 의 split_mb 로 간다(0 = 나누지 않음)."""
    from aoi_capacity.utils import prefs

    window.settings_page._split.setValue(12)
    _pump(styled_qapp)
    assert prefs.load().split_mb == 12 and prefs.to_collect_cfg(prefs.load())["split_mb"] == 12


def test_mode_cards_pick_one_situation_and_map_to_worker_options(window, styled_qapp):
    """상황 카드: 하나만 고르고, 카드 → 워커 인자(full, backfill, recover) · '최근 며칠' 은 refresh_window_days 로.
    처음 수집(캐시 없음)이면 문제 해결 카드는 잠기고 평소 카드가 '처음 수집' 이 된다. 수집이 끝나면 평소 수집으로 돌아간다."""
    from aoi_capacity import i18n
    from aoi_capacity.utils import prefs

    page = window.collect_page
    page.wait_for_plan()
    _pump(styled_qapp, 0.2)
    assert page.mode() == "normal" and page.options() == (False, False, False)
    assert page._cards["normal"].title() == i18n.KO.MODE_FIRST_TITLE            # 아직 캐시가 없다
    assert not page._cards["rebuild"].available()
    page._pick("rebuild")
    assert page.mode() == "normal"                                              # 잠긴 카드는 고를 수 없다
    window._start_collect(False, False)
    t0 = time.time()
    while window.is_collecting() and time.time() - t0 < 20:
        _pump(styled_qapp)
    page.wait_for_plan()
    _pump(styled_qapp, 0.3)
    assert page._cards["rebuild"].available() and page._cards["normal"].title() == i18n.KO.MODE_NORMAL_TITLE
    for key, args in (("backfill", (False, True, False)), ("recover", (False, False, True)), ("rebuild", (True, False, False))):
        page._pick(key)
        assert page.options() == args and page._cards[key].property("selected") == "true"
        assert sum(c.property("selected") == "true" for c in page._cards.values()) == 1
        assert i18n.KO.MODE_RUN_FMT.format(title=page._cards[key].title()) == page._b_run.text()
    page._refresh_days.setValue(5)
    page._pick("refresh")
    assert prefs.load().refresh_window_days == 5 and page.options() == (False, False, False)
    page._pick("normal")
    assert prefs.load().refresh_window_days == 0
    page._pick("recover")
    page.set_running(True)
    page.set_running(False)
    assert page.mode() == "normal"
    page.wait_for_plan()
