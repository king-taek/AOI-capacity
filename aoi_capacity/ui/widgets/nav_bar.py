"""상단 바 — 결과 HTML 의 `.hdr` 와 같은 모양(9/23): 브랜드(파란 막대 + 이름) · 내비 탭 · 오른쪽에 마지막 수집 시각.

예전의 왼쪽 사이드바를 대신한다. 공개 API(`keys` · `set_current` · `current` · `set_status` · `current_changed`)는 그대로다."""
from __future__ import annotations

from typing import Iterable, Tuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from ... import i18n


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


# 수집 전용 프로그램 — 결과 화면(가동률·Error·추이)은 생성된 HTML 파일 쪽에 있다.
NAV_ITEMS: Tuple[Tuple[str, str, str], ...] = (
    ("collect", i18n.KO.NAV_COLLECT, i18n.KO.NAV_COLLECT_SUB),
    ("devices", i18n.KO.NAV_DEVICES, i18n.KO.NAV_DEVICES_SUB),
    ("settings", i18n.KO.NAV_SETTINGS, i18n.KO.NAV_SETTINGS_SUB),
)


class NavBar(QWidget):
    current_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None, items: Iterable[Tuple[str, str, str]] = NAV_ITEMS):
        super().__init__(parent)
        self.setProperty("role", "top")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(58)
        self._items: dict[str, QPushButton] = {}
        self._current = ""
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(16)
        logo = QLabel(self)
        logo.setProperty("role", "logo")
        logo.setFixedSize(9, 18)
        brand = QLabel(i18n.KO.APP_BRAND, self)
        brand.setProperty("role", "brand")
        lay.addWidget(logo)
        lay.addSpacing(-7)
        lay.addWidget(brand)
        lay.addSpacing(4)
        nav = QHBoxLayout()
        nav.setSpacing(2)
        for key, title, sub in items:
            b = QPushButton(title, self)
            b.setProperty("role", "nav")
            b.setProperty("current", "false")
            b.setToolTip(sub)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _c=False, k=key: self.set_current(k))
            nav.addWidget(b)
            self._items[key] = b
        lay.addLayout(nav)
        lay.addStretch(1)
        self._status = QLabel("", self)
        self._status.setProperty("role", "stamp")
        self._status.setToolTip(i18n.KO.CREDIT)
        lay.addWidget(self._status)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def keys(self) -> list[str]:
        return list(self._items)

    def set_current(self, key: str) -> None:
        if key not in self._items:
            return
        changed = key != self._current
        self._current = key
        for k, b in self._items.items():
            b.setProperty("current", "true" if k == key else "false")
            _repolish(b)
        if changed:
            self.current_changed.emit(key)

    def current(self) -> str:
        return self._current

    def set_status(self, text: str) -> None:
        self._status.setText(text)
