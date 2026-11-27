#!/usr/bin/env bash
# Stage C, C5 documentation commit (tasks/IMPL_C5_RULING.md items 2-3: RUNBOOK_A100.md per DEFERRED_MINORS 1.38 CL2-CL6,
# 1.42 CP1-CP5 and the section-4 general rule; DEFERRED_MINORS.md; IMPL_C_REPORT.md): checks of the staged tree, recorded
# unedited (stdout+stderr merged) by reports/round5/logrun.sh. The blobs of every staged path and the sha256 of the staged
# diff are recorded first and last; src/, tests/ and run_pilot.py must equal HEAD (ruling item 4).
#   bash metrix/e1-pilot/reports/impl_c/c5_docs_checks.sh OUTFILE PYTHON
# Run from the repository root. PYTHON: an interpreter with requirements.lock installed (the s3_2 venv of c5_01).
set -u
O="$1"; PY="$2"
L=metrix/e1-pilot/reports/round5/logrun.sh
C="metrix/e1-pilot/src metrix/e1-pilot/tests metrix/e1-pilot/run_pilot.py"
RB=metrix/e1-pilot/RUNBOOK_A100.md
RU=metrix/e1-pilot/tasks/IMPL_C5_RULING.md
{ echo "# Stage C, C5 documentation commit (staged; parent $(git rev-parse HEAD)): checks on the staged tree. Executor, host $(hostname) (Anthropic cloud container, CPU only, no GPU). $(date -u)"
  echo "# stdout+stderr merged, unedited. Commands recorded by reports/round5/logrun.sh."; } > "$O"
STATE="git rev-parse HEAD; git write-tree; git diff --quiet -- $C && echo WORKTREE_EQUALS_INDEX_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --quiet HEAD -- $C && echo INDEX_EQUALS_HEAD_FOR_SRC_TESTS_RUN_PILOT; git diff --cached --stat HEAD; sha256sum metrix/e1-pilot/reports/impl_c/c5_docs_checks.sh; git diff --cached --name-only HEAD | xargs git ls-files -s --; git diff --cached HEAD | sha256sum"
bash $L "$O" git ls-remote origin refs/heads/metrix-e1-pilot-protocol-v1
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
bash $L "$O" bash -c "echo 'staged paths outside metrix/e1-pilot/ (expected none):'; git diff --cached --name-only HEAD | grep -v '^metrix/e1-pilot/'; echo \"grep exit \$?\""
# (trial 1, c5_02_docs_checks_trial1_script_error.txt, did this with grep -o '...[^」]*...' under the POSIX locale: the
# multibyte bracket expression matched nothing, R was empty and grep -c counted every line; replaced by Python, which
# reads both files as UTF-8 and fails when the text is empty or not found exactly once)
bash $L "$O" python3 -c "
import re, sys
ru = open('$RU', encoding='utf-8').read(); rb = open('$RB', encoding='utf-8').read()
m = re.search('总则：(「[^」]*」)', ru)
r = m.group(1) if m else ''
print('general rule of ruling item 2 (from the ruling file):', r)
print('characters:', len(r), '| occurrences in the RUNBOOK:', rb.count(r) if r else 0)
sys.exit(0 if r and rb.count(r) == 1 else 1)"
bash $L "$O" bash -c "echo 'old placeholders, private method, home venv, pending wording in the RUNBOOK (expected none):'; grep -n '<名称>\|_state()\|~/metrix-venv\|待 Review Gate\|待决\|report_only\|b17_plus' $RB; echo \"grep exit \$?\""
bash $L "$O" bash -c "echo 'long commands labelled in section 3 (name: count of lines \"长命令 <name>\"):'; for n in s3_2a s3_2 s3_4_data s3_4_config s3_4_model formal test_generate test_evaluate; do echo \"\$n: \$(grep -cE \"长命令 \$n(\\\$|[^a-z0-9_])\" $RB)\"; done; echo 'listed in section 1:'; grep -o '共 8 条,依次为[^;]*' $RB"
bash $L "$O" bash -c "echo 'tee without -a on env.txt / fetch.txt (expected none):'; grep -n 'tee \"\$E\"\|tee \"\$WORK/command_output/fetch.txt\"' $RB; echo \"grep exit \$?\""
bash $L "$O" bash -c "echo 'CP5 wording (section 1 Python row, 3.0 note, 3.2a note):'; grep -n '不能建 venv' $RB | cut -c1-160"
bash $L "$O" env PYTHONPATH=metrix/e1-pilot/src $PY -c "
import re, sys
from metrix_e1 import frozen as FZ, record as R
fields = R.template_fields(FZ.load().protocol_text)
rb = open('$RB', encoding='utf-8').read()
block = re.search(r'\n\`\`\`\n(Experiment ID: METRIX-E1-PILOT-l6-compare-.*?)\n\`\`\`\n', rb, flags=re.S).group(1).split('\n')
names = [ln.split(': ', 1)[0] for ln in block]
print('protocol section 10 fields', len(fields), '| RUNBOOK 3.7 item 5 template lines', len(block))
print('same names in the same order:', names == fields)
sys.exit(0 if names == fields else 1)"
bash $L "$O" $PY metrix/e1-pilot/reports/round3/outside_metrix_check.py
bash $L "$O" sha256sum $RU
bash $L "$O" git status --short --untracked-files=all
bash $L "$O" bash -c "$STATE"
