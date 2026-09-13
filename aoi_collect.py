#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AOI Capacity collector
======================
Reads Camtek AOI BatchReport (.htm) files and each wafer's WaferInfo.ini from the NAS shares,
keeps an incremental cache, and writes ONE self-contained HTML dashboard (template.html + data).

Standard library only. Windows / Python 3.8+.

    python aoi_collect.py                 # incremental run using config.json next to this file
    python aoi_collect.py --config X.json
    python aoi_collect.py --full          # ignore cache, re-read the latest N reports per device
    python aoi_collect.py --no-update     # skip the GitHub self-update check

Device list: devices.csv next to this file (columns 장비명, NAS경로, 폴더, 사용, 메모).
  폴더 = device folder under the NAS root; empty = the root itself is the device; "*" = auto-discover
  every sub-folder that contains a Report folder. Excel's cp949 CSV and UTF-8 are both accepted.

Design rules (from the hand-over document):
  * Never walk Scanresult recursively. The INI path is computed exactly:
        {scan_root}/{equipment}/{process_code}/{lot}/{wafer_id}/WaferInfo.ini
  * Only the needed INI keys are read. Source files are never modified.
  * A report that fails to parse is logged and skipped; the run continues.
  * Self-update: compares the GitHub branch head SHA with the local VERSION file,
    downloads the branch zip, verifies, swaps files (with .bak rollback), re-executes.
"""
import argparse, csv, datetime as dt, hashlib, json, os, re, shutil, sys, time, urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(HERE, "VERSION")
DEFAULT_CONFIG = {
    "devices_csv": os.path.join(HERE, "devices.csv"),
    "nas_roots": [],
    "report_dir": "Report",
    "scan_dir": "Scanresult",
    "reports_per_device": 50,
    "retention_days": 90,
    "output_dir": HERE,
    "output_name": "AOI_capacity.html",
    "write_csv": False,
    "cache_file": os.path.join(HERE, "aoi_cache.json"),
    "update": {"enabled": True, "repo": "king-taek/AOI-capacity", "branch": ""}
}
INI_KEYS = {
    "Recipe": ["Name"],
    "AutoCycleInfo": ["Machine", "Operator", "WaferStartTime", "WaferEndTime", "BatchStartTime", "OCRID",
                      "ActiveStation", "ActiveSlot", "FillID", "CarrierID", "UseLot", "UseWaferID"],
    "BatchInfo": ["GlobalLotId", "OperatorId"],
}
OUT_COLS = ["device", "lot", "wafer_id", "status", "norm_status", "recipe",
            "wafer_start_time", "wafer_end_time", "batch_start", "ini_match", "data_issue"]
REPORT_RE = re.compile(r"^(.+?)_(\d{4})_(.+)_(\d{1,2}-[A-Za-z]{3}-\d{2})_\((\d{2}\.\d{2}\.\d{2})\)_BatchReport\.html?$", re.I)
DT_FORMATS = ["%d-%b-%y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%d-%b-%y %H:%M:%S"]


def log(msg):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


# ----------------------------------------------------------------------------- helpers
def parse_dt(s):
    s = (s or "").strip()
    for f in DT_FORMATS:
        try:
            return dt.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def norm_status(s):
    t = (s or "").strip().lower()
    if t == "pass": return "PASS"
    if "skip" in t: return "SKIPPED"
    if "failed to read wafer id" in t: return "ID_READ_ERROR"
    if "scan error" in t: return "SCAN_ERROR"
    if "wafer aborted by user" in t: return "USER_ABORT"
    if "abort" in t: return "ABORTED"
    return "OTHER" if t else ""


class TableParser(HTMLParser):
    """Collects every <table> as a list of rows, each row a list of cell texts (nested tables flattened)."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._t, self._r, self._c = [], None, None, None
    def handle_starttag(self, tag, attrs):
        if tag == "table": self._t = []
        elif tag == "tr" and self._t is not None: self._r = []
        elif tag in ("td", "th") and self._r is not None: self._c = []
    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._c is not None and self._r is not None:
            self._r.append(re.sub(r"\s+", " ", "".join(self._c)).strip()); self._c = None
        elif tag == "tr" and self._r is not None and self._t is not None:
            self._t.append(self._r); self._r = None
        elif tag == "table" and self._t is not None:
            self.tables.append(self._t); self._t = None
    def handle_data(self, data):
        if self._c is not None: self._c.append(data)


def parse_report(name, text):
    m = REPORT_RE.match(name)
    rep = {"equipment": m.group(1) if m else "", "process_code": m.group(2) if m else "",
           "report_lot": m.group(3) if m else "", "summary": {}, "wafers": []}
    p = TableParser(); p.feed(text)
    for tb in p.tables:
        if not tb: continue
        head = [h.lower() for h in tb[0]]
        iw = next((i for i, h in enumerate(head) if re.fullmatch(r"wafer\s*id", h)), -1)
        il = next((i for i, h in enumerate(head) if h == "lot"), -1)
        if iw >= 0 and il >= 0:
            def idx(k): return next((i for i, h in enumerate(head) if h.startswith(k)), -1)
            ix = {"status": idx("pass"), "recipe": idx("recipe")}
            for row in tb[1:]:
                if len(row) <= iw: continue
                g = lambda i: row[i] if 0 <= i < len(row) else ""
                rep["wafers"].append({"lot": row[il], "wafer_id": row[iw], "status": g(ix["status"]), "recipe": g(ix["recipe"])})
        else:
            for row in tb:
                for i in range(0, len(row) - 1, 2):
                    k = re.sub(r"[:\s]+$", "", row[i])
                    if k and k not in rep["summary"]: rep["summary"][k] = row[i + 1]
    return rep


def read_ini(path):
    out, sec = {}, ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in ";#": continue
            if line[0] == "[" and line.endswith("]"):
                sec = line[1:-1]; out.setdefault(sec, {}); continue
            if "=" not in line: continue
            k, v = line.split("=", 1)
            k = k.strip()
            if sec in INI_KEYS and k in INI_KEYS[sec]: out[sec][k] = v.strip()
    return out


def rows_for_report(dev_name, rep, scan_root):
    rows = []
    s = rep["summary"]
    for w in rep["wafers"]:
        r = {"device": dev_name, "lot": w["lot"], "wafer_id": w["wafer_id"], "status": w["status"],
             "norm_status": norm_status(w["status"]), "recipe": w["recipe"] or s.get("Recipe", ""),
             "wafer_start_time": "", "wafer_end_time": "", "batch_start": s.get("Batch Start", ""),
             "ini_match": "", "data_issue": ""}
        if re.match(r"^loadport", w["lot"], re.I) or re.match(r"^slot\s*\d+", w["wafer_id"], re.I) or not w["wafer_id"]:
            r["ini_match"], r["data_issue"] = "NO_WAFER_ID", "LoadPort/Slot 행이라 INI 경로를 만들 수 없음"
        else:
            ini_path = os.path.join(scan_root, rep["equipment"], rep["process_code"], w["lot"], w["wafer_id"], "WaferInfo.ini")
            if not os.path.isfile(ini_path):
                r["ini_match"], r["data_issue"] = "NOT_FOUND", "예상 경로에 WaferInfo.ini 없음"
            else:
                try:
                    ini = read_ini(ini_path); a = ini.get("AutoCycleInfo", {})
                    r["ini_match"] = "EXACT"
                    r["wafer_start_time"], r["wafer_end_time"] = a.get("WaferStartTime", ""), a.get("WaferEndTime", "")
                    iss = []
                    st, en = parse_dt(r["wafer_start_time"]), parse_dt(r["wafer_end_time"])
                    if not (st and en and en >= st): iss.append("Wafer 시작/종료 시각 누락 또는 역전")
                    if a.get("UseLot") and a["UseLot"] != w["lot"]: iss.append("Lot 불일치")
                    if a.get("UseWaferID") and a["UseWaferID"] != w["wafer_id"]: iss.append("Wafer ID 불일치")
                    r["data_issue"] = "; ".join(iss)
                except Exception as e:  # noqa
                    r["ini_match"], r["data_issue"] = "READ_ERROR", f"{type(e).__name__}: {e}"
        rows.append(r)
    return rows


# ----------------------------------------------------------------------------- device list (CSV)
CSV_ALIASES = {"name": ["장비명", "장비", "name", "device"], "root": ["nas경로", "nas", "경로", "root", "path"],
               "sub": ["폴더", "장비폴더", "folder", "sub"], "on": ["사용", "enabled", "use", "on"], "memo": ["메모", "memo", "note"]}


def read_devices_csv(path):
    """Read the device list CSV (UTF-8 with/without BOM, or cp949 from Korean Excel). Returns list of dicts."""
    raw = open(path, "rb").read()
    text = None
    for enc in ("utf-8-sig", "cp949", "euc-kr"):
        try: text = raw.decode(enc); break
        except UnicodeDecodeError: continue
    if text is None: text = raw.decode("utf-8", "replace")
    rows = list(csv.reader([l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]))
    if not rows: return []
    head = [h.strip().lower() for h in rows[0]]
    def col(key):
        for a in CSV_ALIASES[key]:
            if a in head: return head.index(a)
        return -1
    ix = {k: col(k) for k in CSV_ALIASES}
    if ix["root"] < 0:  # no header: assume 장비명, NAS경로, 폴더, 사용, 메모
        ix = {"name": 0, "root": 1, "sub": 2, "on": 3, "memo": 4}; body = rows
    else: body = rows[1:]
    out = []
    for r in body:
        g = lambda k: r[ix[k]].strip() if 0 <= ix[k] < len(r) else ""
        if not g("root"): continue
        on = g("on").upper() not in ("N", "NO", "0", "FALSE", "X", "아니오")
        out.append({"name": g("name"), "root": g("root"), "sub": g("sub"), "on": on, "memo": g("memo")})
    return out


def devices_from_csv(cfg):
    """Resolve CSV rows to device folders. Unreachable entries are logged and skipped."""
    devs = []
    for row in read_devices_csv(cfg["devices_csv"]):
        if not row["on"]: continue
        root = row["root"]
        root = root.rstrip("\\/") + os.sep if re.fullmatch(r"[A-Za-z]:\\?", root) else root
        sub = row["sub"]
        if sub in ("*", "auto", "AUTO"):
            found = _discover_under(root, cfg)
            if not found: log(f"[건너뜀] {row['name'] or root}: NAS 접근 불가 또는 장비 폴더 없음 ({root})")
            devs.extend(found); continue
        path = os.path.join(root, sub) if sub else root
        if not os.path.isdir(os.path.join(path, cfg["report_dir"])):
            log(f"[건너뜀] {row['name'] or sub or root}: Report 폴더 없음/접근 불가 ({path})"); continue
        devs.append({"name": row["name"] or sub or os.path.basename(path.rstrip("\\/")) or path, "path": path})
    return _dedupe_sort(devs)


def _discover_under(root, cfg):
    if not os.path.isdir(root): return []
    if os.path.isdir(os.path.join(root, cfg["report_dir"])):
        return [{"name": os.path.basename(root.rstrip("\\/")) or root, "path": root}]
    out = []
    try:
        for e in os.scandir(root):
            if e.is_dir() and os.path.isdir(os.path.join(e.path, cfg["report_dir"])): out.append({"name": e.name, "path": e.path})
    except OSError as ex:
        log(f"[건너뜀] {root}: {ex}")
    return out


def _dedupe_sort(devs):
    seen, uniq = set(), []  # same folder listed twice (explicit row + "*" row): the first row wins
    for d in devs:
        key = os.path.normcase(os.path.normpath(d["path"]))
        if key in seen: continue
        seen.add(key); uniq.append(d)
    devs = uniq
    names = {}
    for d in devs: names[d["name"]] = names.get(d["name"], 0) + 1
    for d in devs:  # duplicate names across shares: prefix with the share (drive letter or host)
        if names[d["name"]] > 1:
            share = d["path"].split(os.sep)[0] or d["path"][:2]
            d["name"] = f"{share} {d['name']}"
    devs.sort(key=lambda d: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", d["name"])])
    return devs


# ----------------------------------------------------------------------------- discovery (fallback when no CSV)
def discover_devices(cfg):
    """Each NAS root either IS a device folder (has Report/) or CONTAINS device folders. One listing per root, no recursion."""
    devs, names = [], {}
    for root in cfg["nas_roots"]:
        root = root.rstrip("\\/") + os.sep if re.fullmatch(r"[A-Za-z]:\\?", root) else root
        if not os.path.isdir(root):
            log(f"[건너뜀] NAS 접근 불가: {root}"); continue
        if os.path.isdir(os.path.join(root, cfg["report_dir"])):
            devs.append({"name": os.path.basename(root.rstrip("\\/")) or root, "path": root}); continue
        try:
            for e in os.scandir(root):
                if e.is_dir() and os.path.isdir(os.path.join(e.path, cfg["report_dir"])):
                    devs.append({"name": e.name, "path": e.path})
        except OSError as ex:
            log(f"[건너뜀] {root}: {ex}")
    for d in devs: names[d["name"]] = names.get(d["name"], 0) + 1
    for d in devs:  # disambiguate duplicate folder names across shares with the share's drive/host
        if names[d["name"]] > 1:
            share = d["path"].split(os.sep)[0] or d["path"][:2]
            d["name"] = f"{share} {d['name']}"
    devs.sort(key=lambda d: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", d["name"])])
    return devs


# ----------------------------------------------------------------------------- collect
def collect(cfg, full=False):
    cache = {"reports": {}}
    if not full and os.path.isfile(cfg["cache_file"]):
        try:
            with open(cfg["cache_file"], "r", encoding="utf-8") as f: cache = json.load(f)
        except Exception as e:  # noqa
            log(f"캐시 읽기 실패, 새로 시작: {e}")
    if os.path.isfile(cfg.get("devices_csv") or ""):
        devs = devices_from_csv(cfg); log(f"devices.csv 기준 장비 {len(devs)}대: {', '.join(d['name'] for d in devs)}")
    else:
        log(f"devices.csv 가 없어 nas_roots 를 자동 탐색합니다 ({cfg.get('devices_csv')})")
        devs = discover_devices(cfg); log(f"장비 {len(devs)}대 발견: {', '.join(d['name'] for d in devs)}")
    reports, dev_meta, errors, n_new = cache["reports"], [], [], 0
    for d in devs:
        dm = {"name": d["name"], "note": d["path"], "reports": 0, "found": 0, "error": ""}
        rep_dir, scan_root = os.path.join(d["path"], cfg["report_dir"]), os.path.join(d["path"], cfg["scan_dir"])
        try:
            files = [e for e in os.scandir(rep_dir) if e.is_file() and e.name.lower().endswith((".htm", ".html"))]
            files.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            pick = files[: cfg["reports_per_device"]]
            dm["found"], dm["reports"] = len(files), len(pick)
            for e in pick:
                key, mtime = e.path, e.stat().st_mtime
                if key in reports and abs(reports[key]["mtime"] - mtime) < 1 and reports[key].get("device") == d["name"]:
                    continue
                try:
                    with open(e.path, "r", encoding="utf-8", errors="replace") as f: text = f.read()
                    rep = parse_report(e.name, text)
                    reports[key] = {"mtime": mtime, "device": d["name"], "rows": rows_for_report(d["name"], rep, scan_root),
                                    "seen": time.time()}
                    n_new += 1
                except Exception as ex:  # noqa
                    errors.append({"device": d["name"], "path": e.path, "error": f"{type(ex).__name__}: {ex}"})
        except OSError as ex:
            dm["error"] = f"{type(ex).__name__}: {ex}"; log(f"[{d['name']}] {dm['error']}")
        dev_meta.append(dm)
    # retention: drop cached reports whose newest wafer/batch time is older than retention_days
    cutoff = dt.datetime.now() - dt.timedelta(days=cfg["retention_days"])
    def newest(entry):
        ts = [parse_dt(r.get("wafer_end_time") or r.get("batch_start")) for r in entry["rows"]]
        ts = [t for t in ts if t]
        return max(ts) if ts else dt.datetime.fromtimestamp(entry.get("seen", 0))
    for k in [k for k, v in reports.items() if newest(v) < cutoff]: del reports[k]
    cache["reports"] = reports
    os.makedirs(os.path.dirname(os.path.abspath(cfg["cache_file"])), exist_ok=True)
    with open(cfg["cache_file"], "w", encoding="utf-8") as f: json.dump(cache, f, ensure_ascii=False)
    rows = [r for v in reports.values() for r in v["rows"]]
    log(f"새로 읽은 Report {n_new}개 · 캐시 Report {len(reports)}개 · Wafer 행 {len(rows)} · 오류 {len(errors)}건")
    return rows, dev_meta, errors


# ----------------------------------------------------------------------------- output
def write_html(cfg, rows, dev_meta, errors, started):
    tpl_path = os.path.join(HERE, "template.html")
    with open(tpl_path, "r", encoding="utf-8") as f: tpl = f.read()
    ver = read_version(); u = cfg.get("update") or {}
    meta = {"generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "generated_iso": dt.datetime.now().isoformat(timespec="seconds"),
            "mode": "auto", "devices": dev_meta, "reportErrors": errors, "limit": cfg["reports_per_device"],
            "elapsed": int((time.time() - started) * 1000), "retention_days": cfg["retention_days"],
            "sha": ver.get("sha", ""), "branch": ver.get("branch", ""), "repo": ver.get("repo") or u.get("repo") or "king-taek/AOI-capacity",
            "version": (ver.get("sha", "")[:7] + (" · " + ver["applied"][:10] if ver.get("applied") else "")) if ver.get("sha") else ""}
    emb = {"cols": OUT_COLS, "rows": [[r.get(c, "") for c in OUT_COLS] for r in rows], "meta": meta}
    data = json.dumps(emb, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    out = tpl.replace("__DATA__", data, 1)
    os.makedirs(cfg["output_dir"], exist_ok=True)
    target = os.path.join(cfg["output_dir"], cfg["output_name"])
    tmp = target + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(out)
    os.replace(tmp, target)  # atomic swap so viewers never see a half-written file
    log(f"HTML 저장: {target} ({len(out)//1024} KB)")
    if cfg.get("write_csv"):
        csv_path = os.path.splitext(target)[0] + ".csv"
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=OUT_COLS); w.writeheader(); w.writerows(rows)
        log(f"CSV 저장: {csv_path}")


# ----------------------------------------------------------------------------- self update
# Pattern borrowed from king-taek/coding (app/utils/updater.py):
#  * the reference is the latest commit SHA of the repo branch (no manual version bump);
#  * api.github.com first, github.com Atom feed as fallback when the API host is blocked;
#  * HTTPS goes through the system proxy; on certificate failure (corporate SSL inspection)
#    retry once without verification;
#  * download the branch zip, stage a verified tree, then swap files with .bak rollback;
#  * a git checkout (developer run) never self-updates.
UPDATE_FILES = ["aoi_collect.py", "template.html", "run_collect.bat", "config.example.json", "devices.example.csv", "README.md"]
_last_error = ""


def _ssl_ctx(insecure=False):
    import ssl
    if insecure:
        c = ssl.create_default_context(); c.check_hostname = False; c.verify_mode = ssl.CERT_NONE; return c
    try:
        import truststore  # optional: use the Windows trust store like a browser
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:  # noqa
        c = ssl.create_default_context()
        try: c.load_default_certs()
        except Exception: pass  # noqa
        return c


def fetch(url, timeout=20):
    """GET bytes via system proxy; retry without certificate verification on SSL errors."""
    import ssl
    headers = {"User-Agent": "aoi-capacity-updater", "Accept": "application/vnd.github+json", "Cache-Control": "no-cache"}
    for insecure in (False, True):
        try:
            handlers = [urllib.request.ProxyHandler(urllib.request.getproxies()), urllib.request.HTTPSHandler(context=_ssl_ctx(insecure))]
            opener = urllib.request.build_opener(*handlers)
            with opener.open(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa
            reason = getattr(e, "reason", e)
            if not insecure and (isinstance(e, ssl.SSLError) or isinstance(reason, ssl.SSLError)):
                log("  인증서 검증 실패 → 검증 없이 재시도 (회사 SSL 검사 프록시)"); continue
            raise


def read_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:  # noqa
        return {}


def write_version(sha, branch, repo, message=""):
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        json.dump({"sha": sha, "branch": branch, "repo": repo, "message": message, "applied": dt.datetime.now().isoformat(timespec="seconds")}, f, ensure_ascii=False)


def default_branch(repo):
    try:
        return json.loads(fetch(f"https://api.github.com/repos/{repo}").decode("utf-8")).get("default_branch") or "main"
    except Exception:  # noqa
        return "main"


def latest_commit(repo, branch):
    """{'sha','message','date'} of the branch head; API first, Atom feed fallback."""
    global _last_error
    try:
        d = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/{branch}").decode("utf-8"))
        msg = ((d.get("commit") or {}).get("message") or "").splitlines()
        return {"sha": d["sha"], "message": msg[0] if msg else "", "date": ((d.get("commit") or {}).get("committer") or {}).get("date", "")}
    except Exception as e:  # noqa
        _last_error = f"api.github.com: {e}"
    try:
        txt = fetch(f"https://github.com/{repo}/commits/{branch}.atom").decode("utf-8", "replace")
        m = re.search(r"commit/([0-9a-fA-F]{40})", txt)
        if m: return {"sha": m.group(1).lower(), "message": "", "date": ""}
        _last_error = "github.com atom: SHA 없음"
    except Exception as e:  # noqa
        _last_error = f"github.com: {e}"
    return None


def self_update(cfg):
    """Returns True when aoi_collect.py itself was replaced (caller re-executes)."""
    u = cfg.get("update") or {}
    if not u.get("enabled"): return False
    if os.path.isdir(os.path.join(HERE, ".git")):
        log("git 작업 폴더에서 실행 중 · 자동 업데이트 생략 (git pull 사용)"); return False
    repo = u.get("repo") or "king-taek/AOI-capacity"
    cur = read_version()
    branch = (u.get("branch") or cur.get("branch") or "").strip() or default_branch(repo)
    latest = latest_commit(repo, branch)
    if not latest:  # tracked branch deleted/renamed (e.g. a merged claude/* branch) -> follow the repo default branch
        db = default_branch(repo)
        if db != branch:
            log(f"브랜치 {branch} 조회 실패 → 기본 브랜치 {db}로 전환"); branch = db; latest = latest_commit(repo, branch)
    if not latest:
        log(f"업데이트 확인 실패(오프라인/차단?): {_last_error}"); return False
    if cur.get("sha") == latest["sha"]:
        log(f"최신 버전 ({branch} @ {latest['sha'][:7]})"); return False
    log(f"새 버전 {branch} @ {latest['sha'][:7]} {latest.get('message','')!r} (현재 {str(cur.get('sha',''))[:7] or '미상'}) · 다운로드")
    import zipfile, io as _io, py_compile
    try:
        blob = fetch(f"https://github.com/{repo}/archive/{latest['sha']}.zip", timeout=60)
        zf = zipfile.ZipFile(_io.BytesIO(blob))
    except Exception as e:  # noqa
        log(f"  zip 다운로드 실패: {e}"); return False
    staging = os.path.join(HERE, ".update.part")
    shutil.rmtree(staging, ignore_errors=True); os.makedirs(staging)
    got = {}
    for name in zf.namelist():
        rel = name.split("/", 1)[1] if "/" in name else name
        if rel in UPDATE_FILES:
            data = zf.read(name)
            with open(os.path.join(staging, rel), "wb") as f: f.write(data)
            got[rel] = data
    # verify the staged tree before touching anything
    try:
        if "template.html" in got and b"__DATA__" not in got["template.html"]: raise ValueError("template.html에 __DATA__ 자리가 없음")
        if "aoi_collect.py" in got: py_compile.compile(os.path.join(staging, "aoi_collect.py"), doraise=True)
        if "aoi_collect.py" not in got or "template.html" not in got: raise ValueError("필수 파일 누락")
    except Exception as e:  # noqa
        log(f"  검증 실패, 적용하지 않음: {e}"); shutil.rmtree(staging, ignore_errors=True); return False
    changed_self, swapped = False, []
    try:
        for rel, data in got.items():
            dest = os.path.join(HERE, rel)
            if os.path.isfile(dest) and hashlib.sha256(open(dest, "rb").read()).digest() == hashlib.sha256(data).digest(): continue
            if os.path.isfile(dest): shutil.copy2(dest, dest + ".bak")
            os.replace(os.path.join(staging, rel), dest); swapped.append(rel)
            log(f"  갱신: {rel}")
            if rel == os.path.basename(__file__): changed_self = True
    except Exception as e:  # noqa
        log(f"  적용 실패, 롤백: {e}")
        for rel in swapped:
            bak = os.path.join(HERE, rel) + ".bak"
            if os.path.isfile(bak): os.replace(bak, os.path.join(HERE, rel))
        shutil.rmtree(staging, ignore_errors=True); return False
    shutil.rmtree(staging, ignore_errors=True)
    write_version(latest["sha"], branch, repo, latest.get("message", ""))
    return changed_self


# ----------------------------------------------------------------------------- main
def load_config(path):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict): cfg[k].update(v)
            else: cfg[k] = v
    else:
        log(f"설정 파일이 없어 기본값을 씁니다. 예시: {os.path.join(HERE, 'config.example.json')}")
    return cfg


def main():
    ap = argparse.ArgumentParser(description="AOI Capacity collector")
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"))
    ap.add_argument("--full", action="store_true", help="캐시를 무시하고 최신 N개 Report를 다시 읽음")
    ap.add_argument("--no-update", action="store_true", help="GitHub 자동 업데이트 확인 생략")
    args = ap.parse_args()
    started = time.time()
    cfg = load_config(args.config)
    if not args.no_update and self_update(cfg):
        log("스크립트가 갱신되어 다시 실행합니다.")
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:] + ["--no-update"])
    rows, dev_meta, errors = collect(cfg, full=args.full)
    write_html(cfg, rows, dev_meta, errors, started)
    log(f"완료 · {time.time() - started:.1f}초")


if __name__ == "__main__":
    main()
