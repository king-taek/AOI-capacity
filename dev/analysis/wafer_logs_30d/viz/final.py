import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
S=os.path.join(WORK,'sonnet'); os.makedirs(S,exist_ok=True)
HERE=os.path.dirname(os.path.abspath(__file__))
out=json.load(open(os.path.join(S,'p1.json')))
exec(open(os.path.join(HERE,'p5.py')).read().split('out={}')[0].split('from common import *')[1])  # fmt, ok, card, pick
def card2(r,med,note):
    c=card(r,med,note)
    se=dt.datetime.fromisoformat(c['scan_end']).replace(microsecond=0)
    c['scan_end']=fmt(se)
    c['last_recipe_starts_after_scan_end']=max(x['offset_from_scanstart_s'] for x in c['recipes'])>(se-r['_ss']).total_seconds()
    return c
# 3
g5=[r for r in RW if r['_fam']=='TB500 PI4' and r['_gen']=='EagleG5' and r['rstatus']=='Pass' and len(r['ext'])==2]
mw=st.median(r['_wt'] for r in g5); md=st.median(r['_dur'] for r in g5 if r['_dur'])
a=pick([r for r in g5 if 'Copy' not in r['job']],mw,md)
tp=[r for r in RW if r['_gen']=='EagleTP' and r['rstatus']=='Pass' and len(r['ext'])==1]
tw=st.median(r['_wt'] for r in tp); td=st.median(r['_dur'] for r in tp if r['_dur'])
b=pick(tp,tw,td)
out['wafer_example']=dict(g5_pi4_multi=card2(a,mw,f'EagleG5 TB500 PI4 2-recipe Pass wafers (n={len(g5)}); median wafer time {mw:.0f}s, median ScanLog dur {md:.0f}s'),
  tp_single=card2(b,tw,f'EagleTP single-recipe Pass wafers all jobs (n={len(tp)}); median wafer time {tw:.0f}s, median ScanLog dur {td:.0f}s'))
D='AOI-24';F='TB500 RDL3'
m=[r for r in RW if r['dev']==D and r['_fam']==F and r['rstatus']=='Pass' and sorted(r['ext'])==['x20','x5']]
s=[r for r in RW if r['dev']==D and r['_fam']==F and r['rstatus']=='Pass' and sorted(r['ext'])==['x20']]
mm=(st.median(r['_wt'] for r in m),st.median(r['_dur'] for r in m if r['_dur']))
sm=(st.median(r['_wt'] for r in s),st.median(r['_dur'] for r in s if r['_dur']))
out['rdl_example']=dict(multi=card2(pick(m,*mm),mm[0],f'{D} {F} x20+x5 Pass (n={len(m)}); median {mm[0]:.0f}s'),single=card2(pick(s,*sm),sm[0],f'{D} {F} x20-only Pass (n={len(s)}); median {sm[0]:.0f}s'))
# 5
def scans(job,wid):
    v=sorted([r for r in R if r['job']==job and r['wid']==wid and r['_s']],key=lambda r:r['_s'])
    return [dict(dev=r['dev'],lot=r['lot'],start=r['start'],end=r['end'],status=r['rstatus'],slot=r['slot'],report=r['rep']) for r in v]
out['repeat_example']=dict(primary=dict(job='2D@R5-AS-T256-A01_0859253PD-0A BS CUP',wid='GX57511826',scans=scans('2D@R5-AS-T256-A01_0859253PD-0A BS CUP','GX57511826'),
    note='VAF -> VAF-DIA (DIA step) -> VAF RE / VAF 3D RE (renamed lots, other device AOI-3)'),
  alt=dict(job='R_T254 LIVE_0858711PD_FS UBM',wid='42105364EWB0',scans=scans('R_T254 LIVE_0858711PD_FS UBM','42105364EWB0'),note='PWV-FS -> PWV-DIA -> PWV -> PWV-FS RESCAN, one device'))
# 6
lid='1561_AOI-17_HVB-PIDS3'; l=lots[lid]; rs=sorted(l['reports'],key=lambda x:pt(x['bs']))
ws=[r for r in R if r['lot_id']==lid]
ex=[]
for rp in rs:
    b,e=pt(rp['bs']),pt(rp['be'])
    ex.append(dict(name=rp['name'],bs=str(b),be=str(e),n=rp['n'],wafer_starts_in_window=sum(1 for r in ws if r['_s'] and b<=r['_s']<=e),
                   wafer_starts_in_window_pm10min=sum(1 for r in ws if r['_s'] and b-dt.timedelta(minutes=10)<=r['_s']<=e+dt.timedelta(minutes=10))))
out['overwrite_example']=dict(lot_id=lid,device=l['device'],job=l['job'],lot=l['lot'],reports=ex,gap_min=round((pt(rs[1]['bs'])-pt(rs[0]['be'])).total_seconds()/60,1),
  wafer_folders_total=len(ws),first_wafer_start=min(r['start'] for r in ws if r['start']),last_wafer_start=max(r['start'] for r in ws if r['start']),
  also_same_pattern='297 lots have exactly 2 reports 10-30 min apart with first n>=5; the first report window holds 0 wafer-folder starts in nearly all of them')
# 7
AC=json.load(open(A+'/ac4.json'))
byl=collections.defaultdict(list)
for r in RW:
    if r['_ss']: byl[r['lot_id']].append((r['_ss']-r['_s']).total_seconds())
def crex(dev,job,at):
    v=sorted([(pt(lots[x]['bs']),x) for x in AC if lots.get(x) and lots[x]['device']==dev and lots[x]['job']==job and pt(lots[x]['bs'])])
    crs=[(AC[x]['cr'] or '').lower() for _,x in v]
    i=next(i for i,(t,x) in enumerate(v) if str(t)[:10]==at and crs[i-1]!=crs[i])
    sel=v[max(0,i-3):i+3]
    return dict(device=dev,job=job,lots=[dict(lot_id=x,lot=lots[x]['lot'],bs=str(t),cr=AC[x]['cr'],af=AC[x]['af'],cap=AC[x]['cap'],n_wafers=len(byl[x]),median_load_s=round(st.median(byl[x])) if byl[x] else None) for t,x in sel])
out['cr_example']=dict(primary=crex('AOI-10','2D@R2-88850ITA0-SM-INT-BW_0857982PD-0A','2026-09-30'),alt=crex('AOI-5','2D@R4-SY4W001X013040K08VAR_0855437PD-0A','2026-09-14'),
  load_def='median of (scanstart - wafer start) seconds per lot, wafers inside report window')
# 8
P0=dt.datetime(2026,9,9).date(); days=[(P0+dt.timedelta(days=i)) for i in range(31)]
dl={d:[set(),0] for d in days}
for r in R:
    if r['_s'] and r['_in'] and r['_s'].date() in dl:
        x=dl[r['_s'].date()]; x[0].add(r['lot_id']); x[1]+=1
bsl=collections.Counter(pt(l['bs']).date() for l in lots.values() if pt(l['bs']))
out['daily_lots']=dict(days=[str(d) for d in days],lots=[len(dl[d][0]) for d in days],wafers=[dl[d][1] for d in days],lots_by_report_start=[bsl.get(d,0) for d in days],
   note='wafers = wafer-folder rows whose start falls inside a report window (+/-10 min), by start date; lots = distinct lot_ids among them; lots_by_report_start = lots3 entries by first report bs date')
json.dump(out,open(os.path.join(S,'viz.json'),'w'),ensure_ascii=False,separators=(',',':'))
print(os.path.getsize(os.path.join(S,'viz.json')))
print(json.dumps({k:out[k] for k in ['wafer_example','rdl_example','overwrite_example']},ensure_ascii=False)[:6000])
print(json.dumps(out['repeat_example'],ensure_ascii=False)); print(json.dumps(out['cr_example'],ensure_ascii=False)); print(out['daily_lots']['lots'],out['daily_lots']['wafers'])
