# E2-c 阶段 2 模拟实现 I2：驱动程序、启动器接口与合成测试

- 日期：2026-10-21
- 研究基线：`f7a0ffe867b55a0087731a2b29fe5fbd8487b3fa`（阶段 1 已最终验收）
- 本轮性质：只做实现和纯合成测试，不是正式阶段 2。
  - 没有执行正式 verify，也没有执行正式 freeze；
  - 没有枚举真实键空间，没有运行 33 个真实训练流；
  - 没有生成 test2，没有接触任何盐值，没有写正式冻结文件；
  - 没有训练或评测任何模型，没有进入阶段 3、4。
- **结论**：
  - V4 故障注入测试：50/50 通过（原有 41 项加 I2 新增 9 项）。
  - 阶段 2 合成测试：36/36 通过。
  - 两套测试各正式运行一次；正式运行之前各做过一次开发运行（第 4.4 节），开发运行也全部通过。

**关于裁决文件**：《E2-c 阶段 2 设计裁决与实现接口 v1》没有随任务提供，仓库和容器里也找不到。本实现按任务消息中列出的裁决要点实施（第 1 节），没有改变预注册或正式研究规则。

## 1. 裁决要点的落实

| 裁决 | 实现 | 位置 |
|---|---|---|
| B1 代码级跨阶段冻结核对 | 阶段 3、4 的每次启动都必须带 `--approved-stage2-commit C --approved-freeze-sha256 S`，两项都来自审核，不从工作区的任何文件读取。`git_anchor` 依次核对：<br>· 冻结文件的 sha256 等于 S；<br>· C 存在，并且是 HEAD 的祖先；<br>· C 中该文件的 blob 等于 S；<br>· 该文件在历史中只被 C 改动过一次（只写一次）；<br>· 工作区与提交一致；<br>· 仓库不是浅克隆。<br>阶段 3 首次启动把 C、S 绑定进 `run_freeze.json`。续跑要求 C、S 不变。阶段 4 要求 C、S 以及冻结文件的 sha256 都与阶段 3 绑定的一致 | `run_e2c.py`：`git_anchor`、`main` |
| 不信任同一工作区的冻结文件和 sidecar | 冻结回执 `stage2_freeze_receipt.json` 写明它不被启动器信任。测试把冻结文件和回执一起改成相互一致，或改完再提交一次，启动器都拒绝 | V4 `freeze_and_sidecar_replaced`；阶段 2 `freeze_replaced_refused_by_launcher` |
| B2 完整的 H、U、R_star、M1_star 计数结构 | `keyspace_format_problem`：<br>· 只能有 `R_star_sha256`、`M1_star_sha256`、`counts` 三个字段，两个哈希都是 64 位十六进制；<br>· `counts` 恰好是四个整数。<br>`check_baseline` 还要求四个计数等于附录 A 的 12006 / 5093 / 6913 / 4129。<br>冻结文件中的这一项直接取自阶段 4 自己的 keyspace 作业（`e2c_stage4.py keyspace`）的输出，所以与阶段 4 重算后的比较格式相同 | `run_e2c.py`；`e2c_stage2.py verify` |
| B3 只接受盐值承诺 | `freeze` 只有 `--salt-commitment-sha256` 一个参数。<br>· 关闭了参数缩写，`--salt`、`--salt-file`、`--salt-commitment` 都被解析器拒绝；<br>· 承诺必须是 64 位小写十六进制，并且不能是空行的哈希；<br>· `check_baseline` 对冻结文件做同样的检查 | `e2c_stage2.py`；`run_e2c.commitment_problem` |
| F11 含义不变 | F11 只表示键空间计数与附录 A 不一致，有两种情形：<br>· 阶段 4 keyspace 作业给出的四个计数与附录 A 不同；<br>· 从预注册逐字节复原的附录 A 脚本（sha256 `dfa649e3…`），输出与附录 A 不逐字相同。<br>处理：退出码 3，状态 `F11`，不冻结 | `cmd_verify` |
| V2 失败单独按完整性失败记录 | 以下任何一项都记为 `INTEGRITY_FAILURE_V2`（退出码 3，不是 F11），不冻结：<br>· 训练流中出现留出键；<br>· 接受样本数不等于 12000 × 64；<br>· 训练流与阶段 1 提交的批次链不一致；<br>· E1 的非 U 题集中出现留出键；<br>· 种子表不是那 33 个 | `v2_check` |
| verify 与 freeze 分开授权 | 真实运行必须同时满足：<br>· 环境变量 `E2C_STAGE2_AUTHORIZED` 等于对应命令名；<br>· 带 `--authorization` 文本。<br>verify 的授权不能用于 freeze，反过来也不行。<br>freeze 还要求审核批准的 verify 记录（提交号和 sha256 走命令行，并按 B1 的方式锚定在 git 中） | `env_checks`；`cmd_freeze` |

## 2. 新增和修改的文件

逐文件的 sha256 见 `sha256_files.txt`，完整代码差异见 `code_diff_vs_f7a0ffe.patch`。

| 文件 | 状态 | f7a0ffe 的 sha256 | 本轮的 sha256 |
|---|---|---|---|
| `e2c_stage2.py` | 新增 | — | `bcaffd6f…` |
| `e2c_stage2_tests.py` | 新增 | — | `86e3f518…` |
| `run_e2c.py` | 最小修改 | `aa9d9983…` | `33711975…` |
| `e2c_launcher_tests.py` | 最小修改 | `62272f89…` | `f8106be2…` |

**`run_e2c.py` 的修改**（只改了下面几处，阶段 3、4 的业务逻辑没有改动）：
- 文档字符串；
- `KEYSPACE_COUNTS`、`HEX64` / `HEX40`、`EMPTY_LINE_HASHES` 三组常量；
- `check_baseline` 中盐值承诺和 R* / M1* 的两项检查；
- 新增 `commitment_problem`、`keyspace_format_problem`、`git_anchor`；
- 新增 `training_stream_seeds()`，阶段 4 原来写在行内的种子表达式改为调用它，行为不变；
- `main` 新增两个审核参数，以及跨阶段的核对。

**`e2c_launcher_tests.py` 的修改**：
- 每个测试目录现在是一个 git 仓库，它的首个提交加入冻结文件，作为模拟的已批准提交；
- 每次启动都带上审核参数；
- `--out` 不变，原有 41 项的断言不变；
- 新增 9 项 I2 用例（第 4.1 节）。

**审计材料**：`impl_i2/` 目录下的各文件，见第 4.4 节和第 6 节。

## 3. 接口

```
e2c_stage2.py verify --expected-commit X --authorization T [--resume]      需要 E2C_STAGE2_AUTHORIZED=verify
e2c_stage2.py freeze --expected-commit V --approved-verify-commit V --approved-verify-sha256 S_V
                     --salt-commitment-sha256 C --authorization T          需要 E2C_STAGE2_AUTHORIZED=freeze
e2c_stage2.py check  [--approved-verify-commit V --approved-verify-sha256 S_V]
                     [--approved-freeze-commit Y --approved-freeze-sha256 F]   只读，不需要授权
run_e2c.py --stage 3 --approved-stage2-commit Y --approved-freeze-sha256 F [--resume]
run_e2c.py --stage 4 --salt-file 盐值文件 --approved-stage2-commit Y --approved-freeze-sha256 F [--resume]
```

### 3.1 verify 的顺序

每一步失败都立即停止。

1. **授权与环境**（退出码 5）：出现任何测试变量或 `E2C_KEYSPACE_STAGE` 都拒绝。这一步在读写任何文件之前。
2. **预算账本开区间**：这一步是为了把被拒绝的启动也记入账本。
   - 预算按区间并集计算，上限 3600 秒，verify 与 freeze 共用，永不重置；
   - 账本有 fcntl 锁，并用"进程号 + 进程启动时间"判断写区间的进程是否还在；
   - 进程已不在的遗留区间按最后一次心跳关闭，并标为 stale。
3. **启动前核对**（退出码 5，此时还不建立尝试目录）：
   - HEAD 等于 `--expected-commit`；
   - `stage2/` 以外的工作区干净；
   - 相对 f7a0ffe 的代码改动恰好就是允许的 4 个文件；
   - 预注册 `434f5869…`、设计审核记录 `96f0df48…` 不变；
   - λ / λ₂ 文件 `6c23606e…`、校准记录 `a2301dc7…` 不变，两者中的 λ 值一致；
   - 环境与 `stage1/environment.json` 一致；
   - 60 个阶段 1 批次链记录的摘要等于 `22017d1b…`。
4. **E1 题集**（退出码 5）：
   - E1 的 4 个冻结锚点都等于 `d22fcdab…`；
   - 自 4b33c86 以来没有改动，也没有未提交的修改；
   - 题集目录的内容恰好与清单一致；
   - 13 个文件的 sha256 和行数都与清单一致；
   - K=2 题集恰好是那 8 个。
5. **附录 A**：
   - 脚本从预注册原文逐字节复原，sha256 `dfa649e3…`；预期输出的 sha256 为 `3b58fb66…`；
   - 用 `python3 -I` 在临时目录中运行脚本，输出不逐字相同即 F11。
6. **键空间**：
   - 运行 `e2c_stage4.py keyspace`，只在这个子进程的环境里设置 `E2C_KEYSPACE_STAGE=2`；
   - 输出格式不对：完整性失败；计数与附录 A 不同：F11。
7. **键规则**：在全部键的两种语句顺序上，`e2c_test2.key` / `held` 与 E1 的 `body_key` / `is_heldout` 一致；字母表与附录 A 相同；总数 119,340；留出键数等于 H。不一致按完整性失败处理。
8. **V2**：
   - 33 个种子分给 4 个工作进程，每个种子取 12000 × 64 个接受样本，用 E1 的生成器，并按 `train_e2c.py` 的批次链定义计算哈希；
   - 训练流与 60 个阶段 1 记录逐点比对；
   - 再加上非 U 题集中的留出键计数。
9. **收尾核对**：
   - 再核对一次 E1 题集，运行中有变化按完整性失败处理；
   - 代码树和冻结文档与启动时相同；
   - 与此前各次尝试的输出逐字节比对，不一致按完整性失败处理；
   - 泄漏扫描：所有输出中不得出现"字母=数字;字母=数字"形式的文本。
10. **只写一次的输出**：`stage2/v2_streams.json`，然后是 `stage2/stage2_verify.json`。
    - 写法是临时文件、fsync、`os.link`（目标已存在就失败），然后删除临时文件；
    - 退出码 3 时另写 `verify_stop.json`，之后的 verify 一律拒绝，等待审核决定。

### 3.2 退出码

| 退出码 | 含义 |
|---|---|
| 0 | 通过 |
| 3 | F11、V2 完整性失败或其他完整性失败 |
| 4 | 其他错误 |
| 5 | 拒绝 |
| 6 | 应有的输出缺失 |
| 7 | 阶段 2 累计 1 小时上限（F9） |
| 130 | 中断，用 `--resume` 续跑 |

### 3.3 freeze

执行顺序：
1. 冻结文件或回执已存在：拒绝。
2. 核对 verify 记录的锚定；记录状态为 PASS；`v2_streams.json` 的 sha256 与记录一致。
3. 核对盐值承诺的格式。
4. 启动前核对；代码树和冻结文档与 verify 时相同；E1 题集与 verify 时相同。
5. 用 `run_e2c.make_baseline` 生成冻结内容，λ、λ₂ 逐位取自 `lambda_selected.json`。
6. 追加 `stage2` 块：verify 记录的 sha256 和提交号、V2 训练流的 sha256、33 个种子、E1 逐文件的 sha256、环境。
7. 用启动器自己的 `check_baseline` 核对生成的内容，结果必须为空。
8. 只写一次地写出冻结文件，再写回执。

冻结文件内容确定，不含时间戳；回执中有时间。

## 4. 测试矩阵与结果

两套测试都只用桩作业和合成数据：
- 合成题面只用不是字母的符号 `#$%&*+<>@^`，所以不会出现任何真实键；
- 阶段 2 测试中，V2 用 33 个种子，每个种子 3 次更新 × 4 个样本，训练流是合成的。

### 4.1 V4（`e2c_launcher_tests.py`）：正式运行 50/50

- 运行时间：01:36:47–01:46:37 UTC，各用例合计 579.8 秒。
- 结果文件：`launcher_tests_i2.json`，sha256 `33128676…`。
- 原有 41 项全部通过：38 项启动器测试，加上键空间保护和合成 test2 两项。
- 新增 9 项：

| 用例 | 注入 | 期望 | 结果 |
|---|---|---|---|
| `approvals_missing` | 不带审核参数；参数为空 | 5，没有启动任何作业 | PASS |
| `freeze_replaced_unapproved` | 换成另一份内容有效、但未经批准的冻结文件 | 5 | PASS |
| `freeze_and_sidecar_replaced` | 改冻结文件后再提交，记录的审核值也改成与之一致；另一次用原审核值 | 两次都是 5 | PASS |
| `approved_commit_without_freeze` | 批准的提交并没有加入冻结文件 | 5 | PASS |
| `stage4_freeze_rebound` | 阶段 3 完成后，换成另一份冻结文件和另一组审核值（各自都有效） | 阶段 4 为 5，没有启动 keyspace 和 judge | PASS |
| `resume_with_other_approvals` | 冻结内容相同，但换了提交 | 续跑为 5 | PASS |
| `keyspace_counts_structure` | 计数只有两项；H 差 1；U 写成浮点数；多一个字段 | 四种都是 5 | PASS |
| `salt_commitment_malformed` | 大写；63 位；非十六进制；sha256("")；sha256("\n")；盐值本身 | 六种都是 5 | PASS |
| `shallow_clone_refused` | 深度为 1 的浅克隆 | 5（"shallow"） | PASS |

### 4.2 阶段 2（`e2c_stage2_tests.py`）：正式运行 36/36

- 运行时间：01:46:41–01:55:18 UTC，共 516.7 秒，89 次程序调用。
- 结果文件：`stage2_tests_i2.json`。

| 类别 | 用例与结果 |
|---|---|
| 正常路径 | `verify_pass`：<br>· 退出码 0；33 个种子；12 个阶段 1 链点一致；<br>· keyspace 桩只看到 `E2C_S2_STUB_KEYSPACE_STAGE`，没有 `E2C_KEYSPACE_STAGE`。<br>`verify_deterministic`：两份副本得到的记录和训练流文件都逐字节相同。<br>`freeze_pass_launcher_accepts`：check 0，阶段 3 退出码 0，阶段 4 退出码 0（启动器使用桩作业），`run_freeze.json` 绑定了审核值 |
| B1 冻结只写一次 | `freeze_replaced_refused_by_launcher`：三次都是 5，包括冻结文件和回执被同时篡改。<br>`freeze_written_once`：第二次 freeze 为 5，两个文件的 sha 都不变。<br>`freeze_needs_approved_record`：记录未提交、sha 错误、提交不对、记录提交后又被改动，四种都是 5，冻结文件不存在。<br>`freeze_code_changed_since_verify`：5 |
| B3 | `freeze_commitment_only`：<br>· 7 种格式错误的承诺都是 5，包括 48 位十六进制和盐值本身；<br>· 3 种盐值参数被解析器拒绝（退出码 2）；<br>· 合法承诺为 0 |
| F11 与 B2 | `f11_counts`：H、U、R_star、M1_star 各差 1，都得到 3 / F11，没有写记录，没有启动 V2，之后的 verify 为 5。<br>`f11_appendix_output`：3 / F11。<br>`keyspace_record_format`：三种格式错误都是 3 / `INTEGRITY_FAILURE`，不是 F11。<br>`prereg_changed`：5，没有建立尝试目录 |
| E1 题集 | `e1_sets_mismatch`：改一个字节、多一个文件、锚点不符、有未提交修改，四种都是 5，没有建立尝试目录。<br>`e1_set_changed_during_run`：3 |
| V2（完整性失败，不是 F11） | `v2_heldout_in_stream`：种子 205 注入一个留出键，3 / `INTEGRITY_FAILURE_V2`。<br>`v2_reference_chain_mismatch`：3 / V2。<br>`v2_reference_files_changed`：5。<br>`v2_non_u_set_heldout`：3 / V2。<br>`v2_missing_seed`：6。<br>`v2_seed_table`：33 个种子，等于 `run_e2c.training_stream_seeds()` |
| 中断、恢复与预算 | `interrupt_and_resume`：130 后续跑为 0，账本区间为 INTERRUPTED、PASS。<br>`resume_nondeterministic`：3（"differs from attempt 01"）。<br>`crash_then_resume`：模拟崩溃退出码 9，续跑为 0，遗留区间被标为 stale。<br>`budget_cap`：上限 1 秒，两次启动都是 7，用量 1.186 秒，两次启动都记入账本。<br>`stale_interval`：已死进程的区间被关闭；进程仍存活时为 5 |
| 启动状态、git 与输入 | `launch_state`：已有尝试却首次启动、续跑时没有尝试、通过之后再启动，均为 5。<br>`git_state`：HEAD 不对、工作区不干净、不允许的代码改动，均为 5；允许的改动为 0。<br>`inputs_mismatch`：环境、λ 文件、校准文件不符，均为 5。<br>`key_rules_mismatch`：3 |
| 泄漏与 checkpoint | `leak_scan_hit`：3。<br>`checkpoint_access_blocked`：3，`x.pt` 没有被创建 |
| 真实入口与单元测试 | `real_entry_refuses`：7 种真实模式调用都是 5（第 5 节）。<br>`unit_write_once`：6 个进程竞争写同一文件，只有 1 个成功，没有遗留临时文件。<br>`unit_appendix_a`：附录 A 脚本复原正确，篡改过的副本为 5。<br>`unit_tripwires`：保护、三个绊线、审计钩子都起作用。<br>`unit_chain_definition`：静态核对，`train_e2c.py` 与 `stream_check` 中训练流和批次链的代码行相同 |

### 4.3 静态检查（`static_checks.txt`）

- 4 个文件都能用 `py_compile` 编译。
- pyflakes 4.0.3：这次装在会话的临时目录里，没有装进仓库。阶段 1 时环境里没有这个工具。
  - 新增的两个文件和 `run_e2c.py`：0 个警告；
  - `e2c_launcher_tests.py`：1 个警告（变量 `dn` 未使用），在已验收的 f7a0ffe 版本中就有，本轮没有改动。

### 4.4 实际执行次数

| 运行 | 次数 | 结果 | 记录 |
|---|---|---|---|
| V4 开发运行（8 个用例：`all_succeed`、`lambda2_missing`、`freeze_changed_before_resume`，以及 5 个新用例） | 1 | 8/8 | `dev/v4_dev_cases.txt` |
| 阶段 2 开发运行（全部 36 项，89 次调用） | 1 | 36/36 | `dev/stage2_tests_dev1.*` |
| V4 正式运行（50 项） | 1 | 50/50 | `launcher_tests_i2.json` |
| 阶段 2 正式运行（36 项，89 次调用） | 1 | 36/36 | `stage2_tests_i2.json` |
| 只读的输入就绪检查（进程内） | 1 | 通过 | 本报告第 5 节 |

- 两次开发运行的代码与正式运行完全相同：开发结果中记录的 4 个 sha256 与正式运行前记录的一致。
- **只读输入就绪检查**的内容：
  - 60 个阶段 1 记录的摘要等于 `22017d1b…`；
  - E1 锚点、清单和 13 个文件的哈希与行数都没有问题；
  - 环境一致；
  - `stage2/` 和正式冻结文件都不存在。
  - 这次检查只读哈希和行数，没有计算任何键，没有抽取任何训练流。
- **预算**：这些都是合成运行，没有计入任何阶段的账本。阶段 1 的账本已经在 13,564.2 秒关闭；阶段 2 的账本由正式 verify 首次创建。是否把本轮约 30 分钟的测试时间记为阶段 2 的补计，由审核决定。

## 5. 阶段 2 真实入口未执行的证据

1. `experiments/gate_e/e2c/stage2/` 和 `e2c_workload_freeze.json` 在提交前都不存在，`real_entry_refuses` 测试运行前后也都不存在。所有测试输出都在 `/tmp` 下的临时目录中。
2. 在真实模式（不设 `E2C_S2_TEST_DIR`）下调用了 7 次，全部在读写任何文件之前以退出码 5 拒绝：
   - 没有授权的 verify；
   - 只有 `--authorization` 文本、没有授权变量的 verify；
   - freeze；
   - V2 工作进程；
   - 真实模式下出现 `E2C_TEST_DIR`；
   - 设置了 `E2C_KEYSPACE_STAGE=0`；
   - 测试模式下带授权变量。
3. 本轮从未设置 `E2C_KEYSPACE_STAGE=2`，也从未设置任何 `E2C_STAGE2_AUTHORIZED`。
   - 测试程序在这两个变量存在时拒绝启动；
   - keyspace 桩记录了它收到的环境，其中只有 `E2C_S2_STUB_KEYSPACE_STAGE`；
   - 没有授权时，`e2c_test2.keyspace()` 仍然拒绝运行（`unit_tripwires` 中的 guard 项）。
4. 测试模式下，`e2c_test2` 的 `keyspace`、`training_stream_keys` 和 `generate` 都被替换为绊线，调用即报错。全部 36 项通过，说明这些函数一次也没有被调用。
5. 打开 checkpoint 会被审计钩子拦截，`checkpoint_access_blocked` 验证了这一点。本轮没有打开任何 checkpoint。
6. V4 中沿用的 `synthetic_generation`（阶段 1 已验收的用例，没有改动）只用字母 a–j 的非留出键，这些键都不在 R* 中。它直接调用 `generate()`，不调用 `keyspace()`。

## 6. 阶段 1 文件未改动的证明

见 `untouched_proof.txt`，内容是暂存后用 git 生成的输出。
- 相对 f7a0ffe 的改动只有：
  - `run_e2c.py`（M）、`e2c_launcher_tests.py`（M）、`e2c_stage2.py`（A）、`e2c_stage2_tests.py`（A）；
  - `impl_i2/` 下的新文件。
- 以下各项相对 f7a0ffe 都没有差异：
  - `stage1/` 整个目录、预注册、`DESIGN_REVIEW.md`；
  - E1（`experiments/gate_e/` 中除 `e2c/` 以外的全部内容）；
  - `open_mythos/`。
- `STAGE1_FINAL_AUDIT.json` 的 `code_final` 列出 33 个代码文件。其中 31 个的 sha256 与列表相同；另外 2 个就是经批准修改的 `run_e2c.py` 和 `e2c_launcher_tests.py`。
- V4 第一次运行的 F3 失败记录和修复记录都保持原样，本轮的 V4 结果写入新文件 `impl_i2/launcher_tests_i2.json`：
  - `stage1/v4/launcher_tests.json`（`8bbea5e4…`）；
  - `launcher_tests_dev_run_1037_1049.json`（`32c3f1fb…`）；
  - `f3_evidence/`；
  - `launcher_tests_remediation_01.json`（`caf05c49…`）；
  - `remediation_01/`。
- λ / λ₂：`stage1/gate4/lambda_selected.json` 仍为 `6c23606e…`。

## 7. 新发现的设计问题（需要裁决）与剩余风险

### 7.1 需要在正式 verify 或冻结之前裁决

1. **盐值的长度会与承诺混淆**：
   - 我在设计复核中建议用 `secrets.token_hex(32)` 生成盐值，但它也是 64 位十六进制，形状与承诺完全相同。
   - 后果：如果误把盐值当作承诺传入，B3 的格式检查无法识别。
   - **更正建议**：盐值改用 `secrets.token_hex(24)`，即 48 位十六进制、192 位，仍满足预注册"至少 128 位"的要求。这样误传的盐值会因长度不对被拒绝，`freeze_commitment_only` 已经验证了 48 位会被拒绝。
   - 是否在阶段 4 用代码强制"盐值是至少 32 位、且不是 64 位的小写十六进制"，需要裁决。这一项不在 v1 的要点之内，本轮没有实现。
2. **阶段 4 仍不检查盐值的长度和格式**：同上，需要在冻结之前决定是否加入。冻结之后代码就不能再改。
3. **冻结后不能再新增代码**：
   - 运行后核验脚本和报告脚本还没有写。冻结之后，代码树范围内新增任何 `.py` 文件，阶段 3、4 的每次启动都会被拒绝。
   - `ALLOWED_CODE_CHANGES` 写死了 I2 的 4 个文件。在正式 verify 之前，任何别的代码改动都要同时更新这个常量，也就是又一次代码修改和审核。
4. **停止标记之后的处理方式**：出现 `verify_stop.json` 后，按预注册由审核决定。但如果审核允许重新验证，执行机制（换输出目录，还是登记一次人工处理）需要事先规定。
5. **驱动自己也枚举键空间 H**：键规则核对在 `e2c_stage2.py` 进程内枚举全部 119,340 个键，只输出计数，不涉及 R* / M1*。按预注册"只有阶段 2 的哈希脚本可以枚举"的规定，需要确认 `e2c_stage2.py` 本身算作阶段 2 的哈希脚本。

### 7.2 剩余风险

1. **真实路径只用桩测试过**：以下四条路径都没有真实执行过：
   - 用真实题集运行附录 A 脚本；
   - 在 `E2C_KEYSPACE_STAGE=2` 下运行 `e2c_stage4.py keyspace`；
   - 52 个字母的键规则核对；
   - 用 `encode_rows` 抽取真实训练流。
   批次链定义的一致性目前只有源码行级别的静态核对。正式 verify 会用 60 个阶段 1 记录（种子 1–5、91–93、99）做动态核对。
2. **V2 的真实耗时没有实测**：总计 33 × 768,000 = 25,344,000 个接受样本，另有约 11% 的拒绝重抽，由 4 个进程执行。
   - 估计 5–20 分钟，这只是推算，没有测过。
   - 上限是 1 小时，并且包括 verify、freeze 和所有重启。
3. **仓库不能是浅克隆**：`git_anchor` 要求完整克隆。当前克隆是完整的（232 个提交）。如果以后的容器是浅克隆，需要先运行 `git fetch --unshallow`。
4. **环境核对很严**：要求 `sys.version` 字符串完全相同。重建的容器即使 Python 版本相同，只要编译信息不同也会被拒绝。这是保守的做法。
5. **泄漏扫描的范围有限**：只识别"字母=数字;字母=数字"这一种形式。驱动本身不写键列表，扫描只是兜底。
6. **启动器的阶段 3、4 真实路径**（真实训练、LFS、真实 test2）仍然只经过桩测试，这与阶段 1 时相同。
7. **只读命令不计时**：`check` 命令是只读的，没有记入预算账本。

## 8. 下一轮真实验证的命令草案（本轮没有运行）

`<X>` 是审核通过的 I2 提交（本报告所在的提交）。

### 0. 启动前只读核对

```
cd /home/user/OpenMythos && git fetch origin claude/openmythos-research
git status --porcelain                        # 应为空
git rev-parse HEAD                            # 应为 <X>
git rev-parse --is-shallow-repository         # 应为 false
env | grep -E '^(E2C_|STUB_)'                 # 应为空
ls experiments/gate_e/e2c/stage2 experiments/gate_e/e2c/e2c_workload_freeze.json   # 都应不存在
```

### 1. verify（需要单独的阶段 2 verify 授权）

```
E2C_STAGE2_AUTHORIZED=verify setsid nohup python3 experiments/gate_e/e2c/e2c_stage2.py verify \
    --expected-commit <X> --authorization "<verify 授权文本与日期>" \
    > /tmp/e2c_stage2_verify_console.txt 2>&1 < /dev/null &
# 进度：experiments/gate_e/e2c/stage2/attempts/01/driver_log.txt；预算：stage2/budget_ledger_s2.json
# 中断（退出码 130）或容器重启之后：同一命令加 --resume
python3 experiments/gate_e/e2c/e2c_stage2.py check
sha256sum experiments/gate_e/e2c/stage2/stage2_verify.json        # 即 <S_V>
git add experiments/gate_e/e2c/stage2 && git commit -m "gate_e/e2c: stage 2 verify record" \
    && git push -u origin claude/openmythos-research               # 即 <V>
```

完成后停止，等待审核。

### 2. 审核方生成盐值（在审核方自己的机器上，不在本容器中，也不贴进对话）

```
python3 -c "import secrets; open('e2c_salt.txt', 'w').write(secrets.token_hex(24))"
python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1]).read().strip().encode()).hexdigest())' e2c_salt.txt
# 输出即承诺 <C>，读取方式与阶段 4 完全相同
```

### 3. freeze（需要单独的 freeze 授权，<V>、<S_V>、<C> 由审核提供）

```
E2C_STAGE2_AUTHORIZED=freeze python3 experiments/gate_e/e2c/e2c_stage2.py freeze \
    --expected-commit <V> --approved-verify-commit <V> --approved-verify-sha256 <S_V> \
    --salt-commitment-sha256 <C> --authorization "<freeze 授权文本与日期>"
git add experiments/gate_e/e2c/e2c_workload_freeze.json experiments/gate_e/e2c/stage2 \
    && git commit -m "gate_e/e2c: stage 2 freeze" && git push -u origin claude/openmythos-research   # 即 <Y>
python3 experiments/gate_e/e2c/e2c_stage2.py check --approved-verify-commit <V> --approved-verify-sha256 <S_V> \
    --approved-freeze-commit <Y> --approved-freeze-sha256 <F>
```

完成后停止，等待审核。

### 4. 阶段 3（以后，需要单独授权）

```
python3 experiments/gate_e/e2c/run_e2c.py --stage 3 --approved-stage2-commit <Y> --approved-freeze-sha256 <F>
```

本报告提交后暂停，等待对 I2 的审核。
