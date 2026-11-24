# code-reviewer final report, Implementation stage B, round 2: staged work commit after the round-1 fixes (parent 0bc0eecf1f684773248c198afb94e7026dcfb16d); invoked 2026-11-23 08:06 UTC (background); invocation text: code-reviewer_prompt_round2.txt; input: review_input_round2.diff, review_fixes_round2.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a1e76ac5738a4607c.jsonl)
---
code-reviewer 第 2 轮审查：Metrix E1-PILOT Implementation 阶段 B（暂存、未提交；父提交 0bc0eecf1f684773248c198afb94e7026dcfb16d）

结论：PASS。没有 BLOCKER，但有 2 条新的 MAJOR：
1. 评测中出现非有限值时，按本轮的设计 stops.st6 不会触发。
2. 新增的 TEST 评测入口没有任何前提守卫。

审查方式：
- 先读了仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md。它的 tools 行（Read, Grep, Glob）与已加载的定义一致。
- 只用 Read、Grep、Glob 读暂存后的工作区文件、两份 diff 和已暂存的原始输出，没有执行任何命令（我没有 Bash）。
- 读代码得出的判断标『未验证』；引用 /home/user/OpenMythos/metrix/e1-pilot/reports/impl_b/t6_fix_round.txt（下称 t6）行号的判断标『已验证』。

## 一、第 1 轮各项核对

**MAJOR 1（预检模式隔离）：已修，正确。**
- gate.py:39-41、171、206：judge 与 judge_test 拒绝 preflight。
- train.py:371-373：预检步数必须等于 contract.preflight_steps。
- evaluate.py:84-88、305：非冒烟模式拒绝在 CPU 上评测。
- mode.py 的文档和字段名 shortened_steps 已更正。
- 测试通过：t6:116、130、274『已验证』。
- 遗留："第一个配置"没有核对，见 MINOR。

**MAJOR 2（G0.8）：已修，正确。**
- gate.py:184-185 要求 checkpoint 的种子集合恰好等于三个训练种子。
- 新增"只有 2 个种子""出现种子 404"两个反例，t6:126『已验证』。

**MAJOR 3（NonFinite）：已修，但有问题。**
- NonFinite 不再带状态（train.py:43-45）；errors.py:19 只对 ST6 允许 status 为 None。
- 但评测路径抛出的 NonFinite 不带数值，st6 对它不起作用，见新 MAJOR 1。

**MAJOR 4（pending() 未被强制）：已修，正确。**
- test_data.py:96-102、113 在三个前提条件之后检查全部解释已裁决。
- "超出任务书"只写在 test_data.py:13 的 docstring 里。交 Review Gate 的登记还无法核实，见 MINOR。

**MAJOR 5（条件 2、3）：已修，正确。**
- record.py:162-174 定义了两类记录，都含 kind。
- 选择冻结记录用 gate0_record_sha256 绑定已提交的 Gate 0 记录（test_data.py:90-92）。
- 条件 2、3 各有一个正向对照，只调用单个检查函数，不进入生成：t6:230、238『已验证』。

**MAJOR 6（B17）：已修，但有新问题。**
- 评测时间改为预检中实测一次 FP32 DEV 评测的秒数 × 评测单位数。
- 单位数中 TEST 部分计入了 31 个模型，见 MINOR。B17 仍待 Review Gate。

**MAJOR 7（T1–T3）：已修，但有新问题。**
- gate.py:142-218 实现了 compute_test_values 与 judge_test。
- TEST 评测入口没有守卫，见新 MAJOR 2；T3 包含 Acc_CB(N) 却没有列入解释，见 MINOR。

**MAJOR 8（GpuClock）：已修，正确。** compute.py:128-146；t6:216『已验证』。

**MAJOR 9（B14）：登记充分。** interpretations.py:70-78 写明了四点张力：
- G0.5 三个部分不满足都给同一原因；
- G0.4 不满足时改判 OPTIMIZATION_FAIL，而第 8 节对 [0.40, 0.70) 没有提 G0.4；
- G0.3、G0.9、G0.10 的原因为 null，而第 9 节说要给出一个原因；
- 可能输出多个原因。

**MAJOR 10（B5）：已修，正确。**
- train.py:210-216、261 对 A 的每个值都用 r.uniform。
- 测试用独立生成的 r.uniform 序列逐值比对，t6:153『已验证』。
- B5 写明分布与 purpose 字符串协议没有规定。

**第 1 轮 MINOR：**

| 项目 | 判断 | 位置或说明 |
|---|---|---|
| KL 调用处测试 | 已修但不完整 | 测试发现不了 kl.detach()，见 MINOR |
| ST13 | 已加 st13_scan | src 中还没有调用方 |
| TestAuthorization | 已修但位置不对 | 见 MINOR |
| σ_d = 0 | 已修 | stats.halfwidth_check；t6:207 |
| FLOP 系数 | 已修 | contract.py:372-381 |
| STATUSES | 已修 | contract.py:384-390；t6:98 |
| ImmediateGain | 已实现 | stats.py:65-68，没有调用方 |
| PROTOCOL_FROZEN 哈希 | 已修 | record.py:84-87 |
| _sliced 逐 id 比较 | 已修 | evaluate.py:53-55 |
| 重复逻辑 | 已修 | |
| smoke_steps 改名 | 已修 | |
| CUDA synchronize | 已修 | train.py:327-330、399、431 |
| 评测拒绝 CPU | 已修 | |
| B21–B23 | 已补 | |
| G0.3 端点 | 已补 | t6:129 |
| (e) 放宽范围 | 已修 | 限定为 ST6 |
| DeviceLedger | 已修 | t6:218 |
| 死代码 | 已修 | lora_parameters 已删；路径函数改为常量；step_numbers 已接入；purpose_format、think id、anchor_docs_per_step、source_sha256 都已使用。例外：z_alpha、z_power 仍未使用，见 MINOR |
| render_text、cost_usd、config.json 哈希 | 未见登记 | 说"登记到阶段 C"，暂存内容中没有，见 MINOR |

**data-auditor 的三条观察：**
- 观察 1：已修。data.py:491、505-514 按字节读，非 dev 行只解码 split 字段；输出与第 1 轮逐字节相同，t6:26-36、43『已验证』。但打印的计数说明与代码不符，见 MINOR。
- 观察 2：B3 已写明 train_Y 的行序（interpretations.py:25-26）。
- 观察 3：见第一条 MINOR。

## 二、问题清单

MAJOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:115-118；stops.py:78-86；tests/test_stops.py:203-210 | 评测中的非有限值抛出的 NonFinite 不带数值（values 为空列表）。按本轮的设计，调用方用 stops.st6(fz, e.values, …) 决定状态，而 st6 只在 values 中含非有限值时才停。所以对评测抛出的 NonFinite，st6 什么也不做：选定配置或对照的评测出现 NaN 时，既不给 IMPLEMENTATION_FAIL，也不剔除该配置。训练路径（train.py:323 传入 [x]）没有这个问题。唯一的测试是手工构造 NonFinite("loss is nan", [nan])，没有覆盖评测路径 | `raise NonFinite("%s: %d non-finite values (first at item %d)" % (what, len(bad), bad[0]))`；`bad = [x for x in values if not math.isfinite(x)]` / `if bad:`『未验证』 | _check_finite 传入 `[values[i] for i in bad]`，或让 st6 直接接收 NonFinite；补一个经由 evaluate 的测试（Stub 输出 NaN logits），断言 st6 抛出 ST6

MAJOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:295-307 | 新增的 split="test" 评测入口没有任何前提守卫：不要求 TestAuthorization，不复核已提交的 Gate 0 与冻结记录，不要求 ST10 已通过（L6 双方计数一致），也不限制"TEST 只评一次"。src 中目前没有读取 test_qa.jsonl 的加载函数，TEST 隔离完全依赖阶段 C 的调用方。不确定之处：这些检查是否计划放在阶段 C 的 run_pilot | `check_device(mode, device)` 之后直接执行 `qs = data[qa_file]`，没有其它检查『未验证』 | split="test" 时要求传入 TestAuthorization（以及 ST10 通过的凭据），并按 run_test_part 的方式复核已提交记录；记录 TEST 已评测，拒绝第二次；补测试

MINOR | metrix/e1-pilot/src/metrix_e1/test_data.py:141-144、176-182；leakage.py:206-216 | 第 1 轮 TestAuthorization 的问题只修了一半。复核放在 run_test_part 中，而它在 TEST 已生成并写盘之后才运行，挡不住提前生成。真正解析 eval_sets.jsonl 的 test 行、实例化 TEST 模板的 generate_test 仍然只做 isinstance 检查，传入 TestAuthorization(None, None, None) 就能通过 | generate_test 唯一的检查：`if not isinstance(authorization, LK.TestAuthorization): raise`『未验证』 | 在 generate_test 开头做同样的已提交记录复核，或把复核放进 TestAuthorization 的构造

MINOR | metrix/e1-pilot/src/metrix_e1/compute.py:201-208；interpretations.py:88-94 | B17 的评测单位数在 TEST 部分计入了 N 加全部 30 次训练，即 31 × 1.5 = 46.5。协议在 TEST 上只评 N 与 F、L、A、S、Y 各 3 个最终 checkpoint，即 16 × 1.5 = 24；未选中的搜索配置不评 TEST。预估因此多出 22.5 个 DEV 评测单位，可能让 ST11 误停。B17 已写明"N and 30 runs on TEST"，是公开的选择，但与协议的 TEST 评测范围不符 | `test = (1 + contract.arms.counts["total_training_runs"]) * acc.test_questions_per_fact / acc.dev_questions_per_fact`；test_st11 断言 80.5『未验证』 | 改为 1 + 5 × 训练种子数；或在 B17 中把多算的部分写明为安全余量，交 Review Gate

MINOR | metrix/e1-pilot/src/metrix_e1/gate.py:152-153、161-164 | T3 的原文是"N 在 TEST-QA 上满足 G0.3 的同样范围"，实现同时检查 Acc_CB(N)，而它是 TRAIN 闭卷指标，不是 TEST-QA 指标。B22、B24 都没有写这一点。N 的闭卷输入不变，数值应与 G0.3 时相同，实际影响很小 | `and _in(x["acc_cb"], g.g3_cb)`；`"acc_cb": float(N["acc_cb"])`『未验证』 | 在 B24 中写明 T3 是否包含 Acc_CB(N)，交 Review Gate

MINOR | metrix/e1-pilot/tests/test_train.py:253-273 | 测试名称说检验 KL 的梯度，实际只检查 lt.requires_grad 为 True。如果实现写成 `loss = ce + λ * kl.detach()`，lt 仍带梯度，第 2 步的 KL 仍大于 0，测试照样通过。读 train.py:420-427，当前实现是正确的 | `seen.append((lt.requires_grad, lb.requires_grad))`；`assert seen[0] == (True, False)`『未验证』 | 只用 λ·KL 反传一次，断言可训练参数的梯度非零

MINOR | metrix/e1-pilot/tests/test_test_data.py:170-176；src/metrix_e1/test_data.py:113 | 测试直接调用 check_interpretations_ruled，没有检验 check_preconditions 会调用它；删掉第 113 行，全部测试仍然通过 | 测试中只有 `TD.check_interpretations_ruled()`『未验证』 | 让条件 1–3 都满足（或 monkeypatch 它们），断言 check_preconditions 因待决解释而失败

MINOR | metrix/e1-pilot/tests/test_test_data.py:179-183；src/metrix_e1/leakage.py:215-216 | run_test_part 的复核只测了"未提交"一种情况，哈希不一致的分支没有测试；删掉 `if got != want` 测试仍通过 | 测试中只有 `match="not committed"`『未验证』 | 补"已提交但哈希不同"的用例

MINOR | metrix/e1-pilot/src/metrix_e1/train.py:371-373 | 预检只核对步数，不核对协议第 8 节第 2 步的"第一个配置"，任何 spec 都能用预检模式跑 | 没有任何 spec 检查『未验证』 | 预检模式下要求 spec 等于 search_runs(contract, "F")[0]

MINOR | metrix/e1-pilot/src/metrix_e1/data.py:514、526、648；reports/impl_b/t6_fix_round.txt:11 | 打印的"rows parsed and decoded: 100"与代码不符。循环对全部 400 个 dev 行都做 UTF-8 解码和 json.loads，只是保留其中 100 个；decoded_rows 实际是输出的窗口数。这只涉及 DEV 行，但这一行原始输出会被当作"读了多少行"的证据 | `"decoded_rows": len(out)`；`r = json.loads(line.decode("utf-8"))` 对每个 dev 行都执行。输出行（t6:11）『已验证』，代码判断『未验证』 | 分别打印"解析的 dev 行 400、保留的窗口 100"，或在每个域取满后跳过解析

MINOR | metrix/e1-pilot/src/metrix_e1/contract.py:247-248、268 | 第 1 轮列出的 z_alpha、z_power 仍然只解析、不使用（只用 z_sum），Executor 的处理表没有提到这一项 | grep z_alpha 只命中 contract.py『未验证』 | 删除，或在 size_estimate 中使用

MINOR | metrix/e1-pilot/src/metrix_e1/interpretations.py:79 | B15 的 "where" 写的是 gate.g0_8，代码中没有这个函数，实际是 gate.repro_compare | `"where": "gate.g0_8"`『未验证』 | 改为 gate.repro_compare

MINOR | metrix/e1-pilot/src/metrix_e1/compute.py:67；evaluate.py:84 | 两个同名函数 check_device 含义不同：一个是 ST8 设备检查，参数 (fz, contract, mode, info)；一个是评测拒绝 CPU，参数 (mode, device)。容易混用 | 两处 `def check_device`『未验证』 | 改名，例如 evaluate.require_gpu

MINOR | metrix/e1-pilot/src/metrix_e1/stops.py:153-164 | st13_scan 只要 SELECTION_FREEZE_REL 在 HEAD 中有已提交文件，就当作已冻结，不核对 kind、mode、label（test_data._committed 会核对这些）；src 中也还没有调用方 | `R.committed_json(repo_root, R.SELECTION_FREEZE_REL)` 之后直接 `return []`『未验证』 | 复用 test_data._committed 的检查；阶段 C 接线

MINOR | metrix/e1-pilot/src/metrix_e1/gate.py:215-217 | judge_test 先算出状态，再检查 Gate 0 是否为 PASS；结果不受影响，但前提检查应放在最前 | `out = _status(...)` 位于 `if not mode.smoke and gate0_status != "PASS"` 之前『未验证』 | 把检查移到函数开头

MINOR | metrix/e1-pilot/src/metrix_e1/interpretations.py:5-8；test_data.py:13 | Executor 说要交 Review Gate 或登记到阶段 C 的事项，在暂存内容中都找不到登记：第 4 个前提条件、render_text、cost_usd、config.json 哈希。interpretations.py 引用的 reports/IMPL_B_REPORT.md 不存在，DEFERRED_MINORS.md 也没有阶段 B 的新条目 | Glob `metrix/e1-pilot/reports/IMPL_B*` 无结果；review_input_round2.diff 第 1–38 行的 stat 中没有这两个文件『已验证』 | 提交前补报告与登记，逐项列出

MINOR | metrix/e1-pilot/src/metrix_e1/record.py:87 | PROTOCOL_FROZEN_unchanged_since_load 为 False 时只记录、不停止，按 ST12 应当停止 | `"PROTOCOL_FROZEN_unchanged_since_load": FZ.sha256_hex(pf) == fz.record.source_sha256`『未验证』 | 为 False 时抛出 ST12Error

## 三、核对后未发现问题的部分

- **TEST 生成器拒绝执行，没有产生文件**：t6:62-66 打印 refused、RESULT: FAIL，exit=1；t6:67-77 中 test_out_never 不存在，data_c 里没有 TEST 文件『已验证』。
- **正向对照不会进入生成**：读代码只调用单个检查函数，不调用 generate_test『未验证』。
- **DEV 与 TEST 不会混用**：
  - evaluate.SPLIT_FILES 分开两组文件；
  - stats.evaluation_summary 的键带 split；
  - compute_values 只读 scores_dev，喂入 TEST 摘要会报 KeyError，不会静默混用；
  - G0.8 只用 DEV；
  - TEST 比较的 purpose 为 "F-N:TEST:avg"（t6:137『已验证』）。
- **模式隔离**：
  - preflight 与 smoke 的记录带 label，write_record 拒绝写入正式目录（record.py:115-125）；
  - 带 label 的 Gate 0 记录或冻结记录会被 test_data._committed 拒绝『未验证』。
- **数据与导出**：
  - 改动后重新生成的数据与第 1 轮逐字节相同（t6:26-36）；
  - verify 通过（t6:43-45）；
  - 泄漏命令通过（t6:60-61）；
  - 全部测试 189 passed（t6:277）；
  - 导出与第 1 轮逐字节相同（t6:279-287）『已验证』。
- **改动范围**：只在 metrix/e1-pilot/ 下（review_input_round2.diff 第 1–38 行）『已验证』。

结论：PASS
