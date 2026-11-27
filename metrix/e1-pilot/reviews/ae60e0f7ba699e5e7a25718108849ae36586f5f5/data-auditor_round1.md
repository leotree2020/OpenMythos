# data-auditor, C1 second submission, round 1 (staged tree 365960a0e2c5cc28869be9ed44a08d4170389633, parent 5f5cd51e)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
# data-auditor 报告：C1 第二次送审，第 1 轮

运行环境：主机 `vm`，Anthropic 云容器，只用 CPU（无 nvidia 设备节点，`torch.cuda.is_available()` 为 False）。没有加载任何模型权重：只读取了 tokenizer 文件，tiny 模型在内存中随机初始化。没有生成、读取或统计真实 TEST。只在 `metrix/e1-pilot/audit/` 下写入，暂存区未改动：write-tree 运行前后都是 `365960a0e2c5cc28869be9ed44a08d4170389633`，与 tree.txt 一致。

定义核对：仓库中 `.claude/agents/data-auditor.md` 的 tools 行为 `Read, Grep, Glob, Write, Bash`，与已加载的定义一致。

## 0. 状态（`audit/stdout/impl_c/ic5_00_state.txt`）

命令：`ic5_run_logged.sh … bash -c "git rev-parse HEAD && git write-tree && cat tree.txt && {git diff --cached --stat; git diff --cached;} | cmp - input.diff …"`

原始输出摘录：
```
5f5cd51e83d8f637ca6252dc1ba71c32818bf19b
365960a0e2c5cc28869be9ed44a08d4170389633
365960a0e2c5cc28869be9ed44a08d4170389633
INPUT_DIFF_IDENTICAL
DELTA_DIFF_IDENTICAL
WORKTREE_EQUALS_INDEX
7a0cfbee…a35f3  metrix/e1-pilot/reports/impl_c/c1b_gate_probe.py
30b4a243d6c1bffa979800d7eccb6b9ce8d96ee2e3876a33861bfb88cdb6d3a2  -   (git diff --cached HEAD -- src tests；与 c1b_02 记录的相同)
ls: cannot access 'metrix/e1-pilot/results': No such file or directory
```
input.diff 与 delta_from_round3.diff 都能从当前暂存树原样复现，因此本次审计的对象就是送审的那棵树。

## 1. 闸门场景（`audit/ic5_01_gate_scenarios.py` → `audit/stdout/impl_c/ic5_01_gate_scenarios.txt`）

命令：`ic5_run_logged.sh …/ic5_01_gate_scenarios.txt venv/bin/python -I -B audit/ic5_01_gate_scenarios.py /home/user/OpenMythos venv/bin/python <scratchpad>/ic5_repos`

做法：
- 运行的探针就是暂存版（sha256 7a0cfbee…）。它只作为子进程被驱动，我的脚本不 import、不调用、不复制 Executor 的代码。
- 每次运行探针之前，脚本先按我自己的模型算出预期并打印成 "pre-registered" 行。
- 同一进程内、两个操作之间的状态变化，由临时 clone 中的 pre-push 钩子触发；每个钩子只动作一次。

原始输出末尾：
```
probe's CANONICAL_REPO line == my reading of origin's URL at the probe's start: checked in 127 runs, mismatches []
probe runs 130; runs whose stdout+stderr contain the URL secret: 0
summary: compared operations same 326 | DIFFERENT 2 | INFO (no expectation) 22 | ERROR or unparsable probe output among them: 2 | post-checks FAILED 0
gates (my model vs the code through the staged probe): NOT consistent
RESULT: FAIL
exit=1
```

各组结果（完整原文在 stdout 文件中）：

**(a) 检出条件（X0–X10）。** 七类条件各自对 marker、st10rec、pre、begin 四个操作运行，结果全部是预期的 `STOP - BLOCKED`；"nothing written" 后检全部 ok，拒绝信息也给出了对应原因。
- X1 另一分支，X2 分离 HEAD
- X3 领先远端，X4 落后远端（另一 clone 推送），X5 分叉
- X6 origin 为另一仓库名：钩子在首个 pre 的 dry run 中把 URL 改为 `OtherOwner/OtherName`。输出为 `remote origin is repository 'OtherOwner/OtherName', not the pilot's 'X6/remote'`。
- X7 远端不可达，X8 远端没有 main 分支，X9 远端为空仓库
- X10 浅克隆
- 对照组 X0 与 X10u（unshallow 之后）：marker ACCEPT、st10rec REFUSE（记录已存在）、pre ACCEPT、begin ACCEPT，标记提交的各项后检全部 ok。

**(b) 两处检索（W01–W09、T00–T03）。**
- 标记只在工作区、只在远端最新树（工作区副本已删）、两处都有：marker 与 begin 均为 BLOCKED。
- 有结果文件（无论有无标记，无论在工作区还是远端最新树）：EVALUATED。
- ST10 记录只在工作区、只在最新树、两处都有：st10rec 为 REFUSE；没有记录时为 ACCEPT。

"按裁决不检索"组（W-n1–W-n11、T-n1–T-n6）：更早历史、本地或远端侧分支、reflog、本地或远端标签、`--no-ff` 与 `-s ours` 合并、只在 index 中，结果全部是预期的 ACCEPT，此时 begin 正常写入新标记。唯一例外是 W-n11（标记只在 index）：begin 因"有暂存"而 BLOCKED，与模型一致。

**(c) ST10 与会话。**
- A 组 52 个 ST10 场景，st10 与 begin 两个操作全部一致。A20（缩写的 code commit）只记 INFO，实际被 REFUSE。
- C1 完整流程全部一致：begin，错误哈希 REFUSE，非 TEST 模型 REFUSE，eval ACCEPTED-BY-GATES，gate 认领后重复 REFUSE，16 个模型未全部认领时 finish REFUSE，全部认领后 finish ACCEPT。finish 之后 marker 为 EVALUATED、begin 为 EVALUATED、st10rec 为 REFUSE。结果提交的父提交是标记提交，只改动结果文件这一个路径，内容为 `{probe, session_id(=标记的), marker_commit}`。
- C2（新进程）、K1（新 clone）为 EVALUATED；K2（过期 clone）为 BLOCKED，pull 之后为 EVALUATED；C3（同一进程第二次 begin）为 BLOCKED。
- begin 之后 HEAD 或分支被改动，eval、gate、finish 均为 BLOCKED：E1 本地新提交，E2 新提交已推送，E3 切到另一分支，E4 分离 HEAD，E5 reset。
- E7（begin 之后 ST10 记录在工作区被改）：eval 为 REFUSE。

**(d) 提交与推送前提。**
- D1 有暂存、D2 没有身份、D3 pushurl 不可推送、D3b 本地钩子拒绝 dry run：pre 与 begin 均为 BLOCKED，且什么都没写入。
- D4（远端 pre-receive 拒绝）、D4b（钩子只拒绝真实推送）：begin 为 BLOCKED，本地留下只改动标记路径的提交，远端不变；此后 marker、st10rec、pre、begin 全部 BLOCKED。
- D5（results 目录被 `.gitignore` 忽略）：begin 为 BLOCKED，标记留在工作区，此后 marker 为 BLOCKED。
- G1/G2（记录不是 JSON 对象）为 REFUSE；U1/U4 的 URL 秘密没有泄漏；P1/P4 探针拒绝运行。

**与 Executor 的差异只有 2 处，原因相同：**
```
[DIFFERENT] finish   expected REFUSE   observed ERROR   AttributeError: 'NoneType' object has no attribute 'marker_commit'
```
出现在 C0（begin 之前调用 finish）和 C2（新进程中调用 finish）。原因在代码里：`finish_test_evaluation` 与 `claim_checkpoint` 的守卫 `_LIVE.get(getattr(session, "session_id", None)) is not session` 在 session 为 None 时求值为 False，于是 None 通过了守卫。`require_test_session` 的守卫以 isinstance 开头，不受影响。ic5_03 第 c 节有静态证明。

**对 Executor 所问"评测调用不 fetch"的判断（E6）。** 场景：另一 clone 在标记之后推送，本地 HEAD 仍是标记提交。结果是 eval 和 16 个 gate 都 ACCEPT（INFO，因为不 fetch）；finish 因为要 fetch 而 BLOCKED（`HEAD … is not the latest commit`）；之后 marker 为 BLOCKED。我的判断：
- 远端最新树中仍有标记，任何其他 begin 都会被拒，所以这种做法不会导致"评测两次"。
- 每次调用都会对 HEAD（即标记提交）上的记录重新执行 st10_check，所以也不会在 ST10 不成立时评测。
- 结论是符合防范对象；与裁决第 1 项"所有 TEST 路径"的字面读法有出入，记为 MINOR-2，请 Review Gate 确认。

## 2. 四个冻结内容哈希（`audit/ic5_02_content_hashes.py` → `ic5_02_content_hashes.txt`）

命令：`… ic5_02_content_hashes.py /home/user/OpenMythos <S>/inputs/qwen_tokenizer <S>/c1_data`

原始输出：
```
facts        mine 406c8801…6b97 | PROTOCOL_FROZEN 406c8801…6b97 | Executor generate 406c8801… | Executor verify 406c8801… | ALL EQUAL True
train_S      686fdd2f…c1e | … ALL EQUAL True
candidates   e5d15c99…3705 | … ALL EQUAL True
anchor_texts 8828bc4f…2408 (我用 Qwen tokenizer 自行解码 ids 得到的哈希也相同) | … ALL EQUAL True
```
- 8 个数据文件的字节 sha256 与我在 stage B 的记录、以及 c1b_02 中 Executor 的列表全部相等；c1_data 中没有 TEST 文件。
- D 节（静态）：`content_hashes` 在 HEAD 与现在的四个序列化表达式、键序、辅助函数完全相同。
- `RESULT: PASS`。与 Executor 一致。
- 本轮没有重跑 L1–L6、候选可行性与 split：数据与我已审过的版本逐字节相同（`audit/stdout/impl_a/17_ia_compare_gen4.txt`，L1–L6/候选可行性/split 均为 PASS：`18_ia_leakage_gen4.txt`、`20_ia_feasibility_gen4.txt`、`19_ia_split_gen4.txt`）。

## 3. 静态核对（`audit/ic5_03_static.py` → `ic5_03_static.txt`）

命令：`… ic5_03_static.py /home/user/OpenMythos`，结果 `RESULT: PASS`。

- a. test_data.main 的顺序：`check_preconditions`(161) < `code_commit`(174) < `check_commit_preconditions`(175) < `refuse_if_st10_record`(176) < `generate_test`(177)。这些都是 main 顶层的无条件语句，generate_test 只被调用这一次。
- b. ST10 记录、标记与结果中没有 TEST 行：
  - ST10 记录对 report 只读 `report['checks']`（只取键）与 `report['checks'][c]['value']`；文件只以 sha256 出现。
  - 标记中只有 `rows_hashes`。
  - 结果文件是调用方传入的 `result` 加 session_id 与 marker_commit，其内容取决于 C2 的 run_pilot。
- c. TEST 路径与检出：
  - `check_checkout` 的实现与裁决第 1 项逐条对应（检查 5 项，失败均为 BLOCKED）；`_where` 只查工作区与 `cat-file -e <tip>:<rel>`。
  - 调用图：refuse_if_marker、refuse_if_st10_record、check_commit_preconditions、begin 都经过 check_checkout；require_test_session 经过 `_check_session_checkout`（不 fetch）；finish 两者都经过。
  - evaluate_model 中的顺序：verify_authorization(329) < require_test_session(331) < require_gpu(332) < claim_checkpoint(333) < score_qa(338)。
- d. 探针调用的 15 个包内函数，参数与实际签名全部一致；它读写的模块属性都存在；它的守卫（第 91 行）在覆盖 CANONICAL_REPO（第 93 行）和第一个操作（第 102 行）之前。
- e. 已删除的检索在代码中无残留：remote_heads、--all、--reflog、--full-history、rev-list、--heads、_ever_committed、log、tags 均为 0 处；唯一的 ls-remote 是 `_push` 核对已推送的 ref。
- f. B25 的 status 为 `ACCEPTED（Review Gate 2026-11-25）`；按我的读法 pending() 为 `[]`。
- h. IMPL_C1_RULING.md 中的防范对象与调用文字逐字相同。

与 Executor 的说明一致。

## 4. B25（`audit/ic5_04_b25.py` → `ic5_04_b25.txt`）

命令：`… ic5_04_b25.py /home/user/OpenMythos venv/bin/python <S>/ic5_b25`。

我按 B25 的文字自写了实现：字节经 numpy 取得，没有用 uint8 view。在 5 个随机种子的 tiny Qwen3 上（state_dict 有 25 个键，tied 权重在两个键名下都出现，非持久 buffer 不在其中），先算出我的哈希，再运行探针的 tinysha 对照：
```
seed 0 mine a895622c…e251 | probe … a895622c…e251 | equal True
seed 1 / 4 / 7 / 12345 … equal True
distinct hashes over the seeds: 5 of 5
```
另外：train() 与 eval() 模式下哈希相同；改动一个元素哈希就变，改回后恢复。`RESULT: PASS`。与 Executor 一致。

## 5. TEST 生成器黑盒（`audit/ic5_05_test_refusal.py` → `ic5_05_test_refusal.txt`）

只运行了一次：`cd src && venv/bin/python -m metrix_e1.test_data --inputs <S>/inputs --data <S>/c1_data --out <S>/ic5_test_out`

```
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL   (generator exit code 1)
refusal line == the Executor's in c1b_02_checks.txt: True
the refusal names the Gate 0 record …: True
out_dir exists: False | data dir unchanged: True | src tree unchanged: True | git status unchanged: True | results directory created: False
```
脚本 `RESULT: PASS`。与 Executor 一致。

## MINOR 登记（均在防范对象以外，不作为 BLOCK 理由）

- **MINOR-1**：`finish_test_evaluation(session=None)` 与 `claim_checkpoint(None, …)` 抛出 AttributeError，而不是文档写的拒绝（"no TEST session of this process"）。实际影响：什么都不写入，也不会引起评测。evaluate_model 会先经过 require_test_session，因此 claim_checkpoint(None) 走不到。建议改用 `isinstance(session, TestSession)` 守卫。
- **MINOR-2**：评测调用只做本地的标记提交检查，不 fetch。这符合防范对象，但与裁决第 1 项的字面读法不同，请 Review Gate 确认。行为见 E6。
- **提示（C2）**：结果文件的内容由调用方决定，C2 需要核对其中不含 TEST 原文。
- **提示**：只在 index 中的标记或 ST10 记录不在检索范围内（这符合裁决），但 begin 与 TEST 驱动会被"有暂存"挡住，不构成缺口。
- **仅覆盖了静态核对**：生成 TEST 之后真实推送被拒的路径无法黑盒复现，因为黑盒复现需要生成真实 TEST。

## 试跑记录

- ic5_01 试跑 1 发现我自己脚本的 5 个后检缺陷（W04/W06–W08 预置了结果文件；E5 在 reset 之后找不到标记提交），已修正。预期模型没有改动。上面那 2 个 DIFFERENT 在试跑中已经出现，原样保留。
- ic5_03 试跑 1 有一个检查器缺陷，已修正。
- 试跑原文与修改说明：`ic5_0x_trials_and_script_fixes.txt` 以及各个 `*_superseded.txt`。TEST 生成器没有试跑过。

## 文件（全部在 `/home/user/OpenMythos/metrix/e1-pilot/audit/` 下）

脚本：
- `ic5_01_gate_scenarios.py`
- `ic5_02_content_hashes.py`
- `ic5_03_static.py`
- `ic5_04_b25.py`
- `ic5_05_test_refusal.py`
- `ic5_run_logged.sh`

完整 stdout（`stdout/impl_c/`）：
- `ic5_00_state.txt`
- `ic5_01_gate_scenarios.txt`
- `ic5_02_content_hashes.txt`
- `ic5_03_static.txt`
- `ic5_04_b25.txt`
- `ic5_05_test_refusal.txt`
- `ic5_99_git_status_final.txt`（其中 exit=2 只来自最后一条 `ls results`，该目录本就不存在）
- `ic5_0x_trials_and_script_fixes.txt`
- `ic5_01_trial1_superseded.txt`
- `ic5_03_trial{1,2,3}_superseded.txt`
- `ic5_04_trial1_superseded.txt`

## 运行后 `git status --short` 原始输出（write-tree 365960a0e2c5cc28869be9ed44a08d4170389633）
```
M  metrix/e1-pilot/reports/IMPL_C_REPORT.md
A  metrix/e1-pilot/reports/impl_c/c1b_01_checks.txt
A  metrix/e1-pilot/reports/impl_c/c1b_02_checks.txt
A  metrix/e1-pilot/reports/impl_c/c1b_gate_probe.py
A  metrix/e1-pilot/reports/impl_c/c1b_mutate.py
A  metrix/e1-pilot/reports/impl_c/c1b_probe_run.py
M  metrix/e1-pilot/src/metrix_e1/evaluate.py
M  metrix/e1-pilot/src/metrix_e1/frozen.py
M  metrix/e1-pilot/src/metrix_e1/gate.py
M  metrix/e1-pilot/src/metrix_e1/interpretations.py
M  metrix/e1-pilot/src/metrix_e1/leakage.py
M  metrix/e1-pilot/src/metrix_e1/record.py
M  metrix/e1-pilot/src/metrix_e1/stops.py
M  metrix/e1-pilot/src/metrix_e1/test_data.py
A  metrix/e1-pilot/src/metrix_e1/testgate.py
A  metrix/e1-pilot/tasks/IMPL_C1_RULING.md
A  metrix/e1-pilot/tasks/IMPL_C_OWNER_MESSAGE.md
M  metrix/e1-pilot/tests/test_data_hashes.py
M  metrix/e1-pilot/tests/test_evaluate.py
M  metrix/e1-pilot/tests/test_gate.py
M  metrix/e1-pilot/tests/test_stops.py
M  metrix/e1-pilot/tests/test_test_data.py
A  metrix/e1-pilot/tests/test_testgate.py
?? metrix/e1-pilot/audit/ic5_01_gate_scenarios.py
?? metrix/e1-pilot/audit/ic5_02_content_hashes.py
?? metrix/e1-pilot/audit/ic5_03_static.py
?? metrix/e1-pilot/audit/ic5_04_b25.py
?? metrix/e1-pilot/audit/ic5_05_test_refusal.py
?? metrix/e1-pilot/audit/ic5_run_logged.sh
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_00_state.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_01_gate_scenarios.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_01_trial1_superseded.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_02_content_hashes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_03_static.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_03_trial1_superseded.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_03_trial2_superseded.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_03_trial3_superseded.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_04_b25.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_04_trial1_superseded.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_05_test_refusal.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_0x_trials_and_script_fixes.txt
?? metrix/e1-pilot/audit/stdout/impl_c/ic5_99_git_status_final.txt
```
暂存部分与送审时相同，新增的只有 audit/ 下的未跟踪文件。

## 判定依据

- 防范对象范围内的项目全部与 Executor 一致，全部可以复算。
- 唯一的不一致是 MINOR-1。它不可能导致评测两次，也不可能让 TEST 在 ST10 不成立时被评测，按裁决记为 MINOR。
- 按 metrix/CLAUDE.md 第 10 节，data-auditor 目前仍是"待验证"，本 PASS 仅作参考。

结论：PASS
