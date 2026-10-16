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

[R1 Gate D 完整执行计划](docs/R1_GATE_D_PLAN.md)规定最后一次本配置小模型 200→600 步续训、匹配暴露量的 n-gram 检查，以及 [60/200/600 比较器](scripts/r1_gate_d_compare.py) 的配置/Checkpoint/数据/恢复链一致性守卫（附 [离线测试](tests/test_r1_gate_d_compare.py)）。**Gate D 已于 2026-10-16 在 Codespaces 完成，结果见 [Gate D 实测](docs/R1_GATE_D_RESULT.md)。**

## R1 Gate D 完成与 R1 Gate E 扩展验证

600-step Checkpoint 已实测：`Resumed from step 200`，最终验证 **NLL 2.417668 / PPL 11.219663**；同模型 SGD 窗口精确重放 **153600 目标位置**（RNG 状态匹配），**matched Bigram PPL 13.021447**，全语料前缀 Bigram PPL 12.597172。训练后 argmax 空格占比从 100% 降至 **32.52%**，反转历史上下文 mean probability TV 达到 **0.214781**；但 Greedy 生成仍陷入 `the the the`，并非具备流畅自然语言能力。60/200/600 模型数据/超参数/恢复链校验全部通过。详见 [R1 Gate D Result](docs/R1_GATE_D_RESULT.md)。

依据预设停止规则，**不再无止境训练这只 dim48 CPU Tiny 模型**。[R1 Gate E](docs/R1_GATE_E_PLAN.md) 将在同一 600-step Checkpoint 上扩大固定 Heldout 检查到 128 个窗口（8192 个字节目标），同时做逐窗口的模型和 matched Bigram NLL 对比及探索性配对 bootstrap，避免只凭先前 1024 个目标作较强结论。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r1_gate_e_validation.py --repo . \
      --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
      --eval-windows 128 \
      --out research/mini_mythos/results/r1/gate_e_validation_128.json

新脚本只读权重、核对数据和 RNG 后写入新的 JSON，不覆盖 16-window 既有报告。**Gate E 已于 2026-10-16 在 Codespaces 完成，结果见 [Gate E 实测](docs/R1_GATE_E_RESULT.md)。**

## R1 Gate E 已验证：97/97；下一步冻结独立测试（Gate F）

**97/97 tests PASS**。Step-600 GQA 模型在 128 个确定性 WikiText-2 validation 窗口（8192 个字节目标）上取得 **NLL 2.455182 / PPL 11.648557**，优于同训练样本暴露量的 Add-1 Bigram **PPL 13.417210** 和全训练前缀 Bigram **PPL 12.977333**。模型赢下 121/128 个窗口，paired NLL 优势 +0.141356 nats/byte；探索性 window-bootstrap 95% 区间 [0.125281, 0.157897]。这是**已反复使用的 validation**，不能替代一次未参与决策的 test。记录见 [Gate E Report](docs/R1_GATE_E_RESULT.md)。

[Gate F 预注册协议](docs/R1_GATE_F_PLAN.md)：不再训练、不改 Checkpoint；下载官方 WikiText-2 **test** split（下载前解析不可变修订 SHA），固定前 1200 个合格 text 项，只取最多 250000 bytes 并评估 256 个各 64 字节的目标窗口，与相同训练曝光量 Add-1 统计基线对照。以下操作**尚未在 Codespaces 运行**：

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r1_gate_f_prepare_test.py \
      --repo . --revision main --test-docs 1200 \
      --out-dir research/mini_mythos/results/r1/gate_f_test
    python research/mini_mythos/scripts/r1_gate_f_test.py \
      --repo . --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
      --test-dir research/mini_mythos/results/r1/gate_f_test \
      --test-windows 256 --max-test-bytes 250000 \
      --out research/mini_mythos/results/r1/gate_f_result.json

Gate F 工具会拒绝覆盖 test 结果或修改冻结的步数、Tokenizer 和评估窗口。这是本代 tiny CPU 模型的最终独立测试；随后回到上游 OpenMythos 的真实 Tokenizer 与 GPU 训练链路审计。

## R1 Gate F 独立测试已通过 — R2 上游优先正式开启（2026-10-16）

官方 WikiText-2 Test Split（独立于此前反复使用的 validation）已经一经冻结就执行：**106/106 tests PASS**。测试源仓库版本 `b08601e04326c79dfdd32d625aee71d232d685c3`、1200 条合格记录、256 x 64 = 16384 评分目标。600-step GQA dim48 的 **Test PPL=10.852968**，同训练样本暴露量 Add-1 Bigram **12.790071**，全前缀 Add-1 Bigram **12.404059**；模型在 253/256 个窗口胜出，paired NLL = +0.164231 nats/byte。结果文件仍位于 Codespaces 忽略目录。详见 [Gate F 实测](docs/R1_GATE_F_RESULT.md)。

**R1 最小字节级训练/测试门槛完成，CPU Tiny 训练关闭。** 不应据此声称获得 Claude Mythos 的真实架构、权重或对话/推理能力。下一条主线是 [R2 OpenMythos 上游/Tokenizer/GPU 训练准备审计](docs/R2_UPSTREAM_READINESS.md)。优先分析社区 [PR #27](https://github.com/kyegomez/OpenMythos/pull/27) 约 117.8M 参数 MLA+MoE 训练先例，关联 [PR #26](https://github.com/kyegomez/OpenMythos/pull/26) BF16 源码兼容性与 Tokenizer 一致性问题，不直接从头造新架构，也不贸然运行内置 3B 脚本。

Codespaces 下一步（**只读预检，不分配模型权重，不消耗 GPU 预训练预算**）：

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_preflight.py --repo . \
      --out research/mini_mythos/results/r2/preflight.json

报告包括 PyTorch/CUDA/GPU/VRAM/BF16、源码与依赖 SHA/版本、训练状态的数量级估算以及 P0/P1 审计清单。脚本已提交，**目前还没有 Codespaces 运行后的 R2 设备清单**。

## R2 Gate A 实测：现有 Codespaces CPU only，先复现上游 PR #27

2026-10-16 Codespaces：**110/110 tests PASS**，PyTorch `2.14.1+cu130` 但 **CUDA available=False，GPU=0**，仅余 **13.06 GiB** 本地空间。预训练不能在当前容器直接进行。正式训练仍有数据 cursor、Tokenizer 修订、Checkpoint 安全、Heldout Eval 和核心 KV Cache 的静态 GAP，以及 BF16/ACT/MoE 待确认事项。[R2 Gate A 原始日志记录](docs/R2_GATE_A_ENVIRONMENT.md)。

已从 GitHub 读取上游 PR #27 **固定 Commit `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`** 的真实 `experiments/config.py`、`data.py`、`train.py`、`evaluate.py`、`run_all.sh`、`README.md`。其中发现 tokenizer eval override、无法严格恢复训练游标、mutable dataset、伪称单循环为 plain Transformer 及**把 complex RoPE buffers 连同模型强制转 bf16 后虚部被丢弃**的风险。纯 PyTorch CPU buffer cast 已验证一般行为；还需用户 Codespaces 的真实 Tiny OpenMythos 微型模型诊断，详见 [R2 PR #27 固定源码审计](docs/R2_PR27_SOURCE_REVIEW.md)。

### Codespaces 下步：只读取 PR 源码并执行 CPU 预检

    git pull --ff-only origin mini-mythos-research
    git fetch https://github.com/kyegomez/OpenMythos.git \
      refs/pull/27/head:refs/remotes/pr27-audit
    git rev-parse refs/remotes/pr27-audit
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_static_audit.py --repo .
    python research/mini_mythos/scripts/r2_rope_dtype_probe.py --repo .

`git rev-parse` 应等于上面的冻结 SHA；如果 PR HEAD 变动，需要改为抓取固定提交，不要悄悄改研究对象。两项新工具只读取源码并实例化 dim48 CPU 微型模型作复数相位测试，结果位于 Git 忽略目录 `results/r2/`。**这两项还未在 Codespaces 跑过，不能把新脚本提交当作实测 PASS。**

R2 仍采取“**先模仿、再验证、再超越**”：不直接 merge PR，不修改上游 `open_mythos/main.py`，不启动 PR 的 `run_all.sh` 或 3B 脚本，也不声称获得了 Anthropic 私有模型细节。

## R2 Gate B 验收：114/114 测试，PR27 BF16 RoPE 相位损坏已动态确认

Codespaces（2026-10-16）实际输出：**114/114 tests PASS**。固定 PR27 Commit `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4` 上，全部 14 项源码风险规则 FOUND；这些 `FOUND` 只是源码证据。**另有真实动态错误证据**：PyTorch 2.14.1+cu130 CPU tiny 上，`freqs_cis` 和 `freqs_cis_mla` 的 Complex64 RoPE 频率表均在 `.to(dtype=torch.bfloat16)` 后变成没有虚部的实数 BF16，`phase_information_lost=True`；源文件未修改、GPU 训练未执行。[Gate B 结果与下一步](docs/R2_GATE_B_RESULT.md)。

为降低修改范围，我们先提交了 [BF16 autocast 研究候选](scripts/r2_bf16_autocast_candidate.py) 与 [GQA/MLA CPU 回归测试](tests/test_r2_bf16_autocast_candidate.py)：**保持 FP32 主权重、Complex64 RoPE buffer，不直接 BF16 cast 整个模型；临时改全序列 causal mask 为 BF16，使用 BF16 autocast 进行前向/反向、检查梯度**。这是有限的研究 smoke，不包含 PR27 118M GPU 训练，不直接修改 `open_mythos/main.py`。

Codespaces 下一步（仅 CPU）：

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_bf16_autocast_candidate.py \
      --repo . --device cpu --attentions gqa mla

产生的本地证据：`research/mini_mythos/results/r2/bf16_autocast_candidate.json`。**Gate C 已于 2026-10-16 实际执行：120/120 tests PASS，GQA/MLA 两种注意力的 BF16 前后向、非零有限梯度和 RoPE 相位保持均 PASS。详见 [Gate C 实测](docs/R2_GATE_C_RESULT.md)。** 上游完整的 Tokenizer pin、可恢复 Streaming 数据游标、安全 Checkpoint、MoE expert load 和真实 GPU BF16 smoke 仍需后续 Gate 完成。

## R2 Gate C 完成：120/120 PASS；Gate D 固定 Tokenizer

用户 Codespaces 运行 Gate C：**120/120 tests PASS（4.398 秒）**，GQA BF16 Loss=4.521300、grad_norm=1.924440、RoPE 相位保留、logits 对 FP32 max abs delta=0.00234181；MLA Loss=4.605480、grad_norm=1.942811、相位保留、delta=0.00261885。来源代码未修改，无实际 GPU 训练。详见 [R2 Gate C 实测报告](docs/R2_GATE_C_RESULT.md)。

下步 [R2 Gate D Tokenizer 身份检查](docs/R2_GATE_D_TOKENIZER_PLAN.md)：不训练模型，按 HF 不可变 SHA 固定 PR #27 的 GPT2 tokenizer，把所有 Token→ID、fast backend config、special ID 和六个固定文本编码 probe 的 SHA/明细写入只读 Contract；复验同一版本，拒绝替换 Tokenizer 与 embeddings 大小不符。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_tokenizer_contract.py freeze \
      --repo . --revision main
    python research/mini_mythos/scripts/r2_pr27_tokenizer_contract.py verify \
      --repo . --offline

预期新报告：`research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json`。Gate D 已实测：130/130 tests PASS，HF GPT2 Commit 不可变固定，并通过离线二次校验；PR27 原始 train/evaluate 仍未接入。详见 [Gate D 实测](docs/R2_GATE_D_RESULT.md)。后续会单独接入严格校验，再研究 FineWeb-Edu 数据位置与 RNG 恢复。

## R2 Gate D 完成：130/130 PASS；Gate E 绑定 Tokenizer 的研究层 Checkpoint

2026-10-16 真实 Codespaces：130/130 tests PASS。PR27 `gpt2` Tokenizer 固定 HF Commit `607a30d783dfa663caf39e06633721c8d4cfcd7e`，embedding rows **50257**，完整 Token→ID SHA256 `56547338e1f0301492f97c9ec86f9ff477d96513336d9497331e1f58f4afd911`，backend SHA256 `11e818f948f43497f364722def50c13f419158554961ee4bb095fbd3350895c3`；整份 Contract SHA256 `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`，离线再加载完全 MATCH。[Gate D 实测报告](docs/R2_GATE_D_RESULT.md)。

下一实验 [Gate E：绑定 Tokenizer 的研究 Checkpoint/评估入口](docs/R2_GATE_E_CHECKPOINT_PLAN.md)：使用缓存中的真实 GPT2 Tokenizer，执行 CPU 4维 Embedding/Head 合成一轮 AdamW，在保存的权重文件上附加独立的 Tokenizer metadata + SHA256 JSON manifest。resume/eval 读取权重**之前**先比对冻结的 Token ID/Backend/特殊 Token、model vocab 与权重内容 SHA；随后仅使用 `torch.load(weights_only=True)` 并检查模型张量实际行数。严格拒绝错误 revision、缺失元数据或损坏 checkpoint。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_guarded_checkpoint.py smoke --repo .
    python research/mini_mythos/scripts/r2_pr27_guarded_checkpoint.py verify --repo .

生成 `research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.pt` 和 `.manifest.json`，不覆盖之前的结果。**Gate E 于 2026-10-16 实测 140/140 tests PASS；`smoke` 和独立 `verify` 均通过安全加载和完整性校验。真实结果归档见 [Gate E Result](docs/R2_GATE_E_RESULT.md)。仍仅隔离研究层 Demo，未修改 PR27 原始 trainer/eval，也没有 118M GPU 训练。**

## R2 Gate E 完成：140/140 PASS；Gate F 恢复训练数据游标

用户 Codespaces 实际执行：**140/140 tests PASS（4.036 秒）**；真实冻结 GPT-2 Tokenizer 下，CPU 4 维 Embedding/Head 进行一次合成 AdamW 更新，Loss **10.897187**；`smoke` 内置读取与独立 `verify` 均确认 Token-ID/backend 身份 MATCH、模型 Embedding 行数 50257、Checkpoint metadata 与文件 SHA256 PASS，并以 `weights_only=True` 安全加载原始 step1。未训练真实 OpenMythos，也没有 PR27 正式训练入口补丁。详见 [R2 Gate E 实测](docs/R2_GATE_E_RESULT.md)。

[R2 Gate F：可保存/恢复数据流与 RNG 的单 Worker CPU 验证](docs/R2_GATE_F_STREAM_RESUME_PLAN.md) 现已提交。使用原冻结 GPT2 Tokenizer、合成的 PR27 形状文档和相同 EOS/packed-window 规则，保存来源和 buffer Cursor、Python/Torch RNG、真实 Tiny AdamW 模型/优化器状态；要求**连续 12 步**与**5 步 checkpoint + 恢复 7 步**的 Token、Loop 选择、随机性、Loss 和模型/优化器状态**逐位相同**。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_stream_resume.py --repo .

预计新文件在 Git 忽略的 `results/r2`：`pr27_gate_f_stream_cpu.pt`、`.manifest.json`、`pr27_gate_f_stream_comparison.json`。**Gate F 新代码尚未在 Codespaces 验证。** 这是受控**单 Worker、本地合成数据**流程，不等同于当前 PR27 `num_workers=2` 的 FineWeb-Edu Streaming Loader 可恢复；正式数据分片/预取与 GPU 训练依旧 BLOCKED。
