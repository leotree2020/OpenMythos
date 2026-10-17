#!/usr/bin/env bash
# Loop-mechanism comparison: 4 mechanisms × 3 seeds on multi-hop tracking,
# trained on hops 1..4, evaluated on hops 1..12 at T = 1..24. CPU only.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/loop_mech
STEPS=${STEPS:-3000}
JOBS=${JOBS:-3}
mkdir -p $D/ckpts $D/logs

for s in 1 2 3; do for m in fixed_act fixed_final rand_act rand_final; do
  echo "$m $s"
done; done | xargs -P "$JOBS" -n 2 sh -c '
  [ -f '"$D"'/ckpts/$0_s$1.pt ] || python '"$D"'/train_task.py --mech $0 --seed $1 \
    --steps '"$STEPS"' --out '"$D"'/ckpts/$0_s$1.pt > '"$D"'/logs/train_$0_s$1.log 2>&1'

rm -f $D/results.jsonl
python $D/eval_task.py --ckpt $D/ckpts/*.pt --out $D/results.jsonl > $D/logs/eval.log 2>&1
python $D/summarize.py $D/results.jsonl
