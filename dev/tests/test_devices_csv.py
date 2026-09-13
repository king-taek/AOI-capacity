"""devices.csv 읽기/쓰기와 장비 폴더 판정."""
from __future__ import annotations

from aoi_capacity import devices
from conftest import make_cfg, make_device


def _cfg():
    return {"report_dir": "Report", "scan_dir": "Scanresult"}


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
