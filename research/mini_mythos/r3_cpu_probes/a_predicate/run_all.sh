#!/bin/bash
# Resumable formal run: one process per case id, one JSON part per case (skips parts that already exist).
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
for c in T-01 T-02a T-02b T-03 T-04 T-04b-A1 T-04b-A2 T-05 T-06 T-07a T-07b T-08a T-08b T-08c T-09 T-10 T-11a1 T-11a2 T-11b1 T-11b2 T-11c1 T-11c2 T-11c3 T-11d1 T-11d2 T-11e T-14a T-14b T-14c; do
  [ -s results/parts/$c.json ] && continue
  python3 a_cases.py --only $c --repeat 5 --race-repeat 50 --out results/parts/$c.json.tmp > results/parts/$c.stdout.txt 2> results/parts/$c.stderr.txt && mv results/parts/$c.json.tmp results/parts/$c.json
done
echo ALLDONE > results/parts/ALLDONE
