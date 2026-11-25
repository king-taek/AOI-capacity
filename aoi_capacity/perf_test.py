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
import time
from typing import Callable, Dict, List, Optional

from . import collect, i18n, nas_guard
from .utils import config as config_mod
from .utils import paths

K = i18n.KO
LogFn = Callable[[str], None]

LOT_NOW_NAME = "LOT_지금.html"
LOT_SKIP_NAME = "LOT_계산건너뜀.html"
SUMMARY_NAME = "요약.txt"
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
        should_stop: Optional[Callable[[], bool]] = None, now: Optional[dt.datetime] = None) -> dict:
    """시험 한 번 → {"dir", "summary", "result", ...}. 결과 폴더는 `<out_root>\\<YYYYMMDD_HHMMSS>`."""
    cfg = config_mod.check_or_raise(cfg)
    nas_guard.check_cfg(cfg)
    roots = nas_guard.roots_for_cfg(cfg)
    now = now or dt.datetime.now()
    out = os.path.join(out_root or default_root(), now.strftime("%Y%m%d_%H%M%S"))
    nas_guard.assert_local(out, roots)                # ★ 무엇을 읽기 전에 저장 위치부터
    say = log or (lambda m: None)
    stop = should_stop or (lambda: False)
    steps = 9
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
        for name, extra in ((LOT_NOW_NAME, {"selftest": True}), (LOT_SKIP_NAME, {"selftest": True, "lot_skip_model": True})):
            tick(i, K.PERF_WHAT_LOT_FMT.format(name=name))
            path = collect.write_html(cfg, rows, dev_meta, [], time.time(), mode="publish", lot_only=True, log=log, out_dir=out,
                                      out_name=name, params_store={}, prep=prep, meta_extra=extra)
            lot_files.append({"name": name, "bytes": os.path.getsize(path), "skip_model": bool(extra.get("lot_skip_model"))})
            i += 1
        res["lot_files"] = lot_files
    except Stopped:
        res["stopped"] = True
    res["same"] = {a["kind"]: a["sha256_norm"] == b["sha256_norm"] for a, b in zip(res["a"], res["b"])}
    tick(steps, K.PERF_WHAT_WRITE)
    _write_text(os.path.join(out, RESULT_NAME), json.dumps(res, ensure_ascii=False, indent=1), roots)
    _write_text(os.path.join(out, SUMMARY_NAME), render_summary(res), roots, bom=True)    # 메모장이 한글을 바로 읽게 BOM
    say(f"속도 시험 끝: {out}")
    return {"dir": out, "summary": os.path.join(out, SUMMARY_NAME), "result": os.path.join(out, RESULT_NAME),
            "same": res["same"], "stopped": res["stopped"]}


# ── 요약(사람이 읽는 한 장) ────────────────────────────────────────────────────
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
         "장비 NAS 는 읽지 않았습니다. 이 폴더를 통째로(또는 이 파일과 결과.json) 보내 주세요.", ""]
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
    L += ["", "■ 3. LOT 배포판 열기 시간 (LOTD-01) — 직접 열어 보기"]
    if res.get("lot_files"):
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
