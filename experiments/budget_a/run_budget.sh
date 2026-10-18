#!/usr/bin/env bash
# Level-A training-budget diagnostic: both arms x seeds 1-3, 12,000 steps with
# the extended schedule, comparability check against the Gate A level-A
# checkpoint at step 3000 (run aborts on failure), checkpoints at 3000/6000/
# 9000; then dev-set curves for the intermediate checkpoints, the final
# test2 evaluation and the pre-registered verdict.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/budget_a
GA=experiments/gen_gate_a
mkdir -p $D/runs $D/logs
for s in 1 2 3; do for a in openmythos transformer; do echo "$a $s"; done; done |
  xargs -P 4 -n 2 sh -c 'python '"$GA"'/train_level.py --level A --arm $0 --seed $1 --steps 12000 --schedule extended --save-at 3000,6000,9000 --compare-at 3000 --compare-ckpt '"$GA"'/runs/A_$0_s$1.pt --out '"$D"'/runs/A_$0_s$1.json > '"$D"'/logs/A_$0_s$1.log 2>&1' || true
if ls $D/runs/*_ABORTED.json >/dev/null 2>&1; then echo "COMPARABILITY FAILED: stopping"; exit 3; fi
for a in openmythos transformer; do for s in 1 2 3; do [ -f $D/runs/A_${a}_s$s.pt ] || { echo "missing run A_${a}_s$s"; exit 4; }; done; done
rm -f $D/runs/eval_dev_curve.jsonl $D/runs/eval_test2.jsonl
python $D/eval_budget.py --split dev --om-loops 4 --ckpt $D/runs/A_*_step*.pt --out $D/runs/eval_dev_curve.jsonl > $D/logs/eval_dev_curve.log 2>&1
python $D/eval_budget.py --split test2 --ckpt $D/runs/A_openmythos_s{1,2,3}.pt $D/runs/A_transformer_s{1,2,3}.pt --out $D/runs/eval_test2.jsonl > $D/logs/eval_test2.log 2>&1
python $D/analyze_budget.py $D/runs/eval_test2.jsonl > $D/verdict.md
echo DONE
