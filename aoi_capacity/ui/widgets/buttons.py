"""버튼 — role 프로퍼티(default / primary / ghost / danger)로 style.qss 가 모양을 정한다."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QWidget


def make_button(text: str, role: str = "default", parent: QWidget | None = None, tooltip: str = "") -> QPushButton:
    b = QPushButton(text, parent)
    b.setProperty("role", role)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    return b


def set_role(button: QPushButton, role: str) -> None:
    """role 을 바꾸면 스타일을 다시 계산하게 한다(QSS 는 프로퍼티 변경을 자동으로 보지 않는다)."""
    button.setProperty("role", role)
    button.style().unpolish(button)
    button.style().polish(button)
