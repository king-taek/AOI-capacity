"""설정 · 정보(수집 탭 맨 아래에 들어간다) — 표시(테마), 주의 기준, 데이터 폴더, 버전·업데이트, NAS 안내.

주의 기준은 결과 HTML 을 만들 때 함께 들어간다(화면에서도 바꿀 수 있다)."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ... import i18n
from ...utils import paths, prefs
from ..widgets.buttons import make_button
from ..widgets.inputs import NoWheelSpinBox as QSpinBox


class SettingsPage(QWidget):
    theme_changed = pyqtSignal(str)
    thresholds_changed = pyqtSignal(int, int)
    update_check_requested = pyqtSignal()

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

        self._dark = QCheckBox(K.SET_DARK_MODE, card)
        self._dark.setChecked(p.color_mode != "light")
        self._th_util = QSpinBox(card)
        self._th_util.setRange(0, 100)
        self._th_util.setSuffix(K.SET_TH_UTIL_SUFFIX)
        self._th_util.setValue(int(p.threshold_util))
        self._th_err = QSpinBox(card)
        self._th_err.setRange(0, 999)
        self._th_err.setSuffix(K.SET_TH_ERR_SUFFIX)
        self._th_err.setValue(int(p.threshold_err))
        self._backfill = QSpinBox(card)
        self._backfill.setRange(1, 3650)
        self._backfill.setSuffix(K.SET_BACKFILL_SUFFIX)
        self._backfill.setValue(int(p.backfill_days))
        self._retention = QSpinBox(card)
        self._retention.setRange(0, 36500)
        self._retention.setSpecialValueText(K.SET_RETENTION_FOREVER)   # 0 = 기한 없이 보관(10/5)
        self._retention.setSuffix(K.SET_RETENTION_SUFFIX)
        self._retention.setValue(int(p.retention_days))
        self._workers = QSpinBox(card)
        self._workers.setRange(1, 32)
        self._workers.setSuffix(K.SET_READ_WORKERS_SUFFIX)
        self._workers.setValue(int(p.read_workers))
        self._html_days = QSpinBox(card)
        self._html_days.setRange(0, 36500)
        self._html_days.setSpecialValueText(K.SET_HTML_DAYS_ALL)
        self._html_days.setSuffix(K.SET_HTML_DAYS_SUFFIX)
        self._html_days.setValue(int(p.html_days))
        for box in (self._th_util, self._th_err, self._backfill, self._retention, self._workers, self._html_days):
            box.setMinimumWidth(120)
        self._backfill.setToolTip(K.SET_COLLECT_RANGE_HELP)
        self._workers.setToolTip(K.SET_COLLECT_RANGE_HELP)
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

        def small(text):
            lb = QLabel(text, card)
            lb.setProperty("role", "muted")
            return lb

        rows = [
            (K.SET_THRESHOLDS, hrow(small(K.SET_TH_UTIL), self._th_util, small(K.SET_TH_ERR), self._th_err)),
            (K.SET_BACKFILL_DAYS, hrow(self._backfill)),
            (K.SET_RETENTION_DAYS, hrow(self._retention)),
            (K.SET_HTML_DAYS, hrow(self._html_days)),
            (K.SET_READ_WORKERS, hrow(self._workers)),
            ("", self._dark),
            (K.SET_DATA_DIR, hrow(self._data_dir, b_open, b_log)),
            (K.SET_VERSION, hrow(self._version, b_upd)),
        ]
        for r, (label, item) in enumerate(rows):
            self._put(self._grid, r, label, item)

        self._dark.toggled.connect(self._on_theme)
        self._th_util.valueChanged.connect(self._on_th)
        self._th_err.valueChanged.connect(self._on_th)
        self._backfill.valueChanged.connect(lambda v: prefs.patch(backfill_days=int(v)))
        self._retention.valueChanged.connect(lambda v: prefs.patch(retention_days=int(v)))
        self._workers.valueChanged.connect(lambda v: prefs.patch(read_workers=int(v)))
        self._html_days.valueChanged.connect(lambda v: prefs.patch(html_days=int(v)))
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.data_root()))))
        b_log.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.log_file()))))
        b_upd.clicked.connect(self.update_check_requested.emit)
        self.refresh_version()

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

    def _on_theme(self, dark: bool) -> None:
        mode = "dark" if dark else "light"
        prefs.patch(color_mode=mode)
        self.theme_changed.emit(mode)

    def _on_th(self, _v) -> None:
        u, e = int(self._th_util.value()), int(self._th_err.value())
        prefs.patch(threshold_util=u, threshold_err=e)
        self.thresholds_changed.emit(u, e)
