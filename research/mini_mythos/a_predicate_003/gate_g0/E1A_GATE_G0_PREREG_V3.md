# E1A_GATE_G0_PREREG_V3 — 第一次最小受控进程门控测试（G0）预注册 第 3 版

**状态：`FROZEN AT THE COMMIT THAT ADDS THIS FILE / G0 NOT TESTED / EXECUTION NOT AUTHORIZED / IMPLEMENTATION NOT AUTHORIZED AND NOT CONFORMING`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V3-SPEC-001`。基准 `ab66d183752eb8b74f38225a5ebc1187dd2da565`。
机器可读判据：`g0_criteria_v3.json`，SHA-256 `653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a`（本文件与之配套；任一改动都使执行授权失效）。
被取代的 V2：`g0_criteria_v2.json` `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438`、`E1A_GATE_G0_PREREG_V2.md` `ce170a4c85e4ac1d05a47b5a7801a8b392f51909525f0c7e883c33162fef3ff2`（冻结提交 `77750c38998489c3093f80439b52c3c5269db059`）。更早的 V1：`g0_criteria_v1.json` `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`。**V1、V2 的文件、哈希、提交历史保持字节不变，不被覆盖，也不被重新解释。**

**G0–G3 是规划分类，不是已经执行的实验，也不替代 BV-1…BV-10 的编号。本文件不授权任何执行，也不授权修改任何代码。**

## 0. 与 V2 的关系

* V3 是**新版本**。**从未在 V1 或 V2 下执行过任何 G0 运行**，所以没有任何结果会被 V3 改变。
* 为什么需要 V3：对 V2 的语义审查（`G0_V2_SEMANTIC_REVIEW.md` 与 23 个反例）发现：重复的 FORKED / REGISTERED / RELEASED、损坏的字段没有规则；「缺失」类 FAIL 规则把台架写失败和证据损坏误判为协议违规（`RegWriter.write` 先递增 `seq` 再追加）；C16 的证据没有字段名与类型；放行证据只有**写入前**时间戳（发现 F-18），无法区分「尝试」「成功写入」「子进程通过门控」。
* **检查编号 `G0-C01…C17` 全部保持不变，没有新增、拆分或重命名。** 14 项与 V2 文字逐字相同（IDENTICAL），3 项语义改变（MODIFIED：**C03、C07、C16**）。V2→V3 映射：

| ID | 名称 | 失败类别 V2 → V3 | 关系 | 说明 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C02` | authorization_and_bindings | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C03` | registration_sequence_and_integrity | FAIL → FAIL | **MODIFIED** | witness model (ledger first-hand, durable copy for fidelity only); seq gap never a proof; duplicates / malformed fields / multi-node -> FAIL; hole rule needs writer_clean; damaged / foreign / write-failed -> BLOCKED; corroborated REGISTERED-without-FORKED -> FAIL; default UNEVALUABLE |
| `G0-C04` | identity_registered_before_release | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C05` | no_action_before_release | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C06` | gate_descriptor_hygiene | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C07` | release_only_after_registration | FAIL → FAIL | **MODIFIED** | F-18: attempt / success / gate pass are separate facts; a pre-write time is not proof of a write; failed write + FIRST_ACTION -> FAIL; failed or successful write without FIRST_ACTION -> BLOCKED; more than one release write -> FAIL |
| `G0-C08` | exit_observed_unreaped | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C09` | reap_by_specific_pid | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C10` | exit_status_zero | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C11` | process_budget | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C12` | zero_signals | FAIL → FAIL | **IDENTICAL** | text byte-identical to V2 |
| `G0-C13` | cleanup_and_no_residue | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C14` | observer_descriptor_baseline | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C15` | time_bounds | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |
| `G0-C16` | evidence_complete | BLOCKED → BLOCKED | **MODIFIED** | exact field names, types and validation time (evidence_schema); V2-conformant evidence lacking reg_memory_records, reg_writer_seq, evidence_schema, consumed_dir or guard.release_writes is now BLOCKED |
| `G0-C17` | no_unexplained_error | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V2 |

## 1. 目的与范围

与 V1/V2 相同：验证 GATED-SPAWN 在真实 Linux 内核上的**最小正向路径** `INTENT → fork → GATE → REGISTERED → RELEASE → EXIT → REAP`——一个牺牲子进程被受控创建、登记、释放、正常退出并被回收；全程**零信号**。**不在范围：** G1、G2、G3、BV-1…BV-10、E1-A 单元、E1-B/C/D、E2/E3，以及任何关于 Mythos 模型架构、R3、Parcae 或上游台架的结论。

## 2. 裁决政策（项目负责人指令，V3 的依据）

| # | 政策 | 由这些规则实现 |
|---|---|---|
| 1 | Reliable evidence that the registration protocol or a process-safety constraint was violated -> FAIL, labelled as a G0 bench/protocol failure; never automatically attributed to the Mythos model architecture | `C03-F1`, `C03-F2`, `C03-F3`, `C03-F4`, `C07-F1`, `C07-F2`, `C07-F3`, `C07-F4` |
| 2 | Incomplete registry, write failure, damaged parse, evidence that cannot be corroborated -> BLOCKED | `C03-U0`, `C03-U1`, `C03-U2`, `C03-U3`, `C03-U4`, `C07-U1`, `C07-U2`, `C07-U3`, `C07-U4`, `C07-U5` |
| 3 | A corroborated REGISTERED without FORKED -> FAIL in principle (violates the fixed G0 record sequence); BLOCKED if integrity cannot be proven | `C03-F2`, `C03-U2`, `C03-U3` |
| 4 | A seq gap alone is never a proof of FAIL | `C03-U2`, `C03-U3` |
| 5 | Positive evidence together with evidence damage: judge whether the positive evidence is still credible; FAIL does not win unconditionally | `C03-F1`, `C03-F2`, `C03-F3`, `C03-F4`, `C03-U2` |
| 6 | PASS needs every necessary process-evidence and integrity condition at once | `C03-pass_when`, `C07-pass_when`, `C16` |

**FAIL 的归因：** 本判据下产生的每一个 FAIL 都是 **G0 台架 / 协议失败**，摘要必须写明 `fail_scope = 'G0 bench/protocol failure; not evidence about the Mythos model architecture'`；不得自动归因于 Mythos 模型架构、R3 或 Parcae。

## 3. 输入与环境

与 V2 相同：CPU、Python 3.13.16 且以 `python3 -B` 运行、Linux（当前内核 6.18.44-fc-v165）、仅标准库；无 cgroup、无 proc connector、无网络、无 GPU。被测代码：`bench/`（不改动）及 `gate_g0/{g0_auth,g0_judge,g0_run}.py`。

## 4. 过程（固定，不可参数化；与 V2 的差别仅在步骤 4、7 的证据记录）

1. **授权与预检（不启动进程，只读）：** 加载并验证与 **V3** 文件哈希绑定的单次授权；S0 预检（无前次未解决残留、无带标记 `g0_run.py` 的存活非僵尸进程（观察者及其祖先除外）、观察者无子进程、`/proc` 枚举完整、`run_id` 唯一、解释器与信号配置符合 C01）。预检不干净时不 fork、不消耗授权。
2. **目录与授权消耗：** `evidence/` 若不存在则由本次运行非递归创建（0755），否则须是真实目录、非符号链接、属当前有效 uid、不可被组/其他写；运行目录与授权消耗目录排他创建，不覆盖任何已存在的目录或文件；失败 ⇒ BLOCKED，错误尽可能保存。预检干净后、fork **之前**排他创建授权消耗标记。写 `RUN_START`；安装守卫：拦截并记录所有 `kill / killpg / pidfd_send_signal / raise_signal / pthread_kill / exec* / spawn* / system / popen / subprocess`，`fork` 计数且最多放行 1 次，`waitpid` 只放行等于那一个子进程的正 pid；**守卫对放行字节的每一次写入记录 `mono_before`、`mono_after` 与结果（`ok` 且 `returned == 1`，或 `error` 与 errno / 异常文本）；失败的写入被记录，不被丢弃；写入前的时间从不被记为写入。**
3. **一次** `spawn_direct`（`hold_release=True`）：写 `INTENT` → `fork` → 子进程在门上阻塞 → 观察者读 `/proc` 指纹、开 pidfd、校验 `ppid`/起始时间 → 写 `REGISTERED`。观察者在 `hold_before_release_s`（0.3 s）内持续排空控制通道；**保持期结束时拍 S1 快照**。
4. **放行：** 写 `RELEASED` → **放行尝试**（向门写 `R`，守卫记录尝试与结果）→ 写入成功后发 `SPEC` → 子进程读 `SPEC`、发 `FIRST_ACTION`（**通过门控**）、发 `READY` → **S2 快照**。写入失败（如 `EPIPE`）⇒ 运行停止，BLOCKED，除非证据证明了违规。
5. 观察者经**控制通道**发 `EXIT` 消息（不是信号）；子进程 `_exit(0)`。→ **S3 快照**：在任何 wait 调用之前确认 pidfd 可读且 `/proc` 状态为 `Z`。
6. **回收**：对那一个具体 pid 做 `waitpid`（可为非阻塞轮询，受 `reap_deadline_s` 约束，不得无界等待）→ 记录退出码 → 等 `/proc/<pid>` 消失 → **S4 快照**。
7. `final_cleanup`（仅在子进程已退出**且已回收**之后）→ 令牌扫描（仅诊断）→ 写 `RUN_END` → **在最后一次登记写入之后、解析登记文件之前**取**账本**（`reg_memory_records`）与 `reg_writer_seq` → 解析登记文件得到持久副本（`reg`、`reg_parse_info`）→ **S5 快照** → 组装证据（含 `evidence_schema`）→ 以**读回的 JSON 类型**判定（`json.loads(json.dumps(evidence))`）→ 写 `g0_evidence.json`、`g0_summary.json`（FAIL 时含 `fail_scope`）。
8. **异常与提前中止：** 总时长在运行中检查；超时或异常：**不发信号**，写 `RUN_END(cleanup_confirmed=false)`，保存证据，列出仍存活进程的已验证身份并写 `MANUAL_DISPOSITION_REQUIRED.json`；裁决 BLOCKED，除非证据证明了违规。摘要与证据文件**只写入本进程创建的运行目录**。

## 5. 判据（冻结；`g0_criteria_v3.json` 为准）

「与 V2 的关系」：IDENTICAL = 文字与 V2 逐字相同；MODIFIED = 决策语义改变。

| ID | 名称 | 失败类别 | 与 V2 | 内容 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED | IDENTICAL | no unresolved earlier run (no MANUAL_DISPOSITION_REQUIRED.json, no earlier g0_ run directory without a closed g0_summary.json); no live non-zombie process, other than this observer and its ancestors, whose command line contains the marker 'g0_run.py' (this marker is the definition of the V1 term 'bench token'); observer has 0 children; /proc enumeration complete; run id unique (its run directory does not exist before this run creates it); Python is 3.13.16 started with -B; SIGCHLD is not ignored; pidfd_open and socket.send_fds are available |
| `G0-C02` | authorization_and_bindings | BLOCKED | IDENTICAL | a valid single-use G0 authorization bound to THIS criteria file (V2) was consumed: its consumption marker is created exclusively after a clean preflight and BEFORE the fork (a run whose preflight failed consumes nothing); git head, E1-A prereg, G0 criteria, G0 prereg text, bench code and G0 code hashes equal the authorized values at the start AND again at the end |
| `G0-C03` | registration_sequence_and_integrity | FAIL | MODIFIED | registration-file order, protocol and integrity, decided by checks.G0-C03.rules. FAIL when reliable first-hand evidence (the writer's own ledger and/or independent guard and child evidence) proves a violation of the fixed G0 record sequence or of the registration protocol. UNEVALUABLE -> BLOCKED when the registry is incomplete, an append failed, the durable copy is damaged or contains foreign lines, the run stopped early without proof of a violation, or the evidence cannot be corroborated. PASS only on a completed run whose ledger shows exactly the fixed sequence AND whose durable copy is faithful to the ledger. A gap in seq numbers is never by itself a proof of violation. A FAIL is a G0 bench/protocol failure; it is not evidence about the Mythos model architecture |
| `G0-C04` | identity_registered_before_release | FAIL | IDENTICAL | REGISTERED pid/starttime equal the /proc fingerprint read while the child was held; the child's ppid is the observer; pid equals the pid returned by fork |
| `G0-C05` | no_action_before_release | FAIL | IDENTICAL | while REGISTERED but unreleased, observed at the END of the hold (snapshot S1, taken after the observer drained the control channel for hold_before_release_s; messages are counted cumulatively over the whole hold): the child is blocked (state S), sent no message, kept the observer's sid/pgrp; its FIRST_ACTION is not earlier than the RELEASED record |
| `G0-C06` | gate_descriptor_hygiene | FAIL | IDENTICAL | held (snapshot S1, end of the hold): child descriptors are a subset of {0,1,2,gate read end,control socket}, the gate pipe appears exactly once and read-only (no write-capable descriptor); after release (snapshot S2): no descriptor refers to the gate pipe |
| `G0-C07` | release_only_after_registration | FAIL | MODIFIED | release evidence. The release of the gated child is judged by three separate facts: the ATTEMPT (guard.release_writes entry with mono_before), the SUCCESS (the same entry has result 'ok', returned 1 and mono_after) and the GATE PASS (the child's own FIRST_ACTION). PASS: exactly one attempt, it succeeded, and REGISTERED <= RELEASED <= mono_before <= mono_after <= child FIRST_ACTION (REGISTERED and RELEASED times taken from the ledger). FAIL (evidenced): REGISTERED or RELEASED later than the attempt's mono_before; more than one release write; the child passed the gate although every recorded release write failed; the child's FIRST_ACTION is earlier than the successful write's mono_after. UNEVALUABLE -> BLOCKED: no release attempt recorded; the attempt failed and the child did not pass the gate; the write succeeded but the child did not pass the gate; the child passed the gate but no attempt is recorded while RELEASED is in the ledger (instrumentation inconsistency); required times missing. A time taken before the write is never evidence that the byte was written |
| `G0-C08` | exit_observed_unreaped | BLOCKED | IDENTICAL | after the EXIT message and before any wait call the child was observed exited-but-unreaped: pidfd readable and /proc state Z with ppid = observer |
| `G0-C09` | reap_by_specific_pid | BLOCKED | IDENTICAL | waitpid on that specific pid (non-blocking polls bounded by reap_deadline_s are allowed; exactly one call returns that pid, every other call on it returns 0) returned that pid; afterwards /proc/<pid> is absent (or carries a different starttime), waited for at most reap_deadline_s; times EXITED_UNREAPED < REAPED <= PROC_GONE |
| `G0-C10` | exit_status_zero | FAIL | IDENTICAL | the reaped exit code is 0 (normal exit after the EXIT message) |
| `G0-C11` | process_budget | FAIL | IDENTICAL | exactly one fork in the whole run; at every snapshot the observer has at most one child and the child has no child; the registry contains exactly one node and no ticket |
| `G0-C12` | zero_signals | FAIL | IDENTICAL | no kill/killpg/pidfd_send_signal/raise_signal/pthread_kill/exec/spawn/subprocess call was attempted (guard violations empty) and every cleanup kill entry is 'already_exited' |
| `G0-C13` | cleanup_and_no_residue | BLOCKED | IDENTICAL | final cleanup ok, run set consistent, DEAD record with basis present, observer has no child, diagnostic token scan finds no unregistered live process, no snapshot reported incomplete /proc enumeration, RUN_END present with cleanup_confirmed true (on any abnormal stop the run writes RUN_END with cleanup_confirmed false, which fails this check) |
| `G0-C14` | observer_descriptor_baseline | BLOCKED | IDENTICAL | the observer's open descriptor count at S5 equals S0 |
| `G0-C15` | time_bounds | BLOCKED | IDENTICAL | total duration <= max_seconds, measured at the end AND enforced while the run is in progress (checked at every phase boundary and loop iteration; a breach records the deadline hit 'total' and stops the run); no phase deadline was hit (ready, exit, reap, proc_gone, total) |
| `G0-C16` | evidence_complete | BLOCKED | MODIFIED | evidence completeness and type: every field listed in evidence_schema.fields is present with its declared type in the evidence as READ BACK from g0_evidence.json (JSON types; bool is never accepted as int or number; a nullable field may be null; a present field of the wrong type counts as missing) and evidence_schema equals 'e1a-gate-g0-evidence-3'. Relative to V2 the required set changes: the V2 item 'in-memory record count' is replaced by reg_memory_records and reg_writer_seq (the count is derived), and evidence_schema, consumed_dir and guard.release_writes (replacing guard.release_byte_pre_write_monos) are added. Consistency between the registry witnesses is judged by G0-C03, not by this check |
| `G0-C17` | no_unexplained_error | BLOCKED | IDENTICAL | no exception, no abort reason, exit-code policy consistent with the verdict |

### 5.1 `G0-C03`：见证模型与规则（MODIFIED）

**三类见证（谁能证明什么）：**
* **ledger**：evidence.reg_memory_records: what the writer appended successfully, in order. First-hand for what the observer did; unaffected by damage to the file.
* **durable_copy**：evidence.reg + evidence.reg_parse_info: the registry file as parsed. Used ONLY to check fidelity to the ledger (rule C03-U2); never used to prove a violation or an absence.
* **independent**：evidence.guard (fork_calls, release_writes), evidence.events, snapshot S1.messages_received, existence of snapshot S2: first-hand facts not derived from the registry.

**定义：**
* **completed_run**：evidence.exception is null AND evidence.aborted is null AND evidence.deadline_hits is empty
* **early_stop**：not completed_run
* **writer_clean**：the seq values of the ledger are exactly 1..n AND evidence.reg_writer_seq == n (no append failed)
* **disk_faithful**：reg_parse_info has missing=false, unreadable=false, torn_tail=false, corrupt_lines=0 AND the (seq, kind, node_id) triples of the durable copy equal those of the ledger, in order
* **foreign_lines**：triples present in the durable copy and absent from the ledger
* **lifecycle_positions**：RUN_START=0, INTENT=1, FORKED=2, REGISTERED=3, RELEASED=4, DEAD=5; RUN_END is separate (always last); ABORTED is the alternative to REGISTERED and RELEASED
* **hole**：a position p in 0..5 absent from the ledger while a position q > p of the same lifecycle is present in the ledger; RUN_END does not count as a later record; an ABORTED record excuses the absence of REGISTERED and RELEASED
* **tail_absence**：every absent required record has a higher position than every present lifecycle record (nothing present follows an absence); an empty ledger is a tail absence
* **release_attempt**：evidence.guard.release_writes is non-empty (an entry exists, with mono_before)
* **release_write_ok**：an entry of guard.release_writes has result 'ok' and returned == 1 (mono_after recorded)
* **gate_passed**：the child's own FIRST_ACTION exists: events.first_action_mono is set, or S1.messages_received > 0, or snapshot S2 exists

**FAIL 规则（先评估；只依赖各自的见证）：**

| ID | 依赖 | 适用 | 内容 |
|---|---|---|---|
| `C03-F1` | ledger | always | a violation visible in the ledger itself: (a) more than one RUN_START, RUN_END, or, for the node, more than one INTENT, FORKED, REGISTERED, RELEASED, ABORTED or DEAD; (b) the first occurrences violate the order RUN_START < INTENT < FORKED < REGISTERED < RELEASED < DEAD < RUN_END, a record precedes RUN_START, any record follows RUN_END, any record of the node follows its DEAD, or RELEASED and ABORTED both exist; (c) seq not strictly increasing; (d) a field of a present record has the wrong type or value: RUN_START needs run_id (non-empty string) and observer_pid (int, not bool); RUN_END needs the same run_id and cleanup_confirmed (bool); INTENT needs node_id (string) and creator (string); FORKED needs pid (int, not bool); REGISTERED needs pid and starttime (int, not bool); DEAD needs a non-empty basis; (e) RUN_END with cleanup_confirmed true while the node has no DEAD or has an ABORTED; (f) more than one node, or an INTENT whose creator is not 'O' (G0 allows exactly one node and no ticket) |
| `C03-F2` | ledger | only when writer_clean and no foreign_lines | a hole in the ledger, for example REGISTERED present while FORKED is absent, RELEASED present while REGISTERED is absent, FORKED present while INTENT is absent, any record present while RUN_START is absent: the fixed record sequence was not followed. Because no append failed and no foreign line exists, the missing record was never attempted |
| `C03-F3` | ledger + independent | only when no foreign_lines and the independent evidence needed is present | independent evidence proves that an action happened whose precursor record is absent from the ledger: guard.fork_calls >= 1 with no INTENT; a release_attempt with no REGISTERED or no RELEASED; gate_passed with no REGISTERED or no RELEASED. This applies even when an append failed: an action that happened although its precursor append failed is itself the violation |
| `C03-F4` | ledger | only when completed_run and no foreign_lines | a completed run whose ledger lacks any of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis), RUN_END, or contains an ABORTED record |

**UNEVALUABLE → BLOCKED 规则（仅当没有任何 FAIL 规则触发；报告第一条匹配的，列出全部匹配的）：**

| ID | 内容 |
|---|---|
| `C03-U0` | the evidence needed is missing or of the wrong type: reg_memory_records, reg_writer_seq, reg or reg_parse_info (a rule whose own evidence is missing simply cannot fire) |
| `C03-U2` | the durable copy is not faithful or carries foreign lines: file missing or unreadable, torn tail, corrupt line, lost line, extra line, or any difference between the durable triples and the ledger. The durable registry cannot be trusted, so nothing can be concluded from it and the run cannot PASS |
| `C03-U3` | the writer failed: the ledger seq values are not exactly 1..n or reg_writer_seq != n (an append failed; a missing record may be explained by the failure) |
| `C03-U1` | early_stop with tail_absence, writer_clean and a faithful durable copy: the lifecycle could not be completed, which proves nothing about the protocol (includes stopping before the fork: an empty ledger, or RUN_START and RUN_END(false) only) |
| `C03-U4` | any other combination that is not PASS (default: when no rule matches the check is UNEVALUABLE, never PASS and never FAIL) |

* **PASS：** completed_run AND writer_clean AND disk_faithful AND the ledger contains exactly once each of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis) and RUN_END, in that order, with valid fields, no ABORTED and no second node AND no fail rule fired. The VALUE of RUN_END.cleanup_confirmed is judged by G0-C13, not here (a registry that is correct but records an unconfirmed cleanup passes C03 and fails C13)
* **优先级与证据损坏：** fail_when is evaluated first, on the witnesses each rule relies on. Damage to the durable copy never suppresses a rule that does not rely on it: a violation proven by the ledger or by independent evidence stays FAIL (its credibility is reported as first-hand, with the damage listed). Damage that undermines a rule's own witness suppresses that rule: absence-based rules (F2, F3, F4) need writer_clean and no foreign lines, because a failed append or a foreign line makes an absence uninterpretable. If no fail rule fires, the first matching unevaluable rule is reported and all matching ones are listed
* **seq_gap**：a gap in the numbering of the durable copy or of the ledger is never by itself a proof of violation: it means a failed append (U3) or a lost line (U2)
* **registered_without_forked**：REGISTERED present while FORKED is absent: FAIL (F2) when the ledger is gapless and the durable copy faithful or at least free of foreign lines; BLOCKED when integrity cannot be proven (U3, U0, U2 with foreign lines)
* **positive_evidence_with_damage**：decided by relies_on: a ledger-based violation survives damage to the file; an inference from the file never survives damage to the file
* **fidelity_scope**：the durable copy is compared with the ledger on the (seq, kind, node_id) triples only; an alteration inside another field of a record is not detected by this check (known limitation; C16 types only the container)

### 5.2 `G0-C07`：放行证据（MODIFIED，发现 F-18）

**FAIL 规则：**

| ID | 内容 |
|---|---|
| `C07-F1` | ledger REGISTERED.mono > ledger RELEASED.mono, or ledger RELEASED.mono > release_writes[0].mono_before (the release was attempted before the RELEASED record existed) |
| `C07-F2` | more than one entry in guard.release_writes |
| `C07-F3` | gate_passed AND release_writes is non-empty AND no entry has result 'ok' with returned == 1 (the child passed the gate although no release write succeeded) |
| `C07-F4` | gate_passed AND events.first_action_mono < mono_after of the successful entry (the child acted before the release write had completed) |

**UNEVALUABLE → BLOCKED 规则：**

| ID | 内容 |
|---|---|
| `C07-U1` | no release attempt is recorded and the child has not passed the gate (the run stopped before the release) |
| `C07-U2` | the attempt failed (result 'error', for example EPIPE) and the child did not pass the gate |
| `C07-U3` | the write succeeded but the child did not pass the gate (no FIRST_ACTION) |
| `C07-U4` | the child passed the gate but no attempt is recorded while RELEASED is in the ledger (the release instrumentation and the child disagree; reported as an instrumentation inconsistency, not as a verdict on the protocol). When RELEASED is also absent from the ledger the violation is C03-F3 |
| `C07-U5` | a time needed by the rules is missing (ledger REGISTERED or RELEASED, mono_before, mono_after, first_action_mono) |

* **PASS：** exactly one release_writes entry, result 'ok', returned 1, and REGISTERED.mono <= RELEASED.mono <= mono_before <= mono_after <= events.first_action_mono
* 放行「尝试」「成功写入」「子进程通过门控」是三个独立事实：写入前的时间戳从不构成「已写入」的证据。

### 5.3 `G0-C16`：证据模式（MODIFIED）

performed by the judge, once, before any check, on the evidence AS READ BACK from g0_evidence.json (JSON types): a present field of the wrong type counts as missing; bool is never accepted as int or number; nullable fields may be null; extra keys are ignored. g0_run may self-check before writing (diagnostic only); the judge's validation is authoritative

* 版本标识：`evidence_schema` = `e1a-gate-g0-evidence-3`。
* 序列化：the verdict is computed from json.loads(json.dumps(evidence)) so that the judged types are the stored types

| 字段路径 | 类型 | 可为 null | 使用它的检查 | 说明 |
|---|---|---|---|---|
| `evidence_schema` | string | 否 | C16 | must equal 'e1a-gate-g0-evidence-3' |
| `run_id` | string | 否 | C03 C16 |  |
| `auth_expected` | object[6 hex strings: git_head prereg_sha256 g0_criteria_sha256 g0_prereg_sha256 bench_code_sha256 g0_code_sha256] | 否 | C02 |  |
| `bindings_start` | object[same 6 keys] | 否 | C02 |  |
| `bindings_end` | object[same 6 keys] | 否 | C02 |  |
| `auth_consumed` | bool | 否 | C02 |  |
| `observer` | object{pid:int, sid:int, pgrp:int} | 否 | C04 C05 C08 |  |
| `preflight` | object{ok:bool, problems:list, children:int, token_residue:list, unresolved_prior:list, enumeration_problems:object, run_id_unique:bool, fd_count:int, total_procs:int} | 否 | C01 |  |
| `evidence_root` | object{path:string, created_by_this_run:bool, uid:int, mode:int, ino:int} | 否 | C16 | finding F-13 |
| `consumed_dir` | object{path:string, created_by_this_run:bool, uid:int, mode:int, ino:int} | 否 | C16 | finding F-13 |
| `run_dir` | object{path:string, created_by_this_process:bool} | 否 | C16 | finding F-12 |
| `node` | object{node_id:string, pid:int, starttime:int, gate_ino:int} | 否 | C03 C04 C06 C09 |  |
| `snapshots.S0_before_fork.name` | string | 否 | C16 |  |
| `snapshots.S0_before_fork.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S0_before_fork.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S0_before_fork.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S0_before_fork.total_procs` | int | 否 | C16 |  |
| `snapshots.S0_before_fork.enum_problems` | object | 否 | C13 |  |
| `snapshots.S0_before_fork.fd_count` | int | 否 | C14 |  |
| `snapshots.S0_before_fork.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S1_held_registered_unreleased.name` | string | 否 | C16 |  |
| `snapshots.S1_held_registered_unreleased.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S1_held_registered_unreleased.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S1_held_registered_unreleased.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S1_held_registered_unreleased.total_procs` | int | 否 | C16 |  |
| `snapshots.S1_held_registered_unreleased.enum_problems` | object | 否 | C13 |  |
| `snapshots.S1_held_registered_unreleased.fd_count` | int | 否 | C14 |  |
| `snapshots.S1_held_registered_unreleased.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S2_ready_after_release.name` | string | 否 | C16 |  |
| `snapshots.S2_ready_after_release.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S2_ready_after_release.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S2_ready_after_release.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S2_ready_after_release.total_procs` | int | 否 | C16 |  |
| `snapshots.S2_ready_after_release.enum_problems` | object | 否 | C13 |  |
| `snapshots.S2_ready_after_release.fd_count` | int | 否 | C14 |  |
| `snapshots.S2_ready_after_release.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S3_exited_unreaped.name` | string | 否 | C16 |  |
| `snapshots.S3_exited_unreaped.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S3_exited_unreaped.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S3_exited_unreaped.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S3_exited_unreaped.total_procs` | int | 否 | C16 |  |
| `snapshots.S3_exited_unreaped.enum_problems` | object | 否 | C13 |  |
| `snapshots.S3_exited_unreaped.fd_count` | int | 否 | C14 |  |
| `snapshots.S3_exited_unreaped.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S4_reaped.name` | string | 否 | C16 |  |
| `snapshots.S4_reaped.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S4_reaped.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S4_reaped.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S4_reaped.total_procs` | int | 否 | C16 |  |
| `snapshots.S4_reaped.enum_problems` | object | 否 | C13 |  |
| `snapshots.S4_reaped.fd_count` | int | 否 | C14 |  |
| `snapshots.S4_reaped.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S5_final.name` | string | 否 | C16 |  |
| `snapshots.S5_final.mono` | number | 否 | C08 C09 C15 |  |
| `snapshots.S5_final.children` | list[int] | 否 | C11 C13 |  |
| `snapshots.S5_final.grandchildren` | list[int] | 否 | C11 |  |
| `snapshots.S5_final.total_procs` | int | 否 | C16 |  |
| `snapshots.S5_final.enum_problems` | object | 否 | C13 |  |
| `snapshots.S5_final.fd_count` | int | 否 | C14 |  |
| `snapshots.S5_final.child` | object | 是 | C04 C05 C08 C09 |  |
| `snapshots.S0_before_fork.token_residue` | list | 否 | C13 |  |
| `snapshots.S5_final.token_residue` | list | 否 | C13 |  |
| `snapshots.S1_held_registered_unreleased.fds` | object{fd:{target:string, access:string\|null}} | 否 | C06 |  |
| `snapshots.S2_ready_after_release.fds` | object{fd:{target:string, access:string\|null}} | 否 | C06 |  |
| `snapshots.S1_held_registered_unreleased.messages_received` | int | 否 | C05 C03 |  |
| `snapshots.S1_held_registered_unreleased.first_action_mono` | number | 是 | C05 |  |
| `events.first_action_mono` | number | 否 | C05 C07 C03 |  |
| `events.exit_sent_mono` | number | 否 | C08 |  |
| `events.pidfd_readable_mono` | number | 否 | C08 |  |
| `events.reap_mono` | number | 否 | C09 |  |
| `events.proc_gone_mono` | number | 否 | C09 |  |
| `guard.violations` | list | 否 | C12 |  |
| `guard.fork_calls` | int | 否 | C11 C03 |  |
| `guard.fork_pids` | list[int] | 否 | C04 C11 |  |
| `guard.waitpid_calls` | list[object{pid:int, options:int, returned:int, status:int, mono:number}] | 否 | C08 C09 |  |
| `guard.release_writes` | list[object{mono_before:number, mono_after:number\|null, result:string('ok'\|'error'), returned:int\|null, errno:int\|null, error:string\|null}] | 否 | C07 C03 | finding F-18: replaces V2's guard.release_byte_pre_write_monos; one entry per write of the release byte, recorded before AND after the real write |
| `reap.waitpid_pid` | int | 否 | C09 |  |
| `reap.exit_status` | int | 否 | C10 |  |
| `reap.raw_status` | int | 否 | C10 |  |
| `cleanup.cleanup_ok` | bool | 否 | C13 |  |
| `cleanup.run_set` | object{consistent:bool} | 否 | C13 |  |
| `cleanup.rounds` | list | 否 | C12 |  |
| `cleanup.residual_detail` | list | 否 | C13 |  |
| `timing.duration` | number | 否 | C15 |  |
| `deadline_hits` | list[string] | 否 | C15 |  |
| `exception` | string | 是 | C17 C03 |  |
| `aborted` | string | 是 | C17 C03 |  |
| `reg` | list[object{seq:int, kind:string, ...}] | 否 | C03 C04 C05 C11 C13 | the DURABLE copy parsed from registry.jsonl; read for fidelity by C03 and as in V2 by C04 C05 C11 C13 (finding F-19) |
| `reg_parse_info` | object{torn_tail:bool, corrupt_lines:int, missing:bool, unreadable:bool} | 否 | C03 |  |
| `reg_memory_records` | list[object{seq:int, kind:string, ...}] | 否 | C03 C07 | the LEDGER: the records the writer appended successfully, in order (RegWriter.records), captured after the last registry write; replaces V2's 'in-memory record count', which is derived from it |
| `reg_writer_seq` | int | 否 | C03 | RegWriter.seq at the same moment; seq is incremented BEFORE the append, so a failed append leaves reg_writer_seq > len(reg_memory_records) |

### 5.4 裁决规则与已知限度

* A check whose evidence is missing or unreadable is UNEVALUABLE and counts as BLOCKED, whatever its on_fail class (FAIL requires evidence).
* 1. any evaluable check that failed with on_fail FAIL -> experiment verdict FAIL (a confirmed protocol or safety violation takes precedence over bench-level problems)
* 2. else any failed or unevaluable check -> BLOCKED
* 3. else PASS
* NOT TESTED = the run did not start. An exit code of 0 never replaces the verdict.
* V3 FAIL scope: every FAIL produced under these criteria is a G0 bench/protocol failure; the summary must say so; it is not evidence about the Mythos model architecture, R3 or Parcae.
* V3 clarification (replaces the V2 clarification for G0-C03): the rules in checks.G0-C03.rules and checks.G0-C07.rules decide what is a proven violation (FAIL) and what is insufficient or uncorroborated evidence (UNEVALUABLE -> BLOCKED); an early stop alone never makes them a FAIL and never hides a proven violation; damage to a witness suppresses only the rules that rely on that witness.
* V3 meaning of 'evaluable' in rule 1 above: a FAIL-class check counts as an evaluable failure only if the witnesses of the rule that fired are intact (the 'relies_on' of that rule); a FAIL cannot be derived from damaged evidence, so rule 1 never gives FAIL unconditional precedence over evidence damage.
* V3 PASS requires every check to PASS, which includes a faithful durable registry (C03), a proven successful release followed by the child's gate pass (C07) and complete typed evidence (C16).
* V3 known limitation L-1 (unchanged from V2, finding F-14): checks composed of several sub-conditions other than G0-C03 and G0-C07 (for example C05, C06, C11) are UNEVALUABLE as a whole when part of their evidence is missing after an early stop; this can only turn a FAIL into BLOCKED, never into PASS.
* V3 known limitation L-2 (finding F-19): G0-C04, C05, C11 and C13 read the durable copy 'reg' as in V2, not the ledger; under damage of the durable copy they can be UNEVALUABLE where the ledger would suffice. Conservative (BLOCKED), not changed in V3.
* V3 procedural obligations that the judge does not verify (unchanged from V2): the consumption marker is created before the fork (C02), S1 is taken at the end of the hold (C05, C06), the total budget is enforced at run time (C15).

## 6. PASS 的含义与限度

PASS 只表示：在本内核与本 Python 上，一个受控子进程按规定顺序被创建、登记、释放、退出并被回收，没有信号、多余进程或残留，且登记表与证据完整可信。它**不是**对 G1/G2/G3、BV、EPIPE 撤销证明、票据后代、janitor 恢复、观察者死亡、任何 E1-A 单元的证据；也不证明 Python 层守卫之外的所有内核路径安全；更不是关于 Mythos 模型架构的任何证据。

## 7. 授权与绑定

执行需要单独的 `AUTHORIZATION_E1A_GATE_G0.json`（schema `e1a-gate-auth-1`，`stage="G0"`，单次使用），绑定：git HEAD、E1-A 预注册哈希（`e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）、**本 V3 判据哈希、本文件哈希**、台架代码哈希、G0 代码哈希；`grants` 只含 1 个 fork、0 个信号、无故障注入。绑定到 V1 或 V2 文件哈希的授权对 V3 代码**自动无效**。本阶段**不创建**该文件。

## 8. 修改政策

首次在 V3 下执行 G0 之后，不得修改本文件或判据。更正 = 新文件 `g0_criteria_v4.json` / `E1A_GATE_G0_PREREG_V4.md`，旧文件与其下取得的结果保留。执行后不得修改期望以迎合结果。

## 9. 实施一致性（执行前必须满足）

V3 描述的是实现**必须**满足的程序与判定。当前 `g0_run.py` / `g0_judge.py` / `g0_auth.py` **不满足**（仍绑定 V1 文件、旧 C03 / C07 / C16 逻辑、只记录写入前时间戳）。在它们被实现、静态审计、经 ChatGPT / Grok 交叉审核，并由负责人**单独**授权之前，**不得授权任何 G0 执行**，也不得运行纯逻辑测试之外的任何测试：

* **F-8**：bounded reap: non-blocking waitpid polls of the one specific pid, bounded by reap_deadline_s
* **F-9**：runtime total budget checked at phase boundaries and loop iterations; phase deadlines capped by the remaining total
* **F-12**：evidence and summary files are written only into a run directory created by this process
* **F-13**：evidence root and consumption directory are created or validated with explicit ownership; run directory exclusive; failures BLOCKED with the error saved
* **C03-V3**：the judge implements checks.G0-C03.rules on the ledger (reg_memory_records, reg_writer_seq), the durable copy (reg, reg_parse_info) and the independent evidence
* **C07-V3**：the guard records guard.release_writes (mono_before, mono_after, result, returned, errno, error) for every write of the release byte; the judge implements checks.G0-C07.rules
* **C16-V3**：g0_run writes every field of evidence_schema.fields, including on the abnormal path where available; the judge validates presence and type before any check on the evidence as read back from JSON
* **LEDGER**：reg_memory_records and reg_writer_seq are captured after the last registry write and before the registry file is parsed
* **SUMMARY**：g0_summary.json carries fail_scope = 'G0 bench/protocol failure; not evidence about the Mythos model architecture' whenever the verdict is FAIL

执行性约束（来自判据 `enforcement`）：

* **reap_wait**：the wait for the child to be reaped is bounded by limits.reap_deadline_s; no unbounded wait (finding F-8)
* **total_budget**：limits.max_seconds is checked at every phase boundary and loop iteration while the run is in progress, not only at the end (finding F-9); the deadline-hit names are ready, exit, reap, proc_gone, total
* **summary_write**：g0_summary.json and the evidence files are written only into a run directory created by this very process (finding F-12)
* **directories**：the evidence root is created by the run only if absent (non-recursive, mode 0755) and validated otherwise (real directory, not a symlink, owned by the effective uid, not group/other-writable); the run directory and the consumption directory are created exclusively; nothing existing is overwritten; any failure is BLOCKED with the error saved where possible (finding F-13)
* **release_evidence**：the guard records, for every write of the release byte, mono_before, mono_after and the result ('ok' with returned == 1, or 'error' with errno and error text); a failed write is recorded, never dropped; a pre-write time is never recorded as a write (finding F-18)
* **registry_ledger**：the observer's in-memory record list and the writer's seq are captured after the last registry write, before the registry file is parsed, and stored as reg_memory_records and reg_writer_seq
