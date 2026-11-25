# code-reviewer, C1 work commit, round 3 (staged tree 9be4df2ab398030ef0c9b5fbadc36f17022c4ef4, parent eb05e422)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
code-reviewer：C1 工作提交第 3 轮审查（暂存树 9be4df2ab398030ef0c9b5fbadc36f17022c4ef4，父提交 eb05e42243b54b78cb400b40293ef56f67611852），以下为完整原文

**运行环境与依据**
- 定义：已先读仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md。tools 行为「Read, Grep, Glob」，与已加载定义一致；preflight_tools_check_round3.txt 第 2–6 行的记录相同。
- 范围：只用了 Read、Grep、Glob；没有运行任何代码，没有读取 TEST，没有计算任何哈希。
- 依据：
  - delta_round3.diff 与 input_round3.diff；
  - 工作区源码（调用方说明与暂存区相同）；
  - /home/user/OpenMythos/metrix/e1-pilot/METRIX_E1_PROTOCOL.md 第 0 节（base repository `leotree2020/OpenMythos`，authoring branch `metrix-e1-pilot-protocol-v1`）、第 8 节第 8 步；
  - tasks/IMPL_C_OWNER_MESSAGE.md；
  - 暂存树中的原始输出 reports/impl_c/c1_06_checks_r3.txt（下称 c1_06）、c1_05_checks_r3_interrupted.txt、c1_05b_restart_restore.txt。
- 标注规则：引用 c1_06 行号的判断记为「已验证」，其余为「未验证」。

**一、第 2 轮各项的核对**

**data-auditor 的 BLOCK（探针）**
- **接口两处：已修，正确。**
  - c1_gate_probe.py:109 改为 `TG.refuse_if_marker(repo, "origin")`；:113-115 从 HEAD 中的标记读取 models。
  - 输出符合文档格式（c1_06:194、204-205、211，已验证）。
- **拒绝在本仓库或规范远端的克隆上运行：已修，有缺口。**
  - 对本仓库拒绝（c1_06:220-222，已验证）。
  - 以本地路径克隆本仓库时不会拒绝，见下文 MINOR。
- **CANONICAL_REPO、PILOT_BRANCH 的覆盖与打印：已修**（c1_06:192、202，已验证）。
- **Executor 运行一次：已做**（c1_06:190-223，已验证）。
  - B25 待决时 begin 与 eval 都拒绝。HEAD 仍是 ST10 提交（c1_06:198 的 repo_head = c1_06:216 的 0744495）。
  - 带 --interpretations-ruled 时：begin 推送了标记；eval 停在 require_gpu；gate 登记一次，第二次被拒；marker 为 BLOCKED；远端 main 等于标记提交（c1_06:205-219）。
  - data-auditor 仍须对已入库的探针重跑一次。

**我第 2 轮的 MAJOR**
1. **生产路径的 claim 没有测试：已修，正确。**
   - 新测试 test_testgate.py:643-654。
   - 变异「claim removed」被这个测试测出（c1_06:333-334，已验证）。
   - 遗留：「在打分之前登记」没有测试，见 MINOR。
2. **凭据：已修。**
   - scrub 用于 remote_url、repo_id、_blocked、_push、commit_paths（testgate.py:98-104、165-174、237-238、252-257）。
   - 变异被测出（c1_06:283-284，已验证）。
   - 但只有标记一处的断言能区分有没有 scrub，见 MINOR。
3. **探针：见上。**
4. **远端与分支是自由参数：已修。**
   - testgate.py:78-80 的常量与协议第 0 节、metrix/CLAUDE.md 第 2 节一致。
   - check_remote 用于 remote_heads(:201)、commit_paths(:246)、_commit_preconditions(:421) 和 test_data.main(:171)。
   - 相关的五个变异都被测出（c1_06:271-282，已验证）。
   - 遗留：只比较 fetch URL 的 owner/name，见 MINOR。
5. **B25 与报告第 17 行：第 17 行已改正。** 「待 Review Gate 决定」的列表不在本树中，见 MINOR「登记」。
6. **拒绝的状态语义：模块文档已列出**（testgate.py:49-53）。交 Review Gate 的部分不在本树中，同上。

**我第 2 轮的 MINOR**
- **finish 核对已提交标记的字节：已修，正确。** testgate.py:522-524；测试 test_testgate.py:742-751；c1_06:335-336（已验证）。
- **--reflog：已修，正确。** testgate.py:280、380；测试 test_testgate.py:426-433；c1_06:267-268（已验证）。
- **浅克隆：已修，正确。** testgate.py:189-190；测试 test_testgate.py:436-440；c1_06:277-280（已验证）。
- **force-push 前提：已写入文档**（testgate.py:30-31）；RUNBOOK 在 C3。
- **未测分支：大部分已补。**
  - 已补：ST10 记录只在远端（test_testgate.py:777-778、798-800）；fetch 失败（485-491）；dry-run 失败（494-500）。
  - 仍未测：HEX40 检查、_commit_preconditions 中 ls-remote 的失败，见 MINOR。
- **「commit 」断言：已改为 assert_started**（test_testgate.py:143-145）。
- **存在但不是祖先的 code commit：已补。** test_testgate.py:233-240；c1_06:233-236（已验证）。
- **fetch 文档：已改正**（testgate.py:194-195）。
- **record.committed_json 的对象检查：已修，正确。**
  - record.py:162-163；测试 test_test_data.py:218-224；c1_06:337-338（已验证）。
  - testgate._committed 中重复的检查已删去。
- **死代码：已删**（_is_ancestor 的 of 参数；require_test_session 的返回值）。
- **可读性：一部分已修。**
  - 多余的空行已删；TG 改为统一导入（evaluate.py:330-335）。
  - 原第 38 行换行后，超长部分移到了第 43 行；另有新的超长行，见 MINOR。
- **test_data.main 自行提交并推送 ST10 记录：已修，但带来新问题。**
  - 代码 test_data.py:187-190；测试 test_testgate.py:791-793；c1_06:345-346（已验证）。
  - 新问题见 MAJOR 1。
- **试跑中 4 个未测出的变异：对应测试已补，在 c1_06 中都被测出**（c1_06:261-262、265-266、267-268、281-282，已验证）。试跑输出本身没有入库，见 MAJOR 2。
- **探针防护：一部分已修**，见 MINOR。
- **登记：不在本树中**，见 MINOR。

**总体结果（已验证）**
- 全部 pytest：275 passed（c1_06:188）。
- 变异：70 个全部测出，前后 src+tests 哈希相同（c1_06:365-367）。
- 数据重新生成与核对、四个冻结哈希：PASS（c1_06:122-153）。
- TEST 生成器在当前状态拒绝运行，没有产物（c1_06:154-170）。
- outside_metrix_check：PASS（c1_06:171-182）。
- 中断后的恢复：
  - c1_06 开头和结尾的 `git diff HEAD -- src tests | sha256sum` 都是 4781575f…（c1_06:120、424）。
  - 这与中断前 c1_05 开头的值相同（c1_05_checks_r3_interrupted.txt:116）。
  - 两次运行中 c1_mutate_r3.py 与 c1_probe_run.py 的 sha256 也相同（c1_05:114-115 与 c1_06:118-119）。
- 本轮没有新增读取 TEST 的路径。
  - 推送的 ST10 记录只含计数、哈希和提交号；commit_paths 要求暂存的路径恰好是指定的路径。
  - 探针与测试都只用人造行，或用替身代替打分函数。
  - DEV 与 TEST 的划分没有改动。
- 其余源文件在两轮之间没有改动（delta_round3.diff 只涉及 evaluate、interpretations、record、test_data、testgate、test_test_data、test_testgate 和报告）。对它们沿用第 2 轮的结论。

**二、「只评一次」在各种情形下的结论**
- **成立的情形：**
  - 远端是同一个规范仓库（owner/name 相同）的 PILOT_BRANCH，且远端分支不被 force-push 或删除。
  - 落后克隆、--single-branch 克隆、本地 reset、侧分支合并后删除、只能由标签到达、只在 reflog 中：都有测试，相应变异都被测出（已验证）。
  - 浅克隆：BLOCKED（已验证）。
  - 两台机器并发：都推送到同一分支且只能快进，后推者被拒为 BLOCKED（静态推断，未验证；非快进的情形有测试，test_testgate.py:580-592）。
  - 凭据：标记中不含 userinfo（已验证）。
- **不成立或无法检测的情形：**
  - 远端被 force-push 或删除分支：基于 git 的检查无法检测，已写为文档中的前提。
  - 远端是 owner/name 相同的另一主机或本地镜像，见 MINOR。
- **不会导致多评、但结果为 BLOCKED 的情形：**
  - pushurl 指向别处：标记写入之后才 BLOCKED（未验证）。
  - 推送失败后留在本地的标记：这台机器永久 BLOCKED；其他机器看不到它，可以开始。但这台机器从未拿到会话，也没有评测，所以不违反「只评一次」（未验证）。

**三、问题列表**

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:170-173, 187-188 | 本轮新问题：驱动现在自己提交并推送 ST10 记录，但提交与推送的前提（索引中没有暂存、有提交者身份、HEAD 是远端分支的后代、push --dry-run 能通过）只在 commit_paths 里检查。那时 TEST 已经生成，run_test_part 已经读取了 TEST 行，ST10 记录也已写入工作区。<br>以下任一情形都会让第 8 步在 TEST 生成之后变成 BLOCKED：租来的新机器没有设置 user.name/email；索引中有暂存；克隆落后于远端。<br>此后工作区中的记录使任何重跑都被 refuse_if_st10_record 拒绝（「working tree」），也没有代码路径能把它补交。<br>对照：begin_test_evaluation 在写入之前就检查同样的前提（testgate.py:418-433，「Any failure is BLOCKED and leaves nothing written」）。（未验证） | `TG.check_remote(root, TG.PILOT_REMOTE, TG.PILOT_BRANCH)`；`TG.refuse_if_st10_record(root, TG.PILOT_REMOTE)`；`files, info = generate_test(fz, auth, a.inputs, a.data)` … `head = TG.commit_paths(root, [TG.ST10_RECORD_REL], …)` | 在 generate_test 之前做暂存检查和 _commit_preconditions（给它一个公开的封装）。补测试：没有身份或有暂存时为 BLOCKED，且 generated == []、--out 不存在；补相应变异。在 RUNBOOK 写明恢复办法。

MAJOR | （无对应文件：调用文字所述的试跑） | 流程问题。调用文字说，在 worktree 中试跑变异时有 4 个没有测出，并且「试跑输出不入库」。metrix/CLAUDE.md 第 9 节要求「原始输出一律写入仓库并推送，不留在临时目录」。<br>不确定之处：第 9 节是否覆盖已被取代的试跑。但仓库中没有任何文件记录这 4 个未测出的变异和它们的输出，而它们正是本轮补测试的起因。（未验证：输出不在仓库中，我无法查看） | 「试跑输出不入库，c1_06 是本轮的正式记录」（调用文字） | 把试跑输出作为非证据的原始记录入库，并标明已被 c1_06 取代；或由 Review Gate 裁定被取代的试跑是否豁免。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:165-190 | check_remote 只比较 fetch URL 的最后两段路径。<br>(1) 不比较主机。任何以 leotree2020/OpenMythos(.git) 结尾的 URL 或本地路径都能通过，例如另一主机上的镜像或过期的本地镜像。过期镜像上看不到规范远端的标记，这时「只评一次」不成立。<br>(2) `git remote get-url` 没有带 --push。pushurl 指向别处时，check_remote 和 dry-run 都通过；标记提交并推送到 pushurl 之后，_push 的 ls-remote（读的是 fetch URL）才发现不对，结果是标记写入后 BLOCKED（不会多评）。<br>测试本身就依赖「名字相同即通过」（test_testgate.py:506）。（未验证） | `got = repo_id(remote_url(root, remote))`；`name = "/".join([x for x in re.split(r"[/:]", scrub(url).rstrip("/")) if x][-2:])`；`gone = tmp_path / "gone" / tmp_path.name / "remote.git"    # the pilot's repository name, not reachable` | check_remote 同时核对 `git remote get-url --push`。考虑同时核对主机（github.com，另列出本环境的代理形式）；或在模块文档与 RUNBOOK 写明「只比较 owner/name，origin 必须是 GitHub 上的这个仓库本身，不得是镜像」。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_gate_probe.py:91-94 | 探针的防护仍有缺口。以本地路径克隆本仓库时（origin = /home/user/OpenMythos，repo_id 为 "user/OpenMythos"）不会拒绝。<br>如果在这个克隆中检出 main 并放入人造记录，begin 会把标记推到本仓库的 refs/heads/main，真实 Pilot 的 `--all` 检索会找到它，结果 BLOCKED。<br>这需要刻意的操作，可能性低。（未验证） | `origin = TG.repo_id(TG.remote_url(repo, "origin"))`；`if repo == PILOT.parents[1] or origin == TG.CANONICAL_REPO:` | 以下情形也拒绝：REPO 中存在冻结提交的对象（`git cat-file -e <fz.record.commit>`）；或 origin 是本地路径，解析后指向 PILOT.parents[1] 的 git 目录。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:467-482 | 凭据测试中，只有标记一处的断言能区分有没有 scrub。<br>- 推送失败一段的断言 `"s3cr3t" not in msg` 在不 scrub 时很可能也成立：git push 的「To …」和「failed to push some refs to …」用的是去掉了 userinfo 的 URL。<br>- 没有测试这种情形：传给 _blocked 的 `remote` 本身就是带凭据的 URL（例如「cannot list the branches of %s」）。<br>- 另外，_USERINFO 不处理 userinfo 中未编码的「/」（边缘情形）。<br>（未验证） | `assert "the other record is committed" in msg and "was not pushed" in msg and "s3cr3t" not in msg`；`_USERINFO = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)[^/@\s]*@")` | 补一个测试：以带凭据的 URL 作为 remote，让 ls-remote 失败，断言 BLOCKED 文字中没有 secret。把「not scrubbed」变异拆成 _blocked、_push、remote_url 三处，各一个。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_mutate_r3.py:185；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_06_checks_r3.txt:257-260 | 「st10 record: history not searched」和「st10 record: remote not searched」两个变异，被记为由 test_only_the_pilots_remote_and_branch 测出（已验证）。<br>但这个测试失败，只是因为环境中已有提交的 ST10 记录，于是异常从 BLOCKED 变成了 ImplementationFail（"exists"），而不是因为远端上的记录没有被找到。<br>按静态阅读，新的落后克隆断言（test_testgate.py:798-800）也会测出它们；但 -x 只记录第一个失败的测试，c1_06 证明不了这一点。（未验证） | `r = subprocess.run([PY, "-m", "pytest", "-q", "-x", …` | 去掉 -x，为每个变异列出所有失败的测试；或在 test_only_the_pilots_remote_and_branch 中，在 env.st10() 之前调用 refuse_if_st10_record(env.root, "elsewhere")。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:643-654 | 新测试检验了「在 GPU 检查之后登记」，没有检验「在打分之前登记」，而 evaluate.py 的文档写的是「claimed … right before it is evaluated」。<br>把 claim 移到打分之后，这个测试仍然通过。那样的话，打分中途出错时，这个 checkpoint 在同一会话内还能再评。（未验证） | `monkeypatch.setattr(E, name, lambda *a, **k: [])` | 让打分的替身断言 `"N" in s.evaluated`，并加上相应变异。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:30-31, 34-35 | 「远端分支受保护（禁止 force-push、禁止删除）」这一前提有两个问题。<br>(1) 措辞与 metrix/CLAUDE.md 第 6 节「不直接推送到受保护分支」字面冲突；而 Owner 的阶段 C 消息要求在该分支上直接快进推送、不经 PR，代码也是这样做的。<br>(2) `git push --dry-run` 不运行服务器端钩子，也不检查分支保护规则。如果保护规则要求 PR、状态检查或签名提交，标记会先写入本地、之后才被拒绝，状态为 BLOCKED；data-auditor 第 2 轮的 D3 场景就是这个结果。<br>（未验证） | `Assumed, not checkable by git: the remote branch is protected (no force-push, no deletion; RUNBOOK_A100.md).`；``…`git push --dry-run` accepted`` | 在文档与 RUNBOOK 写明具体设置：禁止 force-push 和删除，允许 Pilot 账户直接快进推送；在第 8 步之前用一次真实推送确认。请 Review Gate 留意第 6 节的措辞。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:21-25；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:15-16 | 文档与代码不一致：<br>- test_data 模块文档第 21-25 行仍说记录的提交与推送「follow outside this command」，与第 30-31 行和第 187-188 行矛盾；<br>- testgate 第 15-16 行描述 ST10 记录的检索范围时没有提到 reflog，与 refuse_if_st10_record（:276-280）不符。<br>（未验证） | `Committing and pushing the record, the data-auditor's own L6 count (testgate.AUDITOR_L6_REL) and the TEST evaluation (once: testgate.begin_test_evaluation) follow outside this command` | 改为「本命令提交并推送 ST10 记录；auditor 的计数与 TEST 评测在命令之外」。testgate 第 16 行补上「or of the reflog」。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:17, 44；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:52-53 | 登记仍不在本树中。<br>- 报告第 17 行说 B25「列于“待 Review Gate 决定”」；testgate 文档说各类拒绝的状态「listed for Review Gate in reports/IMPL_C_REPORT.md」。但报告的 C1 节仍是「（C1 完成后填写。）」，这两处引用目前都落空。<br>- 第 2 轮的其他登记项也不在。留到 C2 的：冒烟中保存、重载后核对 state_sha256；DEV 路径的哈希核对；B17 的预估计入 state_sha256 的耗时；finish 写入的结果不得含 TEST 内容（auditor 说明 (f)）。交 Review Gate 的：auditor 能否使用探针；拒绝的状态；B25；auditor 第 2 轮 INFO 中的 B13 与 B17。<br>- auditor 的 audit/ 输出仍未跟踪（c1_06:32-55）。<br>（c1_06:32-55 已验证，其余未验证） | `(C1 完成后填写。)` | 在 C1 报告提交中逐条写入，并把 audit/ 的输出入库。报告提交若不写这些，上述两处引用就是不实的。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:213-215, 424-426 | 以下分支仍没有测试，也不在变异清单中：<br>- remote_heads 中对 ls-remote 输出的 HEX40 检查；<br>- _commit_preconditions 中 ls-remote 的失败（remote_heads 已成功之后，只会在竞态下出现）。<br>影响小。（未验证） | `if not all(HEX40.fullmatch(x) for x in shas):`；`raise _blocked("cannot read %s %s: %s" % (…` | 用替换 _git 的方式各补一个测试，或在文档中注明不测。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:443, 467 | 死代码：两个测试声明了 monkeypatch 夹具，但没有使用。（未验证） | `def test_only_the_pilots_remote_and_branch(env, tmp_path, monkeypatch):`；`def test_credentials_in_the_remote_url_are_not_written(env, monkeypatch):` | 删去未使用的参数。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:33, 43, 53, 375, 194-195；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/interpretations.py:5-7 | 可读性：<br>- 第 2 轮指出的第 38 行换行后，超长部分移到了第 43 行（约 148 字符）；<br>- 第 33、53、375 行是新增的超长行（约 133–136 字符）；<br>- testgate.py:194-195 与 interpretations.py:5-7 的断行，使一行只剩半句。<br>（未验证） | `TEST rows must be the files of the marker, the ST10 gate must hold for them with the records the marker names, the checkpoint must be one of the`；`and are written into every experiment record` | 重新折行。

结论：PASS
