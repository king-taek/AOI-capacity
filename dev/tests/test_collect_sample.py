"""샘플 수집 도구(scripts/collect_sample.py) 계약.

현장에서 사용자가 직접 돌리는 도구라 두 가지를 반드시 지켜야 한다.
1. NAS 는 읽기만 한다 — NAS 아래에 어떤 파일도 만들지 않고, 저장 위치가 NAS 안이면 시작조차 하지 않는다.
2. Scanresult 를 재귀 검색하지 않는다 — Report 이름에서 계산한 Lot 폴더만 정확히 한 번 나열한다.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import time
import zipfile
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("collect_sample", _ROOT / "scripts" / "collect_sample.py")
sampler = importlib.util.module_from_spec(_spec)
sys.modules["collect_sample"] = sampler
_spec.loader.exec_module(sampler)

EQ, PROC = "2D@R2-GA285AAB_0859840PD-0A", "6321"
INI = "[AutoCycleInfo]\nWaferStartTime=15-Sep-26 05:31:04 PM\nWaferEndTime=15-Sep-26 05:32:02 PM\nUseLot={lot}\n"


JOB, SETUP = "TB500_RDL2 - Multi", "Setup1"


def _report(lot: str, status: str) -> str:
    """실장비 형식 — 경로의 출처는 파일명이 아니라 Job/Setup 이다."""
    return ("<html><body><table>"
            "<tr><td>Batch Start</td><td>15-Sep-26 05:25:14 PM</td><td>Batch End</td><td>15-Sep-26 06:25:14 PM</td></tr>"
            f"<tr><td>Wafers Scanned</td><td>2</td><td>Job/Setup</td><td>{JOB}/{SETUP}</td></tr></table>"
            "<table><tr><th>Lot</th><th>Wafer ID</th><th>Pass/Fail</th></tr>"
            f"<tr><td>{lot}</td><td>K625407-01B0</td><td>Pass</td></tr>"
            f"<tr><td>{lot}</td><td>K625407-02B0</td><td>{status}</td></tr></table></body></html>")


@pytest.fixture
def nas(tmp_path):
    """Y:\\AOI-25 를 흉내 낸 트리 — 정상 · 표기별 · Scan error · 재스캔 후보를 섞는다."""
    root = tmp_path / "nas" / "AOI-25"
    rep, scan = root / "Report", root / "Scanresult"
    rep.mkdir(parents=True)
    cases = [("KLN", "Pass"), ("KLN-3D", "Pass"), ("XAC DIA", "Pass"), ("WUK SRD", "Pass"), ("TUK RE", "Pass"),
             ("HCL", "Scan Error: Scan2d optic is not valid on machine."), ("HCL", "Pass")]
    now = time.time()
    for i, (lot, status) in enumerate(cases):
        p = rep / f"{EQ}_{PROC}_{lot}_26-Sep-15_({8 + i:02d}.00.00)_BatchReport.htm"
        p.write_text(_report(lot, status), encoding="utf-8")
        os.utime(p, (now - (len(cases) - i) * 600,) * 2)
        for w in ("K625407-01B0", "K625407-02B0"):
            d = scan / JOB / SETUP / lot / w
            d.mkdir(parents=True, exist_ok=True)
            (d / "WaferInfo.ini").write_text(INI.format(lot=lot), encoding="utf-8")
    (scan / JOB / SETUP / "HCL" / "K625407-02B0_RE").mkdir()      # 재스캔용 폴더처럼 보이는 것(INI 없음)
    (rep / "다른이름.htm").write_text("<html>x</html>", encoding="utf-8")
    return root


def _fingerprint(root: Path):
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, hashlib.md5(p.read_bytes()).hexdigest())
            for p in sorted(root.rglob("*")) if p.is_file()}


def test_run_collects_expected_sample_and_never_writes_to_nas(tmp_path, nas, capsys):
    before = _fingerprint(nas)
    out = tmp_path / "desktop"
    assert sampler.main(["--root", str(nas), "--out", str(out), "--days", "1"]) == 0
    assert _fingerprint(nas) == before, "★ NAS 원본이 바뀌었다"

    folder = next(p for p in out.iterdir() if p.is_dir())
    summary = (folder / "요약.txt").read_text(encoding="utf-8")
    for suffix in ("RE", "SRD", "DIA", "3D", "(접미사 없음)"):
        assert suffix in summary                       # Lot 표기 히스토그램
    assert "SCAN_ERROR" in summary and "재스캔 확인용" in summary
    assert "K625407-02B0_RE/  (WaferInfo.ini 없음)" in (folder / "scan_폴더구조.txt").read_text(encoding="utf-8")
    assert len(list((folder / "Report").glob("*.htm"))) >= 6
    assert list(folder.rglob("WaferInfo.ini"))
    assert (folder / "report_목록.txt").read_text(encoding="utf-8").count("BatchReport") >= 7

    zips = list(out.glob("*.zip"))
    assert len(zips) == 1
    with zipfile.ZipFile(zips[0]) as z:
        names = z.namelist()
    assert any(n.endswith("요약.txt") for n in names) and any("WaferInfo.ini" in n for n in names)


def test_refuses_to_write_inside_the_nas(nas):
    assert sampler.main(["--root", str(nas), "--out", str(nas / "sample")]) == 2
    assert not (nas / "sample").exists()


def test_scanresult_is_never_walked_recursively(tmp_path, nas, monkeypatch):
    """Lot 폴더만 정확히 나열해야 한다 — Scanresult 루트나 그 위쪽을 훑으면 실패."""
    scan_root = (nas / "Scanresult").resolve()
    bad = []
    real = os.scandir

    def watched(path=".", *a, **kw):
        p = Path(str(path)).resolve()
        if p == scan_root or p in scan_root.parents or (scan_root in p.parents and len(p.parts) - len(scan_root.parts) < 3):
            bad.append(str(p))
        return real(path, *a, **kw)

    monkeypatch.setattr(os, "scandir", watched)
    assert sampler.main(["--root", str(nas), "--out", str(tmp_path / "d")]) == 0
    assert not bad, f"Scanresult 를 훑었다: {bad}"


def test_missing_report_dir_is_reported_not_crashed(tmp_path, capsys):
    assert sampler.main(["--root", str(tmp_path / "없는장비"), "--out", str(tmp_path / "d")]) == 2
    out = capsys.readouterr().out
    assert "없음" in out and "--list" in out          # 원인과 다음 시도를 알려 준다


def test_reports_folder_name_is_detected_automatically(tmp_path, nas):
    """AOI-25 는 Report 가 아니라 Reports 다 — 설정 없이도 찾아낸다."""
    (nas / "Report").rename(nas / "Reports")
    assert sampler.main(["--root", str(nas), "--out", str(tmp_path / "d")]) == 0
    folder = next(p for p in (tmp_path / "d").iterdir() if p.is_dir())
    assert list(folder.rglob("WaferInfo.ini"))


def test_diagnose_points_at_an_unexpected_report_folder_name(tmp_path, nas, capsys):
    """이름을 짐작할 수 없으면 그 폴더 안에 무엇이 있는지 보여 준다."""
    (nas / "Report").rename(nas / "보고서")
    assert sampler.main(["--root", str(nas), "--out", str(tmp_path / "d")]) == 2
    out = capsys.readouterr().out
    assert "보고서" in out and "--root" in out


def test_list_mode_shows_immediate_children(tmp_path, nas, capsys):
    assert sampler.main(["--list", "--root", str(nas)]) == 0
    out = capsys.readouterr().out
    assert "[폴더] Report" in out and "[폴더] Scanresult" in out
    assert sampler.main(["--list", "--root", str(tmp_path / "없음")]) == 2


@pytest.mark.parametrize("given,expected_tail", [("Y:", "Y:" + os.sep), ("Y:" + os.sep, "Y:" + os.sep),
                                                 ('"Y:' + os.sep + 'AOI-25"', "AOI-25")])
def test_norm_root_fixes_bare_drive_letter(given, expected_tail):
    assert str(sampler.norm_root(given)).endswith(expected_tail.rstrip(os.sep)) or \
           str(sampler.norm_root(given)) == expected_tail


@pytest.mark.parametrize("lot,expected", [
    ("TUK RESCAN", ("TUK", "RESCAN")), ("XAC-DIA", ("XAC", "DIA")), ("KLN_3D", ("KLN", "3D")),
    ("HCL", ("HCL", "")), ("WUK SRD", ("WUK", "SRD")),
])
def test_lot_suffix_split(lot, expected):
    assert sampler.lot_parts(lot) == expected
