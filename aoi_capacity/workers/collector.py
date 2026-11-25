"""수집 워커 — `collect.collect()` + `collect.write_html()` 을 QThread 에서 돌린다.

- 모든 시그널은 생성 시 받은 `token` 을 같이 보낸다. MainWindow 는 자기 토큰과 다르면(늦게 온 옛 실행) 무시한다.
- 취소는 `stop()`(threading.Event). 코어가 바로 `CollectCancelled` 로 빠져나오며 읽은 것까지 캐시에 저장하고(10/11, 이어하기), HTML 은 만들지 않는다.
- 테스트는 스레드를 띄우지 않고 `run()` 을 직접 부른다(dev/tests/test_collector_worker.py).
- 수집 상태와 산출물 상태는 다르다(C06): HTML 을 썼는데 CSV 만 못 썼으면 `done` 으로 끝내되 `CollectResult.state` 가
  `completed_with_warnings` 이고 `warnings` 에 사유가 있다. 사용자 문구는 `warning_lines`(ko.py, 로그용) · `outcome_items`(수집 카드 알림) 로 만든다.
- 11/25: 결과 HTML 뒤의 배포는 `progress` 로 '공유 폴더에 올리는 중 1/2' 를 알리고, 중지를 누르면 아직 시작 안 한 배포는 건너뛴다(`phase` 가
  "publish" 인 동안 창을 닫으면 MainWindow 가 기다릴지 묻는다). 실패하면 `failure`(종류 · 단계 · 원문)를 채운 뒤 `failed` 를 보낸다 —
  화면은 종류로 쉬운 문장과 다음 행동을 고르고 원문은 '자세히' 와 로그에만 둔다(CORE-10 · QT-15).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import List

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from .. import collect, i18n, nas_guard, publish
from ..utils.config import ConfigError

STATE_COMPLETED, STATE_COMPLETED_WITH_WARNINGS = "completed", "completed_with_warnings"
#: 실패 종류 — html: 캐시까지 저장했고 결과 HTML 만 못 씀 · config: 설정 · nas: 장비 NAS 아래에 쓰려 함 · rebuild: 재구축 검증 실패 · io: 파일/네트워크 · other
FAIL_KINDS = ("html", "config", "nas", "rebuild", "io", "other")


def failure_kind(exc: BaseException, stage: str) -> str:
    if isinstance(exc, ConfigError):
        return "config"
    if isinstance(exc, nas_guard.NasWriteRefused):
        return "nas"
    if stage == "html":
        return "html"
    if isinstance(exc, collect.RebuildRejected):
        return "rebuild"
    if isinstance(exc, OSError):
        return "io"
    return "other"


def _publish_why(why: str) -> str:
    K = i18n.KO
    return {publish.WHY_UNREACHABLE: K.PUBLISH_WHY_UNREACHABLE, publish.WHY_DENIED: K.PUBLISH_WHY_DENIED,
            publish.WHY_LOCKED: K.PUBLISH_WHY_LOCKED}.get(why, "")


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
    published_full: str = ""                             # 전체 배포를 올린 폴더(끝까지 올렸을 때만, 10/30)
    published: str = ""                                  # LOT 추적을 올린 배포 폴더(끝까지 올렸을 때만, 10/30) — 꺼짐이거나 실패면 빈 값

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
            elif w.get("kind") == "publish":
                out.append(i18n.KO.COLLECT_DONE_PUBLISH_FAILED_FMT.format(path=w.get("path", ""), error=w.get("error", "")))
            elif w.get("kind") == "publish_locked":
                out.append(i18n.KO.COLLECT_DONE_PUBLISH_LOCKED_FMT.format(path=w.get("path", "")))
            elif w.get("kind") == "publish_full":
                out.append(i18n.KO.COLLECT_DONE_PUBLISH_FULL_FAILED_FMT.format(path=w.get("path", ""), error=w.get("error", "")))
            elif w.get("kind") == "publish_full_locked":
                out.append(i18n.KO.COLLECT_DONE_PUBLISH_FULL_LOCKED_FMT.format(path=w.get("path", "")))
            else:
                out.append(str(w.get("error") or w))
        return out

    @property
    def outcome_items(self) -> List[dict]:
        """수집 카드 알림 항목(11/25 QT-16 · PP-04) — 문제마다 {head, desc, action, tip}. action ∈ devices · log · republish · "".
        배포 실패는 이유 종류로 짧은 문장을 고르고(원문은 로그에만), 두 배포가 같은 이유면 한 항목으로 묶는다."""
        K = i18n.KO
        items: List[dict] = []
        pub = {}
        for w in self.warnings:
            kind = w.get("kind")
            if kind == collect.WARN_CSV:
                items.append({"head": K.OUTCOME_CSV_HEAD, "desc": K.OUTCOME_CSV_DESC, "action": "", "tip": f"{w.get('path', '')}\n{w.get('error', '')}"})
            elif kind == "cache":
                items.append({"head": K.OUTCOME_CACHE_HEAD, "desc": K.OUTCOME_CACHE_DESC_FMT.format(path=w.get("path", "")), "action": "", "tip": ""})
            elif kind in ("publish", "publish_full"):
                pub.setdefault(("fail", w.get("why") or ""), []).append(w)
            elif kind in ("publish_locked", "publish_full_locked"):
                pub.setdefault(("locked", ""), []).append(w)
            else:
                items.append({"head": str(w.get("error") or w), "desc": "", "action": "log", "tip": ""})
        what = lambda ws: K.OUTCOME_WHAT_JOIN.join(K.PUBLISH_WHAT_FULL if w["kind"].startswith("publish_full") else K.PUBLISH_WHAT_LOT for w in ws)
        for (state, why), ws in pub.items():
            tip = "\n".join(str(w.get("path", "")) for w in ws)
            if state == "locked":
                items.append({"head": K.OUTCOME_PUBLISH_LOCKED_HEAD_FMT.format(what=what(ws)), "desc": K.OUTCOME_PUBLISH_LOCKED_DESC, "action": "", "tip": tip})
            else:
                desc = _publish_why(why) or (str(ws[0].get("error", "")) if why == publish.WHY_CONFIG else K.PUBLISH_WHY_OTHER)
                items.append({"head": K.OUTCOME_PUBLISH_HEAD_FMT.format(what=what(ws)), "desc": desc,
                              "action": "" if why == publish.WHY_CONFIG else "republish", "tip": tip,
                              "kinds": ["full" if w["kind"].startswith("publish_full") else "lot" for w in ws]})
        unreachable, partial = self.unreachable_devices, self.partial_devices
        if unreachable:
            items.append({"head": K.OUTCOME_UNREACHABLE_HEAD_FMT.format(n=len(unreachable), names=", ".join(unreachable)),
                          "desc": K.COLLECT_DONE_UNREACHABLE_HINT, "action": "devices", "tip": ""})
        if partial:
            items.append({"head": K.OUTCOME_PARTIAL_HEAD_FMT.format(n=len(partial), names=", ".join(partial)),
                          "desc": K.OUTCOME_PARTIAL_DESC_FMT.format(reports=len(self.errors)), "action": "log", "tip": ""})
        elif self.errors and not items:
            items.append({"head": K.COLLECT_DONE_SEE_LOG, "desc": "", "action": "log", "tip": ""})
        return items

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
                 refresh_window_days=None, rebuild_all=None, refresh_range=None, rdl_patch=False, parent=None):
        super().__init__(parent)
        self.token = token
        self.cfg = cfg
        self.full = full
        self.backfill = backfill
        self.recover = recover
        self.refresh_window_days = refresh_window_days   # None 이면 cfg["refresh_window_days"](prefs 에서 옴)
        self.rebuild_all = rebuild_all                   # None 이면 cfg["rebuild_all"]; full 은 그 별칭
        self.rdl_patch = rdl_patch                       # 수집 창 'RDL 영역 INI 패치'(10/5)
        self.refresh_range = refresh_range               # ("YYYY-MM-DD", "YYYY-MM-DD") — 수집 창 '기간 다시 읽기'(10/5)
        self.signals = CollectorSignals()
        self._stop = threading.Event()
        self.phase = "collect"                           # collect → html → publish → done (창을 닫을 때 MainWindow 가 본다)
        self.failure: dict = {}                          # 실패했으면 {kind, stage, detail}

    def stop(self) -> None:
        self._stop.set()

    def is_cancelled(self) -> bool:
        return self._stop.is_set()

    def run(self) -> None:  # noqa: D401
        tok = self.token
        started = time.time()
        stats: dict = {}
        warnings: List[dict] = []
        stage = "collect"
        try:
            rows, dev_meta, errors = collect.collect(
                self.cfg, self.full, self.backfill, recover=self.recover,
                refresh_window_days=self.refresh_window_days, rebuild_all=self.rebuild_all, refresh_range=self.refresh_range, rdl_patch=self.rdl_patch,
                progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)),
                log=lambda m: self.signals.log.emit(tok, str(m)),
                should_stop=self._stop.is_set,
                on_device=lambda n, s, d: self.signals.device.emit(tok, str(n), str(s), str(d)),
                stats=stats,
            )
            if self._stop.is_set():
                raise collect.CollectCancelled()
            stage = self.phase = "html"
            prep = collect.HtmlPrep(rows)                  # 수집 HTML · 배포판이 같은 준비를 한 번만(PH-01)
            path = collect.write_html(self.cfg, rows, dev_meta, errors, started, mode="gui", timing=stats, warnings=warnings, prep=prep,
                                      log=lambda m: self.signals.log.emit(tok, str(m)),
                                      progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)))
            pub: dict = {}
            stage = self.phase = "publish"
            publish.publish_after_collect(self.cfg, rows, dev_meta, log=lambda m: self.signals.log.emit(tok, str(m)), status=pub, params_store=stats.get("params_store"),
                                          progress=lambda d, t, p: self.signals.progress.emit(tok, int(d), int(t), str(p)),
                                          should_stop=self._stop.is_set, prep=prep)   # 10/27: 조용히 — 실패해도 수집은 성공. 11/25: 단계를 알리고 중지면 남은 배포는 건너뜀
            self.phase = "done"
            if pub.get("error"):                       # 10/30: 조용히 실패해도 수집이 끝났을 때 알림 카드에는 보인다
                warnings.append({"kind": "publish", "path": pub.get("dir", ""), "error": pub["error"], "why": pub.get("why", "")})
            elif pub.get("locked"):
                warnings.append({"kind": "publish_locked", "path": pub.get("dir", "")})
            if pub.get("full_error"):                  # 10/30: 전체 배포도 같은 방식 — 실패해도 수집은 성공, 알림 카드에만
                warnings.append({"kind": "publish_full", "path": pub.get("full_dir", ""), "error": pub["full_error"], "why": pub.get("full_why", "")})
            elif pub.get("full_locked"):
                warnings.append({"kind": "publish_full_locked", "path": pub.get("full_dir", "")})
        except collect.CollectCancelled:
            saved = stats.get("cancel_saved")
            if saved:
                self.signals.log.emit(tok, i18n.KO.COLLECT_CANCELLED_SAVED_FMT.format(n=saved))
            self.signals.cancelled.emit(tok)
            return
        except Exception as exc:  # noqa: BLE001
            detail = f"{type(exc).__name__}: {exc}"
            self.failure = {"kind": failure_kind(exc, stage), "stage": stage, "detail": detail}
            self.signals.failed.emit(tok, detail)
            return
        cache_status = str(stats.get("cache_status") or collect.CACHE_OK)
        if cache_status == collect.CACHE_CORRUPT:
            warnings.append({"kind": "cache", "path": str(stats.get("cache_preserved") or self.cfg.get("cache_file") or "")})
        result = CollectResult(rows=len(rows), devices=len(dev_meta), dev_meta=dev_meta, errors=errors, html_path=path,
                               elapsed=time.time() - started, warnings=warnings, cache_status=cache_status,
                               published=str(pub.get("dir", "")) if pub.get("ok") or pub.get("locked") else "",
                               published_full=str(pub.get("full_dir", "")) if pub.get("full_ok") or pub.get("full_locked") else "")
        for line in result.warning_lines:                 # 로그에도 남긴다 — 시트를 닫아도 사유가 보이게
            self.signals.log.emit(tok, line)
        self.signals.done.emit(tok, result)
