# AOI Capacity — AOI 장비 가동률

Camtek AOI 장비의 NAS `Report/*_BatchReport.htm` 과 `Scanresult/.../WaferInfo.ini` 를 읽어 장비별 가동률(검사 / 오류 / 미가동)을
내는 프로그램입니다. 두 조각으로 나뉩니다.

| | 하는 일 |
|---|---|
| **수집 프로그램** (PyQt6, `AOI_Capacity.exe`) | NAS 를 읽어 결과 HTML 한 장을 만듭니다. 수집 · 장비 목록 · 설정 화면만 있습니다. |
| **결과 화면** (`AOI_capacity.html`) | **파일을 더블클릭하면** 브라우저에서 열립니다. 수집 프로그램이 꺼져 있어도 조회·정렬·필터·클릭이 됩니다. |

결과 HTML 한 장에 데이터·스타일·스크립트가 모두 들어 있어 **인터넷도 로컬 서버도 필요 없습니다**(외부 요청 0).
새 데이터를 보려면 수집 프로그램에서 '지금 수집' 을 누른 뒤, 열어 둔 화면을 새로고침(F5)하세요. 자동 주기 수집은 없습니다.
설정·장비 목록·수집 캐시·결과 HTML 은 모두 그 PC 의 `%LOCALAPPDATA%\AOI_Capacity` 에만 저장됩니다.

> **NAS 원본은 읽기만 합니다.** NAS 경로 아래에는 어떤 파일도 만들거나 바꾸거나 지우지 않습니다.
> 코드(`aoi_capacity/nas_guard.py`)와 테스트(`dev/tests/test_nas_guard.py`)가 이를 강제합니다.

## 화면

**수집 프로그램**

| 메뉴 | 내용 |
|---|---|
| 수집 | **지금 수집** 버튼, 처음 수집 기간 / 이력 보관 기간, 결과 폴더, 결과 HTML 경로와 **결과 화면 열기**, 로그 |
| 장비 목록 | `devices.csv` 편집(행 추가/삭제, 폴더 찾아보기, `*` 자동, CSV 가져오기/내보내기, 연결 확인) |
| 설정 · 정보 | 어두운 화면, 주의 장비 기준, 데이터 폴더, 버전 · 업데이트 확인 |

**결과 화면**(HTML 파일을 더블클릭)

| 메뉴 | 내용 |
|---|---|
| 홈 | 선택한 날짜의 모든 장비 가동률 카드/표(기본 순서: AOI-1…AOI-25 → 4F-AOI-01…). 카드 클릭 → Lot 단위 24시간 타임라인 + 오류 목록 |
| 추이 | 일 · 주 · 월 막대, 이번 기간 vs 이전 기간 비교 |
| 장비 비교 | 선택한 날 · 최근 7일 · 최근 30일 기준 장비 순위와 변화 |
| 설정 | 주의 장비 기준, HTML 로 저장. 바꾼 값은 **그 브라우저에만** 저장되며 원본 파일이나 수집 설정에는 반영되지 않습니다 |

가동률 = 검사시간(WaferStartTime~WaferEndTime 합) ÷ 24시간. 오늘은 00:00 부터 현재 시각까지로 나눕니다.
오류 Wafer 종료부터 다음 Wafer 시작까지의 공백은 '정지(추정)' 으로 봅니다(장비 이벤트 로그가 아닙니다).

## 설치 (사용자)

1. 배포 zip(`AOI_Capacity_<날짜>_<sha7>.zip`)을 원하는 위치(예: `C:\AOI_Capacity`)에 압축 해제합니다. NAS 나 OneDrive 안은 피하세요.
2. `AOI_Capacity.exe` 를 실행합니다. 백신이 exe 를 막으면 `run_aoi.bat` 을 대신 실행합니다.
3. **처음 실행**(lite 배포)에는 콘솔 창이 뜨고 필요한 패키지(PyQt6 등, 약 250 MB)를 인터넷에서 설치합니다. 몇 분 걸릴 수 있으니 창을 닫지 마세요. 두 번째 실행부터는 바로 창이 뜹니다.
4. '장비 목록' 에서 NAS 경로와 장비 폴더를 적고 저장한 뒤, '수집' 에서 **지금 수집**을 누릅니다.
5. 수집이 끝나면 '결과 화면 열기' 를 누르거나, `%LOCALAPPDATA%\AOI_Capacity\AOI_capacity.html` 을 **더블클릭**합니다.
   그 파일은 바탕화면에 바로 가기를 만들어 두면 편합니다.

자세한 안내는 zip 안의 `설치방법.txt` 에 있습니다.

## 최신 코드 받기

`scripts\update_code.bat` 을 더블클릭하거나 `python scripts\update_code.py` 를 실행하면 이 폴더가 지정한 브랜치의
최신 내용으로 맞춰집니다. **받을 브랜치는 `scripts\update_code.py` 맨 위의 `BRANCH = "..."` 한 줄**입니다.

- `.git` 이 있는 폴더 → `git fetch` + 빨리감기 병합. 커밋하지 않은 변경이 있으면 멈추고 알려 줍니다.
- GitHub zip 을 푼 폴더 → 브랜치 zip 을 받아 **바뀐 파일만** 덮어씁니다. 원본은 `_backup_날짜시각\` 에 남고,
  이 폴더에만 있는 파일은 지우지 않습니다.
- `--check` 를 붙이면 무엇이 새로 왔는지 보기만 합니다.

## 샘플 보내기 (개발용)

재스캔(RE · SRD) 표기와 Scan error 뒤 재스캔 흐름을 정확히 구현하려면 실물 파일이 필요합니다.
`scripts\make_sample.bat` 을 더블클릭하면(또는 `python scripts\collect_sample.py`) 바탕화면에
`AOI_sample_<날짜>.zip` 한 장이 만들어집니다. **NAS 는 읽기만 하고**, Report 목록 · 고른 Report 원본 ·
해당 Lot 폴더의 `WaferInfo.ini` 와 폴더 목록(수정시각 포함) · 요약(Lot 접미사 통계)이 들어갑니다.
보내기 전에 `요약.txt` 로 내용을 확인하세요.

    scripts\make_sample.bat --all                 :: 전 장비(30대) → zip 한 장  ★
    scripts\make_sample.bat                       :: 한 대만(기본 Y:\AOI-25)
    scripts\make_sample.bat --root X:\AOI-1 --days 3

`--all` 은 `scripts\collect_sample.py` 위쪽 `DEVICE_ROOTS` 의 장비를 차례로 훑습니다(경로가 바뀌면 그 목록만 고치세요).
접근할 수 없는 장비는 건너뛰고 계속하며, 맨 위 `요약.txt` 에 장비별 한 줄 표(Report 수 · 폴더 이름 · Job/Setup 유무 ·
읽지 못한 시각 · Lot 표기)가 들어갑니다. Report 안의 로고 이미지는 용량 때문에 빼고 담습니다(`--keep-images` 로 유지).

## 수집 범위 (현재 30대)

수집·연결 확인은 `aoi_capacity/scope.py` 의 허용 목록 안에서만 합니다. 4대(AOI-1·8·9·25) 현장 테스트를 마치고 **30대 전부**로 넓혔습니다.

| 장비 | 경로 |
|---|---|
| AOI-1 ~ AOI-7 | `X:\AOI-n` |
| AOI-8 · AOI-9 | `M:\AOI-n` |
| AOI-10 ~ AOI-16 | `V:\AOI-n` |
| AOI-17 ~ AOI-23 | `P:\AOI-n` |
| AOI-24 · AOI-25 | `Y:\AOI-n` |
| 4F-AOI-01 ~ 05 | `I:\4F-AOI-0n` |

목록에 없는 이름(오타·새 장비)에는 목록 조회조차 하지 않으며, 화면에는 "수집 안 함" 으로 표시됩니다.
`devices.csv` 의 다른 행과 이전에 모아 둔 캐시는 **지우지 않고** 그대로 둡니다(`prefs.json` 의 `scope_devices`, `["*"]` 이면 제한 없음).

> ⚠️ `devices.csv` 의 **`폴더` 칸이 `*`(자동 탐색)인 행은 범위 제한 중 통째로 건너뜁니다** — 어떤 장비가 있는지 알려면
> 공유 폴더를 나열해야 하고, 그 나열 자체가 범위 밖 접근이기 때문입니다. 그래서 기본 목록에서는 4층도 5줄로 또박또박 적습니다.
> 예전 `devices.csv` 에 `4층 / I:\ / *` 행이 남아 있으면 그 5대는 수집되지 않으니, 장비 목록 화면에서 5줄로 바꿔 주세요.

## 장비 목록 (devices.csv)

첫 실행 때 `aoi_capacity/assets/devices.default.csv` 가 데이터 폴더의 `devices.csv` 로 복사됩니다. GUI 에서 편집하거나 Excel 로 편집해 가져올 수 있습니다(cp949 · UTF-8 모두 읽습니다).

| 장비명 | NAS경로 | 폴더 | 사용 | 메모 |
|---|---|---|---|---|
| AOI-9 | M:\ | AOI-9 | Y | Camtek 8~9 |
| AOI-24 | \\10.142.80.88\Camtek24-25 | AOI-24 | Y | UNC 경로도 됨 |
| 4F-AOI-01 | I:\ | 4F-AOI-01 | Y | `*` 로도 쓸 수 있지만 **수집 범위 제한 중에는 건너뜁니다** |

- 폴더를 비우면 NAS경로 자체가 장비 폴더입니다. `*` 면 Report 폴더가 있는 하위 폴더를 모두 자동 등록하므로 장비가 늘어나도 CSV 를 고칠 필요가 없습니다.
- 사용이 `N` 이면 수집하지 않습니다. 접근할 수 없는 행은 로그에 남기고 건너뜁니다.

## 수집 기간

- 처음 수집(캐시 없음)이나 '과거 이력 다시 채우기' 는 수정시각이 최근 `처음 수집 기간`(기본 30일) 안인 Report 를 전부 읽습니다.
- 이후에는 장비마다 **마지막으로 가져온 Report 이후에 생긴 파일을 전부** 읽습니다. 처음 보는 장비는 30일치로 읽습니다.
- 캐시는 `이력 보관 기간`(기본 90일) 동안 유지되어 주·월 추이가 쌓입니다.
- Scanresult 는 재귀 검색하지 않고 Wafer 마다 계산된 정확 경로의 WaferInfo.ini 만 확인합니다.
- 수집을 중지하면 이번 결과는 버리고 이전 결과가 그대로 남습니다.

## 데이터 폴더

`%LOCALAPPDATA%\AOI_Capacity` (환경변수 `AOI_DATA_HOME` 으로 바꿀 수 있음)

| 파일 | 내용 |
|---|---|
| `prefs.json` | 설정 |
| `devices.csv` | 장비 목록 |
| `aoi_cache.json` | 수집 캐시(장비별 마지막 수정시각 커서 포함) |
| `AOI_capacity.html` | 결과 화면 — **파일을 더블클릭하면 브라우저에서 그대로 열립니다**(Python·서버 불필요, 외부 요청 없음). 새 데이터는 수집을 다시 실행한 뒤 새로고침 |
| `app.log`, `collect.log` | 로그 |

결과 폴더를 바꿀 수는 있지만 NAS 경로 아래로는 지정할 수 없습니다.

## 자동 업데이트

실행할 때 GitHub 저장소 기본 브랜치의 최신 커밋 SHA 를 `app/VERSION` 과 비교해 새 버전을 안내합니다. 동의하면 브랜치 zip 을 받아
새 트리를 만들고 검증한 뒤 `app.new` 로 준비해 두며, **다음 실행 때** 런처(`AOI_Capacity.exe`)가 `app/` 을 교체합니다.
새 버전이 다른 패키지를 요구하면 동봉 파이썬에 먼저 설치하고, 설치에 실패하면 업데이트를 적용하지 않습니다.
api.github.com 이 막히면 github.com Atom 피드로, 회사 SSL 검사 프록시에서 인증서 검증이 실패하면 검증 없이 한 번 더 시도합니다.
git 작업 폴더에서 실행 중이면 자동 적용을 하지 않습니다(`git pull` 사용).

새 버전 배포는 기본 브랜치에 푸시하기만 하면 됩니다. `requirements.txt` 를 바꾸는 변경은 사용자 PC 의 첫 업데이트에서 패키지 설치가 필요하니 주의하세요.

## 헤드리스 수집 (선택)

자동 주기 수집은 없습니다(수동 실행만). 작업 스케줄러 등에서 창 없이 수집하려면 `scripts/run_collect.bat`(→ `python -m aoi_capacity.cli`) 을 씁니다. GUI 와 같은 데이터 폴더를 쓰며,
`--config` 로 `docs/config.example.json` 형식의 설정 파일을 줄 수도 있습니다.

## 개발

```
pip install -r requirements.txt -r dev/requirements-dev.txt
python main.py                                   # 개발 실행
QT_QPA_PLATFORM=offscreen python -m pytest -q    # 테스트 (빠른 확인: -m "not ui")
```

빌드(Windows + 인터넷):

```
python scripts\build.py exe-lite        # 런처 exe + python 런타임 + app\  (라이브러리는 첫 실행 때 설치)
python scripts\build.py exe             # 라이브러리까지 동봉(인터넷 없는 PC 용)
python scripts\make_release_zip.py --lite
```

폴더 구성: `main.py`(진입) · `aoi_capacity/`(`collect.py` 수집 코어, `devices.py`, `nas_guard.py`, `i18n/`, `utils/`, `workers/`, `ui/`) ·
`scripts/`(런처·빌드) · `dev/`(테스트) · `docs/`(브라우저 데모 `aoi_collector_demo.html`, 설정 예시, 스크린샷).
작업 규칙은 `CLAUDE.md` 를 보세요.
