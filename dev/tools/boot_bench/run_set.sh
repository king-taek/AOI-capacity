#!/bin/bash
# run_set.sh <variant> : 세 조건으로 잰다(순차 — 동시에 돌리면 CPU 가 섞인다)
S=$(cd "$(dirname "$0")" && pwd)
v=$1; shift
for cond in "dpr1_cpu1 --dpr 1 --cpu 1" "dpr1_cpu4 --dpr 1 --cpu 4" "dpr15_cpu1 --dpr 1.5 --cpu 1"; do
  set -- $cond; name=$1; shift
  node $S/measure.js $S/html/$v.html --label "$v/$name" "$@" --out $S/out/${v}__${name}.json >/dev/null 2>$S/out/${v}__${name}.err && echo "ok $v $name" || echo "FAIL $v $name"
done
