#!/usr/bin/env bash
# Stage R: native Parcae-140M on the reasoning probes (dev split) at recurrence depth 4, 8, 16, 32.
# One rented GPU, unattended, ~20-30 minutes. Results are committed and pushed to this branch.
#
#   export GH_TOKEN=<fine-grained token: leotree2020/OpenMythos, Contents read+write>
#   export PRICE_PER_HOUR=<the pod's real price, USD/hour>
#   curl -fsSL https://raw.githubusercontent.com/leotree2020/OpenMythos/mythos-reasoning-eval-v1/research/mini_mythos/reasoning/run_reasoning.sh | bash
set -euo pipefail

: "${GH_TOKEN:?set GH_TOKEN}"
: "${PRICE_PER_HOUR:?set PRICE_PER_HOUR}"
BRANCH=mythos-reasoning-eval-v1
W="${REASONING_WORK:-/workspace/mythosR}"
REPO="$W/repo"
RD=research/mini_mythos/reasoning
START=$(date +%s)
mkdir -p "$W"
exec > >(tee -a "$W/run_reasoning.log") 2>&1
echo "price per hour used: \$$PRICE_PER_HOUR (check it is the real price)"

elapsed_hours() { awk -v s="$START" -v n="$(date +%s)" 'BEGIN{printf "%.4f", (n-s)/3600}'; }

publish() {
  local msg="$1" R="$REPO/$RD/results"
  if [ ! -d "$REPO/.git" ]; then echo "publish skipped: no repository checkout yet"; return 0; fi
  mkdir -p "$R/native_dev"
  cp "$W"/scores/native_dev/* "$R/native_dev/" 2>/dev/null || true
  cp "$W"/report_native_dev.{json,md} "$R/" 2>/dev/null || true
  cp "$W/run_reasoning.log" "$R/run_reasoning.txt" 2>/dev/null || true
  { echo "wall_hours=$(elapsed_hours)"; echo "price_per_hour=$PRICE_PER_HOUR";
    awk -v h="$(elapsed_hours)" -v p="$PRICE_PER_HOUR" 'BEGIN{printf "spent_usd=%.2f\n", h*p}'; } > "$R/COST.txt"
  git -C "$REPO" add -f "$R"
  git -C "$REPO" commit -q -m "reasoning: $msg" || true
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
git -C "$REPO" config user.name "reasoning-runner"
git -C "$REPO" config user.email "reasoning-runner@users.noreply.github.com"
nvidia-smi | tee "$W/nvidia_smi.txt"
if [ ! -x "$W/venv/bin/python" ]; then python3 -m venv "$W/venv"; fi
V="$W/venv/bin"
"$V/pip" install -q --upgrade pip
"$V/pip" install -q "torch==2.11.0" --index-url https://download.pytorch.org/whl/cu128
"$V/pip" install -q "numpy==1.26.4" "einops==0.8.0" "tokenizers==0.23.2" "huggingface-hub==1.33.0"
[ -d "$W/parcae" ] || git clone -q https://github.com/sandyresearch/parcae "$W/parcae"
git -C "$W/parcae" checkout -q 69284c13746e849104f738d6d1a347b1f457df76
REASONING_WORK="$W" "$V/python" - <<'PY'
import os
from huggingface_hub import hf_hub_download
W = os.environ["REASONING_WORK"]
for f in ("pytorch_model.bin", "config.json"):
    hf_hub_download("SandyResearch/parcae-140m", f, revision="236739ce93ba1afc1b3f172fb4a509f4500d2852", local_dir=W + "/model")
hf_hub_download("SandyResearch/parcae-tokenizer", "tokenizer.json", revision="6247b5d0592876b73660f34c2dd16c9db9e9045c", local_dir=W + "/tok")
PY
COMMON=(--upstream "$W/parcae" --model-dir "$W/model" --tokenizer "$W/tok/tokenizer.json" --device cuda)

echo "== probe sets (deterministic; must match the committed manifest) $(date -u)"
"$V/python" -B "$REPO/$RD/build_sets.py" --out "$W/reasoning_sets.jsonl" --check "$REPO/$RD/results/sets_manifest.json"

echo "== tests (CPU, tiny model) $(date -u)"
(cd "$REPO/$RD" && STAGE0_UPSTREAM="$W/parcae" "$V/python" -B -m unittest test_reasoning -v)

echo "== native Parcae on the dev probes, depths 4, 8, 16, 32 $(date -u)"
(cd "$REPO/$RD" && "$V/python" -B score.py --sets "$W/reasoning_sets.jsonl" --split dev --depths 4,8,16,32 \
    --out "$W/scores/native_dev" "${COMMON[@]}")
(cd "$REPO/$RD" && "$V/python" -B report.py --scores "$W/scores/native_dev" --sets "$W/reasoning_sets.jsonl" \
    --split dev --label "native Parcae-140M" --out "$W/report_native_dev.json")
publish "native dev probes at depth 4/8/16/32"
echo "DONE: about \$$(awk -v h="$(elapsed_hours)" -v p="$PRICE_PER_HOUR" 'BEGIN{printf "%.2f", h*p}'). Stop and delete the pod now."
