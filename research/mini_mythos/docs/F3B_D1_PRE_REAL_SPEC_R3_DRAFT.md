# F3-B / D1 — 真实 D1 执行前规范 R3（草案）

**状态：`R3 DRAFT / PENDING OWNER DECISION`（修订 2，响应 F3B-D1-SPEC-R3-REVIEW-002）。不是 FROZEN，不是 PASS，不是任何授权。**

任务：F3B-D1-SPEC-R3-001（规范冲突消解）→ 修订 2：F3B-D1-SPEC-R3-REVIEW-002（证据可信性与执行预算）。日期：2026-10-26。起草者：Claude Code。
修订 2 基准：`94601916bc1fd0faa33b9f819b3a0d8cc7d61dc5`（首版草案所在提交，保留在 Git 历史中，未被覆盖）。
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
6. **第 7 节的 11 项裁决是项目负责人待批准的决策记录**。「草案建议」栏只是建议，**不是**已批准规范；只有当「状态」栏变为 `APPROVED` 并写明决定人与日期，且 R3 转为正式修订文件之后，才产生约束力。修订 2 在多处细化了建议，但没有把任何一项变成已批准。

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
| **S0 预检（离线）** | 配置 SHA-256、冻结清单 10/10、环境快照、仓库 clean、`mode=real` 检查、运行目录为新目录；**预算账本 `open` 行（K0）写入并外部固定**（11.1、11.2）；Hub/Xet 缓存目录设为新建空目录（11.4） | — | — |
| **S1 元数据** | 解析固定修订（返回 SHA 必须等于冻结值，禁止 `main`）；列 `wikitext-2-raw-v1/` 目录；记录三个 split 各自的路径、大小、LFS `sha256`、`blob_id`、Xet 元数据（如有），并按 11.5 机械判定每个文件的 `integrity_basis`（不明 → BLOCKED）；README 的元数据 | L0 | L0 |
| **S2 train 获取** | 下载 train 与 README；按 11.5 的完整性基础核对 train 哈希（同算法比较，不符 FAIL，基础不明 BLOCKED）；记录 `R6.pre` 哈希；切换离线（只针对 Hub 客户端，见 S8） | L0–L2 | L0 |
| **S3 Tokenizer** | T7（train 部分）扫描；仅 train 合格行拟合；保存；重复拟合；T2/T4(train)/T5(train)/T6；写 `absence_witness`（11.4）与 `tokenizer_hash_logged`；计算 `P_k1` 并**外部固定 K1**（11.2） | L0–L4 | **无 L1+** |
| **S4 held-out 审计** | K1 已固定后才允许联网下载 validation/test；按 11.5 同算法核对哈希；T7（val/test 部分）；R7 审计；T4/T5（val/test）；写 `heldout_audit_done` | L0–L4（已有） | L0–L4，**仅限 R7 允许的输出** |
| **S5 D1 读取** | 冻结的 Driver（读取器、验证器、负例）在 train 窗口上运行，由**外层监督器**按预算账本的剩余时间限时（11.1）；运行前后各一次 R6 哈希与 `stat` 快照 | L2（快照）+ 冻结代码的读取 | 不涉及 |
| **S6 独立验收** | 新的独立验收脚本核对全部清单、事件日志与外部固定记录、预算账本与各闸门（第 6 节） | — | — |

S4 与 S5 的先后顺序不影响任何闸门（Driver 只需要 train 与 Tokenizer）。草案采用 S4 先于 S5，使清单引用关系保持单向（见第 5 节）。

### 2.3 事件日志（对应 S6）`【PROPOSED / NOT APPROVED】`

- 文件 `evidence/event_log.jsonl`，JSON Lines，**只追加**。每行是规范 JSON（键排序、紧凑分隔符、ASCII 转义）加 `\n`，包含：`seq`（从 0 连续递增，**只表示顺序，不是时间**）、`utc`（墙钟，**仅供信息，不用于计量，也不用于判定**）、`event`、`split`（或 `null`）、`level`（L0–L4）、`path`（相对路径或 `null`）、`sha256`（如有，带算法标签，见 11.5）、`prev`（上一行原始字节（含换行）的 SHA-256 十六进制；首行为 64 个 `0`）。
- 事件名集合：`meta_query`、`download_start`、`download_done`、`hash_done`、`parse_open`、`text_read`、`fit_start`、`fit_done`、`tokenizer_hash_logged`、`absence_witness`、`heldout_audit_done`、`pre_read_snapshot`、`post_read_snapshot`、`driver_start`、`driver_exit`、`interrupted`。
- **`tokenizer_hash_logged`**：写入 `tokenizer.json` 的 SHA-256；它是 T1/R6 的分界点 `t_fix`。其前一行必须是 `absence_witness`（见 3.4）。
- **哈希链只提供完整性检测，不证明日志真实**（修订 2，见 11.2）：它能发现「没有同步重算整条链」的修改，但任何能重写文件的人都可以重算整条链。因此日志的可信度来自关键前缀的**外部固定**（11.2），判定依据是 `seq` 的顺序、链的完整性和外部固定的前缀哈希；时间戳与 `seq` 都**不用于耗时计量**——耗时只来自预算账本（11.1）。
- 记录器是一个极小的单写入者模块，由获取与拟合脚本共同使用；它自身需要独立的单元测试。该模块尚未编写。
- **前缀哈希（对应 11.2、第 5 节）：** `P_k = SHA-256(第 0 行至第 k 行的原始字节)`。它只依赖 ≤ k 的行，因此引用它不会产生循环。预算账本 `budget_ledger.jsonl` 用同样的行格式与前缀哈希定义。

## 3. validation/test 完整性与 Tokenizer 拟合隔离 `【PROPOSED / NOT APPROVED】`

| 编号 | 要求 |
|---|---|
| I1 | `tokenizer_hash_logged` 之前，validation/test 没有任何 L1+ 事件（事件日志证明）；允许 L0 |
| I2 | 拟合语料**只能**由 train 合格行构成（v1 §4.1「拟合输入」）。记录喂入行数与语料 SHA-256（语料 = 按行号顺序的 NFC 文本的 UTF-8 字节，各行以固定的 `\x00` 分隔后哈希；分隔符属本草案的具体化） |
| I3 | 拟合模块不接受 validation/test 路径作为参数，运行时断言文件名属于 train；独立静态检查：拟合模块源码不出现 validation/test 的路径常量 |
| I4 | **缺席见证（修订 2，对应 S1/S6；完整规则与局限见 11.4）：** 写 `tokenizer_hash_logged` 之前，对**明确列出的受控目录集合**做只读扫描（路径、大小、类型，**不读取内容、不计算内容哈希**），要求其中没有 validation/test 文件的任何迹象；它证明的是「该时刻、该范围内未发现」，**不证明「从未访问」** |
| I5 | `tokenizer_hash_logged` 与 K1 外部固定（11.2）之后才允许 S4。S4 对 validation/test 的文件摘要必须与 S1 记录的**同算法**摘要相等（完整性基础表见 11.5；不符 FAIL；基础不明或元数据不足 → BLOCKED） |
| I6 | held-out 审计脚本的输出只允许：文件哈希、行数、合格行数、一级标题行数、Token 计数（两种口径，见 4.2）、最大 Token ID、是否出现 ID 0、round-trip 不一致行数、特殊字符串出现次数。**不得**输出任何行文本、任何 Token ID 序列、任何逐行统计。由输出键白名单加静态检查保证 |
| I7 | 「不用于拟合、不用于任何模型评估」是组织约束；机器可核对的替代物是 I3 与 I6 加上「held-out 数据文件的路径不出现在任何训练、评估代码中」的静态检查。**这三项只能证明代码层面没有这样做，不能证明没有人手工使用**；该局限在验收记录中明示 |
| I8（待裁决） | v1 §5.5 R7 写明「D3 的最终 test 评估仍是后续一次性事项」。对 test 做计数与 round-trip 是否影响这个「一次性」属性，原文没有裁决；若做，用途被 11.6 严格限定。见 R3-D08 |

## 4. 验收矩阵（正常与异常输入）`【PROPOSED / NOT APPROVED】`

状态词沿用 v1 §6：完整性不符 → FAIL；输入缺失、不可达、前置条件不满足 → BLOCKED。「承担者」中的「新」指尚未编写的独立脚本；「冻」指已冻结的代码。

### 4.1 R6

| 编号 | 检查 | 正常输入 → 期望 | 异常输入 → 期望 | 证据 | 承担者 |
|---|---|---|---|---|---|
| R6.1 | **读前**：Driver 启动前计算 train 文件 SHA-256，须等于 S2 的哈希、LFS `sha256` 与 `runtime_manifest.parquet_sha256` | 三者一致 → PASS | 文件被换/截断/内容改一字节 → FAIL `R6_PRE_HASH_MISMATCH`；文件不存在 → BLOCKED | `pre_read_snapshot` 事件 | 新（冻结 Driver 不做） |
| R6.2 | **读后**：Driver 退出后再算一次，等于读前 | 一致 → PASS | 运行期间被改 → FAIL `R6_POST_HASH_MISMATCH` | `post_read_snapshot` 事件 | 新；冻结验证器的 `fsha(src_path)==manifest` 是其中一个冗余检查 |
| R6.3 | **粒度与限定语（PROPOSED CLARIFICATION，对应 S3；修订 2，见 11.3）：** 读前/读后各针对「整个冻结 Driver 运行」一次，加 `stat`（大小、`mtime_ns`、`ctime_ns`、inode）快照（`ctime_ns` 由内核维护，普通用户不能回写，所以「改后又改回」通常也会让它变化）。**该检查只能证明两个检查时刻的文件状态相同，不能证明运行期间每一次读取（A、B 的 6 段、12 个负例、验证器的多次读取）读到的内容一致**；验收记录必须写出这句限定语。可选更强控制见 11.3 | 两个时刻的哈希与 `stat` 均相同 → PASS（仅限该限定语所述含义） | 任一不同 → FAIL `R6_POST_HASH_MISMATCH` 或 `R6_STAT_CHANGED`（良性的 `chmod`/硬链接也会改 `ctime`，保守判 FAIL，重新运行）。**已记录的预期漏检用例：** 保持 `ctime` 不变的 ABA（需要 root、回拨系统时钟或直接写块设备），以及目标文件系统不维护 `ctime` 的情形（**目标文件系统 NOT TESTED**）；它们不作为通过依据，只作为残余风险。选用 11.3 的监视控制可缩小但不消除该风险 | 同上 | 新 |
| R6.4 | **隔离**：I1、I4（受控范围内的缺席见证，11.4）、K1 外部固定（11.2） | 无 val/test 的 L1+ 事件在 `t_fix` 之前，受控范围内缺席见证无 val/test 迹象，K1 固定记录存在且前缀哈希与重算一致 → PASS | 之前出现任何 val/test L1+ 事件，或见证命中 → FAIL `R6_HELDOUT_TOUCHED_EARLY`；日志哈希链断、或前缀哈希与外部固定记录不符 → FAIL `EVENT_LOG_BROKEN`；日志或 K1 固定记录不存在、无法核对远端 → BLOCKED | 事件日志、固定记录 | 新 |
| R6.5 | **身份绑定**：S1 的路径/oid ↔ S2 下载的文件 ↔ 清单 | 全部一致 → PASS | 路径不属于 `wikitext-2-raw-v1/`、split 与文件名不符、非「每个 split 恰好一个 Parquet」→ BLOCKED（v1 §3.1 原规则）；哈希与 oid 不符 → FAIL | `hub_metadata.json`、`train_data_manifest.json` | 新 |

### 4.2 R7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| R7.1 | 文件摘要与 A1 中**同算法**的摘要相等（完整性基础见 11.5） | 相等 → PASS | 不符 → FAIL；基础不明/元数据不足、文件缺失/下载失败/不可达 → BLOCKED | 新 |
| R7.2 | 行数：Parquet 元数据 `num_rows` 与实际物化行数相等 | 相等 → PASS | 不等 → FAIL；`text` 列缺失或某行非字符串 → BLOCKED（沿用冻结读取器对 `NON_STRING_TEXT` 的处理） | 新 |
| R7.3 | 合格行数（`text.strip()!=""`）、一级标题行数 | 两个**互相独立**的实现给出相同结果 → PASS（PROPOSED：沿用 R2 的双实现原则） | 两个实现不一致 → FAIL | 新（两份） |
| R7.4 | **Token 计数口径（PROPOSED CLARIFICATION，对应 S4）：** 同时记录 `tokens_total = Σ len(tokens(r))`（含 EOS 前缀，且「第一个合格行」按每个 split 单独判定）与 `tokens_encode_only = Σ len(encode(NFC(text)))`，二者差必须等于该 split 的 EOS 前缀个数 | 恒等式成立 → PASS | 不成立 → FAIL | 新 |
| R7.5 | round-trip（即 T4 在 val/test 上）：`decode(encode(NFC(x))) == NFC(x)`，不一致行数为 0 | 0 → PASS | >0 → FAIL（记录个数，不记录内容）；decode 抛异常 → FAIL | 新 |
| R7.6 | 输出白名单（I6）、静态检查（I3、I7）与 test 用途限制（11.6） | 输出键全部在白名单内；静态检查通过；`usage_declaration` 存在 → PASS | 出现白名单外的键或文本/ID 序列、审计模块引用模型/训练代码 → FAIL | 新 |
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

## 5. Manifest 与日志前缀：单向哈希引用，不允许循环 `【PROPOSED / NOT APPROVED】`（修订 2：已逐条检查，见 11.7）

**规则：** 每个工件只能引用**更早生成**的工件（或日志/账本的某个**前缀**）的 SHA-256；不能引用自身，不能引用后来生成的东西。每个清单包含 `produced_at_seq`（日志里的顺序号，只表示顺序）和 `refs`（名称 → 带算法标签的摘要）。验收脚本按下面的层级号校验：每条引用边必须指向**严格更低**的层级，且被引用摘要等于磁盘或固定记录上的实际值。

```
层级  节点                                      引用（→ 只能指向更低层级）
 0    A1  hub_metadata.json            (S1)     —
 0    BP0 预算账本前缀 [0..0]（`open` 行）          —
 1    PIN0 pin_K0.json                          → BP0
 1    A2  train_data_manifest.json     (S2)     → A1
 2    LP1 事件日志前缀 [0..k1]  (k1 = tokenizer_hash_logged 所在行；其前一行是 absence_witness)   —（前缀本身不含任何后来的摘要）
 3    PIN1 pin_K1.json   (外部固定 LP1)         → LP1
 4    A4  tokenizer_manifest.json      (S3)     → A1, A2, LP1, PIN1
 5    LP2 事件日志前缀 [0..k2]  (k2 = heldout_audit_done 所在行)
 6    PIN2 pin_K2.json                          → LP2
 7    A5  heldout_manifest.json        (S4)     → A1, A4, LP2, PIN2
 8    A6  runtime_manifest.json        (S5 前)  → A2, A4, A5
            （保留冻结读取器使用的三个键 parquet_sha256 / tokenizer_sha256 / actual_vocab_size；
              可选 formal 块里的 tokenizer_fit_manifest_sha256 取 A4 的摘要，lfs_oid_parquet 取 A1 中 train 的值）
 9    A7  driver evidence + D1_DECISION (S5)    → A6   （冻结 Driver 已把 manifest_sha256 记入每个 trace 的 run 记录）
10    LP3 事件日志前缀 [0..k3]  (k3 = driver_exit 所在行)
11    PIN3 pin_K3.json                          → LP3
12    BP  预算账本前缀 [0..close]                —
13    PIN4 pin_K4.json                          → BP
14    A8  acceptance record            (S6)     → A1, A2, A4, A5, A6, A7, LP3, PIN0–PIN4, BP
```

- **事件日志与预算账本是增长的文件**，所以任何工件引用的都是**前缀节点**（LP1、LP2、LP3、BP），而不是整文件。若 A4 引用整个日志，就会形成「A4 ← 日志 ← 记录 A4 的 `manifest_written` 行 ← A4」的环；引用前缀并记录 `k` 可避免。
- **前缀哈希的计算方式（唯一定义）：** 日志有 `L_0 … L_n` 共 n+1 行，每行是规范 JSON 加换行，含 `prev` 字段；`P_k = SHA-256(L_0 ‖ L_1 ‖ … ‖ L_k 的原始字节串)`。写入顺序固定：先写第 `k` 行（如 `tokenizer_hash_logged`），再计算 `P_k`，再写 pin、再写工件，最后追加 `manifest_written` / `pin_pushed` 等记录这些工件摘要的行。这些后写的行属于 `P_{k'}`（`k' > k`），**不属于** `P_k`，因此不存在「工件包含自己所属前缀」的情况。
- 冻结读取器和验证器只读取 A6 的三个键，**额外的键会被忽略**（对 `d1_reader.py` / `d1_verifier.py` 的核对，不是新要求）；不改它们的代码。
- `formal` 块里的值仍然是**自述**；真正的核对由 S6 的验收脚本对照 A1/A2/A4 重新计算（第 6 节）。

## 6. `FORMAL_D1_CANDIDATE` 不是 D1 PASS；不修改冻结 Driver 的独立验收方案 `【PROPOSED / NOT APPROVED】`

1. **性质：** `FORMAL_D1_CANDIDATE` 是冻结 Driver 写进决定文件的记账标签（`d1_driver.py` 的 `identity()`、`d1_formal_experiment`）。它只代表「配置 `status` 为 `FROZEN`，且清单里有一个自洽的 `formal` 块」。它**不**代表数据或 Tokenizer 经过了任何核对；决定文件中的 `d1_overall` 恒为 `NOT_DECLARED__PIPELINE_INCOMPLETE`。已知它可以被一个没有真实数据支撑的清单满足。
2. **独立验收脚本（新，尚未编写；`d1_acceptance.py` 为暂定名）：** 输入是运行目录。它**不信任** `identity` 与 `formal` 块，而是从工件重新核对：
   - 引用图无环，所有哈希与磁盘一致；
   - A1 的元数据与冻结配置（repo、revision、`wikitext-2-raw-v1/`）相符，三个 split 各一个 Parquet；
   - 事件日志哈希链完整；关键前缀 K1–K3 与预算账本前缀 K4 的哈希与外部固定记录一致（11.2）；I1/I4 在其限定范围内成立（11.4）；预算账本证明总耗时 ≤ 预算，或标记 BLOCKED（11.1）；
   - R6.1–R6.5、R7.1–R7.7、T1–T7 全部有证据并通过；
   - 冻结清单 10/10、配置 `status`、环境快照与 Python 完整版本；
   - Driver 的决定文件中 `read_resume`、`negatives_meta` 的分项结论，以及运行数据的 `identity`；
   - `authorization_ref` 必须能解析为仓库里已提交的授权文件，并记录该文件的 SHA-256（`【PROPOSED】`；授权文件的形式由负责人决定）。
3. **输出：** 逐闸门的 PASS / FAIL / BLOCKED / NOT TESTED 列表和 `ALL_GATES_PASS_CANDIDATE` 或 `NOT_ACCEPTED`。**脚本本身不宣布 D1 PASS**：D1 的结论只能由项目负责人在 ChatGPT 独立复审后作出（与冻结 Driver 的 `declared` 字段一致）。
4. **不修改冻结 Driver 的原因与代价：** 冻结代码已通过验收，任何改动都触发新的冻结与重新验收。代价是：R6 的读前读后核对只能在 Driver 之外进行（R6.3 的局限），且 Driver 的 `not_tested` 清单仍是写死的文字——验收脚本必须自己判断哪些闸门已有证据，而不能依赖该清单。
5. **验收脚本的局限（修订 2）：** 它与被验收的脚本在同一信任域内运行；它能发现不一致、缺失和被固定记录证伪的改写，不能发现「如实记录了错误事实」或「绕过记录器」的行为。这些局限在每份验收记录中明示，并由 11.2 的外部固定与审核者的独立复核补充。

## 7. 待项目负责人裁决事项——决策记录（均为 `PROPOSED / NOT APPROVED`；状态：`PENDING OWNER DECISION`）

本表是**决策记录**。「草案建议」不是规范。每项的「状态」初始为 `PENDING OWNER DECISION`，「决定人 / 日期 / 决定」三栏留空，由项目负责人填写；ChatGPT 的审核意见与草案建议同样不构成批准。修订 2 更新了 D01、D03、D06、D07、D08、D09 的建议内容，**没有**批准任何一项。

| ID | 事项 | 草案建议（PROPOSED，非规范） | 备选 | 状态 | 决定人 / 日期 / 决定 |
|---|---|---|---|---|---|
| R3-D01 | S1/S2 的消解：validation/test 的 L1+ 操作何时允许；缺席见证的受控范围与局限（11.4） | 严格：`t_fix` 之前禁止任何 L1+（2.1）；分阶段获取（2.2）；缺席见证按 11.4，接受「不能证明从未访问」的局限 | 选项 B：允许下载并算哈希，但禁止解析与读文本 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D02 | T7 的 val/test 部分后移到 `t_fix` 之后（取代 R1 §8「先检查三个 split」） | 采纳 | 保留原文：先扫描三个 split，同时放弃「未被打开」 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D03 | R6 的粒度与局限；是否采用 11.3 的更强控制 | 整个 Driver 运行前后各一次哈希 + `stat`，**明示只证明两个检查时刻**；可选 C-1（私有只读副本）、C-3（inotify 监视，标准库 `ctypes`）；接受 ABA 漏检的残余风险 | 要求每个子进程前后各一次（需改冻结 Driver，触发重新冻结）；或选 C-2 `chattr +i` | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D04 | R7 的 Token 计数口径 | 两种口径都记录并要求恒等式（4.2 R7.4） | 只选其一 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D05 | 中断行为（S5） | `BLOCKED(interrupted)`、`.partial`、不续跑不重试、新运行目录（4.2 R7.7） | 允许在阶段边界续跑 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D06 | 完整性基础：LFS SHA-256、Git blob SHA-1、Xet 元数据的区分；元数据不足时的处理（11.5） | 仅接受 B-LFS；B-GIT / B-XET 在元数据语义未被受控验证前 **BLOCKED**；摘要带算法标签，禁止跨算法比较；先做仅 L0 的元数据验证任务（需单独授权） | 立即接受 B-GIT（需先证明该文件非 LFS/Xet，目前无法证明） | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D07 | 30 分钟预算：范围与**计时方式**（11.1） | 范围按字面：从预算账本 `open` 到 `close` 共用 30 分钟；计时用 `CLOCK_BOOTTIME` + `boot_id` + 墙钟交叉检查，**不用 `seq`**；主机重启、时钟异常或账本缺失 → `BLOCKED(budget_unprovable)`；外层监督器终止超限的冻结 Driver | 选项 2：网络阶段与计算阶段各自 30 分钟；或改用 `CLOCK_MONOTONIC`（不含挂起时间） | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D08 | 是否在 D1 阶段对 test 做审计，及其用途限制（11.6） | 做，且**仅限**完整性、Token 统计、round-trip、特殊字符串计数；**禁止**训练、模型选择、调参、质量评估等一切其他用途 | 推迟 test 的审计到 D3 的一次性评估时 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D09 | 新脚本集（记录器、预算账本与监督器、获取、拟合、审计、清单生成、验收、外部固定工具）的授权与重新冻结流程；外部固定方式（11.2：默认 Git 推送固定 + 审核者带外副本） | 各自独立分支、独立测试、整体再冻结一次 | 分批冻结；或要求签名提交/外部时间戳 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D10 | 授权文件形式（第 6 节的 `authorization_ref`） | 仓库里已提交的授权记录文件 + 其 SHA-256 | 由负责人另定 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D11 | `tokenizer.json` 能否提交公开仓库（v1 §3.5、§11，沿用） | 仍只提交哈希与统计 | — | PENDING OWNER DECISION | ____ / ____ / ____ |

## 8. 本草案不改变的内容（核对清单）

- v1/R1/R2 全文、读取器、验证器、驱动器、`d1_env_manifest.py`、`d1_selftest_data.py`、测试、`D1_FROZEN_CONFIG.json`（`status = FROZEN`）、`D1_CODE_SHA256SUMS`、Codespaces 证据：**未改动**。
- 数据窗口（2048 个合格行）、`seq_len=64`、块长 65、游标 `d1_cursor_v2`、九步检查、P1–P5、LR1–LR9、CR1–CR3、哈希链、Tokenizer 行为冻结（R1 §8 除 T7 一行）、静态公式 `P(V)=206,976+320V`：**未改动**。
- 30 分钟的**数值**与 Driver 内的超时常量：**未改动**（S7 / R3-D07 只涉及预算范围与计时方式）。
- 本草案不授权任何下载、拟合、D1 执行、训练、GPU 或 D2/D3。

## 9. 文档一致性核对（本次执行）

对第 1 节每条引文，用脚本在源文件中逐字查找；同时核对 v1/R1/R2 的 SHA-256 未变；并检查本稿内部：判定词、决策 ID、引用层级（无环）、残留的过期表述。结果见检查点文档 `F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。

## 11. 修订 2 的细则（响应 F3B-D1-SPEC-R3-REVIEW-002）`【PROPOSED / NOT APPROVED】`

本节给出第 2–7 节所引用的细则。每一条都标出**它能证明什么**与**不能证明什么**。凡涉及本环境之外的行为（目标文件系统、Hub 元数据字段语义、网络出口），一律标 `NOT VERIFIED` / `NOT TESTED`。

### 11.1 跨进程预算账本（对应 S7 / R3-D07）

**目标：** 把 v1 §8 的「30 分钟墙钟硬上限」在获取、拟合、审计、读取、验证**多个独立进程**之间计量，且不依赖事件日志的 `seq` 或墙钟时间戳。

- **计时源：** `time.clock_gettime_ns(CLOCK_BOOTTIME)`。理由：同一次开机内，所有进程读到同一条单调时间线；不受 `settimeofday`/NTP 跳变影响；包含系统挂起时间（比 `CLOCK_MONOTONIC` 保守）。本沙箱已确认该时钟与 `/proc/sys/kernel/random/boot_id` 可读（**目标环境 NOT TESTED**）。
- **账本：** `evidence/budget_ledger.jsonl`，行格式与哈希链同 2.3。字段：`seq`、`kind`（`open`/`stage_start`/`stage_end`/`anomaly`/`close`）、`stage`、`boot_id`、`bt_ns`（`CLOCK_BOOTTIME`）、`wall_ns`（`CLOCK_REALTIME`，**仅用于异常交叉检查**）、`prev`。`open` 行另含 `budget_ns`（30 分钟，数值来自冻结配置，**本草案不改动**）与 `deadline_bt_ns = bt_ns + budget_ns`。
- **谁写：** 阶段的开始/结束行由**外层监督器**代写，不由各阶段脚本自己写；监督器逐个启动阶段脚本与冻结 Driver。绕过监督器的操作不被计量——见残余风险。
- **剩余预算：** `remaining = deadline_bt_ns − 当前 bt_ns`。任何阶段开始前若 `remaining ≤ 0` → 不启动，`BLOCKED(budget_exhausted)`。
- **冻结 Driver：** 其 30 分钟计时器从 Driver 自己启动算起（代码常量，真实模式拒绝 `--timeout-seconds`），所以**无法被告知「只剩 10 分钟」**。监督器在 `deadline_bt_ns` 到达时对 Driver 子进程发 SIGTERM，宽限后 SIGKILL，记录 `BLOCKED(budget_exceeded)`，保留证据，不重试（与 S5 一致）。Driver 自带的计时器仍作为第二道上限。
- **异常与不可证明（一律 `BLOCKED(budget_unprovable)`，不得判 PASS，也不得靠猜测放行）：**
  1. 账本缺失、哈希链断、首行不是 `open`、`close` 缺失；
  2. 任意两行的 `boot_id` 不同（**主机重启/容器重建**：跨开机无法用 `CLOCK_BOOTTIME` 计量，也不用墙钟替代）；
  3. 相邻两行 `bt_ns` 倒退；
  4. 相邻两行 `|Δwall − Δbt| > τ`（**时钟跳变**；τ 为待裁决参数，草案暂取 5 s，见 R3-D07）；
  5. 事件日志里某阶段有 `*_start`/`*_done` 而账本没有对应的 `stage_start`/`stage_end`（按阶段名交叉核对，**不比较时间**）。
- **总预算判定：** `close.bt_ns − open.bt_ns ≤ budget_ns`（含阶段之间的空闲时间，即字面的「整段共用」）；超出 → `BLOCKED(budget_exceeded)`。
- **可验证验收条件：** S6 的验收脚本重新读取账本并执行上述 1–5 与总预算判定。合成账本测试：(a) 正常 → PASS；(b) 两个不同 `boot_id` → BLOCKED；(c) 人为把 `wall_ns` 拨快 1 小时 → BLOCKED；(d) 总计 30:01 → BLOCKED；(e) 缺 `close` → BLOCKED；(f) 删掉中间一行（链断）→ BLOCKED；(g) `seq` 被人为重排而 `bt_ns` 不变 → 判定结果不变（证明未使用 `seq` 计时）。
- **残余风险：** 账本由与被计量代码同一信任域的监督器写入；未经监督器启动的操作（手工下载、另开终端）不被计量；`stage_start` 之间的人为等待算入预算，这可能让预算过紧（若负责人觉得不合理，走备选「各阶段各 30 分钟」并另行裁决）；重启即 BLOCKED 意味着一次主机重启会使整个运行作废，需新运行目录重来。

### 11.2 哈希链的真实能力与关键前缀的外部固定（对应 S6）

- **哈希链能做什么：** 检测「只改了某一行而没重算其后各行 `prev`」的修改。**不能做什么：** 能写文件的人可以重算整条链，所以单靠链既不能阻止、也不能发现整体改写、尾部截断或在末尾追加伪造行。因此 2.3 中先前「日志防篡改」的说法在本稿**撤销**，改为「完整性检测」。
- **关键前缀与固定记录：**
  - **K0** = 预算账本第 0 行（`open`）的前缀哈希；
  - **K1** = 事件日志 `P_{k1}`，`k1` 为 `tokenizer_hash_logged` 所在行；
  - **K2** = `P_{k2}`，`k2` 为 `heldout_audit_done` 所在行；
  - **K3** = `P_{k3}`，`k3` 为 `driver_exit` 所在行；
  - **K4** = 预算账本到 `close` 行的前缀哈希。

  固定记录 `pin_Kn.json` 内容：`{name, log, line_count, algo:"sha256", prefix_sha256, created_by, run_id}`（不含数据，不含文本）。
- **固定方式（默认，供 R3-D09 裁决）：**
  1. **Git 推送：** 把 `pin_Kn.json` 提交并**普通推送**到远端（建议专用证据分支，避免改动代码分支；推送需要对 Git 远端的出口，**与 `HF_HUB_OFFLINE` 无关**；出口被封 → `BLOCKED`，**不得跳过固定**）。远端保留该文件的内容与推送顺序（提交祖先关系）。
  2. **带外副本：** 在继续下一阶段之前，把 `P_k` 与 `line_count` 通过独立于执行主机的渠道发给审核者或负责人，由对方留存。
  3. **可选加强（需裁决，非默认）：** 由负责人持有、**不在执行主机上**的密钥签名；或外部时间戳服务（需第三方出口）。
- **先后约束（闸门）：** S4 脚本启动时检查 `pin_K1.json` 已存在且 `git ls-remote` 显示远端已有其内容，否则 `BLOCKED`（这是把「先固定 Tokenizer，再接触 val/test」变成可执行条件）。驱动 Driver 前检查 K0/K2；验收前检查 K3/K4。
- **信任边界（必须写入每份验收记录）：**
  - 能证明：被固定前缀内的任何行的**修改、插入、删除、重排**，以及固定时刻之后的尾部截断（`line_count` 与总行数对不上），都会使前缀哈希或行数与固定记录不符 → `FAIL`。
  - **不能证明：** 日志内容本身是真实的（脚本可以如实记录了错误的事实，或者在记录器之外操作）；最后一个固定点**之后**追加或改写的行（所以 K3、K4 在流程末端固定）；执行主机与推送凭据同时被控制时，伪造发生在固定**之前**；GitHub 远端本身可信；提交时间戳可信（作者可设定，所以**不用提交时间判断先后**，只用远端祖先关系和审核者的带外副本）。
- **可验证验收条件：** 验收脚本重新计算 `P_k`，与（a）本地 `pin_Kn.json`、（b）刚从远端拉取的副本、（c）事件日志里的 `pin_pushed` 行三者比对。负例（合成日志）：改旧行并重算整条链 → `P_k` 与固定记录不符 → FAIL；在固定前缀内插入一行并重算链 → FAIL；删除末尾若干行 → 行数不符 → FAIL；固定文件缺失或远端无法访问 → BLOCKED；仅在最后固定点之后追加一行 → **不被固定点发现**（记录为已知局限，由 K3/K4 位置缩小窗口）。
- **残余风险：** 同 11.2「不能证明」；以及固定动作本身引入了网络出口和一个远端依赖。

### 11.3 R6 前后哈希的真实含义与可选加强（对应 D03 / R3-D03）

- **前后各一次哈希 + `stat` 只证明：** 检查时刻 T_pre 和 T_post 的文件内容一致，且 `size/mtime_ns/ctime_ns/inode` 一致。
- **它没有证明：** 在 T_pre 与 T_post 之间，**每一次**读取（读取器 A 路径一次、B 路径 6 个独立进程、12 个负例进程、验证器的多次读取）读到的都是同一份内容。若文件在某次读取期间被换成别的内容、读完后又改回去，两次哈希相同而中间读取读到了不同数据。`ctime_ns` 能挡住大多数此类情形，但不是全部（见 R6.3 的预期漏检用例）。
- **可选的更强控制（不是默认要求；C-4 需要重新冻结）：**

| 编号 | 控制 | 能挡住 | 局限 / 状态 |
|---|---|---|---|
| C-1 | 运行专用的**只读副本**：S5 前把 train 文件复制到新建的运行私有目录（模式 0444），以副本为 `src_path` | 其他进程误改原件；共享缓存被改 | 同一用户仍可 `chmod` 后改写；路径变化需核对冻结读取器能否用清单里的路径读取（**NOT TESTED**） |
| C-2 | `chattr +i`（不可变位）覆盖运行期 | 同一非特权用户的改写 | 需要 `CAP_LINUX_IMMUTABLE`（通常是 root）和文件系统支持；**目标环境 NOT TESTED**；运行后用 `lsattr` 复核并解除 |
| C-3 | **inotify 监视**（用标准库 `ctypes` 调 `inotify_init1`/`inotify_add_watch`，避免新增依赖）监视 `IN_MODIFY\|IN_ATTRIB\|IN_CLOSE_WRITE\|IN_MOVE_SELF\|IN_DELETE_SELF`，任何事件 → FAIL | 监视器存活期间的 ABA 改写 | 监视器自身可能失效，所以需要心跳行；**`mmap` 写入不产生 `IN_MODIFY`**；监视器启动前/崩溃后无保护；**NOT TESTED** |
| C-4 | 每个读取子进程前后各哈希一次 | 子进程粒度的变化 | 必须改冻结 Driver（触发 R3-D09 的重新冻结），本草案不采用 |

- **可验证验收条件：** 验收记录必须逐字写出「该检查只证明两个检查时刻一致」这句限定语（脚本模板内含此文本，缺失 → 验收失败）；若选用 C-1/C-2/C-3，则对应控制的证据（副本哈希、`lsattr` 输出、监视日志与心跳）为必选工件。合成测试：把文件改一字节再改回（保持 `ctime` 被测试夹具回写）→ 不选 C-3 时**预期漏检**并被如实记录；选 C-3 时 FAIL。
- **残余风险：** 在本草案默认配置下，该检查不覆盖运行期内的 TOCTOU/ABA；负责人需要明确接受或加选控制（R3-D03）。

### 11.4 I4 缺席见证的范围与局限（对应 I4 / R3-D01）

- **受控目录集合（`absence_witness` 行内必须列出，用解析后的真实路径）：**
  1. Hub 缓存根（`HF_HOME`、`HF_HUB_CACHE`、`HUGGINGFACE_HUB_CACHE` 解析结果）及其下 `datasets--*/blobs/`、`snapshots/*/`、`refs/`、`.no_exist/`；
  2. 下载目标目录（`local_dir`）及其 `.cache/huggingface/download/` 下的 `*.metadata`、`*.incomplete`；
  3. **Xet 块缓存**（`HF_XET_CACHE` 或默认 `…/xet/`；本环境装有 `hf-xet`）；
  4. `datasets` 库缓存（`…/datasets/`）；
  5. 运行目录、`TMPDIR`、`XDG_CACHE_HOME`。

  S0 把这些缓存根设为**新建空目录**，使 S2 之前基线为空。验收脚本检查列表**包含**由环境变量推出的必选目录，缺项 → FAIL。
- **检查内容（只读，不读文件内容，不计算内容哈希）：**
  (a) 路径/文件名不含 validation/test 的任何模式（`validation-*`、`test-*`、`*/validation/*`、`*/test/*`）；
  (b) `blobs/` 中的 blob 文件名集合必须**等于**预期集合（S2 的 train blob 名与 README blob 名）；出现 A1 中 val/test 的 oid 名 → 命中；出现其他任何多余 blob → 失败（无法排除它是 val/test）；
  (c) Xet 块缓存**无法按文件归属**：只记录条目数与总大小，并要求其来源仅为 S2 的 train/README 下载；这一条只能靠「基线为空 + 事件日志无 val/test 下载 + 请求清单固定」间接支撑，**不能独立证明**；
  (d) 每个目录的条目列表哈希（路径+大小+类型）写入 `absence_witness` 行，并随 K1 外部固定。
- **能证明：** 在见证时刻、在上述受控目录内，没有发现 validation/test 的文件或可归属的痕迹；且事件日志中没有这两个 split 的 L1+ 记录。
- **不能证明：** 该 split「从未被访问」。具体不覆盖：受控范围之外的路径；记录器之外的读取路径（不经记录器的 Hub 调用、别的用户/进程/人手工操作）；见证之前下载后又删除的文件；不落盘的流式读取；Xet 块的归属；网络代理侧是否有请求。可选的更强手段（`auditd` 规则或对受控目录的 inotify 监视、出口请求日志）需要权限与环境配合，**NOT TESTED**，不作为默认要求。
- **措辞规则：** 验收记录与报告里只能写「受控范围内**未发现**访问迹象」，**不得写**「证明未被打开/未访问」。R6/T1 中的「未被打开」按此理解（PROPOSED CLARIFICATION，同意与否由 R3-D01 裁决）。
- **可验证验收条件与负例（合成缓存目录）：** 放入 `validation-00000.parquet` → FAIL；放入以 A1 中 val 的 oid 命名的 blob → FAIL；放入一个未预期的 blob → FAIL；Xet 缓存目录在 S0 非空 → BLOCKED；受控目录列表缺 Xet → FAIL；只有 train/README 的干净目录 → PASS。
- **残余风险：** 见「不能证明」。

### 11.5 完整性基础：LFS SHA-256、Git blob SHA-1、Xet 元数据（对应 S9 / R3-D06）

| 基础 | 判定依据（来自 L0 元数据） | 比较对象 | 算法标签 | 说明 |
|---|---|---|---|---|
| **B-LFS** | 元数据含 `lfs.sha256`（及 `lfs.size`） | 本地对**文件内容**算 SHA-256，与 `lfs.sha256` 比较；同时核对大小 | `sha256:` | 与 v1 §3.2「LFS `sha256`（oid）」一致 |
| **B-GIT** | 元数据**不含** `lfs` 字段，只有 `blob_id` | 本地对文件内容按 Git 规则算 `SHA-1("blob " + 字节数 + "\0" + 内容)`，与 `blob_id` 比较 | `git-blob-sha1:` | 只在**已证明该文件非 LFS** 时才有意义；SHA-1 强度弱于 SHA-256 |
| **B-XET** | 元数据含 Xet 内容标识（如 `xetHash`） | **本地无法等价重算**（Xet 哈希不是文件内容的 SHA-256 或 SHA-1，由 Xet 协议定义） | `xet:` | 不得与 SHA-256/SHA-1 比较；若同时有 `lfs.sha256` 则按 B-LFS 判定，Xet 值仅记录 |

- **必须避免的错误（修订 1 的缺陷）：** 对 LFS 文件，Hub 返回的 `blob_id` 是 **LFS 指针文件**（形如 `version https://git-lfs.github.com/spec/v1` / `oid sha256:…` / `size …` 的小文本）的 Git blob SHA-1，**不是内容哈希**。若把内容的 Git SHA-1 与它比较，会永远不符，或（若实现为「相符才算」）错误地以指针为内容。因此「重算 blob SHA-1 与 `blob_id` 比较」**只允许用于 B-GIT**，且前提是已确认没有 `lfs` 字段。
- **规则：**
  1. 所有摘要在日志、清单、验收记录中使用 `算法标签:十六进制` 形式；比较函数**拒绝跨算法比较**（抛错，不返回 False）；长度与字符集不符 → BLOCKED。
  2. 每个文件的 `integrity_basis ∈ {B-LFS, B-GIT, B-XET, UNKNOWN}` 由记录下来的机械规则从 L0 元数据得出，写入 A1。
  3. **元数据不足 → 默认 BLOCKED（`INTEGRITY_BASIS_UNKNOWN`）**：包括字段缺失、`lfs` 与 `blob_id` 同时缺失、只有 Xet 值、字段语义与预期不符。「只有本地算出的哈希、没有可比较的来源」不构成完整性检查，同样 BLOCKED。
  4. **草案默认：只接受 B-LFS。** B-GIT 只有在负责人批准、且 `blob_id` 语义在受控的仅 L0 元数据任务（**需另行授权，本草案不执行**）中被验证之后才可启用；B-XET 单独出现 → BLOCKED。三个 split 必须全部具备被接受的基础，否则整体 BLOCKED。
  5. 修订 SHA（`revision=`）仍须等于冻结值（v1 §3.2），它锚定元数据本身。
- **可验证验收条件（合成元数据夹具）：** LFS 且哈希相符 → PASS；LFS 且哈希不符 → FAIL；只有 `blob_id`（B-GIT）→ 默认 BLOCKED；用内容 SHA-1 去比较 LFS 的 `blob_id` → 比较函数拒绝（类型/标签测试）；仅有 `xetHash` → BLOCKED；`sha256:` 与 `git-blob-sha1:` 互比 → 抛错；摘要长度不对 → BLOCKED。
- **NOT VERIFIED / NOT TESTED：** Hub 实际返回的字段名、语义，Xet 后端是否仍返回 `lfs.sha256`，目标环境 `huggingface_hub`/`hf-xet` 的行为——本窗口没有访问网络，均未验证。
- **残余风险：** 若 Hub 元数据本身被篡改，哈希对照没有独立的第二来源（修订 SHA 只能间接锚定）；这一点与 v1 §3.2 的原假设相同。

### 11.6 test 审计的用途限制（对应 I8 / R3-D08）

- **允许（且仅限）：** (i) 文件完整性核对（11.5）；(ii) 行数、合格行数、一级标题行数、特殊字符串出现次数；(iii) Token 统计：两种口径的计数、最大 Token ID、是否出现 ID 0；(iv) round-trip 不一致行数。即 I6 的输出白名单，**一项都不多**。
- **禁止：** 把 validation/test 的任何审计结果或内容用于**训练、模型选择、调参、早停、检查点选择、质量评估**（困惑度/损失/BPC/准确率等）、阈值设定、Tokenizer 词表大小或拟合方式的调整，以及由审计结果推导任何设计变更。审计发现异常（如 round-trip 不一致）时的唯一动作是 `FAIL`/`BLOCKED` 并停止 D1，**不得**据此修改 Tokenizer。validation 在 D1 阶段同样只做上述审计；它在后续阶段的使用由那些阶段各自的预注册规定。
- **`usage_declaration`：** 审计输出必含 `usage_declaration = {"purpose":"integrity_and_tokenizer_statistics_only","prohibited":[…上述禁止项…]}`；其规范文本的 SHA-256 在负责人批准后写入验收模板，验收脚本核对相等。
- **机器可核对的部分：** 输出键白名单（I6）、审计模块的 AST 静态检查（不得导入模型、训练、优化器代码；不得出现 held-out 路径常量以外的路径用法；见 I3/I7）、`usage_declaration` 存在且相等。
- **不能证明：** 没有人手工把这些统计用于别的用途；统计本身（计数、最大 ID）会泄露 test 分布的极少量信息（已接受的微小代价，由负责人在 R3-D08 中确认）。
- **与「一次性」的关系：** v1 §5.5 把「最终 test 评估」留给 D3 的一次性事项；本审计**不是评估**。是否仍影响该「一次性」属性，由 R3-D08 裁决；备选是把 test 审计推迟到 D3。
- **可验证验收条件：** 合成测试：输出含白名单外键 → FAIL；审计模块导入 `torch`/训练代码 → 静态检查 FAIL；`usage_declaration` 缺失或文本哈希不符 → FAIL；正常输出 → PASS。
- **残余风险：** 同「不能证明」。

### 11.7 A1–A8 引用顺序与事件日志前缀哈希的自检（对应第 5 节）

- **自检方法：** 把第 5 节的层级表转为边列表，用拓扑排序（Kahn 算法）验证：每条边都指向严格更低层级且无环。执行结果见检查点文档 `F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md` 的「修订 2 自检」。
- **前一版草案的问题：** A4 引用 `A3[0..seq(tokenizer_hash_logged)]`，没有定义「前缀」的哈希怎么算，也没有说明写入顺序，容易被理解为引用整个日志，从而形成「A4 ← 日志 ← 记录 A4 的行 ← A4」的环。
- **修订：** 引用的是 `P_k`（2.3），只依赖前 `k+1` 行；工件摘要只写在 `k` 之后的行（`manifest_written`、`pin_pushed`），因此不属于任何被该工件引用的前缀。S3 的写入顺序固定为：① 保存 `tokenizer.json` → ② 追加 `absence_witness` → ③ 追加 `tokenizer_hash_logged`（第 `k1` 行，内容是 `tokenizer.json` 的摘要，**不是** A4 的摘要）→ ④ 计算 `P_{k1}` → ⑤ 写 `pin_K1.json` 并推送 → ⑥ 追加 `pin_pushed`（第 `k1+1` 行）→ ⑦ 写 A4（引用 `P_{k1}` 与 PIN1）→ ⑧ 追加 `manifest_written`（A4 摘要）。验收脚本核对该顺序：`tokenizer_hash_logged` 的行号 = 固定记录里的 `line_count − 1`。
- **预算账本** 同理：BP0（`open` 行）与 BP（到 `close`）都是前缀，A8 同时引用 PIN0 与 PIN4；验收脚本另验证 BP0 是 BP 的前缀。
- **残余风险：** 层级表是人工转换的，自检只能证明「表里写的引用」无环，不能证明实现时没有加入表外引用；所以验收脚本也要对**实际生成的清单**做同样的无环与层级检查。

## 12. 修订 2 逐项记录（F3B-D1-SPEC-R3-REVIEW-002）

每项记录：问题、原规则、修订规则、可验证验收条件、残余风险、状态。所有「修订规则」均为 `PROPOSED / NOT APPROVED`；状态栏中的 `PENDING OWNER DECISION` 表示需要第 7 节对应决策记录由项目负责人批准。

### 12.1 项 1：D07 跨进程单调计时（R3-D07）

| 栏 | 内容 |
|---|---|
| 问题 | 首版 D07 用事件日志的 `seq` 时间戳估算预算；`seq` 只是顺序号，墙钟可被改动，且多进程、重启、时钟跳变时无法得出剩余预算。 |
| 原规则 | R3-D07：预算范围按字面共用 30 分钟，用 `seq` 时间戳估算。 |
| 修订规则 | 见 11.1：预算账本 + `CLOCK_BOOTTIME` + `boot_id` + 绝对截止时间；外层监督器限时冻结 Driver；重启、时钟异常、账本缺失、阶段对不上 → `BLOCKED(budget_unprovable)`；`seq` 与 `utc` 不参与计时。 |
| 验收条件 | 11.1 的合成账本测试 (a)–(g)；验收脚本重算总预算。 |
| 残余风险 | 监督器与被计量代码同信任域；绕过监督器的操作不被计量；一次重启使整个运行作废；τ 取值待裁决。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D07）。监督器、账本模块**未编写**。 |

### 12.2 项 2：S6 哈希链仅为完整性，设计外部固定

| 栏 | 内容 |
|---|---|
| 问题 | 首版称哈希链「防篡改」并能防止插入/删除/重排；实际上任何能重写文件的人都可重算整条链。 |
| 原规则 | 2.3：日志以行内哈希链保证防篡改。 |
| 修订规则 | 见 2.3 与 11.2：哈希链只作完整性检测；关键前缀 K0–K4 通过 Git 普通推送与带外副本固定（可选签名/时间戳）；S4 以 K1 已固定为启动条件；信任边界逐条写明。 |
| 验收条件 | 11.2 的负例：改旧行重算链、前缀内插入、尾部截断 → FAIL；固定缺失或远端不可达 → BLOCKED；最后固定点之后的追加列为已知不可发现。 |
| 残余风险 | 日志真实性依旧不能证明；固定点之间与之后存在窗口；多一个远端依赖和网络出口。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D09 的外部固定方式；R3-D01）。 |

### 12.3 项 3：D03 Driver 前后哈希只覆盖两个检查时刻

| 栏 | 内容 |
|---|---|
| 问题 | 首版把「Driver 前后各一次哈希」描述成覆盖整个读取过程；它只比较两个时刻的状态。 |
| 原规则 | R6.3：读前/读后各一次，针对整个 Driver 运行。 |
| 修订规则 | 见 R6.3 与 11.3：增加 `ctime_ns`，必须写出限定语；记录 TOCTOU/ABA 残余风险；列出 C-1…C-4 可选控制及各自的局限，不默认强制。 |
| 验收条件 | 验收记录含限定语；ABA 夹具（保持 `ctime`）在默认配置下作为预期漏检被如实记录，选用 C-3 时 FAIL；改一字节 → FAIL。 |
| 残余风险 | 默认配置不覆盖运行期内的内容替换；C-1…C-3 的目标环境可用性 NOT TESTED；C-4 需重新冻结。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D03）。 |

### 12.4 项 4：I4 缺席见证的范围

| 栏 | 内容 |
|---|---|
| 问题 | 首版 I4 的措辞可被读成「证明 validation/test 从未被访问」，且未列出缓存目录集合，未提 Xet 块缓存。 |
| 原规则 | I4：写 `tokenizer_hash_logged` 之前扫描下载目录，没有 val/test 文件。 |
| 修订规则 | 见 I4 与 11.4：明确受控目录集合（含 Hub 缓存、Xet 缓存、datasets 缓存、临时目录）；S0 使用新建空缓存；检查名称、blob 集合、Xet 条目；写明不能证明的范围；报告措辞只写「受控范围内未发现访问迹象」。 |
| 验收条件 | 11.4 的合成缓存目录负例/正例；目录列表缺项 → FAIL。 |
| 残余风险 | 受控范围之外、记录器之外、见证之前已删除、不落盘读取、Xet 块归属，均无法覆盖。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D01）。 |

### 12.5 项 5：D06 完整性基础的区分

| 栏 | 内容 |
|---|---|
| 问题 | 首版建议对非 LFS 回退时重算 Git blob SHA-1 与 `blob_id` 比较；但 LFS 文件的 `blob_id` 是指针文件的 SHA-1，不是内容哈希；Xet 元数据又是另一种哈希。 |
| 原规则 | R3-D06 首版：重算 blob SHA-1 并与 `blob_id` 比较。 |
| 修订规则 | 见 11.5：B-LFS / B-GIT / B-XET 三种基础、算法标签、禁止跨算法比较；元数据不足默认 BLOCKED；草案默认只接受 B-LFS；B-GIT 的启用需先做仅 L0 的元数据验证任务（另行授权）。 |
| 验收条件 | 11.5 的合成元数据夹具与比较函数拒绝测试。 |
| 残余风险 | Hub 元数据字段语义 NOT VERIFIED；Xet 后端是否返回 `lfs.sha256` NOT VERIFIED；元数据本身没有独立第二来源。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D06）。 |

### 12.6 项 6：D08 test 审计的用途

| 栏 | 内容 |
|---|---|
| 问题 | 首版没有限定 test 审计结果的用途，存在被用于调参/选择/质量评估的空间，并可能影响 D3 的「一次性」最终评估。 |
| 原规则 | R3-D08：是否做 test 审计，未限定用途。 |
| 修订规则 | 见 11.6：只允许完整性、Token 统计、round-trip、特殊字符串计数；禁止训练、模型选择、调参、质量评估等所有其他用途；`usage_declaration` + I6 白名单 + AST 静态检查；备选为推迟到 D3。 |
| 验收条件 | 11.6 的合成测试（白名单外键、导入训练代码、声明缺失均 FAIL）。 |
| 残余风险 | 无法证明没有人手工另作他用；统计会泄露极少量分布信息。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D08）。 |

### 12.7 项 7：A1–A8 引用顺序与前缀哈希（无循环依赖）

| 栏 | 内容 |
|---|---|
| 问题 | 首版 A4 引用日志前缀但没有定义前缀哈希与写入顺序，可能被实现成引用整个日志而形成环。 |
| 原规则 | §5：A4 引用 `A3[0..seq(tokenizer_hash_logged)]`。 |
| 修订规则 | 见第 5 节、2.3 与 11.7：层级表（每条边指向严格更低层级）；`P_k` 的唯一定义；S3 写入顺序；增加 BP0/PIN0…PIN4；验收脚本对**实际清单**再做无环检查。 |
| 验收条件 | 检查点中的拓扑排序自检结果；验收脚本的无环/层级检查（合成清单：人为加一条指向更高层级的边 → FAIL）。 |
| 残余风险 | 层级表由人工转换；实现可能加入表外引用。 |
| 状态 | 已自检；ChatGPT 复核 PENDING。 |

### 12.8 项 8：11 项裁决保留为待批准的决策记录

| 栏 | 内容 |
|---|---|
| 问题 | 首版第 7 节的「草案建议」栏可能被读成已批准规范。 |
| 原规则 | §7：表格列出 11 项待裁决事项。 |
| 修订规则 | 第 0 节新增第 6 条与第 7 节标题/说明：它是**决策记录**，每项增加「状态」与「决定人 / 日期 / 决定」栏（均未填）；D01、D03、D06、D07、D08、D09 的建议内容按修订 2 更新，但**没有任何一项被批准**。 |
| 验收条件 | 全文检索：11 项均为 `PENDING OWNER DECISION`；无 `APPROVED`（作为状态词）；状态行为 `R3 DRAFT / PENDING OWNER DECISION`。 |
| 残余风险 | 无（文字性约束）；批准后仍需经正式修订文件落实。 |
| 状态 | PENDING OWNER DECISION（全部 R3-D01…D11）。 |

## 13. 下一条唯一研发指令

等待 ChatGPT 审核 R3 修订稿，并由项目负责人对第 7 节的决策记录（R3-D01…R3-D11）作出正式批准。批准前：不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。

---

**最终状态：`R3 DRAFT / PENDING OWNER DECISION`。** 未标记 FROZEN，未标记 PASS；11 项裁决均为待批准的决策记录。
