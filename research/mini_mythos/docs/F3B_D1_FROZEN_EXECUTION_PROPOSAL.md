# F3-B / D1 — 执行前冻结方案（真实数据 + Tokenizer + 断点读取）

**状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`**

日期：2026-10-26。起草者：Claude Code（接替 Grok，按项目负责人 2026-10-26 交接指令）。
仓库：`leotree2020/OpenMythos`；分支：`mini-mythos-p1c-gate22c-readiness`；起草时 HEAD：`326121990cef4064d2c2d6cdc48a0d53da3cab3e`。
依据：`F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md` 的 D1-01…D1-04 与 D2 前置冲突；Grok 的五份 F3-B 设计文档。

## 0. 本文件是什么、不是什么

- 这是**设计文档**。本次没有下载数据、没有拟合 Tokenizer、没有读取任何真实数据行、没有实例化或训练模型、没有使用 GPU。
- 它**不是**实验结果，**不**宣布 D1 PASS 或 CLOSED。D1 要等 ChatGPT 审核本文件，并由项目负责人单独明确授权后才能执行。
- 本文件所有数值分三类标签，不混用：
  - **FROZEN**：本方案规定的参数，执行前不得因为看到结果而修改。
  - **DERIVED**：由源码阅读或算术推出，未实测。
  - **NOT VERIFIED / NOT MEASURED**：当前无法确认，执行时才会测量，或因环境限制无法确认。
- 凡被写成「历史事实」的数字，均来自仓库中已归档文档，且仅适用于其原始条件。

## 1. 继承状态与 Git 核对（本次实际执行的命令结果）

| 项目 | 结果 |
|---|---|
| 分支 | `mini-mythos-p1c-gate22c-readiness` |
| 本地 HEAD | `326121990cef4064d2c2d6cdc48a0d53da3cab3e` |
| 远端 HEAD（`git ls-remote` 与 fetch 后 `origin/…`） | `326121990cef4064d2c2d6cdc48a0d53da3cab3e`，与 ChatGPT 上次核实值一致 |
| `git status --porcelain=v1` | 空（浅克隆的新目录） |
| `git remote -v` | `origin https://github.com/leotree2020/OpenMythos`（fetch/push） |
| 受保护文件 `research/mini_mythos/gate2_1/TEST_RESULTS.json` | **本环境不存在**，也不在 Git 跟踪内。它是项目负责人旧环境中的未提交文件，本次未触碰，也无法从此环境验证其字节与哈希（`UNKNOWN`） |
| 比 `F3B_*` 更新的正式验收文件 | 未发现。最新的是 `F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md` |

状态变化说明：`SESSION_START_PROTOCOL.md` 与 `PROJECT_STATUS_20261025.md` 中「Claude Code 暂缓接管」已被项目负责人 2026-10-26 的交接指令取代，本次提交在这两处追加了说明，没有删改历史段落。

## 2. 授权边界与禁止事项（沿用交接指令）

本文件的提交范围仅限只读源码审计和研究文档。禁止：下载或遍历新数据、拟合或训练 BPE、训练语言模型、执行 D1/D2/D3、启动 GPU、修改 Parcae/AxoNN、修改递归 Transformer 结构、重复已 CLOSED 实验、清理未知 dirty 文件、覆盖历史日志与 Checkpoint、自动推进下一阶段。架构方向 Prelude → Recurrent Core → Coda 与独立随机权重原则不变。

## 3. D1-01 不可变数据源（FROZEN 规则 / 测量结果留待执行）

### 3.1 数据身份

| 项 | 冻结值 |
|---|---|
| `repo_id` | `Salesforce/wikitext` |
| `config` | `wikitext-2-raw-v1` |
| `revision` | `b08601e04326c79dfdd32d625aee71d232d685c3`（40 位完整 Git SHA，禁止使用 `main`、分支名或短 SHA） |
| splits | `train` / `validation` / `test` |
| 文本字段 | `text`（字符串） |

历史依据：`R1_GATE_F_RESULT.md` 记载，R1 当时把 `main` 解析为该 SHA 并读取 test split。ChatGPT 审核称该修订版的树中有 train/validation/test 三个 Parquet 文件。以上均为二手信息，**本环境无法访问 `huggingface.co` 复核**（见第 9 节）。因此：

- Parquet 的确切文件名与路径：**NOT VERIFIED**。执行时必须先通过 Hub API 列出该修订版 `wikitext-2-raw-v1/` 目录，把实际路径写入 `data_manifest.json`。若与「每个 split 恰好一个 Parquet」的预期不符，状态为 **BLOCKED**，不得自行改选文件。
- 若该修订版无法解析（404、被删除、被重写），状态为 **BLOCKED**，**不得**回退到 `main` 或最新版本。

### 3.2 获取方式（FROZEN）

用 `huggingface_hub` 以显式 `revision=` 下载上述三个 Parquet 文件；用 `pyarrow` 读取。**不使用** `datasets.load_dataset(..., streaming=True)`：它在不同版本里对行顺序和分片的行为不同，会让「行索引」这一身份失去确定性。下载后：

1. 计算每个文件的 SHA-256，同时记录 Hub 返回的该文件 LFS `sha256`（oid）。二者必须一致；不一致为 **FAIL**（来源完整性）。
2. 再把下载目录切到离线读取（`HF_HUB_OFFLINE=1`），确认之后的读取不依赖网络。
3. 下载 README（Dataset Card）并计算 SHA-256，原文保存其 YAML 头里的 `license` 字段。

### 3.3 行与「文档」的定义（FROZEN，属设计选择，请 ChatGPT 重点审核）

- **来源单位 = Parquet 的一行**。来源身份 = `(split, row_index)`，`row_index` 是该 split 内 0 起的物理行号。
- 不使用 R1 的做法（`strip()` 后只保留长度 ≥ 16 的行，再用 `\n\n` 拼接）。该做法会丢失行与行号的对应关系，也改变文本内容。D1 不复用 `r1_prepare_wikitext.py` 的选择逻辑。
- **合格行**：`text.strip() != ""`。只丢弃空白行，保留标题行与短行。被丢弃的行数必须记录。
- 合格行的文本**按存储原样使用**，不做 `strip()`（WikiText 行首空格和行尾 `\n` 是文本的一部分）。
- **文章边界**：满足正则 `^ = (?!=).*(?<!=) = \n$` 的合格行视为一级标题行，即新文章的开始。
- **EOS 规则**：对合格行 `r`，其 Token 序列为  
  `tokens(r) = ([EOS] 若 r 是一级标题行且不是该 split 的第一个合格行，否则 []) + encode(NFC(text_r))`  
  不使用 BOS，不对每一行加 EOS（一行不是一篇文档）。EOS 属于标题行的 Token 前缀，因此行内偏移量足以描述任何位置，不需要额外游标状态。
- 这套边界规则是设计选择，不是 WikiText 官方定义。其在真实数据上是否成立（标题行数量、文章数量）**NOT MEASURED**，由执行时测量并记录，不得事后改规则。

### 3.4 每个 split 必须记录的测量项（执行时填，目前一律 NOT MEASURED）

文件路径、文件大小、文件 SHA-256、Hub LFS oid、总行数、空白行数、合格行数、一级标题行数、合格行 UTF-8 字节数、NFC 后字节数、按冻结 Tokenizer 编码后的 Token 数（对 validation/test 仅计数，见 5.5）、最大 Token ID、是否出现 ID 0。

> 不能把本文件里的任何统计写成已验证。唯一的历史参照是 R1 记载的：test split 前 1200 条合格记录共 591,728 字节、文件 SHA-256 `71450871c67d6f39a0a5a85f8b5eeb7b8022179ff03c8af867e8e92ecc6456a1`——那是 R1 的选择规则下的 `test.txt`，**与 D1 的规则不同，不能拿来对账**。

### 3.5 许可与来源（执行前必须记录，不是已核对结论）

- ChatGPT 审核指出：HF 页面元数据显示 `cc-by-sa-3.0` / `gfdl`，而 Dataset Card 正文又写 CC BY-SA 4.0，措辞不一致。本环境无法复核，保持 **NOT VERIFIED**。
- D1 必须：保存固定修订版 README 原文与哈希；记录 YAML 头许可字段与正文许可/署名要求的原文摘录；在报告中并列写出二者，不自行裁决。
- **ShareAlike 风险（需项目负责人决定）**：BPE 的 `tokenizer.json`（词表与合并规则）由 CC BY-SA 文本导出。本仓库是公开仓库的 fork。把 `tokenizer.json` 提交进 Git 是否构成需要 ShareAlike 的再分发，这是法律问题，本文件**不裁决**。方案：D1 **只提交哈希与统计，不提交 `tokenizer.json` 和任何数据文件**；是否提交 Tokenizer 文件，作为第 11 节的待决事项。

## 4. D1-02 Tokenizer（`ALTERNATIVE RESEARCH TOKENIZER`）

标签：此 Tokenizer 是项目内部的替代研究 Tokenizer，**不是**官方 Parcae Tokenizer，不得称其复现了官方设置。官方 Parcae Tokenizer 的许可与训练资产身份仍为 **BLOCKED**，本方案不依赖它。

### 4.1 冻结配置

| 项 | 冻结值 |
|---|---|
| 库与算法 | Hugging Face `tokenizers` 的 `BPE` 模型 + `BpeTrainer` |
| 字节级 | **ByteLevel BPE**。初始字母表 = `ByteLevel.alphabet()`（256 个字节符号） |
| 规范化 | Unicode **NFC**（`normalizers.NFC()`）。decode 的比较基准是 `NFC(原文)`，不是原文 |
| 预分词 | `pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)` |
| 解码器 | `decoders.ByteLevel()` |
| 目标词表 | **4096（目标值）**。`BpeTrainer(vocab_size=4096, min_frequency=2)` |
| 实际词表 | 拟合后读取 `tokenizer.get_vocab_size()`，**与目标值分开记录**；本文件不预测它 |
| 特殊 Token | 按此顺序加入：`<\|pad\|>` = 0，`<\|bos\|>` = 1，`<\|eos\|>` = 2。ID 由训练器按 `special_tokens` 顺序分配，执行时断言这三个 ID |
| UNK | **不设**。字节级字母表覆盖所有字节，不存在无法表示的输入 |
| 拟合输入 | **仅 train split 的全部合格行**（第 3.3 节规则），按行号顺序，每行 NFC 文本 |
| 并行与随机性 | `TOKENIZERS_PARALLELISM=false`；无显式随机种子（BPE 训练在固定输入顺序下应确定，用第 4.3 节的重复拟合检验，不假设） |
| 依赖版本 | 拟合时精确记录 `tokenizers`、`pyarrow`、`huggingface_hub`、Python 版本；建议的精确固定版本见第 8 节 |

「无法表示的字符」的处理：字节级 BPE 把任意 Unicode 先编码为 UTF-8 字节，再映射到字母表，因此**没有**无法表示的字符，也就没有 UNK。验收时用「全部合格行 round-trip 无差异」来证明这一点，而不是靠断言。

### 4.2 Packing 与 PAD / `ignore_index`

- **跨文档 Packing**：D1/D2 的训练流是把合格行的 Token 序列首尾相接成一条连续流，再切成固定长度块。文章之间只有第 3.3 节的 EOS 分隔，不做 padding。
- **块长**：序列长度 `seq_len = 64`，每块 `65` 个 Token（输入取前 64，标签取后 64，即标签右移一位），块互不重叠，末尾不足一块的部分丢弃并记录丢弃的 Token 数。（`seq_len` 属 D1 数据路径参数，D2 如需调整须另行冻结。）
- **PAD**：D1 的流中**不含 padding**，所以 PAD(0) 不会出现在输入或标签里。验收要求：全部合格行的 Token 中**不出现 ID 0**。
- **PAD 与 `ignore_index` 的区别（源码核对，补充 ChatGPT 的说法）**：
  - 钉住的 Parcae 中，`Parcae._default_objective = {"ignore_index": -100, …}`（`parcae.py:18`），F3-A 以默认值构造，因此 F3-A 用的是 `-100`。
  - 但上游 `scripts/train.py:287` 在训练路径里构造 `objective` 时把 `"ignore_index": tokenizer.pad_id`（`train.py:252-254` 另有 `pad_id is None → 0` 的兜底）。
  - 所以「默认 -100」与「上游训练路径用 PAD id」两种口径都真实存在。D1 因无 padding 而不受影响；**D2 必须显式声明采用哪一种**，并保证真实标签里不会碰巧出现被忽略的 ID。这点建议 ChatGPT 复核。

### 4.3 验收项（Tokenizer 部分）

全部由执行时的测量判定，期望值在此冻结：

| 编号 | 检查 | PASS 条件 |
|---|---|---|
| T1 | train-only 拟合 | 拟合迭代器只绑定 train 合格行；记录喂入行数与拟合语料的 SHA-256；validation/test 的 Parquet 在 `tokenizer.json` 的 SHA-256 写入日志**之前**未被打开（按日志时间戳与顺序核对） |
| T2 | 词表边界 | 特殊 Token ID 为 0/1/2；`259 < 实际词表 ≤ 4096`（即学到了合并规则且没超过目标）。实际值只记录，不预设 |
| T3 | 重复拟合 | 用相同输入再拟合一次，两份 `tokenizer.json` 的 SHA-256 相同。不同则状态 **FAIL**，且不得因此改变其他冻结项 |
| T4 | round-trip | 对 train/validation/test 全部合格行：`decode(encode(NFC(x))) == NFC(x)`，不一致行数为 0 |
| T5 | ID 范围 | 所有 Token ID 在 `[0, 实际词表)` 内，且全体合格行中不含 ID 0 |
| T6 | 文件身份 | 保存 `tokenizer.json`，记录 SHA-256；之后每次读取都先核对该哈希 |

## 5. D1-03 真实数据读取与恢复（单进程 CPU，`num_workers=0`）

### 5.1 范围

只证明**单进程、固定顺序、无 shuffle** 的读取在保存/恢复后与不中断的读取逐块一致。**不证明**多 Worker、14 文件 Parquet 分片、FineWeb 远端行级恢复、`scripts/train.py` 的 DataLoader 恢复；也不能用 R2 的合成 Worker 测试（Gate M–Q）替代这里的真实数据恢复。

### 5.2 冻结参数

| 项 | 冻结值 |
|---|---|
| 模式 | 内存中的 Parquet `text` 列（pyarrow 读取），顺序遍历；无 `streaming`，无多进程 |
| 遍历顺序 | train split 的合格行，按 `row_index` 升序 |
| Shuffle / 随机状态 | **无**。游标里 `rng` 字段固定为 `null`。shuffle 后的恢复属于 **NOT TESTED** |
| 有界窗口 | train split 的**前 2048 个合格行** |
| 块 | `seq_len = 64`、块长 65、不重叠 |
| 中断位置（按已完整输出的块数） | `b1 = 211`，`b2 = 1511` |
| 备用中断点（仅当覆盖条件 C1/C2 未满足时，按此顺序，机械使用，不得自由选择） | `307`, `419`, `523`, `631` |

窗口前置条件（输入性质检查，不满足为 **BLOCKED**，不得调参凑合）：窗口内至少 10 个一级标题行；窗口总块数 ≥ 2000。（预期远高于此，但属 **NOT MEASURED**。）

### 5.3 游标结构（FROZEN）

保存为一个 JSON 文件：

```json
{
  "schema": "d1_cursor_v1",
  "dataset": {"repo_id": "...", "config": "...", "revision": "...", "split": "train",
              "parquet_sha256": "..."},
  "tokenizer_sha256": "...",
  "window_rows": 2048, "seq_len": 64, "block_len": 65,
  "next_eligible_row": 0,      // 下一个要读的合格行序号（窗口内 0 起）
  "source_row_index": 0,       // 对应的 Parquet 物理 row_index
  "row_token_offset": 0,       // 该行 tokens(r) 中已进入流的 Token 数
  "carry": [],                 // 已产出但尚未组成完整块的 Token ID（长度 < 65）
  "emitted_blocks": 0,
  "stream_token_pos": 0,       // 进入流的 Token 总数
  "chain_hash": "...",         // 到 emitted_blocks 为止的块哈希链
  "rng": null
}
```

加载游标时必须做的一致性检查（任何一项不符都抛错，状态 FAIL）：数据集身份与 `parquet_sha256`、`tokenizer_sha256`、窗口参数与冻结值相同；由 `(next_eligible_row, row_token_offset)` 独立重算出的流位置等于 `stream_token_pos`（重算 = 窗口内第 0 到 `next_eligible_row − 1` 个合格行各自 `len(tokens(r))` 之和，加上 `row_token_offset`），并且 `stream_token_pos == emitted_blocks × 65 + len(carry)`（块不重叠、每块 65 个 Token，所以这是确定公式）。这两项由验证器独立复核，不由读取器自证。

### 5.4 两条路径与逐项比较（FROZEN）

- **路径 A（连续）**：从窗口起点一次读完全部块。
- **路径 B（中断恢复）**：读到 `b1` 块后写出游标文件、销毁读取器；用新对象仅凭游标文件恢复，读到 `b2` 块后再保存、销毁、恢复；读完全部块。
- **独立参照（验证器内部，与读取器不共享游标逻辑）**：对窗口内每个合格行单独编码得到 `tokens(r)`，按行序首尾相接成参照流，再按 65 切块。读取器不得被用来生成参照。

每个输出块记录一行：`block_index`、块 Token 的 SHA-256、起止 `(source_row_index, 行内偏移)`、涉及的 `source_row_index` 列表，以及哈希链值 `H_i = SHA256(H_{i-1} ‖ 块哈希)`。同时记录每个来源行的 `(source_row_index, tokens(r) 的 SHA-256, 在各块中贡献的 Token 数)`。

**覆盖条件**（保证恢复点没有恰好落在「容易」的位置）：  
C1：至少一个保存的游标 `row_token_offset > 0`（落在一行中间）；  
C2：至少一个保存的游标 `len(carry) > 0`。  
若 `b1, b2` 不满足，则按 5.2 的备用点顺序追加中断点直到满足；全部用完仍不满足则 **BLOCKED(coverage)**。

### 5.5 PASS 判定（正式，不以进程退出码代替）

D1 的数据读取部分 PASS，当且仅当下列全部成立，并由独立的验证脚本从原始证据文件重新计算得出：

| 编号 | 条件 |
|---|---|
| R1 | A 与 B 的逐块记录序列长度相同，且逐块完全相同（块哈希、起止位置、涉及来源行） |
| R2 | A 与 B 的最终哈希链相同，且都等于独立参照的哈希链 |
| R3 | 每个来源行的 Token 被输出的总数 = `len(tokens(r))`（窗口末尾属于被丢弃的尾部 Token 的行除外，丢弃量单独记录）；没有任何来源行被输出两次，也没有行被漏掉 |
| R4 | 每个游标文件都通过 5.3 的一致性检查 |
| R5 | 覆盖条件 C1、C2 满足 |
| R6 | train 的 Parquet 哈希在窗口读取前后相同；validation/test 在 Tokenizer 固定前未被打开（T1） |
| R7 | validation 与 test 只做「文件哈希、行数、合格行数、Token 计数、round-trip（T4）」；**不**用于拟合 Tokenizer，**不**用于任何模型评估。D3 的最终 test 评估仍是后续一次性事项 |

任何 FAIL 条件不得通过放宽容差、改窗口、改中断点来“修复”；只能记录并停止。

## 6. D1-04 负例与停止标准

负例不训练模型，直接在同一验证器上运行。每个负例的「正确行为」是**验证器检测出预期故障并判 FAIL**；负例本身的结论（meta-PASS）是「检测到了预期的故障码」。程序正常退出**不能**代替这个判断。

| 编号 | 注入 | 预期检测结果 |
|---|---|---|
| N1 跳过 | 从第一个保存的游标恢复时，把 `next_eligible_row` 加 1 且重置 `row_token_offset = 0`，同时重算 `stream_token_pos`，使游标自洽（模拟「读取器悄悄少读一行」） | 验证器输出 `ROW_SKIPPED(split, source_row_index)`；R1、R2、R3 判 FAIL |
| N2 重复 | 从第二个保存的游标恢复时，把 `next_eligible_row` 减 1 且重置 `row_token_offset = 0`，同样重算位置使其自洽 | `ROW_DUPLICATED(split, source_row_index)`；R1、R2、R3 判 FAIL |
| N3a 篡改游标 | 把 `row_token_offset` 加 1，**不**改 `stream_token_pos` | 加载阶段的一致性检查抛 `CURSOR_INCONSISTENT`（对应 R4） |
| N3b 篡改游标（绕过加载检查） | 同 N3a，但临时关闭加载检查，让读取器继续读 | 验证器在块比较里报 `TOKEN_OFFSET_MISMATCH`；R1、R2 判 FAIL |
| N4（附加，可选） | 游标中的 `tokenizer_sha256` 改一位 | 加载抛 `TOKENIZER_HASH_MISMATCH` |
| N5（附加，可选） | 游标中的 `revision` 改为 `main` | 加载抛 `REVISION_MISMATCH` |

必备：N1、N2、N3a、N3b 全部检测到**各自预期的故障码**。N4、N5 若运行则一并记录，不影响必备项。

**无效注入保护**：每个注入后的块序列必须与干净 B 路径至少有一个块哈希不同；否则该负例判 **BLOCKED(invalid injection)**，不得当作通过。

**停止标准**（任一发生即停止，状态按下表写入，不得重试到“成功”）：

| 情形 | 状态 |
|---|---|
| 网络或 Hub 不可达；修订版无法解析；文件路径与预期不符 | BLOCKED |
| 文件 SHA-256 与 Hub 的 LFS oid 不一致 | FAIL |
| 依赖缺失或版本与第 8 节冻结的不符 | BLOCKED |
| 窗口前置条件、覆盖条件不满足 | BLOCKED |
| T1–T6 或 R1–R7 任一不满足 | FAIL |
| 出现 NaN/Inf（D1 不涉及模型，不应出现）、未预期异常、墙钟超时 | FAIL 或 BLOCKED（按原因） |

## 7. 证据保存与验收流程

### 7.1 位置与命名

新建目录 `research/mini_mythos/gate3_d1/`（不在 `.gitignore` 的 `results/*` 与 `*.log` 规则内；日志一律存为 `.txt`）。内容：

| 文件 | 说明 |
|---|---|
| `D1_FROZEN_CONFIG.json` | 本文第 3–6 节所有 FROZEN 数值的机器可读版本；其 Git blob SHA 写入执行日志 |
| `RUN_META.json` | **进程内**读取的 `sys.version`、`sys.executable`、库版本、Git HEAD、`git status --porcelain=v1`、起止时间（不再从命令行字符串推断解释器版本，避免重现 F3-A 的「元数据 3.10.21 vs 命令 3.11」矛盾） |
| `data_manifest.json` | 第 3.4 节各项测量、文件路径、哈希、README 哈希与许可原文摘录 |
| `tokenizer_manifest.json` | 实际词表、特殊 Token ID、`tokenizer.json` SHA-256、重复拟合哈希、T1–T6 结果 |
| `trace_A.jsonl` / `trace_B.jsonl` / `trace_reference.jsonl` | 逐块记录 |
| `cursors/*.json` | 保存的游标 |
| `negatives.json` | N1–N5 的注入内容、预期故障码、实际故障码 |
| `D1_DECISION.json` | **由独立验证脚本**从以上原始文件重新计算后生成的 PASS/FAIL/BLOCKED 与逐项判据 |
| `stdout.txt`、`stderr.txt`、`exit_code.txt`、`SHA256SUMS` | 原始输出与全部文件的哈希 |

数据 Parquet 文件和（待决）`tokenizer.json` 不进入 Git。

### 7.2 两次提交纪律（沿用 F3-A 做法）

1. **冻结提交**：执行脚本（读取器、验证器）与 `D1_FROZEN_CONFIG.json` 先提交，记录其 SHA-256；ChatGPT 审核。
2. **执行提交**：获得项目负责人明确授权后运行，原始证据整体提交，历史证据一律不覆盖。

执行脚本**本次未编写**：本轮只允许文档工作。

## 8. 依赖、环境与 CPU 资源

- **运行环境**：必须是有 `huggingface.co` 访问权限的 CPU 环境（例如项目负责人的 Codespaces）。**本沙箱不满足**：实测 `huggingface.co` 的 CONNECT 被代理以 403 拒绝，`arxiv.org` 与 `together.ai` 的域名解析也失败。PyPI 与 GitHub 可达。
- **建议的精确固定版本（PROPOSED；在执行主机上是否可得 NOT VERIFIED）**：`tokenizers==0.23.3`、`pyarrow==26.0.0`、`huggingface_hub==2.2.0`、`numpy==1.26.4`。这些版本来自 2026-10-22 在本沙箱对 Parcae 依赖的解析与 CI 日志，**不是**在执行主机上验证过的组合；执行前由 ChatGPT 确认或替换，并作为冻结值写入 `D1_FROZEN_CONFIG.json`。D1 本身**不需要** torch。
- **Python**：版本在冻结提交里指定一个具体值，并由进程内 `sys.version` 校验；不符为 BLOCKED。
- **资源（ESTIMATE，未测量）**：单进程、无 GPU；内存预计不超过约 1 GB；磁盘预计不超过约 100 MB（三个 Parquet 加 README 加产物）；Tokenizer 拟合与窗口读取预计数分钟量级；设 **30 分钟墙钟硬上限**，超时按第 6 节处理。下载量与耗时都依赖网络，无法在此预测。
- **成本**：无付费资源。不涉及 GPU，不触发 ¥700/¥5,000 历史上限。

## 9. D2 前置兼容性：词表 128 → 4096（只记录，不修改模型）

### 9.1 事实

- F3-A 的冻结模型（`gate3_cpu_train/f3a_lifecycle.py:48-53`）：`n_embd=64`、`intermediate_size=128`、4 头（`num_key_value_heads=4`）、**`vocab_size=padded_vocab_size=128`**、`block_size=32`、层数 2/2/2、`mean_recurrence=2`；`tie_embeddings` 未设置，沿用 `ParcaeConfig` 默认 **`False`**（`parcae/config.py:34`）。脚本断言总参数 **247,936**。
- 新研究 Tokenizer 的目标词表为 4096。其 Token ID 可达约 4095，会使 `torch.nn.Embedding(128, …)` 越界；输出头的维度也不匹配。**不得**用截断或取模把 4096 压回 128 来维持旧参数量。

### 9.2 与词表大小相关的参数（DERIVED，来自源码阅读，**未实测**）

按 `parcae.py` 的构造（`wte`：第 55 行；`lm_head`：第 99–104 行；`value_embeds`：第 67–73 行；`has_ve`：`mixer.py:18`）：

| 部件 | 形状 | 参数量 |
|---|---|---|
| 输入嵌入 `wte` | `padded_vocab × n_embd` | `V × 64` |
| 输出头 `lm_head`（`tie_embeddings=False` 时独立） | `n_embd × padded_vocab` | `V × 64` |
| `value_embeds`（有效层数 = 2+2+2 = 6，`has_ve(i, 6)` 为奇数 i：1、3、5，共 3 张表） | 每张 `padded_vocab × (kv头数×头维 = 4×16 = 64)` | `3 × V × 64` |
| 合计 | | **`320 × V`** |

- V = 128：40,960。V = 4096：1,310,720。**增量 = 1,269,760**。
- 若新配置令 `tie_embeddings=True`，`lm_head` 与 `wte` 共享，合计变为 `256 × V`，增量降为 1,015,808。是否绑定是 D2 的显式设计决定，不是本文件的。
- **ESTIMATE**：在 `tie_embeddings=False` 的前提下，新配置参数量约 `247,936 + 1,269,760 = 1,517,696`；这只是估算，不是实际值。
- **诚实的对账失败**：我另外按源码手算了整个 F3-A 模型（6 个 Transformer 块、adapter、C、`ln_f`、3 个 `ve_gate` 与上述词表部件），得到 247,104，与脚本断言的 247,936 **相差 832，残差无法解释**。因此上面的分项只能当作估算，且「词表相关参数集合是否完整」**NOT VERIFIED**。832 不是 128 的整数倍，不像是词表相关项漏算，但这是推测，不是证明。
- **D2 的要求**：必须在冻结配置里写明新的 `vocab_size`、`padded_vocab_size`（建议取不小于实际词表的 64 的倍数；`Config.padding_multiple` 默认是 512，需显式覆盖）、是否 `tie_embeddings`、`ignore_index` 口径（见 4.2）；用实例化后的**实测**参数量与新的初始权重哈希取代 247,936；明确这是同一 2/2/2 结构家族的**另一个独立随机初始化模型**，F3-A 的结论不能原样搬过去。
- 新 Tokenizer 的 token 级 PPL 不能与历史字节级 PPL（R1 Gate F：NLL 2.384439 / PPL 10.852968）直接比较。

### 9.3 D3（仅记录）

沿用 ChatGPT 审核的公平协议：同一 Tokenizer、同一训练 Token、同一评估 Token；同训练 Token 与近似同 FLOPs 两个维度分开报告；验证集用于设计，test 只做冻结后的最终一次评估；参数共享不等于节省 FLOPs。本次不展开。

## 10. 风险、BLOCKED 与 NOT VERIFIED 登记

| 项 | 状态 | 说明 |
|---|---|---|
| 固定修订版下三个 Parquet 的路径与文件哈希 | NOT VERIFIED | 本环境无法访问 HF；执行时测量 |
| 数据许可（元数据 vs 正文不一致） | NOT VERIFIED | 执行时保存 README 原文，不自行裁决 |
| `tokenizer.json` 能否进入公开仓库（CC BY-SA 的再分发） | 待负责人决定 | 方案默认不提交该文件 |
| 官方 Parcae Tokenizer | BLOCKED | 许可与资产身份未确认；本方案不依赖 |
| 文章边界规则（一级标题正则）在真实数据上的表现 | NOT MEASURED | 设计选择，请 ChatGPT 审核 |
| 窗口大小、中断块号、备用点 | FROZEN 但属人工选择 | 无统计依据，只保证先于测量；若 ChatGPT 认为覆盖不足可在冻结提交前调整 |
| BPE 拟合的确定性 | 不假设 | 由 T3 重复拟合检验 |
| 实际词表是否等于 4096 | NOT MEASURED | 目标值与实际值分开记录 |
| D2 参数量 | DERIVED/ESTIMATE，且有 832 的对账残差 | D2 必须实测 |
| `ignore_index` 口径 | 已发现双口径 | D2 显式冻结 |
| F3-A 的 `RUN_META` Python 3.10.21 vs `/usr/bin/python3.11` | NOT VERIFIED（沿用） | D1 改为进程内记录 |
| 受保护的 `gate2_1/TEST_RESULTS.json` | UNKNOWN | 不在本环境，未触碰 |
| 多 Worker、14 文件 Parquet 分片、FineWeb 远端行恢复、shuffle 恢复、`scripts/train.py` 数据恢复、MuonAdamW、GPU | NOT TESTED | 不在 D1 范围 |

## 11. 需要 ChatGPT 审核 / 项目负责人决定的事项

**ChatGPT 审核重点**
1. 文章边界与 EOS 规则（3.3）是否可接受，或应改为整个 split 单流、不插 EOS。
2. 窗口 2048 行、块长 65、中断块 211/1511 及备用点是否足够，C1/C2 覆盖条件是否充分。
3. N3 拆成 N3a/N3b 两层是否符合「错位游标」的原意。
4. `ignore_index` 双口径（4.2）的核对。
5. 第 8 节建议的精确依赖版本。
6. 5.3 中 `stream_token_pos` 的两条一致性公式是否足够；N1/N2 的「重算位置使游标自洽」是否是对「悄悄少读/多读一行」的合理模拟。

**项目负责人待决**
1. 是否授权在有 HF 访问权限的环境里执行 D1（含 Tokenizer 拟合——这是 BPE 词表拟合，不是语言模型训练）。
2. `tokenizer.json` 是否可提交进公开仓库（许可风险）。
3. 执行环境：是否使用 Codespaces 并提供 Python 版本。

## 12. 下一条唯一指令

等待 ChatGPT 审核本文件，并由项目负责人明确授权后，才允许：先提交 D1 执行脚本与 `D1_FROZEN_CONFIG.json`（冻结提交），经 ChatGPT 确认，再在有 HF 访问权限的 CPU 环境运行 D1，保存全部原始证据并停在 `PENDING CHATGPT REVIEW`。**在此之前不得下载、拟合、训练或启动 GPU，不得开始 D2/D3。**

---

**最终状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
