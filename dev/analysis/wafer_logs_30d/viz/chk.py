import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import collections
R=[json.loads(l) for l in open(A+'/wafers.jsonl')]
print(len(R))
print(collections.Counter(r['rstatus'] for r in R).most_common(8))
print(collections.Counter(family(r['job']) for r in R).most_common(15))
print(collections.Counter(r['machine'].split('_')[0] if r['machine'] else None for r in R).most_common(8))
print(min(r['start'] for r in R if r['start']), max(r['start'] for r in R if r['start']))
