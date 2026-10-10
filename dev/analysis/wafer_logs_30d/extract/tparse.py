import sys, os, re, json, glob, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'scripts')))
import collect_wafer_logs as T
def ini(text):
    out={}; sec=''
    for l in text.splitlines():
        l=l.strip()
        if l.startswith('[') and l.endswith(']'): sec=l[1:-1]; out.setdefault(sec,{}); continue
        if '=' in l and sec: k,v=l.split('=',1); out[sec][k.strip()]=v.strip()
    return out
FMTS=["%d-%b-%y %I:%M:%S %p","%m/%d/%Y %I:%M:%S %p","%m/%d/%Y %H:%M:%S","%d-%b-%y %H:%M:%S","%m/%d/%y %H:%M:%S"]
def pt(v):
    v=(v or '').strip()
    for f in FMTS:
        try: return dt.datetime.strptime(v,f)
        except ValueError: pass
    m=re.match(r'(\d+)/(\d+)/(\d+) (\d+):(\d+):(\d+) (AM|PM)',v)
    if m:
        mo,d,y,h,mi,s,ap=m.groups(); h=int(h)%12+(12 if ap=='PM' else 0)
        return dt.datetime(int(y),int(mo),int(d),h,int(mi),int(s))
    return None
