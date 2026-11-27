# code-reviewer, C2 fix commit, round 1 (staged tree b40224e68d1d42f9b4dc886fe9e159f9d99162b1, parent 1900b1fe)
# invocation text: code-reviewer_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 2 段（C2）修复提交，第 1 轮。暂存树 b40224e6，父提交 1900b1fe。

依据：
- input_code.diff 与 input.diff 的文件清单。
- 仓库中的代码：pilot.py、testgate.py、stops.py、compute.py、record.py、test_data.py、train.py、run_pilot.py、tests/test_run_pilot.py。
- METRIX_E1_PROTOCOL.md 第 7–11 节。
- tasks/IMPL_C2_OWNER_MESSAGE.md、reports/DEFERRED_MINORS.md 1.32、第 1 轮两份审查原文。

我只用了 Read、Grep、Glob，没有运行任何代码或 git 命令。"已验证"指引用了暂存的原始输出（路径与行号已写明）；其余判断都是读代码得出的，标为"未验证"。

## 原始输出核对（已验证）

- 全部 pytest：317 passed（reports/impl_c/c2b_03_checks.txt:103）。
- 变异：25 个全部 CAUGHT，前后树哈希 EQUAL，RESULT: PASS（c2b_03_checks.txt:106-162）。
- 录制前后的状态：
  - 工作区等于暂存区，代码 diff 的 sha256 为 3920af52…（c2b_03_checks.txt:23-24、178-179；c2b_04_smoke.txt:6-7、220-221）。
  - 写树是 6071ea72，不是送审树 b40224e6（见 MINOR）。
  - pilot.py 的暂存 blob a6633d1 与 c2b_01b_restore_after_kill.txt:5 一致。
- 冒烟：
  - 30 次训练，每次 3 步（c2b_04_smoke.txt:86）。
  - ST3 记为 would stop（:27）。
  - Gate 0 为 NOT_TESTED（:60、85）。
  - 第 8 步生成器 exit 1，--out 未创建（:63）。
  - 三个 LABEL.txt（:213-215）。
  - ST11 只读 B17，为 1.703 h（:14；c2b_smoke_records/step2_record.json:98、125、127）。本次 ST11 没有触发，所以 ST11 的 "smoke: would stop" 分支没有被冒烟执行。
- 仓库中没有 results 目录（c2b_03_checks.txt:74）。
- CF29 所说的风险已经实际发生，并已恢复（c2b_01b_restore_after_kill.txt:3-22）。

## 第 1 轮各项核对

1. **MAJOR 1（第 1 步前停止只写 <work>）**：未修，按说明交 Review Gate。docstring 已补全各情形（pilot.py:1032-1039）。【未验证】
2. **MAJOR 2（ST10 没有实验记录）**：已修但有问题。test-generate 与 test-evaluate 的 ST10 都写记录（pilot.py:1111-1116、1242-1250）。但 test-generate 的记录中 code_commit 为空，重复运行会再记一次 ST10，这条路径也没有测试（下文 MAJOR 4、MINOR 7）。
3. **MAJOR 3（步内停止）**：已修。ST1、ST11、ST2、ST3 先写并提交该步记录（pilot.py:296-307、560、565、650、749），未提交的记录随实验记录一起提交（1048-1050）。formal 下的这两条提交路径没有测试或变异执行过（下文 MAJOR 4）。
4. **MAJOR 4 / IC7-M1（标记之后的崩溃）**：已修但有问题。判断条件是"工作区中有标记"，不是"本进程已经开始评测"；TEST 评测完成之后再运行一次，会提交一份 BLOCKED 记录（下文 MAJOR 3）。
5. **MAJOR 5（ST7 事前判断）**：已修但有问题。
   - 训练前的估计对每个 arm 都乘了 A 因子。
   - TEST 的估计把 15 次 checkpoint 加载按 load_s 计。
   - 估计值有没有真的传给 before_run，没有测试。
   - 见下文 MAJOR 1、2、4。
6. **MAJOR 6（非有限值）**：已修且正确。control_evaluation（656-663）用于 640、794、1196 行；预检见 587-589。预检的读法交 Review Gate（MINOR 21）。
7. **MAJOR 7（剔除的配置）**：KeyError 已修且正确（695-701、833；提交链测试断言 F6 的哈希在冻结记录中）。G0.2 的读法写在注释中，交 Review Gate（801-805）。
8. **MAJOR 8（冻结前的 ST12）**：已修且正确（830、839-840）。
9. **MAJOR 9（冒烟第 8 步）**：已修且正确（852-856）；测试与变异见 c2b_03:154-155。
10. **MAJOR 10（预检）**：已修且正确。565 行读 b17_estimate_hours，624-627 行的开销只报告；ST11 是否读两者之和交 Review Gate。
11. **MAJOR 11（重跑）**：(b)(c) 已修（267-274、309-321）。(a) 同一 --work 重跑未修，交 Owner/RUNBOOK（MINOR 9）。连续性检查另有一处误拒（MINOR 8）。
12. **MAJOR 12（formal 独有路径）**：已修。提交链测试执行了以下真实代码：
    - formal 的 step_start（含 fetch 与 dry-run push）；
    - step_end 中的 commit_paths；
    - 第 1 步写 manifest；
    - step8_freeze 与 freeze_record_problem；
    - final_record 提交实验记录。

    但它只走 Gate 0 PASS 这一条路径（下文 MAJOR 4）。

第 1 轮 MINOR 各项：

- **已修**：
  - 实验记录 Status 改为 NOT_TESTED（交 Review Gate）；
  - 文件名带开始时间；
  - first_load 经 check_device；
  - GPU 时钟段整体在 try/finally 内；
  - _name、g0、G08_REEVALUATIONS 已处理；
  - Pilot.write 文档写明例外；
  - 11-27 裁决改引 tasks/IMPL_C2_OWNER_MESSAGE.md；
  - 路径清单、负向检查已改；
  - fetch-model 先做 ST8；
  - 误导的 del 已删去；
  - e2e 测试检查实验记录；
  - 冻结后 formal 拒绝；
  - N 的哈希与第 3 步记录比对（没有测试）。
- **部分修复**：
  - 标记之前的异常转为 BLOCKED，但 TEST 文件的读取仍在 try 之外（MINOR 13）；
  - smoke 配置的重复没有修完（MINOR 10）；
  - 新增的 IMPL_C_REPORT 引用指向尚不存在的内容（MINOR 15）；
  - 录制不在送审树上（MINOR 18）。
- **登记**：--smoke 与子命令、崩溃的状态词、变异在工作区运行（这项风险已实际发生，MINOR 19）。

## 重点问题的结论（未验证）

- **防范对象内**：没有找到"评两次 TEST"或"ST10 不成立时评测 TEST"的路径。
  - begin 之前新增的检查（start_checks、已提交的第 2、3 步记录、checkpoint 文件、ST7、N 的哈希）都只会在 begin 之前多一次拒绝，没有改动 refuse_if_marker、st10_check、claim_checkpoint。
  - 标记之后的崩溃处理只写记录，然后重新抛出，不重试。
- **连续性检查**：不会挡住正常的 formal → test-generate → test-evaluate 顺序（同一个 --work 时，ledger 在第 2 步预检第一次加载模型时写入）。
- **冒烟第 8 步的保护**：完整覆盖生成器的前提 2、3（它们只读 HEAD 与工作区）。
- **stop_in_step 与 uncommitted**：
  - 只会提交结果目录下、本进程用 p.write 写出的文件（write_record 拒绝把 formal 记录写到别处），不会提交 <work> 中的文件。
  - 漏提交只发生在 commit_paths 失败时（MINOR 11）。
- **提交链测试的替换**：被替换的是设备、时钟/ledger、模型、训练步数、评测、读结果值的停止与 Gate 0 判定。要检验的 step_start、step_end、commit、step8_freeze、final_record 都是真实代码，没有被掩盖。但被替换的 before_run 使 ST7 事前判断的接线没有被执行；停止路径也没有覆盖。

## 问题

MAJOR | metrix/e1-pilot/src/metrix_e1/pilot.py:323-330（调用处 676） | [部分已验证：A 因子的数值见 reports/impl_c/c2b_smoke_records/step2_record.json:100-104、141（a_factor 6.75，other_runs 22）；乘法的用法未验证] run_seconds 对每一次训练都乘 A 因子，而 B17（compute.estimate_total_hours）只对 A 的 8 次运行乘 a_factor，其余 22 次的因子为 1。A 因子由 token 数决定、与模型无关，formal 下也应在 6.75 左右。所以 F、L、S、Y 每次训练的 ST7 事前估计约为实际训练时间的 6.75 倍。最后几次训练是第 6 步的 S、Y，那时累计时间最接近 4 小时，可能出现不必要的 ST7 停止（BLOCKED，需 Owner 决定） | `return (q["mean_step_s"] * self.contract.training.total_steps * q["a_factor"] + …)`；compute.py:223 `train_s = mean_step_seconds * tr.total_steps * (other_runs + a_runs * a_factor)` | run_seconds 接收 spec，只在 spec.arm == "A" 时乘 a_factor；补测试（A 与非 A 的估计值）与变异

MAJOR | pilot.py:185-193（使用处 1175、1182；对照 452-459、604-607、1195） | [未验证] TEST 评测的 ST7 事前估计对 16 个模型都只计 load_s。15 个 checkpoint 实际走 load_checkpoint：先 torch.load 整个 state dict，再加载 base_model，再 load_state_dict，这对应预检中的 reload_s（604-607 行正是这样测的），不是 load_s。估计因此少计 15 ×（reload_s − load_s），也没有任何余量。标记之后，循环内的 before_run() 只在已经超限时才停止，所以估计偏低时 ST7 会在标记之后触发，唯一一次 TEST 评测被消耗而且不完整（BLOCKED）——这正是 MAJOR 5 要防的情形。它在防范对象之外，所以列 MAJOR | `return (n["test_models"] * (pre["load_s"] + per_eval) + …)`；`model = base if name == TG.BASE_MODEL else p.load_checkpoint(...)`；预检 `fresh = p.base_model(); fresh.load_state_dict(torch.load(path, …)…)` 计为 reload_s | N 计 load_s，15 个 checkpoint 计 reload_s；是否加安全余量交 Review Gate；为 test_evaluation_seconds 的各组成部分补测试

MAJOR | pilot.py:1243、1251-1258（另见 testgate.py:103-106、398-400；tests/test_run_pilot.py:397-399） | [未验证] run_test_evaluate 用"工作区中有标记"判断 TEST 已开始评测，而不是"本进程的 begin 已经写了标记"。TEST 评测完成之后，Executor 若意外再运行一次 test-evaluate（防范对象中的情形）：begin 中的 refuse_if_marker 抛出 TestAlreadyEvaluated（不是 ProtocolStop），被新加的 `except Exception` 捕获；因为标记存在，代码写并提交一份 Status 为 BLOCKED 的实验记录，写的是 "crash after the TEST marker (TEST counts as evaluated)"，然后重新抛出。在它之前出现的 ProtocolStop（before_run(look_ahead) 的 ST7——此时已用时间更多、start_checks、checkpoint 文件检查）走另一个分支，同样提交 BLOCKED 记录。已提交的 TEST 结果是 PASS 或 PIPELINE_NOT_QUALIFIED，最新的实验记录却写 BLOCKED，也与 TestAlreadyEvaluated 的文档 "Carries no section 9 status: the pilot's status is the one of its result" 相矛盾。闸门本身仍拒绝第二次评测，所以不是 BLOCKER。e2e 测试的最后一步（397-399）正走这条路径；它复用同一个 Pilot（p.started 相同），会把第一次运行已提交的实验记录覆盖为 BLOCKED，而测试没有断言这一点 | `except Exception as e: … if not (p.root / TG.MARKER_REL).exists(): raise … status, actual, nxt = "BLOCKED", {"crashed": repr(e)}, …`；`with pytest.raises(TG.TestAlreadyEvaluated): P.run_test_evaluate(p)` | 改用本进程的状态判断（例如 begin 写出标记后设置的标志）；TestAlreadyEvaluated 单独处理（不写记录，或记为"拒绝"而不是 BLOCKED）；e2e 测试最后一步断言远端没有新增或被改写的 BLOCKED 记录

MAJOR | tests/test_run_pilot.py:412-422、326、519-521；reports/impl_c/c2_mutate_fix1.py:29-99 | [已验证：c2b_03_checks.txt:106-159 的 25 个变异都不涉及下列路径；其余未验证] 本次几项修复在 formal 下的关键路径没有测试或变异执行，而这些正是第 1 轮 MAJOR 2、3、5 的修复内容：(a) stop_in_step 在 formal 下提交该步记录——唯一的测试（412-422）是 smoke 模式，commit 是空操作；(b) final_record 把 p.uncommitted 与实验记录一起提交（1048-1050）——提交链测试只走 PASS 路径，结束时 uncommitted 为空，删去 `left` 不会使任何测试失败；(c) run_test_generate 的 ST10 实验记录（1111-1116）；(d) ST7 事前判断的接线，即 run_seconds、eval_seconds、look_ahead 有没有传给 before_run——e2e 与提交链测试都把 before_run 换成空函数，test_preflight_overhead_counts 只核算术；(e) N 的哈希与第 3 步记录不符时 BLOCKED（1185-1187） | `p = P.Pilot(M.smoke_mode(1), …)`；`p.before_run = lambda next_seconds=0.0: None`；MUTS 中没有涉及 `left`、`st10_over_limit`、`run_seconds()`、`look_ahead`、`n_sha` 的替换 | 补：formal 下 ST3（或 ST11）停止的提交链测试（克隆 + 裸远端，断言该步记录、已写的训练记录与实验记录都已推送、工作区干净）；test-generate 的 ST10 记录测试（已提交一份超限的 ST10 记录、替换子进程）；对 before_run 收到的 next_seconds 的断言；N 哈希不符的测试；以及对应的变异

MINOR | pilot.py:1182-1183、1240-1245（docstring 1229-1231） | [未验证] test-evaluate 在标记之前遇到的 ST7（本次新增的事前判断）、ST8、ST9（整批作废）、ST12 都按"拒绝"处理，不写第 10 节的实验记录，只有 ST10 例外。而 ST7"停并报告进度"、ST9"整批作废"都是协议停止。CF30 已把"标记之前的拒绝不写记录"交 Review Gate；本次新增的 ST7 事前停止也走这条路径 | `if not (p.root / TG.MARKER_REL).exists() and code != "ST10": … return False, …` | 在交 Review Gate 的待决项中写明 ST7/ST8/ST9 也走此路径；或像 ST10 一样，对 stop 码不为 None 的协议停止写记录

MINOR | pilot.py:323-334 | [未验证] 估计量的两处小偏差，方向相反、量级小：(1) run_seconds 没有计入 save_checkpoint 中的 FZ.file_sha256（448 行；预检测了 file_hash_s，却没在这里用）；(2) eval_seconds 在第 7 步（792）之前用 load_s，而随后的 load_checkpoint 对应 reload_s；在 train_and_evaluate 中（687）模型已经在内存里，又多计了一次 load_s | `+ 2 * q["hash_s"] + q["save_s"] + q["reload_s"] + q["load_s"] + q["dev_evaluation_seconds"]` | 补上 file_hash_s；第 7 步用 reload_s

MINOR | pilot.py:1101-1126 | [未验证] run_test_generate 的两个问题：(1) 不设置 p.code_commit，ST10 实验记录 "Environment (CPU/GPU, commit, seed)" 中的 code_commit 为 None，而第 10 节要求写 commit；(2) st10_over_limit 读的是任何已提交的 ST10 记录：若之前一次生成已超限，再运行 test-generate（子进程会被 refuse_if_st10_record 拒绝）也会再写一份"本次运行 ST10"的记录 | run_test_generate 中没有 `p.code_commit = TG.code_commit(p.root)`；`over = st10_over_limit(p)` 不区分记录是不是本次子进程提交的 | 设置 code_commit；只在子进程运行前 HEAD 没有 ST10 记录、运行后有时才写记录

MINOR | pilot.py:315-318（ledger 的写入见 389-390、577-579） | [未验证] device ledger 在第 2 步预检第一次加载模型时才写入，第 1 步记录却在第 1 步结束时就已提交。formal 若在两者之间停止（第 2 步开始时的 ST12、data.verify 崩溃、ST1 等），之后用同一个 --work 重跑会被 start_checks 拒绝，消息是 "continue only with that run's --work"，而它正是那个 --work。失败方向安全，重跑本来也由 Owner 决定 | `if TG._blob(self.root, "HEAD:%s" % STEP1_RECORD_REL) is not None and not self.ledger.path.exists():` | 消息写明两种可能；或改以"已提交第 2 步之后的记录"为条件；登记

MINOR | pilot.py:436-437、309-321 | [未验证] 第 1 轮 MAJOR 11 (a) 未修：同一个 --work 重跑时，预检与 N 的评测照常运行（GPU 时间计入 ST7），第 1–3 步的记录也会再提交一次，直到第 4 步第一次保存才因 checkpoint 已存在而 IMPLEMENTATION_FAIL。说明中交 Owner/RUNBOOK 处理 | `if path.exists(): raise ImplementationFail("checkpoint %s exists: each run is trained once" % path)` | start_checks 在 ckpt_dir 中已有 checkpoint 时，于第 1 步之前拒绝；登记

MINOR | pilot.py:1074-1080 | [未验证] smoke_model_config 仍然自己读 config.json 并重复覆盖循环，没有用新抽出的 smoke_config（475-481）。DEFERRED_MINORS 1.32 CF18 写的是"已修" | `cfg = AutoConfig.from_pretrained(...)`；`for k, v in SMOKE_MODEL_OVERRIDES.items(): setattr(cfg, k, v)` | 改为 `cfg = smoke_config(p.model_dir)`

MINOR | pilot.py:266-274 | [未验证] commit 在调用 commit_paths 之前就把 paths 从 uncommitted 中移除。commit_paths 因暂存或提交失败而 BLOCKED 时，这些文件不再由 final_record 补交（final_record 的 precommit 多半也会失败，影响小） | `for x in paths: if x in self.uncommitted: self.uncommitted.remove(x)` 位于 `TG.commit_paths(...)` 之前 | 提交成功之后再移除

MINOR | pilot.py:1048-1050、815、838 | [未验证] uncommitted 也包括 Gate 0 记录与冻结记录，而它们是 TEST 生成器的前提 2、3。第 7 或第 8 步若在 p.write 之后、step_end 提交之前崩溃，final_record 会把它们随实验记录一起提交。内容在写出之前已校验（freeze_record_problem），时间窗口很小；属范围外，登记 | `left = [x for x in p.uncommitted if x not in paths]` | 登记；或 final_record 对 Gate 0 与冻结记录不补交、只报告

MINOR | pilot.py:1155-1158 | [未验证] CF15 只覆盖了已提交记录与 checkpoint 文件。p.load_data() 和读 <work>/test 中 TEST 文件的 FZ.read_jsonl 仍在 try 之外，--work/test 缺文件时以 traceback 退出（发生在标记之前，不会评测） | `data = dict(p.rows, **{n: FZ.read_jsonl(tdir / n) for n in D.TEST_FILES})` 位于 `try:` 之前 | 一并转为 BLOCKED

MINOR | pilot.py:267、315、319、853（对照 533） | [未验证] pilot.py 有四处调用 testgate 的私有函数 `_blob`，第 1 步又用 FZ.git_blob 做同一件事 | `TG._blob(self.root, "HEAD:%s" % r)`；`FZ.git_blob(p.root, "HEAD", rel)` | 统一用一个公开函数

MINOR | pilot.py:58、804-805、982、1007、1038；reports/DEFERRED_MINORS.md:554 | [已核对仓库文件] 这些位置把待决事项指向 reports/IMPL_C_REPORT.md 中 C2 的"待 Review Gate 决定"第 1–5 项，但该文件中只有 C1 的待决项（IMPL_C_REPORT.md:90-94、148-158），没有 C2 节。Owner 消息要求把 2026-11-27 的裁决"记入 IMPL_C_REPORT.md"，也还没写入（与第 1 轮同类问题） | `whether ST11 should read the sum is for Review Gate (reports/IMPL_C_REPORT.md)` | 在本提交或紧随其后的报告提交中写入 C2 节与该裁决

MINOR | metrix/e1-pilot/reports/impl_c/c2b_checks.sh:3 | [已核对] 用法行写的文件名是 c2_checks.sh | `#   bash metrix/e1-pilot/reports/impl_c/c2_checks.sh OUTFILE PYTHON INPUTS SCRATCH` | 改为 c2b_checks.sh

MINOR | metrix/e1-pilot/reports/impl_c/c2_mutate_fix1.py:111-114 | [已核对] parse 中"成对替换列表"的分支没有任何变异使用（25 个都是单对替换），是死代码 | `pairs, tests = (rest[0], rest[1]) if isinstance(rest[0], list) else ...` | 删去，或注明保留原因

MINOR | reports/impl_c/c2b_03_checks.txt:25、180；c2b_04_smoke.txt:5、219 | [已验证] 录制时的写树是 6071ea72，送审树是 b40224e6（tree.txt；多出的是证据文件）。两者之间的联系只有两样：代码 diff 的 sha256 3920af52（我无法复算），以及 pilot.py 的 blob a6633d1（c2b_01b_restore_after_kill.txt:5 与 input_code.diff 的 index 行一致）。tests/test_run_pilot.py 的 blob b435d76 没有出现在任何原始输出中 | `6071ea727fec6bf2eedff62f184a02bfc1a4ac64` 对 `b40224e68d1d…` | 在 STATE 中加入 src/、tests/、run_pilot.py 的 `git ls-files -s`，或由 data-auditor 复算代码 diff 的 sha256

MINOR | reports/impl_c/c2_mutate_fix1.py:130-142；c2b_01b_restore_after_kill.txt:3-22 | [已验证] CF29 的风险已经发生：被杀的变异进程把 `if False:` 留在了受跟踪的 pilot.py 中，而当时并行运行的 c2b_02 冒烟读的是同一个工作区（c2b_02 已作废；c2b_04 在恢复之后单独运行）。runner 仍然直接改写受跟踪的源文件 | `path.write_text(s, encoding="utf-8")` … `finally: path.write_bytes(orig)` | 在临时克隆中运行变异；登记

MINOR | pilot.py:1251-1258 | [未验证] 标记之后的崩溃处理捕获的是 Exception，不包括 KeyboardInterrupt。操作者在评测中途按 Ctrl-C 时不会写记录。属范围外，登记 | `except Exception as e:` | 登记；或对 BaseException 先写记录再重新抛出

MINOR | pilot.py:587-589 | [未验证] 预检中的非有限值记为 IMPLEMENTATION_FAIL（代码注释写 "as for a control"）。但预检的配置（F 的第一个配置）在当时既不是选定配置，也不是对照，协议 ST6 对这种情形只写"停该次"。已交 Review Gate（CF6），登记 | `STP.st6(p.fz, e.values or [float("nan")], "preflight %s: %s" % (spec.name, e), True)` | 按 Review Gate 的裁决处理

MINOR | pilot.py:1101-1117 | [未验证] test-generate 不做 start_checks。若用另一个 --work 运行，TEST 文件会写到那个 --work，ST10 记录照常提交；之后用原来 --work 的 test-evaluate 读不到 TEST 文件，而 TEST 不能再生成。属范围外，登记 | run_test_generate 中没有 `p.start_checks(...)` | test-generate 也检查 device ledger（确认是同一个 --work）

结论：PASS
