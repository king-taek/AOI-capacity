"""입력 칸 — 마우스 휠로 값이 바뀌지 않는다(10/11 사용자 요청: 페이지를 스크롤하다 숫자·날짜가 슬며시 바뀌는 사고).

11/25(사용자: "화살표 필요없음. 날짜는 달력으로 고를 수 있도록 해주고, 최근 며칠 다시 읽기는 숫자 입력으로만 되도록. 스크롤도 없이 오직 숫자 입력만"):
- 숫자 칸(`NoWheelSpinBox`)은 ▲▼ 단추가 없고 휠 · 방향키 · PageUp/Down 으로도 바뀌지 않는다 — 자판으로 숫자를 쳐서만 바꾼다.
- 날짜 칸(`NoWheelDateEdit`)도 ▲▼ · 드롭다운 화살표가 없다. 칸을 누르면(또는 F4 · Alt+↓) 달력이 열리고 고르면 닫힌다. 자판으로 날짜를 쳐도 된다.
휠 이벤트는 받지 않고 부모(스크롤 영역)로 넘긴다."""
from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QAbstractSpinBox, QCalendarWidget, QDateEdit, QSpinBox, QVBoxLayout, QFrame

_STEP_KEYS = (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_PageUp, Qt.Key.Key_PageDown)


class NoWheelSpinBox(QSpinBox):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def wheelEvent(self, ev):  # noqa: N802
        ev.ignore()

    def keyPressEvent(self, ev):  # noqa: N802
        if ev.key() in _STEP_KEYS:                       # 숫자는 쳐서만 — 방향키로 값이 움직이지 않는다
            ev.ignore()
            return
        super().keyPressEvent(ev)

    def stepBy(self, steps: int) -> None:  # noqa: N802 - 어떤 길로도 한 칸씩 올리고 내리지 않는다
        return


class _CalendarPopup(QFrame):
    def __init__(self, edit: "NoWheelDateEdit"):
        super().__init__(edit, Qt.WindowType.Popup)
        self.setProperty("role", "calPopup")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.cal = QCalendarWidget(self)
        self.cal.setGridVisible(False)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        lay.addWidget(self.cal)
        self._edit = edit
        self.cal.clicked.connect(self._pick)
        self.cal.activated.connect(self._pick)

    def _pick(self, d: QDate) -> None:
        self._edit.setDate(d)
        self.close()


class NoWheelDateEdit(QDateEdit):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._popup = None

    def setCalendarPopup(self, on: bool) -> None:  # noqa: N802 - Qt 기본 팝업(화살표가 붙는다) 대신 칸을 누르면 여는 달력
        self._want_cal = bool(on)

    def calendarPopup(self) -> bool:  # noqa: N802
        return bool(getattr(self, "_want_cal", True))

    def wheelEvent(self, ev):  # noqa: N802
        ev.ignore()

    def stepBy(self, steps: int) -> None:  # noqa: N802
        return

    def open_calendar(self) -> None:
        if not self.isEnabled():
            return
        if self._popup is None:
            self._popup = _CalendarPopup(self)
        cal = self._popup.cal
        cal.setDateRange(self.minimumDate(), self.maximumDate())
        cal.setSelectedDate(self.date())
        self._popup.adjustSize()
        self._popup.move(self.mapToGlobal(self.rect().bottomLeft()))
        self._popup.show()
        cal.setFocus()

    def calendar_open(self) -> bool:
        return self._popup is not None and self._popup.isVisible()

    def mousePressEvent(self, ev):  # noqa: N802
        super().mousePressEvent(ev)
        if ev.button() == Qt.MouseButton.LeftButton:
            self.open_calendar()

    def keyPressEvent(self, ev):  # noqa: N802
        alt_down = ev.key() == Qt.Key.Key_Down and ev.modifiers() & Qt.KeyboardModifier.AltModifier
        if ev.key() == Qt.Key.Key_F4 or alt_down:
            self.open_calendar()
            return
        if ev.key() in _STEP_KEYS:
            ev.ignore()
            return
        super().keyPressEvent(ev)
