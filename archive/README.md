# 보관물 (archive/)

더 이상 코드·문서·테스트가 참조하지 않지만 **지우지 않기로 한** 파일들이다(사용자 결정 D62, 2026-09-20).

- 옮길 때는 `git mv` 로 옮겨 이력이 이어진다. 큰 텍스트·HTML 은 gzip 으로 보관한다(`gzip -n -9`, 압축을 풀면 원본과 바이트까지 같다).
- 원본의 sha256 은 [`SHA256SUMS`](SHA256SUMS) 에 있다 — `.gz` 항목은 **압축을 푼 내용**의 지문이다. 가드: `dev/tests/test_archive.py`.
- 이 폴더는 배포·업데이트 payload 에 들어가지 않는다(`updater._UPDATE_TOP_ALLOW` 허용 목록 밖, 가드 `test_update_payload.py`).
- 여기 있는 것은 **참고 기록**이다. 현재 규칙은 `CLAUDE.md`, 현재 상태는 `진행상황.md`.

| 원래 위치 | 지금 위치 | 무엇 · 왜 보관 |
|---|---|---|
| `v6cmp.png` · `v6home.png` · `v6set.png` · `v6trend.png` (저장소 루트) | `screenshots/` | 9/13 옛 화면(v6, 다크 테마) 스크린샷. 어떤 문서도 참조하지 않았다 |
| `docs/screenshots/compare.png` · `home.png` · `trend.png` | `screenshots/` | 같은 시기 옛 화면 스크린샷 |
| `docs/aoi_collector_demo.html` | `docs/aoi_collector_demo.html.gz` | 옛 브라우저 데모(다크 테마, Google Fonts 링크 포함 — 지금 제품 화면의 '외부 요청 0' 규칙과 맞지 않아 안내에서 뺐다). 실제 현장 데이터가 들어 있으니 바깥에 배포하지 않는다 |
| `docs/design/dashboard-redesign/PROMPT.md` | `design/PROMPT.md` | 디자인 handoff 의 '할 일 4가지' 프롬프트 — 9/19 전부 반영됨(CHANGELOG 10절) |
| `docs/design/dashboard-redesign/PROMPT_extract-script.md` | `design/PROMPT_extract-script.md` | 추출 스크립트 회수 요청문 — 9/20 답을 받아 `scripts/` 에 들어왔다 |
| `docs/design/dashboard-redesign/patch/collector-backup-lookup.md` | `design/patch/collector-backup-lookup.md` | 수집기 수정안 — 커밋 `6b4a114` 로 적용됨(`devices.scan_dirs_of` · `collect.ini_roots_for` · `MOVED_ONLY`) |
| `docs/design/dashboard-redesign/app/Err-Popup-A.dc.html` | `design/app/Err-Popup-A.dc.html` | 승인된 Error 상세 팝업 시안 — 본체와 제품 화면에 반영됨 |
| `docs/design/dashboard-redesign/app/AOI-4 해결 제안.dc.html` · `aoi-recovery.json` | `design/app/` | 수집기 수정 제안서와 그 검증 결과 — 위 patch 와 함께 적용 완료. 제안서는 `support.js` 런타임과 `aoi-recovery.json` 을 같은 폴더에서 읽는 DC 형식이라 여기서는 열리지 않는다(내용은 텍스트로 읽을 수 있다) |

## 같은 결정으로 압축만 한 것(위치는 그대로)

| 파일 | 왜 |
|---|---|
| `dev/samples/AOI_capacity_2026-09-16_3일치.html` → `.html.gz` | 첫 현장 수집. 30일치 샘플이 상태 문구·형식·열을 전부 덮지만(`dev/samples/README.md`), 독특한 회귀가 있을 수 있어 지우지 않는다 |
| `dev/samples/AOI_capacity_2026-09-17_30대.html` → `.html.gz` | 30대 첫 수집. 같은 이유 |

압축을 풀어 보려면: `gunzip -k 파일.gz` (원본은 남긴다). 코드에서는 `dev/tests/sample_rows.load` 가 `.gz` 를 그대로 읽는다.
