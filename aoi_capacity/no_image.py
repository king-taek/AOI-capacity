"""No image 점검(10/22 사용자 요청 — "스캔은 됐는데 이미지가 안 나온다", Lot 이름에 NO IMAGE 가 붙은 재스캔).

Lot 이름에 `NO IMAGE` 가 붙은 Report 는 이미지 문제 때문에 다시 스캔한 것이다. 원인을 가르려면 **재스캔한 Wafer 와 그 원래 스캔(같은 Wafer ID 의 앞선 PASS)** 의
Wafer 폴더 안 ini · txt 를 나란히 봐야 하는데 수집기는 읽지 않는다. 캐시에서 쌍을 골라 그 Wafer 폴더 **안만**(맨 위 텍스트 파일 + 하위 폴더 한 단계) 읽기 전용으로 읽어
**8MB 이하 zip 한 장**으로 만든다. 경로는 캐시 행에서 계산한 정확한 Wafer 폴더이고(`collect._rdl_wafer_dir`, 재귀 검색 아님) 장비는 수집과 같은 게이트를 지난 Camtek 만 본다.
★ NAS 는 읽기만 한다. 쓰기는 `write_report` 한 곳(저장 위치는 `nas_guard.assert_local`). 이미지 · .dat 는 담지 않고 목록에만 적는다."""
from __future__ import annotations

import datetime as dt
import io
import os
import re
import zipfile
from typing import Callable, Dict, List, Optional, Tuple

from . import collect, failures, image_survey, nas_guard, scope

LogFn = Callable[[str], None]
DEFAULT_DAYS, MIN_DAYS, MAX_DAYS = 60, 1, 90
MAX_ZIP_BYTES = 8 * 1000 * 1000                  # 사용자 지시: zip 1개 8MB 이하(MB 를 1,000,000 으로 잡아 어느 쪽으로 세도 넘지 않는다)
RESERVE_BYTES = 300 * 1000                       # 요약 · 표본.tsv · zip 중앙 디렉터리 몫
MAX_REPORTS, WAFERS_PER_REPORT = 40, 2
MAX_FILE_BYTES = 256 * 1024
MAX_FILES_PER_DIR = 60
_NO_IMAGE = re.compile(r"(?i)NO[\s_-]*IMAGE")
_TEXT_EXT = image_survey.TEXT_EXT


def clamp_days(v) -> int:
    try:
        return max(MIN_DAYS, min(MAX_DAYS, int(v)))
    except (TypeError, ValueError):
        return DEFAULT_DAYS


def is_no_image(row: dict) -> bool:
    return bool(_NO_IMAGE.search(str(row.get("lot") or "")) or _NO_IMAGE.search(str(row.get("report") or "")))


def _outcome(r: dict) -> str:
    return str(r.get("outcome") or r.get("norm_status") or "")


def pick_cases(cache: dict, cfg: dict, devs: List[dict], cutoff: dt.datetime, *, max_reports: int = MAX_REPORTS,
               per_report: int = WAFERS_PER_REPORT) -> List[dict]:
    """NO IMAGE Report 마다 Wafer 를 per_report 장(처음 · 끝) 고르고, 각각의 **원래 스캔**(같은 Wafer ID · 앞선 PASS · NO IMAGE 아님 중 가장 가까운 것)을 짝지운다. 캐시만 본다."""
    by_key = {str(d["key"]): d for d in devs if d.get("kind") != "kla" and scope.is_allowed(cfg, str(d["name"]))}
    dirs: Dict[str, Tuple[str, list]] = {}
    for k, d in by_key.items():
        scan_root = os.path.join(str(d["path"]), str(d.get("scan_dir") or cfg["scan_dir"]))
        dirs[k] = (scan_root, collect._backup_roots(d, scan_root))
    exact: List[dict] = []                                          # 폴더를 계산할 수 있는 모든 EXACT 행 — 원래 스캔 후보와 NO IMAGE 후보
    for key, e in (cache.get("reports") or {}).items():
        dk = key.split("|", 1)[0]
        if e.get("superseded_by") or dk not in by_key:
            continue
        for r in e.get("rows") or ():
            if r.get("kind") or r.get("ini_match") != "EXACT" or not r.get("wafer_id"):
                continue
            start = collect.parse_dt(r.get("batch_start"))
            end = collect.parse_dt(r.get("batch_end") or r.get("batch_start"))
            w = collect._rdl_wafer_dir(r, *dirs[dk])
            if start is None or end is None or not w:
                continue
            exact.append({"dk": dk, "device": str(by_key[dk]["name"]), "root": str(by_key[dk]["path"]), "wafer_dir": w, "row": r, "start": start, "end": end,
                          "rkey": key, "no_image": is_no_image(r)})
    by_wafer: Dict[str, List[dict]] = {}
    for x in exact:
        by_wafer.setdefault(str(x["row"]["wafer_id"]), []).append(x)
    reports: Dict[str, List[dict]] = {}
    for x in exact:
        if x["no_image"] and x["end"] >= cutoff:
            reports.setdefault(x["rkey"], []).append(x)
    cases: List[dict] = []
    for rkey, xs in sorted(reports.items(), key=lambda kv: kv[1][0]["start"], reverse=True)[:max_reports]:
        xs.sort(key=lambda x: str(x["row"]["wafer_id"]))
        pick = [xs[0]] if len(xs) == 1 or per_report < 2 else [xs[0], xs[-1]]
        for x in pick:
            prev = [o for o in by_wafer.get(str(x["row"]["wafer_id"]), ())
                    if not o["no_image"] and o["rkey"] != x["rkey"] and o["end"] <= x["start"] and _outcome(o["row"]) == "PASS"]
            orig = max(prev, key=lambda o: o["end"]) if prev else None
            cases.append({"rescan": x, "original": orig})
    return cases


def _safe(s: str) -> str:
    return image_survey._safe(s)


def _read_dir_texts(path: str, budget: int) -> Tuple[Dict[str, bytes], int]:
    """폴더 하나의 텍스트 파일(ini · txt · json …) 중 작은 것만, 합이 budget 바이트를 넘지 않게. → ({이름: bytes}, 못 담은 수)"""
    names: List[str] = []
    with nas_guard.scandir(path) as it:
        for e in it:
            try:
                if e.is_file() and os.path.splitext(e.name)[1].lower() in _TEXT_EXT:
                    names.append(e.name)
            except OSError:
                continue
    key = {k.lower(): i for i, k in enumerate(image_survey.KEY_FILES)}
    names.sort(key=lambda n: (key.get(n.lower(), 99), n.lower()))            # 핵심 파일 먼저
    out: Dict[str, bytes] = {}
    used = skipped = 0
    for n in names[:MAX_FILES_PER_DIR]:
        data = image_survey._read_small(os.path.join(path, n))
        if data is None:
            continue
        data = data[:MAX_FILE_BYTES]
        if used + len(data) > budget:
            skipped += 1
            continue
        out[n] = data
        used += len(data)
    return out, skipped + max(0, len(names) - MAX_FILES_PER_DIR)


def read_wafer(s: dict, allowed: Callable[[str], bool], budget: int = 1_500_000) -> dict:
    """Wafer 폴더 하나 — 허용 장비 · 그 장비 폴더 아래만. → {"listing", "files": {상대 경로: bytes}, "note", "left"}"""
    res: dict = {"listing": "", "files": {}, "note": "", "left": 0}
    w = s["wafer_dir"]
    if not allowed(s["device"]):
        res["note"] = "수집 범위 밖 장비라 읽지 않음"
        return res
    if not nas_guard.is_under(w, s["root"]):
        res["note"] = "장비 폴더 밖 경로라 읽지 않음"
        return res
    try:
        top = image_survey._list_top(w)
    except OSError as ex:
        res["note"] = f"Wafer 폴더를 못 읽음 — {type(ex).__name__}: {ex}"
        return res
    subs: Dict[str, dict] = {}
    for t in [t for t in top if t["dir"]][:image_survey.MAX_SUBDIRS]:
        try:
            subs[t["name"]] = image_survey._list_sub(os.path.join(w, t["name"]))
        except OSError as ex:
            subs[t["name"]] = {"count": 0, "ext": {"읽기 실패": 1}, "sampled": 0, "entries": [(0.0, f"{type(ex).__name__}: {ex}", "")]}
    res["listing"] = image_survey.render_listing(top, subs)
    files, left = _read_dir_texts(w, budget)
    res["files"].update(files)
    res["left"] += left
    for t in [t for t in top if t["dir"]][:image_survey.MAX_SUBDIRS]:
        rest = budget - sum(len(v) for v in res["files"].values())
        if rest <= 0:
            res["left"] += 1
            continue
        try:
            sub, sk = _read_dir_texts(os.path.join(w, t["name"]), rest)
        except OSError:
            continue
        res["files"].update({f"{t['name']}/{n}": d for n, d in sub.items()})
        res["left"] += sk
    return res


def gather(cfg: dict, days: int, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, now: Optional[dt.datetime] = None,
           resolver=None, **kw) -> dict:
    now = now or dt.datetime.now()
    days = clamp_days(days)
    cutoff = now - dt.timedelta(days=days)
    stop = should_stop or (lambda: False)
    log(f"No image 점검 — 지난 {days}일({cutoff:%m/%d %H:%M} ~) 에 시작된 Lot 이름 NO IMAGE 재스캔과 원래 스캔")
    cache = collect._load_cache(cfg, rederive=False, dirty=collect._Dirty())
    probe = failures.probe_devices(cfg, log, stop, resolver)
    collect._assign_device_keys(cache, probe["ok"], cfg, collect._Dirty())      # 장비 키(`dev:AOI-25`)는 수집이 붙인다 — 캐시를 저장하지 않으니 메모리에서만
    cases = pick_cases(cache, cfg, probe["ok"], cutoff, **kw)
    log(f"재스캔 Wafer {len(cases)}장 · 원래 스캔을 찾은 것 {sum(1 for c in cases if c['original'])}장")
    allowed = lambda n: scope.is_allowed(cfg, n)  # noqa: E731
    budget_total = MAX_ZIP_BYTES - RESERVE_BYTES
    for i, c in enumerate(cases, 1):
        if stop():
            log("멈춤 요청 — 지금까지 모은 것으로 마무리합니다")
            break
        # zip 은 압축하므로 원본이 더 커도 된다 — 사례마다 원본 기준 몫을 주고(압축률은 쓰는 단계에서 8MB 로 다시 막는다)
        share = max(200_000, budget_total * 4 // max(1, len(cases)) // 2)
        for which in ("rescan", "original"):
            if c[which] is not None:
                c[which]["result"] = read_wafer(c[which], allowed, share)
        r = c["rescan"]
        log(f"[{i}/{len(cases)}] {r['device']} {r['row'].get('lot', '')} / {r['row'].get('wafer_id', '')} — 재스캔 파일 {len(r['result']['files'])}개"
            + (f" · 원래 스캔 {c['original']['device']} 파일 {len(c['original']['result']['files'])}개" if c["original"] else " · 원래 스캔 못 찾음"))
    return {"now": now, "days": days, "cutoff": cutoff, "cases": cases, "probe": probe}


def render_summary(g: dict, dropped: int) -> str:
    n = len(g["cases"])
    return (f"No image 점검 — {g['now']:%Y-%m-%d %H:%M} 기준 지난 {g['days']}일\n\n"
            f"Lot 이름에 NO IMAGE 가 붙은 재스캔 Wafer {n}장 · 원래 스캔(같은 Wafer ID 의 앞선 PASS)을 찾은 것 {sum(1 for c in g['cases'] if c['original'])}장\n\n"
            "구성: 사례.tsv(사례 한 줄씩) · files/<번호>_<Wafer>/rescan|original/ 안에 listing.txt(폴더 목록 · 하위 폴더 항목의 수정 시각 순) 와 읽은 ini · txt 원본.\n"
            "이미지 · .dat 는 담지 않고 목록에만 있습니다. 파일 내용에는 Lot · Job 이름이 들어 있습니다 — 공유 범위는 직접 판단해 주세요.\n"
            f"zip 크기 상한 {MAX_ZIP_BYTES // 1000000}MB 때문에 담지 못한 파일 {dropped}개.\n")


def write_report(cfg: dict, g: dict, out_dir: str) -> Tuple[str, int]:
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"AOI_no_image_{g['now']:%Y%m%d_%H%M}.zip")
    head = ["번호", "구분", "장비", "Job", "Setup", "Lot", "Wafer", "Report", "레시피", "방식", "배치 시작", "배치 끝", "Defect", "Wafer 폴더", "읽은 파일", "못 담은 파일", "비고"]
    rows = [head]
    buf = io.BytesIO()
    limit = MAX_ZIP_BYTES - RESERVE_BYTES
    dropped = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n, c in enumerate(g["cases"], 1):
            for which, label in (("rescan", "재스캔(NO IMAGE)"), ("original", "원래 스캔")):
                s = c[which]
                if s is None:
                    rows.append([n, label, "", "", "", "", c["rescan"]["row"].get("wafer_id", ""), "", "", "", "", "", "", "", "", "", "같은 Wafer ID 의 앞선 PASS 를 캐시에서 못 찾음"])
                    continue
                r, res = s["row"], s.get("result") or {"listing": "", "files": {}, "note": "건너뜀", "left": 0}
                put = 0
                base = f"files/{n:03d}_{_safe(str(r.get('wafer_id') or 'wafer'))}/{which}"
                items = ([(f"{base}/listing.txt", res["listing"].encode("utf-8"))] if res["listing"] else []) + [(f"{base}/{_safe(k.replace('/', '__'))}", v) for k, v in res["files"].items()]
                for name, data in items:
                    if buf.tell() >= limit:          # 압축된 크기를 바로 알 수 있다 — 상한 직전이면 더 담지 않는다(파일 하나 최대 256KB < 예비 300KB)
                        dropped += 1
                        continue
                    z.writestr(name, data)
                    put += 1
                rows.append([n, label, s["device"], r.get("job", ""), r.get("setup", ""), r.get("lot", ""), r.get("wafer_id", ""), r.get("report", ""), r.get("recipe", ""),
                             r.get("scan_mode", ""), r.get("batch_start", ""), r.get("batch_end", ""), r.get("faults", ""), s["wafer_dir"], put, res.get("left", 0), res.get("note", "")])
        z.writestr("요약.txt", render_summary(g, dropped + sum(((c[w] or {}).get("result") or {}).get("left", 0) for c in g["cases"] for w in ("rescan", "original"))))
        z.writestr("사례.tsv", failures._tsv(rows))
    data = buf.getvalue()
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError(f"zip 이 {MAX_ZIP_BYTES // 1000000}MB 를 넘었습니다({len(data)}바이트)")
    with open(out, "wb") as fh:
        fh.write(data)
    return out, dropped


def run(cfg: dict, days: int, out_dir: str, *, log: LogFn, should_stop: Optional[Callable[[], bool]] = None, **kw) -> dict:
    nas_guard.assert_local(out_dir, nas_guard.roots_for_cfg(cfg))       # NAS 를 읽기 전에 저장 위치부터 확인
    g = gather(cfg, days, log=log, should_stop=should_stop, **kw)
    path, dropped = write_report(cfg, g, out_dir)
    return {"path": path, "items": len(g["cases"]), "days": g["days"], "out_dir": out_dir, "dropped": dropped, "size": os.path.getsize(path)}
