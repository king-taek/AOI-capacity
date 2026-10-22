"""끊긴 KLA 네트워크 드라이브 다시 연결 (10/22).

KLA 드라이브(Z: W: U: T: …)는 PC 를 다시 켜거나 한참 지나면 '연결 끊김' 이 되고, 그러면 수집이 `[건너뜀]` 으로 지나갔다.
`kla_drives.txt` 에 비밀번호가 적혀 있으면 수집 직전에 그 드라이브만 다시 연결한다.

* 파일: 결과 폴더(설정 `output_dir`) 또는 데이터 폴더의 `kla_drives.txt`. 한 줄이면 비밀번호(모든 드라이브 공통, 현재 Windows 계정으로 연결),
  두 줄이면 첫 줄 계정 · 둘째 줄 비밀번호. 이 파일은 저장소·업데이트 배포물에 들어가지 않는다(로컬 전용).
* 원격 주소는 Windows 가 기억하는 드라이브 연결(`WNetGetConnection`)에서 읽는다 — 새로 지어내지 않는다.
* ★ 범위 게이트(`devices_from_rows`)를 지난 KLA 행만 부른다. NAS 에는 아무것도 쓰지 않는다(연결만 다시 맺는다).
* 비밀번호는 로그·화면·예외 문구에 절대 남기지 않는다.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from .utils import paths

FILE_NAME = "kla_drives.txt"
_DRIVE_RE = re.compile(r"^([A-Za-z]):")
IS_WINDOWS: Callable[[], bool] = lambda: os.name == "nt"


def password_files(cfg: dict) -> List[Path]:
    out: List[Path] = []
    configured = str((cfg or {}).get("output_dir") or "")
    if configured:
        out.append(Path(configured) / FILE_NAME)
    out.append(paths.data_root() / FILE_NAME)
    return out


def read_credentials(cfg: dict) -> Optional[Tuple[Optional[str], str]]:
    """(계정 또는 None, 비밀번호). 파일이 없거나 비었으면 None."""
    for p in password_files(cfg):
        try:
            text = p.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if len(lines) == 1:
            return None, lines[0]
        if len(lines) >= 2:
            return lines[0], lines[1]
    return None


def _remote_of(letter: str) -> Optional[str]:
    """Windows 가 기억하는 `\\\\서버\\공유`. 끊긴 드라이브도 기억은 남아 있다."""
    import ctypes

    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.c_ulong(1024)
    rc = ctypes.windll.mpr.WNetGetConnectionW(letter + ":", buf, ctypes.byref(n))  # type: ignore[attr-defined]
    return buf.value.rstrip("\\") if rc in (0, 1201) and buf.value else None   # 1201 = 기억만 남고 끊긴 연결 — 주소는 채워 준다


def _win_connect(letter: str, remote: str, user: Optional[str], password: str) -> Tuple[bool, str]:
    """끊긴 연결을 풀고 같은 드라이브 문자로 다시 맺는다 → (성공, 오류 번호 문구). 비밀번호는 명령줄에 싣지 않는다(API 호출)."""
    import ctypes
    from ctypes import wintypes

    class NETRESOURCE(ctypes.Structure):
        _fields_ = [("dwScope", wintypes.DWORD), ("dwType", wintypes.DWORD), ("dwDisplayType", wintypes.DWORD),
                    ("dwUsage", wintypes.DWORD), ("lpLocalName", wintypes.LPWSTR), ("lpRemoteName", wintypes.LPWSTR),
                    ("lpComment", wintypes.LPWSTR), ("lpProvider", wintypes.LPWSTR)]

    mpr = ctypes.windll.mpr  # type: ignore[attr-defined]
    local = letter + ":"
    mpr.WNetCancelConnection2W(local, 0, True)          # 끊긴 채 남은 연결 정리(없으면 오류 코드만 돌아온다)
    nr = NETRESOURCE(1, 1, 0, 0, local, remote, None, None)   # RESOURCE_CONNECTED(연결 추가에는 무시됨) · RESOURCETYPE_DISK
    rc = mpr.WNetAddConnection2W(ctypes.byref(nr), password, user, 1)   # CONNECT_UPDATE_PROFILE — 다시 켜도 기억
    return rc == 0, f"Windows 오류 {rc}"


CONNECT: Callable[[str, str, Optional[str], str], Tuple[bool, str]] = _win_connect
REMOTE_OF: Callable[[str], Optional[str]] = _remote_of


def reconnect(path: str, cfg: dict) -> Tuple[bool, List[str]]:
    """`Z:\\` 같은 KLA 드라이브를 다시 연결해 본다 → (연결됨, 로그 줄). 파일이 없거나 Windows 가 아니면 (False, [])."""
    m = _DRIVE_RE.match(str(path or ""))
    if not m or not IS_WINDOWS():
        return False, []
    cred = read_credentials(cfg)
    if cred is None or not cred[1]:
        return False, []
    letter = m.group(1).upper()
    try:
        remote = REMOTE_OF(letter)
    except Exception as ex:  # noqa: BLE001 - 주소를 못 읽으면 건너뜀 그대로
        return False, [f"[{letter}:] 드라이브 연결 주소를 읽지 못했습니다 — {type(ex).__name__}"]
    if not remote:
        return False, [f"[{letter}:] 드라이브 연결 주소를 알 수 없어 다시 연결하지 못합니다(탐색기에서 한 번 연결해 두세요)"]
    try:
        ok, why = CONNECT(letter, remote, cred[0], cred[1])
    except Exception as ex:  # noqa: BLE001
        return False, [f"[{letter}:] 다시 연결 실패 — {type(ex).__name__}"]
    return ok, [f"[{letter}:] {remote} 다시 연결 {'성공' if ok else '실패 (' + why + ')'}"]
