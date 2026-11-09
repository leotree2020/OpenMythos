#!/usr/bin/env bash
# Thermo-B on a local CPU: same code as the GPU run (train.py / report.py), smaller configuration.
# No GPU, no git push, nothing rented. The test set is never used unless RUN_TEST=1 (and then only
# after a complete, passed dev gate) - a CPU pilot should not spend it.
#
#   cd research/mini_mythos/thermo_b && bash run_thermo_b_cpu.sh
#
# Default = CPU pilot: arms C (full), E (expand), T (thermo), one LR, seed 0, ~1M training tokens per
# run (120 steps of 8 x 1024), learning curve + geometry on 25 dev windows per domain, final dev
# score on the same 100 windows (2 replicas). Measured on 4 cores: training ~970 tok/s (bf16),
# so about 25 minutes per run and 1.5 hours for the pilot. Everything is configurable:
#
#   W=<work dir>            default $HOME/mythos_thermo_b_cpu (data ~0.2 GB, model 0.6 GB, venv)
#   PYTHON=<python>         interpreter with torch 2.11, numpy, einops, tokenizers, huggingface-hub,
#                           pyarrow (default: $W/venv/bin/python, created with the CPU wheels if missing)
#   THREADS=4  PRECISION=bf16  TOKENS=983040  SEQ_LEN=1024  GLOBAL_BATCH=8  MICRO_BATCH=2
#   LRS="3e-4"              LR search values for C and E (seed 0); the plan uses "1e-4 3e-4 1e-3"
#   SEEDS="0"               "0 1" adds the second seed of C and E and T seed 1 (needed for the gate)
#   ARMS="full expand thermo"
#   PROBE_PER_DOMAIN=25 DEV_PER_DOMAIN=25 EVAL_REPLICAS=2   (100 / 0 / 2 = the plan: all dev windows)
#   SKIP_TESTS=1            skip the CPU unit tests
#   RUN_TEST=1              evaluate the test set if the dev gate passes (off by default)
#
# The full plan on CPU (weeks): TOKENS=50000000 GLOBAL_BATCH=32 MICRO_BATCH=2 LRS="1e-4 3e-4 1e-3"
# SEEDS="0 1" PROBE_PER_DOMAIN=100 DEV_PER_DOMAIN=0.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MM="$(cd "$HERE/.." && pwd)"
W="${W:-$HOME/mythos_thermo_b_cpu}"
THREADS="${THREADS:-4}"
PRECISION="${PRECISION:-bf16}"
TOKENS="${TOKENS:-983040}"
SEQ_LEN="${SEQ_LEN:-1024}"
GLOBAL_BATCH="${GLOBAL_BATCH:-8}"
MICRO_BATCH="${MICRO_BATCH:-2}"
LRS="${LRS:-3e-4}"
SEEDS="${SEEDS:-0}"
ARMS="${ARMS:-full expand thermo}"
PROBE_PER_DOMAIN="${PROBE_PER_DOMAIN:-25}"
DEV_PER_DOMAIN="${DEV_PER_DOMAIN:-25}"
EVAL_REPLICAS="${EVAL_REPLICAS:-2}"
CORPUS_TOKENS="${CORPUS_TOKENS:-60000000}"
CKPT_EVERY="${CKPT_EVERY:-20}"
S1="$MM/stage1/results/r1"
mkdir -p "$W"
exec > >(tee -a "$W/run_thermo_b_cpu.log") 2>&1
START=$(date +%s)
echo "== Thermo-B CPU run $(date -u); work dir $W"
echo "config: tokens $TOKENS seq $SEQ_LEN batch $GLOBAL_BATCH/$MICRO_BATCH $PRECISION threads $THREADS lrs [$LRS] seeds [$SEEDS] arms [$ARMS]"

echo "== setup $(date -u)"
if [ -z "${PYTHON:-}" ]; then
  if [ ! -x "$W/venv/bin/python" ]; then
    python3 -m venv "$W/venv"
    "$W/venv/bin/pip" install -q --upgrade pip
    "$W/venv/bin/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cpu
    "$W/venv/bin/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0" "pyarrow==19.0.1"
  fi
  PYTHON="$W/venv/bin/python"
fi
"$PYTHON" -c "import torch, numpy, tokenizers; print('torch', torch.__version__, 'numpy', numpy.__version__)"
"$PYTHON" -m pip freeze > "$W/pip_freeze.txt" 2>/dev/null || true
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
THERMO_WORK="$W" "$PYTHON" - <<'PY'
import os
from huggingface_hub import hf_hub_download
W = os.environ["THERMO_WORK"]
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download("SandyResearch/parcae-140m", f, revision="236739ce93ba1afc1b3f172fb4a509f4500d2852", local_dir=W + "/model")
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c", local_dir=W + "/tok")
PY
COMMON=(--upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json" --device cpu --threads "$THREADS")

echo "== data: Stage 1 corpus reproduced (sha256) and extended to $CORPUS_TOKENS tokens; eval sets unchanged $(date -u)"
(cd "$MM/stage3b" && "$PYTHON" -B extend_data.py --results "$S1" --out "$W/data" \
    --tokenizer "$W/tok/tokenizer.json" --total-tokens "$CORPUS_TOKENS")
SETS="$W/data/eval_sets.jsonl"

if [ "${SKIP_TESTS:-0}" != 1 ]; then
  echo "== tests (CPU, tiny model) $(date -u)"
  for t in stage2:test_stage2 stage3:test_stage3 stage3b:test_stage3b thermo_b:test_thermo_b; do
    (cd "$MM/${t%%:*}" && STAGE0_UPSTREAM="$W/parcae" "$PYTHON" -B -m unittest "${t##*:}")
  done
fi

echo "== native dev scores: the Stage 1 CPU baseline (each run re-checks it at step 0, <= 1e-6) $(date -u)"
mkdir -p "$W/native"
"$PYTHON" - "$S1/per_window.csv" "$W/native/native_dev.csv" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
with open(src, encoding="utf-8") as f, open(dst, "w", encoding="utf-8") as g:
    g.write(f.readline())
    for line in f:
        if line.split(",")[1] == "dev":
            g.write(line)
PY

train() {   # arm lr seed
  local arm=$1 lr=$2 seed=$3
  local name="${arm}_lr${lr}_s${seed}"
  case " $ARMS " in *" $arm "*) ;; *) echo "skip $name (arm not selected)"; return 0;; esac
  if [ -f "$W/runs/$name/summary.json" ]; then echo "skip $name (done)"; return 0; fi
  echo "== train $name $(date -u)"
  (cd "$HERE" && "$PYTHON" -B train.py --arm "$arm" --lr "$lr" --seed "$seed" --tokens "$TOKENS" \
      --seq-len "$SEQ_LEN" --global-batch "$GLOBAL_BATCH" --micro-batch "$MICRO_BATCH" --precision "$PRECISION" \
      --probe-per-domain "$PROBE_PER_DOMAIN" --dev-per-domain "$DEV_PER_DOMAIN" --eval-replicas "$EVAL_REPLICAS" \
      --ckpt-every "$CKPT_EVERY" --out "$W/runs/$name" --data "$W/data" --sets "$SETS" \
      --native-dev "$W/native/native_dev.csv" --resume "${COMMON[@]}") \
      || { echo "TRAINING FAILED: $name"; exit 4; }
}
lr_of() { basename "$1" | sed -E 's/^[a-z]+_lr([^_]+)_s[0-9]+$/\1/'; }
report() { (cd "$HERE" && "$PYTHON" -B report.py "$@"); }

echo "== LR search: C and E, seed 0 $(date -u)"
for lr in $LRS; do
  train full "$lr" 0
  train expand "$lr" 0
done
first=${LRS%% *}
FULL_LR=$first; EXP_LR=$first
ls "$W"/runs/full_lr*_s0/summary.json >/dev/null 2>&1 && FULL_LR=$(lr_of "$(report choose "$W"/runs/full_lr*_s0)")
ls "$W"/runs/expand_lr*_s0/summary.json >/dev/null 2>&1 && EXP_LR=$(lr_of "$(report choose "$W"/runs/expand_lr*_s0)")
echo "chosen LR: C $FULL_LR, E $EXP_LR (T uses E's)"

echo "== further seeds and T $(date -u)"
for seed in $SEEDS; do
  if [ "$seed" != 0 ]; then train full "$FULL_LR" "$seed"; train expand "$EXP_LR" "$seed"; fi
  train thermo "$EXP_LR" "$seed"
done

echo "== dev gate (complete only with seeds 0 and 1 of C, E and T) $(date -u)"
GATE=0
report gate --runs "$W/runs" --full "$FULL_LR" --expand "$EXP_LR" > "$W/gate.json" || GATE=$?
cat "$W/gate.json"
if [ "$GATE" -eq 0 ] && [ "${RUN_TEST:-0}" = 1 ]; then
  for key in candidate_run control_run; do
    name=$("$PYTHON" -c "import json,sys;print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$W/gate.json" "$key")
    [ -f "$W/runs/$name/eval_test.json" ] || (cd "$MM/stage3" && "$PYTHON" -B eval_run.py --run "$W/runs/$name" \
        --split test --sets "$SETS" --out "$W/runs/$name/eval_test.csv" "${COMMON[@]}")
  done
  echo "NOTE: the test set was used; add a line to stage1/TEST_LOG.md by hand."
elif [ "$GATE" -eq 0 ]; then
  echo "dev gate passed; test set NOT used (RUN_TEST=1 to use it)"
fi

echo "== summary $(date -u)"
report summarize --runs "$W/runs" --native "$W/native" --stage1 "$S1/per_window.csv" --out "$W/summary.json"
echo "DONE in $(awk -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%.2f", (n-s)/3600}') hours. Summary: $W/summary.md"
