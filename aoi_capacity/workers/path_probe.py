"""배포 경로 자동 시험 워커(10/30 임시) — `aoi_capacity.path_probe.run` 을 QThread 에서 부른다.

쓰기는 공유 폴더의 시험 하위 폴더와 이 PC 의 결과 zip 뿐이고, 장비 NAS 아래면 시작 전에 거부된다(규칙 1)."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal

from .. import i18n, nas_guard, path_probe

K = i18n.KO


class PathProbeWorker(QThread):
    log = pyqtSignal(str)
    step = pyqtSignal(str)              # 지금 하는 검사 이름
    done = pyqtSignal(object, str)      # 결과 dict(path · ok · failed · total · stopped) | None, 오류 문구

    def __init__(self, cfg: dict, out_dir: str, parent=None):
        super().__init__(parent)
        self.cfg, self.out_dir = cfg, out_dir
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # noqa: D401
        try:
            result = path_probe.run(self.cfg, self.out_dir, log=self.log.emit, progress=self.step.emit, should_stop=self._stop.is_set)
            self.done.emit(result, "")
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(None, str(ex))
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, K.TEST_PATH_FAIL_FMT.format(error=f"{type(ex).__name__}: {ex}"))
