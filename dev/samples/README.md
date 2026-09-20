# 현장 수집 결과 보관

앱이 실제 NAS 를 읽어 만든 결과 HTML 을 그대로 둔다. **개발·검증용**이고 배포본에는 들어가지 않는다
(업데이트 payload 는 `updater._UPDATE_TOP_ALLOW` 허용 목록뿐이라 `dev/` 는 통째로 빠진다 — 가드 `test_update_payload.py`).

## 왜 두는가

- 화면(`template.html`)을 고칠 때 **NAS 없이도 진짜 데이터로 확인**할 수 있다. 가짜 데이터로는
  드러나지 않는 것들(배치 중단이 파란 막대에 묻히는 문제, 빈 job 때문에 INI 를 못 찾는 문제,
  같은 Lot 안 7~8분 공백)이 전부 여기서 나왔다.
- 행을 꺼내는 법 — HTML 한 장에 데이터가 박혀 있다. **`dev/tests/sample_rows.py` 한 곳으로만 읽는다**
  (`.gz` 도 풀어 읽고, 열은 이름으로 매핑하며 문자열 풀 범위를 검증한다. 옛 파일 안의 옛 JS 는 실행하지 않는다 — 데이터만 꺼낸다):

```python
import sys
sys.path.insert(0, "dev/tests")
import sample_rows

rows, meta, sha = sample_rows.load(sample_rows.sample_path("AOI_capacity_2026-09-18_30일치.html"))   # .gz 를 알아서 찾는다
# rows: 열 이름 → 값 dict 의 목록 · meta: 임베디드 meta · sha: 읽은 **파일 그대로**의 sha256(전후 비교표의 input_sha)
```

- 화면만 다시 그려 보려면 그 `rows` 를 `collect.write_html` 에 그대로 넘기면 된다(NAS 접근 없음). 옛 샘플의
  `norm_status`·`scan_type` 은 그때 규칙의 값이지만 화면은 열 때마다 `status`·`lot` 원문에서 다시 계산하므로 상관없다.
- 집계 수치를 재려면 `python dev/tools/measure.py <샘플>` — 열람 시계를 그 파일의 수집 시각에 고정해 언제 돌려도 같은 값이 나온다.
  단계별 전후 수치는 `dev/samples/ledger_2026-09-18.md` 에 적는다.

## 파일

전부 gzip 이다(`gzip -n -9`, 압축을 풀면 원본과 바이트까지 같다). `sample_rows.load` 가 그대로 읽는다.

| 파일 | 언제 | 무엇 |
|---|---|---|
| `AOI_capacity_2026-09-16_3일치.html.gz` | 2026-09-16 21:01 수집 | 첫 현장 수집. 9/13~9/16 · 25대 · 15,626행 · 수집 28.6분. 원본 sha256 `956529e4c39a2d8b5ca7dae300b2db2240862a4c0f5984cc83c0e0c6ee073f37`(1,981,897 bytes) |
| `AOI_capacity_2026-09-17_30대.html.gz` | 2026-09-17 08:38 수집 | 30대 전부(4층 포함). 9/13~9/17 · 18,719행 · 수집 5.1분(목록 197초·읽기 108초). 원본 sha256 `58b705564fb2481aeffbfb147f4b010cb4b0a4377bbdf3d5d9a26f90cf861a81`(2,385,282 bytes). 9/17 인계 프롬프트가 분석한 그 첨부 |
| `AOI_capacity_2026-09-18_30일치.html.gz` | 2026-09-18 12:59 수집 | **30일치**(8/19~9/18 · 31개 날짜) · 30대 · 156,109행(원천 Wafer 155,246 + 실패 배치 863) · Report 12,665개 · 상태 문구 213종 · Job 534종(빈 Job 47행/6 Report). 원본 18.7MB → 2.4MB. 원본 HTML sha256 `261acbc5…`(CRLF 그대로), gz sha256 `75101ef5…`. 임베디드 `meta.sha` = `9be6d0dc`(D35 커밋). 9/18 실행 계획(D36~D45)의 입력. **테스트·measure·원장이 쓰는 기준 샘플** |

행을 꺼낼 때는 `dev/tests/sample_rows.py` 를 쓴다(`.gz` 도 풀어 읽고, 열은 **이름으로** 매핑하며 문자열 풀 범위를 검증한다).
집계 수치를 재려면 `python dev/tools/measure.py <샘플>` — 열람 시계를 그 파일의 수집 시각에 고정해 언제 돌려도 같은 값이 나온다.
캐시·HTML 쓰기의 크기와 메모리는 `python dev/tools/measure_cache.py <샘플> --out <임시 폴더>` (P3-A 전후 비교: 30일치 156,109행 →
캐시 JSON 86.6MB, HTML 쓰기 최고점 옛 치환 방식 181MB → 순차 쓰기 107MB, 바뀐 것 없는 실행의 캐시 쓰기 0바이트).
단계별 전후 수치는 `dev/samples/ledger_2026-09-18.md` 에 적는다.

옛 샘플 두 장은 9/20 에 압축했다(D62). 압축 전에 30일치와 대조한 결과 **내용상 부분집합**이다 — 열 이름 17개 동일,
상태 문구(40종·47종)가 전부 30일치의 213종 안에 있고, `ini_match`·`kind`·`scan_type`·`time_basis`·시각 표기 형식·장비 이름에
30일치에 없는 값이 하나도 없다(`dev/tests/test_sample_rows.py` 가 상태 문구 포함 관계와 원본 지문을 계속 확인한다).
그래도 지우지 않는 이유: 옛 파싱 규칙 시점의 실측 파일이라 독특한 회귀의 근거가 될 수 있다.

`AOI_capacity_2026-09-18_30일치.html.gz` 에 대해 알아 둘 것:

- 8/19 는 2,412행뿐이라 **부분일일 가능성**이 있다(보관 30일 창의 첫날). 9/18 은 12:59 수집이라 **부분일**이다(27대의 마지막 스캔 08:30~11:36).
  데이터가 적다는 이유만으로 확정하지 않는다 — 화면은 두 날에 '부분일 가능' 표시만 한다.
- `norm_status`·`scan_type` 은 D35 시점 규칙(`PARSER_VERSION` 2)으로 저장된 값이다. 화면은 열 때마다 `status` 원문에서 다시 계산한다.
- 실행 계획 파일이 적은 원본 sha256(`59d48739…`, 18,721,841 bytes)과 이 파일의 sha256 은 다르다 — 줄 끝(CRLF)·크기가 다르지만
  임베디드 행 156,109개·Report 12,665개·상태 분포·`generated_iso` 는 계획의 수치와 모두 같다.

`AOI_capacity_2026-09-16_3일치.html.gz` 에 대해 알아 둘 것:

- **4층 5대가 빠져 있다.** 당시 `devices.csv` 의 `4층 / I:\ / *` 행이 자동 탐색이라 범위 제한 중
  통째로 건너뛰었다(`acaa6ce` 에서 고침 — 지금은 `*` 행도 허용 목록의 이름만 정확 경로로 확인해 동작한다). `meta.devices` 에 `4층`이 `scope: "out"` 으로 남아 있다.
- **AOI-10 의 9/15 가동률(24.1%)은 실제보다 낮다.** `R_TB500 TOP D-DIE_0860312PD` 배치들의 job 을
  못 읽어 INI 경로가 어긋났고, 그래서 8.8시간이 '미가동' 으로 잡혔다(`acaa6ce` 에서 고침).
- `norm_status`·`scan_type` 은 **그때 규칙으로 계산된 값**이다. 지금 규칙으로 보려면 다시 계산한다:
  `r["norm_status"] = collect.norm_status(r["status"])`, `r["scan_type"] = collect.scan_type(r["lot"])`.

그 밖의 파일: `status_mapping_2026-09-18.tsv`(상태 문구 213종 분류 fixture, 사람이 검토) · `ini_ownership_2026-09-18.tsv` · `material_merge_2026-09-18.tsv`(D37·D39 조사표) · `ledger_2026-09-18.md`(전후 수치 원장).
