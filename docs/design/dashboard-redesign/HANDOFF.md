# AOI Capacity 결과 화면 재설계 — 핸드오프 (9/19, 역사 문서)

> **저장소 주(2026-09-20)**: 이 handoff 의 할 일은 전부 반영됐고 화면은 제품 `template.html` 로 이식됐다. 지금 이 폴더가 어떤 역할인지,
> 무엇이 아직 코드·테스트에 쓰이는지, 디자인 규칙과 제품 규칙이 어디서 다른지는 [`STATUS.md`](STATUS.md) 를 본다.
> 아래는 그때의 문서 그대로이며, 보관으로 옮긴 파일(`PROMPT.md` · `patch/` · 시안)은 `archive/design/` 에 있다.

이 폴더 하나로 Claude Code 에서 이어서 작업할 수 있습니다.
`PROMPT.md`(→ `archive/design/PROMPT.md`) 의 내용을 그대로 붙여넣고 시작하세요.

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
STATUS.md                      ★ 지금 상태 — 무엇이 살아 있고 무엇이 보관됐는지, 제품과 다른 규칙 표 (2026-09-20)
HANDOFF.md                     이 파일
CHANGELOG.md                   지금까지의 요청과 반영 내역
RULES.md                       9/19 시점의 계산 규칙 (역사 문서 — 제품 규칙은 CLAUDE.md)
scripts/                       추출 스크립트(9/20 회수) — make_aoi_data.js 는 legacy 프로필의 oracle, 고치지 않는다
app/
  AOI-Dashboard.dc.html        본체 — 가동률 · Error · 추이 · 리포트 + 팝업
  AOI-Dashboard-offline.dc.html  오프라인 빌드의 원본 (데이터를 aoi-data.js 로 읽음, design_bundle.py 가 만든다)
  support.js                   DC 런타임 (수정 금지)
  aoi-data.json                화면이 읽는 데이터 (31일 × 30대)
data/
  AOI4_경로확인.txt              1차 조사 — AOI-4 경로 확인
  Scanresult_백업조사.txt        2차 조사 — 30대 백업 폴더 현황
  백업복구_검수.txt               3차 조사 — 복구율 측정
  못찾은것_분류.txt               4차 조사 — 못 찾은 것의 원인 분류
offline_shell.html · .json     Claude Design 번들의 껍데기 (design_bundle.py 입력)
github.md                      저장소 연결 기록 (역사 문서)

→ archive/design/ 로 옮긴 것(D62): PROMPT.md · PROMPT_extract-script.md · patch/collector-backup-lookup.md ·
  app/Err-Popup-A.dc.html(반영됨) · app/AOI-4 해결 제안.dc.html + app/aoi-recovery.json(적용됨)
→ 생성물이라 저장소에 없는 것: AOI 가동 현황 (오프라인).html · app/aoi-data.js  (`python dev/tools/design_bundle.py`)
→ 원본 수집 결과 `data/AOI_capacity 3.html`(20MB)은 저장소에 넣지 않았다
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
