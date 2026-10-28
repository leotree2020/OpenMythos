# OpenMythos 项目地图（五模块 / 研发状态）

**基线**：2026-10-25 备份前冻结研究 Commit `0853051ec1791adbc54e4e8c90f2be146a0ff092`，文件清单 `research/mini_mythos/backup/PROJECT_TREE_MANIFEST_20261025.json`。**本页属于研发管理索引，不是新的实验 PASS。**

## 1. 范围和可审计统计口径

本地图覆盖 `leotree2020/OpenMythos` 仓库在上述基线的 **444 个 Git 跟踪文件 / 2,803,100 bytes**。不包含未提交工作区、外部 Parcae/AxoNN 源码、模型权重、HF 缓存或依赖包。按文件的**主要用途**排他性归类；研究用训练脚本算实验，只有正式训练入口和 pilot_train 算训练；归档的 JSON/日志归文档与证据。

| 模块 | 文件数 | Python 文件数 | bytes | 典型位置 |
|---|---:|---:|---:|---|
| 核心模型 | 5 | 5 | 94,110 | `open_mythos/` |
| 训练 | 3 | 2 | 24,480 | `training/`, `research/mini_mythos/scripts/pilot_train.py` |
| 实验与工具 | 97 | 70 | 635,081 | `research/mini_mythos/scripts/`, `gate2_1/`, `gate2_2/` |
| 测试 | 76 | 75 | 475,415 | `tests/`, `research/mini_mythos/tests/`, CI |
| 文档与证据 | 263 | 1 | 1,574,014 | `docs/`, Markdown, `evidence/`, 运行归档 |
| **合计** | **444** | **153** | **2,803,100** | |

## 最新 Git 文件树快照（2026-10-25）

2026-10-25 研究分支 `2ceb08b1db34871104a45e27e5ec2f7bc81e0ce1` 的完整递归 Git tree 经实际读取（非截断）：**470 个 Git 跟踪文件、154 个 .py 文件、3,003,079 bytes**。这是可审计的**统计基准 Commit**，其后的文档更新会使 HEAD/文件数/字节数继续变化，应以后续重新扫描为准。

| 模块（沿用原基线归类） | 当前文件数 | 当前 bytes |
|---|---:|---:|
| 核心模型 | 5 | 94,110 |
| 训练 | 3 | 24,480 |
| 实验与工具 | 98 | 639,567 |
| 测试 | 76 | 482,919 |
| 文档与证据 | 288 | 1,762,003 |
| **合计** | **470** | **3,003,079** |

统计方法：2026-10-25 原 444 文件冻结分组 + 该基线到以上 HEAD 的 Git 变更（26 个新增文件、1 个既有测试文件修改），并通过两个 Git tree 的实际文件 size 总和复核。**当前精确 LOC 仍是 NOT MEASURED**。最新详细研究状态见 `docs/PROJECT_STATUS_20261025.md`。

### F2-E 限定收口后的新统计基线

`ee1b3c8564f4cc868e73efd58e4ddc42c35e4f78` 的完整 Git tree 实测：**481 文件 / 154 Python 文件 / 3,050,894 bytes**。比上面 `2ceb08b1` 统计增加 Grok 的 F2-E closeout 实验文件、Native CPU Train Lifecycle 仅设计文档、本项目进度报告和 ChatGPT 正式审核。此表取代上表的“当前”含义；两表的 SHA/数值均作为历史快照保留。

| 模块 | 文件数 | bytes |
|---|---:|---:|
| 核心模型 | 5 | 94,110 |
| 训练 | 3 | 24,480 |
| 实验与工具 | 98 | 639,567 |
| 测试 | 76 | 484,810 |
| 文档与证据 | 299 | 1,807,927 |
| **合计** | **481** | **3,050,894** |

最新实验结论和下一阶段见 `docs/PROJECT_STATUS_20261025.md`、`docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`；精确代码行数仍为 **NOT MEASURED**。

**注意：上述为文件数量和 bytes，绝非已测得的代码行数。** 精确物理行数/非空行数/注释行数须在可访问完整 Git 工作树的执行环境运行 `python research/mini_mythos/scripts/project_map_inventory.py --repo . --output ...`。工具不能执行时标记 **NOT MEASURED**，禁止将字节数换算为 LOC。

## 2. 模块状态：已验证 / 问题 / 尚未开始

### A. 核心模型

- **代码**：`open_mythos/main.py`（模型主体）、`moda.py`、`variants.py`、`tokenizer.py`、`__init__.py`。
- **已验证（有限范围）**：早期 R1 CPU Tiny GQA 真实 WikiText-2 字节级预测，step600 test NLL 2.384439 / PPL 10.852968；匹配暴露量 Add-1 Bigram PPL 12.790071。原生 Parcae 独立复现的 F2-B/C/D 验收**不能直接外推为本目录所有模型配置 PASS**。
- **问题**：Tiny 自由生成重复，连贯语言生成/推理/编程尚无能力证明；不同动态采样模式 n/k 语义的作者意图 UNKNOWN。
- **未开始/未验证**：同预算非递归 Transformer 公平对照、规模化模型质量证明、真实能力基准。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/F2B_FINAL_ACCEPTANCE_20261024.md`、`docs/F2C_FINAL_ACCEPTANCE_20261024.md`。

### B. 训练

- **代码**：`training/3b_fine_web_edu.py`、`training/requirements.txt`、研究 pilot 入口 `scripts/pilot_train.py`。
- **已验证（有限范围）**：R1 Tiny 真实文本训练及 checkpoint 重放；R2 分片、数据流、恢复方面的独立 CPU 证据。并非原生 Parcae 完整训练入口已 PASS。
- **F3-A 最新正式验收**：Grok B1 配置/执行 `34c4414`/`3b582c7`，R1 配置/执行 `8ea2d67`/`14974c8`，最终异常校验提交 `dd36b939`。ChatGPT `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md` 独立复核并批准 **F3-A CPU 固定输入、原生 2/2/2 Parcae、AdamW、6 步与文件恢复研究性生命周期 PASS/CLOSED（限定范围）**。三项异常恢复经过单独 checked loader/验证器，未集成到历史 R1 恢复入口；真实 DataLoader、MuonAdamW、GPU 仍未测试。
- **未开始/未验证**：独立的真实数据 DataLoader 恢复、生产 `scripts/train.py`、MuonAdamW、GPU Pilot、同计算预算质量与效率实验。F3-A 结果中的 Python 元数据 3.10.21 与 `/usr/bin/python3.11` 命令不一致，需只读注明，不能视为环境已验明。
- **证据**：`docs/R1_GATE_F_RESULT.md`、`docs/R2_GATE_Q_RESULT.md`、`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`。

### C. 实验与工具

- **代码**：`research/mini_mythos/scripts/`、`gate2_1/`、`gate2_2/` 中非测试脚本和配置。
- **已验证**：F2-B 原生循环 PASS/CLOSED；F2-C 冻结三个梯度标量的数值检查 PASS/CLOSED（纯 fp64 原版路径仍受限）；F2-D 固定深度与 per-batch RNG/Checkpoint PASS/CLOSED。R0/R1/R2 历史阶段有已归档的限定结果。
- **已验证（2026-10-25 最新）**：Grok `fbeaf7c` 补齐每条 Mask 摘要、Checkpoint replay 精确 2、RNG 配对、权重/74 梯度验收与负例。ChatGPT `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md` 对六项声明文件 SHA-256 和 9/9 Mask 内容哈希独立校验，并正式批准 **F2-E E1–E5 PASS/CLOSED（限于冻结 Parcae 2/2/2 CPU 微型采样/Mask/重复/Checkpoint 范围）**。**E6 仍 INCONCLUSIVE**；无模型 Bug 或作者意图证明，不能将整个 F2-E 无条件标 PASS。
- **最新独立审核**：F3-A 原生 Parcae CPU 固定 6 步 B1/R1、文件恢复后 Loss/LR/参数/优化器/RNG 指纹匹配、三项异常 Checkpoint 对照完成；正式 **PASS/CLOSED（研究性冻结条件）**。原始训练 loader 没有直接整合最终 checked loader，且没有重新运行 `scripts/train.py`。证据：`docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`。
- **证据**：`docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`、`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### D. 测试

- **代码**：`tests/`、`research/mini_mythos/tests/`、`interfaces/test_*.py`、`gate2_1/test_*.py`、`gate2_2/test_*.py`、`.github/workflows/`。
- **已验证**：R1 Gate F 记录 106/106 单元测试 PASS；不同冻结阶段有单独的测试证据。不得将历史 106 或 205/241/248 等数字当作当前 HEAD 全套测试结果。
- **已验证（最新限定范围）**：F2-E closeout 已归档 Mask SHA 并独立重建核对 9/9，严格拒绝 replay=1 且预期 ON=2/OFF=0，新增 sampler/post-backward RNG 比较、权重/梯度身份检查、FAIL exit 1 演示；限定 E1–E5 正式 PASS/CLOSED。更大模型、新种子或完整训练不在此验收内。
- **未开始/未验证**：最新 HEAD 全套单测；真实 Streaming Dataset/Tokenizer/heldout 的训练与恢复、MuonAdamW、生产 `scripts/train.py`、GPU 等均需另外验收，不可外推 F3-A 的固定小样本 PASS。
- **证据**：`docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`。

### E. 文档与证据

- **位置**：`research/mini_mythos/docs/`、`gate2_2/evidence/`、`docs/p1b/ci/`、`backup/`、仓库 README。
- **已验证**：Git SHA 锚点、F2-B/C/D 正式独立审计、F2-E B1 证据 SHA-256 复核、独立备份分支。
- **问题**：历史文档中可能有过期的“下一步”；本地未提交 `gate2_1/TEST_RESULTS.json` 未纳入 Git 备份；旧工作区状态不能通过远端断言。
- **未开始/未验证**：每次新会话自动/人工刷新项目地图的 LOC 和 Git 状态、建立持续变化报告。
- **证据**：`backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`、`backup/PROJECT_TREE_MANIFEST_20261025.json`。

## 3. 当前研发门禁与下一阶段

1. **当前唯一下一项（仅设计）**：Grok `dd36b939` 三项异常校验获 ChatGPT `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md` 审核批准，**F3-A 限定研究性 CPU 生命周期 PASS/CLOSED**；结束所有 F3-A 微型实验。接下来只读审计真实数据/Tokenizer/数据分片与 worker 恢复、冻结 heldout 评估与同计算预算非循环基线方案。**未授权实际真实数据训练、GPU、上游修改**；Claude Code 暂缓。
2. **之后分级执行**：先冻结真实数据、数据流恢复与公平模型评估的可复验收计划，项目负责人授权后再开展 CPU 正确性实验；真实规模吞吐/显存才考虑另行批准 GPU。
3. **再之后**：在受控的真实数据训练条件下比较模型能力、参数量/FLOPs/延迟，保持独立随机权重与循环核心不变。
4. **最后且独立批准**：GPU 门禁、规模训练、效率优化、架构创新。不能用当前微型 PASS 自动解锁 Gate 2.2-C。

## 4. 新会话强制入口

**所有新会话在执行任何代码/提出新实验前必须先读取 `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`，再读取本项目地图和最新正式检查点。** 先报告 Git HEAD、工作区 dirty 文件、最新验收门禁、五模块状态与下一条唯一批准指令。若缺少仓库/工作区访问，标记 UNKNOWN 并停止任何可能破坏数据的操作。不可从聊天记忆猜测当前 HEAD 或 PASS。

## 5. 变更控制

- 本文初版是**基线快照**，后续应以实际 Git 工作树扫描结果补充精确 LOC，不要悄悄覆盖旧基线。
- 每次阶段验收后更新：模块统计（含基线 SHA）、PASS/FAIL/BLOCKED/NOT TESTED、证据路径、剩余风险、下一步；另保留阶段检查点。
- 原始五条科研规则始终有效：CPU 优先、预设验收、上游不变、交叉审核、阶段检查点。


## F3-B 设计阶段审核（2026-10-25）

Grok `103344e47184735e03727d062ce81cbae6632e47` 提交五份研究设计文档，未提交新的训练实验。ChatGPT 独立审核见 `docs/F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`：**F3-B DESIGN DELIVERABLES PASS/CLOSED（仅五份设计交付）**；**D1 DRAFT / NOT FROZEN / NOT AUTHORIZED**，D2/D3 NOT TESTED/NOT AUTHORIZED；官方 Parcae Tokenizer BLOCKED，GPU 未授权。

**当前唯一下一步（不跑代码、不下载/拟合 Tokenizer）**：Grok 仅编写一份 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，锁定 `Salesforce/wikitext` / `wikitext-2-raw-v1` / revision `b08601e04326c79dfdd32d625aee71d232d685c3`，冻结 BPE train-only 编码/许可/特殊 Token、单进程 source ID 与 Token cursor/断点续读、有限比较窗口及跳/重/错位负例。**D2 必须单独解决 vocab128→目标 BPE4096 时输入/输出形状与实际参数量变化**，不能仍称 247936 参数模型。Git 历史 R2 Gate M/N/O/P/Q 的文件级和本地合成专项 PASS 不代表远端逐行/DataLoader Resume PASS。

下一步仅为 D1 门禁设计提交，之后需 ChatGPT 审核和项目负责人明确 CPU D1 数据读取/Tokenizer 拟合的执行授权；不自动授权新训练、GPU 或架构变更。


## D1 预飞行方案（2026-10-26）

Claude Code 接替 Grok 担任主要研发工程师（项目负责人 2026-10-26 指令），ChatGPT 继续独立审核。新增 `docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`（仅文档，0 行执行代码）：逐条冻结 D1-01…D1-04，并把 D2 的 vocab 128→4096 参数量冲突登记为前置事项（词表相关参数 DERIVED 为 `320×V`，整体对账有 832 残差，故只作 ESTIMATE，D2 必须实测）。

**状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`**。D1 `NOT FROZEN→PROPOSED`，未获执行授权；D2/D3 `NOT TESTED`；GPU 未授权；官方 Parcae Tokenizer `BLOCKED`。本次没有新增实验 PASS，也没有刷新五模块文件数/字节数统计（该基线仍是上方 `ee1b3c8` 快照，当前 HEAD 的精确统计 **NOT MEASURED**）。

## D1 预飞行方案 R1 修订（2026-10-26）

基准 `ab6d8271f30cb49e097f3979e29f42bf0e96d545`。依据项目负责人转达的 ChatGPT / Work 独立复审意见，新增 `docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL_R1.md`（仅文档）；v1 方案 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`（SHA-256 `a55b2cb7…ba9e`）**原样保留**为历史证据。R1 要点：负例分为 LR（加载拒绝）与 CR（继续读取）两类并各有 PASS 判据；N1/N2 改为合法游标恢复后读取过程内整行跳过/重复；游标升级为 `d1_cursor_v2` 并采用 9 步固定顺序校验；5 个预先确定、升序的中断点 P1–P5，空 carry 合法；固定 Token/哈希序列化与尾部核算；冻结 Tokenizer 的 encode/decode/特殊 Token/padding/truncation/后处理；勘误：F3-A 参数量静态公式 `P(V)=206,976+320V`（V=128 与归档断言 247,936 精确吻合，适用前提见 R1 第 10 节）。

**状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。修订成功不是实验 PASS。五模块统计基线本次未刷新（NOT MEASURED）。

## D1 预飞行方案 R2 最小修订（2026-10-26）

基准 `579ffd11ec2dba0b9cbf0eae67d7ce4e26874c19`。R1 复审结论 `PRE-FLIGHT FAIL`；新增 `docs/F3B_D1_FROZEN_EXECUTION_PROPOSAL_R2.md`（仅文档）。v1（SHA-256 `a55b2cb7…ba9e`）与 R1（SHA-256 `f92c4e79…1d7a`）**原样保留**。R2 只改 5 处：（1）CR 负例用可信干净前缀 + 续读 trace 重新核算整个窗口，逐行核对 Token 数量、原始位置与完整内容，注入证据与干净证据分开保存；（2）CR3 的原始游标先通过全部九步校验，不得关闭加载检查，仅在读取循环内注入消费偏移，磁盘游标不改；（3）CR3 固定 `δ=+1`、P2 只选 Token 数 ≥ 3 的行，删除 `δ=−1` 回退；（4）P2 搜索区间为合格行序号 [600,900)，找不到记 `BLOCKED(schedule)`，删除「相邻中断点相隔 300 行」的错误断言，改以实际 Token 流位置严格递增为判据，P3/P4 搜索起点包含行起点；（5）哈希链用零起始块号：`H_{j+1}=SHA256(H_j ‖ block_hash_j)`，32 字节原始摘要拼接，`chain_hash=H_N`，并给出合成校验向量。R1 其余条款（LR1–LR9 主体、九步校验、空 carry、EOF、序列化、`P(V)=206,976+320V`）保留。

**状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。修订成功不是实验 PASS，不是 D1 CLOSED。

## D1 执行脚本冻结准备（2026-10-26）

基准 `8a1700835c619fc1ad579da12713ece612403b8e`（ChatGPT 已对 R2 设计做静态复审 PASS，这不是 D1 实验 PASS）。新增 `gate3_d1/`：`d1_reader.py`（读取器）、`d1_verifier.py`（独立验证器，与读取器不互相 import、不共享游标校验/来源映射/参照流函数）、`d1_driver.py`（clean A/B + LR1–LR9 + CR1–CR3 编排）、`d1_env_manifest.py`、`D1_FROZEN_CONFIG.json`、`requirements-d1.txt`、`D1_ENV_FREEZE.md`、`D1_CODE_SHA256SUMS`，以及 `tests/test_d1_selftest.py` 和记录 `docs/F3B_D1_CODE_FREEZE_PREP_20261026.md`。实现区分中间 carry 与 EOF tail，并断言来源片段无空洞、无重叠、完全覆盖。自测仅用合成数据（24 项 OK），不是 D1 证据。**未**下载 Parquet、未拟合 Tokenizer、未做 D1 数据实验、未训练、未用 GPU；数据获取与 Tokenizer 拟合脚本尚未编写。

**状态：`D1 CODE FREEZE CANDIDATE / PENDING CHATGPT CODE REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。

## D1 代码冻结候选勘误 C1（2026-10-26）

审核基准 `090b6191f7558a43462691bb4fa9afa4b56fed9b`（ChatGPT：`CODE FREEZE CANDIDATE FAIL`，仅针对代码完整性，不否定合成自测，不代表 D1 真实实验失败）。新增 `docs/F3B_D1_CODE_FREEZE_C1_ERRATA_20261026.md`，并修订 `gate3_d1/`：`verify_cr` 对故障与 control trace 重算块哈希/链/总数/位置/EOF tail 元数据，并与独立构造的预期单变异流及整窗口来源顺序全量比对；`verify_clean` 独立重算 P1–P5；新增回归测试（37 项合成自测 OK，旧验证器上 6 项失败）；身份标签区分合成/real/正式候选；Python 完整补丁版本固定（候选值，执行主机 NOT VERIFIED）；30 分钟硬超时判 BLOCKED 且不重试；R6/R7/T1–T6 与数据获取完整性标 NOT TESTED，流水线不输出总体 D1 PASS。仅 CPU 合成数据；未下载、未拟合、未训练、无 GPU。

**状态：`D1 CODE FREEZE CANDIDATE C1 / PENDING CHATGPT RE-REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。

## D1 代码冻结候选勘误 C2（2026-10-26）

基准 `3775dc333577094d30297d3e28f9aa8d5d40039c`（ChatGPT 已静态认可 C1 的四项核心修复）。新增 `docs/F3B_D1_CODE_FREEZE_C2_ERRATA_20261026.md`，最小门禁修订三项：（1）驱动器把读取器退出码 4 映射为 BLOCKED（不再报 FAIL），驱动器退出码 PASS 0 / FAIL 1 / BLOCKED 4，clean 非 PASS 时 negatives 记 NOT TESTED；（2）30 分钟上限为代码常量，real 模式禁止 `--timeout-seconds` 覆盖且拒绝放宽后的配置，selftest 只能缩短；（3）验证器异常退出、结果文件缺失/畸形/与退出码不符、驱动器自身异常均被记录为 FAIL 或 BLOCKED。每项有合成回归测试，并在 C1 代码上证明差异（11/12 失败）。全量自测 49 项 OK。只读环境盘点见 `gate3_d1/c2_logs/env_inventory.txt`（仅沙箱；执行主机 NOT VERIFIED；候选版本未改）。

**状态：`D1 CODE FREEZE CANDIDATE C2 / PENDING CHATGPT FINAL CODE REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。

## D1 代码冻结候选微型勘误 C2a（2026-10-26）

基准 `f28f32b6d1514f15ccf680f752f5c414322cab51`。新增 `docs/F3B_D1_CODE_FREEZE_C2A_ERRATA_20261026.md`：（1）`verifier_verdict()` 只在「退出码 4 且结果文件不存在」时记 BLOCKED，文件存在但畸形/未知 verdict/退出码不符均 FAIL；（2）聚合采用 FAIL 优先于 BLOCKED，保留每项明细与 `counts`。4 项相关测试在 C2 代码上失败；全量 52 项合成自测 OK。读取器、验证器、冻结配置未改。

**状态：`D1 CODE FREEZE CANDIDATE C2a / PENDING CHATGPT FINAL CODE REVIEW`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`。

## D1 代码冻结候选 C2b（2026-10-26）

基准 `796cc6138caaedf8a45d9abd12554ef62235e77d`。新增 `docs/F3B_D1_CODE_FREEZE_C2B_ERRATA_20261026.md`，仅修两个边界问题（只改 `d1_driver.py` 与测试）：（1）CR 的故障/对照两个读取器结果用 `aggregate()` 合并，FAIL > BLOCKED > PASS，保留各读取器退出码与状态；（2）`verifier_verdict()` 对非字符串 `verdict`（列表/字典/null/数字/布尔）返回 FAIL，不抛 `TypeError`。新增测试在 C2a 基准上失败；全量 56 项合成回归 OK。读取器、验证器、冻结配置未改。

**状态：`D1 CODE FREEZE CANDIDATE C2b / PENDING CHATGPT FINAL ACCEPTANCE`**。D1 `NOT TESTED / NOT AUTHORIZED`；D2/D3 `NOT TESTED`；执行主机环境 `BLOCKED`。

## D1 代码冻结验收归档（2026-10-26）

已验收提交 `0197c21ca38130e66d804961b85a15ee39634b26`：ChatGPT Work 独立 C2b 代码冻结验收 **PASS**（据项目负责人转述；证据为 56 项 CPU 合成测试的日志核验，**未在独立环境重新执行**；Work 原文不在仓库）。新增 `docs/F3B_D1_CODE_FREEZE_ACCEPTANCE_ARCHIVE_20261026.md`（已验收文件的 blob/SHA-256、未完成状态、环境确认任务）。D1 真实实验 `NOT TESTED / NOT AUTHORIZED`；R6 读取前部分、R7、T1–T6、数据获取完整性 `NOT TESTED`；获取与 Tokenizer 拟合脚本未编写；配置 `status` 仍为 `FROZEN_CANDIDATE…`（执行前冻结提交待授权）。指定 Codespaces CPU 环境无法从本会话访问：**执行环境核查 BLOCKED**，Claude 沙箱不得当作执行环境，候选版本未改。

**状态：`D1 CODE FREEZE ACCEPTED (C2b) / D1 REAL EXPERIMENT NOT TESTED, NOT AUTHORIZED / EXECUTION ENVIRONMENT BLOCKED`**。

## D1 环境适配归档与冻结前整理（2026-10-26）

代码冻结验收提交 `0197c21c`（ChatGPT Work 独立 C2b 验收 PASS）；环境适配候选提交 `2c5986a89b023ff50acb6da6e1b4d068b515ca53`（分支 `d1-codespaces-py3138-validation-20261026`，把 Python 候选版本由 3.13.16 适配为 Codespaces 的 3.13.8；tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0 不变）。ChatGPT 审核与交叉审核均 PASS（限定于配置差异、SHA-256 与合成回归层面，无实质性阻断问题）。Codespaces Python 3.13.8 上 56 项 CPU 合成回归 **56 PASS、0 SKIP、0 FAIL**，含合成 real-mode 代码路径（原始日志 `gate3_d1/codespaces_env_logs/selftest_py3138.txt` 原样保留）。本次整理：更新 `D1_ENV_FREEZE.md` 的版本与状态表述（未改算法、参数、30 分钟限制、数据规则）、重新生成 `D1_CODE_SHA256SUMS`、新增原生环境证据采集命令。**原生环境快照（解释器路径、pip freeze、pip check、CPU/OS、Git 状态）未归档：BLOCKED，待项目负责人在 Codespaces 回传**。R6 读取前部分、R7、T1–T6、数据获取完整性 `NOT TESTED`；真实 D1 `NOT TESTED / NOT AUTHORIZED`；配置 `status` 仍为 `FROZEN_CANDIDATE__…`，**未**设为 `FROZEN`。

**下一条唯一指令**：最终配置冻结审核（ChatGPT 审核本检查点后，由项目负责人决定是否授权正式冻结）。

## D1 Codespaces 原生环境证据验收归档（2026-10-26）

证据提交 `852f30e13ab108311b160c9d1b55c3823dfa9b51`（前一检查点 `ef6b51a5`）。`gate3_d1/codespaces_env_logs/native_env_evidence_py3138.txt`（SHA-256 `e4e05c650e23a4a14b3327ca668d439871ad073747c66c752726d802166ccf1c`，本会话独立重算一致）经完整读取与逐项核对 **PASS**：Codespaces Python 3.13.8（venv `/workspaces/.venvs/openmythos-d1-py3138`）、tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0、`pip check` 退出码 0、Linux x86_64 / 2 CPU、采集时 Git HEAD `ef6b51a` 且工作区干净、冻结清单 10/10 OK（本会话在 `852f30e` 上独立复核同样 10/10）。详见 `docs/F3B_D1_NATIVE_ENV_ACCEPTANCE_20261026.md`。正式状态：D1 CODE FREEZE PASS；Codespaces 合成回归 56/56 PASS；原生环境证据 PASS；**最终配置冻结 NOT AUTHORIZED（`status` 仍为 `FROZEN_CANDIDATE__…`）**；真实 D1 NOT TESTED / NOT AUTHORIZED；R6 剩余部分、R7、T1–T6、数据获取完整性 NOT TESTED；D2/D3 NOT TESTED。

**下一条唯一指令**：等待项目负责人批准最终配置冻结提交。

## D1 最终配置冻结（2026-10-26）

项目负责人授权 `APPROVED — Final Configuration Freeze Only`。冻结前 Git SHA `ebb45680f7391c3fac975b7cdbf29d1a7a94ed67`，冻结分支 `d1-final-config-freeze-20261026`。`gate3_d1/D1_FROZEN_CONFIG.json` 的 `status` 由 `FROZEN_CANDIDATE__PENDING_ENV_ADAPTATION_REVIEW` 改为 **`FROZEN`**（另同步 `python_full_version_status` 说明文字）；结构化比较确认实验参数、数据规则、负例规则、30 分钟限制、Python 3.13.8 与三项依赖固定版本、`authorization` 段均未变。`D1_CODE_SHA256SUMS` 重新生成，10/10 OK；读取器/验证器/驱动器/测试源码/历史证据无 diff。**已知限制：** `tests/test_d1_selftest.py::test_identity_labels` 中有一条冻结前哨兵断言（`status != "FROZEN"`），冻结后必然失败；因授权禁止改测试而未改，等待决定（见 `docs/F3B_D1_FINAL_CONFIG_FREEZE_20261026.md` 第 6 节）。真实 D1 `NOT TESTED / NOT AUTHORIZED`；R6 剩余部分、R7、T1–T6、数据获取 `NOT TESTED`；D2/D3 `NOT TESTED`。

**状态：`D1 FINAL CONFIG FROZEN / PENDING CHATGPT INDEPENDENT ACCEPTANCE`**。下一条唯一指令：等待 ChatGPT 独立验收最终冻结提交。

## D1 冻结后哨兵测试修正（2026-10-26）

冻结提交 `9e257788c0510d5e263d5256d4bd3cebebdb8057` 保持不变；修复分支 `d1-final-freeze-sentinel-fix-20261026`。ChatGPT 裁决：批准限定范围的测试与状态文档修正，不批准算法变更。`tests/test_d1_selftest.py::test_identity_labels` 的冻结前哨兵断言 `status != "FROZEN"` 改为 `== "FROZEN"`（一行）；`D1_ENV_FREEZE.md` 的过期状态描述与当前事实同步；`D1_CODE_SHA256SUMS` 只有这两个文件的行变化，配置哈希 `0d35dc21…` 不变，10/10 OK。沙箱（Python 3.13.16）：精确测试 PASS；56 项 `OK (skipped=1)`（real-mode 版本门禁，设计如此）。**Codespaces（3.13.8）最终回归尚未执行：PENDING CODESPACES VALIDATION，不宣布 56/56 PASS。** 真实 D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。详见 `docs/F3B_D1_FREEZE_SENTINEL_FIX_20261026.md`。

**下一条唯一指令**：等待项目负责人回传 Codespaces CPU 合成回归结果，交 ChatGPT 与 Grok 交叉审核最终最小差异。

## D1 冻结后 CPU 回归证据归档与 Closeout（2026-10-26）

日志提交 `1298619e163af6257d206134e5ed031e0082947f`（修复基准 `6b57087c595ce795333c6636dceb32ff5b61fef3`，分支 `d1-final-freeze-sentinel-fix-20261026`）。Codespaces Python 3.13.8 冻结后 CPU 合成回归日志 `gate3_d1/sentinel_fix_logs/codespaces_regression_py3138.txt`（SHA-256 `be1bff0493a4da59c71b962188ac1bc3a5766b6caa26a419ea23a0ceae6fac1e`，本会话重算一致）经完整读取核对：**56 PASS、0 SKIP、0 FAIL、0 ERROR，50.656 s，退出码 0**，56 个测试名与源码一一对应，`test_identity_labels`、`test_real_mode_pipeline` 均 ok（合成，非真实 D1）。冻结清单 10/10 OK、配置哈希 `0d35dc21…` 与 `status = FROZEN` 不变，Reader/Verifier/Driver/配置相对冻结提交 `9e257788` 无 diff，测试文件仅哨兵断言一行。验收：D1 代码冻结 PASS；最终配置 FROZEN PASS；Codespaces 原生环境 PASS；56 项冻结后回归 PASS；代码变更范围 PASS；**Grok 对最终哨兵修复差异的交叉审核 PENDING**；真实 D1 NOT TESTED / NOT AUTHORIZED；R6 剩余、R7、T1–T6、数据获取 NOT TESTED；D2/D3 NOT TESTED。详见 `docs/F3B_D1_FINAL_REGRESSION_CLOSEOUT_20261026.md`。

**状态：`READY FOR CLOSEOUT / CROSS-REVIEW PENDING`**。下一条唯一指令：取得 Grok 交叉审核后标记配置与环境准备范围 CLOSED。

## D1 真实执行前规范 R3 草案（2026-10-26）

基准 `97d0faf2982f4122941d2299a23cab6ab2ba04a3`，分支 `d1-pre-real-spec-r3-20261026`。新增 `docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 与检查点 `docs/F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`：逐条引用 v1/R1/R2 原文（24/24 片段逐字核对），列出冲突与缺口 S1–S10（S1：下载后对三个文件算哈希 vs validation/test 未被打开；S2：T7 扫描 val/test vs R6/T1；另有 R6 粒度、R7 Token 计数、中断行为、T1 事件日志、30 分钟预算等），给出分阶段处理规范（元数据/下载/哈希/解析/读文本五级）、R6/R7/T1–T7 验收矩阵、单向哈希引用的清单、`FORMAL_D1_CANDIDATE` 不是 D1 PASS 及不改冻结 Driver 的独立验收方案，以及 11 项待裁决事项（R3-D01…D11，全部 PROPOSED / NOT APPROVED）。冻结文件、v1/R1/R2 未改动；未下载、未拟合、未运行 D1、无 GPU。

**状态：`DRAFT / PENDING CHATGPT REVIEW`**（不是 FROZEN，不是 PASS）。下一条唯一指令：等待 ChatGPT 复审并由项目负责人裁决。

## D1 真实执行前规范 R3 修订稿（2026-10-26）

修订基准 `94601916bc1fd0faa33b9f819b3a0d8cc7d61dc5`，分支 `d1-pre-real-spec-r3-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 已按 F3B-D1-SPEC-R3-REVIEW-002 原地修订（新增第 11、12 节），检查点追加到 `docs/F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。仅文档。**状态：R3 DRAFT / PENDING OWNER DECISION（不是 FROZEN、不是 PASS）**；11 项裁决（R3-D01…D11）为待项目负责人批准的决策记录。冻结文件与 v1/R1/R2 未改；真实 D1 NOT TESTED / NOT AUTHORIZED。下一条唯一指令：等待 ChatGPT 审核 R3 修订稿及项目负责人正式批准。

## D1 真实执行前规范 R3 第三轮修订（2026-10-26）

修订基准 `eeea55269df485d3e6305a82a3c478ef141a2788`，分支 `d1-pre-real-spec-r3-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 已按 F3B-D1-SPEC-R3-REVIEW-003 原地修订（新增 2.4 事件注册表、第 5 节正式边列表、11.8 摘要格式边界、第 14 节修订 3 记录），检查点追加到 `docs/F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。仅文档。**状态：R3 DRAFT / PENDING OWNER DECISION**；R3-D01…D11 为待项目负责人批准的决策记录。冻结文件与 v1/R1/R2 未改；真实 D1 NOT TESTED / NOT AUTHORIZED。下一条唯一指令：等待 ChatGPT 对第三轮 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 真实执行前规范 R3 第四轮收口（2026-10-26）

修订基准 `ca40fb74d8fea2c17a1a5116ba8939b17ce2e847`，分支 `d1-pre-real-spec-r3-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 已按 F3B-D1-SPEC-R3-CLOSURE-004 原地收口（2.4 状态词枚举与 R7.7 序列、新增 11.9 异常终止的收尾与证据归档、4.1 R6.6 独立验收、新增第 16 节），检查点追加到 `docs/F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。仅文档。**状态：R3 DRAFT / PENDING OWNER DECISION**；R3-D01…D11 为待项目负责人批准的决策记录。冻结文件与 v1/R1/R2 未改；真实 D1 NOT TESTED / NOT AUTHORIZED。下一条唯一指令：等待 ChatGPT 对第四轮（收口）R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 真实执行前规范 R3 最终一致性修复（2026-10-26）

修订基准 `2ad41913ed08598f1aecfad2575a4f3a6bf51c90`，分支 `d1-pre-real-spec-r3-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 已按 F3B-D1-SPEC-R3-FINAL-005 原地修复（F1a / F1b / F1c、后验模式例外、选项 Y 失败路径、新增第 18 节），检查点追加到 `docs/F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。仅文档。**状态：R3 DRAFT / PENDING OWNER DECISION**；R3-D01…D11 为待项目负责人批准的决策记录。冻结文件与 v1/R1/R2 未改；真实 D1 NOT TESTED / NOT AUTHORIZED。下一条唯一指令：等待 ChatGPT 对最终一致性修复（FINAL-005）后的 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 R3 负责人决策与已批准候选规范（2026-10-26）

分支 `d1-r3-approved-candidate-20261026`，源基准 `4c1d29d9e01c6df2d3b5e796181f728cc3cb88ed`。新增 `docs/F3B_D1_R3_OWNER_DECISION_20261026.md`（R3-D01…D11，`OWNER APPROVED — 2026-10-26`，D07 方案 X）、`docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`（已批准候选规范）、`docs/F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`（SHA-256 登记）。原草案 `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md` 与历史检查点原样保留。**状态：OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION；不是 R3 FROZEN、不是运行授权。**下一条唯一指令：等待 ChatGPT 独立核对正式 R3 候选规范和批准记录。

## D1 R3 最终勘误（2026-10-26）

分支 `d1-r3-approved-candidate-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md` 按 F3B-D1-R3-FINAL-ERRATA-001 做了两处文档勘误（终止原因与预算结果对照；`reap_done` 终止时间字段 Schema）；勘误后 SHA-256 登记在 `docs/F3B_D1_R3_FINAL_ERRATA_CHECKPOINT_20261026.md`。负责人决策记录与原草案字节不变。**状态：R3 APPROVED CANDIDATE / ERRATA SELF-CHECK PASS / PENDING CHATGPT FINAL VERIFICATION；不是 R3 FROZEN、不是运行授权。**下一条唯一指令：等待 ChatGPT 复核这两处勘误。

## D1 R3 边界勘误（2026-10-26）

分支 `d1-r3-approved-candidate-20261026`。`docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md` 按 F3B-D1-R3-ERRATA-EDGE-002 做了三个边界规则的文档勘误（终止宽限与升级、回收耗时与升级分离、预算不可证明与已存在 FAIL 的优先级）；勘误后 SHA-256 登记在 `docs/F3B_D1_R3_ERRATA_EDGE_CHECKPOINT_20261026.md`。负责人决策记录与原草案字节不变。**状态：R3 APPROVED CANDIDATE / EDGE ERRATA SELF-CHECK / PENDING CHATGPT FINAL VERIFICATION；不是 R3 FROZEN、不是运行授权。**下一条唯一指令：等待 ChatGPT 对边界勘误作最终确认。

## D1 R3 规范冻结（2026-10-26）

分支 `d1-r3-spec-freeze-20261026`，Git 基准 `79273d127548e2462026c2ae000dc2499798f5bd`。新增 `docs/F3B_D1_R3_SPEC_FREEZE_RECORD_20261026.md` 与 `docs/F3B_D1_R3_SPEC_FREEZE_CHECKPOINT_20261026.md`；冻结对象为 `docs/F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`（SHA-256 `66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5`）与 `docs/F3B_D1_R3_OWNER_DECISION_20261026.md`（SHA-256 `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319`），不得再编辑。**正式状态：R3 SPEC FROZEN / IMPLEMENTATION NOT TESTED / REAL D1 NOT AUTHORIZED。**下一条唯一指令：等待单独授权后，启动第一个合成数据 CPU 正确性实验。

## D1 G1/G2 CPU 实验（2026-10-27）

分支 `d1-r3-g1g2-cpu-probe-20261027`，基准 `39c55ca2cfa6d0587807be2af524d67479e76251`。新增 `research/mini_mythos/r3_cpu_probes/g1g2/`（探针 `g1g2_probe.py`、测试 `test_g1g2_probe.py`、`results/`）、`docs/F3B_D1_G1G2_CPU_001_REPORT_20261027.md`、`docs/F3B_D1_G1G2_CPU_001_CHECKPOINT_20261027.md`。结论：工具 PASS，R3 存活判定 G1 / G2 规则 FAIL；冻结 R3 未改。下一条唯一指令：等待 ChatGPT 对 G1/G2 CPU 实验结果进行独立审核。

## D1 G1/G2 审核后处理（2026-10-27）

分支 `d1-r3-a-revision-proposal-20261027`，基准 `af7b39abd17c64df1e08165cd2904a4a68cb1bed`。新增 `docs/F3B_D1_R3_A_PREDICATE_REVISION_PROPOSAL_DRAFT_20261027.md`、`docs/F3B_D1_R3_A_PREDICATE_CPU_TEST_PLAN_DRAFT_20261027.md`、`docs/F3B_D1_G1G2_REVIEW_001_CHECKPOINT_20261027.md`。仅文档草稿；冻结 R3 未改；G1/G2 FAIL 证据保留。下一条唯一指令：等待项目负责人批准修订方向及后续最小 CPU 实验。

## D1 A 判定提案修订（2026-10-27）

分支 `d1-r3-a-revision-proposal-20261027`，基准 `cc474f56ae77882fa77cfe4e7deb0e6b5d4305e8`。修订 `docs/F3B_D1_R3_A_PREDICATE_REVISION_PROPOSAL_DRAFT_20261027.md` 与 `docs/F3B_D1_R3_A_PREDICATE_CPU_TEST_PLAN_DRAFT_20261027.md`（RV-01…RV-04：三态 UNKNOWN、跨会话后代归属、TOCTOU/pidfd、子收割者维度拆分），新增检查点 `docs/F3B_D1_A_PREDICATE_PROPOSAL_REVIEW_002_CHECKPOINT_20261027.md`。仅文档，用例均 NOT TESTED；方案选择 PENDING；Grok DEFERRED。

## D1 R3-A CPU 受控对照实验（2026-10-27）

分支 `d1-r3-a-cpu-validation-20261027`。新增 `research/mini_mythos/r3_cpu_probes/a_predicate/`（`a_lab.py`、`a_cases.py`、`a_node.py`、`a_merge.py`、`run_all.sh`、`test_a_lab.py`、`results/`：1860 条原始记录 gz、派生统计、单元测试输出、第 1 轮与开发记录）与 `docs/F3B_D1_A_CPU_001_REPORT_20261027.md`、`docs/F3B_D1_A_CPU_001_CHECKPOINT_20261027.md`。CA、CB 在授权矩阵上均 PASS、无明确优劣；冻结 R3 未改；ChatGPT PENDING；Grok DEFERRED。

## D1 CPU-002 最小争议实验（2026-10-27）

分支 `d1-r3-a-cpu-002-minimal-dispute-20261027`。新增 `research/mini_mythos/r3_cpu_probes/a_predicate_002/`（`e2_lab.py`、`e2_cases.py`、`e2_merge.py`、`run_all.sh`、`test_e2_lab.py`、`results/`：430 条原始记录 gz、派生统计、单元测试输出、开发记录）与 `docs/F3B_D1_A_CPU_002_PLAN_20261027.md`、`..._REPORT_...`、`..._CHECKPOINT_...`。CPU-001 原始记录位于 `r3_cpu_probes/a_predicate/results/`（只读）。无明确 A/B 优劣；ChatGPT PENDING；GROK DEFERRED。

## D1 CPU-003 安全监督器设计（2026-10-27）

分支 `d1-r3-a-cpu-003-design-20261027`（基线 `6bd8c53`）。新增 `docs/F3B_D1_A_CPU_003_DESIGN_PLAN_20261027.md`、`..._ARCHITECTURE_OPTIONS_...`、`..._CHECKPOINT_...`（仅文档；实验均 NOT TESTED）。CPU-001 / CPU-002 原始记录位置不变（见各自检查点）。

## D1 CPU-003 设计勘误（2026-10-27）

分支 `d1-r3-a-cpu-003-design-20261027`。新增 `docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md`；就地修订 CPU-003 设计计划与架构候选文档；追加 CPU-003 检查点的勘误后状态。仅文档；实验均 NOT TESTED；Grok 状态：已完成（负责人提供概括，原始报告未入库）。

## D1 CPU-003 设计勘误-002（2026-10-27）

分支 `d1-r3-a-cpu-003-design-20261027`。新增 `docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_002_20261027.md`；带标记地最小修订 ERRATA-001、设计计划与架构候选文档；追加检查点第 12、13 节。仅文档；实验均 NOT TESTED。

## D1 CPU-003 E1-A 预注册与台架（2026-10-27）

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`（基线 `6a089f5`）。新增 `research/mini_mythos/a_predicate_003/`：预注册 `prereg/e1_provability_table_v1.json`（先于台架单独提交：`b2aec0f`，更正 `c02f201`、`f9d3cd8`；最终 SHA-256 `e6b7ca5c88de81df…`）、台架 `bench/`（GATED-SPAWN 观察者 / 门 / janitor / 监督器桩 / 候选 P0-P1-P2 / 独立真值）、测试 `tests/`（已编写、未运行）、工具 `tools/`、`STATIC_REVIEW.md`、`run_e1a.sh`（未运行）；新增检查点 `docs/F3B_D1_A_CPU_003_E1A_PREP_CHECKPOINT_20261027.md`。E1-A 仍 EXPERIMENT NOT TESTED；E1-B/C/D 未冻结；运行器需负责人单独授权文件才可 `--execute`。

## D1 CPU-003 E1-A 静态审核修复（2026-10-27）

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。F3B-D1-A-CPU-003-E1A-STATIC-FIX-001：只修台架（`a_predicate_003/bench`、`tests`），预注册未改（SHA-256 `e6b7ca5c…`）。四项：unsafe 事件优先于台架 BLOCKED 且候选异常不记台架 BLOCKED；清理责任自 fork 起、仅由确认死亡解除；`RUN_END.cleanup_confirmed` 与 janitor 退出条件；BV 与单元测试分阶段授权。新增检查点 `docs/F3B_D1_A_CPU_003_E1A_STATIC_FIX_CHECKPOINT_20261027.md`。测试只写未跑，E1-A 仍 EXPERIMENT NOT TESTED。

## D1 CPU-003 E1-A 最终执行边界修复（2026-10-27）

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。F3B-D1-A-CPU-003-E1A-STATIC-FIX-002：只修台架（`a_predicate_003/bench`、`tests`），预注册未改（SHA-256 `e6b7ca5c…`）。三项：最终清理集合一致性（入口关闭、不动点清理、RUN_END 前核对运行集合、janitor 责任未解除不得强杀）；登记文件完整性（缺失 / 损坏 / 撕裂 / 序号缺口 ⇒ janitor 不得退出 0，且无法识别的进程不发信号）；BV 证据来源（负责人签发的 `bv_binding` + 原始记录重新推导，否则 SMOKE）。新增检查点 `docs/F3B_D1_A_CPU_003_E1A_STATIC_FIX2_CHECKPOINT_20261027.md`。测试只写未跑，E1-A 仍 EXPERIMENT NOT TESTED。

## D1 CPU-003 E1-A 静态审核最终收口（2026-10-27）

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`。F3B-D1-A-CPU-003-E1A-STATIC-CLOSEOUT-001：只修两处台架问题——撤销票据的未确认创建责任（门管道 EPIPE 证明，不猜 pid）与登记文件的运行生命周期约束；预注册未改（SHA-256 `e6b7ca5c…`）。新增检查点 `docs/F3B_D1_A_CPU_003_E1A_STATIC_CLOSEOUT_CHECKPOINT_20261027.md`。测试只写未跑，E1-A 仍 EXPERIMENT NOT TESTED。

## D1 CPU-003 E1-A 纯逻辑测试 LOGIC-TEST-001（2026-10-27）

分支 `d1-r3-a-cpu-003-e1a-prep-20261027`（基线 `fcb6de8`）。按授权只运行五个纯逻辑 / Mock 测试文件；第 1 个文件被本轮新增的执行守卫的 argv 缺陷阻断（未执行任何测试断言），按规则暂停、未修复。证据在 `a_predicate_003/logic_test_results/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_LOGIC_TEST_CHECKPOINT_20261027.md`。台架 / 测试 / 预注册未改；进程级测试未授权。

## D1 CPU-003 E1-A 纯逻辑测试重新执行（2026-10-27）

LOGIC-TEST-001-RERUN-001：修复执行守卫的 argv 缺陷（+1 行）后，五个纯逻辑 / Mock 测试文件共 172 个测试全部通过（0 失败 / 0 错误 / 0 跳过，守卫越界调用 0）。证据 `a_predicate_003/logic_test_results_rerun1/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_LOGIC_TEST_RERUN_CHECKPOINT_20261027.md`。台架 / 测试 / 预注册未改；进程级测试、BV、E1-A 仍未授权。

## D1 CPU-003 E1-A 真实进程门控验证准备 GATE-PREP-001（2026-10-27）

基线 `a7ce70f`。仅准备，未执行：先冻结 G0 判据与预注册文本（`e287b95`），再写独立 G0 入口 / 单次授权互锁 / 纯判定函数 / 纯逻辑测试（未运行）/ 安全评审（`a_predicate_003/gate_g0/`），并给静态审计加 `--dir gate_g0` 严格配置（台架审计 0 违规，G0 目录 0 违规）。没有进程、信号、进程级测试、BV、E1-A 单元；没有有效的 G0 授权文件；台架 / 预注册 / R3 / CPU-001/002 / Parcae 未改。检查点 `docs/F3B_D1_A_CPU_003_E1A_GATE_PREP_CHECKPOINT_20261027.md`。下一步：提交 ChatGPT 独立审核，等待负责人另行批准第一次受控 G0 运行。

## D1 CPU-003 E1-A G0 执行前审核 G0-PREFLIGHT-001（2026-10-27）

基线 `d8a0728`（ChatGPT：G0 PREPARATION CONDITIONAL PASS）。仅分析，未执行：纯逻辑测试执行路径静态审计（46 个测试，0 个进程相关调用，`run()` 受三层保护）、`g0_run.py` 阻塞路径分析（发现 `waitpid` 无超时 F-8、无运行期总预算 F-9）、六项预注册偏差处置（5 项 ACCEPTABLE，第 6 项 REQUIRES V2，无 BLOCKED）。冻结 V1、台架、G0 实现未改；没有运行任何测试或进程。检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_PREFLIGHT_CHECKPOINT_20261027.md`，分析 `a_predicate_003/g0_preflight_review/G0_PREFLIGHT_REVIEW.md`。下一步：ChatGPT 复核，等待负责人批准下一阶段。

## D1 CPU-003 E1-A G0 V2 判据冻结 G0-V2-SPEC-001（2026-10-27）

基线 `e0ffef9`。新增并冻结 `gate_g0/g0_criteria_v2.json` + `E1A_GATE_G0_PREREG_V2.md`（V2 冻结提交 `77750c3`，只含这三个文件；V1 文件、哈希、提交不变且不被重新解释）。C03 明确两种情形：有证据证明登记顺序 / 完整性违规 ⇒ FAIL，因超时或提前中止证据不足 ⇒ UNEVALUABLE → BLOCKED；检查编号 C01–C17 不变（8 IDENTICAL / 8 CLARIFIED / 1 MODIFIED），六项文字偏差正式处理。登记 F-13（`evidence/` 父目录无人创建）并给出 F-8/F-9/F-12/F-13/C03 的文件级修复设计，均未实现。G0 实现、台架、E1-A 预注册、R3、CPU-001/002、Parcae 未改；没有运行任何测试或进程。检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V2_SPEC_CHECKPOINT_20261027.md`。下一步：交 ChatGPT / Grok 交叉审核，待负责人授权实施。

## D1 CPU-003 E1-A G0 V2 语义收口审核 G0-V2-SEMANTIC-REVIEW-001（2026-10-27）

基线 `f679995`。仅源码与规则审计：C03 的 F1–F4 不覆盖 `integrity_issues()` 的全部违规（重复 FORKED / REGISTERED / RELEASED 与字段格式错误无规则；缺失类规则把台架写失败 / 证据损坏误判为 FAIL）；F-15 内存记录数无规则；C16 新增证据可使旧 PASS 变 BLOCKED（被 V2 §10 挡住）。分类：多项 SEMANTIC CHANGE REQUIRES V3，其余 DOCUMENTATION ONLY / NO ISSUE；建议先决定是否出 V3 再授权实施。23 个反例矩阵（源码推导，未执行）。V1/V2 冻结文件、台架、G0 实现未改；没有运行任何测试或进程。检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V2_SEMANTIC_REVIEW_CHECKPOINT_20261027.md`，报告 `a_predicate_003/g0_preflight_review/G0_V2_SEMANTIC_REVIEW.md`。下一步：ChatGPT / Grok 交叉审核，待负责人决定是否出 V3。

## D1 CPU-003 E1-A G0 V3 最小语义修订 G0-V3-SPEC-001（2026-10-27）

基线 `ab66d18`。新增并冻结 `gate_g0/g0_criteria_v3.json` + `E1A_GATE_G0_PREREG_V3.md`（V3 冻结提交 `7c4b99c`，只含这三个文件；V1/V2 字节不变）。C01–C17 编号稳定：14 项与 V2 相同，3 项 MODIFIED（C03 见证模型：账本 + 独立证据判违规、持久副本只做保真，seq 空洞从不单独成为 FAIL；C07 放行证据 F-18：尝试 / 成功写入 / 通过门控三事实；C16 证据模式 91 个字段含类型与校验时机）。51 个静态反例（设计审核，非测试 PASS）。Grok 审核待定，不声称双 AI 共识；DD-1…DD-5 待裁决。实现、测试、授权均未动。检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V3_SPEC_CHECKPOINT_20261027.md`，报告 `a_predicate_003/g0_preflight_review/G0_V3_SPEC_REVIEW.md`。下一步：提交 ChatGPT / Grok 审核。

## D1 CPU-003 E1-A G0 V3 独立审核收口 G0-V3-REVIEW-CLOSEOUT-001（2026-10-27）

基线 `b4ca97d`（ChatGPT：V3 冻结提交与范围合规 PASS）。静态审计三个问题：F-20（`disk_faithful` 只比较三元组，C04 / C11 / C13 读持久副本的其余字段 ⇒ 案例 A 错误 PASS、案例 B 错误 FAIL）、F-21（`json.loads(json.dumps())` 不是读回文件；V3 文字三处互相排斥）、F-22（C03-F3 与 `precedence` 对追加失败互相矛盾）。结论：三项都需要 V4；给出一次性最小差异清单（完整记录保真、读 `reg` 的检查在不保真时 UNEVALUABLE、F3 需求表、P0–P7 写入—读回—校验—裁决—摘要流水线）。不创建 V4，等 Grok 与 DD-1…DD-5 裁决。V1/V2/V3、实现、台架、测试未改；没有运行任何测试或进程。检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V3_CLOSEOUT_CHECKPOINT_20261027.md`，报告 `a_predicate_003/g0_preflight_review/G0_V3_CLOSEOUT_REVIEW.md`。下一步：ChatGPT / Grok 审核。

## D1 CPU-003 E1-A G0 V4 最终规范 G0-V4-SPEC-001（2026-10-27）

基线 `279eaae`。新增并冻结 `gate_g0/g0_criteria_v4.json` + `E1A_GATE_G0_PREREG_V4.md`（V4 冻结提交 `753b460`，只含这三个文件；V1/V2/V3 字节不变）。C01–C17 编号稳定：10 项相同、7 项修改。F-20 整条记录保真 + M-2；F-21 证据流水线 P0–P7；F-22 条件规则表；DD-1…DD-5 登记为拟批准决策（DD-1/3/4 为 derived，待审核者确认）。67 个静态案例（含 51 个 V3 迁移，3 个裁决改变）与 15 个流水线案例；只读静态检查 0 不一致。未修改任何代码 / 测试 / 既有冻结文件；未运行任何测试或 G0。状态：G0 V4 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED。检查点：`research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G0_V4_SPEC_CHECKPOINT_20261027.md`。

## D1 CPU-003 E1-A G0 V5 最小结案修订 G0-V5-CLOSEOUT-SPEC-001（2026-10-27）

基线 `d127ec5`。新增并冻结 `gate_g0/g0_criteria_v5.json` + `E1A_GATE_G0_PREREG_V5.md`（V5 冻结提交 `8530ba5`，只含这三个文件；V1–V4 字节不变）。F-23：摘要文件存在不再等于结案；新增 `g0_closed.json`（临时文件 O_EXCL + fsync + 读回 + `os.link` 原子排他发布，目录 fsync，读回）；C01 对历史运行要求有效标记并绑定经哈希核对的摘要与证据，进程残留独立判定。C02–C17 与 DD-1…DD-5 不变（仅 C01 MODIFIED）。38 个闭环案例（A–H）、19 个 P6/P7 失败案例、7 个崩溃点；只读静态检查 0 不一致。未修改任何代码 / 测试 / 既有冻结文件；未运行任何测试或 G0。状态：G0 V5 SPEC FROZEN / IMPLEMENTATION NOT AUTHORIZED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED。检查点：`research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G0_V5_CLOSEOUT_SPEC_CHECKPOINT_20261027.md`。

## D1 CPU-003 E1-A G0 V5 工具实现 G0-V5-IMPLEMENTATION-001（2026-10-27）

基线 `13043b9`；独立实现分支 `d1-r3-a-cpu-003-e1a-g0-v5-impl-20261027`。授权范围仅为编码与静态审核：`g0_auth.py`（V5 绑定与冻结哈希表）、`g0_judge.py`（C01–C17、C03/C07/C16 规则、M-2、结案标记与 CL-01…CL-23 求值）、`g0_run.py`（F-8 有界回收、F-9 总预算、F-12/F-13 目录、F-18 放行写入记录、P0–P7 流水线、K0–K7 原子排他结案发布）已按冻结 V5 写完；184 个纯逻辑测试方法（67 + 38 + 19 + 15 案例与结构 / 守卫 / 预算 / 目录测试）已写但**未运行（NOT TESTED）**。静态审计：64 行需求对应表 0 未找到，AST 审计 0 违规，`bench/`、V1–V5、E1-A 预注册未变。未解决：B-1（消耗目录两句冻结文字）、B-2（CE-E1 案例标签）、B-3（真实环境行为）、B-4（测试未运行）。状态：G0 V5 IMPLEMENTATION COMPLETE (CODE WRITTEN) / STATIC AUDIT RECORDED / PURE TESTS NOT TESTED / REAL G0 NOT AUTHORIZED。检查点：`research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G0_V5_IMPLEMENTATION_CHECKPOINT_20261027.md`。

## D1 CPU-003 E1-A G0 V5 CPU 正确性测试 G0-V5-PURE-TEST-001（2026-10-27）

基线 `33fb344`；最终测试对象见检查点。在进程安全哨兵（fork / 信号 / 等待 / subprocess 全部替换为计数哨兵）之下运行 198 个 CPU 测试：198 / 198 PASS，两次运行一致，哨兵 0 次触发，变异检查 10 / 10 被发现。发现并最小修复 2 个实现缺陷：D-1（启动异常泄漏为退出码 1，现一律 3）、D-2（格式损坏的放行 / fork 记录曾产生错误 FAIL，现为见证不可用）；测试自身缺陷 T-0…T-3 已修正。V1–V5、bench、Parcae 未改。真实进程行为（pidfd、fork、/proc、run()）未被验证。状态：CPU TESTS PASS / REAL G0 NOT AUTHORIZED。报告：`research/mini_mythos/a_predicate_003/g0_v5_pure_test_results/G0_V5_PURE_TEST_REPORT.md`；检查点：`research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G0_V5_PURE_TEST_CHECKPOINT_20261027.md`。

## D1 CPU-003 E1-A G0 V5 CPU 测试最终收口（2026-10-27）

基线 `40f3f5b`，修复与被测 HEAD `a4a8509`。三处边界：① `g0_run.main` 解析参数后的任何 SystemExit 一律退出码 3（argparse 的 0/2 保留）；② 环境信息改为 `os.uname()` 只读方式，哨兵先于一切安装；③ 运行器从 `.git` 独立验证 HEAD 与预期 SHA、冻结文件与 bench 哈希，并记录 15 个关键文件哈希，不符即 REFUSED/退出码 3。全量 216/216 ×2 PASS，哨兵 0 命中，负控制（SystemExit(1)、错误 SHA、缺失 SHA）有效。结果见 `a_predicate_003/g0_v5_closeout_test_results/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V5_CLOSEOUT_CHECKPOINT_20261027.md`。状态：CPU TESTS PASS；REAL G0 NOT AUTHORIZED；等待 ChatGPT/Grok 验收。

## D1 CPU-003 E1-A G0 V5 首次真实执行 G0-V5-REAL-001（2026-10-27）

HEAD `0cf75c1`（代码与 CPU 验收提交 `a4a8509` 相同）。执行前检查全部通过后创建单次授权 `OWNER-G0-REAL-001-20261027`（仅本地，未提交，已消耗）并 `python3 -B g0_run.py --execute` 执行一次：退出码 0，C01–C17 全部 PASS，一次 fork（子进程 298）、零信号、按 pid 回收、状态 0，用时 0.431 s，结案标记已发布，独立复判 PASS，无残留。结论 **G0 REAL-001: PASS**；G1/G2/G3 / BV / E1-A 仍未授权。证据 `a_predicate_003/evidence/g0_20261027_144311_479c54/`，结果 `a_predicate_003/g0_v5_real_001_results/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_G0_V5_REAL_001_CHECKPOINT_20261027.md`。下一步：ChatGPT 与 Grok 审核真实证据。

## D1 CPU-003 E1-A G1 负向门控设计 G1-NEGATIVE-GATE-DESIGN-001（2026-10-27）

基线 `c3cf742`（G0 REAL-001 PASS）；分支 `d1-r3-a-cpu-003-e1a-g1-negative-gate-design-20261027`。仅设计：四个最小负向门控测试 ABORT / EOF / INVALID_BYTE / TIMEOUT（期望退出码 111/111/111/112，一子进程、一次 fork、零信号），逐测试的刺激、独立“未提前动作”证据、PID/starttime 身份、退出与 waitpid 回收证据、PASS/FAIL/BLOCKED 判据；独立入口 `gate_g1/g1_run.py`（不复用 SIGKILL 拆除的原 unittest，只读复用 G0 机制）；单次授权、首败即停、无信号、无按名称清理、结案沿用 P0–P7/K0–K7。设计 `a_predicate_003/gate_g1/E1A_GATE_G1_DESIGN.md`，检查点 `docs/F3B_D1_A_CPU_003_E1A_G1_NEGATIVE_GATE_DESIGN_CHECKPOINT_20261027.md`。状态：G1 DESIGN PREPARED / G1 REAL NOT TESTED / G1 EXECUTION NOT AUTHORIZED；等待 ChatGPT/Grok 审核。

## D1 CPU-003 E1-A G1 负向门控实现 G1-IMPLEMENTATION-001（2026-10-27）

基线 `48d241f`；分支 `d1-r3-a-cpu-003-e1a-g1-impl-20261027`。先以独立提交 `8385cd1` 冻结 G1 判据 V1（`gate_g1/g1_criteria_v1.json` `1992d75d…1257` + 预注册文本 `37487237…cd69`），再实现 `g1_auth.py` / `g1_judge.py` / `g1_run.py`（T1 ABORT / T2 EOF / T3 INVALID_BYTE / T4 TIMEOUT，17 项判据，只读复用 G0 设施，未改 G0 / Bench / Parcae / R3）；CPU 测试 222 个只写未跑（NOT TESTED）；静态审计 FINDINGS 0、追溯 36 行。状态：G1 IMPLEMENTATION COMPLETE / STATIC AUDIT RECORDED / CPU TESTS NOT TESTED / G1 REAL NOT AUTHORIZED。检查点 `docs/F3B_D1_A_CPU_003_E1A_G1_IMPLEMENTATION_CHECKPOINT_20261027.md`，审核报告 `a_predicate_003/g1_impl_static_audit/`。下一步：ChatGPT / Grok 审核，随后另行授权 CPU 测试。

## D1 CPU-003 E1-A G1 实现审核修复 REVIEW-FIX-001（2026-10-28）

审核基准 `453fe4e`，修复提交 `a5d9168`。三项实施层修复：① `run()` 异常路径检查本轮全部节点及 guard 的未回收子进程（不再用可能过期的 `S.rec`）；② CPU runner 验收：仅完整选择且全部 289 个预期测试 ID 各执行一次并 PASS（0 SKIP/FAIL/ERROR/加载错误/哨兵违规）才算 PASS，诊断分组最多 INCOMPLETE；③ 逐测试停止规则改为判定器自己的 C04–C15 检查（最小反例：pid 不一致但退出码正确时旧规则继续运行）。G1 V1 判据与预注册、G0、Bench、R3、Parcae 不变；测试只写未跑（NOT TESTED）；静态审计 FINDINGS 0、追溯 38 行。检查点 `docs/F3B_D1_A_CPU_003_E1A_G1_IMPLEMENTATION_REVIEW_FIX_001_CHECKPOINT_20261028.md`。状态：G1 IMPLEMENTATION COMPLETE / STATIC AUDIT RECORDED / CPU TESTS NOT TESTED / G1 REAL NOT AUTHORIZED。

## D1 CPU-003 E1-A G1 CPU 测试 G1-CPU-TEST-001（2026-10-28）

被测代码 `d175a1a`（证据提交另记于 `g1_cpu_test_results_001/EVIDENCE_COMMIT_RECORD.md`）。在进程安全哨兵下完整运行两次（无 `--groups`）：各 289 个唯一测试全部 PASS，0 FAIL / ERROR / SKIP / XFAIL / XPASS / 加载错误 / 哨兵违规，退出码 0，两次结果一致；独立脚本逐项核对。状态：G1 CPU TEST PASS；G1 REAL NOT AUTHORIZED（CPU 测试 PASS ≠ 真实 G1 PASS）。结果 `a_predicate_003/g1_cpu_test_results_001/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_G1_CPU_TEST_001_CHECKPOINT_20261028.md`。下一步：ChatGPT / Grok 审核，随后由负责人单独决定是否授权真实 G1。

## D1 CPU-003 E1-A G1 真实执行 G1-REAL-001（2026-10-28）

执行时 Git SHA `3eef8d7`（证据提交另记于 `g1_real_001_results/EVIDENCE_COMMIT_RECORD.md`）。项目负责人授权一次真实 CPU 执行：run_id `g1_20261028_025922_68ac93`，T1 ABORT / T2 EOF / T3 INVALID_BYTE / T4 TIMEOUT 依序各一次 fork，共 4 次，零信号、零残留；退出 111/111/111/112；17 项判据对四个测试全部 PASS，`g1_closed.json` 已发布并与 evidence / summary 哈希绑定；独立脚本逐项复核通过。授权文件与 `authorization_used.json` 不提交。G1 V1 判据、G0、Bench、R3、Parcae 与架构未改。状态：G1 REAL EXECUTED — CROSS-REVIEW PENDING（记录判定 PASS，待 ChatGPT / Grok 独立复核）；G2 / G3 / BV / E1-A 未授权。结果 `a_predicate_003/g1_real_001_results/`，检查点 `docs/F3B_D1_A_CPU_003_E1A_G1_REAL_001_CHECKPOINT_20261028.md`。

## D1 CPU-003 E1-A G1 最终交叉审核结案与 G2 身份/后代设计草案（2026-10-28）

基线 `450914367c247231c51be02e13775cb001e69c5d`（原 G1 实验与证据最终记录 HEAD），本次仅文档提交，另起分支 `d1-r3-a-cpu-003-e1a-g1-closeout-g2-design-20261028`。**G1-REAL-001 已由 ChatGPT 直接核验（归档 SHA-256 18/18、独立原始证据检查 60/60）与项目负责人提供的 Grok 独立审核结果共同确认：G1 REAL-001 CROSS-REVIEW PASS**；run_id `g1_20261028_025922_68ac93`，原始 G1 执行 checkpoint 和证据保持不变。正式结案记录：`docs/F3B_D1_A_CPU_003_E1A_G1_REAL_001_FINAL_CROSS_REVIEW_CHECKPOINT_20261028.md`（注明 Grok 原始报告未单独入库）。

**G2-DESIGN-001：仅设计草稿 / 源码审计记录 / ChatGPT 与 Grok 设计复核待进行。** 设计位于 `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md`，含 G2-D01…D07 候选身份、后代、跨会话、迟到 CREATED、旁观者、回收与不确定性用例，以及 G2-R01…R08 风险。核心未解决问题：**后代的合法 waitpid 回收者与独立真值机制未确定，不能执行真实 G2**。设计 checkpoint：`docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_CHECKPOINT_20261028.md`。明确区分 E1-A Gate G2 与此前归档 R3-A 存活谓词 G1/G2 FAIL；G2 判据未冻结，未实施、未运行 CPU/真实测试，G2/G3/BV/E1-A 均未授权；冻结 G0/G1、Bench、R3、Parcae 和模型架构未动。下一条唯一指令：交 ChatGPT 与 Grok 独立审核 G2 设计，解决回收所有权与身份/血缘独立真值分歧；未经负责人后续单独授权，不实施或执行。

## D1 CPU-003 E1-A G2 设计修订 G2-DESIGN-REVISION-001（2026-10-28）

基线 `8f9e8b2c027b3f6c0b738650b57af62d52dce141`（G2-DESIGN-001 审核结论 CHANGES REQUIRED，原始 F1–F9 保存于 `a_predicate_003/gate_g2/G2_DESIGN_REVIEW_001_FINDINGS.md`）。仅文档修订：`G2_IDENTITY_DESCENDANTS_DESIGN.md` 升为 V1（V0 原样归档为 `…_V0_8f9e8b2.md`），新增修订记录 `G2_DESIGN_REVISION_001_RECORD.md`。要点：声明 PID / 内核身份 / gate 持有证明 / 创建血缘分层，放行前后证据分类（READY 不能证明放行前验证）；同父错 PID、重复 PID、共享 gate fd 反例；EXIT_OBSERVED / ZOMBIE / REAP_CONFIRMED / PROC_GONE 四态分离；回收者方案 A（创建者回收）与 B（观察者 subreaper）均给出可验证设计，**未选择**；隔离 sidecar 证据；撤回“两次稳定扫描即证明无后代”的暗示，不可证实的完整性声明保持 UNKNOWN / BLOCKED；逐卡片 SUT / 独立真值 / 预防性与检测性要求；不调用原 SIGKILL 清理路径的安全退出与人工处置流程；进程预算、判据优先级 FAIL > BLOCKED > PASS、CPU-only 与 REAL 阶段边界、15 项未决选择 O-1…O-15。状态：**G2 DESIGN REVISION PREPARED — CROSS-REVIEW PENDING；G2 CRITERIA NOT FROZEN；G2 CPU / REAL NOT AUTHORIZED**。检查点 `docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_REVISION_001_CHECKPOINT_20261028.md`。下一步：ChatGPT 与 Grok 审核新版设计。

## D1 CPU-003 E1-A G2 V2 设计草案与 Grok 审核暂缓（2026-10-28）

**阶段：DESIGN V2 DRAFT PREPARED / REVIEW PENDING；G2 CRITERIA NOT FROZEN / IMPLEMENTATION-CPU-REAL NOT AUTHORIZED。** 从已核对 GitHub 远端提交 `ee7e9d46bc46b8dc15cc66ca06569d32a677561d`（V1）建立独立文档分支 `d1-r3-a-cpu-003-e1a-g2-v2-design-20261028`；原 Bench、Parcae、G0/G1 冻结源码和既有证据未授权修改。用户明确说明 Grok 额度受限，许可暂不等待 Grok 而**只推进文档修订**；Grok 对 G2 V1/V2 的状态是 **DEFERRED / NOT REVIEWED，不是 PASS**，不得把临时例外当作授权实施或执行。

主要入口：`a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V2.md`（当前设计 V2）；`a_predicate_003/gate_g2/G2_V1_REVIEW_AND_GROK_DEFER_RECORD.md`（ChatGPT 对 V1 的 R1–R5 发现与审核来源）；`docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_REVISION_002_CHECKPOINT_20261028.md`（本阶段 checkpoint）。V1 逐字节归档为 `G2_IDENTITY_DESCENDANTS_DESIGN_V1_ee7e9d4.md`，旧默认 `G2_IDENTITY_DESCENDANTS_DESIGN.md` 顶部指向 V2。V2 不把 gate 管道持有当作唯一创建血缘证明，不把创建者 WAIT_REPORT 当作独立回收证明，区分 CPU 夹具 subject BLOCKED 与 test PASS，并把不发信号的异常回收责任列为 REAL 阻断项。建议方案 A（合法创建者回收）仅为研究偏好；O-1…O-15 仍未冻结。

**下一条唯一指令：** 只读审核 V2 文档和新 checkpoint，记录反例/剩余设计阻断；未获后续负责人分阶段授权前，不冻结、不实现、不运行 CPU/REAL，不进入 G3/BV/E1-A。

## G2 V2 独立源码设计审核（2026-10-28；CHANGES REQUIRED）

来源：`d1-r3-a-cpu-003-e1a-g2-v2-design-20261028` @ `6c223ef2efa8830c1552d44e046b72063d87a637`，冻结 V2 设计 blob `e58fe0e0881beebcef2f3d8b0510b7e4175da1da`。本次 ChatGPT **只读复核真实源码、只对独立审核文档及导航做 Git 写入**，审核分支 `d1-r3-a-cpu-003-e1a-g2-v2-review-20261028`。

审核结论：**G2 V2 DESIGN CHANGES REQUIRED / REAL DESIGN PREREQUISITES BLOCKED / CRITERIA NOT FROZEN / G2 CPU & REAL NOT TESTED, NOT AUTHORIZED。** 发现与最小反例见 `a_predicate_003/gate_g2/G2_V2_INDEPENDENT_DESIGN_REVIEW_001.md`（V2-F01…F06，特别是 B0 `_on_created` 自动放行导致 D01 无放行前 gate 见证；创建者 wait 报告/可信插桩的证明等级；无信号异常清理与孤儿责任；sidecar 完整性；CPU subject 与 test 双层验收）。阶段 checkpoint：`docs/F3B_D1_A_CPU_003_E1A_G2_V2_INDEPENDENT_DESIGN_REVIEW_001_CHECKPOINT_20261028.md`。O-1…O-15 是 **ChatGPT 待审批建议、OWNER DECISION UNDECIDED**。Grok 受额度限制为 `DEFERRED / NOT PERFORMED`；用户的临时例外仅允许继续**文档工作**，不等于 Grok PASS。原生 Parcae、Bench、冻结 G0/G1、R3、测试、实验数据一律未授权改动。下一条唯一指令：仅提出 V2.1 最小文档修订后重新独立审核；不得冻判据、实现、CPU 运行、真实 fork、信号或进入 G3/BV/E1-A。

## G2 V2.1 最小文档修订（2026-10-28；仅准备，审核待完成）

只读源与审核基准：`d1-r3-a-cpu-003-e1a-g2-v2-review-20261028` @ `cf9a77b22af4487452e1ecf5add6fb284b0aa69e`。本轮另开文档分支 `d1-r3-a-cpu-003-e1a-g2-v21-doc-20261028`，按 V2 审核 F01–F06 编写 **G2 V2.1 最小设计差分**：`a_predicate_003/gate_g2/G2_DESIGN_V2_1_MINIMAL_DELTA_20261028.md`，阶段记录：`docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_V2_1_CHECKPOINT_20261028.md`。V2.1 区分 B0 原生 Observer 的事后检测与 P1 隔离驱动的拟议放行前检查；不将同管道 FD/PPID 视为唯一创建血缘；限定创建者 WAIT_REPORT 与可信 wait 调用记录的证明等级；孤儿、异常 EOF、未决回收明确 BLOCKED；sidecar 哈希链只证明归档内部一致性、不证明发送者或内核真值；CPU 夹具将被测判定与测试验收分离。14 个旧卡 ID，D01 分 B0/P1 后为 15 个候选 arm 项，均未冻结。

**G2 V2.1 DESIGN DELTA PREPARED / REVIEW PENDING；OWNER O-1…O-15 UNDECIDED；Grok DEFERRED（不是 PASS）；G2 CRITERIA NOT FROZEN；IMPLEMENTATION / CPU / REAL NOT TESTED / NOT AUTHORIZED；REAL 仍被合法回收与无信号异常责任阻断。** 无法用“默认许可”代替独立 Grok 的实际审查。G0/G1 已验收结果、原生 Parcae、Bench 与模型架构保持不变。**下一步唯一指令：只读审核 V2.1 文档是否足以成为后续 CPU-only 规格设计依据；不得自动冻结/实施/运行。**

## G2 V2.1 独立设计复核：限定为 CPU-only 规范草拟依据（2026-10-28）

来源：`d1-r3-a-cpu-003-e1a-g2-v21-doc-20261028` @ `870fb38c7beec33c090e743dd27fa4d3682b6700`；V2.1 设计 blob `c2ed7330e9f5e9f18ea6d9461d47aee5eeaeace2`。本轮 ChatGPT 基于冻结 Bench 实际 `observer.py:103–139,276–302`、`node.py:19–74` 等只读复核，结论：**`G2 V2.1 DOCUMENT DESIGN REVIEW PASS (CPU-ONLY J1 FIXTURE-SPEC DRAFTING INPUT ONLY)`**；这不是整体 G2 安全 PASS、不是 G2 判据冻结，也不是批准 CPU 测试或 REAL 运行。

独立审核记录：`a_predicate_003/gate_g2/G2_V2_1_INDEPENDENT_DESIGN_REVIEW_001.md`；新 checkpoint：`docs/F3B_D1_A_CPU_003_E1A_G2_V2_1_DESIGN_REVIEW_001_CHECKPOINT_20261028.md`。审核区分 B0 的原生自动放行与 P1 的假设性 held-release 驱动；禁止把 B0 缺陷复现 TEST PASS 当 B0 安全 PASS；创建者回收证据仅在明示的可信边界内成立，后代异常清理/合法回收仍为 REAL BLOCKED。Sidecar 的完整性哈希不构成事件真实性；未来 CPU 夹具独立真值不可直接输入 J1，必须由独立验收 oracle 比较。O-1…O-15 全部 OWNER UNDECIDED；Grok 因额度限制 `DEFERRED / NOT PERFORMED`，非 PASS。

下一步唯一指令：仅起草以 B0 缺陷侦测为目标的 **纯 CPU J1 夹具预注册规范文档**，优先六类最小对照：同父错误 PID、重复身份、缺失放行前证据、Z/DEAD/ECHILD、sidecar 缺尾、RELEASED 无 R；未纳入的历史卡记 `DEFERRED_BY_SCOPE`。不得冻结判据、实施或运行代码、测试、进程、GPU，也不得改变原生 Parcae、Bench、G0/G1 或进入 G3/BV/E1-A。

## E1-A G2 J1 CPU-only 夹具预注册规范草稿 V0（2026-10-28）

从已核对的 V2.1 限定审核基准 `d1-r3-a-cpu-003-e1a-g2-v21-review-20261028` @ `672b20bc8091c42c31786c66b8ea28191584def7` 建立独立 **纯文档** 分支 `d1-r3-a-cpu-003-e1a-g2-j1-cpu-spec-draft-20261028`。新增规范 `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md`，阶段记录 `docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_DRAFT_001_CHECKPOINT_20261028.md`。拟议研究问题仅为纯 CPU J1 检测冻结 B0 的合成账本/观察证据中是否存在**明确异常或证据不足**，不是 B0/P1 实时放行或 Parcae 模型测试。

预注册草稿覆盖 **6 个场景族、12 个唯一夹具 ID（4 个严格限定的预期 PASS 正向控制、2 个明确 FAIL、6 个预期 BLOCKED）**。每个案例分为 J1 可见的 `Lane S` 模拟观察与不提供给 J1 的独立真值 `Lane O`（后者仅供独立验收 oracle 比较）；分开 `expected_subject_verdict`、`observed_behavior_label` 与 `test_acceptance_verdict`，禁止将“缺陷复现测试 PASS”误报为原生安全 PASS。15 个 arm-qualified 历史卡仅选 6 个，其他 9 个均标注 `DEFERRED_BY_SCOPE`，不是 PASS。**全部夹具字节/哈希未生成，所有实际 CPU 测试 NOT TESTED。**

**状态：SPEC DRAFT PREPARED / INDEPENDENT DOCUMENT REVIEW PENDING / CRITERIA NOT FROZEN / IMPLEMENTATION & CPU NOT AUTHORIZED / REAL BLOCKED & NOT AUTHORIZED / Grok DEFERRED (NOT PASS) / O-1…O-15 UNDECIDED。** 原生 Parcae、Bench、冻结 G0/G1、R3、已存证据及模型架构保持不变。下一条唯一指令：对规范草稿做独立、源码可追溯的只读设计审核；不冻结、不实施、不运行任何测试/进程。

## G2 J1 CPU SPEC V0 独立审核：CHANGES REQUIRED（2026-10-28）

来源：`d1-r3-a-cpu-003-e1a-g2-j1-cpu-spec-draft-20261028` @ `fb5bb8779b93fb9027964e43229f368c1750488e`；V0 spec Git Blob `44cd58d1089ca8b394658acafe4f8477e371d2f0`。在独立审核分支 `d1-r3-a-cpu-003-e1a-g2-j1-spec-review-20261028`，ChatGPT 以冻结 `bench/observer.py`、`registry.py` 等源码复核六族 12 个拟议合成夹具的真值隔离、断言与判定，形成**`G2 J1 CPU SPEC V0 DOCUMENT REVIEW CHANGES REQUIRED`**（规范可审查，不是实际 CPU 测试 FAIL）。

审核报告：`a_predicate_003/gate_g2/G2_J1_CPU_SPEC_V0_INDEPENDENT_REVIEW_001.md`；检查点：`docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_V0_REVIEW_001_CHECKPOINT_20261028.md`。六项发现 F01～F06：J1 输入没有明确排除夹具 ID/答案元数据；单一断言状态能被固定输出应付；sidecar 可信 seal 不匹配的完整性 FAIL 与依赖日志推理的 BLOCKED 混用；假设性模拟见证者不能等同原生 B0 真实来源；序列化/读取完整性不够封闭；J1 检出缺陷 TEST PASS 不等于 B0 安全 PASS。12 个 ID/6 族/4 narrow PASS+2 FAIL+6 BLOCKED 都是**拟议预期**，实际测试与夹具字节为 NOT TESTED/NOT MATERIALIZED；9 个其他 arm 保留 DEFERRED_BY_SCOPE。

**状态：G2 SPEC V0 REVIEW CHANGES REQUIRED / V0.1 DOC REVISION NEXT / G2 CRITERIA NOT FROZEN / G2 CODE & CPU NOT AUTHORIZED / G2 REAL BLOCKED & NOT AUTHORIZED / Grok DEFERRED（不是 PASS）/ O-1…O-15 OWNER UNDECIDED。** G0/G1 已验收与原生 Parcae/Bench/R3/模型架构未改。下一条唯一指令：**仅修订 J1 SPEC V0.1 文档并重新只读审核**，先解决输入隔离与单一断言固定输出，不实施/运行任何代码或进程。

## G2 J1 CPU SPEC V0.1 六项问题修订 — Claude Code 实施分工（2026-10-28）

**最新文档分支：** `d1-r3-a-cpu-003-e1a-g2-j1-spec-v01-doc-20261028`，基于已核对 `d1-r3-a-cpu-003-e1a-g2-j1-spec-review-20261028` @ `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6`。历史 V0 审核为 **CHANGES REQUIRED**，六项 F01～F06。独立文件 `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md` 是**新 V0.1 草稿，不替换/篡改已审核的 V0**。阶段 checkpoint：`docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_V0_1_REVISION_CHECKPOINT_20261028.md`。

V0.1 在 **6 个场景族内设计 18 个待审核夹具**，其中**预期** 5 narrow PASS / 5 FAIL / 8 BLOCKED，均是拟议的 **subject verdict**，**尚无实际 CPU 测试**。现在 J1 API 不得收到 fixture_id/评分/私有 truth；私有 oracle 仅由独立验收器使用；五类 assertion 有相反结果对照，四类无法全面区分的 assertion 明确 `SMOKE_ONLY`；可信 seal 不匹配的完整性断言预期 FAIL、依赖缺陷日志作推断预期 BLOCKED；G2_WITNESS_SIM、G2_WRAP_SIM、SEAL_MANIFEST_SIM 被标注为假设性证据，不能冒充原生 B0 的真实记录。另 9 个 arm `DEFERRED_BY_SCOPE`，非 PASS。所有夹具字节和 SHA256 尚未生成。

**研发职责：** ChatGPT 负责验收设计、独立审核与 checkpoint；用户要求**以后实际代码开发由 Claude Code 负责**，但必须在 V0.1 独立审核后另行获得代码阶段授权，再形成绑定 Git SHA 的 Claude Code 实施指令。**目前代码未授权、未委派执行；所有 CPU/REAL 均 NOT TESTED / NOT AUTHORIZED。** Grok 因额度限制 `DEFERRED / NOT PERFORMED` 不是 PASS，O-1～O-15 OWNER UNDECIDED；G2 REAL 仍 BLOCKED，原生 Parcae/Bench/R3/G0/G1 及模型架构未动。

**下一条唯一指令：** 对 V0.1 规范文档做独立只读源码设计审核，记录反例及 checkpoint；不冻结、不写代码、不运行测试，也不代替 Claude Code 启动实施。

## G2 J1 V0.1 限定审核及 Claude Code 开发指令交接（2026-10-28）

从 `d1-r3-a-cpu-003-e1a-g2-j1-spec-v01-doc-20261028` @ `07ec81519684e7cc6b0477f086787c4dc32f4520` 创建独立文档/交接分支 `d1-r3-a-cpu-003-e1a-g2-j1-v01-review-claude-handoff-20261028`。ChatGPT 已对 **V0.1 18 个拟议 J1 合成 CPU 夹具及五类对照、四类 SMOKE_ONLY** 做独立只读源码审查，结论为 **`DOCUMENT REVIEW PASS — ONLY AS CODE-IMPLEMENTATION HANDOFF INPUT`**。该结论**不**等于 G2 整体设计、冻结判据、代码/CPU 测试或 REAL 通过。V0.1 当前预期被测输出为 5 limited PASS、5 FAIL、8 BLOCKED；实际 0/18 NOT TESTED；Grok 审核 DEFERRED（不是 PASS），O-1～O-15 OWNER UNDECIDED。

**新审核报告：** `a_predicate_003/gate_g2/G2_J1_CPU_SPEC_V0_1_INDEPENDENT_REVIEW_001.md`。**Claude Code 开发任务书：** `a_predicate_003/gate_g2/CLAUDE_CODE_J1_IMPLEMENTATION_ONLY_HANDOFF_20261028.md`。**最新 checkpoint：** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_V0_1_REVIEW_AND_CLAUDE_HANDOFF_CHECKPOINT_20261028.md`。

**分工与边界：** ChatGPT 负责设计、审查、验收/checkpoint；用户要求由 Claude Code 负责实际编码。本次已准备完整开发任务，但**尚未调用 Claude Code**。未来由用户将任务书交给 Claude Code，它只能在**新的隔离代码分支**实现纯 J1 schema/judge/oracle/codec 和未经执行的静态测试源码，不能跑 Python/pytest/CPU 夹具或真实进程、不能生成运行证据、不能修改 Parcae/Bench/冻结 G0/G1/R3、不能自行冻结判据或进入 REAL。完成后代码 commit/push 并停止，回交 ChatGPT 审核。**G2 REAL 仍因合法回收者、孤儿和无信号异常收尾 BLOCKED。下一条唯一指令：交付 Claude Code 实施指令并停止本会话工作。**

## D1 CPU-003 E1-A G2 J1 实现源码 G2-J1-IMPL-PREP-001（2026-10-28）

基线 `02d79a26e4ad6b49527bc90e6be4fe9130b45cff`（交接分支 HEAD，已核对），开发分支 `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028`。仅新增 `a_predicate_003/gate_g2/j1/` 纯 Python 合成证据判定器源码（`schema.py` / `judge.py` / `codec.py` / `oracle.py` / `README.md` / 未运行的测试源码）：五类有对照断言 + 四类 SMOKE_ONLY（无 PASS 路径）、Lane S/Lane O 隔离、harness 绑定信任表、严格 bool≠int、RELEASED=放行意图、Zombie/DEAD/ECHILD≠合法回收、哈希一致≠内核事件真实性。**未运行任何测试或 Python 项目代码（含语法检查），均为 NOT TESTED**；未冻结判据、未生成夹具、未改 Bench / Parcae / G0 / G1 / R3；Grok DEFERRED，O-1…O-15 未决，G2 REAL BLOCKED。状态：IMPLEMENTATION SOURCE PREPARED — STATIC REVIEW PENDING。检查点 `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_PREP_001_CHECKPOINT_20261028.md`。下一步：交 ChatGPT 做独立静态代码审查，之后另行授权才可考虑夹具与 CPU 验收。

## J1 实施源码独立静态审核：CHANGES REQUIRED（2026-10-28）

Claude Code 开发分支 `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028` 远端 HEAD 已独立核验为 `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`，开发基准 `02d79a26e4ad6b49527bc90e6be4fe9130b45cff`。Git compare 确认只新增 `gate_g2/j1/` 7 个文件（其中单元测试源码未运行）、新增开发 checkpoint、更新两份导航：10 文件/1805 行新增/0 删除，冻结 Bench、Parcae、G0/G1、R3、已有证据不变。

ChatGPT 在独立审查分支 `d1-r3-a-cpu-003-e1a-g2-j1-impl-static-review-20261028` 完成 **只读源码静态审核**，结论 **`J1 IMPLEMENTATION STATIC REVIEW CHANGES REQUIRED`**。完整报告：`a_predicate_003/gate_g2/G2_J1_IMPL_SOURCE_INDEPENDENT_STATIC_REVIEW_001.md`；最新 checkpoint：`docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_STATIC_REVIEW_001_CHECKPOINT_20261028.md`。7 项发现 F01–F07：Oracle 对 `INPUT_INVALID` 的 BLOCKED 可能误判 test PASS；预期答案与 18 项清单及 S/O 证据无独立绑定；ATTRIBUTION 未强制 same-ticket/gate 见证；UNIQUE_REGISTRY 可以在不完整 RUN_START/生命周期上 PASS；调用者给定信任角色不等于真实性认证；真实原生 registry 带浮点 mono/wall 与当前封闭合成输入不兼容；Claude 自报一次空 `python3` 启动，**Git 范围 PASS 但严格零-Python 程序约束 FAIL**。所有反例仅源码推导，**未执行**。

**状态：代码已写但 STATIC REVIEW CHANGES REQUIRED / CPU 与 18 夹具 NOT TESTED / CRITERIA NOT FROZEN / G2 REAL BLOCKED / Grok DEFERRED 非 PASS / O-1…O-15 OWNER UNDECIDED。** 下一条唯一指令：准备给 Claude Code 的 *SOURCE-ONLY 修正任务*，由负责人另行授权；不得由 ChatGPT 修改代码，不得运行 CPU/REAL 或改上游，修复后重新提交并独立静态审核。

## J1 独立静态审核后的 Claude Code 代码修复交接（2026-10-28）

只读核验起点：`d1-r3-a-cpu-003-e1a-g2-j1-impl-static-review-20261028` @ `1b2ba339d267b8c04e1db5fb71d29da45a597758`，原 Claude Code 实现 HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68` 不变。最新文档交接分支：`d1-r3-a-cpu-003-e1a-g2-j1-fix-handoff-20261028`，新增 **`a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_HANDOFF_20261028.md`** 与 **`docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX_HANDOFF_CHECKPOINT_20261028.md`**，未提交任何代码修正。

静态审查 **`CHANGES REQUIRED`** 未解除：F01 无效 Lane S 的 BLOCKED 可能被当作测试 PASS；F02 原始 expected 及 aggregate 可被伪造；F03 同 node 但 gate/ticket 关联不足；F04 native B0 RUN_START/生命周期不完整仍可能得到 UNIQUE_REGISTRY PASS；F05 信任来源只是假设性 harness；F06 原生 B0 浮点记录与合成 J1 接口不兼容；F07 历史一次空 Python 启动作为自报程序性 FAIL 保留。最新交接说明采用保守的 **synthetic-only** 边界，不在本次制作真实 B0 adapter 或可信内核见证；正式 18 个夹具仍为未物化/未测试。

**下一步唯一指令：用户向 Claude Code 发送上述 SOURCE-ONLY 修复任务**；Claude 独立分支仅改 `gate_g2/j1/` 和新 checkpoint/导航，添加**未运行**反例测试源码，commit/push 后 STOP，交回 ChatGPT 做新一轮独立静态审核。**ChatGPT 本轮不改程序；G2 CPU NOT TESTED，判据 NOT FROZEN，REAL BLOCKED，Grok DEFERRED（非 PASS），O-1…O-15 未决定。**

## D1 CPU-003 E1-A G2 J1 源码修正 G2-J1-IMPL-CORRECTION-001（2026-10-28）

基线 = 交接分支 HEAD `692e551126c5171b13565f2ece30bf39d6ce8352`（已核验），修正分支 `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028`。仅在 `a_predicate_003/gate_g2/j1/` 修复独立静态审核 J1-IMPL-F01…F06：无效输入走独立的 `input_valid / INPUT_INVALID` 通道且 Oracle 永不给出正式 PASS；预期结果钉死到 V0.1 的 18 项清单（18 个预期值未改），`aggregate` 去掉 `expected_ids` 且在无独立 S/O 封存与证明前恒为 BLOCKED/NOT_READY；ATTRIBUTION 需要显式、一致的 gate/ticket 关联否则 BLOCKED；UNIQUE_REGISTRY 按冻结 Bench 生命周期规则按值复述并仅声称有限给定集合；信任映射明示为未认证的假设性 harness 声明，J1 仅限手写合成 B0 形态输入，原生适配器未实现。补充 F01–F06 的未运行负向测试源码。**本任务未调用任何 Python**，全部 NOT TESTED；F07 历史程序性偏差保留；未改 Bench / Parcae / G0 / G1 / R3、未冻结判据、未生成夹具；Grok DEFERRED，G2 REAL BLOCKED。检查点 `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_001_CHECKPOINT_20261028.md`。下一步：交 ChatGPT 独立静态复审。

## J1 修正源码独立静态复审：仍有未经验证的 PASS 路径（2026-10-28）

来源：Claude Code 修正分支 `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` @ `045fa24a1b25f57d27d18dfc9b70b7c437c55898`，基准 `692e551126c5171b13565f2ece30bf39d6ce8352`；原修正 Git compare 为 2 commits / 8 files / +628/-199，只在 `gate_g2/j1/` 及 `docs/` 修改，Bench/Parcae/G0/G1/R3/原始证据未改。ChatGPT 建立独立文档审核分支 `d1-r3-a-cpu-003-e1a-g2-j1-fix-static-review-20261028`，只读源码后形成报告 `a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`，新 checkpoint `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_STATIC_REVIEW_001_CHECKPOINT_20261028.md`。

**复审结论：`STATIC REVIEW CHANGES REQUIRED`。** 原 F01/F02 的 Oracle 正式验收通道已静态收紧为始终 `BLOCKED / NOT_READY`，无效输入不再取得 formal PASS；原 F05/F06 仍严格合成范围。但发现 4 项新/剩余问题：`J1-FIX-REVIEW-F01` 高：缺 INTENT 的 DEAD/ABORTED 节点绕过 frozen registry ORPHAN_RECORD；`F02` 高：UNIQUE_REGISTRY 明定的 (pid,starttime) 与实现采用可选 boot_id/pidns 的 `same_instance` 不同；`F03` 高：ATTRIBUTION 的多见证 identity 冲突与同 gate 跨节点冲突可能被遗漏；`F04` 中：Oracle 汇总遇到不可 hash 的 fixture_id 可能 TypeError，而非 fail-closed。**这些均为源码反例推断，未执行。** Claude Code 自报这次没有调用 Python，连接器无法独立验证其本地命令记录；前次空 Python 解释器偏差继续保留历史记录。

**状态：J1 源码已提交但静态复审 CHANGES REQUIRED / CPU 与 18 S/O 均 NOT TESTED / 判据 NOT FROZEN / G2 REAL BLOCKED / Grok DEFERRED 非 PASS / O-1…O-15 OWNER UNDECIDED。** 下一条唯一任务：获得负责人对 **Claude Code SOURCE-ONLY 修正** 的授权后，在隔离分支处理 F01～F04 并补未运行反例测试源码，commit/push/STOP，交回 ChatGPT 复审。不得在 ChatGPT 直接改代码、运行 Python/CPU/G2 REAL，亦不可改上游 Parcae、Bench 或既有证据。
