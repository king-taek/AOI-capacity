import sys, os, json, datetime as dt
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'extract')))
from tparse import pt

WORK = os.environ.get('AOI_WORK') or sys.exit('set AOI_WORK')
BASE = WORK
os.makedirs(os.path.join(BASE, 'haiku'), exist_ok=True)
LO = dt.datetime(2026, 9, 15)
HI = dt.datetime(2026, 10, 6)  # exclusive: through 2026-10-05

def merge(ivs):
    ivs = sorted(ivs)
    out = []
    for s, e in ivs:
        if out and s <= out[-1][1]:
            if e > out[-1][1]:
                out[-1][1] = e
        else:
            out.append([s, e])
    return out

def hm(t):
    return t.strftime("%H:%M")

def analyze(dev):
    per_day = {}
    with open(f"{BASE}/an3/lots3.json", encoding="utf-8") as f:
        lots = json.load(f)
    by_day = {}
    for lot in lots:
        if lot.get("device") != dev:
            continue
        for r in lot.get("reports") or []:
            s = pt(r.get("bs")); e = pt(r.get("be"))
            if s is None or e is None or e <= s:
                continue
            # split interval across days; record which days it touches
            cur = s
            while cur < e:
                day0 = dt.datetime(cur.year, cur.month, cur.day)
                day1 = day0 + dt.timedelta(days=1)
                seg_e = min(e, day1)
                by_day.setdefault(day0.date(), []).append((cur, seg_e, s, e))
                cur = seg_e
    results = []
    for day in sorted(by_day):
        d0 = dt.datetime(day.year, day.month, day.day)
        d1 = d0 + dt.timedelta(days=1)
        if not (LO <= d0 < HI):
            continue
        items = by_day[day]
        # a block crossing midnight: any report window that spans midnight of this day
        crosses = any(s < d1 and e > d1 for (_, _, s, e) in items) or any(s < d0 < e for (_, _, s, e) in items)
        # merged (not split) windows that touch midnight
        spans = []
        for (_, _, s, e) in items:
            spans.append((s, e))
        mg = merge(spans)
        crossing = [b for b in mg if b[0] < d1 and b[1] > d1 or b[0] < d0 < b[1]]
        clipped = []
        for s, e in mg:
            s2 = max(s, d0); e2 = min(e, d1)
            if e2 > s2:
                clipped.append((s2, e2))
        busy = sum(int((e - s).total_seconds() // 60) for s, e in clipped)
        pct = busy / 1440 * 100
        ok = (not crossing) and 3 <= len(clipped) <= 4 and 55 <= pct <= 70
        results.append(dict(day=str(day), blocks=len(clipped), busy=busy, pct=round(pct, 1),
                            crossing=len(crossing), ok=ok, clipped=clipped))
    return results

def main():
    chosen = None
    for dev in ["AOI-12", "AOI-8"]:
        res = analyze(dev)
        cands = [r for r in res if r["ok"]]
        print(dev, "days in window:", len(res), "candidates:", len(cands))
        for r in cands[:20]:
            print("  ", r["day"], r["blocks"], r["busy"], r["pct"])
        if cands:
            chosen = (dev, cands[0])
            break
    if not chosen:
        print("NO CANDIDATE")
        return
    dev, r = chosen
    clipped = r["clipped"]
    blocks = [[hm(s), hm(e)] for s, e in clipped]
    gaps = [int((clipped[i + 1][0] - clipped[i][1]).total_seconds() // 60) for i in range(len(clipped) - 1)]
    out = {"dev": dev, "day": r["day"], "blocks": blocks, "gaps_min": gaps,
           "busy_min": r["busy"], "pct": int(round(r["pct"]))}
    with open(f"{BASE}/haiku/idle_example.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    main()
