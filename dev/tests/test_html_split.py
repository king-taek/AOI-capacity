"""결과 HTML 분할(9/23) — 한도(`split_mb`)를 넘으면 기간별 자립형 HTML 여러 장.

- 가장 최근 구간이 원래 이름, 옛 구간은 `AOI_capacity_<첫날>~<끝날>.html`, 각 파일은 한도 이하.
- 구간은 겹치지 않고 빈틈 없이 이어지며, 화면 모델(buildModel)은 파일마다 자기 구간의 날만 그린다.
- 경계 앞뒤 하루치 행과 같은 Wafer 의 앞선 시도를 맥락으로 더 넣으므로 **각 날의 장비-일 값이 나누지 않은 파일과 같다**(자정 넘는 배치·Rescan·대기).
- 다음 수집에서 필요 없어진 옛 구간 파일은 정리하되 그 이름 모양 밖의 파일은 건드리지 않는다."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aoi_capacity import collect
from aoi_capacity.utils import paths
import sample_rows

HARNESS = Path(__file__).with_name("js_harness.js")


def _cfg(out: Path, split_mb: int) -> dict:
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(out), "cache_file": str(out / "c.json"), "split_mb": split_mb, "scope_devices": ["*"]})
    return cfg


def _embedded(path: Path) -> dict:
    return sample_rows.embedded(path.read_text(encoding="utf-8"))


def _model(emb: dict) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node 가 없어 화면 모델을 돌릴 수 없음")
    out = subprocess.run([node, str(HARNESS)], input=json.dumps({"embedded": emb}), capture_output=True, text=True,
                         encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.fixture(scope="module")
def sample():
    rows, meta, _sha = sample_rows.load(sample_rows.sample_path("AOI_capacity_2026-09-18_30일치.html"))
    return rows, meta


def test_split_parts_fit_the_limit_cover_every_day_once_and_match_the_unsplit_model(tmp_path, sample):
    rows, meta = sample
    whole_dir, split_dir = tmp_path / "whole", tmp_path / "split"
    collect.write_html(_cfg(whole_dir, 0), rows, meta["devices"], [], 0.0)
    whole = whole_dir / "AOI_capacity.html"
    assert whole.stat().st_size > 7 * collect.MB                     # 이 샘플(약 10MB)이면 7MB 한도에서 나뉜다
    main = collect.write_html(_cfg(split_dir, 7), rows, meta["devices"], [], 0.0)
    assert Path(main).name == "AOI_capacity.html"
    files = sorted(split_dir.glob("*.html"))
    assert len(files) >= 2
    rx = paths.part_re("AOI_capacity.html")
    for f in files:
        assert f.stat().st_size <= 7 * collect.MB, f.name
        assert f.name == "AOI_capacity.html" or rx.match(f.name)
    parts = [_embedded(f)["meta"]["part"] for f in files]
    assert sorted(p["index"] for p in parts) == list(range(1, len(files) + 1))
    assert all(p["count"] == len(files) for p in parts)
    ranges = sorted((p["from"], p["to"]) for p in parts)
    for (a0, b0), (a1, _b1) in zip(ranges, ranges[1:]):
        assert b0 < a1                                                  # 겹치지 않는다
    full = _model(_embedded(whole))
    seen = []
    for f in files:
        m = _model(_embedded(f))
        p = _embedded(f)["meta"]["part"]
        assert all(p["from"] <= d <= p["to"] for d in m["days"])       # 자기 구간만 그린다
        seen += m["days"]
        for d in m["days"]:
            for dv, t in m["detail"][d].items():
                ref = full["detail"][d][dv]
                assert [t[k] for k in ("r", "d", "t", "x", "s", "e", "w", "den")] == \
                       [ref[k] for k in ("r", "d", "t", "x", "s", "e", "w", "den")], (f.name, d, dv)
    assert sorted(seen) == full["days"]                                 # 모든 날이 정확히 한 파일에


def test_no_split_below_the_limit_and_stale_parts_are_cleaned_but_nothing_else(tmp_path, sample):
    rows, meta = sample
    out = tmp_path / "o"
    collect.write_html(_cfg(out, 5), rows, meta["devices"], [], 0.0)
    assert len(list(out.glob("AOI_capacity_*~*.html"))) >= 1
    (out / "AOI_capacity_메모.html").write_text("사용자 파일", encoding="utf-8")
    (out / "AOI_capacity_2026-01-01~2026-01-02.txt").write_text("모양이 다른 파일", encoding="utf-8")
    collect.write_html(_cfg(out, 0), rows, meta["devices"], [], 0.0)       # 이번엔 나누지 않는다
    assert list(out.glob("AOI_capacity_*~*.html")) == []
    assert (out / "AOI_capacity_메모.html").is_file() and (out / "AOI_capacity_2026-01-01~2026-01-02.txt").is_file()
    assert "part" not in _embedded(out / "AOI_capacity.html")["meta"]


def test_split_rows_by_day_keeps_a_report_together_and_puts_undated_rows_in_the_newest_part():
    rows = [{"batch_start": f"9/{d}/2026 11:00:00 PM", "wafer_start_time": f"9/{d + 1}/2026 12:30:00 AM", "report": f"r{d}"}
            for d in range(1, 11) for _ in range(40)] + [{"report": "x"}]
    parts = collect.split_rows_by_day(rows, budget=3000)
    assert len(parts) >= 3
    assert parts[0][2][-1] == {"report": "x"}
    for a, b, part in parts:
        mine = [r for r in part if r.get("batch_start")]
        days = {collect.parse_dt(r["batch_start"]).date().isoformat() for r in mine}
        assert {a, b} <= days                                       # 배치 시작일로 나눈다(Wafer 시각이 다음 날이어도)


def test_header_chip_names_this_part_and_lists_the_others():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node 없음")
    files = [{"name": "AOI_capacity.html", "from": "2026-09-10", "to": "2026-09-18"},
             {"name": "AOI_capacity_2026-08-01~2026-09-09.html", "from": "2026-08-01", "to": "2026-09-09"}]
    meta = {"generated_iso": "2026-09-18T12:00:00", "devices": [],
            "part": {"index": 2, "count": 2, "from": "2026-08-01", "to": "2026-09-09", "files": files}}
    out = subprocess.run([node, str(HARNESS)], input=json.dumps({"screen": {"rows": [], "meta": meta, "calls": [["partChip"]]}}),
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr
    chip = json.loads(out.stdout)[0]
    assert "분할 2/2" in chip and "08/01~09/09" in chip and "AOI_capacity.html (09/10~09/18)" in chip
    assert "href" not in chip                                         # 링크가 아니라 글자 — 바깥 요청 0건 규칙
    single = subprocess.run([node, str(HARNESS)], input=json.dumps({"screen": {"rows": [], "meta": {"devices": []}, "calls": [["partChip"]]}}),
                            capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert json.loads(single.stdout) == [""]
