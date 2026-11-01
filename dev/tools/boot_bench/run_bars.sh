#!/bin/bash
S=$(cd "$(dirname "$0")" && pwd)
for v in bars_a bars_b bars_c; do
  node $S/measure.js $S/html/$v.html --label "$v/dpr1_cpu1" --dpr 1 --cpu 1 --out $S/out/${v}__dpr1_cpu1.json >/dev/null 2>&1 && echo "ok $v 1" || echo "FAIL $v"
  node $S/measure.js $S/html/$v.html --label "$v/dpr15_cpu1" --dpr 1.5 --cpu 1 --out $S/out/${v}__dpr15_cpu1.json >/dev/null 2>&1 && echo "ok $v 15" || echo "FAIL $v 15"
  node $S/measure.js $S/html/$v.html --label "$v/dpr1_cpu4" --dpr 1 --cpu 4 --out $S/out/${v}__dpr1_cpu4.json >/dev/null 2>&1 && echo "ok $v 4" || echo "FAIL $v 4"
done; echo BARSDONE
