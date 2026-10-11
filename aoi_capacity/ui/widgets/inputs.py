"""마우스 휠로 값이 바뀌지 않는 입력 칸 — 페이지를 스크롤하다 숫자·날짜가 슬며시 바뀌는 사고를 막는다(10/11 사용자 요청).

휠 이벤트는 받지 않고 부모(스크롤 영역)로 넘긴다. 값은 칸을 눌러 직접 쓰거나 ▲▼ 버튼·방향키로만 바뀐다."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDateEdit, QSpinBox


class NoWheelSpinBox(QSpinBox):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, ev):  # noqa: N802
        ev.ignore()


class NoWheelDateEdit(QDateEdit):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, ev):  # noqa: N802
        ev.ignore()
