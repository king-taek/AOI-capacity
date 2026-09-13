"""수집 페이지 — '지금 수집' 버튼, 수집 기간 설정, 로그. 실제 실행은 MainWindow 가 워커로 한다."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget)

from ... import collect, i18n, nas_guard
from ...utils import paths, prefs
from ..widgets.buttons import make_button

MAX_LOG_LINES = 1000


class CollectPage(QWidget):
    collect_requested = pyqtSignal(bool, bool)   # full, backfill
    stop_requested = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._running = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        h = QLabel(i18n.KO.COLLECT_PAGE_TITLE, self)
        h.setProperty("role", "h2")
        lay.addWidget(h)

        # 계획 안내 + 실행 버튼
        top = QFrame(self)
        top.setProperty("role", "card")
        tl = QVBoxLayout(top)
        tl.setContentsMargins(18, 16, 18, 16)
        tl.setSpacing(10)
        self._plan = QLabel("", top)
        self._plan.setProperty("role", "help")
        self._plan.setWordWrap(True)
        row = QHBoxLayout()
        self._b_run = make_button(i18n.KO.BTN_COLLECT_NOW, "primary", top)
        self._b_stop = make_button(i18n.KO.BTN_STOP, "default", top)
        self._b_stop.hide()
        self._status = QLabel(i18n.KO.COLLECT_IDLE, top)
        self._status.setProperty("role", "muted")
        row.addWidget(self._b_run)
        row.addWidget(self._b_stop)
        row.addSpacing(8)
        row.addWidget(self._status, 1)
        self._opt_backfill = QCheckBox(i18n.KO.COLLECT_OPT_BACKFILL, top)
        self._opt_full = QCheckBox(i18n.KO.COLLECT_OPT_FULL, top)
        opts = QHBoxLayout()
        opts.addWidget(self._opt_backfill)
        opts.addWidget(self._opt_full)
        opts.addStretch(1)
        tl.addWidget(self._plan)
        tl.addLayout(row)
        tl.addLayout(opts)
        lay.addWidget(top)

        # 설정
        card = QFrame(self)
        card.setProperty("role", "card")
        g = QGridLayout(card)
        g.setContentsMargins(18, 14, 18, 14)
        g.setHorizontalSpacing(12)
        g.setVerticalSpacing(8)
        p = prefs.load()
        self._backfill = QSpinBox(card)
        self._backfill.setRange(1, 3650)
        self._backfill.setSuffix(i18n.KO.COLLECT_DAYS_SUFFIX)
        self._backfill.setValue(int(p.backfill_days))
        self._retention = QSpinBox(card)
        self._retention.setRange(1, 3650)
        self._retention.setSuffix(i18n.KO.COLLECT_DAYS_SUFFIX)
        self._retention.setValue(int(p.retention_days))
        self._out = QLineEdit(p.output_dir, card)
        self._out.setProperty("role", "mono")
        self._out.setPlaceholderText(str(paths.data_root()))
        self._b_out = make_button(i18n.KO.BTN_BROWSE, parent=card)
        self._csv = QCheckBox(i18n.KO.COLLECT_WRITE_CSV, card)
        self._csv.setChecked(bool(p.write_csv))
        g.addWidget(QLabel(i18n.KO.COLLECT_BACKFILL_DAYS, card), 0, 0)
        g.addWidget(self._backfill, 0, 1)
        g.addWidget(QLabel(i18n.KO.COLLECT_RETENTION_DAYS, card), 0, 2)
        g.addWidget(self._retention, 0, 3)
        g.addWidget(QLabel(i18n.KO.COLLECT_OUTPUT_DIR, card), 1, 0)
        g.addWidget(self._out, 1, 1, 1, 2)
        g.addWidget(self._b_out, 1, 3)
        hint = QLabel(i18n.KO.COLLECT_OUTPUT_DEFAULT_HINT, card)
        hint.setProperty("role", "muted")
        g.addWidget(hint, 2, 1, 1, 3)
        g.addWidget(self._csv, 3, 1, 1, 3)
        g.setColumnStretch(1, 1)
        lay.addWidget(card)

        # 로그
        lt = QLabel(i18n.KO.COLLECT_LOG_TITLE, self)
        lt.setProperty("role", "eyebrow")
        self._log = QPlainTextEdit(self)
        self._log.setProperty("role", "console")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(MAX_LOG_LINES)
        lay.addWidget(lt)
        lay.addWidget(self._log, 1)

        self._b_run.clicked.connect(self._on_run)
        self._b_stop.clicked.connect(self.stop_requested.emit)
        self._b_out.clicked.connect(self._browse_out)
        self._backfill.valueChanged.connect(lambda v: (prefs.patch(backfill_days=int(v)), self.refresh_plan()))
        self._retention.valueChanged.connect(lambda v: prefs.patch(retention_days=int(v)))
        self._csv.toggled.connect(lambda on: prefs.patch(write_csv=bool(on)))
        self._out.editingFinished.connect(self._apply_out)
        self._opt_backfill.toggled.connect(lambda _x: self.refresh_plan())
        self._opt_full.toggled.connect(lambda _x: self.refresh_plan())
        self.refresh_plan()

    # ── 공개 API ──
    def refresh_plan(self) -> None:
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        try:
            plan = collect.plan_run(cfg, full=self._opt_full.isChecked(), backfill=self._opt_backfill.isChecked())
        except Exception:  # noqa: BLE001
            self._plan.setText("")
            return
        if self._opt_full.isChecked():
            text = i18n.KO.COLLECT_PLAN_FULL_FMT.format(days=plan.backfill_days)
        elif self._opt_backfill.isChecked():
            text = i18n.KO.COLLECT_PLAN_BACKFILL_FMT.format(days=plan.backfill_days)
        elif plan.first_run:
            text = i18n.KO.COLLECT_PLAN_FIRST_FMT.format(days=plan.backfill_days)
        else:
            text = i18n.KO.COLLECT_PLAN_INCR_FMT.format(n=plan.known_devices)
        self._plan.setText(text)

    def set_running(self, running: bool) -> None:
        self._running = running
        self._b_run.setEnabled(not running)
        self._b_stop.setVisible(running)
        self._b_stop.setEnabled(running)
        for w in (self._opt_backfill, self._opt_full, self._backfill, self._retention, self._out, self._b_out, self._csv):
            w.setEnabled(not running)
        self._status.setText(i18n.KO.COLLECT_RUNNING if running else i18n.KO.COLLECT_IDLE)
        if not running:
            self._opt_backfill.setChecked(False)
            self._opt_full.setChecked(False)
            self.refresh_plan()

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def options(self) -> tuple:
        return self._opt_full.isChecked(), self._opt_backfill.isChecked()

    # ── 내부 ──
    def _on_run(self) -> None:
        full, backfill = self.options()
        self.collect_requested.emit(full, backfill)

    def _browse_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, i18n.KO.COLLECT_OUTPUT_DIR, self._out.text() or str(paths.data_root()))
        if chosen:
            self._out.setText(chosen)
            self._apply_out()

    def _apply_out(self) -> None:
        value = self._out.text().strip()
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        try:
            nas_guard.assert_local(paths.output_dir(value), nas_guard.roots_for_cfg(cfg))
        except nas_guard.NasWriteRefused:
            self._out.setText(p.output_dir)
            self.error.emit(i18n.KO.COLLECT_OUTPUT_ON_NAS_TITLE, i18n.KO.COLLECT_OUTPUT_ON_NAS_BODY)
            return
        if value != p.output_dir:
            prefs.patch(output_dir=value)
