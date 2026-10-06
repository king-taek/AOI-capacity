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


def _row(dev, wafer, s=None, e=None, *, lot="LOT-A", status="Pass", job="J1", report=None, bs=None, be=None, day=DAY, mode=""):
    rep = report or f"{job}_6321_{lot}_{int(day[8:])}-Sep-26_(00.00.00)_BatchReport.htm"
    return {"device": dev, "kind": "", "job": job, "setup": "6321", "lot": lot, "wafer_id": wafer, "status": status,
            "wafer_start_time": _ts(s, day) if s else "", "wafer_end_time": _ts(e, day) if e else "",
            "batch_start": _ts(bs, day) if bs else (_ts(s, day) if s else ""), "batch_end": _ts(be, day) if be else (_ts(e, day) if e else ""),
            "report": rep, "ini_match": "EXACT" if s else "NOT_FOUND", "scan_type": "", "recipe": "", "scan_mode": mode, "data_issue": "",
            "faults": "3" if status == "Pass" else ""}


def _fixture_rows():
    rows = []
    # AOI-1: 정상 스캔 두 Lot + Error 하나(원인 ALIGN) + INI 없는 Pass 행(배치 창 추정)
    for i in range(6):
        rows.append(_row("AOI-1", f"W{i}", f"08:{i*5:02d}", f"08:{i*5+4:02d}", lot="LOT-A", job="TB500_RDL2", mode="MULTI"))
    rows.append(_row("AOI-1", "E1", "09:00", "09:03", lot="LOT-B", status="Alignment Error.", job="TB500_RDL2"))
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
        rows.append(_row("AOI-10", f"K{i}", f"09:{i*10:02d}", f"09:{i*10+8:02d}", lot="LOT-K", job="TB500_RDL3"))
    # 전날(9/17): AOI-1 에 Error 하나 — Error 탭의 '최근 7일' 이 이틀이 되어 기간 팝업(여러 날)을 검사할 수 있다
    rows.append(_row("AOI-1", "P1", "14:00", "14:03", lot="LOT-P", status="Scan Error.", job="TB500_RDL2", day="2026-09-17"))
    for i in range(3):
        rows.append(_row("AOI-1", f"Q{i}", f"15:{i*5:02d}", f"15:{i*5+3:02d}", lot="LOT-Q", job="TB500_RDL2", day="2026-09-17", mode="SINGLE"))
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
    pg.wait_for_selector('main[data-key="view:errors"]')   # 새 화면은 표시자가 출발한 두 프레임 뒤에 그린다
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
    assert pg.locator('button[data-fk="nav:trend"]').count() == 0 and pg.locator('button[data-fk="nav:kla"]').count() == 0   # 10/5: 추이 · KLA 탭 없음
    pg.locator('button[data-fk="nav:report"]').click()
    pg.wait_for_selector('main[data-key="view:report"]')   # 새 화면은 표시자가 출발한 두 프레임 뒤에 그린다
    rpt = pg.inner_text("main")
    assert "TB500 · Kendall" in rpt and "개 Job 만 봅니다" in rpt                    # D59
    assert "평균 Defect" in rpt and "수집 예정" not in rpt                             # D08
    assert pg.evaluate("[...document.querySelectorAll('main .panel')].some(p => p.style.overflowX === 'auto')")   # D10
    assert errors == []


def test_narrow_viewport_has_no_horizontal_page_scroll(page):
    pg, errors, _ = page
    pg.set_viewport_size({"width": 390, "height": 800})
    pg.locator('button[data-fk="nav:report"]').click()
    pg.wait_for_selector('main[data-key="view:report"]')   # 새 화면은 표시자가 출발한 두 프레임 뒤에 그린다
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
    pg.evaluate("window.__m = document.querySelector('main'); window.__p = document.querySelector('main .panel'); window.__r = document.querySelector('main button.rowbtn[data-key=\"slot:0\"]'); window.__d0 = window.__r.dataset.row")
    pg.locator('button[data-fk="seg:가동률 낮은 순"]').click()
    pg.wait_for_selector('button[data-fk="seg:가동률 낮은 순"].on')
    assert pg.evaluate("document.querySelector('main') === window.__m && document.querySelector('main .panel') === window.__p")
    # 줄은 제자리(9/24): 순위 칸 노드는 그대로, 그 칸에 오는 장비만 바뀐다 — 행이 자리를 옮기거나 떠오르지 않는다
    assert pg.evaluate("document.querySelector('main button.rowbtn[data-key=\"slot:0\"]') === window.__r")
    assert pg.evaluate("window.__r.dataset.row") != pg.evaluate("window.__d0")
    assert pg.evaluate("[...document.querySelectorAll('main button.rowbtn')].every(r => !r.getAnimations().some(a => a.constructor.name !== 'CSSTransition' && a.effect && a.effect.getKeyframes().some(k => k.transform)))")
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert pg.evaluate("document.querySelector('main[data-key=\"view:errors\"]') !== window.__m")             # 뷰가 바뀌면 main 은 새 노드
    assert errors == []


def test_error_tab_period_popup_filters_and_no_total_link(page):
    """Error 탭: 기간 전체를 고른 채 장비를 누르면 그 기간 그대로(여러 날) · 유형 필터 · '전체 기간 합계로' 없음."""
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert "전체 기간 합계로" not in pg.inner_text("main")
    pg.locator('main button[data-fk="seg:기간 전체 2일"]').click()        # 10/5: 기간은 헤더에서 — Error 탭은 '일자별' · '기간 전체' 둘
    pg.wait_for_selector('main button[data-fk="seg:기간 전체 2일"].on')
    pg.locator('main .row2[data-row="dev:AOI-1"] .rowbtn').click()
    pg.wait_for_selector('.dlg[data-dlg="err"]')
    txt = pg.locator('.dlg[data-dlg="err"]').inner_text()
    assert "· 2일" in txt and "하루씩 보기" in txt and "날짜별" in txt and "09/17" in txt      # 9/17 + 9/18 두 날
    assert "SCAN_ERROR" in txt and "ALIGN_ERROR" in txt                                      # 두 날의 Error 가 함께
    pg.locator('.dlg[data-dlg="err"] button', has_text="하루씩 보기").click()
    pg.wait_for_selector('.dlg[data-dlg="err"] h3', state="attached")
    # 바뀐 글자는 제자리에서 0.24초 동안 넘어간다(9/24) — 다 넘어간 뒤 읽는다
    pg.wait_for_function("document.querySelector('.dlg[data-dlg=\"err\"]').innerText.includes('언제 났나')", timeout=3000)
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    # 유형 필터: 첫 유형의 깔때기 → 카드 라벨·칩, 목록은 그 유형만
    pg.locator('main .row2[data-row^="type:"] .fbtn').first.click()
    pg.wait_for_selector('main .fchip')
    pg.wait_for_function("document.querySelector('main').innerText.includes('Error (필터)')", timeout=3000)   # 글자 넘김(0.24초) 뒤
    assert "Error (필터)" in pg.inner_text("main") and pg.locator('main .row2[data-row^="type:"]').count() == 1
    pg.locator('main .fchip').first.click()
    pg.wait_for_selector('main .fchip', state="detached")
    assert errors == []


def test_error_lists_keep_rows_in_place_and_only_text_changes(page):
    """Error 탭에서 날짜를 바꿔도 유형별·장비별·Job별 줄은 제자리(순위 칸 slot:i 가 같은 노드 · 이동 트윈 없음)이고
    안의 글자만 바뀐다 — 숫자는 세고 글자는 제자리에서 넘어가며(흐림·번쩍임 없음), 끝나면 정확히 새 값(9/23 사용자 요청: 목록이 출렁인다)."""
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    first = 'main .errlist .row2[data-key="slot:0"]'
    assert pg.get_attribute(first, "data-row") == "type:ALIGN_ERROR"                     # 9/18 하루
    pg.evaluate(f"window.__t = document.querySelector('{first}')")
    pg.locator('[data-key="chart:errors"] button[title^="09/17"]').click()
    pg.wait_for_selector('main .errlist .row2[data-row="type:SCAN_ERROR"]')
    assert pg.evaluate(f"document.querySelector('{first}') === window.__t")               # 같은 줄 노드, 내용만 교체
    rows = "[...document.querySelectorAll('main .errlist .row2, main .errlist > .rowbtn')]"
    assert pg.evaluate(f"{rows}.every(r => !r.style.transform && !r.hasAttribute('data-leaving'))")
    assert pg.evaluate(f"typeof gsap === 'undefined' || gsap.getTweensOf({rows}).length === 0")  # Flip·등장 트윈 없음
    pg.wait_for_timeout(450)
    nm = "window.__t.querySelector('[data-tx]')"
    assert pg.evaluate(f"{nm}.textContent") == "SCAN_ERROR"                                    # 넘어가기가 끝나면 정확히 새 이름
    assert pg.evaluate(f"{nm}.__tr") == 1 and pg.evaluate(f"{nm}.getAnimations().length") == 0    # 한 번 넘어갔고, CSS 흐림·깜박임 없음
    bad = pg.evaluate("[...document.querySelectorAll('main .errlist [data-txn][data-txf=\"n\"]')].filter(e => e.textContent !== e.dataset.txn + '건').length")
    assert bad == 0                                                                          # 세기가 끝나면 정확히 새 값
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
    order = pg.evaluate("[...document.querySelectorAll('[data-row^=\"job:\"]')].map(e => e.dataset.row.slice(4))")
    assert order == ["Kendall FS", "TB500 RDL2-Multi"]                      # 그룹 순서 · 이름순 · 멀티는 다른 Job(D76)
    hdr = pg.locator('.thead button.th', has_text="배치")
    hdr.click()
    pg.wait_for_selector('.thead button.th[aria-sort="descending"]')
    hdr.click()
    pg.wait_for_selector('.thead button.th[aria-sort="ascending"]')
    pg.wait_for_function("document.querySelector('main').innerText.includes('오름차순')", timeout=3000)   # 글자 넘김(0.24초) 뒤
    assert errors == []


def test_motion_hooks_lottie_countup_sweep_and_recede(page):
    """세 라이브러리의 자리: 브랜드의 Lottie 표식 · 'Error 없음' 의 Lottie 체크 · GSAP 카운트업(끝 값이 정확) · 막대 sweep(끝나면 clip-path 남지 않음) · 팝업 뒤 무대 물러남."""
    pg, errors, _ = page
    assert pg.locator('.brand .lt svg').count() == 1                                     # lottie 가 브랜드 표식을 그렸다
    pg.locator('button[data-fk="day:prev"]').click()                                     # 날짜를 바꾸면 카드 숫자가 이전 값에서 새 값으로
    pg.wait_for_function("document.querySelector('[data-fk=\"day:date\"]').value === '2026-09-17'")   # 10/6 C8: 하루 날짜는 입력 칸
    pg.wait_for_timeout(900)
    v = pg.locator('main .cards [data-count]').first
    assert v.inner_text() == f"{float(v.get_attribute('data-count')):.1f}"              # 카운트업이 끝나면 정확히 새 값
    assert pg.evaluate("[...document.querySelectorAll('[data-bar]')].every(e => !e.style.clipPath)")   # sweep 뒤 clip-path 정리
    pg.locator('button[data-fk="day:next"]').click()
    pg.wait_for_function("document.querySelector('[data-fk=\"day:date\"]').value === '2026-09-18'")
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
    # 팝업의 DOM 순서는 고정이고 겹침은 z-index 로만 바뀐다(9/24 — 요소를 옮기면 CSS 전환이 끊겨 번쩍였다)
    st = pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving])')].sort((a, b) => +a.style.zIndex - +b.style.zIndex).map(o => o.dataset.key + ':' + (o.classList.contains('behind') ? 'behind' : 'top'))")
    assert st == ["ov:err:behind", "ov:dev:top"]
    assert pg.evaluate("[...document.querySelectorAll('.ov:not([data-leaving])')].map(o => o.dataset.key)") == ["ov:dev", "ov:err"]
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


def test_stackbar_stays_top_left_while_the_popup_scrolls_and_lot_panel_fades_in_once(page):
    """스택 바는 팝업 덮개 밖(#app)에 있어 팝업을 스크롤해도 왼쪽 위에 고정된다(.ov 의 perspective 가 fixed 기준 상자가 되던 문제, 9/24).
    선택 Lot 상세 박스는 처음 나타날 때만 제자리 페이드(fadeIn — 아래에서 올라오지 않음), 다른 Lot 으로 바꾸면 같은 박스에서 글자만 바뀐다."""
    pg, errors, _ = page
    pg.set_viewport_size({"width": 1280, "height": 420})
    pg.locator('button.rowbtn[data-fk="dev:AOI-1"]').click()
    pg.wait_for_selector('.dlg[data-dlg="dev"]')
    pg.locator('.dlg[data-dlg="dev"] button', has_text="Error 보기").click()
    pg.wait_for_selector('.stackbar .sb')
    assert pg.evaluate("document.querySelector('.stackbar').parentElement.id") == "app"
    top0 = pg.evaluate("document.querySelector('.stackbar').getBoundingClientRect().top")
    scrolled = pg.evaluate("(() => { const o = document.querySelector('.ov:not(.behind):not([data-leaving])'); o.scrollTop = 400; return o.scrollTop; })()")
    assert scrolled > 0
    assert pg.evaluate("document.querySelector('.stackbar').getBoundingClientRect().top") == top0
    pg.keyboard.press("Escape")
    pg.wait_for_selector('.dlg[data-dlg="err"]', state="detached")
    pg.wait_for_timeout(700)
    calls = pg.locator('.dlg[data-dlg="dev"] .callout')
    assert calls.count() >= 2
    calls.nth(0).click()
    pg.wait_for_selector('.dlg[data-dlg="dev"] .sel')
    assert pg.evaluate("document.querySelector('.dlg[data-dlg=\"dev\"] .sel').getAnimations().map(a => a.animationName)") == ["fadeIn"]
    pg.wait_for_timeout(500)
    pg.evaluate("window.__sel = document.querySelector('.dlg[data-dlg=\"dev\"] .sel'); window.__st = window.__sel.getAnimations()[0].startTime")
    calls.nth(1).click()
    pg.wait_for_timeout(60)
    assert pg.evaluate("document.querySelector('.dlg[data-dlg=\"dev\"] .sel') === window.__sel")                     # 같은 박스
    assert pg.evaluate("window.__sel.getAnimations().every(a => a.startTime === window.__st)")                          # 페이드를 다시 돌리지 않는다
    assert errors == []


def test_tab_indicator_survives_in_tab_clicks_and_follows_the_tab(page):
    """탭 표시자(9/24): 같은 탭 안에서 다른 버튼을 눌러도 사라지지 않고(morph 가 인라인 스타일을 지우던 문제), 탭을 옮기면 그 탭에 가서 선다."""
    pg, errors, _ = page
    box = "(() => { const p = [...document.querySelectorAll('.nav .ind b')].map(e => e.getBoundingClientRect()), on = document.querySelector('.nav button.on').getBoundingClientRect(); return [Math.round(p[0].left), Math.round(p[2].right), Math.round(on.left), Math.round(on.right)]; })()"
    b0 = pg.evaluate(box)
    near = lambda b: abs(b[0] - b[2]) <= 1 and abs(b[1] - b[3]) <= 1          # 10/5: 자리를 소수까지 맞추므로 반올림 차 1px 까지
    assert near(b0)
    pg.locator('button[data-fk="seg:가동률 낮은 순"]').click()
    pg.wait_for_selector('button[data-fk="seg:가동률 낮은 순"].on')
    pg.wait_for_timeout(100)
    assert pg.evaluate(box) == b0                                                       # 같은 탭 안 — 그대로
    pg.locator('button[data-fk="nav:report"]').click()
    pg.wait_for_selector('main[data-key="view:report"]')
    pg.wait_for_timeout(900)
    b1 = pg.evaluate(box)
    assert near(b1) and b1 != b0                                                         # 새 탭에 가서 선다
    assert errors == []


def test_tab_indicator_moves_like_a_body_dragged_by_its_front(page):
    """탭 표시자 물리(9/24 4차): 앞 끝이 먼저 가고 뒤가 딸려 와 움직이는 동안 늘어나며, 앞 끝이 도착한 뒤에는 폭이 늘지 않고 줄어들며 선다.
    (3차는 반대였다 — 움직일 때 좁고 도착해서 넓어졌다.) 미리 계산한 표본(`__s.run.fr`)을 본다 — 시계와 무관하다."""
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:report"]').click()
    fr = pg.evaluate("(() => { const s = document.querySelector('.nav .ind').__s; return s && s.run ? s.run.fr.map(q => [q.x[0], q.x[q.x.length - 1]]) : null; })()")
    if fr is None:
        pytest.skip("애니메이션이 꺼진 환경(reduced motion / WAAPI 없음)")
    (l0, r0), (tl, tr) = fr[0], fr[-1]
    w0, wt = r0 - l0, tr - tl
    assert tr > r0                                                                          # 오른쪽으로 간다
    k = next(i for i, (l, r) in enumerate(fr) if r >= tr - 1.5)                            # 앞(오른쪽) 끝 도착
    assert k > 1
    assert max(r - l for l, r in fr[:k + 1]) > max(w0, wt) + 8                            # 움직이는 동안 늘어난다
    assert max(r - l for l, r in fr[k:]) <= max(fr[k][1] - fr[k][0], wt) + 0.5            # 도착 뒤 더 넓어지지 않는다
    assert min(r - l for l, r in fr[k:]) >= wt - 4                                          # 눌림은 조금만
    assert max(r for _, r in fr) <= tr + 4                                                  # 앞 끝은 거의 지나치지 않는다
    assert all(l <= l0 + 0.5 for l, _ in fr[:2])                                            # 뒤 끝은 늦게 출발한다
    assert errors == []



def test_recipe_groups_apply_at_once_persist_in_browser_and_export(page, tmp_path):
    """D67: 레시피 묶음 편집기 — 묶으면 Error 탭 Job별이 그 이름 하나로 바로 바뀌고, 다시 열어도 이 브라우저에 남으며,
    '내보내기' 는 수집기가 읽는 모양(v · saved · groups[name, jobs])이고 '사본 저장' 도 그 묶음을 담는다. 바깥 요청 0건."""
    pg, errors, requests = page
    pg.locator('[data-fk="rg:open"]').click()
    pg.wait_for_selector('[data-dlg="recipe"]')
    pg.fill('[data-fk="rg:q"]', "_")
    pg.wait_for_timeout(150)
    assert sorted(pg.locator(".rgrow .mono").all_inner_texts()) == ["R_KENDALL_A0_FS", "TB500_RDL2", "TB500_RDL2-Multi", "TB500_RDL3"]
    assert pg.evaluate("document.activeElement.dataset.fk") == "rg:q"           # 입력 중 다시 그려도 포커스는 그 칸
    pg.get_by_role("button", name="목록 전부 선택").click()
    pg.fill('[data-fk="rg:name"]', "MIX RECIPE")
    pg.get_by_role("button", name="새 묶음으로").click()
    assert pg.locator(".rgcard b").all_inner_texts() == ["MIX RECIPE"]
    assert pg.input_value('[data-fk="rg:name"]') == ""                        # 만든 뒤 이름 칸은 비운다(속성값까지)
    with pg.expect_download() as dl:
        pg.get_by_role("button", name="내보내기").click()
    exp = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    assert dl.value.suggested_filename == "recipe_groups.json"
    assert exp["v"] == 1 and exp["saved"] and [g["name"] for g in exp["groups"]] == ["MIX RECIPE"]
    assert sorted(exp["groups"][0]["jobs"]) == ["R_KENDALL_A0_FS", "TB500_RDL2", "TB500_RDL2-Multi", "TB500_RDL3"]
    pg.keyboard.press("Escape")
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert "MIX RECIPE" in pg.locator('[data-row^="job:"]').all_inner_texts()[0]
    pg.reload()
    pg.wait_for_selector('main[data-key^="view:"]')
    pg.locator('[data-fk="rg:open"]').click()
    pg.wait_for_selector('[data-dlg="recipe"]')
    assert pg.locator(".rgcard b").all_inner_texts() == ["MIX RECIPE"]
    assert "내보내기 필요" in pg.locator('[data-dlg="recipe"] .dh').inner_text()
    with pg.expect_download() as dl2:
        pg.evaluate("saveHtml()")                                   # 헤더 버튼은 팝업 아래(inert) — 같은 함수를 직접
    meta = sample_rows.unfold(sample_rows.embedded(Path(dl2.value.path()).read_text(encoding="utf-8")))[1]
    assert [g["name"] for g in meta["recipe_groups"]["groups"]] == ["MIX RECIPE"]
    pg.get_by_role("button", name="되돌리기").click()
    assert pg.locator(".rgcard").count() == 0
    assert requests == [] and errors == []


def test_recipe_tab_shows_per_device_stats_and_compares_two_periods(page):
    """D70: 레시피 탭 — 레시피(Job 묶음)를 고르면 생산량 · 장당 스캔 · 장비별 표, 아래 전후 비교는 두 기간 × 두 레시피 묶음.
    값은 원천 행에서: AOI-1 의 TB500_RDL2 PASS 는 9/17 3장 + 9/18 6장(Error 행·Test 는 생산량이 아니다)."""
    pg, errors, requests = page
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    pg.fill('[data-fk="rcp:q"]', "RDL2")
    pg.wait_for_timeout(150)
    assert pg.evaluate("document.activeElement.dataset.fk") == "rcp:q"
    pg.wait_for_timeout(450)                                                    # 바뀐 글자는 0.24초 동안 한 글자씩 넘어간다
    assert [x.split("\n")[0] for x in pg.locator(".rcprow").all_inner_texts()] == ["TB500 RDL2"]   # 10/6: 멀티 · 단일 Job(D76)은 한 레시피 줄로
    assert "멀티 67%" in pg.locator(".rcprow").first.inner_text()
    pg.locator(".rcprow").first.click()
    # 첫 화면(10/5): 장당 스캔 멀티 vs 단일 — 9/18 W 6장 멀티 4분, 9/17 Q 3장 단일 3분 → 단일 1분 빠름(같은 장비 AOI-1)
    tiles = pg.locator(".scanhero .mtile").all_inner_texts()
    assert "4.0" in tiles[0] and "6장" in tiles[0] and "3.0" in tiles[1] and "3장" in tiles[1]
    assert "전체 장\n단일 1.0분 빠름" in tiles[2] and "같은 장비\n단일 1.0분 빠름" in tiles[2] and "1대를 합침" in tiles[2]   # 10/6 C1: 두 비교를 같은 크기로
    assert pg.locator(".scanhero .scan-source-chip").count() == 4                       # 10/6 C2: 방식마다 INI · Report 보완 칩
    assert pg.locator(".scanhero .jchip").count() == 2                 # 이 레시피로 보는 Job: RDL2-Multi · PI2
    assert [x.split("\n")[0] for x in pg.locator(".dbrow:not(.head):not(.axis)").all_inner_texts()] == ["AOI-1"]
    assert pg.locator(".dbrow .dd").count() == 2                        # 같은 장비에 멀티 · 단일 두 점
    how = pg.locator(".how").inner_text()                               # 10/6: 어떻게 셌나 — 실제 숫자로
    assert "9장" in how and "WaferStartTime" in how and "Batch Start" in how
    assert pg.locator("main section.cards").count() == 0              # 생산량 등은 상세 보기 안
    pg.locator('[data-fk="rcp:more"]').click()
    pg.wait_for_timeout(200)
    cards = pg.locator("main section.cards > div").all_inner_texts()
    assert cards[0].split("\n")[0] == "생산량" and "6장" in cards[0]           # 상세는 고른 Job(RDL2-Multi)만
    assert [x.split("\n")[0] for x in pg.locator(".rcpdev").all_inner_texts()] == ["AOI-1"]
    assert pg.locator(".cmp").count() == 0
    pg.locator('[data-fk="rcp:cmp"]').click()
    pg.wait_for_selector(".cmp")
    pg.locator(".jpick .btn").nth(1).click()                               # 상세에서 단일(RDL2)을 골라 A 쪽에 더한다
    pg.locator(".cmpside").nth(0).get_by_role("button", name=re.compile("＋")).click()
    pg.wait_for_timeout(300)
    pg.fill('[data-fk="cmp:cmpAf"]', "2026-09-17")
    pg.fill('[data-fk="cmp:cmpAt"]', "2026-09-17")
    pg.fill('[data-fk="cmp:cmpBf"]', "2026-09-18")
    pg.fill('[data-fk="cmp:cmpBt"]', "2026-09-18")
    pg.wait_for_timeout(500)                                    # 바뀐 숫자는 제자리에서 0.24초 동안 한 글자씩 넘어간다(9/24)
    rows = {r.split("\n")[0]: r.split("\n")[1:] for r in pg.locator(".cmp .cmprow:not(.dev):not(.head)").all_inner_texts()}
    assert rows["생산량(Wafer)"][:2] == ["3", "6"] and "+100.0%" in rows["생산량(Wafer)"][2]
    assert rows["멀티 스캔 장 비율(%)"][:2] == ["0.0", "100.0"]
    # 다른 레시피를 B 에 더하면 B 쪽 생산량이 늘어난다(전 = RDL2, 후 = RDL2 + RDL3)
    pg.fill('[data-fk="rcp:q"]', "RDL3")                         # 10/6: 레시피 탭은 TB500 RDL · TB500 PI 만 — 다른 레시피(RDL3)를 더한다
    pg.wait_for_timeout(150)
    pg.locator(".rcprow").first.click()
    pg.locator(".cmpside").nth(1).get_by_role("button", name=re.compile("＋")).click()
    pg.wait_for_timeout(500)
    rows = {r.split("\n")[0]: r.split("\n")[1:] for r in pg.locator(".cmp .cmprow:not(.dev):not(.head)").all_inner_texts()}
    assert rows["생산량(Wafer)"][:2] == ["3", "8"]               # 첫 레시피가 양쪽 묶음의 시작, 다른 레시피를 골라도 A 는 그대로
    assert requests == [] and errors == []


def test_header_period_limits_every_tab_to_the_chosen_days(page):
    """10/5: 헤더에서 기간을 고르면 모든 탭이 그 날만 그린다 — 프리셋 최근 7일 · 1달 · 전체, 날짜 두 칸. '최근' 은 데이터의 끝날 기준."""
    pg, errors, requests = page
    days = lambda: pg.locator(".rangebar .rdays").inner_text()
    assert days() == "2일" and pg.input_value('[data-fk="range:vf"]') == "2026-09-17"
    pg.locator('[data-fk="range:vf"]').fill("2026-09-18")
    pg.locator('[data-fk="range:vf"]').dispatch_event("change")
    pg.wait_for_timeout(300)
    assert days() == "1일" and pg.input_value('[data-fk="range:vt"]') == "2026-09-18"
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    bars = lambda: pg.locator('main [data-key="chart:errors"] .chart').first.locator(":scope > *").count()
    assert bars() == 1
    pg.get_by_role("button", name="전체", exact=True).first.click()
    pg.wait_for_timeout(300)
    assert days() == "2일" and bars() == 2
    assert requests == [] and errors == []


def test_floor_and_maker_filters_are_picked_separately(page):
    """10/5: 층과 장비 종류는 따로 — '2층' 을 고른 채 'Camtek' 을 눌러도 2층이 풀리지 않는다."""
    pg, errors, _ = page
    pg.locator('button[data-fk="seg:2층"]').click()
    pg.locator('button[data-fk="seg:Camtek"]').click()
    pg.wait_for_timeout(200)
    assert pg.locator('button[data-fk="seg:2층"].on').count() == 1 and pg.locator('button[data-fk="seg:Camtek"].on').count() == 1
    names = [x.split("\n")[0] for x in pg.locator(".homelist .rowbtn").all_inner_texts()]
    assert names == ["AOI-1", "AOI-2", "AOI-3", "AOI-10"][:len(names)] and names
    pg.locator('button[data-fk="seg:KLA"]').click()
    pg.wait_for_timeout(200)
    assert pg.locator(".homelist .rowbtn").count() == 0 and pg.locator('button[data-fk="seg:2층"].on').count() == 1
    assert errors == []


def test_recipe_group_of_multi_job_still_shows_single_on_the_same_row(page):
    """10/6(사용자 보고): 레시피 묶음(D67)에 멀티 Job(`TB500_RDL2-Multi`)만 넣어 두면 단일 Job 이 같은 이름으로 한 줄 더 생겼다.
    줄기가 같은 Job 묶음은 한 레시피(이름은 사용자 묶음 이름)."""
    pg, errors, _ = page
    pg.evaluate("""localStorage.setItem('aoi.recipeGroups.v1', JSON.stringify({v:1, saved:'2099-01-01T00:00:00',
        groups:[{name:'RDL2 묶음', jobs:['TB500_RDL2-Multi']}]}))""")
    pg.reload()
    pg.wait_for_selector('main[data-key^="view:"]')
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    pg.fill('[data-fk="rcp:q"]', "RDL2")
    pg.wait_for_timeout(450)
    rows = [x.split("\n")[0] for x in pg.locator(".rcprow").all_inner_texts()]
    assert rows == ["TB500 RDL2"]                                         # 10/6: 이 탭의 레시피 이름은 표기 이름(묶음 편집기와 무관) — 멀티 · 단일 Job 은 한 줄
    assert pg.locator(".scanhero .jchip").count() == 2                    # 멀티 · 단일 둘 다 이 레시피
    pg.evaluate("localStorage.removeItem('aoi.recipeGroups.v1')")
    assert errors == []


def _open_recipe(pg, q="RDL2"):
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    pg.fill('[data-fk="rcp:q"]', q)
    pg.wait_for_timeout(450)


def test_recipe_close_point_labels_do_not_overlap(page):
    """10/6 handoff C3: 장비별 점 그래프의 두 숫자는 같은 높이, 가까우면 가운데에서 좌우로 10px 이상 띄운다(점은 그대로) · 칸 밖으로 안 나간다.
    작은 fixture 에는 겹치는 값이 없어 두 숫자를 같은 자리(50%)로 옮긴 뒤 배치 함수를 다시 부른다."""
    pg, errors, _ = page
    for width in (1440, 820, 390):
        pg.set_viewport_size({"width": width, "height": 900})
        _open_recipe(pg)
        r = pg.evaluate("""(() => {const tr = document.querySelector('[data-key="rcp:mdev"] button.dbrow .dtrack');
            const dots = [...tr.querySelectorAll('.dd')].map(d => d.style.left);
            for (const l of tr.querySelectorAll('.dlab')) l.dataset.p = '50';
            layoutPairLabels(document);
            const T = tr.getBoundingClientRect(), [a, b] = [...tr.querySelectorAll('.dlab')].map(l => l.getBoundingClientRect()).sort((x, y) => x.left - y.left);
            return {top: [a.top, b.top], gap: b.left - a.right, inside: a.left >= T.left - 0.5 && b.right <= T.right + 0.5,
                    dots: [...tr.querySelectorAll('.dd')].map(d => d.style.left).join() === dots.join()};})()""")
        assert abs(r["top"][0] - r["top"][1]) < 0.5 and r["gap"] >= 9.5 and r["inside"] and r["dots"], (width, r)
    assert errors == []


def test_recipe_device_row_selection_shows_matching_provenance(page):
    """10/6 handoff C3: 장비 행을 누르면(Enter · Space 도) 아래 고정 칸에 그 장비의 중앙 · 계산 장 수 · INI/Report 보완 — 행은 같은 노드로 남는다."""
    pg, errors, _ = page
    _open_recipe(pg)
    row = pg.locator('[data-key="rcp:mdev"] button.dbrow[data-row="dev:AOI-1"]')
    pg.evaluate("window.__row = document.querySelector('[data-key=\"rcp:mdev\"] button.dbrow[data-row=\"dev:AOI-1\"]')")
    row.focus()
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(200)
    assert row.get_attribute("aria-pressed") == "true"
    det = pg.locator('[data-key="rcp:mdev:detail"] .mdsel:not([hidden])')
    assert det.count() == 1 and det.get_attribute("data-dev") == "AOI-1"
    txt = det.inner_text()
    assert "멀티" in txt and "6장으로 계산 / PASS 6장" in txt and "INI 6 + Report 보완 0" in txt and "단일" in txt
    assert pg.evaluate("window.__row === document.querySelector('[data-key=\"rcp:mdev\"] button.dbrow[data-row=\"dev:AOI-1\"]')")
    assert errors == []


def test_recipe_how_summary_and_details_are_accessible(page):
    """10/6 handoff C5: '어떻게 셌나' 여섯 카드 — 닫혀 있어도 핵심 숫자 · 두 시각 필드가 보이고, 카드마다 따로 펼치며(키보드도) 다시 그려도 유지된다."""
    pg, errors, _ = page
    _open_recipe(pg)
    items = pg.locator(".how .how-item")
    assert items.count() == 8 and pg.locator(".how .how-item[open]").count() == 0
    how = pg.locator(".how").inner_text()
    assert "PASS 9장" in how and "WaferStartTime → WaferEndTime" in how and "Batch Start → Batch End" in how
    pg.locator('[data-fk="how:time"]').click()
    pg.locator('[data-fk="how:batch"]').focus()
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(250)
    assert pg.locator(".how .how-item[open]").count() == 2
    pg.locator('[data-fk="rcp:more"]').click()                                       # 다른 곳을 눌러 다시 그려도 펼친 카드는 그대로
    pg.wait_for_timeout(250)
    assert pg.locator(".how .how-item[open]").count() == 2
    pg.locator('[data-fk="how:time"]').click()
    pg.wait_for_timeout(150)
    assert pg.locator(".how .how-item[open]").count() == 1
    assert errors == []


def test_recipe_no_match_clearly_identifies_retained_or_empty_detail(page):
    """10/6 handoff C7: 검색 결과 0개면 이전 상세를 그대로 두지 않고 '검색 결과가 없습니다' + 이전 선택 요약 — 버튼은 검색만 지우고 그 상세로, 검색 칸에 포커스."""
    pg, errors, _ = page
    _open_recipe(pg)
    assert pg.locator(".scanhero").count() == 1
    pg.fill('[data-fk="rcp:q"]', "ZZZ-NOPE")
    pg.wait_for_timeout(450)
    empty = pg.locator('[data-key="rcp:empty-detail"]')
    assert pg.locator(".scanhero").count() == 0 and "검색 결과가 없습니다" in empty.inner_text()
    assert "이전 선택" in empty.inner_text() and "TB500 RDL2" in empty.inner_text()
    assert "검색 결과 0개" in pg.locator(".rcpnote").inner_text()
    pg.locator('[data-fk="rcp:clear"]').click()
    pg.wait_for_timeout(450)
    assert pg.input_value('[data-fk="rcp:q"]') == "" and pg.evaluate("document.activeElement.dataset.fk") == "rcp:q"
    assert pg.locator(".scanhero").count() == 1
    assert errors == []


def test_date_controls_keep_day_inside_the_visible_period(page):
    """10/6 handoff C8: 날짜는 두 줄 — 위 '조회 기간', 아래 '하루 날짜'. 하루는 기간 안의 데이터 날짜만, 기간이 하루를 밀어내면 마지막 날로 옮기고 짧게 알린다."""
    pg, errors, _ = page
    day = lambda: pg.input_value('[data-fk="day:date"]')
    assert pg.locator(".date-controls .date-control-row").count() == 2 and day() == "2026-09-18"
    pg.locator('[data-fk="day:date"]').fill("2026-09-17")
    pg.locator('[data-fk="day:date"]').dispatch_event("change")
    pg.wait_for_timeout(250)
    assert day() == "2026-09-17" and "09/17 하루" in pg.locator('main[data-key="view:home"] .scope-badge').inner_text()
    pg.locator('[data-fk="range:vf"]').fill("2026-09-18")
    pg.locator('[data-fk="range:vf"]').dispatch_event("change")
    pg.wait_for_timeout(300)
    assert day() == "2026-09-18" and "하루 날짜 09/17 → 09/18" in pg.locator(".daynote").inner_text()
    assert pg.locator('[data-fk="day:prev"]').is_disabled() and pg.locator('[data-fk="day:next"]').is_disabled()   # 하루짜리 기간
    pg.get_by_role("button", name="전체", exact=True).first.click()
    pg.wait_for_timeout(300)
    assert day() == "2026-09-18" and pg.locator(".daynote").count() == 0             # 안에 있으면 그대로 · 알림 없음
    pg.locator('[data-fk="day:date"]').fill("2026-09-01")                            # 데이터 없는 날은 고르지 않는다
    pg.locator('[data-fk="day:date"]').dispatch_event("change")
    pg.wait_for_timeout(250)
    assert day() == "2026-09-18"
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    assert pg.locator(".daynav").count() == 0 and pg.locator(".date-controls .date-control-row").count() == 1     # 10/6: 하루가 기준이 아닌 탭은 하루 날짜 줄이 없다
    assert "2일" in pg.locator('main[data-key="view:recipe"] .scope-badge').inner_text()
    assert errors == []


def test_error_day_selection_matches_the_header_date(page):
    """10/6 handoff C8: Error 기간 전체에서 날짜 막대를 고르면 일자별이 되고 헤더의 하루 날짜도 그 날 — 같은 막대를 다시 누르면 기간 전체로."""
    pg, errors, _ = page
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    pg.get_by_role("button", name=re.compile("^기간 전체")).first.click()
    pg.wait_for_timeout(250)
    assert "~" in pg.locator('main[data-key="view:errors"] .scope-badge').inner_text()
    pg.locator('main [data-key="chart:errors"] .chart > button').first.click()       # 09/17
    pg.wait_for_timeout(300)
    assert pg.input_value('[data-fk="day:date"]') == "2026-09-17" and pg.locator('main[data-key="view:errors"] .scope-badge').inner_text() == "09/17 하루"
    pg.locator('main [data-key="chart:errors"] .chart > button').first.click()
    pg.wait_for_timeout(300)
    assert "~" in pg.locator('main[data-key="view:errors"] .scope-badge').inner_text()
    assert errors == []


def test_narrow_dashboard_controls_and_labels_stay_visible(page):
    """10/6 handoff C4: 820 · 390px 에서 네 탭과 장비 팝업 모두 쪽 가로 스크롤이 없고, 필터 버튼 · 숫자가 화면 안에 있다(표 안 스크롤은 허용)."""
    pg, errors, _ = page
    js_out = """[...document.querySelectorAll('main button, main .num, header button, header input, .dlg button')].filter(e => {const r = e.getBoundingClientRect();
        return r.width && (r.right > innerWidth + 1 || r.left < -1) && !e.closest('.cmpdev, .nav, [style*="overflow-x"]');}).length"""
    for width in (820, 390):
        pg.set_viewport_size({"width": width, "height": 860})
        for v in ("home", "errors", "report", "recipe"):
            pg.locator(f'button[data-fk="nav:{v}"]').click()
            pg.wait_for_selector(f'main[data-key="view:{v}"]')
            pg.wait_for_timeout(300)
            assert pg.evaluate("document.documentElement.scrollWidth") <= width, (width, v)
            assert pg.evaluate(js_out) == 0, (width, v)
        pg.locator('button[data-fk="nav:home"]').click()
        pg.wait_for_selector('main[data-key="view:home"]')
        pg.locator('button.rowbtn[data-fk="dev:AOI-1"]').click()
        pg.wait_for_selector('.dlg[data-dlg="dev"]')
        pg.wait_for_timeout(500)
        assert pg.evaluate("document.documentElement.scrollWidth") <= width
        assert pg.evaluate("""(() => {const b = document.querySelector('[data-callw]'); if (!b) return true; const B = b.getBoundingClientRect();
            return [...b.querySelectorAll('.callout')].every(c => {const r = c.getBoundingClientRect(); return r.left >= B.left - 1 && r.right <= B.right + 1;});})()""")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)
    assert errors == []


# ── 10/6 'RDL 단일스캔' 개편: Report 1LOT당 · 이상치 · x5 단일 무시 · 장비 상세 팝업 · 하루 날짜 줄 ────────────────────
def _rdl_rows():
    """AOI-5 의 TB500_RDL4(단일 x20): Report A = PASS 22장(+Aborted 한 줄 — 원인 없는 중단은 허용) · 한 장만 150분(이상치) ·
    Report B = Error 가 있어 제외 · Report C = 19장이라 제외 · x5 만 쓴 단일 6장(실수로 돌린 것 — 무시)."""
    rows = []
    def add(wafer, s, e, *, lot, report, bs, be, status="Pass", recipe="x20"):
        r = _row("AOI-5", wafer, s, e, lot=lot, job="TB500_RDL4", report=report, bs=bs, be=be, mode="SINGLE", status=status)
        r["recipe"] = recipe
        rows.append(r)
    for i in range(21):
        add(f"A{i}", f"08:{i*2:02d}" if i < 30 else "09:00", f"08:{i*2+1:02d}", lot="LOT-A", report="RA.htm", bs="08:00", be="14:00")
    add("A21", "11:00", "13:30", lot="LOT-A", report="RA.htm", bs="08:00", be="14:00")                    # 150분 — 평균 ± 3σ 밖
    rows.append(_row("AOI-5", "A22", lot="LOT-A", status="Aborted.", job="TB500_RDL4", report="RA.htm", bs="08:00", be="14:00", mode="SINGLE"))
    for i in range(20):
        add(f"B{i}", f"16:{i*2:02d}", f"16:{i*2+1:02d}", lot="LOT-B", report="RB.htm", bs="16:00", be="17:00")
    add("BE", "17:00", "17:01", lot="LOT-B", report="RB.htm", bs="16:00", be="17:00", status="Alignment Error.")
    for i in range(19):
        add(f"C{i}", f"18:{i*2:02d}", f"18:{i*2+1:02d}", lot="LOT-C", report="RC.htm", bs="18:00", be="19:00")
    for i in range(6):
        add(f"X{i}", f"20:{i*2:02d}", f"20:{i*2+1:02d}", lot="LOT-X", report="RX.htm", bs="20:00", be="21:00", recipe="x5")
    return rows


@pytest.fixture
def rdl_page(page_factory, tmp_path):
    emb = collect._embed_rows(_rdl_rows())
    meta = _meta()
    meta["scope"]["devices"] = ["AOI-5"]
    meta["devices"] = [{"name": "AOI-5", "note": "X:\\AOI-5", "report_dir": "Report", "status": "ok"}]
    emb["meta"] = meta
    out = tmp_path / "rdl.html"
    out.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", json.dumps(emb, ensure_ascii=False).replace("</", "<\\/"), 1), encoding="utf-8")
    ctx = page_factory.new_context(viewport={"width": 1280, "height": 900})
    pg = ctx.new_page()
    errors: list = []
    pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(out.as_uri())
    pg.wait_for_selector('main[data-key^="view:"]')
    yield pg, errors
    ctx.close()


def test_rdl_tab_lot_stat_outlier_x5_rule_and_wording(rdl_page):
    pg, errors = rdl_page
    assert [t.strip() for t in pg.locator("nav button").all_inner_texts()] == ["가동률", "Error", "TB500 · Kendall", "RDL 단일스캔"]
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    pg.wait_for_timeout(400)
    assert pg.locator("main h1").inner_text().strip() == "RDL 단일스캔"
    assert pg.locator('[data-key="rcp:note"]').inner_text().strip() == "전체 1개"            # '레시피 n개' · '상위 n개' 군더더기 없음
    assert pg.locator('[data-key="rcp:detail"] .scanhero h2').inner_text().strip() == "TB500 RDL4"   # '장당 스캔 — 멀티 vs 단일 ·' 문구 없음
    assert "tfade" in pg.locator('[data-key="rcp:detail"] .scanhero h2').get_attribute("class")
    tiles = pg.locator(".scanhero .mtile").all_inner_texts()
    single = [t for t in tiles if t.startswith("단일")][0]
    assert "(x20)" in single
    assert "Report 1LOT당 409.1분" in single.replace("\n", " ") and "Lot 1개" in single      # 22장 → 360분 × 25 ÷ 22(20~24장은 25장 기준으로 환산) · Error/19장 Report 는 제외
    assert "이상치 1개 제외" in single and "150.0분" in single and "3σ" in single               # 어떤 값이 왜 빠졌는지
    how = pg.locator(".how").inner_text()
    assert "x5 · x10 단일 6장 제외" in how and "PASS 4" not in how                           # x5 만 쓴 단일은 통계에서 무시
    assert "제외 Lot 2개" in how and "이상치" in how
    body = pg.locator("main").inner_text().lower()
    assert "fault" not in body and "배치 기준" not in body and "하루 평균" not in body and "날짜별 생산량" not in body
    pg.locator('[data-fk="rcp:more"]').click()
    pg.wait_for_timeout(300)
    assert "하루 평균" not in pg.locator("main").inner_text() and "날짜별 생산량" not in pg.locator("main").inner_text()
    assert errors == []


def test_rdl_device_row_double_click_opens_detail_popup(rdl_page):
    pg, errors = rdl_page
    pg.locator('button[data-fk="nav:recipe"]').click()
    pg.wait_for_selector('main[data-key="view:recipe"]')
    pg.locator(".dbrow[data-row='dev:AOI-5']").dblclick()
    pg.wait_for_selector('.dlg[data-dlg="rcpdev"]')
    dlg = pg.locator('.dlg[data-dlg="rcpdev"]')
    txt = dlg.inner_text()
    assert "AOI-5" in txt and "TB500 RDL4" in txt and "장(행)별 원자료" in txt and "장비 간 비교" in txt and "이상치 제외" in txt
    assert dlg.locator(".rawrow").count() == 22 + 20 + 19          # 이 기간 AOI-5 의 PASS 장(Error 행 · x5 단일은 없음)
    assert dlg.locator(".rawrow .bad").count() >= 1                    # 이상치로 뺀 장은 붉게
    assert pg.evaluate("document.activeElement && document.activeElement.id") == "dlg-rcpdev-title"
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    assert pg.locator('.dlg[data-dlg="rcpdev"]').count() == 0
    pg.locator('[data-fk="rcp:devpop"]').click()                        # 키보드 · 터치용 단추도 같은 팝업
    pg.wait_for_selector('.dlg[data-dlg="rcpdev"]')
    assert errors == []


def test_day_row_only_where_a_day_is_the_basis_and_range_is_dimmed_then(rdl_page):
    pg, errors = rdl_page
    assert pg.locator('[data-key="daynav"]').count() == 1 and pg.locator(".rangebar.dim").count() == 1      # 가동률: 하루 기준 → 조회 기간은 회색
    for k in ("report", "recipe"):
        pg.locator(f'button[data-fk="nav:{k}"]').click()
        pg.wait_for_selector(f'main[data-key="view:{k}"]')
        assert pg.locator('[data-key="daynav"]').count() == 0 and pg.locator(".rangebar.dim").count() == 0
    pg.locator('button[data-fk="nav:errors"]').click()
    pg.wait_for_selector('main[data-key="view:errors"]')
    assert pg.locator('[data-key="daynav"]').count() == 1 and pg.locator(".rangebar.dim").count() == 1      # Error 일자별
    pg.locator(".rangebar .seg button").first.click()                    # 기간 버튼을 누르면 하루 기준이 풀린다
    pg.wait_for_timeout(300)
    assert pg.locator('[data-key="daynav"]').count() == 0 and pg.locator(".rangebar.dim").count() == 0
    assert errors == []
