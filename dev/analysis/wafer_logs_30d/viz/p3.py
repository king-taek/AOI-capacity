import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
for g in ['EagleTP']:
    v=[r for r in RW if r['_gen']==g and r['rstatus']=='Pass' and len(r['ext'] or {})<=1]
    print(len(v),st.median([r['_wt'] for r in v]), st.median([r['_dur'] for r in v if r['_dur']]))
    c=collections.defaultdict(list)
    for r in v: c[r['job']].append(r['_wt'])
    for j,x in sorted(c.items(),key=lambda a:-len(a[1]))[:10]: print(j,len(x),round(st.median(x)))
    print(collections.Counter(r['dev'] for r in v))
# PI4 G5 per device
c=collections.defaultdict(list)
for r in RW:
    if r['_fam']=='TB500 PI4' and r['_gen']=='EagleG5' and r['rstatus']=='Pass' and len(r['ext'])==2: c[r['dev']].append(r['_wt'])
print({d:(len(x),round(st.median(x))) for d,x in c.items()})
