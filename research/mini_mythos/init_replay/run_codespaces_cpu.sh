#!/usr/bin/env bash
# Existing inputs only. Repeated invocation reads prior result; never overwrites it.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
EVIDENCE="${M2L_EVIDENCE_DIR:-/workspaces/OpenMythos/mythos_evidence/m2_long_v1}"
OUT="${INIT01_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/init_replay_v1}"
if [[ ! -x "$PY" ]]; then echo "BLOCKED: existing CPU Python not found: $PY" >&2; exit 2; fi
if [[ -e "$OUT" ]]; then
  if [[ ! -f "$OUT/result.json" ]]; then
    echo "BLOCKED: output exists without result.json; preserve it, do not delete: $OUT" >&2
    exit 2
  fi
  echo 'Existing result: read only; no native model invocation.'
  "$PY" -I -B - "$OUT/result.json" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); b=p.read_bytes(); r=json.loads(b)
print('experiment',r.get('experiment'))
print('execution_status',r.get('execution_status'))
print('initialization_replay_status',r.get('initialization_replay_status'))
print('rows',len(r.get('rows',[])))
if r.get('error'):print(r['error'])
print('sha256',hashlib.sha256(b).hexdigest(),str(p))
raise SystemExit(2 if r.get('execution_status')!='PASS' else (0 if r.get('initialization_replay_status')=='PASS' else 1))
PY
  exit "$?"
fi
if [[ ! -d "$PARCAE/.git" || ! -f "$EVIDENCE/pilot.json" ]]; then
  echo 'BLOCKED: existing upstream or M2-L pilot missing; no clone/download performed.' >&2; exit 2
fi
bash -n research/mini_mythos/init_replay/run_codespaces_cpu.sh
export CUDA_VISIBLE_DEVICES='' OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCHDYNAMO_DISABLE=1 PYTHONDONTWRITEBYTECODE=1
set +e
"$PY" -I -B research/mini_mythos/init_replay/replay_initialization.py \
  --parcae-dir "$PARCAE" --evidence "$EVIDENCE" --out "$OUT"
code=$?
set -e
printf 'INIT-01 exit %s: 0=exact six-state replay PASS, 1=completed mismatch, 2=BLOCKED. No training occurred.\n' "$code"
exit "$code"
