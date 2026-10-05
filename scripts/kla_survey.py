"""KLA AOI 사전 조사 — 결과 파일(`*.001` · 확장자 없음) 구성을 장비별로 훑어 zip 한 장으로 만든다.

KLA 는 Camtek 과 로그 구성이 다르다(BatchReport 가 없다). 수집기를 만들기 전에 실물에서 확인할 것:
  1. 드라이브 맨 위 구성 — 날짜 폴더(`YYYY-MM-DD`)만 있는지, 다른 폴더가 섞였는지.
  2. 날짜 폴더 → Lot 폴더(`TB500.INT764@6322`) → Wafer 폴더(`2026-10-05-12-42_6`) 이름 규칙이 늘 맞는지.
  3. Wafer 폴더 안의 결과 파일 — 확장자(.001 · 없음 · 그 밖), 한 폴더에 몇 개인지, jpg 는 몇 장인지.
  4. 결과 파일 머리말 — FileTimestamp · ResultTimestamp · LotID · DeviceID · SetupID · StepID · WaferID · Slot.
     · 시각 표기가 MM-DD-YYYY 인지(폴더 날짜와 대조), ResultTimestamp 가 Lot 안에서 같은 값인지(= Lot 시작?).
     · Wafer 폴더 이름의 시:분과 FileTimestamp 가 같은지.
  5. Defect 개수 세 가지 — TiffFileName(jpg 이름) 줄 수 · DefectList 레코드 수 · SummaryList 의 NDEFECT.
  6. 같은 Lot 이 여러 날짜 폴더에 걸치는지, 같은 WaferID 가 여러 번 나오는지(재스캔).
  7. SetupID(레시피) 목록과 건수 — 레시피 묶기·레시피별 현황의 재료.

★ NAS 는 **읽기만** 한다(scandir · open(..., "rb") 뿐). 쓰기는 `--out` 폴더(기본 바탕화면)뿐이다.
★ 재귀 검색을 하지 않는다 — 날짜 폴더 → Lot 폴더 → Wafer 폴더를 한 단계씩만 나열한다.
★ 표준 라이브러리만 쓴다 — 이 파일 하나만 있으면 돌아간다.

    python kla_survey.py                     # 아래 KLA_ROOTS 전 장비, 최근 2일
    python kla_survey.py --days 1            # 최근 1일만(빠르게)
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
TS_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})\s+(\d{2}):(\d{2}):(\d{2})")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)\b(.*)$")
QUOTED = re.compile(r'"([^"]*)"')
IMAGE_EXT = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp"}
HEAD_KEYS = ("FileVersion", "FileTimestamp", "InspectionStationID", "SampleType", "ResultTimestamp", "LotID",
             "SampleSize", "DeviceID", "SetupID", "StepID", "WaferID", "Slot", "InspectionTest",
             "LotStatus", "WaferStatus")
MAX_READ = 64 * 1024 * 1024        # 결과 파일 한 개를 읽을 최대 크기(그보다 크면 앞부분만)


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
    """'10-05-2026 12:42:33' → (MM-DD 로 읽은 datetime, DD-MM 로 읽은 datetime). 못 읽으면 None."""
    m = TS_RE.search(s or "")
    if not m:
        return None, None
    a, b, y, H, M, S = (int(x) for x in m.groups())
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


def survey_wafer(tool: str, date_dir: str, lot: str, wafer: str, wpath: str) -> dict:
    """Wafer 폴더 하나: 나열 → 결과 파일 후보 확인 → 읽어서 파싱."""
    rec = {"tool": tool, "date_dir": date_dir, "lot_dir": lot, "wafer_dir": wafer}
    m = WAFER_DIR_RE.match(wafer)
    rec["wafer_dir_rule"] = bool(m)
    if m:
        rec["dir_time"] = "%s-%s-%s %s:%s" % m.groups()[:5]
        rec["dir_slot"] = m.group(6)
    items, err = scan(wpath)
    if items is None:
        rec["error"] = err
        return rec
    exts = Counter()
    cands = []
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
    results = [c for c in cands if read_head(os.path.join(wpath, c[0])).lstrip(b"\xef\xbb\xbf").startswith(b"FileVersion")]
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
        rec.update({k: v for k, v in p.items() if k not in ("head",)})
        rec["truncated"] = len(data) >= MAX_READ
    except OSError as ex:
        rec["error"] = f"{type(ex).__name__}: {ex}"
    return rec


def list_lots(tool: str, root: str, days: int, today: dt.date):
    """맨 위 → 날짜 폴더 → Lot 폴더 → Wafer 폴더 이름까지 나열(한 단계씩). 돌려주는 값: 사실, Wafer 작업 목록."""
    facts: dict = {"tool": tool, "root": root}
    top, err = scan(root)
    if top is None:
        facts["error"] = err
        return facts, []
    dates = sorted((n for n, isdir, *_ in top if isdir and DATE_DIR_RE.match(n)), reverse=True)
    facts["top_total"] = len(top)
    facts["top_date_dirs"] = len(dates)
    facts["top_other"] = [("[폴더] " if isdir else "") + n for n, isdir, *_ in top
                          if not (isdir and DATE_DIR_RE.match(n))][:60]
    facts["date_range"] = [dates[-1], dates[0]] if dates else []
    lo = (today - dt.timedelta(days=days - 1)).isoformat()
    pick = [d for d in dates if lo <= d <= today.isoformat()] or dates[:1]
    facts["dates_picked"] = pick
    jobs, lots = [], []
    for d in pick:
        items, err = scan(os.path.join(root, d))
        if items is None:
            lots.append({"date_dir": d, "error": err})
            continue
        for lot, isdir, size, mtime in sorted(items):
            if not isdir:
                lots.append({"date_dir": d, "file_in_date_dir": lot, "size": size})
                continue
            lp = os.path.join(root, d, lot)
            witems, err = scan(lp)
            if witems is None:
                lots.append({"date_dir": d, "lot_dir": lot, "error": err})
                continue
            wdirs = sorted(n for n, isd, *_ in witems if isd)
            lots.append({"date_dir": d, "lot_dir": lot, "mtime": stamp(mtime), "wafer_dirs": len(wdirs),
                         "wafer_dir_names": wdirs,
                         "files_in_lot_dir": [(n, s) for n, isd, s, _ in witems if not isd][:30]})
            jobs += [(tool, d, lot, w, os.path.join(lp, w)) for w in wdirs]
    facts["lots"] = lots
    return facts, jobs


def summarize(facts: dict, recs: list[dict]) -> dict:
    """장비 한 대의 점검 사실."""
    got = [r for r in recs if r.get("result_name")]
    s: dict = {"wafer_dirs": len(recs), "with_result": len(got),
               "no_result": [f"{r['date_dir']}\\{r['lot_dir']}\\{r['wafer_dir']}" for r in recs if not r.get("result_name")][:30],
               "multi_result": sum(1 for r in recs if len(r.get("result_files", [])) > 1),
               "wafer_dir_rule_miss": [r["wafer_dir"] for r in recs if not r["wafer_dir_rule"]][:20],
               "result_ext": dict(Counter(r["result_ext"] for r in got)),
               "other_files": dict(Counter(n for r in recs for n in (os.path.splitext(x)[1].lower() or "(없음)" for x in r.get("others", [])))),
               "no_eof": sum(1 for r in got if not r.get("eof")),
               "errors": [r.get("error") for r in recs if r.get("error")][:10]}
    # 시각 표기: MM-DD 와 DD-MM 중 폴더 이름 시각과 맞는 쪽
    mmdd = ddmm = both = 0
    dir_vs_file, res_minus_file = [], []
    for r in got:
        a, b = parse_ts(r.get("file_ts", ""))
        if not r.get("dir_time"):
            continue
        d = dt.datetime.strptime(r["dir_time"], "%Y-%m-%d %H:%M")
        ok_a = a is not None and abs((a - d).total_seconds()) < 3600 * 6
        ok_b = b is not None and abs((b - d).total_seconds()) < 3600 * 6
        mmdd += ok_a and not ok_b
        ddmm += ok_b and not ok_a
        both += ok_a and ok_b
        if a:
            dir_vs_file.append(round((a - d).total_seconds() / 60, 1))
            ra, _ = parse_ts(r.get("result_ts", ""))
            if ra:
                res_minus_file.append(round((a - ra).total_seconds() / 60, 1))
    q = lambda xs: (sorted(xs)[0], sorted(xs)[len(xs) // 2], sorted(xs)[-1]) if xs else None  # noqa: E731
    s["ts_format"] = {"MM-DD": mmdd, "DD-MM": ddmm, "둘 다 맞음": both}
    s["file_ts_minus_dir_min"] = q(dir_vs_file)               # (최소, 중앙, 최대) 분
    s["file_ts_minus_result_ts_min"] = q(res_minus_file)
    # Lot 단위
    by_lot = defaultdict(list)
    for r in got:
        by_lot[(r["date_dir"], r["lot_dir"])].append(r)
    lot_rows, rts_const = [], 0
    for (d, lot), rs in sorted(by_lot.items()):
        fts = sorted(x for x in (parse_ts(r.get("file_ts", ""))[0] for r in rs) if x)
        rts = {r.get("result_ts") for r in rs}
        rts_const += len(rts) == 1
        lot_rows.append({"date_dir": d, "lot_dir": lot, "wafers": len(rs),
                         "lot_id": sorted({r.get("lot_id") for r in rs}), "setup_id": sorted({r.get("setup_id") for r in rs}),
                         "step_id": sorted({r.get("step_id") for r in rs}),
                         "first_file_ts": fts[0].isoformat(" ") if fts else "", "last_file_ts": fts[-1].isoformat(" ") if fts else "",
                         "result_ts_values": sorted(x for x in rts if x)[:5],
                         "defects_tiff": sum(r.get("tiff_lines", 0) for r in rs),
                         "defects_records": sum(r.get("defect_records", 0) for r in rs)})
    s["lots"] = len(by_lot)
    s["result_ts_same_in_lot"] = f"{rts_const}/{len(by_lot)}"
    s["lot_dir_eq_lot_id"] = sum(1 for (d, lot), rs in by_lot.items() if all(r.get("lot_id") == lot for r in rs))
    s["lot_in_many_dates"] = sorted(l for l, n in Counter(lot for (d, lot) in by_lot).items() if n > 1)[:20]
    wid = Counter((r.get("lot_id"), r.get("wafer_id")) for r in got)
    s["wafer_id_repeated"] = [f"{l} / {w} ×{n}" for (l, w), n in wid.most_common() if n > 1][:30]
    s["slot_vs_dir_slot_mismatch"] = sum(1 for r in got if r.get("dir_slot") and r.get("slot") and r["dir_slot"] != r["slot"])
    # Defect 개수 세 가지
    s["defect_count_agree"] = {
        "tiff==records": sum(1 for r in got if r.get("tiff_lines") == r.get("defect_records")),
        "records==NDEFECT": sum(1 for r in got if r.get("ndefect") is not None and r.get("defect_records") == r.get("ndefect")),
        "jpg_files==tiff_unique": sum(1 for r in got if r.get("jpg_files") == r.get("tiff_unique")),
        "jpg 파일 0장": sum(1 for r in got if not r.get("jpg_files")), "전체": len(got)}
    s["setup_ids"] = Counter(r.get("setup_id", "") for r in got).most_common()
    s["device_ids"] = Counter(r.get("device_id", "") for r in got).most_common(30)
    s["step_ids"] = Counter(r.get("step_id", "") for r in got).most_common(30)
    s["stations"] = Counter(r.get("station", "") for r in got).most_common(5)
    s["lot_status"] = Counter(r.get("lot_status", "") for r in got).most_common(10)
    s["wafer_status_samples"] = Counter(r.get("wafer_status", "") for r in got).most_common(8)
    s["keys_seen"] = dict(Counter(k for r in got for k in r.get("keys", {})))
    s["lot_table"] = lot_rows
    return s


def pick_copies(recs: list[dict], n: int) -> list[dict]:
    """담을 결과 파일: 확장자 없는 것 · .001 아닌 것 · EOF 없는 것 먼저, 그다음 Lot 마다 첫·끝 Wafer."""
    got = [r for r in recs if r.get("result_name")]
    out, seen = [], set()
    def add(r):
        if r["result_path"] not in seen and len(out) < n:
            seen.add(r["result_path"])
            out.append(r)
    for r in got:
        if r["result_ext"] != ".001" or not r.get("eof"):
            add(r)
    by_lot = defaultdict(list)
    for r in got:
        by_lot[(r["date_dir"], r["lot_dir"])].append(r)
    for rs in by_lot.values():
        rs = sorted(rs, key=lambda r: r["wafer_dir"])
        add(rs[0])
        add(rs[-1])
    return out


def run_tool(tool: str, root: str, folder: Path, args, pool, today) -> dict:
    t0 = time.time()
    facts, jobs = list_lots(tool, root, args.days, today)
    if "error" in facts:
        return {**facts, "ok": False}
    if args.max_wafers and len(jobs) > args.max_wafers:
        facts["wafers_skipped"] = len(jobs) - args.max_wafers
        jobs = jobs[-args.max_wafers:]                                   # 최근 쪽을 남긴다
    say(f"      Lot {sum(1 for l in facts['lots'] if 'wafer_dirs' in l)}개 · Wafer 폴더 {len(jobs)}개 읽는 중…")
    recs = list(pool.map(lambda j: survey_wafer(*j), jobs))
    s = summarize(facts, recs)
    tf = folder / tool
    tf.mkdir(parents=True, exist_ok=True)
    (tf / "samples").mkdir(exist_ok=True)
    for r in pick_copies(recs, args.copy):
        dst = tf / "samples" / f"{r['date_dir']}__{r['lot_dir']}__{r['wafer_dir']}__{r['result_name']}"
        try:
            shutil.copyfile(r["result_path"], dst)                        # NAS 에서 읽어 로컬에만 쓴다
        except OSError as ex:
            s.setdefault("copy_errors", []).append(f"{r['result_name']}: {ex}")
    cols = ["tool", "date_dir", "lot_dir", "wafer_dir", "dir_time", "dir_slot", "files", "jpg_files", "result_name",
            "result_ext", "result_size", "result_mtime", "file_ts", "result_ts", "lot_id", "device_id", "setup_id",
            "setup_date", "step_id", "wafer_id", "slot", "station", "tiff_lines", "tiff_unique", "defect_records",
            "ndefect", "lot_status", "wafer_status", "eof", "error"]
    with open(tf / "wafers.tsv", "w", encoding="utf-8-sig") as f:
        f.write("\t".join(cols) + "\n")
        for r in recs:
            f.write("\t".join(str(r.get(c, "")).replace("\t", " ") for c in cols) + "\n")
    facts.update(s)
    facts["ok"] = True
    facts["seconds"] = round(time.time() - t0, 1)
    (tf / "사실.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return facts


def report_lines(f: dict) -> list[str]:
    if not f.get("ok"):
        return [f"■ {f['tool']} ({f['root']}) — 읽지 못함: {f.get('error')}", ""]
    dc = f["defect_count_agree"]
    L = [f"■ {f['tool']} ({f['root']})  {f['seconds']}초",
         f"   맨 위: 항목 {f['top_total']}개 중 날짜 폴더 {f['top_date_dirs']}개 · 범위 {' ~ '.join(f['date_range'])}",
         f"   날짜 폴더 아닌 것: {', '.join(f['top_other'][:12]) or '없음'}",
         f"   본 날짜: {', '.join(f['dates_picked'])} · Lot {f['lots']}개 · Wafer 폴더 {f['wafer_dirs']}개 · 결과 파일 있음 {f['with_result']}",
         f"   결과 파일 확장자: {f['result_ext']} · 한 폴더에 여러 개 {f['multi_result']} · EndOfFile 없음 {f['no_eof']}",
         f"   결과 파일 없는 Wafer 폴더: {len(f['no_result'])}개 {f['no_result'][:3]}",
         f"   Wafer 폴더 이름 규칙 밖: {f['wafer_dir_rule_miss'][:5] or '없음'}",
         f"   시각 표기 판정: {f['ts_format']}",
         f"   FileTimestamp − 폴더 시각(분) 최소/중앙/최대: {f['file_ts_minus_dir_min']}",
         f"   FileTimestamp − ResultTimestamp(분): {f['file_ts_minus_result_ts_min']} · Lot 안 ResultTimestamp 같음 {f['result_ts_same_in_lot']}",
         f"   Lot 폴더 이름 = LotID: {f['lot_dir_eq_lot_id']}/{f['lots']} · 여러 날짜에 걸친 Lot: {f['lot_in_many_dates'][:5] or '없음'}",
         f"   같은 LotID/WaferID 반복: {f['wafer_id_repeated'][:5] or '없음'}",
         f"   Slot ≠ 폴더 이름 Slot: {f['slot_vs_dir_slot_mismatch']}",
         f"   Defect 개수 일치(전체 {dc['전체']}): jpg이름줄=레코드 {dc['tiff==records']} · 레코드=NDEFECT {dc['records==NDEFECT']}"
         f" · 실제 jpg 파일=jpg이름 {dc['jpg_files==tiff_unique']} · jpg 0장 {dc['jpg 파일 0장']}",
         f"   SetupID {len(f['setup_ids'])}종: " + ", ".join(f"{k}({v})" for k, v in f["setup_ids"][:8]),
         f"   Wafer 폴더 안 기타 파일: {f['other_files'] or '없음'}"]
    if f.get("errors"):
        L.append(f"   오류: {f['errors'][:3]}")
    return L + [""]


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
    ap = argparse.ArgumentParser(description="KLA AOI 사전 조사(NAS 읽기 전용)")
    ap.add_argument("--days", type=int, default=2, help="최근 며칠치 날짜 폴더를 볼지(기본 2)")
    ap.add_argument("--only", nargs="+", help="고른 장비만 (예: K2 4F-K1)")
    ap.add_argument("--out", default="", help="저장 위치 (기본 바탕화면)")
    ap.add_argument("--workers", type=int, default=8, help="동시에 읽을 개수(기본 8)")
    ap.add_argument("--copy", type=int, default=8, help="장비마다 원본 결과 파일을 몇 개 담을지(기본 8)")
    ap.add_argument("--max-wafers", type=int, default=3000, help="장비마다 읽을 Wafer 폴더 상한(0 = 무제한)")
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
    folder = out_base / ("KLA_survey_" + time.strftime("%Y%m%d_%H%M"))
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
            say(f"      {'결과 파일 %d개 · %s초' % (f['with_result'], f['seconds']) if f.get('ok') else '건너뜀 — ' + str(f.get('error'))}")

    all_setups = Counter()
    for f in facts:
        for k, v in f.get("setup_ids", []):
            all_setups[(k, f["tool"])] += v
    lines = [f"KLA 사전 조사 · {stamp(time.time())} · 최근 {args.days}일", ""]
    for f in facts:
        lines += report_lines(f)
    lines += ["■ SetupID × 장비 (Wafer 수)"]
    by_setup = defaultdict(dict)
    for (k, tool), v in all_setups.items():
        by_setup[k][tool] = v
    for k in sorted(by_setup, key=lambda k: -sum(by_setup[k].values())):
        lines.append(f"   {k}   " + " · ".join(f"{t}:{v}" for t, v in sorted(by_setup[k].items())))
    lines += ["", "※ NAS 는 읽기만 했습니다(나열·읽기·로컬로 복사). 원본은 아무것도 바꾸지 않았습니다.",
              "※ 장비 폴더마다 wafers.tsv(Wafer 한 줄씩) · 사실.json · samples\\(원본 결과 파일 몇 개)가 있습니다."]
    (folder / "요약.txt").write_text("\n".join(lines), encoding="utf-8")
    (folder / "요약.json").write_text(json.dumps([{k: v for k, v in f.items() if k not in ("lots", "lot_table")} for f in facts],
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
