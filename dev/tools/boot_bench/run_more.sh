#!/bin/bash
S=$(cd "$(dirname "$0")" && pwd)
while ! grep -q TEXTDONE $S/out/text.log; do sleep 10; done
for v in baseline lite pixel hybrid cheap text_bars text_story text_lens; do node $S/measure.js $S/html/$v.html --label "$v/dpr1_cpu1#3" --dpr 1 --cpu 1 --out $S/out/${v}__dpr1_cpu1_r3.json >/dev/null 2>&1 && echo "ok $v r3" || echo "FAIL $v r3"; done
for v in baseline pixel; do node $S/measure.js $S/html/$v.html --label "$v/dpr15_cpu1#2" --dpr 1.5 --cpu 1 --out $S/out/${v}__dpr15_cpu1_r2.json >/dev/null 2>&1 && echo "ok $v dpr15 r2" || echo "FAIL $v dpr15 r2"; done
echo MOREDONE
