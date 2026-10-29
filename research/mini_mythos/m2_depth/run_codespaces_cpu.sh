#!/usr/bin/env bash
# Read existing weights only; no clone, package installation, backward or optimizer.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
EVIDENCE="${M2D_EVIDENCE:-/workspaces/OpenMythos/mythos_evidence/m2_long_v1}"
TEXT="${M2D_TEXT:-/workspaces/mythos-m2long-20261029/research/mini_mythos/m2/evidence/tinyshakespeare.txt}"
OUT="${M2D_OUTPUT:-/workspaces/OpenMythos/mythos_evidence/m2_depth_v1}"
if [[ ! -x "$PY" ]]; then echo "BLOCKED: pinned CPU Python absent: $PY" >&2; exit 2; fi
if [[ ! -f "$EVIDENCE/pilot.json" || ! -f "$TEXT" ]]; then
  echo "BLOCKED: existing M2-L evidence or text missing; do not retrain" >&2; exit 2
fi
if [[ -e "$OUT" || -e "$OUT.console.log" ]]; then
  echo "BLOCKED: output already exists; preserve it and set M2D_OUTPUT to a new path" >&2; exit 2
fi
"$PY" -B -c 'from pathlib import Path; p=Path("research/mini_mythos/m2_depth/run_depth.py"); compile(p.read_bytes(),str(p),"exec"); print("M2-D syntax PASS")'
mkdir -p "$(dirname "$OUT")"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCHDYNAMO_DISABLE=1 PYTHONDONTWRITEBYTECODE=1
set +e
"$PY" -B research/mini_mythos/m2_depth/run_depth.py \
  --parcae-dir "$PARCAE" --evidence "$EVIDENCE" --text "$TEXT" --out "$OUT" \
  2>&1 | tee "$OUT.console.log"
CODES=("${PIPESTATUS[@]}")
set -e
RC="${CODES[0]}"
if [[ "${CODES[1]}" != 0 ]]; then echo "BLOCKED: saving console log failed" >&2; exit 2; fi
if [[ -f "$OUT/result.json" ]]; then
  "$PY" -B - "$OUT/result.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
for k in ('execution_status','baseline_status','primary_status'):
 print(k,r.get(k,'NOT TESTED'))
PY
  sha256sum "$OUT/result.json"
fi
printf 'Exit code %s: 0=primary screen PASS, 1=primary screen FAIL, 2=BLOCKED.\n' "$RC"
exit "$RC"
