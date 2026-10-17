#!/usr/bin/env bash
# Basic-learnability experiment: OpenMythos vs parameter-matched Transformer,
# 3 seeds each, simplified shortcut-free variable tracking. CPU only.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/basic_learn
mkdir -p $D/ckpts $D/logs
for s in 1 2 3; do for a in openmythos transformer; do echo "$a $s"; done; done |
  xargs -P "${JOBS:-4}" -n 2 sh -c '[ -f '"$D"'/ckpts/$0_s$1.pt ] || python '"$D"'/train.py --arm $0 --seed $1 --out '"$D"'/ckpts/$0_s$1.pt > '"$D"'/logs/train_$0_s$1.log 2>&1'
rm -f $D/results.jsonl
python $D/eval.py --ckpt $D/ckpts/openmythos_s{1,2,3}.pt $D/ckpts/transformer_s{1,2,3}.pt --out $D/results.jsonl > $D/logs/eval.log 2>&1
python $D/analyze.py $D/results.jsonl > $D/analysis.md
echo DONE
