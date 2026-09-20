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
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Tuple

from . import devices as devices_mod
from . import i18n, nas_guard, scope

_LOG = logging.getLogger("aoi.collect")

#: NAS 읽기는 **기다리는 시간이 대부분**이다(SMB 왕복 지연). Report 하나마다 본문 1회 + Wafer 마다
#: INI 존재 확인·읽기가 붙어 3일치 30대면 왕복이 수만 번이다. 한 줄로 읽으면 그 지연이 전부 더해지므로
#: 여러 개를 동시에 읽는다. 읽기만 하니 순서가 바뀌어도 결과는 같다(합치는 일은 메인 스레드가 한다).
#: 0·1 이면 예전처럼 한 줄로 읽는다. 너무 키우면 NAS 가 되레 느려져 8 로 둔다.
READ_WORKERS = 8

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
    "read_workers": READ_WORKERS,                 # NAS 를 동시에 몇 개씩 읽을지(1 = 한 줄로)
}
MAX_READ_RETRY = 3   # 읽기에 실패한 Report 를 몇 번까지 다시 시도하고 커서를 붙잡아 둘지
INI_KEYS = {
    "Recipe": ["Name"],
    "AutoCycleInfo": ["Machine", "Operator", "WaferStartTime", "WaferEndTime", "BatchStartTime", "OCRID",
                      "ActiveStation", "ActiveSlot", "FillID", "CarrierID", "UseLot", "UseWaferID"],
    "BatchInfo": ["GlobalLotId", "OperatorId"],
}
#: ★ 행을 만드는 규칙(`_STATUS_RULES`·`scan_type`·`_is_placeholder`·`_job_setup_by_table_lot`·`rows_for_report`)을
#: 바꾸면 올린다. 캐시는 Report 의 수정시각만 보고 재파싱을 건너뛰므로, 이 번호가 다르면 캐시를 읽을 때
#: `norm_status`·`scan_type` 을 원문(status·lot)에서 **NAS 접근 없이** 다시 계산한다(`_rederive_rows`).
#: INI 경로가 바뀌는 수정(빈 job 되찾기 등)은 Report 를 다시 읽어야 하므로 '누락 복구'(`recover`)가 따로 있다.
PARSER_VERSION = 5
#: 누락 복구가 다시 읽는 대상 — INI 를 못 찾았거나 읽다 실패한 행이 있는 Report 만.
#: STALE(다른 시도가 덮어쓴 INI)은 다시 읽어도 되돌아오지 않고, NO_WAFER_ID(자리표시)·BATCH_FAILED 는 경로 자체가 없다.
#: MOVED_ONLY(폴더에 `MoveResultFlag` 만 있고 INI 가 없음 = 이동만 되고 아직 스캔 안 함, 실물 AOI-4 `XBL WBG\24`)는 뒤에 스캔되면 INI 가 생긴다.
RECOVERABLE_INI = ("NOT_FOUND", "READ_ERROR", "MOVED_ONLY")
#: 장비별 수집 상태(`dev_meta[].status`) — 화면이 '데이터 없음' 과 '수집 실패' 를 구분해 보여 주는 근거.
DEV_OK, DEV_NO_DATA, DEV_PARTIAL, DEV_UNREACHABLE = "ok", "no_data", "partial", "unreachable"
#: kind = "" (Wafer 한 장) · "batch" (통째로 실패한 배치 한 건 — Wafer 시각이 하나도 없는 시도)
#: `cause`(원인 코드들, 세미콜론) · `outcome`(종료 결과) 은 D43 의 두 축 — `norm_status` 는 호환 필드(원인이 있으면 첫 원인, 없으면 결과).
#: 옛 17열 파일에는 두 열이 없다 — 화면(template)은 언제나 `status` 원문에서 다시 계산하므로 옛 파일도 새 규칙으로 읽힌다.
#: `time_basis`(D37) — INI 의 Wafer 시각이 그 Report 의 Batch 구간에 어떻게 들어가는가(STRICT_IN_BATCH · TOLERANCE_ONLY · BATCH_ONLY · MISSING …).
#: 시간의 주인(같은 INI 시각을 여러 Report 가 참조할 때)은 화면이 원천 행 전체에서 정한다 — 이 열은 사람이 CSV 로 볼 근거다.
#: `slots`(D38) — kind="slot" 합성 행의 영향 Slot 수(서로 다른 LoadPort/Slot 조합). 다른 행은 빈 값.
#: `faults` · `scanned_dice` · `yield`(ROW_SCHEMA_VERSION 5) — Report 표의 Faults · Scanned Dice · Yield 원문 그대로(`100%` 포함). 리포트 화면의 평균 fault 근거.
#: 캐시에 든 옛 행에는 이 세 열이 없다(빈 값으로 나간다) — 채우려면 `--full` 재수집(Report 를 다시 읽어야 한다).
ROW_SCHEMA_VERSION = 5
OUT_COLS = ["device", "kind", "job", "setup", "lot", "wafer_id", "status", "norm_status", "cause", "outcome", "scan_type", "recipe",
            "faults", "scanned_dice", "yield",
            "wafer_start_time", "wafer_end_time", "batch_start", "batch_end", "report", "ini_match", "time_basis", "slots", "data_issue"]
QUALITY_COLS = ("faults", "scanned_dice", "yield")
#: 합성 행의 종류 — "batch"(통째로 실패한 시도, D06) · "slot"(일부 성공한 배치의 자리표시 행 Error, Report 당 1건, D38)
SYNTHETIC_KINDS = ("batch", "slot")
#: HTML 에 박아 넣는 JSON 에서 문자열 풀로 접는 열 — 같은 값이 수없이 되풀이되는 열들이다.
#: (90일치 30대면 행이 십수만 개다. 시각 두 열만 값이 거의 다 달라 접지 않는다.)
POOLED_COLS = tuple(c for c in OUT_COLS if c not in ("wafer_start_time", "wafer_end_time"))
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
    recover_reports: int = 0   # 누락 복구를 켜면 다시 읽을 Report 수(캐시만 보고 센다)


# ----------------------------------------------------------------------------- helpers
def parse_dt(s) -> Optional[dt.datetime]:
    s = (s or "").strip()
    for f in DT_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


#: ★ 원인(cause)과 종료 결과(outcome)는 다른 축이다(사용자 확정 D43).
#:   `Failed to read wafer id … Wafer Skipped.` 는 원인 ID_READ_ERROR + 결과 SKIPPED 다 — 예전에는 `skip` 규칙이 먼저 걸려
#:   ID 인식 실패가 '건너뜀'(정상)에 묻혔다(30일치 실데이터 192행/89 Report). 그래서 **원인 규칙을 전부 먼저** 보고,
#:   남은 것에서 결과를 정한다. `norm_status`(호환 필드)는 '원인이 있으면 첫 원인, 없으면 결과' 다.
#: 순서가 곧 의미다 — 구체적 원인이 앞, 일반 반송(HANDLING_ERROR)이 맨 뒤(fallback). 반송 실패 문구는 `… Batch Aborted. Skipped.` 로
#: 끝나므로 원인/결과 분리로 구조적으로 안전하지만 회귀 테스트는 그대로 둔다. 근거: 30대 30일치 실데이터 상태 문구 213종 전수
#: (`dev/samples/status_mapping_2026-09-18.tsv` 가 문구 → 원인 → 결과 표, 사람이 검토한 고정 fixture).
#: 정규식 문자열은 template.html 의 CAUSE_RULES/OUTCOME_RULES 와 **글자까지 같다**(가드: test_template_contract).
_CAUSE_RULES = [
    # 'Failed to move wafer from LoadPort A to End-Effector Error: Robot: The wafer could not be detected on Hand1 …. Batch Aborted. Skipped.'
    # 'Wafer lost while moving wafer …' · 'Wafer Handling Failure (LoadPort A to End-Effector).' · 'Failed on MoveToStation'
    ("WAFER_LOST", r"wafer\s+lost|failed\s+to\s+sense\s+wafer|failed\s+to\s+move\s+wafer|could\s+not\s+be\s+detected\s+on\s+hand"
                   r"|wafer\s+handling\s+failure|failed\s+on\s+movetostation"),
    ("HW_ERROR", r"hardware\s+failure"),                                   # 'Camera Hardware Failure. … Batch Aborted.'
    ("ID_READ_ERROR", r"failed\s+to\s+read\s+wafer\s+id"),               # '… on PAL' · '… Reading error = ***. Wafer Skipped.'
    # 'Wafer ID Mask length(11) differs from actual Wafer ID length(10). …' · 'Wafer ID Read does not match slot number. …'
    ("ID_FORMAT_ERROR", r"wafer\s+id\s+mask\s+length|wafer\s+id\s+read\s+does\s+not\s+match"),
    ("SCAN_ERROR", r"scan\s*(?:2d|3d)?\s*error"),                          # 'Scan 2D Error.' · 'Scan Error: …'
    ("ALIGN_ERROR", r"alignment\s+error|alignment\s+failed|prealigner\s+fail"),   # 'Alignment Error.' · 'Manual Alignment Failed.' · 'Prealigner failure'
    ("PREALIGNER_RESPONSE_ERROR", r"prealigner:\s*expected\s+status\s+field\s+was\s+not\s+found"),
    ("AUTO_FOCUS_ERROR", r"auto\s+focus\s+error"),
    ("FOCUS_MAPPING_ERROR", r"focus\s+mapping\s+error"),                  # 'Focus Mapping Error. Batch Aborted.' (35행 — 단순 중단이 아니다)
    ("MOTION_ERROR", r"motor->get_position|motion\s+failed\s+to\s+get_continuousscanstatus|acsmotor::get_position"),
    ("CLEAN_REF_ERROR", r"clean\s+reference\s+error"),
    ("NOTHING_TO_SCAN", r"nothing\s+to\s+scan"),
    # 'FAR Model inside recipe is invalid, …' · 'Scan 2D: Illegal Lot Name.' · 'Wafer Map Import failed.' · 'Scanning Multi recipe error.'
    ("RECIPE_ERROR", r"far\s*model|illegal\s+lot\s+name|wafer\s+map\s+import\s+failed|multi\s*recipe\s+error"),
    ("CONTROL_TIMEOUT", r"abort\s+timed-?out"),                            # 'Abort timed-out'
    ("GRAY_LEVEL_LIMIT", r"gray\s+level\s+average\s+exceeds"),
    # 일반 반송·로봇 동작 실패 — 구체 원인이 없을 때의 fallback (맨 뒤)
    ("HANDLING_ERROR", r"robot\s+operation\s+failed|movetabletostoredposandlock|wafer\s+move\s+failure"),
]
#: 종료 결과 — 정확 문구(취소·미확인)를 먼저, 사용자 중단이 일반 중단보다 먼저, 'Aborted. Skipped.' 같은 복합은 마지막 결과인 SKIPPED.
_OUTCOME_RULES = [
    ("PASS", r"^pass$"),
    ("USER_CANCELLED", r"^cancelled$"),
    ("UNKNOWN", r"^-?$"),                                                 # '-' 또는 빈 문구 = 결과 미확인(자리표시)
    ("USER_ABORT", r"wafer\s+aborted\s+by\s+user"),
    ("SKIPPED", r"skip"),
    ("ABORTED", r"abort"),
]
_CAUSE_RX = [(c, re.compile(p, re.I)) for c, p in _CAUSE_RULES]
_OUTCOME_RX = [(c, re.compile(p, re.I)) for c, p in _OUTCOME_RULES]
#: 원인 코드가 있으면 설비 Error(사용자 확정 D43). 결과만 있는 것(중단·건너뜀·취소·미확인)은 여기서 판단하지 않는다.
CAUSE_CODES = tuple(c for c, _ in _CAUSE_RULES)
#: 회귀 가드용 — 옛 이름. 코드 순서 = (원인들, 결과들) 을 이은 것.
_STATUS_RULES = [(c, rx) for c, rx in _CAUSE_RX] + [(c, rx) for c, rx in _OUTCOME_RX if c not in ("PASS", "UNKNOWN")]


def norm_causes(s) -> List[str]:
    """상태 문구에 명시된 실패 유형들(규칙 순서, 중복 없음). 물리적 근본 원인의 확정이 아니다."""
    t = (s or "").strip()
    return [c for c, rx in _CAUSE_RX if rx.search(t)] if t else []


def norm_outcome(s) -> str:
    """종료 결과 — PASS · USER_CANCELLED · UNKNOWN · USER_ABORT · SKIPPED · ABORTED · FAILED(원인만 있고 결과 문구 없음).
    문구가 있는데 원인도 결과도 못 읽으면 UNKNOWN(미지원 문구 — `is_unmapped_status`)."""
    t = (s or "").strip()
    for code, rx in _OUTCOME_RX:
        if rx.search(t):
            return code
    return "FAILED" if norm_causes(t) else "UNKNOWN"


def is_unmapped_status(s) -> bool:
    """읽을 수는 있는데 어느 규칙에도 안 걸리는 문구 — 품질 목록에 남긴다(지우지 않는다)."""
    t = (s or "").strip()
    return bool(t) and t != "-" and not norm_causes(t) and not any(rx.search(t) for _, rx in _OUTCOME_RX)


def cause_field(causes: List[str]) -> str:
    """행에 담는 직렬화 — 규칙 순서로 세미콜론 연결(메모리 모델은 배열)."""
    return ";".join(causes)


def parse_causes(field) -> List[str]:
    return [c for c in str(field or "").split(";") if c]


#: Lot 이름 끝에 붙는 작업 표기 — 실물 근거(AOI-1 Report 2011개 · AOI-8 4784개 · 30대 전수 55,717개):
#:   다시 검사 `MDH-RE` · `XXC 2D 3D RE` · `KFP 3D RESCAN`     재작업 `FVC REWORK` · `KDG-Rework-0831`
#:   시험 가동 `TEST` · `GVG-RDL3 TEST` · `GFX-TEST`  → 가동률에서 **뺀다**(사용자 확정)
#: 3D · 2D · DIA · SRD · EDGE · BUMP TOP · PIDS3/5/7/9 · RDL2/3/4 등은 **검사 종류**라 정상으로 본다(사용자 확정).
#: `RW` 도 정상으로 둔다(사용자 확정 — 재작업인지 확실하지 않다).
_LOT_MARKS = {"TEST": "TEST", "RE": "RESCAN", "RESCAN": "RESCAN", "REWORK": "REWORK"}
#: 가동률(분자·분모) 계산에서 빼는 표기. 화면에는 '제외' 로 남겨 사라지지 않게 한다.
EXCLUDED_SCAN_TYPES = ("TEST",)


#: 토큰 구분자 — 글자(유니코드)·숫자가 아닌 것 전부(사용자 확정 D39: "사이에 뭐가 있든"). `_` 도 구분자다.
#: 30일치 Lot 7,708종에 쓰인 구분자: '-' ' ' '_' '#' '+' ',' "'" '%' '.' '~'. template 의 `lotTokens` 와 같은 규칙.
_TOKEN_SPLIT = re.compile(r"[\W_]+")


def lot_tokens(lot) -> List[str]:
    return [x for x in _TOKEN_SPLIT.split(str(lot or "")) if x]


def scan_type(lot) -> str:
    """Lot 이름에서 작업 표기를 읽는다. 토큰이 통째로 맞을 때만 — `RETURN`·`REX`·`TESTER`·`RW` 는 걸리지 않는다.

    겹치면 **TEST → RESCAN → REWORK** 순. 시험 가동은 가동률에서 빼는 쪽이 세므로 먼저 본다."""
    found = {_LOT_MARKS[t] for t in (x.upper() for x in lot_tokens(lot)) if t in _LOT_MARKS}
    for mark in ("TEST", "RESCAN"):
        if mark in found:
            return mark
    return "REWORK" if found else ""


def norm_lot(lot) -> str:
    """자재 키용 Lot 정규화(D39) — 구분자를 지우고 작업 표기 토큰(RE·RESCAN·REWORK·TEST)만 뺀 뒤 대문자. 화면 표시·Lot 막대에는 쓰지 않는다."""
    return "".join(x for x in lot_tokens(lot) if x.upper() not in _LOT_MARKS).upper()


def norm_wafer(wafer) -> str:
    """자재 키용 Wafer ID 정규화 — 구분자·대소문자만. 앞자리 0·숫자 접미사는 그대로. 작업 표기 토큰을 지우지 않는다."""
    return "".join(lot_tokens(wafer)).upper()


def material_key(lot, wafer) -> str:
    """[정규화 Lot, 정규화 Wafer ID] 의 충돌 없는 직렬화(JSON 배열). 장비명은 넣지 않는다. template 의 `materialKey` 와 같다."""
    return json.dumps([norm_lot(lot), norm_wafer(wafer)], ensure_ascii=False, separators=(",", ":"))


def norm_status(s) -> str:
    """호환 필드 — 원인이 있으면 첫 원인, 없으면 결과. 빈 문구는 빈 값."""
    t = (s or "").strip()
    if not t:
        return ""
    causes = norm_causes(t)
    return causes[0] if causes else norm_outcome(t)


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
    rep = {"name": name, "equipment": m.group(1) if m else "", "process_code": m.group(2) if m else "",
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

            ix = {"status": idx("pass"), "recipe": idx("recipe"),
                  "faults": idx("fault"), "scanned_dice": idx("scanned"), "yield": idx("yield")}
            for row in tb[1:]:
                if len(row) <= iw:
                    continue

                def g(i, row=row):
                    return row[i] if 0 <= i < len(row) else ""

                rep["wafers"].append({"lot": row[il], "wafer_id": row[iw],
                                      "status": g(ix["status"]), "recipe": g(ix["recipe"]),
                                      "faults": g(ix["faults"]).strip(), "scanned_dice": g(ix["scanned_dice"]).strip(),
                                      "yield": g(ix["yield"]).strip()})
        else:
            for row in tb:
                for i in range(0, len(row) - 1, 2):
                    k = re.sub(r"[:\s]+$", "", row[i])
                    if k and k not in rep["summary"]:
                        rep["summary"][k] = row[i + 1]
    job, setup = split_job_setup(rep["summary"].get("Job/Setup", ""))
    if job:
        rep["equipment"], rep["process_code"] = job, setup
    elif not rep["equipment"]:
        # Job/Setup 도 없고 파일명 규칙(4자리 Setup)에도 안 맞는 옛 형식 — 표의 Lot 으로 되찾는다.
        rep["equipment"], rep["process_code"] = _job_setup_by_table_lot(name, rep["wafers"])
    rep["job"], rep["setup"] = rep["equipment"], rep["process_code"]
    if rep["report_lot"] and setup:
        # 파일명의 Job 안에 `…_0614` 같은 4자리가 있으면 REPORT_RE 가 거기서 잘라 Lot 앞에 Setup 이 붙는다
        # (`R_TB500_LIVE_PI3 AOI-22 Copy_0614_Setup1_GVB-PIDS3_…` → `Setup1_GVB-PIDS3`). Job/Setup 이
        # 정답이므로 그 접두사만 떼어 낸다.
        rep["report_lot"] = re.sub(rf"^{re.escape(setup)}[\s_]+", "", rep["report_lot"], flags=re.I)
    if not rep["report_lot"]:                        # 자리표시(`LoadPort A`)는 Lot 이 아니다
        rep["report_lot"] = next((w["lot"] for w in rep["wafers"] if not _is_placeholder(w)), "")
    return rep


#: 파일명 뒤쪽의 `_{날짜}_({시각})_BatchReport.htm` — 앞부분(head)만 떼어 내려고 쓴다.
REPORT_TAIL_RE = re.compile(
    r"^(?P<head>.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)


def _job_setup_by_table_lot(name: str, wafers: List[dict]) -> Tuple[str, str]:
    """`Job/Setup` 도 없고 `REPORT_RE`(4자리 Setup) 에도 안 맞는 파일명에서 job·setup 을 되찾는다.

    파일명은 `{job}_{setup}_{lot}_{날짜}_({시각})_BatchReport.htm` 인데 job 과 lot 에 `_` 가 섞여 있어
    파일명만으로는 경계를 못 가른다. 그런데 **Lot 은 Report 표 안에 적혀 있다** — 뒤에서 그만큼 떼어 내면
    남는 것의 마지막 칸이 setup, 그 앞이 전부 job 이다.
    실물 근거: AOI-10 `R_TB500 TOP D-DIE_0860312PD_SETUP_UDL_26-Sep-14_(01.02.37)_BatchReport.htm`
    — setup 이 `SETUP` 이라 4자리 규칙에 걸리지 않아 job 이 비었고, INI 경로가 통째로 어긋나
    9/15 하루에만 8.8시간이 '미가동' 으로 보였다(실장비 3일치에서 180행).
    """
    m = REPORT_TAIL_RE.match(str(name or ""))
    if not m:
        return "", ""
    lot = next((str(w.get("lot") or "") for w in wafers if not _is_placeholder(w)), "")
    head = m.group("head")
    if not lot or not head.endswith("_" + lot):
        return "", ""
    job, _, setup = head[:-(len(lot) + 1)].rpartition("_")
    return (job.strip(), setup.strip()) if job and setup else ("", "")


#: 4층 장비의 Job 폴더 이름은 Report 의 Job 값과 다르다(사용자가 NAS 에서 확인, 9/20): Report `2D@RE $7781539A-WUP_0858562PD_0A` ↔
#: 폴더 `2D@RE-$7781539A-WUP_0858562PD` — `2D@XX` 뒤 공백이 하이픈이고 끝의 `_0A`/`_0B` 판 번호가 없다. 30일치 4층 NOT_FOUND 2,964행 중
#: 2,789행이 `_0X` 로 끝나는 Job 이었다. 2층(AOI-9 등)은 `-0A` 가 폴더에도 있어 그대로 맞는다.
_JOB_PREFIX_SPACE_RE = re.compile(r"^(2D@[A-Z0-9]+)\s+")
_JOB_REV_SUFFIX_RE = re.compile(r"[_-]0[A-Z]$")


def job_folder_variants(job: str) -> List[str]:
    """Report 의 Job 값으로 만들 **정확 경로 후보** — 원문, `2D@XX ` → `2D@XX-`, 끝의 `_0A`/`-0A` 뗀 것, 둘 다. 중복 없이 순서대로.
    재귀·나열이 아니라 후보 이름 몇 개의 존재만 확인한다(규칙 4). 원문에서 찾으면 나머지는 열지 않는다."""
    job = str(job or "")
    out: List[str] = []
    for v in (job, _JOB_PREFIX_SPACE_RE.sub(r"\1-", job), _JOB_REV_SUFFIX_RE.sub("", job),
              _JOB_REV_SUFFIX_RE.sub("", _JOB_PREFIX_SPACE_RE.sub(r"\1-", job))):
        if v and v not in out:
            out.append(v)
    return out


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


class _IniMemo:
    """수집 한 번 안에서 같은 WaferInfo.ini 를 **한 번만** 연다.

    같은 Wafer 가 여러 Report 에 나오면(재검사) INI 경로가 같다 — 실장비 3일치에서 후보 13,920건 중 1,090건이
    같은 경로의 반복이었다. 결과(읽은 필드 / 없음 / 읽기 오류)를 경로별로 기억하고, 같은 경로를 동시에
    요청한 스레드는 먼저 연 쪽을 기다린다. 실행마다 새로 만든다 — INI 는 다음 검사에서 덮어써지므로
    실행을 넘어 기억하면 안 된다. 읽기 전용이다."""

    MISSING = (FileNotFoundError, NotADirectoryError, IsADirectoryError)

    def __init__(self, reader=None) -> None:
        self._reader = reader or read_ini
        self._lock = threading.Lock()
        self._done: Dict[str, tuple] = {}
        self._busy: Dict[str, threading.Event] = {}
        self._flags: Dict[str, bool] = {}
        self.asked = 0

    def get(self, path: str) -> tuple:
        """→ ("ok", 필드 dict) · ("missing", None) · ("error", 예외)"""
        with self._lock:
            self.asked += 1
            hit = self._done.get(path)
            if hit is not None:
                return hit
            ev = self._busy.get(path)
            owner = ev is None
            if owner:
                ev = self._busy[path] = threading.Event()
        if not owner:
            ev.wait()
            with self._lock:
                return self._done[path]
        try:
            res = ("ok", self._reader(path))
        except self.MISSING:
            res = ("missing", None)
        except Exception as e:  # noqa: BLE001
            res = ("error", e)
        with self._lock:
            self._done[path] = res
            self._busy.pop(path, None)
        ev.set()
        return res

    def exists(self, path: str) -> bool:
        """파일 존재만(`MoveResultFlag`) — 같은 경로는 한 번만 stat 한다. 읽기 전용."""
        with self._lock:
            hit = self._flags.get(path)
        if hit is None:
            hit = os.path.isfile(path)
            with self._lock:
                self._flags[path] = hit
        return hit

    def stats(self) -> Dict[str, int]:
        with self._lock:
            kinds = [k for k, _ in self._done.values()]
            return {"ini_asked": self.asked, "ini_unique": len(self._done),
                    "ini_missing": kinds.count("missing"), "ini_read_error": kinds.count("error")}


def _is_placeholder(w: dict) -> bool:
    """INI 경로를 만들 수 없는 자리표시 행 — `LoadPort A` / `Slot 3`, Wafer ID 나 Lot 이 빈 행.

    ★ Lot 이 비면 `os.path.join` 에서 그 칸이 통째로 사라져 **Setup 폴더의 엉뚱한 INI** 를 가리킨다.
      (실물: AOI-18 은 Report 1,397개 중 절반 이상이 파일명 규칙 밖이라 Lot 을 못 읽는 경우가 있다.)"""
    lot, wid = str(w.get("lot") or ""), str(w.get("wafer_id") or "")
    return bool(re.match(r"^loadport", lot, re.I) or re.match(r"^slot\s*\d+", wid, re.I)
                or not wid.strip() or not lot.strip())


ScanRoots = List[Tuple[str, Optional[dt.date]]]   # (백업 폴더 경로, 경계 날짜 또는 None) — 우선순위 순


def ini_roots_for(batch_start: Optional[dt.datetime], scan_root: str, backups: Optional[ScanRoots]) -> List[str]:
    """이 배치의 INI 가 있을 폴더부터 — 현장은 어느 날짜 기준 **그 이전** Scanresult 를 통째로 백업 폴더로 옮기므로,
    배치 시작일이 경계보다 이른 첫 백업이 1순위다(확인 횟수는 지금과 같은 1번). 거기 없을 때만 나머지를 순서대로 본다.
    경계를 모르는 백업(`Scanresult - 5.9.3`)은 맨 뒤. 백업이 없으면 예전 그대로 `[scan_root]`."""
    backups = list(backups or [])
    if not backups:
        return [scan_root]
    first = scan_root
    if batch_start is not None:
        for root, cut in sorted((b for b in backups if b[1]), key=lambda b: (b[1], b[0])):
            if batch_start.date() < cut:
                first = root
                break
    rest = [scan_root] + [root for root, _ in backups]
    return [first] + [r for r in rest if r != first]


def rows_for_report(dev_name: str, rep: dict, scan_root: str, memo: Optional[_IniMemo] = None,
                    backups: Optional[ScanRoots] = None) -> List[dict]:
    """Report 한 장 → Wafer 행들(+ 통째로 실패한 배치면 배치 행 하나).

    `backups` 가 있으면 INI 를 `ini_roots_for` 순서로 찾는다(정확 경로만, 재귀 없음). 백업에서 찾은 행은 `data_issue` 에 폴더 이름을 남긴다.
    어느 폴더에도 INI 가 없는데 1순위 폴더의 Wafer 자리에 `MoveResultFlag` 만 있으면 `MOVED_ONLY`(이동만 되고 스캔 안 함) — NOT_FOUND 와 섞지 않는다.

    ★ WaferInfo.ini 는 재검사 때 **같은 경로에 덮어써진다**(실물 확인: AOI-25 9/14 00NSP049XYG7).
      그래서 옛 시도의 Report 행에도 '나중 시도의 시각' 이 붙는다. 이를 그대로 쓰면 같은 시간이
      여러 번 계산된다. → INI 시각이 이 Report 의 `Batch Start~End` 밖이면 **이 시도의 것이 아니므로
      시간을 쓰지 않는다**(`ini_match="STALE"`). 값을 지어내지 않고, 시각을 모른다고 표시한다."""
    rows = []
    memo = memo if memo is not None else _IniMemo()
    s = rep["summary"]
    b_start, b_end = parse_dt(s.get("Batch Start", "")), parse_dt(s.get("Batch End", ""))
    for w in rep["wafers"]:
        causes = norm_causes(w["status"])
        r = {"device": dev_name, "kind": "", "job": rep.get("job", ""), "setup": rep.get("setup", ""),
             "report": rep.get("name", ""), "lot": w["lot"], "wafer_id": w["wafer_id"], "status": w["status"],
             "norm_status": norm_status(w["status"]), "cause": cause_field(causes), "outcome": norm_outcome(w["status"]),
             "scan_type": scan_type(w["lot"]),
             "recipe": w["recipe"] or s.get("Recipe", ""),
             "faults": w.get("faults", ""), "scanned_dice": w.get("scanned_dice", ""), "yield": w.get("yield", ""),
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": s.get("Batch Start", ""),
             "batch_end": s.get("Batch End", ""), "ini_match": "", "time_basis": "MISSING", "slots": "", "data_issue": ""}
        if _is_placeholder(w):
            r["ini_match"], r["data_issue"] = "NO_WAFER_ID", "LoadPort/Slot 행이라 INI 경로를 만들 수 없음"
        else:
            jobs_try = job_folder_variants(rep["equipment"])
            rels = [os.path.join(j, rep["process_code"], w["lot"], w["wafer_id"]) for j in jobs_try]
            roots = ini_roots_for(b_start, scan_root, backups)
            # 존재 확인(stat) 없이 바로 연다 — SMB 왕복이 행마다 2번에서 1번으로 준다. 없으면 open 이 알려 준다.
            # 루트(지금 폴더 · 백업) 바깥 순서, Job 폴더 이름 후보 안쪽 순서 — 원문 이름에서 찾으면 나머지는 열지 않는다.
            kind, got, found_in, found_job = "missing", None, roots[0], jobs_try[0]
            for root in roots:
                for j, rel in zip(jobs_try, rels):
                    kind, got = memo.get(os.path.join(root, rel, "WaferInfo.ini"))
                    if kind != "missing":
                        found_in, found_job = root, j
                        break
                if kind != "missing":
                    break
            if kind == "missing":
                if any(memo.exists(os.path.join(roots[0], rel, "MoveResultFlag")) for rel in rels):
                    r["ini_match"], r["data_issue"] = "MOVED_ONLY", "Wafer 폴더에 MoveResultFlag 만 있고 WaferInfo.ini 없음 — 이동만 되고 스캔 안 함"
                else:
                    r["ini_match"], r["data_issue"] = "NOT_FOUND", ("예상 경로에 WaferInfo.ini 없음" if len(roots) == 1
                                                                  else f"예상 경로와 백업 폴더 {len(roots) - 1}개 어디에도 WaferInfo.ini 없음")
            elif kind == "error":
                r["ini_match"], r["data_issue"] = "READ_ERROR", f"{type(got).__name__}: {got}"
            else:
                try:
                    a = got.get("AutoCycleInfo", {})
                    r["ini_match"] = "EXACT"
                    r["wafer_start_time"], r["wafer_end_time"] = a.get("WaferStartTime", ""), a.get("WaferEndTime", "")
                    iss = []
                    st, en = parse_dt(r["wafer_start_time"]), parse_dt(r["wafer_end_time"])
                    r["time_basis"] = time_basis(st, en, b_start, b_end)
                    if not (st and en and en >= st):
                        iss.append("Wafer 시작/종료 시각 누락 또는 역전")
                    elif r["time_basis"] == "OUTSIDE_BATCH":
                        r["ini_match"] = "STALE"       # 덮어써진 INI — 이 시도가 아니라 다른 시도의 시각
                        r["wafer_start_time"] = r["wafer_end_time"] = ""
                        iss.append("이 배치 시각 밖의 INI(다시 검사하며 덮어써짐) — 시간 미사용")
                    if a.get("UseLot") and a["UseLot"] != w["lot"]:
                        iss.append("Lot 불일치")
                    if a.get("UseWaferID") and a["UseWaferID"] != w["wafer_id"]:
                        iss.append("Wafer ID 불일치")
                    if found_in != scan_root:
                        iss.append(f"백업 폴더에서 찾음: {os.path.basename(found_in.rstrip(chr(92) + '/'))}")
                    if found_job != rep["equipment"]:
                        iss.append(f"Job 폴더 이름이 Report 와 다름: {found_job}")
                    r["data_issue"] = "; ".join(iss)
                except Exception as e:  # noqa: BLE001
                    r["ini_match"], r["data_issue"] = "READ_ERROR", f"{type(e).__name__}: {e}"
        rows.append(r)
    return synthesize_rows(rows)


def _in_batch_window(st, en, b_start, b_end) -> bool:
    """INI 의 Wafer 시각이 이 Report 의 배치 구간 안인가(여유 `BATCH_WINDOW_MARGIN_SEC`)."""
    return time_basis(st, en, b_start, b_end) in ("STRICT_IN_BATCH", "TOLERANCE_ONLY", "UNKNOWN_BATCH")


def time_basis(st, en, b_start, b_end) -> str:
    """시간 근거(D37) — template 의 `timeBasis` 와 같은 규칙.
    STRICT_IN_BATCH(여유 없이 안) · TOLERANCE_ONLY(±여유로만) · OUTSIDE_BATCH · MISSING · INVALID(역전) · UNKNOWN_BATCH(배치 시각 없음 — 판단하지 않고 그대로 쓴다)."""
    if not (st and en):
        return "MISSING"
    if en < st:
        return "INVALID"
    if not (b_start and b_end):
        return "UNKNOWN_BATCH"
    if b_start <= st and en <= b_end:
        return "STRICT_IN_BATCH"
    margin = dt.timedelta(seconds=BATCH_WINDOW_MARGIN_SEC)
    if (b_start - margin) <= st and en <= (b_end + margin):
        return "TOLERANCE_ONLY"
    return "OUTSIDE_BATCH"


def _is_error_row(r: dict) -> bool:
    """명시적 실패 행 — 원인 코드가 있거나, 결과가 중단(ABORTED·USER_ABORT)·FAILED 인 행. 건너뜀·PASS·취소·미확인은 아니다."""
    return bool(norm_causes(r.get("status"))) or norm_outcome(r.get("status")) in ("ABORTED", "USER_ABORT", "FAILED")


def _lead_error_row(errs: List[dict]) -> Tuple[dict, List[str]]:
    """대표 행과 원인 합집합 — **결정적으로** 고른다(입력 순서를 뒤집어도 같은 대표).

    대표 원인 = 서로 다른 근거 행이 가장 많은 원인, 같으면 규칙 순서(구체적 원인 우선). 원인 없는 행만 있으면 첫 행.
    대표 행 = 그 원인을 가진 행 중 자리표시가 아닌 것 우선, 그 다음 상태 원문 사전순 — 원문은 그대로 보존한다.
    ★ 첫 행을 그냥 쓰면 하위 행의 원인이 대표에 가려진다(E04: ABORTED 부모 아래 명시적 Error 13 Report)."""
    union: List[str] = []
    count: Dict[str, int] = {}
    for r in errs:
        for c in norm_causes(r.get("status")):
            if c not in union:
                union.append(c)
            count[c] = count.get(c, 0) + 1
    order = {c: i for i, c in enumerate(CAUSE_CODES)}
    union.sort(key=lambda c: order[c])
    if union:
        top = max(union, key=lambda c: (count[c], -order[c]))
        cand = [r for r in errs if top in norm_causes(r.get("status"))]
    else:
        cand = list(errs)
    real = [r for r in cand if r.get("ini_match") != "NO_WAFER_ID"]
    lead = min(real or cand, key=lambda r: str(r.get("status") or ""))
    return lead, union


def failed_batch_row(dev_name: str, rep: dict, rows: List[dict]) -> Optional[dict]:
    """통째로 실패한 시도를 **배치 한 건**으로 만든다.

    실물(AOI-25 9/14)에서 확인한 모습: 배치가 중단되면 Wafer 를 한 장도 스캔하지 못해 Scanresult 에
    흔적이 전혀 남지 않고, Report 에는 `LoadPort A / Slot n` 자리표시 행이 20~25줄 생긴다.
    그래서 ① 시간을 아는 유일한 근거는 Report 의 `Batch Start~End` 이고,
    ② 오류는 'Slot 행 24건' 이 아니라 '배치 중단 1건' 으로 세는 게 맞다(사용자 확정).
    정상적으로 일부라도 스캔한 배치는 만들지 않는다. 대표 행·원인 합집합은 `_lead_error_row` 가 결정적으로 고른다.
    `rep` 는 옛 호출 호환용(값은 행에서 읽는다) — 캐시 재구축(`synthesize_rows`)도 같은 규칙을 쓴다."""
    return _batch_from_rows([r for r in rows if r.get("kind", "") == ""])


def _first(rows: List[dict], key: str) -> str:
    return next((str(r.get(key) or "") for r in rows if r.get(key)), "")


def _batch_from_rows(rows: List[dict]) -> Optional[dict]:
    if not rows:
        return None
    b_start, b_end = _first(rows, "batch_start"), _first(rows, "batch_end")
    st, en = parse_dt(b_start), parse_dt(b_end)
    if not (st and en and en >= st):
        return None
    if any(r.get("wafer_start_time") and r.get("wafer_end_time") for r in rows):
        return None                                   # 한 장이라도 이 배치 안에서 검사됐으면 실패가 아니다
    if any(norm_outcome(r.get("status")) == "PASS" for r in rows):
        return None                                   # 정상 통과한 Wafer 가 있으면 실패한 배치가 아니다
                                                      # (INI 가 지워져 시간만 없는 배치를 오류로 만들지 않는다)
    errs = [r for r in rows if _is_error_row(r)]
    if not errs:
        return None
    lead, union = _lead_error_row(errs)
    # ★ Lot 은 **덮어쓰기 전에** 고른다 — 아래 루프가 ini_match 를 전부 BATCH_FAILED 로 바꾸면
    #   'NO_WAFER_ID 가 아닌 행' 조건이 늘 참이 되어 `LoadPort A` 가 Lot 으로 올라온다(실물 30대 중 8건).
    lot = next((r["lot"] for r in rows if r.get("ini_match") not in ("NO_WAFER_ID", "BATCH_FAILED") and r.get("lot")
                and not _is_placeholder(r)), "")
    for r in rows:                                    # 이 배치의 행들은 배치 한 건으로 묶어 센다(사용자 확정)
        r["ini_match"] = "BATCH_FAILED"
    return {"device": _first(rows, "device"), "kind": "batch", "job": _first(rows, "job"), "setup": _first(rows, "setup"),
            "report": _first(rows, "report"), "lot": lot, "wafer_id": "",
            "status": lead["status"], "norm_status": norm_status(lead["status"]), "cause": cause_field(union),
            "outcome": norm_outcome(lead["status"]), "scan_type": scan_type(lot),
            "recipe": lead.get("recipe", ""), "faults": "", "scanned_dice": "", "yield": "", "wafer_start_time": b_start,
            "wafer_end_time": b_end, "batch_start": b_start,
            "batch_end": b_end, "ini_match": "BATCH", "time_basis": "BATCH_ONLY", "slots": "",
            "data_issue": f"검사된 Wafer 없음 — 배치 시각으로만 표시 (행 {len(rows)}개 중 오류 {len(errs)}개)"}


def slot_error_row(rows: List[dict]) -> Optional[dict]:
    """일부만 성공한 배치의 **자리표시(LoadPort/Slot) 행 Error** 를 Report 당 한 건으로 만든다(사용자 확정 D38).

    통째로 실패한 배치가 아니어도 자리표시 행에 명시적 원인(ID 읽기 실패·반송 실패·정렬 오류 …)이 남는다 — 30일치에서 125 Report,
    예전에는 화면에서 아예 빠지거나(62) '건너뜀' 에 묻혔다(65). 행마다 세지 않고 Report 당 1건 + 영향 Slot 수(서로 다른 Lot/Wafer 자리표시 조합).
    정확 발생 시각은 없다 — 시간 미확인(0 기여), 시간 범위는 Batch Start~End(범위 추정). Batch 전체 시간을 Error 시간으로 복사하지 않는다.
    배치 행(kind=batch)이 있는 Report 에는 만들지 않는다(이중 계산 없음)."""
    src = [r for r in rows if r.get("kind", "") == ""]
    if any(r.get("kind") == "batch" for r in rows) or not src:
        return None
    ph = [r for r in src if r.get("ini_match") == "NO_WAFER_ID" and norm_causes(r.get("status"))]
    if not ph:
        return None
    lead, union = _lead_error_row(ph)
    slots = {(str(r.get("lot") or ""), str(r.get("wafer_id") or "")) for r in ph}
    lots = {str(r.get("lot") or "") for r in src if r.get("ini_match") != "NO_WAFER_ID" and r.get("lot") and not _is_placeholder(r)}
    jobs = {str(r.get("job") or "") for r in src}
    lot = next(iter(lots)) if len(lots) == 1 else ""
    note = [] if len(lots) <= 1 else [f"Lot 여러 개({len(lots)})"]
    if len(jobs) > 1:
        note.append(f"Job 여러 개({len(jobs)})")
    b_start, b_end = _first(src, "batch_start"), _first(src, "batch_end")
    return {"device": _first(src, "device"), "kind": "slot", "job": _first(src, "job") if len(jobs) == 1 else "", "setup": _first(src, "setup"),
            "report": _first(src, "report"), "lot": lot, "wafer_id": "",
            "status": lead["status"], "norm_status": norm_status(lead["status"]), "cause": cause_field(union),
            "outcome": norm_outcome(lead["status"]), "scan_type": scan_type(lot), "recipe": lead.get("recipe", ""),
            "faults": "", "scanned_dice": "", "yield": "",
            "wafer_start_time": "", "wafer_end_time": "", "batch_start": b_start, "batch_end": b_end,
            "ini_match": "BATCH_SLOT", "time_basis": "MISSING", "slots": str(len(slots)),
            "data_issue": f"자리표시 행 Error — Report 당 1건 · 영향 Slot {len(slots)}개 · 시간 미확인(Batch 범위 추정)" + (" · " + " · ".join(note) if note else "")}


def synthesize_rows(rows: List[dict]) -> List[dict]:
    """Report 한 장의 행에서 합성 행(batch · slot)을 **결정적으로 다시 만든다** — 새 수집·캐시 재분류·옛 payload 가 같은 규칙.

    slot 행은 지우고 다시 만든다(두 번 돌려도 수·내용이 같다). batch 행은 이미 있으면 그대로 두고 원인만 다시 합친다
    (자식 행의 ini_match 가 BATCH_FAILED 로 바뀌어 있어 되돌릴 원천이 없다), 없으면 지금 규칙으로 만든다."""
    src = [r for r in rows if r.get("kind", "") == ""]
    batch = next((r for r in rows if r.get("kind") == "batch"), None)
    if batch is None:
        batch = _batch_from_rows(src)
    else:
        errs = [x for x in src if _is_error_row(x)]
        batch["cause"] = cause_field(_lead_error_row(errs)[1] if errs else norm_causes(batch.get("status", "")))
    out = list(src)
    if batch:
        out.append(batch)
    slot = slot_error_row(out)
    if slot:
        out.append(slot)
    return out


# ----------------------------------------------------------------------------- cache
def _load_cache(cfg: dict, full: bool = False, log: Optional[LogFn] = None, rederive: bool = True) -> dict:
    """캐시 JSON 을 읽는다. `rederive=True`(수집 경로)면 규칙 번호가 다를 때 행을 지금 규칙으로 다시 계산한다 —
    15만 행이면 몇 초가 걸리므로 **UI 스레드에서 부르는 계획 조회(`plan_run`)는 이것을 끄고** 수집 워커에서만 켠다."""
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
    if rederive and cache.get("parser_version") != PARSER_VERSION:
        n = _rederive_rows(cache)
        if n:
            _say(log, f"분류 규칙이 바뀌어 캐시 행 {n}개의 상태·검사 종류를 다시 계산했습니다(NAS 는 읽지 않음)")
    return cache


def _rederive_rows(cache: dict) -> int:
    """캐시에 든 행의 `norm_status`·`cause`·`outcome`·`scan_type`·`time_basis` 를 지금 규칙으로 다시 계산하고 합성 행(batch·slot)을
    같은 규칙으로 다시 만든다(`synthesize_rows`). 원문(status·lot·시각)만 쓰므로 NAS 접근이 없다. 두 번 돌려도 결과가 같다.

    돌려주는 값은 값이 바뀐 행 수(합성 행 수 변화 포함). 캐시의 `parser_version` 을 지금 번호로 맞춘다."""
    changed = 0
    for entry in cache.get("reports", {}).values():
        rows = entry.get("rows") or []
        for r in rows:
            if r.get("kind") in SYNTHETIC_KINDS:
                continue
            new = {"norm_status": norm_status(r.get("status", "")), "cause": cause_field(norm_causes(r.get("status", ""))),
                   "outcome": norm_outcome(r.get("status", "")), "scan_type": scan_type(r.get("lot", "")),
                   "time_basis": time_basis(parse_dt(r.get("wafer_start_time")), parse_dt(r.get("wafer_end_time")),
                                            parse_dt(r.get("batch_start")), parse_dt(r.get("batch_end")))}
            if any(r.get(k) != v for k, v in new.items()):
                r.update(new)
                changed += 1
            r.setdefault("slots", "")
            for c in QUALITY_COLS:
                r.setdefault(c, "")
        before = json.dumps([r for r in rows if r.get("kind") in SYNTHETIC_KINDS], sort_keys=True, ensure_ascii=False)
        rebuilt = synthesize_rows(rows)
        after = json.dumps([r for r in rebuilt if r.get("kind") in SYNTHETIC_KINDS], sort_keys=True, ensure_ascii=False)
        if before != after:
            changed += 1
        entry["rows"] = rebuilt
    cache["parser_version"] = PARSER_VERSION
    return changed


def _needs_recovery(entry: dict) -> bool:
    """누락 복구 대상인가 — INI 를 못 찾았거나 읽다 실패한 행이 하나라도 있는 Report."""
    return any(r.get("ini_match") in RECOVERABLE_INI for r in entry.get("rows") or ())


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
    cache["parser_version"] = PARSER_VERSION
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, path)


#: 캐시 파일 요약의 메모 — (경로) → (mtime_ns, size, 요약). 계획 조회는 체크박스를 누를 때마다 불리는데
#: 83MB 캐시를 매번 파싱하면 2초, 규칙 번호까지 다르면 7초씩 화면이 멈췄다(실측). 파일이 바뀌면(수집 뒤) 자동으로 다시 읽는다.
_PLAN_MEMO: Dict[str, tuple] = {}


def _cache_summary(path: str) -> dict:
    """계획 조회에 필요한 것만 — Report 수 · 장비 커서 수 · 누락 복구 대상 수. 행은 재분류하지 않는다(수집 워커가 한다)."""
    empty = {"n_reports": 0, "known_devices": 0, "n_recover": 0}
    if not path or not os.path.isfile(path):
        return empty
    try:
        st = os.stat(path)
        key = (st.st_mtime_ns, st.st_size)
    except OSError:
        return empty
    hit = _PLAN_MEMO.get(path)
    if hit and hit[0] == key:
        return hit[1]
    cache = _load_cache({"cache_file": path}, rederive=False)
    summary = {"n_reports": len(cache.get("reports", {})), "known_devices": len(cache.get("last_mtime", {})),
               "n_recover": sum(1 for e in cache.get("reports", {}).values() if _needs_recovery(e))}
    _PLAN_MEMO[path] = (key, summary)
    return summary


def plan_run(cfg: dict, full: bool = False, backfill: bool = False, recover: bool = False) -> RunPlan:
    """UI 안내용 — 캐시만 보고 이번 실행이 어떤 성격인지 알려준다(NAS 접근 없음). 행을 다시 계산하지 않고 결과를 메모한다."""
    s = _cache_summary("" if full else str(cfg.get("cache_file") or ""))
    first = full or backfill or not s["n_reports"]
    return RunPlan(first_run=first, known_devices=s["known_devices"], backfill_days=int(cfg["backfill_days"]),
                   recover_reports=s["n_recover"] if recover and not full else 0)


# ----------------------------------------------------------------------------- collect
def _say(log: Optional[LogFn], msg: str) -> None:
    _LOG.info(msg)
    if log:
        log(msg)


def _check(should_stop: Optional[Callable[[], bool]]) -> None:
    if should_stop and should_stop():
        raise CollectCancelled()


def _workers(cfg: dict, n_tasks: int) -> int:
    """동시에 몇 개를 읽을지. 설정이 1 이하면 한 줄로 읽는다(예전 동작)."""
    try:
        want = int(cfg.get("read_workers", READ_WORKERS) or 1)
    except (TypeError, ValueError):
        want = READ_WORKERS
    return max(1, min(want, max(1, n_tasks)))


def _run(cfg: dict, tasks, fn, should_stop) -> list:
    """작업들을 동시에(또는 한 줄로) 돌리고 **입력 순서 그대로** 결과를 돌려준다.

    ★ 여기서 하는 일은 NAS **읽기**뿐이다. 캐시·행을 합치는 일은 부르는 쪽(메인 스레드)이 한다 —
      스레드가 공유 dict 를 고치지 않으니 순서가 바뀌어도 결과가 달라지지 않는다."""
    tasks = list(tasks)
    if not tasks:
        return []
    n = _workers(cfg, len(tasks))
    if n == 1:
        return [fn(t) for t in tasks]
    with ThreadPoolExecutor(max_workers=n, thread_name_prefix="aoi-read") as pool:
        out = list(pool.map(fn, tasks))
    _check(should_stop)                      # 취소는 각 작업 안에서도 보지만, 끝나고 한 번 더 본다
    return out


def _list_new_reports(devs, cache, cfg, backfill, log, progress, on_device, should_stop, recover=False):
    """1차 패스: 장비마다 Report 폴더를 한 번 나열(scandir+stat 만)해 읽을 파일을 고른다. NAS 읽기 전용.

    장비 30대를 한 줄로 나열하면 SMB 왕복 지연이 30번 더해진다 — 동시에 나열한다(`read_workers`).

    돌려주는 `known` 은 '이미 캐시에 잘 들어 있는 파일들의 수정시각' — 커서를 어디까지 밀어도 되는지
    계산할 때 쓴다(읽기에 실패한 파일을 커서가 넘어가 버리지 않게)."""
    reports, last = cache["reports"], cache["last_mtime"]
    backfill_since = time.time() - float(cfg["backfill_days"]) * 86400
    done = _Counter()

    def one(d):
        _check(should_stop)
        on_device(d["name"], "listing", "")
        did = str(d["id"])
        dm = {"name": d["name"], "id": did, "note": d["path"], "reports": 0, "found": 0, "error": "",
              "report_dir": str(d.get("report_dir") or cfg["report_dir"]), "recovered": 0, "read_errors": 0}
        rep_dir = os.path.join(d["path"], str(d.get("report_dir") or cfg["report_dir"]))
        try:
            files = [e for e in nas_guard.scandir(rep_dir) if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
            files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            # 누락 복구는 커서와 무관하게 backfill 창 전체를 다시 훑되, 다시 읽는 건 복구 대상뿐이다(아래)
            since = backfill_since if (backfill or recover or did not in last) else float(last[did]) - CLOCK_SKEW_SEC
            pick, known = [], []
            for e in files:
                m = e.stat().st_mtime
                if m < since:
                    continue
                cached = reports.get(e.path)
                if cached and abs(float(cached.get("mtime", 0)) - m) < 1 and _is_same_device(cached, e.path, d):
                    if recover and _needs_recovery(cached):
                        dm["recovered"] += 1
                        pick.append(e)
                    else:
                        known.append(m)
                else:
                    pick.append(e)
            dm["found"], dm["reports"] = len(files), len(pick)
            out = (d, dm, pick, known)
        except OSError as ex:
            dm["error"] = f"{type(ex).__name__}: {ex}"
            on_device(d["name"], "error", dm["error"])
            out = (d, dm, [], [])
        i = done.bump()
        progress(i, len(devs), i18n.KO.COLLECT_PHASE_LIST_FMT.format(device=d["name"], i=i, n=len(devs)))
        return out

    plan = _run(cfg, devs, one, should_stop)
    for d, dm, pick, _known in plan:              # 로그는 장비 순서대로 한 번에(스레드에서 섞이지 않게)
        if dm["error"]:
            _say(log, f"[{d['name']}] {dm['error']}")
        elif pick:
            rec = f" (누락 복구 {dm['recovered']}개 포함)" if dm.get("recovered") else ""
            _say(log, f"[{d['name']}] Report {dm['found']}개 중 새 파일 {len(pick)}개{rec}")
    return plan


class _Counter:
    """스레드 여러 개가 같이 세는 진행 카운터."""

    def __init__(self) -> None:
        self._n, self._lock = 0, threading.Lock()

    def bump(self, k: int = 1) -> int:
        with self._lock:
            self._n += k
            return self._n


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


def _backup_roots(d: dict, scan_root: str) -> ScanRoots:
    """장비 dict 의 `scan_dirs`(devices.with_dirs 가 붙임) → (경로, 경계 날짜) 목록. 맨 앞(지금 폴더)은 뺀다."""
    out: ScanRoots = []
    for x in list(d.get("scan_dirs") or [])[1:]:
        path = os.path.join(str(d["path"]), str(x.get("name") or ""))
        if not x.get("name") or path == scan_root:
            continue
        try:
            cut = dt.date.fromisoformat(str(x.get("cutoff"))) if x.get("cutoff") else None
        except ValueError:
            cut = None
        out.append((path, cut))
    return out


def collect(cfg: dict, full: bool = False, backfill: bool = False, *, recover: bool = False,
            progress: Optional[ProgressFn] = None, log: Optional[LogFn] = None,
            should_stop: Optional[Callable[[], bool]] = None,
            on_device: Optional[DeviceFn] = None, stats: Optional[dict] = None) -> Tuple[List[dict], List[dict], List[dict]]:
    """NAS 를 읽어 (rows, dev_meta, errors) 를 돌려주고 캐시를 갱신한다. HTML 은 `write_html` 이 따로 쓴다.

    `stats` 에 dict 를 주면 단계별 경과(ms)·읽은 수·INI 왕복 수를 채워 준다(`write_html` 이 `meta.timing` 으로 박는다).
    현장에서 "어디서 시간이 가는지" 를 재는 유일한 근거다 — 값은 결과에 영향을 주지 않는다.

    `recover` 는 INI 를 못 찾았던 Report(`RECOVERABLE_INI`)만 수정시각과 상관없이 다시 읽는다 — 파서를 고친 뒤
    옛 캐시를 되살리는 길. 나머지 캐시 Report 는 평소처럼 건너뛴다."""
    progress = progress or (lambda d, t, p: None)
    on_device = on_device or (lambda n, s, d: None)
    stats = stats if stats is not None else {}
    clock = time.perf_counter
    t0 = clock()
    nas_guard.check_cfg(cfg)  # 출력·캐시가 NAS 아래면 시작조차 하지 않는다
    progress(0, 0, i18n.KO.COLLECT_PHASE_DEVICES)
    cache = _load_cache(cfg, full=full, log=log)
    backfill = backfill or full or not cache["reports"]
    devs = devices_mod.resolve_devices(cfg, log)
    _migrate_cursors(cache, devs, log)
    stats["devices_ms"] = int((clock() - t0) * 1000)
    t1 = clock()
    if backfill:
        _say(log, f"초기 수집: 최근 {cfg['backfill_days']}일 안의 Report 를 전부 읽습니다")
    elif recover:
        _say(log, f"누락 복구: 최근 {cfg['backfill_days']}일 안에서 INI 를 못 찾았던 Report 만 다시 읽습니다")
    plan = _list_new_reports(devs, cache, cfg, backfill, log, progress, on_device, should_stop, recover=recover)
    stats["list_ms"] = int((clock() - t1) * 1000)
    t2 = clock()

    reports, last, failed = cache["reports"], cache["last_mtime"], cache["failed"]
    total = sum(len(pick) for _, _, pick, _ in plan)
    n_new, errors, dev_meta = 0, [], []
    progress(0, total, i18n.KO.COLLECT_PHASE_DEVICES)

    # ── 2차 패스: Report 를 읽어 행으로 바꾼다. NAS 왕복 지연이 대부분이라 **여러 개를 동시에 읽는다**.
    #    Report 하나가 한 작업이라 장비마다 양이 달라도 알아서 고르게 나뉜다.
    #    스레드는 **읽기만** 하고(공유 dict 를 고치지 않는다), 캐시에 넣는 일은 아래 메인 스레드가 순서대로 한다.
    done, left, left_lock, bad_in = _Counter(), {}, threading.Lock(), {}
    memo = _IniMemo()                         # 같은 WaferInfo.ini 는 이번 실행에서 한 번만 연다
    jobs = []
    for d, dm, pick, _known in plan:
        if dm["error"] or not pick:
            continue
        left[str(d["id"])] = len(pick)
        on_device(d["name"], "parsing", "")
        scan_root = os.path.join(d["path"], str(d.get("scan_dir") or cfg["scan_dir"]))
        backups = _backup_roots(d, scan_root)
        jobs.extend((d, dm, e, scan_root, backups) for e in pick)

    def read_one(job):
        d, _dm, e, scan_root, backups = job
        _check(should_stop)
        t_job = clock()
        mtime = e.stat().st_mtime
        try:
            rep = parse_report(e.name, nas_guard.read_text(e.path))
            out = (job, mtime, rows_for_report(d["name"], rep, scan_root, memo, backups), None, clock() - t_job)
        except CollectCancelled:
            raise
        except Exception as ex:  # noqa: BLE001
            out = (job, mtime, None, f"{type(ex).__name__}: {ex}", clock() - t_job)
        progress(done.bump(), total, i18n.KO.COLLECT_PHASE_PARSE_FMT.format(device=d["name"], name=e.name))
        with left_lock:                       # 여러 스레드가 같이 줄이므로 잠그고 센다
            n = left.get(str(d["id"]))
            n = left[str(d["id"])] = (n - 1) if n is not None else None
            if out[3] is not None:
                bad_in[str(d["id"])] = bad_in.get(str(d["id"]), 0) + 1
            failed_any = bad_in.get(str(d["id"]), 0) > 0
        if n == 0:                            # 이 장비 몫을 다 읽었다 — 실패가 섞였으면 초록이 아니라 '일부 실패'
            on_device(d["name"], "partial" if failed_any else "done", "")
        return out

    by_dev: Dict[str, dict] = {str(d["id"]): {"ok": list(known), "blocked": []}
                               for d, dm, _pick, known in plan if not dm["error"]}
    for (d, _dm, e, _scan, _bk), mtime, rows_of, err, sec in _run(cfg, jobs, read_one, should_stop):
        did = str(d["id"])
        _dm["read_sum_ms"] = _dm.get("read_sum_ms", 0) + int(sec * 1000)   # 병렬로 겹치는 시간의 **합**(경과시간 아님)
        if err is None:
            reports[e.path] = {"mtime": mtime, "device": d["name"], "device_id": did,
                               "rows": rows_of, "seen": time.time(), "parser_version": PARSER_VERSION}
            failed.pop(e.path, None)
            by_dev[did]["ok"].append(mtime)
            n_new += 1
            continue
        tries = int(failed.get(e.path, {}).get("tries", 0)) + 1
        failed[e.path] = {"mtime": mtime, "tries": tries, "device_id": did, "error": err}
        errors.append({"device": d["name"], "path": e.path, "tries": tries, "error": err})
        _dm["read_errors"] += 1
        # 재시도가 남아 있으면 커서를 이 파일 앞에서 멈춰 다음 수집에 다시 읽는다
        by_dev[did]["blocked" if tries < MAX_READ_RETRY else "ok"].append(mtime)
        if tries >= MAX_READ_RETRY:
            _say(log, f"[{d['name']}] {e.name}: {tries}번 실패해 더는 붙잡지 않습니다(오류 목록에는 남습니다)")
    for d, dm, _pick, _known in plan:
        if dm["error"]:
            dev_meta.append(dm)
            continue
        # 커서는 이 장비의 파싱이 끝난 뒤에만 전진 — 중간에 취소되면 다음에 같은 파일을 다시 본다
        cur = by_dev[str(d["id"])]
        _advance_cursor(last, str(d["id"]), cur["ok"], cur["blocked"])
        on_device(d["name"], "partial" if dm["read_errors"] else "done", "")
        dev_meta.append(dm)
    _check(should_stop)
    stats["read_ms"] = int((clock() - t2) * 1000)
    t3 = clock()

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
    _mark_device_status(dev_meta, rows)
    dev_meta.extend(_out_of_scope_meta(cfg, devs))
    stats["cache_ms"] = int((clock() - t3) * 1000)
    stats.update(memo.stats())
    stats.update({"reports_found": sum(int(dm.get("found") or 0) for dm in dev_meta),
                  "reports_read": n_new, "reports_failed": len(errors), "devices": len(devs),
                  "read_workers": _workers(cfg, max(1, len(jobs))), "total_ms": int((clock() - t0) * 1000)})
    _say(log, f"새로 읽은 Report {n_new}개 · 캐시 Report {len(reports)}개 · Wafer 행 {len(rows)} · 오류 {len(errors)}건")
    _say(log, "단계별 경과: 장비 확인 {devices_ms}ms · 목록 {list_ms}ms · 읽기 {read_ms}ms"
              "(Report {reports_read}개 · INI 요청 {ini_asked}건 → 실제 {ini_unique}건, 없음 {ini_missing}) · 캐시 {cache_ms}ms"
              " · 동시 {read_workers}개".format(**stats))
    if hidden:
        _say(log, f"수집 범위({scope.describe(cfg)}) 밖 장비의 캐시 {hidden}행은 화면에서 제외했습니다(캐시는 그대로 둡니다)")
    return rows, dev_meta, errors


def _mark_device_status(dev_meta: List[dict], rows: List[dict]) -> None:
    """장비마다 '접근 못 함 / 일부 Report 실패 / 데이터 없음 / 정상' 을 적는다 — 화면과 완료 안내가 구분해 보여 준다.

    '읽기가 끝났다' 와 '성공했다' 는 다르다: Report 가 전부 깨진 장비를 초록으로 칠하면 안 된다."""
    n_rows: Dict[str, int] = {}
    for r in rows:
        n_rows[str(r.get("device"))] = n_rows.get(str(r.get("device")), 0) + 1
    for dm in dev_meta:
        dm["rows"] = n_rows.get(str(dm["name"]), 0)
        dm["status"] = (DEV_UNREACHABLE if dm.get("error") else DEV_PARTIAL if dm.get("read_errors")
                        else DEV_NO_DATA if not dm["rows"] else DEV_OK)


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


def _embed_rows(rows: List[dict]) -> dict:
    """HTML 에 박을 형태로 접는다 — `POOLED_COLS` 는 문자열 풀의 번호로 바꾼다.

    장비 30대 × 보관 90일이면 행이 십수만 개다. 장비명·Job·Setup·Report 이름·상태 문구는 행마다
    같은 값이 되풀이되므로 그대로 두면 HTML 이 수십 MB 가 된다. 풀로 접으면 그 반복이 사라진다.
    (CSV 는 사람이 읽는 파일이라 접지 않는다 — `_write_csv` 는 원래 문자열을 그대로 쓴다.)"""
    pool: List[str] = []
    index: Dict[str, int] = {}

    def put(v) -> int:
        v = "" if v is None else str(v)
        i = index.get(v)
        if i is None:
            i = index[v] = len(pool)
            pool.append(v)
        return i

    pooled = [c in POOLED_COLS for c in OUT_COLS]
    out = [[put(r.get(c, "")) if pooled[i] else str(r.get(c, "") or "")
            for i, c in enumerate(OUT_COLS)] for r in rows]
    return {"cols": list(OUT_COLS), "pooled": [c for c in OUT_COLS if c in POOLED_COLS],
            "pool": pool, "rows": out}


def write_html(cfg: dict, rows: List[dict], dev_meta: List[dict], errors: List[dict], started: float, *,
               mode: str = "auto", log: Optional[LogFn] = None, progress: Optional[ProgressFn] = None,
               timing: Optional[dict] = None) -> str:
    """template.html 에 데이터를 넣어 출력 폴더에 HTML 한 장을 쓴다. 임시 파일에 쓴 뒤 교체(원자적)."""
    nas_guard.check_cfg(cfg)  # ★ NAS 아래에는 절대 쓰지 않는다
    if progress:
        progress(0, 0, i18n.KO.COLLECT_PHASE_WRITE)
    from .utils import paths

    t_html = time.perf_counter()
    tpl = nas_guard.read_text(paths.template_path())
    ver = _version_info()
    now = dt.datetime.now()
    meta = {"generated": now.strftime("%Y-%m-%d %H:%M"), "generated_iso": now.isoformat(timespec="seconds"),
            "mode": mode, "devices": dev_meta, "reportErrors": errors, "limit": "",
            "scope": {"restricted": not scope.unrestricted(cfg), "devices": scope.scope_list(cfg)},
            "elapsed": int((time.time() - started) * 1000), "retention_days": cfg["retention_days"],
            "timing": dict(timing) if timing else {},
            "sha": ver.get("sha", ""), "branch": ver.get("branch", ""), "repo": ver.get("repo", ""),
            "version": (str(ver.get("sha", ""))[:7]) if ver.get("sha") else ""}
    emb = _embed_rows(rows)
    if meta["timing"]:
        meta["timing"]["html_ms"] = int((time.perf_counter() - t_html) * 1000)   # 템플릿 읽기 + 접기까지(쓰기 전)
    emb["meta"] = meta
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
