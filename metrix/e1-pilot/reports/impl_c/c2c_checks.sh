#!/usr/bin/env bash
# Stage C, C2 second fix commit: the checks of the staged tree, recorded unedited (stdout+stderr merged) by reports/round5/logrun.sh.
#   bash metrix/e1-pilot/reports/impl_c/c2c_checks.sh OUTFILE PYTHON INPUTS SCRATCH
# Run from the repository root. SCRATCH is a directory outside the repository (data and the refused TEST --out).
set -u
O="$1"; PY="$2"; IN="$3"; SC="$4"
L=metrix/e1-pilot/reports/round5/logrun.sh
E="env PYTHONPATH=metrix/e1-pilot/src METRIX_INPUTS_DIR=$IN"
{ echo "# Stage C, C2 second fix commit (staged; parent 0cbee197, the evidence commit after the fix commit 49fc9a35): checks on the staged tree (the working tree of src/, tests/ and run_pilot.py equals the index, checked first and last). Executor, host $(hostname) (Anthropic cloud container, CPU only). $(date -u)"
  echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh. METRIX_INPUTS_DIR=$IN"; } > "$O"
STATE='git diff --quiet -- metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py && echo WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT; git diff --cached HEAD -- metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py | sha256sum; git write-tree; git ls-files -s -- metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py'
bash $L "$O" git ls-remote origin refs/heads/metrix-e1-pilot-protocol-v1
bash $L "$O" git rev-parse HEAD
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
bash $L "$O" $E $PY -m metrix_e1.data generate --inputs "$IN" --out "$SC/c2c_data"
bash $L "$O" $E $PY -m metrix_e1.data verify --inputs "$IN" --data "$SC/c2c_data"
bash $L "$O" $E $PY -m metrix_e1.test_data --inputs "$IN" --data "$SC/c2c_data" --out "$SC/c2c_test_out"
bash $L "$O" bash -c "ls -la $SC/c2c_test_out 2>&1; ls $SC/c2c_data; git status --short -- metrix/e1-pilot/results 2>&1; ls metrix/e1-pilot/results 2>&1"
bash $L "$O" $PY metrix/e1-pilot/reports/round3/outside_metrix_check.py
bash $L "$O" $E $PY -m pytest -q -p no:cacheprovider --durations=8 metrix/e1-pilot/tests
bash $L "$O" $E $PY metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py $PY
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
