"""Wafer 폴더 로그 모으기 도구(scripts/collect_wafer_logs.py) 계약.

1. NAS 는 읽기만 한다 — 실행 전후로 장비 폴더 아래 모든 파일·폴더의 이름·크기·수정시각이 같아야 한다.
2. Scanresult 를 재귀 검색하지 않는다 — Report 로 계산한 Lot 폴더만 본다(옆 Lot 폴더는 zip 에 없다).
3. `.dat` 과 이미지는 담지 않고, 한 Lot 안에서 내용이 같은 파일은 한 번만 담는다.
4. zip 은 마지막 장을 빼고 [part_min, part_max] 안이다.
"""
from __future__ import annotations

import importlib.util
import os
import random
import sys
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("collect_wafer_logs", _ROOT / "scripts" / "collect_wafer_logs.py")
tool = importlib.util.module_from_spec(_spec)
sys.modules["collect_wafer_logs"] = tool
_spec.loader.exec_module(tool)


def _report(job: str, setup: str, lot: str, wafers, status="Pass") -> str:
    rows = "".join(f"<tr><td>{lot}</td><td>{w}</td><td>{status}</td></tr>" for w in wafers)
    return ("<html><body><table>"
            "<tr><td>Batch Start</td><td>15-Sep-26 05:25:14 PM</td><td>Batch End</td><td>15-Sep-26 06:25:14 PM</td></tr>"
            f"<tr><td>Wafers Scanned</td><td>{len(wafers)}</td><td>Job/Setup</td><td>{job}/{setup}</td></tr></table>"
            "<table><tr><th>Lot</th><th>Wafer ID</th><th>Pass/Fail</th></tr>"
            f"{rows}</table></body></html>")


def _make_nas(base: Path, rnd: random.Random):
    """장비 두 대 · Lot 다섯 개. 각 Wafer 폴더에 공통 파일 · Wafer 마다 다른 파일 · .dat · 이미지 · 하위 폴더."""
    lots = [("AOI-1", "TB500_RDL4 - Multi", "LOTA", 2), ("AOI-1", "R_TB500_LIVE_PI2", "LOTB", 2),
            ("AOI-2", "TB500_RDL3 - Multi", "LOTC", 3), ("AOI-2", "Kendall_X", "LOTD", 2),
            ("AOI-2", "Other_Job", "LOTE RESCAN", 2)]
    for i, (dev, job, lot, n) in enumerate(lots):
        root = base / dev
        (root / "Report").mkdir(parents=True, exist_ok=True)
        wafers = [f"W{i}{k:02d}" for k in range(n)]
        name = f"{job.replace(' ', '')}_6321_{lot.replace(' ', '_')}_26-Sep-15_(18.{i:02d}.00)_BatchReport.htm"
        (root / "Report" / name).write_text(_report(job, "Setup1", lot, wafers), encoding="utf-8")
        common = rnd.randbytes(30_000)                           # 같은 Lot 안에서 Wafer 마다 같은 파일
        for w in wafers:
            wd = root / "Scanresult" / job / "Setup1" / lot / w
            (wd / "Zones").mkdir(parents=True)
            (wd / "Zones" / "ScanArea.ini").write_bytes(common)
            (wd / "RTP.txt").write_bytes(common)                 # 다른 경로지만 같은 내용 → 한 번만
            (wd / "WaferInfo.ini").write_text(f"[AutoCycleInfo]\nUseWaferID={w}\n", encoding="utf-8")
            (wd / "ScanLog.ini").write_bytes(rnd.randbytes(25_000))
            (wd / "s_FrameData.dat").write_bytes(b"\0" * 5000)
            (wd / "x.jpeg").write_bytes(b"\xff\xd8" * 100)
            (wd / "MoveResultFlag").write_bytes(b"")
            if "RDL3" in job:
                (wd / "RecipesInfo.ini").write_text("[Recipe-1]\nName=x20\n[Recipes]\nCount=1\n", encoding="utf-8")
        # 옆 Lot 폴더(같은 Setup) — Report 가 가리키지 않으니 담기면 안 된다
        decoy = root / "Scanresult" / job / "Setup1" / f"DECOY{i}" / "W99"
        decoy.mkdir(parents=True)
        (decoy / "WaferInfo.ini").write_text("decoy", encoding="utf-8")
    return [base / "AOI-1", base / "AOI-2"]


def _snapshot(base: Path):
    out = {}
    for d, dirs, files in os.walk(base):
        for n in dirs + files:
            p = os.path.join(d, n)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def test_collects_read_only_dedups_and_splits(tmp_path):
    nas, out = tmp_path / "nas", tmp_path / "out"
    roots = _make_nas(nas, random.Random(7))
    before = _snapshot(nas)
    rc = tool.main(["--roots", *map(str, roots), "--out", str(out), "--min-lots", "5", "--days", "100000",
                    "--part-max", "200000", "--part-min", "150000", "--workers", "3"])
    assert rc == 0
    assert _snapshot(nas) == before                               # NAS 아래 아무것도 바뀌지 않음

    parts = sorted(out.glob("AOI_wafer_logs_*_part*.zip"))
    assert len(parts) >= 2
    for p in parts[:-1]:
        assert 150_000 <= p.stat().st_size <= 200_000, (p.name, p.stat().st_size)
    assert parts[-1].stat().st_size <= 200_000

    names = []
    for p in parts:
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            names += z.namelist()
    assert len(names) == len(set(names))
    assert not [n for n in names if n.endswith((".dat", ".jpeg"))]
    assert not [n for n in names if "DECOY" in n]                 # 계산한 Lot 폴더만
    assert "요약.txt" in names and "lots.json" in names
    lot_dirs = {n.split("/")[0] for n in names if "/" in n}
    assert len(lot_dirs) == 5
    # 같은 내용(Zones/ScanArea.ini · RTP.txt · 빈 MoveResultFlag)은 Lot 마다 한 번 — 다른 Wafer 의 WaferInfo 는 전부
    for lot in lot_dirs:
        mine = [n for n in names if n.startswith(lot + "/")]
        assert sum(n.endswith(("ScanArea.ini", "RTP.txt")) for n in mine) == 1
        assert sum(n.endswith("MoveResultFlag") for n in mine) == 1
        waf = [n for n in mine if n.endswith("WaferInfo.ini")]
        assert len(waf) == len({n.split("/")[1] for n in mine if n.split("/")[1] not in ("report", "_목록.tsv")})
        assert any(n.startswith(lot + "/report/") for n in mine) and lot + "/_목록.tsv" in mine


def test_listing_marks_skipped_and_same(tmp_path):
    nas, out = tmp_path / "nas", tmp_path / "out"
    roots = _make_nas(nas, random.Random(3))
    assert tool.main(["--roots", str(roots[0]), "--out", str(out), "--min-lots", "1", "--days", "100000"]) == 0
    text = ""
    for p in out.glob("*.zip"):
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if n.endswith("_목록.tsv"):
                    text += z.read(n).decode("utf-8")
    assert "건너뜀: .dat 제외" in text and "건너뜀: 이미지 제외" in text and "\t= " in text


def test_refuses_output_on_nas_drive(tmp_path):
    nas = tmp_path / "nas"
    roots = _make_nas(nas, random.Random(1))
    before = _snapshot(nas)
    assert tool.main(["--roots", str(roots[0]), "--out", str(roots[0] / "out")]) == 2
    assert _snapshot(nas) == before


def test_job_folder_variants_match_the_app():
    from aoi_capacity import collect
    for job in ("2D@RE $7781539A-WUP_0858562PD_0A", "TB500_RDL4 - Multi", "2D@R2 X-0B", ""):
        assert tool.job_folder_variants(job) == collect.job_folder_variants(job)


def test_categories():
    c = tool.categories
    assert c("TB500_RDL4 - Multi", "L", "AOI-1", False) == ["RDL 멀티"]
    assert c("TB500_RDL2", "L RE", "4F-AOI-01", True) == ["RDL 기타", "4층", "Error 포함", "RESCAN"]
    assert c("R_TB500_LIVE_PI3 Enhanced", "L", "AOI-3", False) == ["PI Enhanced"]
    assert c("TB500_RDL1 Swelling", "L", "AOI-3", False) == ["그 밖의 Job"]
    assert c("Kendall_A", "L TEST", "AOI-3", False) == ["Kendall", "TEST"]


# ── 2차 수집(--wide, 10/10) ─────────────────────────────────────────────────────
def test_wide_reads_only_key_files_at_the_wafer_top(tmp_path):
    """맨 위의 핵심 파일만 읽고(하위 폴더 · 이미지 · .dat · 그 밖 파일은 개수만), NAS 는 그대로, 장비를 돌아가며 고른다."""
    nas, out = tmp_path / "nas", tmp_path / "out"
    roots = _make_nas(nas, random.Random(5))
    before = _snapshot(nas)
    rc = tool.main(["--wide", "--roots", *map(str, roots), "--out", str(out), "--days", "100000",
                    "--part-max", "200000", "--part-min", "150000", "--workers", "2"])
    assert rc == 0 and _snapshot(nas) == before
    parts = sorted(out.glob("AOI_wafer_logs2_*_part*.zip"))
    assert parts
    names, manifest = [], ""
    for p in parts:
        with zipfile.ZipFile(p) as z:
            names += z.namelist()
            manifest += "".join(z.read(n).decode("utf-8") for n in z.namelist() if n.endswith("_목록.tsv"))
    files = {n.rsplit("/", 1)[-1] for n in names if n.count("/") >= 2 and "/report/" not in n}
    assert {"WaferInfo.ini", "ScanLog.ini", "MoveResultFlag", "RecipesInfo.ini"} <= files
    assert "RTP.txt" in files                       # 파라미터 표본(첫 · 마지막 Wafer)은 맨 위 밖 파일 · 하위 폴더까지(아래 목록에서 확인)
    assert not files & {"s_FrameData.dat", "x.jpeg"}                                  # 이미지 · .dat 는 어디서도 읽지 않는다
    rows = [l.split("\t") for l in manifest.splitlines() if l and not l.startswith("wafer\t")]
    lotc = {(r[0], r[1]): r[5] for r in rows if r[0].startswith("W2")}                 # LOTC = Wafer 셋(W200 · W201 · W202)
    assert ("W200", "Zones/ScanArea.ini") in lotc and ("W202", "Zones/ScanArea.ini") in lotc
    assert lotc[("W202", "Zones/ScanArea.ini")].startswith("= ")                       # 같은 Lot 안 같은 내용은 한 번
    assert ("W201", "RTP.txt") not in lotc and ("W201", "Zones/ScanArea.ini") not in lotc   # 가운데 Wafer 는 맨 위 핵심 파일만
    assert lotc[("W201", "(안 읽음)")].endswith("이미지 1 · .dat 1 · 그 밖 1 · 하위 폴더 1")
    assert lotc[("W200", "(안 읽음)")].endswith("이미지 1 · .dat 1 · 그 밖 0 · 하위 폴더 0")
    lot_ids = sorted({n.split("/")[0] for n in names if "/" in n})
    assert [i.split("_")[1] for i in lot_ids[:2]] == ["AOI-1", "AOI-2"]            # 장비를 돌아가며 하나씩


def test_spread_order_covers_ends_first_and_every_index():
    assert tool.spread_order(0) == [] and tool.spread_order(1) == [0]
    for n in (2, 3, 7, 25, 100):
        order = tool.spread_order(n)
        assert sorted(order) == list(range(n)) and order[:2] == [0, n - 1]
        if n >= 3:
            assert order[2] == (n - 1) // 2


def test_wide_survey_spreads_over_the_window(tmp_path):
    root = tmp_path / "nas" / "AOI-1"
    (root / "Report").mkdir(parents=True)
    for d in range(1, 29):
        name = f"J_6321_L{d:02d}_26-Sep-{d:02d}_(10.00.00)_BatchReport.htm"
        (root / "Report" / name).write_text(_report("J", "Setup1", f"L{d:02d}", ["W1"]), encoding="utf-8")
    dev = tool.survey_device(root, 100000, 4, spread=True)
    lots = sorted(r["lot"] for r in dev["reports"])
    assert lots == ["L01", "L10", "L19", "L28"]                                    # 최근 4개가 아니라 기간 전체에
    assert sorted(r["lot"] for r in tool.survey_device(root, 100000, 4)["reports"]) == ["L25", "L26", "L27", "L28"]


def test_report_name_date_is_year_month_day():
    """10/10 현장: `26-Aug-31` 을 31일이 아니라 2031년으로 읽어 '최근 며칠' 이 걸리지 않았다 — 이름의 날짜는 YY-Mon-DD."""
    import time as _t
    got = tool.name_day("2D@RE-X_6321_MDG_26-Aug-31_(10.13.58)_BatchReport.htm")
    assert _t.localtime(got)[:3] == (2026, 8, 31)
    old = tool.name_day("J_6321_L_26-Aug-01_(10.00.00)_BatchReport.htm")
    new = tool.name_day("J_6321_L_26-Sep-30_(10.00.00)_BatchReport.htm")
    assert old < new
