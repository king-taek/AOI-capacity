"""결과 HTML(template.html) 계약 — 자바스크립트를 실행하지 않고 문자열로만 검사한다(실행 검사는 test_dashboard_js.py).

이 파일 한 장은 사용자가 **더블클릭해서 여는 화면**이다. 그래서
- 데이터는 `__DATA__` 자리에 박혀 들어가고,
- 바깥으로 나가는 요청(폰트·스크립트·fetch)이 한 건도 없어야 하며,
- 브라우저가 NAS 를 직접 읽는 경로(폴더 API)는 없어야 한다(수집은 Python 수집기만 한다).
D47·D48(9/20) 로 화면은 재설계 구조(가동률 · Error · 추이 · 리포트 + 팝업, 라이트 단일)다.
"""
from __future__ import annotations

import re
from pathlib import Path

from aoi_capacity.utils import paths

HTML = paths.template_path().read_text(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs" / "design" / "dashboard-redesign"


def test_data_placeholder_present_once():
    assert HTML.count("__DATA__") == 1


def test_no_network_use_at_all():
    for bad in ("fetch(", "api.github.com", "fonts.googleapis.com", "XMLHttpRequest",
                "<script src=", '<link rel="stylesheet"', "http://", "https://"):
        assert bad not in HTML, bad


def test_browser_never_reads_the_nas_itself():
    """★ 수집은 Python 수집기만 한다 — 브라우저 폴더 API 경로는 남아 있지 않다."""
    for bad in ("showDirectoryPicker", "getDirectoryHandle", "getFileHandle", "collectAll",
                "indexedDB", "queryPermission", "nasList"):
        assert bad not in HTML, bad


def test_no_pyqt_gui_mode_left():
    for bad in ('data-gui', 'Q.get("gui")', "btnRunTop"):
        assert bad not in HTML, bad


def test_entry_points_the_app_and_user_need():
    for fn in ("function loadDemo(", "function buildModel(", "function cmpDev(", "function saveHtml(",
               "function reportUrl(", "function openReport(", "function collectChip(", "function unfold("):
        assert fn in HTML, fn


def test_light_only_theme_but_qt_tokens_stay():
    """D48-⑥ 라이트 단일. 다만 수집 창(ui/theme.py)이 읽는 `:root{}`(dark) 와 `:root[data-theme="light"]{}` 토큰 블록은 남는다."""
    assert '<html lang="ko" data-theme="light">' in HTML
    assert re.search(r":root\{[^}]*--accent:#4A9EE8", HTML) and re.search(r':root\[data-theme="light"\]\{[^}]*--accent:#2E6BA8', HTML)
    assert "setTheme(" not in HTML and "prefers-color-scheme: dark" not in HTML


def _js_rules(text, name):
    body = text[text.index(f"const {name}="):]
    body = body[:body.index("];") + 1]
    return re.findall(r'\["([A-Z_]+)",/(.*?)/i\]', body)


def test_status_classification_matches_the_python_side_and_the_design_script():
    """★ 같은 Report 를 파이썬·브라우저·디자인 스크립트가 다르게 읽으면 안 된다 — 정규식 문자열과 순서가 글자까지 같다(D43)."""
    from aoi_capacity import collect

    assert _js_rules(HTML, "CAUSE_RULES") == [(c, p) for c, p in collect._CAUSE_RULES]
    assert _js_rules(HTML, "OUTCOME_RULES") == [(c, p) for c, p in collect._OUTCOME_RULES]
    design = (DESIGN / "scripts" / "make_aoi_data.js").read_text(encoding="utf-8")
    assert _js_rules(design, "CR") == [(c, p) for c, p in collect._CAUSE_RULES]
    assert "const causeOf=t=>{const x=String(t||\"\").trim();for(const[c,rx]of CAUSE_RULES)if(rx.test(x))return c;return null;};" in HTML


def test_model_has_a_product_profile_and_a_legacy_profile_equal_to_the_design_script():
    """D47·D56: 제품 프로필(buildModelV3)이 기본이고, legacy 프로필은 make_aoi_data.js 이식 그대로(디자인 동일성 가드 전용)."""
    assert 'const RULES={profile:"product",waitToObsEnd:true,denomToday:true,abortIsError:true,estimateFromBatch:true};' in HTML
    assert 'return rules.profile==="legacy"?buildModelLegacy(rowsIn,metaIn,rules):buildModelV3(rowsIn,metaIn,rules);' in HTML
    body = HTML[HTML.index("const MON="):HTML.index("/* ---------- ④ 화면")]
    for frag in ("function lotName(rep,fb,tableFirst)", "function jobKey(s)", "const JM={\"RKENDALLPI4DG\":\"RKENDALLA0PI4\"};",
                 "function buildModelV3(", "function buildModelLegacy(", "function dayStats(list,ds)", "if(gap>240)gap=240;",
                 "const RT=new Set(['RE','RESCAN','REWORK','SRD','R']);", "const K_NONE=0,K_ERR=1,K_SCAN=2,K_RESCAN=3,K_TEST=4,K_WAIT=5;"):
        assert frag in body, frag
    assert "Date.now()" not in body and "new Date()" not in body          # D40: 집계에 열람 시계 없음
    assert "generated_iso" in body and "MODEL_VERSION=3" in HTML


def test_screen_terms_are_the_design_terms_and_old_ones_are_gone():
    """D48-⑦: Scan · Rescan · Test · Error · 에러 후 대기 · 대기. 옛 화면 용어는 JS 에 남지 않는다."""
    for term in (">Scan<", ">Rescan<", ">Test<", ">Error<", ">에러 후 대기<", ">대기<"):
        assert term in HTML, term
    for gone in ("중복스캔", "재스캔", "재작업", "미가동", "정지(추정)", "DISPLAY_META", "metricState", "materialIndex", "occurrenceIndex"):
        assert gone not in HTML, gone


def test_four_tabs_and_the_three_popups():
    for frag in ('["home","가동률"],["errors","Error"],["trend","추이"],["report","TB500 · Kendall"]',   # D59: 리포트 → TB500 · Kendall
                 "function homeHtml(", "function errorsHtml(", "function trendHtml(", "function reportHtml(",
                 "function typePopupHtml(", "function devPopupHtml(", "function errPopupHtml("):
        assert frag in HTML, frag
    assert HTML.count('role="dialog"') == 3


def test_report_tab_follows_d49():
    body = HTML[HTML.index("function reportHtml("):HTML.index("/* ---------- boot")]
    assert "const MIN_N=5;" in body and "L[12]-L[11]" in body          # 표본 5개 미만 제외 · 배치 시작~종료
    assert len(re.findall(r'^\s*"[^"]+":"[^"]+"(?:,|\};)$', HTML[HTML.index("const JOB_ALIAS={"):HTML.index("const PROPS=")], re.M)) == 21


def test_p4_screen_items_are_present():
    """개선 계획 P4(9/20): D59 탭 이름·안내, D06 기록 없음 분리, D16 선택 키에 Report, D15 옛 추정 코드 제거, D05 접근성, D10 표 가로 스크롤, D14 설정 덮어쓰기, D08 평균 fault."""
    assert "<h1>TB500 · Kendall</h1>" in HTML and "개 Job 만 봅니다" in HTML                    # D59
    assert "noRec(t){return S.util(t)===null;}" in HTML and "기록 없음 ${q.no}대" in HTML       # D06·D57
    assert 'const lotKey=L=>L[0]+"|"+L[1]+"|"+L[2]+"|"+(L[11]||0)+"|"+(L[8]||0);' in HTML      # D16
    for gone in ("isEst(", "estBar(", "showRepeat", "mEst", "ABORT.test("):                     # D15·D08
        assert gone not in HTML, gone
    assert HTML.count('aria-labelledby="dlg-') == 3 and "function trapTab(e)" in HTML and ".inert=" in HTML   # D05
    assert 'class="panel" style="overflow-x:auto"' in HTML                                     # D10
    assert "function applySettings(m)" in HTML and "dashboard_settings" in HTML                 # D14
    assert "faults" in HTML and "평균 fault" in HTML and "수집 예정" not in HTML                 # D08
    assert "열람 시각 기준" not in HTML                                                          # D11: 열람 시계는 어디에도 없다


def test_error_popup_shows_the_text_of_each_type_not_the_lot_representative():
    """같은 Lot 에 유형이 둘이면(30일치 175 Lot) 줄마다 그 유형의 원문 — 모델의 `st` 는 Lot 당 하나라 화면이 로드한 행에서 유형별로 찾는다."""
    assert "function causeText(dev,rep,c)" in HTML
    assert 'status:causeText(eDev,P.rep[L[8]]||"",c)||(L[10]>=0?P.st[L[10]]:"(원문 없음)")' in HTML


def test_home_cards_sort_with_cmp_dev_not_alphabetically():
    assert "localeCompare" not in HTML
    assert "sorted.sort((a,b)=>cmpDev(a.n,b.n))" in HTML


def test_report_opens_only_through_a_file_url_built_from_meta():
    body = HTML[HTML.index("function reportUrl("):HTML.index("function openReport(")]
    assert "devPath(r.device)" in body and 'file:///' in body and "encodeURIComponent" in body
    assert 'data-h="${h(()=>openReport({device:mDev,report:rep}))}"' in HTML          # 장비 팝업의 Report 줄
    assert "a.target=\"_blank\";a.rel=\"noopener\"" in HTML


def test_scope_notice_and_collect_status_are_rendered_from_meta():
    assert "meta.scope" in HTML and "수집 범위" in HTML and "수집 안 함" in HTML
    assert 'if(d.status)devStatus[d.name]=' in HTML
    assert 'status==="unreachable"' in HTML and "수집 실패" in HTML
    assert 'status==="partial"' in HTML and "일부 누락" in HTML
    assert ".st.warn{" in HTML


def test_embedded_string_pool_is_unfolded_on_load_and_refolded_on_save():
    from aoi_capacity import collect

    assert "const P=emb.pool||null,F=new Set(emb.pooled||[]);" in HTML
    assert "if(P&&F.has(c)){const v=P[a[i]];if(v===undefined)throw" in HTML          # D09: 풀 번호 범위 밖은 빈 문자열로 숨기지 않는다
    assert set(collect.POOLED_COLS) < set(collect.OUT_COLS)
    body = HTML[HTML.index("function saveHtml("):HTML.index("/* ── 렌더 ── */")]
    assert '"device","lot","wafer_id"' not in body          # 열을 손으로 고르지 않는다
    assert "embCols" in body and "embPooled" in body and "pooled,pool,rows" in body
    assert "embCols=emb.cols.slice()" in HTML


def test_no_period_over_period_comparison_anywhere():
    for gone in ("deltaHtml", "prevKeys", "이전 기간", "이전 주", "이전 월", "전일 대비", "전주 대비", "class=\"delta"):
        assert gone not in HTML, gone


def test_today_basis_wording_is_last_record_not_now():
    for bad in ("현재까지", "00:00 ~ 현재"):
        assert bad not in HTML, bad
    assert "마지막 기록" in HTML and "수집 기준" in HTML and "수집 시각 정보 없음" in HTML   # D11: 수집 시각이 없으면 24시간 분모, 열람 시계는 쓰지 않는다


def test_no_stale_update_base_constant():
    assert "UPDATE_BASE=" not in HTML


def test_readme_and_settings_help_follow_the_confirmed_rules():
    from aoi_capacity.i18n import ko

    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
    for bad in ("이전 기간 비교", "현재 시각까지"):
        assert bad not in readme, bad
        assert bad not in ko.SET_UTIL_DEFINITION, bad
    assert "Rescan" in ko.SET_UTIL_DEFINITION and "마지막 기록" in ko.SET_UTIL_DEFINITION
    assert "리포트" in readme and "Rescan" in readme
