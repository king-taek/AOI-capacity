"""설정 · 정보(수집 탭 맨 아래에 들어간다) — 처음 수집 기간, 결과 HTML 기간, 배포 폴더, 데이터 폴더, 버전·업데이트.

11/25: 배포 폴더 줄마다 [지금 올리기] [바탕화면에 바로가기] [폴더 열기] 와 마지막 배포 결과 한 줄(PP-05) — 옛 조사 도구의 '발행 시험' 카드는 없앴다.
실제 올리기는 수집 페이지가 한다(`publish_requested` · `shortcut_requested`, 수집과 겹치지 않게).

10/30: 주의 장비 기준 · 이력 보관 기간 · NAS 동시 읽기 · 어두운 화면은 옵션에서 뺐다(고정값은 `utils/prefs.py` 맨 위)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ... import i18n
from ...utils import paths, prefs

K_ = i18n.KO
from ..widgets.buttons import make_button
from ..widgets.inputs import NoWheelSpinBox as QSpinBox


class SettingsPage(QWidget):
    update_check_requested = pyqtSignal()
    publish_requested = pyqtSignal(str)               # "lot" · "full" — 지금 올리기
    shortcut_requested = pyqtSignal(str)              # "lot" · "full" — 바탕화면 바로가기

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        p = prefs.load()
        K = i18n.KO
        # 10/24: 카드 넷 · 설명 문단 셋 → 카드 하나에 '이름 | 값' 줄. 긴 설명은 툴팁으로(사용자: 글자가 너무 많다)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        card = QFrame(self)
        card.setProperty("role", "card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(6)
        self.top_form, self._grid = QGridLayout(), QGridLayout()   # 위: 수집 페이지가 넣는 줄(add_row) · 아래: 설정 — 첫 열 폭을 같게 해 줄이 맞는다
        for g in (self.top_form, self._grid):
            g.setHorizontalSpacing(14)
            g.setVerticalSpacing(9)
            g.setColumnMinimumWidth(0, 150)
            g.setColumnStretch(1, 1)
            cl.addLayout(g)
        cl.insertSpacing(1, 9)
        lay.addWidget(card)

        self._backfill = QSpinBox(card)
        self._backfill.setRange(1, 3650)
        self._backfill.setPrefix(K.SET_BACKFILL_PREFIX)
        self._backfill.setSuffix(K.SET_BACKFILL_SUFFIX)
        self._backfill.setValue(int(p.backfill_days))
        self._html_days = QSpinBox(card)
        self._html_days.setRange(0, 36500)
        self._html_days.setSpecialValueText(K.SET_HTML_DAYS_ALL)
        self._html_days.setSuffix(K.SET_HTML_DAYS_SUFFIX)
        self._html_days.setValue(int(p.html_days))
        self._publish = QLineEdit(str(p.publish_dir or ""), card)
        self._publish.setProperty("role", "mono")
        self._publish.setPlaceholderText(K.SET_PUBLISH_PLACEHOLDER)
        self._publish.setToolTip(K.SET_PUBLISH_HELP)
        self._publish.setMinimumWidth(360)
        self._publish_full = QLineEdit(str(p.publish_full_dir or ""), card)
        self._publish_full.setProperty("role", "mono")
        self._publish_full.setPlaceholderText(K.SET_PUBLISH_PLACEHOLDER)
        self._publish_full.setToolTip(K.SET_PUBLISH_FULL_HELP)
        self._publish_full.setMinimumWidth(360)
        for box in (self._backfill, self._html_days):
            box.setMinimumWidth(120)
        self._backfill.setToolTip(K.SET_COLLECT_RANGE_HELP)
        self._html_days.setToolTip(K.SET_HTML_DAYS_HELP)
        self._data_dir = QLabel(str(paths.data_root()), card)
        self._data_dir.setProperty("role", "mono")
        b_open = make_button(K.BTN_OPEN_FOLDER, "ghost", card)
        b_log = make_button(K.BTN_OPEN_LOG, "ghost", card)
        self._version = QLabel(K.SET_VERSION_UNKNOWN, card)
        self._version.setProperty("role", "mono")
        self._version.setToolTip(K.SET_NAS_NOTICE + "\n\n" + K.SET_UTIL_DEFINITION)
        b_upd = make_button(K.BTN_CHECK_UPDATE, parent=card)

        def hrow(*ws, stretch=True):
            r = QHBoxLayout()
            r.setSpacing(8)
            for w in ws:
                r.addWidget(w) if isinstance(w, QWidget) else r.addLayout(w)
            if stretch:
                r.addStretch(1)
            return r

        self._pub_btns, self._pub_status = {}, {}

        def pub_row(kind: str, edit: QLineEdit):
            b_now = make_button(K.SET_PUBLISH_NOW, "default", card)
            b_short = make_button(K.SET_PUBLISH_SHORTCUT, "ghost", card)
            b_dir = make_button(K.BTN_OPEN_FOLDER, "ghost", card)
            st = QLabel("", card)
            st.setProperty("role", "muted")
            st.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            st.hide()
            self._pub_btns[kind], self._pub_status[kind] = (b_now, b_short, b_dir), st
            b_now.clicked.connect(lambda: (self._save_publish_dirs(), self.publish_requested.emit(kind)))
            b_short.clicked.connect(lambda: (self._save_publish_dirs(), self.shortcut_requested.emit(kind)))
            b_dir.clicked.connect(lambda: edit.text().strip() and QDesktopServices.openUrl(QUrl.fromLocalFile(edit.text().strip())))
            edit.textChanged.connect(lambda _t: self._sync_publish())
            col = QVBoxLayout()
            col.setSpacing(4)
            r = hrow(edit, b_now, b_short, b_dir, stretch=False)
            r.setStretch(0, 1)
            col.addLayout(r)
            col.addWidget(st)
            return col

        rows = [
            (K.SET_BACKFILL_DAYS, hrow(self._backfill)),
            (K.SET_HTML_DAYS, hrow(self._html_days)),
            (K.SET_PUBLISH_DIR, pub_row("lot", self._publish)),
            (K.SET_PUBLISH_FULL_DIR, pub_row("full", self._publish_full)),
            (K.SET_DATA_DIR, hrow(self._data_dir, b_open, b_log)),
            (K.SET_VERSION, hrow(self._version, b_upd)),
        ]
        for r, (label, item) in enumerate(rows):
            self._put(self._grid, r, label, item)

        self._backfill.valueChanged.connect(lambda v: prefs.patch(backfill_days=int(v)))
        self._html_days.valueChanged.connect(lambda v: prefs.patch(html_days=int(v)))
        self._publish.editingFinished.connect(lambda: prefs.patch(publish_dir=self._publish.text().strip()))
        self._publish_full.editingFinished.connect(lambda: prefs.patch(publish_full_dir=self._publish_full.text().strip()))
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.data_root()))))
        b_log.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.log_file()))))
        b_upd.clicked.connect(self.update_check_requested.emit)
        self._pub_busy = False
        self._sync_publish()
        self.refresh_version()

    def _save_publish_dirs(self) -> None:
        prefs.patch(publish_dir=self._publish.text().strip(), publish_full_dir=self._publish_full.text().strip())

    def _sync_publish(self) -> None:
        for kind, edit in (("lot", self._publish), ("full", self._publish_full)):
            on = bool(edit.text().strip())
            b_now, b_short, b_dir = self._pub_btns[kind]
            b_now.setEnabled(on and not self._pub_busy)
            b_short.setEnabled(on)
            b_dir.setEnabled(on)
            b_now.setToolTip("" if on else K_.SET_PUBLISH_OFF)

    def set_publish_busy(self, busy: bool) -> None:
        """수집 중 · 다른 올리기 중에는 '지금 올리기' 를 잠근다(같은 배포 폴더에 동시에 쓰지 않게)."""
        self._pub_busy = bool(busy)
        self._sync_publish()

    def set_publish_status(self, kind: str, text: str, ok: bool = True) -> None:
        st = self._pub_status.get(kind)
        if st is None:
            return
        st.setText(text)
        st.setProperty("role", "muted" if ok else "loadErr")
        st.style().unpolish(st)
        st.style().polish(st)
        st.setVisible(bool(text))

    def publish_status(self, kind: str) -> str:
        st = self._pub_status.get(kind)
        return st.text() if st is not None else ""

    def add_row(self, label: str, item) -> None:
        """설정 줄들 위에 '이름 | 값' 한 줄을 더한다 — 수집 페이지의 결과 폴더 · CSV · 결과 파일."""
        self._put(self.top_form, self.top_form.rowCount() if self.top_form.count() else 0, label, item)

    def _put(self, g: QGridLayout, r: int, label: str, item) -> None:
        if label:
            name = QLabel(label, self)
            name.setProperty("role", "formLabel")
            g.addWidget(name, r, 0, Qt.AlignmentFlag.AlignVCenter)
        if isinstance(item, QWidget):
            g.addWidget(item, r, 1)
        else:
            g.addLayout(item, r, 1)

    def refresh_version(self) -> None:
        try:
            from ...utils import updater

            v = updater.current_version() or {}
        except Exception:  # noqa: BLE001
            v = {}
        sha, branch = str(v.get("sha", "")), str(v.get("branch", ""))
        self._version.setText(f"{sha[:7]} · {branch}" if sha else i18n.KO.SET_VERSION_UNKNOWN)
