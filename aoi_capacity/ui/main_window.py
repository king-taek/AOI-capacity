"""메인 창 — 좌측 NavBar | QStackedWidget(대시보드 · 장비 목록 · 수집 · 설정).

- 수집은 `CollectorWorker`(QThread) 로 돌리고 창 위에 `LoadingOverlay` 를 덮는다. 시그널마다 토큰을 비교해
  옛 실행의 늦은 신호는 버린다. 완료되면 대시보드(HTML)를 다시 읽고, 취소·실패 시 이전 결과는 그대로다.
- 업데이트 확인은 `utils.updater` 를 지연 import 한다(M4 에서 추가). 모듈이 없어도 앱은 정상 동작한다.
- 테스트(conftest)는 `_check_for_update_async` 를 클래스 수준에서 막는다.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Dict, Optional

from PyQt6.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from .. import devices, i18n
from ..utils import paths, prefs
from ..workers.collector import CollectorWorker, CollectResult
from . import theme
from .pages.collect_page import CollectPage
from .pages.dashboard_page import VIEWS, DashboardPage
from .pages.devices_page import DevicesPage
from .pages.settings_page import SettingsPage
from .widgets import sheets
from .widgets.loading_overlay import LoadingOverlay
from .widgets.nav_bar import NavBar
from .widgets.sheets import SB, SheetHost

log = logging.getLogger("aoi.ui")

# 살아 있는 워커를 모듈 전역에 잡아둔다 — 창이 먼저 사라져도 QThread 가 GC 로 죽지 않게.
_LIVE_COLLECTORS: Dict[int, CollectorWorker] = {}
STATUS_FLASH_MS = 4000


class _UpdateSignals(QObject):
    checked = pyqtSignal(int, bool, object)      # token, manual, (status, info)
    progress = pyqtSignal(int, int, int, str)    # token, done, total, phase
    applied = pyqtSignal(int, object)            # token, result dict
    failed = pyqtSignal(int, str)                # token, message


class _UpdateWorker(QThread):
    """업데이트 확인/적용을 UI 밖에서. `mode` ∈ {"check", "apply"}."""

    def __init__(self, token: int, mode: str, manual: bool = False, info: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self.token, self.mode, self.manual, self.info = token, mode, manual, info or {}
        self.signals = _UpdateSignals()

    def run(self) -> None:  # noqa: D401
        from ..utils import updater  # 지연 import — 없으면 호출부에서 이미 걸렀다

        tok = self.token
        try:
            if self.mode == "check":
                if self.manual:
                    result = updater.manual_check()
                else:
                    info = updater.check_for_update()
                    result = ("update", info) if info else ("latest", {})
                self.signals.checked.emit(tok, self.manual, result)
                return
            ok = updater.download_and_apply(
                self.info.get("repo", ""), self.info.get("branch", ""), self.info.get("sha", ""),
                progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)))
            if not ok:
                self.signals.failed.emit(tok, updater.last_error())
                return
            self.signals.applied.emit(tok, {"staged": updater.update_pending(), "deps_changed": updater.deps_changed()})
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(tok, f"{type(exc).__name__}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(i18n.KO.APP_TITLE)
        icon = paths.logo_path("logo.ico")
        if icon.is_file():
            self.setWindowIcon(QIcon(str(icon)))
        self._collect_token = 0
        self._worker: Optional[CollectorWorker] = None
        self._update_token = 0
        self._update_worker: Optional[_UpdateWorker] = None
        self._update_info: Optional[dict] = None
        self._restore_geometry()

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.nav = NavBar(central)
        self.stack = QStackedWidget(central)
        page_wrap = QWidget(central)
        page_wrap.setProperty("role", "main")
        wl = QVBoxLayout(page_wrap)
        wl.setContentsMargins(18, 16, 18, 16)
        wl.addWidget(self.stack)
        root.addWidget(self.nav)
        root.addWidget(page_wrap, 1)

        self.dashboard = DashboardPage(self.stack)
        self.devices_page = DevicesPage(self.stack)
        self.collect_page = CollectPage(self.stack)
        self.settings_page = SettingsPage(self.stack)
        self._pages = {"dashboard": self.dashboard, "devices": self.devices_page,
                       "collect": self.collect_page, "settings": self.settings_page}
        for w in self._pages.values():
            self.stack.addWidget(w)

        self._sheets = SheetHost(self)        # sheets.host_for() 가 이 속성 이름을 찾는다
        self.overlay = LoadingOverlay(central)

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._refresh_last_collect)
        self._collect_timer = QTimer(self)    # 예약: 자동 수집(prefs.auto_collect_minutes>0 일 때만 시작)
        self._collect_timer.timeout.connect(lambda: self._start_collect(False, False))

        self._wire()
        self.dashboard.load()
        self._refresh_last_collect()
        p = prefs.load()
        self.nav.set_current(p.last_view if p.last_view in self.nav.keys() else "home")
        if p.last_view in self.nav.keys():
            self._on_nav(p.last_view)
        if int(p.auto_collect_minutes) > 0:
            self._collect_timer.start(int(p.auto_collect_minutes) * 60_000)
        QTimer.singleShot(400, self._check_for_update_async)

    # ── 배선 ──
    def _wire(self) -> None:
        self.nav.current_changed.connect(self._on_nav)
        self.collect_page.collect_requested.connect(self._start_collect)
        self.collect_page.stop_requested.connect(self._stop_collect)
        self.collect_page.error.connect(lambda t, b: sheets.error(self, t, b))
        self.overlay.cancel_requested.connect(self._stop_collect)
        self.devices_page.saved.connect(self.collect_page.refresh_plan)
        self.devices_page.error.connect(lambda t, b: sheets.error(self, t, b))
        self.devices_page.message.connect(self.flash_status)
        self.settings_page.theme_changed.connect(self._on_theme)
        self.settings_page.thresholds_changed.connect(self.dashboard.set_thresholds)
        self.settings_page.update_check_requested.connect(lambda: self._check_for_update_async(manual=True))

    # ── 내비게이션 ──
    def _on_nav(self, key: str) -> None:
        if self.stack.currentWidget() is self.devices_page and key != "devices":
            self._confirm_devices_dirty()
        if key in VIEWS:
            self.stack.setCurrentWidget(self.dashboard)
            self.dashboard.show_view(key)
        elif key in self._pages:
            self.stack.setCurrentWidget(self._pages[key])
        prefs.patch(last_view=key)

    def current_page_key(self) -> str:
        return self.nav.current()

    def _confirm_devices_dirty(self) -> None:
        if not self.devices_page.is_dirty():
            return
        if sheets.ask(self, i18n.KO.DEV_UNSAVED_TITLE, i18n.KO.DEV_UNSAVED_BODY) == SB.Yes:
            self.devices_page.save()

    # ── 상태줄(내비 하단) ──
    def _refresh_last_collect(self) -> None:
        html = paths.output_html(prefs.load().output_dir)
        try:
            ts = html.stat().st_mtime
            when = time.strftime("%m-%d %H:%M", time.localtime(ts))
            self.nav.set_status(i18n.KO.NAV_LAST_COLLECT_FMT.format(when=when))
        except OSError:
            self.nav.set_status(i18n.KO.NAV_LAST_COLLECT_NEVER)

    def flash_status(self, text: str) -> None:
        self.nav.set_status(text)
        self._status_timer.start(STATUS_FLASH_MS)

    # ── 테마 ──
    def _on_theme(self, mode: str) -> None:
        app = QApplication.instance()
        if app is not None:
            theme.apply_to_app(app, mode)
        self.dashboard.set_theme(mode)
        self.overlay.update()

    # ── 수집 ──
    def is_collecting(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _start_collect(self, full: bool = False, backfill: bool = False) -> None:
        if self.is_collecting():
            sheets.warn(self, i18n.KO.COLLECT_BUSY_TITLE, i18n.KO.COLLECT_BUSY_BODY)
            return
        self._confirm_devices_dirty()
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        names = self._device_names(cfg)
        if not names:
            sheets.warn(self, i18n.KO.COLLECT_NO_DEVICES_TITLE, i18n.KO.COLLECT_NO_DEVICES_BODY)
            return
        self._collect_token += 1
        tok = self._collect_token
        w = CollectorWorker(tok, cfg, full=full, backfill=backfill)
        s = w.signals
        s.progress.connect(self._on_collect_progress)
        s.device.connect(self._on_collect_device)
        s.log.connect(self._on_collect_log)
        s.done.connect(self._on_collect_done)
        s.failed.connect(self._on_collect_failed)
        s.cancelled.connect(self._on_collect_cancelled)
        _LIVE_COLLECTORS[tok] = w
        self._worker = w
        self.collect_page.set_running(True)
        self.overlay.show_overlay(i18n.KO.LOADING_COLLECT_TITLE, cancelable=True)
        self.overlay.set_devices(names)
        log.info("collect start token=%s full=%s backfill=%s devices=%s", tok, full, backfill, len(names))
        w.start()

    @staticmethod
    def _device_names(cfg: dict) -> list:
        try:
            return [d["name"] for d in devices.resolve_devices(cfg)]
        except Exception as exc:  # noqa: BLE001 - CSV 깨짐 등은 워커가 다시 만나 failed 로 보고한다
            log.warning("resolve_devices failed before collect: %s", exc)
            return []

    def _stop_collect(self) -> None:
        if self.is_collecting() and self._worker is not None:
            self.overlay.set_stopping()
            self._worker.stop()

    def _is_current(self, token: int) -> bool:
        return token == self._collect_token

    def _release_worker(self, token: int) -> None:
        w = _LIVE_COLLECTORS.pop(token, None)
        if w is not None:
            w.wait(3000)
        if self._worker is w:
            self._worker = None

    def _on_collect_progress(self, token: int, done: int, total: int, phase: str) -> None:
        if self._is_current(token):
            self.overlay.set_progress(done, total, phase)

    def _on_collect_device(self, token: int, name: str, state: str, detail: str) -> None:
        if not self._is_current(token):
            return
        self.overlay.set_device_state(name, state)
        if detail:
            self.overlay.set_detail(f"{name} · {detail}")

    def _on_collect_log(self, token: int, line: str) -> None:
        if self._is_current(token):
            self.collect_page.append_log(line)

    def _finish_collect(self, token: int) -> None:
        self._release_worker(token)
        self.overlay.hide_overlay()
        self.collect_page.set_running(False)

    def _on_collect_done(self, token: int, result: CollectResult) -> None:
        if not self._is_current(token):
            self._release_worker(token)
            return
        self._finish_collect(token)
        m, s = divmod(int(result.elapsed), 60)
        toast = i18n.KO.COLLECT_DONE_TOAST_FMT.format(devices=result.devices, rows=result.rows, elapsed=f"{m:02d}:{s:02d}")
        self.collect_page.set_status(toast)
        self.collect_page.append_log(toast)
        self.dashboard.reload_after_collect()
        self._refresh_last_collect()
        bad = result.bad_devices
        if bad or result.errors:
            sheets.warn(self, i18n.KO.COLLECT_DONE_WITH_ERRORS_TITLE,
                        i18n.KO.COLLECT_DONE_WITH_ERRORS_FMT.format(bad_devices=len(bad), bad_reports=len(result.errors)))

    def _on_collect_failed(self, token: int, message: str) -> None:
        if not self._is_current(token):
            self._release_worker(token)
            return
        self._finish_collect(token)
        log.error("collect failed: %s", message)
        self.collect_page.append_log(message)
        sheets.error(self, i18n.KO.COLLECT_FAILED_TITLE, i18n.KO.COLLECT_FAILED_FMT.format(detail=message))

    def _on_collect_cancelled(self, token: int) -> None:
        if not self._is_current(token):
            self._release_worker(token)
            return
        self._finish_collect(token)
        self.collect_page.set_status(i18n.KO.COLLECT_CANCELLED_TOAST)
        self.collect_page.append_log(i18n.KO.COLLECT_CANCELLED_TOAST)

    # ── 업데이트 ──
    @staticmethod
    def _updater():
        try:
            from ..utils import updater
            return updater
        except Exception as exc:  # noqa: BLE001 - M4 이전 또는 손상된 설치
            log.info("updater unavailable: %s", exc)
            return None

    def _check_for_update_async(self, manual: bool = False) -> None:
        upd = self._updater()
        if upd is None:
            if manual:
                sheets.info(self, i18n.KO.UPDATE_CHECK_TITLE, i18n.KO.UPDATE_UNKNOWN)
            return
        if self._update_worker is not None and self._update_worker.isRunning():
            return
        self._update_token += 1
        w = _UpdateWorker(self._update_token, "check", manual=manual, parent=self)
        w.signals.checked.connect(self._on_update_checked)
        w.signals.failed.connect(self._on_update_failed)
        self._update_worker = w
        if manual:
            self.flash_status(i18n.KO.UPDATE_CHECKING)
        w.start()

    def _on_update_checked(self, token: int, manual: bool, result) -> None:
        if token != self._update_token:
            return
        status, info = (result or ("unknown", {}))[:2]
        info = dict(info or {})
        if status == "update":
            sha = str(info.get("sha", ""))[:7]
            msg = info.get("message") or ""
            body = (i18n.KO.UPDATE_AVAILABLE_BODY_FMT.format(sha=sha, message=f" · {msg}" if msg else "")
                    if info.get("current") else i18n.KO.UPDATE_UNKNOWN_CURRENT_FMT.format(sha=sha))
            upd = self._updater()
            if upd is not None and getattr(upd, "is_git_checkout", lambda: False)():
                if manual:
                    sheets.info(self, i18n.KO.UPDATE_AVAILABLE_TITLE, i18n.KO.UPDATE_GIT_HINT)
                return
            if sheets.ask(self, i18n.KO.UPDATE_AVAILABLE_TITLE, body) == SB.Yes:
                self._apply_update(info)
        elif manual:
            sheets.info(self, i18n.KO.UPDATE_CHECK_TITLE,
                        i18n.KO.UPDATE_LATEST if status == "latest" else i18n.KO.UPDATE_UNKNOWN)

    def _apply_update(self, info: dict) -> None:
        if self.is_collecting():
            sheets.warn(self, i18n.KO.COLLECT_BUSY_TITLE, i18n.KO.UPDATE_BUSY_BODY)
            return
        self._update_token += 1
        self._update_info = info
        w = _UpdateWorker(self._update_token, "apply", info=info, parent=self)
        w.signals.progress.connect(self._on_update_progress)
        w.signals.applied.connect(self._on_update_applied)
        w.signals.failed.connect(self._on_update_failed)
        self._update_worker = w
        self.overlay.show_overlay(i18n.KO.UPDATE_DOWNLOADING, cancelable=False)
        self.overlay.set_progress(0, 0, i18n.KO.UPDATE_PHASE_DOWNLOAD)
        w.start()

    def _on_update_progress(self, token: int, done: int, total: int, phase: str) -> None:
        if token == self._update_token:
            self.overlay.set_progress(done, total, phase)

    def _on_update_applied(self, token: int, result) -> None:
        if token != self._update_token:
            return
        self.overlay.hide_overlay()
        res = dict(result or {})
        body = i18n.KO.UPDATE_DONE_RESTART_STAGED if res.get("staged") else i18n.KO.UPDATE_DONE_RESTART
        if res.get("deps_changed"):
            body += i18n.KO.UPDATE_DEPS_CHANGED
        sheets.info(self, i18n.KO.UPDATE_CHECK_TITLE, body)
        self.settings_page.refresh_version()
        if res.get("needs_restart", True):
            app = QApplication.instance()
            if app is not None:
                QTimer.singleShot(0, app.quit)

    def _on_update_failed(self, token: int, message: str) -> None:
        if token != self._update_token:
            return
        self.overlay.hide_overlay()
        log.error("update failed: %s", message)
        if self._update_worker is not None and self._update_worker.mode == "apply":
            upd = self._updater()
            blocked = bool(upd is not None and getattr(upd, "deps_blocked", lambda: False)())
            head = i18n.KO.UPDATE_NEEDS_NEW_BUNDLE if blocked else i18n.KO.UPDATE_FAILED
            sheets.error(self, i18n.KO.UPDATE_CHECK_TITLE, f"{head}\n\n{message}")
        elif self._update_worker is not None and self._update_worker.manual:
            sheets.info(self, i18n.KO.UPDATE_CHECK_TITLE, f"{i18n.KO.UPDATE_UNKNOWN}\n\n{message}")

    # ── 창 ──
    def _restore_geometry(self) -> None:
        p = prefs.load()
        w = int(p.window_width) if int(p.window_width) >= 900 else 1280
        h = int(p.window_height) if int(p.window_height) >= 600 else 820
        self.resize(w, h)
        self.setMinimumSize(900, 600)
        if p.window_maximized:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def closeEvent(self, ev) -> None:  # noqa: N802
        maximized = bool(self.windowState() & Qt.WindowState.WindowMaximized)
        g = self.normalGeometry() if maximized else self.geometry()
        prefs.patch(window_width=int(g.width()), window_height=int(g.height()), window_maximized=maximized)
        self._collect_token += 1
        self._update_token += 1
        for tok, w in list(_LIVE_COLLECTORS.items()):
            w.stop()
            w.wait(3000)
            _LIVE_COLLECTORS.pop(tok, None)
        self._worker = None
        if self._update_worker is not None and self._update_worker.isRunning():
            self._update_worker.wait(3000)
        super().closeEvent(ev)
