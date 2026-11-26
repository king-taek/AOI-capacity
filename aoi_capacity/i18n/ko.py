"""사용자에게 보이는 한국어 문구 — 이 파일에만 둔다.

규칙
- 이름은 `기능_역할` (BTN_, NAV_, COLLECT_, UPDATE_, NAS_ …). `_FMT` 로 끝나면 `str.format` 자리표시자가 있다.
- 로그 메시지는 여기 두지 않는다(로거 인자에 그대로 쓴다).
- 순수 상수 모듈: 표준 라이브러리 외 import 금지(첫 실행 부트스트랩 전에도 로드된다).
"""

# ── 앱 ──────────────────────────────────────────────────────────────────
APP_TITLE = "AOI Capacity"
APP_BRAND = "AOI 수집기"
CREDIT = "정확 경로만 확인 · 재귀 검색 없음 · NAS 원본은 읽기만"

# ── 내비게이션 ─────────────────────────────────────────────────────────
NAV_DEVICES = "장비 목록"
NAV_DEVICES_SUB = "NAS 경로 · 폴더"
NAV_COLLECT = "수집"
NAV_COLLECT_SUB = "지금 수집 · 결과 열기"
NAV_LAST_COLLECT_FMT = "마지막 수집 {when}"
NAV_LAST_COLLECT_NEVER = "아직 수집한 적 없음"

# ── 공통 버튼 ──────────────────────────────────────────────────────────
BTN_OK = "확인"
BTN_CANCEL = "취소"
BTN_YES = "예"
BTN_NO = "아니오"
BTN_CLOSE = "닫기"
BTN_STOP = "중지"
BTN_BROWSE = "찾아보기…"
BTN_SAVE = "저장"
BTN_REVERT = "되돌리기"
BTN_ADD_ROW = "행 추가"
BTN_REMOVE_ROW = "행 삭제"
BTN_IMPORT_CSV = "CSV 가져오기…"
BTN_EXPORT_CSV = "CSV 내보내기…"
BTN_CHECK_CONN = "연결 확인"
BTN_AUTO_FOLDER = "* 자동"
BTN_COLLECT_NOW = "지금 수집"
BTN_OPEN_FOLDER = "폴더 열기"
BTN_OPEN_LOG = "로그 열기"
BTN_OPEN_RESULT = "결과 열기"
BTN_OPEN_RESULT_FOLDER = "폴더 열기"
BTN_CHECK_UPDATE = "업데이트 확인"
BTN_LOAD_DEFAULT_DEVICES = "예시 목록 불러오기"
BTN_MORE = "더보기"

# ── 대시보드 ───────────────────────────────────────────────────────────

# ── 장비 목록 ──────────────────────────────────────────────────────────
DEV_PAGE_TITLE = "장비 목록"
DEV_PAGE_SHORT = "한 줄이 장비 하나 · 이 PC 에만 저장되고 NAS 에는 아무것도 쓰지 않습니다"
DEV_PAGE_HELP = ("한 줄이 장비 하나입니다. NAS 경로는 드라이브 문자(X:\\)나 주소(\\\\10.142.80.90\\공유) 어느 쪽이든 되고, "
                 "폴더는 NAS 경로 아래 장비 폴더 이름입니다. 폴더를 비우면 NAS 경로 자체가 장비 폴더이고, "
                 "* 이면 그 안의 장비 폴더를 자동 등록합니다(수집 범위 제한 중에는 공유를 나열하지 않고 허용 목록의 장비 이름만 확인합니다). "
                 "이 목록은 이 PC 에만 저장되며 NAS 에는 아무것도 쓰지 않습니다.")
DEV_COL_NAME = "장비명"
DEV_COL_ROOT = "NAS 경로"
DEV_COL_SUB = "폴더"
DEV_COL_ON = "사용"
DEV_COL_MEMO = "메모"
DEV_COL_STATUS = "상태"
DEV_STATUS_OK = "정상"
DEV_STATUS_AUTO_FMT = "자동 · {n}대"
DEV_STATUS_NO_REPORT = "Report 폴더 없음"
DEV_STATUS_UNREACHABLE = "접근 불가"
DEV_STATUS_CHECKING = "확인 중…"
DEV_STATUS_OUT_OF_SCOPE = "수집 안 함(범위 밖)"
DEV_SAVED_TOAST = "장비 목록을 저장했습니다"
DEV_SAVED_INLINE = "✓ 저장됨"
DEV_SAVE_FAIL_TITLE = "장비 목록을 저장하지 못했습니다"
DEV_SAVE_LOCKED = "devices.csv 가 다른 프로그램(Excel 등)에서 열려 있거나 쓸 수 없는 위치입니다. 그 프로그램을 닫은 뒤 다시 저장하세요. 표에 고친 내용은 그대로 있습니다."
DEV_CHECK_SUMMARY_FMT = "연결 확인 — {items}"
DEV_CHECK_ITEM_FMT = "{label} {n}"
DEV_STATUS_AUTO = "자동"
DEV_STATUS_ERROR = "확인 실패"
DEV_IMPORTED_FMT = "{n}행을 가져왔습니다"
DEV_UNSAVED_TITLE = "저장하지 않은 변경"
DEV_UNSAVED_BODY = "장비 목록에 저장하지 않은 변경이 있습니다. 저장할까요?"
DEV_BROWSE_TITLE = "장비 폴더 또는 NAS 공유 선택"
DEV_CSV_FILTER = "CSV 파일 (*.csv)"
DEV_EMPTY_HINT = "장비가 없습니다. '행 추가' 또는 '예시 목록 불러오기'를 누르세요."

# ── 수집 ───────────────────────────────────────────────────────────────
COLLECT_PAGE_TITLE = "수집"
# 상황별 수집 카드(9/23 — "어떤 상황에 어떤 옵션을 눌러야 하는지 직관적으로"): 제목 · 이럴 때 · 무엇을 하나 · 걸리는 시간
COLLECT_SEC_TROUBLE = "다른 수집 방법"
COLLECT_SEC_HTML = "결과 파일만 다시 만들기"
COLLECT_SEC_DEV = "조사 도구"
COLLECT_SEC_SETTINGS = "설정"
MODE_NORMAL_TITLE = "평소 수집"
MODE_NORMAL_WHEN = "새로 생긴 Report 만 읽습니다"
MODE_NORMAL_WHAT = "지난 수집 뒤 새로 생긴 Report 만 읽습니다. 수집을 며칠 쉬었어도 이것으로 이어서 읽습니다."
MODE_FIRST_TITLE = "처음 수집"
MODE_FIRST_WHEN = "이 PC 에서 처음 한 번 — 최근 Report 를 전부 읽습니다"
MODE_FIRST_WHAT_FMT = "모든 장비의 최근 {days}일 Report 를 전부 읽습니다. 처음 한 번만이고, 장비 수에 따라 수십 분 걸릴 수 있습니다."
MODE_BACKFILL_TITLE = "빠진 날 채우기"
MODE_BACKFILL_WHEN = "비어 있는 날 · 장비가 있을 때"
MODE_BACKFILL_WHAT_FMT = "최근 {days}일 안에서 아직 읽지 않은 Report 를 모두 찾아 읽습니다. 이미 읽은 것은 건너뜁니다."
MODE_REFRESH_TITLE = "최근 며칠 다시 읽기"
MODE_REFRESH_WHEN = "최근 결과가 이상할 때"
MODE_REFRESH_WHAT = "이미 읽은 것도 이 기간은 다시 읽습니다. 그 이전 기록은 그대로 둡니다."
MODE_REFRESH_DAYS_PREFIX = "최근"
MODE_REFRESH_DAYS_SUFFIX = " 일"
MODE_RECOVER_TITLE = "시간 미확인 복구"
MODE_RECOVER_WHEN = "'시간 미확인' 이 많을 때"
MODE_RECOVER_WHAT = "INI 를 못 찾았던 Report 만 다시 읽어 시각을 되찾습니다. 새 Report 도 함께 읽습니다."
COLLECT_PHASE_RDL_FMT = "RDL INI 읽는 중 · {device}"
MODE_RANGE_TITLE = "기간 다시 읽기"
MODE_RANGE_WHEN = "고른 기간만 처음부터 다시 읽기"
MODE_RANGE_WHAT = "고른 기간에 끝난 Report(와 KLA Wafer)를 이미 읽었어도 다시 읽습니다. 기간 밖 기록은 그대로 둡니다."
COLLECT_PLAN_RANGE_FMT = "{a} ~ {b} 에 끝난 Report 를 다시 읽습니다"
MODE_BADGE_REC = "추천"
MODE_BADGE_MEDIUM = "몇 분"
MODE_BADGE_SLOW = "오래 걸림 · 수십 분"
MODE_BADGE_TARGET_FMT = "대상 Report {n}개"
COLLECT_TROUBLE_LOCKED = "처음 수집을 마치면 쓸 수 있습니다"
COLLECT_BUSY_GAPS = "빈칸을 채우는 중이라 잠시 수집할 수 없습니다"
COLLECT_BUSY_PUBLISH = "공유 폴더에 올리는 중이라 잠시 수집할 수 없습니다"
COLLECT_BUSY_FAILLOGS = "실패 로그를 모으는 중이라 잠시 수집할 수 없습니다"
COLLECT_DONE_OK_FMT = "✓ 수집 완료 · {devices}대 · {elapsed}"
BTN_COLLECT_AGAIN = "다시 수집"
MODE_BADGE_NONE = "대상 없음"
MODE_DISABLED_FIRST = "처음 수집을 마친 뒤에 쓸 수 있습니다."
MODE_STALE_FMT = "마지막 수집이 {days}일 전 — 이번엔 평소보다 조금 더 걸립니다"
MODE_RUN_FMT = "{title} 시작"
COLLECT_PLAN_FIRST_FMT = "읽을 기간: 최근 {days}일"
COLLECT_PLAN_INCR_FMT = "읽을 장비: {n}대"
# ── 수집 모드(D60): 문구는 코드가 실제로 하는 일과 같아야 한다 ────────────────────────────
#   backfill = 검색 창만 넓힌다(캐시된 파일은 건너뛴다) · refresh = 창 안의 캐시된 Report 도 다시 읽는다(창 밖 이력 보존)
#   full/rebuild = 보관 기간 전부를 새 후보 캐시에 모아 검증 뒤 교체(실패하면 기존 캐시 유지, 이력 삭제 없음)
COLLECT_PLAN_BACKFILL_FMT = "최근 {days}일 중 아직 안 읽은 Report 만 읽습니다 · 읽은 것은 건너뜁니다"
COLLECT_PLAN_REFRESH_FMT = "최근 {days}일 Report {reread}개를 다시 읽습니다 · 그 전 {keep}개는 그대로"
COLLECT_PLAN_RECOVER_FMT = "시간 미확인 Report {n}개를 다시 읽습니다"
COLLECT_PLAN_RECOVER_NONE = "다시 읽을 Report 가 없습니다 — 새 Report 만 읽습니다"
COLLECT_PLAN_LOADING = "수집 계획 확인 중…"
COLLECT_OUTPUT_DIR = "결과 폴더"
COLLECT_OUTPUT_DEFAULT_HINT = "비우면 이 PC 의 데이터 폴더에 저장합니다. NAS 폴더는 지정할 수 없습니다."
COLLECT_RESULT_TITLE = "결과 파일"
COLLECT_RESULT_NONE = "아직 결과 파일이 없습니다"
COLLECT_LOG_TITLE = "로그"
COLLECT_RUNNING = "수집 중…"
COLLECT_IDLE = ""
COLLECT_DONE_TOAST_FMT = "수집 완료 · 장비 {devices}대 · {elapsed}"
COLLECT_DONE_TOAST_PUBLISHED = " · AOI LOT 올림"   # 11/25(LOTE-14): 수집 창 문구는 팀원이 누르는 바로가기 이름 'AOI LOT' 으로
COLLECT_DONE_PUBLISH_FAILED_FMT = ("AOI LOT 배포는 올리지 못했습니다(수집 결과는 정상 저장됨): {path}\n{error}\n"
                                   "공유 폴더 연결 · 경로를 확인하고 알림의 '다시 올리기' 를 누르세요.")
COLLECT_DONE_PUBLISH_LOCKED_FMT = ("AOI LOT 배포 파일은 올렸지만 안내 파일이 열려 있어 최신으로 바꾸지 못했습니다: {path}\n"
                                   "다음 수집 때 다시 가리킵니다.")
DUR_SEC_FMT = "{s}초"
DUR_MIN_FMT = "{m}분 {s}초"
DUR_HOUR_FMT = "{h}시간 {m}분"
OUTCOME_GO_DEVICES = "장비 목록 확인"
OUTCOME_SHOW_LOG = "로그 보기"
COLLECT_DONE_UNREACHABLE_HINT = "NAS 연결이나 장비 목록의 경로를 확인해 보세요. 다른 장비는 정상으로 저장됐습니다."
COLLECT_DONE_WITH_ERRORS_TITLE = "수집은 끝났지만 일부 문제가 있습니다"
COLLECT_DONE_SEE_LOG = "일부 Report 를 읽지 못했습니다 — 로그에 자세히 있습니다."
# ── 부분 성공(C06)·캐시 손상(C15) 안내 — 수집은 끝났고 HTML 은 정상이다 ──────────────────────
COLLECT_DONE_CSV_FAILED_FMT = ("CSV 는 저장하지 못했습니다(HTML 결과 화면은 정상 저장됨): {path}\n{error}\n"
                               "Excel 등에서 열려 있으면 닫고 다시 수집하세요. 이전 CSV 는 그대로 남아 있습니다.")
COLLECT_CACHE_CORRUPT_FMT = ("캐시 파일을 읽을 수 없어 처음부터 다시 수집했습니다. 손상된 원본은 지우지 않고 보존했습니다: {path}")
COLLECT_CANCELLED_TOAST = "중지했습니다 · 읽은 것은 저장됨"
COLLECT_CANCELLED_SAVED_FMT = "중지: Report {n}개까지 저장했습니다. 다시 수집하면 남은 것부터 이어서 읽습니다."
COLLECT_PLAN_RESUME_REBUILD = "▶ 명령줄의 '전체 다시 만들기'(--rebuild-all)가 중간에 멈췄습니다. 같은 명령을 다시 실행하면 이어서 합니다."
COLLECT_PLAN_RESUME_REFRESH = "▶ 지난 '다시 읽기' 가 중간에 멈췄습니다. 같은 설정으로 다시 누르면 이미 읽은 것은 건너뜁니다."
CLI_CANCELLED = "중지했습니다 — 읽은 것까지 저장했습니다. 같은 명령을 다시 실행하면 이어서 합니다."
COLLECT_FAILED_TITLE = "수집 실패"
COLLECT_NO_DEVICES_TITLE = "장비가 없습니다"
COLLECT_NO_DEVICES_BODY = "'장비 목록' 에서 장비를 먼저 등록하세요."
COLLECT_BUSY_TITLE = "수집이 진행 중입니다"
COLLECT_BUSY_BODY = "수집이 끝난 뒤 다시 시도하세요."
COLLECT_OUTPUT_ON_NAS_TITLE = "결과 폴더로 쓸 수 없는 위치"
COLLECT_OUTPUT_ON_NAS_BODY = "NAS 원본 폴더 안에는 결과를 저장할 수 없습니다. 이 PC 의 폴더를 고르세요."

# 수집 단계 문구 — collect.progress(done, total, phase) 의 phase 로 전달되어 로딩창에 그대로 표시된다.
COLLECT_PHASE_DEVICES = "장비 목록 확인"
COLLECT_PHASE_LIST_FMT = "{device} · 새 Report 찾는 중 ({i}/{n}대)"
# 11/25: 굵은 줄은 단계 · 장비, 줄바꿈 뒤(파일 이름)는 로딩창의 흐린 줄로 간다(CLI 는 한 줄로 이어 찍는다)
COLLECT_PHASE_PARSE_FMT = "Report 읽는 중 · {device}\n{name}"
COLLECT_PHASE_RETRY_FMT = "읽지 못한 Report 한 번 더 읽는 중 · {device}\n{name}"
COLLECT_PHASE_RETENTION = "오래된 이력 정리"
COLLECT_PHASE_SAVE = "캐시 저장 중"
COLLECT_PHASE_ROWS = "결과 정리 중"
COLLECT_PHASE_PUBLISH_FMT = "공유 폴더에 올리는 중 {i}/{n} · {what}"
PUBLISH_WHAT_LOT = "AOI LOT"   # 수집 창의 배포 이름은 바로가기 이름 'AOI LOT' 하나(LOTE-14 · COPY-11)
PUBLISH_WHAT_FULL = "전체"
COLLECT_PHASE_WRITE = "화면 만드는 중"
COLLECT_PHASE_DONE = "완료"

# 로딩창
LOADING_COLLECT_TITLE = "데이터 수집"
LOADING_ELAPSED_FMT = "{elapsed}"
LOADING_ELAPSED_TIP = "시작한 뒤 지난 시간"
LOADING_COUNT_FMT = "{done} / {total}"
LOADING_LEFT_FMT = "· 남은 {t}"
LOADING_LEFT_TIP = "지금 단계의 속도로 센 남은 시간 — 단계가 바뀌면 다시 셉니다"
LOADING_DEVICES_FMT = "장비 {done} / {total}"
LOADING_STOPPING = "중지하는 중…"
LOADING_STOPPING_NOTE = "지금 읽던 것만 마치고 멈춥니다 · 읽은 것은 저장됩니다"
LOADING_LEGEND_WAIT = "대기"
LOADING_LEGEND_READ = "읽는 중"
LOADING_LEGEND_DONE = "완료"
LOADING_LEGEND_ERR = "접근 불가"
LOADING_LEGEND_PARTIAL = "일부 실패"
LOADING_LEGEND_SKIP = "건너뜀"
LOADING_DEVICE_ERR_FMT = "{name} 접근 불가 — 끝난 뒤 알림에 정리합니다"
LOADING_DEVICE_ERR_MORE_FMT = "{name} 외 {n}대 접근 불가 — 끝난 뒤 알림에 정리합니다"
LOADING_CLOSE_BUSY_TITLE = "공유 폴더에 올리는 중입니다"
LOADING_CLOSE_BUSY_BODY = ("수집은 끝났고 배포 파일을 올리는 중입니다. 올리기가 끝난 뒤 창을 닫을까요?\n\n"
                           "'아니오' 는 지금 바로 닫습니다(올리던 배포는 다음 수집 때 다시 올립니다) · '취소' 는 창을 그대로 둡니다.")
LOADING_CLOSE_BUSY_BODY_MANUAL = ("배포 파일을 공유 폴더에 올리는 중입니다. 올리기가 끝난 뒤 창을 닫을까요?\n\n"
                                  "'아니오' 는 창을 바로 닫고 올리기는 뒤에서 마저 끝냅니다 · '취소' 는 창을 그대로 둡니다.")
LOADING_CLOSE_WAITING = "올리기가 끝나면 창을 닫습니다"

# ── 설정 · 정보 ────────────────────────────────────────────────────────
SET_BACKFILL_DAYS = "처음 수집 기간"
SET_BACKFILL_PREFIX = "최근 "
SET_BACKFILL_SUFFIX = "일"
SET_COLLECT_RANGE_HELP = ("처음 보는 장비는 이 기간 안의 Report 를 전부 읽습니다. 그다음부터는 새 Report 만 읽습니다. "
                          "기간을 늘리면 첫 수집이 그만큼 오래 걸립니다.")
SET_DATA_DIR = "데이터 폴더"
SET_VERSION = "버전"
SET_VERSION_UNKNOWN = "미상 (개발 실행)"
SET_NAS_NOTICE = "이 프로그램은 NAS 의 Report 와 WaferInfo.ini 를 읽기만 하며, NAS 에는 어떤 파일도 만들거나 바꾸지 않습니다."
SET_UTIL_DEFINITION = ("가동률 = (Scan + Rescan 시간) ÷ 24시간. 수집한 날(오늘)만 00:00 부터 모든 장비의 마지막 기록까지로 나눕니다 "
                       "('오늘' 은 수집 시각의 날짜 — 며칠 뒤 열어도 같은 숫자). Test LOT 은 전부 Test 로 분모에만 들어갑니다. "
                       "Rescan 은 같은 자재(Job · LOT · Wafer ID)의 앞선 시도가 Pass 였을 때만이고, Error·Skipped 뒤의 재시도는 Scan 입니다. "
                       "한 장비의 1분은 한 번만 셉니다 — INI 로 확실한 구간을 먼저 놓고, 배치 시작~종료의 남은 빈 시간을 INI 가 없는 Wafer 들이 나눠 갖습니다(팝업에 '배치 시각으로 추정' 표). "
                       "Error 는 LOT 단위로 세고, Error 를 담은 배치가 끝난 뒤 다음 기록까지의 공백을 '에러 후 대기' 로 봅니다.")

# ── 행 비고(data_issue) — 캐시의 `issue_codes` 를 출력 때 문장으로(C12 · collect.issue_text). 위치 인자 {0},{1} ──────────
ISSUE_JOIN = "; "
ISSUE_TEXTS = {
    "NO_WAFER_ID_ROW": "LoadPort/Slot 행이라 INI 경로를 만들 수 없음",
    "JOB_UNKNOWN": "Job 을 알 수 없어 INI 경로를 만들지 않음",
    "SETUP_UNKNOWN": "Setup 을 알 수 없어 INI 경로를 만들지 않음",
    "MOVED_ONLY": "Wafer 폴더에 MoveResultFlag 만 있고 WaferInfo.ini 없음 — 이동만 되고 스캔 안 함",
    "INI_NOT_FOUND": "예상 경로에 WaferInfo.ini 없음",
    "INI_NOT_FOUND_BACKUPS": "예상 경로와 백업 폴더 {0}개 어디에도 WaferInfo.ini 없음",
    "INI_READ_ERROR": "{0}",
    "TIME_MISSING_OR_REVERSED": "Wafer 시작/종료 시각 누락 또는 역전",
    "INI_STALE": "이 배치 시각 밖의 INI(다시 검사하며 덮어써짐) — 시간 미사용",
    "LOT_MISMATCH": "LOT 불일치",
    "WAFER_ID_MISMATCH": "Wafer ID 불일치",
    "FOUND_IN_BACKUP": "백업 폴더에서 찾음: {0}",
    "JOB_FOLDER_DIFFERS": "Job 폴더 이름이 Report 와 다름: {0}",
    "BATCH_NO_WAFER": "검사된 Wafer 없음 — 배치 시각으로만 표시 (행 {0}개 중 오류 {1}개)",
    "SLOT_ERROR": "자리표시 행 Error — Report 당 1건 · 영향 Slot {0}개 · 시간 미확인(Batch 범위 추정)",
    "MULTI_LOT": "LOT 여러 개({0})",
    "MULTI_JOB": "Job 여러 개({0})",
}

# ── 헤드리스 CLI(aoi_capacity/cli.py) 출력 문구 ──────────────────────────────────────────
CLI_DESC = "AOI Capacity 수집기(헤드리스)"
CLI_HELP_REFRESH_WINDOW = ("최근 N일 안의 Report 는 캐시에 있어도(수정시각이 같아도) 다시 읽음. 창 밖 이력은 그대로 두고, "
                           "다시 읽다 실패한 Report 는 이전 행을 유지한 채 다음에 재시도")
CLI_HELP_REBUILD_ALL = ("보관 기간(retention_days) 전부를 새 후보 캐시에 모아 검증을 통과할 때만 기존 캐시와 바꿈. "
                        "실패하면 기존 캐시를 그대로 둠(이력 삭제 없음)")
CLI_HELP_FULL = "--rebuild-all 의 옛 별칭(같은 동작)"
CLI_HELP_BACKFILL = ("검색 창을 최근 backfill_days 로 넓힘. 이미 캐시된 Report(수정시각 같음)는 건너뜀 — "
                     "다시 읽으려면 --refresh-window")
CLI_HELP_RECOVER = "INI 를 못 찾았던 Report 만 다시 읽음(누락 복구)"
CLI_HELP_UPDATE = "시작 전에 GitHub 최신 커밋으로 자기 갱신(선택). 갱신되면 같은 인자(--update 제외)로 수집을 한 번 다시 실행하고 그 종료 코드를 돌려줌"
CLI_UPDATE_GIT_SKIP = "git 작업 폴더 — 자동 업데이트 생략(git pull 사용)"
CLI_UPDATE_DOWNLOADING_FMT = "새 버전 {sha} 다운로드"
CLI_UPDATE_DONE_RERUN = "갱신 완료 — 새 코드로 수집을 다시 실행합니다(끝날 때까지 기다립니다)"
CLI_UPDATE_RERUN_DONE_FMT = "다시 실행 종료 코드 {code}"
CLI_UPDATE_LATEST = "최신 버전입니다"
CLI_UPDATE_HELD_FMT = "업데이트 보류({sha}): {reason}"
CLI_UPDATE_CHECK_FAILED_FMT = "업데이트 확인 실패: {error}"
CLI_UPDATE_STEP_ERROR_FMT = "업데이트 단계 오류(무시): {error}"
CLI_PLAN_FMT = ("모드 {mode} · 캐시 Report {total}개(다시 읽기 {reread} · 그대로 {keep} · 누락 복구 {recover})"
                " · 새 Report 는 NAS 를 본 뒤 셈")
CLI_REBUILD_REJECTED_FMT = "전체 다시 만들기 거부 — 기존 캐시·HTML 은 그대로입니다: {error}"
CLI_CACHE_CORRUPT_FMT = "캐시 파일이 손상되어 처음부터 다시 수집했습니다. 손상 원본 보존: {path}"
CACHE_UNREADABLE_FMT = ("캐시 파일을 열 수 없습니다 — 다른 프로그램(백신 · 백업 · 다른 수집)이 쓰는 중일 수 있으니 잠시 뒤 다시 해 주세요."
                        " 캐시는 그대로 두었습니다: {path} ({error})")
CLI_UNREACHABLE_FMT = "접근 실패 장비: {items}"
CLI_UNREACHABLE_ITEM_FMT = "{name} ({error})"
CLI_PARTIAL_FMT = "일부 Report 를 읽지 못한 장비: {items}"
CLI_PARTIAL_ITEM_FMT = "{name} ({n}개)"
CLI_WARNING_FMT = "경고({kind}): {path} — {error}"
CLI_DONE_FMT = "완료 · {sec:.1f}초 · 종료 코드 {code}"

# ── 설정 값 검사(C13 · utils/config.py) — 성능·기간 값은 경고 + 고침, 범위·경로 값은 실행 차단 ────────────
CFG_TRUE = "켬"
CFG_FALSE = "끔"
CFG_BAD_INT_FMT = "설정 '{key}' 값 {value} 은(는) 정수가 아니라 기본값 {default} 을(를) 씁니다"
CFG_OUT_OF_RANGE_FMT = "설정 '{key}' 값 {value} 은(는) 허용 범위({lo}~{hi}) 밖이라 {fixed} 으로 맞춥니다"
CFG_BAD_BOOL_FMT = "설정 '{key}' 값 {value} 은(는) 참/거짓이 아니라 '{default}' 으로 둡니다"
CFG_BAD_STR_FMT = "설정 '{key}' 값 {value} 은(는) 문자열이 아니라 기본값 '{default}' 을(를) 씁니다"
CFG_RETENTION_LT_BACKFILL_FMT = "이력 보관 기간({retention}일)이 처음 수집 기간({backfill}일)보다 짧아 {fixed}일로 늘립니다"
CFG_FATAL_SCOPE_FMT = "수집 범위(scope_devices) 설정이 장비 이름 목록이 아니라 수집을 시작하지 않습니다: {value}"
CFG_FATAL_PATH_FMT = "경로 설정 '{key}' 이(가) 문자열이 아니라 수집을 시작하지 않습니다: {value}"
CFG_FATAL_FOLDER_NAME_FMT = "폴더 이름 설정 '{key}' 에 경로 구분자나 상위 폴더 표기가 있어(다른 폴더를 가리킬 수 있음) 수집을 시작하지 않습니다: {value}"
CLI_CFG_WARNING_FMT = "설정 경고: {message}"
CLI_CFG_FATAL_FMT = "설정 오류 — 수집을 시작하지 않습니다: {message}"

# ── NAS 안전장치 ───────────────────────────────────────────────────────
NAS_WRITE_REFUSED_FMT = "NAS 원본 폴더 안에는 파일을 쓸 수 없습니다: {path}  (NAS: {root})"

# ── 자동 업데이트 ──────────────────────────────────────────────────────
UPDATE_CHECK_TITLE = "업데이트 확인"
UPDATE_CHECKING = "업데이트를 확인하는 중…"
UPDATE_AVAILABLE_TITLE = "새 버전이 있습니다"
UPDATE_AVAILABLE_BODY_FMT = "({sha}{message}) — 지금 받을까요?\n\n받은 뒤 프로그램을 다시 실행하면 적용됩니다."
UPDATE_UNKNOWN_CURRENT_FMT = "현재 버전을 알 수 없어 최신 버전({sha})을 받습니다. 지금 받을까요?"
UPDATE_LATEST = "이미 최신 버전입니다."
UPDATE_NAV_FMT = "새 버전 {sha} 받기"
UPDATE_NAV_TIP = "프로그램을 켜 둔 동안 새 버전이 나왔습니다. 누르면 지금 받을지 묻습니다."
UPDATE_UNKNOWN = "업데이트를 확인할 수 없습니다 (네트워크 또는 GitHub 접근 문제)."
UPDATE_GIT_HINT = "개발용 git 폴더에서 실행 중이라 자동 업데이트를 적용하지 않습니다. git pull 을 사용하세요."
UPDATE_DOWNLOADING = "새 버전을 받는 중…"
UPDATE_OVERLAY_TITLE = "업데이트"
UPDATE_PHASE_DOWNLOAD = UPDATE_DOWNLOADING
UPDATE_PHASE_EXTRACT = "압축을 푸는 중…"
UPDATE_PHASE_PREPARE = "새 파일을 준비하는 중…"
UPDATE_PHASE_DEPS = "필요한 패키지를 확인하는 중…"
UPDATE_PHASE_APPLY = "적용하는 중…"
UPDATE_PHASE_DONE = "완료"
UPDATE_DONE_RESTART = "업데이트를 받았습니다. 프로그램을 다시 실행하면 새 버전이 적용됩니다."
UPDATE_DONE_RESTART_STAGED = UPDATE_DONE_RESTART
UPDATE_DEPS_CHANGED = "\n\n필요한 패키지 목록이 바뀌었습니다. 다음 실행 때 설치가 진행될 수 있습니다."
UPDATE_NEEDS_NEW_BUNDLE = ("새 버전에 필요한 패키지를 이 PC 에 설치하지 못해 업데이트를 적용하지 않았습니다. "
                           "인터넷 연결을 확인하거나 새 배포본 zip 을 받아 설치하세요.")
UPDATE_FAILED = "업데이트에 실패했습니다. 기존 버전을 그대로 사용합니다."
UPDATE_BUSY_BODY = "수집이 진행 중일 때는 업데이트를 적용할 수 없습니다. 수집이 끝난 뒤 다시 시도하세요."
UPDATE_ERR_HTTP_FMT = "HTTP {code} ({host})"
UPDATE_ERR_TIMEOUT_FMT = "응답 시간 초과 ({host})"
UPDATE_ERR_CONNECT_FMT = "연결 실패 — {host} ({reason})"
UPDATE_ERR_OTHER_FMT = "{kind} — {host} ({detail})"
UPDATE_ERR_NO_SHA_API = "GitHub API 응답에 커밋 정보가 없습니다"
UPDATE_ERR_NO_SHA_ATOM = "GitHub 피드에서 커밋을 찾지 못했습니다"
UPDATE_ERR_GITHUB = "GitHub 에 연결할 수 없습니다"
UPDATE_ERR_BAD_ZIP = "받은 파일이 올바른 배포 zip 이 아닙니다"
UPDATE_ERR_VERIFY_FMT = "새 파일 검증 실패: {detail}"
UPDATE_ERR_MISSING_FILE_FMT = "필수 파일 없음: {rel}"
UPDATE_ERR_EMPTY_FILE_FMT = "빈 파일: {rel}"
UPDATE_ERR_STAT_FAIL_FMT = "파일을 읽을 수 없음: {rel} ({error})"
UPDATE_ERR_TEMPLATE_DATA = "template.html 에 __DATA__ 자리가 없습니다"
UPDATE_ERR_QSS_FMT = "style.qss 를 렌더링할 수 없습니다 ({error})"
UPDATE_ERR_PIP_START_FMT = "패키지 설치를 시작하지 못했습니다 ({error})"
UPDATE_ERR_PIP_RC_FMT = "패키지 설치 실패 (pip 종료 코드 {rc})"
UPDATE_ERR_NO_TREE = "받은 zip 에 앱 폴더(aoi_capacity)가 없습니다"

# ── 자동 업데이트 · 보호 장치(P1: TLS 검증 · CI 게이트 · zip 검사 · 허용 목록 · 저널 롤백 · pip 상한) ──
UPDATE_ERR_TLS_VERIFY_FMT = ("보안 연결(TLS)의 인증서를 확인할 수 없어 업데이트를 중단했습니다 — {host} ({reason}). "
                             "회사 프록시가 인증서를 바꿔 끼우는 환경이면 그 인증서를 Windows 신뢰 저장소에 등록한 뒤 다시 시도하세요. "
                             "검증 없이 받는 길은 없습니다.")
UPDATE_ERR_BAD_SHA_FMT = "대상 커밋 식별자가 40자리 SHA 가 아닙니다 ({sha})"
UPDATE_CI_QUERY_FAILED_FMT = "GitHub 자동 테스트(tests) 결과를 조회하지 못했습니다 — {detail}"
UPDATE_CI_PENDING = "새 커밋의 자동 테스트(tests)가 아직 끝나지 않았습니다. 잠시 뒤 다시 확인하세요."
UPDATE_CI_FAILED = "새 커밋의 자동 테스트(tests)가 실패했습니다. 통과한 커밋이 올라오면 그때 받습니다."
UPDATE_CI_NO_RUN = "새 커밋에 대한 자동 테스트(tests) 기록이 없습니다. 기록이 생길 때까지 현재 버전을 유지합니다."
UPDATE_HELD_FMT = "새 커밋({sha})이 있지만 아직 적용하지 않습니다. 현재 버전을 그대로 사용합니다.\n\n{reason}"
UPDATE_ERR_ZIP_TOO_BIG_FMT = "받은 zip 이 한도를 넘습니다 (파일 {files}개 · {mb} MB — 한도 {max_files}개 · {max_mb} MB)"
UPDATE_ERR_ZIP_ENTRY_FMT = "받은 zip 에 허용되지 않는 경로가 있습니다: {name}"
UPDATE_ERR_ZIP_CASE_FMT = "받은 zip 에 대소문자만 다른 경로가 있습니다: {name}"
UPDATE_ERR_ZIP_ROOTS_FMT = "받은 zip 의 최상위 폴더가 하나가 아닙니다 ({roots})"
UPDATE_ERR_ZIP_ROOT_SHA_FMT = "받은 zip 의 폴더 이름({root})이 대상 커밋({sha})과 맞지 않습니다"
UPDATE_ERR_UNEXPECTED_TOP_FMT = "새 트리에 허용 목록 밖의 항목이 있습니다: {names}"
UPDATE_ERR_APPLY_ROLLED_BACK_FMT = "적용 중 실패해 이전 파일로 되돌렸습니다 ({error})"
UPDATE_ERR_ROLLBACK_ITEM_FMT = "- {dst}  (백업: {aside}) — {error}"
UPDATE_ERR_ROLLBACK_ITEM_MISSING = "원본이 제자리에 없습니다"
UPDATE_ERR_ROLLBACK_FMT = ("적용 중 실패했고 일부 파일을 되돌리지 못했습니다. 백업(*.old-update)은 지우지 않았습니다.\n"
                           "앱 폴더 {folder} 에서 아래 항목의 백업 이름을 원래 이름으로 되돌린 뒤 다시 실행하세요:\n{items}\n원인: {error}")
UPDATE_ERR_PIP_TIMEOUT_FMT = "패키지 설치가 {sec}초 안에 끝나지 않아 중단했습니다 (인터넷 연결·회사 프록시를 확인하세요)"
UPDATE_ERR_PIP_CANCELLED = "패키지 설치를 취소했습니다"
UPDATE_ERR_PIP_KILL_FMT = "설치 프로세스(pip)를 끝내지 못했습니다 — 작업 관리자에서 python 프로세스를 확인하세요 ({error})"

# ── 첫 실행 부트스트랩(콘솔) ───────────────────────────────────────────
BOOT_DEPS_INSTALLING = "[AOI] 처음 실행입니다. 필요한 패키지를 설치합니다 (몇 분 걸릴 수 있습니다, 창을 닫지 마세요)…"
BOOT_DEPS_FAILED = "[AOI] 패키지 설치에 실패했습니다. 인터넷 연결 또는 회사 프록시를 확인한 뒤 다시 실행하세요."
BOOT_DEPS_DONE = "[AOI] 설치가 끝났습니다. 프로그램을 시작합니다."
BOOT_PRESS_ENTER = "계속하려면 Enter 를 누르세요..."
BOOT_LOG_HINT_FMT = "[AOI] 자세한 내용은 로그 파일을 보세요: {path}"

# ── 보관·HTML 기간·HTML 만 다시 만들기(10/5) ─────────────────────────────────
HTML_ONLY_NO_CACHE = "가진 데이터가 없습니다 — 먼저 수집을 한 번 해 주세요"
HTML_ONLY_REDERIVE = "규칙이 바뀌어 다시 분류 중 — 다음 수집 뒤엔 빨라집니다"      # PH-05: 업데이트 뒤 첫 'HTML 만 만들기'는 캐시 전체를 메모리에서 다시 분류한다
SET_HTML_DAYS = "결과 파일 기본 기간"
SET_HTML_DAYS_SUFFIX = " 일"
SET_HTML_DAYS_ALL = "전부"
SET_HTML_DAYS_HELP = "수집이 끝나면 만드는 AOI_capacity.html 에 최근 며칠을 담을지(0 = 가진 데이터 전부). 파일은 나누지 않습니다. 다른 기간은 아래 '결과 파일만 다시 만들기' 로."
HTML_ONLY_TITLE = "결과 파일만 다시 만들기"   # 수집 창 구역 이름(COLLECT_SEC_HTML) · 실패 안내(ACT_HTML_ONLY)와 같은 이름(COPY-11)
HTML_ONLY_WHEN = "NAS 를 읽지 않고 가진 데이터로 결과 파일만 다시 만듭니다"
HTML_ONLY_HAVE_FMT = "가진 데이터: {first} ~ {last} · {rows:,}행"
HTML_ONLY_NONE = "가진 데이터가 없습니다 — 먼저 수집하세요"
BACKFILL_FROM = "시작일"
HTML_ONLY_RUN = "이 기간으로 만들기"
HTML_ONLY_ALL = "전체 기간으로 만들기"
HTML_ONLY_ALL_HELP = "수집 뒤 결과 파일은 최근 1달(설정)만 담습니다 — 가진 데이터 전부를 한 장으로 보려면 이 버튼(파일이 커지고 열 때 느릴 수 있습니다)"
HTML_ONLY_DONE_FMT = "결과 파일을 만들었습니다: {path}"
HTML_ONLY_RUNNING = "만드는 중…"
HTML_ONLY_DONE_SHORT_FMT = "만들고 열었습니다 · {name}"
HTML_ONLY_FAIL_FMT = "결과 파일을 만들지 못했습니다: {error}"

# 파라미터 빈 구간 채우기(10/11) — 캐시에 Report 는 있는데 파라미터 값이 없는 곳을 NAS 의 Wafer 폴더에서 바로 채운다
PARAMS_FILL_PHASE_FMT = "파라미터 읽는 중 · {device}"

# 옛 기간 빈칸 채우기(10/24) — 수집기가 나중에 모으기 시작한 값(스캔 비율 · 파라미터 · RDL 판정)이 옛 Report 에 빈 곳을 한 번에 채운다
GAPS_TITLE = "옛 기간 빈칸 채우기"
GAPS_TIP = ("수집기 업데이트 전에 모은 Report 에는 나중에 생긴 값이 비어 있습니다. Report 를 다시 읽지 않고, 그 Wafer 폴더 안 파일만 "
            "정확한 경로로 읽어 채웁니다(NAS 읽기 전용 · 수집 범위 밖 장비 접근 없음). 나중 검사로 폴더가 다시 쓰였으면 값을 지어내지 않고 빈 채로 둡니다. "
            "멈춰도 읽은 것은 저장되고, 다시 누르면 남은 것부터 합니다. 끝나면 결과 파일을 다시 만듭니다.")
GAPS_ROW_SLOT = "슬롯 번호"
GAPS_ROW_SLOT_TIP = "결과 화면 '스캔을 어디에 했니?' 탭의 Slot No · Wafer ID 지도 — Wafer 폴더의 WaferInfo.ini 한 장만 읽어 ActiveSlot 을 채웁니다"
GAPS_ROW_SEC = "스캔 비율"
GAPS_ROW_SEC_TIP = "장비 팝업의 '그중 스캔 n%' — Wafer 폴더의 ScanLog.ini 로 잰 실제 촬영 시간"
GAPS_ROW_PARAMS = "파라미터"
GAPS_ROW_PARAMS_TIP = "파라미터 탭 — LOT 마다 첫 Wafer 의 레시피 값"
GAPS_ROW_RDL = "RDL 멀티/단일"
GAPS_ROW_RDL_TIP = "RDL 단일스캔 탭 — '-미구분' 으로 보이는 RDL LOT 의 멀티/단일 판정"
GAPS_ROW_KLA = "KLA 이미지 개수"
GAPS_ROW_KLA_TIP = "KLA 장의 Defect 를 이미지 개수(결과 파일 IMAGECOUNT 합)로 — 결과 파일 한 장씩만 다시 읽습니다"
GAPS_PHASE_KLA_FMT = "KLA 이미지 개수 읽는 중 · {device}"
GAPS_MISSING_WAFER_FMT = "{n:,}장 비어 있음"
GAPS_MISSING_REPORT_FMT = "{n:,}개 비어 있음"
GAPS_FULL = "모두 채워짐"
GAPS_FILLED_PCT_FMT = "{p}% 채움"
GAPS_SPAN_FMT = "{a} ~ {b}"
GAPS_ETA_FMT = "{t}"
GAPS_RUN = "빈칸 채우기"
GAPS_PHASE_SLOT_FMT = "슬롯 번호 읽는 중 · {device}"
GAPS_PHASE_SEC_FMT = "스캔 비율 읽는 중 · {device}"
GAPS_RUNNING = "채우는 중…"
GAPS_PROGRESS_FMT = "{phase} · {done:,} / {total:,}"
GAPS_LEFT_FMT = " · 남은 {t}"
GAPS_DONE_FMT = "채웠습니다 — 슬롯 번호 {slot:,}장 · 스캔 비율 {sec:,}장 · 파라미터 {params:,}개 · RDL {rdl:,}개 · KLA 이미지 개수 {kla:,}장 · 결과 파일을 새로 만들었습니다"
GAPS_STOPPED = "멈췄습니다 — 읽은 것은 저장했고, 다시 누르면 이어서 합니다"
GAPS_FAIL_FMT = "빈칸을 채우지 못했습니다: {error}"
GAPS_AUTO_PHASE_FMT = "옛 빈칸 채우는 중(최대 {sec}초)"
GAPS_AUTO_NOTE_FMT = "평소 수집 때 최근 것부터 {sec}초씩 저절로 채워집니다 — 한꺼번에 채우려면 '빈칸 채우기'"
GAPS_AUTO_OFF = "평소 수집 때 저절로 채우기는 꺼져 있습니다(설정 gap_fill_sec = 0)"

# 예상 시간(10/11) — 지난 실행의 실측으로 센다. 실측이 없으면 '대략'
ETA_UNDER_MIN = "1분 안쪽"
ETA_MIN_FMT = "약 {m}분"
ETA_HOUR_FMT = "약 {h}시간 {m}분"
ETA_ROUGH_FMT = "{t}"                       # 11/25: '대략 약' 겹침을 없앴다 — 대략인 것은 툴팁(ETA_ROUGH_TIP)으로만
MODE_BADGE_ETA_FMT = "{t}"
MODE_BADGE_USUAL_ETA_FMT = "보통 {t}"
MODE_BADGE_TARGET_ETA_FMT = "대상 {n}개 · {t}"
ETA_BASIS_TIP = "이 PC 에서 지난 실행에 걸린 시간으로 계산한 값입니다."
ETA_ROUGH_TIP = "아직 이 PC 의 실행 기록이 없어 대략 센 값입니다."
CLI_HELP_HTML_ONLY = "수집하지 않고 가진 데이터(캐시)만으로 결과 HTML 을 다시 만든다(NAS 를 읽지 않음)"
CLI_HELP_FROM = "결과 HTML 에 담을 첫날 YYYY-MM-DD(--html-only 와 함께, 비우면 처음부터)"
CLI_HELP_TO = "결과 HTML 에 담을 끝날 YYYY-MM-DD(--html-only 와 함께, 비우면 끝까지)"
CLI_HTML_ONLY_BAD_DATE_FMT = "날짜 형식이 틀립니다(YYYY-MM-DD): {value}"
CLI_CONFIG_NOT_FOUND_FMT = "설정 파일을 찾을 수 없습니다: {path}"
PREFS_BROKEN_FMT = "설정 파일을 읽지 못해 기본값으로 시작했습니다 — 원본: {path}"
CLI_CONFIG_BAD_JSON_FMT = "설정 파일(JSON)이 깨졌습니다: {path} — {line}번째 줄 {col}번째 칸: {error}"
CLI_CONFIG_UNREADABLE_FMT = "설정 파일을 읽지 못했습니다: {path} ({error})"
HTML_RANGE_REVERSED_FMT = "시작({day_from})이 끝({day_to})보다 늦습니다"
HTML_RANGE_EMPTY_FMT = "고른 기간({day_from} ~ {day_to})에 데이터가 없습니다 — 가진 데이터: {first} ~ {last}"
RETENTION_FOREVER_TEXT = "기한 없음 — 전부"
RETENTION_DAYS_FMT = "{days}일"
COLLECT_PHASE_KLA = "KLA 결과 파일 읽는 중"

# ── Wafer 폴더 로그 모으기(10/9) ─────────────────────────────────────────────
WAFER_LOGS_TITLE = "Wafer 로그 30일 전체 수집"
WAFER_LOGS_OUT = "저장 위치"
WAFER_LOGS_STOPPING = "멈추는 중 — 지금 읽던 것만 끝내고 마무리합니다"
WAFER_LOGS_BUSY = "가동률 수집 중에는 로그를 모을 수 없습니다(NAS 를 함께 읽지 않게)"

FAIL_LOGS_SHORT = "수집 실패 원인 · 로그를 zip 한 장으로"

SET_PUBLISH_DIR = "AOI LOT 배포 폴더"
SET_PUBLISH_PLACEHOLDER = "비우면 배포 안 함"
SET_PUBLISH_HELP = ("팀 공유 폴더 경로를 적으면 수집이 끝날 때마다 AOI LOT('스캔을 어디에 했니?' 화면만 담은 HTML)을 조용히 올립니다(실패해도 수집은 성공, 로그에만 남음). "
                    "폴더 안에 바로가기용 AOI_LOT.html · latest.js · data 폴더(최근 3개)가 생깁니다. 장비 NAS 아래 경로는 거부합니다.")
PUBLISH_DIR_DEFAULT = "\\\\k5cifsn2\\k5tsvdata$\\Eng'r\\HT Lim\\LOT 추적"   # 11/4 사용자 확정(HT Lim 아래 LOT 추적 · 전체를 따로) — 팀 공유 폴더(장비 NAS 와 다른 공유)
PUBLISH_FULL_DIR_DEFAULT = "\\\\k5cifsn2\\k5tsvdata$\\Eng'r\\HT Lim\\전체"   # 11/4 — 모든 탭을 담은 배포판(LOT 추적 폴더 안의 하위 폴더)
PUBLISH_DIR_PAST3 = "\\\\k5cifsn2\\k5tsvdata$\\Eng'r\\HT Lim"   # 11/4 오전 기본값(HT Lim 바로 아래) — prefs v13 이 이 값 그대로인 설정만 `LOT 추적` 하위 폴더로 옮긴다
PUBLISH_DIR_PAST2 = "\\\\k5cifsn2\\k5tsvdata$\\1. Conder Scan\\0. 전산 X\\임현택\\LOT추적"   # 10/30~11/3 기본값 — prefs v12 가 이 값 그대로인 설정만 HT Lim 으로 옮긴다
PUBLISH_FULL_DIR_PAST2 = "\\\\k5cifsn2\\k5tsvdata$\\1. Conder Scan\\0. 전산 X\\임현택\\전체"
PUBLISH_DIR_PAST = "\\\\10.142.80.167\\1.Engr\\0. 전산 X\\임현택 ENG'R\\LOT추적"   # 10/30 한나절 기본값(IP 공유) — prefs v11 이 이 값 그대로인 설정만 Conder Scan 으로 되돌린다
PUBLISH_FULL_DIR_PAST = "\\\\10.142.80.167\\1.Engr\\0. 전산 X\\임현택 ENG'R\\전체"
SET_PUBLISH_FULL_DIR = "전체 배포 폴더"
SET_PUBLISH_FULL_HELP = ("팀 공유 폴더 경로를 적으면 수집이 끝날 때마다 모든 탭(최근 90일)을 담은 HTML 을 AOI LOT 배포 뒤에 조용히 올립니다(실패해도 수집은 성공, 로그에만 남음). "
                         "폴더 안에 바로가기용 AOI_ALL.html · latest.js · data 폴더(최근 3개)가 생깁니다. AOI LOT 배포 폴더와 달라야 하고 장비 NAS 아래 경로는 거부합니다.")
PUBLISH_FULL_SAME_DIR = "전체 배포 폴더가 AOI LOT 배포 폴더와 같아 올리지 않았습니다(서로 다른 폴더를 적어 주세요)"
PUBLISH_FULL_STUB_TITLE = "AOI Capacity 전체"
PUBLISH_FULL_STUB_LOADING = "AOI Capacity 전체 화면을 여는 중…"
PUBLISH_FULL_STUB_FALLBACK = "자동으로 열리지 않으면 data 폴더에서 가장 최근 all_ 로 시작하는 파일을 여세요."
COLLECT_DONE_TOAST_PUBLISHED_FULL = " · 전체 배포됨"
COLLECT_DONE_PUBLISH_FULL_FAILED_FMT = ("전체 배포는 올리지 못했습니다(수집 결과는 정상 저장됨): {path}\n{error}\n"
                                        "공유 폴더 연결 · 경로를 확인하고 알림의 '다시 올리기' 를 누르세요.")
COLLECT_DONE_PUBLISH_FULL_LOCKED_FMT = ("전체 배포 파일은 올렸지만 안내 파일이 열려 있어 최신으로 바꾸지 못했습니다: {path}\n"
                                        "다음 수집 때 다시 가리킵니다.")
PUBLISH_STUB_TITLE = "스캔을 어디에 했니?"
PUBLISH_STUB_LOADING = "AOI LOT 을 여는 중…"
PUBLISH_STUB_FALLBACK = "자동으로 열리지 않으면 data 폴더에서 가장 최근 lot_ 로 시작하는 파일을 여세요."
PUBLISH_NOT_ABS_FMT = "배포 폴더는 전체 경로로 적어 주세요: {path}"
PUBLISH_SHORTCUT_LOCKED = "바로가기 파일이 열려 있어 바꾸지 못했습니다"
PUBLISH_DIR_MISSING = "배포 폴더에 닿지 못했습니다(공유 연결 · 경로 확인)"
PUBLISH_NO_DIR = "배포 폴더를 적어 주세요"


# ── 배포 지금 올리기(11/25 — 설정의 배포 폴더 줄마다. 옛 '발행 시험' 카드는 없앴다) ─────────────
SET_PUBLISH_NOW = "지금 올리기"
SET_PUBLISH_SHORTCUT = "바탕화면에 바로가기"
SET_PUBLISH_RUNNING = "올리는 중… 1~2분 걸릴 수 있습니다"
SET_PUBLISH_DONE_FMT = "{when} 올림 · {size} · {sec}초"
SET_PUBLISH_AUTO_FMT = "{when} 수집 끝에 올림"
SET_PUBLISH_DONE_LOCKED_FMT = "{when} 올림 · 안내 파일이 열려 있어 최신으로 못 바꿈(다음에 다시 가리킴)"
SET_PUBLISH_FAIL_FMT = "{when} 못 올림 · {why}"
SET_PUBLISH_SHORTCUT_DONE_FMT = "바탕화면에 바로가기를 만들었습니다: {path}"
SET_PUBLISH_OFF = "비어 있어 올리지 않습니다"
SET_PUBLISH_BUSY = "수집 · 다른 올리기가 끝난 뒤에 누르세요"
# 배포 실패 이유(PP-04) — 예외 원문은 로그에만
PUBLISH_WHY_UNREACHABLE = "공유 폴더에 닿지 못했습니다(네트워크 · VPN 연결과 경로를 확인하세요)"
PUBLISH_WHY_DENIED = "공유 폴더에 쓸 권한이 없습니다"
PUBLISH_WHY_LOCKED = "누가 파일을 열고 있어 바꾸지 못했습니다"
PUBLISH_WHY_OTHER = "올리는 중 오류가 났습니다(로그에 자세히)"
PUBLISH_SKIPPED_SAME_HOST = "AOI LOT 배포가 같은 서버에 닿지 못해 전체 배포는 건너뛰었습니다"

# ── 수집 결과 알림(11/25 — 문제마다 한 항목: 굵은 머리 + 흐린 설명 + 그 문제에 맞는 단추) ─────────
OUTCOME_CSV_HEAD = "CSV 를 저장하지 못함"
OUTCOME_CSV_DESC = "Excel 등에서 열려 있으면 닫으세요 — 다음 수집 때 다시 씁니다. 결과 화면(HTML)은 정상 저장됐습니다."
OUTCOME_CACHE_HEAD = "캐시 파일을 읽을 수 없어 처음부터 다시 수집함"
OUTCOME_CACHE_DESC_FMT = "손상된 원본은 지우지 않고 보존했습니다: {path}"
OUTCOME_UNREACHABLE_HEAD_FMT = "접근 못 한 장비 {n}대 · {names}"
OUTCOME_PARTIAL_HEAD_FMT = "일부 Report 를 못 읽음 {n}대 · {names}"
OUTCOME_PARTIAL_DESC_FMT = "Report {reports}개 — 수집 끝에 한 번 더 읽어도 안 됐습니다. 다음 수집 때 다시 읽습니다."
OUTCOME_PUBLISH_HEAD_FMT = "배포를 올리지 못함 · {what}"
OUTCOME_PUBLISH_LOCKED_HEAD_FMT = "배포는 올렸지만 안내 파일을 못 바꿈 · {what}"
OUTCOME_PUBLISH_LOCKED_DESC = "누가 안내 파일을 열고 있었습니다 — 다음 수집 때 다시 가리킵니다."
OUTCOME_WHAT_JOIN = " · "
OUTCOME_REPUBLISH = "다시 올리기"
OUTCOME_REPUBLISHING = "다시 올리는 중…"
OUTCOME_REPUBLISH_DONE = "다시 올렸습니다"

# ── 수집 실패 안내(CORE-10 · QT-15) — 쉬운 문장 + 해결 한 줄, 원문은 '자세히' · app.log ─────────
FAIL_HTML_BODY = ("Report 를 읽고 저장하는 데까지는 끝났지만 결과 파일(HTML)을 쓰지 못했습니다. "
                  "결과 파일이 다른 프로그램에서 열려 있거나 결과 폴더에 쓸 수 없었습니다.\n\n"
                  "읽은 데이터는 저장됐습니다 — '결과 파일만 다시 만들기' 로 다시 만들면 됩니다(NAS 는 다시 읽지 않습니다).")
FAIL_CONFIG_BODY = "설정 · 장비 목록에 문제가 있어 수집을 시작하지 않았습니다. 장비 목록의 이름 · 경로를 확인하세요."
FAIL_NAS_BODY = "결과 · 캐시를 저장할 폴더가 장비 NAS 아래라 아무것도 쓰지 않았습니다. 설정의 결과 폴더를 이 PC 의 폴더로 바꾸세요."
FAIL_REBUILD_BODY = "전체 다시 만들기 결과가 검증을 통과하지 못해 기존 결과를 그대로 두었습니다. 로그에 이유가 있습니다."
FAIL_IO_BODY = "파일을 읽거나 쓰지 못해 수집을 멈췄습니다. 네트워크 연결 · 권한 · 디스크 공간을 확인한 뒤 다시 수집하세요. 이미 저장한 것은 다시 읽지 않습니다."
FAIL_OTHER_BODY = "예상하지 못한 오류로 수집을 멈췄습니다. 이미 저장한 것은 그대로 있습니다 — 다시 수집해 보고, 되풀이되면 '실패 로그 수집' 으로 자료를 보내 주세요."
ACT_HTML_ONLY = "결과 파일만 다시 만들기"
ACT_DEVICES = "장비 목록 열기"
ACT_LOG = "로그 보기"
SHEET_DETAIL_SHOW = "자세히 ▸"
SHEET_DETAIL_HIDE = "자세히 ▾"
UNHANDLED_TITLE = "처리 중 오류"
UNHANDLED_BODY = "예상하지 못한 오류로 방금 하던 일을 마치지 못했습니다. 창은 그대로 쓸 수 있습니다 — 자세한 내용은 로그에 남겼습니다."

# ── 실패 로그 수집(10/20) ───────────────────────────────────────────────────
# 속도 시험(11/25 — PH-01 · PH-03 · LOTD-01, 현택 "테스트는 수집기에 테스트 버튼 만들어줘"). 결과 파일(요약.txt)의 글은 perf_test.py 에
PERF_TITLE = "속도 시험"
PERF_SHORT = "단추 하나로 끝까지 · 도중에 브라우저 탭이 두 번 열립니다 · 다 끝나면 닫아도 됩니다"
PERF_WHEN = ("가진 데이터(캐시)만으로 결과 파일 세 장(기본 · AOI LOT 배포 · 전체 배포)을 예전 방식과 지금 방식으로 만들어 걸린 시간과 "
             "두 방식의 결과가 바이트까지 같은지 재고, 이어서 AOI LOT 배포판 시험 파일 두 장을 기본 브라우저로 차례로 엽니다. "
             "시험 파일은 스스로 LOT 화면을 눌러 본 뒤 결과를 다운로드 폴더에 한 장 내려받고, 수집기가 그것을 가져와 요약에 적습니다. "
             "장비 NAS 는 읽지 않고 공유 폴더에도 올리지 않습니다. 끝나면 결과 폴더가 열립니다 — 요약.txt 하나만 보내 주세요. 데이터가 많으면 몇 분 걸립니다.")
PERF_RUN = "속도 시험 시작"
PERF_STOP = "멈춤"
PERF_OPEN = "결과 폴더 열기"
PERF_RUNNING = "재는 중… 도중에 브라우저 탭이 두 번 열립니다 — 그대로 두세요"
PERF_STOPPING = "멈추는 중…"
PERF_DONE_FMT = "끝났습니다 — {path}"
PERF_SEND = "이 폴더의 요약.txt 하나만 보내 주세요."
PERF_LOT_FMT = "LOT 배포판 열기 — 지금 {now} · 계산 건너뜀 {skip}"
PERF_LOT_SEC_FMT = "{sec:.1f}초"
PERF_LOT_NONE = "못 받음"
PERF_LOT_MISSING_FMT = "LOT 시험 결과를 받지 못했습니다 — 결과 폴더의 {files} 를 열어 브라우저 맨 위 노란 띠 숫자도 함께 보내 주세요."
PERF_STOPPED_FMT = "멈췄습니다 — 거기까지의 결과: {path}"
PERF_FAIL_FMT = "속도 시험을 하지 못했습니다: {error}"
PERF_BUSY = "수집 · 빈칸 채우기 · 배포 · 실패 로그 수집이 끝난 뒤에 시작하세요."
PERF_PHASE_FMT = "속도 시험 {i}/{n} · {what}"
PERF_WHAT_LOAD = "가진 데이터 읽는 중"
PERF_WHAT_A_FMT = "예전 방식 — {what}"
PERF_WHAT_B_FMT = "지금 방식 — {what}"
PERF_WHAT_LOT_FMT = "AOI LOT 시험 파일 {name}"
PERF_WHAT_OPEN_FMT = "브라우저로 {name} 여는 중 — 결과를 기다립니다(최대 {sec}초)"
PERF_WHAT_WRITE = "요약 쓰는 중"
COLLECT_BUSY_PERF = "속도 시험 중이라 잠시 수집할 수 없습니다"
FAIL_LOGS_TITLE = "실패 로그 수집"
FAIL_LOGS_WHEN = ("수집이 안 된 장비 · 읽지 못한 Report · Wafer · 데이터가 멈춘 장비 · INI 읽기 오류를 모아 zip 한 장으로 만듭니다. "
                  "이 PC 의 app.log 와 캐시를 먼저 보고, 실패한 파일만 NAS 에서 **읽기 전용**으로 가져옵니다(쓰기 · 이동 없음, 수집 범위 밖 장비는 보지 않습니다). "
                  "zip 에는 원인 · 오류 문구 · 파일명 · 경로 · 파일 내용 · app.log 발췌 · 장비별 상태가 들어갑니다. 파일 내용에 LOT · Job 이름이 있으니 공유 범위는 직접 판단하세요.")
FAIL_LOGS_DAYS_PREFIX = "지난"
FAIL_LOGS_DAYS_SUFFIX = "일"
FAIL_LOGS_RUN = "실패 로그 수집"
FAIL_LOGS_OPEN = "저장 폴더 열기"
FAIL_LOGS_RUNNING = "모으는 중…"
FAIL_LOGS_DONE_FMT = "끝났습니다 — 실패 항목 {n}개 · {path}"
FAIL_LOGS_NONE_FMT = "끝났습니다 — 지난 {days}일 안에 찾은 실패가 없습니다 · {path}"
FAIL_LOGS_FAIL_FMT = "실패 로그를 모으지 못했습니다: {error}"

KLA_LOCK_HINT_FMT = "폴더 생성 {age} 전 — 스캔이 멈춰 파일이 잠겼거나 읽기 권한이 없는 것으로 보임(다음 수집에서 다시 읽음)"
KLA_LOCK_HINT_NOAGE = "스캔이 멈춰 파일이 잠겼거나 읽기 권한이 없는 것으로 보임(다음 수집에서 다시 읽음)"
KLA_LOCK_HINT_REPEAT_FMT = " · 수집 {n}번 연달아 같은 파일 — 다시 읽어도 안 풀리는 고정 오류일 가능성(그 Wafer 한 장은 KLA 데이터에서 빠짐)"
