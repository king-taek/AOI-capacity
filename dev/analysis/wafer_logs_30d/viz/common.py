import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import *
import collections
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d]='EagleG5'
def P(s): return dt.datetime.fromisoformat(s) if s else None
lots={l['lot_id']:l for l in json.load(open(A+'/lots3.json'))}
R=[]
for l in open(A+'/wafers.jsonl'):
    r=json.loads(l)
    r['_s'],r['_e'],r['_ss']=P(r['start']),P(r['end']),P(r['scanstart'])
    r['_wt']=(r['_e']-r['_s']).total_seconds() if r['_s'] and r['_e'] else None
    r['_dur']=float(r['dur'])/1000 if r['dur'] else None
    r['_fam']=family(r['job']); r['_gen']=GEN.get(r['dev'])
    r['_in']=False
    if r['_s']:
        for rp in lots[r['lot_id']]['reports']:
            b0,b1=pt(rp['bs']),pt(rp['be'])
            if b0 and b1 and b0.timestamp()-600<=r['_s'].timestamp()<=b1.timestamp()+600: r['_in']=True;break
    R.append(r)
RW=[r for r in R if r['_in'] and r['_wt'] and 0<r['_wt']<7200]
