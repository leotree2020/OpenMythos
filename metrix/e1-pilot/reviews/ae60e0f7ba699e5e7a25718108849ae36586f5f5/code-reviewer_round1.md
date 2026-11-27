# code-reviewer, C1 second submission, round 1 (staged tree 365960a0e2c5cc28869be9ed44a08d4170389633, parent 5f5cd51e)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
code-reviewer：C1 第二次送审第 1 轮（暂存树 365960a0e2c5cc28869be9ed44a08d4170389633，父提交 5f5cd51e），完整原文

**运行环境与依据**
- 定义：已先读仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，tools 行为「Read, Grep, Glob」。
- 本轮只用了 Read、Grep、Glob：没有运行任何代码，没有读取 TEST，没有计算哈希。
- 依据：input.diff、delta_from_round3.diff，工作区源码（调用文字说明它与暂存区相同），tasks/IMPL_C1_RULING.md、tasks/IMPL_C_OWNER_MESSAGE.md，协议第 3 节、第 8 节第 8 步、第 11 节 ST10，以及暂存的原始输出 reports/impl_c/c1b_02_checks.txt（下称 c1b_02）和 c1b_01_checks.txt（下称 c1b_01）。
- 判定范围按防范对象原文：TEST 闸门要防的是「按规则办事的 Executor 在按 RUNBOOK 操作时，意外评测 TEST 两次，或在 ST10 不成立时评测 TEST」；不防有仓库写权限者的故意篡改（改写历史、伪造记录），这类风险由 GitHub 分支保护和审查记录承担。审查按此范围判定：范围外的边缘情况记为 MINOR 并登记，不作为 BLOCKER。

**一、裁决第 1–9 项逐条核对**

- **第 1 项：基本符合。**
  - check_checkout 依次检查 owner/name、检出分支（分离 HEAD 时为 "HEAD"）、不是浅克隆、`fetch --no-tags`、HEAD == FETCH_HEAD（testgate.py:185-206）。
  - 标记和记录只在两处查找：工作区，以及该最新提交的文件树（_where，:209-214）。
  - reflog、--all、remote_heads、check_remote 已无残留（grep 无匹配）。
  - 驱动、begin、finish 都会 fetch。相关变异全部测出（c1b_02:224-274，已验证）。
  - 评测调用不 fetch 的读法：见 MAJOR 1。库函数 generate_test 和 run_test_part 本身不做检出检查：见 MINOR 5。
- **第 2 项：符合。**
  - test_data.main 在 generate_test 之前调用 code_commit、check_commit_preconditions、refuse_if_st10_record（test_data.py:174-177）。
  - 生成之后推送被拒时：BLOCKED，what 中写明「TEST counts as generated…」，重跑在生成之前被拒（test_testgate.py:786-802）。
  - 变异测出：c1b_02:302-305、312-314、361-363（已验证）。
- **第 3 项：符合。**
  - B25 的 status 为 ACCEPTED_C1，ruling 为 RULING_REF_C1；text 写明计算定义，与 train.state_sha256（train.py:283-291）逐项一致。
  - pending() 为 []。
  - 证据：c1b_02:108 共 293 passed；变异 c1b_02:366-371 测出（已验证）。
  - 「C2 冒烟中保存并重载 checkpoint」属于 C2。
- **第 4 项：符合。** 状态词列在模块文档 testgate.py:66-71。
- **第 5 项：符合。** 探针的新接口按入库版本跑过一次（c1b_02:110-181，已验证）。
- **第 6 项：符合。** 不比较主机，不检索标签；模块文档写明了 GitHub 设置（testgate.py:18-19）；RUNBOOK 在 C3。
- **第 7 项：符合，有一处待补。** c1b_01 已入库，但树中没有标明它已被取代，见 MINOR 11。
  - 两次运行所测的 src/tests 相同：哈希都是 adfeb518…（c1b_01:387 = c1b_02:385；diff 哈希 c1b_01:92 = c1b_02:36，已验证）。
- **第 8 项：不涉及本次审查。**
- **第 9 项：符合，有一处待补。** 轮次已从 1 重新计；防范对象以外各项的登记尚未写入，见 MINOR 11。

**二、在防范对象范围内的路径分析**

- **崩溃后重跑：成立。**
  - 标记在工作区或远端最新提交中，都会 BLOCKED（test_testgate.py:335-341、526-539、555-565）。
  - 结果文件在工作区时为 TestAlreadyEvaluated（refuse_if_marker）。
- **另一台机器：成立。**
  - 落后时 BLOCKED；快进之后标记在远端最新提交中被找到（:343-361）。
  - 两个克隆并发时，推送只能快进，后推者 BLOCKED（静态推断，未验证）。
- **推送失败、生成之后推送被拒：成立。** 本地提交领先远端，check_checkout 为 BLOCKED（:526-539、786-802）。
- **ST10 不成立：成立。** begin 与每次评测调用都重跑 st10_check：
  - 记录已提交，且与授权、行哈希绑定；
  - code commit 是 HEAD 的祖先；
  - 计数为整数，按冻结上限重新判定；
  - auditor 的计数一致。
  - 测试 :213-297；变异 c1b_02:183-211（已验证）。
- **同一克隆中两个并发进程：不成立。** 见 MAJOR 2。

**三、问题列表**

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:458-465, 468-477（文档 :54-58） | 评测调用不 fetch 的读法。<br>- 裁决第 1 项字面要求「所有 TEST 路径……HEAD 等于 fetch 后远端该分支的最新提交，否则 BLOCKED」。evaluate_model(split="test") 每次调用只在本地核对「PILOT_BRANCH，且 HEAD == 标记提交」，不 fetch。<br>- 我的判断：在防范对象范围内，这不会打开「评两次」或「ST10 不成立仍评」的路径。<br>　1）另一次评测只能经 begin 开始，而 begin 会 fetch，并在远端最新提交的文件树中看到标记。<br>　2）ST10 记录与 auditor 计数在标记提交中固定，每次调用仍重跑 st10_check。<br>　3）如果每次调用都 fetch，网络中断就会让评测中途 BLOCKED（按补充裁决 4 视为已评）。<br>- 不确定之处：这与裁决字面不同，需要 Review Gate 确认。唯一的实际差别是：begin 之后若有人向远端推送（例如 auditor 改了计数），剩余模型仍会评完，到 finish 才 BLOCKED。<br>（静态分析，未验证） | `if local != PILOT_BRANCH or head != session.marker_commit:`；文档 `the calls do not fetch again` | 请 Review Gate 确认这一读法。确认后代码不必改，但须在 RUNBOOK 写明：begin 到 finish 之间任何人不得向该分支推送（否则 finish BLOCKED，视为已评）。另补一个测试固定这一行为（见 MINOR 7）。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:438-455, 474-477（及 :217-229、:235） | 删去「已提交标记等于本会话所写」的比较后，同一克隆中两个并发的 begin 可以都拿到会话。调用文字说这项比较「已不可能失败」，在这种情形下不成立。<br>原因：begin 只在第一次 fetch 后查标记（refuse_if_marker）；第二次 fetch（check_commit_preconditions）只比较 HEAD 与远端最新提交，不再查标记。<br>**情形一（交错较宽）：**<br>　1）p2 在 p1 写标记之前通过 refuse_if_marker。<br>　2）p1 提交并推送 M1，拿到会话，开始评 N。<br>　3）p2 此时 HEAD = M1 = 远端最新提交，check_commit_preconditions 通过。<br>　4）p2 写 S2（与 M1 的内容不同），提交 M2（父为 M1），快进推送成功，拿到第二个会话。<br>　5）p1 已在进行的 N 照常评完，下一次调用才 BLOCKED；p2 评完全部模型。结果是 N 被评两次。<br>**情形二（交错更紧）：** p2 的提交落在 p1 提交与 p1 的 _push 读取 HEAD 之间。p1 推送的就是 M2；p2 的推送为 up-to-date，ls-remote 也是 M2。两个会话的 marker_commit 都是 M2，而 require_test_session 不比较标记中的 session_id，于是两个进程都评完全部模型。<br>不确定之处：同一克隆在数秒窗口内被误启动两次，是否算「按 RUNBOOK 操作时意外」。若 Review Gate 认为算，这是 BLOCKER 级缺口。<br>（静态推断，未验证） | `check_commit_preconditions(root, "the TEST marker")`（不查标记）；`head = commit_paths(root, [MARKER_REL], …)`；`session = TestSession(session_id, head)`；`head = _git(root, "rev-parse", "HEAD").stdout.strip()`（_push 开头）；require_test_session 中没有 `marker.get("session_id")` 的比较 | 修复代价很小，任选其一或都做：<br>- begin 在 commit_paths 返回后核对两点，否则 BLOCKED：`<head>:MARKER_REL` 的字节等于本会话写的 blob；`<head>^` 中没有标记（`git cat-file -e <head>^:MARKER_REL` 失败）。<br>- require_test_session 与 finish 核对 `marker["session_id"] == session.session_id`。<br>补测试与变异，例如在 commit_paths 之前模拟另一进程写入并提交。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:322-347 | split="test" 且 with_s_mapping=True 时，`split != "dev"` 的检查在登记与全部打分之后才执行。<br>后果：模型已登记，TEST 已评完，然后 ValueError 丢掉结果；该 checkpoint 在会话中不能再评，finish 无法完成，最终为「标记无结果 → 视为已评，BLOCKED」。不会评两次，但白白用掉唯一一次 TEST 评测。<br>（未验证） | `TG.claim_checkpoint(test_session, checkpoint_name)` … `if with_s_mapping:` / `if split != "dev": raise ValueError(...)` | 把 with_s_mapping 与 split 的参数检查移到函数开头、TEST 闸门之前。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:795；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:249 | `monkeypatch.setattr(TG.time, "sleep", …)` 不起作用。<br>commit_paths 的默认参数 `sleep=time.sleep` 在定义时就绑定了原函数，test_data.main 又不传 sleep，所以驱动测试遇到推送失败时会真实睡 2+4+8 = 14 s。<br>旁证：c1b_02:294 中「preconditions: dry-run push not checked」用时 19.30 s，其余同类约 4–6 s。只影响测试耗时，不影响结论。<br>（语义为静态推断；c1b_02:294 的耗时已验证） | `monkeypatch.setattr(TG.time, "sleep", lambda s: None)`；`def commit_paths(repo_root, rels, message, what, retries=4, sleep=time.sleep):` | 默认值改为 `sleep=None`，在函数内取 `time.sleep`；或者测试改为替换 commit_paths 的 sleep。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:135-151；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:257-264 | 按裁决第 1 项「所有 TEST 路径」：库函数 generate_test 与 run_test_part 本身不做 check_checkout，只靠 main 先调用。<br>包内只有 main 调用它们，评测仍须经过 begin，所以在防范对象内不构成路径。但 C2 的 run_pilot 若直接调用 generate_test，就会绕过检出检查和「ST10 记录已存在」的检查。<br>（未验证） | `def generate_test(fz, authorization, inputs_dir, data_dir):` 只有 `LK.verify_authorization(authorization, fz)` | 在 generate_test 开头调用 TG.check_checkout；或者在文档写明 main 是唯一入口，并在 C2 审查时核对。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:204-205 | 生成之后推送被拒，重跑时 check_checkout 的 BLOCKED 文字建议「push the local commits」。<br>按裁决第 2 项，这时应由 Owner 决定是否手工提交这一个文件；照字面操作的 Executor 会自行推送。不会导致多评（之后 refuse_if_st10_record 拒绝），属于措辞问题。<br>（未验证） | `"bring the checkout to it (fast-forward pull, or push the local commits) first"` | 改为写明「由 TEST 路径产生的本地提交，须经 Owner 决定才能推送」；或者写进 RUNBOOK。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:644-665 | Executor 选择的「评测调用不 fetch」没有测试固定。<br>MOVED 的三种情形都移动了本地 HEAD。缺少这样的用例：只有远端被另一克隆推进、本地仍在标记提交时，evaluate 继续，finish 为 BLOCKED。<br>（未验证） | `MOVED = {"a_commit_after_begin": …, "the_marker_rewritten": …, "another_branch": …}` | 用 diverge(env, tmp_path) 补一个用例，断言上面两点。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:209-214 | _where 把 `git cat-file -e` 的任何失败都当作「不存在」，与模块文档 :67-69「a failing git command that reads the repository ImplementationFail」不一致：git 出错时放行。<br>tip 刚经 rev-parse 验证，实际风险很低，属于防范对象以外的边缘情况。<br>（未验证） | `if _git(root, "cat-file", "-e", "%s:%s" % (tip, rel)).returncode == 0:` | 用 `git ls-tree <tip> -- <rel>` 区分两种情况：返回 0 且输出为空表示不存在；非 0 表示出错，报 ImplementationFail。或者在文档中注明。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:381-389 | 测试名写的是「history, other refs and the reflog are not searched」，实际只构造了一种情形：标记在较早的提交中，之后被删除。没有侧分支、标签或 reflog 的情形。<br>（未验证） | `def test_history_other_refs_and_the_reflog_are_not_searched(env):` | 改名；或者补侧分支、标签各一行断言。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:177-185 | 如果在 TEST 文件写入 --out 之后、ST10 记录写入之前崩溃（例如 run_test_part 抛出），换一个 --out 或换一台机器就能再次生成 TEST（内容相同，是确定性的）。<br>不涉及评测，属于防范对象以外。<br>（未验证） | `(out / name).write_bytes(blob)` … `path, rec = TG.write_st10_record(fz, auth, report, files)` | 登记；在 RUNBOOK 写明这种情形按 BLOCKED 报告 Owner。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:46；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1b_01_checks.txt:58；/home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md:496-510 | 本树中的引用与登记尚未就位：<br>- 报告第 46 行引用的 C1 节「第二次送审(按裁决修改)」不存在。<br>- c1b_01 的文件头与 c1b_02 相同，没有标明已被 c1b_02 取代；只有调用文字说明了这一点。<br>- CC4–CC6、CC15–CC18 在 DEFERRED_MINORS 中仍写「未处理」；调用文字说会在之后的报告提交中登记。<br>（已验证：IMPL_C_REPORT.md 中 grep 不到该节；c1b_01:58；DEFERRED_MINORS.md:496-510） | `落实情况写在 C1 节“第二次送审(按裁决修改)”` | 在报告提交中完成三件事：写入该节；标明 c1b_01 已被取代（c1b_01:270-276 与 c1b_02:271-274 是同一 src/tests 哈希 adfeb518… 下的两次运行）；更新 1.29 的「处理」列。

**四、其他已核对、无问题的项**
- **原始输出（已验证）：**
  - 全部 pytest：293 passed（c1b_02:108）。
  - 变异：74 个全部测出，前后 src+tests 哈希相同（c1b_02:384-386）。
  - TEST 生成器在当前状态拒绝运行，没有任何产物（c1b_02:73-89）。
  - outside_metrix_check：PASS（c1b_02:90-101）。
  - 四个冻结哈希：PASS（c1b_02:58-71）。
- **c1b_mutate.py：**
  - 每个变异指名应当失败的测试，不用 -x。
  - 只有全部指名的测试都失败才算测出。
  - 替换串必须恰好匹配一次，运行后逐字节恢复文件。
  - 写法合理，未发现假阳性的路径（静态阅读，未验证）。
- **数据隔离、模式隔离、数值（静态阅读，未验证）：**
  - 没有新增读取 TEST 的路径。测试、探针与 c1b_probe_run.py 只用人造行和临时仓库。
  - 非 formal 模式下 TEST 评测仍被拒（evaluate.py:323-325）。
  - 没有写死协议数值：上限取自 SPLIT_MANIFEST（leakage._rules）。CANONICAL_REPO、PILOT_BRANCH 与协议第 0 节、metrix/CLAUDE.md 第 2 节一致。
  - 被评的模型共 16 个：N，加上 F/L/A 的选定配置与 S/Y 各 3 个种子；S/Y 沿用 F 的选定配置 F3（c1b_02:155-160，已验证）。
- **死代码：** testgate、test_data、evaluate 的改动部分没有未用的 import 或函数；TestSession.marker_sha256 已删去（静态阅读，未验证）。

结论：PASS
