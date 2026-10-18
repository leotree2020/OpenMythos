#!/usr/bin/env bash
# Fault-injection tests of run_gate_d.sh with a stub in place of diag_state.py
# (no model, no diagnostic data). Results in validation/launcher_tests.txt.
set -uo pipefail
cd "$(dirname "$0")"
T=$(mktemp -d) OUTF=validation/launcher_tests.txt
: > "$OUTF"
pass=0 fail=0
check() { if [ "$2" = "$3" ]; then r=PASS pass=$((pass+1)); else r=FAIL fail=$((fail+1)); fi
  echo "$r | $1 | expected $2, got $3 | $4" | tee -a "$OUTF"; }
cat > "$T/stub.sh" <<'S'
#!/usr/bin/env bash
# args: --arm A --seed S --step T --out-dir R ; behaviour from STUB_FAIL ("arm_seed_step:code") and STUB_SLEEP
while [ $# -gt 0 ]; do case $1 in --arm) A=$2;; --seed) S=$2;; --step) T=$2;; --out-dir) R=$2;; esac; shift 2; done
# a failing state fails at once; the others take STUB_SLEEP seconds
if [ "${STUB_FAIL:-}" = "${A}_${S}_${T}:3" ]; then sleep 0.2; echo "INTEGRITY FAILURE" >&2; exit 3; fi
if [ "${STUB_FAIL:-}" = "${A}_${S}_${T}:1" ]; then sleep 0.2; echo "crash" >&2; exit 1; fi
sleep "${STUB_SLEEP:-0.2}"
if [ "${STUB_FAIL:-}" = "${A}_${S}_${T}:skip" ]; then exit 0; fi
echo '{}' > "$R/${A}_s${S}_step${T}.json"
S
chmod +x "$T/stub.sh"
run() { mkdir -p "$T/$1"; [ -e "$T/$1/timing.json" ] || echo '{"frozen_workload": {"level": "stub"}}' > "$T/$1/timing.json"
  env GATE_D_TEST_DIR="$T/$1" GATE_D_TEST_CMD="$T/stub.sh" "${@:2}" bash run_gate_d.sh > "$T/$1.out" 2>&1; }
started() { grep -c 'started ' "$T/$1/logs/run_status.txt"; }
killed() { grep -c 'killed ' "$T/$1/logs/run_status.txt" || true; }
left() { ps -eo args | grep -c "[s]tub.sh.*$T/$1" || true; }
run ok; check "normal: 30 stub states" 0 $? "$(ls "$T/ok/results" | wc -l) result files"
run ok; check "relaunch on non-empty results" 5 $? "$(tail -1 "$T/ok.out")"
run integ STUB_FAIL=openmythos_1_9000:3 STUB_SLEEP=3; rc=$?
check "integrity failure -> exit 3" 3 $rc "$(grep -h INTEGRITY "$T/integ/logs/run_status.txt")"
check "integrity: no new state after failure" 4 "$(started integ)" "started=$(started integ) of 30"
check "integrity: running states killed" 3 "$(killed integ)" ""
check "integrity: nothing left running" 0 "$(left integ)" ""
check "integrity: no analysis" no "$( [ -e "$T/integ/logs/analyze.log" ] && echo yes || echo no)" ""
run crash STUB_FAIL=transformer_2_6000:1 STUB_SLEEP=0.3; rc=$?
check "other error: running states killed" 3 "$(killed crash)" ""
check "other error -> exit 4" 4 $rc "$(grep -h 'RUN ERROR' "$T/crash/logs/run_status.txt")"
check "other error: nothing left running" 0 "$(left crash)" ""
run miss STUB_FAIL=openmythos_3_0:skip; rc=$?
check "missing result file -> exit 6" 6 $rc "$(grep -h 'RESULT CHECK' "$T/miss/logs/run_status.txt")"
GATE_D_TEST_CMD="$T/stub.sh" bash run_gate_d.sh > "$T/formal.out" 2>&1; rc=$?
check "stub command without test dir refused" 5 $rc "$(cat "$T/formal.out")"
mkdir -p "$T/nowl"; echo '{}' > "$T/nowl/timing.json"
env GATE_D_TEST_DIR="$T/nowl" GATE_D_TEST_CMD="$T/stub.sh" bash run_gate_d.sh > "$T/nowl.out" 2>&1; rc=$?
check "no frozen workload refused" 5 $rc "$(cat "$T/nowl.out")"
echo "TOTAL: $pass passed, $fail failed" | tee -a "$OUTF"
rm -rf "$T"
[ $fail -eq 0 ]
