# code-reviewer, C2 work commit, round 1 (staged tree b80c9062134db0d950cd9786209862f69ffda06c, parent f8139f9)
# invocation text: code-reviewer_prompt.txt; final report extracted unchanged by reports/round6/review_extract.py
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 2 段（C2）工作提交，第 1 轮。暂存树 b80c9062，父提交 f8139f9。
依据：input_code.diff、仓库中的代码、METRIX_E1_PROTOCOL.md（第 0、7、8、9、10、11 节）、IMPLEMENTATION_TASK_ORDER_V1.md、IMPL_C1_RULING.md、IMPL_C2_OWNER_MESSAGE.md、DEFERRED_MINORS。我没有运行任何代码，只用了 Read、Grep、Glob。"已验证"指引用了暂存的原始输出（路径与行号已写明）或仓库中的文件；其余判断都是读代码得出的，标为"未验证"。

## 说明核对

**与原始输出一致（已验证）：**
- pytest 312 passed：c2_05_checks.txt:108。
- 变异 17 个全部 CAUGHT，前后树哈希 EQUAL：c2_05_checks.txt:111-148。
- 冒烟结果：
  - 30 次训练，每次 3 步：c2_06_smoke.txt:86。
  - ST11、ST3 记为 would stop 后继续：c2_06_smoke.txt:14、27。
  - Gate 0 为 NOT_TESTED：c2_06_smoke.txt:60、85。
  - 第 8 步生成器 exit 1，--out 未创建，没有 TEST 文件：c2_06_smoke.txt:63、212。
  - 三个 LABEL.txt：c2_06_smoke.txt:213-215。
  - 每次训练保存、重载后 state_sha256 不变：c2_06_smoke.txt:20-57；例 c2_smoke_records/training_runs/L-L6-seed202.json:15、22。
- c2_02 误写的记录为 BLOCKED / ST8：c2_02_stray_experiment_record_formal.json:802、808；c2_02_checks_superseded.txt:155-156。

**与代码一致（未验证）：**
- formal 没有 --steps，build_mode 只对 smoke 构造缩减步数。
- 第 1–7 步与冒烟第 8 步开始时都做 ST12、ST13 扫描和提交前提；第 2 步起含 data.verify（CA23）。
- 第 1 步只写 STEP1_FIELDS，写后重新 ST12，与 HEAD 比较决定是否提交。
- checkpoint 保存→重载→比较哈希，DEV 评测的是重载后的模型（B25、C1 裁决第 3 项）。
- S、Y 继承 F 的配置（train.seed_runs）。
- test-evaluate 的顺序与结果内容如说明所述，结果中没有题目文字和 general_* 行（CD13）。
- generate_test 唯一的调用方是 main，run_pilot 以子进程运行 main（CD5、CE5）。
- gate.py 重构前后数值不变。
- tests/test_run_pilot.py 有 14 个测试。
- 在防范对象内，没有找到"评两次 TEST"或"ST10 不成立时评 TEST"的路径。

**与说明不一致：**
- "标记存在之后的任何停止都写实验记录"只对 ProtocolStop 成立，崩溃不写（MAJOR 4）。
- final_record 文档列出的"第 1 步前停止"情形不全（MAJOR 1）。
- formal 的第 8 步（冻结记录）前没有 ST12（MAJOR 8）。

**关于第 (3) 问：** c2_mutate.py 只运行所指名的测试，所以它只能证明这些测试会失败，不能证明"只由它们拦下"。就检验目的而言这已足够。有两个变异是因为间接原因被拦下的，结果仍然成立：
- "checkpoint: label not checked"：在 CPU 上是 first_load 的 TypeError 让测试失败（见 MINOR m4）。
- "formal: no device check before step 1"：是被 monkeypatch 的提交前提抛出的 AssertionError 让测试失败。

## 问题

MAJOR | metrix/e1-pilot/src/metrix_e1/pilot.py:902-905（另见 190、261-264、895-901） | [未验证] formal 在第 1 步开始前停止时，实验记录只写到 <work>，不提交。这与协议第 10 节"每次运行(含被停止的)提交一份"不相容。走这条路径的不只是 docstring 列出的三种情形（ST8、代码未提交、第 1 步提交前提），还有 A100 上真实发生的 ST8（如 40GB 卡）、第 1 步开始时的 ST12（BLOCKED）和 ST13（IMPLEMENTATION_FAIL、整批作废）。Pilot.__init__ 中的 ST12（190 行）失败时连 <work> 中的记录也没有。另外，c2_02 的事故说明开发容器也能通过远端与分支检查，所以仅靠 check_commit_preconditions 区分不出"不是 Pilot 的机器" | `if p.mode.formal and command == "formal" and not p.step1_started:` … `outside_repo=True`；`self.step1_started = True` 在 st12、st13_scan、precommit 之后；`self.fz = STP.st12(self.root)` 在 run_gate 之外 | 交 Review Gate 决定：是接受"第 1 步前的停止由操作者按 RUNBOOK 手工提交 <work> 中的记录"，还是区分"非 Pilot 机器"（不写仓库）与"Pilot 机器上的 ST8/ST12/ST13"（写入并提交）。同时补全 docstring 列出的情形，并让 __init__ 中的 ST12 也产生记录

MAJOR | pilot.py:962-970、1064-1066；test_data.py:200-203 | [未验证] ST10（协议第 11 节："停止;不评测 TEST;BLOCKED;报告 Owner"）发生时没有任何第 10 节实验记录：
- test-generate 不写实验记录。TEST 部分超限时，test_data.main 只打印并 exit 1。
- test-evaluate 在标记写入前被 begin 中的 st10_check 拦下（L6 计数不一致或超限）时，按设计不写记录。

结果是 Pilot 的 BLOCKED 状态不在任何实验记录中，而 formal 那份记录的 Status 是 PASS | `if not (p.root / TG.MARKER_REL).exists(): ... return False, getattr(e, "status", None)`；`passed = P.run_test_generate(p) == 0` | 交 Review Gate：至少对 ST10 这类协议停止写并提交一份实验记录，与操作性拒绝（检出不对、文件缺失）分开处理

MAJOR | pilot.py:476-479、534、553-554、636-637、876 | [未验证] formal 下 ST1、ST11（第 2 步）、ST2（第 3 步）、ST3（第 4 步）都在 step_end 之前抛出，造成三个后果：
- 该步记录既不写也不提交。
- 已写进 results/ 的 details/N_dev.json、F 的 6 个 training_runs 记录及其 details 留在工作区，没有提交。
- 实验记录的 Actual 只有 `{"stopped": str(e)}`。

ST2 的消息不含数值（stops.py:50 "N does not satisfy G0.3"）；ST11 的消息只有总时长。协议第 8 节第 2 步要求记录的每步耗时、tokens/s、峰值显存，恰好在 ST11 触发、需要"报告 Owner"时丢失 | `STP.st1(p.fz, report)` 在 `p.step_end(2, …)` 之前；`out["st11"] = … p.stop_check(STP.st11, …)` 在 preflight() 内部；`stop = p.stop_check(STP.st2, p.fz, ok)` 在 `p.step_end(3, …)` 之前；`actual, nxt = {"stopped": str(e)}, …` | 抛出之前先写并提交该步记录（leakage 报告、预检全部输出、G0.3 数值、阳性对照数值、已完成的训练记录），或把这些值写进实验记录的 Actual

MAJOR | pilot.py:1062-1071（docstring 1054-1057） | [未验证] 标记提交之后若发生非 ProtocolStop 异常（CUDA OOM、torch.load 失败、OSError、KeyError 等），不写实验记录，直接以 traceback 退出。此时 TEST 已"视为已评"、状态应为 BLOCKED，却不进任何记录。这与 docstring "the experiment record is written and committed whatever happens after"、说明"标记存在之后的任何停止都写实验记录"以及第 10 节都不符 | 只有 `except (ProtocolStop, TD.PreconditionFailed) as e:`；run_gate 有 `except Exception as e: crash = e`（879-882），run_test_evaluate 没有对应的处理 | 标记存在后捕获 Exception，写并提交记录（BLOCKED、崩溃信息）后再重新抛出；补一个"评测中途注入 RuntimeError"的测试与变异

MAJOR | pilot.py:524、569、578、1010、1019 | [未验证] 协议第 8 节"任何一步若会使累计时间超过上限,按 ST7 停下"要求事前判断，但代码只在训练前做了预估判断，而且预估只含训练时间（不含该次 DEV 评测和 checkpoint 开销）。N 的评测、G0.8 的第二次评测、TEST 评测之前都是 next_seconds=0。
- 最关键的是 test-evaluate：begin 之前只核对已用时间。若剩余预算不够评完 16 个模型，ST7 会在标记提交后中途触发，唯一一次 TEST 评测被消耗且不完整（BLOCKED、视为已评）。
- 按防范对象这属于范围外，所以列 MAJOR | `p.run_estimate_seconds = summ[...] * total_steps * parts["a_factor"]`；begin 之前和循环内的 `p.before_run()` 都不带参数 | begin 之前用已提交的第 2 步预检记录估计整个 TEST 评测（16 次加载、哈希、评测 × test/dev 题数比），按 ST7 判定；训练前的预估加上该次评测与 checkpoint 开销

MAJOR | pilot.py:875、544、682、493、1021→1067 | [未验证] train.NonFinite（status 为 None）在 train_and_evaluate 之外发生时，不经过 stops.st6：
- N 的 DEV 评测（对照）、G0.8 第二次评测（选定配置）、预检中的非有限值，在 run_gate 中被记为 NOT_TESTED。
- TEST 评测中的非有限值被记为 BLOCKED。

协议 ST6 规定发生在选定配置或对照上时为 IMPLEMENTATION_FAIL | `status = e.status or "NOT_TESTED"`；`status = getattr(e, "status", None) or "BLOCKED"`；train.py:44 `super().__init__("ST6", None, message)` | 在这些调用处捕获 NonFinite 并调用 `STP.st6(..., selected_or_control=True)`；补测试

MAJOR | pilot.py:689、716（剔除路径见 589） | [未验证] 对搜索中按 ST6 剔除的配置，代码的处理前后不一致：
- 第 7 步 G0.2 的输入写死为 `all_finite: True, nonfinite: []`，不反映 p.excluded。
- 若 Gate 0 仍为 PASS，step8_freeze 对被剔除的运行取 `runs[s.name]["state_sha256"]` 会 KeyError（剔除时返回的结果没有这个键）。formal 以崩溃结束，冻结记录无法提交，TEST 永远到不了。
- 协议第 7 节允许剔除后照常选择。两种读法——"剔除的运行违反 G0.2，Gate 0 不通过"，或"不违反，冻结记录要处理缺失的 checkpoint 哈希"——代码都没有一致地实现 | `inp = {"leakage": leakage, "all_finite": True, "nonfinite": [], …}`；`checkpoints = {s.name: runs[s.name]["state_sha256"] for s in plan}`；剔除时 `return {"spec": spec, "finite": False, "record": …}` | 交 Review Gate 决定 G0.2 对被剔除配置的读法；按裁决把 p.excluded 传给 G0.2，或在冻结前给出明确的协议停止，而不是 KeyError

MAJOR | pilot.py:710-725 | [未验证] formal 第 8 步的第一部分（提交冻结记录）开始前没有执行 ST12（PROTOCOL_FROZEN、四个冻结文件、inputs 与 data.verify），也没有 ST13 扫描，只有提交前提和内容哈希。这违反实施指令第 5 节"每步开始前执行 ST12"。另外 formal 不写第 8 步的记录 | step8_freeze 中没有 `p.step_start(8)` 或 `STP.st12(...)`，只有 `p.precommit("the freeze record")` 和 freeze_record_problem 中的 `p.fz.check_data_dir(p.data_dir)` | 冻结记录之前调用 step_start(8)（至少调用 STP.st12(root, inputs, data_dir) 与 st13_scan）

MAJOR | pilot.py:728-748；test_data.py:162-186 | [未验证] 冒烟第 8 步的"拒绝"依赖仓库状态。子进程 test_data.main 读的是本包所在的仓库（`check_preconditions(None, …)`）。
- 场景：在 Pilot 的检出上，formal 已提交 Gate 0 PASS 与冻结记录、test-generate 尚未运行，此时运行 smoke。四项前提和提交前提都成立，冒烟会真的生成 TEST（写到 <work>/step8_refused_out），并提交、推送 formal 的 ST10 记录。此后正式的 test-generate 会被 refuse_if_st10_record 拒绝。
- 这违反实施指令第 7 节"第 8 步只测试 TEST 生成器拒绝运行，不生成任何 TEST"和 metrix/CLAUDE.md 第 7 节，也破坏冒烟与正式的隔离。
- 防范对象只针对评测，这是生成，属范围外，所以列 MAJOR 而不是 BLOCKER | `r = subprocess.run(test_generate_command(p, out), cwd=str(p.root), …)`；test_data.py:162 `fz, auth = check_preconditions(None, a.inputs, a.data)`，随后 175-186 生成文件并 commit_paths | smoke 第 8 步开始前，若 HEAD 上已有 formal 的 Gate 0 或冻结记录就拒绝运行该子进程（或改在没有这些记录的临时克隆上运行），并补测试

MAJOR | pilot.py:516-534（模块说明 43-48）；interpretations.py:101-107 | [未验证] 这项改动没有改变 B17 本身的计算（b17_estimate_hours 仍单独列出），但改变了 ST11 读的量：从 B17（已裁决 ACCEPTED）变为"B17 + checkpoint 开销"。
- 两者之和总是 ≥ B17，ST11 只会更严；但 B17 的文字没有修改，也没有登记新解释，而每份实验记录都写入 B17 原文。记录所写的估计定义与 ST11 实际使用的不一致。
- CA21 只要求计入 state_sha256 的耗时；模型加载、保存、重载是另外加的。
- 仍有漏计：每个 checkpoint 文件的 FZ.file_sha256（formal 30 次，test-evaluate 再 15 次，按协议参数量每个约 6.9 GB），以及 begin 对 N 多算的一次 state_sha256 | `total = hours + overhead / 3600.0`；`p.stop_check(STP.st11, p.fz, p.contract, total)`；375 行 `"file_sha256": FZ.file_sha256(path)`；1006 行 `got = FZ.file_sha256(...)`；1012 行 `TG.begin_test_evaluation(fz, auth, data, T.state_sha256(base))` | 交 Review Gate：把扩展后的估计登记为新解释，或修订 B17 后重新裁决；把文件哈希和 begin 的那次哈希计入

MAJOR | pilot.py:281、359-360、196-197；testgate.py:268-272 | [未验证] formal 重跑不可行，或会破坏簿记。重跑的场景包括崩溃之后、ST7 经 Owner 延长上限之后、ST9 换机"从第 3 步重新开始"：
- (a) 同一个 --work：第一次训练就因 checkpoint 已存在而 ImplementationFail，而此前预检和 N 已经用掉了 GPU 时间。
- (b) 换新的 --work：device_ledger.json 与 gpu_clock.json 从头开始，ST9 不再与首次记录的设备名比对，ST7 的累计从 0 算。
- (c) 评测是确定性的，details/N_dev.json、*_dev.json、*_dev_g08.json、gate0_record.json 会与已提交版本逐字节相同。`git add` 不暂存这些文件，commit_paths 要求"暂存路径恰为这些路径"不成立，结果 BLOCKED。第 1 步对 manifest 已按 HEAD 处理，其余记录没有 | `if path.exists(): raise ImplementationFail("checkpoint %s exists: each run is trained once" …)`；`self.ledger = CP.DeviceLedger(self.work / DEVICE_LEDGER)`；testgate.py:270 `if add.returncode != 0 or staged != sorted(rels):` | 由 Review Gate 或 RUNBOOK 定重跑方式。代码上至少：只提交与 HEAD 不同的路径；ledger 与 clock 能跨 --work 延续，或在没有既有 ledger 时拒绝以续跑方式运行

MAJOR | tests/test_run_pilot.py（全文件）；pilot.py:270-284、710-725、906-916 | [已验证：c2_mutate.py 与 c2_05_checks.txt:111-146 中没有针对这些路径的变异；其余未验证] formal 独有的路径没有任何测试或冒烟执行过：
- 每步的 commit_paths 提交（step_end）。
- step8_freeze，即冻结记录，它是 TEST 生成器的前提 3。
- formal 命令的实验记录提交。

冒烟走的是 commit 的空操作分支和 step8_smoke_refusal；e2e 测试的冻结记录由夹具直接构造。这些代码第一次运行将是在 A100 上花掉数小时 GPU 时间之后 | `def commit(self, …): if not self.mode.formal: return None`；test_run_pilot.py:334 `sel_sha = write(root, R.SELECTION_FREEZE_REL, R.selection_freeze_record(...))` | 仿照 eval_clone，在临时克隆加裸远端上，把训练和评测替换为小模型，跑通 formal 第 1–8 步的提交链（含 step8_freeze 与 freeze_record_problem）；为冻结记录中的哈希来源和提交路径加变异

MINOR | pilot.py:857-860 | [未验证] formal 命令在 Gate 0 PASS 时，实验记录的 Status 写为 "PASS"。第 9 节 PASS 的定义是 Gate 0 与 T1–T3 全部满足；B14 只接受 gate0_status 使用 PASS，不覆盖实验记录的 Status 字段 | `return "PASS", actual, ("Owner decides on TEST generation …` | 记录中明确写"Gate 0 PASS；Pilot 状态待 TEST"，或交 Review Gate 定这个字段的取值

MINOR | pilot.py:822 | [未验证] 实验记录文件名固定，重跑会覆盖先前的记录。例如评测中途停止后再运行一次 test-evaluate，这次被 refuse_if_marker 拦下的 BLOCKED 记录会覆盖真正评测那次已提交的记录（git 历史中仍保留） | `name = "experiment_record_%s.json" % command` | 文件名加上 Experiment ID，或拒绝覆盖

MINOR | pilot.py:999-1006 | [未验证] 标记写入之前，读取已提交记录时抛出的 R.NotCommitted（不是 ProtocolStop）和 KeyError 不被 run_test_evaluate 捕获，以 traceback 退出，而不是 BLOCKED 拒绝。此时没有发生评测，影响仅在报告形式 | `run_rec, _ = R.committed_json(...)`；`except (ProtocolStop, TD.PreconditionFailed)` | 转为 ProtocolStop BLOCKED

MINOR | pilot.py:309 | [部分已验证：c2_05_checks.txt:113-114 显示 CAUGHT；TypeError 这一原因未验证] formal 模式在没有 CUDA 时，first_load 以 TypeError 失败（device_info() 返回 None）。正常流程中 ST8 会先拦下，但变异 "checkpoint: label not checked" 在 CPU 上正是由这个 TypeError 使测试失败的 | `name = CP.device_info()["name"]` | device_info() 为 None 时抛 ST8；测试断言更具体的失败原因

MINOR | pilot.py:1010-1016 | [未验证] test_evaluate 在 try/finally 之外打开了 GPU 时钟段（begin 之前的 before_run、base_model）。若这里出现非 ProtocolStop 异常，时钟不关闭，下一个进程按"未关闭的段计到现在"处理，多计了空闲时间（只会多计，不会少计） | `p.before_run()` 与 `base = p.base_model()` 在 `try:` 之前 | 让 try/finally 覆盖整个函数

MINOR | pilot.py:751-752 | [未验证] `_name` 的参数 p 没有使用，且重复了 RunSpec.name 的格式（train.py:64） | `def _name(p, arm, config_id, seed): return "%s-%s-seed%d" % …` | 改用 RunSpec.name 或共享同一个格式

MINOR | pilot.py:714 | [未验证] 变量 `g0` 未使用 | `g0, g0_sha = R.committed_json(p.root, R.GATE0_RECORD_REL)` | 改为 `_`

MINOR | pilot.py:87、160-162 | [未验证] `G08_REEVALUATIONS = 3` 是可由协议推出的数，却写成常量，再在运行时比对 | `G08_REEVALUATIONS = 3` | 直接用 len(contract.training.training_seeds)

MINOR | pilot.py:338-339 与 935-941 | [未验证] smoke_model_config 重复了 base_model 中的覆盖循环 | 两处都是 `for k, v in SMOKE_MODEL_OVERRIDES.items(): setattr(cfg, k, v)` | 抽成一个函数

MINOR | pilot.py:823-827；219-221；30-35 | [未验证] outside_repo 分支绕过 record.write_record，在正式结果目录之外写了 mode=formal 的记录。Pilot.write 的文档（"a formal record goes nowhere else"）和模块文档（formal 记录与每次运行的实验记录都在仓库结果目录）因此不再准确 | `path = p.work / name` … `path.write_text(json.dumps(rec, …))` | 在文档中写明这个例外，或给这份记录加非 formal 的标记

MINOR | pilot.py:7、899-901 | [已核对仓库文件] 文档引用了尚不存在的内容：
- 第 7 行写 2026-11-27 裁决在 reports/IMPL_C_REPORT.md，但该文件中没有 "2026-11-27"，只有第 92 行提出的请求。
- 899-901 行引用的 RUNBOOK_A100.md 第 4 节不在本次提交中 | `Review Gate's ruling of 2026-11-27 (reports/IMPL_C_REPORT.md): item 1` | 改为引用 tasks/IMPL_C2_OWNER_MESSAGE.md，或在同一提交中写进报告

MINOR | tests/test_run_pilot.py:122 | [未验证] 被检查的路径包含 formal 从不写出的 step8_record.json | `for k in range(1, 9)` | 与实际写出的路径一致

MINOR | tests/test_run_pilot.py:146-147 | [未验证] 这个负向检查直接对本仓库的 results 目录调用 R.write_record。若 write_record 的拒绝逻辑回归，测试会在本仓库工作区写出 metrix/e1-pilot/results/x.json | `R.write_record(dict(rec), p.root / R.FORMAL_RESULTS_REL / "x.json", p.root)` | 用 tmp_path 作为 repo_root

MINOR | metrix/e1-pilot/run_pilot.py:40 | [未验证] 实施指令第 7、11 节写的是 `run_pilot.py --smoke`，实现为子命令 `smoke` 加 `--steps` | `a = sub.add_parser("smoke")` | 在 RUNBOOK 与报告中写明，或交 Review Gate 确认

MINOR | run_pilot.py:57-62；pilot.py:425-432 | [未验证] fetch-model 下载权重之前不做任何主机或设备检查，本阶段红线 2（不下载权重文件）只能靠操作者自觉 | `for name, sha in P.fetch_model(FZ.load(), a.inputs).items():` | 下载之前先做 ST8 设备检查

MINOR | pilot.py:364 | [未验证] save_checkpoint 中的 `del model` 并不能释放训练后的模型，因为调用方到 577 行才释放。重载时显存中同时有训练后的权重与梯度、加载的 state dict 和重载的模型。80 GB 下足够，但代码读起来像已经释放 | 调用方仍持有引用时执行 `del model`、`gc.collect()`、`empty_cache()` | 由调用方负责释放，或删去这段误导的释放代码

MINOR | tests/test_run_pilot.py:348-376 | [未验证] e2e 测试只检查结果文件中没有合成题目文字，没有检查已提交的 test-evaluate 实验记录 | `blob = git(remote, "show", "main:%s" % TG.RESULT_REL)` | 对实验记录做同样的断言

MINOR | stops.py:162-164；pilot.py | [未验证] 冻结记录提交后 st13_scan 不再扫描，formal 也没有"已冻结则拒绝运行"的检查。因此 formal 可以在 TEST 已生成之后再次运行，重新训练、选择，并覆盖 Gate 0 与冻结记录。之后的 TEST 评测会因 ST10 记录绑定旧授权而被拒（testgate.py:363-365），不构成评两次；属防范对象以外 | `R.committed_record(...)` 后 `return []` | 登记；formal 在已有冻结记录时拒绝运行

MINOR | pilot.py:1012 | [未验证] TEST 时 N 的哈希只取这次加载的 base 模型，没有与第 3 步记录的 N 的 state_sha256（p.base_sha）或权重文件哈希比对 | `T.state_sha256(base)` | begin 之前与已提交的第 3 步记录比对

MINOR | pilot.py:881 | [未验证] 崩溃记为 NOT_TESTED。第 9 节 NOT_TESTED 的定义是"未运行,或在没有违反任何条件的情况下提前停止"，崩溃不明确属于其中任何一种 | `status, actual, nxt = "NOT_TESTED", {"crashed": repr(e)}, …` | 登记，交 Review Gate 定崩溃使用的状态词

MINOR | reports/impl_c/c2_05_checks.txt:28-30、170-172；c2_06_smoke.txt:4-6、218-220 | [已验证：两份原始输出与 tree.txt] 原始输出是在 write-tree 05a76f57 上录制的，送审树是 b80c9062（加入了证据文件）。没有任何一份原始输出显示 b80c9062 中的 src/、tests/、run_pilot.py 与 05a76f57 相同；c2_05 只给出 05a76f57 下代码 diff 的 sha 222c9375… | `05a76f57fc9962d3dc0b42a0e98186f9a6738106`，而 tree.txt 为 `b80c9062…` | 提交前在最终树上再录一次 STATE（含代码 diff 的 sha）

MINOR | reports/impl_c/c2_mutate.py:102-114 | [已验证：c2_05_checks.txt:147 EQUAL] 变异直接改写本仓库工作区中受跟踪的源文件，在 finally 中恢复并比对哈希；进程若被强制终止，工作区会留下变异后的代码 | `path.write_text(s, encoding="utf-8")` … `finally: path.write_bytes(orig)` | 登记；可改在临时克隆中运行

结论：PASS
