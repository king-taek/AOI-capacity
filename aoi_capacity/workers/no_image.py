"""No image 점검 워커(10/22) — `aoi_capacity.no_image.run` 을 QThread 에서 부른다.

장비 확인은 수집과 같은 게이트(`devices.resolve_devices`)를 지나므로 범위 밖 장비에는 접근하지 않고,
저장 위치는 시작 전에 `nas_guard.assert_local` 로 확인한다(규칙 1). 멈춤은 Wafer 사이마다 확인한다."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal

from .. import i18n, nas_guard, no_image

K = i18n.KO


class NoImageWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(object, str)      # 결과 dict(path · items · days · out_dir) | None, 오류 문구

    def __init__(self, cfg: dict, days: int, out_dir: str, parent=None):
        super().__init__(parent)
        self.cfg, self.days, self.out_dir = cfg, days, out_dir
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # noqa: D401
        try:
            result = no_image.run(self.cfg, self.days, self.out_dir, log=self.log.emit, should_stop=self._stop.is_set)
            self.done.emit(result, "")
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(None, str(ex))
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, K.NO_IMAGE_FAIL_FMT.format(error=f"{type(ex).__name__}: {ex}"))
