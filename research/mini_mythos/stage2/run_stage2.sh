#!/usr/bin/env bash
# Stage 2 on one rented GPU, unattended. Results are committed and pushed to this branch after
# every phase, so nothing is lost if the machine goes away.
#
#   export GH_TOKEN=<fine-grained token: leotree2020/OpenMythos, Contents read+write>
#   export PRICE_PER_HOUR=0.69          # what the pod costs, USD/hour
#   export MAX_USD=20                   # stop starting new work beyond this spend
#   curl -fsSL https://raw.githubusercontent.com/leotree2020/OpenMythos/mythos-stage2-gpu-v1/research/mini_mythos/stage2/run_stage2.sh | bash
set -euo pipefail

: "${GH_TOKEN:?set GH_TOKEN}"
: "${PRICE_PER_HOUR:?set PRICE_PER_HOUR}"
MAX_USD="${MAX_USD:-20}"
BRANCH=mythos-stage2-gpu-v1
W="${STAGE2_WORK:-/workspace/mythos}"
REPO="$W/repo"
S1=research/mini_mythos/stage1
S2=research/mini_mythos/stage2
START=$(date +%s)
mkdir -p "$W"
exec > >(tee -a "$W/run_stage2.log") 2>&1

elapsed_hours() { awk -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n-s)/3600}'; }
spent() { awk -v h="$(elapsed_hours)" -v p="$PRICE_PER_HOUR" 'BEGIN{printf "%.2f", h*p}'; }
budget_left() { awk -v s="$(spent)" -v m="$MAX_USD" 'BEGIN{exit !(s < m)}'; }

publish() {   # copy small results into the repo, commit, push (never weights or checkpoints)
  local msg="$1" R="$REPO/$S2/results"
  mkdir -p "$R/runs"
  [ -d "$W/native" ] && cp "$W"/native/{agreement.json,native_dev.csv,native_dev_bf16.csv} "$R/" 2>/dev/null || true
  for d in "$W"/runs/*/; do
    [ -d "$d" ] || continue
    n=$(basename "$d"); mkdir -p "$R/runs/$n"
    cp "$d"/{config.json,summary.json,train_log.jsonl,eval_dev.csv} "$R/runs/$n/" 2>/dev/null || true
  done
  [ -f "$W/summary.json" ] && cp "$W"/summary.{json,md} "$R/"
  cp "$W/run_stage2.log" "$R/" 2>/dev/null || true
  { echo "wall_hours=$(elapsed_hours)"; echo "spent_usd=$(spent)"; echo "price_per_hour=$PRICE_PER_HOUR"; } > "$R/COST.txt"
  git -C "$REPO" add "$S2/results"
  git -C "$REPO" -c user.name="stage2-runner" -c user.email="stage2-runner@users.noreply.github.com" \
      commit -q -m "stage2: $msg" || true
  for i in 1 2 3; do
    git -C "$REPO" pull -q --rebase origin "$BRANCH" && git -C "$REPO" push -q origin "HEAD:$BRANCH" && return 0
    sleep $((i * 5))
  done
  echo "WARNING: push failed; results remain in $R"
}
trap 'publish "final state (exit $?)"' EXIT

echo "== setup $(date -u)"
if [ ! -d "$REPO/.git" ]; then
  git clone -q -b "$BRANCH" "https://x-access-token:${GH_TOKEN}@github.com/leotree2020/OpenMythos.git" "$REPO"
else
  git -C "$REPO" pull -q --ff-only origin "$BRANCH"
fi
for f in "$S1/results/r1/data_lock.json" "$S1/results/r1/manifest.json" "$S1/results/r1/per_window.csv"; do
  [ -f "$REPO/$f" ] || { echo "missing $f (Stage 1 revision 1 results not merged into $BRANCH)"; exit 2; }
done
nvidia-smi | tee "$W/nvidia_smi.txt"
python3 -m venv "$W/venv"
V="$W/venv/bin"
"$V/pip" install -q --upgrade pip
"$V/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cu128
"$V/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0" pyarrow
"$V/pip" freeze > "$W/pip_freeze.txt"
"$V/python" -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name())"
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
"$V/python" - <<'PY'
import os
from huggingface_hub import hf_hub_download
W = os.environ.get("STAGE2_WORK", "/workspace/mythos")
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download("SandyResearch/parcae-140m", f, revision="236739ce93ba1afc1b3f172fb4a509f4500d2852", local_dir=W + "/model")
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c", local_dir=W + "/tok")
PY
COMMON=(--upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json" --device cuda)

echo "== data (rebuild from the Stage 1 r1 lock) $(date -u)"
if [ ! -f "$W/data/manifest.json" ]; then
  (cd "$REPO/$S1" && "$V/python" build_data.py --out "$W/data" --tokenizer "$W/tok/tokenizer.json" \
      --lock "$REPO/$S1/results/r1/data_lock.json")
fi
diff "$W/data/manifest.json" "$REPO/$S1/results/r1/manifest.json" && echo "DATA IDENTICAL TO STAGE 1"
SETS="$W/data/eval_sets.jsonl"

echo "== tests (CPU, tiny model) $(date -u)"
(cd "$REPO/$S2" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_stage2 -v)

echo "== native GPU evaluation + agreement with the Stage 1 CPU baseline $(date -u)"
(cd "$REPO/$S2" && "$V/python" -B evaluate.py --sets "$SETS" --cpu-reference "$REPO/$S1/results/r1/per_window.csv" \
    --out "$W/native" "${COMMON[@]}")      # exits non-zero (and stops the run) if agreement fails
publish "native GPU evaluation and agreement"

train() {   # mode lr seed [extra args]
  local mode=$1 lr=$2 seed=$3; shift 3
  local name="${mode}_lr${lr}_s${seed}${SUFFIX:-}"
  if [ -f "$W/runs/$name/summary.json" ]; then echo "skip $name (done)"; return 0; fi
  if ! budget_left; then echo "BUDGET: spent $(spent) >= $MAX_USD, not starting $name"; return 1; fi
  echo "== train $name $(date -u) (spent so far \$$(spent))"
  local rc=0
  (cd "$REPO/$S2" && "$V/python" -B train.py --mode "$mode" --lr "$lr" --seed "$seed" --out "$W/runs/$name" \
      --data "$W/data" --sets "$SETS" "${COMMON[@]}" "$@") || rc=$?
  if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then echo "TRAINING FAILED: $name (exit $rc); stopping"; exit "$rc"; fi
  return "$rc"   # 0 done, 3 stopped on request; budget exhaustion returns 1 above
}
lr_of() { basename "$1" | sed -E 's/^[a-z]+_lr([^_]+)_s[0-9]+$/\1/'; }

for lr in 1e-4 3e-4 1e-3; do train lora "$lr" 0 || break; publish "lora lr $lr seed 0"; done
LORA_LR=$(lr_of "$(cd "$REPO/$S2" && "$V/python" report.py choose "$W"/runs/lora_lr*_s0)")
echo "chosen LoRA lr $LORA_LR"
train lora "$LORA_LR" 1 && publish "lora seed 1"
STEPS=$(( 20000000 / (32 * 1024) ))
SUFFIX=_resume train lora "$LORA_LR" 0 --stop-after-step $((STEPS / 2)) || true
SUFFIX=_resume train lora "$LORA_LR" 0 --resume && publish "lora resume test"

for lr in 1e-5 3e-5 1e-4; do train full "$lr" 0 || break; publish "full lr $lr seed 0"; done
FULL_LR=$(lr_of "$(cd "$REPO/$S2" && "$V/python" report.py choose "$W"/runs/full_lr*_s0)")
echo "chosen full lr $FULL_LR"
train full "$FULL_LR" 1 && publish "full seed 1"

echo "== summary $(date -u)"
(cd "$REPO/$S2" && "$V/python" report.py summarize --native "$W/native" --runs "$W/runs" --out "$W/summary.json" \
    --price-per-hour "$PRICE_PER_HOUR" --hours "$(elapsed_hours)")
cp "$W/pip_freeze.txt" "$W/nvidia_smi.txt" "$REPO/$S2/results/" 2>/dev/null || true
echo "DONE: spent about \$$(spent). Stop the pod now."
