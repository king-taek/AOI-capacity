"""Refinements + new analyses: CR excluding confounded pairs, repeat summary, changeover gaps, capacity quadrant, recipe switch time, cap check, AOI-17 params."""
import sys, json, re, collections, statistics as st, datetime as dt
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
lots, AC, R = load()
RW = [r for r in R if r['_in'] and r['_wt'] is not None and 0 < r['_wt'] < 7200]
OUT = {}
# ---- CR refined: matched same device+job+af, drop pairs where scan duration also moved > 20% (recipe change confound)
dj = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(load=[], scan=[])))
for r in RW:
    if r['_load'] is None or r['lot_id'] not in AC: continue
    d = dj[(r['dev'], r['job'], r['_af'])][r['_cr'].lower() == 'wafer']; d['load'].append(r['_load']); d['scan'].append(r['_dur'])
rows = []; h_all = 0; h_clean = 0; n_all = 0; n_clean = 0; conf = []
for k, d in dj.items():
    if len(d[True]['load']) >= 10 and len(d[False]['load']) >= 10:
        dl = st.median(d[True]['load']) - st.median(d[False]['load']); sw, sl = med(d[True]['scan']), med(d[False]['scan'])
        confounded = sw and sl and abs(sw - sl) / max(sl, 1) > 0.2
        n = len(d[True]['load']); h_all += max(0, dl) * n / 3600; n_all += n
        if not confounded: h_clean += max(0, dl) * n / 3600; n_clean += n
        else: conf.append(dict(dev=k[0], job=k[1][:40], n_w=n, delta_load=round(dl), scan_w=round(sw), scan_l=round(sl)))
cw = sum(1 for r in RW if r['_load'] is not None and r['_cr'].lower() == 'wafer')
OUT['cr_refined'] = dict(matched_h=round(h_all), matched_wafers=n_all, clean_h=round(h_clean), clean_wafers=n_clean, cr_wafer_wafers_total=cw,
                         extrapolated_clean_h=round(h_clean / n_clean * cw) if n_clean else None, confounded=sorted(conf, key=lambda x: -x['n_w'])[:6])
# per-gen clean delta (s/wafer) for the explanation
gd = collections.defaultdict(list)
for k, d in dj.items():
    if len(d[True]['load']) >= 10 and len(d[False]['load']) >= 10:
        sw, sl = med(d[True]['scan']), med(d[False]['scan'])
        if sw and sl and abs(sw - sl) / max(sl, 1) > 0.2: continue
        gd[GEN.get(k[0])].extend([st.median(d[True]['load']) - st.median(d[False]['load'])] * len(d[True]['load']))
OUT['cr_delta_by_gen'] = {g: dict(n=len(v), med=round(st.median(v)), p25=round(sorted(v)[len(v)//4]), p75=round(sorted(v)[len(v)*3//4])) for g, v in gd.items()}
# ---- Repeat summary into 3 buckets with hours
VALID = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9\-]{6,}$')
TOK = re.compile(r'(^|[\s_-])(RE|RESCAN|REWORK|R\d?)([\s_-]|$)', re.I); STEP = re.compile(r'(^|[\s_-])(DIA|SRD|3D|EDGE|BUMP|CENTER|PCM|SPT|2D)([\s_-]|$)', re.I)
core = lambda l: re.sub(r'[\s_-]+', '-', TOK.sub(r'\1\3', TOK.sub(r'\1\3', l))).strip('-').upper()
steps = lambda l: tuple(sorted(m.group(2).upper() for m in STEP.finditer(l)))
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s'] and VALID.match(r['wid']): seen[(r['job'], r['wid'])].append(r)
pairs = []
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]): pairs.append((a, b))
lp = collections.Counter((a['lot_id'], b['lot_id']) for a, b in pairs)
lotsize = collections.Counter(r['lot_id'] for r in R if r['_s'])
B = collections.Counter(); BH = collections.Counter(); detail = collections.Counter(); detailH = collections.Counter()
for a, b in pairs:
    wt = b['_wt'] / 3600 if b['_wt'] and 0 < b['_wt'] < 7200 else 0
    rec_diff = (a['recipe'] or '').strip() != (b['recipe'] or '').strip()
    istest = a['job'].upper().startswith('NO PATTERN') or 'TEST' in a['job'].upper() or re.search(r'(^|[\s_-])TEST([\s_-]|$)', a['lot'] + ' ' + b['lot'], re.I)
    sa = (a['rstatus'] or '').strip().lower()
    if a['lot_id'] == b['lot_id']: d = '같은 Lot 안 재시도'; bk = '진짜 재검사'
    elif istest: d = '테스트·모니터 웨이퍼'; bk = '테스트·모니터'
    elif steps(a['lot']) != steps(b['lot']) or rec_diff: d = '다른 검사 단계·레시피'; bk = '다른 검사(재검사 아님)'
    elif core(a['lot']) == core(b['lot']): d = '같은 Lot 다시(RE 표기)'; bk = '진짜 재검사'
    else:
        n = lp[(a['lot_id'], b['lot_id'])]
        d = 'Lot 통째로 다른 이름으로 다시' if n >= 20 and n / max(1, lotsize[a['lot_id']]) >= .8 else '일부 장만 다른 이름으로 다시'; bk = '진짜 재검사'
    B[bk] += 1; BH[bk] += wt; detail[d] += 1; detailH[d] += wt
OUT['repeat3'] = dict(total=len(pairs), hours=round(sum(BH.values())), buckets={k: dict(n=B[k], h=round(BH[k]), pct=round(100 * B[k] / len(pairs))) for k in B}, detail={k: dict(n=detail[k], h=round(detailH[k])) for k in detail})
# genuine re-inspection: first status
fs = collections.Counter()
for a, b in pairs:
    pass
# ---- N1: lot changeover gaps
devb = collections.defaultdict(list)
for l in lots.values():
    for rp in l['reports']:
        b0, b1 = rp['_b0'], rp['_b1']
        if b0 and b1 and b1 > b0 and b0 >= dt.datetime(2026, 9, 9): devb[l['device']].append((b0, b1, l['job'], l['error'], rp['n']))
gaps = []
for dev, bs in devb.items():
    bs.sort(); m = []
    for b0, b1, job, err, n in bs:
        if m and b0 <= m[-1][1]: m[-1][1] = max(m[-1][1], b1); m[-1][3] = m[-1][3] or err
        else: m.append([b0, b1, job, err, n])
    for (a0, a1, ja, ea, na), (b0, b1, jb, eb, nb) in zip(m, m[1:]):
        g = (b0 - a1).total_seconds() / 60
        if g <= 0: continue
        gaps.append(dict(dev=dev, g=g, same=(ja == jb), err=ea, hour=a1.hour, nb=nb))
short = [x for x in gaps if x['g'] < 120]
OUT['n1_summary'] = dict(gaps=len(gaps), short=len(short), short_h=round(sum(x['g'] for x in short) / 60),
                         same_job=q([x['g'] for x in short if x['same'] and not x['err']], 1), diff_job=q([x['g'] for x in short if not x['same'] and not x['err']], 1), after_error=q([x['g'] for x in short if x['err']], 1),
                         same_job_h=round(sum(x['g'] for x in short if x['same'] and not x['err']) / 60), diff_job_h=round(sum(x['g'] for x in short if not x['same'] and not x['err']) / 60), after_error_h=round(sum(x['g'] for x in short if x['err']) / 60))
# per device median (short gaps, non-error), and recoverable hours at fleet p25 per type
p25 = {t: sorted(x['g'] for x in short if x['same'] == t and not x['err'])[len([x for x in short if x['same'] == t and not x['err']]) // 4] for t in (True, False)}
OUT['n1_p25'] = {'same': round(p25[True], 1), 'diff': round(p25[False], 1)}
bydev = collections.defaultdict(list)
for x in short: bydev[x['dev']].append(x)
rows = []
for dev in sorted(bydev, key=devorder):
    v = bydev[dev]; s = [x['g'] for x in v if x['same'] and not x['err']]; d = [x['g'] for x in v if not x['same'] and not x['err']]
    rec = sum(max(0, x['g'] - p25[x['same']]) for x in v if not x['err']) / 60
    rows.append(dict(dev=dev, gen=GEN.get(dev), n=len(v), same_med=round(st.median(s), 1) if s else None, diff_med=round(st.median(d), 1) if d else None, same_n=len(s), diff_n=len(d), recover_h=round(rec)))
OUT['n1_dev'] = rows; OUT['n1_recover_total_h'] = round(sum(x['recover_h'] for x in rows))
# recoverable if every short gap were at fleet median instead (more conservative)
medg = {t: st.median([x['g'] for x in short if x['same'] == t and not x['err']]) for t in (True, False)}
OUT['n1_recover_at_median_h'] = round(sum(max(0, x['g'] - medg[x['same']]) for x in short if not x['err']) / 60)
OUT['n1_gap_hist'] = dict(collections.Counter('<5분' if x['g'] < 5 else '5~15분' if x['g'] < 15 else '15~30분' if x['g'] < 30 else '30~60분' if x['g'] < 60 else '1~2시간' for x in short))
OUT['n1_gap_hist_h'] = {k: round(v / 60) for k, v in collections.Counter().items()}
hh = collections.Counter()
for x in short: hh['<5분' if x['g'] < 5 else '5~15분' if x['g'] < 15 else '15~30분' if x['g'] < 30 else '30~60분' if x['g'] < 60 else '1~2시간'] += x['g'] / 60
OUT['n1_gap_hist_h'] = {k: round(v) for k, v in hh.items()}
# ---- N2: capacity quadrant: wafers per busy hour vs busy %
T0 = dt.datetime(2026, 9, 9); T1 = max(b1 for bs in devb.values() for _, b1, *_ in bs)
HRS = (T1 - T0).total_seconds() / 3600
cap = []
wcount = collections.Counter(r['dev'] for r in RW if r['_s'] >= T0)
wtmed = collections.defaultdict(list)
for r in RW:
    if r['_s'] >= T0: wtmed[r['dev']].append(r['_wt'])
for dev, bs in devb.items():
    bs.sort(); m = []
    for b0, b1, *_ in bs:
        if m and b0 <= m[-1][1]: m[-1][1] = max(m[-1][1], b1)
        else: m.append([b0, b1])
    busy = sum((b1 - b0).total_seconds() for b0, b1 in m) / 3600
    cap.append(dict(dev=dev, gen=GEN.get(dev), busy_pct=round(100 * busy / HRS, 1), wafers=wcount[dev], wph=round(wcount[dev] / busy, 1), wpd=round(wcount[dev] / (HRS / 24), 1), wt_med=round(st.median(wtmed[dev])) if wtmed[dev] else None,
                    wafer_share_of_busy=round(100 * sum(wtmed[dev]) / 3600 / busy, 1)))
cap.sort(key=lambda x: devorder(x['dev']))
OUT['n2'] = cap
fleet_wph = st.median([x['wph'] for x in cap]); fleet_busy = st.median([x['busy_pct'] for x in cap])
OUT['n2_medians'] = dict(wph=round(fleet_wph, 1), busy=round(fleet_busy, 1))
quad = collections.defaultdict(list)
for x in cap:
    quad[('느림' if x['wph'] < fleet_wph else '빠름') + '·' + ('한가' if x['busy_pct'] < fleet_busy else '바쁨')].append(x['dev'])
OUT['n2_quad'] = dict(quad)
# ---- N3: recipe switch time (x20→x5) per device and hours
sw = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and len(r['_ex']) == 2 and r['_dur']:
        (t1, k1), (t2, k2) = r['_ex']
        if k1.lower() == 'x20' and k2.lower() == 'x5': sw[r['dev']].append((t2 - t1).total_seconds() - r['_dur'])
rows = []
best = min(st.median(v) for v in sw.values() if len(v) >= 50)
for dev in sorted(sw, key=devorder):
    v = sw[dev]
    if len(v) < 30: continue
    m = st.median(v); rows.append(dict(dev=dev, n=len(v), switch_med=round(m), p25=round(sorted(v)[len(v)//4]), p75=round(sorted(v)[len(v)*3//4]), hours=round(sum(v) / 3600, 1), excess_h=round(sum(max(0, x - best) for x in v) / 3600, 1)))
OUT['n3'] = dict(best=round(best), rows=rows, total_h=round(sum(x['hours'] for x in rows)), excess_h=round(sum(x['excess_h'] for x in rows)))
# does switch time depend on CR/AF settings?
swset = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and len(r['_ex']) == 2 and r['_dur']:
        (t1, k1), (t2, k2) = r['_ex']
        if k1.lower() == 'x20' and k2.lower() == 'x5': swset[(r['dev'], r['_cr'], r['_af'])].append((t2 - t1).total_seconds() - r['_dur'])
OUT['n3_settings'] = [dict(dev=k[0], cr=k[1], af=k[2], n=len(v), switch=round(st.median(v))) for k, v in sorted(swset.items(), key=lambda kv: devorder(kv[0][0])) if len(v) >= 30]
# ---- cap check: per-recipe DefectsNum == cap
caph = collections.Counter(); capn = collections.Counter()
for r in RW:
    cp = r['_cap']
    if not cp or not r['pidef']: continue
    try: cpv = int(float(cp))
    except: continue
    for k, v in r['pidef'].items():
        try: x = int(float(v))
        except: continue
        capn[r['_fam'] or '기타'] += 1
        if x >= cpv: caph[r['_fam'] or '기타'] += 1
OUT['cap_hits'] = {f: dict(n=capn[f], hit=caph[f]) for f in capn if caph[f]}
# ---- AOI-17 Enhanced: parameter diffs vs other devices (params4 fam rows)
q4 = json.load(open(f'{A}/params4.json'))
pd = []
for x in q4['fam']:
    if 'Enhanced' not in x['family']: continue
    for row in x['rows']:
        if 'AOI-17' in row.get('dev_off', []): pd.append(dict(fam=x['family'], cat=row['cat'], key=row['key'][:70], cons=str(row['cons'])[:30], aoi17=str(row['vals'].get('AOI-17'))[:30]))
OUT['aoi17_param_off'] = dict(n=len(pd), by_cat=dict(collections.Counter(p['cat'] for p in pd)), sample=[p for p in pd if p['cat'] in ('광학', '검출 기준', '얼라인·포커스 설정')][:25])
# AOI-17 Enhanced recnames / recipe pixel: compare 'recnames' and 'pos'
rn = collections.defaultdict(collections.Counter)
for r in RW:
    if r['_fam'] and 'Enhanced' in r['_fam']: rn[r['dev']][tuple(sorted(x.strip() for x in r['recnames']))] += 1
OUT['aoi17_recnames'] = {d: c.most_common(2) for d, c in rn.items()}
json.dump(OUT, open(f'{F}/a3.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
for k, v in OUT.items(): print('==', k); print(json.dumps(v, ensure_ascii=False, default=str)[:3500])
