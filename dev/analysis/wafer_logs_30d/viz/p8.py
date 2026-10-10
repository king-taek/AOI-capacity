import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
byl=collections.defaultdict(list)
for r in R: byl[r['lot_id']].append(r)
cands=[]
for lid,l in lots.items():
    rp=l['reports']
    if len(rp)!=2: continue
    rs=sorted(rp,key=lambda x:pt(x['bs']))
    b1,e1,b2,e2=pt(rs[0]['bs']),pt(rs[0]['be']),pt(rs[1]['bs']),pt(rs[1]['be'])
    if not all((b1,e1,b2,e2)): continue
    gap=(b2-e1).total_seconds()/60
    if not (10<=gap<=30) or rs[0]['n']<5: continue
    ws=byl[lid]
    c1=sum(1 for r in ws if r['_s'] and b1<=r['_s']<=e1); c2=sum(1 for r in ws if r['_s'] and b2<=r['_s']<=e2)
    cx=sum(1 for r in ws if r['_s'] and not(b1<=r['_s']<=e1 or b2<=r['_s']<=e2))
    cands.append((lid,l['device'],rs[0]['n'],rs[1]['n'],round(gap),c1,c2,cx,len(ws)))
print(len(cands))
for c in sorted(cands,key=lambda c:(c[5]-c[2]))[:15]: print(c)
