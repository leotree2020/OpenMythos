# E1A_GATE_TEST_INVENTORY — 现有进程级测试清单与风险分级

**状态：只读审计，未执行任何测试。** 对象：`tests/test_e1a_gate.py`（14 个测试）及其调用的 `observer / gate / node / proto / registry / janitor / validity / trial / common` 模块。基准 `a7ce70fb71134d1098de7a50ed475b1b1518e64b`。

**分级（本轮规划分类，不是已执行的实验，也不替代 BV 编号）：** G0 最小正向门控；G1 负向门控；G2 身份与后代；G3 恢复、故障注入、SIGKILL、异常残留；E = E1-A 实验单元（需要单元授权）；P = 纯文件 / 不启动进程。

## 1. 通用事实

- `GateCase.setUp` 建立临时 REG 与 `Observer`；`tearDown` 对每个出现过的试验标签调用 `finish_trial_cleanup()`，其中 `kill_registered()` 会对**仍存活**的已登记节点经 pidfd 发 **SIGKILL**，并 `waitpid(具体 pid)` 回收直接子进程。因此凡是让节点留在“等待 EXIT/EOF（最长 120 s）”的测试，**拆除时都会发 SIGKILL**。
- 没有任何测试依赖 cgroup、proc connector 或特殊权限：需要 `os.pidfd_open`（内核 ≥ 5.3）、`signal.pidfd_send_signal`、`socket.send_fds/recv_fds`（SEQPACKET）、`/proc`；`/proc/<pid>/environ` 的读取（盲性检查）需要同一 uid。
- unittest 默认**不是失败即停**：一个测试失败后，后面的测试仍会在可能有残留的状态下继续运行。没有测试在运行前检查“前次运行遗留”。
- 这些测试只用 `assert` 判定，**不产生证据文件**，不与 Git SHA / 预注册 / 台架哈希绑定。

## 2. 逐测试清单

| # | 测试 | 真实行为（fork / exec / waitpid / pidfd / 信号） | 进程数与后代 | 故障注入 / 恢复 | 可能残留 | 失败时的停止与清理责任 | 验收与证据 | 分级 |
|---|---|---|---|---|---|---|---|---|
| 1 | `test_released_node_reports_ready_with_its_own_session` | `spawn_direct`：1 次 fork（无 exec）；pidfd_open；子进程 `setsid`；拆除时 **SIGKILL** + `waitpid` | 1 个，0 后代 | 无 | 子进程若 kill 失败则存活 ≤ 120 s | tearDown 清理并断言 cleanup_ok；失败时其余测试继续 | assert：READY、sid = pid；无证据文件 | **G3 as written**（拆除 SIGKILL）；其正向部分由新 G0 无信号版本取代 |
| 2 | `test_unreleased_node_does_nothing_and_abort_ends_it`（BV-1） | 1 fork；预排队 SPEC；写 `A` 中止；子进程 exit 111；`waitpid` | 1，0 | 否（正常中止） | 无（自行退出） | 同上 | assert：未动作、sid 未变、exit 111 | **G1** |
| 3 | `test_silent_gate_times_out_with_exit_112`（BV-3） | 1 fork，`t_gate_max=2 s`，门沉默 → exit 112；`waitpid` | 1，0 | 否 | 无 | 同上 | assert：exit 112 | **G1** |
| 4 | `test_observer_death_closes_the_gate`（BV-2） | 2 次 fork：辅助进程（受登记）→ 其内部再 fork 一个**未登记**的 G；辅助进程 `_exit` 模拟观察者死亡；G 靠 EOF 自行退出；G 无法被清理（未登记） | 2（G 为未登记孙进程） | **是：观察者死亡模拟** | **G 未登记，若不自行退出则无法清理（ERRATA-002 R1）** | 轮询至多 T_gate_max+3 s | assert：G 死亡、未行动、未登记 | **G3** |
| 5 | `test_closing_the_gate_write_end_ends_the_child_with_exit_111` | 1 fork；观察者关闭门写端 → 子进程读 EOF → exit 111；`waitpid` | 1，0 | 否 | 无 | 同上 | assert：exit 111 | **G1** |
| 6 | `test_descendants_are_registered_through_tickets_and_ordered` | 1 + 1 fork（父节点 + 经**票据**创建的子节点，SCM_RIGHTS 传 gate_r）；拆除 **SIGKILL** 两者 | 2（1 后代） | 无 | 子节点若 kill 失败存活 ≤ 120 s | 同上 | assert：后代已登记、ppid、REG 顺序 | **G2**（拆除含 SIGKILL） |
| 7 | `test_no_gate_write_end_leaks_into_nodes` | 1 fork；读 `/proc/<pid>/fd`；拆除 **SIGKILL** | 1，0 | 无 | 同上 | 同上 | assert：fd 卫生 | **G2** |
| 8 | `test_janitor_refuses_a_wrong_identity_and_acts_on_the_right_one`（BV-6） | 1 fork；进程内 janitor：错误起始时间 → 拒绝；正确 → **pidfd SIGKILL**；`waitpid` | 1，0 | **是：janitor 对活进程发 SIGKILL** | 无（被杀并回收） | 同上 | assert：拒绝 / 已发送 / 死亡 | **G3** |
| 9 | `test_janitor_ignores_intent_only_and_torn_records`（BV-7） | **不启动进程**；纯文件；`signal_fn` 抛错以证明未调用 | 0 | 否 | 无 | — | assert：无目标、仅报告 | **P**（可与 G1 的登记负向检查并列） |
| 10 | `test_failed_registration_keeps_cleanup_responsibility_until_death_is_confirmed` | 1 fork（`fingerprint` 被 mock 成 ppid 不符）→ ABORTED；子进程收到 `A` 退出 111；`finish_cleanup(grace=5)` 可能对**仍存活**的未登记直接子进程补发 SIGKILL（竞态） | 1，0 | 部分（登记失败注入） | 极小 | 同上 | assert：ABORTED、exit 111、DEAD 记录 | **G1**（含可能的 SIGKILL 竞态） |
| 11 | `test_janitor_cleans_up_when_run_end_does_not_confirm_cleanup` | 1 fork；`RUN_END(False)`；`cleanup_until_clear` → **pidfd SIGKILL** | 1，0 | **是：恢复路径** | 无 | 同上 | assert：clear、已死 | **G3** |
| 12 | `test_janitor_does_not_trust_a_false_confirmation` | 1 fork；仅 `decide`（读）；拆除 **SIGKILL** | 1，0 | 部分（虚假确认） | 同上 | 同上 | assert：CLEANUP | **G3 as written**（拆除 SIGKILL） |
| 13 | `test_correct_configuration_is_accepted_by_all_candidates` | 3 次 `run_trial`（E1A-a × P0/P1/P2）：每次 1 fork + **exec** `python -I -S sup_stub.py`；监督器桩经票据再创建根节点（SCM_RIGHTS）；`/proc/<pid>/environ` 盲性检查；**SIGKILL** 清理 | 每次 2，合计 6 | 否 | 同上 | 同上 | assert：bench_reasons 空、裁决 PASS | **E**（E1-A 单元，需单元授权 + BV 证据） |
| 14 | `test_session_sharing_root_is_blocked_by_p2_and_missed_by_p0` | 2 次 `run_trial`（E1A-b × P2/P0），同上 | 合计 4 | 否 | 同上 | 同上 | assert：P2 PASS、P0 FAIL | **E** |

## 3. 覆盖缺口（没有任何进程级测试）

- 门上收到 `R` 以外的字节（未授权释放）→ 应 exit 111；
- 对**已撤销票据**的门探测：创建者仍持有读端时不得证明、读端消失时 `EPIPE` 才证明（CLOSEOUT-01 的核心假设，目前只有 mock 测试）；
- 入口关闭后的 `CREATED` 晚到、`TICKET_DENIED` 经真实套接字；
- 观察者死亡后 janitor 对 `RUN_END` 缺失的真实恢复（测试 11 只覆盖 `RUN_END(False)`）；
- 退出与回收的区分（下节 F-1）。

## 4. 本轮审计发现（不改台架，交审核者裁决）

**F-1（与“退出 ≠ 回收”直接相关）：** `observer._confirmed_dead()` 对**已登记**节点用 `common.process_is_dead()`，后者把 `/proc` 状态 `Z`（僵尸，已退出**未回收**）也算作“已死”。`finish_cleanup()` 在 `reap_direct()` 之后才求值，正常路径下已回收；但若 `reap_direct()` 超时（`exit_status` 仍为 `None`），僵尸仍会被判定为已确认死亡并写入 `DEAD`——即**可以在子进程尚未被回收时宣布清理完成**。直接子进程（观察者创建）应额外要求 `exit_status is not None`。本轮**不修改台架**（会改变代码哈希并使 172/172 逻辑测试证据失效）；G0 判据 `G0-C08/C09/C10` 独立要求“在回收前观察到 `Z`”与“`waitpid` 的具体返回”，因此 G0 不依赖该缺陷；是否在 G1 之前修复，请审核者决定。

**F-2：** 现有 `tests/test_e1a_gate.py` 不能按 G0 单独运行（测试 1 在拆除时发 SIGKILL，测试之间无失败即停，无证据文件，无运行前残留检查，无授权互锁）。因此 G0 采用独立入口 `gate_g0/g0_run.py`，不重构台架。

**F-3：** `GateCase.tearDown` 的 SIGKILL 清理在 G0 中**不被使用**：G0 的子进程由控制通道的 `EXIT` 消息结束，守卫禁止一切信号。
