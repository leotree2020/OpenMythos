# F3-B / D1 — 执行前冻结方案 R1（修订版）

**状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`**

日期：2026-10-26。起草者：Claude Code。仓库：`leotree2020/OpenMythos`；分支：`mini-mythos-p1c-gate22c-readiness`。
基准 Commit：`ab6d8271f30cb49e097f3979e29f42bf0e96d545`（v1 方案所在提交）。
v1 原文：`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`（336 行，SHA-256 `a55b2cb7a9e04d3b38dd4657b08bc90c478ef31204b5435e8916e3bbb362ba9e`，git blob `cdab6660eb83d8c774efc678d88f3341cd49c054`）。**v1 原样保留作为历史证据，本次未改动一个字节。**

## 0. 本文件是什么、不是什么

- 这是对 v1 **验收逻辑**的修订，**仅文档**。没有下载 Parquet、没有拟合 Tokenizer、没有实例化或训练模型、没有 GPU、没有读取任何真实数据行。
- 修订成功**不是** D1 实验 PASS。D1 仍然 `NOT TESTED / NOT AUTHORIZED`；D2、D3 `NOT TESTED`。
- 来源说明：本次修订依据项目负责人下达的 7 条修订项（ChatGPT / Work 的复审意见）。**Work 复审原文不在仓库中**，我没有读到，所以下面「v1 的问题」是我对这 7 条指令的理解，而不是对原文的转述；若与 Work 原意有出入，以 ChatGPT 复审为准。
- 标签沿用 v1：**FROZEN**（执行前冻结，不得因结果修改）、**DERIVED**（由源码/算术推出）、**NOT VERIFIED / NOT MEASURED**（未确认）。
- **继承不变**：v1 第 1 节（Git 核对）、第 2 节（授权边界）、第 3.1–3.2 节（数据身份与获取方式）、第 3.4–3.5 节（测量项与许可）、第 4.1 节中本文件未覆盖的部分、第 8 节（依赖与资源）、第 10 节（风险登记）仍然有效。**凡本文件与 v1 冲突，以本文件为准**；冲突点见第 2 节映射表。

## 1. v1 存在的验收逻辑问题（对 7 条修订项的归纳）

| 编号 | v1 的问题 | R1 的处理 |
|---|---|---|
| P1 | N1/N2 通过**改写游标**再「重算位置使其自洽」来模拟跳读/重读。自洽的游标既可能被加载检查拒绝，也可能被接受，预期结果不确定；并且这混淆了「游标被篡改」与「读取过程出错」两种不同故障 | 第 3 节：N1/N2 改为**合法游标恢复后，读取过程中受控地整行跳过/重复**，并写明首个受影响来源行、预期错误码和独立检测条件 |
| P2 | 加载阶段会拒绝的负例与读取阶段才能发现的负例，共用一套「FAIL」口径 | 第 4 节：分为 **LR（加载拒绝类）** 与 **CR（继续读取类）**，各有 PASS 判据 |
| P3 | 游标校验只有位置公式，缺少 Token 内容、来源行身份、偏移合法性、EOF、输出前缀/哈希链 | 第 5 节：9 步固定顺序的游标校验 |
| P4 | C1/C2 的覆盖条件用「不满足则按备用点顺序追加」，使中断调度变成**结果相关**的；并把「carry 非空」当作要求，隐含空 carry 不正常 | 第 6 节：5 个**预先确定、升序**的中断点；空 carry 是**合法**状态，并有专门的合法性检查 |
| P5 | 未写明 Token ID 的字节序列化、哈希输入、哈希链初值、尾部 Token 核算 | 第 7 节 |
| P6 | Tokenizer 的 encode/decode/特殊 Token/自动添加/padding/truncation/后处理行为没有逐项冻结 | 第 8 节 |
| P7 | v1 第 9.2 节的 832 差额写成「无法解释」 | 第 10 节勘误：已解释并对账成功，并给出公式 `P(V)=206,976+320V` 及适用前提 |

## 2. v1 → R1 规则映射（冲突处以 R1 为准）

| v1 条目 | R1 | 说明 |
|---|---|---|
| 5.2 中断块 `b1=211`、`b2=1511` 与备用点 | **作废**，由第 6 节 P1–P5 取代 | 去掉结果相关的备用点 |
| 5.3 游标 `d1_cursor_v1` | **取代**为 `d1_cursor_v2`（第 5.1 节） | 增加身份、EOF、前缀字段 |
| 5.3 的位置一致性公式 | 保留并并入第 5.2 的第 7 步 | |
| 5.4 的 C1/C2 | **作废**，由第 6 节性质 K1–K5 取代 | |
| 5.5 的 R1–R7 | **取代**为第 9 节 R1–R8 | R4、R5 重写，新增尾部核算 |
| 6 的 N1 | → **CR1** | 读取过程跳行，不再改游标 |
| 6 的 N2 | → **CR2** | 读取过程重复行 |
| 6 的 N3a | → **LR1** | |
| 6 的 N3b | → **CR3** | 绕过加载检查后继续读取 |
| 6 的 N4 / N5 | → **LR2 / LR3** | 由「可选」改为**必备** |
| 6 的故障码 `CURSOR_INCONSISTENT` | → `CURSOR_POSITION_MISMATCH` | 名称细化 |
| 4.1 中 Tokenizer 行为描述 | 由第 8 节**补充**，其余冻结值（NFC、ByteLevel、ID 0/1/2、无 UNK、train-only）不变 | |
| 9.2 中「832 无法解释」 | **勘误**，见第 10 节 | v1 原文不改，在此处更正 |

## 3. CR 类：读取过程出错（继续读取类）负例

**定义**：游标本身**合法**，加载检查（第 5.2 节）与验证器的独立检查**都通过**；故障由读取循环中的受控注入产生；读取器**继续读到窗口末尾**，由验证器通过比较 trace 与参照发现问题。

每个负例**独立可执行**：只读取某个已保存的合法游标文件（来自第 6 节的干净 B 路径）和固定的注入开关，不依赖其他负例的结果。每次运行产生各自的 trace 文件，**从不**并入 R1–R3 使用的 A/B trace。

下面「序号」指窗口内**合格行序号**（`ordinal`，0 起）。`n` 为所用游标的 `next_eligible_row`（游标所在行，可能已读了一部分）。

| 编号 | 起始游标 | 注入（读取循环内） | 首个受影响来源行 | 预期错误码 |
|---|---|---|---|---|
| **CR1 跳行** | P2（行中间） | 读完游标所在行（序号 `n`）后，**整行跳过序号 `n+1`**：该行的 `tokens(r)` 一个也不进入流，然后从 `n+2` 继续 | 序号 `n+1`，物理行号 = 验证器独立映射得到的 `source_row_index` | `ROW_SKIPPED(train, source_row_index)` |
| **CR2 重复** | P4（块对齐） | 读到序号 `n+1` 的一整行后，**回退并把该行再完整读一遍**，然后继续 `n+2` | 序号 `n+1`（第二次出现） | `ROW_DUPLICATED(train, source_row_index)` |
| **CR3 偏移错位** | P2（行中间） | 临时关闭加载检查，把 `row_token_offset` 加 `δ`（`δ=+1`；若 `offset+1 ≥ len(tokens(r))` 则取 `δ=−1`），其余字段不变，然后继续读取 | 序号 `n`（该行少读或多读 1 个 Token） | `TOKEN_OFFSET_MISMATCH(train, source_row_index)` |

**独立检测条件**：验证器**不使用读取器的任何内部状态**，只用 trace 里的块哈希和来源行片段记录，加上自己重新编码得到的参照流。故障码按下列固定顺序判定，取第一个成立者：

1. 存在合格行，其被输出的 Token 数为 0（扣除尾部后）→ `ROW_SKIPPED`，首个受影响行取序号最小者。
2. 存在合格行，其被输出的 Token 数 **大于** `len(tokens(r))` → `ROW_DUPLICATED`，取序号最小者。
3. 存在合格行，其被输出的 Token 数在 `(0, len(tokens(r)))` 内，或其输出片段在行内不连续/次序不对 → `TOKEN_OFFSET_MISMATCH`，取序号最小者。
4. 块哈希与参照不同，但上面三项都不成立 → `UNCLASSIFIED_DIVERGENCE`（视为验证器无法归类，负例**不通过**）。

**CR 类 PASS 判据**（每个负例都必须全部满足，meta-PASS）：

- (a) 起始游标通过读取器的加载检查，**并且**通过验证器的独立检查（证明这是合法游标，不是加载拒绝类）。
- (b) 读取器没有抛异常，读到了窗口末尾，trace 含该游标之后的全部块。
- (c) 验证器输出的故障码、`split`、`source_row_index` 与上表一致，其中 `source_row_index` 由验证器自己从 Parquet 与合格行规则映射，**不取自 trace**。
- (d) 有效注入保护：该 trace 与同一游标的干净恢复 trace 至少有一个块哈希不同；否则判 `BLOCKED(invalid injection)`，**不算通过**。
- (e) 阳性对照：同一次执行中，同一起始游标的**无注入**恢复 trace 与参照逐块一致。
- (f) 该 trace 中，游标之前已输出的前缀块（`block_index < emitted_blocks`）不出现，且首个块号正好等于游标的 `emitted_blocks`。

## 4. LR 类：加载拒绝类负例

**定义**：游标文件被改成**非法**，期望是读取器的加载检查在**输出任何块之前**拒绝它。

**LR 类 PASS 判据**（每个都必须全部满足）：

- (a) 被改文件的 SHA-256 与原游标不同（注入确实发生）。
- (b) 读取器加载时抛出 `CursorError`，其 `code` 等于下表预期，且是第 5.2 节固定顺序中**第一个**失败的检查。
- (c) trace 中**零个**块（拒绝发生在输出之前）。
- (d) 验证器对**同一个被改文件**运行自己的独立游标检查，得到**相同**的故障码（两套实现互相印证）。
- (e) 被改文件与原游标**仅有一个字段**不同（由验证器逐字段 diff 确认），以保证「第一个失败检查」就是预期的那个。

| 编号 | 起始游标 | 唯一改动 | 预期 `code`（对应检查步骤） |
|---|---|---|---|
| LR1 | P2 | `row_token_offset` 加 `δ`（同 CR3 的 `δ` 规则），`stream_token_pos` 不变 | `CURSOR_POSITION_MISMATCH`（第 7 步） |
| LR2 | P1 | `tokenizer_sha256` 的最后一个十六进制字符改为另一个字符 | `TOKENIZER_HASH_MISMATCH`（第 3 步） |
| LR3 | P1 | `dataset.revision` 改为 `"main"` | `REVISION_MISMATCH`（第 2 步） |
| LR4 | P3（carry 恒非空） | `carry[0]` 改为另一个**合法**ID（`+1`，若越界则 `−1`，且结果 ≠ 0） | `CARRY_TOKEN_MISMATCH`（第 8 步） |
| LR5 | P1 | `row_tokens_sha256` 的最后一个十六进制字符改为另一个字符 | `ROW_IDENTITY_MISMATCH`（第 6 步） |
| LR6 | P2 | `row_token_offset` 改为 `len(tokens(r))`（刚好越界） | `OFFSET_OUT_OF_RANGE`（第 5 步） |
| LR7 | P5（EOF） | `row_token_offset` 改为 `1` | `EOF_INCONSISTENT`（第 5 步） |
| LR8 | P3 | `chain_hash` 的最后一个十六进制字符改为另一个字符 | `CHAIN_HASH_MISMATCH`（第 9 步） |
| LR9 | P4 | `last_block_hash` 的最后一个十六进制字符改为另一个字符 | `LAST_BLOCK_HASH_MISMATCH`（第 9 步） |

**不是负例的合法性检查（阳性）**：P4 的 `carry` 为空，是**合法**状态，加载必须成功（属性 K4，见第 6 节）。

**负例整体判定**：LR1–LR9 与 CR1–CR3 **全部**满足各自 PASS 判据，负例部分才 PASS；任何一个 `BLOCKED(invalid injection)` 或判据不满足，则整体不 PASS。负例的 meta-PASS 与 D1 数据读取的 PASS 是**两个不同的结论**，在 `D1_DECISION.json` 中分别记录。

## 5. 游标 `d1_cursor_v2` 与校验（强化）

### 5.1 游标结构（FROZEN）

规范 JSON：键按字典序排序，分隔符 `(",", ":")`，`ensure_ascii=True`，UTF-8，不带末尾换行。文件的 SHA-256 在 trace 中记录。

```json
{
  "schema": "d1_cursor_v2",
  "dataset": {"repo_id": "...", "config": "...", "revision": "...", "split": "train",
              "parquet_sha256": "..."},
  "tokenizer_sha256": "...",
  "window_rows": 2048, "seq_len": 64, "block_len": 65,
  "next_eligible_row": 0,       // 游标所在行的序号（窗口内 0 起）；EOF 时 = window_rows
  "source_row_index": 0,        // 该行的 Parquet 物理行号；EOF 时 null
  "row_text_sha256": "...",     // 该行 NFC 文本的 SHA-256；EOF 时 null
  "row_tokens_sha256": "...",   // 该行 tokens(r)（含 EOS 前缀）按第 7 节序列化的 SHA-256；EOF 时 null
  "row_token_offset": 0,        // tokens(r) 中已进入流的个数；合法范围 [0, len(tokens(r))-1]；EOF 时 0
  "carry": [],                  // 已进入流、尚未组成完整块的 Token ID，长度 0..64，空是合法状态
  "emitted_blocks": 0,
  "stream_token_pos": 0,
  "chain_hash": "...",          // 第 7 节的哈希链值 H_{emitted_blocks}
  "last_block_hash": null,      // emitted_blocks=0 时为 null，否则是第 emitted_blocks-1 块的哈希
  "eof": false,
  "rng": null
}
```

**位置规范化（FROZEN）**：当流位置恰好落在某行 `tokens(r)` 的末尾时，游标一律表示为「下一行、`row_token_offset = 0`」（该行是最后一行则为 EOF），不允许出现 `offset == len(tokens(r))` 的表示；因此第 5 步把 `offset == len` 判为非法（LR6 利用这一点）。P3、P4 的流位置若恰在行末，同样按此规范化。

### 5.2 加载检查（FROZEN；固定顺序，第一个失败者即为该游标的故障码）

读取器与验证器**各自独立实现**这 9 步，二者不共享代码。参照量（每行的 `tokens(r)`、参照流、参照块哈希链）都由检查方自己对窗口内行重新编码得到。

| 步 | 检查 | 失败码 |
|---|---|---|
| 1 | 字段齐全、类型正确、`schema == "d1_cursor_v2"` | `SCHEMA_INVALID` |
| 2 | `dataset.repo_id/config/revision/split` 等于冻结值（`revision` 必须是 40 位十六进制，禁止 `main`）；`parquet_sha256` 等于已记录文件哈希 | `REVISION_MISMATCH` / `PARQUET_HASH_MISMATCH` |
| 3 | `tokenizer_sha256` 等于已记录的 `tokenizer.json` 哈希 | `TOKENIZER_HASH_MISMATCH` |
| 4 | `window_rows/seq_len/block_len` 等于冻结值 | `WINDOW_PARAMS_MISMATCH` |
| 5 | `0 ≤ next_eligible_row ≤ window_rows`；若 `eof` 为真则要求 `next_eligible_row == window_rows` 且 `row_token_offset == 0` 且三个行字段为 `null`，若 `eof` 为假则要求 `next_eligible_row < window_rows`（不一致 → `EOF_INCONSISTENT`）；非 EOF 时 `0 ≤ row_token_offset ≤ len(tokens(r))−1`（越界 → `OFFSET_OUT_OF_RANGE`） | `EOF_INCONSISTENT` / `OFFSET_OUT_OF_RANGE` / `ROW_OUT_OF_RANGE` |
| 6 | 非 EOF 时：`source_row_index` 等于该序号经合格行规则映射的物理行号；`row_text_sha256`、`row_tokens_sha256` 等于重算值 | `ROW_IDENTITY_MISMATCH` |
| 7 | `stream_token_pos == Σ_{i<next_eligible_row} len(tokens(i)) + row_token_offset`（EOF 时偏移为 0），**且** `stream_token_pos == 65 × emitted_blocks + len(carry)` | `CURSOR_POSITION_MISMATCH` |
| 8 | `len(carry) ≤ 64`（否则 `CARRY_LENGTH_INVALID`）；`carry` 每个 ID 在 `[1, 实际词表)`（否则 `TOKEN_ID_INVALID`）；`carry == 参照流[65×emitted_blocks : stream_token_pos]` | `CARRY_LENGTH_INVALID` / `TOKEN_ID_INVALID` / `CARRY_TOKEN_MISMATCH` |
| 9 | 用参照块（块 `0..emitted_blocks−1`）按第 7 节重算哈希链，等于 `chain_hash`；`last_block_hash` 等于参照第 `emitted_blocks−1` 块的哈希（`emitted_blocks=0` 时必须为 `null`） | `CHAIN_HASH_MISMATCH` / `LAST_BLOCK_HASH_MISMATCH` |

**空 carry** 通过第 7、8、9 步检查即合法，**不得**作为错误处理；**EOF 游标**的 `carry` 就是尾部 Token（长度 `< 65`，可为空）。

## 6. 中断调度与覆盖性质（FROZEN，预先确定，升序执行）

**所有中断点在测量之前已完全确定**，不存在「覆盖不满足就追加备用点」。中断点按**流位置严格升序**排列；B 路径按此顺序执行。

窗口：train 的前 2048 个合格行；`seq_len = 64`，块长 65。

| 中断点 | 位置规则（FROZEN） | 由构造保证的性质 |
|---|---|---|
| **P1** | 序号 150 行的**起点**（`row_token_offset = 0`） | K1：行边界游标（`offset = 0`、非 EOF） |
| **P2** | 序号 ≥ 600 的**第一个满足 `len(tokens(r)) ≥ 2` 的行**，`offset = ⌊len(tokens(r))/2⌋` | K2：行中游标（`0 < offset < len`） |
| **P3** | 序号 900 行起点之后的**第一个**流位置 `s`，满足 `s mod 65 = 32` | K3：`len(carry) = 32`，carry **恒非空** |
| **P4** | 序号 1200 行起点之后的**第一个**流位置 `s`，满足 `s mod 65 = 0` | K4：`len(carry) = 0`，**空 carry 的合法游标** |
| **P5** | 窗口末尾（所有 2048 行读完、最后一个完整块输出之后） | K5：EOF 游标，`carry` = 尾部 Token |

**升序的保证**：相邻中断点的起始序号至少相差 300 行，每个合格行至少 1 个 Token，所以相邻点的流位置至少相差 300 个 Token；而 P3、P4 的「第一个满足同余的位置」到所在行起点的距离不超过 64 个 Token，故顺序恒为 P1 < P2 < P3 < P4 < P5，与具体数据无关。若 P2 的规则找不到满足条件的行（序号 600…899 中没有长度 ≥ 2 的行）→ `BLOCKED(schedule)`，**不改规则**。

**窗口前置条件**（输入性质检查，不满足 → `BLOCKED`，不调参）：窗口内至少 10 个一级标题行；窗口总块数 ≥ 2000。

**B 路径执行方式（FROZEN）**：6 段，每段是一次**独立的 Python 进程调用**（`--cursor-in` / `--cursor-out`）：从起点到 P1 → 从 P1 到 P2 → … → 从 P5 读到结束（零块）。每段结束时读取器对象被销毁，下一段仅凭游标文件恢复，避免进程内状态泄漏。「单进程」的含义是**不使用 DataLoader 工作进程或任何多进程并行**；各段按顺序串行执行。

**调度验收（对应 R5）**：验证器从保存的游标文件中独立核对 K1–K5 各自成立、`stream_token_pos` 严格递增、B 路径的保存顺序与 P1…P5 一致。

## 7. 序列化、哈希与尾部核算（FROZEN）

| 项 | 规定 |
|---|---|
| Token ID 序列化 | 每个 ID 为 **无符号 32 位整数，小端序（little-endian），4 字节**；序列直接首尾相接，**无头部、无长度前缀、无分隔符** |
| 块哈希 | `block_hash_i = SHA-256(65 个 ID 序列化后的 260 字节)`，输出 32 字节原始摘要，JSON 中用小写十六进制 |
| 哈希链初值 | `H_0 = SHA-256(b"MINI-MYTHOS-D1-CHAIN-V1")`（该 ASCII 字节串，无结尾 NUL） |
| 哈希链递推 | `H_i = SHA-256(H_{i−1}(32 字节原始) ‖ block_hash_i(32 字节原始))`，`i ≥ 1`；`chain_hash` 字段存 `H_{emitted_blocks}` |
| 来源行文本哈希 | `row_text_sha256 = SHA-256(NFC(text) 的 UTF-8 字节)`；另记录未做 NFC 的原始行 `raw_text_sha256` 以便追溯 |
| 行 Token 哈希 | `row_tokens_sha256 = SHA-256(tokens(r) 按上面规则序列化)`，`tokens(r)` **含**可能的 EOS 前缀 |
| 文件哈希 | trace、游标、manifest 等文件的 SHA-256 均对**磁盘上的字节**计算 |
| trace 文件 | JSON Lines，UTF-8，每行一个对象，键排序，分隔符 `(",",":")`，行尾 `\n`，不允许 NaN/Infinity |
| 尾部 | 窗口总 Token 数 `T`；完整块数 `N = ⌊T/65⌋`；`tail_len = T − 65N`（`0 ≤ tail_len ≤ 64`）；尾部 Token 被丢弃并**记录** `tail_len` 与 `tail_sha256`（对尾部 ID 序列化后 SHA-256） |
| 行覆盖核算 | 对每个合格行 `r`：`emitted(r) + tail(r) = len(tokens(r))`，其中 `emitted(r)` 为该行在所有输出块中贡献的 Token 数，`tail(r)` 为该行落入尾部的 Token 数（只有最后一个或最后几个行可能非零，由参照流按位置给出） |
| 参照 | 验证器独立构造：对窗口内每个合格行单独编码得到 `tokens(r)`，按序首尾相接成参照流，再按 65 切块。读取器不得用于生成参照 |

## 8. Tokenizer 行为冻结（补充 v1 第 4.1 节；其余冻结值不变）

| 项 | 冻结值 |
|---|---|
| 使用的类 | 原生 `tokenizers.Tokenizer`。**禁止**经由 `transformers` 的 `PreTrainedTokenizerFast` 包装（它会附加自动行为） |
| encode 调用 | `tokenizer.encode(nfc_text, is_pretokenized=False, add_special_tokens=False)`，取 `.ids` |
| 自动添加 | **不自动添加** BOS/EOS/PAD。`post_processor = None`（保存的 `tokenizer.json` 中 `post_processor` 为 `null`）。BOS 在 D1 流中**不使用**；EOS **仅**按 v1 第 3.3 节的规则由数据路径显式插入 |
| padding | **不启用**（不调用 `enable_padding`；保存的 `tokenizer.json` 中 `padding` 为 `null`）。D1 流无 padding |
| truncation | **不启用**（不调用 `enable_truncation`；`truncation` 为 `null`）。不存在最大长度截断 |
| 特殊 Token 对象 | `AddedToken(content, special=True, normalized=False, lstrip=False, rstrip=False, single_word=False)`，顺序 `<\|pad\|>`=0、`<\|bos\|>`=1、`<\|eos\|>`=2 |
| 特殊 Token 与输入文本 | `tokenizers` 可能把输入文本中**字面出现**的特殊 Token 字符串识别为特殊 Token。该行为在本环境**未实测**，因此不依赖它：执行时先检查三个特殊 Token 字符串在三个 split 全部 NFC 文本中**出现次数为 0**；非 0 → `BLOCKED`。另做一次**观察记录**（不参与 PASS）：对一段含 `<\|eos\|>` 字面的合成字符串编码，记录实际结果 |
| decode 调用 | `tokenizer.decode(ids, skip_special_tokens=False)`；`decoders.ByteLevel()`。round-trip 比较对象是 `encode(nfc_text)` 的输出（**不含**数据路径插入的 EOS 前缀）解码后与 `nfc_text` 的逐字符相等 |
| 规范化 / 预分词 | 与 v1 相同：`normalizers.NFC()`；`pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)` |
| 编码前的文本 | 先由数据路径做一次显式 NFC（用于哈希与长度核算）；Tokenizer 自带的 NFC 对已是 NFC 的文本是恒等变换，**不得**依赖它来改变文本 |
| 保存校验 | 保存 `tokenizer.json` 后立即重新加载，核对：特殊 Token 的 ID、`padding/truncation/post_processor` 均为 `null`、词表大小与拟合时一致、同一合成字符串前后编码结果相同 |
| 库 API 说明 | 上述属性名（`padding`、`truncation` 等）取自对该库 API 的记忆，**本环境未安装/未实测**；若执行时 API 与此不符，冻结提交里必须据实调整并重新经 ChatGPT 审核，不得在执行时现场改 |

## 9. R1 版本的 D1 判据（取代 v1 第 5.5 节）

D1 的数据读取与恢复部分 PASS，当且仅当下列**全部**成立，并由独立验证脚本从原始证据文件重新计算得出（不以进程退出码代替）：

| 编号 | 条件 |
|---|---|
| R1 | A、B、参照三者逐块记录序列长度相同且逐块完全一致（块哈希、起止位置、来源行片段） |
| R2 | A、B、参照的最终哈希链相同；`tail_len` 与 `tail_sha256` 相同 |
| R3 | 第 7 节的行覆盖核算对窗口内**每个**合格行成立；没有来源行被输出超过 `len(tokens(r))` 个 Token，也没有行为 0 个（除落入尾部者） |
| R4 | 第 6 节保存的 5 个游标，每个都通过读取器加载检查**和**验证器独立检查（含空 carry 的 P4 与 EOF 的 P5）；检查在输出任何块之前完成 |
| R5 | 第 6 节调度验收成立：K1–K5、严格升序、B 路径 6 段独立进程 |
| R6 | train Parquet 哈希在读取前后相同；validation/test 在 `tokenizer.json` 的 SHA-256 写入日志之前未被打开（v1 的 T1） |
| R7 | validation 与 test 只做文件哈希、行数、合格行数、Token 计数、round-trip；不用于拟合 Tokenizer，不用于任何模型评估 |
| R8 | 负例部分满足第 4 节末尾的整体判定（LR1–LR9、CR1–CR3 全部 meta-PASS） |

v1 的 T1–T6（Tokenizer 验收项）保留不变；R1 版本新增 **T7**：三个特殊 Token 字符串在全部 NFC 文本中出现次数为 0（第 8 节）。

**逻辑一致性说明**（防止规则互相冲突）：

1. R1–R3 只使用干净的 A/B 路径与参照；负例 trace 另存于独立文件，**不进入** R1–R3。
2. R4 只约束**干净**保存的游标；LR 负例中被改过的游标**应当**被拒绝，二者不冲突。
3. CR 负例使用**合法**游标，故先通过加载检查，才会进入「读取并被比较发现」；LR 负例使用**非法**游标，在加载处终止、零块。一个负例不可能同时属于两类。
4. 空 carry（P4）既是 R4 要求通过的合法游标，也是 LR9 的起点；LR9 只改 `last_block_hash`，不触碰 carry，所以与「空 carry 合法」不冲突。
5. K3（carry 恒非空）仅用于 LR4 的 carry 内容篡改；K4（carry 恒空）仅用于验证空 carry 合法。二者各有专用中断点，不依赖数据。

## 10. 勘误：F3-A 参数量的静态对账（取代 v1 第 9.2 节中「832 残差无法解释」）

**状态：DERIVED（源码阅读 + 算术）。在 V=128 处与 F3-A 脚本的运行时断言 247,936 精确吻合；在 V=4096 处未实测。**

v1 的错误：我把配置中未显式指定的 `norm_class_name` 当成 RMSNorm（每个归一化 64 个参数）。实际情况（钉住的 Parcae `69284c13746e849104f738d6d1a347b1f457df76`）：

- `models/config.py` 的默认 `norm_class_name = "LayerNorm"`；`simple_ops` 默认 `False`；
- `modules/norms.py` 只定义 `RMSNorm`，没有 `LayerNorm`，所以 `Config.Norm` 的 `getattr(norms, …)` 触发 `AttributeError`，回落到 `getattr(torch.nn, "LayerNorm")`（`config.py:193-203`）；
- `torch.nn.LayerNorm` 默认带 weight 与 bias，每个 `2×n_embd = 128` 个参数。

F3-A 配置（`gate3_cpu_train/f3a_lifecycle.py:48-53`）下的分项（`n_embd=64`、`intermediate_size=128`、4 头、`num_key_value_heads=4`、2/2/2 层）：

| 部分 | 计算 | 参数量 |
|---|---|---|
| 6 个 Transformer 块的注意力 + MLP（`bias=False`） | `6 × (4×64×64 + 2×64×128) = 6 × 32,768` | 196,608 |
| 13 个 LayerNorm（6 块 × 2 + `ln_f`） | `13 × 128` | 1,664 |
| 3 个 `ve_gate`（`Linear(32,4,bias=False)`） | `3 × 128` | 384 |
| adapter（对角注入：`A_log`、`dt_bias`、`B`） | `64 + 64 + 64×64` | 4,224 |
| `C` | `64×64` | 4,096 |
| **非词表部分合计** | | **206,976** |
| 词表相关：`wte` + 独立 `lm_head` + 3 张 value-embedding 表 | `320 × V` | `320V` |

**静态公式 `P(V) = 206,976 + 320 × V`**。`P(128) = 247,936`（与 F3-A 记录的断言一致）；`P(4096) = 1,517,696`（**DERIVED，未实测**）。v1 的「247,104 与 832 差额」就是把 13 个归一化少算了 64 个偏置：`13 × 64 = 832`。

**适用前提（任何一条不成立，公式即失效，D2 必须重新推导并实测）**：

1. `tie_embeddings = False`（`ParcaeConfig` 默认；绑定则词表项为 `256V` 而非 `320V`）；
2. `bias = False`、`qk_bias = False`、`prelude_norm = False`（若 `prelude_norm=True` 多一个归一化，+128）；
3. 归一化落到 `torch.nn.LayerNorm`（即 `norm_class_name` 为默认且 `simple_ops=False`）。若 D2 改用 `RMSNorm`（官方 `parcae-small-140m` 用的是 RMSNorm），非词表项变为 `206,976 − 832 = 206,144`；
4. `n_embd=64`、`intermediate_size=128`、`num_attention_heads=num_key_value_heads=4`（`kv_dim=64`）、层数 2/2/2、`recurrent_embedding_dimension=64`、对角注入（默认）；
5. `mean_recurrence=2`、`mean_backprop_depth=2`：它们决定 `config.n_layer = 2×2 = 4`，进而决定 `ve_gate` 出现在层号 1、3、7（`has_ve(i, 4)` 为奇数；核心层号 `i+2`，尾部层号 `i+6`），共 3 个；同时 value-embedding 表按 `has_ve(i, 6)` 为层号 1、3、5，共 3 张；
6. `padded_vocab_size = V`（F3-A 显式设置；D2 若依赖 `padding_multiple=512` 的默认取整，`V` 会被取整，公式中的 `V` 必须用**取整后**的值）。

**对 D2 的约束不变**：必须用实例化后的**实测**参数量与新的初始权重哈希，不得把 `1,517,696` 当作实测值。

## 11. R1 修订自身的审计记录

| 项目 | 内容 |
|---|---|
| 环境 | 本沙箱（Linux 6.18，只读源码审计），Python 标准库做算术核对；**未**导入 torch、tokenizers、pyarrow；**未**访问 `huggingface.co`（本环境被代理拒绝） |
| 输入 | v1 方案原文；`F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`；项目负责人 7 条修订项；钉住 Parcae 源码（`parcae.py`、`mixer.py`、`models/config.py`、`modules/norms.py`、`scripts/train.py`、`models/parcae/config.py`）；F3-A `f3a_lifecycle.py` |
| 预期 | 7 条修订项全部有明确条款；每个负例可独立执行且预期确定；规则间无逻辑冲突；v1 原文未变；三个索引文件只追加；无二进制/无数据/无模型产物 |
| 实际 | 见第 12 节（提交前填写的 Git 审计结果） |
| 状态 | 文档修订项：**DONE（待 ChatGPT 复审）**。D1 执行：**NOT TESTED / NOT AUTHORIZED**。D2、D3：**NOT TESTED**。官方 Parcae Tokenizer：**BLOCKED**。HF 访问、许可、文件哈希：**NOT VERIFIED**。窗口与中断点的数据适用性：**NOT MEASURED** |

PASS/FAIL 在本阶段**不适用**于任何实验；这里没有任何实验被执行。

## 12. Git diff 审计结果（提交前）

见本文件所在提交的提交说明与最终报告；审计方法：

1. `sha256sum F3B_D1_FROZEN_EXECUTION_PROPOSAL.md` 必须仍为 `a55b2cb7a9e04d3b38dd4657b08bc90c478ef31204b5435e8916e3bbb362ba9e`；
2. 三个索引文件的 `git diff` 中**不得出现被删除的行**（只追加）；
3. `git diff --name-only ab6d8271…HEAD` 只含：本文件 + 三个索引文件；
4. 无 `.pt/.bin/.parquet/.safetensors`；
5. 工作区 `git status --porcelain=v1` 为空，且推送为普通快进。

## 13. 需要 ChatGPT 复审的重点

1. CR1–CR3 的故障码判定顺序（第 3 节）是否覆盖了「重复且同时偏移」之类的组合；本方案按「取第一个成立者」处理，组合故障只报最先成立者。
2. 9 步游标检查（第 5.2 节）的顺序是否导致某个 LR 负例的「第一个失败检查」不是预期的那个（我逐个核对过，LR1–LR9 各只触发其目标步骤；请独立复核）。
3. P1–P5 的位置规则与 B 路径「每段独立进程」是否过度或不足。
4. 第 8 节关于 `tokenizers` 库行为的说明（特殊 Token 字面识别、`padding/truncation` 属性名）均**未实测**，是否接受「先做数据守卫 + 执行前冻结提交时据实调整」的处理。
5. 勘误的适用前提列表（第 10 节）是否完整。

## 14. 下一条唯一指令

等待 ChatGPT 复审本 R1 方案；复审通过且项目负责人明确授权后，才可先提交 D1 执行脚本与 `D1_FROZEN_CONFIG.json` 的**冻结提交**，再在有 HF 访问权限的 CPU 环境运行 D1。**在此之前不得下载、拟合、训练或启动 GPU，不得开始 D2/D3。**

---

**最终状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
