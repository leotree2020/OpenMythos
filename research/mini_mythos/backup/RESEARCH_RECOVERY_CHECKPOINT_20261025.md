# Mini-Mythos / OpenMythos — 全项目恢复检查点

**备份日期：2026-10-25（Asia/Tokyo）**  
**触发原因：Grok 使用额度暂时耗尽；暂停研发，防止会话丢失或新 AI 误解实验状态。**  
**备份性质：GitHub 代码/历史证据的远端保护与恢复指令，不代表运行新的实验。**

> **最重要的恢复结论：F2-B、限定范围 F2-C、F2-D 的冻结 CPU 范围 PASS/CLOSED；F2-E-A 源码设计 PASS/CLOSED；F2-E-B1 则因验收探针缺口仍为 PENDING R1，绝不能写成 FINAL PASS。下次恢复先阅读本文和 F2-E R1 审核门禁，禁止直接启动 GPU 或更改 Parcae 架构。**

## A. 唯一研究源和备份锚点

- 主研究仓库：`https://github.com/leotree2020/OpenMythos`
- 活动研究分支：`mini-mythos-p1c-gate22c-readiness`
- **暂停时原始研究 HEAD**：`0853051ec1791adbc54e4e8c90f2be146a0ff092`；这是 ChatGPT F2-E-B1 审核/R1 门禁检查点。
- 原始 R1/R2 的其他研究工作和 Mini-Mythos 源码也包含在这个 Commit 的仓库文件树中。不要拿早期 `mini-mythos-research` 分支名称替代当前真实研究分支。
- 已创建完整的**暂停前 Git 文件树清单**：`research/mini_mythos/backup/PROJECT_TREE_MANIFEST_20261025.json`，针对上述 `0853051...` commit 的 **444 个已跟踪文件**（约 2,803,100 字节原始文件内容），记录每个文件路径、Git blob SHA 和大小；该清单不包含 `.git` 历史包或本地未提交更改。
- 清单自身提交：`9a6cd30b014da41e51a830d91443cade2217670b`；本文件及备份分支在完成时另有更新的 Git HEAD，务必以最终创建的备份分支为准。
- 原版上游 `sandyresearch/parcae` 固定 Commit：`69284c13746e849104f738d6d1a347b1f457df76`。已批准实验中保持原样。
- AxoNN 独立固定 Commit：`c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`。
- OpenMythos 上游候选（与原生 Parcae 是不同来源）：`kyegomez/OpenMythos`；曾审核 PR #27 固定 `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`。它是公开 PR 的代码候选，不等于已完成真实 GPU 训练。
- **已有工作区例外**：Grok 多次报告 `research/mini_mythos/gate2_1/TEST_RESULTS.json` 存在既有未提交本地修改。**该内容不在 GitHub 备份中**，ChatGPT 也无法访问它的未提交实际字节。恢复时不可 `git reset --hard`、`git clean -fd`、`git stash -u` 后删除、`git checkout --` 该文件或在未检查前覆盖。应由持有旧 Codespaces 工作区的人独立导出并核对。
- 当前 GitHub 备份不代表旧 Codespaces 实时文件系统、Python 虚拟环境、HF 数据缓存、模型权重或未上传的实验原始数据的镜像。

## B. 五条不可改变的科研规则

1. **CPU 优先，GPU 按需**：源码、数学、单测、Tiny 模型、梯度验证优先 CPU；CUDA 特性、显存、吞吐和规模训练必须另行申请授权。
2. **实验必须明确目的、环境、输入、预期与实际和正式 PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT TESTED**。命令 Exit 0、stderr 为空、GitHub 文件存在，不单独构成 PASS。
3. **上游源码不修改**；先忠实复现 Parcae 和 OpenMythos 上游行为，独立研究探针保持隔离；绝不因单个 Tiny 失败擅改递归 Transformer 架构。
4. **ChatGPT 与 Grok 相互独立审核**；有分歧，保存分歧并设计最小受控 CPU 实验；不能以任一 AI 意见代替原始证据。
5. **每阶段必须写入 Git 检查点**：实验结果、原始证据哈希、Git HEAD/status、依赖、遗留问题和下一条指令；新会话首先阅读最新检查点。

## C. 阶段索引：如何不丢失早期研究

早期工作不止 F2 系列。以下历史记录保存在本研究 Git 文件树：

| 阶段 | 证据入口 | 已确认边界 |
|---|---|---|
| R0 架构和训练风险 | `research/mini_mythos/docs/R0_ARCHITECTURE_TRAINING_AUDIT.md`、`R0_GATE_A_RESULT.md` | 原版审计、微型复现；不能宣传拿到 Claude Mythos 权重 |
| ACT 001–004 | `docs/ACT_001_002_RESEARCH_REPORT.md`、`docs/ACT_003_*`、`docs/ACT_004_*` | Adaptive Computation/缓存/循环实验与分阶段评审 |
| R1 数据/训练复现 | `docs/R1_GATE_A_RESULT.md` … `R1_GATE_F_RESULT.md` | 小模型真实文本与 heldout 对照。历史 Gate F 记录 106/106 单测、Tiny GQA PPL 10.852968 对 Add-1 12.790071；仍不具备可信的连贯语言生成能力 |
| R2 数据流/PR #27 | `docs/R2_GATE_A_ENVIRONMENT.md` … `docs/R2_GATE_Q_RESULT.md`、`docs/R2_PR27_SOURCE_REVIEW.md` | 上游先行、数据分片/worker 与流式恢复；Gate Q 文件记录 241/241 和 8/8 CPU 单测，但真实远端 Parquet/GPU 不能据此推断 PASS |
| P1-N、P1-C Gate 2.2 | `docs/p1c/`、`gate2_2/` | 模型/optimizer/tokenizer/训练入口/显存风险门禁。**Gate 2.2-C、native 完整训练及所需 GPU correctness 不因 F2 PASS 而自动解锁** |
| F2-B | `docs/F2B_FINAL_ACCEPTANCE_20261024.md` | **PASS/CLOSED**：原生 Parcae 的限定循环机制/固定深度 CPU 行为 |
| F2-C | `docs/F2C_FINAL_ACCEPTANCE_20261024.md` | **PASS/CLOSED（限定）**：3 个预选 Core 标量、2 个 FD 步长，FULL (0,2)/TBPTT (1,1)。原版 float32 路径下的纯 fp64 仍 BLOCKED |
| F2-D D1–D6 | `docs/F2D_D1_D6_FINAL_ACCEPTANCE_20261025.md` | **PASS/CLOSED（限定）**：固定深度、OFF/per-iteration/per-block 的数值和 RNG/checkpoint 验证 |
| F2-D D7 | `docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md` | **PASS/CLOSED（限定）**：默认 per-batch 自动采样 S1–S6、CPU RNG、重算/梯度；**不是所有采样模式的结论** |
| F2-E A | `docs/F2E_A_CHATGPT_REVIEW_AND_B1_CPU_GATE_20261025.md` | **PASS/CLOSED（设计阶段）**；冻结 E1–E6 的 CPU 门禁 |
| **F2-E B1** | **`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`** | **PENDING R1，未关闭**；下次唯一直接恢复点 |

完整文件路径应加前缀 `research/mini_mythos/`；本表中 `docs/` 和 `gate2_2/` 均相对这一根目录。历史早期文档可能包含旧的「下一步」指令：**当前较新的 F2-E R1 门禁优先级最高**。

## D. 最新实验（F2-E B1）的源、执行和真实审定

- Grok F2-E B1 原始实验 Commit：`bcfd38e77bae2524d58b560d79920e2106fd1f03`。
- ChatGPT 最近正式独立审核/R1 门禁：`0853051ec1791adbc54e4e8c90f2be146a0ff092`。
- CPU 执行由 Grok 报告：Python 3.11.2；PyTorch 2.14.1+cpu；x86_64；2 threads（沿用微型模型配置），Parcae HEAD `69284c1` 且记录 clean；`247936` 参数，74 个训练梯度张量为既有验收预期，实际 F2-E 还必须作全量验证。
- 测试入口：`research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`。
- 原始证据目录：`research/mini_mythos/gate2_2/evidence/f2e/b1/`，包含 JSON、RUN_META、stdout、stderr、exit。
- 原始执行命令：
  ```bash
  PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py --parcae-root /tmp/parcae-src --output research/mini_mythos/gate2_2/evidence/f2e/b1/F2E_B1_RESULTS.json
  ```
- 原始归档 `RUN_META.json` 中 SHA256 值在 ChatGPT 审核时通过独立 4/4 复核：
  - `F2E_B1_RESULTS.json` = `cfa698eecdd34fbcb99f65d576122095999665823033399ee63bb897ea09c9b1`
  - `stdout.txt` = `7836a732ee844f68f4620ac27878201afbb7221ff7b06434c380535f04818535`
  - `stderr.txt` (empty) = `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - `exit_code.txt` = `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`
- 实验配置：CPU float32 SDPA，2/2/2 Prelude/Core/Coda，mean_recurrence=2，mean_backprop_depth=2，state_init=like-init，sampling_scheme=poisson-truncated-full，seed42/输入种子1000。
- 权重 SHA256 = `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`；B1/S8 输入 SHA `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`；B2/S8 输入 SHA `ba67e905c68c9fcd61eb3ab5a028ef28ea5c575be78b84d18212ea68e6f900ae`.
- 已观察 E1 per-batch `n=[1],k=[1]`, outer=2，符合 scalar `n=T`；
- 已观察 E2 per-sequence `n=[0,0], k=[1,2]`, outer=2，记录两个梯度阶段的 recurrent masks [2,1,1]；
- 已观察 E3 per-token `n=[[0,0,0,1,0,0,1,0],[1,0,0,2,0,0,0,5]]`，`k=[[1,2,2,2,2,1,2,1],[2,2,1,2,2,1,2,2]]`，outer=7。原理上 no-grad 接受更新总数 10、grad 接受更新总数 27；对应原始 mask true counts 5+2+1+1+1 与 16+11。
- 当前 `torch.where` 探针还混入与 Core 接受掩码无关的 [B,S,64] 调用；实际 native `iterate_forward()` 截断均值尚未被捕获（测试只自算），不能宣布完整验证。
- E4 仅有 per-sequence 重复、E5 仅有 per-sequence OFF/ON；**per-token 这两格 NOT TESTED**。
- E6 原始受控实验曾报告全张量最大差 0.424110 和正对照 0.277730，但该代码在 **per-batch** 模型中覆盖 per-token sampler（实际未触发），又未只测后续 active token；其 **因果耦合结论应标记 INCONCLUSIVE**。未经对照不得改写为 DETECTED。Cross-mode logits equivalence = NOT APPLICABLE。
- 原版 `per-batch` 采样：`T=max(Poisson(t+s),1), n=T, k=min(T,s)`，外层 n+k；`per-sequence/per-token`：`k=min(T,s), n=T-k`，外层 max(n_i)+max(k_i)；返回 per-element n/k 的均值会分别转换为 long 截断。**作者意图 INTENT UNKNOWN，不能擅自定性或修复。**

## E. 下次恢复的唯一批准任务：F2-E B1-R1

**不是新架构、不是新训练、不是 GPU。** 首先阅读：
`research/mini_mythos/docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`
及 `research/mini_mythos/docs/F2E_A_CHATGPT_REVIEW_AND_B1_CPU_GATE_20261025.md`。

只允许修改 `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`，在**独立**新目录 `research/mini_mythos/gate2_2/evidence/f2e/b1r1/` 写入新证据。必须解决：

1. **实际原版返回值**：不重跑 `iterate_forward`，不改原版源码，以只调用一次原版的 noninvasive wrapper 捕获返回 `num_steps_no_grad`/`num_steps_with_grad`；分开校验真实截断均值与 outer max。
2. **每轮真实 Mask/接受更新**：只截取 recurrent `torch.where`，区分 no_grad/grad、局部轮次、全局 step 和 [B,1,1]/[B,S,1]；验证 active mask 按采样矩阵生成、状态写入选择和总接受次数。不要把其他 `torch.where` 误计。
3. **补 E4/E5 per-token**：与 per-sequence 都做同种模式的完整重复和 Checkpoint OFF/ON 对照，冻结输入、权重、采样 RNG；两侧 74 梯度张量的名称/有限/非零，全部 Logits/Loss/grad 比较，冻结的 3 个 F2-C Core 标量，Backward 重算与无重新采样。数值容差依原门禁，绝不后调。
4. **E6 单独隔离**：真正 per-token 模型、B2/S8、测试侧预置合法异构 T/n/k，标记 CONTROLLED；扰动一个更早 inactive Token 仅一个状态通道 +0.1，测量**后续 active Token**（不是全张量）的状态变化，另做 +0.1 正对照；观测阈值严格 `>1e-6`。如不具备非侵入性证据，标记 INCONCLUSIVE/ BLOCKED，不修改原版，也不强制 DETECTED。
5. **真实负例与保存**：正式验收函数拒绝错 n/k/shape、Mask、max、均值、RNG、梯度、checkpoint replay、输入/权重；记录 Git、依赖、每格预期与实际，原始 stdout/stderr/exit、SHA256。失败不应 Exit 0。
6. **结束门禁**：单独新 Commit；状态 `PENDING CHATGPT REVIEW`；停止让 ChatGPT 独立审核。保留旧证据及无关 dirty file。

可以交给后续 Grok/ChatGPT/任何编程 Agent 的简短指令：

> **请先读取本恢复检查点以及 F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md。只执行 F2-E-B1-R1 的原生 Parcae CPU 验收探针修正。不要运行新实验模式，不修改 Parcae/AxoNN，不启动 GPU，不修改历史证据，不触碰 gate2_1/TEST_RESULTS.json。按照原冻结种子、模型、输入与容差重跑 E1–E6；在 f2e/b1r1/ 归档并提交 Commit；状态保持 PENDING CHATGPT REVIEW 后停止。**

## F. 恢复、复核和安全操作指令

GitHub 可访问时，以**具体 Commit**为主，绝不依赖模型聊天记忆推断分支状态：

```bash
git clone https://github.com/leotree2020/OpenMythos.git OpenMythos-Recovery
cd OpenMythos-Recovery
git fetch origin mini-mythos-p1c-gate22c-readiness
git switch -c mini-mythos-p1c-gate22c-readiness --track origin/mini-mythos-p1c-gate22c-readiness
git rev-parse HEAD
git status --short
cat research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md
cat research/mini_mythos/docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md
```

如果旧 Codespaces 存在本地未提交结果，请先在旧工作区单独保存该文件原始字节（可选：存成文件+sha256；仅在安全的私人位置），不要用上述新 clone 代替该内容。**远端备份只包括已提交 Git 文件**。继续执行前确认 `git status --short`、上游 Parcae SHA、Python/PyTorch 和可用 CPU 环境。

所有验收与备份证据是研发过程的一部分，不是 Anthropic Claude Mythos 的真实技术、权重或性能复刻证明。对 Claude Mythos 的黑箱重建只能用合法公开的上游源和可复现实验做科研假设。

## G. 恢复后的优先级

1. 恢复 Git/代码与已跟踪证据，独立保护本地 dirty file。
2. 阅读 F2-E R1 门禁；如 Grok 额度仍不足，可以由其他具代码执行权限的 Agent 在同一冻结门禁下接续，不能擅自降低验收标准。
3. 在 CPU 上完成最小 E4/E5 per-token 和 E6 探针隔离，取得完整证据后请 ChatGPT 独立审核。
4. 只有 F2-E 的范围明确 PASS/CLOSED，才讨论新研究问题和是否有必要验证 GPU。
5. **不自动解锁 Gate 2.2-C / 全量训练**；这些拥有独立门禁。

**暂停状态：BACKED UP / DEVELOPMENT PAUSED / F2-E B1-R1 NOT STARTED.**
