# Mini-Mythos / OpenMythos — 全项目研发进度（2026-10-25 更新版）

## 最新阶段补记：F3-A-R1 CPU 正常训练与断点恢复（2026-10-25）

**本段是本文件最新阶段状态，优先于下方 F3-A 初次审计与旧时间点快照，不能把老文中的 R1 待执行当成当前事实。** Grok 先提交 F3-A-R1 冻结补充 `8ea2d674404c44f5887fd248ef25a33c1a622727`，随后提交完整 R1 CPU 运行 `14974c8e2a6ad11bea7b45df4242b5acbad3abfe`。维持原 Parcae 2/2/2/AdamW/linear scheduler/fixed input/6 steps。第 1 步 LR=0 不更新、step2–6 更新；Loss 4.96057→2.73600；连续与文件恢复在 step4–6 的模型 SHA、loss、LR、optimizer SHA、scheduler 新建 config、torch/python/numpy RNG SHA 均一致。

ChatGPT 独立复核：R1 四项文本证据 SHA-256 全部 MATCH，提交脚本 SHA-256 独立计算，原生六步学习率与上游数学 6/6 一致；**F3-A 正常训练与断点恢复路径限定 PASS/CLOSED；F3-A 整体 PARTIAL / NOT CLOSED**。原因：实际保存的 scheduler 内容只验证字段存在，未验证错误配置；没有有效格式但错误的 RNG 内容的受控恢复失败例；所谓坏 shape 负例实际上只移除一个 state_dict 键。详见 `research/mini_mythos/docs/F3A_R1_CHATGPT_INDEPENDENT_REVIEW_AND_FINAL_DELTA_GATE_20261025.md`。二进制 checkpoint 的 SHA-256 本次无法通过现有 GitHub 只读二进制接口独立核实，仅验证文件存在、size 与 Git blob SHA。

**当前唯一下一步**：用已有 R1 已提交 Checkpoint，在限定研究目录内完成三个内容级异常恢复/拒绝负例；若需要真实运行仅允许最多一个独立的恢复 step，不重跑整个 6 步训练，不修改上游或架构、不启 GPU、不做规模训练；新证据归档并停在 PENDING CHATGPT REVIEW。完成后推进真实数据训练/数据流恢复的方案审计，避免无限扩展微型探针。

## 最新阶段补记：F3-A 首次 CPU Train Lifecycle 运行（2026-10-25）

**此补记优先于本报告下方早期“未授权/未执行”措辞**。项目负责人已授权 Grok 执行 F3-A。Grok **先冻结** `docs/F3A_FROZEN_CONFIG.md`（commit `34c4414667e939560cae69c0a2dc58fca14f9ef5`），再提交 `gate3_cpu_train/f3a_lifecycle.py` 和 CPU 六步 AdamW 固定输入生命周期实测（commit `3b582c7ac8c4ac7e4473d48ee78e05b5326b8026`）。损失 `4.933872→2.713740`，第 2–6 步权重更新，step4–6 的 A/B Loss/LR/权重哈希相同，四项声明文本 SHA256 经 ChatGPT 独立 MATCH。第 1 步 frozen warmup LR0，权重不变，必须保留该预期与原冻结 STOP 条款矛盾，不得事后掩盖。

**ChatGPT 正式审核结论：F3-A PARTIAL POSITIVE / NOT CLOSED。** `step()` 每步重设 RNG，导致恢复 RNG 未获真实因果验证；Checkpoint 的 step/scheduler 内容没有被加载器验收；未逐步对比 optimizer state、三类 RNG 和训练位置；错误 Checkpoint 负例仅改字典并未测试真实 loader 拒绝。详见 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md`。二进制 checkpoint `f3a_step3.pt` 已在 GitHub 追踪（size=3,079,307 bytes；Git blob SHA `b351dacfa9aac7be759ade893b249ebb9485d5b8`）；报告的 SHA-256 未能从当前只读二进制连接器独立重算，需如实标记。

**下一步**：仅允许冻结 F3-A-R1 的最小恢复验证补充、隔离 CPU 验收及原始证据归档，严禁启动新的采样/架构实验、GPU、规模训练、修改上游 Parcae。完成后 `PENDING CHATGPT REVIEW` 停止。已关闭的 F2-B/C/D 与 F2-E E1–E5 维持原结果，E6 仍 INCONCLUSIVE。Claude Code 暂不接管；Grok 主开发，ChatGPT 审核。

**状态性质**：研究项目总体进度与治理检查点，不是新模型实验。  
**最新实测 Git 统计基线**：研究分支 `mini-mythos-p1c-gate22c-readiness` 的 `ee1b3c8564f4cc868e73efd58e4ddc42c35e4f78`，完整 Git recursive tree（`truncated=false`），**481 个 tracked 文件、154 个 Python 文件、3,050,894 bytes**。本文及后续 Git 文档更新会推进 HEAD，新的会话必须重新验证。  
**上一次历史基线**：`0853051ec1791adbc54e4e8c90f2be146a0ff092`，444 文件、153 Python、2,803,100 bytes；中间 `2ceb08b1db34871104a45e27e5ec2f7bc81e0ce1` 为 470 文件、154 Python、3,003,079 bytes。  
**统计注意**：文件大小单位 bytes，不是代码行数；精确 LOC **NOT MEASURED**。不含上游 Parcae/AxoNN 代码、环境依赖、HF 缓存、模型权重和未提交工作区。

## A. 一句话结论

**Mini-Mythos 已取得小模型真实数据训练/有限 heldout 优势以及原生 Parcae F2-B、F2-C、F2-D 和 F2-E E1–E5 的冻结 CPU 正确性验证；下一阶段应从探针研究切换到随机权重的原生 CPU 完整训练链，而不是无限延续 F2-E。**

**严格限定**：F2-E `E1–E5 PASS/CLOSED` 是固定 `2/2/2` 原生 Parcae、特定 float32 CPU 配置、种子/输入、采样/Mask/重复性/Checkpoint 微型验收的结论；`E6 INCONCLUSIVE`，**整个 F2-E 不等于无条件全 PASS**。原生完整 CPU Training Lifecycle 尚未运行/验收，GPU Gate 2.2-C 仍 BLOCKED。不能声称复现了 Anthropic Claude Mythos 未公开的真实架构/权重/能力。

当前开发分工以用户最新决定为准：**Grok 继续开发与 CPU 执行**；**ChatGPT 独立验收**；Claude Code 暂缓接手。

## B. 五大模块：统一排他统计

沿用原 `PROJECT_MAP.md` 冻结的排他分类，对基线 Git tree 差异分组并与 `ee1b3c8` 实际 blob sizes 汇总核对：

| 研发模块 | 当前 Git 文件数 | 当前 bytes | 阶段状态 |
|---|---:|---:|---|
| 核心模型 | 5 | 94,110 | Tiny 预测能力有限验证；模型语言能力未成熟 |
| 训练 | 3 | 24,480 | R1 Tiny 历史训练已验证；原生端到端生命周期 NOT TESTED |
| 实验与工具 | 98 | 639,567 | F2-B/C/D 和 F2-E E1–E5 限定 PASS/CLOSED |
| 测试 | 76 | 484,810 | F2-E 本次限定验收独立通过；无当前 HEAD 全套测试证据 |
| 文档与证据 | 299 | 1,807,927 | 历史证据与独立审核可追溯 |
| **合计** | **481** | **3,050,894** | **Python 文件合计 154** |

以上为 `ee1b3c8` 的**不可变基线快照**。未来文件/文档继续增减时，不要修改这些历史数字来假装是新的 HEAD 统计；应新增新的计量 SHA。扫描 `research/mini_mythos/scripts/project_map_inventory.py` 可取得完整工作树中的准确物理/非空代码行数，尚无已执行结果。

## C. 五模块详细进度

### 1. 核心模型 — 基础机制存在，语言能力仍早期

- 文件：`open_mythos/main.py`, `moda.py`, `variants.py`, `tokenizer.py`, `__init__.py`。
- 历史 Tiny GQA：随机权重训练至 step600，官方 WikiText-2 test 的 byte-level next-token NLL `2.384439`、PPL `10.852968`；匹配训练暴露量的 Add-1 Bigram 基线 PPL `12.790071`。这是限定预测能力证据，非稳健语言生成证明。
- 当前弱点：Greedy 生成重复；没有同预算非循环 Transformer 的质量、FLOPs、训练稳定性、推理成本对照；推理/编程/对话能力 **NOT PROVED**。
- 路线：保留 `Prelude → Recurrent Core → Coda`，从随机初始化训练独立权重；保留上游，模型架构创新只能在后续公平对照阶段引入。

### 2. 训练 — 优先级转为真实完整生命周期

- 文件：`training/3b_fine_web_edu.py`, `training/requirements.txt`, `research/mini_mythos/scripts/pilot_train.py`。
- 已有 R1 Tiny 真实数据训练、冻结官方 test、部分 checkpoint 恢复；R2 数据分片、worker、恢复等有限 CPU 证据。
- **首次 CPU 统一训练链已运行但未正式验收**：固定输入 6 步 AdamW、linear scheduler、step3 文件保存并重建模型继续 step4–6；权重/Loss/LR 等局部观察积极，但关键恢复状态没有独立验收，整体 `PARTIAL / NOT CLOSED`。见本文最上方 F3-A 补记。
- Grok 先提交 `docs/F3A_FROZEN_CONFIG.md` 冻结后运行并归档 `docs/F3A_RESULT.md`；ChatGPT 审核 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md` 明确指出恢复状态与负例的关键验收缺口。不得把记录中的 `LOCAL PASS` 当作整体 `CLOSED`。
- 规模 GPU：`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md` 的环境/成本/真实证据要求仍未通过。

### 3. 实验与工具 — F2 必要 CPU 数学验证已有明确出口

- **F2-B `PASS/CLOSED`**：固定范围原生 Parcae recurrence CPU 路径。
- **F2-C `PASS/CLOSED`（有限）**：冻结三个 Core 梯度标量的 FD 验证，不是完整权重数学证明；纯 fp64 原生路径仍有局限。
- **F2-D `PASS/CLOSED`（有限）**：冻结 fixed-depth/per-batch 自动采样与 checkpoint/RNG/梯度微型验收。
- **F2-E E1–E5 `PASS/CLOSED`（有限）**：per-batch/per-sequence/per-token n/k，真实返回值、实际 recurrent Mask、重复性、Checkpoint OFF/ON 数值/梯度对照；详细审核 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`。
- **F2-E E6 `INCONCLUSIVE`**：直接 Core update 重放不能证明 live masked-loop 的 token 因果传播。原版 Parcae 作者意图 UNKNOWN，不能推断 bug。E6 不是当前完整训练链设计的必经阻塞。
- 决策：**停止新增无必要的 F2-E 采样探针**，推进新训练阶段；旧证据全部保留不可变。

### 4. 测试 — 有历史回归数据，最新 HEAD 全量未跑

- 已归档 R1 Gate F 106/106 单测和 R2 Gate Q 241/241 + 8/8 专项等历史结果（**不同历史时点**）。
- F2-E final closeout：固定本地记录 E1–E5 LOCAL PASS，19 个受控负例被拒绝，特定 E5 checkpoint backward replay 精确两次，9 条 Mask SHA-256 与独立期望重建全部匹配。GitHub 结果/日志/脚本六项声明 SHA-256 全部独立复核。
- 本次 ChatGPT 审核未重新执行 native Parcae CPU 或当前 HEAD 全套 pytest/unittest；不能用历史测试数宣传最新全量 PASS。
- 仍保留未来独立测试：训练 Optimizer 更新、scheduler 步数、checkpoint/resume 逐步等价、完整数值和 RNG 状态。

### 5. 文档与治理 — 可复现和恢复体系已成熟建立

- 已有 `docs/SESSION_START_PROTOCOL.md`、`docs/PROJECT_MAP.md`、本进度快照、旧恢复备份、R0/R1/R2/F2 原始报告与各阶段 ChatGPT/Grok 独立审核结果。
- 新增验收归档 `gate2_2/evidence/f2e/b1_closeout/`；Grok 源提交 `fbeaf7c5030c460343ca2006dc53813c21786dfd`；正式独立审核 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`。
- 现存运维风险：Grok 旧 Codespaces 的 `research/mini_mythos/gate2_1/TEST_RESULTS.json` 曾多次 dirty，该未提交文件实际内容 **NOT VERIFIED** 且不可从 GitHub 恢复。保护它，不执行 reset/clean/覆盖。
- 新会话读最新 Git HEAD、SOP、项目地图、**本进度**和最新阶段验收；旧文中的 Claude 接管/旧 F2-E 待审核字样被最新正式状态取代。

## D. 研发路线与验收门禁（无虚假百分比）

| 阶段 | 当前判断 | 必要出口 |
|---|---|---|
| R0/R1 小模型、R2 数据工具 | 历史限定验收 / 已归档 | 保留复现证据，不以 Tiny PPL 推断模型成熟度 |
| F2-B/C/D | **PASS/CLOSED（限定）** | 不再重复 |
| F2-E E1–E5 | **PASS/CLOSED（限定）** | 不再扩展为新采样研究 |
| F2-E E6 | **INCONCLUSIVE** | 如未来有专门、已授权的因果问题才独立研究 |
| Native Parcae CPU Train Lifecycle 冻结配置 | **F3-A 初始方案已冻结、执行已完成；存在 warmup STOP 标准内部冲突** | 需要在独立 R1 补充中预先清晰裁决，不改历史冻结文件 |
| Native Parcae CPU Train Lifecycle 执行 | **已授权执行，局部积极 / 整体 NOT CLOSED** | 校验逐步 optimizer/RNG/scheduler/step 文件恢复、实际损坏文件拒绝、独立审核 |
| 更大模型与公平非循环基线 | **NOT TESTED** | 实际模型质量、FLOPs、训练时间/稳定性、推理开销受控对比 |
| GPU Pilot / Gate 2.2-C | **BLOCKED** | 凭据、预算/实时定价、启动环境、真实证据提取器、用户授权 |

不按测试数、代码行数或阶段标签简单算统一完成百分比；现阶段的真正里程碑是**基础 CPU 正确性从“仍待收口”转为“限定正式收口”，下一步是开始真实原生训练链**。

## E. 唯一下一条研发指令、授权与 STOP

**当前下一步（Grok，F3-A 狭义验收收口，不扩大研发范围）**：
1. 最新 Git 状态/dirty 只读核对并保护 `gate2_1/TEST_RESULTS.json`；
2. 读取 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`，确认 F2-E E1–E5 仅限定 PASS/CLOSED、E6 INCONCLUSIVE；
3. 必须阅读 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md`，在新冻结补充中处理 LR0 / 原 STOP 条款冲突，修正每步强制 RNG 重置及重载状态的真实比较，让修改后的加载器实际拒绝坏 Checkpoint；保留原始 B1 结果而非覆盖；
4. 提交训练计划和检查点，待项目负责人授权 CPU 端到端执行与 ChatGPT 复核。

**禁止自动运行训练或 GPU，不改 Parcae/AxoNN 原版，不擅自改递归架构，不覆盖旧证据。** 如训练计划中存在尚不合理的 loss 单调下降断言，需在冻结前调整为可预先定义且能被真实训练支持的标准；不能运行之后倒改验收线。绝不可将当前 CPU 微型测试 PASS 外推到 GPU Gate 2.2-C。

## F. 证据索引

- `research/mini_mythos/docs/R1_GATE_F_RESULT.md` — 真实 tiny heldout
- `research/mini_mythos/docs/R2_GATE_Q_RESULT.md` — 分片/多 worker 合成 CPU 数据验收
- `research/mini_mythos/docs/F2B_FINAL_ACCEPTANCE_20261024.md`
- `research/mini_mythos/docs/F2C_FINAL_ACCEPTANCE_20261024.md`
- `research/mini_mythos/docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`
- `research/mini_mythos/docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`
- `research/mini_mythos/docs/F2_CPU_TRAIN_LIFECYCLE_PLAN.md`（设计草案）
- `research/mini_mythos/gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`
- `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`
- `research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`

**本文件只汇总现存 GitHub 数据与已经独立审核的证据，本次未运行新训练、未改上游、未新开 GPU。**
