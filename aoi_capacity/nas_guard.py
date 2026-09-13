"""NAS 읽기 전용 안전장치.

★ 절대 규칙: NAS 원본(Report/Scanresult 가 있는 공유) 아래에는 어떤 파일도 만들거나 바꾸거나 지우지 않는다.

이 모듈은 Qt 에 의존하지 않는 순수 함수들이다.
- `roots_for_cfg(cfg)`   설정과 devices.csv 에서 NAS 루트를 모두 모은다(사용 여부와 무관하게 전부).
                         드라이브 문자로 등록된 네트워크 드라이브는 드라이브 전체(X:\\)와 UNC 동치까지 넣는다.
- `assert_local(path, roots)`  path 가 어느 NAS 루트 아래면 `NasWriteRefused`.
- `check_cfg(cfg)`       cache_file / output_dir 이 NAS 아래가 아닌지 확인(collect 진입 시와 쓰기 직전, 이중 방어).
- `read_text/read_bytes/scandir`  NAS 를 읽을 때 쓰는 헬퍼(읽기 모드만 존재한다).

쓰기 API(`open(...,'w')`, `os.replace/rename/remove/makedirs`, `shutil.*`)는 collect.py 의
`_save_cache` · `write_html` · `_write_csv` 안에만 있고, 각 함수가 첫 줄에서 `assert_local` 을 부른다.
회귀 가드: dev/tests/test_nas_guard.py (정적 AST 검사 + 동적 트립와이어).
"""
from __future__ import annotations

import ntpath
import os
import re
from typing import Iterable, List, Optional

from . import i18n

_LONG_PREFIX = "\\\\?\\"


class NasWriteRefused(RuntimeError):
    """NAS 루트 아래에 쓰려는 시도. 호출부는 이 예외를 사용자에게 그대로 보여 준다."""


def normalize(path, pathmod=None) -> str:
    """비교용 정규화: 긴 경로 접두 제거 → 절대경로 → normpath → normcase(Windows 는 소문자, / → \\).

    `pathmod` 에 `ntpath` 를 주면 Linux 테스트에서도 Windows 의미론으로 검증할 수 있다."""
    pm = pathmod or os.path
    p = str(path).strip()
    if p.startswith(_LONG_PREFIX):
        p = p[len(_LONG_PREFIX):]
        if p.upper().startswith("UNC\\"):
            p = "\\\\" + p[4:]
    windows = pm is ntpath or pm.sep == "\\"
    if windows:
        p = p.replace("/", "\\")
        if re.fullmatch(r"[A-Za-z]:", p):
            p += "\\"
    if not pm.isabs(p):
        p = pm.abspath(p)
    return pm.normcase(pm.normpath(p))


def is_under(path, root, pathmod=None) -> bool:
    """path 가 root 와 같거나 그 아래인가(정규화 후 접두 비교)."""
    pm = pathmod or os.path
    r = normalize(root, pm)
    if not r:
        return False
    p = normalize(path, pm)
    if p == r:
        return True
    prefix = r if r.endswith(pm.sep) else r + pm.sep
    return p.startswith(prefix)


def _unc_for_drive(root: str) -> Optional[str]:
    """Windows 에서 드라이브 문자(X:\\...)가 네트워크 드라이브면 같은 위치의 UNC 경로. 아니면 None. 실패는 조용히 무시."""
    m = re.match(r"^([A-Za-z]):", root)
    if not m or os.name != "nt":
        return None
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.c_ulong(1024)
        rc = ctypes.windll.mpr.WNetGetConnectionW(m.group(1) + ":", buf, ctypes.byref(n))  # type: ignore[attr-defined]
        if rc == 0 and buf.value:
            return buf.value.rstrip("\\") + root[2:]
    except Exception:  # noqa: BLE001 - best effort
        pass
    return None


def _share_root(unc: str) -> Optional[str]:
    """\\\\host\\share\\a\\b → \\\\host\\share (공유 전체를 금지 구역으로)."""
    m = re.match(r"^(\\\\[^\\]+\\[^\\]+)", unc)
    return m.group(1) if m else None


def expand_roots(roots: Iterable[str]) -> List[str]:
    """등록된 NAS 경로를 금지 구역 목록으로 넓힌다: 네트워크 드라이브는 드라이브 전체 + UNC 동치, UNC 는 공유 루트까지."""
    out: List[str] = []
    for r in roots:
        r = str(r or "").strip()
        if not r:
            continue
        out.append(r)
        if r.startswith("\\\\"):
            share = _share_root(r)
            if share:
                out.append(share)
        else:
            unc = _unc_for_drive(r)
            if unc:
                out.append(unc)
                out.append(r[:2] + "\\")
                share = _share_root(unc)
                if share:
                    out.append(share)
    seen, uniq = set(), []
    for r in out:
        k = normalize(r)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def roots_for_cfg(cfg: dict) -> List[str]:
    """설정의 nas_roots + devices.csv 의 NAS경로(사용 여부 무관) 전부."""
    roots = list(cfg.get("nas_roots") or [])
    csv_path = cfg.get("devices_csv") or ""
    if csv_path and os.path.isfile(csv_path):
        from .devices import read_devices_csv  # 지연 import: devices 가 이 모듈을 import 한다

        for row in read_devices_csv(csv_path):
            if row.get("root"):
                roots.append(row["root"])
    return expand_roots(roots)


def assert_local(path, roots: Iterable[str], pathmod=None) -> None:
    for r in roots:
        if is_under(path, r, pathmod):
            raise NasWriteRefused(i18n.KO.NAS_WRITE_REFUSED_FMT.format(path=path, root=r))


def check_cfg(cfg: dict, roots: Optional[List[str]] = None) -> List[str]:
    """cache_file / output_dir 이 NAS 아래면 예외. 확인에 쓴 루트 목록을 돌려준다."""
    roots = roots if roots is not None else roots_for_cfg(cfg)
    for key in ("cache_file", "output_dir"):
        v = cfg.get(key)
        if v:
            assert_local(v, roots)
    return roots


# ── 읽기 헬퍼(쓰기 모드는 존재하지 않는다) ─────────────────────────────
def read_text(path, encoding: str = "utf-8", errors: str = "replace") -> str:
    with open(path, "r", encoding=encoding, errors=errors) as f:
        return f.read()


def read_bytes(path) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def scandir(path):
    return os.scandir(path)
