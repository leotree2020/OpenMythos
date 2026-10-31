#!/usr/bin/env bash
# C1 default: prepare only. Each later phase must be explicitly requested.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PHASE=${1:-prepare}
if [[ $# -gt 0 ]]; then shift; fi
case "$PHASE" in prepare) FILE=prepared.json;; train) FILE=training.json;; evaluate) FILE=result.json;; *) echo 'Use prepare, train, or evaluate'; exit 2;; esac
OUT=${C1_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1}
PY=${C1_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}
UP=${C1_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}
if [[ -e "$OUT/$FILE" ]]; then
  python3 - "$OUT/$FILE" "$PHASE" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); raw=p.read_bytes()
def pairs(items):
    d={}
    for k,v in items:
        if k in d: raise ValueError('duplicate key')
        d[k]=v
    return d
def bad(x): raise ValueError(x)
try:
    r=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    assert r.get('experiment')=='MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1' and r.get('phase')==sys.argv[2]
    rc=r.get('exit_code',2); assert type(rc)is int and rc in (0,1,2)
except Exception:
    print('BLOCKED: invalid/unrelated existing bytes retained'); raise SystemExit(2)
for k in ('phase','status','budget','outcome','error'):
    if k in r: print(k,json.dumps(r[k],ensure_ascii=False))
print(hashlib.sha256(raw).hexdigest(),p)
print('Existing phase READ ONLY; no overwrite, retry or automatic resume.')
raise SystemExit(rc)
PY
  exit $?
fi
[[ -x "$PY" && -d "$UP" ]] || { echo 'BLOCKED: original CPU environment/upstream missing; no installation'; exit 2; }
if [[ "$PHASE" == prepare && ( -e "$OUT" || -e "$OUT.prepare.console.log" ) ]]; then
  echo 'BLOCKED: partial prepare evidence retained'; exit 2
fi
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$(dirname "$OUT")"
set +e
"$PY" -B "$HERE/run_cpu.py" "$PHASE" --out "$OUT" --parcae-dir "$UP" "$@" 2>&1 | tee -a "$OUT.$PHASE.console.log"
rc=${PIPESTATUS[0]}
set -e
printf 'C1 %s exit %s. Execution/prepare PASS is not candidate quality PASS.\n' "$PHASE" "$rc"
exit "$rc"
