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
import json
import os
import re
import sys
import time
import zipfile
import zlib
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
    """Report 이름의 날짜(배치 종료일) → epoch(그날 0시). 못 읽으면 None."""
    m = REPORT_RE.match(name)
    if not m:
        return None
    mon = MONTHS.get(m.group(5).lower())
    if not mon:
        return None
    try:
        return time.mktime((2000 + int(m.group(6)), mon, int(m.group(4)), 0, 0, 0, 0, 0, -1))
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


def survey_device(root: Path, days: int, n_read: int) -> dict:
    """한 대: Report 폴더를 한 번 나열하고 최근 Report 를 n_read 개만 연다. 읽기 전용."""
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
    for t, name, path in files[:n_read]:
        try:
            text = read_bytes(path).decode("utf-8", errors="replace")
        except OSError:
            continue
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
            "error": err, "cats": categories(job, lots[0], dev["name"], err)})
    dev["ok"] = True
    dev["n_listed"] = len(files)
    return dev


# ── zip 나누기 ──────────────────────────────────────────────────────────────────
class Packer:
    """zip 을 차례로 채운다. 항목을 넣기 전에 압축 크기를 미리 재서 PART_MAX 를 넘기 전에 다음 장으로 넘긴다."""

    def __init__(self, out_dir: Path, base: str, part_max: int = PART_MAX, reserve: int = RESERVE):
        self.out_dir, self.base, self.part_max, self.reserve = out_dir, base, part_max, reserve
        self.parts, self.z, self.cd = [], None, 0

    def _open(self):
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


def walk_wafer(wdir: Path):
    """Wafer 폴더 **안**만 본다(이 폴더 밖으로 나가지 않는다). [(상대경로, 크기, 수정시각, 내용 또는 None, 건너뛴 이유)]"""
    out, stack = [], [(wdir, "", 0)]
    while stack:
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
            if not why:
                try:
                    data = read_bytes(e.path)
                except OSError as ex:
                    why = f"읽기 실패: {ex}"
            out.append((r, st.st_size, st.st_mtime, data, why))
    out.sort(key=lambda x: x[0].lower())
    return out


def recipe_mode(files) -> str:
    """첫 Wafer 의 RecipesInfo.ini 레시피 수로 멀티/단일을 본다(없고 WaferInfo 만 있으면 단일)."""
    by = {r: d for r, _s, _m, d, _w in files if d is not None}
    ri = by.get("RecipesInfo.ini")
    if ri is not None:
        n = len(re.findall(rb"^\s*\[Recipe-\d+\]", ri, re.M))
        return "멀티" if n >= 2 else "단일"
    return "단일" if "WaferInfo.ini" in by else "모름"


def collect_lot(idx: int, c: dict, scan_names, pool, packer: Packer) -> dict:
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
    results = list(pool.map(lambda e: walk_wafer(Path(e.path)), wafers))

    try:
        rep = IMG_B64.sub('src=""', read_bytes(c["report_path"]).decode("utf-8", errors="replace")).encode("utf-8")
        packer.add(f"{lot_id}/report/{c['report']}", rep, c["t"])
    except OSError:
        pass
    first = {}                                     # sha1 → 처음 담은 zip 안 이름 (이 Lot 안에서만)
    rows = ["wafer\t상대경로\t크기\t수정시각\tsha1\t저장"]
    n_files = n_stored = n_same = n_skip = 0
    raw = 0
    for w, files in zip(wafers, results):
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


# ── 고르기 ──────────────────────────────────────────────────────────────────────
def pick(cands, cat: str, chosen_keys: set, dev_count: dict, tried: set):
    """그 갈래에서 아직 안 고른 Report 하나 — 덜 쓴 장비, 꽉 찬 Lot(20장 이상), 최근 순."""
    pool = [c for c in cands if cat in c["cats"] and c["key"] not in chosen_keys and c["key"] not in tried]
    if not pool:
        return None
    pool.sort(key=lambda c: (dev_count.get(c["device"], 0), len(c["wafers"]) < 20 and cat != "Error 포함", -c["t"]))
    return pool[0]


def run(args) -> int:
    t0 = time.time()
    out_dir = Path(args.out or OUT_DIR)
    roots = [norm_root(r) for r in (args.roots or DEVICE_ROOTS)]
    drives = {os.path.splitdrive(str(r))[0].upper() for r in roots} - {""}
    out_abs = os.path.normcase(os.path.abspath(out_dir))
    if os.path.splitdrive(str(out_dir))[0].upper() in drives or any(
            out_abs.startswith(os.path.normcase(os.path.abspath(r))) for r in roots):
        say(f"[오류] 저장 위치가 NAS 쪽입니다: {out_dir}. 로컬 폴더를 --out 으로 지정하세요.")
        return 2

    say(f"1/3 둘러보기 — 장비 {len(roots)}대, 최근 {args.days}일 Report 를 장비마다 {args.survey}개까지 엽니다")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        devs = list(pool.map(lambda r: survey_device(r, args.days, args.survey), roots))
    cands, scan_of = [], {}
    for d in devs:
        state = f"Report {len(d['reports'])}개 읽음" if d["ok"] else f"건너뜀 — {d['error']}"
        say(f"   {d['name']:<12} {state}")
        if d["ok"]:
            scan_of[d["name"]] = d["scan_dirs"]
            cands.extend(d["reports"])
    seen = set()
    for c in cands:
        c["key"] = (c["device"], c["job"], c["setup"], c["lot"])
    cands = [c for c in cands if not (c["key"] in seen or seen.add(c["key"]))]   # 같은 Lot 폴더는 한 번
    if not cands:
        say("[오류] 읽은 Report 가 없습니다. 드라이브 연결과 DEVICE_ROOTS 를 확인하세요.")
        return 2
    counts = {}
    for c in cands:
        for k in c["cats"]:
            counts[k] = counts.get(k, 0) + 1
    say("   후보 Lot: " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])))

    if args.plan:
        chosen, dev_count, keys = [], {}, set()
        for cat, n in QUOTAS:
            for _ in range(n):
                c = pick(cands, cat, keys, dev_count, set())
                if c:
                    keys.add(c["key"])
                    dev_count[c["device"]] = dev_count.get(c["device"], 0) + 1
                    chosen.append((cat, c))
        say("\n고를 Lot(첫 바퀴):")
        for cat, c in chosen:
            say(f"   [{cat}] {c['device']} · {c['job']} / {c['lot']} · {len(c['wafers'])}장 · {c['report']}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    base = "AOI_wafer_logs_" + time.strftime("%Y%m%d_%H%M")
    packer = Packer(out_dir, base, args.part_max, min(RESERVE, args.part_max // 10))
    lots, dev_count, keys, tried = [], {}, set(), set()
    deadline = t0 + args.max_minutes * 60
    stop_why = ""

    def done_ok() -> int:
        return sum(1 for x in lots if not x.get("skip"))

    def take(cat: str, pool) -> bool:
        for _ in range(6):                                  # 폴더가 없으면 같은 갈래의 다음 후보
            c = pick(cands, cat, keys, dev_count, tried)
            if c is None:
                return False
            tried.add(c["key"])
            c["why"] = cat
            say(f"   [{len(lots) + 1:>2}] {cat:<10} {c['device']} · {c['job']} / {c['lot']} ({len(c['wafers'])}장)")
            info = collect_lot(len(lots) + 1, c, scan_of.get(c["device"], []), pool, packer)
            lots.append(info)
            if info.get("skip"):
                say(f"        건너뜀 — {info['skip']}")
                continue
            keys.add(c["key"])
            dev_count[c["device"]] = dev_count.get(c["device"], 0) + 1
            say(f"        Wafer {info['wafer_dirs']} · 파일 {info['files']} → 담음 {info['stored']} · 같은 내용 {info['same']}"
                f" · 건너뜀 {info['skipped']} · {info['mode']}")
            say(f"        zip {len(packer.parts)}장 · 합계 {packer.total() / 1e6:.1f}MB · 지금 장 {packer.size() / 1e6:.1f}MB"
                f" · {(time.time() - t0) / 60:.0f}분 지남")
            return True
        return False

    say(f"\n2/3 Lot 담기 — 저장 위치 {out_dir}")
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for cat, n in QUOTAS:
                for _ in range(n):
                    if time.time() > deadline:
                        break
                    take(cat, pool)
            i = 0
            while True:
                rdl_single = any(x.get("mode") == "단일" and x.get("cats", [""])[0].startswith("RDL") for x in lots)
                if done_ok() >= args.min_lots and packer.size() >= args.part_min and (rdl_single or i >= 12):
                    break                                   # RDL 단일을 12번 더 찾아도 없으면 그만(요약에 방식이 보인다)
                if time.time() > deadline:
                    stop_why = f"시간 상한({args.max_minutes}분)"
                    break
                if len(lots) >= args.max_lots:
                    stop_why = f"Lot 수 상한({args.max_lots})"
                    break
                order = (["RDL 멀티", "RDL 기타"] if not rdl_single and i < 12 else []) + FILL_ORDER
                if not any(take(cat, pool) for cat in order[i % len(order):] + order[:i % len(order)]):
                    stop_why = "더 고를 후보 없음(--days · --survey 를 늘려 보세요)"
                    break
                i += 1
    except KeyboardInterrupt:
        stop_why = "중간에 멈춤(Ctrl+C)"
        say("\n멈춤 — 지금까지 담은 것으로 마무리합니다")

    # ── 요약 ──
    say("\n3/3 요약 쓰는 중…")
    ok = [x for x in lots if not x.get("skip")]
    lines = [f"AOI Wafer 폴더 로그 · {stamp(time.time())} · 걸린 시간 {(time.time() - t0) / 60:.1f}분",
             f"담은 Lot {len(ok)}개 (시도 {len(lots)}) · 파일 {sum(x['files'] for x in ok)}개 중 "
             f"담음 {sum(x['stored'] for x in ok)} · 같은 내용이라 생략 {sum(x['same'] for x in ok)} · "
             f"건너뜀 {sum(x['skipped'] for x in ok)}(.dat · 이미지 · 너무 큼)",
             f"담은 원본 크기 {sum(x['stored_bytes'] for x in ok) / 1e6:.1f}MB", "",
             f"{'#':<4}{'갈래':<12}{'장비':<12}{'방식':<6}{'Wafer':>6}{'파일':>7}{'담음':>6}  Job / Lot", "-" * 100]
    for x in lots:
        if x.get("skip"):
            lines.append(f"{x['lot_id'][:2]:<4}{x['why']:<12}{x['device']:<12}  건너뜀 — {x['skip']}  ({x['job']} / {x['lot']})")
        else:
            lines.append(f"{x['lot_id'][:2]:<4}{x['why']:<12}{x['device']:<12}{x['mode']:<6}{x['wafer_dirs']:>6}"
                         f"{x['files']:>7}{x['stored']:>6}  {x['job']} / {x['lot']}")
    lines += ["", "■ 폴더 구조: <번호_장비_Lot>/<Wafer>/<파일> · <번호_장비_Lot>/report/<Report> · <번호_장비_Lot>/_목록.tsv",
              "  _목록.tsv 의 '저장' 칸: zip 이름(담음) · '= 이름'(앞의 파일과 내용이 같아 생략) · '건너뜀: 이유'",
              "※ NAS 에서 읽기만 했습니다. 원본은 아무것도 바꾸지 않았습니다."]
    if stop_why:
        lines.append(f"※ 멈춘 이유: {stop_why}")
    summary = "\n".join(lines)
    packer.add("요약.txt", summary.encode("utf-8"), final=True)
    packer.add("lots.json", json.dumps(lots, ensure_ascii=False, indent=1).encode("utf-8"), final=True)
    packer.close()
    (out_dir / f"{base}_요약.txt").write_text(summary, encoding="utf-8")

    say(summary)
    say("\n보낼 파일:")
    for p in packer.parts:
        mb = p.stat().st_size
        note = "" if args.part_min <= mb <= args.part_max else ("  ← 마지막 장이라 25MB 에 못 미침" if p == packer.parts[-1] else "  ← 크기 범위 밖")
        say(f"   {p.name}  {mb / 1e6:.2f}MB{note}")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="Wafer 폴더 로그 모으기(NAS 읽기 전용)")
    ap.add_argument("--roots", nargs="+", help="장비 폴더(비우면 DEVICE_ROOTS 전부)")
    ap.add_argument("--out", default="", help="저장 위치(비우면 OUT_DIR)")
    ap.add_argument("--days", type=int, default=14, help="최근 며칠의 Report 에서 고를지")
    ap.add_argument("--survey", type=int, default=15, help="장비마다 열어 볼 최근 Report 수")
    ap.add_argument("--min-lots", type=int, default=10, help="최소 Lot 수")
    ap.add_argument("--max-lots", type=int, default=150, help="최대 Lot 수")
    ap.add_argument("--max-minutes", type=float, default=120, help="이 시간이 지나면 담던 Lot 까지만 하고 마무리")
    ap.add_argument("--workers", type=int, default=8, help="동시에 읽는 수")
    ap.add_argument("--part-max", type=int, default=PART_MAX, help=argparse.SUPPRESS)
    ap.add_argument("--part-min", type=int, default=PART_MIN, help=argparse.SUPPRESS)
    ap.add_argument("--plan", action="store_true", help="고를 Lot 만 보여 주고 끝낸다")
    return run(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
