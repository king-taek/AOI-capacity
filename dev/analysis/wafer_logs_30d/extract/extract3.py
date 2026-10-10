"""30일 전수 로그 → wafers.jsonl(장 단위) · lots3.json(Lot 단위) · params3.json(Lot 첫 Wafer 파라미터)."""
import sys, os, re, json, collections, datetime as dt, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'scripts')))
from tparse import pt
import collect_wafer_logs as T
root, out = sys.argv[1], sys.argv[2]
HDR = re.compile(rb'^### ([^\t\n]+)\t(\d+)\t([^\n]*)\n', re.M)
def ini(text):
    o = {}; sec = ''
    for l in text.splitlines():
        l = l.strip()
        if not l or l[0] in ';#': continue
        if l.startswith('[') and ']' in l: sec = l[1:l.index(']')]; continue
        if '=' in l:
            k, v = l.split('=', 1); o[sec + '.' + k.strip()] = v.strip()
    return o
def split_bundle(b):
    out = {}; ms = list(HDR.finditer(b))
    for i, m in enumerate(ms):
        end = ms[i+1].start() if i+1 < len(ms) else len(b)
        out[m.group(1).decode('utf-8', 'replace')] = (b[m.end():end].decode('cp949', 'replace'), m.group(3).decode('utf-8','replace'))
    return out
def vd(v):
    for fm in ("%m-%d-%Y %H:%M:%S", "%m-%d-%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M:%S %p"):
        try: return dt.datetime.strptime(v.strip(), fm)
        except ValueError: pass
def em(v):
    v = v.replace('오전', 'AM').replace('오후', 'PM')
    m = re.match(r'(\d{4})-(\d\d)-(\d\d) (AM|PM) (\d+):(\d\d):(\d\d)', v)
    if m:
        y, mo, d, ap, h, mi, s = m.groups(); h = int(h) % 12 + (12 if ap == 'PM' else 0)
        return dt.datetime(int(y), int(mo), int(d), h, int(mi), int(s))
    return pt(v)
iso = lambda d: d.strftime('%Y-%m-%dT%H:%M:%S') if d else None
lots = json.load(open(os.path.join(root, 'lots.json'), encoding='utf-8'))
W = open(os.path.join(out, 'wafers.jsonl'), 'w', encoding='utf-8')
L = []; P = {}; nw = 0
PARAM_SKIP = T.PARAM_SKIP_RE
for x in lots:
    if x.get('skip'): continue
    lid = x['lot_id']; d = os.path.join(root, lid)
    b = os.path.join(d, '_묶음')
    bundles = {}
    if os.path.isdir(b):
        for f in os.listdir(b):
            bundles[f[:-4]] = split_bundle(open(os.path.join(b, f), 'rb').read())
    # reports: per wafer faults/status + batch times
    rep_rows = {}; reps = []
    for rp in sorted(glob.glob(os.path.join(d, 'report', '*'))):
        try: txt = open(rp, encoding='utf-8', errors='replace').read()
        except OSError: continue
        f = T.report_facts(txt); sm = f['summary']
        p = T._Tables(); p.feed(txt)
        cols = {}
        for tb in p.tables:
            if not tb: continue
            head = [h.lower() for h in tb[0]]
            iw = next((i for i, h in enumerate(head) if re.fullmatch(r'wafer\s*id', h)), -1)
            if iw < 0: continue
            idx = {k: next((i for i, h in enumerate(head) if h == k), -1) for k in ('faults', 'scanned dice', 'bad dice', 'yield', 'pass/fail', 'lot', 'recipe')}
            for r in tb[1:]:
                if len(r) <= iw: continue
                wid = r[iw]
                g = lambda k: r[idx[k]] if idx[k] >= 0 and idx[k] < len(r) else ''
                rep_rows[wid] = dict(faults=g('faults'), dice=g('scanned dice'), bad=g('bad dice'), yld=g('yield'), status=g('pass/fail'), rlot=g('lot'), rrec=g('recipe'), rep=os.path.basename(rp))
        reps.append(dict(name=os.path.basename(rp), bs=sm.get('Batch Start', ''), be=sm.get('Batch End', ''), job=f['job'], setup=f['setup'],
                         n=len([1 for l, w in f['wafers'] if not T.is_placeholder(l, w)]), summary={k: v for k, v in sm.items() if k in ('Wafers Scanned', 'Recipe', 'Batch Time', 'Operator', 'Lot')}))
    wafers = sorted(set().union(*[set(v) for v in bundles.values()]) if bundles else [])
    lotrow = dict(lot_id=lid, device=x['device'], job=x['job'], setup=x['setup'], lot=x['lot'], bs=x['batch_start'], be=x['batch_end'],
                  error=x['error'], mode=x.get('mode'), wafers=len(wafers), reports=reps, rep_wafers=len(rep_rows))
    L.append(lotrow)
    for w in wafers:
        wi = ini(bundles.get('WaferInfo.ini', {}).get(w, ('', ''))[0])
        sl = ini(bundles.get('ScanLog.ini', {}).get(w, ('', ''))[0])
        pi = ini(bundles.get('ProductionInfo.ini', {}).get(w, ('', ''))[0])
        w2 = ini(bundles.get('Wafer2Table.ini', {}).get(w, ('', ''))[0])
        ri = bundles.get('RecipesInfo.ini', {}).get(w, ('', ''))[0]
        ext = {}
        for k, v in bundles.items():
            if k.startswith('ExtendedScanMetaData_') and w in v:
                m = re.search(r'"DateTime"\s*:\s*"([^"]+)"', v[w][0])
                if m: ext[k[21:-5]] = iso(pt(m.group(1)))
        rr = rep_rows.get(wi.get('AutoCycleInfo.UseWaferID', ''), rep_rows.get(w, {}))
        g = lambda o, k, dflt='': o.get(k, dflt)
        row = dict(
            lot_id=lid, dev=x['device'], job=x['job'], setup=x['setup'], lot=x['lot'], w=w,
            wid=g(wi, 'AutoCycleInfo.UseWaferID'), start=iso(pt(g(wi, 'AutoCycleInfo.WaferStartTime'))), end=iso(pt(g(wi, 'AutoCycleInfo.WaferEndTime'))),
            bstart_ini=g(wi, 'AutoCycleInfo.BatchStartTime'), recipe=g(wi, 'Recipe.Name'), op=g(wi, 'AutoCycleInfo.Operator'), machine=g(wi, 'AutoCycleInfo.Machine'),
            slot=g(wi, 'AutoCycleInfo.ActiveSlot'), cass=g(wi, 'AutoCycleInfo.Cassette').count('1') if g(wi, 'AutoCycleInfo.Cassette') else None,
            uselot=g(wi, 'AutoCycleInfo.UseLot'), qa=g(wi, 'General.key_quickAlign'),
            scanstart=iso(pt(g(sl, 'General.StartScan'))), dur=g(sl, 'General.Duration'), dur2d=g(sl, '2D.Duration'), dur3d=g(sl, '3D.Duration'),
            sldef=g(sl, 'General.DefectsNum'), dies=g(sl, 'General.ScanDies'), bad=g(sl, 'General.BadDies'), yld=g(sl, 'General.Yield'),
            verify=iso(vd(g(sl, 'General.VerifyDate'))) if g(sl, 'General.VerifyDate') else None, vdone=g(sl, 'General.VerifyDone'),
            reviewer=g(sl, 'General.ReviewerUser'), expmap=iso(em(g(sl, 'General.ExportMapStarted'))) if g(sl, 'General.ExportMapStarted') else None,
            slver=g(sl, 'Version.Name'), eqid=g(sl, 'General.EquipmentId'), user=g(sl, 'General.User'),
            pidef={k[11:]: v for k, v in pi.items() if k.startswith('DefectsNum.')},
            pos={k[14:]: v for k, v in pi.items() if k.startswith('PosAboveChuck.')},
            pareto={k[7:]: v for k, v in pi.items() if k.startswith('Pareto.')},
            wpass=g(pi, 'WaferPass.WaferPassByClassID'),
            stdaff=g(w2, 'WAFER ALIGNMENT.StdAffine'), stdorth=g(w2, 'WAFER ALIGNMENT.StdOrtho'), rot=g(w2, 'WAFER ALIGNMENT.Rotate  w2t'),
            nrec=len(re.findall(r'\[Recipe-\d+\]', ri)), recnames=re.findall(r'^Name=(.*)$', ri, re.M), ext=ext,
            rfault=rr.get('faults', ''), rdice=rr.get('dice', ''), ryld=rr.get('yld', ''), rstatus=rr.get('status', ''), rrec=rr.get('rrec', ''), rep=rr.get('rep', ''),
            has_ini=bool(wi), has_sl=bool(sl), has_pi=bool(pi), moved=False)
        W.write(json.dumps(row, ensure_ascii=False) + '\n'); nw += 1
    # params: first wafer folder's ini/txt (flattened key=value)
    pw = (x.get('param_wafers') or [None])[0]
    if pw and os.path.isdir(os.path.join(d, pw)):
        fl = {}
        for dp, dn, fn in os.walk(os.path.join(d, pw)):
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), os.path.join(d, pw)).replace('\\', '/')
                if not re.search(r'\.(ini|txt|json|xml|csv)$', rel, re.I) or PARAM_SKIP.match(rel): continue
                try: t = open(os.path.join(dp, f), 'rb').read().decode('cp949', 'replace')
                except OSError: continue
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
        P[lid] = fl
    # resolve '= other lot' dedup: _목록.tsv says "= <lot>/<wafer>/<rel>" for files stored elsewhere — collect refs
    man = os.path.join(d, '_목록.tsv')
    if pw and os.path.isfile(man):
        refs = {}
        for line in open(man, encoding='utf-8').read().splitlines()[1:]:
            f = line.split('\t')
            if len(f) == 6 and f[0] == pw and f[5].startswith('= '):
                refs[f[1]] = f[5][2:]
        if refs: P.setdefault(lid, {})['__refs__'] = refs
W.close()
json.dump(L, open(os.path.join(out, 'lots3.json'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump(P, open(os.path.join(out, 'params3_raw.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print('lots', len(L), 'wafers', nw, 'params', len(P))
