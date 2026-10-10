import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
OUT=os.path.join(WORK,'sonnet'); os.makedirs(OUT,exist_ok=True)
def fmt(d): return d.isoformat() if d else None
def ok(r):
    if not (r['_s'] and r['_ss'] and r['_e'] and r['_dur']): return False
    se=r['_ss']+dt.timedelta(seconds=r['_dur'])
    if not (r['_s']<=r['_ss']<=se<=r['_e']): return False
    ex={k:P(v) for k,v in r['ext'].items()}
    if any(v is None for v in ex.values()): return False
    return all(r['_ss']<=v<=r['_e'] for v in ex.values()) and min(ex.values())==r['_ss']
def card(r,med_wt,note=''):
    se=r['_ss']+dt.timedelta(seconds=r['_dur'])
    ex=sorted(((P(v),k) for k,v in r['ext'].items()))
    return dict(dev=r['dev'],gen=r['_gen'],job=r['job'],lot=r['lot'],wid=r['wid'],slot=r['slot'],status=r['rstatus'],report=r['rep'],
      start=fmt(r['_s']),scanstart=fmt(r['_ss']),recipes=[dict(recipe=k,start=fmt(t),offset_from_scanstart_s=int((t-r['_ss']).total_seconds())) for t,k in ex],
      scan_end=fmt(se),end=fmt(r['_e']),
      load_s=int((r['_ss']-r['_s']).total_seconds()),scanlog_dur_s=round(r['_dur'],1),post_s=int((r['_e']-se).total_seconds()),wafer_s=int(r['_wt']),median_wafer_s=round(med_wt),note=note)
def pick(cands,med_wt,med_dur,exclude_ids=()):
    cands=[r for r in cands if ok(r)]
    cands.sort(key=lambda r:abs(r['_wt']-med_wt)+abs(r['_dur']-med_dur)*0.7)
    return cands[0]
out={}
# 3: PI4 G5 multi
g5=[r for r in RW if r['_fam']=='TB500 PI4' and r['_gen']=='EagleG5' and r['rstatus']=='Pass' and len(r['ext'])==2]
mw=st.median(r['_wt'] for r in g5); md=st.median(r['_dur'] for r in g5 if r['_dur'])
print('PI4 G5',len(g5),mw,md)
a=pick(g5,mw,md); 
tp=[r for r in RW if r['_gen']=='EagleTP' and r['rstatus']=='Pass' and len(r['ext'])==1]
tw=st.median(r['_wt'] for r in tp); td=st.median(r['_dur'] for r in tp if r['_dur'])
print('TP',len(tp),tw,td)
b=pick(tp,tw,td)
out['wafer_example']=dict(g5_pi4_multi=card(a,mw,'EagleG5 TB500 PI4 2-recipe, median over all G5 PI4 Pass 2-recipe wafers (n=%d)'%len(g5)),
                          tp_single=card(b,tw,'EagleTP single-recipe, median over all EagleTP Pass 1-recipe wafers (n=%d)'%len(tp)))
# 4: RDL
D='AOI-24';F='TB500 RDL3'
m=[r for r in RW if r['dev']==D and r['_fam']==F and r['rstatus']=='Pass' and sorted(r['ext'])==['x20','x5']]
s=[r for r in RW if r['dev']==D and r['_fam']==F and r['rstatus']=='Pass' and sorted(r['ext'])==['x20']]
mm=(st.median(r['_wt'] for r in m),st.median(r['_dur'] for r in m if r['_dur']))
sm=(st.median(r['_wt'] for r in s),st.median(r['_dur'] for r in s if r['_dur']))
print('RDL',len(m),mm,len(s),sm, collections.Counter(r['job'] for r in m).most_common(3),collections.Counter(r['job'] for r in s).most_common(3))
out['rdl_example']=dict(multi=card(pick(m,*mm),mm[0],f'{D} {F} x20+x5, median over n={len(m)}'),single=card(pick(s,*sm),sm[0],f'{D} {F} x20 only, median over n={len(s)}'))
json.dump(out,open(os.path.join(OUT,'p5.json'),'w'),ensure_ascii=False)
print(json.dumps(out,ensure_ascii=False,indent=1))
