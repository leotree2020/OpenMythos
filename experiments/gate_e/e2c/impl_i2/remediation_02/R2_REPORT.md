# E2-c I2-R2 限定修复：发布后越过上限的最终状态与子进程启动方式

- **日期**：2026-10-21
- **审核对象**：`f1f1b0b7c7ace3243e3d11b0456e995f6d9ab943`（I2-R1）
- **授权**：I2-R2 限定修复，只修复模拟实现及测试。不授权真实的阶段 2 verify、freeze，也不授权阶段 3、4。
- **结论**：
  - 阶段 2 合成测试 51/51 通过：原 45 项，新增 6 项；`verify_budget_inside_publish_window` 按裁决改写。只正式运行一次。
  - 另做 1 项补充开发检查：驱动在发布之后、账本关闭之前被 SIGKILL。结果通过，不属于正式套件。
  - V4 没有重跑：`run_e2c.py` 和 `e2c_launcher_tests.py` 与 f1f1b0b 逐字节相同，I2-R1 的 52/52 仍然有效。
- **本轮范围**：
  - 只用模拟数据、桩作业和临时目录；
  - 没有枚举真实键空间，没有运行 33 个种子的正式 V2，没有生成盐值或 test2，没有创建正式冻结文件，没有进入阶段 3、4；
  - I2 的 50/50、36/36 记录和 I2-R1 的 52/52、45/45 记录都没有被覆盖或修改；
  - 预注册、E1、阶段 1 文件、λ 和 λ₂ 都没有改动（见 `untouched_proof.txt`）。

## 1. 问题与修复

| 来源 | 问题 | 修复 |
|---|---|---|
| 审核 BLOCKER | 上限在最后一次检查之后、发布窗口之内被越过时，verify 仍返回 PASS（I2-R1 正式记录：越过 10.84 秒，退出码 0） | 最终状态改在账本区间关闭时决定（`Ledger.close()`）：<br>· 原为 PASS、但关闭时累计用量 ≥ 上限的，改为 `BUDGET_CAP_REVIEW_REQUIRED`，退出码 7；<br>· 已发布的文件保持原样，不修改、不重写；<br>· 写一份不可覆盖的审核记录，绑定已发布文件的 sha256（第 2 节） |
| 审核 | 发布之后、账本关闭之前越过上限，也不得报告 PASS | 同上：关闭时判定，覆盖发布窗口内和发布后两个位置。verify 和 freeze 同样处理 |
| 审核 | freeze 准入只核对 verify 记录本身 | 新增 `budget_admission()`：核对批准提交中的账本、未解决的审核或停止记录，以及它们在 git 历史中是否出现过；有审核待决时拒绝（第 2.3 节） |
| 审核 | `--resume` 可能绕过审核 | 任一审核记录存在时，verify（包括 `--resume`）一律拒绝；删除记录也绕不过 freeze 的历史检查（第 2.4 节） |
| 审核任务 2 | 驱动有心跳、看门狗两个线程，却用 `subprocess.Popen(preexec_fn=...)` 设置 `PR_SET_PDEATHSIG` | 删除 `preexec_fn`，改为 exec 包装器：在新的单线程解释器中设置 `PR_SET_PDEATHSIG`，核对父进程后 `execv` 真正的命令（第 3 节） |
| 自查 | 作业首进程正常退出后，留在同一进程组内的子孙进程会继续运行，而且不计入账本 | 作业或 V2 工作进程正常退出后，`end_group()` 向整个进程组发 SIGKILL |

修改范围（相对 f1f1b0b）：
- `e2c_stage2.py`：+178 / −49 行；
- `e2c_stage2_tests.py`：+176 / −19 行，新增 7 个测试函数和 1 个辅助函数，改写 1 个既有测试（见第 4 节），`verify_pass` 增加断言；
- `run_e2c.py`、`e2c_launcher_tests.py`：没有改动。

完整差异见 `code_diff_vs_f1f1b0b.patch`。

## 2. 任务 1：F9 的最终状态

### 2.1 判定规则

一次 verify 或 freeze 启动的最终状态，在它的账本区间关闭时决定，依据是关闭时刻的累计用量（`e2c_stage2.py` 中的 `Ledger.close`）：

| 越过上限的时刻 | 已发布的文件 | 最终状态 | 退出码 |
|---|---|---|---|
| 没有越过（关闭时累计用量 < 上限） | 正常发布 | PASS（不变） | 0 |
| 最后一次检查之前（看门狗、作业轮询、显式检查） | 没有发布，临时文件被丢弃 | BUDGET_CAP（不变） | 7 |
| 最后一次检查之后、发布窗口之内 | 按最后一次检查的决定发布，保持原样 | **BUDGET_CAP_REVIEW_REQUIRED** | 7 |
| 发布之后、账本关闭之前（清理、写停止标记等） | 保持原样 | **BUDGET_CAP_REVIEW_REQUIRED** | 7 |

- **发布窗口内越过**：窗口结束时立即比较一次（`over >= 0`）。
- **发布后越过**：`Ledger.close()` 发现 PASS 的启动在关闭时已达到上限，就把区间状态改为 `BUDGET_CAP_REVIEW_REQUIRED`，并记下 `status_before_close: "PASS"`。
- **关闭之后**：只写审核记录、`summary.json` 和日志，耗时为毫秒级，不计入账本。这些步骤只记录已经决定的状态，不能把任何状态改成 PASS。
- **已发布文件的内容**：
  - `stage2_verify.json` 内部的 `status` 字段仍然是 `"PASS"`，这是最后一次检查时决定并已发布的内容，按要求不重写。
  - 权威的最终状态以账本区间、`summary.json` 和审核记录为准。freeze 准入正是按账本判定的（第 2.3 节）。
- **每个区间记录**：`cap_seconds`、`used_seconds_at_end`，以及 `published`（本次启动发布的文件名及其 sha256）。`published` 只在区间关闭时写入。

### 2.2 审核记录

审核记录只写一次，写在 `stage2/` 下：verify 写 `budget_review_required.json`，freeze 写 `budget_review_required_freeze.json`。字段如下：

- `status`：`BUDGET_CAP_REVIEW_REQUIRED`；
- `command`：verify 或 freeze；
- `where`：越过的位置，为 "inside the publish window, after the last budget check" 或 "after the publication, before the ledger closed"；
- `crossed_by_seconds`、`cap_seconds`、`used_seconds_at_end`；
- `interval`；verify 另记 `attempt`；
- 绑定的 sha256：
  - verify：`verify_record_sha256` 和 `v2_streams_sha256`；
  - freeze：`freeze_sha256`、`receipt_sha256` 和 `verify_record_sha256`；
- `written_utc`；
- `resolution`："only by the review: verify (also with --resume) and freeze refuse while this record exists or existed in the history; the published files are never rewritten"。

### 2.3 freeze 准入（`budget_admission`）

freeze 先核对 verify 记录（B1 的 `git_anchor`），再依次核对以下几项，任一不符就拒绝（退出码 5）：

1. 工作区中存在 `budget_review_required.json`、`budget_review_required_freeze.json` 或 `verify_stop.json`。
2. 上述任一文件出现在 `git log HEAD` 的历史中：删除记录并不能解决审核。
3. 批准的 verify 提交中没有 `stage2/budget_ledger_s2.json`（读取方式为 `git show <commit>:…`，不读工作区副本）。
4. 已提交的账本中：
   - 发布了该 verify 记录（`published.stage2_verify.json` 等于批准的 sha256）的区间必须恰好一个；
   - 该区间的状态必须是 PASS，且 `used_seconds_at_end < cap_seconds`。
5. 已提交的账本中有任何区间处于 `BUDGET_CAP_REVIEW_REQUIRED`。
6. 工作区账本不是已提交账本的延续：已有区间必须逐项相同，唯一允许的差别是给当时未关闭的区间加上 `stale` 键（遗留区间规则）。

freeze 自身也遵循第 2.1 节的规则：
- 冻结文件和回执在发布窗口内或发布之后越过上限时，两者都保持原样，退出码 7，并写 `budget_review_required_freeze.json`；
- PASS 的 JSON（`freeze_sha256`）只在退出码为 0 时输出；
- 冻结文件只写一次，所以不能再次冻结，只能由审核决定。

### 2.4 续跑与只读检查

- **verify**（`verify_state_problem`）：只要任一审核记录存在，就拒绝。这一检查在授权检查、环境检查和打开账本之后，排在 verify 自己的其他检查之前，提示 "a budget review is pending; only the review resolves it (no resume)"，不论是否带 `--resume`。
- **审核记录被删除之后**：
  - verify 仍被"记录只写一次"拒绝（verify 记录已存在）；
  - freeze 仍被第 2.3 节第 2、4、5 项拒绝。
- **`check` 命令**：
  - 报告 `review_pending`，即存在的审核或停止记录，以及处于 REVIEW 的区间；
  - 报告累计用量和每个区间的状态；
  - 有待决审核时退出码为 3。

### 2.5 正式运行中的实际记录

**(a) 发布窗口内越过**（`verify_budget_inside_publish_window`）：测试钩子把窗口拉长到 41 秒，上限 40 秒。

```
review record budget_review_required.json:
  attempt "01", cap_seconds 40.0, command "verify", crossed_by_seconds 10.076606, interval 1,
  status BUDGET_CAP_REVIEW_REQUIRED, used_seconds_at_end 50.077123,
  verify_record_sha256 f83c2a9b5647eac20ceafdd848d479aee59ecd4bd89602850a619bab3e5cac94,
  v2_streams_sha256 ac9baffa23bec70bf1f40ea17b2edee7f989d4b0f303b375be2cb6fb8309a304,
  where "inside the publish window, after the last budget check", written_utc 2026-10-21T05:00:33Z
ledger interval 1: status BUDGET_CAP_REVIEW_REQUIRED, used_seconds_at_end 50.077123, published {both sha256 above}
summary.json: status BUDGET_CAP_REVIEW_REQUIRED, exit 7, publish_window_seconds 41.000811,
  signal_inside_publish_window "BudgetExceeded arrived inside the publish window after the outputs were decided; deferred"
stderr:
  BUDGET_CAP_REVIEW_REQUIRED: the cap was crossed inside the publish window, after the last budget check by 10.076606 s;
  the published files stay as written; freeze refuses until the review resolves budget_review_required.json
  final status BUDGET_CAP_REVIEW_REQUIRED (exit 7)
```

**(b) 发布之后、账本关闭之前越过**（`verify_budget_after_publish_before_close`）：测试钩子在关闭前停 41 秒，上限 40 秒。

```
review record: crossed_by_seconds 9.954634, used_seconds_at_end 49.954634, cap_seconds 40.0,
  verify_record_sha256 0a6de0b8dda10df9edce3471f8b3c7794e6d97fbe661adae27582354a7c15c6e,
  where "after the publication, before the ledger closed"
ledger interval 1: status_before_close PASS -> status BUDGET_CAP_REVIEW_REQUIRED, published {both sha256}
summary.json: status BUDGET_CAP_REVIEW_REQUIRED, exit 7, publish_window_seconds 0.000708
stderr: published ... last budget check to both published: 0.71 ms; budget used 8.954 s of 40 s
        BUDGET_CAP_REVIEW_REQUIRED: the cap was crossed after the publication, before the ledger closed by 9.954634 s; ...
        final status BUDGET_CAP_REVIEW_REQUIRED (exit 7)
```

**(c) freeze 在发布之后越过**（`freeze_budget_after_publish`）：上限设为"verify 用量 + 15 秒" = 24.57 秒，关闭前停 20 秒。

```
review record budget_review_required_freeze.json: command "freeze", interval 2, cap_seconds 24.57,
  used_seconds_at_end 33.564727, crossed_by_seconds 8.994727,
  freeze_sha256 9b5393fe2626b8b92c801aaf59c070c04976d6ba864302956cbf0db2c3cacf46,
  receipt_sha256 05bc741e90682cf9df819c0addfe85ba3265d6605a01e7b401b02f87b8f52879,
  verify_record_sha256 03ba69ccf106dc4654fb3b438fe88bd816ff77e87b8075253805fc9ce6271120
ledger interval 2: status_before_close PASS -> BUDGET_CAP_REVIEW_REQUIRED; published {freeze, receipt}
stdout: no freeze_sha256 (printed only on exit 0)
```

**(d) 冻结与续跑被拒绝**（`review_blocks_freeze_and_resume`）：verify 退出码 7，审核记录和账本随 verify 记录一起提交，作为模拟的审核批准。之后依次尝试：

| 尝试 | 退出码 | 拒绝原因（原文） |
|---|---|---|
| freeze | 5 | REFUSED: the stage-2 budget does not admit a freeze: budget_review_required.json exists (unresolved); budget_review_required.json is in the history (only the review resolves it); the launch that published the record ended as BUDGET_CAP_REVIEW_REQUIRED at 50.417418 s of 40.0 s; a launch in the committed ledger is BUDGET_CAP_REVIEW_REQUIRED |
| verify --resume | 5 | REFUSED: budget_review_required.json exists: a budget review is pending; only the review resolves it (no resume) |
| 删除工作区中的审核记录后 freeze | 5 | …: budget_review_required.json is in the history (only the review resolves it); the launch that published the record ended as BUDGET_CAP_REVIEW_REQUIRED …; a launch in the committed ledger is BUDGET_CAP_REVIEW_REQUIRED |
| 删除后 verify --resume | 5 | REFUSED: verify is complete; stage2_verify.json is written once |
| 提交删除后 freeze（`--expected-commit` 为新 HEAD） | 5 | 同上：仍在历史中，已提交账本中仍为 REVIEW |
| 把工作区账本改成 PASS、用量 1 秒后 freeze | 5 | 同上，另加：interval 1 of the working-tree ledger differs from the committed one |

六次尝试都没有写出冻结文件。完整原文见 `stage2_tests_r2.json` 中该测试的 `evidence.refusals`。

**(e) 补充开发检查**（`dev/supplement_kill_after_publish.*`）：在 05:09:25Z 运行，使用最终代码，不属于正式套件。两个 verify 文件都发布后、账本关闭前，驱动被 SIGKILL：

- 驱动退出码 −9；
- 区间 1 未关闭（`end` 为 null），没有 `published`；
- 没有 `summary.json`，也没有审核记录：进程已死，什么都没有报告，更没有 PASS；
- 即使提交了这时的状态：
  - freeze 退出码 5（遗留区间，不接受补计）；
  - 接受补计后 freeze 退出码 5（"the committed ledger does not name exactly one launch that published the approved record"）；
  - `verify --resume --accept-stale-supplement` 退出码 5（记录只写一次）；
- 没有冻结文件，没有遗留进程。

## 3. 任务 2：`preexec_fn` 的风险与修复

### 3.1 风险

- **I2-R1 的做法**：用 `preexec_fn` 在 fork 之后、exec 之前调用 `prctl(PR_SET_PDEATHSIG, SIGKILL)`。
- **为什么不安全**：驱动除主线程外还有心跳线程和看门狗线程。
  - fork 之后，子进程里只剩调用 fork 的那个线程。其他线程在 fork 那一刻持有的锁（例如账本的 `threading.Lock`、malloc 的内部锁、I/O 缓冲区锁、导入锁）在子进程中永远不会释放。
  - `preexec_fn` 是 Python 代码，如果碰到这类锁，子进程会在 exec 之前死锁。
  - Python 文档明确说明 `preexec_fn` 在有线程时不安全。本环境的 Python 3.13.16 对此不发出警告，但这不能作为安全的证据。
- **后果**：
  - 驱动的等待循环仍在检查预算，所以驱动本身不会永久挂起；
  - 但会白白耗掉预算，最后以超时（退出码 4）或预算超限（退出码 7）结束；V2 工作进程同理。
- **观察**：I2-R1 的运行中没有观察到这种情况，但没有观察到不等于不会发生，所以选择修复，而不是论证。

### 3.2 修复

```python
EXEC_WRAPPER = ("import ctypes, os, signal, sys\n"
                "if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL) != 0: os._exit(71)\n"
                "if os.getppid() != int(sys.argv[1]): os._exit(70)\n"
                "os.execv(sys.argv[2], sys.argv[2:])\n")
def child_argv(argv):
    return [sys.executable, "-I", "-c", EXEC_WRAPPER, str(os.getpid()), *argv]
```

- **驱动一侧**：两个作业（附录 A、键空间）和 V2 工作进程都通过 `Popen(child_argv(argv), start_new_session=True)` 启动，不带 `preexec_fn`。驱动 fork 出的子进程里不再执行任何 Python 代码：建新会话、重定向和 exec 都在 CPython 的 C 代码中完成。
- **包装器一侧**：包装器是一个新的单线程解释器，`-I` 隔离模式下不读用户 site 目录和 `PYTHON*` 环境变量。它依次：
  1. 调用 `prctl(PR_SET_PDEATHSIG, SIGKILL)`，失败时退出 71；
  2. 核对 `getppid()`：如果驱动在 fork 和 prctl 之间已经死去，父进程已经变成别的进程，于是退出 70，不执行作业；
  3. 用 `execv` 执行真正的命令，参数和环境不变。
- **PDEATHSIG 的保持与归属**：
  - `PR_SET_PDEATHSIG` 在 `execve` 之后仍然有效（set-user-ID、set-group-ID 或带文件能力的程序除外，python 不属于这些）。
  - 它跟随的是"创建子进程的那个线程"。所有 `Popen` 调用都在主线程（`run_bounded` 和 `run_v2` 都由 `cmd_verify` 调用），主线程存活到进程退出；心跳和看门狗线程从不启动进程。
- **退出码 70、71**：驱动把它们当作运行错误（退出码 4）：作业由 `run_bounded` 处理，V2 工作进程由 `run_v2` 处理。
- **作业正常退出后**：`end_group()` 向它的进程组发 SIGKILL，留在组里的子孙进程不能继续运行。
- **代价**：每次启动多一次解释器启动，本机实测约 15 毫秒。一次 verify 只启动 2 个作业和 `workers` 个 V2 工作进程。

### 3.3 各种情形

`PR_SET_PDEATHSIG` 只作用于直接子进程（包装器 exec 之后的作业首进程或 V2 工作进程），**不保证子孙进程终止**。

| 情形 | 直接子进程 | 同一进程组内的子孙进程 | 自行脱离进程组的子孙进程 | 证据 |
|---|---|---|---|---|
| 作业正常结束（退出码 0） | 等到它退出 | `end_group()` 发 SIGKILL | 不覆盖 | `job_leaves_descendant` ok：verify 0，遗留子孙已终止，无遗留进程 |
| 作业以错误结束（非 0） | 同上；verify 退出码 4 | 同上 | 不覆盖 | `job_leaves_descendant` fail：verify 4，同上 |
| 驱动收到 SIGTERM 或 SIGINT | `kill_group()`：SIGTERM，最多等 5 秒，再 SIGKILL，最后对整个组再发一次 SIGKILL | 同组成员一并终止 | 不覆盖 | `sigterm_during_job`（附录 A、键空间）、`interrupt_and_resume`（V2）：130，作业及其子进程都已终止 |
| 达到预算上限 | 同上（`BudgetExceeded`） | 同上 | 不覆盖 | `appendix_job_budget_cap`、`keyspace_job_budget_cap`：7，作业及其子进程都已终止 |
| 驱动被 SIGKILL | 内核按 PDEATHSIG 发 SIGKILL | **不覆盖**：被 init 或 subreaper 收养后继续运行，所用时间不计入账本 | 不覆盖 | `sigkill_driver`：作业随驱动终止；桩作业自己的子进程仍然存活，由测试清理 |
| fork 之后、prctl 之前驱动已死 | 包装器退出 70，不执行作业 | — | — | `wrapper_parent_check`：父进程不对时退出 70，作业没有运行；父进程正确时退出 0 |
| prctl 失败 | 包装器退出 71，不执行作业 | — | — | 没有测试：无法在本环境中让 prctl 失败 |
| 驱动有线程时连续、并发启动 | 不挂起 | — | — | `spawn_stress`：心跳周期 0.01 秒，看门狗开启；200 次 `run_bounded` 加 25 批每批 4 个并发，共 300 次启动，用时 21.81 秒，单次最长 0.105 秒 |

真实路径中不存在子孙进程：
- 静态检查（`static_checks.txt`）显示，`e2c_stage4.py`、`e2c_test2.py`、`e2c_common.py`、`e_common.py`、`e_task.py`、`levels.py`、`data.py`、附录 A 脚本和 V2 工作进程路径中，进程调用次数都是 0；
- 所以"驱动被 SIGKILL 后子孙存活"只出现在测试桩中。

驱动自身的 git 调用（`subprocess.run(["git", …])`）不经过包装器。它们是本地只读命令，毫秒级完成，不属于实验计算，看门狗同样覆盖这段时间。

## 4. 任务 3：测试矩阵与正式结果

| 审核要求 | 测试 | 正式结果 |
|---|---|---|
| 未越过上限 → PASS | `verify_pass`（新增断言：summary 和区间都是 PASS，`published` 绑定记录的 sha256，`used < cap`，没有审核记录） | 退出码 0；发布窗口 0.000359 秒 |
|  | `freeze_pass_launcher_accepts` | check 0，stage3 0，stage4 0 |
| 最后一次检查之后越过 → 文件保留、状态非 PASS | `verify_budget_inside_publish_window`（改写：I2-R1 期望退出码 0，现在期望 7） | 退出码 7；两个文件都保留（f83c2a9b5647），文件内容未重写；越过 10.076606 秒 |
| 审核记录阻止 freeze | `review_blocks_freeze_and_resume` | freeze 退出码 5 |
| resume 或修改 sidecar 不能绕过审核 | 同上 | resume、删除记录、删除后 resume、提交删除、改写账本：都是 (5, True)；没有冻结文件 |
| 发布后、账本关闭前越过 → 不静默 PASS | `verify_budget_after_publish_before_close` | 退出码 7；区间 PASS → REVIEW，49.955 秒，上限 40 秒 |
|  | `freeze_budget_after_publish` | 退出码 7；冻结文件保留（9b5393fe2626）；stdout 没有 PASS 的 JSON |
|  | 补充开发检查：发布后 SIGKILL | 驱动 −9；没有 PASS；freeze 和 resume 都是 5 |
| 子进程启动与异常退出：无死锁，无未记录的运行 | `spawn_stress`、`wrapper_parent_check`、`job_leaves_descendant` | 见第 3.3 节 |
|  | `sigkill_driver`、`sigterm_during_job`、`appendix_job_budget_cap`、`keyspace_job_budget_cap` | 原有测试，全部通过（见第 3.3 节） |

### 4.1 运行次数

| 运行 | 结果 | 代码 | 记录 |
|---|---|---|---|
| 开发 1（14 项：新增和受影响的测试） | 14/14；04:37:09–04:45:27 UTC | 驱动为最终版；测试文件 `990f9aca…` 还没有把证据写入结果文件，测试逻辑与最终版相同 | `dev/stage2_tests_r2_dev1.*` |
| 开发 2（2 项） | 2/2 | 最终版（测试文件增加证据记录、加宽 stderr 摘录） | `dev/stage2_tests_r2_dev2.*` |
| **阶段 2 正式** | **51/51**，共 121 次调用；04:47:50–05:04:13 UTC | 最终版 | `stage2_tests_r2.json`、`formal_runs_console.txt` |
| 补充开发检查（1 项） | 通过；05:09:25 UTC | 最终版 | `dev/supplement_kill_after_publish.*` |

- 正式运行所用代码的 sha256 见 `static_checks.txt`，与本提交中的代码相同。
- 开发运行中没有失败。修改过程中有两次编辑错误：一次缩进错误；一次替换误删了 `freeze_budget_before_write` 和 `sigterm_during_job`。两者都在运行之前发现，那两个函数从 f1f1b0b 原样恢复，与 f1f1b0b 逐字节相同。
- 静态检查：pyflakes 只报 1 个警告，在 `e2c_launcher_tests.py` 中，这段代码自 f7a0ffe 起没有改动。
- 泄漏检查：用驱动自己的 `leak_scan` 扫描 `remediation_02/` 下的 7 个结果文件，类似键的字符串为 0。
- 按裁决，模拟测试的耗时不计入阶段 2。

## 5. 剩余风险（如实说明）

1. **区间关闭之后的簿记**：审核记录、`summary.json` 和日志在区间关闭之后写入，耗时毫秒级，不计入账本。它们不能产生 PASS。如果驱动恰好在关闭之后、写审核记录之前被杀，账本区间已经是 REVIEW，freeze 仍会按第 2.3 节第 4、5 项拒绝。
2. **审核记录没有解决机制**：代码中没有解决审核记录的途径。记录一旦进入历史，这个输出目录就永久拒绝 freeze。解决需要一个单独授权的程序，例如审核裁决后换用新的输出目录，或者修改代码。本轮没有设计这一程序。
3. **首次提交之前的文件**：首次提交之前，执行者可以删除或伪造账本、审核记录。`budget_admission` 核对的是批准提交中的账本和 git 历史，没有密码学封印。信任锚是审核者对批准提交的检查。
4. **驱动被 SIGKILL 时的子孙进程**：PDEATHSIG 不覆盖子孙进程，它们会继续运行，所用时间也不计入账本。真实作业不创建子进程（静态检查），所以这只是前提条件，不是已证明的保证：如果将来的作业开始创建子进程，这条前提就需要重新核对。
5. **阶段 3 不检查阶段 2 的审核记录**：`run_e2c.py` 只核对审核给出的 `--approved-stage2-commit` 和 `--approved-freeze-sha256`，依赖审核不批准带审核记录的冻结提交。如果要在代码层面保证，需要修改 `run_e2c.py` 并重跑 V4，本轮没有做。
6. **verify 的 stdout**：verify 在最终判定之前就输出两份文件的 sha256。这段 JSON 不含状态，状态只看退出码、`summary.json` 和账本。freeze 只在退出码为 0 时输出。如果审核要求两者一致，可以在下一轮修改。
7. **发布文件中的状态字段**：越过上限时，`stage2_verify.json` 内部的 `status` 仍为 `"PASS"`，因为它不被重写。读者必须以账本和审核记录为准，freeze 准入已经强制这样做。
8. **退出码 71 的分支没有测试**；包装器给每次启动增加约 15 毫秒。
9. **仍无法做到零秒超限的部分**：与 I2-R1 第 4 节相同，包括发布窗口（实测 0.36–0.71 毫秒）、看门狗响应、终止进程组的宽限期，以及长时间的 C 层调用。区别在于：现在任何越过都不会再报告 PASS，而是交给审核。
10. **真实路径**：仍然只经过桩测试，包括真实键空间作业、真实附录 A 脚本、52 个字母的键规则核对和 33 个真实训练流。

## 6. 待裁决事项

- 审核记录的解决程序（第 5 节第 2 项）。
- 是否要求 `run_e2c.py` 在阶段 3 核对阶段 2 的审核记录（第 5 节第 5 项，需要重跑 V4）。
- verify 的 stdout 是否也只在退出码为 0 时输出（第 5 节第 6 项）。
- I2 报告第 7.1 节第 3、4、5 项仍然待裁决：冻结后不能新增代码、停止标记之后的处理方式、驱动本身枚举 H。
- I2-R1 报告第 6 节中"发布窗口内越过上限时是否仍按 PASS 处理"已按本轮裁决处理：不再按 PASS 处理。
