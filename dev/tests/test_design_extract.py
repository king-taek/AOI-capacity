"""디자인 세션의 추출 스크립트(docs/design/dashboard-redesign/scripts/make_aoi_data.js) 가드.

- 9/20 확인: 원본 입력(`AOI_capacity 3.html`, 20MB)으로 돌리면 저장소의 `app/aoi-data.json` 과 **바이트 단위로 같다**(2,246,736 bytes).
  그 원본은 저장소에 없으므로 여기서는 제품 30일치 샘플로 **돌아가는지와 출력 계약**만 본다. Node 가 없으면 skip. 네트워크·NAS 없음.
"""
from __future__ import annotations

import gzip
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "docs" / "design" / "dashboard-redesign" / "scripts" / "make_aoi_data.js"
SAMPLE = ROOT / "dev" / "samples" / "AOI_capacity_2026-09-18_30일치.html.gz"


def test_extract_script_is_shipped_verbatim_with_its_shim():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "[원본]" in src and "function dayStats(" in src and "const CR=[" in src
    assert "if(gap>240)gap=240;" in src            # D48 제품 유지 항목 ① — 이식 때 관측 종료까지로 바꾼다
    assert "Math.min(1440," in src                 # D48 제품 유지 항목 ② — 이식 때 오늘은 마지막 스캔까지로 바꾼다


@pytest.mark.slow
def test_extract_script_runs_on_the_product_sample(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음")
    if not SAMPLE.is_file():
        pytest.skip("30일치 샘플 없음")
    src = tmp_path / "in.html"
    src.write_bytes(gzip.decompress(SAMPLE.read_bytes()))
    out = tmp_path / "aoi-data.json"
    r = subprocess.run([node, "--max-old-space-size=4096", str(SCRIPT), str(src), str(out)], capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-800:]
    d = json.loads(out.read_text(encoding="utf-8"))
    assert set(d) == {"day", "generated", "devices", "days", "pool", "detail", "jobG", "jobGroups", "scope"}
    assert len(d["devices"]) == 30 and len(d["days"]) >= 30
    t = d["detail"][d["days"][-1]]
    one = next(iter(t.values()))
    assert {"r", "x", "t", "d", "s", "w", "e", "seg", "ct", "lots", "cv", "bseg", "be"} <= set(one)
    assert len(d["jobG"]) == len(d["pool"]["job"]) and all(0 <= g < len(d["jobGroups"]) for g in d["jobG"])
