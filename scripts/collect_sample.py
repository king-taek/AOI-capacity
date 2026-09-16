"""AOI-25 샘플 모으기 — 개발에 필요한 실물 Report/INI 를 한 폴더에 모아 zip 한 장으로 만든다.

무엇을 모으는가
  1. Report 폴더의 **전체 파일 목록**(이름·크기·수정시각) — Lot 표기 규칙(RE · SRD · DIA · 3D …)을 여기서 본다.
  2. 고른 Report 원본 `.htm` — Scan error 가 있는 것, 그 Lot 의 앞뒤(재스캔 후보), 표기별 대표, 최근 하루치.
  3. 고른 Report 의 **정확 경로** Lot 폴더에 있는 `WaferInfo.ini` 와 그 폴더 목록(수정시각 포함).
     INI 가 재스캔 때 덮어써지는지, 재스캔용 폴더가 따로 생기는지를 이 목록으로 본다.

★ NAS 는 **읽기만** 한다. NAS 아래에는 파일을 만들지도 바꾸지도 지우지도 않는다. 쓰기는 `--out` 폴더(기본 바탕화면)뿐이다.
★ Scanresult 를 재귀 검색하지 않는다. Report 파일명에서 계산한 Lot 폴더 **하나만** 나열한다.
★ 표준 라이브러리만 쓴다 — 앱이 설치돼 있지 않아도 이 파일 하나만 있으면 돌아간다.

    python collect_sample.py                          # Y:\\AOI-25 → 바탕화면에 zip
    python collect_sample.py --root Y:\\AOI-25 --days 2
    python collect_sample.py --scan 200               # 최근 Report 200개까지 훑어보기(기본 120)
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

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
    job, setup = info.get("job", ""), info.get("setup", "")
    if not job:
        return 0                                   # Job/Setup 을 못 읽은 Report 는 경로를 만들 수 없다
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


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="AOI 샘플 모으기(NAS 읽기 전용)")
    ap.add_argument("--root", default=DEFAULT_ROOT, help=r"장비 폴더 (기본 Y:\AOI-25)")
    ap.add_argument("--out", default="", help="저장 위치 (기본 바탕화면)")
    ap.add_argument("--report-dir", default="", help="비우면 Report / Reports 를 자동으로 찾는다")
    ap.add_argument("--scan-dir", default="", help="비우면 Scanresult 를 자동으로 찾는다")
    ap.add_argument("--scan", type=int, default=120, help="상태를 보려고 열어 볼 최근 Report 개수")
    ap.add_argument("--days", type=int, default=1, help="최근 며칠치 Report 를 함께 담을지")
    ap.add_argument("--max-reports", type=int, default=40, help="담을 Report 최대 개수")
    ap.add_argument("--max-ini", type=int, default=8, help="Report 한 건당 담을 INI 최대 개수")
    ap.add_argument("--list", action="store_true", help="--root 폴더 안에 무엇이 있는지만 보고 끝낸다(경로 찾기용)")
    args = ap.parse_args(argv)

    root = norm_root(args.root)
    if args.list:
        return list_folder(root)
    rep_name = find_subdir(root, args.report_dir, REPORT_DIR_NAMES)
    scan_name = find_subdir(root, args.scan_dir, SCAN_DIR_NAMES) or (args.scan_dir or "Scanresult")
    if not rep_name:
        diagnose(root, args.report_dir or "Report")
        return 2
    rep_dir, scan_root = root / rep_name, root / scan_name
    say(f"    폴더: {rep_name} · {scan_name}")

    out_base = Path(args.out) if args.out else Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    # ★ NAS 아래에는 절대 쓰지 않는다
    if os.path.normcase(os.path.abspath(out_base)).startswith(os.path.normcase(os.path.abspath(root))):
        say(f"[오류] 저장 위치가 NAS 안입니다: {out_base}. 다른 폴더를 --out 으로 지정하세요.")
        return 2
    name = "AOI_sample_" + time.strftime("%Y%m%d_%H%M")
    out_dir = out_base / name
    (out_dir / "Report").mkdir(parents=True, exist_ok=True)

    say(f"1/4 Report 폴더 목록 읽는 중… {rep_dir}")
    infos = scan_reports(rep_dir, args.scan)
    if not infos:
        say("[오류] Report 폴더에 .htm 파일이 없습니다.")
        return 2
    say(f"    Report {len(infos)}개 · 최근 {min(args.scan, len(infos))}개를 열어 상태를 봅니다")

    listing = [f"# {rep_dir}", f"# 전체 {len(infos)}개 · 만든 시각 {stamp(time.time())}", "",
               "수정시각\t크기\t파일명"]
    listing += [f"{stamp(i['mtime'])}\t{i['size']}\t{i['name']}" for i in infos]
    (out_dir / "report_목록.txt").write_text("\n".join(listing), encoding="utf-8")

    say("2/4 보낼 Report 고르는 중…")
    chosen, why = pick_samples(infos, args.days, args.max_reports)
    for i in chosen:
        try:
            shutil.copy2(i["path"], out_dir / "Report" / i["name"])
        except OSError as ex:
            why[i["name"]] += f" (복사 실패: {ex})"

    say("3/4 WaferInfo.ini 와 Lot 폴더 목록 모으는 중…")
    scan_lines = [f"# {scan_root}", "# 고른 Report 의 Lot 폴더만 정확 경로로 한 번씩 나열했습니다(재귀 검색 없음).",
                  "# INI 수정시각이 Report 시각보다 늦으면 재스캔 때 덮어써졌을 수 있습니다."]
    seen_lots = set()
    n_ini = sum(copy_ini_for(i, scan_root, out_dir, args.max_ini, scan_lines, seen_lots) for i in chosen)
    (out_dir / "scan_폴더구조.txt").write_text("\n".join(scan_lines), encoding="utf-8")

    suffixes = Counter(lot_parts(i["lot"])[1] or "(접미사 없음)" for i in infos if i["matched"])
    flags = Counter(f for i in infos if i["read"] for f in (i["flags"] or ["(오류 표시 없음)"]))
    summary = [
        f"AOI 샘플 · {stamp(time.time())}",
        f"대상: {root}",
        f"Report 전체 {len(infos)}개 (기간 {stamp(infos[-1]['mtime'])} ~ {stamp(infos[0]['mtime'])})",
        f"열어 본 Report {sum(1 for i in infos if i['read'])}개 · 담은 Report {len(chosen)}개 · 담은 INI {n_ini}개",
        "",
        "■ Lot 접미사 (RE · SRD · DIA · 3D 표기 확인용)",
        *[f"   {k:<16} {v}건" for k, v in suffixes.most_common()],
        "",
        "■ 열어 본 Report 의 상태 표시",
        *[f"   {k:<16} {v}건" for k, v in flags.most_common()],
        "",
        "■ Job/Setup (Scanresult 경로의 출처)",
        *[f"   {k:<40} {v}건" for k, v in Counter(f"{i.get('job','')}/{i.get('setup','')}"
                                                  for i in infos if i.get("read")).most_common(10)],
        "",
        "■ 담은 Report 와 고른 이유",
        *[f"   {i['name']}\n      → {why[i['name']]}" for i in chosen],
        "",
        "※ 이 폴더에는 NAS 에서 '복사'만 했습니다. NAS 원본은 읽기만 했고 아무것도 바꾸지 않았습니다.",
    ]
    (out_dir / "요약.txt").write_text("\n".join(summary), encoding="utf-8")

    say("4/4 zip 으로 묶는 중…")
    zip_path = out_base / (name + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out_dir.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out_base))
    size_mb = zip_path.stat().st_size / 1e6
    say("")
    say("완료했습니다.")
    say(f"  보낼 파일: {zip_path}  ({size_mb:.1f} MB)")
    say(f"  풀린 폴더: {out_dir}")
    say("  먼저 요약.txt 를 열어 내용을 확인한 뒤 보내 주세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
