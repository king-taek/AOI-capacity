"""AOI-25 샘플 모으기 — 개발에 필요한 실물 Report/INI 를 한 폴더에 모아 zip 한 장으로 만든다.

무엇을 모으는가
  1. Report 폴더의 **전체 파일 목록**(이름·크기·수정시각) — Lot 표기 규칙(RE · SRD · DIA · 3D …)을 여기서 본다.
  2. 고른 Report 원본 `.htm` — Scan error 가 있는 것, 그 Lot 의 앞뒤(재스캔 후보), 표기별 대표, 최근 하루치.
  3. 고른 Report 의 **정확 경로** Lot 폴더에 있는 `WaferInfo.ini` 와 그 폴더 목록(수정시각 포함).
     INI 가 재스캔 때 덮어써지는지, 재스캔용 폴더가 따로 생기는지를 이 목록으로 본다.

★ NAS 는 **읽기만** 한다. NAS 아래에는 파일을 만들지도 바꾸지도 지우지도 않는다. 쓰기는 `--out` 폴더(기본 바탕화면)뿐이다.
★ Scanresult 를 재귀 검색하지 않는다. Report 파일명에서 계산한 Lot 폴더 **하나만** 나열한다.
★ 표준 라이브러리만 쓴다 — 앱이 설치돼 있지 않아도 이 파일 하나만 있으면 돌아간다.

    python collect_sample.py --all                    # 아래 DEVICE_ROOTS 전 장비 → zip 한 장
    python collect_sample.py                          # 한 대만(기본 Y:\\AOI-25)
    python collect_sample.py --root X:\\AOI-1 --days 2
    python collect_sample.py --roots "X:\\AOI-1" "M:\\AOI-8"   # 고른 몇 대만
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  --all 로 훑을 장비 목록 — 경로가 바뀌면 여기만 고치면 됩니다.
DEVICE_ROOTS = [
    r"X:\AOI-1", r"X:\AOI-2", r"X:\AOI-3", r"X:\AOI-4", r"X:\AOI-5", r"X:\AOI-6", r"X:\AOI-7",
    r"M:\AOI-8", r"M:\AOI-9",
    r"V:\AOI-10", r"V:\AOI-11", r"V:\AOI-12", r"V:\AOI-13", r"V:\AOI-14", r"V:\AOI-15", r"V:\AOI-16",
    r"P:\AOI-17", r"P:\AOI-18", r"P:\AOI-19", r"P:\AOI-20", r"P:\AOI-21", r"P:\AOI-22", r"P:\AOI-23",
    r"Y:\AOI-24", r"Y:\AOI-25",
    r"I:\4F-AOI-01", r"I:\4F-AOI-02", r"I:\4F-AOI-03", r"I:\4F-AOI-04", r"I:\4F-AOI-05",
]
# ══════════════════════════════════════════════════════════════════════════════

REPORT_RE = re.compile(
    r"^(.+?)_(\d{4})_(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)
STATUS_PATTERNS = [
    ("SCAN_ERROR", re.compile(r"scan\s*error", re.I)),
    ("ID_READ_ERROR", re.compile(r"failed\s+to\s+read\s+wafer\s+id", re.I)),
    ("USER_ABORT", re.compile(r"wafer\s+aborted\s+by\s+user", re.I)),
    ("ABORTED", re.compile(r"abort", re.I)),
    ("SKIPPED", re.compile(r"skip", re.I)),
]
TAGS = re.compile(r"<[^>]+>")
DEFAULT_ROOT = r"Y:\AOI-25"
REPORT_DIR_NAMES = ("Report", "Reports")
SCAN_DIR_NAMES = ("Scanresult", "ScanResult", "Scanresults")


class _Tables(HTMLParser):
    """표를 행 단위 셀 목록으로 모은다(앱의 TableParser 와 같은 방식, 여기서는 단독 실행을 위해 따로 둔다)."""

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
    """Report 안에서 Job/Setup · Lot · Wafer ID · Batch 시각을 꺼낸다.

    ★ Scanresult 경로의 출처는 파일명이 아니라 이 `Job/Setup` 이다."""
    p = _Tables()
    p.feed(text)
    out = {"job": "", "setup": "", "lots": [], "wafers": [], "summary": {}}
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
        out["job"], _, out["setup"] = js.rpartition("/")
        out["job"], out["setup"] = out["job"].strip(), out["setup"].strip()
    seen = []
    for lot, _w in out["wafers"]:
        if lot and lot not in seen and not re.match(r"^loadport", lot, re.I):
            seen.append(lot)
    out["lots"] = seen
    return out


def find_subdir(root: Path, configured: str, defaults) -> str:
    for name in ([configured] if configured else []) + list(defaults):
        if os.path.isdir(root / name):
            return name
    return ""


#: Report 안에 박힌 로고(base64)는 내용과 무관한데 zip 의 90%를 차지한다 — 복사할 때 뺀다.
IMG_B64 = re.compile(r'src="data:image/[^;]+;base64,[^"]*"')
#: 시각 표기는 장비마다 다르다(앱의 collect.DT_FORMATS 와 같은 목록 — 단독 실행을 위해 여기에도 둔다).
DT_FORMATS = ["%d-%b-%y %I:%M:%S %p", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%d-%b-%y %H:%M:%S"]
#: Lot 이름의 작업 표기(앱의 collect.scan_type 과 같은 규칙)
LOT_MARKS = {"RE": "RESCAN", "RESCAN": "RESCAN", "REWORK": "REWORK"}


def parse_dt(value: str):
    v = str(value or "").strip()
    for f in DT_FORMATS:
        try:
            return time.strptime(v, f)
        except ValueError:
            pass
    return None


def shape(value: str) -> str:
    """시각 표기의 '모양' — 9/16/2026 1:54:03 PM → 9/99/9999 9:99:99 PM."""
    return re.sub(r"\d", "9", str(value or "").strip()) or "(빈값)"


def path_tail(path) -> str:
    """경로의 마지막 폴더 이름(장비 이름). 구분자는 Windows·POSIX 둘 다 본다."""
    return re.split(r"[\\/]+", str(path or "").rstrip("\\/"))[-1] if str(path or "") else ""


def lot_marks(lot: str) -> set:
    return {LOT_MARKS[t] for t in (x.upper() for x in re.split(r"[\s_-]+", str(lot or "")) if x) if t in LOT_MARKS}


def copy_report(src: str, dst: Path, keep_images: bool) -> None:
    if keep_images:
        shutil.copy2(src, dst)
        return
    dst.write_text(IMG_B64.sub('src=""', read_text(src)), encoding="utf-8")


def say(msg: str) -> None:
    print(msg, flush=True)


def stamp(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def read_text(path) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def lot_parts(lot: str):
    """Lot 이름을 앞부분과 접미사로 나눈다. 'TUK RESCAN' → ('TUK', 'RESCAN'), 'XAC-DIA' → ('XAC', 'DIA')."""
    m = re.split(r"[\s_-]+", str(lot).strip(), maxsplit=1)
    return (m[0], m[1].upper()) if len(m) == 2 else (str(lot).strip(), "")


def scan_reports(rep_dir: Path, limit: int):
    """Report 폴더를 한 번 나열하고(scandir+stat), 최근 것부터 limit 개만 열어 상태를 본다. 읽기 전용."""
    files = [e for e in os.scandir(rep_dir) if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
    files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
    infos = []
    for i, e in enumerate(files):
        m = REPORT_RE.match(e.name)
        info = {"name": e.name, "path": e.path, "mtime": e.stat().st_mtime, "size": e.stat().st_size,
                "equipment": m.group(1) if m else "", "process": m.group(2) if m else "",
                "lot": m.group(3) if m else "", "matched": bool(m), "flags": [], "read": False}
        if i < limit:
            try:
                raw = read_text(e.path)
                info["flags"] = [k for k, rx in STATUS_PATTERNS if rx.search(TAGS.sub(" ", raw))]
                facts = report_facts(raw)
                info.update({"job": facts["job"], "setup": facts["setup"], "lots": facts["lots"],
                             "batch_start": facts["summary"].get("Batch Start", ""),
                             "batch_end": facts["summary"].get("Batch End", ""),
                             "wafers_scanned": facts["summary"].get("Wafers Scanned", "")})
                if facts["lots"]:
                    info["lot"] = facts["lots"][0]        # 파일명 대신 Report 안의 Lot 을 믿는다
                info["read"] = True
            except OSError as ex:
                info["flags"] = [f"READ_ERROR({type(ex).__name__})"]
        infos.append(info)
    return infos


def pick_samples(infos, days: int, max_reports: int):
    """보내면 도움이 되는 Report 를 고른다. (선택목록, 이유별 설명)"""
    chosen, why = [], {}

    def add(info, reason):
        if info["name"] in why:
            why[info["name"]] += f" · {reason}"
            return
        if len(chosen) >= max_reports:
            return
        why[info["name"]] = reason
        chosen.append(info)

    read = [i for i in infos if i["read"]]
    # 1) Scan error 가 있는 Report 와, 같은 Lot 의 앞뒤 Report(재스캔 전후를 보기 위해)
    errs = [i for i in read if "SCAN_ERROR" in i["flags"]][:6]
    for e in errs:
        add(e, "Scan error 포함")
        same = [i for i in read if i["lot"] == e["lot"] and i["name"] != e["name"]]
        same.sort(key=lambda i: abs(i["mtime"] - e["mtime"]))
        for s in same[:2]:
            add(s, f"같은 Lot({e['lot']}) 앞뒤 — 재스캔 확인용")
    # 2) 다른 오류 유형도 한 개씩
    for kind in ("ID_READ_ERROR", "USER_ABORT", "ABORTED"):
        for i in read:
            if kind in i["flags"]:
                add(i, f"{kind} 포함")
                break
    # 3) Lot 접미사(RE · SRD · DIA · 3D …) 별 대표 2개씩 — 표기 규칙 확정용
    by_suffix = {}
    for i in read:
        if i["matched"]:
            by_suffix.setdefault(lot_parts(i["lot"])[1], []).append(i)
    for suffix, items in sorted(by_suffix.items()):
        for i in items[:2]:
            add(i, f"Lot 표기 '{suffix or '(접미사 없음)'}' 대표")
    # 4) 최근 N일치 — 하루 가동률을 실제와 맞춰 보기 위해
    since = time.time() - days * 86400
    for i in read:
        if i["mtime"] >= since:
            add(i, f"최근 {days}일치")
    # 5) 파일명 형식이 다른 것(파서가 못 읽는 이름) 2개
    for i in [x for x in infos if not x["matched"]][:2]:
        add(i, "파일명 형식이 다름")
    return chosen, why


def copy_ini_for(info, scan_root: Path, out_dir: Path, max_ini: int, lines: list, seen=None) -> int:
    """Report 에서 계산한 **정확한** Lot 폴더 하나만 나열해 WaferInfo.ini 를 복사한다(재귀 검색 없음)."""
    # Job/Setup 이 있으면 그것이 정답이고, 없으면(AOI-1 처럼 옛 형식) 파일명 규칙으로 돌아간다
    job = info.get("job", "") or info.get("equipment", "")
    setup = info.get("setup", "") if info.get("job") else info.get("process", "")
    if not job:
        return 0                                   # 어느 쪽으로도 경로를 만들 수 없다
    lot_dir = scan_root / job / setup / info["lot"] if setup else scan_root / job / info["lot"]
    if seen is not None:
        if str(lot_dir) in seen:
            return 0                       # 같은 Lot 을 가리키는 Report 가 여럿이면 한 번만 나열한다
        seen.add(str(lot_dir))
    lines.append(f"\n[{info['name']}]\n  Lot 폴더: {lot_dir}")
    if not os.path.isdir(lot_dir):
        lines.append("  → 폴더 없음(이 Lot 의 Scanresult 가 지워졌거나 경로 규칙이 다릅니다)")
        return 0
    n = 0
    try:
        wafers = sorted(os.scandir(lot_dir), key=lambda e: e.name)
    except OSError as ex:
        lines.append(f"  → 나열 실패: {ex}")
        return 0
    for w in wafers:
        if not w.is_dir():
            lines.append(f"  (파일) {w.name}")
            continue
        ini = Path(w.path) / "WaferInfo.ini"
        if ini.is_file():
            st = ini.stat()
            lines.append(f"  {w.name}/WaferInfo.ini  {st.st_size}B  수정 {stamp(st.st_mtime)}")
            if n < max_ini:
                rel = Path(job) / setup / info["lot"] / w.name if setup else Path(job) / info["lot"] / w.name
                dst = out_dir / "Scanresult" / rel / "WaferInfo.ini"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ini, dst)
                n += 1
        else:
            lines.append(f"  {w.name}/  (WaferInfo.ini 없음)")
    return n


def norm_root(text: str) -> Path:
    """`Y:` 처럼 드라이브 문자만 준 경우 `Y:\\` 로 맞춘다(그냥 두면 '그 드라이브의 현재 폴더' 가 된다)."""
    t = str(text).strip().strip('"')
    return Path(t + os.sep if re.fullmatch(r"[A-Za-z]:", t) else t)


def list_folder(path: Path, title: str = "") -> int:
    """폴더 바로 아래 이름만 보여 준다 — 경로를 못 찾을 때 어디에 무엇이 있는지 확인하는 용도."""
    say(title or f"[{path}] 바로 아래 목록")
    if not os.path.isdir(path):
        say("   → 이 경로에 접근할 수 없습니다(없거나, 권한이 없거나, 드라이브가 연결되지 않음)")
        return 2
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError as ex:
        say(f"   → 목록을 읽지 못했습니다: {ex}")
        return 2
    if not entries:
        say("   → 비어 있습니다")
    for e in entries[:60]:
        say(f"   {'[폴더] ' if e.is_dir() else '       '}{e.name}")
    if len(entries) > 60:
        say(f"   … 외 {len(entries) - 60}개")
    return 0


def diagnose(root: Path, report_dir: str) -> None:
    """Report 폴더를 못 찾았을 때 무엇이 문제인지 짚어 준다(이름만 읽고 파일은 열지 않는다)."""
    say(f"[오류] Report 폴더를 찾을 수 없습니다: {root / report_dir}")
    say("")
    say("■ 확인한 것")
    drive = os.path.splitdrive(str(root.resolve() if not str(root).startswith("\\\\") else root))[0]
    if drive:
        ok = os.path.isdir(drive + os.sep)
        say(f"   {drive}{os.sep:<24} {'있음' if ok else '없음 — 네트워크 드라이브가 연결되지 않았을 수 있습니다'}")
    say(f"   {str(root):<25} {'있음' if os.path.isdir(root) else '없음'}")
    if os.path.isdir(root):
        say("")
        list_folder(root, f"■ {root} 안에 있는 것")
        try:
            cand = [e.name for e in os.scandir(root) if e.is_dir() and e.name.lower().startswith("report")]
        except OSError:
            cand = []
        if cand and cand[0] != report_dir:
            say("")
            say(f"   → Report 폴더 이름이 '{cand[0]}' 인 것 같습니다. `--report-dir \"{cand[0]}\"` 을 붙여 주세요.")
    else:
        letters = [f"{c}:" for c in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.isdir(f"{c}:{os.sep}")]
        if letters:
            say("")
            say("   지금 이 PC 에서 보이는 드라이브: " + " ".join(letters))
    say("")
    say("■ 이렇게 해 보세요 (저장소 폴더에서 실행 · 경로에 공백이 있으면 따옴표)")
    say(r'   python scripts\collect_sample.py --root Y:\AOI-25')
    say(r'   python scripts\collect_sample.py --list --root Y:\          (Y 드라이브에 어떤 폴더가 있는지 보기)')
    say(r'   python scripts\collect_sample.py --root \\10.142.80.88\공유이름\AOI-25   (드라이브 문자 대신 주소로)')


def collect_one(root: Path, out_dir: Path, args) -> dict:
    """장비 한 대를 훑어 out_dir 에 담고, 점검에 필요한 사실을 돌려준다. NAS 는 읽기만 한다."""
    facts = {"root": str(root), "ok": False, "error": ""}
    rep_name = find_subdir(root, args.report_dir, REPORT_DIR_NAMES)
    scan_name = find_subdir(root, args.scan_dir, SCAN_DIR_NAMES) or (args.scan_dir or "Scanresult")
    if not rep_name:
        facts["error"] = "Report 폴더를 찾지 못함(경로·권한 확인)" if not os.path.isdir(root) else \
                         f"Report 폴더 없음 (안에 있는 것: {', '.join(sorted(os.listdir(root))[:6])})"
        return facts
    rep_dir, scan_root = root / rep_name, root / scan_name
    facts.update({"report_dir": rep_name, "scan_dir": scan_name, "scan_dir_exists": os.path.isdir(scan_root)})

    infos = scan_reports(rep_dir, args.scan)
    if not infos:
        facts["error"] = f"{rep_name} 폴더에 .htm 파일이 없음"
        return facts
    (out_dir / "Report").mkdir(parents=True, exist_ok=True)
    read = [i for i in infos if i["read"]]

    listing = [f"# {rep_dir}", f"# 전체 {len(infos)}개 · 만든 시각 {stamp(time.time())}", "",
               "수정시각\t크기\t파일명"]
    listing += [f"{stamp(i['mtime'])}\t{i['size']}\t{i['name']}" for i in infos]
    (out_dir / "report_목록.txt").write_text("\n".join(listing), encoding="utf-8")

    chosen, why = pick_samples(infos, args.days, args.max_reports)
    for i in chosen:
        try:
            copy_report(i["path"], out_dir / "Report" / i["name"], args.keep_images)
        except OSError as ex:
            why[i["name"]] += f" (복사 실패: {ex})"

    scan_lines = [f"# {scan_root}", "# 고른 Report 의 Lot 폴더만 정확 경로로 한 번씩 나열했습니다(재귀 검색 없음).",
                  "# INI 수정시각이 Report 시각보다 늦으면 다시 검사하며 덮어써졌을 수 있습니다."]
    seen_lots = set()
    n_ini = sum(copy_ini_for(i, scan_root, out_dir, args.max_ini, scan_lines, seen_lots) for i in chosen)
    (out_dir / "scan_폴더구조.txt").write_text("\n".join(scan_lines), encoding="utf-8")

    # ── 점검용 사실 ──────────────────────────────────────────────────────
    marks = Counter()
    for i in read:
        for m in lot_marks(i["lot"]):
            marks[m] += 1
    times = Counter(shape(i.get("batch_start", "")) for i in read)
    bad_time = sum(1 for i in read if i.get("batch_start") and parse_dt(i["batch_start"]) is None)
    ini_lines = [l for l in scan_lines if "WaferInfo.ini" in l]
    facts.update({
        "ok": True, "reports": len(infos), "read": len(read), "copied": len(chosen), "ini_copied": n_ini,
        "oldest": stamp(infos[-1]["mtime"]), "newest": stamp(infos[0]["mtime"]),
        "filename_rule_match": sum(1 for i in infos if i["matched"]),
        "job_setup": Counter(f"{i.get('job','')}/{i.get('setup','')}" for i in read).most_common(3),
        "has_job_setup": sum(1 for i in read if i.get("job")),
        "batch_time_shapes": times.most_common(4), "batch_time_unparsed": bad_time,
        "status_flags": Counter(f for i in read for f in (i["flags"] or ["(오류 표시 없음)"])).most_common(),
        "lot_marks": dict(marks), "lot_samples": [i["lot"] for i in read[:6]],
        "ini_found": len(ini_lines), "ini_missing": sum(1 for l in scan_lines if "WaferInfo.ini 없음" in l),
        "lot_dir_missing": sum(1 for l in scan_lines if "폴더 없음" in l),
    })

    summary = [f"AOI 샘플 · {stamp(time.time())}", f"대상: {root}  (폴더: {rep_name} · {scan_name})",
               f"Report 전체 {len(infos)}개 (기간 {facts['oldest']} ~ {facts['newest']})",
               f"열어 본 Report {len(read)}개 · 담은 Report {len(chosen)}개 · 담은 INI {n_ini}개", "",
               "■ Lot 작업 표기", *([f"   {k:<10} {v}건" for k, v in marks.most_common()] or ["   (없음)"]), "",
               "■ 상태 표시", *[f"   {k:<16} {v}건" for k, v in facts["status_flags"]], "",
               "■ Batch 시각 표기", *[f"   {k:<26} {v}건" for k, v in facts["batch_time_shapes"]],
               f"   읽지 못한 시각 {bad_time}건", "",
               "■ 담은 Report 와 고른 이유", *[f"   {i['name']}\n      → {why[i['name']]}" for i in chosen], "",
               "※ NAS 에서 '복사'만 했습니다. 원본은 읽기만 했고 아무것도 바꾸지 않았습니다."]
    if not args.keep_images:
        summary.insert(4, "※ Report 안의 로고 이미지는 용량 때문에 뺐습니다(내용은 그대로).")
    (out_dir / "요약.txt").write_text("\n".join(summary), encoding="utf-8")
    return facts


def make_zip(out_base: Path, folder: Path) -> Path:
    zip_path = out_base / (folder.name + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out_base))
    return zip_path


def sweep(roots, out_base: Path, args) -> int:
    """여러 장비를 한 번에 훑어 zip 한 장으로 만든다. 한 대가 막혀도 나머지는 계속한다."""
    folder = out_base / ("AOI_sample_all_" + time.strftime("%Y%m%d_%H%M"))
    folder.mkdir(parents=True, exist_ok=True)
    facts = []
    for n, raw in enumerate(roots, 1):
        root = norm_root(raw)
        name = path_tail(root) or f"device{n}"
        say(f"[{n}/{len(roots)}] {root}")
        try:
            f = collect_one(root, folder / name, args)
        except Exception as ex:                      # noqa: BLE001 - 한 대 때문에 전체가 멈추지 않게
            f = {"root": str(root), "ok": False, "error": f"{type(ex).__name__}: {ex}"}
        f["name"] = name
        facts.append(f)
        say(f"      {'Report %d개 · 담은 %d개 · INI %d개' % (f['reports'], f['copied'], f['ini_copied'])}"
            if f["ok"] else f"      건너뜀 — {f['error']}")

    (folder / "요약.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = [f for f in facts if f["ok"]]
    lines = [f"AOI 전 장비 샘플 · {stamp(time.time())}",
             f"장비 {len(facts)}대 중 {len(ok)}대 성공 · Report 합계 {sum(f['reports'] for f in ok)}개", "",
             f"{'장비':<12}{'Report':>8}{'기간(최근)':>22}  {'폴더':<10}{'Job/Setup':>10}{'시각오류':>8}  표기",
             "-" * 96]
    for f in facts:
        if not f["ok"]:
            lines.append(f"{f['name']:<12}  건너뜀 — {f['error']}")
            continue
        marks = " ".join(f"{k}:{v}" for k, v in sorted(f["lot_marks"].items())) or "-"
        lines.append(f"{f['name']:<12}{f['reports']:>8}{f['newest']:>22}  {f['report_dir']:<10}"
                     f"{('있음' if f['has_job_setup'] else '없음'):>10}{f['batch_time_unparsed']:>8}  {marks}")
    lines += ["", "■ 장비별 자세한 내용은 각 폴더의 요약.txt 를, 기계가 읽는 사실은 요약.json 을 보세요.",
              "※ NAS 에서 '복사'만 했습니다. 원본은 읽기만 했고 아무것도 바꾸지 않았습니다."]
    (folder / "요약.txt").write_text("\n".join(lines), encoding="utf-8")
    say("")
    say("\n".join(lines[:5 + len(facts)]))

    zip_path = make_zip(out_base, folder)
    say("")
    say(f"완료했습니다.  보낼 파일: {zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB)")
    say(f"  풀린 폴더: {folder}")
    say("  먼저 요약.txt 를 열어 내용을 확인한 뒤 보내 주세요.")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="AOI 샘플 모으기(NAS 읽기 전용)")
    ap.add_argument("--root", default=DEFAULT_ROOT, help=r"장비 폴더 한 대 (기본 Y:\AOI-25)")
    ap.add_argument("--roots", nargs="+", help="장비 폴더 여러 대")
    ap.add_argument("--all", action="store_true", help="파일 위쪽 DEVICE_ROOTS 의 전 장비를 훑는다")
    ap.add_argument("--out", default="", help="저장 위치 (기본 바탕화면)")
    ap.add_argument("--report-dir", default="", help="비우면 Report / Reports 를 자동으로 찾는다")
    ap.add_argument("--scan-dir", default="", help="비우면 Scanresult 를 자동으로 찾는다")
    ap.add_argument("--scan", type=int, default=0, help="상태를 보려고 열어 볼 최근 Report 개수")
    ap.add_argument("--days", type=int, default=1, help="최근 며칠치 Report 를 함께 담을지")
    ap.add_argument("--max-reports", type=int, default=0, help="담을 Report 최대 개수")
    ap.add_argument("--max-ini", type=int, default=0, help="Report 한 건당 담을 INI 최대 개수")
    ap.add_argument("--keep-images", action="store_true", help="Report 안의 로고 이미지도 그대로 담는다(용량 10배)")
    ap.add_argument("--list", action="store_true", help="--root 폴더 안에 무엇이 있는지만 보고 끝낸다(경로 찾기용)")
    args = ap.parse_args(argv)

    many = bool(args.all or args.roots)
    args.scan = args.scan or (80 if many else 120)              # 여러 대면 한 대당 가볍게
    args.max_reports = args.max_reports or (10 if many else 40)
    args.max_ini = args.max_ini or (4 if many else 8)

    out_base = Path(args.out) if args.out else Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    roots = [norm_root(r) for r in (args.roots or DEVICE_ROOTS)] if many else [norm_root(args.root)]
    for r in roots:                                             # ★ NAS 아래에는 절대 쓰지 않는다
        if os.path.normcase(os.path.abspath(out_base)).startswith(os.path.normcase(os.path.abspath(r))):
            say(f"[오류] 저장 위치가 NAS 안입니다: {out_base}. 다른 폴더를 --out 으로 지정하세요.")
            return 2

    if args.list:
        return list_folder(roots[0])
    if many:
        return sweep(roots, out_base, args)

    root = roots[0]
    folder = out_base / ("AOI_sample_" + time.strftime("%Y%m%d_%H%M"))
    say(f"1/3 훑는 중… {root}")
    facts = collect_one(root, folder, args)
    if not facts["ok"]:
        diagnose(root, args.report_dir or "Report")
        return 2
    say(f"    폴더: {facts['report_dir']} · {facts['scan_dir']} · Report {facts['reports']}개")
    say(f"2/3 담은 Report {facts['copied']}개 · INI {facts['ini_copied']}개")
    say("3/3 zip 으로 묶는 중…")
    zip_path = make_zip(out_base, folder)
    say("")
    say(f"완료했습니다.  보낼 파일: {zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB)")
    say(f"  풀린 폴더: {folder}")
    say("  먼저 요약.txt 를 열어 내용을 확인한 뒤 보내 주세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
