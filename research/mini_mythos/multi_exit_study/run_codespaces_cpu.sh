#!/usr/bin/env bash
# Default is prepare: no training/H1. Explicit train requires a real review report.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PHASE=${1:-prepare}
if [[ $# -gt 0 ]]; then shift; fi
case "$PHASE" in prepare) FILE=prepared.json;; train) FILE=training.json;; evaluate) FILE=result.json;; *) echo 'Use prepare, train, or evaluate';exit 2;; esac
OUT=${MES1_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/mes1_v1}
PY=${MES1_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}
UP=${MES1_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}
if [[ -e "$OUT/$FILE" ]]; then
  python3 - "$OUT/$FILE" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);raw=p.read_bytes()
try:
    r=json.loads(raw)
    assert r.get('experiment')=='MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1'
    rc=r.get('exit_code',2);assert type(rc)is int and rc in (0,1,2)
except Exception:
    print('BLOCKED: invalid/unrelated existing bytes retained');raise SystemExit(2)
for k in ('phase','status','budget','outcome','error'): 
    if k in r: print(k,json.dumps(r[k],ensure_ascii=False))
print(hashlib.sha256(raw).hexdigest(),p)
print('Existing phase READ ONLY: no rerun, overwrite or automatic resume.')
raise SystemExit(rc)
PY
  exit $?
fi
[[ -x "$PY" && -d "$UP" ]] || { echo 'BLOCKED: original CPU environment/upstream missing; no installation';exit 2; }
if [[ "$PHASE" == prepare && ( -e "$OUT" || -e "$OUT.prepare.console.log" ) ]]; then
  echo 'BLOCKED: partial prepare evidence retained';exit 2
fi
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$(dirname "$OUT")"
set +e
"$PY" -B "$HERE/run_cpu.py" "$PHASE" --out "$OUT" --parcae-dir "$UP" "$@" 2>&1 | tee -a "$OUT.$PHASE.console.log"
rc=${PIPESTATUS[0]}
set -e
printf 'MES-1 %s exit %s. Prepare/train PASS is not quality PASS.\n' "$PHASE" "$rc"
exit "$rc"
