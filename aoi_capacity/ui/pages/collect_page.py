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
                             QPlainTextEdit, QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

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
MODES = ("normal", "backfill", "refresh", "recover", "rebuild", "range")
_ARGS = {"normal": (False, False, False), "backfill": (False, True, False), "refresh": (False, False, False),
         "recover": (False, False, True), "rebuild": (True, False, False), "range": (False, False, False)}   # range 는 refresh_range() 로
# 10/24: 'RDL 영역 INI 패치' 카드는 '옛 기간 빈칸 채우기' 로 합쳤다(같은 일 — Wafer 폴더 안만 읽는다). CLI 의 rdl_patch 는 그대로.


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


class _GapFillWorker(QThread):
    """옛 기간 빈칸 채우기(10/24) — `collect.fill_gaps` 로 캐시 행이 가리키는 Wafer 폴더 안만 읽고, 끝나면 가진 데이터로 결과 HTML 을 다시 만든다.
    끝나면 (통계 | None, 오류 문구). 중지는 읽던 것만 마치고 저장한다."""
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(object, str)

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self._cfg = cfg
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # noqa: D401
        try:
            st = collect.fill_gaps(self._cfg, log=self.log.emit, progress=lambda d, t, p: self.progress.emit(int(d), int(t), str(p)),
                                   should_stop=lambda: self._stop)
            if not st.get("stopped"):
                st["html"] = collect.html_from_cache(self._cfg, log=self.log.emit)
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
    """상황 카드 하나 — 누르면(또는 Space/Enter) 고른다. 고른 카드는 파란 테두리와 채운 점.
    10/24: 제목 · 한 줄('이럴 때')만 보이고 '무엇을 하나' 는 마우스를 올리면(툴팁) — 화면의 글자를 줄였다(사용자: 글자가 너무 많다)."""
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
        lay.setContentsMargins(14, 11, 14, 11)
        lay.setSpacing(4)
        top = QHBoxLayout()
        top.setSpacing(8)
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
        self._when.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._when.setContentsMargins(22, 0, 0, 0)
        lay.addWidget(self._when)
        self.extra = QHBoxLayout()
        self.extra.setSpacing(6)
        self.extra.setContentsMargins(22, 2, 0, 0)
        lay.addLayout(self.extra)
        lay.addStretch(1)                               # 격자에서 카드 높이가 맞춰질 때 글자는 위에 모여 있게
        self._what = what
        self._why = ""
        self._enabled = True
        self._apply_tip()

    def _apply_tip(self) -> None:
        self.setToolTip(self._what if self._enabled else self._why)

    def set_texts(self, title: Optional[str] = None, when: Optional[str] = None, what: Optional[str] = None) -> None:
        if title is not None:
            self._title.setText(title)
            self.setAccessibleName(title)
        if when is not None:
            self._when.setText(when)
        if what is not None:
            self._what = what
            self._apply_tip()

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
        self._why = why
        self.setProperty("enabled", "true" if on else "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor if on else Qt.CursorShape.ArrowCursor)
        self._apply_tip()
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


def _tool(parent: QWidget, title: str, short: str, tip: str) -> tuple:
    """조사 도구 한 칸(10/24) — 굵은 제목 + 한 줄 설명, 긴 설명은 제목 옆 ⓘ 에 마우스를 올리면. → (틀, 세로 레이아웃)"""
    f = QFrame(parent)
    f.setProperty("role", "tool")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(16, 12, 16, 12)
    lay.setSpacing(8)
    head = QHBoxLayout()
    head.setSpacing(8)
    head.addWidget(_label(title, "toolTitle", f))
    if short:
        head.addWidget(_label(short, "muted", f))
    if tip:
        info = _label("ⓘ", "info", f)
        info.setToolTip(tip)
        info.setCursor(Qt.CursorShape.WhatsThisCursor)
        head.addWidget(info)
    head.addStretch(1)
    lay.addLayout(head)
    return f, lay


def _date_edit(parent: QWidget, d: QDate) -> QDateEdit:
    w = QDateEdit(parent)
    w.setCalendarPopup(True)
    w.setDisplayFormat("yyyy-MM-dd")
    w.setDate(d)
    w.setMinimumWidth(124)
    return w


def _row(*items, stretch: bool = True, spacing: int = 8) -> QHBoxLayout:
    r = QHBoxLayout()
    r.setSpacing(spacing)
    for it in items:
        if isinstance(it, int):
            r.addSpacing(it)
        elif isinstance(it, QHBoxLayout):
            r.addLayout(it)
        else:
            r.addWidget(it)
    if stretch:
        r.addStretch(1)
    return r


class _GapRow:
    """빈칸 채우기 카드의 한 줄 — 이름 · 채워진 비율 막대 · 비어 있는 수 · 기간/예상."""

    def __init__(self, parent: QWidget, grid: QGridLayout, row: int, name: str, tip: str):
        self.name = _label(name, "gapName", parent)
        self.name.setToolTip(tip)
        self.bar = QProgressBar(parent)
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.setFixedSize(120, 6)
        self.count = _label("", "gapCount", parent)
        self.note = _label("", "muted", parent)
        for c, w in enumerate((self.name, self.bar, self.count, self.note)):
            grid.addWidget(w, row, c, Qt.AlignmentFlag.AlignVCenter)
        self._ws = (self.name, self.bar, self.count, self.note)

    def set(self, missing: int, have: int, text: str, note: str) -> None:
        total = missing + have
        self.bar.setValue(int(1000 * have / total) if total else 1000)
        self.count.setText(text)
        self.count.setProperty("kind", "warn" if missing else "ok")
        _repolish(self.count)
        self.note.setText(note)

    def set_visible(self, on: bool) -> None:
        for w in self._ws:
            w.setVisible(on)


class CollectPage(QWidget):
    """10/24 다시 짬(사용자: "정보가 너무 많고 글자가 많고 가독성이 부족하다") — 위에서 아래로 쓰는 빈도 순:
    ① 수집(평소 수집 카드 · 다른 방법 접기 · 실행 줄) ② 옛 기간 빈칸 채우기(빈칸이 있을 때만) ③ 결과 파일만 다시 만들기 · 조사 도구 · 설정 · 로그(전부 접힘).
    설명 문단은 한 줄로 줄이고 긴 설명은 툴팁(ⓘ)으로 옮겼다. 위젯 이름(`_b_run` · `_cards` …)은 그대로다."""
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
        lay.setContentsMargins(0, 0, 6, 12)
        lay.setSpacing(12)
        p = prefs.load()
        today = QDate.currentDate()

        # ── 머리: 제목 · 결과 열기 ──
        self._b_open = make_button(K.BTN_OPEN_RESULT, "default", body)
        self._b_folder = make_button(K.BTN_OPEN_RESULT_FOLDER, "ghost", body)
        lay.addLayout(_row(_label(K.COLLECT_PAGE_TITLE, "h1", body), stretch=False))
        lay.itemAt(lay.count() - 1).layout().addStretch(1)
        lay.itemAt(lay.count() - 1).layout().addWidget(self._b_open)
        lay.itemAt(lay.count() - 1).layout().addWidget(self._b_folder)

        # ── ① 수집 ──
        pick, pl = _card(body)
        self._cards: Dict[str, ModeCard] = {}
        self._cards["normal"] = ModeCard("normal", K.MODE_NORMAL_TITLE, K.MODE_NORMAL_WHEN, K.MODE_NORMAL_WHAT, pick)
        pl.addWidget(self._cards["normal"])
        trouble = QWidget(pick)
        grid = QGridLayout(trouble)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._cards["backfill"] = ModeCard("backfill", K.MODE_BACKFILL_TITLE, K.MODE_BACKFILL_WHEN, "", pick)
        self._cards["refresh"] = ModeCard("refresh", K.MODE_REFRESH_TITLE, K.MODE_REFRESH_WHEN, K.MODE_REFRESH_WHAT, pick)
        self._cards["recover"] = ModeCard("recover", K.MODE_RECOVER_TITLE, K.MODE_RECOVER_WHEN, K.MODE_RECOVER_WHAT, pick)
        self._cards["range"] = ModeCard("range", K.MODE_RANGE_TITLE, K.MODE_RANGE_WHEN, K.MODE_RANGE_WHAT, pick)
        self._cards["rebuild"] = ModeCard("rebuild", K.MODE_REBUILD_TITLE, K.MODE_REBUILD_WHEN, "", pick)
        for i, key in enumerate(("backfill", "refresh", "recover", "range")):
            grid.addWidget(self._cards[key], i // 2, i % 2)
        grid.addWidget(self._cards["rebuild"], 2, 0, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        # 카드 안 입력 — 빠진 날의 시작일(10/22) · 최근 며칠 · 다시 읽을 기간(10/5)
        self._b_from = _date_edit(self._cards["backfill"], today.addDays(-int(p.backfill_days or 30)))
        self._b_from.setMaximumDate(today)
        self._cards["backfill"].extra.addWidget(_label(K.BACKFILL_FROM, "muted", self._cards["backfill"]))
        self._cards["backfill"].extra.addWidget(self._b_from)
        self._cards["backfill"].extra.addStretch(1)
        self._refresh_days = QSpinBox(self._cards["refresh"])
        self._refresh_days.setRange(1, 90)
        self._refresh_days.setValue(max(1, int(p.refresh_pick_days or 3)))
        self._refresh_days.setSuffix(K.MODE_REFRESH_DAYS_SUFFIX)
        self._refresh_days.setFixedWidth(84)
        self._cards["refresh"].extra.addWidget(_label(K.MODE_REFRESH_DAYS_PREFIX, "muted", self._cards["refresh"]))
        self._cards["refresh"].extra.addWidget(self._refresh_days)
        self._cards["refresh"].extra.addStretch(1)
        self._r_from = _date_edit(self._cards["range"], today.addDays(-6))
        self._r_to = _date_edit(self._cards["range"], today)
        for w in (self._r_from, self._r_to):
            w.setMaximumDate(today)
        rx = self._cards["range"].extra
        rx.addWidget(self._r_from)
        rx.addWidget(_label("~", "muted", self._cards["range"]))
        rx.addWidget(self._r_to)
        rx.addStretch(1)
        self._trouble = Collapsible(K.COLLECT_SEC_TROUBLE, trouble, pick)
        pl.addWidget(self._trouble)
        self._cards["normal"].set_badges([(K.MODE_BADGE_REC, "rec")])
        for k in ("backfill", "refresh", "recover", "range"):
            self._cards[k].set_badges([(K.MODE_BADGE_MEDIUM, "slow")])
        self._cards["rebuild"].set_badges([(K.MODE_BADGE_SLOW, "warn")])

        rule = QFrame(pick)
        rule.setProperty("role", "rule")
        pl.addWidget(rule)
        self._resume = _label("", "help", pick, wrap=True)      # 멈춘 수집이 있을 때만 — 계획 줄과 따로 한 줄(10/11)
        self._resume.setStyleSheet("font-weight:600;")
        self._resume.hide()
        pl.addWidget(self._resume)
        self._plan = _label("", "muted", pick, wrap=True)
        self._plan.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._status = _label(K.COLLECT_IDLE, "muted", pick)
        self._b_stop = make_button(K.BTN_STOP, "default", pick)
        self._b_stop.hide()
        self._b_run = make_button(K.BTN_COLLECT_NOW, "primary", pick)
        self._b_run.setProperty("size", "lg")
        act = _row(self._plan, stretch=False, spacing=10)
        act.setStretch(0, 1)
        act.addWidget(self._status)
        act.addWidget(self._b_stop)
        act.addWidget(self._b_run)
        pl.addLayout(act)
        lay.addWidget(pick)

        # ── ② 옛 기간 빈칸 채우기(10/24) — 빈칸이 있을 때만 보인다 ──
        self._gaps, gl = _card(body)
        gtitle = _label(K.GAPS_TITLE, "cardTitle", self._gaps)
        ginfo = _label("ⓘ", "info", self._gaps)
        ginfo.setToolTip(K.GAPS_TIP)
        self._gap_eta = _label("", "badge", self._gaps)
        self._gap_eta.setProperty("kind", "slow")
        gl.addLayout(_row(gtitle, ginfo, stretch=False))
        gl.itemAt(gl.count() - 1).layout().addStretch(1)
        gl.itemAt(gl.count() - 1).layout().addWidget(self._gap_eta)
        gg = QGridLayout()
        gg.setHorizontalSpacing(14)
        gg.setVerticalSpacing(6)
        gg.setColumnStretch(3, 1)
        self._gap_rows = {"sec": _GapRow(self._gaps, gg, 0, K.GAPS_ROW_SEC, K.GAPS_ROW_SEC_TIP),
                          "params": _GapRow(self._gaps, gg, 1, K.GAPS_ROW_PARAMS, K.GAPS_ROW_PARAMS_TIP),
                          "rdl": _GapRow(self._gaps, gg, 2, K.GAPS_ROW_RDL, K.GAPS_ROW_RDL_TIP)}
        gl.addLayout(gg)
        self._b_gaps = make_button(K.GAPS_RUN, "primary", self._gaps)
        self._b_gaps.setEnabled(False)
        self._gap_status = _label("", "muted", self._gaps, wrap=True)
        gl.addLayout(_row(self._b_gaps, self._gap_status, stretch=False))
        gl.itemAt(gl.count() - 1).layout().setStretch(1, 1)
        self._gaps.hide()
        self._gap_n = 0
        self._gap_worker: Optional[_GapFillWorker] = None
        lay.addWidget(self._gaps)

        # ── ③ 결과 파일만 다시 만들기(10/5) — 수집 없이 가진 데이터로 ──
        hbox = QWidget(body)
        hl = QVBoxLayout(hbox)
        hl.setContentsMargins(4, 0, 0, 4)
        hl.setSpacing(8)
        self._have = _label(K.COLLECT_PLAN_LOADING, "muted", hbox, wrap=True)
        self._have.setToolTip(K.HTML_ONLY_WHEN)
        self._d_from, self._d_to = _date_edit(hbox, today), _date_edit(hbox, today)
        self._b_html = make_button(K.HTML_ONLY_RUN, "default", hbox)
        self._b_html.setEnabled(False)
        self._b_all = make_button(K.HTML_ONLY_ALL, "ghost", hbox, tooltip=K.HTML_ONLY_ALL_HELP)
        self._b_all.setEnabled(False)
        self._span: Optional[tuple] = None
        hl.addWidget(self._have)
        hl.addLayout(_row(self._d_from, _label("~", "muted", hbox), self._d_to, self._b_html, self._b_all))
        self._sec_html = Collapsible(K.COLLECT_SEC_HTML, hbox, body)
        lay.addWidget(self._sec_html)
        self._days_worker: Optional[_DaysWorker] = None
        self._html_worker: Optional[_HtmlOnlyWorker] = None

        # ── 조사 도구 — 개발자에게 보낼 자료 · 현상 조사(NAS 는 읽기만). 가동률 수집과 동시에 돌지 않는다 ──
        dev = QWidget(body)
        dl = QVBoxLayout(dev)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(8)

        # 실패 로그 수집(10/20)
        fcard, fl = _tool(dev, K.FAIL_LOGS_TITLE, K.FAIL_LOGS_SHORT, K.FAIL_LOGS_WHEN)
        self._fl_days = QSpinBox(fcard)
        self._fl_days.setRange(1, 90)
        self._fl_days.setValue(max(1, min(90, int(p.fail_log_days or 3))))
        self._fl_days.setSuffix(K.FAIL_LOGS_DAYS_SUFFIX)
        self._fl_days.setFixedWidth(84)
        self._fl_out = QLineEdit(str(paths.data_root() / "fail_logs"), fcard)
        self._fl_out.setProperty("role", "mono")
        self._b_fl_browse = make_button(K.BTN_BROWSE, parent=fcard)
        self._fl_status = _label("", "muted", fcard, wrap=True)
        self._b_fl_run = make_button(K.FAIL_LOGS_RUN, "primary", fcard)
        self._b_fl_open = make_button(K.FAIL_LOGS_OPEN, "ghost", fcard)
        r = _row(_label(K.FAIL_LOGS_DAYS_PREFIX, "muted", fcard), self._fl_days, 12, _label(K.WAFER_LOGS_OUT, "muted", fcard), self._fl_out,
                 self._b_fl_browse, stretch=False)
        r.setStretch(4, 1)
        fl.addLayout(r)
        fl.addLayout(_row(self._b_fl_run, self._b_fl_open, self._fl_status))
        dl.addWidget(fcard)
        self._fl_worker: Optional[QThread] = None        # 실패 로그 · Review 이미지 조사가 같은 자리를 쓴다(둘 다 NAS 읽기라 동시에 돌지 않음)

        # Review 이미지 순서 조사(10/22) — 저장 위치는 실패 로그와 같은 폴더
        icard, il = _tool(dev, K.IMG_SURVEY_TITLE, K.IMG_SURVEY_SHORT, K.IMG_SURVEY_WHEN)
        self._is_days = QSpinBox(icard)
        self._is_days.setRange(1, 90)
        self._is_days.setValue(max(1, min(90, int(p.image_survey_days or 7))))
        self._is_days.setSuffix(K.FAIL_LOGS_DAYS_SUFFIX)
        self._is_days.setFixedWidth(84)
        self._is_terms = QLineEdit(image_survey_mod.DEFAULT_TERMS_TEXT, icard)
        self._is_terms.setPlaceholderText(K.IMG_SURVEY_TERMS_HINT)
        self._is_terms.setToolTip(K.IMG_SURVEY_TERMS_HINT)
        r = _row(_label(K.FAIL_LOGS_DAYS_PREFIX, "muted", icard), self._is_days, 12, _label(K.IMG_SURVEY_TERMS_LABEL, "muted", icard),
                 self._is_terms, stretch=False)
        r.setStretch(4, 1)
        il.addLayout(r)
        self._is_status = _label("", "muted", icard, wrap=True)
        self._b_is_run = make_button(K.IMG_SURVEY_RUN, "primary", icard)
        self._b_is_pixel = make_button(K.IMG_SURVEY_PIXEL_RUN, "default", icard, tooltip=K.IMG_SURVEY_PIXEL_HINT)
        il.addLayout(_row(self._b_is_run, self._b_is_pixel, self._is_status))
        dl.addWidget(icard)

        # Wafer 로그 30일 전체 수집(10/10) — 개발자 조사용
        wcard, wl = _tool(dev, K.WAFER_LOGS_TITLE, K.WAFER_LOGS_SHORT, K.WAFER_LOGS_WHEN)
        self._wl_out = QLineEdit(wafer_logs.default_out_dir(), wcard)
        self._wl_out.setProperty("role", "mono")
        self._b_wl_browse = make_button(K.BTN_BROWSE, parent=wcard)
        r = _row(_label(K.WAFER_LOGS_OUT, "muted", wcard), self._wl_out, self._b_wl_browse, stretch=False)
        r.setStretch(1, 1)
        wl.addLayout(r)
        self._wl_status = _label("", "muted", wcard, wrap=True)
        self._b_wl_run = make_button(K.WAFER_LOGS_RUN, "default", wcard)
        self._b_wl_stop = make_button(K.WAFER_LOGS_STOP, "default", wcard)
        self._b_wl_stop.hide()
        self._b_wl_open = make_button(K.WAFER_LOGS_OPEN, "ghost", wcard)
        wl.addLayout(_row(self._b_wl_run, self._b_wl_stop, self._b_wl_open, self._wl_status))
        dl.addWidget(wcard)
        self._wl_worker: Optional[wafer_logs.WaferLogsWorker] = None

        # 파라미터 이력 — 30일 로그 zip 으로(D89). 이 PC 의 zip 만 읽는다
        pcard, pzl = _tool(dev, K.PARAM_ZIP_TITLE, K.PARAM_ZIP_SHORT, K.PARAM_ZIP_WHEN)
        self._b_pzip = make_button(K.PARAM_ZIP_RUN, "default", pcard)
        self._b_pzip.clicked.connect(self._on_param_zip)
        pzl.addLayout(_row(self._b_pzip))
        dl.addWidget(pcard)
        self._pz_worker: Optional[_ParamZipWorker] = None
        self._sec_dev = Collapsible(K.COLLECT_SEC_DEV, dev, body)
        lay.addWidget(self._sec_dev)

        # ── 설정 — 저장 위치 · 화면 · 기간 · 버전(10/11 설정 탭을 이리로) ──
        sec = QWidget(body)
        sv = QVBoxLayout(sec)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)
        self.settings_page = SettingsPage(sec)
        f = self.settings_page.top_form
        self._out = QLineEdit(p.output_dir, sec)
        self._out.setProperty("role", "mono")
        self._out.setPlaceholderText(str(paths.data_root()))
        self._out.setToolTip(K.COLLECT_OUTPUT_DEFAULT_HINT)
        self._b_out = make_button(K.BTN_BROWSE, parent=sec)
        self._csv = QCheckBox(K.COLLECT_WRITE_CSV, sec)
        self._csv.setChecked(bool(p.write_csv))
        self._result = _label("", "mono", sec, wrap=True)
        self._result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        r = _row(self._out, self._b_out, stretch=False)
        r.setStretch(0, 1)
        self.settings_page.add_row(K.COLLECT_OUTPUT_DIR, r)
        self.settings_page.add_row("", self._csv)
        self.settings_page.add_row(K.COLLECT_RESULT_TITLE, self._result)
        sv.addWidget(self.settings_page)
        self._sec_settings = Collapsible(K.COLLECT_SEC_SETTINGS, sec, body)
        lay.addWidget(self._sec_settings)

        # ── 로그 ──
        self._log = QPlainTextEdit(body)
        self._log.setProperty("role", "console")
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(MAX_LOG_LINES)
        self._log.setMinimumHeight(220)
        self._sec_log = Collapsible(K.COLLECT_LOG_TITLE, self._log, body)
        lay.addWidget(self._sec_log)
        lay.addStretch(1)

        for c in self._cards.values():
            c.picked.connect(self._pick)
        self._b_open.clicked.connect(self._open_result)
        self._b_folder.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(paths.output_dir(prefs.load().output_dir)))))
        self._b_run.clicked.connect(self._on_run)
        self._b_gaps.clicked.connect(self._on_gaps)
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
        self._b_is_pixel.clicked.connect(lambda: self._on_image_survey(pixel=True))
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

    # ── 옛 기간 빈칸 채우기(10/24) ──
    def _nas_busy(self) -> bool:
        return (self._running or self._wl_worker is not None or self._fl_worker is not None or self._pz_worker is not None
                or self._gap_worker is not None)

    def _on_gaps(self) -> None:
        if self._gap_worker is not None:                      # 도는 중에 다시 누르면 멈춤
            self._gap_worker.stop()
            self._b_gaps.setEnabled(False)
            self._gap_status.setText(K.WAFER_LOGS_STOPPING)
            return
        if self._nas_busy() or not self._gap_n:
            return
        w = _GapFillWorker(prefs.to_collect_cfg(prefs.load()), self)
        w.log.connect(self.append_log)
        w.progress.connect(self._on_gaps_progress)
        w.done.connect(self._on_gaps_done)
        w.finished.connect(lambda w=w: self._worker_done("_gap_worker", w))
        self._gap_worker = w
        self._gap_t0 = time.monotonic()
        self._b_gaps.setText(K.BTN_STOP)
        self._gap_status.setText(K.GAPS_RUNNING)
        self._b_run.setEnabled(False)
        self._b_pzip.setEnabled(False)
        w.start()

    def _on_gaps_progress(self, done: int, total: int, phase: str) -> None:
        if total > 0:
            self._gap_status.setText(K.GAPS_PROGRESS_FMT.format(done=done, total=total, phase=phase))

    def _on_gaps_done(self, st, err: str) -> None:
        self._b_gaps.setText(K.GAPS_RUN)
        self._b_gaps.setEnabled(True)
        self._b_run.setEnabled(not self._running and self._wl_worker is None)
        self._b_pzip.setEnabled(not self._running)
        if st is None:
            msg = K.GAPS_FAIL_FMT.format(error=err)
            self.error.emit(K.GAPS_TITLE, msg)
        elif st.get("stopped"):
            msg = K.GAPS_STOPPED
        else:
            msg = K.GAPS_DONE_FMT.format(sec=int((st.get("sec") or {}).get("filled", 0)), params=int((st.get("params") or {}).get("added", 0)),
                                         rdl=int((st.get("rdl") or {}).get("filled", 0)))
        self._gap_status.setText(msg)
        self.append_log(msg)
        self.refresh_result()
        self.refresh_plan()

    def _update_gaps(self, plan) -> None:
        """빈칸 카드 — 캐시만 보고 센다(NAS 접근 없음). 빈칸이 하나도 없으면 카드를 숨긴다(도는 중·방금 끝난 결과는 보인다)."""
        et = plan.etas or {}
        n = plan.sec_missing + plan.params_missing + plan.rdl_reports
        self._gap_n = n
        if self._gap_worker is None:
            self._gaps.setVisible(bool(plan.total_reports) and (n > 0 or bool(self._gap_status.text())))
            self._b_gaps.setEnabled(n > 0 and not self._nas_busy())
        rows = (("sec", plan.sec_missing, plan.sec_have, K.GAPS_MISSING_WAFER_FMT, plan.sec_from, plan.sec_to),
                ("params", plan.params_missing, plan.params_have, K.GAPS_MISSING_REPORT_FMT, plan.params_from, plan.params_to),
                ("rdl", plan.rdl_reports, plan.rdl_have, K.GAPS_MISSING_REPORT_FMT, "", ""))
        total_sec, rough_any = 0, False
        for key, miss, have, fmt, a, b in rows:
            sec, rough = et.get(key, (None, True))
            if miss and sec:
                total_sec += sec
                rough_any = rough_any or rough
            note = " · ".join(x for x in ((K.GAPS_SPAN_FMT.format(a=a, b=b) if a and a != b else a),
                                          (K.GAPS_ETA_FMT.format(t=eta_text(sec, rough)) if miss and sec is not None else "")) if x)
            g = self._gap_rows[key]
            g.set(miss, have, fmt.format(n=miss) if miss else K.GAPS_FULL, note)
            g.set_visible(bool(miss or have))
        self._gap_eta.setText(K.GAPS_ETA_FMT.format(t=eta_text(total_sec, rough_any)) if n else "")
        self._gap_eta.setVisible(bool(n))
        self._gap_eta.setToolTip(K.ETA_BASIS_TIP)

    def _on_param_zip(self) -> None:
        if self._pz_worker is not None or self._running or self._wl_worker is not None or self._gap_worker is not None:
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
        self._update_gaps(plan)
        if self._mode == "rebuild":
            text = K.COLLECT_PLAN_FULL_FMT.format(days=_days_text(plan.retention_days))
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

    def _update_cards(self, plan, n_recover) -> None:
        """캐시로 아는 사실을 카드에 적는다: 처음이면 '처음 수집' 하나만, 복구 대상 수, 마지막 수집이 오래됐는지."""
        first = plan.total_reports == 0 and self._mode != "rebuild"
        if first != self._first_run:
            self._first_run = first
            for k in ("backfill", "refresh", "recover", "rebuild", "range"):
                self._cards[k].set_available(not first, K.MODE_DISABLED_FIRST)
        n = self._cards["normal"]
        if first:
            n.set_texts(title=K.MODE_FIRST_TITLE, when=K.MODE_FIRST_WHEN, what=K.MODE_FIRST_WHAT_FMT.format(days=plan.backfill_days))
            n.set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_SLOW, "warn")])
        else:
            last = results.last_collect_time()
            days = int((time.time() - last) // 86400) if last else 0
            stale = days > collect.PATTERN_MAX_DAYS
            n.set_texts(title=K.MODE_NORMAL_TITLE, when=K.MODE_STALE_FMT.format(days=days) if stale else K.MODE_NORMAL_WHEN, what=K.MODE_NORMAL_WHAT)
            n.set_badges([(K.MODE_BADGE_REC, "rec")])
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

    # ── Wafer 폴더 로그 모으기(10/9) ──
    def wafer_logs_running(self) -> bool:
        # 실패 로그 · 빈칸 채우기도 NAS 를 읽으니 가동률 수집과 겹치지 않게
        return self._wl_worker is not None or self._fl_worker is not None or self._gap_worker is not None

    def _on_wafer_logs(self) -> None:
        if self._wl_worker is not None or self._fl_worker is not None or self._gap_worker is not None:
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
        if self._fl_worker is not None or self._wl_worker is not None or self._gap_worker is not None:
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
    def _on_image_survey(self, pixel: bool = False) -> None:
        if self._fl_worker is not None or self._wl_worker is not None or self._gap_worker is not None:
            return
        if self._running:
            self.error.emit(K.IMG_SURVEY_TITLE, K.WAFER_LOGS_BUSY)
            return
        out = self._fl_out.text().strip() or str(paths.data_root() / "fail_logs")
        w = image_survey.ImageSurveyWorker(prefs.to_collect_cfg(prefs.load()), int(self._is_days.value()), out, self,
                                        terms=image_survey_mod.parse_terms(self._is_terms.text()), pixel=pixel)
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
        for w in (self._b_is_run, self._b_is_pixel, self._is_days, self._is_terms, self._b_fl_run, self._fl_days, self._fl_out, self._b_fl_browse):
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
        for attr in ("_wl_worker", "_fl_worker", "_gap_worker"):
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
        self._b_is_pixel.setEnabled(not running and self._fl_worker is None and self._wl_worker is None)
        self._b_pzip.setEnabled(not running and self._pz_worker is None and self._gap_worker is None)
        if self._gap_worker is None:
            self._b_gaps.setEnabled(not running and bool(self._gap_n))
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
