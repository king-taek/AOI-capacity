"""Audit claims 1-3: time decomposition, multi-recipe Duration semantics, CleanReference cost."""
import sys, json, collections, statistics as st
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
lots, AC, R = load()
RW = [r for r in R if r['_in'] and r['_wt'] is not None and 0 < r['_wt'] < 7200]
OUT = {}
G5 = 'EagleG5'
# ---------- Claim 1: gen shares as currently computed ----------
gs = collections.defaultdict(lambda: collections.defaultdict(float))
for r in RW:
    if r['_load'] is not None and r['_post'] is not None and r['_dur'] is not None:
        g = gs[r['_gen']]; g['load'] += r['_load']; g['post'] += r['_post']; g['scan'] += r['_dur']; g['n'] += 1
OUT['gen_share_asis'] = {g: dict(n=int(v['n']), load_h=round(v['load']/3600), post_h=round(v['post']/3600), scan_h=round(v['scan']/3600), scan_pct=round(100*v['scan']/(v['load']+v['post']+v['scan']), 1)) for g, v in gs.items()}
# ---------- Claim 2: what does Duration cover for 2-recipe wafers? ----------
# For each 2-recipe wafer: seg1 = t2 - t1 (first recipe incl. switch), seg2 = end - t2 (second recipe incl. post)
chk = collections.defaultdict(list)
for r in RW:
    if len(r['_ex']) == 2 and r['_dur'] and r['_e'] and r['_ss']:
        (t1, k1), (t2, k2) = r['_ex']
        seg1 = (t2 - t1).total_seconds(); seg2 = (r['_e'] - t2).total_seconds()
        off = (t1 - r['_ss']).total_seconds()
        fam = r['_fam'] or '기타'
        grp = 'RDL' if fam.startswith('TB500 RDL') else 'PI' if 'PI' in fam else '기타'
        chk[grp].append((r['_dur'], seg1, seg2, off, r['_post'], k1, k2, r['dev']))
for grp, v in chk.items():
    ratio1 = [d / s1 for d, s1, s2, *_ in v if s1 > 0]
    ratio_both = [d / (s1 + s2) for d, s1, s2, *_ in v if s1 + s2 > 0]
    bins = collections.Counter()
    for d, s1, s2, *_ in v:
        if s1 <= 0: continue
        x = d / s1
        bins['dur≈1st(0.8~1.05)' if 0.8 <= x <= 1.05 else 'dur<0.8·1st' if x < 0.8 else 'dur≈both(≥0.95·합)' if d >= 0.95 * (s1 + s2) else '그 사이'] += 1
    OUT.setdefault('dur_semantics', {})[grp] = dict(n=len(v), dur_over_seg1=q(ratio1, 2), dur_over_both=q(ratio_both, 2), bins=dict(bins),
                                                  scanstart_eq_ext1=round(100 * sum(1 for x in v if abs(x[3]) <= 2) / len(v), 1),
                                                  seg1=q([x[1] for x in v], 0), seg2=q([x[2] for x in v], 0), dur=q([x[0] for x in v], 0), post_asis=q([x[4] for x in v], 0))
# RDL: single-recipe x5 scans give the true x5 scan time
x5 = [r['_dur'] for r in RW if r['_fam'] and r['_fam'].startswith('TB500 RDL') and 'Swelling' not in r['_fam'] and r['nrec'] <= 1 and (r['recipe'] or '').strip().lower() == 'x5' and r['_dur']]
OUT['rdl_x5_single_dur'] = q(x5, 0)
# RDL per device: single post vs multi (post_asis, seg2, post_true = post_asis - seg2 + (seg2 - x5scan) ...) -> simpler: post_true_multi = (seg1 - dur) [switch] + (seg2 - x5_med)
x5m = st.median(x5) if x5 else 95
rp = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and 'Swelling' not in r['_fam'] and r['_post'] is not None and r['_dur']:
        if r['nrec'] >= 2 and len(r['_ex']) == 2:
            (t1, k1), (t2, k2) = r['_ex']; seg1 = (t2 - t1).total_seconds(); seg2 = (r['_e'] - t2).total_seconds()
            rp[(r['dev'], 'multi')].append(dict(post=r['_post'], seg2=seg2, switch=seg1 - r['_dur'], post_true=seg2 - x5m + (seg1 - r['_dur']), wt=r['_wt'], scan_both=r['_dur'] + x5m))
        elif r['nrec'] <= 1:
            rp[(r['dev'], 'single')].append(dict(post=r['_post'], wt=r['_wt'], scan=r['_dur']))
rows = []
for (dev, mode), v in sorted(rp.items(), key=lambda kv: (devorder(kv[0][0]), kv[0][1])):
    if len(v) < 30: continue
    d = dict(dev=dev, mode=mode, n=len(v), post_asis=round(med([x['post'] for x in v])))
    if mode == 'multi':
        d.update(seg2=round(med([x['seg2'] for x in v])), switch=round(med([x['switch'] for x in v])), post_true=round(med([x['post_true'] for x in v])))
    rows.append(d)
OUT['rdl_post_fixed'] = rows
# fleet-level G5 hours: how much of "post" is really second-recipe scanning?
g5 = dict(load=0.0, scan=0.0, post=0.0, second_scan=0.0, switch=0.0, n=0, n2=0)
for r in RW:
    if r['_gen'] != G5 or r['_load'] is None or r['_post'] is None or r['_dur'] is None: continue
    g5['n'] += 1; g5['load'] += r['_load']; g5['scan'] += r['_dur']
    if len(r['_ex']) == 2:
        (t1, k1), (t2, k2) = r['_ex']; seg1 = (t2 - t1).total_seconds(); seg2 = (r['_e'] - t2).total_seconds()
        g5['n2'] += 1
        # estimate second-recipe scan: seg2 minus a single-recipe post (use 20 s), switch = seg1 - dur (if positive)
        sw = max(0.0, seg1 - r['_dur']); sc2 = max(0.0, seg2 - 20)
        g5['switch'] += sw; g5['second_scan'] += sc2; g5['post'] += r['_post'] - sw - sc2
    else: g5['post'] += r['_post']
OUT['g5_hours_fixed'] = {k: (round(v / 3600) if k not in ('n', 'n2') else v) for k, v in g5.items()}
tot = g5['load'] + g5['scan'] + g5['post'] + g5['second_scan'] + g5['switch']
OUT['g5_hours_fixed']['scan_pct_asis'] = round(100 * g5['scan'] / tot, 1)
OUT['g5_hours_fixed']['scan_pct_fixed'] = round(100 * (g5['scan'] + g5['second_scan']) / tot, 1)
OUT['g5_hours_fixed']['overhead_h_fixed'] = round((g5['load'] + g5['post'] + g5['switch']) / 3600)
# same for the other gens (2-recipe share is small there)
for gen in ('EagleT', 'EagleTP', 'EAGLE'):
    a = dict(load=0.0, scan=0.0, post=0.0, sc2=0.0, sw=0.0, n2=0, n=0)
    for r in RW:
        if r['_gen'] != gen or r['_load'] is None or r['_post'] is None or r['_dur'] is None: continue
        a['n'] += 1; a['load'] += r['_load']; a['scan'] += r['_dur']
        if len(r['_ex']) == 2:
            (t1, k1), (t2, k2) = r['_ex']; seg1 = (t2 - t1).total_seconds(); seg2 = (r['_e'] - t2).total_seconds(); a['n2'] += 1
            sw = max(0.0, seg1 - r['_dur']); sc2 = max(0.0, seg2 - 20); a['sw'] += sw; a['sc2'] += sc2; a['post'] += r['_post'] - sw - sc2
        else: a['post'] += r['_post']
    t = a['load'] + a['scan'] + a['post'] + a['sc2'] + a['sw']
    OUT.setdefault('gen_fixed', {})[gen] = dict(n=a['n'], n2=a['n2'], scan_pct_fixed=round(100 * (a['scan'] + a['sc2']) / t, 1), load_h=round(a['load']/3600), post_h=round(a['post']/3600), sw_h=round(a['sw']/3600), sc2_h=round(a['sc2']/3600))
# G5 load under same settings (CR != Wafer, AF None) per gen, and the AF=Wafer effect on G5
inh = collections.defaultdict(list); afw = collections.defaultdict(list)
for r in RW:
    if r['_load'] is None: continue
    if r['_cr'].lower() != 'wafer' and r['_af'].lower() == 'none': inh[r['_gen']].append(r['_load'])
    if r['_cr'].lower() != 'wafer' and r['_af'].lower() == 'wafer': afw[r['_gen']].append(r['_load'])
OUT['load_same_settings'] = {g: q(v, 0) for g, v in inh.items()}
OUT['load_cr_lot_af_wafer'] = {g: q(v, 0) for g, v in afw.items()}
# G5 load by single vs multi recipe (same settings) - does multi change load?
lm = collections.defaultdict(list)
for r in RW:
    if r['_gen'] == G5 and r['_load'] is not None and r['_cr'].lower() != 'wafer': lm[('multi' if r['nrec'] >= 2 else 'single', r['_af'])].append(r['_load'])
OUT['g5_load_by_mode_af'] = {f'{k[0]}|af={k[1]}': q(v, 0) for k, v in lm.items()}
# ---------- Claim 3: CleanReferenceEvery=Wafer cost ----------
# (a) as-is: per (fam, gen) median base vs CR=Wafer
base = collections.defaultdict(list); wl = collections.defaultdict(list)
for r in RW:
    if r['_load'] is None or r['lot_id'] not in AC: continue
    k = (r['_fam'] or '기타', r['_gen'])
    (wl if r['_cr'].lower() == 'wafer' else base)[k].append(r['_load'])
asis = []; tot_asis = 0
for k, v in wl.items():
    if len(v) >= 30 and len(base[k]) >= 30:
        ex = max(0, st.median(v) - st.median(base[k])) * len(v) / 3600; tot_asis += ex
        asis.append(dict(fam=k[0], gen=k[1], wafers=len(v), base=round(st.median(base[k])), wafer=round(st.median(v)), extra_h=round(ex, 1)))
OUT['cr_asis'] = dict(total_h=round(tot_asis), rows=sorted(asis, key=lambda x: -x['extra_h']))
# which jobs make up the CR=Wafer wafers (기타 EagleT etc.)
jw = collections.Counter(); jl = collections.defaultdict(list)
for r in RW:
    if r['_load'] is None or r['_cr'].lower() != 'wafer': continue
    jw[(r['dev'], r['job'])] += 1; jl[(r['dev'], r['job'])].append(r['_load'])
OUT['cr_wafer_top_devjob'] = [dict(dev=k[0], job=k[1][:45], gen=GEN.get(k[0]), n=n, load=round(st.median(jl[k]))) for k, n in jw.most_common(15)]
# (b) matched A: same device + same job, lots with both CR settings (same af)
dj = collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    if r['_load'] is None or r['lot_id'] not in AC: continue
    dj[(r['dev'], r['job'], r['_af'])][r['_cr'].lower() == 'wafer'].append(r['_load'])
mA = []; hA = 0; nA = 0; diffs = []
for k, d in dj.items():
    if len(d[True]) >= 10 and len(d[False]) >= 10:
        dlt = st.median(d[True]) - st.median(d[False]); diffs.append(dlt)
        hA += max(0, dlt) * len(d[True]) / 3600; nA += len(d[True])
        mA.append(dict(dev=k[0], job=k[1][:40], af=k[2], n_w=len(d[True]), n_l=len(d[False]), load_w=round(st.median(d[True])), load_l=round(st.median(d[False])), delta=round(dlt)))
mA.sort(key=lambda x: -x['n_w'])
OUT['cr_matched_devjob'] = dict(pairs=len(mA), wafers_covered=nA, extra_h=round(hA), delta_med=round(st.median(diffs)) if diffs else None, delta_q=q(diffs, 0), rows=mA[:20])
# (c) matched B: same job (any device within same gen), CR=Wafer vs CR=Lot/None, same af
jg = collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    if r['_load'] is None or r['lot_id'] not in AC: continue
    jg[(r['job'], r['_gen'], r['_af'])][r['_cr'].lower() == 'wafer'].append(r['_load'])
mB = []; hB = 0; nB = 0; dB = []
for k, d in jg.items():
    if len(d[True]) >= 10 and len(d[False]) >= 10:
        dlt = st.median(d[True]) - st.median(d[False]); dB.append(dlt); hB += max(0, dlt) * len(d[True]) / 3600; nB += len(d[True])
        mB.append(dict(job=k[0][:40], gen=k[1], af=k[2], n_w=len(d[True]), n_l=len(d[False]), load_w=round(st.median(d[True])), load_l=round(st.median(d[False])), delta=round(dlt)))
mB.sort(key=lambda x: -x['n_w'])
OUT['cr_matched_job_gen'] = dict(pairs=len(mB), wafers_covered=nB, extra_h=round(hB), delta_med=round(st.median(dB)) if dB else None, delta_q=q(dB, 0), rows=mB[:20])
# (d) wafer-weighted extrapolation: apply matched median delta per gen to all CR=Wafer wafers of that gen
dg = collections.defaultdict(list)
for x in mB: dg[x['gen']].extend([x['delta']] * x['n_w'])
cw = collections.Counter(r['_gen'] for r in RW if r['_load'] is not None and r['_cr'].lower() == 'wafer')
ext = {g: dict(wafers=n, delta=round(st.median(dg[g])) if dg[g] else None, extra_h=round(n * st.median(dg[g]) / 3600) if dg[g] else None) for g, n in cw.items()}
OUT['cr_extrapolated'] = dict(by_gen=ext, total_h=sum(x['extra_h'] or 0 for x in ext.values()), cr_wafer_wafers=sum(cw.values()))
# the suspicious RDL2 G5 CR=Wafer 1083 s: which lots?
odd = collections.Counter()
for r in RW:
    if r['_fam'] == 'TB500 RDL2' and r['_cr'].lower() == 'wafer' and r['_load'] is not None: odd[(r['dev'], r['job'], r['lot'])] += 1
OUT['rdl2_crwafer_lots'] = [dict(dev=k[0], job=k[1], lot=k[2], n=n, load=round(med([r['_load'] for r in RW if r['dev'] == k[0] and r['lot'] == k[2] and r['_fam'] == 'TB500 RDL2']))) for k, n in odd.most_common(8)]
json.dump(OUT, open(f'{F}/a1.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
for k, v in OUT.items(): print('==', k); print(json.dumps(v, ensure_ascii=False, default=str)[:3000])
