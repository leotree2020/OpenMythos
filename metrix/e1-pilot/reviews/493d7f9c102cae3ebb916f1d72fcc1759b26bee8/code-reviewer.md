# code-reviewer final report, Implementation stage B second fix commit (staged; parent fdbb9def89351aa187c1b1ae9749884bc3a80fe9); invoked 2026-11-23 13:55 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-adda4086e68f3de39.jsonl)
---
code-reviewer 第 4 轮：Metrix E1-PILOT Implementation 阶段 B 第二个修复提交（暂存，未提交；父提交 fdbb9def89351aa187c1b1ae9749884bc3a80fe9）

结论：PASS，没有 BLOCKER。有 1 条 MAJOR（上一轮带过来，交 Review Gate 裁决）和 8 条 MINOR。
- 上一轮的 MAJOR，代码部分已修，修法正确：测试不再让 l6_check.py 读取完整的 eval_sets.jsonl。遗留的是已经执行过的那些运行如何定性，仍交 Review Gate。
- 上一轮 9 条 MINOR：已修且正确 5 条；已修但留有缺口 2 条；未修 2 条，二者都推到了之后的提交。

审查方式：
- 先读了 /home/user/OpenMythos/.claude/agents/code-reviewer.md，tools 行为 Read, Grep, Glob，与已加载的定义一致。
- 只用 Read、Grep、Glob，没有执行任何命令。只靠读代码得出的判断标『未验证』。
- 引用本提交暂存的原始输出的判断标『已验证』，与上一轮的标法相同。这两份输出是 /home/user/OpenMythos/metrix/e1-pilot/reports/impl_b/t9_fix_commit_push.txt（下称 t9）和 t10_fix2_commit.txt（下称 t10）。

## 一、上一轮各项核对

| 上一轮项目 | 判断 | 依据 |
|---|---|---|
| MAJOR：l6_check.py 在测试中以文本模式解码 test 行 | 代码已修，正确；遗留的定性仍待裁决，见第二节 MAJOR | 见下方说明 |
| MINOR：verify_authorization 弱于前提条件 | 已修，三项各有有效测试；仍有缺口，见第二节 MINOR 1 | 见下方说明 |
| MINOR：split="test" 不限模式 | 已修，正确 | 见下方说明 |
| MINOR：ST10 凭据与“只评一次” | 未修 | 登记不在本提交中，无法核实；evaluate_model 中仍没有这两项检查『未验证』 |
| MINOR：generate_test 的拒绝须发生在读取之前 | 已修，正确 | 见下方说明 |
| MINOR：测试依赖“当前仍有待决的解释” | 该测试已修，正确；同类问题在另一个测试中仍存在，见第二节 MINOR 5 | 见下方说明 |
| MINOR：死 import 与多余空行 | 已修 | test_verify_authorization_branches 中已没有 `mode as M`；test_test_data.py:196-199、test_train.py:276-278 都是 2 个空行。本提交在别处新增了 3 个空行，见第二节 MINOR 4『未验证』 |
| MINOR：test_stops 的注释 | 已修，正确 | test_stops.py:202-203 的注释现在与 211-219 的断言一致：冒烟记录下仍抛 ST13，正式记录下返回 []『未验证』 |
| MINOR：EM 生成不检查非有限值 | 已修，有测试，但测试只覆盖第一次前向，见第二节 MINOR 2 | 见下方说明 |
| MINOR：审查原文与 auditor 输出未入库 | 未修 | 按 Executor 的安排放到之后的报告提交，见第二节 MINOR 7 |

各项说明：

**MAJOR（l6_check.py）**
- _dev_rows_only（test_data_hashes.py:73-98）以 "rb" 方式读取源文件。它只在行前缀的原始字节上匹配 split 字段，把 DEV 行逐字节写入临时文件，test 行既不解码也不写出。所用正则与 data.py:491 的 `_ROW_HEAD` 相同。
- 参考脚本没有改动：diff stat 中没有 reports/round5/。
- l6_check.py 只从 manifest 读取 general_text 的两个 sha256（l6_check.py:68-74），所以只替换 source_file_sha256 的那份 manifest 副本足以让它运行。它按文件顺序取每个 domain 的前 25 行 DEV，去掉 test 行不影响结果。
- 我用 Grep 查了 tests/ 与 src/，没有其它以文本模式打开 eval_sets.jsonl 的地方。test_st12 只用 shutil.copyfile 复制、用 read_bytes 翻转一个字节。
- t10:58 记录 test_byte_identical_to_reference_scripts PASSED。t10:209-211、75 中出现了本提交新增的测试，可见这次 pytest 运行的是新代码『已验证』。

**MINOR（verify_authorization 的三项复核）**
- leakage.py:220-231 新增三项复核：Gate 0 状态为 PASS、冻结记录绑定 Gate 0 记录、授权的冻结提交等于当前 PROTOCOL_FROZEN 的冻结提交。
- 三个参数化用例的 match 串分别是 "not PASS"、"not bound"、"PROTOCOL_FROZEN names"，都只会由新增的那一行检查产生。
- other_protocol_frozen 用例里，两份记录与授权都写的是 "1"*40，所以 committed_record 能通过，测试确实落到最后一项检查上。删掉任意一项检查，对应用例都会失败。
- 正对照是 test_verify_authorization_branches:220。_repo 现在写入真实的 PROTOCOL_FROZEN，所以这次调用会走完全部检查。
- 证据：t10:208-211『已验证』。

**MINOR（split="test" 不限模式）**
- evaluate.py:318-320 在 verify_authorization 之前拒绝非正式模式。
- 测试覆盖了 smoke 和 preflight。删掉这项检查后，None 授权会得到 "TEST paths run only…"，与 "formal mode only" 不匹配，测试失败。
- 第一段改用 FORMAL_MODE + cpu：删掉 verify_authorization 后，require_gpu 的信息 "evaluates only on the GPU" 与 "TEST path" 不匹配，测试同样失败。
- 证据：t10:74『已验证』。

**MINOR（generate_test 先拒绝、后读取）**
- 测试监视了 check_inputs、load_qwen_tokenizer、build_general_dev 和 FZ.read_jsonl，并断言 `called == []`。
- 把 verify_authorization 移到其中任一读取之后，测试都会失败。
- 证据：t10:187『已验证』。

**MINOR（测试依赖待决解释）**
- test_test_data.py:207-212 先把 INT.pending 替换为返回 ["B19"]，再替换为返回 []，作为对照。对照只构造授权对象，不调用任何 TEST 路径。contract 参数已删除。
- 证据：t10:207『已验证』。

**MINOR（EM 非有限值）**
- evaluate.py:220-225 新增 `_finite_argmax`，并在 250 行（首次前向）和 266 行（循环内）两处调用。
- 证据：t10:75『已验证』。

**本提交的原始输出**
- t9:256-258 记录，fdbb9def 的 diff 与上一轮的审查输入逐字节相同。
- t9:259-269 记录，metrix/ 以外的检查为 RESULT: PASS。
- t9:282-288 记录，推送是快进。
- t9:271-276 与 289-294 记录，推送前后远端标签不变。
- t10:27-33 记录，TEST 生成器拒绝执行，exit=1，没有产生输出目录。
- t10:241 记录，198 passed。
- 以上『已验证』。

## 二、问题清单

MAJOR | metrix/e1-pilot/reports/round5/l6_check.py:82；metrix/e1-pilot/tests/test_data_hashes.py:73-98 | 上一轮 MAJOR 的遗留。今后不会再触发；未定的是此前已经执行过的运行（阶段 A 与阶段 B 的各次 pytest）。协议第 3 节（METRIX_E1_PROTOCOL.md:158）把“解码 test 行的内容”定义为读取 TEST。照字面读，UTF-8 解码属于这一类，这些运行就落入 ST13，即本次 Pilot 全部作废；也可以把这里的“解码”理解为分词器解码。不确定之处正在这里，须由 Review Gate 裁决。另外，参考脚本本身没有改，以后若有人手工对完整文件运行它，仍会解码 test 行；它的文档字符串写着 "No TEST data is read"，按严格读法并不成立 | `with open(a.eval_sets, encoding="utf-8") as fh:`。运行清单与裁决请求按计划放在报告提交里，本提交无法核实。运行事实『已验证』（上一轮 t8:110），读法判断『未验证』 | 报告中逐条列出这些运行，标明执行时间和对应提交，明确交 Review Gate 裁决。裁决之前，登记中写明 l6_check.py 不得再对完整的 eval_sets.jsonl 运行

MINOR | metrix/e1-pilot/src/metrix_e1/leakage.py:201-207；metrix/e1-pilot/src/metrix_e1/test_data.py:66-97 | 文档字符串说复核了“条件 2 和 3 中授权所代表的全部内容”，实际仍有缺口。条件 3 的三项内容没有复核：选定配置是 SEARCH_SPACE 中的配置；30 个 checkpoint 哈希齐全；data_content_hashes 一致。解释裁决检查也没有复核。所以，一个已提交、formal、已绑定但内容不完整的冻结记录，配上手工构造的授权，仍能通过 verify_authorization，也就能进入 evaluate_model(split="test")。上一轮说过，阶段 C 很可能在另一个进程中评测 TEST，这一缺口会在那时起作用 | verify_authorization 中没有 `training_plan`、`checkpoints`、`INT.pending` 的调用。状态检查、绑定检查与 test_data.check_gate0_record、check_selection_record 的写法重复『未验证』 | 在 verify_authorization 中补上不依赖数据目录的部分：INT.pending() 为空、selected 可构成训练计划、30 个 checkpoint 哈希齐全，最好与 test_data 共用一个函数；否则把文档字符串改为准确列出复核了哪几项，并登记到阶段 C

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:266；metrix/e1-pilot/tests/test_evaluate.py:139-143、180-185 | 新测试只检验了第一次前向（250 行）的检查。NaNStub 每次调用都返回 NaN，所以把 266 行的循环内检查改回 `.argmax(-1)`，测试仍会通过。上一轮举的例子正是“NaN 只出现在 KV cache 路径”，即循环内这一步 | `out.logits[:] = float("nan")`，每次调用都如此『未验证』 | 增加一个桩模型：第 1 次调用返回有限值，之后返回 NaN（Stub 已有 calls 计数），并断言抛出 NonFinite

MINOR | metrix/e1-pilot/tests/test_evaluate.py:177-179 | 本提交新增了 3 个连续空行，正是上一轮刚修掉的那类格式问题 | diff 中 `+` `+` `+` 之后紧接 `+def test_nonfinite_logits_stop_em_generation`『未验证』 | 删去 1 个空行

MINOR | metrix/e1-pilot/tests/test_test_data.py:183-189 | 上一轮指出的“依赖当前仍有待决解释”在 test_pending_interpretations_block_test 中仍然存在（该段代码本提交未改）。Review Gate 裁决 B1 或全部解释之后，实现没有错，测试却会失败 | `assert INT.pending()  # current state: every entry awaits Review Gate`；`match="B1"`『未验证』 | 同样用 monkeypatch 构造“有待决”与“无待决”两种状态，不依赖 INT.ENTRIES 的当前内容

MINOR | metrix/e1-pilot/tests/test_data_hashes.py:81、93-95 | l6_check.py 自己的哈希固定检查变成了同义反复：manifest 副本中的 source_file_sha256 就是用这份过滤后的副本算出来的。_dev_rows_only 在过滤前也没有核对源文件的哈希。另有魔法值：源文件路径写死，与 D.params(fz).general_source 重复；计数 400 / 800 写死。生成器一侧的 check_inputs 仍会核对同一路径的哈希，所以实际风险小 | `manifest["general_text"]["source_file_sha256"] = FZ.file_sha256(out)`；`src = PILOT.parents[1] / "research/mini_mythos/stage1/results/r1/eval_sets.jsonl"`；`assert n == {"dev": 400, "other": 800}`『未验证』 | 过滤前断言 `FZ.file_sha256(src)` 等于冻结 manifest 中的原值（协议允许对整个文件求哈希）；路径改用 D.params(fz).general_source；计数与 generated["info"]["general_dev"]["rows_by_split"] 比较

MINOR | metrix/e1-pilot/reports/impl_b/t9_fix_commit_push.txt:285-287 | 过程问题，上一轮已指出，仍未处理。fdbb9def 已推送，而仓库中没有 reviews/74a4d444…/ 和 reviews/fdbb9def…/。两轮审查原文仍在会话临时目录，audit/ 下的 stdout 与脚本也未入库。CLAUDE.md 第 5 节第 5 条、第 9 节要求原始输出随提交推送。Executor 说放在之后的报告提交，本提交无法核实 | Glob `metrix/e1-pilot/reviews/{74a4d444,fdbb9def}*/**` 无结果；`74a4d44..fdbb9de  HEAD -> metrix-e1-pilot-protocol-v1`（t9:287）『已验证』 | 报告提交中补齐 reviews/74a4d444…/、reviews/fdbb9def…/ 与本轮的 reviews，以及 audit/ 下的脚本和 stdout，并在报告中写明推送顺序

MINOR | metrix/e1-pilot/reports/impl_b/t10_fix2_commit.txt:23-26 | 证据不完整。这条 grep 先筛出含 "eval_sets" 的行，所以显示不出 test_data_hashes.py:84 的 `open(src, "rb")`。搜索范围也不含 reports/，即本问题的主角 l6_check.py。我用 Grep 补查了 src/ 与 tests/，结论“只有二进制方式打开”成立 | `grep -rn 'eval_sets' … | grep -n 'open(\|_run(\|eval-sets\|src = '`『已验证』（t10:23-26 的输出与我对 src/、tests/ 的 Grep 一致） | 报告中说明 grep 的口径，或改用列出全部 `open(` / `read_text` / `_run(` 调用及其参数的检查

MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:317-323 | 上一轮第 2 项 MAJOR 中的 ST10 凭据和 TEST“只评一次”（协议第 8 节第 8 步，METRIX_E1_PROTOCOL.md:528）仍未实现。登记不在本提交中，无法核实 | evaluate_model 中没有 ST10 记录或评测次数的检查『未验证』 | 报告提交中把二者写成阶段 C 的硬性前提，阶段 C 审查时复核

结论：PASS
