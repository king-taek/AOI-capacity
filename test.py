#!/usr/bin/env python
"""AOI Capacity — NAS 읽기 성능 현장 측정(읽기 전용, 결과 파일 한 장).

무엇을 재나(Claude · ChatGPT 제안서의 P0~P2 · E01~E04 · E08~E10 를 한 번에, 작은 표본으로):
  0. 환경       — Windows/Python, `net use` · Get-SmbMapping/Connection/ClientConfiguration(조회만), 드라이브 → UNC → 앱의 NAS 묶음
  1. 목록       — 묶음마다 장비 1대: 전체 scandir · FindFirstFileExW('*', LARGE_FETCH) · 날짜 패턴(최근 3일) · scandir 다시(따뜻한 캐시)
  2. Report     — 장비마다 최근 Report K개를 앱처럼 NAS 묶음별 동시 읽기 → 읽기/해시·파싱 시간, Wafer 작업 목록(앱과 같은 후보 순서)
  3. 직렬 특성  — 묶음마다 Wafer 몇십 장을 한 줄로: INI 성공/없음/오류 · MoveResultFlag · 후보 순위별 시간,
                  그 뒤 분석용으로만 부모 폴더(Lot·Setup·Job·Wafer) 존재 확인 → A(부모 부재 묶기)·B(후보 학습)·C(Lot 나열) 손익 추정
  4. API 비교   — 처음 보는 경로에 open().read() · os.open+read 1회 · os.stat · isfile · GetFileAttributesExW · 정확 이름 FindFirstFileExW
  5. 동시성 곡선 — 묶음마다 혼자 1·2·4·8·16개(오름차순 → 내림차순, 매번 새 Wafer) + 모든 묶음 동시 8개(지금 앱과 같은 모양)

지키는 것(CLAUDE.md 절대 규칙):
  * NAS 는 **읽기만** 한다 — open 은 'rb'/O_RDONLY, 쓰는 파일은 로컬 결과 JSON 하나(`nas_guard.assert_local` 로 확인).
  * 장비는 앱과 같은 `devices.resolve_devices`(수집 범위 게이트)만 쓴다 — 범위 밖 장비는 건드리지 않는다.
  * Scanresult 를 재귀 검색하지 않는다 — Report 에서 계산한 정확 경로만 연다. 예외는 조사용 Lot 폴더 한 단계 나열(`--lot-list-max`,
    현장 조사 도구 `scripts/collect_sample.py` 와 같은 범위)이며 `--lot-list-max 0` 이면 하지 않는다.
  * 캐시·결과 HTML·설정은 건드리지 않는다(앱 수집을 대신하지 않는다).

실행(현장 PC — 앱과 같은 사용자로, 수집이 돌지 않을 때):
  * git 폴더:        python test.py
  * 배포본(exe-lite): test.py 를 `AOI_Capacity_Lite\\app\\` 에 두고 그 폴더에서  ..\\python\\python.exe test.py
  * 옵션 없이 실행하면(더블클릭 포함) 측정 방식·장비·시간 등을 차례로 묻는다 — Enter 만 누르면 기본값.
  * 옵션으로 바로:   python test.py --quick        (표본을 절반으로, 묻지 않음 · --ask 를 붙이면 그래도 묻는다)
  * 장비 일부만:     python test.py --devices AOI-1,AOI-9,4F-AOI-01
  결과: `%LOCALAPPDATA%\\AOI_Capacity\\bench\\nas_bench_<시각>.json` — 이 파일 하나를 첨부한다. Ctrl+C 로 멈춰도 그때까지 결과를 쓴다.
  결과에는 장비 경로·Job·Lot·Wafer 이름이 들어간다(분석용). 기본 설정이면 보통 15~30분, `--max-minutes`(기본 40)를 넘으면 남은 단계를 건너뛴다.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import platform
import random
import statistics
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

BENCH_VERSION = 1
MISSING_EXC = (FileNotFoundError, NotADirectoryError, IsADirectoryError)


# ----------------------------------------------------------------------------- 앱 코드 찾기
def _find_app() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.path.join(here, "app"), os.path.dirname(here), os.path.join(os.path.dirname(here), "app"), os.getcwd()):
        if os.path.isfile(os.path.join(base, "aoi_capacity", "collect.py")):
            return base
    raise SystemExit("aoi_capacity 패키지를 찾지 못했습니다 — test.py 를 저장소 맨 위나 배포본의 app 폴더에 두고 실행하세요.")


APP_BASE = _find_app()
if APP_BASE not in sys.path:
    sys.path.insert(0, APP_BASE)

from aoi_capacity import collect, devices as devices_mod, nas_guard, scope  # noqa: E402
from aoi_capacity import cli as cli_mod  # noqa: E402
from aoi_capacity.utils import config as config_mod, paths  # noqa: E402


# ----------------------------------------------------------------------------- 작은 도구
T0 = time.perf_counter()
LOG: list = []
_LOG_LOCK = threading.Lock()


def log(msg: str) -> None:
    line = f"[{time.perf_counter() - T0:7.1f}s] {msg}"
    with _LOG_LOCK:
        LOG.append(line)
    try:
        print(line, flush=True)
    except Exception:  # noqa: BLE001
        pass


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 2)


def dist(xs) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": round(statistics.fmean(xs), 2), "p50": pct(xs, 50), "p90": pct(xs, 90),
            "p95": pct(xs, 95), "p99": pct(xs, 99), "max": round(max(xs), 2), "sum": round(sum(xs), 1)}


def ms_since(t: float) -> float:
    return (time.perf_counter() - t) * 1000.0


class Deadline:
    def __init__(self, minutes: float) -> None:
        self.end = time.perf_counter() + minutes * 60

    def left(self) -> float:
        return self.end - time.perf_counter()

    def over(self) -> bool:
        return self.left() <= 0


def run_cmd(args, timeout=40) -> dict:
    """조회용 명령(net use · PowerShell Get-*). 실패해도 계속한다."""
    t = time.perf_counter()
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout)
        out = p.stdout.decode("utf-8", "replace") if p.stdout else ""
        if "�" in out and os.name == "nt":
            out = p.stdout.decode("cp949", "replace")
        err = p.stderr.decode("utf-8", "replace") if p.stderr else ""
        return {"cmd": " ".join(args), "rc": p.returncode, "ms": round(ms_since(t)), "out": out[-20000:], "err": err[-4000:]}
    except Exception as e:  # noqa: BLE001
        return {"cmd": " ".join(args), "error": f"{type(e).__name__}: {e}"}


# ----------------------------------------------------------------------------- 읽기 전용 원시 작업(시간 재기)
def op_open_read(path: str):
    """앱과 같은 방식(open 'rb' 전체 읽기). → (결과, ms, bytes, 오류)"""
    t = time.perf_counter()
    try:
        with open(path, "rb") as f:
            n = len(f.read())
        return "ok", ms_since(t), n, ""
    except MISSING_EXC:
        return "missing", ms_since(t), 0, ""
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}"


def op_os_read_once(path: str):
    t = time.perf_counter()
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            n = len(os.read(fd, 1 << 20))
        finally:
            os.close(fd)
        return "ok", ms_since(t), n, ""
    except MISSING_EXC:
        return "missing", ms_since(t), 0, ""
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}"


def op_stat(path: str):
    t = time.perf_counter()
    try:
        os.stat(path)
        return "ok", ms_since(t), 0, ""
    except MISSING_EXC:
        return "missing", ms_since(t), 0, ""
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}"


def op_isfile(path: str):
    t = time.perf_counter()
    r = os.path.isfile(path)
    return ("ok" if r else "missing"), ms_since(t), 0, ""


def op_isdir(path: str):
    """부모 폴더 존재 확인 — isdir 대신 stat 으로 오류(권한 등)와 부재를 가른다."""
    t = time.perf_counter()
    try:
        st = os.stat(path)
        import stat as _st
        return ("ok" if _st.S_ISDIR(st.st_mode) else "notdir"), ms_since(t), 0, ""
    except MISSING_EXC:
        return "missing", ms_since(t), 0, ""
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}"


_K32 = None


def _k32():
    global _K32
    if _K32 is None:
        import ctypes
        from ctypes import wintypes

        k = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        k.GetFileAttributesExW.argtypes = [wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p]
        k.GetFileAttributesExW.restype = wintypes.BOOL
        _K32 = k
    return _K32


def op_win_getattr(path: str):
    import ctypes
    from ctypes import wintypes

    class _D(ctypes.Structure):
        _fields_ = [("attr", wintypes.DWORD), ("c", wintypes.DWORD * 2), ("a", wintypes.DWORD * 2), ("w", wintypes.DWORD * 2),
                    ("hi", wintypes.DWORD), ("lo", wintypes.DWORD)]

    t = time.perf_counter()
    d = _D()
    ok = _k32().GetFileAttributesExW(path, 0, ctypes.byref(d))
    ms = ms_since(t)
    if ok:
        return "ok", ms, 0, ""
    err = ctypes.get_last_error()
    return ("missing" if err in (2, 3) else "error"), ms, 0, ("" if err in (2, 3) else f"WinError {err}")


def op_win_find_exact(path: str):
    t = time.perf_counter()
    try:
        got = nas_guard.find_pattern(os.path.dirname(path), os.path.basename(path))
        return ("ok" if got else "missing"), ms_since(t), 0, ""
    except MISSING_EXC:
        return "missing", ms_since(t), 0, ""
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"
        return ("missing" if "WinError 3" in msg else "error"), ms_since(t), 0, ("" if "WinError 3" in msg else msg)


API_METHODS = {"py_open_read": op_open_read, "os_read_once": op_os_read_once, "os_stat": op_stat, "isfile": op_isfile}
if os.name == "nt":
    API_METHODS.update({"win_getattr": op_win_getattr, "win_find_exact": op_win_find_exact})


# ----------------------------------------------------------------------------- 묶음별 동시 실행(앱의 _run 과 같은 모양)
def run_grouped(items, group_of, per_group: int, fn):
    """묶음마다 per_group 개 스레드. 결과는 입력 순서. 예외는 결과 자리에 (None, 예외)."""
    items = list(items)
    queues = collections.OrderedDict()
    for i, it in enumerate(items):
        queues.setdefault(group_of(it), collections.deque()).append(i)
    results = [None] * len(items)
    lock = threading.Lock()

    def lane(q):
        while True:
            with lock:
                if not q:
                    return
                i = q.popleft()
            try:
                results[i] = fn(items[i])
            except Exception as e:  # noqa: BLE001
                results[i] = (None, e)

    lanes = [(q, max(1, min(per_group, len(q)))) for q in queues.values()]
    with ThreadPoolExecutor(max_workers=max(1, sum(k for _, k in lanes)), thread_name_prefix="bench") as pool:
        for f in [pool.submit(lane, q) for q, k in lanes for _ in range(k)]:
            f.result()
    return results


# ----------------------------------------------------------------------------- Wafer 작업(앱의 rows_for_report 와 같은 후보 순서)
class Wafer:
    __slots__ = ("dev", "group", "report", "lot", "wafer_id", "setup", "roots", "variants", "cands", "flags", "key")

    def __init__(self, dev, group, report, lot, wafer_id, setup, roots, variants):
        self.dev, self.group, self.report = dev, group, report
        self.lot, self.wafer_id, self.setup = lot, wafer_id, setup
        self.roots, self.variants = roots, variants
        rels = [os.path.join(j, setup, lot, wafer_id) for j in variants]
        # 루트 바깥 · Job 후보 안쪽 — 첫 non-missing(ok 또는 error)에서 멈춘다(collect.py rows_for_report)
        self.cands = [(ri, vi, os.path.join(root, rel, "WaferInfo.ini")) for ri, root in enumerate(roots) for vi, rel in enumerate(rels)]
        self.flags = [os.path.join(roots[0], rel, "MoveResultFlag") for rel in rels]
        self.key = self.cands[0][2].lower()


def resolve_wafer(w: Wafer, rec: list, stage: str) -> dict:
    """앱과 똑같이 한 장을 푼다. rec 에 작업마다 기록을 붙인다."""
    t = time.perf_counter()
    win = None
    for ri, vi, path in w.cands:
        res, ms, n, err = op_open_read(path)
        rec.append({"stage": stage, "g": w.group, "dev": w.dev, "type": "ini", "res": res, "ms": round(ms, 2), "bytes": n,
                    "rank": ri * len(w.variants) + vi, "ri": ri, "vi": vi, "path": path, "err": err})
        if res != "missing":
            win = (ri, vi, res)
            break
    flag = None
    if win is None:
        for p in w.flags:
            res, ms, _n, err = op_isfile(p)
            rec.append({"stage": stage, "g": w.group, "dev": w.dev, "type": "flag", "res": res, "ms": round(ms, 2), "path": p, "err": err})
            if res == "ok":
                flag = True
                break
    return {"win": win, "flag": flag, "ms": ms_since(t)}


# ----------------------------------------------------------------------------- 단계들
def stage_env(cfg, out) -> None:
    env = {"platform": platform.platform(), "python": sys.version, "exe": sys.executable, "cpu_count": os.cpu_count(),
           "app_base": APP_BASE, "bench_version": BENCH_VERSION, "started": dt.datetime.now().isoformat(timespec="seconds")}
    for name in ("VERSION",):
        p = os.path.join(APP_BASE, name)
        if os.path.isfile(p):
            env["app_version_file"] = open(p, encoding="utf-8", errors="replace").read().strip()[:200]
    if os.path.isdir(os.path.join(APP_BASE, ".git")):
        env["git_head"] = run_cmd(["git", "-C", APP_BASE, "rev-parse", "HEAD"], timeout=10).get("out", "").strip()
    out["env"] = env
    out["config"] = {k: cfg.get(k) for k in ("read_workers", "retention_days", "backfill_days", "report_dir", "scan_dir",
                                             "devices_csv", "nas_roots", "scope_devices")}
    out["config"]["scope"] = scope.describe(cfg)
    out["app_constants"] = {"MAX_READ_THREADS": collect.MAX_READ_THREADS, "READ_WORKERS": collect.READ_WORKERS,
                            "FULL_LIST_EVERY_SEC": collect.FULL_LIST_EVERY_SEC, "PATTERN_MAX_DAYS": collect.PATTERN_MAX_DAYS}
    if os.name == "nt":
        ps = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
        out["smb"] = [
            run_cmd(["net", "use"]),
            run_cmd(ps + ["Get-SmbMapping | Select-Object LocalPath,RemotePath,Status | Format-Table -AutoSize | Out-String -Width 300"]),
            run_cmd(ps + ["Get-SmbConnection | Select-Object ServerName,ShareName,Dialect,NumOpens,Encrypted,Signed,Credentials | Format-Table -AutoSize | Out-String -Width 300"]),
            run_cmd(ps + ["Get-SmbClientConfiguration | Select-Object FileNotFoundCacheLifetime,DirectoryCacheLifetime,FileInfoCacheLifetime,EnableMultiChannel,DirectoryCacheEntriesMax,FileInfoCacheEntriesMax,EnableBandwidthThrottling,SessionTimeout | Format-List | Out-String -Width 300"]),
            run_cmd(ps + ["Get-SmbMultichannelConnection | Format-Table -AutoSize | Out-String -Width 300"]),
        ]
    else:
        out["smb"] = [{"note": "Windows 가 아니라 SMB 조회를 건너뜀"}]


def stage_devices(cfg, only, out) -> list:
    t = time.perf_counter()
    devs = devices_mod.resolve_devices(cfg, log)
    if only:
        want = {x.strip().lower() for x in only.split(",") if x.strip()}
        devs = [d for d in devs if str(d["name"]).lower() in want]
    groups = collections.OrderedDict()
    info = []
    for d in devs:
        g = collect.nas_group(d["path"])
        d["_group"] = g
        groups.setdefault(g, []).append(str(d["name"]))
        unc = nas_guard._unc_for_drive(str(d["path"]))
        info.append({"name": d["name"], "path": str(d["path"]), "unc": unc, "group": g, "report_dir": d.get("report_dir"),
                     "scan_dir": d.get("scan_dir"), "scan_dirs": d.get("scan_dirs")})
    n = int(cfg.get("read_workers") or collect.READ_WORKERS)
    ng = max(1, len(groups))
    out["devices"] = info
    out["groups"] = {g: {"devices": names, "app_cap_per_group": max(1, min(n, collect.MAX_READ_THREADS // ng))} for g, names in groups.items()}
    out["devices_ms"] = round(ms_since(t))
    log(f"장비 {len(devs)}대 · NAS 묶음 {len(groups)}개: " + " · ".join(f"{g or '(로컬)'}={len(v)}대" for g, v in groups.items()))
    return devs


def _list_files(d, method: str, days: int = 3):
    rep_dir = os.path.join(str(d["path"]), str(d.get("report_dir") or "Report"))
    t = time.perf_counter()
    if method.startswith("scandir"):
        files = [e for e in nas_guard.scandir(rep_dir)]
        files = [(e.name, e.path, e.stat().st_mtime) for e in files if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
    elif method == "find_all_large_fetch":
        files = [(e.name, e.path, e.stat().st_mtime) for e in nas_guard.find_pattern(rep_dir, "*")
                 if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
    else:  # 날짜 패턴(앱의 증분 목록과 같은 방식)
        now = time.time()
        pats = collect.report_name_patterns(now - days * 86400, now) or []
        seen, files = set(), []
        for p in pats:
            for e in nas_guard.find_pattern(rep_dir, p):
                if e.name not in seen and e.is_file() and e.name.lower().endswith((".htm", ".html")):
                    seen.add(e.name)
                    files.append((e.name, e.path, e.stat().st_mtime))
    return files, ms_since(t)


def stage_listing(devs, out, deadline) -> None:
    """묶음마다 장비 1대에 목록 방식 비교. 순서는 묶음마다 돌려 바꾼다(따뜻한 캐시 편향을 섞는다)."""
    res = []
    methods = ["scandir", "find_all_large_fetch", "find_patterns_3d"] if os.name == "nt" else ["scandir"]
    by_group = collections.OrderedDict()
    for d in devs:
        by_group.setdefault(d["_group"], d)
    for gi, (g, d) in enumerate(by_group.items()):
        if deadline.over():
            break
        order = methods[gi % len(methods):] + methods[:gi % len(methods)]
        for m in order + ["scandir_again"]:
            try:
                files, ms = _list_files(d, m)
                res.append({"group": g, "dev": d["name"], "method": m, "ms": round(ms, 1), "files": len(files)})
                log(f"목록 [{d['name']}] {m}: {len(files)}개 {ms:.0f}ms")
            except Exception as e:  # noqa: BLE001
                res.append({"group": g, "dev": d["name"], "method": m, "error": f"{type(e).__name__}: {e}"})
                log(f"목록 [{d['name']}] {m}: 실패 {e}")
    out["listing"] = res


def stage_reports(devs, cfg, args, out) -> list:
    """장비마다 최근 Report K개 → 파싱 → Wafer 작업. 목록은 최근 며칠 패턴(Windows) 또는 scandir."""
    t = time.perf_counter()
    method = "find_patterns" if os.name == "nt" else "scandir"

    def list_one(d):
        try:
            files, ms = _list_files(d, method, days=args.days)
            if not files and method != "scandir":
                files, ms2 = _list_files(d, "scandir")
                ms += ms2
        except Exception as e:  # noqa: BLE001
            return d, [], 0.0, f"{type(e).__name__}: {e}"
        files.sort(key=lambda x: x[2], reverse=True)
        return d, files[: args.reports_per_device], ms, ""

    listed = run_grouped(devs, lambda d: d["_group"], 8, list_one)
    jobs = []
    for item in listed:
        if item is None or item[0] is None:
            continue
        d, files, ms, err = item
        if err:
            log(f"[{d['name']}] Report 목록 실패: {err}")
        for name, path, mtime in files:
            jobs.append((d, name, path, mtime))
    log(f"Report {len(jobs)}개 읽기(묶음마다 8개 동시)")

    def read_one(job):
        d, name, path, mtime = job
        t1 = time.perf_counter()
        try:
            raw = nas_guard.read_bytes(path)
        except Exception as e:  # noqa: BLE001
            return {"dev": d["name"], "group": d["_group"], "name": name, "error": f"{type(e).__name__}: {e}", "read_ms": ms_since(t1)}
        read_ms = ms_since(t1)
        c0, t2 = time.thread_time(), time.perf_counter()
        sha = hashlib.sha256(raw).hexdigest()
        try:
            rep = collect.parse_report(name, collect._decode_report(raw))
        except Exception as e:  # noqa: BLE001
            return {"dev": d["name"], "group": d["_group"], "name": name, "error": f"parse {type(e).__name__}: {e}", "read_ms": read_ms}
        return {"dev": d["name"], "group": d["_group"], "name": name, "bytes": len(raw), "read_ms": read_ms,
                "parse_ms": ms_since(t2), "parse_cpu_ms": (time.thread_time() - c0) * 1000, "sha": sha[:12], "rep": rep, "d": d}

    got = run_grouped(jobs, lambda j: j[0]["_group"], 8, read_one)
    wafers, seen, rstats = [], set(), []
    counts = collections.Counter()
    for r in got:
        if not isinstance(r, dict):
            continue
        rstats.append({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k not in ("rep", "d")})
        if "rep" not in r:
            continue
        rep, d = r["rep"], r["d"]
        scan_root = os.path.join(str(d["path"]), str(d.get("scan_dir") or cfg.get("scan_dir") or "Scanresult"))
        backups = collect._backup_roots(d, scan_root)
        b_start = collect.parse_dt(rep["summary"].get("Batch Start", ""))
        roots = collect.ini_roots_for(b_start, scan_root, backups)
        variants = collect.job_folder_variants(rep["equipment"])
        for w in rep["wafers"]:
            counts["rows"] += 1
            if collect._is_placeholder(w):
                counts["placeholder"] += 1
                continue
            if not variants:
                counts["job_unknown"] += 1
                continue
            wf = Wafer(d["name"], d["_group"], r["name"], w["lot"], w["wafer_id"], rep["process_code"], roots, variants)
            if wf.key in seen:
                counts["dup_path"] += 1
                continue
            seen.add(wf.key)
            wafers.append(wf)
    out["reports"] = {"ms": round(ms_since(t)), "n": len(rstats), "list_method": method, "counts": dict(counts),
                      "read_ms": dist([x.get("read_ms") for x in rstats]), "parse_ms": dist([x.get("parse_ms") for x in rstats]),
                      "parse_cpu_ms": dist([x.get("parse_cpu_ms") for x in rstats]), "bytes": dist([x.get("bytes") for x in rstats]),
                      "errors": [x for x in rstats if x.get("error")][:50],
                      "per_group": {g: {"reports": sum(1 for x in rstats if x.get("group") == g),
                                        "read_ms": dist([x.get("read_ms") for x in rstats if x.get("group") == g])}
                                    for g in dict.fromkeys(x.get("group") for x in rstats)},
                      "candidates_per_wafer": dist([len(w.cands) for w in wafers]),
                      "roots_per_wafer": dist([len(w.roots) for w in wafers]), "variants_per_wafer": dist([len(w.variants) for w in wafers])}
    log(f"Report {len(rstats)}개 · Wafer 작업 {len(wafers)}개 ({out['reports']['ms']/1000:.0f}초)")
    return wafers


def allocate(wafers, args, seed):
    """묶음마다 Report 단위로 섞어 직렬(serial) · API · 동시성(sweep) 풀로 나눈다 — 서로 겹치지 않는 경로."""
    rnd = random.Random(seed)
    by_g = collections.OrderedDict()
    for w in wafers:
        by_g.setdefault(w.group, collections.OrderedDict()).setdefault((w.dev, w.report), []).append(w)
    plan = {}
    for g, reps in by_g.items():
        keys = list(reps)
        rnd.shuffle(keys)
        serial, api, pool = [], [], []
        for k in keys:
            if len(serial) < args.serial_wafers:
                serial.extend(reps[k])
            elif len(api) < args.api_wafers:
                api.extend(reps[k])
            else:
                pool.extend(reps[k])
        rnd.shuffle(pool)
        plan[g] = {"serial": serial, "api": api, "pool": pool}
    return plan


def stage_serial(plan, args, out, deadline) -> None:
    """묶음마다 한 줄로 앱과 같은 탐색 → 그 뒤 분석용 부모 폴더 확인 · Lot 나열(표본)."""
    rec, per_w, probes, lot_lists = [], [], {}, []
    for g, p in plan.items():
        if deadline.over():
            log("시간 한도 — 직렬 단계 중단")
            break
        log(f"직렬 [{g or '(로컬)'}] Wafer {len(p['serial'])}장")
        for w in p["serial"]:
            r = resolve_wafer(w, rec, "serial")
            per_w.append((w, r))
    # 분석용 부모 확인(앱에는 없는 요청 — 탐색이 끝난 뒤라 따뜻한 캐시일 수 있다)
    missed = []
    for w, r in per_w:
        n_try = (r["win"][0] * len(w.variants) + r["win"][1]) if r["win"] else len(w.cands)
        for ri, vi, path in w.cands[:n_try]:
            missed.append((w, ri, vi, path))

    def probe(path, level):
        k = path.lower()
        if k not in probes:
            res, ms, _n, err = op_isdir(path)
            probes[k] = {"path": path, "level": level, "res": res, "ms": round(ms, 2), "err": err}
        return probes[k]["res"]

    for w, ri, vi, path in missed:
        if deadline.over():
            break
        wafer_dir = os.path.dirname(path)
        lot_dir = os.path.dirname(wafer_dir)
        setup_dir = os.path.dirname(lot_dir)
        job_dir = os.path.dirname(setup_dir)
        if probe(lot_dir, "lot") == "ok":
            probe(wafer_dir, "wafer")
        elif probe(setup_dir, "setup") != "ok":
            probe(job_dir, "job")
    # C: 있는 Lot 폴더 한 단계 나열(표본)
    lots = [v for v in probes.values() if v["level"] == "lot" and v["res"] == "ok"]
    for v in lots[: max(0, args.lot_list_max)]:
        if deadline.over():
            break
        t = time.perf_counter()
        try:
            n = sum(1 for _ in nas_guard.scandir(v["path"]))
            lot_lists.append({"path": v["path"], "ms": round(ms_since(t), 2), "entries": n})
        except Exception as e:  # noqa: BLE001
            lot_lists.append({"path": v["path"], "ms": round(ms_since(t), 2), "error": f"{type(e).__name__}: {e}"})
    out["serial"] = {"ops": rec, "wafers": len(per_w), "probes": list(probes.values()), "lot_list": lot_lists,
                     "winners": [{"g": w.group, "dev": w.dev, "report": w.report, "lot": w.lot,
                                  "win": list(r["win"][:2]) if r["win"] else None, "res": r["win"][2] if r["win"] else ("flag" if r["flag"] else "none"),
                                  "cands": len(w.cands), "ms": round(r["ms"], 2)} for w, r in per_w]}


def stage_api(plan, out, deadline, seed) -> None:
    """처음 보는 Wafer 의 1순위 INI 경로에 방법을 하나씩(무작위) — 같은 경로를 두 번 만지지 않는다. Lot 의 첫 Wafer 는 부모 폴더 확인도 차갑게."""
    rnd = random.Random(seed + 1)
    methods = list(API_METHODS)
    rec, seen_lot = [], set()
    for g, p in plan.items():
        for w in p["api"]:
            if deadline.over():
                break
            path = w.cands[0][2]
            lot_dir = os.path.dirname(os.path.dirname(path))
            if lot_dir.lower() not in seen_lot:
                seen_lot.add(lot_dir.lower())
                res, ms, _n, err = op_isdir(lot_dir)
                rec.append({"g": g, "method": "parent_isdir_cold", "res": res, "ms": round(ms, 2), "err": err})
            m = rnd.choice(methods)
            res, ms, n, err = API_METHODS[m](path)
            rec.append({"g": g, "method": m, "res": res, "ms": round(ms, 2), "bytes": n, "err": err})
    summ = {}
    for m in methods + ["parent_isdir_cold"]:
        for res in ("ok", "missing", "notdir", "error"):
            xs = [x["ms"] for x in rec if x["method"] == m and x["res"] == res]
            if xs:
                summ[f"{m}:{res}"] = dist(xs)
    out["api"] = {"ops": rec, "summary": summ}
    log("API 비교: " + " · ".join(f"{k} p50 {v['p50']}ms(n{v['n']})" for k, v in summ.items()))


def _run_level(wafers, level: int, stage: str):
    rec: list = []
    lock = threading.Lock()
    c0, t = time.process_time(), time.perf_counter()

    def one(w):
        local: list = []
        r = resolve_wafer(w, local, stage)
        with lock:
            rec.extend(local)
        return r["ms"]

    with ThreadPoolExecutor(max_workers=level) as pool:
        lat = list(pool.map(one, wafers))
    wall = time.perf_counter() - t
    cpu = time.process_time() - c0
    by = collections.defaultdict(list)
    for x in rec:
        by[f"{x['type']}_{x['res']}"].append(x["ms"])
    return {"level": level, "wafers": len(wafers), "ops": len(rec), "wall_s": round(wall, 2),
            "wafers_per_s": round(len(wafers) / wall, 2) if wall else None, "ops_per_s": round(len(rec) / wall, 2) if wall else None,
            "cpu_s": round(cpu, 2), "wafer_ms": dist(lat), "op_ms": {k: dist(v) for k, v in by.items()},
            "errors": sum(1 for x in rec if x["res"] == "error")}


def stage_sweep(plan, args, out, deadline) -> None:
    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    res = []
    for g, p in plan.items():
        pool = list(p["pool"])
        need = len(levels) * 2 + 1                       # 오름 · 내림 · (모든 묶음 동시 몫 1)
        chunk = min(args.sweep_wafers, len(pool) // need) if need else 0
        passes = [("up", levels), ("down", list(reversed(levels)))]
        if chunk < 10:                                   # 부족하면 오름차순만
            chunk = min(args.sweep_wafers, len(pool) // (len(levels) + 1))
            passes = passes[:1]
        if chunk < 5:
            log(f"동시성 [{g or '(로컬)'}] Wafer 가 부족해 건너뜀({len(pool)}장)")
            continue
        for name, lv in passes:
            for level in lv:
                if deadline.over():
                    log("시간 한도 — 동시성 단계 중단")
                    break
                part, pool = pool[:chunk], pool[chunk:]
                r = _run_level(part, level, f"sweep_{name}")
                r.update({"group": g, "pass": name})
                res.append(r)
                log(f"동시성 [{g or '(로컬)'}] {name} {level:2d}개: {r['wafers']}장 {r['wall_s']}초 · {r['wafers_per_s']}장/s · "
                    f"INI ok p50 {r['op_ms'].get('ini_ok', {}).get('p50')}ms p95 {r['op_ms'].get('ini_ok', {}).get('p95')}ms")
        p["pool"] = pool
        p["_chunk"] = chunk
    # 모든 묶음 동시(묶음마다 8개 — 지금 앱과 같은 모양)
    if len(plan) > 1 and not deadline.over():
        parts = {g: p["pool"][: p.get("_chunk", args.sweep_wafers)] for g, p in plan.items() if p.get("_chunk")}
        parts = {g: v for g, v in parts.items() if v}
        if len(parts) > 1:
            log(f"모든 묶음 동시 8개씩: {len(parts)}묶음")
            outs = {}

            def go(g):
                outs[g] = _run_level(parts[g], 8, "sweep_all")

            ths = [threading.Thread(target=go, args=(g,)) for g in parts]
            t = time.perf_counter()
            for th in ths:
                th.start()
            for th in ths:
                th.join()
            wall = time.perf_counter() - t
            for g, r in outs.items():
                r.update({"group": g, "pass": "all_groups_8", "total_wall_s": round(wall, 2)})
                res.append(r)
                log(f"동시(전체) [{g or '(로컬)'}] 8개: {r['wafers_per_s']}장/s")
    out["sweep"] = res


# ----------------------------------------------------------------------------- 분석(추정 — 현장 요청 수 기반)
def analyze(out) -> None:
    a: dict = {}
    s = out.get("serial") or {}
    ops = s.get("ops") or []
    if ops:
        by = collections.defaultdict(list)
        for x in ops:
            by[f"{x['type']}_{x['res']}"].append(x["ms"])
        a["serial_op_ms"] = {k: dist(v) for k, v in by.items()}
        a["serial_ops_per_wafer"] = round(len(ops) / max(1, s.get("wafers", 1)), 3)
        rank = collections.Counter((x["rank"], x["res"]) for x in ops if x["type"] == "ini")
        a["ini_by_rank"] = {f"{r}:{res}": n for (r, res), n in sorted(rank.items())}
        miss_ms = pct(by.get("ini_missing", []), 50) or 0
        # A: 부모 부재로 묶을 수 있는 실패
        probes = {p["path"].lower(): p for p in s.get("probes", [])}
        per_parent = collections.Counter()
        present_parents = collections.Counter()
        job_absent = collections.Counter()
        for x in ops:
            if x["type"] != "ini" or x["res"] != "missing":
                continue
            lot = os.path.dirname(os.path.dirname(x["path"])).lower()
            st = probes.get(lot, {}).get("res")
            if st == "missing":
                per_parent[lot] += 1
                job = os.path.dirname(os.path.dirname(lot)).lower()
                if probes.get(job, {}).get("res") == "missing":
                    job_absent[job] += 1
            elif st == "ok":
                present_parents[lot] += 1
        n_miss = len(by.get("ini_missing", []))
        touched = {os.path.dirname(os.path.dirname(x["path"])).lower() for x in ops if x["type"] == "ini"}
        present_all = len(touched - set(per_parent))           # A0 은 성공하는 Lot 에도 먼저 확인을 붙인다
        a0 = sum(k - 1 for k in per_parent.values()) - present_all
        a1 = sum(k - 2 for k in per_parent.values()) - len(present_parents)
        a2 = sum(k - 2 for k in per_parent.values() if k >= 3) - sum(1 for k in present_parents.values() if k >= 3)
        pr_ms = [p["ms"] for p in s.get("probes", []) if p["level"] == "lot"]
        a["A_parent_absent"] = {
            "ini_missing": n_miss, "missing_under_absent_lot": sum(per_parent.values()), "absent_lots": len(per_parent),
            "missing_under_present_lot": sum(present_parents.values()), "present_lots_with_miss": len(present_parents),
            "k_per_absent_lot": dist(list(per_parent.values())),
            "lots_touched": len(touched), "A0_ops_saved_net": a0, "A1_ops_saved_net": a1, "A2_ops_saved_net_k3": a2,
            "missing_under_absent_job": sum(job_absent.values()), "absent_jobs": len(job_absent),
            "note": "net = 줄어든 INI 실패 open − 늘어난 부모 확인. 시간 = 실패 open p50 × 절감 − 부모 확인 p50 × 확인 수",
            "miss_p50_ms": miss_ms, "lot_probe_ms_warm": dist(pr_ms),
            "wafer_dir_missing_under_present_lot": sum(1 for p in s.get("probes", []) if p["level"] == "wafer" and p["res"] == "missing"),
            "wafer_dir_present_under_present_lot": sum(1 for p in s.get("probes", []) if p["level"] == "wafer" and p["res"] == "ok"),
        }
        # B: 한 Report 안에서 승자(루트, Job 후보)가 섞이는지
        rep = collections.defaultdict(list)
        for w in s.get("winners", []):
            rep[(w["dev"], w["report"])].append(tuple(w["win"]) if w["win"] else None)
        mixed = sum(1 for v in rep.values() if len({x for x in v if x}) > 1)
        wasted = sum(1 for x in ops if x["type"] == "ini" and x["res"] == "missing" and x["rank"] > 0)
        a["B_learned_order"] = {"reports": len(rep), "reports_mixed_winners": mixed,
                                "wins_by_combo": dict(collections.Counter(str(tuple(w["win"])) if w["win"] else w["res"] for w in s.get("winners", []))),
                                "missing_before_later_rank": wasted}
        # C: Lot 나열 비용
        ll = [x for x in s.get("lot_list", []) if "ms" in x and not x.get("error")]
        a["C_lot_list"] = {"n": len(ll), "ms": dist([x["ms"] for x in ll]), "entries": dist([x["entries"] for x in ll])}
    # 동시성 곡선 요약
    sw = out.get("sweep") or []
    curve = collections.defaultdict(dict)
    for r in sw:
        curve[r["group"]][f"{r['pass']}:{r['level']}"] = r["wafers_per_s"]
    a["sweep_wafers_per_s"] = curve
    api = (out.get("api") or {}).get("summary") or {}
    a["api_p50_ms"] = {k: v.get("p50") for k, v in api.items()}
    out["analysis"] = a

    lines = []
    lines.append(f"NAS 묶음 {len(out.get('groups') or {})}개: " + ", ".join(f"{g or '(로컬)'} {len(v['devices'])}대(앱 동시 {v['app_cap_per_group']})"
                                                                     for g, v in (out.get("groups") or {}).items()))
    if a.get("serial_op_ms"):
        so = a["serial_op_ms"]
        lines.append("직렬 INI: 성공 p50 {} ms · 없음 p50 {} ms · Flag p50 {} ms · Wafer 당 요청 {}".format(
            so.get("ini_ok", {}).get("p50"), so.get("ini_missing", {}).get("p50"), so.get("flag_missing", {}).get("p50"),
            a.get("serial_ops_per_wafer")))
    if a.get("A_parent_absent"):
        x = a["A_parent_absent"]
        lines.append(f"A(부모 부재): 실패 {x['ini_missing']} 중 없는 Lot 아래 {x['missing_under_absent_lot']}건 · A1 순절감 {x['A1_ops_saved_net']}요청")
    if a.get("B_learned_order"):
        x = a["B_learned_order"]
        lines.append(f"B: Report {x['reports']}개 중 승자 섞임 {x['reports_mixed_winners']}개 · 앞 순위 실패 {x['missing_before_later_rank']}건")
    for g, c in curve.items():
        lines.append(f"동시성 [{g or '(로컬)'}] 장/s: " + " ".join(f"{k}={v}" for k, v in c.items()))
    out["summary_lines"] = lines


# ----------------------------------------------------------------------------- 대화형 입력(옵션 없이 실행했을 때)
def _ask(prompt: str, default: str = "") -> str:
    shown = f"{prompt} [{default}]: " if default != "" else f"{prompt}: "
    try:
        got = input(shown).strip()
    except EOFError:
        return default
    return got or default


def _ask_int(prompt: str, default: int, lo: int = 0, hi: int = 10 ** 6) -> int:
    while True:
        v = _ask(prompt, str(default))
        try:
            n = int(v)
            if lo <= n <= hi:
                return n
        except ValueError:
            pass
        print(f"  {lo}~{hi} 사이 숫자로 입력해 주세요.")


def _ask_yes(prompt: str, default: bool) -> bool:
    while True:
        v = _ask(prompt + " (y/n)", "y" if default else "n").lower()
        if v in ("y", "yes", "예", "ㅛ"):
            return True
        if v in ("n", "no", "아니오", "ㅜ"):
            return False
        print("  y 또는 n 으로 입력해 주세요.")


def interactive(args) -> bool:
    """옵션 없이 실행하면 필요한 값을 차례로 묻는다. Enter 만 누르면 [기본값]. False 면 실행하지 않는다."""
    print("=" * 64)
    print(" AOI Capacity — NAS 읽기 성능 측정 (읽기 전용, NAS 에는 아무것도 쓰지 않습니다)")
    print(" 값을 묻는 곳에서 Enter 만 누르면 [괄호 안 기본값]을 씁니다.")
    print("=" * 64)
    print(" 1) 기본 측정   — 보통 15~30분(권장)")
    print(" 2) 빠른 측정   — 표본 절반, 보통 8~15분")
    print(" 3) 직접 설정   — 표본 수·동시성 단계를 하나씩 정함")
    mode = _ask_int("측정 방식 번호", 1, 1, 3)
    if mode == 2:
        args.quick = True
    args.devices = _ask("측정할 장비(쉼표로 구분, 예: AOI-1,AOI-9 · 비우면 수집 범위 전체)", "")
    if mode == 3:
        args.days = _ask_int("Report 를 고를 최근 일수", args.days, 1, 60)
        args.reports_per_device = _ask_int("장비마다 읽을 Report 수", args.reports_per_device, 1, 200)
        args.serial_wafers = _ask_int("NAS 묶음마다 한 줄로 잴 Wafer 수", args.serial_wafers, 0, 5000)
        args.api_wafers = _ask_int("NAS 묶음마다 파일 확인 방식 비교 Wafer 수", args.api_wafers, 0, 5000)
        args.skip_listing = not _ask_yes("Report 목록 방식 비교를 할까요", True)
        args.skip_sweep = not _ask_yes("동시성 곡선(1·2·4·8·16개)을 잴까요", True)
        if not args.skip_sweep:
            args.sweep_wafers = _ask_int("동시성 한 단계의 Wafer 수", args.sweep_wafers, 5, 5000)
            while True:
                lv = _ask("동시성 단계(쉼표로 구분)", args.levels)
                try:
                    if all(0 < int(x) <= 64 for x in lv.split(",") if x.strip()):
                        args.levels = lv
                        break
                except ValueError:
                    pass
                print("  1~64 사이 숫자를 쉼표로 구분해 입력해 주세요.")
    lot = _ask_yes("Lot 폴더 한 단계 나열(조사용, 최대 30개)도 할까요", True)
    args.lot_list_max = args.lot_list_max if lot else 0
    args.max_minutes = _ask_int("최대 실행 시간(분) — 넘으면 남은 단계를 건너뜀", int(args.max_minutes), 5, 600)
    print("-" * 64)
    print(f" 방식 {['', '기본', '빠른', '직접 설정'][mode]} · 장비 {args.devices or '수집 범위 전체'} · "
          f"Lot 나열 {'함' if args.lot_list_max else '안 함'} · 최대 {args.max_minutes}분")
    return _ask_yes("이대로 시작할까요", True)


def _pause() -> None:
    """더블클릭으로 연 창이 바로 닫히지 않게."""
    try:
        input("\nEnter 키를 누르면 창을 닫습니다...")
    except EOFError:
        pass


# ----------------------------------------------------------------------------- main
def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(description="AOI Capacity NAS 읽기 성능 현장 측정(읽기 전용)")
    ap.add_argument("--config", default=os.path.join(os.getcwd(), "config.json"), help="없으면 GUI 설정(prefs)을 쓴다")
    ap.add_argument("--out", default="", help="결과 폴더(로컬). 기본 %%LOCALAPPDATA%%\\AOI_Capacity\\bench")
    ap.add_argument("--devices", default="", help="쉼표로 장비 이름 제한(수집 범위 안에서만)")
    ap.add_argument("--days", type=int, default=3, help="Report 를 고를 최근 일수")
    ap.add_argument("--reports-per-device", type=int, default=10)
    ap.add_argument("--serial-wafers", type=int, default=60, help="묶음마다 직렬 특성 Wafer 수")
    ap.add_argument("--api-wafers", type=int, default=40, help="묶음마다 API 비교 Wafer 수")
    ap.add_argument("--sweep-wafers", type=int, default=50, help="동시성 한 단계의 Wafer 수(묶음마다)")
    ap.add_argument("--levels", default="1,2,4,8,16")
    ap.add_argument("--lot-list-max", type=int, default=30, help="조사용 Lot 폴더 나열 표본 수(0 = 안 함)")
    ap.add_argument("--max-minutes", type=float, default=40)
    ap.add_argument("--seed", type=int, default=20260928)
    ap.add_argument("--quick", action="store_true", help="표본 절반")
    ap.add_argument("--skip-sweep", action="store_true")
    ap.add_argument("--skip-listing", action="store_true")
    ap.add_argument("--ask", action="store_true", help="옵션을 주더라도 실행할 때 값을 물어본다")
    args = ap.parse_args(argv)
    raw = sys.argv[1:] if argv is None else list(argv)
    asked = args.ask or (not raw and sys.stdin is not None and sys.stdin.isatty())   # 옵션 없이 실행 → 값을 묻는다
    if asked:
        try:
            go = interactive(args)
        except KeyboardInterrupt:
            go = False
        if not go:
            print("측정을 시작하지 않았습니다.")
            _pause()
            return 1
    rc = _run(args)
    if asked:
        _pause()
    return rc


def _run(args) -> int:
    if args.quick:
        args.reports_per_device = max(3, args.reports_per_device // 2)
        args.serial_wafers, args.api_wafers, args.sweep_wafers = args.serial_wafers // 2, args.api_wafers // 2, args.sweep_wafers // 2

    problems: list = []
    cfg = cli_mod.load_config(args.config, problems)
    if config_mod.fatal(problems):
        for p in config_mod.fatal(problems):
            print("설정 오류:", p.message())
        return 1
    out_dir = args.out or str(paths.data_root() / "bench")
    nas_guard.assert_local(out_dir, nas_guard.expand_roots(nas_guard.roots_for_cfg(cfg)))   # 결과 파일은 NAS 밖에만
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "nas_bench_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    out: dict = {"args": vars(args)}
    deadline = Deadline(args.max_minutes)
    status = "ok"
    try:
        log("환경 조사")
        stage_env(cfg, out)
        devs = stage_devices(cfg, args.devices, out)
        if not devs:
            raise RuntimeError("측정할 장비가 없습니다(수집 범위·연결 확인)")
        if not args.skip_listing:
            stage_listing(devs, out, deadline)
        wafers = stage_reports(devs, cfg, args, out)
        plan = allocate(wafers, args, args.seed)
        out["allocation"] = {g: {k: len(v) for k, v in p.items()} for g, p in plan.items()}
        stage_serial(plan, args, out, deadline)
        stage_api(plan, out, deadline, args.seed)
        if not args.skip_sweep:
            stage_sweep(plan, args, out, deadline)
    except KeyboardInterrupt:
        status = "interrupted"
        log("Ctrl+C — 지금까지 결과를 씁니다")
    except Exception as e:  # noqa: BLE001
        status = "error"
        out["error"] = traceback.format_exc()
        log(f"오류: {e}")
    try:
        analyze(out)
    except Exception:  # noqa: BLE001
        out["analysis_error"] = traceback.format_exc()
    out["status"] = status
    out["elapsed_s"] = round(time.perf_counter() - T0, 1)
    out["log"] = LOG
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print()
    for line in out.get("summary_lines", []):
        print("  " + line)
    print(f"\n결과 파일: {out_path}\n이 파일을 첨부해 주세요.")
    return 0 if status == "ok" else 2


if __name__ == "__main__":
    sys.exit(main())
