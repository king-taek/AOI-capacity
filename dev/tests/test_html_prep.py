"""수집 끝 HTML 여러 장의 같은 준비를 한 번만(PH-01 · PH-03 · PP-07 · PH-02) — **결과 바이트는 그대로**여야 한다.

수집이 끝나면 같은 행으로 HTML 이 세 장(수집 HTML · LOT 배포 · 전체 배포) 만들어진다. `collect.HtmlPrep` 이 템플릿 · 행마다 날짜 ·
같은 행 묶음의 접기 JSON · 파라미터 Job 묶음을 한 번만 만든다. 여기서 지키는 것:

1. 기간 자르기(`rows_for_range`)는 예전 구현(아래 `_old_rows_for_range` — 바꾸기 전 코드 그대로)과 같은 행 객체를 같은 순서로 고른다.
2. 접기(`_embed_rows`, LOT 배포판의 빈 열 포함)와 JSON 이어 붙이기는 예전 방식(행 사본 → 접기 → `json.dumps`)과 글자까지 같다.
3. 세 장(+기간 · 전부)을 준비 없이 만든 것과 준비를 나눠 쓴 것이 바이트까지 같다(생성 시각 · 걸린 시간만 다름).
4. 파라미터 Job 묶음 기억(`job_memo`)은 30일 · 90일 묶음을 기억 없이 만든 것과 같게 한다.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest

from aoi_capacity import collect, params
from test_params import RECIPE, _snap

NORM = re.compile(rb'"(generated|generated_iso|elapsed|html_ms)":("[^"]*"|\d+)')


# ── 예전 구현(바꾸기 전 코드 그대로 — 기준) ─────────────────────────────────
def _old_wafer_key(r):
    if r.get("kind") or collect._is_placeholder(r):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(r.get("wafer_id") or "").upper())


def _old_rows_for_range(rows, day_from="", day_to=""):
    memo = {}
    days = sorted({d for d in (collect._row_day(r, memo) for r in rows) if d})
    if not days:
        return list(rows), "", ""
    lo = max(day_from or days[0], days[0])
    hi = min(day_to or days[-1], days[-1])
    if not day_from and not day_to:
        return list(rows), days[0], days[-1]
    if lo > hi:
        return [], lo, hi
    d0 = (dt.date.fromisoformat(lo) - dt.timedelta(days=1)).isoformat()
    d1 = (dt.date.fromisoformat(hi) + dt.timedelta(days=1)).isoformat()
    pick = [r for r in rows if d0 <= collect._row_day(r, memo) <= d1 or (not collect._row_day(r, memo) and not day_to)]
    have = {id(r) for r in pick}
    reps = {(r.get("device"), r.get("report")) for r in pick}
    keys = {k for k in (_old_wafer_key(r) for r in pick) if k}
    for r in rows:
        if id(r) in have:
            continue
        d = collect._row_day(r, memo)
        if (r.get("device"), r.get("report")) in reps or (d and d < d0 and _old_wafer_key(r) in keys):
            pick.append(r)
            have.add(id(r))
    order = {id(r): k for k, r in enumerate(rows)}
    pick.sort(key=lambda r: order[id(r)])
    return pick, lo, hi


def _old_embed(rows):
    pool, index = [], {}

    def put(v):
        v = "" if v is None else str(v)
        i = index.get(v)
        if i is None:
            i = index[v] = len(pool)
            pool.append(v)
        return i

    pooled = [c in collect.POOLED_COLS for c in collect.OUT_COLS]
    out = [[put(r.get(c, "")) if pooled[i] else str(r.get(c, "") or "") for i, c in enumerate(collect.OUT_COLS)] for r in rows]
    return {"cols": list(collect.OUT_COLS), "pooled": [c for c in collect.OUT_COLS if c in collect.POOLED_COLS], "pool": pool, "rows": out}


# ── 자료: 여러 날 · 자정 넘는 배치 · 같은 Wafer 의 앞선 시도 · 날짜 없는 행 · 합성 행 · 자리표시 ───────────
def _rows():
    rows = []
    for day in range(1, 21):
        for dev in ("AOI-1", "AOI-2", "4F-AOI-01"):
            for k in range(3):
                bs = f"9/{day}/2026 {(k * 9 + 1) % 12 or 12}:15:00 {'PM' if k == 2 else 'AM'}"
                rep = f"J_6321_L{day % 7}{k}_26-Sep-{day:02d}_(10.00.00)_BatchReport.htm"
                for w in range(4):
                    rows.append({"device": dev, "job": f"JOB{k}", "lot": f"L{day % 7}{k}", "wafer_id": f"WID{(day + w) % 9:03d}-{k}",
                                 "status": "Pass" if w else "Error: Wafer lost", "report": rep, "batch_start": bs,
                                 "wafer_start_time": bs, "faults": str(w * 7), "recipe": "x20|x5" if k else "x20", "slot_no": str(w + 1),
                                 "ini_match": "EXACT", "kind": ""})
            rows.append({"device": dev, "kind": "batch", "report": f"F_{day}.htm", "batch_start": f"9/{day}/2026 11:59:00 PM",
                         "status": "Aborted", "lot": "LoadPort A", "wafer_id": ""})
    rows.append({"device": "AOI-1", "report": "nodate.htm", "lot": "X", "wafer_id": "WID001-0", "status": "Pass"})       # 날짜 없음
    rows.append({"device": "AOI-2", "report": "J_6321_L50_26-Sep-05_(10.00.00)_BatchReport.htm", "lot": "Slot 3", "wafer_id": "Slot 3"})
    rows.append({"device": "AOI-2", "report": "x</script>.htm", "lot": "Y", "wafer_id": "W</x", "status": "Pass",
                 "batch_start": "9/9/2026 01:00:00 AM"})                                                                   # `</` 바꾸기
    return rows


@pytest.mark.parametrize("a,b", [("", ""), ("2026-09-05", "2026-09-07"), ("2026-09-15", ""), ("", "2026-09-03"),
                                 ("2026-08-01", "2026-12-31"), ("2026-08-01", ""), ("2026-10-01", "2026-10-05"),
                                 ("2026-09-20", "2026-09-20"), ("2026-09-01", "2026-09-20")])
def test_range_picks_the_same_row_objects_in_the_same_order_as_before(a, b):
    rows = _rows()
    old = _old_rows_for_range(rows, a, b)
    new = collect.rows_for_range(rows, a, b)
    assert [id(r) for r in new[0]] == [id(r) for r in old[0]] and new[1:] == old[1:]
    assert collect.rows_for_range(rows, a, b, days=collect._row_days(rows))[0] == new[0]


def test_embed_and_payload_match_the_old_copy_then_fold_then_dump():
    rows = _rows()
    assert collect._embed_rows(rows) == _old_embed(rows)
    blank = collect.LOT_ONLY_BLANK_COLS
    copies = [{**r, **{c: "" for c in blank}} for r in rows]
    assert collect._embed_rows(rows, blank) == _old_embed(copies)
    meta = {"generated": "x</y", "n": 1, "k": [1, "가"]}
    emb = _old_embed(rows)
    old = json.dumps(dict(emb, meta=meta), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    assert collect._payload(_old_embed(rows), meta) == old == collect._payload_join(collect._emb_json(emb), meta)


def _cfg(out: Path, **over) -> dict:
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(out), "cache_file": str(out / "c.json"), "scope_devices": ["*"], "write_csv": True})
    cfg.update(over)
    return cfg


def _store():
    st = params.empty_store()
    for i, (dev, job, day) in enumerate((("AOI-1", "J1", 2), ("AOI-2", "J1", 18), ("AOI-1", "J2", 3), ("AOI-2", "J3", 19), ("AOI-1", "J1", 19))):
        params.put(st, f"dev:{dev}|r{i}.htm", dev=dev, job=job, setup="", t=f"2026-09-{day:02d} 08:00", report=f"r{i}.htm",
                   files=_snap(**{"Recipe.ini": RECIPE.replace("Threshold[um]=5", f"Threshold[um]={i}")}))
    return st


def test_three_collection_end_html_are_byte_identical_with_or_without_shared_prep(tmp_path, monkeypatch):
    """수집 HTML(최근 7일 + CSV) · LOT 배포 · 전체 배포(30일 — 데이터 전부) · 기간 · 전부 — 준비를 나눠 쓴 것 = 하나씩 만든 것."""
    monkeypatch.setattr(collect, "_version_info", lambda: {"sha": "abc", "branch": "main"})
    rows = collect.render_issue_rows(_rows())
    dm = [{"name": n, "key": "dev:" + n, "note": ""} for n in ("AOI-1", "AOI-2", "4F-AOI-01")]
    st = _store()
    calls = [("gui", dict(html_days=7), dict(mode="gui", timing={"x": 1}, params_store=st)),
             ("lot", dict(), dict(mode="publish", lot_only=True, params_store={})),
             ("full", dict(html_days=30, write_csv=False), dict(mode="publish", params_store=st)),
             ("rng", dict(), dict(mode="html_only", day_from="2026-09-05", day_to="2026-09-08")),
             ("all", dict(html_days=0, write_csv=False), dict(mode="gui"))]

    def run(sub, prep):
        out = {}
        for tag, c, k in calls:
            p = collect.write_html(_cfg(tmp_path / sub, **c), rows, dm, [], 0.0, out_name=f"{tag}.html", prep=prep, **k)
            out[tag] = NORM.sub(b"", Path(p).read_bytes())
            csv = Path(p).with_suffix(".csv")
            if csv.exists():
                out[tag + ".csv"] = csv.read_bytes()
        return out

    alone = run("a", None)
    prep = collect.HtmlPrep(rows)
    shared = run("b", prep)
    assert alone.keys() == shared.keys() and "gui.csv" in alone
    for k in alone:
        assert alone[k] == shared[k], k
    assert len(prep.emb) < len(calls) and prep.params                         # 실제로 나눠 썼다(같은 행 묶음 · 파라미터 Job)
    assert b'"params"' in alone["gui"] and b'"lot_only":true' in alone["lot"]
    other = collect.HtmlPrep(list(rows))                                       # 다른 리스트의 준비는 쓰지 않는다
    p = collect.write_html(_cfg(tmp_path / "c", **calls[0][1]), rows, dm, [], 0.0, out_name="gui.html", prep=other, **calls[0][2])
    assert NORM.sub(b"", Path(p).read_bytes()) == alone["gui"] and not other.emb


def test_params_job_memo_gives_the_same_bundle_for_30_and_90_day_windows():
    st = _store()
    plain = [collect.params_for_range(st, f, "2026-09-19") for f in ("2026-09-15", "2026-09-01", "")]
    memo: dict = {}
    shared = [collect.params_for_range(st, f, "2026-09-19", memo=memo) for f in ("2026-09-15", "2026-09-01", "")]
    assert plain == shared and memo
    assert len(plain[0]["jobs"]) < len(plain[1]["jobs"])                     # 짧은 기간은 그 안에 돈 Job 만
    assert collect.params_for_range(st, "", "2026-09-02", memo=memo) == collect.params_for_range(st, "", "2026-09-02")   # 끝날이 다르면 다시
