"""devices.csv 읽기/쓰기와 장비 폴더 판정."""
from __future__ import annotations

from aoi_capacity import devices
from conftest import make_cfg, make_device


def _cfg():
    # 장비 해석 엔진 자체를 보는 테스트 → 수집 범위 제한 없음을 명시한다.
    # 기본값(AOI-25 만)의 격리는 test_scope_isolation.py 가 검증한다.
    return {"report_dir": "Report", "scan_dir": "Scanresult", "scope_devices": ["*"]}


def test_read_csv_cp949_and_utf8_and_aliases(tmp_path):
    body = "장비명,NAS경로,폴더,사용,메모\nA,X:\\,AOI-1,Y,메모\nB,Y:\\,,N,\n"
    (tmp_path / "k.csv").write_bytes(body.encode("cp949"))
    (tmp_path / "u.csv").write_text(body, encoding="utf-8-sig")
    (tmp_path / "e.csv").write_text("device,root,folder,enabled\nC,\\\\host\\share,AOI-3,no\n", encoding="utf-8")
    k = devices.read_devices_csv(tmp_path / "k.csv")
    assert k == devices.read_devices_csv(tmp_path / "u.csv")
    assert k[0] == {"name": "A", "root": "X:\\", "sub": "AOI-1", "on": True, "memo": "메모"}
    assert k[1]["on"] is False
    e = devices.read_devices_csv(tmp_path / "e.csv")
    assert e[0]["root"] == "\\\\host\\share" and e[0]["on"] is False


def test_read_csv_without_header_and_comments(tmp_path):
    (tmp_path / "n.csv").write_text("# 주석\nA,X:\\,AOI-1,Y\n\nB,Z:\\,*,아니오,m\n", encoding="utf-8")
    rows = devices.read_devices_csv(tmp_path / "n.csv")
    assert [r["name"] for r in rows] == ["A", "B"] and rows[1]["on"] is False and rows[1]["sub"] == "*"


def test_write_then_read_roundtrip(tmp_path):
    rows = [{"name": "A", "root": "X:\\", "sub": "AOI-1", "on": True, "memo": "m"},
            {"name": "B", "root": "\\\\h\\s", "sub": "*", "on": False, "memo": ""}]
    p = tmp_path / "devices.csv"
    devices.write_devices_csv(p, rows)
    assert p.read_bytes().startswith(b"\xef\xbb\xbf")     # Excel 호환 BOM
    assert devices.read_devices_csv(p) == rows
    assert not (tmp_path / "devices.csv.tmp").exists()


def test_devices_from_rows_auto_dup_and_unreachable(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path)
    logs = []
    devs = devices.devices_from_csv(cfg, log=logs.append)
    assert [d["name"] for d in devs] == ["8호기", "9호기", "AOI-10"]
    assert any("없음" in l for l in logs)                  # 접근 불가 행은 로그로
    assert all("AOI-9" not in d["name"] for d in devs)     # 같은 폴더의 * 행은 명시 행(9호기)에 밀린다


def test_duplicate_folder_names_get_share_prefix(tmp_path):
    make_device(tmp_path / "X", "AOI-1")
    make_device(tmp_path / "I", "AOI-1")
    rows = [{"name": "", "root": str(tmp_path / "X"), "sub": "*", "on": True, "memo": ""},
            {"name": "", "root": str(tmp_path / "I"), "sub": "*", "on": True, "memo": ""}]
    devs = devices.devices_from_rows(rows, _cfg())
    assert len(devs) == 2 and len({d["name"] for d in devs}) == 2


def test_check_rows_status(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    rows = devices.read_devices_csv(csv_path)
    st = {r["name"]: r["status"] for r in devices.check_rows(rows, _cfg())}
    assert st["9호기"] == "ok" and st["엑스전체"] == "auto:2" and st["8호기"] == "ok" and st["없음"] == "unreachable"


def test_discover_devices_fallback_without_csv(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, tmp_path / "missing.csv", nas_roots=[str(nas / "X")])
    assert [d["name"] for d in devices.resolve_devices(cfg)] == ["AOI-9", "AOI-10"]


# ── Scanresult 백업 폴더 (30대 실물 이름 그대로) ─────────────────────────────
import datetime as dt
import os
import pytest


@pytest.mark.parametrize("name,year,expected", [
    ("Scanresult_Back up_260918", None, dt.date(2026, 9, 18)),
    ("Scanresult Backup_260707", None, dt.date(2026, 7, 7)),
    ("Scanresult backup260904", None, dt.date(2026, 9, 4)),
    ("Scanresult_BAKCUP_260429", None, dt.date(2026, 4, 29)),
    ("Scanresult_Backup_250324", None, dt.date(2025, 3, 24)),
    ("Scanresult - BACKTUP 0827", 2026, dt.date(2026, 8, 27)),
    ("Scanresult_0901", 2026, dt.date(2026, 9, 1)),
    ("Scanresult_260820", None, dt.date(2026, 8, 20)),
    ("Scanresult_Backup_268020", None, None),     # 있을 수 없는 날짜
    ("Scanresult - 5.9.3", 2026, None),           # 백업이 아니라 버전명
    ("Scanresult_BACKUP", 2026, None),            # 날짜 없음
])
def test_backup_cutoff_reads_every_folder_name_seen_on_30_machines(name, year, expected):
    assert devices.backup_cutoff(name, year) == expected


def test_scan_dirs_of_lists_the_live_folder_first_then_backups_by_cutoff(tmp_path):
    dev = make_device(tmp_path / "X", "AOI-5")
    for n in ("Scanresult_Backup_250324", "Scanresult_0901", "Scanresult_Back up_260607", "Scanresult - 5.9.3", "Scanresult_Backup_268020"):
        (dev / n).mkdir()
    (dev / "Scanresult_0901" / "x").write_text("", encoding="utf-8")
    t = dt.datetime(2026, 9, 1, 12, 0).timestamp()
    os.utime(dev / "Scanresult_0901", (t, t))
    (dev / "ScanresultNotes.txt").write_text("", encoding="utf-8")          # 파일은 후보가 아니다
    out = devices.scan_dirs_of(str(dev), "Scanresult")
    assert out[0] == {"name": "Scanresult", "cutoff": ""}
    assert [x["name"] for x in out[1:4]] == ["Scanresult_Backup_250324", "Scanresult_Back up_260607", "Scanresult_0901"]
    assert [x["cutoff"] for x in out[1:4]] == ["2025-03-24", "2026-06-07", "2026-09-01"]
    assert {x["name"] for x in out[4:]} == {"Scanresult - 5.9.3", "Scanresult_Backup_268020"} and all(x["cutoff"] == "" for x in out[4:])
    assert devices.scan_dirs_of(str(tmp_path / "nowhere"), "Scanresult") == [{"name": "Scanresult", "cutoff": ""}]


def test_with_dirs_attaches_backups_and_collect_uses_them(tmp_path):
    dev = make_device(tmp_path / "X", "AOI-4")
    (dev / "Scanresult_Back up_260918").mkdir()
    d = devices.with_dirs({"name": "AOI-4", "path": str(dev), "id": "x"}, _cfg())
    assert [x["name"] for x in d["scan_dirs"]] == ["Scanresult", "Scanresult_Back up_260918"]
    from aoi_capacity import collect
    roots = collect._backup_roots(d, str(dev / "Scanresult"))
    assert roots == [(str(dev / "Scanresult_Back up_260918"), dt.date(2026, 9, 18))]
