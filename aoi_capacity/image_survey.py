"""Review 이미지 순서 조사(10/22 사용자 요청 — 'Review 에서 Color image 보다 Scan image 가 먼저 나온다, 특히 PI').

원인을 가르려면 Wafer 폴더 안의 이미지·목록 파일의 모양이 필요한데 수집기는 읽지 않는다. 이 모듈은 캐시의 최근 Report 에서 Wafer 를 **표본**(PI 우선)으로 골라
그 Wafer 폴더 **안만**(맨 위 목록 + 하위 폴더 한 단계 + 이미지·검토 관련 작은 텍스트 파일) 읽기 전용으로 읽어 로컬 zip 한 장으로 만든다.
경로는 캐시 행에서 계산한 정확한 Wafer 폴더이고(`collect._rdl_wafer_dir`, 재귀 검색 아님), 장비는 수집과 같은 게이트(`devices.resolve_devices`)를 지난 Camtek 만 본다.
★ NAS 는 읽기만 한다. 쓰기는 `write_report` 한 곳(저장 위치는 `nas_guard.assert_local`)."""
from __future__ import annotations

import datetime as dt
import io
import os
import re
import zipfile
from typing import Callable, Dict, List, Optional

from . import collect, failures, nas_guard, scope

LogFn = Callable[[str], None]
DEFAULT_DAYS, MIN_DAYS, MAX_DAYS = 7, 1, 90
PER_DEVICE_PI, PER_DEVICE_OTHER, MAX_TOTAL = 3, 1, 80
#: 카드 'Lot 지정' 칸의 기본값 — 현상이 나는 Lot(AOI-17 · AOI-25 의 PI2, 사용자 10/23). 이슈가 풀리면 카드와 함께 지운다.
DEFAULT_TERMS_TEXT = "FTL-PIDS7, LNY-PIDS7"
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_SUBDIRS = 12
STAT_FIRST, STAT_LAST, STAT_SPREAD = 100, 100, 100          # 하위 폴더 항목이 많으면 이만큼만 시각을 잰다(SMB 왕복)
TEXT_EXT = {".ini", ".txt", ".json", ".xml", ".log", ".org", ".csv"}
KEY_FILES = ("ScanLog.ini", "Scanlog.Org", "ScanResultImageList.txt", "ColorImageGrabingInfo.ini", "WaferInfo.ini",
             "RecipesInfo.ini", "Recipe.ini", "ProductionInfo.ini")
_NAME_HINT = re.compile(r"(?i)color|image|review|verify|defect")
_PI = re.compile(r"(?i)(?<![A-Z])PI\d?(?![A-Z])")
_SAFE = re.compile(r"[^0-9A-Za-z가-힣._ -]+")


def clamp_days(v) -> int:
    try:
        return max(MIN_DAYS, min(MAX_DAYS, int(v)))
    except (TypeError, ValueError):
        return DEFAULT_DAYS


def is_pi(job: str) -> bool:
    return bool(_PI.search(job or ""))


def _spread(items: list, n: int) -> list:
    """시간 순 목록에서 n 개를 고르게(양 끝 포함)."""
    if n <= 0 or not items:
        return []
    if len(items) <= n:
        return list(items)
    if n == 1:
        return [items[len(items) // 2]]
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)]


def pick_samples(cache: dict, cfg: dict, devs: List[dict], cutoff: dt.datetime, *, per_pi=PER_DEVICE_PI, per_other=PER_DEVICE_OTHER,
                 max_total=MAX_TOTAL) -> List[dict]:
    """장비마다 기간 안 EXACT Report 에서 PI 는 per_pi 개, 나머지는 per_other 개(고르게). 캐시만 본다."""
    out: List[dict] = []
    for d in devs:
        if d.get("kind") == "kla" or not scope.is_allowed(cfg, str(d["name"])):
            continue
        scan_root = os.path.join(str(d["path"]), str(d.get("scan_dir") or cfg["scan_dir"]))
        backups = collect._backup_roots(d, scan_root)
        cands: List[dict] = []
        for key, e in (cache.get("reports") or {}).items():
            if e.get("superseded_by") or key.split("|", 1)[0] != str(d["key"]):
                continue
            for r in e.get("rows") or ():
                if r.get("kind") or r.get("ini_match") != "EXACT":
                    continue
                end = collect.parse_dt(r.get("batch_end") or r.get("batch_start"))
                if end is None or end < cutoff:
                    continue
                w = collect._rdl_wafer_dir(r, scan_root, backups)
                if w:
                    cands.append({"device": str(d["name"]), "root": str(d["path"]), "wafer_dir": w, "row": r, "end": end, "pi": is_pi(str(r.get("job") or ""))})
                break                                   # Report 하나에서 Wafer 하나
        cands.sort(key=lambda c: c["end"])
        out += _spread([c for c in cands if c["pi"]], per_pi) + _spread([c for c in cands if not c["pi"]], per_other)
    return out[:max_total]


def parse_terms(text: str) -> List[List[str]]:
    """'TB500.INT556 FTL, TB500.INT808 LNY' → 줄·쉼표·세미콜론으로 나눈 항목마다 공백으로 나눈 낱말(대소문자 무시)."""
    out = []
    for part in re.split(r"[,;\n]+", text or ""):
        words = [w.lower() for w in part.split() if w.strip()]
        if words:
            out.append(words)
    return out


def pick_by_terms(cache: dict, cfg: dict, devs: List[dict], terms: List[List[str]], *, per_term_reports=3, per_report=6,
                  max_total=MAX_TOTAL) -> List[dict]:
    """사용자가 적은 Lot 이름으로 캐시의 Report 를 찾는다(기간 제한 없음) — 항목의 낱말이 모두 Lot · Job · Setup · Wafer · Report 이름 안에 있으면 맞다.
    항목마다 가장 최근 Report per_term_reports 개, Report 마다 EXACT Wafer per_report 장을 고르게. 캐시만 본다."""
    out: List[dict] = []
    for words in terms:
        found: List[tuple] = []
        for d in devs:
            if d.get("kind") == "kla" or not scope.is_allowed(cfg, str(d["name"])):
                continue
            scan_root = os.path.join(str(d["path"]), str(d.get("scan_dir") or cfg["scan_dir"]))
            backups = collect._backup_roots(d, scan_root)
            for key, e in (cache.get("reports") or {}).items():
                if e.get("superseded_by") or key.split("|", 1)[0] != str(d["key"]):
                    continue
                rows = [r for r in e.get("rows") or () if not r.get("kind") and r.get("ini_match") == "EXACT"]
                if not rows:
                    continue
                hay = " ".join(str(rows[0].get(k) or "") for k in ("lot", "job", "setup", "report")).lower()
                hay += " " + " ".join(str(r.get("wafer_id") or "") for r in rows).lower()
                if not all(w in hay for w in words):
                    continue
                end = collect.parse_dt(rows[0].get("batch_end") or rows[0].get("batch_start")) or dt.datetime.min
                found.append((end, d, scan_root, backups, rows))
        found.sort(key=lambda f: f[0], reverse=True)
        for end, d, scan_root, backups, rows in found[:per_term_reports]:
            for r in _spread(rows, per_report):
                w = collect._rdl_wafer_dir(r, scan_root, backups)
                if w:
                    out.append({"device": str(d["name"]), "root": str(d["path"]), "wafer_dir": w, "row": r, "end": end,
                                "pi": is_pi(str(r.get("job") or "")), "term": " ".join(words)})
    return out[:max_total]


def _safe(s: str) -> str:
    return _SAFE.sub("_", s).strip("._ ") or "x"


def _fmt_time(t: float) -> str:
    try:
        return dt.datetime.fromtimestamp(t).isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return ""


def _list_top(path: str) -> List[dict]:
    out = []
    with nas_guard.scandir(path) as it:
        for e in it:
            try:
                st = e.stat()
                out.append({"name": e.name, "dir": e.is_dir(), "size": st.st_size, "mtime": st.st_mtime})
            except OSError:
                out.append({"name": e.name, "dir": False, "size": "", "mtime": 0.0})
    return sorted(out, key=lambda x: x["name"].lower())


def _list_sub(path: str) -> dict:
    """하위 폴더 한 단계 — 확장자별 개수 + 시각을 잰 항목(많으면 처음 · 끝 · 고르게)을 시각 순으로."""
    names: List[str] = []
    with nas_guard.scandir(path) as it:
        for e in it:
            names.append(e.name)
    names.sort()
    ext: Dict[str, int] = {}
    for n in names:
        k = os.path.splitext(n)[1].lower() or "(없음)"
        ext[k] = ext.get(k, 0) + 1
    if len(names) <= STAT_FIRST + STAT_LAST + STAT_SPREAD:
        pick = names
    else:
        mid = _spread(names[STAT_FIRST:-STAT_LAST], STAT_SPREAD)
        pick = names[:STAT_FIRST] + mid + names[-STAT_LAST:]
    ents = []
    for n in pick:
        try:
            st = os.stat(os.path.join(path, n))
            ents.append((st.st_mtime, n, st.st_size))
        except OSError:
            ents.append((0.0, n, ""))
    ents.sort()
    return {"count": len(names), "ext": ext, "sampled": len(pick), "entries": ents}


def render_listing(top: List[dict], subs: Dict[str, dict]) -> str:
    lines = ["# 맨 위 (이름순)", "이름\t종류\t크기\t수정 시각"]
    for t in top:
        lines.append(f"{t['name']}\t{'폴더' if t['dir'] else '파일'}\t{t['size']}\t{_fmt_time(t['mtime']) if t['mtime'] else ''}")
    for name, s in subs.items():
        lines += ["", f"# 하위 폴더 {name} — {s['count']}개 · 확장자 " + ", ".join(f"{k} {v}" for k, v in sorted(s["ext"].items())),
                  f"(시각을 잰 {s['sampled']}개를 수정 시각 순으로)", "수정 시각\t이름\t크기"]
        lines += [f"{_fmt_time(m) if m else ''}\t{n}\t{sz}" for m, n, sz in s["entries"]]
    return "\n".join(lines) + "\n"


def _read_small(path: str) -> Optional[bytes]:
    try:
        return nas_guard.read_head(path, MAX_FILE_BYTES)[:MAX_FILE_BYTES]
    except OSError:
        return None


def survey_wafer(s: dict, allowed: Callable[[str], bool]) -> dict:
    """표본 Wafer 폴더 하나를 읽는다. 허용 장비 · 그 장비 폴더 아래 경로만. → {"listing": 글, "files": {이름: bytes}, "note": 글, "facts": {...}}"""
    res: dict = {"listing": "", "files": {}, "note": "", "facts": {}}
    w = s["wafer_dir"]
    if not allowed(s["device"]):
        res["note"] = "수집 범위 밖 장비라 읽지 않음"
        return res
    if not nas_guard.is_under(w, s["root"]):
        res["note"] = "장비 폴더 밖 경로라 읽지 않음"
        return res
    try:
        top = _list_top(w)
    except OSError as ex:
        res["note"] = f"Wafer 폴더를 못 읽음 — {type(ex).__name__}: {ex}"
        return res
    subs: Dict[str, dict] = {}
    for t in [t for t in top if t["dir"]][:MAX_SUBDIRS]:
        try:
            subs[t["name"]] = _list_sub(os.path.join(w, t["name"]))
        except OSError as ex:
            subs[t["name"]] = {"count": 0, "ext": {"읽기 실패": 1}, "sampled": 0, "entries": [(0.0, f"{type(ex).__name__}: {ex}", "")]}
    res["listing"] = render_listing(top, subs)
    by_lower = {t["name"].lower(): t["name"] for t in top if not t["dir"]}
    want = [by_lower[k.lower()] for k in KEY_FILES if k.lower() in by_lower]
    want += [t["name"] for t in top if not t["dir"] and t["name"] not in want and _NAME_HINT.search(t["name"])
             and os.path.splitext(t["name"])[1].lower() in TEXT_EXT]
    for name in want:
        data = _read_small(os.path.join(w, name))
        if data is not None:
            res["files"][name] = data
    res["facts"] = {"top_files": sum(1 for t in top if not t["dir"]), "top_jpg": sum(1 for t in top if t["name"].lower().endswith((".jpg", ".jpeg"))),
                    "subdirs": "; ".join(f"{n}={s_['count']}" for n, s_ in subs.items())}
    return res


def gather(cfg: dict, days: int, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, now: Optional[dt.datetime] = None,
           resolver=None, terms: Optional[List[List[str]]] = None, **kw) -> dict:
    now = now or dt.datetime.now()
    days = clamp_days(days)
    cutoff = now - dt.timedelta(days=days)
    stop = should_stop or (lambda: False)
    log(f"Review 이미지 순서 조사 — 지난 {days}일({cutoff:%m/%d %H:%M} ~) 표본")
    cache = collect._load_cache(cfg, rederive=False, dirty=collect._Dirty())
    probe = failures.probe_devices(cfg, log, stop, resolver)
    collect._assign_device_keys(cache, probe["ok"], cfg, collect._Dirty(), log)      # 장비 dict 에 안정 키(d["key"]) 를 붙인다 — 메모리 안에서만, 캐시 파일은 쓰지 않는다
    if terms:
        samples = pick_by_terms(cache, cfg, probe["ok"], terms)
        log(f"Lot 지정 {len(terms)}개 — 맞는 Wafer {len(samples)}장")
    else:
        samples = pick_samples(cache, cfg, probe["ok"], cutoff, **kw)
    log(f"표본 {len(samples)}장(PI {sum(1 for s in samples if s['pi'])}) — 장비 {len({s['device'] for s in samples})}대")
    allowed = lambda n: scope.is_allowed(cfg, n)  # noqa: E731
    for i, s in enumerate(samples, 1):
        if stop():
            log("멈춤 요청 — 지금까지 모은 것으로 마무리합니다")
            break
        s["result"] = survey_wafer(s, allowed)
        log(f"[{i}/{len(samples)}] {s['device']} {s['row'].get('job', '')} / {s['row'].get('wafer_id', '')} — "
            + (s["result"]["note"] or f"파일 {len(s['result']['files'])}개 · {s['result']['facts'].get('subdirs', '')}"))
    return {"now": now, "days": days, "cutoff": cutoff, "samples": samples, "probe": probe}


def _tsv(rows: List[List[object]]) -> str:
    return failures._tsv(rows)


def render_summary(g: dict) -> str:
    done = [s for s in g["samples"] if (s.get("result") or {}).get("listing")]
    pi = [s for s in g["samples"] if s["pi"]]
    return (f"Review 이미지 순서 조사 — {g['now']:%Y-%m-%d %H:%M} 기준 지난 {g['days']}일\n\n"
            f"표본 {len(g['samples'])}장(PI {len(pi)}장 · 그 밖 {len(g['samples']) - len(pi)}장) · 장비 {len({s['device'] for s in g['samples']})}대 · 폴더를 읽은 것 {len(done)}장\n\n"
            "구성: 표본.tsv(표본 한 줄씩) · files/<장비>/<번호>_<Wafer>/ 안에 listing.txt(폴더 목록과 하위 폴더 항목의 수정 시각 순) 와 읽은 ini·txt 원본.\n"
            "파일 내용에는 Lot · Job 이름이 들어 있습니다 — 공유 범위는 직접 판단해 주세요.\n")


def write_report(cfg: dict, g: dict, out_dir: str) -> str:
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"AOI_review_image_{g['now']:%Y%m%d_%H%M}.zip")
    head = ["번호", "장비", "PI", "Job", "Setup", "Lot", "Wafer", "Report", "레시피", "방식", "배치 시작", "Defect", "Wafer 폴더", "맨 위 파일", "맨 위 jpg", "하위 폴더(개수)", "비고"]
    rows = [head]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, s in enumerate(g["samples"], 1):
            r, res = s["row"], s.get("result") or {"listing": "", "files": {}, "note": "건너뜀", "facts": {}}
            f = res["facts"]
            rows.append([n, s["device"], "PI" if s["pi"] else "", r.get("job", ""), r.get("setup", ""), r.get("lot", ""), r.get("wafer_id", ""),
                         r.get("report", ""), r.get("recipe", ""), r.get("scan_mode", ""), r.get("batch_start", ""), r.get("faults", ""), s["wafer_dir"],
                         f.get("top_files", ""), f.get("top_jpg", ""), f.get("subdirs", ""), res["note"]])
            base = f"files/{_safe(s['device'])}/{n:03d}_{_safe(str(r.get('wafer_id') or 'wafer'))}"
            if res["listing"]:
                z.writestr(f"{base}/listing.txt", res["listing"])
            for name, data in res["files"].items():
                z.writestr(f"{base}/{_safe(name)}", data)
        z.writestr("요약.txt", render_summary(g))
        z.writestr("표본.tsv", _tsv(rows))
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    return out


def run(cfg: dict, days: int, out_dir: str, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, **kw) -> dict:
    """kw 의 `terms`(parse_terms 결과)가 있으면 기간 표본 대신 그 Lot 들만 본다."""
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))       # NAS 를 읽기 전에 저장 위치부터 확인
    g = gather(cfg, days, log=log, should_stop=should_stop, **kw)
    path = write_report(cfg, g, out_dir)
    return {"path": path, "items": len(g["samples"]), "days": g["days"], "out_dir": out_dir}
