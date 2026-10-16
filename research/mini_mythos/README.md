# Mini-Mythos Research Overlay v0.4 — Reproduce before optimizing

> **项目主目标（2026-10-16 纠偏）：** 以开源 OpenMythos 为基础，根据公开证据研究、训练并评估 Claude Mythos 的独立功能性复刻。ACT-001–004 仅为机制实验，非项目最终目标。研究路线及证据边界见 [Mythos Reconstruction Roadmap](docs/MYTHOS_RECONSTRUCTION_ROADMAP.md)。

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


## ACT-003 Gate B：扩大 Heldout 样本和多种子对照

[act_gate_b.py](scripts/act_gate_b.py) 复用 ACT-001 的原版/Forced Final 训练逻辑；唯一的实验参数扩展是 Heldout 批次数量。默认五个训练随机种子（11/22/33/44/55）、GQA/MLA、深度 1/2、30 个训练步骤，以及每组 **100 个固定合成 Heldout 批次**。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/act_gate_b.py --repo . --device cpu \
      --seeds 11 22 33 44 55 --attentions gqa mla --depths 1 2 \
      --steps 30 --heldout-batches 100

结果存放于 Git 忽略的 research/mini_mythos/results/act003_gate_b/，包括每个种子的原始 JSON 和 summary.json。正的 ΔLoss = Forced Final Loss − Original Loss 表示原版更低；负值则相反。Bootstrap 区间以**训练种子**为重采样单位，不把重复使用的 Heldout 批次错误地当作独立训练样本。结果仍然是小型合成实验，不代表真实预训练模型的性能结论。

为便于快速检查运行链路，可先执行 --seeds 22 --attentions gqa --depths 2 --steps 3 --heldout-batches 5 --out-dir research/mini_mythos/results/act003_gate_b_smoke。完整运行请使用上面的默认设计。

## ACT-004 · Compute-aware depth sweep

[ACT-004 实验设计与运行说明](docs/ACT_004.md) / [脚本](scripts/act_compute_sweep.py)。在 Codespaces 中运行：

    python research/mini_mythos/scripts/act_compute_sweep.py --repo . \
      --seeds 11 22 33 --attentions gqa mla --depths 1 2 4 \
      --steps 30 --heldout-batches 30

此阶段记录**整组 A/B 实验耗时**、循环调用次数和 Loss 差异，不把整组耗时解释成某个策略的独立加速比，也不声称 FLOPs 已经匹配。

## R0 · 复刻准备度审计（第一轮）

[源码审计报告](docs/R0_ARCHITECTURE_TRAINING_AUDIT.md) | [自动静态审计](scripts/r0_audit.py) | [CPU 动态探针](scripts/r0_probe.py)

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r0_audit.py --repo .
python research/mini_mythos/scripts/r0_probe.py --repo .
```

重点检查实际训练评估链路、Tokenizer 版本固定、Checkpoint/数据恢复、MoE bias 更新，以及 KV Cache 的多 Token 分块一致性。探针只测试微型 CPU 模型，尚未在此回合运行，不能据此宣称 R0 完整验收或具备真实语言能力。

## R0 Gate A · KV Cache 故障复现与隔离修复验证

2026-10-16 Codespaces 运行：60/60 测试通过；GQA/MLA 微模型 Checkpoint 恢复均 PASS；多 Token（6 前缀 + 2 新 chunk）KV Cache 路径均报告 8 vs 2 尺寸不匹配。证据与源码分析见 [R0 Gate A 结果](docs/R0_GATE_A_RESULT.md)。

已在研究层新增 [r0_cache_mask.py](scripts/r0_cache_mask.py) 临时因果掩码覆盖及 [r0_cache_compare.py](scripts/r0_cache_compare.py) 的原版/修复版数值对照。**不是上游核心修复或生产环境补丁，尚待 Codespaces 执行验证。**

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r0_cache_compare.py --repo . --attentions gqa mla --strict
```

实验结果写入 `research/mini_mythos/results/r0/cache_mask_comparison.json`。

## R0 Gate A 验收更新（2026-10-16）

最新 Codespaces 实测：**67/67 单元测试通过**；`r0_cache_compare.py --strict` 对 GQA/MLA 都得到 **upstream=FAIL、research_mask=PASS**，最大绝对偏差均为 `2.9802322387695312e-08`。证据已归档至 [R0 Gate A](docs/R0_GATE_A_RESULT.md)。这是 CPU 微模型的缓存分块缺陷隔离修复，不是整个 R0 或 Mythos 复刻完成。

## R1：真正文本训练 Pilot（新主线）

[R1 执行计划和完整命令](docs/R1_REAL_TEXT_PILOT.md) | [公开文本数据准备](scripts/r1_prepare_wikitext.py) | [训练 / 验证 PPL / 安全 Checkpoint / 生成](scripts/r1_text_pilot.py)

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r1_prepare_wikitext.py --repo . --revision main
python research/mini_mythos/scripts/r1_text_pilot.py --repo . \
  --train-text research/mini_mythos/results/r1/data/train.txt \
  --validation-text research/mini_mythos/results/r1/data/validation.txt \
  --attention gqa --depth 2 --seq-len 64 --batch-size 4 \
  --steps 60 --eval-windows 16 \
  --out-dir research/mini_mythos/results/r1/pilot_gqa
```

WikiText-2 的默认 `main` 版本可变；真实可复现性需固定 Hugging Face 数据仓库 revision SHA 和保留数据 SHA-256。此 Pilot 使用固定的 **257-token UTF-8 byte tokenizer**，属于微型训练链路验证，不应将其 PPL 和正式 subword 模型 PPL 直接比较。运行结果保持本地忽略，不会自动上传 GitHub。**代码已提交，用户 Codespaces 还未运行本次 R1 Pilot。**

## R1 Gate A 完成（2026-10-16）：第一次真实文本训练

Codespaces 实测 **73/73 tests PASS**。数据：WikiText-2 train 2000 篇（995396 bytes；SHA-256 4790992d8539e04893b3e066ff65f07750517d68484fd4cb28665c5e71b0fa8b）、validation 300 篇（120904 bytes；SHA-256 3508547d6576f65c2ba10f0e3ca7ac23f1cd1a6593db45b65395d7aa60e32c1b）。微模型仅使用两个文本文件的**选定前缀**（默认最多 train 250000 bytes、validation 50000 bytes）。GQA Depth 2、60 steps、16 validation windows 共 1024 计分 byte tokens，heldout NLL **5.51615 → 3.37635**，PPL **248.675 → 29.264**，本地 Checkpoint 和报告已保存。生成 24 个空格，不具备可信流畅语言证据。详见 [R1 Gate A 结果](docs/R1_GATE_A_RESULT.md)。

## R1 Gate B：检查是否只是学习高频字符

[诊断脚本](scripts/r1_language_diagnostics.py)（只读取 Checkpoint，不继续训练）比较模型、train-fitted Smoothed Unigram/Bigram 和均匀基线，检查非空格 Loss、空格预测率，以及三条提示词的 greedy/sample 输出。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r1_language_diagnostics.py --repo . \
      --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
      --eval-windows 16 --generated-bytes 64

结果：research/mini_mythos/results/r1/pilot_gqa/diagnostics.json。新的诊断脚本尚未在 Codespaces 实际执行，不应猜测 unigram/bigram 对照结果。

## R1 Gate B 结果（2026-10-16）

[R1 Gate B 报告](docs/R1_GATE_B_RESULT.md)：用户 Codespaces 结果复现了训练后的模型 PPL 29.264，但它比 train-fitted Unigram PPL 26.919 和 Bigram PPL 12.597 更差；1024 个 heldout 位置的 argmax 全部预测为空格（实际空格 19.4%），greedy 生成也全部是空格。80 项测试中 79 PASS、1 ERROR；Error 是测试字段名 `perplexity` 与真实 API `ppl` 不符，修复已提交，等待重新验证。

已新增同一 Checkpoint 的无训练历史顺序消融 `context_order_probe`，比较保持最后字节不变、仅反转前置上下文顺序时的 logits / NLL 差异，判断模型是否仅在字节频率层面拟合。不会更新现有 `latest.pt`。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r1_language_diagnostics.py --repo . \
      --pilot-dir research/mini_mythos/results/r1/pilot_gqa \
      --eval-windows 16 --generated-bytes 64

当前不应宣称已有有效自然语言模型或 Mythos 复刻的能力；下一步需要具备统计基线优势、训练步数/Tokenizer 的合理扩展与可复现实测。

## R1 Gate B 二次验证和 Gate C 控制性续训

2026-10-16 真实 Codespaces 实测：**82/82 tests PASS**；60-step GQA 重新载入后的 heldout PPL 29.26364。Unigram PPL 26.91942、Bigram PPL 12.59717，模型仍落后于这两个 train-fitted 统计基线；argmax 预测空格比例 100%，历史顺序反转的目标 NLL 变化约 3.58e-7，平均概率 TV 约 2.17e-5。详见 [Gate B 报告](docs/R1_GATE_B_RESULT.md)。

Gate C（**200-step 已执行并保存结果**）：保留 60-step 原始 checkpoint，在副本中仅增加训练步数到 200；记录 heldout、Bigram、空格塌缩与上下文敏感性。历史命令保留下方供审计。

    git pull --ff-only origin mini-mythos-research
    cp -a research/mini_mythos/results/r1/pilot_gqa research/mini_mythos/results/r1/pilot_gqa_step200
    python research/mini_mythos/scripts/r1_text_pilot.py --repo . \
      --train-text research/mini_mythos/results/r1/data/train.txt \
      --validation-text research/mini_mythos/results/r1/data/validation.txt \
      --attention gqa --depth 2 --seq-len 64 --batch-size 4 \
      --steps 200 --eval-windows 16 --resume \
      --out-dir research/mini_mythos/results/r1/pilot_gqa_step200
    python research/mini_mythos/scripts/r1_language_diagnostics.py \
      --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step200 \
      --eval-windows 16 --generated-bytes 64

## R1 Gate C：200-step 实测与精确样本暴露对照

2026-10-16 Codespaces 已将 GQA（dim48、depth2、byte tokenizer）的 60-step Checkpoint 完整续训到 **200 steps**。Heldout PPL 从 **29.26364 → 25.16696**；较 Unigram **26.91942** 更优，但仍差于 Bigram **12.59717**。目标空格占比 19.4%、argmax 预测空格占比依然 **100%**。历史顺序反转的概率 TV 从 2.17e-5 增至 0.002449，证明这类输入敏感性上升，尚不等于有有效语言能力。详见 [R1 Gate C 报告](docs/R1_GATE_C_RESULT.md)。

下一项是**训练样本暴露量匹配**的统计基线：此前 n-gram 统计了整段约 25 万字节的训练前缀，而模型在 200 steps 只看到 51,200 个监督位置（含重复）。新脚本使用保存的训练随机偏移发生器状态，精确重放模型实际看到的 `(previous byte, next byte)` 对，检查 RNG 状态完全一致后估计 n-gram。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r1_exposure_baselines.py --repo . \
      --pilot-dir research/mini_mythos/results/r1/pilot_gqa --eval-windows 16
    python research/mini_mythos/scripts/r1_exposure_baselines.py --repo . \
      --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step200 --eval-windows 16

2026-10-16 已经在 Codespaces 成功执行：86/86 tests PASS，60 和 200 步的 RNG 状态与重放严格一致，结果详见 Gate C 报告。

## R1 Gate C 同训练样本对照已完成；Gate D 受控续训准备

Codespaces 真实执行：**86/86 PASS**。两个 Checkpoint 的训练窗口随机数状态均严格重放一致。60-step 15360 次监督目标：模型 PPL **29.264**，matched Unigram **27.513**，matched Bigram **19.158**。200-step 51200 次监督目标：模型 PPL **25.167**，matched Unigram **26.951**，matched Bigram **14.812**。模型已超过 matched Unigram，但尚未超过 Bigram；Greedy 始终为空格。记录见 [R1 Gate C](docs/R1_GATE_C_RESULT.md)。

[R1 Gate D 完整执行计划](docs/R1_GATE_D_PLAN.md)规定最后一次本配置小模型 200→600 步续训、匹配暴露量的 n-gram 检查，以及 [60/200/600 比较器](scripts/r1_gate_d_compare.py) 的配置/Checkpoint/数据/恢复链一致性守卫（附 [离线测试](tests/test_r1_gate_d_compare.py)）。**新增脚本和 Gate D 计划已提交，但 600-step 尚未运行。**
