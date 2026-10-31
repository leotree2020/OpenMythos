#!/usr/bin/env bash
# Convenience handoff only. Invoke the unchanged, reviewed D1 parent train phase.
# No prepare/evaluate/manual worker, source edit, installation, retry or resume.
set -euo pipefail
blocked() { printf 'BLOCKED: %s\n' "$1" >&2; exit 2; }
[[ $# -eq 1 && "$1" == --start-training ]] || blocked 'Explicit --start-training acknowledgement required.'
WT=/workspaces/mythos-d1-20261031
OUT=/workspaces/OpenMythos/mythos_evidence/dual_state_v1
PIN=596af7f8997ca793e880a6e1d80c25c7b2043329
REPORT_REF=539310a54492cd219b4e37c252985ac75b73ed7a
REPORT_PATH=research/mini_mythos/dual_state/evidence/D1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md
PREP_SHA=d7ce57ca11316d0ff892bf35b26ec9ed1ef2f04a2b8587dd4671c7eae8b5a1d1
DATA_SHA=9e3700d93bb1c30541e91bc60678a44ff898925f69e2f527f0050de96a0a8750
REPORT_SHA=728d6960a88c997f5cea85d6fa1dcda57d3c5bfdc4378c6e319b9cffeaf57d0d
[[ -d "$WT" ]] || blocked 'Original prepared worktree missing; no replacement created.'
cd "$WT"
[[ "$(git rev-parse --show-toplevel)" == "$WT" && "$(git rev-parse HEAD)" == "$PIN" ]] || blocked 'Wrong worktree or execution pin; no checkout performed.'
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || blocked 'Tracked worktree changes; files retained.'
check_sha() {
  [[ -f "$1" ]] || blocked "Missing file: $1"
  local actual
  actual=$(sha256sum -- "$1")
  [[ "${actual%% *}" == "$2" ]] || blocked "Byte identity mismatch: $1"
}
check_sha "$OUT/prepared.json" "$PREP_SHA"
check_sha "$OUT/data.json" "$DATA_SHA"
for name in train.started jobs review.md training.json result.json evaluate.started evaluations train.error.log; do
  [[ ! -e "$OUT/$name" && ! -L "$OUT/$name" ]] || blocked "Existing/partial evidence retained: $name; no retry/resume."
done
[[ ! -e "$OUT.train.console.log" && ! -L "$OUT.train.console.log" ]] || blocked 'Existing training console log retained; no retry.'
export D1_OUTPUT_DIR="$OUT"
export D1_PYTHON=/workspaces/mythos-m2-cpu312/bin/python
export D1_PARCAE_DIR=/workspaces/mythos-parcae-pinned
[[ -x "$D1_PYTHON" && -d "$D1_PARCAE_DIR" ]] || blocked 'Original environment/upstream missing; no installation.'
REPORT=$(mktemp)
trap 'rm -f -- "$REPORT"' EXIT
# Retrieve the actual supplied report, not an approval request or generated verdict.
git show "$REPORT_REF:$REPORT_PATH" > "$REPORT"
check_sha "$REPORT" "$REPORT_SHA"
printf '%s\n' 'D1: starting ONLY the 12 approved CPU training trajectories.'
printf '%s\n' 'R01 remains OPEN/LOW: a worker numerical FAIL may produce parent BLOCKED. Preserve both; inspect jobs, never auto-retry.'
printf '%s\n' 'No development scoring now. Quality NOT TESTED; candidate selection NOT ASSESSED.'
bash research/mini_mythos/dual_state/run_codespaces_cpu.sh train \
  --review-report "$REPORT" \
  --reviewer 'Claude Code (owner-supplied D1 review; code and prepared bytes checked)' \
  --review-approved
