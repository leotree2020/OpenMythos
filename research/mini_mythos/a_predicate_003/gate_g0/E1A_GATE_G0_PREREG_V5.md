# E1A_GATE_G0_PREREG_V5 — 第一次最小受控进程门控测试（G0）预注册 第 5 版（最小结案修订）

**状态：`FROZEN AT THE COMMIT THAT ADDS THIS FILE / G0 NOT TESTED / EXECUTION NOT AUTHORIZED / IMPLEMENTATION NOT AUTHORIZED AND NOT CONFORMING / DECISIONS PROPOSED, PENDING OWNER APPROVAL`**
任务：`F3B-D1-A-CPU-003-E1A-G0-V5-CLOSEOUT-SPEC-001`。基准 `d127ec58c0adc90d11fb7fc59240632fc4e36d5b`。
机器可读判据：`g0_criteria_v5.json`，SHA-256 `d36da0c0ad83f14c85eae3e055e3172fc7004811d9beae78e78dfc06782cb821`（本文件与之配套；任一改动都使执行授权失效）。
被取代的 V4：`g0_criteria_v4.json` `6f3ed20767b5842616068037d53940e82ac8a88859332503d1c3e698c0b38414`、`E1A_GATE_G0_PREREG_V4.md` `05de3f1f4ff9e035535f78a402c450d90815abae14e4ac2809e3e1fd8e48cd42`（冻结提交 `753b4609de831b49187b198a1832e1b08424ac88`）。更早：V3 `g0_criteria_v3.json` `653f64c74b63b120f3fd662010aa14fcdb7400714fbfca447dc4845c138f872a`；V2 `g0_criteria_v2.json` `43f7eb79d43b624bdea5db53705fe923bfe7d94a70ff43da7a43fecd51e5c438`；V1 `g0_criteria_v1.json` `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`。**V1、V2、V3、V4 的文件、哈希、提交历史保持字节不变，不被覆盖，也不被重新解释。**

**G0–G3 是规划分类，不是已经执行的实验，也不替代 BV-1…BV-10 的编号。本文件不授权任何执行，也不授权修改任何代码。**

## 0. 与 V4 的关系（只修改结案确认）

* V5 是**新版本**，也是一次**最小修订**：**从未在 V1…V4 任何版本下执行过 G0 运行**，所以没有任何结果会被 V5 改变。
* 为什么需要 V5：ChatGPT 与 Grok 对 V4 的独立静态审核确认 **F-23**——V4 的 P6 在摘要写入、fsync 或读回失败时，`g0_summary.json` 仍可能留在运行目录中（半截或未经验证）；现有预检（`g0_run.py` 第 224–225 行）与 V4 对 G0-C01 的文字只检查该文件**是否存在**，于是这样的运行目录会被当成已结案，新的真实 G0 运行不会被拒绝。
* **只修改：** ① 流水线 P6/P7 的结案确认流程；② `G0-C01` 对历史运行的结案验证要求；③ 新增机器可读的结案标记 `g0_closed.json`；④ 与之相关的目录、同步和异常处理。
* **不改变：** `G0-C02…C17` 的文字与裁决规则（逐字相同）；C03、C07、C16 的规则；DD-1…DD-5 及 V4 全部既有条件决策；`FAIL` 只表示 G0 台架 / 协议失败。
* **检查编号 `G0-C01…C17` 保持不变。** V4 → V5：16 项 IDENTICAL，1 项 MODIFIED（**C01**）。

| ID | 名称 | 失败类别 V4 → V5 | 关系 | 说明 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED → BLOCKED | **MODIFIED** | earlier runs are closed only by a valid g0_closed.json bound to verified summary and evidence; summary existence no longer closes a run; process residue is evaluated independently of the marker |
| `G0-C02` | authorization_and_bindings | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C03` | registration_sequence_and_integrity | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C04` | identity_registered_before_release | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C05` | no_action_before_release | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C06` | gate_descriptor_hygiene | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C07` | release_only_after_registration | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C08` | exit_observed_unreaped | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C09` | reap_by_specific_pid | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C10` | exit_status_zero | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C11` | process_budget | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C12` | zero_signals | FAIL → FAIL | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C13` | cleanup_and_no_residue | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C14` | observer_descriptor_baseline | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C15` | time_bounds | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C16` | evidence_complete | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |
| `G0-C17` | no_unexplained_error | BLOCKED → BLOCKED | **IDENTICAL** | text and decision rules byte-identical to V4 |

* **V5 变更清单（机器可读：`v4_to_v5_changes`；检查工具核对「实际改动的路径 = 清单声明的路径」）：**

| 变更 | 对应问题 | 涉及路径 | 内容 |
|---|---|---|---|
| `V5-CH-1` | F-23 | `evidence_pipeline.stages.P6` | a failed P6 no longer relies on a missing summary file to keep later runs out; a partial or unverified summary file is not closure and the missing marker is what blocks |
| `V5-CH-2` | F-23 | `evidence_pipeline.stages.P7`, `evidence_pipeline.stages.P5`, `evidence_pipeline.principle`, `evidence_pipeline.preserved_on_failure`, `evidence_pipeline.durability_limits`, `evidence_pipeline.overwrite_policy` | P7 publishes the closure marker (K1..K7) and returns the exit code only afterwards; P5, durability and overwrite texts adapted |
| `V5-CH-3` | F-23 | `checks.G0-C01` | C01 requires every earlier run to be closed by a valid marker and evaluates process residue independently |
| `V5-CH-4` | F-23 | `closure` | new: marker schema, atomic exclusive publication, preflight facts and rules CL-01..CL-23, crash points, what closure does and does not prove |
| `V5-CH-5` | F-23 | `enforcement`, `verdict_rule`, `verdict_policy`, `implementation_obligations`, `limitations`, `meaning_of_pass`, `amendment_policy` | enforcement, verdict policy, verdict rule, obligations, limitations and the meaning of PASS mention the closure; amendment policy points to the next file names |
| `V5-CH-6` | V4 erratum | `evidence_schema` | documentation only: the note of field 'evidence_schema' said 'e1a-gate-g0-evidence-3' while the schema id, C16 and the obligations say '-4'; the note now says '-4'. The preflight field note names the new unresolved_prior format. No field, type or consumer changed. Reviewers are asked to confirm that this correction belongs in V5 |
| `V5-CH-7` | identity | `criteria_id`, `schema_version`, `base_commit`, `supersedes`, `decision_register`, `v4_to_v5_mapping`, `v4_to_v5_changes` | identity, supersession, decision register (DD-1..DD-5 and all V4 decisions unchanged; closure decisions added), V4->V5 mapping and change list |

* **V4 勘误（V5-CH-6，请审核者确认放在 V5 是否合适）：** V4 的证据模式字段 `evidence_schema` 的说明写成 `must equal 'e1a-gate-g0-evidence-3'`，而模式标识、C16 文字和义务写的都是 `-4`——这是 V4 冻结文本中的一处已知矛盾。V5 把该说明改为 `-4`，只改文字，不改任何字段、类型或使用者。
* 为保持历史完整，V4 引入的 V3 → V4 映射与规则迁移表保留在 §14 附录中，不重新解释。

## 1. 目的与范围

与 V1…V4 相同：验证 GATED-SPAWN 在真实 Linux 内核上的**最小正向路径** `INTENT → fork → GATE → REGISTERED → RELEASE → EXIT → REAP`——一个牺牲子进程被受控创建、登记、释放、正常退出并被回收；全程**零信号**。**不在范围：** G1、G2、G3、BV-1…BV-10、E1-A 单元、E1-B/C/D、E2/E3，以及任何关于 Mythos 模型架构、R3、Parcae 或上游台架的结论。

## 2. 裁决政策

| # | 政策 | 由这些规则实现 |
|---|---|---|
| 1 | Reliable evidence that the registration protocol or a process-safety constraint was violated -> FAIL, labelled as a G0 bench/protocol failure; never attributed to the Mythos model architecture | `C03-F1`, `C03-F2`, `C03-F3a`, `C03-F3b`, `C03-F3c`, `C03-F4`, `C07-F1`, `C07-F2`, `C07-F3` |
| 2 | Incomplete registry, write failure, damaged parse, unfaithful durable copy, evidence that cannot be corroborated -> BLOCKED | `C03-U0`, `C03-U1`, `C03-U2`, `C03-U3`, `C03-U4`, `C03-U5`, `C07-U1`, `C07-U2`, `C07-U3`, `C07-U4`, `C07-U5`, `C07-U6`, `C07-U7` |
| 3 | A corroborated REGISTERED without FORKED -> FAIL; BLOCKED if integrity cannot be proven | `C03-F2`, `C03-U2`, `C03-U3` |
| 4 | A seq gap or an append failure alone is never a proof of FAIL | `C03-U2`, `C03-U3` |
| 5 | Positive evidence together with evidence damage: FAIL only if the witnesses of the fired rule are intact | `C03-F1`, `C03-F2`, `C03-F3a`, `C03-F3b`, `C03-F3c`, `C03-F4`, `C03-U2` |
| 6 | PASS needs every necessary process-evidence and integrity condition at once | `C03-pass_when`, `C07-pass_when`, `C16` |
| 7 | Damage to the durable copy must never produce a wrong PASS or a wrong FAIL: it only prevents PASS and makes the disk-dependent checks UNEVALUABLE | `C03-U2`, `C03-pass_when` |
| 8 | A gate pass proven by independent credible evidence without a valid registration -> FAIL; a pass that cannot be confirmed, or contradicting witnesses -> BLOCKED | `C03-F3c`, `C03-U5`, `C07-U4`, `C07-U6`, `C07-U7` |
| 9 | A run is closed only by a valid, published g0_closed.json bound to the verified summary and evidence; the existence of g0_summary.json closes nothing; exit code 0 or 1 is returned only after the marker was published and verified, otherwise 3 | `G0-C01`, `P6`, `P7`, `CL-02`, `CL-04`, `CL-05`, `CL-06`, `CL-11`, `CL-13`, `CL-16` |
| 10 | The closure marker is not proof that any process has exited; a valid marker with a live 'g0_run.py' process or a MANUAL_DISPOSITION_REQUIRED.json is BLOCKED | `G0-C01`, `CL-20`, `CL-21`, `CL-22` |

**FAIL 的归因：** 本判据下产生的每一个 FAIL 都是 **G0 台架 / 协议失败**，摘要必须写明 `fail_scope = 'G0 bench/protocol failure; not evidence about the Mythos model architecture'`；不得归因于 Mythos 模型架构、R3 或 Parcae。

## 3. 决策登记（拟由负责人批准的决策）

前 9 项是 V4 决策，**逐字不变**（DD-1…DD-5 等不被 V5 改变）；后 6 项是 V5 的结案决策。**它们是拟由项目负责人批准的决策，不是已完成的真实验证**：ChatGPT 与 Grok 的意见是项目负责人转述的**审核意见**（静态设计审查），两位审核者的原文**不在本任务的会话中**；「来源」一栏标明每项决定是任务文本明确写出的（stated），还是规范制定者推出、需要审核者确认的（derived）。

| ID | 主题 | 基线 | 规则 | 来源（derivation）：依据 | 状态 |
|---|---|---|---|---|---|
| `F-20/M-1` | durable-copy fidelity | disk_faithful compares (seq, kind, node_id) triples only | whole canonical record comparison; C03-U2 with a fidelity report | stated：stated in the task text of G0-V4-SPEC-001 (full canonical JSON record comparison instead of the triples) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `M-2` | disk-dependent checks | C04 C05 C11 C13 read the durable copy unconditionally (limitation L-2) | when the durable copy is not faithful, C04 C05 C11 C13 are UNEVALUABLE; violations proven by the ledger or by independent witnesses are not cancelled by damage to other fields | stated：stated in the task text (choose M-2; ledger or independent proof stays FAIL) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `DD-1` | ledger design | the ledger keeps the full records | retained; the ledger is the first-hand witness for what the writer did and is itself checked against the durable copy | derived：implied by the task text ('memory ledger ... cannot be cancelled'; whole-record comparison against the ledger) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `DD-2` | hole rule when the durable copy is damaged elsewhere | F2 relies on the ledger only | retained: F2 needs a clean writer and no foreign lines, and does not need a faithful durable copy | stated：stated in the task text ('a violation already reliably proven by the ledger ... is not cancelled automatically by damage of other disk fields') | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `DD-3` | failed release write while the child passed the gate | C07-F3: FAIL | UNEVALUABLE (C07-U6): the witnesses contradict each other. Exception kept as FAIL (C07-F3): a FIRST_ACTION earlier than the first recorded attempt, because no recorded write can explain it | derived：task text: 'cannot confirm the pass behaviour or the witnesses contradict each other: BLOCKED' | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `DD-4` | gate passed but no release attempt recorded | BLOCKED if RELEASED is in the ledger, FAIL (C03-F3) if not | UNEVALUABLE (C07-U4, C03-U5) in both cases: the pass cannot be confirmed | derived：task text: same sentence as DD-3 | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `DD-5` | child passed the gate although the REGISTERED append failed | ambiguous (F3 text vs precedence text) | FAIL (C03-F3c) when the pass is proven by independent credible evidence (successful release write + the child's FIRST_ACTION, in order); an append failure or seq gap alone is BLOCKED | stated：stated in the task text (append failure or gap only: BLOCKED; independent credible proof of a gate pass without valid registration: FAIL) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `F-21` | evidence saving and judging order | three mutually exclusive statements | pipeline P0-P7 | stated：stated in the task text (P0-P7 in this order, no default=str, exclusive write, BLOCKED exit 3 on any failure) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `F-22` | C03-F3 and writer_clean | contradictory prose | one machine-readable requirements table | stated：stated in the task text (machine-readable condition table; no contradictory writer_clean text) | PROPOSED_V4_DECISION_PENDING_OWNER_APPROVAL |
| `F-23` | summary existence is not closure | V4: a run directory with g0_summary.json is treated as closed | closure marker g0_closed.json created after the evidence and summary were saved and verified; preflight requires a valid marker bound to both files | stated：stated in the task text of G0-V5-CLOSEOUT-SPEC-001 (Grok proposed g0_closed.json, ChatGPT agreed with the distinctions) | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |
| `CL-A` | atomic exclusive publication | none | temporary file with O_EXCL, fsync, verify, os.link to the final name (EEXIST means never replace), directory fsync, verify; no rename / replace / direct write | derived：derived by the specifier from the task text's request to research the smallest atomic exclusive publication scheme without overwriting; os.link was chosen because it is standard library, atomic and exclusive (alternatives in closure.publication.why_not_*); reviewers to confirm | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |
| `CL-B` | handling of an unsynced or unconfirmed closure | none | a published valid marker is judged by preflight on what the files are (CLOSED_OK if all bindings hold); the process exits 3 and prints G0-CLOSE-UNCONFIRMED; the outcome is reported as BLOCKED unless exit status, absence of G0-CLOSE-* markers and read-back agree (reporting_rule) | derived：derived by the specifier from the task text (file sync failure, crash after publication, re-preflight); reviewers to confirm | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |
| `CL-C` | closure is not process-exit proof | none | the marker has process_exit_proof = false; G0-C01 evaluates live 'g0_run.py' processes and MANUAL_DISPOSITION_REQUIRED.json independently of the marker | stated：stated in the task text (the closure marker must not be taken as independent proof that the original process exited) | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |
| `CL-D` | preflight accepts a valid marker of any recorded verdict | V4 accepted any run with a summary | a valid marker with recorded_verdict PASS, FAIL or BLOCKED closes the run; the verdict decides nothing about closure | derived：derived by the specifier (V4 C01 required a closed run, not a PASS); reviewers to confirm | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |
| `CL-E` | the temporary name is never deleted | V4: no unlink of an existing file | g0_closed.json.tmp stays next to the marker; a byte-identical temporary file is tolerated by preflight, any other content is STRAY_CLOSURE_FILE | derived：derived by the specifier to keep V4's no-delete rule; reviewers to confirm | PROPOSED_V5_DECISION_PENDING_OWNER_APPROVAL |

## 4. 输入与环境

与 V4 相同：CPU、Python 3.13.16 且以 `python3 -B` 运行、Linux（当前内核 6.18.44-fc-v165）、仅标准库；无 cgroup、无 proc connector、无网络、无 GPU。被测代码：`bench/`（不改动）及 `gate_g0/{g0_auth,g0_judge,g0_run}.py`。

## 5. 过程（固定，不可参数化）

1. **授权与预检（不启动进程，只读）：** 加载并验证与 **V5** 文件哈希绑定的单次授权；S0 预检：对证据根下**每个以 `g0_` 开头的条目**按 §8.4 的规则 CL-01…CL-23 判定「已结案」——有合法的 `g0_closed.json` 并绑定经哈希核对的摘要与证据、无人工处置文件；**摘要文件存在不算结案**；另外无带标记 `g0_run.py` 的存活非僵尸进程（观察者及其祖先除外；与结案标记**独立**评估）、观察者无子进程、`/proc` 枚举完整、`run_id` 唯一、解释器与信号配置符合 C01。预检不干净时不 fork、不消耗授权。
2. **目录与授权消耗：** `evidence/` 若不存在则由本次运行非递归创建（0755），否则须是真实目录、非符号链接、属当前有效 uid、不可被组/其他写；运行目录与授权消耗目录排他创建，不覆盖任何既有目录或文件；失败 ⇒ BLOCKED，错误尽可能保存。预检干净后、fork **之前**排他创建授权消耗标记。写 `RUN_START`；安装守卫：拦截并记录所有 `kill / killpg / pidfd_send_signal / raise_signal / pthread_kill / exec* / spawn* / system / popen / subprocess`，`fork` 计数且最多放行 1 次（并记录返回的 pid），`waitpid` 只放行等于那一个子进程的正 pid；守卫对放行字节的每一次写入记录 `mono_before`、`mono_after` 与结果；失败的写入被记录，不被丢弃。
3. **一次** `spawn_direct`（`hold_release=True`）：写 `INTENT` → `fork` → 子进程在门上阻塞 → 观察者读 `/proc` 指纹、开 pidfd、校验 `ppid`/起始时间 → 写 `REGISTERED`。观察者在 `hold_before_release_s`（0.3 s）内持续排空控制通道；**保持期结束时拍 S1 快照**。
4. **放行：** 写 `RELEASED` → **放行尝试**（向门写 `R`，守卫记录尝试与结果）→ 写入成功后发 `SPEC` → 子进程读 `SPEC`、发 `FIRST_ACTION`（**通过门控**）、发 `READY` → **S2 快照**。写入失败（如 `EPIPE`）⇒ 运行停止，BLOCKED，除非证据证明了违规。
5. 观察者经**控制通道**发 `EXIT` 消息（不是信号）；子进程 `_exit(0)`。→ **S3 快照**：在任何 wait 调用之前确认 pidfd 可读且 `/proc` 状态为 `Z`。
6. **回收**：对那一个具体 pid 做 `waitpid`（可为非阻塞轮询，受 `reap_deadline_s` 约束，不得无界等待）→ 记录退出码 → 等 `/proc/<pid>` 消失 → **S4 快照**。
7. `final_cleanup`（仅在子进程已退出**且已回收**之后）→ 令牌扫描（仅诊断）→ 写 `RUN_END` →（此后按 §7 的流水线 **P0–P7**：取账本与写入器序号 → 解析登记文件 → 严格序列化 → 排他写入并 fsync → 读回并核对字节与 SHA-256 → 校验类型 → **只对读回的证据裁决** → 保存并核对摘要 → **发布并核对结案标记 `g0_closed.json`（§8）** → 返回已发布标记所记录的退出码）。
8. **异常与提前中止：** 总时长在运行中检查；超时或异常：**不发信号**，写 `RUN_END(cleanup_confirmed=false)`，保存证据，列出仍存活进程的已验证身份并写 `MANUAL_DISPOSITION_REQUIRED.json`；裁决 BLOCKED，除非证据证明了违规。摘要、证据与结案标记**只写入本进程创建的运行目录**，并遵守 §7 与 §8 的不覆盖规则。已写出 `MANUAL_DISPOSITION_REQUIRED.json` 时，即使结案标记已合法发布，该运行目录仍阻止后续运行（CL-20）。

## 6. 判据（冻结；`g0_criteria_v5.json` 为准）

「与 V4」：IDENTICAL = 文字与 V4 逐字相同；MODIFIED = 内容改变（`note` 说明改变了什么）。

| ID | 名称 | 失败类别 | 与 V4 | 内容 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED | MODIFIED | no unresolved earlier run and a clean process / interpreter state. (1) EARLIER RUNS: every entry of the evidence root whose name starts with 'g0_' is a closed run in the sense of closure.preflight (rules CL-01..CL-20 do not match it): a valid g0_closed.json that binds a g0_summary.json and a g0_evidence.json which preflight reads and verifies by size, SHA-256 and field bindings, with the same run id, criteria id and criteria hash, and no MANUAL_DISPOSITION_REQUIRED.json in the run directory; the mere existence of g0_summary.json never makes a run closed; no MANUAL_DISPOSITION_REQUIRED.json in the evidence root; the evidence root can be listed completely. (2) PROCESSES: no live non-zombie process, other than this observer and its ancestors, whose command line contains the marker 'g0_run.py' (this marker is the definition of the V1 term 'bench token'); a valid closure marker is not proof that an earlier run's processes have exited, so this condition is evaluated independently of (1); observer has 0 children; /proc enumeration complete. (3) run id unique (its run directory does not exist before this run creates it); Python is 3.13.16 started with -B; SIGCHLD is not ignored; pidfd_open and socket.send_fds are available. Any failure -> BLOCKED, no fork, no authorization consumed; the matching closure rules are listed as '<entry name>:<REASON>' in evidence.preflight.unresolved_prior |
| `G0-C02` | authorization_and_bindings | BLOCKED | IDENTICAL | a valid single-use G0 authorization bound to THIS criteria file (V2) was consumed: its consumption marker is created exclusively after a clean preflight and BEFORE the fork (a run whose preflight failed consumes nothing); git head, E1-A prereg, G0 criteria, G0 prereg text, bench code and G0 code hashes equal the authorized values at the start AND again at the end |
| `G0-C03` | registration_sequence_and_integrity | FAIL | IDENTICAL | registration-file order, protocol and integrity, decided by checks.G0-C03.rules. FAIL when reliable first-hand evidence (the writer's own ledger and/or independent guard and child evidence, never the durable copy) proves a violation of the fixed G0 record sequence or of the registration protocol. UNEVALUABLE -> BLOCKED when the registry is incomplete, an append failed, the durable copy is not faithful (any difference in any field of any record, a lost, foreign, torn or corrupt line) or carries foreign lines, a pass of the gate cannot be confirmed or the witnesses contradict each other, or the run stopped early without proof of a violation. PASS only on a completed run whose ledger shows exactly the fixed sequence AND whose durable copy is faithful to the ledger. A gap in seq numbers or a failed append is by itself never a proof of violation. Every unfaithful difference is listed in the C03 report (rules.fidelity_report). A FAIL is a G0 bench/protocol failure; it is not evidence about the Mythos model architecture |
| `G0-C04` | identity_registered_before_release | FAIL | IDENTICAL | REGISTERED pid/starttime equal the /proc fingerprint read while the child was held; the child's ppid is the observer; pid equals the pid returned by fork Evaluated only when the durable copy is faithful to the ledger (G0-C03 definitions.disk_faithful); otherwise UNEVALUABLE, and the C03 fidelity report lists the differences. |
| `G0-C05` | no_action_before_release | FAIL | IDENTICAL | while REGISTERED but unreleased, observed at the END of the hold (snapshot S1, taken after the observer drained the control channel for hold_before_release_s; messages are counted cumulatively over the whole hold): the child is blocked (state S), sent no message, kept the observer's sid/pgrp; its FIRST_ACTION is not earlier than the RELEASED record Evaluated only when the durable copy is faithful to the ledger (G0-C03 definitions.disk_faithful); otherwise UNEVALUABLE, and the C03 fidelity report lists the differences. |
| `G0-C06` | gate_descriptor_hygiene | FAIL | IDENTICAL | held (snapshot S1, end of the hold): child descriptors are a subset of {0,1,2,gate read end,control socket}, the gate pipe appears exactly once and read-only (no write-capable descriptor); after release (snapshot S2): no descriptor refers to the gate pipe |
| `G0-C07` | release_only_after_registration | FAIL | IDENTICAL | release evidence. The release of the gated child is judged by three separate facts: the ATTEMPT (guard.release_writes entry with mono_before), the SUCCESS (the same entry has result 'ok', returned 1 and mono_after) and the GATE PASS (the child's own FIRST_ACTION). PASS: exactly one attempt, it succeeded, and REGISTERED <= RELEASED <= mono_before <= mono_after <= child FIRST_ACTION (REGISTERED and RELEASED times taken from the ledger). FAIL (evidenced): REGISTERED or RELEASED later than the attempt's mono_before; more than one release write; the child's FIRST_ACTION earlier than the first attempt's mono_before (the child acted before the release was even attempted). UNEVALUABLE -> BLOCKED: no release attempt recorded and no gate pass; the attempt failed and the child did not pass; the write succeeded but the child did not pass; the child passed the gate but no attempt is recorded (the pass cannot be confirmed); the child passed the gate although every recorded write failed (the witnesses contradict); the child's FIRST_ACTION lies between mono_before and mono_after (the times contradict); required times missing. A time taken before the write is never evidence that the byte was written |
| `G0-C08` | exit_observed_unreaped | BLOCKED | IDENTICAL | after the EXIT message and before any wait call the child was observed exited-but-unreaped: pidfd readable and /proc state Z with ppid = observer |
| `G0-C09` | reap_by_specific_pid | BLOCKED | IDENTICAL | waitpid on that specific pid (non-blocking polls bounded by reap_deadline_s are allowed; exactly one call returns that pid, every other call on it returns 0) returned that pid; afterwards /proc/<pid> is absent (or carries a different starttime), waited for at most reap_deadline_s; times EXITED_UNREAPED < REAPED <= PROC_GONE |
| `G0-C10` | exit_status_zero | FAIL | IDENTICAL | the reaped exit code is 0 (normal exit after the EXIT message) |
| `G0-C11` | process_budget | FAIL | IDENTICAL | exactly one fork in the whole run; at every snapshot the observer has at most one child and the child has no child; the registry contains exactly one node and no ticket Evaluated only when the durable copy is faithful to the ledger (G0-C03 definitions.disk_faithful); otherwise UNEVALUABLE, and the C03 fidelity report lists the differences. |
| `G0-C12` | zero_signals | FAIL | IDENTICAL | no kill/killpg/pidfd_send_signal/raise_signal/pthread_kill/exec/spawn/subprocess call was attempted (guard violations empty) and every cleanup kill entry is 'already_exited' |
| `G0-C13` | cleanup_and_no_residue | BLOCKED | IDENTICAL | final cleanup ok, run set consistent, DEAD record with basis present, observer has no child, diagnostic token scan finds no unregistered live process, no snapshot reported incomplete /proc enumeration, RUN_END present with cleanup_confirmed true (on any abnormal stop the run writes RUN_END with cleanup_confirmed false, which fails this check) Evaluated only when the durable copy is faithful to the ledger (G0-C03 definitions.disk_faithful); otherwise UNEVALUABLE, and the C03 fidelity report lists the differences. |
| `G0-C14` | observer_descriptor_baseline | BLOCKED | IDENTICAL | the observer's open descriptor count at S5 equals S0 |
| `G0-C15` | time_bounds | BLOCKED | IDENTICAL | total duration <= max_seconds, measured at the end AND enforced while the run is in progress (checked at every phase boundary and loop iteration; a breach records the deadline hit 'total' and stops the run); no phase deadline was hit (ready, exit, reap, proc_gone, total) |
| `G0-C16` | evidence_complete | BLOCKED | IDENTICAL | evidence completeness and type: every field listed in evidence_schema.fields is present with its declared type in the evidence AS READ BACK by pipeline stage P3 from g0_evidence.json (bytes and SHA-256 verified against what was written; JSON types; no NaN; bool is never accepted as int or number; a nullable field may be null; a present field of the wrong type counts as missing) and evidence_schema equals 'e1a-gate-g0-evidence-4'. The required field set is that of V3 (the schema id changes so that V3 and V4 evidence cannot be confused). Consistency between the registry witnesses is judged by G0-C03, not by this check |
| `G0-C17` | no_unexplained_error | BLOCKED | IDENTICAL | no exception, no abort reason, exit-code policy consistent with the verdict |

### 6.1 `G0-C03`：见证、定义与规则（与 V4 逐字相同）

**三类见证：**
* **ledger**：evidence.reg_memory_records: what the writer appended successfully, in order. First-hand for what the observer did; unaffected by damage to the file.
* **durable_copy**：evidence.reg + evidence.reg_parse_info: the registry file as parsed. Used ONLY for the fidelity comparison (rule C03-U2), for the foreign-line test, and by the disk-dependent checks listed in witness_dependencies; never used to prove a violation or an absence.
* **independent**：evidence.guard (fork_calls, fork_pids, release_writes), evidence.events (first_action_mono), snapshots S1..S5: first-hand facts not derived from the registry.

**定义：**
* **completed_run**：evidence.exception is null AND evidence.aborted is null AND evidence.deadline_hits is empty
* **early_stop**：not completed_run
* **canon**：canon(record) = json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False) of the record as read back from JSON
* **writer_clean**：the seq values of the ledger are exactly 1..n AND evidence.reg_writer_seq == n (no append failed)
* **disk_faithful**：reg_parse_info has missing=false, unreadable=false, torn_tail=false, corrupt_lines=0 AND the durable copy has exactly as many records as the ledger AND canon(durable[i]) == canon(ledger[i]) for every i (whole record, every field, same order)
* **foreign_lines**：durable records whose (seq, kind, node_id) triple is absent from the ledger triples (a provenance test; an altered record with an unchanged triple is unfaithful, not foreign)
* **lifecycle_positions**：RUN_START=0, INTENT=1, FORKED=2, REGISTERED=3, RELEASED=4, DEAD=5; RUN_END is separate (always last); ABORTED is the alternative to REGISTERED and RELEASED
* **valid_record**：a ledger record of the required kind whose fields pass the type and value tests of C03-F1(d)
* **hole**：a position p in 0..5 absent from the ledger while a position q > p of the same lifecycle is present in the ledger; RUN_END does not count as a later record; an ABORTED record excuses the absence of REGISTERED and RELEASED
* **tail_absence**：every absent required record has a higher position than every present lifecycle record (nothing present follows an absence); an empty ledger is a tail absence
* **fork_proven**：guard.fork_pids is non-empty (the real fork returned a pid and the guard recorded it)
* **release_attempt**：guard.release_writes has an entry (mono_before recorded)
* **release_write_ok**：an entry of guard.release_writes has result 'ok', returned == 1 and a mono_after
* **gate_passed**：events.first_action_mono is a number (the child's own FIRST_ACTION message was received)
* **gate_pass_proven**：release_write_ok AND gate_passed AND exactly one release attempt AND events.first_action_mono >= mono_after of that write: two independent first-hand witnesses (the observer's guard and the child) agree, in order
* **gate_pass_unconfirmed**：gate_passed AND NOT gate_pass_proven (no recorded release attempt, every recorded write failed, more than one attempt, or the times contradict)

**FAIL 规则（先评估；每条只依赖 §6.1 需求表所列的见证）：**

| ID | 内容 |
|---|---|
| `C03-F1` | a violation visible in the ledger itself: (a) more than one RUN_START, RUN_END, or, for the node, more than one INTENT, FORKED, REGISTERED, RELEASED, ABORTED or DEAD; (b) the first occurrences violate the order RUN_START < INTENT < FORKED < REGISTERED < RELEASED < DEAD < RUN_END, a record precedes RUN_START, any record follows RUN_END, any record of the node follows its DEAD, or RELEASED and ABORTED both exist; (c) seq not strictly increasing; (d) a field of a present record has the wrong type or value: RUN_START needs run_id (non-empty string) and observer_pid (int, not bool); RUN_END needs the same run_id and cleanup_confirmed (bool); INTENT needs node_id (string) and creator (string); FORKED needs pid (int, not bool); REGISTERED needs pid and starttime (int, not bool); DEAD needs a non-empty basis; (e) RUN_END with cleanup_confirmed true while the node has no DEAD or has an ABORTED; (f) more than one node, or an INTENT whose creator is not 'O' (G0 allows exactly one node and no ticket) |
| `C03-F2` | a hole in the ledger, for example REGISTERED present while FORKED is absent, RELEASED present while REGISTERED is absent, FORKED present while INTENT is absent, any record except RUN_END present while RUN_START is absent: the fixed record sequence was not followed. Because no append failed and no foreign line exists, the missing record was never attempted |
| `C03-F3a` | fork_proven AND the ledger has no valid INTENT: the process was created without a durable intent. Needs a clean writer (otherwise the missing INTENT may be explained by the failed append and the result is BLOCKED, C03-U3) |
| `C03-F3b` | release_write_ok AND the ledger has no valid REGISTERED or no valid RELEASED: the release byte was written without a durable registration. Needs a clean writer (otherwise BLOCKED, C03-U3, unless C03-F3c applies) |
| `C03-F3c` | gate_pass_proven AND the ledger has no valid REGISTERED or no valid RELEASED: the child passed the gate without a valid registration. Applies even when an append failed or the seq has a gap, because the pass is proven by two independent first-hand witnesses and a failed append can explain the missing record but cannot make the pass compliant |
| `C03-F4` | a completed run whose ledger lacks any of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis), RUN_END, or contains an ABORTED record |

**UNEVALUABLE → BLOCKED 规则（仅当没有任何 FAIL 规则触发；报告第一条匹配的，列出全部匹配的）：**

| ID | 内容 |
|---|---|
| `C03-U0` | the evidence needed is missing or of the wrong type: reg_memory_records, reg_writer_seq, reg or reg_parse_info (a rule whose own evidence is missing simply cannot fire) |
| `C03-U2` | the durable copy is not faithful or carries foreign lines: file missing or unreadable, torn tail, corrupt line, lost line, extra line, or ANY difference in ANY field of ANY record between the durable copy and the ledger. The durable registry cannot be trusted, so the run cannot PASS and the disk-dependent checks are UNEVALUABLE. The C03 report lists every difference (rules.fidelity_report) |
| `C03-U3` | the writer failed: the ledger seq values are not exactly 1..n or reg_writer_seq != n (an append failed or a seq gap exists) and no fail rule fired. An append failure or a seq gap alone is never a FAIL |
| `C03-U5` | independent evidence indicates an action but a precursor record is missing or invalid and the proof condition of C03-F3a, F3b or F3c is not met: a pass of the gate that is unconfirmed (no recorded release attempt, failed or repeated or time-inconsistent writes), contradicting witnesses, or a single witness with an unclean writer |
| `C03-U1` | early_stop with tail_absence, writer_clean and a faithful durable copy: the lifecycle could not be completed, which proves nothing about the protocol (includes stopping before the fork: an empty ledger, or RUN_START and RUN_END(false) only) |
| `C03-U4` | any other combination that is not PASS (default: when no rule matches the check is UNEVALUABLE, never PASS and never FAIL) |

**规则需求表（机器可读的唯一来源；`writer_clean` 的要求只在这里陈述）：**

| 规则 | needs_ledger | needs_writer_clean | needs_no_foreign_lines | needs_independent_evidence | needs_completed_run | relies_on_durable_copy |
|---|---|---|---|---|---|---|
| `C03-F1` | 是 | 否 | 否 | 否 | 否 | 否 |
| `C03-F2` | 是 | 是 | 是 | 否 | 否 | 否 |
| `C03-F3a` | 是 | 是 | 是 | 是 | 否 | 否 |
| `C03-F3b` | 是 | 是 | 是 | 是 | 否 | 否 |
| `C03-F3c` | 是 | 否 | 是 | 是 | 否 | 否 |
| `C03-F4` | 是 | 是 | 是 | 否 | 是 | 否 |

* true = required; false = explicitly NOT required; every FAIL rule has relies_on_durable_copy false except through the no-foreign-lines test, which can only suppress a rule, never create a FAIL
* writer_clean is required by C03-F2, F3a, F3b and F4 and is explicitly not required by C03-F1 and F3c; this table is the only statement of these requirements

**保真报告（`fidelity_report`）：** whenever disk_faithful is false the C03 result carries a report, so that the unfaithfulness is evidence and not a bare verdict 条目类型：LOST (ledger record absent from the durable copy)；FOREIGN (durable record whose triple is not in the ledger)；ALTERED (same triple, different fields; the names of the differing fields)；PARSE (missing, unreadable, torn tail, corrupt lines: the counts)；COUNT (record counts differ)。字段：type, index, seq, kind, node_id, fields (ALTERED only), ledger_canon_prefix and durable_canon_prefix (first 200 characters of canon)。at most the first 50 entries are listed, with the total count

* **PASS：** completed_run AND writer_clean AND disk_faithful AND the ledger contains exactly once each of RUN_START, INTENT, FORKED, REGISTERED, RELEASED, DEAD (with basis) and RUN_END, in that order, with valid fields, no ABORTED and no second node AND no fail rule fired. The VALUE of RUN_END.cleanup_confirmed is judged by G0-C13, not here
* **优先级：** The fail rules are evaluated first, each only on the witnesses it relies on (rules.requirements). Damage to the durable copy never suppresses a fail rule whose witnesses are intact: a violation proven by the ledger or by independent evidence stays FAIL, and its credibility is reported as first-hand with the damage listed. Damage that undermines a rule's own witness suppresses that rule as stated in rules.requirements. If no fail rule fires, the first matching unevaluable rule is reported and all matching ones are listed
* **seq_gap**：a gap in the numbering of the durable copy or of the ledger is never by itself a proof of violation: it means a failed append (C03-U3) or a lost line (C03-U2)
* **registered_without_forked**：REGISTERED present while FORKED is absent: FAIL (C03-F2) when the writer is clean and no foreign line exists; BLOCKED when integrity cannot be proven (C03-U3, C03-U0, C03-U2 with foreign lines)
* **positive_evidence_with_damage**：decided by rules.requirements: a violation proven by the ledger or by independent evidence survives damage to the durable copy; an inference from the durable copy never survives damage to the durable copy
* **append_failure_vs_gate_pass**：an append failure or seq gap alone: BLOCKED. Independent credible proof that the child passed the gate without a valid registration: FAIL (C03-F3c). A pass that cannot be confirmed, or witnesses that contradict each other: BLOCKED (C03-U5)
* **fidelity_scope**：the durable copy is compared with the ledger on whole canonical records; an alteration of any field of any record is detected. The comparison cannot tell which of the two witnesses is wrong; it only makes the disagreement visible and refuses to let either decide a PASS or a durable-copy-based FAIL

### 6.2 `G0-C07`：放行证据（与 V4 逐字相同）

**FAIL 规则：**

| ID | 内容 |
|---|---|
| `C07-F1` | ledger REGISTERED.mono > ledger RELEASED.mono, or ledger RELEASED.mono > release_writes[0].mono_before (the release was attempted before the RELEASED record existed) |
| `C07-F2` | more than one entry in guard.release_writes |
| `C07-F3` | release_writes is non-empty AND gate_passed AND events.first_action_mono < release_writes[0].mono_before (the child acted before the release was even attempted: no recorded write can explain it) |

**UNEVALUABLE → BLOCKED 规则：**

| ID | 内容 |
|---|---|
| `C07-U1` | no release attempt is recorded and the child has not passed the gate (the run stopped before the release) |
| `C07-U2` | the attempt failed (result 'error', for example EPIPE) and the child did not pass the gate |
| `C07-U3` | the write succeeded but the child did not pass the gate (no FIRST_ACTION) |
| `C07-U4` | the child passed the gate but no release attempt is recorded (the pass cannot be confirmed; the instrumentation and the child disagree), whether or not RELEASED is in the ledger |
| `C07-U5` | a time needed by the rules is missing (ledger REGISTERED or RELEASED, mono_before, mono_after, first_action_mono) |
| `C07-U6` | the child passed the gate although every recorded release write failed (the witnesses contradict each other) |
| `C07-U7` | the child passed the gate, a write succeeded, and mono_before <= events.first_action_mono < mono_after (the times contradict: the child cannot have received SPEC before the write returned) |

* **PASS：** exactly one release_writes entry, result 'ok', returned 1, and REGISTERED.mono <= RELEASED.mono <= mono_before <= mono_after <= events.first_action_mono

### 6.3 M-2：依赖持久副本的检查（与 V4 逐字相同）

* a check that reads fields of the durable copy is UNEVALUABLE when disk_faithful is false; a check that reads only the ledger, the independent evidence or the snapshots is not affected by the durable copy

| 检查 | 读取的持久副本字段 |
|---|---|
| `G0-C04` | REGISTERED.pid, REGISTERED.starttime (durable copy) |
| `G0-C05` | RELEASED.mono (durable copy) |
| `G0-C11` | INTENT.creator, INTENT.node_id (durable copy) |
| `G0-C13` | DEAD.basis, RUN_END.cleanup_confirmed (durable copy) |

### 6.4 `G0-C16`：证据模式

* 版本标识：`evidence_schema` = `e1a-gate-g0-evidence-4`（字段集合与 V3、V4 相同；V5 只改了两处说明文字，见 §0）。
* 验证：performed once, at pipeline stage P4, on the evidence AS READ BACK at stage P3 (not on the in-memory evidence): a present field of the wrong type counts as missing; bool is never accepted as int or number; nullable fields may be null; extra keys are ignored; the judge (P5) receives only the read-back evidence
* 序列化：strict: json.dumps(evidence, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False) with no default= argument (pipeline stage P1); there is no json.loads(json.dumps()) round trip in memory

| 字段路径 | 类型 | 可为 null | 使用它的检查 | 说明 |
|---|---|---|---|---|
| `evidence_schema` | string | 否 | C16 | must equal 'e1a-gate-g0-evidence-4' |
| `run_id` | string | 否 | C03 C16 |  |
| `auth_expected` | object[6 hex strings: git_head prereg_sha256 g0_criteria_sha256 g0_prereg_sha256 bench_code_sha256 g0_code_sha256] | 否 | C02 |  |
| `bindings_start` | object[same 6 keys] | 否 | C02 |  |
| `bindings_end` | object[same 6 keys] | 否 | C02 |  |
| `auth_consumed` | bool | 否 | C02 |  |
| `observer` | object{pid:int, sid:int, pgrp:int} | 否 | C04 C05 C08 |  |
| `preflight` | object{ok:bool, problems:list, children:int, token_residue:list, unresolved_prior:list, enumeration_problems:object, run_id_unique:bool, fd_count:int, total_procs:int} | 否 | C01 | V5: unresolved_prior entries are '<entry name>:<REASON>' (closure.preflight rules) or 'MANUAL_DISPOSITION_REQUIRED.json' / ':<REASON>' for global rules; type and field set unchanged |
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

## 7. 证据保存、裁决与结案流水线

* the verdict is computed only from evidence that was written, fsynced, read back and byte-verified; nothing is silently converted; nothing is overwritten; every failure is BLOCKED with exit code 3; a run is closed only by a published and verified g0_closed.json bound to the verified evidence and summary; exit code 0 or 1 is returned only after the closure marker was published and verified (P7)

| 阶段 | 名称 | 操作 | 失败 ⇒ |
|---|---|---|---|
| `P0` | construct | assemble the evidence dictionary E in memory, including evidence_schema; capture the ledger (a copy of RegWriter.records) and reg_writer_seq after the last registry write and before the registry file is parsed; parse the registry file into reg and reg_parse_info | an exception is handled by the abnormal path of the procedure (no signal, RUN_END false, MANUAL_DISPOSITION where a process may live); the pipeline continues with what exists |
| `P1` | strict serialisation | B = json.dumps(E, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8'); NO default= argument, so nothing is silently converted (no default=str); sha256(B) is computed | TypeError, ValueError or RecursionError (a non-JSON value, NaN) -> BLOCKED; nothing is written; stderr: G0-EVIDENCE-UNSAVED run_id=<id> stage=P1 reason=<text> |
| `P2` | exclusive write, fsync | fd = os.open(<run_dir>/g0_evidence.json, O_WRONLY\|O_CREAT\|O_EXCL, 0o644) in the run directory created by this process; write ALL bytes (loop until complete); os.fsync(fd); os.close(fd); fsync the run directory | the file exists (another run or a previous attempt: never overwritten, never reused), any OSError, a short write that cannot be completed, an fsync failure -> BLOCKED; a partially written file created by this process is preserved, not deleted; stderr: G0-EVIDENCE-UNSAVED run_id=<id> stage=P2 sha256=<sha256(B)> partial=<true\|false> reason=<text>; best effort: an exclusive g0_blocked_<run_id>.json note in the run directory or the validated evidence root (its own failure only adds a stderr line) |
| `P3` | read back and verify | open the file again, best effort os.posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED), read all bytes B2; require a regular file, len(B2) == len(B), sha256(B2) == sha256(B); E2 = json.loads(B2.decode('utf-8'), parse_constant=<reject>) | differing bytes or hash, a parse error, a non-regular file -> BLOCKED; stderr: G0-EVIDENCE-UNVERIFIED run_id=<id> stage=P3 written_sha256=<h> read_sha256=<h> |
| `P4` | validate types | validate E2 against evidence_schema.fields (presence, type, nullable, bool never int); the result feeds G0-C16 and the UNEVALUABLE state of the checks that need the failing fields | does not stop the pipeline: G0-C16 fails (BLOCKED class); verdict BLOCKED unless an evidenced FAIL exists on intact witnesses |
| `P5` | judge the read-back evidence | the judge receives E2 only; it never sees E; verdict, exit code and per-check results are computed; the C03 fidelity report is part of the result | an exception in the judge -> BLOCKED; stderr: G0-JUDGE-ERROR run_id=<id>; no summary is written and no closure marker is created, so the next preflight finds the run directory without a valid g0_closed.json and refuses to start (closure.preflight CL-02) |
| `P6` | save and verify the summary | S = {run_id, criteria_id, criteria_sha256, evidence_sha256 (= sha256(B2)), verdict, exit_code, checks, c03_fidelity_report, fail_scope (when FAIL), pipeline: {P0..P5 results}}; strict serialisation as in P1; exclusive write + fsync + directory fsync as in P2; read back and verify bytes, hash and parse as in P3; the bytes read back (Bs2) and their SHA-256 are kept for the closure marker (P7). Writing g0_summary.json is NOT closing the run | write failure, read-back mismatch or parse failure -> the verdict is NOT recorded: BLOCKED, exit code 3; stderr: G0-SUMMARY-UNSAVED run_id=<id> verdict=<computed verdict> evidence_sha256=<h> reason=<text>. The evidence file remains and a partial or unverified g0_summary.json may remain; neither is evidence of closure: no closure marker is created, so the next preflight sees a run directory without a valid g0_closed.json and refuses to start (closure.preflight CL-02), whatever g0_summary.json contains |
| `P7` | publish the closure marker and exit | closure.publication steps K1..K7: build g0_closed.json from the read-back evidence and summary hashes, write it to g0_closed.json.tmp (O_EXCL), fsync, verify, publish it with os.link under g0_closed.json (exclusive, atomic), fsync the run directory, verify the published file, then exit with recorded_exit_code (PASS 0, FAIL 1, BLOCKED 3). Only here may exit code 0 or 1 be returned; any uncaught exception anywhere in the pipeline is caught and mapped to 3 | K1..K4 fail: nothing is published; stderr G0-CLOSE-UNPUBLISHED ...; exit 3. K5, K6 or an exception after K4: the marker stays; stderr G0-CLOSE-UNCONFIRMED ...; exit 3. The saved evidence, summary and marker are never altered (closure.publication.failures) |

**失败时保留的证据：**
* **P1**：nothing is on disk; stderr names the stage; the run directory, registry file and MANUAL_DISPOSITION_REQUIRED.json (if any) remain
* **P2**：a partial g0_evidence.json if one was created; registry; stderr with sha256(B) so that B can be recomputed only if E is reproduced; optional g0_blocked note
* **P3**：the saved evidence file as read (not repaired); stderr with both hashes
* **P5**：the verified evidence file
* **P6**：the verified evidence file; any partial or unverified g0_summary.json as it is (not repaired, not evidence of closure); stderr with the computed verdict and evidence_sha256
* **P7**：evidence, summary and registry as saved; a partial or complete g0_closed.json.tmp; the published g0_closed.json if K4 returned; stderr with the G0-CLOSE-* marker and the three hashes

* **耐久性限度：** fsync of the file and of the directory is requested and its failure is BLOCKED, and the read-back is verified byte for byte, but a read-back served from the page cache does not prove that the medium holds the bytes (best effort posix_fadvise DONTNEED reduces this); when durability cannot be guaranteed the unsaved state is marked on stderr and the verdict is BLOCKED; the same holds for the closure marker: fsync of the temporary file and of the directory is requested and its failure is reported (G0-CLOSE-UNPUBLISHED / G0-CLOSE-UNCONFIRMED), but a successful verification does not prove that the medium holds the bytes
* **不覆盖规则：** no file of another run is ever opened for writing; g0_evidence.json, g0_summary.json and g0_closed.json.tmp are created with O_EXCL only; g0_closed.json is created only by os.link of the verified temporary file and only when the final name does not exist; there is no rename, replace, truncate or unlink of an existing file anywhere in G0

## 8. 结案标记 `g0_closed.json`（F-23）

### 8.1 问题与原则

* **V4 的缺陷：** V4 P6 creates g0_summary.json with O_EXCL and then writes, fsyncs and reads it back. When the write, the fsync or the read-back fails, a partial or unverified g0_summary.json can remain in the run directory. The preflight of g0_run.py (lines 224-225) and the V4 wording of G0-C01 test only whether g0_summary.json EXISTS, so that run directory would be treated as closed and a new real G0 run would not be refused.
* **V5 原则：** a run is closed if and only if g0_closed.json exists, is valid, and binds a g0_summary.json and a g0_evidence.json that preflight reads and verifies by hash. The existence of g0_summary.json (or of g0_evidence.json) never closes a run. The marker is created only after the evidence and the summary have been saved, read back and byte/SHA-256 verified, and it is published atomically and exclusively: the final name never exists with partial content. Closed is a statement about files; it is NOT proof that the run's processes have exited.
* 结案标记的**四个不同层面**：**存在性**（文件是否存在——本身不说明任何事）、**内容有效性**（§8.2 的严格验证 + §8.4 的绑定核对）、**原子发布**（§8.3：最终名字只会以完整内容出现）、**真实进程终止**（标记**不**证明；由 C01 的存活进程扫描与 `MANUAL_DISPOSITION_REQUIRED.json` 独立判定）。

### 8.2 标记的机器可读结构（schema `e1a-gate-g0-closed-1`）

* 序列化：strict, exactly as evidence_pipeline P1: json.dumps(C, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('utf-8'), no default= argument, no trailing newline, no indentation; the file contains exactly these bytes
* 验证：a file is a VALID marker only if: it is a regular file (lstat; not a symlink) of 1..4096 bytes; its bytes decode as UTF-8 and parse as JSON with duplicate object keys, NaN and Infinity rejected; the parsed value is an object with exactly the keys of fields (no missing key, no extra key); every value has its type (bool is never an int); every const field has its value; hex fields match ^[0-9a-f]{64}$; recorded_verdict and recorded_exit_code are one of the pairs (PASS, 0), (FAIL, 1), (BLOCKED, 3); and the file's bytes are identical to the strict serialisation of the parsed object (canonical form)
* 大小上限：4096 字节。

| 字段 | 类型 | 可为 null | 固定值 | 说明 |
|---|---|---|---|---|
| `closed_schema` | string | 否 | `e1a-gate-g0-closed-1` | format version of the closure marker |
| `run_id` | string | 否 | — | matches ^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$, starts with 'g0_', and equals the run directory's name, summary.run_id and evidence.run_id |
| `criteria_id` | string | 否 | `E1A-GATE-G0-CRITERIA-V5` | equals summary.criteria_id and the criteria id of the running tool |
| `criteria_sha256` | string[64 lowercase hex digits] | 否 | — | SHA-256 of g0_criteria_v5.json as bound by the authorization; equals summary.criteria_sha256 and the criteria hash of the running tool |
| `evidence_sha256` | string[64 lowercase hex digits] | 否 | — | SHA-256 of the bytes of g0_evidence.json AS READ BACK at P3; equals summary.evidence_sha256 |
| `evidence_bytes` | int[>= 1] | 否 | — | length of those bytes |
| `summary_sha256` | string[64 lowercase hex digits] | 否 | — | SHA-256 of the bytes of g0_summary.json AS READ BACK at P6 |
| `summary_bytes` | int[>= 1] | 否 | — | length of those bytes |
| `recorded_verdict` | string in {PASS, FAIL, BLOCKED} | 否 | — | the verdict of the verified summary (summary.verdict) |
| `recorded_exit_code` | int in {0, 1, 3} | 否 | — | the exit code of the verified summary (summary.exit_code); PASS 0, FAIL 1, BLOCKED 3, bool is never accepted as int |
| `process_exit_proof` | bool | 否 | `False` | always false: the marker says nothing about whether any process of the run has exited |

### 8.3 原子排他发布（K0–K7）

* **方案：** The marker is built from the read-back bytes of the saved evidence and summary, written to a temporary name created with O_EXCL, fsynced, read back and verified there, published by link(2) under the final name (link fails with EEXIST when the final name exists, so nothing is ever replaced and the final name appears complete or not at all), then the directory is fsynced and the final name is read back and verified. The temporary name is never deleted by G0.
* **为什么不直接创建最终文件再逐步写入：** a file created under its final name and then written step by step is visible with partial content; any failure in between would look like a closure attempt to a later reader
* **为什么不用 rename / replace：** os.rename and os.replace silently replace an existing destination on POSIX; an exclusive 'rename if absent' needs renameat2(RENAME_NOREPLACE), which the standard library does not expose (V5 stays standard-library only)
* **为什么用 link：** os.link is standard-library, atomic and exclusive (EEXIST), publishes an already fsynced inode and needs no extra privileges; its cost is that the temporary name remains as a second name of the same inode, and the filesystem must support hard links

| 步骤 | 名称 | 操作 | 此步之后标记已发布 |
|---|---|---|---|
| `K0` | preconditions | P3 verified the evidence file (bytes B2, sha256(B2)) and P6 verified the summary file (bytes Bs2, sha256(Bs2), parsed S2); if any of P1..P3, P5, P6 failed, no marker is created and K1..K7 do not run | 否 |
| `K1` | build | C = {closed_schema, run_id, criteria_id, criteria_sha256, evidence_sha256 = sha256(B2), evidence_bytes = len(B2), summary_sha256 = sha256(Bs2), summary_bytes = len(Bs2), recorded_verdict = S2.verdict, recorded_exit_code = S2.exit_code, process_exit_proof = false}; Bc = strict serialisation of C; the pair (recorded_verdict, recorded_exit_code) is checked against the allowed pairs; C is validated with marker_schema.validation | 否 |
| `K2` | write the temporary file | fd = os.open(<run_dir>/g0_closed.json.tmp, O_WRONLY\|O_CREAT\|O_EXCL\|O_NOFOLLOW, 0o644); write ALL bytes of Bc (loop until complete); os.fsync(fd); os.close(fd) | 否 |
| `K3` | verify the temporary file | open it again with O_RDONLY\|O_NOFOLLOW; require a regular file; read all bytes; require bytes == Bc (length and SHA-256) and marker_schema.validation to pass | 否 |
| `K4` | publish exclusively | os.link(<run_dir>/g0_closed.json.tmp, <run_dir>/g0_closed.json, follow_symlinks=False); no os.rename, os.replace, direct creation or any other fallback under the final name; the moment link returns, the process sets published = true | 是 |
| `K5` | sync the directory | open <run_dir> with O_RDONLY\|O_DIRECTORY, os.fsync, close | 是 |
| `K6` | verify the published name | open <run_dir>/g0_closed.json with O_RDONLY\|O_NOFOLLOW; require a regular file; read all bytes; require bytes == Bc and marker_schema.validation to pass | 是 |
| `K7` | exit | the process exit code is recorded_exit_code (0, 1 or 3); only here may 0 or 1 be returned | 是 |

**失败与异常处理：**

| 失败发生在 | 已发布 | 退出码 | stderr | 磁盘上保留 | 下一次预检 |
|---|---|---|---|---|---|
| K1, K2, K3, K4 | 否 | 3 | `G0-CLOSE-UNPUBLISHED run_id=<id> step=<K1\|K2\|K3\|K4> verdict=<recorded_verdict> evidence_sha256=<h> summary_sha256=<h> closed_sha256=<sha256(Bc) or -> reason=<text>` | evidence, summary and the registry stay; a temporary file stays as it is (partial or complete); the final name is not created by this process (at K4 EEXIST an existing foreign file stays untouched) | the run directory has no valid marker: BLOCKED (NO_CLOSED, or the reason of whatever occupies the final name) |
| K5, K6, K7, or an uncaught exception once link has returned | 是 | 3 | `G0-CLOSE-UNCONFIRMED run_id=<id> step=<K5\|K6\|K7> verdict=<recorded_verdict> evidence_sha256=<h> summary_sha256=<h> closed_sha256=<sha256(Bc)> reason=<text>` | everything above plus the published g0_closed.json (kept, never removed or repaired) | judged only on what the files are: a valid marker with all bindings and no residue is CLOSED_OK; a marker that is not valid is BLOCKED |

* **退出码规则：** the process exit code is recorded_exit_code only if K1..K7 all succeeded; any failure of K1..K6 or an exception anywhere in P7 yields 3 with the stderr marker above; the recorded verdict and exit code inside the saved summary and marker are NOT changed by such a failure (nothing is overwritten)
* **报告规则：** the G0 outcome of a run is its recorded_verdict only if (a) the process exit status equals recorded_exit_code AND (b) no G0-CLOSE-* marker was printed AND (c) the marker passes closure.preflight when read back. Otherwise the outcome is BLOCKED (closure not confirmed) whatever the recorded verdict says; in particular a recorded PASS without exit code 0 is not a PASS
* **临时文件：** g0_closed.json.tmp is never deleted, renamed or truncated by G0 or by preflight; a temporary file that is byte-identical to a valid marker is tolerated, any other content is a stray file

### 8.4 预检对历史运行的判定（C01）

* evaluated by the preflight of G0-C01 over every entry of the evidence root whose name starts with 'g0_' (the consumption directory '_g0_consumed' is not such an entry), read-only: preflight never creates, repairs, renames, deletes, publishes or completes anything, and never writes a marker on behalf of an earlier run

**事实（每个运行目录一次，加三个全局事实）：**

| 事实 | 取值 | 含义 |
|---|---|---|
| `entry` | real_dir, not_a_directory, unreadable | lstat of the entry: a real directory owned by the effective uid / a symlink, file or other / not readable |
| `closed` | absent, not_regular, unreadable, oversize_or_empty, unparsable, noncanonical, schema_invalid, ok | result of marker_schema.validation applied in this order to <entry>/g0_closed.json: absent; not a regular file or a symlink; unreadable; size 0 or > 4096; not UTF-8 / not JSON / duplicate keys / NaN (truncated files land here); valid but bytes differ from the strict serialisation; key set, type, const, hex or verdict/exit pair wrong; ok |
| `closed_runid` | match, mismatch, na | closed.run_id == the entry's name (na unless closed == ok) |
| `criteria_vs_tool` | match, mismatch, na | closed.criteria_id and closed.criteria_sha256 equal those of the running tool (the criteria bound by the current authorization); na unless closed == ok |
| `criteria_vs_summary` | match, mismatch, na | closed.criteria_id and closed.criteria_sha256 equal summary.criteria_id and summary.criteria_sha256; na unless closed == ok and summary == ok |
| `summary` | absent, not_regular, unreadable, size_mismatch, hash_mismatch, unparsable, ok, na | <entry>/g0_summary.json: absent; not a regular file; unreadable; length != closed.summary_bytes; sha256 != closed.summary_sha256; not strict JSON; ok (na unless closed == ok) |
| `summary_binding` | match, mismatch, na | summary.run_id == closed.run_id AND summary.evidence_sha256 == closed.evidence_sha256 AND summary.verdict == closed.recorded_verdict AND summary.exit_code == closed.recorded_exit_code AND the pair is one of (PASS,0), (FAIL,1), (BLOCKED,3) (na unless summary == ok) |
| `evidence` | absent, not_regular, unreadable, size_mismatch, hash_mismatch, unparsable, ok, na | <entry>/g0_evidence.json judged like the summary against closed.evidence_sha256 and closed.evidence_bytes (na unless closed == ok) |
| `evidence_binding` | match, mismatch, na | evidence.run_id == closed.run_id (na unless evidence == ok) |
| `tmp` | absent, identical, other | <entry>/g0_closed.json.tmp (identical requires closed == ok): absent / a regular file whose bytes equal the bytes of a valid g0_closed.json / anything else |
| `stray_closure_names` | False, True | another entry in the run directory whose name starts with 'g0_closed' and is neither g0_closed.json nor g0_closed.json.tmp |
| `manual_disposition` | False, True | <entry>/MANUAL_DISPOSITION_REQUIRED.json exists |
| `root_manual_disposition` | False, True | <evidence root>/MANUAL_DISPOSITION_REQUIRED.json exists (global) |
| `root_listing` | complete, incomplete | the evidence root could be listed completely (global) |
| `live_marker_process` | False, True | G0-C01 process scan: a live non-zombie process other than this observer and its ancestors whose command line contains 'g0_run.py' (global) |

**规则（机器可读：`closure.preflight.rules`；检查工具按此表求值）：**

| 规则 | 原因码 | 范围 | 适用条件 | 触发条件 | 人工处理与含义 |
|---|---|---|---|---|---|
| `CL-01` | `NOT_A_DIRECTORY` | 目录 | — | entry∈{not_a_directory,unreadable} | H1：a 'g0_' entry that is not a real directory, or cannot be read |
| `CL-02` | `NO_CLOSED` | 目录 | entry∈{real_dir} | closed∈{absent} | H1：no g0_closed.json: whatever else exists (a complete summary, a partial summary, a temporary file) the run is not closed |
| `CL-03` | `CLOSED_UNREADABLE` | 目录 | entry∈{real_dir} | closed∈{not_regular,unreadable,oversize_or_empty} | H1：g0_closed.json is a symlink or not a regular file, unreadable, empty or larger than 4096 bytes |
| `CL-04` | `CLOSED_PARSE` | 目录 | entry∈{real_dir} | closed∈{unparsable} | H1：g0_closed.json is not strict JSON (truncated, not UTF-8, duplicate keys, NaN) |
| `CL-05` | `CLOSED_NONCANONICAL` | 目录 | entry∈{real_dir} | closed∈{noncanonical} | H1：g0_closed.json parses but its bytes differ from the strict serialisation of what it says (edited, re-formatted, extra whitespace or newline) |
| `CL-06` | `CLOSED_SCHEMA` | 目录 | entry∈{real_dir} | closed∈{schema_invalid} | H1：g0_closed.json has a missing or extra key, a wrong type, a wrong const, a malformed hash or an impossible verdict / exit code pair |
| `CL-07` | `CLOSED_RUNID` | 目录 | closed∈{ok} | closed_runid∈{mismatch} | H1：closed.run_id differs from the directory name |
| `CL-08` | `CRITERIA_MISMATCH` | 目录 | closed∈{ok} | criteria_vs_tool∈{mismatch} ∨ criteria_vs_summary∈{mismatch} | H1：closed.criteria_id / criteria_sha256 differs from the running tool's or from the summary's |
| `CL-09` | `SUMMARY_MISSING` | 目录 | closed∈{ok} | summary∈{absent} | H1：a valid marker but no g0_summary.json |
| `CL-10` | `SUMMARY_UNREADABLE` | 目录 | closed∈{ok} | summary∈{not_regular,unreadable} | H1：g0_summary.json is not a regular file or cannot be read |
| `CL-11` | `SUMMARY_HASH` | 目录 | closed∈{ok} | summary∈{size_mismatch,hash_mismatch} | H1：the bytes of g0_summary.json differ from closed.summary_bytes / summary_sha256 |
| `CL-12` | `SUMMARY_PARSE` | 目录 | closed∈{ok} | summary∈{unparsable} | H1：g0_summary.json has the bound hash but is not strict JSON |
| `CL-13` | `SUMMARY_BINDING` | 目录 | summary∈{ok} | summary_binding∈{mismatch} | H1：summary.run_id, evidence_sha256, verdict or exit_code disagrees with the marker |
| `CL-14` | `EVIDENCE_MISSING` | 目录 | closed∈{ok} | evidence∈{absent} | H1：a valid marker but no g0_evidence.json |
| `CL-15` | `EVIDENCE_UNREADABLE` | 目录 | closed∈{ok} | evidence∈{not_regular,unreadable} | H1：g0_evidence.json is not a regular file or cannot be read |
| `CL-16` | `EVIDENCE_HASH` | 目录 | closed∈{ok} | evidence∈{size_mismatch,hash_mismatch} | H1：the bytes of g0_evidence.json differ from closed.evidence_bytes / evidence_sha256 |
| `CL-17` | `EVIDENCE_PARSE` | 目录 | closed∈{ok} | evidence∈{unparsable} | H1：g0_evidence.json has the bound hash but is not strict JSON |
| `CL-18` | `EVIDENCE_BINDING` | 目录 | evidence∈{ok} | evidence_binding∈{mismatch} | H1：evidence.run_id disagrees with the marker |
| `CL-19` | `STRAY_CLOSURE_FILE` | 目录 | closed∈{ok} | tmp∈{other} ∨ stray_closure_names∈{True} | H1：a temporary file with other content than the marker, or another 'g0_closed*' file, next to a valid marker |
| `CL-20` | `MANUAL_DISPOSITION` | 目录 | entry∈{real_dir} | manual_disposition∈{True} | H2：MANUAL_DISPOSITION_REQUIRED.json in the run directory: an unresolved manual disposition, whatever the marker says |
| `CL-21` | `ROOT_MANUAL_DISPOSITION` | global | — | root_manual_disposition∈{True} | H2：MANUAL_DISPOSITION_REQUIRED.json in the evidence root |
| `CL-22` | `LIVE_RESIDUE` | global | — | live_marker_process∈{True} | H2：a live non-zombie process carrying the 'g0_run.py' marker (the closure marker is not proof that the earlier run's processes exited) |
| `CL-23` | `ROOT_LISTING_INCOMPLETE` | global | — | root_listing∈{incomplete} | H1：the evidence root cannot be listed completely, so no run directory can be shown to be closed |

* **结果：** an earlier run directory is CLOSED_OK iff none of the directory-scoped rules CL-01..CL-20 matches it; the preflight is clean for earlier runs iff every 'g0_' entry is CLOSED_OK and none of the global rules CL-21..CL-23 matches. Otherwise G0-C01 fails: verdict BLOCKED, no fork, no authorization consumed, and every matching rule is listed as '<entry name>:<REASON>' (global rules as ':<REASON>') in evidence.preflight.unresolved_prior. The first matching rule in id order is the primary reason.
* **人工处理类别：**
* **H1**：a person inspects the run directory and decides outside G0 (for example archives it outside the evidence root); G0 tooling never repairs, completes, renames or deletes a run directory or a marker, and never writes a marker for an earlier run
* **H2**：a person resolves the manual disposition or the live process outside G0 as MANUAL_DISPOSITION_REQUIRED.json already requires; G0 tooling does not interpret the decision
* **允许保留的文件：** files present in a run directory are never touched by preflight; a run directory may legitimately contain g0_evidence.json, g0_summary.json, g0_closed.json, a g0_closed.json.tmp identical to g0_closed.json, registry.jsonl and g0_blocked_<run_id>.json notes
* **V4 的读法：** V4 (and the code of g0_run.py lines 224-225) call a run directory closed when g0_summary.json exists and no MANUAL_DISPOSITION_REQUIRED.json is present

### 8.5 崩溃点

| 崩溃点 | 发生在 | 磁盘事实 | 下一次预检 |
|---|---|---|---|
| `X1` | P6 verified, before K2 creates the temporary file | closed=absent, tmp=absent | NO_CLOSED |
| `X2` | K2 started writing (process killed mid-write) | closed=absent, tmp=other | NO_CLOSED |
| `X3` | K2 fsynced, before K4 | closed=absent, tmp=other | NO_CLOSED |
| `X4` | K4 returned, before K5 (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X5` | K5 returned, before K6 (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X6` | K6 verified, before the process exits (process killed) | closed=ok, tmp=identical | CLOSED_OK |
| `X7` | K4 returned, then the operating system crashed before the directory entry reached the disk | closed=absent, tmp=other | NO_CLOSED |

### 8.6 结案标记证明什么、不证明什么

**证明：**
* g0_evidence.json and g0_summary.json existed with exactly the bound bytes when the marker was built (verified by read-back and SHA-256 before the marker was created)
* the marker was published atomically and exclusively: the final name exists only with complete, fsynced content
* the recorded verdict and exit code are those of the verified summary

**不证明：**
* that the observer, the child or any other process of the run has exited (G0-C01's live-process scan and MANUAL_DISPOSITION_REQUIRED.json are the only residue evidence)
* that the storage medium holds the bytes (L-4)
* that the marker was not written by someone else with write access to the directory (no signature; the bindings detect inconsistency, not forgery)
* that the process-level result was reported: a closed run may have been left by a process that exited 3 or was killed after K4 (see reporting_rule)

## 9. 裁决规则与已知限度

* A check whose evidence is missing or unreadable is UNEVALUABLE and counts as BLOCKED, whatever its on_fail class (FAIL requires evidence).
* 1. any evaluable check that failed with on_fail FAIL -> experiment verdict FAIL (a confirmed protocol or safety violation takes precedence over bench-level problems)
* 2. else any failed or unevaluable check -> BLOCKED
* 3. else PASS
* NOT TESTED = the run did not start. An exit code of 0 never replaces the verdict.
* V4 FAIL scope: every FAIL produced under these criteria is a G0 bench/protocol failure; the summary must say so; it is not evidence about the Mythos model architecture, R3 or Parcae.
* V4 clarification: the rules in checks.G0-C03.rules and checks.G0-C07.rules decide what is a proven violation (FAIL) and what is insufficient, unconfirmable, contradicting or uncorroborated evidence (UNEVALUABLE -> BLOCKED); an early stop alone never makes them a FAIL and never hides a proven violation; each rule relies only on the witnesses listed in rules.requirements.
* V4 meaning of 'evaluable' in rule 1 above: a FAIL-class check counts as an evaluable failure only if the witnesses of the rule that fired are intact; a FAIL cannot be derived from the durable copy or from damaged evidence.
* V4 disk-damage rule (M-2): when the durable copy is not faithful to the ledger, the checks listed in witness_dependencies.disk_dependent_checks are UNEVALUABLE; damage to the durable copy can therefore never create a PASS or a durable-copy-based FAIL, while a violation proven by the ledger or by independent witnesses still decides FAIL.
* V4 PASS requires every check to PASS, which includes a faithful durable registry (C03), a proven successful release followed by the child's gate pass (C07) and complete typed evidence read back from the saved file (C16), and requires pipeline stages P0..P7 to have succeeded.
* V4 limitations: see the limitations object (L-1, L-3, L-4, L-5; L-2 is resolved by M-2).
* V5 closure: a run is closed by a published g0_closed.json and by nothing else (closure.principle); the existence of g0_summary.json never closes a run; the earlier-run condition of G0-C01 is evaluated with closure.preflight.rules; any matching rule is BLOCKED.
* V5 exit codes: 0 and 1 are returned only after the closure marker was published and verified (P7); otherwise 3 with a G0-CLOSE-* marker on stderr; the recorded verdict inside the saved files is never altered by such a failure.
* V5 reporting: the outcome of a run is its recorded verdict only under closure.publication.reporting_rule; otherwise it is BLOCKED (closure not confirmed).
* V5 limitations: see the limitations object (L-6, L-7, L-8).

**限度：**
* **L-1**：(unchanged, finding F-14) checks composed of several sub-conditions other than G0-C03 and G0-C07 (for example C05, C06, C11) are UNEVALUABLE as a whole when part of their evidence is missing after an early stop; this can only turn a FAIL into BLOCKED, never into PASS
* **L-3**：(unchanged) procedural obligations that the judge does not verify: the consumption marker is created before the fork (C02), S1 is taken at the end of the hold (C05, C06), the total budget is enforced at run time (C15)
* **L-4**：(new) durability: fsync success and a byte-exact read-back do not prove that the storage medium holds the bytes; a failure is BLOCKED, a success is the best evidence available to a user-space process
* **L-5**：(new) the fidelity comparison shows that the ledger and the durable copy disagree; it cannot tell which of the two is wrong. Neither is allowed to decide a PASS or a durable-copy-based FAIL; a violation proven by the ledger itself or by independent witnesses still decides FAIL
* **L-2**：(resolved by M-2) checks that read the durable copy are UNEVALUABLE when it is not faithful
* **L-6**：(new) the closure marker is a statement about files, not about processes: it does not prove that any process of the run has exited, and a person or process with write access can forge one (no signature); residue is detected only by the live-process scan and MANUAL_DISPOSITION_REQUIRED.json
* **L-7**：(new) publication needs a filesystem with hard links in the evidence root; when link fails the run ends BLOCKED without a marker and its directory blocks later runs until a person decides (H1); no fallback to a non-exclusive scheme exists by design
* **L-8**：(new) the temporary name remains next to the marker (two names of one inode); a directory-sync failure after publication cannot be repaired by G0 and is reported only on stderr and by the exit code 3; the saved summary and marker of such a run may record PASS or FAIL while the outcome is BLOCKED (closure.publication.reporting_rule)

## 10. PASS 的含义与限度

PASS 只表示：在本内核与本 Python 上，一个受控子进程按规定顺序被创建、登记、释放、退出并被回收，没有信号、多余进程或残留，且登记表与证据完整、可信、已保存并经读回核对，运行已由合法的结案标记结案，并且进程退出码 0 在标记发布并核对**之后**才返回。它**不是**对 G1/G2/G3、BV、EPIPE 撤销证明、票据后代、janitor 恢复、观察者死亡、任何 E1-A 单元的证据；也不证明 Python 层守卫之外的所有内核路径安全；更不是关于 Mythos 模型架构的任何证据。

## 11. 授权与绑定

执行需要单独的 `AUTHORIZATION_E1A_GATE_G0.json`（schema `e1a-gate-auth-1`，`stage="G0"`，单次使用），绑定：git HEAD、E1-A 预注册哈希（`e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）、**本 V5 判据哈希、本文件哈希**、台架代码哈希、G0 代码哈希；`grants` 只含 1 个 fork、0 个信号、无故障注入。绑定到 V1、V2、V3 或 V4 文件哈希的授权对 V5 代码**自动无效**。本阶段**不创建**该文件。

## 12. 修改政策

首次在 V5 下执行 G0 之后，不得修改本文件或判据。更正 = 带下一个版本号的新文件，旧文件与其下取得的结果保留。执行后不得修改期望以迎合结果。

## 13. 实施一致性（执行前必须满足）

V5 描述的是实现**必须**满足的程序与判定。当前 `g0_run.py` / `g0_judge.py` / `g0_auth.py` **不满足**（仍绑定 V1 文件、旧 C03 / C07 / C16 逻辑、只记录写入前时间戳、先判定再写文件、`default=str`、预检只检查 `g0_summary.json` 是否存在）。在它们被实现、静态审计、经 ChatGPT / Grok 审核，并由负责人**单独**授权之前，**不得授权任何 G0 执行**：

* **F-8**：bounded reap: non-blocking waitpid polls of the one specific pid, bounded by reap_deadline_s
* **F-9**：runtime total budget checked at phase boundaries and loop iterations; phase deadlines capped by the remaining total
* **F-12**：evidence and summary files are written only into a run directory created by this process
* **F-13**：evidence root and consumption directory are created or validated with explicit ownership; run directory exclusive; failures BLOCKED with the error saved
* **LEDGER**：reg_memory_records and reg_writer_seq are captured after the last registry write and before the registry file is parsed
* **C03-V4**：the judge implements checks.G0-C03.rules, including rules.requirements, the whole-record fidelity comparison and the fidelity report
* **C07-V4**：the guard records guard.release_writes (mono_before, mono_after, result, returned, errno, error) for every write of the release byte; the judge implements checks.G0-C07.rules
* **M-2**：the judge makes C04, C05, C11 and C13 UNEVALUABLE when disk_faithful is false
* **C16-V4**：g0_run writes every field of evidence_schema.fields (schema id e1a-gate-g0-evidence-4); the judge validates the read-back evidence before any check
* **SUMMARY**：g0_summary.json carries the fields listed in evidence_pipeline P6, including fail_scope = 'G0 bench/protocol failure; not evidence about the Mythos model architecture' whenever the verdict is FAIL
* **PIPELINE**：g0_run executes evidence_pipeline P0..P7; no default=str; exclusive creation of g0_evidence.json and g0_summary.json; every failure is BLOCKED with exit code 3 and the stderr markers (including G0-CLOSE-UNPUBLISHED and G0-CLOSE-UNCONFIRMED); main maps any uncaught exception to 3
* **CLOSE-1**：g0_run executes closure.publication K0..K7 and never creates g0_closed.json by any other means; it does not delete g0_closed.json.tmp
* **CLOSE-2**：the preflight of g0_run implements closure.preflight (facts, rules CL-01..CL-23) read-only, lists the matching rules as '<entry name>:<REASON>' in evidence.preflight.unresolved_prior, and no longer treats the existence of g0_summary.json as closure
* **CLOSE-3**：table-driven tests are derived from the closure cases (cases A..H and the P7 failure cases of the V5 review) before any real run; running them requires a separate authorization

执行性约束（来自判据 `enforcement`）：

* **reap_wait**：the wait for the child to be reaped is bounded by limits.reap_deadline_s; no unbounded wait (finding F-8)
* **total_budget**：limits.max_seconds is checked at every phase boundary and loop iteration while the run is in progress, not only at the end (finding F-9); the deadline-hit names are ready, exit, reap, proc_gone, total
* **summary_write**：g0_summary.json and the evidence files are written only into a run directory created by this very process (finding F-12)
* **directories**：the evidence root is created by the run only if absent (non-recursive, mode 0755) and validated otherwise (real directory, not a symlink, owned by the effective uid, not group/other-writable); the run directory and the consumption directory are created exclusively; nothing existing is overwritten; any failure is BLOCKED with the error saved where possible (finding F-13)
* **release_evidence**：the guard records, for every write of the release byte, mono_before, mono_after and the result ('ok' with returned == 1, or 'error' with errno and error text); a failed write is recorded, never dropped; a pre-write time is never recorded as a write (finding F-18)
* **registry_ledger**：the observer's in-memory record list and the writer's seq are captured after the last registry write, before the registry file is parsed, and stored as reg_memory_records and reg_writer_seq
* **evidence_pipeline**：stages P0..P7 of evidence_pipeline are executed in order; the verdict is computed only on the evidence read back at P3; the closure marker is published at P7 only after the evidence (P3) and the summary (P6) were saved and verified
* **disk_fidelity**：the durable copy is compared with the ledger as whole canonical records; the C03 result carries the fidelity report
* **closure**：g0_closed.json is created only as specified in closure.publication (temporary file, fsync, verify, os.link, directory fsync, verify); preflight judges earlier runs only with closure.preflight.rules and never repairs anything

## 14. 附录：V4 引入的 V3 → V4 映射与规则迁移（历史，V5 不改变）

| ID | 名称 | 失败类别 V3 → V4 | 关系 | 说明 |
|---|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C02` | authorization_and_bindings | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C03` | registration_sequence_and_integrity | FAIL → FAIL | **MODIFIED** | whole-record fidelity (M-1); conditional F3 (F3a / F3b / F3c) with a machine-readable requirements table; writer_clean contradiction removed; U5 added; fidelity report; gate-pass proof defined |
| `G0-C04` | identity_registered_before_release | FAIL → FAIL | **MODIFIED** | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C05` | no_action_before_release | FAIL → FAIL | **MODIFIED** | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C06` | gate_descriptor_hygiene | FAIL → FAIL | **IDENTICAL** | text byte-identical to V3 |
| `G0-C07` | release_only_after_registration | FAIL → FAIL | **MODIFIED** | contradicting or unconfirmable gate-pass evidence is BLOCKED (V3 FAIL F3 / F4 become U6 / U7); early action before the attempt is FAIL (new F3); U4 broadened |
| `G0-C08` | exit_observed_unreaped | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C09` | reap_by_specific_pid | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C10` | exit_status_zero | FAIL → FAIL | **IDENTICAL** | text byte-identical to V3 |
| `G0-C11` | process_budget | FAIL → FAIL | **MODIFIED** | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C12` | zero_signals | FAIL → FAIL | **IDENTICAL** | text byte-identical to V3 |
| `G0-C13` | cleanup_and_no_residue | BLOCKED → BLOCKED | **MODIFIED** | M-2: UNEVALUABLE when the durable copy is not faithful; evaluable cases unchanged |
| `G0-C14` | observer_descriptor_baseline | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C15` | time_bounds | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |
| `G0-C16` | evidence_complete | BLOCKED → BLOCKED | **MODIFIED** | evidence is the read-back of the saved file (pipeline P3/P4); schema id e1a-gate-g0-evidence-4; field set unchanged |
| `G0-C17` | no_unexplained_error | BLOCKED → BLOCKED | **IDENTICAL** | text byte-identical to V3 |

| V3 规则 | V4 规则 | 状态 | 说明 |
|---|---|---|---|
| C03-F1 | C03-F1 | unchanged | evaluated on the ledger |
| C03-F2 | C03-F2 | unchanged | now stated only through rules.requirements |
| C03-F3 | C03-F3a / C03-F3b / C03-F3c | split and conditioned | fork, release write and proven gate pass are separate; only F3c ignores writer_clean (DD-5) |
| C03-F4 | C03-F4 | unchanged |  |
| C03-U0 | C03-U0 | unchanged |  |
| C03-U2 | C03-U2 | strengthened | any field difference, with a fidelity report |
| C03-U3 | C03-U3 | unchanged | now also covers the writer-failure branches of F3a / F3b |
| (none) | C03-U5 | new | unconfirmed or contradicting independent evidence of an action with a missing precursor |
| C03-U1 | C03-U1 | unchanged |  |
| C03-U4 | C03-U4 | unchanged | fail-safe default |
| C07-F1 | C07-F1 | unchanged |  |
| C07-F2 | C07-F2 | unchanged |  |
| C07-F3 (all writes failed, child passed: FAIL) | C07-U6 | FAIL -> UNEVALUABLE | witnesses contradict (DD-3) |
| C07-F4 (FIRST_ACTION < mono_after: FAIL) | C07-F3 (FIRST_ACTION < mono_before: FAIL) and C07-U7 (mono_before <= FIRST_ACTION < mono_after: UNEVALUABLE) | split | only an action before the attempt is a proven violation |
| C07-U1 | C07-U1 | unchanged |  |
| C07-U2 | C07-U2 | unchanged |  |
| C07-U3 | C07-U3 | unchanged |  |
| C07-U4 (only when RELEASED is in the ledger) | C07-U4 | broadened | no attempt recorded + gate passed is unconfirmable whether or not RELEASED is in the ledger (DD-4) |
| C07-U5 | C07-U5 | unchanged |  |
