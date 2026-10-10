import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
def med(v): return st.median(v)
for fam in ['TB500 PI4','TB500 RDL4','TB500 RDL3','TB500 RDL2']:
  for g in ['EagleG5','EagleTP','EagleT','EAGLE']:
    for nr in [1,2,3]:
        v=[r['_wt'] for r in RW if r['_fam']==fam and r['_gen']==g and r['rstatus']=='Pass' and len(r['ext'] or {})==nr]
        if len(v)>20: print(fam,g,nr,len(v),round(med(v)),round(st.median([r['_dur'] for r in RW if r['_fam']==fam and r['_gen']==g and r['rstatus']=='Pass' and len(r['ext'] or {})==nr and r['_dur']])))
print(collections.Counter(len(r['ext'] or {}) for r in RW if r['_fam']=='TB500 PI4'))
