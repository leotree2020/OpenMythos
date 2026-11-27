#!/usr/bin/env bash
# Stage C, C3: the final checks (Implementation Task Order V1 section 11, items 1, 2, 4, 7) on the staged tree of the C3
# commit, recorded unedited (stdout+stderr merged) by reports/round5/logrun.sh. The code (src/, tests/, run_pilot.py) is
# that of CODE_COMMIT (the third C2 fix commit); the first and last blocks show it is unchanged.
#   bash metrix/e1-pilot/reports/impl_c/c3_checks.sh OUTFILE PYTHON INPUTS SCRATCH CODE_COMMIT
# Run from the repository root. SCRATCH is a directory outside the repository (data and the refused TEST --out).
set -u
O="$1"; PY="$2"; IN="$3"; SC="$4"; CC="$5"
L=metrix/e1-pilot/reports/round5/logrun.sh
E="env PYTHONPATH=metrix/e1-pilot/src METRIX_INPUTS_DIR=$IN"
C="metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py"
{ echo "# Stage C, C3 commit (staged; code of $CC): final checks on the staged tree. Executor, host $(hostname) (Anthropic cloud container, CPU only, no GPU). $(date -u)"
  echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh. METRIX_INPUTS_DIR=$IN"; } > "$O"
STATE="git rev-parse HEAD; git write-tree; git diff --quiet -- $C && echo WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --quiet $CC -- $C && echo INDEX_EQUALS_${CC}_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --stat HEAD; sha256sum metrix/e1-pilot/reports/impl_c/c3_checks.sh"
bash $L "$O" git ls-remote origin refs/heads/metrix-e1-pilot-protocol-v1
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
bash $L "$O" $E $PY -m metrix_e1.data generate --inputs "$IN" --out "$SC/c3_data"
bash $L "$O" $E $PY -m metrix_e1.data verify --inputs "$IN" --data "$SC/c3_data"
bash $L "$O" $E $PY -m metrix_e1.test_data --inputs "$IN" --data "$SC/c3_data" --out "$SC/c3_test_out"
bash $L "$O" bash -c "ls -la $SC/c3_test_out 2>&1; ls $SC/c3_data; git status --short -- metrix/e1-pilot/results 2>&1; ls metrix/e1-pilot/results 2>&1"
bash $L "$O" $PY metrix/e1-pilot/reports/round3/outside_metrix_check.py
bash $L "$O" $E $PY -m pytest -q -p no:cacheprovider --durations=8 metrix/e1-pilot/tests
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
