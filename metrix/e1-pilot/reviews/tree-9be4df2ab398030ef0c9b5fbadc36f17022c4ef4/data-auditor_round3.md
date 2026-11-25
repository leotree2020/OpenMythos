# data-auditor, C1 work commit, round 3 (staged tree 9be4df2ab398030ef0c9b5fbadc36f17022c4ef4, parent eb05e422)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
数据审计报告：METRIX E1-PILOT 阶段 C 第 1 段（C1）工作提交，第 3 轮

审计对象：暂存树 9be4df2ab398030ef0c9b5fbadc36f17022c4ef4，父提交 eb05e42243b54b78cb400b40293ef56f67611852，仓库 /home/user/OpenMythos。
运行环境：主机 vm，Anthropic 云容器，只用 CPU（/dev 下没有 nvidia 设备节点，torch.cuda.is_available() 为 False）。
- 任务 2 只加载了 Qwen tokenizer。
- 探针里的 tiny 模型是随机初始化的 2 层 Qwen3，没有加载任何模型权重。
- 我没有生成、读取或统计真实 TEST；所有 TEST 行都是我自己写的人造行。
定义核对：已先读仓库中的 .claude/agents/data-auditor.md。其正文和 tools 行（Read, Grep, Glob, Write, Bash）与我加载的定义一致。

## 结论先行
- **结论是 BLOCK，原因只有一项。** 检出分支不是 main 时，你说 `marker` 操作应为 STOP - BLOCKED，实际是 ACCEPT（N1、N2 两项，见差异汇总）。
  - 本项依据的是你本轮给出的语义。在运行探针之前，我已按这一语义把预期登记为 BLOCKED。
  - 已提交的 testgate 文档也写了同样的行为。
  - 代码只在传入分支参数时才检查检出分支，而标记检索 remote_heads 不传这个参数。
  - 这不让任何闸门被绕过：begin 写标记之前、TEST 驱动生成 TEST 之前，都会检查检出分支（N1、N2 中 begin 均为 BLOCKED，且没有写入任何东西）。
  - 但说明与代码不一致，而且是预先登记的预期没有兑现。按定义（任一项不一致即为 BLOCK）判 BLOCK。是否可以接受，由 Review Gate 裁决。
- **其余全部一致：**
  - 已提交的探针（不带替代参数）可以正常使用，没有出现任何 ERROR 或无法解析的输出。
  - 共比对 253 项：same 251，DIFFERENT 2，INFO 11，后置核对失败 0。
  - 第 2 轮的 BLOCK 项（探针与接口不符）已修复。
  - 本轮补测全部通过：B13、浅克隆、URL 中带凭据、Gate 0 或冻结记录不是 JSON 对象、探针自身的防护。
  - 四个冻结内容哈希一致；静态核对 a–l 全部 PASS；TEST 生成器拒绝运行，且没有任何产物。

## 脚本（新写，放在 /home/user/OpenMythos/metrix/e1-pilot/audit/）
- 全部由我的 ic3_ 脚本改写。没有 import、调用或复制 Executor 的代码；探针只以子进程 `python -I -B` 方式运行。

| 脚本 | 用途 | sha256 前缀 |
|---|---|---|
| ic4_01_gate_scenarios.py | 任务 1 | 7d39c519… |
| ic4_02_content_hashes.py | 任务 2 | f64d8c95… |
| ic4_03_static.py | 任务 3 | a6a31004… |
| ic4_04_test_refusal.py | 任务 4 | c642df09… |
| ic4_run_logged.sh | 运行包装：stdout 与 stderr 合并后完整写入文件 | fa7c6286… |

## 完整 stdout（/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/）

| 文件 | 内容 | sha256 前缀 |
|---|---|---|
| ic4_00_state.txt | 状态 | 3cc266b9… |
| ic4_01_gate_scenarios.txt | 任务 1，正式运行 | b342806b… |
| ic4_01_gate_scenarios_run1_script_error.txt | 第一次运行，因我脚本的格式化错误中断 | 28bc981b… |
| ic4_01a_script_fix_after_run1.txt | 修复前后的脚本 diff | c6aa38c5… |
| ic4_02_content_hashes.txt | 任务 2 | 4962fc47… |
| ic4_03_static.txt | 任务 3 | f1205100… |
| ic4_04_test_refusal.txt | 任务 4 | 7f59dd4b… |
| ic4_99_git_status_final.txt | 最终 git status | f942b60f… |

调试运行的说明：
- ic4_01 的第一次运行因我脚本中的 `%` 格式化错误中断，原样保留。中断前 106 项 same，0 项 DIFFERENT。
- 修复只有两行，都是机械性改动，没有改任何预期，见 ic4_01a 中的 diff。
- ic4_03 有两次试跑（输出在会话临时目录，不作为证据），暴露了我自己检查逻辑中的 4 处错误。原因是 require_gpu 现在出现在两个分支里，以及几处字符串和形式匹配问题。修正后正式运行。

---

## 0. 状态（ic4_00_state.txt）
命令：`bash audit/ic4_run_logged.sh audit/stdout/impl_c/ic4_00_state.txt bash -c "<rev-parse; write-tree; cmp input_round3.diff; cmp delta_round3.diff; diff --quiet; status; sha256sum; diff 我第 2 轮核对过的修正副本 -> 暂存探针; git diff HEAD -- src tests | sha256sum; 版本>"`

原始输出（节选）：
```
eb05e42243b54b78cb400b40293ef56f67611852
9be4df2ab398030ef0c9b5fbadc36f17022c4ef4
9be4df2ab398030ef0c9b5fbadc36f17022c4ef4
INPUT_DIFF_IDENTICAL
DELTA_DIFF_IDENTICAL
WORKTREE_EQUALS_INDEX
11a77fc775dcc60f...  metrix/e1-pilot/reports/impl_c/c1_gate_probe.py
--- diff: my round-2 checked corrected copy -> staged probe:
12,14c12,17 (文档)   38c41  PILOT = Path("/home/user/...") -> Path(__file__).resolve().parents[2]
87a91,95  origin = TG.repo_id(TG.remote_url(repo, "origin")); if repo == PILOT.parents[1] or origin == TG.CANONICAL_REPO: sys.exit("probe refused: ..."); TG.CANONICAL_REPO, TG.PILOT_BRANCH = origin, "main"; print(...)
--- git diff HEAD -- metrix/e1-pilot/src metrix/e1-pilot/tests | sha256sum (c1_06_checks_r3.txt records 4781575f...):
4781575f4499c85edad8d5276dc9027758e6f445055f53eaadf3b4b9162a97d3  -
3.13.18 2.11.0+cu130 5.22.2 False
```
- 暂存的探针 = 我第 2 轮核对过的修正副本 + 文档 + `PILOT = parents[2]` + 防护与覆盖，与你的说明一致。
- 现在 src/ 和 tests/ 相对 HEAD 的 diff 哈希，等于 c1_06 记录的值，所以 Executor 的 pytest、变异和探针运行，用的就是暂存的代码。
- c1_05b 的恢复：从第 2 轮树 dc4f28df 到本轮树，src/ 与 tests/ 中改动的恰是 c1_05b 标为 "worktree reference" 的 7 个文件；暂存的 evaluate.py 第 333 行有 `TG.claim_checkpoint(test_session, checkpoint_name)`（ic4_99）。与 c1_05b 一致。

---

## 1. 闸门场景：独立模型与已提交探针的黑盒比对（ic4_01_gate_scenarios.txt）
命令：`cd <scratchpad> && bash audit/ic4_run_logged.sh audit/stdout/impl_c/ic4_01_gate_scenarios.txt python3 -I -B audit/ic4_01_gate_scenarios.py /home/user/OpenMythos <scratchpad>/venv/bin/python <scratchpad>/ic4_repos`
- 脚本不再接受替代探针参数。
- 首行核对原文：`the probe run is the staged one: True`（sha256 11a77fc7…）。

做法：
- 第 2 轮的全部场景都重跑：A 组 ST10 共 54 个；C、K、B、D、E 组；F 组为 B25 对照，不带 --interpretations-ruled。
- 预期按第 3 轮语义更新：
  - 本地检索加入 reflog；
  - 浅克隆、检出分支不是 main、远端不可达，均为 BLOCKED；
  - Gate 0 或冻结记录不是对象时为 REFUSE；
  - 本地 pre-push 钩子：拒绝 dry-run 时为 BLOCKED 且不写入；只拒绝真实推送时为 BLOCKED 且本地留标记。
- 只来自你本轮说明的预期，标注为 “(stated r3)”。
- 所有预期都在运行探针之前由我的模型算出。新增各组在运行前另外打印 “pre-registered” 行。

原始输出（汇总）：
```
probe's first line is the --interpretations-ruled line exactly when the flag is given (every run): True
probe's CANONICAL_REPO line == my reading of origin's URL: checked in 119 runs, mismatches []
probe runs 124; runs whose stdout+stderr contain the URL secret: 0
summary: compared operations same 251 | DIFFERENT 2 | INFO (no expectation) 11 | ERROR or unparsable probe output among them: 0 | post-checks FAILED 0
RESULT: FAIL
exit=1
```

**第 2 轮场景重跑：全部 same。**
- A 组全部一致，包括 A06/A06b、A58b 的 "is a JSON list, not an object"。
- C1：begin 为 ACCEPT，`marker commit … models 16`。后置核对全部 ok：
  - 标记提交只改动标记路径，快进，没有标签；
  - 标记有 14 个键；checkpoints 为 30+N，models 为我的 16 个；
  - remote 字段与 branch 字段都正确；标记中没有人造 TEST 内容。
- C1 中 eval 和 gate 的序列与第 2 轮相同。C2、K1、K2、K3 均为 BLOCKED，且没有写入。
- B01–B16 全部一致。D1–D12、E0–E4、F1/F2 全部一致。
- F1 的拒绝文字含 "interpretations not yet ruled by Review Gate: B25"。

**本轮新增场景：**

| 场景 | 预期（运行前登记） | 观察 |
|---|---|---|
| B13 标记提交只在 reflog（reset --hard，未推送） | STOP - BLOCKED | same（"marker … in commit 6f684d70…"） |
| B13b 侧分支上提交标记后 `branch -D`，只有 HEAD 的 reflog 能到达 | STOP - BLOCKED | same |
| B13r 标记与结果只在 reflog | EVALUATED | same |
| B17 远端只有 tag 指向标记，没有分支 | INFO（说明：不在检索范围内） | ACCEPT |
| N1 检出分支 'work' | marker BLOCKED (stated r3)；begin BLOCKED | **marker ACCEPT（DIFFERENT）**；begin same，文字 "the checked-out branch 'work' is not the pilot's 'main'"，没有写入 |
| N2 分离 HEAD | marker BLOCKED (stated r3)；begin BLOCKED | **marker ACCEPT（DIFFERENT）**；begin same（"'HEAD' is not the pilot's 'main'"），没有写入 |
| N1c 同一仓库切回 main（对照） | marker、begin 均 ACCEPT | same，标记提交的后置核对全部 ok |
| S1 --depth 1 浅克隆 | st10 REFUSE（code commit 不可达）；marker、begin BLOCKED | same（"the clone is shallow: its history is incomplete"），没有写入 |
| S1u 同一克隆 fetch --unshallow 之后 | st10、marker、begin 均 ACCEPT | same，标记 remote == "file:///…/S0_source/remote.git" |
| U1 origin 为 file://auditor:SECRET@/… | marker、begin、eval 均 ACCEPT | same |
| U2 本地 pre-push 钩子打印 $2（URL）并拒绝每次推送 | begin BLOCKED（dry-run 失败），不写入；eval REFUSE | same |
| U3 钩子放过 dry-run、拒绝真实推送并打印 URL | begin BLOCKED，本地留标记；eval REFUSE | same |
| U4 带 secret 的 URL 指向不存在的路径 | marker、begin 均 BLOCKED | same |
| G1 Gate 0 记录是 JSON 数组 | begin、eval 均 REFUSE | same（"gate0_record.json is a JSON list, not an object"） |
| G2 冻结记录是 JSON 数组 | begin、eval 均 REFUSE | same（"selection_freeze_record.json is a JSON list, not an object"） |
| G3 Gate 0 记录是 JSON 字符串 | REFUSE | same（"is a JSON str, not an object"） |
| G4 冻结记录是 JSON null | REFUSE | same（"is a JSON NoneType, not an object"） |
| P1 克隆的 origin 为 …/leotree2020/OpenMythos.git，带 marker 与 begin 操作 | 探针拒绝 | same（"probe refused: … (origin leotree2020/OpenMythos) is the pilot's repository"），没有写入，也没有 FETCH_HEAD |
| P2 origin 为 https://auditor:SECRET@github.com/leotree2020/OpenMythos.git，无操作 | 拒绝 | same，输出中没有 secret |
| P3 origin 为 git@github.com:leotree2020/OpenMythos.git，无操作 | 拒绝 | same |
| P4 REPO 为本仓库，无操作 | 拒绝 | same，本仓库 HEAD、index 树、FETCH_HEAD 时间与 status 都未变 |

各组补充说明：
- **U1：**
  - 后置核对：标记 remote == 'file:///…/U1_secret_url/remote.git'；
  - 已提交的标记、探针输出、远端 `git log --all -p` 中都没有 secret（FETCH_HEAD 中也没有，记为 info）。
- **U2：**
  - 后置核对：钩子日志中有 secret，说明 git 的 stderr 里确实带着 secret；
  - 拒绝文字原文："a dry-run push to origin main fails: auditor pre-push hook refuses this push: url=file:///…/U2_secret_hook/remote.git"，已去掉凭据；
  - 输出中没有 secret。
- **U3：**
  - 拒绝文字原文："the TEST marker … is committed (bc7076a6…) but was not pushed to origin main (auditor pre-push hook refuses this push: url=file:///…"，已去掉凭据；
  - 后置核对：本地标记提交只改动标记路径，远端未变；本地标记的 remote 字段已去掉凭据。
- **G1–G4：** st10 为 INFO，观察为 ACCEPT，因为 ST10 闸门本身不读这两份记录的内容；没有出现任何 AttributeError 或 ERROR；没有写入。
- **P2、P3：** 不带任何操作运行，因此即使防护失效也不会访问网络。
- **H6、H7、H8（git 层面）：** ST10 记录、结果文件、标记三者分别提交后 reset --hard。我的检索（rev-list --all --reflog）和代码的检索形式（git log --full-history --all --reflog）都能找到；第 2 轮不带 --reflog 的形式找不到。

**与 Executor 是否一致：**
- **与 c1_06 中 Executor 运行探针的输出一致：**
  - tiny 模型的哈希：seed 0 为 a895622c…，seed 7 为 0aaed642…；
  - B25 待决时，begin 和 eval 的拒绝文字相同；
  - begin 为 ACCEPT，models 16；eval:N:0 为 ACCEPTED-BY-GATES；
  - eval:N:7 的拒绝文字相同（0aaed642… is not the marker's a895622c…）；
  - gate:N 第一次 ACCEPT、第二次 REFUSE，之后 eval:N:0 为 REFUSE，begin 之后 marker 为 BLOCKED；
  - 探针拒绝本仓库。
- **与你本轮说明的语义：** 只有 N1 和 N2 的 marker 不一致，见差异汇总。其余各项一致：reflog、浅克隆、begin 在非 main 检出上 BLOCKED、凭据被去掉、非对象记录为 REFUSE、探针的防护与覆盖。

---

## 2. 四个冻结内容哈希（ic4_02_content_hashes.txt）
命令：`bash audit/ic4_run_logged.sh audit/stdout/impl_c/ic4_02_content_hashes.txt <venv>/python -I -B audit/ic4_02_content_hashes.py /home/user/OpenMythos <scratchpad>/inputs/qwen_tokenizer <scratchpad>/c1_data`

原始输出（节选）：
```
  facts        mine 406c8801c5b6... | PROTOCOL_FROZEN 406c8801... | Executor generate 406c8801... | Executor verify 406c8801... | ALL EQUAL True
  train_S      mine 686fdd2f62ed... | ... | ALL EQUAL True
  candidates   mine e5d15c9952d8... | ... | ALL EQUAL True
  anchor_texts mine 8828bc4fcc5a... | ... | ALL EQUAL True
anchor texts from my decode of the stored ids (pinned Qwen tokenizer): 8828bc4f... | every decoded text == stored text: True
（8 个数据文件）now == my round 3 == Executor listing (r3): equal True ×8; test_qa.jsonl / general_test.jsonl present: []
D. content_hashes 的四个序列化表达式、键序、辅助函数与 HEAD 相同: identical True ×4, helpers True ×5
RESULT: PASS
exit=0
```
与 Executor 一致：本轮重新生成的数据，与 c1_06_checks_r3.txt 中的生成值和 verify 值完全相同。

---

## 3. 静态核对（ic4_03_static.txt）
命令：`bash audit/ic4_run_logged.sh audit/stdout/impl_c/ic4_03_static.txt python3 -I -B audit/ic4_03_static.py /home/user/OpenMythos`
- 文件按文本读入后用 ast 解析，不 import。
- 结果：`static checks a-i: PASS`，j–l 全部通过，`RESULT: PASS`，exit=0。

要点（原文节选）：
- **b. 非对象 JSON：**
  - `record.committed_json non-object check: ["if not isinstance(obj, dict):\n    raise NotCommitted('%s is a JSON %s, not an object' % (rel, type(obj).__name__))"]`；
  - testgate._committed 只是转调用 R.committed_json，原有的重复检查已删去；
  - verify_authorization 捕获 R.NotCommitted。
- **c. test_data.main 的步骤顺序：**
  - 原文：`[('check_preconditions', 5), ('out.resolve() == root', 8), ('present = ', 9), ('TG.code_commit(root)', 11), ('TG.check_remote(', 12), ('refuse_if_st10_record', 13), ('generate_test(', 14), ('out.mkdir', 15), ('run_test_part', 17), ('leakage_test_report', 18), ('write_st10_record', 19), ('TG.commit_paths(', 23)]`；
  - check_remote 的调用为 `TG.check_remote(root, TG.PILOT_REMOTE, TG.PILOT_BRANCH)`；
  - commit_paths 只提交 `[TG.ST10_RECORD_REL]`；--remote 参数已删去；
  - 各项检查都在 generate_test 之前。
- **d. ST10 记录与标记的内容：**
  - ST10 记录的 8 个键只有计数、哈希、提交号与授权，counts 只读 `['checks'][c]['value']`；
  - 标记的 14 个键，其中 `marker['remote'] = remote_url(root, remote)`，remote_url 返回 `scrub(...)`；
  - 两者都不含 TEST 内容。
- **e. evaluate_model 的顺序：**
  - 原文：`[(329, 'verify_authorization'), (331, 'require_test_session'), (332, 'require_gpu'), (333, 'claim_checkpoint'), (335, 'require_gpu'), (337, "data['candidates.json']") ...]`；
  - else 分支只有 `require_gpu(mode, device)`。
- **f. 测试与报告脚本：**
  - c1_probe_run.py 的行全是字面量人造行（'SYNTHETIC', 'Synthetic?', 's-0', 'synthetic', 'synthetic-0'），在 tempfile 临时目录中；
  - test_testgate 中每次调用 TD.main 之前都已打桩，--inputs 为 'unused'。
- **g. 历史检索：**
  - 两处检索的 revs 都是 `['--all', '--reflog'] + remote_heads(root, remote)`；
  - remote_heads 的第一条语句是 `check_remote(root, remote)`。
- **h. begin 与 finish：**
  - _commit_preconditions 与 commit_paths 都以 `check_remote(root, remote, branch)` 开头；
  - finish_test_evaluation 检查 `sha != session.marker_sha256`；
  - require_test_session 没有 return。
- **i. B25：** 仍是唯一待决的解释；所有 TEST 路径都调用 verify_authorization。
- **j. 探针与接口：**
  - 探针对 TG、E、LK、FZ 的每个调用，参数都与签名一致；
  - `session.marker_commit` 是 TestSession 的字段；
  - `probe interface mismatches: []`。
- **k. 远端与分支（与差异项直接相关）：**
  ```
  the checked-out branch is tested only when a branch argument is given: True
  testgate.py  remote_heads           check_remote(root, remote)                               branch given (checked-out branch tested): False
  testgate.py  commit_paths           check_remote(root, remote, branch)                       ... True
  testgate.py  _commit_preconditions  check_remote(root, remote, branch)                       ... True
  test_data.py main                   TG.check_remote(root, TG.PILOT_REMOTE, TG.PILOT_BRANCH)  ... True
  constants: CANONICAL_REPO 'leotree2020/OpenMythos', PILOT_REMOTE 'origin', PILOT_BRANCH 'metrix-e1-pilot-protocol-v1'
  scrub applied in: ['_blocked', '_push', 'commit_paths', 'remote_url', 'repo_id']
  ```
- **l. 探针防护的顺序：**
  - 原文：`statement index: refusal 4 | override 5 | fz load 8 | operations loop 13`；
  - 即先拒绝，后覆盖 CANONICAL_REPO 与 PILOT_BRANCH，再加载冻结文件和执行操作。

与 Executor 一致：a–l 全部一致。k 从静态上解释了任务 1 中 N1 和 N2 的差异。

---

## 4. 以黑盒方式运行 TEST 生成器（ic4_04_test_refusal.txt）
命令：`bash audit/ic4_run_logged.sh audit/stdout/impl_c/ic4_04_test_refusal.txt <venv>/python -I -B audit/ic4_04_test_refusal.py /home/user/OpenMythos <venv>/python <scratchpad>/inputs <scratchpad>/c1_data <scratchpad>/ic4_test_out_c1`

脚本内部实际运行：`cd metrix/e1-pilot/src && <venv>/python -m metrix_e1.test_data --inputs … --data …/c1_data --out …/ic4_test_out_c1`

原始输出（节选）：
```
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
exit code 1 | killed by the auditor False
refusal line == the Executor's in c1_06_checks_r3.txt (...): True
out_dir ... exists: False | data dir unchanged: True | inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status ... unchanged: True
results directory created: False | st10_record.json in the working tree or in any commit: False
RESULT: PASS
exit=0
```
与 Executor 一致：拒绝的文字与 c1_06 中的原文相同，且没有任何产物。

---

## 差异汇总（导致 BLOCK 的唯一一项）
- **现象：**
  - N1（检出分支 'work'）和 N2（分离 HEAD）中，`marker` 操作，即 `testgate.refuse_if_marker(repo, "origin")`，返回 "ACCEPT no marker"；
  - 运行前登记的预期为 STOP - BLOCKED，依据是你本轮的说明：“若临时仓库的检出分支不是 main，begin 与 marker 为 BLOCKED”。
- **原因：**
  - testgate.py:183–188 只在 `branch is not None` 时检查检出分支；
  - remote_heads（第 201 行）调用的是 `check_remote(root, remote)`，不传分支，所以 refuse_if_marker 和 refuse_if_st10_record 都不检查检出分支。
- **与已提交文字的不一致：**
  - 模块文档第 28–31 行写 “every look-up on a remote, every commit and push checks the remote's URL and the branch against them (check_remote, BLOCKED otherwise)”；
  - check_remote 的文档（第 178–179 行）写 “`branch` (when given) and the checked-out branch are the pilot's branch”，可读作无论如何都检查检出分支。
- **影响：**
  - 不绕过任何闸门：begin 在写标记前、test_data.main 在生成 TEST 前，都检查了检出分支（N1、N2 的 begin 为 BLOCKED 且没有写入；静态 k 也确认）；
  - refuse_if_marker 在非 main 检出上的回答本身是正确的：它检索了 --all、--reflog 和远端全部分支；
  - Executor 的测试与变异清单中，没有针对 marker 在非 main 检出上的用例。
- **修复（二选一，由 Review Gate 决定）：**
  - (a) 让检出分支的检查对标记检索也生效，例如把检出分支的检查移出 `if branch is not None`；
  - (b) 改正第 28–31 行、第 178–179 行的文档和本轮说明：写明检出分支只在 begin 的预检、commit_paths 和 TEST 驱动中检查，标记检索不检查。
- 改后可用 ic4_01（N 组）重跑验证。

## INFO（不计入结论，供 Review Gate 参考）
1. test_data.py 的模块文档仍有过时文字：第 21–25 行写 “Committing and pushing the record, … follow outside this command”。这与第 27–31 行和代码不符，因为 main 现在会自己提交并推送 ST10 记录。
2. test_data.main 在生成 TEST 之前，没有预检索引是否有暂存，也没有做推送预检。如果索引有暂存或推送不是快进，会在 TEST 已生成、ST10 记录已写入工作区之后，才由 commit_paths 判为 BLOCKED。工作区中的这份记录仍会拒绝第二次生成。
3. B17（远端只有 tag 指向标记、没有分支）仍不在检索范围内，与你的说明一致。
4. st10 操作本身不检查 B25，也不读两份记录的内容。所有 TEST 路径都先调用 verify_authorization。
5. 探针把 CANONICAL_REPO 设为临时仓库的 origin，所以“另一个仓库”这一拒绝无法用黑盒测到。静态 k 和 Executor 的测试（test_only_the_pilots_remote_and_branch）覆盖了这一点。
6. 未经 scrub 的 raise 只有两处，带的都是本地 git log 和 git status 的输出：_ever_committed:161、code_commit:269。
7. src/、tests/、reports/ 下有被忽略的 __pycache__，最新文件时间为 01:27:10 UTC，早于我的第一次运行（01:39:21）。比我的状态文件更新的 .pyc 数量为 0（ic4_99），所以不是我写入的。

## 运行后的 `git status --short` 原始输出（ic4_99_git_status_final.txt）
```
A  metrix/e1-pilot/reports/IMPL_C_REPORT.md
A  metrix/e1-pilot/reports/impl_c/c1_00_session_start.txt
A  metrix/e1-pilot/reports/impl_c/c1_01_env_fetch.txt
A  metrix/e1-pilot/reports/impl_c/c1_02_checks.txt
A  metrix/e1-pilot/reports/impl_c/c1_03_checks_r2.txt
A  metrix/e1-pilot/reports/impl_c/c1_04_checks_r2b.txt
A  metrix/e1-pilot/reports/impl_c/c1_05_checks_r3_interrupted.txt
A  metrix/e1-pilot/reports/impl_c/c1_05b_restart_restore.txt
A  metrix/e1-pilot/reports/impl_c/c1_06_checks_r3.txt
A  metrix/e1-pilot/reports/impl_c/c1_gate_probe.py
A  metrix/e1-pilot/reports/impl_c/c1_mutate.py
A  metrix/e1-pilot/reports/impl_c/c1_mutate_r2.py
A  metrix/e1-pilot/reports/impl_c/c1_mutate_r3.py
A  metrix/e1-pilot/reports/impl_c/c1_probe_run.py
M  metrix/e1-pilot/src/metrix_e1/evaluate.py
M  metrix/e1-pilot/src/metrix_e1/frozen.py
M  metrix/e1-pilot/src/metrix_e1/gate.py
M  metrix/e1-pilot/src/metrix_e1/interpretations.py
M  metrix/e1-pilot/src/metrix_e1/leakage.py
M  metrix/e1-pilot/src/metrix_e1/record.py
M  metrix/e1-pilot/src/metrix_e1/stops.py
M  metrix/e1-pilot/src/metrix_e1/test_data.py
A  metrix/e1-pilot/src/metrix_e1/testgate.py
A  metrix/e1-pilot/tasks/IMPL_C_OWNER_MESSAGE.md
M  metrix/e1-pilot/tests/test_data_hashes.py
M  metrix/e1-pilot/tests/test_evaluate.py
M  metrix/e1-pilot/tests/test_gate.py
M  metrix/e1-pilot/tests/test_stops.py
M  metrix/e1-pilot/tests/test_test_data.py
A  metrix/e1-pilot/tests/test_testgate.py
?? metrix/e1-pilot/audit/ic2_01_gate_scenarios.py
?? metrix/e1-pilot/audit/ic2_02_content_hashes.py
?? metrix/e1-pilot/audit/ic2_03_static.py
?? metrix/e1-pilot/audit/ic2_04_test_refusal.py
?? metrix/e1-pilot/audit/ic2_run_logged.sh
?? metrix/e1-pilot/audit/ic3_01_gate_scenarios.py
?? metrix/e1-pilot/audit/ic3_02_content_hashes.py
?? metrix/e1-pilot/audit/ic3_03_static.py
?? metrix/e1-pilot/audit/ic3_04_test_refusal.py
?? metrix/e1-pilot/audit/ic3_run_logged.sh
?? metrix/e1-pilot/audit/ic4_01_gate_scenarios.py
?? metrix/e1-pilot/audit/ic4_02_content_hashes.py
?? metrix/e1-pilot/audit/ic4_03_static.py
?? metrix/e1-pilot/audit/ic4_04_test_refusal.py
?? metrix/e1-pilot/audit/ic4_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_01_gate_scenarios.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_01b_B05_history.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_02_content_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_03_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_04_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic2_99_git_status_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_01_gate_scenarios_staged_probe.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_01b_gate_scenarios_corrected_probe.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_02_content_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_03_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_04_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic3_99_git_status_final.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_01_gate_scenarios.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_01_gate_scenarios_run1_script_error.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_01a_script_fix_after_run1.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_02_content_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_03_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_04_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic4_99_git_status_final.txt
```
- A 和 M 行是被审对象原有的暂存内容，未被改动：HEAD 仍为 eb05e422…，write-tree 仍为 9be4df2a…，工作区等于暂存区（ic4_99 中为 WORKTREE_EQUALS_INDEX）。
- 本次新增的只有 audit/ 下的 ic4_ 文件。
- 临时仓库都在会话临时目录 /tmp/claude-0/-home-user/8645aeea-5a45-5281-b238-3e6075410a17/scratchpad/ic4_repos，在仓库之外。

结论：BLOCK
