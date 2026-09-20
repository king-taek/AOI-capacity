"""결과 HTML(template.html) 의 **제품 제약** — 자바스크립트를 실행하지 않고 글자로만 보는 것은 여기까지다(S05, 9/20).

이 파일 한 장은 사용자가 **더블클릭해서 여는 화면**이다. 글자 검사로 지키는 것은 다음뿐이다:
- 데이터는 `__DATA__` 자리 하나에 박힌다 · 바깥으로 나가는 요청(폰트·스크립트·fetch)이 한 건도 없다 · 브라우저가 NAS 를 읽는 경로가 없다
- 라이트 단일 테마 · 화면 용어(Scan · Rescan · Test · Error · 에러 후 대기 · 대기)와 금지 용어·금지 기능(옛 추정 코드 · 전 기간 대비 · 열람 시계 · 옛 상수)
- 분류 정규식이 파이썬·디자인 스크립트와 글자까지 같다(D43) · 모델 구간에 열람 시계(`Date.now`/`new Date`)가 없다(D40)
- 팝업 셋에 접근 가능한 이름이 있다(D05) · 새 탭으로 여는 링크는 `noopener`

**동작**은 글자가 아니라 실행으로 본다 — 예전에 여기 있던 JS 원문 일치 검사와 그 의도를 이어받은 테스트:

| 없앤 글자 검사(옛 이름) | 의도 | 지금 그 의도를 보는 테스트 |
|---|---|---|
| `test_entry_points_the_app_and_user_need` (`function loadDemo(` 등 8개 이름) | 로더·모델·저장·Report 열기 진입점이 있다 | `test_dashboard_js.py` 하네스가 `unfold`·`buildModel` 을 실제로 부른다 · `::test_report_url_…` · `::test_home_…collect_chips…` · `test_dashboard_browser.py::test_home_rows_follow_device_order_and_save_copy_refolds…`(사본 저장 내려받기) |
| `test_model_has_a_product_profile_and_a_legacy_profile…` (`const RULES={…}` 원문 · 함수 조각 8개 · `MODEL_VERSION=3`) | 기본 프로필은 product 이고 네 스위치가 켜져 있다, legacy 는 디자인 스크립트와 같다 | `test_dashboard_js.py::test_default_profile_is_product_with_the_four_rules_on_and_constants_match` · `::test_legacy_profile_equals_the_design_script_on_the_30_day_sample`(slow) · D40 은 이 파일 `test_no_view_clock_in_the_model_section` |
| `test_four_tabs_and_the_three_popups` (nav 배열 원문 · 함수 이름 7개) | 4탭 · 3팝업이 열린다 | `test_dashboard_js.py::test_header_has_four_tabs_and_each_popup_renders_an_accessible_dialog` · `test_dashboard_browser.py::test_error_popup_type_popup_trend_and_report_tab` |
| `test_report_tab_follows_d49` (`const MIN_N=5;` · `L[12]-L[11]` · JOB_ALIAS 줄 수) | 표본 5개 미만은 회귀를 내지 않고 Error 배치는 제외, 표기명 21개 | `test_dashboard_js.py::test_report_tab_regresses_only_with_five_or_more_clean_batches_and_lists_exclusions` · `::test_default_profile_…constants_match`(JOB_ALIAS 21개 = 디자인 `job_alias.js`) |
| `test_p4_screen_items_are_present` (D59 h1 · `noRec(t){…}` · `lotKey` 원문 · D14 `applySettings` · D08 · D05 `.inert=`) | 기록 없음 분리 · Lot 선택 키에 Report · 설정 덮어쓰기 · 접근성 | `test_dashboard_js.py::test_home_…no_record_count` · `::test_lot_key_separates_two_reports…` · `::test_dashboard_settings_override_the_attention_thresholds` · `test_dashboard_browser.py::test_device_popup_focus_inert_tab_trap_and_escape_return` · 금지 식별자는 이 파일 `test_removed_features_stay_removed` |
| `test_error_popup_shows_the_text_of_each_type…` (`causeText(…)` 호출 원문) | 한 Lot 에 유형이 둘이면 줄마다 그 유형의 원문 | `test_dashboard_js.py::test_error_popup_shows_each_types_own_phrase_when_one_lot_has_two_types` |
| `test_home_cards_sort_with_cmp_dev_not_alphabetically` (`sorted.sort((a,b)=>cmpDev(…))`) | 홈 목록은 AOI-1…25 뒤에 4F(사전순 아님) | `test_dashboard_js.py::test_home_…` (AOI-2 → AOI-10 → 4F) · `test_dashboard_browser.py::test_home_rows_follow_device_order…` |
| `test_report_opens_only_through_a_file_url_built_from_meta` (`devPath(r.device)` · `file:///` · `encodeURIComponent`) | Report 경로는 meta.devices[].note + report_dir + report 로만, 드라이브·UNC | `test_dashboard_js.py::test_report_url_is_built_only_from_meta_for_drive_and_unc_paths`; `noopener` 는 이 파일 `test_links_to_new_tabs_have_no_opener` |
| `test_scope_notice_and_collect_status_are_rendered_from_meta` (`devStatus[d.name]=` 등) | 수집 범위 · 수집 안 함 · 수집 실패 · 일부 누락 칩 | `test_dashboard_js.py::test_home_…collect_chips…` · `::test_foot_shows_scope_and_out_of_scope_devices_from_meta` |
| `test_embedded_string_pool_is_unfolded_on_load_and_refolded_on_save` (로더·`saveHtml` 원문) | 풀 번호 범위 밖·열 중복은 예외, 사본은 같은 열·풀 구조 | `test_dashboard_js.py::test_unfold_rejects_out_of_range_pool_index_and_duplicate_columns` · `test_dashboard_browser.py::…save_copy_refolds_the_same_columns` |
| `test_light_only_theme_but_qt_tokens_stay` 의 토큰 색 정규식 | 수집 창이 읽는 `:root` 토큰 두 블록 | `test_theme.py`(theme.py 가 실제로 파싱) |
"""
from __future__ import annotations

import re
from pathlib import Path

import template_facts
from aoi_capacity.utils import paths

HTML = paths.template_path().read_text(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[2]
DESIGN = ROOT / "docs" / "design" / "dashboard-redesign"
MODEL_START, SCREEN_START = "/* ---------- ③ 모델", "/* ---------- ④ 화면"


def test_data_placeholder_present_once():
    assert HTML.count("__DATA__") == 1


_VENDOR = re.compile(r'<script id="vendor">.*?</script>', re.S)
_ALLOWED_VENDOR_URL = re.compile(r"https?://(?:gsap\.com|www\.w3\.org/(?:2000/svg|1999/xhtml|1999/xlink))(?:[/\w.-]*)")


def _without_vendor(html: str) -> str:
    """제3자 라이브러리(GSAP+Flip · animate.css 일부)를 **인라인**으로 싣는다 — 그 라이선스 머리말의 홈페이지 주소와
    SVG/XHTML 네임스페이스 문자열은 요청이 아니다. vendor 블록과 `/*! … */` 머리말을 걷어내고 나머지에서 네트워크 흔적을 찾는다."""
    html = _VENDOR.sub("", html)
    return re.sub(r"/\*!.*?\*/", "", html, flags=re.S)


def test_no_network_use_at_all():
    body = _without_vendor(HTML)
    for bad in ("fetch(", "api.github.com", "fonts.googleapis.com", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket", "import(",
                "<script src=", '<link rel="stylesheet"', "http://", "https://"):
        assert bad not in body, bad
    assert HTML.count("<script") == 3, "embedded JSON · 인라인 라이브러리(vendor) · 화면 스크립트 — 셋뿐"


def test_vendor_block_makes_no_requests_either():
    """vendor 블록(GSAP·Flip)도 요청 API 를 쓰지 않고, 안에 든 주소는 라이선스·네임스페이스뿐이다."""
    m = _VENDOR.search(HTML)
    assert m, "vendor 블록이 없다"
    v = m.group(0)
    for bad in ("fetch(", "XMLHttpRequest", "navigator.sendBeacon", "new WebSocket", "import(", "<script src=", "document.write("):
        assert bad not in v, bad
    urls = re.findall(r"https?://[^\s\"')]+", v)
    assert urls and all(_ALLOWED_VENDOR_URL.fullmatch(u.rstrip(".")) for u in urls), sorted(set(urls))


def test_vendored_libraries_are_inline_with_their_notices():
    """GSAP(+Flip) 와 animate.css 일부를 파일 안에 그대로 싣는다 — 라이선스 머리말을 지우지 않는다."""
    assert '<script id="vendor">' in HTML
    for notice in ("GSAP 3.", "Subject to the terms at https://gsap.com/standard-license", "Flip 3.", "animate.css", "MIT"):
        assert notice in HTML, notice


def test_browser_never_reads_the_nas_itself():
    """★ 수집은 Python 수집기만 한다 — 브라우저 폴더 API 경로는 남아 있지 않다."""
    for bad in ("showDirectoryPicker", "getDirectoryHandle", "getFileHandle", "collectAll",
                "indexedDB", "queryPermission", "nasList"):
        assert bad not in HTML, bad


def test_light_only_theme():
    """D48-⑥ 라이트 단일. 수집 창이 읽는 `:root` 토큰 블록의 값은 test_theme.py 가 실제로 파싱해서 본다."""
    assert '<html lang="ko" data-theme="light">' in HTML
    assert "setTheme(" not in HTML and "prefers-color-scheme: dark" not in HTML


def test_status_classification_matches_the_python_side_and_the_design_script():
    """★ 같은 Report 를 파이썬·브라우저·디자인 스크립트가 다르게 읽으면 안 된다 — 정규식 문자열과 순서가 글자까지 같다(D43).
    문구별 분류 결과가 같은지는 test_status_mapping.py 가 213문구로 실행해 본다."""
    from aoi_capacity import collect

    assert template_facts.rules("CAUSE_RULES", HTML) == [(c, p) for c, p in collect._CAUSE_RULES]
    assert template_facts.rules("OUTCOME_RULES", HTML) == [(c, p) for c, p in collect._OUTCOME_RULES]
    design = (DESIGN / "scripts" / "make_aoi_data.js").read_text(encoding="utf-8")
    assert template_facts.rules("CR", design) == [(c, p) for c, p in collect._CAUSE_RULES]


def test_no_view_clock_in_the_model_section():
    """D40: 집계는 수집 시각(meta.generated_iso)만 본다 — 모델 구간에 열람 시계가 없다. 값이 맞는지는 test_dashboard_js 의 D57 테스트."""
    body = template_facts.section(HTML, MODEL_START, SCREEN_START)
    assert "Date.now()" not in body and "new Date()" not in body
    assert "generated_iso" in body
    assert isinstance(template_facts.model_version(HTML), int)


def test_screen_terms_are_the_design_terms_and_old_ones_are_gone():
    """D48-⑦: Scan · Rescan · Test · Error · 에러 후 대기 · 대기. 옛 화면 용어는 JS 에 남지 않는다."""
    for term in (">Scan<", ">Rescan<", ">Test<", ">Error<", ">에러 후 대기<", ">대기<"):
        assert term in HTML, term
    for gone in ("중복스캔", "재스캔", "재작업", "미가동", "정지(추정)", "DISPLAY_META", "metricState", "materialIndex", "occurrenceIndex"):
        assert gone not in HTML, gone


def test_removed_features_stay_removed():
    """옛 장비-일 추정(D15) · PyQt GUI 모드 · 옛 업데이트 상수 · '수집 예정' 자리표시(D08) · 열람 시각 문구(D11)는 돌아오지 않는다."""
    for gone in ("isEst(", "estBar(", "showRepeat", "mEst", "ABORT.test(",
                 "data-gui", 'Q.get("gui")', "btnRunTop", "UPDATE_BASE=",
                 "수집 예정", "열람 시각 기준", "현재까지", "00:00 ~ 현재"):
        assert gone not in HTML, gone


def test_no_period_over_period_comparison_anywhere():
    for gone in ("deltaHtml", "prevKeys", "이전 기간", "이전 주", "이전 월", "전일 대비", "전주 대비", "class=\"delta"):
        assert gone not in HTML, gone


def test_today_basis_wording_is_last_record_not_now():
    assert "마지막 기록" in HTML and "수집 기준" in HTML and "수집 시각 정보 없음" in HTML   # D11: 수집 시각이 없으면 24시간 분모


def test_the_three_dialogs_have_accessible_names():
    """D05: 팝업은 role=dialog · aria-modal · 제목 id(aria-labelledby) 를 갖는다. 포커스가 실제로 그리 가는지는 browser 테스트."""
    assert HTML.count('role="dialog"') == 3
    assert HTML.count('aria-modal="true"') == 3
    assert sorted(re.findall(r'aria-labelledby="(dlg-[a-z]+-title)"', HTML)) == ["dlg-dev-title", "dlg-err-title", "dlg-type-title"]
    for t in ("dlg-dev-title", "dlg-err-title", "dlg-type-title"):
        assert f'id="{t}"' in HTML, t


def test_links_to_new_tabs_have_no_opener():
    """Report 는 사람이 연 그 탭이 연다 — 새 탭에 이 화면의 opener 를 주지 않는다."""
    n = HTML.count('target="_blank"') + HTML.count('a.target="_blank"')
    assert n >= 1 and n == HTML.count('rel="noopener"') + HTML.count('a.rel="noopener"')


def test_readme_and_settings_help_follow_the_confirmed_rules():
    from aoi_capacity.i18n import ko

    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
    for bad in ("이전 기간 비교", "현재 시각까지", "통째로 건너뜁니다", "50% 미만이면"):
        assert bad not in readme, bad
        assert bad not in ko.SET_UTIL_DEFINITION and bad not in ko.DEV_PAGE_HELP, bad
    assert "Rescan" in ko.SET_UTIL_DEFINITION and "마지막 기록" in ko.SET_UTIL_DEFINITION
    assert "TB500 · Kendall" in readme and "Rescan" in readme and "not slow" in readme
