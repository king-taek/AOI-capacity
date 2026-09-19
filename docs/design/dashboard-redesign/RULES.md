# 화면이 따르는 계산 규칙

사용자와 하나씩 확정한 것입니다. **임의로 바꾸지 마세요.**

## 가동률

```
가동률 = (Scan + Rescan) ÷ 24시간
```
- Test 는 분모(24시간)에 포함하고 분자에서는 뺍니다
- 하루는 00:00~24:00 고정

막대의 6단계: **Scan**(진한 파랑) · **Rescan**(연한 파랑) · **Test**(보라) ·
**Error**(빨강) · **에러 후 대기**(연한 빨강, Error 와 같은 색 계열) · **대기**(회색)
- 시각적으로만 8분 이하 틈은 같은 종류끼리 이어 붙입니다(수치는 원본 그대로)
- 눈금선은 그리지 않습니다. 0·6·12·18·24시 숫자만

## Error

- **건수는 Lot 단위**입니다. 같은 Lot 에서 같은 유형이 여러 번 나도 **1건**
- 유형 이름은 `collect.py` 의 `CAUSE_RULES` 코드명을 **영문 그대로** (`ALIGN_ERROR`, `SCAN_ERROR` …)
- 대기 시간 = Error 구간 + 그 뒤 다음 웨이퍼까지의 공백(최대 240분)
  - **한 공백은 한 번만 배분**합니다. 시각 미기록 Error 여러 건이 같은 시점에 몰려도
    그 뒤 공백을 각자 가져가지 않습니다(중복 계산 버그였음)
  - 검증식: 모든 device-day 에서 `Scan + Rescan + Test + Error + 대기 ≤ 1440분`

## 자재 동일성 (중복 · 재스캔 판정)

```
동일 자재 = Job(병합 키) + Lot(재스캔 표기 제외) + Wafer ID
```
- 앞선 시도가 **Error** → 이번 스캔은 **정상 Scan** (실패한 웨이퍼의 재시도)
- 앞선 시도가 **Pass** → **Rescan** (장비가 달라도 무관)
- Lot 비교 시 `RE` · `RESCAN` · `REWORK` · `SRD` 토큰은 떼고 맞춥니다
- **R접두어(`2D@RE-` · `2D@R2-` · `R3` · `R4` · `R5`)가 다르면 다른 Job** 이고, 따라서 중복도 아닙니다

## Lot 이름

Report 파일명에서 뽑습니다. Report 안의 Lot 칸이 아닙니다.

```
Job_설비번호(4자리)_Lot_날짜_(시각)_BatchReport.htm   → 4자리 다음 칸
설비번호가 없으면                                      → 날짜 바로 앞 칸
```
- 앞의 `Setup1_` · `6324_` · `SETUP_` 은 버립니다 → `Setup1_FKC-PIDS5` → **FKC**
- 3글자 코드 뒤 꼬리표는 **DIA · 2D · 3D · EDGE · CENTER · RE · SRD · PCM · DUMMY · SPT** 만 남깁니다
  - 버리는 것: `PIDS*` · `PIDV` · `RDL*` · `FS` · `WBG` · `BUMP TOP` · `STRIP` · `REWORK` · `TPDV*`
- 끝의 날짜 꼬리(`_0821D`)나 설명 칸(`_Bump Surface`)도 버립니다
- **모르는 낱말이 섞이면 손대지 않고 원문 그대로** (`AMD Venice_U-Pad Dummy_Bump Surface`)
- 규칙으로 못 빼면 Report 안의 Lot 칸 사용 (`POST_0820N`)
- 표시할 때는 띄어쓰기·대소문자만 다른 것을 같은 Lot 으로 봅니다 (`TEST` ↔ `test`)

## Job 병합

통계에서만 묶고, **표기는 실제 쓰인 이름 그대로**. 대표 이름은 가장 많이 쓴 것.

묶는다:
- 구분자 · 공백 · 대소문자 차이 (`PD-0B` ↔ `PD_0B`, `R_ TB500` ↔ `R_TB500`)
- `_Copy` · `_COPY` 접미어
- `LIVE` 유무
- 장비별 복사본 (`PI3` ↔ `PI3 AOI-22 Copy_0614`)
- `Test_` 접두어
- 끝의 4자리 날짜 (`_1229` · `_0126` · `- 0729copy`)
- `A0` ↔ `AO` 오타, `PD` 누락
- 사용자 직접 지정: `R_Kendall_PI4_DG` → `R_Kendall A0_PI4`

나눈다:
- **R접두어** (RE · R2 · R3 · R4 · R5) 와 앞머리 (`INCI-` · `CMP@2D-` · `SEQ_`)
- `- Enhanced` · `- Swelling` · `- JJ` · `_Final` · `-x5` · `_REV` · `_ver2` · `_DUMMY`
- 장비명 유무 (`BS-CAMTEK` ↔ `BS`)
- 공정 단계 번호 (PI2 · PI3 · PI4 · PI5, RDL1~RDL4)
- 끝 코드 누락 · 추가

### 표기명 (JOB_ALIAS) — 21개

```
R_TB500_LIVE_PI3                        TB500 PI3
R_TB500_LIVE_PI2                        TB500 PI2
R_TB500_LIVE_PI4                        TB500 PI4
R_ TB500 LIVE_0860154PD_BS UBM          TB500 BS UBM
R_TB500 LIVE_FS                         TB500 FS
R_TB500 LIVE_0860154PD_R-ETCH           TB500 R-ETCH
TB500_RDL4 - Multi                      TB500 RDL4
TB500_RDL3 - Multi                      TB500 RDL3
TB500_RDL2 - Multi                      TB500 RDL2
TB500_RDL1 - Multi                      TB500 RDL1
R_TB500 TOP D-DIE_0860312PD             TB500 TOP D-DIE
TB500_RDL3 - Multi - Swelling           TB500 RDL3 Swelling
TB500_RDL4 - Multi - Swelling           TB500 RDL4 Swelling
R_TB500_LIVE_PI3 - Enhanced             TB500 PI3 Enhanced
R_Kendall A0_PI4                        Kendall PI4
R_Kendall A0_PI3                        Kendall PI3
R_KENDALL_A0_PI5                        Kendall PI5
R_KENDALL_A0_PI2                        Kendall PI2
R_KENDALL_A0_FS                         Kendall FS
R_MSFT_Kendall_0859275PD_BS-CAMTEK      Kendall BS
2D@RE-KENDALL A0 TOP DIE_0859659PD-0B   Kendall TOP DIE
```
`R_MSFT_Kendall_0859275PD_BS`(192장)는 이름이 겹쳐서 표기명을 붙이지 않습니다.

## 시각 기록이 부족할 때 (추정)

그 날 그 장비의 **시각 확인 비율이 50% 미만**이면 Report 의 배치 시작·종료 시각으로 가동률을 냅니다.
- 31일 × 30대 중 147 device-day(18%)가 해당
- 막대·숫자는 실측과 **같은 모양**으로 보여 주고, 티 내지 않습니다
- 상세 팝업에서만 `가동률 (추정)` · `돌아간 시간 (추정)` · `대기 (추정)` · `시각 확인 48%` 로 표시하고
  한 줄로 작게 이유를 적습니다
- 추정일 때 Scan · Rescan · Test 는 가를 수 없습니다(배치 단위라서). 그 칸들을 빼고 다른 칸으로 바꿉니다
- Lot 이름표는 배치 시작·종료 시각 위치에 붙습니다. Lot 이름 · 장수 · Error 는 INI 없이도 알 수 있습니다
- 검증: INI 가 정상인 AOI-15 에서 두 방식이 거의 일치(09/17 70% vs 70%)

## 살펴볼 장비 기준

가동률 < 40% **또는** Error ≥ 3건. Tweaks 로 조절 가능.

## 데이터 출처

`aoi-data.json` 은 수집 결과 `AOI_capacity.html` 안의 embedded JSON 에서 뽑았습니다.

원본 열: `device, kind, job, setup, lot, wafer_id, status, norm_status, cause, outcome,
scan_type, recipe, wafer_start_time, wafer_end_time, batch_start, batch_end, report,
ini_match, time_basis, slots, data_issue`

**`faults` · `scanned_dice` · `yield` 는 빠져 있습니다** — 리포트의 평균 fault 를 채우려면
`collect.py` 의 내보낼 열 목록에 추가하고 재수집해야 합니다.

`aoi-data.json` 구조:
```
{ day, generated, devices[], days[],
  pool: { job[], lot[], rep[], st[] },          문자열 풀
  detail: { "2026-09-18": { "AOI-1": {
    r,x,t,d,s      Scan·Error·Test·Rescan·에러후대기 (분)
    w,e            Wafer 수, Error 건수(Lot 단위)
    cv             시각 확인 비율 %
    be, bseg[]     배치 기준 점유 분, 병합된 배치 구간
    seg[]          [시작분, 끝분, 종류]  종류 0=Scan 1=Error 2=Test 4=Rescan
    ct{}           { 유형: [건수, 대기분] }
    lots[]         [jobIdx, lotIdx, a, b, w, e, dup, test, repIdx, causes{}, stIdx, ba, bb]
                    a·b = 웨이퍼 시각 구간, ba·bb = 배치 시각 구간
  }}},
  jobG[], jobGroups[]                            Job 병합 그룹
}
```
