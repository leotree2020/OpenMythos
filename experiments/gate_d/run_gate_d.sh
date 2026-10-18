#!/usr/bin/env bash
# Gate D formal diagnostics: D1-D5 on the 30 model states (2 arms x 3 seeds x
# steps 0/3000/6000/9000/12000) with the workload frozen in timing.json, then
# the mechanical grading (analyze.py).
#   - refuses to start (exit 5) if results/ is not empty or timing.json has no
#     frozen workload
#   - at most 4 single-threaded states at a time; the first state that exits
#     non-zero stops the run: nothing new is started, running states are
#     killed, nothing is analysed (exit 3 integrity failure, exit 4 other)
#   - exit 6 if any of the 30 result files is missing afterwards
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONPATH=../..
R=results LOGS=logs STATUS=logs/run_status.txt
if [ -e "$R" ] && [ -n "$(ls -A "$R")" ]; then echo "REFUSED: $R is not empty"; exit 5; fi
python -c "import json,sys; sys.exit(0 if json.load(open('timing.json')).get('frozen_workload') else 1)" \
  || { echo "REFUSED: no frozen workload in timing.json"; exit 5; }
mkdir -p "$R" "$LOGS"
log() { echo "$(date -u +%FT%TZ) $*" | tee -a "$STATUS"; }
log "launch gate D: workload $(python -c "import json; print(json.load(open('timing.json'))['frozen_workload'])")"

declare -A JOB=()
queue=()
for a in openmythos transformer; do for s in 1 2 3; do for t in 12000 9000 6000 3000 0; do
  queue+=("$a $s $t"); done; done; done
launch() {
  python diag_state.py --arm "$1" --seed "$2" --step "$3" > "$LOGS/$1_s$2_step$3.log" 2>&1 &
  JOB[$!]="$1 $2 $3"
  log "started $1_s$2_step$3 (pid $!)"
}
stop_all() {
  local p
  for p in "${!JOB[@]}"; do kill -TERM "$p" 2>/dev/null && log "killed ${JOB[$p]} (pid $p)"; done
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
  job=${JOB[$done_pid]}; unset "JOB[$done_pid]"
  if [ $rc -eq 0 ]; then log "finished $job"; continue; fi
  if [ $rc -eq 3 ]; then log "INTEGRITY FAILURE: $job (see $LOGS)"; fail=3
  else log "RUN ERROR: $job exited with status $rc"; fail=4; fi
  log "stopping: killing ${#JOB[@]} running state(s)"
  stop_all
  break
done
if [ $fail -ne 0 ]; then log "stopped with exit $fail; nothing analysed"; exit $fail; fi
n=$(ls "$R"/*.json | wc -l)
[ "$n" -eq 30 ] || { log "RESULT CHECK FAILED: $n of 30 result files"; exit 6; }
log "all 30 states done"
python analyze.py > "$LOGS/analyze.log" 2>&1
log DONE
