"""2차 패턴 분석 — 재스캔 · 레시피 순서 · G5 오버헤드 · 유휴 · 소형 Lot · STALE · 다중 Report · 복구 시간 → facts4.json"""
import sys, os, re, json, collections, statistics as st, datetime as dt
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
for r in R:
    r['_s'], r['_e'], r['_ss'] = P(r['start']), P(r['end']), P(r['scanstart'])
    r['_wt'] = (r['_e'] - r['_s']).total_seconds() if r['_s'] and r['_e'] else None
    r['_load'] = (r['_ss'] - r['_s']).total_seconds() if r['_s'] and r['_ss'] else None
    r['_dur'] = (num(r['dur']) or 0) / 1000 if r['dur'] else None
    r['_post'] = ((r['_e'] - r['_ss']).total_seconds() - r['_dur']) if (r['_ss'] and r['_e'] and r['_dur'] is not None) else None
    r['_fam'] = family(r['job']); r['_gen'] = GEN.get(r['dev'], '?')
    try: r['_def'] = sum(int(float(v)) for v in r['pidef'].values()) if r['pidef'] else None
    except: r['_def'] = None
    # which report window contains this wafer (lot may have several reports)
    reps = lots[r['lot_id']]['reports']; r['_rep'] = None
    if r['_s']:
        for rp in reps:
            b0, b1 = pt(rp['bs']), pt(rp['be'])
            if b0 and b1 and b0.timestamp() - 600 <= r['_s'].timestamp() <= b1.timestamp() + 600: r['_rep'] = rp; break
    r['_inwin'] = r['_rep'] is not None
# ── K. STALE (any report of the lot) ──
st_dev = collections.defaultdict(lambda: [0, 0])
for r in R:
    if r['_s']: st_dev[r['dev']][0] += 1; st_dev[r['dev']][1] += (not r['_inwin'])
F['stale_any'] = dict(total=sum(v[0] for v in st_dev.values()), stale=sum(v[1] for v in st_dev.values()),
                      by_dev={d: dict(n=v[0], stale=v[1], pct=round(100*v[1]/v[0], 1)) for d, v in sorted(st_dev.items(), key=lambda kv: devorder(kv[0]))})
# how old are stale INIs relative to the lot's latest report end (days)
age = []
for r in R:
    if r['_s'] and not r['_inwin']:
        ends = [pt(rp['be']) for rp in lots[r['lot_id']]['reports'] if pt(rp['be'])]
        if ends: age.append((r['_s'] - max(ends)).total_seconds() / 86400)
F['stale_age_days'] = dict(after=q([a for a in age if a > 0], 1), before=q([-a for a in age if a <= 0], 1))
RW = [r for r in R if r['_inwin'] and r['_wt'] is not None and 0 < r['_wt'] < 7200]
# ── L. lots with several reports ──
multi_rep = [l for l in lots.values() if len(l['reports']) > 1]
mr_stats = []
for l in multi_rep:
    reps = sorted(l['reports'], key=lambda rp: pt(rp['bs']) or dt.datetime.min)
    gaps = []
    for a, b in zip(reps, reps[1:]):
        ea, sb = pt(a['be']), pt(b['bs'])
        if ea and sb: gaps.append((sb - ea).total_seconds() / 60)
    mr_stats.append(dict(n=len(reps), first_n=reps[0]['n'], sizes=[rp['n'] for rp in reps], gaps=gaps))
F['multi_report'] = dict(lots=len(multi_rep), of=len(lots), reports_extra=sum(m['n'] - 1 for m in mr_stats),
                         gap_min=q([g for m in mr_stats for g in m['gaps']], 0),
                         gap_hist={'<10분': sum(1 for m in mr_stats for g in m['gaps'] if g < 10), '10분~1시간': sum(1 for m in mr_stats for g in m['gaps'] if 10 <= g < 60),
                                   '1~24시간': sum(1 for m in mr_stats for g in m['gaps'] if 60 <= g < 1440), '1일 이상': sum(1 for m in mr_stats for g in m['gaps'] if g >= 1440)},
                         first_size_hist=collections.Counter(min(m['first_n'], 25) for m in mr_stats).most_common(8))
# ── A. repeated wafer scans ──
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s']: seen[(r['job'], r['wid'])].append(r)
cls = collections.Counter(); cls_h = collections.Counter(); gapbins = collections.Counter(); first_status = collections.Counter(); re_lotmark = collections.Counter()
by_dev_cls = collections.defaultdict(collections.Counter); by_fam_cls = collections.defaultdict(collections.Counter)
pass_pass = 0; ex_total = 0; hours_extra = 0
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]):
        if a['lot_id'] == b['lot_id']: c = '같은 Lot 안(재시도)'
        elif a['dev'] == b['dev']: c = '같은 장비 · 다른 Lot'
        else: c = '다른 장비'
        cls[c] += 1; ex_total += 1
        if b['_wt']: cls_h[c] += b['_wt'] / 3600; hours_extra += b['_wt'] / 3600
        g = (b['_s'] - a['_e']).total_seconds() / 3600 if a['_e'] else None
        if g is not None: gapbins['<1시간' if g < 1 else '1~24시간' if g < 24 else '1~7일' if g < 168 else '7일 이상'] += 1
        sa = (a['rstatus'] or '').strip().lower()
        first_status['Pass' if sa == 'pass' else ('없음' if not sa else '오류·중단')] += 1
        if sa == 'pass' and (b['rstatus'] or '').strip().lower() == 'pass': pass_pass += 1
        by_dev_cls[b['dev']][c] += 1; by_fam_cls[b['_fam'] or '기타'][c] += 1
        re_lotmark['RE/RESCAN/REWORK 표기' if re.search(r'(^|[\s_-])(RE|RESCAN|REWORK)([\s_-]|$)', b['lot'], re.I) else '표기 없음'] += 1
F['repeat'] = dict(extra=ex_total, hours=round(hours_extra, 1), cls=dict(cls), cls_hours={k: round(v, 1) for k, v in cls_h.items()}, gap=dict(gapbins), first_status=dict(first_status),
                   pass_pass=pass_pass, lotmark=dict(re_lotmark), by_dev={d: dict(c) for d, c in sorted(by_dev_cls.items(), key=lambda kv: devorder(kv[0]))},
                   by_fam={f: dict(c) for f, c in sorted(by_fam_cls.items(), key=lambda kv: -sum(kv[1].values()))})
# repeat examples: job with most 'same device other lot' repeats
jobrep = collections.Counter()
for k, v in seen.items():
    if len(v) >= 2: jobrep[k[0]] += len(v) - 1
F['repeat_jobs'] = jobrep.most_common(15)
# ── B. recipe order vs total wafer time (same device, same fam) ──
ordt = collections.defaultdict(list)
for r in RW:
    ex = sorted((P(v), k) for k, v in r['ext'].items() if v)
    if len(ex) == 2 and r['_fam'] and 'PI' in r['_fam']:
        ordt[(r['_fam'], r['dev'], ex[0][1] + '→' + ex[1][1])].append(r['_wt'])
F['order_time'] = [dict(fam=k[0], dev=k[1], order=k[2], **q(v, 0)) for k, v in sorted(ordt.items()) if len(v) >= 30]
# ── C. overhead per device (fam) ──
ov = collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    f = r['_fam'] or '기타'
    ov[(r['dev'], f)]['load'].append(r['_load']); ov[(r['dev'], f)]['post'].append(r['_post']); ov[(r['dev'], f)]['scan'].append(r['_dur']); ov[(r['dev'], f)]['wt'].append(r['_wt'])
F['overhead_dev'] = [dict(dev=k[0], gen=GEN.get(k[0]), fam=k[1], n=len(v['wt']), load=q(v['load'], 0)['med'], post=q(v['post'], 0)['med'], scan=q(v['scan'], 0)['med'], wt=q(v['wt'], 0)['med'],
                          scan_share=round(100 * (q(v['scan'], 0)['med'] or 0) / q(v['wt'], 0)['med'], 0))
                     for k, v in sorted(ov.items(), key=lambda kv: (devorder(kv[0][0]), kv[0][1])) if len(v['wt']) >= 50 and q(v['load'], 0) and q(v['post'], 0)]
# gen-level overhead share
gs = collections.defaultdict(lambda: collections.defaultdict(float))
for r in RW:
    if r['_load'] is not None and r['_post'] is not None and r['_dur'] is not None:
        g = gs[r['_gen']]; g['load'] += r['_load']; g['post'] += r['_post']; g['scan'] += r['_dur']; g['n'] += 1
F['gen_share'] = {g: dict(n=int(v['n']), load_h=round(v['load']/3600), post_h=round(v['post']/3600), scan_h=round(v['scan']/3600),
                          scan_pct=round(100*v['scan']/(v['load']+v['post']+v['scan']), 1)) for g, v in gs.items()}
# ── E. idle gaps by hour / weekday; fleet busy by hour ──
devb = collections.defaultdict(list)
for l in lots.values():
    for rp in l['reports']:
        b0, b1 = pt(rp['bs']), pt(rp['be'])
        if b0 and b1 and b1 > b0 and b0 >= dt.datetime(2026, 9, 9): devb[l['device']].append((b0, b1))
gap_hour = collections.Counter(); gap_hour_min = collections.Counter(); long_gap_hour = collections.Counter(); gap_wd = collections.Counter(); gaps_all = []
for dev, bs in devb.items():
    bs.sort()
    # merge overlapping
    m = []
    for b0, b1 in bs:
        if m and b0 <= m[-1][1]: m[-1][1] = max(m[-1][1], b1)
        else: m.append([b0, b1])
    for (a0, a1), (b0, b1) in zip(m, m[1:]):
        g = (b0 - a1).total_seconds() / 60
        if g <= 0: continue
        gaps_all.append((dev, a1, g))
        gap_hour[a1.hour] += 1; gap_hour_min[a1.hour] += g
        if g > 60: long_gap_hour[a1.hour] += 1
        gap_wd[a1.weekday()] += g / 60
F['gap_by_hour'] = [dict(h=h, n=gap_hour[h], minutes=round(gap_hour_min[h]), over60=long_gap_hour[h]) for h in range(24)]
F['gap_by_weekday_hours'] = [round(gap_wd[i]) for i in range(7)]
# fleet busy fraction per hour-of-day (merged windows), per device days
hh = collections.defaultdict(lambda: [0.0]*24); days_dev = {}
for dev, bs in devb.items():
    bs.sort(); m = []
    for b0, b1 in bs:
        if m and b0 <= m[-1][1]: m[-1][1] = max(m[-1][1], b1)
        else: m.append([b0, b1])
    for b0, b1 in m:
        t = b0
        while t < b1:
            nxt = min(b1, (t + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0))
            hh[dev][t.hour] += (nxt - t).total_seconds() / 3600; t = nxt
    days_dev[dev] = (max(b1 for _, b1 in m) - min(b0 for b0, _ in m)).total_seconds() / 86400
F['busy_hour_pct'] = {d: [round(100 * hh[d][h] / days_dev[d], 0) for h in range(24)] for d in sorted(hh, key=devorder)}
F['busy_pct_dev'] = {d: round(100 * sum(hh[d]) / (days_dev[d] * 24), 1) for d in sorted(hh, key=devorder)}
fleet = [sum(hh[d][h] for d in hh) / sum(days_dev.values()) * 100 for h in range(24)]
F['fleet_busy_hour_pct'] = [round(x, 1) for x in fleet]
# gap sizes: how much idle is in gaps <30min vs 30-120 vs >120 (minutes total)
gb = collections.Counter()
for dev, t, g in gaps_all: gb['<30분' if g < 30 else '30분~2시간' if g < 120 else '2~8시간' if g < 480 else '8시간 이상'] += g / 60
F['gap_hours_by_size'] = {k: round(v) for k, v in gb.items()}
F['gap_count_by_size'] = dict(collections.Counter('<30분' if g < 30 else '30분~2시간' if g < 120 else '2~8시간' if g < 480 else '8시간 이상' for _, _, g in gaps_all))
# ── G. small lots ──
bylot = collections.defaultdict(list)
for r in RW: bylot[r['lot_id']].append(r)
small = collections.Counter(); small_h = collections.Counter(); small_jobs = collections.Counter(); ovh = collections.defaultdict(list)
for lid, rs in bylot.items():
    l = lots[lid]; n = len(rs)
    rs.sort(key=lambda r: r['_s'])
    b0, b1 = pt(l['bs']), pt(l['be'])
    if not (b0 and b1): continue
    span = (b1 - b0).total_seconds(); busy = sum(r['_wt'] for r in rs)
    k = '1장' if n == 1 else '2~3장' if n <= 3 else '4~9장' if n <= 9 else '10~24장' if n <= 24 else '25장'
    small[k] += 1; small_h[k] += span / 3600
    if span > 0 and busy <= span: ovh[k].append((span - busy) / n)
    if n <= 3: small_jobs[family(l['job']) or re.sub(r'[_\s-]+\d{4}$', '', l['job'])[:30]] += 1
F['lot_size_class'] = {k: dict(lots=small[k], hours=round(small_h[k]), overhead_per_wafer_s=q(ovh[k], 0)['med'] if ovh[k] else None) for k in ['1장', '2~3장', '4~9장', '10~24장', '25장']}
F['small_lot_jobs'] = small_jobs.most_common(12)
# ── T. error → recovery ──
err_rows = [r for r in R if r['rstatus'] and r['rstatus'].strip().lower() not in ('pass', 'fail', '')]
rec = collections.defaultdict(list)
for r in err_rows:
    if not r['_e']: continue
    nxt = [b0 for b0, b1 in devb.get(r['dev'], []) if b0 > r['_e']]
    if nxt: rec[re.sub(r'\d+', '#', r['rstatus'].strip())[:40]].append((min(nxt) - r['_e']).total_seconds() / 60)
F['recovery_min'] = {k: q(v, 0) for k, v in sorted(rec.items(), key=lambda kv: -len(kv[1])) if len(v) >= 5}
# ── M. slow device ratio per fam job ──
fam_med = collections.defaultdict(list); dev_fam = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and r['_dur']: fam_med[(r['_fam'], r['_gen'])].append(r['_dur']); dev_fam[(r['_fam'], r['_gen'], r['dev'])].append(r['_dur'])
ratio = []
for k, v in dev_fam.items():
    if len(v) >= 50:
        fm = st.median(fam_med[k[:2]]); dm = st.median(v)
        ratio.append(dict(fam=k[0], gen=k[1], dev=k[2], n=len(v), dev_med=round(dm), fam_med=round(fm), ratio=round(dm / fm, 2)))
ratio.sort(key=lambda x: -x['ratio'])
F['scan_ratio'] = ratio
# ── N. wafers per busy hour & night share ──
night = collections.Counter(); tot = collections.Counter()
for dev, bs in devb.items():
    for b0, b1 in bs:
        tot[dev] += 1; night[dev] += (b0.hour >= 22 or b0.hour < 6)
F['night_start_pct'] = round(100 * sum(night.values()) / sum(tot.values()), 1)
# ── R. review backlog ──
rv_wd = collections.Counter(); unrev_fam = collections.defaultdict(lambda: [0, 0])
for r in R:
    if not r['has_sl'] or not r['_e']: continue
    f = r['_fam'] or '기타'; unrev_fam[f][0] += 1
    v = P(r['verify'])
    if v: rv_wd[v.weekday()] += 1
    else: unrev_fam[f][1] += 1
F['review_weekday'] = [rv_wd[i] for i in range(7)]
F['unreviewed_fam'] = {f: dict(n=v[0], unrev=v[1], pct=round(100*v[1]/v[0], 1)) for f, v in sorted(unrev_fam.items(), key=lambda kv: -kv[1][0])}
# review lead vs defects: does defect count affect review time?
rvd = collections.defaultdict(list)
for r in R:
    v = P(r['verify'])
    if v and r['_e'] and r['_def'] is not None:
        h = (v - r['_e']).total_seconds() / 3600
        if -1 < h < 2000: rvd['<10' if r['_def'] < 10 else '10~99' if r['_def'] < 100 else '100+'].append(h)
F['review_by_defect'] = {k: q(v, 1) for k, v in rvd.items()}
# ── Q. per-wafer time by cassette fill (within fam) ──
# ── defect per wafer per family (fleet) ──
dq = collections.defaultdict(list)
for r in RW:
    if r['_def'] is not None: dq[r['_fam'] or '기타'].append(r['_def'])
F['def_fam'] = {f: q(v, 0) for f, v in sorted(dq.items(), key=lambda kv: -len(kv[1]))}
# share of wafers with 0 defects
F['zero_def_pct'] = round(100 * sum(1 for r in RW if r['_def'] == 0) / sum(1 for r in RW if r['_def'] is not None), 1)
# ── daily fleet wafers & busy ──
daily_w = collections.Counter(); daily_b = collections.Counter()
for r in R:
    if r['_s'] and r['_s'] >= dt.datetime(2026, 9, 9): daily_w[r['start'][:10]] += 1
for dev, bs in devb.items():
    for b0, b1 in bs: daily_b[b0.strftime('%Y-%m-%d')] += (b1 - b0).total_seconds() / 3600
F['daily_fleet'] = [dict(day=d, wafers=daily_w[d], busy_h=round(daily_b[d])) for d in sorted(daily_w)]
json.dump(F, open(f'{A}/facts4.json', 'w', encoding='utf-8'), ensure_ascii=False, default=str)
print('ok', F['stale_any']['total'], F['stale_any']['stale'], F['repeat']['extra'], F['multi_report'])
