#!/usr/bin/env bash
# Preserve old and partial evidence. This launcher never installs or downloads.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=${MECH_C_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/mech_c_v1}
PY=${MECH_C_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}
UP=${MECH_C_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}
if [[ -f "$OUT/result.json" ]]; then
  python3 - "$OUT/result.json" <<'PY'
import json,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);raw=p.read_bytes()
try:r=json.loads(raw)
except (ValueError,TypeError):
    print('BLOCKED: invalid existing JSON retained.');raise SystemExit(2)
if not isinstance(r,dict) or r.get('experiment')!='MYTHOS-MECH-C-LORA-CPU-V1':
    print('BLOCKED: unrelated existing evidence, no change.');raise SystemExit(2)
for k in ('execution_status','native_compatibility_status','pairing_status','capacity_control_status','outcome','error'):
    if k in r: print(k,json.dumps(r[k],ensure_ascii=False))
print(hashlib.sha256(raw).hexdigest(),p)
print('Existing evidence: READ ONLY. No training or overwrite.')
rc=r.get('exit_code',2)
raise SystemExit(rc if type(rc) is int and rc in (0,1,2) else 2)
PY
  exit $?
fi
if [[ -e "$OUT" || -e "$OUT.console.log" ]]; then
  echo 'BLOCKED: partial directory/log exists; retain it, do not retrain.';exit 2
fi
if [[ ! -x "$PY" || ! -d "$UP" ]]; then
  echo "BLOCKED: existing CPU runtime/upstream missing: $PY ; $UP";exit 2
fi
if [[ "$(git -C "$UP" rev-parse HEAD)" != 69284c13746e849104f738d6d1a347b1f457df76 ||
      -n "$(git -C "$UP" status --porcelain --untracked-files=no)" ]]; then
  echo 'BLOCKED: upstream pin/cleanliness mismatch; no repair.';exit 2
fi
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$(dirname "$OUT")"
# Reserve log without clobbering another invocation.
(set -o noclobber; : > "$OUT.console.log") || exit 2
set +e
"$PY" -B "$HERE/run_cpu.py" --parcae-dir "$UP" --out "$OUT" 2>&1 | tee -a "$OUT.console.log"
rc=${PIPESTATUS[0]}
set -e
echo "MECH-C exit $rc: 0=primary C4-S16 PASS, 1=completed primary FAIL, 2=BLOCKED."
exit "$rc"
