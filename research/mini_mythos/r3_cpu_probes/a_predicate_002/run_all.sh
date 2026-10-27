#!/bin/bash
# Resumable formal run for CPU-002: one process per case id, one JSON part per case (skips existing parts).
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p results/parts
for c in E1-P1 E1-P2 E1-P3 E1-A1 E1-A2 E1-A3 E1-X1a E1-X1z E1-X2 E1-S1 E1-S2 E2-00a E2-00b E2-00c E2-01 E2-02 E2-03 E2-04 E2-05 E2-06 E2-08a E2-08b E3-01 E3-01b E3-02a E3-02b E3-03 E3-03p; do
  [ -s results/parts/$c.json ] && continue
  [ -s results/parts/$c.json.gz ] && continue
  python3 e2_cases.py --only $c --repeat 5 --race-repeat 50 --out results/parts/$c.json.tmp > results/parts/$c.stdout.txt 2> results/parts/$c.stderr.txt && mv results/parts/$c.json.tmp results/parts/$c.json
done
echo ALLDONE > results/parts/ALLDONE
