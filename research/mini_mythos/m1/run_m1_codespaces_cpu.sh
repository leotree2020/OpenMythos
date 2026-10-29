#!/usr/bin/env bash
# CPU-only original Parcae controlled learning; run inside PR #12 checkout.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
SEED="${1:-42}"
case "$SEED" in 42|20261029|20261030) ;; *) echo "Unsupported seed: $SEED" >&2; exit 2;; esac
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
ENV_DIR="${M1_ENV_DIR:-/tmp/mythos-m1-cpu-venv}"
PARCAE_DIR="${M1_PARCAE_DIR:-/tmp/mythos-m1-official-parcae}"
OUT="${M1_OUTPUT_DIR:-research/mini_mythos/results/m1_cpu}"
PIN="69284c13746e849104f738d6d1a347b1f457df76"
mkdir -p "$OUT"
if [[ ! -x "$ENV_DIR/bin/python" ]]; then "$PYTHON_BIN" -m venv "$ENV_DIR"; fi
"$ENV_DIR/bin/python" -m pip install -r research/mini_mythos/scripts/requirements-p1b-parcae.txt
if [[ ! -d "$PARCAE_DIR/.git" ]]; then
  git clone -q --no-checkout https://github.com/sandyresearch/parcae.git "$PARCAE_DIR"
  # A new --no-checkout clone has an empty index/worktree. Populate it before
  # checking status; otherwise all tracked files appear deleted.
  git -C "$PARCAE_DIR" fetch -q --depth 1 origin "$PIN"
  git -C "$PARCAE_DIR" checkout -q --detach "$PIN"
elif [[ -n "$(git -C "$PARCAE_DIR" status --porcelain --untracked-files=no)" ]]; then
  echo "Upstream has modifications; abort" >&2; exit 2
fi
git -C "$PARCAE_DIR" fetch -q --depth 1 origin "$PIN"
git -C "$PARCAE_DIR" checkout -q --detach "$PIN"
test "$(git -C "$PARCAE_DIR" rev-parse HEAD)" = "$PIN"
test -z "$(git -C "$PARCAE_DIR" status --porcelain --untracked-files=no)"
M1="research/mini_mythos/m1/native_parcae_cpu_learning.py"
"$ENV_DIR/bin/python" "$M1" --arm standard --seed "$SEED" --out "$OUT/A_$SEED.json" 2>&1 | tee "$OUT/A_$SEED.log"
"$ENV_DIR/bin/python" "$M1" --arm parcae --parcae-dir "$PARCAE_DIR" --seed "$SEED" --out "$OUT/B_$SEED.json" 2>&1 | tee "$OUT/B_$SEED.log"
"$ENV_DIR/bin/python" - "$OUT" "$SEED" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]); seed=sys.argv[2]
a=json.loads((p/f'A_{seed}.json').read_text()); b=json.loads((p/f'B_{seed}.json').read_text())
assert a['data']==b['data'],'Data identity mismatch'
assert a['status']=='PASS' and b['status']=='PASS','Learning criterion failed'
print('A/B M1 LEARNING PASS; NOT architecture superiority')
for r in (a,b):
 print(r['arm'],'parameters',r['model']['params'],'val NLL',r['observed']['final_val_nll'],'test NLL',r['observed']['final_test_nll'])
PY
printf 'Git HEAD: '; git rev-parse HEAD
printf 'Pinned upstream: '; git -C "$PARCAE_DIR" rev-parse HEAD
printf 'Upstream tracked changes: '; git -C "$PARCAE_DIR" status --porcelain --untracked-files=no
