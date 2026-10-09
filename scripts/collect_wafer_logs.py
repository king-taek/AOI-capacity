"""Wafer 폴더 로그 모으기 — Scanresult 의 Wafer 폴더에 함께 있는 INI·로그 파일을 Lot 단위로 모아 zip 몇 장으로 만든다.

왜: WaferInfo.ini 말고도 Wafer 폴더에는 레시피별 스캔 시작 시각(`ExtendedScanMetaData_x*.json`), 레시피별 Defect 수
(`ProductionInfo.ini`), 스캔 요약(`ScanLog.ini`) 같은 파일이 있다. 수집기에 넣기 전에 여러 장비·Job·Lot 에서 실물을 본다.

무엇을 하는가
  1. 둘러보기: 장비마다 Report 폴더를 한 번 나열하고 최근 Report 몇 개만 열어 Job/Setup · Lot · Wafer 수 · 오류를 본다.
  2. Lot 고르기: RDL 멀티 · RDL 기타 · PI · PI Enhanced · Kendall · 그 밖의 Job · 4층 · Error 포함 · RESCAN 을 고루(최소 10 Lot),
     장비가 겹치지 않게. 그 뒤에도 마지막 zip 이 25MB 가 될 때까지 Lot 을 더 담는다(시간·Lot 수 상한 안에서).
  3. 담기: Report 의 Job/Setup/Lot 으로 계산한 **정확한 Lot 폴더** 하나를 나열하고, 그 안의 Wafer 폴더마다 파일을 읽는다.
     `.dat`(프레임·Die 기록, 한 장에 수십 MB)와 이미지는 담지 않고 이름·크기만 목록에 남긴다.
  4. 한 Lot 안에서 **내용이 같은 파일은 한 번만** 담는다 — 나머지는 목록에 '= 처음 담은 파일' 로 적는다.
  5. zip 은 한 장에 25MB 이상 29.9MB 이하로 나눈다(마지막 장이 25MB 에 못 미치면 끝에 그 이유를 적는다).

★ NAS 는 **읽기만** 한다. 쓰기는 OUT_DIR(로컬)뿐이고, 저장 위치가 NAS 드라이브면 시작하지 않는다.
★ Scanresult 를 재귀 검색하지 않는다. Report 에서 계산한 Lot 폴더 하나와 그 아래 Wafer 폴더 안만 본다.
★ 표준 라이브러리만 쓴다 — 이 파일 하나만 있으면 돌아간다(`python collect_wafer_logs.py`).

    python collect_wafer_logs.py                 # 기본: DEVICE_ROOTS 전부 둘러보고 OUT_DIR 에 zip
    python collect_wafer_logs.py --plan          # 고를 Lot 만 보여 주고 끝(파일은 읽지 않음)
    python collect_wafer_logs.py --roots "X:\\AOI-1" "I:\\4F-AOI-01" --min-lots 4
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
import time
import zipfile
import zlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  사용자가 고치는 값 — 저장 위치와 장비 경로
OUT_DIR = r"C:\Users\304236\Desktop\AOI가동률이얼마나될까요\ini 수집"
DEVICE_ROOTS = [
    r"X:\AOI-1", r"X:\AOI-2", r"X:\AOI-3", r"X:\AOI-4", r"X:\AOI-5", r"X:\AOI-6", r"X:\AOI-7",
    r"M:\AOI-8", r"M:\AOI-9",
    r"V:\AOI-10", r"V:\AOI-11", r"V:\AOI-12", r"V:\AOI-13", r"V:\AOI-14", r"V:\AOI-15", r"V:\AOI-16",
    r"P:\AOI-17", r"P:\AOI-18", r"P:\AOI-19", r"P:\AOI-20", r"P:\AOI-21", r"P:\AOI-22", r"P:\AOI-23",
    r"Y:\AOI-24", r"Y:\AOI-25",
    r"I:\4F-AOI-01", r"I:\4F-AOI-02", r"I:\4F-AOI-03", r"I:\4F-AOI-04", r"I:\4F-AOI-05",
]
# ══════════════════════════════════════════════════════════════════════════════

#: 수집 창 버튼(`aoi_capacity/workers/wafer_logs.py`)이 기대하는 이 파일의 호출 방식 판 — `parse_args` · `run(args, log, should_stop, result)`.
#: 앱이 옛 사본(예: 손으로 넣은 첫 판)을 불러 엉뚱한 오류를 내지 않도록 판을 확인한다. 호출 방식을 바꾸면 둘 다 올린다.
TOOL_API = 5                       # 3: --wide · 4: --all · 5: --all 이 Job별 최소 · 10장 상한 · 암호화(.enc)
#: zip 한 장의 크기 — MB(10^6) 로 보든 MiB(2^20) 로 보든 '25MB 이상 · 29.9MB 이하' 가 되게 잡았다.
PART_MAX = 29_900_000
PART_MIN = 25 * 1024 * 1024
#: 마지막 요약 파일을 넣을 자리.
RESERVE = 400_000
#: 파일 하나가 압축 뒤 이보다 크면 담지 않는다 — 그래야 zip 이 다음 장으로 넘어갈 때 앞 장이 25MB 아래로 끝나지 않는다.
MAX_COMPRESSED = 2_500_000
#: 이보다 큰 파일은 아예 읽지 않는다(NAS 에서 끌어오지 않는다).
MAX_RAW = 20_000_000
#: 담지 않는 확장자 — `.dat` 은 사용자 지시(한 장에 47MB 짜리 s_FrameData.dat), 이미지는 로그가 아니다.
SKIP_EXT = {".dat"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif"}
MAX_WAFERS_PER_LOT = 30
MAX_DEPTH = 5

#: 2차 수집(`--wide`, 10/10): Wafer 폴더 **맨 위**에서 이 핵심 파일만 읽고(장당 수십 KB) 나머지는 개수 · 크기만 센다 —
#: 1차 56 Lot 분석에서 쓸모가 확인된 것만: 시각 · Duration · 검토(ScanLog · Scanlog.Org) · 레시피별 Defect · 분류 Pareto(ProductionInfo) ·
#: 실제 LOT(ProductInfo) · 자동화 설정(Recipe.ini) · 레시피 수(RecipesInfo · MultiRecipe) · 레시피별 시작(ExtendedScanMetaData_*) ·
#: 카메라 보정(Params_SystemInfo) · 얼라인(Wafer2Table · WLUP) · 결함 이미지 수(ColorImageGrabingInfo).
WIDE_FILES = frozenset(n.lower() for n in (
    "WaferInfo.ini", "ScanLog.ini", "Scanlog.Org", "ProductionInfo.ini", "ProductInfo.ini", "Recipe.ini", "RecipesInfo.ini",
    "MultiRecipe.ini", "Params_SystemInfo.ini", "Wafer2Table.ini", "WLUP.txt", "ColorImageGrabingInfo.ini",
    "UniqueResultTypeIds.ini", "DiceLocationStat.txt", "EquipmentInfo.ini", "ScanOverlapLog.txt", "MoveResultFlag"))
WIDE_RE = re.compile(r"^ExtendedScanMetaData_.+\.json$", re.I)
#: 2차 수집의 **파라미터 표본**(10/10 사용자 요청 — 장비별 파라미터 상태 분석): Lot 마다 첫 · 마지막 Wafer 는 하위 폴더
#: (`Zones/` · `Recipe2-Zones/` · `TrainData/` · `FocusMapping/` …)까지 들어가 이 확장자의 텍스트 파일을 전부 읽는다(RTP.txt · GlobalRTP · OpticPreset ·
#: AlignRtp · WaferType · 분류표 …). 1차 56 Lot 실측: 같은 장비 · 같은 레시피는 Lot 사이 2~12 키만 다르고(측정값), 장비가 다르면 540~2,165 키가 다르다.
#: Lot 당 압축 중앙 46KB(최대 315KB). 바이너리(.dat · .flt · .zip · .grd · .dcm · 이미지)와 `WaferInfo.org`(바이너리)는 읽지 않는다.
PARAM_EXT = frozenset({".ini", ".txt", ".json", ".xml", ".csv", ".log", ".org", ""})
PARAM_SKIP_NAMES = frozenset({"waferinfo.org"})
#: **30일 전체 수집**(`--all`, 10/10 사용자 요청 — "최근 30일치 데이터 전부, 몇 시간 걸려도 됨"): 기간 안 Report 를 전부 열고 Lot 폴더 · Wafer 를 전부 본다.
#: 30대 × 30일 ≈ Report 12,700 · Wafer 156,000(9/18 30일치 샘플). 그래서 Wafer 마다 분석에 쓰는 결과 파일만 읽고(`ALL_FILES`),
#: Lot 마다 종류별로 **한 파일에 묶어** 담는다(`_묶음/<파일>.txt` — 낱개 2.3KB → 0.5KB/장, 2차 수집 데이터로 실측).
#: Lot 의 첫 Wafer 는 파라미터 표본(하위 폴더까지 텍스트 전부, Wafer 마다 다른 결과 파일은 `PARAM_SKIP_RE` 로 뺌)이고 같은 내용은 **모든 Lot 에 걸쳐 한 번만**(Lot 당 ~15KB).
#: 여러 Lot 을 동시에 읽는다(`LOT_INFLIGHT` — 파라미터 Wafer 한 장이 Lot 을 붙잡지 않게). Report 는 둘러볼 때 읽은 것을 압축해 두고 다시 읽지 않는다.
ALL_FILES = frozenset(n.lower() for n in (
    "WaferInfo.ini", "ScanLog.ini", "ProductionInfo.ini", "Wafer2Table.ini", "RecipesInfo.ini"))
ALL_PRESENCE = frozenset({"moveresultflag"})          # 있는지만 적는다(0바이트 — 열지 않는다)
PARAM_SKIP_RE = re.compile(
    r"^(Scanlog\.Org|ColorImageGrabingInfo\.ini|ScanResultImageList\.txt|DiceLocationStat\.txt|WLUP\.txt|frameToChuckPlane.*|"
    r".*CurrWaferSurfaceInterpolation.*|.*FocusMappingDebug.*|UniqueResultTypeIds\.ini|DieRegPos.*|ImageProcessing\.log|"
    r"ScanOverlapLog.*|.*\.md|FocusMapping/DieReferenceLocation\.json|FocusMapping/FocusPointsForScan\.xml|"
    r"TrainData/ScanAreaVectorInfo.*|DieAlignment\.dat_block\.ini|ExternalCoordSystems\.ini|AFBestIm.*)$", re.I)
LOT_INFLIGHT = 3
MAX_PARTS = 10                        #: zip 은 최대 10장(사용자 요청). 넘으면 거기서 멈추고 요약에 적는다.
PER_JOB_MIN = 15                      #: Job(원문)마다 최소 이만큼 Lot — 30일 안에 모자라면 그 Job 만 옛 Lot 으로 채운다(사용자 요청).
LOOK_BACK_DAYS = 90                   #: Job별 최소를 채우려고 되돌아보는 최대 기간. 30일 밖은 모자란 Job 에만 쓴다.
#: 암호화(사용자 요청 10/10) — 전송 중 노출·실수 공유를 막는 수준의 대칭 암호(SHA-256 키스트림 + HMAC, 표준 라이브러리). 강한 비밀이 아니다:
#: 키가 저장소에 있어 저장소를 가진 사람은 푼다. 더 세게 막으려면 환경변수 `AOI_LOG_KEY` 에 암호를 두면 그 값으로 바뀐다(그 값을 알아야 푼다).
#: 해독은 같은 도구 `--decode <파일>.enc`(또는 workers 가 부르는 쪽에서) — XOR 한 번이라 빠르다. zip 크기와 거의 같다(머리말 64바이트).
ENC_MAGIC = b"AOIXLOG1"
ENC_KEY = b"aoi-capacity/wafer-logs"


def _enc_secret(passphrase=None) -> bytes:
    if passphrase:
        return passphrase.encode("utf-8")
    return os.environ.get("AOI_LOG_KEY", "").encode("utf-8") or ENC_KEY


def _keystream(key: bytes, nonce: bytes, n: int) -> bytes:
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(key + nonce + ctr.to_bytes(8, "big")).digest()
        ctr += 1
    return bytes(out[:n])


def encrypt_bytes(data: bytes, secret: bytes) -> bytes:
    salt, nonce = os.urandom(16), os.urandom(8)
    key = hashlib.sha256(secret + salt).digest()
    ct = (int.from_bytes(data, "big") ^ int.from_bytes(_keystream(key, nonce, len(data)), "big")).to_bytes(len(data), "big") if data else b""
    mac = hmac.new(key, nonce + ct, hashlib.sha256).digest()
    return ENC_MAGIC + salt + nonce + mac + ct


def decrypt_bytes(blob: bytes, secret: bytes) -> bytes:
    if blob[:8] != ENC_MAGIC:
        raise ValueError("암호 파일 형식이 아닙니다(.enc 가 맞는지 확인하세요)")
    salt, nonce, mac, ct = blob[8:24], blob[24:32], blob[32:64], blob[64:]
    key = hashlib.sha256(secret + salt).digest()
    if not hmac.compare_digest(mac, hmac.new(key, nonce + ct, hashlib.sha256).digest()):
        raise ValueError("암호가 다르거나 파일이 손상됐습니다")
    return (int.from_bytes(ct, "big") ^ int.from_bytes(_keystream(key, nonce, len(ct)), "big")).to_bytes(len(ct), "big") if ct else b""
#: 모드마다 기본값 — (1차 깊게, 2차 넓게)
DEFAULTS = {"days": (14, 30), "survey": (15, 24), "min_lots": (10, 300), "max_lots": (150, 600)}

#: Lot 고르는 순서와 몫(첫 바퀴). 한 Lot 이 여러 갈래에 들어갈 수 있다.
QUOTAS = [("RDL 멀티", 3), ("RDL 기타", 1), ("PI", 2), ("PI Enhanced", 1), ("Kendall", 1),
          ("그 밖의 Job", 1), ("4층", 1), ("Error 포함", 1), ("RESCAN", 1)]
#: 첫 바퀴 뒤 더 담을 때 돌아가며 고르는 순서.
FILL_ORDER = ["RDL 멀티", "PI", "RDL 기타", "Kendall", "그 밖의 Job", "PI Enhanced", "4층", "Error 포함", "RESCAN"]

REPORT_RE = re.compile(
    r"^(.+?)_(\d{4})_(.+)_(\d{1,2})-([A-Za-z]{3})-(\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
ERROR_RE = re.compile(r"scan\s*error|failed\s+to\s+read\s+wafer\s+id|abort", re.I)
TAGS = re.compile(r"<[^>]+>")
IMG_B64 = re.compile(r'src="data:image/[^;]+;base64,[^"]*"')
REPORT_DIR_NAMES = ("Report", "Reports")
SCAN_PRIMARY = ("Scanresult", "ScanResult", "Scanresults")
_JOB_PREFIX_SPACE_RE = re.compile(r"^(2D@[A-Z0-9]+)\s+")
_JOB_REV_SUFFIX_RE = re.compile(r"[_-]0[A-Z]$")


def say(msg: str = "") -> None:
    print(msg, flush=True)


def stamp(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def norm_root(text: str) -> Path:
    t = str(text).strip().strip('"')
    return Path(t + os.sep if re.fullmatch(r"[A-Za-z]:", t) else t)


def safe(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(name)).strip("_")[:60] or "_"


def read_bytes(path) -> bytes:
    with open(path, "rb") as f:          # 읽기 전용
        return f.read()


# ── Report ─────────────────────────────────────────────────────────────────────
class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._t, self._r, self._c = [], None, None, None

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


def report_facts(text: str) -> dict:
    """Job/Setup · Lot · Wafer 행 · Batch 시각. 경로의 출처는 파일명이 아니라 Report 안의 Job/Setup 이다."""
    p = _Tables()
    p.feed(text)
    out = {"job": "", "setup": "", "wafers": [], "summary": {}}
    for tb in p.tables:
        if not tb:
            continue
        head = [h.lower() for h in tb[0]]
        iw = next((i for i, h in enumerate(head) if re.fullmatch(r"wafer\s*id", h)), -1)
        il = next((i for i, h in enumerate(head) if h == "lot"), -1)
        if iw >= 0 and il >= 0:
            for row in tb[1:]:
                if len(row) > max(iw, il):
                    out["wafers"].append((row[il], row[iw]))
        else:
            for row in tb:
                for i in range(0, len(row) - 1, 2):
                    k = re.sub(r"[:\s]+$", "", row[i])
                    if k and k not in out["summary"]:
                        out["summary"][k] = row[i + 1]
    js = out["summary"].get("Job/Setup", "")
    if "/" in js:
        job, _, setup = js.rpartition("/")
        out["job"], out["setup"] = job.strip(), setup.strip()
    return out


def is_placeholder(lot: str, wid: str) -> bool:
    return bool(re.match(r"^loadport", lot, re.I) or re.match(r"^slot\s*\d+", wid, re.I) or not lot or not wid)


def job_folder_variants(job: str):
    """앱의 collect.job_folder_variants 와 같다 — 원문, `2D@XX ` → `2D@XX-`, 끝 `_0A` 뗀 것, 둘 다."""
    out = []
    for v in (job, _JOB_PREFIX_SPACE_RE.sub(r"\1-", job), _JOB_REV_SUFFIX_RE.sub("", job),
              _JOB_REV_SUFFIX_RE.sub("", _JOB_PREFIX_SPACE_RE.sub(r"\1-", job))):
        if v and v not in out:
            out.append(v)
    return out


def name_day(name: str):
    """Report 이름의 날짜(배치 종료일) → epoch(그날 0시). 못 읽으면 None.
    이름의 날짜는 **YY-Mon-DD**(`…_26-Aug-31_(03.23.59)_BatchReport.htm` = 2026-08-31) — 10/10 까지 DD-Mon-YY 로 잘못 읽어
    2031년 같은 미래 날짜가 되어 '최근 며칠' 이 걸리지 않았다(2차 수집 Lot 이 2~10월에 퍼진 까닭)."""
    m = REPORT_RE.match(name)
    if not m:
        return None
    mon = MONTHS.get(m.group(5).lower())
    if not mon:
        return None
    try:
        return time.mktime((2000 + int(m.group(4)), mon, int(m.group(6)), 0, 0, 0, 0, 0, -1))
    except (OverflowError, ValueError):
        return None


def categories(job: str, lot: str, device: str, error: bool):
    j = job.lower()
    cats = []
    if "swelling" in j:
        cats.append("그 밖의 Job")
    elif re.search(r"rdl\s*\d", j):
        cats.append("RDL 멀티" if "multi" in j else "RDL 기타")
    elif re.search(r"(^|[_\s-])pi\s*\d", j):
        cats.append("PI Enhanced" if "enhanced" in j else "PI")
    elif j.startswith("kendall"):
        cats.append("Kendall")
    else:
        cats.append("그 밖의 Job")
    if device.upper().startswith("4F"):
        cats.append("4층")
    if error:
        cats.append("Error 포함")
    toks = {t.upper() for t in re.split(r"[\s_-]+", lot) if t}
    if toks & {"RE", "RESCAN"}:
        cats.append("RESCAN")
    if "TEST" in toks:
        cats.append("TEST")
    return cats


def find_subdir(root: Path, names) -> str:
    for n in names:
        if os.path.isdir(root / n):
            return n
    return ""


def scan_dirs(root: Path):
    """`Scanresult` 로 시작하는 폴더 전부(지금 쓰는 것 먼저, 백업 뒤) — 장비 폴더를 한 번만 나열한다."""
    try:
        names = sorted(e.name for e in os.scandir(root) if e.is_dir() and e.name.lower().startswith("scanresult"))
    except OSError:
        names = []
    primary = [n for n in names if n.lower() in {p.lower() for p in SCAN_PRIMARY}]
    return primary + [n for n in names if n not in primary]


def survey_device(root: Path, days: int, n_read, should_stop=None, spread: bool = False, keep_report: bool = False) -> dict:
    """한 대: Report 폴더를 한 번 나열하고 Report 를 n_read 개만 연다 — 기본은 최근 순, spread 면 기간 전체에 고르게(2차 수집). 읽기 전용."""
    dev = {"root": str(root), "name": root.name or str(root), "ok": False, "error": "", "reports": []}
    rep = find_subdir(root, REPORT_DIR_NAMES)
    if not rep:
        dev["error"] = "Report 폴더 없음(경로·드라이브 연결 확인)"
        return dev
    dev["report_dir"] = rep
    dev["scan_dirs"] = scan_dirs(root)
    since = time.time() - days * 86400
    files = []
    try:
        for e in os.scandir(root / rep):
            if not e.is_file() or not e.name.lower().endswith((".htm", ".html")):
                continue
            day = name_day(e.name)
            t = day if day is not None else e.stat().st_mtime
            if t >= since - 86400:
                files.append((t, e.name, e.path))
    except OSError as ex:
        dev["error"] = f"Report 폴더 나열 실패: {ex}"
        return dev
    files.sort(reverse=True)
    if spread and n_read and len(files) > n_read > 1:
        files = [files[i] for i in sorted({round(k * (len(files) - 1) / (n_read - 1)) for k in range(n_read)})]
    for t, name, path in files[:n_read]:
        if should_stop and should_stop():
            break
        try:
            text = read_bytes(path).decode("utf-8", errors="replace")
        except OSError:
            continue
        if keep_report:
            text = IMG_B64.sub('src=""', text)              # 로고 base64 를 먼저 떼면 해석도 빠르다
        f = report_facts(text)
        m = REPORT_RE.match(name)
        job, setup = f["job"], f["setup"]
        if not job and m:                                       # 옛 형식 — 파일명 규칙
            job, setup = m.group(1), m.group(2)
        real = [(l, w) for l, w in f["wafers"] if not is_placeholder(l, w)]
        lots = []
        for l, _w in real:
            if l not in lots:
                lots.append(l)
        if not job or not lots:
            continue
        err = bool(ERROR_RE.search(TAGS.sub(" ", text)))
        dev["reports"].append({
            "device": dev["name"], "root": str(root), "report": name, "report_path": path, "t": t,
            "job": job, "setup": setup, "lot": lots[0], "wafers": [w for l, w in real if l == lots[0]],
            "batch_start": f["summary"].get("Batch Start", ""), "batch_end": f["summary"].get("Batch End", ""),
            "error": err, "cats": categories(job, lots[0], dev["name"], err),
            **({"rep_z": zlib.compress(text.encode("utf-8"), 6)} if keep_report else {})})
    dev["ok"] = True
    dev["n_listed"] = len(files)
    return dev


# ── zip 나누기 ──────────────────────────────────────────────────────────────────
class _Full(Exception):
    """zip 장수 상한(MAX_PARTS)에 도달 — 더 담지 않고 멈춘다."""


class Packer:
    """zip 을 차례로 채운다. 항목을 넣기 전에 압축 크기를 미리 재서 PART_MAX 를 넘기 전에 다음 장으로 넘긴다."""

    def __init__(self, out_dir: Path, base: str, part_max: int = PART_MAX, reserve: int = RESERVE, max_parts: int = 0):
        self.out_dir, self.base, self.part_max, self.reserve = out_dir, base, part_max, reserve
        self.max_parts = max_parts
        self.parts, self.z, self.cd = [], None, 0

    def _open(self):
        if self.max_parts and len(self.parts) >= self.max_parts:
            raise _Full()
        path = self.out_dir / f"{self.base}_part{len(self.parts) + 1:02d}.zip"
        self.z = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, allowZip64=False)
        self.cd = 0
        self.parts.append(path)

    def size(self) -> int:
        return (self.z.fp.tell() + self.cd + 22) if self.z else 0

    def total(self) -> int:
        """지금까지 만든 zip 전체 크기(닫힌 장 + 지금 장)."""
        return sum(p.stat().st_size for p in self.parts[:-1 if self.z else None]) + self.size()

    @staticmethod
    def compressed_len(data: bytes) -> int:
        c = zlib.compressobj(6, zlib.DEFLATED, -15)            # zipfile 과 같은 설정이라 실제 크기와 같다
        return len(c.compress(data)) + len(c.flush())

    def add(self, name: str, data: bytes, mtime: float = 0.0, final: bool = False) -> str:
        nb = len(name.encode("utf-8"))
        need = 30 + nb + self.compressed_len(data) + 46 + nb + 64
        room = self.part_max - (0 if final else self.reserve)
        if self.z is not None and self.size() + need > room:
            self.close()
        if self.z is None:
            self._open()
        tm = time.localtime(mtime or time.time())
        zi = zipfile.ZipInfo(name, date_time=tm[:6] if tm.tm_year >= 1980 else (1980, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        self.z.writestr(zi, data, compresslevel=6)
        self.cd += 46 + nb
        return self.parts[-1].name

    def close(self):
        if self.z is not None:
            self.z.close()
            self.z = None


# ── Lot 담기 ────────────────────────────────────────────────────────────────────
def lot_dir_of(c: dict, scan_names) -> tuple:
    """정확 경로 후보(Scanresult 폴더 × Job 이름 후보)의 존재만 차례로 본다. 찾으면 (경로, Scanresult, Job 폴더)."""
    root = Path(c["root"])
    for sd in scan_names:
        for jv in job_folder_variants(c["job"]):
            p = root / sd / jv / c["setup"] / c["lot"] if c["setup"] else root / sd / jv / c["lot"]
            if os.path.isdir(p):
                return p, sd, jv
    return None, "", ""


def walk_wafer(wdir: Path, should_stop=None):
    """Wafer 폴더 **안**만 본다(이 폴더 밖으로 나가지 않는다). [(상대경로, 크기, 수정시각, 내용 또는 None, 건너뛴 이유)]"""
    out, stack = [], [(wdir, "", 0)]
    while stack:
        if should_stop and should_stop():
            return out                                  # 멈춤 — 부르는 쪽이 이 Lot 을 버린다
        d, rel, depth = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name.lower())
        except OSError as ex:
            out.append((rel or ".", 0, 0.0, None, f"나열 실패: {ex}"))
            continue
        for e in entries:
            r = f"{rel}/{e.name}" if rel else e.name
            if e.is_symlink():
                continue
            if e.is_dir():
                if depth < MAX_DEPTH:
                    stack.append((Path(e.path), r, depth + 1))
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            ext = os.path.splitext(e.name)[1].lower()
            why = ""
            if ext in SKIP_EXT:
                why = ".dat 제외"
            elif ext in IMAGE_EXT:
                why = "이미지 제외"
            elif st.st_size > MAX_RAW:
                why = "너무 큼"
            data = None
            if should_stop and should_stop():
                return out
            if not why:
                try:
                    data = read_bytes(e.path)
                except OSError as ex:
                    why = f"읽기 실패: {ex}"
            out.append((r, st.st_size, st.st_mtime, data, why))
    out.sort(key=lambda x: x[0].lower())
    return out


def walk_wafer_top(wdir: Path, should_stop=None):
    """2차 수집: Wafer 폴더 **맨 위 한 번만** 나열하고 WIDE_FILES 만 읽는다(하위 폴더는 들어가지 않는다).
    돌려줌: (walk_wafer 와 같은 줄 목록, 안 읽은 것 {"files", "bytes", "image", "dat", "other", "dirs"})."""
    out, rest = [], {"files": 0, "bytes": 0, "image": 0, "dat": 0, "other": 0, "dirs": 0}
    try:
        entries = sorted(os.scandir(wdir), key=lambda e: e.name.lower())
    except OSError as ex:
        return [(".", 0, 0.0, None, f"나열 실패: {ex}")], rest
    for e in entries:
        if should_stop and should_stop():
            return out, rest
        if e.is_symlink():
            continue
        if e.is_dir():
            rest["dirs"] += 1
            continue
        try:
            st = e.stat()
        except OSError:
            continue
        if e.name.lower() not in WIDE_FILES and not WIDE_RE.match(e.name):
            ext = os.path.splitext(e.name)[1].lower()
            rest["files"] += 1
            rest["bytes"] += st.st_size
            rest["image" if ext in IMAGE_EXT else "dat" if ext in SKIP_EXT else "other"] += 1
            continue
        data, why = None, ""
        if st.st_size > MAX_RAW:
            why = "너무 큼"
        else:
            try:
                data = read_bytes(e.path)
            except OSError as ex:
                why = f"읽기 실패: {ex}"
        out.append((e.name, st.st_size, st.st_mtime, data, why))
    return out, rest


def walk_wafer_params(wdir: Path, should_stop=None):
    """2차 수집의 파라미터 표본 Wafer: 이 Wafer 폴더 **안에서만** 하위 폴더까지 내려가 PARAM_EXT 텍스트 파일을 전부 읽는다.
    돌려줌은 walk_wafer_top 과 같은 (줄 목록, 안 읽은 것) — 하위 폴더는 들어가므로 dirs 는 세지 않는다."""
    out, rest = [], {"files": 0, "bytes": 0, "image": 0, "dat": 0, "other": 0, "dirs": 0}
    stack = [(wdir, "", 0)]
    while stack:
        if should_stop and should_stop():
            return out, rest
        d, rel, depth = stack.pop()
        try:
            entries = sorted(os.scandir(d), key=lambda e: e.name.lower())
        except OSError as ex:
            out.append((rel or ".", 0, 0.0, None, f"나열 실패: {ex}"))
            continue
        for e in entries:
            if should_stop and should_stop():
                return out, rest
            r = f"{rel}/{e.name}" if rel else e.name
            if e.is_symlink():
                continue
            if e.is_dir():
                if depth < MAX_DEPTH:
                    stack.append((Path(e.path), r, depth + 1))
                else:
                    rest["dirs"] += 1
                continue
            try:
                st = e.stat()
            except OSError:
                continue
            ext = os.path.splitext(e.name)[1].lower()
            if ext not in PARAM_EXT or e.name.lower() in PARAM_SKIP_NAMES:
                rest["files"] += 1
                rest["bytes"] += st.st_size
                rest["image" if ext in IMAGE_EXT else "dat" if ext in SKIP_EXT else "other"] += 1
                continue
            data, why = None, ""
            if st.st_size > MAX_RAW:
                why = "너무 큼"
            else:
                try:
                    data = read_bytes(e.path)
                except OSError as ex:
                    why = f"읽기 실패: {ex}"
            out.append((r, st.st_size, st.st_mtime, data, why))
    out.sort(key=lambda x: x[0].lower())
    return out, rest


def spread_order(n: int):
    """0 · 끝 · 가운데 · 사분점 … 순서 — 앞에서 몇 개만 써도 기간 전체를 고르게 덮는다."""
    if n <= 0:
        return []
    out, segs = [0] + ([n - 1] if n > 1 else []), [(0, n - 1)]
    while segs:
        nxt = []
        for a, b in segs:
            if b - a > 1:
                m = (a + b) // 2
                out.append(m)
                nxt += [(a, m), (m, b)]
        segs = nxt
    return out


def recipe_mode(files) -> str:
    """첫 Wafer 의 RecipesInfo.ini 레시피 수로 멀티/단일을 본다(없고 WaferInfo 만 있으면 단일)."""
    by = {r: d for r, _s, _m, d, _w in files if d is not None}
    ri = by.get("RecipesInfo.ini")
    if ri is not None:
        n = len(re.findall(rb"^\s*\[Recipe-\d+\]", ri, re.M))
        return "멀티" if n >= 2 else "단일"
    return "단일" if "WaferInfo.ini" in by else "모름"


def collect_lot(idx: int, c: dict, scan_names, pool, packer: Packer, should_stop=None, wide: bool = False) -> dict:
    lot_id = f"{idx:02d}_{safe(c['device'])}_{safe(c['lot'])}"
    info = {k: c[k] for k in ("device", "report", "job", "setup", "lot", "batch_start", "batch_end", "error", "cats")}
    info.update({"lot_id": lot_id, "wafers_in_report": len(c["wafers"]), "why": c.get("why", "")})
    lot_dir, sd, jv = lot_dir_of(c, scan_names)
    if lot_dir is None:
        info["skip"] = "Lot 폴더 없음"
        return info
    info.update({"scan_dir": sd, "job_folder": jv, "lot_dir": str(lot_dir)})
    try:
        wafers = sorted((e for e in os.scandir(lot_dir) if e.is_dir()), key=lambda e: e.name)[:MAX_WAFERS_PER_LOT]
    except OSError as ex:
        info["skip"] = f"Lot 폴더 나열 실패: {ex}"
        return info
    if not wafers:
        info["skip"] = "Wafer 폴더 없음"
        return info
    if wide:
        sample = {0, len(wafers) - 1}                   # 파라미터 표본: 첫 · 마지막 Wafer 는 하위 폴더까지
        info["param_wafers"] = [wafers[i].name for i in sorted(sample)]
        got = list(pool.map(lambda ie: (walk_wafer_params if ie[0] in sample else walk_wafer_top)(Path(ie[1].path), should_stop),
                            enumerate(wafers)))
        results, rests = [g[0] for g in got], [g[1] for g in got]
    else:
        results = list(pool.map(lambda e: walk_wafer(Path(e.path), should_stop), wafers))
        rests = [None] * len(wafers)
    if should_stop and should_stop():
        info["skip"] = "멈춤 요청(이 Lot 은 담지 않음)"
        return info

    try:
        rep = IMG_B64.sub('src=""', read_bytes(c["report_path"]).decode("utf-8", errors="replace")).encode("utf-8")
        packer.add(f"{lot_id}/report/{c['report']}", rep, c["t"])
    except OSError:
        pass
    first = {}                                     # sha1 → 처음 담은 zip 안 이름 (이 Lot 안에서만)
    rows = ["wafer\t상대경로\t크기\t수정시각\tsha1\t저장"]
    n_files = n_stored = n_same = n_skip = 0
    raw = 0
    for w, files, rest in zip(wafers, results, rests):
        if rest and (rest["files"] or rest["dirs"]):   # 2차 수집: 읽지 않은 것은 Wafer 마다 한 줄로
            n_files += rest["files"]
            n_skip += rest["files"]
            rows.append(f"{w.name}\t(안 읽음)\t{rest['bytes']}\t\t\t건너뜀: 파일 {rest['files']} — 이미지 {rest['image']} · "
                        f".dat {rest['dat']} · 그 밖 {rest['other']} · 하위 폴더 {rest['dirs']}")
        for rel, size, mtime, data, why in files:
            n_files += 1
            if data is None:
                n_skip += 1
                rows.append(f"{w.name}\t{rel}\t{size}\t{stamp(mtime) if mtime else ''}\t\t건너뜀: {why}")
                continue
            h = hashlib.sha1(data).hexdigest()
            if h in first:
                n_same += 1
                rows.append(f"{w.name}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t= {first[h]}")
                continue
            if Packer.compressed_len(data) > MAX_COMPRESSED:
                n_skip += 1
                rows.append(f"{w.name}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t건너뜀: 압축해도 너무 큼")
                continue
            name = f"{lot_id}/{w.name}/{rel}"
            part = packer.add(name, data, mtime)
            first[h] = name
            n_stored += 1
            raw += len(data)
            rows.append(f"{w.name}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t{part}")
    packer.add(f"{lot_id}/_목록.tsv", "\n".join(rows).encode("utf-8"))
    info.update({"wafer_dirs": len(wafers), "files": n_files, "stored": n_stored, "same": n_same,
                 "skipped": n_skip, "stored_bytes": raw, "mode": recipe_mode(results[0])})
    return info


def walk_wafer_all(wdir: Path, should_stop=None):
    """30일 전체: Wafer 폴더 맨 위를 한 번 나열해 ALL_FILES · ExtendedScanMetaData_* 만 읽고 MoveResultFlag 는 있는지만. (줄 목록, 안 읽은 것)"""
    out, rest = [], {"files": 0, "bytes": 0, "image": 0, "dat": 0, "other": 0, "dirs": 0}
    try:
        entries = sorted(os.scandir(wdir), key=lambda e: e.name.lower())
    except OSError as ex:
        return [(".", 0, 0.0, None, f"나열 실패: {ex}")], rest
    for e in entries:
        if should_stop and should_stop():
            return out, rest
        if e.is_symlink():
            continue
        if e.is_dir():
            rest["dirs"] += 1
            continue
        try:
            st = e.stat()
        except OSError:
            continue
        low = e.name.lower()
        if low in ALL_PRESENCE:
            out.append((e.name, st.st_size, st.st_mtime, b"", ""))
            continue
        if low not in ALL_FILES and not WIDE_RE.match(e.name):
            ext = os.path.splitext(e.name)[1].lower()
            rest["files"] += 1
            rest["bytes"] += st.st_size
            rest["image" if ext in IMAGE_EXT else "dat" if ext in SKIP_EXT else "other"] += 1
            continue
        data, why = None, ""
        if st.st_size > MAX_RAW:
            why = "너무 큼"
        else:
            try:
                data = read_bytes(e.path)
            except OSError as ex:
                why = f"읽기 실패: {ex}"
        out.append((e.name, st.st_size, st.st_mtime, data, why))
    return out, rest


def is_bundle(rel: str) -> bool:
    """30일 전체에서 Lot 묶음 파일로 들어가는 맨 위 결과 파일인가."""
    return "/" not in rel and (rel.lower() in ALL_FILES or bool(WIDE_RE.match(rel)))


def read_lot_all(c: dict, scan_names, wpool, should_stop=None) -> dict:
    """30일 전체 — 한 Lot 을 읽기만 한다(스레드에서). 담기는 메인 스레드의 pack_lot_all 이 한다."""
    lot_dir, sd, jv = lot_dir_of(c, scan_names)
    if lot_dir is None:
        return {"skip": "Lot 폴더 없음"}
    try:
        wafers = sorted((e for e in os.scandir(lot_dir) if e.is_dir()), key=lambda e: e.name)[:200]
    except OSError as ex:
        return {"skip": f"Lot 폴더 나열 실패: {ex}"}
    if not wafers:
        return {"skip": "Wafer 폴더 없음"}
    psample = {0, len(wafers) - 1}                                # 첫 · 마지막 Wafer 는 파라미터까지(꼼꼼히 — Lot 중간 변경도 잡게)
    got = list(wpool.map(lambda ie: (walk_wafer_params if ie[0] in psample else walk_wafer_all)(Path(ie[1].path), should_stop),
                         enumerate(wafers)))
    if should_stop and should_stop():
        return {"skip": "멈춤 요청(이 Lot 은 담지 않음)"}
    return {"scan_dir": sd, "job_folder": jv, "lot_dir": str(lot_dir), "wafers": [w.name for w in wafers], "got": got}


def pack_lot_all(idx: int, c: dict, data: dict, packer: Packer, gseen: dict) -> dict:
    """30일 전체 — 읽은 Lot 을 zip 에 담는다(메인 스레드). 결과 파일은 종류별 묶음, 첫 Wafer 의 파라미터는 모든 Lot 에 걸쳐 같은 내용 한 번."""
    lot_id = f"{idx:04d}_{safe(c['device'])}_{safe(c['lot'])}"
    info = {k: c[k] for k in ("device", "report", "job", "setup", "lot", "batch_start", "batch_end", "error", "cats")}
    info.update({"lot_id": lot_id, "wafers_in_report": len(c["wafers"]), "why": "30일 전체",
                 "reports": [r[0] for r in c.get("reports", [])]})
    if data.get("skip"):
        info["skip"] = data["skip"]
        return info
    info.update({k: data[k] for k in ("scan_dir", "job_folder", "lot_dir")})
    wafers, got = data["wafers"], data["got"]
    info["param_wafers"] = sorted({wafers[0], wafers[-1]})
    for name, t, rz in c.get("reports", []):
        if rz:
            packer.add(f"{lot_id}/report/{name}", zlib.decompress(rz), t)
    bundles = {}
    rows = ["wafer\t상대경로\t크기\t수정시각\tsha1\t저장"]
    n_files = n_stored = n_same = n_skip = raw = 0
    for w, (files, rest) in zip(wafers, got):
        kinds = []
        for rel, size, mtime, d, why in files:
            n_files += 1
            if rel.lower() in ALL_PRESENCE and "/" not in rel:
                kinds.append(rel)
                continue
            if d is None:
                n_skip += 1
                rows.append(f"{w}\t{rel}\t{size}\t{stamp(mtime) if mtime else ''}\t\t건너뜀: {why}")
                continue
            if is_bundle(rel):
                bundles.setdefault(rel, []).append(f"### {w}\t{size}\t{stamp(mtime)}\n".encode("utf-8") + d + b"\n")
                kinds.append(rel)
                n_stored += 1
                raw += len(d)
                continue
            if PARAM_SKIP_RE.match(rel):                 # 파라미터 표본에서 Wafer 마다 다른 결과 파일은 뺀다
                n_skip += 1
                continue
            h = hashlib.sha1(d).hexdigest()
            if h in gseen:
                n_same += 1
                rows.append(f"{w}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t= {gseen[h]}")
                continue
            if Packer.compressed_len(d) > MAX_COMPRESSED:
                n_skip += 1
                rows.append(f"{w}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t건너뜀: 압축해도 너무 큼")
                continue
            name = f"{lot_id}/{w}/{rel}"
            part = packer.add(name, d, mtime)
            gseen[h] = name
            n_stored += 1
            raw += len(d)
            rows.append(f"{w}\t{rel}\t{size}\t{stamp(mtime)}\t{h[:12]}\t{part}")
        n_files += rest["files"]
        n_skip += rest["files"]
        rows.append(f"{w}\t(묶음)\t{rest['bytes']}\t\t\t{' · '.join(kinds) or '없음'} | 안 읽음: 파일 {rest['files']} — 이미지 {rest['image']} · "
                    f".dat {rest['dat']} · 그 밖 {rest['other']} · 하위 폴더 {rest['dirs']}")
    for typ, chunks in bundles.items():
        packer.add(f"{lot_id}/_묶음/{typ}.txt", b"".join(chunks))
    packer.add(f"{lot_id}/_목록.tsv", "\n".join(rows).encode("utf-8"))
    info.update({"wafer_dirs": len(wafers), "files": n_files, "stored": n_stored, "same": n_same,
                 "skipped": n_skip, "stored_bytes": raw, "mode": recipe_mode(got[0][0])})
    return info


class _Done(Exception):
    """2차 수집이 끝났을 때 1차 고르기 단계를 건너뛰는 신호."""


# ── 고르기 ──────────────────────────────────────────────────────────────────────
def pick(cands, cat: str, chosen_keys: set, dev_count: dict, tried: set):
    """그 갈래에서 아직 안 고른 Report 하나 — 덜 쓴 장비, 꽉 찬 Lot(20장 이상), 최근 순."""
    pool = [c for c in cands if cat in c["cats"] and c["key"] not in chosen_keys and c["key"] not in tried]
    if not pool:
        return None
    pool.sort(key=lambda c: (dev_count.get(c["device"], 0), len(c["wafers"]) < 20 and cat != "Error 포함", -c["t"]))
    return pool[0]


def run(args, log=None, should_stop=None, result=None) -> int:
    """수집 본체 — 명령줄(`main`)과 수집 창 버튼(`aoi_capacity/workers/wafer_logs.py`)이 같이 쓴다.
    log: 한 줄씩 받는 함수(기본 print) · should_stop: 참이면 담던 Lot 까지만 하고 마무리 · result: 끝에 zip 목록 등을 채울 dict."""
    log = log or say
    should_stop = should_stop or (lambda: False)
    t0 = time.time()
    all_mode = bool(getattr(args, "all", False))
    wide = bool(getattr(args, "wide", False)) or all_mode
    if all_mode:                                        # 30일 전체: 기간 안 Report 전부 · Lot 전부 · Job별 최소 · zip 10장 상한
        for k, v in (("days", 30), ("max_lots", 10 ** 9), ("min_lots", 10 ** 9), ("max_minutes", 24 * 60),
                     ("per_job_min", PER_JOB_MIN), ("look_back", LOOK_BACK_DAYS)):
            if getattr(args, k, None) is None:
                setattr(args, k, v)
    else:
        for k, pair in DEFAULTS.items():
            if getattr(args, k, None) is None:
                setattr(args, k, pair[1 if wide else 0])
        if getattr(args, "max_minutes", None) is None:
            args.max_minutes = 120
    out_dir = Path(args.out or OUT_DIR)
    roots = [norm_root(r) for r in (args.roots or DEVICE_ROOTS)]
    drives = {os.path.splitdrive(str(r))[0].upper() for r in roots} - {""}
    out_abs = os.path.normcase(os.path.abspath(out_dir))
    if os.path.splitdrive(str(out_dir))[0].upper() in drives or any(
            out_abs.startswith(os.path.normcase(os.path.abspath(r))) for r in roots):
        log(f"[오류] 저장 위치가 NAS 쪽입니다: {out_dir}. 로컬 폴더를 --out 으로 지정하세요.")
        return 2

    if all_mode:
        log(f"30일 전체 수집 — 최근 {args.days}일 Report 를 전부 열고 Lot · Wafer 를 전부 봅니다(Wafer 마다 결과 파일만 · Lot 마다 첫 Wafer 는 파라미터까지). "
            "몇 시간 걸릴 수 있고, 멈추면 지금까지 담은 것으로 zip 을 마무리합니다")
    elif wide:
        log("2차 수집(넓게) — Wafer 폴더 맨 위의 핵심 파일만 읽고(Lot 마다 첫 · 마지막 Wafer 는 Zones 등 하위 폴더의 파라미터까지), "
            "장비마다 기간 전체에 고르게 Lot 을 고릅니다")
    log(f"1/3 둘러보기 — 장비 {len(roots)}대, 최근 {args.days}일 Report 를 "
        + ("전부 엽니다" if all_mode else f"장비마다 {args.survey}개까지 엽니다" + (" (기간 전체에 고르게)" if wide else "")))
    survey_days = args.look_back if all_mode else args.days
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        devs = list(pool.map(lambda r: survey_device(r, survey_days, args.survey, should_stop, spread=wide and not all_mode,
                                                     keep_report=all_mode), roots))
    if should_stop():
        log("멈춤 요청 — 둘러보기까지만 하고 끝냅니다(파일은 만들지 않았습니다)")
        return 1
    cands, scan_of = [], {}
    for d in devs:
        state = f"Report {len(d['reports'])}개 읽음" if d["ok"] else f"건너뜀 — {d['error']}"
        log(f"   {d['name']:<12} {state}")
        if d["ok"]:
            scan_of[d["name"]] = d["scan_dirs"]
            cands.extend(d["reports"])
    for c in cands:
        c["key"] = (c["device"], c["job"], c["setup"], c["lot"])
    if all_mode:                                        # 같은 Lot 폴더를 가리키는 Report 는 한 Lot 으로 — Report 는 전부 담는다
        groups = {}
        for c in sorted(cands, key=lambda c: c["t"]):
            groups.setdefault(c["key"], []).append(c)
        merged = []
        for cs in groups.values():
            c = dict(cs[-1])
            c["reports"] = [(x["report"], x["t"], x.get("rep_z")) for x in cs]
            c["t"] = max(x["t"] for x in cs)
            merged.append(c)
        win = time.time() - args.days * 86400
        chosen = [c for c in merged if c["t"] >= win]       # 최근 30일 Lot 은 전부
        have = {c["key"] for c in chosen}
        byjob = {}
        for c in merged:
            byjob.setdefault(c["job"], []).append(c)
        topup = 0
        for job, cs in byjob.items():                       # Job별 최소 — 모자라면 그 Job 의 옛 Lot(30일 밖)으로 채운다
            n = sum(1 for c in cs if c["key"] in have)
            if n >= args.per_job_min:
                continue
            for c in sorted((c for c in cs if c["key"] not in have), key=lambda c: -c["t"])[:args.per_job_min - n]:
                chosen.append(c); have.add(c["key"]); topup += 1
        cands = chosen
        jobs = len(byjob)
        log(f"   Report {sum(len(d['reports']) for d in devs if d['ok']):,}개 · Lot 폴더 {len(merged):,}개 · Job {jobs}종 · "
            f"담을 Lot {len(cands):,}개(최근 {args.days}일 전부 + Job별 {args.per_job_min}개 채우기 {topup}개)")
    else:
        seen = set()
        cands = [c for c in cands if not (c["key"] in seen or seen.add(c["key"]))]   # 같은 Lot 폴더는 한 번
    if not cands:
        log("[오류] 읽은 Report 가 없습니다. 드라이브 연결과 DEVICE_ROOTS 를 확인하세요.")
        return 2
    counts = {}
    for c in cands:
        for k in c["cats"]:
            counts[k] = counts.get(k, 0) + 1
    log("   후보 Lot: " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))

    if args.plan and all_mode:
        per = {}
        for c in cands:
            per.setdefault(c["device"], []).append(c)
        log("\n장비별 Lot 폴더(30일 전체 — 전부 담는다):")
        for d, cs in per.items():
            log(f"   {d:<12} {len(cs):>5}개 · Wafer(Report 표) {sum(len(c['wafers']) for c in cs):>6}장")
        return 0
    if args.plan and wide:
        per = {}
        for c in cands:
            per.setdefault(c["device"], []).append(c)
        log("\n장비별 후보 Lot(2차 수집은 장비를 돌아가며 하나씩, 각 장비 안에서는 기간 전체에 고르게):")
        for d, cs in per.items():
            log(f"   {d:<12} {len(cs):>3}개 · {stamp(min(c['t'] for c in cs))[:10]} ~ {stamp(max(c['t'] for c in cs))[:10]}")
        return 0
    if args.plan:
        chosen, dev_count, keys = [], {}, set()
        for cat, n in QUOTAS:
            for _ in range(n):
                c = pick(cands, cat, keys, dev_count, set())
                if c:
                    keys.add(c["key"])
                    dev_count[c["device"]] = dev_count.get(c["device"], 0) + 1
                    chosen.append((cat, c))
        log("\n고를 Lot(첫 바퀴):")
        for cat, c in chosen:
            log(f"   [{cat}] {c['device']} · {c['job']} / {c['lot']} · {len(c['wafers'])}장 · {c['report']}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    base = ("AOI_wafer_logs30_" if all_mode else "AOI_wafer_logs2_" if wide else "AOI_wafer_logs_") + time.strftime("%Y%m%d_%H%M")
    packer = Packer(out_dir, base, args.part_max, min(RESERVE, args.part_max // 10), max_parts=MAX_PARTS if all_mode else 0)
    lots, dev_count, keys, tried = [], {}, set(), set()
    deadline = t0 + args.max_minutes * 60
    stop_why = ""

    def done_ok() -> int:
        return sum(1 for x in lots if not x.get("skip"))

    def collect_one(c: dict, label: str, pool) -> bool:
        tried.add(c["key"])
        c["why"] = label
        log(f"   [{len(lots) + 1:>2}] {label:<10} {c['device']} · {c['job']} / {c['lot']} ({len(c['wafers'])}장)")
        info = collect_lot(len(lots) + 1, c, scan_of.get(c["device"], []), pool, packer, should_stop, wide=wide)
        lots.append(info)
        if info.get("skip"):
            log(f"        건너뜀 — {info['skip']}")
            return False
        keys.add(c["key"])
        dev_count[c["device"]] = dev_count.get(c["device"], 0) + 1
        log(f"        Wafer {info['wafer_dirs']} · 파일 {info['files']} → 담음 {info['stored']} · 같은 내용 {info['same']}"
            f" · 건너뜀 {info['skipped']} · {info['mode']}")
        log(f"        zip {len(packer.parts)}장 · 합계 {packer.total() / 1e6:.1f}MB · 지금 장 {packer.size() / 1e6:.1f}MB"
            f" · {(time.time() - t0) / 60:.0f}분 지남")
        return True

    def take(cat: str, pool) -> bool:
        for _ in range(6):                                  # 폴더가 없으면 같은 갈래의 다음 후보
            if should_stop():
                return False
            c = pick(cands, cat, keys, dev_count, tried)
            if c is None:
                return False
            if collect_one(c, cat, pool):
                return True
        return False

    def limit_reached() -> str:
        if should_stop():
            return "멈춤 요청"
        if time.time() > deadline:
            return f"시간 상한({args.max_minutes:g}분)"
        if len(lots) >= args.max_lots:
            return f"Lot 수 상한({args.max_lots})"
        return ""

    def run_wide(pool) -> str:
        """장비를 돌아가며 하나씩 — 각 장비 안에서는 기간 양 끝 · 가운데 · 사분점 … 순서(spread_order)."""
        per = {}
        for c in sorted(cands, key=lambda c: -c["t"]):
            per.setdefault(c["device"], []).append(c)
        queues = {d: [cs[i] for i in spread_order(len(cs))] for d, cs in per.items()}
        while True:
            moved = False
            for d in list(queues):
                if done_ok() >= args.min_lots and packer.size() >= args.part_min:
                    return ""
                why = limit_reached()
                if why:
                    return why
                if queues[d]:
                    collect_one(queues[d].pop(0), "넓게", pool)
                    moved = True
            if not moved:
                return "더 고를 후보 없음(--days · --survey 를 늘려 보세요)"

    def run_all(wpool, lpool) -> str:
        """30일 전체: 장비를 돌아가며 · 장비 안에서는 기간 고르게(spread_order) 순서로, Lot 을 LOT_INFLIGHT 개씩 동시에 읽고 순서대로 담는다."""
        per = {}
        for c in sorted(cands, key=lambda c: -c["t"]):
            per.setdefault(c["device"], []).append(c)
        queues = [[cs[i] for i in spread_order(len(cs))] for cs in per.values()]
        order = [q[i] for i in range(max(map(len, queues), default=0)) for q in queues if i < len(q)]
        total, gseen, it, inflight = len(order), {}, iter(order), deque()
        t_start = time.time()

        def submit() -> None:
            c = next(it, None)
            if c is not None:
                inflight.append((c, lpool.submit(read_lot_all, c, scan_of.get(c["device"], []), wpool, should_stop)))
        for _ in range(LOT_INFLIGHT):
            submit()
        while inflight:
            c, fut = inflight.popleft()
            data = fut.result()
            why = limit_reached()
            if why:
                for c2, f2 in inflight:
                    f2.cancel()
                return why
            try:
                info = pack_lot_all(len(lots) + 1, c, data, packer, gseen)
            except _Full:
                for c2, f2 in inflight:
                    f2.cancel()
                return f"zip {MAX_PARTS}장 상한 — 더 담지 못해 여기서 멈춥니다(데이터가 예상보다 큽니다)"
            lots.append(info)
            n = len(lots)
            el = time.time() - t_start
            eta = el / n * (total - n) / 60
            if info.get("skip"):
                log(f"   [{n:,}/{total:,}] {c['device']} · {c['job']} / {c['lot']} — 건너뜀: {info['skip']}")
            else:
                log(f"   [{n:,}/{total:,}] {c['device']} · {c['job']} / {c['lot']} · Wafer {info['wafer_dirs']} · "
                    f"zip {len(packer.parts)}장 {packer.total() / 1e6:.0f}MB · {el / 60:.0f}분 지남 · 남은 예상 {eta:.0f}분")
            submit()
        return ""

    log(f"\n2/3 Lot 담기 — 저장 위치 {out_dir}")
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            if all_mode:
                with ThreadPoolExecutor(max_workers=LOT_INFLIGHT) as lpool:
                    stop_why = run_all(pool, lpool)
                raise _Done
            if wide:
                stop_why = run_wide(pool)
                raise _Done
            for cat, n in QUOTAS:
                for _ in range(n):
                    if time.time() > deadline or should_stop():
                        break
                    take(cat, pool)
            i = 0
            while True:
                rdl_single = any(x.get("mode") == "단일" and x.get("cats", [""])[0].startswith("RDL") for x in lots)
                if done_ok() >= args.min_lots and packer.size() >= args.part_min and (rdl_single or i >= 12):
                    break                                   # RDL 단일을 12번 더 찾아도 없으면 그만(요약에 방식이 보인다)
                stop_why = limit_reached()
                if stop_why:
                    break
                order = (["RDL 멀티", "RDL 기타"] if not rdl_single and i < 12 else []) + FILL_ORDER
                if not any(take(cat, pool) for cat in order[i % len(order):] + order[:i % len(order)]):
                    stop_why = "더 고를 후보 없음(--days · --survey 를 늘려 보세요)"
                    break
                i += 1
    except _Done:
        pass
    except KeyboardInterrupt:
        stop_why = "중간에 멈춤(Ctrl+C)"
        log("\n멈춤 — 지금까지 담은 것으로 마무리합니다")

    # ── 요약 ──
    log("\n3/3 요약 쓰는 중…")
    ok = [x for x in lots if not x.get("skip")]
    lines = [f"AOI Wafer 폴더 로그{' 30일 전체' if all_mode else ' 2차(넓게 · 핵심 파일만)' if wide else ''} · {stamp(time.time())} · 걸린 시간 {(time.time() - t0) / 60:.1f}분",
             f"담은 Lot {len(ok)}개 (시도 {len(lots)}) · 파일 {sum(x['files'] for x in ok)}개 중 "
             f"담음 {sum(x['stored'] for x in ok)} · 같은 내용이라 생략 {sum(x['same'] for x in ok)} · "
             f"건너뜀 {sum(x['skipped'] for x in ok)}({'핵심 파일 밖 · 이미지 · .dat' if wide else '.dat · 이미지 · 너무 큼'})",
             f"담은 원본 크기 {sum(x['stored_bytes'] for x in ok) / 1e6:.1f}MB", "",
             f"{'#':<5}{'갈래':<12}{'장비':<12}{'방식':<6}{'Wafer':>6}{'파일':>7}{'담음':>6}  Job / Lot", "-" * 100]
    for x in lots:
        if x.get("skip"):
            lines.append(f"{x['lot_id'].split('_')[0]:<5}{x['why']:<12}{x['device']:<12}  건너뜀 — {x['skip']}  ({x['job']} / {x['lot']})")
        else:
            lines.append(f"{x['lot_id'].split('_')[0]:<5}{x['why']:<12}{x['device']:<12}{x['mode']:<6}{x['wafer_dirs']:>6}"
                         f"{x['files']:>7}{x['stored']:>6}  {x['job']} / {x['lot']}")
    lines += ["", "■ 폴더 구조: <번호_장비_Lot>/<Wafer>/<파일> · <번호_장비_Lot>/report/<Report> · <번호_장비_Lot>/_목록.tsv",
              "  _목록.tsv 의 '저장' 칸: zip 이름(담음) · '= 이름'(앞의 파일과 내용이 같아 생략) · '건너뜀: 이유'"
              + (" · '(안 읽음)' 줄 = 그 Wafer 폴더에서 읽지 않은 파일 수" if wide else ""),
              *(["  <번호_장비_Lot>/_묶음/<파일>.txt = 그 Lot 모든 Wafer 의 결과 파일(WaferInfo · ScanLog · ProductionInfo · Wafer2Table · RecipesInfo ·"
                 " ExtendedScanMetaData_*)을 '### <Wafer>\t<크기>\t<수정시각>' 줄로 이어 붙인 것",
                 "  파라미터 표본: Lot 마다 첫 Wafer 는 하위 폴더(Zones · Recipe2-Zones · TrainData …)까지 텍스트 설정 파일 전부 —"
                 " 같은 내용은 모든 Lot 에 걸쳐 한 번만('= 이름' 은 다른 Lot 을 가리킬 수 있다), lots.json 의 param_wafers"] if all_mode else
                ["  파라미터 표본: Lot 마다 첫 · 마지막 Wafer 는 하위 폴더(Zones · Recipe2-Zones · TrainData …)까지 텍스트 파일 전부"
                 " — lots.json 의 param_wafers"] if wide else []),
              "※ NAS 에서 읽기만 했습니다. 원본은 아무것도 바꾸지 않았습니다."]
    if stop_why:
        lines.append(f"※ 멈춘 이유: {stop_why}")
    summary = "\n".join(lines)
    try:
        packer.add("요약.txt", summary.encode("utf-8"), final=True)
        packer.add("lots.json", json.dumps(lots, ensure_ascii=False, indent=1).encode("utf-8"), final=True)
    except _Full:
        pass
    packer.close()
    parts = packer.parts
    encrypt = all_mode and not getattr(args, "no_encrypt", False)
    if encrypt and parts:
        log("\n암호화하는 중… (보낼 파일은 .enc, 저는 같은 도구로 바로 풉니다)")
        secret = _enc_secret(getattr(args, "key", None))
        enc = []
        for pp in parts:
            e = pp.with_name(pp.name + ".enc")
            e.write_bytes(encrypt_bytes(pp.read_bytes(), secret))
            pp.unlink()
            enc.append(e)
        parts = enc
    summary_path = out_dir / f"{base}_요약.txt"
    if not encrypt:                                         # 암호화하면 Job·Lot 이름이 든 요약을 평문으로 밖에 두지 않는다(zip 안에 있다)
        summary_path.write_text(summary, encoding="utf-8")
    if result is not None:
        result.update(out_dir=str(out_dir), parts=[str(p) for p in parts], summary=(None if encrypt else str(summary_path)),
                      lots=len(ok), stop_why=stop_why, encrypted=encrypt)

    log(summary if len(lines) < 400 else "\n".join(lines[:6] + ["   … Lot 목록은 zip 안 요약.txt 에"] + lines[-6:]))
    log("\n보낼 파일:" + ("  (암호화됨 · .enc)" if encrypt else ""))
    for p in parts:
        mb = p.stat().st_size
        log(f"   {p.name}  {mb / 1e6:.2f}MB")
    if encrypt:
        log("※ 암호화된 .enc 파일입니다. 받는 사람이 열 수는 없고, 개발자(Claude)가 같은 도구로 바로 풉니다.")
    return 0


def decode(args) -> int:
    """암호화된 .enc 를 푼다 — 같은 도구, XOR 한 번이라 빠르다. 결과는 원래 zip."""
    secret = _enc_secret(getattr(args, "key", None))
    out_dir = Path(args.out) if args.out else None
    for f in args.decode:
        src = Path(f)
        try:
            data = decrypt_bytes(src.read_bytes(), secret)
        except (OSError, ValueError) as ex:
            say(f"[오류] {src.name}: {ex}")
            return 2
        name = src.name[:-4] if src.name.lower().endswith(".enc") else src.name + ".zip"
        dst = (out_dir or src.parent) / name
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
        say(f"풀었습니다: {dst}  ({len(data) / 1e6:.1f}MB)")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    args = parse_args(argv)
    if getattr(args, "decode", None):
        return decode(args)
    return run(args)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Wafer 폴더 로그 모으기(NAS 읽기 전용)")
    ap.add_argument("--roots", nargs="+", help="장비 폴더(비우면 DEVICE_ROOTS 전부)")
    ap.add_argument("--out", default="", help="저장 위치(비우면 OUT_DIR)")
    ap.add_argument("--wide", action="store_true",
                    help="2차 수집: Wafer 폴더 맨 위의 핵심 파일만, 장비마다 기간 전체에 고르게 많은 Lot(기본 30일 · 300 Lot)")
    ap.add_argument("--all", action="store_true",
                    help="30일 전체 수집: 기간 안 Report · Lot · Wafer 전부(Wafer 마다 결과 파일만, Lot 묶음 · 첫 Wafer 는 파라미터까지). 몇 시간 걸린다")
    ap.add_argument("--days", type=int, default=None, help="최근 며칠의 Report 에서 고를지(기본 14 · --wide · --all 30)")
    ap.add_argument("--survey", type=int, default=None, help="장비마다 열어 볼 Report 수(기본 15 · --wide 24)")
    ap.add_argument("--min-lots", type=int, default=None, help="최소 Lot 수(기본 10 · --wide 300)")
    ap.add_argument("--max-lots", type=int, default=None, help="최대 Lot 수(기본 150 · --wide 600)")
    ap.add_argument("--per-job-min", type=int, default=None, help="Job(원문)마다 최소 Lot 수 — --all 에서 30일에 모자라면 옛 Lot 으로 채운다(기본 15)")
    ap.add_argument("--look-back", type=int, default=None, help="Job별 최소를 채우려고 되돌아보는 최대 기간(일, --all 기본 90)")
    ap.add_argument("--no-encrypt", action="store_true", help="--all 의 출력을 암호화하지 않는다(기본은 암호화 .enc)")
    ap.add_argument("--decode", nargs="+", metavar="FILE", help="암호화된 .enc 를 풀어 원래 zip 으로(다른 옵션 없이)")
    ap.add_argument("--key", default=None, help="암호(비우면 환경변수 AOI_LOG_KEY, 그것도 없으면 저장소 기본 키)")
    ap.add_argument("--max-minutes", type=float, default=None, help="이 시간이 지나면 담던 Lot 까지만 하고 마무리(기본 120분 · --all 24시간)")
    ap.add_argument("--workers", type=int, default=8, help="동시에 읽는 수")
    ap.add_argument("--part-max", type=int, default=PART_MAX, help=argparse.SUPPRESS)
    ap.add_argument("--part-min", type=int, default=PART_MIN, help=argparse.SUPPRESS)
    ap.add_argument("--plan", action="store_true", help="고를 Lot 만 보여 주고 끝낸다")
    return ap.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main())
