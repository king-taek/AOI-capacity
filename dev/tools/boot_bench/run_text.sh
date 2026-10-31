#!/bin/bash
S=$(cd "$(dirname "$0")" && pwd)
while ! grep -q ALLDONE $S/out/all.log; do sleep 10; done
for v in text_lens text_bars text_story; do $S/run_set.sh $v; done
echo TEXTDONE
