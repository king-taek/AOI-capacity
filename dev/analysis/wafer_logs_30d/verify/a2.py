"""Audit claims 4-8 + follow-ups (PI Duration semantics, AOI-25 RDL2 CR=Wafer lots)."""
import sys, json, re, collections, statistics as st, datetime as dt
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
lots, AC, R = load()
RW = [r for r in R if r['_in'] and r['_wt'] is not None and 0 < r['_wt'] < 7200]
OUT = {}
# ---- follow-up: single-recipe durations for PI recipes (what does Duration cover on 2-recipe PI wafers?)
sd = collections.defaultdict(list)
for r in RW:
    if r['nrec'] <= 1 and r['_dur'] and r['_fam'] and 'PI' in r['_fam'] and r['_gen'] == 'EagleG5': sd[(r['_fam'], (r['recipe'] or '').strip())].append(r['_dur'])
OUT['pi_single_dur'] = [dict(fam=k[0], recipe=k[1], **q(v, 0)) for k, v in sorted(sd.items()) if len(v) >= 20]
# 2-recipe PI: dur vs seg1, seg2 by order, by AF setting
pi = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and 'PI' in r['_fam'] and len(r['_ex']) == 2 and r['_dur'] and r['_gen'] == 'EagleG5':
        (t1, k1), (t2, k2) = r['_ex']; s1 = (t2 - t1).total_seconds(); s2 = (r['_e'] - t2).total_seconds()
        pi[(k1 + '→' + k2, r['_af'])].append((r['_dur'], s1, s2, r['_post']))
OUT['pi_two'] = [dict(order=k[0], af=k[1], n=len(v), dur=round(med([x[0] for x in v])), seg1=round(med([x[1] for x in v])), seg2=round(med([x[2] for x in v])), post=round(med([x[3] for x in v])),
                      dur_minus_seg1=round(med([x[0] - x[1] for x in v])), both_minus_dur=round(med([x[1] + x[2] - x[0] for x in v]))) for k, v in sorted(pi.items(), key=lambda kv: -len(kv[1])) if len(v) >= 50]
# 기타 two-recipe singles
sd2 = collections.defaultdict(list)
for r in RW:
    if r['nrec'] <= 1 and r['_dur'] and (r['recipe'] or '').strip() in ('R-ETCH', 'PAD', '2D+3D_CAMTEK', '2D+3D_CAMTEK_BUMP'): sd2[(r['recipe'] or '').strip()].append(r['_dur'])
OUT['etc_single_dur'] = {k: q(v, 0) for k, v in sd2.items()}
# ---- follow-up: AOI-25 RDL2 CR=Wafer lots
rows = []
for lid, l in lots.items():
    if l['device'] == 'AOI-25' and l['job'] == 'TB500_RDL2 - Multi':
        ws = [r for r in RW if r['lot_id'] == lid]
        if len(ws) < 10: continue
        b0, b1 = pt(l['bs']), pt(l['be'])
        rows.append(dict(lot=l['lot'], cr=(AC.get(lid) or {}).get('cr'), af=(AC.get(lid) or {}).get('af'), n=len(ws), load=round(med([r['_load'] for r in ws])), scan=round(med([r['_dur'] for r in ws])), wt=round(med([r['_wt'] for r in ws])),
                         batch_h=round((b1 - b0).total_seconds() / 3600, 1) if b0 and b1 else None, day=str(b0)[:10] if b0 else None))
rows.sort(key=lambda x: x['day'] or '')
OUT['aoi25_rdl2_lots'] = rows
# ---- Claim 4: repeat scans deep dive
VALID = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9\-]{6,}$')
TOK = re.compile(r'(^|[\s_-])(RE|RESCAN|REWORK|R\d?)([\s_-]|$)', re.I); STEP = re.compile(r'(^|[\s_-])(DIA|SRD|3D|EDGE|BUMP|CENTER|PCM|SPT|2D)([\s_-]|$)', re.I)
core = lambda l: re.sub(r'[\s_-]+', '-', TOK.sub(r'\1\3', TOK.sub(r'\1\3', l))).strip('-').upper()
steps = lambda l: tuple(sorted(m.group(2).upper() for m in STEP.finditer(l)))
seen = collections.defaultdict(list)
for r in R:
    if r['wid'] and r['_s'] and VALID.match(r['wid']): seen[(r['job'], r['wid'])].append(r)
ORDER = ['검사 단계가 다름(DIA·SRD 등)', '같은 장비 · 다른 Lot 이름', '같은 Lot 다시(RE 표기·재실행)', '다른 장비 · 다른 Lot 이름', '같은 Lot 재시도']
pairs = []
for k, v in seen.items():
    if len(v) < 2: continue
    v.sort(key=lambda r: r['_s'])
    for a, b in zip(v, v[1:]):
        if a['lot_id'] == b['lot_id']: c = ORDER[4]
        elif steps(a['lot']) != steps(b['lot']): c = ORDER[0]
        elif core(a['lot']) == core(b['lot']): c = ORDER[2]
        elif a['dev'] != b['dev']: c = ORDER[3]
        else: c = ORDER[1]
        pairs.append((c, a, b))
cls = collections.Counter(c for c, *_ in pairs); hrs = collections.Counter()
for c, a, b in pairs:
    if b['_wt'] and 0 < b['_wt'] < 7200: hrs[c] += b['_wt'] / 3600
OUT['repeat_asis'] = dict(extra=len(pairs), hours=round(sum(hrs.values())), cls={k: dict(n=cls[k], h=round(hrs[k])) for k in ORDER})
# focus: '같은 장비 · 다른 Lot 이름' + '다른 장비 · 다른 Lot 이름' -> sub-classify
def lotpair_key(a, b): return (a['lot_id'], b['lot_id'])
lp = collections.Counter(lotpair_key(a, b) for c, a, b in pairs if c in (ORDER[1], ORDER[3]))
lotsize = collections.Counter(r['lot_id'] for r in R if r['_s'])
sub = collections.Counter(); subh = collections.Counter(); subj = collections.defaultdict(collections.Counter); ex = collections.defaultdict(list)
DATE6 = re.compile(r'(^|\D)(\d{4}|\d{6})(\D|$)')
for c, a, b in pairs:
    if c not in (ORDER[1], ORDER[3]): continue
    npair = lp[lotpair_key(a, b)]; fracA = npair / max(1, lotsize[a['lot_id']])
    gap_h = (b['_s'] - a['_e']).total_seconds() / 3600 if a['_e'] else None
    rec_diff = (a['recipe'] or '').strip() != (b['recipe'] or '').strip()
    sa = (a['rstatus'] or '').strip().lower(); sb = (b['rstatus'] or '').strip().lower()
    if rec_diff: s = '레시피가 다름(다른 검사)'
    elif sa and sa != 'pass': s = '첫 검사가 Error·중단 → 다시'
    elif a['job'].upper().startswith('NO PATTERN') or 'TEST' in a['job'].upper() or 'TEST' in (a['lot'] + b['lot']).upper(): s = '모니터·테스트 웨이퍼'
    elif npair >= 20 and fracA >= 0.8: s = 'Lot 통째로 다시(이름만 바뀜)'
    elif npair >= 5: s = 'Lot 일부(5장 이상) 다시'
    else: s = '낱장(1~4장) 다시'
    sub[s] += 1
    if b['_wt'] and 0 < b['_wt'] < 7200: subh[s] += b['_wt'] / 3600
    subj[s][a['job'][:40]] += 1
    if len(ex[s]) < 6: ex[s].append(dict(job=a['job'][:36], wid=a['wid'], lotA=a['lot'][:28], lotB=b['lot'][:28], devA=a['dev'], devB=b['dev'], tA=a['start'][:16], tB=b['start'][:16], recA=(a['recipe'] or '')[:14], recB=(b['recipe'] or '')[:14], stA=(a['rstatus'] or '')[:12], gap_h=round(gap_h, 1) if gap_h is not None else None, npair=npair))
OUT['repeat_otherlot_sub'] = dict(n=sum(sub.values()), h=round(sum(subh.values())), sub={k: dict(n=v, h=round(subh[k]), top_jobs=subj[k].most_common(4)) for k, v in sub.most_common()}, ex=ex)
# the time gap distribution for whole-lot renames: same day?
gaps = collections.Counter()
for c, a, b in pairs:
    if c in (ORDER[1], ORDER[3]) and a['_e']:
        g = (b['_s'] - a['_e']).total_seconds() / 3600; gaps['<1시간' if g < 1 else '1~24시간' if g < 24 else '1~7일' if g < 168 else '7일 이상'] += 1
OUT['repeat_otherlot_gap'] = dict(gaps)
# 같은 Lot 다시(RE) class: how many are after errors vs after Pass (both Pass => true re-inspection)
re_st = collections.Counter()
for c, a, b in pairs:
    if c == ORDER[2]:
        sa = (a['rstatus'] or '').strip().lower(); re_st['첫 검사 Pass' if sa == 'pass' else '첫 검사 없음' if not sa else '첫 검사 Error·중단'] += 1
OUT['repeat_re_firststatus'] = dict(re_st)
# step-different class sanity: recipe differs?
sd_c = collections.Counter()
for c, a, b in pairs:
    if c == ORDER[0]: sd_c['recipe differs' if (a['recipe'] or '').strip() != (b['recipe'] or '').strip() else 'same recipe'] += 1
OUT['repeat_step_recipe'] = dict(sd_c)
# ---- Claim 5: idle / busy
devb = collections.defaultdict(list)
for l in lots.values():
    for rp in l['reports']:
        b0, b1 = rp['_b0'], rp['_b1']
        if b0 and b1 and b1 > b0 and b0 >= dt.datetime(2026, 9, 9): devb[l['device']].append((b0, b1))
T0 = dt.datetime(2026, 9, 9); T1 = max(b1 for bs in devb.values() for _, b1 in bs)
OUT['window'] = dict(t0=str(T0), t1=str(T1), hours=round((T1 - T0).total_seconds() / 3600))
busy_span = {}; busy_fixed = {}; idle_gaps = collections.Counter(); idle_total = 0; merged = {}
for dev, bs in devb.items():
    bs.sort(); m = []
    for b0, b1 in bs:
        if m and b0 <= m[-1][1]: m[-1][1] = max(m[-1][1], b1)
        else: m.append([b0, b1])
    merged[dev] = m
    busy = sum((b1 - b0).total_seconds() for b0, b1 in m) / 3600
    span = (m[-1][1] - m[0][0]).total_seconds() / 3600
    busy_span[dev] = round(100 * busy / span, 1); busy_fixed[dev] = round(100 * busy / ((T1 - T0).total_seconds() / 3600), 1)
    for (a0, a1), (b0, b1) in zip(m, m[1:]):
        g = (b0 - a1).total_seconds() / 3600
        if g > 0: idle_gaps['<30분' if g < .5 else '30분~2시간' if g < 2 else '2~8시간' if g < 8 else '8시간 이상'] += g; idle_total += g
head_tail = sum(((m[0][0] - T0).total_seconds() + (T1 - m[-1][1]).total_seconds()) / 3600 for m in merged.values())
OUT['busy'] = dict(mean_span=round(sum(busy_span.values()) / len(busy_span), 1), mean_fixed=round(sum(busy_fixed.values()) / len(busy_fixed), 1),
                   idle_gap_h=round(idle_total), idle_gaps={k: round(v) for k, v in idle_gaps.items()}, idle_lt2h_pct=round(100 * (idle_gaps['<30분'] + idle_gaps['30분~2시간']) / idle_total, 1),
                   head_tail_h=round(head_tail), total_h=round(len(merged) * (T1 - T0).total_seconds() / 3600), busy_h=round(sum(sum((b1 - b0).total_seconds() for b0, b1 in m) for m in merged.values()) / 3600),
                   span_vs_fixed=[dict(dev=d, span=busy_span[d], fixed=busy_fixed[d]) for d in sorted(merged, key=devorder) if abs(busy_span[d] - busy_fixed[d]) >= 3])
# ---- Claim 6: rows lacking own INI — separate 'never scanned' from 'overwritten'
tot_rows = 0; scanned_rows = 0; ini_rows = 0; lots2 = 0; lots_all = 0; overwritten = 0; never = 0; ws_missing = 0
inicount = collections.Counter(id(r['_rep']) for r in R if r['_rep'] is not None)
for l in lots.values():
    reps = l['reports']; lots_all += 1
    if len(reps) >= 2: lots2 += 1
    for rp in reps:
        tot_rows += rp['n']
        try: ws = int(rp['summary'].get('Wafers Scanned', '') or -1)
        except ValueError: ws = -1
        ini_here = inicount.get(id(rp), 0); ini_rows += ini_here
        if ws < 0: ws_missing += 1; continue
        scanned_rows += ws
        overwritten += max(0, ws - ini_here); never += max(0, rp['n'] - ws)
OUT['claim6'] = dict(lots=lots_all, lots_multi=lots2, pct=round(100 * lots2 / lots_all, 1), rows=tot_rows, rows_with_ws=tot_rows, scanned_rows=scanned_rows, ini_rows=ini_rows, rows_without_ini=tot_rows - ini_rows,
                     never_scanned_rows=never, scanned_but_no_ini=overwritten, ws_missing_reports=ws_missing,
                     pct_asis=round(100 * (tot_rows - ini_rows) / tot_rows, 1), pct_overwritten=round(100 * overwritten / tot_rows, 1), pct_never=round(100 * never / tot_rows, 1))
# ---- Claim 7: review lead time & right censoring
rv = []; unrev = collections.Counter(); tot = collections.Counter(); unrev3 = collections.Counter(); tot3 = collections.Counter(); unrev_def = collections.defaultdict(lambda: [0, 0])
CUT = T1 - dt.timedelta(days=3)
for r in R:
    if not r.get('has_sl') or not r['_e']: continue
    f = r['_fam'] or '기타'; g = r['_gen']
    v = r['_v']; tot[g] += 1
    if v:
        h = (v - r['_e']).total_seconds() / 3600
        if -1 < h < 2000: rv.append(h)
    else: unrev[g] += 1
    if r['_e'] < CUT:
        tot3[g] += 1
        if not v: unrev3[g] += 1
    if r['_def'] is not None:
        k = '0' if r['_def'] == 0 else '1~9' if r['_def'] < 10 else '10~99' if r['_def'] < 100 else '100+'
        unrev_def[k][0] += 1; unrev_def[k][1] += (not v)
# review within 24h / 72h for wafers older than 3 days
done24 = 0; done72 = 0; n3 = 0; med3 = []
for r in R:
    if not r.get('has_sl') or not r['_e'] or r['_e'] >= CUT: continue
    n3 += 1
    if r['_v']:
        h = (r['_v'] - r['_e']).total_seconds() / 3600; med3.append(h); done24 += h <= 24; done72 += h <= 72
OUT['review'] = dict(all_med=q(rv, 1), unrev_pct_asis=round(100 * sum(unrev.values()) / sum(tot.values()), 1), unrev_pct_excl3d=round(100 * sum(unrev3.values()) / sum(tot3.values()), 1),
                     by_gen_asis={g: round(100 * unrev[g] / tot[g], 1) for g in tot}, by_gen_excl3d={g: round(100 * unrev3[g] / tot3[g], 1) for g in tot3},
                     n_excl3d=n3, done24_pct=round(100 * done24 / n3, 1), done72_pct=round(100 * done72 / n3, 1), med_excl3d=round(st.median(med3), 1),
                     unrev_by_defects={k: dict(n=v[0], unrev_pct=round(100 * v[1] / v[0], 1)) for k, v in sorted(unrev_def.items())})
# G5 TB500 lead by family (excl last 3 days)
fl = collections.defaultdict(list)
for r in R:
    if r.get('has_sl') and r['_e'] and r['_e'] < CUT and r['_v'] and r['_gen'] == 'EagleG5' and r['_fam']:
        fl[r['_fam']].append((r['_v'] - r['_e']).total_seconds() / 3600)
OUT['review_g5_fam'] = {f: q(v, 1) for f, v in sorted(fl.items(), key=lambda kv: -len(kv[1])) if len(v) >= 100}
# ---- Claim 8: AOI-17 Enhanced
e = collections.defaultdict(list)
for r in RW:
    if r['_fam'] and 'Enhanced' in r['_fam'] and r['_dur'] and len(r['_ex']) == 2:
        (t1, k1), (t2, k2) = r['_ex']; s1 = (t2 - t1).total_seconds(); s2 = (r['_e'] - t2).total_seconds()
        e[(r['_fam'], r['dev'])].append((r['_dur'], s1, s2, r['_wt'], int(float(r['dies'])) if r.get('dies') else None, r['_def'], k1 + '→' + k2, r['_cr'], r['_af']))
OUT['aoi17'] = [dict(fam=k[0], dev=k[1], n=len(v), dur=round(med([x[0] for x in v])), seg1=round(med([x[1] for x in v])), seg2=round(med([x[2] for x in v])), wt=round(med([x[3] for x in v])), dies=med([x[4] for x in v]), defects=med([x[5] for x in v]),
                    order=collections.Counter(x[6] for x in v).most_common(1)[0][0], cr=collections.Counter(x[7] for x in v).most_common(1)[0][0], af=collections.Counter(x[8] for x in v).most_common(1)[0][0]) for k, v in sorted(e.items()) if len(v) >= 10]
# AOI-17 non-Enhanced PI for comparison
e2 = collections.defaultdict(list)
for r in RW:
    if r['dev'] in ('AOI-17', 'AOI-18', 'AOI-19') and r['_fam'] in ('TB500 PI2', 'TB500 PI3', 'TB500 PI4') and r['_dur'] and len(r['_ex']) == 2:
        (t1, k1), (t2, k2) = r['_ex']; e2[(r['_fam'], r['dev'])].append((r['_dur'], (t2 - t1).total_seconds(), (r['_e'] - t2).total_seconds(), r['_wt']))
OUT['aoi17_plain_pi'] = [dict(fam=k[0], dev=k[1], n=len(v), dur=round(med([x[0] for x in v])), seg1=round(med([x[1] for x in v])), seg2=round(med([x[2] for x in v])), wt=round(med([x[3] for x in v]))) for k, v in sorted(e2.items()) if len(v) >= 20]
# AOI-17 Enhanced by job string & day
e3 = collections.defaultdict(list)
for r in RW:
    if r['dev'] == 'AOI-17' and r['_fam'] and 'Enhanced' in r['_fam'] and r['_dur']: e3[(r['job'], r['start'][:10])].append(r['_dur'])
OUT['aoi17_by_job_day'] = [dict(job=k[0], day=k[1], n=len(v), dur=round(med(v))) for k, v in sorted(e3.items())]
json.dump(OUT, open(f'{F}/a2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
for k, v in OUT.items(): print('==', k); print(json.dumps(v, ensure_ascii=False, default=str)[:3500])
