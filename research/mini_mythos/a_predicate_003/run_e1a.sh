#!/usr/bin/env bash
# Wrapper for the FIRST CONTROLLED E1-A RUN.  WRITTEN, NOT RUN.  Do NOT use before the owner separately authorizes the run
# (the runner additionally refuses without AUTHORIZATION_E1A_RUN.json referencing the SHA-256 of the frozen preregistration).
# It only records git state and forwards to the runner; stdout/stderr go to files whose names contain neither "registry.jsonl"
# nor any role label (the supervisor stub inherits these descriptors in launch context L1 and must stay blind).
set -u
cd "$(dirname "$0")/../../.." || exit 2
A=research/mini_mythos/a_predicate_003
RUN_ID="e1a_$(date +%Y%m%d_%H%M%S)"
META="$A/evidence/_meta"
mkdir -p "$META"
git rev-parse HEAD > "$META/${RUN_ID}_git_head_before.txt"
git status --short > "$META/${RUN_ID}_git_status_before.txt"
git check-ignore -v "$A/evidence/$RUN_ID/trials.jsonl" "$A/evidence/$RUN_ID/registry.jsonl" "$A/evidence/$RUN_ID/summary.json" > "$META/${RUN_ID}_check_ignore.txt" 2>&1
python3 "$A/bench/e1a_runner.py" --execute --run-id "$RUN_ID" "$@" > "$META/${RUN_ID}_runner_stdout.txt" 2> "$META/${RUN_ID}_runner_stderr.txt"
RC=$?
git status --short > "$META/${RUN_ID}_git_status_after.txt"
echo "runner exit code: $RC (run id $RUN_ID)"
exit $RC
