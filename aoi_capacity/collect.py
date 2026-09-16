"""수집 코어 — Camtek AOI BatchReport(.htm) 와 각 Wafer 의 WaferInfo.ini 를 읽어 원천 행을 만들고
증분 캐시에 쌓은 뒤, template.html 에 데이터를 넣어 HTML 한 장을 쓴다. 표준 라이브러리만 쓴다.

설계 규칙(인수인계 문서 + CLAUDE.md)
  * ★ NAS 는 읽기만 한다. 쓰기(`open(...,'w')`, `os.replace`, `os.makedirs`)는 `_save_cache` · `write_html` · `_write_csv`
    세 함수에만 있고, 각 함수가 첫 줄에서 `nas_guard.assert_local` 을 부른다. 회귀 가드: dev/tests/test_nas_guard.py
  * Scanresult 를 재귀 검색하지 않는다. INI 경로는 정확히 계산해 존재만 확인한다:
        {scan_root}/{job}/{setup}/{lot}/{wafer_id}/WaferInfo.ini
    job·setup 은 Report 안의 `Job/Setup` 값에서 온다(파일명이 아니다). 옛 형식은 파일명 규칙으로 폴백.
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
from . import i18n, nas_guard, scope

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
    "scope_devices": list(scope.DEFAULT_SCOPE),   # ★ 수집 허용 장비. ["*"] 면 제한 없음
}
MAX_READ_RETRY = 3   # 읽기에 실패한 Report 를 몇 번까지 다시 시도하고 커서를 붙잡아 둘지
INI_KEYS = {
    "Recipe": ["Name"],
    "AutoCycleInfo": ["Machine", "Operator", "WaferStartTime", "WaferEndTime", "BatchStartTime", "OCRID",
                      "ActiveStation", "ActiveSlot", "FillID", "CarrierID", "UseLot", "UseWaferID"],
    "BatchInfo": ["GlobalLotId", "OperatorId"],
}
#: kind = "" (Wafer 한 장) · "batch" (통째로 실패한 배치 한 건 — Wafer 시각이 하나도 없는 시도)
OUT_COLS = ["device", "kind", "lot", "wafer_id", "status", "norm_status", "scan_type", "recipe",
            "wafer_start_time", "wafer_end_time", "batch_start", "batch_end", "ini_match", "data_issue"]
REPORT_RE = re.compile(r"^(.+?)_(\d{4})_(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)
#: 장비마다 다르다 — AOI-8·25 는 `13-Sep-26 01:03:29 PM`, AOI-1 은 `9/16/2026 1:54:03 PM`,
#: INI 의 BatchStartTime 은 `09/10/2026 18:50:08`(24시간제).
DT_FORMATS = ["%d-%b-%y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S",
              "%d-%b-%y %H:%M:%S"]
CLOCK_SKEW_SEC = 60
#: INI 시각이 그 Report 의 Batch 구간에서 이만큼 벗어나면 "다른 시도의 INI" 로 본다(시계 오차 여유).
BATCH_WINDOW_MARGIN_SEC = 600

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


#: 실장비 Report 에서 실제로 나온 표기를 근거로 만든 순서 — 위에서부터 먼저 맞는 것을 쓴다.
#: 근거는 30대 전수 샘플(Report 55,717개 중 2,400행)에서 나온 표기 전부다. 반송 실패는 문구 끝이
#: `… Batch Aborted. Skipped.` 라 `skip` 규칙보다 **위**에 둔다 — 아래에 두면 '건너뜀'(정상)으로 묻힌다.
_STATUS_RULES = [
    # 'Failed to move wafer from LoadPort A to End-Effector Error: Robot: The wafer could not be
    #  detected on Hand1 after the GET motion. . Batch Aborted. Skipped.'
    ("WAFER_LOST", re.compile(r"wafer\s+lost|failed\s+to\s+sense\s+wafer"
                              r"|failed\s+to\s+move\s+wafer|could\s+not\s+be\s+detected\s+on\s+hand", re.I)),
    ("HW_ERROR", re.compile(r"hardware\s+failure", re.I)),             # 'Camera Hardware Failure. … Batch Aborted.'
    ("SKIPPED", re.compile(r"skip", re.I)),
    ("ID_READ_ERROR", re.compile(r"failed\s+to\s+read\s+wafer\s+id", re.I)),
    ("SCAN_ERROR", re.compile(r"scan\s*(?:2d|3d)?\s*error", re.I)),     # 'Scan 2D Error.' · 'Scan Error: …'
    ("ALIGN_ERROR", re.compile(r"alignment\s+error", re.I)),
    # 'FAR Model inside recipe is invalid, …' · 'Scan 2D: Illegal Lot Name.' · 'Wafer Map Import failed.'
    ("RECIPE_ERROR", re.compile(r"far\s*model|illegal\s+lot\s+name|wafer\s+map\s+import\s+failed", re.I)),
    ("USER_ABORT", re.compile(r"wafer\s+aborted\s+by\s+user", re.I)),
    ("ABORTED", re.compile(r"abort", re.I)),
]


#: Lot 이름 끝에 붙는 작업 표기 — 실물 근거(AOI-1 Report 2011개 · AOI-8 4784개 · 30대 전수 55,717개):
#:   다시 검사 `MDH-RE` · `XXC 2D 3D RE` · `KFP 3D RESCAN`     재작업 `FVC REWORK` · `KDG-Rework-0831`
#:   시험 가동 `TEST` · `GVG-RDL3 TEST` · `GFX-TEST`  → 가동률에서 **뺀다**(사용자 확정)
#: 3D · 2D · DIA · SRD · EDGE · BUMP TOP · PIDS3/5/7/9 · RDL2/3/4 등은 **검사 종류**라 정상으로 본다(사용자 확정).
#: `RW` 도 정상으로 둔다(사용자 확정 — 재작업인지 확실하지 않다).
_LOT_MARKS = {"TEST": "TEST", "RE": "RESCAN", "RESCAN": "RESCAN", "REWORK": "REWORK"}
#: 가동률(분자·분모) 계산에서 빼는 표기. 화면에는 '제외' 로 남겨 사라지지 않게 한다.
EXCLUDED_SCAN_TYPES = ("TEST",)


def scan_type(lot) -> str:
    """Lot 이름에서 작업 표기를 읽는다. 토큰이 통째로 맞을 때만 — `RETURN`·`REX` 는 걸리지 않는다.

    겹치면 **TEST → RESCAN → REWORK** 순. 시험 가동은 가동률에서 빼는 쪽이 세므로 먼저 본다."""
    found = {_LOT_MARKS[t] for t in (x.upper() for x in re.split(r"[\s_\-]+", str(lot or "")) if x)
             if t in _LOT_MARKS}
    for mark in ("TEST", "RESCAN"):
        if mark in found:
            return mark
    return "REWORK" if found else ""


def norm_status(s) -> str:
    t = (s or "").strip()
    if t.lower() == "pass":
        return "PASS"
    for code, rx in _STATUS_RULES:
        if rx.search(t):
            return code
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
    """Report 한 장을 (job, setup, lot, wafer 행, 요약)으로 푼다.

    ★ Scanresult 경로의 출처는 **Report 안의 `Job/Setup`** 이다(파일명이 아니다).
      파일명은 `{Job}_{Setup}_{Lot}_{날짜}_({시각})_BatchReport.htm` 인데 Job 과 Lot 에 `_`·` `·`-` 가
      섞여 있어 파일명만으로는 경계를 못 가른다(실장비 516개 중 옛 규칙에 맞는 건 6개뿐이었다).
      `Job/Setup` 이 없는 옛 형식 Report 만 파일명 규칙으로 되돌아간다."""
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
    job, setup = split_job_setup(rep["summary"].get("Job/Setup", ""))
    if job:
        rep["equipment"], rep["process_code"] = job, setup
    rep["job"], rep["setup"] = rep["equipment"], rep["process_code"]
    if rep["report_lot"] and setup:
        # 파일명의 Job 안에 `…_0614` 같은 4자리가 있으면 REPORT_RE 가 거기서 잘라 Lot 앞에 Setup 이 붙는다
        # (`R_TB500_LIVE_PI3 AOI-22 Copy_0614_Setup1_GVB-PIDS3_…` → `Setup1_GVB-PIDS3`). Job/Setup 이
        # 정답이므로 그 접두사만 떼어 낸다.
        rep["report_lot"] = re.sub(rf"^{re.escape(setup)}[\s_]+", "", rep["report_lot"], flags=re.I)
    if not rep["report_lot"]:                        # 자리표시(`LoadPort A`)는 Lot 이 아니다
        rep["report_lot"] = next((w["lot"] for w in rep["wafers"] if not _is_placeholder(w)), "")
    return rep


def split_job_setup(value: str) -> Tuple[str, str]:
    """`TB500_RDL2 - Multi/Setup1` → (`TB500_RDL2 - Multi`, `Setup1`). 마지막 `/` 로만 가른다."""
    v = str(value or "").strip()
    if "/" not in v:
        return (v, "") if v else ("", "")
    job, _, setup = v.rpartition("/")
    return job.strip(), setup.strip()


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


def _is_placeholder(w: dict) -> bool:
    """INI 경로를 만들 수 없는 자리표시 행 — `LoadPort A` / `Slot 3`, Wafer ID 나 Lot 이 빈 행.

    ★ Lot 이 비면 `os.path.join` 에서 그 칸이 통째로 사라져 **Setup 폴더의 엉뚱한 INI** 를 가리킨다.
      (실물: AOI-18 은 Report 1,397개 중 절반 이상이 파일명 규칙 밖이라 Lot 을 못 읽는 경우가 있다.)"""
    lot, wid = str(w.get("lot") or ""), str(w.get("wafer_id") or "")
    return bool(re.match(r"^loadport", lot, re.I) or re.match(r"^slot\s*\d+", wid, re.I)
                or not wid.strip() or not lot.strip())


def rows_for_report(dev_name: str, rep: dict, scan_root: str) -> List[dict]:
    """Report 한 장 → Wafer 행들(+ 통째로 실패한 배치면 배치 행 하나).

    ★ WaferInfo.ini 는 재검사 때 **같은 경로에 덮어써진다**(실물 확인: AOI-25 9/14 00NSP049XYG7).
      그래서 옛 시도의 Report 행에도 '나중 시도의 시각' 이 붙는다. 이를 그대로 쓰면 같은 시간이
      여러 번 계산된다. → INI 시각이 이 Report 의 `Batch Start~End` 밖이면 **이 시도의 것이 아니므로
      시간을 쓰지 않는다**(`ini_match="STALE"`). 값을 지어내지 않고, 시각을 모른다고 표시한다."""
    rows = []
    s = rep["summary"]
    b_start, b_end = parse_dt(s.get("Batch Start", "")), parse_dt(s.get("Batch End", ""))
    for w in rep["wafers"]:
        r = {"device": dev_name, "kind": "", "lot": w["lot"], "wafer_id": w["wafer_id"], "status": w["status"],
             "norm_status": norm_status(w["status"]), "scan_type": scan_type(w["lot"]),
             "recipe": w["recipe"] or s.get("Recipe", ""),
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": s.get("Batch Start", ""),
             "batch_end": s.get("Batch End", ""), "ini_match": "", "data_issue": ""}
        if _is_placeholder(w):
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
                    elif not _in_batch_window(st, en, b_start, b_end):
                        r["ini_match"] = "STALE"       # 덮어써진 INI — 이 시도가 아니라 다른 시도의 시각
                        r["wafer_start_time"] = r["wafer_end_time"] = ""
                        iss.append("이 배치 시각 밖의 INI(다시 검사하며 덮어써짐) — 시간 미사용")
                    if a.get("UseLot") and a["UseLot"] != w["lot"]:
                        iss.append("Lot 불일치")
                    if a.get("UseWaferID") and a["UseWaferID"] != w["wafer_id"]:
                        iss.append("Wafer ID 불일치")
                    r["data_issue"] = "; ".join(iss)
                except Exception as e:  # noqa: BLE001
                    r["ini_match"], r["data_issue"] = "READ_ERROR", f"{type(e).__name__}: {e}"
        rows.append(r)
    failed = failed_batch_row(dev_name, rep, rows)
    if failed:
        rows.append(failed)
    return rows


def _in_batch_window(st, en, b_start, b_end) -> bool:
    """INI 의 Wafer 시각이 이 Report 의 배치 구간 안인가(여유 `BATCH_WINDOW_MARGIN_SEC`)."""
    if not (b_start and b_end):
        return True                                   # 배치 시각을 모르면 판단하지 않는다(그대로 쓴다)
    margin = dt.timedelta(seconds=BATCH_WINDOW_MARGIN_SEC)
    return (b_start - margin) <= st and en <= (b_end + margin)


def failed_batch_row(dev_name: str, rep: dict, rows: List[dict]) -> Optional[dict]:
    """통째로 실패한 시도를 **배치 한 건**으로 만든다.

    실물(AOI-25 9/14)에서 확인한 모습: 배치가 중단되면 Wafer 를 한 장도 스캔하지 못해 Scanresult 에
    흔적이 전혀 남지 않고, Report 에는 `LoadPort A / Slot n` 자리표시 행이 20~25줄 생긴다.
    그래서 ① 시간을 아는 유일한 근거는 Report 의 `Batch Start~End` 이고,
    ② 오류는 'Slot 행 24건' 이 아니라 '배치 중단 1건' 으로 세는 게 맞다(사용자 확정).
    정상적으로 일부라도 스캔한 배치는 만들지 않는다."""
    s = rep["summary"]
    st, en = parse_dt(s.get("Batch Start", "")), parse_dt(s.get("Batch End", ""))
    if not (st and en and en >= st):
        return None
    if any(r["wafer_start_time"] and r["wafer_end_time"] for r in rows):
        return None                                   # 한 장이라도 이 배치 안에서 검사됐으면 실패가 아니다
    if any(norm_status(r["status"]) == "PASS" for r in rows):
        return None                                   # 정상 통과한 Wafer 가 있으면 실패한 배치가 아니다
                                                      # (INI 가 지워져 시간만 없는 배치를 오류로 만들지 않는다)
    errs = [r for r in rows if norm_status(r["status"]) not in ("", "PASS", "SKIPPED")]
    if not errs:
        return None
    real = [r for r in errs if r["ini_match"] != "NO_WAFER_ID"]   # 자리표시(Slot)가 아닌 진짜 Wafer 행
    lead = (real or errs)[0]
    # ★ Lot 은 **덮어쓰기 전에** 고른다 — 아래 루프가 ini_match 를 전부 BATCH_FAILED 로 바꾸면
    #   'NO_WAFER_ID 가 아닌 행' 조건이 늘 참이 되어 `LoadPort A` 가 Lot 으로 올라온다(실물 30대 중 8건).
    lot = next((r["lot"] for r in rows if r["ini_match"] != "NO_WAFER_ID" and r["lot"]), "") \
        or rep.get("report_lot", "")
    for r in rows:                                    # 이 배치의 행들은 배치 한 건으로 묶어 센다(사용자 확정)
        r["ini_match"] = "BATCH_FAILED"
    return {"device": dev_name, "kind": "batch", "lot": lot, "wafer_id": "",
            "status": lead["status"], "norm_status": norm_status(lead["status"]), "scan_type": scan_type(lot),
            "recipe": lead.get("recipe", ""), "wafer_start_time": s.get("Batch Start", ""),
            "wafer_end_time": s.get("Batch End", ""), "batch_start": s.get("Batch Start", ""),
            "batch_end": s.get("Batch End", ""), "ini_match": "BATCH",
            "data_issue": f"검사된 Wafer 없음 — 배치 시각으로만 표시 (행 {len(rows)}개 중 오류 {len(errs)}개)"}


# ----------------------------------------------------------------------------- cache
def _load_cache(cfg: dict, full: bool = False, log: Optional[LogFn] = None) -> dict:
    cache: dict = {"reports": {}, "last_mtime": {}, "failed": {}}
    path = cfg.get("cache_file") or ""
    if full or not path or not os.path.isfile(path):
        return cache
    try:
        loaded = json.loads(nas_guard.read_text(path))
        if isinstance(loaded, dict):
            cache.update(loaded)
            cache.setdefault("reports", {})
            cache.setdefault("last_mtime", {})
            cache.setdefault("failed", {})
    except Exception as e:  # noqa: BLE001
        _say(log, f"캐시 읽기 실패, 새로 시작: {e}")
    return cache


def _migrate_cursors(cache: dict, devs: List[dict], log: Optional[LogFn] = None) -> None:
    """옛 캐시의 '표시명' 커서를 '경로' 커서로 옮긴다(표시명이 바뀌어도 이력이 갈라지지 않게).

    옮길 짝을 못 찾은 키는 건드리지 않는다 — 사용자 데이터는 지우지 않는다."""
    last = cache["last_mtime"]
    for d in devs:
        did = str(d["id"])
        if did in last:
            continue
        for alias in [d.get("name"), *(d.get("aliases") or [])]:
            key = str(alias or "")
            if key and key in last:
                last[did] = last.pop(key)
                _say(log, f"캐시 커서 이관: '{key}' → {d.get('name')} (경로 키)")
                break


def _cache_device(path: str, entry: dict, devs: List[dict]) -> Optional[dict]:
    """캐시에 있는 Report 하나가 지금 수집 대상 장비 중 어디에 속하는지. 파일시스템을 보지 않는다."""
    did = entry.get("device_id")
    for d in devs:
        if did and str(d["id"]) == str(did):
            return d
        if nas_guard.is_under(path, str(d["path"])):
            return d
    return None


def _rows_from_cache(cache: dict, devs: List[dict], cfg: dict) -> Tuple[List[dict], int]:
    """출력용 행 — 범위 밖 장비의 캐시는 **지우지 않고 빼기만** 한다.

    표시명이 바뀐 장비의 옛 행은 현재 표시명으로 바꿔 내보낸다(같은 장비가 둘로 갈라지지 않게)."""
    rows, hidden = [], 0
    unrestricted = scope.unrestricted(cfg)
    for path, entry in cache["reports"].items():
        dev = _cache_device(path, entry, devs)
        if dev is None and not unrestricted:
            name = str(entry.get("device") or "")
            if not scope.is_allowed(cfg, name, scope.path_tail(os.path.dirname(os.path.dirname(path)))):
                hidden += len(entry.get("rows") or ())
                continue
        name = str(dev["name"]) if dev else str(entry.get("device") or "")
        for r in entry.get("rows") or ():
            rows.append({**r, "device": name} if name and r.get("device") != name else r)
    return rows, hidden


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
    """1차 패스: 장비마다 Report 폴더를 한 번 나열(scandir+stat 만)해 읽을 파일을 고른다. NAS 읽기 전용.

    돌려주는 `known` 은 '이미 캐시에 잘 들어 있는 파일들의 수정시각' — 커서를 어디까지 밀어도 되는지
    계산할 때 쓴다(읽기에 실패한 파일을 커서가 넘어가 버리지 않게)."""
    reports, last = cache["reports"], cache["last_mtime"]
    backfill_since = time.time() - float(cfg["backfill_days"]) * 86400
    plan = []
    for i, d in enumerate(devs):
        _check(should_stop)
        progress(0, 0, i18n.KO.COLLECT_PHASE_LIST_FMT.format(device=d["name"], i=i + 1, n=len(devs)))
        on_device(d["name"], "listing", "")
        did = str(d["id"])
        dm = {"name": d["name"], "id": did, "note": d["path"], "reports": 0, "found": 0, "error": ""}
        rep_dir = os.path.join(d["path"], str(d.get("report_dir") or cfg["report_dir"]))
        try:
            files = [e for e in nas_guard.scandir(rep_dir) if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
            files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            since = backfill_since if (backfill or did not in last) else float(last[did]) - CLOCK_SKEW_SEC
            pick, known = [], []
            for e in files:
                m = e.stat().st_mtime
                if m < since:
                    continue
                cached = reports.get(e.path)
                if cached and abs(float(cached.get("mtime", 0)) - m) < 1 and _is_same_device(cached, e.path, d):
                    known.append(m)
                else:
                    pick.append(e)
            dm["found"], dm["reports"] = len(files), len(pick)
            if pick:
                _say(log, f"[{d['name']}] Report {len(files)}개 중 새 파일 {len(pick)}개")
            plan.append((d, dm, pick, known))
        except OSError as ex:
            dm["error"] = f"{type(ex).__name__}: {ex}"
            _say(log, f"[{d['name']}] {dm['error']}")
            on_device(d["name"], "error", dm["error"])
            plan.append((d, dm, [], []))
    return plan


def _is_same_device(cached: dict, path: str, dev: dict) -> bool:
    cid = cached.get("device_id")
    if cid:
        return str(cid) == str(dev["id"])
    return cached.get("device") == dev["name"] or nas_guard.is_under(path, str(dev["path"]))


def _advance_cursor(last: dict, did: str, ok_mtimes, blocked_mtimes) -> None:
    """커서는 **성공적으로 캐시에 들어간 파일까지만** 전진한다.

    읽기에 실패해 아직 재시도가 남은 파일이 있으면 그 파일보다 앞에서 멈춘다 →
    다음 증분 수집에서 그 Report 를 다시 만난다(영구 누락 방지)."""
    cur = float(last.get(did, 0))
    limit = min(blocked_mtimes) if blocked_mtimes else None
    usable = [m for m in ok_mtimes if limit is None or m < limit]
    if usable:
        last[did] = max(cur, max(usable))
    elif cur:
        last[did] = cur


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
    _migrate_cursors(cache, devs, log)
    if backfill:
        _say(log, f"초기 수집: 최근 {cfg['backfill_days']}일 안의 Report 를 전부 읽습니다")
    plan = _list_new_reports(devs, cache, cfg, backfill, log, progress, on_device, should_stop)

    reports, last, failed = cache["reports"], cache["last_mtime"], cache["failed"]
    total = sum(len(pick) for _, _, pick, _ in plan)
    done, n_new, errors, dev_meta = 0, 0, [], []
    progress(0, total, i18n.KO.COLLECT_PHASE_DEVICES)
    for d, dm, pick, known in plan:
        if dm["error"]:
            dev_meta.append(dm)
            continue
        did = str(d["id"])
        scan_root = os.path.join(d["path"], str(d.get("scan_dir") or cfg["scan_dir"]))
        on_device(d["name"], "parsing", "")
        ok_mtimes, blocked = list(known), []
        for e in pick:
            _check(should_stop)
            progress(done, total, i18n.KO.COLLECT_PHASE_PARSE_FMT.format(device=d["name"], name=e.name))
            mtime = e.stat().st_mtime
            try:
                rep = parse_report(e.name, nas_guard.read_text(e.path))
                reports[e.path] = {"mtime": mtime, "device": d["name"], "device_id": did,
                                   "rows": rows_for_report(d["name"], rep, scan_root), "seen": time.time()}
                failed.pop(e.path, None)
                ok_mtimes.append(mtime)
                n_new += 1
            except Exception as ex:  # noqa: BLE001
                tries = int(failed.get(e.path, {}).get("tries", 0)) + 1
                failed[e.path] = {"mtime": mtime, "tries": tries, "device_id": did,
                                  "error": f"{type(ex).__name__}: {ex}"}
                errors.append({"device": d["name"], "path": e.path, "tries": tries,
                               "error": f"{type(ex).__name__}: {ex}"})
                # 재시도가 남아 있으면 커서를 이 파일 앞에서 멈춰 다음 수집에 다시 읽는다
                (blocked if tries < MAX_READ_RETRY else ok_mtimes).append(mtime)
                if tries >= MAX_READ_RETRY:
                    _say(log, f"[{d['name']}] {e.name}: {tries}번 실패해 더는 붙잡지 않습니다(오류 목록에는 남습니다)")
            done += 1
        # 커서는 이 장비의 파싱이 끝난 뒤에만 전진 — 중간에 취소되면 다음에 같은 파일을 다시 본다
        _advance_cursor(last, did, ok_mtimes, blocked)
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
    for k in [k for k, v in failed.items() if dt.datetime.fromtimestamp(float(v.get("mtime", 0))) < cutoff]:
        del failed[k]
    _save_cache(cfg, cache)
    rows, hidden = _rows_from_cache(cache, devs, cfg)
    dev_meta.extend(_out_of_scope_meta(cfg, devs))
    _say(log, f"새로 읽은 Report {n_new}개 · 캐시 Report {len(reports)}개 · Wafer 행 {len(rows)} · 오류 {len(errors)}건")
    if hidden:
        _say(log, f"수집 범위({scope.describe(cfg)}) 밖 장비의 캐시 {hidden}행은 화면에서 제외했습니다(캐시는 그대로 둡니다)")
    return rows, dev_meta, errors


def _out_of_scope_meta(cfg: dict, devs: List[dict]) -> List[dict]:
    """화면에 '수집 안 함' 으로 보여 줄 장비들. devices.csv 텍스트만 읽고 NAS 에는 접근하지 않는다."""
    if scope.unrestricted(cfg):
        return []
    path = cfg.get("devices_csv") or ""
    if not path or not os.path.isfile(path):
        return []
    try:
        rows_csv = devices_mod.read_devices_csv(path)
    except Exception:  # noqa: BLE001 - 목록 표시는 부가 기능이라 실패해도 수집 결과를 막지 않는다
        return []
    live = {str(d["name"]) for d in devs}
    return [{"name": s["name"], "note": s.get("note", ""), "scope": "out",
             "reports": 0, "found": 0, "error": ""}
            for s in devices_mod.skipped_by_scope(rows_csv, cfg) if s["name"] and s["name"] not in live]


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
            "scope": {"restricted": not scope.unrestricted(cfg), "devices": scope.scope_list(cfg)},
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
