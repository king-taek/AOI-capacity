import sys, os, re, json, collections, statistics as st, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt; from fam import family
A = sys.argv[1]
def P(s): return dt.datetime.fromisoformat(s) if s else None
def q(v, nd=0):
    v = sorted(x for x in v if x is not None); n = len(v)
    return dict(n=n, med=round(st.median(v), nd), p10=round(v[n//10], nd), p90=round(v[n*9//10], nd), mean=round(sum(v)/n, nd)) if n else None
def num(x):
    try: return float(x)
    except: return None
lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
R = [json.loads(l) for l in open(f'{A}/wafers.jsonl', encoding='utf-8')]
for r in R:
    r['_s'], r['_e'], r['_ss'] = P(r['start']), P(r['end']), P(r['scanstart'])
    r['_wt'] = (r['_e'] - r['_s']).total_seconds() if r['_s'] and r['_e'] else None
    r['_dur'] = (num(r['dur']) or 0) / 1000 if r['dur'] else None
    r['_fam'] = family(r['job'])
    r['_rep'] = None
    if r['_s']:
        for rp in lots[r['lot_id']]['reports']:
            b0, b1 = pt(rp['bs']), pt(rp['be'])
            if b0 and b1 and b0.timestamp() - 600 <= r['_s'].timestamp() <= b1.timestamp() + 600: r['_rep'] = rp; break
F = {}
# 1. repeat deep dive
TOK = re.compile(r'(^|[\s_-])(RE|RESCAN|REWORK|SRD|R\d?)([\s_-]|$)', re.I)
def lotcore(l): return re.sub(r'[\s_-]+', '-', TOK.sub(r'\1\3', TOK.sub(r'\1\3', l))).strip('-').upper()
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s']: seen[(r['job'], r['wid'])].append(r)
rel = collections.Counter(); per_wafer = collections.Counter(); hrs_dev = collections.Counter(); job_detail = collections.defaultdict(lambda: dict(extra=0, hours=0.0, same_core=0, lots=set(), devs=set(), gaps=[]))
examples = collections.defaultdict(list)
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s']); per_wafer[min(len(v), 6)] += 1
    for a, b in zip(v, v[1:]):
        same_core = lotcore(a['lot']) == lotcore(b['lot'])
        c = ('같은 Lot 이름' if a['lot'] == b['lot'] else '같은 Lot(RE 표기만 다름)' if same_core else '다른 Lot 이름')
        rel[c] += 1
        if b['_wt']: hrs_dev[b['dev']] += b['_wt'] / 3600
        jd = job_detail[k[0]]; jd['extra'] += 1; jd['hours'] += (b['_wt'] or 0) / 3600; jd['same_core'] += same_core; jd['lots'].add(b['lot']); jd['devs'].add(b['dev'])
        if a['_e']: jd['gaps'].append((b['_s'] - a['_e']).total_seconds() / 3600)
        if len(examples[k[0]]) < 3: examples[k[0]].append((a['dev'], a['lot'], a['start'][:16], b['dev'], b['lot'], b['start'][:16]))
F['repeat_rel'] = dict(rel); F['repeat_per_wafer'] = dict(per_wafer)
F['repeat_hours_dev'] = {d: round(h, 1) for d, h in sorted(hrs_dev.items(), key=lambda kv: -kv[1])}
top = sorted(job_detail.items(), key=lambda kv: -kv[1]['extra'])[:20]
F['repeat_top_jobs'] = [dict(job=j, extra=d['extra'], hours=round(d['hours'], 1), same_core_pct=round(100*d['same_core']/d['extra']), lots=len(d['lots']), devs=sorted(d['devs']),
                             gap_h=q(d['gaps'], 1), ex=examples[j]) for j, d in top]
# wafers scanned twice in same job within 24h on same device: how many lots are 'full lot rescans' (>=20 wafers repeated between two lots)
pair_lots = collections.Counter()
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]): pair_lots[(a['lot_id'], b['lot_id'])] += 1
F['pair_lots_hist'] = dict(collections.Counter('1~2장' if n <= 2 else '3~9장' if n < 10 else '10~19장' if n < 20 else '20장 이상' for n in pair_lots.values()))
F['pair_lots_wafers'] = dict(collections.Counter(('1~2장' if n <= 2 else '3~9장' if n < 10 else '10~19장' if n < 20 else '20장 이상') for n in pair_lots.values() for _ in range(n)))
# 2. multi-report lots: earlier reports' wafers whose INI belongs to a later report (collector STALE exposure)
exposure = 0; rows_total = 0; lots_hit = 0
for l in lots.values():
    reps = l['reports']
    rows_total += sum(rp['n'] for rp in reps)
    if len(reps) < 2: continue
    n_rows = sum(rp['n'] for rp in reps); n_ini = sum(1 for r in R if r['lot_id'] == l['lot_id'] and r['_s'])
    # wafers with INI matched to each report
    hit = n_rows - n_ini
    if hit > 0: exposure += hit; lots_hit += 1
F['stale_exposure'] = dict(rows_without_own_ini=exposure, rows_total=rows_total, lots_hit=lots_hit)
# 3. multi-recipe timing check for PI G5
chk = collections.defaultdict(list)
for r in R:
    if r['_rep'] and r['_fam'] and 'PI' in r['_fam'] and r['_dur'] and r['_e']:
        ex = sorted((P(v), k) for k, v in r['ext'].items() if v)
        if len(ex) == 2:
            seg1 = (ex[1][0] - ex[0][0]).total_seconds(); seg2 = (r['_e'] - ex[1][0]).total_seconds()
            chk[r['_fam']].append((r['_dur'] - seg1, seg2 - (r['_dur'] - seg1)))
F['multi_check'] = {f: dict(second_scan=q([a for a, _ in v]), post_after=q([b for _, b in v])) for f, v in chk.items() if len(v) >= 100}
# 4. same device both orders
ordt = collections.defaultdict(lambda: collections.defaultdict(list))
for r in R:
    if r['_rep'] and r['_fam'] and 'PI' in r['_fam'] and r['_wt']:
        ex = sorted((P(v), k) for k, v in r['ext'].items() if v)
        if len(ex) == 2: ordt[(r['_fam'], r['dev'])][ex[0][1] + '→' + ex[1][1]].append(r['_wt'])
F['order_both'] = [dict(fam=k[0], dev=k[1], orders={o: q(v) for o, v in d.items()}) for k, d in sorted(ordt.items()) if len(d) >= 2 and all(len(v) >= 20 for v in d.values())]
# 5. AOI-17 Enhanced slow
e17 = [r for r in R if r['dev'] == 'AOI-17' and r['_fam'] and 'Enhanced' in r['_fam'] and r['_rep'] and r['_dur']]
by_day = collections.defaultdict(list)
for r in e17: by_day[(r['_fam'], r['start'][:10])].append((r['_dur'], num(r['dur2d']) or 0, num(r['dur3d']) or 0, tuple(sorted(x.strip() for x in r['recnames']))))
F['aoi17_enh'] = [dict(fam=k[0], day=k[1], n=len(v), dur=round(st.median([x[0] for x in v])), d3=round(st.median([x[2] for x in v])/1000), rec=collections.Counter(x[3] for x in v).most_common(1)[0][0]) for k, v in sorted(by_day.items())]
# where else do Enhanced run, time per device/day for PI4 Enhanced
e_all = collections.defaultdict(list)
for r in R:
    if r['_fam'] == 'TB500 PI4 Enhanced' and r['_rep'] and r['_dur']: e_all[(r['dev'], r['job'])].append(r['_dur'])
F['pi4enh_dev_job'] = [dict(dev=k[0], job=k[1], n=len(v), dur=round(st.median(v))) for k, v in sorted(e_all.items()) if len(v) >= 10]
# 6. G5 load by job for single-recipe '기타'
ld = collections.defaultdict(list)
for r in R:
    if r['_rep'] and r['_s'] and r['_ss'] and not r['_fam'] and r['nrec'] <= 1:
        gen = 'G5' if r['dev'] in ('AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05') else 'old'
        ld[(gen, r['dev'])].append((r['_ss'] - r['_s']).total_seconds())
F['load_single_dev'] = [dict(gen=k[0], dev=k[1], **q(v)) for k, v in sorted(ld.items()) if len(v) >= 50]
# 7. 3D usage: wafers with dur3d > 0 by device
d3 = collections.Counter(); d3n = collections.Counter()
for r in R:
    if r['_rep'] and r['dur3d'] is not None and r['dur3d'] != '':
        d3n[r['dev']] += 1; d3[r['dev']] += (num(r['dur3d']) or 0) > 0
F['use3d'] = {d: round(100 * d3[d] / d3n[d]) for d in d3n if d3n[d]}
# 8. yield field: report yield <100 share; wafer pass flag
wp = collections.Counter(r['wpass'] for r in R if r['_rep'])
F['wafer_pass'] = dict(wp.most_common(5))
json.dump(F, open(f'{A}/facts5.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
for k, v in F.items(): print('==', k); print(json.dumps(v, ensure_ascii=False)[:2500])
