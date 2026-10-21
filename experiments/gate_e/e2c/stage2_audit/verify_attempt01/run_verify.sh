#!/bin/bash
# E2-c stage-2 formal verify: one launch only. Started detached (setsid nohup); the driver's stdout and stderr go to
# verify_console.txt, the launch markers and the real exit code to launch_record.txt (both outside the repository).
RUN=$(cd "$(dirname "$0")" && pwd)
E=/home/user/OpenMythos/experiments/gate_e/e2c
SHA=1f6524441c2a08a583be9acc38d14b09848d11d1
REC="$RUN/launch_record.txt"
set -o noclobber
{ echo "launch_once_marker $(date -u +%FT%T.%3NZ) pid $$" > "$RUN/launched.marker"; } 2>/dev/null || { echo "REFUSED: launched.marker exists; the verify is launched once" >> "$REC"; exit 99; }
set +o noclobber
cd "$E" || exit 98
# guards repeated at the instant of launch (any failure: no launch)
if [ "$(GIT_OPTIONAL_LOCKS=0 git rev-parse HEAD)" != $SHA ] || [ -n "$(GIT_OPTIONAL_LOCKS=0 git status --porcelain --untracked-files=all)" ] \
   || [ -e stage2 ] || [ -e e2c_workload_freeze.json ] || env | grep -qE '^(E2C_|STUB_)' \
   || pgrep -f '[e]2c_stage2.py|[_]v2-worker|[e]2c_stage4.py' >/dev/null; then
  echo "NO-GO at launch $(date -u +%FT%T.%3NZ): a guard failed; the driver was not started" >> "$REC"; exit 97
fi
echo "start_utc $(date -u +%FT%T.%3NZ)" >> "$REC"
echo "cwd $PWD" >> "$REC"
echo "command E2C_STAGE2_AUTHORIZED=verify PYTHONHASHSEED=0 $(command -v python3) e2c_stage2.py verify --expected-commit $SHA --authorization \"E2-c Stage2 Formal Verify GO; reviewed implementation 1f652444; single initial execution; cumulative budget 3600 seconds; verify only\"" >> "$REC"
E2C_STAGE2_AUTHORIZED=verify PYTHONHASHSEED=0 python3 e2c_stage2.py verify \
  --expected-commit $SHA \
  --authorization "E2-c Stage2 Formal Verify GO; reviewed implementation 1f652444; single initial execution; cumulative budget 3600 seconds; verify only" &
child=$!
echo "driver_pid $child" >> "$REC"
wait $child
rc=$?
echo "end_utc $(date -u +%FT%T.%3NZ)" >> "$REC"
echo "exit_code $rc" >> "$REC"
