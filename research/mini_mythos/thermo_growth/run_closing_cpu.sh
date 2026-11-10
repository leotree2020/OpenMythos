#!/usr/bin/env bash
# Parcae closing experiment (README.md) on a local CPU: does the growing knowledge space add anything?
# Two disjoint book sets (A, B); five runs each. Nothing is pushed; the test set is never used.
# Finished runs are skipped, so the same command continues after an interruption.
#
#   cd research/mini_mythos/thermo_growth && W=<work dir> PYTHON=<python> bash run_closing_cpu.sh
#
# The work dir must already hold parcae/ (pinned checkout), model/ and tok/ (run_growth_cpu.sh sets them up).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MM="$(cd "$HERE/.." && pwd)"
: "${W:?set W (work dir)}"
: "${PYTHON:?set PYTHON}"
THREADS="${THREADS:-4}"
SETS="$MM/stage1/results/r1/eval_sets.jsonl"
exec > >(tee -a "$W/run_closing_cpu.log") 2>&1
echo "== Parcae closing experiment $(date -u)"

COMMON=(--sets "$SETS" --upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json"
        --threads "$THREADS" --anchor 3 --norm-limit 1.5)
run() {   # set name args...
  local set=$1 name=$2; shift 2
  local out="$W/closing/$set/$name"
  if [ -f "$out/summary.json" ]; then echo "skip $set/$name (done)"; return 0; fi
  rm -rf "$out"
  echo "== read: set $set, $name $(date -u)"
  (cd "$HERE" && "$PYTHON" -B grow.py --data "$W/books_cl_$set" --out "$out" "${COMMON[@]}" "$@")
}

for set in A B; do
  skip=0; [ "$set" = B ] && skip=30
  echo "== books, set $set $(date -u)"
  (cd "$HERE" && "$PYTHON" -B books.py --results "$MM/stage1/results/r1" --tokenizer "$W/tok/tokenizer.json" \
      --out "$W/books_cl_$set" --books 20 --book-tokens 16384 --heldout 10 --tail-windows 8 --heldout-windows 4 \
      --skip-books "$skip")
  run "$set" U_none --mode none --unfreeze --base-lr 1e-5
  run "$set" U_auto --mode auto --unfreeze --base-lr 1e-5 --crystallize 12
  run "$set" F_auto --mode auto --crystallize 12
  K=$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1]))['k_final'])" "$W/closing/$set/F_auto/summary.json")
  echo "set $set: F_auto grew $K directions"
  run "$set" F_static --mode static --k-target "$K"
  run "$set" F_sched --mode schedule --k-target "$K" --crystallize 12
  (cd "$HERE" && "$PYTHON" -B closing.py --set A "$W/closing/A" --set B "$W/closing/B" --out "$W/closing/CLOSING.md") || true
done
echo "DONE $(date -u). Summary: $W/closing/CLOSING.md"
