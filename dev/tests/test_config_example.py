"""docs/config.example.json 가드(S13) — 헤드리스 설정 예시가 `collect.DEFAULT_CONFIG` 와 조용히 어긋나지 않게.

- 예시의 공개 키(`_` 로 시작하지 않는 것)는 전부 DEFAULT_CONFIG 에 있고 값의 **타입이 같다**(bool 과 int 를 구분한다).
- DEFAULT_CONFIG 의 공개 키는 전부 예시에 있다 — 예외는 `NOT_IN_EXAMPLE` 에 이름을 적고 이유를 남긴다(무조건 모든 내부 키를 노출하지 않는다).
- `cli.load_config` 로 실제로 읽힌다(NAS 없이, 파일만).
"""
from __future__ import annotations

import json
from pathlib import Path

from aoi_capacity import cli, collect, scope

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "docs" / "config.example.json"
#: DEFAULT_CONFIG 에는 있지만 예시에 일부러 넣지 않는 키 — 지금은 없다. 화면 문턱(attention_util·attention_err)이 설정 키로 들어오면
#: 여기서 이름을 빼고 예시에 넣거나, 내부 키로 남길 이유를 적는다.
NOT_IN_EXAMPLE: frozenset[str] = frozenset()   # 지금은 공개 키 전부가 예시에 있다


def _example() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def _public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def test_example_public_keys_are_a_subset_of_default_config_with_the_same_types():
    ex = _public(_example())
    unknown = set(ex) - set(collect.DEFAULT_CONFIG)
    assert not unknown, f"DEFAULT_CONFIG 에 없는 키가 예시에 있다: {sorted(unknown)}"
    for k, v in ex.items():
        assert type(v) is type(collect.DEFAULT_CONFIG[k]), f"{k}: 예시 {type(v).__name__} ≠ 기본 {type(collect.DEFAULT_CONFIG[k]).__name__}"


def test_every_default_config_key_is_in_the_example_or_explicitly_excused():
    missing = set(collect.DEFAULT_CONFIG) - set(_public(_example()))
    assert missing <= NOT_IN_EXAMPLE, f"예시에 빠진 공개 키: {sorted(missing - NOT_IN_EXAMPLE)}"


def test_example_scope_and_workers_show_the_real_defaults():
    ex = _public(_example())
    assert ex["scope_devices"] == list(scope.DEFAULT_SCOPE), "예시의 수집 범위는 scope.py 의 기본 목록 그대로 — 목록이 바뀌면 여기도"
    assert ex["read_workers"] == collect.READ_WORKERS


def test_example_loads_through_the_cli_loader(tmp_path):
    src = tmp_path / "config.json"
    src.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = cli.load_config(str(src))
    ex = _public(_example())
    for k, v in ex.items():
        assert cfg[k] == v, k
    assert not any(k.startswith("_") for k in cfg), "설명 키(_…)는 cfg 로 들어오지 않는다"
