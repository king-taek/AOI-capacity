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
