"""D43 — 30일치 실데이터 상태 문구 213종의 **고정 fixture**(dev/samples/status_mapping_2026-09-18.tsv)와 Python·JS 분류가 같은지.

fixture 는 사람이 검토한 표다 — 같은 함수로 만들어 통과시키는 표가 아니라, 규칙을 바꾸면 어긋나는 문구가 여기서 드러난다.
JS 쪽은 Node 가 있을 때만(하네스의 classify 모드, 네트워크·쓰기 없음).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aoi_capacity import collect

ROOT = Path(__file__).resolve().parents[2]
TSV = ROOT / "dev" / "samples" / "status_mapping_2026-09-18.tsv"


def fixture():
    out = []
    for line in TSV.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or line.startswith("rows\t"):
            continue
        n, causes, outcome, norm, old, status = line.split("\t", 5)
        out.append({"rows": int(n), "causes": [c for c in causes.split(";") if c], "outcome": outcome, "norm": norm, "old": old, "status": status})
    return out


def test_fixture_covers_all_213_phrases_and_156109_rows():
    f = fixture()
    assert len(f) == 213 and sum(x["rows"] for x in f) == 156109
    assert len({x["status"] for x in f}) == 213


def test_python_classification_matches_the_reviewed_fixture():
    for x in fixture():
        assert collect.norm_causes(x["status"]) == x["causes"], x["status"]
        assert collect.norm_outcome(x["status"]) == x["outcome"], x["status"]
        assert collect.norm_status(x["status"]) == x["norm"], x["status"]
        assert not collect.is_unmapped_status(x["status"]), x["status"]     # 213종 전부 매핑됨 — 미분류 0


def test_acceptance_counts_from_the_fixture():
    """계획의 수용 기준을 fixture 로 확인한다(행 단위)."""
    f = fixture()
    rows = lambda pred: sum(x["rows"] for x in f if pred(x))
    assert rows(lambda x: x["causes"] == ["ID_READ_ERROR"] and x["outcome"] == "SKIPPED") == 192      # 건너뜀에 묻히던 ID 인식 실패
    assert rows(lambda x: x["status"] == "Focus Mapping Error. Batch Aborted.") == 35 and \
        next(x for x in f if x["status"] == "Focus Mapping Error. Batch Aborted.")["causes"] == ["FOCUS_MAPPING_ERROR"]
    assert rows(lambda x: x["status"] in ("Aborted.", "Aborted")) == 8976 + 3221 and \
        all(x["causes"] == [] and x["outcome"] == "ABORTED" for x in f if x["status"] in ("Aborted.", "Aborted"))
    assert rows(lambda x: x["status"] == "Cancelled") == 1 and next(x for x in f if x["status"] == "Cancelled")["outcome"] == "USER_CANCELLED"
    assert rows(lambda x: x["status"] == "-") == 2 and next(x for x in f if x["status"] == "-")["outcome"] == "UNKNOWN"
    other = [x for x in f if x["old"] == "OTHER"]
    assert sum(x["rows"] for x in other) == 38 and len(other) == 11
    assert sum(x["rows"] for x in other if x["causes"]) == 35 and len([x for x in other if x["causes"]]) == 9
    assert all("WAFER_LOST" in x["causes"] for x in f if "Batch Aborted. Skipped." in x["status"] and "move wafer" in x["status"])


@pytest.mark.skipif(not shutil.which("node"), reason="node 가 없는 환경")
def test_js_classification_matches_python_and_the_fixture():
    f = fixture()
    out = subprocess.run([shutil.which("node"), str(ROOT / "dev" / "tests" / "js_harness.js")],
                         input=json.dumps({"classify": [x["status"] for x in f]}), capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    assert out.returncode == 0, out.stderr
    js = json.loads(out.stdout)
    for x in f:
        j = js[x["status"]]
        assert j["causes"] == x["causes"] and j["outcome"] == x["outcome"] and j["norm_status"] == x["norm"] and not j["unmapped"], x["status"]
    extra = subprocess.run([shutil.which("node"), str(ROOT / "dev" / "tests" / "js_harness.js")],
                           input=json.dumps({"classify": ["Something new", "", "-"]}), capture_output=True, text=True, timeout=60, cwd=str(ROOT))
    j = json.loads(extra.stdout)
    assert j["Something new"]["unmapped"] and j["Something new"]["outcome"] == "UNKNOWN" and j[""]["norm_status"] == ""
