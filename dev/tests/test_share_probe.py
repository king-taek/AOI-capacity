"""공유 폴더 시험 도구(scripts/share_probe.py) 계약.

1. 장비 NAS 아래이거나 장비 NAS 와 같은 공유(이름 · IP · 드라이브 문자 어느 표기든)면 아무것도 쓰지 않고 멈춘다.
2. 쓰기는 `<공유 폴더>/_aoi_share_probe/` 안뿐이고 --clean 은 이 도구가 만든 파일만 지운다.
3. 시험 페이지는 바깥으로 요청을 보내지 않는다(주소는 장비 폴더 file:// 링크뿐).
4. 표준 라이브러리만 쓴다 — 앱 패키지를 import 하지 않는다.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("share_probe", _ROOT / "scripts" / "share_probe.py")
sp = importlib.util.module_from_spec(_spec)
sys.modules["share_probe"] = sp
_spec.loader.exec_module(sp)

DRIVES = {"X:": r"\\10.142.80.90\aoi", "S:": r"\\k5cifsn2\k5tsvdata$"}
resolver = DRIVES.get


def _dns(host):
    table = {"k5cifsn2": ("k5cifsn2.corp.local", [], ["10.1.2.3"]),
             "10.1.2.3": ("10.1.2.3", [], ["10.1.2.3"]),
             "10.142.80.90": ("10.142.80.90", [], ["10.142.80.90"])}
    if host.lower() not in table:
        raise OSError("no dns")
    return table[host.lower()]


def test_refuses_under_device_root_and_same_share_in_any_spelling():
    roots = [("AOI-1", r"X:\AOI-1"), ("AOI-9", r"\\10.1.2.3\k5tsvdata$\AOI-9")]
    for t in (r"X:\AOI-1\out", r"X:\other", r"\\10.142.80.90\aoi\x",     # 같은 드라이브 · UNC 동치
              r"\\K5CIFSN2\K5TSVDATA$\1. Conder Scan",                    # 이름 ↔ IP 같은 서버 · 같은 공유
              r"S:\1. Conder Scan"):                                      # 드라이브 문자 → 같은 공유
        with pytest.raises(sp.Refused):
            sp.check_target(t, roots, resolver=resolver, resolve=_dns)


def test_other_share_on_same_server_is_allowed_but_noted():
    info = sp.check_target(r"\\k5cifsn2\team$\AOI", [("AOI-9", r"\\10.1.2.3\k5tsvdata$\AOI-9")],
                           resolver=resolver, resolve=_dns)
    assert info["same_server"] == ["AOI-9"]
    info = sp.check_target(r"\\k5cifsn2\k5tsvdata$\x", [("AOI-1", r"X:\AOI-1")], resolver=resolver, resolve=_dns)
    assert info["same_server"] == [] and info["checked_roots"] == 1


def test_read_devices_and_links(tmp_path):
    csv = tmp_path / "devices.csv"
    csv.write_text("장비명,NAS경로,폴더,사용,메모\nAOI-1,X:\\,AOI-1,Y,\nAOI-2,X:\\,AOI-2,Y,\nAOI-8,M:\\,AOI-8,N,\nK1,Z:\\,,Y,\n",
                   encoding="utf-8-sig")
    devs = sp.read_devices(csv)
    assert [d[:2] for d in devs] == [("AOI-1", r"X:\AOI-1"), ("AOI-2", r"X:\AOI-2"), ("AOI-8", r"M:\AOI-8"), ("K1", "Z:\\")]
    links = sp.device_links(devs, resolver=resolver)
    assert [l["label"] for l in links] == ["AOI-1 (X:)", "AOI-1 (UNC)"]   # 드라이브마다 하나 · 꺼진 장비 · KLA 제외
    assert links[0]["url"] == "file:///X:/AOI-1/" and links[1]["url"] == "file://10.142.80.90/aoi/AOI-1/"


def _snapshot(root: Path):
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*")}


def test_run_writes_only_inside_probe_dir_and_clean_removes_only_own_files(tmp_path):
    share, nas, out = tmp_path / "share", tmp_path / "nas", tmp_path / "out"
    (nas / "AOI-1").mkdir(parents=True)
    share.mkdir()
    (share / "남의 파일.txt").write_text("x", encoding="utf-8")
    csv = tmp_path / "devices.csv"
    csv.write_text(f"장비명,NAS경로,폴더,사용\nAOI-1,{nas},AOI-1,Y\n", encoding="utf-8")
    before_nas, before_share = _snapshot(nas), _snapshot(share)
    args = SimpleNamespace(target=str(share), devices=str(csv), no_devices=False, sizes=[0.02, 0.05], gz_raw_mb=0.05, out=str(out))
    res = sp.run(args, log=lambda *_: None)
    sp._save(res, out, str(share), log=lambda *_: None)
    assert _snapshot(nas) == before_nas
    probe = share / sp.PROBE_DIR
    new = set(_snapshot(share)) - set(before_share)
    assert all(Path(p) == probe or Path(p).parent == probe for p in new)
    names = sorted(p.name for p in probe.iterdir())
    assert names == sorted([sp.MARKER, "시험_0.02MB.html", "시험_0.05MB.html", "시험_gzip.html", sp.HAMMER_FILE, "시험_안내.html"])
    assert not any(".tmp-" in n for n in names)
    assert all(w["replace_ok"] for w in res["writes"])
    # 시험 페이지: 가짜 데이터 행 수가 맞고, 바깥 주소가 없다
    page = (probe / "시험_0.05MB.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1))
    assert len(data["rows"]) == data["n"] > 0
    for f in probe.glob("*.html"):
        assert not re.search(r"https?://", f.read_text(encoding="utf-8")), f.name
    (probe / "팀원이 만든 것.txt").write_text("y", encoding="utf-8")
    gone = sp.Probe(str(share)).clean()
    assert sp.MARKER not in gone and len(gone) == 5
    assert sorted(p.name for p in probe.iterdir()) == ["팀원이 만든 것.txt"]   # 남의 파일은 그대로 · 폴더도 남는다
    assert (share / "남의 파일.txt").read_text(encoding="utf-8") == "x"


def test_run_stops_without_devices_csv_unless_told(tmp_path):
    args = SimpleNamespace(target=str(tmp_path), devices=str(tmp_path / "없음.csv"), no_devices=False, sizes=[0.01], gz_raw_mb=0.01, out="")
    with pytest.raises(sp.Refused):
        sp.run(args, log=lambda *_: None)
    assert not (tmp_path / sp.PROBE_DIR).exists()


def test_main_refuses_target_under_nas(tmp_path, capsys):
    nas = tmp_path / "nas"
    (nas / "AOI-1").mkdir(parents=True)
    csv = tmp_path / "devices.csv"
    csv.write_text(f"장비명,NAS경로,폴더,사용\nAOI-1,{nas},AOI-1,Y\n", encoding="utf-8")
    rc = sp.main(["--target", str(nas / "AOI-1"), "--devices", str(csv), "--out", str(tmp_path / "o"), "--yes", "--sizes", "0.01"])
    assert rc == 3 and "멈춤" in capsys.readouterr().out
    assert sorted(p.name for p in (nas / "AOI-1").iterdir()) == []


def test_stdlib_only():
    tree = ast.parse((_ROOT / "scripts" / "share_probe.py").read_text(encoding="utf-8"))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    assert mods <= set(sys.stdlib_module_names) | {"__future__"}, mods
