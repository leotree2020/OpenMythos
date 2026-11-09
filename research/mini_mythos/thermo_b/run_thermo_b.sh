#!/usr/bin/env bash
# Thermo-B (rank expansion: C full rank vs E rank 1->28 vs T rank 1->28 + temperature; Parcae frozen,
# LoRA r28) on one rented GPU, unattended. Results are committed and pushed to this branch after every
# phase; rerunning the same command skips finished runs and resumes an interrupted one from its checkpoint.
#
#   export GH_TOKEN=<fine-grained token: leotree2020/OpenMythos, Contents read+write>
#   export PRICE_PER_HOUR=<the pod's real price, USD/hour>
#   export MAX_USD=6                    # stop starting new training beyond this spend
#   curl -fsSL https://raw.githubusercontent.com/leotree2020/OpenMythos/mythos-idea-thermo-v1/research/mini_mythos/thermo_b/run_thermo_b.sh | bash
set -euo pipefail

: "${GH_TOKEN:?set GH_TOKEN}"
: "${PRICE_PER_HOUR:?set PRICE_PER_HOUR}"
MAX_USD="${MAX_USD:-6}"
BRANCH=mythos-idea-thermo-v1
W="${THERMO_WORK:-/workspace/mythos_thermo_b}"
REPO="$W/repo"
S1=research/mini_mythos/stage1
S2=research/mini_mythos/stage2
S3=research/mini_mythos/stage3
S3B=research/mini_mythos/stage3b
TB=research/mini_mythos/thermo_b
TOKENS=50000000
CORPUS_TOKENS=60000000
LRS="1e-4 3e-4 1e-3"
START=$(date +%s)
mkdir -p "$W"
exec > >(tee -a "$W/run_thermo_b.log") 2>&1
echo "price per hour used for the budget: \$$PRICE_PER_HOUR (check it is the real price)"

elapsed_hours() { awk -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n-s)/3600}'; }
spent() { awk -v h="$(elapsed_hours)" -v p="$PRICE_PER_HOUR" 'BEGIN{printf "%.2f", h*p}'; }
budget_left() { awk -v s="$(spent)" -v m="$MAX_USD" 'BEGIN{exit !(s < m)}'; }

publish() {   # copy small results into the repo, commit, push (never weights or checkpoints)
  local msg="$1" R="$REPO/$TB/results"
  if [ ! -d "$REPO/.git" ]; then echo "publish skipped: no repository checkout yet"; return 0; fi
  mkdir -p "$R/run_files"     # not "runs" or *.log: both are in the repo .gitignore
  [ -d "$W/native" ] && cp "$W"/native/*.json "$W"/native/*.csv "$R/" 2>/dev/null || true
  for d in "$W"/runs/*/; do
    [ -d "$d" ] || continue
    n=$(basename "$d"); mkdir -p "$R/run_files/$n"
    cp "$d"/{config.json,summary.json,train_log.jsonl,curve.jsonl,eval_dev.csv,eval_test.csv,eval_test.json} \
       "$R/run_files/$n/" 2>/dev/null || true
  done
  [ -f "$W/summary.json" ] && cp "$W"/summary.{json,md} "$R/"
  [ -f "$W/gate.json" ] && cp "$W/gate.json" "$R/"
  cp "$W/run_thermo_b.log" "$R/run_thermo_b.txt" 2>/dev/null || true
  cp "$W"/data/{extension.json,manifest.json} "$R/" 2>/dev/null || true
  cp "$W/pip_freeze.txt" "$W/nvidia_smi.txt" "$R/" 2>/dev/null || true
  { echo "wall_hours=$(elapsed_hours)"; echo "spent_usd=$(spent)"; echo "price_per_hour=$PRICE_PER_HOUR"; } > "$R/COST.txt"
  git -C "$REPO" add -f "$TB/results" "$S1/TEST_LOG.md"
  git -C "$REPO" -c user.name="thermo-b-runner" -c user.email="thermo-b-runner@users.noreply.github.com" \
      commit -q -m "thermo-b: $msg" || true
  for i in 1 2 3; do
    git -C "$REPO" pull -q --rebase origin "$BRANCH" && git -C "$REPO" push -q origin "HEAD:$BRANCH" && return 0
    sleep $((i * 5))
  done
  echo "WARNING: push failed; results remain in $R"
}
trap 'publish "final state (exit $?)"' EXIT

echo "== setup $(date -u)"
if [ -e "$REPO" ] && [ ! -d "$REPO/.git" ]; then   # leftover from an interrupted clone: keep it aside
  mv "$REPO" "$REPO.incomplete.$(date +%s)"
fi
if [ ! -d "$REPO/.git" ]; then
  git clone -q -b "$BRANCH" "https://x-access-token:${GH_TOKEN}@github.com/leotree2020/OpenMythos.git" "$REPO"
else
  git -C "$REPO" pull -q --ff-only origin "$BRANCH"
fi
CODE=$(git -C "$REPO" rev-parse --short=8 HEAD)
nvidia-smi | tee "$W/nvidia_smi.txt"
if [ ! -x "$W/venv/bin/python" ]; then python3 -m venv "$W/venv"; fi
V="$W/venv/bin"
"$V/pip" install -q --upgrade pip
"$V/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cu128
"$V/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0" "pyarrow==19.0.1"
"$V/pip" freeze > "$W/pip_freeze.txt"
"$V/python" -c "import torch;print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name())"
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
THERMO_WORK="$W" "$V/python" - <<'PY'
import os
from huggingface_hub import hf_hub_download
W = os.environ["THERMO_WORK"]
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download("SandyResearch/parcae-140m", f, revision="236739ce93ba1afc1b3f172fb4a509f4500d2852", local_dir=W + "/model")
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c", local_dir=W + "/tok")
PY
COMMON=(--upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json" --device cuda)

echo "== data: Stage 1 corpus reproduced and extended to ~60M tokens (Stage 3b pipeline), eval sets unchanged $(date -u)"
"$V/python" "$REPO/$S3B/extend_data.py" --results "$REPO/$S1/results/r1" --out "$W/data" \
    --tokenizer "$W/tok/tokenizer.json" --total-tokens "$CORPUS_TOKENS"
SETS="$W/data/eval_sets.jsonl"
SETS_SHA=$(sha256sum "$SETS" | cut -c1-8)

echo "== tests (CPU, tiny model) $(date -u)"
(cd "$REPO/$S2" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_stage2 -v)
(cd "$REPO/$S3" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_stage3 -v)
(cd "$REPO/$S3B" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_stage3b -v)
(cd "$REPO/$TB" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_thermo_b -v)

echo "== native GPU evaluation and agreement with Stage 1 $(date -u)"
if [ ! -f "$W/native/agreement.json" ]; then
  (cd "$REPO/$S2" && "$V/python" -B evaluate.py --sets "$SETS" --cpu-reference "$REPO/$S1/results/r1/per_window.csv" \
      --out "$W/native" "${COMMON[@]}")      # exits non-zero (and stops the run) if agreement fails
fi
publish "native GPU evaluation"

train() {   # arm lr seed  (every run checks at step 0 that it reproduces the native dev scores)
  local arm=$1 lr=$2 seed=$3
  local name="${arm}_lr${lr}_s${seed}"
  if [ -f "$W/runs/$name/summary.json" ]; then echo "skip $name (done)"; return 0; fi
  if ! budget_left; then echo "BUDGET: spent $(spent) >= $MAX_USD, not starting $name"; return 1; fi
  echo "== train $name $(date -u) (spent so far \$$(spent))"
  (cd "$REPO/$TB" && "$V/python" -B train.py --arm "$arm" --lr "$lr" --seed "$seed" --tokens "$TOKENS" \
      --out "$W/runs/$name" --data "$W/data" --sets "$SETS" --native-dev "$W/native/native_dev.csv" --resume "${COMMON[@]}") \
      || { echo "TRAINING FAILED: $name"; exit 4; }
}
lr_of() { basename "$1" | sed -E 's/^[a-z]+_lr([^_]+)_s[0-9]+$/\1/'; }
report() { (cd "$REPO/$TB" && "$V/python" -B report.py "$@"); }

echo "== LR search: C and E, $TOKENS tokens, seed 0 $(date -u)"
for lr in $LRS; do
  train full "$lr" 0 || break; publish "C lr $lr"
  train expand "$lr" 0 || break; publish "E lr $lr"
done
FULL_LR=$(lr_of "$(report choose "$W"/runs/full_lr*_s0)")
EXP_LR=$(lr_of "$(report choose "$W"/runs/expand_lr*_s0)")
echo "chosen LR: C $FULL_LR, E $EXP_LR (T uses E's)"

echo "== second seed for C and E; T (temperature) seeds 0 and 1 $(date -u)"
train full "$FULL_LR" 1 && publish "C seed 1"
train expand "$EXP_LR" 1 && publish "E seed 1"
train thermo "$EXP_LR" 0 && publish "T seed 0"
train thermo "$EXP_LR" 1 && publish "T seed 1"

echo "== dev gate $(date -u)"
GATE=0
report gate --runs "$W/runs" --full "$FULL_LR" --expand "$EXP_LR" > "$W/gate.json" || GATE=$?
cat "$W/gate.json"
if [ "$GATE" -eq 0 ]; then
  CAND=$("$V/python" -c "import json,sys;print(json.load(open(sys.argv[1]))['candidate_run'])" "$W/gate.json")
  CTRL=$("$V/python" -c "import json,sys;print(json.load(open(sys.argv[1]))['control_run'])" "$W/gate.json")
  echo "== dev gate passed: test set, frozen candidates $CAND and $CTRL only $(date -u)"
  for name in "$CAND" "$CTRL"; do
    if [ ! -f "$W/runs/$name/eval_test.json" ]; then
      (cd "$REPO/$S3" && "$V/python" -B eval_run.py --run "$W/runs/$name" --split test --sets "$SETS" \
          --out "$W/runs/$name/eval_test.csv" "${COMMON[@]}")
    fi
  done
  if ! grep -q "Thermo-B" "$REPO/$S1/TEST_LOG.md"; then
    echo "| $(date -u '+%Y-%m-%d %H:%M') | Thermo-B 冻结候选(秩的逐级扩张):\`$CAND\` 与 C \`$CTRL\`,5000 万 token,深度 8,无 BOS,2 副本,GPU FP32 | \`$CODE\` | \`${SETS_SHA}…\` | 开发集关口通过后按 \`thermo_b/README.md\` 自动评测(仅测试集 800 窗口);测试集又一次用于比较,报告中注明。 |" \
        >> "$REPO/$S1/TEST_LOG.md"
  fi
  publish "test set evaluation of the frozen candidates"
elif [ "$GATE" -eq 1 ]; then
  echo "dev gate not passed: status FAIL, test set not used"
else
  echo "dev gate incomplete (missing runs, probably budget); test set not used"
fi

echo "== summary $(date -u)"
report summarize --runs "$W/runs" --native "$W/native" --stage1 "$REPO/$S1/results/r1/per_window.csv" \
    --out "$W/summary.json" --price-per-hour "$PRICE_PER_HOUR" --hours "$(elapsed_hours)"
echo "DONE: spent about \$$(spent). Stop the pod now."
