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

预计新文件在 Git 忽略的 `results/r2`：`pr27_gate_f_stream_cpu.pt`、`.manifest.json`、`pr27_gate_f_stream_comparison.json`。**Gate F 已于 2026-10-16 在 Codespaces 实测：148/148 tests PASS，连续 12 步与 5+7 步恢复的 Loss 差为 0.0，模型/AdamW/游标/Python+Torch RNG 全部逐位一致。详见 [Gate F Result](docs/R2_GATE_F_RESULT.md)。** 这是受控**单 Worker、本地合成数据**流程，不等同于当前 PR27 `num_workers=2` 的 FineWeb-Edu Streaming Loader 可恢复；正式数据分片/预取与 GPU 训练依旧 BLOCKED。

## R2 Gate F 结果归档：148/148 PASS；下一关模拟多 Worker 预取与已提交数据位置

GitHub Codespaces 实测：**148/148 单元测试 PASS（4.110 秒）**。本地固定 64 条 PR27 形状文档，55 Train/9 Heldout，真实固定 GPT2 Tokenizer；单 Worker PackedCursor 上连续训练 12 steps 与 5 steps 后保存并恢复 7 steps，**Loss 差 0.0，Trace、模型参数、AdamW Optimizer、Cursor 与 Python/Torch RNG 均逐位完全相同**。没有读取 FineWeb-Edu，没有 GPU，也没有修改上游原版 DataLoader。[Gate F 实测报告](docs/R2_GATE_F_RESULT.md)。

下一项 [R2 Gate G](docs/R2_GATE_G_PREFETCH_PLAN.md) 是**两个逻辑 Worker** 的 CPU 故障注入模拟：任务从固定 SHA 的全局索引派发，Worker 完成顺序故意乱序，程序在 optimizer step 5 后 checkpoint，而多个任务已完成预取却**还没有参与 optimizer.step()**。恢复时必须从已提交的 task 5 重新发放，不能根据最后派发的 task 9 跳过 5–8。再次强制 12 vs 5+7 steps 的 Tiny AdamW 全状态逐位一致。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_prefetch_commit.py --repo .

新结果写入 Git 忽略目录的 `pr27_gate_g_prefetch_cpu.pt`、`.manifest.json`、`pr27_gate_g_prefetch_comparison.json`，不会覆盖 Gate F。**Gate G 于 2026-10-16 在 Codespaces 实测 156/156 项测试 PASS；Task 5–8 已预取但未提交，错误派发游标 9 会跳过数据；从 committed 5 恢复后全部状态与训练轨迹逐位一致。详见 [Gate G Result](docs/R2_GATE_G_RESULT.md)。** 本实验**不会启动真实子进程、HF Streaming 或 CUDA**；真正 FineWeb-Edu 多 Worker/预取及生产 GPU 恢复仍属于 P0 阻塞项。

## R2 Gate G 通过：156/156；Gate H 真正 2 个 DataLoader 子进程

2026-10-16 用户 Codespaces：**156/156 tests PASS（4.183 秒）**。两个**逻辑** Worker 在 0 OS 子进程的模拟中，optimizer committed frontier 5、派发 frontier 9，预取任务 5–8 尚未进入优化器。若从派发 index 9 恢复就会跳过这些任务；按 committed index 5 恢复后 `Trace=True`、Loss 差 **0.0**，模型、AdamW、cursor、Python/Torch RNG 全部逐位一致。**没有真实 HF FineWeb-Edu、没有真实多进程 DataLoader、没有 GPU 训练**。[Gate G 实测结果](docs/R2_GATE_G_RESULT.md)。

下一项 [R2 Gate H](docs/R2_GATE_H_REAL_DATALOADER_PLAN.md) 已提交，使用真实 Linux PyTorch **`DataLoader(num_workers=2, prefetch_factor=2, in_order=True)`**，从数据集的子进程 `__getitem__` 共享读取计数，要求主训练器实际看到不同 OS Worker PID，并且在 checkpoint 时检测已经被子进程 fetch 但尚未应用优化器的 Task。中断后丢弃旧迭代器，使用**不可变本地合成 Task 索引**从 committed index 重新构造全新 DataLoader，比较 Tiny CPU AdamW 连续 12 steps 与恢复 5+7 steps 的逐位轨迹。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_real_dataloader_resume.py --repo .

Gate H 的单测包含**真正启动两个 DataLoader 子进程**的测试，耗时可能比先前纯 Python 测试更长。本地新证据：`research/mini_mythos/results/r2/pr27_gate_h_real_loader_cpu.pt`、`.manifest.json`、`pr27_gate_h_real_loader_comparison.json`。**Gate H 已在 Codespaces 真实双进程环境实测通过：162/162 tests PASS，任务 5–8 已预取未提交，恢复从任务 5 开始，Trace/AdamW/模型/RNG/Cursor 全部逐位相同；详见 [Gate H Result](docs/R2_GATE_H_RESULT.md)。** 研究对象仍然是 Map-style 已索引的本地合成任务，绝不是原版 FineWeb-Edu IterableDataset 或断电/进程杀死的生产恢复证明。

## R2 Gate H 完成：162/162 PASS；Gate I 真实 FineWeb-Edu 数据来源固定

2026-10-16 Codespaces：**162/162 tests PASS（14.719 秒）**。确实启动了 2 个 OS 子进程的 DataLoader：连续路径 PIDs `[82311,82312]`，中断路径 `[82348,82349]`，恢复路径 `[82398,82399]`。第 5 次 optimizer 提交后，Worker 已取 Task 5–8 但未用于更新；从已提交 index **5** 重建 DataLoader，连续 12 与 5+7 恢复的 Trace、模型/AdamW、Cursor、Python/Torch RNG 完全逐位一致，Loss 最大差 **0.0**。数据为可索引的本地合成文档，**未使用 FineWeb-Edu 或 GPU**。详见 [Gate H 实测](docs/R2_GATE_H_RESULT.md)。

下一项 [Gate I：真实 FineWeb-Edu Source Snapshot](docs/R2_GATE_I_FINEWEB_SNAPSHOT_PLAN.md) 只冻结**数据来源**，不启动训练：先解析官方 `HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train` 的不可变 HF Commit SHA，再流式选最早的 32 条合格文本（至多扫描 128 行、单文档最多 256KiB、选中的总文本最多 4MiB），生成本地 JSONL 以及来源/正文/SHA256/授权元数据 Manifest。`verify` 完全离线复验，不重读线上最新版本。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_fineweb_source_snapshot.py freeze --repo . --revision main
    python research/mini_mythos/scripts/r2_fineweb_source_snapshot.py verify --repo .

文件仅存 Git 忽略目录 `research/mini_mythos/results/r2/fineweb_gate_i_32`，内含 `snapshot.jsonl`（**原始真实文本不得 commit**）和 `manifest.json`。冻结文档限制不代表 Hugging Face 后端 Parquet 缓存/网络带宽的绝对上限。如果获取失败，请保留失败日志，不要改动原定 32 条/版本/数据源约束。

**Gate I 于 2026-10-16 已在 Codespaces 实测通过：171/171 tests PASS，32 条官方 FineWeb-Edu 文档冻结并完成离线 SHA-256 复验。详见 [Gate I 实测结果](docs/R2_GATE_I_RESULT.md)。** 即便通过，也仍然没有修复原版 PR27 FineWeb-Edu IterableDataset 多 Worker 的真实 Shard/Offset/队列恢复。

## R2 Gate I 通过：171/171；下一关真实文本双进程 CPU 重放

2026-10-16 Codespaces 实测：**171/171 tests PASS（15.046 秒）**。官方 `HuggingFaceFW/fineweb-edu` 的 `sample-10BT/train` 实际版本冻结为 `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，前 32 条源文档全部捕获，真实 UTF-8 文本 **111361 bytes**，本地 JSONL **119588 bytes**，SHA256 `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1`；离线重新验证 **VERIFIED**。没有训练模型，也没有修改原始 PR27 Streaming Loader。[R2 Gate I 实测](docs/R2_GATE_I_RESULT.md)。

已新增 [R2 Gate J](docs/R2_GATE_J_REALTEXT_REPLAY_PLAN.md) 脚本 [r2_fineweb_local_replay.py](scripts/r2_fineweb_local_replay.py) 及配套 [回归测试](tests/test_r2_fineweb_local_replay.py)。运行时先检查上述真实数据不可变 SHA/正文大小和现有 GPT2 Tokenizer Contract，再把原样 32 条文本转成本地固定的 PR27 形状 Token/ID 索引，使用 Gate H 的真实双进程 DataLoader，在**真实 FineWeb 文本**上运行 Tiny 4D Embedding/Head CPU AdamW 的 12 vs 5+7 步一致性实验。不会重新访问 HF 数据集或下载模型权重。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_fineweb_local_replay.py --repo .

Gate J 结果：`results/r2/pr27_gate_j_realtext_cpu.pt`、`pr27_gate_j_realtext_cpu.manifest.json`、`pr27_gate_j_realtext_replay.json`（均在 Git ignore 下）。**Gate J 于 2026-10-16 已在用户 Codespaces 实测：179/179 tests PASS（26.679 秒），冻结真实 FineWeb 文本上的 Tiny CPU AdamW 12 vs 5+7 Step 双进程恢复完整逐位一致，Loss 差 0.0。详见 [Gate J 实测](docs/R2_GATE_J_RESULT.md)。**

非常重要：Gate J 在真实文本上会执行**小型 CPU 训练管线 smoke**，但不计算正式模型质量分数，也没有构建独立 Test Split。Gate J 是先在全局内容上 Pack Tokens 再交给 Worker，PR27 原版是各 HF Worker 分片后分别 Token Pack；它们的数据顺序并不相同。**Gate J 不能证明 PR27 原版 IterableDataset/SIGKILL 恢复，也不能解锁 118M GPU 实训。**

## R2 Gate J 已验证：179/179；Gate K 测试原版的 Worker 分片→各 Worker 独立 Packing

2026-10-16 Codespaces：**179/179 tests PASS（26.679 秒）**。HF FineWeb-Edu 32 条真实冻结文档（内部仅用 28 条做 Tiny CPU 训练、4 条被排除，**不是正式独立 Test**），官方数据 SHA `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，GPT2 Contract `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`。连续/5步断点/恢复7步都观察到两个真实 OS Worker PID，任务 5–8 预取但未提交，恢复从 5 开始，Trace/参数/AdamW/Cursor/Python+Torch RNG 逐位一致，Loss 差 **0.0**。没有 GPU 或正式模型质量评估，也没有远程 HF Streaming 或 PR27 代码修改。[Gate J 实测报告](docs/R2_GATE_J_RESULT.md)。

下一项 [R2 Gate K](docs/R2_GATE_K_HF_WORKER_SHARD_PLAN.md) 专门验证上游 PR27 `experiments/data.py` 的不同步骤顺序：**先让每个 Worker 在 HF IterableDataset 上调用 `.shard(num_shards=2,index=worker_id)`，再在 Worker 内独立 Tokenize、追加 EOS 和打包**。将前一步真实文档做成仅本地的**两个 Arrow HF IterableDataset 分片**，让真正双 OS 子进程消费，并通过保存已提交的 Chunk SHA 在重新建立 Worker 后重放 5 条已提交 Chunk，继续 7 步；要求所有训练状态逐位一致，同时证实与 Gate J 全局预先 Pack 的窗口不同。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_hf_worker_shard_pack.py --repo .

本地新文件：`research/mini_mythos/results/r2/pr27_gate_k_worker_pack_cpu.pt`、`.manifest.json`、`pr27_gate_k_worker_pack_report.json`。**Gate K 首次运行（187 项测试 1 ERROR）发现 HF 双重分片，详见 [Failure 001](docs/R2_GATE_K_FAILURE_001.md)；随后修复版本已于 2026-10-16 重测 190/190 tests PASS，详见 [Gate K Result](docs/R2_GATE_K_RESULT.md)。** 该方案从开头 O(N) 重放已提交 Batch 的摘要，只适用于小规模本地快照，不具备生产大规模 IterableDataset 精确 shard seek 的性质，也没有真实 SIGKILL 或远程 Parquet 断点恢复。

## R2 Gate K 首次失败：HF 手动 + 自动双重 Sharding；修复待验证

2026-10-16 用户 Codespaces 上传的完整运行日志：**187 tests，1 ERROR（33.794 秒）**；唯一失败是 `GateKTests.test_real_worker_shard_then_pack_resume_matches_full_run`。HF 提示 `Too many dataloader workers: 2 (max is dataset.num_shards=1). Stopping 1 dataloader workers.` 单独运行 Gate K CLI 也返回 `RuntimeError: Missing one of two actual DataLoader worker PIDs`。**首次 Gate K 运行尚未通过；该历史失败记录已保留，后续修复于 2026-10-16 获得 190/190 PASS**；此前 Gate J 的 179/179 PASS 独立保留。[失败根因和修复记录](docs/R2_GATE_K_FAILURE_001.md)。

原因：Gate K 将本地数据预先变成 2 个 HF IterableDataset Arrow Shards，随后 Worker 中又调用显式 `.shard(2,worker_id)`，每个 Worker 减至 1 Shard；HF 自己的 `_iter_pytorch()` 又按 2 Worker 自动 Sharding，终止多余 Worker。本次研究修复不修改上游 PR27：让 **HF 原生 Worker 自动分片恰好一次**，随后分别 GPT2 Tokenize、EOS、Pack。新增主进程真实 HF 分片审计（所有训练文档 ID 散列恰好被两个 Worker 分区覆盖，不遗漏不交叉）与两个显式/自动双重分片负控，涵盖 4 Shards 时的源文档遗漏演示。**这也提示 PR27 原版手动 `.shard` 可能存在生产数据覆盖 P0，需要额外核查真实远程 Shards。**

重新执行修复后的 Gate K（不需要重冻 Gate I，不需要删除 Gate J 报告）：

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_hf_worker_shard_pack.py --repo .

验收重点：`Source docs covered once: True`、三个运行阶段两名真实 Worker PID、`Global-pack vs shard-then-pack differing chunks` 大于 0、Trace/Model/AdamW/Cursor/RNG True 和 Loss 差 0.0。**修复后 Gate K 已实际验证通过：190/190 tests PASS，真实双 Worker source document 28/28 恰好覆盖一次，模型/AdamW/Cursor/RNG 恢复逐位一致。详见 [Gate K Result](docs/R2_GATE_K_RESULT.md)。** 实验仍然是**本地 HF IterableDataset 2 个 Arrow Shards**，不是原始 remote FineWeb IterableDataset/O(1) shard seek，也没有 GPU。

## R2 Gate K 最终通过：190/190；Gate L 验证 PR27 多 Shard 静默数据漏读风险

2026-10-16 Gate K 修复重测：**190/190 tests PASS（39.748 秒）**，本地 HF IterableDataset 2 个 Arrow Shards 由两个真正 OS Worker 原生自动分片一次，开发来源 28/28 文档恰好被消费（14/14、无重叠或缺失）。连续/中断/恢复分别观测两个不同 PID；优化器提交位置 5，已预取尚未训练窗口数量 4，恢复从 5 开始，Tiny CPU 模型参数/AdamW/Cursor/Python+Torch RNG/训练 Trace 均逐位一致、Loss 差 0.0。Gate J 先全局 Packing 与 Gate K Worker 局部分片 Packing 的首 12 Chunk 中 11 条不同。[Gate K 通过结果](docs/R2_GATE_K_RESULT.md)。首次 187 项有 1 ERROR 的双重分片故障仍归档在 [Failure 001](docs/R2_GATE_K_FAILURE_001.md)。**原版 PR27 远程 HF Streaming、实际 Parquet Source Offset/SIGKILL/GPU 仍未验证。**

**Gate L 已于 2026-10-16 在用户 Codespaces 实测：197/197 tests PASS；两个真实 OS Worker 都存活时，HF 原生分片为 28/28，模拟 PR27 双重分片只覆盖 14/28。具体记录见 [Gate L Result](docs/R2_GATE_L_RESULT.md)。** [实验计划](docs/R2_GATE_L_DOUBLE_SHARD_COVERAGE_PLAN.md)、[代码](scripts/r2_pr27_double_shard_coverage.py)、[回归测试](tests/test_r2_pr27_double_shard_coverage.py)。本关没有模型训练，完全离线，只将 Gate I 真实文本来源验证后的 28 条开发文档转成 SHA Hash（**不把原始文本传给 Worker**），在本地创建 **8 个 HF Arrow Shards**，启动两组各两个真实 OS Worker：对照 A 只使用 HF 自动 Worker Sharding；负控 B 模拟上游 PR27 显式 Worker `.shard()` 然后 HF 又自动分片。重点不是 PID 是否存在，而是即便 B 组两个 Worker 都正常运行，是否仍然**漏读真实来源的 ID Hash**。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_double_shard_coverage.py --repo .

结果保存在 Git ignored `research/mini_mythos/results/r2/pr27_gate_l_double_shard_coverage.json`，报告不含真实正文。Gate L 在本地 8 Shards 实测 14/28 文档静默漏读，但**不能把这 50% 推定成正式远程 FineWeb-Edu 的遗漏比例**；`Resolving data files: 2410` 也不直接代表 `sample-10BT` 本身有 2410 个 Shards。真实多 Shard 证据、原始 PR27 Loader 的修复与断点恢复依然属于后续 P0 工作。

## R2 Gate L 通过：197/197；Gate M 查询实际冻结 sample-10BT 文件元数据

2026-10-16 用户 Codespaces：**197/197 tests PASS（48.077 秒）**。使用 Gate I 已冻结真实 FineWeb 快照里的 28 个内部训练文档 SHA，在本地 8 个 HF Arrow Shards 上启动两个真实 OS Worker 做源覆盖 A/B。Native auto-shard only **28/28**；PR27-like manual `.shard` + HF native auto-shard **14/28**，两个 Worker 均正常输出但**静默遗漏 14 个来源文档序号** `4,5,6,7,12,13,14,15,16,17,18,22,23,24`。实验没有读取线上 HF 数据、没有传递原始文本给 Worker，也没有运行任何模型训练。[Gate L 实测报告](docs/R2_GATE_L_RESULT.md)。**该 50% 比率不是原版 FineWeb-Edu 远程 Parquet 的实测遗漏率。**

已提交 [Gate M 实验计划](docs/R2_GATE_M_REMOTE_FILE_INVENTORY_PLAN.md)、[仅元数据文件清单程序](scripts/r2_pr27_remote_parquet_inventory.py) 以及 [8 项离线测试](tests/test_r2_pr27_remote_parquet_inventory.py)。只查询已固定的 HF Commit `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` 下 `HuggingFaceFW/fineweb-edu` 的 `sample/10BT/*.parquet` 路径与 Size（不下载 Parquet 正文）；SHA 冻结清单，然后只对**文件 ID**做 HF 正常一次 Worker 分片与 PR27 风格双重分片的覆盖投影，`verify` 完全离线。正式 HF `IterableDataset.num_shards` 还需下一轮单独证明，不能把文件数量当成训练 Shard/文档/Token 数。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_remote_parquet_inventory.py freeze --repo .
    python research/mini_mythos/scripts/r2_pr27_remote_parquet_inventory.py verify --repo .

Gate M 新文件位于 Git ignore `research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json`，拒绝覆盖。**Gate M 已于 2026-10-16 实测 205/205 tests PASS：真实 `sample-10BT` Parquet 文件数为 14、清单 SHA 固定、文件 ID 分片投影原生 14/14、双重分片 7/14，离线 VERIFY 通过；见 [Gate M Result](docs/R2_GATE_M_RESULT.md)。**

## R2 Gate M 已实测：205/205 PASS；Gate N 直接查看真正的 HF Streaming num_shards

2026-10-16 Codespaces：**205/205 tests PASS（47.955 秒）**。固定 HuggingFaceFW/fineweb-edu 的 HF Commit `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，真实 `sample/10BT` 目录中是 **14 个 Parquet 文件**，文件名+Size SHA `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209`，离线清单验证成功。对 14 个**文件 ID**按 HF Worker 已知分片规则投影：Native HF auto 一次 **14/14**、PR27 manual+auto 两次 **7/14**，预测跳过文件编号 `001,003,005,007,009,011,013`。**这些不是已测得的远端 IterableDataset 逻辑 Shard 位置或缺失文档/Token 比例**；用户没有下载 Parquet 文件正文、训练模型或运行原版 PR27。[Gate M 实测](docs/R2_GATE_M_RESULT.md)。

已提交 [Gate N](docs/R2_GATE_N_REAL_HF_SHARD_COUNT_PLAN.md)：[真实 HF Streaming Metadata Probe](scripts/r2_pr27_live_hf_shard_metadata.py) 和 [9 项离线回归测试](tests/test_r2_pr27_live_hf_shard_metadata.py)。此关复核 Gate I Snapshot SHA、Gate M 的 14 文件清单外部 SHA，再调用**真正版本固定**的 `datasets.load_dataset(...,streaming=True,revision=SOURCE_REVISION)` **只构造 Dataset 对象**。从主进程读取 `ds.num_shards`，调用 `.shard(2,w,contiguous=True/False)` 后读取子视图的 Shard 计数，不显式迭代源文档、不建 DataLoader、不训练模型。保存包版本与逻辑 Shard-ID 预测，支持独立离线 Verify。

    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py freeze --repo .
    python research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py verify --repo .

新报告位于 Git ignored `research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json`，拒绝覆盖。**Gate N 已于 2026-10-17 用户 Codespaces 实测通过：214/214 tests PASS、真实 HF `ds.num_shards=14`、手动+自动 `.shard()` 真实 API 视图计数 4+3，离线 VERIFY 成功，见 [Gate N Result](docs/R2_GATE_N_RESULT.md)。仍不能宣称远端实际文档/Token 漏读率=50%。** 即便 `num_shards` 与文件数相等，也只是数量吻合，不代表真实 Shard ID/Parquet 文件路径一一对应。构建 HF Streaming Dataset 可能自动读取在线元数据/Schema/File Header，因此不得绝对保证零 Parquet 网络字节；本工具不会显式迭代任何真实文档。

## R2 Gate N 已实测通过：214/214；Gate O 解析真实文件到逻辑 Shard 的元数据映射

2026-10-17 用户 Codespaces：**Gate N 专项 9/9 PASS，完整 214/214 tests PASS（74.424 秒）**。固定 `HuggingFaceFW/fineweb-edu` 同一不可变 Commit，真实 `load_dataset(...,streaming=True)` 的 Dataset `num_shards=14`，恰与 Gate M 的 14 个 Parquet 文件数量一致。调用**真实 HF API** `.shard(2,w,contiguous=True)`/`contiguous=False` 各 7/7；手动后再 noncontiguous 的真实元数据视图计数 **4+3**。根据 Shard 分配规则预测原生 14/14、双重 7/14，漏失逻辑 Index 1,3,5,7,9,11,13。`verify` 完全离线 PASS。环境 Python 3.14.2、`datasets` 5.1.0、torch 2.14.1、huggingface_hub 2.2.0、pyarrow 26.0.0；没有迭代文档、运行原版 PR27 Worker 或训练。详见 [Gate N 实测结果](docs/R2_GATE_N_RESULT.md)。

已提交 [Gate O 预注册方案](docs/R2_GATE_O_REAL_HF_FILE_SHARD_MAPPING_PLAN.md)、[Gate O 文件路径映射脚本](scripts/r2_pr27_real_hf_file_shard_mapping.py)、[11 项离线单测（含新修复防回归测试）](tests/test_r2_pr27_real_hf_file_shard_mapping.py)。此关使用**安装版本固定的 HF `datasets==5.1.0` 源码结构**，通过真实 Streaming Dataset 的内部 Parquet `files` 元数据和原生 `.shard()` 子视图，审计每个逻辑 Shard 实际对应哪个 Parquet 文件相对路径；只保留经过白名单校验的 `sample/10BT/NNN_00000.parquet`，不写出 URL Token、远程完整 URL 或正文。不主动迭代文档、不创建 DataLoader、不训练模型。使用 Gate I/M/N 已验证本地证据，发现未知结构就停止。

    git status --short
    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_real_hf_file_shard_mapping.py' -v
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py freeze --repo .
    python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py verify --repo .

结果：`research/mini_mythos/results/r2/pr27_gate_o_real_hf_file_shard_mapping.json`（Git ignored、不覆盖）。**Gate O 已于 2026-10-17 实测通过：专项 11/11 PASS、全量 225/225 PASS（48.712 秒），真实 HF Source 文件路径映射 Native 14/14、双重分片视图 7/14，离线 VERIFY 成功，详见 [Gate O Result](docs/R2_GATE_O_RESULT.md)。首次 10 项中 9 PASS、1 FAIL 的 FakeDataset 计数污染问题仍在 [Failure 001](docs/R2_GATE_O_FAILURE_001.md) 归档，经过隔离夹具修复才重新通过全部 11 项。** 即使源路径映射成功，也不是实际原版 PR27 Worker 漏读文档或 Token 的计量。用户工作区里原有未跟踪 `SETUP_LEOTREE2020.md` / `mini_mythos_leotree2020_overlay_v04.zip` 应原样保留。

## R2 Gate O 正式通过：225/225；Gate P 两个真实 Linux Worker 只重放真实来源文件身份

2026-10-17 Codespaces：Gate O 专项 **11/11 tests PASS**；全量 **225/225 tests PASS（48.712 秒）**。真实固定 `sample-10BT` HF Streaming 的 `_ex_iterable.kwargs['files']` 源元数据以及真正 `.shard()` 的文件路径视图审核成功，实际 Parquet 身份 Native 14/14、手动 contiguous + HF native auto 路径 **7/14**。元数据视图中缺失七条真实文件身份：`001_00000.parquet`、`003_00000.parquet`、`005_00000.parquet`、`007_00000.parquet`、`009_00000.parquet`、`011_00000.parquet`、`013_00000.parquet`。`freeze` 与 `verify` 均运行成功，`Offline Gate O HF real file-shard mapping: VERIFIED`。[正式结果](docs/R2_GATE_O_RESULT.md)。**未运行原版 PR27 双 OS Worker 远端读行，因此不是已测得的文档或 Token 漏读比例。**

已提交 [Gate P 实验计划](docs/R2_GATE_P_OS_WORKER_REAL_FILE_ID_REPLAY_PLAN.md)、[Gate P 真实 OS Worker 身份重放工具](scripts/r2_pr27_os_worker_file_identity_replay.py)、[8 项新回归测试](tests/test_r2_pr27_os_worker_file_identity_replay.py)。从严格验证过的 Gate O JSON 提取原始 HF 14 个 Parquet 文件**路径 ID**，将它们作为 14 条本地 Arrow 身份记录（14 个本地 Shards），让两个真的 Linux `DataLoader` Worker 分别执行 HF 自动分片或先手动后自动分片；仅检查文件身份的覆盖、worker PID、顺序和缺失，**不从远端下载 Parquet 正文、不让 Worker 读取真实文本、不训练模型**。这一关是本地身份重放，而不是原版远端 Worker。

    git status --short
    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_os_worker_file_identity_replay.py' -v
    python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
    python research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py freeze --repo .
    python research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py verify --repo .

Git ignored 输出 `research/mini_mythos/results/r2/pr27_gate_p_os_worker_file_identity_replay.json`，拒绝覆盖。**Gate P 目前只提交候选代码，尚未在用户 Codespaces 运行。总测试数预计 233（包含 8 个 Gate P 测试），不得提前宣称成功。** 用户现有未跟踪的 `SETUP_LEOTREE2020.md` 与 `mini_mythos_leotree2020_overlay_v04.zip` 原样保留。
