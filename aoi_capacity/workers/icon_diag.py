"""바로가기 아이콘 진단 워커(11/4 임시) — `aoi_capacity.icon_diag.run` 을 QThread 에서 부른다. 문제가 풀리면 카드와 함께 지운다."""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from .. import i18n, icon_diag, nas_guard

K = i18n.KO


class IconDiagWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(object, str)      # 결과 dict(zip · report · local_dir · share_dir · summary) | None, 오류 문구

    def __init__(self, cfg: dict, parent=None):
        super().__init__(parent)
        self.cfg = cfg

    def run(self) -> None:  # noqa: D401
        try:
            self.done.emit(icon_diag.run(self.cfg, log=self.log.emit), "")
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(None, str(ex))
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, K.ICON_DIAG_FAIL_FMT.format(error=f"{type(ex).__name__}: {ex}"))
