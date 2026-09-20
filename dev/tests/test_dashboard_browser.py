"""결과 HTML 의 클릭 경로를 진짜 Chromium(Playwright)으로 실측한다 — S06(개선 계획 P4, 9/20).

문자열 검사(`test_template_contract.py`)와 Node 하네스(`test_dashboard_js.py`)는 화면이 **그려지는지**를 보지 못한다.
여기서는 작은 fixture 행을 template 에 박아 파일로 열고(바깥 요청 0건 — file:// 만), 실제로 눌러 본다:
가동률 → 장비 팝업(포커스 · inert · Tab 트랩 · ESC 복귀, D05) → Error 보기 → 유형 팝업 → 추이 → TB500 · Kendall(D59).
콘솔 오류·페이지 오류가 하나라도 있으면 실패.

마커 `browser` — CI 의 browser 잡이 `-m browser` 로 따로 돈다. Playwright(파이썬 패키지)나 Chromium 이 없으면 skip.
Chromium 은 기본 설치 → `PLAYWRIGHT_CHROMIUM_EXECUTABLE` → `/opt/pw-browsers/chromium-*/chrome-linux/chrome` 순으로 찾는다.
네트워크·pip 은 쓰지 않는다.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.browser

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "aoi_capacity" / "ui" / "assets" / "template.html"
DAY = "2026-09-18"


def _ts(hhmm: str, day: str = DAY) -> str:
    """'08:00' → '18-Sep-26 08:00:00 AM' (실장비 Report 표기 — 모델의 P() 가 읽는 형식)."""
    y, m, d = day.split("-")
    mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m) - 1]
    h, mi = map(int, hhmm.split(":"))
    return f"{int(d)}-{mon}-{y[2:]} {(h % 12 or 12):02d}:{mi:02d}:00 {'AM' if h < 12 else 'PM'}"


def _row(dev, wafer, s=None, e=None, *, lot="LOT-A", status="Pass", job="J1", report=None, bs=None, be=None):
    rep = report or f"{job}_6321_{lot}_18-Sep-26_(00.00.00)_BatchReport.htm"
    return {"device": dev, "kind": "", "job": job, "setup": "6321", "lot": lot, "wafer_id": wafer, "status": status,
            "wafer_start_time": _ts(s) if s else "", "wafer_end_time": _ts(e) if e else "",
            "batch_start": _ts(bs) if bs else (_ts(s) if s else ""), "batch_end": _ts(be) if be else (_ts(e) if e else ""),
            "report": rep, "ini_match": "EXACT" if s else "NOT_FOUND", "scan_type": "", "recipe": "", "data_issue": "",
            "faults": "3" if status == "Pass" else ""}


def _fixture_rows():
    rows = []
    # AOI-1: 정상 스캔 두 Lot + Error 하나(원인 ALIGN) + INI 없는 Pass 행(배치 창 추정)
    for i in range(6):
        rows.append(_row("AOI-1", f"W{i}", f"08:{i*5:02d}", f"08:{i*5+4:02d}", lot="LOT-A", job="R_TB500_LIVE_PI2_COPY"))
    rows.append(_row("AOI-1", "E1", "09:00", "09:03", lot="LOT-B", status="Alignment Error.", job="R_TB500_LIVE_PI2_COPY"))
    for i in range(4):
        rows.append(_row("AOI-1", f"X{i}", f"10:{i*6:02d}", f"10:{i*6+5:02d}", lot="LOT-C", job="R_KENDALL_A0_FS"))
    rows.append(_row("AOI-1", "N1", lot="LOT-D", bs="11:00", be="11:30", job="J-OTHER"))
    # AOI-2: Test Lot + 스캔
    for i in range(3):
        rows.append(_row("AOI-2", f"T{i}", f"07:{i*10:02d}", f"07:{i*10+8:02d}", lot="TEST-LOT"))
    for i in range(3):
        rows.append(_row("AOI-2", f"S{i}", f"12:{i*10:02d}", f"12:{i*10+9:02d}", lot="LOT-E"))
    return rows


def _meta():
    return {"generated": f"{DAY} 13:00", "generated_iso": f"{DAY}T13:00:00", "mode": "auto",
            "scope": {"restricted": True, "devices": ["AOI-1", "AOI-2", "AOI-3"]},
            "devices": [{"name": d, "note": f"X:\\{d}", "report_dir": "Report", "status": "ok"} for d in ("AOI-1", "AOI-2", "AOI-3")]}


def _build_html(tmp_path: Path) -> Path:
    rows = _fixture_rows()
    cols = list(rows[0].keys())
    emb = {"cols": cols, "pooled": [], "pool": None, "rows": [[r[c] for c in cols] for r in rows], "meta": _meta()}
    tpl = TEMPLATE.read_text(encoding="utf-8")
    assert "__DATA__" in tpl
    out = tmp_path / "AOI_capacity.html"
    out.write_text(tpl.replace("__DATA__", json.dumps(emb, ensure_ascii=False).replace("</", "<\\/"), 1), encoding="utf-8")
    return out


def _launch(pw):
    """Chromium 을 찾는다 — 기본 설치 → 환경변수 → /opt/pw-browsers. 다 실패하면 None."""
    candidates = [None, os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None]
    candidates += sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"), reverse=True)
    last = None
    for exe in candidates:
        if exe is not None and not Path(exe).is_file():
            continue
        try:
            return pw.chromium.launch(executable_path=exe) if exe else pw.chromium.launch()
        except Exception as e:  # noqa: BLE001 — 설치 상태에 따라 예외 종류가 다르다
            last = e
    pytest.skip(f"Chromium 을 띄우지 못함: {last}")


@pytest.fixture(scope="module")
def page_factory():
    sync_playwright = pytest.importorskip("playwright.sync_api").sync_playwright
    with sync_playwright() as pw:
        browser = _launch(pw)
        try:
            yield browser
        finally:
            browser.close()


@pytest.fixture
def page(page_factory, tmp_path):
    html = _build_html(tmp_path)
    ctx = page_factory.new_context(viewport={"width": 1280, "height": 800})
    pg = ctx.new_page()
    errors: list = []
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
    requests: list = []
    pg.on("request", lambda r: requests.append(r.url) if not r.url.startswith("file:") else None)
    pg.goto(html.as_uri())
    pg.wait_for_selector("main")
    yield pg, errors, requests
    ctx.close()


def _active(pg):
    return pg.evaluate("(() => { const a = document.activeElement; return a ? [a.tagName, a.getAttribute('data-fk') || a.id || ''] : null; })()")


def test_home_renders_and_makes_no_external_request(page):
    pg, errors, requests = page
    text = pg.inner_text("main")
    assert "AOI-1" in text and "AOI-2" in text and "평균 가동률" in text
    assert "기록 없음 1대" in text                       # AOI-3 은 기록이 없다 — 평균에서 빼고 대수만(D06·D57)
    assert requests == [] and errors == []


def test_device_popup_focus_inert_tab_trap_and_escape_return(page):
    pg, errors, _ = page
    row = pg.locator('button.rowbtn[data-fk="dev:AOI-1"]')
    row.focus()
    pg.keyboard.press("Enter")
    pg.wait_for_selector('.dlg[data-dlg="dev"]')
    assert _active(pg) == ["H2", "dlg-dev-title"]                                   # 열리면 제목으로
    assert pg.evaluate("document.querySelector('#app>main').inert") is True         # 아래 화면은 막힌다
    dlg = pg.locator('.dlg[data-dlg="dev"]')
    assert dlg.get_attribute("aria-labelledby") == "dlg-dev-title"
    for _ in range(25):                                                              # Tab 은 팝업 안에서만 돈다
        pg.keyboard.press("Tab")
        assert pg.evaluate("(() => { const d = document.querySelector('.dlg[data-dlg=\"dev\"]'); return d.contains(document.activeElement); })()")
    assert "Wafer 12장 중 1장은 INI(시각 기록)가 없어" in dlg.inner_text()           # D56②·D58 안내(행 12 = Pass 10 + Error 1 + INI 없는 Pass 1)
    pg.locator("button.callout").first.click()
    pg.wait_for_selector(".sel")
    assert "Report 열기" in pg.locator(".sel").inner_text()
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="dev"]', state="detached")
    assert _active(pg) == ["BUTTON", "dev:AOI-1"]                                   # 닫히면 열었던 행으로
    assert pg.evaluate("document.querySelector('#app>main').inert") is False
    assert errors == []


def test_error_popup_type_popup_trend_and_report_tab(page):
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector("main")
    assert "Error 대기" in pg.inner_text("main")                                     # D11 지표 이름
    pg.locator("button.rowbtn").filter(has_text="ALIGN_ERROR").first.click()
    pg.wait_for_selector('.dlg[data-dlg="type"]')
    assert "ALIGN_ERROR" in pg.locator('.dlg[data-dlg="type"] h2').inner_text()
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="type"]', state="detached")
    pg.locator("button.rowbtn").filter(has_text="AOI-1").first.click()              # 장비별 → Error 상세 팝업
    pg.wait_for_selector('.dlg[data-dlg="err"]')
    err = pg.locator('.dlg[data-dlg="err"]').inner_text()
    assert "Error 대기" in err and "ALIGN_ERROR" in err and "Alignment Error." in err
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    pg.locator('button[data-fk="nav:trend"]').click()
    assert "날짜별 평균 가동률" in pg.inner_text("main")
    pg.locator('button[data-fk="nav:report"]').click()
    rpt = pg.inner_text("main")
    assert "TB500 · Kendall" in rpt and "개 Job 만 봅니다" in rpt                    # D59
    assert "평균 fault" in rpt and "수집 예정" not in rpt                             # D08
    assert pg.evaluate("[...document.querySelectorAll('main .panel')].some(p => p.style.overflowX === 'auto')")   # D10
    assert errors == []


def test_narrow_viewport_has_no_horizontal_page_scroll(page):
    pg, errors, _ = page
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.locator('button[data-fk="nav:report"]').click()
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    assert errors == []
