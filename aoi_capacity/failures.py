"""실패 로그 수집(10/20 사용자 요청 — '실패한 것들의 원인 · 로그 · 파일명 · 파일 내용을 지난 며칠치로 모아 달라').

수집 중에 실패해도 화면에는 거의 안 드러난다(K1·K3·K6 는 10/6 부터 장비 목록에서 사라졌는데 `[건너뜀]` 로그 한 줄뿐이었다). 이 모듈은 그 흔적을 한 장의 zip 으로 모은다.
출처 넷 — ① app.log(여러 판, 기간 안의 실패 줄 · `[수집 상세]` 의 오류 줄) ② 캐시 `failed`(지금도 못 읽는 Report) ③ 캐시 행(INI 읽기 오류 · 장비별 마지막 데이터 · INI 일치율)
④ 장비 확인(`devices.resolve_devices` — 수집과 같은 범위 게이트, 범위 밖에는 접근하지 않는다). 실패한 파일은 **정확한 경로만** 읽기 전용으로 읽어 내용을 담는다.

★ NAS 는 읽기만 한다. zip 은 로컬 폴더에만 쓰고(`nas_guard.assert_local`), 이 모듈의 쓰기는 `write_report` 한 곳이다.
"""
from __future__ import annotations

import datetime as dt
import io
import os
import re
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import collect, devices, nas_guard, scope
from .utils import paths

LogFn = Callable[[str], None]
STALE_DAYS = 2              # 마지막 Wafer 가 이만큼 이상 지났으면 '데이터 멈춤' 표시(확정이 아니라 확인 요청)
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_LOG_RECORDS = 4000
MAX_INI_EXAMPLES = 5
DEFAULT_DAYS, MIN_DAYS, MAX_DAYS = 3, 1, 90

CAT_DEVICE = "장비 접근 못 함"
CAT_REPORT = "Report 읽기 실패"
CAT_KLA = "KLA Wafer 읽기 실패"
CAT_STALE = "데이터 멈춤?"
CAT_INI = "INI 문제"

_REC = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),\d+ (\w+) ([\w.]+): (.*)$")
_MARKS = ("[건너뜀]", "[범위 밖]", "실패", "읽지 못", "접근", "오류", "PermissionError", "Traceback")
_ERR_LINE = re.compile(r"^\s*오류 device=(.*?) · path=(.*?) · tries=(\d+) · error=(.*)$")
_SKIP_LINE = re.compile(r"^\[건너뜀\] (.+?): (.*)$")
_QUOTED = re.compile(r"'([^']+)'")
_SAFE = re.compile(r"[^0-9A-Za-z가-힣._ -]+")


def clamp_days(v) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    return max(MIN_DAYS, min(MAX_DAYS, n))


# ── ① app.log ───────────────────────────────────────────────────────────────
def _log_paths(base: Path) -> List[Path]:
    out = [base] + [Path(f"{base}.{i}") for i in range(1, 6)]
    return [p for p in out if p.is_file()]


def read_log_records(base: Path, cutoff: dt.datetime) -> List[dict]:
    """로그 판들에서 기간 안 기록을 시간 순으로 — 여러 줄 기록(수집 상세)은 한 기록으로 묶는다."""
    recs: List[dict] = []
    for p in _log_paths(base):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        cur: Optional[dict] = None
        for line in text.splitlines():
            m = _REC.match(line)
            if m:
                try:
                    ts = dt.datetime.strptime(f"{m[1]} {m[2]}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    cur = None
                    continue
                cur = {"ts": ts, "level": m[3], "logger": m[4], "text": m[5]}
                recs.append(cur)
            elif cur is not None:
                cur["text"] += "\n" + line
    recs = [r for r in recs if r["ts"] >= cutoff]
    recs.sort(key=lambda r: r["ts"])
    return recs


def is_failure_record(r: dict) -> bool:
    if r["level"] in ("WARNING", "ERROR", "CRITICAL"):
        return True
    t = r["text"]
    return t.startswith("[수집 상세]") or any(k in t for k in _MARKS)


def log_errors(recs: List[dict]) -> List[dict]:
    """`[수집 상세]` 의 `오류 device=… · path=… · tries=… · error=…` 줄 — KLA 읽기 실패는 캐시에 남지 않아 이 줄이 유일한 기록이다."""
    out: Dict[tuple, dict] = {}
    for r in recs:
        for line in r["text"].splitlines():
            m = _ERR_LINE.match(line)
            if m:
                key = (m[1], m[2])
                out[key] = {"device": m[1], "path": m[2], "tries": int(m[3]), "error": m[4], "ts": r["ts"], "source": "app.log"}
    return list(out.values())


def log_skips(recs: List[dict]) -> Dict[str, str]:
    """`[건너뜀] <장비>: <이유>` — 장비 이름 → 가장 최근 이유."""
    out: Dict[str, str] = {}
    for r in recs:
        for line in r["text"].splitlines():
            m = _SKIP_LINE.match(line.strip())
            if m:
                out[m[1]] = m[2]
    return out


# ── ② ③ 캐시 ────────────────────────────────────────────────────────────────
def _dev_name(cache: dict, dk: str) -> str:
    d = (cache.get("devices") or {}).get(dk) or {}
    return str(d.get("name") or dk)


def cache_failures(cache: dict, cutoff: dt.datetime) -> List[dict]:
    out = []
    for key, f in (cache.get("failed") or {}).items():
        try:
            mt = dt.datetime.fromtimestamp(float(f.get("mtime") or 0))
        except (TypeError, ValueError, OSError, OverflowError):
            mt = None
        if mt is not None and mt < cutoff:
            continue
        out.append({"device": _dev_name(cache, str(f.get("device_key") or "")), "path": str(f.get("path") or key),
                    "tries": int(f.get("tries") or 0), "error": str(f.get("error") or ""), "ts": mt, "source": "캐시"})
    return out


def device_facts(cache: dict, cutoff: dt.datetime) -> Dict[str, dict]:
    """장비마다 마지막 데이터 시각 · 기간 안 Report 수 · INI 일치 비율 · INI 오류 예시(캐시만 본다 — NAS 접근 없음)."""
    facts: Dict[str, dict] = {}

    def fact(name: str) -> dict:
        return facts.setdefault(name, {"last": None, "reports": 0, "rows": 0, "exact": 0, "ini_err": 0, "ini_nf": 0, "examples": []})

    for entry in (cache.get("reports") or {}).values():
        if entry.get("superseded_by"):
            continue
        name = str(entry.get("device") or "")
        rows = entry.get("rows") or []
        if not name or not rows:
            continue
        f = fact(name)
        newest = max((collect.parse_dt(r.get("batch_end") or r.get("batch_start")) or dt.datetime.min for r in rows), default=dt.datetime.min)
        if newest > dt.datetime.min and (f["last"] is None or newest > f["last"]):
            f["last"] = newest
        if newest < cutoff:
            continue
        f["reports"] += 1
        for r in rows:
            if r.get("kind"):
                continue
            f["rows"] += 1
            im = r.get("ini_match")
            f["exact"] += im == "EXACT"
            codes = str(r.get("issue_codes") or "")
            if im == "READ_ERROR" or "INI_READ_ERROR" in codes:
                f["ini_err"] += 1
                if len(f["examples"]) < MAX_INI_EXAMPLES:
                    f["examples"].append({"report": str(r.get("report") or entry.get("rel") or ""), "wafer": str(r.get("wafer_id") or ""),
                                          "codes": codes})
            elif im in ("NOT_FOUND", "MOVED_ONLY"):
                f["ini_nf"] += 1
    for e in (cache.get("kla") or {}).values():
        name = str(e.get("name") or "")
        if not name:
            continue
        f = fact(name)
        ts = [str(r.get("t") or "") for ws in (e.get("lots") or {}).values() for r in ws.values()]
        if ts:
            last = max(ts)
            try:
                d = dt.datetime.fromisoformat(last)
            except ValueError:
                continue
            if f["last"] is None or d > f["last"]:
                f["last"] = d
            f["reports"] += sum(1 for t in ts if t >= cutoff.isoformat(timespec="minutes"))
    return facts


# ── ④ 장비 확인 ─────────────────────────────────────────────────────────────
def probe_devices(cfg: dict, log: LogFn, should_stop: Optional[Callable[[], bool]] = None,
                  resolver: Optional[Callable[..., list]] = None) -> dict:
    """수집과 같은 게이트로 장비를 확인한다(범위 밖 접근 없음). → {"ok": [장비 dict], "missed": {이름: 이유}, "paths": {이름: 경로}}"""
    seen: List[str] = []

    def cap(msg: str) -> None:
        seen.append(msg)
        log(msg)

    devs = (resolver or devices.resolve_devices)(cfg, log=cap, should_stop=should_stop)
    missed = devices.missed_in_scope(cfg, devs, seen)
    return {"ok": devs, "missed": missed, "paths": {str(d["name"]): str(d["path"]) for d in devs}}


# ── 파일 내용 ───────────────────────────────────────────────────────────────
def file_path_of(item: dict) -> str:
    """내용을 읽을 파일 경로 — Report 는 path 그대로, KLA 는 오류 문구 안의 결과 파일(`'N:\\\\…\\\\x.001'`)."""
    p = str(item.get("path") or "")
    if p.lower().endswith((".htm", ".html")):
        return p
    m = _QUOTED.search(str(item.get("error") or ""))
    return m[1].replace("\\\\", "\\") if m else ""


def _safe(s: str) -> str:
    return _SAFE.sub("_", s).strip("._ ") or "x"


def fetch_content(item: dict, allowed: Callable[[str], bool], roots: Dict[str, str]) -> dict:
    """실패한 파일 하나를 읽기 전용으로 읽는다. 허용 장비이고 **그 장비의 확인된 폴더 아래** 경로만 — 장비 폴더를 못 찾았으면(roots 에 없음) 읽지 않는다.
    앞 `MAX_FILE_BYTES` 까지만 읽는다."""
    path = file_path_of(item)
    out: dict = {"file": os.path.basename(path.replace("\\", "/")) if path else "", "size": "", "mtime": "", "data": None, "note": ""}
    dev = str(item.get("device") or "")
    if not path:
        out["note"] = "파일 경로를 알 수 없음"
        return out
    if not allowed(dev):
        out["note"] = "수집 범위 밖 장비라 읽지 않음"
        return out
    root = roots.get(dev)
    if not root or not nas_guard.is_under(path, root):
        out["note"] = "장비 폴더를 확인하지 못했거나 그 밖의 경로라 읽지 않음"
        return out
    try:
        st = os.stat(path)
        out["size"], out["mtime"] = st.st_size, dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    except OSError as ex:
        out["note"] = f"파일 정보를 못 읽음 — {type(ex).__name__}: {ex}"
    try:
        data = nas_guard.read_head(path, MAX_FILE_BYTES)
    except OSError as ex:
        out["note"] = (out["note"] + " / " if out["note"] else "") + f"내용을 못 읽음 — {type(ex).__name__}: {ex}"
        return out
    out["data"] = data[:MAX_FILE_BYTES]
    if len(data) > MAX_FILE_BYTES:
        out["note"] = f"앞 {MAX_FILE_BYTES // 1024}KB 만 담음(전체 {out['size'] or '?'} 바이트)"
    return out


# ── 모으기 ──────────────────────────────────────────────────────────────────
def gather(cfg: dict, days: int, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, now: Optional[dt.datetime] = None,
           log_base: Optional[Path] = None, resolver: Optional[Callable[..., list]] = None, read_files: bool = True) -> dict:
    now = now or dt.datetime.now()
    days = clamp_days(days)
    cutoff = now - dt.timedelta(days=days)
    stop = should_stop or (lambda: False)
    log(f"실패 로그 — 지난 {days}일({cutoff:%m/%d %H:%M} ~) 검사")

    recs = read_log_records(log_base or paths.log_file(), cutoff)[-MAX_LOG_RECORDS * 4:]
    fail_recs = [r for r in recs if is_failure_record(r)][-MAX_LOG_RECORDS:]
    log(f"app.log 기록 {len(recs)}개 중 실패 관련 {len(fail_recs)}개")

    cache = collect._load_cache(cfg, rederive=False, dirty=collect._Dirty())
    facts = device_facts(cache, cutoff)
    probe = probe_devices(cfg, log, stop, resolver)

    items: List[dict] = []
    for name, why in sorted(probe["missed"].items()):
        last = facts.get(name, {}).get("last")
        items.append({"category": CAT_DEVICE, "device": name, "path": "", "error": why, "tries": "", "ts": None, "source": "장비 확인",
                      "note": f"마지막 데이터 {last:%Y-%m-%d %H:%M}" if last else "캐시에 데이터 없음"})
    for it in cache_failures(cache, cutoff) + log_errors(recs):
        it["category"] = CAT_REPORT if str(it["path"]).lower().endswith((".htm", ".html")) else CAT_KLA
        items.append(it)
    seen = set()
    uniq = []
    for it in items:                                   # 같은 (장비, 경로, 오류) 는 한 번 — 캐시와 로그가 겹친다
        k = (it["device"], it["path"], it["category"], str(it["error"])[:80])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    items = [it for it in uniq if scope.is_allowed(cfg, it["device"])]      # 범위 밖 장비는 목록에서도 뺀다(캐시·로그는 지우지 않는다)
    ok_names = {str(d["name"]) for d in probe["ok"]}
    for name, f in sorted(facts.items()):
        if not scope.is_allowed(cfg, name):
            continue
        if f["last"] is not None and name in ok_names and (now - f["last"]).days >= STALE_DAYS:
            items.append({"category": CAT_STALE, "device": name, "path": "", "tries": "", "ts": None, "source": "캐시",
                          "error": f"마지막 데이터 {f['last']:%Y-%m-%d %H:%M} — {(now - f['last']).days}일 새 데이터 없음(설비가 선 것일 수도 있음)", "note": ""})
        if f["ini_err"]:
            ex = f["examples"][0] if f["examples"] else {}
            items.append({"category": CAT_INI, "device": name, "path": "", "tries": f["ini_err"], "ts": None, "source": "캐시",
                          "error": f"INI 읽기 오류 {f['ini_err']}행 · 예: {ex.get('report', '')} {ex.get('codes', '')}", "note": ""})

    allowed = lambda n: scope.is_allowed(cfg, n)  # noqa: E731
    roots = probe["paths"]
    if read_files:
        todo = [it for it in items if it["category"] in (CAT_REPORT, CAT_KLA)]
        for i, it in enumerate(todo, 1):
            if stop():
                log("멈춤 요청 — 지금까지 모은 것으로 마무리합니다")
                break
            it["content"] = fetch_content(it, allowed, roots)
            log(f"[{i}/{len(todo)}] {it['device']} {it['content']['file'] or it['path']} — "
                + (f"{len(it['content']['data'])}바이트" if it["content"]["data"] is not None else it["content"]["note"]))
    return {"now": now, "days": days, "cutoff": cutoff, "items": items, "facts": facts, "probe": probe, "log_records": fail_recs}


# ── 쓰기(로컬 zip 한 장) ────────────────────────────────────────────────────
def _tsv(rows: List[List[object]]) -> str:
    return "\n".join("\t".join(str(c).replace("\t", " ").replace("\r", " ").replace("\n", " ⏎ ") for c in r) for r in rows) + "\n"


def render_summary(g: dict) -> str:
    items = g["items"]
    by: Dict[str, int] = {}
    for it in items:
        by[it["category"]] = by.get(it["category"], 0) + 1
    lines = [f"실패 로그 요약 — {g['now']:%Y-%m-%d %H:%M} 기준 지난 {g['days']}일 ({g['cutoff']:%Y-%m-%d %H:%M} ~)", "",
             f"실패 항목 {len(items)}개: " + (" · ".join(f"{k} {v}" for k, v in by.items()) or "없음"), ""]
    for cat in (CAT_DEVICE, CAT_STALE, CAT_REPORT, CAT_KLA, CAT_INI):
        sub = [it for it in items if it["category"] == cat]
        if not sub:
            continue
        lines.append(f"■ {cat} ({len(sub)})")
        for it in sub[:60]:
            lines.append(f"  · {it['device']}  {it.get('path') or ''}  {str(it['error'])[:200]}")
        if len(sub) > 60:
            lines.append(f"  … 외 {len(sub) - 60}개(실패목록.tsv 참고)")
        lines.append("")
    lines.append("파일 내용에는 Lot · Job 이름이 들어 있습니다 — 공유 범위는 직접 판단해 주세요.")
    return "\n".join(lines) + "\n"


def write_report(cfg: dict, g: dict, out_dir: str) -> str:
    """zip 한 장을 만든다. 저장 위치가 NAS 아래면 거부(`nas_guard.assert_local`)."""
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"AOI_fail_logs_{g['now']:%Y%m%d_%H%M}.zip")
    head = ["분류", "장비", "파일명", "경로", "오류", "시도", "파일 크기", "파일 수정 시각", "기록 시각", "출처", "내용 파일 / 비고"]
    tsv = [head]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, it in enumerate(g["items"], 1):
            c = it.get("content") or {}
            member = ""
            if c.get("data") is not None:
                member = f"files/{_safe(str(it['device']))}/{n:03d}_{_safe(c.get('file') or 'file')}"
                z.writestr(member, c["data"])
            note = member or c.get("note") or it.get("note") or ""
            if member and c.get("note"):
                note += f" ({c['note']})"
            tsv.append([it["category"], it["device"], c.get("file", ""), it.get("path", ""), it["error"], it.get("tries", ""),
                        c.get("size", ""), c.get("mtime", ""), f"{it['ts']:%Y-%m-%d %H:%M:%S}" if it.get("ts") else "", it.get("source", ""), note])
        z.writestr("요약.txt", render_summary(g))
        z.writestr("실패목록.tsv", _tsv(tsv))
        st = [["장비", "접근", "이유", "마지막 데이터", "기간 안 Report", "INI 확인한 행", "INI 정확 일치 %", "INI 읽기 오류", "INI 없음"]]
        names = sorted(set(g["facts"]) | set(g["probe"]["missed"]) | set(g["probe"]["paths"]))
        for name in names:
            if not scope.is_allowed(cfg, name):
                continue
            f = g["facts"].get(name) or {}
            opened = name in g["probe"]["paths"]
            pct = f"{f['exact'] / f['rows'] * 100:.0f}" if f.get("rows") else ""
            st.append([name, "열림" if opened else "못 엶", g["probe"]["missed"].get(name, ""),
                       f"{f['last']:%Y-%m-%d %H:%M}" if f.get("last") else "", f.get("reports", ""), f.get("rows", ""), pct,
                       f.get("ini_err", ""), f.get("ini_nf", "")])
        z.writestr("장비상태.tsv", _tsv(st))
        z.writestr("app_log_발췌.txt", "\n".join(f"{r['ts']:%Y-%m-%d %H:%M:%S} {r['level']} {r['logger']}: {r['text']}" for r in g["log_records"]) + "\n")
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    return out


def run(cfg: dict, days: int, out_dir: str, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, **kw) -> dict:
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))       # NAS 를 읽기 전에 저장 위치부터 확인
    g = gather(cfg, days, log=log, should_stop=should_stop, **kw)
    path = write_report(cfg, g, out_dir)
    return {"path": path, "items": len(g["items"]), "days": g["days"], "out_dir": out_dir,
            "by": {c: sum(1 for i in g["items"] if i["category"] == c) for c in {i["category"] for i in g["items"]}}}
