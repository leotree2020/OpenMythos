# Mini-Mythos / OpenMythos — 全项目研发进度（2026-10-25 更新版）

## D1 代码冻结候选 C2b 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C2a 段）

基准 `796cc6138caaedf8a45d9abd12554ef62235e77d`。C2b 两项：CR 的故障/对照读取器各自退出码与状态保留，整体按 FAIL > BLOCKED > PASS 聚合（`cr_reader_verdict` + `aggregate`）；`verifier_verdict()` 对非字符串 verdict 安全返回 FAIL。新增测试在 C2a 上失败（CR1/CR2 误记 BLOCKED；`TypeError: unhashable type`），56 项合成回归 OK。读取器、验证器、冻结配置、历史文档未改。

**状态：`D1 CODE FREEZE CANDIDATE C2b / PENDING CHATGPT FINAL ACCEPTANCE`**。仅 CPU 合成数据；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED；执行主机环境 BLOCKED。**下一条唯一指令**：等待 ChatGPT 最终验收。

## D1 代码冻结候选微型勘误 C2a 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C2 段）

基准 `f28f32b6d1514f15ccf680f752f5c414322cab51`。C2a 两项：验证器结果判读区分「文件不存在」与「存在但不可解析」（只有退出码 4 且无文件才 BLOCKED；畸形/未知 verdict/退出码不符为 FAIL）；负例聚合 FAIL 优先于 BLOCKED，每项状态明细与 `counts` 保留。4 项相关测试在 C2 代码上失败，52 项合成自测 OK。读取器、验证器、冻结配置未改。

**状态：`D1 CODE FREEZE CANDIDATE C2a / PENDING CHATGPT FINAL CODE REVIEW`**。仅 CPU 合成数据；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 最终代码复审。

## D1 代码冻结候选勘误 C2 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C1 段）

基准 `3775dc333577094d30297d3e28f9aa8d5d40039c`。C2 只做三项最小门禁修订：读取器退出码 4 → BLOCKED（驱动器退出码 PASS 0 / FAIL 1 / BLOCKED 4）；30 分钟硬上限设为代码常量，real 模式禁止覆盖、selftest 只能缩短；验证器异常退出、结果缺失/畸形/与退出码不符以及驱动器自身异常都写入决定文件为 FAIL 或 BLOCKED。12 项新回归测试（C1 代码上 11 项失败），全量 49 项合成自测 OK。只读环境盘点：沙箱满足候选固定值，**执行主机 NOT VERIFIED**，冻结配置未改。详见 `F3B_D1_CODE_FREEZE_C2_ERRATA_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE C2 / PENDING CHATGPT FINAL CODE REVIEW`**。仅 CPU 合成数据；未下载、未拟合、未训练、无 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 最终代码复审；授权前不得运行 D1。

## D1 代码冻结候选勘误 C1 检查点（2026-10-26；本文件最新阶段进度，优先于下方代码冻结准备段）

审核基准 `090b6191f7558a43462691bb4fa9afa4b56fed9b`：`CODE FREEZE CANDIDATE FAIL`（代码完整性）。已修订：（1）`verify_cr` 重算故障/control trace 的块哈希、链、块号、总数、`stream_token_pos`、EOF tail 元数据；（2）独立构造 CR1/CR2/CR3 预期的单变异流与整窗口来源顺序并全量比对；（3）对抗性回归测试（单块哈希、tail_sha256、来源顺序、control 篡改；37 项合成自测 OK，旧验证器上 6 项失败）；（4）`verify_clean` 独立重算 P1–P5；（5）real 模式与正式 D1 身份分离；（6）Python 完整补丁版本候选固定（**执行主机未核实**）；（7）30 分钟硬超时 → BLOCKED、保留证据、不重试；（8）R6/R7/T1–T6/数据获取完整性标 NOT TESTED，流水线不输出总体 D1 PASS。详见 `F3B_D1_CODE_FREEZE_C1_ERRATA_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE C1 / PENDING CHATGPT RE-REVIEW`**。仅 CPU 合成数据；未下载、未拟合、未训练、无 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得运行 D1。

## D1 执行脚本冻结准备检查点（2026-10-26；本文件最新阶段进度，优先于下方 R2 段）

基准 `8a1700835c619fc1ad579da12713ece612403b8e`。准备了 D1 读取器、独立验证器、LR1–LR9 / CR1–CR3 受控负例脚本、`D1_FROZEN_CONFIG.json`、CPU 环境与依赖冻结说明（`research/mini_mythos/gate3_d1/`）和合成数据自测（`tests/test_d1_selftest.py`，24 项 OK；固定版本 venv 中同样通过，含 `--mode real` 代码路径）。读取器与验证器互不 import、不共享游标校验/来源映射/参照流函数；区分中间 carry 与 EOF tail；来源片段无空洞/无重叠/完全覆盖断言在两套实现中各有一份并被反向测试。详细记录与 12 条需复审的实现决定见 `F3B_D1_CODE_FREEZE_PREP_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE / PENDING CHATGPT CODE REVIEW`**。没有下载 Parquet、拟合 Tokenizer、D1 数据实验、模型实例化、训练或 GPU；数据获取与 Tokenizer 拟合脚本尚未编写；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 代码复审；授权前不得运行 D1。

## D1 预飞行 R2 最小修订检查点（2026-10-26；本文件最新阶段进度，优先于下方 R1 段）

基准 `579ffd11ec2dba0b9cbf0eae67d7ce4e26874c19`。R1 复审结论 `PRE-FLIGHT FAIL`。新增 `F3B_D1_FROZEN_EXECUTION_PROPOSAL_R2.md`，仅文档；v1（SHA-256 `a55b2cb7…ba9e`）与 R1（SHA-256 `f92c4e79…1d7a`）原样保留。修订项：（1）CR 负例由可信干净前缀 + 续读 trace 重新核算整个窗口，逐行对照 Token 数量、原始位置与完整内容，续读 trace 不重复历史块，故障注入证据与干净前缀分别保存、不得覆盖；（2）CR3 原始游标先通过全部九步校验，不得关闭加载检查，仅在读取循环内注入 Token 消费偏移，磁盘游标不改；（3）CR3 固定 `δ=+1`，P2 只选 Token 数 ≥ 3 的行，删除 `δ=−1`，预期码恒为 `TOKEN_OFFSET_MISMATCH`（LR1 随之固定为 `+1`，属于消除冲突的最小改动）；（4）P2 搜索合格行序号 [600,900)，找不到记 `BLOCKED(schedule)`，删除「相邻中断点至少相隔 300 行」的错误断言，改以实际 Token 流位置严格递增为判据，P3/P4 搜索起点包含行起点；（5）哈希链零起始块号，`H_{j+1}=SHA256(H_j ‖ block_hash_j)`，32 字节原始摘要拼接，`chain_hash=H_N`。

**状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`**。没有下载、拟合、模型实例化、训练或 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得执行 D1。

## D1 预飞行 R1 修订检查点（2026-10-26；本文件最新阶段进度，优先于下方 v1 段）

基准 `ab6d8271f30cb49e097f3979e29f42bf0e96d545`。新增 `F3B_D1_FROZEN_EXECUTION_PROPOSAL_R1.md`，仅文档；v1 方案原样保留（SHA-256 `a55b2cb7…ba9e`）。修订项：（1）N1/N2 改为合法游标恢复后读取过程内整行跳过/重复，写明首个受影响来源行、错误码与独立检测条件；（2）负例分 LR（加载拒绝）与 CR（继续读取）两类，分别给出 PASS 判据；（3）游标 `d1_cursor_v2` 增加 Token 内容、来源行身份、合法偏移、EOF、输出前缀与哈希链校验，9 步固定顺序；（4）5 个预先确定、升序的中断点，空 carry 合法；（5）Token 以 uint32 小端序列化，固定块哈希、哈希链初值与尾部核算；（6）冻结 Tokenizer 的编码/解码/特殊 Token/自动添加/padding/truncation/后处理；（7）勘误：v1 的 832 参数差额是把 13 个 `torch.nn.LayerNorm`（带偏置）误按 RMSNorm 计算，静态公式 `P(V)=206,976+320V`，V=128 处等于归档断言 247,936，适用前提见 R1 第 10 节；V=4096 处仍是 DERIVED，D2 须实测。

**状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`**。没有下载、拟合、模型实例化、训练或 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。Work 复审原文不在仓库中，R1 依据项目负责人转达的 7 条修订项。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得执行 D1。

## D1 预飞行方案检查点（2026-10-26；本文件最新阶段进度）

**交接**：项目负责人决定由 Claude Code 接替 Grok 做主要研发，ChatGPT 继续独立审核；下文各处「Claude Code 暂缓接管」已被取代，历史段落保留不改。

**本阶段产物**：`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，基于 HEAD `326121990cef4064d2c2d6cdc48a0d53da3cab3e`。内容：不可变数据源规则（含固定修订版、Parquet 行索引身份、合格行与文章边界/EOS 规则）、train-only ByteLevel BPE 冻结项（目标 4096，实际词表另测）、单进程游标恢复（A/B 路径、独立参照、块哈希链、覆盖条件）、N1–N5 负例、停止标准、证据布局、依赖与 CPU 资源估算、D2 词表冲突登记、风险与 BLOCKED 清单。

**状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`**。没有下载、没有 Tokenizer 拟合、没有读取真实数据行、没有实例化或训练模型、没有 GPU。D1 未 PASS、未 CLOSED；D2/D3 NOT TESTED。

**本阶段发现（需要审核）**：（1）上游 `scripts/train.py:287` 令 `ignore_index = tokenizer.pad_id`，而模型默认 `-100`（F3-A 用默认），D2 须显式选择；（2）词表相关参数由源码推为 `320×V`，但按源码手算的 F3-A 总参数为 247,104，与记录的 247,936 差 832，原因未明，因此 D2 参数量只能实测；（3）本沙箱 `huggingface.co` 被代理拒绝，D1 必须在有 HF 访问的环境执行。

**下一条唯一指令**：ChatGPT 审核本方案并经项目负责人明确授权后，才先提交 D1 执行脚本冻结提交；此前不得下载、拟合、训练或启动 GPU。


## F3-B 最新设计审核（2026-10-25；本报告最新阶段进度）

Grok 设计提交 `103344e47184735e03727d062ce81cbae6632e47` 新增五份方案、更新项目地图，没有提交任何新的模型训练代码或模型权重。ChatGPT 阅读五份设计，核对 R1 Gate F/WikiText HF 固定版本、R2 Gate M/N/O/P/Q 文件元数据与本地合成来源身份测试，以及原生 Parcae 嵌入与 LM Head 输入输出尺寸。独立审核文件 `research/mini_mythos/docs/F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`。

**正式状态：`F3-B DESIGN DELIVERABLES PASS/CLOSED`，仅限所要求的五份设计成果；`D1 DRAFT / NOT FROZEN / NOT AUTHORIZED`，D2/D3 `NOT TESTED/NOT AUTHORIZED`，GPU 不授权。** 旧 F3-A 2/2/2 固定输入 CPU AdamW 六步恢复门禁仍保持研究性限定 PASS/CLOSED；不可当成数据流训练/模型能力证明。

建议复用已经验证的 WikiText-2 raw 数据身份 `Salesforce/wikitext` / `wikitext-2-raw-v1` / `b08601e04326c79dfdd32d625aee71d232d685c3`。Grok 初稿仅写通用 config + “version can be pinned”，还缺 **真正冻结 repo+revision/许可说明**，必须在 D1 preflight 固定 train-only BPE 类型与实际词表/特殊 Token/Tokenizer hash、单进程 row/token cursor 与确定比较窗口、无意外重复/遗漏及错 cursor 负例、证据清单和 CPU 停止条件。

**关键 D2 前置冲突**：F3-A 验收时 vocabulary=128、参数=247936；F3-B 研究 BPE 目标 vocabulary≈4096，不能直接给旧模型喂新 Token ID 而仍称参数量相同。D2 另须冻结嵌入、输出 Head、padded_vocab_size 和重算实际参数量，并区分 PAD token ID 与 labels ignore_index=-100。

**下一条唯一指令**：Grok 只读起草 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md` 并提交审核；**没有授权 CPU D1 读取/Tokenizer 拟合，也没有授权真实文本模型训练或 GPU**。FineWeb-Edu 14 文件身份与双重分片历史 Gate M/N/O/P/Q 限定证据有效，但远端 Parquet 真正逐行读取/真实训练继续 NOT TESTED；官方 Parcae Tokenizer license/identity 保持 BLOCKED。历史脏文件 `gate2_1/TEST_RESULTS.json` 不可覆盖。

## 最终最新研究状态：F3-A 冻结 CPU Train Lifecycle 限定结案

**2026-10-25 最新独立审核优先级最高**：Grok 的 F3-A B1 与 R1 已提供连续训练、文件恢复的固定 6 步等价证据。最后异常检查 commit `dd36b939457a6c6197b0026fe38854c4edd05365` 在不重跑完整训练的条件下，完成 Scheduler 内容错误拒绝、Torch RNG 信任身份比较失败、保持 key 的实际张量 shape mismatch 拒绝；五项文本/脚本 SHA-256 由 ChatGPT 独立重新计算全 MATCH。正式报告：`research/mini_mythos/docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`。

**当前决定：F3-A 研究性原生 Parcae CPU 固定输入 AdamW 六步训练与 Checkpoint/Resume 生命周期 PASS/CLOSED（仅冻结微型范围）**。严禁推论原生 `scripts/train.py`、MuonAdamW、真实 Streaming DataLoader 恢复、真实语言能力/规模训练、GPU 已经通过。异常严格校验位于独立 checked loader，而不是先前运行六步训练的 R1 loader，因此在将来真实训练系统需要明确集成；损坏 RNG 的 `FAIL` 是**正确检测到异常的预期负例**，不是正常训练失败。

**出处风险保持**：最后 `RUN_META.json` 声称 Python 3.10.21、执行命令指定 `/usr/bin/python3.11`，二者不一致，准确运行解释器版本 `NOT VERIFIED`；二进制 `.pt` SHA-256 为 Grok 本地报告，ChatGPT 没有独立重算二进制。旧 `gate2_1/TEST_RESULTS.json` dirty 必须保护，禁止清理。不能更改旧结果隐瞒上述差异。

**下一研发主线（尚未授权运行）**：Grok 只读调查并设计/冻结真实数据加载、Tokenizer、分片/worker 恢复、heldout 质量指标及公平 Transformer 对照的后续阶段 Gate。**正式停止 F3-A 微型实验扩展**，不启动真实数据训练/GPU，不修改 Parcae/AxoNN 源码，保留 Prelude→Recurrent Core→Coda 和独立随机权重战略。

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
| Native Parcae CPU Train Lifecycle 执行 | **F3-A 固定 CPU 微型范围 PASS/CLOSED** | 原生 full train.py / DataLoader 恢复 / MuonAdamW / GPU / 更大模型仍 NOT TESTED；未来新 gate 单独验收 |
| 更大模型与公平非循环基线 | **NOT TESTED** | 实际模型质量、FLOPs、训练时间/稳定性、推理开销受控对比 |
| GPU Pilot / Gate 2.2-C | **BLOCKED** | 凭据、预算/实时定价、启动环境、真实证据提取器、用户授权 |

不按测试数、代码行数或阶段标签简单算统一完成百分比；现阶段的真正里程碑是**基础 CPU 正确性从“仍待收口”转为“限定正式收口”，下一步是开始真实原生训练链**。

## E. 唯一下一条研发指令、授权与 STOP

**当前下一步（Grok，仅真实数据与评估方案设计，未经授权不可执行）**：
1. 最新 Git 状态/dirty 只读核对并保护 `gate2_1/TEST_RESULTS.json`；
2. 读取 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`，确认 F2-E E1–E5 仅限定 PASS/CLOSED、E6 INCONCLUSIVE；
3. 已完成的 F3-A 原生小模型循环训练与文件恢复结果严禁重复；首先读取 `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`，随后只读审计真实数据及 Tokenizer、可恢复数据流、heldout/污染控制、同预算标准 Transformer 基线，冻结下一阶段验收方案。历史 R1/最终证据全部保存；
4. 提交新阶段的设计/验收门禁检查点，等待项目负责人明确授权实际真实数据训练；ChatGPT 继续独立审核，不启动 GPU。

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
