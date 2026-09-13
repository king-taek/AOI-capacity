"""장비 목록 — devices.csv 읽기/쓰기와 장비 폴더 판정.

CSV 열: 장비명, NAS경로, 폴더, 사용, 메모  (영문 헤더도 인식, 헤더가 없으면 이 순서로 본다)
- 폴더 비움  → NAS경로 자체가 장비 폴더(안에 Report 폴더)
- 폴더 "*"   → NAS경로 안에서 Report 폴더가 있는 하위 폴더를 모두 자동 등록(재귀 없음, 한 단계)
- 사용 N/0/아니오 → 건너뜀

NAS 는 읽기만 한다(`nas_guard.read_bytes/scandir`, `os.path.isdir`). CSV 쓰기는 이 PC 의 데이터 폴더에만.
"""
from __future__ import annotations

import csv
import logging
import os
import re
from typing import Callable, Dict, List, Optional

from . import nas_guard

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

LogFn = Callable[[str], None]


def _log(log: Optional[LogFn], msg: str) -> None:
    _LOG.info(msg)
    if log:
        log(msg)


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


def _norm_root(root: str) -> str:
    root = str(root).strip()
    return root.rstrip("\\/") + os.sep if re.fullmatch(r"[A-Za-z]:\\?", root) else root


def _has_report(path: str, cfg: dict) -> bool:
    return os.path.isdir(os.path.join(path, cfg["report_dir"]))


def _discover_under(root: str, cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, str]]:
    """root 자체가 장비 폴더면 그것 하나, 아니면 root 바로 아래에서 Report 폴더가 있는 폴더들(한 단계, 재귀 없음)."""
    if not os.path.isdir(root):
        return []
    if _has_report(root, cfg):
        return [{"name": os.path.basename(root.rstrip("\\/")) or root, "path": root}]
    out = []
    try:
        for e in nas_guard.scandir(root):
            if e.is_dir() and _has_report(e.path, cfg):
                out.append({"name": e.name, "path": e.path})
    except OSError as ex:
        _log(log, f"[건너뜀] {root}: {ex}")
    return out


def _share_label(path: str) -> str:
    """X:\\AOI-1 → 'X:', \\\\host\\share\\AOI-1 → 'share', /nas/X/AOI-1 → 'X'."""
    parent = os.path.dirname(str(path).rstrip("\\/"))
    stripped = parent.rstrip("\\/")
    return os.path.basename(stripped) or stripped or parent


def _dedupe_sort(devs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen, uniq = set(), []  # 같은 폴더가 두 번(명시 행 + * 행) 나오면 먼저 적힌 행이 이긴다
    for d in devs:
        key = os.path.normcase(os.path.normpath(d["path"]))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)
    names: Dict[str, int] = {}
    for d in uniq:
        names[d["name"]] = names.get(d["name"], 0) + 1
    for d in uniq:  # 공유가 다른 동명 폴더는 부모 폴더(공유·드라이브) 이름을 앞에 붙여 구분
        if names[d["name"]] > 1:
            d["name"] = f"{_share_label(d['path'])} {d['name']}"
    uniq.sort(key=lambda d: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", d["name"])])
    return uniq


def devices_from_rows(rows: List[Dict[str, object]], cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, str]]:
    """CSV 행을 실제 장비 폴더 목록 [{name, path}] 로 푼다. 접근할 수 없는 행은 로그에 남기고 건너뛴다."""
    devs: List[Dict[str, str]] = []
    for row in rows:
        if not row.get("on", True):
            continue
        root = _norm_root(str(row.get("root", "")))
        sub = str(row.get("sub", "")).strip()
        label = str(row.get("name") or sub or root)
        if sub in (AUTO, "auto", "AUTO"):
            found = _discover_under(root, cfg, log)
            if not found:
                _log(log, f"[건너뜀] {label}: NAS 접근 불가 또는 장비 폴더 없음 ({root})")
            devs.extend(found)
            continue
        path = os.path.join(root, sub) if sub else root
        if not _has_report(path, cfg):
            _log(log, f"[건너뜀] {label}: Report 폴더 없음/접근 불가 ({path})")
            continue
        devs.append({"name": str(row.get("name") or sub or os.path.basename(path.rstrip("\\/")) or path), "path": path})
    return _dedupe_sort(devs)


def devices_from_csv(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, str]]:
    return devices_from_rows(read_devices_csv(cfg["devices_csv"]), cfg, log)


def discover_devices(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, str]]:
    """devices.csv 가 없을 때의 폴백: nas_roots 각각을 * 로 본다."""
    devs: List[Dict[str, str]] = []
    for root in cfg.get("nas_roots") or []:
        root = _norm_root(root)
        found = _discover_under(root, cfg, log)
        if not found:
            _log(log, f"[건너뜀] NAS 접근 불가 또는 장비 폴더 없음: {root}")
        devs.extend(found)
    return _dedupe_sort(devs)


def resolve_devices(cfg: dict, log: Optional[LogFn] = None) -> List[Dict[str, str]]:
    """설정에 맞는 장비 목록. devices.csv 가 있으면 그것, 없으면 nas_roots 자동 탐색."""
    path = cfg.get("devices_csv") or ""
    if path and os.path.isfile(path):
        devs = devices_from_csv(cfg, log)
        _log(log, f"devices.csv 기준 장비 {len(devs)}대: {', '.join(d['name'] for d in devs)}")
        return devs
    _log(log, f"devices.csv 가 없어 nas_roots 를 자동 탐색합니다 ({path or '경로 미지정'})")
    devs = discover_devices(cfg, log)
    _log(log, f"장비 {len(devs)}대 발견: {', '.join(d['name'] for d in devs)}")
    return devs


def check_rows(rows: List[Dict[str, object]], cfg: dict) -> List[Dict[str, object]]:
    """UI 의 '연결 확인': 행마다 상태 문자열 키를 돌려준다(ok / auto:<n> / no_report / unreachable)."""
    out = []
    for row in rows:
        root = _norm_root(str(row.get("root", "")))
        sub = str(row.get("sub", "")).strip()
        if not os.path.isdir(root):
            out.append({**row, "status": "unreachable"})
            continue
        if sub in (AUTO, "auto", "AUTO"):
            n = len(_discover_under(root, cfg))
            out.append({**row, "status": f"auto:{n}" if n else "no_report"})
            continue
        path = os.path.join(root, sub) if sub else root
        out.append({**row, "status": "ok" if _has_report(path, cfg) else "no_report"})
    return out
