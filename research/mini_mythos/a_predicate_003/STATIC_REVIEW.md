# F3B-D1-A-CPU-003 E1-A — 台架静态审查报告（STATIC REVIEW）

**状态：`CPU-003 E1-A PREREGISTRATION COMPLETE / BENCH IMPLEMENTED / STATIC REVIEW PENDING / EXPERIMENT NOT TESTED`**

本文件由 Claude Code 编写，供独立审核者（ChatGPT）做**静态审查**。它不是实验结果；台架中**没有任何进程级代码路径被执行过**。

## 0. 本轮实际执行了什么（如实）

| 动作 | 性质 | 是否启动进程 / 发信号 |
|---|---|---|
| `python3 -c ast.parse` 逐文件语法检查 | 只读 | 否 |
| `tools/static_audit.py`（AST 审计，不 import 被审文件） | 只读 | 否 |
| `tools/check_prereg_schema.py`（纯 JSON；**独立重新推导**分类表并与冻结表比对） | 只读 | 否 |
| `bench/e1a_runner.py --check` / `--plan`（读文件、算哈希、比对钉死的 CPU-001/002 代码、核对食谱与预注册一致、计算计划规模） | 只读 | 否 |
| `bench/e1a_runner.py --execute`（**不带授权文件**，仅用来确认互锁拒绝：在授权检查处返回码 2，未触及任何进程逻辑） | 互锁验证 | 否 |
| AST 版“穷人 pyflakes”（未定义名 / 未使用 import / 跨模块属性是否存在，草稿工具，不入库） | 只读 | 否 |
| `bash -n run_e1a.sh`（仅语法） | 只读 | 否 |
| 只读读取 `/proc/self/cgroup`、`/sys/fs/cgroup`、`/proc/net/connector`、`/proc/config.gz`（P3/P4 可行性事实，第 8 节） | 只读 | 否 |

**未执行：** `tests/test_e1a_*.py` 全部**已编写、未运行**（包括不 fork 的纯逻辑测试——按指令保持“已编写、未运行”）；没有 fork、没有信号、没有故障注入、没有运行 E1-A / E1-B/C/D / E2 / E3；未修改冻结 R3 / 真实 D1 / CPU-001 / CPU-002 的代码或证据；没有真实数据、训练、GPU。

## 1. 预注册与提交顺序

| 提交 | 内容 | `e1_provability_table_v1.json` SHA-256 |
|---|---|---|
| `b2aec0f` | 首次冻结（仅预注册 + 侧文件） | `9df3eafde8972645660abbc229b185a8328f24377d0db1e7941e7621fcac0828` |
| `c02f201` | PREP-CORR-1（仅预注册） | `22d64ef856a92c73b87c0c8343afec4d847e9110a1964e14c62623a36d52e3a8` |
| `f9d3cd8` | PREP-CORR-2（仅预注册） | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| 本分支其后的提交 | 台架实现、测试、工具、文档 | 预注册不再改动 |

两次更正都发生在**任何台架提交之前、任何执行之前**，由“把预注册落实为静态拓扑 / 判定代码”时发现，并记录在预注册的 `correction_log`：

- **PREP-CORR-1：** (1) 检查 C5 原写成“等式”，但场景 d 中根不是监督器的子进程，不应因此成为 C5 缺陷，改为“监督器子进程集合减去（根 ∪ 已声明辅助进程）非空”；(2) 场景 d 原构造会让领头节点 L 作为未声明子进程留在监督器下，从而额外触发 C5，与分类表不符——改为 L 在根登记并释放后退出并被监督器按**具体 pid** 回收，根被重新挂到监督器之外（SETUP 阶段不设置 subreaper）。分类表各行未变。
- **PREP-CORR-2：** 实验级 PASS 原写“每个单元 PASS”，会因基线候选 P0/P1 在其 ECD 之外的单元上按预期 FAIL 而使整个实验 FAIL。新增第 8 步（候选级判定）与第 9 步（**实验判定 = S0 候选 P2 的判定**；P0/P1 的 FAIL 作为能力发现报告，不决定实验判定；任何候选的不安全事件使实验 FAIL）。分类、场景、期望码集、参数均未改。

**预期的“P0/P1 在部分单元 FAIL”不是为通过而调参：** 它由冻结的 ECD 机械推出（缺陷所需规则不在候选的证据能力内 ⇒ UNPROVABLE ⇒ 任何 ACCEPT 都是无证明的确定答案 ⇒ FAIL），`check_prereg_schema.py` 独立重算并逐格比对。

## 2. 冻结分类矩阵（由冻结 JSON 生成，非手工转录）

| 场景 | 证据 | 真实缺陷集 | P0 | P1 | P2 |
|---|---|---|---|---|---|
| `E1A-a` | REAL_KERNEL | — | PROVABLE → ACCEPT | PROVABLE → ACCEPT | PROVABLE → ACCEPT |
| `E1A-a2` | REAL_KERNEL | — | PROVABLE → ACCEPT | PROVABLE → ACCEPT | PROVABLE → ACCEPT |
| `E1A-b` | REAL_KERNEL | C1,C2,C3 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `STAGE_SESSION_NOT_DEDICATED` | PROVABLE → BLOCKED `ROOT_NOT_PGROUP_LEADER, ROOT_NOT_SESSION_LEADER, ROOT_SESSION_IS_SUPERVISOR_SESSION` |
| `E1A-c` | REAL_KERNEL | C1,C2 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `STAGE_SESSION_NOT_DEDICATED` | PROVABLE → BLOCKED `ROOT_NOT_SESSION_LEADER, ROOT_SESSION_IS_SUPERVISOR_SESSION` |
| `E1A-d` | REAL_KERNEL | C1,C3 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `STAGE_SESSION_NOT_DEDICATED` | PROVABLE → BLOCKED `ROOT_NOT_PGROUP_LEADER, ROOT_NOT_SESSION_LEADER` |
| `E1A-e1` | REAL_KERNEL | C4 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `ROOT_HAS_PREEXISTING_CHILDREN` |
| `E1A-e2` | REAL_KERNEL | C5 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `SUPERVISOR_HAS_UNREGISTERED_CHILDREN` |
| `E1A-f` | SIMULATED | C6 | PROVABLE → BLOCKED `ROOT_FINGERPRINT_MISMATCH` | PROVABLE → BLOCKED `ROOT_FINGERPRINT_MISMATCH` | PROVABLE → BLOCKED `ROOT_FINGERPRINT_MISMATCH` |
| `E1A-g` | REAL_KERNEL | C7 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `SIGCHLD_NOT_DEFAULT` |
| `E1A-h1` | SIMULATED | C8 | PROVABLE → BLOCKED `PREFLIGHT_FAILED` | PROVABLE → BLOCKED `PREFLIGHT_FAILED` | PROVABLE → BLOCKED `SUBREAPER_NOT_VERIFIED` |
| `E1A-h2` | SIMULATED | C8 | PROVABLE → BLOCKED `PREFLIGHT_FAILED` | PROVABLE → BLOCKED `PREFLIGHT_FAILED` | PROVABLE → BLOCKED `SUBREAPER_NOT_VERIFIED` |
| `E1A-i` | REAL_KERNEL | C1,C2,C3 | UNPROVABLE → 拒绝（BLOCKED/UNKNOWN）；ACCEPT = FAIL | PROVABLE → BLOCKED `STAGE_SESSION_NOT_DEDICATED` | PROVABLE → BLOCKED `ROOT_NOT_PGROUP_LEADER, ROOT_NOT_SESSION_LEADER, ROOT_SESSION_IS_SUPERVISOR_SESSION` |

P3（proc connector）、P4（cgroup）能力 UNVERIFIED，**未分类、未运行、不被宣称为 PROVABLE**。

## 3. 静态审计（`tools/static_audit.py`，AST，结果：0 条违规）

策略：`os.fork` 只在 `gate.py`；`os.exec*` 只在 `trial.py`；`os.setsid/os.setpgid` 只在 `node.py`/`trial.py`；**所有信号只经 `PidfdHandle.send`**（`signal.pidfd_send_signal` 只出现在 `common.py`）；任何位置不得调用 `os.kill` / `os.killpg` / `signal.raise_signal` / `signal.pthread_kill`（监督器桩的插桩是对这些名称的**属性赋值**，不是调用）；等待只允许观察者对**具体 pid** 的 `os.waitpid`（拒绝负 pid、`P_ALL`、`os.wait*`），监督器桩使用保存的原函数；禁止 `subprocess` / `multiprocessing` / `threading` / `shutil` / `pty`、`os.system` / `os.popen` / `os.spawn*`；字符串中不得出现 `pkill` / `killall` / `pgrep`；`read_cmdline` / `read_environ` 只用于 `truth.py` 的诊断。

特权调用清单（审计实际发现的全部位置）：

| 文件 | 特权调用 | 行 |
|---|---|---|
| `common.py` | `os.pidfd_open` | 199 |
| `common.py` | `signal.pidfd_send_signal` | 224 |
| `gate.py` | `os._exit` | 48,52,54,58,61,80,81 |
| `gate.py` | `os.fork` | 72 |
| `janitor.py` | `os._exit` | 90 |
| `node.py` | `os._exit` | 62,67,71,73,75 |
| `node.py` | `os.setpgid` | 57 |
| `node.py` | `os.setsid` | 55 |
| `observer.py` | `os.waitpid` | 258 |
| `sup_stub.py` | `os._exit` | 114,137,143 |
| `trial.py` | `os.execve` | 56,62 |
| `trial.py` | `os.setsid` | 37 |
| `truth.py` | `read_cmdline` | 67,104 |
| `truth.py` | `read_environ` | 67 |
| `validity.py` | `os._exit` | 66,72 |

## 4. 协议与不变量 → 代码对照

**创建–登记–释放（GATED-SPAWN），一次完整流程：**

1. 创建者 N（观察者本身，或已释放的节点 / 监督器桩）→ 观察者：`TICKET`。
2. 观察者写 `INTENT`（`O_APPEND` 单次 `write`），建门管道和节点控制套接字，回 `TICKET_OK`，经 `SCM_RIGHTS` 交给 N：**门读端 + 子节点控制端**（门写端**只留在观察者**）。
3. N `fork`（`gate.fork_gated`）：子进程**第一步**重置信号、清空信号掩码并 `close_fds_except({0,1,2,门读端,控制端})`，然后在门上等待。N 关闭自己手里的门读端和控制端，发 `CREATED(pid)`。
4. 观察者：`pidfd_open` → 用 `/proc` 指纹复核（`starttime` 稳定、`ppid` = 创建者 pid）→ 写 `REGISTERED`（含 pid / starttime / sid / pgrp / 创建者）→ 写 `RELEASED` → 向门写入 `b"R"` → 发 `SPEC`；回 `REGISTERED_OK`。任一步失败：写 `ABORTED`、向门写 `b"A"`（或关闭写端），回 `REGISTER_FAILED`。
5. 子进程只有读到**恰好** `b"R"` 才继续；`b"A"`、EOF（观察者死亡）、其它字节、`T_gate_max` 超时都以 111 / 112 自行结束。

| 不变量 / 检查 | 实现位置 | 何时评估 |
|---|---|---|
| I1 释放前无动作 | `gate.gate_wait`（只接受 `b"R"`）；节点只在门之后才读 `SPEC` | BV-1（运行级）；每次试验用 `FIRST_ACTION` 单调时钟 ≥ `RELEASED` 记录（BV-4） |
| I2 非 `R` 即结束 | `gate.gate_wait` | BV-2（观察者死亡）、BV-3（门沉默） |
| I3 子进程无门写端 | 门写端只在观察者；创建者只收到读端 | BV-8：`/proc/<pid>/fd` 中不得出现任何节点的门管道 inode，且描述符数 ≤ 6 |
| I4 起手关闭继承的描述符 | `gate.child_hygiene` / `close_fds_except` | BV-8 |
| BV-4 登记先于释放 | `registry.check_order`（纯函数） + 单调时钟 | 每次试验 |
| BV-5 后代同协议 | 创建者必须是**已释放**节点；`CREATED` 的创建者必须与票据一致；`_stray_reasons` 对 S0 前、S0 后各做一次谱系对账（监督器后代 / 已登记节点的子进程必须全部已登记） | 每次试验 |
| BV-6 janitor 身份不符不发信号 | `janitor.run_cleanup`：先 `pidfd_open` 再比 `starttime`；`AlreadyExited`→gone，其它→拒绝 | 运行级（正例 + 反例） |
| BV-7 janitor 忽略 INTENT-only 与撕裂尾行 | `registry.parse_reg` / `cleanup_targets` | 运行级（纯文件） |
| BV-9 监督器盲 | `truth.blindness_reasons`：argv / environ / 描述符目标中不得含登记文件路径、`registry.jsonl`、角色词 | 每次试验 |
| BV-10 插桩先于候选导入 | `sup_stub.install_instrumentation` 先于 `candidates` 导入；报告“导入时已加载的候选模块 = ∅”与包装是否生效 | 每次试验（S0 前、S0 后各一次） |

**其它安全设计：** 每个节点有 `T_NODE_MAX`=120 s 的寿命上限，并在控制套接字 EOF（观察者死亡）时自行结束；监督器桩以新的 `python -I -S -B` 经 `exec` 启动，只有 fd 3 一个控制套接字；清理只对**已登记且身份确认**的节点经 `PidfdHandle` 发 `SIGKILL`；运行结束的令牌扫描只**诊断**（列出未登记且命令行含运行令牌的存活进程，使实验 BLOCKED），**从不发信号**；失败关闭——无法确认身份则不发信号、记录、该运行中止（`RunAbort`）。

## 5. 预注册判定函数 → 代码

| 预注册步骤 | 代码 |
|---|---|
| 1 台架不可验证 → BLOCKED | `trial.run_trial` 收集 `bench_reasons` → `truth.judge` 第一分支 |
| 2 不安全事件 → FAIL | `truth.candidate_unsafe_events`（`S0` 阶段、非 infra 的 kill / wait 调用）+ `extra_unsafe` |
| 3 PROVABLE/ACCEPT | `truth.judge` |
| 4 PROVABLE/BLOCKED（码集精确相等、引用规则 ⊇ 必需且 ⊆ ECD） | `truth.judge` |
| 5 UNPROVABLE（BLOCKED/UNKNOWN 为 PASS；ACCEPT 为 FAIL） | `truth.judge` |
| 6 单元判定（BLOCKED > 5% → INSUFFICIENT；任一 FAIL → FAIL） | `truth.cell_verdict` |
| 8 候选判定 / 9 实验判定 | `truth.candidate_verdict` / `truth.experiment_verdict` |

**独立真值：** `truth.kernel_defects`（观察者从 `/proc` 读 C1–C5、C7）与场景拓扑核对（不符 ⇒ `TOPOLOGY_NOT_AS_DESIGNED`，台架 BLOCKED）；根的自报指纹与观察者读数不一致 ⇒ `TRUTH_SOURCES_DISAGREE`；监督器桩用**独立的** ctypes `prctl(PR_GET_CHILD_SUBREAPER)` 复读标志，与候选自己的调用对账；节点存活由 pidfd + `/proc` 双来源判断；`pidfd` 只用于身份与生命周期，**从不用于推断血缘**（血缘来自登记时的创建者记录）。

## 6. 自审中发现并已修复的问题（均在任何执行之前）

1. 预注册：C5 措辞、场景 d 构造、实验级聚合规则（第 1 节）。
2. `select.select` 在描述符 ≥ 1024 时会失败 → 全部改用 `poll`（`common.poll_ready`）。
3. 对已死亡（僵尸）进程打开 pidfd 被误报为“身份不符” → 新增 `AlreadyExited`，janitor 记为 `gone`。
4. 登记失败的直接子进程不会被回收 → 记录 `forked_pid`，`reap_direct` 按**具体 pid** 回收。
5. 盲性检查原用运行目录名，会被包装脚本的重定向误伤 → 只禁止登记文件路径、`registry.jsonl`、角色词；包装脚本的输出文件名不含这些词。
6. `exec` 的 Python 会在 CPU-001/002 目录写 `__pycache__` → 加 `-B`。
7. L4（伪终端）的主端关闭先于清理会触发挂断竞争 → 改为清理之后再关闭。
8. janitor 寿命上限 900 s 可能短于完整运行 → 3600 s。
9. ERRATA-002 的 R5（已释放节点不经协议 fork 后代）原只有 S0 前对账 → 增加 S0 后对账与运行结束的令牌扫描（仅诊断）。
10. 校验工具：`BV-1..BV-10` 比较原用字典序列表，已改为集合比较。
11. 运行级有效性检查之间的清理标签，避免误杀运行级节点（janitor）。

## 7. 未验证的风险与未知（审核者请重点看）

| ID | 内容 |
|---|---|
| S-1 | **所有进程级路径从未执行**：`AF_UNIX/SOCK_SEQPACKET` + `send_fds/recv_fds` 在 Python 3.13.16 / 内核 6.18.44 上的行为、`exec` 后 fd 3 继承、pidfd 对僵尸“可读”的语义、`poll` 对 pidfd 的行为，全部是**设计假设**。首次受控运行的头几个失败很可能是台架缺陷（CPU-001/002 的历史如此）。 |
| S-2 | ERRATA-002 R1–R7 的映射：R1（未释放进程不自行退出）→ BV-2/BV-3 检测，令牌扫描只诊断，不发信号；R2（观察者与 janitor 同时失效）→ 无自动清理，只能人工；R3（pid 复用且 `starttime` 相同）→ 概率极低但非零，`pidfd_open` 先于核对；R4（掉电）→ 范围外；R5 → 谱系对账 + 令牌扫描；R6（门写端泄漏）→ BV-8 + `T_gate_max`；R7（观察者缺陷）→ 单线程、极简，测试已写未跑。 |
| S-3 | 盲性是**构造性**的（同一 uid 下不构成安全边界）；监督器在 L1/L2 继承运行器的 stdio，包装脚本必须把输出重定向到不含禁止词的文件（见 `run_e1a.sh`）。 |
| S-4 | 场景 `E1A-g` 依赖“`SIGCHLD=SIG_IGN` 经 `execve` 保留，且 Python 启动后 `getsignal` 返回 `SIG_IGN`”两条假设。 |
| S-5 | 场景 `E1A-a2` / `E1A-i` 依赖“X 在监督器尚未成为 subreaper 时被孤立，因此不被收养为监督器的子进程”；若环境存在其它 subreaper 祖先，X 仍是非子进程，但需首次运行确认拓扑（`TOPOLOGY_NOT_AS_DESIGNED` 会捕获）。 |
| S-6 | L4（控制终端）需要伪终端；不可用则 L4 单元 INSUFFICIENT（实验 BLOCKED），不是失败。 |
| S-7 | 单环境（Firecracker 微型虚机、内核 6.18.44-fc-v165、uid 0、cgroup v1）、单 Python 版本；结论不外推。 |
| S-8 | 测试文件（含纯逻辑测试）**未运行**，可能含错误；它们的期望值来自冻结的预注册，不来自观察。 |
| S-9 | 完整计划 1120 次试验（36 个单元 + 400 次误拒扫描）的耗时未测量，未做 5,000 次压力运行。 |
| S-10 | E1-A 只检验 S0 判定及其无副作用，**不检验**后续归属质量（E1-B/C/D，仍待负责人批准，未冻结）。 |

## 8. P3 / P4 只读调研（未改任何系统配置）

- `/proc/self/cgroup`：仅 cgroup **v1** 控制器（`pids`、`memory`、`cpu`……）；`/sys/fs/cgroup` 下有 `unified` 目录但 `/proc/mounts` 中没有 cgroup2 挂载。
- `/proc/config.gz`：`CONFIG_CONNECTOR=y`、`CONFIG_PROC_EVENTS=y`、`CONFIG_CGROUPS=y`、`CONFIG_CGROUP_PIDS=y`、`CONFIG_PID_NS=y`；存在 `/proc/net/connector`；当前 uid 0。
- **没有**打开 netlink 套接字、没有订阅 proc connector、没有创建 cgroup。因此 P3/P4 仍是 **UNVERIFIED**（只知道内核配置与挂载布局），未被宣称为 PROVABLE。

## 9. 给审核者的检查清单

1. 预注册（`f9d3cd8`）：分类矩阵是否与 ECD 一致？两次更正是否合理、是否在台架之前？
2. `truth.judge` 与预注册第 1–9 步是否逐条一致？
3. 插桩 / `S0` 阶段标签是否可能漏记候选的 kill / wait？
4. 门协议的状态机（`observer.py`、`gate.py`、`node.py`）：是否存在释放前动作、描述符泄漏或死锁路径？
5. `janitor.run_cleanup` 是否在任何路径上对未确认身份的进程发信号？
6. 场景拓扑（`scenarios.RECIPES`）与预注册 `construction` 文字是否一致？
7. 是否有被遗漏的“台架不可验证”条件？
8. 首次受控运行前还需要哪些条件（建议：先做 `--only E1A-a:P2 --reps 1` 之类的单格冒烟，由负责人单独授权）。

## 10. 文件清单与哈希（提交时刻）

| 文件 | 行数 | SHA-256 |
|---|---|---|
| `bench/candidates.py` | 192 | `f7cf1141863b55f83f96bbc7193b89060bd7295487f93bc8451f6fe11fbe3d5f` |
| `bench/common.py` | 238 | `1b9252047fbc2411ebccb105b88d5491c546194c37f9d7711fb01656ee302a4c` |
| `bench/e1a_runner.py` | 245 | `aa71a6a0653b81b017a9432ad372349a4a162328ca4c5eee231e4d8b944bcd58` |
| `bench/gate.py` | 82 | `e4989e350a55c3d39f4058d5dd8ae1207f70f1b380971d2e2495aacf835ad680` |
| `bench/janitor.py` | 90 | `3802aad7a6eaee706f5390b05d8cc0d7bf5c1a42ca7a0d37d385b0f41b2329b8` |
| `bench/node.py` | 75 | `1b2a76b6e0c2569d5733d36e393c59bcd32545403236fc485c639352a78f6607` |
| `bench/observer.py` | 308 | `07ae2b221e7f17b536b40a89af81a5730dda411e017c043d8013c74fc6a3dc38` |
| `bench/proto.py` | 98 | `400b05f83111e0ff9cb79bd810626b0725d2c152ae686fc60b593ff748ba5d31` |
| `bench/registry.py` | 115 | `310e0824a0f1ec3edca27a3dd4665c006d40780cb930e668262ce084a8db3d5b` |
| `bench/scenarios.py` | 96 | `1c056cf9b212834fc246503fa70ef6b519e1f1b9e247c85cfce6beeed4b589fc` |
| `bench/sup_stub.py` | 147 | `2a66b79900e418a2bff5e83434d6516dcbc60421423fe0c4799a82b58e735c86` |
| `bench/trial.py` | 235 | `d64ef8a2b9dc73f17e6391ed16f917208ba4e35c7622b7c5ad9504c5b64cbbed` |
| `bench/truth.py` | 185 | `5bddde930f748c5f37acacd65b62adf4539c2a036bb8aa8bdceef4db8fb9a9dc` |
| `bench/validity.py` | 164 | `4ea5f62db9dee9e24aee033c04e0c3b385d0f4fc248e31cd76d073f2a896fb32` |
| `tests/test_e1a_gate.py` | 105 | `63cdbfb232f3f83b4770acc3bbe0fb3fe5e3f1cbc5c2b546b811d2509162809b` |
| `tests/test_e1a_logic.py` | 274 | `4910f3761fb3c3d46a17a076c5f4a57b6dd6464eb2406d4b9f539172f68bfac2` |
| `tests/test_e1a_runner_interlock.py` | 43 | `08291260ef78661427c9cf34ca6161bcaf7402490d120f090cb3129e7eb2fd52` |
| `tools/check_prereg_schema.py` | 108 | `94728063b039c15755f65112b1409aa87a548ca0c42c9b84165cea39177082e9` |
| `tools/static_audit.py` | 122 | `c4a1e4c01f18827470995b1820c5296a65201bb63582429ab837fdc7f6b8c310` |
| `run_e1a.sh` | 19 | `aaab833f7414f2a8db1d5b41abf4fd05d9a522eb7a5af245a53728b20317cb02` |
| `prereg/e1_provability_table_v1.json` | 992 | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| `prereg/e1_provability_table_v1.json.sha256` | 1 | `f3b8ae6f47f4a802eed650f866c580b60de36df4e9a880c9c78dfd25e8c3afc4` |

静态检查结果：`check_prereg_schema.py` ok=True；`e1a_runner.py --check` ok=True（预注册 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）；静态审计 0 条违规。
