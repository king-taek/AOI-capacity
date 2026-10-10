import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
AC=json.load(open(A+'/ac4.json'))
byl=collections.defaultdict(list)
for r in RW:
    if r['_ss']: byl[r['lot_id']].append((r['_ss']-r['_s']).total_seconds())
seq=collections.defaultdict(list)
for lid,a in AC.items():
    l=lots.get(lid)
    if l and pt(l['bs']): seq[(l['device'],l['job'])].append((pt(l['bs']),lid))
res=[]
for k,v in seq.items():
    v.sort(); crs=[(AC[l]['cr'] or '').lower() for _,l in v]
    sw=[i for i in range(1,len(v)) if crs[i]!=crs[i-1] and {crs[i],crs[i-1]}=={'lot','wafer'}]
    nsw=len(sw)
    for i in sw:
        L=[l for _,l in v[max(0,i-3):i]]; Rr=[l for _,l in v[i:i+3]]
        # require runs of same cr
        if len(L)<2 or len(Rr)<2: continue
        if len(set(crs[max(0,i-3):i]))!=1 or len(set(crs[i:i+3]))!=1: continue
        ml=[st.median(byl[l]) for l in L if len(byl[l])>=5]; mr=[st.median(byl[l]) for l in Rr if len(byl[l])>=5]
        if len(ml)<2 or len(mr)<2: continue
        res.append((k,nsw,crs[i-1],crs[i],round(st.median(ml)),round(st.median(mr)),str(v[i][0])[:10],[ (l,len(byl[l])) for l in L+Rr]))
res.sort(key=lambda x:(x[1]>2, -abs(x[4]-x[5])))
for x in res[:12]: print(x)
print(len(res))
