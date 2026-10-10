import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
D='AOI-24';F='TB500 RDL3'
m=[r for r in RW if r['dev']==D and r['_fam']==F and r['rstatus']=='Pass' and sorted(r['ext'])==['x20','x5']]
for r in m[:5]:
    print(r['start'],r['scanstart'],r['ext'],r['dur'],r['end'])
