import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import collections
OUT=os.path.join(WORK,'sonnet'); os.makedirs(OUT,exist_ok=True)
lots=json.load(open(A+'/lots3.json'))
devs=[f'AOI-{i}' for i in range(1,26)]+[f'4F-AOI-0{i}' for i in range(1,6)]
P0=dt.datetime(2026,9,9); P1=dt.datetime(2026,10,10)  # end exclusive
win=collections.defaultdict(list)
bad=0
for l in lots:
    for r in l['reports']:
        b,e=pt(r['bs']),pt(r['be'])
        if not b or not e or e<=b: bad+=1; continue
        win[l['device']].append((b,e))
print('bad',bad, 'devs in data', sorted(win), )
merged={}
for d,w in win.items():
    w.sort(); m=[]
    for b,e in w:
        if m and b<=m[-1][1]:
            if e>m[-1][1]: m[-1][1]=e
        else: m.append([b,e])
    merged[d]=m
days=[(P0+dt.timedelta(days=i)) for i in range(31)]
v=[]
for d in devs:
    row=[]
    for day in days:
        t0,t1=day,day+dt.timedelta(days=1); s=0
        for b,e in merged.get(d,[]):
            lo,hi=max(b,t0),min(e,t1)
            if hi>lo: s+=(hi-lo).total_seconds()
        row.append(round(s/86400*100))
    v.append(row)
BINS=[0,5,10,15,20,30,45,60,90,120,240,480,1440,float('inf')]
cnt=[0]*(len(BINS)-1); hrs=[0.0]*(len(BINS)-1)
for d in devs:
    m=merged.get(d,[])
    for (b0,e0),(b1,e1) in zip(m,m[1:]):
        if e0<P0 or b1>P1: continue
        g=(b1-e0).total_seconds()/60
        for i in range(len(BINS)-1):
            if BINS[i]<=g<BINS[i+1]: cnt[i]+=1; hrs[i]+=g/60; break
hist=[dict(lo=BINS[i],hi=None if BINS[i+1]==float('inf') else BINS[i+1],n=cnt[i],hours=round(hrs[i],1)) for i in range(len(cnt))]
out=dict(days=[d.strftime('%Y-%m-%d') for d in days],devs=devs,v=v)
print([ (d,sum(r)/len(r)) for d,r in zip(devs,v)][:30])
print(hist)
json.dump(dict(heat=out,gapHist=hist),open(os.path.join(OUT,'p1.json'),'w'))
