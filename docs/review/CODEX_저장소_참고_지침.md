# AOI 화면 검토 — 저장소 · graphify 참고 지침 (Codex 용, 보조 문서)

> 먼저 받은 `CODEX_화면검토_지침.md`(4단계: 둘러보기 → 질문 → 예시 3개 → handoff)를 그대로 따르되,
> **첨부 HTML 만 보지 말고 아래 저장소와 코드 지도를 함께 참고**하세요. 목적은 두 가지입니다.
> ① 이미 사용자가 정한 것(결정 D01~D78)을 거스르는 제안을 하지 않기 ② handoff 에서 고칠 위치를 **함수 · 선택자 · 가드 테스트 이름**으로 정확히 가리키기.

## 1. 저장소

- GitHub: **`king-taek/AOI-capacity`** — https://github.com/king-taek/AOI-capacity
- 기준 브랜치: **`main`** (현장 PC 자동 업데이트가 이 브랜치의 CI 통과 커밋을 받아 감)
- **읽기만** 하세요. 커밋 · 푸시 · PR · 이슈 · 코멘트 금지. 구현은 handoff 를 받은 Claude Code 가 합니다.
- 첨부 HTML 은 수집기가 `aoi_capacity/ui/assets/template.html` 에 데이터(`__DATA__` 자리)를 끼워 만든 것입니다. **화면 코드의 원본은 template.html 하나**이고, 첨부 HTML 의 `<script>` 는 그 사본입니다. 첨부 HTML 머리의 `v<sha7>`(바닥글) 로 어느 커밋에서 만들어졌는지 확인하고, main 이 그보다 앞서 있으면 main 기준으로 판단하세요(최근 커밋 몇 개는 레시피 탭을 바꿨습니다).

## 2. 먼저 읽을 파일 (이 순서)

| 순서 | 파일 | 무엇을 얻나 |
|---|---|---|
| 1 | `CLAUDE.md` | 절대 규칙 · 화면 구조 · 애니메이션 원칙(“틀은 그대로, 내용만”) · 색 · 용어의 정본. 특히 '화면 구조' · '레시피 탭' · '화면 기간' 절 |
| 2 | `진행상황.md` | **확정된 결정 표(D01~D78)** — 사용자가 직접 정한 것. 여기에 반하는 제안은 하지 말고, 바꾸고 싶으면 '질문' 으로. `## 작업 기록` 맨 위 몇 줄이 최근 변화 |
| 3 | `aoi_capacity/ui/assets/template.html` | 화면 전부(CSS · 렌더 함수 · 모델). 아래 3절의 함수 지도로 찾아 들어가세요 |
| 4 | `dev/tests/test_dashboard_browser.py` | Chromium 클릭 경로 테스트 — 지금 화면이 **어떻게 동작해야 하는지**의 실제 계약 |
| 5 | `dev/tests/test_template_contract.py` · `test_dashboard_js.py` | 깨면 안 되는 가드(바깥 요청 0 · 용어 · 제거된 기능이 돌아오지 않기 · 애니메이션 규칙 등) |
| 6 | `docs/design/dashboard-redesign/STATUS.md` | 9/19 디자인 시안과 지금 제품의 차이 — 시안으로 되돌리자는 제안을 피하기 위해 |
| 참고 | `docs/review/` · `docs/audit/` · `docs/history/` | 지난 검토 · 감사 기록 — 이미 다뤄진 지적인지 확인 |

계산 규칙(가동률 · Error · Rescan · INI 시각 · 멀티/단일 판정)은 `CLAUDE.md` '결과 화면 모델' 절과 template 의 `buildModelV3` · `fillModes` · `rcpIndex` 에 있습니다 — **검토 범위 밖**이지만, 화면 문구가 규칙을 틀리게 설명하고 있다면 그건 지적하세요.

## 3. graphify 코드 지도

main 에 푸시될 때마다 GitHub Actions(`.github/workflows/graphify.yml`)가 코드 지도를 다시 만들어 **`graphify-out` 브랜치**에 올립니다(커밋 하나로 덮어씀, main 에는 들어가지 않음).

- 위치: https://github.com/king-taek/AOI-capacity/tree/graphify-out
  - `GRAPH_REPORT.md` — 요약 · 커뮤니티(묶음)별 허브. **여기부터** 읽으세요
  - `graph.json` — 노드(파일 · 함수 · 클래스) · 엣지(호출 · import · 포함), 신뢰도 표시(EXTRACTED / INFERRED)
  - `graph.html` · `GRAPH_TREE.html` — 브라우저로 여는 그래프 · 트리 보기
- **template.html 의 인라인 JS 함수도 들어 있습니다**(`dev/tools/graphify_build.py` 가 `<script>` 를 잠깐 `_template_inline.js` 로 빼서 분석) — 그래프에서 파일 이름이 `_template_inline.js` 로 보이는 노드가 화면 함수입니다.
- 신선도: `GRAPH_REPORT.md` 의 `Built from commit:` 이 main 의 최신 SHA 와 같은지 확인하세요. 다르면 아래로 직접 만들어도 됩니다(API 키 · 네트워크 불필요, AST 만):
  ```
  pip install "graphifyy[sql]"
  python dev/tools/graphify_build.py --out <임시 폴더>     # 저장소 안에 쓰지 않도록 임시 폴더 지정
  ```

### graphify 로 할 일
1. 개선 후보마다 **그 화면을 그리는 함수**를 찾고(예: 레시피 탭 → `rcpHtml`), 그 함수를 **누가 부르고 무엇을 부르는지** 엣지로 확인 → handoff 의 '관련 함수' 와 '같이 바뀌는 곳' 에 적기.
2. 같은 CSS 클래스 · 도우미(`barsHtml` · `segHtml` · `modeBar` · `scanRange` · `jobNm` 등)를 여러 화면이 같이 쓰는지 확인 → 한 화면만 고치려다 다른 화면이 바뀌는 제안이면 그 사실을 적기.
3. 커뮤니티 묶음으로 "화면 렌더 · 애니메이션 엔진(morph · Flip · navGo) · 모델 · 수집기" 경계를 파악하고, **애니메이션 엔진 쪽 변경**이 필요한 제안은 크기를 L 로 표시.

## 4. 화면 함수 지도 (template.html, 빠른 진입점)

| 화면 | 함수 | 비고 |
|---|---|---|
| 머리 · 기간 · 바닥글 | `headerHtml` · `rangeHtml` · `footHtml` | 탭 표시자 `navInd`/`navGo`(물리 모델, WAAPI) |
| 가동률 탭 | `homeHtml` | 24시간 막대 `segHtml` · `S.segsOf`, 목록은 순위 칸 `data-key="slot:i"` |
| 장비 팝업 | `devPopupHtml` | Lot 이름표 · 'Report 열기' `reportUrl`/`openReport` |
| Error 탭 · 팝업 | `errorsHtml` · `errPopupHtml` · `typePopupHtml` | 글자 넘김 `txAnim` · 21일 막대 끌기 `data-drag="errwin"` |
| TB500 · Kendall | `reportHtml` | 정렬 `rptSort`, 펼침 `data-reveal` |
| 레시피 탭 | `rcpHtml` · `cmpHtml` · `rcpIndex` · `rcpAgg` · `famIndex` | 최근 개편(D77 · D78) — 중점 검토 |
| 레시피 묶음 팝업 | `recipePopupHtml` | localStorage `aoi.recipeGroups.v1` |
| 팝업 덱 | `popupsHtml` · `stackbarHtml` · `layoutDeck` · `liftFront` | `POPUP_ORDER` 고정, z-index 겹침 |
| 렌더 엔진 | `render` · `morphChildren` · `flipAfter` · `enterView` · `runRolls` | 바꾸면 전 화면에 영향 |

## 5. handoff 에 추가로 적을 것

`CODEX_화면검토_지침.md` 4단계 형식에 아래를 더하세요.

- 각 개선안의 **관련 함수 · CSS 선택자 · data-key** (graphify 로 확인한 호출 관계 포함)
- **영향 받는 가드 테스트**(파일 · 테스트 이름)와, 그 테스트를 **바꿔야 하는지 / 새로 필요한지**
- 관련 결정 번호(예: “D77 유지 — 가동률 줄 없음”, “D72 헤더 기간과 충돌 없음”)
- 기준 커밋: handoff 를 쓸 때 본 main SHA 와 graphify 의 `Built from commit`

## 6. 하지 말 것 (추가)
- 저장소에 쓰기(커밋 · 브랜치 · PR · 이슈 · 코멘트)
- `graphify-out` 브랜치나 산출물을 main 에 넣자는 제안(업데이터가 main SHA 를 보므로 헛 업데이트가 생김)
- 수집기(`aoi_capacity/collect.py` 등) · 업데이터 변경 제안 — 이번 범위는 결과 HTML 화면
