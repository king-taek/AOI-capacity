import sys, os, re, json, collections, statistics as st, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt; from fam import family, category, CATS
A = sys.argv[1]
def P(s): return dt.datetime.fromisoformat(s) if s else None
def q(v, nd=0):
    v = sorted(x for x in v if x is not None); n = len(v)
    return dict(n=n, med=round(st.median(v), nd), p10=round(v[n//10], nd), p90=round(v[n*9//10], nd), mean=round(sum(v)/n, nd)) if n else None
def num(x):
    try: return float(x)
    except: return None
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d] = 'EagleG5'
devorder = lambda d: (d.startswith('4F'), int(re.sub(r'\D', '', d) or 0))
lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
AC = json.load(open(f'{A}/ac4.json'))
R = [json.loads(l) for l in open(f'{A}/wafers.jsonl', encoding='utf-8')]
for r in R:
    r['_s'], r['_e'], r['_ss'] = P(r['start']), P(r['end']), P(r['scanstart'])
    r['_wt'] = (r['_e'] - r['_s']).total_seconds() if r['_s'] and r['_e'] else None
    r['_load'] = (r['_ss'] - r['_s']).total_seconds() if r['_s'] and r['_ss'] else None
    r['_dur'] = (num(r['dur']) or 0) / 1000 if r['dur'] else None
    r['_post'] = ((r['_e'] - r['_ss']).total_seconds() - r['_dur']) if (r['_ss'] and r['_e'] and r['_dur'] is not None) else None
    r['_fam'] = family(r['job']); r['_gen'] = GEN.get(r['dev'], '?')
    r['_in'] = False
    if r['_s']:
        for rp in lots[r['lot_id']]['reports']:
            b0, b1 = pt(rp['bs']), pt(rp['be'])
            if b0 and b1 and b0.timestamp() - 600 <= r['_s'].timestamp() <= b1.timestamp() + 600: r['_in'] = True; break
RW = [r for r in R if r['_in'] and r['_wt'] and 0 < r['_wt'] < 7200]
F = {}
# (b) clean reference cost: per (fam, gen): median load with cr=Lot(or None) vs cr=Wafer, then hours = sum over wafers in cr=Wafer lots of (load - base)
base = collections.defaultdict(list); wload = collections.defaultdict(list)
for r in RW:
    a = AC.get(r['lot_id']); 
    if not a or r['_load'] is None: continue
    k = (r['_fam'] or '기타', r['_gen'])
    (wload if (a['cr'] or '').lower() == 'wafer' else base)[k].append(r['_load'])
cost = []; total_h = 0
for k, v in wload.items():
    if len(v) >= 30 and len(base[k]) >= 30:
        b = st.median(base[k]); w = st.median(v); extra = max(0, (w - b)) * len(v) / 3600; total_h += extra
        cost.append(dict(fam=k[0], gen=k[1], wafers=len(v), base=round(b), wafer=round(w), extra_h=round(extra, 1)))
cost.sort(key=lambda x: -x['extra_h'])
F['cr_cost'] = dict(rows=cost, total_h=round(total_h))
# current per-wafer CR settings (latest lot per dev/job) with 30-day volume
seq = collections.defaultdict(list)
for lid in AC: seq[(lots[lid]['device'], lots[lid]['job'])].append(lid)
cur_w = []
wcount = collections.Counter(r['lot_id'] for r in RW)
for (dev, job), ls in seq.items():
    ls.sort(key=lambda l: pt(lots[l]['bs']) or dt.datetime.min)
    a = AC[ls[-1]]
    if (a['cr'] or '').lower() == 'wafer':
        n_w = sum(wcount[l] for l in ls if (AC[l]['cr'] or '').lower() == 'wafer')
        ld = [r['_load'] for l in ls for r in RW if r['lot_id'] == l and r['_load'] is not None] if n_w else []
        cur_w.append(dict(dev=dev, gen=GEN.get(dev), job=job, lots=len(ls), wafers=n_w, af=a['af'], load=round(st.median(ld)) if ld else None, last=str(pt(lots[ls[-1]]['bs']))[:10]))
cur_w.sort(key=lambda x: -x['wafers'])
F['cr_wafer_current'] = cur_w[:40]; F['cr_wafer_current_total'] = dict(pairs=len(cur_w), wafers=sum(x['wafers'] for x in cur_w))
# G5 inherent: load for cr in (Lot,None) & af None by gen
inh = collections.defaultdict(list)
for r in RW:
    a = AC.get(r['lot_id'])
    if a and r['_load'] is not None and (a['cr'] or 'None').lower() != 'wafer' and (a['af'] or 'None').lower() == 'none': inh[r['_gen']].append(r['_load'])
F['load_inherent'] = {g: q(v) for g, v in inh.items()}
# load by dev for G5 with same settings (cr Lot, af None|Wafer) 
ldv = collections.defaultdict(list)
for r in RW:
    a = AC.get(r['lot_id'])
    if a and r['_load'] is not None and r['_gen'] == 'EagleG5' and (a['cr'] or 'None').lower() != 'wafer': ldv[(r['dev'], a['af'] or 'None')].append(r['_load'])
F['g5_load_dev'] = [dict(dev=k[0], af=k[1], **q(v)) for k, v in sorted(ldv.items(), key=lambda kv: devorder(kv[0][0])) if len(v) >= 50]
# (d) RDL post single vs multi same device
rp = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and 'Swelling' not in r['_fam'] and r['_post'] is not None and r['_dur']:
        rp[(r['dev'], 'multi' if r['nrec'] >= 2 else 'single')].append((r['_post'], r['_dur'], r['_wt'], r['_load']))
F['rdl_post'] = [dict(dev=k[0], mode=k[1], n=len(v), post=q([x[0] for x in v])['med'], scan=q([x[1] for x in v])['med'], wt=q([x[2] for x in v])['med'], load=q([x[3] for x in v])['med']) for k, v in sorted(rp.items(), key=lambda kv: (devorder(kv[0][0]), kv[0][1])) if len(v) >= 30]
# (c) wafer id sanity for top repeat job + DIA classification
TOK = re.compile(r'(^|[\s_-])(RE|RESCAN|REWORK|R\d?)([\s_-]|$)', re.I)
STEP = re.compile(r'(^|[\s_-])(DIA|SRD|3D|EDGE|BUMP|CENTER|PCM|SPT|2D)([\s_-]|$)', re.I)
def core(l): return re.sub(r'[\s_-]+', '-', TOK.sub(r'\1\3', TOK.sub(r'\1\3', l))).strip('-').upper()
def steps(l): return tuple(sorted(m.group(2).upper() for m in STEP.finditer(l)))
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s']: seen[(r['job'], r['wid'])].append(r)
cls = collections.Counter(); cls_h = collections.Counter(); byjob = collections.defaultdict(collections.Counter)
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]):
        if a['lot_id'] == b['lot_id']: c = '같은 Lot 재시도'
        elif steps(a['lot']) != steps(b['lot']): c = '검사 단계가 다름(DIA·SRD 등)'
        elif core(a['lot']) == core(b['lot']): c = '같은 Lot 다시(RE 표기·재실행)'
        elif a['dev'] != b['dev']: c = '다른 장비 · 다른 Lot 이름'
        else: c = '같은 장비 · 다른 Lot 이름'
        cls[c] += 1; cls_h[c] += (b['_wt'] or 0) / 3600; byjob[k[0]][c] += 1
F['repeat_cls2'] = dict(cls); F['repeat_cls2_h'] = {k: round(v) for k, v in cls_h.items()}
# wafer id sanity: wid distinct per lot for top job
j = 'CMP2D-DT-GH10N-BIN1-H-U1_0856268PD-0A'
wl = collections.defaultdict(set); lw = collections.defaultdict(set)
for r in R:
    if r['job'] == j and r['wid']: wl[r['wid']].add(r['lot']); lw[r['lot']].add(r['wid'])
F['cmp2d'] = dict(wids=len(wl), lots=len(lw), wid_in_many_lots=sum(1 for v in wl.values() if len(v) > 1), lots_sample={l: len(w) for l, w in list(lw.items())[:8]}, wid_sample=[(w, sorted(l)) for w, l in list(wl.items())[:5]])
# 'other lot name' pairs: sample 10 for same device
samp = []
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]):
        if a['lot_id'] != b['lot_id'] and steps(a['lot']) == steps(b['lot']) and core(a['lot']) != core(b['lot']) and a['dev'] == b['dev'] and len(samp) < 12:
            samp.append((k[0][:40], k[1], a['lot'], a['start'][:16], b['lot'], b['start'][:16], (a['rstatus'] or '')[:10], (b['rstatus'] or '')[:10]))
F['repeat_other_samples'] = samp
F['repeat_other_jobs'] = sorted([(jb, c['같은 장비 · 다른 Lot 이름'] + c['다른 장비 · 다른 Lot 이름']) for jb, c in byjob.items()], key=lambda x: -x[1])[:12]
# (a) refined change events: persistent vs toggle, excluding step-variant pairs
Q = json.load(open(f'{A}/params4.json'))
ev = Q['events']['sample'] + Q['events']['det_events']
# we need full sequences — recompute from raw: too heavy here; approximate with det_events: toggles = value pattern A->B then B->A later for same dev/job/key
seqk = collections.defaultdict(list)
for e in Q['events']['det_events']:
    for c in e['changes']:
        if c[0] == '검출 기준': seqk[(e['dev'], e['job'], c[1])].append((e['tb'], c[2], c[3]))
tog = 0; pers = 0
for k, v in seqk.items():
    v.sort(); vals = [v[0][1]] + [x[2] for x in v]
    if len(set(vals)) <= 2 and len(v) >= 2: tog += 1
    else: pers += 1
F['det_key_seq'] = dict(keys=len(seqk), toggling=tog, other=pers)
json.dump(F, open(f'{A}/facts6.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
for k, v in F.items(): print('==', k); print(json.dumps(v, ensure_ascii=False)[:3000])
