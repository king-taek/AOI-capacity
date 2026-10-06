# AOI 화면 개선 handoff — 2026-10-06

## 요약

사용자가 고른 8개 안만 구현한다. 결과 HTML의 표시·문구·상호작용을 다듬으며 기존 배치·테마·애니메이션·계산 규칙을 유지한다. 이 문서는 Codex의 읽기 전용 검토 결과이며 제품 구현은 아직 하지 않았다.

| 우선순위 | 항목 | 최종 선택 | 크기 | 바뀌는 행동 |
|---|---|---|---|---|
| P1 | C1 두 비교 결과의 비중 | B + 쉬운 근거 문구 | S | 전체 장 비교와 같은 장비 비교를 같은 크기로 읽음 |
| P1 | C2 INI·Report 출처 | B − 불필요한 설명 | S | 출처 장 수를 두 칩으로 읽음 |
| P1 | C3 장비별 숫자 | C + 항상 숫자, 같은 높이 | M | 숫자는 항상 보이고 행 선택으로 근거 확인 |
| P1 | C5 계산 근거 | C | M | 여섯 카드의 요약은 항상, 설명만 개별 펼침 |
| P2 | C4 작은 창 | A | M | 현재 열 순서에서 막대·필터·Lot·비교값 잘림 해결 |
| P2 | C6 목록 범위 | A | S | 상위 40개 표시와 전체 검색 범위를 한 줄로 안내 |
| P2 | C7 검색 결과 0개 | C | S | 이전 선택을 작은 요약으로 보관, 검색 지우고 복원 |
| P2 | C8 기간·하루 날짜 | 재검토 A | S | 조회 기간 아래 하루 날짜를 배치, 실제 집계 범위 표시 |

C4의 CSS 부분은 S지만 Lot 이름표를 실제 폭에 맞추는 표시 배치까지 포함하므로 최종 크기는 M이다. 선정안 중 애니메이션 엔진을 고칠 L 작업은 없다.

## 기준·확인한 자료

- 저장소: https://github.com/king-taek/AOI-capacity — `main`.
- handoff 작성 시 다시 확인한 main SHA: `01d26c73c612b28c45933517852754df20010ff6`.
- graphify `GRAPH_REPORT.md`의 `Built from commit`: `01d26c73`. `graph.json.built_at_commit`은 `01d26c73c612b28c45933517852754df20010ff6`; main과 동일하다.
- 화면 원본: `aoi_capacity/ui/assets/template.html`. 첨부 HTML의 사본 script를 제품 코드로 취급하지 않는다.
- 첨부 실데이터: `AOI_capacity_2026-09-21.html`, 버전 `4a6f0bc`, 2026-09-21~2026-10-05, 157,299행. 해당 샘플과 확인한 main의 template 화면 코드가 동일함을 대조했다.
- 순서대로 확인: `CLAUDE.md`, `진행상황.md`, template, `dev/tests/test_dashboard_browser.py`, `dev/tests/test_template_contract.py`, `dev/tests/test_dashboard_js.py`, `docs/design/dashboard-redesign/STATUS.md`; 이전 감사 기록도 참고했다.
- 선택 예시: `AOI_screen_review_ABC_2026-10-06.html`. 최신 예시의 C1~C7과 새 C8 A가 선택 기준이다. 아래 문서에 필요한 조각을 넣었으므로 이 문서만으로 구현할 수 있다.
- 예시의 `DATA`, `DATE_DAYS`, `dateState`, `.du-*`, `layoutPairLabels` 등은 선택용 코드다. 고정된 날짜·수치를 제품에 복사하지 않는다. 아래의 **신규 제안** 식별자와 기존 제품 식별자를 구분한다.

## 사용자 답변 — 원문

### 2단계

1. `화면 지원 범위: PC, 노트북 중심`
2. `같은 비중으로..?`
3. `2`
4. `3`
5. `모르겠어`
6. `1, 다듬고 싶은 부분이 있으면 제안 줘`
7. `1`
8. `전부 다`

확인된 의미: 전체·같은 장비 비교 동일 비중, 핵심 계산 근거 항상 표시·상세 펼침, 상위 40개+전체 검색, 기존 애니메이션·배치 유지. 미정이었던 검색 빈 상태는 3단계에서 C로 정했다.

### 3단계

- C1: `B / 비교 근거를 좀 더 쉽게 이해할 수 있게 쓰면 좋겠어`
- C2: `B / B로 하되 '이 칩은 스캔 시간의 출처입니다. 멀티/단일 판정의 출처와 별도로 표시합니다.' -> 이런 불필요한 텍스트는 없애고 싶어`
- C3: `C / C로 하되 A처럼 숫자 적어줘 숫자는 같은 높이로 적어줘 겹칠것같으면 그냥 양옆으로 적고 조금 띄우면 됨`
- C4: `A`
- C5: `C`
- C6: `A`
- C7: `C`
- C8 최초: `미선택 / 이거는,,, 좀 더 다양하게 생각해봐야할듯 기간도 설정하고 날짜도 설정하고 뭐 그런 경우가 많은데 이거를 어떻게 해야 UX가 좋을까? 사용하기 편하고 헷갈리지 않아야하는데`
- C8 재검토 후 최종: `C8은 A가 낫긴하겠다`
- 공통: `PC·노트북 중심 / 현재 배치 유지 / 전체·같은 장비 비교 동일 비중 / 핵심 계산 근거 항상 표시 / 상세 펼침 / 상위 40개+전체 검색 / 애니메이션 유지`

## 공통 구현 계약

1. 결과 HTML 화면만 수정한다. 수집기·업데이터·`buildModelV3`·`fillModes`·`rcpIndex`·`rcpAgg`의 계산과 데이터 스키마는 유지한다. `rcpAgg`가 `cmpHtml`에도 쓰이므로 표시 개선을 이유로 통계 함수를 고치지 않는다.
2. 외부 요청 0. 새 라이브러리·폰트·CDN 없이 기존 인라인 자원만 사용한다. `translate="no"` 유지.
3. 라이트 토큰 유지: `var(--surface)`, `var(--surface-2)`, `var(--ink)`, `var(--ink-2)`, `var(--ink-3)`, `var(--line)`, `var(--accent-soft)`, `var(--nav-on)`; 글꼴 `var(--sans)`·`var(--mono)`. 멀티/단일/미판정은 `MODE_C.M/S/U`를 사용한다. 테마 상수 변경 없음.
4. 용어 Scan·Rescan·Test·Error·에러 후 대기·대기·가동률·Lot·Wafer·Job·Report 유지. Job/Lot/Wafer 원문을 바꾸지 않는다.
5. `hdr`, `rangebar`, `stage`, 화면별 `view:*`, 기존 `rcp:hero/mdev/how`, 행 `slot:i`를 유지한다. 행을 장비 이름 키로 바꾸거나 이동시키지 않는다. `.rcpscroll`·검색 input도 같은 노드를 유지한다.
6. `render`·`morphChildren`·Flip·`navGo`·`navInd`·`runRolls`·팝업 덱 알고리즘은 변경하지 않는다. 신규 표시 상태·측정은 해당 컴포넌트에 한정한다. 예시 파일의 `innerHTML` 재생성을 제품에 이식하지 않는다.
7. PC 1440×900/1280×800 및 작은 창 820px를 우선 확인하고 390×844 기본 잘림도 확인한다. 탭 줄과 기존 상세 표 내부의 허용된 스크롤은 유지하되 페이지 가로 스크롤로 해결하지 않는다.
8. 입력·선택 시 기존 숫자/글자 변화 규칙 유지. C3 선택 반응은 배경·테두리 160ms, 설명 펼침은 필요하면 해당 설명의 opacity 180ms ease-out만. 반복 sweep·countup·카드 등장·행 이동 없음. reduced-motion에서는 추가 움직임을 끈다.
9. 팝업 inert·Tab trap·ESC·포커스 복원·`POPUP_ORDER` 유지. 신규 C3 근거는 인라인이며 팝업을 추가하지 않는다.

## graphify 호출 관계·같이 바뀌는 곳

아래 `→`는 graph.json의 AST `calls / EXTRACTED`로 확인했다. 동적 팝업 호출과 상태 해석은 소스 직접 대조로 보완했다.

| 대상 | 확인한 호출 관계 | 함께 영향받는 곳·경계 |
|---|---|---|
| C1/2/3/5/6/7 | `render → rcpHtml → rcpIndex/rcpAgg/qs` | 렌더 함수 안의 표현만; 모델 계산 유지 |
| C2 | `rcpHtml → scanRange/modeBar` | 두 helper의 직접 호출자는 현재 `rcpHtml` 하나. 상세·머리·목록의 각각 다른 용도를 구분 |
| C6 | `rcpHtml → rcpFamKey → famIndex` 및 `rcpHtml → jobNm` | family·원문 검색 대상 유지. `jobNm`은 Error·팝업·비교에서도 공유 |
| 비교 | `rcpHtml → cmpHtml → rcpAgg/rcpGroupsOf/jobNm` | C1의 차이 타일과 전후 비교는 별도. C4는 `cmpHtml`의 표시만 |
| C4 홈/Error | `render → homeHtml/errorsHtml`; 둘 다 `→ segHtml` | `segHtml`은 `rangeHtml`, `devPopupHtml`, `recipePopupHtml`도 공유. 전역 seg·rowbtn 변경 금지 |
| C4 장비 팝업 | 소스: `render → popupsHtml → POPUP["dev"]() → devPopupHtml`; `devPopupHtml → ticksHtml/segHtml/reportUrl/openReport` | graph의 동적 `POPUP[k]()`는 직접 dev 호출 edge로 단정하지 않는다. 타임라인·Report 연결·덱 유지 |
| 공유 막대 | `rcpHtml/errorsHtml/errPopupHtml/typePopupHtml → barsHtml` | C2 용어 정정 때문에 `barsHtml` 전체를 변경하지 않는다; recipe가 넘기는 title만 |
| C8 | `render → headerHtml → rangeHtml → rangeOf/setRange/segHtml`; `setRange → setState/render/toast` | 날짜 컨트롤의 배치·범위 표시만. 실제 날짜 선택은 기존 상태·함수에 연결 |

graph 커뮤니티의 모델/레시피(8), 렌더·애니메이션(14), 화면 helper(23), 묶음 편집기(51) 경계를 확인했다. 선정안은 화면 표현·국소 UI 상태에 머문다. 구현 중 엔진 변경이 필요해지면 이 문서 범위를 넘어가는 L 변경으로 분리하여 근거를 보고한다.

## 개선안 C1 — 두 비교 결과의 비중 (P1 · S)

### 화면·지금

- 레시피 오른쪽 `.scanhero .mtile.verdict`, `data-key="rcp:hero"` 내부. `rcpHtml`의 `verdict` 생성부.
- 전체 장 차이는 큰 글자, 같은 장비 차이는 작은 설명이다. 샘플 TB500 RDL4에서 전체는 **단일 5.1분 빠름**, 같은 장비 4대는 **멀티 1.3분 빠름**으로 방향이 달라 작은 설명을 놓치면 오해한다.

### 바꿀 것 — B

- 기존 멀티/단일/차이 3타일 유지. 세 번째 타일 내부에 `범위 / 차이 / 비교 근거` 2행 표를 넣는다.
- 두 결과 모두 20px/700, 범위 12px/600, 근거 11.5~12px/1.6. 어느 결과에도 배지·더 큰 크기로 우선순위를 주지 않는다.
- 한국어 원문:
  - 범위 `전체 장` / 근거 `장비 구분 없이 멀티·단일 장을 각각 모아 비교`.
  - 범위 `같은 장비` / 근거 `장비마다 멀티·단일을 먼저 비교 → {n}대를 합침`.
  - 결과 `{빠른 방식} {차이}분 빠름`; 0차이면 `차이 0.0분`.
- 가중치 설명은 해당 근거의 `title` 및 C5 계산 카드 상세에 `장비별 차이를 합칠 때, 각 장비에서 표본이 적은 방식의 장 수를 가중치로 사용합니다.`로 둔다. 표에 긴 통계 설명을 상시 추가하지 않는다.
- `A.paired`가 없으면 두 번째 행에 `비교 가능한 장비 없음`, 근거 `두 방식 모두 계산 가능한 장이 3장 이상인 장비가 없습니다.`. 시간 중앙값이 없으면 실제 장 수와 구분한다. 한 방식의 PASS만 있으면 `이 기간에는 {방식}만 돌았습니다`; 두 방식 PASS가 있는데 한쪽 시간만 없으면 `{방식}의 계산 가능한 시간이 없습니다`; 둘 다 시간 없음이면 `계산 가능한 스캔 시간 없음`; 양 방식 판정 장이 없으면 `멀티 · 단일을 가릴 근거가 없습니다`. 시간 없음과 그 방식으로 돌리지 않음을 혼동하지 않는다.
- 좁은 타일은 `범위 / 결과` 2열, 근거만 같은 행 아래에 둔다. 페이지 전체 배치는 유지한다. 큰 글자가 안 잘리도록 min-width:0 및 줄바꿈 허용.

### 예시 조각·움직임

```html
<!-- 기존 verdict 타일 안; 모든 값은 기존 mM/mS/A.paired로 생성 -->
<div class="verdict-table">
  <div class="head">범위</div><div class="head">차이</div><div class="head basis">비교 근거</div>
  <div>전체 장</div><div class="result num">단일 5.1분 빠름</div>
  <div class="basis">장비 구분 없이 멀티·단일 장을 각각 모아 비교</div>
  <div>같은 장비</div><div class="result num">멀티 1.3분 빠름</div>
  <div class="basis">장비마다 멀티·단일을 먼저 비교 → 4대를 합침</div>
</div>
```

수치는 예시다. `.verdict-table`은 신규 선택자. 결과 색만 `MODE_C[빠른 방식]`, 표 배경·선은 기존 토큰. 숫자 변경에는 기존 전환을 사용하고 타일 전체 등장 없음.

### 받아들임 기준·가드·결정

1. RDL4에서 반대 방향인 두 결과·단위를 동시에 읽을 수 있고 크기가 같다.
2. paired 없음·한 방식만·값 없음·0차이 각각 사실에 맞는 문구로 표시한다.
3. 390px와 세 번째 타일이 좁은 1280px에서 두 결과·근거가 잘리지 않는다.
4. 기존 `dev/tests/test_dashboard_browser.py::test_recipe_tab_shows_per_device_stats_and_compares_two_periods`의 통계·Job·점 개수·전후 비교 assertion 유지. 차이 타일 문구 assertion은 새 문구에 맞춰 보강한다.
5. 신규 브라우저 가드 제안: `test_recipe_verdict_labels_both_comparison_scopes` — 반대 방향 fixture와 표시 동등성/빈 상태.

D75/D77/D78 유지. `rcpAgg` 가중치·샘플 정의, 기존 멀티/단일 타일, 전후 비교 계산을 건드리지 않는다.

## 개선안 C2 — INI·Report 출처 문구 (P1 · S)

### 화면·지금

`rcpHtml`의 `tile`, `hero`, `devT`, `dot`, `how`, 상세 `cards/rowsH/bars`; `scanRange`의 값 없음 문구. `.scanhero .s/.hint`, `.srows`, `.dbrow .dd[title]`, `.how`, `.rcpdev .rng`, `[data-key="chart:recipe"]`. 기존 키 `rcp:hero/mdev/how/more` 유지.

실제 중앙값은 INI와 Report 보완을 함께 쓰는데 일부 제목·tooltip이 `장당 스캔(INI)`·`INI 장당 중앙`·`INI 시각 없음`으로만 설명한다. RDL4는 1,426장 = INI 1,206 + Report 보완 220이므로 표시 문구를 정정해야 한다.

### 바꿀 것 — B, 불필요한 안내 제거

- 각 방식 타일의 기존 출처 문장을 두 칩으로 정돈: `INI {o.sI.length}장`, `Report 보완 {o.rep}장`.
- 칩은 11.5px, 줄바꿈 가능한 flex, gap 6~7px, 기존 line/surface-2. 판정용 MODE_C 색을 출처별 새 의미로 재사용하지 않는다.
- 기존 `{o.n}장 중 {o.s.length}장으로 계산`·Report가 있으면 `INI만 {중앙}분/장`은 유지한다. INI만 값이 없으면 `INI만 —`; Report만 보완해 계산한 값 자체는 정상 표시한다.
- Report 보완 0도 `Report 보완 0장`으로 표시하고 출처 합계가 계산 장 수와 맞게 한다.
- 혼합 값의 이름은 `장당 스캔`, 설명이 필요하면 `장당 스캔 · INI + Report 보완`. 실제 INI만 집계는 `INI만`으로 구분한다.
- 띠 안내는 `띠 = 장당 스캔 하위 10% ~ 상위 10% · 굵은 눈금 = 중앙`.
- 장비별 부제는 `장당 스캔 중앙(분)`; 점 title은 `{장비} · {방식} {중앙}분/장 · {계산 장 수}장으로 계산 · INI {n} + Report 보완 {n}`.
- 빈 시간 배열은 `계산 가능한 스캔 시간 없음`/`스캔 시간 없음`으로 정리한다. 데이터가 INI 없이 Report로 계산됐을 때 `INI 없음`을 값 없음 의미로 표시하지 않는다.
- C5 시각 카드에서 `위의 큰 숫자 · 띠 · 장비별 점이 모두 이것입니다`를 제거하고 INI+Report 정의에 맞춘다. 상세 표·날짜별 tooltip에도 동일 원칙 적용.
- **삭제**: `이 칩은 스캔 시간의 출처입니다. 멀티/단일 판정의 출처와 별도로 표시합니다.`. 이와 동의어인 상시 해설을 다시 넣지 않는다. 선택 예시의 전체 출처 예시 박스/비율 막대는 문구 비교용이며 제품에 중복 추가하지 않는다.

```html
<div class="scan-source-chips">
  <span class="scan-source-chip">INI <b class="num">981장</b></span>
  <span class="scan-source-chip">Report 보완 <b class="num">130장</b></span>
</div>
<!-- 기존 계산 장 수·INI만·배치 기준 줄은 아래 유지 -->
```

신규 칩 선택자만 추가. 클릭 기능 없음, hover/등장 애니메이션 없음.

### 받아들임 기준·가드·결정

1. 혼합·INI만·Report만·시간 없음의 4 fixture에서 출처와 값 설명이 일치한다.
2. RDL4 전체 1,426=1,206+220, 멀티 1,111=981+130이 맞고 기존 중앙값은 바뀌지 않는다.
3. 선택한 방식·기간·장비에 해당하는 출처를 표시하며 판정 출처 수와 혼동해 더하지 않는다.
4. 기존 recipe 브라우저 테스트는 출처 표현 assertion 보강; 통계 assertion 유지. 신규 `test_recipe_wording_distinguishes_ini_and_report_time` 제안.
5. `dev/tests/test_dashboard_js.py::test_unjudged_rows_take_the_mode_of_their_report_or_the_nearest_report`와 `test_product_model_invariants_hold_on_the_30_day_sample`은 변경 없이 통과해야 한다.

D77/D78 유지. `scanRange`는 현재 recipe 전용이지만 `.srows`·상세 tooltip 등 모든 recipe 호출 위치를 확인한다. 공유 `barsHtml`·`jobNm`·모델은 변경하지 않는다.

## 개선안 C3 — 장비 행 선택 + 항상 숫자 (P1 · M)

### 화면·지금

`rcpHtml`의 `dv/devH/dot/near/side/devT`; `.dbrow .dtrack/.dd/.dlab.M/.dlab.S/.dx/.dc`; 컨테이너 `rcp:mdev`, 행 `slot:i`, `data-row="dev:{장비}"` 유지.

RDL4 AOI-23 멀티 12.8/단일 12.6처럼 가까운 라벨이 기존 near 비율 판정으로도 겹친다. 사용자 최종안은 **C의 근거 확인 + 숫자는 항상·같은 높이·좌우 분리**다. A의 상하 2층 배치는 선택하지 않았다.

### 바꿀 것

- 점·연결선·축·dmx·중앙값·장비 정렬 유지. 모든 유효 M/S 수치가 항상 표시된다. 점이 없으면 해당 라벨 없음; 둘 다 없으면 `스캔 시간 없음`.
- 숫자 top 25px, line-height 16px, 최소 font-size 10.5px, `.num`. 같은 행의 M/S 라벨 y값은 같다.
- 같은 값도 두 방식의 숫자를 합치지 않는다. 겹치면 값이 작은 쪽 라벨을 왼쪽, 큰 쪽을 오른쪽으로 보내며 최소 10px 간격. 같은 값은 M 왼쪽/S 오른쪽. **점 위치를 바꾸지 않는다**.
- near를 통계 축의 비율로만 판단하지 않는다. 실제 track 폭·현재 글꼴의 라벨 `getBoundingClientRect().width`로 계산하고 track 양끝으로 clamp한다. 리사이즈·검색·기간·묶음 변경 후 다시 맞춘다.
- 행 클릭/Enter/Space로 선택. 위·아래 레이아웃 이동 없이 옅은 배경·테두리 표시; 비교 행 아래 고정된 인라인 근거 영역에 장비·M/S 중앙·`{계산 장 수}장으로 계산 / PASS {전체 장 수}장`·각 INI/Report 수를 표시한다.
- mouse hover 또는 행 키보드 focus로 임시 근거를 보여주고, 떠나면 고정 선택으로 돌아간다. 기본은 첫 유효 행; 선택한 장비가 필터/기간에서 빠지면 남은 첫 행, 남은 행 없으면 `기록 없음`.
- 신규 UI 상태(예: `state.rcpDevSel`, 제안 이름)는 화면 표시용이다. `slot:i` 선택 표시를 고정 장비명에 매달지 말고 현재 `data-row`와 상태로 판정한다.
- 신규 근거 키 예: `rcp:mdev:detail`. 기존 `.dbrow.head/.axis`는 클릭 대상 제외. 실제 행만 `button` 또는 동등한 keyboard/ARIA 지원. 기존 slot 태그를 div→button으로 바꾸더라도 이후 렌더 간 동일 노드가 유지되게 한다.

### 선택 예시의 핵심 코드 — 제품 선택자에 맞춰 이식

```css
/* rcp:mdev 내부로 한정; dot/axis 계산을 변경하지 않음 */
[data-key="rcp:mdev"] .dbrow:not(.head):not(.axis) .dtrack{height:46px}
[data-key="rcp:mdev"] .dlab.M,
[data-key="rcp:mdev"] .dlab.S{top:25px;line-height:16px}
```

라벨 배치 절차: `center = pointPercent × trackWidth`; `left = clamp(center − labelWidth/2)` → x순 정렬 → 두 사각형 사이가 10px보다 작으면 두 점의 중간을 기준으로 `leftLabel.right=mid−5`, `rightLabel.left=mid+5` → 두 라벨을 함께 좌우 이동해 track 안에 넣는다. 숫자가 track보다 길 정도의 비정상적으로 작은 폭은 C4의 최소 track 폭 확보로 처리한다. 라벨을 감추거나 숫자를 줄여 가짜 값으로 만들지 않는다.

DOM 측정 helper는 recipe에 한정하고 requestAnimationFrame 한 번으로 묶는다. 초기 표시·현재 track 크기 변화만 관찰하고 자기가 쓴 style 때문에 반복 실행하지 않도록 한다. 기존 렌더 엔진을 재작성하거나 전체 화면 Flip을 추가할 이유는 없다.

### 받아들임 기준·가드·결정

1. 1440/1280/820/390px에서 AOI-23 두 숫자 y값이 같고 사각형 간격 ≥10px, track 밖으로 나가지 않는다.
2. 동일 값·0근처·축 끝·한 방식만·세 자리 수·글꼴 로드/브라우저 125% 확대도 확인한다.
3. 행을 hover/focus/선택하면 해당 행의 출처·장 수가 맞고 떠나면 고정 선택이 복원된다. Tab/Enter/Space 사용 가능.
4. 기간/검색/묶음 변경 시 선택 내용과 행 데이터가 함께 갱신되고 낡은 장비 근거가 남지 않는다.
5. 기존 recipe 브라우저 테스트의 `.dbrow .dd` 개수·순서·계산 assertion 유지. `test_render_morphs_in_place_instead_of_rebuilding`은 변경 없이 유지하고 recipe 행에도 노드 동일성 보강.
6. 신규 `test_recipe_close_point_labels_do_not_overlap`, `test_recipe_device_row_selection_shows_matching_provenance` 제안.

D75/D77 유지. C2와 문구를 같이 맞추며 분모 `d[k].n`와 계산 장 수 `d[k].s.length`를 구분한다. 모델·축·점·정렬·애니메이션 엔진은 건드리지 않는다.

## 개선안 C5 — 여섯 계산 카드 개별 펼침 (P1 · M)

### 화면·지금

`rcpHtml`의 `how/exT/bxT`, `.how .howgrid`, 키 `rcp:how`. 현재 여섯 칸에 긴 설명이 모두 노출돼 숫자를 찾기 어렵다.

### 바꿀 것 — C

- 위치·여섯 개 개념 유지: `장`, `INI · Report`, `배치`, `Lot`, `판정`, `계산`.
- 각 카드를 `details`로 만들고 **제목·핵심 값·출처/제외 요약은 summary 안**에 넣는다. summary 다음에 값을 두면 닫혔을 때 숨겨지므로 금지한다.
- 기본 닫힘, 카드마다 독립적으로 펼침. 제목 12px/600, 주요 값 18px/700, 출처·짧은 요약 11.5px. 기존 표면·선·반경을 사용.
- 항상 보이는 요약:
  - 장: `PASS {a.w}장` + `멀티 {a.M.n} · 단일 {a.S.n}` 및 필요한 미판정 수.
  - 시각: `{a.s.length}장으로 계산` + `INI {a.sI.length} + Report 보완 {a.rep}`; `WaferStartTime → WaferEndTime`; 못 채운 장이 있으면 `{n}장 시간 없음`.
  - 배치: `Lot {a.b.length}개로 계산` + `Batch Start → Batch End`; `제외 Lot {합계}개`.
  - Lot: `Lot {a.lots.size}개` + `Report 한 장 = 배치 한 번`.
  - 판정: `멀티 {M} · 단일 {S} · 판정 못 함 {U}` + `그 장 INI {n} · 같은 Report {a.mr} · 가까운 Report {a.mn}`. 긴 줄은 줄바꿈.
  - 계산: `중앙값 · 시간당 60 ÷ 중앙` + `같은 장비 {A.paired.n}대 비교` 또는 `같은 장비 비교 근거 없음`.
- 펼친 내용에는 기존 PASS/Test/중복 제외 규칙, Report 시간 배분, 실제 제외 이유 `exT/bxT`, 판정 추정 순서, 가중치 정의를 남긴다. C2에서 지적한 INI만이라는 오해 문구는 정정.
- 펼침 상태는 family별·카드별 국소 UI 상태(신규 제안 `rcpHowOpen`)로 관리. 현재 family의 무관한 클릭·날짜/값 재렌더에 접히지 않으며 다른 family에 상태가 섞이지 않는다. 새 localStorage 설정을 만들지 않는다.

```html
<details class="how-item" data-key="how:time">
  <summary>
    <span class="hk">INI · Report · 자세히</span>
    <span class="how-value num">1,426장으로 계산</span>
    <span class="how-summary">INI 1,206 + Report 보완 220</span>
    <span class="how-summary">WaferStartTime → WaferEndTime</span>
  </summary>
  <div class="how-explain">기존 계산 설명을 C2의 출처 표현에 맞춰 배치</div>
</details>
```

위 설명 영역에는 기존 계산 설명 본문을 옮기며 작업용 placeholder를 화면에 넣지 않는다. 신규 `.how-item/.how-value/.how-summary/.how-explain`, `how:wafer/time/batch/lot/mode/calc` 키를 제안한다. `.howgrid>div` 규칙을 카드에 맞게 국소 조정한다.

### 움직임·받아들임 기준·가드·결정

- native details로 설명 영역만 열고 필요하면 opacity 180ms ease-out. 카드 전체 재등장·고정 큰 height 애니메이션 없음. reduced-motion에서는 즉시.
1. 닫힌 6카드에서 핵심 수치·두 시각 필드·출처를 읽을 수 있다.
2. 하나를 열어도 다른 카드가 자동으로 닫히지 않는다; Tab/Enter/Space 지원.
3. 실제 제외 사유·숫자가 보존되고 열림 상태가 같은 family의 재렌더에서 유지된다.
4. 390px에서는 한 열, summary/원문 필드가 잘리지 않는다.
5. 기존 recipe 브라우저 테스트의 `9장`, `WaferStartTime`, `Batch Start` 검증 유지; 여섯 카드 open/close assertion 보강. `test_render_morphs_in_place_instead_of_rebuilding` 유지.
6. 신규 `test_recipe_how_summary_and_details_are_accessible` 제안. 렌더 속성 갱신이 `open`을 지우지 않도록 UI 상태와 HTML 속성을 동기화한다.

D75/D77/D78 유지. 계산 helper·데이터 수·상세 보기 Job 선택·전후 비교는 변경하지 않는다.

## 개선안 C4 — 작은 창의 열 너비 보정 (P2 · M)

### 화면·지금

홈의 고정 inline grid, Error `.row2` 안의 고정 inner grid, 장비 팝업의 `W=880` 기준 Lot 이름표, `.cmp .cmprow`의 min 열 너비가 작은 창에서 실제 내용을 밀거나 잘라낸다. page scrollWidth가 맞더라도 버튼/숫자 실제 bbox는 밖에 나갈 수 있다.

### 바꿀 것 — A

- 현재 열 순서 유지. 타임라인을 다음 줄로 내리는 B나 내용을 세로 카드로 바꾸는 C는 구현하지 않는다.
- 홈 `homeHtml`: `.homelist .rowbtn`의 inline `grid-template-columns`/gap을 제거·축소할 수 있게 scoped CSS로 옮긴다. `.thead`도 같은 열 계약. 마지막 chevron 포함 **5열** 유지. 모든 shrinkable 셀 min-width:0.
- ≤820px 시작값: `58px 44px minmax(90px,1fr) 48px 18px`, gap 6px, padding 9px 12px. ≤420px: `54px 38px minmax(80px,1fr) 38px 14px`, gap 4px, padding 9px 10px. 실제 장비 원문이 길면 기존 ellipsis/title 유지. 단위 포함 숫자는 숨기지 않는다.
- 홈의 `ticksHtml`을 좁은 창에서 0/12/24만 표시하되 **home 내부 축에 한정**. 팝업·다른 날짜 축을 전역 변경하지 않는다.
- Error `errorsHtml`: outer `.row2`는 `minmax(0,1fr) 34px`, rowbtn 각 이름/건수/시간/chevron 열의 fixed 폭·gap을 좁은 화면에서 줄인다. `.fbtn`은 30~34px 그대로 확보. 이름만 ellipsis/title, 건수·시간·필터는 가려지지 않게. 유형·장비·Job 세 목록 모두 확인.
- Lot `devPopupHtml`: 현재 raw title·클릭·hits·줄기·선택·D10 fold 유지. 이름표의 실제 컨테이너 폭을 측정해 `labelWidth`, left, height와 lane 간격을 계산한다. `left∈[0,containerWidth−labelWidth]`; 긴 이름표는 해당 컨테이너 안에서 줄바꿈, 최대 width 100%. height가 늘면 lane y 및 calloutH도 따라 늘려 다음 줄·선택 원문과 겹치지 않는다. `W=880`, `ROW=26`을 작은 창에서도 고정 px처럼 사용하지 않는다. 원문은 기존 title·선택 상자에서 확인 가능.
- `cmpHtml`: `.cmp .cmprow:not(.dev)`는 작은 창에서 이름의 min-width를 0으로, A/B/변화 값 영역 확보. 예시처럼 변화의 값과 %는 같은 셀 안 두 줄 허용. 장비별 7열 비교는 기존 표 내부 스크롤을 허용해 수치를 보존하며 페이지를 넘치게 하지 않는다. 계산/방향/색은 그대로.

```css
@media(max-width:820px){
  .homelist .rowbtn,.homelist .thead{
    grid-template-columns:58px 44px minmax(90px,1fr) 48px 18px;
    gap:6px;
  }
  main[data-key="view:errors"] .errlist .row2{
    grid-template-columns:minmax(0,1fr) 34px;
  }
  main[data-key="view:errors"] .errlist .rowbtn{min-width:0}
  .cmp .cmprow:not(.dev){
    grid-template-columns:minmax(0,1fr) 44px 44px minmax(70px,1fr);gap:5px;
  }
}
```

이 조각의 수치들은 출발점이며 acceptance를 충족하도록 실제 font/폭으로 검증한다. 적용 전에 기존 inline grid가 scoped CSS를 덮지 않게 정리해야 한다. 신규 전역 `.rowbtn/.seg/.fbtn` override로 해결하지 않는다.

### 관련 키·움직임·받아들임 기준

- 홈/Error `slot:i`·`data-row`, Lot `data-fk="lot:{key}"`·callout 부모 `data-sig`, 비교 `slot:i/dslot:i` 유지. Lot 위치 변화는 해당 popup의 표시 배치이며 덱/Flip 엔진 변경 없음.
1. 1280/820/390px 및 125% 확대에서 페이지 scrollWidth≤viewport, 필터 버튼·단위 포함 숫자의 bbox가 안에 있다.
2. 홈 24시간 막대 폭 ≥80px(390), 0/12/24가 충돌하지 않는다. 장비 순서·sort·층/장비 종류 필터 유지.
3. 긴 Error 원문과 긴 Lot fixture에서 버튼 클릭 가능, 원문은 title/선택 상자에 보존된다.
4. Lot 줄바꿈 시 이름표·지시선·후속 선택 상자끼리 겹치지 않고 Report 열기와 포커스 계약 유지.
5. 비교 A/B/변화/%가 읽히고 표 내부 스크롤과 페이지 스크롤을 구별한다.
6. 기존 `test_narrow_viewport_has_no_horizontal_page_scroll`을 네 탭·팝업으로 보강하고 신규 `test_narrow_dashboard_controls_and_labels_stay_visible` 제안. `test_floor_and_maker_filters_are_picked_separately`, `test_device_popup_focus_inert_tab_trap_and_escape_return`, `test_stackbar_stays_top_left_while_the_popup_scrolls_and_lot_panel_fades_in_once`는 계약 유지.

D29/D10/D72/D76/D77 유지. 팝업 이름표 최초 등장 1회·원문·Lot fold/hits·기존 비교 의미를 건드리지 않는다. 예시의 합성 타임라인/비교값을 제품 데이터로 넣지 않는다.

## 개선안 C6 — 상위 40개와 전체 검색 안내 (P2 · S)

### 화면·바꿀 것

`rcpHtml`의 `fam/list/hitQ/listH`, `.rcplist` 검색 바로 아래에 한 줄 추가한다. `[data-fk="rcp:q"]`, `.rcpscroll`, `.rcprow[data-key="slot:i"]` 유지.

지금 `list.slice(0,40)`인데 표시 한도 안내가 없어 337개 중 일부만 있는 것으로 보인다. **검색 대상은 현재 조회 기간에 존재하는 모든 family의 표시명+원문 Job**이며 다른 기간까지 확장하지 않는다.

- 검색 없음: `생산량 상위 {표시 수}개 / 전체 {기간 내 family 수}개 · 전체 검색 가능`.
- 검색 있음: `검색 결과 {결과 수}개 · {표시 수}개 표시`.
- 검색 결과 >40: 뒤에 `상위 40개` 추가.
- 0개: `검색 결과 0개`; C7의 빈 상태와 연결.
- total은 Q필터 **전** `fam.size`, match는 필터 후 `list.length`, shown은 `Math.min(40,list.length)`. 전체 검색이 보관 cache/NAS 전체 검색이라는 문구를 쓰지 않는다.
- 글자 11.5px, 기존 ink-3, padding 7~8px 12px. 긴 줄은 줄바꿈. 별도 버튼·페이지 이동·더보기 없음.

```js
// rcpHtml 표시 코드의 제안 조각; 기존 hitQ/sort/slice 순서는 유지
const total = fam.size, matched = list.length, shown = Math.min(40, matched);
const listNotice = !Q
  ? `생산량 상위 ${shown}개 / 전체 ${total}개 · 전체 검색 가능`
  : `검색 결과 ${matched}개 · ${shown}개 표시${matched>40?' · 상위 40개':''}`;
```

### 받아들임 기준·가드·결정

1. 샘플 기본 `상위 40개 / 전체 337개`, 40개 밖 원문 Job로 검색해 결과를 찾는다.
2. 기간을 줄이면 total도 해당 기간 기준으로 바뀐다. 검색 중/0개/>40개 문구가 맞는다.
3. 원문 검색·family 묶음·생산량 순서·멀티/단일 한 줄 계약 유지.
4. 기존 `test_recipe_group_of_multi_job_still_shows_single_on_the_same_row` 유지, recipe 브라우저 테스트 보강. 신규 `test_recipe_list_limit_is_disclosed_and_search_is_not_limited` 제안.

D75/D77 및 사용자 Q4 유지. `famIndex/jobNm`·원문·조회 기간·계산은 변경하지 않는다. 안내만 즉시 갱신하고 새 등장 연출 없음.

## 개선안 C7 — 검색 0개면 이전 선택 요약 (P2 · S)

### 화면·지금

`rcpHtml`의 `hitQ/list/SF/detail/cmpSel`, `.rcplist .empty`, 오른쪽 상세 영역. 기존 검색이 0개여도 이전 상세가 남아 검색 결과처럼 보인다.

### 바꿀 것 — C

- Q가 있고 list.length===0인 경우만 오른쪽 상세를 작은 빈 상태+이전 선택 요약으로 바꾼다.
- 첫 문장 `검색 결과가 없습니다`.
- 이전 선택이 있으면 `이전 선택` 라벨 + 원래 표시명 + `멀티 {중앙} / 단일 {중앙}분/장`, 버튼 `검색 지우고 이전 상세로`.
- 원래 상세의 긴 카드·차트·계산 설명은 이때 숨긴다. query와 이전 선택을 별개 UI 상태로 보존한다. 검색 전 자동 첫 행 선택이었던 경우도 마지막 실제 표시 family를 보관한다.
- 버튼은 query만 비우고 기존 family 상세로 돌아간 뒤 `[data-fk="rcp:q"]`에 focus. 검색·계산·비교 묶음을 초기화하지 않는다.
- 이전 family가 새 조회 기간에서 사라졌으면 남아 있다고 표시하지 않는다. `이 기간에는 이전 선택의 기록이 없습니다` + `검색 지우기`. 이전 선택 자체가 없으면 요약 없이 `검색 지우기`.
- Q가 없고 기간 자체에 family가 0이면 `이 기간에 맞는 레시피가 없습니다`; 이전 기간 수치를 같은 기간 값으로 보여주지 않는다.
- Q 결과가 1개 이상인 경우의 현재 선택 규칙은 유지한다. C7을 이유로 검색 때마다 첫 행을 강제 선택하지 않는다.
- 전후 비교는 별도 기존 영역 그대로. 기존 A/B 묶음·날짜는 보존하고 실제 추가 대상 `cmpSel`이 없으면 ＋ 추가를 만들지 않는다.

```html
<div class="panel recipe-empty" data-key="rcp:empty-detail">
  <h3>검색 결과가 없습니다</h3>
  <div class="recipe-retained">
    <span class="muted">이전 선택</span>
    <p><b>TB500 RDL4</b> · 멀티 17.1 / 단일 12.0분/장</p>
    <button class="btn" data-fk="rcp:clear">검색 지우고 이전 상세로</button>
  </div>
</div>
```

신규 이름·키는 제안이다. 오른쪽 wrapper에 고정 `rcp:detail` 키를 두어 내부 빈 상태만 바뀌게 하고 좌측 input/list·main은 유지한다. 대체 정보는 기존 집계에서만 얻는다. 큰 exit/enter 애니메이션 없음.

### 받아들임 기준·가드·결정

1. RDL4 선택→없는 검색어 입력 시 0개 안내와 이전 요약만 보인다.
2. 복원 버튼→검색어 빈칸·RDL4 원래 상세·검색 focus, 펼침/비교 상태 유지.
3. 자동 초기 선택→0개, 이전 선택 없음, 기간 변경으로 이전 family 없음 각각 올바른 상태.
4. 빠른 연속 검색에도 원문·수치가 이전 family와 맞으며 input 노드/selection을 유지한다.
5. 기존 recipe/morph 브라우저 테스트는 계약 유지. 신규 `test_recipe_no_match_clearly_identifies_retained_or_empty_detail` 제안.

D75/D77 유지. `rcpIndex/rcpAgg`·Job 묶음·비교 그룹·검색 원문 범위를 변경하지 않는다.

## 개선안 C8 — 조회 기간 아래 하루 날짜 (P2 · S)

### 화면·지금

`headerHtml/rangeHtml/rangeOf/setRange`, `.hdr .rangebar/.daynav/.daylab`, `hdr/rangebar` 키. 기존 입력 키 `range:vf`, `range:vt`, `day:prev`, `day:next` 유지.

상단 기간과 하루 이동이 나란히 있어 어느 조작이 어느 탭에 적용되는지 혼동된다. 최종은 **재검토 A: 두 줄·기간 아래 하루**다. 최초 C8 A와 새 재검토 A를 혼동하지 않는다.

### 바꿀 것

- 브랜드·4탭·Lottie 그대로. 날짜 조작 영역 안 1행 `조회 기간`: `최근 7일 / 1달 / 전체` + `시작`/`끝` 입력 + `{n}일`.
- 바로 아래 2행 `하루 날짜`: ‹ / 날짜 / › / 최신. 하루 날짜는 클릭·키보드로 date input을 쓸 수 있게 하고 min/max를 실제 `D.days` 첫날/끝날로 제한한다. 입력한 날짜가 `D.days`에 없으면 기존 날짜를 유지하고 짧게 안내한다. `.daylab`은 날짜 input의 wrapper로 남기고 기존 plain 날짜와 input을 중복 표시하지 않는다. 기존 부분 날짜 표시도 보존한다.
- 사본 저장·레시피 묶음·수집 시각은 기존 action 영역에 유지; 두 날짜 라벨과 섞지 않는다. 탭 줄 좁은 화면 이동 계약 유지.
- 라벨 12px/600, date input 기존 `.inp` 크기(약128px), gap 6~8px. 390px는 label과 입력 그룹이 자연스럽게 줄바꿈; 시작/끝은 구별 가능.
- `rangeHtml`은 현재 `data-key="rangebar"`다. `hdr/rangebar`라는 slash 합성 키를 새로 만들지 않는다. 하루 영역에는 필요하면 신규 `data-key="daynav"`를 넣되 기존 `.daylab`을 제거하지 않는다.
- 기간은 기존 `rangeOf/setRange`에 연결한다. 최근/최신은 열람 날짜가 아니라 HTML의 데이터 끝날 기준(D40). 1달 선택 시 가능한 날짜만 보이는 현재 동작 유지.
- 기존 하루가 새 기간 안이면 유지, 밖이면 새 `D.days` 마지막 날. 바뀐 경우만 짧은 role=status로 `하루 날짜 {이전} → {새 날짜}`. 누를 때마다 장문 설명/새 toast 없음.

### 범위·상태 계약 — 소스와 맞춰 구현

| 조작/화면 | 실제 상태·표시 |
|---|---|
| 가동률 | `S.dayStr()` 하루. 제목 옆 `{MM/DD} 하루` |
| Error 일자별 | `state.pickDay===undefined ? S.dayStr() : state.pickDay`의 유효 하루. 제목 옆 그 날짜 `하루` |
| Error 기간 전체 | `pickDay===null`, `D.days` 전체. 제목 옆 `{시작} ~ {끝} · {n}일` |
| TB500 · Kendall / 레시피 | `D.days` 기간 전체. 제목 옆 `{시작} ~ {끝} · {n}일`; 하루 입력 옆 짧게 `가동률 · Error 일자별에서 사용` |
| ‹/›/최신/하루 input | `dayI` 및 현재와 같이 `pickDay:undefined`. Error에서 날짜를 직접 고르면 **일자별로 전환**되는 기존 동작 유지, 범위 배지도 즉시 하루로 |
| Error 날짜 막대 선택 | 기존 같은 막대 재클릭→기간 전환 유지. 일자 선택 시 `dayI`를 그 날과 맞춰 헤더 날짜·Error 표시가 어긋나지 않게 함 |
| 탭 왕복 | 기간·하루·기존 Error 모드 유지. 날짜 선택이 recipe/report 통계를 하루로 바꾸지 않음 |
| 전후 비교 | 기존 `cmpAf/At/Bf/Bt`, `cmpA/B` 독립. 조회 기간 밖 비교도 현재 허용 유지 |
| 데이터 없는 기간 | 기존 `그 기간에는 데이터가 없습니다` 동작, 이전 기간·하루 유지 |

선택 예시는 날짜 조작 관계를 보여주는 조각이다. 제품에서는 Error의 실제 `pickDay`·막대 선택 계약을 우선하여 위처럼 동기화한다. 새 global 일/기간 모드나 전후 비교 기간의 자동 연결은 추가하지 않는다.

```html
<!-- 기존 hdr 안의 날짜 영역; data-in/data-h는 제품 handler를 사용 -->
<div class="date-controls">
  <div class="date-control-row">
    <b>조회 기간</b><div><!-- 기존 rangeHtml(), key rangebar 유지 --></div>
  </div>
  <div class="date-control-row" data-key="daynav">
    <b>하루 날짜</b>
    <div class="daynav"><!-- 기존 ‹ .daylab › 최신 + 하루 date input --></div>
  </div>
</div>
```

신규 `.date-controls/.date-control-row`, 하루 input `data-fk="day:date"`는 제안 이름. init의 date change 위임에서 하루 input을 별도로 처리하고 `INPUT_KEYS`의 범용 text input 처리에 섞지 않는다. 하루를 고를 때 `setRange(day,day)`로 기간까지 줄이지 않는다.

### 움직임·받아들임 기준·가드·결정

- 헤더·`.daylab`의 기존 전환 유지, 탭 표시자 물리 모델·nav 감시 유지. 날짜 조작마다 헤더/뷰 재등장 없음. 신규 안내는 즉시·reduced-motion 동일.
1. 전체→09/25 하루→최근7일: 기간09/29~10/05, 하루10/05 및 이동 안내. 10/02 선택→전체: 하루10/02 유지.
2. 직접 하루 입력·‹/›·최신 모두 기간 안 데이터 날짜만 선택, 1일 기간이면 두 화살표 disabled.
3. 가동률→recipe/report→가동률 왕복 시 기간/하루 유지, 각 배지가 실제 내용의 범위를 설명한다.
4. Error 기간 전체→하루 입력은 일자별 전환을 분명히 표시. Error 막대09/30 선택 시 헤더도09/30; 같은 막대 재클릭은 기간 전체로, 기간은 유지.
5. 전후 비교를 다른 두 기간으로 고른 후 헤더 하루 이동에도 A/B 날짜·그룹 유지. 빈 기간·역순 입력의 기존 처리 유지.
6. 기존 `test_header_period_limits_every_tab_to_the_chosen_days` 보강, `test_tab_indicator_survives_in_tab_clicks_and_follows_the_tab`·`test_tab_indicator_moves_like_a_body_dragged_by_its_front` 유지. 신규 `test_date_controls_keep_day_inside_the_visible_period`, `test_error_day_selection_matches_the_header_date` 제안.

D40/D72/D76 유지. 기준시각·기간 필터 계산·비교 기간·데이터 모델·수집기 기간 기능을 변경하지 않는다.

## 가드 테스트 실행·보강표

아래의 신규 이름은 **아직 저장소에 없는 제안 이름**이다. 구현자가 `dev/tests/test_dashboard_browser.py`에 추가한다. 기존 테스트 이름/계산 assertion을 무작정 완화하거나 삭제하지 않는다.

| 파일 | 기존 테스트 | 작업 |
|---|---|---|
| `dev/tests/test_dashboard_browser.py` | `test_recipe_tab_shows_per_device_stats_and_compares_two_periods` | C1/2/3/5/6/7 표현 assertion 보강. 값·Job·점 수·상세·전후 비교 유지 |
| 동일 | `test_recipe_group_of_multi_job_still_shows_single_on_the_same_row` | 변경 없이 유지 |
| 동일 | `test_render_morphs_in_place_instead_of_rebuilding` | 기존 계약 유지 + recipe/header/input/details 노드 동일성 보강 |
| 동일 | `test_narrow_viewport_has_no_horizontal_page_scroll` | 네 탭·장비 팝업·비교·820/390으로 보강; 실제 bbox 검증 별도 |
| 동일 | `test_home_rows_follow_device_order_and_save_copy_refolds_the_same_columns` | 변경 없이 유지, 원문·데이터 불변 |
| 동일 | `test_floor_and_maker_filters_are_picked_separately` | 변경 없이 유지 |
| 동일 | `test_header_period_limits_every_tab_to_the_chosen_days` | C8 범위·하루 유지/복귀·날짜 없는 기간 보강 |
| 동일 | `test_tab_indicator_survives_in_tab_clicks_and_follows_the_tab` / `test_tab_indicator_moves_like_a_body_dragged_by_its_front` | 변경 없이 유지 |
| 동일 | `test_error_tab_period_popup_filters_and_no_total_link` / `test_error_lists_keep_rows_in_place_and_only_text_changes` | Error 모드·필터·행 노드 계약 유지; 새 날짜 동기화 assertion 보강 |
| 동일 | `test_device_popup_focus_inert_tab_trap_and_escape_return` / `test_popups_stack_behind_each_other_and_escape_closes_the_top` | 변경 없이 유지 |
| 동일 | `test_motion_hooks_lottie_countup_sweep_and_recede` / `test_stackbar_stays_top_left_while_the_popup_scrolls_and_lot_panel_fades_in_once` | 변경 없이 유지 |
| `dev/tests/test_template_contract.py` | `test_no_network_use_at_all` / `test_vendor_block_makes_no_requests_either` / `test_vendored_libraries_are_inline_with_their_notices` | 변경 없이 유지 |
| 동일 | `test_browser_never_reads_the_nas_itself` / `test_light_only_theme` / `test_screen_terms_are_the_design_terms_and_old_ones_are_gone` | 변경 없이 유지 |
| 동일 | `test_removed_features_stay_removed` / `test_no_period_over_period_comparison_anywhere` / `test_no_view_clock_in_the_model_section` | 변경 없이 유지 |
| 동일 | `test_the_dialogs_have_accessible_names` / `test_links_to_new_tabs_have_no_opener` | 변경 없이 유지 |
| `dev/tests/test_dashboard_js.py` | `test_product_model_invariants_hold_on_the_30_day_sample` / `test_multi_and_single_scans_are_different_jobs_but_the_same_material` | 변경 없이 계산 계약 유지 |
| 동일 | `test_unjudged_rows_take_the_mode_of_their_report_or_the_nearest_report` / `test_recipe_tab_leaves_kla_out` / `test_error_tab_leaves_kla_out` | 변경 없이 유지 |
| 동일 | `test_header_has_four_tabs_and_each_popup_renders_an_accessible_dialog` / `test_floor_and_maker_filters_combine` | 변경 없이 유지 |

### 검증 순서

1. 표현 변경별 위의 신규 브라우저 fixture/acceptance를 작성한다. 근접값·양방향 차이·Report만·40개 밖 검색·0개 복원·날짜 경계에 실제 실패 가능성을 검증한다.
2. 기존 recipe/browser/template/model 가드를 실행한다. Chromium 설치 등 저장소의 기존 실행 절차를 따른다.
3. 선택 예시와 같은 09/21~10/05 실데이터 HTML을 **고친 template로 재생성**하여 1440/1280/820/390, reduced-motion, 외부 HTTP 요청0/JS 오류0을 확인한다. 기존 샘플 파일을 고쳐 구현 완료로 삼지 않는다.
4. Windows Chrome/Edge의 Segoe UI/Malgun Gothic, 100%/125% 확대, 팝업 덱/Report 열기 실제 현장 경로를 최종 확인한다.
5. main과 graph 기준이 바뀌었으면 실제 구현 기준 SHA를 기록하고 관련 소스·가드를 재대조한다. graphify 산출물을 main에 넣지 않는다.

## 고르지 않은 것·나중에

- C1 A/C, C2 A/C 및 중복 출처 설명 박스, C3 수치 hover 전용·상하 2층 라벨·고정 수치 열, C4 B/C, C5 A/B, C6 B/C, C7 A/B는 구현하지 않는다.
- C8 최초 3안과 재검토 B(통합 달력)/C(날짜 띠)는 구현하지 않는다. 헤더 날짜 이동 잠금도 선택하지 않았다.
- 다크·추가 탭·새 라이브러리·전 기간 자동 비교·수집/업데이트 최적화는 범위 밖.

## 데이터·규칙 질문 / 확인 범위

새로 사용자에게 확인받아야 할 계산 변경은 없다. C1의 반대 방향은 비교 범위가 다른 사실을 보여줄 뿐 레시피 효과를 단정하지 않는다. C2는 표시 문구 정정이며 D78 통계 규칙 변경이 아니다.

`app.log` 마지막 HTML 생성 기록은 2026-10-06 12:59:39, 버전4a6f0bc, 09/21~10/05, 157,299행으로 첨부와 일치했다. 생성 구간 12:59:35.828~12:59:39.056은 약3.23초이며 **브라우저 로딩 시간은 아니다**. 로그에 브라우저 클릭/렌더 계측은 없으므로 UI 검증을 대체하지 않는다.

Codex가 확인한 것은 원본 화면 동작, graph/source/test 계약, 선택 예시의 Chromium 동작이다. 첫 예시 검증 127개, C1~C7 수정 및 새 C8 검증 71개에서 외부 HTTP 요청/JavaScript 오류가 없었다. 이는 **제품 패치 테스트 통과를 의미하지 않는다**. NAS Report의 실제 내용은 이 환경에서 열지 못했으며 현장 확인이 필요하다.

Codex는 저장소에 쓰기·커밋·푸시·PR·이슈·코멘트를 하지 않았다. 이 handoff 전달은 배포/머지 승인과 별개다.
