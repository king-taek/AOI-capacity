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

Design rules (from the hand-over document):
  * Never walk Scanresult recursively. The INI path is computed exactly:
        {scan_root}/{equipment}/{process_code}/{lot}/{wafer_id}/WaferInfo.ini
  * Only the needed INI keys are read. Source files are never modified.
  * A report that fails to parse is logged and skipped; the run continues.
"""
import argparse, csv, datetime as dt, hashlib, json, os, re, shutil, sys, time, urllib.request
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(HERE, "version.json")
DEFAULT_CONFIG = {
    "nas_roots": ["X:\\", "M:\\", "V:\\", "P:\\", "Y:\\", "I:\\"],
    "report_dir": "Report",
    "scan_dir": "Scanresult",
    "reports_per_device": 50,
    "retention_days": 90,
    "output_dir": HERE,
    "output_name": "AOI_capacity.html",
    "write_csv": False,
    "cache_file": os.path.join(HERE, "aoi_cache.json"),
    "update": {
        "enabled": True,
        "base_url": "https://raw.githubusercontent.com/king-taek/AOI-capacity/main/",
        "files": ["template.html", "aoi_collect.py", "version.json"]
    }
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


# ----------------------------------------------------------------------------- discovery
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
    devs = discover_devices(cfg)
    log(f"장비 {len(devs)}대 발견: {', '.join(d['name'] for d in devs)}")
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
    ver = read_version()
    meta = {"generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "generated_iso": dt.datetime.now().isoformat(timespec="seconds"),
            "mode": "auto", "devices": dev_meta, "reportErrors": errors, "limit": cfg["reports_per_device"],
            "elapsed": int((time.time() - started) * 1000), "version": ver.get("version", ""), "retention_days": cfg["retention_days"]}
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
def read_version():
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:  # noqa
        return {"version": "0"}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "aoi-capacity", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()


def self_update(cfg):
    """Download newer template/script from GitHub. Returns True if aoi_collect.py itself changed (caller re-executes)."""
    u = cfg.get("update") or {}
    if not u.get("enabled"): return False
    try:
        remote = json.loads(fetch(u["base_url"] + "version.json").decode("utf-8"))
    except Exception as e:  # noqa
        log(f"업데이트 확인 실패(오프라인?): {e}"); return False
    local = read_version()
    if str(remote.get("version")) == str(local.get("version")):
        log(f"최신 버전입니다 (v{local.get('version')})"); return False
    log(f"새 버전 v{remote.get('version')} (현재 v{local.get('version')}) · 다운로드")
    changed_self = False
    for name in u.get("files", []):
        try:
            data = fetch(u["base_url"] + name)
            dest = os.path.join(HERE, name)
            if os.path.isfile(dest) and hashlib.sha256(open(dest, "rb").read()).hexdigest() == hashlib.sha256(data).hexdigest():
                continue
            if os.path.isfile(dest): shutil.copy2(dest, dest + ".bak")
            with open(dest, "wb") as f: f.write(data)
            log(f"  갱신: {name}")
            if name == os.path.basename(__file__): changed_self = True
        except Exception as e:  # noqa
            log(f"  {name} 다운로드 실패: {e}")
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
