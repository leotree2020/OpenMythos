# data-auditor, C2 second fix commit, round 1 (staged tree a6ce8a0ea0aeff1e86443a2a22a2a4eb349bcc50, parent 0cbee197; committed as dd65a36169752a2c2df27028ecd66e3fcde2677b)
# invocation text: data-auditor_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py; trust status: pending verification (metrix/CLAUDE.md section 10), PASS for reference only
---
## data-auditor 审计报告：C2 第二个修复提交，第 1 轮

审计对象：暂存树 a6ce8a0ea0aeff1e86443a2a22a2a4eb349bcc50，父提交 0cbee197。

**结论：四项任务都已复算，结果都与 Executor 一致，没有 BLOCKER。** 另登记 2 个新的 MINOR，都在防范对象之外。

- 按 metrix/CLAUDE.md 第 10 节，data-auditor 仍是「待验证」，本次 PASS 只作参考。
- 审查依据 C1 裁决的防范对象：按 RUNBOOK 操作时意外评测 TEST 两次，或在 ST10 不成立时评测 TEST。下面各项均按此范围判定。

### 运行环境与限制
- 主机 `vm`，Anthropic 云容器，只用 CPU，`/dev` 下没有 nvidia 设备。
- 只加载了 Qwen 分词器。30 个冒烟 checkpoint 只哈希文件字节，没有加载。e2e 用的是 Executor 测试自建的随机小模型。
- 没有生成、读取或统计真实 TEST。e2e 中的 TEST 行是测试夹具自己写的合成行。
- 只写入了 `metrix/e1-pilot/audit/`，没有改动暂存区。证据是 ic9_00b：全部运行结束后，index 与 a6ce8a0e 的 6715 个条目逐项相同。
- e2e 驱动一次只运行一个，没有并行。
- `src/metrix_e1/__pycache__` 中没有比我的运行更新的 .pyc。

记号：`$S` = `/tmp/claude-0/-home-user/14ee74de-5799-5f8c-a07c-f9bcdb0676fe/scratchpad`，`$P` = `$S/venv/bin/python`。每条命令都在 audit/ 目录下以 `bash ic9_run_logged.sh <stdout 文件> ...` 的形式运行。

**脚本**，都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/`：
- 公共：`ic9_run_logged.sh`、`ic9_00_state.py`
- 数据与 TEST 拒绝：`ic9_01_hashes.py`、`ic9_02_data_recheck.py`、`ic9_03_test_refusal.py`
- 静态核对与驱动：`ic9_04_static.py`、`ic9_04_e2e.py`、`ic9_04_trace_plugin.py`、`ic9_04d_branch_tests.py`、`ic9_04d_plugin.py`、`ic9_04e_lookahead.py`、`ic9_04e_probe.py`
- 训练与补充：`ic9_05_trainings.py`、`ic9_06_smoke_labels.py`、`ic9_07_mutation_remnants.py`

**完整 stdout**，都在 `/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/`：
- 状态：`ic9_00_state.txt`、`ic9_00b_state_final.txt`
- 数据：`ic9_01_hashes.txt`、`ic9_02_data_recheck.txt`、`ic9_03_test_refusal.txt`
- 静态与分支：`ic9_04_static.txt`、`ic9_04d_branch_tests.txt`、`ic9_04e_lookahead.txt`
- e2e：`ic9_04a_e2e_normal.txt`、`ic9_04b_e2e_stop_after_marker.txt`、`ic9_04c_e2e_crash_after_marker.txt`、`ic9_04d_e2e_interrupt_after_marker.txt`、`ic9_04e2_e2e_st7_before_begin.txt`
- 其余：`ic9_05_trainings.txt`、`ic9_06_smoke_labels.txt`、`ic9_07_mutation_remnants.txt`、`ic9_99_git_status_final.txt`
- 试跑说明：`ic9_0x_trials_and_script_fixes.txt`。ic9_04_static 在正式运行之前有 3 次试跑失败，都是我脚本里预期字符串写错，stdout 没有保存，该文件逐条说明了原因与修正；ic9_07 有 1 次试跑，只改了措辞。

### 0. 审计对象的状态
- 命令：`$P -I -B ic9_00_state.py /home/user/OpenMythos $S/review_c2c $S/c2c_smoke`。全部运行之后又跑了一次，输出为 ic9_00b。
- 原始输出摘录：
  - `HEAD 0cbee197… == parent: True`
  - `index entries 6715 | tree a6ce8a0e entries 6715 | identical: True`
  - staged diff 是 input.diff 的尾部：True
  - `input_code.diff sha256 895b7cba… == git diff --cached …: True`
  - `working tree == index for src/tests/run_pilot.py: True`
  - 代码 diff 的 sha256 为 `a479c73c…`
  - `c2c_03_checks.txt` 与 `c2c_04_mutate_fix2b.txt`：两处 diff sha256 都等于 `a479c73c`；两处 ls-files 代码块都等于暂存树的代码条目：`[True, True]`
  - `c2c_02's code state == c2c_01's (ls-files lines, code diff sha256, write-tree e5abf74b): True`
  - `code entries differing between the smoke's state and the staged tree: ['metrix/e1-pilot/tests/test_run_pilot.py']`
  - 树对象 e5abf74b 的代码条目等于冒烟记录中的 ls-files 行：True
  - 冒烟记录副本 44 个，其中 43 个与 `$S/c2c_smoke/records` 逐字节相同，另 1 个是 LABEL.txt
  - RUNBOOK_A100.md 与 c3_hf_tree_70d244cc.txt 都是 `??`，未暂存
  - `RESULT: PASS`
- 与 Executor 一致：冒烟在 c2c_01 的树上运行，之后只改了 tests/test_run_pilot.py，src/ 与 run_pilot.py 没有变化。CG18 已修：录制的 STATE 中记录了 ls-files 代码条目，与送审树逐行相同。

### 1. 冒烟数据目录与 TEST 生成器拒绝
- 命令：
  - `$P -I -B ic9_01_hashes.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2c_smoke $S/c2c_data`
  - `$P -I -B ic9_02_data_recheck.py /home/user/OpenMythos $S/inputs/qwen_tokenizer $S/c2c_smoke`
  - `$P -I -B ic9_03_test_refusal.py /home/user/OpenMythos $P $S/inputs $S/c2c_smoke $S/ic9_test_out`
- 四个冻结内容哈希，每个都是「我的值 = PROTOCOL_FROZEN = step1_record」，`ALL EQUAL True`：
  - facts `406c8801…6b97`
  - train_S `686fdd2f…bc1e`
  - candidates `e5d15c99…3705`
  - anchor_texts `8828bc4f…2408`；我用分词器解码 512 篇锚文本 ids 得到同一个值
- 8 个文件：byte_sha256 与 canonical_sha256 同时等于 step1_record、我阶段 B 的记录、Executor 的 c2c_03 清单、c2c_data 的字节。
- step1_manifest_fields：`DATA_MANIFEST.json files == mine: True | SPLIT_MANIFEST.json split_sha256 == mine: True`。TEST 条目保持冻结值，test_qa 为 null；train_Y 的规范化哈希写在 split_sha256 中；两个 manifest 的工作区与 index 都等于冻结字节。
- 模板：32 个模板无差异，template_set_sha256 为 `2b524113…e28f`，三方相等。
- L1–L6 的 Gate 0 部分：
  - L1、L3a、L3b、L4、L5、L6 都是 0；L2 为 0.2，配对 capital.TRAIN.1 / capital.DEV.1。
  - 我的值、step2 报告、我阶段 A 的记录三方相等，detail 逐项相等，result 为 PASS。
- 候选可行性：`minimum available 5 | minimum pool 4 | cells with available < 4: [] | cells with pool < 4: []`；160 个列表中违反四重约束的为 0。
- split：
  - 160 个 fact_id 互不相同，learned 120、unread 40，两者不交；8 个 cell 各 15+5。
  - TRAIN 中没有 unread 的 fact；train_F 120、train_S 120、train_Y 240。
  - dev_qa 320；general DEV 每个 domain 25 条；锚文本 512。
- 冒烟没有产生 TEST：
  - `files under …/c2c_smoke: 119 | named test_qa.jsonl / general_test.jsonl: []`
  - step8_record 显示返回码 1，refused True。
- 生成器黑盒运行。运行前写出的预期即下面三行、exit 1，原始输出：
  ```
  TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
  no TEST content was generated, read or written
  RESULT: FAIL
  ```
  - `exit code 1 | killed by the auditor False`
  - --out 没有创建；数据目录、inputs、src 与 git status 都没有变化；没有 results 目录，也没有 ST10 记录。
- 三个脚本都是 `RESULT: PASS`。与 Executor 一致：拒绝行与 c2c_03 相同。

### 2. e2e 驱动（Executor 的 `test_test_evaluate_end_to_end_once` 作为驱动，加我的透传追踪插件）
- 命令：`$P -I -B ic9_04_e2e.py /home/user/OpenMythos $P $S/inputs $S/ic9_e2e_<x> <mode>`
- 预期在运行前打印。插件给 Pilot 实例换上一个子类，用来追踪测试中途重新赋值的 before_run 与 base_model；只记录调用，不改变调用和结果。
- 我对夹具 timing 的 TEST 事前估计：1 + 15×0.1 + 16×1×3/2 + 17×0.1 + 15×0.1 = **29.7 s**。

**normal（ic9_04a，`1 passed in 240.80s`，`RESULT: PASS`）**
- 第 0 次运行（新增：N 的哈希不符）：
  - 15 个 .pt 全部核对；look-ahead `[29.7]`；base_model 调用 1 次；状态哈希不等于第 3 步记录中的 N。
  - test_evaluate 抛出：`BLOCKED: the base model's state sha256 46da1003… is not N's a895622c… of the step 3 record; TEST not started`
  - `begun_by_this_process [False]`；没有 begin、没有评测、没有 final_record、没有 commit_paths；返回 `(False,'BLOCKED')`。与预期相等。
- 第 1 次运行（改动的 checkpoint 文件）：只哈希 1 个 .pt，没有 look-ahead，`begun [False]`，返回 `(False,'BLOCKED')`，不写记录。
- 第 2 次运行（评测）：
  - begin 之前与预期相等：look-ahead `[29.7]`，before_run `[29.7]`，状态哈希等于 N。
  - **begin 入口处观察到 `begin_called True, marker_before_begin False`，工作区中没有标记文件。**
  - 之后 16 次 `evaluate_model(split=test)`，顺序与标记中的模型相同；16 次 claim；没有 DEV 评测。
  - compute、judge、report、finish 各调用 1 次；final_record 为 PIPELINE_NOT_QUALIFIED；没有调用 begun_by_this_process。
- 第 3 次运行：
  - begin 之前的部分与第 2 次相同。
  - **begin 入口处为 `(True, True, True, True)`**，即 base 哈希等于 N、begin_called True、marker_before_begin True、工作区中有标记文件。
  - begin 抛出 TestAlreadyEvaluated。**final_record 0 次、write_experiment_record 0 次、commit_paths `[]`**，run_test_evaluate 抛出 TestAlreadyEvaluated。
- 远端在夹具之后**只有 3 个提交**：marker(A)、result(A)、实验记录(A，PIPELINE_NOT_QUALIFIED)。第 0、1、3 次运行都没有推送任何提交。
- 其余：没有合成文字，没有 general_test 键，没有逐题字段；克隆工作区干净，HEAD 等于远端；test_details 有 16 个文件；本仓库没有变化。

**stop_after_marker（ic9_04b，pytest 退出码 1，与预期相同，`RESULT: PASS`）**
- 第 3 次 TEST 评测时注入 ProtocolStop：`begun_by_this_process [True]`，2 次 claim。
- final_record 为 `('test-evaluate','BLOCKED',['stopped','test_begun'],True)`。
- 远端为 marker 加实验记录（BLOCKED，stop code None），没有 result。返回 `(False,'BLOCKED')`。

**crash_after_marker（ic9_04c，退出码 1，`RESULT: PASS`）**
- 注入 RuntimeError：begun True；记录为 BLOCKED，`crash after the TEST marker: RuntimeError('auditor-injected crash…')`，Actual 的键为 `['crashed','test_begun']`，test_begun 为 True。
- 记录已推送，异常原样抛出；克隆干净。

补充模式（任务未要求）：
- **interrupt_after_marker（ic9_04d_e2e，退出码 2 即 pytest 被中断，`RESULT: PASS`）**：注入 KeyboardInterrupt。记录 BLOCKED，`crash after the TEST marker: KeyboardInterrupt(…)`，已推送，原样抛出。CG20 已修且正确。
- **st7_before_begin（ic9_04e2，退出码 1，`RESULT: PASS`）**：在 before_run(29.7) 处注入 Stop ST7。
  - 没有 base_model、没有状态哈希、没有 begin、没有评测；`begun [False]`。
  - 记录 BLOCKED，stop code ST7，test_begun False，已推送。
  - 远端只有 1 个提交（实验记录），没有标记，没有 result，没有 test_details。CG5 的行为与 Executor 的说明一致，记不记录交 Review Gate。
- 局限：e2e 中的 ST7 是我注入的；真实的 GpuClock 路径在 CPU 上没有走到。

### 3. 静态核对、look-ahead 数值、分支测试
- 命令：
  - `$P -I -B ic9_04_static.py /home/user/OpenMythos`
  - `$P -I -B ic9_04e_lookahead.py /home/user/OpenMythos $P $S/inputs $S/c2c_smoke $S/ic9_04e`
  - `$P -I -B ic9_04d_branch_tests.py /home/user/OpenMythos $P $S/inputs $S/ic9_04d`

**begun_by_this_process 及其两个标志**
- 返回 `p.begin_called and (not p.marker_before_begin) and (p.root / TG.MARKER_REL).exists()`。
- test_evaluate 中的语句顺序：
  - 第 1198 行：N 哈希比对
  - 第 1201 行：`p.marker_before_begin = …exists()`
  - 第 1202 行：`p.begin_called = True`
  - 下一条语句是 `session = TG.begin_test_evaluation(fz, auth, data, base_sha)`，在第 1203 行
- 包内对这两个属性的赋值只有两处：`__init__` 中的 False/None，以及 test_evaluate 中的这两行。

**run_test_evaluate 的三个处理分支**，按顺序为 `['(ProtocolStop, TD.PreconditionFailed)', 'TG.TestAlreadyEvaluated', 'BaseException']`：
- 第 1 个：`begun = begun_by_this_process(p)`；`if not begun and code is None` 时 return，不调用 final_record。
- 第 2 个：`['p.close_clock()', 'raise']`。
- 第 3 个：`not begun_by_this_process(p)` 时裸 raise；否则 `crash = e`，状态 BLOCKED，test_begun True。
- try 之后调用 final_record，然后 `raise crash`。

**TestAlreadyEvaluated 的来源**
- 基类是 Exception，不会被第 1 个分支截获。
- 它只在 refuse_if_marker 中抛出；refuse_if_marker 只被 begin 调用，位于第 440 行，早于第 460 行写入标记。

**其余静态结果**
- 标记之前的 try 包含 load_data 与 read_jsonl，处理器为 `(R.NotCommitted, KeyError, OSError, TypeError, ValueError)`，转为 BLOCKED。
- run_test_generate 的行号顺序：formal 检查 1116 < code_commit 1118 < `start_checks('test-generate')` 1119 < `before = TG._blob(…ST10_RECORD_REL)` 1120 < subprocess.run 1123；`over = st10_over_limit(p) if before is None else []`；final_record 只在 `if over:` 内。
- run_seconds：`factor = q['a_factor'] if spec.arm == 'A' else 1.0`，各项与 Executor 的说明一致。
- before_run 的 7 个调用点与其后的加载都等于我的预期：step3 'load' 之后是 base_model；train_and_evaluate 中 run_seconds(spec) 之后是 base_model，eval_seconds(None) 之后是 p.evaluate(reloaded)；step7 'reload' 之后是 load_checkpoint。
- Pilot.commit 先调用 commit_paths，再从 uncommitted 中移除。start_checks 的检查顺序是 ledger、freeze、checkpoints。run_pilot.py 只在 main 中构造 1 次 Pilot，也不在循环中运行命令。
- `RESULT: PASS`。

**look-ahead 数值（ic9_04e）**
- 我的值由冒烟第 2 步记录中的 timing 与冻结文件算出，在驱动运行之前打印：
  - TEST：`0.317 + 15×0.211 + 16×30.228175×3/2 + 17×0.095869 + 15×0.031793 = 731.066353819 s`
  - 代码返回 `731.066353819`，相等。
  - 上一轮的公式算得 732.653 s，差 1.587 s。
- 训练运行：非 A 为 91.947243100 s，A 为 442.268971664 s；乘 A 因子的运行有 8 个。
  - 30 个运行逐个等于代码值。按 arm 列出的代码值：`{'A': [442.268971664], 'F'/'L'/'S'/'Y': [91.9472431]}`。
  - 我 30 个训练项之和 4629.565850006 s，等于 B17 记录的 train_seconds（other_runs 22、a_runs 8）。
- eval_seconds 三种情形都相等：load 30.545、reload 30.439、None 30.228。
- 预检之前两者都返回 0.0。
- 驱动 ic9_04e_probe.py 只调用这三个被审函数，没有调用检查代码，作为子进程运行，属于 C1 裁决第 5 项允许的驱动；分析脚本没有 import Executor 的任何代码。

**分支测试（ic9_04d，`9 passed`）**
- 运行了 records、test_generate、st7_look_ahead、overhead_counts、continuity、smoke_step8、stop_inside_a_step、formal_stop_and_crash[st3] 与 [crash] 这 9 个测试，没有启动生成器子进程。
- test_generate 测试中 `st10_over_limit` 的结果为 `[[], ['L4']]`：第三次调用时运行之前已有 ST10 记录，所以没有读，与我的预期相同。

### 4. 冒烟的 30 次训练
- 命令：`$P -I -B ic9_05_trainings.py /home/user/OpenMythos $S/c2c_smoke`
- 我从 DEV 明细复算的选定配置为 F2、L6（L5 与 L6 都是 61/240，按 dNLL 选 L6）、A1，排名与 step4/5 相同。
- 30 个运行名与我从冻结 SEARCH_SPACE 推出的计划相同，顺序也与 step6 的 training_plan 相同；excluded 为 []。
- 逐项核对：
  - 文件 SHA-256 与字节数都等于记录。
  - state 等于 reloaded，30/30；30 个哈希互不相同，都不等于 N。
  - Acc 与 dNLL 等于我的复算值。
- G0.8：分数差 0、NLL 差 0、预测差异 0。
- `RESULT: PASS`。限制同前两轮：重载后的哈希无法在不加载权重的前提下独立复算。

### 补充
- **ic9_06**：
  - 76 个 JSON 都带 SMOKE 标签，实验记录只有一对；Gate 0 为 NOT_TESTED；would-stop 为 `['ST3']`，与按记录值推出的结果相同；没有任何步记录带 stopped 字段。
  - overhead 为 33.024732316 s，差 0；B17 为 1.773 h，ST11 在界内。
- **ic9_07**：c2_mutate_fix2.py 的 35 个变异与 fix2b 的 1 个变异，原文在暂存的 pilot.py 和 run_pilot.py 中各恰好出现 1 次；暂存与工作区字节相同，没有残留的变异。我没有重跑变异。c2c_03 的 34/35 与 c2c_04 的 CAUGHT 都按记录接受，两份录制首尾的 STATE 相同（见第 0 项 b）。

### 修复逐条核对（本人范围内）
| 项 | 结论 | 依据 |
|---|---|---|
| MAJOR 1 / IC8-M4（A 因子） | 已修且正确 | 静态 i；ic9_04e：30 个运行逐个相等，训练项之和等于 B17 |
| MAJOR 2（TEST 估计，reload_s） | 已修且正确；是否加余量交 Review Gate | 静态 j；ic9_04e 731.066 s；e2e 29.7 s |
| MAJOR 3 / IC8-M1（TestAlreadyEvaluated） | 已修且正确 | 静态 b；e2e normal 第 3 次运行不写记录、远端无新提交 |
| MAJOR 4（测试） | 已补；9 个指名测试在暂存树上通过 | ic9_04d |
| IC8-M2 / CG7 / CG22（test-generate） | 已修且正确 | 静态 d；ic9_04d `[[], ['L4']]` |
| CG5（begin 之前带停止码的停止写记录） | 行为与说明一致；记不记录交 Review Gate | ic9_04e2 |
| CG9、CG11、CG13 | 已修 | 静态 a、k；continuity 测试通过 |
| CG20（KeyboardInterrupt） | 已修且正确 | ic9_04d_e2e |
| IC8-M3 / CG18（证据文字与 STATE） | 已修 | DEFERRED_MINORS 1.33 段首的更正；ic9_00 b |
| CG10、CG8 的消息 | 只读过 diff，未独立复核 | 不在复算项目内 |

### 新登记的问题（都在防范对象之外，记为 MINOR，不构成 BLOCK）
- **IC9-M1**：test_evaluate 开始时没有重置 `p.begin_called` 与 `p.marker_before_begin`。
  - 同一个 Pilot 在一次评测之后若再次运行，并在 begin 之前遇到没有停止码的拒绝，这两个旧值会使 begun_by_this_process 为 True，从而写一份「已开始」的记录。
  - 生产中每个进程只构造 1 个 Pilot、只运行 1 个命令（静态 h），所以走不到。只有测试复用 Pilot：records 测试自己手动重置了这两个值；e2e 的第 3 次运行会走到 begin，所以不受影响。
  - 建议在 test_evaluate 开始时重置。
- **IC9-M2**：只作报告的 `checkpoint_overhead_report_only` 仍按 50 × load_s 计算，其中包括 15 个 TEST checkpoint 与 3 次 G0.8 重载；本次的 test_evaluation_seconds 对同样的加载改用 reload_s。
  - 两种计法对同一批加载不一致。该值只用于报告，没有任何停止条件读取它。

### 运行后 `git status --short` 的原始输出（ic9_99_git_status_final.txt）
```
M  metrix/e1-pilot/reports/DEFERRED_MINORS.md
A  metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py
A  metrix/e1-pilot/reports/impl_c/c2_mutate_fix2b.py
A  metrix/e1-pilot/reports/impl_c/c2c_01_checks_superseded.txt
A  metrix/e1-pilot/reports/impl_c/c2c_02_smoke.txt
A  metrix/e1-pilot/reports/impl_c/c2c_03_checks.txt
A  metrix/e1-pilot/reports/impl_c/c2c_04_mutate_fix2b.txt
A  metrix/e1-pilot/reports/impl_c/c2c_checks.sh
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/LABEL.txt
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/experiment_record_smoke_20261127T070352Z.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/experiment_record_smoke_20261127T070352Z.txt
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/gate0_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/smoke_report.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step1_manifest_fields.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step1_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step2_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step3_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step4_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step5_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step6_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step7_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/step8_record.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A1-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A1-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/A-A6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/F-F6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L1-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L3-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L4-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L5-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L6-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L6-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/L-L6-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/S-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/S-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/S-F2-seed303.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/Y-F2-seed101.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/Y-F2-seed202.json
A  metrix/e1-pilot/reports/impl_c/c2c_smoke_records/training_runs/Y-F2-seed303.json
M  metrix/e1-pilot/src/metrix_e1/pilot.py
M  metrix/e1-pilot/tests/test_run_pilot.py
?? metrix/e1-pilot/RUNBOOK_A100.md
?? metrix/e1-pilot/audit/ic9_00_state.py
?? metrix/e1-pilot/audit/ic9_01_hashes.py
?? metrix/e1-pilot/audit/ic9_02_data_recheck.py
?? metrix/e1-pilot/audit/ic9_03_test_refusal.py
?? metrix/e1-pilot/audit/ic9_04_e2e.py
?? metrix/e1-pilot/audit/ic9_04_static.py
?? metrix/e1-pilot/audit/ic9_04_trace_plugin.py
?? metrix/e1-pilot/audit/ic9_04d_branch_tests.py
?? metrix/e1-pilot/audit/ic9_04d_plugin.py
?? metrix/e1-pilot/audit/ic9_04e_lookahead.py
?? metrix/e1-pilot/audit/ic9_04e_probe.py
?? metrix/e1-pilot/audit/ic9_05_trainings.py
?? metrix/e1-pilot/audit/ic9_06_smoke_labels.py
?? metrix/e1-pilot/audit/ic9_07_mutation_remnants.py
?? metrix/e1-pilot/audit/ic9_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_00b_state_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_01_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_02_data_recheck.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_03_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04a_e2e_normal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04b_e2e_stop_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04c_e2e_crash_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04d_branch_tests.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04d_e2e_interrupt_after_marker.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04e2_e2e_st7_before_begin.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_04e_lookahead.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_05_trainings.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_06_smoke_labels.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_07_mutation_remnants.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_0x_trials_and_script_fixes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic9_99_git_status_final.txt
?? metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt
exit=0
```
- RUNBOOK_A100.md 与 c3_hf_tree_70d244cc.txt 是 Executor 的 C3 草稿，不是我写的。
- 除 audit/ 之外，没有新增或改动的路径。暂存的条目与送审树 a6ce8a0e 相同。

结论：PASS
