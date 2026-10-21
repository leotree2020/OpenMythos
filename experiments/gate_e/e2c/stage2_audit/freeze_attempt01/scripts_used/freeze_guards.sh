#!/bin/bash
# Read-only guards for the single E2-c stage-2 freeze (revision r1). Run by the preflight (mode "preflight") and again
# by run_freeze.sh at the instant of launch (mode "launch": the reviewer's approved commitment and a GO reference are
# then required). Every command's own exit status is checked before its output is read; a failed command is a FAIL,
# never "no change" or "nothing found". Writes nothing in the repository. Exit 0 only when every guard passes.
set -u
MODE=${1:?usage: freeze_guards.sh preflight|launch}
export GIT_OPTIONAL_LOCKS=0 PYTHONDONTWRITEBYTECODE=1
D=$(cd "$(dirname "$0")" && pwd)
. "$D/checks_lib.sh"
REPO=/home/user/OpenMythos
E=$REPO/experiments/gate_e/e2c
C=e79acc6e7a39e1ec4e720d9a66ec05bc8848f150
VSHA=6331b06a73071c1a8d464a96fe47c4c8499bf1456e0c1f87dfbfbee16611564a
SSHA=a8bdcd34199441038442111ef28dac221ec37c7eb063b772fbbbb6750c6055fc
APPROVED_SC=52d1b31e99a7a277ab4bc8cec1ee736994c79606ffce6aa0c5a73176d8d181bc
fail=0
ok() { echo "PASS $*"; }
no() { echo "FAIL $*"; fail=1; }
echo "# freeze guards r1 ($MODE) $(date -u +%FT%T.%3NZ)"
if git_capture h -C "$REPO" rev-parse HEAD; then
  [ "$h" = $C ] && ok "G1 local HEAD $h" || no "G1 local HEAD $h"
else no "G1 git rev-parse HEAD failed"; fi
if git_capture r -C "$REPO" ls-remote origin refs/heads/claude/openmythos-research; then
  r=${r%%$'\t'*}; [ "$r" = $C ] && ok "G2 remote claude/openmythos-research $r" || no "G2 remote branch '$r' (empty: ref missing)"
else no "G2 git ls-remote failed"; fi
if git_capture st -C "$REPO" status --porcelain --untracked-files=all; then
  ops=0; for x in MERGE_HEAD rebase-merge rebase-apply CHERRY_PICK_HEAD; do [ -e "$REPO/.git/$x" ] && ops=$((ops + 1)); done
  n=$(count_lines "$st"); [ "$n" = 0 ] && [ $ops = 0 ] && ok "G3 working tree clean, no operation in progress" || no "G3 status lines $n, operations $ops"
else no "G3 git status failed"; fi
if git_capture sh -C "$REPO" rev-parse --is-shallow-repository; then
  [ "$sh" = false ] && ok "G4 full (non-shallow) clone" || no "G4 shallow: $sh"
else no "G4 git rev-parse --is-shallow-repository failed"; fi
present=""
for f in e2c_workload_freeze.json stage2/stage2_freeze_receipt.json stage2/verify_stop.json stage2/budget_review_required.json stage2/budget_review_required_freeze.json; do
  [ -e "$E/$f" ] && present="$present $f"
done
[ -d "$E/stage2" ] && [ -z "$present" ] && ok "G5 no freeze, receipt, stop or review record in the working tree" || no "G5 stage2/ missing or present:$present"
if tmp=$(find "$E" "$E/stage2" -maxdepth 1 -name '.*.tmp.*' -print 2>&1); then
  n=$(count_lines "$tmp"); [ "$n" = 0 ] && ok "G6 no temporary file of an interrupted write in e2c/ or stage2/" || no "G6 temporary files: $tmp"
else no "G6 find failed: $tmp"; fi
if sha_of a "$E/stage2/stage2_verify.json" && sha_of b "$E/stage2/v2_streams.json"; then
  [ ${#VSHA} = 64 ] && [ "$a" = $VSHA ] && [ "$b" = $SSHA ] && ok "G7 stage2_verify.json $a; v2_streams.json $b" || no "G7 stage2_verify.json $a / v2_streams.json $b"
else no "G7 sha256sum failed"; fi
lg=$(cd "$D" && python3 -B ledger_guard.py 2>&1); lrc=$?
printf '%s\n' "$lg" | sed 's/^/    /'
[ $lrc = 0 ] && ok "G8 ledger unchanged since e79acc6: one closed PASS verify interval, caps 3600, no supplement or stale report" || no "G8 ledger (exit $lrc)"
names=$(env | cut -d= -f1)
none_matching bad '^(E2C_|STUB_)' "$names"; case $? in
  0) ok "G9 no E2C_* / STUB_* variable set" ;; 1) no "G9 set: $(echo $bad)" ;; *) no "G9 variable check failed" ;; esac
no_process pr '[e]2c_stage2\.py (verify|freeze|check|_v2-worker)|[e]2c_stage4\.py|[r]un_e2c\.py|[t]rain_e2c\.py'; case $? in
  0) ok "G10 no E2-c driver, worker, job, launcher or trainer running" ;; 1) no "G10 running: $pr" ;; *) no "G10 pgrep failed" ;; esac
dfout=$(df -B1M --output=avail "$REPO" 2>&1)
dfrc=$?
if [ $dfrc -ne 0 ]; then
  no "G11 df failed (exit $dfrc): $(printf '%s' "$dfout" | tr '\n' ' ' | head -c 200)"
else
  av=$(printf '%s\n' "$dfout" | tail -n 1 | tr -d ' ')
  if [[ "$av" =~ ^[0-9]+$ ]]; then
    [ "$av" -gt 1000 ] && [ -w "$D" ] && ok "G11 disk ${av} MiB available; log directory $D writable" || no "G11 disk $av MiB / log directory"
  else
    no "G11 df output not parseable: $(printf '%s' "$dfout" | tr '\n' ' ' | head -c 200)"
  fi
fi
if [ "$MODE" = launch ]; then
  cg=$(cd "$D" && python3 -B commitment_guard.py 2>&1); crc=$?
  [ $crc = 0 ] && ok "G12 $cg" || no "G12 $cg"
  [ -n "${FREEZE_GO_REFERENCE:-}" ] && ok "G13 GO reference: $FREEZE_GO_REFERENCE" || no "G13 FREEZE_GO_REFERENCE missing (the explicit freeze GO)"
else
  [[ "$APPROVED_SC" =~ ^[0-9a-f]{64}$ ]] && [ -z "${REVIEWER_SALT_COMMITMENT_SHA256+x}" ] \
    && ok "G12 approved commitment on file ${APPROVED_SC}; no commitment variable set before the GO" \
    || no "G12 approved commitment malformed or a commitment variable already set"
fi
echo "guards ($MODE): $([ $fail = 0 ] && echo ALL PASS || echo FAILED)"
exit $fail
