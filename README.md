# AOI 장비 가동률 (AOI Capacity)

Camtek AOI 장비의 BatchReport와 WaferInfo.ini를 읽어 장비별 가동률을 보여주는 대시보드입니다.

## 구성 (권장: Python 수집기 + HTML 화면)

```
NAS (Report / Scanresult)  ──►  aoi_collect.py (작업 스케줄러, 10분마다)
                                    │  증분 캐시 aoi_cache.json
                                    │  GitHub에서 template.html / aoi_collect.py 자동 갱신
                                    ▼
                          공유 폴더\AOI_capacity.html  ◄── 사용자는 이 파일만 엽니다
```

| 파일 | 역할 |
|---|---|
| `aoi_collect.py` | 수집기. 표준 라이브러리만 사용. NAS를 읽고 `template.html`에 데이터를 넣어 HTML 1개를 씁니다. |
| `template.html` | 화면 템플릿. `__DATA__` 자리에 데이터가 들어갑니다. |
| `config.example.json` | 설정 예시. `config.json`으로 복사해 수정합니다. |
| `devices.example.csv` | 장비 목록 예시. `devices.csv`로 복사해 Excel에서 편집합니다. |
| `run_collect.bat` | 작업 스케줄러에 등록할 실행 파일. |
| `aoi_collector_demo.html` | 브라우저만으로 동작하는 데모(장비 30대 합성 데이터). Python 없이 시험할 때 씁니다. |

### 설치
1. 수집용 PC에 Python 3.8 이상 설치.
2. 이 저장소의 `aoi_collect.py`, `template.html`, `run_collect.bat`, `config.example.json`을 한 폴더(예: `C:\AOI_capacity`)에 둡니다. git으로 clone하지 말고 파일만 복사합니다(git 폴더에서는 자동 업데이트가 꺼지고 `git pull`을 씁니다).
3. `devices.example.csv`를 `devices.csv`로 복사해 장비 목록을 적습니다(아래 참고). `config.example.json`을 `config.json`으로 복사하고 `output_dir`(모두가 여는 공유 폴더)을 수정합니다.
4. `python aoi_collect.py`를 한 번 실행해 `output_dir`에 `AOI_capacity.html`이 생기는지 확인합니다.
5. 작업 스케줄러에서 `run_collect.bat`를 10분 간격으로 등록합니다.

### 장비 목록 (devices.csv)
Excel에서 편집해 CSV로 저장하면 됩니다(한글 Windows Excel의 cp949 저장, UTF-8 모두 읽습니다).

| 장비명 | NAS경로 | 폴더 | 사용 | 메모 |
|---|---|---|---|---|
| AOI-9 | M:\ | AOI-9 | Y | Camtek 8~9 (\\10.142.80.90) |
| AOI-24 | \\10.142.80.88\Camtek24-25 | AOI-24 | Y | 드라이브 문자 대신 UNC 경로도 됨 |
| 4층 | I:\ | * | Y | 폴더가 *이면 이 NAS 안의 장비 폴더를 모두 자동 등록 |

- 폴더: NAS경로 아래의 장비 폴더 이름. 비우면 NAS경로 자체가 장비 폴더입니다. `*`면 Report 폴더가 있는 하위 폴더를 모두 자동 등록하므로 장비가 늘어나도 CSV를 고칠 필요가 없습니다.
- 사용: `N`이면 수집하지 않습니다. 메모는 자유 입력입니다.
- 접근할 수 없는 행은 로그에 남기고 건너뜁니다. 같은 폴더가 두 번 나오면 먼저 적힌 행의 이름을 씁니다.

### 수집기 동작
- `devices.csv`의 각 행을 장비로 씁니다. CSV가 없으면 `config.json`의 `nas_roots`를 자동 탐색합니다(재귀 검색 없음).
- 장비마다 최신 N개 Report를 확인하고, 이미 읽은 파일(경로와 수정시각이 같음)은 건너뜁니다. 캐시에 `retention_days`(기본 90일) 동안 이력을 보관하므로 주·월 추이가 쌓입니다.
- Wafer마다 계산된 정확 경로의 WaferInfo.ini만 확인하고 필요한 키만 읽습니다. 원본은 수정하지 않습니다.
- 실행 시작 때 GitHub 저장소 기본 브랜치의 최신 커밋 SHA를 조회해 로컬 `VERSION` 파일과 다르면 브랜치 zip을 내려받아 검증(`template.html`의 `__DATA__` 자리, 스크립트 문법)한 뒤 파일을 교체하고 스스로 재실행합니다. 교체 전 파일은 `.bak`로 남기고 실패하면 되돌립니다. api.github.com이 막히면 github.com Atom 피드로, 회사 SSL 검사 프록시로 인증서 검증이 실패하면 검증 없이 한 번 더 시도합니다. 오프라인이면 건너뜁니다. `--no-update`로 끌 수 있습니다. (king-taek/coding 저장소의 updater 방식을 따랐습니다.)
- 출력 HTML은 임시 파일에 쓴 뒤 교체하므로 여는 도중 깨진 파일을 보지 않습니다.

### 화면
- **홈**: 선택한 날짜의 모든 장비 가동률. 상단 요약(평균, 주의 장비, 오류 장비, 최저 장비), 정렬(낮은 순·오류 먼저·이름순), 카드/표 전환, 전일 대비 화살표. 카드를 클릭하면 Lot 단위 24시간 타임라인(막대 하나 = Lot 하나, 오류 Wafer와 정지는 빨강)과 Lot 목록, 오류 목록이 펼쳐집니다.
- **추이**: 일·주·월 단위 막대(전체 평균 또는 장비 하나)와 이번 기간 vs 이전 기간 비교 카드.
- **장비 비교**: 선택한 날·최근 7일·최근 30일 기준 장비 순위와 이전 기간 대비 변화.
- **설정**: 브라우저 직접 수집(수동 대체 수단), 이상 판정 기준, HTML 저장, 로그.
- 상단 배지에 마지막 수집 시각과 경과 시간이 나오고, 2시간 이상 지나면 노란색으로 바뀝니다. GitHub에 새 버전이 있으면 안내 줄이 표시됩니다.

### 가동률 정의
- 가동률 = 검사시간(WaferStartTime~WaferEndTime 합) ÷ 24시간. 오늘이면 00:00부터 현재 시각까지로 나눕니다.
- 오류 Wafer 종료부터 다음 Wafer 시작까지의 공백을 "정지(추정)"로 봅니다. 장비 이벤트 로그가 아닙니다.
- 주·월 가동률 = 기간 내 검사시간 합 ÷ 기간 내 경과시간 합. 주는 월요일 시작입니다.

## 브라우저만으로 쓰기 (Python 없이)
`aoi_collector_demo.html`을 Edge/Chrome에서 열고 설정에서 NAS 공유 폴더를 선택하면 브라우저가 직접 읽습니다. 매번 사람이 수집 버튼을 눌러야 하고 이력이 쌓이지 않으므로 시험용이나 임시 대체용입니다.

## 새 버전 배포
`template.html`이나 `aoi_collect.py`를 고쳐 기본 브랜치에 푸시하기만 하면 됩니다. 버전 번호를 따로 올릴 필요 없이 수집기가 다음 실행 때 커밋 SHA 차이를 보고 자동으로 받아 갑니다. 화면 상단에도 새 커밋 안내가 표시됩니다.
