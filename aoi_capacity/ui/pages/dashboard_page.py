"""대시보드 — 수집기가 만든 HTML(template.html + 데이터)을 QWebEngineView 로 그대로 보여준다.

- QWebChannel 없음. 앱 → HTML 방향의 `runJavaScript` 만 쓴다(`go(view)`, `setTheme(mode)`, `setThresholds(u,e)`).
- URL 쿼리 `gui=1` 로 HTML 이 GUI 모드(사이드바·브라우저 전용 수집 메뉴 숨김)로 뜬다.
- QtWebEngine 을 못 불러오면(회사 PC 정책, 테스트 환경 `AOI_NO_WEBENGINE=1`) 안내 + "브라우저로 열기" 폴백.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl, QUrlQuery
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ... import collect, i18n
from ...utils import paths, prefs
from ..widgets.buttons import make_button

WEBENGINE_AVAILABLE = False
if os.environ.get("AOI_NO_WEBENGINE") != "1":
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401

        WEBENGINE_AVAILABLE = True
    except Exception:  # noqa: BLE001 - 모듈 없음 / DLL 로드 실패
        WEBENGINE_AVAILABLE = False

VIEWS = ("home", "trend", "compare")


def build_url(html_path: Path, view: str, p: prefs.Prefs) -> QUrl:
    url = QUrl.fromLocalFile(str(html_path))
    q = QUrlQuery()
    q.addQueryItem("gui", "1")
    q.addQueryItem("theme", "light" if p.color_mode == "light" else "dark")
    q.addQueryItem("view", view if view in VIEWS else "home")
    q.addQueryItem("th_util", str(int(p.threshold_util)))
    q.addQueryItem("th_err", str(int(p.threshold_err)))
    try:
        q.addQueryItem("v", str(int(html_path.stat().st_mtime)))  # 캐시 버스터
    except OSError:
        q.addQueryItem("v", "0")
    url.setQuery(q)
    return url


class DashboardPage(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._view = "home"
        self._loaded = False
        self._pending_view: Optional[str] = None
        self._web = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        if WEBENGINE_AVAILABLE:
            from PyQt6.QtWebEngineWidgets import QWebEngineView

            self._web = QWebEngineView(self)
            self._web.loadFinished.connect(self._on_loaded)
            lay.addWidget(self._web)
        else:
            card = QFrame(self)
            card.setProperty("role", "card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(28, 24, 28, 24)
            t = QLabel(i18n.KO.DASH_NO_WEBENGINE_TITLE, card)
            t.setProperty("role", "h2")
            b = QLabel(i18n.KO.DASH_NO_WEBENGINE_BODY, card)
            b.setProperty("role", "help")
            b.setWordWrap(True)
            btn = make_button(i18n.KO.BTN_OPEN_BROWSER, "primary", card)
            btn.clicked.connect(self.open_in_browser)
            cl.addWidget(t)
            cl.addWidget(b)
            cl.addWidget(btn, 0, Qt.AlignmentFlag.AlignLeft)
            lay.addWidget(card, 0, Qt.AlignmentFlag.AlignTop)
            lay.addStretch(1)

    # ── HTML 파일 ──
    def html_path(self) -> Path:
        return paths.output_html(prefs.load().output_dir)

    def ensure_html(self) -> Path:
        """아직 수집한 적이 없으면 빈 데이터 HTML 을 만들어 둔다(화면이 비지 않게)."""
        path = self.html_path()
        if not path.exists():
            cfg = prefs.to_collect_cfg(prefs.load())
            import time

            collect.write_html(cfg, [], [], [], time.time(), mode="gui")
        return path

    def current_url(self) -> QUrl:
        return build_url(self.ensure_html(), self._view, prefs.load())

    # ── 표시 ──
    def load(self) -> None:
        if self._web is None:
            return
        self._loaded = False
        self._web.load(self.current_url())

    def reload_after_collect(self) -> None:
        self.load()

    def show_view(self, view: str) -> None:
        self._view = view if view in VIEWS else "home"
        if self._web is None:
            return
        if self._loaded:
            self._js(f"go({json.dumps(self._view)})")
        else:
            self._pending_view = self._view

    def set_theme(self, mode: str) -> None:
        self._js(f"setTheme({json.dumps('light' if mode == 'light' else 'dark')})")

    def set_thresholds(self, util: int, err: int) -> None:
        self._js(f"setThresholds({int(util)},{int(err)})")

    def open_in_browser(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.ensure_html())))

    # ── 내부 ──
    def _js(self, code: str) -> None:
        if self._web is not None and self._loaded:
            self._web.page().runJavaScript(code)

    def _on_loaded(self, ok: bool) -> None:
        self._loaded = bool(ok)
        if self._pending_view:
            v, self._pending_view = self._pending_view, None
            self.show_view(v)
