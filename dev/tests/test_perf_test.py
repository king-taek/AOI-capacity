"""수집 창 '속도 시험'(11/25 — PH-01 · PH-03 · LOTD-01). `aoi_capacity.perf_test.run` 이 지키는 것:

1. 캐시만 읽는다(장비 NAS 나열 · 읽기 0) — 결과 HTML 세 장을 (가) 장마다 따로 (나) 준비를 나눠 만든 것이 바이트까지 같다(생성 시각 칸만 빼고).
2. 쓰기는 `<시험 폴더>\\<시각>\\` 아래뿐이고 남는 것은 요약 · 결과 · LOT 시험 파일 두 장(비교용 HTML · CSV 는 지운다). 저장 위치가 NAS 아래면 거부.
3. LOT 시험 파일 두 장은 `meta.selftest`, 둘째만 `meta.lot_skip_model` — 제품 파일(표식 없이 만든 것)에는 둘 다 없다.
4. 이 모듈의 쓰기 호출은 첫 줄에서 `assert_local` 을 부르는 함수 안에만(규칙 1 — publish.py 와 같은 정적 검사).
5. 단추 하나(11/26): `browser` 를 주면 두 장을 차례로 열고, 시험 파일이 내려받은 `aoi_perf_<토큰>_<이름>.json` 을 다운로드 폴더에서
   기다렸다(상한 · 멈춤) 시험 폴더로 옮겨 요약에 'LOT 배포판 열기 — 지금 n.n초 · 계산 건너뜀 m.m초' 를 적는다. 못 받으면 '노란 띠' 안내.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

import pytest

import sample_rows
from aoi_capacity import collect, perf_test
from aoi_capacity.nas_guard import NasWriteRefused
from test_nas_guard import _call_name, _enclosing_function


@pytest.fixture(scope="module")
def sample():
    rows, meta, _sha = sample_rows.load(sample_rows.sample_path("AOI_capacity_2026-09-18_30일치.html"))
    return rows, meta


def _cfg(tmp_path: Path) -> dict:
    cfg = dict(collect.DEFAULT_CONFIG)
    out = tmp_path / "out"
    cfg.update({"output_dir": str(out), "cache_file": str(out / "c.json"), "html_days": 7, "publish_full_days": 14,
                "scope_devices": ["*"], "write_csv": True, "devices_csv": str(tmp_path / "devices.csv")})
    return cfg


def _make_cache(cfg: dict, rows, meta, n: int = 4000) -> None:
    cache = {"reports": {}, "last_mtime": {}, "failed": {}, "devices": {},
             "last_devices": [{"name": d["name"], "key": "dev:" + d["name"], "note": d.get("note", ""), "report_dir": "Report"}
                              for d in meta["devices"] if d.get("name")]}
    for k, r in enumerate(rows[:n]):
        cache["reports"].setdefault(f"dev:{r['device']}|{r.get('report') or k}", {"rows": [], "device": r["device"]})["rows"].append(r)
    collect._save_cache(cfg, cache)


def _files(root: Path) -> dict:
    return {str(p.relative_to(root)): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def _meta_of(path: Path) -> dict:
    return sample_rows.embedded(path.read_text(encoding="utf-8"))["meta"]


def test_run_builds_three_identical_pairs_from_the_cache_only(tmp_path, sample, monkeypatch):
    rows, meta = sample
    cfg = _cfg(tmp_path)
    _make_cache(cfg, rows, meta)
    before = _files(tmp_path)
    real_scandir = os.scandir
    nas = tuple(str(d.get("note") or "").rstrip("\\/") for d in meta["devices"] if d.get("note"))
    assert nas                                                                    # 표본에 장비 경로가 있어야 이 검사가 뜻이 있다

    def guard(path=".", *a, **k):                                                 # 장비 NAS 아래 나열만 막는다 — 로컬(레시피 묶음 찾기 등)은 그대로
        p = os.fspath(path)
        if any(p.startswith(r) for r in nas):
            raise AssertionError(f"NAS 를 나열하면 안 된다: {p}")
        return real_scandir(path, *a, **k)

    monkeypatch.setattr(collect.os, "scandir", guard)
    phases = []
    got = perf_test.run(cfg, str(tmp_path / "perf"), progress=lambda d, t, p: phases.append(p))
    assert got["same"] == {"base": True, "lot": True, "full": True} and not got["stopped"]
    out = Path(got["dir"])
    assert out.parent == tmp_path / "perf"
    assert sorted(os.listdir(out)) == sorted([perf_test.SUMMARY_NAME, perf_test.RESULT_NAME, perf_test.LOT_NOW_NAME, perf_test.LOT_SKIP_NAME])
    after = _files(tmp_path)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert all(k.startswith("perf" + os.sep) for k in changed), changed           # 시험 폴더 밖은 하나도 바뀌지 않았다(캐시 포함)
    res = json.loads((out / perf_test.RESULT_NAME).read_text(encoding="utf-8"))
    assert [x["kind"] for x in res["a"]] == [x["kind"] for x in res["b"]] == ["base", "lot", "full"]
    for x in res["a"] + res["b"]:
        assert set(x["stages"]) == set(perf_test.STAGES) and x["total"] >= x["stages"]["write"] >= 0
    assert res["a"][0]["csv"] and res["a"][0]["stages"]["csv"] > 0                 # 기본 HTML 은 수집처럼 CSV 도
    now, skip = _meta_of(out / perf_test.LOT_NOW_NAME), _meta_of(out / perf_test.LOT_SKIP_NAME)
    assert now["lot_only"] and now["selftest"] and "lot_skip_model" not in now
    assert skip["lot_only"] and skip["selftest"] and skip["lot_skip_model"] is True
    text = (out / perf_test.SUMMARY_NAME).read_text(encoding="utf-8-sig")
    assert "세 장 모두 같습니다" in text and perf_test.LOT_NOW_NAME in text and perf_test.LOT_SKIP_NAME in text
    assert phases and phases[-1]


def test_product_files_carry_no_test_flags(tmp_path, sample):
    """제품 경로(수집 HTML · 배포판)는 stages · meta_extra 를 주지 않는다 — 시험 표식이 들어가지 않는다."""
    rows, meta = sample
    cfg = _cfg(tmp_path)
    p1 = collect.write_html(cfg, rows[:800], meta["devices"], [], 0.0, lot_only=True, out_dir=str(tmp_path / "o"), out_name="lot.html")
    m = _meta_of(Path(p1))
    assert m["lot_only"] and "selftest" not in m and "lot_skip_model" not in m and "selftest_token" not in m


def test_stop_keeps_what_was_measured(tmp_path, sample):
    rows, meta = sample
    cfg = _cfg(tmp_path)
    _make_cache(cfg, rows, meta, n=1500)
    calls = {"n": 0}

    def stop():
        calls["n"] += 1
        return calls["n"] > 2                                   # (가) 두 장 뒤 멈춤
    got = perf_test.run(cfg, str(tmp_path / "perf"), should_stop=stop)
    assert got["stopped"]
    res = json.loads(Path(got["result"]).read_text(encoding="utf-8"))
    assert len(res["a"]) == 2 and not res["b"] and "멈췄습니다" in Path(got["summary"]).read_text(encoding="utf-8-sig")
    assert not [n for n in os.listdir(got["dir"]) if n.endswith((".html", ".csv"))]


def test_refuses_an_output_folder_under_the_nas(tmp_path, fake_nas, sample):
    nas, csv_path = fake_nas
    rows, meta = sample
    cfg = _cfg(tmp_path)
    cfg["devices_csv"] = str(csv_path)
    _make_cache(cfg, rows, meta, n=200)
    with pytest.raises(NasWriteRefused):
        perf_test.run(cfg, str(nas / "X" / "AOI-9" / "perf"))
    assert not (nas / "X" / "AOI-9" / "perf").exists()


def test_perf_module_writes_only_in_guarded_functions():
    tree = ast.parse(Path(perf_test.__file__).read_text(encoding="utf-8"))
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    allowed = set()
    for name, fn in fns.items():
        body = fn.body[1:] if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(fn.body[0].value, ast.Constant) else fn.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Call) and _call_name(body[0].value) == "nas_guard.assert_local":
            allowed.add(name)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        writes = name in {"os.replace", "os.rename", "os.remove", "os.unlink", "os.makedirs", "os.mkdir", "os.utime", "os.chmod",
                          "os.rmdir"} or name.startswith("shutil.")
        if name == "open":
            mode = str(node.args[1].value) if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else ""
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = str(kw.value.value)
            writes = any(ch in mode for ch in "wax+")
        if writes and _enclosing_function(tree, node) not in allowed:
            offenders.append(f"{name} in {_enclosing_function(tree, node)} (line {node.lineno})")
    assert not offenders and {"_make_dir", "_write_text", "_remove", "_move"} <= allowed, offenders


def test_template_self_test_and_skip_model_only_run_with_their_flags():
    """제품 화면 동작 불변: 자가 점검은 meta.selftest 가 없으면 바로 돌아가고, 모델 건너뛰기는 lot_only 와 lot_skip_model 이 둘 다일 때만."""
    t = (Path(collect.__file__).parent / "ui" / "assets" / "template.html").read_text(encoding="utf-8")
    assert "function selfTest(){if(!meta.selftest||" in t and "if(meta.selftest)selfTest();" in t
    assert "D=(meta.lot_only&&meta.lot_skip_model)?liteModel(meta):buildModel(rows,meta);" in t
    assert "if(!D.lite){rgLoad();" in t
    st = t[t.index("function selfTest(){"):t.index("/* ---------- ③ 모델")]
    assert 'if(meta.selftest_token)try{' in st and '"aoi_perf_"+tk+"_"+nm+".json"' in st and "new Blob(" in st   # 11/26: 결과는 blob 다운로드 한 장
    for bad in ("fetch(", "XMLHttpRequest", "sendBeacon", "http://", "https://", "localhost"):
        assert bad not in st, bad


# ── 단추 하나로 끝까지(11/26): 브라우저로 열고 다운로드 폴더에서 결과 받기 ─────────────────────────────
def _result(token: str, name: str, open_ms: int = 1234) -> dict:
    """template `selfTest` 가 내려받는 모양 그대로."""
    return {"v": 1, "token": token, "name": name, "open": open_ms, "lifted": 4100, "lite": name == "skip", "rows": 10,
            "stages": {"parse": 100, "unfold": 20, "model": 0 if name == "skip" else 900, "first": 50},
            "steps": [{"name": "LOT 목록", "ok": True, "ms": 3, "note": "3개"}], "errors": [], "ua": "Chromium"}


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_wait_download_finds_the_tokened_file_and_skips_others(tmp_path):
    dl = tmp_path / "dl"
    dl.mkdir()
    (dl / "aoi_perf_abc_now.json").write_text(json.dumps(_result("zzz", "now")), encoding="utf-8")       # 이름만 같고 토큰이 다른 내용
    (dl / "aoi_perf_tok_now.json.crdownload").write_text("{", encoding="utf-8")                          # 받는 중
    clock = _Clock()
    calls = {"n": 0}

    def sleep(s):
        clock.sleep(s)
        calls["n"] += 1
        if calls["n"] == 3:                                    # 몇 차례 뒤 브라우저가 반쯤 쓴 파일 → 다음 차례에 다 씀(' (1)' 붙은 이름)
            (dl / "aoi_perf_tok_now (1).json").write_text('{"token": "tok"', encoding="utf-8")
        if calls["n"] == 4:
            (dl / "aoi_perf_tok_now (1).json").write_text(json.dumps(_result("tok", "now")), encoding="utf-8")
    got = perf_test.wait_download("tok", "now", [str(tmp_path / "없음"), str(dl)], timeout=60, poll=0.5, clock=clock, sleep=sleep)
    assert got is not None and got[0] == str(dl / "aoi_perf_tok_now (1).json") and got[1]["open"] == 1234
    assert calls["n"] == 4


def test_wait_download_times_out_and_stops(tmp_path):
    clock = _Clock()
    assert perf_test.wait_download("tok", "now", [str(tmp_path)], timeout=3, poll=0.5, clock=clock, sleep=clock.sleep) is None
    assert 3 <= clock.t <= 3.5                                  # 상한까지만 기다린다
    n = {"k": 0}

    def stop():
        n["k"] += 1
        return n["k"] > 2
    with pytest.raises(perf_test.Stopped):
        perf_test.wait_download("tok", "now", [str(tmp_path)], timeout=60, poll=0.5, clock=clock, sleep=clock.sleep, should_stop=stop)


def test_one_button_opens_both_files_in_turn_and_collects_the_results(tmp_path, sample):
    rows, meta = sample
    cfg = _cfg(tmp_path)
    _make_cache(cfg, rows, meta, n=1500)
    dl = tmp_path / "Downloads"
    dl.mkdir()
    opened = []

    def browser(path):                                          # 기본 브라우저 대역: 표식을 읽고 결과 한 장을 '내려받는다'
        m = _meta_of(Path(path))
        assert m["selftest"] and m["selftest_token"] and m["selftest_name"] in ("now", "skip")
        assert not list(dl.iterdir()), "앞 파일의 결과를 가져간 뒤에 다음 파일을 연다(차례로)"
        opened.append((Path(path).name, m["selftest_name"], bool(m.get("lot_skip_model"))))
        ms = 2500 if m["selftest_name"] == "now" else 900
        (dl / f"aoi_perf_{m['selftest_token']}_{m['selftest_name']}.json").write_text(json.dumps(_result(m["selftest_token"], m["selftest_name"], ms)),
                                                                                      encoding="utf-8")
    got = perf_test.run(cfg, str(tmp_path / "perf"), browser=browser, download_dirs=[str(dl)], lot_wait_sec=5)
    assert opened == [(perf_test.LOT_NOW_NAME, "now", False), (perf_test.LOT_SKIP_NAME, "skip", True)]
    assert got["lot_open"] == {"now": 2.5, "skip": 0.9} and got["lot_missing"] == []
    out = Path(got["dir"])
    assert not list(dl.iterdir())                               # 다운로드 폴더에서 옮겼다
    moved = sorted(n for n in os.listdir(out) if n.startswith("aoi_perf_"))
    assert len(moved) == 2 and all(n.endswith(("_now.json", "_skip.json")) for n in moved)
    text = (out / perf_test.SUMMARY_NAME).read_text(encoding="utf-8-sig")
    assert "LOT 배포판 열기 — 지금 2.5초 · 계산 건너뜀 0.9초" in text and "요약.txt) 하나만 보내 주세요" in text and "노란 띠" not in text
    res = json.loads((out / perf_test.RESULT_NAME).read_text(encoding="utf-8"))
    assert [r["got"] for r in res["lot_open"]] == [True, True] and res["lot_open"][1]["lite"] is True


def test_one_button_without_a_download_asks_for_the_band_numbers(tmp_path, sample):
    rows, meta = sample
    cfg = _cfg(tmp_path)
    _make_cache(cfg, rows, meta, n=600)
    opened = []
    got = perf_test.run(cfg, str(tmp_path / "perf"), browser=opened.append, download_dirs=[str(tmp_path / "dl")], lot_wait_sec=0.6)
    assert len(opened) == 2 and got["lot_open"] == {} and got["lot_missing"] == [perf_test.LOT_NOW_NAME, perf_test.LOT_SKIP_NAME]
    text = Path(got["summary"]).read_text(encoding="utf-8-sig")
    assert "지금 못 받음 · 계산 건너뜀 못 받음" in text and "브라우저 맨 위 노란 띠 숫자를 보내 주세요" in text


def test_one_button_stop_while_waiting(tmp_path, sample):
    rows, meta = sample
    cfg = _cfg(tmp_path)
    _make_cache(cfg, rows, meta, n=600)
    flag = {"on": False}
    got = perf_test.run(cfg, str(tmp_path / "perf"), browser=lambda p: flag.update(on=True), download_dirs=[str(tmp_path)],
                        lot_wait_sec=60, should_stop=lambda: flag["on"])
    assert got["stopped"] and "멈췄습니다" in Path(got["summary"]).read_text(encoding="utf-8-sig")
