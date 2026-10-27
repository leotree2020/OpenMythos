# E1A_GATE_G0_PREREG_V2 — 第一次最小受控进程门控测试（G0）预注册 第 2 版

**状态：`FROZEN AT THE COMMIT THAT ADDS THIS FILE / G0 NOT TESTED / EXECUTION NOT AUTHORIZED / IMPLEMENTATION NOT YET CONFORMING`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V2-SPEC-001`。基准 `e0ffef9b4a81e9d11266a09475271f4c57669c8d`。
机器可读判据：`g0_criteria_v2.json`，SHA-256 `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438`（本文件与之配套；任一改动都使执行授权失效）。
被取代的 V1：`g0_criteria_v1.json` `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`、`E1A_GATE_G0_PREREG.md` `9eca01eda5a4c24eb5784c53e65e215e2892c6d0e3bbf7206346184e949051eb`（提交 `e287b952124e8aaf22098e1957c61da5359a5e2c`）。**V1 原文件、哈希、提交历史保持原样，不被覆盖，也不被重新解释。**

**G0–G3 是规划分类，不是已经执行的实验，也不替代 BV-1…BV-10 的编号。本文件不授权任何执行。**

## 0. 与 V1 的关系

* V2 是**新版本**，不是对 V1 的修订。**从未在 V1 下执行过任何 G0 运行**，所以没有任何结果会被 V2 改变。
* 为什么需要 V2：V1 的 C03 是 FAIL 类并要求 `DEAD` 与 `RUN_END`，而 V1 §3 第 8 步写「超时或异常：判 BLOCKED」。按字面，任何提前中止都会使 C03 成为**可评估的失败**，裁决规则①给出 FAIL。V1 自相矛盾；实现取了第 8 步的读法。预注册不能把这种选择留给实现者，所以 V2 把规则写明。
* **检查编号 `G0-C01…C17` 全部保持不变，没有新增、拆分或重命名。** 8 项文字逐字不变（IDENTICAL），8 项只补充定义或时点（CLARIFIED，决策语义不变），1 项语义改变（MODIFIED：C03）。完整映射：

| ID | V1 名称 | V2 名称 | 失败类别 V1 → V2 | 关系 | 说明 |
|---|---|---|---|---|---|
| `G0-C01` | preflight_clean | preflight_clean | BLOCKED → BLOCKED | **CLARIFIED** | defines 'bench token' (deviation 5); lists the interpreter/signal/syscall preconditions the implementation already checks; run-id uniqueness is 'directory does not exist yet' (deviation 3) |
| `G0-C02` | authorization_and_bindings | authorization_and_bindings | BLOCKED → BLOCKED | **CLARIFIED** | consumption timing stated (deviation 2); binding to V2 files follows from the hash bindings |
| `G0-C03` | registration_sequence_and_integrity | registration_sequence_and_integrity | FAIL → FAIL | **MODIFIED** | the only check whose decision semantics change: early stops and damaged evidence are UNEVALUABLE (BLOCKED) unless a violation is proven |
| `G0-C04` | identity_registered_before_release | identity_registered_before_release | FAIL → FAIL | **IDENTICAL** | text byte-identical to V1 |
| `G0-C05` | no_action_before_release | no_action_before_release | FAIL → FAIL | **CLARIFIED** | S1 timing and cumulative message count stated (deviation 1) |
| `G0-C06` | gate_descriptor_hygiene | gate_descriptor_hygiene | FAIL → FAIL | **CLARIFIED** | S1 timing stated (deviation 1) |
| `G0-C07` | release_only_after_registration | release_only_after_registration | FAIL → FAIL | **IDENTICAL** | text byte-identical to V1 |
| `G0-C08` | exit_observed_unreaped | exit_observed_unreaped | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V1 |
| `G0-C09` | reap_by_specific_pid | reap_by_specific_pid | BLOCKED → BLOCKED | **CLARIFIED** | states that the reap wait is bounded and may be a non-blocking poll of the one specific pid (finding F-8); the decision semantics are unchanged |
| `G0-C10` | exit_status_zero | exit_status_zero | FAIL → FAIL | **IDENTICAL** | text byte-identical to V1 |
| `G0-C11` | process_budget | process_budget | FAIL → FAIL | **IDENTICAL** | text byte-identical to V1 |
| `G0-C12` | zero_signals | zero_signals | FAIL → FAIL | **IDENTICAL** | text byte-identical to V1 |
| `G0-C13` | cleanup_and_no_residue | cleanup_and_no_residue | BLOCKED → BLOCKED | **CLARIFIED** | RUN_END on the abnormal path stated (deviation 4) |
| `G0-C14` | observer_descriptor_baseline | observer_descriptor_baseline | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V1 |
| `G0-C15` | time_bounds | time_bounds | BLOCKED → BLOCKED | **CLARIFIED** | runtime enforcement of the total budget stated (finding F-9); the check itself is unchanged |
| `G0-C16` | evidence_complete | evidence_complete | BLOCKED → BLOCKED | **CLARIFIED** | evidence list extended for C03 (parse report, record count) and finding F-13 (ownership records) |
| `G0-C17` | no_unexplained_error | no_unexplained_error | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V1 |

* 同时正式处理上一轮记录的六项文字偏差（§9）。

## 1. 目的与范围

与 V1 相同：验证 GATED-SPAWN 在真实 Linux 内核上的**最小正向路径** `INTENT → fork → GATE → REGISTERED → RELEASE → EXIT → REAP`——一个牺牲子进程被受控创建、登记、释放、正常退出并被回收；全程**零信号**。**不在范围：** G1、G2、G3、BV-1…BV-10、E1-A 单元、E1-B/C/D、E2/E3。G0 的授权**不能**继承为上述任何一项的授权，入口代码也没有通向它们的路径。

## 2. 输入与环境

CPU、Python 3.13.16 且以 `python3 -B` 运行、Linux（当前微型虚机内核 6.18.44-fc-v165）、uid 0（不依赖 root，仅依赖 `pidfd_open` ≥ 5.3 与 `socket.send_fds`）、仅标准库；无 cgroup、无 proc connector、无网络、无 GPU。被测代码：`bench/{observer,gate,node,proto,registry,common,truth}.py`（不改动）及 `gate_g0/{g0_auth,g0_judge,g0_run}.py`。运行目录 `evidence/g0_<run_id>/`，唯一 `run_id`。

## 3. 过程（固定，不可参数化）

1. **授权与预检（不启动进程，只读）：** `main` 先加载并验证与 **V2** 文件哈希绑定的单次授权，之后做 S0 预检：无前次未解决残留（无 `MANUAL_DISPOSITION_REQUIRED.json`；无缺 `g0_summary.json` 的 `g0_*` 目录）、无带标记 `g0_run.py` 的存活非僵尸进程（观察者自身及其祖先除外）、观察者无子进程、`/proc` 枚举完整、`run_id` 唯一（其运行目录尚不存在）、解释器与信号配置符合 C01。预检不干净时不 fork、不消耗授权。
2. **目录与授权消耗：** 证据根目录 `evidence/` 若不存在则由本次运行非递归创建（0755），若存在则须是真实目录、非符号链接、属当前有效 uid、不可被组/其他写；运行目录与授权消耗目录排他创建；**不覆盖任何已存在的目录或文件**；任一创建失败 ⇒ BLOCKED，错误信息尽可能保存。预检干净后、fork **之前**，以排他方式创建授权消耗标记。写 `RUN_START`；安装守卫：**拦截并记录**所有 `kill / killpg / pidfd_send_signal / raise_signal / pthread_kill / exec* / spawn* / system / popen / subprocess`，`fork` 计数且最多放行 1 次，`waitpid` 只放行正的、等于那一个子进程的 pid。
3. **一次** `spawn_direct`（`hold_release=True`）：写 `INTENT` → `fork` → 子进程在门上阻塞 → 观察者读 `/proc` 指纹、开 pidfd、校验 `ppid`/起始时间 → 写 `REGISTERED`。观察者在 `hold_before_release_s`（0.3 s）内持续排空控制通道；**保持期结束时拍 S1 快照**（已登记、未释放）：子进程状态、描述符、累计消息数、sid/pgrp。保持期内子进程必须无任何动作。
4. 写 `RELEASED` → 向门写 `R` → 子进程读 `SPEC`、发 `FIRST_ACTION`、发 `READY` 后留在控制通道上等待。→ **S2 快照**（描述符中不得再有门管道）。
5. 观察者经**控制通道**发 `EXIT` 消息（不是信号）；子进程 `_exit(0)`。→ **S3 快照**：在**任何 wait 调用之前**确认 pidfd 可读且 `/proc` 状态为 `Z`（已退出、未回收）。
6. **回收**：对**那一个具体 pid** 做 `waitpid`（可为非阻塞轮询，受 `reap_deadline_s` 约束，不得无界等待）→ 记录退出码 → 等 `/proc/<pid>` 消失（至多 `reap_deadline_s`）→ **S4 快照**。**退出与回收是两个独立的、有时间戳的证据。**
7. `final_cleanup`（仅在子进程已退出**且已回收**之后调用；入口关闭、不动点、运行集合核对、写 `DEAD`）→ 令牌扫描（仅诊断）→ 写 `RUN_END`（含 `cleanup_confirmed`）→ **S5 快照**，写 `g0_evidence.json`、`g0_summary.json`。
8. **异常与提前中止：** 总时长上限 `max_seconds` 在运行中检查（每个阶段边界与循环迭代），各阶段截止时间见判据文件；超时或异常：**不发信号**，写 `RUN_END(cleanup_confirmed=false)`，保存证据，列出仍存活进程的已验证身份并写 `MANUAL_DISPOSITION_REQUIRED.json`；裁决为 BLOCKED，除非证据证明了违规（C03 规则、其他检查的 FAIL 类）。`g0_summary.json` 与证据文件**只写入本进程创建的运行目录**。

## 4. 预期结果（先于执行写下）

PASS 的预期观测：`fork` 恰 1 次；S1 子进程状态 `S`、描述符 ≤ 5 个且门管道仅一个只读描述符；`FIRST_ACTION` 晚于 `RELEASED`；S3 状态 `Z` 且 ppid = 观察者；`waitpid` 退出码 0；S4 无 `/proc/<pid>`；信号 0 次；`DEAD` 带依据；观察者描述符数 S5 = S0；无残留。

## 5. 判据（冻结；`g0_criteria_v2.json` 为准）

下表的「V1 关系」：IDENTICAL = 文字与 V1 逐字相同；CLARIFIED = 决策语义不变、补充了定义或时点；MODIFIED = 决策语义改变。

| ID | 名称 | 失败类别 | V1 关系 | 内容 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED | CLARIFIED | no unresolved earlier run (no MANUAL_DISPOSITION_REQUIRED.json, no earlier g0_ run directory without a closed g0_summary.json); no live non-zombie process, other than this observer and its ancestors, whose command line contains the marker 'g0_run.py' (this marker is the definition of the V1 term 'bench token'); observer has 0 children; /proc enumeration complete; run id unique (its run directory does not exist before this run creates it); Python is 3.13.16 started with -B; SIGCHLD is not ignored; pidfd_open and socket.send_fds are available |
| `G0-C02` | authorization_and_bindings | BLOCKED | CLARIFIED | a valid single-use G0 authorization bound to THIS criteria file (V2) was consumed: its consumption marker is created exclusively after a clean preflight and BEFORE the fork (a run whose preflight failed consumes nothing); git head, E1-A prereg, G0 criteria, G0 prereg text, bench code and G0 code hashes equal the authorized values at the start AND again at the end |
| `G0-C03` | registration_sequence_and_integrity | FAIL | MODIFIED | registration-file order and integrity, decided by rules.fail_when / rules.unevaluable_when / rules.pass_when (evaluated in that order). FAIL when the registry itself, or evidence independent of it, PROVES an order/integrity/protocol violation. UNEVALUABLE -> BLOCKED when the run stopped early (exception, abort, deadline) or the registry evidence is damaged and no proof of a violation exists. PASS on a completed run when RUN_START is first and unique, for the single node INTENT < FORKED < REGISTERED < RELEASED < DEAD, RUN_END is last and unique, registry.integrity_issues() is empty and the parse report is clean |
| `G0-C04` | identity_registered_before_release | FAIL | IDENTICAL | REGISTERED pid/starttime equal the /proc fingerprint read while the child was held; the child's ppid is the observer; pid equals the pid returned by fork |
| `G0-C05` | no_action_before_release | FAIL | CLARIFIED | while REGISTERED but unreleased, observed at the END of the hold (snapshot S1, taken after the observer drained the control channel for hold_before_release_s; messages are counted cumulatively over the whole hold): the child is blocked (state S), sent no message, kept the observer's sid/pgrp; its FIRST_ACTION is not earlier than the RELEASED record |
| `G0-C06` | gate_descriptor_hygiene | FAIL | CLARIFIED | held (snapshot S1, end of the hold): child descriptors are a subset of {0,1,2,gate read end,control socket}, the gate pipe appears exactly once and read-only (no write-capable descriptor); after release (snapshot S2): no descriptor refers to the gate pipe |
| `G0-C07` | release_only_after_registration | FAIL | IDENTICAL | monotonic times satisfy REGISTERED <= RELEASED <= release byte written <= child FIRST_ACTION |
| `G0-C08` | exit_observed_unreaped | BLOCKED | IDENTICAL | after the EXIT message and before any wait call the child was observed exited-but-unreaped: pidfd readable and /proc state Z with ppid = observer |
| `G0-C09` | reap_by_specific_pid | BLOCKED | CLARIFIED | waitpid on that specific pid (non-blocking polls bounded by reap_deadline_s are allowed; exactly one call returns that pid, every other call on it returns 0) returned that pid; afterwards /proc/<pid> is absent (or carries a different starttime), waited for at most reap_deadline_s; times EXITED_UNREAPED < REAPED <= PROC_GONE |
| `G0-C10` | exit_status_zero | FAIL | IDENTICAL | the reaped exit code is 0 (normal exit after the EXIT message) |
| `G0-C11` | process_budget | FAIL | IDENTICAL | exactly one fork in the whole run; at every snapshot the observer has at most one child and the child has no child; the registry contains exactly one node and no ticket |
| `G0-C12` | zero_signals | FAIL | IDENTICAL | no kill/killpg/pidfd_send_signal/raise_signal/pthread_kill/exec/spawn/subprocess call was attempted (guard violations empty) and every cleanup kill entry is 'already_exited' |
| `G0-C13` | cleanup_and_no_residue | BLOCKED | CLARIFIED | final cleanup ok, run set consistent, DEAD record with basis present, observer has no child, diagnostic token scan finds no unregistered live process, no snapshot reported incomplete /proc enumeration, RUN_END present with cleanup_confirmed true (on any abnormal stop the run writes RUN_END with cleanup_confirmed false, which fails this check) |
| `G0-C14` | observer_descriptor_baseline | BLOCKED | IDENTICAL | the observer's open descriptor count at S5 equals S0 |
| `G0-C15` | time_bounds | BLOCKED | CLARIFIED | total duration <= max_seconds, measured at the end AND enforced while the run is in progress (checked at every phase boundary and loop iteration; a breach records the deadline hit 'total' and stops the run); no phase deadline was hit (ready, exit, reap, proc_gone, total) |
| `G0-C16` | evidence_complete | BLOCKED | CLARIFIED | all snapshots, events, REG records and bindings required by this file are present in the evidence, together with the registry parse report, the in-memory record count of the registry, the evidence-root ownership record and the run-directory creation record |
| `G0-C17` | no_unexplained_error | BLOCKED | IDENTICAL | no exception, no abort reason, exit-code policy consistent with the verdict |

### 5.1 `G0-C03` 细则（MODIFIED）

**定义：**
* **completed_run**：evidence.exception is null AND evidence.aborted is null AND evidence.deadline_hits is empty
* **early_stop**：not completed_run
* **parse_clean**：reg_parse_info has missing=false, unreadable=false, torn_tail=false and corrupt_lines=0
* **independent_evidence**：guard.fork_calls and guard.fork_pids；guard.release_byte_pre_write_monos (the observer's own record that it was about to write the release byte)；child-originated facts: evidence.events.first_action_mono, snapshot S1.messages_received, existence of snapshot S2 (READY was received)；/proc snapshots S0..S5
* **release_byte_written**：guard.release_byte_pre_write_monos is non-empty
* **child_acted**：events.first_action_mono is set, or S1.messages_received > 0, or snapshot S2 exists
* **positive_violation**：a violation visible in records that ARE present (cannot be produced by a lost or unparsed line)
* **absence_based_violation**：a violation that consists of a record NOT being present (can be produced by a lost or unparsed line, hence only trusted when parse_clean)

**FAIL 规则（先评估；有证据才判 FAIL）：**

| ID | 适用条件 | 内容 |
|---|---|---|
| `C03-F1` | always (also when the file is damaged) | among the records that are present: a successor has an earlier seq than its predecessor (RELEASED before REGISTERED, REGISTERED before INTENT, FORKED before INTENT); non-monotonic or duplicated seq; more than one RUN_START, RUN_END, INTENT or DEAD; a record before RUN_START; any record after RUN_END; any record of the node after its DEAD; RELEASED and ABORTED both present; a RUN_END or RUN_START whose fields are malformed or whose run_id differs |
| `C03-F2` | only when parse_clean | the registry itself proves a missing record: a successor is present while its required predecessor is absent (RELEASED without REGISTERED, REGISTERED without INTENT, FORKED without INTENT, DEAD without INTENT); a node record without any INTENT (orphan); a gap in seq; a RUN_END with cleanup_confirmed true while the node has no DEAD record |
| `C03-F3` | only when parse_clean | independent evidence proves that an action took place whose preceding record is absent: no RELEASED record although release_byte_written or child_acted; no REGISTERED record although release_byte_written, child_acted or a RELEASED record exists; no INTENT record although guard.fork_calls >= 1 |
| `C03-F4` | only when parse_clean and completed_run | a required record is absent from a run that completed normally: any of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis), RUN_END; or ABORTED is present |

**UNEVALUABLE → BLOCKED 规则（仅当没有任何 FAIL 规则触发）：**

| ID | 内容 |
|---|---|
| `C03-U1` | early_stop AND parse_clean AND no fail rule fired: the only deviations are missing later-lifecycle records (FORKED, REGISTERED, RELEASED, DEAD, RUN_END, or an ABORTED record from a failed registration) and no independent evidence shows that an action happened without its record -> the lifecycle could not be completed, which proves nothing about the protocol |
| `C03-U2` | no fail rule fired AND (the registry file is missing or unreadable, or has a torn tail or corrupt lines, or the independent evidence needed by C03-F3 is itself missing) -> the evidence is damaged or absent |

* **PASS：** completed_run AND parse_clean AND the PASS condition of the check text holds. The rules are exhaustive: a completed, parse-clean run that does not satisfy pass_when has a missing or irregular record and therefore fires C03-F1, F2 or F4; an early stop that fires no fail rule is C03-U1 or C03-U2.
* **优先级：** fail_when is evaluated first: a proven violation is never hidden by an early stop (this is what V1 intended with 'a confirmed protocol or safety violation takes precedence'); unevaluable_when only applies if no fail rule fires; a damaged file suppresses every absence-based rule, keeping only the positive ones
* **V1 矛盾的处理：** V1 listed C03 as a FAIL-class check demanding DEAD and RUN_END, while V1 section 3 step 8 says that a timeout or exception is judged BLOCKED. Read literally, every early stop would be an evaluable C03 failure and therefore FAIL. V2 states the rule explicitly. V1 is not reinterpreted: no G0 run was ever executed under V1.

### 5.2 裁决规则

缺证据的检查为 UNEVALUABLE（一律按 BLOCKED，FAIL 必须有证据）；① 任一**可评估**且失败的 FAIL 类检查 ⇒ **FAIL**（已确认的协议 / 安全违规优先于台架层面的问题）；② 否则任一失败或 UNEVALUABLE ⇒ **BLOCKED**；③ 否则 **PASS**；**NOT TESTED** = 未启动。**退出码**：PASS 0，FAIL 1，BLOCKED 3；退出码 0 不替代裁决，也不掩盖异常。
**已知限度 L-1（与 V1 相同，保守）：** C03 之外由多个子条件组成的检查（如 C05、C06、C11），在提前中止后若部分证据缺失，整项为 UNEVALUABLE；可见部分里的违规会被报告为 BLOCKED 而不是 FAIL。这只可能把 FAIL 变成 BLOCKED，绝不会变成 PASS；证据保留并由人阅读。是否让这些检查按子条件独立评估，留给后续版本（发现 F-14）。

## 6. PASS 的含义与限度

PASS 只表示：在本内核与本 Python 上，一个受控子进程按规定顺序被创建、登记、释放、退出并被回收，没有信号、多余进程或残留。它**不是**对 G1/G2/G3、BV、EPIPE 撤销证明、票据后代、janitor 恢复、观察者死亡、任何 E1-A 单元的证据；也不证明 Python 层守卫之外的所有内核路径安全。

## 7. 授权与绑定

执行需要单独的 `AUTHORIZATION_E1A_GATE_G0.json`（schema `e1a-gate-auth-1`，`stage="G0"`，单次使用），绑定：git HEAD、E1-A 预注册哈希（`e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）、**本 V2 判据哈希、本文件哈希**、台架代码哈希、G0 代码哈希；`grants` 只含 1 个 fork、0 个信号、无故障注入。绑定到 V1 文件哈希的授权对 V2 代码**自动无效**（哈希不符）。本阶段**不创建**该文件。

## 8. 修改政策

首次在 V2 下执行 G0 之后，不得修改本文件或判据。更正 = 新文件 `g0_criteria_v3.json` / `E1A_GATE_G0_PREREG_V3.md`，旧文件与其下取得的结果保留。执行后不得修改期望以迎合结果。

## 9. 六项文字偏差的正式处理

上一轮（G0-PREFLIGHT-001）对安全评审 §6 的六项偏差的处置：1–5 为 ACCEPTABLE（文字对齐），6 为 REQUIRES V2。V2 把它们落实到下列位置：

| # | 偏差 | 上轮处置 | V2 中的落点 |
|---|---|---|---|
| 1 | S1 is taken after the hold, not before it | `ACCEPTABLE` | E1A_GATE_G0_PREREG_V2.md section 3 step 3; checks G0-C05 and G0-C06 |
| 2 | authorization consumed before the fork | `ACCEPTABLE` | section 3 steps 2-3; check G0-C02 |
| 3 | preflight before the run directory exists; run-id uniqueness = directory does not exist | `ACCEPTABLE` | section 3 steps 1-2; check G0-C01 |
| 4 | RUN_END(cleanup_confirmed=false) on the abnormal path | `ACCEPTABLE` | section 3 step 8; checks G0-C13 and G0-C03 |
| 5 | token = command line contains g0_run.py | `ACCEPTABLE` | check G0-C01 |
| 6 | C03 on incomplete runs | `REQUIRES V2` | check G0-C03 (MODIFIED) and its rules |

## 10. 实施一致性（执行前必须满足）

V2 描述的是实现**必须**满足的程序。当前 `g0_run.py` / `g0_judge.py` **尚未**满足下列义务（发现 F-8/F-9/F-12/F-13 及 C03 规则）；在它们被实现、静态审计、经 ChatGPT/Grok 交叉审核，并由负责人单独授权之前，**不得授权任何 G0 执行**：

* **F-8**：bounded reap: non-blocking waitpid polls of the one specific pid, bounded by reap_deadline_s
* **F-9**：runtime total budget checked at phase boundaries and loop iterations; phase deadlines capped by the remaining total
* **F-12**：evidence and summary files are written only into a run directory created by this process
* **F-13**：evidence root and consumption directory are created or validated with explicit ownership; run directory exclusive; failures BLOCKED with the error saved
* **C03**：the judge implements checks.G0-C03.rules; the registry parse report and the in-memory record count are recorded in the evidence

执行性约束（来自判据 `enforcement`）：

* **reap_wait**：the wait for the child to be reaped is bounded by limits.reap_deadline_s; no unbounded wait (finding F-8)
* **total_budget**：limits.max_seconds is checked at every phase boundary and loop iteration while the run is in progress, not only at the end (finding F-9); the deadline-hit names are ready, exit, reap, proc_gone, total
* **summary_write**：g0_summary.json and the evidence files are written only into a run directory created by this very process (finding F-12)
* **directories**：the evidence root is created by the run only if absent (non-recursive, mode 0755) and validated otherwise (real directory, not a symlink, owned by the effective uid, not group/other-writable); the run directory and the consumption directory are created exclusively; nothing existing is overwritten; any failure is BLOCKED with the error saved where possible (finding F-13)
