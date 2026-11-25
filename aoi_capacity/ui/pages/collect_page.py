"""수집 페이지 — **지금 상황에 맞는 수집을 고르고 시작**한다(9/23 개편). 실제 실행은 MainWindow 가 워커로 한다.

예전에는 체크박스 넷(backfill · refresh · rebuild · recover)이 한 줄에 잘린 채 붙어 있어 언제 무엇을 켜야 할지 알 수 없었다.
이제는 상황 카드 다섯 장으로 고른다 — 제목 · '이럴 때' · '무엇을 하나' · 걸리는 시간 · 추천/대상 수:

  평소 수집(처음이면 '처음 수집')  ← 거의 늘 이것
  ─ 결과가 이상하거나 비어 있을 때만 ─
  빠진 날 채우기(backfill) · 최근 며칠 다시 읽기(refresh) · 시간 미확인 복구(recover) · 기간 다시 읽기(range, 10/5 — 날짜 두 칸)
  ('전체 다시 만들기' 카드는 11/25 사용자 요청으로 없앴다 — 명령줄 `--rebuild-all` 은 그대로)

카드는 한 번에 하나만 고르고, 수집이 끝나면 '평소 수집' 으로 돌아간다(문제 해결용 수집이 다음에도 켜져 있지 않게).
결과 화면은 이 프로그램 안에 없다 — 수집이 만든 HTML 을 사용자가 더블클릭해서 본다('결과 화면 열기' 는 편의 버튼)."""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, List, Optional

from PyQt6.QtCore import QDate, QStandardPaths, QThread, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QProgressBar, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from ... import collect, i18n, nas_guard, publish
from ...utils import paths, prefs, results
from ...workers import failure_logs
from ..widgets.buttons import make_button, set_role
from ..widgets.collapsible import Collapsible
from ..widgets.inputs import NoWheelDateEdit as QDateEdit, NoWheelSpinBox as QSpinBox
from .settings_page import SettingsPage

MAX_LOG_LINES = 1000
K = i18n.KO
log = logging.getLogger("aoi.ui")

#: 상황 카드의 열쇠 → 워커 인자(full, backfill, recover). refresh 는 prefs.refresh_window_days 로 간다(D60).
#: 11/25: '전체 다시 만들기'(rebuild) 카드는 없앴다(사용자: "안 할 것 같아") — CLI `--rebuild-all` 만 남는다.
MODES = ("normal", "backfill", "refresh", "recover", "range")
_ARGS = {"normal": (False, False, False), "backfill": (False, True, False), "refresh": (False, False, False),
         "recover": (False, False, True), "range": (False, False, False)}   # range 는 refresh_range() 로
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


def _why_text(why: str) -> str:
    """배포 실패 이유 종류(publish.error_kind) → 짧은 문장. 원문 예외는 로그에만(11/25 PP-04)."""
    return {publish.WHY_UNREACHABLE: K.PUBLISH_WHY_UNREACHABLE, publish.WHY_DENIED: K.PUBLISH_WHY_DENIED,
            publish.WHY_LOCKED: K.PUBLISH_WHY_LOCKED, publish.WHY_CONFIG: K.PUBLISH_NO_DIR}.get(why, K.PUBLISH_WHY_OTHER)


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


class _PublishWorker(QThread):
    """배포판을 지금 올린다(11/25 — 설정의 배포 폴더 줄 '지금 올리기' · 수집 알림의 '다시 올리기'). 캐시만 읽고 장비 NAS 는 건드리지 않는다.
    jobs = [(종류 "lot" | "full", 폴더)] 를 차례로 올리고 하나 끝날 때마다 one(종류, 결과 dict | None, 이유 종류) — 예외 원문은 로그에만."""
    log = pyqtSignal(str)
    one = pyqtSignal(str, object, str)

    def __init__(self, cfg: dict, jobs: list, parent=None):
        super().__init__(parent)
        self._cfg, self._jobs = cfg, list(jobs)

    def run(self) -> None:  # noqa: D401
        for kind, out_dir in self._jobs:
            fn = publish.publish_full if kind == "full" else publish.publish_lot
            try:
                self.one.emit(kind, fn(self._cfg, out_dir, log=self.log.emit), "")
            except Exception as ex:  # noqa: BLE001
                self.log.emit(f"publish {kind} failed: {type(ex).__name__}: {ex}")
                log.warning("publish %s failed: %s: %s", kind, type(ex).__name__, ex)
                self.one.emit(kind, None, publish.error_kind(ex))


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
    """초 → '약 12분' · '1분 안쪽' · '약 1시간 20분'. 11/25: 실측이 없어도 글자는 같다('대략 약' 겹침 없앰) — 대략인 것은 배지 툴팁으로."""
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
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)     # 11/25: 포커스 테두리는 키보드로 왔을 때만(누르면 '고름' 테두리만)
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
        """[(글자, 종류[, 툴팁])] — 종류: rec(추천 · 초록) · warn(주의 · 노랑) · slow(회색) · "" (파랑)."""
        while self._badges.count():
            w = self._badges.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        for text, kind, *tip in items:
            b = _label(text, "badge", self)
            b.setProperty("kind", kind)
            if tip and tip[0]:
                b.setToolTip(tip[0])
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
        self.pct = _label("", "gapPct", parent)            # 11/25 QT-13: 막대가 '채워진 비율' 임을 숫자로 — 옆 글자는 '비어 있음' 이라 반대로 읽혔다
        self.count = _label("", "gapCount", parent)
        self.note = _label("", "muted", parent)
        for c, w in enumerate((self.name, self.bar, self.pct, self.count, self.note)):
            grid.addWidget(w, row, c, Qt.AlignmentFlag.AlignVCenter)
        self._ws = (self.name, self.bar, self.pct, self.count, self.note)

    def set(self, missing: int, have: int, text: str, note: str) -> None:
        total = missing + have
        self.bar.setValue(int(1000 * have / total) if total else 1000)
        self.pct.setText(K.GAPS_FILLED_PCT_FMT.format(p=int(100 * have / total) if total else 100))
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
    devices_requested = pyqtSignal()                   # 결과 알림의 '장비 목록' — 접근 못 한 장비를 고치러 간다
    error = pyqtSignal(str, str)
    publish_done = pyqtSignal(str, object, str)        # 지금 올리기 · 다시 올리기 한 건이 끝남(종류, 결과 | None, 이유) — 설정 줄이 마지막 결과를 적는다

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._running = False
        self._plan_token = 0
        self._plan_worker: Optional[_PlanWorker] = None
        self._mode = "normal"
        self._first_run = False
        self._done_text = ""                                  # 11/25 QT-11: 방금 끝난 수집 — 실행 줄을 '✓ 수집 완료 [결과 열기] [다시 수집]' 으로
        self._pub_worker: Optional[_PublishWorker] = None
        self._pub_queue: List[tuple] = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = self._scroll = QScrollArea(self)
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

        # ── 배포 경로 시험(10/30 임시 — 새 공유 폴더 시험이 끝나면 지운다) ──

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
        for i, key in enumerate(("backfill", "refresh", "recover", "range")):
            grid.addWidget(self._cards[key], i // 2, i % 2)
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
        self._refresh_days.setFixedWidth(72)
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
        self._b_done_open = make_button(K.BTN_OPEN_RESULT, "primary", pick)     # 11/25 QT-11: 끝나면 다음에 누를 단추가 바로 옆에
        self._b_done_open.setProperty("size", "lg")
        self._b_done_open.hide()
        act = _row(self._plan, stretch=False, spacing=10)
        act.setStretch(0, 1)
        act.addWidget(self._status)
        act.addWidget(self._b_stop)
        act.addWidget(self._b_done_open)
        act.addWidget(self._b_run)
        pl.addLayout(act)
        # 수집 결과 알림(10/24) — 예전엔 끝날 때마다 '확인' 을 눌러야 닫히는 팝업이었다. 이제 카드 안에 남고 다음 수집 때 사라진다.
        self._outcome = QFrame(pick)
        self._outcome.setProperty("role", "outcome")
        ol = QVBoxLayout(self._outcome)
        ol.setContentsMargins(14, 10, 10, 10)
        ol.setSpacing(4)
        self._oc_title = _label("", "outcomeTitle", self._outcome)
        self._oc_x = make_button(K.BTN_CLOSE, "ghost", self._outcome)
        self._oc_x.clicked.connect(self._outcome.hide)
        ol.addLayout(_row(self._oc_title, self._oc_x, stretch=False))
        ol.itemAt(0).layout().setStretch(0, 1)
        # 11/25 QT-16: 문제마다 한 항목(굵은 머리 + 흐린 설명 + 그 문제의 단추) — 예전엔 여러 문장이 줄바꿈으로만 이어졌다
        self._oc_items = QVBoxLayout()
        self._oc_items.setSpacing(8)
        ol.addLayout(self._oc_items)
        self._oc_body = _label("", "outcomeBody", self._outcome, wrap=True)   # 항목 글자를 모은 것(읽기 · 테스트용, 숨김)
        self._oc_body.hide()
        self._oc_dev = make_button(K.OUTCOME_GO_DEVICES, "default", self._outcome)
        self._oc_dev.clicked.connect(self.devices_requested.emit)
        self._oc_log = make_button(K.OUTCOME_SHOW_LOG, "ghost", self._outcome)
        self._oc_log.clicked.connect(self.show_log)
        self._oc_pub = make_button(K.OUTCOME_REPUBLISH, "default", self._outcome)
        self._oc_pub.clicked.connect(self._on_republish)
        self._oc_pub_kinds: List[str] = []
        self._oc_pub_status = _label("", "muted", self._outcome)
        for b in (self._oc_dev, self._oc_log, self._oc_pub, self._oc_pub_status):
            b.hide()
        self._outcome.hide()
        pl.addWidget(self._outcome)
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
        gg.setColumnStretch(4, 1)
        self._gap_rows = {"slot": _GapRow(self._gaps, gg, 0, K.GAPS_ROW_SLOT, K.GAPS_ROW_SLOT_TIP),
                          "sec": _GapRow(self._gaps, gg, 1, K.GAPS_ROW_SEC, K.GAPS_ROW_SEC_TIP),
                          "params": _GapRow(self._gaps, gg, 2, K.GAPS_ROW_PARAMS, K.GAPS_ROW_PARAMS_TIP),
                          "rdl": _GapRow(self._gaps, gg, 3, K.GAPS_ROW_RDL, K.GAPS_ROW_RDL_TIP),
                          "kla": _GapRow(self._gaps, gg, 4, K.GAPS_ROW_KLA, K.GAPS_ROW_KLA_TIP)}
        gl.addLayout(gg)
        self._gap_bar = QProgressBar(self._gaps)                 # 채우는 동안만 — 글자만 바뀌어서 도는지 알기 어려웠다
        self._gap_bar.setTextVisible(False)
        self._gap_bar.setFixedHeight(6)
        self._gap_bar.hide()
        gl.addWidget(self._gap_bar)
        self._b_gaps = make_button(K.GAPS_RUN, "default", self._gaps)         # 11/25 QT-13: 주 버튼은 '평소 수집 시작' 하나
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
        # 11/25 QT-17: 만드는 동안 흐르는 막대 + 한 줄, 끝나면 같은 구역에 짧게(경로 전체는 툴팁) + 폴더 열기
        self._html_bar = QProgressBar(hbox)
        self._html_bar.setRange(0, 0)
        self._html_bar.setTextVisible(False)
        self._html_bar.setFixedHeight(6)
        self._html_bar.hide()
        self._html_status = _label("", "muted", hbox)
        self._html_status.hide()
        self._b_html_folder = make_button(K.BTN_OPEN_FOLDER, "ghost", hbox)
        self._b_html_folder.hide()
        self._html_path = ""
        hl.addWidget(self._html_bar)
        hl.addLayout(_row(self._html_status, self._b_html_folder))
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
        self._fl_days.setFixedWidth(72)
        self._fl_out = QLineEdit(str(paths.data_root() / "fail_logs"), fcard)
        self._fl_out.setProperty("role", "mono")
        self._b_fl_browse = make_button(K.BTN_BROWSE, parent=fcard)
        self._fl_status = _label("", "muted", fcard, wrap=True)
        self._b_fl_run = make_button(K.FAIL_LOGS_RUN, "default", fcard)
        self._b_fl_open = make_button(K.FAIL_LOGS_OPEN, "ghost", fcard)
        r = _row(_label(K.FAIL_LOGS_DAYS_PREFIX, "muted", fcard), self._fl_days, 12, _label(K.WAFER_LOGS_OUT, "muted", fcard), self._fl_out,
                 self._b_fl_browse, stretch=False)
        r.setStretch(4, 1)
        fl.addLayout(r)
        fl.addLayout(_row(self._b_fl_run, self._b_fl_open, self._fl_status))
        dl.addWidget(fcard)
        self._fl_worker: Optional[QThread] = None        # 실패 로그 워커 자리

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
        self._result = _label("", "mono", sec, wrap=True)
        self._result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        r = _row(self._out, self._b_out, stretch=False)
        r.setStretch(0, 1)
        self.settings_page.add_row(K.COLLECT_OUTPUT_DIR, r)
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
        self._b_done_open.clicked.connect(self._open_result)
        self._b_html_folder.clicked.connect(lambda: self._html_path and QDesktopServices.openUrl(
            QUrl.fromLocalFile(os.path.dirname(self._html_path))))
        self.settings_page.publish_requested.connect(self.publish_now)
        self.settings_page.shortcut_requested.connect(self._on_shortcut)
        self._b_gaps.clicked.connect(self._on_gaps)
        self._b_html.clicked.connect(self._on_html_only)
        self._b_all.clicked.connect(self._on_html_all)
        self._b_stop.clicked.connect(self.stop_requested.emit)
        self._b_out.clicked.connect(self._browse_out)
        self._refresh_days.valueChanged.connect(self._on_refresh_days)
        for w in (self._r_from, self._r_to):
            w.dateChanged.connect(lambda _d: self._mode == "range" and self.refresh_plan())
        self._b_from.dateChanged.connect(lambda _d: self._mode == "backfill" and self.refresh_plan())
        self._out.editingFinished.connect(self._apply_out)
        self._b_fl_run.clicked.connect(self._on_fail_logs)
        self._b_fl_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self._fl_out.text().strip())))
        self._b_fl_browse.clicked.connect(self._browse_fl_out)
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
        self.clear_done()
        self._b_run.setText(self._run_label())
        self.refresh_plan()

    def _run_label(self) -> str:
        return K.BTN_COLLECT_AGAIN if self._done_text else K.MODE_RUN_FMT.format(title=self._cards[self._mode].title())

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
        if attr != "_days_worker":
            self._sync_buttons()

    def _on_days(self, got) -> None:
        if not got or not got[0]:
            self._have.setText(K.HTML_ONLY_NONE)
            self._span = None
            self._sync_buttons()
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
        self._sync_buttons()

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
        w = _HtmlOnlyWorker(prefs.to_collect_cfg(prefs.load()), a, b, self)
        w.log.connect(self.append_log)
        w.done.connect(self._on_html_done)
        w.finished.connect(lambda w=w: self._worker_done("_html_worker", w))
        self._html_worker = w
        self._sec_html.set_open(True)
        self._html_bar.show()
        self._html_status.setText(K.HTML_ONLY_RUNNING)
        self._html_status.setToolTip("")
        self._html_status.show()
        self._b_html_folder.hide()
        self._sync_buttons()
        w.start()

    def make_default_html(self) -> None:
        """수집 실패 안내의 '결과 파일만 다시 만들기' — 수집이 만들었을 기간(설정의 결과 HTML 기본 기간)으로 바로 만든다."""
        self._sec_html.set_open(True)
        QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(self._sec_html, 0, 40))
        if self._span:
            self._on_html_only()

    def _on_html_done(self, path, err: str) -> None:
        self._html_worker = None if self._html_worker is not None and not self._html_worker.isRunning() else self._html_worker
        self._html_bar.hide()
        if path:
            self._html_path = str(path)
            self.append_log(K.HTML_ONLY_DONE_FMT.format(path=path))
            self._html_status.setText(K.HTML_ONLY_DONE_SHORT_FMT.format(name=os.path.basename(str(path))))
            self._html_status.setToolTip(str(path))
            self._b_html_folder.show()
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        else:
            self._html_status.setText(K.HTML_ONLY_FAIL_FMT.format(error=err))
            self.append_log(K.HTML_ONLY_FAIL_FMT.format(error=err))
            self.error.emit(K.HTML_ONLY_TITLE, K.HTML_ONLY_FAIL_FMT.format(error=err))
        QTimer.singleShot(0, self._sync_buttons)

    # ── 옛 기간 빈칸 채우기(10/24) ──
    def _nas_busy(self) -> bool:
        return self._running or self._fl_worker is not None or self._gap_worker is not None

    def _busy_reason(self) -> str:
        """수집을 지금 시작할 수 없는 이유(없으면 "") — 실행 줄에 적는다(11/25 QT-12: 이유 없이 꺼지던 '평소 수집 시작')."""
        if self._running:
            return ""
        if self._gap_worker is not None:
            return K.COLLECT_BUSY_GAPS
        if self._pub_worker is not None:
            return K.COLLECT_BUSY_PUBLISH
        if self._fl_worker is not None:
            return K.COLLECT_BUSY_FAILLOGS
        return ""

    def _sync_buttons(self) -> None:
        """버튼 켜짐/꺼짐을 한 곳에서 정한다(11/25 QT-14 — 완료 콜백마다 따로 계산하다 서로 덮었다: 배포 중 실패 로그가 끝나면
        '평소 수집' 이 다시 켜졌고, 가진 데이터가 없는데 중지 뒤 '이 기간으로 만들기' 가 켜졌다). 모든 완료 콜백은 이것만 부른다."""
        run, gap, pub, fl, html = (self._running, self._gap_worker is not None, self._pub_worker is not None,
                                   self._fl_worker is not None, self._html_worker is not None)
        busy = self._busy_reason()
        self._b_run.setEnabled(not run and not busy)
        self._b_run.setText(self._run_label())
        if gap:
            self._b_gaps.setEnabled(not getattr(self, "_gap_stopping", False))
        else:
            self._b_gaps.setEnabled(not run and not fl and not pub and bool(self._gap_n))
        self._b_fl_run.setEnabled(not run and not fl and not gap)
        for w in (self._fl_days, self._fl_out, self._b_fl_browse):
            w.setEnabled(not fl)
        have = bool(self._span)
        self._b_html.setEnabled(not run and not html and have)
        self._b_all.setEnabled(not run and not html and have)
        for w in (*self._cards.values(), self._refresh_days, self._r_from, self._r_to, self._b_from, self._out, self._b_out):
            w.setEnabled(not run)
        self.settings_page.set_publish_busy(run or pub)
        self._oc_pub.setEnabled(not run and not pub)
        if not run:
            if busy:
                self._status.setProperty("role", "muted")
                self._status.setText(busy)
            elif self._done_text:
                self._status.setProperty("role", "doneOk")
                self._status.setText(self._done_text)
            elif self._status.text() in (K.COLLECT_BUSY_GAPS, K.COLLECT_BUSY_PUBLISH, K.COLLECT_BUSY_FAILLOGS):
                self._status.setText(K.COLLECT_IDLE)
            _repolish(self._status)

    def _on_gaps(self) -> None:
        if self._gap_worker is not None:                      # 도는 중에 다시 누르면 멈춤
            self._gap_worker.stop()
            self._gap_stopping = True
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
        self._gap_stopping = False
        self._gap_t0 = time.monotonic()
        self._b_gaps.setText(K.BTN_STOP)
        self._gap_status.setText(K.GAPS_RUNNING)
        self._sync_buttons()
        w.start()

    def _on_gaps_progress(self, done: int, total: int, phase: str) -> None:
        self._gap_bar.show()
        if total <= 0:
            self._gap_bar.setRange(0, 0)                         # 총량 모름 — 흐르는 막대
            if phase:
                self._gap_status.setText(phase)
            return
        now = time.monotonic()
        if total != getattr(self, "_gap_total", None) or done < getattr(self, "_gap_done", 0):
            self._gap_t1, self._gap_total = now, total             # 단계가 바뀌었다 — 남은 시간은 새로 센다
        self._gap_done = done
        self._gap_bar.setRange(0, total)
        self._gap_bar.setValue(done)
        el = now - self._gap_t1
        left = K.GAPS_LEFT_FMT.format(t=eta_text(el * (total - done) / done, False)) if done >= 5 and el >= 8 and done < total else ""
        self._gap_status.setText(K.GAPS_PROGRESS_FMT.format(done=done, total=total, phase=phase) + left)

    def _on_gaps_done(self, st, err: str) -> None:
        self._gap_bar.hide()
        self._gap_total = None
        self._gap_stopping = False
        self._b_gaps.setText(K.GAPS_RUN)
        if self._gap_worker is not None and not self._gap_worker.isRunning():
            self._gap_worker = None
        QTimer.singleShot(0, self._sync_buttons)              # 워커가 끝난(finished) 뒤 한 번 더 — 자리가 비워진 다음에 정한다
        if st is None:
            msg = K.GAPS_FAIL_FMT.format(error=err)
            self.error.emit(K.GAPS_TITLE, msg)
        elif st.get("stopped"):
            msg = K.GAPS_STOPPED
        else:
            msg = K.GAPS_DONE_FMT.format(slot=int((st.get("slot") or {}).get("filled", 0)), sec=int((st.get("sec") or {}).get("filled", 0)), params=int((st.get("params") or {}).get("added", 0)),
                                         rdl=int((st.get("rdl") or {}).get("filled", 0)), kla=int((st.get("kla") or {}).get("filled", 0)))
        self._gap_status.setText(msg)
        self.append_log(msg)
        self.refresh_result()
        self.refresh_plan()

    def _update_gaps(self, plan) -> None:
        """빈칸 카드 — 캐시만 보고 센다(NAS 접근 없음). 빈칸이 하나도 없으면 카드를 숨긴다(도는 중·방금 끝난 결과는 보인다)."""
        et = plan.etas or {}
        n = plan.slot_missing + plan.sec_missing + plan.params_missing + plan.rdl_reports + plan.kla_missing
        self._gap_n = n
        if self._gap_worker is None:
            self._gaps.setVisible(bool(plan.total_reports) and (n > 0 or bool(self._gap_status.text())))
        self._sync_buttons()
        rows = (("slot", plan.slot_missing, plan.slot_have, K.GAPS_MISSING_WAFER_FMT, plan.slot_from, plan.slot_to),
                ("sec", plan.sec_missing, plan.sec_have, K.GAPS_MISSING_WAFER_FMT, plan.sec_from, plan.sec_to),
                ("params", plan.params_missing, plan.params_have, K.GAPS_MISSING_REPORT_FMT, plan.params_from, plan.params_to),
                ("rdl", plan.rdl_reports, plan.rdl_have, K.GAPS_MISSING_REPORT_FMT, "", ""),
                ("kla", plan.kla_missing, plan.kla_have, K.GAPS_MISSING_WAFER_FMT, "", ""))
        total_sec, rough_any = 0, False
        for key, miss, have, fmt, a, b in rows:
            sec, rough = et.get(key, (None, True))
            if miss and sec:
                total_sec += sec
                rough_any = rough_any or rough
            note = K.GAPS_SPAN_FMT.format(a=a, b=b) if a and a != b else a     # 예상 시간은 머리 배지 하나에만(10/24)
            g = self._gap_rows[key]
            g.set(miss, have, fmt.format(n=miss) if miss else K.GAPS_FULL, note)
            g.set_visible(bool(miss or have))
        self._gap_eta.setText(K.GAPS_ETA_FMT.format(t=eta_text(total_sec, rough_any)) if n else "")
        self._gap_eta.setVisible(bool(n))
        self._gap_eta.setToolTip(K.ETA_ROUGH_TIP if rough_any else K.ETA_BASIS_TIP)

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
        if self._mode == "range":
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
        first = plan.total_reports == 0
        if first != self._first_run:
            self._first_run = first
            for k in ("backfill", "refresh", "recover", "range"):
                self._cards[k].set_available(not first, K.MODE_DISABLED_FIRST)
        self._trouble.set_note(K.COLLECT_TROUBLE_LOCKED if first else "")      # 11/25 QT-12: 왜 못 누르는지 — 마우스를 올리지 않아도 보이게
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
        self._b_run.setText(self._run_label())
        et = plan.etas or {}

        def eta(mode):
            sec, _rough = et.get(mode, (None, True))
            return None if sec is None else eta_text(sec)

        def tip(mode):                                    # 11/25 QT-08: 대략인지는 글자가 아니라 툴팁으로
            return K.ETA_ROUGH_TIP if et.get(mode, (None, True))[1] else K.ETA_BASIS_TIP

        if not first and eta("incremental"):
            n.set_badges([(K.MODE_BADGE_REC, "rec"), (K.MODE_BADGE_USUAL_ETA_FMT.format(t=eta("incremental")), "slow", tip("incremental"))])
        if not first:
            for m, name in (("backfill", "backfill"), ("range", "range")):
                if eta(m):
                    self._cards[name].set_badges([(K.MODE_BADGE_ETA_FMT.format(t=eta(m)), "slow", tip(m))])
            self._cards["refresh"].set_badges([(K.MODE_BADGE_TARGET_ETA_FMT.format(n=plan.reread_reports, t=eta("refresh")), "slow", tip("refresh"))]
                                              if plan.reread_reports and eta("refresh") else [(K.MODE_BADGE_MEDIUM, "slow")])
        if n_recover is not None and not first:
            self._cards["recover"].set_badges([(K.MODE_BADGE_TARGET_ETA_FMT.format(n=n_recover, t=eta("recover")), "warn", tip("recover"))
                                               if n_recover and eta("recover") else (K.MODE_BADGE_TARGET_FMT.format(n=n_recover), "warn") if n_recover
                                               else (K.MODE_BADGE_NONE, "slow")])

    def wafer_logs_running(self) -> bool:
        # 실패 로그 · 빈칸 채우기도 NAS 를 읽으니 가동률 수집과 겹치지 않게
        return self._fl_worker is not None or self._gap_worker is not None

    # ── 배포 지금 올리기(11/25 — 설정의 배포 폴더 줄 · 수집 알림의 '다시 올리기'. 옛 '발행 시험' 카드를 대신한다) ──
    def publish_now(self, kinds) -> None:
        """kinds = "lot" · "full" 또는 그 목록 — 설정에 적힌 폴더로 캐시에서 다시 만들어 올린다(장비 NAS 접근 없음). 비어 있는 폴더는 건너뛴다."""
        kinds = [kinds] if isinstance(kinds, str) else list(kinds)
        if self._pub_worker is not None or self._running:
            self.error.emit(K.SET_PUBLISH_DIR if kinds[:1] == ["lot"] else K.SET_PUBLISH_FULL_DIR, K.SET_PUBLISH_BUSY)
            return
        cfg = prefs.to_collect_cfg(prefs.load())
        jobs = [(k, str(cfg.get("publish_full_dir" if k == "full" else "publish_dir") or "").strip()) for k in kinds]
        jobs = [(k, d) for k, d in jobs if d]
        if not jobs:
            return
        w = _PublishWorker(cfg, jobs, self)
        w.log.connect(self.append_log)
        w.one.connect(self._on_publish_one)
        w.finished.connect(lambda w=w: self._publish_finished(w))
        self._pub_worker = w
        for k, _d in jobs:
            self.settings_page.set_publish_status(k, K.SET_PUBLISH_RUNNING)
        self._sync_buttons()
        w.start()

    def _on_publish_one(self, kind: str, got, why: str) -> None:
        when = time.strftime("%H:%M")
        if got is None:
            text = K.SET_PUBLISH_FAIL_FMT.format(when=when, why=_why_text(why))
        elif not got.get("pointer_ok"):
            text = K.SET_PUBLISH_DONE_LOCKED_FMT.format(when=when)
        else:
            text = K.SET_PUBLISH_DONE_FMT.format(when=when, size=f"{int(got['bytes']) / 1048576:.1f}MB", sec=got["sec"])
        self.settings_page.set_publish_status(kind, text, ok=got is not None)
        self.append_log(text)
        if kind in self._oc_pub_kinds:
            self._oc_pub_status.setText(K.OUTCOME_REPUBLISH_DONE if got is not None else _why_text(why))
            self._oc_pub_status.show()
        self.publish_done.emit(kind, got, why)

    def _publish_finished(self, w) -> None:
        if self._pub_worker is w:
            self._pub_worker = None
        w.deleteLater()
        self._sync_buttons()

    def _on_republish(self) -> None:
        self._oc_pub_status.setText(K.OUTCOME_REPUBLISHING)
        self._oc_pub_status.show()
        self.publish_now(self._oc_pub_kinds or ["lot", "full"])

    def _on_shortcut(self, kind: str) -> None:
        cfg = prefs.to_collect_cfg(prefs.load())
        out = str(cfg.get("publish_full_dir" if kind == "full" else "publish_dir") or "").strip()
        title = K.SET_PUBLISH_FULL_DIR if kind == "full" else K.SET_PUBLISH_DIR
        if not out or not os.path.isabs(out):
            self.error.emit(title, K.PUBLISH_NO_DIR if not out else K.PUBLISH_NOT_ABS_FMT.format(path=out))
            return
        desk = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation) or str(paths.data_root())
        try:
            path = publish.write_shortcut(desk, out, cfg, kind=publish.FULL if kind == "full" else publish.LOT)
        except Exception as ex:  # noqa: BLE001
            log.warning("shortcut failed: %s: %s", type(ex).__name__, ex)
            self.error.emit(title, _why_text(publish.error_kind(ex)))
            return
        text = K.SET_PUBLISH_SHORTCUT_DONE_FMT.format(path=path)
        self.settings_page.set_publish_status(kind, text, ok=True)
        self.append_log(text)

    # ── 실패 로그 수집(10/20) ──
    def _on_fail_logs(self) -> None:
        if self._fl_worker is not None or self._gap_worker is not None:
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
        if self._fl_worker is not None and not self._fl_worker.isRunning():
            self._fl_worker = None
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
        QTimer.singleShot(0, self._sync_buttons)
        self._sync_buttons()

    def _browse_fl_out(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, K.WAFER_LOGS_OUT, self._fl_out.text())
        if chosen:
            self._fl_out.setText(chosen)

    def shutdown(self, ms: int = 15_000) -> None:
        """창을 닫을 때 — 로그 모으기를 멈추고(지금까지 담은 것으로 zip 마무리) 기다린다. 올리는 중인 배포는 끝날 때까지 기다린다."""
        w = self._pub_worker
        if w is not None:
            try:
                w.wait(ms)
            except RuntimeError:
                self._pub_worker = None
        for attr in ("_fl_worker", "_gap_worker"):
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
        self._b_stop.setVisible(running)
        self._b_stop.setEnabled(running)
        self._status.setProperty("role", "muted")
        self._status.setText(K.COLLECT_RUNNING if running else K.COLLECT_IDLE)
        _repolish(self._status)
        if running:
            self._outcome.hide()
            self.clear_done()
        self._sync_buttons()
        if not running:
            self._pick("normal")                         # 문제 해결용 수집은 한 번만 — 다음엔 평소 수집으로 돌아간다

    def set_status(self, text: str) -> None:
        self._status.setProperty("role", "muted")
        self._status.setText(text)
        _repolish(self._status)

    def show_done(self, text: str) -> None:
        """11/25 QT-11: 수집이 끝나면 실행 줄을 '✓ 수집 완료 · 39대 · 3분 20초  [결과 열기](주)  [다시 수집]' 으로 — 다음 고르기 · 수집 때 원래대로."""
        self._done_text = text
        have = results.html_path().is_file()
        self._b_done_open.setVisible(have)
        set_role(self._b_run, "default" if have else "primary")
        self._sync_buttons()

    def clear_done(self) -> None:
        if not self._done_text:
            return
        self._done_text = ""
        self._b_done_open.hide()
        set_role(self._b_run, "primary")
        self._status.setProperty("role", "muted")
        self._status.setText(K.COLLECT_IDLE)
        _repolish(self._status)
        self._b_run.setText(self._run_label())

    def mode_title(self) -> str:
        """고른 수집 방법의 이름 — 로딩 화면 제목에 쓴다."""
        return self._cards[self._mode].title()

    def show_outcome(self, title: str, items: list, devices: bool = False) -> None:
        """수집 결과 알림을 카드 안에 띄운다. items 가 비면 숨긴다.
        11/25 QT-16: 항목마다 굵은 머리 + 흐린 설명 + 그 문제에 맞는 단추(장비 목록 확인 · 로그 보기 · 다시 올리기). 문자열을 주면 머리만 있는 항목."""
        while self._oc_items.count():
            it = self._oc_items.takeAt(0)
            w = it.widget()
            if w is not None:
                for b in (self._oc_dev, self._oc_log, self._oc_pub, self._oc_pub_status):
                    if b.parent() is w:
                        b.setParent(self._outcome)
                        b.hide()
                w.deleteLater()
        if not items:
            self._outcome.hide()
            return
        items = [{"head": x, "desc": "", "action": "devices" if devices and i == 0 else ""} if isinstance(x, str) else x
                 for i, x in enumerate(items)]
        self._oc_title.setText(title)
        self._oc_body.setText("\n".join(" — ".join(t for t in (x.get("head", ""), x.get("desc", "")) if t) for x in items))
        used = set()
        for x in items:
            box = QFrame(self._outcome)
            box.setProperty("role", "ocItem")
            bl = QHBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(10)
            col = QVBoxLayout()
            col.setSpacing(1)
            head = _label(x.get("head", ""), "ocHead", box, wrap=True)
            head.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            if x.get("tip"):
                head.setToolTip(x["tip"])
            col.addWidget(head)
            if x.get("desc"):
                col.addWidget(_label(x["desc"], "ocDesc", box, wrap=True))
            bl.addLayout(col, 1)
            act = x.get("action", "")
            btns = {"devices": (self._oc_dev,), "log": (self._oc_log,), "republish": (self._oc_pub_status, self._oc_pub)}.get(act, ())
            if act and act not in used:
                used.add(act)
                for b in btns:
                    b.setParent(box)
                    bl.addWidget(b, 0, Qt.AlignmentFlag.AlignTop)
                    b.setVisible(b is not self._oc_pub_status)
                if act == "republish":
                    self._oc_pub_kinds = list(dict.fromkeys(x.get("kinds") or ["lot", "full"]))
                    self._oc_pub_status.setText("")
            self._oc_items.addWidget(box)
        if "log" not in used:                               # 로그 보기는 늘 한 군데 — 마지막 항목 옆
            last = self._oc_items.itemAt(self._oc_items.count() - 1).widget()
            self._oc_log.setParent(last)
            last.layout().addWidget(self._oc_log, 0, Qt.AlignmentFlag.AlignTop)
            self._oc_log.show()
        self._sync_buttons()
        self._outcome.show()

    def show_log(self) -> None:
        self._sec_log.set_open(True)
        QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(self._sec_log, 0, 40))

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
