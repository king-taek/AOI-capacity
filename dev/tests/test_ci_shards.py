"""CI 조각 나누기(`AOI_SHARD`) — 조각들을 합치면 전체와 정확히 같고 서로 겹치지 않는다(빠지는 테스트가 없어야 초록불이 믿을 만하다)."""
from __future__ import annotations

import conftest


class _It:
    def __init__(self, nodeid):
        self.nodeid = nodeid


def test_shards_partition_all_tests_exactly():
    items = [_It(f"dev/tests/test_{c}.py::t{k}") for c in "bacde" for k in range(7)]
    picks = [conftest.shard_pick(items, f"{i}/3") for i in (1, 2, 3)]
    ids = [it.nodeid for part in picks for it in part]
    assert sorted(ids) == sorted(it.nodeid for it in items) and len(ids) == len(set(ids))
    assert max(map(len, picks)) - min(map(len, picks)) <= 1
    assert conftest.shard_pick(items, "") == items
