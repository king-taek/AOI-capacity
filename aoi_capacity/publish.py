"""LOT 추적 배포(10/27) — 수집할 때마다 LOT 추적만 담은 HTML 을 팀 공유 폴더에 조용히 올린다.

폴더 모양::

    <배포 폴더>\\AOI_LOT.html        바로가기가 가리키는 안내 파일(거의 안 바뀜) — latest.js 를 읽고 최신 데이터 파일로 이동한다
    <배포 폴더>\\latest.js           최신 데이터 파일 이름 한 줄(매번 바뀜)
    <배포 폴더>\\data\\lot_<날짜>_<시각>.html   화면 + 데이터 한 장(덮어쓰지 않고 새 이름으로)

열려 있는 파일은 Windows 가 교체를 막는다(공유 폴더 시험 10/26: 열린 동안 5번 모두 실패). 그래서 데이터 파일은 덮어쓰지 않고,
바꾸는 것은 몇 바이트짜리 latest.js 뿐이며(열리자마자 이동하는 안내 파일만 읽는다) 잠겨 있으면 몇 번 다시 시도한다.
오래된 데이터 파일은 `KEEP_FILES` 개만 남기고 지우되, 열려 있어 못 지우면 다음에 다시 시도한다.

**전체 배포(10/30)**: 같은 틀을 한 번 더 — `publish_full_dir` 에 `AOI_ALL.html` · `latest.js` · `data\\all_날짜_시각.html`(모든 탭, 최근 `publish_full_days` 일 · 기본 90일).
LOT 추적 배포와 폴더가 달라야 하고(같은 폴더면 `latest.js` 가 겹친다) 수집이 끝나면 LOT 추적 뒤에 이어서 올린다. 장비 NAS 경로는 Report 열기에 필요해 그대로 담는다(사용자 확정).

★ 배포 폴더가 장비 NAS 아래면 쓰지 않는다(`nas_guard.assert_local`) — 이 모듈의 쓰기 함수는 첫 줄에서 부른다. 가드 `test_lot_publish.py`.
"""
from __future__ import annotations

import datetime as dt
import html
import os
import re
import time
import urllib.parse
from typing import Callable, Dict, List, NamedTuple, Optional

from . import collect, i18n, nas_guard

STUB_NAME = "AOI_LOT.html"
SHORTCUT_NAME = "AOI_LOT_shortcut.url"          # 폴더 안에 두는 인터넷 바로가기 — 팀원은 이 파일을 더블클릭하거나 바탕화면으로 복사
LATEST_NAME = "latest.js"
DATA_DIR = "data"
KEEP_FILES = 3
REPLACE_TRIES = 6
REPLACE_WAIT_SEC = 1.0


class Kind(NamedTuple):
    """배포 종류 하나 — 파일 이름 · 안내 파일이 읽는 전역 이름 · 문구. LOT 추적이 기본, 전체 배포는 `FULL`."""
    stub: str
    shortcut: str
    var: str
    prefix: str
    title: str
    loading: str
    fallback: str

    @property
    def data_re(self):
        return re.compile(r"^" + self.prefix + r"_\d{8}_\d{4,6}\.html$")


LOT = Kind(STUB_NAME, SHORTCUT_NAME, "AOI_LOT_LATEST", "lot", i18n.KO.PUBLISH_STUB_TITLE, i18n.KO.PUBLISH_STUB_LOADING, i18n.KO.PUBLISH_STUB_FALLBACK)
FULL = Kind("AOI_ALL.html", "AOI_ALL_shortcut.url", "AOI_ALL_LATEST", "all", i18n.KO.PUBLISH_FULL_STUB_TITLE,
            i18n.KO.PUBLISH_FULL_STUB_LOADING, i18n.KO.PUBLISH_FULL_STUB_FALLBACK)


def stub_text(kind: Kind = LOT) -> str:
    return ('<!doctype html><meta charset="utf-8">'
            f'<title>{html.escape(kind.title)}</title>'
            f'<body style="font:14px system-ui,sans-serif;padding:24px;color:#444">{html.escape(kind.loading)}'
            f'<p id="m" style="display:none">{html.escape(kind.fallback)}</p>'
            f'<script src="{LATEST_NAME}"></script>'
            f'<script>var u=window.{kind.var};if(u){{location.replace(u)}}else{{document.getElementById("m").style.display="block"}}</script>')


def latest_text(data_name: str, kind: Kind = LOT) -> str:
    return f'window.{kind.var}="{DATA_DIR}/{data_name}";\n'


def stub_url(share_dir: str, kind: Kind = LOT) -> str:
    """안내 파일의 file:// 주소 — UNC(`\\\\서버\\공유\\…`)는 `file://서버/공유/…`, 드라이브(`Z:\\…`)는 `file:///Z:/…`. 한글 · 공백은 퍼센트 인코딩."""
    p = str(share_dir).strip().rstrip("\\/").replace("\\", "/")
    q = lambda t: urllib.parse.quote(t, safe="/$:()@!,;=+-_.~")
    if p.startswith("//"):
        return "file:" + "//" + q(p[2:]) + "/" + kind.stub
    return "file:///" + q(p) + "/" + kind.stub


def raw_stub_url(share_dir: str, kind: Kind = LOT) -> str:
    """한글을 퍼센트 인코딩하지 않은 주소(공백만 %20) — .url 은 ANSI 로 읽히고 셸이 %XX 를 UTF-8 바이트 그대로 ANSI 로 해석해 경로가 깨진다(실측 10/27)."""
    p = str(share_dir).strip().rstrip("\\/").replace("\\", "/").replace(" ", "%20")
    if p.startswith("//"):
        return "file://" + p[2:] + "/" + kind.stub
    return "file:///" + p + "/" + kind.stub


def _ansi() -> str:
    return "mbcs" if os.name == "nt" else "cp949"


def shortcut_text(share_dir: str, kind: Kind = LOT) -> str:
    """바로가기(.url) 내용 — 한글 경로는 이 PC 의 ANSI 코드 페이지로 쓸 수 있을 때 그 글자 그대로(`shortcut_bytes`)."""
    return f"[InternetShortcut]\r\nURL={raw_stub_url(share_dir, kind)}\r\n"


def shortcut_bytes(share_dir: str, kind: Kind = LOT) -> bytes:
    """.url 파일 바이트 — ANSI(한글 윈도의 CP949)로 그대로, 인코딩이 안 되는 글자가 있으면 퍼센트 인코딩 판(UTF-8)으로."""
    try:
        return shortcut_text(share_dir, kind).encode(_ansi())
    except (UnicodeEncodeError, LookupError):
        return f"[InternetShortcut]\r\nURL={stub_url(share_dir, kind)}\r\n".encode("utf-8")


def write_shortcut(dest_dir: str, share_dir: str, cfg: dict, name: str = "", kind: Kind = LOT) -> str:
    """`dest_dir` 에 배포 폴더의 안내 파일을 여는 인터넷 바로가기(.url)를 만든다 — 바탕화면 등 이 PC 의 폴더. 만든 경로."""
    roots = nas_guard.roots_for_cfg(cfg)
    nas_guard.assert_local(dest_dir, roots)
    os.makedirs(dest_dir, exist_ok=True)
    path = os.path.join(dest_dir, name or kind.shortcut)
    if not _write_text(path, shortcut_bytes(share_dir, kind), roots, tries=2):
        raise PermissionError(13, i18n.KO.PUBLISH_SHORTCUT_LOCKED, path)
    return path


def _write_text(path: str, text, roots: List[str], *, tries: int = REPLACE_TRIES, newline: str = "") -> bool:
    """임시 파일에 쓰고 이름 바꿔 교체 — 잠겨 있으면 `tries` 번까지 기다려 다시. 성공 여부."""
    nas_guard.assert_local(path, roots)
    tmp = f"{path}.{os.getpid()}-{time.time_ns()}.tmp"
    try:
        with (open(tmp, "wb") if isinstance(text, bytes) else open(tmp, "w", encoding="utf-8", newline=newline)) as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        for i in range(max(1, tries)):
            try:
                os.replace(tmp, path)
                return True
            except PermissionError:
                if i + 1 < tries:
                    time.sleep(REPLACE_WAIT_SEC)
        return False
    finally:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def _prune(data_dir: str, keep: int, roots: List[str], protect=(), kind: Kind = LOT) -> int:
    """오래된 데이터 파일 정리 — 최신 `keep` 개만 남긴다(`protect` = 이번에 쓴 것과 latest.js 가 지금 가리키는 이름은 지우지 않는다). 지운 개수. 못 지운 것(열려 있음)은 다음에."""
    nas_guard.assert_local(data_dir, roots)
    try:
        names = sorted(n for n in os.listdir(data_dir) if kind.data_re.match(n))
    except OSError:
        return 0
    gone = 0
    now = time.time()
    for n in os.listdir(data_dir):                      # 쓰다 끊겨 남은 임시 파일(1시간 넘음)
        if n.endswith(".tmp"):
            fp = os.path.join(data_dir, n)
            try:
                if now - os.path.getmtime(fp) > 3600:
                    os.remove(fp)
            except OSError:
                pass
    for n in names[:-keep] if keep > 0 else names:
        if n in protect:
            continue
        try:
            os.remove(os.path.join(data_dir, n))
            gone += 1
        except OSError:
            pass
    return gone


def _pointed_name(share_dir: str, kind: Kind = LOT) -> str:
    """latest.js 가 지금 가리키는 데이터 파일 이름(못 읽으면 빈 값)."""
    try:
        with open(os.path.join(share_dir, LATEST_NAME), encoding="utf-8") as f:
            m = re.search(r"data/(" + kind.prefix + r"_[0-9_]+\.html)", f.read())
        return m.group(1) if m else ""
    except OSError:
        return ""


def _publish(kind: Kind, cfg: dict, share_dir: str, *, rows: Optional[list] = None, dev_meta: Optional[list] = None,
             params_store: Optional[dict] = None, log: Optional[Callable[[str], None]] = None,
             now: Optional[dt.datetime] = None) -> Dict[str, object]:
    """`kind` 의 배포판을 만들어 `share_dir` 에 올린다(LOT 추적 · 전체 공통). → `publish_lot` 의 결과와 같은 모양."""
    share_dir = str(share_dir or "").strip()
    if not share_dir:
        raise ValueError(i18n.KO.PUBLISH_NO_DIR)
    if not os.path.isabs(share_dir):
        raise ValueError(i18n.KO.PUBLISH_NOT_ABS_FMT.format(path=share_dir))     # 상대 경로는 엉뚱한 곳에 폴더를 만든다
    roots = nas_guard.roots_for_cfg(cfg)
    nas_guard.assert_local(share_dir, roots)          # ★ 장비 NAS 아래면 여기서 멈춘다
    t0 = time.perf_counter()
    stamp = (now or dt.datetime.now()).strftime("%Y%m%d_%H%M")
    data_dir = os.path.join(share_dir, DATA_DIR)
    if not (os.path.isdir(share_dir) or os.path.isdir(os.path.dirname(share_dir.rstrip('\\/')))):   # 무거운 HTML 을 만들기 전에 — 닿지 못하면 바로 실패(새 하위 폴더는 만들 수 있다)
        raise FileNotFoundError(2, i18n.KO.PUBLISH_DIR_MISSING, share_dir)
    name = f"{kind.prefix}_{stamp}.html"
    n = 0
    while os.path.exists(os.path.join(data_dir, name)):      # 같은 분에 또 올리면 덮어쓰지 않고 번호를 붙인다
        n += 1
        name = f"{kind.prefix}_{stamp}{(now or dt.datetime.now()).strftime('%S')}{'' if n == 1 else '_' + str(n)}.html"
    if kind is FULL:
        full_cfg = dict(cfg, html_days=int(cfg.get("publish_full_days") or 0), write_csv=False)   # 모든 탭 · 최근 N일(0 = 전부) · CSV 는 쓰지 않는다
        if rows is not None:
            path = collect.write_html(full_cfg, rows, dev_meta or [], [], time.time(), mode="publish", log=log,
                                      out_dir=data_dir, out_name=name, params_store=params_store)
        else:
            path = collect.html_from_cache(full_cfg, log=log, out_dir=data_dir, out_name=name)
    elif rows is not None:
        path = collect.write_html(cfg, rows, dev_meta or [], [], time.time(), mode="publish", log=log, lot_only=True,
                                  out_dir=data_dir, out_name=name, params_store={})
    else:
        path = collect.html_from_cache(cfg, log=log, lot_only=True, out_dir=data_dir, out_name=name)
    stub = os.path.join(share_dir, kind.stub)
    ok = _write_text(os.path.join(share_dir, LATEST_NAME), latest_text(name, kind), roots)
    try:
        cur = open(stub, encoding="utf-8").read() if os.path.isfile(stub) else None
    except OSError:
        cur = None
    if cur != stub_text(kind):
        ok = _write_text(stub, stub_text(kind), roots) and ok
    short = os.path.join(share_dir, kind.shortcut)
    try:
        cur_s = open(short, "rb").read() if os.path.isfile(short) else None
    except OSError:
        cur_s = None
    if cur_s != shortcut_bytes(share_dir, kind):
        _write_text(short, shortcut_bytes(share_dir, kind), roots, tries=2)           # 못 써도 배포는 성공 — 바로가기는 이미 있거나 다음에
    size = os.path.getsize(path)
    pruned = _prune(data_dir, KEEP_FILES, roots, protect={name, _pointed_name(share_dir, kind)}, kind=kind)
    res = {"dir": share_dir, "data": path, "bytes": size, "sec": round(time.perf_counter() - t0, 1),
           "pointer_ok": ok, "pruned": pruned}
    if log:
        label = "전체 배포" if kind is FULL else "LOT 추적 배포"
        log(f"{label}: {path} ({res['bytes'] >> 20}MB · {res['sec']}초 · 안내 {'갱신' if ok else '못 바꿈(열려 있음)'} · 정리 {pruned}개)")
    return res


def publish_lot(cfg: dict, share_dir: str, *, rows: Optional[list] = None, dev_meta: Optional[list] = None,
                log: Optional[Callable[[str], None]] = None, now: Optional[dt.datetime] = None) -> Dict[str, object]:
    """LOT 추적 배포판을 만들어 `share_dir` 에 올린다. NAS(장비)는 읽지 않는다 — `rows` · `dev_meta` 를 주면(방금 수집한 것) 그것으로,
    안 주면 가진 데이터(캐시)로 만든다.

    → {"dir", "data", "bytes", "sec", "pointer_ok", "pruned"}. 안내 파일 · latest.js 는 잠겨 있어 못 바꿨으면 pointer_ok False
    (데이터 파일은 이미 올라가 있다 — 다음 수집에서 다시 가리킨다)."""
    return _publish(LOT, cfg, share_dir, rows=rows, dev_meta=dev_meta, log=log, now=now)


def publish_full(cfg: dict, share_dir: str, *, rows: Optional[list] = None, dev_meta: Optional[list] = None,
                 params_store: Optional[dict] = None, log: Optional[Callable[[str], None]] = None,
                 now: Optional[dt.datetime] = None) -> Dict[str, object]:
    """전체 배포판(모든 탭 · 최근 cfg `publish_full_days` 일, 0 = 가진 데이터 전부)을 `share_dir` 에 올린다. 결과 모양은 `publish_lot` 과 같다.
    `params_store` = 방금 수집한 파라미터 묶음(파라미터 탭) — 캐시로 만들 때는 캐시의 것."""
    return _publish(FULL, cfg, share_dir, rows=rows, dev_meta=dev_meta, params_store=params_store, log=log, now=now)


def _run_one(kind: Kind, cfg: dict, share_dir: str, rows: list, dev_meta: list, params_store: Optional[dict],
             log: Optional[Callable[[str], None]], status: Optional[dict], prefix: str) -> Optional[Dict[str, object]]:
    label = "전체 배포" if kind is FULL else "LOT 추적 배포"
    try:
        res = _publish(kind, cfg, share_dir, rows=rows, dev_meta=dev_meta, params_store=params_store, log=log)
    except Exception as exc:  # noqa: BLE001 - 배포는 부가 산출물이다(CSV 와 같은 취급)
        if log:
            log(f"{label} 실패(수집은 정상): {type(exc).__name__}: {exc}")
        if status is not None:
            status.update({prefix + "error": f"{type(exc).__name__}: {exc}", prefix + "dir": share_dir})
        return None
    if status is not None:
        status[prefix + "dir"] = share_dir
        status[prefix + ("ok" if res.get("pointer_ok") else "locked")] = True
    return res


def _enabled(share_dir: str) -> bool:
    return bool(share_dir) and not (os.name != "nt" and share_dir.startswith("\\\\"))     # 꺼짐 · Windows 가 아니면 UNC 에 닿을 수 없다(개발 환경·CI)


def _same_folder(a: str, b: str) -> bool:
    key = lambda p: os.path.normcase(os.path.normpath(str(p).strip().rstrip("\\/")))
    if key(a) == key(b):
        return True
    try:
        return os.path.samefile(a, b)           # 심볼릭 링크 · 다른 이름의 같은 공유는 파일 시스템 정체로 본다(둘 다 이미 있을 때만)
    except OSError:
        return False


def publish_after_collect(cfg: dict, rows: list, dev_meta: list, log: Optional[Callable[[str], None]] = None,
                          status: Optional[dict] = None, params_store: Optional[dict] = None) -> Optional[Dict[str, object]]:
    """수집이 끝난 뒤 조용히 배포 — cfg `publish_dir`(LOT 추적) · `publish_full_dir`(전체)가 비어 있으면 그 배포는 안 한다. 실패해도 수집은 성공으로 두고 로그에 한 줄만 남긴다.
    LOT 추적을 먼저 올리고 전체가 이어진다(둘은 서로 영향이 없다). 돌려주는 값은 LOT 추적 결과(꺼짐 · 실패면 None).

    `status` 를 주면 결과를 거기에 적는다(10/30, 수집 창이 끝에 보여 주려고): 끝까지 올렸으면 `ok`(+`dir`), 안내 파일이 잠겨 못 바꿨으면 `locked`,
    실패하면 `error`(+`dir`). 전체 배포는 같은 이름에 `full_` 을 붙인다(`full_ok` · `full_locked` · `full_error` · `full_dir`). 안 했으면(꺼짐) 비어 있다."""
    share_dir = str(cfg.get("publish_dir") or "").strip()
    full_dir = str(cfg.get("publish_full_dir") or "").strip()
    res = _run_one(LOT, cfg, share_dir, rows, dev_meta, None, log, status, "") if _enabled(share_dir) else None
    if _enabled(full_dir) and share_dir and _same_folder(share_dir, full_dir):     # 같은 폴더면 latest.js 가 겹쳐 서로 덮는다
        if log:
            log(i18n.KO.PUBLISH_FULL_SAME_DIR)
        if status is not None:
            status.update(full_error=i18n.KO.PUBLISH_FULL_SAME_DIR, full_dir=full_dir)
    elif _enabled(full_dir):
        _run_one(FULL, cfg, full_dir, rows, dev_meta, params_store, log, status, "full_")
    return res
