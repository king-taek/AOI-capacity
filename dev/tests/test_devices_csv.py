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


# ── C05: 지금 쓰는 Scanresult 폴더를 '백업' 으로 한 번 더 세지 않는다 (Windows 경로 의미로 비교) ──────────
@pytest.mark.parametrize("a,b", [
    ("Scanresult", "SCANRESULT"), ("Scanresult", "ScanResult"), ("Scanresult", "Scanresult\\"), ("Scanresult", "Scanresult/"),
    ("X:\\AOI-1\\Scanresult\\", "x:/aoi-1/SCANRESULT"), ("\\\\host\\share\\AOI-1\\Scanresult", "\\\\HOST\\Share\\AOI-1\\scanresult\\"),
])
def test_dir_key_treats_case_and_trailing_separator_as_one(a, b):
    """`os.path.normcase` 는 Linux 에서 아무것도 하지 않는다 — 판정은 `ntpath` 로 하므로 어느 OS 에서 돌려도 같다."""
    assert devices.dir_key(a) == devices.dir_key(b) and devices.same_dir(a, b)
    assert not devices.same_dir("Scanresult", "Scanresult_Backup_260918")
    assert devices.dir_key("") == "" and not devices.same_dir("", "Scanresult")


def _case_insensitive_isdir(monkeypatch):
    """Windows 의 대소문자 무시 파일시스템을 Linux 에서 흉내 낸다 — 마지막 조각을 대소문자 무시로 찾는다(명시적 시뮬레이션)."""
    real = os.path.isdir

    def ci_isdir(p):
        if real(p):
            return True
        parent, leaf = os.path.split(str(p).rstrip("\\/"))
        if not leaf or not real(parent):
            return False
        return any(n.lower() == leaf.lower() and real(os.path.join(parent, n)) for n in os.listdir(parent))

    monkeypatch.setattr(devices.os.path, "isdir", ci_isdir)


def test_live_folder_spelled_differently_is_one_root_not_a_backup(tmp_path, monkeypatch):
    """실제 폴더 `ScanResult` · 설정 `Scanresult`: isdir 은 참이라 예전엔 `ScanResult` 가 backups 에 한 번 더 들어가
    없는 INI 마다 확인이 두 배였다. 이제 맨 앞은 나열된 실제 철자, 백업은 0개."""
    dev = make_device(tmp_path / "X", "AOI-5")
    (dev / "Scanresult").rename(dev / "ScanResult")
    _case_insensitive_isdir(monkeypatch)
    d = devices.with_dirs({"name": "AOI-5", "path": str(dev), "id": "x"}, _cfg())
    assert d["scan_dir"] == "ScanResult" and d["scan_dirs"] == [{"name": "ScanResult", "cutoff": ""}]
    from aoi_capacity import collect
    assert collect._backup_roots(d, str(dev / "Scanresult")) == []           # 설정 철자로 만든 루트와도 같은 폴더
    assert collect._backup_roots(d, str(dev / "ScanResult")) == []


def test_backups_that_differ_only_by_case_or_separator_are_deduped_and_live_folder_kept_first(tmp_path):
    dev = make_device(tmp_path / "X", "AOI-6")
    (dev / "Scanresult_Backup_260918").mkdir()
    (dev / "SCANRESULT_BACKUP_260918").mkdir()                              # Windows 에서는 같은 폴더(Linux 픽스처라 둘 다 만든다)
    (dev / "Scanresult - 5.9.3").mkdir()
    out = devices.scan_dirs_of(str(dev), "SCANRESULT")                       # 설정 철자가 달라도 맨 앞은 나열된 실제 철자
    assert out[0] == {"name": "Scanresult", "cutoff": ""}
    assert [x["name"] for x in out[1:]] == ["SCANRESULT_BACKUP_260918", "Scanresult - 5.9.3"]   # 사전순 첫 철자 하나만
    assert out[1]["cutoff"] == "2026-09-18"
    assert len({devices.dir_key(x["name"]) for x in out}) == len(out)
    # 우선순위(정확 경로 → 경계 이른 백업 → 경계 모르는 백업)는 그대로다
    from aoi_capacity import collect
    d = devices.with_dirs({"name": "AOI-6", "path": str(dev), "id": "y"}, _cfg())
    roots = collect._backup_roots(d, str(dev / "Scanresult"))
    assert [c for _, c in roots] == [dt.date(2026, 9, 18), None]
    assert collect.ini_roots_for(dt.datetime(2026, 9, 1), str(dev / "Scanresult"), roots)[0] == str(dev / "SCANRESULT_BACKUP_260918")


# ── C08: 장비 확인 단계를 read_workers 개씩 동시에 — 결과·로그 순서는 1개로 돌린 것과 같다 ──────────
def _many_devices(tmp_path):
    nas = tmp_path / "nas"
    for i in range(1, 13):
        make_device(nas / "X", f"AOI-{i}")
    make_device(nas / "M", "AOI-13")
    (nas / "M" / "AOI-13" / "Report").rename(nas / "M" / "AOI-13" / "Reports")           # 폴더 이름이 다른 장비
    (nas / "X" / "AOI-3" / "Scanresult_Backup_260918").mkdir()
    csv_path = tmp_path / "devices.csv"
    csv_path.write_text(
        "장비명,NAS경로,폴더,사용,메모\n"
        + "".join(f"AOI-{i},{nas / 'X'},AOI-{i},Y,\n" for i in range(1, 13))
        + f"열셋,{nas / 'M'},AOI-13,Y,\n"
        f"엑스전체,{nas / 'X'},*,Y,\n"
        f"없음,{nas / 'none'},AOI-1,Y,접근불가\n"
        f"AOI-99,{nas / 'X'},AOI-99,Y,폴더 없음\n",
        encoding="utf-8-sig")
    return nas, csv_path


def _snapshot(cfg, csv_path):
    logs = []
    devs = devices.resolve_devices(cfg, logs.append)
    rows = devices.read_devices_csv(csv_path)
    return devs, logs, devices.check_rows(rows, cfg)


@pytest.mark.parametrize("workers", [2, 8, 32])
def test_device_check_pool_gives_identical_results_and_log_order(tmp_path, workers):
    nas, csv_path = _many_devices(tmp_path)
    base = _snapshot(make_cfg(tmp_path, csv_path, read_workers=1), csv_path)
    many = _snapshot(make_cfg(tmp_path, csv_path, read_workers=workers), csv_path)
    assert many == base
    devs, logs, checks = base
    assert [d["name"] for d in devs] == [f"AOI-{i}" for i in range(1, 13)] + ["열셋"]     # 사용자가 붙인 이름은 그대로
    assert next(d for d in devs if d["name"] == "열셋")["report_dir"] == "Reports"
    assert [x["name"] for x in next(d for d in devs if d["name"] == "AOI-3")["scan_dirs"]] == ["Scanresult", "Scanresult_Backup_260918"]
    assert [l for l in logs if l.startswith("[건너뜀]")] == [f"[건너뜀] 없음: Report 폴더 없음/접근 불가 ({nas / 'none' / 'AOI-1'})",
                                                        f"[건너뜀] AOI-99: Report 폴더 없음/접근 불가 ({nas / 'X' / 'AOI-99'})"]
    assert {r["name"]: r["status"] for r in checks}["엑스전체"] == "auto:12" and {r["name"]: r["status"] for r in checks}["없음"] == "unreachable"
    # 범위 제한 + 32개 — 범위 밖 행의 로그도 행 순서 그대로
    restricted = dict(scope_devices=["AOI-2", "AOI-13"])
    a = _snapshot(make_cfg(tmp_path, csv_path, read_workers=1, **restricted), csv_path)
    b = _snapshot(make_cfg(tmp_path, csv_path, read_workers=workers, **restricted), csv_path)
    assert a == b and [d["name"] for d in a[0]] == ["AOI-2", "열셋"]
    assert sum(1 for l in a[1] if l.startswith("[범위 밖]")) == 13                      # AOI-1·3~12 · 없음(AOI-1) · AOI-99 행


def test_pool_size_follows_read_workers_and_task_count():
    assert devices._pool_size({"read_workers": 8}, 30) == 8 and devices._pool_size({"read_workers": 8}, 3) == 3
    assert devices._pool_size({"read_workers": 1}, 30) == 1 and devices._pool_size({}, 30) == 8
    assert devices._pool_size({"read_workers": "abc"}, 30) == 8 and devices._pool_size({"read_workers": 999}, 100) == 32
    assert devices._pool_size({"read_workers": 0}, 30) == 1


def test_cancel_stops_submitting_new_checks(tmp_path, monkeypatch):
    """취소되면 아직 시작하지 않은 확인은 하지 않는다 — 이미 들어간 SMB 호출을 끊는다고 주장하지는 않는다."""
    nas, csv_path = _many_devices(tmp_path)
    probes = []
    real = os.path.isdir
    monkeypatch.setattr(devices.os.path, "isdir", lambda p: (probes.append(str(p)), real(p))[1])
    cfg = make_cfg(tmp_path, csv_path, read_workers=8)
    assert devices.resolve_devices(cfg, should_stop=lambda: True) == []
    assert [p for p in probes if str(nas) in p] == []                                    # 장비 폴더는 하나도 만지지 않았다
    # 한 줄로 돌릴 때 첫 확인 뒤 취소 → 그 행만 확인하고 나머지는 건너뛴다(결정적)
    probes.clear()
    seen = {"n": 0}

    def stop_after_first() -> bool:
        seen["n"] += 1
        return seen["n"] > 1

    devs = devices.devices_from_rows(devices.read_devices_csv(csv_path), make_cfg(tmp_path, csv_path, read_workers=1),
                                     should_stop=stop_after_first)
    assert [d["name"] for d in devs] == ["AOI-1"]
    assert all(str(nas / "X" / "AOI-1") in p for p in probes if str(nas) in p)
    # collect 는 취소를 이어받아 CollectCancelled 로 끝난다(캐시 없음)
    from aoi_capacity import collect
    with pytest.raises(collect.CollectCancelled):
        collect.collect(cfg, should_stop=lambda: True)
    assert not (tmp_path / "out" / "aoi_cache.json").exists()
