"""수집 페이지 — '지금 수집' 버튼, 수집 기간 설정, 결과 HTML 안내, 로그. 실제 실행은 MainWindow 가 워커로 한다.

결과 화면은 이 프로그램 안에 없다. 수집이 만든 HTML 한 장을 사용자가 더블클릭해서 본다
('결과 화면 열기' 버튼은 그 파일을 기본 브라우저로 띄워 주는 편의 기능일 뿐이다)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget)

from ... import collect, i18n, nas_guard
from ...utils import paths, prefs, results
from ..widgets.buttons import make_button

MAX_LOG_LINES = 1000


class _PlanWorker(QThread):
    """계획 조회를 UI 스레드 밖에서 — 캐시 파일(수십 MB)을 읽는 동안 창이 멈추지 않게. 결과는 토큰으로 가려 늦게 온 옛 조회는 버린다."""
    result = pyqtSignal(int, object)   # token, RunPlan | None

    def __init__(self, token: int, cfg: dict, full: bool, backfill: bool, recover: bool, parent=None):
        super().__init__(parent)
        self._args = (token, cfg, full, backfill, recover)

    def run(self) -> None:  # noqa: D401
        token, cfg, full, backfill, recover = self._args
        try:
            plan = collect.plan_run(cfg, full=full, backfill=backfill, recover=recover)
        except Exception:  # noqa: BLE001
            plan = None
        self.result.emit(token, plan)


class CollectPage(QWidget):
    collect_requested = pyqtSignal(bool, bool, bool)   # full, backfill, recover
    stop_requested = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._running = False
        self._plan_token = 0
        self._plan_worker: Optional[_PlanWorker] = None
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
        self._opt_recover = QCheckBox(i18n.KO.COLLECT_OPT_RECOVER, top)
        # D60: 최근 N일 다시 읽기(이력 보존) — N 은 아래 '처음 수집 기간' 값을 같이 쓴다. prefs.refresh_window_days → cfg 로 간다.
        self._opt_refresh = QCheckBox("", top)
        opts = QHBoxLayout()
        opts.addWidget(self._opt_refresh)
        opts.addWidget(self._opt_backfill)
        opts.addWidget(self._opt_full)
        opts.addWidget(self._opt_recover)
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
        self._opt_refresh.setChecked(int(p.refresh_window_days or 0) > 0)
        self._refresh_option_label()
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

        # 결과 화면(HTML 한 장) — 더블클릭이 기본, 버튼은 편의
        rcard = QFrame(self)
        rcard.setProperty("role", "card")
        rl = QVBoxLayout(rcard)
        rl.setContentsMargins(18, 14, 18, 14)
        rl.setSpacing(8)
        rt = QLabel(i18n.KO.COLLECT_RESULT_TITLE, rcard)
        rt.setProperty("role", "cardTitle")
        self._result = QLabel("", rcard)
        self._result.setProperty("role", "mono")
        self._result.setWordWrap(True)
        self._result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hint = QLabel(i18n.KO.COLLECT_RESULT_HINT, rcard)
        hint.setProperty("role", "help")
        hint.setWordWrap(True)
        rrow = QHBoxLayout()
        self._b_open = make_button(i18n.KO.BTN_OPEN_RESULT, "primary", rcard)
        self._b_folder = make_button(i18n.KO.BTN_OPEN_RESULT_FOLDER, "ghost", rcard)
        rrow.addWidget(self._b_open)
        rrow.addWidget(self._b_folder)
        rrow.addStretch(1)
        rl.addWidget(rt)
        rl.addWidget(self._result)
        rl.addWidget(hint)
        rl.addLayout(rrow)
        lay.addWidget(rcard)

        # 로그
        lt = QLabel(i18n.KO.COLLECT_LOG_TITLE, self)
        lt.setProperty("role", "eyebrow")
        self._log = QPlainTextEdit(self)
        self._log.setProperty("role", "console")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(MAX_LOG_LINES)
        lay.addWidget(lt)
        lay.addWidget(self._log, 1)

        self._b_open.clicked.connect(self._open_result)
        self._b_folder.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(paths.output_dir(prefs.load().output_dir)))))
        self._b_run.clicked.connect(self._on_run)
        self._b_stop.clicked.connect(self.stop_requested.emit)
        self._b_out.clicked.connect(self._browse_out)
        self._backfill.valueChanged.connect(lambda v: (prefs.patch(backfill_days=int(v)), self._apply_refresh_option(), self.refresh_plan()))
        self._opt_refresh.toggled.connect(lambda _x: (self._apply_refresh_option(), self.refresh_plan()))
        self._retention.valueChanged.connect(lambda v: prefs.patch(retention_days=int(v)))
        self._csv.toggled.connect(lambda on: prefs.patch(write_csv=bool(on)))
        self._out.editingFinished.connect(self._apply_out)
        self._opt_backfill.toggled.connect(lambda _x: self.refresh_plan())
        self._opt_full.toggled.connect(lambda _x: self.refresh_plan())
        self._opt_recover.toggled.connect(lambda _x: self.refresh_plan())
        self.refresh_plan()
        self.refresh_result()

    # ── 공개 API ──
    def refresh_result(self) -> None:
        """결과 파일 경로와 버튼 상태를 갱신한다(수집 직후·설정 변경 후)."""
        path = results.html_path()
        have = path.is_file()
        self._result.setText(str(path) if have else i18n.KO.COLLECT_RESULT_NONE)
        self._b_open.setEnabled(have)
        self._b_folder.setEnabled(True)

    def _open_result(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(results.ensure_html())))

    def refresh_plan(self) -> None:
        """계획 문구를 갱신한다 — 캐시 읽기는 워커 스레드에서(UI 스레드가 몇 초씩 멈추던 원인)."""
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        self._plan_token += 1
        token = self._plan_token
        self._plan.setText(i18n.KO.COLLECT_PLAN_LOADING)
        w = _PlanWorker(token, cfg, self._opt_full.isChecked(), self._opt_backfill.isChecked(), self._opt_recover.isChecked(), self)
        w.result.connect(self._on_plan)
        w.finished.connect(lambda w=w: self._plan_done(w))
        self._plan_worker = w
        w.start()

    def _plan_done(self, w: "_PlanWorker") -> None:
        # deleteLater 뒤에도 self._plan_worker 가 죽은 래퍼를 쥐고 있으면 closeEvent 의 isRunning() 이
        # RuntimeError 를 내고 PyQt 가 qFatal 로 프로세스를 죽인다(Linux CI 에서 실측). 참조를 먼저 지운다.
        if self._plan_worker is w:
            self._plan_worker = None
        w.deleteLater()

    def wait_for_plan(self, ms: int = 10_000) -> None:
        """테스트·종료용 — 진행 중인 계획 조회를 기다린다."""
        w = self._plan_worker
        if w is None:
            return
        try:
            running = w.isRunning()
        except RuntimeError:                            # 이미 삭제된 래퍼
            self._plan_worker = None
            return
        if running:
            w.wait(ms)

    def _refresh_option_label(self) -> None:
        self._opt_refresh.setText(i18n.KO.COLLECT_OPT_REFRESH_FMT.format(days=int(self._backfill.value())))

    def _apply_refresh_option(self) -> None:
        """체크 상태 → prefs.refresh_window_days(켜면 '처음 수집 기간' 일수, 끄면 0) → to_collect_cfg 가 cfg 로 넘긴다."""
        self._refresh_option_label()
        days = int(self._backfill.value()) if self._opt_refresh.isChecked() else 0
        if int(prefs.load().refresh_window_days or 0) != days:
            prefs.patch(refresh_window_days=days)

    def refresh_days(self) -> int:
        return int(self._backfill.value()) if self._opt_refresh.isChecked() else 0

    def _on_plan(self, token: int, plan) -> None:
        if token != self._plan_token:
            return                                      # 늦게 온 옛 조회
        if plan is None:
            self._plan.setText("")
            return
        if self._opt_full.isChecked():
            text = i18n.KO.COLLECT_PLAN_FULL_FMT.format(days=plan.retention_days)
        elif plan.refresh_days > 0 and not plan.first_run:
            text = i18n.KO.COLLECT_PLAN_REFRESH_FMT.format(days=plan.refresh_days, reread=plan.reread_reports,
                                                           keep=plan.keep_reports)
        elif self._opt_backfill.isChecked():
            text = i18n.KO.COLLECT_PLAN_BACKFILL_FMT.format(days=plan.backfill_days)
        elif plan.first_run:
            text = i18n.KO.COLLECT_PLAN_FIRST_FMT.format(days=plan.backfill_days)
        elif self._opt_recover.isChecked():
            text = (i18n.KO.COLLECT_PLAN_RECOVER_FMT.format(n=plan.recover_reports) if plan.recover_reports
                    else i18n.KO.COLLECT_PLAN_RECOVER_NONE)
        else:
            text = i18n.KO.COLLECT_PLAN_INCR_FMT.format(n=plan.known_devices)
        self._plan.setText(text)

    def set_running(self, running: bool) -> None:
        self._running = running
        self._b_run.setEnabled(not running)
        self._b_stop.setVisible(running)
        self._b_stop.setEnabled(running)
        for w in (self._opt_refresh, self._opt_backfill, self._opt_full, self._opt_recover, self._backfill, self._retention,
                  self._out, self._b_out, self._csv):
            w.setEnabled(not running)
        self._status.setText(i18n.KO.COLLECT_RUNNING if running else i18n.KO.COLLECT_IDLE)
        if not running:
            self._opt_backfill.setChecked(False)
            self._opt_full.setChecked(False)
            self._opt_recover.setChecked(False)
            self._opt_refresh.setChecked(False)         # 한 번 실행하는 옵션 — 끄면서 prefs 도 0 으로 되돌린다
            self._apply_refresh_option()
            self.refresh_plan()

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    def options(self) -> tuple:
        return self._opt_full.isChecked(), self._opt_backfill.isChecked(), self._opt_recover.isChecked()

    # ── 내부 ──
    def _on_run(self) -> None:
        full, backfill, recover = self.options()
        self.collect_requested.emit(full, backfill, recover)

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
