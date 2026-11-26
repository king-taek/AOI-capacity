"""속도 시험 워커(11/25) — `aoi_capacity.perf_test.run` 을 QThread 에서 부른다(UI 스레드 밖, 규칙 9).

캐시만 읽고 장비 NAS 는 건드리지 않으며, 저장 위치는 `run` 이 시작 전에 `nas_guard.assert_local` 로 확인한다(규칙 1).
멈춤은 HTML 한 장을 다 만든 뒤마다 · LOT 시험 결과를 기다리는 동안 확인한다(한 장을 만드는 중간에는 끊지 않는다).
LOT 시험 파일 두 장은 이 스레드에서 `perf_test.open_in_browser`(표준 `os.startfile`/`webbrowser` — Qt 호출 아님)로 연다(11/26 단추 하나)."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal

from .. import i18n, nas_guard, perf_test

K = i18n.KO


class PerfTestWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str)
    done = pyqtSignal(object, str)      # 결과 dict(dir · summary · result · same · stopped) | None, 오류 문구

    def __init__(self, cfg: dict, out_root: str = "", parent=None):
        super().__init__(parent)
        self.cfg, self.out_root = cfg, out_root
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # noqa: D401
        try:
            result = perf_test.run(self.cfg, self.out_root, log=self.log.emit, progress=self.progress.emit,
                                   should_stop=self._stop.is_set, browser=perf_test.open_in_browser)
            self.done.emit(result, "")
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(None, str(ex))
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, K.PERF_FAIL_FMT.format(error=f"{type(ex).__name__}: {ex}"))
