import json, re, collections, datetime as dt, sys, os, statistics as st
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract'))); from tparse import pt; from fam import family
WORK = os.environ.get('AOI_WORK') or sys.exit('set AOI_WORK')
A = os.path.join(WORK, 'an3'); os.chdir(A)  # 아래 상대 경로(facts*.json 등)는 an3 폴더 기준
os.makedirs(os.path.join(WORK, 'report2'), exist_ok=True)
f = json.load(open('facts.json')); f4 = json.load(open('facts4.json')); f5 = json.load(open('facts5.json')); f6 = json.load(open('facts6.json')); q4 = json.load(open('params4.json'))
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d] = 'EagleG5'
devorder = lambda d: (d.startswith('4F'), int(re.sub(r'\D', '', d) or 0))
D = {}
D['gen'] = GEN
D['cov'] = dict(f['cov'], day_from='2026-09-09', day_to='2026-10-10', days=32, zips=8, minutes=543.9, report_rows=f5['stale_exposure']['rows_total'])
D['gen_share'] = f4['gen_share']; D['time_fam'] = f['time_fam']; D['overhead_dev'] = f4['overhead_dev']
D['load_inherent'] = f6['load_inherent']; D['g5_load_dev'] = f6['g5_load_dev']
D['cr_load'] = [x for x in q4['cr_load'] if x['n'] >= 100]; D['cr_cost'] = f6['cr_cost']; D['cr_cur'] = f6['cr_wafer_current'][:25]; D['cr_cur_total'] = f6['cr_wafer_current_total']; D['cr_lots'] = dict(lots=q4['cr_wafer_lots']['lots'], wafers=q4['cr_wafer_lots']['wafers'])
# repeats (valid wafer ids)
lots = {l['lot_id']: l for l in json.load(open('lots3.json'))}
R = [json.loads(l) for l in open('wafers.jsonl')]
P = lambda s: dt.datetime.fromisoformat(s) if s else None
VALID = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9\-]{6,}$')
TOK = re.compile(r'(^|[\s_-])(RE|RESCAN|REWORK|R\d?)([\s_-]|$)', re.I); STEP = re.compile(r'(^|[\s_-])(DIA|SRD|3D|EDGE|BUMP|CENTER|PCM|SPT|2D)([\s_-]|$)', re.I)
core = lambda l: re.sub(r'[\s_-]+', '-', TOK.sub(r'\1\3', TOK.sub(r'\1\3', l))).strip('-').upper()
steps = lambda l: tuple(sorted(m.group(2).upper() for m in STEP.finditer(l)))
seen = collections.defaultdict(list); nvalid = 0; ninv = 0; inv = collections.Counter()
for r in R:
    if r['wid'] and r['start']:
        if VALID.match(r['wid']): seen[(r['job'], r['wid'])].append(r); nvalid += 1
        else: ninv += 1; inv[r['wid']] += 1
cls = collections.Counter(); h = collections.Counter(); byjob = collections.defaultdict(collections.Counter); bydev = collections.defaultdict(collections.Counter); gap = collections.Counter(); stt = collections.Counter(); fam = collections.Counter(); rep_w = 0
ORDER = ['검사 단계가 다름(DIA·SRD 등)', '같은 장비 · 다른 Lot 이름', '같은 Lot 다시(RE 표기·재실행)', '다른 장비 · 다른 Lot 이름', '같은 Lot 재시도']
for k, v in seen.items():
    if len(v) < 2: continue
    rep_w += 1
    v.sort(key=lambda r: r['start'])
    for a, b in zip(v, v[1:]):
        if a['lot_id'] == b['lot_id']: c = ORDER[4]
        elif steps(a['lot']) != steps(b['lot']): c = ORDER[0]
        elif core(a['lot']) == core(b['lot']): c = ORDER[2]
        elif a['dev'] != b['dev']: c = ORDER[3]
        else: c = ORDER[1]
        wt = (P(b['end']) - P(b['start'])).total_seconds() / 3600 if b['end'] else 0
        cls[c] += 1; h[c] += wt if 0 < wt < 2 else 0; byjob[k[0]][c] += 1; bydev[b['dev']][c] += 1; fam[family(k[0]) or '기타'] += 1
        if a['end']:
            g = (P(b['start']) - P(a['end'])).total_seconds() / 3600; gap['<1시간' if g < 1 else '1~24시간' if g < 24 else '1~7일' if g < 168 else '7일 이상'] += 1
        sa = (a['rstatus'] or '').strip().lower(); stt['Pass' if sa == 'pass' else '없음' if not sa else '오류·중단'] += 1
D['repeat'] = dict(valid=nvalid, invalid=ninv, invalid_top=inv.most_common(6), repeated_wafers=rep_w, extra=sum(cls.values()), hours=round(sum(h.values())),
                   cls=[dict(k=k, n=cls[k], h=round(h[k])) for k in ORDER], gap=dict(gap), first=dict(stt), fam=fam.most_common(8),
                   bydev=[dict(dev=d, **{k: c.get(k, 0) for k in ORDER}, total=sum(c.values()), wafers=sum(1 for r in R if r['dev'] == d and r['wid'])) for d, c in sorted(bydev.items(), key=lambda kv: devorder(kv[0]))],
                   jobs=[dict(job=j, total=sum(c.values()), **{k: c.get(k, 0) for k in ORDER}) for j, c in sorted(byjob.items(), key=lambda kv: -sum(kv[1].values()))[:15]])
D['pair_lots'] = dict(hist=f5['pair_lots_hist'], wafers=f5['pair_lots_wafers'])
# idle
D['busy_dev'] = f4['busy_pct_dev']; D['fleet_hour'] = f4['fleet_busy_hour_pct']; D['gap_h'] = f4['gap_hours_by_size']; D['gap_n'] = f4['gap_count_by_size']
D['weekday'] = f['weekday']; D['lot_size'] = f4['lot_size_class']; D['small_jobs'] = f4['small_lot_jobs']; D['idle'] = f['idle']; D['night'] = f4['night_start_pct']
D['daily'] = f4['daily_fleet']
# data quality
D['multi_report'] = f4['multi_report']; D['stale_exp'] = f5['stale_exposure']; D['stale_true'] = f4['stale_age_days']; D['stale_dev'] = f4['stale_any']['by_dev']; D['faults_match'] = f['faults_match']
D['has'] = dict(ini=f['cov']['has_ini'], sl=f['cov']['has_sl'], pi=f['cov']['has_pi'], in_report=f['cov']['in_report'])
# errors
D['recovery'] = f4['recovery_min']; D['status'] = f['status'][:14]; D['errdev'] = f['errdev']
# review
D['review'] = f['review']; D['review_all'] = f['review_all']; D['unrev_fam'] = f4['unreviewed_fam']; D['review_def'] = f4['review_by_defect']; D['review_hour'] = f['review_hour']
# multi
D['rdl_post'] = f6['rdl_post']; D['multi_check'] = f4 and f5['multi_check']; D['multi'] = [m for m in f['multi'] if m['n'] >= 100]; D['def_time'] = f['def_time']; D['def_fam'] = f4['def_fam']; D['zero_def'] = f4['zero_def_pct']
D['use3d'] = f5['use3d']
# params
fams = []
for x in q4['fam']:
    fams.append(dict(family=x['family'], devices=x['devices'], compared=x['compared'], ndiff=x['ndiff'], diffcat=x['diffcat'], cnt=x['cnt'],
                     meta={d: dict(lots=m['lots'], wafer_s=m['wafer_s'], cr=m['cr'], af=m['af'], cap=m['cap'], last_t=m['last_t']) for d, m in x['meta'].items()},
                     rows=[dict(cat=r['cat'], key=r['key'], cons=r['cons'][:24], ncons=r['ncons'], off={d: r['vals'][d][:24] for d in r['dev_off']}) for r in x['rows'] if r['cat'] in ('검출 기준', '자동화·레시피 동작', '얼라인·포커스 설정')][:60]))
D['fams'] = fams; D['cap'] = q4['cap_by_fam']
D['events'] = dict(npairs=q4['events']['npairs'], n=q4['events']['n'], cat=q4['events']['cat'])
try:
    p5 = json.load(open('params5.json')); D['p5'] = {k: v for k, v in p5.items() if k != 'persistent'}; D['persistent'] = p5['persistent']
except FileNotFoundError: D['p5'] = None; D['persistent'] = []
D['aoi17'] = dict(enh=f5['aoi17_enh'], pi4=f5['pi4enh_dev_job'])
D['focus'] = f['focus_drift'][:12]; D['aff'] = {d: dict(med=v['med'], p90=v['p90'], n=v['n']) for d, v in f['aff_dev'].items()}
D['pareto'] = f['pareto'][:8]; D['ops'] = f['ops']; D['scan_ratio'] = [x for x in f4['scan_ratio'] if x['ratio'] >= 1.25 or x['ratio'] <= 0.8]
D['time_dev'] = f['time_dev']; D['def_dev'] = f['def_dev']
json.dump(D, open(os.path.join(WORK, 'report2', 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print('ok', len(json.dumps(D, ensure_ascii=False)), 'p5', D['p5'] is not None, D['repeat']['extra'], D['repeat']['hours'])
