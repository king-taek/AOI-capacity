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
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ... import collect, i18n, nas_guard
from ...utils import paths, prefs, results
from ... import image_survey as image_survey_mod
from ...workers import failure_logs, image_survey, wafer_logs
from ..widgets.buttons import make_button
from ..widgets.collapsible import Collapsible
from ..widgets.inputs import NoWheelDateEdit as QDateEdit, NoWheelSpinBox as QSpinBox
from .settings_page import SettingsPage

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


class _ParamZipWorker(QThread):
    """30일 Wafer 로그 zip 으로 파라미터 이력 채우기(D89) — 이 PC 의 zip 만 읽는다. 끝나면 (통계 | None, 오류 문구)."""
    log = pyqtSignal(str)
    done = pyqtSignal(object, str)

    def __init__(self, cfg: dict, folder: str, parent=None):
        super().__init__(parent)
        self._args = (cfg, folder)

    def run(self) -> None:  # noqa: D401
        cfg, folder = self._args
        try:
            self.done.emit(collect.import_param_zips(cfg, folder, log=self.log.emit), "")
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, f"{type(ex).__name__}: {ex}")


class _ParamFillWorker(QThread):
    """파라미터 빈 구간 채우기(10/11) — 캐시에서 빈 Report 를 찾아 그 Wafer 폴더 안만 읽는다. 끝나면 (통계 | None, 오류 문구)."""
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    done = pyqtSignal(object, str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # noqa: D401
        try:
            st = collect.fill_params(self._cfg, log=self.log.emit, progress=lambda d, t, p: self.progress.emit(d, t),
                                     should_stop=lambda: self._stop)
            self.done.emit(st, "")
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, f"{type(ex).__name__}: {ex}")


def eta_text(sec, rough: bool = False) -> str:
    """초 → '약 12분' · '1분 안쪽' · '약 1시간 20분'. 실측이 없으면 앞에 '대략'."""
    sec = max(0, int(sec or 0))
    m = (sec + 30) // 60
    t = K.ETA_UNDER_MIN if sec < 60 else K.ETA_MIN_FMT.format(m=m) if m < 60 else K.ETA_HOUR_FMT.format(h=m // 60, m=m % 60)
    return K.ETA_ROUGH_FMT.format(t=t) if rough else t


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

        # 맨 위 조사용 카드 줄(10/22 사용자 요청) — Review 이미지 순서 조사 · No image 수집 같은 임시 조사 버튼. 이슈가 풀리면 카드와 이 줄을 지운다
        self._top_cards = QVBoxLayout()
        self._top_cards.setSpacing(14)
        lay.addLayout(self._top_cards)

        # 상황 카드 + 실행
        pick, pl = _card(body, K.COLLECT_PICK_TITLE)
        self._cards: Dict[str, ModeCard] = {}
        self._cards["normal"] = ModeCard("normal", K.MODE_NORMAL_TITLE, K.MODE_NORMAL_WHEN, K.MODE_NORMAL_WHAT, pick)
        pl.addWidget(self._cards["normal"])
        # 10/11: 매일 쓰는 건 '평소 수집' 하나 — 나머지 복구 카드는 접이식 구역 안으로(사용자: 버튼이 너무 중구난방)
        trouble = QWidget(pick)
        tl = QVBoxLayout(trouble)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(10)
        # 10/5: 업데이트 전에 읽은 RDL Report 의 멀티/단일 판정을 채운다(RDL 이 있는 장비만)
        self._cards["rdl"] = ModeCard("rdl", K.MODE_RDL_TITLE, K.MODE_RDL_WHEN, K.MODE_RDL_WHAT, pick)
        tl.addWidget(self._cards["rdl"])
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
        # 10/22: '빠진 날 채우기' 의 시작일 — 이 날부터 오늘까지 아직 읽지 않은 것만 읽는다(기본 = 오늘 − backfill_days)
        self._b_from = QDateEdit(self._cards["backfill"])
        self._b_from.setCalendarPopup(True)
        self._b_from.setDisplayFormat("yyyy-MM-dd")
        self._b_from.setMaximumDate(today)
        self._b_from.setDate(today.addDays(-int(prefs.load().backfill_days or 30)))
        self._b_from.setMinimumWidth(130)
        bx = self._cards["backfill"].extra
        bx.addWidget(_label(K.BACKFILL_FROM, "muted", self._cards["backfill"]))
        bx.addWidget(self._b_from)
        bx.addStretch(1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        tl.addLayout(grid)
        self._trouble = Collapsible(K.COLLECT_SEC_TROUBLE, trouble, pick)
        pl.addWidget(self._trouble)
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
        self._resume = _label("", "help", pick, wrap=True)      # 멈춘 수집이 있을 때만 — 계획 줄과 따로 한 줄(10/11)
        self._resume.setStyleSheet("font-weight:600;")
        self._resume.hide()
        pl.addWidget(self._resume)
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
        self._sec_html = Collapsible(K.COLLECT_SEC_HTML, hcard, body)
        lay.addWidget(self._sec_html)
        self._days_worker: Optional[_DaysWorker] = None
        self._html_worker: Optional[_HtmlOnlyWorker] = None

        # 파라미터 이력 채우기(D89, 10/11 사용자 Q9) — 30일 Wafer 로그 zip 폴더를 골라 한 번. 캐시를 고치므로 수집과 동시에 돌지 않는다.
        pcard, pl = _card(body, K.PARAM_ZIP_TITLE)
        pl.addWidget(_label(K.PARAM_ZIP_WHEN, "help", pcard, wrap=True))
        # 빈 구간 채우기(10/11) — 수집된 기간 중 파라미터가 비어 있는 곳을 NAS 에서 바로. 한 줄 요약 + 예상 시간.
        self._pf_sum = _label("", "mono", pcard, wrap=True)
        self._pf_help = _label("", "muted", pcard, wrap=True)
        self._pf_status = _label("", "muted", pcard, wrap=True)
        self._b_pfill = make_button(K.PARAMS_FILL_RUN, "primary", pcard)
        self._b_pfill.setEnabled(False)
        self._b_pfill.clicked.connect(self._on_param_fill)
        pfrow = QHBoxLayout()
        pfrow.addWidget(self._b_pfill)
        pfrow.addWidget(self._pf_status, 1)
        pl.addWidget(self._pf_sum)
        pl.addWidget(self._pf_help)
        pl.addLayout(pfrow)
        self._pf_n = 0
        self._pf_worker: Optional[_ParamFillWorker] = None
        self._pf_t0 = 0.0
        prow = QHBoxLayout()
        self._b_pzip = make_button(K.PARAM_ZIP_RUN, "default", pcard)
        self._b_pzip.clicked.connect(self._on_param_zip)
        prow.addWidget(self._b_pzip)
        prow.addStretch(1)
        pl.addLayout(prow)
        dev = QWidget(body)
        dl = QVBoxLayout(dev)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(12)
        dl.addWidget(pcard)
        self._pz_worker: Optional[_ParamZipWorker] = None

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
        dl.addWidget(wcard)

        # 실패 로그 수집(10/20) — 수집이 안 된 장비 · 읽지 못한 파일의 원인 · 로그 · 파일 내용을 지난 N일치로 모아 zip 한 장(NAS 는 읽기만)
        fcard, fl = _card(body, K.FAIL_LOGS_TITLE)
        fl.addWidget(_label(K.FAIL_LOGS_WHEN, "help", fcard, wrap=True))
        frow = QHBoxLayout()
        self._fl_days = QSpinBox(fcard)
        self._fl_days.setRange(1, 90)
        self._fl_days.setValue(max(1, min(90, int(p.fail_log_days or 3))))
        self._fl_days.setSuffix(K.FAIL_LOGS_DAYS_SUFFIX)
        self._fl_days.setFixedWidth(84)
        frow.addWidget(_label(K.FAIL_LOGS_DAYS_PREFIX, "muted", fcard))
        frow.addWidget(self._fl_days)
        frow.addWidget(_label(K.FAIL_LOGS_DAYS_HINT, "muted", fcard))
        frow.addStretch(1)
        fl.addLayout(frow)
        frow2 = QHBoxLayout()
        self._fl_out = QLineEdit(str(paths.data_root() / "fail_logs"), fcard)
        self._fl_out.setProperty("role", "mono")
        self._b_fl_browse = make_button(K.BTN_BROWSE, parent=fcard)
        frow2.addWidget(QLabel(K.WAFER_LOGS_OUT, fcard))
        frow2.addWidget(self._fl_out, 1)
        frow2.addWidget(self._b_fl_browse)
        fl.addLayout(frow2)
        fact = QHBoxLayout()
        self._fl_status = _label("", "muted", fcard, wrap=True)
        self._b_fl_run = make_button(K.FAIL_LOGS_RUN, "primary", fcard)
        self._b_fl_open = make_button(K.FAIL_LOGS_OPEN, "default", fcard)
        fact.addWidget(self._b_fl_run)
        fact.addWidget(self._b_fl_open)
        fact.addWidget(self._fl_status, 1)
        fl.addLayout(fact)
        dl.addWidget(fcard)
        self._fl_worker: Optional[QThread] = None        # 실패 로그 · Review 이미지 조사가 같은 자리를 쓴다(둘 다 NAS 읽기라 동시에 돌지 않음)

        # Review 이미지 순서 조사(10/22) — Color image 보다 Scan image 가 먼저 나오는 현상 조사용 표본 수집(NAS 는 읽기만)
        icard, il = _card(body, K.IMG_SURVEY_TITLE)
        il.addWidget(_label(K.IMG_SURVEY_WHEN, "help", icard, wrap=True))
        irow = QHBoxLayout()
        self._is_days = QSpinBox(icard)
        self._is_days.setRange(1, 90)
        self._is_days.setValue(max(1, min(90, int(p.image_survey_days or 7))))
        self._is_days.setSuffix(K.FAIL_LOGS_DAYS_SUFFIX)
        self._is_days.setFixedWidth(84)
        irow.addWidget(_label(K.FAIL_LOGS_DAYS_PREFIX, "muted", icard))
        irow.addWidget(self._is_days)
        irow.addStretch(1)
        il.addLayout(irow)
        trow = QHBoxLayout()
        self._is_terms = QLineEdit(image_survey_mod.DEFAULT_TERMS_TEXT, icard)
        self._is_terms.setPlaceholderText(K.IMG_SURVEY_TERMS_HINT)
        trow.addWidget(QLabel(K.IMG_SURVEY_TERMS_LABEL, icard))
        trow.addWidget(self._is_terms, 1)
        il.addLayout(trow)
        iact = QHBoxLayout()
        self._is_status = _label("", "muted", icard, wrap=True)
        self._b_is_run = make_button(K.IMG_SURVEY_RUN, "primary", icard)
        iact.addWidget(self._b_is_run)
        iact.addWidget(self._is_status, 1)
        il.addLayout(iact)
        self._top_cards.addWidget(icard)
        self._sec_dev = Collapsible(K.COLLECT_SEC_DEV, dev, body)
        lay.addWidget(self._sec_dev)
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
        sec = QWidget(body)
        sv = QVBoxLayout(sec)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(12)
        sv.addWidget(scard)
        self.settings_page = SettingsPage(sec)           # 10/11: 설정 탭을 없애고 수집 탭 맨 아래로
        sv.addWidget(self.settings_page)
        self._sec_settings = Collapsible(K.COLLECT_SEC_SETTINGS, sec, body)
        lay.addWidget(self._sec_settings)

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
        self._b_from.dateChanged.connect(lambda _d: self._mode == "backfill" and self.refresh_plan())
        self._csv.toggled.connect(lambda on: prefs.patch(write_csv=bool(on)))
        self._out.editingFinished.connect(self._apply_out)
        self._b_wl_run.clicked.connect(self._on_wafer_logs)
        self._b_wl_stop.clicked.connect(self._stop_wafer_logs)
        self._b_wl_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._wl_out.text().strip())))
        self._b_wl_browse.clicked.connect(self._browse_wl_out)
        self._b_fl_run.clicked.connect(self._on_fail_logs)
        self._b_fl_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._fl_out.text().strip())))
        self._b_fl_browse.clicked.connect(self._browse_fl_out)
        self._b_is_run.clicked.connect(self._on_image_survey)
        self._is_days.valueChanged.connect(lambda v: prefs.patch(image_survey_days=int(v)))
        self._fl_days.valueChanged.connect(lambda v: prefs.patch(fail_log_days=int(v)))
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

    def backfill_days(self) -> Optional[int]:
        """'빠진 날 채우기' 를 고른 동안만 시작일부터 오늘까지의 일수(1~3650). 다른 카드면 None."""
        if self._mode != "backfill":
            return None
        return max(1, min(3650, self._b_from.date().daysTo(QDate.currentDate()) + 1))

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

    def _on_param_fill(self) -> None:
        if self._pf_worker is not None:                       # 실행 중에 다시 누르면 멈춤
            self._pf_worker.stop()
            self._b_pfill.setEnabled(False)
            return
        if self._pz_worker is not None or self._running or self._wl_worker is not None or not self._pf_n:
            return
        w = _ParamFillWorker(prefs.to_collect_cfg(prefs.load()), self)
        w.log.connect(self.append_log)
        w.progress.connect(self._on_param_fill_progress)
        w.done.connect(self._on_param_fill_done)
        w.finished.connect(lambda w=w: self._worker_done("_pf_worker", w))
        self._pf_worker = w
        self._pf_t0 = time.monotonic()
        self._b_pfill.setText(K.BTN_STOP)
        self._b_pzip.setEnabled(False)
        self._b_run.setEnabled(False)
        self.append_log(K.PARAMS_FILL_START_FMT.format(n=self._pf_n))
        w.start()

    def _on_param_fill_progress(self, done: int, total: int) -> None:
        el = time.monotonic() - self._pf_t0
        if total <= 0:
            return
        left = el * (total - done) / done if done >= 3 and el >= 5 else None
        self._pf_status.setText(K.PARAMS_FILL_PROGRESS_FMT.format(done=done, total=total, t=eta_text(left)) if left is not None
                                else K.PARAMS_FILL_PROGRESS_FMT.format(done=done, total=total, t="…"))

    def _on_param_fill_done(self, st, err: str) -> None:
        self._b_pfill.setText(K.PARAMS_FILL_RUN)
        self._b_pzip.setEnabled(not self._running)
        self._b_run.setEnabled(not self._running and self._wl_worker is None)
        if st is not None:
            msg = (K.PARAMS_FILL_STOPPED_FMT if st.get("stopped") else K.PARAMS_FILL_DONE_FMT).format(added=st.get("added", 0), empty=st.get("empty", 0))
            self.append_log(msg)
            self._status.setText(msg)
            self._pf_status.setText(msg)
        else:
            self.append_log(K.PARAMS_FILL_FAIL_FMT.format(error=err))
            self.error.emit(K.PARAM_ZIP_TITLE, K.PARAMS_FILL_FAIL_FMT.format(error=err))
        self.refresh_plan()

    def _on_param_zip(self) -> None:
        if self._pz_worker is not None or self._running or self._wl_worker is not None or self._pf_worker is not None:
            return
        folder = QFileDialog.getExistingDirectory(self, K.PARAM_ZIP_PICK, str(paths.data_root()))
        if not folder:
            return
        self._b_pzip.setEnabled(False)
        self._b_run.setEnabled(False)
        w = _ParamZipWorker(prefs.to_collect_cfg(prefs.load()), folder, self)
        w.log.connect(self.append_log)
        w.done.connect(self._on_param_zip_done)
        w.finished.connect(lambda w=w: self._worker_done("_pz_worker", w))
        self._pz_worker = w
        self.append_log(K.PARAM_ZIP_START_FMT.format(folder=folder))
        w.start()

    def _on_param_zip_done(self, st, err: str) -> None:
        self._b_pzip.setEnabled(not self._running)
        self._b_run.setEnabled(not self._running and self._wl_worker is None)
        if st is not None:
            msg = K.PARAM_ZIP_DONE_FMT.format(added=st.get("added", 0), lots=st.get("lots", 0), known=st.get("skipped_known", 0))
            self.append_log(msg)
            self._status.setText(msg)
        else:
            self.append_log(K.PARAM_ZIP_FAIL_FMT.format(error=err))
            self.error.emit(K.PARAM_ZIP_TITLE, K.PARAM_ZIP_FAIL_FMT.format(error=err))

    def _open_result(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(results.ensure_html())))

    def refresh_plan(self) -> None:
        """계획 문구·카드 상태를 갱신한다 — 캐시 읽기는 워커 스레드에서(UI 스레드가 몇 초씩 멈추던 원인)."""
        p = prefs.load()
        cfg = prefs.to_collect_cfg(p)
        bdays = self.backfill_days()
        if bdays:
            cfg["backfill_days"] = bdays
        self._cards["backfill"].set_texts(what=K.MODE_BACKFILL_WHAT_FMT.format(days=bdays or int(p.backfill_days)))
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
            self._resume.hide()
            return
        self._update_cards(plan, n_recover)
        self._update_param_fill(plan)
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
        note = {"rebuild": K.COLLECT_PLAN_RESUME_REBUILD, "refresh": K.COLLECT_PLAN_RESUME_REFRESH}.get(getattr(plan, "resumable", ""), "")
        self._resume.setText(note)
        self._resume.setVisible(bool(note))
        self._plan.setText(text)

    def _update_param_fill(self, plan) -> None:
        """파라미터 카드 한 줄 요약 · 예상 시간 · 버튼 — 캐시만 보고 쓴다(NAS 접근 없음)."""
        self._pf_n = plan.params_missing
        busy = self._pf_worker is not None
        if not plan.total_reports:
            self._pf_sum.setText(K.PARAMS_FILL_NO_CACHE)
            self._pf_help.setText("")
        elif not plan.params_missing:
            self._pf_sum.setText(K.PARAMS_FILL_NONE_FMT.format(a=plan.span_from, b=plan.span_to, total=plan.total_reports))
            self._pf_help.setText("")
        else:
            sec, rough = (plan.etas or {}).get("params", (None, True))
            self._pf_sum.setText(K.PARAMS_FILL_SUMMARY_FMT.format(a=plan.span_from, b=plan.span_to, total=plan.total_reports, missing=plan.params_missing,
                                                                 devs=plan.params_devices, fa=plan.params_from, fb=plan.params_to))
            self._pf_help.setText(K.PARAMS_FILL_HELP_FMT.format(n=plan.params_missing, t=eta_text(sec, rough)))
            self._pf_help.setToolTip(K.ETA_BASIS_TIP)
        if not busy:
            self._b_pfill.setEnabled(bool(plan.params_missing) and not self._running and self._pz_worker is None and self._wl_worker is None)

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
        et = plan.etas or {}

        def eta(mode):
            sec, rough = et.get(mode, (None, True))
            return None if sec is None else eta_text(sec, rough)

        if not first and eta("incremental"):
            n.set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_USUAL_ETA_FMT.format(t=eta("incremental")), "slow")])
        if not first:
            for m, name in (("backfill", "backfill"), ("range", "range")):
                if eta(m):
                    self._cards[name].set_badges([(K.MODE_BADGE_USUAL_ETA_FMT.format(t=eta(m)), "slow")])
            self._cards["refresh"].set_badges([(K.MODE_BADGE_TARGET_ETA_FMT.format(n=plan.reread_reports, t=eta("refresh")), "slow")]
                                              if plan.reread_reports else [(K.MODE_BADGE_MEDIUM, "slow")])
            self._cards["rebuild"].set_badges([(K.MODE_BADGE_ETA_FMT.format(t=eta("rebuild")), "warn")])
        if n_recover is not None and not first:
            self._cards["recover"].set_badges([(K.MODE_BADGE_TARGET_ETA_FMT.format(n=n_recover, t=eta("recover")), "warn") if n_recover
                                               else (K.MODE_BADGE_NONE, "slow")])
        if not first:
            self._cards["rdl"].set_badges([(K.MODE_BADGE_TARGET_ETA_FMT.format(n=plan.rdl_reports, t=eta("rdl")), "warn")
                                           if plan.rdl_reports else (K.MODE_BADGE_NONE, "slow")])

    # ── Wafer 폴더 로그 모으기(10/9) ──
    def wafer_logs_running(self) -> bool:
        return self._wl_worker is not None or self._fl_worker is not None      # 실패 로그도 NAS 를 읽으니 가동률 수집과 겹치지 않게

    def _on_wafer_logs(self) -> None:
        if self._wl_worker is not None or self._fl_worker is not None:
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
        if on:
            self._sec_dev.set_open(True)                # 도는 동안은 '중지' 버튼이 보여야 한다
        self._b_wl_run.setEnabled(not on)
        self._b_wl_stop.setVisible(on)
        self._b_wl_stop.setEnabled(on)
        self._wl_out.setEnabled(not on)
        self._b_wl_browse.setEnabled(not on)
        self._b_run.setEnabled(not on and not self._running)     # 가동률 수집과 동시에 NAS 를 읽지 않는다

    # ── 실패 로그 수집(10/20) ──
    def _on_fail_logs(self) -> None:
        if self._fl_worker is not None or self._wl_worker is not None:
            return
        if self._running:
            self.error.emit(K.FAIL_LOGS_TITLE, K.WAFER_LOGS_BUSY)
            return
        out = self._fl_out.text().strip() or str(paths.data_root() / "fail_logs")
        self._fl_out.setText(out)
        w = failure_logs.FailureLogsWorker(prefs.to_collect_cfg(prefs.load()), int(self._fl_days.value()), out, self)
        w.log.connect(self.append_log)
        w.done.connect(self._on_fail_logs_done)
        w.finished.connect(lambda w=w: self._worker_done("_fl_worker", w))
        self._fl_worker = w
        self._set_fail_logs_running(True)
        self._fl_status.setText(K.FAIL_LOGS_RUNNING)
        w.start()

    def _on_fail_logs_done(self, result, err: str) -> None:
        self._set_fail_logs_running(False)
        if result:
            fmt = K.FAIL_LOGS_DONE_FMT if result.get("items") else K.FAIL_LOGS_NONE_FMT
            text = fmt.format(n=result.get("items", 0), days=result.get("days", 0), path=result.get("path", ""))
        else:
            text = err
            self.error.emit(K.FAIL_LOGS_TITLE, err)
        self._fl_status.setText(text)
        self.append_log(text)

    def _set_fail_logs_running(self, on: bool) -> None:
        if on:
            self._sec_dev.set_open(True)
        for w in (self._b_fl_run, self._fl_days, self._fl_out, self._b_fl_browse):
            w.setEnabled(not on)
        self._b_run.setEnabled(not on and not self._running and self._wl_worker is None)
        self._b_wl_run.setEnabled(not on and not self._running and self._wl_worker is None)

    # ── Review 이미지 순서 조사(10/22) — 저장 위치는 실패 로그와 같은 폴더 ──
    def _on_image_survey(self) -> None:
        if self._fl_worker is not None or self._wl_worker is not None:
            return
        if self._running:
            self.error.emit(K.IMG_SURVEY_TITLE, K.WAFER_LOGS_BUSY)
            return
        out = self._fl_out.text().strip() or str(paths.data_root() / "fail_logs")
        w = image_survey.ImageSurveyWorker(prefs.to_collect_cfg(prefs.load()), int(self._is_days.value()), out, self,
                                        terms=image_survey_mod.parse_terms(self._is_terms.text()))
        w.log.connect(self.append_log)
        w.done.connect(self._on_image_survey_done)
        w.finished.connect(lambda w=w: self._worker_done("_fl_worker", w))
        self._fl_worker = w
        self._set_image_survey_running(True)
        self._is_status.setText(K.IMG_SURVEY_RUNNING)
        w.start()

    def _on_image_survey_done(self, result, err: str) -> None:
        self._set_image_survey_running(False)
        if result:
            text = K.IMG_SURVEY_DONE_FMT.format(n=result.get("items", 0), path=result.get("path", ""))
        else:
            text = err
            self.error.emit(K.IMG_SURVEY_TITLE, err)
        self._is_status.setText(text)
        self.append_log(text)

    def _set_image_survey_running(self, on: bool) -> None:
        for w in (self._b_is_run, self._is_days, self._is_terms, self._b_fl_run, self._fl_days, self._fl_out, self._b_fl_browse):
            w.setEnabled(not on)
        self._b_run.setEnabled(not on and not self._running and self._wl_worker is None)
        self._b_wl_run.setEnabled(not on and not self._running and self._wl_worker is None)

    def _browse_fl_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, K.WAFER_LOGS_OUT, self._fl_out.text())
        if chosen:
            self._fl_out.setText(chosen)

    def _browse_wl_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, K.WAFER_LOGS_OUT, self._wl_out.text())
        if chosen:
            self._wl_out.setText(chosen)

    def shutdown(self, ms: int = 15_000) -> None:
        """창을 닫을 때 — 로그 모으기를 멈추고(지금까지 담은 것으로 zip 마무리) 기다린다."""
        for attr in ("_wl_worker", "_fl_worker"):
            w = getattr(self, attr, None)
            if w is None:
                continue
            try:
                w.stop()
                w.wait(ms)
            except RuntimeError:
                setattr(self, attr, None)

    def set_running(self, running: bool) -> None:
        self._running = running
        self._b_run.setEnabled(not running and self._wl_worker is None and getattr(self, "_pz_worker", None) is None)
        self._b_wl_run.setEnabled(not running and self._wl_worker is None and self._fl_worker is None)
        self._b_fl_run.setEnabled(not running and self._fl_worker is None and self._wl_worker is None)
        self._b_is_run.setEnabled(not running and self._fl_worker is None and self._wl_worker is None)
        if hasattr(self, "_b_pzip"):
            self._b_pzip.setEnabled(not running and self._pz_worker is None)
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
