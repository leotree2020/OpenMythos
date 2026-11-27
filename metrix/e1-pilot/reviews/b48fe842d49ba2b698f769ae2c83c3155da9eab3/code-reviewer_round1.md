# code-reviewer, C1 fix commit, round 1 (staged tree ae5fcb2f7e2ea844c6ee04e7ecb8e3157efde08c, parent ae60e0f7); interrupted by HTTP 429 and resumed (interruption.txt, resume_message_code-reviewer.txt)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
code-reviewer：C1 第二次送审，修复提交第 1 轮（暂存树 ae5fcb2f7e2ea844c6ee04e7ecb8e3157efde08c，父提交 ae60e0f7ba699e5e7a25718108849ae36586f5f5）。以下为完整原文。

**运行环境与依据**
- 定义：已读仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，tools 行为「Read, Grep, Glob」。审查因 API 429 中断，按 coordinator 消息从中断处继续；继续前重读了该定义。
- 工具：只用了 Read、Grep、Glob。没有运行任何代码，没有读取 TEST，没有计算哈希。
- 读过的材料：
  - 调用文字 review_c1b_fix/code-reviewer_prompt.txt；
  - input.diff 与 tree.txt；
  - 第 1 轮原文 review_c1b/code-reviewer_round1.md；
  - 工作区源码 testgate.py、evaluate.py、test_data.py、tests/test_testgate.py、record.committed_json。调用文字与 c1b_04:485 都说明工作区等于暂存区；
  - 协议第 8 节（:550）；
  - 暂存的原始输出 reports/impl_c/c1b_04_checks_fix.txt（下称 c1b_04，正式记录）与 c1b_03_checks_fix.txt（下称 c1b_03，已被取代）。行号按 input.diff 中的文件内行号。
- 判定范围按防范对象原文：TEST 闸门要防的是「按规则办事的 Executor 在按 RUNBOOK 操作时，意外评测 TEST 两次，或在 ST10 不成立时评测 TEST」；不防有仓库写权限者的故意篡改（改写历史、伪造记录），这类风险由 GitHub 分支保护和审查记录承担。审查按此范围判定：范围外的边缘情况记为 MINOR 并登记，不作为 BLOCKER。

**一、逐条核对**

- **code-reviewer MAJOR 2（同一克隆中两个并发的 begin）：已修且正确。**
  - 位置与代码：testgate.py:464-466。begin 在 commit_paths 返回之后检查两点，否则 BLOCKED，且不创建会话：
    - `_blob(head:MARKER_REL) == blob`；
    - `_blob(head^:MARKER_REL) is None`。
  - 两个进程不可能都拿到会话（静态推导，未验证）：
    - 会话 i 要求：已推送的提交 head_i 中的标记字节等于本进程写的 blob_i，且 head_i 的父提交中没有标记。
    - blob 含 128 位随机 session_id，所以 blob_1 ≠ blob_2，进而 head_1 ≠ head_2。
    - 两者都曾是远端分支的最新提交（_push 用 ls-remote 核对）。普通推送只能快进，所以一个是另一个的祖先，设 head_1 是 head_2 的祖先。
    - head_2^ 是 head_1 或其后代，而 head_1 中有标记。要让 head_2^ 中没有标记，二者之间必须有一个删除标记的提交。
    - 包内没有删除标记的路径：commit_paths 只 add 标记路径或结果路径。只有有人手工删掉工作区的标记，`git add -- MARKER_REL` 才会暂存删除，这超出防范对象。
  - 第 1 轮所述两种情形，以及新发现的交错：
    - 情形一（第二个 begin 在第一个推送之后才提交）：第二个的父提交含标记 → BLOCKED。第一个会话的下一次调用中，_check_session_checkout 看到 HEAD 不再是 M1 → BLOCKED。第一个进程已在进行的那个模型只评一次，不构成评两次。
    - 情形二（第二个的提交落在第一个提交与第一个 _push 读 HEAD 之间）：第一个的 head 是 M2，字节不等 → BLOCKED。第二个的父提交 M1 含标记 → BLOCKED。
    - 同一工作区中、add 之前标记文件被另一个进程覆盖：已提交的字节不是本会话的 → BLOCKED。另一个进程的 add 之后暂存为空，或提交失败 → BLOCKED。
    - 两个进程同时 add 或 commit：暂存检查失败、「nothing to commit」或 index.lock → BLOCKED。
  - 不另加 session_id 比较：同意 Executor 的判断。两项检查通过时，标记提交中的标记就是本会话的。_check_session_checkout 要求 HEAD 等于 marker_commit，committed_json 要求工作区等于 HEAD，所以这项比较不可能失败。
  - 证据（已验证）：
    - 全部 pytest：298 passed（c1b_04:558）；
    - 变异「begin: parent marker not checked」被 test_a_second_begin_in_the_same_clone_is_blocked 测出（c1b_04:756-757）；
    - 变异「begin: pushed marker bytes not checked」被 test_a_marker_file_overwritten_before_the_commit_is_blocked 测出（c1b_04:758-759）。
  - 正常单次运行不会误判：父提交就是 refuse_if_marker 查过的最新提交；探针中 begin 为 ACCEPT（c1b_04:572、594，已验证）。

- **code-reviewer MAJOR 1（评测调用不 fetch）：未修，按约定交 Review Gate；新补的测试正确。**
  - test_evaluation_calls_do_not_fetch_finish_does（tests/test_testgate.py:701-717）固定了这一行为：另一克隆推进远端后，本地评测调用继续；finish 先 fetch，然后 BLOCKED，不写结果。
  - 依据：静态阅读；298 passed（已验证）。
  - Review Gate 确认之前，这一条仍列为 MAJOR，见第二节。

- **MINOR（with_s_mapping 与 split 的检查在登记之后）：已修且正确。**
  - 检查已移到 evaluate.py:322-323，位于 TEST 闸门之前；`if with_s_mapping:` 中的旧检查已删去。
  - DEV 路径行为不变；SPLIT_FILES 只有 dev 和 test 两项，`split != "dev"` 等价于 TEST。
  - 变异测出（c1b_04:760-761，已验证）。测试的区分度见第二节 MINOR。

- **MINOR（sleep 默认值在定义时绑定）：已修且正确（静态，未验证）。**
  - commit_paths、begin、finish 的默认值改为 None，在 _push 内调用时才取 time.sleep（testgate.py:245）。test_data.main 不传 sleep，所以 tests:876 的 monkeypatch 现在生效。
  - 更正我第 1 轮引用的证据：第 1 轮所引 c1b_02:294 的 19.30 s 不是这个原因。c1b_04:744 中同一变异仍为 19.74 s，原因是在该变异下 test_driver_checks_the_commit_preconditions_before_generating（tests:838-864）越过了 dry-run 检查，向 no-such-remote 推送失败，真实睡眠 2+4+8 s。这只发生在变异运行中，见第二节 MINOR。

- **MINOR（generate_test 不做检出检查）：已按“文档写明，C2 核对”处理，有一处措辞问题。** test_data.py:138-139 的文档写入了一个尚不存在的文件，见第二节 MINOR。
  - 包内只有 main 调用 generate_test（test_data.py:178；grep 已核对，静态）。
  - main 的顺序为 code_commit → check_commit_preconditions → refuse_if_st10_record → generate_test（test_data.py:175-178）。

- **MINOR（BLOCKED 文字建议“push the local commits”）：已修且正确。**
  - 新文字见 testgate.py:212-214。探针输出 c1b_04:589 中可见新文字（已验证）。
  - 本地领先的提交不是 TEST 路径产生的时，“fast-forward pull”帮不上忙。但这条消息以“report to the Owner”结尾，不会导致多评，不另列问题。

- **MINOR（测试名）：已修且正确。** 已改名为 test_a_marker_deleted_in_a_later_commit_is_not_searched（tests:381）。

- **data-auditor MINOR-1（session 为 None 时 AttributeError）：已修且正确。**
  - claim_checkpoint 与 finish 的守卫改为以 `isinstance(session, TestSession)` 开头（testgate.py:510、522），与 require_test_session（:488）一致。
  - 新测试（tests:640、750-751）能区分旧代码：旧写法 `_LIVE.get(None) is not None` 为假，接着访问 `session.evaluated` 或 `session.marker_commit` 会抛 AttributeError，而 refused 只接受 ImplementationFail。
  - 变异「finish: any session」测出（c1b_04:796-797，已验证）。copy.copy 的会话越过被削弱的守卫后，以“models not evaluated”被拒，消息不匹配，所以测试失败。

- **登记、不修的三项：本树中尚未登记。**
  - 三项为：_where 的失败放行；TEST 写出之后、ST10 记录之前崩溃；报告的引用。
  - 调用文字说会在报告提交中登记。本树中 IMPL_C_REPORT.md:46 仍引用不存在的节；c1b_01、c1b_03 都没有标明已被取代（*.md 中 grep c1b_0 无匹配，已验证）。见第二节 MINOR。

- **变异脚本：符合。**
  - c1b_mutate.py 未改动（diff stat 中没有它）。
  - c1b_mutate_fix1.py 共 78 个变异，全部测出；前后 src+tests 哈希相同（c1b_04:842-844，已验证）。
  - c1b_03 记录了 77/78，「pushed marker bytes not checked」未测出（c1b_03:324-325，已验证），与 Executor 的说明一致：test_a_commit_of_another_begin_between_commit_and_push_is_blocked 中，父提交也含标记。
  - 两次运行的 src/tests diff 哈希不同（607e767e… vs a229d493…，c1b_03:52、c1b_04:486）：c1b_03 运行之后又改动了 src/tests（补了第三个测试）。我无法独立复算暂存树 ae5fcb2f 的 src/tests 是否等于 c1b_04 运行时的索引 5b1b3a0e（未验证），这一点依据调用文字的说明。

**二、问题列表**

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:472-479（文档 :56-63）；/home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:701-717 | 第 1 轮 MAJOR 1 沿用，仍待 Review Gate 确认。evaluate_model(split="test") 每次调用只做本地检查，不 fetch。<br>- 新测试证实：begin 之后若远端被推进（例如 auditor 改了计数），剩余模型会照常评完，直到 finish 才 BLOCKED（视为已评）。<br>- 不确定之处：这与裁决第 1 项「所有 TEST 路径」的字面不同，但在防范对象内我未找到由此产生的评两次或 ST10 不成立仍评的路径。<br>（静态，未验证；测试通过见 c1b_04:558，已验证） | `if local != PILOT_BRANCH or head != session.marker_commit:`；测试中 `evaluate(env, env.base_model, s, "N", data=data)        # no fetch: the call goes on although the remote moved` | 由 Review Gate 裁决。确认后代码不改；RUNBOOK（C3）写明 begin 到 finish 之间任何人不得向该分支推送。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:407-422 | test_a_commit_of_another_begin_between_commit_and_push_is_blocked 不能单独检验任何一项检查，文档只写了「字节不同」。<br>这个情形里，推送的提交字节不同，父提交也含本次的标记，两项检查都会触发。c1b_03:324-325 证实：去掉字节检查后该测试仍通过。<br>它作为情形二的组合回归测试是合理的。两项检查的单独区分由另外两个测试承担（c1b_04:756-759）。<br>（已验证） | 文档 `the pushed commit holds the other marker's bytes`；c1b_03:325 `passed test_a_commit_of_another_begin_between_commit_and_push_is_blocked` | 文档补一句「父提交也含本次标记，两项检查都会拒绝；单项由另外两个测试区分」。或者再断言两个进程都 BLOCKED（模拟另一个进程的 begin 也走到检查）。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:113-116, 464 | _blob 把 `git cat-file blob` 的任何失败都当作「没有这个 blob」。<br>- 第一项比较（`!= blob`）因此偏向拒绝，安全。<br>- 父提交检查（`is not None`）则偏向放行：git 读取出错时，当作父提交没有标记。<br>这与模块文档 :70「a failing git command that reads the repository ImplementationFail」不一致，与第 1 轮登记的 _where 属同一类，在防范对象之外（cat-file 只读，实际风险很低）。<br>（静态，未验证） | `return r.stdout if r.returncode == 0 else None`；`_blob(root, "%s^:%s" % (head, MARKER_REL)) is not None` | 与 _where 一并登记。或者用 `git ls-tree <head>^ -- <rel>` 区分「不存在」（返回 0、输出为空）与「出错」（非 0 → ImplementationFail）。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:720-728 | test_s_mapping_on_test_is_refused_before_the_gate 在 CPU 上测出变异，靠的是 require_gpu 先抛 GPU_REFUSAL（而不是 ValueError），不是靠 `s.evaluated == set()`。<br>它所防的危害是「先登记、再丢弃结果」，而这一危害在测试中从未出现：变异后调用在 GPU 检查处就停了，走不到登记。<br>检查只要位于 require_gpu 之前，现在的写法就是对的，测试结论也成立。<br>（静态；变异测出见 c1b_04:760-761，已验证） | `E.evaluate_model(..., M.FORMAL_MODE, "cpu", split="test", with_s_mapping=True, ...)`，没有替换 require_gpu | 可选：仿照 test_evaluate_model_claims_after_the_gpu_check，替换 E.require_gpu 与各打分函数，让变异后的登记真的发生，再由 `s.evaluated == set()` 失败。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:138-139 | 文档把「run_pilot.py runs main as a subprocess」写成现状，但 metrix/e1-pilot/run_pilot.py 尚不存在（Glob 无匹配，已验证）。读者可能以为这一点已实现并经过审查。 | `(run_pilot.py runs main as a subprocess)` | 改为写明这是 C2 的要求，例如「run_pilot.py（C2）须以子进程运行 main，不得直接调用本函数」，并在 C2 审查时核对。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:838-864 | test_driver_checks_the_commit_preconditions_before_generating 没有替换 sleep。在「preconditions: dry-run push not checked」变异下，驱动会真实重试推送并睡 14 s（c1b_04:744 用时 19.74 s；c1b_02 中同一变异为 19.30 s）。<br>只影响变异运行的耗时，不影响结论。这也更正了我第 1 轮把该耗时归因于 test_driver_push_refused… 的说法。<br>（耗时已验证；归因为静态推断，未验证） | `stub_driver(env, monkeypatch, generated)`，无 `monkeypatch.setattr(TG.time, "sleep", ...)` | 可选：在该测试中同样替换 TG.time.sleep。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:46；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1b_01_checks.txt；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1b_03_checks_fix.txt；/home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md | 第 1 轮 MINOR 沿用，本树中仍未就位。<br>- 报告引用的 C1 节「第二次送审(按裁决修改)」不存在。<br>- c1b_01 与 c1b_03 的文件头没有标明已被取代（c1b_03 的文件头与 c1b_04 形式相同，结论行为 RESULT: FAIL）。<br>- 登记不修的各项（_where 失败放行、TEST 写出后崩溃可再次生成、本轮的 _blob）尚未写入 DEFERRED_MINORS。<br>调用文字说这些在报告提交中完成。<br>（已验证：*.md 中 grep「第二次送审」只命中 IMPL_C_REPORT.md:46 这一处引用；grep c1b_0 无匹配） | `落实情况写在 C1 节“第二次送审(按裁决修改)”`；c1b_03:410 `RESULT: FAIL` | 在报告提交中写入该节；标明 c1b_01、c1b_03 已被取代，并写明各自被哪份记录取代、原因；在 DEFERRED_MINORS 中登记上述各项。

**三、其他已核对、无问题的项**
- **原始输出（已验证）：**
  - 全部 pytest：298 passed（c1b_04:558）；
  - 变异：78 个全部测出，前后 src+tests 哈希相同（c1b_04:842-844）；
  - 四个冻结哈希：PASS；数据逐字节重新生成：一致（c1b_04:508-521）；
  - TEST 生成器在当前状态拒绝，没有产物（c1b_04:523-539）；
  - outside_metrix_check：PASS（c1b_04:540-551）；
  - 探针：第二个克隆完整走完 begin → 16 个 gate → finish，标记为 EVALUATED（c1b_04:592-620）。
- **新增代码（静态阅读，未验证）：**
  - 没有未用的 import 或函数：_blob 只在 begin 中使用；c1b_mutate_fix1.py 的常量都被使用。
  - 没有写死协议数值，也没有新增读取 TEST 的路径；测试只用人造行和临时仓库。
  - 非 formal 模式下 TEST 评测仍被拒（evaluate.py:325-327）。
  - begin 的 BLOCKED 发生在创建会话、写入 _LIVE 之前，失败时不会残留会话（testgate.py:464-469）。
- **c1b_mutate_fix1.py（静态阅读，未验证）：**
  - 替换串必须恰好匹配一次；
  - 每个变异指名应当失败的测试，不用 -x，只有全部指名的测试都失败才算测出；
  - 运行后逐字节恢复文件；
  - 新增 3 个变异的替换串与当前源码一致（c1b_04 中没有「NOT APPLICABLE」）。

结论：PASS
