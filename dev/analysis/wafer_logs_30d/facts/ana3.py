"""30일 전수 분석 — 결과를 facts.json 으로."""
import sys, os, re, json, collections, statistics as st, datetime as dt, math
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt; from fam import family
A = sys.argv[1]
def P(s): return dt.datetime.fromisoformat(s) if s else None
def q(v, nd=1):
    v = sorted(x for x in v if x is not None); n = len(v)
    if not n: return None
    return dict(n=n, med=round(st.median(v), nd), p10=round(v[n//10], nd), p90=round(v[n*9//10], nd), mean=round(sum(v)/n, nd))
def num(x):
    try: return float(x)
    except: return None
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d] = 'EagleG5'
devorder = lambda d: (d.startswith('4F'), int(re.sub(r'\D', '', d) or 0))
lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
R = [json.loads(l) for l in open(f'{A}/wafers.jsonl', encoding='utf-8')]
F = {}
# ── 0. coverage ──
F['cov'] = dict(lots=len(lots), wafers=len(R), devices=len({r['dev'] for r in R}), jobs=len({r['job'] for r in R}),
                has_ini=sum(r['has_ini'] for r in R), has_sl=sum(r['has_sl'] for r in R), has_pi=sum(r['has_pi'] for r in R),
                in_report=sum(1 for r in R if r['rfault'] != '' or r['rstatus'] != ''),
                day_from=min(r['start'] for r in R if r['start'])[:10], day_to=max(r['start'] for r in R if r['start'])[:10])
# per wafer derived
for r in R:
    s, e, ss = P(r['start']), P(r['end']), P(r['scanstart'])
    b0, b1 = pt(lots[r['lot_id']]['bs']), pt(lots[r['lot_id']]['be'])
    r['_s'], r['_e'], r['_ss'] = s, e, ss
    r['_inwin'] = bool(s and b0 and b1 and b0.timestamp() - 600 <= s.timestamp() <= b1.timestamp() + 600)
    r['_wt'] = (e - s).total_seconds() if s and e else None
    r['_load'] = (ss - s).total_seconds() if s and ss else None
    r['_dur'] = (num(r['dur']) or 0) / 1000 if r['dur'] else None
    r['_post'] = ((e - ss).total_seconds() - r['_dur']) if (ss and e and r['_dur'] is not None) else None
    try: r['_def'] = sum(int(float(v)) for v in r['pidef'].values()) if r['pidef'] else None
    except: r['_def'] = None
    r['_fam'] = family(r['job'])
    r['_gen'] = GEN.get(r['dev'], '?')
    r['_multi'] = r['nrec'] >= 2
    ex = sorted((P(v), k) for k, v in r['ext'].items() if v)
    r['_ex'] = ex
F['stale'] = dict(inwin=sum(r['_inwin'] for r in R), total=sum(1 for r in R if r['_s']))
RW = [r for r in R if r['_inwin'] and r['_wt'] is not None and 0 < r['_wt'] < 7200]
# ── 1. time structure by family × gen ──
ts = collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    k = (r['_fam'] or '기타', r['_gen'])
    ts[k]['wafer'].append(r['_wt']); ts[k]['load'].append(r['_load']); ts[k]['scan'].append(r['_dur']); ts[k]['post'].append(r['_post'])
F['time_fam'] = [dict(fam=k[0], gen=k[1], n=len(v['wafer']), wafer=q(v['wafer'], 0), load=q(v['load'], 0), scan=q(v['scan'], 0), post=q(v['post'], 0))
                 for k, v in sorted(ts.items(), key=lambda kv: -len(kv[1]['wafer'])) if len(v['wafer']) >= 30]
# per device x family (fam only)
td = collections.defaultdict(list)
for r in RW:
    if r['_fam']: td[(r['_fam'], r['dev'])].append(r['_wt'])
F['time_dev'] = [dict(fam=k[0], dev=k[1], gen=GEN.get(k[1]), **q(v, 0)) for k, v in sorted(td.items()) if len(v) >= 20]
# ── 2. inter-wafer gap & lot overhead ──
bylot = collections.defaultdict(list)
for r in RW: bylot[r['lot_id']].append(r)
gaps = []; lot_ov = []; lotsz = collections.defaultdict(list)
for lid, rs in bylot.items():
    rs.sort(key=lambda r: r['_s'])
    for a, b in zip(rs, rs[1:]):
        g = (b['_s'] - a['_e']).total_seconds()
        if -5 < g < 3600: gaps.append(g)
    l = lots[lid]; b0, b1 = pt(l['bs']), pt(l['be'])
    if b0 and b1 and len(rs) >= 2:
        span = (b1 - b0).total_seconds(); busy = sum(r['_wt'] for r in rs)
        if span > 0: lot_ov.append(dict(n=len(rs), span=span, busy=busy, head=(rs[0]['_s'] - b0).total_seconds(), tail=(b1 - rs[-1]['_e']).total_seconds()))
    lotsz[l['job']].append(len(rs))
F['gap'] = q(gaps, 0)
F['lot_overhead'] = dict(n=len(lot_ov), busy_pct=q([100 * x['busy'] / x['span'] for x in lot_ov], 1), head=q([x['head'] for x in lot_ov], 0), tail=q([x['tail'] for x in lot_ov], 0))
F['lot_size'] = q([len(v) for v in bylot.values()], 0)
F['lot_size_hist'] = collections.Counter(min(len(v), 26) for v in bylot.values())
# ── 3. device daily activity / idle (from batch windows) ──
devb = collections.defaultdict(list)
for l in lots.values():
    b0, b1 = pt(l['bs']), pt(l['be'])
    if b0 and b1 and b1 > b0: devb[l['device']].append((b0, b1))
idle = {}
hour_heat = collections.defaultdict(lambda: [0.0] * 24)   # dev -> hours busy by hour-of-day
for dev, bs in devb.items():
    bs.sort(); g = []
    for (a0, a1), (b0, b1) in zip(bs, bs[1:]):
        gg = (b0 - a1).total_seconds() / 60
        if gg > 0: g.append(gg)
    idle[dev] = dict(n=len(bs), gap_med=round(st.median(g), 1) if g else None, gap_p90=round(sorted(g)[len(g)*9//10], 1) if g else None,
                     gaps_over_60=sum(1 for x in g if x > 60), gaps_over_240=sum(1 for x in g if x > 240),
                     busy_h=round(sum((b1 - b0).total_seconds() for b0, b1 in bs) / 3600, 1), days=len({b0.date() for b0, _ in bs}))
    for b0, b1 in bs:
        t = b0
        while t < b1:
            nxt = min(b1, (t + dt.timedelta(hours=1)).replace(minute=0, second=0))
            hour_heat[dev][t.hour] += (nxt - t).total_seconds() / 3600; t = nxt
F['idle'] = {d: idle[d] for d in sorted(idle, key=devorder)}
F['hour_heat'] = {d: [round(x, 1) for x in hour_heat[d]] for d in sorted(hour_heat, key=devorder)}
# weekday activity
wd = collections.Counter(); wdh = collections.Counter()
for dev, bs in devb.items():
    for b0, b1 in bs: wd[b0.weekday()] += 1; wdh[b0.weekday()] += (b1 - b0).total_seconds() / 3600
F['weekday'] = [dict(d=i, lots=wd[i], hours=round(wdh[i], 1)) for i in range(7)]
# ── 4. defects ──
dq = collections.defaultdict(list)
for r in RW:
    if r['_def'] is not None and r['_fam']: dq[(r['_fam'], r['dev'])].append(r['_def'])
F['def_dev'] = [dict(fam=k[0], dev=k[1], gen=GEN.get(k[1]), **q(v, 0)) for k, v in sorted(dq.items()) if len(v) >= 20]
# cap hits: ProductionInfo per-recipe exactly 3000 / 200000 ... ScanLog DefectsNum == cap
caphit = collections.Counter(); capn = collections.Counter()
for r in RW:
    if r['_def'] is None: continue
    capn[r['dev']] += 1
    if r['_def'] in (3000, 2000, 1999, 200000) or (r['sldef'] and num(r['sldef']) in (3000.0, 2000.0)): caphit[r['dev']] += 1
F['caphit'] = {d: dict(n=capn[d], hit=caphit[d]) for d in sorted(capn, key=devorder) if caphit[d]}
# defect vs time (all fam)
db = collections.defaultdict(list)
for r in RW:
    if r['_def'] is None: continue
    k = 0 if r['_def'] < 10 else 1 if r['_def'] < 100 else 2 if r['_def'] < 1000 else 3
    db[(r['_fam'] and r['_fam'].split()[1][:3], k)].append(r['_wt'])
F['def_time'] = [dict(fam=k[0] or '기타', bucket=['<10', '10~99', '100~999', '1000+'][k[1]], **q(v, 0)) for k, v in sorted(db.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])) if len(v) >= 30]
# pareto classes
par = collections.Counter(); parn = collections.Counter()
for r in RW:
    for k, v in r['pareto'].items():
        x = num(v)
        if x: par[k] += x; parn[k] += 1
F['pareto'] = [dict(cls=k, total=round(v), wafers=parn[k]) for k, v in par.most_common(12)]
# ── 5. review lead time ──
rv = collections.defaultdict(list); unrev = collections.Counter(); tot = collections.Counter(); rv_hour = collections.Counter()
for r in R:
    if not r['has_sl'] or not r['_e']: continue
    tot[r['dev']] += 1
    v = P(r['verify'])
    if v:
        h = (v - r['_e']).total_seconds() / 3600
        if -1 < h < 2000: rv[r['dev']].append(h); rv_hour[v.hour] += 1
    else: unrev[r['dev']] += 1
F['review'] = [dict(dev=d, gen=GEN.get(d), total=tot[d], unreviewed=unrev[d], **(q(rv[d], 1) or {})) for d in sorted(tot, key=devorder)]
F['review_hour'] = [rv_hour[h] for h in range(24)]
F['review_all'] = q([x for v in rv.values() for x in v], 1)
# ── 6. rescan / repeated wafers ──
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s']: seen[(r['job'], r['wid'])].append((r['_s'], r['dev'], r['lot'], r['lot_id']))
rep = {k: sorted(v) for k, v in seen.items() if len(v) > 1}
rescan_dev = collections.Counter(); rescan_fam = collections.Counter(); tot_dev = collections.Counter()
for r in R:
    if r['wid']: tot_dev[r['dev']] += 1
for k, v in rep.items():
    for s, dev, lot, lid in v[1:]: rescan_dev[dev] += 1; rescan_fam[family(k[0]) or '기타'] += 1
F['rescan'] = dict(repeated_wafers=len(rep), extra_scans=sum(len(v) - 1 for v in rep.values()), total_wafers=sum(tot_dev.values()),
                   by_dev={d: dict(n=tot_dev[d], extra=rescan_dev[d]) for d in sorted(tot_dev, key=devorder)}, by_fam=dict(rescan_fam.most_common(12)))
# lot names with RE / RESCAN / REWORK
F['lot_marks'] = collections.Counter(m for l in lots.values() for m in (['RE'] if re.search(r'(^|[\s_-])(RE|RESCAN)([\s_-]|$)', l['lot'], re.I) else []) + (['REWORK'] if 'REWORK' in l['lot'].upper() else []) + (['TEST'] if re.search(r'(^|[\s_-])TEST([\s_-]|$)', l['lot'], re.I) else []))
# ── 7. report statuses / errors ──
stc = collections.Counter(); errdev = collections.Counter(); repn = collections.Counter()
for r in R:
    s = (r['rstatus'] or '').strip()
    if not s: continue
    repn[r['dev']] += 1
    key = 'Pass' if s.lower() == 'pass' else 'Fail' if s.lower() == 'fail' else re.sub(r'\d+', '#', s)[:60]
    stc[key] += 1
    if key not in ('Pass', 'Fail'): errdev[r['dev']] += 1
F['status'] = stc.most_common(25)
F['errdev'] = {d: dict(n=repn[d], err=errdev[d]) for d in sorted(repn, key=devorder)}
# ── 8. data quality ──
fm = collections.Counter()
for r in R:
    if r['_def'] is None or not r['rfault'].strip().isdigit(): continue
    fm['match' if int(r['rfault']) == r['_def'] else ('stale' if not r['_inwin'] else 'mismatch')] += 1
F['faults_match'] = dict(fm)
F['ops'] = collections.Counter(r['op'] for r in R if r['op']).most_common(8)
F['machines'] = {d: sorted({r['machine'] for r in R if r['dev'] == d and r['machine']}) for d in sorted({r['dev'] for r in R}, key=devorder)}
F['slver'] = collections.Counter(r['slver'] for r in R if r['slver']).most_common(5)
F['moved_only'] = 0
F['partial'] = dict(cass_lt_25=sum(1 for v in bylot.values() if v and v[0]['cass'] and v[0]['cass'] < 25), lots=len(bylot))
# ── 9. multi recipe ──
mr = collections.defaultdict(list); order = collections.Counter()
for r in RW:
    if len(r['_ex']) == 2 and r['_e']:
        (t1, k1), (t2, k2) = r['_ex']
        mr[(r['_fam'] or '기타', k1, k2)].append(((t2 - t1).total_seconds(), (r['_e'] - t2).total_seconds()))
        order[(r['_fam'] or '기타', k1 + '→' + k2)] += 1
F['multi'] = [dict(fam=k[0], first=k[1], second=k[2], n=len(v), first_s=q([a for a, _ in v], 0), second_s=q([b for _, b in v], 0)) for k, v in sorted(mr.items(), key=lambda kv: -len(kv[1])) if len(v) >= 20]
F['multi_order'] = [dict(fam=k[0], order=k[1], n=v) for k, v in order.most_common(12)]
# ── 10. alignment / focus drift per device over days ──
aff = collections.defaultdict(lambda: collections.defaultdict(list)); foc = collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    a = num(r['stdaff'])
    if a is not None and 0 <= a < 50: aff[r['dev']][r['start'][:10]].append(a)
    for k, v in r['pos'].items():
        x = num(v)
        if x and r['_fam']: foc[(r['dev'], k)][r['start'][:10]].append(x)
F['aff_dev'] = {d: dict(med=round(st.median([x for v in dd.values() for x in v]), 2), p90=round(sorted([x for v in dd.values() for x in v])[int(len([x for v in dd.values() for x in v])*.9)], 2), n=sum(len(v) for v in dd.values()),
                       days=[(day, round(st.median(v), 2)) for day, v in sorted(dd.items())]) for d, dd in sorted(aff.items(), key=lambda kv: devorder(kv[0]))}
F['focus_drift'] = [dict(dev=k[0], recipe=k[1], n=sum(len(v) for v in dd.values()), days=[(day, round(st.median(v), 1)) for day, v in sorted(dd.items())],
                         rng=round(max(st.median(v) for v in dd.values()) - min(st.median(v) for v in dd.values()), 1))
                    for k, dd in foc.items() if len(dd) >= 5 and sum(len(v) for v in dd.values()) >= 50]
F['focus_drift'].sort(key=lambda x: -x['rng'])
# ── 11. daily throughput per device ──
daily = collections.defaultdict(lambda: collections.defaultdict(int))
for r in R:
    if r['_s']: daily[r['dev']][r['start'][:10]] += 1
F['daily'] = {d: dict(sorted(v.items())) for d, v in sorted(daily.items(), key=lambda kv: devorder(kv[0]))}
json.dump(F, open(f'{A}/facts.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
print('ok', F['cov'], F['stale'])
