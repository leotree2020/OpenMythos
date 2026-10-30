#!/usr/bin/env bash
# Run only in an already-created, pinned isolated worktree. No downloads or resets.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
OUT="${R1A_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/r1_addition_v1}"
DIR=research/mini_mythos/r1_addition
if [[ -f "$OUT/result.json" ]]; then
  set +e
  python3 - "$OUT/result.json" <<'PY'
import json,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]); b=p.read_bytes(); r=json.loads(b)
if r.get('experiment')!='MYTHOS-R1A-CARRY-ADDITION-CPU-V1':
 print('BLOCKED: other experiment in output directory'); sys.exit(2)
print('EXISTING RESULT; NO RERUN')
for k in ('execution_status','execution_scope','baseline_learning_status','parcae_learning_status','test_status','primary'):
 print(k, r.get(k,'NOT TESTED'))
print(hashlib.sha256(b).hexdigest(),p)
code=r.get('exit_code',2)
sys.exit(code if type(code) is int and code in (0,1,2) else 2)
PY
  rc=$?
  exit "$rc"
fi
if [[ -e "$OUT" || -e "$OUT.console.log" ]]; then
  echo 'BLOCKED: partial existing output/log preserved; no rerun or deletion' >&2; exit 2
fi
[[ -x "$PY" ]] || { echo "BLOCKED: missing existing CPU Python $PY" >&2; exit 2; }
[[ -d "$PARCAE/.git" ]] || { echo "BLOCKED: missing pinned Parcae $PARCAE" >&2; exit 2; }
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
"$PY" -B -m unittest discover -s "$DIR" -p 'test_task.py' -v
mkdir -p "$(dirname "$OUT")"
set +e
"$PY" -B "$DIR/run_cpu.py" --parcae-dir "$PARCAE" --out "$OUT" 2>&1 | tee "$OUT.console.log"
rc=${PIPESTATUS[0]}
set -e
echo "R1-A exit $rc: 0=primary benefit PASS; 1=scientific/learning FAIL; 2=BLOCKED."
exit "$rc"
