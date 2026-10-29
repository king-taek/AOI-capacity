"""카세트 슬롯 번호 `slot_no`(ROW_SCHEMA_VERSION 10, 10/24 — 사용자: LOT 추적에 Slot No 와 Wafer ID 를 AOI 레시피 검증과 같은 방식으로).

- Camtek: WaferInfo.ini `[AutoCycleInfo] ActiveSlot`(이미 여는 파일 — 열기 추가 0). EXACT 행만, STALE · 없음은 빈 값(지어내지 않는다).
- KLA: 결과 파일 머리 `Slot N;`, 없으면 Wafer 폴더 이름 끝(`…_6`).
- 화면: LOT 추적의 검사 순서 아래 'Slot No · Wafer ID' 카세트 지도(기준 검사 하나) · Wafer × 검사 줄 이름 앞 #번호 · 슬롯 순서."""
from __future__ import annotations

from aoi_capacity import collect, kla
from test_recipes_info import _rows, _wafer_dir
from test_dashboard_js import _lot_keys, _lot_screen, meta, screen, w


def test_slot_no_is_a_row_column():
    assert collect.ROW_SCHEMA_VERSION == 10 and "slot_no" in collect.OUT_COLS and "slot_no" in collect.POOLED_COLS


def test_collector_reads_active_slot_from_the_waferinfo_it_already_opens(tmp_path, fake_nas):
    nas, csv_path = fake_nas
    [r0] = _rows(tmp_path, csv_path)
    assert r0["ini_match"] == "EXACT" and r0["slot_no"] == ""                    # ActiveSlot 이 없으면 빈 값
    ini = _wafer_dir(nas) / "WaferInfo.ini"
    ini.write_text(ini.read_text(encoding="utf-8").replace("Operator=MAINT\n", "Operator=MAINT\nActiveSlot=06\n"), encoding="utf-8")
    [r] = _rows(tmp_path / "again", csv_path)
    assert r["ini_match"] == "EXACT" and r["slot_no"] == "6"


def test_kla_slot_from_header_then_folder_name():
    assert kla._slot_no({"slot": "10", "dir_slot": 4}) == "10"
    assert kla._slot_no({"slot": "", "dir_slot": 4}) == "4"
    assert kla._slot_no({"slot": "x"}) == ""


def _slot_rows():
    A = "J1_6321_SLT-1_18-Sep-26_(01.00.00)_BatchReport.htm"
    B = "J1_6321_SLT-1 RE_18-Sep-26_(03.00.00)_BatchReport.htm"
    ids = [f"SLOTW{i:05d}X" for i in range(3)]
    rows = [w("AOI-1", i, "00:10", "00:20", lot="SLT-1", report=A) | {"slot_no": str(3 - n)} for n, i in enumerate(ids)]
    rows += [w("AOI-2", ids[2], "02:10", "02:20", lot="SLT-1 RE", report=B) | {"slot_no": "1"}]
    return rows


def test_lot_tab_shows_slot_map_below_the_inspection_order():
    rows = _slot_rows()
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    sec = out.split("Slot No · Wafer ID")[1]
    assert out.index("검사 순서") < out.index("Slot No · Wafer ID") < out.index("Wafer × 검사")
    assert "검사 #1 기준" in sec                                                # 슬롯을 아는 Wafer 가 가장 많은 검사
    assert '<b class="num">#1</b><span class="mono">SLOTW00002X</span>' in sec and '<b class="num">#3</b><span class="mono">SLOTW00000X</span>' in sec
    mx = out.split("Wafer × 검사")[1]
    assert mx.index("SLOTW00002X") < mx.index("SLOTW00001X") < mx.index("SLOTW00000X")   # 격자 줄은 슬롯 순서
    assert '<span class="sn">#1</span>SLOTW00002X' in mx


def test_publish_lot_tab_shows_the_wafer_grid_like_the_full_screen():
    """10/29 사용자: 배포판의 Slot 세로 목록(25→1, 빈 칸 · 경고)은 빼고 원본과 같은 Wafer × 검사 격자로."""
    rows = _slot_rows()
    (k,) = _lot_keys(_lot_screen(rows))
    (out,) = screen(rows, meta("AOI-1", "AOI-2") | {"lot_only": True}, [["lotHtml"]], state={"view": "lot", "lotPick": {"k": "lot", "v": k}})
    assert "Slot No · Wafer ID" not in out and "lotslots" not in out and "정확하지 않을 수 있습니다" not in out
    mx = out.split("Wafer × 검사")[1]
    assert mx.index("SLOTW00002X") < mx.index("SLOTW00001X") < mx.index("SLOTW00000X")   # 줄 이름 앞 #슬롯 · 슬롯 순서는 원본과 같다
    assert '<span class="sn">#1</span>SLOTW00002X' in mx


def test_lot_tab_without_slots_says_how_to_fill_them():
    rows = [r | {"slot_no": ""} for r in _slot_rows()]
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    assert "슬롯 번호가 아직 없습니다" in out and "lotslots" in out


def test_fill_gaps_fills_slot_no_from_wafer_ini_only_when_folder_not_rewritten(tmp_path, fake_nas):
    """10/25 '옛 기간 빈칸 채우기' 의 슬롯 번호 줄 — 빈 slot_no 를 Wafer 폴더의 WaferInfo.ini 한 장만 읽어 채운다.
    INI 의 WaferStartTime 이 행과 다르면(나중 검사가 덮어씀) 쓰지 않고, 해 본 Report 는 다시 열지 않는다."""
    import json
    from conftest import make_cfg
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    collect.collect(cfg)
    inis = [p for p in nas.rglob("WaferInfo.ini")]
    assert inis
    for ini in inis:
        t = ini.read_text(encoding="utf-8")
        ini.write_text(t.replace("Operator=MAINT\n", "Operator=MAINT\nActiveSlot=07\n"), encoding="utf-8")
    plan = collect.plan_run(cfg)
    assert plan.slot_missing > 0 and plan.slot_have == 0 and plan.etas["slot"][0] is not None
    st = collect.fill_gaps(cfg)
    assert st["slot"]["filled"] == plan.slot_missing and st["slot"]["empty"] == 0
    rows = [r for e in json.load(open(cfg["cache_file"], encoding="utf-8"))["reports"].values() for r in e["rows"] if r.get("ini_match") == "EXACT" and not r.get("kind")]
    assert rows and all(r["slot_no"] == "7" for r in rows)
    after = collect.plan_run(cfg)
    assert after.slot_missing == 0 and after.slot_have == len(rows)
    assert collect.fill_gaps(cfg)["slot"]["targets"] == 0                            # 두 번째는 할 일이 없다


def test_fill_gaps_leaves_slot_empty_when_ini_was_rewritten(tmp_path, fake_nas):
    import json
    from conftest import make_cfg
    nas, csv_path = fake_nas
    cfg = make_cfg(tmp_path, csv_path, collect_params=False)
    collect.collect(cfg)
    for ini in nas.rglob("WaferInfo.ini"):
        t = ini.read_text(encoding="utf-8")
        import re
        ini.write_text(re.sub(r"WaferStartTime=.*", "WaferStartTime=09/20/2026 01:00:00", t) + "\nActiveSlot=3\n", encoding="utf-8")
    st = collect.fill_gaps(cfg)
    assert st["slot"]["filled"] == 0 and st["slot"]["empty"] == st["slot"]["targets"] > 0
    assert collect.plan_run(cfg).slot_missing == 0
