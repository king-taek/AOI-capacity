"""사용자 설정(prefs.json) — 이 PC 에만 저장.

- 한 개의 flat dataclass + `extra` 탈출구. `from_dict` 는 모르는 키를 버리므로 파일 버전이 앞뒤로 어긋나도 깨지지 않는다.
- `load()` 는 절대 예외를 내지 않는다(없거나 깨지면 기본값). 저장은 tmp → replace 로 원자적.
- `patch(**fields)` 가 호출부의 유일한 갱신 API.
- `migrate()` 는 순수 함수: 기본값을 바꿀 때 "옛 기본값 그대로인 값" 만 새 기본값으로 옮긴다(사용자가 고른 값은 보존).
"""
from __future__ import annotations

import copy
import dataclasses
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .. import scope as _scope
from . import config as _config
from . import paths

PREFS_VERSION = 7


@dataclass
class Prefs:
    backfill_days: int = 30
    read_workers: int = 8
    retention_days: int = 0           # 이력 보관 기간(일) — 0 = 기한 없이(10/5 사용자 확정)
    output_dir: str = ""              # 비우면 data_root()
    write_csv: bool = False
    report_dir: str = "Report"
    scan_dir: str = "Scanresult"
    threshold_util: int = 40          # 주의 장비: 가동률 미만
    threshold_err: int = 3            # 주의 장비: 오류 건수 이상
    color_mode: str = "light"         # light | dark — 9/23 부터 라이트가 기본(결과 HTML 과 같은 모양)
    window_width: int = 0
    window_height: int = 0
    window_maximized: bool = False
    last_view: str = "collect"
    scope_devices: List[str] = field(default_factory=lambda: list(_scope.DEFAULT_SCOPE))  # ★ 수집 허용 장비
    refresh_pick_days: int = 3        # 수집 페이지 '최근 N일 다시 읽기' 카드의 N(고를 때만 refresh_window_days 로 들어간다)
    html_days: int = 30               # 수집 뒤 결과 HTML 에 담을 최근 일수(0 = 전부, 기본 1달 — 10/5 사용자). 전체 기간은 수집 창 버튼
    refresh_window_days: int = 0      # D60: 최근 N일 안의 Report 는 캐시에 있어도 다시 읽기(0 = 끔). 수집 페이지 체크박스가 켜고 끈다
    prefs_version: int = PREFS_VERSION
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Prefs":
        """모르는 키는 버리고, 아는 키는 **형을 검사해** 받는다(C13) — 잘못된 값 하나 때문에 파일 전체를 기본값으로 되돌리지 않는다.

        정수·참/거짓·문자열 필드는 `utils.config` 의 같은 규칙으로 읽고, 못 읽으면 그 필드만 기본값이다.
        `prefs_version` 이 잘못돼도 장비 목록(`scope_devices`)은 그대로 둔다(현재 버전으로 간주해 이동하지 않는다).
        `scope_devices` 는 목록/문자열이면 그대로 두어 실행 시점의 `normalize_config` 가 판정한다(잘못된 항목을 조용히 넓히지 않는다)."""
        fields = {f.name: f for f in dataclasses.fields(cls)}
        raw = d if isinstance(d, dict) else {}
        known: Dict[str, Any] = {}
        for k, v in raw.items():
            f = fields.get(k)
            if f is None:
                continue
            default = f.default if f.default is not dataclasses.MISSING else f.default_factory()  # type: ignore[misc]
            if k == "scope_devices":
                if isinstance(v, str):
                    v = [v]
                known[k] = v if isinstance(v, list) else (default if v is None else v)
            elif k == "extra":
                known[k] = v if isinstance(v, dict) else {}
            elif isinstance(default, bool):
                b = _config.parse_bool(v)
                known[k] = default if b is None else b
            elif isinstance(default, int):
                n = _config.parse_int(v)
                known[k] = default if n is None else n
            elif isinstance(default, str):
                known[k] = v if isinstance(v, str) else default
            else:
                known[k] = v
        return cls(**known)


def migrate(p: Prefs) -> Prefs:
    """버전 간 기본값 이동 — **옛 기본값 그대로인 값만** 새 기본값으로 옮긴다(사용자가 고른 값은 보존).

    v2: 수집 범위가 AOI-25 한 대에서 AOI-1 · AOI-8 · AOI-9 · AOI-25 로 늘었다.
    v3: 4대 현장 테스트를 마치고 30대 전부로 늘었다(사용자 확정).
        어느 쪽이든 **옛 기본값 그대로인 설정만** 새 목록으로 바꾼다 — `_scope.PAST_DEFAULTS` 참조.
    v4(9/23): 화면 기본이 어두운 화면 → 밝은 화면(결과 HTML 과 같은 모양, 사용자 요청). 옛 기본값("dark")인 설정만 옮긴다 —
        v4 뒤에 사용자가 어두운 화면을 고르면 그대로 남는다.
    v5(10/5): 이력은 **기한 없이 보관**(사용자 확정 — '데이터는 계속 쌓아 놓고'). 고른 값과 상관없이 0(기한 없음)으로 옮긴다.
    v6(10/5): 수집 범위에 KLA 8대 추가 — 옛 기본 30대 그대로인 설정만 38대로(`_scope.PAST_DEFAULTS`).
    v7(10/5): 결과 HTML 기본 기간 60일 → 1달(30일, 사용자 요청) — 옛 기본값 60 그대로인 설정만."""
    if p.prefs_version < PREFS_VERSION and list(p.scope_devices or []) in _scope.PAST_DEFAULTS:
        p.scope_devices = list(_scope.DEFAULT_SCOPE)
    if p.prefs_version < 4 and p.color_mode == "dark":
        p.color_mode = "light"
    if p.prefs_version < 5:
        p.retention_days = 0
    if p.prefs_version < 7 and int(p.html_days) == 60:
        p.html_days = 30
    if p.prefs_version < PREFS_VERSION:
        p.prefs_version = PREFS_VERSION
    return p


_cached: Optional[tuple] = None  # (path, mtime_ns, size, Prefs)


def load() -> Prefs:
    global _cached
    path = paths.prefs_file()
    try:
        st = os.stat(path)
        key = (str(path), st.st_mtime_ns, st.st_size)
        if _cached and _cached[:3] == key:
            return copy.deepcopy(_cached[3])
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        p = migrate(Prefs.from_dict(data if isinstance(data, dict) else {}))
        _cached = key + (copy.deepcopy(p),)
        return p
    except Exception:  # noqa: BLE001 - 없거나 깨진 파일은 기본값
        return Prefs()


def save(p: Prefs) -> None:
    global _cached
    path = paths.prefs_file()
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p.to_dict(), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    _cached = None


def patch(**fields: Any) -> Prefs:
    p = load()
    for k, v in fields.items():
        if not hasattr(p, k):
            raise AttributeError(k)
        setattr(p, k, v)
    save(p)
    return p


def to_collect_cfg(p: Prefs) -> Dict[str, Any]:
    """수집 코어가 받는 cfg. 경로는 전부 이 PC 의 데이터 폴더(또는 사용자가 고른 로컬 폴더)."""
    from .. import collect

    cfg = copy.deepcopy(collect.DEFAULT_CONFIG)
    cfg.update({
        "devices_csv": str(paths.devices_csv_path()),
        "nas_roots": [],
        "report_dir": p.report_dir or "Report",
        "scan_dir": p.scan_dir or "Scanresult",
        "backfill_days": p.backfill_days,
        "read_workers": p.read_workers,
        "retention_days": p.retention_days,
        "output_dir": str(paths.output_dir(p.output_dir)),
        "output_name": "AOI_capacity.html",
        "write_csv": p.write_csv,
        "cache_file": str(paths.cache_file()),
        "scope_devices": list(p.scope_devices) if isinstance(p.scope_devices, list) and p.scope_devices else
                         (p.scope_devices if p.scope_devices else list(_scope.DEFAULT_SCOPE)),
        "refresh_window_days": p.refresh_window_days,
        "rebuild_all": False,          # GUI 의 '전체 다시 만들기' 는 워커 인자(full)로 넘긴다 — 설정에 남기지 않는다
        "attention_util": p.threshold_util,   # D14: 결과 HTML 의 meta.dashboard_settings 로 나간다(prefs 의 이름은 옛 그대로 threshold_*)
        "attention_err": p.threshold_err,
        "html_days": p.html_days,
    })
    # ★ CLI(config.json)와 같은 규칙으로 정규화한다 — 성능·기간 값은 고치고, 범위·경로 문제는 그대로 두어 수집 진입점이 막는다(C13)
    cfg, _problems = _config.normalize_config(cfg)
    return cfg
