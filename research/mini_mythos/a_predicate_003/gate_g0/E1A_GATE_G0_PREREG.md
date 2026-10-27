# E1A_GATE_G0_PREREG — 第一次最小受控进程门控测试（G0）的预注册

**状态：`FROZEN AT THE COMMIT THAT ADDS THIS FILE / G0 NOT TESTED / EXECUTION NOT AUTHORIZED`**
任务：`F3B-D1-A-CPU-003-E1A-GATE-PREP-001`。基准 `a7ce70fb71134d1098de7a50ed475b1b1518e64b`。
机器可读判据：`g0_criteria_v1.json`，SHA-256 `4d3acd67d9d98e26d8c608cbfd037b5b7f75e78afe4a2c33e7de63fb7dee3ce2`（本文件与之配套；任一改动都使执行授权失效）。

**G0–G3 是本轮规划分类，不是已经执行的实验，也不替代 BV-1…BV-10 的编号。** 本文件不授权任何执行。

## 1. 目的与范围

验证 GATED-SPAWN 在真实 Linux 内核上的**最小正向路径**：
`INTENT → fork → GATE → REGISTERED → RELEASE → EXIT → REAP`——一个牺牲子进程被受控创建、登记、释放、正常退出并被回收；全程**零信号**。

**不在范围：** G1（ABORT / 门超时 / 未授权释放 / 无读端 EPIPE）、G2（pidfd 身份 / SCM_RIGHTS / 后代登记）、G3（观察者死亡 / janitor / SIGKILL / 异常残留）、BV-1…BV-10、E1-A 单元、E1-B/C/D、E2/E3。G0 的授权**不能**继承为上述任何一项的授权，入口代码也没有通向它们的路径。

## 2. 输入与环境

CPU、Python 3.13.16、Linux（当前微型虚机内核 6.18.44-fc-v165）、uid 0（不依赖 root 权限，仅依赖 `pidfd_open` ≥ 5.3 与 `socket.send_fds`），仅标准库。无 cgroup、无 proc connector、无网络、无 GPU。被测代码：`bench/{observer,gate,node,proto,registry,common,truth}.py`（不改动）及 `gate_g0/{g0_auth,g0_judge,g0_run}.py`。独立临时运行目录 `evidence/g0_<run_id>/`，唯一 `run_id`。

## 3. 过程（固定，不可参数化）

1. **S0 预检（不启动进程）：** 验证授权与哈希绑定；确认无前次未解决残留、无带台架令牌的存活进程（祖先除外）、观察者无子进程、`/proc` 枚举完整、运行 id 唯一；记录观察者描述符数与全局进程数。
2. 写 `RUN_START`；安装守卫：**拦截并记录**所有 `kill / killpg / pidfd_send_signal / raise_signal / pthread_kill / exec* / spawn* / system / popen / subprocess`，`fork` 计数且最多放行 1 次，`waitpid` 只放行正的具体 pid。
3. **一次** `spawn_direct`（`hold_release=True`）：写 `INTENT` → `fork` → 子进程在门上阻塞 → 观察者读 `/proc` 指纹、开 pidfd、校验 `ppid`/起始时间 → 写 `REGISTERED`。→ **S1 快照**（已登记、未释放）：子进程状态、描述符、消息、sid/pgrp；保持 0.3 s，期间子进程必须无任何动作。
4. 写 `RELEASED` → 向门写 `R` → 子进程读 `SPEC`、发 `FIRST_ACTION`、发 `READY` 后留在控制通道上等待。→ **S2 快照**（描述符中不得再有门管道）。
5. 观察者经**控制通道**发 `EXIT` 消息（不是信号）；子进程 `_exit(0)`。→ **S3 快照**：在**任何 wait 调用之前**确认 pidfd 可读且 `/proc` 状态为 `Z`（已退出、未回收）。
6. `waitpid(该具体 pid)` → 记录退出码 → **S4 快照**：`/proc/<pid>` 不存在（或起始时间不同）。**退出与回收是两个独立的、有时间戳的证据。**
7. `final_cleanup`（入口关闭、不动点、运行集合核对、写 `DEAD`）→ 令牌扫描（仅诊断）→ 写 `RUN_END`（含 `cleanup_confirmed`）→ **S5 快照**，写 `g0_evidence.json`、`g0_summary.json`、消耗授权标记。
8. 总时长上限 20 s；各阶段截止时间见判据文件。超时或异常：**不发信号**，保存证据，判 BLOCKED，列出仍存活进程的已验证身份并写 `MANUAL_DISPOSITION_REQUIRED.json`。

## 4. 预期结果（先于执行写下）

PASS 的预期观测：`fork` 恰 1 次；S1 子进程状态 `S`、描述符 ≤ 5 个且门管道仅一个只读描述符；`FIRST_ACTION` 晚于 `RELEASED`；S3 状态 `Z` 且 ppid = 观察者；`waitpid` 退出码 0；S4 无 `/proc/<pid>`；信号 0 次；`DEAD` 带依据；观察者描述符数 S5 = S0；无残留。

## 5. 判据（冻结；`g0_criteria_v1.json` 为准）

| ID | 名称 | 失败类别 | 内容 |
|---|---|---|---|
| `G0-C01` | preflight_clean | BLOCKED | no unresolved earlier run (no MANUAL_DISPOSITION_REQUIRED.json, no earlier g0 run directory without a closed summary), no live process carrying a bench token other than the ancestors of this run, observer has 0 children, /proc enumeration complete, run id unique |
| `G0-C02` | authorization_and_bindings | BLOCKED | a valid single-use G0 authorization was consumed; git head, E1-A prereg, G0 criteria, G0 prereg text, bench code and G0 code hashes equal the authorized values at the start AND again at the end |
| `G0-C03` | registration_sequence_and_integrity | FAIL | REG shows RUN_START first, then for the single node INTENT < FORKED < REGISTERED < RELEASED < DEAD, RUN_END last and unique; registry.integrity_issues() is empty |
| `G0-C04` | identity_registered_before_release | FAIL | REGISTERED pid/starttime equal the /proc fingerprint read while the child was held; the child's ppid is the observer; pid equals the pid returned by fork |
| `G0-C05` | no_action_before_release | FAIL | while REGISTERED but unreleased the child is blocked (state S), sent no message, kept the observer's sid/pgrp; its FIRST_ACTION is not earlier than the RELEASED record |
| `G0-C06` | gate_descriptor_hygiene | FAIL | held: child descriptors are a subset of {0,1,2,gate read end,control socket}, the gate pipe appears exactly once and read-only (no write-capable descriptor); after release: no descriptor refers to the gate pipe |
| `G0-C07` | release_only_after_registration | FAIL | monotonic times satisfy REGISTERED <= RELEASED <= release byte written <= child FIRST_ACTION |
| `G0-C08` | exit_observed_unreaped | BLOCKED | after the EXIT message and before any wait call the child was observed exited-but-unreaped: pidfd readable and /proc state Z with ppid = observer |
| `G0-C09` | reap_by_specific_pid | BLOCKED | waitpid on that specific pid returned that pid; afterwards /proc/<pid> is absent (or carries a different starttime); times EXITED_UNREAPED < REAPED <= PROC_GONE |
| `G0-C10` | exit_status_zero | FAIL | the reaped exit code is 0 (normal exit after the EXIT message) |
| `G0-C11` | process_budget | FAIL | exactly one fork in the whole run; at every snapshot the observer has at most one child and the child has no child; the registry contains exactly one node and no ticket |
| `G0-C12` | zero_signals | FAIL | no kill/killpg/pidfd_send_signal/raise_signal/pthread_kill/exec/spawn/subprocess call was attempted (guard violations empty) and every cleanup kill entry is 'already_exited' |
| `G0-C13` | cleanup_and_no_residue | BLOCKED | final cleanup ok, run set consistent, DEAD record with basis present, observer has no child, diagnostic token scan finds no unregistered live process, no snapshot reported incomplete /proc enumeration, RUN_END confirmed |
| `G0-C14` | observer_descriptor_baseline | BLOCKED | the observer's open descriptor count at S5 equals S0 |
| `G0-C15` | time_bounds | BLOCKED | total duration <= max_seconds and no phase deadline was hit |
| `G0-C16` | evidence_complete | BLOCKED | all snapshots, events, REG records and bindings required by this file are present in the evidence |
| `G0-C17` | no_unexplained_error | BLOCKED | no exception, no abort reason, exit-code policy consistent with the verdict |

**裁决规则：** 缺证据的检查为 UNEVALUABLE（一律按 BLOCKED，FAIL 必须有证据）；① 任一**可评估**且失败的 FAIL 类检查 ⇒ **FAIL**（已确认的协议 / 安全违规优先于台架层面的问题）；② 否则任一失败或 UNEVALUABLE ⇒ **BLOCKED**；③ 否则 **PASS**；**NOT TESTED** = 未启动。**退出码**：PASS 0，FAIL 1，BLOCKED 3；退出码 0 不替代裁决，也不掩盖异常（任何异常、中止原因都使裁决不是 PASS）。

## 6. PASS 的含义与限度

PASS 只表示：在本内核与本 Python 上，一个受控子进程按规定顺序被创建、登记、释放、退出并被回收，没有信号、多余进程或残留。它**不是**对 G1/G2/G3、BV、EPIPE 撤销证明、票据后代、janitor 恢复、观察者死亡、任何 E1-A 单元的证据；也不证明 Python 层守卫之外的所有内核路径安全。

## 7. 授权与绑定

执行需要单独的 `AUTHORIZATION_E1A_GATE_G0.json`（schema `e1a-gate-auth-1`，`stage="G0"`，单次使用），绑定：git HEAD、E1-A 预注册哈希（`e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）、本判据哈希、本文件哈希、台架代码哈希、G0 代码哈希；`grants` 只含 1 个 fork、0 个信号、无故障注入。本轮**不创建**该文件。

## 8. 修改政策

首次执行后不得修改本文件或判据。更正 = 新文件 `g0_criteria_v2.json` / `E1A_GATE_G0_PREREG_V2.md`，旧文件与其下取得的结果保留。执行后不得修改期望以迎合结果。
