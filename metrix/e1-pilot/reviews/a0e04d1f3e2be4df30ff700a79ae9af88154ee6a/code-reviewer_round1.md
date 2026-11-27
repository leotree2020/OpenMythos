# code-reviewer, C2 third fix commit, round 1: final report, unchanged (extracted by reports/round6/review_extract.py from code-reviewer_round1_transcript.jsonl)
# staged tree c7869d358c4adf6677d0f9843937bb6f3009b67b, parent 2665ab1036b66180ef1dee6b869135a45efefaa5; invocation text: code-reviewer_prompt.txt
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 2 段（C2）第三个修复提交，第 1 轮。暂存树 c7869d358c4adf6677d0f9843937bb6f3009b67b，父提交 2665ab1036b66180ef1dee6b869135a45efefaa5。仓库根目录 /home/user/OpenMythos，下文路径都相对于它。

**依据**
- scratchpad/review_c2d/ 下的 input_code.diff、input.diff（含 DEFERRED_MINORS 1.34）、tree.txt、notes.txt。
- 仓库代码：src/metrix_e1/pilot.py、testgate.py、test_data.py、_cli.py，run_pilot.py，tests/test_run_pilot.py。
- 协议 METRIX_E1_PROTOCOL.md 第 283、528、582、619–621 行。
- 上一轮两份原文：reviews/dd65a361…/code-reviewer_round1.md、data-auditor_round1.md。
- 录制：reports/impl_c/c2d_01_checks.txt、c2d_02_smoke.txt、c2d_smoke_records/step2_record.json。

**方法**：我只用了 Read、Grep、Glob，没有运行代码、git、pytest 或变异。「已验证」表示引用了仓库中的录制（写明行号）；其余判断来自读代码，标为「未验证」。

## 一、录制核对（已验证）

- **代码绑定**：tree.txt 中的 blob 与两份录制首尾一致。
  - pilot.py e7299974（tree.txt:1188）、test_run_pilot.py b90f57d8（:1218）、run_pilot.py 3ee2e0b4（:1173）、testgate.py 14a03a16（:1193）。
  - 对应 c2d_01:23、38、43、55 与 254、269、274、286；c2d_02:8、23、40 与 262、277、294。
- **首尾状态**：
  - 首尾都输出了 WORKTREE_EQUALS_INDEX（c2d_01:20、251；c2d_02:6、260）。
  - 代码 diff 的 sha256 都是 b0a72366…（c2d_01:21、252；c2d_02:7、261）。
  - 写树都是 da82a1e1（c2d_01:22、253；c2d_02:5、259）。
  - HEAD 等于远端，为 2665ab10…（c2d_01:4、7；c2d_02:4）。
- **pytest**：324 passed（c2d_01:142），比上一轮的 321 多 3 个，正好是 test_test_evaluate_begin_wiring 的 3 个参数。
- **变异**：43 个全部测出，变异前后 sha256 相同，RESULT: PASS（c2d_01:236-238）。
- **TEST 生成器**：拒绝，--out 未创建，没有 results 目录（c2d_01:99-104、113）。
- **冒烟**：
  - 30 次训练，每次 3 步；NOT_TESTED；生成器 exit 1，--out 未创建；RESULT: PASS（c2d_02:103、126-128）。
  - step2_record.json:112-115 的计数为 base_loads 32、checkpoint_reloads 18、test_file_hashes 15。
- **脚本 sha256（未验证）**：录制中记有两个脚本的 sha256（c2d_01:63-64、294-295）。我无法计算 sha256，所以它们与暂存 blob 77bab3ea、b13909d4（tree.txt:562、711）的对应没有核对。

## 二、上一轮各项核对

1. **MAJOR 1 / CH1：已修且正确（结果分支）；标记分支逻辑正确，但没有测试能单独测出它（见问题 1）。**
   - 代码（未验证）：refuse_if_test_evaluated（pilot.py:1252-1263）只读工作区与 HEAD。
     - 有结果时抛 TestAlreadyEvaluated，由 1297-1299 原样抛出，不写记录。
     - 有标记无结果时抛 ProtocolStop(None, "BLOCKED")。1171 已重置标志，所以 1288 的 begun 为 False，1289-1291 返回，不写记录。
   - 测试（已验证）：e2e 最后一次运行把 before_run 换成抛 ST7 的函数（tests:425-430），断言 TestAlreadyEvaluated 且远端不变。去掉该调用的变异已测出（c2d_01:193-194）。
2. **MAJOR 2 / CH2：已修且正确。**
   - 新顺序（pilot.py:1171-1177）：重置标志 → code_commit → start_checks → refuse_if_test_evaluated → check_preconditions → device_check。
   - start_checks 之前只有 `if not p.mode.formal` 与 code_commit 两处会抛出，都是 ImplementationFail、没有停止码，走 1300-1303 的路径，不写记录（未验证）。
   - wrong_work 测试（tests:797-801）存在；把 start_checks 移到 check_preconditions 之后的变异由它测出（c2d_01:195-196，已验证）。
3. **MAJOR 3 / CH3：已修且正确。**
   - crash_after_begin（tests:764-787）运行真实的 test_evaluate。
     - E.evaluate_model 经 Pilot.evaluate 按模块属性调用（pilot.py:487-489），所以替换有效。
     - 第 2 次 TEST 评测在标记之后崩溃。断言：远端有标记、没有结果；恰有一份 test-evaluate 记录，Status 为 BLOCKED，test_begun 为 True，带崩溃消息；异常原样抛出。
   - refused_inside_begin（788-796）：注入点 check_commit_preconditions(…, "the TEST marker") 在 testgate.py:449，早于 460 行写标记。断言 begin_called 为 True、marker_before_begin 为 False、不写记录、远端不变。
   - 三个变异都由 crash_after_begin 测出（c2d_01:187-192，已验证）。
   - 「不重置标志」的变异是因为预期的原因被测出的：再运行时沿用旧值 True/False，begun 为 True，于是写记录并推送（推理，未验证）。

**MINOR 各项**
- CH4：已修且正确。
  - 15 次文件哈希在 1189-1196，早于 1204 的 before_run；GPU 时钟由 before_run → first_load 打开（402-417）。
  - 测试 tests:357-358；两个变异已测出（c2d_01:201-202、207-208，已验证）。
- CH5：第 3 步已加 hash_s（657 行）；S 的 s_mapping 登记，同意。没有测试（见问题 4）。
- CH6：交 Review Gate，同意。
- CH7：已修（1171 行）；变异已测出（c2d_01:191-192，已验证）。
- CH8：已修。
  - 739 行断言了 code_commit；745-752 行覆盖「没有 ledger 时拒绝、子进程未启动」。
  - 两个变异已测出（c2d_01:197-200，已验证）。
- CH9：已修。
  - _formal_on_clone 的 docstring（650-653）与函数体相符：不替换 G.judge 与 train_run，fake_eval 不处理 with_em / with_s_mapping（未验证）。
  - records 测试的 docstring 已更新（503-507）；训练步数改读 total_steps（278）；提交链改用 search_runs（621）。
- CH10：已修。
  - 「begun read from the marker file alone」现在只指名 RECORDS，并已测出（c2d_01:185-186）。
  - STATE 记录了两个脚本的 sha256（c2d_01:63-64）。
- CH11：未修（按计划放到报告提交）。见问题 7。
- CH12：代码（177-187）与测试（349-355）已修；模块 docstring 中的公式未同步（见问题 3）。

## 三、重点问题结论

**refuse_if_test_evaluated 与 refuse_if_marker 的关系（未验证）**
- 前者只会增加拒绝，不会放行任何东西。begin 中的完整检查（fetch、对 tip 判定）未改动（testgate.py:391-405、440）。ST10 闸门也未改动（443、496）。
- 防范对象内没有新的「评两次」或「ST10 不成立时评测」路径。
- 不会误拒正常的第一次评测：标记只由 begin 写入（457-460），结果只由 finish 写入（530-532），第一次 begin 之前两者都不存在。
- 判定口径与 refuse_if_marker 相同：先看结果、再看标记、含工作区。唯一差别是用 HEAD 而不是 fetch 后的 tip（见问题 5）。

**新顺序下各种拒绝与停止是否写记录（未验证）**
- 不写记录：
  - 非 formal、code_commit 失败：ImplementationFail，原样抛出。
  - start_checks：没有停止码的 BLOCKED。
  - 已评：TestAlreadyEvaluated，原样抛出。
  - 有标记无结果：没有停止码的 BLOCKED。
  - PreconditionFailed；try 块中的记录或文件缺失；checkpoint 不符；N 的哈希不符。
  - begin 中写标记之前、没有停止码的拒绝。
- 写记录：
  - check_preconditions 的 ST12、device_check 的 ST8、before_run 的 ST7 / ST9 / ST8、begin 中的 ST10。
  - begin 之后的任何停止、崩溃或中断。
- 与 run_test_evaluate 的 docstring 一致。

**测试替换的范围**
- eval_clone 替换了 before_run、base_model、device_check 与 E.require_gpu。所以 test-evaluate 的测试从不走真实的 ST7 / ST8 / ST9 路径，ST7 只在 e2e 中注入过。
- refuse_if_test_evaluated 相对于 device_check / check_preconditions 的先后，只由 wrong_work 的变异与 e2e 的 ST7 保护（见问题 1）。

## 四、问题

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1261-1263；tests/test_run_pilot.py:340、783-786；reports/impl_c/c2_mutate_fix3.py:103-105 | 【未验证（推理，未运行变异）】refuse_if_test_evaluated 的「有标记无结果」分支没有任何测试能单独测出。crash_after_begin 再运行时，before_run 是 eval_clone 的空函数；删去这一分支后，运行会一直走到 begin，由 refuse_if_marker 拒绝（marker_before_begin 为 True，所以 begun 为 False），结果同样是 (False, "BLOCKED")、不写记录，测试仍通过；这一分支也没有对应的变异。所以说明中「有标记无结果时，在任何带停止码的检查之前拒绝」这一点没有被检验。同类缺口：e2e 的 ST7 注入只覆盖工作区与 HEAD 都有结果的情形；device_check 被替换，若把 refuse_if_test_evaluated 移到 device_check 之后也测不出。属防范对象之外（不涉及评两次） | `p.before_run = lambda next_seconds=0.0: None`（eval_clone）；`assert P.run_test_evaluate(p) == (False, "BLOCKED")     # the same Pilot again: begun earlier, not now` | 在 crash_after_begin 再运行之前，把 p.before_run 换成抛 ST7 的函数（与 e2e 相同），断言 (False, "BLOCKED") 且远端 tip 不变；加一个变异 `if present(TG.MARKER_REL):` → `if False:`，指名 crash_after_begin；登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1266-1269；tests/test_run_pilot.py:788-801 | 【未验证（推理）】begun_by_this_process 的第三个条件（标记现在存在）只有 refused_inside_begin 能测出：RECORDS 中无标记的情形把 begin_called 置为 False，e2e 与 crash_after_begin 在条件成立或 begin_called 为 False 时运行。但 c2_mutate_fix3.py 中没有删去这一条件的变异，这项测试的检出能力没有录制证据 | `return p.begin_called and not p.marker_before_begin and (p.root / TG.MARKER_REL).exists()` | 下次录制时加一个变异（删去 `and (p.root / TG.MARKER_REL).exists()`），指名 refused_inside_begin；或登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1157-1167 | 【已核对仓库文件】test_evaluate 的 docstring 没有随新顺序更新：仍写先做 generator 的前提检查，再在「before the marker is written: the continuity checks, …」中列出连续性检查；也没有提到 refuse_if_test_evaluated 与开头的标志重置 | "the generator's preconditions again (…) give the TestAuthorization; before the marker is written: the continuity checks, the checkpoint files…" | 按实际顺序改写：重置标志 → code_commit → start_checks → 只读的已评检查 → 前提检查 → ST8 → …

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:54-59 | 【已核对仓库文件】模块 docstring 中的 CHECKPOINT_OVERHEAD 公式没有随 CH12 更新：仍写 "loads x load"，也没有 185-187 新增的 "checkpoint_reloads x reload_s" 项；括号中的说明却已列出 G0.8 与 TEST 的重载，公式与说明不一致。另有 "and the sum; whether ST11\nshould read" 的断行残留 | `CHECKPOINT_OVERHEAD = loads x load + runs x (2 hashes + save + reload + file hash) + TEST state hashes x hash + TEST checkpoint files x file hash` | 改为 base loads x load + runs x (…) + further reloads x reload + TEST state hashes x hash + TEST checkpoint files x file hash

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:657 | 【已核对 tests：没有任何测试读取第 3 步的 look-ahead 值】CH5 在第 3 步加上的 hash_s 没有测试或变异，删去也不会使任何测试失败。另外 `(p.pre["hash_s"] if p.pre else 0.0)` 与 eval_seconds 内部对「预检之前」的处理重复 | `p.before_run(p.eval_seconds("load") + (p.pre["hash_s"] if p.pre else 0.0))     # N is also hashed` | 在提交链测试中断言 looks 含 eval_seconds("load") + pre["hash_s"]；或给 eval_seconds 加一个是否计哈希的参数；或登记

MINOR | metrix/e1-pilot/src/metrix_e1/pilot.py:1252-1263（对照 testgate.py:391-405；pilot.py:1066-1074） | 【未验证】(1) 「有结果 → TestAlreadyEvaluated；有标记无结果 → BLOCKED」的判定现在分写在两个模块中，消息不同、参照点也不同（HEAD 对比 fetch 后的 tip），以后改其中一处容易与另一处不一致。(2) 不 fetch 的后果：检出的仓库落后于远端时，预检通过，begin 之前仍可能遇到 ST7 / ST8 / ST9 并写记录；之后 final_record 的 precommit 在 check_checkout 处因 HEAD ≠ tip 失败，记录只留在工作区，原来的停止不被掩盖。属防范对象之外，也与 2026-11-27 裁决第 1 项（只在 begin 与 finish 时 fetch）一致 | `return (p.root / rel).exists() or TG._blob(p.root, "HEAD:%s" % rel) is not None`；refuse_if_marker 中的 `tip = check_checkout(root)` | 考虑在 testgate 中提供一个接受参照提交的版本（例如复用 _where(root, rel, "HEAD")），供两处共用；在报告中登记检出落后于远端的情形

MINOR | metrix/e1-pilot/reports/impl_c/c2d_01_checks.txt:1；c2d_02_smoke.txt:1；reports/impl_c/c2d_checks.sh:9 | 【已验证：c2d_01:4、7 与 c2d_02:4 给出 2665ab1036b66180ef1dee6b869135a45efefaa5】录制首行与脚本中写的父提交 "2665ab17" 有误（Executor 已承认），录制首行描述与其 STATE 不一致 | `(staged; parent 2665ab17, the evidence commit after the second fix commit dd65a361)` | 不改录制文件；在 DEFERRED_MINORS 或 IMPL_C_REPORT 中登记更正

MINOR | metrix/e1-pilot/reports/IMPL_C_REPORT.md（只有到 60 行 "## C1" 为止的节）；src/metrix_e1/pilot.py:194 | 【已核对仓库文件】CH11 仍未完成：没有 C2 节，也没有 2026-11-27 的裁决；本次 docstring 指向 "reports/IMPL_C_REPORT.md C2"，该节尚不存在。另外，本次新增了一类不写实验记录的拒绝（TEST 已开始或已评之后再运行，在任何带停止码的检查之前拒绝）。协议 582 行要求「每次运行（含被停止的）提交一份」，这类拒绝算不算一次运行，与待决第 1 项是同一个问题 | `No margin is added (for Review Gate, reports/IMPL_C_REPORT.md C2)` | 在报告提交中写入 C2 节、2026-11-27 裁决，并在待决第 1 项中列出这一路径与 CH6

结论：PASS
