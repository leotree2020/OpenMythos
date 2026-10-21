#!/bin/bash
# E2-c stage-2 freeze, revision r1: ONE launch only. Run it only after an explicit freeze GO, passing the reviewer's
# approved commitment (it must equal APPROVED_SC below character for character):
#
#   REVIEWER_SALT_COMMITMENT_SHA256=52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc \
#   FREEZE_GO_REFERENCE="<GO message id / time>" \
#     setsid nohup bash /home/user/e2c_stage2_freeze_attempt01_r1/run_freeze.sh \
#       > /home/user/e2c_stage2_freeze_attempt01_r1/wrapper_out.txt 2>&1 < /dev/null &
#
# No retry, no --resume, no --accept-stale-supplement. The launch marker is created exclusively first; if a guard then
# fails, nothing is started (exit 97) and the marker stays (a new attempt needs the review). After the driver ends, the
# wrapper records the driver's exit code and exits with that same code.
RUN=$(cd "$(dirname "$0")" && pwd)
E=/home/user/OpenMythos/experiments/gate_e/e2c
C=e79acc6e7a39e1ec4e720d9a66ec05bc8848f150
VSHA=6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a
APPROVED_SC=52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc
AUTH="E2-c Stage2 Formal Freeze GO; accepted verify e79acc6; single initial execution; shared cumulative budget 3600 seconds; freeze only"
REC="$RUN/launch_record.txt"
set -o noclobber
{ echo "launch_once_marker $(date -u +%FT%T.%3NZ) pid $$" > "$RUN/launched.marker"; } 2>/dev/null \
  || { echo "REFUSED $(date -u +%FT%T.%3NZ): launched.marker exists; the freeze is launched once" >> "$REC"; exit 99; }
set +o noclobber
if [ "${REVIEWER_SALT_COMMITMENT_SHA256-}" != "$APPROVED_SC" ]; then
  echo "NO-GO at launch $(date -u +%FT%T.%3NZ): REVIEWER_SALT_COMMITMENT_SHA256 is not the approved commitment; the driver was not started" >> "$REC"; exit 97
fi
if ! bash "$RUN/freeze_guards.sh" launch > "$RUN/launch_guards.txt" 2>&1; then
  echo "NO-GO at launch $(date -u +%FT%T.%3NZ): a guard failed (launch_guards.txt); the driver was not started" >> "$REC"; exit 97
fi
GO="$FREEZE_GO_REFERENCE"
cd "$E" || { echo "NO-GO: cannot enter $E; the driver was not started" >> "$REC"; exit 98; }
{
  echo "start_utc $(date -u +%FT%T.%3NZ)"
  echo "go_reference $GO"
  echo "cwd $PWD"
  echo "command E2C_STAGE2_AUTHORIZED=freeze PYTHONHASHSEED=0 /usr/bin/python3 e2c_stage2.py freeze --expected-commit $C --approved-verify-commit $C --approved-verify-sha256 $VSHA --salt-commitment-sha256 $APPROVED_SC --authorization \"$AUTH\""
} >> "$REC"
env -u REVIEWER_SALT_COMMITMENT_SHA256 -u FREEZE_GO_REFERENCE E2C_STAGE2_AUTHORIZED=freeze PYTHONHASHSEED=0 \
  /usr/bin/python3 e2c_stage2.py freeze \
    --expected-commit $C \
    --approved-verify-commit $C \
    --approved-verify-sha256 $VSHA \
    --salt-commitment-sha256 $APPROVED_SC \
    --authorization "$AUTH" \
  > "$RUN/freeze_stdout.txt" 2> "$RUN/freeze_stderr.txt" &
child=$!
echo "driver_pid $child" >> "$REC"
wait $child
rc=$?
echo "end_utc $(date -u +%FT%T.%3NZ)" >> "$REC"
echo "exit_code $rc" >> "$REC"
exit $rc
