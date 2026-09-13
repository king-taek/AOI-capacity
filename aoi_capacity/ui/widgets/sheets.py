"""창 안에 뜨는 시트(팝업) — OS 대화상자 대신 현재 테마의 카드로 묻고 알린다.

API (참고 저장소와 같은 시그니처)
    sheets.info(parent, title, text) / warn / error   → StandardButton.Ok
    sheets.ask(parent, title, text, buttons, default) → 사용자가 누른 StandardButton
호스트(`SheetHost`)는 MainWindow 가 `self._sheets` 로 만들어 둔다. 호스트를 못 찾으면 네이티브 QMessageBox 로 폴백.
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QEvent, QEventLoop, QObject, Qt
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

from ... import i18n
from .. import theme
from .buttons import make_button

SB = QMessageBox.StandardButton
_LABELS = {SB.Ok: i18n.KO.BTN_OK, SB.Cancel: i18n.KO.BTN_CANCEL, SB.Yes: i18n.KO.BTN_YES, SB.No: i18n.KO.BTN_NO, SB.Close: i18n.KO.BTN_CLOSE}
_ORDER = (SB.Yes, SB.Ok, SB.No, SB.Cancel, SB.Close)


def _scrim_color() -> QColor:
    c = QColor(15, 19, 25, 170) if theme.is_dark_mode() else QColor(15, 23, 32, 110)
    return c


class SheetHost(QWidget):
    """부모 창 전체를 덮는 오버레이. 한 번에 시트 하나만 띄운다."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.hide()
        self._loop: Optional[QEventLoop] = None
        self._result = SB.NoButton
        self._default = SB.NoButton
        self._escape = SB.NoButton
        self._frame: Optional[QFrame] = None
        parent.installEventFilter(self)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # 부모 크기를 따라간다
    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:  # noqa: N802
        if obj is self.parent() and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            self._center()
        return super().eventFilter(obj, ev)

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), _scrim_color())

    def _center(self) -> None:
        if self._frame:
            f = self._frame
            f.adjustSize()
            w = min(max(f.sizeHint().width(), 380), max(380, self.width() - 48))
            f.resize(w, f.sizeHint().height())
            f.move((self.width() - f.width()) // 2, max(24, (self.height() - f.height()) // 3))

    def keyPressEvent(self, ev):  # noqa: N802
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._default != SB.NoButton:
            self._finish(self._default)
        elif ev.key() == Qt.Key.Key_Escape and self._escape != SB.NoButton:
            self._finish(self._escape)
        else:
            super().keyPressEvent(ev)

    def _finish(self, btn) -> None:
        self._result = btn
        if self._loop:
            self._loop.quit()

    def run(self, title: str, text: str, buttons, default, kind: str = "info"):
        """모달로 띄우고 누른 버튼을 돌려준다(중첩 이벤트 루프)."""
        if self._loop:  # 이미 떠 있으면 네이티브 폴백(중첩 방지)
            return _native(self.parent(), title, text, buttons, default, kind)
        self.setGeometry(self.parent().rect())
        frame = QFrame(self)
        frame.setProperty("role", "sheet")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)
        t = QLabel(title, frame)
        t.setProperty("role", "sheetTitle")
        t.setWordWrap(True)
        b = QLabel(text, frame)
        b.setProperty("role", "sheetBody")
        b.setWordWrap(True)
        b.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(t)
        lay.addWidget(b)
        row = QHBoxLayout()
        row.addStretch(1)
        chosen = [x for x in _ORDER if buttons & x]
        self._default = default if default in chosen else (chosen[0] if chosen else SB.NoButton)
        self._escape = SB.Cancel if SB.Cancel in chosen else (SB.No if SB.No in chosen else (SB.Ok if SB.Ok in chosen else SB.Close if SB.Close in chosen else SB.NoButton))
        for x in chosen:
            role = "primary" if x == self._default else ("danger" if kind == "error" and x == SB.Ok and len(chosen) > 1 else "default")
            btn = make_button(_LABELS.get(x, str(x)), role, frame)
            btn.clicked.connect(lambda _c=False, _x=x: self._finish(_x))
            row.addWidget(btn)
        lay.addLayout(row)
        self._frame = frame
        self._result = SB.NoButton
        self.show()
        self.raise_()
        frame.show()
        self._center()
        self.setFocus()
        self._loop = QEventLoop(self)
        self._loop.exec()
        self._loop = None
        frame.hide()
        frame.deleteLater()
        self._frame = None
        self.hide()
        return self._result


def host_for(widget: Optional[QWidget]) -> Optional[SheetHost]:
    w = widget
    while w is not None:
        host = getattr(w, "_sheets", None)
        if isinstance(host, SheetHost):
            return host
        w = w.parentWidget()
    return None


def _native(parent, title, text, buttons, default, kind):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default != SB.NoButton:
        box.setDefaultButton(default)
    box.setIcon({"info": QMessageBox.Icon.Information, "warn": QMessageBox.Icon.Warning, "error": QMessageBox.Icon.Critical,
                 "ask": QMessageBox.Icon.Question}.get(kind, QMessageBox.Icon.NoIcon))
    return SB(box.exec())


def _show(parent, title, text, buttons, default, kind):
    host = host_for(parent)
    if host is None:
        return _native(parent, title, text, buttons, default, kind)
    return host.run(title, text, buttons, default, kind)


def info(parent, title, text):
    return _show(parent, title, text, SB.Ok, SB.Ok, "info")


def warn(parent, title, text):
    return _show(parent, title, text, SB.Ok, SB.Ok, "warn")


def error(parent, title, text):
    return _show(parent, title, text, SB.Ok, SB.Ok, "error")


def ask(parent, title, text, buttons=SB.Yes | SB.No, default=SB.Yes):
    return _show(parent, title, text, buttons, default, "ask")
