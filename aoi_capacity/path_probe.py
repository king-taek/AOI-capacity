"""배포 경로 자동 시험(10/30 임시 — 새 공유 폴더에 배포가 되는지 한 번에 재고 결과를 zip 한 장으로 남긴다).

시험이 끝나면 이 모듈과 수집 창의 '배포 경로 시험' 카드를 함께 지운다.

무엇을 재는가(실제 배포 `publish.py` 의 함수를 그대로 불러 쓴다 — 시험이 통과하면 실제 배포도 같은 길로 간다)
  · 공유 폴더가 장비 NAS 와 다른 곳인가 · 닿는가(폴더 · 목록 · 지연)
  · LOT추적 · 전체 폴더를 만들 수 있는가, 그 안 `_aoi_path_test\\` 에 안내 파일(AOI_LOT.html · AOI_ALL.html) · latest.js · data 파일을
    임시 파일에 쓰고 이름 바꾸기 · 덮어쓰기 · 읽어 비교 · 지우기 · 오래된 파일 정리(`_prune`)
  · 열려 있는 파일을 교체할 수 있는가(Windows 는 못 하는 게 정상 — 안내만)
  · 한글 · 따옴표(') · 공백이 든 이름의 파일, `.url` 바로가기(ANSI 인코딩 · 주소 변환), AOI.ico 를 올리고 내용이 같은지
  · 왕복 지연(stat 20번) · 1 / 10 / 30MB 쓰기 · 읽기 시간 · 남은 용량

★ 쓰기는 공유 폴더의 `_aoi_path_test\\`(시험이 끝나면 지운다)와 이 PC 의 결과 zip 뿐이다. 실제 배포 파일(AOI_LOT.html · latest.js · data\\…)은 건드리지 않는다.
★ 장비 NAS 아래면 아무것도 쓰지 않는다(`nas_guard.assert_local` — 이 모듈의 쓰기 함수는 첫 줄에서 부른다. 가드 `test_nas_guard.py`).
"""
from __future__ import annotations

import ctypes
import datetime as dt
import hashlib
import io
import json
import locale
import os
import platform
import statistics
import sys
import time
import traceback
import urllib.parse
import zipfile
from typing import Callable, Dict, List, Optional

from . import collect, i18n, nas_guard, publish
from .utils import paths

K = i18n.KO

TEST_DIR = "_aoi_path_test"
SIZES_MB = (1, 10, 30)               # 첫 폴더(LOT추적)는 셋 다, 둘째 폴더(전체)는 앞의 둘 — 실제 전체 배포 파일은 100MB 안팎
SIZES_MB_SECOND = (1, 10)
STAT_ROUNDS = 20
LOG_TAIL_LINES = 400
KOREAN_NAME = "한글 시험's 파일(1).txt"          # 한글 · 공백 · 따옴표 · 괄호 — 실제 폴더 이름(임현택 ENG'R)과 같은 종류의 글자
Log = Callable[[str], None]


class _Rec:
    """검사 결과 모음 — `check` 한 번이 표의 한 줄(통과 True · 실패 False · 참고 None)."""

    def __init__(self, log: Optional[Log], progress: Optional[Callable[[str], None]], should_stop: Optional[Callable[[], bool]]):
        self.rows: List[dict] = []
        self.log, self.progress, self.should_stop = log, progress, should_stop
        self.artifacts: Dict[str, bytes] = {}
        self.stopped = False

    def stop(self) -> bool:
        if self.should_stop and self.should_stop():
            self.stopped = True
        return self.stopped

    def check(self, group: str, name: str, fn: Callable[[], tuple], *, force: bool = False) -> Optional[bool]:
        """`force` = 멈춤 요청이 있어도 돌린다(시험 파일 지우기)."""
        if not force and (self.stopped or self.stop()):
            return None
        if self.progress:
            self.progress(f"{group} · {name}")
        t0 = time.perf_counter()
        try:
            ok, detail = fn()
        except Exception as exc:  # noqa: BLE001 - 어떤 오류든 표의 한 줄로 남기고 다음 검사로
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        ms = (time.perf_counter() - t0) * 1000
        self.rows.append({"group": group, "name": name, "ok": ok, "ms": round(ms, 1), "detail": str(detail)})
        if self.log:
            self.log(f"[배포 경로 시험] {'통과' if ok else '실패' if ok is False else '참고'} · {group} · {name} · {ms:.0f}ms · {detail}")
        return ok


# ── 쓰기 도구(전부 첫 줄에서 assert_local) ─────────────────────────────
def _mkdirs(path: str, roots: List[str]) -> bool:
    """폴더를 만든다(이미 있으면 False, 새로 만들었으면 True)."""
    nas_guard.assert_local(path, roots)
    existed = os.path.isdir(path)
    os.makedirs(path, exist_ok=True)
    return not existed


def _remove(path: str, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.remove(path)


def _rmdir(path: str, roots: List[str]) -> None:
    nas_guard.assert_local(path, roots)
    os.rmdir(path)


def _free_bytes(path: str, roots: List[str]) -> int:
    """남은 용량(바이트). UNC 는 Windows API 로, 그 밖에는 표준 함수로."""
    nas_guard.assert_local(path, roots)
    if os.name == "nt":
        free = ctypes.c_ulonglong(0)
        if not ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), ctypes.byref(free), None, None):   # type: ignore[attr-defined]
            raise OSError("GetDiskFreeSpaceExW 실패")
        return int(free.value)
    import shutil
    return int(shutil.disk_usage(path).free)


def write_zip(out_dir: str, name: str, members: Dict[str, bytes], roots: List[str]) -> str:
    """결과 zip 한 장을 만든다. 저장 위치가 장비 NAS 아래면 거부."""
    nas_guard.assert_local(out_dir, roots)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for member, data in members.items():
            z.writestr(member, data)
    with open(out, "wb") as fh:
        fh.write(buf.getvalue())
    return out


# ── 읽기 도구 ───────────────────────────────────────────────────────
def _read(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:16]


def _fmt_mb_s(nbytes: int, sec: float) -> str:
    return f"{nbytes / 1048576 / sec:.1f}MB/s" if sec > 0 else "-"


def _p95(xs: List[float]) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * 0.95))]


def _listing(path: str, limit: int = 60) -> str:
    try:
        out = []
        for n in sorted(os.listdir(path))[:limit]:
            fp = os.path.join(path, n)
            try:
                st = os.stat(fp)
                out.append(f"{'<DIR>' if os.path.isdir(fp) else f'{st.st_size:>12,}'}  {dt.datetime.fromtimestamp(st.st_mtime):%Y-%m-%d %H:%M:%S}  {n}")
            except OSError as exc:
                out.append(f"(읽지 못함)  {n}  {exc}")
        return "\n".join(out) if out else "(비어 있음)"
    except OSError as exc:
        return f"(나열하지 못함: {type(exc).__name__}: {exc})"


# ── 폴더 하나 시험 ─────────────────────────────────────────────────────
def _test_folder(rec: _Rec, kind: publish.Kind, base: str, sizes: tuple, roots: List[str], tag: str) -> None:
    td = os.path.join(base, TEST_DIR)
    dd = os.path.join(td, publish.DATA_DIR)
    made: List[str] = []                                  # 이 시험이 만든 파일(끝에서 지운다)
    made_dirs: List[str] = []

    def mk(path: str) -> bool:
        new = _mkdirs(path, roots)
        if new:
            made_dirs.append(path)
        return new

    def put(path: str, data) -> bool:
        ok = publish._write_text(path, data, roots, tries=1)
        if ok:
            made.append(path)
        return ok

    rec.artifacts[f"폴더목록/{tag}_시험_전.txt"] = (_listing(base) + "\n").encode("utf-8")

    def folder():
        new = mk(base) if not os.path.isdir(base) else False
        return os.path.isdir(base), ("새로 만들었다" if new else "이미 있었다") + f" · {base}"
    rec.check(tag, "배포 폴더 만들기 · 확인", folder)

    def pointed():
        return None, f"latest.js 가 지금 가리키는 파일: {publish._pointed_name(base, kind) or '(없음)'}"
    rec.check(tag, "지금 배포된 파일 확인", pointed)

    def cleanup():
        left = []
        for p in reversed(made):
            if os.path.isfile(p):
                try:
                    _remove(p, roots)
                except OSError as exc:
                    left.append(f"{os.path.basename(p)}({type(exc).__name__})")
        for d in (dd, td):
            if os.path.isdir(d):
                try:
                    _rmdir(d, roots)
                except OSError:
                    left.append(os.path.basename(d) + "\\")
        return not left, ("시험 파일을 모두 지웠다" if not left else "못 지운 것: " + ", ".join(left))

    try:
        def subdirs():
            a, b = mk(td), mk(dd)
            return os.path.isdir(dd), f"{TEST_DIR} {'새로' if a else '이미'} · data {'새로' if b else '이미'}"
        if not rec.check(tag, f"시험 하위 폴더({TEST_DIR}\\data) 만들기", subdirs):
            rec.check(tag, "시험 중단", lambda: (False, "시험 폴더를 만들지 못해 이 폴더의 나머지 시험을 건너뜁니다"))
            return

        def korean():
            p = os.path.join(td, KOREAN_NAME)
            data = "한글 · 따옴표(') · 공백 시험\n".encode("utf-8")
            if not put(p, data):
                return False, "쓰지 못함"
            names = os.listdir(td)
            same = _read(p) == data
            return KOREAN_NAME in names and same, f"목록에 같은 이름 {'있음' if KOREAN_NAME in names else '없음'} · 내용 {'같음' if same else '다름'}"
        rec.check(tag, "한글 · 따옴표 · 공백 이름 파일 쓰기 · 읽기", korean)

        def stub():
            p = os.path.join(td, kind.stub)
            text = publish.stub_text(kind)
            if not put(p, text):
                return False, "쓰지 못함"
            got = _read(p).decode("utf-8")
            return got == text, f"{kind.stub} {len(text)}자 · 읽어 비교 {'같음' if got == text else '다름'}"
        rec.check(tag, f"안내 파일 {kind.stub} 쓰기", stub)

        def latest():
            p = os.path.join(td, publish.LATEST_NAME)
            v1 = publish.latest_text(f"{kind.prefix}_20260101_0000.html", kind)
            v2 = publish.latest_text(f"{kind.prefix}_20260101_0001.html", kind)
            if not put(p, v1):
                return False, "처음 쓰기 실패"
            t0 = time.perf_counter()
            if not put(p, v2):                                 # 같은 이름 덮어쓰기(os.replace) — 실제 배포가 매번 하는 일
                return False, "덮어쓰기 실패"
            ms = (time.perf_counter() - t0) * 1000
            got = _read(p).decode("utf-8")
            return got == v2, f"덮어쓰기 {ms:.0f}ms · 읽어 비교 {'같음(새 내용)' if got == v2 else '다름'}"
        rec.check(tag, "latest.js 쓰기 · 덮어쓰기", latest)

        def locked():
            p = os.path.join(td, publish.LATEST_NAME)
            v3 = publish.latest_text(f"{kind.prefix}_20260101_0002.html", kind)
            with open(p, "rb"):                                # 누군가 이 파일을 열고 있는 상태
                replaced = publish._write_text(p, v3, roots, tries=1)
            note = "열린 파일도 교체됨" if replaced else "열린 파일은 교체 못 함(Windows 의 정상 동작 — 실제 배포는 다시 시도하고 데이터 파일은 새 이름으로 올린다)"
            return None, note
        rec.check(tag, "열려 있는 latest.js 교체(참고)", locked)

        def sizes_run():
            lines = []
            for mb in sizes:
                if rec.stop():
                    break
                data = os.urandom(mb << 20)
                name = f"{kind.prefix}_20260102_{mb:04d}.html"
                p = os.path.join(dd, name)
                t0 = time.perf_counter()
                ok = put(p, data)
                tw = time.perf_counter() - t0
                if not ok:
                    lines.append(f"{mb}MB 쓰기 실패")
                    return False, " · ".join(lines)
                t0 = time.perf_counter()
                got = _read(p)
                tr = time.perf_counter() - t0
                if got != data:
                    lines.append(f"{mb}MB 읽어 비교 다름")
                    return False, " · ".join(lines)
                lines.append(f"{mb}MB 쓰기+이름바꾸기 {tw:.1f}초({_fmt_mb_s(len(data), tw)}) · 읽기 {tr:.1f}초({_fmt_mb_s(len(data), tr)})")
            return True, " | ".join(lines)
        rec.check(tag, f"data 파일 쓰기 · 읽기 시간({'/'.join(str(s) for s in sizes)}MB)", sizes_run)

        def prune():
            for i in range(1, 6):
                put(os.path.join(dd, f"{kind.prefix}_2026030{i}_0000.html"), b"x")
            before = sorted(n for n in os.listdir(dd) if kind.data_re.match(n))
            gone = publish._prune(dd, publish.KEEP_FILES, roots, kind=kind)
            after = sorted(n for n in os.listdir(dd) if kind.data_re.match(n))
            for n in before:
                if n not in after:
                    made[:] = [m for m in made if os.path.basename(m) != n]
            return len(after) == publish.KEEP_FILES and gone == len(before) - len(after), f"{len(before)}개 → {len(after)}개 남김(지운 {gone}개, 남길 개수 {publish.KEEP_FILES})"
        rec.check(tag, "오래된 data 파일 정리(삭제 권한)", prune)

        ico_dst = os.path.join(td, publish.ICON_NAME)

        def icon():
            src = publish.app_icon()
            if not src:
                return None, "이 PC 에 앱 아이콘(logo.ico)이 없어 건너뜀"
            data = _read(src)
            if not put(ico_dst, data):
                return False, "쓰지 못함"
            return _read(ico_dst) == data, f"{publish.ICON_NAME} {len(data):,}바이트 · sha {_sha(data)} · 읽어 비교 같음"
        rec.check(tag, "AOI.ico 올리기", icon)

        def shortcut():
            p = os.path.join(td, kind.shortcut)
            icon_arg = ico_dst if os.path.isfile(ico_dst) else None
            want = publish.shortcut_bytes(td, kind, icon_arg)
            if not put(p, want):
                return False, "쓰지 못함"
            got = _read(p)
            rec.artifacts[f"바로가기_샘플/{tag}_{kind.shortcut}"] = got
            enc = publish._ansi()
            try:
                text = got.decode(enc)
                how = f"{enc}(ANSI)"
            except (UnicodeDecodeError, LookupError):
                text, how = got.decode("utf-8", "replace"), "UTF-8(퍼센트 인코딩 판)"
            url_ok = "URL=file:" in text
            icon_ok = (not icon_arg) or ("IconFile=" in text)
            return got == want and url_ok, f"{how} · {len(got)}바이트 · 아이콘 줄 {'있음' if icon_ok and icon_arg else '없음'}\n{text.strip()}"
        rec.check(tag, f"바로가기 {kind.shortcut} 만들기", shortcut)

        def urls():
            s, r = publish.stub_url(td, kind), publish.raw_stub_url(td, kind)
            back = urllib.parse.unquote(s)
            want = "file:" + "//" + td.replace("\\", "/").lstrip("/") + "/" + kind.stub if td.startswith("\\\\") else None
            ok = (back == want) if want else True
            return ok, f"stub_url={s}\nraw_stub_url={r}\n되돌린 주소 {'같음' if ok else '다름: ' + back}"
        rec.check(tag, "주소 변환(file://, 한글 · 따옴표 · 공백)", urls)

        def latency():
            xs = []
            for _ in range(STAT_ROUNDS):
                t0 = time.perf_counter()
                os.stat(td)
                xs.append((time.perf_counter() - t0) * 1000)
            t0 = time.perf_counter()
            n = len(os.listdir(td))
            lm = (time.perf_counter() - t0) * 1000
            return None, f"stat {STAT_ROUNDS}번 중앙 {statistics.median(xs):.1f}ms · 95% {_p95(xs):.1f}ms · 최대 {max(xs):.1f}ms · 폴더 나열 {n}개 {lm:.1f}ms"
        rec.check(tag, "왕복 지연", latency)

        def free():
            b = _free_bytes(td, roots)
            return b > (200 << 20), f"남은 용량 {b / (1 << 30):.1f}GB"
        rec.check(tag, "남은 용량", free)
    finally:                                              # 멈춤 요청 · 예상 밖 오류에도 시험 파일은 지운다
        rec.check(tag, "시험 파일 지우기", cleanup, force=True)
    rec.artifacts[f"폴더목록/{tag}_시험_후.txt"] = (_listing(base) + "\n").encode("utf-8")


# ── 전체 ────────────────────────────────────────────────────────────────
def _env_info(cfg: dict, root: str) -> dict:
    ver = ""
    try:
        ver = collect.version_text()
    except Exception:  # noqa: BLE001
        pass
    return {
        "시각": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "수집기 버전": ver,
        "컴퓨터 이름": platform.node(),
        "운영체제": platform.platform(),
        "파이썬": sys.version.split()[0],
        "os.name": os.name,
        "파일 시스템 인코딩": sys.getfilesystemencoding(),
        "선호 인코딩": locale.getpreferredencoding(False),
        "바로가기 ANSI 코드페이지": publish._ansi(),
        "시험 경로": root,
        "시험 경로 repr": repr(root),
        "절대 경로인가": os.path.isabs(root),
        "배포가 켜질 수 있는 경로인가(publish._enabled)": publish._enabled(root),
        "설정 publish_dir": str(cfg.get("publish_dir") or ""),
        "설정 publish_full_dir": str(cfg.get("publish_full_dir") or ""),
        "설정 publish_full_days": cfg.get("publish_full_days"),
        "데이터 폴더": str(paths.data_root()),
    }


def _log_tail() -> bytes:
    try:
        with open(paths.log_file(), "rb") as f:
            lines = f.read().splitlines()[-LOG_TAIL_LINES:]
        return b"\n".join(lines) + b"\n"
    except OSError as exc:
        return f"(app.log 를 읽지 못함: {exc})\n".encode("utf-8")


def render_summary(info: dict, rows: List[dict], zip_name: str, stopped: bool) -> str:
    ok = sum(1 for r in rows if r["ok"] is True)
    bad = [r for r in rows if r["ok"] is False]
    lines = [
        "배포 경로 시험 결과",
        f"시험 경로: {info.get('시험 경로')}",
        f"시각: {info.get('시각')} · 컴퓨터: {info.get('컴퓨터 이름')} · 수집기 {info.get('수집기 버전')}",
        "",
        ("★ 중단됨 — 일부 검사를 하지 못했습니다" if stopped else
         ("★ 모두 통과" if not bad else f"★ 실패 {len(bad)}개")) + f" (통과 {ok} · 실패 {len(bad)} · 참고 {sum(1 for r in rows if r['ok'] is None)})",
        "",
    ]
    if bad:
        lines.append("실패한 검사:")
        for r in bad:
            lines.append(f"  ✖ [{r['group']}] {r['name']} — {r['detail'].splitlines()[0] if r['detail'] else ''}")
        lines.append("")
    lines.append("전체 검사표:")
    for r in rows:
        mark = "✔" if r["ok"] is True else "✖" if r["ok"] is False else "ℹ"
        lines.append(f"  {mark} [{r['group']}] {r['name']} ({r['ms']:.0f}ms)")
        for d in str(r["detail"]).splitlines():
            lines.append(f"       {d}")
    lines += ["", f"이 파일({zip_name})을 그대로 보내 주세요."]
    return "\n".join(lines) + "\n"


def run(cfg: dict, out_dir: str, *, root: Optional[str] = None, log: Optional[Log] = None,
        progress: Optional[Callable[[str], None]] = None, should_stop: Optional[Callable[[], bool]] = None) -> dict:
    """시험을 돌리고 결과 zip 을 만든다. → {"path", "ok", "failed", "total", "stopped", "rows"}.
    검사 하나가 실패해도 끝까지 돌고(예외도 표의 한 줄), zip 은 항상 만든다. 저장 위치가 장비 NAS 아래면 시작 전에 거부."""
    roots = nas_guard.roots_for_cfg(cfg)
    nas_guard.assert_local(out_dir, roots)
    root = str(root or K.TEST_PATH_ROOT).strip()
    rec = _Rec(log, progress, should_stop)
    info = _env_info(cfg, root)
    now = dt.datetime.now()
    zip_name = f"AOI_path_test_{now:%Y%m%d_%H%M%S}.zip"

    try:
        def guard():
            hits = [r for r in roots if nas_guard.is_under(root, r)]
            return not hits, ("장비 NAS 아래가 아님" if not hits else f"장비 NAS({hits[0]}) 아래라 쓰지 않습니다") + f" · 장비 NAS 경로 {len(roots)}개와 비교"
        safe = rec.check("준비", "장비 NAS 와 다른 곳인가", guard)

        def reach():
            t0 = time.perf_counter()
            isdir = os.path.isdir(root)
            ms = (time.perf_counter() - t0) * 1000
            if not isdir:
                parent = os.path.dirname(root.rstrip("\\/"))
                return False, f"폴더에 닿지 못했습니다({ms:.0f}ms) — 상위 {parent!r} 은 {'열림' if os.path.isdir(parent) else '안 열림'}"
            t0 = time.perf_counter()
            names = os.listdir(root)
            return True, f"열림 {ms:.0f}ms · 나열 {len(names)}개 {(time.perf_counter() - t0) * 1000:.0f}ms"
        reachable = rec.check("준비", "공유 폴더에 닿는가", reach) if safe else None
        rec.artifacts["폴더목록/시험경로_맨위.txt"] = (_listing(root) + "\n").encode("utf-8") if reachable else "(닿지 못해 나열하지 않음)\n".encode("utf-8")

        if safe and reachable:
            for kind, sub, sizes in ((publish.LOT, K.TEST_PATH_LOT_DIR, SIZES_MB), (publish.FULL, K.TEST_PATH_FULL_DIR, SIZES_MB_SECOND)):
                if rec.stop():
                    break
                _test_folder(rec, kind, os.path.join(root, sub), sizes, roots, sub)
        elif safe and not rec.stopped:
            rec.rows.append({"group": "준비", "name": "나머지 시험", "ok": False, "ms": 0, "detail": "공유 폴더에 닿지 못해 쓰기 시험을 하지 않았습니다"})
    except Exception as exc:  # noqa: BLE001 - 예상 밖 오류도 zip 에 남긴다
        rec.rows.append({"group": "시험", "name": "예상 밖 오류", "ok": False, "ms": 0, "detail": traceback.format_exc()})
        if log:
            log(f"[배포 경로 시험] 예상 밖 오류: {type(exc).__name__}: {exc}")

    rows = rec.rows
    bad = sum(1 for r in rows if r["ok"] is False)
    members: Dict[str, bytes] = {
        "요약.txt": render_summary(info, rows, zip_name, rec.stopped).encode("utf-8"),
        "결과.json": json.dumps({"info": info, "rows": rows, "stopped": rec.stopped}, ensure_ascii=False, indent=2).encode("utf-8"),
        "검사표.tsv": ("그룹\t검사\t결과\t밀리초\t내용\n" + "\n".join(
            f"{r['group']}\t{r['name']}\t{'통과' if r['ok'] is True else '실패' if r['ok'] is False else '참고'}\t{r['ms']}\t{str(r['detail']).replace(chr(10), ' / ')}"
            for r in rows) + "\n").encode("utf-8"),
        "환경.txt": ("\n".join(f"{k}: {v}" for k, v in info.items()) + "\n\n장비 NAS 경로(쓰기 금지 구역):\n" + "\n".join(f"  {r}" for r in roots) + "\n").encode("utf-8"),
        "app_log_최근.txt": _log_tail(),
    }
    members.update(rec.artifacts)
    path = write_zip(out_dir, zip_name, members, roots)
    if log:
        log(f"[배포 경로 시험] 끝 — 실패 {bad}개 / {len(rows)}개 · {path}")
    return {"path": path, "ok": bad == 0 and not rec.stopped, "failed": bad, "total": len(rows), "stopped": rec.stopped, "rows": rows}
