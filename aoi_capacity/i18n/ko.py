"""사용자에게 보이는 한국어 문구 — 이 파일에만 둔다.

규칙
- 이름은 `기능_역할` (BTN_, NAV_, COLLECT_, UPDATE_, NAS_ …). `_FMT` 로 끝나면 `str.format` 자리표시자가 있다.
- 로그 메시지는 여기 두지 않는다(로거 인자에 그대로 쓴다).
- 순수 상수 모듈: 표준 라이브러리 외 import 금지(첫 실행 부트스트랩 전에도 로드된다).
"""

# ── 앱 ──────────────────────────────────────────────────────────────────
APP_TITLE = "AOI Capacity"
APP_SUBTITLE = "AOI 장비 가동률"
CREDIT = "정확 경로만 확인 · 재귀 검색 없음 · NAS 원본은 읽기만"

# ── 내비게이션 ─────────────────────────────────────────────────────────
NAV_DEVICES = "장비 목록"
NAV_DEVICES_SUB = "NAS 경로 · 폴더"
NAV_COLLECT = "수집"
NAV_COLLECT_SUB = "지금 수집 · 결과 열기"
NAV_SETTINGS = "설정 · 정보"
NAV_SETTINGS_SUB = "주의 기준 · 업데이트"
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
BTN_OPEN_BROWSER = "브라우저로 열기"
BTN_OPEN_RESULT = "결과 화면 열기"
BTN_OPEN_RESULT_FOLDER = "폴더 열기"
BTN_CHECK_UPDATE = "업데이트 확인"
BTN_LOAD_DEFAULT_DEVICES = "예시 목록 불러오기"

# ── 대시보드 ───────────────────────────────────────────────────────────

# ── 장비 목록 ──────────────────────────────────────────────────────────
DEV_PAGE_TITLE = "장비 목록"
DEV_PAGE_HELP = ("한 줄이 장비 하나입니다. NAS경로는 드라이브 문자(X:\\)나 주소(\\\\10.142.80.90\\공유) 어느 쪽이든 되고, "
                 "폴더는 NAS경로 아래 장비 폴더 이름입니다. 폴더를 비우면 NAS경로 자체가 장비 폴더이고, "
                 "* 이면 그 안의 장비 폴더(Report 폴더가 있는 폴더)를 모두 자동 등록합니다. "
                 "이 목록은 이 PC 에만 저장되며 NAS 에는 아무것도 쓰지 않습니다.")
DEV_COL_NAME = "장비명"
DEV_COL_ROOT = "NAS경로"
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
DEV_REVERTED_TOAST = "저장된 목록으로 되돌렸습니다"
DEV_IMPORTED_FMT = "{n}행을 가져왔습니다"
DEV_UNSAVED_TITLE = "저장하지 않은 변경"
DEV_UNSAVED_BODY = "장비 목록에 저장하지 않은 변경이 있습니다. 저장할까요?"
DEV_BROWSE_TITLE = "장비 폴더 또는 NAS 공유 선택"
DEV_CSV_FILTER = "CSV 파일 (*.csv)"
DEV_EMPTY_HINT = "장비가 없습니다. '행 추가' 또는 '예시 목록 불러오기'를 누르세요."

# ── 수집 ───────────────────────────────────────────────────────────────
COLLECT_PAGE_TITLE = "수집"
COLLECT_PLAN_FIRST_FMT = "처음 수집: 모든 장비의 최근 {days}일 Report 를 전부 읽습니다. 장비 수에 따라 몇 분 걸릴 수 있습니다."
COLLECT_PLAN_INCR_FMT = "증분 수집: 마지막으로 가져온 이후 새로 생긴 Report 만 읽습니다 (알고 있는 장비 {n}대)."
# ── 수집 모드(D60): 문구는 코드가 실제로 하는 일과 같아야 한다 ────────────────────────────
#   backfill = 검색 창만 넓힌다(캐시된 파일은 건너뛴다) · refresh = 창 안의 캐시된 Report 도 다시 읽는다(창 밖 이력 보존)
#   full/rebuild = 보관 기간 전부를 새 후보 캐시에 모아 검증 뒤 교체(실패하면 기존 캐시 유지, 이력 삭제 없음)
COLLECT_PLAN_BACKFILL_FMT = ("검색 창 넓히기: 최근 {days}일 안에서 아직 캐시에 없는 Report 를 찾아 읽습니다. "
                             "이미 캐시된 Report(수정시각 같음)는 건너뜁니다 — 다시 읽으려면 '최근 N일 다시 읽기' 를 켜세요.")
COLLECT_PLAN_FULL_FMT = ("전체 다시 만들기: 보관 기간 {days}일 안의 Report 를 전부 새 후보 캐시에 모아 검증한 뒤 바꿉니다. "
                         "검증에 실패하면 기존 캐시를 그대로 둡니다(이력이 지워지지 않습니다).")
COLLECT_PLAN_REFRESH_FMT = ("최근 {days}일 다시 읽기: 캐시된 Report {reread}개를 다시 읽고, 창 밖 {keep}개는 그대로 둡니다. "
                            "새 Report 도 함께 읽습니다. 다시 읽다 실패한 Report 는 이전 결과를 유지합니다.")
COLLECT_OPT_BACKFILL = "검색 창 넓히기 (backfill · 캐시된 파일은 건너뜀)"
COLLECT_OPT_FULL = "전체 다시 만들기 (검증 뒤 교체 · 이력 보존)"
COLLECT_OPT_REFRESH_FMT = "최근 {days}일 다시 읽기(이력 보존)"
COLLECT_OPT_RECOVER = "시간 미확인 Report 다시 읽기"
COLLECT_PLAN_RECOVER_FMT = "누락 복구: INI 를 못 찾았던 Report {n}개를 다시 읽습니다. 새 Report 도 함께 읽습니다."
COLLECT_PLAN_RECOVER_NONE = "누락 복구: 다시 읽을 Report 가 없습니다. 새 Report 만 읽습니다."
COLLECT_PLAN_LOADING = "수집 계획 확인 중…"
COLLECT_BACKFILL_DAYS = "처음 수집 기간"
COLLECT_RETENTION_DAYS = "이력 보관 기간"
COLLECT_DAYS_SUFFIX = " 일"
COLLECT_OUTPUT_DIR = "결과 폴더"
COLLECT_OUTPUT_DEFAULT_HINT = "비우면 이 PC 의 데이터 폴더에 저장합니다. NAS 폴더는 지정할 수 없습니다."
COLLECT_WRITE_CSV = "CSV 도 함께 저장"
COLLECT_RESULT_TITLE = "결과 화면"
COLLECT_RESULT_HINT = ("수집이 끝나면 이 HTML 파일 한 장에 모든 데이터가 들어갑니다. "
                       "파일을 더블클릭하면 이 프로그램이 꺼져 있어도 브라우저에서 그대로 열립니다. "
                       "새로 수집한 내용은 열려 있던 화면을 새로고침(F5)하면 보입니다.")
COLLECT_RESULT_NONE = "아직 수집한 적이 없습니다 — '지금 수집' 을 먼저 누르세요."
COLLECT_LOG_TITLE = "로그"
COLLECT_RUNNING = "수집 중…"
COLLECT_IDLE = "대기"
COLLECT_DONE_TOAST_FMT = "수집 완료 · 장비 {devices}대 · {elapsed}"
COLLECT_DONE_WITH_ERRORS_TITLE = "수집은 끝났지만 일부 문제가 있습니다"
COLLECT_DONE_UNREACHABLE_FMT = "접근 못 함 {n}대: {names}"
COLLECT_DONE_PARTIAL_FMT = "일부 Report 실패 {n}대: {names} (Report {reports}개)"
COLLECT_DONE_SEE_LOG = "자세한 내용은 로그를 보세요."
# ── 부분 성공(C06)·캐시 손상(C15) 안내 — 수집은 끝났고 HTML 은 정상이다 ──────────────────────
COLLECT_DONE_CSV_FAILED_FMT = ("CSV 는 저장하지 못했습니다(HTML 결과 화면은 정상 저장됨): {path}\n{error}\n"
                               "Excel 등에서 열려 있으면 닫고 다시 수집하세요. 이전 CSV 는 그대로 남아 있습니다.")
COLLECT_CACHE_CORRUPT_FMT = ("캐시 파일을 읽을 수 없어 처음부터 다시 수집했습니다. 손상된 원본은 지우지 않고 보존했습니다: {path}")
COLLECT_CANCELLED_TOAST = "수집을 중지했습니다. 이전 결과가 그대로 남아 있습니다."
COLLECT_FAILED_TITLE = "수집 실패"
COLLECT_FAILED_FMT = "수집 중 오류가 났습니다.\n\n{detail}"
COLLECT_NO_DEVICES_TITLE = "장비가 없습니다"
COLLECT_NO_DEVICES_BODY = "'장비 목록' 에서 장비를 먼저 등록하세요."
COLLECT_BUSY_TITLE = "수집이 진행 중입니다"
COLLECT_BUSY_BODY = "수집이 끝난 뒤 다시 시도하세요."
COLLECT_OUTPUT_ON_NAS_TITLE = "결과 폴더로 쓸 수 없는 위치"
COLLECT_OUTPUT_ON_NAS_BODY = "NAS 원본 폴더 안에는 결과를 저장할 수 없습니다. 이 PC 의 폴더를 고르세요."

# 수집 단계 문구 — collect.progress(done, total, phase) 의 phase 로 전달되어 로딩창에 그대로 표시된다.
COLLECT_PHASE_DEVICES = "장비 목록 확인"
COLLECT_PHASE_LIST_FMT = "{device} · 새 Report 찾는 중 ({i}/{n}대)"
COLLECT_PHASE_PARSE_FMT = "{device} · {name}"
COLLECT_PHASE_RETENTION = "오래된 이력 정리"
COLLECT_PHASE_WRITE = "화면 만드는 중"
COLLECT_PHASE_DONE = "완료"

# 로딩창
LOADING_COLLECT_TITLE = "데이터 수집"
LOADING_ELAPSED_FMT = "경과 {elapsed}"
LOADING_COUNT_FMT = "{done} / {total}"
LOADING_DEVICES_FMT = "장비 {done}/{total}"
LOADING_STOPPING = "중지하는 중…"
LOADING_LEGEND_WAIT = "대기"
LOADING_LEGEND_READ = "읽는 중"
LOADING_LEGEND_DONE = "완료"
LOADING_LEGEND_ERR = "접근 불가"
LOADING_LEGEND_PARTIAL = "일부 실패"

# ── 설정 · 정보 ────────────────────────────────────────────────────────
SET_PAGE_TITLE = "설정 · 정보"
SET_DARK_MODE = "어두운 화면"
SET_THRESHOLDS = "주의 장비 기준"
SET_TH_UTIL = "가동률"
SET_TH_UTIL_SUFFIX = " % 미만"
SET_TH_ERR = "또는 오류"
SET_TH_ERR_SUFFIX = " 건 이상"
SET_COLLECT_RANGE = "수집 기간"
SET_BACKFILL_DAYS = "처음 볼 때 최근"
SET_BACKFILL_SUFFIX = " 일치"
SET_RETENTION_DAYS = "화면에 남기는 기간"
SET_RETENTION_SUFFIX = " 일"
SET_READ_WORKERS = "동시에 읽기"
SET_READ_WORKERS_SUFFIX = " 개씩"
SET_COLLECT_RANGE_HELP = ("처음 보는 장비는 이 기간 안의 Report 를 전부 읽습니다. 그다음부터는 새 Report 만 읽습니다. "
                          "기간을 늘리면 첫 수집이 그만큼 오래 걸립니다.\n"
                          "NAS 읽기는 기다리는 시간이 대부분이라 여러 개를 동시에 읽습니다. NAS 가 되레 느려지면 숫자를 낮추세요(1 = 한 줄로).")
SET_DATA_DIR = "데이터 폴더"
SET_VERSION = "버전"
SET_VERSION_UNKNOWN = "미상 (개발 실행)"
SET_NAS_NOTICE = "이 프로그램은 NAS 의 Report 와 WaferInfo.ini 를 읽기만 하며, NAS 에는 어떤 파일도 만들거나 바꾸지 않습니다."
SET_UTIL_DEFINITION = ("가동률 = (Scan + Rescan 시간) ÷ 24시간. 수집한 날(오늘)만 00:00 부터 모든 장비의 마지막 기록까지로 나눕니다 "
                       "('오늘' 은 수집 시각의 날짜 — 며칠 뒤 열어도 같은 숫자). Test Lot 은 전부 Test 로 분모에만 들어갑니다. "
                       "한 장비의 1분은 한 번만 셉니다 — INI 로 확실한 구간을 먼저 놓고, 배치 시작~종료의 남은 빈 시간을 INI 가 없는 Wafer 들이 나눠 갖습니다(팝업에 '배치 시각으로 추정' 표). "
                       "Error 는 Lot 단위로 세고, Error 를 담은 배치가 끝난 뒤 다음 기록까지의 공백을 '에러 후 대기' 로 봅니다.")

# ── 행 비고(data_issue) — 캐시의 `issue_codes` 를 출력 때 문장으로(C12 · collect.issue_text). 위치 인자 {0},{1} ──────────
ISSUE_JOIN = "; "
ISSUE_TEXTS = {
    "NO_WAFER_ID_ROW": "LoadPort/Slot 행이라 INI 경로를 만들 수 없음",
    "JOB_UNKNOWN": "Job 을 알 수 없어 INI 경로를 만들지 않음",
    "MOVED_ONLY": "Wafer 폴더에 MoveResultFlag 만 있고 WaferInfo.ini 없음 — 이동만 되고 스캔 안 함",
    "INI_NOT_FOUND": "예상 경로에 WaferInfo.ini 없음",
    "INI_NOT_FOUND_BACKUPS": "예상 경로와 백업 폴더 {0}개 어디에도 WaferInfo.ini 없음",
    "INI_READ_ERROR": "{0}",
    "TIME_MISSING_OR_REVERSED": "Wafer 시작/종료 시각 누락 또는 역전",
    "INI_STALE": "이 배치 시각 밖의 INI(다시 검사하며 덮어써짐) — 시간 미사용",
    "LOT_MISMATCH": "Lot 불일치",
    "WAFER_ID_MISMATCH": "Wafer ID 불일치",
    "FOUND_IN_BACKUP": "백업 폴더에서 찾음: {0}",
    "JOB_FOLDER_DIFFERS": "Job 폴더 이름이 Report 와 다름: {0}",
    "BATCH_NO_WAFER": "검사된 Wafer 없음 — 배치 시각으로만 표시 (행 {0}개 중 오류 {1}개)",
    "SLOT_ERROR": "자리표시 행 Error — Report 당 1건 · 영향 Slot {0}개 · 시간 미확인(Batch 범위 추정)",
    "MULTI_LOT": "Lot 여러 개({0})",
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
CLI_REBUILD_REJECTED_FMT = "전체 재구축 거부 — 기존 캐시·HTML 은 그대로입니다: {error}"
CLI_CACHE_CORRUPT_FMT = "캐시 파일이 손상되어 처음부터 다시 수집했습니다. 손상 원본 보존: {path}"
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
CFG_ERROR_TITLE = "설정 오류"
CLI_CFG_WARNING_FMT = "설정 경고: {message}"
CLI_CFG_FATAL_FMT = "설정 오류 — 수집을 시작하지 않습니다: {message}"
CFG_ERROR_BODY_FMT = "설정을 고친 뒤 다시 실행하세요.\n\n{items}"

# ── NAS 안전장치 ───────────────────────────────────────────────────────
NAS_WRITE_REFUSED_FMT = "NAS 원본 폴더 안에는 파일을 쓸 수 없습니다: {path}  (NAS: {root})"

# ── 자동 업데이트 ──────────────────────────────────────────────────────
UPDATE_CHECK_TITLE = "업데이트 확인"
UPDATE_CHECKING = "업데이트를 확인하는 중…"
UPDATE_AVAILABLE_TITLE = "새 버전이 있습니다"
UPDATE_AVAILABLE_BODY_FMT = "새 버전이 있습니다 ({sha}{message}). 지금 받을까요?\n\n받은 뒤 프로그램을 다시 실행하면 적용됩니다."
UPDATE_UNKNOWN_CURRENT_FMT = "현재 버전을 알 수 없어 최신 버전({sha})을 받습니다. 지금 받을까요?"
UPDATE_LATEST = "이미 최신 버전입니다."
UPDATE_UNKNOWN = "업데이트를 확인할 수 없습니다 (네트워크 또는 GitHub 접근 문제)."
UPDATE_GIT_HINT = "개발용 git 폴더에서 실행 중이라 자동 업데이트를 적용하지 않습니다. git pull 을 사용하세요."
UPDATE_DOWNLOADING = "새 버전을 받는 중…"
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
CAUSE_PREFIX = "\n\n원인: "
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
