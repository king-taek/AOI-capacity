import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
g=collections.defaultdict(list)
for r in R:
    w=r['wid'] or ''
    if r['_s'] and re.fullmatch(r'[A-Za-z0-9]{6,}',w) and re.search(r'\d',w) and re.search(r'[A-Za-z]',w) and r['_in']:
        g[(r['job'],w)].append(r)
c=[(k,v) for k,v in g.items() if len(v)>=3]
print(len(c))
def score(v):
    lots=set(r['lot'] for r in v); dia=any(re.search(r'\bDIA\b|DIA',r['lot'].upper()) for r in v)
    return (dia and len(lots)>=3, dia, len(lots), len(v))
c.sort(key=lambda kv:score(kv[1]),reverse=True)
for k,v in c[:12]:
    v.sort(key=lambda r:r['_s'])
    print(k, [(r['dev'],r['lot'],r['start'][5:16],r['rstatus']) for r in v])
