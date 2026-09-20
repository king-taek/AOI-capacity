"""결과 HTML 의 클릭 경로를 진짜 Chromium(Playwright)으로 실측한다 — S06(개선 계획 P4, 9/20).

문자열 검사(`test_template_contract.py`)와 Node 하네스(`test_dashboard_js.py`)는 화면이 **그려지는지**를 보지 못한다.
여기서는 작은 fixture 행을 template 에 박아 파일로 열고(바깥 요청 0건 — file:// 만), 실제로 눌러 본다:
가동률(장비 순서) → 장비 팝업(포커스 · inert · Tab 트랩 · ESC 복귀, D05) → Error 보기 → 유형 팝업 → 추이 → TB500 · Kendall(D59) → 사본 저장(내려받은 파일의 열·풀 구조).
데이터는 수집기의 `collect._embed_rows` 로 접어 넣는다 — 제품이 만드는 HTML 과 같은 계약이다.
콘솔 오류·페이지 오류가 하나라도 있으면 실패.

마커 `browser` — CI 의 browser 잡이 `-m browser` 로 따로 돈다. Playwright(파이썬 패키지)나 Chromium 이 없으면 skip.
Chromium 은 기본 설치 → `PLAYWRIGHT_CHROMIUM_EXECUTABLE` → `/opt/pw-browsers/chromium-*/chrome-linux/chrome` 순으로 찾는다.
네트워크·pip 은 쓰지 않는다.
"""
from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path

import pytest

import sample_rows
from aoi_capacity import collect

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


def _row(dev, wafer, s=None, e=None, *, lot="LOT-A", status="Pass", job="J1", report=None, bs=None, be=None, day=DAY):
    rep = report or f"{job}_6321_{lot}_{int(day[8:])}-Sep-26_(00.00.00)_BatchReport.htm"
    return {"device": dev, "kind": "", "job": job, "setup": "6321", "lot": lot, "wafer_id": wafer, "status": status,
            "wafer_start_time": _ts(s, day) if s else "", "wafer_end_time": _ts(e, day) if e else "",
            "batch_start": _ts(bs, day) if bs else (_ts(s, day) if s else ""), "batch_end": _ts(be, day) if be else (_ts(e, day) if e else ""),
            "report": rep, "ini_match": "EXACT" if s else "NOT_FOUND", "scan_type": "", "recipe": "", "data_issue": "",
            "faults": "3" if status == "Pass" else ""}


def _fixture_rows():
    rows = []
    # AOI-1: 정상 스캔 두 Lot + Error 하나(원인 ALIGN) + INI 없는 Pass 행(배치 창 추정)
    for i in range(6):
        rows.append(_row("AOI-1", f"W{i}", f"08:{i*5:02d}", f"08:{i*5+4:02d}", lot="LOT-A", job="R_TB500_LIVE_PI2"))
    rows.append(_row("AOI-1", "E1", "09:00", "09:03", lot="LOT-B", status="Alignment Error.", job="R_TB500_LIVE_PI2"))
    for i in range(4):
        rows.append(_row("AOI-1", f"X{i}", f"10:{i*6:02d}", f"10:{i*6+5:02d}", lot="LOT-C", job="R_KENDALL_A0_FS"))
    rows.append(_row("AOI-1", "N1", lot="LOT-D", bs="11:00", be="11:30", job="J-OTHER"))
    # AOI-2: Test Lot + 스캔
    for i in range(3):
        rows.append(_row("AOI-2", f"T{i}", f"07:{i*10:02d}", f"07:{i*10+8:02d}", lot="TEST-LOT"))
    for i in range(3):
        rows.append(_row("AOI-2", f"S{i}", f"12:{i*10:02d}", f"12:{i*10+9:02d}", lot="LOT-E"))
    # AOI-10: 홈 목록이 번호순(AOI-2 뒤)인지 보기 위한 한 Lot — 사전순이면 AOI-1 다음에 온다
    for i in range(2):
        rows.append(_row("AOI-10", f"K{i}", f"09:{i*10:02d}", f"09:{i*10+8:02d}", lot="LOT-K"))
    # 전날(9/17): AOI-1 에 Error 하나 — Error 탭의 '최근 7일' 이 이틀이 되어 기간 팝업(여러 날)을 검사할 수 있다
    rows.append(_row("AOI-1", "P1", "14:00", "14:03", lot="LOT-P", status="Scan Error.", job="R_TB500_LIVE_PI2", day="2026-09-17"))
    for i in range(3):
        rows.append(_row("AOI-1", f"Q{i}", f"15:{i*5:02d}", f"15:{i*5+4:02d}", lot="LOT-Q", job="R_TB500_LIVE_PI2", day="2026-09-17"))
    return rows


def _meta():
    return {"generated": f"{DAY} 13:00", "generated_iso": f"{DAY}T13:00:00", "mode": "auto",
            "scope": {"restricted": True, "devices": ["AOI-1", "AOI-2", "AOI-3", "AOI-10"]},
            "devices": [{"name": d, "note": f"X:\\{d}", "report_dir": "Report", "status": "ok"} for d in ("AOI-1", "AOI-2", "AOI-3", "AOI-10")]}


def _embedded() -> dict:
    emb = collect._embed_rows(_fixture_rows())          # 제품과 같은 접기(24열 · 문자열 풀)
    emb["meta"] = _meta()
    return emb


def _build_html(tmp_path: Path) -> Path:
    emb = _embedded()
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
    pg.wait_for_selector('main[data-key^="view:"]')          # 로더(main) 가 먼저 그려지고 다음 틱에 화면이 온다
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
    assert pg.evaluate("document.querySelector('#app>.stage').inert") is True       # 아래 화면은 막힌다
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
    assert pg.evaluate("document.querySelector('#app>.stage').inert") is False
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
    pg.locator("button.rowbtn").filter(has_text=re.compile(r"AOI-1(?!\d)")).first.click()   # 장비별 → Error 상세 팝업(AOI-10 이 아니라)
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


def test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns(page, tmp_path):
    """홈 목록은 devices.sort_key 순(AOI-1 · AOI-2 · AOI-3 · AOI-10 — 사전순이면 AOI-10 이 AOI-2 앞), '사본 저장' 이 내려준 HTML 은
    수집기가 준 열·풀 구조 그대로이고 펼치면 같은 행이다(saveHtml, D16 이전부터의 계약)."""
    pg, errors, requests = page
    order = pg.evaluate("[...document.querySelectorAll('main button.rowbtn[data-fk^=\"dev:\"]')].map(b => b.dataset.fk)")
    assert order == ["dev:AOI-1", "dev:AOI-2", "dev:AOI-3", "dev:AOI-10"]   # 번호순 — 사전순이면 AOI-10 이 AOI-2 앞에 온다
    with pg.expect_download() as dl:
        pg.get_by_role("button", name="사본 저장").click()
    saved = Path(dl.value.path()).read_text(encoding="utf-8")
    emb0 = _embedded()
    emb1 = sample_rows.embedded(saved)
    assert emb1["cols"] == emb0["cols"] and set(emb1["pooled"]) == set(emb0["pooled"])
    rows0, _ = sample_rows.unfold(emb0)
    rows1, meta1 = sample_rows.unfold(emb1)
    assert rows1 == rows0
    assert meta1["mode"] == "saved" and meta1.get("saved_iso") and meta1["generated_iso"] == emb0["meta"]["generated_iso"]
    assert "__DATA__" not in saved and requests == [] and errors == []


def test_render_morphs_in_place_instead_of_rebuilding(page):
    """깜박임의 근원(#app 통째 innerHTML) 제거 — 상태가 바뀌어도 main·패널·바뀌지 않은 행 노드는 같은 객체로 남는다."""
    pg, errors, _ = page
    pg.evaluate("window.__m = document.querySelector('main'); window.__p = document.querySelector('main .panel'); window.__r = document.querySelector('button.rowbtn[data-fk=\"dev:AOI-2\"]')")
    pg.locator('button[data-fk="seg:가동률 낮은 순"]').click()
    pg.wait_for_selector('button[data-fk="seg:가동률 낮은 순"].on')
    assert pg.evaluate("document.querySelector('main') === window.__m && document.querySelector('main .panel') === window.__p")
    assert pg.evaluate("document.querySelector('button.rowbtn[data-fk=\"dev:AOI-2\"]') === window.__r")     # 순서만 바뀐 행도 같은 노드(FLIP 대상)
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert pg.evaluate("document.querySelector('main[data-key=\"view:errors\"]') !== window.__m")             # 뷰가 바뀌면 main 은 새 노드
    assert errors == []


def test_error_tab_period_popup_filters_and_no_total_link(page):
    """Error 탭: 7일을 고른 채 장비를 누르면 그 기간 그대로(여러 날) · 유형 필터 · '전체 기간 합계로' 없음."""
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert "전체 기간 합계로" not in pg.inner_text("main")
    pg.locator('button[data-fk="seg:최근 7일"]').click()
    pg.wait_for_selector('button[data-fk="seg:최근 7일"].on')
    pg.locator('main button.rowbtn[data-key="dev:AOI-1"]').click()
    pg.wait_for_selector('.dlg[data-dlg="err"]')
    txt = pg.locator('.dlg[data-dlg="err"]').inner_text()
    assert "· 2일" in txt and "하루씩 보기" in txt and "날짜별" in txt and "09/17" in txt      # 9/17 + 9/18 두 날
    assert "SCAN_ERROR" in txt and "ALIGN_ERROR" in txt                                      # 두 날의 Error 가 함께
    pg.locator('.dlg[data-dlg="err"] button', has_text="하루씩 보기").click()
    pg.wait_for_selector('.dlg[data-dlg="err"] h3', state="attached")
    assert "언제 났나" in pg.locator('.dlg[data-dlg="err"]').inner_text()
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    # 유형 필터: 첫 유형의 깔때기 → 카드 라벨·칩, 목록은 그 유형만
    pg.locator('main .row2[data-key^="type:"] .fbtn').first.click()
    pg.wait_for_selector('main .fchip')
    assert "Error (필터)" in pg.inner_text("main") and pg.locator('main .row2[data-key^="type:"]').count() == 1
    pg.locator('main .fchip').first.click()
    pg.wait_for_selector('main .fchip', state="detached")
    assert errors == []


def test_popups_stack_behind_each_other_and_escape_closes_the_top(page):
    """팝업이 겹치면 아래 팝업은 닫히지 않고 뒤로 물러난다(behind · inert) — ESC 는 맨 위만 닫는다."""
    pg, errors, _ = page
    pg.locator('button.rowbtn[data-fk="dev:AOI-1"]').click()
    pg.wait_for_selector('.dlg[data-dlg="dev"]')
    pg.locator('.dlg[data-dlg="dev"] button', has_text="Error 보기").click()
    pg.wait_for_selector('.dlg[data-dlg="err"]')
    st = pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving])')].map(o => o.dataset.key + ':' + (o.classList.contains('behind') ? 'behind' : 'top') + ':' + o.inert)")
    assert st == ["ov:dev:behind:true", "ov:err:top:false"]
    assert pg.evaluate("getComputedStyle(document.querySelector('.ov.behind .dlg')).transform") != "none"
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    assert pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving])')].map(o => o.dataset.key + ':' + o.classList.contains('behind'))") == ["ov:dev:false"]
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="dev"]', state="detached")
    assert errors == []


def test_report_tab_groups_and_sorts_by_column(page):
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:report"]').click()
    pg.wait_for_selector('main[data-key="view:report"]')
    groups = pg.evaluate("[...document.querySelectorAll('.grp')].map(g => g.firstChild.textContent)")
    assert groups == ["Kendall", "TB500"]
    order = pg.evaluate("[...document.querySelectorAll('[data-key^=\"job:\"]')].map(e => e.dataset.key.slice(4))")
    assert order == ["Kendall FS", "TB500 PI2"]                                          # 그룹 순서 · 이름순
    hdr = pg.locator('.thead button.th', has_text="배치")
    hdr.click()
    pg.wait_for_selector('.thead button.th[aria-sort="descending"]')
    hdr.click()
    pg.wait_for_selector('.thead button.th[aria-sort="ascending"]')
    assert "오름차순" in pg.inner_text("main")
    assert errors == []


def test_motion_hooks_lottie_countup_sweep_and_recede(page):
    """세 라이브러리의 자리: 브랜드의 Lottie 표식 · 'Error 없음' 의 Lottie 체크 · GSAP 카운트업(끝 값이 정확) · 막대 sweep(끝나면 clip-path 남지 않음) · 팝업 뒤 무대 물러남."""
    pg, errors, _ = page
    assert pg.locator('.brand .lt svg').count() == 1                                     # lottie 가 브랜드 표식을 그렸다
    pg.locator('button[data-fk="day:prev"]').click()                                     # 날짜를 바꾸면 카드 숫자가 이전 값에서 새 값으로
    pg.wait_for_selector('.daylab:has-text("9월 17일")')
    pg.wait_for_timeout(900)
    v = pg.locator('main .cards [data-count]').first
    assert v.inner_text() == f"{float(v.get_attribute('data-count')):.1f}"              # 카운트업이 끝나면 정확히 새 값
    assert pg.evaluate("[...document.querySelectorAll('[data-bar]')].every(e => !e.style.clipPath)")   # sweep 뒤 clip-path 정리
    pg.locator('button[data-fk="day:next"]').click()
    pg.wait_for_selector('.daylab:has-text("9월 18일")')
    pg.locator('button.rowbtn[data-fk="dev:AOI-2"]').click()                              # AOI-2 는 Error 가 없다
    pg.wait_for_selector('.dlg[data-dlg="dev"]')
    assert pg.evaluate("document.querySelector('#app>.stage').classList.contains('behind')")   # 팝업이 열리면 무대가 물러난다
    pg.locator('.dlg[data-dlg="dev"] button', has_text="Error 보기").click()
    pg.wait_for_selector('.dlg[data-dlg="err"] .lt-empty .lt svg')                       # Lottie 체크
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="dev"]', state="detached")
    assert pg.evaluate("!document.querySelector('#app>.stage').classList.contains('behind')")
    assert errors == []


def test_popup_deck_click_behind_brings_it_to_front_and_stackbar_lists_them(page):
    """팝업 위의 팝업: 뒤 카드는 새 카드의 왼쪽 뒤로 물러나고, scrim 의 그 자리를 누르거나 스택 바의 칩을 누르면 그 팝업이 앞으로 온다."""
    pg, errors, _ = page
    pg.locator('button.rowbtn[data-fk="dev:AOI-1"]').click()
    pg.wait_for_selector('.dlg[data-dlg="dev"]')
    pg.locator('.dlg[data-dlg="dev"] button', has_text="Error 보기").click()
    pg.wait_for_selector('.dlg[data-dlg="err"]')
    pg.wait_for_timeout(500)
    # 뒤 카드(dev)는 앞 카드보다 왼쪽에 있다
    lx = pg.evaluate("[document.querySelector('.ov.behind .dlg').getBoundingClientRect().left, document.querySelector('.ov:not(.behind) .dlg').getBoundingClientRect().left]")
    assert lx[0] < lx[1] - 40
    assert pg.evaluate("[...document.querySelectorAll('.stackbar .sb')].map(e => e.classList.contains('cur'))") == [False, True]
    # 스택 바의 첫 칩(장비 팝업) → 앞으로
    pg.locator('.stackbar button.sb').first.click()
    pg.wait_for_timeout(500)
    st = pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving])')].map(o => o.dataset.key + ':' + (o.classList.contains('behind') ? 'behind' : 'top'))")
    assert st == ["ov:err:behind", "ov:dev:top"]
    # scrim 을 뒤 카드가 있는 자리에서 누르면 그 카드가 앞으로, 빈 자리를 누르면 맨 위가 닫힌다
    # 뒤 카드가 보이는 띠(뒤 카드의 왼쪽 ~ 앞 카드의 왼쪽) 가운데를 누른다 — 뷰포트 밖으로 밀린 부분은 뺀다
    r = pg.evaluate("(() => { const b = document.querySelector('.ov.behind .dlg').getBoundingClientRect(), t = document.querySelector('.ov:not(.behind) .dlg').getBoundingClientRect(); return [(Math.max(b.left, 0) + t.left) / 2, Math.max(b.top, 0) + 120]; })()")
    assert r[0] > 8
    pg.mouse.click(r[0], r[1])
    pg.wait_for_timeout(500)
    assert pg.evaluate("document.querySelector('.ov:not(.behind):not([data-leaving]) .dlg').dataset.dlg") == "err"
    pg.mouse.click(5, 700)                                   # 빈 scrim
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    assert pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving]) .dlg')].map(d => d.dataset.dlg)") == ["dev"]
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="dev"]', state="detached")
    assert errors == []
