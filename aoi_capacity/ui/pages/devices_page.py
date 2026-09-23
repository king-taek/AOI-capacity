"""장비 목록 편집 — 표 하나가 devices.csv 다. 저장은 이 PC 의 데이터 폴더에만 한다(NAS 에는 절대 쓰지 않는다)."""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
                             QTableWidgetItem, QVBoxLayout, QWidget)

from ... import devices as devices_mod
from ... import i18n, nas_guard
from ...utils import paths, prefs
from ..widgets.buttons import make_button

COLS = ("name", "root", "sub", "on", "memo", "status")
HEADERS = (i18n.KO.DEV_COL_NAME, i18n.KO.DEV_COL_ROOT, i18n.KO.DEV_COL_SUB, i18n.KO.DEV_COL_ON, i18n.KO.DEV_COL_MEMO, i18n.KO.DEV_COL_STATUS)
_STATUS_TEXT = {"ok": i18n.KO.DEV_STATUS_OK, "no_report": i18n.KO.DEV_STATUS_NO_REPORT,
                "unreachable": i18n.KO.DEV_STATUS_UNREACHABLE, "out_of_scope": i18n.KO.DEV_STATUS_OUT_OF_SCOPE}


class _CheckWorker(QThread):
    """'연결 확인' — NAS 폴더 존재 여부를 UI 스레드 밖에서 본다(읽기만)."""
    result = pyqtSignal(int, object)

    def __init__(self, token: int, rows: List[dict], cfg: dict, parent=None):
        super().__init__(parent)
        self.token, self.rows, self.cfg = token, rows, cfg

    def run(self) -> None:
        try:
            self.result.emit(self.token, devices_mod.check_rows(self.rows, self.cfg))
        except Exception as exc:  # noqa: BLE001
            self.result.emit(self.token, [{**r, "status": f"error:{exc}"} for r in self.rows])


class DevicesPage(QWidget):
    saved = pyqtSignal()
    message = pyqtSignal(str)               # 토스트/상태줄용 짧은 문구
    error = pyqtSignal(str, str)            # 제목, 본문 (MainWindow 가 시트로 띄움)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._dirty = False
        self._check_token = 0
        self._checker: Optional[_CheckWorker] = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        h = QLabel(i18n.KO.DEV_PAGE_TITLE, self)
        h.setProperty("role", "h1")
        help_ = QLabel(i18n.KO.DEV_PAGE_HELP, self)
        help_.setProperty("role", "help")
        help_.setWordWrap(True)
        lay.addWidget(h)
        lay.addWidget(help_)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self._b_add = make_button(i18n.KO.BTN_ADD_ROW, parent=self)
        self._b_del = make_button(i18n.KO.BTN_REMOVE_ROW, parent=self)
        self._b_browse = make_button(i18n.KO.BTN_BROWSE, parent=self, tooltip=i18n.KO.DEV_BROWSE_TITLE)
        self._b_auto = make_button(i18n.KO.BTN_AUTO_FOLDER, parent=self)
        self._b_import = make_button(i18n.KO.BTN_IMPORT_CSV, parent=self)
        self._b_export = make_button(i18n.KO.BTN_EXPORT_CSV, parent=self)
        self._b_check = make_button(i18n.KO.BTN_CHECK_CONN, parent=self)
        self._b_default = make_button(i18n.KO.BTN_LOAD_DEFAULT_DEVICES, "ghost", self)
        self._b_revert = make_button(i18n.KO.BTN_REVERT, "ghost", self)
        self._b_save = make_button(i18n.KO.BTN_SAVE, "primary", self)
        for b in (self._b_add, self._b_del, self._b_browse, self._b_auto, self._b_import, self._b_export, self._b_check, self._b_default):
            bar.addWidget(b)
        bar.addStretch(1)
        bar.addWidget(self._b_revert)
        bar.addWidget(self._b_save)
        lay.addLayout(bar)

        self._table = QTableWidget(0, len(COLS), self)
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 130)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 60)
        self._table.setColumnWidth(5, 120)
        self._table.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self._table, 1)
        self._empty = QLabel(i18n.KO.DEV_EMPTY_HINT, self)
        self._empty.setProperty("role", "muted")
        lay.addWidget(self._empty)

        self._b_add.clicked.connect(lambda: self.add_row())
        self._b_del.clicked.connect(self.remove_selected)
        self._b_browse.clicked.connect(self.browse)
        self._b_auto.clicked.connect(self.set_auto)
        self._b_import.clicked.connect(self.import_csv)
        self._b_export.clicked.connect(self.export_csv)
        self._b_check.clicked.connect(self.check_connections)
        self._b_default.clicked.connect(self.load_default)
        self._b_revert.clicked.connect(self.load)
        self._b_save.clicked.connect(self.save)
        self.load()

    # ── 표 ↔ 행 ──
    def rows(self) -> List[Dict[str, object]]:
        out = []
        for r in range(self._table.rowCount()):
            def txt(c):
                it = self._table.item(r, c)
                return it.text().strip() if it else ""
            on_item = self._table.item(r, 3)
            out.append({"name": txt(0), "root": txt(1), "sub": txt(2),
                        "on": bool(on_item and on_item.checkState() == Qt.CheckState.Checked), "memo": txt(4)})
        return out

    def _set_rows(self, rows: List[Dict[str, object]]) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for row in rows:
            self.add_row(row, mark_dirty=False)
        self._table.blockSignals(False)
        self._dirty = False
        self._update_buttons()

    def add_row(self, row: Optional[Dict[str, object]] = None, mark_dirty: bool = True) -> int:
        row = row or {"name": "", "root": "", "sub": "", "on": True, "memo": ""}
        r = self._table.rowCount()
        self._table.blockSignals(True)
        self._table.insertRow(r)
        for c, key in enumerate(("name", "root", "sub")):
            it = QTableWidgetItem(str(row.get(key, "")))
            if key == "root":
                it.setFont(self._mono_font())
            self._table.setItem(r, c, it)
        on = QTableWidgetItem("")
        on.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        on.setCheckState(Qt.CheckState.Checked if row.get("on", True) else Qt.CheckState.Unchecked)
        self._table.setItem(r, 3, on)
        self._table.setItem(r, 4, QTableWidgetItem(str(row.get("memo", ""))))
        st = QTableWidgetItem("")
        st.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self._table.setItem(r, 5, st)
        self._table.blockSignals(False)
        if mark_dirty:
            self._mark_dirty()
        self._update_buttons()
        return r

    def _mono_font(self):
        f = self.font()
        f.setFamilies(["Cascadia Mono", "Consolas", "D2Coding", "monospace"])
        return f

    def _on_item_changed(self, _item) -> None:
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        self._dirty = True
        self._update_buttons()

    def is_dirty(self) -> bool:
        return self._dirty

    def _update_buttons(self) -> None:
        self._b_save.setEnabled(self._dirty)
        self._b_revert.setEnabled(self._dirty)
        self._empty.setVisible(self._table.rowCount() == 0)

    def _selected_row(self) -> int:
        sel = self._table.selectionModel().selectedRows() if self._table.selectionModel() else []
        return sel[0].row() if sel else (self._table.currentRow() if self._table.currentRow() >= 0 else -1)

    # ── 동작 ──
    def load(self) -> None:
        paths.ensure_user_files()
        p = paths.devices_csv_path()
        rows = devices_mod.read_devices_csv(p) if p.exists() else []
        self._set_rows(rows)

    def load_default(self) -> None:
        self._set_rows(devices_mod.read_devices_csv(paths.default_devices_csv()))
        self._mark_dirty()

    def save(self) -> bool:
        rows = [r for r in self.rows() if r["root"] or r["name"] or r["sub"]]
        p = prefs.load()
        roots = nas_guard.expand_roots(r["root"] for r in rows)
        try:  # 데이터 폴더·결과 폴더가 NAS 아래면 저장 자체를 거부
            nas_guard.assert_local(paths.data_root(), roots)
            nas_guard.assert_local(paths.output_dir(p.output_dir), roots)
            devices_mod.write_devices_csv(paths.devices_csv_path(), rows, roots)
        except nas_guard.NasWriteRefused as exc:
            self.error.emit(i18n.KO.COLLECT_OUTPUT_ON_NAS_TITLE, str(exc))
            return False
        self._dirty = False
        self._update_buttons()
        self.message.emit(i18n.KO.DEV_SAVED_TOAST)
        self.saved.emit()
        return True

    def remove_selected(self) -> None:
        r = self._selected_row()
        if r >= 0:
            self._table.removeRow(r)
            self._mark_dirty()

    def set_auto(self) -> None:
        r = self._selected_row()
        if r < 0:
            r = self.add_row()
        self._table.item(r, 2).setText(devices_mod.AUTO)

    def browse(self) -> None:
        r = self._selected_row()
        start = self._table.item(r, 1).text() if r >= 0 else ""
        chosen = QFileDialog.getExistingDirectory(self, i18n.KO.DEV_BROWSE_TITLE, start or "",
                                                  QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks)
        if not chosen:
            return
        chosen = os.path.normpath(chosen)
        if r < 0:
            r = self.add_row()
        p = prefs.load()
        if os.path.isdir(os.path.join(chosen, p.report_dir or "Report")):   # 장비 폴더를 골랐다
            self._table.item(r, 1).setText(os.path.dirname(chosen) or chosen)
            self._table.item(r, 2).setText(os.path.basename(chosen))
            if not self._table.item(r, 0).text():
                self._table.item(r, 0).setText(os.path.basename(chosen))
        else:                                                              # 공유(장비 폴더들의 부모)를 골랐다
            self._table.item(r, 1).setText(chosen)
            self._table.item(r, 2).setText(devices_mod.AUTO)

    def import_csv(self) -> None:
        fn, _ = QFileDialog.getOpenFileName(self, i18n.KO.BTN_IMPORT_CSV, "", i18n.KO.DEV_CSV_FILTER)
        if not fn:
            return
        rows = devices_mod.read_devices_csv(fn)
        for row in rows:
            self.add_row(row)
        self.message.emit(i18n.KO.DEV_IMPORTED_FMT.format(n=len(rows)))

    def export_csv(self) -> None:
        fn, _ = QFileDialog.getSaveFileName(self, i18n.KO.BTN_EXPORT_CSV, "devices.csv", i18n.KO.DEV_CSV_FILTER)
        if not fn:
            return
        rows = self.rows()
        try:
            devices_mod.write_devices_csv(fn, rows)
        except nas_guard.NasWriteRefused as exc:
            self.error.emit(i18n.KO.COLLECT_OUTPUT_ON_NAS_TITLE, str(exc))

    def check_connections(self) -> None:
        rows = self.rows()
        for r in range(self._table.rowCount()):
            self._table.item(r, 5).setText(i18n.KO.DEV_STATUS_CHECKING)
        self._check_token += 1
        p = prefs.load()
        # 수집 범위(scope)까지 들어간 cfg 를 그대로 쓴다 — 범위 밖 행은 연결 확인도 하지 않는다
        w = _CheckWorker(self._check_token, rows, prefs.to_collect_cfg(p), self)
        w.result.connect(self._on_checked)
        self._checker = w
        w.start()

    def _on_checked(self, token: int, rows) -> None:
        if token != self._check_token:
            return
        for r, row in enumerate(rows):
            if r >= self._table.rowCount():
                break
            st = str(row.get("status", ""))
            if st.startswith("auto:"):
                text = i18n.KO.DEV_STATUS_AUTO_FMT.format(n=st.split(":")[1])
            else:
                text = _STATUS_TEXT.get(st, st)
            self._table.blockSignals(True)
            self._table.item(r, 5).setText(text)
            self._table.blockSignals(False)
