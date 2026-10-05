#!/usr/bin/env python
"""AOI Capacity — NAS 읽기 성능 현장 측정 2판(읽기 전용, 결과 파일 한 장, 정밀 모드 약 25~35분).

1판(9/29) 결과로 좁혀진 질문을 **반복·순서 교차·새 경로**로 정확히 잰다:
  L  목록 방식   — NAS 묶음마다 장비 2대 × {scandir · FindFirstFileExW('*',LARGE_FETCH) · 날짜 패턴 3일 · 1일} × 3회,
                   회차마다 순서를 돌려(라틴 방진) 차가운 첫 요청의 편향을 가른다.
  R  Report 읽기 — 묶음마다 앞 몇 개는 한 줄로(순수 비용), 나머지는 앱처럼 8개 동시(경합 비용).
  M  읽기 방식   — 처음 보는 INI 에 방식 하나씩(방식마다 같은 수): open().read() · os.open+read 1회 · CreateFileW+ReadFile ·
                   GetFileAttributesExW · os.stat · isfile · 정확 이름 FindFirstFileExW. 중앙값의 95% 신뢰구간(부트스트랩).
                   같은 경로 즉시 재읽기 · 12초 뒤 재읽기(클라이언트 캐시 효과)도 따로.
  T  시각 일치   — INI 내용의 WaferStart/EndTime 과 INI 파일의 생성·수정 시각, Wafer 폴더 수정 시각(Lot 폴더 한 단계 나열) 비교,
                   그 시각으로 판정했을 때 STALE(시간 근거) 결과가 내용 기준과 같은지, 잃게 되는 UseLot/UseWaferID 검사 수.
  S  동시성      — 묶음마다 혼자 1·2·4·6·8·12·16개 × 3회(오름 → 내림 → 오름, 매번 새 Wafer) → 평균 ± 표준편차.
  G  전 묶음 동시 — 네 묶음을 함께 4·8·12개 × 2회(묶음끼리 간섭).
  C  카나리아    — 측정 내내 묶음마다 15초 간격으로 같은 파일 stat 1번 → NAS 부하의 시간 변화(다른 결과를 해석하는 기준선).
  A  탐색(A·B·C안) — 1판과 같은 직렬 탐색·부모 폴더 확인(작게).
  ★ 실제 수집(메뉴 4 · --real-collect) — 최근 N일(기본 2)을 **앱의 collect.collect 그대로** 수집: 처음(빈 캐시) → 곧바로 다시(증분 ·
    이름 패턴 목록) → 전체 목록 강제(하루 한 번 수집과 같은 모양). 앱이 부르는 NAS 읽기 함수(Report·INI 읽기 · 나열 · isfile/isdir)를
    감싸 요청마다 시간을 재고, 단계별 시간·NAS 별 평균 동시 수·30초 창 타임라인을 남긴다. 캐시·HTML 은 측정용 로컬 폴더에만.

지키는 것(CLAUDE.md 절대 규칙):
  * NAS 는 **읽기만** 한다 — open 은 'rb'/O_RDONLY, CreateFileW 는 GENERIC_READ + OPEN_EXISTING 만. 쓰는 파일은 로컬 결과 JSON 하나
    (`nas_guard.assert_local`). 캐시·결과 HTML·설정은 건드리지 않는다.
  * 장비는 앱과 같은 `devices.resolve_devices`(수집 범위 게이트)만 쓴다.
  * Scanresult 를 재귀 검색하지 않는다 — Report 에서 계산한 정확 경로만. 예외: 조사용 Lot/Wafer 폴더 **한 단계** 나열(T · A 단계,
    `scripts/collect_sample.py` 와 같은 범위) — 옵션 `--no-dir-list` 면 하지 않는다.

실행(현장 PC — 앱과 같은 사용자로, 수집이 돌지 않을 때):
  * 옵션 없이 실행하면(IDE 실행 · 더블클릭) 측정 방식을 묻는다 — Enter 만 누르면 기본값(정밀).
  * git 폴더: python test.py  · 배포본: `AOI_Capacity_Lite\\app\\` 에 두고 ..\\python\\python.exe test.py
  * 옵션으로 바로: python test.py --quick (약 10분) · --ask 를 붙이면 옵션이 있어도 묻는다.
  결과: `%LOCALAPPDATA%\\AOI_Capacity\\bench\\nas_bench_<시각>.json` 한 장을 첨부. Ctrl+C 로 멈춰도 그때까지 결과를 쓴다.
  결과에는 장비 경로·Job·Lot·Wafer 이름이 들어간다(분석용). `--max-minutes`(기본 50)를 넘으면 남은 단계를 건너뛴다.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import itertools
import json
import os
import platform
import random
import stat as stat_mod
import statistics
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

BENCH_VERSION = 2
MISSING_EXC = (FileNotFoundError, NotADirectoryError, IsADirectoryError)
IS_WIN = os.name == "nt"


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


def now_s() -> float:
    return round(time.perf_counter() - T0, 2)


def pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 2)


def med_ci(xs, n: int = 400, seed: int = 7):
    """중앙값의 95% 부트스트랩 신뢰구간."""
    xs = [x for x in xs if x is not None]
    if len(xs) < 5:
        return None
    rnd = random.Random(seed)
    meds = sorted(statistics.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return [round(meds[int(0.025 * n)], 2), round(meds[int(0.975 * n) - 1], 2)]


def dist(xs, ci: bool = False) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    out = {"n": len(xs), "mean": round(statistics.fmean(xs), 2), "p05": pct(xs, 5), "p50": pct(xs, 50), "p90": pct(xs, 90),
           "p95": pct(xs, 95), "p99": pct(xs, 99), "max": round(max(xs), 2), "min": round(min(xs), 2), "sum": round(sum(xs), 1)}
    if len(xs) > 1:
        out["sd"] = round(statistics.stdev(xs), 2)
    if ci:
        out["p50_ci95"] = med_ci(xs)
    return out


def ms_since(t: float) -> float:
    return (time.perf_counter() - t) * 1000.0


class Deadline:
    def __init__(self, minutes: float) -> None:
        self.end = time.perf_counter() + minutes * 60

    def over(self) -> bool:
        return time.perf_counter() >= self.end


def run_cmd(args, timeout=40) -> dict:
    """조회용 명령(net use · PowerShell Get-*). 실패해도 계속한다."""
    t = time.perf_counter()
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout)
        out = p.stdout.decode("utf-8", "replace") if p.stdout else ""
        if "�" in out and IS_WIN:
            out = p.stdout.decode("cp949", "replace")
        err = p.stderr.decode("utf-8", "replace") if p.stderr else ""
        if "�" in err and IS_WIN:
            err = p.stderr.decode("cp949", "replace")
        return {"cmd": " ".join(args), "rc": p.returncode, "ms": round(ms_since(t)), "out": out[-20000:], "err": err[-3000:]}
    except Exception as e:  # noqa: BLE001
        return {"cmd": " ".join(args), "error": f"{type(e).__name__}: {e}"}


# ----------------------------------------------------------------------------- Win32(읽기 전용)
_W = None


def _win():
    global _W
    if _W is None:
        import ctypes
        from ctypes import wintypes as wt

        k = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        k.GetFileAttributesExW.argtypes = [wt.LPCWSTR, ctypes.c_int, ctypes.c_void_p]
        k.GetFileAttributesExW.restype = wt.BOOL
        k.FindFirstFileExW.argtypes = [wt.LPCWSTR, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, wt.DWORD]
        k.FindFirstFileExW.restype = wt.HANDLE
        k.FindNextFileW.argtypes = [wt.HANDLE, ctypes.c_void_p]
        k.FindNextFileW.restype = wt.BOOL
        k.FindClose.argtypes = [wt.HANDLE]
        k.FindClose.restype = wt.BOOL
        k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
        k.CreateFileW.restype = wt.HANDLE
        k.ReadFile.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD), ctypes.c_void_p]
        k.ReadFile.restype = wt.BOOL
        k.CloseHandle.argtypes = [wt.HANDLE]
        k.CloseHandle.restype = wt.BOOL

        class FT(ctypes.Structure):
            _fields_ = [("lo", wt.DWORD), ("hi", wt.DWORD)]

        class FAD(ctypes.Structure):
            _fields_ = [("attr", wt.DWORD), ("ctime", FT), ("atime", FT), ("mtime", FT), ("size_hi", wt.DWORD), ("size_lo", wt.DWORD)]

        class FD(ctypes.Structure):
            _fields_ = [("attr", wt.DWORD), ("ctime", FT), ("atime", FT), ("mtime", FT), ("size_hi", wt.DWORD), ("size_lo", wt.DWORD),
                        ("r0", wt.DWORD), ("r1", wt.DWORD), ("name", wt.WCHAR * 260), ("alt", wt.WCHAR * 14)]

        _W = {"k": k, "ct": ctypes, "wt": wt, "FAD": FAD, "FD": FD, "INVALID": wt.HANDLE(-1).value}
    return _W


def _ft(ft):
    t = (int(ft.hi) << 32) | int(ft.lo)
    return (t - 116444736000000000) / 1e7 if t else None


def win_find(dir_path: str, pattern: str = "*"):
    """FindFirstFileExW(BASIC, LARGE_FETCH) 한 단계 나열 → [{name, dir, ctime, mtime, size}] (읽기 전용). 폴더가 없으면 FileNotFoundError."""
    if not IS_WIN:                                    # 개발 PC 확인용 — 같은 모양으로 os.scandir
        import fnmatch
        out = []
        for e in os.scandir(dir_path):
            if fnmatch.fnmatch(e.name, pattern):
                st = e.stat()
                out.append({"name": e.name, "dir": e.is_dir(), "ctime": st.st_ctime, "mtime": st.st_mtime, "size": st.st_size})
        return out
    W = _win()
    k, ct = W["k"], W["ct"]
    d = W["FD"]()
    h = k.FindFirstFileExW(os.path.join(dir_path, pattern), 1, ct.byref(d), 0, None, 2)
    if h is None or h == W["INVALID"]:
        err = ct.get_last_error()
        if err in (2, 18):
            return []
        if err == 3:
            raise FileNotFoundError(dir_path)
        raise ct.WinError(err)
    out = []
    try:
        while True:
            if d.name not in (".", ".."):
                out.append({"name": d.name, "dir": bool(d.attr & 0x10), "ctime": _ft(d.ctime), "mtime": _ft(d.mtime),
                            "size": (int(d.size_hi) << 32) | int(d.size_lo)})
            if not k.FindNextFileW(h, ct.byref(d)):
                err = ct.get_last_error()
                if err == 18:
                    break
                raise ct.WinError(err)
    finally:
        k.FindClose(h)
    return out


def file_times(path: str):
    """→ (결과, ms, {ctime, mtime, size}) — Windows 는 GetFileAttributesExW(생성·수정 시각), 그 밖은 os.stat."""
    t = time.perf_counter()
    if IS_WIN:
        W = _win()
        d = W["FAD"]()
        ok = W["k"].GetFileAttributesExW(path, 0, W["ct"].byref(d))
        ms = ms_since(t)
        if ok:
            return "ok", ms, {"ctime": _ft(d.ctime), "mtime": _ft(d.mtime), "size": (int(d.size_hi) << 32) | int(d.size_lo)}
        err = W["ct"].get_last_error()
        return ("missing" if err in (2, 3) else "error"), ms, {"err": f"WinError {err}"}
    try:
        st = os.stat(path)
        return "ok", ms_since(t), {"ctime": st.st_ctime, "mtime": st.st_mtime, "size": st.st_size}
    except MISSING_EXC:
        return "missing", ms_since(t), {}
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), {"err": f"{type(e).__name__}: {e}"}


# ----------------------------------------------------------------------------- 읽기 방식(각각 → 결과, ms, bytes, 오류[, data])
def op_open_read(path: str, keep: bool = False):
    """앱과 같은 방식(open 'rb' 전체 읽기)."""
    t = time.perf_counter()
    try:
        with open(path, "rb") as f:
            data = f.read()
        return "ok", ms_since(t), len(data), "", (data if keep else None)
    except MISSING_EXC:
        return "missing", ms_since(t), 0, "", None
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}", None


def op_os_read_once(path: str):
    t = time.perf_counter()
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
        try:
            n = len(os.read(fd, 1 << 20))
        finally:
            os.close(fd)
        return "ok", ms_since(t), n, "", None
    except MISSING_EXC:
        return "missing", ms_since(t), 0, "", None
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}", None


def op_win_createfile_read(path: str):
    """CreateFileW(GENERIC_READ, 공유 읽기·쓰기·삭제, OPEN_EXISTING, SEQUENTIAL_SCAN) + ReadFile 64KB 반복 — 읽기 전용."""
    W = _win()
    k, ct, wt = W["k"], W["ct"], W["wt"]
    t = time.perf_counter()
    h = k.CreateFileW(path, 0x80000000, 0x7, None, 3, 0x80 | 0x08000000, None)
    if h is None or h == W["INVALID"]:
        err = ct.get_last_error()
        return ("missing" if err in (2, 3) else "error"), ms_since(t), 0, ("" if err in (2, 3) else f"WinError {err}"), None
    total = 0
    try:
        buf = ct.create_string_buffer(65536)
        got = wt.DWORD(0)
        while True:
            if not k.ReadFile(h, buf, 65536, ct.byref(got), None):
                return "error", ms_since(t), total, f"WinError {ct.get_last_error()}", None
            if got.value == 0:
                break
            total += got.value
            if got.value < 65536:
                break
    finally:
        k.CloseHandle(h)
    return "ok", ms_since(t), total, "", None


def op_stat(path: str):
    t = time.perf_counter()
    try:
        os.stat(path)
        return "ok", ms_since(t), 0, "", None
    except MISSING_EXC:
        return "missing", ms_since(t), 0, "", None
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}", None


def op_isfile(path: str):
    t = time.perf_counter()
    r = os.path.isfile(path)
    return ("ok" if r else "missing"), ms_since(t), 0, "", None


def op_getattr(path: str):
    res, ms, info = file_times(path)
    return res, ms, 0, info.get("err", ""), None


def op_find_exact(path: str):
    t = time.perf_counter()
    try:
        got = win_find(os.path.dirname(path), os.path.basename(path))
        return ("ok" if got else "missing"), ms_since(t), 0, "", None
    except MISSING_EXC:
        return "missing", ms_since(t), 0, "", None
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}", None


def op_isdir(path: str):
    """폴더 존재 확인 — stat 으로 오류(권한 등)와 부재를 가른다."""
    t = time.perf_counter()
    try:
        st = os.stat(path)
        return ("ok" if stat_mod.S_ISDIR(st.st_mode) else "notdir"), ms_since(t), 0, "", None
    except MISSING_EXC:
        return "missing", ms_since(t), 0, "", None
    except Exception as e:  # noqa: BLE001
        return "error", ms_since(t), 0, f"{type(e).__name__}: {e}", None


READ_METHODS = {"py_open_read": op_open_read, "os_read_once": op_os_read_once, "os_stat": op_stat, "isfile": op_isfile}
if IS_WIN:
    READ_METHODS.update({"win_createfile_read": op_win_createfile_read, "win_getattr": op_getattr, "win_find_exact": op_find_exact})


def parse_ini_bytes(raw: bytes) -> dict:
    """collect.read_ini 와 같은 규칙으로 이미 읽은 바이트를 푼다(다시 열지 않는다)."""
    out: dict = {}
    sec = ""
    for line in raw.decode("utf-8", "replace").splitlines():
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
        if sec in collect.INI_KEYS and k in collect.INI_KEYS[sec]:
            out[sec][k] = v.strip()
    return out


# ----------------------------------------------------------------------------- 묶음별 동시 실행(앱의 _run 과 같은 모양)
def run_grouped(items, group_of, per_group: int, fn):
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
    if not lanes:
        return results
    with ThreadPoolExecutor(max_workers=max(1, sum(k for _, k in lanes)), thread_name_prefix="bench") as pool:
        for f in [pool.submit(lane, q) for q, k in lanes for _ in range(k)]:
            f.result()
    return results


# ----------------------------------------------------------------------------- Wafer 작업(앱의 rows_for_report 와 같은 후보 순서)
class Wafer:
    __slots__ = ("dev", "group", "report", "lot", "wafer_id", "setup", "roots", "variants", "cands", "flags", "key", "b_start", "b_end")

    def __init__(self, dev, group, report, lot, wafer_id, setup, roots, variants, b_start, b_end):
        self.dev, self.group, self.report = dev, group, report
        self.lot, self.wafer_id, self.setup = lot, wafer_id, setup
        self.roots, self.variants, self.b_start, self.b_end = roots, variants, b_start, b_end
        rels = [os.path.join(j, setup, lot, wafer_id) for j in variants]
        # 루트 바깥 · Job 후보 안쪽 — 첫 non-missing(ok 또는 error)에서 멈춘다(collect.py rows_for_report)
        self.cands = [(ri, vi, os.path.join(root, rel, "WaferInfo.ini")) for ri, root in enumerate(roots) for vi, rel in enumerate(rels)]
        self.flags = [os.path.join(roots[0], rel, "MoveResultFlag") for rel in rels]
        self.key = self.cands[0][2].lower()


def resolve_wafer(w: Wafer, rec: list, stage: str, keep: bool = False) -> dict:
    """앱과 똑같이 한 장을 푼다. rec 에 작업마다 기록을 붙인다."""
    t = time.perf_counter()
    win, data, path_ok = None, None, None
    for ri, vi, path in w.cands:
        res, ms, n, err, raw = op_open_read(path, keep)
        rec.append({"stage": stage, "g": w.group, "dev": w.dev, "t": now_s(), "type": "ini", "res": res, "ms": round(ms, 2), "bytes": n,
                    "rank": ri * len(w.variants) + vi, "ri": ri, "vi": vi, "path": path, "err": err})
        if res != "missing":
            win, data, path_ok = (ri, vi, res), raw, path
            break
    flag = None
    if win is None:
        for p in w.flags:
            res, ms, _n, err, _ = op_isfile(p)
            rec.append({"stage": stage, "g": w.group, "dev": w.dev, "t": now_s(), "type": "flag", "res": res, "ms": round(ms, 2),
                        "path": p, "err": err})
            if res == "ok":
                flag = True
                break
    return {"win": win, "flag": flag, "ms": ms_since(t), "data": data, "path": path_ok}


# ----------------------------------------------------------------------------- C: 카나리아(측정 내내 NAS 부하 기준선)
class Canary:
    def __init__(self, targets: dict, every: float) -> None:
        self.targets, self.every = targets, every
        self.rec: list = []
        self.stop = threading.Event()
        self.th = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop.wait(self.every):
            for g, path in self.targets.items():
                res, ms, _n, err, _ = op_stat(path)
                self.rec.append({"g": g, "t": now_s(), "res": res, "ms": round(ms, 2), "err": err})

    def start(self):
        if self.targets:
            self.th.start()
        return self

    def finish(self) -> list:
        self.stop.set()
        if self.th.is_alive():
            self.th.join(timeout=30)
        return self.rec


# ----------------------------------------------------------------------------- 단계: 환경 · 장비
def stage_env(cfg, out) -> None:
    env = {"platform": platform.platform(), "python": sys.version, "exe": sys.executable, "cpu_count": os.cpu_count(),
           "app_base": APP_BASE, "bench_version": BENCH_VERSION, "started": dt.datetime.now().isoformat(timespec="seconds"),
           "tz_offset_min": round(dt.datetime.now().astimezone().utcoffset().total_seconds() / 60)}
    p = os.path.join(APP_BASE, "VERSION")
    if os.path.isfile(p):
        env["app_version_file"] = open(p, encoding="utf-8", errors="replace").read().strip()[:200]
    if os.path.isdir(os.path.join(APP_BASE, ".git")):
        env["git_head"] = run_cmd(["git", "-C", APP_BASE, "rev-parse", "HEAD"], timeout=10).get("out", "").strip()
    out["env"] = env
    out["config"] = {k: cfg.get(k) for k in ("read_workers", "retention_days", "backfill_days", "report_dir", "scan_dir", "devices_csv")}
    out["config"]["scope"] = scope.describe(cfg)
    out["app_constants"] = {"MAX_READ_THREADS": collect.MAX_READ_THREADS, "READ_WORKERS": collect.READ_WORKERS,
                            "FULL_LIST_EVERY_SEC": collect.FULL_LIST_EVERY_SEC, "PATTERN_MAX_DAYS": collect.PATTERN_MAX_DAYS}
    if IS_WIN:
        ps = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
        out["smb"] = [
            run_cmd(["net", "use"]),
            run_cmd(ps + ["Get-SmbClientConfiguration | Select-Object FileNotFoundCacheLifetime,DirectoryCacheLifetime,FileInfoCacheLifetime,EnableMultiChannel,DirectoryCacheEntriesMax,FileInfoCacheEntriesMax,EnableBandwidthThrottling,SessionTimeout,EnableLargeMtu,MaxCmds | Format-List | Out-String -Width 300"]),
            run_cmd(ps + ["Get-NetAdapter | Where-Object Status -eq Up | Select-Object Name,InterfaceDescription,LinkSpeed | Format-Table -AutoSize | Out-String -Width 300"]),
            run_cmd(ps + ["Get-MpComputerStatus | Select-Object AMRunningMode,RealTimeProtectionEnabled,OnAccessProtectionEnabled | Format-List | Out-String -Width 300"]),
        ]
        out["ping"] = {}
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
        info.append({"name": d["name"], "path": str(d["path"]), "unc": nas_guard._unc_for_drive(str(d["path"])), "group": g,
                     "report_dir": d.get("report_dir"), "scan_dir": d.get("scan_dir"), "scan_dirs": d.get("scan_dirs")})
    n = int(cfg.get("read_workers") or collect.READ_WORKERS)
    ng = max(1, len(groups))
    out["devices"] = info
    out["groups"] = {g: {"devices": names, "app_cap_per_group": max(1, min(n, collect.MAX_READ_THREADS // ng))} for g, names in groups.items()}
    out["devices_ms"] = round(ms_since(t))
    if IS_WIN:
        for g in groups:
            if g and all(c.isdigit() or c == "." for c in g):
                out["ping"][g] = run_cmd(["ping", "-n", "10", g], timeout=40).get("out", "")[-600:]
    log(f"장비 {len(devs)}대 · NAS 묶음 {len(groups)}개: " + " · ".join(f"{g or '(로컬)'}={len(v)}대" for g, v in groups.items()))
    return devs


# ----------------------------------------------------------------------------- L: 목록 방식(반복 · 순서 교차)
def _list_files(d, method: str):
    rep_dir = os.path.join(str(d["path"]), str(d.get("report_dir") or "Report"))
    t = time.perf_counter()
    if method == "scandir":
        files = [(e.name, e.path, e.stat().st_mtime) for e in nas_guard.scandir(rep_dir)
                 if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
    elif method == "large_fetch":
        files = [(x["name"], os.path.join(rep_dir, x["name"]), x["mtime"]) for x in win_find(rep_dir, "*")
                 if not x["dir"] and x["name"].lower().endswith((".htm", ".html"))]
    else:  # pattern_<n>d — 앱의 증분 목록과 같은 방식
        days = int(method.split("_")[1][:-1])
        now = time.time()
        pats = collect.report_name_patterns(now - days * 86400, now) or []
        seen, files = set(), []
        for p in pats:
            for x in win_find(rep_dir, p):
                if x["name"] not in seen and not x["dir"] and x["name"].lower().endswith((".htm", ".html")):
                    seen.add(x["name"])
                    files.append((x["name"], os.path.join(rep_dir, x["name"]), x["mtime"]))
    return files, ms_since(t)


def stage_listing(devs, args, out, deadline) -> None:
    methods = ["scandir", "large_fetch", "pattern_3d", "pattern_1d"] if IS_WIN else ["scandir"]
    by_group = collections.OrderedDict()
    for d in devs:
        by_group.setdefault(d["_group"], []).append(d)
    picks = []
    for g, ds in by_group.items():
        idx = sorted({0, len(ds) // 2, len(ds) - 1})[: args.list_devices]
        picks.extend(ds[i] for i in idx)
    res = []
    for r in range(args.list_rounds):
        for di, d in enumerate(picks):                 # 장비를 번갈아 → 같은 장비의 다음 방식까지 시간 간격이 생긴다
            if deadline.over():
                log("시간 한도 — 목록 단계 중단")
                out["listing"] = res
                return
            k = (r + di) % len(methods)
            order = methods[k:] + methods[:k]          # 라틴 방진: 회차·장비마다 첫 방식이 바뀐다
            for pos, m in enumerate(order):
                try:
                    files, ms = _list_files(d, m)
                    res.append({"group": d["_group"], "dev": d["name"], "round": r, "pos": pos, "method": m, "ms": round(ms, 1),
                                "files": len(files), "t": now_s()})
                except Exception as e:  # noqa: BLE001
                    res.append({"group": d["_group"], "dev": d["name"], "round": r, "pos": pos, "method": m,
                                "error": f"{type(e).__name__}: {e}", "t": now_s()})
        log(f"목록 {r + 1}회차 끝(장비 {len(picks)}대 × 방식 {len(methods)}개)")
    out["listing"] = res


# ----------------------------------------------------------------------------- R: Report 읽기 → Wafer 작업
def stage_reports(devs, cfg, args, out) -> list:
    t = time.perf_counter()
    method = f"pattern_{args.days}d" if IS_WIN else "scandir"

    def list_one(d):
        try:
            files, ms = _list_files(d, method)
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
        if not item or item[0] is None:
            continue
        d, files, _ms, err = item
        if err:
            log(f"[{d['name']}] Report 목록 실패: {err}")
        jobs.extend((d, name, path, mtime) for name, path, mtime in files)

    def read_one(job, mode):
        d, name, path, _mtime = job
        t1 = time.perf_counter()
        try:
            raw = nas_guard.read_bytes(path)
        except Exception as e:  # noqa: BLE001
            return {"dev": d["name"], "group": d["_group"], "name": name, "mode": mode, "error": f"{type(e).__name__}: {e}", "read_ms": ms_since(t1)}
        read_ms = ms_since(t1)
        c0, t2 = time.thread_time(), time.perf_counter()
        hashlib.sha256(raw).hexdigest()
        try:
            rep = collect.parse_report(name, collect._decode_report(raw))
        except Exception as e:  # noqa: BLE001
            return {"dev": d["name"], "group": d["_group"], "name": name, "mode": mode, "error": f"parse {type(e).__name__}: {e}", "read_ms": read_ms}
        return {"dev": d["name"], "group": d["_group"], "name": name, "mode": mode, "bytes": len(raw), "read_ms": read_ms,
                "parse_ms": ms_since(t2), "parse_cpu_ms": (time.thread_time() - c0) * 1000, "rep": rep, "d": d, "t": now_s()}

    # 묶음마다 앞 몇 개는 한 줄로(순수 비용) — 묶음끼리도 차례로
    rnd = random.Random(args.seed + 5)
    rnd.shuffle(jobs)
    serial_jobs, taken = [], collections.Counter()
    rest = []
    for j in jobs:
        if taken[j[0]["_group"]] < args.serial_reports:
            taken[j[0]["_group"]] += 1
            serial_jobs.append(j)
        else:
            rest.append(j)
    log(f"Report 한 줄 읽기 {len(serial_jobs)}개 → 8개 동시 {len(rest)}개")
    got = [read_one(j, "serial") for j in serial_jobs]
    got += [r for r in run_grouped(rest, lambda j: j[0]["_group"], 8, lambda j: read_one(j, "par8")) if isinstance(r, dict)]
    wafers, seen, rstats = [], set(), []
    counts = collections.Counter()
    for r in got:
        rstats.append({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items() if k not in ("rep", "d")})
        if "rep" not in r:
            continue
        rep, d = r["rep"], r["d"]
        scan_root = os.path.join(str(d["path"]), str(d.get("scan_dir") or cfg.get("scan_dir") or "Scanresult"))
        backups = collect._backup_roots(d, scan_root)
        b_start = collect.parse_dt(rep["summary"].get("Batch Start", ""))
        b_end = collect.parse_dt(rep["summary"].get("Batch End", ""))
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
            wf = Wafer(d["name"], d["_group"], r["name"], w["lot"], w["wafer_id"], rep["process_code"], roots, variants, b_start, b_end)
            if wf.key in seen:
                counts["dup_path"] += 1
                continue
            seen.add(wf.key)
            wafers.append(wf)
    per_group = {}
    for g in dict.fromkeys(x.get("group") for x in rstats):
        xs = [x for x in rstats if x.get("group") == g]
        per_group[g] = {m: {"read_ms": dist([x.get("read_ms") for x in xs if x.get("mode") == m], ci=True),
                            "bytes": dist([x.get("bytes") for x in xs if x.get("mode") == m])} for m in ("serial", "par8")}
    out["reports"] = {"ms": round(ms_since(t)), "n": len(rstats), "list_method": method, "counts": dict(counts),
                      "parse_ms": dist([x.get("parse_ms") for x in rstats]), "parse_cpu_ms": dist([x.get("parse_cpu_ms") for x in rstats]),
                      "errors": [x for x in rstats if x.get("error")][:50], "per_group": per_group,
                      "items": [{k: x.get(k) for k in ("group", "dev", "mode", "bytes", "read_ms", "t")} for x in rstats],
                      "candidates_per_wafer": dist([len(w.cands) for w in wafers]),
                      "roots_per_wafer": dist([len(w.roots) for w in wafers]), "variants_per_wafer": dist([len(w.variants) for w in wafers])}
    log(f"Report {len(rstats)}개 · Wafer 작업 {len(wafers)}개 ({out['reports']['ms'] / 1000:.0f}초)")
    return wafers


def allocate(wafers, args):
    """묶음마다 Report 단위로 섞어 단계별 풀로 나눈다 — 단계끼리 같은 경로를 만지지 않는다."""
    rnd = random.Random(args.seed)
    by_g = collections.OrderedDict()
    for w in wafers:
        by_g.setdefault(w.group, collections.OrderedDict()).setdefault((w.dev, w.report), []).append(w)
    plan = {}
    for g, reps in by_g.items():
        keys = list(reps)
        rnd.shuffle(keys)
        want = [("methods", args.method_wafers), ("times", args.time_wafers), ("serial", args.serial_wafers)]
        buckets = {k: [] for k, _ in want}
        pool = []
        for key in keys:
            for name, n in want:
                if len(buckets[name]) < n:
                    buckets[name].extend(reps[key])
                    break
            else:
                pool.extend(reps[key])
        rnd.shuffle(pool)
        buckets["pool"] = pool
        plan[g] = buckets
    return plan


# ----------------------------------------------------------------------------- M: 읽기 방식
def stage_methods(plan, args, out, deadline) -> None:
    rnd = random.Random(args.seed + 1)
    methods = list(READ_METHODS)
    rec = []
    for g, p in plan.items():
        ws = list(p["methods"])
        assign = [methods[i % len(methods)] for i in range(len(ws))]
        rnd.shuffle(assign)                               # 방식마다 같은 수, 순서는 무작위
        for w, m in zip(ws, assign):
            if deadline.over():
                break
            path = w.cands[0][2]
            res, ms, n, err, _ = READ_METHODS[m](path)
            rec.append({"g": g, "dev": w.dev, "method": m, "res": res, "ms": round(ms, 2), "bytes": n, "err": err, "t": now_s()})
        log(f"읽기 방식 [{g or '(로컬)'}] {len(ws)}개")
    # 캐시 효과: 처음 보는 경로(동시성 풀에서 따로 뗌)를 차갑게 → 곧바로 → 12초 뒤(FileInfo 캐시 10초 넘김) 다시 읽는다
    warm, fresh = [], {g: [w.cands[0][2] for w in _take(p, args.warm_paths)] for g, p in plan.items()}
    for g, ps in fresh.items():
        for path in ps:
            for kind in ("cold", "again_now"):
                res, ms, *_ = op_open_read(path)
                warm.append({"g": g, "kind": kind, "res": res, "ms": round(ms, 2), "path": path})
    if warm and not deadline.over():
        time.sleep(12)
        for g, ps in fresh.items():
            for path in ps:
                res, ms, *_ = op_open_read(path)
                warm.append({"g": g, "kind": "again_12s", "res": res, "ms": round(ms, 2), "path": path})
    summ = {}
    for m in methods:
        for res in ("ok", "missing", "error"):
            xs = [x["ms"] for x in rec if x["method"] == m and x["res"] == res]
            if xs:
                summ[f"{m}:{res}"] = dist(xs, ci=True)
    per_group = {}
    for g in plan:
        per_group[g] = {m: dist([x["ms"] for x in rec if x["g"] == g and x["method"] == m and x["res"] == "ok"], ci=True) for m in methods}
    wsum = {f"{k}:{res}": dist([x["ms"] for x in warm if x["kind"] == k and x["res"] == res])
            for k in ("cold", "again_now", "again_12s") for res in ("ok", "missing")}
    out["methods"] = {"ops": rec, "summary": summ, "per_group_ok": per_group, "warm": warm, "warm_summary": wsum}
    log("읽기 방식(있는 파일 p50): " + " · ".join(f"{k.split(':')[0]} {v['p50']}ms" for k, v in summ.items() if k.endswith(":ok")))


# ----------------------------------------------------------------------------- T: 시각 일치
def _dt_of(epoch):
    return dt.datetime.fromtimestamp(epoch) if epoch else None


def _diff(a, b):
    return round((a - b).total_seconds(), 1) if (a and b) else None


def stage_times(plan, args, out, deadline) -> None:
    rec, lots = [], []
    for g, p in plan.items():
        lot_dirs = collections.OrderedDict()
        for w in p["times"]:
            if deadline.over():
                break
            local: list = []
            r = resolve_wafer(w, local, "times", keep=True)
            item = {"g": g, "dev": w.dev, "report": w.report, "lot": w.lot, "wafer": w.wafer_id, "res": r["win"][2] if r["win"] else "none"}
            if r["win"] and r["win"][2] == "ok" and r["data"] is not None:
                ini = parse_ini_bytes(r["data"])
                a = ini.get("AutoCycleInfo", {})
                st, en = collect.parse_dt(a.get("WaferStartTime", "")), collect.parse_dt(a.get("WaferEndTime", ""))
                fres, fms, finfo = file_times(r["path"])
                ct, mt = _dt_of(finfo.get("ctime")), _dt_of(finfo.get("mtime"))
                wafer_dir = os.path.dirname(r["path"])
                item.update({
                    "open_ms": round(local[-1]["ms"], 2), "getattr_ms": round(fms, 2), "getattr_res": fres,
                    "ini_start": a.get("WaferStartTime", ""), "ini_end": a.get("WaferEndTime", ""),
                    "d_end_mtime": _diff(mt, en), "d_start_ctime": _diff(ct, st), "d_end_ctime": _diff(ct, en),
                    "dur_ini": _diff(en, st), "dur_meta": _diff(mt, ct),
                    "basis_content": collect.time_basis(st, en, w.b_start, w.b_end),
                    "basis_meta": collect.time_basis(ct, mt, w.b_start, w.b_end),
                    "uselot_mismatch": bool(a.get("UseLot") and a["UseLot"] != w.lot),
                    "usewafer_mismatch": bool(a.get("UseWaferID") and a["UseWaferID"] != w.wafer_id),
                    "wafer_dir": wafer_dir, "_en": en,
                })
                lot_dirs.setdefault(os.path.dirname(wafer_dir), []).append(item)
            rec.append(item)
        # Lot 폴더 한 단계 나열 — Wafer 폴더의 수정 시각이 WaferEndTime 을 대신할 수 있는지
        if not args.no_dir_list:
            for lot_dir, items in list(lot_dirs.items())[: args.time_lots]:
                if deadline.over():
                    break
                t = time.perf_counter()
                try:
                    ents = win_find(lot_dir, "*")
                    ms = ms_since(t)
                except Exception as e:  # noqa: BLE001
                    lots.append({"g": g, "lot_dir": lot_dir, "error": f"{type(e).__name__}: {e}"})
                    continue
                by = {e["name"].lower(): e for e in ents}
                diffs = []
                for it in items:
                    e = by.get(os.path.basename(it["wafer_dir"]).lower())
                    it["d_end_dirmtime"] = _diff(_dt_of(e["mtime"]) if e else None, it.get("_en"))
                    it["d_end_dirctime"] = _diff(_dt_of(e["ctime"]) if e else None, it.get("_en"))
                    diffs.append(it["d_end_dirmtime"])
                lots.append({"g": g, "lot_dir": lot_dir, "ms": round(ms, 2), "entries": len(ents), "dirs": sum(1 for e in ents if e["dir"]),
                             "wafers_here": len(items)})
        log(f"시각 일치 [{g or '(로컬)'}] Wafer {len([x for x in rec if x['g'] == g])}장 · Lot 나열 {len([x for x in lots if x['g'] == g])}개")
    for it in rec:
        it.pop("_en", None)

    def agree(key):
        xs = [x[key] for x in rec if x.get(key) is not None]
        if not xs:
            return {"n": 0}
        a = [abs(v) for v in xs]
        return {"n": len(xs), "within_2s": round(sum(v <= 2 for v in a) / len(a), 4), "within_10s": round(sum(v <= 10 for v in a) / len(a), 4),
                "within_60s": round(sum(v <= 60 for v in a) / len(a), 4), "diff_s": dist(xs)}

    oks = [x for x in rec if "basis_content" in x]
    by_dev = {}
    for x in oks:
        if x.get("d_end_mtime") is not None:
            by_dev.setdefault(x["dev"], []).append(x["d_end_mtime"])
    out["times"] = {
        "items": rec, "lot_list": lots,
        "agree": {k: agree(k) for k in ("d_end_mtime", "d_start_ctime", "d_end_ctime", "d_end_dirmtime", "d_end_dirctime")},
        "d_end_mtime_by_device": {k: dist(v) for k, v in by_dev.items()},
        "basis_same_meta": round(sum(x["basis_content"] == x["basis_meta"] for x in oks) / len(oks), 4) if oks else None,
        "basis_pairs": dict(collections.Counter(f"{x['basis_content']}>{x['basis_meta']}" for x in oks)),
        "uselot_mismatch": sum(x["uselot_mismatch"] for x in oks), "usewafer_mismatch": sum(x["usewafer_mismatch"] for x in oks), "ok": len(oks),
        "lot_list_ms": dist([x["ms"] for x in lots if "ms" in x], ci=True), "lot_entries": dist([x["entries"] for x in lots if "entries" in x]),
        "open_ms": dist([x["open_ms"] for x in oks], ci=True), "getattr_ms_warm": dist([x["getattr_ms"] for x in oks]),
    }
    a = out["times"]["agree"]
    log(f"시각 일치: INI 수정시각≈종료 ±2s {a['d_end_mtime'].get('within_2s')} · 생성시각≈시작 ±2s {a['d_start_ctime'].get('within_2s')} · "
        f"Wafer 폴더 수정시각≈종료 ±2s {a['d_end_dirmtime'].get('within_2s')} · STALE 판정 같음 {out['times']['basis_same_meta']}")


# ----------------------------------------------------------------------------- S · G: 동시성
def _run_level(wafers, level: int, stage: str):
    rec: list = []
    lock = threading.Lock()
    c0, t = time.process_time(), time.perf_counter()
    t_start = now_s()

    def one(w):
        local: list = []
        r = resolve_wafer(w, local, stage)
        with lock:
            rec.extend(local)
        return r["ms"]

    with ThreadPoolExecutor(max_workers=level) as pool:
        lat = list(pool.map(one, wafers))
    wall = time.perf_counter() - t
    by = collections.defaultdict(list)
    for x in rec:
        by[f"{x['type']}_{x['res']}"].append(x["ms"])
    n_ok = len(by.get("ini_ok", []))
    return {"level": level, "t": t_start, "wafers": len(wafers), "ops": len(rec), "ini_ok": n_ok, "wall_s": round(wall, 3),
            "wafers_per_s": round(len(wafers) / wall, 2) if wall else None, "ok_per_s": round(n_ok / wall, 2) if wall else None,
            "cpu_s": round(time.process_time() - c0, 2), "wafer_ms": dist(lat), "op_ms": {k: dist(v) for k, v in by.items()},
            "errors": sum(1 for x in rec if x["res"] == "error")}


def _take(p, n):
    part, p["pool"] = p["pool"][:n], p["pool"][n:]
    return part


def stage_sweep(plan, args, out, deadline) -> None:
    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    g_levels = [int(x) for x in args.group_levels.split(",") if x.strip()]
    res = []
    multi = len(plan) > 1
    for g, p in plan.items():
        avail = len(p["pool"])
        reserve = len(g_levels) * args.group_rounds if multi else 0
        rounds, chunk = args.sweep_rounds, 0
        while rounds >= 1:
            chunk = min(args.sweep_wafers, avail // (len(levels) * rounds + reserve)) if avail else 0
            if chunk >= 10:
                break
            rounds -= 1
        if rounds < 1 or chunk < 5:
            log(f"동시성 [{g or '(로컬)'}] Wafer 가 부족해 건너뜀({avail}장)")
            continue
        p["_chunk"] = chunk
        for r in range(rounds):
            lv = levels if r % 2 == 0 else list(reversed(levels))
            for level in lv:
                if deadline.over():
                    log("시간 한도 — 동시성 단계 중단")
                    out["sweep"] = res
                    return
                x = _run_level(_take(p, chunk), level, "sweep")
                x.update({"group": g, "round": r, "dir": "up" if r % 2 == 0 else "down"})
                res.append(x)
            log(f"동시성 [{g or '(로컬)'}] {r + 1}/{rounds}회차: " + " ".join(
                f"{y['level']}={y['wafers_per_s']}" for y in res if y["group"] == g and y["round"] == r) + " 장/s")
    out["sweep"] = res
    # G: 모든 묶음 동시
    gres = []
    if multi:
        for r in range(args.group_rounds):
            lv = g_levels if r % 2 == 0 else list(reversed(g_levels))
            for level in lv:
                if deadline.over():
                    break
                parts = {g: _take(p, p.get("_chunk", 0)) for g, p in plan.items() if p.get("_chunk")}
                parts = {g: v for g, v in parts.items() if len(v) >= 5}
                if len(parts) < 2:
                    break
                outs = {}

                def go(g, level=level):
                    outs[g] = _run_level(parts[g], level, "group")

                ths = [threading.Thread(target=go, args=(g,)) for g in parts]
                t = time.perf_counter()
                for th in ths:
                    th.start()
                for th in ths:
                    th.join()
                wall = time.perf_counter() - t
                for g, x in outs.items():
                    x.update({"group": g, "round": r, "total_wall_s": round(wall, 2), "groups": len(parts)})
                    gres.append(x)
                log(f"전 묶음 동시 {level}개({r + 1}회차): " + " ".join(f"{g}={outs[g]['wafers_per_s']}" for g in outs) + " 장/s")
    out["group_sweep"] = gres


# ----------------------------------------------------------------------------- A: 탐색(A·B·C안) — 1판과 같은 직렬 탐색 + 부모 확인
def stage_serial(plan, args, out, deadline) -> None:
    rec, per_w, probes, lot_lists = [], [], {}, []
    for g, p in plan.items():
        if deadline.over():
            break
        for w in p["serial"]:
            per_w.append((w, resolve_wafer(w, rec, "serial")))
    missed = []
    for w, r in per_w:
        n_try = (r["win"][0] * len(w.variants) + r["win"][1]) if r["win"] else len(w.cands)
        missed.extend((w, path) for _ri, _vi, path in w.cands[:n_try])

    def probe(path, level):
        k = path.lower()
        if k not in probes:
            res, ms, _n, err, _ = op_isdir(path)
            probes[k] = {"path": path, "level": level, "res": res, "ms": round(ms, 2), "err": err}
        return probes[k]["res"]

    for w, path in missed:
        if deadline.over():
            break
        wafer_dir = os.path.dirname(path)
        lot_dir = os.path.dirname(wafer_dir)
        setup_dir = os.path.dirname(lot_dir)
        if probe(lot_dir, "lot") == "ok":
            probe(wafer_dir, "wafer")
        elif probe(setup_dir, "setup") != "ok":
            probe(os.path.dirname(setup_dir), "job")
    if not args.no_dir_list:
        for v in [v for v in probes.values() if v["level"] == "lot" and v["res"] == "ok"][:10]:
            t = time.perf_counter()
            try:
                n = sum(1 for _ in nas_guard.scandir(v["path"]))
                lot_lists.append({"path": v["path"], "ms": round(ms_since(t), 2), "entries": n})
            except Exception as e:  # noqa: BLE001
                lot_lists.append({"path": v["path"], "error": f"{type(e).__name__}: {e}"})
    out["serial"] = {"ops": rec, "wafers": len(per_w), "probes": list(probes.values()), "lot_list": lot_lists,
                     "winners": [{"g": w.group, "dev": w.dev, "report": w.report, "win": list(r["win"][:2]) if r["win"] else None,
                                  "res": r["win"][2] if r["win"] else ("flag" if r["flag"] else "none")} for w, r in per_w]}


# ----------------------------------------------------------------------------- 분석
def analyze(out) -> None:
    a: dict = {}
    lines = []
    lines.append(f"NAS 묶음 {len(out.get('groups') or {})}개: " + ", ".join(f"{g or '(로컬)'} {len(v['devices'])}대" for g, v in (out.get("groups") or {}).items()))
    # L
    lst = [x for x in out.get("listing", []) if "ms" in x]
    if lst:
        by_m = {m: dist([x["ms"] for x in lst if x["method"] == m], ci=True) for m in dict.fromkeys(x["method"] for x in lst)}
        by_pos = {f"{m}@{'first' if p == 0 else 'later'}": dist([x["ms"] for x in lst if x["method"] == m and (x["pos"] == 0) == (p == 0)])
                  for m in by_m for p in (0, 1)}
        ratio = []
        for (dev, r), grp in itertools.groupby(sorted(lst, key=lambda x: (x["dev"], x["round"])), key=lambda x: (x["dev"], x["round"])):
            grp = {x["method"]: x["ms"] for x in grp}
            if "scandir" in grp and "large_fetch" in grp and grp["large_fetch"] > 0:
                ratio.append(grp["scandir"] / grp["large_fetch"])
        a["listing"] = {"by_method": by_m, "by_position": by_pos, "scandir_over_large_fetch": dist(ratio, ci=True)}
        lines.append("목록 p50(ms): " + " · ".join(f"{m} {v['p50']}" for m, v in by_m.items()) +
                     (f" · scandir/대량조회 배수 p50 {a['listing']['scandir_over_large_fetch'].get('p50')}" if ratio else ""))
    # R
    rp = (out.get("reports") or {}).get("per_group") or {}
    if rp:
        lines.append("Report 읽기 p50(ms) 한 줄/8개 동시: " + " · ".join(
            f"{g} {v['serial']['read_ms'].get('p50')}/{v['par8']['read_ms'].get('p50')}" for g, v in rp.items()))
    # M
    ms = (out.get("methods") or {}).get("summary") or {}
    if ms:
        lines.append("읽기 방식 p50(ms, 있는 파일): " + " · ".join(f"{k.split(':')[0]} {v['p50']}{v.get('p50_ci95') or ''}"
                                                              for k, v in ms.items() if k.endswith(":ok")))
    ws = (out.get("methods") or {}).get("warm_summary") or {}
    if ws.get("again_now:ok", {}).get("n"):
        lines.append(f"같은 파일 다시 읽기 p50: 처음 {ws.get('cold:ok', {}).get('p50')}ms · 곧바로 {ws['again_now:ok']['p50']}ms · 12초 뒤 {ws.get('again_12s:ok', {}).get('p50')}ms")
    # T
    tm = out.get("times") or {}
    if tm.get("ok"):
        ag = tm["agree"]
        lines.append(f"시각 일치(±2초/±60초): INI 수정≈종료 {ag['d_end_mtime'].get('within_2s')}/{ag['d_end_mtime'].get('within_60s')} · "
                     f"INI 생성≈시작 {ag['d_start_ctime'].get('within_2s')}/{ag['d_start_ctime'].get('within_60s')} · "
                     f"Wafer 폴더 수정≈종료 {ag['d_end_dirmtime'].get('within_2s')}/{ag['d_end_dirmtime'].get('within_60s')} · "
                     f"STALE 판정 같음 {tm['basis_same_meta']} (n{tm['ok']}) · UseLot/Wafer 불일치 {tm['uselot_mismatch']}/{tm['usewafer_mismatch']}")
    # S
    curve = collections.defaultdict(lambda: collections.defaultdict(list))
    lat = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in out.get("sweep") or []:
        curve[x["group"]][x["level"]].append(x["wafers_per_s"])
        lat[x["group"]][x["level"]].append(x["op_ms"].get("ini_ok", {}).get("p50"))
    a["sweep"] = {g: {lv: {"wafers_per_s": dist(v), "ok_p50_ms": dist(lat[g][lv])} for lv, v in sorted(c.items())} for g, c in curve.items()}
    for g, c in curve.items():
        lines.append(f"동시성 [{g or '(로컬)'}] 장/s 평균±sd: " + " ".join(
            f"{lv}={statistics.fmean(v):.1f}±{(statistics.stdev(v) if len(v) > 1 else 0):.1f}" for lv, v in sorted(c.items())))
    gc = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in out.get("group_sweep") or []:
        gc[x["level"]][x["group"]].append(x["wafers_per_s"])
    a["group_sweep"] = {lv: {g: dist(v) for g, v in d.items()} for lv, d in gc.items()}
    for lv, d in sorted(gc.items()):
        lines.append(f"전 묶음 동시 {lv}개 장/s: " + " ".join(f"{g}={statistics.fmean(v):.1f}" for g, v in d.items()) +
                     f" (합 {sum(statistics.fmean(v) for v in d.values()):.1f})")
    # C
    can = out.get("canary") or []
    if can:
        a["canary"] = {g: dist([x["ms"] for x in can if x["g"] == g]) for g in dict.fromkeys(x["g"] for x in can)}
        lines.append("카나리아 stat p50/p95(ms): " + " · ".join(f"{g} {v['p50']}/{v['p95']}" for g, v in a["canary"].items()))
    # A
    s = out.get("serial") or {}
    ops = s.get("ops") or []
    if ops:
        by = collections.defaultdict(list)
        for x in ops:
            by[f"{x['type']}_{x['res']}"].append(x["ms"])
        a["serial_op_ms"] = {k: dist(v) for k, v in by.items()}
        a["serial_ops_per_wafer"] = round(len(ops) / max(1, s.get("wafers", 1)), 3)
        a["ini_by_rank"] = dict(collections.Counter(f"{x['rank']}:{x['res']}" for x in ops if x["type"] == "ini"))
        lines.append(f"탐색: Wafer 당 요청 {a['serial_ops_per_wafer']} · 순위별 {a['ini_by_rank']}")
    out["analysis"] = a
    out["summary_lines"] = lines


# ----------------------------------------------------------------------------- 실제 수집 측정(앱의 collect.collect 그대로, 최근 N일)
class OpRecorder:
    """앱이 부르는 NAS 읽기 함수를 감싸 시간만 잰다(동작은 그대로 — 예외도 그대로 올린다). NAS 경로만 센다."""

    def __init__(self, roots) -> None:
        self.roots = [r for r in roots if r]
        self.rec: list = []
        self.slow: list = []
        self.lock = threading.Lock()
        self.saved: list = []
        self._gidx: dict = {}
        self.tls = threading.local()

    def is_nas(self, path) -> bool:
        try:
            p = os.fspath(path)
        except TypeError:
            return False
        return any(nas_guard.is_under(p, r) for r in self.roots)

    def add(self, kind, path, t0, res) -> None:
        ms = ms_since(t0)
        try:
            g = collect.nas_group(os.fspath(path))
        except Exception:  # noqa: BLE001
            g = "?"
        with self.lock:
            gi = self._gidx.setdefault(g, len(self._gidx))
            self.rec.append((kind, gi, round(t0 - T0, 4), round(ms, 2), res))
            if ms > 2000:
                self.slow.append({"kind": kind, "ms": round(ms), "res": res, "path": os.fspath(path)})

    def wrap(self, owner, name, kind, materialize=False, is_path_fn=True):
        orig = getattr(owner, name)
        rec = self

        def w(path, *a, **k):
            if getattr(rec.tls, "depth", 0) or not rec.is_nas(path):   # 안쪽 호출(read_text → read_bytes)은 한 번만 센다
                return orig(path, *a, **k)
            rec.tls.depth = 1
            kind_now = "find_all" if (kind == "find_pattern" and a and a[0] == "*") else kind
            t0 = time.perf_counter()
            try:
                out = orig(path, *a, **k)
                if materialize:
                    out = list(out)
                res = "ok"
                if kind_now in ("isfile", "isdir") and not out:
                    res = "false"
                return iter(out) if materialize else out
            except MISSING_EXC:
                res = "missing"
                raise
            except BaseException:
                res = "error"
                raise
            finally:
                rec.tls.depth = 0
                rec.add(kind_now, path, t0, res)

        self.saved.append((owner, name, orig))
        setattr(owner, name, w)
        return w

    def install(self) -> None:
        self.wrap(nas_guard, "read_bytes", "read_report")
        self.wrap(nas_guard, "read_text", "read_ini")
        self.wrap(nas_guard, "scandir", "scandir", materialize=True)
        if collect.PATTERN_LISTER is not None:
            self.wrap(nas_guard, "find_pattern", "find_pattern")
            self.saved.append((collect, "PATTERN_LISTER", collect.PATTERN_LISTER))
            collect.PATTERN_LISTER = nas_guard.find_pattern
        if getattr(collect, "FULL_LISTER", None) is not None:      # 9/30 부터 전체 나열도 대량 조회
            self.saved.append((collect, "FULL_LISTER", collect.FULL_LISTER))
            collect.FULL_LISTER = nas_guard.find_pattern
        self.wrap(os.path, "isfile", "isfile")
        self.wrap(os.path, "isdir", "isdir")
        self.wrap(os.path, "getmtime", "getmtime")

    def uninstall(self) -> None:
        for owner, name, orig in reversed(self.saved):
            setattr(owner, name, orig)
        self.saved.clear()

    def summary(self, wall_s: float) -> dict:
        groups = {i: g for g, i in self._gidx.items()}
        by_kind = collections.defaultdict(list)
        by_group = collections.defaultdict(lambda: collections.defaultdict(list))
        for kind, gi, _t, ms, res in self.rec:
            by_kind[f"{kind}:{res}"].append(ms)
            by_group[groups[gi]][f"{kind}:{res}"].append(ms)
        out = {"ops": len(self.rec), "by_kind": {k: dist(v) for k, v in sorted(by_kind.items())}, "per_group": {}}
        for g, d in by_group.items():
            busy = sum(sum(v) for v in d.values()) / 1000.0
            out["per_group"][g] = {"ops": sum(len(v) for v in d.values()), "busy_s": round(busy, 1),
                                   "avg_concurrency": round(busy / wall_s, 2) if wall_s else None,
                                   "by_kind": {k: {"n": len(v), "p50": pct(v, 50), "p95": pct(v, 95), "sum_s": round(sum(v) / 1000, 1)}
                                               for k, v in sorted(d.items())}}
        # 30초 창마다 묶음별 동시 진행 수(평균)
        tl = collections.defaultdict(lambda: collections.defaultdict(float))
        for _kind, gi, t, ms, _res in self.rec:
            tl[int(t // 30)][groups[gi]] += ms / 1000.0
        out["timeline_30s"] = {k * 30: {g: round(v / 30, 2) for g, v in d.items()} for k, d in sorted(tl.items())}
        out["slowest"] = sorted(self.slow, key=lambda x: -x["ms"])[:40]
        return out


def real_collect_runs(cfg, args, out_dir, out) -> None:
    """최근 N일을 **앱과 같은 collect.collect** 로 실제로 수집한다 — 캐시·HTML 은 측정용 로컬 폴더에만(평소 캐시·결과는 건드리지 않는다).

    회차: 처음 수집(빈 캐시) → 곧바로 다시(증분 · 이름 패턴 목록) → 전체 목록 강제(하루 한 번 수집과 같은 모양). 동시 수마다 반복."""
    import copy
    import signal

    run_root = os.path.join(out_dir, "real_" + dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    nas_guard.assert_local(run_root, nas_guard.expand_roots(nas_guard.roots_for_cfg(cfg)))
    os.makedirs(run_root, exist_ok=True)
    roots = nas_guard.expand_roots(nas_guard.roots_for_cfg(cfg))
    stop = threading.Event()
    prev_handler = None
    try:
        prev_handler = signal.signal(signal.SIGINT, lambda *_: (stop.set(), log("Ctrl+C — 지금 회차를 멈춥니다(읽던 파일은 끝까지 읽고 멈춤)")))
    except Exception:  # noqa: BLE001
        pass
    runs = []
    deadline = Deadline(args.max_minutes)
    workers = [int(x) for x in str(args.collect_workers).split(",") if x.strip()]
    kinds = ["fresh"] + (["again"] if args.collect_again else []) + (["full_relist"] if args.collect_full_relist else [])
    try:
        for w in workers:
            cache_file = os.path.join(run_root, f"cache_w{w}.json")
            for kind in kinds:
                if stop.is_set() or deadline.over():
                    break
                c2 = copy.deepcopy(cfg)
                c2.update({"cache_file": cache_file, "output_dir": os.path.join(run_root, f"w{w}"), "read_workers": w,
                           "backfill_days": args.collect_days, "retention_days": args.collect_days,
                           "refresh_window_days": 0, "rebuild_all": False, "write_csv": False})
                c2, problems = config_mod.normalize_config(c2)
                if config_mod.fatal(problems):
                    raise RuntimeError("측정용 설정 오류: " + "; ".join(p.message() for p in config_mod.fatal(problems)))
                label = f"w{w}:{kind}"
                log(f"━━ 실제 수집 {label} — 최근 {args.collect_days}일, NAS 마다 동시 {w}개")
                rec = OpRecorder(roots)
                saved_full = None
                if kind == "full_relist":                    # 마지막 전체 나열이 주기를 넘은 것처럼 — 하루 한 번 수집과 같은 목록
                    c2["full_list_every_hours"] = 0           # 새 앱(7일 주기 cfg)
                    if hasattr(collect, "FULL_LIST_EVERY_SEC"):   # 옛 앱(20시간 상수)
                        saved_full, collect.FULL_LIST_EVERY_SEC = collect.FULL_LIST_EVERY_SEC, 0
                stats: dict = {}
                phases: list = []
                last = {"phase": None}

                def progress(done, total, phase, _last=last, _phases=phases):
                    ph = str(phase or "")
                    key = "list" if "새 Report 찾는 중" in ph else ("read" if " · " in ph else ph)
                    t = now_s()
                    if key != _last["phase"] or t - _last.get("t", 0) >= 5:   # 단계가 바뀔 때와 5초마다 진행 수
                        _last["phase"], _last["t"] = key, t
                        _phases.append({"t": t, "phase": key, "done": done, "total": total})

                logs: list = []
                t0 = time.perf_counter()
                status, err = "ok", ""
                rows = dev_meta = errors = None
                rec.install()
                try:
                    rows, dev_meta, errors = collect.collect(c2, progress=progress, log=logs.append, stats=stats,
                                                             should_stop=lambda: stop.is_set() or deadline.over())
                except collect.CollectCancelled:
                    status = "cancelled"
                except Exception as e:  # noqa: BLE001
                    status, err = "error", traceback.format_exc()
                    log(f"수집 오류: {e}")
                finally:
                    rec.uninstall()
                    if saved_full is not None:
                        collect.FULL_LIST_EVERY_SEC = saved_full
                wall = time.perf_counter() - t0
                html_ms, html_mb = None, None
                if status == "ok":
                    t1 = time.perf_counter()
                    try:
                        warn: list = []
                        path = collect.write_html(c2, rows, dev_meta, errors, time.time() - wall, mode="auto", timing=stats, warnings=warn)
                        html_ms = round(ms_since(t1))
                        html_mb = round(os.path.getsize(path) / 1e6, 2) if path and os.path.isfile(path) else None
                    except Exception as e:  # noqa: BLE001
                        log(f"HTML 쓰기 오류(측정용 폴더): {e}")
                r = {"label": label, "workers": w, "kind": kind, "status": status, "error": err, "wall_s": round(wall, 1),
                     "stats": stats, "html_ms": html_ms, "html_mb": html_mb, "phases": phases,
                     "rows": len(rows or []), "errors": len(errors or []),
                     "devices": [{k: d.get(k) for k in ("name", "reports", "found", "read_errors", "error", "listing", "read_sum_ms", "kept", "status")}
                                 for d in (dev_meta or [])],
                     "ops": rec.summary(wall), "log": logs[-400:]}
                runs.append(r)
                out["real_collect"] = {"run_dir": run_root, "days": args.collect_days, "runs": runs}
                st = stats
                log(f"   {label}: {wall:.0f}초 · 장비확인 {st.get('devices_ms', 0) / 1000:.1f}s · 목록 {st.get('list_ms', 0) / 1000:.1f}s · "
                    f"읽기 {st.get('read_ms', 0) / 1000:.1f}s · 캐시 {st.get('cache_ms', 0) / 1000:.1f}s · HTML {((html_ms or 0) / 1000):.1f}s · "
                    f"Report {st.get('reports_read', 0)}개 · INI {st.get('ini_unique', 0)}건(없음 {st.get('ini_missing', 0)}) · "
                    f"이름 패턴 목록 {st.get('list_pattern', 0)}대 · NAS 요청 {r['ops']['ops']}건")
                if status != "ok":
                    break
    finally:
        if prev_handler is not None:
            try:
                signal.signal(signal.SIGINT, prev_handler)
            except Exception:  # noqa: BLE001
                pass
    out["real_collect"] = {"run_dir": run_root, "days": args.collect_days, "runs": runs}


def real_collect_summary(out) -> list:
    lines = []
    rc = out.get("real_collect") or {}
    for r in rc.get("runs", []):
        st = r.get("stats") or {}
        lines.append(f"[{r['label']}] {r['status']} {r['wall_s']}초 = 장비확인 {st.get('devices_ms', 0) / 1000:.1f} + 목록 {st.get('list_ms', 0) / 1000:.1f}"
                     f" + 읽기 {st.get('read_ms', 0) / 1000:.1f} + 캐시 {st.get('cache_ms', 0) / 1000:.1f} (HTML {((r.get('html_ms') or 0) / 1000):.1f}s)"
                     f" · Report {st.get('reports_read', 0)}/{st.get('reports_found', 0)} · INI {st.get('ini_unique', 0)}(없음 {st.get('ini_missing', 0)})"
                     f" · 패턴 목록 {st.get('list_pattern', 0)}대")
        for g, v in (r.get("ops") or {}).get("per_group", {}).items():
            k = v["by_kind"]
            lines.append(f"    {g}: 요청 {v['ops']} · 평균 동시 {v['avg_concurrency']} · Report 읽기 p50 {k.get('read_report:ok', {}).get('p50')}ms"
                         f" · INI p50 {k.get('read_ini:ok', {}).get('p50')}ms(없음 {k.get('read_ini:missing', {}).get('p50')}ms)"
                         f" · 목록 {round(sum(k.get(x, {}).get('sum_s', 0) for x in ('scandir:ok', 'find_pattern:ok', 'find_all:ok')), 1)}s")
    return lines


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


def _ask_levels(prompt: str, default: str) -> str:
    while True:
        lv = _ask(prompt, default)
        try:
            if lv.strip() and all(0 < int(x) <= 64 for x in lv.split(",") if x.strip()):
                return lv
        except ValueError:
            pass
        print("  1~64 사이 숫자를 쉼표로 구분해 입력해 주세요.")


def interactive(args) -> bool:
    """옵션 없이 실행하면 필요한 값을 차례로 묻는다. Enter 만 누르면 [기본값]. False 면 실행하지 않는다."""
    print("=" * 70)
    print(" AOI Capacity — NAS 읽기 성능 측정 2판 (읽기 전용, NAS 에는 아무것도 쓰지 않습니다)")
    print(" 값을 묻는 곳에서 Enter 만 누르면 [괄호 안 기본값]을 씁니다.")
    print("=" * 70)
    print(" 1) 정밀 측정   — 반복 3회 · 순서 교차 · 시각 일치 검사, 약 25~35분(권장)")
    print(" 2) 빠른 측정   — 반복 1회 · 표본 적게, 약 8~12분")
    print(" 3) 직접 설정   — 반복 수·표본 수·동시성 단계를 하나씩 정함")
    print(" 4) 실제 수집   — 최근 며칠을 앱과 똑같이 수집하며 단계·요청별 속도 기록(평소 캐시·결과는 그대로)")
    mode = _ask_int("측정 방식 번호", 1, 1, 4)
    if mode == 2:
        args.quick = True
    if mode == 4:
        args.real_collect = True
        args.collect_days = _ask_int("수집할 최근 일수", args.collect_days, 1, 30)
        args.collect_workers = _ask_levels("NAS 마다 동시 읽기 수(쉼표로 여러 개면 차례로 비교, 예: 8 또는 8,16)", args.collect_workers)
        args.collect_again = _ask_yes("처음 수집 뒤 곧바로 한 번 더(증분 · 이름 패턴 목록) 잴까요", True)
        args.collect_full_relist = _ask_yes("전체 목록으로 한 번 더(하루 한 번 수집과 같은 모양) 잴까요", True)
        args.max_minutes = _ask_int("최대 실행 시간(분)", int(args.max_minutes), 5, 600)
        print("-" * 70)
        print(f" 실제 수집 · 최근 {args.collect_days}일 · 동시 {args.collect_workers} · 곧바로 다시 {'함' if args.collect_again else '안 함'}"
              f" · 전체 목록 다시 {'함' if args.collect_full_relist else '안 함'}")
        print(" 캐시·HTML 은 측정용 폴더(%LOCALAPPDATA%\\AOI_Capacity\\bench\\real_…)에만 만들고 평소 결과는 건드리지 않습니다.")
        return _ask_yes("이대로 시작할까요", True)
    args.devices = _ask("측정할 장비(쉼표로 구분, 예: AOI-1,AOI-9 · 비우면 수집 범위 전체)", "")
    if mode == 3:
        args.days = _ask_int("Report 를 고를 최근 일수(1~14)", args.days, 1, 14)
        args.reports_per_device = _ask_int("장비마다 읽을 Report 수", args.reports_per_device, 1, 300)
        args.list_rounds = _ask_int("목록 방식 반복 횟수(0 = 안 함)", args.list_rounds, 0, 10)
        args.method_wafers = _ask_int("NAS 묶음마다 읽기 방식 비교 Wafer 수", args.method_wafers, 0, 5000)
        args.time_wafers = _ask_int("NAS 묶음마다 시각 일치 검사 Wafer 수", args.time_wafers, 0, 5000)
        args.sweep_rounds = _ask_int("동시성 곡선 반복 횟수(0 = 안 함)", args.sweep_rounds, 0, 10)
        if args.sweep_rounds:
            args.levels = _ask_levels("동시성 단계(쉼표로 구분)", args.levels)
            args.sweep_wafers = _ask_int("동시성 한 단계의 최대 Wafer 수", args.sweep_wafers, 5, 5000)
            args.group_rounds = _ask_int("전 묶음 동시 반복 횟수(0 = 안 함)", args.group_rounds, 0, 10)
    args.no_dir_list = not _ask_yes("조사용 Lot 폴더 한 단계 나열(시각 일치 검사에 필요)도 할까요", True)
    args.max_minutes = _ask_int("최대 실행 시간(분) — 넘으면 남은 단계를 건너뜀", int(args.max_minutes), 5, 600)
    print("-" * 70)
    print(f" 방식 {['', '정밀', '빠른', '직접 설정'][mode]} · 장비 {args.devices or '수집 범위 전체'} · "
          f"폴더 나열 {'안 함' if args.no_dir_list else '함'} · 최대 {args.max_minutes}분")
    return _ask_yes("이대로 시작할까요", True)


def _pause() -> None:
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
    ap = argparse.ArgumentParser(description="AOI Capacity NAS 읽기 성능 현장 측정 2판(읽기 전용)")
    ap.add_argument("--config", default=os.path.join(os.getcwd(), "config.json"), help="없으면 GUI 설정(prefs)을 쓴다")
    ap.add_argument("--out", default="", help="결과 폴더(로컬). 기본 %%LOCALAPPDATA%%\\AOI_Capacity\\bench")
    ap.add_argument("--devices", default="", help="쉼표로 장비 이름 제한(수집 범위 안에서만)")
    ap.add_argument("--days", type=int, default=7, help="Report 를 고를 최근 일수(날짜 패턴, 14 이하)")
    ap.add_argument("--reports-per-device", type=int, default=25)
    ap.add_argument("--serial-reports", type=int, default=10, help="묶음마다 한 줄로 읽을 Report 수")
    ap.add_argument("--list-devices", type=int, default=2, help="목록 비교에 쓸 장비 수(묶음마다)")
    ap.add_argument("--list-rounds", type=int, default=3)
    ap.add_argument("--method-wafers", type=int, default=175, help="묶음마다 읽기 방식 비교 Wafer 수")
    ap.add_argument("--warm-paths", type=int, default=15, help="묶음마다 재읽기(캐시 효과) 경로 수")
    ap.add_argument("--time-wafers", type=int, default=120, help="묶음마다 시각 일치 검사 Wafer 수")
    ap.add_argument("--time-lots", type=int, default=40, help="묶음마다 시각 검사용 Lot 폴더 나열 수")
    ap.add_argument("--serial-wafers", type=int, default=40, help="묶음마다 탐색(A·B·C) Wafer 수")
    ap.add_argument("--sweep-wafers", type=int, default=60, help="동시성 한 단계의 최대 Wafer 수(묶음마다)")
    ap.add_argument("--sweep-rounds", type=int, default=3)
    ap.add_argument("--levels", default="1,2,4,6,8,12,16")
    ap.add_argument("--group-levels", default="4,8,12")
    ap.add_argument("--group-rounds", type=int, default=2)
    ap.add_argument("--canary-sec", type=float, default=15.0, help="카나리아 간격(초, 0 = 안 함)")
    ap.add_argument("--no-dir-list", action="store_true", help="조사용 Lot/Wafer 폴더 한 단계 나열을 하지 않는다")
    ap.add_argument("--max-minutes", type=float, default=50)
    ap.add_argument("--seed", type=int, default=20260930)
    ap.add_argument("--quick", action="store_true", help="반복 1회 · 표본 적게(약 10분)")
    ap.add_argument("--real-collect", action="store_true", help="최근 며칠을 앱과 똑같이 실제 수집하며 속도 기록")
    ap.add_argument("--collect-days", type=int, default=2)
    ap.add_argument("--collect-workers", default="8", help="NAS 마다 동시 읽기 수, 쉼표로 여러 개면 차례로")
    ap.add_argument("--no-collect-again", dest="collect_again", action="store_false")
    ap.add_argument("--no-collect-full-relist", dest="collect_full_relist", action="store_false")
    ap.add_argument("--ask", action="store_true", help="옵션을 주더라도 실행할 때 값을 물어본다")
    args = ap.parse_args(argv)
    raw = sys.argv[1:] if argv is None else list(argv)
    asked = args.ask or (not raw and sys.stdin is not None and sys.stdin.isatty())
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
        args.reports_per_device = min(args.reports_per_device, 12)
        args.list_rounds, args.sweep_rounds, args.group_rounds = 1, 1, 1
        args.method_wafers, args.time_wafers, args.serial_wafers = 70, 50, 20
        args.list_devices, args.serial_reports, args.warm_paths, args.time_lots = 1, 5, 8, 15
        args.levels = "1,4,8,16"
        args.group_levels = "8"
    args.days = max(1, min(14, args.days))
    problems: list = []
    cfg = cli_mod.load_config(args.config, problems)
    if config_mod.fatal(problems):
        for p in config_mod.fatal(problems):
            print("설정 오류:", p.message())
        return 1
    out_dir = args.out or str(paths.data_root() / "bench")
    nas_guard.assert_local(out_dir, nas_guard.expand_roots(nas_guard.roots_for_cfg(cfg)))   # 결과 파일은 NAS 밖에만
    os.makedirs(out_dir, exist_ok=True)
    prefix = "nas_collect_" if args.real_collect else "nas_bench_"
    out_path = os.path.join(out_dir, prefix + dt.datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")
    out: dict = {"args": vars(args)}
    if args.real_collect:
        return _run_real(cfg, args, out_dir, out_path, out)
    deadline = Deadline(args.max_minutes)
    status, canary, stage_ms = "ok", None, {}

    def step(name, fn, *a):
        t = time.perf_counter()
        log(f"── {name}")
        try:
            return fn(*a)
        finally:
            stage_ms[name] = round(ms_since(t))

    try:
        step("환경", stage_env, cfg, out)
        devs = step("장비", stage_devices, cfg, args.devices, out)
        if not devs:
            raise RuntimeError("측정할 장비가 없습니다(수집 범위·연결 확인)")
        targets = {}
        for d in devs:
            targets.setdefault(d["_group"], os.path.join(str(d["path"]), str(d.get("report_dir") or "Report")))
        if args.canary_sec > 0:
            canary = Canary(targets, args.canary_sec).start()
        wafers = step("Report", stage_reports, devs, cfg, args, out)
        plan = allocate(wafers, args)
        out["allocation"] = {g: {k: len(v) for k, v in p.items()} for g, p in plan.items()}
        if args.list_rounds > 0:
            step("목록", stage_listing, devs, args, out, deadline)
        step("읽기 방식", stage_methods, plan, args, out, deadline)
        step("시각 일치", stage_times, plan, args, out, deadline)
        if args.sweep_rounds > 0:
            step("동시성", stage_sweep, plan, args, out, deadline)
        step("탐색", stage_serial, plan, args, out, deadline)
    except KeyboardInterrupt:
        status = "interrupted"
        log("Ctrl+C — 지금까지 결과를 씁니다")
    except Exception as e:  # noqa: BLE001
        status = "error"
        out["error"] = traceback.format_exc()
        log(f"오류: {e}")
    if canary is not None:
        out["canary"] = canary.finish()
    out["stage_ms"] = stage_ms
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


def _run_real(cfg, args, out_dir, out_path, out) -> int:
    status = "ok"
    try:
        log("── 환경")
        stage_env(cfg, out)
        real_collect_runs(cfg, args, out_dir, out)
        runs = (out.get("real_collect") or {}).get("runs") or []
        if any(r["status"] == "cancelled" for r in runs):
            status = "interrupted"
        elif any(r["status"] == "error" for r in runs):
            status = "error"
    except KeyboardInterrupt:
        status = "interrupted"
    except Exception as e:  # noqa: BLE001
        status = "error"
        out["error"] = traceback.format_exc()
        log(f"오류: {e}")
    try:
        out["summary_lines"] = real_collect_summary(out)
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
