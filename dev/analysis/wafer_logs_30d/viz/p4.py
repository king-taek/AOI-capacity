import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
c=collections.Counter()
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and r['_gen']=='EagleG5': c[(tuple(sorted(r['ext'].keys())),r['rstatus'])]+=1
print(c.most_common(12))
c2=collections.defaultdict(lambda: collections.defaultdict(list))
for r in RW:
    if r['_fam'] and r['_fam'].startswith('TB500 RDL') and r['_gen']=='EagleG5' and r['rstatus']=='Pass':
        k=tuple(sorted(r['ext'].keys())); c2[(r['dev'],r['_fam'])][k].append(r['_wt'])
for k,v in sorted(c2.items()):
    print(k,{kk:(len(x),round(st.median(x))) for kk,x in v.items() if len(x)>=15})
