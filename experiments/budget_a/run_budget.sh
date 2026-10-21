#!/usr/bin/env bash
# Level-A training-budget diagnostic: both arms x seeds 1-3, 12,000 steps with
# the extended schedule, comparability check against the Gate A level-A
# checkpoint at step 3000, checkpoints at 3000/6000/9000; then dev-set curves
# for the intermediate checkpoints, the final test2 evaluation and the
# pre-registered verdict.
#
# Stopping rules (PREREGISTRATION.md 11.1 and revision 2):
#   - refuses to start (exit 5) if the run, log or result paths are not empty
#   - at most 4 trainings at a time; the first one to exit non-zero stops the
#     launch: no further training is started and the running ones are killed
#       exit 3  comparability failure (that run exited 3 and wrote its
#               *_ABORTED.json)
#       exit 4  any other training failure (other exit code, signal, or exit 3
#               without an ABORTED record)
#   - exit 6 if verify_runs.py finds anything wrong with the six results
#     (names, seed, steps, schedule, comparability, stale or extra files)
#   - nothing is evaluated unless all of the above passed
#
# Fault-injection tests only: with BUDGET_TEST_DIR set, everything goes to
# that directory, STEPS/SEEDS/SAVE_AT/COMPARE_AT/REF_DIR may be overridden
# and the final checkpoints are evaluated on the dev set, never on test2.
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH=.
D=experiments/budget_a
GA=experiments/gen_gate_a

if [ -n "${BUDGET_TEST_DIR:-}" ]; then
  OUT=$BUDGET_TEST_DIR
  STEPS=${STEPS:-250} SEEDS=${SEEDS:-97,98,99} SAVE_AT=${SAVE_AT:-20,40}
  COMPARE_AT=${COMPARE_AT:-40} REF_DIR=${REF_DIR:?REF_DIR required in test mode}
  FINAL_SPLIT=dev GATE_A_SHA=
else
  for v in STEPS SEEDS SAVE_AT COMPARE_AT REF_DIR; do
    [ -z "${!v:-}" ] || { echo "$v may only be set with BUDGET_TEST_DIR"; exit 5; }
  done
  OUT=$D
  STEPS=12000 SEEDS=1,2,3 SAVE_AT=3000,6000,9000 COMPARE_AT=3000 REF_DIR=$GA/runs
  FINAL_SPLIT=test2 GATE_A_SHA=--gate-a-sha
fi
RUNS=$OUT/runs LOGS=$OUT/logs
STATUS=$LOGS/launcher_status.txt

# ---- refuse to run on top of earlier outputs
for p in "$RUNS" "$LOGS"; do
  if [ -e "$p" ] && [ -n "$(ls -A "$p")" ]; then
    echo "REFUSED: $p is not empty (earlier outputs must be moved away first)"; exit 5
  fi
done
[ ! -e "$OUT/verdict.md" ] || { echo "REFUSED: $OUT/verdict.md exists"; exit 5; }
mkdir -p "$RUNS" "$LOGS"
touch "$RUNS/.launch_marker"

log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$STATUS"; }
log "launch: steps=$STEPS seeds=$SEEDS save_at=$SAVE_AT compare_at=$COMPARE_AT ref_dir=$REF_DIR out=$OUT"

declare -A JOB=()
queue=()
for s in ${SEEDS//,/ }; do for a in openmythos transformer; do queue+=("$a $s"); done; done

launch() {
  local a=$1 s=$2
  python $GA/train_level.py --level A --arm "$a" --seed "$s" --steps "$STEPS" \
    --schedule extended --save-at "$SAVE_AT" --compare-at "$COMPARE_AT" \
    --compare-ckpt "$REF_DIR/A_${a}_s$s.pt" --out "$RUNS/A_${a}_s$s.json" \
    > "$LOGS/A_${a}_s$s.log" 2>&1 &
  JOB[$!]="$a $s"
  log "started A_${a}_s$s (pid $!)"
}

stop_all() {
  local p
  for p in "${!JOB[@]}"; do
    kill -TERM "$p" 2>/dev/null && log "killed A_${JOB[$p]// /_s} (pid $p)"
  done
  for p in "${!JOB[@]}"; do wait "$p" 2>/dev/null || true; done
  JOB=()
}
trap 'log "launcher interrupted"; stop_all; exit 130' INT TERM HUP

fail=0 next=0
while :; do
  while [ $fail -eq 0 ] && [ ${#JOB[@]} -lt 4 ] && [ $next -lt ${#queue[@]} ]; do
    launch ${queue[$next]}; next=$((next + 1))
  done
  [ ${#JOB[@]} -gt 0 ] || break
  set +e; wait -n -p done_pid "${!JOB[@]}"; rc=$?; set -e
  read -r a s <<< "${JOB[$done_pid]}"; unset "JOB[$done_pid]"
  if [ $rc -eq 0 ]; then
    if [ -e "$RUNS/A_${a}_s${s}_ABORTED.json" ]; then
      log "RUN ERROR: A_${a}_s$s exited 0 but wrote an ABORTED record"; fail=4
    else
      log "finished A_${a}_s$s"; continue
    fi
  elif [ $rc -eq 3 ] && [ -e "$RUNS/A_${a}_s${s}_ABORTED.json" ]; then
    log "COMPARABILITY FAILED: A_${a}_s$s at step $COMPARE_AT (see $RUNS/A_${a}_s${s}_ABORTED.json)"; fail=3
  else
    log "RUN ERROR: A_${a}_s$s exited with status $rc (no comparability record)"; fail=4
  fi
  log "stopping: no further training will be started; killing ${#JOB[@]} running"
  stop_all
  break
done
if [ $fail -ne 0 ]; then
  log "launch stopped with exit $fail after starting $next of ${#queue[@]} trainings; nothing evaluated"
  exit $fail
fi

# ---- strict check of the six results before any evaluation
if ! python $D/verify_runs.py --dir "$RUNS" --marker "$RUNS/.launch_marker" \
    --seeds "$SEEDS" --steps "$STEPS" --save-at "$SAVE_AT" --compare-at "$COMPARE_AT" \
    --ref-dir "$REF_DIR" $GATE_A_SHA 2>&1 | tee -a "$STATUS"; then
  log "RESULT CHECK FAILED: nothing evaluated"; exit 6
fi
log "result check passed"

finals=() steps_ck=()
for a in openmythos transformer; do for s in ${SEEDS//,/ }; do
  finals+=("$RUNS/A_${a}_s$s.pt")
  for n in ${SAVE_AT//,/ }; do steps_ck+=("$RUNS/A_${a}_s${s}_step$n.pt"); done
done; done
python $D/eval_budget.py --split dev --om-loops 4 --ckpt "${steps_ck[@]}" \
  --out "$RUNS/eval_dev_curve.jsonl" > "$LOGS/eval_dev_curve.log" 2>&1
python $D/eval_budget.py --split $FINAL_SPLIT --ckpt "${finals[@]}" \
  --out "$RUNS/eval_$FINAL_SPLIT.jsonl" > "$LOGS/eval_$FINAL_SPLIT.log" 2>&1
python $D/analyze_budget.py "$RUNS/eval_$FINAL_SPLIT.jsonl" --split $FINAL_SPLIT \
  --seeds "$SEEDS" --runs-dir "$RUNS" > "$OUT/verdict.md"
log DONE
