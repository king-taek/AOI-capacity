"""공유 폴더 시험 워커 — `scripts/share_probe.py` 를 QThread 에서 부른다(10/24, 사용자: bat 이 회사 PC 에서 지워져 수집 창 버튼으로).

- 도구 본체는 표준 라이브러리 단독 스크립트다(`share_probe.bat` 로도 돈다). 같은 코드를 **파일 경로로 불러** 쓴다 —
  배포 payload 에 들어 있다(`updater._UPDATE_KEEP_ONLY`).
- 세 가지 일: `probe`(1~5 시험 · 결과 JSON) · `hammer`(교체 시험 — 팀원이 '교체 중 열기' 를 누르는 동안) · `clean`(도구가 만든 파일만 지움).
- 쓰기는 도구가 `<공유 폴더>\\_aoi_share_probe\\` 안과 로컬 결과 폴더에만 한다. 공유 폴더가 장비 NAS 아래이거나 같은 공유면
  도구가 멈춘다(devices.csv 기준). 이 워커도 시작 전에 `nas_guard.assert_local` 로 장비 경로 아래가 아닌지 한 번 더 본다(규칙 1).
- 장비 NAS 는 읽지 않으므로 가동률 수집과 서로 막지 않는다.
"""
from __future__ import annotations

import importlib.util
import threading
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .. import i18n, nas_guard
from ..utils import paths

K = i18n.KO
TOOL_PATH = Path(__file__).resolve().parents[2] / "scripts" / "share_probe.py"
#: 이 워커가 부르는 도구의 호출 방식 판(스크립트의 TOOL_API 와 같거나 커야 한다).
TOOL_API = 2
HAMMER_SEC = 300
JOBS = ("probe", "hammer", "clean")


class ToolOutdated(RuntimeError):
    """도구 파일이 옛 판이다(parse_args 없음)."""


def load_tool(path: Path = TOOL_PATH):
    """도구 스크립트를 모듈로 불러온다(없으면 FileNotFoundError)."""
    if not Path(path).is_file():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location("aoi_share_probe", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if getattr(mod, "TOOL_API", 0) < TOOL_API or not callable(getattr(mod, "parse_args", None)):
        raise ToolOutdated(str(path))
    return mod


def default_target() -> str:
    """도구 파일 맨 위 TARGET(사용자가 고치는 값) — 못 읽으면 빈 칸."""
    try:
        return str(load_tool().TARGET)
    except Exception:  # noqa: BLE001
        return ""


def result_dir() -> Path:
    """결과 JSON 폴더 — 도구 기본값과 같은 곳(앱 데이터 폴더 아래)."""
    return paths.data_root() / "share_probe"


class ShareProbeWorker(QThread):
    log = pyqtSignal(str)
    done = pyqtSignal(str, object, str)     # 일(job), 결과 dict | None, 오류 문구

    def __init__(self, cfg: dict, job: str, target: str, parent=None, tool_path: Path = TOOL_PATH,
                 out_dir: str = "", devices_csv: str = "", extra_args=()):
        super().__init__(parent)
        if job not in JOBS:
            raise ValueError(job)
        self.cfg, self.job, self.target, self.tool_path = cfg, job, target, Path(tool_path)
        self.out_dir = out_dir or str(result_dir())
        self.devices_csv = devices_csv or str(paths.devices_csv_path())
        self.extra_args = list(extra_args)
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:  # noqa: D401
        try:
            if not self.target.strip():
                self.done.emit(self.job, None, K.SHARE_PROBE_NO_TARGET)
                return
            roots = nas_guard.roots_for_cfg(self.cfg)
            nas_guard.assert_local(self.target, roots)
            nas_guard.assert_local(self.out_dir, roots)
            try:
                tool = load_tool(self.tool_path)
            except FileNotFoundError:
                self.done.emit(self.job, None, K.SHARE_PROBE_NO_TOOL_FMT.format(path=self.tool_path))
                return
            except ToolOutdated:
                self.done.emit(self.job, None, K.SHARE_PROBE_OLD_TOOL_FMT.format(path=self.tool_path))
                return
            argv = ["--target", self.target, "--devices", self.devices_csv, "--out", self.out_dir, "--yes", *self.extra_args]
            if self.job == "hammer":
                argv += ["--hammer", str(HAMMER_SEC)]
            args = tool.parse_args(argv)
            out = Path(self.out_dir)
            if self.job == "clean":
                gone = tool.Probe(args.target).clean()
                self.done.emit(self.job, {"gone": gone}, "")
                return
            if self.job == "hammer":
                if not Path(args.devices).is_file():
                    raise tool.Refused(K.SHARE_PROBE_NO_DEVICES_FMT.format(path=args.devices))
                tool.check_target(args.target, [(n, f) for n, f, _o, _s in tool.read_devices(Path(args.devices))])
                res = tool.hammer(args, log=self.log.emit, should_stop=self._stop.is_set)
                res["saved"] = str(tool._save({"target": args.target, **res}, out, args.target, log=self.log.emit))
                self.done.emit(self.job, res, "")
                return
            res = tool.run(args, log=self.log.emit)
            res["saved"] = str(tool._save(res, out, args.target, log=self.log.emit))
            self.done.emit(self.job, res, "")
        except nas_guard.NasWriteRefused as ex:
            self.done.emit(self.job, None, str(ex))
        except Exception as ex:  # noqa: BLE001
            name = type(ex).__name__
            fmt = K.SHARE_PROBE_REFUSED_FMT if name == "Refused" else K.SHARE_PROBE_FAIL_FMT
            self.done.emit(self.job, None, fmt.format(error=str(ex) if name == "Refused" else f"{name}: {ex}"))
