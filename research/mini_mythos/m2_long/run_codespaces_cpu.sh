#!/usr/bin/env bash
# Execute preregistered M2-L CPU pilot using isolated clean worktree.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}"
OUT="${M2L_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/m2_long_v1}"
TEXT="research/mini_mythos/m2/evidence/tinyshakespeare.txt"
ALICE="research/mini_mythos/m2_long/evidence/alice_publicdomain.txt"
PIN="69284c13746e849104f738d6d1a347b1f457df76"
if [[ ! -x "$PY" ]]; then echo "BLOCKED: pinned CPU Python missing: $PY" >&2; exit 2; fi
# Fail fast on syntax problems before data download, dependency checks or training.
"$PY" -m py_compile research/mini_mythos/m2_long/experiment.py
bash -n research/mini_mythos/m2_long/run_codespaces_cpu.sh
if [[ ! -d "$PARCAE/.git" ]]; then
  if [[ -d /tmp/mythos-m1-parcae-clean-20261029/.git ]]; then
    PARCAE="/tmp/mythos-m1-parcae-clean-20261029"
  else
    echo "BLOCKED: clean pinned Parcae checkout missing; set M2_PARCAE_DIR" >&2
    exit 2
  fi
fi
if [[ "$(git -C "$PARCAE" rev-parse HEAD)" != "$PIN" ]]; then
  echo "BLOCKED: wrong Parcae source commit" >&2; exit 2
fi
if [[ -n "$(git -C "$PARCAE" status --porcelain --untracked-files=no)" ]]; then
  echo "BLOCKED: modified Parcae tracked files" >&2; exit 2
fi
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "BLOCKED: tracked OpenMythos research files modified" >&2; exit 2
fi
"$PY" - <<'PY'
import sys,torch,numpy,einops
assert sys.version_info[:2] == (3,12),sys.version
assert torch.__version__ == "2.11.0+cpu",torch.__version__
assert numpy.__version__ == "1.26.4",numpy.__version__
assert einops.__version__ == "0.8.0",einops.__version__
print("M2-L CPU ENV PASS",torch.__version__,flush=True)
PY
if [[ ! -f "$TEXT" ]]; then "$PY" research/mini_mythos/m2/download_text.py; fi
# Freeze bytes before training, without inspecting model output or OOD quality.
"$PY" - "$ALICE" <<'PY'
import hashlib,sys
from pathlib import Path
from urllib.request import urlopen
p=Path(sys.argv[1])
url=("https://raw.githubusercontent.com/dakrone/corpus/"
     "f25de55809404f0173504d6853b7b6df93d51ae0/data/alice-in-wonderland.txt")
expected="146e69455b17fac23bee136d0121ced326e0b99caf206df0281cb67241963875"
b=p.read_bytes() if p.exists() else urlopen(url,timeout=120).read()
assert len(b)==167497,(len(b),"unexpected OOD byte count")
assert hashlib.sha256(b).hexdigest()==expected,"independent OOD source drift"
assert hashlib.sha1(b"blob "+str(len(b)).encode()+bytes([0])+b).hexdigest()=="6c89ee6db335fcd14ff756e5841aba7b9cd708d0","Git blob changed"
p.parent.mkdir(parents=True,exist_ok=True)
if not p.exists(): p.write_bytes(b)
print("M2-L SEALED OOD BYTES PASS",expected,flush=True)
PY
mkdir -p "$OUT"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export TORCHDYNAMO_DISABLE=1
printf 'EXPERIMENT CODE HEAD: '; git rev-parse HEAD
printf 'UPSTREAM PIN: '; git -C "$PARCAE" rev-parse HEAD
"$PY" research/mini_mythos/m2_long/experiment.py \
  --parcae-dir "$PARCAE" --text "$TEXT" --alice "$ALICE" --out "$OUT" \
  2>&1 | tee -a "$OUT/run.log"
"$PY" - "$OUT/pilot.json" <<'PY'
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
for k in ("execution_status","continuity_status","budget_status",
          "quality_validation_status","ood_status"):
 print(k,r.get(k,"NOT TESTED"))
PY
sha256sum "$OUT/pilot.json"
echo "Evidence in $OUT"
