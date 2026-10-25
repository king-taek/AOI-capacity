"""카세트 슬롯 번호 `slot_no`(ROW_SCHEMA_VERSION 10, 10/24 — 사용자: LOT 추적에 Slot No 와 Wafer ID 를 AOI 레시피 검증과 같은 방식으로).

- Camtek: WaferInfo.ini `[AutoCycleInfo] ActiveSlot`(이미 여는 파일 — 열기 추가 0). EXACT 행만, STALE · 없음은 빈 값(지어내지 않는다).
- KLA: 결과 파일 머리 `Slot N;`, 없으면 Wafer 폴더 이름 끝(`…_6`).
- 화면: LOT 추적의 검사 순서 아래 'Slot No · Wafer ID' 카세트 지도(기준 검사 하나) · Wafer × 검사 줄 이름 앞 #번호 · 슬롯 순서."""
from __future__ import annotations

from aoi_capacity import collect, kla
from test_recipes_info import _rows, _wafer_dir
from test_dashboard_js import _lot_keys, _lot_screen, w


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


def test_lot_tab_without_slots_says_how_to_fill_them():
    rows = [r | {"slot_no": ""} for r in _slot_rows()]
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    assert "슬롯 번호가 아직 없습니다" in out and "lotslots" in out
