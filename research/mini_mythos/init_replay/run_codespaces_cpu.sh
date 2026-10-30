#!/usr/bin/env bash
# Idempotent, CPU-only bootstrap. No installs, source reset, deletes or training.
set -euo pipefail
REPO=/workspaces/OpenMythos
WT=/workspaces/mythos-p1r1-20261030
PIN="${1:?Pass the exact reviewed OpenMythos commit SHA}"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo 'BLOCKED: full commit SHA required'; exit 2; }
git -C "$REPO" cat-file -e "$PIN^{commit}"
if [[ ! -e "$WT" ]]; then
  git -C "$REPO" worktree add --detach "$WT" "$PIN"
fi
[[ "$(git -C "$WT" rev-parse --show-toplevel)" == "$WT" && "$(git -C "$WT" rev-parse HEAD)" == "$PIN" ]] || {
  echo 'BLOCKED: existing worktree is another source version; not resetting it'; exit 2;
}
cd "$WT"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
PILOT="${M2L_EVIDENCE_DIR:-/workspaces/OpenMythos/mythos_evidence/m2_long_v1}/pilot.json"
OUT="${P1R_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/p1r_init_v1}"
if [[ -f "$OUT/result.json" ]]; then
  echo 'Existing result: read only, no repeated native execution.'
  python3 - "$OUT/result.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
print('experiment',r.get('experiment'))
print('execution_status',r.get('execution_status'))
print('outcome',json.dumps(r.get('outcome'),ensure_ascii=False,indent=2))
if r.get('error'): print(r['error'])
PY
  sha256sum "$OUT/result.json"
  exit 0
fi
if [[ -e "$OUT" || -e "$OUT.console.log" ]]; then
  echo 'BLOCKED: incomplete previous output exists; preserving it, not rerunning'; exit 2
fi
[[ -x "$PY" && -d "$PARCAE/.git" && -f "$PILOT" ]] || {
  echo 'BLOCKED: existing CPU environment, pinned upstream or old pilot missing'; exit 2;
}
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || {
  echo 'BLOCKED: tracked source edits detected'; exit 2;
}
bash -n research/mini_mythos/init_replay/run_codespaces_cpu.sh
"$PY" -m py_compile research/mini_mythos/init_replay/run_init_replay.py
export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export TORCHDYNAMO_DISABLE=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$(dirname "$OUT")"
echo "P1-R1 source: $PIN; six original initializer/probe sequences, zero optimizer updates."
set +e
"$PY" research/mini_mythos/init_replay/run_init_replay.py \
  --parcae-dir "$PARCAE" --pilot "$PILOT" --out "$OUT" 2>&1 | tee "$OUT.console.log"
statuses=("${PIPESTATUS[@]}")
set -e
[[ "${statuses[1]}" == 0 ]] || { echo 'BLOCKED: console log write failed'; exit 2; }
[[ ! -f "$OUT/result.json" ]] || sha256sum "$OUT/result.json"
echo "Exit ${statuses[0]}: 0=bounded reproduction PASS; 1=executed comparison FAIL; 2=BLOCKED."
exit "${statuses[0]}"
