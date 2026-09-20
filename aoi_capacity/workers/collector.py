"""수집 워커 — `collect.collect()` + `collect.write_html()` 을 QThread 에서 돌린다.

- 모든 시그널은 생성 시 받은 `token` 을 같이 보낸다. MainWindow 는 자기 토큰과 다르면(늦게 온 옛 실행) 무시한다.
- 취소는 `stop()`(threading.Event). 코어가 Report 사이마다 확인해 `CollectCancelled` 로 빠져나오며, 캐시·HTML 은 그대로다.
- 테스트는 스레드를 띄우지 않고 `run()` 을 직접 부른다(dev/tests/test_collector_worker.py).
- 수집 상태와 산출물 상태는 다르다(C06): HTML 을 썼는데 CSV 만 못 썼으면 `done` 으로 끝내되 `CollectResult.state` 가
  `completed_with_warnings` 이고 `warnings` 에 사유가 있다. 사용자 문구는 `warning_lines`(ko.py) 로 만든다.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import List

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .. import collect, i18n

STATE_COMPLETED, STATE_COMPLETED_WITH_WARNINGS = "completed", "completed_with_warnings"


@dataclass
class CollectResult:
    rows: int
    devices: int
    dev_meta: List[dict] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    html_path: str = ""
    elapsed: float = 0.0
    warnings: List[dict] = field(default_factory=list)   # write_html 의 부가 산출물 경고(CSV 잠김 등) + 캐시 손상 안내
    cache_status: str = collect.CACHE_OK                 # ok · missing · corrupt(원본은 .bad-<시각> 으로 보존됨)

    @property
    def state(self) -> str:
        return STATE_COMPLETED_WITH_WARNINGS if self.warnings else STATE_COMPLETED

    @property
    def warning_lines(self) -> List[str]:
        """사용자에게 보여 줄 경고 문장들(ko.py). 종류를 모르는 경고는 원문 오류를 그대로 보여 준다."""
        out = []
        for w in self.warnings:
            if w.get("kind") == collect.WARN_CSV:
                out.append(i18n.KO.COLLECT_DONE_CSV_FAILED_FMT.format(path=w.get("path", ""), error=w.get("error", "")))
            elif w.get("kind") == "cache":
                out.append(i18n.KO.COLLECT_CACHE_CORRUPT_FMT.format(path=w.get("path", "")))
            else:
                out.append(str(w.get("error") or w))
        return out

    @property
    def bad_devices(self) -> List[dict]:
        """접근하지 못한 장비(목록 조회 실패)."""
        return [d for d in self.dev_meta if d.get("error")]

    @property
    def unreachable_devices(self) -> List[str]:
        return [str(d["name"]) for d in self.bad_devices]

    @property
    def partial_devices(self) -> List[str]:
        """접근은 됐지만 Report 일부를 읽지 못한 장비 — '완료' 로 뭉개면 안 된다."""
        return [str(d["name"]) for d in self.dev_meta if not d.get("error") and d.get("read_errors")]


class CollectorSignals(QObject):
    progress = pyqtSignal(int, int, int, str)   # token, done, total, phase
    device = pyqtSignal(int, str, str, str)     # token, name, state, detail
    log = pyqtSignal(int, str)                  # token, line
    done = pyqtSignal(int, object)              # token, CollectResult
    failed = pyqtSignal(int, str)               # token, message
    cancelled = pyqtSignal(int)                 # token


class CollectorWorker(QThread):
    def __init__(self, token: int, cfg: dict, *, full: bool = False, backfill: bool = False, recover: bool = False,
                 refresh_window_days=None, rebuild_all=None, parent=None):
        super().__init__(parent)
        self.token = token
        self.cfg = cfg
        self.full = full
        self.backfill = backfill
        self.recover = recover
        self.refresh_window_days = refresh_window_days   # None 이면 cfg["refresh_window_days"](prefs 에서 옴)
        self.rebuild_all = rebuild_all                   # None 이면 cfg["rebuild_all"]; full 은 그 별칭
        self.signals = CollectorSignals()
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def is_cancelled(self) -> bool:
        return self._stop.is_set()

    def run(self) -> None:  # noqa: D401
        tok = self.token
        started = time.time()
        stats: dict = {}
        warnings: List[dict] = []
        try:
            rows, dev_meta, errors = collect.collect(
                self.cfg, self.full, self.backfill, recover=self.recover,
                refresh_window_days=self.refresh_window_days, rebuild_all=self.rebuild_all,
                progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)),
                log=lambda m: self.signals.log.emit(tok, str(m)),
                should_stop=self._stop.is_set,
                on_device=lambda n, s, d: self.signals.device.emit(tok, str(n), str(s), str(d)),
                stats=stats,
            )
            if self._stop.is_set():
                raise collect.CollectCancelled()
            path = collect.write_html(self.cfg, rows, dev_meta, errors, started, mode="gui", timing=stats, warnings=warnings,
                                      log=lambda m: self.signals.log.emit(tok, str(m)),
                                      progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)))
        except collect.CollectCancelled:
            self.signals.cancelled.emit(tok)
            return
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(tok, f"{type(exc).__name__}: {exc}")
            return
        cache_status = str(stats.get("cache_status") or collect.CACHE_OK)
        if cache_status == collect.CACHE_CORRUPT:
            warnings.append({"kind": "cache", "path": str(stats.get("cache_preserved") or self.cfg.get("cache_file") or "")})
        result = CollectResult(rows=len(rows), devices=len(dev_meta), dev_meta=dev_meta, errors=errors, html_path=path,
                               elapsed=time.time() - started, warnings=warnings, cache_status=cache_status)
        for line in result.warning_lines:                 # 로그에도 남긴다 — 시트를 닫아도 사유가 보이게
            self.signals.log.emit(tok, line)
        self.signals.done.emit(tok, result)
