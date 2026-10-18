#!/usr/bin/env bash
# Formal Gate A run for one level: both arms x seeds 1-3, 3000 steps,
# 4 jobs in parallel, then test-set evaluation and the pre-registered verdict.
#   ./run_level.sh A
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/gen_gate_a
L=$1
case $L in A|B|C1|C2) ;; *) echo "level must be A, B, C1 or C2"; exit 2 ;; esac
mkdir -p $D/runs $D/logs
for s in 1 2 3; do for a in openmythos transformer; do echo "$a $s"; done; done |
  xargs -P 4 -n 2 sh -c 'python '"$D"'/train_level.py --level '"$L"' --arm $0 --seed $1 --out '"$D"'/runs/'"$L"'_$0_s$1.json > '"$D"'/logs/'"$L"'_$0_s$1.log 2>&1'
rm -f $D/runs/eval_$L.jsonl
python $D/eval_level.py --ckpt $D/runs/${L}_openmythos_s{1,2,3}.pt $D/runs/${L}_transformer_s{1,2,3}.pt --out $D/runs/eval_$L.jsonl > $D/logs/eval_$L.log 2>&1
python $D/analyze_level.py $D/runs/eval_$L.jsonl > $D/level_$L.md
echo DONE
