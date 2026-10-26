# F3-B / D1 — 执行脚本冻结准备记录（冻结候选，待 ChatGPT 代码复审）

**状态：`D1 CODE FREEZE CANDIDATE / PENDING CHATGPT CODE REVIEW`**

日期：2026-10-26。起草者：Claude Code。分支：`mini-mythos-p1c-gate22c-readiness`。基准 Commit：`8a1700835c619fc1ad579da12713ece612403b8e`（R2 设计所在提交；ChatGPT 对 R2 的复审为静态设计层面 PASS）。

## 0. 边界

- 本阶段只准备：读取器、独立验证器、LR1–LR9 / CR1–CR3 受控负例脚本、`D1_FROZEN_CONFIG.json`、CPU 环境与依赖冻结说明。
- **没有**下载真实 Parquet，**没有**拟合 Tokenizer，**没有**进行 D1 数据实验，**没有**实例化或训练模型，**没有** GPU，**没有**开始 D2/D3。
- 「R2 设计复审 PASS」**不是** D1 实验 PASS。D1 仍为 `NOT TESTED / NOT AUTHORIZED`。
- 代码自测只使用**合成数据**（见第 4 节），其通过**不是** D1 证据。
- 代码在 `research/mini_mythos/gate3_d1/`（v1 第 7.1 节预留的目录），测试在 `research/mini_mythos/tests/test_d1_selftest.py`。文件清单与 SHA-256 见 `gate3_d1/D1_CODE_SHA256SUMS`。

## 1. 五项准备内容与指令要求的对应

| 要求 | 落实 |
|---|---|
| D1 读取器 | `d1_reader.py`：`d1_cursor_v2` 九步固定顺序加载检查；读取循环；`--stop-pos` 精确停在预定流位置并保存游标；`--cursor-in/--cursor-out`；所有输出以 `open(..., 'x')` 写出（write-once） |
| 独立验证器（不共享游标校验、来源映射、参照流构建） | `d1_verifier.py` 自带：`Ref`（参照流、来源映射 `locate/decompose`、块哈希链）、`check_cursor`（九步）、`tile_errors`、调度计算、`cursor_bytes`（正确读取器在某流位置应写出的游标字节）。静态测试断言读取器、验证器、驱动器互不 import；驱动器只经命令行调用二者 |
| LR1–LR9、CR1–CR3 受控负例脚本 | `d1_driver.py negatives`：LR 的单字段改动由驱动器直接编辑 JSON；CR 的注入由读取器 `--inject` 开关实现（在读取循环的读取计划上，且仅在加载检查通过之后）；每个负例写入自己的 `evidence/negatives/<id>/` |
| `D1_FROZEN_CONFIG.json` | 已写；包含数据身份、窗口、调度、负例预期码与步骤、序列化、环境与固定版本 |
| CPU 执行环境及依赖冻结说明 | `gate3_d1/D1_ENV_FREEZE.md`、`requirements-d1.txt`、`d1_env_manifest.py` |

### 1.1 中间 carry 与真正 EOF tail 的区分

- 中途停止的运行，`final.kind = "carry"`，字段为 `carry_ids / carry_segments / carry_len`，**没有** `tail_*` 字段；
- 读到窗口末尾的运行，`final.kind = "eof_tail"`，字段为 `tail_ids / tail_segments / tail_len / tail_sha256`，且要求 `tail_len = T mod 65` 与 `tail_ids = 参照流[65N:T]`；
- 读取器在窗口末尾核对 `流位置 = T` 且 `len(pending) = T − 65⌊T/65⌋`，否则退出码 5；验证器对 `carry` 型 final 要求 `carry_ids = 参照流[65e:pos]`、`pos < T`、不含 `tail_len`，对 `eof_tail` 型要求等于尾部；
- EOF 游标的 `carry` 就是尾部（R1 第 5.2 节），其读取段（B 第 6 段）读取零个块，`tail` 来自恢复的 carry，由验证器按参照位置映射来源行；
- 自测 `test_carry_versus_eof_tail` 逐项断言（含 P3 carry=32、P4 carry 为空且合法）。

### 1.2 来源片段无空洞、无重叠、完全覆盖

- 读取器：`assert_tiles(...)`，在每次干净运行（无注入）结束时核对该次运行的全部片段从起点首尾相接到终点，错误分别报 `SEGMENT_GAP / SEGMENT_OVERLAP / SEGMENT_UNCOVERED / SEGMENT_EMPTY`，失败退出码 5；
- 验证器：独立的 `tile_errors(...)`，对 A 路径整个窗口与 B 路径 6 次运行拼接后的整个窗口各核对一次；另外逐块要求读取器的 `segments` 等于验证器按参照流分解的结果，并逐段用内容核对（`claim_errors`）；
- CR 负例的 trace 按设计**不**满足覆盖（那正是被检出的故障），它们走 R2 第 2.4 节的逐行核算；
- 自测直接对两套实现各构造「空洞 / 重叠 / 未覆盖 / 跳行」，断言都被检出（`test_reader_assert_tiles`、`test_verifier_tile_errors`）。

### 1.3 R2 五项修订在代码中的位置

| R2 项 | 代码 |
|---|---|
| 1 CR 前缀核算 | `verify_cr` / `account` / `classify`：重新验证 `A_trace` 前缀块（哈希、内容、链），合并 carry 归属与续读段，对 2048 行逐行分类；续读 trace 首块号必须等于 `emitted_blocks` 且无历史块；注入与干净证据分目录、clean 目录只读、前后 SHA-256 比对 |
| 2 CR3 合法游标 | 读取器没有关闭加载检查的开关；注入只改读取计划；游标文件前后哈希比较（`evidence_before/after.json` 含该游标） |
| 3 CR3 最小反例 | 配置固定 `delta: 1`；`--inject shift_consume_offset` 固定 +1；调度要求 P2 行 `len ≥ 3` |
| 4 P2 搜索边界 | `build_schedule`：区间 [600,900)，无则 `BLOCKED(schedule)`（驱动器在此停止，不读任何数据）；P3/P4 搜索起点含行起点；升序按实际流位置判定 |
| 5 哈希链下标 | 读取器 `H[j+1] = sha256(H[j] ‖ bh[j])`，验证器独立同式；自测用 R2 第 5 节的合成向量检验两套序列化 |

## 2. 实现阶段新增的、R2 文本没有逐字规定的决定（请 ChatGPT 重点审核）

1. **新增故障码 `DATASET_IDENTITY_MISMATCH`**（第 2 步中 `repo_id/config/split` 不符）。R1 表只列了 `REVISION_MISMATCH / PARQUET_HASH_MISMATCH`。
2. **一级标题正则作用于 NFC 之后的文本**（v1 未写明先后）。标题行是 ASCII，实际无差别，但这是字面决定。
3. **Trace 格式**：`run`（含 `pid`、`start_cursor_sha256`、`carry_len`、`start_stream_pos`、`inject`、`stop_pos`、配置/清单哈希）、`block`（`ids` 全量 + `segments`）、`final`（`kind` 为 `eof_tail / carry / rejected`）。R2 第 2.2 节给出骨架，字段名与 `kind` 分类是实现决定。
4. **`rejected` 型 trace**：加载被拒时，读取器写出只含 `run` 与 `final(kind=rejected)` 的 trace（零个块）并退出码 3，另写 `load_report`（逐步 PASS/FAIL）。
5. **注入的实现位置**：读取器在加载检查通过后修改**读取计划**（`skip_next_row` 删除计划中的第 2 项，`repeat_next_row` 重复第 2 项，`shift_consume_offset` 把首项起点 +1），不改任何游标字段、不改磁盘文件。是否算「读取循环内部」请复核；它与「关闭加载检查」的区别在于所有九步检查都先对**原文件**完整执行并记录 PASS。
6. **验证器额外要求**：B 路径的每个游标文件字节等于验证器自己生成的「正确游标」字节（`cursor_bytes`），B 路径 6 次运行的 `pid` 互不相同，每段的 `start_cursor_sha256` 等于上一段保存的游标文件哈希。
7. **A 路径用作 CR 的可信前缀**（沿用 R2 第 8 节第 3 点的已提复核项）：前缀块在验证器内重新验证，而不是默认可信。
8. **自测模式**：`--mode selftest` 使用 `TOY-BYTE-ENCODER-V1` 标记文件和 `jsonl:` 源，`--mode real` 强制 `parquet:` 源与 `tokenizers` 文件；两种模式的源类型互相禁止。驱动器的决定文件在 selftest 下 `d1_experiment=false`。
9. **字符串形态**：游标以规范 JSON 字节（排序键、`(",",":")`、`ensure_ascii`）为准，非规范字节即 `SCHEMA_INVALID`。
10. **R6 / R7 的覆盖范围**：验证器只核对「运行后源文件哈希等于清单」（R6 的一部分）。validation/test split 的获取、哈希、行数、round-trip（R7）和「validation/test 在 `tokenizer.json` 哈希写入日志之前未被打开」属于**尚未编写**的获取脚本，验证器输出里标注 `NOT_APPLICABLE_THIS_STAGE`。
11. **P1–P5 与块窗口前置条件**（≥10 个一级标题、≥2000 块）在 `schedule` 步骤检查，不满足归入 `BLOCKED(schedule)`（驱动器同样不继续读取）。
12. **Python 版本**：配置允许 3.11/3.12/3.13（v1 要求「指定一个具体值」，执行主机未知，故用允许集合）；是否收紧为单一版本请项目负责人决定。

## 3. 仍未编写 / 未验证（执行 D1 之前的缺口）

- 数据获取脚本（Hub API 列文件、LFS oid 比对、README 哈希、许可摘录）、Tokenizer 拟合脚本及其 T1–T6 验收、validation/test 处理脚本、`runtime_manifest.json` 的生成者：**均未编写**（不在本阶段授权清单内）。
- HF 访问、Parquet 文件名、许可、真实数据的标题行数与块数、P2 区间内是否有 `len ≥ 3` 的行：**NOT MEASURED**。
- `tokenizers` 对输入文本中字面特殊 Token 字符串的识别行为：未测；以「窗口文本中出现次数必须为 0，否则 BLOCKED」的守卫替代。
- 真实 BPE 训练出的 Tokenizer 在 `tokenizers 0.23.3` 下的编码结果：未测；自测只用手工构造、未训练的字节级 BPE 走通代码路径。
- `padding / truncation / post_processor` 属性名：已在准备阶段沙箱（`tokenizers 0.23.3`）中验证存在且默认值为 `None`（API 存在性检查，未拟合）；这纠正了 R1 第 8 节「未实测」的状态，仅限该版本。
- 执行主机的 Python / 库版本、墙钟耗时：**NOT VERIFIED / NOT MEASURED**。

## 4. 代码自测记录（合成数据；不是 D1 证据）

| 项目 | 内容 |
|---|---|
| 环境 | 准备阶段沙箱，Linux 6.18，4 CPU，Python 3.13.16，`tokenizers 0.23.3`，`pyarrow 26.0.0`；无 GPU；无网络访问 |
| 输入 | `d1_selftest_data.py` 生成的合成行（含空白行、一级/二级标题、非 NFC 字符、2048 个合格行，约 15.7 万 Token / 2409 块 / `tail_len=20`、41 个一级标题）；`variant=no_p2_row` 用于 BLOCKED 用例 |
| 预期 | clean A/B 全部判据 PASS；LR1–LR9、CR1–CR3 各自 meta-PASS；对验证器的 10 项篡改/反向用例全部得到预期的 FAIL 或 BLOCKED；P2 无候选行 → `BLOCKED(schedule)` 且不读任何数据；carry 与 EOF tail 区分正确；覆盖断言能抓空洞/重叠/未覆盖/跳行；链向量与 R2 第 5 节一致；读取器/验证器/驱动器互不 import、只依赖标准库与 pyarrow/tokenizers、无 torch/GPU 字样 |
| 实际 | `python -m unittest research/mini_mythos/tests/test_d1_selftest.py`：24 项，OK（约 49 s）；在固定版本 venv（`tokenizers 0.23.3`、`pyarrow 26.0.0`）中同样 24 项 OK，其中包含 `--mode real`（合成 Parquet + 手工构造、未训练的字节级 BPE）的完整流水线 |
| 状态 | 代码自测 PASS（仅表示代码在合成输入上行为符合设计）。D1 实验：**NOT TESTED / NOT AUTHORIZED** |

自测的第一次运行里，BLOCKED 用例**失败过一次**：我的合成变体保留了标题行，标题行满足 `len ≥ 3`，所以 P2 规则找到了候选行。这是测试数据的错误而不是代码缺陷，已把变体改为区间内所有行都不超过 2 个 Token 后通过。

## 5. Git 审计与检查点

提交前后的 Git 状态、diff 文件清单、历史文件 SHA-256（v1 `a55b2cb7…ba9e`、R1 `f92c4e79…1d7a`、R2 `1d4c3629…05d9`）不变性，在最终报告和提交说明里给出。三个索引文件只追加。

## 6. 需要 ChatGPT 复审的重点

1. 第 2 节 12 条实现决定，尤其第 1、5、6、10 条。
2. 读取器 `validate_cursor` 与验证器 `check_cursor` 两套实现的步骤顺序是否都与 R1 第 5.2 节一致（两套独立实现，请独立对照）。
3. `verify_cr` / `account` / `classify` 是否满足 R2 第 2.4 节「整窗口、逐行、不依赖续读 trace 内零计数」。
4. 注入以「读取计划修改」实现是否可接受。
5. 缺口清单（第 3 节）是否应在冻结提交前补齐，还是作为执行前的下一道独立准备。

## 7. 下一条唯一指令

等待 ChatGPT 对本冻结候选（`gate3_d1/` 全部文件与 `tests/test_d1_selftest.py`）复审。通过且项目负责人明确授权后，才可编写/审核获取与 Tokenizer 拟合脚本并做冻结提交；**在此之前不得下载、拟合、运行 D1、训练或使用 GPU，不得开始 D2/D3。**

---

**最终状态：`D1 CODE FREEZE CANDIDATE / PENDING CHATGPT CODE REVIEW`。** 未宣布 D1 PASS 或 CLOSED。
