# F3-B / D1 — 执行前冻结方案 R2（最小修订）

**状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`**

日期：2026-10-26。起草者：Claude Code。仓库：`leotree2020/OpenMythos`；分支：`mini-mythos-p1c-gate22c-readiness`。
基准 Commit：`579ffd11ec2dba0b9cbf0eae67d7ce4e26874c19`（R1 所在提交）。
历史证据（均**原样保留，未改一个字节**）：
- v1：`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`（336 行，SHA-256 `a55b2cb7a9e04d3b38dd4657b08bc90c478ef31204b5435e8916e3bbb362ba9e`）；
- R1：`F3B_D1_FROZEN_EXECUTION_PROPOSAL_R1.md`（304 行，SHA-256 `f92c4e792dcb83108ac9c00a11d60fe5cb2111c1ed146f8f3b67842a943a1d7a`）。

## 0. 本文件是什么、不是什么

- R1 复审结论为 `PRE-FLIGHT FAIL`。本文件只修订 R1 中被指出的 5 处设计缺陷，**仅文档**：没有下载 Parquet、没有拟合 Tokenizer、没有实例化或训练模型、没有 GPU、没有读取任何真实数据行。
- 修订成功**不是** D1 PASS，也不是 CLOSED。D1 仍为 `NOT TESTED / NOT AUTHORIZED`；D2、D3 `NOT TESTED`。
- **继承规则**：v1 → R1 → R2 依次叠加，**凡冲突以 R2 为准**，其次 R1，再次 v1。R1 的其余条款（LR1–LR9 主体、`d1_cursor_v2` 与 9 步校验、空 carry 合法、EOF、Token 序列化、逐来源行 Token 覆盖、第 8 节 Tokenizer 冻结、第 10 节静态公式 `P(V)=206,976+320V` 及其适用前提）**保持不变**，本文件不重述。
- 标签沿用：**FROZEN**（执行前冻结）、**DERIVED**（由源码/算术推出）、**NOT VERIFIED / NOT MEASURED**（未确认）。

## 1. R1 → R2 取代表

| R1 条款 | R2 处理 | 本文件章节 |
|---|---|---|
| 第 3 节 CR 的「独立检测条件」第 1–4 条（只看续读 trace 里的零计数）与 PASS 判据 (a)–(f) | **取代** | 第 2 节 |
| 第 3 节 CR3 行（「临时关闭加载检查」、`δ=−1` 回退） | **取代** | 第 3 节 |
| 第 4 节 LR1 中「`δ` 同 CR3 的 `δ` 规则」 | **改写为固定 `+1`**（因 CR3 的 δ 规则已删除，属于由修订引起的具体冲突；LR1 其余不变） | 第 3.4 节 |
| 第 6 节 P2、P3、P4 位置规则、「升序的保证」段及其「相差 300 行」断言 | **取代** | 第 4 节 |
| 第 7 节「哈希链递推」行 | **取代** | 第 5 节 |
| 第 9 节 R1 条件中的「来源行片段」比较 | **补充**：比较对象为验证器展开 carry 归属后的规范化片段 | 第 2.2 节 |

## 2. CR 负例：前缀核算（修订项 1）

### 2.1 R1 的缺陷与 R2 的原则

R1 的 CR 判定只看**续读 trace**，而续读 trace 按规则不含游标之前的块（正确）。结果是：游标之前的所有合格行在续读 trace 里的输出 Token 数都是 0，R1 的第 1 条「输出 Token 数为 0 → `ROW_SKIPPED`」会把它们全部误判为跳行；反过来，真正被跳过的那一行没有任何独立于「零计数」的证据。

R2 原则（FROZEN）：

1. **恢复后的续读 trace 不重复输出任何历史块**（沿用 R1 CR 判据 (f)，并增强：首个块号必须等于游标的 `emitted_blocks`，且不存在 `block_index < emitted_blocks` 的块）。
2. 验证器用 **可信的干净前缀证据 + 续读 trace** 重新拼出**整个窗口**，再对窗口内**全部 2048 个合格行**逐行核算 Token 数量、原始位置、完整内容。判定依据是**整窗口核算**，绝不是续读 trace 里的零计数。
3. 故障注入后的证据与干净证据**分别保存**，互相不能覆盖。

### 2.2 trace 记录要求（FROZEN；R1 只写了「块哈希、起止位置、来源行片段」，现补全）

JSON Lines，规范化同 R1 第 7 节「trace 文件」行。每个读取器进程调用写一个 trace 文件，记录类型：

| 类型 | 字段 |
|---|---|
| `run`（首行） | `start_cursor_sha256`（输入游标文件的磁盘字节哈希；从头开始则为 `null`）、`carry_len`（游标 `carry` 长度，从头开始为 0）、`inject`（注入开关名或 `null`） |
| `block` | `block_index`（零起始）、`block_hash`、`ids`（65 个 Token ID）、`segments` |
| `final`（末行） | `tail_ids`、`tail_segments`、`tail_len`、`tail_sha256`、`chain_hash`（`H_N`，见第 5 节）、`blocks_total` |

`segments` 为列表，元素 `{"ordinal", "source_row_index", "row_offset", "count"}`，含义：该块（或尾部）里一段连续 Token 来自合格行 `ordinal` 的 `tokens(r)[row_offset : row_offset+count]`。**一个行跨块时每块各记一段**。**本次运行输出流**（所有块的 `ids` 依次相接，再接 `tail_ids`）的**前 `carry_len` 个 Token 是游标 carry，不写入 `segments`**；其来源由验证器按参照流位置 `[65×emitted_blocks, 65×emitted_blocks + carry_len)` 自行映射到行（读取器恢复后不知道 carry 的来源行，不允许它猜）。每个块的 `segments` 的 `count` 之和 = 65 − 该块中属于 carry 的 Token 数；尾部同理。

这些 `segments` 是**读取器的自述**，**不被信任**：验证器对每一段核对 (i) `source_row_index` 等于自己对该 `ordinal` 的物理行映射；(ii) 该段 Token 与块内 `ids` 的对应切片一致；(iii) `ids` 切片等于验证器自己编码的 `tokens(ordinal)[row_offset : row_offset+count]`；(iv) 块的 `ids` 重算 SHA-256 等于 `block_hash`。任何一项不成立 → `TRACE_CLAIM_INVALID`（该负例**不通过**；不是预期故障码）。

R1 第 9 节 R1 条件中的「来源行片段」在 A、B、参照之间比较时，使用验证器**展开 carry 归属后**的规范化片段（B 路径每段恢复后的第一个块，其 carry 部分由验证器补出），否则 A 与 B 的片段表示不同。

### 2.3 证据文件布局与不可覆盖规则（FROZEN）

```
evidence/clean/        A_trace.jsonl, B_seg1..B_seg6_trace.jsonl, cursors/P1..P5.json   （干净证据，只读）
evidence/negatives/CRk/  trace.jsonl, control_trace.jsonl, accounting.json              （k=1,2,3；各自独立）
evidence/negatives/LRk/  mutated_cursor.json, load_report.json                          （k=1..9）
```

- `evidence/clean/` 里的文件一经写出即**只读**；验证器在每个负例**开始前**和**结束后**各计算一次这些文件的 SHA-256，**任何变化 → `BLOCKED(evidence mutated)`**。
- `evidence/negatives/CRk/` 的输出路径在运行前必须**不存在**，已存在 → `BLOCKED(output exists)`，**不覆盖**。
- `control_trace.jsonl`：同一起始游标、**无注入**的续读 trace（R1 判据 (e) 的阳性对照），与注入 trace 同样独立保存。
- 磁盘上的起始游标 `cursors/Pk.json` 在整个 CR 过程中**不得被修改**：其 SHA-256 在注入前、注入后必须相同。

### 2.4 整窗口核算（FROZEN）

对负例 `CRk`，起始游标 `Pk` 的 `emitted_blocks = e`、`stream_token_pos = s`、`carry` 长度 `c`：

1. **可信前缀**：取 `A_trace.jsonl` 中 `block_index ∈ [0, e)` 的块。验证器**重新验证**（不假设它们可信）：每块 `ids` 的哈希等于自己独立编码得到的参照块哈希；`segments` 按 2.2 的 (i)–(iii) 核对；用这 `e` 个块按第 5 节重算哈希链，等于游标 `chain_hash`（游标本身已在 R1 第 5.2 节第 9 步被独立核对）。任何一步失败 → `BLOCKED(prefix evidence invalid)`。
2. **carry 归属**：位置 `[65e, s)` 的 `c` 个 Token 按参照流映射到合格行（可能跨行）。
3. **续读段**：负例 `trace.jsonl` 中 `block_index ≥ e` 的块和 `final` 的 `segments`（已按 2.2 核对）。
4. 把 1–3 合并为整窗口，对每个合格行 `ordinal = 0..2047` 计算：`consumed(r)` = 该行在合并后各段中的 `count` 之和（含尾部段）、按流中出现顺序排列的 `(row_offset, count)` 序列、把这些段的 Token 依次相接得到的 `consumed_ids(r)`。
5. **逐行分类**（按固定顺序取第一个成立者；全部 2048 行都要分类，一行属于哪一类只由这行自己的数据决定）：

| 序 | 条件 | 分类 |
|---|---|---|
| a | `consumed(r) == 0` | `ROW_SKIPPED` |
| b | `consumed(r) > len(tokens(r))` | `ROW_DUPLICATED` |
| c | `consumed(r) ≠ len(tokens(r))`（含 `0 < consumed < len`），或段序列不是从 0 开始首尾相接的单调覆盖，或 `SHA-256(consumed_ids(r)) ≠ row_tokens_sha256` | `TOKEN_OFFSET_MISMATCH` |
| d | 以上都不成立 | `OK` |

6. **窗口级补充**：块 `≥ e` 的块哈希与参照比较、`final.chain_hash` 与参照比较，只作辅助记录；**行级分类是判定依据**。如果存在块哈希不一致，但没有任何行被分类为非 `OK` → `UNCLASSIFIED_DIVERGENCE`（负例**不通过**）。

零计数规则因此只在**整窗口** `consumed` 上使用；游标之前的行由前缀与 carry 归属提供计数，不会被误判。

### 2.5 CR 类 PASS 判据（取代 R1 第 3 节判据；每个负例必须全部满足）

- (a) 起始游标 `Pk` 的**原始文件**通过读取器的加载检查（九步全部 PASS，`load_report` 逐步记录）**并且**通过验证器的独立检查；**读取器不提供也不使用任何关闭或绕过加载检查的开关**。
- (b) 读取器没有抛异常，读到窗口末尾，`trace.jsonl` 含游标之后的全部块与 `final`。
- (c) 首个块号 `== e`，不存在 `block_index < e` 的块（trace 不重复历史块）。
- (d) 整窗口核算 2.4 完成，且**恰好一个**合格行的分类不是 `OK`，该行的 `ordinal`、`split`、`source_row_index`（验证器自己映射）、分类（即预期错误码）与第 3 节表一致，且 `consumed(r)` 与表中预期值一致。其余 2047 行全部 `OK`。
- (e) 有效注入保护：`trace.jsonl` 与 `control_trace.jsonl` 至少有一个块哈希不同，否则 `BLOCKED(invalid injection)`，**不算通过**。
- (f) 阳性对照：`control_trace.jsonl` 按同一整窗口核算，2048 行全部 `OK`，且块序列与参照逐块一致。
- (g) 证据隔离：2.3 的所有哈希检查通过（`Pk.json` 前后相同；`evidence/clean/` 前后相同；输出路径事先不存在）。

## 3. CR 负例定义（修订项 2、3）

`n` 为起始游标的 `next_eligible_row`（游标所在行序号）；`o` 为其 `row_token_offset`。注入**只发生在读取循环内部**，由读取器在**加载检查全部通过之后**启用，且注入开关不修改任何磁盘文件。

### 3.1 表（取代 R1 第 3 节的表）

| 编号 | 起始游标 | 读取循环内注入 | 唯一异常行 | 预期分类/码 | 预期 `consumed(r)` |
|---|---|---|---|---|---|
| **CR1 跳行** | P2 | 读完序号 `n` 的行后，整行跳过序号 `n+1`，从 `n+2` 继续 | 序号 `n+1` | `ROW_SKIPPED` | 0 |
| **CR2 重复** | P4 | 读完序号 `n+1` 的一整行后，将其再完整读一遍，然后继续 `n+2` | 序号 `n+1` | `ROW_DUPLICATED` | `2 × len(tokens(r))` |
| **CR3 偏移错位** | P2 | 开始消费序号 `n` 的行时，把 Token 消费起点从 `o` 改为 `o+1`（**固定 `δ=+1`**），即该行第 `o` 个 Token 不进入流；其余字段不变 | 序号 `n` | `TOKEN_OFFSET_MISMATCH` | `len(tokens(r)) − 1` |

### 3.2 CR3 的合法游标（修订项 2）

- 原始 `P2.json` 先走**完整的九步加载检查**并全部通过；**不允许关闭任何加载检查**（R1 的「临时关闭加载检查」作废）。
- 通过之后，读取器在**读取循环内部**把序号 `n` 行的 Token 消费起点由 `o` 改为 `o+1`。这是读取过程内的消费偏差，不是改游标。
- 磁盘上的 `P2.json` 不得修改（2.3 的前后哈希检查，判据 (a)(g)）。
- 与 LR1 的区别：LR1 改**游标文件**中的 `row_token_offset`，在加载第 7 步被拒；CR3 的游标文件**原封不动**并通过全部九步，偏差发生在读取之后。

### 3.3 CR3 最小反例（修订项 3）

- P2 只允许选择 `len(tokens(r)) ≥ 3` 的行（第 4 节）。此时 `o = ⌊len/2⌋ ≥ 1` 且 `o + 1 ≤ len − 1`（`len=3` 时 `o=1`，`o+1=2=len−1`；`len ≥ 3` 恒成立），所以被丢弃的 Token 严格位于行内，该行的 `consumed = len − 1 ∈ (0, len)`，必然落入分类 c，不会落入 a 或 b。
- **删除 `δ=−1` 回退分支**。`δ` 固定为 `+1`，没有任何数据相关的分支。
- 预期故障码恒为 `TOKEN_OFFSET_MISMATCH`。

### 3.4 LR1 的唯一改动（具体冲突的消除）

R1 的 LR1 写「`row_token_offset` 加 `δ`（同 CR3 的 `δ` 规则）」。CR3 的 δ 规则已删除，故 LR1 改为：**`row_token_offset` 加 1，`stream_token_pos` 不变**。因为 P2 行满足 `len ≥ 3` 且 `o ≤ len−2`，`o+1 ≤ len−1`，仍在第 5 步合法范围内，第 5、6 步通过，第 7 步失败 → `CURSOR_POSITION_MISMATCH`，与 R1 一致。LR1 的其余条目、LR2–LR9 **一律不变**。

## 4. 中断点 P2/P3/P4 的搜索规则与升序判据（修订项 4）

记号：`cum(k) = Σ_{i<k} len(tokens(i))`，即合格行 `k` 的起点在 Token 流中的位置；`len` 含 EOS 前缀。

### 4.1 位置规则（取代 R1 第 6 节对应行）

| 中断点 | 规则（FROZEN） |
|---|---|
| P1 | 序号 150 行的起点：流位置 `cum(150)`，`row_token_offset = 0` |
| **P2** | 在合格行序号**闭开区间 `[600, 900)`** 中取**第一个** `len(tokens(r)) ≥ 3` 的行，`row_token_offset = ⌊len/2⌋`。区间内无此行 → 记录 **`BLOCKED(schedule)`**，不放宽条件、不换区间 |
| **P3** | 搜索起点**包含**序号 900 行的起点：取最小的流位置 `s ≥ cum(900)`，满足 `s mod 65 = 32` |
| **P4** | 搜索起点**包含**序号 1200 行的起点：取最小的流位置 `s ≥ cum(1200)`，满足 `s mod 65 = 0` |
| P5 | 窗口末尾（读完全部 2048 行、输出最后一个完整块之后）的 EOF 游标 |

流位置 `s` 若恰在某行末尾，按 R1 第 5.1 节「位置规范化」表示为下一行 `offset=0`（最后一行则 EOF）。P3 的 carry 长度恒为 32（非空），P4 的 carry 恒为空（合法）。

### 4.2 删除错误断言，改用实际流位置判据

R1 称「相邻中断点的起始序号至少相差 300 行」。这一说法**对 P2→P3 是错的**：P2 可能落在序号 899，而 P3 的搜索起点是序号 900，二者最近只隔 1 行。该断言**删除**。

升序的唯一判据是**实际 Token 流位置严格递增**：`s(P1) < s(P2) < s(P3) < s(P4) < s(P5)`。验证器从保存的游标文件读取 `stream_token_pos` 逐一核对；任何一处不成立 → `BLOCKED(schedule)`，不调整规则。

在 4.1 的规则下，该判据对**任意数据**恒成立（每个合格行至少 1 个 Token）；这是对规则本身的检查，不是执行的前提：

- `s(P1) = cum(150) < cum(600) < s(P2)`，因为 P2 行序号 ≥ 600 且 `offset ≥ 1`。
- `s(P2) < cum(ord_P2) + len ≤ cum(900) ≤ s(P3)`，因为 `ord_P2 ≤ 899` 且 `offset < len`。
- `s(P3) ≤ cum(900) + 64 < cum(900) + 300 ≤ cum(1200) ≤ s(P4)`（`s mod 65 = 32` 的最小解距搜索起点不超过 64；900 到 1200 共 300 行，至少 300 个 Token）。
- `s(P4) ≤ cum(1200) + 64 < cum(2048) ≤ s(P5)`。

## 5. 哈希链下标（修订项 5；取代 R1 第 7 节「哈希链递推」行）

全部块编号**零起始**：`j = 0, 1, …, N−1`，`N` 为已输出完整块数（游标中为 `emitted_blocks`）。

| 量 | 定义（FROZEN） |
|---|---|
| `block_hash_j` | `SHA-256(第 j 块 65 个 Token ID 按 uint32 小端、无头部序列化得到的 260 字节)`，32 字节**原始摘要** |
| `H_0` | `SHA-256(b"MINI-MYTHOS-D1-CHAIN-V1")`，32 字节原始摘要（初始哈希） |
| 递推 | `H_{j+1} = SHA-256( H_j ‖ block_hash_j )`，`j = 0..N−1`；`‖` 是 **32 字节原始摘要**与 **32 字节原始摘要**的字节拼接（共 64 字节输入），**不得使用十六进制字符串**参与拼接 |
| `chain_hash` | `H_N`；游标的 `chain_hash` 字段是 `H_{emitted_blocks}`（`emitted_blocks = 0` 时即 `H_0`） |
| `last_block_hash` | `block_hash_{emitted_blocks − 1}`；`emitted_blocks = 0` 时为 `null` |
| JSON 展示 | 摘要在 JSON 中用小写十六进制表示，但只是展示形式，计算始终使用原始字节 |

R1 原式「`H_i = SHA-256(H_{i−1} ‖ block_hash_i)`，`i ≥ 1`」与零起始块号冲突（`block_hash_0` 永不被使用，且游标 `last_block_hash` 的下标含义不清）。R2 用 `H_{j+1}` 的写法消除该歧义；R1 第 5.2 节第 9 步沿用的「`H_{emitted_blocks}`」「第 `emitted_blocks−1` 块」两个说法与此一致，无需改动。

**合成校验向量**（DERIVED：用 Python 标准库 `hashlib`/`struct` 对**合成**输入计算，**不是 D1 证据**，不涉及任何数据或 Tokenizer，供实现方对照字节约定）。块 0 的 ID 为 `0..64`，块 1 的 ID 为 `65..129`：

| 项 | 值 |
|---|---|
| 序列化长度（块 0） | 260 字节 |
| `H_0` | `c5a91b61d09dd6ace479fcb77286d5f3da165cc4c0f0010d44aa271aa2d9dd11` |
| `block_hash_0` | `fee16ec542015efdeec7654ea06333eb655815da008a8a349efad6d02e86ed35` |
| `H_1` = SHA-256(`H_0`‖`block_hash_0`) | `9bc269374738a4926714df76039ce40097138356c621e2aab3dfc7dff8875a10` |
| `block_hash_1` | `67e5aabc0cc44b005d4a0eedeec3c54ae65ea2b62f758f6077ea48547b9aaa57` |
| `H_2` = SHA-256(`H_1`‖`block_hash_1`) | `7ae2356958f57f0ef4ac1f872392f55f44dd422703ed64e82a4655e033833d2e` |
| 反例：把 `H_0`、`block_hash_0` 先转成十六进制字符串再拼接得到的哈希（**必须不等于** `H_1`） | `2f001906d9e7048e83651dd08c43581c14aed68fbfc2d9c7c6e03897c056c329` |

## 6. 逻辑一致性复核（R2 修订后）

1. **前缀与零计数**：零计数只用于整窗口 `consumed`；游标之前的行由干净前缀（重新验证）与 carry 归属提供计数，续读 trace 不含历史块与零计数规则不再冲突。
2. **CR 与 LR 的互斥**：CR 的游标原样通过九步；LR 的游标是单字段被改且在加载处被拒、零块。CR3 不再关闭加载检查，因此 CR3 与 LR1 不再是「同一偏移、一个绕过检查」的混淆关系。
3. **P2 条件**：`len ≥ 3` 同时满足 CR3（`o+1 ≤ len−1`）、LR1（`+1` 仍在第 5 步范围内）、K2（行中游标）。找不到 → `BLOCKED(schedule)`，三个负例同时 BLOCKED，不存在「P2 有、CR3 无」的情形。
4. **P3/P4 起点包含行起点**：与 R1 第 5.1 节位置规范化一致（`s = cum(k)` 即「下一行 offset 0」）。
5. **哈希链**：步骤 9、`last_block_hash`、`chain_hash`、`final.chain_hash` 全部用零起始的 `H_{j+1}` 约定。
6. **证据隔离与 R1–R3**：R1 第 9 节「R1–R3 只使用干净的 A/B 路径与参照」保持成立；负例 trace、control trace、核算结果只写入 `evidence/negatives/`。
7. **D1 PASS 与负例 meta-PASS**：仍是两个独立结论，在 `D1_DECISION.json` 中分别记录（R1 第 4 节末尾，不变）。

## 7. R2 修订自身的审计记录

| 项目 | 内容 |
|---|---|
| 环境 | 本沙箱（Linux 6.18，只读源码/文档审计）；仅用 Python 标准库做第 5 节合成向量的算术核对；**未**导入 torch、tokenizers、pyarrow；**未**访问 `huggingface.co`；**未**读取任何真实数据行 |
| 输入 | R1 方案原文（基准 `579ffd11…`）；项目负责人的 R2 最小修订指令（5 项）；R1 的第 3–7、9 节 |
| 预期 | 5 项修订均有明确条款；CR1–CR3 的预期故障码、唯一异常行、预期 `consumed(r)` 确定；规则间无冲突；R1 与 v1 原文未变；三个索引文件只追加；无二进制/数据/模型产物 |
| 实际 | 见提交说明与最终报告（Git diff 审计结果：v1/R1 两份 SHA-256 不变；索引文件无删除行；变更文件清单；无二进制） |
| 状态 | 文档修订：**DONE（待 ChatGPT 复审）**。D1 执行：**NOT TESTED / NOT AUTHORIZED**。D2、D3：**NOT TESTED**。官方 Parcae Tokenizer：**BLOCKED**。HF 访问、许可、文件哈希：**NOT VERIFIED**。窗口与中断点的数据适用性（P2 区间内是否存在 `len ≥ 3` 的行、窗口前置条件）：**NOT MEASURED** |

PASS/FAIL 在本阶段**不适用**于任何实验；这里没有任何实验被执行。

## 8. 需要 ChatGPT 复审的重点

1. 2.2 的 trace 记录要求（`ids` 全量、`segments` 自述但被逐段核对、carry 归属由验证器映射）是否足以支持整窗口核算且不泄露读取器内部状态。
2. 2.4 的行级分类顺序 a→b→c 在 CR1–CR3 下各自只产生唯一异常行；请独立复核没有组合故障被漏判。
3. 干净前缀取 `A_trace.jsonl` 并**重新验证**，而不是假设其可信，是否可接受。
4. 4.2 的升序论证是否严谨；`s mod 65 = 32` / `0` 的最小解距搜索起点不超过 64 的说法。
5. 第 3.4 节对 LR1 的改写是否仅限于「由修订引起的具体冲突」。

## 9. 下一条唯一指令

等待 ChatGPT 复审本 R2 方案；复审通过且项目负责人明确授权后，才可先提交 D1 执行脚本与 `D1_FROZEN_CONFIG.json` 的**冻结提交**，再在有 HF 访问权限的 CPU 环境运行 D1。**在此之前不得下载、拟合、训练或启动 GPU，不得开始 D2/D3。**

---

**最终状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
