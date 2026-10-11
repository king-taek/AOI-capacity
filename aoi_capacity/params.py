"""레시피 파라미터(10/11, D89) — Lot 마다 첫 Wafer 폴더의 카메라 레시피 파일을 읽어 두고, 결과 HTML 의 '파라미터' 탭이 장비끼리 비교한다.

읽기(수집 스레드에서, NAS 읽기만):
  INI 를 찾은(EXACT) **첫 Wafer 폴더 안만** 본다 — 맨 위 한 번 나열 + 하위 폴더 `Zones` · `Recipe2-Zones` · `TrainData` 나열(재귀 아님, 규칙 4 —
  Wafer 폴더는 Report 로 계산한 정확 경로다). 결과 · 이미지 · 장비 고정 파일(EquipmentInfo 따위)은 열지 않는다.
보관(메인 스레드, 캐시 `params`):
  파일마다 파싱해 **측정값(Wafer 마다 바뀌는 키)을 뺀** 정규화 글로 바꾸고 그 해시로 한 번만 둔다(`blobs`) — 같은 설정이면 Lot 이 몇 개든 늘지 않는다.
  Report 마다 스냅숏 `{dev, job, setup, t, report, f: {파일: 해시}, rn: [레시피 이름]}`.
HTML(`build_meta`):
  Job 마다 장비별 **가장 최근 스냅숏**을 묶어 그룹 · Zone · 키 순서대로, 값은 다수값 + 다른 장비만(`x`), 바뀐 이력(`h`).
"""
from __future__ import annotations

import base64
import functools
import collections
import gzip
import hashlib
import json
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

from . import nas_guard

#: Wafer 폴더 맨 위에서 읽는 파일(대소문자 무시). MultiRecipe · Zones.ini · Recipe2-Zones.ini 는 화면에 그리지 않고 레시피 이름 · Zone 순서에만 쓴다.
TOP_FILES = ("Recipe.ini", "RTP.txt", "GlobalRTP.ini", "DefectsClustering.ini", "AlignRtp.ini", "Params_AlignRTP.ini",
             "OpticPreset.ini", "Recipe2-OpticPreset.ini", "OpticsPreset.ini", "Recipe2-OpticsPreset.ini",
             "Params_SystemInfo.ini", "Params_WaferInfo.ini", "WaferType.ini", "MultiRecipe.ini", "Zones.ini", "Recipe2-Zones.ini")
#: 하위 폴더 — 그 안의 *.ini 만(한 단계).
SUB_DIRS = ("Zones", "Recipe2-Zones", "TrainData")
FOCUS_REL = "FocusMapping/FocusMapping.ini"
#: 그리지 않는 키(어느 파일이든) — 카메라 마지막 위치 · 레시피 이름 칸.
SKIP_KEYS = {"lastcam", "lastcamzoom", "recipe name"}
#: 측정값 — 같은 장비 · 같은 Job 의 이어진 Lot 사이에서 거의 늘 바뀌는 키(30일 로그 2,159쌍으로 확인, 10/11). `상대 경로/섹션/키` 에 맞춘다.
#: 설정이 아니라서 비교하면 모든 장비가 '다름' 이 되고, 보관하면 Lot 마다 새 스냅숏이 생긴다. 레시피 · 장비와 같이 바뀌는 것(TrainData Step · Size,
#: ExtraScanLength, NominalHeight)은 설정으로 남긴다.
MEASURE_RE = re.compile("|".join((
    r"^(Params_AlignRTP|AlignRtp)\.ini/.*/Rotate_Wafer$",
    r"^(Recipe2-)?Optics?Preset\.ini/.*/(FocusPosAboveChuck|Zwafer|LightSrc(Ref|Dif|Dif2)_NominalGL|Id)$",
    r"^Params_SystemInfo\.ini/.*/(DistortionPath|GainPath|OffsetPath|LastModifyTime)$",
    r"^Params_WaferInfo\.ini/.*/ScanResultsPath$",
    r"^TrainData/.*/ChuckPos[XY]$",
    r"^(Recipe2-)?Zones\.ini/MskPixelCount/",
)), re.I)
#: 그룹(화면 순서) — (이름, 파일 판정, 접힘). Zones 두 그룹의 이름은 레시피 이름으로 바꾼다(`zone_group_name`).
GROUPS: Tuple[Tuple[str, object, bool], ...] = (
    ("Recipe 동작", lambda r: r == "Recipe.ini", False),
    ("검출 (RTP)", lambda r: r == "RTP.txt", False),
    ("Zones", lambda r: r.startswith("Zones/"), False),
    ("Zones (Recipe 2)", lambda r: r.startswith("Recipe2-Zones/"), False),
    ("Global RTP", lambda r: r in ("GlobalRTP.ini", "DefectsClustering.ini"), False),
    ("Focus · Alignment", lambda r: r in (FOCUS_REL, "AlignRtp.ini", "Params_AlignRTP.ini"), True),
    ("광학", lambda r: r in ("OpticPreset.ini", "Recipe2-OpticPreset.ini", "OpticsPreset.ini", "Recipe2-OpticsPreset.ini"), True),
    ("System", lambda r: r in ("Params_SystemInfo.ini", "Params_WaferInfo.ini", "WaferType.ini"), True),
    ("Teaching", lambda r: r.startswith("TrainData/"), True),
)
#: 장비마다 다른 것이 정상인 그룹 — 다른 칸만 HTML 에 담는다(크기).
DEVICE_GROUPS = {"광학", "System", "Teaching"}
#: Recipe.ini 의 Every 값 — 숫자 대신 글자로(사용자 10/11 Q10). collect.EVERY_LABELS 와 같은 표.
EVERY_KEYS = {"cleanreferenceevery", "autofocusevery"}
EVERY_LABELS = {"1": "None", "2": "Lot", "3": "Wafer"}
SEP = "\x1f"
UNIT_RE = r"[A-Za-z%µ°/.²]{1,12}"


# ───────────────────────────────────────────────────────── 읽기(NAS, 스레드)
def read_wafer_files(wdir: str) -> Dict[str, bytes]:
    """Wafer 폴더 하나(정확 경로)에서 파라미터 파일 바이트 — {상대 경로(/): 바이트}. 읽기 전용, 재귀 없음."""
    out: Dict[str, bytes] = {}
    with nas_guard.scandir(wdir) as it:
        top = {e.name.lower(): (e.name, e.is_dir()) for e in it}
    for name in TOP_FILES:
        hit = top.get(name.lower())
        if hit and not hit[1]:
            try:
                out[name] = nas_guard.read_bytes(os.path.join(wdir, hit[0]))
            except OSError:
                pass
    for sub in SUB_DIRS:
        hit = top.get(sub.lower())
        if not (hit and hit[1]):
            continue
        sd = os.path.join(wdir, hit[0])
        try:
            with nas_guard.scandir(sd) as it:
                names = sorted(e.name for e in it if e.name.lower().endswith(".ini") and e.is_file())
        except OSError:
            continue
        for n in names:
            try:
                out[f"{sub}/{n}"] = nas_guard.read_bytes(os.path.join(sd, n))
            except OSError:
                pass
    hit = top.get("focusmapping")
    if hit and hit[1]:
        try:
            out[FOCUS_REL] = nas_guard.read_bytes(os.path.join(wdir, hit[0], "FocusMapping.ini"))
        except OSError:
            pass
    return out


def decode(b: bytes) -> str:
    """레시피 파일은 한글 Windows 에서 쓴 ANSI(cp949) — 잘못된 바이트는 대체 문자로."""
    return b.decode("cp949", "replace").replace("\r\n", "\n").replace("\r", "\n")


# ───────────────────────────────────────────────────────── 파싱 · 정규화
def _split_comment(v: str) -> Tuple[str, str]:
    m = re.search(r"\s+;", v)
    if m:
        return v[:m.start()].strip(), v[m.end():].strip()
    return v.strip(), ""


def parse_ini(text: str) -> List[Tuple[str, str, str, str]]:
    """→ [(섹션, 키, 값, 주석)] 파일 순서."""
    out, sec = [], ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and "]" in line:
            sec = line[1:line.index("]")]
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        v, n = _split_comment(v)
        out.append((sec, k.strip(), v, n))
    return out


def parse_rtp(text: str) -> List[Tuple[str, str, str, str, str]]:
    """RTP.txt → [(Zone, 알고리즘, 키, 값, 주석)] — `Alg=` 줄이 그 아래 키들의 알고리즘."""
    out, zone, alg = [], "", ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        if line.startswith("[") and "]" in line:
            zone, alg = line[1:line.index("]")], ""
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v, n = _split_comment(v)
        if k == "Alg":
            alg = v
            continue
        n = re.sub(r"~\d+\s*\)?\s*$", "", n.strip())
        if n.startswith("("):
            n = n[1:].rstrip(")").strip()
        out.append((zone, alg, k, v, n))
    return out


def _keep(rel: str, sec: str, key: str) -> bool:
    if key.lower() in SKIP_KEYS:
        return False
    return not MEASURE_RE.search(f"{rel}/{sec}/{key}")


def normalize(rel: str, data: bytes) -> str:
    """파일 하나 → 정규화 글(줄마다 `섹션␟알고리즘␟키␟값␟주석`, 측정값 · 그리지 않는 키 제외). 같은 설정이면 같은 글."""
    text = decode(data)
    lines = []
    if rel == "RTP.txt":
        for zone, alg, k, v, n in parse_rtp(text):
            if _keep(rel, zone, k):
                lines.append(SEP.join((zone, alg, k, v, n)))
    else:
        for sec, k, v, n in parse_ini(text):
            if _keep(rel, sec, k):
                lines.append(SEP.join((sec, "", k, v, n)))
    return "\n".join(lines)


def recipe_names(multi: str) -> List[str]:
    """정규화한 MultiRecipe.ini → [레시피 1, 레시피 2 …] (`recipe_n=-1,PI_Bubble,…` 의 둘째 칸)."""
    got = {}
    for line in multi.splitlines():
        f = line.split(SEP)
        if len(f) >= 4:
            m = re.fullmatch(r"recipe_(\d+)", f[2], re.I)
            if m:
                parts = f[3].split(",")
                if len(parts) > 1 and parts[1].strip():
                    got[int(m.group(1))] = parts[1].strip()
    return [got[k] for k in sorted(got)]


def zone_order(zones_ini: str) -> List[str]:
    """정규화한 Zones.ini → [ALGName] 의 Zone 이름 순서."""
    return [f[3] for f in (ln.split(SEP) for ln in zones_ini.splitlines()) if len(f) >= 4 and f[0] == "ALGName"]


def snapshot(raw: Dict[str, bytes]) -> Dict[str, str]:
    """{상대 경로: 바이트} → {상대 경로: 정규화 글} (빈 파일은 뺀다)."""
    out = {}
    for rel, b in raw.items():
        norm = normalize(rel, b)
        if norm:
            out[rel] = norm
    return out


def blob_key(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


# ───────────────────────────────────────────────────────── 캐시 보관(메인 스레드)
def empty_store() -> dict:
    return {"v": 1, "blobs": {}, "snaps": {}}


def put(store: dict, key: str, *, dev: str, job: str, setup: str, t: str, report: str, files: Dict[str, str]) -> bool:
    """스냅숏 하나를 넣는다(같은 키 · 같은 내용이면 그대로) → 바뀌었으면 True."""
    blobs, snaps = store.setdefault("blobs", {}), store.setdefault("snaps", {})
    f = {}
    for rel, text in sorted(files.items()):
        h = blob_key(text)
        blobs.setdefault(h, text)
        f[rel] = h
    rn = recipe_names(files.get("MultiRecipe.ini", ""))
    snap = {"dev": dev, "job": job, "setup": setup, "t": t, "report": report, "f": f, "rn": rn}
    if snaps.get(key) == snap:
        return False
    snaps[key] = snap
    return True


def prune_blobs(store: dict) -> None:
    """어느 스냅숏도 가리키지 않는 글을 지운다."""
    used = {h for s in store.get("snaps", {}).values() for h in s.get("f", {}).values()}
    for h in [h for h in store.get("blobs", {}) if h not in used]:
        del store["blobs"][h]


# ───────────────────────────────────────────────────────── HTML 용 묶음
@functools.lru_cache(maxsize=1 << 16)
def _canon(v: str) -> str:
    try:
        return "n:" + repr(round(float(v), 9))
    except (TypeError, ValueError):
        return "s:" + (v or "").strip()


def split_unit(key: str, note: str) -> Tuple[str, str]:
    """`Threshold[um]` · `Size (um)` → ('Threshold', 'um'); 주석의 `[um]` 도 단위로."""
    unit, name = "", key
    m = re.search(r"[_\s]*[\[(](" + UNIT_RE + r")[\])]$", key)
    if m:
        unit, name = m.group(1), key[:m.start()].rstrip("_ ")
    if not unit and note:
        m = re.search(r"\[(" + UNIT_RE + r")\]", note)
        if m:
            unit = m.group(1)
    return name or key, unit


def _ounion(lists: Iterable[List]) -> List:
    """순서 있는 합집합 — 첫 목록 순서를 지키고 새 항목은 앞 항목 바로 뒤에(앞 항목이 없으면 맨 앞). 연결 목록이라 선형."""
    HEAD, END = object(), object()                     # 항목에 None 이 있을 수 있다(알고리즘 없는 섹션)
    nxt: Dict = {HEAD: END}
    for lst in lists:
        prev = HEAD
        for x in lst:
            if x not in nxt:
                nxt[x], nxt[prev] = nxt[prev], x
            prev = x
    out, cur = [], nxt[HEAD]
    while cur is not END:
        out.append(cur)
        cur = nxt[cur]
    return out


def _group_of(rel: str) -> Optional[Tuple[int, str, bool]]:
    for i, (name, match, fold) in enumerate(GROUPS):
        if match(rel):
            return i, name, fold
    return None


def _struct(files: Dict[str, str]) -> Dict[int, "collections.OrderedDict"]:
    """장비 하나의 스냅숏 → {그룹 번호: {(파일, zone 소문자): {zone, algs: {alg: {키 식별: (키, 값, 주석)}}}}}."""
    G: Dict[int, collections.OrderedDict] = {i: collections.OrderedDict() for i in range(len(GROUPS))}
    order = {"Zones/": [z.lower() for z in zone_order(files.get("Zones.ini", ""))],
             "Recipe2-Zones/": [z.lower() for z in zone_order(files.get("Recipe2-Zones.ini", ""))]}

    def add(gi, file, zone, alg, k, v, n):
        z = G[gi].setdefault((file, (zone or "").lower()), {"zone": zone, "algs": collections.OrderedDict()})
        a = z["algs"].setdefault(alg, collections.OrderedDict())
        ident, i = k, 2
        while ident in a:
            ident, i = f"{k}#{i}", i + 1
        a[ident] = (k, v, n)

    zone_files: Dict[str, list] = {"Zones/": [], "Recipe2-Zones/": []}
    for rel in sorted(files):
        g = _group_of(rel)
        if g is None:
            continue
        gi = g[0]
        rows = [ln.split(SEP) for ln in files[rel].splitlines()]
        rows = [r for r in rows if len(r) == 5]
        pre = next((p for p in zone_files if rel.startswith(p)), None)
        if pre:
            zn = next((r[3] for r in rows if r[0] == "General" and r[2] == "ZoneName"), None) or os.path.splitext(rel[len(pre):])[0]
            zone_files[pre].append((gi, zn, rows))
            continue
        base = os.path.basename(rel)
        for sec, alg, k, v, n in rows:
            add(gi, base, sec, alg or None, k, v, n)
    for pre, lst in zone_files.items():
        o = order[pre]
        lst.sort(key=lambda t: o.index(t[1].lower()) if t[1].lower() in o else 10 ** 6)
        for gi, zn, rows in lst:
            for sec, _alg, k, v, n in rows:
                if sec == "General" and k == "ZoneName":
                    continue
                add(gi, pre + "*.ini", zn, sec, k, v, n)
    return G


def _file_items(rel: str, text: str) -> Dict[Tuple, Tuple[str, str]]:
    """이력 비교용 — 파일 하나의 {(섹션, 알고리즘, 키 식별): (값, 표시 이름)}. 같은 키가 겹치면 #2 · #3."""
    out: Dict[Tuple, Tuple[str, str]] = {}
    zone_pre = next((p for p in ("Zones/", "Recipe2-Zones/") if rel.startswith(p)), None)
    rows = [r for r in (ln.split(SEP) for ln in text.splitlines()) if len(r) == 5]
    zn = None
    if zone_pre:
        zn = next((r[3] for r in rows if r[0] == "General" and r[2] == "ZoneName"), None) or os.path.splitext(rel[len(zone_pre):])[0]
    for sec, alg, k, v, _n in rows:
        ident, i = (sec, alg, k), 2
        while ident in out:
            ident, i = (sec, alg, f"{k}#{i}"), i + 1
        out[ident] = (v, " · ".join(x for x in (zn, sec, alg, k) if x))
    return out


def _every(k: str, v: str, n: str) -> str:
    """Clean reference · AutoFocus 의 Every 값은 글자만(Q10)."""
    if k.lower() in EVERY_KEYS:
        return n if n and len(n) <= 20 else EVERY_LABELS.get(v.strip(), v)
    return v


def build_meta(store: dict, sort_key=None, *, max_changes: int = 40) -> dict:
    """캐시 `params` → HTML `meta.params` = {"v": 2, "jobs": [{"j": Job, "n": 장비 수, "t": 가장 최근 스캔, "z": gzip+base64(JSON)}]}.
    Job 하나의 JSON(아래)은 **그 Job 만의 pool** 을 갖고 gzip 으로 접어 둔다 — 30일 516 Job 이 펼치면 21MB 라서, 화면이 고를 때만 푼다
    (브라우저 내장 DecompressionStream, 바깥 요청 없음).

    {"pool": [문자열], "jobs": [{"j": Job, "d": [장비], "l": [[시각, Report]…], "g": [[그룹 이름, 접힘, [[zone, alg, [[키, 단위, 주석, 다수값, {장비 번호: 값}, [빠진 장비], 동률]…]]…]]…],
      "h": [[시각, 장비, Report, [[이름, 이전, 지금]…], 더 있음]…]}]} — 문자열은 전부 pool 번호."""
    blobs = store.get("blobs", {})
    _memo: Dict[Tuple[str, Optional[str]], dict] = {}

    def items_of(rel: str, h: Optional[str]) -> dict:
        if h is None:
            return {}
        got = _memo.get((rel, h))
        if got is None:
            got = _memo[(rel, h)] = _file_items(rel, blobs.get(h, ""))
        return got

    files_of = lambda s: {rel: blobs.get(h, "") for rel, h in s.get("f", {}).items()}
    by_job: Dict[str, Dict[str, list]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for s in store.get("snaps", {}).values():
        if s.get("job") and s.get("f"):
            by_job[s["job"]][s.get("dev", "")].append(s)
    jobs_out = []
    for job in sorted(by_job):
        pool: List[str] = []
        pidx: Dict[str, int] = {}

        def P(s) -> int:
            s = "" if s is None else str(s)
            i = pidx.get(s)
            if i is None:
                i = pidx[s] = len(pool)
                pool.append(s)
            return i

        per_dev = by_job[job]
        devs = sorted(per_dev, key=sort_key or (lambda d: d))
        for d in devs:
            per_dev[d].sort(key=lambda s: s.get("t") or "")
        latest = {d: per_dev[d][-1] for d in devs}
        S = {d: _struct(files_of(latest[d])) for d in devs}
        rn = next((latest[d]["rn"] for d in devs if latest[d].get("rn")), [])
        groups = []
        for gi, (gname, _m, fold) in enumerate(GROUPS):
            if gname == "Zones" and rn:
                gname = f"Zones — {rn[0]}"
            elif gname == "Zones (Recipe 2)" and len(rn) > 1:
                gname = f"Zones — {rn[1]}"
            zkeys = _ounion([list(S[d][gi].keys()) for d in devs])
            zones_out = []
            for zk in zkeys:
                zs = {d: S[d][gi].get(zk) for d in devs}
                disp = next(z["zone"] for z in zs.values() if z)
                for alg in _ounion([list(z["algs"].keys()) for z in zs.values() if z]):
                    idents = _ounion([list(z["algs"][alg].keys()) for z in zs.values() if z and alg in z["algs"]])
                    items = []
                    for ident in idents:
                        vals, notes, raw = {}, {}, None
                        for di, d in enumerate(devs):
                            z = zs[d]
                            if z and alg in z["algs"] and ident in z["algs"][alg]:
                                k, v, n = z["algs"][alg][ident]
                                raw = raw or k
                                vals[di] = _every(k, v, n)
                                if n:
                                    notes[di] = n
                        cnt = collections.Counter(_canon(v) for v in vals.values())
                        first = {}
                        for di in sorted(vals):
                            first.setdefault(_canon(vals[di]), di)
                        best = sorted(cnt, key=lambda c: (-cnt[c], first[c]))
                        tie = len(best) > 1 and cnt[best[0]] == cnt[best[1]]
                        major = next(vals[di] for di in sorted(vals) if _canon(vals[di]) == best[0])
                        exc = {str(di): P(v) for di, v in vals.items() if _canon(v) != best[0]}
                        missing = [di for di in range(len(devs)) if di not in vals]
                        if gname in DEVICE_GROUPS and not exc and not missing:
                            continue
                        note = next((notes[di] for di in sorted(notes) if _canon(vals[di]) == best[0]), None) or next(iter(notes.values()), "")
                        if raw.lower() in EVERY_KEYS:
                            note = ""
                        name, unit = split_unit(raw, note)
                        items.append([P(name), P(unit), P(note), P(major), exc, missing, 1 if tie else 0])
                    if items:
                        zones_out.append([P(disp or ""), P(alg or ""), items])
            if zones_out:
                groups.append([P(gname), 1 if fold else 0, zones_out])
        hist = []
        for di, d in enumerate(devs):
            prev = None
            for s in per_dev[d]:
                if prev is not None and prev.get("f") != s.get("f"):
                    fa, fb = prev.get("f", {}), s.get("f", {})
                    ch = []
                    for rel in _ounion([list(fa), list(fb)]):          # 바뀐 파일만 펴서 비교한다(같은 해시는 같은 글)
                        if fa.get(rel) == fb.get(rel) or _group_of(rel) is None:
                            continue
                        a, b = items_of(rel, fa.get(rel)), items_of(rel, fb.get(rel))
                        for key in _ounion([list(a), list(b)]):
                            va, vb = a.get(key, ("", ""))[0], b.get(key, ("", ""))[0]
                            if va != vb and _canon(va) != _canon(vb):
                                ch.append([P((b.get(key) or a.get(key))[1]), P(va), P(vb)])
                    if ch:
                        hist.append([s.get("t") or "", di, P(s.get("report") or ""), ch[:max_changes], max(0, len(ch) - max_changes)])
                prev = s
        hist.sort(key=lambda x: x[0], reverse=True)
        body = {"pool": pool, "d": devs, "l": [[latest[d].get("t") or "", P(latest[d].get("report") or "")] for d in devs],
                "g": groups, "h": hist}
        raw = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        jobs_out.append({"j": job, "n": len(devs), "t": max((latest[d].get("t") or "") for d in devs),
                         "z": base64.b64encode(gzip.compress(raw, 6, mtime=0)).decode("ascii")})
    return {"v": 2, "jobs": jobs_out}


def unpack(job_entry: dict) -> dict:
    """`build_meta` 의 Job 하나를 편다(테스트 · 점검용 — 화면은 JS 가 같은 일을 한다)."""
    return json.loads(gzip.decompress(base64.b64decode(job_entry["z"])).decode("utf-8"))
