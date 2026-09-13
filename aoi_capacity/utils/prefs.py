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
from typing import Any, Dict, Optional

from . import paths

PREFS_VERSION = 1


@dataclass
class Prefs:
    backfill_days: int = 30
    retention_days: int = 90
    output_dir: str = ""              # 비우면 data_root()
    write_csv: bool = False
    report_dir: str = "Report"
    scan_dir: str = "Scanresult"
    threshold_util: int = 40          # 주의 장비: 가동률 미만
    threshold_err: int = 3            # 주의 장비: 오류 건수 이상
    color_mode: str = "dark"          # dark | light
    web_software_render: bool = False
    window_width: int = 0
    window_height: int = 0
    window_maximized: bool = False
    last_view: str = "home"
    auto_collect_minutes: int = 0     # 예약: 0 = 자동 수집 안 함(현재 UI 노출 없음)
    prefs_version: int = PREFS_VERSION
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Prefs":
        names = {f.name for f in dataclasses.fields(cls)}
        known = {k: v for k, v in (d or {}).items() if k in names}
        p = cls(**known)
        if not isinstance(p.extra, dict):
            p.extra = {}
        return p


def migrate(p: Prefs) -> Prefs:
    """버전 간 기본값 이동. 지금은 v1 이 최초라 아무것도 바꾸지 않는다."""
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
        "backfill_days": int(p.backfill_days),
        "retention_days": int(p.retention_days),
        "output_dir": str(paths.output_dir(p.output_dir)),
        "output_name": "AOI_capacity.html",
        "write_csv": bool(p.write_csv),
        "cache_file": str(paths.cache_file()),
    })
    return cfg
