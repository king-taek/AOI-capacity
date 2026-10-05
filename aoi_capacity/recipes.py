"""레시피 묶음(사용자가 결과 HTML 안에서 만든 Job 묶음) — 수집기가 다음 HTML 에 담는다(D67).

화면(template)의 '레시피 묶음' 편집기가 `recipe_groups.json` 을 내보낸다:
    {"v": 1, "saved": "2026-10-05T12:00:00", "groups": [{"name": "TB500 RDL3", "jobs": ["원문 Job", …]}, …]}
`write_html` 이 이 파일을 찾아 `meta.recipe_groups` 로 넣으면, 새 HTML 은 열 때부터 그 묶음으로 집계한다.

찾는 곳: cfg `recipe_groups_file` 이 있으면 그 파일 하나. 비어 있으면 데이터 폴더의 `recipe_groups.json` 과
다운로드 폴더의 `recipe_groups*.json`(브라우저가 `recipe_groups (1).json` 처럼 번호를 붙인다) 중 **안에 적힌 `saved` 가 가장 늦은 것**.
읽기만 한다 — 이 모듈은 파일을 만들거나 고치지 않는다. 묶음은 통계·표시에만 쓰이고 Rescan 판정(자재 키)에는 쓰이지 않는다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

FILE_NAME = "recipe_groups.json"
MAX_BYTES = 8 * 1024 * 1024
MAX_GROUPS = 2000
MAX_JOBS = 20000


def normalize(data: Any) -> Optional[dict]:
    """모양을 검사해 깨끗한 사본을 돌려준다. 모양이 틀리면 None. 이름이 비거나 겹치는 묶음, 다른 묶음에 이미 든 Job 은 뺀다."""
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        return None
    saved = data.get("saved")
    out, names, taken = [], set(), set()
    for g in data["groups"][:MAX_GROUPS]:
        if not isinstance(g, dict):
            continue
        name = g.get("name")
        jobs = g.get("jobs")
        if not isinstance(name, str) or not name.strip() or not isinstance(jobs, list):
            continue
        name = name.strip()
        if name in names:
            continue
        keep = []
        for j in jobs:
            if isinstance(j, str) and j not in taken and len(taken) < MAX_JOBS:
                taken.add(j)
                keep.append(j)
        if keep:
            names.add(name)
            out.append({"name": name, "jobs": keep})
    return {"v": 1, "saved": saved if isinstance(saved, str) else "", "groups": out}


def _read(path: Path) -> Optional[dict]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return None
        return normalize(json.loads(path.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
        return None


def candidates(cfg: dict) -> List[Path]:
    explicit = str(cfg.get("recipe_groups_file") or "").strip()
    if explicit:
        return [Path(explicit)]
    from .utils import paths

    out = [paths.data_root() / FILE_NAME]
    for base in (os.environ.get("USERPROFILE"), str(Path.home())):
        if not base:
            continue
        dl = Path(base) / "Downloads"
        try:
            found = sorted(p for p in dl.glob("recipe_groups*.json") if p.is_file())
        except OSError:
            found = []
        out += [p for p in found if p not in out]
    return out


def load(cfg: dict, log: Optional[Callable[[str], None]] = None) -> Tuple[Optional[dict], str]:
    """(묶음, 쓴 파일 경로). 찾지 못하면 (None, "")."""
    best, best_path = None, ""
    for p in candidates(cfg):
        d = _read(p)
        if d is None:
            continue
        if best is None or d["saved"] > best["saved"]:
            best, best_path = d, str(p)
    if log:
        if best is not None:
            log(f"레시피 묶음 {len(best['groups'])}개를 담습니다 — {best_path} (저장 {best['saved'] or '시각 없음'})")
        elif str(cfg.get("recipe_groups_file") or "").strip():
            log(f"레시피 묶음 파일을 읽지 못했습니다: {cfg.get('recipe_groups_file')}")
    return best, best_path
