"""수집 허용 장비 범위(scope) — 지금은 30대 전부(`DEFAULT_SCOPE`).

★ 절대 규칙: 허용 목록 밖 장비에는 **파일 접근을 하지 않는다**(scandir / stat / isdir / isfile / open).
  그래서 게이트는 "파일을 만지기 전" 단계인 `devices.py` 에 걸리고, 수집 루프·CLI·백필·예약 실행·
  연결 확인이 모두 같은 함수를 쓴다. 회귀 가드: `dev/tests/test_scope_isolation.py`.

- 비교는 **이름만** 본다(경로는 PC 마다 다르다). `key()` 로 공백·밑줄·하이픈을 지우고 소문자로 맞춘다:
  `AOI-25` == `aoi 25` == `AOI_25`.
- `폴더 *`(자동 탐색) 행은 공유 폴더를 나열해야 어떤 장비인지 알 수 있다 → **나열 자체가 다른 장비 접근**이라
  범위 제한 중에는 그 행을 통째로 건너뛴다(`allows_auto_row`).
- 탈출구: 범위에 `"*"` 하나만 넣으면 제한이 없어진다(되돌리기·향후 확장용, 기본값 아님).
- 이 모듈은 파일시스템도 Qt 도 건드리지 않는 순수 함수다.
"""
from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Sequence

#: 현재 수집 대상 — 30대 전부(사용자 확정). 4대(AOI-1·8·9·25) 현장 테스트를 마치고 넓혔다.
#: 바꿀 때는 README·CLAUDE.md 와 dev/tests/test_scope_isolation.py, 그리고
#: prefs.migrate(이미 저장된 설정을 새 기본값으로 옮긴다)를 함께 본다.
DEFAULT_SCOPE: List[str] = (
    [f"AOI-{i}" for i in range(1, 26)] + [f"4F-AOI-{i:02d}" for i in range(1, 6)]
)
#: 지금까지 기본값이었던 목록들 — 사용자가 직접 고르지 않고 그대로 둔 설정만 새 기본값으로 옮긴다.
PAST_DEFAULTS: List[List[str]] = [["AOI-25"], ["AOI-1", "AOI-8", "AOI-9", "AOI-25"]]
ANY = "*"
CFG_KEY = "scope_devices"


def key(name) -> str:
    """비교용 키 — 공백·밑줄·하이픈 제거 후 소문자."""
    return re.sub(r"[\s_\-]+", "", str(name or "")).lower()


def scope_list(cfg: Dict[str, object] | None = None) -> List[str]:
    """설정의 허용 목록. 없거나 비었으면 기본값(빈 목록을 '아무것도 허용 안 함' 으로 오해하지 않는다)."""
    raw = (cfg or {}).get(CFG_KEY)
    if isinstance(raw, str):
        raw = [raw]
    items = [str(x).strip() for x in (raw or []) if str(x).strip()]
    return items or list(DEFAULT_SCOPE)


def unrestricted(cfg: Dict[str, object] | None = None) -> bool:
    return ANY in scope_list(cfg)


def allowed_keys(cfg: Dict[str, object] | None = None) -> set:
    return {key(x) for x in scope_list(cfg)}


def is_allowed(cfg: Dict[str, object] | None, *candidates) -> bool:
    """후보 이름(장비명·폴더명·경로의 마지막 조각) 중 하나라도 허용 목록에 있으면 True."""
    if unrestricted(cfg):
        return True
    keys = allowed_keys(cfg)
    return any(key(c) in keys for c in candidates if str(c or "").strip())


def path_tail(path) -> str:
    """경로의 마지막 폴더 이름. 구분자는 Windows·POSIX 둘 다 본다."""
    return re.split(r"[\\/]+", str(path or "").rstrip("\\/"))[-1] if path else ""


def row_candidates(row: Dict[str, object]) -> List[str]:
    """devices.csv 행 하나에서 뽑는 이름 후보 — 파일시스템을 전혀 건드리지 않는다."""
    name = str(row.get("name") or "")
    sub = str(row.get("sub") or "").strip()
    root = str(row.get("root") or "")
    out = [name, sub, path_tail(os.path.join(root, sub) if sub else root)]
    return [c for c in out if c.strip()]


def allows_row(cfg: Dict[str, object] | None, row: Dict[str, object]) -> bool:
    return is_allowed(cfg, *row_candidates(row))


def allows_auto_row(cfg: Dict[str, object] | None = None) -> bool:
    """`폴더 *` 자동 탐색을 해도 되는가 — 제한이 걸려 있으면 안 된다(공유 나열 = 다른 장비 접근)."""
    return unrestricted(cfg)


def describe(cfg: Dict[str, object] | None = None) -> str:
    return "제한 없음" if unrestricted(cfg) else ", ".join(scope_list(cfg))
