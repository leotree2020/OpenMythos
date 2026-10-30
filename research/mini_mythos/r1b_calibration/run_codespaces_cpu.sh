#!/usr/bin/env bash
# One bounded original-runtime run. Existing evidence is read, never replaced.
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT="${R1B_OUTPUT_DIR:-/workspaces/OpenMythos/mythos_evidence/r1b_calibration_v1}"
PY="${M2_CPU_PYTHON:-/workspaces/mythos-m2-cpu312/bin/python}"
PARCAE="${R1B_PARCAE_DIR:-${M2_PARCAE_DIR:-/workspaces/mythos-parcae-pinned}}"
LOG="$OUT.console.log"
export CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export TORCHDYNAMO_DISABLE=1

if [[ -f "$OUT/result.json" ]]; then
  set +e
  python3 -B "$HERE/run_cpu.py" --read-existing "$OUT/result.json"
  rc=$?
  set -e
  echo "Existing R1-B-CAL result only; exit $rc. No training or overwrite."
  exit "$rc"
fi
if [[ -e "$OUT" || -e "$LOG" ]]; then
  echo "BLOCKED: partial output or log exists; preserve it. $OUT" >&2
  exit 2
fi
if [[ ! -x "$PY" ]]; then
  echo "BLOCKED: pinned CPU Python missing: $PY" >&2; exit 2
fi
if [[ ! -d "$PARCAE/.git" && ! -f "$PARCAE/.git" ]]; then
  echo "BLOCKED: pinned Parcae checkout missing: $PARCAE" >&2; exit 2
fi
ROOT=$(git -C "$HERE" rev-parse --show-toplevel)
cd "$ROOT"
"$PY" -m py_compile "$HERE/task.py" "$HERE/run_cpu.py"
bash -n "$HERE/run_codespaces_cpu.sh"
mkdir -p "$(dirname "$OUT")"
# Exclusive log creation prevents a second launcher from truncating evidence.
(set -o noclobber; : > "$LOG") || { echo "BLOCKED: log already exists" >&2; exit 2; }
printf 'R1-B-CAL source: '; git rev-parse HEAD
set +e
"$PY" -B "$HERE/run_cpu.py" --parcae-dir "$PARCAE" --out "$OUT" 2>&1 | tee -a "$LOG"
rc=${PIPESTATUS[0]}
set -e
if [[ -f "$OUT/result.json" ]]; then sha256sum "$OUT/result.json"; fi
echo "Exit $rc: 0=development qualification PASS; 1=learning floor FAIL; 2=BLOCKED (inspect reason)."
echo "Final test and extra-depth benefit remain NOT TESTED; no automatic follow-up."
exit "$rc"
