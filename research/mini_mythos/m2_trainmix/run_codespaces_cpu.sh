#!/usr/bin/env bash
# One bounded paired CPU intervention. Never install packages or overwrite evidence.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
EVIDENCE="${M2L_EVIDENCE_DIR:-/workspaces/OpenMythos/mythos_evidence/m2_long_v1}"
TEXT="${M2_TEXT:-/workspaces/mythos-m2long-20261029/research/mini_mythos/m2/evidence/tinyshakespeare.txt}"
OUT="${M2T_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/m2_trainmix_v1}"
if [[ ! -x "$PY" ]]; then echo "BLOCKED: existing pinned Python missing: $PY" >&2; exit 2; fi
if [[ ! -d "$PARCAE/.git" ]]; then echo "BLOCKED: existing upstream checkout missing: $PARCAE" >&2; exit 2; fi
if [[ ! -f "$EVIDENCE/pilot.json" || ! -f "$TEXT" ]]; then echo 'BLOCKED: saved evidence or corpus missing' >&2; exit 2; fi
if [[ -e "$OUT" || -e "$OUT.console.log" ]]; then echo "BLOCKED: output already exists; not deleting or rerunning: $OUT" >&2; exit 2; fi
bash -n research/mini_mythos/m2_trainmix/run_codespaces_cpu.sh
"$PY" -m py_compile research/mini_mythos/m2_trainmix/run_trainmix.py
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCHDYNAMO_DISABLE=1 PYTHONDONTWRITEBYTECODE=1
mkdir -p "$(dirname "$OUT")"
echo 'M2-T: fixed2 versus balanced1/3; native model training has not yet passed.'
set +e
"$PY" research/mini_mythos/m2_trainmix/run_trainmix.py \
  --parcae-dir "$PARCAE" --evidence "$EVIDENCE" --text "$TEXT" --out "$OUT" \
  2>&1 | tee "$OUT.console.log"
statuses=("${PIPESTATUS[@]}")
set -e
code="${statuses[0]}"
if [[ "${statuses[1]}" -ne 0 ]]; then echo 'BLOCKED: console log write failed' >&2; exit 2; fi
if [[ -f "$OUT/result.json" ]]; then
  "$PY" - "$OUT/result.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
print('execution_status',r['execution_status'])
print('budget_status',r['budget_status'])
for k,v in (r.get('outcome') or {}).items():
 if k.endswith('_status'):print(k,v)
PY
  sha256sum "$OUT/result.json"
fi
printf 'Exit code %s: 0=intervention screen PASS, 1=screen FAIL, 2=BLOCKED/execution error. Read all component statuses.\n' "$code"
exit "$code"
