"""보관 샘플(dev/samples/*.html[.gz])에서 원천 행을 꺼내는 **유일한** 헬퍼.

- `id="embedded"` script 의 JSON 을 파싱하고, `cols` 를 **이름으로** 매핑한다(고정 17열 인덱스를 가정하지 않는다).
- `pooled` 에 있는 열만 `pool[index]` 로 되돌린다. 문자열 풀 범위 밖 번호·빠진 필수 열은 즉시 실패한다.
- eval · HTML 재실행 · 네트워크 · 쓰기 없음. 표준 라이브러리만 쓴다.
- `sha256` 으로 어떤 파일을 읽었는지 지문을 남긴다(전후 비교표의 input_sha).
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "dev" / "samples"
REQUIRED_COLS = ("device", "lot", "wafer_id", "status", "wafer_start_time", "wafer_end_time",
                 "batch_start", "batch_end", "report", "ini_match")


def read_bytes(path: Path) -> bytes:
    raw = Path(path).read_bytes()
    return gzip.decompress(raw) if str(path).endswith(".gz") else raw


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def embedded(text: str) -> dict:
    head = text.index('id="embedded">') + len('id="embedded">')
    tail = text.index("</script>", head)
    return json.loads(text[head:tail])


def unfold(emb: dict) -> Tuple[List[dict], dict]:
    """(rows, meta) — 열 이름 기반 복원 + 풀 검증."""
    cols = list(emb["cols"])
    missing = [c for c in REQUIRED_COLS if c not in cols]
    if missing:
        raise ValueError(f"필수 열이 없습니다: {missing}")
    pool = emb.get("pool") or []
    pooled = set(emb.get("pooled") or [])
    for c in pooled:
        if c not in cols:
            raise ValueError(f"pooled 열이 cols 에 없습니다: {c}")
    n_pool = len(pool)
    is_pooled = [c in pooled for c in cols]
    rows: List[dict] = []
    for a in emb["rows"]:
        if len(a) != len(cols):
            raise ValueError(f"행 길이 {len(a)} ≠ 열 수 {len(cols)}")
        o: Dict[str, str] = {}
        for i, c in enumerate(cols):
            v = a[i]
            if is_pooled[i]:
                if not isinstance(v, int) or not (0 <= v < n_pool):
                    raise ValueError(f"문자열 풀 범위 밖: 열 {c} 값 {v!r}")
                v = pool[v]
            o[c] = "" if v is None else v
        rows.append(o)
    return rows, dict(emb.get("meta") or {})


def load(path: Path) -> Tuple[List[dict], dict, str]:
    """→ (rows, meta, 파일 sha256). `.gz` 면 풀어서 읽되 sha 는 **파일 그대로** 의 것."""
    text = read_bytes(path).decode("utf-8")
    rows, meta = unfold(embedded(text))
    return rows, meta, sha256(path)


def sample_path(name: str) -> Path:
    p = SAMPLES / name
    if not p.exists() and (SAMPLES / (name + ".gz")).exists():
        p = SAMPLES / (name + ".gz")
    return p
