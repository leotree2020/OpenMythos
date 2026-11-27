#!/usr/bin/env bash
# Stage C, C4 documentation commit, round 2 (RUNBOOK_A100.md per tasks/IMPL_C4_RULING.md items 1 and 3-7, IMPL_C_REPORT.md,
# DEFERRED_MINORS.md 1.39): checks of the staged tree, recorded unedited (stdout+stderr merged) by reports/round5/logrun.sh.
#   bash metrix/e1-pilot/reports/impl_c/c4_docs_checks_r2.sh OUTFILE PYTHON INPUTS CODE_COMMIT
# Run from the repository root.
set -u
O="$1"; PY="$2"; IN="$3"; CC="$4"
L=metrix/e1-pilot/reports/round5/logrun.sh
E="env PYTHONPATH=metrix/e1-pilot/src METRIX_INPUTS_DIR=$IN"
C="metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py"
RB=metrix/e1-pilot/RUNBOOK_A100.md
DOCS="metrix/e1-pilot/RUNBOOK_A100.md metrix/e1-pilot/reports/IMPL_C_REPORT.md metrix/e1-pilot/reports/DEFERRED_MINORS.md metrix/e1-pilot/reports/impl_c/c4_04_uv_check.txt metrix/e1-pilot/reports/impl_c/c4_07_runbook_sim.txt metrix/e1-pilot/reports/impl_c/c4_runbook_sim.sh"
{ echo "# Stage C, C4 documentation commit, round 2 (staged; parent $(git rev-parse HEAD); code of $CC): checks on the staged tree. Executor, host $(hostname) (Anthropic cloud container, CPU only, no GPU). $(date -u)"
  echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh. METRIX_INPUTS_DIR=$IN"; } > "$O"
STATE="git rev-parse HEAD; git write-tree; git diff --quiet -- $C && echo WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --quiet $CC -- $C && echo INDEX_EQUALS_${CC}_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --stat HEAD; sha256sum metrix/e1-pilot/reports/impl_c/c4_docs_checks_r2.sh; git ls-files -s -- $DOCS; git diff --cached HEAD -- $DOCS | sha256sum"
bash $L "$O" git ls-remote origin refs/heads/metrix-e1-pilot-protocol-v1
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
bash $L "$O" bash -c "echo 'pending wording in the RUNBOOK (expected none):'; grep -n '待 Review Gate\|待决\|report_only\|b17_plus' $RB; echo \"grep exit \$?\""
bash $L "$O" $E $PY -c "
import re, sys
from metrix_e1 import frozen as FZ, record as R
fields = R.template_fields(FZ.load().protocol_text)
rb = open('$RB', encoding='utf-8').read()
block = re.search(r'\n\`\`\`\n(Experiment ID: METRIX-E1-PILOT-l6-compare-.*?)\n\`\`\`\n', rb, flags=re.S).group(1).split('\n')
names = [ln.split(': ', 1)[0] for ln in block]
print('protocol section 10 fields', len(fields), '| RUNBOOK 3.7 item 5 template lines', len(block))
print('same names in the same order:', names == fields)
print('every line is Field: value:', all(': ' in ln for ln in block))
sys.exit(0 if names == fields else 1)"
bash $L "$O" $PY metrix/e1-pilot/reports/round3/outside_metrix_check.py
bash $L "$O" $E $PY -m pytest -q -p no:cacheprovider metrix/e1-pilot/tests/test_test_data.py::test_interpretations_ruled_by_review_gate metrix/e1-pilot/tests/test_environment.py
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
