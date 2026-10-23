"""공유 폴더 시험 — LOT 추적 HTML 을 회사 공유 폴더에 올려 팀원이 열어 보게 할 수 있는지 미리 잰다.

무엇을 재는가(내 PC 에서 이 도구를 돌리면 1~5 를 자동으로, 6 은 팀원이 시험 페이지를 열어서)
  1. 공유 폴더가 장비 NAS 와 **다른 공유**인가 — 같은 공유면 아무것도 쓰지 않고 멈춘다(앱의 'NAS 는 읽기만' 규칙).
  2. 쓰기 권한 · 남은 용량 · 왕복 지연(stat 20번).
  3. 10 / 30 / 60MB 파일을 '임시 파일에 다 쓰고 이름을 한 번에 바꾸는' 방식(실제 발행과 같은 방식)으로 쓸 때 걸리는 시간.
  4. 누군가 파일을 열고 있을 때 이름 바꾸기가 되는가(Windows 만 — 삭제 공유를 주지 않은 핸들 / 준 핸들).
  5. 팀원이 열 시험 페이지를 공유 폴더 안 `_aoi_share_probe` 폴더에 만든다(가짜 데이터 — 회사 데이터는 담지 않는다).
  6. 팀원: `시험_안내.html` 을 열고 '시험 시작' → 열기 시간 · gzip 풀기 · 브라우저 종류 · 장비 폴더 링크 · 쓰기 권한을 확인하고
     '결과 복사' 로 보내 준다. `--hammer` 를 돌리는 동안 '교체 중 열기' 를 누르면 교체 도중에 깨진 파일이 열리는지 본다.

★ 쓰기는 `<공유 폴더>\\_aoi_share_probe\\` 안과 내 PC 의 결과 폴더뿐이다. 장비 NAS 에는 어떤 파일도 만들지 않는다.
★ 표준 라이브러리만 쓴다 — 앱을 import 하지 않는다. 결과 HTML 은 바깥으로 요청을 보내지 않는다.

    python share_probe.py                       # 아래 TARGET 으로 1~5
    python share_probe.py --target "\\\\server\\share\\folder"
    python share_probe.py --hammer 300          # 300초 동안 15초마다 시험_교체.html 을 바꿔 쓴다(팀원이 그동안 열어 본다)
    python share_probe.py --clean               # 이 도구가 만든 시험 파일 지우기
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import json
import os
import platform
import random
import re
import shutil
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
#  시험할 공유 폴더 — 바뀌면 여기만 고치거나 --target 으로 준다.
TARGET = r"\\k5cifsn2\k5tsvdata$\1. Conder Scan\0. 전산 X\임현택"
# ══════════════════════════════════════════════════════════════════════════════

TOOL_API = 1
PROBE_DIR = "_aoi_share_probe"
MARKER = "_aoi_share_probe.json"
SIZES_MB = (10, 30, 60)
GZ_RAW_MB = 44            # 실데이터(8/16~10/23) LOT 추적 열만 남긴 크기 — gzip 시험 페이지의 원본 크기
HAMMER_FILE = "시험_교체.html"
HAMMER_MB = 10
HAMMER_EVERY = 15
FREE_NEED_MB = 200
REPLACE_TRIES = 10        # 이름 바꾸기 재시도(잠겨 있을 때)
REPLACE_WAIT = 0.5


class Refused(RuntimeError):
    """장비 NAS 와 같은 공유라서 쓰지 않는다."""


# ── 경로 · 공유 판정 ─────────────────────────────────────────────────
def _norm(p: str) -> str:
    p = str(p or "").strip().replace("/", "\\")
    unc = p.startswith("\\\\")
    body = re.sub(r"\\+", "\\\\", p.lstrip("\\")).rstrip("\\")
    return (("\\\\" + body) if unc else body).lower()


def _under(path: str, root: str) -> bool:
    p, r = _norm(path), _norm(root)
    if not r:
        return False
    if re.fullmatch(r"[a-z]:", r):
        r += "\\"
    return p == r.rstrip("\\") or p.startswith(r if r.endswith("\\") else r + "\\")


def unc_of(path: str, resolver=None) -> str:
    """드라이브 문자 경로를 같은 위치의 UNC 로(네트워크 드라이브가 아니거나 모르면 그대로)."""
    m = re.match(r"^([A-Za-z]):", path or "")
    if not m:
        return path
    unc = (resolver or _wnet)(m.group(1).upper() + ":")
    return (unc.rstrip("\\") + path[2:]) if unc else path


def _wnet(drive: str):
    if os.name != "nt":
        return None
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.c_ulong(1024)
        if ctypes.windll.mpr.WNetGetConnectionW(drive, buf, ctypes.byref(n)) == 0:
            return buf.value
    except Exception:
        pass
    return None


def share_of(path: str):
    """UNC 경로의 (호스트, 공유) — 소문자. UNC 가 아니면 None."""
    m = re.match(r"^\\\\([^\\]+)\\([^\\]+)", (path or "").replace("/", "\\"))
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def host_ids(host: str, resolve=None) -> set:
    """호스트 이름과 그 IPv4 들 — 이름(k5cifsn2)과 IP(10.x) 로 적힌 같은 서버를 같게 본다. 이름 풀이 실패는 이름만."""
    ids = {host.lower()}
    try:
        name, aliases, ips = (resolve or socket.gethostbyname_ex)(host)
        names = [x.lower() for x in [name, *aliases] if x and not re.fullmatch(r"[\d.]+", x)]
        ids.update(names)
        ids.update(x.split(".")[0] for x in names)   # k5cifsn2.corp.local ↔ k5cifsn2
        ids.update(ips)
    except Exception:
        pass
    return ids


def read_devices(csv_path: Path):
    """devices.csv → [(이름, 장비 폴더 경로, 사용, 폴더 칸)] — 앱과 같은 열 이름(장비명, NAS경로, 폴더, 사용)."""
    raw = csv_path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    lines = [l for l in (text or raw.decode("utf-8", "replace")).splitlines() if l.strip() and not l.lstrip().startswith("#")]
    rows = list(csv.reader(lines))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    has_head = any(h in head for h in ("nas경로", "root", "path"))
    ix = lambda names, d: next((head.index(n) for n in names if n in head), d)
    i_name, i_root, i_sub, i_on = (ix(("장비명", "name"), 0), ix(("nas경로", "root", "path"), 1),
                                   ix(("폴더", "sub", "folder"), 2), ix(("사용", "on", "use"), 3))
    out = []
    for r in rows[1:] if has_head else rows:
        get = lambda i: r[i].strip() if 0 <= i < len(r) else ""
        root, sub = get(i_root), get(i_sub)
        if not root:
            continue
        full = root.rstrip("\\/") + ("\\" + sub if sub and sub != "*" else "\\")
        out.append((get(i_name), full, get(i_on).upper() not in ("N", "0", "FALSE"), sub))
    return out


def check_target(target: str, roots, resolver=None, resolve=None) -> dict:
    """공유 폴더가 장비 NAS 아래이거나 같은 공유면 Refused. 같은 서버의 다른 공유면 알림만."""
    t_unc = unc_of(target, resolver)
    t_share = share_of(t_unc)
    info = {"target": target, "target_unc": t_unc, "same_server": [], "checked_roots": 0}
    t_ids = host_ids(t_share[0], resolve) if t_share else set()
    for name, root in roots:
        info["checked_roots"] += 1
        r_unc = unc_of(root, resolver)
        for a in (target, t_unc):
            for b in (root, r_unc, root[:2] + "\\" if re.match(r"^[A-Za-z]:", root) else ""):
                if b and _under(a, b):
                    raise Refused(f"공유 폴더가 장비 NAS({name} {root}) 아래입니다 — 쓰지 않습니다: {target}")
        r_share = share_of(r_unc)
        if t_share and r_share:
            same_host = r_share[0] == t_share[0] or bool(t_ids & host_ids(r_share[0], resolve))
            if same_host and r_share[1] == t_share[1]:
                raise Refused(f"공유 폴더가 장비 NAS({name} {r_unc})와 같은 공유입니다 — 쓰지 않습니다: {t_unc}")
            if same_host:
                info["same_server"].append(name)
    return info


# ── 쓰기(시험 폴더 안만) ─────────────────────────────────────────────
class Probe:
    """시험 폴더 하나 — 만든 파일 이름을 표식 파일에 적어 두고 --clean 은 그 이름만 지운다."""

    def __init__(self, target: str):
        self.dir = os.path.join(target, PROBE_DIR)
        self.made = set()

    def _inside(self, name: str) -> str:
        p = os.path.join(self.dir, name)
        if os.path.dirname(os.path.abspath(p)) != os.path.abspath(self.dir):
            raise ValueError(name)
        return p

    def open(self):
        os.makedirs(self.dir, exist_ok=True)
        mk = os.path.join(self.dir, MARKER)
        if os.path.isfile(mk):
            try:
                self.made = set(json.loads(Path(mk).read_text(encoding="utf-8")).get("files", []))
            except (OSError, ValueError):
                pass
        self._save_marker()

    def _save_marker(self):
        Path(self.dir, MARKER).write_text(json.dumps({"tool": "share_probe", "api": TOOL_API, "files": sorted(self.made)},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")

    def publish(self, name: str, data: bytes) -> dict:
        """임시 파일에 다 쓰고(fsync) 이름을 한 번에 바꾼다 — 실제 발행과 같은 방식. 잠겨 있으면 잠깐씩 다시."""
        dst = self._inside(name)
        tmp = self._inside(f"{name}.tmp-{os.getpid()}")
        self.made.update({name})
        self._save_marker()
        t0 = time.perf_counter()
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        t1 = time.perf_counter()
        errs = []
        for i in range(REPLACE_TRIES):
            try:
                os.replace(tmp, dst)
                break
            except OSError as e:
                errs.append(f"{type(e).__name__}: {e}")
                time.sleep(REPLACE_WAIT)
        else:
            try:
                os.remove(tmp)
            except OSError:
                pass
        t2 = time.perf_counter()
        return {"name": name, "mb": round(len(data) / 1e6, 1), "write_s": round(t1 - t0, 2), "replace_s": round(t2 - t1, 3),
                "replace_ok": len(errs) < REPLACE_TRIES, "replace_errors": errs[:3], "retries": len(errs)}

    def read_back(self, name: str) -> dict:
        t0 = time.perf_counter()
        n = len(Path(self._inside(name)).read_bytes())
        return {"name": name, "read_s": round(time.perf_counter() - t0, 2), "mb": round(n / 1e6, 1)}

    def clean(self) -> list:
        gone = []
        mk = os.path.join(self.dir, MARKER)
        if not os.path.isfile(mk):
            return gone
        files = json.loads(Path(mk).read_text(encoding="utf-8")).get("files", [])
        for name in files:
            for p in [self._inside(name)] + [os.path.join(self.dir, x) for x in os.listdir(self.dir)
                                             if x.startswith(name + ".tmp-")]:
                if os.path.isfile(p):
                    os.remove(p)
                    gone.append(os.path.basename(p))
        os.remove(mk)
        try:
            os.rmdir(self.dir)          # 남이 넣은 파일이 있으면 폴더는 그대로 둔다
        except OSError:
            pass
        return gone


def hold_test(probe: Probe) -> dict:
    """Windows: 누가 파일을 열고 있을 때 이름 바꾸기가 되는가 — 삭제 공유 없음(대부분 프로그램) / 있음."""
    if os.name != "nt":
        return {"skipped": "Windows 에서만"}
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    GENERIC_READ, OPEN_EXISTING = 0x80000000, 3
    R, W, D = 1, 2, 4
    name = "시험_잠금.html"
    out = {}
    probe.publish(name, b"<!doctype html><title>hold</title>v0")
    for label, share in (("삭제 공유 없음", R | W), ("삭제 공유 있음", R | W | D)):
        h = k32.CreateFileW(probe._inside(name), GENERIC_READ, share, None, OPEN_EXISTING, 0, None)
        if h in (None, wintypes.HANDLE(-1).value):
            out[label] = f"열기 실패 {ctypes.get_last_error()}"
            continue
        try:
            tmp = probe._inside(name + ".tmp-hold")
            Path(tmp).write_bytes(b"<!doctype html><title>hold</title>v1")
            try:
                os.replace(tmp, probe._inside(name))
                out[label] = "열린 채로 바꿈 성공"
            except OSError as e:
                out[label] = f"열린 동안 실패({e.winerror if hasattr(e, 'winerror') else e})"
                os.remove(tmp)
        finally:
            k32.CloseHandle(h)
        if not out[label].startswith("열린 채로"):
            r = probe.publish(name, b"<!doctype html><title>hold</title>v2")
            out[label] += f" → 닫은 뒤 {'성공' if r['replace_ok'] else '여전히 실패'}"
    return out


# ── 시험 페이지(가짜 데이터) ─────────────────────────────────────────
def fake_payload(target_bytes: int, seed: int = 7) -> bytes:
    """LOT 추적 열 모양을 흉내 낸 가짜 JSON — 장비 · Job · Lot · Wafer ID · 시각 · Defect. 회사 데이터 아님."""
    rnd = random.Random(seed)
    devs = [f"DEV-{i:02d}" for i in range(1, 42)]
    jobs = [f"JOB_{rnd.choice('ABCDEFGH')}{i:03d} - Multi" for i in range(400)]
    pool = devs + jobs + ["PASS", "Scan error", "EXACT", "NOT_FOUND", "x20", "x20|x5"]
    head = '{"cols":["device","job","lot","wafer_id","start","end","faults","status"],"pool":' + json.dumps(pool) + ',"rows":['
    parts, size, i = [head], len(head), 0
    t = datetime(2026, 1, 1).timestamp()
    while size < target_bytes - 64:
        t += rnd.randint(30, 400)
        lot = f"L{rnd.randint(0, 9999):04d}{rnd.choice('ABCDEF')}"
        row = json.dumps([rnd.randrange(41), 41 + rnd.randrange(400), lot, f"W{rnd.randint(0, 99999999):08d}{rnd.choice('ABCDEFGH')}",
                          datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.fromtimestamp(t + rnd.randint(40, 300)).strftime("%Y-%m-%d %H:%M:%S"),
                          str(rnd.randint(0, 5000)), 441 + (rnd.random() < 0.05)], separators=(",", ":"))
        parts.append(("," if i else "") + row)
        size += len(row) + 1
        i += 1
    parts.append('],"n":' + str(i) + "}")
    return "".join(parts).encode()


PAGE_CSS = """body{font:14px/1.5 'Segoe UI','Malgun Gothic',sans-serif;margin:0;background:#F6F8FA;color:#1B2530}
main{max-width:860px;margin:0 auto;padding:24px 16px}h1{font-size:20px;margin:0 0 4px}.muted{color:#5A6673}
.box{background:#fff;border:1px solid #DCE3EA;border-radius:10px;padding:14px 16px;margin:12px 0}
.bad{color:#C62828;font-weight:700}.ok{color:#1565C0;font-weight:700}table{border-collapse:collapse;width:100%}
td,th{border-bottom:1px solid #EDF1F5;padding:6px 8px;text-align:left;vertical-align:top}th{width:34%;color:#5A6673;font-weight:600}
button{font:inherit;padding:6px 12px;border:1px solid #B8C4D0;border-radius:6px;background:#fff;cursor:pointer;margin:2px}
button.on{background:#1565C0;color:#fff;border-color:#1565C0}textarea{width:100%;height:220px;font:12px Consolas,monospace}
#nojs{background:#FFEBEE;border:1px solid #C62828;color:#C62828;padding:12px;border-radius:8px;font-weight:700}"""


def size_page(mb_label: str, payload: bytes, stamp: str, gz: bool = False) -> bytes:
    """크기 시험 페이지 — 열리면 데이터를 풀어 행 수를 확인하고 부모(안내 페이지)에 결과를 postMessage 한다."""
    if gz:
        data = base64.b64encode(gzip.compress(payload, 6)).decode()
        holder = f'<script type="text/plain" id="gz">{data}</script>'
    else:
        holder = f'<script type="application/json" id="data">{payload.decode()}</script>'
    js = """
const T={stamp:%s,label:%s,gz:%s};
async function go(){const nav=(performance.getEntriesByType('navigation')||[])[0]||{};const t0=performance.now();let txt,ok=false,rows=0,err='';
 try{if(T.gz){const b=atob(document.getElementById('gz').textContent);const u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);
   if(typeof DecompressionStream==='undefined')throw new Error('DecompressionStream 없음');
   txt=await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).text();}
  else txt=document.getElementById('data').textContent;
  const d=JSON.parse(txt);rows=d.rows.length;ok=rows===d.n;if(!ok)err='행 수가 맞지 않음(파일이 잘렸을 수 있음)';}catch(e){err=String(e&&e.message||e);}
 const r={type:'probe',label:T.label,stamp:T.stamp,gz:T.gz,ok,rows,err,openMs:Math.round(t0),parseMs:Math.round(performance.now()-t0),
  fileMs:Math.round(nav.responseEnd||0),bytes:document.documentElement.outerHTML.length};
 document.getElementById('out').innerHTML=(ok?'<span class="ok">정상</span>':'<span class="bad">문제: '+err+'</span>')+
  ' · 파일 생성 '+T.stamp+' · 행 '+rows.toLocaleString()+' · 열기까지 '+(r.openMs/1000).toFixed(1)+'초 · 풀기 '+(r.parseMs/1000).toFixed(1)+'초';
 try{if(parent!==window)parent.postMessage(r,'*');}catch(e){}}
go();""" % (json.dumps(stamp), json.dumps(mb_label), "true" if gz else "false")
    html = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>시험 {mb_label}</title><style>{PAGE_CSS}</style></head>'
            f'<body><main><h1>공유 폴더 시험 — {mb_label}</h1><p class="muted">가짜 데이터입니다(회사 데이터 아님).</p>'
            f'<div class="box" id="out">불러오는 중…</div></main>{holder}<script>{js}</script></body></html>')
    return html.encode()


def guide_page(stamp: str, pages: list, links: list, target_unc: str) -> bytes:
    """팀원이 여는 안내 페이지 — 크기 페이지를 iframe 으로 차례로 열어 시간을 재고, 수동 확인 단추와 '결과 복사'."""
    cfg = {"stamp": stamp, "pages": pages, "links": links, "share": target_unc, "hammer": HAMMER_FILE}
    js = r"""
const C=%s;const R={pages:{},links:{},hammer:[],write:null};
const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function brow(){const ua=navigator.userAgent;const m=ua.match(/Edg\/([\d.]+)/)||ua.match(/Chrome\/([\d.]+)/);return (/Edg\//.test(ua)?'Edge ':/Chrome\//.test(ua)?'Chrome ':'기타 ')+(m?m[1]:'')}
function ls(){try{localStorage.setItem('aoi.probe','1');localStorage.removeItem('aoi.probe');return '됨'}catch(e){return '안 됨'}}
const ENV={browser:brow(),url:(()=>{try{return decodeURI(location.href)}catch(e){return location.href}})(),ds:typeof DecompressionStream!=='undefined'?'있음':'없음',ls:ls(),cores:navigator.hardwareConcurrency||'',mem:navigator.deviceMemory||''};
function loadOne(p,q){return new Promise(res=>{const f=document.createElement('iframe');f.style.cssText='width:1px;height:1px;border:0;position:absolute;left:-9999px';
  const t0=performance.now();let done=false;const fin=r=>{if(done)return;done=true;window.removeEventListener('message',on);f.remove();res(r)};
  const on=e=>{if(e.data&&e.data.type==='probe'&&e.source===f.contentWindow)fin(Object.assign({wallMs:Math.round(performance.now()-t0)},e.data))};
  window.addEventListener('message',on);setTimeout(()=>fin({ok:false,err:'120초 안에 답 없음',wallMs:120000}),120000);
  f.src=encodeURI(p)+(q?'?r='+q:'');document.body.appendChild(f);})}
async function runAll(){const b=$('run');b.disabled=true;for(const p of C.pages){$('st').textContent=p.label+' 여는 중…';R.pages[p.label]=await loadOne(p.file,Date.now());draw();}
  $('st').textContent='끝 — 아래 확인을 마치고 결과 복사';b.disabled=false}
async function runHammer(){const b=$('ham');b.disabled=true;R.hammer=[];for(let i=0;i<10;i++){$('st').textContent='교체 중 열기 '+(i+1)+'/10';
  const r=await loadOne(C.hammer,Date.now());R.hammer.push(r);draw();await new Promise(z=>setTimeout(z,5000));}$('st').textContent='교체 중 열기 끝';b.disabled=false}
function mark(kind,key,v){if(kind==='link')R.links[key]=v;else R.write=v;draw()}
function sec(ms){return ms==null?'—':(ms/1000).toFixed(1)+'초'}
function draw(){const pr=C.pages.map(p=>{const r=R.pages[p.label];return `<tr><th>${esc(p.label)}</th><td>${!r?'—':r.ok?`<span class="ok">정상</span> · 열기 ${sec(r.wallMs)} · 풀기 ${sec(r.parseMs)}`:`<span class="bad">${esc(r.err||'실패')}</span> · ${sec(r.wallMs)}`}</td></tr>`}).join('');
  $('res').innerHTML=pr;
  const hs=R.hammer.map((r,i)=>r.ok?`${i+1}:${esc(r.stamp)}`:`${i+1}:<span class="bad">깨짐</span>`).join(' · ');$('hres').innerHTML=hs||'—';
  $('links').innerHTML=C.links.length?C.links.map(l=>`<tr><th>${esc(l.label)}</th><td><a href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.path)}</a><br>
   <button class="${R.links[l.label]==='열림'?'on':''}" data-k="${esc(l.label)}" data-v="열림">열림</button><button class="${R.links[l.label]==='안 열림'?'on':''}" data-k="${esc(l.label)}" data-v="안 열림">안 열림</button></td></tr>`).join(''):'<tr><td class="muted">장비 링크 없음(devices.csv 를 못 읽음)</td></tr>';
  document.querySelectorAll('#links button').forEach(b=>b.onclick=()=>mark('link',b.dataset.k,b.dataset.v));
  document.querySelectorAll('#wr button').forEach(b=>{b.className=R.write===b.dataset.v?'on':'';b.onclick=()=>mark('write',null,b.dataset.v)});
  $('txt').value=summary()}
function summary(){const L=['[공유 폴더 시험 결과] '+new Date().toLocaleString(),'브라우저: '+ENV.browser,'연 주소: '+ENV.url,'gzip 풀기 기능: '+ENV.ds+' · localStorage: '+ENV.ls+' · CPU '+ENV.cores+' · 메모리 '+ENV.mem+'GB','파일 생성: '+C.stamp];
  for(const p of C.pages){const r=R.pages[p.label];L.push(p.label+': '+(!r?'안 함':r.ok?'정상 열기 '+sec(r.wallMs)+' 풀기 '+sec(r.parseMs):'실패 '+(r.err||'')+' '+sec(r.wallMs)))}
  L.push('교체 중 열기: '+(R.hammer.length?R.hammer.map(r=>r.ok?r.stamp:'깨짐').join(', '):'안 함'));
  for(const l of C.links)L.push('장비 링크 '+l.label+': '+(R.links[l.label]||'확인 안 함'));
  L.push('이 폴더에 새 파일 만들기: '+(R.write||'확인 안 함'));L.push('접속(직접 적기): 사내 유선 / 사내 Wi-Fi / VPN');return L.join('\n')}
function copy(){const t=$('txt');t.value=summary();t.select();let ok=false;try{ok=document.execCommand('copy')}catch(e){}
  if(navigator.clipboard)navigator.clipboard.writeText(t.value).then(()=>{$('cp').textContent='복사됨'},()=>{$('cp').textContent=ok?'복사됨':'직접 선택해 복사하세요'});else $('cp').textContent=ok?'복사됨':'직접 선택해 복사하세요'}
$('nojs').remove();$('ui').hidden=false;
$('env').innerHTML=[['브라우저',ENV.browser],['연 주소',ENV.url],['gzip 풀기 기능',ENV.ds],['localStorage',ENV.ls],['파일 생성',C.stamp]].map(([k,v])=>`<tr><th>${k}</th><td>${esc(v)}</td></tr>`).join('');
$('run').onclick=runAll;$('ham').onclick=runHammer;$('copy').onclick=copy;$('share').textContent=C.share;draw();""" % json.dumps(cfg, ensure_ascii=False)
    html = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>공유 폴더 시험</title><style>{PAGE_CSS}</style></head><body><main>
<h1>공유 폴더 시험</h1><p class="muted">LOT 추적 화면을 공유 폴더에서 바로 열 수 있는지 확인합니다. 가짜 데이터만 씁니다.</p>
<div id="nojs">이 글이 보이면 브라우저가 이 위치의 HTML 스크립트를 막고 있습니다 — 이 화면을 캡처해 보내 주세요.</div>
<div id="ui" hidden>
<div class="box"><table id="env"></table></div>
<div class="box"><b>1. 열기 시간</b> <span class="muted">— 10 · 30 · 60MB 와 gzip 페이지를 차례로 엽니다(몇 분 걸릴 수 있음)</span><br>
<button id="run">시험 시작</button> <span id="st" class="muted"></span><table id="res" style="margin-top:8px"></table></div>
<div class="box"><b>2. 교체 중 열기</b> <span class="muted">— 담당자가 '교체 시험'을 돌리는 동안만 누르세요. 5초마다 10번 엽니다</span><br>
<button id="ham">교체 중 열기</button> <span id="hres" class="muted"></span></div>
<div class="box"><b>3. 장비 폴더 링크</b> <span class="muted">— 누르면 새 탭에 폴더 목록이 보이는지(Report 열기에 필요)</span><table id="links"></table></div>
<div class="box" id="wr"><b>4. 쓰기 권한</b> <span class="muted">— 탐색기로 이 폴더(<span id="share"></span>\\{PROBE_DIR})에서 '새로 만들기 → 텍스트 문서'가 되나요? 됐으면 지워 주세요</span><br>
<button data-v="만들어짐">만들어짐</button><button data-v="권한 없음">권한 없음</button></div>
<div class="box"><b>5. 결과 보내기</b> <button id="copy">결과 복사</button> <span id="cp" class="muted"></span>
<p class="muted">복사한 글에 접속 방식(사내 유선 / Wi-Fi / VPN)을 적어 메신저로 보내 주세요.</p><textarea id="txt" readonly></textarea></div>
</div></main><script>{js}</script></body></html>"""
    return html.encode()


def file_url(path: str) -> str:
    """template 의 reportUrl 과 같은 모양 — 드라이브 문자는 file:///X:/…, UNC 는 file://host/…"""
    from urllib.parse import quote

    unc = path.startswith("\\\\")
    parts = [p for p in re.split(r"[\\/]+", path.lstrip("\\")) if p]
    enc = [p if i == 0 and re.fullmatch(r"[A-Za-z]:", p) else quote(p, safe="") for i, p in enumerate(parts)]
    return ("file://" if unc else "file:///") + "/".join(enc) + "/"


def device_links(devs, resolver=None) -> list:
    """드라이브 문자마다 Camtek 장비 하나 — 드라이브 문자 링크와(알면) UNC 링크 둘."""
    out, seen = [], set()
    for name, full, on, sub in devs:
        key = full[:2].upper() if re.match(r"^[A-Za-z]:", full) else (share_of(full) or ("", ""))[0]
        if not on or not sub or sub == "*" or key in seen:
            continue
        seen.add(key)
        out.append({"label": f"{name} ({full[:2]})", "path": full, "url": file_url(full)})
        u = unc_of(full, resolver)
        if u != full:
            out.append({"label": f"{name} (UNC)", "path": u, "url": file_url(u)})
    return out[:16]


# ── 실행 ─────────────────────────────────────────────────────────────
def _local_out(out: str = "") -> Path:
    if out:
        return Path(out)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "AOI_Capacity" / "share_probe"


def _devices_csv(path: str = "") -> Path:
    if path:
        return Path(path)
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "AOI_Capacity" / "devices.csv"


def _rtt(path: str, n: int = 20) -> dict:
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        os.stat(path)
        ts.append((time.perf_counter() - t0) * 1000)
    ts.sort()
    return {"stat_ms_p50": round(ts[len(ts) // 2], 1), "stat_ms_max": round(ts[-1], 1)}


def run(args, log=print) -> dict:
    res = {"tool_api": TOOL_API, "started": datetime.now().isoformat(timespec="seconds"), "host": platform.node(),
           "python": sys.version.split()[0], "target": args.target}
    devs = []
    csv_path = _devices_csv(args.devices)
    if csv_path.is_file():
        devs = read_devices(csv_path)
    else:
        log(f"! devices.csv 를 찾지 못했습니다({csv_path}) — 장비 NAS 비교 · 장비 링크 없이 진행하려면 --no-devices")
        if not args.no_devices:
            raise Refused("devices.csv 가 없어 장비 NAS 와 같은 공유인지 확인할 수 없습니다 — 멈춥니다")
    res["devices_csv"] = str(csv_path)
    log("1) 장비 NAS 와 같은 공유인지 확인")
    res["share_check"] = check_target(args.target, [(n, f) for n, f, _on, _s in devs])
    log(f"   장비 경로 {res['share_check']['checked_roots']}개와 비교 — 같은 공유 아님"
        + (f" (같은 서버: {', '.join(res['share_check']['same_server'][:5])})" if res["share_check"]["same_server"] else ""))
    if not os.path.isdir(args.target):
        raise Refused(f"공유 폴더가 열리지 않습니다: {args.target}")
    log("2) 쓰기 · 용량 · 왕복 지연")
    probe = Probe(args.target)
    probe.open()
    try:
        du = shutil.disk_usage(probe.dir)
        res["free_mb"] = round(du.free / 1e6)
    except OSError as e:
        res["free_mb"] = None
        res["free_err"] = str(e)
    res["rtt"] = _rtt(probe.dir)
    log(f"   쓰기 됨 · 남은 용량 {res['free_mb']}MB · stat 왕복 {res['rtt']['stat_ms_p50']}ms(최대 {res['rtt']['stat_ms_max']})")
    sizes = list(args.sizes)
    if res["free_mb"] is not None and res["free_mb"] < FREE_NEED_MB and max(sizes) > 10:
        sizes = [s for s in sizes if s <= 10]
        log(f"   ! 남은 용량이 {FREE_NEED_MB}MB 보다 적어 10MB 시험만 합니다")
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log("3) 발행 방식(임시 파일 → 이름 바꾸기)으로 쓰기")
    res["writes"], pages = [], []
    for mb in sizes:
        label = f"{mb:g}MB"
        name = f"시험_{label}.html"
        w = probe.publish(name, size_page(label, fake_payload(int(mb * 1e6)), stamp))
        w.update(probe.read_back(name))
        res["writes"].append(w)
        pages.append({"label": label, "file": name})
        log(f"   {label}: 쓰기 {w['write_s']}초 · 이름 바꾸기 {w['replace_s']}초{' (재시도 %d)' % w['retries'] if w['retries'] else ''}"
            f" · 다시 읽기 {w['read_s']}초(내 PC 캐시가 섞일 수 있음)")
    raw = fake_payload(int(args.gz_raw_mb * 1e6))
    gz_label = f"gzip({args.gz_raw_mb:g}MB→)"
    w = probe.publish("시험_gzip.html", size_page(gz_label, raw, stamp, gz=True))
    res["writes"].append(w)
    pages.append({"label": f"gzip {args.gz_raw_mb:g}MB(파일 {w['mb']}MB)", "file": "시험_gzip.html"})
    log(f"   gzip: 원본 {args.gz_raw_mb:g}MB → 파일 {w['mb']}MB · 쓰기 {w['write_s']}초 (가짜 데이터라 실데이터보다 덜 줄어듦)")
    log("4) 열린 파일 바꾸기")
    res["hold"] = hold_test(probe)
    for k, v in res["hold"].items():
        log(f"   {k}: {v}")
    log("5) 팀원 시험 페이지")
    probe.publish(HAMMER_FILE, size_page("교체 시험", fake_payload(HAMMER_MB * 1_000_000, seed=1), stamp))
    links = device_links(devs)
    probe.publish("시험_안내.html", guide_page(stamp, pages, links, res["share_check"]["target_unc"]))
    res["guide"] = os.path.join(probe.dir, "시험_안내.html")
    res["guide_unc"] = os.path.join(unc_of(probe.dir), "시험_안내.html")
    log(f"   팀원에게 보낼 경로: {res['guide_unc']}")
    res["finished"] = datetime.now().isoformat(timespec="seconds")
    return res


def hammer(args, log=print) -> dict:
    """교체 시험 — 정해진 시간 동안 시험_교체.html 을 계속 바꿔 쓴다. 팀원은 그동안 안내 페이지의 '교체 중 열기'."""
    probe = Probe(args.target)
    probe.open()
    end = time.time() + args.hammer
    out = {"hammer_s": args.hammer, "rounds": []}
    log(f"교체 시험 {args.hammer}초 — {HAMMER_EVERY}초마다 {HAMMER_FILE}({HAMMER_MB}MB) 교체. Ctrl+C 로 멈춤")
    try:
        n = 0
        while time.time() < end:
            n += 1
            stamp = f"{datetime.now():%H:%M:%S} #{n}"
            r = probe.publish(HAMMER_FILE, size_page("교체 시험", fake_payload(HAMMER_MB * 1_000_000, seed=n), stamp))
            out["rounds"].append({"n": n, "stamp": stamp, **{k: r[k] for k in ("write_s", "replace_s", "replace_ok", "retries", "replace_errors")}})
            log(f"  #{n} {stamp}: 쓰기 {r['write_s']}초 · 바꾸기 {'성공' if r['replace_ok'] else '실패'}"
                + (f"(재시도 {r['retries']}: {r['replace_errors'][0]})" if r["retries"] else ""))
            time.sleep(max(0.0, HAMMER_EVERY - r["write_s"] - r["replace_s"]))
    except KeyboardInterrupt:
        log("  멈춤")
    out["fail"] = sum(1 for r in out["rounds"] if not r["replace_ok"])
    out["retried"] = sum(1 for r in out["rounds"] if r["retries"])
    return out


def _save(res: dict, out_dir: Path, target: str, log=print) -> Path:
    if _under(str(out_dir), target) or _under(str(out_dir), unc_of(target)):
        raise Refused(f"결과 폴더가 공유 폴더 안입니다: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"공유시험_{datetime.now():%Y%m%d_%H%M%S}.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"결과 저장: {p}")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="LOT 추적 HTML 을 공유 폴더에 올릴 수 있는지 시험")
    ap.add_argument("--target", default=TARGET)
    ap.add_argument("--devices", default="", help="devices.csv (기본: %%LOCALAPPDATA%%\\AOI_Capacity\\devices.csv)")
    ap.add_argument("--no-devices", action="store_true", help="devices.csv 없이 진행(장비 NAS 비교 안 함)")
    ap.add_argument("--sizes", type=float, nargs="+", default=list(SIZES_MB))
    ap.add_argument("--gz-raw-mb", type=float, default=GZ_RAW_MB)
    ap.add_argument("--out", default="", help="결과 JSON 폴더(로컬)")
    ap.add_argument("--hammer", type=int, default=0, help="교체 시험 초(팀원이 그동안 '교체 중 열기')")
    ap.add_argument("--clean", action="store_true", help="이 도구가 만든 시험 파일 지우기")
    ap.add_argument("--yes", action="store_true", help="묻지 않기")
    args = ap.parse_args(argv)
    try:
        if args.clean:
            gone = Probe(args.target).clean()
            print(f"지움 {len(gone)}개: {', '.join(gone) if gone else '(없음)'}")
            return 0
        if args.hammer:
            if not args.no_devices and _devices_csv(args.devices).is_file():
                check_target(args.target, [(n, f) for n, f, _o, _s in read_devices(_devices_csv(args.devices))])
            res = hammer(args)
            _save({"target": args.target, **res}, _local_out(args.out), args.target)
            return 0 if not res["fail"] else 2
        res = run(args)
        _save(res, _local_out(args.out), args.target)
        print("\n다음: 팀원에게 위 '팀원에게 보낼 경로' 를 보내 시험_안내.html 을 열게 하세요.")
        if not args.yes and sys.stdin and sys.stdin.isatty():
            a = input(f"지금 교체 시험을 시작할까요? 팀원이 '교체 중 열기' 를 누르는 동안 300초 [y/N] ").strip().lower()
            if a == "y":
                args.hammer = 300
                h = hammer(args)
                _save({"target": args.target, **h}, _local_out(args.out), args.target)
        print("시험이 다 끝나면: share_probe.bat --clean")
        return 0
    except Refused as e:
        print(f"멈춤: {e}")
        return 3
    except OSError as e:
        print(f"오류: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
