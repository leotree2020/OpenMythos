# F3-B / D1 — 真实 D1 执行前规范 R3（草案）

**状态：`R3 DRAFT / PENDING OWNER DECISION`（修订 5 最终一致性修复，响应 F3B-D1-SPEC-R3-FINAL-005；此前为修订 4、修订 3、修订 2）。不是 FROZEN，不是 PASS，不是任何授权。**

任务：F3B-D1-SPEC-R3-001（规范冲突消解）→ 修订 2：F3B-D1-SPEC-R3-REVIEW-002（证据可信性与执行预算）。日期：2026-10-26。起草者：Claude Code。
修订 2 基准：`94601916bc1fd0faa33b9f819b3a0d8cc7d61dc5`（首版草案所在提交，保留在 Git 历史中，未被覆盖）。
修订 3 基准：`eeea55269df485d3e6305a82a3c478ef141a2788`（修订 2，已被 ChatGPT Work 独立审核判为 FAIL；本轮是对其不一致与执行语义缺口的最小文档纠正，见第 14 节）。
修订 5 基准：`2ad41913ed08598f1aecfad2575a4f3a6bf51c90`（修订 4；ChatGPT 第四轮独立验收确认 C04-01、C04-03、C04-04 通过，C04-02 主体设计通过但有三处局部缺口：F1 状态机分支、F4 事后验收工件、选项 X/Y 的失败路径兼容性；见第 18 节）。
修订 4 基准：`ca40fb74d8fea2c17a1a5116ba8939b17ce2e847`（修订 3；ChatGPT 第三轮独立审核确认图结构与 Git 范围无误，但指出四处收口缺口：R7.7 正常路径语义、异常终止收尾、预算测试 (g) 的状态语义、R6.6 进入独立验收；见第 16 节）。
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
6. **第 7 节的 11 项裁决是项目负责人待批准的决策记录**。「草案建议」栏只是建议，**不是**已批准规范；只有当「状态」栏变为 `APPROVED` 并写明决定人与日期，且 R3 转为正式修订文件之后，才产生约束力。修订 2、修订 3 在多处细化了建议，但没有把任何一项变成已批准。

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

**R6/T1 中的「未被打开」（PROPOSED CLARIFICATION，对应 S1、S6）：** 对 validation/test，在事件 `tokenizer_hash_logged`（定义见 2.3、2.4）之前，**不允许任何 L1 及以上的操作**；允许 L0。理由：这样「未打开」可以按 11.4 的受控检查来核对——**在受控范围内、指定检查时刻，未发现 validation/test 访问迹象**——而不是依赖易被改写的时间戳。该检查**不是**「从未访问」的证明（11.4 逐层写明了它能与不能证明什么）。
替代选项（供负责人选择，同样 PROPOSED / NOT APPROVED）：**选项 B**——允许 L1、L2（下载并计算哈希，以保留 v1 §3.2 第 1 步的字面做法），但禁止 L3、L4。B 的代价：无法再把「受控范围内没有这些文件」作为见证依据，只能依赖事件日志。草案默认采用严格版本（L1 以上禁止）。

### 2.2 阶段表

| 阶段 | 内容 | 允许对 train | 允许对 validation/test |
|---|---|---|---|
| **S0 预检（离线）** | 配置 SHA-256、冻结清单 10/10、环境快照、仓库 clean、`mode=real` 检查、运行目录为新目录；**预算账本 `open` 行（K0）写入并外部固定**（11.1、11.2）；Hub/Xet 缓存目录设为新建空目录（11.4） | — | — |
| **S1 元数据** | 解析固定修订（返回 SHA 必须等于冻结值，禁止 `main`）；列 `wikitext-2-raw-v1/` 目录；记录三个 split 各自的路径、大小、LFS `sha256`、`blob_id`、Xet 元数据（如有），并按 11.5 机械判定每个文件的 `integrity_basis`（不明 → BLOCKED）；README 的元数据 | L0 | L0 |
| **S2 train 获取** | 下载 train 与 README；按 11.5 的完整性基础核对 train 哈希（同算法比较，不符 FAIL，基础不明 BLOCKED）；记录 `R6.pre` 哈希；切换离线（只针对 Hub 客户端，见 S8） | L0–L2 | L0 |
| **S3 Tokenizer** | T7（train 部分）扫描；仅 train 合格行拟合；保存；重复拟合；T2/T4(train)/T5(train)/T6；写 `absence_witness`（11.4）与 `tokenizer_hash_logged`；计算 `P_k1` 并**外部固定 K1**（11.2） | L0–L4 | **无 L1+** |
| **S4 held-out 审计** | K1 经远端内容验证（`pin_remote_verified`=PASS）且 `gate_check`(G_S4)=PASS 后才允许联网下载 validation/test（11.2）；按 11.5 同算法核对哈希；T7（val/test 部分）；R7 审计；T4/T5（val/test）；写 `heldout_audit_done` | L0–L4（已有） | L0–L4，**仅限 R7 允许的输出** |
| **S5 D1 读取** | 冻结的 Driver（读取器、验证器、负例）在 train 窗口上运行，由**外层监督器**按预算账本的剩余时间限时（11.1）；运行前后各一次 R6 哈希与 `stat` 快照，**最终读后快照与闸门结论先于 K3 写入**（2.4） | L2（快照）+ 冻结代码的读取 | 不涉及 |
| **S6 独立验收** | 新的独立验收脚本核对全部清单、事件日志与外部固定记录、预算账本与各闸门（第 6 节） | — | — |

S4 与 S5 的先后顺序不影响任何闸门（Driver 只需要 train 与 Tokenizer）。草案采用 S4 先于 S5，使清单引用关系保持单向（见第 5 节）。

### 2.3 事件日志（对应 S6）`【PROPOSED / NOT APPROVED】`

- 文件 `evidence/event_log.jsonl`，JSON Lines，**只追加**。每行是规范 JSON（键排序、紧凑分隔符、ASCII 转义）加 `\n`。**通用字段**：`seq`（从 0 连续递增，**只表示顺序，不是时间**）、`utc`（墙钟，**仅供信息，不用于计量，也不用于判定**）、`event`、`stage`（`S0`–`S6` 或 `W`，`W` 表示预算关闭后的收尾）、`stage_id`（监督器分配，对应预算账本的 `stage_start`；`W` 与 `S6` 为 `null`）、`split`（或 `null`）、`level`（L0–L4 或 `null`）、`path`（相对路径或 `null`）、`digest`（如有；带算法标签，见 11.8）、`prev`（上一行原始字节（含换行）的摘要，带标签 `sha256:<64 位十六进制>`；首行为 `sha256:` 加 64 个 `0`）。各事件的**专有必填字段**见 2.4。
- **事件名只能来自 2.4 的注册表。** 未登记的 `event`、缺必填字段、违反「前置」「重复」约束的行，一律 FAIL（`EVENT_UNREGISTERED` / `EVENT_FIELD_MISSING` / `EVENT_ORDER_VIOLATION`）。
- **`tokenizer_hash_logged`**：写入 `tokenizer.json` 的 SHA-256；它是 T1/R6 的分界点 `t_fix`。其前一行必须是 `absence_witness`（见 3.4）。
- **哈希链只提供完整性检测，不证明日志真实**（修订 2，见 11.2）：它能发现「没有同步重算整条链」的修改，但任何能重写文件的人都可以重算整条链。因此日志的可信度来自关键前缀的**外部固定**（11.2），判定依据是 `seq` 的顺序、链的完整性和外部固定的前缀哈希；时间戳与 `seq` 都**不用于耗时计量**——耗时只来自预算账本（11.1）。
- 记录器是一个极小的单写入者模块，由获取与拟合脚本共同使用；它自身需要独立的单元测试。该模块尚未编写。
- **前缀哈希（对应 11.2、第 5 节）：** `P_k = SHA-256(第 0 行至第 k 行的原始字节)`。它只依赖 ≤ k 的行，因此引用它不会产生循环。预算账本 `budget_ledger.jsonl` 用同样的行格式与前缀哈希定义。

### 2.4 事件注册表（唯一权威；修订 3）`【PROPOSED / NOT APPROVED】`

本节是事件名、阶段、必填字段、顺序约束与异常状态的**唯一**定义。其他章节（S0–S6、K0–K4、R6/R7/T1–T7、11.1–11.2）只能引用这里登记的事件，不得另造事件名，也不得给同一事件名另一含义。「进入前缀」指该行落在哪一个被外部固定的前缀内（LP1 = 第 0…k1 行，LP2 = 第 0…k2 行，LP3 = 第 0…k3 行，成功路径的 `k3` 是 `read_phase_closed`，失败路径的 `k3` 是 `run_aborted`（11.9）；`—` 表示不在任何被固定的前缀内，只由 A8 与最终证据提交覆盖）。

**(a) 事件日志 `event_log.jsonl`**

| 事件 | 阶段 | 专有必填字段 | 重复 | 前置（必须已出现） | 紧随 / 后置约束 | 进入前缀 | 异常状态 |
|---|---|---|---|---|---|---|---|
| `run_start` | S0 | `run_id`、`spec_ref`、`config_digest` | 否（只能是第 0 行） | — | 之后是 `pin_pushed`(K0) | LP1 | 缺失或不在第 0 行 → FAIL `EVENT_LOG_BROKEN` |
| `pin_pushed` | S0（K0）、S3（K1）、S4（K2）、W（K3、K4） | `pin`、`pin_digest`、`commit`、`branch`、`remote` | 每个 `pin` 一次 | K0：`run_start`，且账本 `open` 已写；K1：上一行是 `tokenizer_hash_logged`；K2：上一行是 `heldout_audit_done`；K3：上一行是 `read_phase_closed`（成功路径）**或** `run_aborted`（失败路径，11.9）；K4：账本 `close` 已写（选项 X），或账本 `pin_phase` 已写（选项 Y，此时 K4' 的终点是 `pin_phase`，11.9(f)）。**某个 `pin` 的终点事件不存在，就不产生该 `pin`**（例如 S4 中断时没有 K2），缺失记入 `wrapup_end.pins_missing` | 之后是 `pin_remote_verified` | K0→LP1；K1→LP2；K2→LP3；K3、K4→`—` | 推送失败 → BLOCKED `PIN_PUSH_FAILED`（在失败路径上只记入缺失证据，不改变已有的 BLOCKED / FAIL 结论） |
| `pin_remote_verified` | 同 `pin_pushed`；另在 S4、S5 的门禁前复验 | `pin`、`result`（PASS/FAIL/BLOCKED）、`remote_tip`、`commit`、`reason` | 是（同一 `pin` 的**最后一次**决定结果） | 对应的 `pin_pushed` | K0 的 PASS 是 `preflight_done` 的前置；K1 的 PASS 是 `gate_check`(G_S4) 的前置；K2 的 PASS 是 `manifest_written`(A5) 的前置 | 同该 `pin` 的 `pin_pushed` | FAIL / BLOCKED 见 11.2 的 RV 规则 |
| `preflight_done` | S0 | `checks`（配置、冻结清单 10/10、仓库 clean、`mode=real`、新运行目录、空缓存目录、账本 `open` 已写）、`result` | 否 | `pin_remote_verified`(K0)=PASS | 之后才能有任何 S1 事件 | LP1 | 任一检查不过 → BLOCKED `PREFLIGHT_FAILED` |
| `meta_query` | S1（S4 可对 validation/test 再做 L0） | `op`、`status` | 是 | `preflight_done` | S1 结束前须有 `manifest_written`(A1) | 按位置 | Hub 不可达 → BLOCKED；修订不符按 v1 §3.2 原规则（本草案不改） |
| `download_start` | S2（train、README）；S4（validation、test） | `split`、`path` | 每个文件一次 | S2：`manifest_written`(A1)。S4：`gate_check`(G_S4)=PASS，**且** `seq` 大于 `tokenizer_hash_logged` | 之后是 `download_done` 或 `interrupted` | 按位置 | 下载失败 → BLOCKED `DOWNLOAD_FAILED`；validation/test 的 `download_start` 早于 `tokenizer_hash_logged` 或 G_S4 → FAIL `R6_HELDOUT_TOUCHED_EARLY` |
| `download_done` | 同上 | `split`、`path`、`size` | 每个文件一次 | 对应 `download_start` | 之后是 `hash_done` | 按位置 | 大小与 A1 记录不符 → FAIL `SIZE_MISMATCH` |
| `hash_done` | S2、S4 | `split`、`path`、`digest`、`expected_digest`、`basis`、`match` | 每个文件每阶段一次 | `download_done` | S2 的 train：之后是 `offline_switch`，再是 `manifest_written`(A2) | 按位置 | 同算法不符 → FAIL `INTEGRITY_MISMATCH`；基础不明 → BLOCKED `INTEGRITY_BASIS_UNKNOWN`（11.5） |
| `offline_switch` | S2、S4 | `scope`（`hf_client`） | 是 | S2：`hash_done`(train)；S4：validation/test 的全部 `hash_done` | — | 按位置 | 失败 → BLOCKED |
| `online_switch` | S4 | `scope`（`hf_client`） | 否 | `gate_check`(G_S4)=PASS | 之后才能有 validation/test 的 `download_start` | LP2 | 失败 → BLOCKED |
| `parse_open` | S3（train）；S4（validation、test） | `split`、`path`、`row_groups`、`num_rows` | 每个文件一次 | train：`offline_switch`。validation/test：对应 `hash_done`(match) | 之后是 `text_read` | 按位置 | validation/test 出现在 `tokenizer_hash_logged` 之前 → FAIL `R6_HELDOUT_TOUCHED_EARLY` |
| `text_read` | 同上 | `split`、`path`、`rows` | 每个文件一次 | 对应 `parse_open` | — | 按位置 | 同上 |
| `check_result` | S3、S4（R7.7 在中断时由监督器代写，11.9） | `check_id`（T2–T7、R7.1–R7.7 之一）、`scope`、`status`（见下方「状态词枚举」）、`code` | 是 | 对应数据已读取 | `fit_start` 的前置是 `check_result`(T7, train)=PASS；`absence_witness` 的前置是 T2–T6 全部 PASS；`heldout_audit_done` 的前置见该行 | 按位置 | 按各检查的 FAIL / BLOCKED 规则 |
| `fit_start` | S3 | `fit_index`（从 1）、`corpus_rows`、`corpus_digest` | 是（T3 的重复拟合 `fit_index`≥2） | `check_result`(T7, train)=PASS | 之后是同一 `fit_index` 的 `fit_done` | LP1 | 喂入行数≠train 合格行数 → FAIL |
| `fit_done` | S3 | `fit_index`、`tokenizer_digest`、`vocab_size` | 与 `fit_start` 一一对应 | 同一 `fit_index` 的 `fit_start` | 全部 `fit_done` 之后才能有 `absence_witness` | LP1 | 中断 → BLOCKED `INTERRUPTED`；重复拟合摘要不同 → FAIL（T3） |
| `absence_witness` | S3 | `dirs`、`listing_digests`、`result`（CLEAN / HIT / UNSCOPED）| 否 | T2–T6 的 `check_result` 全部 PASS，且所有 `fit_done` 已写 | **紧邻下一行**是 `tokenizer_hash_logged` | LP1 | HIT → FAIL `R6_HELDOUT_TOUCHED_EARLY`；UNSCOPED（缓存目录非空、目录列表缺必选项）→ BLOCKED / FAIL（11.4） |
| `tokenizer_hash_logged` | S3 | `digest`（`tokenizer.json`，`sha256:`）、`absence_result`（必须是 `CLEAN`） | 否 | 紧邻上一行是 `absence_witness`（`result`=CLEAN） | **紧邻下一行**是 `pin_pushed`(K1)。本行是第 `k1` 行（K1 前缀的终点） | LP1 | 上一行不是 `absence_witness` → FAIL `EVENT_ORDER_VIOLATION` |
| `gate_check` | S4（`G_S4`）、S5（`G_S5`） | `gate`、`requires`（列表）、`status`、`reason` | 每个 `gate` 可多次，**最后一次**决定 | G_S4：同一阶段内新做的 `pin_remote_verified`(K0)=PASS 与 (K1)=PASS，且 `tokenizer_hash_logged` 已写。G_S5：`pin_remote_verified`(K0)=PASS 与 (K2)=PASS，且 `manifest_written`(A4)、(A5) 已写 | G_S4=PASS → `online_switch`；G_S5=PASS → `manifest_written`(A6) | G_S4→LP2；G_S5→LP3 | 不满足 → BLOCKED `GATE_NOT_MET` |
| `heldout_audit_done` | S4 | `audit_output_digest`、`usage_declaration_digest`、`status` | 否 | validation/test 的 `hash_done`；validation/test 的 T4、T5、T7，以及 **R7.1–R7.6 各一条 `check_result`=PASS**；**R7.7 一条 `check_result`=NOT_APPLICABLE（`code`=NO_INTERRUPTION）**；且此前日志中**不存在** `interrupted` 或 `run_aborted` | **紧邻下一行**是 `pin_pushed`(K2)。本行是第 `k2` 行 | LP2 | 审计输出不符合 11.6 的 Schema → FAIL；R7.1–R7.6 缺任何一条 PASS、R7.7 不是 NOT_APPLICABLE、或日志里已有 `interrupted` / `run_aborted` 却写了本行 → FAIL `EVENT_ORDER_VIOLATION` |
| `manifest_written` | S1、S2、S3、S4、S5、S6 | `artifact`（A1、A2、A4、A5、A6、A7、A8）、`path`、`digest`；失败路径的 A7 可带 `partial`=true（只表示 Driver 证据目录不完整，**不等于任何 PASS**） | 每个 `artifact` 恰一次（**唯一例外**：后验模式不追加 `manifest_written`(A8)，见下方「后验模式例外」） | 见下方「工件写入点」 | — | 见下方「工件写入点」 | 缺失、重复、顺序不符 → FAIL `MANIFEST_EVENT_ORDER`（失败路径上缺失的工件记入 `run_aborted.missing_evidence`，不算顺序违规） |
| `pre_read_snapshot` | S5 | `path`、`digest`、`size`、`stat`（`size`、`mtime_ns`、`ctime_ns`、`ino`） | 否 | `manifest_written`(A6) | 之后是 `driver_start` | LP3 | 摘要不等于 A6 的 `parquet_sha256`（经 11.8 转换）→ FAIL `R6_PRE_HASH_MISMATCH` |
| `driver_start` | S5 | `pid`、`pgid`、`argv_digest` | 否 | `pre_read_snapshot` | 之后是 `driver_exit` | LP3 | — |
| `driver_exit` | S5 | `exit_code` 或 `signal`、`terminated_by`（`none` / `budget` / `interrupt`）；由监督器写入 | 否 | `driver_start` | 之后是 `children_reaped` | LP3 | 被预算终止 → BLOCKED `budget_exceeded`（失败路径，11.9 F2）；Driver 自己以非零码退出（含其内部超时）属**正常路径**，如实记录 |
| `children_reaped` | S5 | `confirmed`、`residual_found`、`residual_pids`；由监督器写入 | 否 | `driver_exit` | 成功路径：之后是 `manifest_written`(A7)。`confirmed`=false 或 `residual_found`=true → 失败路径（11.9 F3） | LP3 | `confirmed`=false → BLOCKED `TERMINATION_UNCONFIRMED`；`residual_found`=true → BLOCKED `residual_process` |
| `post_read_snapshot` | S5 | `path`、`digest`、`size`、`stat`、`compare`（`hash`、`size`、`stat`） | 否 | 成功路径：`manifest_written`(A7)（已晚于 `children_reaped`）。失败路径：仅当 `children_reaped.confirmed`=true 才补做，可省略并记入 `missing_evidence` | 之后是三个 `gate_result` | LP3 | 见 R6.2、R6.6 |
| `gate_result` | S5 | `gate`（R6.1、R6.2、R6.3）、`status`（PASS / FAIL / BLOCKED）、`code` | 每个 `gate` 一次 | `post_read_snapshot` | 三个都写完后才能有 `read_phase_closed`。失败路径上写入的 `gate_result` 只是对机械检查的如实记录，**不构成整体通过** | LP3 | 按各闸门的 FAIL / BLOCKED 规则 |
| `read_phase_closed` | S5 | `s5_status`（`COMPLETED` / `DRIVER_NONPASS` / `GATE_FAILED`，均表示**证据完整地结束**）、`gates`（逐项状态） | 否 | 三个 `gate_result`；`children_reaped.confirmed`=true 且 `residual_found`=false；此前日志无 `interrupted`、`run_aborted` | **仅成功路径（证据完整）**，与 `run_aborted` 互斥。本行是第 `k3` 行（K3 前缀的终点）；**紧邻下一行**是 `pin_pushed`(K3)（预算关闭后） | LP3 | 缺失（且无 `run_aborted`）→ 不得固定 K3，BLOCKED；与 `run_aborted` 并存 → FAIL `EVENT_ORDER_VIOLATION` |
| `interrupted` | 任一阶段 | `stage`、`stage_id`、`reason`、`signal`；由监督器写入 | 至多一次（终止性） | 任一事件 | 之后只允许：监督器代写的 `driver_exit`、`children_reaped`（S5）、`check_result`(R7.7, BLOCKED, INTERRUPTED)（S4），然后必须是 `run_aborted`；**不得**再有该阶段的任何成功事件（`heldout_audit_done`、`read_phase_closed`） | 按位置 | BLOCKED `INTERRUPTED`（R7.7、11.9 F1） |
| `run_aborted` | S0–S5 | `stage`、`stage_id`、`cause`（`PREFLIGHT_FAILED` / `CHECK_FAILED` / `INTEGRITY_FAILED` / `TIMEOUT` / `INTERRUPTED` / `RESIDUAL_PROCESS` / `TERMINATION_UNCONFIRMED` / `LEDGER_WRITE_FAILED`）、`final_status`（BLOCKED / FAIL）、`code`、`missing_evidence`（应有而没有的事件与工件名）、`partial_artifacts`（`*.partial` 等的路径与带标签摘要） | 否（终止性） | 该阶段内的任一事件 | **失败路径的终点**，与 `read_phase_closed` 互斥；之后只允许 W 阶段的 `pin_pushed`、`pin_remote_verified`（K3 紧邻本行）与 S6 的 `manifest_written`(A8)；**不允许**任何 S0–S5 事件。本行是失败路径的第 `k3` 行 | LP3 | 与 `read_phase_closed` 并存、或之后出现 S0–S5 事件 → FAIL `EVENT_ORDER_VIOLATION` |

**状态词枚举（修订 4；注册表里所有 `status` / `result` 字段只能取这些值，其他取值 → FAIL `EVENT_FIELD_MISSING`）：**

| 字段 | 允许的取值 | 说明 |
|---|---|---|
| `check_result.status` | `PASS` / `FAIL` / `BLOCKED` / `NOT_APPLICABLE` | `NOT_APPLICABLE` **只允许**用于检查定义本身写明「条件不出现时不适用」的 `check_id`；本规范里只有 **R7.7**（中断行为门禁）。`NOT_APPLICABLE` **不是 PASS**：验收报告把它作为单独的状态列出，永不折算成 PASS；它只表示「触发该门禁的条件没有出现，并且这一点可由日志与账本独立复核」 |
| `gate_result.status` | `PASS` / `FAIL` / `BLOCKED` | R6.1–R6.3 |
| `gate_check.status` | `PASS` / `BLOCKED` | 门禁不满足就是 BLOCKED |
| `pin_remote_verified.result` | `PASS` / `FAIL` / `BLOCKED` | 见 11.2 |
| `run_aborted.final_status` | `BLOCKED` / `FAIL` | 失败路径的最终状态；**不存在**失败路径上的 PASS |
| 验收报告里未执行到的检查 | `NOT TESTED` | 只出现在验收输出，不进入事件日志 |

**写入者：** 阶段脚本（经记录器）只写**它自己观测到的事实**，包括它自己的 PASS / FAIL / BLOCKED 检查结果。监督器在阶段脚本已无法写入时（被杀、超时、中断）代写 `interrupted`、`driver_exit`、`children_reaped`、`check_result`(R7.7, BLOCKED)、`run_aborted`，并且**只能写 BLOCKED / FAIL 与事实性字段，不得代写任何 PASS 或 NOT_APPLICABLE**。已经写入的行永不改写，`*.partial` 文件永不改名为最终文件。

**后验（postmortem）模式的例外（FINAL-02）：** 仅用于监督器异常退出、账本没有 `close` 的运行（11.9 F4）。(1) `--postmortem` **不向原账本与原事件日志追加任何行**——包括 `manifest_written`(A8)、`pin_pushed`、`wrapup_end`；不续写，也不修复撕裂的末行。(2) 产物是两个独立文件：`evidence/postmortem.json`（事后证据，叶子文件，不是图节点）和后验 A8（`evidence/acceptance_A8_postmortem.json`，`mode`=postmortem）。(3) 后验 A8 的 `refs` 只能逐项引用**原运行中现存**的工件和 `postmortem.json` 的摘要；不存在的节点（至少 BP、PIN3、PIN4，以及未走到的阶段所产生的工件）一律标 `absent` 并说明；**不得**为它在原事件日志里伪造 `manifest_written`(A8)，其摘要只出现在验收脚本的输出和随后提交的证据提交里。(4) 这是对「A8 在 S6 末尾追加一行 `manifest_written`」这一规则的**唯一例外**，第 6 节的验收规范同步注明。(5) 缺 `close`、`run_aborted`、K3 / K4 时，后验验收**始终**输出 `NOT_ACCEPTED`，最终状态**不低于** `BLOCKED(budget_unprovable)`（若原日志里的 `run_aborted.final_status` 为 `FAIL`，则取 `FAIL`）；任何后验产物都不得使状态升级。若运行中 `close` 已存在，则不是 F4，按 S6 常规模式与 `wrapup_end` 规则处理。

**R7.7 的两条最小事件序列（C04-01；其余事件省略，顺序约束以上表为准）：**

```
正常（无中断）：
E check_result R7.1 … R7.6       status=PASS（每项一条，scope 分别覆盖 validation 与 test）
E check_result R7.7              status=NOT_APPLICABLE  code=NO_INTERRUPTION   （由审计脚本在全部审计结束后写）
E heldout_audit_done             （前置：上面七条齐备，且日志里没有 interrupted / run_aborted）
E pin_pushed K2

中断（例：S4 审计进行中被外部信号终止）：
E check_result R7.3              status=PASS            （已完成的检查保持原样，不改写）
E interrupted                    （监督器写）
E check_result R7.7              status=BLOCKED  code=INTERRUPTED   （监督器代写）
E run_aborted                    cause=INTERRUPTED  final_status=BLOCKED  missing_evidence=[check_result R7.4…R7.6, heldout_audit_done, pin K2, manifest A5, …]
   （没有 heldout_audit_done，没有 pin_pushed K2；K3 的终点是 run_aborted）
```

- **`NOT_APPLICABLE` 的有效条件（验收脚本独立复核，任一不满足 → FAIL `R77_NA_INVALID`）：** (1) 日志里在该行及之前没有 `interrupted` 或 `run_aborted`；(2) 预算账本里 S4 阶段没有 `terminate_begin`、没有 `anomaly`，`stage_end` 之前没有被信号终止的记录；(3) 运行目录里没有遗留的 `*.partial` 审计文件。
- **R7.1–R7.6 在正常运行中必须各有一条 `check_result`=PASS**；缺任何一条就不能有 `heldout_audit_done`（注册表前置）。R7.7 在正常运行中不产生 PASS，而是有一条明确的 `NOT_APPLICABLE`——不写这一条同样会使 `heldout_audit_done` 的前置不满足。
- **出现中断必须停止：** `interrupted` 之后，S4 的任何成功事件（`heldout_audit_done`、`pin_pushed`(K2)、`manifest_written`(A5)）都是 FAIL `EVENT_ORDER_VIOLATION`。

**工件写入点（`manifest_written` 的位置，决定其落在哪个前缀）：**

| 工件 | 位置 | 进入前缀 |
|---|---|---|
| A1 | S1，全部 `meta_query` 之后 | LP1 |
| A2 | S2，`offline_switch` 之后 | LP1 |
| A4 | S3，`pin_remote_verified`(K1)=PASS 之后 | LP2 |
| A5 | S4，`pin_remote_verified`(K2)=PASS 之后 | LP3 |
| A6 | S5，`gate_check`(G_S5)=PASS 之后、`pre_read_snapshot` 之前 | LP3 |
| A7 | S5，`children_reaped` 之后、`post_read_snapshot` 之前 | LP3 |
| A8 | S6 末尾 | `—` |

**(b) 预算账本 `budget_ledger.jsonl`**（行格式同 2.3；通用字段 `seq`、`kind`、`boot_id`、`bt_ns`、`wall_ns`、`prev`；`kind` 即事件名）

| 事件（`kind`） | 专有必填字段 | 状态转换 | 重复 | 进入前缀 | 异常状态 |
|---|---|---|---|---|---|
| `open` | `run_id`、`budget_ns`、`deadline_bt_ns`、`supervisor_pid` | `NEW`→`OPEN` | 否（只能是 `seq` 0） | BP0、BP | 缺失 → BLOCKED `budget_unprovable` |
| `stage_start` | `stage`（S0–S5）、`stage_id`、`pgid` | `OPEN`→`STAGE` | 每个 `stage_id` 一次；任何时刻只有一个阶段 | BP | 阶段重叠、`remaining ≤ 0` 时仍启动 → BLOCKED |
| `stage_end` | `stage_id`、`status`（ok / failed / blocked / killed）、`exit` | `STAGE`→`OPEN`（`killed` 必须经 `terminate_begin` → `terminate_signal` → `reap_done`；`failed` 含**被外部信号杀死且无需主动终止任何后代**的阶段，此时直接 `STAGE`→`stage_end`，**不得**出现 `terminate_signal` / `reap_done`） | 每个 `stage_id` 一次 | BP | 与 `stage_start` 不匹配 → BLOCKED。`status` 不是 `ok` 之后，**唯一合法的下一行是 `close`**；选项 Y 还允许 `pin_phase`（11.9(f)）。事件日志已有 `interrupted` / `run_aborted` 而 `status`=ok → FAIL `STAGE_STATUS_MISMATCH` |
| `terminate_begin` | `stage_id`、`reason`（deadline / supervisor_abort / interrupt） | `STAGE`→`TERMINATING` | 每个阶段至多一次 | BP | `reason`=deadline → `close.result` 必为 EXCEEDED；`interrupt` / `supervisor_abort` → `close.run_state` 必为 ABORTED。任何一种之后，该阶段都不得被计为成功 |
| `terminate_signal` | `sig`（TERM / KILL）、`pgid` | `TERMINATING`→`TERMINATING` | 每个阶段至多两次 | BP | **只在已写 `terminate_begin` 之后合法**；在 `STAGE` 状态（没有 `terminate_begin`）出现 → BLOCKED `LEDGER_BAD_TRANSITION` |
| `reap_done` | `confirmed`、`exit`、`residual`、`t_term_bt_ns`、`t_kill_bt_ns`、`t_reaped_bt_ns` | `TERMINATING`→`REAPED` | 每个被终止的阶段一次 | BP | `confirmed`=false → BLOCKED `TERMINATION_UNCONFIRMED`；**只在 `TERMINATING` 状态合法**（即已写 `terminate_begin`），否则 BLOCKED `LEDGER_BAD_TRANSITION` |
| `anomaly` | `code`、`detail` | 任意状态→`ANOMALY` | 是 | BP | 之后只允许 `close`（`result`=UNPROVABLE） |
| `pin_phase`（**仅选项 Y**） | — | `OPEN`→`PIN_PHASE` | 否 | BP | 选项 X 下出现 → FAIL；`ANOMALY` 之后不得出现（直接 `close`，K3 / K4' 记入 `close.pins_missing`）；选项 Y 的成功路径与失败路径（`stage_end` 非 ok 之后）都使用它，顺序见 11.9(f) |
| `close` | `result`（WITHIN_BUDGET / EXCEEDED / UNPROVABLE，**只描述时间与账本有效性**）、`total_ns`、`run_state`（COMPLETED / ABORTED）、`abort_cause`（与 `run_aborted.cause` 同枚举，或 `null`）、`el_end_event`（`read_phase_closed` / `run_aborted` / `unwritable` / `none`）、`el_lines_at_end`（整数或 `null`，不是哈希）；**仅选项 Y** 另含 `pins_verified`、`pins_missing`（选项 X 由 `wrapup_end` 承载） | `OPEN`、`PIN_PHASE`（Y）或 `ANOMALY`→`CLOSED` | 否；必须是 K4 前缀的最后一行（选项 Y 的 K4' 在 `pin_phase`，`close` 之后无任何行） | BP | 缺失、不是终行 → BLOCKED `budget_unprovable`；选项 Y 下 `close` 先于 `pin_phase` 且随后又推送 K3 / K4' → FAIL `OPTION_Y_ORDER_VIOLATION`；前提与取值规则见 11.1(e)、11.9 |
| `wrapup_end` | `pins_verified`（列表）、`pins_missing`（列表，含缺失原因）、`wrapup_ns` | `CLOSED`→`DONE` | 否；**`close` 之后唯一允许的行**（选项 X） | `—` | 缺失或超过上限 W → BLOCKED `wrapup_unprovable` |

**(c) 规范顺序（供自检与验收脚本核对「顺序可满足」；`E` = 事件日志，`B` = 预算账本；选项 X）**

```
B open
E run_start
B stage_start S0
E pin_pushed K0
E pin_remote_verified K0
E preflight_done
B stage_end S0
B stage_start S1
E meta_query (多次)
E manifest_written A1
B stage_end S1
B stage_start S2
E download_start train
E download_done train
E hash_done train
E offline_switch
E manifest_written A2
B stage_end S2
B stage_start S3
E parse_open train
E text_read train
E check_result T7.train
E fit_start 1
E fit_done 1
E fit_start 2
E fit_done 2
E check_result T2
E check_result T3
E check_result T4.train
E check_result T5.train
E check_result T6
E absence_witness
E tokenizer_hash_logged        (第 k1 行)
E pin_pushed K1
E pin_remote_verified K1
E manifest_written A4
B stage_end S3
B stage_start S4
E pin_remote_verified K0
E pin_remote_verified K1
E gate_check G_S4
E online_switch
E download_start validation
E download_done validation
E hash_done validation
E download_start test
E download_done test
E hash_done test
E offline_switch
E parse_open validation
E text_read validation
E parse_open test
E text_read test
E check_result T7.heldout
E check_result T4.heldout
E check_result T5.heldout
E check_result R7.1 … R7.6        (PASS)
E check_result R7.7              (NOT_APPLICABLE)
E heldout_audit_done           (第 k2 行)
E pin_pushed K2
E pin_remote_verified K2
E manifest_written A5
B stage_end S4
B stage_start S5
E pin_remote_verified K0
E pin_remote_verified K2
E gate_check G_S5
E manifest_written A6
E pre_read_snapshot
E driver_start
E driver_exit
E children_reaped
E manifest_written A7
E post_read_snapshot
E gate_result R6.1
E gate_result R6.2
E gate_result R6.3
E read_phase_closed            (第 k3 行)
B stage_end S5
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```

- 该顺序里没有「A 的前置是 B、B 的前置又是 A」的情形；每个前置事件都在其后继之前出现。验收脚本用同一份注册表逐行校验真实日志。
- 选项 Y 的顺序差异见 11.1(g)。失败路径的最小序列见 11.9。
- 本表只登记**哪些事件存在、以什么顺序出现**，不改变 v1/R1/R2 的任何规则。

## 3. validation/test 完整性与 Tokenizer 拟合隔离 `【PROPOSED / NOT APPROVED】`

| 编号 | 要求 |
|---|---|
| I1 | `tokenizer_hash_logged` 之前，validation/test 没有任何 L1+ 事件（事件日志证明）；允许 L0 |
| I2 | 拟合语料**只能**由 train 合格行构成（v1 §4.1「拟合输入」）。记录喂入行数与语料 SHA-256（语料 = 按行号顺序的 NFC 文本的 UTF-8 字节，各行以固定的 `\x00` 分隔后哈希；分隔符属本草案的具体化） |
| I3 | 拟合模块不接受 validation/test 路径作为参数，运行时断言文件名属于 train；独立静态检查：拟合模块源码不出现 validation/test 的路径常量 |
| I4 | **缺席见证（对应 S1/S6；完整规则、分层与局限见 11.4）：** 写 `tokenizer_hash_logged` 之前，对**明确列出的受控目录集合**做只读扫描（路径、大小、类型，**不读取内容、不计算内容哈希**），要求其中没有 validation/test 文件的任何迹象。结论只能表述为**「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象」**；它**不是**「从未访问」的证明，也不证明所有缓存都不含相关内容，更不证明不存在未记录的网络或流式读取 |
| I5 | S4 只能在 K1 经远端内容验证（`pin_remote_verified`=PASS）且 `gate_check`(G_S4)=PASS 之后开始（11.2）。S4 对 validation/test 的文件摘要必须与 S1 记录的**同算法**摘要相等（完整性基础见 11.5；不符 FAIL；基础不明或元数据不足 → BLOCKED） |
| I6 | held-out 审计脚本的输出遵循 11.6 的统一 Schema `d1_heldout_audit_v1`：`envelope`（运行身份、用途声明、规范版本、证据引用；`usage_declaration` 属于这里）与 `statistics`。`statistics` 只允许：文件摘要、文件大小、行数、合格行数、一级标题行数、Token 计数（两种口径，见 4.2）、最大 Token ID、是否出现 ID 0、round-trip 不一致行数、特殊字符串出现次数。**`statistics` 内不得**出现行文本、Token ID 序列、逐行统计、模型评估指标、数组或用途声明。由 Schema 键集合检查加静态检查保证 |
| I7 | 「不用于拟合、不用于任何模型评估」是组织约束；机器可核对的替代物是 I3 与 I6 加上「held-out 数据文件的路径不出现在任何训练、评估代码中」的静态检查。**这三项只能证明代码层面没有这样做，不能证明没有人手工使用**；该局限在验收记录中明示 |
| I8（待裁决） | v1 §5.5 R7 写明「D3 的最终 test 评估仍是后续一次性事项」。对 test 做计数与 round-trip 是否影响这个「一次性」属性，原文没有裁决；若做，用途被 11.6 严格限定。见 R3-D08 |

## 4. 验收矩阵（正常与异常输入）`【PROPOSED / NOT APPROVED】`

状态词沿用 v1 §6：完整性不符 → FAIL；输入缺失、不可达、前置条件不满足 → BLOCKED。「承担者」中的「新」指尚未编写的独立脚本；「冻」指已冻结的代码。

### 4.1 R6

| 编号 | 检查 | 正常输入 → 期望 | 异常输入 → 期望 | 证据 | 承担者 |
|---|---|---|---|---|---|
| R6.1 | **读前**：Driver 启动前计算 train 文件 SHA-256，须等于 S2 的 `hash_done` 摘要、LFS `sha256`（同为 SHA-256，11.5）与 `runtime_manifest.parquet_sha256`（裸格式，经 11.8 转换后比较） | 三者一致 → PASS | 文件被换/截断/内容改一字节 → FAIL `R6_PRE_HASH_MISMATCH`；文件不存在 → BLOCKED | `pre_read_snapshot` 事件 | 新（冻结 Driver 不做） |
| R6.2 | **读后（修订 3）**：Driver 退出、`children_reaped`(`confirmed`=true) 之后，再算一次 train 文件 SHA-256，并核对读前后的摘要、大小与 `stat` 字段（含 `ctime_ns`）；`post_read_snapshot` 与相应闸门结论（`gate_result`）**先于** `read_phase_closed` 写入，K3 在其后才计算并固定 | 一致 → PASS | 运行期间被改 → FAIL `R6_POST_HASH_MISMATCH` / `R6_STAT_CHANGED`；回收未确认 → BLOCKED `TERMINATION_UNCONFIRMED` | `post_read_snapshot`、`gate_result` 事件 | 新；冻结验证器的 `fsha(src_path)==manifest` 是其中一个冗余检查 |
| R6.3 | **粒度与限定语（PROPOSED CLARIFICATION，对应 S3；修订 2，见 11.3）：** 读前/读后各针对「整个冻结 Driver 运行」一次，加 `stat`（大小、`mtime_ns`、`ctime_ns`、inode）快照（`ctime_ns` 由内核维护，普通用户不能回写，所以「改后又改回」通常也会让它变化）。**该检查只能证明两个检查时刻的文件状态相同，不能证明运行期间每一次读取（A、B 的 6 段、12 个负例、验证器的多次读取）读到的内容一致**；验收记录必须写出这句限定语。可选更强控制见 11.3 | 两个时刻的哈希与 `stat` 均相同 → PASS（仅限该限定语所述含义） | 任一不同 → FAIL `R6_POST_HASH_MISMATCH` 或 `R6_STAT_CHANGED`（良性的 `chmod`/硬链接也会改 `ctime`，保守判 FAIL，重新运行）。**已记录的预期漏检用例：** 保持 `ctime` 不变的 ABA（需要 root、回拨系统时钟或直接写块设备），以及目标文件系统不维护 `ctime` 的情形（**目标文件系统 NOT TESTED**）；它们不作为通过依据，只作为残余风险。选用 11.3 的监视控制可缩小但不消除该风险 | 同上 | 新 |
| R6.4 | **隔离**：I1、I4（受控范围内的缺席见证，11.4）、K1 的远端内容验证（11.2） | 无 validation/test 的 L1+ 事件在 `t_fix` 之前；**受控范围内、指定检查时刻未发现访问迹象**；K1 的 RV=PASS → PASS（仅指受控检查通过，不是零访问证明） | 之前出现任何 validation/test 的 L1+ 事件，或见证命中 → FAIL `R6_HELDOUT_TOUCHED_EARLY`；日志哈希链断、或前缀哈希与固定记录不符 → FAIL `EVENT_LOG_BROKEN`；固定记录不存在、无法核对远端 → BLOCKED | 事件日志、固定记录、`pin_remote_verified` | 新 |
| R6.5 | **身份绑定**：S1 的路径/oid ↔ S2 下载的文件 ↔ 清单 | 全部一致 → PASS | 路径不属于 `wikitext-2-raw-v1/`、split 与文件名不符、非「每个 split 恰好一个 Parquet」→ BLOCKED（v1 §3.1 原规则）；哈希与 oid 不符 → FAIL | `hub_metadata.json`、`train_data_manifest.json` | 新 |
| R6.6 | **最终读后证据进入 K3，并由独立验收逐项核对（修订 3 引入，修订 4 明确为独立验收范围 R6.1–R6.6）**。验收脚本**自己**从事件日志文件与固定记录重新核对，不信任 `gate_result`、`pin_remote_verified` 里已有的结论：(a) `post_read_snapshot` 恰有一行，且行号小于 K3 终点（`read_phase_closed`）的行号；(b) R6.1、R6.2、R6.3 三个 `gate_result` 各恰有一行，行号都小于 K3 终点，且各自的状态与从 `pre_read_snapshot` / `post_read_snapshot` 的数据重新推出的结论一致；(c) `read_phase_closed` 的行号 = `k3`，`pin_K3.json` 的 `end_event` = `read_phase_closed`、`line_count` = `k3 + 1`；(d) K3 的远端内容验证 RV（11.2 步骤 1–10）由验收脚本**重新执行**并为 PASS | (a)–(d) 全部成立 → PASS | 读后快照或任一 `gate_result` 的行号在 K3 终点之后 → FAIL `R6_POST_NOT_PINNED`；`line_count` 或 `end_event` 不符 → FAIL `R6_K3_LINECOUNT_MISMATCH`；`gate_result` 与重新推出的结论不一致 → FAIL；缺 `post_read_snapshot`、缺任一 `gate_result`、缺 `read_phase_closed`、`pin_K3.json` 缺失 → BLOCKED `R6_EVIDENCE_MISSING`；RV 无法进行 → BLOCKED `PIN_UNVERIFIABLE`；失败路径（K3 终点是 `run_aborted`，11.9）→ R6.6 记 **NOT TESTED**，整体 `NOT_ACCEPTED`。**任一项缺失，验收输出都不得出现 `ALL_GATES_PASS_CANDIDATE`** | 事件日志、`pin_K3.json`、RV | 新 |

### 4.2 R7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| R7.1 | 文件摘要与 A1 中**同算法**的摘要相等（完整性基础见 11.5） | 相等 → PASS | 不符 → FAIL；基础不明/元数据不足、文件缺失/下载失败/不可达 → BLOCKED | 新 |
| R7.2 | 行数：Parquet 元数据 `num_rows` 与实际物化行数相等 | 相等 → PASS | 不等 → FAIL；`text` 列缺失或某行非字符串 → BLOCKED（沿用冻结读取器对 `NON_STRING_TEXT` 的处理） | 新 |
| R7.3 | 合格行数（`text.strip()!=""`）、一级标题行数 | 两个**互相独立**的实现给出相同结果 → PASS（PROPOSED：沿用 R2 的双实现原则） | 两个实现不一致 → FAIL | 新（两份） |
| R7.4 | **Token 计数口径（PROPOSED CLARIFICATION，对应 S4）：** 同时记录 `tokens_total = Σ len(tokens(r))`（含 EOS 前缀，且「第一个合格行」按每个 split 单独判定）与 `tokens_encode_only = Σ len(encode(NFC(text)))`，二者差必须等于该 split 的 EOS 前缀个数 | 恒等式成立 → PASS | 不成立 → FAIL | 新 |
| R7.5 | round-trip（即 T4 在 val/test 上）：`decode(encode(NFC(x))) == NFC(x)`，不一致行数为 0 | 0 → PASS | >0 → FAIL（记录个数，不记录内容）；decode 抛异常 → FAIL | 新 |
| R7.6 | 输出符合 11.6 的统一 Schema（`envelope` + `statistics`，键集合精确）、静态检查（I3、I7）与 test 用途限制 | Schema 检查全部通过；`envelope.usage_declaration` 存在且与已批准文本一致；静态检查通过 → PASS | Schema 违反 → FAIL（代码见 11.6）；已批准文本摘要尚未提供 → BLOCKED `USAGE_DECLARATION_UNAPPROVED`；审计模块引用模型/训练代码 → FAIL | 新 |
| R7.7 | **中断行为门禁（PROPOSED，对应 S5；修订 4 明确正常路径语义）：** 它不是「必须产生 PASS」的检查，而是**只在中断时触发**的门禁。无中断时记一条 `check_result`(R7.7, `NOT_APPLICABLE`, `NO_INTERRUPTION`)——这是明确的「不适用」，**不是 PASS**，且必须满足 2.4 列出的有效条件；中断时 → `BLOCKED(interrupted)`：监督器写 `interrupted`、`check_result`(R7.7, BLOCKED)、`run_aborted`，**不得**再生成 `heldout_audit_done`；已写出的部分结果文件命名为 `*.partial` 且**永不被使用**；**不自动续跑、不重试**；重新运行必须使用新的运行目录并产生新的事件日志 | 无中断 → `NOT_APPLICABLE`（有效条件成立才算数；验收报告单列「R7.7 NOT_APPLICABLE」，不并入 PASS 计数） | 中断 → BLOCKED `INTERRUPTED`；中断后遗留 `.final` 文件而无 `heldout_audit_done` 事件 → FAIL；`NOT_APPLICABLE` 的有效条件不成立（有 `interrupted`、账本有终止记录、遗留 `*.partial`）→ FAIL `R77_NA_INVALID`；缺少 R7.7 的 `check_result` 且存在 `heldout_audit_done` → FAIL `EVENT_ORDER_VIOLATION` | 新 |

**R7 的整体判定（修订 4）：** R7.1–R7.6 在正常运行中必须各有 `check_result`=PASS；R7.7 必须有 `NOT_APPLICABLE`（无中断）或 `BLOCKED`（有中断）。验收脚本对 R7 的汇总写成「R7.1–R7.6 PASS；R7.7 NOT_APPLICABLE」，**不写成 R7.1–R7.7 全部 PASS**。

### 4.3 T1–T7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| T1 | train-only 拟合；val/test 未被打开（I1–I4） | 语料行数 = train 合格行数，语料哈希已记录，受控缺席见证通过（11.4；仅指受控检查本身）→ PASS | 喂入行数不符、语料哈希缺失 → FAIL；含 val/test 路径 → FAIL | 新（拟合脚本 + 验收脚本） |
| T2 | 特殊 ID 为 0/1/2；`259 < 实际词表 ≤ 4096` | → PASS | V=259（没学到合并规则）、V>4096、特殊 ID 错 → FAIL | 新 |
| T3 | 重复拟合：至少再拟合一次（**至少一次在独立进程**，PROPOSED CLARIFICATION），`tokenizer.json` SHA-256 相同 | 相同 → PASS | 不同 → FAIL；按 v1 §4.3 不得因此改变其他冻结项，D1 就此停止 | 新 |
| T4 | round-trip：train 在 S3，val/test 在 S4 | 不一致行数 0 → PASS | >0 → FAIL | 新 |
| T5 | ID 范围 `[0, 词表)` 且不含 ID 0，对**全体**合格行（不是只窗口） | → PASS | 出现 0 或越界 → FAIL | 新（冻结读取器只检查窗口的 2048 行） |
| T6 | 文件身份：保存、记录哈希；之后每次读取先核对 | 冻结读取器与验证器每次都核对（已实现）→ PASS | 哈希不符 → 读取器 `TOKENIZER_FILE_HASH_MISMATCH`（BLOCKED）或游标 `TOKENIZER_HASH_MISMATCH`（LR2 已覆盖） | 冻（核对）+ 新（记录） |
| T7 | 三个特殊字符串在全部 NFC 文本中出现 0 次；train 部分在拟合之前，val/test 部分在 `t_fix` 之后（**PROPOSED AMENDMENT**，取代 R1 §8 的「先检查三个 split」，对应 S2；拟合只受 train 影响，所以事后扫描 val/test 不影响拟合） | 全部 0 → PASS | 任何一处 >0 → BLOCKED（沿用 R1 §8）；train 在拟合前检查出 >0 → BLOCKED 且不拟合 | 新；冻结读取器只检查窗口 |

## 5. Manifest 与日志前缀：单向哈希引用，不允许循环 `【PROPOSED / NOT APPROVED】`（修订 3：正式边列表、三类依赖、统计更正；见 11.7）

**规则：** 每个工件只能引用**更早生成**的工件（或日志/账本的某个**前缀**）的摘要；不能引用自身，不能引用后来生成的东西。每个清单包含 `produced_at_seq`（日志里的顺序号，只表示顺序）和 `refs`（名称 → 带算法标签的摘要，11.8）。验收脚本按下面的层级号校验：每条依赖边必须指向**严格更低**的层级，且被引用摘要等于磁盘或固定记录上的实际值。

```
层级  节点                                      引用（→ 只能指向更低层级）
 0    A1  hub_metadata.json            (S1)     —
 0    BP0 预算账本前缀 [0..0]（`open` 行）          —
 1    PIN0 pin_K0.json                          → BP0
 1    A2  train_data_manifest.json     (S2)     → A1
 2    LP1 事件日志前缀 [0..k1]  (k1 = tokenizer_hash_logged 所在行；其前一行是 absence_witness)
 3    PIN1 pin_K1.json   (外部固定 LP1)         → LP1
 4    A4  tokenizer_manifest.json      (S3)     → A1, A2, LP1, PIN1
 5    LP2 事件日志前缀 [0..k2]  (k2 = heldout_audit_done 所在行)
 6    PIN2 pin_K2.json                          → LP2
 7    A5  heldout_manifest.json        (S4)     → A1, A4, LP2, PIN2
 8    A6  runtime_manifest.json        (S5 前)  → A2, A4, A5
            （冻结键 parquet_sha256 / tokenizer_sha256 / actual_vocab_size 与可选 formal 块的键保持**裸格式**，转换边界见 11.8）
 9    A7  driver evidence + D1_DECISION (S5)    → A6   （冻结 Driver 已把 manifest_sha256 记入每个 trace 的 run 记录）
10    LP3 事件日志前缀 [0..k3]  (成功路径 k3 = read_phase_closed 所在行，R6 最终读后快照与闸门结论在其内；失败路径 k3 = run_aborted 所在行；2.4、11.9)
11    PIN3 pin_K3.json                          → LP3
12    BP  预算账本前缀 [0..close]（选项 Y 为 [0..pin_phase]，11.1）
13    PIN4 pin_K4.json                          → BP
14    A8  acceptance record            (S6)     → A1, A2, A4, A5, A6, A7, LP3, BP, PIN0, PIN1, PIN2, PIN3, PIN4
```

**正式边列表（机器可读；验收脚本与本稿自检都从这里构图，不从上面的人读表格推断）。** 节点行 `node 名称 层级`；`ref A -> B` 表示 A 的清单/固定记录里**写有** B 的摘要（A 依赖 B）；`rec P -> X` 表示前缀 P 的**日志行里记录了** X 的摘要（2.4 的 `manifest_written` / `pin_pushed` 行落在 P 内），所以 P 的哈希随之依赖 X；`sub P -> Q` 表示 Q 的各行是 P 的开头部分（前缀包含）。

```
node A1 0
node BP0 0
node PIN0 1
node A2 1
node LP1 2
node PIN1 3
node A4 4
node LP2 5
node PIN2 6
node A5 7
node A6 8
node A7 9
node LP3 10
node PIN3 11
node BP 12
node PIN4 13
node A8 14
ref PIN0 -> BP0
ref A2 -> A1
ref PIN1 -> LP1
ref A4 -> A1
ref A4 -> A2
ref A4 -> LP1
ref A4 -> PIN1
ref PIN2 -> LP2
ref A5 -> A1
ref A5 -> A4
ref A5 -> LP2
ref A5 -> PIN2
ref A6 -> A2
ref A6 -> A4
ref A6 -> A5
ref A7 -> A6
ref PIN3 -> LP3
ref PIN4 -> BP
ref A8 -> A1
ref A8 -> A2
ref A8 -> A4
ref A8 -> A5
ref A8 -> A6
ref A8 -> A7
ref A8 -> LP3
ref A8 -> BP
ref A8 -> PIN0
ref A8 -> PIN1
ref A8 -> PIN2
ref A8 -> PIN3
ref A8 -> PIN4
rec LP1 -> A1
rec LP1 -> A2
rec LP1 -> PIN0
rec LP2 -> A4
rec LP2 -> PIN1
rec LP3 -> A5
rec LP3 -> A6
rec LP3 -> A7
rec LP3 -> PIN2
sub LP2 -> LP1
sub LP3 -> LP2
sub BP -> BP0
```

- **失败路径不改变图（修订 4）：** 失败路径只是**使用这 17 个节点中的一个子集**（缺失的工件与固定记录不产生，记入 `run_aborted.missing_evidence` 与 A8 的缺失清单）；`run_aborted` 行里的 `partial_artifacts` 摘要指向叶子文件（`*.partial` 等），不是节点。失败路径上 LP3 里直接出现的摘要记录（例如 S4 中断时 LP3 直接包含 A4 与 PIN1 的记录行）都在上面 43 条边的传递闭包之内，层级方向不变。验收脚本对失败路径按实际日志构图并做同样的无环与层级检查。
- **图的范围：** 17 个节点。事件日志整体（A3）和预算账本整体不是节点——引用的永远是它们的前缀（LP1–LP3、BP0、BP）。原始数据文件和 `tokenizer.json` 是叶子（只被记录摘要，不引用任何别的东西），不在图中。
- **三类边的含义与期望数量：** `ref`（清单与固定记录里写明的引用，也就是 Work 复核所指的「31 条边」）、`rec`（日志行记录工件摘要造成的隐含依赖）、`sub`（前缀包含）。**三类边合在一起也必须无环、且每条边都指向严格更低的层级**——否则隐含依赖可能藏住循环。实际条数以检查点里脚本从上面的列表重新计算的结果为准（本节不预先断言总数）。
- **事件日志与预算账本是增长的文件**，所以任何工件引用的都是**前缀节点**，而不是整文件。若 A4 引用整个日志，就会形成「A4 ← 日志 ← 记录 A4 的 `manifest_written` 行 ← A4」的环；引用前缀并记录 `k` 可避免。
- **前缀哈希的计算方式（唯一定义）：** 日志有 `L_0 … L_n` 共 n+1 行，每行是规范 JSON 加换行，含 `prev` 字段；`P_k = SHA-256(L_0 ‖ L_1 ‖ … ‖ L_k 的原始字节串)`。写入顺序固定（2.4 的规范顺序）：先写第 `k` 行（如 `tokenizer_hash_logged`），再计算 `P_k`，再写 pin、推送，再追加 `pin_pushed`，最后写工件并追加 `manifest_written`。这些后写的行属于 `P_{k'}`（`k' > k`），**不属于** `P_k`，因此不存在「工件包含自己所属前缀」的情况。
- 冻结读取器和验证器只读取 A6 的三个键与 `formal` 块，**额外的键会被忽略**（对 `d1_reader.py` / `d1_verifier.py` 的核对，不是新要求）；不改它们的代码。
- `formal` 块里的值仍然是**自述**；真正的核对由 S6 的验收脚本对照 A1/A2/A4 重新计算（第 6 节）。

## 6. `FORMAL_D1_CANDIDATE` 不是 D1 PASS；不修改冻结 Driver 的独立验收方案 `【PROPOSED / NOT APPROVED】`

1. **性质：** `FORMAL_D1_CANDIDATE` 是冻结 Driver 写进决定文件的记账标签（`d1_driver.py` 的 `identity()`、`d1_formal_experiment`）。它只代表「配置 `status` 为 `FROZEN`，且清单里有一个自洽的 `formal` 块」。它**不**代表数据或 Tokenizer 经过了任何核对；决定文件中的 `d1_overall` 恒为 `NOT_DECLARED__PIPELINE_INCOMPLETE`。已知它可以被一个没有真实数据支撑的清单满足。
2. **独立验收脚本（新，尚未编写；`d1_acceptance.py` 为暂定名）：** 输入是运行目录。它**不信任** `identity` 与 `formal` 块，而是从工件重新核对：
   - 引用图无环，所有哈希与磁盘一致；
   - A1 的元数据与冻结配置（repo、revision、`wikitext-2-raw-v1/`）相符，三个 split 各一个 Parquet；
   - 事件日志与预算账本的每一行符合 2.4 的注册表；事件日志哈希链完整；关键前缀 K0–K4（K3 终点是 `read_phase_closed`，R6 最终读后证据在其内）经远端内容验证 RV 且与带外副本核对（11.2）；I1/I4 在其限定范围内成立（11.4）；预算账本证明总耗时 ≤ 预算，或标记 BLOCKED（11.1）；摘要格式符合 11.8；审计输出符合 11.6 的 Schema；
   - **R6.1–R6.6**（其中 R6.6 由验收脚本自己重新核对，见 4.1）、R7.1–R7.6 通过、**R7.7 为 NOT_APPLICABLE（无中断）并单独标注**、T1–T7 全部有证据并通过；
   - 冻结清单 10/10、配置 `status`、环境快照与 Python 完整版本；
   - Driver 的决定文件中 `read_resume`、`negatives_meta` 的分项结论，以及运行数据的 `identity`；
   - `authorization_ref` 必须能解析为仓库里已提交的授权文件，并记录该文件的 SHA-256（`【PROPOSED】`；授权文件的形式由负责人决定）。
3. **输出：** 逐闸门的 PASS / FAIL / BLOCKED / NOT TESTED（以及 R7.7 的 NOT_APPLICABLE）列表和 `ALL_GATES_PASS_CANDIDATE` 或 `NOT_ACCEPTED`。**任何必需闸门缺证据（记 BLOCKED 或 NOT TESTED），输出一律 `NOT_ACCEPTED`，不得出现 `ALL_GATES_PASS_CANDIDATE`。**失败路径的运行（K3 终点是 `run_aborted`）同样输出 `NOT_ACCEPTED`，并逐项列出已有证据、缺失证据和最终状态（11.9）。**脚本本身不宣布 D1 PASS**：D1 的结论只能由项目负责人在 ChatGPT 独立复审后作出（与冻结 Driver 的 `declared` 字段一致）。
4. **不修改冻结 Driver 的原因与代价：** 冻结代码已通过验收，任何改动都触发新的冻结与重新验收。代价是：R6 的读前读后核对只能在 Driver 之外进行（R6.3 的局限），且 Driver 的 `not_tested` 清单仍是写死的文字——验收脚本必须自己判断哪些闸门已有证据，而不能依赖该清单。
5. **后验模式（FINAL-02）：** 监督器异常退出、账本没有 `close` 的运行，由验收脚本的 `--postmortem` 模式处理（11.9 F4）。它**不向原账本和原事件日志追加任何行**——验收开始时记录两者的 SHA-256，结束时复核，被改动即 FAIL；产物是独立的 `postmortem.json` 与后验 A8（`mode`=postmortem，只引用现存工件并对缺失节点标 `absent`，**不在原日志里产生 `manifest_written`(A8)**，这是 2.4 的唯一例外）。缺 `close`、`run_aborted`、K3 / K4 时，输出始终 `NOT_ACCEPTED`，最终状态不低于 `BLOCKED(budget_unprovable)`，不得升级。
6. **验收脚本的局限（修订 2）：** 它与被验收的脚本在同一信任域内运行；它能发现不一致、缺失和被固定记录证伪的改写，不能发现「如实记录了错误事实」或「绕过记录器」的行为。这些局限在每份验收记录中明示，并由 11.2 的外部固定与审核者的独立复核补充。

## 7. 待项目负责人裁决事项——决策记录（均为 `PROPOSED / NOT APPROVED`；状态：`PENDING OWNER DECISION`）

本表是**决策记录**。「草案建议」不是规范。每项的「状态」初始为 `PENDING OWNER DECISION`，「决定人 / 日期 / 决定」三栏留空，由项目负责人填写；ChatGPT 的审核意见与草案建议同样不构成批准。修订 2 更新了 D01、D03、D06、D07、D08、D09 的建议内容；修订 3 又更新了 D03、D07、D08、D09 的建议内容（RV、K3 终点、终止协议与选项 X/Y、统一 Schema、摘要边界、事件注册表）；修订 4 又更新了 D05、D07 的建议内容（R7.7 的 NOT_APPLICABLE 语义、失败路径与三维度状态、`close` 的取值规则）。**没有**批准任何一项。

| ID | 事项 | 草案建议（PROPOSED，非规范） | 备选 | 状态 | 决定人 / 日期 / 决定 |
|---|---|---|---|---|---|
| R3-D01 | S1/S2 的消解：validation/test 的 L1+ 操作何时允许；缺席见证的受控范围与局限（11.4） | 严格：`t_fix` 之前禁止任何 L1+（2.1）；分阶段获取（2.2）；缺席见证按 11.4，接受「不能证明从未访问」的局限 | 选项 B：允许下载并算哈希，但禁止解析与读文本 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D02 | T7 的 val/test 部分后移到 `t_fix` 之后（取代 R1 §8「先检查三个 split」） | 采纳 | 保留原文：先扫描三个 split，同时放弃「未被打开」 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D03 | R6 的粒度与局限；最终读后证据先于 K3 写入（2.4、R6.6）；是否采用 11.3 的更强控制 | 整个 Driver 运行前后各一次哈希 + `stat`（含 `ctime_ns`），**明示只证明两个检查时刻**；最终读后快照与闸门结论先于 K3 写入；可选 C-1（私有只读副本）、C-3（inotify 监视，标准库 `ctypes`）；接受 ABA 漏检的残余风险 | 要求每个子进程前后各一次（需改冻结 Driver，触发重新冻结）；或选 C-2 `chattr +i` | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D04 | R7 的 Token 计数口径 | 两种口径都记录并要求恒等式（4.2 R7.4） | 只选其一 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D05 | 中断行为（S5）与异常终止的收尾（4.2 R7.7、11.9） | `BLOCKED(interrupted)`、`.partial`、不续跑不重试、新运行目录；R7.7 正常运行写 `NOT_APPLICABLE`（不是 PASS）；中断与其他失败统一走 `run_aborted` 终点与 11.9 的收尾顺序，监督器不写 PASS | 允许在阶段边界续跑 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D06 | 完整性基础：LFS SHA-256、Git blob SHA-1、Xet 元数据的区分；元数据不足时的处理（11.5） | 仅接受 B-LFS；B-GIT / B-XET 在元数据语义未被受控验证前 **BLOCKED**；摘要带算法标签，禁止跨算法比较；先做仅 L0 的元数据验证任务（需单独授权） | 立即接受 B-GIT（需先证明该文件非 LFS/Xet，目前无法证明） | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D07 | 30 分钟预算：范围、**计时方式**与终止/关闭协议（11.1） | 范围按字面：从预算账本 `open` 到 `close` 共用 30 分钟；`CLOCK_BOOTTIME` + `boot_id` + 墙钟交叉检查，**不用 `seq`**；外层监督器按 11.1(d) 终止超限的冻结 Driver（不改冻结 Driver 的超时机制）；主机重启、时钟异常、账本缺失、回收未确认 → `BLOCKED`；预算结果（WITHIN_BUDGET / EXCEEDED / UNPROVABLE）、运行状态（COMPLETED / ABORTED）与实验最终状态相互独立（11.9）。**收尾方案二选一：选项 X（草案建议）** K3/K4 的推送在 `close` 之后，受上限 `W` 约束；**选项 Y** 固定动作在预算内，K4' 不含 `close`。参数 τ、`G_term`、`G_kill`、`W` 待定 | 选项 Z：网络阶段与计算阶段各自 30 分钟；或改用 `CLOCK_MONOTONIC`（不含挂起时间） | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D08 | 是否在 D1 阶段对 test 做审计，及其用途限制与输出 Schema（11.6） | 做，且**仅限**完整性、Token 统计、round-trip、特殊字符串计数；输出遵循统一 Schema（`usage_declaration` 在 Envelope，`statistics` 严格限定）；**禁止**训练、模型选择、调参、质量评估等一切其他用途；用途限制始终生效 | 推迟 test 的审计到 D3 的一次性评估时（Schema 去掉 `test`） | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D09 | 新脚本集（记录器、预算账本与监督器、获取、拟合、审计、清单生成、摘要模块、验收、外部固定与 RV 工具）的授权与重新冻结流程；外部固定方式（11.2：默认 Git 推送 + 远端内容验证 RV + 审核者带外副本）；事件注册表（2.4）与摘要格式边界（11.8）作为这些脚本的共同规格 | 各自独立分支、独立测试、整体再冻结一次 | 分批冻结；或要求签名提交/外部时间戳 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D10 | 授权文件形式（第 6 节的 `authorization_ref`） | 仓库里已提交的授权记录文件 + 其 SHA-256 | 由负责人另定 | PENDING OWNER DECISION | ____ / ____ / ____ |
| R3-D11 | `tokenizer.json` 能否提交公开仓库（v1 §3.5、§11，沿用） | 仍只提交哈希与统计 | — | PENDING OWNER DECISION | ____ / ____ / ____ |

## 8. 本草案不改变的内容（核对清单）

- v1/R1/R2 全文、读取器、验证器、驱动器、`d1_env_manifest.py`、`d1_selftest_data.py`、测试、`D1_FROZEN_CONFIG.json`（`status = FROZEN`）、`D1_CODE_SHA256SUMS`、Codespaces 证据：**未改动**。
- 数据窗口（2048 个合格行）、`seq_len=64`、块长 65、游标 `d1_cursor_v2`、九步检查、P1–P5、LR1–LR9、CR1–CR3、哈希链、Tokenizer 行为冻结（R1 §8 除 T7 一行）、静态公式 `P(V)=206,976+320V`：**未改动**。
- 30 分钟的**数值**与 Driver 内的超时常量：**未改动**（S7 / R3-D07 只涉及预算范围与计时方式）。
- 本草案不授权任何下载、拟合、D1 执行、训练、GPU 或 D2/D3。

## 9. 文档一致性核对（本次执行）

对第 1 节每条引文，用脚本在源文件中逐字查找；同时核对 v1/R1/R2 的 SHA-256 未变；并检查本稿内部：判定词、决策 ID、依赖图（正式边列表构图、拓扑排序、层级严格递减）、事件注册表与全文事件名的一致性、规范顺序的可满足性、摘要格式与冻结接口的对照、残留的过期表述。结果见检查点文档 `F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`。修订 4 另核对：状态词枚举、R7.7 两条序列、四条失败流程（F1–F4）在注册表下的可满足性，以及失败路径上的摘要引用没有越出 17 节点 / 43 边的传递闭包。修订 5 另核对：F1a / F1b / F1c 的账本转换、F1–F3 在选项 X 与（经变换的）选项 Y 下的合法性、F4 后验模式不向原日志追加任何行。

（节号说明：第 10、13、15、17 节的编号不再使用——原「下一条唯一研发指令」现位于第 19 节；为避免打乱已有交叉引用，其余节号保持不变。）

## 11. 细则（修订 2 引入，修订 3 更正与补全，修订 4 收口；响应 F3B-D1-SPEC-R3-REVIEW-002 / REVIEW-003 / CLOSURE-004）`【PROPOSED / NOT APPROVED】`

本节给出第 2–7 节所引用的细则。每一条都标出**它能证明什么**与**不能证明什么**。凡涉及本环境之外的行为（目标文件系统、Hub 元数据字段语义、网络出口），一律标 `NOT VERIFIED` / `NOT TESTED`。

### 11.1 跨进程预算账本、监督器与终止协议（对应 S7 / R3-D07；修订 3 补全）

**目标：** 把 v1 §8 的「30 分钟墙钟硬上限」在获取、拟合、审计、读取、验证**多个独立进程**之间计量，且不依赖事件日志的 `seq` 或墙钟时间戳；并规定监督器、子进程、账本关闭、外部固定的**先后顺序**。**不修改冻结 Driver 的超时机制**（真实模式拒绝 `--timeout-seconds`，Driver 自己的 30 分钟计时器保持不变，作为第二道上限）。

**(a) 计时源与预算区间。** `time.clock_gettime_ns(CLOCK_BOOTTIME)`：同一次开机内所有进程读到同一条单调时间线，不受 `settimeofday`/NTP 跳变影响，包含挂起时间。本沙箱确认该时钟与 `/proc/sys/kernel/random/boot_id` 可读（**目标环境 NOT TESTED**）。**预算区间 = 账本 `open` 行到 `close` 行**，长度 `close.bt_ns − open.bt_ns ≤ budget_ns`（30 分钟，数值来自冻结配置，**本草案不改动**）。`open` 行含 `deadline_bt_ns = bt_ns + budget_ns`。`seq` 与事件日志的 `utc` **不是**计时来源：**`seq` 不参与任何耗时数值的计算**，但**参与账本有效性判定**（`seq` 必须从 0 连续递增；不连续、重排、`prev` 哈希链不符都使账本无效），两者不得混为一谈（见测试 (g1) / (g2)）。

**(b) 账本事件与严格状态转换。** 行格式与全部事件见 2.4(b)。合法转换如下，其余一律非法（非法转换 → BLOCKED `budget_unprovable`）：

| 当前状态 | 允许的下一行 | 下一状态 | 条件 |
|---|---|---|---|
| `NEW` | `open` | `OPEN` | 必须是 `seq` 0 |
| `OPEN` | `stage_start` | `STAGE` | `remaining = deadline_bt_ns − 当前 bt_ns > 0`；上一阶段已 `stage_end`；`stage_id` 未用过 |
| `STAGE` | `stage_end`（`status`=ok / failed / blocked） | `OPEN` | `stage_id` 与 `stage_start` 一致；已完成 (d) 的 T5–T6 且**无残留需要主动终止**（阶段自行退出，或被外部信号杀死但没有存活后代）；**直接转换，不经过 `TERMINATING`**。**`status` 不是 `ok` 之后，唯一合法的下一行是 `close`**（选项 Y 还允许 `pin_phase`） |
| `STAGE` | `terminate_begin` | `TERMINATING` | 每个阶段至多一次。两种进入方式：监督器收到终止信号 / 到截止时间；或 T6 发现仍存活、需要主动终止的后代（`reason`=supervisor_abort）。此后该阶段不得被计为成功 |
| `TERMINATING` | `terminate_signal`（TERM，之后可 KILL） | `TERMINATING` | 至多两行；**只能在这个状态写** |
| `TERMINATING` | `reap_done` | `REAPED` | 必含 `confirmed` 与三个时间点；**只能在这个状态写** |
| `REAPED` | `stage_end`（`status`=killed） | `OPEN` | — |
| 任意 | `anomaly` | `ANOMALY` | 此后只允许 `close`（`result`=UNPROVABLE） |
| `OPEN`（选项 X）/ `PIN_PHASE`（选项 Y）/ `ANOMALY` | `close` | `CLOSED` | 见 (e) |
| `OPEN`（仅选项 Y；成功路径，或失败路径中 `stage_end` 非 ok 之后） | `pin_phase` | `PIN_PHASE` | 见 (f)(g)、11.9(f)；`ANOMALY` 之后不允许 |
| `CLOSED`（选项 X） | `wrapup_end` | `DONE` | 见 (f) |

**(c) 监督器的不变量。**
1. **单一监督器**创建账本、写全部账本行；各阶段脚本不写账本，也无权关闭账本。监督器记录自己的 `pid` 与启动时的 `bt_ns`。
2. **同一 `boot_id`、同一账本**：每次写任何账本行之前先读 `boot_id`，必须等于 `open` 行；不等 → 写 `anomaly`，之后只能 `close(UNPROVABLE)`。
3. **受计时进程都由监督器启动**：每个阶段脚本与冻结 Driver 以 `subprocess.Popen(..., start_new_session=True)` 启动（独立会话/进程组，记录 `pgid`）；监督器用 `prctl(PR_SET_CHILD_SUBREAPER)`（标准库 `ctypes` 调用）使双重 fork 后被孤立的后代重新挂到监督器下，以便等待和清理。阶段之间不重叠。
4. 每行 `O_APPEND` 写入后 `flush` + `fsync`。账本文件由监督器创建（模式 0600；同用户仍可改写，见 (h)）。
5. 监督器用 `waitpid(WNOHANG)` 加不超过 1 s 的轮询睡眠检查 `CLOCK_BOOTTIME`（不使用依赖单调钟的 `signal.setitimer` 作为唯一手段）；因此超限检测的粒度不超过 1 s，加上写入延迟，**实际终止时刻会略晚于 `deadline_bt_ns`**，该延迟计入预算而不被忽略。

**(d) 终止协议（超限时，按顺序执行；每一步都写账本行）。**
- **T1** 写 `terminate_begin{stage_id, reason}`（`reason`=deadline / supervisor_abort / interrupt）。从此刻起该阶段不得被计为成功——**即使它此后以退出码 0 自行结束**；`reason`=deadline 使 `close.result` 必为 `EXCEEDED`，其余两种使 `close.run_state` 必为 `ABORTED`（取值规则见 (e)、11.9(a)）。
- **T2** 对阶段进程组 `killpg(pgid, SIGTERM)`，写 `terminate_signal{TERM}`。
- **T3** 等待至多 `G_term`（暂定 10 s，**待裁决参数**）；以 `CLOCK_BOOTTIME` 计，等待期间直接子进程自行退出则跳到 T5。
- **T4** 若直接子进程仍在，或 `killpg(pgid, 0)` 仍成功（进程组仍有成员）：`killpg(pgid, SIGKILL)`，并对监督器名下被重新挂靠的非监督器自己的后代发 SIGKILL；写 `terminate_signal{KILL}`；再等待至多 `G_kill`（暂定 5 s，待裁决）。
- **T5** 用 `waitpid` 回收直接子进程并记录退出码或信号；循环 `waitpid(-1, WNOHANG)` 回收全部被重新挂靠的后代，直到 `ECHILD` 或 `G_kill` 用尽。
- **T6** **残留检查**：扫描 `/proc`，凡属于该阶段会话/进程组、或父进程为监督器且不是监督器自己的辅助进程者，均为残留。有残留（包括处于不可中断状态而无法回收的进程）→ `confirmed=false`。
- **T7** 写 `reap_done{confirmed, exit, residual, t_term_bt_ns, t_kill_bt_ns, t_reaped_bt_ns}`，随后 `stage_end{status:"killed"}`。
- **时间消耗不得被忽略：** T2–T7 的时间全部落在 `open`…`close` 之内（`close` 在 T7 之后写），并以 `kill_overhead_ns = t_reaped_bt_ns − terminate_begin.bt_ns` 单独报告。由于已发生 `terminate_begin`，结果必为 `BLOCKED(budget_exceeded)`（v1 §6 的「墙钟超时」在冻结 Driver 中也是 BLOCKED，一致）；该数值用于判断 `G_term`、`G_kill` 是否合理，缺失则验收 FAIL。
- **没有发出终止的阶段同样执行 T5–T6**（回收退出状态并做残留检查），此时账本仍在 `STAGE` 状态，**不写** `terminate_signal` / `reap_done`：(i) 无需主动终止的后代 → 直接 `stage_end`（阶段自行退出为 ok / blocked，被外部信号杀死为 `failed`，`exit` 记信号）；(ii) T6 发现仍存活的后代 → **此时才**写 `terminate_begin{reason: supervisor_abort}` 进入 `TERMINATING`，再按 T2–T5、T6、T7 执行，以 `reap_done`、`stage_end{killed}` 收尾，`BLOCKED(residual_process)`。因此「阶段进程被外部信号杀死」本身不构成进入 `TERMINATING` 的理由；先收集退出状态、做残留检查，再决定走 (i) 还是 (ii)（F1b / F1c，11.9）。
- 冻结 Driver 的超时由其自身先触发时（Driver 自己以 BLOCKED 退出），监督器按正常结束记录，不发信号。

**(e) `close` 何时写、写失败怎么办。**
- **写 `close` 的前提（修订 4）：** 监督器所知的运行中阶段已全部有 `stage_end`；**不再要求**「回收已确认」或「存在成功事件」——回收未确认也必须写 `close`（`result=UNPROVABLE`），否则账本永远无法关闭。事件日志的终点要求按路径区分：**成功路径**（S0–S5 都走到）要求已有 `read_phase_closed`；**失败路径**要求已有 `run_aborted`；事件日志已不可写时，`close.el_end_event=unwritable`，`abort_cause` 与诊断写在 `close` 内。失败路径不能强求一个不会出现的成功事件（详见 11.9）。
- **`close` 的取值规则：** `result`（优先级 UNPROVABLE > EXCEEDED > WITHIN_BUDGET）——有 `anomaly`、回收未确认、`boot_id` 变化、状态机非法 → `UNPROVABLE`；否则 `total_ns > budget_ns` 或存在 `reason`=deadline 的 `terminate_begin` → `EXCEEDED`；否则 `WITHIN_BUDGET`。`run_state`：`el_end_event` 为 `read_phase_closed` → `COMPLETED`，其余 → `ABORTED`。`result` **只描述时间与账本有效性**，与实验是否成功无关（三维度的关系见 11.9(a)）。`el_lines_at_end` 是一个**整数**（终点事件的行号 + 1，不可写时为 `null`），不是哈希，因此不给依赖图增加边。
- **写入失败：** 监督器重试一次（含 `fsync`）；仍失败 → 向标准错误输出诊断，向仍在运行的进程组发 SIGKILL（尽力而为），以专用退出码（暂定 70）退出。**没有 `close` 行 = `BLOCKED(budget_unprovable)`，绝不能 PASS。** S0 预检要求运行目录所在磁盘有足够空间，并在**独立的临时文件**上做一次「追加 + `fsync` + 删除」自检（不碰账本）。
- 监督器本身被杀或崩溃：无 `close` → `BLOCKED(budget_unprovable)`；**不允许另起监督器续写同一账本**，只能新建运行目录重做（与 R7.7 一致）。

**(f) 预算究竟包含什么；K3/K4 与预算的关系（消除循环）。**
- 难点：K4 是账本到 `close` 为止的前缀；把 K4 推送到远端必须发生在 `close` **之后**。若要求「K4 固定在预算内完成」同时「K4 前缀包含 `close`」，则不可能满足。下面两个方案各自给出可实施的顺序，二选一，**由负责人在 R3-D07 裁决**；草案建议选项 X。
- **选项 X（草案建议）：K3、K4 的推送与验证在预算关闭之后。**
  - 预算**包含**：S0–S5 的全部活动；K0、K1、K2 的推送与远端验证（它们在 S0、S3、S4 内）；SIGTERM/SIGKILL 与回收；最终残留检查；`close` 的写入。
  - 预算**不包含**：K3、K4 的推送与验证（阶段 `W`）、S6 验收脚本、人工复核。
  - 收尾阶段上限 `W`（暂定 10 分钟，**待裁决**）：`wrapup_end.bt_ns − close.bt_ns ≤ W`；`wrapup_end` 是 `close` 之后**唯一**允许的账本行，不在 K4 内；缺失或超限 → `BLOCKED(wrapup_unprovable)`。
  - 顺序：① `read_phase_closed` → ② 阶段末尾的回收与残留检查（(d) 的 T5–T6） → ③ 账本 `stage_end(S5)` → ④ 账本 `close` → ⑤ 计算 `P_k3`，写 `pin_K3.json`，推送，事件日志 `pin_pushed`(K3) → ⑥ 远端验证 K3（`pin_remote_verified`）→ ⑦ 计算账本到 `close` 的前缀哈希，写 `pin_K4.json`，推送，`pin_pushed`(K4) → ⑧ 远端验证 K4 → ⑨ 账本 `wrapup_end` → ⑩ S6 验收。
  - 此方案下 `close` 在 K4 内（预算终点被外部固定）；代价：K3、K4 固定前存在一个不超过 `W` 的、未被固定的窗口。
- **选项 Y：预算包含全部固定动作。**
  - 预算**包含**：选项 X 的全部，**外加** K3、K4' 的推送与验证；K4' 是账本到 `pin_phase` 行为止的前缀（**不含 `close`**）。
  - 顺序：① `read_phase_closed` → ② 阶段末尾的回收与残留检查 → ③ 账本 `stage_end(S5)` → ④ 账本 `pin_phase` → ⑤ K3 的推送与验证 → ⑥ K4' 的推送与验证 → ⑦ 账本 `close` → ⑧ S6 验收。
  - 此方案下没有 `wrapup_end` 行；`pin_phase` 到 `close` 的间隔同样受上限 `W` 约束（防止推送卡住使账本长期无法关闭），超过则不再等待，尚未完成的 pin 记入 `close.pins_missing`，`close` 照常写入。失败路径的顺序见 11.9(f)（**不得**直接复用选项 X 的「先 `close` 后 pin」）。代价：`close`（预算终点）本身**不在被固定的前缀内**，只能由 A8 与最终证据提交间接覆盖；若 `pin_phase` 与 `close` 之间被改写，不会被 K4' 发现。
- **两个方案都不允许：** 把 K3、K4 的固定放在 `close` 之前却又让 K4 包含 `close`；也不允许在 `close` 之后向账本追加除 `wrapup_end`（选项 X）以外的任何行。
- 选项 Z（沿用此前的备选，不改）：网络阶段与计算阶段各自 30 分钟——不需要上面的收尾顺序，但与「整段共用」的字面解读不同。

**(g) 选项 Y 对其他章节的影响。** 2.4 的账本注册表已为 `pin_phase`、`close.pins_verified` / `pins_missing` 登记（选项 X 下出现 `pin_phase` → FAIL）；第 5 节的 `BP` 节点在选项 Y 下解释为「账本到 `pin_phase` 的前缀」；节点与边的数量不变。选项 Y 的失败路径与 F1–F3 的对应顺序见 11.9(f)。

**(h) 异常与不可证明（一律 `BLOCKED`，不得判 PASS，也不得靠猜测放行）。** 账本缺失；哈希链断；首行不是 `open`；`close` 缺失或不是终行（选项 X 允许其后有一行 `wrapup_end`）；非法状态转换；任意两行 `boot_id` 不同（**主机重启 / 容器重建**：跨开机无法用 `CLOCK_BOOTTIME` 计量，也不用墙钟替代）；相邻两行 `bt_ns` 倒退；相邻两行 `|Δwall − Δbt| > τ`（**时钟跳变**；τ 暂取 5 s，待裁决）；事件日志里的阶段（`stage_id`）在账本里没有对应的 `stage_start`（按 `stage_id` 与阶段名交叉核对，**不比较时间**）；回收未确认（`TERMINATION_UNCONFIRMED`）；超过预算（`budget_exceeded`）；超过 `W`（`wrapup_unprovable`）。

**可验证验收条件（S6 验收脚本重读账本；以下合成账本测试只规定预期，本轮**不运行**）：**

| 用例 | 预期 |
|---|---|
| (a) 正常、同一 `boot_id`、总计 < 预算、`close` 在 `read_phase_closed` 之后 | `result=WITHIN_BUDGET`，`run_state=COMPLETED` |
| (b) 两个不同 `boot_id` | BLOCKED |
| (c) `wall_ns` 人为拨快 1 小时 | BLOCKED |
| (d) 总计 30:01，无 `terminate_begin` | BLOCKED `budget_exceeded` |
| (e) 缺 `close` | BLOCKED |
| (f) 删掉中间一行（链断） | BLOCKED |
| (g1) **耗时数值**：把同一份账本在内存中的 `seq` 字段任意置换（不改 `bt_ns`），调用耗时计算 | 得到的 `close.bt_ns − open.bt_ns` 与未置换时**完全相同**（证明耗时计算不读 `seq`）。这只是对耗时数字的断言，**不是**对验收结果的断言 |
| (g2) **账本有效性**：`seq` 不连续（0,1,3…）、两行重排、重排后重算了 `prev`、`prev` 哈希链不符、状态转换非法 | 验收**一律拒绝**：BLOCKED `budget_unprovable`（代码依次为 `LEDGER_SEQ_INVALID` / `LEDGER_SEQ_INVALID` / `LEDGER_CHAIN_BROKEN` / `LEDGER_BAD_TRANSITION`）；即便耗时数字未变，整体验收结果也不是 PASS |
| (h) 有 `reason`=deadline 的 `terminate_begin`，阶段随后以退出码 0 结束 | `close.result=EXCEEDED`，最终 BLOCKED `budget_exceeded`，不是成功 |
| (h2) 有 `reason`=interrupt 的 `terminate_begin`，总耗时 < 预算 | `close.result=WITHIN_BUDGET`，`run_state=ABORTED`，最终 BLOCKED `interrupted`（预算结果不等于实验成功） |
| (h3) 回收未确认仍必须写 `close` | `close.result=UNPROVABLE`，不因前提不满足而拒绝关闭账本 |
| (h4) 失败路径的 `close` 的 `el_end_event` 是 `run_aborted`，事件日志里却有 `read_phase_closed` | FAIL `EVENT_LOG_BROKEN` |
| (i) `reap_done.confirmed=false` | BLOCKED `TERMINATION_UNCONFIRMED` |
| (j) 阶段脚本留下残留后台进程 | BLOCKED `residual_process` |
| (k) `close` 之后出现 `wrapup_end` 以外的行（选项 X） | BLOCKED |
| (l) `wrapup_ns` > W（选项 X） | BLOCKED `wrapup_unprovable` |
| (m) 缺 `kill_overhead_ns` 的终止记录 | 验收 FAIL |
| (n) 没有 `terminate_begin` 却出现 `terminate_signal` 或 `reap_done`（例如阶段进程只是被外部信号杀死，监督器却照搬终止序列） | BLOCKED `budget_unprovable`（`LEDGER_BAD_TRANSITION`） |
| (o) 选项 Y 下 `pin_phase` 到 `close` 的间隔超过 `W` | `close` 照常写入，未完成的 pin 记入 `pins_missing`；不改变 `result`，也不升级任何状态 |

**残余风险：** 账本由与被计量代码同一信任域的监督器写入，同用户可改写文件（靠 K0、K4 外部固定与 A8 间接约束）；绕过监督器的操作（手工下载、另开终端）不被计量；`stage_start` 之间的人为等待算入预算，可能让预算过紧；一次重启使整个运行作废；监督器的 1 s 轮询粒度与 `G_term`、`G_kill` 都会让终止略晚于截止时刻；进程若处于不可中断状态则无法确认回收；`PR_SET_CHILD_SUBREAPER` 与 `/proc` 扫描在目标环境的可用性 **NOT TESTED**；τ、`G_term`、`G_kill`、`W` 的取值待裁决；选项 X 与 Y 各有前述代价。

### 11.2 哈希链的真实能力与关键前缀的外部固定（对应 S6；修订 3 补全远端内容验证）

- **哈希链能做什么：** 检测「只改了某一行而没重算其后各行 `prev`」的修改。**不能做什么：** 能写文件的人可以重算整条链，所以单靠链既不能阻止、也不能发现整体改写、尾部截断或在末尾追加伪造行。因此 2.3 中先前「日志防篡改」的说法在本稿**撤销**，改为「完整性检测」。
- **关键前缀与固定记录：**
  - **K0** = 预算账本第 0 行（`open`）的前缀；
  - **K1** = 事件日志 `P_{k1}`，`k1` 为 `tokenizer_hash_logged` 所在行；
  - **K2** = `P_{k2}`，`k2` 为 `heldout_audit_done` 所在行；
  - **K3** = `P_{k3}`，成功路径的 `k3` 为 **`read_phase_closed`** 所在行（修订 3：不再是 `driver_exit`。最终读后快照、`post_read_snapshot`、三个 `gate_result` 都在 K3 之内，见 2.4、R6.6）；**失败路径**的 `k3` 为 `run_aborted` 所在行（修订 4，11.9），此时 K3 只固定「最终日志前缀」，不含成功闸门结论；
  - **K4** = 预算账本到 `close` 为止的前缀（选项 X），或到 `pin_phase` 为止的前缀（选项 Y，11.1(f)）。
- **固定记录 `pin_Kn.json`**（规范 JSON：键排序、紧凑分隔符、ASCII 转义，末尾一个换行；与冻结 Driver 的 `canon()` 同一序列化，外加换行）：`{"end_event": …（成功路径的 K3 为 `read_phase_closed`，失败路径为 `run_aborted`）, "line_count": N, "log": "event_log" | "budget_ledger", "name": "Kn", "prefix_digest": "sha256:<64 位十六进制>", "run_id": …, "schema": "d1_pin_v1"}`。`line_count` = `k + 1`。`pin_digest` = 该文件**原始字节**的 `sha256:` 摘要。不含数据，不含文本。
- **固定方式（默认，供 R3-D09 裁决）：**
  1. **Git 推送：** 把 `pin_Kn.json` 提交并**普通推送**到远端的专用证据分支（避免改动代码分支）。推送需要对 Git 远端的出口，**与 `HF_HUB_OFFLINE` 无关**；出口被封 → `BLOCKED`，**不得跳过固定**。
  2. **带外副本：** 在继续下一阶段之前，把 `name`、`line_count`、`prefix_digest`、`pin_digest` 与提交 SHA 通过独立于执行主机的渠道发给审核者或负责人，由对方留存。
  3. **可选加强（需裁决，非默认）：** 由负责人持有、**不在执行主机上**的密钥签名；或外部时间戳服务（需第三方出口）。
- **远端内容验证程序 RV（修订 3；监督器在每次推送后、在 S4/S5 门禁前、以及 S6 验收脚本都执行同一程序）。** `git ls-remote` **只能**得到远端引用指向哪个提交（`remote_tip`），**不能**证明 `pin_Kn.json` 的内容；因此 RV 必须取回对象并读内容：
  1. `git ls-remote` 取得证据分支的 `remote_tip`（仅作参照）。
  2. 把该分支**完整**取回到一个全新的临时仓库（不使用浅克隆；不依赖本地克隆里可能过期的远端跟踪引用）。取回失败（网络、认证、超时）→ **BLOCKED** `PIN_UNVERIFIABLE`。
  3. 确认取回后的分支尖等于 `remote_tip`；不等 → BLOCKED（取回期间远端变化，重试一次，仍不等 → FAIL `PIN_REMOTE_CHANGED`）。
  4. 在已确认的提交 `C_n`（`pin_pushed.commit`）下读取文件：`git cat-file blob C_n:evidence/pins/pin_Kn.json`。`C_n` 不在取回的历史里 → **FAIL** `PIN_COMMIT_MISSING`（推送成功后远端又丢了它，通常意味着被强制改写）；文件在 `C_n` 下不存在 → **FAIL** `PIN_FILE_MISSING`。
  5. 对读到的**原始字节**计算 SHA-256，必须等于本地文件的摘要，且等于事件日志 `pin_pushed.pin_digest`；不等 → **FAIL** `PIN_CONTENT_MISMATCH`。
  6. 解析 JSON，并检查**规范序列化**：把解析结果按规范再序列化（加换行），必须与原始字节逐字节相同；不同 → **FAIL** `PIN_NOT_CANONICAL`。
  7. 检查字段：`name`、`log`、`run_id`、`end_event`、`line_count` 与期望值一致；`prefix_digest` 等于**从本地日志文件实际重算**的 `P_k`（取前 `line_count` 行的原始字节）；任一不符 → **FAIL** `PIN_FIELD_MISMATCH` 或 `PIN_PREFIX_MISMATCH`。
  8. 祖先关系：`C_n` 必须是 `remote_tip` 的祖先或等于它（`git merge-base --is-ancestor`）；各 pin 的提交按固定顺序 `C_0 → C_1 → … → C_n` 依次是祖先；`remote_tip` 下该文件的内容必须与 `C_n` 下相同（blob 相同，没有被后来的提交改写）。违反 → **FAIL** `PIN_ANCESTRY_VIOLATION` 或 `PIN_REWRITTEN`。祖先检查因历史不全而无法判定 → BLOCKED。
  9. **带外副本核对：** 把上述 `commit`、`prefix_digest`、`pin_digest` 与审核者/负责人留存的副本逐项比对。没有带外副本，或审核者尚未核对 → 该项记 **NOT TESTED**（不是 PASS），整体验收结论里写明「远端已验证，带外未核对」。
  10. **结论的含义：** RV 的 PASS 只表示「取回的远端对象里确有这份内容，且与本地一致」。**远端引用与提交 SHA 本身不是不可伪造的证明**：能强制改写远端分支、或同时控制主机与推送凭据的人，可以让整条链自洽。带外副本、分支保护（禁止强制推送；GitHub 设置，**NOT VERIFIED**）和可选签名/时间戳是对这一局限的补充。
- **门禁（把「先固定 Tokenizer，再接触 val/test」变成可执行条件）：**
  - `G_S4`（2.4）：S4 开始时，监督器**重新**执行 K0、K1 的 RV 并写 `pin_remote_verified`，两者都为 PASS，且 `absence_witness.result=CLEAN`、`tokenizer_hash_logged` 已写，才写 `gate_check(G_S4)=PASS`，之后才允许 `online_switch` 与 validation/test 的 `download_start`。S4 脚本启动时读取日志尾部校验这一点，不满足就 `BLOCKED`。
  - `G_S5`：K0、K2 的 RV 都为 PASS，且 A4、A5 已写，才允许 A6 与 `pre_read_snapshot`。
  - 验收脚本对 K3 的要求（修订 4）：R6.6 由验收脚本**自己**重新执行 K3 的 RV 并逐项核对（4.1 R6.6），不引用运行期写下的 `pin_remote_verified` 结论。验收脚本另验证：首个 validation/test 的 L1+ 事件（`download_start`）的 `seq` 大于 `tokenizer_hash_logged`、`pin_pushed`(K1)、`pin_remote_verified`(K1)=PASS 与 `gate_check`(G_S4)=PASS 的 `seq`；这是**事件日志里的顺序**关系，不是时间关系。
- **信任边界（必须写入每份验收记录）：**
  - 能证明：被固定前缀内的任何行的**修改、插入、删除、重排**，以及固定时刻之后的尾部截断（`line_count` 与总行数对不上），都会使前缀哈希或行数与固定记录不符 → `FAIL`。
  - **不能证明：** 日志内容本身是真实的（脚本可以如实记录了错误的事实，或者在记录器之外操作）；最后一个固定点**之后**追加或改写的行（所以 K3、K4 在流程末端固定，并受收尾上限 `W` 约束）；执行主机与推送凭据同时被控制时，伪造发生在固定**之前**；GitHub 远端本身可信；提交时间戳可信（作者可设定，所以**不用提交时间判断先后**，只用远端祖先关系和审核者的带外副本）。
- **可验证验收条件与负例（合成日志与合成远端；本轮不运行）：**

| 用例 | 预期 |
|---|---|
| 改旧行并重算整条链 | `P_k` 与固定记录不符 → FAIL `PIN_PREFIX_MISMATCH` |
| 在固定前缀内插入一行并重算链 | FAIL |
| 删除末尾若干行 | 行数不符 → FAIL |
| 远端提交里的 `pin_Kn.json` 与本地内容不同（`ls-remote` 的提交 SHA 却一致） | FAIL `PIN_CONTENT_MISMATCH`（证明验证读的是内容，不是引用） |
| 远端 `pin_Kn.json` 字节相同但键顺序/空白不同 | FAIL `PIN_NOT_CANONICAL` |
| `run_id` 或 `name` 不符 | FAIL `PIN_FIELD_MISMATCH` |
| 提交 `C_n` 在取回的历史里不存在 | FAIL `PIN_COMMIT_MISSING` |
| 远端分支被强制改写，`C_n` 不再是 `remote_tip` 的祖先 | FAIL `PIN_ANCESTRY_VIOLATION` |
| 固定文件缺失，或远端无法访问 | BLOCKED `PIN_UNVERIFIABLE` |
| K3 的 `line_count` 小于 `post_read_snapshot` 所在行 | FAIL `R6_POST_NOT_PINNED` |
| 仅在最后一个固定点之后追加一行 | **不被固定点发现**（已知局限，由 K3/K4 位置与 `W` 缩小窗口） |

- **残余风险：** 同「不能证明」；固定动作本身引入了网络出口和一个远端依赖；带外副本依赖人工核对；RV 自身的实现尚未编写。

### 11.3 R6 前后哈希的真实含义与可选加强（对应 D03 / R3-D03；修订 3 补充时序）

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
- **时序（修订 3）：** 最终读后快照必须在 Driver 退出、`children_reaped` 之后、K3 固定**之前**写入，并连同相应的 `gate_result` 一起落在 K3 的前缀之内（2.4、R6.2、R6.6）；不得先固定 K3 再补写关键读后证据。该时序由独立验收的 R6.6 重新核对（4.1）；失败路径没有 `read_phase_closed`，R6.6 记 NOT TESTED（11.9）。
- **残余风险：** 在本草案默认配置下，该检查不覆盖运行期内的 TOCTOU/ABA；负责人需要明确接受或加选控制（R3-D03）。



### 11.4 I4 缺席见证的范围、措辞与局限（对应 I4 / R3-D01；修订 3 统一措辞）

- **统一表述（全文、验收记录、报告只能使用这句话，或与之等价的更弱表述）：** **「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象。」** 本稿不使用、验收记录也**不得写**：「证明从未访问」「证明所有缓存都不含相关内容」「证明不存在未记录的网络或流式读取」。R6/T1 中的「未被打开」按此理解（PROPOSED CLARIFICATION，同意与否由 R3-D01 裁决）。
- **受控目录集合（`absence_witness` 行内必须列出，用解析后的真实路径）：**
  1. Hub 缓存根（`HF_HOME`、`HF_HUB_CACHE`、`HUGGINGFACE_HUB_CACHE` 解析结果）及其下 `datasets--*/blobs/`、`snapshots/*/`、`refs/`、`.no_exist/`；
  2. 下载目标目录（`local_dir`）及其 `.cache/huggingface/download/` 下的 `*.metadata`、`*.incomplete`；
  3. **Xet 块缓存**（`HF_XET_CACHE` 或默认 `…/xet/`；本环境装有 `hf-xet`）；
  4. `datasets` 库缓存（`…/datasets/`）；
  5. 运行目录、`TMPDIR`、`XDG_CACHE_HOME`。

  S0 把这些缓存根设为**新建空目录**，使 S2 之前基线为空。验收脚本检查列表**包含**由环境变量推出的必选目录，缺项 → `UNSCOPED`。
- **检查内容（只读，不读文件内容，不计算内容哈希）：**
  (a) 路径/文件名不含 validation/test 的任何模式（`validation-*`、`test-*`、`*/validation/*`、`*/test/*`）；
  (b) `blobs/` 中的 blob 文件名集合必须**等于**预期集合（S2 的 train blob 名与 README blob 名）；出现 A1 中 val/test 的 oid 名 → 命中；出现其他任何多余 blob → 失败（无法排除它是 val/test）；
  (c) Xet 块缓存**无法按文件归属**：只记录条目数与总大小，来源只能由「基线为空 + 事件日志无 validation/test 的 L1+ 记录 + 请求清单固定」间接支撑，**不能独立证明**；
  (d) 每个目录的条目列表摘要（路径+大小+类型）写入 `absence_witness` 行，并随 K1 外部固定。
- **分层陈述——哪些是什么性质的保证：**

| 层 | 内容 | 性质 |
|---|---|---|
| ① 已观测的客观事实 | 见证时刻、上述受控目录里的路径/文件名/blob 名集合/条目数/大小/列表摘要；事件日志里已记录的操作序列；A1 中三个 split 的 oid | 由脚本只读观察得到，可由验收脚本在同一份日志与目录列表上复核 |
| ② 记录器承诺遵守的操作限制 | 获取与拟合脚本只通过记录器调用 Hub 客户端与文件操作；`tokenizer_hash_logged` 之前不对 validation/test 做 L1+；所有此类调用都有对应事件 | **承诺，不是观测**：记录器之外的调用不会留下记录 |
| ③ 静态检查提供的保证 | 拟合模块源码不出现 validation/test 路径常量、不接受这类路径为参数（I3）；审计模块输出键白名单与 AST 检查（I6、I7） | 只对被检查的源码文本成立，不覆盖未被检查的代码或人手工操作 |
| ④ 无法排除的残余风险 | 受控范围之外的路径；记录器之外的读取路径（不经记录器的 Hub 调用、别的用户/进程/人手工操作）；见证之前下载后又删除的文件；不落盘的流式读取；Xet 块的归属；网络代理侧是否有请求；`auditd`/inotify/出口请求日志等更强手段需要权限与环境配合，**NOT TESTED**，不作为默认要求 | **不能被本规范排除** |

- **PASS 的含义：** `absence_witness.result=CLEAN` 且 I1（事件日志中没有 validation/test 的 L1+ 记录）、I4（受控目录检查）、K1 的 RV=PASS 同时成立，表示**「受控检查本身通过」**。它**不得延伸**为全系统零访问证明；验收记录里把 PASS 对应到上表的 ①②③，并把 ④ 原文抄入「残余风险」栏。
- **结果取值：** `CLEAN`；`HIT`（命中 validation/test 迹象 → FAIL `R6_HELDOUT_TOUCHED_EARLY`）；`UNSCOPED`（Xet 缓存目录在 S0 非空、受控目录列表缺必选项 → BLOCKED / FAIL，见下表）。
- **可验证验收条件与负例（合成缓存目录；本轮不运行）：** 放入 `validation-00000.parquet` → HIT / FAIL；放入以 A1 中 val 的 oid 命名的 blob → HIT / FAIL；放入一个未预期的 blob → FAIL；Xet 缓存目录在 S0 非空 → BLOCKED；受控目录列表缺 Xet → FAIL；只有 train/README 的干净目录 → CLEAN / PASS（且验收记录含上述限定语）；验收记录里出现「证明从未访问」类措辞 → 验收模板检查 FAIL。
- **残余风险：** 见表中 ④。

### 11.5 完整性基础：LFS SHA-256、Git blob SHA-1、Xet 元数据（对应 S9 / R3-D06；修订 3 指向 11.8）

| 基础 | 判定依据（来自 L0 元数据） | 比较对象 | 算法标签 | 说明 |
|---|---|---|---|---|
| **B-LFS** | 元数据含 `lfs.sha256`（及 `lfs.size`） | 本地对**文件内容**算 SHA-256，与 `lfs.sha256` 比较；同时核对大小 | `sha256:` | 与 v1 §3.2「LFS `sha256`（oid）」一致 |
| **B-GIT** | 元数据**不含** `lfs` 字段，只有 `blob_id` | 本地对文件内容按 Git 规则算 `SHA-1("blob " + 字节数 + "\0" + 内容)`，与 `blob_id` 比较 | `git-blob-sha1:` | 只在**已证明该文件非 LFS** 时才有意义；SHA-1 强度弱于 SHA-256 |
| **B-XET** | 元数据含 Xet 内容标识（如 `xetHash`） | **本地无法等价重算**（Xet 哈希不是文件内容的 SHA-256 或 SHA-1，由 Xet 协议定义） | `xet:` | 不得与 SHA-256/SHA-1 比较；若同时有 `lfs.sha256` 则按 B-LFS 判定，Xet 值仅记录 |

- **必须避免的错误（修订 1 的缺陷）：** 对 LFS 文件，Hub 返回的 `blob_id` 是 **LFS 指针文件**（形如 `version https://git-lfs.github.com/spec/v1` / `oid sha256:…` / `size …` 的小文本）的 Git blob SHA-1，**不是内容哈希**。若把内容的 Git SHA-1 与它比较，会永远不符，或（若实现为「相符才算」）错误地以指针为内容。因此「重算 blob SHA-1 与 `blob_id` 比较」**只允许用于 B-GIT**，且前提是已确认没有 `lfs` 字段。
- **规则：**
  1. **新证据**（事件日志、预算账本、固定记录、A1/A2/A4/A5/A8、审计输出）中的所有摘要使用 `算法标签:十六进制` 形式；比较函数**拒绝跨算法比较**（抛错，不返回 False）。**冻结接口已使用的键保持裸格式**，转换边界、解析规则与预期结果见 11.8。来自 Hub 元数据的摘要长度或字符集不符 → BLOCKED。
  2. 每个文件的 `integrity_basis ∈ {B-LFS, B-GIT, B-XET, UNKNOWN}` 由记录下来的机械规则从 L0 元数据得出，写入 A1。
  3. **元数据不足 → 默认 BLOCKED（`INTEGRITY_BASIS_UNKNOWN`）**：包括字段缺失、`lfs` 与 `blob_id` 同时缺失、只有 Xet 值、字段语义与预期不符。「只有本地算出的哈希、没有可比较的来源」不构成完整性检查，同样 BLOCKED。
  4. **草案默认：只接受 B-LFS。** B-GIT 只有在负责人批准、且 `blob_id` 语义在受控的仅 L0 元数据任务（**需另行授权，本草案不执行**）中被验证之后才可启用；B-XET 单独出现 → BLOCKED。三个 split 必须全部具备被接受的基础，否则整体 BLOCKED。
  5. 修订 SHA（`revision=`）仍须等于冻结值（v1 §3.2），它锚定元数据本身。
- **可验证验收条件（合成元数据夹具）：** LFS 且哈希相符 → PASS；LFS 且哈希不符 → FAIL；只有 `blob_id`（B-GIT）→ 默认 BLOCKED；用内容 SHA-1 去比较 LFS 的 `blob_id` → 比较函数拒绝（类型/标签测试）；仅有 `xetHash` → BLOCKED；`sha256:` 与 `git-blob-sha1:` 互比 → 抛错；摘要长度不对 → BLOCKED。
- **NOT VERIFIED / NOT TESTED：** Hub 实际返回的字段名、语义，Xet 后端是否仍返回 `lfs.sha256`，目标环境 `huggingface_hub`/`hf-xet` 的行为——本窗口没有访问网络，均未验证。
- **残余风险：** 若 Hub 元数据本身被篡改，哈希对照没有独立的第二来源（修订 SHA 只能间接锚定）；这一点与 v1 §3.2 的原假设相同。

### 11.6 test 审计的用途限制与输出 Schema（对应 I6 / I8 / R7.6 / R3-D08；修订 3 统一）

**用途。**
- **允许（且仅限）：** (i) 文件完整性核对（11.5）；(ii) 行数、合格行数、一级标题行数、特殊字符串出现次数；(iii) Token 统计：两种口径的计数、最大 Token ID、是否出现 ID 0；(iv) round-trip 不一致行数。
- **禁止：** 把 validation/test 的任何审计结果或内容用于**训练、模型选择、调参、早停、检查点选择、质量评估**（困惑度/损失/BPC/准确率等）、阈值设定、Tokenizer 词表大小或拟合方式的调整，以及由审计结果推导任何设计变更。审计发现异常（如 round-trip 不一致）时的唯一动作是 `FAIL`/`BLOCKED` 并停止 D1，**不得**据此修改 Tokenizer。validation 在 D1 阶段同样只做上述审计；它在后续阶段的使用由那些阶段各自的预注册规定。
- **用途限制始终生效：** 不因审计通过或失败、重跑、`usage_declaration` 校验与否、或进入后续阶段而放宽；任何放宽需要新的、经项目负责人批准的修订。
- **不能证明：** 没有人手工把这些统计用于别的用途；统计本身（计数、最大 ID）会泄露 test 分布的极少量信息（已接受的微小代价，由负责人在 R3-D08 中确认）。
- **与「一次性」的关系：** v1 §5.5 把「最终 test 评估」留给 D3 的一次性事项；本审计**不是评估**。是否仍影响该「一次性」属性，由 R3-D08 裁决；备选是把 test 审计推迟到 D3。

**统一输出 Schema `d1_heldout_audit_v1`（I6 与 `usage_declaration` 的统一；`usage_declaration` 属于 Envelope，不属于 Statistics）。** 整个输出文件是一个 JSON 对象，**顶层键恰好是 `envelope` 与 `statistics`**，规范序列化同 11.2。

| 部分 | 键（**键集合必须完全相等**，不得多也不得少） | 类型 / 约束 |
|---|---|---|
| `envelope` | `schema` | 固定字符串 `d1_heldout_audit_v1` |
| | `run_id` | 字符串，等于 `run_start.run_id` |
| | `spec_ref` | 字符串，等于 `run_start.spec_ref` |
| | `evidence_refs` | 对象，恰好两键：`hub_metadata`（A1 的 `sha256:` 摘要）、`tokenizer_manifest`（A4 的 `sha256:` 摘要） |
| | `usage_declaration` | 对象，恰好两键：`purpose`（固定字符串 `integrity_and_tokenizer_statistics_only`）、`prohibited`（固定的字符串数组，见下） |
| | `usage_declaration_digest` | `sha256:` 摘要 = `usage_declaration` 的**对象摘要**（规范 JSON 的 UTF-8 字节，不加换行） |
| `statistics` | `validation`；`test` | 每个 split 一个对象；若 R3-D08 选择推迟 test 审计，则 `test` 键整体缺席，Schema 去掉该键 |
| `statistics.<split>` | `file_digest` | `sha256:` 摘要（带标签的字符串；这是 statistics 中**唯一**允许的字符串值） |
| | `file_size`、`num_rows`、`qualified_rows`、`h1_rows`、`tokens_total`、`tokens_encode_only`、`eos_prefix_count`、`max_token_id`、`roundtrip_mismatch_rows` | JSON 整数，≥ 0，不是布尔，不是浮点 |
| | `id0_present` | 布尔 |
| | `special_string_counts` | 对象，键集合恰好等于 A4 记录的三个特殊 Token 字符串，值为整数 ≥ 0 |

- **不得出现在 `statistics` 内的东西：** `usage_declaration` 或任何元数据；原始文本；Token ID 序列；逐行结果；任何数组；任何浮点数；模型评估指标（如 `loss`、`ppl`、`bpc`、`accuracy` 等键名）；任何除 `file_digest` 以外的字符串值。
- **`prohibited` 的规范内容（草案文本，待批准）：** `["training","model_selection","hyperparameter_tuning","early_stopping","checkpoint_selection","quality_evaluation","threshold_setting","tokenizer_refit_or_adjustment","design_change_from_audit_results","reporting_as_model_metric"]`。`usage_declaration` 对象的规范 JSON 为 `{"prohibited":[…],"purpose":"integrity_and_tokenizer_statistics_only"}`；其对象摘要在**本草案文本**下为 `sha256:72e378a7b8b0d4a4066e429ef994bd6850fe0ba7788103fc81aa5e83bd85f310`。**这只是草案文本的摘要，不是已批准值。**
- **规范文本与哈希如何核对：** 项目负责人批准（R3-D08、R3-D10）后，已批准文本的对象摘要写入授权记录文件（`authorization_ref` 所指文件，其自身 SHA-256 也被记录）。验收脚本读取该已批准摘要，并核对：(1) `usage_declaration` 重新计算的对象摘要等于已批准摘要；(2) `usage_declaration_digest` 等于该重新计算的值。**在批准之前，验收脚本不得用草案摘要代替，只能判 `BLOCKED USAGE_DECLARATION_UNAPPROVED`。**

**缺字段 / 多字段 / 错误声明 / 意外嵌套的预期结果（Schema 规范，本轮不运行任何检查）：**

| 情形 | 预期 |
|---|---|
| 缺少任一必填键（任一层级） | FAIL `AUDIT_SCHEMA_MISSING` |
| 多出任何键（任一层级）；`statistics` 内出现 `usage_declaration` | FAIL `AUDIT_SCHEMA_EXTRA` |
| 键名命中禁用清单（`loss`、`ppl`、`bpc`、`accuracy`、`text`、`ids`、`token_ids`、`rows` 等） | FAIL `AUDIT_FORBIDDEN_CONTENT` |
| 类型错误：布尔当整数、浮点、负数、字符串当数字 | FAIL `AUDIT_SCHEMA_TYPE` |
| `statistics` 内出现数组、未声明的对象、或 `file_digest` 以外的字符串值 | FAIL `AUDIT_UNEXPECTED_NESTING` |
| `usage_declaration` 缺失 | FAIL `AUDIT_USAGE_DECLARATION_MISSING` |
| `usage_declaration` 与已批准文本不符，或 `usage_declaration_digest` 与其内容不符 | FAIL `AUDIT_USAGE_DECLARATION_MISMATCH` |
| 已批准摘要尚未提供 | BLOCKED `USAGE_DECLARATION_UNAPPROVED` |
| 输出文件缺失 | BLOCKED `AUDIT_OUTPUT_MISSING` |
| 输出文件不是合法 JSON | FAIL `AUDIT_SCHEMA_TYPE` |

**最小正负例（仅示意，数值是占位符，不是数据；本轮不运行）：**

正例（`<hex64>` 表示 64 位小写十六进制）：
```
{"envelope":{"evidence_refs":{"hub_metadata":"sha256:<hex64>","tokenizer_manifest":"sha256:<hex64>"},
 "run_id":"<id>","schema":"d1_heldout_audit_v1","spec_ref":"<ref>",
 "usage_declaration":{"prohibited":[…10 项…],"purpose":"integrity_and_tokenizer_statistics_only"},
 "usage_declaration_digest":"sha256:<hex64>"},
 "statistics":{"validation":{"eos_prefix_count":0,"file_digest":"sha256:<hex64>","file_size":0,"h1_rows":0,
 "id0_present":false,"max_token_id":0,"num_rows":0,"qualified_rows":0,"roundtrip_mismatch_rows":0,
 "special_string_counts":{"<s1>":0,"<s2>":0,"<s3>":0},"tokens_encode_only":0,"tokens_total":0},"test":{…同上…}}}
```
负例：N1 删去 `envelope.usage_declaration` → `AUDIT_USAGE_DECLARATION_MISSING`；N2 `statistics.validation` 里加 `usage_declaration` → `AUDIT_SCHEMA_EXTRA`；N3 `statistics.validation.num_rows` 写成 `1.0` 或 `true` → `AUDIT_SCHEMA_TYPE`；N4 `statistics.validation` 里加 `ppl` → `AUDIT_FORBIDDEN_CONTENT`；N5 `statistics.test` 里加数组 `per_row_tokens` → `AUDIT_UNEXPECTED_NESTING`；N6 改动 `usage_declaration.purpose` 的一个字母 → `AUDIT_USAGE_DECLARATION_MISMATCH`；N7 `special_string_counts` 缺一个特殊字符串 → `AUDIT_SCHEMA_MISSING`。

- **机器可核对的其余部分：** 审计模块的 AST 静态检查（不得导入模型、训练、优化器代码；不得出现 held-out 路径常量以外的路径用法；见 I3/I7）。
- **残余风险：** 同「不能证明」；Schema 只约束输出文件的形状，不能阻止有人另写文件。

### 11.7 依赖图与前缀哈希的核对方法（对应第 5 节；修订 3 纠正统计）

- **构图来源：** 只从第 5 节的**正式边列表**（`node` / `ref` / `rec` / `sub` 行）构图，节点名按「空白分隔的任意非空记号」解析，**不使用只识别带数字节点名的正则**（修订 2 的解析方式漏掉了 `BP`，因此漏计了 `PIN4 → BP` 与 `A8 → BP` 两条边）。
- **核验方式（两种，必须都通过）：** (1) 拓扑排序（Kahn 算法）：访问节点数必须等于节点总数；(2) 层级严格递减：每条边 `X → Y` 必须满足 `level(Y) < level(X)`。另做两项交叉核对：正式边列表的 `node` 层级必须与第 5 节人读表格的层级一致；人读表格里每一行「→」右侧的节点集合必须等于正式边列表中 `ref` 边的集合。
- **统计的写法：** 节点数、`ref`/`rec`/`sub` 各自的边数与总数，以及完整的节点与边清单，记录在检查点；**不得照抄他人给出的数字**，必须由脚本从边列表重新计数，若与 Work 复核的数字（17 个节点、`ref` 31 条）不符，报告 FAIL。
- **修订 2 的统计错误及更正：** 修订 2 的检查点记载「29 条边」，这是错误的：漏计 `PIN4 → BP`、`A8 → BP`。该检查点原文**保留不改**，修订 3 的检查点追加更正。
- **隐含依赖：** 日志行里记录了工件摘要，也构成依赖（`rec`）；前缀包含是依赖（`sub`）。三类边合并后仍必须无环。这样可以发现类似「LP3 记录了 A7 的摘要，而 A7 又引用 LP3」的隐藏循环。
- **S3 的写入顺序（与 2.4 的规范顺序一致）：** ① 保存 `tokenizer.json` → ② 完成 T2–T6 的 `check_result` → ③ `absence_witness` → ④ `tokenizer_hash_logged`（第 `k1` 行，内容是 `tokenizer.json` 的摘要，**不是** A4 的摘要）→ ⑤ 计算 `P_{k1}`，写 `pin_K1.json`，推送，追加 `pin_pushed`(K1)（第 `k1+1` 行）→ ⑥ `pin_remote_verified`(K1) → ⑦ 写 A4（引用 `P_{k1}` 与 PIN1）→ ⑧ 追加 `manifest_written`(A4)。验收脚本核对：`tokenizer_hash_logged` 的行号 = `pin_K1.json` 的 `line_count − 1`。
- **预算账本：** BP0（`open` 行）与 BP（到 `close`，选项 Y 为到 `pin_phase`）都是前缀；A8 同时引用 PIN0 与 PIN4；验收脚本另验证 BP0 是 BP 的前缀（`sub`）。
- **修订 4 的重新计算：** 修订 4 新增的事件（`run_aborted`）、字段与流程**没有引入新的工件、也没有引入新的摘要引用**（失败路径只使用既有节点的子集，11.9），所以第 5 节的 17 个节点与 43 条边不变；但仍按本节的方法**重新构图并重新计数**（结果记录在检查点），不沿用上一轮的结果。
- **残余风险：** 边列表由人工从设计转成，自检只能证明「表里写的依赖」无环，不能证明实现时没有加入表外依赖；所以验收脚本也要对**实际生成的清单与日志**做同样的构图、无环与层级检查。

### 11.8 摘要格式与冻结接口的边界（对应 11.5 规则 1；修订 3 新增）

**原则：** 新证据可以用带算法标签的结构；**冻结代码已经使用的键保持原来的裸格式**。新的验收模块负责读取、解析和类型化校验两种格式，转换只发生在清单生成器与验收模块里。**不修改冻结 Reader、Verifier、Driver。**

**格式定义：**
- **带标签摘要**（仅用于新证据）：`<算法>:<小写十六进制>`。已登记的算法与长度：`sha256:`（64）、`git-blob-sha1:`（40）、`git-commit-sha1:`（40）、`xet:`（由协议决定，不比较）。
- **冻结裸格式**：冻结代码里的 64 位小写十六进制正则 `^[0-9a-f]{64}$`（读取器中名为 `HEX64`，驱动器与验证器中名为 `H64`）与 40 位的 `^[0-9a-f]{40}$`（读取器 `HEX40`、验证器 `H40`，用于 `dataset.revision`）。大写、带前缀、带空白都会被冻结代码拒绝。（源码核对：`d1_reader.py` 第 27–28 行，`d1_driver.py` 第 31 行，`d1_verifier.py` 第 29–30 行。）

**Schema 对照表（新接口 ↔ 冻结接口）：**

| 位置 | 新接口（带标签） | 冻结接口（裸格式） | 转换边界与责任 |
|---|---|---|---|
| `runtime_manifest.json` → `parquet_sha256` | A2：`files.train.digest = "sha256:<64>"` | `parquet_sha256`：裸 `^[0-9a-f]{64}$`（读取器、验证器逐字比较） | A6 生成器**去掉 `sha256:`** 后写入；仅接受标签为 `sha256` 的输入 |
| `runtime_manifest.json` → `tokenizer_sha256` | A4：`tokenizer.digest = "sha256:<64>"` | `tokenizer_sha256`：裸 64 位十六进制 | 同上 |
| `runtime_manifest.json` → `actual_vocab_size` | A4：整数 | 整数 | 无转换 |
| `formal.hub_revision` 与数据集 `revision` | A1：`revision = "git-commit-sha1:<40>"` | 裸 `^[0-9a-f]{40}$`，且必须等于冻结配置的 `revision` | A6 生成器去掉 `git-commit-sha1:` |
| `formal.lfs_oid_parquet` | A1：`files.train.lfs_sha256 = "sha256:<64>"` | 裸 64 位十六进制，Driver 要求等于 `parquet_sha256`（字符串逐字相等） | 去掉 `sha256:`；若 A1 的基础不是 B-LFS（11.5）则**不生成 `formal` 块**，由验收脚本判 BLOCKED |
| `formal.tokenizer_fit_manifest_sha256` | A8/A6 内的引用：`sha256:<A4 文件原始字节的摘要>` | 裸 64 位十六进制 | 去掉 `sha256:` |
| `formal.authorization_ref` | 授权记录文件路径 + `sha256:` 摘要（R3-D10） | 非空字符串 | 路径字符串原样写入；摘要只记在 A8 |
| 冻结输出：游标、trace、`manifest_sha256`、`chain_hash`、`row_text_sha256` 等 | 验收模块读取后**在内存里**按算法 `sha256` 做类型化解析 | 保持冻结代码写出的裸格式 | 不改写这些文件；验收脚本用 `parse_frozen_hex()` 读取 |
| 事件日志、预算账本、`pin_Kn.json`、A1/A2/A4/A5/A8、审计输出 | 所有摘要字段使用带标签格式（含 `prev`、`prefix_digest`、`pin_digest`） | — | 仅新模块读写 |

**解析与比较规则（由新的摘要模块承担，暂定名 `d1_digest.py`，尚未编写）：**
1. `parse_tagged(s)` 返回 `(算法, 字节)`；`parse_frozen_hex(s, 长度)` 只接受裸格式。两个函数互不兼容：向 `parse_frozen_hex` 传带前缀的值，或向 `parse_tagged` 传裸值，一律报格式错误。
2. `compare(a, b)` 要求两个带标签值的算法相同；**跨算法比较抛出异常**（`DIGEST_ALGO_MISMATCH`），不返回 False。
3. **不得把带 `sha256:` 前缀的值直接写入冻结代码要求裸 SHA-256 的键。** 清单生成器在写出 A6 之前必须通过一次「冻结键校验」：每个冻结键的值必须能通过 `parse_frozen_hex`。冻结代码自己也会拒绝带前缀的值（失败即关闭），但不得依赖这一点。

**预期结果表：**

| 情形 | 来源 | 预期 |
|---|---|---|
| 非法算法标签（如 `md5:`）、未知标签 | 新证据 | FAIL `DIGEST_MALFORMED` |
| 非法算法标签、长度或字符集不符 | Hub 元数据（外部输入） | BLOCKED `INTEGRITY_BASIS_UNKNOWN` |
| 新证据字段里是裸值（无标签） | 新证据 | FAIL `DIGEST_UNTAGGED` |
| 大写十六进制、含空白 | 任一 | 格式错误（同上两行，依来源） |
| 冻结键里出现带前缀的值 | A6 生成时 | FAIL `FROZEN_KEY_TAGGED`（不写出文件） |
| 冻结键里是合法裸值 | A6 生成时 | 通过 |
| 跨算法比较（如 `sha256:` 对 `git-blob-sha1:`） | 任一 | FAIL `DIGEST_ALGO_MISMATCH`（异常，不是静默的不等） |
| 同算法、值不同 | 任一 | FAIL `DIGEST_MISMATCH` |
| 同算法、值相同 | 任一 | 通过 |

**残余风险：** 转换边界由人工设计，生成器尚未编写；冻结代码对未登记键的容忍（"额外键被忽略"）只经源码检查，没有在本窗口运行验证；`xet:` 标签的值不可本地重算，只能记录。

### 11.9 异常终止的收尾与证据归档（C04-02；修订 4 新增）

**适用范围：** S0–S5 任一阶段发生超时、中断、校验失败（FAIL / BLOCKED 的检查或完整性不符）、或子进程无法确认退出。**不修改冻结 Driver**；以下全部由外层监督器与新脚本在 Driver 之外完成，Driver 自己的退出（包括它自己的内部超时和非零退出码）照实记录，属于**正常路径**，不触发本节。

**(a) 三个相互独立的维度（不得混用）：**

| 维度 | 取值 | 由谁写入 | 含义 |
|---|---|---|---|
| 预算结果 | `WITHIN_BUDGET` / `EXCEEDED` / `UNPROVABLE` | 监督器 `close.result`，S6 复核 | **只**描述时间与账本有效性。`WITHIN_BUDGET` 不表示实验成功 |
| 运行状态 | `COMPLETED` / `ABORTED` | 监督器 `close.run_state` | 证据是否完整地走完 S0–S5：`el_end_event` 为 `read_phase_closed` 即 `COMPLETED`（即使 S5 的 `s5_status` 是 `DRIVER_NONPASS` 或 `GATE_FAILED`，证据仍完整）；为 `run_aborted` / `unwritable` / `none` 即 `ABORTED` |
| 实验最终状态 | 失败路径：`BLOCKED(code)` 或 `FAIL(code)`（`run_aborted.final_status`）；成功路径：S6 输出 `NOT_ACCEPTED` 或 `ALL_GATES_PASS_CANDIDATE` | 失败路径由监督器；成功路径由 S6 验收脚本 | 实验结论。**脚本从不宣布 D1 PASS**（第 6 节） |

- **映射规则：** (1) `EXCEEDED` ⇒ 最终状态至少是 `BLOCKED(budget_exceeded)`，永远不是候选通过；(2) `UNPROVABLE` ⇒ `BLOCKED(budget_unprovable)`；(3) `ABORTED` ⇒ 最终状态取 `run_aborted.final_status`，S6 输出 `NOT_ACCEPTED`；(4) `COMPLETED` 且 `WITHIN_BUDGET` 且所有必需闸门都有证据并通过，才可能是 `ALL_GATES_PASS_CANDIDATE`；(5) 多个原因并存时，最终状态取最严重者（`FAIL` 高于 `BLOCKED`，同级取最早发生者），所有原因都列出。

**(b) 通用收尾顺序（监督器；每一步失败都只追加「缺失证据」说明，不回头改写已写的行）：**
1. 不再启动新阶段（账本状态机：`stage_end` 的 `status` 不是 `ok` 之后只允许 `close`）。
2. 对仍在运行的进程做终止协议（11.1(d) T1–T7）或残留检查（T5–T6）；记录 `reap_done` / `children_reaped`。
3. 事件日志（若仍可写）依次追加：事实性事件（`interrupted` / `driver_exit` / `children_reaped`，S5 回收已确认时可补 `post_read_snapshot`、`gate_result`、`manifest_written`(A7, `partial`=true)）→ **`run_aborted`**（`cause`、`final_status`、`code`、`missing_evidence`、`partial_artifacts`）。**监督器不写任何 PASS / NOT_APPLICABLE**；已有的 PASS 事件保持原样且不被升级为整体通过。
4. 账本 `stage_end` → `close`（选项 X；取值规则见 11.1(e)。选项 Y 见 (f)）。`close.run_state=ABORTED`，`el_end_event=run_aborted`；若事件日志已不可写，则 `el_end_event=unwritable`，`abort_cause` 与诊断直接写在 `close` 里。
5. 收尾阶段 `W`（选项 X；选项 Y 在 `close` 之前做同样的事，见 (f)）：对已存在的终点事件产生并推送 pin，K3 的 `end_event` 是 `run_aborted`，K4 是账本到 `close`（选项 Y 为 `pin_phase`）；执行 RV。**终点事件不存在的 pin 不产生**（例如 S4 中断时没有 K2），连同推送失败的 pin 一起记入 `wrapup_end.pins_missing`（附原因）。
6. 运行目录**原样保留**：不删除、不清理、不改名；`*.partial` 永不转正。
7. S6 以「失败路径模式」运行：输出 `NOT_ACCEPTED`，逐项列出已有证据、缺失证据（NOT TESTED）和最终状态。

**(c) 四条具体流程（预期序列；`E` = 事件日志，`B` = 账本；与 2.4 的注册表一致）：**

**F1 — S4 中断。** 先区分两种触发方式，**账本转换不同**：

**F1a — 监督器自己收到终止信号（SIGINT / SIGTERM）：** 监督器必须按合法转换执行终止协议。
```
# FLOW F1a
E check_result R7.3 PASS
B terminate_begin interrupt
B terminate_signal TERM
B reap_done
E interrupted
E check_result R7.7 BLOCKED
E run_aborted INTERRUPTED
B stage_end S4
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```
（如 `G_term` 内未退出，`terminate_signal TERM` 之后追加 `terminate_signal KILL`；转换路径 `STAGE`→`TERMINATING`→`REAPED`→`OPEN`→`CLOSED`→`DONE`。）

**F1b — 只有 S4 阶段进程被外部信号杀死，监督器没有收到信号，且没有存活的后代：** 账本**没有进入 `TERMINATING`**，因此**不得**写 `terminate_signal` 或 `reap_done`；监督器先用 `waitpid` 收集退出状态（被信号终止），做 T6 残留检查，无残留后直接写 `stage_end{status: failed, exit: signal}`。
```
# FLOW F1b
E check_result R7.3 PASS
E interrupted
E check_result R7.7 BLOCKED
E run_aborted INTERRUPTED
B stage_end S4
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```
（转换路径 `STAGE`→`OPEN`（`stage_end` failed）→`CLOSED`→`DONE`。）

**F1c — 阶段进程被外部信号杀死，但 T6 发现仍存活、需要主动终止的后代：** 此时才进入 `TERMINATING`，`reason`=supervisor_abort，之后与 F1a 相同。
```
# FLOW F1c
E check_result R7.3 PASS
B terminate_begin supervisor_abort
B terminate_signal TERM
B reap_done
E interrupted
E check_result R7.7 BLOCKED
E run_aborted INTERRUPTED
B stage_end S4
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```

- **共同点：** 保留已下载的 validation/test 文件（K1 之后合法获得）、`*.partial` 审计输出、已写的日志与账本、K0 / K1 及其 RV 记录；缺失 R7.4–R7.6（若未完成）、`heldout_audit_done`、K2、A5、A6、A7。预算结果通常 `WITHIN_BUDGET`；运行状态 `ABORTED`；最终 `BLOCKED(interrupted)`；R7.7 为 BLOCKED。重新运行必须用新的运行目录和新的空缓存（S0 的要求）。
- **异常预期：** F1b 里出现 `terminate_signal` 或 `reap_done`（没有 `terminate_begin`）→ BLOCKED `LEDGER_BAD_TRANSITION`；F1b 里 T6 实际发现了存活后代却直接写 `stage_end` 而不进入 `TERMINATING` → BLOCKED `residual_process`（`RESIDUAL_NOT_TERMINATED`）；F1a / F1b / F1c 里 `interrupted` 之后又出现 `heldout_audit_done`、或 `stage_end.status`=ok → FAIL（`EVENT_ORDER_VIOLATION` / `STAGE_STATUS_MISMATCH`）。

**F2 — S5 超时（监督器截止时间到达时冻结 Driver 仍在运行）：**
```
# FLOW F2
B terminate_begin deadline
B terminate_signal TERM
B terminate_signal KILL
B reap_done
E driver_exit budget
E children_reaped
E manifest_written A7
E post_read_snapshot
E gate_result R6.1
E gate_result R6.2
E gate_result R6.3
E run_aborted TIMEOUT
B stage_end S5
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```
- 其中 `manifest_written`(A7) 带 `partial`=true；`post_read_snapshot` 与 `gate_result` 仅当 `children_reaped.confirmed`=true 才补做，且只是对机械检查的**如实记录**——它们可以是 PASS，但**整体仍是失败路径**，没有 `read_phase_closed`，R6.6 记 NOT TESTED。
- 预算结果 `EXCEEDED`；运行状态 `ABORTED`；最终 `BLOCKED(budget_exceeded)`；终止耗时 `kill_overhead_ns` 必须记录（11.1(d)）。

**F3 — S5 残留进程（Driver 自己退出，但回收检查发现残留，或终止后无法确认退出）：**
```
# FLOW F3a (残留被终止并确认)
E driver_exit none
B terminate_begin supervisor_abort
B terminate_signal TERM
B reap_done
E children_reaped
E manifest_written A7
E post_read_snapshot
E gate_result R6.1
E gate_result R6.2
E gate_result R6.3
E run_aborted RESIDUAL_PROCESS
B stage_end S5
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
# FLOW F3b (无法确认退出)
E driver_exit none
B terminate_begin supervisor_abort
B terminate_signal TERM
B terminate_signal KILL
B reap_done
E children_reaped
E run_aborted TERMINATION_UNCONFIRMED
B stage_end S5
B close
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B wrapup_end
E manifest_written A8
```
- F3a：`children_reaped.residual_found`=true、`confirmed`=true；预算结果按时间判定（可以是 `WITHIN_BUDGET`）；最终 `BLOCKED(residual_process)`。F3b：`confirmed`=false，仍有进程可能触碰 train 文件，所以**不补** `post_read_snapshot`、不写 A7；`close.result=UNPROVABLE`；最终 `BLOCKED(termination_unconfirmed)`。

**F4 — 监督器异常退出（被杀、崩溃、账本写失败后以退出码 70 退出）：**
- 监督器已不存在，没有任何收尾可做：**没有 `close`、没有 `run_aborted`（除非它在崩溃前已写出）、没有 K3 / K4**。阶段进程以 `PR_SET_PDEATHSIG`（由监督器启动它们的 `exec` 包装器在 `exec` 之前设置；该设置跨 `execve` 保留，**目标环境 NOT TESTED**）在监督器死亡时被内核杀死，尽力避免孤儿进程继续写文件。
- 事后处理只能由**另一个**只读工具完成：S6 验收脚本的 `--postmortem` 模式。规则（与 2.4「后验模式例外」一致）：
  1. **不续写、不修复、不截断**原账本与原事件日志；不向它们追加任何行，包括 `manifest_written`(A8)、`pin_pushed`、`wrapup_end`、`close`、`run_aborted`。验收脚本开始时记录两个文件的 SHA-256，结束时复核。
  2. 只产生两个**独立**文件：(a) `evidence/postmortem.json`（独立叶子文件，**不是**图节点，内容：最后有效的 `seq`、末行是否撕裂、两份链是否完整、有无 `run_aborted`、缺失的 `close` / K3 / K4、观测到的 `boot_id`、残留进程的尽力扫描、`cause=SUPERVISOR_EXIT`，以及原日志里 `run_aborted.final_status`（如有））；(b) 后验 A8（`evidence/acceptance_A8_postmortem.json`，`mode`=postmortem）。
  3. 后验 A8 **只能**逐项引用原运行中现存的工件与 `postmortem.json` 的摘要，不存在的节点标 `absent` 并说明原因（BP、PIN3、PIN4 必然缺失）；`postmortem.json` 不引用后验 A8（避免环）；后验 A8 的摘要不写入任何原日志，只出现在验收输出和证据提交里。因此依赖图的节点与边**没有变化**：后验 A8 的引用是现有 `A8 → …` 边的子集加一个叶子文件。
  4. 可对现存前缀额外计算并推送标注为 `late=true` 的 pin（文件名 `late_*.json`，不叫 K3 / K4），它们只作为叶子证据列入 `postmortem.json`，**不等同于 K3 / K4，也不能提升任何状态**。
- **状态规则：** 没有 `close` → 预算结果记 `UNPROVABLE`；运行状态 `ABORTED`；验收输出**始终** `NOT_ACCEPTED`，最终状态**不低于** `BLOCKED(budget_unprovable)`（原因 `SUPERVISOR_EXIT`）。即使事件日志里已有 `run_aborted`，也不因此升级；若其 `final_status` 为 `FAIL`，则取更严重的 `FAIL`。缺 `close`、`run_aborted`、K3 / K4 时不得出现 `ALL_GATES_PASS_CANDIDATE`。若 `close` 已存在，则不是 F4，按常规 S6 与 `wrapup_end` 规则处理。

**(d) 验收预期（失败路径；S6 的验收脚本核对，本轮不运行）：**

| 用例 | 预期 |
|---|---|
| F1：存在 `interrupted` 之后又出现 `heldout_audit_done` | FAIL `EVENT_ORDER_VIOLATION` |
| F1：`run_aborted` 缺失但账本 `close.run_state=ABORTED` 且 `el_end_event=run_aborted` | FAIL `EVENT_LOG_BROKEN` |
| F2：监督器代写的事件里出现 `check_result`=PASS 或 `NOT_APPLICABLE` | FAIL（监督器不得代写 PASS） |
| F2：`read_phase_closed` 与 `run_aborted` 同时存在 | FAIL `EVENT_ORDER_VIOLATION` |
| F2：缺 `kill_overhead_ns` | 验收 FAIL |
| F3b：已写 `post_read_snapshot`（`confirmed`=false 时） | FAIL `EVENT_ORDER_VIOLATION` |
| 任一失败路径：验收输出 `ALL_GATES_PASS_CANDIDATE` | FAIL（必须 `NOT_ACCEPTED`） |
| F1b：没有 `terminate_begin` 却出现 `terminate_signal` / `reap_done` | BLOCKED `LEDGER_BAD_TRANSITION` |
| F1b：T6 发现存活后代却直接 `stage_end`，没有进入 `TERMINATING` | BLOCKED `residual_process`（`RESIDUAL_NOT_TERMINATED`） |
| F1a / F1b / F1c：已有 `interrupted` 而 `stage_end.status`=ok | FAIL `STAGE_STATUS_MISMATCH` |
| 任一失败路径：缺失的 pin 没有出现在 `wrapup_end.pins_missing` 且没有说明原因 | FAIL |
| F4：存在 `postmortem.json` 但原账本或原事件日志被改动（续写、截断、修复末行、追加任何行） | FAIL |
| F4：原事件日志里出现由后验产生的 `manifest_written`(A8) | FAIL |
| F4：后验 A8 引用了不存在的节点（BP、PIN3、PIN4 等）而不是标 `absent` | FAIL |
| F4：后验验收输出的状态高于 `BLOCKED(budget_unprovable)` | FAIL |
| F4：没有 `close`，验收输出预算结果 `WITHIN_BUDGET` | FAIL |
| 失败路径：被 `rec` 边引用的摘要指向层级更高的节点（构图检查） | FAIL |

**(f) 选项 Y 下的失败路径（FINAL-03）。** 上面 F1–F3 的事件序列**全部采用选项 X**（先 `close`、后 pin、最后 `wrapup_end`）。若负责人在 R3-D07 选择选项 Y，**不得**复用「先 `close` 后 pin」；失败路径按下面的变换执行，且所需的账本状态转换已登记于 2.4(b) 与 11.1(b)：
- **变换规则（对 F1a、F1b、F1c、F2、F3a、F3b 一律适用）：** 把尾部
  `B stage_end Sx` → `B close` → `E pin_pushed K3` → `E pin_remote_verified K3` → `E pin_pushed K4` → `E pin_remote_verified K4` → `B wrapup_end` → `E manifest_written A8`
  改为
  `B stage_end Sx` → `B pin_phase` → `E pin_pushed K3` → `E pin_remote_verified K3` → `E pin_pushed K4` → `E pin_remote_verified K4` → `B close` → `E manifest_written A8`；其余各行（含 `run_aborted`、`terminate_*`、`reap_done`）不变。
- **与选项 X 的差别：** K3 的终点仍是 `run_aborted`，紧邻其后的 `pin_pushed`(K3) 不变；K4' 是账本到 `pin_phase` 为止的前缀，它包含非 ok 的 `stage_end` 与全部终止记录，**不含 `close`**；没有 `wrapup_end`，pin 的成败写入 `close.pins_verified` / `pins_missing`；`pin_phase` 到 `close` 的间隔受上限 `W` 约束。
- **示例：F2（S5 超时）在选项 Y 下的尾部：**
```
# FLOW Y-F2-TAIL
E run_aborted TIMEOUT
B stage_end S5
B pin_phase
E pin_pushed K3
E pin_remote_verified K3
E pin_pushed K4
E pin_remote_verified K4
B close
E manifest_written A8
```
- **成功路径在选项 Y 下：** `E read_phase_closed` → `B stage_end S5` → `B pin_phase` → `E pin_pushed K3` → `E pin_remote_verified K3` → `E pin_pushed K4` → `E pin_remote_verified K4` → `B close` → `E manifest_written A8`。
- **`ANOMALY` 之后：** 账本一旦进入 `ANOMALY`，只允许 `close`；选项 Y 下不写 `pin_phase`，K3 / K4' 记入 `close.pins_missing`（原因 `LEDGER_ANOMALY`）。F4（监督器已不存在）与选项无关，处理方式不变。
- **异常预期：** 选项 Y 下 `close` 先于 `pin_phase`，之后又出现 K3 / K4' 的推送 → FAIL `OPTION_Y_ORDER_VIOLATION`；选项 X 下出现 `pin_phase` → FAIL；`ANOMALY` 之后出现 `pin_phase` → BLOCKED `LEDGER_BAD_TRANSITION`。
- 若将来对 Y 的失败路径还有本节没有覆盖的情形，该情形记为 `OPTION_Y_FAILURE_PATH_NOT_SPECIFIED`（BLOCKED），在负责人选用 Y 之前必须先补充规范；目前 F1–F3、F4 与成功路径已覆盖。

**(e) 残余风险：** 监督器自身故障时只能靠事后只读工具与此前已固定的 pin（K0、K1、K2…）取证；`PR_SET_PDEATHSIG`、`/proc` 扫描在目标环境 NOT TESTED；失败路径的 `missing_evidence` 与 `partial_artifacts` 由监督器列出，监督器本身出错时列表可能不全，所以验收脚本另做独立的目录列表对照；收尾阶段的 pin 推送在无网络时无法完成——这只会让缺失证据增多，不会让任何状态变好。

## 12. 修订 2 逐项记录（F3B-D1-SPEC-R3-REVIEW-002）

> **修订 3 说明：** 本节是修订 2 的**历史记录**，保留原文。其中被修订 3 取代的规则（预算账本关闭与终止协议、K3 终点、远端 pin 的验证方式、摘要格式边界、统一审计 Schema、依赖图统计）以第 14 节和第 2.4、5、11 节的现行文字为准。

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

## 14. 修订 3 逐项记录（F3B-D1-SPEC-R3-REVIEW-003）

背景：ChatGPT Work 对修订 2（提交 `eeea55269df485d3e6305a82a3c478ef141a2788`）的独立审核结论为 **FAIL**，并对 GitHub 上的 R3 原文复核；本轮只做文档纠正，不重新设计 R3。每项记录：审核输入、问题、原规则、修订规则、可验证验收条件、残余风险、状态。所有修订规则均为 `PROPOSED / NOT APPROVED`；R3-D01…D11 仍全部 `PENDING OWNER DECISION`。第 12 节是修订 2 的历史记录，保留原文；其中与本节冲突的规则以本节和 11 的现行文字为准。

### 14.1 FIX-01：跨进程预算与终止协议闭合

| 栏 | 内容 |
|---|---|
| 审核输入 | §11.1、R3-D07：账本使用 `CLOCK_BOOTTIME`，但未规定监督器结束、子进程终止与账本关闭的先后；K4 固定与 30 分钟预算可能形成不可能满足的要求。 |
| 原规则 | 修订 2 的 11.1：监督器到点发 SIGTERM，宽限后 SIGKILL；`close` 的时机和失败处理未规定。 |
| 修订规则 | 11.1(b) 严格状态转换；(c) 监督器以同一 `boot_id`、同一账本、独立进程组与子收割者控制所有受计时进程；(d) 终止协议 T1–T7（进程组终止、等待、退出码、残留检查，SIGTERM/SIGKILL 时间计入）；(e) `close` 写入前提与写失败处理；(f) 预算包含/不包含的活动，选项 X（K3/K4 在 `close` 之后，有上限 `W`）与选项 Y（固定动作在预算内、K4' 不含 `close`），各给出可实施的顺序；不修改冻结 Driver 的超时机制。 |
| 验收条件 | 11.1 的合成账本用例 (a)–(m)；2.4(b) 的状态转换表可被机器检查；超限、回收未确认、账本缺失、关闭不完整均不得 PASS。 |
| 残余风险 | 见 11.1 末尾：同信任域、绕过监督器、1 s 轮询粒度、不可中断进程、`PR_SET_CHILD_SUBREAPER` 与 `/proc` 在目标环境 NOT TESTED、参数 τ / `G_term` / `G_kill` / `W` 待裁决、X 与 Y 的各自代价。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D07；X / Y 二选一）。 |

### 14.2 FIX-02：远端 Pin 内容验证

| 栏 | 内容 |
|---|---|
| 审核输入 | §11.2：`git ls-remote` 只能证明远端引用与提交 SHA，不能证明 `pin_Kn.json` 内容与本地一致。 |
| 原规则 | 修订 2 的 11.2 / 门禁：S4 启动时检查 pin 文件存在并用 `git ls-remote` 确认。 |
| 修订规则 | 11.2 的远端内容验证程序 RV：完整取回远端对象 → 在已确认提交下读取 `pin_Kn.json` 原始字节 → 核对 SHA-256、规范序列化、`prefix_digest`（从本地日志重算）、`line_count`、`run_id`、`name` → 核对祖先关系与未被改写 → 带外副本核对（未核对记 NOT TESTED）→ 远端不可访问 BLOCKED，文件缺失/内容不符 FAIL；S4 门禁 `G_S4` 要求 K0、K1 刚做过 RV 且为 PASS，才允许 validation/test 的任何 L1+ 操作。 |
| 验收条件 | 11.2 的负例表（尤其「`ls-remote` 的提交 SHA 一致而内容不同 → FAIL」）；验收脚本验证首个 validation/test `download_start` 在事件日志中的顺序晚于 `tokenizer_hash_logged`、`pin_pushed`(K1)、`pin_remote_verified`(K1)=PASS、`gate_check`(G_S4)=PASS。 |
| 残余风险 | 远端引用与提交 SHA 不是不可伪造证明；强制改写或同时控制主机与凭据可让链自洽；分支保护 NOT VERIFIED；带外核对依赖人工；RV 实现未编写。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D09 的固定方式；R3-D01）。 |

### 14.3 FIX-03：R6 最终读后哈希进入固定证据

| 栏 | 内容 |
|---|---|
| 审核输入 | §4.1、§5、§11.2、§11.3：K3 定义为 `driver_exit` 时刻的前缀，最终 `post_read_snapshot` 是否在其内不明确。 |
| 原规则 | K3 = `driver_exit` 所在行的前缀；`post_read_snapshot` 的位置未规定。 |
| 修订规则 | 新增事件 `children_reaped`、`gate_result`、`read_phase_closed`；**K3 的终点改为 `read_phase_closed`**；规定顺序：`driver_exit` → `children_reaped`（子进程状态收集完成）→ `manifest_written`(A7) → `post_read_snapshot`（最终 train Parquet SHA-256，核对读前后摘要、大小与 stat 字段）→ 三个 `gate_result` → `read_phase_closed` → 才计算并固定 K3。同步修改了 2.4 事件注册表、第 5 节依赖图、11.2、11.3、R6.1/R6.2/R6.6、第 6 节。TOCTOU/ABA 的残余风险说明保留（11.3）。 |
| 验收条件 | R6.6：`post_read_snapshot` 与所有 `gate_result` 的行号 < `read_phase_closed` 的行号 = `pin_K3.json` 的 `line_count − 1`；否则 FAIL `R6_POST_NOT_PINNED`。 |
| 残余风险 | 读后快照仍只证明检查时刻（11.3）；A7 摘要在 LP3 内，但 Driver 证据文件本身的真实性仍依赖冻结 Driver 的自带哈希链。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D03）。 |

### 14.4 FIX-04：摘要算法标签与冻结接口兼容

| 栏 | 内容 |
|---|---|
| 审核输入 | §5、§11.5、Manifest Schema：R3 要求「算法标签:十六进制」，冻结 Reader/Verifier/Driver 使用裸 SHA-256 十六进制键。 |
| 原规则 | 修订 2：所有摘要在日志、清单、验收记录中使用带标签形式。 |
| 修订规则 | 新增 11.8：新证据用带标签结构；冻结 `runtime_manifest.json` 既有键与 `formal` 块的键保持裸格式；新的摘要模块负责解析与类型化校验；Schema 对照表列出转换边界；不得把 `sha256:` 前缀写入冻结键；非法标签、跨算法比较、格式错误、摘要不一致的预期结果见预期结果表；11.5 规则 1 改为指向 11.8。**不修改冻结代码。** |
| 验收条件 | 11.8 预期结果表；A6 生成时的「冻结键校验」；对 `d1_reader.py`、`d1_driver.py`、`d1_verifier.py` 的正则（`HEX64`、`H64`、`HEX40`）经 grep 核对与对照表一致。 |
| 残余风险 | 转换边界靠生成器遵守；生成器尚未编写；「额外键被忽略」仅经源码检查。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D09 新脚本集）。 |

### 14.5 FIX-05：事件名称及事件白名单统一

| 栏 | 内容 |
|---|---|
| 审核输入 | §2.3、§4、§5、§11.1–11.2：正文使用 `manifest_written`、`pin_pushed` 等事件，事件名集合没有完整收录。 |
| 原规则 | 2.3 的一句事件名集合。 |
| 修订规则 | 新增 2.4 唯一事件注册表：事件名、阶段、专有必填字段、重复、前置、后置、所属前缀、异常状态；账本事件另表；规范顺序；2.3 规定未登记事件一律 FAIL；其他章节只能引用注册表中的事件。 |
| 验收条件 | 自检脚本：正文所有事件名都在注册表内；规范顺序里每个事件的「前置」都早于它出现；同名事件含义唯一；LP1/LP2/LP3 终点事件与第 5 节一致。 |
| 残余风险 | 注册表由人工维护；将来新增事件需要修订流程。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D09）。 |

### 14.6 FIX-06：I4 缺席见证的措辞与验收一致性

| 栏 | 内容 |
|---|---|
| 审核输入 | §2、I4、§11.4、验收矩阵：措辞可能被读成零访问证明。 |
| 原规则 | 修订 2 的 I4 / 11.4：已限定范围，但各处措辞不一。 |
| 修订规则 | 统一表述「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象」；§2.1、I4、R6.4、T1、11.4 同步；11.4 的分层表区分已观测事实、记录器承诺的限制、静态检查保证、无法排除的残余风险；PASS 限定为受控检查本身通过。 |
| 验收条件 | 全文检索不出现「证明从未访问」类措辞（作为肯定主张）；验收记录模板含统一表述与残余风险栏。 |
| 残余风险 | 见 11.4 分层表第 ④ 行。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D01）。 |

### 14.7 FIX-07：test 输出白名单与 `usage_declaration` 统一

| 栏 | 内容 |
|---|---|
| 审核输入 | I6、R7.6、§11.6：I6 把输出限制为统计项，11.6 又要求 `usage_declaration`。 |
| 原规则 | I6 只含统计键白名单；11.6 要求声明存在。 |
| 修订规则 | 统一 Schema `d1_heldout_audit_v1`：`envelope`（运行身份、用途声明、规范版本、证据引用）与 `statistics`（严格字段）；`usage_declaration` 属于 Envelope；statistics 内不得有文本、Token ID 序列、逐行结果、模型评估指标；规范文本摘要与核对方式；缺字段、多字段、声明错误、意外嵌套的预期结果；最小正例与七个负例；用途限制始终生效。I6、R7.6 同步。 |
| 验收条件 | 11.6 的预期结果表；本轮只写规范，不运行。 |
| 残余风险 | Schema 只约束输出文件形状；已批准文本摘要待 R3-D08 / D10 批准。 |
| 状态 | PROPOSED / PENDING OWNER DECISION（R3-D08）。 |

### 14.8 FIX-08：依赖图统计及检查方法纠正

| 栏 | 内容 |
|---|---|
| 审核输入 | §5、§11.7、§12.7、检查点：Work 确认 17 个节点、31 条边、无环；修订 2 报告的 29 条边不准确，漏计 `PIN4 → BP`、`A8 → BP`。 |
| 原规则 | 修订 2 的自检脚本只识别带数字的节点名。 |
| 修订规则 | 第 5 节增加正式边列表（`node` / `ref` / `rec` / `sub`）；11.7 规定从该列表构图，用拓扑排序与层级严格递减两种方式核验，并交叉核对人读表格；检查点追加更正，保留修订 2 的原记录；三类边合并后也必须无环；统计必须由脚本重新计数。 |
| 验收条件 | 检查点中的脚本结果：17 个节点，`ref` 边数、`rec` 边数、`sub` 边数、总数，列出全部边；若 `ref` 数不是 31 则报告 FAIL。 |
| 残余风险 | 边列表是人工转换；实现可能引入表外依赖。 |
| 状态 | 已自检；ChatGPT 复核 PENDING。 |

## 16. 修订 4 收口记录（F3B-D1-SPEC-R3-CLOSURE-004）

背景：ChatGPT 独立读取远端修订 3（提交 `ca40fb74d8fea2c17a1a5116ba8939b17ce2e847`），重新构建了第 5 节的依赖图，确认 Git 变更只有 5 个 Markdown 文件、17 个节点、`ref` 31 / `rec` 9 / `sub` 3 共 43 条边、无重复边、无环、层级正确、R3-D01–D11 仍未批准；同时指出四处仍需收口的规范缺口。本轮只做文档收口，保留 17 节点 / 43 边设计，并重新计算了图。第 12、14 节是历史记录，保留原文；其中与本节冲突的规则以本节和 2.4、4、11 的现行文字为准。每项记录：原规范问题及章节、最小修订内容、正常路径预期、异常路径预期、状态、残余风险。

### 16.1 C04-01：R7.7 正常路径的 N/A 语义

| 栏 | 内容 |
|---|---|
| 原规范问题及章节 | §4.2 R7.7 写「无中断 → 不适用」，但 §2.4 的 `check_result` 没有可登记的「不适用」状态，`heldout_audit_done` 的前置写成「R7.1–R7.7 的 `check_result` 已写」，正常路径下 R7.7 没有任何可核对的证据；§11.6 未说明中断时的停止语义。 |
| 最小修订内容 | 2.4 新增状态词枚举：`check_result.status` ∈ {PASS, FAIL, BLOCKED, NOT_APPLICABLE}，`NOT_APPLICABLE` 只允许 R7.7 使用且**不是 PASS**；R7.7 正常运行**写入** `check_result`(R7.7, NOT_APPLICABLE, NO_INTERRUPTION)，并规定三项独立复核的有效条件；`heldout_audit_done` 的前置改为「R7.1–R7.6 各一条 PASS + R7.7 一条 NOT_APPLICABLE + 日志里没有 `interrupted` / `run_aborted`」；§4.2 R7.7 行与汇总句同步，验收报告写「R7.1–R7.6 PASS；R7.7 NOT_APPLICABLE」；给出正常与中断两条最小事件序列。 |
| 正常路径预期 | R7.1–R7.6 各有 PASS；R7.7 为 NOT_APPLICABLE（有效条件成立）；之后才能写 `heldout_audit_done` 与 `pin_pushed`(K2)。 |
| 异常路径预期 | 出现中断：监督器写 `interrupted`、`check_result`(R7.7, BLOCKED, INTERRUPTED)、`run_aborted`；不得再有 `heldout_audit_done`、K2、A5；`NOT_APPLICABLE` 的有效条件不成立 → FAIL `R77_NA_INVALID`；缺 R7.7 的 `check_result` 却有 `heldout_audit_done` → FAIL `EVENT_ORDER_VIOLATION`。 |
| 状态 | 文档自检 PASS；实现 NOT TESTED；PROPOSED / PENDING OWNER DECISION（R3-D05、R3-D08）。 |
| 残余风险 | `NOT_APPLICABLE` 的复核依赖账本与日志的完整性（同一信任域，靠 K0 / K1 / K2 缓解）；R7.7 由审计脚本自己写，被外部信号杀死时由监督器代写 BLOCKED。 |

### 16.2 C04-02：异常终止时的预算关闭与证据归档

| 栏 | 内容 |
|---|---|
| 原规范问题及章节 | §11.1(e)：`close` 的前提要求「回收已确认」「已有 `read_phase_closed`」，失败路径下这些条件永远满足不了，账本无法关闭；§11.2：K3 的终点只有成功事件；`close.result` 与实验最终状态混用，且「`terminate_begin` 之后结果必非 PASS」把预算结果和运行状态搅在一起。 |
| 最小修订内容 | 新增 §11.9：三个相互独立的维度（预算结果 / 运行状态 / 实验最终状态）及映射规则；通用收尾顺序；注册表新增 `run_aborted`（失败路径的终点事件，K3 的 `end_event` 为 `run_aborted`）与 `close` 的新字段（`run_state`、`abort_cause`、`el_end_event`、`el_lines_at_end`）、`wrapup_end.pins_missing`；`close` 前提改为不依赖成功事件，回收未确认也必须关闭（UNPROVABLE）；监督器只写 BLOCKED / FAIL 与事实，不写 PASS / NOT_APPLICABLE；部分证据不改写成 PASS；pin 终点不存在则不产生并记入缺失。给出四条具体流程 F1（S4 中断）、F2（S5 超时）、F3a / F3b（S5 残留进程 / 无法确认退出）、F4（监督器异常退出，事后只读 `--postmortem`）。**不新增对冻结 Driver 的任何修改要求。** |
| 正常路径预期 | `read_phase_closed` 存在；`run_state=COMPLETED`；K3 终点是 `read_phase_closed`；未出现 `run_aborted`。 |
| 异常路径预期 | F1：BLOCKED `interrupted`，WITHIN_BUDGET 可能成立，ABORTED；F2：EXCEEDED，BLOCKED `budget_exceeded`；F3a：BLOCKED `residual_process`；F3b：UNPROVABLE，BLOCKED `termination_unconfirmed`，不补读后快照；F4：无 `close`，BLOCKED `budget_unprovable`，事后 `postmortem.json`。任何失败路径的验收输出都是 `NOT_ACCEPTED`，缺失证据逐项列出。 |
| 状态 | 文档自检 PASS；实现 NOT TESTED；PROPOSED / PENDING OWNER DECISION（R3-D07、R3-D09）。 |
| 残余风险 | 监督器自身故障时只能靠事后只读工具与此前已固定的 pin 取证；`PR_SET_PDEATHSIG`、`/proc` 扫描目标环境 NOT TESTED；失败路径无网络时 pin 推送无法完成（缺失证据增多，不改善任何状态）。 |

### 16.3 C04-03：预算测试 (g) 的状态语义

| 栏 | 内容 |
|---|---|
| 原规范问题及章节 | §11.1 测试 (g)「`seq` 被重排而 `bt_ns` 不变 → 判定结果不变」把「耗时数字不变」写成「整体验收结果不变」，与账本有效性要求（`seq` 连续、哈希链、状态转换）矛盾。 |
| 最小修订内容 | (g) 拆为 (g1)（耗时数值：内存中置换 `seq` 不改变 `close.bt_ns − open.bt_ns`，只断言耗时计算不读 `seq`）与 (g2)（账本有效性：`seq` 不连续、重排、重排后重算 `prev`、哈希链不符、状态转换非法，一律 BLOCKED `budget_unprovable`，代码 `LEDGER_SEQ_INVALID` / `LEDGER_CHAIN_BROKEN` / `LEDGER_BAD_TRANSITION`）；11.1(a) 明写「`seq` 不参与耗时数值，但参与账本有效性判定」。同时新增 (h2)–(h4) 说明预算结果不等于实验成功。 |
| 正常路径预期 | (g1) 置换前后耗时相同；账本 `seq` 连续、链完整、转换合法时有效。 |
| 异常路径预期 | (g2) 任一违例，即使耗时数字不变，整体验收也不是 PASS。 |
| 状态 | 文档自检 PASS；测试 NOT TESTED（本轮不运行）。 |
| 残余风险 | 测试只规定预期；账本校验器尚未编写。 |

### 16.4 C04-04：R6.6 进入独立验收

| 栏 | 内容 |
|---|---|
| 原规范问题及章节 | §4.1 R6.6 只有一行概述，§6 的验收清单写「R6.1–R6.5」，未把 R6.6 列为独立验收的必检项；§11.2 没有要求验收脚本自己重新做 K3 的远端内容验证。 |
| 最小修订内容 | §4.1 R6.6 展开为 (a)–(d) 四项由验收脚本**自己**核对：`post_read_snapshot` 在 K3 终点之前；R6.1–R6.3 的 `gate_result` 都在 K3 终点之前且与重新推出的结论一致；`read_phase_closed` 的行号与 `pin_K3.json` 的 `line_count` / `end_event` 一致；K3 经实际远端内容验证 RV（验收脚本重新执行）。§6 改为 R6.1–R6.6；任何必需闸门缺证据，输出一律 `NOT_ACCEPTED`，不得出现 `ALL_GATES_PASS_CANDIDATE`；11.2、11.3 同步。 |
| 正常路径预期 | (a)–(d) 全部成立 → R6.6 PASS。 |
| 异常路径预期 | 读后证据在 K3 之后 → FAIL `R6_POST_NOT_PINNED`；`line_count` / `end_event` 不符 → FAIL `R6_K3_LINECOUNT_MISMATCH`；缺证据 → BLOCKED `R6_EVIDENCE_MISSING`；RV 无法进行 → BLOCKED `PIN_UNVERIFIABLE`；失败路径 → NOT TESTED 且整体 `NOT_ACCEPTED`。 |
| 状态 | 文档自检 PASS；验收脚本 NOT TESTED（未编写）。 |
| 残余风险 | 读后快照仍只证明检查时刻（11.3）；RV 仍受远端信任局限（11.2）。 |

## 18. 修订 5 最终一致性修复记录（F3B-D1-SPEC-R3-FINAL-005）

背景：ChatGPT 第四轮独立验收确认 C04-01、C04-03、C04-04 文档修订通过；C04-02 的主体设计通过，但有三处局部异常路径缺口；依赖图 17 节点、`ref` 31 / `rec` 9 / `sub` 3、共 43 条边、无环；Git 修改范围符合限定。本轮保留已通过的设计，不重写 R3 框架，只修这三处。每项记录：位置、问题、最小修订、正常路径预期、异常路径预期、状态、残余风险。第 16 节等历史记录保留原文；冲突处以本节和 2.4、6、11 的现行文字为准。

### 18.1 FINAL-01：F1 状态机分支

| 栏 | 内容 |
|---|---|
| 位置 | §2.4(b)、§11.1(b)(d)、§11.9 F1 |
| 问题 | 修订 4 的 F1 序列无条件写 `terminate_signal`、`reap_done`；而「只有 S4 阶段进程被外部信号杀死」时账本并未进入 `TERMINATING`，凭空写这些行是非法转换。11.1(d) 末尾还写「残留 → `stage_end{blocked}`」，与 F3a「残留 → 进入 `TERMINATING`」互相矛盾。 |
| 最小修订 | F1 拆为 F1a（监督器收到终止信号：`terminate_begin` → `terminate_signal` → `reap_done` → `stage_end`）、F1b（仅阶段进程被外部信号杀死且无存活后代：先收集退出状态、做残留检查，直接 `stage_end{failed}`，**不写** `terminate_signal` / `reap_done`）、F1c（外部杀死但发现需主动终止的后代：此时才 `terminate_begin{supervisor_abort}`）；注册表与状态机明确 `terminate_signal`、`reap_done` 只在 `TERMINATING` 合法、`failed` 可直接转换；11.1(d) 的矛盾句改为与 F3a 一致。 |
| 正常路径预期 | 无中断，不适用。 |
| 异常路径预期 | F1a、F1b、F1c 各有完整合法序列；F1b 出现 `terminate_signal` / `reap_done` → BLOCKED `LEDGER_BAD_TRANSITION`；F1b 发现存活后代却不进入 `TERMINATING` → BLOCKED `residual_process`；`interrupted` 与 `stage_end.status`=ok 并存 → FAIL。 |
| 状态 | 文档自检 PASS；实现 NOT TESTED；PROPOSED / PENDING OWNER DECISION（R3-D05、R3-D07）。 |
| 残余风险 | 「阶段被外部信号杀死」与「监督器自己收到信号」在 Python 层靠 `waitpid` 状态区分，目标环境行为 NOT TESTED；T6 的残留扫描是尽力而为。 |

### 18.2 FINAL-02：F4 事后验收工件

| 栏 | 内容 |
|---|---|
| 位置 | §2.4(「后验模式例外」)、§6 第 5 条、§11.9 F4 |
| 问题 | 修订 4 写「`postmortem.json` 被 A8 记录摘要」，但 F4 里没有 S6 的正常 A8 写入点，也没有说明后验 A8 是否可以在原日志里写 `manifest_written`(A8)；注册表却规定每个工件恰有一行。 |
| 最小修订 | 明确 `--postmortem` 不续写、不修复、不向原账本和原事件日志追加任何行；`postmortem.json` 是独立叶子证据；后验 A8 是独立文件，只引用现存工件与 `postmortem.json`，缺失节点标 `absent`，**不伪造** `manifest_written`(A8)；该例外同时写入注册表（`manifest_written` 行与「后验模式例外」段）和验收规范（§6 第 5 条）；缺 `close`、`run_aborted`、K3 / K4 时始终 `NOT_ACCEPTED`、最终状态不低于 `BLOCKED(budget_unprovable)`，late pin 不得升级状态。 |
| 正常路径预期 | `close` 存在时不是 F4，按常规 S6 处理。 |
| 异常路径预期 | 后验模式改动原日志 / 账本、在原日志里写入 `manifest_written`(A8)、后验 A8 引用不存在的节点、输出状态高于 `BLOCKED(budget_unprovable)` → FAIL。 |
| 状态 | 文档自检 PASS；`--postmortem` NOT TESTED（未编写）；PROPOSED / PENDING OWNER DECISION（R3-D09）。 |
| 残余风险 | 后验结论仍由同一信任域的脚本产生；late pin 只是叶子证据；`postmortem.json` 本身可被改写，只能靠随后的证据提交与带外副本约束。 |

### 18.3 FINAL-03：选项 X / Y 的失败路径兼容性

| 栏 | 内容 |
|---|---|
| 位置 | §11.1(b)(f)(g)、§11.9(c)(f)、§2.4(b) |
| 问题 | F1–F3 的序列是「先 `close`、后 pin、最后 `wrapup_end`」（选项 X）；选项 Y 要求 pin 在 `close` 之前，但失败路径下状态机里「非 ok 的 `stage_end` 之后只允许 `close`」，选项 Y 无法合法地写 `pin_phase`。 |
| 最小修订 | 明确 F1–F3 的序列采用选项 X；为选项 Y 给出完整的失败路径变换（`stage_end` → `pin_phase` → K3 → K4' → `close`）、示例尾部与成功路径尾部；状态机允许选项 Y 在非 ok 的 `stage_end` 之后写 `pin_phase`，`ANOMALY` 之后不写；`close` 在选项 Y 下承载 `pins_verified` / `pins_missing`；`pin_phase`→`close` 同样受上限 `W` 约束；选项 Y 下复用「先 `close` 后 pin」→ FAIL `OPTION_Y_ORDER_VIOLATION`；仍未覆盖的情形记 `OPTION_Y_FAILURE_PATH_NOT_SPECIFIED`（BLOCKED），负责人选 Y 之前须补充规范。 |
| 正常路径预期 | 选项 X：成功与失败路径都是先 `close`、后 pin。选项 Y：成功与失败路径都是先 `pin_phase`、pin、后 `close`。 |
| 异常路径预期 | 选项 Y 先 `close` 再 pin → FAIL；选项 X 出现 `pin_phase` → FAIL；`ANOMALY` 后出现 `pin_phase` → BLOCKED。 |
| 状态 | 文档自检 PASS；实现 NOT TESTED；PROPOSED / PENDING OWNER DECISION（R3-D07，X / Y 二选一）。 |
| 残余风险 | 选项 Y 下 `close`（预算终点）不在被固定的前缀内；`pin_phase` 与 `close` 之间的改写不会被 K4' 发现；`W` 是新增参数，待裁决。 |

## 19. 下一条唯一研发指令

等待 ChatGPT 对最终一致性修复（FINAL-005）后的 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3；项目负责人对第 7 节的决策记录（R3-D01…R3-D11）作出正式批准。批准前：不下载、不拟合、不运行 D1、不使用 GPU、不修改冻结文件、不开始 D2/D3。

---

**最终状态：`R3 DRAFT / PENDING OWNER DECISION`。** 未标记 FROZEN，未标记 PASS；11 项裁决均为待批准的决策记录。
