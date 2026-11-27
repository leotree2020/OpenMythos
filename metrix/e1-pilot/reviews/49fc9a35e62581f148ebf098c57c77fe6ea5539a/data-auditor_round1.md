# data-auditor, C2 fix commit, round 1 (staged tree b40224e68d1d42f9b4dc886fe9e159f9d99162b1, parent 1900b1fe; committed as 49fc9a35e62581f148ebf098c57c77fe6ea5539a)
# invocation text: data-auditor_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py; trust status: pending verification (metrix/CLAUDE.md section 10), PASS for reference only
---
## data-auditor 审计报告：C2 修复提交第 1 轮（暂存树 b40224e68d1d42f9b4dc886fe9e159f9d99162b1，父提交 1900b1fe）

**结论：五项任务全部复算完成，结果都与 Executor 一致，没有 BLOCKER。** 另登记 4 个新的 MINOR，都在防范对象之外。

按 metrix/CLAUDE.md 第 10 节，data-auditor 仍是「待验证」，本次 PASS 只作参考。

### 运行环境与限制
- 主机 `vm`，Anthropic 云容器，只用 CPU，没有 nvidia 设备节点。
- 只加载了 Qwen 分词器。30 个冒烟 checkpoint 只哈希了文件字节，没有加载。
- 没有生成、读取或统计真实 TEST。e2e 里的 TEST 行是 Executor 测试自己写的合成行。
- 只写入了 `metrix/e1-pilot/audit/`，暂存区没有改动（ic8_00b 在全部运行之后复核：index 与 b40224e6 的 6620 个条目逐项相同）。
- e2e 驱动依次运行，没有并行。
- 我在 audit/ 下多生成了一个 `__pycache__/ic8_04_e2e.cpython-313.pyc`：手动 py_compile 时产生，已被 .gitignore 忽略，没有删除。

记号：`$S` = `/tmp/claude-0/-home-user/14ee74de-5799-5f8c-a07c-f9bcdb0676fe/scratchpad`，`$P` = `$S/venv/bin/python`。每条命令都经 `bash ic8_run_logged.sh <stdout 文件> ...` 运行，cwd 为 audit/。

**脚本**（都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/`）
- `ic8_run_logged.sh`、`ic8_00_state.py`、`ic8_01_hashes.py`、`ic8_02_data_recheck.py`、`ic8_03_test_refusal.py`
- `ic8_04_static.py`、`ic8_04_e2e.py`、`ic8_04_trace_plugin.py`、`ic8_04d_branch_tests.py`、`ic8_04d_plugin.py`
- `ic8_05_trainings.py`、`ic8_06_smoke_labels.py`、`ic8_07_mutation_remnants.py`

**完整 stdout**（都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/`）
- `ic8_00_state.txt`、`ic8_00b_state_final.txt`、`ic8_01_hashes.txt`、`ic8_02_data_recheck.txt`、`ic8_03_test_refusal.txt`
- `ic8_04_static.txt`、`ic8_04a_e2e_normal.txt`、`ic8_04b_e2e_stop_after_marker.txt`、`ic8_04c_e2e_crash_after_marker.txt`、`ic8_04d_branch_tests.txt`
- `ic8_05_trainings.txt`、`ic8_06_smoke_labels.txt`、`ic8_07_mutation_remnants.txt`、`ic8_99_git_status_final.txt`
- 被取代的试跑：`ic8_04a_e2e_normal_trial1_script_error.txt`。原因是我分析脚本的错误：`committed_record` 内部又调用 `committed_json`，嵌套的同一次读取被重复计数。文件末尾附了说明；其余观察在该次试跑中已与预期相同。

### 0. 审计对象的状态
- 命令：`$P -I -B ic8_00_state.py /home/user/OpenMythos $S/review_c2b $S/c2b_smoke`
- 原始输出（摘录）：
  - `HEAD 1900b1fe… == parent: True`
  - `index entries 6620 | tree b40224e6 entries 6620 | identical: True`
  - staged diff 是 input.diff 的尾部：True
  - `input_code.diff sha256 df2492a6… == git diff --cached …: True`
  - 代码 diff 的 sha256 为 `3920af52…`，与 c2b_03、c2b_04 首尾记录的值相同
  - `smoke tree 6071ea72: 40 code entries | staged tree: 40 | identical: True`
  - 暂存的冒烟记录副本：44 个，与 `$S/c2b_smoke/records` 逐字节相同的 43 个，另 1 个是 LABEL.txt
  - RUNBOOK_A100.md 与 c3_hf_tree_70d244cc.txt 都是 `??`，未暂存
  - `RESULT: PASS`
- 与 Executor 一致。说明：两份录制首尾记录的 write-tree 是 6071ea72，不是送审树 b40224e6；两棵树的代码条目相同，见 MINOR IC8-M3。

### 1. 冒烟数据目录：哈希、manifest 字段、L1–L6、候选可行性、split
- 命令：
  - `$P -I -B ic8_01_hashes.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2b_smoke $S/c2b_data`
  - `$P -I -B ic8_02_data_recheck.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2b_smoke`
- 四个冻结内容哈希：每个都是「我的值 = PROTOCOL_FROZEN = step1_record」，`ALL EQUAL True`。
  - facts `406c8801…6b97`、train_S `686fdd2f…bc1e`、candidates `e5d15c99…3705`、anchor_texts `8828bc4f…2408`
  - 我用分词器解码 512 篇锚文本 ids，得到同一个哈希。
- 8 个文件的 byte_sha256 与 canonical_sha256 同时等于以下四方：step1_record、我阶段 B 的记录、Executor 的 c2b_03 清单、c2b_data 的字节（例：`train_Y.jsonl c7430cad…6d15`）。
- step1_manifest_fields：`DATA_MANIFEST.json files == mine: True | SPLIT_MANIFEST.json split_sha256 == mine: True`。
  - TEST 条目保持冻结值，split_sha256 的 test_qa 为 null。
  - train_Y 的规范化哈希写在 split_sha256 中（B3 裁决注记）。
  - 两个 manifest 的工作区与 index 都等于冻结字节。
- 模板：32 个模板无差异，template_set_sha256 为 `2b524113…e28f`，三方相等。
- L1–L6：L1、L3a、L3b、L4、L5、L6 都是 0，L2 为 0.2（配对 capital.TRAIN.1 / capital.DEV.1）。三方相等：我的值、冒烟 step2_record、我阶段 A 的记录。detail 逐项相等，result 为 PASS。
- 候选可行性：`minimum available 5 | minimum pool 4 | cells with available < 4: [] | cells with pool < 4: []`；160 个候选列表中违反四重约束的为 0。
- split：
  - 160 个 fact_id 互不相同；learned 120、unread 40，两者不交；8 个 cell 各 15+5。
  - TRAIN 中没有 unread 的 fact；train_F 120、train_S 120、train_Y 240。
  - dev_qa 320，每个 fact 两题；general DEV 每个 domain 25 条；锚文本 512。
- 两个脚本都是 `RESULT: PASS`。与 Executor 一致，无差异。

### 2. 冒烟没有产生 TEST 内容；TEST 生成器黑盒拒绝
- 命令：`$P -I -B ic8_03_test_refusal.py /home/user/OpenMythos $P $S/inputs $S/c2b_smoke $S/ic8_test_out`
- 冒烟目录：`files under …/c2b_smoke: 119 | named test_qa.jsonl / general_test.jsonl: []`。
- step8_record：返回码 1，stdout 正是下面三行，refused True，out_exists False。
- 我自己运行一次生成器。运行前写出的预期即下面三行、exit 1。原始输出：
  ```
  TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
  no TEST content was generated, read or written
  RESULT: FAIL
  ```
  `exit code 1 | killed by the auditor False`
- 运行后：--out 没有创建；数据目录、inputs、src、git status 都没有变化；没有 results 目录，也没有 ST10 记录。`RESULT: PASS`。
- 与冒烟 step8 的 stdout 和 c2b_03 的拒绝行都相同。

### 3. 三种 e2e 驱动（运行 Executor 的 `test_test_evaluate_end_to_end_once`，加上我的透传追踪插件）
- 命令：`$P -I -B ic8_04_e2e.py /home/user/OpenMythos $P $S/inputs $S/ic8_e2e_<…> <mode>`
- 预期在运行前打印。我的 ST7 事前估计（夹具的 timing 下）：16×(1+1×3/2) + 17×0.1 + 15×0.1 = 43.2 s。

**normal（`ic8_04a`，pytest `1 passed in 208.69s`，`RESULT: PASS`）**
- 第 1 次运行：
  - check_preconditions、start_checks 各 1 次；先读已提交的 freeze、Gate 0、第 2 步、第 3 步记录。
  - 只哈希了 `F-F3-seed101.pt`。
  - 没有 look-ahead、没有 state 哈希、没有 begin、没有评测、没有提交、没有 final_record。
  - 返回 `(False, 'BLOCKED')`，没有标记。
- 第 2 次运行，begin 之前：
  - 15 个 .pt 全部核对。
  - `test_evaluation_seconds [43.2]`，`before_run [43.2]`。
  - base 的哈希 `a895622c…` 等于 step3 的 N 哈希、等于 begin 的参数、等于标记中的 N 哈希。
- 第 2 次运行，begin 之后：
  - 16 次 evaluate_model(split=test)，顺序与标记相同；16 次 claim；没有 DEV 评测。
  - compute、judge、report(test)、finish 依次各调用一次。
  - 实验记录文件为 `experiment_record_test-evaluate_20261127T055652Z.json/.txt`。
  - 返回 `(True, 'PIPELINE_NOT_QUALIFIED')`。
- 第 3 次运行：
  - begin 之前的部分与第 2 次相同。
  - begin 抛出 TestAlreadyEvaluated，没有评测。
  - final_record 以 `('test-evaluate','BLOCKED')` 被调用，message 为 `crash after the TEST marker: TestAlreadyEvaluated(...)`；文件名与第 2 次相同（同一个 Pilot）。
  - 记录被提交并推送，随后重新抛出原异常。
  - 这一结果与我运行前写出的预测相同，见 IC8-M1。
- 远端在夹具之后共 4 个提交：marker(A)、result(A)、实验记录(A，PIPELINE_NOT_QUALIFIED)、实验记录(M，BLOCKED)。
- 新增的 blob 中没有合成文字、没有 general_test 键、没有逐题字段。克隆工作区干净，HEAD 等于远端。test_details 有 16 个文件，位于克隆之外。本仓库没有变化。

**stop_after_marker（`ic8_04b`，`RESULT: PASS`）**
- 第 3 次 TEST 评测时注入 ProtocolStop。
- 观察到：final_record('test-evaluate','BLOCKED')；远端为 marker 之后加一个实验记录（Status BLOCKED，stop message 含注入文字）；没有 result。
- 返回 `(False,'BLOCKED')`，2 个 claim。

**crash_after_marker（`ic8_04c`，`RESULT: PASS`）**
- 第 3 次 TEST 评测时注入 RuntimeError。
- 观察到：实验记录被写入、提交并推送（Status BLOCKED，`crash after the TEST marker: RuntimeError('auditor-injected crash…')`，Actual 为 `{'crashed': …}`）。
- run_test_evaluate 重新抛出 RuntimeError；远端为 marker 加实验记录；克隆干净。
- **IC7-M1 已修且正确。**
- 三种模式的标记之前拒绝都不写记录，TEST 都只评一次。begin 之前新增的检查（已提交的第 2、3 步记录、N 的哈希、ST7 look-ahead）没有改变这两个结论。与 Executor 的说明一致。

### 4. 静态核对，另以 Executor 测试作驱动
- 命令：
  - `$P -I -B ic8_04_static.py /home/user/OpenMythos`
  - `$P -I -B ic8_04d_branch_tests.py /home/user/OpenMythos $P $S/inputs $S/ic8_04d`
- test_evaluate 中各步的源码行号依次递增（`all present and in this order: True`）：
  - 1149 formal 模式检查
  - 1151 check_preconditions
  - 1153 code_commit
  - 1154 start_checks
  - 1155 device_check
  - 1156 load_data
  - 1158 读取 TEST 文件
  - 1160–1163 freeze、Gate 0、step2、step3 记录
  - 1169 file_sha256
  - 1175 test_evaluation_seconds
  - 1182 before_run(look_ahead)
  - 1183 base_model
  - 1184 state_sha256
  - 1185 N 哈希比对（不符时 BLOCKED）
  - 1188 begin
  - 1196 唯一的评测调用 `control_evaluation(split='test', test_session=session, checkpoint_name=name)`，在唯一的 `for name in models` 循环中
  - 1212–1218 compute、judge、report、finish
- control_evaluation 只有一次 `p.evaluate(model, split=split, **kw)`，没有循环。
- 标记之前的读取：`(R.NotCommitted, KeyError, OSError, TypeError)` 都转为 ProtocolStop BLOCKED。
- GPU 时钟段为一个 try/finally，finally 中是 `p.close_clock()`。
- run_test_evaluate 有两个 handler：
  - 第一个 handler 的条件是 `not marker.exists() and code != 'ST10'`，成立时 return，不写记录。
  - 第二个 handler 捕获 Exception：标记不存在时裸 raise；标记存在时记 crash、status BLOCKED，在 try 之后调用 final_record，然后 `raise crash`。
- run_test_generate：
  - 只有一次 `subprocess.run`，之后调用 `st10_over_limit(p)`。
  - 唯一的 final_record 在 `if over:` 内，status BLOCKED，stop code ST10。
  - st10_over_limit 读已提交的 ST10 记录，NotCommitted 时返回 []。
  - test_data.main 在判断超限之前就提交 ST10 记录，所以超限时该分支能读到。
- 冒烟第 8 步：`if formal: raise ImplementationFail` 位于第 854 行，在第 857 行的 subprocess.run 之前；formal 列表检查 HEAD 或工作区中的 Gate 0、冻结、ST10 记录。
- 其余各项与第 1 轮相同：
  - CA20：begin 与 finish 只由 test_evaluate 调用。
  - CD5：generate_test 与 run_test_part 只在 test_data.main 中调用。
  - CD13：提交的 result 只含 6 个键，_summary_record 去掉 general_ 开头的键。
  - fetch 的分工符合裁决第 1 项。
  - `--steps` 只加在 smoke 子解析器上。
- 两项都是 `RESULT: PASS`。
- 驱动：运行前预期 `2 passed`、不启动生成器；实际 `2 passed in 9.14s`，生成器子进程调用为 `[]`。
- 与 Executor 一致。

### 5. 冒烟的 30 次训练
- 命令：`$P -I -B ic8_05_trainings.py /home/user/OpenMythos $S/c2b_smoke`
- 选定配置由我从 DEV 明细复算：F2（排名 F2,F1,F4,F3,F6,F5）、L6（L5 与 L6 都是 61/240，按 dNLL 选 L6）、A1。排名与 rows 都与 step4/5 相同。
- 30 个运行名与我从冻结 SEARCH_SPACE 推出的计划相同，step6 的 training_plan 顺序也相同；excluded 为 []。
- 每个运行逐项核对：
  - 文件 SHA-256 与字节数都等于记录。
  - state_sha256 等于 reloaded_state_sha256（30/30），30 个哈希互不相同，都不等于 N 的哈希。
  - Acc 与 dNLL 等于我的复算值。
- G0.8：分数差 0、NLL 差 0、预测差异 0。
- `RESULT: PASS`。限制同第 1 轮：重载后的哈希无法在不加载权重的前提下独立复算。

### 补充
- `ic8_06_smoke_labels.py`：
  - 76 个 JSON 都带 SMOKE 标签；实验记录只有一对，文件名带开始时间。
  - Gate 0 为 NOT_TESTED。
  - `st11_reads 'b17_estimate_hours'`，1.7032 h 未超过 3.5 h，所以 ST11 为 within bound；would-stop 只有 `['ST3']`，与按记录值推出的结果相同。
  - 没有任何步记录带 stopped 字段。
  - 我复算的 overhead 34.041297313 s 与记录的差为 0；counts 为 50/30/17/15/16；B17 总时长与报告用的和都相等。
  - 本轮 would-stop 比上一轮少了 ST11，原因是 CPU 计时不同：上一轮 0.89 s/step、DEV 评测 102.8 s，本轮 0.194 s/step、29.4 s。冒烟值不是结果。
- `ic8_07_mutation_remnants.py`：c2_mutate_fix1.py 的 25 个变异的原文在暂存与工作区的 pilot.py 和 run_pilot.py 中都恰好出现 1 次，两处字节相同。c2b_01 被杀时留下的变异已清除。`RESULT: PASS`。

### 修复逐条核对（本人范围内）
| 修复项 | 核对结论 | 依据 |
|---|---|---|
| MAJOR 2 | 已修且正确 | 静态核对、ic8_04d；test-generate 分支没有动态测试，见 IC8-M2 |
| MAJOR 4 / IC7-M1 | 已修且正确 | ic8_04c；副作用见 IC8-M1 |
| MAJOR 5 | TEST 的 look-ahead 已修且正确（动态 43.2 s）；训练前的 look-ahead 已修但有问题 | IC8-M4 |
| MAJOR 9 | 已修且正确 | 静态核对、ic8_04d |
| MAJOR 10 | 已修且正确 | ic8_06 |
| MINOR：实验记录文件名带开始时间 | 已修且正确 | ic8_04、ic8_06 |
| MINOR：N 的哈希与第 3 步记录比对 | 已修且正确 | ic8_04 |
| MINOR：标记之前的异常转为 BLOCKED | 已修 | 静态核对 |
| MINOR：GPU 时钟段在 try/finally 内 | 已修 | 静态核对 |
| IC7-M2 → CF30 | 未修，按设计交 Review Gate | DEFERRED_MINORS 1.32 |
| MAJOR 1、3、6、7、8、11、12 | 不在本人复算项目内，未独立复核 | 冒烟中未触发 MAJOR 3 的 stopped 字段 |

### 新登记的问题（都在防范对象之外，记为 MINOR，不构成 BLOCK）
- **IC8-M1：TEST 已评过之后再次运行 test-evaluate，会提交一份 BLOCKED 实验记录，message 为 "crash after the TEST marker: TestAlreadyEvaluated(...)"。**
  - 原因：TestAlreadyEvaluated 的基类是 Exception，标记在工作区中存在，于是走「标记之后崩溃」分支。
  - 仍然拒绝了评测，不会评两次；但这与 testgate 中 TestAlreadyEvaluated 的 docstring「Carries no section 9 status」矛盾，把拒绝记成了崩溃。
  - e2e 测试复用同一个 Pilot，第 3 次运行覆盖了第 2 次的实验记录文件，测试也没有断言这一点。生产中每次运行的开始时间不同，文件名不会重复。
  - 建议单独处理 TestAlreadyEvaluated，并交 Review Gate 决定状态词。
- **IC8-M2：run_test_generate 的 ST10 实验记录分支没有测试或变异覆盖，只有静态核对。** 另外，ST10 超限后若再次运行 test-generate，生成器会拒绝，但该分支仍会读到已提交的超限记录，再写一份 BLOCKED 记录。
- **IC8-M3（证据文字）**：
  - DEFERRED_MINORS 1.32 CF29 写「未发生」，但 c2b_01b_restore_after_kill.txt 记录了 kill 之后 pilot.py 确实留有变异（已恢复，ic8_07 证实没有残留）。
  - CF28 写「录制在送审树上」，实际录制的 write-tree 是 6071ea72，送审树是 b40224e6；两者代码相同。
- **IC8-M4：Pilot.run_seconds 对每个训练运行都乘以 B17 的 a_factor。**
  - B17 在 compute.estimate_total_hours 中只对 A arm 的 8 个运行使用 a_factor，冒烟预检记录中 a_factor 为 6.75。
  - 结果是非 A 运行的 ST7 事前估计偏大。按冒烟计时，约 423 s 对 88 s。偏保守，可能在 4 小时内本可完成时提前触发 ST7。
  - 不涉及数据、指标，也不会导致 TEST 评两次。交 code-reviewer 与 Review Gate。

### 运行后 `git status --short` 的原始输出（`ic8_99_git_status_final.txt`）
```
M  metrix/e1-pilot/reports/DEFERRED_MINORS.md
A  metrix/e1-pilot/reports/impl_c/c2_mutate_fix1.py
A  metrix/e1-pilot/reports/impl_c/c2b_01_checks_superseded_oom.txt
A  metrix/e1-pilot/reports/impl_c/c2b_01b_restore_after_kill.txt
A  metrix/e1-pilot/reports/impl_c/c2b_02_smoke_superseded_oom.txt
A  metrix/e1-pilot/reports/impl_c/c2b_03_checks.txt
A  metrix/e1-pilot/reports/impl_c/c2b_04_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c2b_checks.sh
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/LABEL.txt
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/experiment_record_smoke_20261127T052340Z.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/experiment_record_smoke_20261127T052340Z.txt
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/gate0_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/smoke_report.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step1_manifest_fields.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step1_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step2_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step3_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step4_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step5_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step6_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step7_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/step8_record.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A1-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A1-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/A-A6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/F-F6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L6-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/L-L6-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/S-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/S-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/S-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/Y-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/Y-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2b_smoke_records/training_runs/Y-F2-seed303.json
M  metrix/e1-pilot/src/metrix_e1/pilot.py
M  metrix/e1-pilot/tests/test_run_pilot.py
?? metrix/e1-pilot/RUNBOOK_A100.md
?? metrix/e1-pilot/audit/ic8_00_state.py
?? metrix/e1-pilot/audit/ic8_01_hashes.py
?? metrix/e1-pilot/audit/ic8_02_data_recheck.py
?? metrix/e1-pilot/audit/ic8_03_test_refusal.py
?? metrix/e1-pilot/audit/ic8_04_e2e.py
?? metrix/e1-pilot/audit/ic8_04_static.py
?? metrix/e1-pilot/audit/ic8_04_trace_plugin.py
?? metrix/e1-pilot/audit/ic8_04d_branch_tests.py
?? metrix/e1-pilot/audit/ic8_04d_plugin.py
?? metrix/e1-pilot/audit/ic8_05_trainings.py
?? metrix/e1-pilot/audit/ic8_06_smoke_labels.py
?? metrix/e1-pilot/audit/ic8_07_mutation_remnants.py
?? metrix/e1-pilot/audit/ic8_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_00b_state_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_01_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_02_data_recheck.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_03_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04a_e2e_normal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04a_e2e_normal_trial1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04b_e2e_stop_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04c_e2e_crash_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_04d_branch_tests.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_05_trainings.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_06_smoke_labels.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_07_mutation_remnants.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic8_99_git_status_final.txt
?? metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt
exit=0
```
RUNBOOK_A100.md 与 c3_hf_tree_70d244cc.txt 是 Executor 的 C3 草稿，不是我写的。除 audit/ 之外没有新增或改动的路径。

结论：PASS
