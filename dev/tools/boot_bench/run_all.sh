#!/bin/bash
S=$(cd "$(dirname "$0")" && pwd)
for v in lite pixel css hybrid scan cheap noblur; do $S/run_set.sh $v; done
for v in lite_n2000 lite_n12000; do node $S/measure.js $S/html/$v.html --label "$v/dpr1_cpu1" --dpr 1 --cpu 1 --out $S/out/${v}__dpr1_cpu1.json >/dev/null 2>$S/out/$v.err && echo "ok $v" || echo "FAIL $v"; done
# 반복 2회차(기준 · 주요 변형, 재현성) 
for v in baseline lite pixel css hybrid scan; do node $S/measure.js $S/html/$v.html --label "$v/dpr1_cpu1#2" --dpr 1 --cpu 1 --out $S/out/${v}__dpr1_cpu1_r2.json >/dev/null 2>&1 && echo "ok $v r2" || echo "FAIL $v r2"; done
echo ALLDONE
