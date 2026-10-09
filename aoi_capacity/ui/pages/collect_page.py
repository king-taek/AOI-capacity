"""수집 페이지 — **지금 상황에 맞는 수집을 고르고 시작**한다(9/23 개편). 실제 실행은 MainWindow 가 워커로 한다.

예전에는 체크박스 넷(backfill · refresh · rebuild · recover)이 한 줄에 잘린 채 붙어 있어 언제 무엇을 켜야 할지 알 수 없었다.
이제는 상황 카드 다섯 장으로 고른다 — 제목 · '이럴 때' · '무엇을 하나' · 걸리는 시간 · 추천/대상 수:

  평소 수집(처음이면 '처음 수집')  ← 거의 늘 이것
  ─ 결과가 이상하거나 비어 있을 때만 ─
  빠진 날 채우기(backfill) · 최근 며칠 다시 읽기(refresh) · 시간 미확인 복구(recover) · 전체 다시 만들기(rebuild)
  · 기간 다시 읽기(range, 10/5 — 전체 다시 만들기 밑, 날짜 두 칸)

카드는 한 번에 하나만 고르고, 수집이 끝나면 '평소 수집' 으로 돌아간다(문제 해결용 수집이 다음에도 켜져 있지 않게).
결과 화면은 이 프로그램 안에 없다 — 수집이 만든 HTML 을 사용자가 더블클릭해서 본다('결과 화면 열기' 는 편의 버튼)."""
from __future__ import annotations

import time
from typing import Dict, Optional

from PyQt6.QtCore import QDate, QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QDateEdit, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget)

from ... import collect, i18n, nas_guard
from ...utils import paths, prefs, results
from ...workers import wafer_logs
from ..widgets.buttons import make_button

MAX_LOG_LINES = 1000
K = i18n.KO

#: 상황 카드의 열쇠 → 워커 인자(full, backfill, recover). refresh 는 prefs.refresh_window_days 로 간다(D60).
MODES = ("normal", "rdl", "backfill", "refresh", "recover", "rebuild", "range")
_ARGS = {"normal": (False, False, False), "backfill": (False, True, False), "refresh": (False, False, False),
         "recover": (False, False, True), "rebuild": (True, False, False), "range": (False, False, False),
         "rdl": (False, False, False)}   # rdl 은 MainWindow 가 mode() 로 rdl_patch 를 넘긴다   # range 는 refresh_range() 로


def _repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()


def _label(text: str, role: str, parent: QWidget, wrap: bool = False) -> QLabel:
    lb = QLabel(text, parent)
    lb.setProperty("role", role)
    lb.setWordWrap(wrap)
    return lb


def _card(parent: QWidget, title: str = "") -> tuple:
    f = QFrame(parent)
    f.setProperty("role", "card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(20, 16, 20, 16)
    lay.setSpacing(10)
    if title:
        lay.addWidget(_label(title, "cardTitle", f))
    return f, lay


def _days_text(days) -> str:
    """보관 기간 문구 — 0 은 기한 없음(10/5)."""
    return K.RETENTION_DAYS_FMT.format(days=int(days)) if int(days or 0) > 0 else K.RETENTION_FOREVER_TEXT


class _PlanWorker(QThread):
    """계획 조회를 UI 스레드 밖에서 — 캐시 파일(수십 MB)을 읽는 동안 창이 멈추지 않게. 결과는 토큰으로 가려 늦게 온 옛 조회는 버린다.
    고른 모드의 계획과, 복구 카드에 적을 '시간 미확인 Report 수'(캐시만 보고 센다)를 함께 가져온다."""
    result = pyqtSignal(int, object, object)   # token, RunPlan | None, 복구 대상 수 | None

    def __init__(self, token: int, cfg: dict, full: bool, backfill: bool, recover: bool, parent=None):
        super().__init__(parent)
        self._args = (token, cfg, full, backfill, recover)

    def run(self) -> None:  # noqa: D401
        token, cfg, full, backfill, recover = self._args
        try:
            plan = collect.plan_run(cfg, full=full, backfill=backfill, recover=recover)
            n_rec = collect.plan_run(cfg, recover=True).recover_reports
        except Exception:  # noqa: BLE001
            plan, n_rec = None, None
        self.result.emit(token, plan, n_rec)


class _DaysWorker(QThread):
    """캐시에 있는 데이터의 기간(첫날 · 끝날 · 행 수)을 UI 스레드 밖에서 센다 — 'HTML 만 다시 만들기' 의 기본 기간."""
    result = pyqtSignal(object)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg

    def run(self) -> None:  # noqa: D401
        try:
            self.result.emit(collect.cached_days(self._cfg))
        except Exception:  # noqa: BLE001
            self.result.emit(None)


class _HtmlOnlyWorker(QThread):
    """수집 없이 가진 데이터로 HTML 을 만든다(NAS 를 읽지 않음, 10/5) — 끝나면 (경로 | None, 오류 문구)."""
    log = pyqtSignal(str)
    done = pyqtSignal(object, str)

    def __init__(self, cfg: dict, day_from: str, day_to: str, parent=None):
        super().__init__(parent)
        self._args = (cfg, day_from, day_to)

    def run(self) -> None:  # noqa: D401
        cfg, a, b = self._args
        try:
            path = collect.html_from_cache(cfg, a, b, log=self.log.emit)
            self.done.emit(path, "")
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, f"{type(ex).__name__}: {ex}")


class ModeCard(QFrame):
    """상황 카드 하나 — 누르면(또는 Space/Enter) 고른다. 고른 카드는 파란 테두리와 채운 점."""
    picked = pyqtSignal(str)

    def __init__(self, key: str, title: str, when: str, what: str, parent: QWidget):
        super().__init__(parent)
        self.key = key
        self.setProperty("role", "mode")
        self.setProperty("selected", "false")
        self.setProperty("enabled", "true")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(title)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 14)
        lay.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(9)
        self._dot = _label("", "dot", self)
        self._dot.setFixedSize(14, 14)
        self._title = _label(title, "modeTitle", self)
        top.addWidget(self._dot)
        top.addWidget(self._title)
        top.addStretch(1)
        self._badges = QHBoxLayout()
        self._badges.setSpacing(5)
        top.addLayout(self._badges)
        lay.addLayout(top)
        self._when = _label(when, "modeWhen", self, wrap=True)
        self._what = _label(what, "modeWhat", self, wrap=True)
        lay.addWidget(self._when)
        lay.addWidget(self._what)
        self.extra = QHBoxLayout()
        self.extra.setSpacing(6)
        lay.addLayout(self.extra)
        lay.addStretch(1)                               # 격자에서 카드 높이가 맞춰질 때 글자는 위에 모여 있게
        for lb in (self._when, self._what):
            lb.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._enabled = True

    def set_texts(self, title: Optional[str] = None, when: Optional[str] = None, what: Optional[str] = None) -> None:
        if title is not None:
            self._title.setText(title)
            self.setAccessibleName(title)
        if when is not None:
            self._when.setText(when)
        if what is not None:
            self._what.setText(what)

    def title(self) -> str:
        return self._title.text()

    def set_badges(self, items) -> None:
        """[(글자, 종류)] — 종류: rec(추천 · 초록) · warn(주의 · 노랑) · slow(회색) · "" (파랑)."""
        while self._badges.count():
            w = self._badges.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for text, kind in items:
            b = _label(text, "badge", self)
            b.setProperty("kind", kind)
            b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._badges.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_selected(self, on: bool) -> None:
        self.setProperty("selected", "true" if on else "false")
        self._dot.setProperty("on", "true" if on else "false")
        _repolish(self)
        _repolish(self._dot)

    def set_available(self, on: bool, why: str = "") -> None:
        self._enabled = on
        self.setProperty("enabled", "true" if on else "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor if on else Qt.CursorShape.ArrowCursor)
        self.setToolTip("" if on else why)
        for i in range(self.extra.count()):
            w = self.extra.itemAt(i).widget()
            if w is not None:
                w.setEnabled(on)
        _repolish(self)
        for c in self.findChildren(QLabel):
            _repolish(c)

    def available(self) -> bool:
        return self._enabled

    def mouseReleaseEvent(self, ev):  # noqa: N802
        if ev.button() == Qt.MouseButton.LeftButton and self.rect().contains(ev.pos()) and self._enabled:
            self.picked.emit(self.key)
        super().mouseReleaseEvent(ev)

    def keyPressEvent(self, ev):  # noqa: N802
        if ev.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter) and self._enabled:
            self.picked.emit(self.key)
            return
        super().keyPressEvent(ev)


class CollectPage(QWidget):
    collect_requested = pyqtSignal(bool, bool, bool)   # full, backfill, recover
    stop_requested = pyqtSignal()
    error = pyqtSignal(str, str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._running = False
        self._plan_token = 0
        self._plan_worker: Optional[_PlanWorker] = None
        self._mode = "normal"
        self._first_run = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget(scroll)
        scroll.setWidget(body)
        outer.addWidget(scroll)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 6, 0)
        lay.setSpacing(14)
        p = prefs.load()

        # 머리
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(_label(K.COLLECT_PAGE_TITLE, "h1", body))
        head.addWidget(_label(K.COLLECT_PAGE_SUB, "sub", body, wrap=True))
        lay.addLayout(head)

        # 상황 카드 + 실행
        pick, pl = _card(body, K.COLLECT_PICK_TITLE)
        self._cards: Dict[str, ModeCard] = {}
        self._cards["normal"] = ModeCard("normal", K.MODE_NORMAL_TITLE, K.MODE_NORMAL_WHEN, K.MODE_NORMAL_WHAT, pick)
        pl.addWidget(self._cards["normal"])
        # 10/5: 평소 수집 옆의 두 번째 버튼 — 업데이트 전에 읽은 RDL Report 의 멀티/단일 판정을 채운다(RDL 이 있는 장비만)
        self._cards["rdl"] = ModeCard("rdl", K.MODE_RDL_TITLE, K.MODE_RDL_WHEN, K.MODE_RDL_WHAT, pick)
        pl.addWidget(self._cards["rdl"])
        pl.addSpacing(2)
        pl.addWidget(_label(K.COLLECT_TROUBLE_EYEBROW, "eyebrow", pick))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._cards["backfill"] = ModeCard("backfill", K.MODE_BACKFILL_TITLE, K.MODE_BACKFILL_WHEN, "", pick)
        self._cards["refresh"] = ModeCard("refresh", K.MODE_REFRESH_TITLE, K.MODE_REFRESH_WHEN, K.MODE_REFRESH_WHAT, pick)
        self._cards["recover"] = ModeCard("recover", K.MODE_RECOVER_TITLE, K.MODE_RECOVER_WHEN, K.MODE_RECOVER_WHAT, pick)
        self._cards["rebuild"] = ModeCard("rebuild", K.MODE_REBUILD_TITLE, K.MODE_REBUILD_WHEN, "", pick)
        for i, key in enumerate(("backfill", "refresh", "recover", "rebuild")):
            grid.addWidget(self._cards[key], i // 2, i % 2)
        # 10/5: '전체 다시 만들기' 밑에 — 고른 기간만 다시 읽기(그 기간에 끝난 Report · 시작한 KLA Wafer, 기간 밖 이력은 그대로)
        self._cards["range"] = ModeCard("range", K.MODE_RANGE_TITLE, K.MODE_RANGE_WHEN, K.MODE_RANGE_WHAT, pick)
        grid.addWidget(self._cards["range"], 2, 0, 1, 2)
        today = QDate.currentDate()
        self._r_from, self._r_to = QDateEdit(self._cards["range"]), QDateEdit(self._cards["range"])
        for w, d in ((self._r_from, today.addDays(-6)), (self._r_to, today)):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setMaximumDate(today)
            w.setDate(d)
            w.setMinimumWidth(130)
        rx = self._cards["range"].extra
        rx.addWidget(_label(K.HTML_ONLY_FROM, "muted", self._cards["range"]))
        rx.addWidget(self._r_from)
        rx.addWidget(_label(K.HTML_ONLY_TO, "muted", self._cards["range"]))
        rx.addWidget(self._r_to)
        rx.addStretch(1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        pl.addLayout(grid)
        # '최근 며칠' 의 며칠 — 카드 안에서 바로 고른다(예전엔 '처음 수집 기간' 30일을 그대로 써서 무거웠다)
        self._refresh_days = QSpinBox(self._cards["refresh"])
        self._refresh_days.setRange(1, 90)
        self._refresh_days.setValue(max(1, int(p.refresh_pick_days or 3)))
        self._refresh_days.setSuffix(K.MODE_REFRESH_DAYS_SUFFIX)
        self._refresh_days.setFixedWidth(84)
        rc = self._cards["refresh"].extra
        rc.addWidget(_label(K.MODE_REFRESH_DAYS_PREFIX, "muted", self._cards["refresh"]))
        rc.addWidget(self._refresh_days)
        rc.addStretch(1)
        self._cards["normal"].set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_FAST, "slow")])
        self._cards["backfill"].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])
        self._cards["refresh"].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])
        self._cards["recover"].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])
        self._cards["rebuild"].set_badges([(K.MODE_BADGE_SLOW, "warn")])
        self._cards["range"].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])
        self._cards["rdl"].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])

        rule = QFrame(pick)
        rule.setProperty("role", "rule")
        pl.addSpacing(4)
        pl.addWidget(rule)
        act = QHBoxLayout()
        act.setSpacing(10)
        self._plan = _label("", "help", pick, wrap=True)
        self._plan.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._status = _label(K.COLLECT_IDLE, "muted", pick)
        self._b_stop = make_button(K.BTN_STOP, "default", pick)
        self._b_stop.hide()
        self._b_run = make_button(K.BTN_COLLECT_NOW, "primary", pick)
        self._b_run.setProperty("size", "lg")
        act.addWidget(self._plan, 1)
        act.addWidget(self._status)
        act.addWidget(self._b_stop)
        act.addWidget(self._b_run)
        pl.addLayout(act)
        lay.addWidget(pick)

        # 결과 화면(HTML) — 더블클릭이 기본, 버튼은 편의
        rcard, rl = _card(body, K.COLLECT_RESULT_TITLE)
        self._result = _label("", "mono", rcard, wrap=True)
        self._result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        hint = _label(K.COLLECT_RESULT_HINT, "help", rcard, wrap=True)
        rrow = QHBoxLayout()
        self._b_open = make_button(K.BTN_OPEN_RESULT, "primary", rcard)
        self._b_folder = make_button(K.BTN_OPEN_RESULT_FOLDER, "default", rcard)
        rrow.addWidget(self._b_open)
        rrow.addWidget(self._b_folder)
        rrow.addStretch(1)
        rl.addWidget(self._result)
        rl.addWidget(hint)
        rl.addLayout(rrow)
        lay.addWidget(rcard)

        # HTML 만 다시 만들기(10/5) — 수집 없이 가진 데이터로, 기간을 골라서
        hcard, hl = _card(body, K.HTML_ONLY_TITLE)
        hl.addWidget(_label(K.HTML_ONLY_WHEN, "help", hcard, wrap=True))
        self._have = _label(K.COLLECT_PLAN_LOADING, "muted", hcard, wrap=True)
        hl.addWidget(self._have)
        hrow = QHBoxLayout()
        self._d_from = QDateEdit(hcard)
        self._d_to = QDateEdit(hcard)
        for w in (self._d_from, self._d_to):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setDate(QDate.currentDate())
        self._b_html = make_button(K.HTML_ONLY_RUN, "default", hcard)
        self._b_html.setEnabled(False)
        # 10/5: 수집 뒤 HTML 은 기본 1달 — 가진 데이터 전부는 이 버튼 한 번으로(사용자 요청)
        self._b_all = make_button(K.HTML_ONLY_ALL, "primary", hcard)
        self._b_all.setEnabled(False)
        self._span: Optional[tuple] = None
        hrow.addWidget(QLabel(K.HTML_ONLY_FROM, hcard))
        hrow.addWidget(self._d_from)
        hrow.addWidget(QLabel(K.HTML_ONLY_TO, hcard))
        hrow.addWidget(self._d_to)
        hrow.addWidget(self._b_html)
        hrow.addStretch(1)
        hl.addLayout(hrow)
        arow = QHBoxLayout()
        arow.addWidget(self._b_all)
        arow.addWidget(_label(K.HTML_ONLY_ALL_HELP, "muted", hcard, wrap=True), 1)
        hl.addLayout(arow)
        lay.addWidget(hcard)
        self._days_worker: Optional[_DaysWorker] = None
        self._html_worker: Optional[_HtmlOnlyWorker] = None

        # Wafer 로그 30일 전체 수집(10/9 1차 → 10/10 2차 → 10/10 30일 전체로 교체) — 개발자 조사용. 가동률 수집과 따로 돌고, 둘이 동시에 NAS 를 읽지 않게 서로 막는다.
        wcard, wl = _card(body, K.WAFER_LOGS_TITLE)
        wl.addWidget(_label(K.WAFER_LOGS_WHEN, "help", wcard, wrap=True))
        wrow = QHBoxLayout()
        self._wl_out = QLineEdit(wafer_logs.default_out_dir(), wcard)
        self._wl_out.setProperty("role", "mono")
        self._b_wl_browse = make_button(K.BTN_BROWSE, parent=wcard)
        wrow.addWidget(QLabel(K.WAFER_LOGS_OUT, wcard))
        wrow.addWidget(self._wl_out, 1)
        wrow.addWidget(self._b_wl_browse)
        wl.addLayout(wrow)
        wact = QHBoxLayout()
        self._wl_status = _label("", "muted", wcard, wrap=True)
        self._b_wl_run = make_button(K.WAFER_LOGS_RUN, "default", wcard)
        self._b_wl_stop = make_button(K.WAFER_LOGS_STOP, "default", wcard)
        self._b_wl_stop.hide()
        self._b_wl_open = make_button(K.WAFER_LOGS_OPEN, "default", wcard)
        wact.addWidget(self._b_wl_run)
        wact.addWidget(self._b_wl_stop)
        wact.addWidget(self._b_wl_open)
        wact.addWidget(self._wl_status, 1)
        wl.addLayout(wact)
        lay.addWidget(wcard)
        self._wl_worker: Optional[wafer_logs.WaferLogsWorker] = None

        # 저장 위치
        scard, sl = _card(body, K.COLLECT_SAVE_TITLE)
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        self._out = QLineEdit(p.output_dir, scard)
        self._out.setProperty("role", "mono")
        self._out.setPlaceholderText(str(paths.data_root()))
        self._b_out = make_button(K.BTN_BROWSE, parent=scard)
        self._csv = QCheckBox(K.COLLECT_WRITE_CSV, scard)
        self._csv.setChecked(bool(p.write_csv))
        g.addWidget(QLabel(K.COLLECT_OUTPUT_DIR, scard), 0, 0)
        g.addWidget(self._out, 0, 1)
        g.addWidget(self._b_out, 0, 2)
        g.addWidget(_label(K.COLLECT_OUTPUT_DEFAULT_HINT, "muted", scard, wrap=True), 1, 1, 1, 2)
        g.addWidget(self._csv, 2, 1, 1, 2)
        g.setColumnStretch(1, 1)
        sl.addLayout(g)
        lay.addWidget(scard)

        # 로그
        lay.addWidget(_label(K.COLLECT_LOG_TITLE, "eyebrow", body))
        self._log = QPlainTextEdit(body)
        self._log.setProperty("role", "console")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(MAX_LOG_LINES)
        self._log.setMinimumHeight(180)
        lay.addWidget(self._log, 1)

        for c in self._cards.values():
            c.picked.connect(self._pick)
        self._b_open.clicked.connect(self._open_result)
        self._b_folder.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(paths.output_dir(prefs.load().output_dir)))))
        self._b_run.clicked.connect(self._on_run)
        self._b_html.clicked.connect(self._on_html_only)
        self._b_all.clicked.connect(self._on_html_all)
        self._b_stop.clicked.connect(self.stop_requested.emit)
        self._b_out.clicked.connect(self._browse_out)
        self._refresh_days.valueChanged.connect(self._on_refresh_days)
        for w in (self._r_from, self._r_to):
            w.dateChanged.connect(lambda _d: self._mode == "range" and self.refresh_plan())
        self._csv.toggled.connect(lambda on: prefs.patch(write_csv=bool(on)))
        self._out.editingFinished.connect(self._apply_out)
        self._b_wl_run.clicked.connect(self._on_wafer_logs)
        self._b_wl_stop.clicked.connect(self._stop_wafer_logs)
        self._b_wl_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._wl_out.text().strip())))
        self._b_wl_browse.clicked.connect(self._browse_wl_out)
        self._pick("normal")
        self.refresh_result()

    # ── 상황 고르기 ──
    def mode(self) -> str:
        return self._mode

    def _pick(self, key: str) -> None:
        if key not in self._cards or (not self._cards[key].available() and key != "normal"):
            return
        self._mode = key
        for k, c in self._cards.items():
            c.set_selected(k == key)
        self._apply_refresh_option()
        self._b_run.setText(K.MODE_RUN_FMT.format(title=self._cards[key].title()))
        self.refresh_plan()

    def _on_refresh_days(self, v: int) -> None:
        prefs.patch(refresh_pick_days=int(v))
        self._apply_refresh_option()
        if self._mode == "refresh":
            self.refresh_plan()

    def _apply_refresh_option(self) -> None:
        """'최근 며칠 다시 읽기' 를 고른 동안만 prefs.refresh_window_days = N — to_collect_cfg 가 cfg 로 넘긴다(D60). 다른 카드면 0."""
        days = int(self._refresh_days.value()) if self._mode == "refresh" else 0
        if int(prefs.load().refresh_window_days or 0) != days:
            prefs.patch(refresh_window_days=days)

    def refresh_days(self) -> int:
        return int(self._refresh_days.value()) if self._mode == "refresh" else 0

    def refresh_range(self) -> Optional[tuple]:
        """'기간 다시 읽기' 를 고른 동안만 (시작일, 끝날) — 순서가 거꾸로면 바로잡는다. 다른 카드면 None."""
        if self._mode != "range":
            return None
        a, b = self._r_from.date().toString("yyyy-MM-dd"), self._r_to.date().toString("yyyy-MM-dd")
        return tuple(sorted((a, b)))

    def options(self) -> tuple:
        return _ARGS[self._mode]

    # ── 공개 API ──
    def refresh_result(self) -> None:
        """결과 파일 경로·버튼 상태·가진 데이터 기간을 갱신한다(수집 직후·설정 변경 후)."""
        path = results.html_path()
        have = path.is_file()
        self._result.setText(str(path) if have else K.COLLECT_RESULT_NONE)
        self._b_open.setEnabled(have)
        self._b_folder.setEnabled(True)
        if self._days_worker is None:
            w = _DaysWorker(prefs.to_collect_cfg(prefs.load()), self)
            w.result.connect(self._on_days)
            w.finished.connect(lambda w=w: self._worker_done("_days_worker", w))
            self._days_worker = w
            w.start()

    def _worker_done(self, attr: str, w: QThread) -> None:
        if getattr(self, attr, None) is w:
            setattr(self, attr, None)
        w.deleteLater()

    def _on_days(self, got) -> None:
        if not got or not got[0]:
            self._have.setText(K.HTML_ONLY_NONE)
            self._b_html.setEnabled(False)
            self._b_all.setEnabled(False)
            self._span = None
            return
        first, last, n = got
        self._span = (first, last)
        self._have.setText(K.HTML_ONLY_HAVE_FMT.format(first=first, last=last, rows=n))
        lo, hi = QDate.fromString(first, "yyyy-MM-dd"), QDate.fromString(last, "yyyy-MM-dd")
        for w in (self._d_from, self._d_to):
            w.setDateRange(lo, hi)
        days = int(prefs.to_collect_cfg(prefs.load()).get("html_days") or 0)
        self._d_from.setDate(max(lo, hi.addDays(-(days - 1))) if days > 0 else lo)
        self._d_to.setDate(hi)
        self._b_html.setEnabled(not self._running)
        self._b_all.setEnabled(not self._running)

    def _on_html_all(self) -> None:
        if self._span:
            self._make_html(*self._span)

    def _on_html_only(self) -> None:
        a = self._d_from.date().toString("yyyy-MM-dd")
        b = self._d_to.date().toString("yyyy-MM-dd")
        self._make_html(*sorted((a, b)))

    def _make_html(self, a: str, b: str) -> None:
        if self._html_worker is not None:
            return
        self._b_html.setEnabled(False)
        self._b_all.setEnabled(False)
        w = _HtmlOnlyWorker(prefs.to_collect_cfg(prefs.load()), a, b, self)
        w.log.connect(self.append_log)
        w.done.connect(self._on_html_done)
        w.finished.connect(lambda w=w: self._worker_done("_html_worker", w))
        self._html_worker = w
        w.start()

    def _on_html_done(self, path, err: str) -> None:
        self._b_html.setEnabled(not self._running)
        self._b_all.setEnabled(not self._running and bool(self._span))
        if path:
            self.append_log(K.HTML_ONLY_DONE_FMT.format(path=path))
            self._status.setText(K.HTML_ONLY_DONE_FMT.format(path=path))
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:
            self.append_log(K.HTML_ONLY_FAIL_FMT.format(error=err))
            self.error.emit(K.HTML_ONLY_TITLE, K.HTML_ONLY_FAIL_FMT.format(error=err))

    def _open_result(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(results.ensure_html())))

    def refresh_plan(self) -> None:
        """계획 문구·카드 상태를 갱신한다 — 캐시 읽기는 워커 스레드에서(UI 스레드가 몇 초씩 멈추던 원인)."""
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        self._cards["backfill"].set_texts(what=K.MODE_BACKFILL_WHAT_FMT.format(days=int(p.backfill_days)))
        self._cards["rebuild"].set_texts(what=K.MODE_REBUILD_WHAT_FMT.format(days=_days_text(p.retention_days)))
        self._plan_token += 1
        token = self._plan_token
        self._plan.setText(K.COLLECT_PLAN_LOADING)
        full, backfill, recover = self.options()
        w = _PlanWorker(token, cfg, full, backfill, recover, self)
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

    def _on_plan(self, token: int, plan, n_recover) -> None:
        if token != self._plan_token:
            return                                      # 늦게 온 옛 조회
        if plan is None:
            self._plan.setText("")
            return
        self._update_cards(plan, n_recover)
        if self._mode == "rebuild":
            text = K.COLLECT_PLAN_FULL_FMT.format(days=_days_text(plan.retention_days))
        elif self._mode == "rdl":
            text = (K.COLLECT_PLAN_RDL_FMT.format(n=plan.rdl_reports, devs=plan.rdl_devices) if plan.rdl_reports
                    else K.COLLECT_PLAN_RDL_NONE)
        elif self._mode == "range":
            a, b = self.refresh_range()
            text = K.COLLECT_PLAN_RANGE_FMT.format(a=a, b=b)
        elif plan.mode == "first":
            text = K.COLLECT_PLAN_FIRST_FMT.format(days=plan.backfill_days)
        elif plan.refresh_days > 0:
            text = K.COLLECT_PLAN_REFRESH_FMT.format(days=plan.refresh_days, reread=plan.reread_reports, keep=plan.keep_reports)
        elif self._mode == "backfill":
            text = K.COLLECT_PLAN_BACKFILL_FMT.format(days=plan.backfill_days)
        elif self._mode == "recover":
            text = (K.COLLECT_PLAN_RECOVER_FMT.format(n=plan.recover_reports) if plan.recover_reports
                    else K.COLLECT_PLAN_RECOVER_NONE)
        else:
            text = K.COLLECT_PLAN_INCR_FMT.format(n=plan.known_devices)
        self._plan.setText(text)

    def _update_cards(self, plan, n_recover) -> None:
        """캐시로 아는 사실을 카드에 적는다: 처음이면 '처음 수집' 하나만, 복구 대상 수, 마지막 수집이 오래됐는지."""
        first = plan.total_reports == 0 and self._mode != "rebuild"
        if first != self._first_run:
            self._first_run = first
            for k in ("rdl", "backfill", "refresh", "recover", "rebuild", "range"):
                self._cards[k].set_available(not first, K.MODE_DISABLED_FIRST)
        n = self._cards["normal"]
        if first:
            n.set_texts(title=K.MODE_FIRST_TITLE, when=K.MODE_FIRST_WHEN, what=K.MODE_FIRST_WHAT_FMT.format(days=plan.backfill_days))
            n.set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_SLOW, "warn")])
        else:
            last = results.last_collect_time()
            days = int((time.time() - last) // 86400) if last else 0
            what = K.MODE_NORMAL_WHAT + ("\n" + K.MODE_STALE_FMT.format(days=days) if days > collect.PATTERN_MAX_DAYS else "")
            n.set_texts(title=K.MODE_NORMAL_TITLE, when=K.MODE_NORMAL_WHEN, what=what)
            n.set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_FAST, "slow")])
        if self._mode == "normal":
            self._b_run.setText(K.MODE_RUN_FMT.format(title=n.title()))
        if n_recover is not None and not first:
            self._cards["recover"].set_badges([(K.MODE_BADGE_TARGET_FMT.format(n=n_recover), "warn") if n_recover
                                               else (K.MODE_BADGE_NONE, "slow")])
        if not first:
            self._cards["rdl"].set_badges([(K.MODE_RDL_TARGET_FMT.format(n=plan.rdl_reports, devs=plan.rdl_devices), "warn")
                                           if plan.rdl_reports else (K.MODE_BADGE_NONE, "slow")])

    # ── Wafer 폴더 로그 모으기(10/9) ──
    def wafer_logs_running(self) -> bool:
        return self._wl_worker is not None

    def _on_wafer_logs(self) -> None:
        if self._wl_worker is not None:
            return
        if self._running:
            self.error.emit(K.WAFER_LOGS_TITLE, K.WAFER_LOGS_BUSY)
            return
        out = self._wl_out.text().strip() or wafer_logs.default_out_dir()
        self._wl_out.setText(out)
        w = wafer_logs.WaferLogsWorker(prefs.to_collect_cfg(prefs.load()), out, self)
        w.log.connect(self.append_log)
        w.done.connect(self._on_wafer_logs_done)
        w.finished.connect(lambda w=w: self._worker_done("_wl_worker", w))
        self._wl_worker = w
        self._set_wafer_logs_running(True)
        self._wl_status.setText(K.WAFER_LOGS_RUNNING)
        w.start()

    def _stop_wafer_logs(self) -> None:
        if self._wl_worker is not None:
            self._wl_worker.stop()
            self._b_wl_stop.setEnabled(False)
            self._wl_status.setText(K.WAFER_LOGS_STOPPING)

    def _on_wafer_logs_done(self, result, err: str) -> None:
        self._set_wafer_logs_running(False)
        if result:
            text = K.WAFER_LOGS_DONE_FMT.format(n=len(result.get("parts") or []), lots=result.get("lots", 0),
                                                path=result.get("out_dir", ""))
            self._wl_status.setText(text)
            self.append_log(text)
        else:
            self._wl_status.setText(err)
            self.append_log(err)
            if err != K.WAFER_LOGS_STOPPED:
                self.error.emit(K.WAFER_LOGS_TITLE, err)

    def _set_wafer_logs_running(self, on: bool) -> None:
        self._b_wl_run.setEnabled(not on)
        self._b_wl_stop.setVisible(on)
        self._b_wl_stop.setEnabled(on)
        self._wl_out.setEnabled(not on)
        self._b_wl_browse.setEnabled(not on)
        self._b_run.setEnabled(not on and not self._running)     # 가동률 수집과 동시에 NAS 를 읽지 않는다

    def _browse_wl_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, K.WAFER_LOGS_OUT, self._wl_out.text())
        if chosen:
            self._wl_out.setText(chosen)

    def shutdown(self, ms: int = 15_000) -> None:
        """창을 닫을 때 — 로그 모으기를 멈추고(지금까지 담은 것으로 zip 마무리) 기다린다."""
        w = self._wl_worker
        if w is None:
            return
        try:
            w.stop()
            w.wait(ms)
        except RuntimeError:
            self._wl_worker = None

    def set_running(self, running: bool) -> None:
        self._running = running
        self._b_run.setEnabled(not running and self._wl_worker is None)
        self._b_wl_run.setEnabled(not running and self._wl_worker is None)
        self._b_stop.setVisible(running)
        self._b_stop.setEnabled(running)
        for w in (*self._cards.values(), self._refresh_days, self._r_from, self._r_to, self._out, self._b_out, self._csv, self._b_html, self._b_all):
            w.setEnabled(not running)
        self._b_all.setEnabled(not running and bool(self._span))
        self._status.setText(K.COLLECT_RUNNING if running else K.COLLECT_IDLE)
        if not running:
            self._pick("normal")                         # 문제 해결용 수집은 한 번만 — 다음엔 평소 수집으로 돌아간다

    def set_status(self, text: str) -> None:
        self._status.setText(text)

    def append_log(self, line: str) -> None:
        self._log.appendPlainText(line)

    # ── 내부 ──
    def _on_run(self) -> None:
        full, backfill, recover = self.options()
        self.collect_requested.emit(full, backfill, recover)

    def _browse_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, K.COLLECT_OUTPUT_DIR, self._out.text() or str(paths.data_root()))
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
            self.error.emit(K.COLLECT_OUTPUT_ON_NAS_TITLE, K.COLLECT_OUTPUT_ON_NAS_BODY)
            return
        if value != p.output_dir:
            prefs.patch(output_dir=value)
            self.refresh_result()
