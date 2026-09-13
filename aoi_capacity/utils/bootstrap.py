"""첫 실행 부트스트랩 — lite 배포의 의존성(requirements.txt) 설치 판단·실행.

exe-lite 배포(`scripts/build.py exe-lite`)는 라이브러리를 번들에 넣지 않고 `.deps_installed` 표식도
남기지 않는다. 표식이 없다는 사실이 곧 '아직 설치 안 됨' 신호이고, `main.py` 가 PyQt6 를 import 하기
전에 `ensure_deps()` 를 불러 pip 로 채운다.

- 순수 함수(표식 지문·pip 명령 구성)와 부수효과(`run`)를 분리해 헤드리스 테스트가 가능하다. 테스트는 실제 pip 을 절대 돌리지 않는다.
- `PY_STANDALONE_URL` 은 **단 하나의 출처**다 — 빌드(`scripts/build.py`)가 여기서 가져간다.
- 콘솔 문구는 i18n 에만 둔다. `ko.py` 는 표준 라이브러리만 쓰는 순수 상수 모듈이라 설치 전에도 안전하다.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Callable, List, Optional

from .. import i18n
from . import paths

MARKER_NAME = ".deps_installed"

# python-build-standalone 의 'install_only' Windows x86_64 (자체 포함 CPython).
# 404 가 나면 https://github.com/astral-sh/python-build-standalone/releases 에서 최신 install_only 링크로 바꾼다.
PY_STANDALONE_URL = (
    "https://github.com/astral-sh/python-build-standalone/releases/download/"
    "20250115/cpython-3.11.11+20250115-x86_64-pc-windows-msvc-install_only.tar.gz"
)


# ── 순수 로직 ──
def req_lines(req_text: Optional[str]) -> List[str]:
    """실제 요구사항 줄만(주석·빈 줄 제거). 주석만 바뀐 것을 '의존성 변경' 으로 오인하지 않게."""
    out: List[str] = []
    for line in (req_text or "").splitlines():
        s = line.split("#", 1)[0].strip()
        if s:
            out.append(s)
    return out


def req_fingerprint(req_text: Optional[str]) -> str:
    return hashlib.sha1("\n".join(req_lines(req_text)).encode("utf-8")).hexdigest()


def deps_marker(root: Path) -> Path:
    return Path(root) / MARKER_NAME


def deps_installed(root: Path, req_text: Optional[str]) -> bool:
    """이 requirements 내용으로 설치가 끝났는가(표식 내용 = 지문). req_text 가 None 이면 존재만 본다."""
    mk = deps_marker(root)
    if not mk.exists():
        return False
    if req_text is None:
        return True
    try:
        return mk.read_text(encoding="utf-8").strip() == req_fingerprint(req_text)
    except OSError:
        return False


def write_deps_marker(root: Path, req_text: Optional[str]) -> bool:
    try:
        deps_marker(root).write_text(req_fingerprint(req_text) if req_text else "installed", encoding="utf-8")
        return True
    except OSError:
        return False


def pip_install_cmd(python_exe: str, req_file: Path) -> List[str]:
    """빠진 것만 채운다 — `--upgrade` 없음(CLAUDE.md 규칙 7). `-s` 로 개인 site-packages 를 배제."""
    return [str(python_exe), "-s", "-m", "pip", "install", "-r", str(req_file)]


# ── 오케스트레이션 ──
def _default_run(cmd: List[str]) -> int:
    return subprocess.call(cmd)


def ensure_deps(root: Optional[Path] = None, python_exe: Optional[str] = None, req_file: Optional[Path] = None,
                run: Callable[[List[str]], int] = _default_run,
                log: Callable[[str], None] = lambda _m: None) -> bool:
    """설치 루트의 의존성을 확인하고 없으면 pip 로 설치한다. True = 사용 가능.

    설치가 실패하면 표식을 **쓰지 않는다** — 거짓 표식은 다음 실행이 설치를 영원히 건너뛰게 만든다."""
    root = Path(root) if root is not None else paths.install_root()
    if root is None:
        return True                          # 개발 트리: 판단하지 않는다
    req_file = Path(req_file) if req_file is not None else root / "app" / "requirements.txt"
    if not req_file.is_file():
        return True
    try:
        req_text = req_file.read_text(encoding="utf-8")
    except OSError:
        return True
    if deps_installed(root, req_text):
        return True
    log(i18n.KO.BOOT_DEPS_INSTALLING)
    if run(pip_install_cmd(python_exe or sys.executable, req_file)) != 0:
        log(i18n.KO.BOOT_DEPS_FAILED)
        return False
    write_deps_marker(root, req_text)
    log(i18n.KO.BOOT_DEPS_DONE)
    return True
