"""파라미터 상태 — 참조(dedup) 해소 · AutoCycle 설정 × 시간 · 결함 상한 · 장비 간 차이 · 변경 이력 → params4.json"""
import sys, os, re, json, collections, statistics as st, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt; from fam import family, category, CATS
A, X = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'scripts'))); import collect_wafer_logs as T
lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
P = json.load(open(f'{A}/params3_raw.json', encoding='utf-8'))
def flatten(path, rel):
    fl = {}
    try: t = open(path, 'rb').read().decode('cp949', 'replace')
    except OSError: return fl
    sec = ''; alg = ''; rtp = rel.lower().endswith('rtp.txt')
    for l in t.splitlines():
        l = l.strip()
        if not l or l[0] in ';#': continue
        if l.startswith('[') and ']' in l: sec = l[:l.index(']') + 1]; alg = ''; continue
        if '=' not in l: continue
        k, v = l.split('=', 1); k = k.strip(); v = v.strip()
        if rtp and ';' in v: v = v.split(';', 1)[0].strip()
        if k == 'Alg': alg = v; continue
        fl[f"{rel}{sec}{('<' + alg + '>') if alg else ''}{k}"] = v
    return fl
cache = {}
def full(lid):
    d = P.get(lid)
    if d is None: return None
    out = {k: v for k, v in d.items() if k != '__refs__'}
    for rel, tgt in d.get('__refs__', {}).items():
        if tgt not in cache: cache[tgt] = flatten(os.path.join(X, *tgt.split('/')), rel)
        out.update(cache[tgt])
    return out
def bt(l): return pt(l['bs']) or pt(l['be'])
GUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
UI = re.compile(r'\](LastCam|LastCamZoom|Recipe Name|RecipeName|Id)$')
def norm(k): return re.sub(r'[\s_\-]', '', k).lower()
def num(v):
    try: return float(v)
    except: return None
def same(a, b):
    if a == b: return True
    x, y = num(a), num(b)
    if x is not None and y is not None: return abs(x - y) <= max(1e-9, 0.005 * max(abs(x), abs(y)))
    return False
FULL = {}
for lid in P: FULL[lid] = full(lid)
print('resolved', len(FULL), 'cache', len(cache), file=sys.stderr)
# volatile keys: change in >40% of consecutive same (dev,job,setup) pairs
seq = collections.defaultdict(list)
for lid in FULL: seq[(lots[lid]['device'], lots[lid]['job'], lots[lid]['setup'])].append(lid)
for ls in seq.values(): ls.sort(key=lambda l: bt(lots[l]) or dt.datetime.min)
chg = collections.Counter(); tr = collections.Counter()
for ls in seq.values():
    for a, b in zip(ls, ls[1:]):
        Aa, Bb = FULL[a], FULL[b]
        for k in set(Aa) & set(Bb):
            tr[k] += 1; chg[k] += (not same(Aa[k], Bb[k]))
vol = {k for k in tr if tr[k] >= 5 and chg[k] / tr[k] > 0.4}
def usable(k, v=''):
    return k not in vol and not GUID.search(k) and not GUID.search(str(v)) and not UI.search(k) and category(k) in CATS
# descriptions from RTP.txt comments (first seen)
DESC = {}
# ── AutoCycle settings per lot ──
def ac(fl, key):
    v = fl.get(f'Recipe.ini[AutoCycle]{key}')
    if v is None: return None
    m = re.match(r'(\S+)\s*;\s*(.*)', v)
    return (m.group(2).strip() or m.group(1)) if m else v
AC = {}
for lid, fl in FULL.items():
    AC[lid] = dict(cr=ac(fl, 'CleanReferenceEvery'), af=ac(fl, 'AutoFocusEvery'), afba=ac(fl, 'AutoFocusBeforeAlignment'), ncr=ac(fl, 'NewCleanReferenceOption'),
                   cap=fl.get('GlobalRTP.ini[General]MaxFaultsPerWafer') or next((v for k, v in fl.items() if k.endswith('MaxFaultsPerWafer')), None),
                   fjt=ac(fl, 'FineJobeTuneEvery'), slot=ac(fl, 'SlotFillType'))
json.dump(AC, open(f'{A}/ac4.json', 'w'), ensure_ascii=False)
# join with wafer load times
W = collections.defaultdict(list)
for line in open(f'{A}/wafers.jsonl', encoding='utf-8'):
    r = json.loads(line)
    if r['start'] and r['scanstart'] and r['end']:
        s, ss, e = dt.datetime.fromisoformat(r['start']), dt.datetime.fromisoformat(r['scanstart']), dt.datetime.fromisoformat(r['end'])
        b0, b1 = pt(lots[r['lot_id']]['bs']), pt(lots[r['lot_id']]['be'])
        if b0 and b1 and b0.timestamp() - 600 <= s.timestamp() <= b1.timestamp() + 600:
            W[r['lot_id']].append(((ss - s).total_seconds(), (e - s).total_seconds()))
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d] = 'EagleG5'
def q(v, nd=0):
    v = sorted(v); n = len(v)
    return dict(n=n, med=round(st.median(v), nd), p10=round(v[n//10], nd), p90=round(v[n*9//10], nd)) if n else None
OUT = {}
# CR setting × load time by fam/gen
crt = collections.defaultdict(list); crl = collections.Counter(); crw = collections.Counter()
for lid, a in AC.items():
    l = lots[lid]; f = family(l['job']) or '기타'; g = GEN.get(l['device'], '?')
    key = (f, g, a['cr'] or '?', a['af'] or '?')
    crl[key] += 1; crw[key] += len(W.get(lid, []))
    crt[key] += [x[0] for x in W.get(lid, [])]
OUT['cr_load'] = [dict(fam=k[0], gen=k[1], cr=k[2], af=k[3], lots=crl[k], **q(v)) for k, v in sorted(crt.items(), key=lambda kv: -len(kv[1])) if len(v) >= 30]
# per device current (latest lot) CR / AF / cap per job family
cur = collections.defaultdict(dict)
for (dev, job, setup), ls in seq.items():
    last = ls[-1]; a = AC[last]
    cur[dev][job] = dict(cr=a['cr'], af=a['af'], cap=a['cap'], last=str(bt(lots[last]))[:10], lots=len(ls))
OUT['cur_settings'] = cur
# lots per CR setting where CR = per wafer: hours cost estimate = lots*wafers*(load diff)
per_wafer_cr = [(lid, a) for lid, a in AC.items() if a['cr'] and 'wafer' in a['cr'].lower()]
OUT['cr_wafer_lots'] = dict(lots=len(per_wafer_cr), wafers=sum(len(W.get(lid, [])) for lid, _ in per_wafer_cr),
                            by_dev_job=collections.Counter((lots[lid]['device'], lots[lid]['job']) for lid, _ in per_wafer_cr).most_common(20))
# cap distribution per device (latest per job) for fam jobs
capd = collections.defaultdict(collections.Counter)
for dev, jobs in cur.items():
    for job, v in jobs.items():
        f = family(job)
        if f: capd[f][(dev, v['cap'])] += 1
OUT['cap_by_fam'] = {f: sorted([(d, c) for (d, c) in cnt], key=lambda x: (x[0].startswith('4F'), int(re.sub(r'\D', '', x[0]) or 0))) for f, cnt in capd.items()}
# ── change events (all lots, 30 days) ──
events = []; npairs = 0; ev_cat = collections.Counter(); ev_dev = collections.Counter(); ev_dev_det = collections.Counter()
for (dev, job, setup), ls in seq.items():
    for a, b in zip(ls, ls[1:]):
        npairs += 1
        Aa, Bb = FULL[a], FULL[b]
        d = [k for k in set(Aa) & set(Bb) if usable(k, Aa[k]) and not same(Aa[k], Bb[k])]
        if d:
            cats = collections.Counter(category(k) for k in d)
            ev_cat.update(cats.keys()); ev_dev[dev] += 1
            if '검출 기준' in cats: ev_dev_det[dev] += 1
            events.append(dict(dev=dev, job=job, lot_a=lots[a]['lot'], lot_b=lots[b]['lot'], ta=str(bt(lots[a]))[:16], tb=str(bt(lots[b]))[:16],
                               cats=dict(cats), changes=[[category(k), k, Aa[k], Bb[k]] for k in sorted(d, key=lambda k: (CATS.index(category(k)), k))][:40]))
events.sort(key=lambda e: e['tb'])
OUT['events'] = dict(npairs=npairs, n=len(events), cat=dict(ev_cat), by_dev=dict(ev_dev), by_dev_det=dict(ev_dev_det),
                     det_events=[e for e in events if '검출 기준' in e['cats']][-200:], sample=[dict(e, changes=e['changes'][:8]) for e in events[-300:]])
# ── cross machine diff per family (latest lot per device) ──
fams = collections.defaultdict(lambda: collections.defaultdict(list))
for lid in FULL:
    f = family(lots[lid]['job'])
    if f: fams[f][lots[lid]['device']].append(lid)
res = []
for f, devs in sorted(fams.items(), key=lambda kv: -sum(len(v) for v in kv[1].values())):
    if len(devs) < 3: continue
    dv = {}; meta = {}
    for d, ls in devs.items():
        ls.sort(key=lambda l: bt(lots[l]) or dt.datetime.min); last = ls[-1]
        dv[d] = {norm(k): (v, k) for k, v in FULL[last].items() if usable(k, v)}
        wt = [x[1] for l in ls for x in W.get(l, [])]
        meta[d] = dict(lots=len(ls), jobs=sorted({lots[l]['job'] for l in ls}), last=lots[last]['lot'], last_t=str(bt(lots[last]))[:10], wafer_s=round(st.median(wt)) if wt else None, wafers=len(wt),
                       cr=AC[last]['cr'], af=AC[last]['af'], cap=AC[last]['cap'])
    nd = len(dv); allk = collections.Counter(k for v in dv.values() for k in v)
    rows = []
    for k, c in allk.items():
        if c < max(2, nd / 2): continue
        vals = {d: v[k][0] for d, v in dv.items() if k in v}
        groups = []
        for d, val in vals.items():
            for g in groups:
                if same(g[0], val): g[1].append(d); break
            else: groups.append([val, [d]])
        if len(groups) < 2: continue
        groups.sort(key=lambda g: -len(g[1])); cons = groups[0][0]
        orig = next(v[k][1] for v in dv.values() if k in v)
        rows.append(dict(cat=category(orig), key=orig, cons=cons, ncons=len(groups[0][1]), vals=vals, dev_off=[d for g in groups[1:] for d in g[1]]))
    rows.sort(key=lambda r: (CATS.index(r['cat']), r['key']))
    cnt = {d: collections.Counter(r['cat'] for r in rows if d in r['dev_off']) for d in dv}
    res.append(dict(family=f, devices=sorted(dv, key=lambda d: (d.startswith('4F'), int(re.sub(r'\D', '', d) or 0))), meta=meta, rows=rows[:400],
                    cnt={d: dict(c) for d, c in cnt.items()}, compared=sum(1 for k, c in allk.items() if c >= max(2, nd / 2)), ndiff=len(rows), diffcat=dict(collections.Counter(r['cat'] for r in rows))))
    print(f"{f:22s} 장비 {nd} · 비교 키 {res[-1]['compared']} · 다른 키 {len(rows)} {res[-1]['diffcat']}", file=sys.stderr)
OUT['fam'] = res
json.dump(OUT, open(f'{A}/params4.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
print('ok events', OUT['events']['n'], 'of', npairs, OUT['events']['cat'])
