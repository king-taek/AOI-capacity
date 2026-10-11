"""레시피 파라미터(D89, 10/11) — 읽기 · 정규화(측정값 제외) · 보관(내용 해시로 한 번) · HTML 묶음 · 30일 zip 가져오기 · 수집 연결."""
from __future__ import annotations

import io
import json
import zipfile

from aoi_capacity import collect, params
from conftest import make_cfg
from test_recipes_info import _rows, _wafer_dir

RECIPE = "[AutoCycle]\nAutoFocusEvery=3 ; Wafer\nCleanReferenceEvery=2 ; Lot\n[General]\nLastCam=10\nThreshold[um]=5\n"
ALIGN = "[System Params]\nRotate_Wafer=-0.0023\nAngleTolerance=0.5\n"
MULTI = "[Scan]\nrecipe_1=-1,PI_Bubble,-1,0\nrecipe_2=-1,PI,-1,0\n"


def _snap(**over):
    raw = {"Recipe.ini": RECIPE.encode(), "AlignRtp.ini": ALIGN.encode(), "MultiRecipe.ini": MULTI.encode(),
           "Zones/RDL.ini": b"[General]\nZoneName=RDL\n[Surface]\nMinSize=3\n"}
    raw.update({k: v.encode() for k, v in over.items()})
    return params.snapshot(raw)


def test_measurements_and_camera_position_are_not_kept():
    s = _snap()
    assert "Rotate_Wafer" not in s["AlignRtp.ini"] and "AngleTolerance" in s["AlignRtp.ini"]
    assert "LastCam" not in s["Recipe.ini"]
    # 측정값만 다른 두 Lot 은 같은 스냅숏(보관이 늘지 않는다)
    assert _snap(**{"AlignRtp.ini": ALIGN.replace("-0.0023", "-0.0014")}) == s


def test_store_keeps_each_text_once_and_reports_changes():
    st = params.empty_store()
    assert params._ounion([["a", "b", "d"], ["b", "c", "d"], ["z", "a"], [None]]) == [None, "z", "a", "b", "c", "d"]
    assert params.put(st, "dev:AOI-1|a.htm", dev="AOI-1", job="J", setup="6321", t="2026-10-01 08:00", report="a.htm", files=_snap())
    assert not params.put(st, "dev:AOI-1|a.htm", dev="AOI-1", job="J", setup="6321", t="2026-10-01 08:00", report="a.htm", files=_snap())
    params.put(st, "dev:AOI-2|b.htm", dev="AOI-2", job="J", setup="6321", t="2026-10-01 09:00", report="b.htm", files=_snap())
    assert len(st["blobs"]) == 4 and st["snaps"]["dev:AOI-1|a.htm"]["rn"] == ["PI_Bubble", "PI"]


def _meta(store):
    """Job 이 하나인 묶음을 펴서 (그 Job, pool) — HTML 에는 Job 마다 gzip 으로 접혀 있다."""
    m = params.build_meta(store)
    [J] = m["jobs"]
    body = params.unpack(J)
    assert J["n"] == len(body["d"]) and J["t"]
    return dict(body, j=J["j"]), body["pool"]


def test_build_meta_majority_diff_every_label_zone_names_and_history():
    st = params.empty_store()
    for dev, thr, t in (("AOI-1", "5", "10-01"), ("AOI-2", "5", "10-01"), ("AOI-3", "7", "10-01")):
        params.put(st, f"dev:{dev}|x.htm", dev=dev, job="J", setup="", t=f"2026-{t} 08:00", report="x.htm",
                   files=_snap(**{"Recipe.ini": RECIPE.replace("Threshold[um]=5", f"Threshold[um]={thr}")}))
    params.put(st, "dev:AOI-3|y.htm", dev="AOI-3", job="J", setup="", t="2026-10-02 08:00", report="y.htm",
               files=_snap(**{"Recipe.ini": RECIPE.replace("Threshold[um]=5", "Threshold[um]=5")}))
    J, P = _meta(st)
    assert J["d"] == ["AOI-1", "AOI-2", "AOI-3"]
    groups = {P[g[0]]: g for g in J["g"]}
    assert "Zones — PI_Bubble" in groups and groups["Focus · Alignment"][1] == 1 and groups["Recipe 동작"][1] == 0
    items = {P[it[0]]: it for z in groups["Recipe 동작"][2] for it in z[2]}
    assert P[items["AutoFocusEvery"][3]] == "Wafer" and P[items["CleanReferenceEvery"][3]] == "Lot"     # 숫자 대신 글자(Q10)
    thr = items["Threshold"]
    assert P[thr[1]] == "um" and P[thr[3]] == "5" and thr[4] == {}            # 최신(AOI-3 은 y.htm 에서 5 로 돌아옴)
    [ev] = J["h"]
    assert ev[1] == 2 and [[P[c[1]], P[c[2]]] for c in ev[3]] == [["7", "5"]]


def test_device_groups_keep_only_differing_rows():
    st = params.empty_store()
    for dev, gain in (("AOI-1", "1"), ("AOI-2", "2")):
        params.put(st, f"dev:{dev}|x.htm", dev=dev, job="J", setup="", t="2026-10-01 08:00", report="x.htm",
                   files=params.snapshot({"OpticPreset.ini": f"[Scan1]\nGain={gain}\nMode=A\n".encode()}))
    J, P = _meta(st)
    [g] = J["g"]
    assert P[g[0]] == "광학" and [P[it[0]] for z in g[2] for it in z[2]] == ["Gain"]


def _zip(tmp_path):
    lot = "0001_AOI-9_KLK-3D"
    from conftest import REPORT_HTML
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(f"{lot}/report/2D@R2-GA285AAB_0859840PD-0A_6321_KLK-3D_26-Sep-13_(07.00.00)_BatchReport.htm", REPORT_HTML)
        z.writestr(f"{lot}/W1/Recipe.ini", RECIPE)
        z.writestr(f"{lot}/_목록.tsv", "wafer\t상대경로\t크기\t수정시각\tsha1\t저장\nW1\tRecipe.ini\t1\tt\tx\tpart01\nW1\tRTP.txt\t1\tt\tx\t= 0002_AOI-9_OTHER/W2/RTP.txt\n")
        z.writestr("0002_AOI-9_OTHER/W2/RTP.txt", "[Zone1]\nAlg=Surface\nMin_Defect=3 ; (min size)\n")
        z.writestr("0003_AOI-99_X/W3/Recipe.ini", RECIPE)                     # 범위 밖 장비
    (tmp_path / "zips").mkdir()
    (tmp_path / "zips" / "AOI_wafer_logs30_x_part01.zip").write_bytes(buf.getvalue())
    return tmp_path / "zips"


def test_import_zips_resolves_references_and_skips_out_of_scope(tmp_path, fake_nas):
    _nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    folder = _zip(tmp_path)
    st = collect.import_param_zips(cfg, str(folder))
    assert st["added"] == 1
    cache = json.loads(open(cfg["cache_file"], encoding="utf-8").read())
    [s] = cache["params"]["snaps"].values()
    assert s["dev"] == "AOI-9" and s["job"] and set(s["f"]) == {"Recipe.ini", "RTP.txt"}
    assert collect.import_param_zips(cfg, str(folder))["added"] == 0        # 두 번 넣지 않는다


def test_collector_reads_params_once_per_report_and_html_carries_them(tmp_path, fake_nas, monkeypatch):
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "Recipe.ini").write_text(RECIPE, encoding="utf-8")
    calls = []
    real = params.read_wafer_files
    monkeypatch.setattr(params, "read_wafer_files", lambda p: (calls.append(p), real(p))[1])
    cfg = make_cfg(tmp_path, csv_path)
    stats = {}
    rows, dev_meta, errors = collect.collect(cfg, stats=stats)
    assert calls and all("K625407-01B0" in p for p in calls)
    n = len(calls)
    collect.collect(dict(cfg, refresh_window_days=3650))                      # 다시 읽어도 스냅숏이 있는 Report 는 열지 않는다
    assert len(calls) == n
    path = collect.write_html(cfg, rows, dev_meta, errors, 0.0, timing=stats)
    assert '"params"' in open(path, encoding="utf-8").read()
    monkeypatch.setattr(params, "read_wafer_files", lambda p: (_ for _ in ()).throw(AssertionError("꺼져 있으면 읽지 않는다")))
    collect.collect(dict(make_cfg(tmp_path / "off", csv_path), collect_params=False))


def test_fill_params_reads_only_wafer_folders_of_reports_without_snapshots(tmp_path, fake_nas, monkeypatch):
    """파라미터 빈 구간 채우기(10/11): 스냅숏이 없는 Report 의 Wafer 폴더 안만 읽고, 두 번째 실행은 아무것도 읽지 않는다. 예상 시간 실측도 남는다."""
    from aoi_capacity import nas_guard
    nas, csv_path = fake_nas
    (_wafer_dir(nas) / "Recipe.ini").write_text(RECIPE, encoding="utf-8")
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(dict(cfg, collect_params=False))                         # 파라미터 없이 수집 — 빈 구간을 만든다
    plan = collect.plan_run(cfg)
    assert plan.params_missing >= 1 and plan.params_have == 0 and plan.span_from and plan.params_devices >= 1
    sec, rough = plan.etas["params"]
    assert rough and sec > 0                                                  # 실측이 없으면 대략
    listed, opened = [], []
    real_scan, real_bytes = nas_guard.scandir, nas_guard.read_bytes
    monkeypatch.setattr(nas_guard, "scandir", lambda p, *a, **k: listed.append(str(p)) or real_scan(p, *a, **k))
    monkeypatch.setattr(nas_guard, "read_bytes", lambda p, *a, **k: opened.append(str(p)) or real_bytes(p, *a, **k))
    st = collect.fill_params(cfg)
    assert st["targets"] == plan.params_missing and st["added"] >= 1 and not st["stopped"]
    assert not any(p.lower().endswith((".htm", ".html")) for p in opened)    # Report 는 다시 읽지 않는다
    deep = [p for p in listed if "scanresult" in p.lower() and p.lower().rstrip("/\\").split("scanresult")[-1].strip("/\\")]
    assert deep and all("K625407-01B0" in p for p in deep)                    # Scanresult 아래에서 연 폴더는 계산한 Wafer 폴더(와 그 하위)뿐 — 재귀 검색 없음
    after = collect.plan_run(cfg)
    assert after.params_missing == 0 and after.params_have >= 1
    opened.clear()
    assert collect.fill_params(cfg)["targets"] == 0 and not [p for p in opened if str(nas) in p]
    cache = json.loads(open(cfg["cache_file"], encoding="utf-8").read())
    assert cache["eta"]["params_fill"][0][0] == st["targets"]


def test_estimate_sec_uses_recent_measurements_else_rough_default():
    assert collect.estimate_sec({}, "refresh", 100) == (int(collect.ETA_DEFAULT_FIXED_SEC + 100 * collect.ETA_DEFAULT_PER_UNIT["read"]), True)
    eta = {}
    collect.record_eta({"eta": eta}, "x", 0, 5, 1)                           # 개수 0 은 남기지 않는다
    cache = {}
    for n, w in ((100, 50.0), (100, 40.0), (100, 60.0)):
        collect.record_eta(cache, "incremental", n, w, 10.0)
    sec, rough = collect.estimate_sec(cache["eta"], "refresh", 200)          # 개수당 0.5초(중앙값) × 200 + 고정 10초(수집 계열 실측을 같이 씀)
    assert (sec, rough) == (110, False)
    assert collect.estimate_run_sec(cache["eta"], "incremental") == 60 and collect.estimate_run_sec(cache["eta"], "backfill") is None
    for _ in range(9):
        collect.record_eta(cache, "incremental", 1, 1.0, 1.0)
    assert len(cache["eta"]["incremental"]) == collect.ETA_KEEP


def test_fill_params_stop_keeps_what_was_read_and_resumes(tmp_path, fake_nas, monkeypatch):
    """멈추면 그때까지 읽은 덩어리는 저장되고, 다시 누르면 남은 Report 부터 이어서 한다."""
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    collect.collect(dict(cfg, collect_params=False))
    total = collect.plan_run(cfg).params_missing
    assert total >= 2
    monkeypatch.setattr(collect, "PARAMS_FILL_CHUNK", 1)
    seen = []

    def stop():
        return len(seen) >= 1                                                  # 첫 덩어리를 읽은 뒤 멈춤
    st = collect.fill_params(cfg, progress=lambda d, t, p: seen.append(d), should_stop=stop)
    assert st["stopped"] == 1 and 1 <= st["added"] + st["empty"] < total
    left = collect.plan_run(cfg).params_missing
    assert 0 < left < total                                                    # 읽은 만큼은 저장됐다
    st2 = collect.fill_params(cfg)
    assert st2["targets"] == left and not st2["stopped"] and collect.plan_run(cfg).params_missing == 0
