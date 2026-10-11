"""30일 Wafer 로그 zip 으로 파라미터 이력 한 번 채우기(10/11 사용자 Q9, D89).

현장 수집 창의 'Wafer 로그 30일 전체 수집' 이 만든 `AOI_wafer_logs30_…_partNN.zip`(또는 `.zip.enc`)을 이 PC 의 폴더에서 읽어
Lot 마다 첫 Wafer 의 파라미터 파일을 `params.put` 으로 캐시 스냅숏에 넣는다. NAS 는 건드리지 않는다(로컬 zip 만 읽는다).

zip 구조(`scripts/collect_wafer_logs.py`): `<번호>_<장비>_<Lot>/report/<BatchReport>.htm` · `<Wafer>/<파일>` · `_목록.tsv`
(wafer · 상대경로 · 크기 · 수정시각 · sha1 · 저장 — 같은 내용은 한 번만 담고 나머지는 `= <Lot 폴더>/<Wafer>/<경로>` 참조, 다른 zip 장에 있을 수 있다).
"""
from __future__ import annotations

import importlib.util
import io
import os
import re
import zipfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import params as params_mod
from . import scope

TOOL_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collect_wafer_logs.py"
_LOT_DIR_RE = re.compile(r"^\d+_(.+?)_(.+)$")
_WANT_TOP = {n.lower(): n for n in params_mod.TOP_FILES}


def _decrypt(blob: bytes) -> bytes:
    spec = importlib.util.spec_from_file_location("aoi_collect_wafer_logs_dec", str(TOOL_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.decrypt_bytes(blob, mod._enc_secret())


def _open_zips(folder: str, log: Callable[[str], None]) -> List[zipfile.ZipFile]:
    zips = []
    for name in sorted(os.listdir(folder)):
        low = name.lower()
        p = os.path.join(folder, name)
        if not os.path.isfile(p) or not (low.endswith(".zip") or low.endswith(".zip.enc")):
            continue
        try:
            with open(p, "rb") as f:
                blob = f.read()
            if low.endswith(".enc"):
                blob = _decrypt(blob)
            zips.append(zipfile.ZipFile(io.BytesIO(blob)))
        except Exception as e:  # noqa: BLE001
            log(f"[파라미터 가져오기] {name}: 읽지 못함 — {type(e).__name__}: {e}")
    return zips


def _wanted(rel: str) -> Optional[str]:
    """zip 안 Wafer 폴더 아래 상대 경로 → 파라미터로 쓸 이름(params 의 상대 경로 표기) 또는 None."""
    parts = rel.split("/")
    if len(parts) == 1:
        return _WANT_TOP.get(parts[0].lower())
    if len(parts) == 2 and parts[1].lower().endswith(".ini"):
        sub = next((s for s in params_mod.SUB_DIRS if s.lower() == parts[0].lower()), None)
        if sub:
            return f"{sub}/{parts[1]}"
        if parts[0].lower() == "focusmapping" and parts[1].lower() == "focusmapping.ini":
            return params_mod.FOCUS_REL
    return None


def import_zips(folder: str, store: dict, *, dev_key_of: Callable[[str], str], report_key: Callable[[str, str], str],
                parse_report: Callable[[str, str], dict], parse_dt: Callable[[str], object], cfg: dict,
                log: Callable[[str], None] = lambda m: None, progress: Callable[[int, int, str], None] = lambda d, t, p: None) -> Dict[str, int]:
    """폴더의 zip 들 → `store`(캐시 params)에 스냅숏을 넣는다. 이미 있는 Report 키는 건너뛴다. 범위 밖 장비는 넣지 않는다."""
    zips = _open_zips(folder, log)
    index: Dict[str, zipfile.ZipFile] = {}
    for z in zips:
        for n in z.namelist():
            index.setdefault(n, z)
    lots = sorted({n.split("/", 1)[0] for n in index if "/" in n})
    manifest: Dict[str, Dict[Tuple[str, str], str]] = {}

    def man(lot: str) -> Dict[Tuple[str, str], str]:
        if lot not in manifest:
            m: Dict[Tuple[str, str], str] = {}
            z = index.get(f"{lot}/_목록.tsv")
            if z is not None:
                for line in z.read(f"{lot}/_목록.tsv").decode("utf-8", "replace").splitlines()[1:]:
                    f = line.split("\t")
                    if len(f) >= 6:
                        m[(f[0], f[1])] = f[5]
            manifest[lot] = m
        return manifest[lot]

    def read(lot: str, wafer: str, rel: str, depth: int = 0) -> Optional[bytes]:
        name = f"{lot}/{wafer}/{rel}"
        z = index.get(name)
        if z is not None:
            return z.read(name)
        st = man(lot).get((wafer, rel), "")
        if st.startswith("= ") and depth < 5:
            parts = st[2:].split("/", 2)
            if len(parts) == 3:
                return read(parts[0], parts[1], parts[2], depth + 1)
        return None

    stats = {"zips": len(zips), "lots": len(lots), "added": 0, "skipped_known": 0, "skipped_scope": 0, "no_params": 0, "no_report": 0}
    for i, lot in enumerate(lots):
        progress(i, len(lots), lot)
        m = _LOT_DIR_RE.match(lot)
        if not m:
            continue
        dev = m.group(1)
        if not scope.is_allowed(cfg, dev):
            stats["skipped_scope"] += 1
            continue
        rep_name = next((n.split("/")[-1] for n in index if n.startswith(f"{lot}/report/") and n.lower().endswith(".htm")), None)
        if not rep_name:
            stats["no_report"] += 1
            continue
        key = report_key(dev_key_of(dev), rep_name)
        if key in store.get("snaps", {}):
            stats["skipped_known"] += 1
            continue
        rep = parse_report(rep_name, index[f"{lot}/report/{rep_name}"].read(f"{lot}/report/{rep_name}").decode("utf-8", "replace"))
        # 첫 Wafer = _목록 순서에서 파라미터 파일이 있는 첫 Wafer(수집 도구가 Lot 의 첫 Wafer 를 먼저 적는다)
        wafers: List[str] = []
        for (w, rel) in man(lot):
            if w not in wafers and _wanted(rel):
                wafers.append(w)
        for n in index:
            if n.startswith(lot + "/"):
                parts = n.split("/")
                if len(parts) >= 3 and parts[1] not in ("_묶음", "report") and parts[1] not in wafers and _wanted("/".join(parts[2:])):
                    wafers.append(parts[1])
        if not wafers:
            stats["no_params"] += 1
            continue
        w = wafers[0]
        rels = {rel for (ww, rel) in man(lot) if ww == w}
        rels |= {n[len(f"{lot}/{w}/"):] for n in index if n.startswith(f"{lot}/{w}/")}
        raw = {}
        for rel in sorted(rels):
            want = _wanted(rel)
            if want:
                b = read(lot, w, rel)
                if b is not None:
                    raw[want] = b
        files = params_mod.snapshot(raw)
        if not files:
            stats["no_params"] += 1
            continue
        bst = parse_dt((rep.get("summary") or {}).get("Batch Start", ""))
        if params_mod.put(store, key, dev=dev, job=rep.get("job", ""), setup=rep.get("setup", ""),
                          t=bst.strftime("%Y-%m-%d %H:%M") if bst else "", report=rep_name, files=files):
            stats["added"] += 1
    progress(len(lots), len(lots), "")
    return stats
