#!/usr/bin/env bash
# Toy depth-extrapolation study: 3 seeds trained at T=4, evaluated at
# T=1..16 under the four depth_ablation switches. CPU only, ~1h on 4 cores.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/toy_depth
STEPS=${STEPS:-2500}

mkdir -p $D/data $D/ckpts $D/logs
[ -f $D/data/input.txt ] || curl -sS -o $D/data/input.txt \
  https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt

for s in 1 2 3; do
  [ -f $D/ckpts/seed$s.pt ] || python $D/train_toy.py --seed $s --steps "$STEPS" \
    --out $D/ckpts/seed$s.pt --threads 1 > $D/logs/train_seed$s.log 2>&1 &
done
wait

rm -f $D/results.jsonl
python training/eval_ppl.py --ckpt $D/ckpts/seed{1,2,3}.pt --data $D/data/test.txt \
  --tokenizer bytes --seq-len 128 --batch-size 16 --device cpu --dtype fp32 \
  --n-loops 1,2,3,4,6,8,12,16 --ablations base,remainder,clamp,both \
  --out $D/results.jsonl > $D/logs/eval.log 2>&1
python $D/act_stats.py --ckpt $D/ckpts/seed{1,2,3}.pt --data $D/data/test.txt \
  --out $D/act_stats.json > $D/logs/act_stats.log 2>&1
python $D/summarize.py $D/results.jsonl
