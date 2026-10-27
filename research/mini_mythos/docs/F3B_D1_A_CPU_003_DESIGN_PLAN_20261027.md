# F3B-D1-A-CPU-003 — 安全监督器最小受控实验：设计计划与预注册判据

**状态：`CPU-003 DESIGN COMPLETE / EXPERIMENTS NOT TESTED / DESIGN ONLY / NOT AUTHORIZED TO EXECUTE / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

**勘误（F3B-D1-A-CPU-003-DESIGN-ERRATA-001，2026-10-27）：**本文件已按 `F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md` 就地修订（ERRATA-01 `UNKNOWN` 率验收、ERRATA-02 独立真值、ERRATA-03 安全清理、ERRATA-04 机制状态与实验判定分层；第 10 节列出每处改动）。与本文件旧文冲突之处，以勘误文件为准。历史版本见提交 `6c8bab5`。

**勘误-002（F3B-D1-A-CPU-003-DESIGN-ERRATA-002，2026-10-27）：**在 ERRATA-001 之后追加两处最小修订，见 `F3B_D1_A_CPU_003_DESIGN_ERRATA_002_20261027.md`——(1) 歧义负例改为**按候选机制预先分类**（PROVABLE / UNPROVABLE / BENCH_UNVERIFIABLE，证据能力声明 ECD + 证明规则 + 执行前冻结）；(2) 清理中的创建 / 登记改为 **GATED-SPAWN 协议**（意向记录 → 门 → 登记持久化 → RELEASE；失败关闭）。第 10 节列出改动。`UNKNOWN` 率 0%、台架 BLOCKED 5%、每单元 ≥ 50 仍是建议值，待负责人批准。

本文件只**设计**实验、预先登记独立真值与验收判据。**不执行任何实验**，不启动任何进程故障注入；三项实验（E1 归属、E2 唯一回收者、E3 崩溃恢复）的状态均为 **DESIGN ONLY / NOT TESTED**。判据一经提交，运行后不得为得到 PASS 而修改；若判据本身有错，只能追加带日期的修订记录并保留原判据与原结果（沿用 CPU-002 的做法）。

候选设计、依赖与优缺点见 `F3B_D1_A_CPU_003_ARCHITECTURE_OPTIONS_20261027.md`；Git 状态、证据来源与权限边界见 `F3B_D1_A_CPU_003_CHECKPOINT_20261027.md`。

## 1. 目标与证据基础

在 CPU-001（两种方案在正常矩阵中均正确，无胜者）与 CPU-002（归属前提被违反时误杀 / 误回收；CA 与 Popen 竞争回收污染退出码，CB 在 T5 之后同样；CB 遗漏 T5 滞留僵尸，CA 在监督器崩溃后丢失内存状态）之后，为**未来 R3 修订评审**提供三个可独立验收的最小 CPU 实验方案：

| 实验 | 要回答的问题 | 对应原则 |
|---|---|---|
| **E1** 安全进程归属与 S0 前置条件 | 监督器怎样**确保**只终止、回收阶段真正拥有的进程？无法确认时怎样安全停止？ | P1 |
| **E2** 唯一回收者与退出状态一致性 | 怎样保证每个子进程恰有一个消费退出状态的责任方，且未知状态绝不当成功？ | P2 |
| **E3** 监督器崩溃与恢复责任 | 监督器死亡后谁终止遗留目标、回收僵尸、保全状态，且不误杀非目标？ | P3 |

P1–P3 是 ChatGPT 与 Grok 审核共同的三项原则（依据负责人指令的转述；仓库中没有 Grok 的审核文件，本会话也没有收到其原文，见检查点第 3 节）。

**每个实验都必须回答：什么证据会让我们否定当前设计。**每张实验卡都有「Falsification」一行；计划不只设计有利于候选方案的测试。

## 2. 三个实验共同的约定

### 2.1 COMMON-ENV（环境）

Linux microVM；设计时测得：内核 `6.18.44-fc-v165`、Python 3.13.16（另有 3.11.15、3.12.3；**3.9 / 3.10 / 3.14 不可用**）、root（uid 0）、4 CPU、`os.pidfd_open` / `signal.pidfd_send_signal` / `os.waitid` / `WNOWAIT` / `PR_SET_CHILD_SUBREAPER` 可用、**仅有 cgroup v1 控制器（无 v2 `cgroup.controllers`）**、内核配置 `CONFIG_CONNECTOR` / `CONFIG_PROC_EVENTS` / `CONFIG_PID_NS` 开启。每次执行必须重新记录并核对这些值；差异写入分片的 `environment`。仅标准库、无网络、无 GPU、无真实数据。**未测：非 root、其它内核、其它发行版。**

### 2.2 COMMON-GIT（Git SHA 纪律）

执行前登记：计划提交 SHA、代码提交 SHA、工作树干净；每个结果分片记录 `git_commit` 与 `git_status_short`（CPU-002 运行时存在未跟踪文件的教训：先把所有代码提交再运行）。设计阶段不产生运行 SHA。

### 2.3 COMMON-ORACLE（独立真值原则；ERRATA-02 修订）

真值只来自**台架**，绝不来自被测机制的输出，且分成两类来源，**不得混用**：

1. **生命周期 / 身份稳定性真值：**`pidfd` 可读性 + `/proc` 状态 + 对子进程的 `waitid(WNOWAIT)`（两个独立来源必须一致，否则台架 BLOCKED）。`pidfd` 只说明"这个句柄仍指向同一个进程、它是否已退出"，**不能证明血缘 / 归属**。
2. **归属真值：**台架在**创建时**建立的**独立谱系账本**——节点 ID、创建者、角色（`stage` / `aux` / `aux_family` / `stranger`）、创建序号、出生时的 `(pid, starttime)`、声明的后续操作（`setsid`、双重 fork、退出）。账本由台架观察者持有；**被测监督器必须"盲"**：它作为独立进程启动，`argv`、环境、打开的文件描述符里都没有账本或角色；节点规格走控制通道，**不再放进 `argv`**（CPU-001 / CPU-002 的节点把含节点名的规格 JSON 放在命令行里；被测臂只读 `/proc/<pid>/stat`，不读 `cmdline`，已有结论不受影响，但未来要求更严）；盲性条件启动前由台架断言，不成立则该试验台架 BLOCKED。同 uid 下这是**构造性**的盲，不是安全边界。

后代执行 `setsid()`、双重 fork、父进程退出之后，仍**按创建谱系**判定其真实归属。对被测机制确实无法区分的进程，必须允许其返回 `UNKNOWN`。**【ERRATA-002 修订】**"无法区分"取决于**该候选机制的证据能力声明（ECD）**：每个（场景 × 机制）在执行前被静态分类为 PROVABLE（期望带合法证明引用的正确确定答案）/ UNPROVABLE（期望 `UNKNOWN`；给出确定答案，即使碰巧正确，也是 FAIL）/ BENCH_UNVERIFIABLE（台架无法建立真值 → 台架 BLOCKED），分类表在执行前冻结（`e1_provability_table_v1.json`，哈希写入每个分片），观察结果后不得改类。区分三种情形：**台架已知真相且机制能证明**（期望确定答案）/ **台架已知真相但机制无法证明**（期望 `UNKNOWN`）/ **台架自己无法建立真值**（该试验台架 BLOCKED）。`/proc` 字段相同（`ppid`、`comm`、会话、`starttime` 顺序等）**不等于**已证明身份 / 归属相同。

E3 另设**台架观察者**进程（不属于任何被测机制），故障前对所有节点持有 `pidfd` 并保存登记；退出码由节点声明、信号由台架施加。

### 2.4 COMMON-STATES（机制状态 vs 实验判定；ERRATA-04 修订）

**两个层次，不得混用：**

- **机制协议状态**（被测机制产生）：`ALIVE` / `EXITED` / `UNKNOWN` / `BLOCKED`（含 S0 原因码）等。
- **实验验收判定**（台架按预注册期望给出）：`PASS` / `FAIL` / `BLOCKED` / `NOT TESTED`。**实验 `BLOCKED` 只表示台架层无法建立或完成预注册场景**（拓扑无法构造、两个独立真值来源不一致、真值不可得、工具异常、清理失败、设施不可用）；**机制返回 `BLOCKED` 不会自动成为实验 `BLOCKED`**——符合预期则实验判 `PASS`。`NOT TESTED` = 尚未运行。

典型映射：错误配置被 S0 正确拒绝 → 机制 `BLOCKED`、实验 **PASS**；错误配置被接受并执行危险操作 → 实验 **FAIL**；身份歧义负例正确返回 `UNKNOWN` → 实验 **PASS**；明确目标被错误判为 `EXITED` → 实验 **FAIL**；台架无法构造场景 → 实验 **BLOCKED**；场景未运行 → **NOT TESTED**。完整表见勘误文件第 4 节。

每条记录带 `evidence_kind ∈ {REAL_KERNEL, SIMULATED, INSTRUMENTED}`：真实进程与真实系统调用 / 注入的故障（`/proc` 错误、替换 pid、`ECHILD`）/ 对标准库调用的计数。**不可构造的内核拓扑不得靠伪造声称漏洞复现。**工具正确性（单元测试）与规则判定分开记录。

### 2.5 COMMON-SAFETY（安全边界）

仅创建带运行令牌的牺牲进程；每个用例在**专用新会话**（台架 fork 的会话领头）中运行；只对已登记且指纹匹配的 pid 发信号，经 `pidfd`；回收只针对登记 pid；禁止 `pkill`、按名称匹配、`waitpid(-1)`、`P_ALL`；总子进程数 ≤ 400，线程数 ≤ 16，僵尸批量 ≤ 300；不触碰 pid 1、终端、编辑器、其它用户或系统服务；每个用例有短超时与 `finally` 清理；身份无法确认就不发信号并（台架层）报告 BLOCKED；**清理动作同样受本节约束并计入误信号统计**；特权设施（proc connector、cgroup）仅做只读 / 可行性探针，不修改系统配置。

### 2.6 COMMON-CLEANUP（清理规则；ERRATA-03 替换原文）

原文第 (2) 步"按命令行令牌 + `starttime ≥ 运行起点` 扫描后杀死"**作废**：命令行令牌可伪造 / 碰撞，不能授权发信号。新规则：

1. **创建时登记（【ERRATA-002 修订】GATED-SPAWN 协议，见 ERRATA-002 §2）：**意向记录 `INTENT` 先于 `fork()` 写入登记文件 REG；新进程创建后**先停在门（管道）上**，不执行实验动作、不 `exec`、不创建后代；观察者取得 `pid`，`pidfd_open`，核对 `starttime/sid/pgrp`，`write` 追加 `REGISTERED`，**写成功之后**才向门发 `RELEASE`；登记失败 / 身份核对失败 / 观察者超时 / 观察者死亡 → 不发 RELEASE，新进程读到 `EOF`/`ABORT`/自身超时 `T_gate_max` 后**自行退出**；后代由已登记节点经门票协议创建，节点不能自行释放后代。无法登记者记为 `UNREGISTRABLE`，不得对其发信号。台架中不存在不经此协议创建的牺牲进程。
2. **清理只经登记：**对存活的牺牲进程，先重新核对登记的 `(pid, starttime)` 与 `/proc` 一致，再 `pidfd_send_signal(SIGKILL)`；回收只用具体 pid 的 `waitpid`（仅自己的子进程）。
3. **命令行令牌只做诊断：**扫描 `/proc/*/cmdline` 仅产生残留报告，**绝不授权发信号**。
4. **禁止：**`pkill`、仅按名称匹配、无法验证身份的进程组清理、`kill -- -pgid`、清理性的 `killpg`（CPU-002 的 `run_in_fresh_session` 曾对台架自己创建的会话领头的进程组用 `killpg`，CPU-003 不再允许）。
5. **身份无法确认 → 停止自动发信号：**记录残留（pid、`starttime`、`ppid`、状态、`cmdline` 片段），该试验**台架 BLOCKED**，**不开始下一个试验**。**【ERRATA-002 修订】**另：观察者死亡后超过 `T_gate_max` + 余量仍存在未释放且未退出的进程（ERRATA-002 剩余风险 R1）→ 只做诊断，不发信号，实验 BLOCKED。
6. **最终清理责任（含 E3 中监督器与 Watchdog 同时失效）：**台架观察者独立于所有被测组件，是最终清理者，其登记持久化到只有它写的追加文件；若观察者也失效，由外层运行脚本 **janitor** 读取该文件。**【ERRATA-002 修订】**janitor 只对 `INTENT` + 完整 `REGISTERED` 的记录行动：**重新** `pidfd_open(pid)`（旧描述符整数在观察者死后不可恢复），**再**核对 `starttime`，一致才发 SIGKILL，不一致则不发信号、记录并 BLOCKED；只有 `INTENT` 的进程按协议已自行退出，不对其发信号；REG 末行缺换行符视为撕裂并忽略（因 RELEASE 只在 `REGISTERED` 写成功后发出）。janitor 之外没有自动层，其失效为**残余风险**，须在报告中写明；完整剩余风险 R1–R7 与 BLOCKED 条件见 ERRATA-002 §2.5。本设计只要求**普通进程崩溃**恢复，不扩展为掉电恢复。
7. **失败留痕：**任何自动清理失败都写入诊断文件（登记、验证结果、残留）并保留，**不得悄悄继续**。
8. 清理后做残留检查（登记表、令牌扫描结果仅供对照、监督器的子进程列表），删除临时目录。

### 2.7 COMMON-REPS（重复档位）

| 档位 | 次数 | 用途 |
|---|---|---|
| T0 | 确定性场景 ×5；竞态场景 ×50 | 冒烟与回归 |
| T1 | 竞态 ×500 | 中等压力 |
| T2 | ×5000 | 仅经负责人批准 |
| 强制交错钩子 | 每个操作顺序 ×1（确定性） | **优先于重复次数作为证据** |

**任何档位的「零失败」只说明本轮未观察到错误，不能证明竞态不可能存在。**

### 2.8 COMMON-EVIDENCE-HYGIENE（证据入库纪律）

教训来自 CPU-001 / CPU-002：仓库 `.gitignore` 的 `parts/`（第 101 行）、`*_archive`（第 256、394 行）、`*.log`（第 141 行）以及 `dist/ lib/ var/ downloads/` 等规则会**静默**排除证据，而我两次在没有核对的情况下写成"已提交"。未来所有实验：(1) 规划证据路径时先 `git check-ignore -v`；(2) 证据目录与文件名避开这些模式（不使用 `parts/`、`*_archive`、`*.log` 命名）；(3) 提交后用**远端提交的文件树**（`git ls-tree` / GitHub 文件树）核对每个声明的文件存在，并核对大文件的 blob SHA-256；(4) 报告里的"已提交"只能指已被上述核对的文件。

### 2.9 预注册规则

本文件提交后、任何 CPU-003 运行之前，判据冻结；修订只追加。

## 3. 执行顺序、依赖与待批准事项

**依赖：**E3 的恢复机制需要知道 E1 的登记表（持久化什么）与 E2 的消费者决定（状态在内核还是只在内存），所以 E3 最后；E1-D 依赖 E1-A/B/C 的入围机制；E2-R 依赖 E2-A/B/C。

| 阶段 | 内容 | 前置 |
|---|---|---|
| Stage 0（无进程测试） | E2-V 的**只读**部分（源码审计，已有初步结果）、环境能力清单 | 无（本轮已做初步阅读） |
| Stage 1 | E1-A → E1-B → E1-C → E1-D | 负责人授权 + 阈值决定 + **冻结 `e1_provability_table_v1.json`（ERRATA-002 §1.3；须先于运行代码提交）** |
| Stage 2 | E2-V（运行部分）→ E2-A / E2-B / E2-C → E2-R | 负责人授权 + Python 版本策略 |
| Stage 3 | E3-0 → E3-A / E3-B / E3-C | E1、E2 的结果 + 恢复范围决定 |

**需要负责人决定 / 批准（本计划不替负责人决定）：**

1. 每个 Stage 的执行授权（建议逐 Stage 单独授权）。
2. `UNKNOWN` 率阈值：**W1、W2 目标 0% 是 ChatGPT 建议的预注册门槛，需负责人在执行前正式批准**（度量定义见勘误 ERRATA-01：N 类 `UNKNOWN_rate = U-unexp / (计划试验数 − 台架 BLOCKED)`；负例正确 `UNKNOWN` 计 PASS；安全性与可用性分开报告）；5% 台架 BLOCKED 上限与每单元 ≥ 50 个试验同为提议值。
3. 支持的 Python 版本范围（本环境 3.11 / 3.12 / 3.13；3.9 / 3.10 / 3.14 无法验证）。
4. 是否允许特权设施（proc connector、cgroup）作为证据源，及"仅 root 环境"的风险是否可接受。
5. 恢复范围：自动恢复（Watchdog / 账本）还是 `BLOCKED` + 清理工具；Watchdog 是否在 D1 范围内。
6. T2 档位（×5000）是否批准。

## 4. E1 — 安全进程归属与 S0 前置条件

**共同验收门槛（所有 E1 卡）：**非目标收到误信号 = 0；非目标被误回收 = 0；无法确认归属时**不得猜测**（`UNKNOWN`）；配置错误时安全停止（`BLOCKED`，在任何破坏性动作之前）；真实目标后代不得被遗漏而报告 `EXITED`；明确区分「能安全终止」与「只能返回 `UNKNOWN`」。

**可在真实内核构造 vs 只能注入：**

| 场景 | 证据类型 |
|---|---|
| 根不是会话领头 / 与监督器同会话、旁观者在同会话 | REAL_KERNEL（CPU-002 E1-S2 已构造） |
| 正确启动下的同会话非阶段进程 | **内核不可构造**（`setpgid` 跨会话 → `EPERM`，CPU-002 E1-S1）；不得声称复现 |
| 封闭世界被违反（监督器有未登记子进程） | REAL_KERNEL |
| 绕过登记入口的 `fork` | REAL_KERNEL（台架牺牲代码执行） |
| `SIGCHLD=SIG_IGN` 继承 | REAL_KERNEL |
| 子收割者设置失败 / 读回 0 | SIMULATED |
| 指纹被替换（pid 复用） | SIMULATED（真实 pid 回绕不计划） |
| proc connector 事件丢失 | SIMULATED（如可用） |


### CPU-003-E1-A — S0 会话前置条件

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E1-A — S0 会话前置条件 |
| **Purpose** | 验证 S0 在**任何破坏性操作之前**拒绝错误配置的阶段根（不是会话领头、与监督器共用会话、进程组不对、已有未登记子进程、SIGCHLD 被忽略、子收割者设置 / 读回不一致），并接受正确配置。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：需要 `os.setsid`、`os.getsid`、`prctl`、`pidfd`；Python 3.13.16 为主。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 监督器在专用新会话里运行（台架 `run_in_fresh_session`）。阶段根变体：(a) 正确：新会话领头，`sid==pgid==pid` 且 `sid != 监督器 sid`；(b) 根与监督器同会话；(c) 根自成进程组但同会话（`setpgid(0,0)`，无 `setsid`）；(d) 根不是进程组领头；(e) S0 时根已带未登记子进程；(f) 登记后指纹变化（`starttime` 被注入改动）；(g) 监督器的 `SIGCHLD` 处置为 `SIG_IGN`（经 `exec` 继承，真实内核行为）；(h) 子收割者设置失败 / 读回 0（SIMULATED）；(i) 同会话旁观者 X（牺牲进程）存在。被测候选：S0 谓词 `s0_check()`（O-2 的定义），对照：O-0（无检查）与 O-1（CA-S / CB-S 的 `preflight`）。 |
| **Independent Oracle** | 生命周期 / 身份稳定性：`pidfd` + `/proc` + `waitid`（`pidfd` 不证明血缘）；拓扑与角色真值：台架**创建时**建立的谱系账本（被测监督器盲，见 2.3）；破坏性动作 = 对牺牲旁观者 X 发信号，真值 = X 的 `pidfd` 状态与信号日志；`SIGCHLD` 处置读自 `/proc/<pid>/status` 的 `SigIgn`。 |
| **Expected Result** | (a) 被接受（机制进入 ALIVE / EXITED 等正常状态）；(b)(c)(d)(e)(f)(g)(h) 在发出任何信号或回收之前，机制返回 `BLOCKED(具体原因码)`——**这是机制状态；实验判 PASS**；O-0 对 (b)(i) 预期失败即不安全（CPU-002 已证）。 |
| **PASS Criteria** | 每个错误配置：S0 在第一次信号 / `wait*` 之前返回 `BLOCKED` 及预期原因码；信号总数 = 0；`wait*` 对非目标 = 0；牺牲旁观者全程存活。正确配置：被接受，**误拒 = 0**（T0 与 T1 档）。 |
| **FAIL Criteria** | 任一错误配置被接受；拒绝发生在已有信号或回收之后；原因码缺失或错误；正确配置被误拒；旁观者被触碰。 |
| **BLOCKED Criteria** | **实验层**（台架）：台架无法构造某个拓扑（内核拒绝 / 权限不足）→ 该变体实验 BLOCKED 并如实记录，不得用伪造替代；`pidfd` 不可用；盲性断言不成立。**机制返回 BLOCKED（S0 拒绝）若符合预期，实验判 PASS，不是实验 BLOCKED。** |
| **机制状态 → 实验判定映射（ERRATA-04）** | S0 对错误配置 `BLOCKED(原因码)` → PASS；错误配置被接受 / 先发信号后拒绝 → FAIL；正确配置被 `BLOCKED` → FAIL（误拒，可用性）；台架无法构造 / 盲性不成立 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性：每个变体 ×20；(a) 的误拒检查另加 T1 ×50（不同启动上下文：直接 `setsid`、`nohup`、有 / 无控制终端）。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：所有错误配置只在专用新会话里构造；牺牲进程只在该会话内；不对监督器自己的会话外任何进程发信号。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：**不使用 `killpg`**；专用新会话里的牺牲进程全部经登记 + pidfd 清理，令牌扫描只做诊断。 |
| **Evidence Files** | `a_predicate_003/results/e1a_*.json.gz`、分片 stdout / stderr、`final_integrity_verification.txt`（**路径设计：必须避开 `.gitignore` 的 `parts/`、`*_archive` 等规则，提交前以 `git ls-files` 与远端树核对**）。 |
| **Known Limitations** | 仅 root；仅单内核；S0 谓词是设计草案，不等于真实 R3 启动器；不测真实 Driver。 |
| **Falsification（什么证据会否定当前设计）** | 任何错误配置通过 S0；或正确配置在合理启动上下文（`nohup`、有 / 无 tty、作为会话领头）下被误拒——说明谓词过弱或过严。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E1-B — 封闭世界前提的强制机制比较

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E1-B — 封闭世界前提的强制机制比较 |
| **Purpose** | 找出一种**可验证或可强制**（而非靠人工声明）的机制，使监督器只处理阶段真正拥有的进程：比较 M0 原算法、M1 登记表 + S0 空子进程检查（O-2）、M2 专用监督器进程 + M1（O-3）、M3 严格变体（O-1），以及仅作可行性探针的 M4 cgroup（O-4）与 M5 proc connector（O-5）。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：M4：本环境只有 cgroup v1 → 预期 BLOCKED（环境不满足）；M5：需要特权与内核支持，仅做可行性探针，失败即 BLOCKED。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | B1 阶段开始**之前**已有的辅助子进程（已登记 / 未登记各一）；B2 运行中经受控入口新增的辅助子进程；B3 运行中**绕过入口**新增（裸 `os.fork`、另一线程里的 `subprocess`）——对抗性用例；B4 已登记辅助进程及其后代，辅助进程死亡后后代被重新挂靠；B5 来源不明的未登记孤儿在阶段内同时存在真孤儿时出现（歧义用例）；B6 阶段后代在两次轮询之间诞生并成为孤儿（轮询间隔 10 ms / 100 ms / 1 s）。每个进程带台架标签 `role ∈ {stage, aux, aux_family, stranger}`。 |
| **Independent Oracle** | 归属真值 = 台架创建时的**谱系账本**（创建者、角色 `stage/aux/aux_family/stranger`、出生指纹、声明操作），被测机制盲；`pidfd` + `/proc` 只提供单个进程的身份稳定性与生命周期，**不证明血缘**；`stranger` 的存活 / 僵尸状态由 `pidfd` + `/proc` 判定；`/proc` 字段相同不等于身份相同。区分「真相已知但机制无法证明」（期望 `UNKNOWN`）与「台架无法建立真值」（台架 BLOCKED）。 |
| **Expected Result** | `stranger` 永不被信号 / 回收；`aux`、`aux_family` 不被动；**按预先冻结的分类**：PROVABLE 场景得到带合法证明引用的正确确定答案（目标被终止并回收 / 非目标被排除）；UNPROVABLE 场景得到 `UNKNOWN`（或明确的 `INTRUDER` 诊断，不发信号），**不猜测**。哪些（场景 × 机制）是 PROVABLE / UNPROVABLE 见 ERRATA-002 §1.4 的初始分类表（B3、B5 对 P0–P2 是 UNPROVABLE，对有事件流 / cgroup 证据的 P3 / P4 是 PROVABLE）。 |
| **PASS Criteria** | K1（误信号）= 0 且 K2（误回收）= 0，在**所有**拓扑与机制组合中（每个机制单独统计）；不得出现「真阶段后代仍存活却报告 EXITED」；**PROVABLE 试验**：带合法引用的正确确定答案；**UNPROVABLE 试验**：`UNKNOWN` / `INTRUDER`；每个机制的 ECD 与分类表执行前冻结。 |
| **FAIL Criteria** | 任一误信号或误回收；任一假 `EXITED`；对 `stranger` 的任何猜测性归属；**UNPROVABLE 试验上的任何确定答案（即使碰巧正确）**；**PROVABLE 试验上的错误或无合法引用的确定答案**。**机制的 FAIL 如实保留，不据此改判据或改分类。** |
| **BLOCKED Criteria** | **实验层**（台架）：M4 / M5 的设施不可用 → 对该候选机制实验 BLOCKED（环境无法评估，不计该候选 PASS / FAIL）；拓扑不可构造；盲性断言不成立；谱系账本记录丢失（真值不可得）。机制对 B3、B5 返回 `UNKNOWN` / `INTRUDER` 属预期，实验判 PASS。 |
| **机制状态 → 实验判定映射（ERRATA-04）** | UNPROVABLE 试验返回 `UNKNOWN` / `INTRUDER` → PASS；PROVABLE 试验带合法引用的正确确定答案 → PASS；把 `stranger` 当目标并信号 / 回收 → FAIL；PROVABLE 试验返回 `UNKNOWN` → 可用性缺失（单独记录）；M4 / M5 设施缺失 → 对该候选实验 BLOCKED；BENCH_UNVERIFIABLE → 台架 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性拓扑 ×5；B6 竞态每个轮询间隔 ×50（T1），另加强制交错钩子各 ×1（确定性，优先于重复次数作为证据）。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：B3 的「绕过入口」只由台架自己的牺牲代码执行；`stranger` 一律是牺牲进程。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：`stranger` 不属于被测机制，由台架清理。 |
| **Evidence Files** | `a_predicate_003/results/e1b_*.json.gz`；M4 / M5 的可行性探针输出单独成文件。 |
| **Known Limitations** | M2 的「结构保证」在 Python 层只能近似；不测真实 Driver 内部是否 `fork`；轮询间隔内的短命进程原理上不可见。 |
| **Falsification（什么证据会否定当前设计）** | M1 / M2 在 B3 下仍误归属；或为避免误归属而使合法的 B2、B4 全部 `UNKNOWN`（不可用）；M3 在合法负载上 `UNKNOWN` 率过高（见 E1-D）。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E1-C — 跨 Session 的真实目标后代

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E1-C — 跨 Session 的真实目标后代 |
| **Purpose** | 后代 `setsid()` 之后仍可能属于目标，不能因 SID 不同而排除。设计受控对照，区分**真后代、无关进程、无法归属者**，并比较各种证据源所能提供的区分能力。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：证据源：E-lineage（轮询 `/proc` 的 ppid 闭包 + 连续登记）、E-registry（O-2）、E-procconn（O-5，若可用）、E-cgroup（O-4，若可用）。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | C1 已登记的后代随后 `setsid()` 且父进程死亡（连续性）；C2 后代在首次轮询前就 `setsid()` 并被孤立；C3 双重 fork 守护进程（有 / 无子收割者）；C4 三层链，中间层 `setsid()` 后死亡；C5 **look-alike 陌生进程**：与真孤儿在所有 `/proc` 可见字段上一致（`ppid==监督器`、同一 comm / cmdline 令牌、`starttime` 晚于根、自成会话），仅创建者不同——预期在仅轮询证据下**不可区分**；C6 后代 `exec` 了别的程序；C7 阶段内部多个后代同时 `setsid()`。 |
| **Independent Oracle** | **谱系账本**（创建者标签 + 声明的 `setsid` / 双重 fork / 退出）给出真值；后代执行 `setsid()` 或父进程退出后**仍按创建谱系**判定归属；决策真值表：{目标 / 非目标 / 机制**设计上无法证明**}。C5 的 look-alike 在 E-lineage 下是「真相已知、机制无法证明」，期望 `UNKNOWN`，**不是**「台架无法建立真值」，也不是「非目标」；`pidfd` 不证明血缘。 |
| **Expected Result** | 按 ERRATA-002 §1.4 的冻结分类：有连续性证据（C1、C4 每一跳被观察、C6、B6a）的后代对所有机制是 PROVABLE，被识别为目标；C2、C3、C5、B6b 对仅轮询 / 登记证据的机制（P0–P2）是 UNPROVABLE，期望 `UNKNOWN`；对具备事件流 / cgroup 证据的机制（P3 / P4）是 PROVABLE，期望正确的确定答案（C5 判为非目标）。 |
| **PASS Criteria** | 对每个证据源 / 机制：误信号 = 0、误回收 = 0；真后代仍存活时从不报告 `EXITED`；**UNPROVABLE 试验**输出 `UNKNOWN`（不得猜成目标，也不得猜成非目标并据此回收）；**PROVABLE 试验**输出带合法证明引用的正确确定答案；各证据源的「可确定比例」如实报告。 |
| **FAIL Criteria** | 把 C5 的陌生进程当作目标并信号 / 回收；把真后代遗漏并报告 `EXITED`；**UNPROVABLE 试验给出确定答案**；**PROVABLE 试验给出错误或无引用的确定答案**。 |
| **BLOCKED Criteria** | **实验层**（台架）：proc connector / cgroup 设施不可用（NOT APPLICABLE，记录权限 / 内核信息）；拓扑不可构造；谱系账本缺失。机制对不可区分用例返回 `UNKNOWN` 属预期，实验判 PASS。 |
| **机制状态 → 实验判定映射（ERRATA-04）** | UNPROVABLE 试验返回 `UNKNOWN` → PASS；PROVABLE 试验带合法引用的正确确定答案 → PASS；真后代仍存活却 `EXITED` → FAIL；UNPROVABLE 试验给出确定答案 / 对 look-alike 的无依据确定答案 → FAIL；PROVABLE 试验 `UNKNOWN` → 可用性缺失；谱系账本缺失 / 设施缺失 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性 ×5；C2 / C5 的调度敏感变体 ×50（T1）。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：C5 的 look-alike 是牺牲进程；proc connector 只读订阅，不向内核发送控制消息以外的任何内容。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：所有 `setsid` 后代由台架节点协议自报，因此 pidfd 清理不依赖被测证据源。 |
| **Evidence Files** | `a_predicate_003/results/e1c_*.json.gz`；证据源可行性探针另存。 |
| **Known Limitations** | proc connector 的事件丢失（`ENOBUFS`）与特权依赖；cgroup v1 控制器不提供 v2 式的成员 / kill 语义；不测 PID 命名空间。 |
| **Falsification（什么证据会否定当前设计）** | 存在 `/proc` 可见字段完全相同的真孤儿与陌生进程，却被某机制以「确定」分类——说明该机制在猜测；或所有证据源都无法让合法的 `setsid` 后代得到确定答案——说明跨会话支持需要放弃（改为禁止）。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E1-D — 严格归属变体的可用性（过度 UNKNOWN）与回归

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E1-D — 严格归属变体的可用性（过度 UNKNOWN）与回归 |
| **Purpose** | 量化 CA-S / CB-S 及 E1-A/B/C 中入围机制在**合法负载**上的 `UNKNOWN` 率，并检查它们在 CPU-001 已有测试矩阵上是否保留原有正确性；不因「避免了误杀」就认定足以替代原方案。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：轮询间隔档：10 ms / 100 ms / 1 s。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 合法负载族：W1 名义 D1 阶段（单个脚本，无后代）；W2 N=1…16 个后代，无 `setsid`；W3 后代在随机时刻 `setsid()`；W4 扇出 64 个短命后代，随机退出顺序；W5 双重 fork 守护进程，在首次轮询之前 / 之后退出。回归：CPU-001 的 T-01…T-11（含 T-04b-A）与 T-14，对严格变体 / 入围机制逐项复跑，并预先声明哪些格子**预期**由 PASS 变为 `UNKNOWN`（例如首次轮询晚于孤立的 T-06、T-07）。 |
| **Independent Oracle** | 台架谱系账本（见 2.3）；结果类 {R, U-exp, U-unexp, X, B}（ERRATA-01）：R 确定且正确；U-exp 负例上期望的 `UNKNOWN` / `BLOCKED`；**U-unexp** 名义 / 合法场景上的 `UNKNOWN`（可用性缺失）；**X** 不安全（误信号、误回收、假 `EXITED`、伪造状态、在负例上给确定答案）；B 台架 BLOCKED。 |
| **Expected Result** | 所有 `X` = 0；UNPROVABLE 试验全部为 U-exp；W1、W2 的 `UNKNOWN_rate(N) = U-unexp(N) / executed(N)` 的观察个数为 0（**目标 0%，ChatGPT 建议，待负责人正式批准**）；`UNKNOWN` 仅出现在预先声明（冻结分类表）的场景。 |
| **PASS Criteria** | **分别报告，不合并：**(1) **安全性**——所有类别 `X = 0`，任何非目标误信号 / 误回收都是 FAIL，**不得被低 `UNKNOWN` 率抵消**；(2) **UNPROVABLE 试验正确率**——U-exp 100%（正确返回 `UNKNOWN` 计 PASS，不是可用性 FAIL；PROVABLE 试验带合法引用的正确确定答案同样 PASS）【ERRATA-002 修订】；(3) **可用性**——N 类 `UNKNOWN_rate` 分子 = N 类 U-unexp，分母 = 计划试验数 − 台架 BLOCKED（B 从分子分母同时排除并按单元报告）；W1、W2 观察到 0 个 U-unexp，且每单元 ≥ 50 个已执行试验并报告 95% 上界；L 类只报告比率与 Clopper–Pearson 区间，不判 PASS / FAIL；(4) 回归矩阵除预先声明的 `UNKNOWN` 外与 CPU-001 判定一致。0%、5% B 上限、n ≥ 50 均为**待负责人批准的提议值**。 |
| **FAIL Criteria** | 任一 `X`；回归中出现未预先声明的判定变化；W1 / W2 出现 U-unexp（在批准的 0% 门槛下为可用性未达标——**与安全 FAIL 分开记录**）；**UNPROVABLE 试验上给出确定答案**，或 PROVABLE 试验上给出错误 / 无引用的确定答案【ERRATA-002 修订】。 |
| **BLOCKED Criteria** | **实验层**（台架）：回归所需 CPU-001 台架代码不可导入 / 哈希不符；负载不可构造；单元的台架 BLOCKED 超过计划试验数的 5%（提议值）或 A / M / 安全关键单元存在无法解决的 B → 该单元 INSUFFICIENT，实验 BLOCKED（不能靠排除试验取得 PASS）。排除只依据台架层原因，**不依据机制输出**。 |
| **机制状态 → 实验判定映射（ERRATA-04）** | UNPROVABLE 试验 `UNKNOWN` → PASS；PROVABLE 名义负载 `UNKNOWN` → 可用性未达标（与安全分开）；任一 `X` → FAIL；单元 INSUFFICIENT → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 每个负载 × 每个轮询间隔 ×50（T1）；回归格子 ×5。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：W4 扇出上限 64，总进程数 ≤ 400。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：W4 的短命进程由节点协议自报并按 pidfd 清理。 |
| **Evidence Files** | `a_predicate_003/results/e1d_*.json.gz`、`e1d_unknown_rate_table.json`、回归矩阵对比表。 |
| **Known Limitations** | 负载是合成的，不代表真实 D1；0% 是观察个数目标而非比率为 0 的证明；阈值是决策问题；不重复 CPU-001 的 1860 次。 |
| **Falsification（什么证据会否定当前设计）** | 严格机制在名义负载上 `UNKNOWN` 或在回归中系统性改变判定 → 不能作为替代方案；或安全门槛下仍出现 unsafe → 机制被否定。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |


## 5. E2 — 唯一回收者与退出状态一致性

**共同验收门槛（所有 E2 卡）：**不得把未知退出状态默认为成功；不得出现两个互相竞争的状态消费责任方；所有退出码及信号终止结果符合独立真值；不得错误回收无关子进程；不得因竞争造成不可解释的状态丢失；对不能保证正确性的情形返回明确的 `UNKNOWN`、`BLOCKED` 或对应错误状态。**CA-P 在 CPU-002 的局部通过不等于 Popen 唯一回收者方案已完成架构验收。**

### 5.1 场景矩阵（覆盖指令要求的 10 项及补充）

| 编号 | 场景 | 指令项 | 独立真值 | 关键检查 |
|---|---|---|---|---|
| S01 | 退出码 0 | 1 | 0 | 不把"未知"与"成功"混同：0 必须来自真实消费 |
| S02 | 非零退出码（1、7、255） | 1 | 声明值 | 码保持 |
| S03 | SIGTERM 终止 | 2 | `-15` | 信号编码 |
| S04 | SIGKILL 终止 | 2 | `-9` | 信号编码 |
| S05 | 带 core 标志的信号终止（SIGABRT / SIGSEGV） | 2 | 信号 + core 标志 | 是否保存原始 `status`（`waitstatus_to_exitcode` 丢失 core 标志） |
| S06 | 监督器与第二消费者（Popen / 线程）同时等待 | 3 | 真值 | 恰一个持有 |
| S07 | 子进程在登记前已退出（已是僵尸） | 4 | 真值 | 登记瞬间的状态 |
| S08 | 被重新挂靠的后代 / 非 Popen 目标 | 5 | 真值 | 第二回收者与 Popen 集合不相交 |
| S09 | 回收者在「已消费、未记录」之间异常退出 | 6 | 真值 | 不伪造、不静默丢失 |
| S10 | 状态重复读取 | 7 | 真值 | 幂等；不触发第二次消费 |
| S11 | `ECHILD` 的来源（`SIGCHLD=SIG_IGN` 继承、他人回收、注入） | 8 | 未知 | 绝不返回 0 |
| S12 | 多线程并发等待 + `Popen` 被垃圾回收 / `subprocess._active` 路径 | 9 | 真值 | 无隐蔽消费路径 |
| 版本 | Python 3.11 / 3.12 / 3.13（E2-V） | 10 | 同上 | 差异记录；未验证版本列出 |

### 5.2 实验卡


### CPU-003-E2-A — 设计 A：Popen 作为唯一回收者

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E2-A — 设计 A：Popen 作为唯一回收者 |
| **Purpose** | 验证由 `Popen.poll()/wait()` 独占消费、监督器只读 `returncode` 的设计；明确其对普通子进程、重新挂靠后代和非 Popen 目标的适用边界。CPU-002 的 CA-P 只是局部原型，**其局部通过不等于架构验收**。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：Python 3.13.16 为主；3.11.15 / 3.12.3 见 E2-V。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 场景矩阵 S01–S12（第 5.1 节）：S01 退出码 0；S02 非零退出码（1、7、255）；S03 SIGTERM 终止；S04 SIGKILL 终止；S05 带 core 标志的信号终止（SIGABRT / SIGSEGV）；S06 监督器与 Popen（或第二消费者）并发等待；S07 子进程在登记前已退出；S08 被重新挂靠的后代 / 非 Popen 目标；S09 回收者在「已消费、未记录」之间异常；S10 状态重复读取；S11 `ECHILD` 的来源（`SIGCHLD=SIG_IGN` 继承、他人回收、注入）；S12 多线程并发等待 + `Popen` 被垃圾回收 / `subprocess._active` 路径。 额外：Popen 引用的生命周期（保持引用 vs 提前释放）；监督器对非 Popen 孤儿使用的第二回收者，必须与 Popen 管理的 pid 集合**不相交**，台架注入相交 pid 以检验不相交断言。 |
| **Independent Oracle** | 台架声明的退出码 / 台架施加的信号（独立于被测设计）；内核层「单一状态副本」检查（消费后 `waitid` → `ECHILD`）；对 `os.wait*` 的包装计数得到的「每 pid 成功消费次数」（INSTRUMENTED，仅用于验证不变量，不作为判定来源）。 |
| **Expected Result** | S01–S05、S07、S10 直接成立；S08 需要第二回收者且不相交；S06、S12 无重复消费；S11 → `UNKNOWN`；`Popen.poll()` 因锁争用返回 `None` 时**不得**被读成 ALIVE 之外的任何已知状态。 |
| **PASS Criteria** | 所有适用场景：返回的退出状态等于独立真值（码 / 信号 / 必要时 core 标志）；**每个 pid 恰有一个成功消费者**；`ECHILD` / 未知状态一律 `UNKNOWN` 或 `BLOCKED`，**绝不当作成功（0）**；不回收无关子进程；无不可解释的状态丢失。 另需：不相交断言被违反时给出 `UNKNOWN`（而非 0）。 |
| **FAIL Criteria** | 任何场景返回与真值不符的状态（尤其把失败报告为成功）；两个消费者都声称持有状态或都丢失；回收了无关子进程；状态丢失却没有声明。 另：把 `poll()` 的 `None`（锁忙）当作「已确认存活」。 |
| **BLOCKED Criteria** | 所需 Python 版本 / `pidfd` / `waitid(P_PIDFD)` 不可用；台架无法构造场景；两个独立观察手段不一致。（**仅指实验判定层**；机制返回的协议状态 `BLOCKED` 若符合预期则实验判 PASS，见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | S09 / S11 返回 `UNKNOWN` 或机制 `BLOCKED(SIGCHLD_IGNORED)` → PASS；任何场景把未知状态报告为 0 → FAIL；Python 版本 / `pidfd` 不可用 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；竞态场景 S06 / S12 分档：T0 ×50、T1 ×500；**强制交错钩子**逐一覆盖操作顺序（A 先、B 先、同时）——钩子覆盖优先于重复次数作为证据；T2（×5000）仅在负责人批准后。**任何档位的零失败都不能证明竞态不存在。** |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：子进程只执行台架给定的最小代码；线程并发度 ≤ 16。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：`Popen` 对象在用例结束前显式 `wait` / 确认已回收，避免 `ResourceWarning` 与 `_active` 残留污染后续用例。 |
| **Evidence Files** | `a_predicate_003/results/e2-a_*.json.gz` 与分片；包装计数日志。 |
| **Known Limitations** | 对非 Popen 目标的覆盖不足；`returncode` 回填依赖 CPython 实现；仅测本环境三个 Python 版本。 |
| **Falsification（什么证据会否定当前设计）** | 非相交被违反时出现 0 码；或孤儿无法获得与直接子进程同等的状态语义而需要放弃统一接口。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E2-B — 设计 B：监督器作为唯一回收者

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E2-B — 设计 B：监督器作为唯一回收者 |
| **Purpose** | 验证监督器独占 `waitpid`/`waitid`、其他对象不得再消费的设计，重点是 `Popen` 的**隐蔽消费路径**（`__del__`、`subprocess._active`、`_cleanup()`）与状态同步责任。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：Python 3.13.16 为主；3.11.15 / 3.12.3 见 E2-V。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 场景矩阵 S01–S12（第 5.1 节）：S01 退出码 0；S02 非零退出码（1、7、255）；S03 SIGTERM 终止；S04 SIGKILL 终止；S05 带 core 标志的信号终止（SIGABRT / SIGSEGV）；S06 监督器与 Popen（或第二消费者）并发等待；S07 子进程在登记前已退出；S08 被重新挂靠的后代 / 非 Popen 目标；S09 回收者在「已消费、未记录」之间异常；S10 状态重复读取；S11 `ECHILD` 的来源（`SIGCHLD=SIG_IGN` 继承、他人回收、注入）；S12 多线程并发等待 + `Popen` 被垃圾回收 / `subprocess._active` 路径。 额外：使用 `Popen` 创建但不调用其 `poll/wait` 的变体；使用 `os.posix_spawn` / `fork+exec` 创建的变体；`Popen` 对象被释放（含循环引用、异常路径）后再创建新 `Popen`（触发 `_cleanup()`）；有 / 无 `waitid(WNOWAIT)` 先观察后消费。 |
| **Independent Oracle** | 台架声明的退出码 / 台架施加的信号（独立于被测设计）；内核层「单一状态副本」检查（消费后 `waitid` → `ECHILD`）；对 `os.wait*` 的包装计数得到的「每 pid 成功消费次数」（INSTRUMENTED，仅用于验证不变量，不作为判定来源）。 |
| **Expected Result** | S12 的 GC / `_active` 路径是该设计的主要风险点：若未处理，状态会被 `Popen` 在监督器之前消费；通过创建方式（不用 `Popen`）或保持引用可避免。 |
| **PASS Criteria** | 所有适用场景：返回的退出状态等于独立真值（码 / 信号 / 必要时 core 标志）；**每个 pid 恰有一个成功消费者**；`ECHILD` / 未知状态一律 `UNKNOWN` 或 `BLOCKED`，**绝不当作成功（0）**；不回收无关子进程；无不可解释的状态丢失。 另需：S12 下监督器的状态与真值一致且 `Popen` 无隐蔽消费。 |
| **FAIL Criteria** | 任何场景返回与真值不符的状态（尤其把失败报告为成功）；两个消费者都声称持有状态或都丢失；回收了无关子进程；状态丢失却没有声明。 另：任何一次 `Popen.__del__` / `_cleanup()` 先于监督器消费状态。 |
| **BLOCKED Criteria** | 所需 Python 版本 / `pidfd` / `waitid(P_PIDFD)` 不可用；台架无法构造场景；两个独立观察手段不一致。（**仅指实验判定层**；机制返回的协议状态 `BLOCKED` 若符合预期则实验判 PASS，见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | S12 下监督器取得真值且无隐蔽消费 → PASS；`Popen.__del__` / `_cleanup()` 先于监督器消费 → FAIL；`UNKNOWN` / `BLOCKED` 用于无法保证正确性处 → PASS；台架无法构造 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；竞态场景 S06 / S12 分档：T0 ×50、T1 ×500；**强制交错钩子**逐一覆盖操作顺序（A 先、B 先、同时）——钩子覆盖优先于重复次数作为证据；T2（×5000）仅在负责人批准后。**任何档位的零失败都不能证明竞态不存在。** |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：子进程只执行台架给定的最小代码；线程并发度 ≤ 16。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：`Popen` 对象在用例结束前显式 `wait` / 确认已回收，避免 `ResourceWarning` 与 `_active` 残留污染后续用例。 |
| **Evidence Files** | `a_predicate_003/results/e2-b_*.json.gz` 与分片；包装计数日志。 |
| **Known Limitations** | 与仍使用 `Popen` 的冻结 Driver / Reader 的相互作用需要源码审计，本卡只测模型；崩溃保全见 E3。 |
| **Falsification（什么证据会否定当前设计）** | S12 中隐蔽消费无法被可靠阻止——设计 B 在继续使用 `Popen` 时不成立。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E2-C — 设计 C：统一 Reaper / 状态账本

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E2-C — 设计 C：统一 Reaper / 状态账本 |
| **Purpose** | 验证一个独占回收权限的组件：读取退出状态、写入账本、向其他组件提供只读状态；比较 C1（`waitid(WNOWAIT)` 观察 → 先写账本 → 再消费）、C2（先消费再写账本）、C3（pidfd 事件驱动 + `waitid(P_PIDFD)`）。**不预设优于 A 或 B。** |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：Python 3.13.16 为主；3.11.15 / 3.12.3 见 E2-V。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 场景矩阵 S01–S12（第 5.1 节）：S01 退出码 0；S02 非零退出码（1、7、255）；S03 SIGTERM 终止；S04 SIGKILL 终止；S05 带 core 标志的信号终止（SIGABRT / SIGSEGV）；S06 监督器与 Popen（或第二消费者）并发等待；S07 子进程在登记前已退出；S08 被重新挂靠的后代 / 非 Popen 目标；S09 回收者在「已消费、未记录」之间异常；S10 状态重复读取；S11 `ECHILD` 的来源（`SIGCHLD=SIG_IGN` 继承、他人回收、注入）；S12 多线程并发等待 + `Popen` 被垃圾回收 / `subprocess._active` 路径。 额外：Reaper 作为线程 / 作为子进程；账本内存版 vs 追加文件版；Reaper 在「已消费、未写账本」之间被注入异常（S09）；把状态回填 `Popen.returncode` 的变体（依赖内部实现，版本矩阵验证）；Reaper 崩溃后另一实例接管的最小版本留给 E3。 |
| **Independent Oracle** | 台架声明的退出码 / 台架施加的信号（独立于被测设计）；内核层「单一状态副本」检查（消费后 `waitid` → `ECHILD`）；对 `os.wait*` 的包装计数得到的「每 pid 成功消费次数」（INSTRUMENTED，仅用于验证不变量，不作为判定来源）。 |
| **Expected Result** | C1 在 S09 下不丢状态（内核仍保留，新 Reaper 可读）；C2 存在窗口；C3 在 S06 / S12 下单消费；所有变体在 S11 → `UNKNOWN`。 |
| **PASS Criteria** | 所有适用场景：返回的退出状态等于独立真值（码 / 信号 / 必要时 core 标志）；**每个 pid 恰有一个成功消费者**；`ECHILD` / 未知状态一律 `UNKNOWN` 或 `BLOCKED`，**绝不当作成功（0）**；不回收无关子进程；无不可解释的状态丢失。 另需：C1 在任意注入点崩溃后状态仍可恢复或被声明丢失（不伪造）。 |
| **FAIL Criteria** | 任何场景返回与真值不符的状态（尤其把失败报告为成功）；两个消费者都声称持有状态或都丢失；回收了无关子进程；状态丢失却没有声明。 另：账本记录与内核真值不一致且无标记。 |
| **BLOCKED Criteria** | 所需 Python 版本 / `pidfd` / `waitid(P_PIDFD)` 不可用；台架无法构造场景；两个独立观察手段不一致。（**仅指实验判定层**；机制返回的协议状态 `BLOCKED` 若符合预期则实验判 PASS，见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | C1 在注入点崩溃后状态可恢复或被诚实声明丢失 → PASS；账本与内核不一致且无标记 / 伪造 → FAIL；`UNKNOWN` 用于 `ECHILD` → PASS；台架无法构造 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；竞态场景 S06 / S12 分档：T0 ×50、T1 ×500；**强制交错钩子**逐一覆盖操作顺序（A 先、B 先、同时）——钩子覆盖优先于重复次数作为证据；T2（×5000）仅在负责人批准后。**任何档位的零失败都不能证明竞态不存在。** |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：子进程只执行台架给定的最小代码；线程并发度 ≤ 16。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：`Popen` 对象在用例结束前显式 `wait` / 确认已回收，避免 `ResourceWarning` 与 `_active` 残留污染后续用例。 |
| **Evidence Files** | `a_predicate_003/results/e2-c_*.json.gz` 与分片；包装计数日志。 |
| **Known Limitations** | 账本持久化级别仅考虑进程崩溃；`Popen` 回填属于内部实现依赖；新增组件的自身故障面。 |
| **Falsification（什么证据会否定当前设计）** | Reaper 自身成为新的单点且崩溃保全不优于 A/B；或账本无法与冻结 R3 事件注册表共存（决策问题，非实验可答）。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E2-V — Python 版本行为矩阵与源码审计

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E2-V — Python 版本行为矩阵与源码审计 |
| **Purpose** | 确认 `Popen` 的 `ECHILD→0`、`__del__ / _active`、`_waitpid_lock`、线程语义在 3.11 / 3.12 / 3.13 是否一致；明确**未能验证**的版本（3.9、3.10、3.14）。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：三个解释器：`/usr/bin/python3.11`（3.11.15）、`python3.12`（3.12.3）、`python3.13`（3.13.16）。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | (1) 只读源码审计（本设计阶段已做初步阅读，见 ARCHITECTURE_OPTIONS 3.1）；(2) 在每个解释器上运行 S01–S04、S10–S12 的最小子集，记录 `returncode`、`ResourceWarning`、`_active` 变化。 |
| **Independent Oracle** | 台架声明的退出码 / 信号；内核 `ECHILD` 检查。 |
| **Expected Result** | 三个版本均在 `ECHILD` 时给出 0（源码阅读已显示一致）；`__del__` 路径在三个版本均存在；若有版本差异，如实列出。 |
| **PASS Criteria** | 每个版本每个场景的观察与预注册表一致，**或**差异被完整记录并解释；报告明确列出「未验证版本」。 |
| **FAIL Criteria** | 观察与源码阅读的结论矛盾而未被记录；把单一版本的结果外推到所有版本。 |
| **BLOCKED Criteria** | 解释器不可用或损坏（注意：本环境 3.11 / 3.12 的 site 报 `_distutils_hack` 缺失警告，用 `-S -I` 运行以排除）。（**仅指实验判定层**；机制返回的协议状态 `BLOCKED` 若符合预期则实验判 PASS，见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | 观察与预注册表一致或差异被完整记录 → PASS；差异未记录 / 外推到未验证版本 → FAIL；解释器不可用 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性 ×5 / 版本；S12 的 GC 路径 ×50。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：与 E2-A…C 同。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：每个解释器独立进程，结束即清。 |
| **Evidence Files** | `a_predicate_003/results/e2v_*.json.gz`、源码审计笔记（含文件行号与解释器版本）。 |
| **Known Limitations** | 仅三个版本；其它平台（macOS / Windows）不适用；CPython 实现细节不是公开契约，可能随小版本变化。 |
| **Falsification（什么证据会否定当前设计）** | 任一版本的 `Popen` 行为与其它版本不同，使「Popen 唯一回收者」的边界在版本间不一致 → 需要版本约束进入 S0 前置条件。 |
| **Status** | **DESIGN ONLY / NOT TESTED**（源码阅读不构成实验结果） |

### CPU-003-E2-R — 并发消费竞态压力与强制交错

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E2-R — 并发消费竞态压力与强制交错 |
| **Purpose** | 对 E2-A/B/C 的并发场景（S06、S12）加压：系统化覆盖操作顺序，并用随机调度扰动做额外检查。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：`sys.setswitchinterval` 扰动；线程数 2–16；随机睡眠抖动。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 每个设计 × {监督器线程 vs Popen 线程；N 个线程等待同一 pid；N 个线程等待不同 pid；Reaper 与第二消费者}。**强制交错：**在 `wait*` 前后设置同步钩子，枚举每个有序对（A 先 / B 先 / 并发）。 |
| **Independent Oracle** | 台架声明的退出码；每 pid 成功消费次数（包装计数）；内核单副本检查。 |
| **Expected Result** | 任一顺序下恰有一个消费者持有真实状态，其余得到 `UNKNOWN`/只读副本；设计 A/C 对其预期的顺序给出一致结果。 |
| **PASS Criteria** | 枚举的每个顺序均符合预注册表；随机档位零例外；零伪造 0。 |
| **FAIL Criteria** | 任一顺序出现双消费者或双丢失，或伪造成功状态。 |
| **BLOCKED Criteria** | 钩子无法稳定地强制某顺序（记录并改用概率档位，同时标注覆盖不足）。（**仅指实验判定层**；机制返回的协议状态 `BLOCKED` 若符合预期则实验判 PASS，见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | 每个枚举顺序符合预注册表 → PASS；任一顺序双消费者 / 双丢失 / 伪造成功 → FAIL；钩子无法强制某顺序 → 该顺序实验 BLOCKED（标注覆盖不足）；未运行 → NOT TESTED。 |
| **Repetition Count** | T0 ×50、T1 ×500；T2 ×5000 仅经负责人批准；**不得以「N 次无失败」声称无竞态**。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：线程数上限 16；总子进程数 ≤ 400。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：线程全部 `join`，超时则标 BLOCKED 并杀牺牲子进程。 |
| **Evidence Files** | `a_predicate_003/results/e2r_*.json.gz`、顺序覆盖表。 |
| **Known Limitations** | 调度扰动不能穷尽所有交错；4 个 CPU 的环境。 |
| **Falsification（什么证据会否定当前设计）** | 存在某个可构造的顺序使设计 A 或 C 伪造成功状态——设计被否定（或需要附加约束）。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |


## 6. E3 — 监督器崩溃与恢复责任

**共同验收门槛（所有 E3 卡）：**非目标误杀 / 误回收 = 0；对仍存活的已确认目标，恢复策略必须明确；不能恢复的状态**不得伪造**（只能 `DECLARED_LOST`）；僵尸不得无限期无人负责；恢复失败必须留下明确状态与诊断；安全条件不满足时停止有风险的操作并报告 `BLOCKED`；**严格区分「进程全部退出」与「退出状态全部保存」两个验收条件**。

### 6.1 故障场景矩阵

| 编号 | 场景 | 证据类型 | 备注 |
|---|---|---|---|
| F01 | 监督器正常退出（含仍有存活目标的异常用法） | REAL_KERNEL | 正常退出不应遗留目标；若遗留则是缺陷 |
| F02 | 监督器收到 SIGTERM | REAL_KERNEL | 处理器是否执行清理 |
| F03 | 监督器被 SIGKILL | REAL_KERNEL | 无任何清理 |
| F04 | 监督器在 T5 前崩溃 | REAL_KERNEL（屏障注入） | 已退出未回收的目标 |
| F05 | 已回收部分目标后崩溃 | REAL_KERNEL（屏障注入） | 状态分裂：部分已消费 |
| F06 | 外层子收割者存在 / 不存在 | REAL_KERNEL | 与其它场景交叉；无子收割者时由 pid 1 清理，时间取决于环境 |
| F07 | 监护组件无法接管（被杀 / 未启动） | REAL_KERNEL | 双故障；必须留下诊断，不得静默 |
| F08 | 已取得的状态在内存、尚未持久化 | REAL_KERNEL | 与 E2 的 C1 / C2 时序相关 |
| F09 | 目标后代已改变会话 | REAL_KERNEL | 依赖 E1 的归属机制 |
| F10 | 恢复时 pid 复用 / 身份无法验证 | SIMULATED | 必须不发信号并 BLOCKED |

目标分类（E3 判定用）：**进程状态** ∈ {GONE, ORPHAN_ALIVE（有明确负责方）, ZOMBIE_UNOWNED} × **状态** ∈ {RECOVERED_EXACT, DECLARED_LOST, FORGED（FAIL）, MISSING_UNDECLARED（FAIL）}。

### 6.2 实验卡


### CPU-003-E3-0 — 基线 R-0：冻结 R3 现状 + CPU-002 观察

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E3-0 — 基线 R-0：冻结 R3 现状 + CPU-002 观察 |
| **Purpose** | 记录**没有进程层恢复责任**的基线（R3 仅有证据层 `--postmortem`），作为 E3-A/B/C 的对照；确认哪些场景在基线下已经满足条件 (1) / (2)。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：需要外层子收割者的开 / 关两档；pid 1 的清理时间属环境特性，不可推广。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 故障场景 F01–F10（第 6.1 节）：F01 监督器正常退出；F02 SIGTERM；F03 SIGKILL；F04 T5 前崩溃；F05 已回收部分目标后崩溃；F06 外层子收割者存在 / 不存在（与其它场景交叉）；F07 监护组件本身无法接管；F08 状态在内存、尚未持久化；F09 目标后代已改变会话；F10 恢复时 pid 复用或身份无法验证（SIMULATED）。 监督器 = CPU-001 的 CA / CB 臂（原样）；无 Watchdog、无账本。 |
| **Independent Oracle** | 独立**台架观察者**进程（不属于任何被测机制）：在故障前对所有节点 `pidfd_open` 并持有，节点自报的声明退出码 / 台架施加的信号为状态真值；每个目标被分类为 (进程状态 ∈ {GONE, ORPHAN_ALIVE, ZOMBIE_UNOWNED}) × (状态 ∈ {RECOVERED_EXACT, DECLARED_LOST, FORGED, MISSING_UNDECLARED})。 |
| **Expected Result** | 预期：F03 / F04 后存活目标继续运行、无人负责（条件 1 不满足）；CB 的未回收状态在外层子收割者存在时可读，CA 已消费状态 DECLARED_LOST 或 MISSING；无子收割者时由 pid 1 清理。这些大部分已由 CPU-002 E3-02 观察，本卡补全 F01、F02、F05、F08、F09。 |
| **PASS Criteria** | **两个条件分别判定：**(1) 进程全部退出——无存活目标，无无限期无人负责的僵尸（接管后 ≤ 预注册界限 `T_zombie_max`，建议 5 s；无外层子收割者时清理时间取决于 pid 1，仅报告）；(2) 状态全部保存——每个目标 RECOVERED_EXACT 或 **DECLARED_LOST**，不得 FORGED / MISSING_UNDECLARED。另：非目标误杀 = 0、误回收 = 0；身份无法验证时**不发信号**并留下诊断；恢复失败必须留下明确状态与诊断文件。 |
| **FAIL Criteria** | 任何误杀 / 误回收；任何 FORGED 或 MISSING_UNDECLARED 状态；存活的已确认目标无人处理且未声明；僵尸无限期无人负责；恢复动作基于未验证的身份；无诊断的恢复失败。 |
| **BLOCKED Criteria** | **实验层**（台架）：台架自身无法建立前置（`pidfd` 不可用、观察者无法持有句柄、真值不可得）则本卡实验 BLOCKED。**机制**在安全条件不满足时（身份不可验证、无法确认监督器已死、缺少所需设施）停止有风险的操作并返回协议状态 `BLOCKED` 是**期望行为**，实验判 PASS（不是实验 BLOCKED）；机制基于未验证身份继续行动 → FAIL。（**仅指实验判定层**；见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | 基线观察按预注册分类记录（无 PASS / FAIL 之分的对照观察，伪造状态仍 FAIL）；台架无法建立 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；每个崩溃注入点（带标签的同步屏障）×5；随机时刻 SIGKILL 档位 T1 ×50。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：监督器 / 监护者 / 目标均为台架 fork 的牺牲进程；恢复程序只对账本 / 登记表中**指纹匹配**的 pid 行动；禁止 `pkill`、按名称匹配、`waitpid(-1)`。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：监督器与 Watchdog 同时失效（F07）时，**台架观察者**按登记 + pidfd 清理；观察者也失效则由外层运行脚本 **janitor** 按持久化登记（先 `pidfd_open` 再核对 `starttime`）清理；令牌扫描只做诊断，**绝不授权发信号**；禁止 `pkill` / 名称匹配 / `killpg`；身份无法确认则不发信号并台架 BLOCKED。**【ERRATA-002 修订】**所有牺牲进程（含监督器 / Watchdog / Reaper）经 GATED-SPAWN 创建；J 只处理 `INTENT`+完整 `REGISTERED` 的记录并重新验证身份；观察者死亡后残留未释放进程 → 诊断 + 实验 BLOCKED（ERRATA-002 §2.5 R1）。 |
| **Evidence Files** | `a_predicate_003/results/e3-0_*.json.gz`；每次运行的分类表与诊断文件。 |
| **Known Limitations** | 复用 CPU-002 台架；pid 1 实现特定。 |
| **Falsification（什么证据会否定当前设计）** | 基线在某场景下已满足条件 (1)(2) 且无需新机制 → 对应的新机制没有必要。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E3-A — 机制 R-A：外层 Watchdog / Subreaper

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E3-A — 机制 R-A：外层 Watchdog / Subreaper |
| **Purpose** | 独立监护进程在监督器之前启动、持有监督器 pidfd、成为子收割者；监督器死亡后接管：终止存活的已登记目标、回收僵尸、保存状态。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：需要外层子收割者的开 / 关两档；pid 1 的清理时间属环境特性，不可推广。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 故障场景 F01–F10（第 6.1 节）：F01 监督器正常退出；F02 SIGTERM；F03 SIGKILL；F04 T5 前崩溃；F05 已回收部分目标后崩溃；F06 外层子收割者存在 / 不存在（与其它场景交叉）；F07 监护组件本身无法接管；F08 状态在内存、尚未持久化；F09 目标后代已改变会话；F10 恢复时 pid 复用或身份无法验证（SIMULATED）。 Watchdog 获得目标登记信息的方式：(a) 监督器经管道 / socketpair 实时推送；(b) 共享追加文件；(c) Watchdog 自己通过子收割者观察孤儿（无登记）。比较三种。F07：Watchdog 先被杀 / 未启动。 |
| **Independent Oracle** | 独立**台架观察者**进程（不属于任何被测机制）：在故障前对所有节点 `pidfd_open` 并持有，节点自报的声明退出码 / 台架施加的信号为状态真值；每个目标被分类为 (进程状态 ∈ {GONE, ORPHAN_ALIVE, ZOMBIE_UNOWNED}) × (状态 ∈ {RECOVERED_EXACT, DECLARED_LOST, FORGED, MISSING_UNDECLARED})。 |
| **Expected Result** | (a)(b) 下 F03–F05、F09 可接管并按指纹行动；(c) 无登记时遇到 `setsid` 后代 / look-alike → `UNKNOWN`，不行动；F07 → 退化为 R-0，必须留下诊断；F10 → 不发信号、BLOCKED。 |
| **PASS Criteria** | **两个条件分别判定：**(1) 进程全部退出——无存活目标，无无限期无人负责的僵尸（接管后 ≤ 预注册界限 `T_zombie_max`，建议 5 s；无外层子收割者时清理时间取决于 pid 1，仅报告）；(2) 状态全部保存——每个目标 RECOVERED_EXACT 或 **DECLARED_LOST**，不得 FORGED / MISSING_UNDECLARED。另：非目标误杀 = 0、误回收 = 0；身份无法验证时**不发信号**并留下诊断；恢复失败必须留下明确状态与诊断文件。 |
| **FAIL Criteria** | 任何误杀 / 误回收；任何 FORGED 或 MISSING_UNDECLARED 状态；存活的已确认目标无人处理且未声明；僵尸无限期无人负责；恢复动作基于未验证的身份；无诊断的恢复失败。 |
| **BLOCKED Criteria** | **实验层**（台架）：台架自身无法建立前置（`pidfd` 不可用、观察者无法持有句柄、真值不可得）则本卡实验 BLOCKED。**机制**在安全条件不满足时（身份不可验证、无法确认监督器已死、缺少所需设施）停止有风险的操作并返回协议状态 `BLOCKED` 是**期望行为**，实验判 PASS（不是实验 BLOCKED）；机制基于未验证身份继续行动 → FAIL。（**仅指实验判定层**；见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | 身份不可验证时机制 `BLOCKED` 且不发信号 → PASS；基于未验证身份行动 → FAIL；`DECLARED_LOST` 按"设计上可恢复"预注册表判定（不可恢复场景 PASS，可恢复场景 FAIL）；台架 / 观察者无法建立 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；每个崩溃注入点（带标签的同步屏障）×5；随机时刻 SIGKILL 档位 T1 ×50。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：监督器 / 监护者 / 目标均为台架 fork 的牺牲进程；恢复程序只对账本 / 登记表中**指纹匹配**的 pid 行动；禁止 `pkill`、按名称匹配、`waitpid(-1)`。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：监督器与 Watchdog 同时失效（F07）时，**台架观察者**按登记 + pidfd 清理；观察者也失效则由外层运行脚本 **janitor** 按持久化登记（先 `pidfd_open` 再核对 `starttime`）清理；令牌扫描只做诊断，**绝不授权发信号**；禁止 `pkill` / 名称匹配 / `killpg`；身份无法确认则不发信号并台架 BLOCKED。**【ERRATA-002 修订】**所有牺牲进程（含监督器 / Watchdog / Reaper）经 GATED-SPAWN 创建；J 只处理 `INTENT`+完整 `REGISTERED` 的记录并重新验证身份；观察者死亡后残留未释放进程 → 诊断 + 实验 BLOCKED（ERRATA-002 §2.5 R1）。 |
| **Evidence Files** | `a_predicate_003/results/e3-a_*.json.gz`；每次运行的分类表与诊断文件。 |
| **Known Limitations** | Watchdog 自身是单点；登记推送丢失 / 延迟的窗口；需要子收割者与 pidfd；非 Linux 不适用。 |
| **Falsification（什么证据会否定当前设计）** | Watchdog 在 F07（双故障）时无诊断地静默失败；或在登记缺失时凭猜测杀进程。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E3-B — 机制 R-B：可恢复状态账本

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E3-B — 机制 R-B：可恢复状态账本 |
| **Purpose** | 关键身份、已取得的退出状态与回收进度写入可恢复的账本；监督器死后由独立恢复程序读账本、核对指纹、再行动。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：需要外层子收割者的开 / 关两档；pid 1 的清理时间属环境特性，不可推广。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 故障场景 F01–F10（第 6.1 节）：F01 监督器正常退出；F02 SIGTERM；F03 SIGKILL；F04 T5 前崩溃；F05 已回收部分目标后崩溃；F06 外层子收割者存在 / 不存在（与其它场景交叉）；F07 监护组件本身无法接管；F08 状态在内存、尚未持久化；F09 目标后代已改变会话；F10 恢复时 pid 复用或身份无法验证（SIMULATED）。 账本写入时序比较：先消费再写 vs 先 `waitid(WNOWAIT)` 观察→写账本→再消费（与 E2-C 的 C1/C2 对应）；追加写、每条记录自带校验；撕裂的末行；崩溃点覆盖「已消费未写」「已写未消费」。 |
| **Independent Oracle** | 独立**台架观察者**进程（不属于任何被测机制）：在故障前对所有节点 `pidfd_open` 并持有，节点自报的声明退出码 / 台架施加的信号为状态真值；每个目标被分类为 (进程状态 ∈ {GONE, ORPHAN_ALIVE, ZOMBIE_UNOWNED}) × (状态 ∈ {RECOVERED_EXACT, DECLARED_LOST, FORGED, MISSING_UNDECLARED})。 |
| **Expected Result** | 先写后消费的时序下，F04、F05、F08 不丢状态；先消费后写的时序存在 DECLARED_LOST 窗口且**必须被声明**；账本缺失 / 撕裂 → 恢复程序 `BLOCKED` 并诊断。 |
| **PASS Criteria** | **两个条件分别判定：**(1) 进程全部退出——无存活目标，无无限期无人负责的僵尸（接管后 ≤ 预注册界限 `T_zombie_max`，建议 5 s；无外层子收割者时清理时间取决于 pid 1，仅报告）；(2) 状态全部保存——每个目标 RECOVERED_EXACT 或 **DECLARED_LOST**，不得 FORGED / MISSING_UNDECLARED。另：非目标误杀 = 0、误回收 = 0；身份无法验证时**不发信号**并留下诊断；恢复失败必须留下明确状态与诊断文件。 |
| **FAIL Criteria** | 任何误杀 / 误回收；任何 FORGED 或 MISSING_UNDECLARED 状态；存活的已确认目标无人处理且未声明；僵尸无限期无人负责；恢复动作基于未验证的身份；无诊断的恢复失败。 |
| **BLOCKED Criteria** | **实验层**（台架）：台架自身无法建立前置（`pidfd` 不可用、观察者无法持有句柄、真值不可得）则本卡实验 BLOCKED。**机制**在安全条件不满足时（身份不可验证、无法确认监督器已死、缺少所需设施）停止有风险的操作并返回协议状态 `BLOCKED` 是**期望行为**，实验判 PASS（不是实验 BLOCKED）；机制基于未验证身份继续行动 → FAIL。（**仅指实验判定层**；见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | 账本缺失 / 撕裂时恢复程序 `BLOCKED` + 诊断 → PASS；信任陈旧账本而误杀 → FAIL；伪造或未声明的缺失 → FAIL；台架无法建立 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；每个崩溃注入点（带标签的同步屏障）×5；随机时刻 SIGKILL 档位 T1 ×50。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：监督器 / 监护者 / 目标均为台架 fork 的牺牲进程；恢复程序只对账本 / 登记表中**指纹匹配**的 pid 行动；禁止 `pkill`、按名称匹配、`waitpid(-1)`。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：监督器与 Watchdog 同时失效（F07）时，**台架观察者**按登记 + pidfd 清理；观察者也失效则由外层运行脚本 **janitor** 按持久化登记（先 `pidfd_open` 再核对 `starttime`）清理；令牌扫描只做诊断，**绝不授权发信号**；禁止 `pkill` / 名称匹配 / `killpg`；身份无法确认则不发信号并台架 BLOCKED。**【ERRATA-002 修订】**所有牺牲进程（含监督器 / Watchdog / Reaper）经 GATED-SPAWN 创建；J 只处理 `INTENT`+完整 `REGISTERED` 的记录并重新验证身份；观察者死亡后残留未释放进程 → 诊断 + 实验 BLOCKED（ERRATA-002 §2.5 R1）。 |
| **Evidence Files** | `a_predicate_003/results/e3-b_*.json.gz`；每次运行的分类表与诊断文件。 |
| **Known Limitations** | 仅覆盖进程崩溃，不含掉电；账本与冻结 R3 事件注册表 / `postmortem.json` 的关系需 R3 变更评审；账本不能让存活目标自动被终止（需要执行者）。 |
| **Falsification（什么证据会否定当前设计）** | 账本在某崩溃点下与内核真值矛盾而未被标记；或恢复程序信任了陈旧账本而误杀。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |

### CPU-003-E3-C — 机制 R-C：Watchdog + 账本组合

| 字段 | 内容 |
|---|---|
| **Experiment ID** | CPU-003-E3-C — 机制 R-C：Watchdog + 账本组合 |
| **Purpose** | Watchdog 负责进程生命周期，账本保存关键结果；C1 式先写账本再消费。检验组合是否在 F01–F10 上同时满足条件 (1) 与 (2)，以及增加的复杂度是否带来新的故障面（F07 双故障）。 |
| **Environment** | COMMON-ENV（第 2.1 节）；本卡补充：需要外层子收割者的开 / 关两档；pid 1 的清理时间属环境特性，不可推广。 |
| **Git SHA** | COMMON-GIT（第 2.2 节）：执行前登记「代码提交 SHA + 干净工作树」，每个分片记录 `git_commit` / `git_status_short`。**当前：未执行，无运行 SHA。**设计基线 = 本设计分支提交（见检查点）。 |
| **Inputs / Topology** | 故障场景 F01–F10（第 6.1 节）：F01 监督器正常退出；F02 SIGTERM；F03 SIGKILL；F04 T5 前崩溃；F05 已回收部分目标后崩溃；F06 外层子收割者存在 / 不存在（与其它场景交叉）；F07 监护组件本身无法接管；F08 状态在内存、尚未持久化；F09 目标后代已改变会话；F10 恢复时 pid 复用或身份无法验证（SIMULATED）。 R-A 与 R-B 的全部输入，加上「Watchdog 与账本不一致」「账本领先 / 落后于内核」的注入。 |
| **Independent Oracle** | 独立**台架观察者**进程（不属于任何被测机制）：在故障前对所有节点 `pidfd_open` 并持有，节点自报的声明退出码 / 台架施加的信号为状态真值；每个目标被分类为 (进程状态 ∈ {GONE, ORPHAN_ALIVE, ZOMBIE_UNOWNED}) × (状态 ∈ {RECOVERED_EXACT, DECLARED_LOST, FORGED, MISSING_UNDECLARED})。 |
| **Expected Result** | 条件 (1)(2) 在 F01–F06、F08、F09 成立；F07、F10 → 明确 BLOCKED 与诊断。 |
| **PASS Criteria** | **两个条件分别判定：**(1) 进程全部退出——无存活目标，无无限期无人负责的僵尸（接管后 ≤ 预注册界限 `T_zombie_max`，建议 5 s；无外层子收割者时清理时间取决于 pid 1，仅报告）；(2) 状态全部保存——每个目标 RECOVERED_EXACT 或 **DECLARED_LOST**，不得 FORGED / MISSING_UNDECLARED。另：非目标误杀 = 0、误回收 = 0；身份无法验证时**不发信号**并留下诊断；恢复失败必须留下明确状态与诊断文件。 |
| **FAIL Criteria** | 任何误杀 / 误回收；任何 FORGED 或 MISSING_UNDECLARED 状态；存活的已确认目标无人处理且未声明；僵尸无限期无人负责；恢复动作基于未验证的身份；无诊断的恢复失败。 |
| **BLOCKED Criteria** | **实验层**（台架）：台架自身无法建立前置（`pidfd` 不可用、观察者无法持有句柄、真值不可得）则本卡实验 BLOCKED。**机制**在安全条件不满足时（身份不可验证、无法确认监督器已死、缺少所需设施）停止有风险的操作并返回协议状态 `BLOCKED` 是**期望行为**，实验判 PASS（不是实验 BLOCKED）；机制基于未验证身份继续行动 → FAIL。（**仅指实验判定层**；见 2.4。） |
| **机制状态 → 实验判定映射（ERRATA-04）** | F07 双故障时留下诊断并 `BLOCKED` → PASS；静默失败 → FAIL；组合比单独机制更差 / 新误杀路径 → FAIL；台架无法建立 → 实验 BLOCKED；未运行 → NOT TESTED。 |
| **Repetition Count** | 确定性场景 ×5；每个崩溃注入点（带标签的同步屏障）×5；随机时刻 SIGKILL 档位 T1 ×50。 |
| **Safety Boundaries** | COMMON-SAFETY（第 2.5 节）；本卡补充：监督器 / 监护者 / 目标均为台架 fork 的牺牲进程；恢复程序只对账本 / 登记表中**指纹匹配**的 pid 行动；禁止 `pkill`、按名称匹配、`waitpid(-1)`。 |
| **Cleanup Procedure** | COMMON-CLEANUP（第 2.6 节）；本卡补充：监督器与 Watchdog 同时失效（F07）时，**台架观察者**按登记 + pidfd 清理；观察者也失效则由外层运行脚本 **janitor** 按持久化登记（先 `pidfd_open` 再核对 `starttime`）清理；令牌扫描只做诊断，**绝不授权发信号**；禁止 `pkill` / 名称匹配 / `killpg`；身份无法确认则不发信号并台架 BLOCKED。**【ERRATA-002 修订】**所有牺牲进程（含监督器 / Watchdog / Reaper）经 GATED-SPAWN 创建；J 只处理 `INTENT`+完整 `REGISTERED` 的记录并重新验证身份；观察者死亡后残留未释放进程 → 诊断 + 实验 BLOCKED（ERRATA-002 §2.5 R1）。 |
| **Evidence Files** | `a_predicate_003/results/e3-c_*.json.gz`；每次运行的分类表与诊断文件。 |
| **Known Limitations** | 复杂度与新增组件的自身故障面；是否值得（相对 R-0 + 清理工具）需负责人判断。 |
| **Falsification（什么证据会否定当前设计）** | 组合在任一场景下比 R-A 或 R-B 单独更差，或引入新的误杀路径。 |
| **Status** | **DESIGN ONLY / NOT TESTED** |


## 7. 明确的 NOT TESTED 清单（需要运行实验才能回答）

- 所有 E1 / E2 / E3 卡的结果；S0 谓词、登记表、专用监督器、Reaper / 账本、Watchdog 的任何行为。
- 非 root 环境；其它内核；Python 3.9 / 3.10 / 3.14；cgroup v2；proc connector 的可用性与事件完整性。
- 真实 pid 回绕复用（不计划：需要特权且有影响他人进程的风险）；整组信号的安全条件（提案 T-15）；归属专项 T-12 / T-13。
- CA-S / CB-S 在 CPU-001 完整矩阵上的回归（由 E1-D 设计）；CA-P 的架构验收（由 E2-A 设计）。
- `Popen.returncode` 回填、`subprocess._active` 清理等依赖 CPython 内部实现的做法。
- 冻结 Driver / Reader / Verifier 内部是否 `fork` / 使用 `Popen`（源码审计未做，且冻结代码不得修改）。

## 8. 各设计的"否定条件"汇总

见各卡 Falsification 行。总体上，以下任一出现即应放弃对应设计：O-2 / O-3 在绕过入口时静默接受；严格机制在名义负载上 `UNKNOWN`；任何顺序下伪造成功状态；Reaper 引入新单点而崩溃保全不优于简单方案；Watchdog 在双故障时无诊断；恢复程序基于未验证身份行动。

## 9. 本计划不做什么

不执行任何 CPU-003 实验；不启动进程故障注入；不修改 CPU-001 / CPU-002 的原始记录；不修改冻结 R3、真实 D1、Parcae；不选择最终 CA / CB / CA-S / CB-S / CA-P 方案；不启动 GPU；不将 G3～G6 标为 PASS；不虚构 Grok 或 ChatGPT 的审核文件。

**状态：CPU-003 DESIGN ERRATA-002 COMPLETE / PENDING CHATGPT REVIEW / EXPERIMENTS NOT TESTED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER。**

下一条唯一研发指令：提交 ERRATA-002 给 ChatGPT 审核，等待项目负责人**单独**决定是否授权 Stage 1。不要自动开始 Stage 1、Stage 2 或 Stage 3。

## 10. 勘误记录（就地修改清单）

本节记录 `F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md` 对本文件的每处改动（旧文可由提交 `6c8bab5` 取回）：

| 位置 | 改动 | 勘误项 |
|---|---|---|
| 文件头 | 增加勘误说明与历史提交指引 | 全部 |
| 2.3 COMMON-ORACLE | 重写：`pidfd` 只证明身份稳定性 / 生命周期，不证明血缘；归属真值 = 台架创建时的谱系账本；被测监督器盲；节点规格不再放 `argv`；区分「真相已知而机制无法证明」与「台架无法建立真值」；`/proc` 字段相同 ≠ 身份相同 | ERRATA-02 |
| 2.4 COMMON-STATES | 重写：机制协议状态与实验判定两层；删除"机制按设计拒绝继续即 BLOCKED"的混用表述 | ERRATA-04 |
| 2.5 COMMON-SAFETY | 清理动作同样受约束并计入误信号统计；"BLOCKED"改为"（台架层）BLOCKED" | ERRATA-03 / 04 |
| 2.6 COMMON-CLEANUP | 整节替换：创建时登记、先开 pidfd 再核对、令牌只做诊断、禁止 `pkill` / 名称匹配 / 清理性 `killpg`、身份不明则停止并台架 BLOCKED、观察者 + janitor 的最终清理责任、失败留痕 | ERRATA-03 |
| 第 3 节第 2 项 | `UNKNOWN` 率 0% 标明为 ChatGPT 建议、需负责人正式批准；加入度量定义、5% 与 n ≥ 50 提议值 | ERRATA-01 |
| E1-A | Independent Oracle、Expected Result、BLOCKED Criteria、Cleanup 重写（不再 `killpg`；S0 拒绝=机制 BLOCKED=实验 PASS） | 02 / 03 / 04 |
| E1-B、E1-C | Independent Oracle 与 BLOCKED Criteria 重写（谱系账本；look-alike=真相已知而机制无法证明） | 02 / 04 |
| E1-D | Independent Oracle、Expected、PASS、FAIL、BLOCKED、Known Limitations 重写：类别 N/L/A/M、结果类 R/U-exp/U-unexp/X/B、分子分母、排除规则、安全与可用性分开 | ERRATA-01 |
| 全部 13 张卡 | BLOCKED Criteria 行标明"仅指实验判定层"；新增"机制状态 → 实验判定映射"行 | ERRATA-04 |
| E3-0 / A / B / C | Cleanup 行改为观察者 + janitor、令牌只做诊断；BLOCKED Criteria 行改写（机制 BLOCKED 符合预期=实验 PASS） | 03 / 04 |
| 末尾 | 状态与下一条指令改为勘误版 | — |

### 10.1 ERRATA-002 追加的改动

| 位置 | 改动 |
|---|---|
| 文件头 | 增加勘误-002 说明 |
| 2.3 | 歧义改为"按候选机制预先分类"（ECD、PROVABLE / UNPROVABLE / BENCH_UNVERIFIABLE、冻结哈希、观察后不得改类） |
| 2.6 第 1、5、6 条 | 创建 / 登记改为 GATED-SPAWN 协议；Janitor 只处理 `INTENT`+完整 `REGISTERED` 并重新验证身份；增加观察者死亡后残留未释放进程的 BLOCKED 条件；明确只要求普通进程崩溃恢复 |
| 第 3 节 Stage 1 行 | 前置条件增加"冻结 `e1_provability_table_v1.json`" |
| E1-B、E1-C | Expected / PASS / FAIL / 映射行按 PROVABLE / UNPROVABLE 重写 |
| E1-D | Expected 重写；PASS / FAIL 追加说明；映射行重写 |
| E3-0 / A / B / C | Cleanup 行追加 GATED-SPAWN / Janitor 重新验证 / R1 BLOCKED |
