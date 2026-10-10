import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
byl=collections.defaultdict(list)
for r in R: byl[r['lot_id']].append(r)
for lid,l in lots.items():
    rp=l['reports']
    if len(rp)!=2: continue
    rs=sorted(rp,key=lambda x:pt(x['bs']))
    b1,e1,b2,e2=[pt(rs[0]['bs']),pt(rs[0]['be']),pt(rs[1]['bs']),pt(rs[1]['be'])]
    gap=(b2-e1).total_seconds()/60; d1=(e1-b1).total_seconds()/60; d2=(e2-b2).total_seconds()/60
    if 10<=gap<=30 and rs[0]['n']>=5 and d1>=20 and d2>=20:
        ws=byl[lid]; c1=sum(1 for r in ws if r['_s'] and b1<=r['_s']<=e1); c2=sum(1 for r in ws if r['_s'] and b2<=r['_s']<=e2)
        print(lid,l['job'][:30],rs[0]['n'],rs[1]['n'],round(d1),round(d2),round(gap),c1,c2,len(ws),str(b1)[:10])
