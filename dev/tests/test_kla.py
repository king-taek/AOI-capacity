"""KLA 수집(D73) — Camtek 과 같은 수집기 · 캐시 · 행 계약. 실물(10/5 조사) 모양의 가짜 드라이브로 본다:
날짜 폴더만 센다(D71) · 자정 넘긴 Lot 이 두 날짜 폴더에 겹쳐도 Wafer 폴더 이름으로 한 번 · 결과 파일은 확장자가 아니라 머리로 ·
결함 수 = 레코드 수 · Error 없음(전부 PASS) · 장 시작~다음 장 시작(멈춘 간격·마지막 장은 중앙 간격) · 두 번째 수집은 새 Wafer 만 읽는다."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

import sample_rows
from aoi_capacity import collect, devices, kla, scope
from conftest import make_cfg

T0 = dt.datetime(2026, 10, 4, 22, 30)


def klarf(lot, wafer, slot, rts, n_def, *, two_digit=False):
    ts = rts.strftime("%m-%d-%y %H:%M:%S" if two_digit else "%m-%d-%Y %H:%M:%S")
    recs = "\n".join(f" {i + 1} 1.0 2.0 3 4 0 0 1 1 1 1 0 3 0 0 1 1 1 0 0 0 0 9 0 0 0 0 1 1 1 0;" for i in range(n_def))
    return (f'FileVersion 1 2;\nFileTimestamp {ts};\nResultTimestamp {rts.strftime("%m-%d-%Y %H:%M:%S")};\nLotID "{lot}";\n'
            f'DeviceID "4DT-TB500-H-M1";\nSetupID "ROOT-HVM-4DT-TB500-H-M1-RDL3_K2" 08-20-2026 16:37:00;\nStepID "RDL3_K2";\n'
            f'WaferID "{wafer}";\nSlot {slot};\nDefectList;\n'
            + "".join(f"TiffFileName img{i}.jpg;\nDefectList\n{line}\n" for i, line in enumerate(recs.splitlines()))
            + f"SummarySpec 5\n  TESTNO NDEFECT DEFDENSITY NDIE NDEFDIE ;\nSummaryList\n  3 {n_def} 0.1 30 2 ;\nEndOfFile;\n")


def make_kla(root: Path):
    """K1 드라이브: Lot A 6장(10/4 22:30 시작, 15분 간격, 자정 넘김) — 10/4 폴더에 앞 3장, 10/5 폴더에 6장 전부(겹침).
    Lot B 3장(10/5, 4번째 장 앞 90분 멈춤) + 결과 파일 없는 장 1개. DY(사본) 폴더에 Lot A 복사. 날짜 아닌 파일 몇 개."""
    def wafer(dd, lot, i, t, *, two=False, ext=".001", n_def=2):
        w = root / dd / lot / f"{t:%Y-%m-%d-%H-%M}_{i}"
        w.mkdir(parents=True, exist_ok=True)
        (w / f"4DT_{lot}_W{i}{ext}").write_text(klarf(lot, f"W{i:02d}", i, rts_of[lot], n_def, two_digit=two), encoding="utf-8")
        (w / "img0.jpg").write_bytes(b"x")
        if two:
            (w / "x.pass").write_text("ok", encoding="utf-8")
        return w
    rts_of = {"LOTA@1": T0, "LOTB@2": dt.datetime(2026, 10, 5, 8, 0)}
    for i in range(1, 7):
        t = T0 + dt.timedelta(minutes=15 * (i - 1))
        if t.date() == T0.date():
            wafer("2026-10-04", "LOTA@1", i, t)
        wafer("2026-10-05", "LOTA@1", i, t, two=(i % 2 == 0), ext=".001" if i != 3 else "")
    tb = [dt.datetime(2026, 10, 5, 8, 0), dt.datetime(2026, 10, 5, 8, 12), dt.datetime(2026, 10, 5, 8, 24), dt.datetime(2026, 10, 5, 9, 54)]
    for i, t in enumerate(tb, 1):
        wafer("2026-10-05", "LOTB@2", i, t, n_def=i)
    (root / "2026-10-05" / "LOTB@2" / "2026-10-05-10-06_5").mkdir()        # 스캔 중 — 결과 파일 없음
    for i in range(1, 3):
        wafer("DY", "LOTA@1", i, T0 + dt.timedelta(minutes=15 * (i - 1)))   # 사람 사본 — 세지 않는다(D71)
    (root / "Thumbs.db").write_bytes(b"x")


@pytest.fixture
def kla_nas(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    make_kla(nas / "Z")
    with open(csv_path, "a", encoding="utf-8") as f:
        f.write(f"K1,{nas / 'Z'},,Y,KLA\n")
    return nas, csv_path


def test_scope_and_names():
    assert len(scope.DEFAULT_SCOPE) == 38 and scope.KLA_SCOPE[-1] == "4F-K2"
    assert scope.is_kla("K1") and scope.is_kla("4f_k2") and not scope.is_kla("AOI-1")
    assert devices.kla_name("k 3") == "K3" and devices.kla_name("4f-k1") == "4F-K1"
    assert list(scope.CAMTEK_SCOPE) in scope.PAST_DEFAULTS                   # 옛 기본 30대 그대로인 설정만 38대로


def test_parse_result_counts_defect_records_and_reads_both_timestamp_forms():
    r = kla.parse_result(klarf("L@1", "W01", 1, T0, 3, two_digit=True))
    assert (r["lot"], r["setup"], r["step"], r["wafer"], r["slot"]) == ("L@1", "ROOT-HVM-4DT-TB500-H-M1-RDL3_K2", "RDL3_K2", "W01", "1")
    assert r["defects"] == 3 == r["ndefect"] and r["ndie"] == 30 and r["rts"] == T0.isoformat(timespec="seconds")
    assert kla.parse_ts("10-05-26 19:17:02") == dt.datetime(2026, 10, 5, 19, 17, 2)


def test_collect_reads_kla_once_per_wafer_folder_and_builds_rows(tmp_path, kla_nas):
    _nas, csv_path = kla_nas
    cfg = make_cfg(tmp_path, csv_path)
    stats: dict = {}
    rows, dev_meta, errors = collect.collect(cfg, stats=stats)
    k = [r for r in rows if r["device"] == "K1"]
    assert not errors
    lot_a = sorted((r for r in k if r["lot"] == "LOTA@1"), key=lambda r: r["wafer_start_time"])
    lot_b = sorted((r for r in k if r["lot"] == "LOTB@2"), key=lambda r: collect.parse_dt(r["wafer_start_time"]))
    assert len(lot_a) == 6 and len(lot_b) == 4                          # 두 날짜 폴더 · DY 사본에 겹쳐도 한 번(D71), 결과 파일 없는 장 제외
    assert {r["status"] for r in k} == {"Pass"} and {r["cause"] for r in k} == {""}     # Error 는 수집하지 않는다(D68)
    assert [r["faults"] for r in lot_b] == ["1", "2", "3", "4"] and lot_b[0]["scanned_dice"] == "30"
    assert lot_a[0]["job"] == "ROOT-HVM-4DT-TB500-H-M1-RDL3_K2" and lot_a[0]["recipe"] == "RDL3_K2"
    p = collect.parse_dt
    # 장 시작 ~ 다음 장 시작 · 멈춘 90분 간격과 마지막 장은 중앙 간격(12분)
    assert [(p(r["wafer_end_time"]) - p(r["wafer_start_time"])).seconds // 60 for r in lot_b] == [12, 12, 12, 12]
    assert p(lot_b[0]["batch_start"]) == dt.datetime(2026, 10, 5, 8, 0) and p(lot_b[0]["batch_end"]) == dt.datetime(2026, 10, 5, 10, 6)
    assert len({r["report"] for r in lot_a}) == 1 and lot_a[0]["report"].startswith("KLA:LOTA@1:")
    m = {d["name"]: d for d in dev_meta}["K1"]
    assert m["kind"] == "kla" and m["found"] == 11 and m.get("read_n") == 11 and stats["kla_pending"] == 1
    # 두 번째 수집: 새 Wafer 만(없음) — 결과 파일이 생긴 장 하나만 읽는다
    w5 = next((Path(m["note"]) / "2026-10-05" / "LOTB@2").glob("*_5"))
    (w5 / "r").write_text(klarf("LOTB@2", "W05", 5, dt.datetime(2026, 10, 5, 8, 0), 0), encoding="utf-8")
    stats2: dict = {}
    rows2, meta2, _ = collect.collect(cfg, stats=stats2)
    m2 = {d["name"]: d for d in meta2}["K1"]
    assert m2.get("read_n") == 1 and m2["kept"] == 10 and stats2["kla_pending"] == 0   # 캐시 10장은 그대로, 결과가 생긴 1장만
    assert len([r for r in rows2 if r["device"] == "K1"]) == 11
    # HTML 에도 들어가고, 캐시만으로 다시 만들어도 같다
    path = collect.write_html(cfg, rows2, meta2, [], 0.0, collect_log=stats2.get("log"))
    emb_rows, meta = sample_rows.unfold(sample_rows.embedded(open(path, encoding="utf-8").read()))
    assert sum(1 for r in emb_rows if r["device"] == "K1") == 11
    again = collect.html_from_cache(cfg)
    rows3, _ = sample_rows.unfold(sample_rows.embedded(open(again, encoding="utf-8").read()))
    assert sorted(json.dumps(r, sort_keys=True) for r in rows3 if r["device"] == "K1") == \
           sorted(json.dumps(r, sort_keys=True) for r in emb_rows if r["device"] == "K1")


def test_kla_outside_scope_is_never_touched(tmp_path, kla_nas, monkeypatch):
    _nas, csv_path = kla_nas
    cfg = make_cfg(tmp_path, csv_path, scope_devices=["AOI-9"])
    touched = []
    real = kla.list_dates
    monkeypatch.setattr(kla, "list_dates", lambda root: touched.append(root) or real(root))
    rows, dev_meta, _ = collect.collect(cfg)
    assert touched == [] and not any(r["device"] == "K1" for r in rows)


def test_existing_devices_csv_gets_the_eight_kla_rows_once(tmp_path):
    p = tmp_path / "devices.csv"
    p.write_text("장비명,NAS경로,폴더,사용,메모\nAOI-1,X:\\,AOI-1,Y,\n", encoding="utf-8-sig")
    assert devices.ensure_kla_rows(p) is True
    names = [r["name"] for r in devices.read_devices_csv(p)]
    assert names == ["AOI-1", "K1", "K2", "K3", "K4", "K5", "K6", "4F-K1", "4F-K2"]
    assert devices.ensure_kla_rows(p) is False                               # 하나라도 있으면 건드리지 않는다
    assert {r["root"] for r in devices.read_devices_csv(p) if r["name"] == "K2"} == {"G:\\"}
