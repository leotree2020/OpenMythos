#!/usr/bin/env bash
# Run one gate of the memorization diagnostic for both arms × 3 seeds.
#   ./run_gate.sh 1   -> 32 problems, full batch, 2000 steps
#   ./run_gate.sh 2   -> 512 problems, batch 64, 3000 steps (only after Gate 1 passes)
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/memorize
G=$1
case $G in
  1) N=32; STEPS=2000; BS=32 ;;
  2) N=512; STEPS=3000; BS=64 ;;
  *) echo "gate must be 1 or 2"; exit 2 ;;
esac
mkdir -p $D/runs $D/logs
for s in 1 2 3; do for a in openmythos transformer; do echo "$a $s"; done; done |
  xargs -P 4 -n 2 sh -c 'python '"$D"'/train_mem.py --arm $0 --seed $1 --n '"$N"' --steps '"$STEPS"' --batch-size '"$BS"' --out '"$D"'/runs/g'"$G"'_$0_s$1.json > '"$D"'/logs/g'"$G"'_$0_s$1.log 2>&1'
python $D/analyze_mem.py $G > $D/gate$G.md
echo DONE
