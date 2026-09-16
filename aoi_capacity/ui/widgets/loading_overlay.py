"""수집 로딩창 — 현재 테마에 맞춰 직접 그린 카드.

구성(위→아래)
  ● 데이터 수집                      경과 01:23
  AOI-12 · 2D@R2-…_BatchReport.htm            ← 단계(phase)
  ▮▮▮▮▮▮▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯      ← 장비 스트립: 장비 하나가 칸 하나(대기/읽는 중/완료/접근 불가)
  ━━━━━━━━━━━━━━━━━━━━╸               ← 진행 막대. 총량을 모르면 빛이 흐르는 busy
  파일명(모노, 흐림)                      37 / 240
  범례                                          [중지]

계약: `set_progress(done, total, phase)` — `total<=0` 이면 busy. 애니메이션 타이머는 보이는 동안만 돈다.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

from PyQt6.QtCore import QEvent, QObject, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ... import i18n
from .. import theme
from .buttons import make_button

#: partial = 접근은 됐지만 Report 일부를 읽지 못함 — '완료(초록)' 와 구분한다
STATES = ("wait", "listing", "parsing", "done", "partial", "error", "skipped")


def _c(key: str) -> QColor:
    return QColor(theme.colors()[key])


class _PulseDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self.phase = 0.0

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _c("accent")
        halo = QColor(c)
        halo.setAlpha(int(70 + 60 * math.sin(self.phase)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        r = 5 + 2 * (0.5 + 0.5 * math.sin(self.phase))
        p.drawEllipse(QRectF(7 - r, 7 - r, 2 * r, 2 * r))
        p.setBrush(c)
        p.drawEllipse(QRectF(4, 4, 6, 6))


class DeviceStrip(QWidget):
    """장비 하나 = 칸 하나. 30대가 넘어도 한 줄에 들어가도록 칸 너비를 계산한다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._names: List[str] = []
        self._state: Dict[str, str] = {}
        self._pulse = 0.0
        self.setFixedHeight(18)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_devices(self, names: List[str]) -> None:
        self._names = list(names)
        self._state = {n: "wait" for n in names}
        self.update()

    def set_state(self, name: str, state: str) -> None:
        if name not in self._state:
            self._names.append(name)
        self._state[name] = state if state in STATES else "wait"
        self.update()

    def counts(self) -> Dict[str, int]:
        out = {s: 0 for s in STATES}
        for s in self._state.values():
            out[s] += 1
        return out

    def tick(self, pulse: float) -> None:
        self._pulse = pulse
        if any(s in ("listing", "parsing") for s in self._state.values()):
            self.update()

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        n = len(self._names)
        if not n:
            p.setBrush(_c("nodata"))
            p.drawRoundedRect(QRectF(0, 4, self.width(), 10), 3, 3)
            return
        gap = 3 if n <= 40 else 2
        cell = max(3.0, (self.width() - gap * (n - 1)) / n)
        colors = {"wait": _c("nodata"), "listing": _c("accent"), "parsing": _c("accent"),
                  "done": _c("good"), "partial": _c("warn"), "error": _c("crit"), "skipped": _c("line_2")}
        x = 0.0
        for name in self._names:
            st = self._state.get(name, "wait")
            col = QColor(colors[st])
            if st in ("listing", "parsing"):
                col.setAlpha(int(150 + 100 * (0.5 + 0.5 * math.sin(self._pulse))))
            p.setBrush(col)
            p.drawRoundedRect(QRectF(x, 2, cell, 14), 2, 2)
            x += cell + gap


class ProgressStrip(QWidget):
    """진행 막대. 값은 목표를 향해 부드럽게 따라가고(tween), 총량을 모르면 빛이 흐른다(busy)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._target = 0.0
        self._shown = 0.0
        self._busy = True
        self._sweep = 0.0

    def set_fraction(self, frac: Optional[float]) -> None:
        if frac is None:
            self._busy = True
            return
        self._busy = False
        frac = max(0.0, min(1.0, frac))
        if frac < self._target:      # 범위가 바뀌어 뒤로 가면 튀지 않게 즉시 맞춘다
            self._shown = frac
        self._target = frac

    def tick(self) -> None:
        if self._busy:
            self._sweep = (self._sweep + 0.018) % 1.3
        else:
            self._shown += (self._target - self._shown) * 0.18
            if abs(self._target - self._shown) < 0.002:
                self._shown = self._target
        self.update()

    def reset(self) -> None:
        self._target = self._shown = 0.0
        self._busy = True

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        p.setBrush(_c("raise_"))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        acc, acc2 = _c("accent"), _c("accent_2")
        if self._busy:
            span = w * 0.32
            x = (self._sweep - 0.3) * w
            g = QLinearGradient(x, 0, x + span, 0)
            t = QColor(acc)
            t.setAlpha(0)
            g.setColorAt(0.0, t)
            g.setColorAt(0.5, acc2)
            g.setColorAt(1.0, t)
            p.setBrush(g)
            p.drawRoundedRect(QRectF(max(0.0, x), 0, min(span, w - max(0.0, x)), h), h / 2, h / 2)
        else:
            fill = max(0.0, w * self._shown)
            if fill > 0:
                g = QLinearGradient(0, 0, fill, 0)
                g.setColorAt(0.0, acc)
                g.setColorAt(1.0, acc2)
                p.setBrush(g)
                p.drawRoundedRect(QRectF(0, 0, max(fill, h), h), h / 2, h / 2)


class LoadingOverlay(QWidget):
    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.hide()
        parent.installEventFilter(self)
        self._t0 = 0.0
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

        self._card = QFrame(self)
        self._card.setProperty("role", "loadCard")
        self._card.setFixedWidth(600)
        lay = QVBoxLayout(self._card)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(10)

        head = QHBoxLayout()
        self._dot = _PulseDot(self._card)
        self._title = QLabel(i18n.KO.LOADING_COLLECT_TITLE, self._card)
        self._title.setProperty("role", "loadTitle")
        self._elapsed = QLabel("", self._card)
        self._elapsed.setProperty("role", "loadDetail")
        head.addWidget(self._dot)
        head.addSpacing(6)
        head.addWidget(self._title)
        head.addStretch(1)
        head.addWidget(self._elapsed)
        lay.addLayout(head)

        self._phase = QLabel("", self._card)
        self._phase.setProperty("role", "loadPhase")
        self._phase.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(self._phase)

        self._devices = DeviceStrip(self._card)
        lay.addWidget(self._devices)
        self._bar = ProgressStrip(self._card)
        lay.addWidget(self._bar)

        row = QHBoxLayout()
        self._detail = QLabel("", self._card)
        self._detail.setProperty("role", "loadDetail")
        self._detail.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._count = QLabel("", self._card)
        self._count.setProperty("role", "loadCount")
        row.addWidget(self._detail, 1)
        row.addWidget(self._count)
        lay.addLayout(row)

        foot = QHBoxLayout()
        self._legend = QLabel("", self._card)
        self._legend.setProperty("role", "legend")
        self._legend.setTextFormat(Qt.TextFormat.RichText)
        self._stop = make_button(i18n.KO.BTN_STOP, "default", self._card)
        self._stop.clicked.connect(self._on_stop)
        foot.addWidget(self._legend, 1)
        foot.addWidget(self._stop)
        lay.addLayout(foot)

    # ── 배치 ──
    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:  # noqa: N802
        if obj is self.parent() and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.parent().rect())
            self._center()
        return super().eventFilter(obj, ev)

    def _center(self) -> None:
        self._card.adjustSize()
        self._card.move((self.width() - self._card.width()) // 2, max(24, (self.height() - self._card.height()) // 3))

    def paintEvent(self, _ev):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(15, 19, 25, 170) if theme.is_dark_mode() else QColor(15, 23, 32, 110))

    # ── API ──
    def show_overlay(self, title: str = "", cancelable: bool = True) -> None:
        self._t0 = time.time()
        self._title.setText(title or i18n.KO.LOADING_COLLECT_TITLE)
        self._phase.setText("")
        self._detail.setText("")
        self._count.setText("")
        self._bar.reset()
        self._devices.set_devices([])
        self._stop.setVisible(cancelable)
        self._stop.setEnabled(True)
        self._stop.setText(i18n.KO.BTN_STOP)
        self._update_legend()
        self.setGeometry(self.parent().rect())
        self.show()
        self.raise_()
        self._center()
        self._timer.start()

    def hide_overlay(self) -> None:
        self._timer.stop()
        self.hide()

    def set_devices(self, names: List[str]) -> None:
        self._devices.set_devices(names)
        self._update_legend()

    def set_device_state(self, name: str, state: str) -> None:
        self._devices.set_state(name, state)
        self._update_legend()

    def set_progress(self, done: int, total: int, message: str = "") -> None:
        if message:
            fm = self._phase.fontMetrics()
            self._phase.setText(fm.elidedText(message, Qt.TextElideMode.ElideMiddle, max(160, self._card.width() - 60)))
        if total and total > 0:
            self._bar.set_fraction(done / total)
            self._count.setText(i18n.KO.LOADING_COUNT_FMT.format(done=done, total=total))
        else:
            self._bar.set_fraction(None)
            self._count.setText("")

    def set_detail(self, text: str) -> None:
        fm = self._detail.fontMetrics()
        self._detail.setText(fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max(120, self._card.width() - 200)))

    def set_stopping(self) -> None:
        self._stop.setEnabled(False)
        self._stop.setText(i18n.KO.LOADING_STOPPING)
        self._phase.setText(i18n.KO.LOADING_STOPPING)

    # ── 내부 ──
    def _on_stop(self) -> None:
        self.set_stopping()
        self.cancel_requested.emit()

    def _tick(self) -> None:
        self._pulse += 0.16
        self._dot.phase = self._pulse
        self._dot.update()
        self._devices.tick(self._pulse)
        self._bar.tick()
        s = int(time.time() - self._t0)
        self._elapsed.setText(i18n.KO.LOADING_ELAPSED_FMT.format(elapsed=f"{s // 60:02d}:{s % 60:02d}"))

    def _update_legend(self) -> None:
        c = self._devices.counts()
        col = theme.colors()

        def sw(color, label, n):
            return f'<span style="color:{color}">■</span> {label} {n}'

        self._legend.setText("&nbsp;&nbsp;".join([
            sw(col["nodata"], i18n.KO.LOADING_LEGEND_WAIT, c["wait"]),
            sw(col["accent"], i18n.KO.LOADING_LEGEND_READ, c["listing"] + c["parsing"]),
            sw(col["good"], i18n.KO.LOADING_LEGEND_DONE, c["done"]),
            sw(col["warn"], i18n.KO.LOADING_LEGEND_PARTIAL, c["partial"]),
            sw(col["crit"], i18n.KO.LOADING_LEGEND_ERR, c["error"]),
        ]))
