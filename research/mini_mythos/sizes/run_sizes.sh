#!/usr/bin/env bash
# Stage S: evaluation only, no training. For Parcae 140M / 370M / 770M / 1.3B: dev NLL and the reasoning
# probes at recurrence depth 4, 8, 16, 32. One rented GPU (24 GB is enough), about 1.5-2 hours.
# Results are committed and pushed after every size; rerunning skips finished parts.
#
#   export GH_TOKEN=<fine-grained token: leotree2020/OpenMythos, Contents read+write>
#   export PRICE_PER_HOUR=<the pod's real price, USD/hour>
#   export MAX_USD=4
#   curl -fsSL https://raw.githubusercontent.com/leotree2020/OpenMythos/mythos-reasoning-eval-v1/research/mini_mythos/sizes/run_sizes.sh | bash
set -euo pipefail

: "${GH_TOKEN:?set GH_TOKEN}"
: "${PRICE_PER_HOUR:?set PRICE_PER_HOUR}"
MAX_USD="${MAX_USD:-4}"
SIZES="${SIZES:-parcae-140m parcae-370m parcae-770m parcae-1.3b}"
DEPTHS="${DEPTHS:-4,8,16,32}"
BRANCH=mythos-reasoning-eval-v1
W="${SIZES_WORK:-/workspace/mythosS}"
REPO="$W/repo"
S1=research/mini_mythos/stage1
RD=research/mini_mythos/reasoning
SD=research/mini_mythos/sizes
START=$(date +%s)
mkdir -p "$W"
exec > >(tee -a "$W/run_sizes.log") 2>&1
echo "price per hour used for the budget: \$$PRICE_PER_HOUR (check it is the real price)"

elapsed_hours() { awk -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n-s)/3600}'; }
spent() { awk -v h="$(elapsed_hours)" -v p="$PRICE_PER_HOUR" 'BEGIN{printf "%.2f", h*p}'; }
budget_left() { awk -v s="$(spent)" -v m="$MAX_USD" 'BEGIN{exit !(s < m)}'; }

publish() {
  local msg="$1" R="$REPO/$SD/results"
  if [ ! -d "$REPO/.git" ]; then echo "publish skipped: no repository checkout yet"; return 0; fi
  mkdir -p "$R"
  for d in "$W"/out/*/; do
    [ -d "$d" ] || continue
    n=$(basename "$d"); mkdir -p "$R/$n/nll" "$R/$n/reasoning"
    cp "$d"/nll/* "$R/$n/nll/" 2>/dev/null || true
    cp "$d"/reasoning/* "$R/$n/reasoning/" 2>/dev/null || true
  done
  cp "$W"/summary.{json,md} "$R/" 2>/dev/null || true
  cp "$W/run_sizes.log" "$R/run_sizes.txt" 2>/dev/null || true
  cp "$W/nvidia_smi.txt" "$R/" 2>/dev/null || true
  { echo "wall_hours=$(elapsed_hours)"; echo "spent_usd=$(spent)"; echo "price_per_hour=$PRICE_PER_HOUR"; } > "$R/COST.txt"
  git -C "$REPO" add -f "$R"
  git -C "$REPO" commit -q -m "sizes: $msg" || true
  for i in 1 2 3; do
    git -C "$REPO" pull -q --rebase origin "$BRANCH" && git -C "$REPO" push -q origin "HEAD:$BRANCH" && return 0
    sleep $((i * 5))
  done
  echo "WARNING: push failed; results remain in $R"
}
trap 'publish "final state (exit $?)"' EXIT

echo "== setup $(date -u)"
if [ -e "$REPO" ] && [ ! -d "$REPO/.git" ]; then mv "$REPO" "$REPO.incomplete.$(date +%s)"; fi
if [ ! -d "$REPO/.git" ]; then
  git clone -q -b "$BRANCH" "https://x-access-token:${GH_TOKEN}@github.com/leotree2020/OpenMythos.git" "$REPO"
else
  git -C "$REPO" pull -q --ff-only origin "$BRANCH"
fi
git -C "$REPO" config user.name "sizes-runner"
git -C "$REPO" config user.email "sizes-runner@users.noreply.github.com"
nvidia-smi | tee "$W/nvidia_smi.txt"
if [ ! -x "$W/venv/bin/python" ]; then python3 -m venv "$W/venv"; fi
V="$W/venv/bin"
"$V/pip" install -q --upgrade pip
"$V/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cu128
"$V/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0"
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
SIZES_WORK="$W" "$V/python" - <<'PY'
import os
from huggingface_hub import hf_hub_download
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c",
                local_dir=os.environ["SIZES_WORK"] + "/tok")
PY
TOK="$W/tok/tokenizer.json"

echo "== probe sets (must match the committed manifest) and tests $(date -u)"
"$V/python" -B "$REPO/$RD/build_sets.py" --out "$W/reasoning_sets.jsonl" --check "$REPO/$RD/results/sets_manifest.json"
(cd "$REPO/$RD" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_reasoning -v)

for size in $SIZES; do
  O="$W/out/$size"
  if [ -f "$O/reasoning/score.json" ] && [ -f "$O/nll/nll.json" ]; then echo "skip $size (done)"; continue; fi
  if ! budget_left; then echo "BUDGET: spent $(spent) >= $MAX_USD, not starting $size"; break; fi
  echo "== $size: download $(date -u) (spent so far \$$(spent))"
  SIZE="$size" DEST="$W/model_$size" MODELS="$REPO/$SD/models.json" "$V/python" - <<'PY'
import json, os
from huggingface_hub import hf_hub_download
m = json.load(open(os.environ["MODELS"]))[os.environ["SIZE"]]
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download(m["repo"], f, revision=m["revision"], local_dir=os.environ["DEST"])
PY
  REF=()
  if [ "$size" = parcae-140m ]; then REF=(--cpu-reference "$REPO/$S1/results/r1/per_window.csv"); fi
  if [ ! -f "$O/nll/nll.json" ]; then
    echo "== $size: dev NLL at depths $DEPTHS $(date -u)"
    (cd "$REPO/$SD" && "$V/python" -B nll_eval.py --size "$size" --model-dir "$W/model_$size" \
        --sets "$REPO/$S1/results/r1/eval_sets.jsonl" --depths "$DEPTHS" --out "$O/nll" \
        --upstream "$W/parcae" --tokenizer "$TOK" --device cuda "${REF[@]}")
  fi
  if [ ! -f "$O/reasoning/score.json" ]; then
    echo "== $size: reasoning probes at depths $DEPTHS $(date -u)"
    (cd "$REPO/$RD" && "$V/python" -B score.py --sets "$W/reasoning_sets.jsonl" --split dev --depths "$DEPTHS" \
        --out "$O/reasoning" --upstream "$W/parcae" --model-dir "$W/model_$size" --tokenizer "$TOK" \
        --device cuda --batch-tokens 16384 --no-pin-check)
  fi
  rm -rf "$W/model_$size"                     # free the disk for the next size
  (cd "$REPO/$SD" && "$V/python" -B report_sizes.py --root "$W/out" --sets "$W/reasoning_sets.jsonl" --out "$W/summary.json")
  publish "$size evaluated"
done

echo "== summary $(date -u)"
(cd "$REPO/$SD" && "$V/python" -B report_sizes.py --root "$W/out" --sets "$W/reasoning_sets.jsonl" --out "$W/summary.json")
echo "DONE: spent about \$$(spent). Stop and delete the pod now."
