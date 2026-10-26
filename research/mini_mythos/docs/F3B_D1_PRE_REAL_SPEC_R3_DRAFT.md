# F3-B / D1 — 真实 D1 执行前规范 R3（草案）

**状态：`DRAFT / PENDING CHATGPT REVIEW`。不是 FROZEN，不是 PASS，不是任何授权。**

任务：F3B-D1-SPEC-R3-001（规范冲突消解）。日期：2026-10-26。起草者：Claude Code。
基准：`97d0faf2982f4122941d2299a23cab6ab2ba04a3`，分支 `d1-pre-real-spec-r3-20261026`（从 `d1-final-freeze-sentinel-fix-20261026` 新建）。
输入文档：v1（`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，SHA-256 `a55b2cb7…ba9e`）、R1（`…_R1.md`，`f92c4e79…1d7a`）、R2（`…_R2.md`，`1d4c3629…05d9`）与 `F3B_D1_FINAL_REGRESSION_CLOSEOUT_20261026.md` 本次已完整读取；冻结配置与 `D1_ENV_FREEZE.md` 读取并核对了与本草案相关的段落。**PRE-REAL-AUDIT-001 报告不在仓库里**，只存在于上一次会话的回复中；本文第 1 节的冲突表以该回复为线索，但**每一条都重新对照了原文**，引用以原文为准。

## 0. 本文件是什么、不是什么

1. 这是**规范草案**。没有改动任何冻结文件（v1/R1/R2、读取器、验证器、驱动器、测试、配置、`D1_CODE_SHA256SUMS` 均未触碰），没有下载数据，没有拟合 Tokenizer，没有访问网络，没有执行 D1，没有使用 GPU。
2. **所有 R3 条款都是 `【PROPOSED / NOT APPROVED】`。** 在被项目负责人批准、并经 ChatGPT 复审之前，v1 → R1 → R2 的冻结规则**原样适用**，并且**不得**被本草案暗中重新解释。
3. 本草案区分两类文字，并逐条标注：
   - **PROPOSED CLARIFICATION**：原文含义有歧义或缺失，草案给出一种可验证的具体化；不改变原文已明确的要求。
   - **PROPOSED AMENDMENT**：草案要求改变原文字面要求（必须引用被取代的原文）。冲突 S1、S2 属于这一类，因为两条冻结条文不能同时按字面满足。
4. 草案**不修改冻结的 Driver**。凡需要新增机制的地方，一律以**新的独立脚本**（尚未编写）承担；是否编写、何时编写，需另行授权。
5. 本草案批准后也**不**等于真实 D1 的执行授权。

## 1. 规范冲突与缺口表（原文逐条引用）

下表「原文」栏的引文均已对照源文件核对（见第 9 节）。章节号指原文件内的节号。

| ID | 位置 | 原文要求（引文） | 冲突 / 缺口 | 类别 |
|---|---|---|---|---|
| **S1** | v1 §3.2 第 1 步 vs v1 §5.5 R6、v1 §4.3 T1、R1 §9 R6 | v1 §3.2：「用 `huggingface_hub` 以显式 `revision=` 下载上述三个 Parquet 文件……下载后：1. 计算每个文件的 SHA-256」。v1 §5.5 R6：「train 的 Parquet 哈希在窗口读取前后相同；validation/test 在 Tokenizer 固定前未被打开（T1）」。R1 §9 R6：「validation/test 在 `tokenizer.json` 的 SHA-256 写入日志之前未被打开」 | 要对**三个**文件计算 SHA-256 必须读取它们的全部字节；而 R6/T1 要求 validation/test 在 Tokenizer 哈希写入日志前**未被打开**。两者字面上不能同时满足。「打开」没有定义（元数据查询？下载？计算哈希？解析？读取文本？） | **冲突 + 缺口** |
| **S2** | R1 §8「特殊 Token 与输入文本」行、R1 §9 T7 vs R6/T1 | R1 §8：「执行时先检查三个特殊 Token 字符串在三个 split 全部 NFC 文本中出现次数为 0；非 0 → `BLOCKED`」。R1 §9：「新增 **T7**：三个特殊 Token 字符串在全部 NFC 文本中出现次数为 0」 | 扫描 validation/test 的**文本**，比「计算哈希」更深地打开了这两个文件，且措辞是「先检查」，似乎在编码之前。与 R6/T1 冲突 | **冲突** |
| **S3** | v1 §5.5 R6；R1 §9 R6；R1 §6「B 路径执行方式」 | v1 §5.5：「train 的 Parquet 哈希在窗口读取前后相同」。R1 §6：B 路径为「6 段，每段是一次**独立的 Python 进程调用**」 | 「窗口读取前后」没说粒度：整个流水线一次，还是 A 加 B 共 7 次读取进程各一次。当前 `d1_reader.py` **不计算** Parquet 哈希（游标第 2 步只比较两个字符串）；`d1_verifier.py` 只在 `verify-clean` 末尾做一次读后核对。**读前核对在现有代码里不存在** | **缺口** |
| **S4** | v1 §3.4；v1 §3.3；v1 §4.3 T4；R1 §9 R7 | v1 §3.4：「按冻结 Tokenizer 编码后的 Token 数（对 validation/test 仅计数，见 5.5）」。v1 §3.3：`tokens(r)` 含「[EOS] 若 r 是一级标题行且不是该 split 的第一个合格行」。R1 R7：「只做文件哈希、行数、合格行数、Token 计数、round-trip」 | 「Token 数」是 `Σ len(tokens(r))`（含 EOS 前缀）还是 `Σ len(encode(NFC(text)))`（不含）没有明确。v1 §3.3 的「第一个合格行」按**每个 split** 理解有文字依据，但 §3.4 没重申 | **缺口** |
| **S5** | v1 §6 停止标准表；v1 §6 末句；R2/C2 驱动器行为 | v1 §6 停止标准表同时列出「未预期异常、墙钟超时」与状态「FAIL 或 BLOCKED（按原因）」；v1 §6 末句：「只能记录并停止」 | 「按原因」没有给出规则。获取、拟合、R7 审计等**尚不存在的**步骤被中断（崩溃、被杀、超时）后：部分产物是否保留、能否续跑、算 FAIL 还是 BLOCKED，都没有规定。已冻结 Driver 对**它自己的流水线**选择了「超时 = BLOCKED，保留证据，不重试」，这只是该组件的实现决定 | **缺口** |
| **S6** | v1 §4.3 T1；v1 §7.1 | v1 §4.3 T1：「……validation/test 的 Parquet 在 `tokenizer.json` 的 SHA-256 写入日志**之前**未被打开（按日志时间戳与顺序核对）」。v1 §7.1 的文件清单 | 没有定义这份「日志」：格式、写入者、是否防篡改、「打开」事件包括什么。v1 §7.1 的文件清单里没有任何获取/拟合事件日志。时间戳可被事后改写，「顺序」没有校验手段 | **缺口** |
| **S7** | v1 §8；`D1_ENV_FREEZE.md`（超时行）；冻结配置 `environment.wallclock_timeout` | v1 §8：「设 **30 分钟墙钟硬上限**，超时按第 6 节处理。下载量与耗时都依赖网络，无法在此预测」。`D1_ENV_FREEZE.md`：「尚未编写的获取/Tokenizer 拟合脚本须计入同一个 30 分钟」 | 预算范围没有定：是「获取 + 拟合 + 读取 + 验证」整段共用 30 分钟，还是各阶段各 30 分钟。现有 Driver 的计时从**它自己启动**开始，所以若获取已花掉 20 分钟，Driver 仍有完整的 30 分钟，合计 50 分钟。网络耗时又被原文承认无法预测 | **冲突 + 缺口** |
| **S8** | v1 §3.2 第 2 步 vs S1 的分阶段需要 | v1 §3.2：「再把下载目录切到离线读取（`HF_HUB_OFFLINE=1`），确认之后的读取不依赖网络」 | 若分阶段获取（先 train，后 validation/test），则在 Tokenizer 固定后还需要联网下载。「切到离线」的时刻与范围需要明确 | **缺口（由 S1 引起）** |
| **S9** | v1 §3.2 第 1 步 | 「记录 Hub 返回的该文件 LFS `sha256`（oid）。二者必须一致」 | 假设每个 Parquet 都是 LFS 文件、且 Hub 一定返回 LFS `sha256`。若文件不是 LFS 存储，或存储后端（本环境装有 `hf-xet`）不返回该字段，原文没有替代标准 | **缺口（NOT VERIFIED）** |
| **S10** | R1 §9 FORMAL 相关；冻结配置 `identity_rules`；`d1_driver.identity()` | 配置：「bookkeeping label only; a formal run still needs owner authorization and independent review」 | `identity()` 只比较清单里的字段彼此是否一致，并比较配置里的 revision；一个没有真实数据支撑的清单也能得到 `FORMAL_D1_CANDIDATE`（已用纯函数调用只读验证）。标签不要求 R6/R7/T 的证据。冻结 Driver 不得修改 | **缺口（身份可核对性）** |

## 2. 分阶段数据处理规范草案 `【PROPOSED / NOT APPROVED】`

### 2.1 操作词汇表（严格区分，PROPOSED CLARIFICATION）

| 级别 | 名称 | 含义 | 是否暴露文件内容给本进程 |
|---|---|---|---|
| L0 | **元数据查询** | 只调用 Hub 的元数据接口（解析修订、列目录、读取每个文件的大小/LFS/blob 信息）。不产生任何数据文件 | 否 |
| L1 | **下载** | Hub 客户端把文件字节写到本地磁盘。不解释、不读取 | 否（字节落盘，但不被本流程读取） |
| L2 | **计算哈希** | 以二进制只读方式读取字节并计算 SHA-256；不解析格式 | 字节被读取，但不被解释 |
| L3 | **打开解析** | 用 `pyarrow` 打开：读取 schema、行数、row group 元数据 | 是（结构） |
| L4 | **读取文本** | 物化 `text` 列的值（编码、扫描、统计、拟合、评估都属此级） | 是（内容） |

**R6/T1 中的「未被打开」（PROPOSED CLARIFICATION，对应 S1、S6）：** 对 validation/test，在事件 `tokenizer_hash_logged`（定义见 2.3）之前，**不允许任何 L1 及以上的操作**；允许 L0。理由：这样「未打开」可以由**文件在本地磁盘上不存在**这一客观事实来证明（见 3.4 的缺席见证），而不是依赖易被改写的时间戳。
替代选项（供负责人选择，同样 PROPOSED / NOT APPROVED）：**选项 B**——允许 L1、L2（下载并计算哈希，以保留 v1 §3.2 第 1 步的字面做法），但禁止 L3、L4。B 的代价：无法再用「文件不存在」证明未打开，只能依赖事件日志。草案默认采用严格版本（L1 以上禁止）。

### 2.2 阶段表

| 阶段 | 内容 | 允许对 train | 允许对 validation/test |
|---|---|---|---|
| **S0 预检（离线）** | 配置 SHA-256、冻结清单 10/10、环境快照、仓库 clean、`mode=real` 检查、运行目录为新目录 | — | — |
| **S1 元数据** | 解析固定修订（返回 SHA 必须等于冻结值，禁止 `main`）；列 `wikitext-2-raw-v1/` 目录；记录三个 split 各自的路径、大小、LFS `sha256`、`blob_id`；README 的元数据 | L0 | L0 |
| **S2 train 获取** | 下载 train 与 README；计算 train 哈希并与 LFS `sha256` 比较（不符 FAIL）；记录 `R6.pre` 哈希；切换离线 | L0–L2 | L0 |
| **S3 Tokenizer** | T7（train 部分）扫描；仅 train 合格行拟合；保存；重复拟合；T2/T4(train)/T5(train)/T6；写 `tokenizer_hash_logged` | L0–L4 | **无 L1+** |
| **S4 held-out 审计** | 联网下载 validation/test；计算哈希并与 LFS `sha256` 比较；T7（val/test 部分）；R7 审计；T4/T5（val/test）；写 `heldout_audit_done` | L0–L4（已有） | L0–L4，**仅限 R7 允许的输出** |
| **S5 D1 读取** | 冻结的 Driver（读取器、验证器、负例）在 train 窗口上运行；运行前后各一次 R6 哈希与 `stat` 快照 | L2（快照）+ 冻结代码的读取 | 不涉及 |
| **S6 独立验收** | 新的独立验收脚本核对全部清单、事件日志与各闸门（第 6 节） | — | — |

S4 与 S5 的先后顺序不影响任何闸门（Driver 只需要 train 与 Tokenizer）。草案采用 S4 先于 S5，使清单引用关系保持单向（见第 5 节）。

### 2.3 事件日志（对应 S6）`【PROPOSED / NOT APPROVED】`

- 文件 `evidence/event_log.jsonl`，JSON Lines，**只追加**。每行包含：`seq`（从 0 连续递增）、`utc`、`event`、`split`（或 `null`）、`level`（L0–L4）、`path`（相对路径或 `null`）、`sha256`（如有）、`prev_line_sha256`（上一行的 SHA-256，首行为全零）。
- 事件名集合：`meta_query`、`download_start`、`download_done`、`hash_done`、`parse_open`、`text_read`、`fit_start`、`fit_done`、`tokenizer_hash_logged`、`absence_witness`、`heldout_audit_done`、`pre_read_snapshot`、`post_read_snapshot`、`driver_start`、`driver_exit`、`interrupted`。
- **`tokenizer_hash_logged`**：写入 `tokenizer.json` 的 SHA-256；它是 T1/R6 的分界点 `t_fix`。其前一行必须是 `absence_witness`（见 3.4）。
- 日志本身以「行内哈希链」防止插入、删除、重排；日志中间任何一行被改动，后续链失效 → FAIL。时间戳只用于信息，**判定依据是 `seq` 与哈希链**，不是时间戳（修正 S6「按日志时间戳」的弱点）。
- 记录器是一个极小的单写入者模块，由获取与拟合脚本共同使用；它自身需要独立的单元测试。该模块尚未编写。

## 3. validation/test 完整性与 Tokenizer 拟合隔离 `【PROPOSED / NOT APPROVED】`

| 编号 | 要求 |
|---|---|
| I1 | `tokenizer_hash_logged` 之前，validation/test 没有任何 L1+ 事件（事件日志证明）；允许 L0 |
| I2 | 拟合语料**只能**由 train 合格行构成（v1 §4.1「拟合输入」）。记录喂入行数与语料 SHA-256（语料 = 按行号顺序的 NFC 文本的 UTF-8 字节，各行以固定的 `\x00` 分隔后哈希；分隔符属本草案的具体化） |
| I3 | 拟合模块不接受 validation/test 路径作为参数，运行时断言文件名属于 train；独立静态检查：拟合模块源码不出现 validation/test 的路径常量 |
| I4 | **缺席见证（对应 S1/S6）：** 写 `tokenizer_hash_logged` 之前，记录数据目录的完整文件清单及其哈希（`absence_witness`）；清单里不得有 validation/test 文件 |
| I5 | `tokenizer_hash_logged` 之后才允许 S4。S4 对 validation/test 的文件哈希必须等于 S1 记录的 LFS `sha256`（不符 FAIL；S9 的无 LFS 情形见 7 节待裁决事项 R3-D06） |
| I6 | held-out 审计脚本的输出只允许：文件哈希、行数、合格行数、一级标题行数、Token 计数（两种口径，见 4.2）、最大 Token ID、是否出现 ID 0、round-trip 不一致行数、特殊字符串出现次数。**不得**输出任何行文本、任何 Token ID 序列、任何逐行统计。由输出键白名单加静态检查保证 |
| I7 | 「不用于拟合、不用于任何模型评估」是组织约束；机器可核对的替代物是 I3 与 I6 加上「held-out 数据文件的路径不出现在任何训练、评估代码中」的静态检查。**这三项只能证明代码层面没有这样做，不能证明没有人手工使用**；该局限在验收记录中明示 |
| I8（待裁决） | v1 §5.5 R7 写明「D3 的最终 test 评估仍是后续一次性事项」。对 test 做计数与 round-trip 是否影响这个「一次性」属性，原文没有裁决。见 R3-D08 |

## 4. 验收矩阵（正常与异常输入）`【PROPOSED / NOT APPROVED】`

状态词沿用 v1 §6：完整性不符 → FAIL；输入缺失、不可达、前置条件不满足 → BLOCKED。「承担者」中的「新」指尚未编写的独立脚本；「冻」指已冻结的代码。

### 4.1 R6

| 编号 | 检查 | 正常输入 → 期望 | 异常输入 → 期望 | 证据 | 承担者 |
|---|---|---|---|---|---|
| R6.1 | **读前**：Driver 启动前计算 train 文件 SHA-256，须等于 S2 的哈希、LFS `sha256` 与 `runtime_manifest.parquet_sha256` | 三者一致 → PASS | 文件被换/截断/内容改一字节 → FAIL `R6_PRE_HASH_MISMATCH`；文件不存在 → BLOCKED | `pre_read_snapshot` 事件 | 新（冻结 Driver 不做） |
| R6.2 | **读后**：Driver 退出后再算一次，等于读前 | 一致 → PASS | 运行期间被改 → FAIL `R6_POST_HASH_MISMATCH` | `post_read_snapshot` 事件 | 新；冻结验证器的 `fsha(src_path)==manifest` 是其中一个冗余检查 |
| R6.3 | **粒度（PROPOSED CLARIFICATION，对应 S3）：** 读前/读后各针对「整个冻结 Driver 运行」一次，加 `stat`（大小、`mtime_ns`、inode）快照；不要求每个子进程各一次，因为冻结 Driver 不能改动 | `stat` 与哈希均不变 → PASS | `stat` 或哈希任一变化 → FAIL | 同上 | 新。**局限：** 运行中途被换后再换回，只用读前读后哈希无法发现；`stat` 的 `mtime_ns`/inode 能部分发现。该局限需负责人接受（R3-D03） |
| R6.4 | **隔离**：I1、I4 | 无 val/test 的 L1+ 事件在 `t_fix` 之前，缺席见证无 val/test 文件 → PASS | 之前出现任何 val/test L1+ 事件，或见证里有该文件 → FAIL `R6_HELDOUT_TOUCHED_EARLY`；日志缺失或哈希链断 → FAIL `EVENT_LOG_BROKEN`；日志不存在 → BLOCKED | 事件日志 | 新 |
| R6.5 | **身份绑定**：S1 的路径/oid ↔ S2 下载的文件 ↔ 清单 | 全部一致 → PASS | 路径不属于 `wikitext-2-raw-v1/`、split 与文件名不符、非「每个 split 恰好一个 Parquet」→ BLOCKED（v1 §3.1 原规则）；哈希与 oid 不符 → FAIL | `hub_metadata.json`、`train_data_manifest.json` | 新 |

### 4.2 R7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| R7.1 | 文件哈希等于 LFS `sha256` | 一致 → PASS | 不符 → FAIL；文件缺失/下载失败/不可达 → BLOCKED | 新 |
| R7.2 | 行数：Parquet 元数据 `num_rows` 与实际物化行数相等 | 相等 → PASS | 不等 → FAIL；`text` 列缺失或某行非字符串 → BLOCKED（沿用冻结读取器对 `NON_STRING_TEXT` 的处理） | 新 |
| R7.3 | 合格行数（`text.strip()!=""`）、一级标题行数 | 两个**互相独立**的实现给出相同结果 → PASS（PROPOSED：沿用 R2 的双实现原则） | 两个实现不一致 → FAIL | 新（两份） |
| R7.4 | **Token 计数口径（PROPOSED CLARIFICATION，对应 S4）：** 同时记录 `tokens_total = Σ len(tokens(r))`（含 EOS 前缀，且「第一个合格行」按每个 split 单独判定）与 `tokens_encode_only = Σ len(encode(NFC(text)))`，二者差必须等于该 split 的 EOS 前缀个数 | 恒等式成立 → PASS | 不成立 → FAIL | 新 |
| R7.5 | round-trip（即 T4 在 val/test 上）：`decode(encode(NFC(x))) == NFC(x)`，不一致行数为 0 | 0 → PASS | >0 → FAIL（记录个数，不记录内容）；decode 抛异常 → FAIL | 新 |
| R7.6 | 输出白名单（I6）与静态检查（I3、I7） | 输出键全部在白名单内；静态检查通过 → PASS | 出现白名单外的键或文本/ID 序列 → FAIL | 新 |
| R7.7 | **中断行为（PROPOSED，对应 S5）：** 审计中途被中断 → `BLOCKED(interrupted)`，写 `interrupted` 事件；已写出的部分结果文件命名为 `*.partial` 且**永不被使用**；**不自动续跑、不重试**；重新运行必须使用新的运行目录并产生新的事件日志 | 无中断 → 不适用 | 中断后遗留 `.final` 文件而无 `heldout_audit_done` 事件 → FAIL | 新 |

### 4.3 T1–T7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| T1 | train-only 拟合；val/test 未被打开（I1–I4） | 语料行数 = train 合格行数，语料哈希已记录，缺席见证干净 → PASS | 喂入行数不符、语料哈希缺失 → FAIL；含 val/test 路径 → FAIL | 新（拟合脚本 + 验收脚本） |
| T2 | 特殊 ID 为 0/1/2；`259 < 实际词表 ≤ 4096` | → PASS | V=259（没学到合并规则）、V>4096、特殊 ID 错 → FAIL | 新 |
| T3 | 重复拟合：至少再拟合一次（**至少一次在独立进程**，PROPOSED CLARIFICATION），`tokenizer.json` SHA-256 相同 | 相同 → PASS | 不同 → FAIL；按 v1 §4.3 不得因此改变其他冻结项，D1 就此停止 | 新 |
| T4 | round-trip：train 在 S3，val/test 在 S4 | 不一致行数 0 → PASS | >0 → FAIL | 新 |
| T5 | ID 范围 `[0, 词表)` 且不含 ID 0，对**全体**合格行（不是只窗口） | → PASS | 出现 0 或越界 → FAIL | 新（冻结读取器只检查窗口的 2048 行） |
| T6 | 文件身份：保存、记录哈希；之后每次读取先核对 | 冻结读取器与验证器每次都核对（已实现）→ PASS | 哈希不符 → 读取器 `TOKENIZER_FILE_HASH_MISMATCH`（BLOCKED）或游标 `TOKENIZER_HASH_MISMATCH`（LR2 已覆盖） | 冻（核对）+ 新（记录） |
| T7 | 三个特殊字符串在全部 NFC 文本中出现 0 次；train 部分在拟合之前，val/test 部分在 `t_fix` 之后（**PROPOSED AMENDMENT**，取代 R1 §8 的「先检查三个 split」，对应 S2；拟合只受 train 影响，所以事后扫描 val/test 不影响拟合） | 全部 0 → PASS | 任何一处 >0 → BLOCKED（沿用 R1 §8）；train 在拟合前检查出 >0 → BLOCKED 且不拟合 | 新；冻结读取器只检查窗口 |

## 5. Manifest：单向哈希引用，不允许循环 `【PROPOSED / NOT APPROVED】`

**规则：** 每个工件只能引用**时间上更早生成**的工件的 SHA-256；不能引用自身，不能引用后来生成的工件。每个清单包含 `produced_at_seq`（事件日志中的 `seq`）和 `refs`（名称 → 哈希）。验收脚本拓扑排序校验：引用图无环，且每个被引用哈希等于磁盘上对应文件的实际哈希。

```
A1 hub_metadata.json            (S1)   refs: —
A2 train_data_manifest.json     (S2)   refs: A1
A3 event_log.jsonl              (全程，只追加)   行内哈希链；其他工件引用的是「到某一 seq 为止的前缀哈希」，不是整文件
A4 tokenizer_manifest.json      (S3)   refs: A1, A2, A3[0..seq(tokenizer_hash_logged)]
A5 heldout_manifest.json        (S4)   refs: A1, A4, A3[0..seq(heldout_audit_done)]
A6 runtime_manifest.json        (S5前) refs: A2, A4, A5
      （保留冻结读取器使用的三个键 parquet_sha256 / tokenizer_sha256 / actual_vocab_size；
        可选的 formal 块里的 tokenizer_fit_manifest_sha256 取 A4 的 SHA-256，lfs_oid_parquet 取 A1 中 train 的值）
A7 driver evidence + D1_DECISION  (S5)   refs: A6（运行时清单哈希已被冻结 Driver 记入每个 trace 的 run 记录）
A8 acceptance record            (S6)   refs: A1…A7 的最终哈希
```

- `A3` 之所以引用前缀：事件日志在 `tokenizer_hash_logged` 之后还会继续增长，若 A4 引用整文件，就形成「A4 ← A3 ← A4」的循环；引用前缀并记录 `seq` 可避免。
- 冻结读取器和验证器只读取 A6 的三个键，**额外的键会被忽略**（这是对现有实现的核对，不是新要求）；不改它们的代码。
- `formal` 块里的值仍然是**自述**；真正的核对由 S6 的验收脚本对照 A1/A2/A4 重新计算（第 6 节）。

## 6. `FORMAL_D1_CANDIDATE` 不是 D1 PASS；不修改冻结 Driver 的独立验收方案 `【PROPOSED / NOT APPROVED】`

1. **性质：** `FORMAL_D1_CANDIDATE` 是冻结 Driver 写进决定文件的记账标签（`d1_driver.py` 的 `identity()`、`d1_formal_experiment`）。它只代表「配置 `status` 为 `FROZEN`，且清单里有一个自洽的 `formal` 块」。它**不**代表数据或 Tokenizer 经过了任何核对；决定文件中的 `d1_overall` 恒为 `NOT_DECLARED__PIPELINE_INCOMPLETE`。已知它可以被一个没有真实数据支撑的清单满足。
2. **独立验收脚本（新，尚未编写；`d1_acceptance.py` 为暂定名）：** 输入是运行目录。它**不信任** `identity` 与 `formal` 块，而是从工件重新核对：
   - 引用图无环，所有哈希与磁盘一致；
   - A1 的元数据与冻结配置（repo、revision、`wikitext-2-raw-v1/`）相符，三个 split 各一个 Parquet；
   - 事件日志哈希链完整，I1/I4 成立；
   - R6.1–R6.5、R7.1–R7.7、T1–T7 全部有证据并通过；
   - 冻结清单 10/10、配置 `status`、环境快照与 Python 完整版本；
   - Driver 的决定文件中 `read_resume`、`negatives_meta` 的分项结论，以及运行数据的 `identity`；
   - `authorization_ref` 必须能解析为仓库里已提交的授权文件，并记录该文件的 SHA-256（`【PROPOSED】`；授权文件的形式由负责人决定）。
3. **输出：** 逐闸门的 PASS / FAIL / BLOCKED / NOT TESTED 列表和 `ALL_GATES_PASS_CANDIDATE` 或 `NOT_ACCEPTED`。**脚本本身不宣布 D1 PASS**：D1 的结论只能由项目负责人在 ChatGPT 独立复审后作出（与冻结 Driver 的 `declared` 字段一致）。
4. **不修改冻结 Driver 的原因与代价：** 冻结代码已通过验收，任何改动都触发新的冻结与重新验收。代价是：R6 的读前读后核对只能在 Driver 之外进行（R6.3 的局限），且 Driver 的 `not_tested` 清单仍是写死的文字——验收脚本必须自己判断哪些闸门已有证据，而不能依赖该清单。

## 7. 待项目负责人裁决事项（均为 `PROPOSED / NOT APPROVED`）

| ID | 事项 | 草案建议 | 备选 |
|---|---|---|---|
| R3-D01 | S1/S2 的消解：validation/test 的 L1+ 操作何时允许 | 严格：`t_fix` 之前禁止任何 L1+（2.1）；分阶段获取（2.2） | 选项 B：允许下载并算哈希，但禁止解析与读文本 |
| R3-D02 | T7 的 val/test 部分后移到 `t_fix` 之后（取代 R1 §8「先检查三个 split」） | 采纳 | 保留原文：先扫描三个 split，同时放弃「未被打开」 |
| R3-D03 | R6 的粒度与局限 | 整个 Driver 运行前后各一次哈希 + `stat`；接受「运行中途被换回」无法发现的局限 | 要求每个子进程前后各一次（需改冻结 Driver，触发重新冻结） |
| R3-D04 | R7 的 Token 计数口径 | 两种口径都记录并要求恒等式（4.2 R7.4） | 只选其一 |
| R3-D05 | 中断行为（S5） | `BLOCKED(interrupted)`、`.partial`、不续跑不重试、新运行目录（4.2 R7.7） | 允许在阶段边界续跑 |
| R3-D06 | 无 LFS `sha256`（S9）时的替代标准 | 以 Hub 返回的 `blob_id`（git blob 的 SHA-1）本地重算校验；若两者都没有则 BLOCKED | 直接 BLOCKED |
| R3-D07 | 30 分钟预算范围（S7） | 字面解释：从第一个 `meta_query` 到最后一个阶段共用 30 分钟，由事件日志的 `seq` 时间戳计量；超时 BLOCKED，不重试 | 选项 2：网络阶段（下载）与计算阶段（拟合、审计、Driver）各自 30 分钟（修改原文「依赖网络、无法预测」的处理） |
| R3-D08 | 是否在 D1 阶段对 test 做计数/round-trip（I8） | 做（v1 R7 字面要求），在验收记录中说明它不泄露内容 | 推迟 test 的审计到 D3 的一次性评估时 |
| R3-D09 | 事件日志与新脚本集的授权与重新冻结流程 | 新脚本集（记录器、获取、拟合、审计、清单生成、验收）各自独立分支、独立测试、整体再冻结一次 | 分批冻结 |
| R3-D10 | 授权文件形式（第 6 节 2 的 `authorization_ref`） | 仓库里已提交的授权记录文件 + 其 SHA-256 | 由负责人另定 |
| R3-D11 | `tokenizer.json` 能否提交公开仓库（v1 §3.5、§11，沿用） | 仍只提交哈希与统计 | — |

## 8. 本草案不改变的内容（核对清单）

- v1/R1/R2 全文、读取器、验证器、驱动器、`d1_env_manifest.py`、`d1_selftest_data.py`、测试、`D1_FROZEN_CONFIG.json`（`status = FROZEN`）、`D1_CODE_SHA256SUMS`、Codespaces 证据：**未改动**。
- 数据窗口（2048 个合格行）、`seq_len=64`、块长 65、游标 `d1_cursor_v2`、九步检查、P1–P5、LR1–LR9、CR1–CR3、哈希链、Tokenizer 行为冻结（R1 §8 除 T7 一行）、静态公式 `P(V)=206,976+320V`：**未改动**。
- 30 分钟的**数值**与 Driver 内的超时常量：**未改动**（S7 只涉及范围）。
- 本草案不授权任何下载、拟合、D1 执行、训练、GPU 或 D2/D3。

## 9. 文档一致性核对（本次执行）

对第 1 节每条引文，用脚本在源文件中逐字查找；同时核对 v1/R1/R2 的 SHA-256 未变。结果见检查点文档 `F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。

## 10. 下一条唯一研发指令

等待 ChatGPT 复审本草案，由项目负责人逐项裁决第 7 节的 R3-D01…R3-D11。批准后才可把 R3 转为正式修订文件，再另行授权任务序列的第一步。在此之前：不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。

---

**最终状态：`DRAFT / PENDING CHATGPT REVIEW`。** 未标记 FROZEN，未标记 PASS。
