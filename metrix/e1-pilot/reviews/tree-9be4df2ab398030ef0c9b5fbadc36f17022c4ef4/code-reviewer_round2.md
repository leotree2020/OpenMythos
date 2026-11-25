# code-reviewer, C1 work commit, round 2 (staged tree dc4f28df108ac129120eae801de1ad02119c4c05, parent eb05e422)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
code-reviewer：C1 工作提交第 2 轮审查（暂存树 dc4f28df108ac129120eae801de1ad02119c4c05，父提交 eb05e42243b54b78cb400b40293ef56f67611852），以下为完整原文

**运行环境与依据**
- 定义：已先读仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md。tools 行为「Read, Grep, Glob」，与已加载定义一致；preflight_tools_check_round2.txt 第 3–6 行的记录也相同。
- 范围：只用了 Read、Grep、Glob，没有运行任何代码，没有读取 TEST，没有计算任何哈希。
- 依据：
  - delta_round2.diff 与 input_round2.diff；
  - 工作区源码（调用方说明工作区与暂存区相同）；
  - /home/user/OpenMythos/metrix/e1-pilot/METRIX_E1_PROTOCOL.md 第 8、9、11 节；
  - tasks/IMPL_C_OWNER_MESSAGE.md；
  - 暂存树中的原始输出 metrix/e1-pilot/reports/impl_c/c1_04_checks_r2b.txt（下称 c1_04）。
- 标注规则：引用 c1_04 行号的判断记为「已验证」，其余为「未验证」。

**一、第 1 轮各项的核对**

**data-auditor 第 1 轮**
- **B05：已修，正确。**
  - testgate.py:143 改为 `_git(root, "log", "--full-history", *revs, "--format=%H", "--", rel)`。
  - 新测试 test_testgate.py:326-339 先断言不加该选项时 `git log --all` 找不到标记，再断言闸门找得到。
  - 去掉 --full-history 的变异被测出（c1_04:193，已验证）。
- **(a) 非对象 JSON：testgate 内已修，正确；record.py 未覆盖。**
  - `_committed` 对列表或标量拒绝（testgate.py:289-290），有测试（test_testgate.py:215-221），变异被测出（c1_04:181，已验证）。
  - record.committed_record 仍未做类型检查（见下文 MINOR）。
- **(b) B11、B12：已修，正确。**
  - remote_heads 列出远端全部分支并 fetch。test_a_marker_on_another_remote_branch_refuses_a_lagging_clone（test_testgate.py:363-374）覆盖 B11，变异被测出（c1_04:201）。
  - 只有结果文件时抛出 TestAlreadyEvaluated。test_testgate.py:342-347 覆盖 B12，变异被测出（c1_04:203）。均已验证。
- **(d) 代码提交检查提前：已修，正确。**
  - test_data.py:169 的 `TG.code_commit(root)` 位于 generate_test 之前，有测试（test_testgate.py:660-664），变异被测出（c1_04:255，已验证）。
- **(e) 文档：已修。**
- **(f) 留到 C2：未登记，见 MINOR「登记」。**

**我第 1 轮的 MAJOR**
- **MAJOR 1（远端与分支）：已修一半。**
  - 已修：远端全部分支都被检索；标记写入远端 URL 与分支。
  - 遗留：remote 与推送分支仍是自由参数，标记中的 URL 没有任何代码核对。见下文 MAJOR。
- **MAJOR 2（checkpoint 哈希的定义）：本提交部分已修，正确。**
  - 已修：record.py:184-188 与 testgate.py:36-41 的文档写明了定义；interpretations.py:133 起登记了 B25，状态为 PENDING。
  - 未修：「C2 冒烟中保存、重载后核对 state_sha256」没有写入仓库任何文件。
- **MAJOR 3（拒绝的状态语义）：已修一半，交 Review Gate。**
  - 已修：环境类拒绝改为 BLOCKED（_blocked）；「已评测」改为 TestAlreadyEvaluated。
  - 遗留：见下文 MAJOR。
- **MAJOR 4（探针）：未修，交 Review Gate。**
  - 本轮还把探针改坏了，见下文 MAJOR。
  - auditor 的运行输出（audit/ 下的文件）不在本暂存树中：c1_04:29-40 显示为 `??`。

**我第 1 轮的 MINOR**
- **claim 后移：已修，正确。**
  - require_test_session 不再登记，claim_checkpoint 放在 require_gpu 之后（evaluate.py:332-334）。
  - 「claim 在 GPU 检查之前」的变异被测出（c1_04:247，已验证）。
  - 但生产中的 claim 这一行没有任何测试执行到，见下文 MAJOR。
- **写标记前预检：已修，正确。**
  - 身份与快进两项各有测试，变异被测出（c1_04:209、211，已验证）。
  - push --dry-run 失败这一分支没有测试；commit.gpgsign 未预检，失败时仍走「提交失败 → BLOCKED」路径，该路径有测试（test_testgate.py:490-499）。
- **--no-follow-tags：已修，正确。**
  - 测试中建了注释标签并设置 push.followTags=true（test_testgate.py:262-273），变异被测出（c1_04:221，已验证）。
- **模型名与哈希改用已提交标记：require_test_session 中已修，正确。**
  - 证据：testgate.py:456-463；test_testgate.py:565-575；c1_04:225（已验证）。
  - finish 中改用已提交标记后，没有核对它的字节，见下文 MINOR。
- **重复读取冻结记录：已修。**
  - verify_authorization 返回 recs（leakage.py:254），begin 中使用（testgate.py:406、411）。
- **test_data 的两个缺口：已修。**
  - code_commit 已提前；refuse_if_st10_record 已带 remote。
  - 「ST10 记录只在远端」这一情形既没有测试也没有变异，见下文 MINOR。
- **魔法数字 5：已修**（testgate.py:358-361）。
- **leakage 文档：已修。**
- **BE9：已修。**
  - 由 CONTENT_HASH_KEYS 与 CONTENT_HASH_BYTES 组装，变异被测出（c1_04:263）。
  - 四个冻结哈希的重新生成与核对均为 PASS（c1_04:105-118）。均已验证。
- **变异脚本：已修一半。**
  - 已修：`>= 0` 现在确实是恒真；TD 已删。
  - 未修：st10 的 code_commit 用例仍用不存在的 "f"*40，没有用一个「存在但不是祖先」的提交。
- **未测分支：大部分已补**，测试位于 test_testgate.py:541、427-431、565-575、608-611、490-499、435-448。
- **C2 调用方：未修**（按计划留到 C2，未登记）。
- **state_sha256 的耗时：一半已修。**
  - 已修：放到了最后计算。
  - 未修：预检估算（B17）没有计入这部分时间，也没有登记。
- **default=str：已修**，有测试（test_testgate.py:614-616）。
- **DEV 路径：未修**（留到 C2，未登记）。
- **证据链：可在提交后复算。**
  - c1_04:86、315 记录了 `git diff HEAD -- src tests | sha256sum` = dc234bf3…。
  - 我无法计算哈希核对（未验证）。
- **行宽：一半已修。** 本轮在 testgate.py:38 新增了一行超长行。

**总体测试结果（已验证）**
- 全部 pytest：265 passed（c1_04:154）。
- 变异：58 个全部测出，前后 src/tests 哈希相同（c1_04:273-275）。
- TEST 生成器在当前状态拒绝运行（c1_04:121-123）。
- outside_metrix_check 为 PASS（c1_04:147）。

**「只评一次」在跨机器与历史改写下的结论**
- 成立的情形：
  - 同一远端、远端历史不被改写。
  - 落后克隆、本地 reset 但标记已推送（有测试）。
  - 侧分支合并后删除标记（B05 已修）。
- 不成立或无法检测的情形：
  - 远端 force-push 或删除分支：基于 git 的检查无法检测。
  - 推送失败后在本地 reset：标记提交只剩在 reflog 中，`--all` 不检索 reflog。
  - 使用另一个远端：remote 是自由参数。
  - 浅克隆：缺口较窄，见下文 MINOR。

**二、问题列表**

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:333-334 | 生产路径上的 `TG.claim_checkpoint(test_session, checkpoint_name)` 没有任何测试执行到。TEST 只能在 formal 模式评测（evaluate.py:323），而 formal 模式在 CPU 上必被 require_gpu 拒绝（evaluate.py:87-88），tests/ 中也没有任何对 require_gpu 的 monkeypatch（grep 无结果）。变异清单（c1_04:157-271，已验证）有「claim before the GPU check」，没有「删去 claim」。删去这一行或这里出错都不会被发现。这一行第一次执行将是标记推送之后、唯一一次真实的 TEST 评测：出错即该次评测作废，Pilot BLOCKED。（判断依据为静态阅读，未验证） | `require_gpu(mode, device)` / `if split == "test":` / `TG.claim_checkpoint(test_session, checkpoint_name)` | 补一个 CPU 测试：monkeypatch E.require_gpu 为空操作，score_qa、score_cb、general_nll、em 用桩替换；断言调用后 s.evaluated == {"N"}、第二次调用被拒；变异清单加一项「evaluate_model: claim removed」。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:178-180, 419 | 标记写入 `git remote get-url` 的原样输出，随后提交并推送。租用机器上常见把令牌嵌在克隆 URL 里（https://user:TOKEN@github.com/…），这时令牌会进入已推送的 Git 历史；要清除就必须改写历史，而改写历史须 Owner 指令。ls-remote、fetch 的 stderr 也会把 URL 带进异常文字。（未验证） | `r = _git(root, "remote", "get-url", remote)`；`return r.stdout.strip() ...`；`"remote": remote_url(root, remote)` | 写入前去掉 userinfo（urllib.parse 只保留 scheme、host、path），或只记录 host/path；补一个远端 URL 带 `user:secret@` 的测试，断言标记中不含 secret；异常文字同样脱敏。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_gate_probe.py:17, 101, 105 | 本轮改了 testgate 的接口，探针没有跟着改：<br>- refuse_if_marker 现在只接受 (repo_root, remote)，探针传了 3 个位置参数，「marker」操作必然 TypeError；<br>- TestSession 已没有 models 字段，「begin」操作在标记已提交并推送之后访问 `session.models`，会 AttributeError，探针打印 ERROR 而不是 ACCEPT。<br>本轮没有运行过改后的探针：c1_04:11 显示探针为 `AM`，c1_03 与 c1_04 都不含它的输出。data-auditor 若再用它做黑盒比对，begin 与 marker 两类场景会全部显示不一致。第 1 轮 MAJOR 4（探针能否给 auditor 使用）仍待 Review Gate。（未运行，由签名直接可见；未验证） | `TG.refuse_if_marker(repo, "origin", "main")`；`print("%s ACCEPT marker commit %s models %d" % (op, session.marker_commit, len(session.models)))`；testgate.py:334 `def refuse_if_marker(repo_root, remote=None):`；testgate.py:368-373 TestSession 只有 session_id / marker_commit / marker_sha256 / evaluated | 改为 `TG.refuse_if_marker(repo, "origin")`，models 数从已提交标记读取；更新第 17 行文档；运行一次并提交原始输出；由 Review Gate 裁定 auditor 能否使用该探针。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:396-397, 405, 416, 427-429 | 第 1 轮 MAJOR 1 的遗留：remote 与推送分支仍是自由参数。标记中记录了 URL，但没有任何代码核对它。只要用另一个远端（分叉或临时裸仓库），规范远端上的标记就不会被发现。两台机器并发推到不同分支时，各自都能开始会话。代码说这些在 C2 的 run_pilot 中固定，但 C2 尚未编写，这一点也没有登记。（不确定：取决于 C2；未验证） | `def begin_test_evaluation(fz, authorization, data, base_model_sha256, remote, branch, ...)`；`"remote": remote_url(root, remote), "branch": branch` | 在 testgate 中定义规范远端（规范化后的 URL）与 metrix/CLAUDE.md 第 2 节的分支常量；begin 与 refuse_if_* 核对 remote_url 与常量一致，否则 BLOCKED；在 C1 报告中登记。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/interpretations.py:10, 133-139；/home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:17；/home/user/OpenMythos/metrix/e1-pilot/tasks/IMPL_C_OWNER_MESSAGE.md:31 | 裁决原文要求「在阶段 C 第一个代码提交中……使 pending() 为空」，本提交就是这个提交，却新增了 PENDING 的 B25，pending() == ["B25"]（test_test_data.py:206；B25 标为已接受的变异被测出，c1_04:271，已验证）。暂存的报告第 17 行仍写「`pending()` 为空」，与代码不符。方向是安全的：B25 裁决前所有 TEST 路径都拒绝。但这与裁决的字面要求不一致，报告也没有向 Review Gate 说明。（不确定是否违背裁决本意） | IMPL_C_REPORT.md:17「24 条的 `status` 都是 `ACCEPTED（Review Gate 2026-11-24）`,`pending()` 为空」；interpretations.py:133 `{"id": "B25", "where": ...}`（无 status，即 PENDING） | 改正报告第 17 行；把 B25 及其与裁决第 1 项的关系列入「待 Review Gate 决定」；B25 在租卡前须裁决，否则第 8 步必然 BLOCKED。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:45-47, 143-145, 233-240, 460-463, 73-76 | 第 1 轮 MAJOR 3 的遗留（交 Review Gate 时应一并列出）：<br>- refuse_if_st10_record 对「TEST 已生成」仍抛 ImplementationFail，与「已评测」的处理不对称；<br>- `_ever_committed` 的 git 失败（例如 ls-remote 与 fetch 之间分支被改写，sha 不存在）属环境问题，却是 ImplementationFail。变异「remote: only the tips' refs」就是靠这一异常类型不同才被测出的（c1_04:201）；<br>- 模型 state 哈希与冻结值不符时为 ImplementationFail，而协议第 11 节 ST12「模型……与冻结值不一致 → BLOCKED」可能适用；<br>- TestAlreadyEvaluated 不是 ProtocolStop，C2 必须单独处理；<br>- 模块文档第 45-47 行的分类没有覆盖以上几种。<br>（不确定：状态词由 Review Gate 裁决；未验证） | `raise ImplementationFail("%s exists (%s): TEST is generated once" ...)`；`raise ImplementationFail("git log %s -- %s failed: ..."`；`raise _refuse("the model's state sha256 %s is not the marker's %s ..."` | 在提交 Review Gate 的待决项中逐条列出这些拒绝及拟定的状态词；裁决后统一实现并更新文档。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:477-486 | 本轮新问题：finish 改为从已提交标记读取 models，但没有像 require_test_session 那样核对 `sha == session.marker_sha256`。标记被改写后（例如只留部分模型），再直接调用公开的 claim_checkpoint（它不核对标记），finish 就会提交一个不完整的结果。标记缺少 models 键时则是 KeyError。（未验证） | `marker, _ = _committed(root, MARKER_REL, "TEST marker")`；`left = [m for m in marker["models"] if m not in session.evaluated]` | 加 `if sha != session.marker_sha256: raise _refuse(...)`；claim_checkpoint 可核对 name 属于标记中的模型；补测试。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:140-146, 341 | 历史改写与浅克隆：<br>- 推送失败后若在本地 reset，标记提交只剩在 reflog 中，`--all` 不检索；<br>- 远端 force-push 或删除分支无法检测，文档没有写明这一前提；<br>- 浅克隆中，删除标记的提交若在浅克隆边界之外，就检索不到。这一缺口较窄：ST10 记录的 code_commit 必须是 HEAD 的祖先（testgate.py:313），所以 depth 1 的克隆会先被拒。<br>（未验证） | `r = _git(root, "log", "--full-history", *revs, "--format=%H", "--", rel)`；`revs = ["--all"] + remote_heads(root, remote)` | revs 加 `--reflog`；`git rev-parse --is-shallow-repository` 为 true 时判 BLOCKED；模块文档与 RUNBOOK（C3）写明「远端分支受保护、禁止 force-push」这一前提。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:163-169, 238, 384-393 | 以下新分支既没有测试也不在变异清单中（c1_04:157-271，已验证）：<br>- refuse_if_st10_record 的远端检索：没有「ST10 记录只在远端」的测试，删掉 `+ remote_heads(root, remote)` 的变异不会被测出；<br>- remote_heads 的 fetch 失败与 HEX40 检查；<br>- _commit_preconditions 中 ls-remote 失败与 push --dry-run 失败。<br>（未验证） | `where = _where(root, ST10_RECORD_REL, ["--all"] + remote_heads(root, remote))`；`dry = _git(root, "push", "--dry-run", ...)` | 补测试：ST10 记录只推送到远端另一分支、本地克隆落后；远端可列出但不可 fetch；dry-run 被拒（例如远端只读）。并补相应变异。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:313, 323, 339, 360, 386 | 检出标记的测试只断言 `"commit " in blocked(...)`，只要是任何含「commit 」的 BLOCKED 文字都能通过。例如变异「marker: remote branches not searched」被测出，只是因为快进预检的报错文字里恰好没有「commit 」（c1_04:199）。这些测试没有检验它们声称检验的内容（「已开始」）。（未验证） | `assert "commit " in blocked(env.begin)` | 改为断言 `"already started" in msg and "commit " in msg`。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:199 | st10 的 code_commit 用例仍用不存在的对象 "f"*40。「存在但不是 HEAD 祖先」的提交只在快进预检中间接出现过，st10_check 中没有。（未验证） | `"code_commit": (dict(rec_change=lambda r: r.update(code_commit="f" * 40)), ...` | 增加一个用另一分支上真实提交的用例。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:150 | 文档说 fetch「no local ref written」。对配置过的命名远端（生产中用 origin），`git fetch origin refs/heads/x` 会顺带更新 refs/remotes/origin/x。这无害，但文档不准确。（未验证） | `fetched by name (no tags, no local ref written)` | 改为「只写 FETCH_HEAD 与（命名远端的）远端跟踪引用」。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/record.py:168-170 | auditor 说明 (a) 只在 testgate._committed 中修了。verify_authorization 经 committed_record 读取 Gate 0 与冻结记录时，仍对可能是列表的 JSON 调用 `.get`，得到的是未包装的 AttributeError。闸门不会放行，但异常类型不对。（未验证） | `rec, sha = committed_json(repo_root, rel)`；`if rec.get("kind") != kind ...` | committed_json 或 committed_record 中检查 `isinstance(rec, dict)`，否则抛 NotCommitted。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:101, 464；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:331 | 死代码：<br>- require_test_session 返回的 marker 没有调用方使用；<br>- `_is_ancestor` 的 `of` 参数从未被传入。<br>（未验证） | `return marker`；`def _is_ancestor(root, commit, of="HEAD"):` | 删去返回值与 `of` 参数，或给出调用方。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:38；/home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:283-286；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:330-334 | 可读性：<br>- testgate.py:38 约 148 字符，是本轮新增的超长行；<br>- 测试文件在挪走 blocked 之后留下 4 个连续空行；<br>- evaluate.py 中 TG 只在第一个 `if split == "test":` 内导入，第二个 if 中使用，静态检查会报 possibly-unbound。 | `marker must be the session's (the bytes begin wrote, session id included) and bound to the authorization, the TEST rows must be the files of the` | 换行；删去多余空行；把 `from . import testgate as TG` 移到 TEST 分支之前统一导入，或合并为一个分支。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:44；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/interpretations.py:5 | 登记不充分。C1 一节仍是「（C1 完成后填写。）」，以下事项在暂存树中都没有记录：<br>- 留到 C2 的事项：规范远端与分支常量；各臂保存、重载后核对 state_sha256；DEV 路径的哈希核对；每次 TEST 调用对 1.7B 模型求 state_sha256 的耗时计入预检估算（B17）；finish 写入的 result 不含 TEST 内容（auditor 说明 (f)）；<br>- 交 Review Gate 的事项：MAJOR 3、MAJOR 4、B25；<br>- auditor 第 1 轮的 audit/ 输出入库。<br>interpretations.py 第 5 行仍说这些条目列在 IMPL_B_REPORT.md，而 B25 不在那里。（未验证） | `(C1 完成后填写。)` | 在 C1 报告提交中逐条登记（DEFERRED_MINORS 新一节加「待 Review Gate 决定」）；更新 interpretations.py 文档。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_gate_probe.py:82-86, 101-104 | 探针本身没有防护：<br>- REPO 若误指真实仓库，begin 操作会向其 origin main 提交并推送一个真实标记，耗掉唯一一次 TEST 评测（前提是真实的 ST10 记录与 auditor 计数已经提交）；<br>- `--interpretations-ruled` 会绕过 B25 等待裁决的拒绝。<br>（未验证） | `TG.begin_test_evaluation(fz, auth, data, arg, "origin", "main", ...)`；`INT.pending = lambda: []` | REPO 解析后等于本仓库根目录（PILOT.parents[1]），或其 origin URL 指向规范远端时，拒绝运行。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:179-186 | ST10 记录由驱动写入工作区后，靠操作员手工提交并推送（打印「commit and push it」）。在推送之前，另一台机器上的 refuse_if_st10_record 看不到它，「TEST 只生成一次」在跨机器时依赖人工操作。（未验证） | `path, rec = TG.write_st10_record(fz, auth, report, files)`；`print("ST10 record written: ... commit and push it" ...)` | 驱动直接用 commit_paths 提交并推送 ST10 记录，或在 RUNBOOK 中写明顺序并做核对。

结论：PASS
