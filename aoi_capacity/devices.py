"""장비 목록 — devices.csv 읽기/쓰기, 장비 폴더 판정, 표시명·정렬.

CSV 열: 장비명, NAS경로, 폴더, 사용, 메모  (영문 헤더도 인식, 헤더가 없으면 이 순서로 본다)
- 폴더 비움  → NAS경로 자체가 장비 폴더(안에 Report 폴더)
- 폴더 "*"   → NAS경로 안에서 Report 폴더가 있는 하위 폴더를 모두 자동 등록(재귀 없음, 한 단계)
- 사용 N/0/아니오 → 건너뜀

장비 하나는 네 가지를 분리해 들고 다닌다(이름을 바꿔도 이력이 갈라지지 않게):
    id       정규화한 원본 경로 — 캐시 커서·집계의 안정 키. 절대 표시명이 아니다.
    path     실제 NAS 경로(읽기 전용, 폴더명을 바꾸지 않는다)
    name     표시명 — `AOI-25`, `4F-AOI-01` 로 정리한 이름
    aliases  예전 표시명 후보 — 캐시 커서를 새 키로 옮길 때만 쓴다

★ 수집 허용 범위(`scope.py`) 는 **파일을 만지기 전에** 적용한다. 범위 밖 행은 `os.path.isdir` 조차
  부르지 않고 건너뛴다. 회귀 가드: dev/tests/test_scope_isolation.py

NAS 는 읽기만 한다(`nas_guard.read_bytes/scandir`, `os.path.isdir`). CSV 쓰기는 이 PC 의 데이터 폴더에만.
"""
from __future__ import annotations

import csv
import datetime as dt
import logging
import ntpath
import os
import re
from typing import Callable, Dict, List, Optional

from . import nas_guard, scope

_LOG = logging.getLogger("aoi.devices")

CSV_HEADER = ["장비명", "NAS경로", "폴더", "사용", "메모"]
CSV_ALIASES = {
    "name": ["장비명", "장비", "name", "device"],
    "root": ["nas경로", "nas", "경로", "root", "path"],
    "sub": ["폴더", "장비폴더", "folder", "sub"],
    "on": ["사용", "enabled", "use", "on"],
    "memo": ["메모", "memo", "note"],
}
_OFF_VALUES = ("N", "NO", "0", "FALSE", "X", "아니오", "OFF")
AUTO = "*"

#: 표시명 정리 — "1~7 AOI-1", "I: AOI-1", "AOI_01" 어느 쪽이든 끝의 AOI 번호를 뽑는다.
_AOI_RE = re.compile(r"AOI[\s_-]*0*(\d+)\s*$", re.I)
#: 4층 장비 판정 — 행 이름·메모·공유 이름에 "4층" 또는 "4F" 가 있으면.
_FLOOR4_RE = re.compile(r"(?:^|[^0-9A-Za-z])(?:4\s*층|4F)(?:[^0-9A-Za-z]|$)", re.I)
FLOOR4_PREFIX = "4F-AOI-"
NORMAL_PREFIX = "AOI-"

LogFn = Callable[[str], None]


def _log(log: Optional[LogFn], msg: str) -> None:
    _LOG.info(msg)
    if log:
        log(msg)


# ----------------------------------------------------------------------------- 표시명 · 정렬
def is_floor4(*hints) -> bool:
    return any(_FLOOR4_RE.search(str(h or "")) for h in hints)


def display_name(folder: str, *hints) -> str:
    """폴더명(+ 행 이름·메모 힌트)에서 표시명을 만든다. 폴더명 자체는 바꾸지 않는다.

    `AOI-1` → `AOI-1` · `1~7 AOI-1` → `AOI-1` · 4층의 `AOI-1` → `4F-AOI-01`
    AOI 번호를 못 찾으면 원래 이름을 그대로 쓴다(사용자가 직접 붙인 이름)."""
    raw = str(folder or "").strip()
    m = _AOI_RE.search(raw)
    if not m:
        return raw
    n = int(m.group(1))
    return f"{FLOOR4_PREFIX}{n:02d}" if is_floor4(raw, *hints) else f"{NORMAL_PREFIX}{n}"


def _natural(text: str) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", str(text))]


def sort_key(name: str) -> tuple:
    """홈 기본 순서 — AOI-1 … AOI-25 다음에 4F-AOI-01 … 4F-AOI-05. 사전식(AOI-1, AOI-10, AOI-2)이 아니다."""
    return (1 if str(name).upper().startswith(FLOOR4_PREFIX) else 0, _natural(name))


# ----------------------------------------------------------------------------- CSV
def read_devices_csv(path) -> List[Dict[str, object]]:
    """UTF-8(BOM 유무) 또는 한글 Excel 의 cp949 CSV 를 읽어 [{name, root, sub, on, memo}] 로 돌려준다."""
    raw = nas_guard.read_bytes(path)
    text = None
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("utf-8", "replace")
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    rows = list(csv.reader(lines))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]

    def col(key: str) -> int:
        for a in CSV_ALIASES[key]:
            if a in head:
                return head.index(a)
        return -1

    ix = {k: col(k) for k in CSV_ALIASES}
    if ix["root"] < 0:  # 헤더 없음: 장비명, NAS경로, 폴더, 사용, 메모 순서로 본다
        ix = {"name": 0, "root": 1, "sub": 2, "on": 3, "memo": 4}
        body = rows
    else:
        body = rows[1:]
    out: List[Dict[str, object]] = []
    for r in body:
        def g(k: str) -> str:
            i = ix[k]
            return r[i].strip() if 0 <= i < len(r) else ""

        if not g("root"):
            continue
        out.append({"name": g("name"), "root": g("root"), "sub": g("sub"),
                    "on": g("on").upper() not in _OFF_VALUES, "memo": g("memo")})
    return out


def write_devices_csv(path, rows: List[Dict[str, object]], roots=None) -> None:
    """이 PC 의 데이터 폴더에 저장한다(utf-8-sig, Excel 호환). NAS 아래 경로면 거부."""
    nas_guard.assert_local(path, roots if roots is not None else nas_guard.expand_roots(r.get("root", "") for r in rows))
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for r in rows:
            w.writerow([r.get("name", ""), r.get("root", ""), r.get("sub", ""),
                        "Y" if r.get("on", True) else "N", r.get("memo", "")])
    os.replace(tmp, path)


# ----------------------------------------------------------------------------- 폴더 판정
def _norm_root(root: str) -> str:
    root = str(root).strip()
    return root.rstrip("\\/") + os.sep if re.fullmatch(r"[A-Za-z]:\\?", root) else root


#: 장비마다 폴더 이름이 다르다 — AOI-25 는 `Reports`, 예전 장비는 `Report`. 설정값을 먼저 보고 순서대로 확인한다.
REPORT_DIR_NAMES = ("Report", "Reports")
SCAN_DIR_NAMES = ("Scanresult", "ScanResult", "Scanresults")


def dir_key(name) -> str:
    """폴더 이름·경로의 **Windows 의미** 비교 키 — 대소문자 · `/`↔`\\` · 끝 구분자 차이를 지운다(C05).

    NAS 는 대소문자를 구분하지 않아 `ScanResult` · `Scanresult` · `SCANRESULT` · `Scanresult\\` 는 같은 폴더다.
    `os.path.normcase` 는 Linux 에서 아무것도 하지 않으므로 어느 OS 에서 돌든 `ntpath` 로 판정한다(테스트가 Linux 에서도 같은 결과)."""
    n = str(name or "").strip()
    if not n:
        return ""
    return ntpath.normcase(ntpath.normpath(n))


def same_dir(a, b) -> bool:
    """두 폴더 이름(또는 경로)이 Windows 의미로 같은 곳인가."""
    return dir_key(a) == dir_key(b)


def _candidates(configured: str, defaults) -> List[str]:
    out, seen = [], set()
    for n in [str(configured or "").strip(), *defaults]:
        k = dir_key(n)
        if n and k not in seen:
            seen.add(k)
            out.append(n)
    return out


def find_subdir(path: str, configured: str, defaults) -> str:
    """실제로 있는 하위 폴더 이름을 돌려준다(없으면 빈 문자열). 후보 몇 개만 존재 확인한다 — 탐색이 아니다."""
    for name in _candidates(configured, defaults):
        if os.path.isdir(os.path.join(path, name)):
            return name
    return ""


#: 현장은 **어느 날짜를 기준으로 그 이전 Scanresult 를 통째로 백업 폴더로 옮긴다**(30대 조사: 16대에 백업, Job 폴더 5,078개가 거기 잠겨 있었다).
#: 옮겨진 순간부터 그 Wafer 들의 INI 는 정확 경로에 없어 전부 NOT_FOUND 가 됐다(AOI-4 시각 확인 4%, AOI-7 0건).
#: 폴더 이름은 제각각이라(`Scanresult_Back up_260918` · `Scanresult Backup_260707` · `Scanresult backup260904` · `Scanresult_BAKCUP_260429` ·
#: `Scanresult - BACKTUP 0827` · `Scanresult_0901` · `Scanresult - 5.9.3`) 목록으로는 못 잡고 **`Scanresult` 로 시작하는지**로만 거른다.
_SCAN_PREFIX = "scanresult"
_YYMMDD_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
_MMDD_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")


def backup_cutoff(name: str, year_hint: Optional[int] = None) -> Optional[dt.date]:
    """백업 폴더 이름의 날짜 = **그 이전 것을 담아 둔 경계**. `…_260918` → 2026-09-18, `…_0901` → (해 힌트)-09-01.
    못 읽으면(`Scanresult - 5.9.3`, `…_268020` 같은 있을 수 없는 날짜) None — 후보 맨 뒤로 간다."""
    n = str(name or "")
    m = _YYMMDD_RE.search(n)
    if m:
        try:
            return dt.datetime.strptime(m.group(1), "%y%m%d").date()
        except ValueError:
            pass                                             # 268020 — 날짜가 아니다
    m = _MMDD_RE.search(n)
    if m and year_hint:
        try:
            return dt.datetime.strptime(f"{year_hint}{m.group(1)}", "%Y%m%d").date()
        except ValueError:
            pass
    return None


def scan_dirs_of(path: str, primary: str) -> List[Dict[str, str]]:
    """이 장비 폴더 안의 `Scanresult*` 폴더 전부 — 맨 앞은 지금 쓰는 폴더, 뒤는 백업들(경계 이른 순, 경계를 못 읽은 것은 맨 뒤).

    각 항목은 `{"name": 폴더 이름, "cutoff": "YYYY-MM-DD" 또는 ""}`. 장비 폴더 **하나를 한 번** 나열한다 — 여기 오는 장비는
    이미 수집 범위 안이라 나열해도 규칙(범위 밖 접근 금지·공유 나열 금지)을 어기지 않는다. 나열에 실패하면 primary 만 돌려준다.
    INI 탐색을 재귀로 넓히는 게 아니라 **정확 경로를 확인할 루트를 늘리는 것**이다(CLAUDE.md 규칙 4 그대로)."""
    out = [{"name": primary, "cutoff": ""}]
    try:
        listed = sorted(e.name for e in nas_guard.scandir(path) if e.is_dir() and e.name.lower().startswith(_SCAN_PREFIX))
    except OSError:
        return out
    # ★ C05: 비교는 Windows 의미(`dir_key`)로 — 실제 폴더가 `ScanResult` 이고 설정이 `Scanresult` 면 isdir 은 참이지만 이름이 달라
    #   같은 폴더가 '백업' 으로 한 번 더 잡혀 없는 INI 마다 확인 횟수가 두 배가 됐다. 맨 앞에는 **실제 나열된 철자**를 쓰고,
    #   대소문자·끝 구분자만 다른 항목은 하나로 센다.
    pk = dir_key(primary)
    real = next((n for n in listed if dir_key(n) == pk), None)
    if real is not None:
        out[0]["name"] = real
    names, seen = [], {pk}
    for n in listed:
        k = dir_key(n)
        if k in seen:
            continue
        seen.add(k)
        names.append(n)
    dated, undated = [], []
    for n in names:
        year = None
        if not _YYMMDD_RE.search(n) and _MMDD_RE.search(n):
            try:
                year = dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(path, n))).year
            except OSError:
                year = None
        c = backup_cutoff(n, year)
        (dated if c else undated).append((c, n))
    dated.sort(key=lambda x: (x[0], x[1]))
    out.extend({"name": n, "cutoff": c.isoformat()} for c, n in dated)
    out.extend({"name": n, "cutoff": ""} for _, n in undated)
    return out


def _has_report(path: str, cfg: dict) -> bool:
    return bool(find_subdir(path, cfg.get("report_dir", ""), REPORT_DIR_NAMES))


def _entry(folder: str, path: str, *hints) -> Dict[str, object]:
    """장비 하나 — 표시명/경로/안정 키/예전 이름 후보."""
    return {"name": display_name(folder, *hints), "path": path, "id": device_id(path),
            "aliases": [a for a in (folder, *[str(h) for h in hints if h]) if a]}


def _dirs_of(path: str, cfg: dict) -> Dict[str, object]:
    """장비 폴더 하나의 Report·Scanresult 폴더 이름과 백업 목록 — **읽기만** 한다(isdir 몇 번 + 나열 1번 + getmtime).

    `scan_dir` 은 나열에서 찾은 **실제 철자**로 맞춘다(설정 `Scanresult` · 실제 `ScanResult` 면 `ScanResult`, C05)."""
    report_dir = find_subdir(path, cfg.get("report_dir", ""), REPORT_DIR_NAMES) or str(cfg.get("report_dir") or "Report")
    scan_dir = find_subdir(path, cfg.get("scan_dir", ""), SCAN_DIR_NAMES) or str(cfg.get("scan_dir") or "Scanresult")
    scan_dirs = scan_dirs_of(path, scan_dir)                                  # 백업 폴더까지(맨 앞이 지금 폴더)
    return {"report_dir": report_dir, "scan_dir": str(scan_dirs[0]["name"]), "scan_dirs": scan_dirs}


def with_dirs(dev: Dict[str, object], cfg: dict) -> Dict[str, object]:
    """이 장비에서 실제로 쓰는 Report·Scanresult 폴더 이름을 붙인다(장비마다 다르다)."""
    dev.update(_dirs_of(str(dev["path"]), cfg))
    return dev


def device_id(path) -> str:
    """캐시 커서·집계의 안정 키 — 정규화한 경로. 표시명을 바꿔도 변하지 않는다."""
    return nas_guard.normalize(path)


def _discover_under(root: str, cfg: dict, log: Optional[LogFn] = None, hint: str = "") -> List[Dict[str, object]]:
    """root 자체가 장비 폴더면 그것 하나, 아니면 root 바로 아래의 장비 폴더들(한 단계, 재귀 없음).

    ★ 수집 범위가 제한돼 있으면 **공유를 나열하지 않는다** — 나열은 범위 밖 장비까지 훑는 일이다.
      대신 허용 목록의 이름만 `root/<이름>` 으로 정확히 만들어 존재를 확인한다. 만지는 경로가 전부
      허용 장비라서 규칙을 지키면서도 `폴더 *` 행이 그대로 동작한다.
      (이 길이 없을 때 실장비에서 4층 5대가 3일 내내 한 번도 수집되지 않았다.)"""
    if not os.path.isdir(root):
        return []
    if _has_report(root, cfg):
        folder = os.path.basename(root.rstrip("\\/")) or root
        return [_entry(folder, root, hint)]
    out = []
    if not scope.unrestricted(cfg):
        for name in scope.scope_list(cfg):
            path = os.path.join(root, name)
            if os.path.isdir(path) and _has_report(path, cfg):
                out.append(_entry(name, path, hint))
        return out
    try:
        for e in nas_guard.scandir(root):
            if e.is_dir() and _has_report(e.path, cfg):
                out.append(_entry(e.name, e.path, hint))
    except OSError as ex:
        _log(log, f"[건너뜀] {root}: {ex}")
    return out


def _share_label(path: str) -> str:
    """X:\\AOI-1 → 'X:', \\\\host\\share\\AOI-1 → 'share', /nas/X/AOI-1 → 'X'."""
    parent = os.path.dirname(str(path).rstrip("\\/"))
    stripped = parent.rstrip("\\/")
    return os.path.basename(stripped) or stripped or parent


def _dedupe_sort(devs: List[Dict[str, object]]) -> List[Dict[str, object]]:
    seen, uniq = set(), []  # 같은 폴더가 두 번(명시 행 + * 행) 나오면 먼저 적힌 행이 이긴다
    for d in devs:
        key = os.path.normcase(os.path.normpath(str(d["path"])))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)
    names: Dict[str, int] = {}
    for d in uniq:
        names[str(d["name"])] = names.get(str(d["name"]), 0) + 1
    for d in uniq:  # 공유가 다른 동명 폴더는 부모 폴더(공유·드라이브) 이름을 앞에 붙여 구분
        if names[str(d["name"])] > 1:
            plain = str(d["name"])
            d["name"] = f"{_share_label(str(d['path']))} {plain}"
            d.setdefault("aliases", [])
            d["aliases"] = list(d["aliases"]) + [plain]
    uniq.sort(key=lambda d: sort_key(str(d["name"])))
    return uniq


def _attach_dirs(devs: List[Dict[str, object]], cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, object]]:
    for d in devs:
        with_dirs(d, cfg)
        if d["report_dir"] != (cfg.get("report_dir") or "Report"):
            _log(log, f"[{d['name']}] Report 폴더 이름이 '{d['report_dir']}' 입니다")
        backups = [x for x in (d.get("scan_dirs") or [])[1:] if not same_dir(x["name"], d["scan_dir"])]
        if backups:
            _log(log, f"[{d['name']}] Scanresult 백업 폴더 {len(backups)}개도 조회합니다: "
                      + ", ".join(f"{b['name']}(~{b['cutoff']})" if b["cutoff"] else b["name"] for b in backups))
    return devs


# ----------------------------------------------------------------------------- 장비 목록 풀기
def devices_from_rows(rows: List[Dict[str, object]], cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, object]]:
    """CSV 행을 실제 장비 폴더 목록으로 푼다. 접근할 수 없는 행은 로그에 남기고 건너뛴다.

    ★ 수집 허용 범위 밖 행은 파일시스템을 건드리기 전에 걸러낸다."""
    devs: List[Dict[str, object]] = []
    for row in rows:
        if not row.get("on", True):
            continue
        root = _norm_root(str(row.get("root", "")))
        sub = str(row.get("sub", "")).strip()
        label = str(row.get("name") or sub or root)
        hint = f"{row.get('name', '')} {row.get('memo', '')}"
        if sub in (AUTO, "auto", "AUTO"):
            found = _discover_under(root, cfg, log, hint)      # 제한 중이면 허용 이름만 정확 경로로 확인
            if not found:
                _log(log, f"[건너뜀] {label}: NAS 접근 불가 또는 장비 폴더 없음 ({root})")
            devs.extend(found)
            continue
        if not scope.allows_row(cfg, row):
            _log(log, f"[범위 밖] {label}: 현재 수집 범위({scope.describe(cfg)}) 가 아니라 접근하지 않습니다")
            continue
        path = os.path.join(root, sub) if sub else root
        if not _has_report(path, cfg):
            _log(log, f"[건너뜀] {label}: Report 폴더 없음/접근 불가 ({path})")
            continue
        folder = sub or os.path.basename(path.rstrip("\\/")) or path
        d = _entry(folder, path, hint)
        if row.get("name") and not _AOI_RE.search(str(row["name"])):
            d["name"] = str(row["name"])          # 사용자가 붙인 이름은 그대로 존중한다
        d["aliases"] = [a for a in [folder, str(row.get("name") or ""), d["name"]] if a]
        devs.append(d)
    return _dedupe_sort(devs)


def skipped_by_scope(rows: List[Dict[str, object]], cfg: dict) -> List[Dict[str, object]]:
    """수집하지 않는(범위 밖) 장비 이름 — 화면에 '수집 안 함' 으로 보여 주기 위한 목록. NAS 접근 없음."""
    out = []
    for row in rows:
        if not row.get("on", True):
            continue
        sub = str(row.get("sub", "")).strip()
        auto = sub in (AUTO, "auto", "AUTO")
        if auto:
            continue                                   # `*` 는 이제 제한 중에도 도므로 '수집 안 함' 이 아니다
        if not auto and scope.allows_row(cfg, row):
            continue
        folder = sub if not auto else ""
        name = display_name(folder or str(row.get("name") or ""), row.get("name"), row.get("memo"))
        out.append({"name": name or str(row.get("name") or ""), "note": str(row.get("memo") or ""),
                    "auto": auto})
    out.sort(key=lambda d: sort_key(str(d["name"])))
    return out


def devices_from_csv(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, object]]:
    return devices_from_rows(read_devices_csv(cfg["devices_csv"]), cfg, log)


def discover_devices(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, object]]:
    """devices.csv 가 없을 때의 폴백: nas_roots 각각을 `*` 로 본다.

    범위 제한 중에는 `_discover_under` 가 공유를 나열하지 않고 허용 이름만 정확 경로로 확인한다."""
    devs: List[Dict[str, object]] = []
    for root in cfg.get("nas_roots") or []:
        root = _norm_root(root)
        found = _discover_under(root, cfg, log)
        if not found:
            _log(log, f"[건너뜀] NAS 접근 불가 또는 장비 폴더 없음: {root}")
        devs.extend(found)
    return _dedupe_sort(devs)


def resolve_devices(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, object]]:
    """설정에 맞는 장비 목록. devices.csv 가 있으면 그것, 없으면 nas_roots 자동 탐색."""
    if not scope.unrestricted(cfg):
        _log(log, f"수집 범위: {scope.describe(cfg)} (다른 장비에는 접근하지 않습니다)")
    path = cfg.get("devices_csv") or ""
    if path and os.path.isfile(path):
        devs = _attach_dirs(devices_from_csv(cfg, log), cfg, log)
        _log(log, f"devices.csv 기준 장비 {len(devs)}대: {', '.join(str(d['name']) for d in devs)}")
        return devs
    _log(log, f"devices.csv 가 없어 nas_roots 를 자동 탐색합니다 ({path or '경로 미지정'})")
    devs = _attach_dirs(discover_devices(cfg, log), cfg, log)
    _log(log, f"장비 {len(devs)}대 발견: {', '.join(str(d['name']) for d in devs)}")
    return devs


def check_rows(rows: List[Dict[str, object]], cfg: dict) -> List[Dict[str, object]]:
    """UI 의 '연결 확인': 행마다 상태 문자열 키를 돌려준다(ok / auto:<n> / no_report / unreachable / out_of_scope).

    ★ 범위 밖 행은 연결 확인에서도 접근하지 않는다 — 상태만 out_of_scope 로 알려 준다."""
    out = []
    for row in rows:
        sub = str(row.get("sub", "")).strip()
        auto = sub in (AUTO, "auto", "AUTO")
        if not auto and not scope.allows_row(cfg, row):
            out.append({**row, "status": "out_of_scope"})
            continue
        root = _norm_root(str(row.get("root", "")))
        if not os.path.isdir(root):
            out.append({**row, "status": "unreachable"})
            continue
        if auto:
            n = len(_discover_under(root, cfg))
            out.append({**row, "status": f"auto:{n}" if n else "no_report"})
            continue
        path = os.path.join(root, sub) if sub else root
        out.append({**row, "status": "ok" if _has_report(path, cfg) else "no_report"})
    return out
