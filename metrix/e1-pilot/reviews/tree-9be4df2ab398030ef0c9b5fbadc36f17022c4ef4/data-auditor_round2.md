# data-auditor, C1 work commit, round 2 (staged tree dc4f28df108ac129120eae801de1ad02119c4c05, parent eb05e422); interrupted by HTTP 429 and resumed (interruption_round2.txt, resume_message_data-auditor_round2.txt); an information message about the probe was sent before the interruption (its text is repeated in the resume message)
# extracted unchanged from the subagent transcript by reports/round6/review_extract.py
---
数据审计报告：METRIX E1-PILOT 阶段 C 第 1 段（C1）工作提交，第 2 轮（因 HTTP 429 中断，进程重启后续审）

审计对象：暂存树 dc4f28df108ac129120eae801de1ad02119c4c05，父提交 eb05e42243b54b78cb400b40293ef56f67611852，仓库 /home/user/OpenMythos。
运行环境：主机 vm，Anthropic 云容器，只用 CPU（/dev 下没有 nvidia 设备节点，torch.cuda.is_available() 为 False）。任务 2 只加载了 Qwen tokenizer；探针里的 tiny 模型是随机初始化的 2 层 Qwen3，没有加载任何权重。我没有生成、读取或统计真实 TEST，用到的 TEST 行全部是我自己写的人造行。
定义：已先读仓库中的 .claude/agents/data-auditor.md。它的 frontmatter 和 tools 行（Read, Grep, Glob, Write, Bash）与我加载的定义一致。

## 结论先行
- 被审的 src/ 代码与我的独立模型完全一致。改用 Executor 提供的修正探针副本后：比对 214 项全部相同，DIFFERENT 0，后置核对失败 0。第 1 轮的 B05 已修复。四个冻结内容哈希一致；TEST 生成器拒绝运行，且没有任何产物。
- 结论仍是 BLOCK，原因只有一个：暂存树中的黑盒探针 reports/impl_c/c1_gate_probe.py 与本轮 testgate 的接口不匹配。
  - `marker` 操作总是抛出 `TypeError`，因此这一操作无法复算，共 35 项输出不能比对。
  - `begin` 成功后，探针在打印结果时抛出 `AttributeError`。
- 这个文件是本提交的一部分，也是 Review Gate 为本次审计指定的黑盒工具。Executor 在 c1_03 和 c1_04 中都没有运行过它。按定义，“不可复算即为 BLOCK”。
- 修复方法：把修正副本里的两处改动提交入库，保留 `PILOT = Path(__file__).resolve().parents[2]`，并让 Executor 在自己的检查里至少运行一次探针。入库后用 ic3_01 对已提交的探针重跑，结果应与 ic3_01b 相同。

## 脚本（均为本轮新写，放在 metrix/e1-pilot/audit/；都没有 import、调用或复制 Executor 的代码，探针只以子进程 `python -I -B` 方式运行）
- /home/user/OpenMythos/metrix/e1-pilot/audit/ic3_01_gate_scenarios.py：我的独立闸门模型加黑盒比对。由我的 ic2_01 改写。可选第 4 个参数，用来指定改跑哪个探针文件。
- /home/user/OpenMythos/metrix/e1-pilot/audit/ic3_02_content_hashes.py：任务 2。
- /home/user/OpenMythos/metrix/e1-pilot/audit/ic3_03_static.py：任务 3，文件按文本读入后用 ast 解析，不 import。
- /home/user/OpenMythos/metrix/e1-pilot/audit/ic3_04_test_refusal.py：任务 4，由我的 ic2_04 改写，只改了文件头。
- /home/user/OpenMythos/metrix/e1-pilot/audit/ic3_run_logged.sh：运行包装。把 stdout 和 stderr 合并后完整写入文件，首行记录命令，末行记录 exit。

## 完整 stdout（/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/impl_c/）
| 文件 | 内容 | sha256 前缀 |
|---|---|---|
| ic3_00_state.txt | 状态 | cb58f17d… |
| ic3_01_gate_scenarios_staged_probe.txt | 任务 1，暂存的探针 | 9a1bc847… |
| ic3_01b_gate_scenarios_corrected_probe.txt | 任务 1，修正副本 | d243b1b3… |
| ic3_02_content_hashes.txt | 任务 2 | 7c7df92b… |
| ic3_03_static.txt | 任务 3 | 9e41cff8… |
| ic3_04_test_refusal.txt | 任务 4 | 4eae0239… |
| ic3_99_git_status_final.txt | 最终 git status | 72a15c61… |

另外两份调试试跑的输出（/tmp/claude-0/-home-user/8645aeea-5a45-5281-b238-3e6075410a17/scratchpad/ic3_01_trial.txt 和 ic3_03_trial.txt）不作为证据。

---

## 0. 状态（ic3_00_state.txt）
命令：`bash audit/ic3_run_logged.sh audit/stdout/impl_c/ic3_00_state.txt bash -c "<rev-parse; write-tree; cmp input_round2.diff; cmp delta_round2.diff; diff --quiet; status; sha256sum; diff 暂存探针 修正副本; torch 版本>"`

原始输出（节选）：
```
eb05e42243b54b78cb400b40293ef56f67611852
dc4f28df108ac129120eae801de1ad02119c4c05
dc4f28df108ac129120eae801de1ad02119c4c05
INPUT_DIFF_IDENTICAL
DELTA_DIFF_IDENTICAL
WORKTREE_EQUALS_INDEX
dfcd9c33...f81  metrix/e1-pilot/reports/impl_c/c1_gate_probe.py
772b4dc3...8b1  .../scratchpad/c1_gate_probe_fixed.py
--- diff staged probe -> corrected copy (Executor, session scratchpad):
17c17  marker testgate.refuse_if_marker(REPO, "origin", "main") -> (REPO, "origin")
38c38  PILOT = Path(__file__).resolve().parents[2] -> Path("/home/user/OpenMythos/metrix/e1-pilot")
101c101  TG.refuse_if_marker(repo, "origin", "main") -> TG.refuse_if_marker(repo, "origin")
105c105,107  len(session.models) -> models read from HEAD:<marker>
3.13.18 2.11.0+cu130 5.22.2 False
```
核对修正副本：它与暂存的探针只在上面列出的几处不同，即文档 1 行、PILOT 1 行、`marker` 调用 1 行、`begin` 的打印。与 Executor 的说明一致。我决定两份都跑，暂存版和修正副本分别记录。

---

## 1. 闸门场景：我的独立模型与探针黑盒比对

执行的命令：
- 暂存探针：`cd <scratchpad> && bash audit/ic3_run_logged.sh audit/stdout/impl_c/ic3_01_gate_scenarios_staged_probe.txt python3 -I -B audit/ic3_01_gate_scenarios.py /home/user/OpenMythos <scratchpad>/venv/bin/python <scratchpad>/ic3_repos_staged`
- 修正副本：同上，输出到 ic3_01b_gate_scenarios_corrected_probe.txt，临时仓库目录为 <scratchpad>/ic3_repos_corrected，并在命令末尾加参数 `<scratchpad>/c1_gate_probe_fixed.py`。

做法：
- 我的模型依据协议第 3 节 L6、第 8 节第 8 步、第 11 节 ST10，以及补充裁决 3–5 编写。本轮的结果类别按调用文字更新：
  - 环境类拒绝为 BLOCKED；
  - 已评测为 EVALUATED，即探针输出 "ERROR TestAlreadyEvaluated"；
  - CPU 上的 eval 不登记 checkpoint，登记只由 gate 操作完成；
  - B25 待决时，begin 和 eval 拒绝。
- 所有预期都在探针运行之前算出。与第 1 轮不同，同一进程内 begin 之后的 eval 和 gate 预期，也在运行前由“我预期的标记”加上场景计划的改动算出：我预期的标记是 30 个 checkpoint 哈希加 N，以及我的 16 个 TEST 模型。运行后再核对实际状态是否符合这些假设。
- 我在标记中查找时：
  - 本地：先 rev-list --all，再对每个提交做 cat-file -e，不经过历史简化；
  - 远端：用同样方法遍历裸远端的全部分支。
- 读取的冻结事实与第 1 轮相同：冻结提交 87a244db…；TEST 部分上限 L3a/L3b/L4/L5/L6 全为 0；共 30 个训练 run；我选定 F5/L4/A2，由此得到 16 个 TEST 模型。
- 每个场景使用独立的临时仓库和裸远端，都在会话临时目录中。
- E 组的 pre-push 钩子本轮只在被推送的提交含标记时才动作。原因是 begin 现在先做一次 push --dry-run，这一次也会触发 pre-push：日志中每个 E 场景都是两次 invoked，只有一次 acting on <marker commit>。

### 1-1. 修正副本的结果（ic3_01b，原文）
```
summary: compared operations same 214 | DIFFERENT 0 | INFO (no expectation) 9 | PROBE DEFECT (...) 0 | post-checks FAILED 0
gates (my model vs the code through the probe, ACCEPT* counted as ACCEPT): consistent
probe as delivered: works for every operation
RESULT: PASS
exit=0
```

### 1-2. 暂存探针的结果（ic3_01，原文）
```
summary: compared operations same 181 | DIFFERENT 0 | INFO (no expectation) 7 | PROBE DEFECT (op marker not comparable; begin same* = ACCEPT inferred from the repository) 35 | post-checks FAILED 0
gates (my model vs the code through the probe, ACCEPT* counted as ACCEPT): consistent
probe as delivered: DEFECTIVE (35 outcomes not printed as documented)
RESULT: FAIL
exit=1
```
探针缺陷的原文：
```
  [same*] begin   expected ACCEPT   observed ACCEPT*   AttributeError: 'TestSession' object has no attribute 'models'
    post-check ACCEPT*: begin returned (probe print failed); exactly one new commit adds the marker (['c46b88a5f9a2']) and the remote branch holds it ok
  [PROBE-DEFECT] marker   expected STOP - BLOCKED   observed PROBE-DEFECT   TypeError: refuse_if_marker() takes from 1 to 2 positional arguments but 3 were given
```
- `begin` 成功的情形：我从仓库状态推断为 ACCEPT，依据是恰好一个新提交加入标记，且远端分支包含它。随后的全部核对都通过。
- `marker` 操作：每次都是 TypeError，无法比对。由于 begin 的第一步就是 refuse_if_marker，这道闸门的行为已经通过 begin 测到。
- 除这两类缺陷外，暂存探针与修正副本对每个场景的结论相同。

### 1-3. 各组结果（修正副本，预期 = 观察，均为 same）
**A 组：ST10 闸门，共 54 个场景，各比对 st10 和 begin 两个操作。** 全部与预期一致：
- 记录缺失、只在工作区、只暂存、工作区与提交不同、工作区中已删除：均 REFUSE。
- 记录无法解析；记录是 JSON 数组；记录是 JSON 字符串（A06、A06b，本轮新加的非对象拒绝）：均 REFUSE。
- kind 或 mode 错误、绑定另一授权、另一冻结提交、Gate0 和冻结记录重新提交、两个文件哈希与行不符、多出文件键、code commit 在孤立分支上、不存在或为 null：均 REFUSE。
- 计数为 0.0、"0"、false、null、-1、1e0，缺项、多项、为列表、缺字段：均 REFUSE。
- 五项依次取上限+1 且伪造 PASS、L4 = 10**30、L6 与 auditor 不同：均 STOP ST10 BLOCKED。
- auditor 文件缺失、只在工作区、与提交不同、针对另一文件、另一冻结提交、kind 错误、计数为 0.0、"0"、null，文件是 JSON 数组或无法解析（A58b、A58c）：均 REFUSE。
- A59、A60 两边计数不同：STOP ST10 BLOCKED。
- A61 对照：ACCEPT。
- 每次 begin 未被接受后，都核对了“nothing written”，全部为 ok。

**C、K 组：全部满足时的 begin，以及其他克隆。**
- C1 的 begin 为 ACCEPT。标记提交的后置核对全部 ok：
  - 标记提交 == 本地 HEAD == 远端 main；
  - 唯一父提交是原 HEAD，只改动标记路径；
  - 快进推送，本地与远端都没有标签；
  - 标记含 14 个键，含新增的 remote 与 branch，且 remote == origin 的 URL、branch == main；
  - checkpoints 等于冻结记录的 30 个哈希加 N（共 31 个），models 等于我的 16 个 TEST 模型；
  - st10_record_sha256 和 auditor_count_sha256 等于已提交文件的哈希，code_commit 等于标记提交之前的 HEAD；
  - 标记中没有任何人造 TEST 内容。
- C1 中的 eval 和 gate 调用：

| 调用 | 结果 | 说明 |
|---|---|---|
| eval:N:7 | REFUSE | 哈希不符 |
| eval:N:0，连续两次 | 两次都 ACCEPTED-BY-GATES | CPU 上不登记 |
| eval:F-F5-seed202:1，连续两次 | 两次都 ACCEPT | |
| eval:F-F1-seed101:4 | REFUSE | 不是 TEST 模型 |
| eval:Z-Z9-seed1:0 | REFUSE | 不是 TEST 模型 |
| eval:L-L4-seed303:1 | REFUSE | 哈希不符 |
| gate:F-F5-seed303 | 第一次 ACCEPT，第二次 REFUSE | |
| 随后 eval:F-F5-seed303:1 | REFUSE | 已登记 |
| gate:S-F5-seed101:fff… | REFUSE | |
| gate:N | ACCEPT | |
| 随后 eval:N:0 | REFUSE | already evaluated |
| 再次 gate:N | REFUSE | |
| 最后 eval:F-F5-seed202:1 | ACCEPT | |

  这些调用之后，HEAD 仍是标记提交，工作区干净。
- C0（无会话）：eval 和 gate 均 REFUSE。
- C2（另一进程）：eval REFUSE，begin 和 marker 均 STOP - BLOCKED。
- K1（新克隆）、K2（推送前的旧克隆）、K3（推送前的 --single-branch 克隆，其 origin/main 落后）：begin 均 STOP - BLOCKED，没有写入任何东西。

**B 组：已有标记或结果，比对 marker 和 begin 两个操作。**

| 场景 | 预期 = 观察 |
|---|---|
| B01 标记只在工作区 / B02 只暂存 / B03 在另一本地分支 / B04 线性历史中提交后删除 | STOP - BLOCKED |
| **B05 侧分支提交后删除，--no-ff 合并，删掉侧分支引用（第 1 轮的 BLOCK 项）** | **STOP - BLOCKED（已修复）** |
| B05s 侧分支 -s ours 合并（合并后与 main TREESAME） | STOP - BLOCKED |
| B05r 标记在 main，结果在合并掉的侧分支 | EVALUATED |
| B05x 没有标记，结果在合并掉的侧分支 | EVALUATED |
| B05m 标记和结果都在合并掉的侧分支 | EVALUATED |
| B06 标记与结果都已提交 / B07 结果只在工作区 | EVALUATED |
| B08 远端 side 分支，已 fetch / B09 只在远端 main，本地未 fetch / B10 只能从本地 tag 到达 | STOP - BLOCKED |
| **B11 远端 side 分支，从未 fetch** | **STOP - BLOCKED（第 1 轮观察为 ACCEPT，现已拦下）** |
| **B12 只有结果，没有标记** | **EVALUATED（第 1 轮观察为 ACCEPT，现已拦下）** |
| B16 结果只在远端 side 分支，从未 fetch | EVALUATED |
| B14 --single-branch 克隆，标记之后推到远端 side | STOP - BLOCKED |
| B15 --single-branch 克隆落后，标记之后推到远端 main | STOP - BLOCKED |

B05 的原文：
```
 B05 marker committed and deleted on a side branch merged --no-ff, side ref deleted
  [same] marker   expected STOP - BLOCKED   observed STOP - BLOCKED   BLOCKED: TEST evaluation was already started (marker ... in commit 6736b87f..., commit fb766e26...
  [same] begin    expected STOP - BLOCKED   observed STOP - BLOCKED   ...
    post-check nothing written: marker file absent, HEAD unchanged, remote main unchanged   ok
```

**D 组：begin 的其他情形。**
- D1 同一进程内 begin 两次：第一次 ACCEPT，第二次 STOP - BLOCKED，只产生一个标记提交。
- D2 远端已分叉、D2b 远端领先 HEAD：
  - begin 为 STOP - BLOCKED（"origin main (…) is not an ancestor of HEAD: the push would not be a fast-forward"）；
  - “nothing written”核对 ok，即本地不留标记，符合本轮语义；
  - eval REFUSE；再次 begin 仍为 BLOCKED，且没有写入任何东西。
- D3 远端 pre-receive 钩子拒收：
  - begin 为 STOP - BLOCKED，本地留下只含标记路径的标记提交，远端未变；
  - 再次 begin 为 STOP - BLOCKED（"marker … in working tree, commit 94d913ff…"）。
- D4 远端不可达：marker 和 begin 均 STOP - BLOCKED（"cannot list the branches of origin"），没有写入。
- D5 索引有暂存：STOP - BLOCKED，没有写入。
- D6 begin:xyz：REFUSE。
- D7 工作区有修改和未跟踪文件：ACCEPT，标记提交只含标记路径，其余文件保持原样。
- D8 无提交者身份（user.useConfigOnly 设为 true，没有 user.name 和 user.email，全局配置为空）：STOP - BLOCKED（"no git committer identity"），没有写入。
- D9 push.followTags=true 且本地有注释标签：ACCEPT。后置核对原文："local annotated tag still there, remote has no tag (ls-remote --tags: '') ok"。
- D10 远端还没有任何分支：ACCEPT，远端 main 被创建并等于标记提交。
- D12 results/ 被 .gitignore 忽略：
  - begin 为 STOP - BLOCKED（"staging the TEST marker … failed"），没有提交或推送；
  - 再次 begin 为 STOP - BLOCKED（标记在工作区）。

**E 组：begin 推送期间、标记提交之后的改动（由 pre-push 钩子完成）。**
- E0 对照：钩子运行但不改任何东西，eval、eval、gate 都是 ACCEPT。
- 下列改动发生后，eval 和 gate 全部 REFUSE：
  - E1：工作区中改动 ST10 记录；
  - E2：改动并提交 ST10 记录；
  - E3：改动并提交标记里的 TEST 文件哈希；
  - E4：改动并提交 auditor 文件。

**F 组：B25 待决的对照（不带 --interpretations-ruled），原文：**
```
  [same] begin     expected REFUSE   observed REFUSE   IMPLEMENTATION_FAIL: TEST path refused: interpretations not yet ruled by Review Gate: B25
    post-check begin refusal names B25 ... ok
  [same] eval:N:0  expected REFUSE   observed REFUSE   IMPLEMENTATION_FAIL: TEST path refused: interpretations not yet ruled by Review Gate: B25
    post-check eval refusal names B25   ok
    post-check nothing written ... ok
```
- F2：对同一仓库带上 --interpretations-ruled 运行，begin 和 eval 均为 ACCEPT。
- 另一项核对：每次运行中，探针的第一行恰好在带了该参数时才出现（True）。

**H 组：ST10 记录与结果文件的 B05 同类情形（git 层面，不是黑盒）。**
- 为什么不能黑盒：refuse_if_st10_record 在探针中没有对应操作；TEST 驱动又无法在不生成真实 TEST 的前提下指向临时仓库。
- 这个函数的搜索与标记共用 _where 和 _ever_committed（静态核对见 3-g），而标记的同一机制已由 B05、B05s、B05r、B05x、B05m 黑盒验证。
- 原文：
```
 H1 st10_record.json, side branch merged (no-ff), side ref deleted: mine ['74d3fe539df1'] | git log --full-history [2 commits] | git log (no --full-history) []
 H2 st10_record.json, (ours) ... --full-history [2 commits] | (no --full-history) []
 H3/H4 test_evaluation_result.json, no-ff / ours: 同上；H5 marker (ours): 同上
    post-check Hn found by the code's form iff found by mine ... ok（5/5）
```

### 1-4. INFO（没有预设预期，不计入结论）
- A20：code_commit 为 12 位缩写，REFUSE。
- D6：大写十六进制，REFUSE。
- D11：src/ 下有未跟踪文件，begin REFUSE（"uncommitted changes in the code"），没有写入。
- F1：st10 操作在 B25 待决时为 ACCEPT。st10_check 本身不查 interpretations，但所有 TEST 路径都先调用 verify_authorization（见 3-i）。
- B13：标记提交只在 reflog 中（未推送就 reset --hard 掉），begin ACCEPT。
- B17：远端只有一个 tag 指向标记提交，没有分支，begin ACCEPT。
- B13 和 B17 都只会在改写本地或远端历史之后出现，而改写历史须经人工指令。B13 中 begin 从未返回会话，所以没有发生过 TEST 评测。两者都不阻断，记为观察，供 Review Gate 参考。

与 Executor 是否一致：
- src/ 的行为：一致。Executor 本轮所列的每一项语义（--full-history；非对象 JSON 拒绝；远端全部分支都查；只有结果时为 TestAlreadyEvaluated；环境类拒绝为 BLOCKED；预检身份、快进与 dry-run，失败时不写入；D3 留下本地标记；--no-follow-tags；remote 与 branch 字段；先 require_gpu 再 claim；B25 拒绝），都与我的观察相同。
- 探针：不一致。暂存的 c1_gate_probe.py 与它自己的文档和本轮接口不符；c1_03 与 c1_04 中都没有运行探针的记录。

---

## 2. 四个冻结内容哈希的复算与 content_hashes 改动的核对
执行的命令：`bash audit/ic3_run_logged.sh audit/stdout/impl_c/ic3_02_content_hashes.txt <venv>/python -I -B audit/ic3_02_content_hashes.py /home/user/OpenMythos <scratchpad>/inputs/qwen_tokenizer <scratchpad>/c1_data`

原始输出（节选）：
```
  facts        mine 406c8801c5b6... | PROTOCOL_FROZEN 406c8801... | Executor generate 406c8801... | Executor verify 406c8801... | ALL EQUAL True
  train_S      mine 686fdd2f62ed... | ... | ALL EQUAL True
  candidates   mine e5d15c9952d8... | ... | ALL EQUAL True
  anchor_texts mine 8828bc4fcc5a... | ... | ALL EQUAL True
anchor texts from my decode of the stored ids (pinned Qwen tokenizer): 8828bc4f... | every decoded text == stored text: True
  （8 个数据文件）now == my round 3 == Executor listing (r2b): equal True ×8；test_qa.jsonl / general_test.jsonl present: []
HEAD content_hashes: d = Path(data_dir); anchor = read_jsonl(...); with open(... candidates.json, encoding='utf-8') as fh: cands = json.load(fh); return {...}
now content_hashes:  d = Path(data_dir); return {key: sha256_hex(CONTENT_HASH_BYTES[key](d)) for key in CONTENT_HASH_KEYS}
now _json_file(path) is exactly 'with open(path, encoding="utf-8") as fh: return json.load(fh)': True
CONTENT_HASH_KEYS HEAD ('facts','train_S','candidates','anchor_texts') | now same | HEAD dict key order same | CONTENT_HASH_BYTES key order same
  facts        HEAD canonical_bytes(read_jsonl(d / 'facts.jsonl'))            now 同   identical: True
  train_S      HEAD jsonl_bytes(read_jsonl(d / 'train_S.jsonl'))              now 同   identical: True
  candidates   HEAD canonical_bytes(JSONFILE(d / 'candidates.json'))          now 同   identical: True
  anchor_texts HEAD canonical_bytes([r['text'] for r in read_jsonl(d / 'anchor_text.jsonl')])  now 同  identical: True
  helper canonical_bytes / jsonl_bytes / read_jsonl / parse_jsonl / sha256_hex identical at HEAD and now: True ×5
RESULT: PASS
exit=0
```
与 Executor 一致：本轮重新生成的数据，与 reports/impl_c/c1_04_checks_r2b.txt 中的生成值和 verify 值完全相同。content_hashes 改为由 CONTENT_HASH_KEYS 与 CONTENT_HASH_BYTES 组装后，四个键的序列化表达式、键序和所用的辅助函数都与 HEAD 版本相同。leakage 的计数逻辑本轮没有改动，c1_data 的 8 个文件与此前审计时逐字节相同，所以 Gate 0 部分的 L1–L6、候选可行性与 split 结论沿用此前的审计，本轮未重算。

---

## 3. 静态核对
执行的命令：`bash audit/ic3_run_logged.sh audit/stdout/impl_c/ic3_03_static.txt python3 -I -B audit/ic3_03_static.py /home/user/OpenMythos <scratchpad>/c1_gate_probe_fixed.py`

原始输出（节选）：

**b. testgate 不读文件，TEST 行只用于求哈希，非对象 JSON 被拒：**
```
file reads (open / read_*): []
calls receiving `data`: {'begin_test_evaluation': ['rows_hashes_of(data)'], 'require_test_session': ['rows_hashes_of(data)'], 'rows_hashes_of': []}
the TEST rows only go to rows_hashes_of / rows_sha256 (hash of the canonical JSONL bytes): True
_committed refuses a committed JSON that is not an object: True | used by ['finish_test_evaluation', 'require_test_session', 'st10_check']
```

**c. test_data.main 的步骤顺序：**
```
statement index of each step: [('check_preconditions', 6), ('out.resolve() == root', 9), ('present = ', 10), ('TG.code_commit(root)', 12), ('refuse_if_st10_record', 13), ('generate_test(', 14), ('out.mkdir', 15), ('run_test_part', 17), ('leakage_test_report', 18), ('write_st10_record', 19)]
ST10-record search call: ['TG.refuse_if_st10_record(root, a.remote)']
--out test: ['root = fz.repo_root.resolve()'] | ["if out.resolve() == root or root in out.resolve().parents: raise ImplementationFail(...)"]
```
code_commit 与 ST10 记录的检查都在生成之前，第 1 轮的说明 (d) 已处理。

**d. ST10 记录与标记的内容：**
- ST10 记录的键为 kind/mode/label/frozen_commit/authorization/test_files_sha256/code_commit/counts；`counts = {c: report['checks'][c]['value'] ...}`，没有用到 'detail'。
- 标记的 14 个键都是名称、哈希、提交号、URL 或分支、session id 和时间，不含 TEST 内容。

**e. evaluate_model 中的顺序：**
```
[(329, 'verify_authorization'), (331, 'require_test_session'), (332, 'require_gpu'), (334, 'claim_checkpoint'), (336, "data['candidates.json']"), ...]
claim_checkpoint guarded by: ["split == 'test'"]
```

**f. 测试中是否接触真实 TEST：**
- test_testgate 的 TD.main 每次调用前，都已打桩 check_preconditions、generate_test、LK.load_data 和 LK.run_test_part，且 --inputs 为 'unused'。
- test_testgate.py 的 autouse fixture 把 pending 换成返回 []，但其中没有任何测试使用真实 inputs 或 generated fixture。
- test_test_data 中调用 check_preconditions 的测试不调用任何 TEST 路径。
- 改动过的测试中，提到 eval_sets 的行与 HEAD 相同；唯一新增的一行在 test_testgate 的文档字符串里。

**g. 历史搜索：**
```
_ever_committed git call: ["_git(root, 'log', '--full-history', *revs, '--format=%H', '--', rel)"] | --full-history given: True
remote_heads git calls: ["_git(root, 'ls-remote', '--heads', remote)", "_git(root, 'fetch', '-q', '--no-tags', remote, *[ref for _, ref in heads])"]
refuse_if_marker: revs = ['--all'] + remote_heads(root, remote)
refuse_if_st10_record: where = _where(root, ST10_RECORD_REL, ['--all'] + remote_heads(root, remote))
```

**h. begin 的顺序、预检与 BLOCKED 分类：**
- 顺序：refuse_if_marker(405) < verify_authorization(406) < st10_check(408) < 哈希格式(409) < 暂存检查(414) < _commit_preconditions(416) < code_commit(421) < 写标记(426) < commit_paths(427) < _LIVE 登记(431)。
- _commit_preconditions：检查 var GIT_COMMITTER_IDENT、ls-remote、是否为祖先、push --dry-run --no-follow-tags；拒绝全部为 _blocked。
- _push 使用 `push --no-follow-tags`，没有 force。
- refuse_if_marker 先判断有没有结果（有则 TestAlreadyEvaluated），再判断有没有标记（有则 BLOCKED）。

**i. B25 与 interpretations 闸门：**
- B25 没有 status，按定义视为待决，也是唯一待决的条目。
- verify_authorization 调用 pending_problem。generate_test、run_test_part、evaluate_model 和 begin_test_evaluation 都调用 verify_authorization。

**a–i 小结与 j：**
```
static checks a-i: PASS
== j. the probe against the round-2 testgate interface
  TestSession fields: ['session_id', 'marker_commit', 'marker_sha256', 'evaluated']
  staged probe: line 101 TG.refuse_if_marker(repo, 'origin', 'main') -> parameters ['repo_root', 'remote']: MISMATCH (3 positional for 2 parameters)
  staged probe: line 105 session.models -> TestSession field: MISSING
  staged probe mismatches: ["line 101: TG.refuse_if_marker(repo, 'origin', 'main')", 'line 105: session.models']
  corrected copy (...c1_gate_probe_fixed.py) mismatches: []
RESULT: FAIL
exit=1
```
与 Executor 一致：a 到 i 全部一致。不一致只有 j，即暂存的探针，与任务 1 的发现相同，也与 code-reviewer 第 2 轮的发现相同。

---

## 4. 以黑盒方式运行 TEST 生成器
执行的命令：`bash audit/ic3_run_logged.sh audit/stdout/impl_c/ic3_04_test_refusal.txt <venv>/python -I -B audit/ic3_04_test_refusal.py /home/user/OpenMythos <venv>/python <scratchpad>/inputs <scratchpad>/c1_data <scratchpad>/ic3_test_out_c1`

脚本内部实际运行的命令：`cd metrix/e1-pilot/src && <venv>/python -m metrix_e1.test_data --inputs … --data …/c1_data --out …/ic3_test_out_c1`

原始输出（节选）：
```
out_dir .../ic3_test_out_c1 exists: False
out_dir outside the repository /home/user/OpenMythos: True
----- generator stdout+stderr begin -----
TEST generator refused: metrix/e1-pilot/results/gate0_record.json is not committed at HEAD
no TEST content was generated, read or written
RESULT: FAIL
----- generator stdout+stderr end -----
exit code 1 | killed by the auditor False
out_dir ... exists: False
data dir unchanged (names, sizes, mtimes, sha256): True | test_qa.jsonl / general_test.jsonl in the data dir: []
inputs unchanged: True | src tree unchanged (incl. __pycache__): True | git status --porcelain --ignored --untracked-files=all -- metrix unchanged: True
results directory created: False
metrix/e1-pilot/results/st10_record.json in the working tree or in any commit: False
RESULT: PASS
exit=0
```
与 Executor 一致：拒绝理由与 c1_04_checks_r2b.txt 中的原文相同，且没有任何产物。

---

## 差异汇总（导致 BLOCK 的唯一一项）
- **位置**：metrix/e1-pilot/reports/impl_c/c1_gate_probe.py（暂存版，sha256 dfcd9c33…）。
- **问题**：
  - 第 101 行调用 `TG.refuse_if_marker(repo, "origin", "main")`，但本轮的签名是 `refuse_if_marker(repo_root, remote=None)`，因此 `marker` 操作总是 TypeError；
  - 第 105 行打印 `len(session.models)`，但本轮的 TestSession 已没有 models 字段，因此 `begin` 成功后探针输出 ERROR，而不是 ACCEPT。
- **影响**：
  - 两次运行中共 35 项输出无法按文档比对。
  - 被审的 src/ 行为不受影响：改用修正副本 c1_gate_probe_fixed.py（sha256 772b4dc3…）后，214 项全部一致。
- **修复**：
  - 按修正副本改这两处，入库时保留 `PILOT = Path(__file__).resolve().parents[2]`；
  - 在 Executor 的检查输出中至少运行一次探针；
  - 入库后，用 `ic3_01_gate_scenarios.py` 对已提交的探针重跑，不带第 4 个参数。

## 运行后的 `git status --short` 原始输出
```
A  metrix/e1-pilot/reports/IMPL_C_REPORT.md
A  metrix/e1-pilot/reports/impl_c/c1_00_session_start.txt
A  metrix/e1-pilot/reports/impl_c/c1_01_env_fetch.txt
A  metrix/e1-pilot/reports/impl_c/c1_02_checks.txt
A  metrix/e1-pilot/reports/impl_c/c1_03_checks_r2.txt
A  metrix/e1-pilot/reports/impl_c/c1_04_checks_r2b.txt
A  metrix/e1-pilot/reports/impl_c/c1_gate_probe.py
A  metrix/e1-pilot/reports/impl_c/c1_mutate.py
A  metrix/e1-pilot/reports/impl_c/c1_mutate_r2.py
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
```
- A 和 M 行是被审对象原有的暂存内容，未被改动：HEAD 仍为 eb05e422…，write-tree 仍为 dc4f28df…，工作区等于暂存区。
- 本次新增的只有 audit/ 下的文件。
- `git status --short --ignored` 对 src/、reports/、tests/ 没有列出任何 `!!` 项，说明没有写入 .pyc。
- 临时仓库都在会话临时目录（ic3_repos_staged、ic3_repos_corrected），在仓库之外。

结论：BLOCK
