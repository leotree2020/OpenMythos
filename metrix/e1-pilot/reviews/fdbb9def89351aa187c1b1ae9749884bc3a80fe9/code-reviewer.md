# code-reviewer final report, Implementation stage B fix commit (staged; parent 74a4d4443a3880239996d7adc6c13c636e4edf64); invoked 2026-11-23 13:35 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-aac6bb0daec0148ee.jsonl)
---
code-reviewer 第 3 轮：Metrix E1-PILOT Implementation 阶段 B 修复提交（暂存，未提交；父提交 74a4d4443a3880239996d7adc6c13c636e4edf64）

结论：PASS，没有 BLOCKER。有 1 条 MAJOR（不确定，交 Review Gate 裁决）和 9 条 MINOR。第 2 轮的两条 MAJOR 都已修，但都有遗留：
- MAJOR 1（评测中的非有限值）：修复正确。遗留是 EM 生成路径不检查非有限值（既有代码）。
- MAJOR 2（TEST 评测入口）：只修了授权复核这一部分。ST10 凭据与“只评一次”推到阶段 C；复核比前提条件弱；不限制模式。

审查方式：
- 先读了 /home/user/OpenMythos/.claude/agents/code-reviewer.md。它的 tools 行（Read, Grep, Glob）与已加载的定义一致。
- 只用 Read、Grep、Glob，没有执行任何命令。
- 读代码得出的判断标『未验证』。
- 引用本提交暂存的原始输出（/home/user/OpenMythos/metrix/e1-pilot/reports/impl_b/t8_fix_commit.txt，下称 t8；t7_work_commit_push.txt，下称 t7）的判断标『已验证』。

## 一、第 2 轮各项核对

**新 MAJOR 1（评测中的非有限值）：已修，正确。**
- evaluate.py:115-118 把非有限值本身传入 NonFinite。general_nll 共用同一个检查（evaluate.py:288）。
- 新测试经由 score_qa(NaNStub) 触发，断言：带 8 个值、status 为 None；st6 对选定配置给 IMPLEMENTATION_FAIL，对非选定配置给 exclude_config。t8:125 PASSED『已验证』。
- 遗留：EM 路径不检查，见 MINOR。

**新 MAJOR 2（TEST 评测入口）：修了一部分，已修的部分正确。**
- evaluate.py:307-312 先校验 split，对 test 调 verify_authorization，然后才 require_gpu。
- 测试对 None 和手造授权都断言被拒，t8:126『已验证』。
- 测试能发现守卫被删：删掉后 data 中没有 test_qa.jsonl，抛出的是 KeyError 而不是 ImplementationFail，测试失败『未验证』。
- ST10 凭据与“只评一次”没有实现，复核也比前提条件弱，见 MINOR。

**第 2 轮 MINOR：**

| 项目 | 判断 | 依据 |
|---|---|---|
| generate_test 复核 | 已修 | test_data.py:140 在任何读取之前调用；t8:238。调用顺序没有被测试，见 MINOR |
| B17 的 TEST 单位 | 已修，正确 | compute.py:209 为 (1 + 5 × 3) × 1.5 = 24，与协议第 8 节一致：T1–T3 用 N、F、S、Y，“Δ(L−F)、Δ(A−F) 在 TEST 上只报告”。test_st11 断言 58.0（t8:229）。B17 文字已同步 |
| T3 包含 Acc_CB(N) | 登记充分 | B24 写明，状态仍为 PENDING |
| KL 梯度测试 | 已修，测试有效 | test_train.py:279-290。A1、A3 只差 λ（SEARCH_SPACE.json:157-174）。KL 附着时两者参数不同；对照中 KL 被 detach 时两者逐位相同，所以能发现 kl.detach()。第 1 步 KL 的梯度为 0，用 2 步是对的。t8:287 |
| check_preconditions 调用解释裁决检查 | 已修 | 删掉 test_data.py:108，测试就会失败（t8:258）。测试依赖当前状态，见 MINOR |
| 哈希不一致、冻结提交不一致两个分支 | 已修 | test_test_data.py:199-209；t8:259 |
| 预检核对第一个配置 | 已修 | train.py:374-376。RunSpec 是 frozen dataclass，按全部字段比较；t8:285 |
| data.py 计数标签 | 已修 | t8:11 打印“DEV rows decoded and parsed: 400; windows kept … 100”。test_data_hashes.py:56 断言 parsed_rows 等于 DEV 行数，若解析了 test 行就会变成 1200 而失败；t8:108『已验证』 |
| z_alpha、z_power | 已删 | grep 无残留 |
| B15、B10 的位置 | 已修 | gate.repro_compare（gate.py:46）、stats.stratified_draws / paired_bootstrap（stats.py:99、115）都存在 |
| check_device 改名 | 已修 | evaluate.require_gpu 与 compute.check_device（ST8）不再同名 |
| st13_scan | 已修 | stops.py:159 改用 committed_record。测试中冒烟记录不算冻结、正式记录算；t8:232。调用方仍属阶段 C |
| judge_test 的 Gate 0 检查 | 已修 | 已移到开头，gate.py:206-208 |
| PROTOCOL_FROZEN 加载后改变 | 已修 | record.py:73-75 抛 ST12Error；t8:168 |
| 待登记事项 | 本提交中无法核实 | 第 4 个前提条件、render_text、cost_usd、ImmediateGain、config.json 哈希：报告与 DEFERRED_MINORS.md 不在本提交中 |

**data-auditor 第 2 轮观察：**
- 观察 2：已修（见上表“data.py 计数标签”）。
- 观察 1：登记不充分，见 MAJOR。

**数据、TEST 隔离与测试结果（本提交的原始输出）『已验证』：**
- 重新生成的数据与第 2 轮逐字节相同（t8:26-35）。
- verify 通过（t8:36-44）。
- 泄漏命令 RESULT: PASS（t8:45-60）。
- TEST 生成器拒绝执行，exit=1（t8:61-65），没有产生输出目录（t8:66-77）。
- 导出与第 1 轮逐字节相同（t8:83-85）。
- 全部测试 194 passed（t8:289）。

## 二、问题清单

MAJOR | metrix/e1-pilot/tests/test_data_hashes.py:82-84；metrix/e1-pilot/reports/round5/l6_check.py:82 | data-auditor 观察 1 的登记不充分。“阶段 A 已入库的参考脚本与证据”不是只存在于历史中：每次 pytest 都会对真实的 eval_sets.jsonl 运行 l6_check.py，以文本模式 UTF-8 解码全部 1200 行，其中 800 行是 test 行。本修复提交的 t8 在观察提出之后又执行了一次。协议第 3 节把“解码 test 行的内容”算作读取 TEST，“解析 split 字段、计数”不算。整行 UTF-8 解码属于哪一种，协议没有说清。不确定之处：按宽读法这不是问题；按严读法，每次运行都是冻结前读取 TEST（ST13） | `with open(a.eval_sets, encoding="utf-8") as fh:`、`for lineno, line in enumerate(fh, 1):`；t8:110 `test_byte_identical_to_reference_scripts PASSED`。运行事实『已验证』，读法判断『未验证』 | 登记中写明“每次运行 pytest 都会执行”，并列出已执行过的运行（t4、t6、t8 等）。Review Gate 裁决前，让测试暂停调用 l6_check.py 这一步（跳过，或改为显式的手动步骤），脚本本身不改

MINOR | metrix/e1-pilot/src/metrix_e1/leakage.py:201-215 | verify_authorization 比 check_preconditions 弱。它只核对：两份记录已提交、formal、kind 正确、记录中的 frozen_commit 等于授权自带的 frozen_commit、sha256 相同。它不复核 Gate 0 状态为 PASS，不复核冻结记录的 gate0_record_sha256 绑定，也不把 authorization.frozen_commit 与当前 PROTOCOL_FROZEN 的提交比较。授权只存在于一个进程的内存中，而 ST10 要求 data-auditor 在 TEST 评测前独立计数，所以阶段 C 的 TEST 评测很可能在另一个进程中进行。届时若按已提交记录的哈希手工构造授权，就会绕过 PASS 检查。目前 src 中只有 test_data.py:109 构造授权 | `_, got = R.committed_record(repo_root, rel, kind, authorization.frozen_commit)` 之后只检查 `if got != want`『未验证』 | 在 verify_authorization 中复用 check_gate0_record（PASS）与绑定检查，并用 FZ.load(repo_root).record.commit 比对；或在登记中规定阶段 C 只能经 check_preconditions 取得授权

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:309-312 | split="test" 不限制模式。Gate 0 与冻结记录提交之后，smoke 模式（CPU、随机小模型）或 preflight 模式也能通过 verify_authorization 评测 TEST，与指令第 7 节的冒烟隔离、协议的“TEST 只评一次”冲突 | `if split == "test": ... verify_authorization(...)`，随后 `require_gpu` 对 smoke 放行『未验证』 | split="test" 只允许 formal 模式，并补一个测试

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:298-325 | 第 2 轮 MAJOR 2 的另两项（ST10 通过的凭据、TEST 只评一次）没有在代码中实现，登记到阶段 C 的 run_pilot。这项登记不在本提交中，无法核实 | evaluate_model 中没有 ST10 或评测次数的检查『未验证』 | 登记中把二者写成阶段 C 的硬性前提，最好让 evaluate_model(split="test") 自己核对，例如核对已提交的 ST10 记录和 TEST 已评测标记；阶段 C 审查时复核

MINOR | metrix/e1-pilot/tests/test_test_data.py:80-86；metrix/e1-pilot/src/metrix_e1/test_data.py:140-148 | 测试只证明 generate_test 拒绝手造授权，没有证明拒绝发生在读取之前。把 verify_authorization 移到 build_general_dev 之后，测试仍会以 "not committed" 通过，而那时 test 行已被解析 | 测试只有 `pytest.raises(ImplementationFail, match="not committed")`，没有监视读取函数『未验证』 | 仿照 test_refusal_never_parses_test_rows 监视 D.build_general_dev 与 D.check_inputs，断言拒绝时一次也没有调用

MINOR | metrix/e1-pilot/tests/test_test_data.py:189-196 | 这个测试依赖“当前仍有待决的解释”。Review Gate 全部裁决之后，实现没有错，测试却会失败。签名中的 contract fixture 也没有使用 | 没有 monkeypatch INT.ENTRIES 或 INT.pending；`contract` 在函数体中未使用『未验证』 | monkeypatch INT.pending 返回非空，再加一个“全部已裁决时返回授权”的对照；删除 contract 参数

MINOR | metrix/e1-pilot/tests/test_test_data.py:200、186-188；metrix/e1-pilot/tests/test_train.py:276-278 | 死 import 与多余空行：test_verify_authorization_hash_branches 中的 `from metrix_e1 import mode as M` 未使用；两处新函数前各有 3 个空行 | 函数体中没有 `M.`『未验证』 | 删除

MINOR | metrix/e1-pilot/tests/test_stops.py:202 | 注释与断言的意思相反。注释说“a smoke record does not stop the scan”，而下面断言冒烟记录时 st13_scan 抛出 ST13 | `(M.smoke_mode(3), True)` 对应 `raises("ST13", STP.st13_scan, ...)`『未验证』 | 改为“a smoke record does not count as the freeze: the scan still finds the TEST file”

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:241-258 | 第 2 轮 MAJOR 1 的遗留（既有代码，不是本提交引入）。EM 的贪心生成不检查 logits 是否有限，NaN 的 argmax 会静默给出某个 id；协议 ST6 是“任一次训练或评测出现非有限值”。evaluate_model 先跑 score_qa，通常会先在那里发现 NaN，但不能保证（例如 NaN 只出现在 KV cache 路径） | `past, nxt = o.past_key_values, o.logits[:, -1].float().argmax(-1)` 之前没有 isfinite 检查『未验证』 | 每步检查 torch.isfinite(o.logits[:, -1])，不满足时抛 NonFinite

MINOR | metrix/e1-pilot/reports/impl_b/t7_work_commit_push.txt:36-66 | 过程问题。工作提交 74a4d444 已推送，但仓库中没有 reviews/74a4d444…/：两份第 2 轮审查原文仍在会话临时目录。推送时 data-auditor 的 audit/ib_*、ic_* 与 audit/stdout/impl_b/ 未跟踪，本修复提交也没有包含它们。CLAUDE.md 第 5 节第 5 条、第 9 节要求原始输出随提交推送。Executor 说这些在之后的报告提交中，本提交无法核实 | t7:47-64 的 `?? metrix/e1-pilot/audit/...`；Glob `metrix/e1-pilot/reviews/74a4d444*` 无结果『已验证』 | 在报告提交中补齐，并在报告中写明推送顺序

结论：PASS
