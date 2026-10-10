import sys, os, json, statistics, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_idle_day as F

res = F.analyze("AOI-12")
counts = [r["blocks"] for r in res]
median_blocks = int(statistics.median(counts))
day = [r for r in res if r["day"] == "2026-09-20"][0]
clipped = day["clipped"]
blocks = [[s.strftime("%H:%M"), e.strftime("%H:%M")] for s, e in clipped]
gaps = [int((clipped[i + 1][0] - clipped[i][1]).total_seconds() // 60) for i in range(len(clipped) - 1)]
busy = sum(int((e - s).total_seconds() // 60) for s, e in clipped)
out = {"dev": "AOI-12", "day": "2026-09-20", "blocks": blocks, "gaps_min": gaps,
       "busy_min": busy, "pct": int(round(busy / 1440 * 100)),
       "blocks_median_day": median_blocks}
os.makedirs(os.path.join(F.BASE, "haiku"), exist_ok=True)
with open(os.path.join(F.BASE, "haiku", "idle_example.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
print("day counts", counts)
