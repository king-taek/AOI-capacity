"""결과 HTML 기간(10/5) — 9/23 의 크기별 분할은 사용자 요청으로 롤백하고, **기간을 골라** 한 장으로 만든다.

- 수집 뒤 기본 HTML 은 가진 데이터의 끝날부터 `html_days` 일(0 = 전부), 원래 이름 한 장. 분할 파일은 생기지 않는다.
- 기간을 고르면 `AOI_capacity_<첫날>~<끝날>.html`. 기간 앞뒤 하루치 · 같은 Report · 같은 Wafer 의 앞선 시도를 맥락으로 더 넣으므로
  **기간 안 각 날의 장비-일 값이 전부 담은 파일과 같다**(자정 넘는 배치 · Rescan · 대기), 화면은 기간 밖 날을 그리지 않는다.
- `html_from_cache` 는 NAS 없이 캐시만으로 같은 HTML 을 만든다(기능이 늘 때 재수집하지 않게)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aoi_capacity import collect
import sample_rows

HARNESS = Path(__file__).with_name("js_harness.js")
KEYS = ("r", "d", "t", "x", "s", "e", "w", "den")


def _cfg(out: Path, html_days: int = 0) -> dict:
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(out), "cache_file": str(out / "c.json"), "html_days": html_days, "scope_devices": ["*"]})
    return cfg


def _embedded(path) -> dict:
    return sample_rows.embedded(Path(path).read_text(encoding="utf-8"))


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


def test_a_chosen_period_draws_only_its_days_and_matches_the_whole_file(tmp_path, sample):
    rows, meta = sample
    whole = collect.write_html(_cfg(tmp_path / "w"), rows, meta["devices"], [], 0.0)
    part = collect.write_html(_cfg(tmp_path / "p"), rows, meta["devices"], [], 0.0, day_from="2026-09-01", day_to="2026-09-10")
    assert Path(part).name == "AOI_capacity_2026-09-01~2026-09-10.html"
    assert sorted(p.name for p in (tmp_path / "p").glob("*.html")) == [Path(part).name]      # 한 장 — 분할 없음
    emb = _embedded(part)
    assert emb["meta"]["range"] == {"from": "2026-09-01", "to": "2026-09-10", "explicit": True}
    assert emb["meta"]["data_from"] < "2026-09-01"
    full, m = _model(_embedded(whole)), _model(emb)
    assert m["days"] == [d for d in full["days"] if "2026-09-01" <= d <= "2026-09-10"]
    for d in m["days"]:
        for dv, t in m["detail"][d].items():
            assert [t[k] for k in KEYS] == [full["detail"][d][dv][k] for k in KEYS], (d, dv)


def test_default_html_is_the_last_html_days_of_the_data_in_one_file(tmp_path, sample):
    rows, meta = sample
    out = tmp_path / "o"
    path = collect.write_html(_cfg(out, html_days=7), rows, meta["devices"], [], 0.0)
    assert Path(path).name == "AOI_capacity.html" and [p.name for p in out.glob("*.html")] == ["AOI_capacity.html"]
    r = _embedded(path)["meta"]["range"]
    last = _embedded(path)["meta"]["data_to"]
    assert r["to"] == last and r["explicit"] is False
    assert (collect.dt.date.fromisoformat(r["to"]) - collect.dt.date.fromisoformat(r["from"])).days == 6
    assert "split_mb" not in collect.DEFAULT_CONFIG and not hasattr(collect, "split_rows_by_day")


def test_rows_for_range_keeps_context_and_order():
    rows = [{"batch_start": f"9/{d}/2026 11:00:00 PM", "report": f"r{d}", "lot": "LOT1", "wafer_id": f"W{d % 3}"} for d in range(1, 11)]
    rows.append({"report": "x"})                                            # 날짜를 모르는 행
    got, a, b = collect.rows_for_range(rows, "2026-09-05", "2026-09-06")
    assert (a, b) == ("2026-09-05", "2026-09-06")
    days = [r["report"] for r in got]
    assert days == sorted(days, key=lambda x: [r["report"] for r in rows].index(x))   # 원래 순서
    assert {"r4", "r5", "r6", "r7"} <= set(days)                            # 앞뒤 하루 맥락
    assert {"r1", "r2", "r3"} <= set(days)                                   # 같은 Wafer(W0·W1·W2)의 앞선 시도
    assert "r8" not in days and "x" not in days                              # 끝을 정했으면 날짜 모르는 행은 넣지 않는다
    assert collect.rows_for_range(rows)[0] == rows


def test_html_from_cache_needs_no_nas_and_keeps_report_paths(tmp_path, sample, monkeypatch):
    rows, meta = sample
    cfg = _cfg(tmp_path / "c")
    cache = {"reports": {}, "last_mtime": {}, "failed": {}, "devices": {},
             "last_devices": [{"name": d["name"], "key": "dev:" + d["name"], "note": d.get("note", ""), "report_dir": "Report"}
                              for d in meta["devices"] if d.get("name")]}
    for k, r in enumerate(rows[:3000]):
        cache["reports"].setdefault(f"dev:{r['device']}|{r.get('report') or k}", {"rows": [], "device": r["device"]})["rows"].append(r)
    collect._save_cache(cfg, cache)
    monkeypatch.setattr(collect.os, "scandir", lambda *a, **k: (_ for _ in ()).throw(AssertionError("NAS 를 나열하면 안 된다")))
    first, last, n = collect.cached_days(cfg)
    assert first and last and n == 3000
    path = collect.html_from_cache(cfg, first, first)
    emb = _embedded(path)
    assert emb["meta"]["range"]["from"] == first and emb["meta"]["mode"] == "html_only"
    assert emb["meta"]["collect_log"]["kind"] == "html_only"
    notes = {d["name"]: d.get("note") for d in emb["meta"]["devices"]}
    assert any(notes.values())                                              # Report 열기 경로는 마지막 수집의 것


def test_header_chip_shows_the_period():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node 없음")
    meta = {"generated_iso": "2026-09-18T12:00:00", "devices": [], "data_from": "2026-06-01", "data_to": "2026-09-18",
            "range": {"from": "2026-08-01", "to": "2026-09-09", "explicit": True}}
    out = subprocess.run([node, str(HARNESS)], input=json.dumps({"screen": {"rows": [], "meta": meta, "calls": [["partChip"]]}}),
                         capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr
    chip = json.loads(out.stdout)[0]
    assert "08/01 ~ 09/09" in chip and "2026-06-01" in chip and "분할" not in chip and "href" not in chip
