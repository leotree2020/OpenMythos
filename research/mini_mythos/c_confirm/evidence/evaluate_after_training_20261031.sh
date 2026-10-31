#!/usr/bin/env bash
# Convenience entry only: invoke the unchanged reviewed C1 evaluate phase.
# No prepare/train, source modification, manual worker, installation or retry.
set -euo pipefail
REPO=/workspaces/OpenMythos
PIN=8a646eb56a9bcffb9767ad9f50843f85670b2fa1
OUT=/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1
PREP_SHA=2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829
TRAIN_SHA=38d21ce4b23c60afd46d1c1b4361f937452215ce20a886539fe5d1bf2eeb04d1
cd "$REPO" || { echo "BLOCKED: repository directory missing"; exit 2; }
if ! WT=$(git worktree list --porcelain -z | python3 -c '
import os, sys
from pathlib import Path
pin = sys.argv[1]
rows = sys.stdin.buffer.read().split(b"\0\0")
matches = []
for row in rows:
    fields = {}
    for item in row.split(b"\0"):
        k, _, v = os.fsdecode(item).partition(" ")
        fields[k] = v
    if fields.get("HEAD") == pin and fields.get("worktree"):
        p = Path(fields["worktree"])
        if p.is_dir(): matches.append(str(p))
if not matches:
    sys.exit("BLOCKED: no existing worktree at the reviewed pin; no directories changed")
print(sorted(matches)[0])
' "$PIN"); then
  echo 'BLOCKED: cannot resolve an existing reviewed worktree'; exit 2
fi
[[ "$(git -C "$WT" rev-parse HEAD)" == "$PIN" ]] || { echo 'BLOCKED: worktree HEAD differs'; exit 2; }
printf '%s  %s\n' "$PREP_SHA" "$OUT/prepared.json" "$TRAIN_SHA" "$OUT/training.json" | sha256sum -c - || {
  echo "BLOCKED: existing evidence differs or is missing; no evaluation started"; exit 2
}
export C1_OUTPUT_DIR="$OUT"
export C1_PYTHON=/workspaces/mythos-m2-cpu312/bin/python
export C1_PARCAE_DIR=/workspaces/mythos-parcae-pinned
printf 'Reviewed worktree: %s\nEVALUATE ONLY: saved snapshots; no optimizer updates.\n' "$WT"
cd "$WT"
# The reviewed parent verifies all 15 jobs and 20 local snapshot file hashes,
# and each worker verifies snapshot metadata/full state and its C1T byte buffer.
# Existing or partial result handling remains the original read-only/no-retry policy.
bash research/mini_mythos/c_confirm/run_codespaces_cpu.sh evaluate
