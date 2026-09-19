repo: king-taek/AOI-capacity
branch: main
path: aoi_capacity/ui/assets

## Last sync

date: 2026-09-20T01:10:00Z

### Updated in this project

- 결과 화면(AOI_capacity.html) 전면 재설계 — 라이트 단일 테마, 가동률 · Error · 추이 3화면 + 장비 팝업
- Job·Lot 이름 정리 규칙과 표기명(21개) 확정, Error 건수를 Lot 단위로 재집계
- INI 누락 원인 규명 — Scanresult 백업 폴더 미조회. 수집기 수정안과 30대 검증 결과 정리
- 시각 확인 50% 미만인 device-day 는 Report 배치 시각으로 가동률 추정

## 화면

| 파일 | 내용 |
|---|---|
| `AOI-Dashboard.dc.html` | 본체. 가동률 · Error · 추이 3탭 + 장비 상세 팝업 + Error 유형/Job 팝업 |
| `AOI-4 해결 제안.dc.html` | 수집기 수정 제안서(백업 폴더 조회). 30대 검증 결과 포함 |
| `Err-Popup-A.dc.html` | 승인된 Error 상세 팝업 시안. 아직 본체에 미반영 |
| `aoi-data.json` | 위 화면들이 읽는 데이터(31일 × 30대). 수집 결과 HTML 에서 추출 |

## Screen map

| 프로젝트 화면 | 근거 저장소 파일 |
|---|---|
| AOI-Dashboard — 가동률 | `aoi_capacity/ui/assets/template.html` (`.app` 셸 · `.dev` 카드 · `.strip` 막대 · `:root` 토큰), README.md |
| AOI-Dashboard — 장비 팝업 | template.html (`.detail` · `.segd` · `DISPLAY_META`), collect.py (Lot · materialKey) |
| AOI-Dashboard — Error | template.html (Error 분석 뷰), collect.py `_CAUSE_RULES` |
| AOI-Dashboard — 추이 | template.html (`.cmp` 추이 카드 · 일/주/월) |
| AOI-4 해결 제안 | collect.py:490·999, devices.py:150·184 |
| aoi-data.json | 수집 결과 `AOI_capacity.html` 의 embedded JSON, collect.py CAUSE_RULES |

## 확정된 계산 규칙 (화면이 따르는 것)

- 가동률 = (Scan + Rescan) ÷ 24시간. Test 는 분모에만 포함
- Error 건수 = **Lot 단위**. 같은 Lot 에서 같은 유형이 여러 번 나도 1건
- Error 대기 시간 = Error 구간 + 그 뒤 다음 웨이퍼까지의 공백(최대 240분). 한 공백은 한 번만 배분
- 자재 동일성 = Job(병합 키) + Lot(재스캔 표기 제외) + Wafer ID.
  앞선 시도가 Error → 이번은 정상 Scan, 앞선 시도가 Pass → 장비 무관 Rescan
- Lot 이름 = Report 파일명에서 추출. 4자리 설비번호 다음 칸, 없으면 날짜 앞 칸.
  꼬리표는 DIA·2D·3D·EDGE·CENTER·RE·SRD·PCM·DUMMY·SPT 만 유지
- Job 병합 = 구분자·공백·대소문자 / `_Copy` / `LIVE` 유무 / 장비별 복사본 / `Test_` / 끝의 4자리 날짜 /
  `A0`↔`AO` / `PD` 누락. **R접두어(RE·R2·R3·R4·R5)는 서로 다른 Job**
- 시각 확인 50% 미만인 device-day 는 Report 배치 시각으로 추정하고 팝업에 '추정' 표기

## 남은 일 (9/19 Claude Code 에서 1~4 모두 반영 — CHANGELOG 10절. 남은 것은 실장비 재수집과 이식 결정)

1. **수집기 수정** — `Scanresult` 로 시작하는 백업 폴더도 조회(제안서 참고). 검증 결과 읽을 수 있는 INI 가 24,050 → 53,069 개
2. **`faults` 열 내보내기** — collect.py 의 내보낼 열 목록에 추가해야 리포트의 평균 fault 를 채울 수 있음
3. **Error 상세 팝업 적용** — `Err-Popup-A.dc.html` 을 본체 Error 탭에 연결
4. **TB500 · Kendall 리포트 탭** — 표기명 붙인 21개 Job, 이름순, 기간 31일 기본.
   배치시간 = 준비시간 + 장당시간 × 장수 회귀, `장당 8.11 ± 0.4분` 형식.
   Error·중단·5장 미만 배치는 평균에서 제외
