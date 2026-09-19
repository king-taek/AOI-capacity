# AOI Capacity 결과 화면 재설계 — 핸드오프

이 폴더 하나로 Claude Code 에서 이어서 작업할 수 있습니다.
`PROMPT.md` 의 내용을 그대로 붙여넣고 시작하세요.

## 이 작업이 무엇인가

`king-taek/AOI-capacity` 의 **결과 화면**(`aoi_capacity/ui/assets/template.html` → 수집 시 만들어지는
`AOI_capacity.html`)을 전면 재설계했습니다. 수집기(PyQt6) 쪽은 건드리지 않았고,
INI 누락 문제를 조사하며 **수집기 수정안**을 별도로 정리해 뒀습니다.

사용자 요구의 핵심:
- 다크 모드 폐기, **라이트 단일 테마**
- 처음엔 중요한 것만, **클릭으로 점점 깊이** 들어가는 구조
- 글자 줄이기, 어려운 용어 쉬운 말로
- 가동률 막대를 읽을 수 있게

## 폴더 구성

```
HANDOFF.md                     이 파일
PROMPT.md                      Claude Code 에 붙여넣을 프롬프트
CHANGELOG.md                   지금까지의 요청과 반영 내역
RULES.md                       화면이 따르는 계산 규칙 (가장 중요)
AOI 가동 현황 (오프라인).html   ★ 더블클릭하면 바로 열립니다 (819KB, 외부 요청 0)
app/
  AOI-Dashboard.dc.html        본체 — 가동률 · Error · 추이 3탭 + 팝업
  AOI-Dashboard-offline.dc.html  오프라인 빌드의 원본 (데이터를 aoi-data.js 로 읽음)
  aoi-data.js                  aoi-data.json 을 window.AOI_DATA 로 감싼 것
  Err-Popup-A.dc.html          승인된 Error 상세 팝업 시안 (미반영)
  AOI-4 해결 제안.dc.html       수집기 수정 제안서 (검증 결과 포함)
  support.js                   DC 런타임 (수정 금지)
  aoi-data.json                화면이 읽는 데이터 (31일 × 30대)
  aoi-recovery.json            제안서가 읽는 검증 결과
data/
  AOI_capacity 3.html          원본 수집 결과 (20MB, 모든 데이터의 출처)
  AOI4_경로확인.txt              1차 조사 — AOI-4 경로 확인
  Scanresult_백업조사.txt        2차 조사 — 30대 백업 폴더 현황
  백업복구_검수.txt               3차 조사 — 복구율 측정
  못찾은것_분류.txt               4차 조사 — 못 찾은 것의 원인 분류
patch/
  collector-backup-lookup.md   수집기 수정안 (devices.py · collect.py)
github.md                      저장소 연결 기록
```

## 지금 상태

**동작하는 것** — `AOI 가동 현황 (오프라인).html` 은 **더블클릭만 하면 열립니다.**
런타임·데이터·스타일이 모두 한 파일에 들어 있어 인터넷도 로컬 서버도 필요 없습니다
(실제 제품의 '외부 요청 0, 단일 파일' 제약과 같은 방식).

개발용 `app/AOI-Dashboard.dc.html` 은 `aoi-data.json` 을 fetch 하므로 로컬 서버가 필요합니다
(`python -m http.server`). 고친 뒤 오프라인 파일을 다시 만들려면
`aoi-data.js` 를 갱신하고 `AOI-Dashboard-offline.dc.html` 을 번들하면 됩니다.

| 화면 | 내용 |
|---|---|
| 가동률 | 평균 · 살펴볼 장비 · Error 3칸 → 30대 공용 24시간 막대 목록. 층 필터 · 정렬 · 날짜 이동 |
| 장비 팝업 | 통계 6칸 + 24시간 막대 + Lot 지시선 주석 + Lot 상세(원문·Report) |
| Error | 기간/층/지표 전환 → 날짜별 차트 → 유형별 · 장비별 · Job별 → 유형·Job 팝업 |
| 추이 | 일·주·월 평균 + 장비별 31일 히트맵 |

**남은 일 4가지** — `PROMPT.md` 에 그대로 적어 뒀습니다. → **9/19 Claude Code 에서 4가지 모두 반영**(`CHANGELOG.md` 10절).
이 폴더는 이제 저장소 `docs/design/dashboard-redesign/` 에 있고, 오프라인 HTML 은 `python dev/tools/design_bundle.py` 로 만듭니다
(`aoi-data.js` 와 `AOI 가동 현황 (오프라인).html` 은 생성물이라 저장소에 없습니다). 원본 20MB `AOI_capacity 3.html` 도 넣지 않았습니다.

## 주의

- 결과 HTML 은 **외부 요청 0 · 단일 파일**이어야 합니다. 웹폰트·CDN 금지, 시스템 폰트만.
- NAS 는 **읽기만** 합니다. 어떤 파일도 만들거나 바꾸지 않습니다(`nas_guard.py` 가 강제).
- 지금 화면은 DC(Design Component) 형식입니다. 실제 제품에 넣을 때는
  `template.html` 의 마크업·CSS·JS 로 옮겨야 하며, 데이터는 `__DATA__` 자리에 박힙니다.
