"""수집 로딩창 — 현재 테마에 맞춰 직접 그린 카드.

구성(위→아래, 10/24 다시 짬 — 숫자가 제목보다 크던 것 · 빈 줄 · 0 인 범례를 걷어냄)
  ● 평소 수집                                01:23   ← 제목 = 고른 수집 방법
  Report 읽기                  37 / 240 · 남은 약 4분   ← 단계 + 개수(총량을 모르면 '장비 16 / 41')
  ▮▮▮▮▮▮▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯▯      ← 장비 스트립: 칸 하나 = 장비 하나, 올리면 이름 · 상태
  ━━━━━━━━━━━━━━━━━━━━╸               ← 진행 막대. 총량을 모르면 빛이 흐르는 busy
  AOI-15 · 파일명(모노, 흐림)                     ← 지금 읽는 것 — 없으면 줄째 숨김
  ■ 완료 12  ■ 읽는 중 4  ■ 접근 불가 1    [중지]   ← 0 인 항목은 적지 않음, 문제 장비 이름은 툴팁

계약: `set_progress(done, total, phase)` — `total<=0` 이면 busy. 애니메이션 타이머는 보이는 동안만 돈다.
"""
from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

from PyQt6.QtCore import QEvent, QObject, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from ... import i18n
from .. import theme
from .buttons import make_button

#: partial = 접근은 됐지만 Report 일부를 읽지 못함 — '완료(초록)' 와 구분한다
STATES = ("wait", "listing", "parsing", "done", "partial", "error", "skipped")


def _state_label(state: str) -> str:
    K = i18n.KO
    return {"wait": K.LOADING_LEGEND_WAIT, "listing": K.LOADING_LEGEND_READ, "parsing": K.LOADING_LEGEND_READ,
            "done": K.LOADING_LEGEND_DONE, "partial": K.LOADING_LEGEND_PARTIAL, "error": K.LOADING_LEGEND_ERR,
            "skipped": K.LOADING_LEGEND_SKIP}.get(state, state)


def _c(key: str) -> QColor:
    return QColor(theme.colors()[key])


def _left_text(sec: float) -> str:
    """남은 시간 글자 — '약 3분' · '1분 안쪽'."""
    m = int(sec + 30) // 60
    K = i18n.KO
    return K.ETA_UNDER_MIN if sec < 60 else K.ETA_MIN_FMT.format(m=m) if m < 60 else K.ETA_HOUR_FMT.format(h=m // 60, m=m % 60)


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
        self.setMouseTracking(True)

    def _geom(self):
        n = len(self._names)
        gap = 3 if n <= 40 else 2
        return gap, max(3.0, (self.width() - gap * (n - 1)) / n) if n else 0.0

    def name_at(self, x: float) -> Optional[str]:
        if not self._names:
            return None
        gap, cell = self._geom()
        i = int(x // (cell + gap))
        return self._names[i] if 0 <= i < len(self._names) else None

    def mouseMoveEvent(self, ev):  # noqa: N802
        name = self.name_at(ev.position().x())
        if name:
            QToolTip.showText(ev.globalPosition().toPoint(), f"{name} · {_state_label(self._state.get(name, 'wait'))}", self)
        else:
            QToolTip.hideText()

    def names_in(self, *states: str) -> List[str]:
        return [n for n in self._names if self._state.get(n) in states]

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
        gap, cell = self._geom()
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
        self._elapsed.setProperty("role", "loadElapsed")
        self._elapsed.setToolTip(i18n.KO.LOADING_ELAPSED_TIP)
        head.addWidget(self._dot)
        head.addSpacing(4)
        head.addWidget(self._title)
        head.addStretch(1)
        head.addWidget(self._elapsed)
        lay.addLayout(head)
        lay.addSpacing(2)

        # 단계 + 개수 한 줄 — 개수는 제목보다 작게(예전엔 22px 굵은 숫자가 제목 · 파일명을 눌렀다)
        prow = QHBoxLayout()
        prow.setSpacing(8)
        self._phase = QLabel("", self._card)
        self._phase.setProperty("role", "loadPhase")
        self._phase.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._count = QLabel("", self._card)
        self._count.setProperty("role", "loadCount")
        self._left = QLabel("", self._card)
        self._left.setProperty("role", "loadLeft")
        self._left.setToolTip(i18n.KO.LOADING_LEFT_TIP)
        prow.addWidget(self._phase, 1)
        prow.addWidget(self._count)
        prow.addWidget(self._left)
        lay.addLayout(prow)

        self._devices = DeviceStrip(self._card)
        lay.addWidget(self._devices)
        self._bar = ProgressStrip(self._card)
        lay.addWidget(self._bar)

        self._detail = QLabel("", self._card)
        self._detail.setProperty("role", "loadDetail")
        self._detail.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._detail.hide()
        lay.addWidget(self._detail)

        lay.addSpacing(2)
        foot = QHBoxLayout()
        self._legend = QLabel("", self._card)
        self._legend.setProperty("role", "legend")
        self._legend.setTextFormat(Qt.TextFormat.RichText)
        self._stop = make_button(i18n.KO.BTN_STOP, "default", self._card)
        self._stop.clicked.connect(self._on_stop)
        self._stop.setMinimumHeight(self._stop.sizeHint().height())      # 위 줄들이 Ignored 라 adjustSize 가 버튼을 눌렀다
        foot.addWidget(self._legend, 1)
        foot.addWidget(self._stop)
        lay.addLayout(foot)
        self._total = 0
        self._eta_total = None

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
        self._detail.hide()
        self._count.setText("")
        self._left.setText("")
        self._total = 0
        self._eta_total = None
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
        self._update_count()

    def set_device_state(self, name: str, state: str) -> None:
        self._devices.set_state(name, state)
        self._update_legend()
        if self._total <= 0:
            self._update_count()

    def set_progress(self, done: int, total: int, message: str = "") -> None:
        if message and self._stop.isEnabled():
            fm = self._phase.fontMetrics()
            self._phase.setText(fm.elidedText(message, Qt.TextElideMode.ElideMiddle, max(160, self._card.width() - 220)))
        self._total = total if total and total > 0 else 0
        if self._total:
            self._bar.set_fraction(done / total)
            now = time.monotonic()
            if total != self._eta_total or done < getattr(self, "_eta_done", 0):
                self._eta_t0, self._eta_total = now, total              # 단계(총량)가 바뀌었다 — 남은 시간은 새로 센다
            self._eta_done = done
            el = now - self._eta_t0
            self._left.setText(i18n.KO.LOADING_LEFT_FMT.format(t=_left_text(el * (total - done) / done))
                               if done >= 5 and el >= 8 and done < total else "")
            self._count.setText(i18n.KO.LOADING_COUNT_FMT.format(done=done, total=total))
        else:
            self._bar.set_fraction(None)
            self._left.setText("")
            self._update_count()

    def set_detail(self, text: str) -> None:
        fm = self._detail.fontMetrics()
        self._detail.setText(fm.elidedText(text, Qt.TextElideMode.ElideMiddle, max(120, self._card.width() - 56)))
        self._detail.setVisible(bool(text))

    def set_stopping(self) -> None:
        self._stop.setEnabled(False)
        self._stop.setText(i18n.KO.LOADING_STOPPING)
        self._phase.setText(i18n.KO.LOADING_STOPPING_NOTE)
        self._left.setText("")

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
        el = f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"
        self._elapsed.setText(i18n.KO.LOADING_ELAPSED_FMT.format(elapsed=el))

    def _update_count(self) -> None:
        """총량을 모르는 단계(장비 확인 · 목록)에는 장비 기준 개수를 적는다 — 빈 칸으로 두지 않는다."""
        if self._total > 0:
            return
        c = self._devices.counts()
        n = sum(c.values())
        fin = c["done"] + c["partial"] + c["error"] + c["skipped"]
        self._count.setText(i18n.KO.LOADING_DEVICES_FMT.format(done=fin, total=n) if n else "")

    def _update_legend(self) -> None:
        """0 인 항목은 적지 않는다. 문제 장비(접근 불가 · 일부 실패)의 이름은 툴팁에."""
        c = self._devices.counts()
        col = theme.colors()
        K = i18n.KO
        items = ((col["good"], K.LOADING_LEGEND_DONE, c["done"]),
                 (col["accent"], K.LOADING_LEGEND_READ, c["listing"] + c["parsing"]),
                 (col["line_2"], K.LOADING_LEGEND_WAIT, c["wait"]),
                 (col["warn"], K.LOADING_LEGEND_PARTIAL, c["partial"]),
                 (col["crit"], K.LOADING_LEGEND_ERR, c["error"]))
        self._legend.setText("&nbsp;&nbsp;&nbsp;".join(f'<span style="color:{color}">■</span>&nbsp;{label}&nbsp;<b>{n}</b>'
                                                       for color, label, n in items if n))
        tips = []
        for state, label in (("error", K.LOADING_LEGEND_ERR), ("partial", K.LOADING_LEGEND_PARTIAL)):
            names = self._devices.names_in(state)
            if names:
                tips.append(f"{label}: {', '.join(names)}")
        self._legend.setToolTip("\n".join(tips))
