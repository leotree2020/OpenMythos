# Mini-Mythos Research Overlay v0.4 — Reproduce before optimizing

这是可以**直接叠加到你自己的 OpenMythos Fork 根目录**的增量工程，不覆盖任何上游核心模型源码。

## 文件结构

- `research/mini_mythos/scripts/smoke.py`：调用真实上游模型，CPU GQA/MLA 检查前向/反向、因果性、KV Cache 和基本 ACT 质量。
- `research/mini_mythos/scripts/act_diagnostics.py`：从真实模型的 ACT hook 读取概率，计算循环结束时未分配权重，并与候选强制余量规则作**数学对照**；**不会修改权重或 logits**。
- `research/mini_mythos/scripts/act_math.py`：独立 ACT 权重核算工具（非上游实现），用于离线测试。
- `research/mini_mythos/scripts/pilot_train.py`：极小规模合成数据训练通路测试，不是 OpenMythos 成果复现，也不是正式 Benchmark。
- `research/mini_mythos/tests/`：离线单元测试。
- `research/mini_mythos/scripts/provenance.py`：对 Fork 的本地 Git origin、commit 和关键源文件计算 SHA256；不验证远程父子关系。
- `.github/workflows/mini-mythos-smoke.yml`：Actions CPU CI 工作流。

## 使用方式（浏览器 + GitHub Codespaces）

1. 进入上游仓库 <https://github.com/kyegomez/OpenMythos>，Fork 到你自己的账号。如果已存在 Fork，无需重复 Fork。
2. 在 leotree2020/OpenMythos Fork 内新建 `mini-mythos-research` 分支；不要直接修改 `main`。
3. 从 Fork 新建一个 Codespace（或使用其他获批的云端开发环境）。
4. **把本 ZIP 上传进 Codespace 的仓库根目录**，在终端执行：

```bash
unzip -o mini_mythos_leotree2020_overlay_v04.zip -d .
python -m pip install 'torch>=2.1,<3' 'transformers>=4.40,<6'
python -m unittest discover -s research/mini_mythos/tests -v
python research/mini_mythos/scripts/provenance.py --repo . --strict
python research/mini_mythos/scripts/static_audit.py --repo .
python research/mini_mythos/scripts/smoke.py --repo . --attention gqa
python research/mini_mythos/scripts/act_diagnostics.py --repo . --attention gqa
```

5. 检查 `research/mini_mythos/results/` 的 JSON；如果通过，再提交：

```bash
git status --short
git add research/mini_mythos .github/workflows/mini-mythos-smoke.yml
git commit -m 'test: add reproducible Mini-Mythos research diagnostics'
git push -u origin mini-mythos-research
```

6. 打开 Fork 的 **Actions** → **Mini-Mythos upstream validation**。推送到 `mini-mythos-research` 会自动触发对应分支的工作流；下载对应 GQA/MLA artifact 查看结果。注意：GitHub 的 `workflow_dispatch` 通常要求工作流在默认分支存在，首次使用请依赖 push 触发。

**如 GitHub Actions 受限**，可在 Codespaces 执行上面的相同命令。请避免在未经授权的公司 PC 或内部主机上安装软件或导入生产日志。

## 运行等级与证据界限

- **Level 0 (本地测试)**：只验证实验辅助代码（`act_math.py` 和合成 token 数据）；与真实上游模型是否可运行无关。
- **Level 1 (上游 smoke)**：在真实 Fork 的 OpenMythos 代码上验证动态行为、记录 SHA 与版本；并非有用语言模型的证据。
- **Level 2 (预训练复现)**：专门部署 GPU，复现 PR #27 的数据、参数、checkpoint 与 PPL sweep；当前工作流不会训练 117.8M 模型。
- **Level 3 (架构超越)**：从 Level 2 的相同 token、训练 FLOPs、种子和评测环境开始，单变量消融 ACT/LoRA/loop index。

### 重要边界

上游 `pyproject.toml` 的某一版本固定 `torch==2.11.0` 并依赖 `transformers`；本 CPU smoke 工作流只执行模型导入和小规模测试，不需要整个 GPU 训练栈，但必须包含 `transformers`，否则导入 `open_mythos/__init__.py` 可能失败。

`act_diagnostics.py` 的**候选**“强制补齐最后 ACT 余量”只分析概率质量，不修改上游源码，也不声明改善准确率。在真实预训练权重和 held-out 测试完成前，不应该直接合入生产或主分支。

参考上游：<https://github.com/kyegomez/OpenMythos> / 社区实验：<https://github.com/kyegomez/OpenMythos/pull/27>


## ACT-002 · Same-weight counterfactual (research extension)

See [ACT_002.md](docs/ACT_002.md). The experimental script evaluates the same
two parameter snapshots under both the original and final-remainder ACT rules,
then records the direct ACT policy contrast, parameter-history contrast, and
their interaction before each optimizer step. No upstream model source edits.

```bash
python research/mini_mythos/scripts/act_counterfactual.py \
  --repo . --device cpu --attentions gqa --depths 2 \
  --seed 22 --steps 30 \
  --out research/mini_mythos/results/act002_gqa_seed22.json

python research/mini_mythos/scripts/act_counterfactual_summary.py \
  research/mini_mythos/results/act002_gqa_seed22.json --first 15
```

The short-run GQA and MLA correctness checks are also included in the GitHub
Actions workflow. This is a micro-model, synthetic-data mechanism experiment,
**not** evidence of better language-model accuracy.

## ACT-001 / ACT-002 研究报告

已完成 ACT 质量截断诊断、5 随机种子的合成任务 A/B、GQA/MLA 同权重反事实实验及 MLA 阴性/阳性对照。完整数据与结论边界参见 [ACT-001 / ACT-002 研究报告](docs/ACT_001_002_RESEARCH_REPORT.md)。未在真实预训练模型上证明性能收益。


## ACT-003：原始 JSON 归档与复跑

先阅读 [ACT-003 归档与受控复跑说明](docs/ACT_003_ARCHIVE_REPLAY.md)。

在现有 Codespaces 的仓库根目录执行：

    python research/mini_mythos/scripts/evidence_archive.py pack --repo .
    python research/mini_mythos/scripts/evidence_archive.py verify \
      research/mini_mythos/archives/act001_act002_evidence.zip
    python research/mini_mythos/scripts/evidence_replay.py --repo . \
      --archive research/mini_mythos/archives/act001_act002_evidence.zip \
      --cases gqa22 mla22 mla44

该流程只打包已列入白名单的历史合成数据 JSON；归档 ZIP 及验证结果保存在 Git 忽略的 archives/ 目录，**不会自动推送到 GitHub**。默认要求 10 个历史必需结果齐全，且需要当前环境的源码及依赖版本与归档快照一致。

**Gate A 验证结果（2026-10-16）：** Codespaces 中 42/42 单元测试通过；14 份 JSON 证据归档校验 complete；GQA22 / MLA22 / MLA44 受控复跑均 PASS。详见 [ACT-003 Gate A 验证记录](docs/ACT_003_GATE_A_RESULT.md)。归档 ZIP 仍保存在本地 Codespaces，未上传本仓库。
