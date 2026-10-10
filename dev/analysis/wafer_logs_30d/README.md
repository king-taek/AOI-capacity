# Wafer 로그 30일 전수 분석 — 재실행·검증 패키지

수집 창의 'Wafer 로그 30일 전체 수집' 버튼이 만든 로그(9/9~10/10, Camtek 30대)로 돌린 분석의 스크립트 모음이다.
추출 → 사실 집계 → 검증 → 시각화용 숫자 순서이며, 보고서에 적힌 숫자는 `verify/` 결과가 정본이다
(검증 단계에서 몇 개가 고쳐졌다: G5 스캔 비중 58%→75.3%, 후처리 해석, CR=Wafer 비용, 재검사 분류 등 — `verify/notes.md`).
앱 코드는 건드리지 않는다. 저장소 쪽 입력은 `scripts/collect_wafer_logs.py` 하나(파서 재사용)뿐이다.

## 입력
- 버튼이 만든 암호화 전 zip 8장(`.enc` 면 `python scripts/collect_wafer_logs.py --decode <파일>.enc` 로 먼저 푼다).
- 8장을 **한 폴더에 전부 풀어** 합친다 → 그 폴더 안에 `lots.json` 과 Lot 폴더들이 있어야 한다(아래 `$TREE`).

## 준비
```
export AOI_WORK=/작업/폴더          # 모든 중간·최종 결과가 여기로 간다 (이 폴더 밖에는 쓰지 않는다)
export TREE=/풀어낸/폴더            # 위 입력
cd <저장소>/dev/analysis/wafer_logs_30d
```
`$AOI_WORK` 아래에 `an3/`(추출·집계), `fable/`(검증), `sonnet/`·`haiku/`(시각화), `report2/`(보고서 데이터)가 생긴다.
`AOI_WORK` 를 안 주면 `set AOI_WORK` 로 멈춘다. 스크립트끼리의 import 는 파일 위치 기준이라 어느 폴더에서 실행해도 된다.

## 실행 순서
```
# 1) 추출: 풀어낸 트리 -> an3/wafers.jsonl · lots3.json · params3_raw.json
mkdir -p $AOI_WORK/an3
python extract/extract3.py $TREE $AOI_WORK/an3

# 2) 사실 집계 (인자: an3 폴더). 파라미터 두 개는 2번째 인자로 '풀어낸 트리'도 받는다 (참조 dedup 해소에 원본 파일을 연다)
python facts/ana3.py    $AOI_WORK/an3          # -> facts.json
python facts/ana4.py    $AOI_WORK/an3          # -> facts4.json
python facts/ana5.py    $AOI_WORK/an3          # -> facts5.json
python facts/params4.py $AOI_WORK/an3 $TREE    # -> ac4.json, params4.json   (ana6 · verify 가 쓴다)
python facts/params5.py $AOI_WORK/an3 $TREE    # -> params5.json
python facts/ana6.py    $AOI_WORK/an3          # -> facts6.json  (ac4.json · params4.json 필요)
python facts/build_data.py                     # -> $AOI_WORK/report2/data.json (facts*.json 을 한 장으로)

# 3) 검증 (facts 가 만든 an3 를 다시 독립 계산) -> $AOI_WORK/fable
python verify/a1.py && python verify/a2.py && python verify/a3.py && python verify/write_audit.py
#   load.py 가 첫 실행에 fable/cache.pkl 을 만든다. an3 를 다시 만들었으면 이 pkl 을 지우고 돌린다.

# 4) 시각화용 집계·사례 -> $AOI_WORK/sonnet/viz.json
python viz/p1.py && python viz/p5.py && python viz/final.py
python viz/make_0920.py                        # (선택) 유휴 예시 -> haiku/idle_example.json
```
`viz/p2~p10.py`, `chk.py`, `find_idle_day.py` 는 final 에 이르기까지의 탐색 스크립트(남겨 둔 것)다. final 에 필요한 것은 p1·p5 뿐이다.
스크립트는 같은 입력이면 같은 결과를 낸다 — 이 패키지로 `verify/` 의 a1·a2·a3·audit 4개 JSON 이 원본과 바이트까지 같게 재현됨을 확인했다.
`viz.json` 은 원본과 `overwrite_example.also_same_pattern` 문장 하나만 다르다(원본은 final.py 로 만든 뒤 그 문장을 손으로 고쳤고, 스크립트에는 고친 문장이 들어 있다).

## 숫자 → 만든 스크립트 → 출력 키
JSON 은 `$AOI_WORK/fable/{a1,a2,a3}.json`(`audit.json` 은 이를 보고서 주장별로 정리한 것), 시각화는 `$AOI_WORK/sonnet/viz.json`.

| 숫자 | 스크립트 | 출력 키 (재실행 값) |
|---|---|---|
| G5 스캔 비중 58.0% → 75.3%, 비스캔 2,002h → 약 1,180h | verify/a1.py | `g5_hours_fixed` (`scan_pct_asis` 58.0, `scan_pct_fixed` 75.3, `overhead_h_fixed` 1179); 보정 전은 `gen_share_asis` |
| G5 로딩 66초(나머지 세대 15~17초) | verify/a1.py | `load_same_settings` (EagleG5 med 66, EagleTP 17, EagleT 16, EAGLE 15) · AF=Wafer 일 때는 `load_cr_lot_af_wafer` |
| x5 단독 스캔 55초 | verify/a1.py | `rdl_x5_single_dur` (n 104, med 55) |
| 레시피 전환 시간(장비마다 다름, CR 설정별) | verify/a3.py · a1.py | `n3_settings` (dev·cr·af 별 `switch` 초) · RDL 멀티 후처리 분해는 `rdl_post_fixed` |
| 기준영상(CR=Wafer) 비용 193h / 425h | verify/a3.py | `cr_refined` (`matched_h` 381, `clean_h` 193, `extrapolated_clean_h` 425, 교란 쌍 `confounded`) · 세대별 `cr_delta_by_gen` · 처음 주장 542h 는 `a1.cr_asis` |
| 재검사 17,759건 중 진짜 재검사 4,010건 | verify/a3.py | `repeat3` (`total` 17759, `buckets["진짜 재검사"]` n 4010 · 452h) · 보정 전 분류는 a2 `repeat_asis` |
| 자기 INI 가 없는 행 11.2% | verify/a2.py | `claim6` (`pct_asis` 11.2 = `never_scanned_rows` 5.7% + `scanned_but_no_ini` 6.1%, 다중 Report Lot `pct` 22.9) |
| 검토(리뷰) 지연·미검토 | verify/a2.py | `review` (`all_med` 중앙 3.8h, `unrev_pct_asis` 30.6, `unrev_pct_excl3d` 30.1, `done24_pct` 62.5, 결함 수별 `unrev_by_defects`) · G5 계열별 `review_g5_fam` |
| Lot 교체 공백(2시간 미만 11,369건·4,497h) | verify/a3.py | `n1_summary` (같은 Job/다른 Job/에러 후 중앙값) · `n1_p25` · `n1_dev`(장비별, 합계 `n1_recover_total_h`) · `n1_recover_at_median_h` · `n1_gap_hist`, `n1_gap_hist_h` |
| 바쁨 × 속도 사분면 | verify/a3.py | `n2` (장비별 `busy_pct`·`wph`) · `n2_medians` (wph 9.6, busy 65.0) · `n2_quad` (4분면별 장비 목록) |
| AOI-17 Enhanced 가 느림 | verify/a2.py · a3.py | `aoi17` (703~827초 vs 타 장비 203~305초) · `aoi17_plain_pi` · `aoi17_by_job_day` · 파라미터 차이 `aoi17_param_off`(a3) |
| 유휴 히트맵 (장비 × 날짜 가동 %) | viz/p1.py → viz/final.py | `viz.json` 의 `heat` (`days`·`devs`·`v`), 간격 분포는 `gapHist` |
| 유휴 62.0%(구간 기준) / 60.2%(고정 창 748h) | verify/a2.py | `busy` , 창은 `window` |
| 장 시간 사례 카드 · 덮어써진 INI · 재검사 · CR 사례 · 일별 Lot 수 | viz/final.py | `wafer_example` `rdl_example` `overwrite_example` `repeat_example` `cr_example` `daily_lots` |

## 폴더
- `extract/` tparse(시각 파서·`collect_wafer_logs` 불러오기) · fam(Job 계열 분류) · extract3(트리 → jsonl/json)
- `facts/` ana3~6, params4·5, build_data
- `verify/` load(공용 로더+캐시) · a1~a3 · write_audit · notes.md(검증 메모)
- `viz/` 시각화용 p1~p10·common·load·final·chk, 유휴 예시 find_idle_day·make_0920
