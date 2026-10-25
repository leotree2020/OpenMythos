# F3-B — ChatGPT 独立设计审核与 D1 最小冻结门禁

日期：2026-10-25（Asia/Tokyo）  
仓库：`leotree2020/OpenMythos`；研究分支：`mini-mythos-p1c-gate22c-readiness`。  
Grok 待审提交：`103344e47184735e03727d062ce81cbae6632e47`（其父提交为上轮已审项目进度 `3cba0ee871efdcc47b9e0b2ddc493e471c822932`）。  
文件：`F3B_REAL_DATA_TRAINING_PLAN.md`、`F3B_DATA_STREAMING_AND_RESUME_AUDIT.md`、`F3B_MODEL_EVALUATION_AND_BASELINES.md`、`F3B_D1_D2_D3_ACCEPTANCE_GATE_DRAFT.md`、`F3B_RESEARCH_HANDOFF.md`，以及修改 `PROJECT_MAP.md`。  
审查方式：**GitHub 只读文档 + 历史 R1/R2 证据 + Parcae pinned 模型源码核对 + HF 官方公开数据版本/许可页面核对；没有训练、没有 CPU 数据遍历、没有下载整套训练集，也没有启动 GPU**。

## 1. 独立决策（层级严格区分）

**`F3-B DESIGN DELIVERABLES: PASS / CLOSED`（仅指五份指定研究设计文档已提交、D1/D2/D3 清楚分离，且没有把设计冒充实验 PASS）。**

**`D1 EXECUTION GATE: DRAFT / NOT FROZEN / NOT AUTHORIZED`**。要批准数据获取、BPE 拟合和数据恢复检查前，必须由 Grok 先完成一份**限定 D1 冻结补充**，其中解决以下具体缺项，并经 ChatGPT 审核及项目负责人明确执行授权。此设计审查**不是**对任何新的数据读取/Tokenization 运行或模型训练的 PASS。

**`D2 REAL-TEXT TRAIN: NOT TESTED / NOT AUTHORIZED`**。  
**`D3 QUALITY/EFFICIENCY COMPARISON: NOT TESTED / NOT AUTHORIZED`**。  
**`GPU: BLOCKED / NOT AUTHORIZED`**。  
原生 F3-A `PASS/CLOSED` 的固定 CPU 研究性训练范围保持不变，无需重跑。F2-E E6 `INCONCLUSIVE` 不升级或掩盖。

Grok 的提交新增 5 个设计文档、修改 1 个项目地图；提交中没有新增训练执行代码、模型权重或实验运行产物。无法从 GitHub 验明远端以外的本地工作区，dirty `gate2_1/TEST_RESULTS.json` 仍依 Grok 报告保护。

## 2. 复核事实与已通过的设计决策

### 2.1 历史真实数据和 R2 风险证据

- `docs/R1_GATE_F_RESULT.md` 历史固定数据源为 `Salesforce/wikitext` / `wikitext-2-raw-v1` / official `test`，当时 resolved Git commit `b08601e04326c79dfdd32d625aee71d232d685c3`；byte-token NLL 2.384439/PPL 10.852968 仅适用于当时 byte tokenizer，不能直接对比新 BPE token-PPL。
- 该精确 HF 数据版本在公开数据仓库页面可定位：`https://huggingface.co/datasets/Salesforce/wikitext/tree/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-2-raw-v1`。其中有 train、validation、test 三个 Parquet 文件。
- R2 Gate M/N/O/P/Q 的 Git 已归档结果支持固定 FineWeb-Edu `sample-10BT` / commit `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` 的 **14 个实际 Parquet 文件身份 / 14 个逻辑 Shard / 14↔7 双重分片元数据及真实本地 OS Worker 身份重放**，Gate Q 本地合成 14 shard 8/8 PASS。**没有远端逐文档/Token 行读取，也没有真实 DataLoader 恢复或模型训练**。F3-B 文档这一区分成立。旧版本路线图中 Gate N“尚未完成”的口径已被后续真实 Gate N 结果取代。
- WikiText-2 是合理的 first small CPU candidate；FineWeb-Edu 为未来 scale candidate。选择小数据减少外部成本和 R2 远端网络不确定性，符合 CPU 优先。

### 2.2 已正确的设计判断

- 提议 `train-only BPE`，不访问 validation/test 拟合；明确标记 `ALTERNATIVE RESEARCH TOKENIZER` 而不是官方 Parcae Tokenizer。官方 Tokenizer 的准确身份/许可仍需独立核对。
- `D1 data/stream resume → D2 real-text train → D3 held-out + fair baseline` 的三层顺序科学合理，不可合并。
- D3 明确单独比较同训练 Token 和近似同 FLOPs 预算，说明共享参数不等于共享计算预算；NLL/PPL 要同 tokenizer/同 Token 定义，测试集应在设计冻结后作最终一次性报告。
- ¥700 单次与 ¥5,000 累计为历史参考上限，并**不是**新的 GPU 授权。后续必须另行核实资源环境、费用与真实证据提取器。

## 3. D1 进入执行前必须补齐的有限问题（严格有限，不扩大 F3-B 研究维度）

### D1-01. 锁定数据源的不可变身份与合规元信息（必要）

F3-B 目前写 `wikitext` + 配置名 + “version can be pinned”，并**未锁定 D1 使用的真实 `repo_id` 和 `revision`**。建议复用前次真实使用的：

```text
repo_id = Salesforce/wikitext
config = wikitext-2-raw-v1
revision = b08601e04326c79dfdd32d625aee71d232d685c3
splits = train / validation / test
```

在 D1 freeze 内同时规定下载/API 模式、datasets/hf_hub/pyarrow/tokenizers/Python 版本、字段名 `text`、来源身份 + 每 split 行数/哈希冻结方法（初次实际读取后冻结结果只能作为 D1 **测量结果**，不得事后改预期去迎合结果）。来源快照 file hash 如无法预先确认要标记 `NOT VERIFIED`，冻结如何计算与何时验收。

许可注意：HF dataset 页 metadata/badge 显示 `cc-by-sa-3.0` / `gfdl`，其中 Dataset Card 叙述又标识 CC BY-SA 4.0；这存在页面措辞差异。D1 前需要记录出处与实际适用许可/归属要求，不应笼统写“公开即自由无限制使用”；如需要外部分发则另审合规。

### D1-02. BPE 的实际 Tokenizer identity 与封闭性（必要）

冻结：BPE 类型（ByteLevel BPE 还是非 ByteLevel BPE）、Unicode normalization、pretokenizer/decoder、词表上限 `4096` 与**实测实际** `vocab_size`、train-only 文档过滤规则（包括 WikiText 空行和分段）、seed/迭代顺序、`BOS/EOS/PAD/UNK` 及具体 Token ID、EOS 跨文档行为、Tokenizer JSON/hash、encode/decode round-trip 和未见字符策略。任何被用来拟合 Tokenizer 的文本只允许来自 train；validation/test 只能在 Tokenizer 固定后用于编码/评估，不反向改变规则。

**PAD token ID ≠ cross_entropy 的 `ignore_index`**。原生 Parcae `parcae_lm/models/parcae/parcae.py` 默认 `ignore_index=-100`；D2 如有 padding 必须明确将 `labels` 中被忽略位置置为 `-100`（或显式冻结与 loss 对齐的别的设计），不能简单写“PAD as ignore index”。

### D1-03. 数据断点恢复要有真正可复验收定义（必要）

D1 设计草案只提 “uninterrupted vs resumed document ids/token hashes match”，还需冻结：
- 是 `streaming=True` IterableDataset 还是 `Dataset` map 模式；单进程 `num_workers=0` 为第一步默认，避免把多 Worker 当成已通过；若多 Worker，必须独立定义其恢复门禁。
- 每个来源身份以 `split + dataset row index + document offset/segment index` 定义，记录源文档身份和 Token 序列级 digest，拒绝**非预期**重复/遗漏。相同文本可合法重复，因此不能只凭“文本内容一样”认定跳读。
- 冻结 resume 的有界遍历数量（例如首 64 个合格文档或首 256 个有界 Token 窗口；这是**建议**，执行前必须选择一个明确窗口），中断位置（例如第 1/2 处）、token/row offset、随机种子与 shuffle/buffer 状态、checkpoint schema、恢复算法和比较方式（严格一一相同；记录前后与合并摘要）。
- source row counts、空行剔除、EOS、跨文档 packing、stride 与 label shift，避免“记录数一致但 Token 数据重复/少读”的假阳性。
- 单进程 D1 不自动证明 2-worker / 14 Parquet 文件 shard 身份覆盖，更不证明真实 FineWeb 远端行恢复。

### D1-04. 预先约定负例和 PASS/FAIL/BLOCKED（必要）

至少应有 3 个不训练模型的受控拒绝负例：强制跳过一个 source ID、重复一个 source ID、伪造/错位 checkpoint cursor，要求正式验收器检测并 **FAIL**。可再加 `tokenizer hash mismatch` / dataset revision mismatch，不强制开启新的复杂研究。

必须保存实验命令、环境、输出/原始日志与 SHA、Git HEAD/dirty、输入/预期/实际、状态、下一条指令。无法读取不可变 HF 版本、无法核对许可证/字段或依赖则 `BLOCKED`，不能自动切换到最新版本让实验“运行成功”。

**注意：D1 必须独立获得明确授权。** 若 D1 需要训练 `train-only` BPE，该过程是 Tokenizer 拟合/训练，应在 D1 授权文字中具体允许（与语言模型权重训练区分）；当前 F3-B 设计阶段不允许执行 D1 Tokenizer 拟合。

## 4. D2/D3 先记录、后续门禁裁决；不阻塞 D1 数据设计

### D2-01. 4096 Tokenizer 不能原样接入 F3-A 128 vocab 模型（硬配置冲突）

F3-A 模型为 `vocab_size=padded_vocab_size=128`，共 247,936 参数。Parcae 真实源码含 `torch.nn.Embedding(config.padded_vocab_size,config.n_embd)`、单独的 LM `Linear(n_embd,padded_vocab_size)`（当 `tie_embeddings=False`），某些配置还有 value embeddings。新的 train-only BPE 若实际 vocab≈4096，其 Token IDs 可能 >=128；旧嵌入层会报索引越界且输出头维度不符。D2 **必须冻结新版 `padded_vocab_size`、实际参数量与新的 init weight hash**，明确这是保留**同一 2/2/2 结构配置家族**、但不再拥有 247,936 参数的独立初始化模型。

不允许悄悄截断/对词表求模或将 4096 压回 128 来“维持参数量”；要么在 D2 显式扩词表并重新审算参数量，要么独立冻结 128 Tokenizer 作为另一配置。新 Tokenizer 的 token-PPL 不能不加换算就与历史 byte-PPL 直接比较。

### D2-02. 真正数据训练是独立实验

D1 即使通过，只能证明数据/Tokenizer/恢复。模型训练须另外冻结每步输入/labels、学习率、训练 Token 预算、epoch、checkpoint optimizer/scheduler/RNG/data cursor、stop on nonfinite、heldout 分离和运行成本。此前 F3-A Checked Loader 是独立验证器，未来真实训练入口须审计数据流和 checkpoint schema 的**实际集成**，不能假设原生 `scripts/train.py` 生产路径已通过。

### D3-01. 控制变量与独立 test 集

同一 tokenizer、训练数据、eval tokens、精度和预算记账。对照标准 Transformer vs 固定递归；在相同训练 Token 与近似相同 FLOPs 两个维度分别报告，必要时重复种子才形成架构收益主张。报告参数/模型存储/激活峰值/实际 FLOPs/延迟的测量与估算标签，切勿将参数共享当成省 FLOPs。验证集用于设计/选模、测试集仅最终一次冻结评估，避免调参测试集污染。

## 5. 下一条唯一研发指令 / 授权

**下一步只需一个 D1 冻结配置补充，不需要重新做五份 F3-B 设计研究**。Grok：
1. 读最新 Git HEAD / SOP / project map / 本审核，以及五份原 F3-B 文档；
2. 在不执行下载、Tokenizer 拟合、真实数据迭代、模型训练的情况下，提交 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，逐条冻结 D1-01..04、CPU-only 资源和异常停止；
3. 在另一阶段记录 D2 的 4096 vs 128 词表参数冲突和 D3 NLL/PPL 公平协议，不因此运行或修改模型；
4. 提交 Git checkpoint，保留历史 B1/R1/R2/F2/F3-A 与 dirty `gate2_1/TEST_RESULTS.json`；
5. 以 `D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW` 停止，待项目负责人明确批准 D1 CPU 数据读取/Tokenizer 拟合/保存恢复检查后才执行。

项目战略仍为 Grok 主要研发、ChatGPT 独立审核、Claude Code 暂缓；上游源码保持不变，CPU 优先，GPU Gate 2.2-C 保持 BLOCKED。旧 ￥700 单次/￥5000 累计历史预算上限**不是此任务的资源许可**。

## 6. 研究状态 / 检查点

- F3-B 设计文档交付：**PASS/CLOSED（设计交付物，不是 D1 准备或实际结果 PASS）**。
- D1 数据路径门禁：**DRAFT / NOT FROZEN / NOT AUTHORIZED**。
- D2 真实文字训练：**DRAFT / NOT TESTED / NOT AUTHORIZED**。
- D3 heldout/fair baseline：**DRAFT / NOT TESTED / NOT AUTHORIZED**。
- F3-A 微型原生 Parcae CPU train + resume：**限定 PASS/CLOSED，保留已归档实验**。
- R2 Gate M/N/O/P/Q：**保留各自元数据/本地合成专项 PASS，未做远端真实 Parquet 逐行/Tokenizer/真实训练**。
- Python/PyTorch 运行环境与本地 Git dirty：依当前 Grok 报告，独立远端审核**未验证现场状态**；上轮 F3-A `RUN_META` Python 3.10 vs 命令 3.11 的出处不一致保持待注释。
- 最新可执行许可：**只读研究和 D1 冻结方案文档提交**，不是 CPU D1 运行许可。

本文件提交后新会话必须重新读取真实分支 HEAD 和项目检查点；本次审查没有产生新的 CPU/GPU 实验 PASS。
