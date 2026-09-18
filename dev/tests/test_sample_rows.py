"""보관 샘플 헬퍼(sample_rows) — 이름 기반 열 복원과 문자열 풀 검증. 실데이터 gate 의 입력 지문도 여기서 확인한다."""
from __future__ import annotations

import pytest

import sample_rows

SAMPLE_30 = "AOI_capacity_2026-09-18_30일치.html"
SHA_30_GZ = "75101ef55605a05b9f1b819f67b863a2609e612bc2285b07f8bb69941603ae56"


def test_unfold_maps_columns_by_name_and_validates_the_pool():
    emb = {"cols": ["device", "lot", "wafer_id", "status", "wafer_start_time", "wafer_end_time", "batch_start", "batch_end",
                    "report", "ini_match", "extra"],
           "pooled": ["device", "lot", "wafer_id", "status", "batch_start", "batch_end", "report", "ini_match", "extra"],
           "pool": ["AOI-8", "LOT", "W1", "Pass", "b", "e", "rep.htm", "EXACT", "x"],
           "rows": [[0, 1, 2, 3, "2026-09-15T09:00:00", "2026-09-15T09:05:00", 4, 5, 6, 7, 8]], "meta": {"generated_iso": "2026-09-18T12:59:17"}}
    rows, meta = sample_rows.unfold(emb)
    assert rows[0]["device"] == "AOI-8" and rows[0]["extra"] == "x" and rows[0]["wafer_start_time"] == "2026-09-15T09:00:00"
    assert meta["generated_iso"] == "2026-09-18T12:59:17"
    bad = dict(emb, rows=[[0, 1, 2, 3, "", "", 4, 5, 6, 99, 8]])
    with pytest.raises(ValueError):
        sample_rows.unfold(bad)                                        # 풀 범위 밖
    with pytest.raises(ValueError):
        sample_rows.unfold(dict(emb, cols=emb["cols"][:-1], pooled=emb["pooled"][:-1]))   # 행 길이 ≠ 열 수
    with pytest.raises(ValueError):
        sample_rows.unfold({"cols": ["device"], "rows": [[0]], "pool": ["a"], "pooled": ["device"]})   # 필수 열 없음


@pytest.mark.slow
def test_thirty_day_sample_has_the_recorded_fingerprint_and_row_counts():
    """★ 실데이터 gate 의 입력. gz 지문과 행 수가 원장(ledger_2026-09-18.md)의 것과 같아야 전후 비교가 성립한다."""
    p = sample_rows.sample_path(SAMPLE_30)
    if not p.exists():
        pytest.skip("30일치 샘플이 없는 체크아웃")
    rows, meta, sha = sample_rows.load(p)
    assert sha == SHA_30_GZ
    assert len(rows) == 156109 and meta.get("generated_iso") == "2026-09-18T12:59:17"
    assert sum(1 for r in rows if r.get("kind") == "batch") == 863
    assert len({r["status"] for r in rows}) == 213
