"""설정 값 검사 — GUI(prefs.json)와 CLI(config.json)가 **같은 규칙**으로 cfg 를 정규화한다(C13).

원칙
- 형·범위를 검사한다. `bool("false")` 같은 변환은 하지 않는다(문자열 "false" 는 거짓, "abc" 는 오류).
- **범위·경로 설정은 fail closed** — 잘못되면 `Problem(fatal=True)` 로 실행을 막는다(NAS 접근 0).
  (`scope_devices` 가 목록이 아님 · 경로가 문자열이 아님 · 폴더 이름에 구분자/`..` 가 들어 다른 폴더를 가리킬 수 있는 경우)
- **성능·기간 설정은 경고 + 기본값/클램프** — 워커 안에서 ValueError 로 터지거나 조용히 아무것도 안 읽는 일을 막는다.
- 이 모듈은 파일시스템·Qt 를 건드리지 않는 순수 함수다. 문구는 `i18n/ko.py` 의 `CFG_*`.

규칙 표(`RULES`): 키 → (종류, 기본값, 하한, 상한). 종류 int 는 정수(bool 제외 · 정수값 float · 숫자 문자열 허용),
bool 은 참/거짓(bool · 0/1 · "true"/"false"/"yes"/"no"/"on"/"off"/"1"/"0"), str 은 문자열, name 은 폴더/파일 **이름 하나**.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .. import i18n

INT, BOOL, STR, NAME, PATH = "int", "bool", "str", "name", "path"
MAX_DAYS = 3650
MAX_WORKERS = 32

#: 키 → (종류, 기본값, 하한, 상한). 하한·상한은 int 만 쓴다.
RULES: Dict[str, Tuple[str, Any, Optional[int], Optional[int]]] = {
    "backfill_days": (INT, 30, 1, MAX_DAYS),
    "retention_days": (INT, 90, 1, MAX_DAYS),
    "read_workers": (INT, 8, 1, MAX_WORKERS),
    "refresh_window_days": (INT, 0, 0, MAX_DAYS),
    "attention_util": (INT, 40, 0, 100),          # D14: 살펴볼 장비 — 가동률 미만(%)
    "attention_err": (INT, 3, 0, 999),            # D14: 살펴볼 장비 — Error 건수 이상
    "write_csv": (BOOL, False, None, None),
    "rebuild_all": (BOOL, False, None, None),
    "report_dir": (NAME, "Report", None, None),
    "scan_dir": (NAME, "Scanresult", None, None),
    "output_name": (NAME, "AOI_capacity.html", None, None),
    "devices_csv": (PATH, "", None, None),
    "cache_file": (PATH, "", None, None),
    "output_dir": (PATH, "", None, None),
}
_TRUE = {"true", "1", "yes", "y", "on"}
_FALSE = {"false", "0", "no", "n", "off"}
_INT_RE = re.compile(r"^[+-]?\d+$")
_SEP_RE = re.compile(r"[\\/]")

#: 문제 코드
BAD_INT, OUT_OF_RANGE, BAD_BOOL, BAD_STR, RETENTION_LT_BACKFILL = "bad_int", "out_of_range", "bad_bool", "bad_str", "retention_lt_backfill"
BAD_SCOPE, BAD_PATH, BAD_NAME = "bad_scope", "bad_path", "bad_name"


@dataclass(frozen=True)
class Problem:
    key: str
    code: str
    value: Any
    fatal: bool
    fixed: Any = None

    def message(self) -> str:
        """사용자 문구(ko.py). CLI 는 그대로 출력하고 GUI 는 실패 시트에 담는다."""
        K = i18n.KO
        v = _show(self.value)
        if self.code == BAD_INT:
            return K.CFG_BAD_INT_FMT.format(key=self.key, value=v, default=self.fixed)
        if self.code == OUT_OF_RANGE:
            kind, _d, lo, hi = RULES[self.key]
            return K.CFG_OUT_OF_RANGE_FMT.format(key=self.key, value=v, lo=lo, hi=hi, fixed=self.fixed)
        if self.code == BAD_BOOL:
            return K.CFG_BAD_BOOL_FMT.format(key=self.key, value=v, default=K.CFG_TRUE if self.fixed else K.CFG_FALSE)
        if self.code == BAD_STR:
            return K.CFG_BAD_STR_FMT.format(key=self.key, value=v, default=self.fixed)
        if self.code == RETENTION_LT_BACKFILL:
            return K.CFG_RETENTION_LT_BACKFILL_FMT.format(retention=self.value, backfill=self.fixed, fixed=self.fixed)
        if self.code == BAD_SCOPE:
            return K.CFG_FATAL_SCOPE_FMT.format(value=v)
        if self.code == BAD_NAME:
            return K.CFG_FATAL_FOLDER_NAME_FMT.format(key=self.key, value=v)
        return K.CFG_FATAL_PATH_FMT.format(key=self.key, value=v)


class ConfigError(ValueError):
    """실행을 막는 설정 오류 — `problems` 는 fatal 인 것만. `str()` 은 사용자 문장들(줄바꿈)."""

    def __init__(self, problems: List[Problem]):
        self.problems = [p for p in problems if p.fatal]
        super().__init__("\n".join(p.message() for p in self.problems))


def _show(v: Any) -> str:
    s = repr(v)
    return s if len(s) <= 60 else s[:57] + "..."


# ── 낱개 변환 ─────────────────────────────────────────────────────────────
def parse_int(v: Any) -> Optional[int]:
    """정수로 읽을 수 있으면 int, 아니면 None. bool 은 정수가 아니다(True 를 1 로 받지 않는다). NaN·inf·8.5 는 None."""
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if math.isfinite(v) and v == int(v) else None
    if isinstance(v, str) and _INT_RE.match(v.strip()):
        return int(v.strip())
    return None


def parse_bool(v: Any) -> Optional[bool]:
    """참/거짓으로 읽을 수 있으면 bool, 아니면 None. `bool("false")` 는 절대 쓰지 않는다."""
    if isinstance(v, bool):
        return v
    if isinstance(v, int) and v in (0, 1):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    return None


def is_single_name(v: Any) -> bool:
    """폴더/파일 이름 **하나**인가 — 구분자·`.`·`..`·NUL 이 있으면 다른 폴더를 가리킬 수 있어 아니다."""
    if not isinstance(v, str):
        return False
    s = v.strip()
    return bool(s) and not _SEP_RE.search(s) and s not in (".", "..") and "\x00" not in s


def valid_scope(v: Any) -> bool:
    """`scope_devices` 가 쓸 수 있는 꼴인가 — None(없음) · 문자열 하나 · 문자열 목록(빈 목록 포함, 빈 목록은 기본값)."""
    if v is None or isinstance(v, str):
        return True
    if isinstance(v, (list, tuple)):
        return all(isinstance(x, str) for x in v)
    return False


# ── 정규화 ────────────────────────────────────────────────────────────────
def normalize_config(cfg: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[Problem]]:
    """cfg 사본과 문제 목록을 돌려준다. **있는 키만** 검사한다(없는 키는 부르는 쪽 기본값 그대로) — 부분 cfg 도 받는다.

    성능·기간 값은 고쳐서 넣고(경고), 범위·경로 값은 그대로 두고 fatal 로 표시한다(부르는 쪽이 `ConfigError` 로 막는다)."""
    out: Dict[str, Any] = dict(cfg)
    problems: List[Problem] = []
    for key, (kind, default, lo, hi) in RULES.items():
        if key not in out:
            continue
        v = out[key]
        if kind == INT:
            n = parse_int(v)
            if n is None:
                problems.append(Problem(key, BAD_INT, v, False, default))
                out[key] = default
            elif (lo is not None and n < lo) or (hi is not None and n > hi):
                # 하한 아래: 0 이 뜻이 있는 값(대기 일수·문턱)은 0 으로, 0 이 뜻이 없는 값(기간·동시 읽기)은 기본값으로. 상한 위: 상한으로 클램프
                fixed = (lo if lo == 0 else default) if (lo is not None and n < lo) else hi
                problems.append(Problem(key, OUT_OF_RANGE, v, False, fixed))
                out[key] = fixed
            else:
                out[key] = n
        elif kind == BOOL:
            b = parse_bool(v)
            if b is None:
                problems.append(Problem(key, BAD_BOOL, v, False, default))
                out[key] = default
            else:
                out[key] = b
        elif kind == NAME:
            if v is None or v == "":
                out[key] = default                       # 비움 = 기본값(옛 config.json 호환)
            elif not isinstance(v, str):
                problems.append(Problem(key, BAD_STR, v, False, default))
                out[key] = default
            elif not is_single_name(v):
                problems.append(Problem(key, BAD_NAME, v, True))
            else:
                out[key] = v.strip()
        elif kind == PATH:
            if v is None:
                out[key] = ""
            elif not isinstance(v, str) or "\x00" in v:
                problems.append(Problem(key, BAD_PATH, v, True))
            else:
                out[key] = v.strip()
    if "nas_roots" in out:
        roots = out["nas_roots"]
        if roots is None or roots == "":
            out["nas_roots"] = []
        elif isinstance(roots, str):
            out["nas_roots"] = [roots]
        elif not isinstance(roots, (list, tuple)) or not all(isinstance(x, str) for x in roots):
            problems.append(Problem("nas_roots", BAD_PATH, roots, True))
        else:
            out["nas_roots"] = [str(x) for x in roots]
    if "scope_devices" in out:
        sd = out["scope_devices"]
        if not valid_scope(sd):
            problems.append(Problem("scope_devices", BAD_SCOPE, sd, True))
        elif isinstance(sd, str):
            out["scope_devices"] = [sd]
        elif sd is not None:
            out["scope_devices"] = [x.strip() for x in sd if x.strip()]
    if "backfill_days" in out and "retention_days" in out:
        b, r = out["backfill_days"], out["retention_days"]
        if isinstance(b, int) and isinstance(r, int) and r < b:
            problems.append(Problem("retention_days", RETENTION_LT_BACKFILL, r, False, b))
            out["retention_days"] = b                    # 보관이 수집 창보다 짧으면 방금 읽은 것을 바로 지운다 — 창 길이만큼 늘린다
    return out, problems


def fatal(problems: List[Problem]) -> List[Problem]:
    return [p for p in problems if p.fatal]


def check_or_raise(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """정규화한 cfg 를 돌려주되 fatal 문제가 있으면 `ConfigError`. 수집 진입점(`collect.collect`)이 NAS 를 만지기 전에 부른다."""
    out, problems = normalize_config(cfg)
    bad = fatal(problems)
    if bad:
        raise ConfigError(bad)
    return out


def assert_valid(cfg: Mapping[str, Any]) -> None:
    """값을 고치지 않고 fatal 문제만 막는다 — 장비 게이트(`devices.devices_from_rows` 등)가 파일을 만지기 전에 부른다."""
    _out, problems = normalize_config(cfg)
    bad = fatal(problems)
    if bad:
        raise ConfigError(bad)


def dashboard_settings(cfg: Mapping[str, Any]) -> Dict[str, int]:
    """결과 HTML 의 `meta.dashboard_settings`(D14) — 화면의 PROPS 이름 그대로. 잘못된 값은 기본값."""
    out, _ = normalize_config({"attention_util": cfg.get("attention_util", RULES["attention_util"][1]),
                               "attention_err": cfg.get("attention_err", RULES["attention_err"][1])})
    return {"attentionUtil": int(out["attention_util"]), "attentionErr": int(out["attention_err"])}
