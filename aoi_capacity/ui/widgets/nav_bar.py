"""좌측 내비게이션 — template.html 의 .side 와 같은 항목·부제. 항목 전체가 클릭 대상이다."""
from __future__ import annotations

from typing import Iterable, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ... import i18n


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


class NavItem(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, sub: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.key = key
        self.setProperty("role", "navItem")
        self.setProperty("current", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(1)
        t = QLabel(title, self)
        t.setProperty("role", "navTitle")
        s = QLabel(sub, self)
        s.setProperty("role", "navSub")
        lay.addWidget(t)
        lay.addWidget(s)

    def set_current(self, on: bool) -> None:
        self.setProperty("current", "true" if on else "false")
        _repolish(self)
        for c in self.findChildren(QLabel):
            _repolish(c)

    def mouseReleaseEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.MouseButton.LeftButton and self.rect().contains(ev.pos()):
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(ev)


# 수집 전용 프로그램 — 결과 화면(홈·추이·비교)은 생성된 HTML 파일 쪽에 있다.
NAV_ITEMS: Tuple[Tuple[str, str, str], ...] = (
    ("collect", i18n.KO.NAV_COLLECT, i18n.KO.NAV_COLLECT_SUB),
    ("devices", i18n.KO.NAV_DEVICES, i18n.KO.NAV_DEVICES_SUB),
    ("settings", i18n.KO.NAV_SETTINGS, i18n.KO.NAV_SETTINGS_SUB),
)
_GAP_BEFORE = {"settings"}  # 실행 메뉴와 설정 사이 여백


class NavBar(QWidget):
    current_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None, items: Iterable[Tuple[str, str, str]] = NAV_ITEMS):
        super().__init__(parent)
        self.setProperty("role", "side")
        self.setFixedWidth(210)
        self._items: dict[str, NavItem] = {}
        self._current = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 14, 10, 12)
        lay.setSpacing(2)
        for key, title, sub in items:
            if key in _GAP_BEFORE:
                lay.addSpacing(12)
            it = NavItem(key, title, sub, self)
            it.clicked.connect(self.set_current)
            lay.addWidget(it)
            self._items[key] = it
        lay.addStretch(1)
        self._status = QLabel("", self)
        self._status.setProperty("role", "foot")
        self._status.setWordWrap(True)
        foot = QLabel(i18n.KO.CREDIT, self)
        foot.setProperty("role", "foot")
        foot.setWordWrap(True)
        lay.addWidget(self._status)
        lay.addWidget(foot)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def keys(self) -> list[str]:
        return list(self._items)

    def set_current(self, key: str) -> None:
        if key not in self._items:
            return
        changed = key != self._current
        self._current = key
        for k, it in self._items.items():
            it.set_current(k == key)
        if changed:
            self.current_changed.emit(key)

    def current(self) -> str:
        return self._current

    def set_status(self, text: str) -> None:
        self._status.setText(text)
