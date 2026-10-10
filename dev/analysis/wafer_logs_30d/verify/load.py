"""Shared loader: parse wafers.jsonl + lots3.json + ac4.json once, cache as pickle."""
import sys, os, re, json, pickle, datetime as dt, collections, statistics as st
WORK = os.environ.get('AOI_WORK') or sys.exit('set AOI_WORK')
A = os.path.join(WORK, 'an3')
F = os.path.join(WORK, 'fable')
os.makedirs(F, exist_ok=True)
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt
from fam import family
GEN = {'AOI-1':'EAGLE','AOI-2':'EAGLE','AOI-3':'EagleT','AOI-5':'EagleT','AOI-13':'EagleT','AOI-14':'EagleT','AOI-15':'EagleT','AOI-16':'EagleT','4F-AOI-01':'EagleT','4F-AOI-02':'EagleT',
       'AOI-4':'EagleTP','AOI-6':'EagleTP','AOI-7':'EagleTP','AOI-8':'EagleTP','AOI-9':'EagleTP','AOI-10':'EagleTP','AOI-11':'EagleTP','AOI-12':'EagleTP'}
for d in ['AOI-17','AOI-18','AOI-19','AOI-20','AOI-21','AOI-22','AOI-23','AOI-24','AOI-25','4F-AOI-03','4F-AOI-04','4F-AOI-05']: GEN[d] = 'EagleG5'
devorder = lambda d: (d.startswith('4F'), int(re.sub(r'\D', '', d) or 0))
def P(s): return dt.datetime.fromisoformat(s) if s else None
def num(x):
    try: return float(x)
    except: return None
def q(v, nd=1):
    v = sorted(x for x in v if x is not None); n = len(v)
    if not n: return None
    return dict(n=n, med=round(st.median(v), nd), p25=round(v[n//4], nd), p75=round(v[n*3//4], nd), p10=round(v[n//10], nd), p90=round(v[n*9//10], nd), mean=round(sum(v)/n, nd))
def med(v):
    v = [x for x in v if x is not None]
    return st.median(v) if v else None

def build():
    lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
    for l in lots.values():
        for rp in l['reports']:
            rp['_b0'], rp['_b1'] = pt(rp['bs']), pt(rp['be'])
    AC = json.load(open(f'{A}/ac4.json'))
    R = [json.loads(x) for x in open(f'{A}/wafers.jsonl', encoding='utf-8')]
    for r in R:
        r['_s'], r['_e'], r['_ss'] = P(r['start']), P(r['end']), P(r['scanstart'])
        r['_v'] = P(r['verify'])
        r['_wt'] = (r['_e'] - r['_s']).total_seconds() if r['_s'] and r['_e'] else None
        r['_load'] = (r['_ss'] - r['_s']).total_seconds() if r['_s'] and r['_ss'] else None
        r['_dur'] = (num(r['dur']) or 0) / 1000 if r['dur'] else None
        r['_d2'] = (num(r['dur2d']) or 0) / 1000 if r['dur2d'] else None
        r['_d3'] = (num(r['dur3d']) or 0) / 1000 if r['dur3d'] else None
        r['_post'] = ((r['_e'] - r['_ss']).total_seconds() - r['_dur']) if (r['_ss'] and r['_e'] and r['_dur'] is not None) else None
        r['_fam'] = family(r['job']); r['_gen'] = GEN.get(r['dev'], '?')
        try: r['_def'] = sum(int(float(v)) for v in r['pidef'].values()) if r['pidef'] else None
        except: r['_def'] = None
        r['_ex'] = sorted((P(v), k) for k, v in (r['ext'] or {}).items() if v)
        r['_rep'] = None
        if r['_s']:
            for rp in lots[r['lot_id']]['reports']:
                b0, b1 = rp['_b0'], rp['_b1']
                if b0 and b1 and b0.timestamp() - 600 <= r['_s'].timestamp() <= b1.timestamp() + 600: r['_rep'] = rp; break
        r['_in'] = r['_rep'] is not None
        a = AC.get(r['lot_id']) or {}
        r['_cr'] = (a.get('cr') or 'None'); r['_af'] = (a.get('af') or 'None'); r['_cap'] = a.get('cap')
    return lots, AC, R

def load():
    pk = f'{F}/cache.pkl'
    if os.path.exists(pk):
        with open(pk, 'rb') as fh: return pickle.load(fh)
    d = build()
    with open(pk, 'wb') as fh: pickle.dump(d, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return d

if __name__ == '__main__':
    lots, AC, R = load()
    print(len(lots), len(AC), len(R))
