# F3-B / D1 — 真实执行前规范 R3（已批准候选版）

**状态：`OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`**。负责人已于 2026-10-26（Asia/Tokyo）批准 R3-D01…D11（见 `F3B_D1_R3_OWNER_DECISION_20261026.md`）。**不是 R3 FROZEN，不是 REAL D1 PASS，不是任何运行授权。**在 ChatGPT 独立核对本候选规范与批准记录之前，不标记正式冻结。

- **来源：** 由 R3 草案 FINAL-005 版（`F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`，基准提交 `4c1d29d9e01c6df2d3b5e796181f728cc3cb88ed`，SHA-256 `d52856713e1dd0d53855597bedc8f3f7eec9dfeec8aece24cdafef839054bbef`；ChatGPT 独立审核 `R3 DOCUMENT REVIEW PASS / READY FOR OWNER DECISION`）生成。**原草案、此前各轮的失败与修订记录（草案第 12、14、16、18 节与各轮检查点）原样保留在仓库里，不被本文件取代或删除。**
- **生效决策：** 绑定 `research/mini_mythos/docs/F3B_D1_R3_OWNER_DECISION_20261026.md`（按路径引用；该记录与本文件各自的 SHA-256 登记在独立检查点里（见下面的「登记与完整性」），本文件不含任何自引用或对方的摘要，避免循环）。
- **最终勘误（F3B-D1-R3-FINAL-ERRATA-001，2026-10-26）：** 修正 §11.1(d) 中把 `terminate_begin` 一律等同于 `BLOCKED(budget_exceeded)` 的旧断言（终止原因与预算结果现在严格分开，见 11.1(d) 对照表），并补全 `reap_done` 的终止时间字段 Schema（`t_kill_bt_ns`、`kill_overhead_ns`）。勘误不改变任何已批准的决策或参数。**边界勘误（F3B-D1-R3-ERRATA-EDGE-002）：** 统一终止宽限期与 SIGKILL 升级规则（EDGE-01）、把回收耗时与升级条件分开（EDGE-02）、规定预算 `UNPROVABLE` 不覆盖已证实的 `FAIL`（EDGE-03）；仍不新增事件。本文件当前有效的 SHA-256 登记在 `F3B_D1_R3_ERRATA_EDGE_CHECKPOINT_20261026.md`；此前各版的摘要分别登记在 `F3B_D1_R3_FINAL_ERRATA_CHECKPOINT_20261026.md`（ERRATA-001 版）与 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`（批准时的版本），均被后一版取代。
- **执行条款只使用已批准的选项。** 尤其是 D07：**唯一执行方案是 X**。草案里的选项 B、选项 Y、选项 Z 以及相关的 `pin_phase`、`close.pins_*` 等内容**不属于本规范的执行条款**，只保留在原草案里作为历史。
- 输入文档：v1（`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，SHA-256 `a55b2cb7…ba9e`）、R1（`…_R1.md`，`f92c4e79…1d7a`）、R2（`…_R2.md`，`1d4c3629…05d9`）与 `F3B_D1_FINAL_REGRESSION_CLOSEOUT_20261026.md`；冻结配置与 `D1_ENV_FREEZE.md`。基准提交 `97d0faf2982f4122941d2299a23cab6ab2ba04a3`（D1 冻结、哨兵修正与回归 Closeout 所在提交）。

## 0. 本文件是什么、不是什么

1. 这是**已批准的候选规范**：负责人批准了 R3-D01…D11（第 7 节），本文件把这些决策写成可核对的条款，并附实施所需的细则。其余细则（事件注册表、远端验证 RV、摘要格式边界、失败路径收尾等）是为实施这些决策所必需的具体化，**随本候选一并提交 ChatGPT 独立核对**；核对通过之前，它们不是正式冻结规范。
2. 在本规范被正式冻结之前，v1 → R1 → R2 的冻结规则**原样适用**，并且**不得**被本文件暗中重新解释。本文件区分两类文字，并逐条标注：
   - **CLARIFICATION**：原文含义有歧义或缺失，本文件给出一种可验证的具体化；不改变原文已明确的要求。
   - **AMENDMENT**：要求改变原文字面要求（必须引用被取代的原文）。冲突 S1、S2 属于这一类，因为两条冻结条文不能同时按字面满足。
3. 本文件**不修改冻结的 Driver**。凡需要新增机制的地方，一律以**新的独立脚本**承担；这些脚本**全部尚未编写**，每一个都需要单独的开发授权、独立的 CPU 验收，并在全部完成后整体重新冻结（R3-D09）。**它们都保持 `NOT TESTED`。**
4. 本规范获批**不等于**真实 D1 的执行授权：不授权下载真实数据、拟合正式 Tokenizer、运行 D1、训练、GPU、D2/D3，也不授权第一个合成 CPU 实验（它也必须单独取得执行授权）。
5. 第 7 节的 11 项决策已于 2026-10-26 获负责人批准（状态 `OWNER APPROVED — 2026-10-26`）。Grok 交叉复审仍是 DEFERRED / PENDING，**不是 PASS**。

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

## 2. 分阶段数据处理规范 `【APPROVED CANDIDATE】`

### 2.1 操作词汇表（严格区分，CLARIFICATION）

| 级别 | 名称 | 含义 | 是否暴露文件内容给本进程 |
|---|---|---|---|
| L0 | **元数据查询** | 只调用 Hub 的元数据接口（解析修订、列目录、读取每个文件的大小/LFS/blob 信息）。不产生任何数据文件 | 否 |
| L1 | **下载** | Hub 客户端把文件字节写到本地磁盘。不解释、不读取 | 否（字节落盘，但不被本流程读取） |
| L2 | **计算哈希** | 以二进制只读方式读取字节并计算 SHA-256；不解析格式 | 字节被读取，但不被解释 |
| L3 | **打开解析** | 用 `pyarrow` 打开：读取 schema、行数、row group 元数据 | 是（结构） |
| L4 | **读取文本** | 物化 `text` 列的值（编码、扫描、统计、拟合、评估都属此级） | 是（内容） |

**R6/T1 中的「未被打开」（CLARIFICATION，对应 S1、S6）：** 对 validation/test，在事件 `tokenizer_hash_logged`（定义见 2.3、2.4）之前，**不允许任何 L1 及以上的操作**；允许 L0。理由：这样「未打开」可以按 11.4 的受控检查来核对——**在受控范围内、指定检查时刻，未发现 validation/test 访问迹象**——而不是依赖易被改写的时间戳。该检查**不是**「从未访问」的证明（11.4 逐层写明了它能与不能证明什么）。
R3-D01 已批准：采用严格版本（L1 以上禁止）。草案中曾列出的「选项 B」（允许 L1、L2）**未被选定，不属于执行条款**。

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

S4 与 S5 的先后顺序不影响任何闸门（Driver 只需要 train 与 Tokenizer）。本规范采用 S4 先于 S5，使清单引用关系保持单向（见第 5 节）。

### 2.3 事件日志（对应 S6）`【APPROVED CANDIDATE】`

- 文件 `evidence/event_log.jsonl`，JSON Lines，**只追加**。每行是规范 JSON（键排序、紧凑分隔符、ASCII 转义）加 `\n`。**通用字段**：`seq`（从 0 连续递增，**只表示顺序，不是时间**）、`utc`（墙钟，**仅供信息，不用于计量，也不用于判定**）、`event`、`stage`（`S0`–`S6` 或 `W`，`W` 表示预算关闭后的收尾）、`stage_id`（监督器分配，对应预算账本的 `stage_start`；`W` 与 `S6` 为 `null`）、`split`（或 `null`）、`level`（L0–L4 或 `null`）、`path`（相对路径或 `null`）、`digest`（如有；带算法标签，见 11.8）、`prev`（上一行原始字节（含换行）的摘要，带标签 `sha256:<64 位十六进制>`；首行为 `sha256:` 加 64 个 `0`）。各事件的**专有必填字段**见 2.4。
- **事件名只能来自 2.4 的注册表。** 未登记的 `event`、缺必填字段、违反「前置」「重复」约束的行，一律 FAIL（`EVENT_UNREGISTERED` / `EVENT_FIELD_MISSING` / `EVENT_ORDER_VIOLATION`）。
- **`tokenizer_hash_logged`**：写入 `tokenizer.json` 的 SHA-256；它是 T1/R6 的分界点 `t_fix`。其前一行必须是 `absence_witness`（见 3.4）。
- **哈希链只提供完整性检测，不证明日志真实**（修订 2，见 11.2）：它能发现「没有同步重算整条链」的修改，但任何能重写文件的人都可以重算整条链。因此日志的可信度来自关键前缀的**外部固定**（11.2），判定依据是 `seq` 的顺序、链的完整性和外部固定的前缀哈希；时间戳与 `seq` 都**不用于耗时计量**——耗时只来自预算账本（11.1）。
- 记录器是一个极小的单写入者模块，由获取与拟合脚本共同使用；它自身需要独立的单元测试。该模块尚未编写。
- **前缀哈希（对应 11.2、第 5 节）：** `P_k = SHA-256(第 0 行至第 k 行的原始字节)`。它只依赖 ≤ k 的行，因此引用它不会产生循环。预算账本 `budget_ledger.jsonl` 用同样的行格式与前缀哈希定义。

### 2.4 事件注册表（唯一权威；修订 3）`【APPROVED CANDIDATE】`

本节是事件名、阶段、必填字段、顺序约束与异常状态的**唯一**定义。其他章节（S0–S6、K0–K4、R6/R7/T1–T7、11.1–11.2）只能引用这里登记的事件，不得另造事件名，也不得给同一事件名另一含义。「进入前缀」指该行落在哪一个被外部固定的前缀内（LP1 = 第 0…k1 行，LP2 = 第 0…k2 行，LP3 = 第 0…k3 行，成功路径的 `k3` 是 `read_phase_closed`，失败路径的 `k3` 是 `run_aborted`（11.9）；`—` 表示不在任何被固定的前缀内，只由 A8 与最终证据提交覆盖）。

**(a) 事件日志 `event_log.jsonl`**

| 事件 | 阶段 | 专有必填字段 | 重复 | 前置（必须已出现） | 紧随 / 后置约束 | 进入前缀 | 异常状态 |
|---|---|---|---|---|---|---|---|
| `run_start` | S0 | `run_id`、`spec_ref`、`config_digest` | 否（只能是第 0 行） | — | 之后是 `pin_pushed`(K0) | LP1 | 缺失或不在第 0 行 → FAIL `EVENT_LOG_BROKEN` |
| `pin_pushed` | S0（K0）、S3（K1）、S4（K2）、W（K3、K4） | `pin`、`pin_digest`、`commit`、`branch`、`remote` | 每个 `pin` 一次 | K0：`run_start`，且账本 `open` 已写；K1：上一行是 `tokenizer_hash_logged`；K2：上一行是 `heldout_audit_done`；K3：上一行是 `read_phase_closed`（成功路径）**或** `run_aborted`（失败路径，11.9）；K4：账本 `close` 已写。**某个 `pin` 的终点事件不存在，就不产生该 `pin`**（例如 S4 中断时没有 K2），缺失记入 `wrapup_end.pins_missing` | 之后是 `pin_remote_verified` | K0→LP1；K1→LP2；K2→LP3；K3、K4→`—` | 推送失败 → BLOCKED `PIN_PUSH_FAILED`（在失败路径上只记入缺失证据，不改变已有的 BLOCKED / FAIL 结论） |
| `pin_remote_verified` | 同 `pin_pushed`；另在 S4、S5 的门禁前复验 | `pin`、`result`（PASS/FAIL/BLOCKED）、`remote_tip`、`commit`、`reason` | 是（同一 `pin` 的**最后一次**决定结果） | 对应的 `pin_pushed` | K0 的 PASS 是 `preflight_done` 的前置；K1 的 PASS 是 `gate_check`(G_S4) 的前置；K2 的 PASS 是 `manifest_written`(A5) 的前置 | 同该 `pin` 的 `pin_pushed` | FAIL / BLOCKED 见 11.2 的 RV 规则 |
| `preflight_done` | S0 | `checks`（配置、冻结清单 10/10、仓库 clean、`mode=real`、新运行目录、空缓存目录、账本 `open` 已写）、`result` | 否 | `pin_remote_verified`(K0)=PASS | 之后才能有任何 S1 事件 | LP1 | 任一检查不过 → BLOCKED `PREFLIGHT_FAILED` |
| `meta_query` | S1（S4 可对 validation/test 再做 L0） | `op`、`status` | 是 | `preflight_done` | S1 结束前须有 `manifest_written`(A1) | 按位置 | Hub 不可达 → BLOCKED；修订不符按 v1 §3.2 原规则（本规范不改） |
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
| `driver_exit` | S5 | `exit_code` 或 `signal`、`terminated_by`（`none` / `budget` / `interrupt`）；由监督器写入 | 否 | `driver_start` | 之后是 `children_reaped` | LP3 | `terminated_by`=budget → BLOCKED `budget_exceeded`（失败路径，11.9 F2）；`terminated_by`=interrupt → BLOCKED `interrupted`；Driver 自己以非零码退出（含其内部超时）属**正常路径**，如实记录 |
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
| `stage_end` | `stage_id`、`status`（ok / failed / blocked / killed）、`exit` | `STAGE`→`OPEN`（`killed` 必须经 `terminate_begin` → `terminate_signal` → `reap_done`；`failed` 含**被外部信号杀死且无需主动终止任何后代**的阶段，此时直接 `STAGE`→`stage_end`，**不得**出现 `terminate_signal` / `reap_done`） | 每个 `stage_id` 一次 | BP | 与 `stage_start` 不匹配 → BLOCKED。`status` 不是 `ok` 之后，**唯一合法的下一行是 `close`**。事件日志已有 `interrupted` / `run_aborted` 而 `status`=ok → FAIL `STAGE_STATUS_MISMATCH` |
| `terminate_begin` | `stage_id`、`reason`（deadline / supervisor_abort / interrupt） | `STAGE`→`TERMINATING` | 每个阶段至多一次 | BP | `reason`=deadline → `close.result` 必为 EXCEEDED；`interrupt` / `supervisor_abort` → `close.run_state` 必为 ABORTED。任何一种之后，该阶段都不得被计为成功 |
| `terminate_signal` | `sig`（TERM / KILL）、`pgid`、`result`（`sent` / `gone` / `error`）、`errno`（整数或 `null`；非 `null` 当且仅当 `result`=`error`，记真实错误号） | `TERMINATING`→`TERMINATING` | 每个阶段至多两次（TERM 一次、KILL 至多一次） | BP | **只在已写 `terminate_begin` 之后合法**；在 `STAGE` 状态（没有 `terminate_begin`）出现 → BLOCKED `LEDGER_BAD_TRANSITION`；该行的 `bt_ns` 是发送**尝试**的时刻，成功与否都记 |
| `reap_done` | `confirmed`、`exit`、`residual`、`t_term_bt_ns`、`t_kill_bt_ns`（整数，或 JSON `null` 表示没有升级到 SIGKILL）、`t_gone_bt_ns`（整数，或 `null` 表示没有观察到所有目标已退出）、`t_reaped_bt_ns`、`kill_overhead_ns`（整数 ≥ 0），Schema 与核对见 11.1(d) | `TERMINATING`→`REAPED` | 每个被终止的阶段一次 | BP | **只在 `TERMINATING` 状态合法**（即已写 `terminate_begin`），否则 BLOCKED `LEDGER_BAD_TRANSITION`；记录无效（缺字段、类型 / 取值非法、时间逆序）→ BLOCKED `budget_unprovable`（`REAP_RECORD_INVALID`）；记录内部矛盾 → FAIL `REAP_RECORD_FORGED`；记录真实自洽但协议未遵守或无法确认 → BLOCKED（`TERMINATION_NOT_ESCALATED` / `TERMINATION_PROTOCOL_VIOLATION` / `TERMINATION_UNCONFIRMED` / `KILL_ATTEMPT_FAILED`），不是 FORGED，绝不 PASS（11.1(d)） |
| `anomaly` | `code`、`detail` | 任意状态→`ANOMALY` | 是 | BP | 之后只允许 `close`（`result`=UNPROVABLE） |
| `close` | `result`（WITHIN_BUDGET / EXCEEDED / UNPROVABLE，**只描述时间与账本有效性**）、`total_ns`、`run_state`（COMPLETED / ABORTED）、`abort_cause`（与 `run_aborted.cause` 同枚举，或 `null`）、`el_end_event`（`read_phase_closed` / `run_aborted` / `unwritable` / `none`）、`el_lines_at_end`（整数或 `null`，不是哈希） | `OPEN` 或 `ANOMALY`→`CLOSED` | 否；必须是 K4 前缀的最后一行 | BP | 缺失、不是终行 → BLOCKED `budget_unprovable`；前提与取值规则见 11.1(e)、11.9 |
| `wrapup_end` | `pins_verified`（列表）、`pins_missing`（列表，含缺失原因）、`wrapup_ns` | `CLOSED`→`DONE` | 否；**`close` 之后唯一允许的行** | `—` | 缺失或超过上限 W → BLOCKED `wrapup_unprovable` |

**(c) 规范顺序（供自检与验收脚本核对「顺序可满足」；`E` = 事件日志，`B` = 预算账本）**

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
- 失败路径的最小序列见 11.9。
- 本表只登记**哪些事件存在、以什么顺序出现**，不改变 v1/R1/R2 的任何规则。

## 3. validation/test 完整性与 Tokenizer 拟合隔离 `【APPROVED CANDIDATE】`

| 编号 | 要求 |
|---|---|
| I1 | `tokenizer_hash_logged` 之前，validation/test 没有任何 L1+ 事件（事件日志证明）；允许 L0 |
| I2 | 拟合语料**只能**由 train 合格行构成（v1 §4.1「拟合输入」）。记录喂入行数与语料 SHA-256（语料 = 按行号顺序的 NFC 文本的 UTF-8 字节，各行以固定的 `\x00` 分隔后哈希；分隔符属本规范的具体化） |
| I3 | 拟合模块不接受 validation/test 路径作为参数，运行时断言文件名属于 train；独立静态检查：拟合模块源码不出现 validation/test 的路径常量 |
| I4 | **缺席见证（对应 S1/S6；完整规则、分层与局限见 11.4）：** 写 `tokenizer_hash_logged` 之前，对**明确列出的受控目录集合**做只读扫描（路径、大小、类型，**不读取内容、不计算内容哈希**），要求其中没有 validation/test 文件的任何迹象。结论只能表述为**「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象」**；它**不是**「从未访问」的证明，也不证明所有缓存都不含相关内容，更不证明不存在未记录的网络或流式读取 |
| I5 | S4 只能在 K1 经远端内容验证（`pin_remote_verified`=PASS）且 `gate_check`(G_S4)=PASS 之后开始（11.2）。S4 对 validation/test 的文件摘要必须与 S1 记录的**同算法**摘要相等（完整性基础见 11.5；不符 FAIL；基础不明或元数据不足 → BLOCKED） |
| I6 | held-out 审计脚本的输出遵循 11.6 的统一 Schema `d1_heldout_audit_v1`：`envelope`（运行身份、用途声明、规范版本、证据引用；`usage_declaration` 属于这里）与 `statistics`。`statistics` 只允许：文件摘要、文件大小、行数、合格行数、一级标题行数、Token 计数（两种口径，见 4.2）、最大 Token ID、是否出现 ID 0、round-trip 不一致行数、特殊字符串出现次数。**`statistics` 内不得**出现行文本、Token ID 序列、逐行统计、模型评估指标、数组或用途声明。由 Schema 键集合检查加静态检查保证 |
| I7 | 「不用于拟合、不用于任何模型评估」是组织约束；机器可核对的替代物是 I3 与 I6 加上「held-out 数据文件的路径不出现在任何训练、评估代码中」的静态检查。**这三项只能证明代码层面没有这样做，不能证明没有人手工使用**；该局限在验收记录中明示 |
| I8（R3-D08 已批准） | v1 §5.5 R7 写明「D3 的最终 test 评估仍是后续一次性事项」。R3-D08 已批准在 D1 阶段对 test 做计数与 round-trip 审计；该审计**不是评估**，用途被 11.6 严格限定 |

## 4. 验收矩阵（正常与异常输入）`【APPROVED CANDIDATE】`

状态词沿用 v1 §6：完整性不符 → FAIL；输入缺失、不可达、前置条件不满足 → BLOCKED。「承担者」中的「新」指尚未编写的独立脚本；「冻」指已冻结的代码。

### 4.1 R6

| 编号 | 检查 | 正常输入 → 期望 | 异常输入 → 期望 | 证据 | 承担者 |
|---|---|---|---|---|---|
| R6.1 | **读前**：Driver 启动前计算 train 文件 SHA-256，须等于 S2 的 `hash_done` 摘要、LFS `sha256`（同为 SHA-256，11.5）与 `runtime_manifest.parquet_sha256`（裸格式，经 11.8 转换后比较） | 三者一致 → PASS | 文件被换/截断/内容改一字节 → FAIL `R6_PRE_HASH_MISMATCH`；文件不存在 → BLOCKED | `pre_read_snapshot` 事件 | 新（冻结 Driver 不做） |
| R6.2 | **读后（修订 3）**：Driver 退出、`children_reaped`(`confirmed`=true) 之后，再算一次 train 文件 SHA-256，并核对读前后的摘要、大小与 `stat` 字段（含 `ctime_ns`）；`post_read_snapshot` 与相应闸门结论（`gate_result`）**先于** `read_phase_closed` 写入，K3 在其后才计算并固定 | 一致 → PASS | 运行期间被改 → FAIL `R6_POST_HASH_MISMATCH` / `R6_STAT_CHANGED`；回收未确认 → BLOCKED `TERMINATION_UNCONFIRMED` | `post_read_snapshot`、`gate_result` 事件 | 新；冻结验证器的 `fsha(src_path)==manifest` 是其中一个冗余检查 |
| R6.3 | **粒度与限定语（CLARIFICATION，对应 S3；修订 2，见 11.3）：** 读前/读后各针对「整个冻结 Driver 运行」一次，加 `stat`（大小、`mtime_ns`、`ctime_ns`、inode）快照（`ctime_ns` 由内核维护，普通用户不能回写，所以「改后又改回」通常也会让它变化）。**该检查只能证明两个检查时刻的文件状态相同，不能证明运行期间每一次读取（A、B 的 6 段、12 个负例、验证器的多次读取）读到的内容一致**；验收记录必须写出这句限定语。可选更强控制见 11.3 | 两个时刻的哈希与 `stat` 均相同 → PASS（仅限该限定语所述含义） | 任一不同 → FAIL `R6_POST_HASH_MISMATCH` 或 `R6_STAT_CHANGED`（良性的 `chmod`/硬链接也会改 `ctime`，保守判 FAIL，重新运行）。**已记录的预期漏检用例：** 保持 `ctime` 不变的 ABA（需要 root、回拨系统时钟或直接写块设备），以及目标文件系统不维护 `ctime` 的情形（**目标文件系统 NOT TESTED**）；它们不作为通过依据，只作为残余风险。选用 11.3 的监视控制可缩小但不消除该风险 | 同上 | 新 |
| R6.4 | **隔离**：I1、I4（受控范围内的缺席见证，11.4）、K1 的远端内容验证（11.2） | 无 validation/test 的 L1+ 事件在 `t_fix` 之前；**受控范围内、指定检查时刻未发现访问迹象**；K1 的 RV=PASS → PASS（仅指受控检查通过，不是零访问证明） | 之前出现任何 validation/test 的 L1+ 事件，或见证命中 → FAIL `R6_HELDOUT_TOUCHED_EARLY`；日志哈希链断、或前缀哈希与固定记录不符 → FAIL `EVENT_LOG_BROKEN`；固定记录不存在、无法核对远端 → BLOCKED | 事件日志、固定记录、`pin_remote_verified` | 新 |
| R6.5 | **身份绑定**：S1 的路径/oid ↔ S2 下载的文件 ↔ 清单 | 全部一致 → PASS | 路径不属于 `wikitext-2-raw-v1/`、split 与文件名不符、非「每个 split 恰好一个 Parquet」→ BLOCKED（v1 §3.1 原规则）；哈希与 oid 不符 → FAIL | `hub_metadata.json`、`train_data_manifest.json` | 新 |
| R6.6 | **最终读后证据进入 K3，并由独立验收逐项核对（修订 3 引入，修订 4 明确为独立验收范围 R6.1–R6.6）**。验收脚本**自己**从事件日志文件与固定记录重新核对，不信任 `gate_result`、`pin_remote_verified` 里已有的结论：(a) `post_read_snapshot` 恰有一行，且行号小于 K3 终点（`read_phase_closed`）的行号；(b) R6.1、R6.2、R6.3 三个 `gate_result` 各恰有一行，行号都小于 K3 终点，且各自的状态与从 `pre_read_snapshot` / `post_read_snapshot` 的数据重新推出的结论一致；(c) `read_phase_closed` 的行号 = `k3`，`pin_K3.json` 的 `end_event` = `read_phase_closed`、`line_count` = `k3 + 1`；(d) K3 的远端内容验证 RV（11.2 步骤 1–10）由验收脚本**重新执行**并为 PASS | (a)–(d) 全部成立 → PASS | 读后快照或任一 `gate_result` 的行号在 K3 终点之后 → FAIL `R6_POST_NOT_PINNED`；`line_count` 或 `end_event` 不符 → FAIL `R6_K3_LINECOUNT_MISMATCH`；`gate_result` 与重新推出的结论不一致 → FAIL；缺 `post_read_snapshot`、缺任一 `gate_result`、缺 `read_phase_closed`、`pin_K3.json` 缺失 → BLOCKED `R6_EVIDENCE_MISSING`；RV 无法进行 → BLOCKED `PIN_UNVERIFIABLE`；失败路径（K3 终点是 `run_aborted`，11.9）→ R6.6 记 **NOT TESTED**，整体 `NOT_ACCEPTED`。**任一项缺失，验收输出都不得出现 `ALL_GATES_PASS_CANDIDATE`** | 事件日志、`pin_K3.json`、RV | 新 |

### 4.2 R7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| R7.1 | 文件摘要与 A1 中**同算法**的摘要相等（完整性基础见 11.5） | 相等 → PASS | 不符 → FAIL；基础不明/元数据不足、文件缺失/下载失败/不可达 → BLOCKED | 新 |
| R7.2 | 行数：Parquet 元数据 `num_rows` 与实际物化行数相等 | 相等 → PASS | 不等 → FAIL；`text` 列缺失或某行非字符串 → BLOCKED（沿用冻结读取器对 `NON_STRING_TEXT` 的处理） | 新 |
| R7.3 | 合格行数（`text.strip()!=""`）、一级标题行数 | 两个**互相独立**的实现给出相同结果 → PASS（沿用 R2 的双实现原则） | 两个实现不一致 → FAIL | 新（两份） |
| R7.4 | **Token 计数口径（CLARIFICATION，对应 S4）：** 同时记录 `tokens_total = Σ len(tokens(r))`（含 EOS 前缀，且「第一个合格行」按每个 split 单独判定）与 `tokens_encode_only = Σ len(encode(NFC(text)))`，二者差必须等于该 split 的 EOS 前缀个数 | 恒等式成立 → PASS | 不成立 → FAIL | 新 |
| R7.5 | round-trip（即 T4 在 val/test 上）：`decode(encode(NFC(x))) == NFC(x)`，不一致行数为 0 | 0 → PASS | >0 → FAIL（记录个数，不记录内容）；decode 抛异常 → FAIL | 新 |
| R7.6 | 输出符合 11.6 的统一 Schema（`envelope` + `statistics`，键集合精确）、静态检查（I3、I7）与 test 用途限制 | Schema 检查全部通过；`envelope.usage_declaration` 存在且与已批准文本一致；静态检查通过 → PASS | Schema 违反 → FAIL（代码见 11.6）；已批准文本摘要尚未提供 → BLOCKED `USAGE_DECLARATION_UNAPPROVED`；审计模块引用模型/训练代码 → FAIL | 新 |
| R7.7 | **中断行为门禁（对应 S5；R3-D05）：** 它不是「必须产生 PASS」的检查，而是**只在中断时触发**的门禁。无中断时记一条 `check_result`(R7.7, `NOT_APPLICABLE`, `NO_INTERRUPTION`)——这是明确的「不适用」，**不是 PASS**，且必须满足 2.4 列出的有效条件；中断时 → `BLOCKED(interrupted)`：监督器写 `interrupted`、`check_result`(R7.7, BLOCKED)、`run_aborted`，**不得**再生成 `heldout_audit_done`；已写出的部分结果文件命名为 `*.partial` 且**永不被使用**；**不自动续跑、不重试**；重新运行必须使用新的运行目录并产生新的事件日志 | 无中断 → `NOT_APPLICABLE`（有效条件成立才算数；验收报告单列「R7.7 NOT_APPLICABLE」，不并入 PASS 计数） | 中断 → BLOCKED `INTERRUPTED`；中断后遗留 `.final` 文件而无 `heldout_audit_done` 事件 → FAIL；`NOT_APPLICABLE` 的有效条件不成立（有 `interrupted`、账本有终止记录、遗留 `*.partial`）→ FAIL `R77_NA_INVALID`；缺少 R7.7 的 `check_result` 且存在 `heldout_audit_done` → FAIL `EVENT_ORDER_VIOLATION` | 新 |

**R7 的整体判定（修订 4）：** R7.1–R7.6 在正常运行中必须各有 `check_result`=PASS；R7.7 必须有 `NOT_APPLICABLE`（无中断）或 `BLOCKED`（有中断）。验收脚本对 R7 的汇总写成「R7.1–R7.6 PASS；R7.7 NOT_APPLICABLE」，**不写成 R7.1–R7.7 全部 PASS**。

### 4.3 T1–T7

| 编号 | 检查 | 正常 → 期望 | 异常 → 期望 | 承担者 |
|---|---|---|---|---|
| T1 | train-only 拟合；val/test 未被打开（I1–I4） | 语料行数 = train 合格行数，语料哈希已记录，受控缺席见证通过（11.4；仅指受控检查本身）→ PASS | 喂入行数不符、语料哈希缺失 → FAIL；含 val/test 路径 → FAIL | 新（拟合脚本 + 验收脚本） |
| T2 | 特殊 ID 为 0/1/2；`259 < 实际词表 ≤ 4096` | → PASS | V=259（没学到合并规则）、V>4096、特殊 ID 错 → FAIL | 新 |
| T3 | 重复拟合：至少再拟合一次（**至少一次在独立进程**，CLARIFICATION），`tokenizer.json` SHA-256 相同 | 相同 → PASS | 不同 → FAIL；按 v1 §4.3 不得因此改变其他冻结项，D1 就此停止 | 新 |
| T4 | round-trip：train 在 S3，val/test 在 S4 | 不一致行数 0 → PASS | >0 → FAIL | 新 |
| T5 | ID 范围 `[0, 词表)` 且不含 ID 0，对**全体**合格行（不是只窗口） | → PASS | 出现 0 或越界 → FAIL | 新（冻结读取器只检查窗口的 2048 行） |
| T6 | 文件身份：保存、记录哈希；之后每次读取先核对 | 冻结读取器与验证器每次都核对（已实现）→ PASS | 哈希不符 → 读取器 `TOKENIZER_FILE_HASH_MISMATCH`（BLOCKED）或游标 `TOKENIZER_HASH_MISMATCH`（LR2 已覆盖） | 冻（核对）+ 新（记录） |
| T7 | 三个特殊字符串在全部 NFC 文本中出现 0 次；train 部分在拟合之前，val/test 部分在 `t_fix` 之后（**AMENDMENT**，取代 R1 §8 的「先检查三个 split」，对应 S2；拟合只受 train 影响，所以事后扫描 val/test 不影响拟合） | 全部 0 → PASS | 任何一处 >0 → BLOCKED（沿用 R1 §8）；train 在拟合前检查出 >0 → BLOCKED 且不拟合 | 新；冻结读取器只检查窗口 |

## 5. Manifest 与日志前缀：单向哈希引用，不允许循环 `【APPROVED CANDIDATE】`（修订 3：正式边列表、三类依赖、统计更正；见 11.7）

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
12    BP  预算账本前缀 [0..close]（11.1）
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

## 6. `FORMAL_D1_CANDIDATE` 不是 D1 PASS；不修改冻结 Driver 的独立验收方案 `【APPROVED CANDIDATE】`

1. **性质：** `FORMAL_D1_CANDIDATE` 是冻结 Driver 写进决定文件的记账标签（`d1_driver.py` 的 `identity()`、`d1_formal_experiment`）。它只代表「配置 `status` 为 `FROZEN`，且清单里有一个自洽的 `formal` 块」。它**不**代表数据或 Tokenizer 经过了任何核对；决定文件中的 `d1_overall` 恒为 `NOT_DECLARED__PIPELINE_INCOMPLETE`。已知它可以被一个没有真实数据支撑的清单满足。
2. **独立验收脚本（新，尚未编写；`d1_acceptance.py` 为暂定名）：** 输入是运行目录。它**不信任** `identity` 与 `formal` 块，而是从工件重新核对：
   - 引用图无环，所有哈希与磁盘一致；
   - A1 的元数据与冻结配置（repo、revision、`wikitext-2-raw-v1/`）相符，三个 split 各一个 Parquet；
   - 事件日志与预算账本的每一行符合 2.4 的注册表；事件日志哈希链完整；关键前缀 K0–K4（K3 终点是 `read_phase_closed`，R6 最终读后证据在其内）经远端内容验证 RV 且与带外副本核对（11.2）；I1/I4 在其限定范围内成立（11.4）；预算账本证明总耗时 ≤ 预算，或标记 BLOCKED（11.1）；摘要格式符合 11.8；审计输出符合 11.6 的 Schema；
   - **R6.1–R6.6**（其中 R6.6 由验收脚本自己重新核对，见 4.1）、R7.1–R7.6 通过、**R7.7 为 NOT_APPLICABLE（无中断）并单独标注**、T1–T7 全部有证据并通过；
   - 冻结清单 10/10、配置 `status`、环境快照与 Python 完整版本；
   - Driver 的决定文件中 `read_resume`、`negatives_meta` 的分项结论，以及运行数据的 `identity`；
   - `authorization_ref` 必须能解析为仓库里已提交的授权文件，并记录该文件的 SHA-256（R3-D10 已批准：仓库内已提交的授权记录文件 + 其 SHA-256）。
3. **输出：** 逐闸门的 PASS / FAIL / BLOCKED / NOT TESTED（以及 R7.7 的 NOT_APPLICABLE）列表和 `ALL_GATES_PASS_CANDIDATE` 或 `NOT_ACCEPTED`。**任何必需闸门缺证据（记 BLOCKED 或 NOT TESTED），输出一律 `NOT_ACCEPTED`，不得出现 `ALL_GATES_PASS_CANDIDATE`。**失败路径的运行（K3 终点是 `run_aborted`）同样输出 `NOT_ACCEPTED`，并逐项列出已有证据、缺失证据和最终状态（11.9）。**脚本本身不宣布 D1 PASS**：D1 的结论只能由项目负责人在 ChatGPT 独立复审后作出（与冻结 Driver 的 `declared` 字段一致）。
4. **不修改冻结 Driver 的原因与代价：** 冻结代码已通过验收，任何改动都触发新的冻结与重新验收。代价是：R6 的读前读后核对只能在 Driver 之外进行（R6.3 的局限），且 Driver 的 `not_tested` 清单仍是写死的文字——验收脚本必须自己判断哪些闸门已有证据，而不能依赖该清单。
5. **后验模式（FINAL-02）：** 监督器异常退出、账本没有 `close` 的运行，由验收脚本的 `--postmortem` 模式处理（11.9 F4）。它**不向原账本和原事件日志追加任何行**——验收开始时记录两者的 SHA-256，结束时复核，被改动即 FAIL；产物是独立的 `postmortem.json` 与后验 A8（`mode`=postmortem，只引用现存工件并对缺失节点标 `absent`，**不在原日志里产生 `manifest_written`(A8)**，这是 2.4 的唯一例外）。缺 `close`、`run_aborted`、K3 / K4 时，输出始终 `NOT_ACCEPTED`，最终状态不低于 `BLOCKED(budget_unprovable)`，不得升级。
6. **验收脚本的局限（修订 2）：** 它与被验收的脚本在同一信任域内运行；它能发现不一致、缺失和被固定记录证伪的改写，不能发现「如实记录了错误事实」或「绕过记录器」的行为。这些局限在每份验收记录中明示，并由 11.2 的外部固定与审核者的独立复核补充。

## 7. 已批准的负责人决策（R3-D01…D11；2026-10-26）

逐项的批准文字、适用范围与未被选定的备选记录在 `F3B_D1_R3_OWNER_DECISION_20261026.md`。下表是本规范对这些决策的落地摘要；两者不一致时，以该记录为准。

| ID | 已批准方案（摘要） | 落地条款 | 状态 |
|---|---|---|---|
| R3-D01 | 严格分阶段获取：Tokenizer 固定之前 validation/test 仅允许 L0，禁止 L1+；缺席见证按 11.4 | 2.1、2.2、I1、I4、11.4 | OWNER APPROVED — 2026-10-26 |
| R3-D02 | T7 对 validation/test 的扫描在 Tokenizer 固定之后 | 4.3 T7 | OWNER APPROVED — 2026-10-26 |
| R3-D03 | Driver 整体前后哈希 + `stat`；接受 TOCTOU / ABA 残余风险；C-1 / C-3 为可选加强，**不视为已授权实施** | R6.1–R6.6、11.3 | OWNER APPROVED — 2026-10-26 |
| R3-D04 | 记录 `tokens_encode_only` 与含 EOS 前缀的 `tokens_total`，核对恒等式 | R7.4 | OWNER APPROVED — 2026-10-26 |
| R3-D05 | 中断 BLOCKED；不自动恢复或重试；新运行用新目录；R7.7 正常路径为 NOT_APPLICABLE | R7.7、2.4、11.9 | OWNER APPROVED — 2026-10-26 |
| R3-D06 | 仅批准 B-LFS；B-GIT、B-XET 未经受控验证不得启用 | 11.5、11.8 | OWNER APPROVED — 2026-10-26 |
| R3-D07 | **方案 X**：主预算 30 分钟（`open` 到 `close`）；K3 / K4 在 `close` 之后远端固定；初始参数 τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s；参数适用性需 CPU 测试，调整须有审批与变更记录 | 11.1、11.9 | OWNER APPROVED — 2026-10-26 |
| R3-D08 | D1 仅允许 test（及 validation）的完整性、行数、Token 统计、round-trip、特殊字符串审计；禁止训练、模型选择、调参、质量评估；统一 Schema | I6、R7.6、11.6 | OWNER APPROVED — 2026-10-26 |
| R3-D09 | 新脚本按最小任务独立开发、独立 CPU 验收，完成后整体重新冻结；不得修改现有冻结代码 | 2.4、11.2、11.8 | OWNER APPROVED — 2026-10-26 |
| R3-D10 | 授权记录在 Git 仓库，以 SHA-256 绑定批准版本与后续实验授权；不伪造签名 / 链接 / 身份 | 第 6 节 | OWNER APPROVED — 2026-10-26 |
| R3-D11 | 正式 `tokenizer.json` 不提交公开仓库；仅提交哈希、统计与允许公开的非敏感证据 | v1 §3.5、§11 | OWNER APPROVED — 2026-10-26 |

## 8. 本规范不改变的内容（核对清单）

- v1/R1/R2 全文、读取器、验证器、驱动器、`d1_env_manifest.py`、`d1_selftest_data.py`、测试、`D1_FROZEN_CONFIG.json`（`status = FROZEN`）、`D1_CODE_SHA256SUMS`、Codespaces 证据：**未改动**。
- 数据窗口（2048 个合格行）、`seq_len=64`、块长 65、游标 `d1_cursor_v2`、九步检查、P1–P5、LR1–LR9、CR1–CR3、哈希链、Tokenizer 行为冻结（R1 §8 除 T7 一行）、静态公式 `P(V)=206,976+320V`：**未改动**。
- 30 分钟的**数值**与 Driver 内的超时常量：**未改动**（S7 / R3-D07 只涉及预算范围与计时方式）。
- 本规范不授权任何下载、拟合、D1 执行、训练、GPU 或 D2/D3。

## 9. 文档一致性核对（本候选的核对方法）

对第 1 节每条引文，用脚本在源文件中逐字查找；核对 v1/R1/R2 的 SHA-256 未变；检查本文件内部：判定词、决策 ID、依赖图（正式边列表构图、拓扑排序、层级严格递减）、事件注册表与全文事件名的一致性、规范顺序与失败流程（F1a / F1b / F1c / F2 / F3a / F3b）的可满足性、摘要格式与冻结接口的对照、批准决策与正文的逐条一致性，以及不再残留任何未决的执行二选一。结果见检查点 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`。

（节号说明：第 10、13 节及之后的修订记录节不在本文件中；原「下一条唯一研发指令」位于第 12 节。完整的修订历史见原草案与各轮检查点。）

## 11. 细则 `【APPROVED CANDIDATE】`

本节给出第 2–7 节所引用的细则。每一条都标出**它能证明什么**与**不能证明什么**。凡涉及本环境之外的行为（目标文件系统、Hub 元数据字段语义、网络出口），一律标 `NOT VERIFIED` / `NOT TESTED`。

### 11.1 跨进程预算账本、监督器与终止协议（对应 S7 / R3-D07；修订 3 补全）

**目标：** 把 v1 §8 的「30 分钟墙钟硬上限」在获取、拟合、审计、读取、验证**多个独立进程**之间计量，且不依赖事件日志的 `seq` 或墙钟时间戳；并规定监督器、子进程、账本关闭、外部固定的**先后顺序**。**不修改冻结 Driver 的超时机制**（真实模式拒绝 `--timeout-seconds`，Driver 自己的 30 分钟计时器保持不变，作为第二道上限）。

**(a) 计时源与预算区间。** `time.clock_gettime_ns(CLOCK_BOOTTIME)`：同一次开机内所有进程读到同一条单调时间线，不受 `settimeofday`/NTP 跳变影响，包含挂起时间。本沙箱确认该时钟与 `/proc/sys/kernel/random/boot_id` 可读（**目标环境 NOT TESTED**）。**预算区间 = 账本 `open` 行到 `close` 行**，长度 `close.bt_ns − open.bt_ns ≤ budget_ns`（30 分钟，数值来自冻结配置，**本规范不改动**）。`open` 行含 `deadline_bt_ns = bt_ns + budget_ns`。`seq` 与事件日志的 `utc` **不是**计时来源：**`seq` 不参与任何耗时数值的计算**，但**参与账本有效性判定**（`seq` 必须从 0 连续递增；不连续、重排、`prev` 哈希链不符都使账本无效），两者不得混为一谈（见测试 (g1) / (g2)）。

**(b) 账本事件与严格状态转换。** 行格式与全部事件见 2.4(b)。合法转换如下，其余一律非法（非法转换 → BLOCKED `budget_unprovable`）：

| 当前状态 | 允许的下一行 | 下一状态 | 条件 |
|---|---|---|---|
| `NEW` | `open` | `OPEN` | 必须是 `seq` 0 |
| `OPEN` | `stage_start` | `STAGE` | `remaining = deadline_bt_ns − 当前 bt_ns > 0`；上一阶段已 `stage_end`；`stage_id` 未用过 |
| `STAGE` | `stage_end`（`status`=ok / failed / blocked） | `OPEN` | `stage_id` 与 `stage_start` 一致；已完成 (d) 的 T5–T6 且**无残留需要主动终止**（阶段自行退出，或被外部信号杀死但没有存活后代）；**直接转换，不经过 `TERMINATING`**。**`status` 不是 `ok` 之后，唯一合法的下一行是 `close`** |
| `STAGE` | `terminate_begin` | `TERMINATING` | 每个阶段至多一次。三种进入方式：到截止时间（`reason`=deadline）；监督器收到终止信号（`reason`=interrupt）；T6 发现仍存活、需要主动终止的后代（`reason`=supervisor_abort）。此后该阶段不得被计为成功；**预算结果与最终状态按 11.1(d) 的对照表分别判定** |
| `TERMINATING` | `terminate_signal`（TERM，之后可 KILL） | `TERMINATING` | 至多两行；**只能在这个状态写** |
| `TERMINATING` | `reap_done` | `REAPED` | 必含 `confirmed` 与三个时间点；**只能在这个状态写** |
| `REAPED` | `stage_end`（`status`=killed） | `OPEN` | — |
| 任意 | `anomaly` | `ANOMALY` | 此后只允许 `close`（`result`=UNPROVABLE） |
| `OPEN` / `ANOMALY` | `close` | `CLOSED` | 见 (e) |
| `CLOSED` | `wrapup_end` | `DONE` | 见 (f) |

**(c) 监督器的不变量。**
1. **单一监督器**创建账本、写全部账本行；各阶段脚本不写账本，也无权关闭账本。监督器记录自己的 `pid` 与启动时的 `bt_ns`。
2. **同一 `boot_id`、同一账本**：每次写任何账本行之前先读 `boot_id`，必须等于 `open` 行；不等 → 写 `anomaly`，之后只能 `close(UNPROVABLE)`。
3. **受计时进程都由监督器启动**：每个阶段脚本与冻结 Driver 以 `subprocess.Popen(..., start_new_session=True)` 启动（独立会话/进程组，记录 `pgid`）；监督器用 `prctl(PR_SET_CHILD_SUBREAPER)`（标准库 `ctypes` 调用）使双重 fork 后被孤立的后代重新挂到监督器下，以便等待和清理。阶段之间不重叠。
4. 每行 `O_APPEND` 写入后 `flush` + `fsync`。账本文件由监督器创建（模式 0600；同用户仍可改写，见 (h)）。
5. 监督器用 `waitpid(WNOHANG)` 加不超过 1 s 的轮询睡眠检查 `CLOCK_BOOTTIME`（不使用依赖单调钟的 `signal.setitimer` 作为唯一手段）；因此超限检测的粒度不超过 1 s，加上写入延迟，**实际终止时刻会略晚于 `deadline_bt_ns`**，该延迟计入预算而不被忽略。

**(d) 终止协议（超限时，按顺序执行；每一步都写账本行）。**
- **T1** 写 `terminate_begin{stage_id, reason}`（`reason`=deadline / supervisor_abort / interrupt）。从此刻起该阶段不得被计为成功——**即使它此后以退出码 0 自行结束**；`reason`=deadline 使 `close.result` 必为 `EXCEEDED`，其余两种使 `close.run_state` 必为 `ABORTED`（取值规则见 (e)、11.9(a)）。
- **T2** 对阶段进程组 `killpg(pgid, SIGTERM)`，写 `terminate_signal{TERM, result, errno}`：发送成功 → `result`=`sent`；`ProcessLookupError`（ESRCH，进程组已不存在）→ `result`=`gone`；其他错误（如 EPERM）→ `result`=`error`，`errno` 记真实错误号（其余情形 `errno`=`null`）。无论结果如何，这一行的 `bt_ns` 就是 `t_term_bt_ns`。
- **存活目标判定 A**（T3、T4 共用）：直接子进程尚未被 `waitpid` 回收，**或** `killpg(pgid, 0)` 仍成功，**或** 存在被重新挂靠到监督器下的后代。**A 为假**即「所有目标进程都已退出」。
- **T3（宽限期，ERRATA-EDGE-01）** SIGTERM 之后，监督器每个轮询周期（≤ 1 s）**先检查 A**：**A 为假**（所有目标已退出）→ 记录此刻为 `t_gone_bt_ns`，**提前确认，不发 SIGKILL**，也不必等满 `G_term`，直接进入 T5；**A 为真，且 `now − t_term_bt_ns ≥ G_term`**（`G_term` 初始值 10 s，R3-D07 已批准；调整须有审批与变更记录）→ 进入 T4。同一轮询里 A 已为假就不升级（检查 A 优先于截止时间判断）。若 TERM 的 `result`=`error`（信号没有送达），宽限期没有意义，监督器可立即进入 T4。
- **T4（升级）** 对阶段进程组和监督器名下被重新挂靠的非监督器自己的后代发 SIGKILL，写 `terminate_signal{KILL, result, errno}`（`result` 取值与 T2 相同）。**发送尝试的时刻**就是该行的 `bt_ns`，即 `t_kill_bt_ns`，**无论尝试成功还是失败**（失败也要记真实时刻和真实错误号）。之后按同样的轮询等待至多 `G_kill`（初始值 5 s，R3-D07 已批准；调整须有审批与变更记录）：A 变为假 → 记 `t_gone_bt_ns`；`G_kill` 用尽 A 仍为真（含 KILL 的 `result`=`error`、进程处于不可中断状态）→ `t_gone_bt_ns`=`null`，`confirmed`=false。
- **T5（回收）** 用 `waitpid` 回收直接子进程并记录退出码或信号；循环 `waitpid(-1, WNOHANG)` 回收全部被重新挂靠的后代，直到 `ECHILD`。**回收的快慢与是否需要升级无关**：是否升级只由 T3 / T4 对 A 的观察决定；回收较慢既不构成升级理由，也不是伪造证据；回收耗时计入 `kill_overhead_ns` 并受总预算约束，不另设上限。
- **T6** **残留检查**：扫描 `/proc`，凡属于该阶段会话/进程组、或父进程为监督器且不是监督器自己的辅助进程者，均为残留（`residual` 列表）。**`confirmed` 当且仅当 `t_gone_bt_ns` 非 `null` 且 `residual` 为空。**
- **T7** 写 `reap_done{confirmed, exit, residual, t_term_bt_ns, t_kill_bt_ns, t_gone_bt_ns, t_reaped_bt_ns, kill_overhead_ns}`（字段定义与核对见下），随后 `stage_end{status:"killed"}`。
- **时间消耗不得被忽略：** T2–T7 的时间全部落在 `open`…`close` 之内（`close` 在 T7 之后写）。终止耗时记入 `reap_done.kill_overhead_ns`（定义见下）。**是否构成 `EXCEEDED` 只看总耗时与终止原因，不是「发生了 `terminate_begin` 就必然超限」**——见下面的对照表。
- **`reap_done` 的终止时间字段 Schema（ERRATA-02；EDGE-01/02 修订。不新增事件、不改冻结代码、不改任何已批准参数；只在既有行上增加字段）。** 所有时间都是 `CLOCK_BOOTTIME` 的纳秒整数：

| 位置 | 字段 | 类型与含义 | 取值规则 |
|---|---|---|---|
| `terminate_signal` 行 | `result`、`errno` | `result` ∈ {`sent`, `gone`, `error`}；`errno` 为整数或 `null` | `errno` 非 `null` 当且仅当 `result`=`error`，记**真实**错误号 |
| `reap_done` | `t_term_bt_ns` | 整数。SIGTERM **发送尝试**的时刻 | 等于该阶段唯一一条 `terminate_signal{TERM}` 行的 `bt_ns`，且 ≥ `terminate_begin.bt_ns` |
| `reap_done` | `t_kill_bt_ns` | 整数，或 JSON `null` | 有 `terminate_signal{KILL}` 行 ⇔ 非 `null`，且等于该行的 `bt_ns`（**尝试时刻，成功与否都记**）。没有升级：必须是 `null`——不得省略、不得写 0、不得复制其他时间点 |
| `reap_done` | `t_gone_bt_ns` | 整数，或 JSON `null`。监督器**首次观察到 A 为假**（所有目标已退出）的时刻 | 观察到就是整数；到 `G_term`（无升级）或 `G_kill`（升级后）用尽仍未观察到则 `null` |
| `reap_done` | `t_reaped_bt_ns` | 整数。T5–T6（回收与残留检查）完成、写 `reap_done` 之前读取的时刻 | ≥ 所有前面的非 `null` 时间点，且 ≤ 本行自己的 `bt_ns`。**可以比 `t_gone_bt_ns` 晚很多**（回收慢是允许的） |
| `reap_done` | `kill_overhead_ns` | 整数 ≥ 0，**必需**，存放在 `reap_done` 行里 | **公式：** `t_reaped_bt_ns − terminate_begin.bt_ns`，必须逐位相等。度量「从决定终止到确认回收」的总耗时，是评估 `G_term`、`G_kill` 取值是否合理的依据 |

- **三类判定，互不混用（ERRATA-EDGE-01/02）：** ① **记录无效**（缺字段、类型或取值非法、时间逆序）→ BLOCKED `budget_unprovable`（`REAP_RECORD_INVALID`）；② **记录内部矛盾**（时间点、公式或行内容彼此对不上）→ FAIL `REAP_RECORD_FORGED`；③ **记录真实且自洽，但终止协议没有被遵守或结果无法确认** → BLOCKED，**不是** FORGED，并且**绝不 PASS**。
- **验收脚本的核对（S6，重读账本）。判定顺序：按下面 1→5 的顺序，第一个不符的项决定状态与代码，其余不符的项一并列出；** 因此时间点逆序先于「与行不符」被判为记录无效。
  1. **字段与类型**：上表各字段齐全且类型正确；`terminate_signal` 行有合法的 `result` / `errno`；`confirmed` 为布尔。不符 → ① 。
  2. **顺序**：`terminate_begin.bt_ns` ≤ `t_term_bt_ns` ≤（`t_kill_bt_ns`）≤（`t_gone_bt_ns`）≤ `t_reaped_bt_ns` ≤ 本行 `bt_ns`；无 KILL 时 `t_gone_bt_ns` ≥ `t_term_bt_ns`。逆序 → ① 。
  3. **与行对应、公式、内部一致**（任一不符 → ② ）：恰有一条 TERM 行且 `t_term_bt_ns` 等于它的 `bt_ns`；至多一条 KILL 行，有 ⇔ `t_kill_bt_ns` 非 `null` 且等于该行 `bt_ns`；`kill_overhead_ns` 等于公式；`confirmed` ⇔（`t_gone_bt_ns` 非 `null` 且 `residual` 为空）。
  4. **升级规则（③ ）：**
     - **没有 KILL 行**：要求 `t_gone_bt_ns` 非 `null` 且 `t_gone_bt_ns − t_term_bt_ns ≤ G_term + 1 s`（1 s 是监督器的轮询粒度，11.1(c)5）——即 SIGTERM 在宽限内已使所有目标退出。**`t_reaped_bt_ns` 多晚都不影响这一条**。否则（宽限用尽时仍有目标存活却没有升级）→ BLOCKED `TERMINATION_NOT_ESCALATED`。
     - **有 KILL 行且 TERM 的 `result`=`sent`**：要求 `t_kill_bt_ns − t_term_bt_ns ≥ G_term`，否则 → BLOCKED `TERMINATION_PROTOCOL_VIOLATION`（`KILL_BEFORE_GRACE`；记录自洽，但违反了宽限规则）。TERM 的 `result` 是 `error` 或 `gone` 时，对宽限没有下限要求。
  5. **无法确认（③ ）**：`confirmed`=false → BLOCKED `TERMINATION_UNCONFIRMED`（`close.result`=`UNPROVABLE`）；KILL 行的 `result`=`error` → BLOCKED `KILL_ATTEMPT_FAILED`，真实 `errno` 保留在记录里。这两种情形**都不是**伪造，也都**不得判整体 PASS**。
- **文档验收例子（时间以 `terminate_begin` 之后的秒数表示，换算成纳秒后适用；`G_term` = 10 s，仅作示意，不是实测）：**

| # | 记录 | 判定 | 状态 |
|---|---|---|---|
| E1 | TERM 于 0 s（`sent`）；2 s 观察到 A 为假（`t_gone`=2 s）；无 KILL 行，`t_kill`=`null`；T5–T6 因回收慢到 25 s 才完成（`t_reaped`=25 s，`kill_overhead_ns`=25 s 的纳秒数）；`confirmed`=true | 提前确认，无需升级；回收慢不影响判定 | **PASS**（该记录通过核对） |
| E2 | TERM 于 0 s；10.0 s 时 A 仍为真；KILL 尝试于 10.4 s（`sent`，`t_kill`=10.4 s）；11 s 观察到 A 为假；12 s 回收完毕；`confirmed`=true | 升级时机与记录自洽 | **PASS**（该记录通过核对；该阶段仍按终止原因判定为 BLOCKED） |
| E3 | TERM 于 0 s；10 s 时 A 仍为真；**没有 KILL 行**；进程在 18 s 自行退出（`t_gone`=18 s），`confirmed`=true | 宽限用尽仍有目标却未升级；记录本身真实自洽 | **BLOCKED** `TERMINATION_NOT_ESCALATED`（不是 FORGED） |
| E4 | TERM 于 0 s；KILL 尝试于 10.2 s，`result`=`error`，`errno`=EPERM（真实记录）；`t_gone`=`null`；`confirmed`=false | 无法确认终止，真实错误已保留 | **BLOCKED** `TERMINATION_UNCONFIRMED` / `KILL_ATTEMPT_FAILED`，`close.result`=`UNPROVABLE`（不是 FORGED；绝不 PASS） |
| E5 | KILL 行 `bt_ns`=10.2 s，但 `t_kill_bt_ns`=`null`（或与该行不等）；或没有 KILL 行却写了非 `null` 的 `t_kill_bt_ns`（时间点顺序本身合法，例如落在 `t_term` 与 `t_gone` 之间） | 记录与行内容互相矛盾 | **FAIL** `REAP_RECORD_FORGED` |
| E6 | TERM 于 0 s（`sent`）；KILL 尝试于 3 s；记录其余自洽 | 违反宽限规则，但没有矛盾 | **BLOCKED** `TERMINATION_PROTOCOL_VIOLATION`（`KILL_BEFORE_GRACE`） |
| E7 | `confirmed`=true 而 `t_gone_bt_ns`=`null`；或 `kill_overhead_ns` 与公式不符 | 内部矛盾 | **FAIL** `REAP_RECORD_FORGED` |
| E8 | 缺 `t_gone_bt_ns` 键，或 `kill_overhead_ns` 为负值 / 字符串，或 `t_reaped_bt_ns` < `t_term_bt_ns` | 记录无效 | **BLOCKED** `budget_unprovable`（`REAP_RECORD_INVALID`） |

- **终止原因与预算结果对照（ERRATA-01）：** 预算结果（`close.result`）只描述时间与账本有效性；最终状态由终止原因（和其他失败原因）决定，两者独立。

| 情形 | `close.result`（预算结果） | `run_state` | 最终状态 |
|---|---|---|---|
| 正常结束（没有 `terminate_begin`） | 按总耗时与有效性：`total_ns ≤ budget_ns` 且账本有效 → `WITHIN_BUDGET`；超出 → `EXCEEDED` | 按终点事件 | 由闸门与 S6 决定；超出预算则至少 `BLOCKED(budget_exceeded)` |
| `reason`=deadline | **`EXCEEDED`**（除非最后一行的 `UNPROVABLE` 条件成立） | `ABORTED` | **`BLOCKED(budget_exceeded)`** |
| `reason`=interrupt | 按总耗时与有效性：总耗时未超过预算且账本有效 → **可以是 `WITHIN_BUDGET`**；超出则 `EXCEEDED` | `ABORTED` | **`BLOCKED(interrupted)`**（不是 `budget_exceeded`）。若总耗时同时超出预算，则预算结果为 `EXCEEDED`，最终仍是 `BLOCKED`，两个原因都列出，主代码取最早发生者（11.9(a)(6)） |
| `reason`=supervisor_abort | 按总耗时与有效性独立判定 | `ABORTED` | 按 `run_aborted.cause` 判定的 `BLOCKED` 或 `FAIL`（例如 `RESIDUAL_PROCESS` → `BLOCKED(residual_process)`；`INTEGRITY_FAILED` → `FAIL`） |
| 预算不可证明（`anomaly`、`boot_id` 变化、账本非法）或回收未确认 | **`UNPROVABLE`**（**只是预算结果内部优先级最高**：UNPROVABLE > EXCEEDED > WITHIN_BUDGET） | `ABORTED`（或按终点事件） | 至少 `BLOCKED(budget_unprovable)`，作为原因之一列出；**不覆盖**另一个已证实的实验 `FAIL`——最终状态按严重程度（`FAIL` 高于 `BLOCKED`）取主代码，所有原因保留。整体验收 `NOT_ACCEPTED`，**任何情形都不得 PASS** |

- **优先级规则（ERRATA-EDGE-03）：**
  1. `close.result` **只表示预算结果**（时间与账本有效性）；它的优先级（UNPROVABLE > EXCEEDED > WITHIN_BUDGET）只在预算结果内部起作用，不参与实验最终状态的排序。
  2. 预算 `UNPROVABLE` **不得覆盖**另一个已经证实的实验 `FAIL`。「已证实」指该 `FAIL` 所依据的证据本身通过有效性核对（例如数据完整性不符来自哈希链完整、关键前缀经 RV 的事件日志）。
  3. 最终状态维持既有严重程度规则：`FAIL` 高于 `BLOCKED`；同级时取最早发生者；预算类 `BLOCKED` 原因内部 `budget_unprovable` 优先于 `budget_exceeded`（预算不可证明时，是否超出也无法证明）。
  4. **所有失败原因都保留**，写入 `run_aborted`（原因列表）与验收输出，不因排序而丢弃。
  5. **无论优先级如何，只要预算无法证明（`close.result`=`UNPROVABLE`），整体验收都不能通过**（`NOT_ACCEPTED`）。
- **负例：数据完整性 `FAIL` + 预算账本 `UNPROVABLE`。** 场景：S2 对 train 的 `hash_done` 与 LFS `sha256` 不符（事件日志哈希链完整，K0 经 RV），监督器随后发现账本里 `boot_id` 变化（`anomaly`）。三个维度的期望输出：

| 维度 | 期望输出 | 错误输出（验收必须拒绝） |
|---|---|---|
| 预算结果（`close.result`） | `UNPROVABLE`（原因 `boot_id` 变化） | 写成 `WITHIN_BUDGET` 或 `EXCEEDED` |
| 运行状态（`close.run_state`） | `ABORTED`（`abort_cause`=`INTEGRITY_FAILED`，`el_end_event`=`run_aborted`） | 写成 `COMPLETED` |
| 实验最终状态 | **`FAIL(INTEGRITY_MISMATCH)`** 为主代码；原因列表 = [`FAIL INTEGRITY_MISMATCH`，`BLOCKED budget_unprovable`]；S6 输出 `NOT_ACCEPTED` | 只输出 `BLOCKED(budget_unprovable)`（用预算不可证明覆盖了已证实的 FAIL）→ 验收 FAIL `STATUS_DOWNGRADED`；或输出任何通过类结论 |

- **没有发出终止的阶段同样执行 T5–T6**（回收退出状态并做残留检查），此时账本仍在 `STAGE` 状态，**不写** `terminate_signal` / `reap_done`：(i) 无需主动终止的后代 → 直接 `stage_end`（阶段自行退出为 ok / blocked，被外部信号杀死为 `failed`，`exit` 记信号）；(ii) T6 发现仍存活的后代 → **此时才**写 `terminate_begin{reason: supervisor_abort}` 进入 `TERMINATING`，再按 T2–T5、T6、T7 执行，以 `reap_done`、`stage_end{killed}` 收尾，`BLOCKED(residual_process)`。因此「阶段进程被外部信号杀死」本身不构成进入 `TERMINATING` 的理由；先收集退出状态、做残留检查，再决定走 (i) 还是 (ii)（F1b / F1c，11.9）。
- 冻结 Driver 的超时由其自身先触发时（Driver 自己以 BLOCKED 退出），监督器按正常结束记录，不发信号。

**(e) `close` 何时写、写失败怎么办。**
- **写 `close` 的前提（修订 4）：** 监督器所知的运行中阶段已全部有 `stage_end`；**不再要求**「回收已确认」或「存在成功事件」——回收未确认也必须写 `close`（`result=UNPROVABLE`），否则账本永远无法关闭。事件日志的终点要求按路径区分：**成功路径**（S0–S5 都走到）要求已有 `read_phase_closed`；**失败路径**要求已有 `run_aborted`；事件日志已不可写时，`close.el_end_event=unwritable`，`abort_cause` 与诊断写在 `close` 内。失败路径不能强求一个不会出现的成功事件（详见 11.9）。
- **`close` 的取值规则：** `result`（优先级 UNPROVABLE > EXCEEDED > WITHIN_BUDGET）——有 `anomaly`、回收未确认、`boot_id` 变化、状态机非法 → `UNPROVABLE`；否则 `total_ns > budget_ns` 或存在 `reason`=deadline 的 `terminate_begin` → `EXCEEDED`；否则 `WITHIN_BUDGET`。`run_state`：`el_end_event` 为 `read_phase_closed` → `COMPLETED`，其余 → `ABORTED`。`result` **只描述时间与账本有效性**，与实验是否成功无关，也**不覆盖**已证实的实验 `FAIL`（三维度的关系与优先级见 11.1(d) 对照表后的规则与 11.9(a)）。`el_lines_at_end` 是一个**整数**（终点事件的行号 + 1，不可写时为 `null`），不是哈希，因此不给依赖图增加边。
- **写入失败：** 监督器重试一次（含 `fsync`）；仍失败 → 向标准错误输出诊断，向仍在运行的进程组发 SIGKILL（尽力而为），以专用退出码（初始约定 70）退出。**没有 `close` 行 = `BLOCKED(budget_unprovable)`，绝不能 PASS。** S0 预检要求运行目录所在磁盘有足够空间，并在**独立的临时文件**上做一次「追加 + `fsync` + 删除」自检（不碰账本）。
- 监督器本身被杀或崩溃：无 `close` → `BLOCKED(budget_unprovable)`；**不允许另起监督器续写同一账本**，只能新建运行目录重做（与 R7.7 一致）。

**(f) 预算究竟包含什么；K3 / K4 与预算的关系（R3-D07 已批准：方案 X）。**
- 难点：K4 是账本到 `close` 为止的前缀；把 K4 推送到远端必须发生在 `close` **之后**。因此本规范规定：**K3、K4 的推送与验证在预算关闭之后**，由收尾阶段 `W` 承担，并受上限约束。这是唯一的执行方案，没有二选一。
- 预算**包含**：S0–S5 的全部活动；K0、K1、K2 的推送与远端验证（它们在 S0、S3、S4 内）；SIGTERM / SIGKILL 与回收；最终残留检查；`close` 的写入。
- 预算**不包含**：K3、K4 的推送与验证（阶段 `W`）、S6 验收脚本、人工复核。
- 收尾阶段上限 `W`（初始值 600 s = 10 分钟，R3-D07 已批准）：`wrapup_end.bt_ns − close.bt_ns ≤ W`；`wrapup_end` 是 `close` 之后**唯一**允许的账本行，不在 K4 内；缺失或超限 → `BLOCKED(wrapup_unprovable)`。
- 顺序：① `read_phase_closed` → ② 阶段末尾的回收与残留检查（(d) 的 T5–T6） → ③ 账本 `stage_end(S5)` → ④ 账本 `close` → ⑤ 计算 `P_k3`，写 `pin_K3.json`，推送，事件日志 `pin_pushed`(K3) → ⑥ 远端验证 K3（`pin_remote_verified`）→ ⑦ 计算账本到 `close` 的前缀哈希，写 `pin_K4.json`，推送，`pin_pushed`(K4) → ⑧ 远端验证 K4 → ⑨ 账本 `wrapup_end` → ⑩ S6 验收。失败路径的顺序相同，只是第 ① 步的终点事件是 `run_aborted`（11.9）。
- `close` 在 K4 内（预算终点被外部固定）；代价：K3、K4 固定前存在一个不超过 `W` 的、未被固定的窗口。
- **不允许：** 把 K3、K4 的固定放在 `close` 之前；在 `close` 之后向账本追加除 `wrapup_end` 以外的任何行。
- **参数（初始验收值，R3-D07 已批准）：** τ = 5 s、`G_term` = 10 s、`G_kill` = 5 s、`W` = 600 s。它们在目标环境是否适用需要 CPU 测试；**调整必须保留审批与变更记录**（见决策记录第 5 节），未经记录不得使用其他值。

**(g)** 本候选无此项（原草案此处是对未被选定方案的影响说明，不属于执行条款；为保持交叉引用 (h) 不变而保留编号）。

**(h) 异常与不可证明（一律 `BLOCKED`，不得判 PASS，也不得靠猜测放行）。** 账本缺失；哈希链断；首行不是 `open`；`close` 缺失或不是终行（其后只允许一行 `wrapup_end`）；非法状态转换；任意两行 `boot_id` 不同（**主机重启 / 容器重建**：跨开机无法用 `CLOCK_BOOTTIME` 计量，也不用墙钟替代）；相邻两行 `bt_ns` 倒退；相邻两行 `|Δwall − Δbt| > τ`（**时钟跳变**；τ 初始值 5 s，R3-D07 已批准）；事件日志里的阶段（`stage_id`）在账本里没有对应的 `stage_start`（按 `stage_id` 与阶段名交叉核对，**不比较时间**）；回收未确认（`TERMINATION_UNCONFIRMED`）；超过预算（`budget_exceeded`）；超过 `W`（`wrapup_unprovable`）。

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
| (h2) 有 `reason`=interrupt 的 `terminate_begin`，总耗时 < 预算，账本有效 | `close.result=WITHIN_BUDGET`，`run_state=ABORTED`，最终 BLOCKED `interrupted`（预算结果不等于实验成功） |
| (h5) 有 `reason`=supervisor_abort 的 `terminate_begin`（残留被终止并确认），总耗时 < 预算，账本有效 | `close.result=WITHIN_BUDGET`，`ABORTED`，最终 BLOCKED `residual_process`（或 `run_aborted.cause` 对应的 BLOCKED / FAIL） |
| (h6) 有 `reason`=deadline 的 `terminate_begin` 且 `reap_done.confirmed=false` | `close.result=UNPROVABLE`（预算结果内部优先于 `EXCEEDED`），最终至少 BLOCKED，主代码 `budget_unprovable`，`deadline` 原因一并列出 |
| (h8) S2 数据完整性 `FAIL`（`INTEGRITY_MISMATCH`）+ 账本 `boot_id` 变化（`UNPROVABLE`） | `close.result=UNPROVABLE`；`run_state=ABORTED`；最终 **`FAIL(INTEGRITY_MISMATCH)`** 为主代码，原因列表含 `BLOCKED budget_unprovable`；整体 `NOT_ACCEPTED`；若只输出 `BLOCKED(budget_unprovable)` → 验收 FAIL `STATUS_DOWNGRADED` |
| (h7) 任一终止情形 | 不得出现 PASS；不得出现 `ALL_GATES_PASS_CANDIDATE` |
| (h3) 回收未确认仍必须写 `close` | `close.result=UNPROVABLE`，不因前提不满足而拒绝关闭账本 |
| (h4) 失败路径的 `close` 的 `el_end_event` 是 `run_aborted`，事件日志里却有 `read_phase_closed` | FAIL `EVENT_LOG_BROKEN` |
| (i) `reap_done.confirmed=false` | BLOCKED `TERMINATION_UNCONFIRMED` |
| (j) 阶段脚本留下残留后台进程 | BLOCKED `residual_process` |
| (k) `close` 之后出现 `wrapup_end` 以外的行 | BLOCKED |
| (l) `wrapup_ns` > W | BLOCKED `wrapup_unprovable` |
| (m) `reap_done` 缺任一必需字段（`t_term_bt_ns` / `t_kill_bt_ns` / `t_gone_bt_ns` / `t_reaped_bt_ns` / `kill_overhead_ns`），或为非整数（`t_kill_bt_ns`、`t_gone_bt_ns` 允许 `null`）/ 负值 / 时间逆序；`terminate_signal` 行缺 `result` / `errno` 或取值非法 | BLOCKED `budget_unprovable`（`REAP_RECORD_INVALID`） |
| (m1) 只发 SIGTERM，2 s 内观察到所有目标退出，之后回收很慢（`t_reaped`−`t_gone` 很大）；无 KILL 行，`t_kill_bt_ns`=`null`，`kill_overhead_ns` 等于公式（E1） | PASS（该记录通过核对；回收慢不是升级理由） |
| (m2) 宽限用尽仍有存活目标，KILL 尝试时刻 ≥ `t_term_bt_ns` + `G_term`，`t_kill_bt_ns` 等于 KILL 行的 `bt_ns`（E2） | PASS（该记录通过核对） |
| (m3) 没有 KILL 行，`t_kill_bt_ns` 却是非 `null`（伪造 SIGKILL 时间）；或有 KILL 行而 `t_kill_bt_ns` 为 `null` / 与该行 `bt_ns` 不等（E5） | FAIL `REAP_RECORD_FORGED` |
| (m4) `kill_overhead_ns` ≠ `t_reaped_bt_ns − terminate_begin.bt_ns`；或 `confirmed` 与（`t_gone_bt_ns` 非 `null` 且 `residual` 为空）不一致（E7） | FAIL `REAP_RECORD_FORGED` |
| (m5) 宽限用尽时仍有目标存活，没有 KILL 行，目标稍后自行退出（`t_gone` > `t_term` + `G_term` + 1 s）（E3） | BLOCKED `TERMINATION_NOT_ESCALATED`（不是 FORGED） |
| (m6) TERM 的 `result`=`sent`，KILL 尝试距 TERM < `G_term`，其余自洽（E6） | BLOCKED `TERMINATION_PROTOCOL_VIOLATION`（`KILL_BEFORE_GRACE`） |
| (m7) KILL 行 `result`=`error`（真实 errno），`t_gone`=`null`，`confirmed`=false（E4） | BLOCKED `TERMINATION_UNCONFIRMED` / `KILL_ATTEMPT_FAILED`，`close.result`=`UNPROVABLE`；不是 FORGED；绝不 PASS |
| (m8) TERM 的 `result`=`error`（未送达），监督器立即升级 KILL（无宽限），其余自洽 | PASS（该记录通过核对；该阶段仍按终止原因判定为 BLOCKED） |
| (m9) TERM 的 `result`=`gone`（进程组已不存在），无 KILL 行，`t_gone` 约等于 `t_term` | PASS（该记录通过核对） |
| (n) 没有 `terminate_begin` 却出现 `terminate_signal` 或 `reap_done`（例如阶段进程只是被外部信号杀死，监督器却照搬终止序列） | BLOCKED `budget_unprovable`（`LEDGER_BAD_TRANSITION`） |

**残余风险：** 账本由与被计量代码同一信任域的监督器写入，同用户可改写文件（靠 K0、K4 外部固定与 A8 间接约束）；绕过监督器的操作（手工下载、另开终端）不被计量；`stage_start` 之间的人为等待算入预算，可能让预算过紧；一次重启使整个运行作废；监督器的 1 s 轮询粒度与 `G_term`、`G_kill` 都会让终止略晚于截止时刻；进程若处于不可中断状态则无法确认回收；`PR_SET_CHILD_SUBREAPER` 与 `/proc` 扫描在目标环境的可用性 **NOT TESTED**；τ、`G_term`、`G_kill`、`W` 为 R3-D07 批准的初始验收值，适用性需 CPU 测试；K3 / K4 固定前存在不超过 `W` 的未固定窗口。

### 11.2 哈希链的真实能力与关键前缀的外部固定（对应 S6；修订 3 补全远端内容验证）

- **哈希链能做什么：** 检测「只改了某一行而没重算其后各行 `prev`」的修改。**不能做什么：** 能写文件的人可以重算整条链，所以单靠链既不能阻止、也不能发现整体改写、尾部截断或在末尾追加伪造行。因此 2.3 中先前「日志防篡改」的说法在本稿**撤销**，改为「完整性检测」。
- **关键前缀与固定记录：**
  - **K0** = 预算账本第 0 行（`open`）的前缀；
  - **K1** = 事件日志 `P_{k1}`，`k1` 为 `tokenizer_hash_logged` 所在行；
  - **K2** = `P_{k2}`，`k2` 为 `heldout_audit_done` 所在行；
  - **K3** = `P_{k3}`，成功路径的 `k3` 为 **`read_phase_closed`** 所在行（修订 3：不再是 `driver_exit`。最终读后快照、`post_read_snapshot`、三个 `gate_result` 都在 K3 之内，见 2.4、R6.6）；**失败路径**的 `k3` 为 `run_aborted` 所在行（修订 4，11.9），此时 K3 只固定「最终日志前缀」，不含成功闸门结论；
  - **K4** = 预算账本到 `close` 为止的前缀（R3-D07 方案 X；`close` 在 K4 内）。
- **固定记录 `pin_Kn.json`**（规范 JSON：键排序、紧凑分隔符、ASCII 转义，末尾一个换行；与冻结 Driver 的 `canon()` 同一序列化，外加换行）：`{"end_event": …（成功路径的 K3 为 `read_phase_closed`，失败路径为 `run_aborted`）, "line_count": N, "log": "event_log" | "budget_ledger", "name": "Kn", "prefix_digest": "sha256:<64 位十六进制>", "run_id": …, "schema": "d1_pin_v1"}`。`line_count` = `k + 1`。`pin_digest` = 该文件**原始字节**的 `sha256:` 摘要。不含数据，不含文本。
- **固定方式（R3-D09 已批准的默认）：**
  1. **Git 推送：** 把 `pin_Kn.json` 提交并**普通推送**到远端的专用证据分支（避免改动代码分支）。推送需要对 Git 远端的出口，**与 `HF_HUB_OFFLINE` 无关**；出口被封 → `BLOCKED`，**不得跳过固定**。
  2. **带外副本：** 在继续下一阶段之前，把 `name`、`line_count`、`prefix_digest`、`pin_digest` 与提交 SHA 通过独立于执行主机的渠道发给审核者或负责人，由对方留存。
  3. **可选加强（未选定，不属于已批准的默认；采用须另行授权）：** 由负责人持有、**不在执行主机上**的密钥签名；或外部时间戳服务（需第三方出口）。
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
| C-4 | 每个读取子进程前后各哈希一次 | 子进程粒度的变化 | 必须改冻结 Driver（触发重新冻结），本规范不采用 |

- **可验证验收条件：** 验收记录必须逐字写出「该检查只证明两个检查时刻一致」这句限定语（脚本模板内含此文本，缺失 → 验收失败）；若选用 C-1/C-2/C-3，则对应控制的证据（副本哈希、`lsattr` 输出、监视日志与心跳）为必选工件。合成测试：把文件改一字节再改回（保持 `ctime` 被测试夹具回写）→ 不选 C-3 时**预期漏检**并被如实记录；选 C-3 时 FAIL。
- **时序（修订 3）：** 最终读后快照必须在 Driver 退出、`children_reaped` 之后、K3 固定**之前**写入，并连同相应的 `gate_result` 一起落在 K3 的前缀之内（2.4、R6.2、R6.6）；不得先固定 K3 再补写关键读后证据。该时序由独立验收的 R6.6 重新核对（4.1）；失败路径没有 `read_phase_closed`，R6.6 记 NOT TESTED（11.9）。
- **残余风险：** 在已批准的配置下，该检查不覆盖运行期内的 TOCTOU/ABA；负责人已在 R3-D03 明确接受这一残余风险；加选 C-1 / C-3 须另行授权。



### 11.4 I4 缺席见证的范围、措辞与局限（对应 I4 / R3-D01；修订 3 统一措辞）

- **统一表述（全文、验收记录、报告只能使用这句话，或与之等价的更弱表述）：** **「在受控范围内、指定检查时刻，未发现 validation/test 访问迹象。」** 本稿不使用、验收记录也**不得写**：「证明从未访问」「证明所有缓存都不含相关内容」「证明不存在未记录的网络或流式读取」。R6/T1 中的「未被打开」按此理解（CLARIFICATION，R3-D01 已批准）。
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
  4. **已批准（R3-D06）：只接受 B-LFS。** B-GIT 只有在 `blob_id` 语义在受控的仅 L0 元数据任务（**需另行授权，本规范不执行**）中被验证、并经负责人另行批准之后才可启用；B-XET 单独出现 → BLOCKED。三个 split 必须全部具备被接受的基础，否则整体 BLOCKED。
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
- **与「一次性」的关系：** v1 §5.5 把「最终 test 评估」留给 D3 的一次性事项；本审计**不是评估**。R3-D08 已批准在 D1 阶段做该审计（完整性与统计，不是评估）。

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
- **`prohibited` 的规范内容（R3-D08 批准的文本，见决策记录第 6 节）：** `["training","model_selection","hyperparameter_tuning","early_stopping","checkpoint_selection","quality_evaluation","threshold_setting","tokenizer_refit_or_adjustment","design_change_from_audit_results","reporting_as_model_metric"]`。`usage_declaration` 对象的规范 JSON 为 `{"prohibited":[…],"purpose":"integrity_and_tokenizer_statistics_only"}`；其对象摘要为 `sha256:72e378a7b8b0d4a4066e429ef994bd6850fe0ba7788103fc81aa5e83bd85f310`（已批准值，登记在决策记录第 6 节；该取值的待核对事项见决策记录）。
- **规范文本与哈希如何核对：** 已批准文本的对象摘要登记在授权记录文件（`authorization_ref` 所指文件，其自身 SHA-256 也被记录）里。验收脚本读取该已批准摘要，并核对：(1) `usage_declaration` 重新计算的对象摘要等于已批准摘要；(2) `usage_declaration_digest` 等于该重新计算的值。**授权记录里缺少该摘要时，验收脚本不得用别处的值代替，只能判 `BLOCKED USAGE_DECLARATION_UNAPPROVED`。**

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
- **预算账本：** BP0（`open` 行）与 BP（到 `close`）都是前缀；A8 同时引用 PIN0 与 PIN4；验收脚本另验证 BP0 是 BP 的前缀（`sub`）。
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

- **映射规则：** (1) `EXCEEDED` ⇒ 最终状态至少是 `BLOCKED(budget_exceeded)`，永远不是候选通过；(2) `UNPROVABLE` ⇒ 最终状态至少是 `BLOCKED(budget_unprovable)`，作为原因之一列出，但**不覆盖**已证实的 `FAIL`；(3) `ABORTED` ⇒ 最终状态取 `run_aborted.final_status`（并与其他原因按 (6) 合并），S6 输出 `NOT_ACCEPTED`；(4) `COMPLETED` 且 `WITHIN_BUDGET` 且所有必需闸门都有证据并通过，才可能是 `ALL_GATES_PASS_CANDIDATE`；(5) 终止原因与预算结果分开判定（`deadline` → `EXCEEDED` / `BLOCKED(budget_exceeded)`；`interrupt` → 预算结果可为 `WITHIN_BUDGET`，最终 `BLOCKED(interrupted)`；`supervisor_abort` → 按 `run_aborted.cause`；回收未确认或预算不可证明 → `UNPROVABLE`；详见 11.1(d) 对照表）；(6) 多个原因并存时，最终状态取最严重者（`FAIL` 高于 `BLOCKED`，同级取最早发生者；预算类原因内部 `budget_unprovable` 优先于 `budget_exceeded`），**所有原因都保留并列出**；(7) 无论优先级如何，预算无法证明（`UNPROVABLE`）时整体验收都不能通过。

**(b) 通用收尾顺序（监督器；每一步失败都只追加「缺失证据」说明，不回头改写已写的行）：**
1. 不再启动新阶段（账本状态机：`stage_end` 的 `status` 不是 `ok` 之后只允许 `close`）。
2. 对仍在运行的进程做终止协议（11.1(d) T1–T7）或残留检查（T5–T6）；记录 `reap_done` / `children_reaped`。
3. 事件日志（若仍可写）依次追加：事实性事件（`interrupted` / `driver_exit` / `children_reaped`，S5 回收已确认时可补 `post_read_snapshot`、`gate_result`、`manifest_written`(A7, `partial`=true)）→ **`run_aborted`**（`cause`、`final_status`、`code`、`missing_evidence`、`partial_artifacts`）。**监督器不写任何 PASS / NOT_APPLICABLE**；已有的 PASS 事件保持原样且不被升级为整体通过。
4. 账本 `stage_end` → `close`（取值规则见 11.1(e)）。`close.run_state=ABORTED`，`el_end_event=run_aborted`；若事件日志已不可写，则 `el_end_event=unwritable`，`abort_cause` 与诊断直接写在 `close` 里。
5. 收尾阶段 `W`（11.1(f)）：对已存在的终点事件产生并推送 pin，K3 的 `end_event` 是 `run_aborted`，K4 是账本到 `close`；执行 RV。**终点事件不存在的 pin 不产生**（例如 S4 中断时没有 K2），连同推送失败的 pin 一起记入 `wrapup_end.pins_missing`（附原因）。
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
- 预算结果 `EXCEEDED`；运行状态 `ABORTED`；最终 `BLOCKED(budget_exceeded)`；终止耗时 `kill_overhead_ns` 必须记录在 `reap_done` 里（11.1(d)）。

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
| F2：`reap_done` 缺 `kill_overhead_ns` | BLOCKED `budget_unprovable`（`REAP_RECORD_INVALID`） |
| F2：没有 KILL 行却写了非 `null` 的 `t_kill_bt_ns` | FAIL `REAP_RECORD_FORGED` |
| F2：宽限用尽仍有存活目标、没有 KILL 行 | BLOCKED `TERMINATION_NOT_ESCALATED` |
| F2：KILL 尝试失败（`result`=`error`，真实 errno） | BLOCKED `KILL_ATTEMPT_FAILED` / `TERMINATION_UNCONFIRMED`，不是 FORGED |
| 数据完整性 `FAIL` + 预算 `UNPROVABLE`，最终状态只写 `BLOCKED(budget_unprovable)` | FAIL `STATUS_DOWNGRADED` |
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

**(e) 残余风险：** 监督器自身故障时只能靠事后只读工具与此前已固定的 pin（K0、K1、K2…）取证；`PR_SET_PDEATHSIG`、`/proc` 扫描在目标环境 NOT TESTED；失败路径的 `missing_evidence` 与 `partial_artifacts` 由监督器列出，监督器本身出错时列表可能不全，所以验收脚本另做独立的目录列表对照；收尾阶段的 pin 推送在无网络时无法完成——这只会让缺失证据增多，不会让任何状态变好。

## 12. 来源、历史与下一条唯一研发指令

- **历史记录（保留在仓库里，不在本文件内复制）：** 原草案 `F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`（FINAL-005 版及其第 12、14、16、18 节的逐轮修订记录）、`F3B_D1_PRE_REAL_SPEC_R3_CHECKPOINT_20261026.md`（含修订 2「29 条边」的错误记录及修订 3 的更正、各轮 FAIL / 修订背景）、v1 / R1 / R2。
- **负责人决策：** `F3B_D1_R3_OWNER_DECISION_20261026.md`（R3-D01…D11，`OWNER APPROVED — 2026-10-26`）。
- **登记与完整性：** 决策记录与本文件的 SHA-256、Git 提交、源基准与批准日期登记在 `F3B_D1_R3_OWNER_DECISION_CHECKPOINT_20261026.md`（批准时的候选版）、`F3B_D1_R3_FINAL_ERRATA_CHECKPOINT_20261026.md`（ERRATA-001 版）与 `F3B_D1_R3_ERRATA_EDGE_CHECKPOINT_20261026.md`（边界勘误后的候选版，当前有效）。

**下一条唯一研发指令：** 等待 ChatGPT 独立核对本候选规范与批准记录。审核通过后，才能正式冻结 R3。真实 D1、正式 Tokenizer 拟合及新脚本开发仍需独立授权；第一个合成 CPU 实验也必须单独取得执行授权。

---

**最终状态：`OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`。** 未标记 FROZEN，未标记 PASS；真实 D1 NOT TESTED / NOT AUTHORIZED；新机制全部 NOT TESTED。
