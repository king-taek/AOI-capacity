"""결과 화면의 견고성(11/25 점검 JS-01 · JS-05 · JS-06): 시계가 틀린 행 · 사람이 친 특수 글자가 화면 숫자와 열기를 망치지 않는다.
모델은 Node 하네스(js_harness.js)로 실제로 돌린다 — Node 가 없으면 skip. 네트워크·NAS 없음."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from aoi_capacity import collect
from test_dashboard_js import DAY, NODE, meta, run, w

pytestmark = pytest.mark.skipif(not NODE, reason="node 가 없는 환경")


def _range(m, frm, to):
    return {**m, "range": {"from": frm, "to": to, "explicit": True}}


def test_a_row_from_years_ago_neither_changes_the_period_nor_loses_its_rescan_role():
    """JS-06: 분 단위 축은 기간 첫날 − 1일 무렵부터 — 2015년 행 하나가 장비마다 수년치 배열을 만들지 않고, 기간 안 값은 그대로.
    옛 행은 Rescan 판단(D63 — 앞선 시도가 PASS)에는 계속 쓴다."""
    base = [w("AOI-1", "W1", "08:00", "08:30", lot="LOT-A"), w("AOI-1", "W2", "09:00", "09:40", lot="LOT-B"),
            w("AOI-2", "W3", "23:00", "23:50", lot="LOT-C", day="2026-09-17"),
            w("AOI-2", "W4", "10:00", "10:20", lot="LOT-D", status="Scan 2D Error.")]
    mt = _range(meta("AOI-1", "AOI-2"), "2026-09-17", DAY)
    old_pass = w("AOI-1", "W2", "08:00", "08:30", lot="LOT-B", day="2015-01-05", report="J1_6321_LOT-B_5-Jan-15_(00.00.00)_BatchReport.htm")
    clock_bug = w("AOI-2", "X9", "03:00", "03:10", lot="LOT-Z", day="2001-03-04", report="J1_6321_LOT-Z_4-Mar-01_(00.00.00)_BatchReport.htm")
    a = run(base, mt)
    b = run(base + [old_pass, clock_bug], mt)
    assert a["days"] == b["days"] == ["2026-09-17", DAY]
    for dy in a["days"]:
        for dv in ("AOI-1", "AOI-2"):
            x, y = a["detail"][dy].get(dv), b["detail"][dy].get(dv)
            if dv == "AOI-1" and dy == DAY:
                assert x["r"] == 70 and x["d"] == 0                 # 옛 행이 없으면 둘 다 Scan
                assert y["r"] == 30 and y["d"] == 40                # 2015년의 PASS 가 앞선 시도 → W2 는 Rescan(D63) — 옛 행은 판단에 쓰인다
                continue
            assert x == y, (dy, dv)


def test_rows_dated_after_the_collection_do_not_stretch_todays_denominator():
    """JS-01: 수집 시각 + 1일보다 늦은 행은 오늘 분모(관측 종료, D57)에 넣지 않고 세어서 알린다 — 지우지는 않는다."""
    base = [w("AOI-1", "W1", "08:00", "08:29")]
    future = [w("AOI-2", f"F{i}", "10:00", "10:30", lot="LOT-F", day="2026-09-20") for i in range(3)]
    a = run(base, meta("AOI-1", "AOI-2"))
    b = run(base + future, meta("AOI-1", "AOI-2"))
    assert a["detail"][DAY]["AOI-1"]["den"] == b["detail"][DAY]["AOI-1"]["den"] == 8 * 60 + 29
    assert b["futureRows"] == 3 and a["futureRows"] == 0
    assert "2026-09-20" in b["days"]                                # 행은 남는다(Error · 이력이 조용히 사라지지 않게)


def test_default_html_period_ends_on_the_collection_day_even_with_a_future_row(tmp_path):
    """JS-01: 기본 HTML(최근 html_days 일)은 '가진 데이터의 끝날' 과 '수집한 날' 중 이른 날부터 거꾸로 센다 — 미래 날짜 행 하나가 기간을 통째로 미래로 밀지 않는다.
    미래 행 자체는 지우지 않는다(화면 바닥글이 세어 알린다)."""
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(tmp_path), "cache_file": str(tmp_path / "c.json"), "html_days": 30, "scope_devices": ["*"]})
    today = time.strftime("%Y-%m-%d")
    y, mo, d = today.split("-")
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(mo) - 1]
    row = {c: "" for c in collect.OUT_COLS}
    ok = {**row, "device": "AOI-1", "job": "J1", "lot": "L1", "wafer_id": "W1", "status": "Pass", "report": "R1.htm",
          "wafer_start_time": f"{int(d)}-{mon}-{y[2:]} 08:00:00 AM", "wafer_end_time": f"{int(d)}-{mon}-{y[2:]} 08:30:00 AM",
          "batch_start": f"{int(d)}-{mon}-{y[2:]} 08:00:00 AM", "batch_end": f"{int(d)}-{mon}-{y[2:]} 08:30:00 AM"}
    bad = {**ok, "device": "AOI-2", "wafer_id": "W2", "report": "R2.htm", "wafer_start_time": "5-Jan-29 08:00:00 AM",
           "wafer_end_time": "5-Jan-29 08:30:00 AM", "batch_start": "5-Jan-29 08:00:00 AM", "batch_end": "5-Jan-29 08:30:00 AM"}
    p = collect.write_html(cfg, [ok, bad], [{"name": "AOI-1"}, {"name": "AOI-2"}], [], time.time(), mode="test")
    s = Path(p).read_text(encoding="utf-8")
    i = s.index('id="embedded">') + len('id="embedded">')
    emb = json.loads(s[i:s.index("</script>", i)])
    assert emb["meta"]["range"]["from"] <= today
    assert len(emb["rows"]) == 2                                    # 오늘 행이 기간 안에 남는다(예전엔 2029 기준으로 잘려 미래 행 하나만 남았다)


def test_embedded_json_hides_every_angle_bracket_so_people_typed_text_cannot_swallow_the_script(tmp_path):
    """JS-05: Lot · Job · 상태 같은 사람이 친 글자에 '<!--<script' 가 들어가면 '</' 만 바꾸던 예전 방식은 HTML 파서를 '이중 이스케이프' 상태로 넣어
    #embedded 가 닫히지 않았다(파일이 영영 열리지 않음). '<' 를 통째로 \\u003c 로 — JSON 으로는 같은 글자다. 화면의 사본 저장도 같은 규칙."""
    cfg = dict(collect.DEFAULT_CONFIG)
    cfg.update({"output_dir": str(tmp_path), "cache_file": str(tmp_path / "c.json"), "html_days": 0, "scope_devices": ["*"]})
    nasty = "<!--<script>x</script><img src=x onerror=1>"
    row = {**{c: "" for c in collect.OUT_COLS}, "device": "AOI-1", "job": nasty, "lot": nasty, "wafer_id": "W1", "status": "Pass", "report": "R1.htm",
           "wafer_start_time": "18-Sep-26 08:00:00 AM", "wafer_end_time": "18-Sep-26 08:30:00 AM"}
    p = collect.write_html(cfg, [row], [{"name": "AOI-1"}], [], time.time(), mode="test")
    s = Path(p).read_text(encoding="utf-8")
    i = s.index('id="embedded">') + len('id="embedded">')
    body = s[i:s.index("</script>", i)]
    assert "<" not in body
    emb = json.loads(body)
    assert nasty in emb["pool"]
    tpl = (Path(collect.__file__).parent / "ui" / "assets" / "template.html").read_text(encoding="utf-8")
    assert 'JSON.stringify(emb).replace(/</g,"\\\\u003c")' in tpl           # 사본 저장(saveHtml)도 '<' 를 통째로


def test_screen_keeps_working_when_one_tab_fails_and_says_why_it_is_empty():
    """JS-03 · JS-04 · JS-11 · JS-13(11/25) 의 자리 — 브라우저 확인은 Chromium 으로 따로 했다(탭 하나가 던지면 그 자리에 안내, 다른 탭 계속).
    여기서는 코드가 남아 있는지만 본다."""
    tpl = (Path(collect.__file__).parent / "ui" / "assets" / "template.html").read_text(encoding="utf-8")
    assert "const prevH=H;H=[];" in tpl and "}catch(e){H=prevH;throw e;}" in tpl and 'safeHtml(()=>V==="home"' in tpl   # JS-03
    assert ".homelist .rowbtn span:has(>.st)" in tpl                                                                       # JS-04
    assert "이 브라우저에는 저장할 수 없습니다" in tpl and "return true;}catch(e){_rgNoSave=true;return false;}" in tpl        # JS-11
    assert "개를 모두 읽지 못했습니다(시각 형식)" in tpl and "장비 정보가 없는 파일입니다" in tpl and '${V==null?" disabled":""}' in tpl   # JS-13
