"""KLA AOI 사전 조사(2판) — **모든 폴더**를 나열하고, 최근 Lot 은 날짜 폴더에 걸쳐 **통째로** 읽어 zip 한 장으로 만든다.

1판(10/5)은 '최근 2일' 날짜 폴더만 봐서 Lot 이 잘려 보였다 — 실물(10/5 조사):
  · 날짜 폴더는 Wafer 날짜가 아니다. 10/4 20:45 에 시작한 Lot 25장이 통째로 `2026-10-05` 에 있다(4F-K1 INT988, K2 INT657 …).
    반대로 K1 T254.INT421 은 `2026-10-04` 14장 + `2026-10-05` 11장으로 갈려 있다.
  · 날짜 폴더 말고도 `old` · `BACK UP` · `RE_REVIEW` · `(BAD)2026-06-21` · 맨 위의 Lot 폴더(`TB500.INT522@6322`) 등이 있다.
  · FileTimestamp 가 두 가지다 — 네 자리 연도(폴더 시각 + 0~1분)와 두 자리 연도(몇 시간~하루 뒤, `.pass` 파일 수와 같다 = 검토 뒤 다시 씀).
그래서 2판은:
  1. **나열은 전부** — 맨 위의 모든 폴더(날짜 · 그 밖) → Lot → Wafer 폴더 이름까지(재귀 검색이 아니라 정해진 깊이까지 한 단계씩).
     날짜 아닌 폴더는 그 안이 Lot 인지 · 날짜 폴더인지 보고 한 단계 더 들어간다(최대 깊이 3).
  2. **읽기는 최근 Lot 통째로** — Wafer 폴더 시각이 최근 `--days` 일에 걸친 Lot 은 어느 날짜 폴더에 있든 모든 Wafer 를 읽는다.
     날짜 아닌 폴더의 Lot 은 첫·끝 Wafer 만 몇 개 읽는다(무엇인지 보려고).
  3. `.pass` · `.txt` 가 무엇인지 — 이름 · 크기 · 수정시각 · 앞 1KB.

★ NAS 는 **읽기만** 한다(scandir · open(..., "rb") 뿐). 쓰기는 `--out` 폴더(기본 바탕화면)뿐이다.
★ 표준 라이브러리만 쓴다 — 이 파일 하나만 있으면 돌아간다.

    python kla_survey.py                     # 아래 KLA_ROOTS 전 장비 · 전부 나열 · 최근 3일 Lot 읽기
    python kla_survey.py --days 1            # 읽기는 최근 1일 Lot 만(나열은 그대로 전부)
    python kla_survey.py --only K2 4F-K1     # 고른 장비만
    python kla_survey.py --list K:\\         # 그 드라이브 맨 위에 무엇이 있는지만 보고 끝낸다
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  훑을 장비 — 경로가 바뀌면 여기만 고치면 됩니다.
KLA_ROOTS = {
    "K1": "Z:\\", "K2": "G:\\", "K3": "W:\\", "K4": "N:\\", "K5": "U:\\", "K6": "T:\\",
    "4F-K1": "L:\\", "4F-K2": "K:\\",
}
# ══════════════════════════════════════════════════════════════════════════════

DATE_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
WAFER_DIR_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})_(\d+)$")
TS_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4}|\d{2})\s+(\d{2}):(\d{2}):(\d{2})")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\b(.*)$")
QUOTED = re.compile(r'"([^"]*)"')
IMAGE_EXT = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"}
HEAD_KEYS = ("FileVersion", "FileTimestamp", "InspectionStationID", "SampleType", "ResultTimestamp", "LotID",
             "SampleSize", "DeviceID", "SetupID", "StepID", "WaferID", "Slot", "InspectionTest",
             "LotStatus", "WaferStatus")
MAX_READ = 64 * 1024 * 1024        # 결과 파일 한 개를 읽을 최대 크기(그보다 크면 앞부분만)
SNIP = 1024                        # .pass · .txt 를 앞에서 몇 바이트 볼지
MAX_DEPTH = 3                      # 날짜 아닌 폴더 안으로 들어가는 최대 깊이


def say(msg: str = "") -> None:
    print(msg, flush=True)


def stamp(t: float | None) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)) if t else ""


def scan(path: str):
    """한 폴더를 한 번 나열한다 → [(이름, 폴더?, 크기, 수정시각)]. 실패하면 (None, 오류)."""
    try:
        out = []
        with os.scandir(path) as it:
            for e in it:
                try:
                    isdir = e.is_dir()
                    st = e.stat()
                    out.append((e.name, isdir, 0 if isdir else st.st_size, st.st_mtime))
                except OSError:
                    out.append((e.name, False, -1, 0.0))
        return out, None
    except OSError as ex:
        return None, f"{type(ex).__name__}: {ex}"


def parse_ts(s: str):
    """'10-05-2026 12:42:33' · '10-05-26 19:17:02'(두 자리 연도 — 검토 뒤 다시 쓴 파일, 10/5 조사) → (MM-DD, DD-MM 로 읽은 datetime)."""
    m = TS_RE.search(s or "")
    if not m:
        return None, None
    a, b, y, H, M, S = (int(x) for x in m.groups())
    if y < 100:
        y += 2000
    def mk(mo, d):
        try:
            return dt.datetime(y, mo, d, H, M, S)
        except ValueError:
            return None
    return mk(a, b), mk(b, a)


def parse_result(data: bytes) -> dict:
    """KLA 결과 파일(KLARF 비슷한 텍스트)을 읽어 머리말과 개수만 뽑는다."""
    text = data.decode("utf-8", errors="replace")
    lines = text.splitlines()
    head: dict[str, str] = {}
    keys = Counter()
    tiff, defects, summary, in_list = [], 0, [], False
    summary_spec, want_summary, want_spec = "", False, False
    for raw in lines:
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
        if want_spec:                                  # SummarySpec 의 열 이름은 다음 줄에 있다
            summary_spec += " " + s
            want_spec = not s.endswith(";")
            continue
        if want_summary:
            if re.match(r"^\d", s):
                summary.append(s.rstrip(";").strip())
                if s.endswith(";"):
                    want_summary = False
                continue
            want_summary = False
        m = KEY_RE.match(s)
        if not m:
            continue
        k, rest = m.group(1), m.group(2).strip()
        keys[k] += 1
        if k == "TiffFileName":
            tiff.append(rest.rstrip(";").strip())
        elif k == "DefectList":
            in_list = not rest.startswith(";")
        elif k == "SummarySpec":
            summary_spec, want_spec = rest, not rest.endswith(";")
        elif k == "SummaryList":
            want_summary = True
        elif k in HEAD_KEYS and k not in head:
            head[k] = rest.rstrip(";").strip()
    nd = None
    spec_cols = re.sub(r"^\d+\s*", "", summary_spec).replace(";", "").split()
    if summary and "NDEFECT" in spec_cols:
        try:
            nd = sum(int(r.split()[spec_cols.index("NDEFECT")]) for r in summary)
        except (ValueError, IndexError):
            nd = None
    q = lambda k: (QUOTED.findall(head.get(k, "")) or [head.get(k, "")])  # noqa: E731
    setup_full = head.get("SetupID", "")
    return {
        "head": head, "keys": dict(keys),
        "lot_id": q("LotID")[0], "device_id": q("DeviceID")[0], "setup_id": q("SetupID")[0],
        "setup_date": QUOTED.sub("", setup_full).strip(), "step_id": q("StepID")[0], "wafer_id": q("WaferID")[0],
        "slot": head.get("Slot", ""), "station": " ".join(QUOTED.findall(head.get("InspectionStationID", ""))),
        "file_ts": head.get("FileTimestamp", ""), "result_ts": head.get("ResultTimestamp", ""),
        "tiff_lines": len(tiff), "tiff_unique": len(set(tiff)), "defect_records": defects,
        "summary_spec": summary_spec, "summary": summary, "ndefect": nd,
        "lot_status": head.get("LotStatus", ""), "wafer_status": QUOTED.sub(lambda m: m.group(1), head.get("WaferStatus", "")),
        "eof": "EndOfFile" in keys, "lines": len(lines),
    }


def read_head(path: str, n: int = 64) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def wafer_time(name: str):
    m = WAFER_DIR_RE.match(name)
    if not m:
        return None, None
    y, mo, d, H, M, slot = (int(x) for x in m.groups())
    try:
        return dt.datetime(y, mo, d, H, M), slot
    except ValueError:
        return None, slot


def survey_wafer(tool: str, lot: dict, wafer: str) -> dict:
    """Wafer 폴더 하나: 나열 → 결과 파일 후보 확인 → 읽어서 파싱 + .pass/.txt 앞부분."""
    wpath = os.path.join(lot["path"], wafer)
    rec = {"tool": tool, "where": lot["where"], "lot_dir": lot["lot"], "wafer_dir": wafer}
    t, slot = wafer_time(wafer)
    rec["wafer_dir_rule"] = t is not None
    if t:
        rec["dir_time"] = t.strftime("%Y-%m-%d %H:%M")
        rec["dir_slot"] = str(slot)
    items, err = scan(wpath)
    if items is None:
        rec["error"] = err
        return rec
    exts, cands, side = Counter(), [], []
    for name, isdir, size, mtime in items:
        if isdir:
            exts["(폴더)"] += 1
            continue
        ext = os.path.splitext(name)[1].lower()
        exts[ext or "(없음)"] += 1
        if ext not in IMAGE_EXT:
            cands.append((name, size, mtime, ext))
    rec["files"] = len(items)
    rec["ext_counts"] = dict(exts)
    rec["jpg_files"] = sum(v for k, v in exts.items() if k in (".jpg", ".jpeg"))
    rec["others"] = [c[0] for c in cands][:20]
    results = []
    for c in cands:
        head = read_head(os.path.join(wpath, c[0]), SNIP if c[3] in (".pass", ".txt") else 64)
        if head.lstrip(b"\xef\xbb\xbf").startswith(b"FileVersion"):
            results.append(c)
        elif c[3] in (".pass", ".txt") or not c[3]:
            side.append({"name": c[0], "size": c[1], "mtime": stamp(c[2]), "head": head.decode("utf-8", "replace")[:SNIP]})
    rec["side_files"] = side[:5]
    rec["pass_files"] = sum(1 for c in cands if c[3] == ".pass")
    rec["pass_mtime"] = max((stamp(c[2]) for c in cands if c[3] == ".pass"), default="")
    rec["result_files"] = [c[0] for c in results]
    if not results:
        return rec
    name, size, mtime, ext = sorted(results, key=lambda c: c[2])[-1]       # 여러 개면 가장 늦은 것
    rec.update({"result_name": name, "result_ext": ext or "(없음)", "result_size": size, "result_mtime": stamp(mtime),
                "result_path": os.path.join(wpath, name)})
    try:
        with open(os.path.join(wpath, name), "rb") as f:
            data = f.read(MAX_READ)
        p = parse_result(data)
        rec.update({k: v for k, v in p.items() if k != "head"})
        rec["ts_year_digits"] = 4 if re.search(r"-\d{4}\s", rec.get("file_ts", "")) else (2 if rec.get("file_ts") else 0)
        rec["truncated"] = len(data) >= MAX_READ
    except OSError as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    return rec


# ── 1. 나열: 모든 폴더 ─────────────────────────────────────────────────────────
class Walker:
    """정해진 깊이까지 한 단계씩 나열한다. Lot = Wafer 이름 규칙에 맞는 하위 폴더가 있는 폴더."""

    def __init__(self, root: str, pool):
        self.root, self.pool = root, pool
        self.lots: list[dict] = []          # {where, kind(date|other), date_dir, lot, path, wafers, files, odd}
        self.others: list[str] = []         # 날짜 아닌 폴더에서 본 것(사람이 읽는 줄)
        self.errors: list[str] = []
        self.calls = 0

    def _scan_many(self, paths):
        self.calls += len(paths)
        return list(self.pool.map(scan, paths))

    def _lotify(self, where, kind, date_dir, lot, path, items):
        wafers = sorted(n for n, isd, *_ in items if isd and WAFER_DIR_RE.match(n))
        self.lots.append({"where": where, "kind": kind, "date_dir": date_dir, "lot": lot, "path": path, "wafers": wafers,
                          "odd_dirs": sorted(n for n, isd, *_ in items if isd and not WAFER_DIR_RE.match(n))[:20],
                          "files": [(n, s) for n, isd, s, _ in items if not isd][:30]})

    def date_dir(self, where: str, path: str, date_name: str):
        """날짜 아닌 폴더 안에서 만난 날짜 폴더(`BACK UP\\2026-08-01`) → 그 안의 Lot 폴더 전부 → Wafer 폴더 이름. 맨 위 날짜 폴더는 run() 이 한꺼번에."""
        items, err = scan(path)
        self.calls += 1
        if items is None:
            self.errors.append(f"{where}: {err}")
            return
        lots = sorted(n for n, isd, *_ in items if isd)
        for n, isd, s, _ in items:
            if not isd:
                self.others.append(f"{where}\\{n}  (날짜 폴더 안의 파일, {s} B)")
        for lot, (li, err) in zip(lots, self._scan_many([os.path.join(path, l) for l in lots])):
            if li is None:
                self.errors.append(f"{where}\\{lot}: {err}")
                continue
            self._lotify(f"{where}\\{lot}", "other", date_name, lot, os.path.join(path, lot), li)   # 날짜 아닌 폴더 안의 날짜 폴더

    def other_dir(self, where: str, path: str, items, depth: int):
        """날짜 아닌 폴더: 그 자체가 Lot 이면 Lot, 안에 날짜 폴더·Lot 이 있으면 들어간다(깊이 제한)."""
        if any(isd and WAFER_DIR_RE.match(n) for n, isd, *_ in items):
            self._lotify(where, "other", "", os.path.basename(path.rstrip("\\/")), path, items)
            return
        dirs = sorted(n for n, isd, *_ in items if isd)
        files = [n for n, isd, *_ in items if not isd]
        self.others.append(f"{where}  — 폴더 {len(dirs)}개 · 파일 {len(files)}개" + (f" (예: {', '.join(dirs[:6])})" if dirs else ""))
        if depth >= MAX_DEPTH or not dirs:
            return
        for d, (ci, err) in zip(dirs, self._scan_many([os.path.join(path, d) for d in dirs])):
            sub = f"{where}\\{d}"
            if ci is None:
                self.errors.append(f"{sub}: {err}")
            elif DATE_DIR_RE.match(d):
                self.date_dir(sub, os.path.join(path, d), d)
            else:
                self.other_dir(sub, os.path.join(path, d), ci, depth + 1)

    def run(self):
        top, err = scan(self.root)
        self.calls += 1
        if top is None:
            raise OSError(err)
        self.top = top
        dates = sorted(n for n, isd, *_ in top if isd and DATE_DIR_RE.match(n))
        others = sorted(n for n, isd, *_ in top if isd and not DATE_DIR_RE.match(n))
        # 날짜 폴더 전부 → 그 안의 Lot 폴더 전부를 두 번에 나눠 동시에 나열한다(결과는 이름 순서대로 모은다)
        lot_jobs = []
        for d, (di, err) in zip(dates, self._scan_many([os.path.join(self.root, d) for d in dates])):
            if di is None:
                self.errors.append(f"{d}: {err}")
                continue
            for n, isd, s, _ in di:
                if not isd:
                    self.others.append(f"{d}\\{n}  (날짜 폴더 안의 파일, {s} B)")
            lot_jobs += [(d, n) for n in sorted(n for n, isd, *_ in di if isd)]
        for (d, lot), (li, err) in zip(lot_jobs, self._scan_many([os.path.join(self.root, d, l) for d, l in lot_jobs])):
            if li is None:
                self.errors.append(f"{d}\\{lot}: {err}")
            else:
                self._lotify(f"{d}\\{lot}", "date", d, lot, os.path.join(self.root, d, lot), li)
        for o, (oi, err) in zip(others, self._scan_many([os.path.join(self.root, o) for o in others])):
            if oi is None:
                self.errors.append(f"{o}: {err}")
            else:
                self.other_dir(o, os.path.join(self.root, o), oi, 1)
        return dates, others


# ── 2. Lot 단위로 모으기 · 읽을 Lot 고르기 ─────────────────────────────────────
def lot_table(lots: list[dict]) -> dict:
    """Lot 이름 → 그 Lot 이 있는 곳 전부와 Wafer 폴더 시각 범위."""
    out: dict = {}
    for L in lots:
        T = out.setdefault(L["lot"], {"lot": L["lot"], "places": [], "wafers": 0, "first": None, "last": None, "slots": Counter(), "names": Counter()})
        T["places"].append(L["where"])
        T["wafers"] += len(L["wafers"])
        for w in L["wafers"]:
            t, slot = wafer_time(w)
            T["names"][w] += 1
            if slot is not None:
                T["slots"][slot] += 1
            if t:
                T["first"] = t if T["first"] is None or t < T["first"] else T["first"]
                T["last"] = t if T["last"] is None or t > T["last"] else T["last"]
    return out


def pick_lots(lots: list[dict], table: dict, days: int, today: dt.date, other_lots: int):
    """읽을 (Lot 장소, Wafer 이름) 목록. 날짜 폴더의 Lot 은 Wafer 시각이 최근 days 일에 걸치면 **모든 장소의 모든 Wafer**,
    날짜 아닌 폴더의 Lot 은 최근 것부터 other_lots 개까지 첫·끝 Wafer 만."""
    lo = dt.datetime.combine(today - dt.timedelta(days=days - 1), dt.time())
    hot = {n for n, T in table.items() if T["last"] and T["last"] >= lo
           and any(L["lot"] == n and L["kind"] == "date" for L in lots)}
    jobs = [(L, w) for L in lots if L["kind"] == "date" and L["lot"] in hot for w in L["wafers"]]
    other = sorted((L for L in lots if L["kind"] == "other" and L["wafers"]), key=lambda L: L["wafers"][-1], reverse=True)[:other_lots]
    for L in other:
        jobs += [(L, w) for w in sorted({L["wafers"][0], L["wafers"][-1]})]
    return jobs, hot


# ── 3. 요약 ────────────────────────────────────────────────────────────────────
def summarize(dates, others_top, W: Walker, table: dict, recs: list[dict], hot: set) -> dict:
    s: dict = {}
    date_lots = [L for L in W.lots if L["kind"] == "date"]
    other_lots = [L for L in W.lots if L["kind"] == "other"]
    s["inventory"] = {"date_dirs": len(dates), "date_range": [dates[0], dates[-1]] if dates else [],
                      "other_top_dirs": others_top, "top_files": [n for n, isd, *_ in W.top if not isd][:30],
                      "lot_folders_in_date_dirs": len(date_lots), "lot_folders_elsewhere": len(other_lots),
                      "wafer_dirs_in_date_dirs": sum(len(L["wafers"]) for L in date_lots),
                      "wafer_dirs_elsewhere": sum(len(L["wafers"]) for L in other_lots),
                      "distinct_lots": len(table), "listing_calls": W.calls, "errors": W.errors[:20]}
    s["elsewhere"] = sorted({L["where"].split("\\")[0] for L in other_lots})
    s["elsewhere_lots"] = [f"{L['where']} ({len(L['wafers'])}장)" for L in other_lots][:40]
    s["elsewhere_also_in_date_dirs"] = sorted({L["lot"] for L in other_lots if any(D["lot"] == L["lot"] for D in date_lots)})[:40]
    s["lot_dir_odd_subdirs"] = [f"{L['where']}: {', '.join(L['odd_dirs'][:5])}" for L in W.lots if L["odd_dirs"]][:20]
    s["lot_dir_files"] = dict(Counter(os.path.splitext(n)[1].lower() or "(없음)" for L in W.lots for n, _ in L["files"]))
    s["date_dirs_without_wafer_rule"] = sum(1 for L in date_lots if not L["wafers"])
    # 날짜 폴더 이름과 그 Lot 의 Wafer 시각 — 날짜 폴더는 무엇의 날짜인가
    rel = Counter()
    for L in date_lots:
        ts = [t for t in (wafer_time(w)[0] for w in L["wafers"]) if t]
        if not ts:
            rel["Wafer 없음"] += 1
            continue
        d = L["date_dir"]
        f, l = min(ts).date().isoformat(), max(ts).date().isoformat()
        rel["첫·끝 Wafer 모두 그 날짜" if f == l == d else "끝 Wafer 날짜 = 폴더(시작은 전날)" if l == d else
            "첫 Wafer 날짜 = 폴더(끝은 다음날)" if f == d else "둘 다 다른 날짜"] += 1
    s["date_dir_vs_wafer_dates"] = dict(rel)
    split = [T for T in table.values() if sum(1 for p in T["places"] if "\\" in p and DATE_DIR_RE.match(p.split("\\")[0])) > 1]
    s["lots_split_over_date_dirs"] = len(split)
    s["lots_split_examples"] = [f"{T['lot']}: {', '.join(T['places'][:4])}" for T in split][:15]
    dup_names = [(T["lot"], w) for T in table.values() for w, n in T["names"].items() if n > 1]
    s["same_wafer_dir_in_two_places"] = len(dup_names)
    s["same_wafer_dir_examples"] = [f"{l} / {w}" for l, w in dup_names][:10]
    s["slot_repeated_in_lot"] = sum(1 for T in table.values() if any(v > 1 for v in T["slots"].values()))
    # 읽은 Wafer
    got = [r for r in recs if r.get("result_name")]
    s["parsed"] = {"lots": len(hot), "wafer_dirs": len(recs), "with_result": len(got),
                   "no_result": [f"{r['where']}\\{r['wafer_dir']}" for r in recs if not r.get("result_name")][:20],
                   "multi_result": sum(1 for r in recs if len(r.get("result_files", [])) > 1),
                   "result_ext": dict(Counter(r["result_ext"] for r in got)), "no_eof": sum(1 for r in got if not r.get("eof")),
                   "errors": [r.get("error") for r in recs if r.get("error")][:10]}
    y = Counter(r.get("ts_year_digits") for r in got)
    s["file_ts_year_digits"] = {"4자리": y.get(4, 0), "2자리": y.get(2, 0)}
    s["two_digit_vs_pass"] = {"2자리 연도이면서 .pass 있음": sum(1 for r in got if r.get("ts_year_digits") == 2 and r.get("pass_files")),
                              "2자리 연도인데 .pass 없음": sum(1 for r in got if r.get("ts_year_digits") == 2 and not r.get("pass_files")),
                              "4자리 연도인데 .pass 있음": sum(1 for r in got if r.get("ts_year_digits") == 4 and r.get("pass_files"))}
    dl = defaultdict(list)
    for r in got:
        a, _ = parse_ts(r.get("file_ts", ""))
        if a and r.get("dir_time"):
            d = dt.datetime.strptime(r["dir_time"], "%Y-%m-%d %H:%M")
            dl[r.get("ts_year_digits")].append(round((a - d).total_seconds() / 60, 1))
        mt = r.get("result_mtime")
        if mt and r.get("dir_time"):
            dl["mtime"].append(round((dt.datetime.strptime(mt, "%Y-%m-%d %H:%M:%S") - dt.datetime.strptime(r["dir_time"], "%Y-%m-%d %H:%M")).total_seconds() / 60, 1))
    q = lambda xs: (min(xs), sorted(xs)[len(xs) // 2], max(xs)) if xs else None  # noqa: E731
    s["minutes_after_wafer_dir_time"] = {"FileTimestamp(4자리)": q(dl[4]), "FileTimestamp(2자리)": q(dl[2]), "결과 파일 수정시각": q(dl["mtime"])}
    # Lot 시간: ResultTimestamp(= 첫 Wafer 폴더 시각?) ~ 마지막 Wafer 폴더 시각 + 장당 간격
    lots_rows = []
    by = defaultdict(list)
    for r in got:
        if r["where"].split("\\")[0] and DATE_DIR_RE.match(r["where"].split("\\")[0]):
            by[r["lot_dir"]].append(r)
    first_vs_rts = []
    for lot, rs in sorted(by.items()):
        ts = sorted(dt.datetime.strptime(r["dir_time"], "%Y-%m-%d %H:%M") for r in rs if r.get("dir_time"))
        rts = sorted({x for x in (parse_ts(r.get("result_ts", ""))[0] for r in rs) if x})
        gaps = sorted((b - a).total_seconds() / 60 for a, b in zip(ts, ts[1:]))
        if ts and rts:
            first_vs_rts.append(round((ts[0] - rts[0]).total_seconds() / 60, 1))
        lots_rows.append({"lot": lot, "wafers": len(rs), "places": table[lot]["places"] if lot in table else [],
                          "first_wafer_dir": ts[0].isoformat(" ") if ts else "", "last_wafer_dir": ts[-1].isoformat(" ") if ts else "",
                          "gap_median_min": gaps[len(gaps) // 2] if gaps else None, "gap_max_min": gaps[-1] if gaps else None,
                          "result_ts": [x.isoformat(" ") for x in rts][:4],
                          "setup_id": sorted({r.get("setup_id", "") for r in rs}), "slots": sorted(int(r["dir_slot"]) for r in rs if r.get("dir_slot")),
                          "lot_status": sorted({r.get("lot_status", "") for r in rs}),
                          "defects": sum(int(r.get("defect_records") or 0) for r in rs)})
    s["first_wafer_dir_minus_result_ts_min"] = q(first_vs_rts)
    s["result_ts_values_per_lot"] = dict(Counter(len(L["result_ts"]) for L in lots_rows))
    s["gap_median_per_lot_min"] = q([L["gap_median_min"] for L in lots_rows if L["gap_median_min"] is not None])
    s["lot_table"] = lots_rows
    s["defect_count_agree"] = {"jpg이름줄=레코드": sum(1 for r in got if r.get("tiff_lines") == r.get("defect_records")),
                               "레코드=NDEFECT": sum(1 for r in got if r.get("ndefect") is not None and r.get("defect_records") == r.get("ndefect")),
                               "전체": len(got)}
    s["setup_ids"] = Counter(r.get("setup_id", "") for r in got).most_common()
    s["lot_status"] = Counter(r.get("lot_status", "") for r in got).most_common(10)
    s["wafer_status_samples"] = Counter(r.get("wafer_status", "") for r in got).most_common(8)
    s["side_file_samples"] = [dict(f, wafer=f"{r['where']}\\{r['wafer_dir']}") for r in recs for f in r.get("side_files", [])][:12]
    s["keys_seen"] = dict(Counter(k for r in got for k in r.get("keys", {})))
    return s


def pick_copies(recs: list[dict], n: int) -> list[dict]:
    """담을 결과 파일: 2자리·4자리 연도 각각, 날짜 아닌 폴더, 확장자 .001 아닌 것, 그다음 Lot 마다 첫·끝."""
    got = [r for r in recs if r.get("result_name")]
    out, seen = [], set()
    def add(r):
        if r["result_path"] not in seen and len(out) < n:
            seen.add(r["result_path"])
            out.append(r)
    for want in (2, 4):
        for r in got:
            if r.get("ts_year_digits") == want:
                add(r)
                break
    for r in got:
        if r["result_ext"] != ".001" or not r.get("eof") or not DATE_DIR_RE.match(r["where"].split("\\")[0]):
            add(r)
    by = defaultdict(list)
    for r in got:
        by[r["lot_dir"]].append(r)
    for rs in by.values():
        rs = sorted(rs, key=lambda r: r["wafer_dir"])
        add(rs[0])
        add(rs[-1])
    return out


def run_tool(tool: str, root: str, folder: Path, args, pool, today) -> dict:
    t0 = time.time()
    W = Walker(root, pool)
    try:
        dates, others = W.run()
    except OSError as ex:
        return {"tool": tool, "root": root, "ok": False, "error": str(ex)}
    t_list = time.time() - t0
    table = lot_table(W.lots)
    jobs, hot = pick_lots(W.lots, table, args.days, today, args.other_lots)
    if args.max_wafers and len(jobs) > args.max_wafers:
        jobs = jobs[-args.max_wafers:]
    say(f"      나열 {t_list:.0f}초 — 날짜 폴더 {len(dates)} · 그 밖 {len(others)} · Lot 폴더 {len(W.lots)} · Wafer 폴더 {sum(len(L['wafers']) for L in W.lots)}")
    say(f"      최근 {args.days}일에 걸친 Lot {len(hot)}개(통째로) + 날짜 아닌 폴더 표본 → Wafer {len(jobs)}개 읽는 중…")
    recs = list(pool.map(lambda j: survey_wafer(tool, j[0], j[1]), jobs))
    s = summarize(dates, others, W, table, recs, hot)
    tf = folder / tool
    (tf / "samples").mkdir(parents=True, exist_ok=True)
    for r in pick_copies(recs, args.copy):
        dst = tf / "samples" / (r["where"].replace("\\", "__") + "__" + r["wafer_dir"] + "__" + r["result_name"])
        try:
            shutil.copyfile(r["result_path"], dst)                        # NAS 에서 읽어 로컬에만 쓴다
        except OSError as ex:
            s.setdefault("copy_errors", []).append(f"{r['result_name']}: {ex}")
    cols = ["tool", "where", "lot_dir", "wafer_dir", "dir_time", "dir_slot", "files", "jpg_files", "pass_files", "pass_mtime",
            "result_name", "result_ext", "result_size", "result_mtime", "file_ts", "ts_year_digits", "result_ts", "lot_id",
            "device_id", "setup_id", "setup_date", "step_id", "wafer_id", "slot", "station", "tiff_lines", "tiff_unique",
            "defect_records", "ndefect", "lot_status", "wafer_status", "eof", "error"]
    with open(tf / "wafers.tsv", "w", encoding="utf-8-sig") as f:
        f.write("\t".join(cols) + "\n")
        for r in recs:
            f.write("\t".join(str(r.get(c, "")).replace("\t", " ") for c in cols) + "\n")
    with open(tf / "lots_all.tsv", "w", encoding="utf-8-sig") as f:                # 나열한 Lot 폴더 전부(읽지 않은 것 포함)
        f.write("where\tkind\tdate_dir\tlot\twafer_dirs\tfirst_wafer_dir\tlast_wafer_dir\tslots\tother_subdirs\tfiles\n")
        for L in W.lots:
            ts = [w for w in L["wafers"]]
            f.write("\t".join(str(x) for x in (L["where"], L["kind"], L["date_dir"], L["lot"], len(L["wafers"]),
                                                ts[0] if ts else "", ts[-1] if ts else "",
                                                ",".join(str(wafer_time(w)[1]) for w in ts), "|".join(L["odd_dirs"]),
                                                "|".join(n for n, _ in L["files"]))) + "\n")
    (tf / "그밖의_폴더.txt").write_text("\n".join(W.others + ["", "■ 나열 오류"] + W.errors), encoding="utf-8")
    facts = {"tool": tool, "root": root, "ok": True, "seconds": round(time.time() - t0, 1), "listing_seconds": round(t_list, 1), **s}
    (tf / "사실.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return facts


def report_lines(f: dict) -> list[str]:
    if not f.get("ok"):
        return [f"■ {f['tool']} ({f['root']}) — 읽지 못함: {f.get('error')}", ""]
    I, P, dc = f["inventory"], f["parsed"], f["defect_count_agree"]
    return [f"■ {f['tool']} ({f['root']})  전체 {f['seconds']}초 · 그중 나열 {f['listing_seconds']}초(폴더 {I['listing_calls']}번)",
            f"   날짜 폴더 {I['date_dirs']}개 {' ~ '.join(I['date_range'])} · Lot 폴더 {I['lot_folders_in_date_dirs']} · Wafer 폴더 {I['wafer_dirs_in_date_dirs']}",
            f"   날짜 아닌 맨 위 폴더: {', '.join(I['other_top_dirs']) or '없음'}",
            f"   그 안에서 찾은 Lot 폴더 {I['lot_folders_elsewhere']}개 · Wafer {I['wafer_dirs_elsewhere']}개 (위치: {', '.join(f['elsewhere'][:8]) or '-'})",
            f"   그중 날짜 폴더에도 같은 Lot 이 있는 것: {len(f['elsewhere_also_in_date_dirs'])}개 {f['elsewhere_also_in_date_dirs'][:4]}",
            f"   날짜 폴더 ↔ Wafer 날짜: {f['date_dir_vs_wafer_dates']}",
            f"   여러 날짜 폴더에 갈린 Lot {f['lots_split_over_date_dirs']}개 {f['lots_split_examples'][:2]}",
            f"   같은 Wafer 폴더 이름이 두 곳에: {f['same_wafer_dir_in_two_places']} {f['same_wafer_dir_examples'][:2]} · Slot 이 겹친 Lot {f['slot_repeated_in_lot']}",
            f"   읽은 것: 최근 Lot {P['lots']}개 통째로 · Wafer 폴더 {P['wafer_dirs']} · 결과 파일 {P['with_result']} · 없음 {len(P['no_result'])} · 확장자 {P['result_ext']}",
            f"   FileTimestamp 연도: {f['file_ts_year_digits']} · {f['two_digit_vs_pass']}",
            f"   Wafer 폴더 시각 뒤 몇 분(최소/중앙/최대): {f['minutes_after_wafer_dir_time']}",
            f"   첫 Wafer 폴더 시각 − ResultTimestamp(분): {f['first_wafer_dir_minus_result_ts_min']} · Lot 당 ResultTimestamp 값 수: {f['result_ts_values_per_lot']}",
            f"   Lot 안 Wafer 간격 중앙값(분) 최소/중앙/최대: {f['gap_median_per_lot_min']}",
            f"   Defect: {dc}",
            f"   SetupID {len(f['setup_ids'])}종: " + ", ".join(f"{k}({v})" for k, v in f["setup_ids"][:6]),
            ""]


def list_top(root: str) -> int:
    items, err = scan(root)
    if items is None:
        say(f"읽지 못함: {err}")
        return 2
    for n, isdir, size, mtime in sorted(items)[:300]:
        say(f"{'[폴더]' if isdir else '      '} {stamp(mtime)}  {n}")
    say(f"(항목 {len(items)}개)")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="KLA AOI 사전 조사 2판(NAS 읽기 전용) — 전부 나열 · 최근 Lot 통째로 읽기")
    ap.add_argument("--days", type=int, default=3, help="Wafer 시각이 최근 며칠에 걸친 Lot 을 통째로 읽을지(기본 3, 나열은 늘 전부)")
    ap.add_argument("--only", nargs="+", help="고른 장비만 (예: K2 4F-K1)")
    ap.add_argument("--out", default="", help="저장 위치 (기본 바탕화면)")
    ap.add_argument("--workers", type=int, default=8, help="동시에 읽을 개수(기본 8)")
    ap.add_argument("--copy", type=int, default=10, help="장비마다 원본 결과 파일을 몇 개 담을지(기본 10)")
    ap.add_argument("--other-lots", type=int, default=15, help="날짜 아닌 폴더의 Lot 을 몇 개까지 첫·끝 Wafer 로 읽어 볼지(기본 15)")
    ap.add_argument("--max-wafers", type=int, default=5000, help="장비마다 읽을 Wafer 폴더 상한(0 = 무제한)")
    ap.add_argument("--today", default="", help="기준 날짜 YYYY-MM-DD (기본 오늘)")
    ap.add_argument("--list", metavar="ROOT", help="그 폴더 맨 위만 나열하고 끝낸다(경로 찾기용)")
    args = ap.parse_args(argv)
    if args.list:
        return list_top(args.list)

    roots = {k: v for k, v in KLA_ROOTS.items() if not args.only or k in args.only}
    out_base = Path(args.out) if args.out else Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    for r in roots.values():                                         # ★ NAS 아래에는 절대 쓰지 않는다
        if os.path.normcase(os.path.abspath(out_base)).startswith(os.path.normcase(os.path.abspath(r))):
            say(f"[오류] 저장 위치가 NAS 안입니다: {out_base}. 다른 폴더를 --out 으로 지정하세요.")
            return 2
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    folder = out_base / ("KLA_survey2_" + time.strftime("%Y%m%d_%H%M"))
    folder.mkdir(parents=True, exist_ok=True)

    facts = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for n, (tool, root) in enumerate(roots.items(), 1):
            say(f"[{n}/{len(roots)}] {tool}  {root}")
            try:
                f = run_tool(tool, root, folder, args, pool, today)
            except Exception as ex:                                   # noqa: BLE001 - 한 대 때문에 멈추지 않게
                f = {"tool": tool, "root": root, "ok": False, "error": f"{type(ex).__name__}: {ex}"}
            facts.append(f)
            say(f"      {'완료 %s초' % f['seconds'] if f.get('ok') else '건너뜀 — ' + str(f.get('error'))}")

    lines = [f"KLA 사전 조사 2판 · {stamp(time.time())} · 나열 전부 · 최근 {args.days}일 Lot 통째로 읽기", ""]
    for f in facts:
        lines += report_lines(f)
    by_setup = defaultdict(dict)
    for f in facts:
        for k, v in f.get("setup_ids", []):
            by_setup[k][f["tool"]] = v
    lines += ["■ SetupID × 장비 (읽은 Wafer 수)"]
    for k in sorted(by_setup, key=lambda k: -sum(by_setup[k].values())):
        lines.append(f"   {k}   " + " · ".join(f"{t}:{v}" for t, v in sorted(by_setup[k].items())))
    lines += ["", "※ NAS 는 읽기만 했습니다(나열·읽기·로컬로 복사). 원본은 아무것도 바꾸지 않았습니다.",
              "※ 장비 폴더마다 lots_all.tsv(나열한 Lot 폴더 전부) · wafers.tsv(읽은 Wafer) · 그밖의_폴더.txt · 사실.json · samples\\ 가 있습니다."]
    (folder / "요약.txt").write_text("\n".join(lines), encoding="utf-8")
    (folder / "요약.json").write_text(json.dumps([{k: v for k, v in f.items() if k != "lot_table"} for f in facts],
                                                 ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    zip_path = out_base / (folder.name + ".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out_base))
    say("")
    say(f"완료했습니다.  보낼 파일: {zip_path}  ({zip_path.stat().st_size / 1e6:.1f} MB)")
    say(f"  풀린 폴더: {folder}  — 먼저 요약.txt 를 열어 확인한 뒤 보내 주세요.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
