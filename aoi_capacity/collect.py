"""수집 코어 — Camtek AOI BatchReport(.htm) 와 각 Wafer 의 WaferInfo.ini 를 읽어 원천 행을 만들고
증분 캐시에 쌓은 뒤, template.html 에 데이터를 넣어 HTML 한 장을 쓴다. 표준 라이브러리만 쓴다.

설계 규칙(인수인계 문서 + CLAUDE.md)
  * ★ NAS 는 읽기만 한다. 쓰기(`open(...,'w')`, `os.replace`, `os.makedirs`)는 `_save_cache` · `write_html` · `_write_csv`
    세 함수에만 있고, 각 함수가 첫 줄에서 `nas_guard.assert_local` 을 부른다. 회귀 가드: dev/tests/test_nas_guard.py
  * Scanresult 를 재귀 검색하지 않는다. INI 경로는 정확히 계산해 존재만 확인한다:
        {scan_root}/{equipment}/{process_code}/{lot}/{wafer_id}/WaferInfo.ini
  * 필요한 INI 키만 읽는다. Report 하나가 깨져도 기록만 남기고 계속 간다.
  * 진행 보고: `progress(done, total, phase)` — 총량을 모르는 단계는 `total<=0`(busy).
    장비별 상태는 `on_device(name, state, detail)` — state ∈ {"listing","parsing","done","error","skipped"}.
  * 취소: `should_stop()` 이 True 면 `CollectCancelled`. 캐시·HTML 은 손대지 않아 이전 상태가 그대로 남는다.

수집 기간
  * 처음(캐시 없음) 또는 `backfill=True`: 수정시각이 최근 `backfill_days` 안인 Report 를 전부.
  * 그 뒤: 장비별로 마지막으로 가져온 Report 수정시각 이후 것 전부(시계 오차 60초 여유). 처음 보는 장비는 backfill 창.
  * 캐시는 `retention_days` 동안 보관.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Tuple

from . import devices as devices_mod
from . import i18n, nas_guard

_LOG = logging.getLogger("aoi.collect")

DEFAULT_CONFIG: Dict[str, object] = {
    "devices_csv": "",
    "nas_roots": [],
    "report_dir": "Report",
    "scan_dir": "Scanresult",
    "backfill_days": 30,
    "retention_days": 90,
    "output_dir": "",
    "output_name": "AOI_capacity.html",
    "write_csv": False,
    "cache_file": "",
}
INI_KEYS = {
    "Recipe": ["Name"],
    "AutoCycleInfo": ["Machine", "Operator", "WaferStartTime", "WaferEndTime", "BatchStartTime", "OCRID",
                      "ActiveStation", "ActiveSlot", "FillID", "CarrierID", "UseLot", "UseWaferID"],
    "BatchInfo": ["GlobalLotId", "OperatorId"],
}
OUT_COLS = ["device", "lot", "wafer_id", "status", "norm_status", "recipe",
            "wafer_start_time", "wafer_end_time", "batch_start", "ini_match", "data_issue"]
REPORT_RE = re.compile(r"^(.+?)_(\d{4})_(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)
DT_FORMATS = ["%d-%b-%y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%d-%b-%y %H:%M:%S"]
CLOCK_SKEW_SEC = 60

ProgressFn = Callable[[int, int, str], None]
LogFn = Callable[[str], None]
DeviceFn = Callable[[str, str, str], None]


class CollectCancelled(Exception):
    """사용자가 중지했다. 캐시·출력은 바뀌지 않았다."""


@dataclass
class RunPlan:
    first_run: bool
    known_devices: int
    backfill_days: int


# ----------------------------------------------------------------------------- helpers
def parse_dt(s) -> Optional[dt.datetime]:
    s = (s or "").strip()
    for f in DT_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def norm_status(s) -> str:
    t = (s or "").strip().lower()
    if t == "pass":
        return "PASS"
    if "skip" in t:
        return "SKIPPED"
    if "failed to read wafer id" in t:
        return "ID_READ_ERROR"
    if "scan error" in t:
        return "SCAN_ERROR"
    if "wafer aborted by user" in t:
        return "USER_ABORT"
    if "abort" in t:
        return "ABORTED"
    return "OTHER" if t else ""


class TableParser(HTMLParser):
    """모든 <table> 을 행 단위 셀 텍스트 목록으로 모은다(중첩 표는 펼침)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: List[List[List[str]]] = []
        self._t = None
        self._r = None
        self._c = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._t = []
        elif tag == "tr" and self._t is not None:
            self._r = []
        elif tag in ("td", "th") and self._r is not None:
            self._c = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._c is not None and self._r is not None:
            self._r.append(re.sub(r"\s+", " ", "".join(self._c)).strip())
            self._c = None
        elif tag == "tr" and self._r is not None and self._t is not None:
            self._t.append(self._r)
            self._r = None
        elif tag == "table" and self._t is not None:
            self.tables.append(self._t)
            self._t = None

    def handle_data(self, data):
        if self._c is not None:
            self._c.append(data)


def parse_report(name: str, text: str) -> dict:
    m = REPORT_RE.match(name)
    rep = {"equipment": m.group(1) if m else "", "process_code": m.group(2) if m else "",
           "report_lot": m.group(3) if m else "", "summary": {}, "wafers": []}
    p = TableParser()
    p.feed(text)
    for tb in p.tables:
        if not tb:
            continue
        head = [h.lower() for h in tb[0]]
        iw = next((i for i, h in enumerate(head) if re.fullmatch(r"wafer\s*id", h)), -1)
        il = next((i for i, h in enumerate(head) if h == "lot"), -1)
        if iw >= 0 and il >= 0:
            def idx(k):
                return next((i for i, h in enumerate(head) if h.startswith(k)), -1)

            ix = {"status": idx("pass"), "recipe": idx("recipe")}
            for row in tb[1:]:
                if len(row) <= iw:
                    continue

                def g(i, row=row):
                    return row[i] if 0 <= i < len(row) else ""

                rep["wafers"].append({"lot": row[il], "wafer_id": row[iw],
                                      "status": g(ix["status"]), "recipe": g(ix["recipe"])})
        else:
            for row in tb:
                for i in range(0, len(row) - 1, 2):
                    k = re.sub(r"[:\s]+$", "", row[i])
                    if k and k not in rep["summary"]:
                        rep["summary"][k] = row[i + 1]
    return rep


def read_ini(path) -> dict:
    out: Dict[str, Dict[str, str]] = {}
    sec = ""
    for line in nas_guard.read_text(path).splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line[0] == "[" and line.endswith("]"):
            sec = line[1:-1]
            out.setdefault(sec, {})
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if sec in INI_KEYS and k in INI_KEYS[sec]:
            out[sec][k] = v.strip()
    return out


def rows_for_report(dev_name: str, rep: dict, scan_root: str) -> List[dict]:
    rows = []
    s = rep["summary"]
    for w in rep["wafers"]:
        r = {"device": dev_name, "lot": w["lot"], "wafer_id": w["wafer_id"], "status": w["status"],
             "norm_status": norm_status(w["status"]), "recipe": w["recipe"] or s.get("Recipe", ""),
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": s.get("Batch Start", ""),
             "ini_match": "", "data_issue": ""}
        if re.match(r"^loadport", w["lot"], re.I) or re.match(r"^slot\s*\d+", w["wafer_id"], re.I) or not w["wafer_id"]:
            r["ini_match"], r["data_issue"] = "NO_WAFER_ID", "LoadPort/Slot 행이라 INI 경로를 만들 수 없음"
        else:
            ini_path = os.path.join(scan_root, rep["equipment"], rep["process_code"], w["lot"], w["wafer_id"], "WaferInfo.ini")
            if not os.path.isfile(ini_path):
                r["ini_match"], r["data_issue"] = "NOT_FOUND", "예상 경로에 WaferInfo.ini 없음"
            else:
                try:
                    a = read_ini(ini_path).get("AutoCycleInfo", {})
                    r["ini_match"] = "EXACT"
                    r["wafer_start_time"], r["wafer_end_time"] = a.get("WaferStartTime", ""), a.get("WaferEndTime", "")
                    iss = []
                    st, en = parse_dt(r["wafer_start_time"]), parse_dt(r["wafer_end_time"])
                    if not (st and en and en >= st):
                        iss.append("Wafer 시작/종료 시각 누락 또는 역전")
                    if a.get("UseLot") and a["UseLot"] != w["lot"]:
                        iss.append("Lot 불일치")
                    if a.get("UseWaferID") and a["UseWaferID"] != w["wafer_id"]:
                        iss.append("Wafer ID 불일치")
                    r["data_issue"] = "; ".join(iss)
                except Exception as e:  # noqa: BLE001
                    r["ini_match"], r["data_issue"] = "READ_ERROR", f"{type(e).__name__}: {e}"
        rows.append(r)
    return rows


# ----------------------------------------------------------------------------- cache
def _load_cache(cfg: dict, full: bool = False, log: Optional[LogFn] = None) -> dict:
    cache: dict = {"reports": {}, "last_mtime": {}}
    path = cfg.get("cache_file") or ""
    if full or not path or not os.path.isfile(path):
        return cache
    try:
        loaded = json.loads(nas_guard.read_text(path))
        if isinstance(loaded, dict):
            cache.update(loaded)
            cache.setdefault("reports", {})
            cache.setdefault("last_mtime", {})
    except Exception as e:  # noqa: BLE001
        _say(log, f"캐시 읽기 실패, 새로 시작: {e}")
    return cache


def _save_cache(cfg: dict, cache: dict) -> None:
    nas_guard.check_cfg(cfg)  # ★ NAS 아래에는 절대 쓰지 않는다
    path = cfg["cache_file"]
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, path)


def plan_run(cfg: dict, full: bool = False, backfill: bool = False) -> RunPlan:
    """UI 안내용 — 캐시만 보고 이번 실행이 어떤 성격인지 알려준다(NAS 접근 없음)."""
    cache = _load_cache(cfg, full=full)
    first = full or backfill or not cache.get("reports")
    return RunPlan(first_run=first, known_devices=len(cache.get("last_mtime", {})), backfill_days=int(cfg["backfill_days"]))


# ----------------------------------------------------------------------------- collect
def _say(log: Optional[LogFn], msg: str) -> None:
    _LOG.info(msg)
    if log:
        log(msg)


def _check(should_stop: Optional[Callable[[], bool]]) -> None:
    if should_stop and should_stop():
        raise CollectCancelled()


def _list_new_reports(devs, cache, cfg, backfill, log, progress, on_device, should_stop):
    """1차 패스: 장비마다 Report 폴더를 한 번 나열(scandir+stat 만)해 읽을 파일을 고른다. NAS 읽기 전용."""
    reports, last = cache["reports"], cache["last_mtime"]
    backfill_since = time.time() - float(cfg["backfill_days"]) * 86400
    plan = []
    for i, d in enumerate(devs):
        _check(should_stop)
        progress(0, 0, i18n.KO.COLLECT_PHASE_LIST_FMT.format(device=d["name"], i=i + 1, n=len(devs)))
        on_device(d["name"], "listing", "")
        dm = {"name": d["name"], "note": d["path"], "reports": 0, "found": 0, "error": ""}
        rep_dir = os.path.join(d["path"], cfg["report_dir"])
        try:
            files = [e for e in nas_guard.scandir(rep_dir) if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
            files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            since = backfill_since if (backfill or d["name"] not in last) else float(last[d["name"]]) - CLOCK_SKEW_SEC
            pick = [e for e in files if e.stat().st_mtime >= since
                    and not (e.path in reports and abs(reports[e.path]["mtime"] - e.stat().st_mtime) < 1
                             and reports[e.path].get("device") == d["name"])]
            newest = max((e.stat().st_mtime for e in files), default=None)
            dm["found"], dm["reports"] = len(files), len(pick)
            if pick:
                _say(log, f"[{d['name']}] Report {len(files)}개 중 새 파일 {len(pick)}개")
            plan.append((d, dm, pick, newest))
        except OSError as ex:
            dm["error"] = f"{type(ex).__name__}: {ex}"
            _say(log, f"[{d['name']}] {dm['error']}")
            on_device(d["name"], "error", dm["error"])
            plan.append((d, dm, [], None))
    return plan


def collect(cfg: dict, full: bool = False, backfill: bool = False, *,
            progress: Optional[ProgressFn] = None, log: Optional[LogFn] = None,
            should_stop: Optional[Callable[[], bool]] = None,
            on_device: Optional[DeviceFn] = None) -> Tuple[List[dict], List[dict], List[dict]]:
    """NAS 를 읽어 (rows, dev_meta, errors) 를 돌려주고 캐시를 갱신한다. HTML 은 `write_html` 이 따로 쓴다."""
    progress = progress or (lambda d, t, p: None)
    on_device = on_device or (lambda n, s, d: None)
    nas_guard.check_cfg(cfg)  # 출력·캐시가 NAS 아래면 시작조차 하지 않는다
    progress(0, 0, i18n.KO.COLLECT_PHASE_DEVICES)
    cache = _load_cache(cfg, full=full, log=log)
    backfill = backfill or full or not cache["reports"]
    devs = devices_mod.resolve_devices(cfg, log)
    if backfill:
        _say(log, f"초기 수집: 최근 {cfg['backfill_days']}일 안의 Report 를 전부 읽습니다")
    plan = _list_new_reports(devs, cache, cfg, backfill, log, progress, on_device, should_stop)

    reports, last = cache["reports"], cache["last_mtime"]
    total = sum(len(pick) for _, _, pick, _ in plan)
    done, n_new, errors, dev_meta = 0, 0, [], []
    progress(0, total, i18n.KO.COLLECT_PHASE_DEVICES)
    for d, dm, pick, newest in plan:
        if dm["error"]:
            dev_meta.append(dm)
            continue
        scan_root = os.path.join(d["path"], cfg["scan_dir"])
        on_device(d["name"], "parsing", "")
        for e in pick:
            _check(should_stop)
            progress(done, total, i18n.KO.COLLECT_PHASE_PARSE_FMT.format(device=d["name"], name=e.name))
            try:
                rep = parse_report(e.name, nas_guard.read_text(e.path))
                reports[e.path] = {"mtime": e.stat().st_mtime, "device": d["name"],
                                   "rows": rows_for_report(d["name"], rep, scan_root), "seen": time.time()}
                n_new += 1
            except Exception as ex:  # noqa: BLE001
                errors.append({"device": d["name"], "path": e.path, "error": f"{type(ex).__name__}: {ex}"})
            done += 1
        # 커서는 이 장비의 파싱이 끝난 뒤에만 전진 — 중간에 취소되면 다음에 같은 파일을 다시 본다
        if newest is not None:
            last[d["name"]] = max(float(last.get(d["name"], 0)), newest)
        on_device(d["name"], "done", "")
        dev_meta.append(dm)
    _check(should_stop)

    progress(total, total, i18n.KO.COLLECT_PHASE_RETENTION)
    cutoff = dt.datetime.now() - dt.timedelta(days=float(cfg["retention_days"]))

    def newest_of(entry):
        ts = [parse_dt(r.get("wafer_end_time") or r.get("batch_start")) for r in entry["rows"]]
        ts = [t for t in ts if t]
        return max(ts) if ts else dt.datetime.fromtimestamp(entry.get("seen", 0))

    for k in [k for k, v in reports.items() if newest_of(v) < cutoff]:
        del reports[k]
    _save_cache(cfg, cache)
    rows = [r for v in reports.values() for r in v["rows"]]
    _say(log, f"새로 읽은 Report {n_new}개 · 캐시 Report {len(reports)}개 · Wafer 행 {len(rows)} · 오류 {len(errors)}건")
    return rows, dev_meta, errors


# ----------------------------------------------------------------------------- output
def _version_info() -> dict:
    try:
        from .utils import updater  # 지연 import: 업데이터가 없어도 수집은 돌아야 한다

        return updater.current_version() or {}
    except Exception:  # noqa: BLE001
        return {}


def write_html(cfg: dict, rows: List[dict], dev_meta: List[dict], errors: List[dict], started: float, *,
               mode: str = "auto", log: Optional[LogFn] = None, progress: Optional[ProgressFn] = None) -> str:
    """template.html 에 데이터를 넣어 출력 폴더에 HTML 한 장을 쓴다. 임시 파일에 쓴 뒤 교체(원자적)."""
    nas_guard.check_cfg(cfg)  # ★ NAS 아래에는 절대 쓰지 않는다
    if progress:
        progress(0, 0, i18n.KO.COLLECT_PHASE_WRITE)
    from .utils import paths

    tpl = nas_guard.read_text(paths.template_path())
    ver = _version_info()
    now = dt.datetime.now()
    meta = {"generated": now.strftime("%Y-%m-%d %H:%M"), "generated_iso": now.isoformat(timespec="seconds"),
            "mode": mode, "devices": dev_meta, "reportErrors": errors, "limit": "",
            "elapsed": int((time.time() - started) * 1000), "retention_days": cfg["retention_days"],
            "sha": ver.get("sha", ""), "branch": ver.get("branch", ""), "repo": ver.get("repo", ""),
            "version": (str(ver.get("sha", ""))[:7]) if ver.get("sha") else ""}
    emb = {"cols": OUT_COLS, "rows": [[r.get(c, "") for c in OUT_COLS] for r in rows], "meta": meta}
    data = json.dumps(emb, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    if "__DATA__" not in tpl:
        raise RuntimeError("template.html 에 __DATA__ 자리가 없습니다")
    out = tpl.replace("__DATA__", data, 1)
    os.makedirs(cfg["output_dir"], exist_ok=True)
    target = os.path.join(cfg["output_dir"], cfg["output_name"])
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(out)
    os.replace(tmp, target)
    _say(log, f"HTML 저장: {target} ({len(out) // 1024} KB)")
    if cfg.get("write_csv"):
        _write_csv(cfg, os.path.splitext(target)[0] + ".csv", rows, log)
    if progress:
        progress(1, 1, i18n.KO.COLLECT_PHASE_DONE)
    return target


def _write_csv(cfg: dict, path: str, rows: List[dict], log: Optional[LogFn] = None) -> None:
    nas_guard.check_cfg(cfg)  # ★ NAS 아래에는 절대 쓰지 않는다
    nas_guard.assert_local(path, nas_guard.roots_for_cfg(cfg))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    _say(log, f"CSV 저장: {path}")
