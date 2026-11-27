# code-reviewer, C2 second fix commit, round 1 (staged tree a6ce8a0ea0aeff1e86443a2a22a2a4eb349bcc50, parent 0cbee197)
# invocation text: code-reviewer_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 2 段（C2）第二个修复提交，第 1 轮。暂存树 a6ce8a0e，父提交 0cbee197。

依据：
- scratchpad/review_c2c/ 下的 input_code.diff、input.diff、notes.txt；
- 仓库代码：pilot.py、testgate.py、test_data.py、stops.py、errors.py、data.py、frozen.py、run_pilot.py、tests/test_run_pilot.py；
- METRIX_E1_PROTOCOL.md 第 7、8、10、11 节（283、528、582、619–624 行）；
- 上一轮两份审查原文（reviews/49fc9a35…/code-reviewer_round1.md、data-auditor_round1.md）；
- reports/DEFERRED_MINORS.md 1.33。

我只用了 Read、Grep、Glob，没有运行代码、git 或变异。"已验证"指引用了已暂存的原始输出（写明路径与行号）；其余判断都来自读代码，标为"未验证"。

## 原始输出核对（已验证）

- 代码绑定：
  - 录制首尾的代码 blob 与 input_code.diff 的 index 行一致：pilot.py 219292a、test_run_pilot.py 7ee1819（reports/impl_c/c2c_03_checks.txt:40、57、256、273）。
  - 首尾都输出了 WORKTREE_EQUALS_INDEX（c2c_03:22、238）。
- pytest：321 passed（c2c_03:142）。
- 变异：
  - c2_mutate_fix2.py 共 35 个，测出 34 个，RESULT: FAIL（c2c_03:221-223）。
  - 未测出的一个是 "begun read from the marker file alone"：records 测试 FAILED，e2e passed（c2c_03:185-187）。
  - c2_mutate_fix2b.py 单独重跑这一个变异：CAUGHT，RESULT: PASS，首尾 STATE 与 c2c_03 相同（c2c_04_mutate_fix2b.txt:4-7、23、40、50-54）。
- 冒烟：
  - c2c_02 中 src/ 与 run_pilot.py 的各条 blob 都与 c2c_03 相同；只有 test_run_pilot.py 不同（85275e1，c2c_02:40）。
  - c2c_02 与 c2c_01 的写树都是 e5abf74b（c2c_02:5；c2c_01_checks_superseded.txt:22、55）。
  - 结果：30 次训练，每次 3 步；Gate 0 NOT_TESTED；ST3 记为 would stop；第 8 步生成器 exit 1、--out 未创建；RESULT: PASS（c2c_02:67、103、125-128）。

## 上一轮各项核对

1. **MAJOR 1 / IC8-M4（A 因子）：已修且正确。**
   - run_seconds 只对 arm A 乘 a_factor，并计入 load_s 与 file_hash_s（pilot.py:337-339）。
   - eval_seconds 按调用处先加载什么来计：第 3 步 "load"（650）、第 7 步 "reload"（805）、训练后已在内存 None（700）。
   - 与实际执行的顺序逐项对得上（train_and_evaluate 689-701；save_checkpoint 446-461）。
   - 测试 test_st7_look_ahead_of_a_run 与对应变异已测出（c2c_03:194-195）。【代码部分未验证；变异已验证】
2. **MAJOR 2（TEST 估计）：已修，有一处小偏差（见 MINOR）。**
   - 估计为 N 的 load_s、15 次 reload_s、17 次 hash_s、15 次 file_hash_s，与 test_evaluate 的实际调用一致（1196-1197、1210、require_test_session）。
   - 15 次 checkpoint 文件哈希发生在 GPU 时钟打开之前（1180-1187 在 1195 之前），却也计入了估计。
   - 不加余量，交 Review Gate。【未验证】
3. **MAJOR 3 / IC8-M1（TestAlreadyEvaluated 被记成崩溃）：已修但有问题。**
   - TestAlreadyEvaluated 的分支已经正确：单独捕获、不写记录、原样抛出；e2e 断言远端 tip 不变（tests:420-423）。
   - 但 TEST 评过之后再次运行 test-evaluate 时，begin 之前的 ST7、ST8、ST9 现在作为"带停止码的协议停止"写入并推送 BLOCKED 记录，同一症状仍可经这条路径出现（下文 MAJOR 1）。
   - test_evaluate 中真实设置两个标志的两行（1201-1202）没有任何测试或变异执行（下文 MAJOR 3）。
4. **MAJOR 4（测试）：已修且正确。**
   - formal 下的 ST3 与崩溃（tests:669-704）；
   - test-generate 的 ST10 记录（707-734）；
   - before_run 收到的值：提交链 611-615，e2e 397-401；
   - N 的哈希不符（385-388）；
   - 对应变异都已测出（c2c_03:188-206）。
   - 遗漏：test-generate 的 code_commit 与 start_checks 没有测试（MINOR）。
   - begun 的判定逻辑只用伪造的标志测试过（MAJOR 3）。

上一轮 MINOR（DEFERRED_MINORS 1.33 CG5–CG22）：
- **已修且正确**：
  - CG6（file_hash_s、reload_s、已在内存的模型）；
  - CG7（code_commit；只记本次运行提交的 ST10，有测试）；
  - CG8（消息，320-322）；
  - CG9（start_checks 326-328；测试 465-470；变异见 c2c_03:207-208）；
  - CG10（1088）；
  - CG11（271-274）；
  - CG13（1169-1192，补了 ValueError）；
  - CG16（c2c_checks.sh:3）；
  - CG17（c2_mutate_fix2.py:parse）；
  - CG20（1277-1285；测试 530-532）。
- **已修但有问题**：
  - CG5：begin 之前带停止码的停止写记录。这与 test_evaluate 中检查的先后顺序合在一起，带来新问题（下文 MAJOR 1、MAJOR 2）。
  - CG22：已加 start_checks（1119），但没有测试。
  - CG18：录制已记录 git ls-files -s；但 c2c_04 运行时 c2_mutate_fix2b.py 还未暂存，其字节没有被任何输出绑定（MINOR）。
- **登记不改**：CG12、CG14、CG19、CG21，同意登记。
- **未完成**：CG15。IMPL_C_REPORT.md 仍只有 C1 节（已核对仓库文件：60 行起是 C1，没有 C2 节）；本次 docstring（pilot.py:188-189）又新增了一处指向该文件的引用。

## 重点问题的结论（未验证）

**begun_by_this_process 在 begin 各种失败方式下的结果（三个条件：本进程调用了 begin、调用前没有标记、现在有标记）：**

- 写标记之前的拒绝：check_checkout、verify_authorization、st10_check 的 _refuse、rows、base hash、evaluated_models、check_commit_preconditions、code_commit。
  - 标记不存在，所以 begun 为 False。
  - 没有停止码的拒绝不写记录；ST10 写记录。正确。
- 本次运行之前已有标记、没有结果：refuse_if_marker 抛出没有停止码的 BLOCKED。
  - marker_before_begin 为 True，所以 begun 为 False，不写记录。正确。
- 标记写出之后，暂存、提交或推送失败，或推送后字节核对失败：begun 为 True，写记录。
  - 与 refuse_if_marker 的口径"有标记、没有结果即视为已评"一致。正确。
  - final_record 在 HEAD 与远端不一致或索引中有暂存内容时不提交，只记日志，不会掩盖原来的停止。
- TestAlreadyEvaluated：单独捕获，与标志无关。正确。
- 标志按 Pilot 实例保存，每次调用时不重置；run_pilot.py:64-72 每个进程只建一个 Pilot，所以生产路径不受影响（MINOR）。

**防范对象内：**
- 没有找到"评两次 TEST"或"ST10 不成立时评测 TEST"的路径。
- refuse_if_marker、st10_check、require_test_session、claim_checkpoint 都未改动。
- 本次新增的路径只在 begin 之前多拒绝一次或多写一份记录。

**连续性检查的顺序：**
- formal：ledger、冻结记录、checkpoint，合理。
- test-generate：code_commit、start_checks，然后才启动子进程，合理。
- test-evaluate：check_preconditions（可抛 ST12）在 start_checks 之前。在 CG5 之后，这个顺序有了后果（MAJOR 2）。

## 问题

MAJOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1188-1203、1262-1273（另见 test_data.py:99-108、testgate.py:440） | [未验证] 上一轮 MAJOR 3 的同一症状仍可经另一条路径出现：TEST 已评过（结果已提交）之后，Executor 意外再运行一次 test-evaluate，并且在 begin 中的 refuse_if_marker 之前遇到带停止码的停止，就会提交并推送一份 BLOCKED 实验记录。原因：check_preconditions 不检查标记与结果；refuse_if_marker 只在 begin 中运行，排在 start_checks、ST8、before_run(look_ahead)（ST7、ST9）和加载基座之后；而本次改动让 begin 之前带停止码的停止都写记录。ST7 的可能性不小：第一次 TEST 已把时钟推进了约一个 look_ahead，第二次再加一个 look_ahead，满足 U0 + 2L > 4 h 即触发。协议第 7 节规定 ST7 的计时范围是"从第一次加载模型到 TEST 评测结束"（283 行），TEST 结束后本不应再有 ST7。这次运行还会打开新的时钟段并加载 N。闸门仍然拒绝第二次评测，所以不是 BLOCKER。e2e 的最后一步把 before_run 换成了记录函数，没有覆盖这条路径 | `p.before_run(look_ahead)` 位于 `TG.begin_test_evaluation(...)` 之前；`if not begun and code is None: … return` 之外的停止都走 `final_record` | 在 test_evaluate 开头（check_preconditions 之后、任何可能停止的检查之前）先做只读的已评检查：HEAD 或工作区有 RESULT_REL 时抛出 TestAlreadyEvaluated（不 fetch 也可以，begin 中仍有完整检查）；或在 run_test_evaluate 写 begin 之前的停止记录前检查 RESULT_REL 是否已存在；补测试：TEST 评过之后、before_run 抛 ST7 时，远端 tip 不变

MAJOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1164-1168、1262-1273（stops.py:138-146；data.py:604；frozen.py:316-319） | [未验证；不确定之处：协议 582 行要求"每次运行（含被停止的）提交一份"，Review Gate 可能认为该记录应当存在，或把它视为范围外的边缘情况、降为 MINOR] 本次改动造成的回归：用错误的 --work（例如路径打错、目录为空）运行 test-evaluate 时，第一项检查 check_preconditions 调用 STP.st12(…, data_dir)，因读不到数据目录抛出 ST12Error（"ST12","BLOCKED"）。按本次的新规则，带停止码的停止写记录，于是一份 ST12 BLOCKED 实验记录被写入仓库结果目录，并提交、推送到 pilot 的分支。本来应先拒绝这次运行的连续性检查（start_checks："Raises a BLOCKED stop before anything is written"）排在 check_preconditions 之后，没有机会执行。这份记录把操作失误记成了 pilot 数据的 ST12，而且其 code_commit 为 None（1166 行在 1164 行之后）。改动之前，这种情形是不写记录的拒绝 | `fz, auth = TD.check_preconditions(p.root, p.inputs, p.data_dir)` 在 `p.start_checks("test-evaluate")` 之前；`if not begun and code is None:` | 把 code_commit 与 start_checks 移到 check_preconditions 之前（start_checks 只读 HEAD 与 --work）；补一个错误 --work 的测试（不写记录、远端 tip 不变）；在交 Review Gate 的待决第 1 项中写明这条路径

MAJOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1201-1202；tests/test_run_pilot.py:505-514、536-556；reports/impl_c/c2_mutate_fix2.py:75-92 | [未验证（变异没有运行）] 修复 MAJOR 3 的核心接线没有任何测试执行：真正设置 begin_called 与 marker_before_begin 的是 test_evaluate 中的这两行。records 测试由伪造的 test_evaluate 自己设置这两个标志（"as test_evaluate"）。e2e 只走成功路径与 TestAlreadyEvaluated，两者都不读 begun。所以下列改动都不会使任何测试失败：删去 `p.begin_called = True`；把 `marker_before_begin` 的赋值移到 begin 之后（这时它恒为 True）。这两种改动的后果相同：begin 之后的崩溃或停止不再写记录，而这正是 TEST 被消耗时唯一的证据 | `p.marker_before_begin = (p.root / TG.MARKER_REL).exists()`；`p.begin_called = True`；records 测试中 `p_.marker_before_begin, p_.begin_called = False, True` | 在 e2e（eval_clone）中让真实的 test_evaluate 在 begin 之后失败（例如替换 control_evaluation 或 E.evaluate_model 在第 2 个模型抛出），断言实验记录带 test_begun True 并已推送；再让 begin 在写标记之前失败（例如 dry-run 推送失败），断言不写记录；对这两行各加一个变异

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:193-194（对照 1180-1187、1195、395-410） | [未验证] TEST 估计中的 15 次 checkpoint 文件哈希，在 before_run(look_ahead) 调用 first_load 打开 GPU 时钟之前就已经完成，不计入 ST7 的累计时间。所以估计偏高 15 × file_hash_s（方向保守，但会减少可用余量，可能造成不必要的 ST7 BLOCKED）。另外，用 `test_file_hashes` 作为 checkpoint 加载次数，借用了含义不同的计数名，不易读 | `n["test_file_hashes"] * pre["reload_s"] … + n["test_file_hashes"] * pre["file_hash_s"]` | 去掉 file_hash_s 一项，或在 docstring 写明是有意保守；加载次数用 `n["test_models"] - 1` 或单独的计数名

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:650-652、700-701 | [未验证] 事前估计还有两处小的漏计：第 3 步的估计没有计入 N 的 state_sha256（hash_s）；S 的 3 次训练在评测时还要算 with_s_mapping（evaluate.py:345-347 的 score_s_mapping），估计按一次 DEV 评测计（与 B17 的口径相同）。量级小 | `p.before_run(p.eval_seconds("load"))` 之后紧接着 `T.state_sha256(model)`；`p.evaluate(reloaded, with_em=True, with_s_mapping=spec.arm == "S")` | 登记；或第 3 步加上 hash_s

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1168、1262-1273（对照 final_record 1053-1056 的说明） | [未验证] test-evaluate 在 begin 之前遇到的 ST8 现在会提交并推送记录，而 formal 在第 1 步之前的 ST8 只写到 <work>（理由是"不从不是 pilot 的机器推送"）。start_checks 要求 --work 中有 ledger，所以实际几乎只会发生在 pilot 自己的机器上。两种处理不一致，范围外 | `p.device_info_record = p.device_check()` 位于 run_test_evaluate 的记录分支之内 | 登记；在交 Review Gate 的待决第 1 项中一并写明

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:238-239、1243-1246 | [未验证] begin_called 与 marker_before_begin 是 Pilot 实例的状态，每次调用 test_evaluate 时不重置。同一个 Pilot 第二次调用时，若在 1201 行之前停止，就会沿用上一次的标志（True、False），把停止判为"本进程已开始"。生产中每个进程只调用一次（run_pilot.py:64-72），只影响复用 Pilot 的测试；records 测试为此手工重置（514 行） | `self.begin_called = False`（只在 `__init__` 中） | 在 test_evaluate 开头重置两个标志；登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1118-1119；tests/test_run_pilot.py:707-734 | [已核对仓库测试：tests 中没有 run_test_generate 的 start_checks 或 code_commit 的断言] CG7 的 code_commit 与 CG22 的 start_checks 都没有测试或变异。删去任一行，测试都会通过 | `p.code_commit = TG.code_commit(p.root)`；`p.start_checks("test-generate")` | 在现有测试中断言 final_record 收到时 p.code_commit 已设置；补一个"已提交第 1 步记录、--work 没有 ledger 时拒绝，子进程未被调用"的情形

MINOR | metrix/e1-pilot/tests/test_run_pilot.py:640-666、559-605 | [已核对] `_formal_on_clone` 的 docstring 写的是"The replacements of test_formal_commit_chain… (…, Gate 0 verdict)"，但它没有替换 G.judge，fake_eval 也不处理 with_em=False 与 with_s_mapping（提交链测试中的版本处理了，589-594）。提交链测试本身也没有改用这个辅助函数，两份设置代码重复 | `def fake_eval(…): out = copy.deepcopy(base_ev) … return out` | 改正 docstring；提交链测试改用该辅助函数，或在 docstring 中写明两者的差别

MINOR | metrix/e1-pilot/tests/test_run_pilot.py:496-497、278-281、611-612 | [已核对] 可读性：(1) records 测试的 docstring 仍写 "before the marker a refusal writes no record (ST10 excepted)"，现在 begin 之前带停止码的停止都写记录；(2) test_st7_look_ahead_of_a_run 把训练步数硬写成 300，没有读 contract.training.total_steps；(3) 提交链测试先用 training_plan 加一个与本测试无关的选择 {"F1","L1","A1"} 再筛出 F 的搜索运行，等价于 T.search_runs(p.contract, "F") | `0.1 * 300`；`plan = T.training_plan(p.contract, {"F": "F1", "L": "L1", "A": "A1"})` | 更新 docstring；用 contract.training.total_steps；直接用 search_runs

MINOR | metrix/e1-pilot/reports/impl_c/c2_mutate_fix2.py:84-86；c2_mutate_fix2b.py:21-31；c2c_04_mutate_fix2b.txt:1-7 | [已验证：c2c_03:185-187、221-223；c2c_04:5 的写树与 c2c_03:24 相同] (1) 暂存的 c2_mutate_fix2.py 仍为该变异指名 E2E，任何人重跑都会得到 RESULT: FAIL，证据的结论要靠 fix2b 补齐；(2) c2_mutate_fix2b.py 中除 RECORDS 外的常量都没有使用（死代码）；(3) c2c_04 运行时 fix2b 尚未暂存（写树与 c2c_03 相同），STATE 只覆盖 src/、tests/、run_pilot.py，所以运行时 fix2b 的字节没有被任何输出绑定 | `RECORDS + " " + E2E`；`E2E = …`、`CKPT = …` 等在 fix2b 中未被引用 | 登记；以后的录制在 STATE 中加入所运行脚本的 sha256

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:188-189（另见 58、817、995、1020、1051）；reports/IMPL_C_REPORT.md | [已核对仓库文件] CG15 未完成：IMPL_C_REPORT.md 仍没有 C2 节，也没有写入 2026-11-27 的裁决；本次又新增了一处指向它的引用（"No margin is added (for Review Gate, reports/IMPL_C_REPORT.md)"） | IMPL_C_REPORT.md 只有 "## C1" 节（60 行起） | 按 CG15，在报告提交中写入 C2 节，包括 TEST 估计的余量与待决第 1 项（本审查 MAJOR 1、2 的路径）

结论：PASS
