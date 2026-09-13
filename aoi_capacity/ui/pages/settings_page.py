"""설정 · 정보 — 표시(테마, 주의 기준), 화면 엔진, 데이터 폴더, 버전·업데이트, NAS 안내."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from ... import i18n
from ...utils import paths, prefs
from ..widgets.buttons import make_button


def _card(parent: QWidget, title: str) -> tuple:
    f = QFrame(parent)
    f.setProperty("role", "card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 14, 18, 14)
    lay.setSpacing(8)
    t = QLabel(title, f)
    t.setProperty("role", "cardTitle")
    lay.addWidget(t)
    return f, lay


class SettingsPage(QWidget):
    theme_changed = pyqtSignal(str)
    thresholds_changed = pyqtSignal(int, int)
    update_check_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        p = prefs.load()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)
        h = QLabel(i18n.KO.SET_PAGE_TITLE, self)
        h.setProperty("role", "h2")
        lay.addWidget(h)

        # 표시
        card, cl = _card(self, i18n.KO.SET_DARK_MODE)
        self._dark = QCheckBox(i18n.KO.SET_DARK_MODE, card)
        self._dark.setChecked(p.color_mode != "light")
        cl.addWidget(self._dark)
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        self._th_util = QSpinBox(card)
        self._th_util.setRange(0, 100)
        self._th_util.setSuffix(i18n.KO.SET_TH_UTIL_SUFFIX)
        self._th_util.setValue(int(p.threshold_util))
        self._th_err = QSpinBox(card)
        self._th_err.setRange(0, 999)
        self._th_err.setSuffix(i18n.KO.SET_TH_ERR_SUFFIX)
        self._th_err.setValue(int(p.threshold_err))
        tl = QLabel(i18n.KO.SET_THRESHOLDS, card)
        tl.setProperty("role", "eyebrow")
        g.addWidget(tl, 0, 0, 1, 4)
        g.addWidget(QLabel(i18n.KO.SET_TH_UTIL, card), 1, 0)
        g.addWidget(self._th_util, 1, 1)
        g.addWidget(QLabel(i18n.KO.SET_TH_ERR, card), 1, 2)
        g.addWidget(self._th_err, 1, 3)
        g.setColumnStretch(4, 1)
        cl.addLayout(g)
        self._soft = QCheckBox(i18n.KO.SET_SOFTWARE_RENDER, card)
        self._soft.setChecked(bool(p.web_software_render))
        cl.addWidget(self._soft)
        lay.addWidget(card)

        # 데이터
        card, cl = _card(self, i18n.KO.SET_DATA_DIR)
        row = QHBoxLayout()
        self._data_dir = QLabel(str(paths.data_root()), card)
        self._data_dir.setProperty("role", "mono")
        b_open = make_button(i18n.KO.BTN_OPEN_FOLDER, parent=card)
        b_log = make_button(i18n.KO.BTN_OPEN_LOG, "ghost", card)
        row.addWidget(self._data_dir, 1)
        row.addWidget(b_open)
        row.addWidget(b_log)
        cl.addLayout(row)
        lay.addWidget(card)

        # 정보
        card, cl = _card(self, i18n.KO.SET_VERSION)
        row = QHBoxLayout()
        self._version = QLabel(i18n.KO.SET_VERSION_UNKNOWN, card)
        self._version.setProperty("role", "mono")
        b_upd = make_button(i18n.KO.BTN_CHECK_UPDATE, parent=card)
        row.addWidget(self._version, 1)
        row.addWidget(b_upd)
        cl.addLayout(row)
        n = QLabel(i18n.KO.SET_NAS_NOTICE, card)
        n.setProperty("role", "help")
        n.setWordWrap(True)
        d = QLabel(i18n.KO.SET_UTIL_DEFINITION, card)
        d.setProperty("role", "muted")
        d.setWordWrap(True)
        cl.addWidget(n)
        cl.addWidget(d)
        lay.addWidget(card)
        lay.addStretch(1)

        self._dark.toggled.connect(self._on_theme)
        self._th_util.valueChanged.connect(self._on_th)
        self._th_err.valueChanged.connect(self._on_th)
        self._soft.toggled.connect(lambda on: prefs.patch(web_software_render=bool(on)))
        b_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.data_root()))))
        b_log.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.log_file()))))
        b_upd.clicked.connect(self.update_check_requested.emit)
        self.refresh_version()

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
