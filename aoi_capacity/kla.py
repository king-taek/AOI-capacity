"""KLA AOI 수집(10/5, D68 · D71 · D73) — Camtek 과 같은 수집기 · 같은 캐시 · 같은 행 계약(`collect.OUT_COLS`)으로 모은다.

KLA 는 BatchReport · WaferInfo.ini 가 없다. 드라이브 맨 위가 날짜 폴더(`2026-10-05`) → Lot 폴더(`TB500.INT764@6322`, = LotID)
→ Wafer 폴더(`2026-10-05-12-42_6` = 시작 시각 + Slot) → 결과 파일(`*.001` 또는 확장자 없음 — 확장자가 아니라 `FileVersion` 머리로 찾는다).
실물(10/5 조사 1·2차, `scripts/kla_survey.py`):
  · **날짜 폴더는 Wafer 날짜가 아니다** — 자정을 넘긴 Lot 은 첫날 폴더에 자정까지 · 다음날 폴더에 **Lot 전체가 다시** 있다
    → Lot 안에서 **Wafer 폴더 이름으로 한 번만** 센다(D71). 날짜 아닌 폴더(`DY` · `MOON` · `old` …, 사람·엔지니어링 사본)는 세지 않는다(D71).
  · Wafer 폴더 시각 = 그 장의 **시작**(첫 장 = ResultTimestamp 와 0~1분). FileTimestamp 는 두 자리 연도면 검토 뒤 다시 쓴 시각이라 쓰지 않는다.
  · ResultTimestamp = 그 Lot 실행의 시작 — 같은 Lot 을 다시 돌리면 값이 달라지므로 **실행(run) 단위**로 묶는 열쇠로 쓴다.
  · 결함 수 = DefectList 레코드 수(= SummaryList NDEFECT, D68). Error 는 수집하지 않는다(D68) — 모든 장이 PASS.
행 만들기(`rows_from_store`): 실행마다 Wafer 를 시각순으로 놓고 **장 시작 ~ 다음 장 시작**을 그 장의 스캔 구간으로 쓴다.
간격이 그 실행의 장당 중앙 간격의 3배를 넘으면(장비가 멈춰 있던 것) 그 장은 중앙 간격만큼만, 마지막 장도 중앙 간격만큼 —
'첫 장 ~ 마지막 장 시각'(사용자 제안)에 마지막 장의 스캔 시간을 더한 것이다. 배치 시작 = 첫 장 시작, 배치 끝 = 마지막 장 끝.

★ NAS 는 읽기만 한다(scandir · `nas_guard.read_bytes`). 스레드는 읽기만 하고, 캐시에 넣는 일은 메인 스레드가 입력 순서대로 한다.
캐시: `cache["kla"][<장비 안정 키>] = {"name", "since", "seen_to", "lots": {Lot 폴더: {Wafer 폴더: 기록}}}`.
"""
from __future__ import annotations

import datetime as dt
import os
import re
import statistics
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple

from . import nas_guard, scope

DATE_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
WAFER_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})_(\d+)$")
TS_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4}|\d{2})\s+(\d{2}):(\d{2}):(\d{2})")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\b(.*)$")
QUOTED = re.compile(r'"([^"]*)"')
IMAGE_EXT = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"}
SIDE_EXT = {".pass", ".txt", ".db"}
MAX_READ = 64 * 1024 * 1024
LIST_BACK_DAYS = 2           # 증분 나열: 지난번 본 마지막 날짜 폴더보다 이만큼 앞부터(자정 넘긴 Lot 이 다음 날 폴더에 다시 생긴다)
GAP_CAP_FACTOR = 3.0         # 장 간격이 중앙값의 이 배수를 넘으면 장비가 멈춰 있던 것 — 그 장은 중앙 간격만큼만
TIME_FMT = "%m/%d/%Y %I:%M:%S %p"


def wafer_time(name: str) -> Tuple[Optional[dt.datetime], Optional[int]]:
    m = WAFER_DIR_RE.match(name or "")
    if not m:
        return None, None
    y, mo, d, h, mi, slot = (int(x) for x in m.groups())
    try:
        return dt.datetime(y, mo, d, h, mi), slot
    except ValueError:
        return None, slot


def parse_ts(s: str) -> Optional[dt.datetime]:
    """'10-05-2026 11:53:25' · '10-05-26 11:53:25' → datetime(월-일-연, 10/5 조사: 8대 전부 MM-DD)."""
    m = TS_RE.search(s or "")
    if not m:
        return None
    mo, d, y, h, mi, se = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    try:
        return dt.datetime(y, mo, d, h, mi, se)
    except ValueError:
        return None


def parse_result(text: str) -> dict:
    """KLA 결과 파일(KLARF 비슷한 텍스트)에서 필요한 것만 — LotID · SetupID · StepID · DeviceID · WaferID · Slot · ResultTimestamp ·
    결함 레코드 수 · SummaryList(NDEFECT · NDIE)."""
    head: Dict[str, str] = {}
    defects, in_list, want_spec, want_sum = 0, False, False, False
    spec, summary = "", []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if in_list:
            if re.match(r"^-?\d+\s", s):
                defects += 1
                if s.endswith(";"):
                    in_list = False
                continue
            in_list = False
        if want_spec:
            spec += " " + s
            want_spec = not s.endswith(";")
            continue
        if want_sum:
            if re.match(r"^\d", s):
                summary.append(s.rstrip(";").strip())
                if s.endswith(";"):
                    want_sum = False
                continue
            want_sum = False
        m = KEY_RE.match(s)
        if not m:
            continue
        k, rest = m.group(1), m.group(2).strip()
        if k == "DefectList":
            in_list = not rest.startswith(";")
        elif k == "SummarySpec":
            spec, want_spec = rest, not rest.endswith(";")
        elif k == "SummaryList":
            want_sum = True
        elif k not in head:
            head[k] = rest.rstrip(";").strip()
    cols = re.sub(r"^\d+\s*", "", spec).replace(";", "").split()

    def col_sum(name: str) -> Optional[int]:
        if name not in cols or not summary:
            return None
        try:
            return sum(int(r.split()[cols.index(name)]) for r in summary)
        except (ValueError, IndexError):
            return None

    q = lambda k: (QUOTED.findall(head.get(k, "")) or [head.get(k, "")])[0]  # noqa: E731
    rts = parse_ts(head.get("ResultTimestamp", ""))
    return {"lot": q("LotID"), "setup": q("SetupID"), "step": q("StepID"), "device_id": q("DeviceID"), "wafer": q("WaferID"),
            "slot": head.get("Slot", "").strip(), "rts": rts.isoformat(timespec="seconds") if rts else "",
            "defects": defects, "ndefect": col_sum("NDEFECT"), "ndie": col_sum("NDIE"), "eof": "EndOfFile" in head}


# ── NAS 읽기(스레드에서) ─────────────────────────────────────────────────────
def list_dates(root: str) -> List[str]:
    """맨 위의 날짜 폴더 이름(오름차순). 날짜 아닌 폴더는 보지 않는다(D71). 루트를 못 읽으면 OSError."""
    with os.scandir(root) as it:
        return sorted(e.name for e in it if DATE_DIR_RE.match(e.name) and e.is_dir())


def list_date(root: str, date_dir: str) -> List[Tuple[str, List[str]]]:
    """날짜 폴더 하나 → [(Lot 폴더, [Wafer 폴더 이름])]. Wafer 이름 규칙에 맞는 폴더만."""
    base = os.path.join(root, date_dir)
    out = []
    with os.scandir(base) as it:
        lots = sorted(e.name for e in it if e.is_dir())
    for lot in lots:
        try:
            with os.scandir(os.path.join(base, lot)) as it:
                out.append((lot, sorted(e.name for e in it if e.is_dir() and WAFER_DIR_RE.match(e.name))))
        except OSError:
            out.append((lot, []))
    return out


def read_wafer(path: str) -> Optional[dict]:
    """Wafer 폴더 하나 → 결과 파일을 찾아 읽은 기록. 결과 파일이 아직 없으면(스캔 중 · 중단) None."""
    cands = []
    with os.scandir(path) as it:
        for e in it:
            if e.is_dir():
                continue
            ext = os.path.splitext(e.name)[1].lower()
            if ext in IMAGE_EXT or ext in SIDE_EXT:
                continue
            cands.append((e.stat().st_mtime, e.name))
    for _m, name in sorted(cands, reverse=True):          # 여러 개면 가장 늦은 것부터
        p = os.path.join(path, name)
        data = nas_guard.read_bytes(p)[:MAX_READ]
        if not data.lstrip(b"\xef\xbb\xbf").startswith(b"FileVersion"):
            continue
        rec = parse_result(data.decode("utf-8", errors="replace"))
        rec["file"] = name
        return rec
    return None


# ── 수집(메인 스레드가 합친다) ───────────────────────────────────────────────
def collect_kla(cfg: dict, devs: List[dict], cache: dict, *, run: Callable, now: dt.datetime,
                backfill: bool, refresh_days: int, rebuild: bool, log: Callable[[str], None],
                progress: Callable[[int, int, str], None], phase: str,
                refresh_from: Optional[dt.datetime] = None, refresh_until: Optional[dt.datetime] = None) -> Tuple[List[dict], List[dict], bool, dict]:
    """KLA 장비들을 모은다 → (dev_meta, errors, 바뀐 것 있음, stats).

    `run(items, fn, path_of)` 는 collect 의 `_run` 을 NAS 별로 감싼 것(같은 동시성 예산). 나열은 매번 하고(전부 나열이 장비당 2~6초,
    10/5 실측), 읽기는 캐시에 없는 Wafer 만 — 처음 보는 장비는 `backfill_days` 창 안만(그 앞은 `since` 로 남겨 다시 읽지 않는다)."""
    store = cache.setdefault("kla", {})
    changed = False
    t_all = time.perf_counter()
    window_since = (now.date() - dt.timedelta(days=int(cfg.get("backfill_days") or 30))).isoformat()
    metas: Dict[str, dict] = {}
    for d in devs:
        k = str(d["key"])
        e = store.get(k)
        if e is None:
            e = store[k] = {"name": d["name"], "since": window_since, "seen_to": "", "lots": {}}
            changed = True
        if e.get("name") != d["name"]:
            e["name"] = d["name"]
            changed = True
        if (backfill or rebuild) and window_since < str(e.get("since") or window_since):
            e["since"] = window_since
            changed = True
        metas[k] = {"name": d["name"], "id": str(d["id"]), "key": k, "note": d["path"], "report_dir": "", "kind": "kla",
                    "reports": 0, "found": 0, "error": "", "read_errors": 0, "recovered": 0, "refreshed": 0, "retried": 0, "kept": 0}

    # ① 날짜 폴더 나열(장비마다)
    def p1(d):
        t0 = time.perf_counter()
        try:
            return list_dates(str(d["path"])), "", time.perf_counter() - t0
        except OSError as ex:
            return [], f"{type(ex).__name__}: {ex}", time.perf_counter() - t0
    r1 = run(devs, p1, lambda d: str(d["path"]))
    jobs = []
    for d, (dates, err, sec) in zip(devs, r1):
        m, e = metas[str(d["key"])], store[str(d["key"])]
        m["list_dev_ms"] = int(sec * 1000)
        if err:
            m["error"] = err
            log(f"[{d['name']}] KLA 드라이브를 읽지 못했습니다 — {err}")
            continue
        full = backfill or rebuild or refresh_days > 0 or not e.get("seen_to")
        lo = str(e.get("since") or window_since)
        if not full:
            last = dt.date.fromisoformat(e["seen_to"]) - dt.timedelta(days=LIST_BACK_DAYS)
            lo = max(lo, last.isoformat())
        lo = (dt.date.fromisoformat(lo) - dt.timedelta(days=LIST_BACK_DAYS)).isoformat()
        jobs += [(d, dd) for dd in dates if dd >= lo]
        if dates and dates[-1] != e.get("seen_to"):
            e["seen_to"] = dates[-1]
            changed = True
        m["listing"] = "full" if full else "recent"
        m["pattern_days"] = sum(1 for dd in dates if dd >= lo)
    progress(0, 0, phase)

    # ② 날짜 폴더마다 Lot · Wafer 폴더 이름
    def p2(job):
        d, dd = job
        try:
            return list_date(str(d["path"]), dd), ""
        except OSError as ex:
            return [], f"{type(ex).__name__}: {ex}"
    r2 = run(jobs, p2, lambda j: str(j[0]["path"]))
    want: List[tuple] = []
    seen: set = set()
    refresh_since = refresh_from or ((now - dt.timedelta(days=refresh_days)) if refresh_days > 0 else None)
    for (d, dd), (lots, err) in zip(jobs, r2):
        k = str(d["key"])
        m, e = metas[k], store[k]
        if err:
            log(f"[{d['name']}] {dd} 폴더를 읽지 못했습니다 — {err}")
            continue
        since = dt.date.fromisoformat(str(e.get("since") or window_since))
        for lot, wafers in lots:
            have = e["lots"].get(lot) or {}
            for w in wafers:
                t, _slot = wafer_time(w)
                if t is None or t.date() < since or (k, lot, w) in seen:
                    continue
                seen.add((k, lot, w))                          # 자정 넘긴 Lot 이 두 날짜 폴더에 겹쳐도 한 번만(D71)
                m["found"] += 1
                old = have.get(w)
                if old is not None and not rebuild and not (refresh_since and t >= refresh_since and (refresh_until is None or t < refresh_until)):
                    m["kept"] += 1
                    continue
                if old is not None:
                    m["refreshed"] += 1
                want.append((d, dd, lot, w))

    # ③ 새 Wafer 의 결과 파일 읽기
    def p3(job):
        d, dd, lot, w = job
        t0 = time.perf_counter()
        try:
            return read_wafer(os.path.join(str(d["path"]), dd, lot, w)), "", time.perf_counter() - t0
        except OSError as ex:
            return None, f"{type(ex).__name__}: {ex}", time.perf_counter() - t0
    total = len(want)
    done, lock = [0], threading.Lock()

    def p3p(job):
        out = p3(job)
        with lock:
            done[0] += 1
            n = done[0]
        progress(n, total, phase)
        return out
    r3 = run(want, p3p, lambda j: str(j[0]["path"]))
    errors: List[dict] = []
    pending = 0
    for (d, dd, lot, w), (rec, err, sec) in zip(want, r3):
        k = str(d["key"])
        m, e = metas[k], store[k]
        m["read_n"] = m.get("read_n", 0) + 1
        m["read_sum_ms"] = m.get("read_sum_ms", 0) + int(sec * 1000)
        if err:
            m["read_errors"] += 1
            errors.append({"device": d["name"], "path": os.path.join(str(d["path"]), dd, lot, w), "tries": 1, "error": err})
            continue
        if rec is None:
            pending += 1                                       # 결과 파일이 아직 없다 — 다음 수집에서 다시 본다
            continue
        t, slot = wafer_time(w)
        rec.update({"t": t.isoformat(timespec="minutes"), "dir_slot": slot, "dd": dd})
        e["lots"].setdefault(lot, {})[w] = rec
        changed = True
    retention = int(cfg.get("retention_days") or 0)
    if retention > 0:                                          # 0 = 기한 없음(기본, D69)
        cut = (now - dt.timedelta(days=retention)).isoformat(timespec="minutes")
        for e in store.values():
            for lot in list(e["lots"]):
                ws = e["lots"][lot]
                for w in [w for w, r in ws.items() if str(r.get("t") or "") < cut]:
                    del ws[w]
                    changed = True
                if not ws:
                    del e["lots"][lot]
    for d in devs:
        m = metas[str(d["key"])]
        m["reports"] = sum(1 for _ in _runs(store[str(d["key"])]))
        if not m["error"]:
            log(f"[{d['name']}] KLA Wafer {m['found']}장 중 새로 읽음 {m.get('read_n', 0)}장"
                + (f" (다시 읽기 {m['refreshed']}장 포함)" if m["refreshed"] else "") + f" · 그대로 {m['kept']}장")
    stats = {"kla_devices": len(devs), "kla_wafers_read": len(want), "kla_pending": pending,
             "kla_ms": int((time.perf_counter() - t_all) * 1000)}
    if pending:
        log(f"KLA 결과 파일이 아직 없는 Wafer 폴더 {pending}개(스캔 중이거나 중단) — 다음 수집에서 다시 봅니다")
    return [metas[str(d["key"])] for d in devs], errors, changed, stats


def _runs(entry: dict):
    """한 장비의 (Lot, ResultTimestamp, [(시각, Wafer 폴더, 기록)]) — 같은 Lot 을 다시 돌린 것은 다른 실행."""
    for lot, ws in sorted((entry.get("lots") or {}).items()):
        by: Dict[str, list] = {}
        for w, r in ws.items():
            by.setdefault(str(r.get("rts") or ""), []).append((str(r.get("t") or ""), w, r))
        for rts, items in sorted(by.items()):
            yield lot, rts, sorted(items)


def _fmt(t: dt.datetime) -> str:
    return t.strftime(TIME_FMT)


def rows_from_store(store: dict, cfg: dict, scan_type: Callable[[str], str]) -> List[dict]:
    """캐시의 KLA 기록 → 행(`collect.OUT_COLS`). 범위 밖 장비는 지우지 않고 빼기만 한다."""
    rows: List[dict] = []
    for e in (store or {}).values():
        name = str(e.get("name") or "")
        if not scope.is_allowed(cfg, name):
            continue
        for lot, rts, items in _runs(e):
            ts = [dt.datetime.fromisoformat(t) for t, _w, _r in items]
            gaps = [(b - a).total_seconds() for a, b in zip(ts, ts[1:]) if b > a]
            med = statistics.median(gaps) if gaps else 0.0
            ends = []
            for i, t in enumerate(ts):
                nxt = ts[i + 1] if i + 1 < len(ts) else None
                g = (nxt - t).total_seconds() if nxt else None
                if g is None or g <= 0 or (med and g > med * GAP_CAP_FACTOR):
                    ends.append(t + dt.timedelta(seconds=med) if med else None)   # 마지막 장 · 멈춰 있던 간격 → 중앙 간격만큼
                else:
                    ends.append(nxt)
            bs = ts[0]
            be = max([x for x in ends if x] or [ts[-1]])
            report = f"KLA:{lot}:{rts or items[0][0]}"
            for (t_iso, w, r), t, end in zip(items, ts, ends):
                lot_id = str(r.get("lot") or lot)
                rows.append({"device": name, "kind": "", "job": str(r.get("setup") or ""), "setup": str(r.get("step") or ""),
                             "lot": lot_id, "wafer_id": str(r.get("wafer") or ""), "status": "Pass", "norm_status": "PASS",
                             "cause": "", "outcome": "PASS", "scan_type": scan_type(lot_id), "recipe": str(r.get("step") or ""),
                             "faults": str(r.get("defects", "")), "scanned_dice": "" if r.get("ndie") is None else str(r.get("ndie")),
                             "yield": "", "wafer_start_time": _fmt(t), "wafer_end_time": _fmt(end) if end else "",
                             "batch_start": _fmt(bs), "batch_end": _fmt(be), "report": report, "ini_match": "EXACT",
                             "time_basis": "STRICT_IN_BATCH", "slots": "", "data_issue": "", "issue_codes": ""})
    return rows
