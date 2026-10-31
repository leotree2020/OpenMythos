#!/usr/bin/env bash
# Launch only the already-reviewed MES-1 train phase. No model/source changes.
set -euo pipefail
REPO=/workspaces/OpenMythos
PIN=7bcb08f480d0bda2dba5b1351442190001492782
REVIEW_REF=80c35f7321039f8351a13f56375413408f14407d
REVIEW_PATH=research/mini_mythos/multi_exit_study/evidence/MES1_CLAUDE_REVIEW_20261031.md
export MES1_OUTPUT_DIR=/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1
cd "$REPO"
git cat-file -e "$REVIEW_REF^{commit}" 2>/dev/null || git fetch origin mini-mythos-mes1-budget-holdout-cpu-20261031

# Locate an existing worktree at the reviewed commit; tolerate the pasted path typo.
WT=$(python3 - "$REPO" "$PIN" <<'PY'
import subprocess, sys
from pathlib import Path
repo, pin = sys.argv[1:]
text = subprocess.check_output(['git','-C',repo,'worktree','list','--porcelain'], text=True)
for record in text.strip().split('\n\n'):
    fields = dict(line.split(' ',1) for line in record.splitlines() if ' ' in line)
    path = Path(fields.get('worktree',''))
    if fields.get('HEAD') == pin and path.is_dir() and (path/'research/mini_mythos/multi_exit_study/run_codespaces_cpu.sh').is_file():
        print(path); break
else:
    raise SystemExit('BLOCKED：未找到已审核提交的现有 worktree；未创建、删除或覆盖。')
PY
)
printf '使用已有工作目录：%s\n' "$WT"
[[ "$(git -C "$WT" rev-parse HEAD)" == "$PIN" ]] || { echo 'BLOCKED：执行版本不符'; exit 2; }

# This reads existing preparation bytes only. It does not execute prepare or open H1.
python3 - "$MES1_OUTPUT_DIR" "$PIN" <<'PY'
import hashlib, json, sys
from pathlib import Path
out, pin = Path(sys.argv[1]), sys.argv[2]
def need(ok, message):
    if not ok: raise SystemExit('BLOCKED：' + message)
raw = (out/'prepared.json').read_bytes()
need(hashlib.sha256(raw).hexdigest() == 'd6ec93cb908d3994b6098b913c9b045d06b055a8fbade92bf62cdd0c5ae20678', 'prepared.json 与此前终端摘要不符；保留现场')
r = json.loads(raw)
need(r.get('experiment') == 'MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1' and r.get('phase') == 'prepare' and r.get('status') == 'PASS' and type(r.get('exit_code')) is int and r['exit_code'] == 0, 'prepare 状态或实验身份不符')
need(r.get('code_head') == pin, '准备结果的代码版本不符')
need(set(r.get('starts',{})) == {'101','202','303','404','505'}, '准备结果种子不完整')
expected = {
'H1': '92cf3818dbeb838e62c3937f836ecd3f4c94190ca7b6a9719e0b1a1e0156a6ce',
'HC': '18ec9725035bb257b0bf62a3ab7f38961a69c42878f522ad41f1daa01d85fab4',
'H2': 'e6256d5ff6cd99e113ac07b7c373953f5e3b9c9bfd6a689d7e90904064350543',
}
for name, digest in expected.items():
    need(r['holdouts'][name]['allocation_sha256'] == digest, name + ' 与 Claude 的分配摘要不符')
counts = {'GPT': (5941,73433088), 'P2': (5433,80289792), 'P4': (3822,114130944), 'A': (3000,145428480)}
need(r['budget']['ceiling_flops'] == 436285440000 and set(r['budget']['arms']) == set(counts), '预算身份不符')
for name, (steps, flops) in counts.items():
    arm = r['budget']['arms'][name]
    need((arm['steps'],arm['step_flops'],arm['total_flops']) == (steps,flops,steps*flops), name + ' 预算不符')
existing = [name for name in ('training.json','train.started','jobs','pretraining_review.md','result.json','H1.json') if (out/name).exists()]
need(not existing, '已有训练或评估证据 ' + ', '.join(existing) + '；不重复启动、不自动恢复')
print('已有 prepare 文件、五种子、预算与 Claude 分配摘要：匹配。未重跑 prepare。')
PY

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT
git show "$REVIEW_REF:$REVIEW_PATH" > "$TMP"
REVIEW="$MES1_OUTPUT_DIR/claude_review_supplied_20261031.md"
if [[ -e "$REVIEW" ]]; then
  cmp -s "$TMP" "$REVIEW" || { echo 'BLOCKED：已有审核文件内容不同，不覆盖'; exit 2; }
else
  (set -o noclobber; cat "$TMP" > "$REVIEW")
fi
cd "$WT"
# Executing this train invocation acknowledges the actual owner-supplied review.
bash research/mini_mythos/multi_exit_study/run_codespaces_cpu.sh train \
  --review-report "$REVIEW" \
  --reviewer "Claude Code (owner-supplied review, 2026-10-31)" \
  --review-approved
