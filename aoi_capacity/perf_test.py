"""수집 창 '속도 시험'(11/25 — 현택 "시험 진행해줘", "테스트는 수집기에 테스트 버튼 만들어줘").

현택 PC(실데이터)에서 한 번 눌러 결과 폴더를 그대로 보내면 되게 한다. 시험하는 것:

- **PH-01 · PH-03**(수집 끝 HTML 3장 · 기간 자르기): 가진 데이터(캐시)로 기본 · LOT 배포판 · 전체 배포판 세 장을
  (가) 예전처럼 장마다 따로(`write_html(prep=None)` — 장마다 날짜 해석 · 기간 자르기 · 접기를 처음부터)
  (나) 지금처럼 `collect.HtmlPrep` 하나를 나눠 쓰며 만들어 단계별 시간(준비 · 기간 자르기 · 접기 · JSON · 쓰기 · CSV)과
  **세 장이 바이트까지 같은지**(생성 시각 · 걸린 시간 칸만 빼고 sha256)를 적는다. 배포판은 공유 폴더가 아니라 시험 폴더에
  HTML 만 만든다(바로가기 · latest.js 없이 — 배포가 부르는 `write_html` 인자 그대로).
- **LOTD-01**(LOT 배포판이 쓰지 않는 가동률 · Error 모델 계산): 같은 LOT 배포판을 두 장(`LOT_지금.html` · `LOT_계산건너뜀.html`)
  만든다. 둘 다 `meta.selftest` — 열리면 스스로 LOT 화면을 눌러 보고 맨 위 띠에 '열기 n.n초 · 자동 점검 m가지 · 오류 k개'.
  두 번째만 `meta.lot_skip_model`(모델 계산을 건너뛰는 시험 길). 제품 배포판에는 두 표식이 없다.
- **단추 하나로 끝까지**(11/26 현택 "시험들 메인브랜치에 넣어줘 · 단일버튼으로"): `browser` 를 주면(수집 창 워커) 두 장을 **기본 브라우저로
  차례로** 연다(이 스레드에서 표준 `os.startfile`/`webbrowser` — Qt 호출 없음). 시험 파일은 자가 점검이 끝나면 결과를 blob 으로
  `aoi_perf_<토큰>_<now|skip>.json` 한 장 내려받는다(바깥 요청 아님). 토큰은 실행마다 새로 만든 무작위 값(`meta.selftest_token`) —
  다운로드 폴더(`recipes.download_dirs`)에서 그 이름만 기다렸다(파일마다 `LOT_WAIT_SEC`, 멈춤 존중) 시험 폴더로 옮기고 요약에 숫자를 적는다.
  못 받으면 요약에 '노란 띠 숫자를 보내 주세요' 한 줄.

★ 장비 NAS 는 한 번도 읽지 않는다(캐시 파일만). 쓰기는 이 PC 의 `<데이터 폴더>\\perf_test\\<시각>\\` 아래뿐이고,
이 모듈의 쓰기 함수(`_make_dir` · `_write_text` · `_remove`)는 첫 줄에서 `nas_guard.assert_local` 을 부른다(가드 `test_perf_test.py`).
비교용 HTML 여섯 장(+CSV)은 크기가 커서(실데이터 한 장 40~110MB) 해시를 적은 뒤 지운다.
요약 파일의 글은 이 모듈에 둔다(파일 내용 — `failures.py` 의 요약과 같은 취급). 화면 문구는 `i18n/ko.py`."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import secrets
import time
import webbrowser
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import collect, i18n, nas_guard, recipes
from .utils import config as config_mod
from .utils import paths

K = i18n.KO
LogFn = Callable[[str], None]

LOT_NOW_NAME = "LOT_지금.html"
LOT_SKIP_NAME = "LOT_계산건너뜀.html"
SUMMARY_NAME = "요약.txt"
#: 시험 파일이 내려받는 결과의 이름 — 브라우저가 같은 이름이 있으면 ' (1)' 을 붙이므로 기다릴 때는 접두로 찾는다
DOWNLOAD_FMT = "aoi_perf_{token}_{name}.json"
LOT_WAIT_SEC = 180.0         # 파일마다 결과를 기다리는 상한(현택 PC 실데이터 열기 10초 + 자동 점검 몇 초 — 넉넉히)
LOT_POLL_SEC = 0.5
#: (파일 이름, 결과 이름, meta 표식) — 차례로 연다(동시에 열면 두 탭이 CPU 를 나눠 숫자가 흔들린다)
LOT_FILES = ((LOT_NOW_NAME, "now", {}), (LOT_SKIP_NAME, "skip", {"lot_skip_model": True}))
LOT_LABELS = {"now": "지금", "skip": "계산 건너뜀"}
RESULT_NAME = "결과.json"
STAGES = ("prep", "range", "params", "fold", "json", "write", "csv")
STAGE_LABELS = {"prep": "준비", "range": "기간 자르기", "params": "파라미터", "fold": "접기", "json": "JSON", "write": "쓰기", "csv": "CSV"}
KINDS = (("base", "기본(수집 HTML)"), ("lot", "LOT 배포판"), ("full", "전체 배포판"))
#: 실행마다 달라지는 칸 — 비교할 때만 0 으로 맞춘다(생성 시각 · 걸린 시간). test_html_prep 의 NORM 과 같다.
_NORM_RE = re.compile(rb'"(generated|generated_iso|elapsed|html_ms)":("[^"]*"|\d+)')


class Stopped(Exception):
    """멈춤을 눌렀다 — 지금까지 만든 것만 정리한다."""


def default_root() -> str:
    return str(paths.data_root() / "perf_test")


# ── 쓰기(이 모듈에서 쓰는 곳은 이 셋뿐 — 첫 줄 assert_local) ─────────────────────────
def _make_dir(path: str, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.makedirs(path, exist_ok=True)


def _write_text(path: str, text: str, roots: List[str], *, bom: bool = False) -> None:
    nas_guard.assert_local(path, roots)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8", newline="\r\n" if bom else "\n") as f:
        f.write(text)


def _remove(path: str, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    try:
        os.remove(path)
    except OSError:
        pass


def _move(src: str, dst: str, roots: List[str]) -> None:
    """다운로드 폴더의 시험 결과 한 장을 시험 폴더로(옮기기 — 다른 드라이브면 써 넣고 원본을 지움). 양쪽 다 이 PC 여야 한다."""
    nas_guard.assert_local(dst, roots)
    nas_guard.assert_local(src, roots)
    try:
        os.replace(src, dst)
    except OSError:
        with open(src, "rb") as f:
            data = f.read()
        with open(dst, "wb") as f:
            f.write(data)
        try:
            os.remove(src)
        except OSError:
            pass


def open_in_browser(path: str) -> None:
    """기본 브라우저로 로컬 HTML 한 장을 연다 — 워커 스레드에서 불러도 되는 표준 라이브러리만(Qt 호출 없음, 규칙 3: 로컬 서버 · localhost 없음)."""
    start = getattr(os, "startfile", None)
    if start is not None:          # Windows: 탐색기에서 더블클릭한 것과 같다(.html 연결 프로그램)
        start(path)
        return
    webbrowser.open(Path(path).resolve().as_uri())


def wait_download(token: str, name: str, dirs: List[str], *, timeout: float = LOT_WAIT_SEC, poll: float = LOT_POLL_SEC,
                  should_stop: Optional[Callable[[], bool]] = None, clock: Callable[[], float] = time.monotonic,
                  sleep: Callable[[float], None] = time.sleep) -> Optional[tuple]:
    """다운로드 폴더들에서 `aoi_perf_<token>_<name>*.json` 이 나타나 읽힐 때까지 기다린다 → (경로, 내용) | None(시간 초과).
    읽기만 한다. 반쯤 쓰인 파일(브라우저는 `.crdownload` 로 받다가 이름을 바꾼다 — 그래도 JSON 해석이 실패하면 다음 차례에 다시)과
    토큰이 다른 파일은 건너뛴다. 멈춤이면 `Stopped`."""
    stem = DOWNLOAD_FMT.format(token=token, name=name)[:-len(".json")]
    stop = should_stop or (lambda: False)
    end = clock() + max(0.0, float(timeout))
    while True:
        if stop():
            raise Stopped()
        for d in dirs:
            try:
                names = sorted(n for n in os.listdir(d) if n.startswith(stem) and n.endswith(".json"))
            except OSError:
                continue
            for n in names:
                p = os.path.join(d, n)
                try:
                    with open(p, "rb") as f:
                        data = json.loads(f.read().decode("utf-8-sig"))
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict) and data.get("token") == token and data.get("name") == name:
                    return p, data
        if clock() >= end:
            return None
        sleep(poll)


def _lot_open_result(name: str, file: str, data: Optional[dict]) -> dict:
    """내려받은 결과(template `selfTest` 가 쓴 것)에서 요약에 쓸 값만."""
    if not data:
        return {"name": name, "file": file, "got": False}
    steps = [s for s in (data.get("steps") or []) if isinstance(s, dict)]
    errs = [str(e) for e in (data.get("errors") or [])]
    st = data.get("stages") if isinstance(data.get("stages"), dict) else {}
    return {"name": name, "file": file, "got": True, "open_sec": round(float(data.get("open") or 0) / 1000, 2),
            "lifted_sec": round(float(data.get("lifted") or 0) / 1000, 2), "lite": bool(data.get("lite")),
            "stages_ms": {k: st.get(k) for k in ("parse", "unfold", "model", "first")}, "rows": data.get("rows"),
            "steps": [{"name": str(s.get("name", "")), "ok": bool(s.get("ok")), "ms": s.get("ms"), "note": str(s.get("note") or "")} for s in steps],
            "errors": errs[:50], "browser": str(data.get("ua") or "")[:200]}


# ── 읽기 ────────────────────────────────────────────────────────────────
def load_rows(cfg: dict, log: Optional[LogFn] = None):
    """캐시만 읽어 (행, 장비 meta, 파라미터 묶음) — `collect.html_from_cache` 와 같은 준비(NAS 접근 0)."""
    cache = collect._load_cache(cfg, log=log, dirty=collect._Dirty())   # 규칙이 바뀌었으면 메모리에서만 다시 분류 — 캐시 파일은 그대로
    if not cache["reports"]:
        raise RuntimeError(K.HTML_ONLY_NO_CACHE)
    rows, _hidden = collect._rows_from_cache(cache, collect._DeviceIndex([]), cfg)
    dev_meta = [dict(d) for d in (cache.get("last_devices") or [])]
    names = {str(d.get("name")) for d in dev_meta}
    for n in sorted({str(r.get("device")) for r in rows} - names):
        dev_meta.append({"name": n, "note": "", "report_dir": cfg["report_dir"]})
    for dm in dev_meta:
        dm.setdefault("reports", 0)
        dm.setdefault("found", 0)
        dm.setdefault("error", "")
    collect._mark_device_status(dev_meta, rows)
    return collect.render_issue_rows(rows), dev_meta, cache.get("params") or {}


def file_digest(path: str) -> Dict[str, object]:
    """크기 · sha256(원본) · sha256(생성 시각 · 걸린 시간 칸을 0 으로 맞춘 것 — 두 실행을 비교하는 값)."""
    with open(path, "rb") as f:
        data = f.read()
    norm = _NORM_RE.sub(lambda m: b'"' + m.group(1) + b'":0', data)
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "sha256_norm": hashlib.sha256(norm).hexdigest()}


# ── 실행 ────────────────────────────────────────────────────────────────
def _jobs(cfg: dict, params: dict):
    """수집이 끝날 때 만드는 세 장 — `workers/collector.py`(기본) · `publish._publish`(LOT · 전체)가 `write_html` 에 주는 인자 그대로."""
    full_cfg = dict(cfg, html_days=int(cfg.get("publish_full_days") or 0), write_csv=False)
    return [("base", cfg, dict(mode="gui", params_store=params)),
            ("lot", cfg, dict(mode="publish", lot_only=True, params_store={})),
            ("full", full_cfg, dict(mode="publish", params_store=params))]


def _one(kind: str, cfg: dict, kw: dict, rows, dev_meta, out_dir: str, name: str, prep, roots, log) -> dict:
    st: Dict[str, float] = {}
    warnings: List[dict] = []
    t0 = time.perf_counter()
    path = collect.write_html(cfg, rows, dev_meta, [], time.time(), log=log, out_dir=out_dir, out_name=name, prep=prep,
                              stages=st, warnings=warnings, **kw)
    total = time.perf_counter() - t0
    res = {"kind": kind, "name": name, "total": round(total, 3), "stages": {k: round(float(st.get(k, 0.0)), 3) for k in STAGES}}
    res.update(file_digest(path))
    csv_path = os.path.splitext(path)[0] + ".csv"
    res["csv"] = os.path.isfile(csv_path) and kind == "base"
    if warnings:
        res["warnings"] = [str(w.get("error", w)) for w in warnings]
    for p in (path, csv_path):                       # 비교용 파일은 크다 — 해시를 적었으니 지운다
        if os.path.isfile(p):
            _remove(p, roots)
    return res


def run(cfg: dict, out_root: str = "", *, log: Optional[LogFn] = None,
        progress: Optional[Callable[[int, int, str], None]] = None,
        should_stop: Optional[Callable[[], bool]] = None, now: Optional[dt.datetime] = None,
        browser: Optional[Callable[[str], None]] = None, download_dirs: Optional[List[str]] = None,
        lot_wait_sec: float = LOT_WAIT_SEC) -> dict:
    """시험 한 번 → {"dir", "summary", "result", ...}. 결과 폴더는 `<out_root>\\<YYYYMMDD_HHMMSS>`.

    `browser`(경로 → 열기)를 주면 LOT 시험 파일 두 장을 차례로 열고 결과를 다운로드 폴더(`download_dirs`, 기본
    `recipes.download_dirs()`)에서 받아 온다. 주지 않으면(시험 · CLI) 두 장을 만들기만 하고 요약이 손으로 열어 보라고 적는다."""
    cfg = config_mod.check_or_raise(cfg)
    nas_guard.check_cfg(cfg)
    roots = nas_guard.roots_for_cfg(cfg)
    now = now or dt.datetime.now()
    out = os.path.join(out_root or default_root(), now.strftime("%Y%m%d_%H%M%S"))
    nas_guard.assert_local(out, roots)                # ★ 무엇을 읽기 전에 저장 위치부터
    say = log or (lambda m: None)
    stop = should_stop or (lambda: False)
    steps = 9 + (len(LOT_FILES) if browser else 0)
    tick = (lambda i, what: progress(i, steps, K.PERF_PHASE_FMT.format(i=i, n=steps, what=what))) if progress else (lambda i, what: None)

    def check():
        if stop():
            raise Stopped()

    _make_dir(out, roots)
    tick(0, K.PERF_WHAT_LOAD)
    t0 = time.perf_counter()
    rows, dev_meta, params = load_rows(cfg, log)
    load_s = time.perf_counter() - t0
    memo: Dict[str, str] = {}
    days = sorted({d for d in (collect._row_day(r, memo) for r in rows) if d})
    first, last = (days[0], days[-1]) if days else ("", "")
    say(f"속도 시험: 캐시 행 {len(rows)}개 · {first} ~ {last} · 읽기 {load_s:.1f}초 → {out}")
    res: Dict[str, object] = {"when": now.isoformat(timespec="seconds"), "dir": out, "rows": len(rows), "data_from": first,
                              "data_to": last, "load_sec": round(load_s, 2), "version": collect._version_info().get("sha", ""),
                              "html_days": int(cfg.get("html_days") or 0), "publish_full_days": int(cfg.get("publish_full_days") or 0),
                              "publish_lot_days": int(cfg.get("publish_lot_days") or 0), "a": [], "b": [], "stopped": False}
    jobs = _jobs(cfg, params)
    prep_cls = getattr(collect, "HtmlPrep", None)
    try:
        i = 1
        for kind, c, kw in jobs:                      # (가) 예전처럼 따로 — 장마다 준비를 처음부터
            check()
            tick(i, K.PERF_WHAT_A_FMT.format(what=dict(KINDS)[kind]))
            res["a"].append(_one(kind, c, kw, rows, dev_meta, out, f"a_{kind}.html", None, roots, log))
            i += 1
        if prep_cls is not None:                      # (나) 지금처럼 준비 하나를 나눠 씀
            t1 = time.perf_counter()
            prep = prep_cls(rows)
            res["b_prep_sec"] = round(time.perf_counter() - t1, 3)
            for kind, c, kw in jobs:
                check()
                tick(i, K.PERF_WHAT_B_FMT.format(what=dict(KINDS)[kind]))
                res["b"].append(_one(kind, c, kw, rows, dev_meta, out, f"b_{kind}.html", prep, roots, log))
                i += 1
        else:
            prep = None
            res["b_missing"] = True                   # 준비 나눠 쓰기(HtmlPrep)가 없는 판 — (가)만
            i += 3
        check()
        lot_files = []
        token = secrets.token_hex(6)                   # 이번 실행의 결과만 알아보는 표 — 다운로드 폴더의 다른 파일 · 옛 시험과 섞이지 않게
        res["token"] = token
        for name, key, extra in LOT_FILES:
            tick(i, K.PERF_WHAT_LOT_FMT.format(name=name))
            path = collect.write_html(cfg, rows, dev_meta, [], time.time(), mode="publish", lot_only=True, log=log, out_dir=out,
                                      out_name=name, params_store={}, prep=prep,
                                      meta_extra={"selftest": True, "selftest_token": token, "selftest_name": key, **extra},
                                      compress=True)   # 공유 폴더 배포판과 같게(publish.COMPRESS — LOTD-04)
            lot_files.append({"name": name, "key": key, "path": path, "bytes": os.path.getsize(path), "skip_model": bool(extra.get("lot_skip_model"))})
            i += 1
        res["lot_files"] = [{k: v for k, v in f.items() if k != "path"} for f in lot_files]
        if browser:
            _write_text(os.path.join(out, RESULT_NAME), json.dumps(res, ensure_ascii=False, indent=1), roots)   # 기다리는 동안 꺼져도 앞 결과는 남게
            dirs = [str(d) for d in (download_dirs if download_dirs is not None else recipes.download_dirs())]
            res["download_dirs"] = dirs
            res["lot_open"] = []
            for f in lot_files:
                check()
                tick(i, K.PERF_WHAT_OPEN_FMT.format(name=f["name"], sec=int(lot_wait_sec)))
                i += 1
                try:
                    browser(f["path"])
                except Exception as ex:  # noqa: BLE001 — 못 열어도 시험은 끝까지(요약이 손으로 열라고 적는다)
                    say(f"속도 시험: {f['name']} 를 브라우저로 열지 못했습니다 — {type(ex).__name__}: {ex}")
                    res["lot_open"].append(dict(_lot_open_result(f["key"], f["name"], None), open_error=f"{type(ex).__name__}: {ex}"))
                    continue
                got = wait_download(token, f["key"], dirs, timeout=lot_wait_sec, should_stop=stop)
                if got is None:
                    say(f"속도 시험: {f['name']} 의 결과를 {int(lot_wait_sec)}초 동안 받지 못했습니다(다운로드 폴더 {', '.join(dirs) or '없음'})")
                    res["lot_open"].append(_lot_open_result(f["key"], f["name"], None))
                    continue
                src, data = got
                dst = os.path.join(out, os.path.basename(src))
                _move(src, dst, roots)
                r = _lot_open_result(f["key"], f["name"], data)
                r["result_file"] = os.path.basename(dst)
                res["lot_open"].append(r)
                say(f"속도 시험: {f['name']} 열기 {r['open_sec']:.1f}초 · 자동 점검 {len(r['steps'])}가지 · 오류 {len(r['errors'])}개")
    except Stopped:
        res["stopped"] = True
    res["same"] = {a["kind"]: a["sha256_norm"] == b["sha256_norm"] for a, b in zip(res["a"], res["b"])}
    tick(steps, K.PERF_WHAT_WRITE)
    _write_text(os.path.join(out, RESULT_NAME), json.dumps(res, ensure_ascii=False, indent=1), roots)
    _write_text(os.path.join(out, SUMMARY_NAME), render_summary(res), roots, bom=True)    # 메모장이 한글을 바로 읽게 BOM
    say(f"속도 시험 끝: {out}")
    lot_open = res.get("lot_open") or []
    return {"dir": out, "summary": os.path.join(out, SUMMARY_NAME), "result": os.path.join(out, RESULT_NAME),
            "same": res["same"], "stopped": res["stopped"],
            "lot_open": {r["name"]: r["open_sec"] for r in lot_open if r.get("got")},
            "lot_missing": [r["file"] for r in lot_open if not r.get("got")]}


# ── 요약(사람이 읽는 한 장) ────────────────────────────────────────────────────
def _lot_open_lines(res: dict) -> List[str]:
    """단추 하나로 연 결과(11/26) — 'LOT 배포판 열기 — 지금 n.n초 · 계산 건너뜀 m.m초' 한 줄 + 파일마다 단계 · 점검 · 오류."""
    got = {r["name"]: r for r in res.get("lot_open") or [] if r.get("got")}
    head = " · ".join(f"{LOT_LABELS[k]} {got[k]['open_sec']:.1f}초" if k in got else f"{LOT_LABELS[k]} 못 받음" for _n, k, _e in LOT_FILES)
    L = [f"  LOT 배포판 열기 — {head}",
         "  (기본 브라우저가 두 파일을 차례로 열어 스스로 LOT 고르기 · Wafer 이력 · 검색을 눌러 본 시간 — 열기 = 목록을 그린 첫 화면까지)"]
    fmt = lambda v: "—" if v is None else f"{float(v) / 1000:.2f}"
    for r in res.get("lot_open") or []:
        if not r.get("got"):
            continue
        st = r.get("stages_ms") or {}
        errs = r.get("errors") or []
        L += ["", f"  [{LOT_LABELS[r['name']]}] {r['file']} — 열기 {r['open_sec']:.1f}초 · 덮개 걷힘 {r['lifted_sec']:.1f}초 · "
                  f"자동 점검 {len(r.get('steps') or [])}가지 · 오류 {len(errs)}개",
              f"    JSON 해석 {fmt(st.get('parse'))} · 펼치기 {fmt(st.get('unfold'))} · 모델 {'건너뜀 ' if r.get('lite') else ''}{fmt(st.get('model'))}"
              f" · 첫 화면 {fmt(st.get('first'))} (초)"]
        L += [f"    {'✓' if s['ok'] else '✗'} {s['name']} {s.get('ms')}ms" + (f" — {s['note']}" if s.get("note") else "") for s in r.get("steps") or []]
        L += [f"    오류: {e}" for e in errs[:20]]
        if r.get("browser"):
            L.append(f"    브라우저: {r['browser']}")
    if len(got) < len(LOT_FILES):
        miss = [r["file"] for r in res.get("lot_open") or [] if not r.get("got")]
        L += ["", f"  ※ 결과를 받지 못한 파일: {', '.join(miss) or '—'} — 그 파일을 이 폴더에서 다시 열어(더블클릭) "
                  "브라우저 맨 위 노란 띠 숫자를 보내 주세요."]
    return L


def _sec(v) -> str:
    return f"{float(v):.2f}"


def _table(items: List[dict], tag: str) -> List[str]:
    """한 장에 한 줄 — 글꼴 폭과 상관없이 읽히게 표 대신 '합계 = 단계 · 단계' 로."""
    lines = []
    for it in items:
        st = it["stages"]
        parts = [f"{STAGE_LABELS[k]} {_sec(st.get(k, 0))}" for k in STAGES
                 if k in ("prep", "range", "fold", "json", "write") or float(st.get(k, 0)) >= 0.005]
        lines.append(f"  ({tag}) {dict(KINDS)[it['kind']]}: 합계 {_sec(it['total'])}초 = " + " · ".join(parts))
    return lines


def render_summary(res: dict) -> str:
    a, b = res.get("a") or [], res.get("b") or []
    when = str(res.get("when", ""))[:16].replace("T", " ")
    L = [f"AOI 수집기 속도 시험 — {when}",
         f"가진 데이터(캐시) 행 {res.get('rows', 0):,}개 · {res.get('data_from') or '—'} ~ {res.get('data_to') or '—'} · 캐시 읽기 {res.get('load_sec', 0)}초",
         "장비 NAS 는 읽지 않았습니다. 이 파일(요약.txt) 하나만 보내 주세요.", ""]
    if res.get("stopped"):
        L += ["※ 중간에 멈췄습니다 — 아래는 거기까지의 결과입니다.", ""]
    L += ["■ 1. 수집 끝 HTML 3장 만드는 시간 (PH-01 · PH-03) — 단위: 초",
          "  (가) 예전처럼 따로: 장마다 날짜 해석 · 기간 자르기 · 접기를 처음부터",
          "  (나) 지금처럼: 날짜 해석 · 접기를 한 번 하고 나눠 씀", ""]
    L += _table(a, "가")
    if b:
        L += _table(b, "나")
        ta, tb = sum(x["total"] for x in a), sum(x["total"] for x in b) + float(res.get("b_prep_sec") or 0)
        L += [f"  (나) 공통 준비(날짜 한 번 해석) {_sec(res.get('b_prep_sec') or 0)}초 — 합계에 넣음",
              "", f"  세 장 합계: (가) {ta:.1f}초 → (나) {tb:.1f}초 ({abs(ta - tb):.1f}초 {'빨라짐' if ta >= tb else '느려짐'})"]
    elif res.get("b_missing"):
        L += ["  (나) 이 판에는 준비 나눠 쓰기(HtmlPrep)가 없어 (가)만 쟀습니다."]
    span = lambda n: f"최근 {n}일" if n else "전부"
    L += ["", f"  · 기간 자르기 = 보관한 전체 행에서 그 HTML 의 기간(기본 {span(res.get('html_days'))} · 전체 배포 "
          f"{span(res.get('publish_full_days'))} · LOT 배포 {span(res.get('publish_lot_days'))})만 고르기",
          "  · (가) 를 먼저, (나) 를 나중에 쟀습니다 — 같은 PC 에서 다른 프로그램이 바쁘면 숫자가 흔들립니다.", ""]
    L += ["■ 2. 결과 파일이 같은지 (생성 시각 · 걸린 시간 칸만 빼고 바이트 비교 · sha256)"]
    same = res.get("same") or {}
    for x, y in zip(a, b):
        ok = same.get(x["kind"])
        L.append(f"  {dict(KINDS)[x['kind']]:<12} {'같음' if ok else '다름 ← 알려 주세요'}  "
                 f"({x['bytes'] / 1048576:.1f}MB · {x['sha256_norm'][:12]} / {y['sha256_norm'][:12]})")
    if a and b:
        L.append("  → " + ("세 장 모두 같습니다." if all(same.get(x["kind"]) for x in a) else "다른 장이 있습니다 — 결과.json 과 함께 보내 주세요."))
    L.append("  (비교에 쓴 HTML 은 크기가 커서 지웠습니다 — 크기 · sha256 은 결과.json 에 있습니다.)")
    L += ["", "■ 3. LOT 배포판 열기 시간 (LOTD-01)"]
    if res.get("lot_open") is not None:
        L += _lot_open_lines(res)
    elif res.get("lot_files"):
        L += ["  이 폴더의 두 파일을 Edge(또는 Chrome)에서 차례로 더블클릭해 열어 주세요.",
              f"    {LOT_NOW_NAME:<20} 지금 배포판과 같음",
              f"    {LOT_SKIP_NAME:<20} 안 쓰는 계산(가동률 · Error)을 건너뜀 — 시험용",
              "  열리면 몇 초 동안 혼자 LOT 몇 개 고르기 · Wafer 이력 · 검색을 눌러 본 뒤,",
              "  맨 위 노란 띠에 '열기 n.n초 · 자동 점검 m가지 · 오류 k개' 가 나옵니다.",
              "  두 파일을 차례로 열어 맨 위 띠 숫자를 보내 주세요. 오류가 있으면 '자세히' 를 눌러 나온 글도 함께 보내 주세요.",
              "  (파일마다 처음 연 숫자가 중요합니다 — 다른 창은 닫고 여는 것이 좋습니다.)"]
    else:
        L.append("  (멈춰서 만들지 못했습니다)")
    return "\n".join(L) + "\n"
