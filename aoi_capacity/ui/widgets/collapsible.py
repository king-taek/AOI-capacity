"""접이식 구역 — 제목 줄을 누르면 안의 내용이 펼쳐지고 접힌다. 기본은 접힘(자주 안 쓰는 도구를 첫 화면에서 치운다, 10/11)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class Collapsible(QWidget):
    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None, *, open_: bool = False):
        super().__init__(parent)
        self._title = title
        self._content = content
        self._head = QPushButton(self)
        self._head.setProperty("role", "section")
        self._head.setCursor(Qt.CursorShape.PointingHandCursor)
        self._head.setCheckable(True)
        self._head.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(10)
        head.addWidget(self._head)
        self._note = QLabel("", self)                  # 11/25: 머리 오른쪽 흐린 한 줄 — 왜 못 쓰는지 등(마우스를 올리지 않아도 보이게)
        self._note.setProperty("role", "muted")
        self._note.hide()
        head.addWidget(self._note)
        head.addStretch(1)
        lay.addLayout(head)
        lay.addWidget(content)
        self._head.toggled.connect(self._apply)
        self._head.setChecked(open_)
        self._apply(open_)

    def _apply(self, on: bool) -> None:
        self._head.setText(("▾  " if on else "▸  ") + self._title)
        self._content.setVisible(on)

    def is_open(self) -> bool:
        return self._head.isChecked()

    def set_open(self, on: bool) -> None:
        self._head.setChecked(on)

    def set_note(self, text: str) -> None:
        self._note.setText(text)
        self._note.setVisible(bool(text))

    def note(self) -> str:
        return self._note.text() if self._note.isVisibleTo(self) else ""
