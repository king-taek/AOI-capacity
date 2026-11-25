"""'스캔을 어디에 했니?' 의 레시피 칸 · Slot 지도 검증(11/25 현택: "5x · 10x · 20x 제대로 작성되나 · slot map 코드 제대로 되어 있나").

- 레시피: RDL 멀티 스캔 Report 에서 INI 를 못 찾은 장은 Report 표의 첫 레시피(`x20`)만 남아 한 검사에 'x20 · x20|x5' 로 적혔다
  (실데이터 RDL Report 4,407개 중 804개) — 같은 Report 의 멀티 값으로 읽는다(`lotRcpOf`, 표시 · 재시도/재스캔 판정만).
- 슬롯: 한 검사 안에서 같은 슬롯에 다른 Wafer 가 둘 이상이면(옛 장비의 ActiveSlot 이 장마다 바뀌지 않음) 그 검사는 지도 기준에서 뺀다(`lotSlotsOk`)."""
from __future__ import annotations

from test_dashboard_js import _lot_keys, _lot_screen, w

A = "TB500_RDL3 - Multi_Setup1_GVB-RDL3_18-Sep-26_(01.00.00)_BatchReport.htm"
B = "TB500_RDL3 - Multi_Setup1_GVB-RDL3_18-Sep-26_(05.00.00)_BatchReport.htm"
JOB = "TB500_RDL3 - Multi"
IDS = [f"RCPW{i:05d}X" for i in range(3)]


def _rows():
    rows = [w("AOI-1", IDS[0], "00:10", "00:20", lot="GVB-RDL3", job=JOB, report=A) | {"recipe": "x20|x5", "scan_mode": "MULTI"},
            w("AOI-1", IDS[1], "00:30", "00:40", lot="GVB-RDL3", job=JOB, report=A) | {"recipe": "x20|x5", "scan_mode": "MULTI"},
            w("AOI-1", IDS[2], None, None, lot="GVB-RDL3", job=JOB, report=A, bs="00:05", be="01:00") | {"recipe": "x20"}]   # INI 없음 — 표의 첫 레시피만
    rows += [w("AOI-2", i, f"0{4 + n}:10", f"0{4 + n}:20", lot="GVB-RDL3", job=JOB, report=B) | {"recipe": "x20", "scan_mode": "SINGLE"} for n, i in enumerate(IDS)]
    return rows


def test_recipe_column_reads_the_reports_multi_recipe_for_rows_without_ini():
    rows = _rows()
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    assert "x20 · x20|x5" not in out and "x20|x5 · x20" not in out and "x20|x5" in out
    assert out.count(">x20<") >= 1                                                  # 단일 Report 는 그대로 x20


def test_slot_map_skips_an_inspection_whose_slots_collide():
    rows = _rows()
    for r in rows:
        if r["report"] == A:
            r["slot_no"] = "13" if r["ini_match"] == "EXACT" else ""             # 옛 장비 — 두 장이 같은 #13
    for n, r in enumerate(x for x in rows if x["report"] == B):
        r["slot_no"] = str(n + 1) if n < 2 else ""                                # 슬롯을 아는 장 수가 같으면 앞 검사가 기준이 되던 자리
    (k,) = _lot_keys(_lot_screen(rows))
    out = _lot_screen(rows, k)
    assert '<span class="sn">#13</span>' not in out and '<span class="sn">#1</span>' in out and '<span class="sn">#2</span>' in out
