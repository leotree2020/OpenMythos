#!/usr/bin/env bash
# Growth by surprise while reading books, on a local CPU. No GPU, no git push, test set never used.
#
#   cd research/mini_mythos/thermo_growth && bash run_growth_cpu.sh
#
# 1. books: PG-19 (Stage 1 locked source, last shard), disjoint from all evaluation windows
# 2. auto: the knowledge space grows by itself where reality's pull is reproducible (beats noise by T)
# 3. controls with the same final number of directions k: schedule (evenly spaced, same surprise
#    direction) and static (k random directions from the start)
# 4. compare.py: side-by-side summary -> $W/growth_summary.md
#
# Settings (environment): W (work dir, default $HOME/mythos_growth_cpu), PYTHON, THREADS=4, BOOKS=20,
# BOOK_TOKENS=16384, SEQ_LEN=512, MICRO_BATCH=2, PAGE=4, LR=3e-4, T0=2.0, T_MIN=1.0, COOL=0.95,
# SKIP_TESTS=1. Reading 20 books x 16k tokens takes about 15-20 minutes per run on 4 cores.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MM="$(cd "$HERE/.." && pwd)"
W="${W:-$HOME/mythos_growth_cpu}"
THREADS="${THREADS:-4}"
BOOKS="${BOOKS:-20}"
BOOK_TOKENS="${BOOK_TOKENS:-16384}"
SEQ_LEN="${SEQ_LEN:-512}"
MICRO_BATCH="${MICRO_BATCH:-2}"
PAGE="${PAGE:-4}"
LR="${LR:-3e-4}"
T0="${T0:-2.0}"
T_MIN="${T_MIN:-1.0}"
COOL="${COOL:-0.95}"
mkdir -p "$W"
exec > >(tee -a "$W/run_growth_cpu.log") 2>&1
echo "== growth by surprise, CPU run $(date -u); work dir $W"

if [ -z "${PYTHON:-}" ]; then
  if [ ! -x "$W/venv/bin/python" ]; then
    python3 -m venv "$W/venv"
    "$W/venv/bin/pip" install -q --upgrade pip
    "$W/venv/bin/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cpu
    "$W/venv/bin/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0" "pyarrow==19.0.1"
  fi
  PYTHON="$W/venv/bin/python"
fi
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
GROWTH_WORK="$W" "$PYTHON" - <<'PY'
import os
from huggingface_hub import hf_hub_download
W = os.environ["GROWTH_WORK"]
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download("SandyResearch/parcae-140m", f, revision="236739ce93ba1afc1b3f172fb4a509f4500d2852", local_dir=W + "/model")
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c", local_dir=W + "/tok")
PY
SETS="$MM/stage1/results/r1/eval_sets.jsonl"

echo "== books $(date -u)"
(cd "$HERE" && "$PYTHON" -B books.py --results "$MM/stage1/results/r1" --tokenizer "$W/tok/tokenizer.json" \
    --out "$W/books" --books "$BOOKS" --book-tokens "$BOOK_TOKENS")

if [ "${SKIP_TESTS:-0}" != 1 ]; then
  echo "== tests $(date -u)"
  (cd "$HERE" && STAGE0_UPSTREAM="$W/parcae" "$PYTHON" -B -m unittest test_growth test_anneal_split)
fi

COMMON=(--data "$W/books" --sets "$SETS" --upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json"
        --threads "$THREADS" --seq-len "$SEQ_LEN" --micro-batch "$MICRO_BATCH" --page "$PAGE" --lr "$LR"
        --t0 "$T0" --t-min "$T_MIN" --cool "$COOL")
run() {   # name mode [extra...]
  local name=$1 mode=$2; shift 2
  if [ -f "$W/runs/$name/summary.json" ]; then echo "skip $name (done)"; return 0; fi
  echo "== read: $name $(date -u)"
  (cd "$HERE" && "$PYTHON" -B grow.py --mode "$mode" --out "$W/runs/$name" "${COMMON[@]}" "$@")
}

run auto auto
K=$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1]))['k_final'])" "$W/runs/auto/summary.json")
echo "auto grew $K directions"
if [ "$K" -gt 0 ]; then
  run schedule schedule --k-target "$K"
  run static static --k-target "$K"
else
  echo "no direction grew: controls skipped"
fi

echo "== summary $(date -u)"
(cd "$HERE" && "$PYTHON" -B compare.py "$W"/runs/auto "$W"/runs/schedule "$W"/runs/static --out "$W/growth_summary.md")
echo "DONE. Summary: $W/growth_summary.md"
