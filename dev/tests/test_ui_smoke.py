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
def window(styled_qapp, fake_nas, monkeypatch):
    from aoi_capacity import devices
    from aoi_capacity.utils import paths, prefs

    nas, csv_path = fake_nas
    rows = devices.read_devices_csv(csv_path)
    devices.write_devices_csv(paths.devices_csv_path(), rows)
    # 가짜 NAS 장비는 AOI-25 가 아니다 — 창 동작 자체를 보는 테스트라 범위 제한을 푼다.
    # 기본값(AOI-25)에서 범위 밖 장비만 있을 때의 동작은 test_collect_refuses_out_of_scope_devices 가 본다.
    prefs.patch(scope_devices=["*"])
    from aoi_capacity.ui.main_window import MainWindow

    from aoi_capacity.ui import main_window

    # 가짜 NAS 에는 접근 못 하는 장비가 있다 — 수집 완료 안내(모달)가 뜨면 테스트가 멈추니 가로채서 내용만 본다
    warned = []
    monkeypatch.setattr(main_window.sheets, "warn", lambda _w, title, text: warned.append(text))
    w = MainWindow()
    w._warned = warned
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

    for key, page in (("devices", window.devices_page), ("collect", window.collect_page)):
        window.nav.set_current(key)
        _pump(styled_qapp)
        assert window.stack.currentWidget() is page
        assert prefs.load().last_view == key


def test_no_embedded_dashboard_viewer(window):
    """★ 결과 화면은 앱 안에 없다 — 생성된 HTML 파일을 사용자가 직접 연다."""
    assert not hasattr(window, "dashboard")
    assert set(window._pages) == {"collect", "devices"}
    assert [k for k in window.nav.keys()] == ["collect", "devices"]


def test_collect_flow_writes_html_and_updates_status(window, styled_qapp):
    from aoi_capacity import i18n
    from aoi_capacity.utils import paths

    warned = window._warned
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
    # 범위 안인데 접근하지 못한 장비는 수집 카드 안 알림에 이름이 나온다 — '확인' 을 눌러야 닫히는 팝업은 없다(10/24)
    page = window.collect_page
    assert not warned and page._outcome.isVisible() and "접근 못 함" in page._oc_body.text() and page._oc_dev.isVisible()
    page._oc_dev.click()
    assert window.nav.current() == "devices"
    window.nav.set_current("collect")
    window._start_collect(False, False)
    assert not page._outcome.isVisible()                          # 다음 수집이 시작되면 지난 알림은 사라진다
    while window.is_collecting() and time.time() - t0 < 40:
        _pump(styled_qapp)
    _pump(styled_qapp, 0.2)
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


def test_removed_options_are_not_on_the_settings_page(window):
    """10/30: 주의 장비 기준 · 이력 보관 기간 · NAS 동시 읽기 · 어두운 화면은 설정에서 없앴고, CSV 도 함께 저장 체크는 수집 화면에서 없앴다."""
    from PyQt6.QtWidgets import QCheckBox, QLabel

    page = window.settings_page
    for gone in ("_dark", "_th_util", "_th_err", "_retention", "_workers"):
        assert not hasattr(page, gone), gone
    assert not hasattr(window.collect_page, "_csv")
    texts = {lb.text() for lb in window.findChildren(QLabel)} | {b.text() for b in window.findChildren(QCheckBox)}
    for gone in ("주의 장비 기준", "이력 보관 기간", "NAS 마다 동시에 읽기", "어두운 화면", "CSV 도 함께 저장"):
        assert gone not in texts, gone


def test_collect_range_is_editable_and_saved(window, styled_qapp):
    """새로 넣은 장비를 며칠치부터 읽을지 — 설정에서 바꿀 수 있어야 한다(30대 확대 후 필요)."""
    from aoi_capacity.utils import prefs

    window.settings_page._backfill.setValue(3)
    _pump(styled_qapp)
    assert prefs.load().backfill_days == 3
    assert prefs.to_collect_cfg(prefs.load())["backfill_days"] == 3


def test_html_days_is_editable_and_reaches_the_collect_cfg(window, styled_qapp):
    """결과 HTML 기본 기간(일) — 설정에서 바꾸면 수집 cfg 의 html_days 로 간다(0 = 전부). 분할 설정(split_mb)은 롤백했다(10/5)."""
    from aoi_capacity.utils import prefs

    window.settings_page._html_days.setValue(12)
    _pump(styled_qapp)
    assert prefs.load().html_days == 12 and prefs.to_collect_cfg(prefs.load())["html_days"] == 12
    assert "split_mb" not in prefs.to_collect_cfg(prefs.load())


def test_html_only_card_builds_from_cache_without_collecting(window, styled_qapp, tmp_path):
    """'HTML 만 다시 만들기' 카드 — 가진 데이터가 없으면 버튼이 꺼져 있고, 기간 칸 둘과 실행 버튼이 있다."""
    page = window.collect_page
    for _ in range(50):
        _pump(styled_qapp)
        if page._days_worker is None:
            break
        page._days_worker.wait(200)
    _pump(styled_qapp)
    assert page._d_from.displayFormat() == "yyyy-MM-dd" and page._d_to.calendarPopup()
    assert not page._b_html.isEnabled() and not page._b_all.isEnabled()   # 테스트 데이터 폴더에는 캐시가 없다


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
    # 10/5 '기간 다시 읽기' — 전체 다시 만들기 밑, 날짜 두 칸(거꾸로 골라도 바로잡음), 고른 동안만 refresh_range
    from PyQt6.QtCore import QDate
    assert page.refresh_range() is None and not page._cards["range"].isHidden()
    page._r_from.setDate(QDate(2026, 9, 20))
    page._r_to.setDate(QDate(2026, 9, 10))
    page._pick("range")
    assert page.refresh_range() == ("2026-09-10", "2026-09-20") and page.options() == (False, False, False)
    assert prefs.load().refresh_window_days == 0
    page._pick("normal")
    assert page.refresh_range() is None
    # 10/24 RDL 영역 INI 패치 카드는 '옛 기간 빈칸 채우기' 로 합쳤다 — 상황 카드에서는 고를 수 없다
    page._pick("rdl")
    assert page.mode() == "normal" and "rdl" not in page._cards
    page._pick("recover")
    page.set_running(True)
    page.set_running(False)
    assert page.mode() == "normal"
    page.wait_for_plan()


def test_number_boxes_ignore_the_mouse_wheel(window):
    """10/11: 스크롤하다 숫자·날짜가 바뀌지 않는다 — 휠은 받지 않고 부모로 넘긴다."""
    from PyQt6.QtWidgets import QAbstractSpinBox

    boxes = window.collect_page.findChildren(QAbstractSpinBox)
    assert len(boxes) >= 8
    for b in boxes:
        assert type(b).wheelEvent is not QAbstractSpinBox.wheelEvent, type(b)


def test_settings_live_inside_the_collect_page(window):
    assert window.settings_page.parent() is not None
    assert window.collect_page.isAncestorOf(window.settings_page)


def test_gap_card_shows_missing_counts_and_fills_them(window, styled_qapp):
    """10/24 옛 기간 빈칸 채우기 — 수집 뒤 빈칸(이 가짜 NAS 는 ScanLog 가 없어 스캔 비율이 빈다)이 있으면 카드가 보이고, 누르면 채운 뒤 결과 파일을 다시 만든다."""
    from aoi_capacity import i18n

    page = window.collect_page
    window._start_collect(False, False)
    t0 = time.time()
    while window.is_collecting() and time.time() - t0 < 20:
        _pump(styled_qapp)
    page.wait_for_plan()
    _pump(styled_qapp, 0.3)
    assert not page._gaps.isHidden() and page._b_gaps.isEnabled()
    assert page._gap_rows["sec"].count.text().endswith(i18n.KO.GAPS_MISSING_WAFER_FMT.split("}")[-1])
    page._b_gaps.click()
    assert page.wafer_logs_running() and not page._b_run.isEnabled()        # 도는 동안 가동률 수집과 겹치지 않는다
    t0 = time.time()
    while page._gap_worker is not None and time.time() - t0 < 20:
        _pump(styled_qapp)
    page.wait_for_plan()
    _pump(styled_qapp, 0.3)
    assert page._gap_status.text().startswith(i18n.KO.GAPS_DONE_FMT.split("{")[0]), page._gap_status.text()
    assert page._gap_rows["sec"].count.text() == i18n.KO.GAPS_FULL and not page._b_gaps.isEnabled()


def test_loading_overlay_reads_cleanly(window, styled_qapp):
    """10/24 로딩 화면: 제목 = 고른 수집 방법, 총량 모르는 단계엔 장비 개수, 0 인 범례 없음, 문제 장비 이름은 툴팁, 빈 파일 줄은 숨김."""
    from aoi_capacity import i18n
    ov = window.overlay
    ov.show_overlay(window.collect_page.mode_title())
    assert ov._title.text() == window.collect_page.mode_title()
    ov.set_devices(["AOI-1", "AOI-2", "AOI-3"])
    ov.set_progress(0, 0, "장비 확인")
    assert ov._count.text() == i18n.KO.LOADING_DEVICES_FMT.format(done=0, total=3)
    assert i18n.KO.LOADING_LEGEND_ERR not in ov._legend.text()          # 0 이면 적지 않는다
    ov.set_device_state("AOI-2", "error")
    ov.set_device_state("AOI-1", "done")
    assert ov._count.text() == i18n.KO.LOADING_DEVICES_FMT.format(done=2, total=3)
    assert "AOI-2" in ov._legend.toolTip()
    assert not ov._detail.isVisible()
    ov.set_detail("AOI-3 · x_BatchReport.htm")
    assert ov._detail.isVisible()
    ov.set_progress(37, 240, "Report 읽기")
    assert ov._count.text() == "37 / 240" and ov._phase.text() == "Report 읽기"
    ov.set_stopping()
    ov.set_progress(38, 240, "Report 읽기")                             # 멈추는 중엔 단계 글자가 안내를 덮지 않는다
    assert ov._phase.text() == i18n.KO.LOADING_STOPPING_NOTE
    ov.hide_overlay()


def test_update_recheck_runs_every_30_minutes_and_skips_when_busy(window, styled_qapp, monkeypatch):
    """10/24: 켜 둔 동안에도 새 버전을 확인한다 — 수집 · 덮개 · 안내 창 중에는 건너뛴다."""
    from aoi_capacity.ui import main_window as mw

    _pump(styled_qapp, 0.6)
    assert window._update_timer.isActive() and window._update_timer.interval() == mw.UPDATE_RECHECK_MS == 30 * 60 * 1000
    calls = []
    monkeypatch.setattr(mw.MainWindow, "_check_for_update_async", lambda self, **k: calls.append(k))
    monkeypatch.setattr(mw.MainWindow, "is_collecting", lambda self: True)
    window._periodic_update_check()
    assert calls == []
    monkeypatch.setattr(mw.MainWindow, "is_collecting", lambda self: False)
    window._periodic_update_check()
    assert calls == [{"periodic": True}]


def test_periodic_update_check_only_shows_a_badge_and_badge_asks(window, styled_qapp, monkeypatch):
    """실행 중 확인은 창을 띄우지 않고 상단 바 알림만 — 거절한 버전이 30분마다 다시 묻지 않는다. 알림을 누르면 묻는다."""
    from aoi_capacity.ui import main_window as mw

    asked, applied = [], []
    monkeypatch.setattr(mw.sheets, "ask", lambda _w, title, body: asked.append(body) or mw.SB.No)
    monkeypatch.setattr(mw.MainWindow, "_apply_update", lambda self, info: applied.append(info["sha"]))
    monkeypatch.setattr(mw.MainWindow, "_updater", staticmethod(lambda: type("U", (), {"is_git_checkout": staticmethod(lambda: False)})))
    info = {"sha": "a" * 40, "message": "새 기능", "current": True, "repo": "r", "branch": "main"}

    w = mw._UpdateWorker(window._update_token, "check")
    w.periodic = True
    window._update_worker = w
    window._on_update_checked(window._update_token, False, ("update", info))
    assert asked == []
    assert window.nav.update_text() == "새 버전 aaaaaaa 받기"

    window.nav._update.click()           # 알림을 누르면 그때 묻는다
    assert len(asked) == 1 and applied == []
    monkeypatch.setattr(mw.sheets, "ask", lambda _w, title, body: asked.append(body) or mw.SB.Yes)
    window.nav._update.click()
    assert applied == ["a" * 40]

    w2 = mw._UpdateWorker(window._update_token, "check")     # 시작 때 확인은 예전처럼 묻는다
    window._update_worker = w2
    window._on_update_checked(window._update_token, False, ("update", info))
    assert len(asked) == 3


def test_test_path_card_saves_both_publish_folders_and_resets(window):
    """10/30 임시 카드(수집 창 맨 위) — '시험 경로 넣기'가 LOT 추적 · 전체 폴더를 prefs 에 저장하고 '원래 경로로'가 기본값으로 돌린다. 시험이 끝나면 카드와 함께 지운다."""
    from aoi_capacity import i18n
    from aoi_capacity.utils import config, prefs

    page = window.collect_page
    page._b_tp_apply.click()
    root = i18n.KO.TEST_PATH_ROOT
    lot, full = root + "\\" + i18n.KO.TEST_PATH_LOT_DIR, root + "\\" + i18n.KO.TEST_PATH_FULL_DIR
    assert page._tp_lot.text() == lot and page._tp_full.text() == full
    p = prefs.load()
    assert (p.publish_dir, p.publish_full_dir) == (lot, full)
    page._b_tp_reset.click()
    p = prefs.load()
    assert (p.publish_dir, p.publish_full_dir) == (config.PUBLISH_DIR_DEFAULT, config.PUBLISH_FULL_DIR_DEFAULT)
    page._tp_full.setText("")
    page._tp_full.editingFinished.emit()
    assert prefs.load().publish_full_dir == ""                    # 비우면 전체 배포 안 함
