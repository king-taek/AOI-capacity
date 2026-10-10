import sys, os, re, json, collections, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt; from fam import family, category, CATS
A, X = sys.argv[1], sys.argv[2]
lots = {l['lot_id']: l for l in json.load(open(f'{A}/lots3.json', encoding='utf-8'))}
P = json.load(open(f'{A}/params3_raw.json', encoding='utf-8'))
def flatten(path, rel):
    fl = {}
    try: t = open(path, 'rb').read().decode('cp949', 'replace')
    except OSError: return fl
    sec = ''; alg = ''; rtp = rel.lower().endswith('rtp.txt')
    for l in t.splitlines():
        l = l.strip()
        if not l or l[0] in ';#': continue
        if l.startswith('[') and ']' in l: sec = l[:l.index(']') + 1]; alg = ''; continue
        if '=' not in l: continue
        k, v = l.split('=', 1); k = k.strip(); v = v.strip()
        if rtp and ';' in v: v = v.split(';', 1)[0].strip()
        if k == 'Alg': alg = v; continue
        fl[f"{rel}{sec}{('<' + alg + '>') if alg else ''}{k}"] = v
    return fl
cache = {}
def full(lid):
    d = P[lid]; out = {k: v for k, v in d.items() if k != '__refs__'}
    for rel, tgt in d.get('__refs__', {}).items():
        if tgt not in cache: cache[tgt] = flatten(os.path.join(X, *tgt.split('/')), rel)
        out.update(cache[tgt])
    return out
def num(v):
    try: return float(v)
    except: return None
def same(a, b):
    if a == b: return True
    x, y = num(a), num(b)
    return x is not None and y is not None and abs(x - y) <= max(1e-9, 0.005 * max(abs(x), abs(y)))
STEP = re.compile(r'(^|[\s_-])(DIA|SRD|3D|EDGE|BUMP|CENTER|PCM|SPT|2D)([\s_-]|$)', re.I)
def steps(l): return tuple(sorted(m.group(2).upper() for m in STEP.finditer(l)))
def bt(l): return pt(l['bs']) or pt(l['be']) or dt.datetime.min
seq = collections.defaultdict(list)
for lid in P: seq[(lots[lid]['device'], lots[lid]['job'], lots[lid]['setup'])].append(lid)
GUID = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-', re.I)
OUT = dict(keys=collections.Counter(), pairs=0, pairs_step=0, changed_pairs=0, changed_pairs_step=0, cat_pairs=collections.Counter(), persistent=[], toggle_keys=collections.Counter(), persist_keys=collections.Counter(), persist_dev=collections.Counter(), persist_cat=collections.Counter(), toggle_cat=collections.Counter())
for (dev, job, setup), ls in seq.items():
    ls.sort(key=lambda l: bt(lots[l]))
    if len(ls) < 2: continue
    fl = [full(l) for l in ls]
    # consecutive pairs
    for i in range(len(ls) - 1):
        OUT['pairs'] += 1
        stp = steps(lots[ls[i]]['lot']) != steps(lots[ls[i+1]]['lot'])
        if stp: OUT['pairs_step'] += 1
        d = [k for k in set(fl[i]) & set(fl[i+1]) if not GUID.search(k) and category(k) in CATS and not same(fl[i][k], fl[i+1][k])]
        if d:
            OUT['changed_pairs'] += 1; OUT['changed_pairs_step'] += stp
            for c in {category(k) for k in d}: OUT['cat_pairs'][c] += 1
    # key-level sequences (ignore step-variant lots: take only lots with the most common step signature)
    sig = collections.Counter(steps(lots[l]['lot']) for l in ls).most_common(1)[0][0]
    idx = [i for i, l in enumerate(ls) if steps(lots[l]['lot']) == sig]
    if len(idx) < 2: continue
    keys = set().union(*[set(fl[i]) for i in idx])
    for k in keys:
        if GUID.search(k) or category(k) not in CATS: continue
        vals = [(i, fl[i][k]) for i in idx if k in fl[i]]
        if len(vals) < 2: continue
        # collapse equal consecutive
        runs = [vals[0]]
        for i, v in vals[1:]:
            if not same(runs[-1][1], v): runs.append((i, v))
        if len(runs) == 1: continue
        OUT['keys'][category(k)] += 1
        # toggle: some later value equals an earlier (non-adjacent) value
        tog = any(same(runs[a][1], runs[b][1]) for a in range(len(runs)) for b in range(a + 2, len(runs)))
        if tog or len(runs) > 3: OUT['toggle_keys'][category(k)] += 1; OUT['toggle_cat'][category(k)] += 1
        else:
            OUT['persist_keys'][category(k)] += 1; OUT['persist_cat'][category(k)] += 1; OUT['persist_dev'][dev] += 1
            if category(k) in ('검출 기준', '자동화·레시피 동작'):
                i0, i1 = runs[0][0], runs[1][0]
                OUT['persistent'].append(dict(dev=dev, job=job, key=k, old=runs[0][1][:40], new=runs[1][1][:40], when=str(bt(lots[ls[i1]]))[:10], before=str(bt(lots[ls[i0]]))[:10], cat=category(k), nlots=len(ls)))
OUT['persistent'].sort(key=lambda e: e['when'])
for k in ('keys', 'cat_pairs', 'toggle_keys', 'persist_keys', 'persist_dev', 'persist_cat', 'toggle_cat'): OUT[k] = dict(OUT[k])
json.dump(OUT, open(f'{A}/params5.json', 'w', encoding='utf-8'), ensure_ascii=False)
print({k: v for k, v in OUT.items() if k != 'persistent'}, len(OUT['persistent']))
