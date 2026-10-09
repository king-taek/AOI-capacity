"""Wafer 폴더 로그 모으기 워커 — `scripts/collect_wafer_logs.py` 의 `run()` 을 QThread 에서 부른다(10/9).

- 도구 본체는 표준 라이브러리 단독 스크립트 하나다(현장에서 `make_wafer_logs.bat` 로도 돈다). 같은 코드를 **파일 경로로 불러** 쓴다 —
  배포 payload 에 들어 있다(`updater._UPDATE_KEEP_ONLY`).
- 장비는 가동률 수집과 **같은 게이트**(`devices.resolve_devices` — 범위 · 설정 검사)를 지난 Camtek 장비만 넘긴다. KLA · 범위 밖은 넘기지 않는다(규칙 2).
- 저장 위치는 시작 전에 `nas_guard.assert_local` 로 확인한다(규칙 1). 도구도 NAS 드라이브면 스스로 거부한다.
- 멈춤은 `stop()` — 도구가 Lot · 파일 사이마다 확인해 담던 Lot 은 버리고 지금까지 담은 것으로 zip 을 마무리한다.
"""
from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .. import devices, i18n, nas_guard

K = i18n.KO
TOOL_PATH = Path(__file__).resolve().parents[2] / "scripts" / "collect_wafer_logs.py"


def load_tool(path: Path = TOOL_PATH):
    """도구 스크립트를 모듈로 불러온다(없으면 FileNotFoundError)."""
    if not Path(path).is_file():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location("aoi_collect_wafer_logs", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def default_out_dir() -> str:
    """도구 파일 맨 위 OUT_DIR(사용자가 고치는 값) — 못 읽으면 바탕화면 아래 폴더."""
    try:
        return str(load_tool().OUT_DIR)
    except Exception:  # noqa: BLE001
        return str(Path.home() / "Desktop" / "AOI_wafer_logs")


class WaferLogsWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(object, str)      # 결과 dict(out_dir · parts · summary · lots · stop_why) | None, 오류 문구

    def __init__(self, cfg: dict, out_dir: str, parent=None, tool_path: Path = TOOL_PATH, extra_args=()):
        super().__init__(parent)
        self.cfg, self.out_dir, self.tool_path, self.extra_args = cfg, out_dir, Path(tool_path), list(extra_args)
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # noqa: D401
        try:
            nas_guard.assert_local(self.out_dir, nas_guard.roots_for_cfg(self.cfg))
            try:
                tool = load_tool(self.tool_path)
            except FileNotFoundError:
                self.done.emit(None, K.WAFER_LOGS_NO_TOOL_FMT.format(path=self.tool_path))
                return
            devs = devices.resolve_devices(self.cfg, log=self.log.emit, should_stop=self._stop.is_set)
            roots = [str(d["path"]) for d in devs if d.get("kind") != "kla"]
            if self._stop.is_set():
                self.done.emit(None, K.WAFER_LOGS_STOPPED)
                return
            if not roots:
                self.done.emit(None, K.WAFER_LOGS_NO_DEVICES)
                return
            result: dict = {}
            args = tool.parse_args(["--roots", *roots, "--out", self.out_dir, *self.extra_args])
            tool.run(args, log=self.log.emit, should_stop=self._stop.is_set, result=result)
            if result.get("parts"):
                self.done.emit(result, "")
            else:
                self.done.emit(None, K.WAFER_LOGS_STOPPED if self._stop.is_set() else
                               K.WAFER_LOGS_NO_ZIP)
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(None, str(ex))
        except Exception as ex:  # noqa: BLE001
            self.done.emit(None, K.WAFER_LOGS_FAIL_FMT.format(error=f"{type(ex).__name__}: {ex}"))
