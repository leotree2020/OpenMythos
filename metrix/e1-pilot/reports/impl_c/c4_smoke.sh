#!/usr/bin/env bash
# Stage C, C4 code commit: the CPU smoke test (Implementation Task Order V1 section 7) on the staged code, 3 optimizer
# steps per training run; work directory outside the repository; run alone, after c4_checks.sh. Recorded unedited
# (stdout+stderr merged) by reports/round5/logrun.sh.
#   bash metrix/e1-pilot/reports/impl_c/c4_smoke.sh OUTFILE PYTHON INPUTS WORK
# Run from the repository root.
set -u
O="$1"; PY="$2"; IN="$3"; W="$4"
L=metrix/e1-pilot/reports/round5/logrun.sh
C="metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py"
{ echo "# Stage C, C4 code commit (staged; parent $(git rev-parse HEAD)): the CPU smoke test on the staged code, 3 optimizer steps per training run; work directory outside the repository; run alone, after c4_02. Executor, host $(hostname) (Anthropic cloud container, CPU only, no GPU). $(date -u)"
  echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh."; } > "$O"
STATE="git rev-parse HEAD; git write-tree; git diff --quiet -- $C && echo WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT; git diff --cached HEAD -- $C | sha256sum; git ls-files -s -- $C; sha256sum metrix/e1-pilot/reports/impl_c/c4_smoke.sh"
bash $L "$O" bash -c "$STATE"
bash $L "$O" $PY metrix/e1-pilot/run_pilot.py smoke --steps 3 --inputs "$IN" --work "$W"
bash $L "$O" bash -c "cd $W && find . -type f | sort | xargs ls -l | awk '{print \$5, \$9}'"
bash $L "$O" bash -c "cd $W && echo TEST files: \$(find . -name test_qa.jsonl -o -name general_test.jsonl | wc -l); cat checkpoints/LABEL.txt data/LABEL.txt preflight/LABEL.txt"
bash $L "$O" $PY -c "import json,sys; r=json.load(open(sys.argv[1])); pre=r['preflight']; print(json.dumps({k: pre.get(k) for k in ('b17_estimate_hours','checkpoint_overhead','st11_estimate_hours','st11_reads','st11_bound_hours','st11','timing')}, indent=1, sort_keys=True))" "$W/records/step2_record.json"
bash $L "$O" bash -c "$STATE; ls metrix/e1-pilot/results 2>&1"
