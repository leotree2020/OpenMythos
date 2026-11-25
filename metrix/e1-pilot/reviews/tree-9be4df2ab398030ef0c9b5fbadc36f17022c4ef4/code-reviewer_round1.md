# code-reviewer, C1 work commit, round 1 (staged tree 2408558f7e3b4703fa32ef6363871b3cf6833e5a, parent eb05e422); interrupted by HTTP 429 and resumed (interruption.txt, resume_message_code-reviewer.txt)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
code-reviewer：C1 工作提交审查（暂存树 2408558f7e3b4703fa32ef6363871b3cf6833e5a，父提交 eb05e42243b54b78cb400b40293ef56f67611852），因 HTTP 429 中断后续审，以下为完整原文

运行环境与依据：只用了 Read、Grep、Glob，没有运行任何代码，也没有读取 TEST。依据是暂存 diff（/tmp/claude-0/-home-user/8645aeea-5a45-5281-b238-3e6075410a17/scratchpad/review_c1/input.diff）、工作区源码（interruption.txt 记录工作区等于暂存区）、/home/user/OpenMythos/metrix/e1-pilot/METRIX_E1_PROTOCOL.md 第 3、8、9、11 节、IMPLEMENTATION_TASK_ORDER_V1.md、IMPL_C_OWNER_MESSAGE.md、DEFERRED_MINORS.md 1.26 节。续审前已重读 /home/user/OpenMythos/.claude/agents/code-reviewer.md，tools 行为「Read, Grep, Glob」，与已加载定义一致。

一、上一轮 BLOCKER 1–3 与 MAJOR 4–8 在本次实现中的状态
（上一轮原文：/home/user/OpenMythos/metrix/e1-pilot/reviews/tree-65225a5afeaa119b9d89394b2d30cb2270342e26/code-reviewer_stage-c-commit1.jsonl 第 77 行）

- 上次 BLOCKER 1（ST10 记录没有写入者，闸门只看 within_limit 标志）：已解决。
  - test_data.main 调用 testgate.write_st10_record 写入原始计数。
  - st10_check 用 stops.st10 按 test_limits(fz)（取自冻结的 SPLIT_MANIFEST）重新判定，不读取任何标志或结论词。
  - 依据（已验证）：c1_02_checks.txt:326-327（stops.st10 去掉超限判定的变异被测出）、:328-329（计数改从标志读取的变异被测出）、:380-381（驱动改用报告标志判定的变异被测出）、:336-339（ST10 记录存在性与历史检查的变异被测出）。
  - 残留：L3a/L3b/L4/L5 的计数仍以已提交记录为准，只有 L6 有 data-auditor 交叉核对。这与补充裁决 3 的要求一致，不列为问题。
- 上次 BLOCKER 2（「TEST 只评一次」不由代码强制）：已解决。标记的提交、推送与 ls-remote 核对、本进程会话、每个 checkpoint 一次、finish 的结果提交都已实现。已验证：c1_02_checks.txt:340-375。
- 上次 BLOCKER 3（TEST 文件没有绑定）：已解决。ST10 记录与标记都含 test_files_sha256，require_test_session 对将要评测的行重新求哈希。已验证：c1_02_checks.txt:310-311、:364-365。
- 上次 MAJOR 4（evaluate_model 中新加的检查没有测试）：已解决。已验证：c1_02_checks.txt:376-377；测试 test_evaluate_model_passes_every_gate_then_stops_at_the_gpu_check 与 test_evaluate_model_refusals 的报错文字都来自 require_test_session。
- 上次 MAJOR 5（「已评测」分支未测到）：已解决。test_marker_with_a_result_is_refused_as_evaluated 断言 ImplementationFail「TEST was already evaluated」，与 BLOCKED 分支的异常类型和文字都不同。已验证：c1_02_checks.txt:346-347。
- 上次 MAJOR 6（BE2 报错无法区分）：已解决。四种情形各用锚定到整句的正则，包括「授权等于 fz、PROTOCOL_FROZEN 指向另一提交」。已验证：c1_02_checks.txt:382-385。
- 上次 MAJOR 7（ACCEPTED 找不到裁决记录）：已解决。tasks/IMPL_C_OWNER_MESSAGE.md 第二段含裁决第 1 项原文；RULING_REF 指向 IMPL_C_REPORT.md 对应一节，符合补充裁决 2。
- 上次 MAJOR 8（参数化测试只断言 is not None）：已解决。REFUSED 每个用例有自己的报错正则，refused() 同时断言前缀「IMPLEMENTATION_FAIL: TEST path refused: 」。
- 另外已核对：
  - 全部 pytest 通过，256 passed（c1_02_checks.txt:301）。
  - 变异 46 个，测出 46 个（c1_02_checks.txt:396）；但其中第 6 个变异本身有缺陷，见下文 MINOR。
  - TEST 生成器在当前状态拒绝运行，没有产生文件（c1_02_checks.txt:267-283）。
  - outside_metrix_check 通过（c1_02_checks.txt:284-295）。
  - diff stat 不含协议、三个 JSON 与 PROTOCOL_FROZEN，也没有 metrix/ 以外的文件。

二、问题列表

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:240-262, 291-305, 308-316 | 跨机器「只评一次」依赖调用方传入的 remote 与 branch，两者都是自由参数。refuse_if_marker 只 fetch 这一个远端分支（`refs/heads/%s`）。在落后的克隆上若传入另一个分支名或另一个远端（例如临时裸仓库），已经推送到规范远端其他分支上的标记不会被发现，推送也可能去到不是规范仓库的地方。（未验证；推断依据代码阅读，C2 的调用尚未编写） | `f = _git(root, "fetch", "-q", "--no-tags", remote, "refs/heads/%s" % branch)`；`revs.append("FETCH_HEAD")`；`begin_test_evaluation(fz, authorization, data, base_model_sha256, remote, branch, ...)` | 远端名与分支名从常量或冻结配置取（metrix/CLAUDE.md 第 2 节的分支），把远端 URL 写入标记；查找标记时 fetch 远端全部 heads（`+refs/heads/*`）或用 ls-remote 列出全部分支后逐一检查；补一个「标记在远端另一分支、本地克隆落后」的测试。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:330, 382；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/record.py:183-188 | 闸门实际上把协议第 8 节第 8 步的「checkpoint 哈希」定义为内存中模型的 train.state_sha256（含 dtype、shape、state_dict 键集合）。这是一个新的实现选择，但冻结记录的生产侧（selection_freeze_record 的 docstring、freeze_record_problem）没有写明，也没有登记到 interpretations.py。C2 若写入文件字节哈希，或 L 臂重载后 state_dict 键不同，16 次 TEST 调用会在 GPU 预算用完之后全部被拒，Pilot 变成 BLOCKED。（不确定：取决于 C2 的实现；未验证） | `if model_sha256 != session.checkpoints[checkpoint_name]:`；evaluate.py:330 `state_sha256(model)`；record.py `"checkpoints": dict(checkpoints)` 没有说明哈希定义 | 在 record.selection_freeze_record 与 testgate 的 docstring 写明 checkpoints[name] = train.state_sha256(评测时加载的模型)，并作为解释项送 Review Gate；C2 冒烟测试中保存并重载各臂 checkpoint，核对 state_sha256 与写入冻结记录的值相同。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:72-73, 251, 258, 333, 397-398 | 拒绝路径的状态语义。_refuse 返回 ImplementationFail（errors.py:42-47，状态 IMPLEMENTATION_FAIL）。这同样用于环境条件（远端无法 fetch、索引里有已暂存改动）和「TEST 已评测」。协议第 9 节把 IMPLEMENTATION_FAIL 限定为「实现与本协议不一致」等，把环境与资源问题归 BLOCKED。若 C2 把异常状态写入实验记录，重跑一个已完成的 Pilot 会被标成 IMPLEMENTATION_FAIL。（不确定：C2 如何把异常映射到 Pilot 状态尚未编写；未验证） | `def _refuse(message): return ImplementationFail("TEST path refused: %s" % message)`；`raise _refuse("cannot fetch %s %s to look for a TEST marker there: ..."`；`raise _refuse("TEST was already evaluated ...")` | 环境类拒绝用 BLOCKED；「已评测」用一个不改变 Pilot 状态的拒绝（例如单独的异常类，不携带第 9 节状态）；或提请 Review Gate 裁决这些拒绝的状态词。

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_gate_probe.py:1-20 | 这是 Executor 写给 data-auditor 使用的黑盒探针（docstring 写明「for the data-auditor」）。metrix/CLAUDE.md 第 1 节规定 data-auditor 不复用 Executor 的检查代码。探针内含 Executor 自己的判断逻辑：由已提交记录构造授权、以 GPU_REFUSAL 子串判定 ACCEPT。此外：
- 仓库中没有它的运行输出；
- c1_02_checks.txt:185-207 的 git status 中也没有它，说明它是在检查之后才加入的；
- interruption.txt:43、48 显示临时目录中有 c1_gate_probe.py 与 probe_try/，即曾试运行。
（不确定：只调用被测代码的驱动脚本是否算「检查代码」） | `"""Stage C, C1: black-box probe of the TEST gates ... for the data-auditor.`；`if GPU_REFUSAL in str(e): print("%s ACCEPT ACCEPTED-BY-GATES ..."` | 由 Review Gate 裁定 data-auditor 可否使用该探针；若保留，提交其运行原始输出，或改由 data-auditor 自写驱动。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:329-331；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:385, 394-396 | require_test_session 在 require_gpu 之前就把 checkpoint 记为已评。正式运行中若传错 device（或评测中途出错），该模型唯一的一次准入已被消耗，却没有评测。finish 检查的「every model was evaluated」实际含义是「每个模型都通过了闸门」，并不说明评测完成。（未验证） | `session.evaluated.add(checkpoint_name)` 位于 testgate.py:385；evaluate.py:331 `require_gpu(mode, device)` 在其后 | 把 require_gpu 移到 TEST 闸门之前（CPU 测试可 monkeypatch require_gpu）；finish 核对 result 中每个模型都有条目，或把字段改名为 admitted。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:291-305, 340-355 | begin 先写入并提交标记，之后才发现提交或推送的前提不满足：
- 远端已前进（非快进）；
- 未配置 git 身份，或开了 commit.gpgsign；
- 没有推送权限。
任何一种都会留下本地标记，此后永久 BLOCKED，提示「counts as evaluated」，但实际上 TEST 尚未评测，恢复需要改写本地历史，而这必须等 Owner 指令。test_a_rejected_non_fast_forward_push_is_blocked（tests/test_testgate.py:381）演示了这一情形。 | `c = _git(root, "commit", ...)`；`head = _push(...)` 之前没有 `merge-base --is-ancestor FETCH_HEAD HEAD`，也没有 `push --dry-run` | 写标记前先预检：本地 HEAD 是 FETCH_HEAD 的后代、`git var GIT_COMMITTER_IDENT` 可用、`git push --dry-run` 成功；RUNBOOK（C3）写明这些前提。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:297；/home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:245 | push 没有加 `--no-follow-tags`。若 A100 机器的 git 配置为 push.followTags=true，可达的注释标签会被一起推送，与 Owner「不推送标签」的要求不符。测试中的临时仓库没有任何标签，所以 `ls-remote --tags == ""` 这条断言不可能失败。（未验证） | `r = _git(root, "push", remote, "HEAD:refs/heads/%s" % branch)`；`assert git(env.root, "ls-remote", "--tags", "origin") == ""` | 加 `--no-follow-tags`；测试里先建一个注释标签并设 push.followTags=true，再断言远端没有标签。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:378-384 | 模型名与哈希的检查用的是内存中可变的 session.models 与 session.checkpoints，没有用刚从已提交标记读出的 marker["models"] 与 marker["checkpoints"]。进程内若改动了 session 对象，就绕过了「哈希等于已提交标记」这一条。 | `if checkpoint_name not in session.models:`；`if model_sha256 != session.checkpoints[checkpoint_name]:`（同一函数第 367 行已有 `marker, sha = _committed(...)`） | 改用 marker 中的 models 与 checkpoints。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:320-327 | 冻结记录的重读与 sha 比较和 verify_authorization（leakage.py:237-244）完全重复；except 分支与 sha 不等分支除竞态外不可达。 | `try:  # verified above by verify_authorization; read here ...`；`if freeze_sha != authorization.selection_record_sha256:` | 改为只读取记录（或让 verify_authorization 返回 recs），删去不可达的分支。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/test_data.py:166-175；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:155-162 | 「TEST 只生成一次」有两个缺口：
- code_commit 的未提交改动检查要到 write_st10_record（生成与泄漏检查之后）才执行。代码有未提交改动时，TEST 已生成，随后才被拒，也没有 ST10 记录；换一个 --out 重跑就会再次生成。
- refuse_if_st10_record 不 fetch 远端，这与 refuse_if_marker 不一致。
| `files, info = generate_test(...)` 在 `path, rec = TG.write_st10_record(...)` 之前；`_ever_committed(root, ST10_RECORD_REL, ["--all"])` | 在 generate_test 之前调用 TG.code_commit(root)；refuse_if_st10_record 与 refuse_if_marker 使用同样的远端检查。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:271 | 魔法数字 5（受训 arm 数）。 | `want = len(contract.training.training_seeds) * 5` | 由 ("F", "L", "A") + contract.arms.inheriting 推出。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:262 | docstring 引用了不存在的函数 testgate.st10_problem，实际名称是 st10_check。（已验证：grep 只在此处命中） | `the gate re-judges them against the frozen limits (testgate.st10_problem)."""` | 改为 testgate.st10_check。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:303-305；/home/user/OpenMythos/metrix/e1-pilot/tests/test_test_data.py:268 | BE9 登记的做法是「content_hashes 按 CONTENT_HASH_KEYS 组装」；本次实现保留字面键，再断言它与同一文件中的另一个字面量相等。不用 monkeypatch 时，这个分支不可达。测试文件中仍有第三份字面键。 | `if tuple(got) != CONTENT_HASH_KEYS:  # one list of keys (DEFERRED_MINORS BE9)`；`for k in ("facts", "train_S", "candidates", "anchor_texts")` | 按 DEFERRED_MINORS 1.26 的登记由键列表组装；测试改用 FZ.CONTENT_HASH_KEYS。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_mutate.py:26；/home/user/OpenMythos/metrix/e1-pilot/tests/test_testgate.py:183 | 变异「st10: ancestor test always true」把 `.returncode == 0)` 换成 ` >= 0)`，得到 `CompletedProcess >= 0`，结果是 TypeError，而不是「恒为真」。它被测出是因为程序崩溃，不是因为有测试检出了「恒为真」。另外，没有测试使用一个存在但不是 HEAD 祖先的提交；code_commit 用例用的是不存在的对象 "f"*40。（已验证：c1_02_checks.txt:314-315 的失败原因是 `test_st10_check_control - Type...`） | `("st10: ancestor test always true", ..., '.returncode == 0)\n\n\ndef auth_fields', ' >= 0)\n\n\ndef auth_fields', TG)` | 变异改为 `.returncode >= 0)`；补一个用另一分支上真实提交的用例。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_mutate.py:14 | 变量 TD 未使用，与 TT 指向同一个测试文件。 | `TG, TT, TD, TE, TS, TH = ("tests/test_testgate.py", "tests/test_test_data.py", "tests/test_test_data.py", ...` | 删去 TD。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:104-106, 338, 346-353, 368, 397-398, 403-408 | 以下闸门分支既没有测试，也不在变异清单中：
- rows_hashes_of 缺少 TEST 文件；
- begin 时代码有未提交改动；
- 标记暂存或提交失败；
- 已提交标记的 session_id 相同但字节不同（第 368 行后半个条件）；
- finish 时索引有已暂存改动；
- finish 暂存或提交失败。
| 例：`if marker.get("session_id") != session.session_id or sha != session.marker_sha256:` 只有前半个条件被测到（test_evaluate_model_refuses_another_committed_marker 改的是 session_id） | 逐条补测试或变异。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:178-182, 308, 388 | 本提交中 auditor_count_record 只被测试使用；begin_test_evaluation 与 finish_test_evaluation 还没有生产调用方（调用方在 C2 的 run_pilot）。 | grep：除 testgate 定义处外，只有 tests/ 与 reports/impl_c/c1_gate_probe.py 引用 | C2 接入后复核；在此之前在报告中注明。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:330 | 每次 TEST 调用都先对整个模型求 state_sha256：对 1.7B FP32 模型，要把约 6.9 GB 拷回 CPU 再求哈希，16 次调用。这部分时间不在 B17 的预检估算内；即使调用随后会被拒，哈希也照样计算。（未验证：没有计时） | `TG.require_test_session(fz, test_authorization, test_session, checkpoint_name, data, state_sha256(model))` | 预检时估算这部分时间并计入，或先做便宜的检查、最后再求哈希。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:400-401 | finish 用 `default=str` 序列化结果，会把非 JSON 值（Tensor、Fraction 等）静默转成字符串写入 TEST 结果。 | `json.dumps(dict(result, ...), ensure_ascii=False, indent=1, sort_keys=True, default=str)` | 去掉 default=str，让类型错误显式报出。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/evaluate.py:306-344（DEV 路径；已有代码） | DEV 与 TEST 混用：evaluate_model(split="dev") 以及 score_qa、general_nll、em 等底层函数不核对传入的行是否就是 DEV 文件。把 TEST 行放在 dev 键下传入，或直接调用底层函数，都绕过 TEST 闸门。模块 docstring 承认这一限制（「the checks hold for the package's own paths」）。（未验证；属于 C2 入口的问题） | `qa_file, gen_file = SPLIT_FILES[split]`；`facts, cands, qs = data["facts.jsonl"], data["candidates.json"], data[qa_file]` | C2 的 run_pilot 在 DEV 评测前核对 dev_qa.jsonl 与 general_dev.jsonl 的哈希与 ST12 一致；C2 的 data-auditor 复审 TEST 路径时一并检查。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c1_02_checks.txt:185-233, 400-422 | 证据链：c1_02 记录于暂存之前，当时 c1_gate_probe.py 还不存在。没有已提交的输出能把暂存树 2408558f 中的 src/tests 与当时被测试的字节对应起来；interruption.txt 只核对了 diff 文件相同，没有核对 src/tests 的哈希。（未验证：本审查无法计算 sha256） | c1_02 第 225-233 行只记录了未跟踪文件哈希和 `git diff HEAD -- src tests | sha256sum`（048e0ddd…） | 提交前补记 `git diff --cached HEAD -- metrix/e1-pilot/src metrix/e1-pilot/tests | sha256sum` 与新文件的 sha256，与 c1_02 中的值比对。

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/testgate.py:32, 82；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/interpretations.py（B1–B24 各行，例如 B17 条目） | 多行超过 120 字符，与仓库其余代码的行宽不一致。 | testgate.py:32 `tags, no force) and checks the remote ref. Only then it returns the TestSession. A failed push leaves the marker committed: BLOCKED, report to the Owner.` | 换行。

结论：PASS
