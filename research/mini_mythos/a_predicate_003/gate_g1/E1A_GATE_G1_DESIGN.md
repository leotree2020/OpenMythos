# E1A_GATE_G1_DESIGN — 负向门控（G1）最小测试设计

任务 F3B-D1-A-CPU-003-E1A-G1-NEGATIVE-GATE-DESIGN-001。基准提交 `c3cf742dea57cad28c997a23df76b2f038e86d4d`（分支 `d1-r3-a-cpu-003-e1a-g1-negative-gate-design-20261027`）。
**状态：设计稿，供 ChatGPT/Grok 审核。未写任何代码、未创建授权文件、未运行任何进程级测试。** G1 EXECUTION NOT AUTHORIZED。

> 命名说明：这里的 G1 是 E1-A **台架门控测试阶段**（G0 正向、G1 负向、G2 身份与后代、G3 恢复与故障注入，见 `E1A_GATE_TEST_INVENTORY.md`），与已归档的 R3 “存活判定 G1/G2 规则 FAIL”记录无关；后者未被触碰。G0 REAL-001 PASS（`g0_20261027_144311_479c54`）只证明 G0 流程可用，**不推出任何 G1 结论**。

## 1. 依据与不变量

读取的材料：`SESSION_START_PROTOCOL.md`、G0 REAL-001 checkpoint、`E1A_GATE_TEST_INVENTORY.md`、`bench/gate.py`、`bench/observer.py`、`bench/node.py`、`bench/registry.py`、`bench/validity.py`、`tests/test_e1a_gate.py`、`gate_g0/g0_run.py`、`g0_auth.py`、`g0_criteria_v5.json`。

被测不变量（`gate.py` 头部 I1/I2/I3，ERRATA-002 §2）：

* I1 子进程在从门管道读到 `b"R"` 之前不执行任何实验动作；
* I2 除 `b"R"` 之外的任何结果（中止字节 `A`、EOF、门沉默 `T_GATE_MAX`、其他字节）都会结束进程（`gate_wait` → `os._exit(111 / 112)`）；
* I3 门写端不在子进程中（G0 的 C06 已覆盖，G1 沿用）。

退出码：`EXIT_GATE_ABORT=111`、`EXIT_GATE_TIMEOUT=112`、`EXIT_CHILD_EXC=113`（`common.py`）。`gate.fork_gated` 的子进程只有两种方式离开 `gate_wait` 之前：`111/112` 或异常 `113`；`node_main` 只会以 `0` 或 `113` 退出。因此**退出码 111/112 本身证明进程死在门里（没有越过门）**，不依赖子进程自述。

## 2. 四个最小测试

每个测试：一个观察者、**恰好一个**受控子进程（`Observer.spawn_direct(..., hold_release=True)`，SPEC=`{"role":"sleeper","mode":"setsid","children":[]}`，`setsid` 使任何越权动作在 `/proc` 的 sid 上可见）、一次 fork、**零信号**、无后代。四个测试**顺序**执行，固定顺序 T1→T2→T3→T4，任何时刻最多一个子进程。

| | T1 ABORT | T2 EOF | T3 INVALID_BYTE | T4 TIMEOUT |
|---|---|---|---|---|
| 对应旧测试 | BV-1 / 清单 #2 | 清单 #5 | 清单 §3 覆盖缺口 | BV-3 / 清单 #3 |
| `t_gate_max` | 5.0 s（兜底） | 5.0 s（兜底） | 5.0 s（兜底） | **2.0 s**（被测） |
| 刺激（REGISTERED 记录已落盘、保持 0.3 s、S1 快照之后） | 向 SPEC 控制套接字预排队一条 `SPEC`（泄漏门会据此行动）；调用 `Observer.abort_held(rec)`：写 `ABORTED` 记录 → 向门写 `b"A"` → 关门写端 | 关闭门写端 `os.close(rec.gate_w)`，**不写任何字节**，不写 ABORTED/RELEASED | 向门写端写**恰好一个字节 `b"r"`**（小写 r），随后关闭门写端；不写 R | **无刺激**：门写端保持打开且沉默，直到观察到子进程退出；之后才关闭 |
| 观察者向门写的字节序列（守卫记录） | `[A]` | `[]`，且 `close` 发生在 REGISTERED 之后 | `[r]` | `[]`，门写端在子进程退出的观察时刻仍打开 |
| 期望退出码 | 111 | 111 | 111 | 112 |
| 期望登记序列 | INTENT, FORKED, REGISTERED, ABORTED, DEAD | INTENT, FORKED, REGISTERED, DEAD | INTENT, FORKED, REGISTERED, DEAD | INTENT, FORKED, REGISTERED, DEAD |
| 绝对禁止出现 | RELEASED、门上的 `R`、任何 FIRST_ACTION/READY/TICKET 消息 | 同左，且不得有 ABORTED | 同左，且不得有 ABORTED | 同左，且门上不得有任何字节 |
| 时间窗 | 退出 ≤ 刺激后 5 s | 同左 | 同左 | 子进程退出时刻距 fork **≥ 1.8 s 且 ≤ 2.0+3.0 s**（过早的 112 不可能来自计时器） |

说明：T1–T3 退出码都是 111，退出码本身不能区分三种刺激；区分靠观察者侧的**刺激精确性证据**（守卫记录的门写字节序列、`close` 次序、登记序列）。`b"r"` 取小写 r：一字节之差，能暴露大小写不敏感或 `in b"Rr"` 之类的宽松比较；其他字节值不在最小集内（审核问题 Q2）。

### 2.1 每个测试的操作顺序（统一骨架，沿用 G0 的 S0–S5 与 P0–P7）

1. 预检（只读，见 §6）；S0：fork 前快照（观察者 fd 基线、子进程数 0、token 残留 0）。
2. `spawn_direct(..., hold_release=True)`：INTENT → fork → FORKED → 身份核验 → REGISTERED。**不释放。**
3. 保持 0.3 s，期间 `serve()` 消息泵；S1（held）：子进程 `/proc` 身份（pid/starttime/ppid/sid/pgrp/state）、fd 列表、`messages_received==0`、`first_action_mono is None`。
4. 刺激（按上表；T4 无刺激）。刺激前再取一次 `/proc` 指纹作为 S1b，与 REGISTERED 记录对比。
5. 等待 `PidfdHandle.exited()`（pidfd 可读 = 已退出），**回收前**取 S3：`/proc/<pid>` 状态须为 `Z`（已退出未回收；G0 C08 机制）。
6. 非阻塞 `waitpid(具体 pid, WNOHANG)` 轮询直至返回该 pid（G0 C09 机制），记录 `exit_status`；`/proc/<pid>` 消失（S4）。
7. 本测试节点的清理核验：`Observer.finish_cleanup(nodes=[rec])` 仅在回收之后调用，此时 pidfd 已可读 → `already_exited`，**无信号**；整个运行结束时再调用一次全局 `final_cleanup` 并写 `RUN_END`（G0 同一做法）。
8. 判定本测试的 17 项（§4）。**非 PASS → 立即停止，后续测试标记 `NOT_RUN`（不计为 PASS）。**

## 3. 逐测试独立证据与 PASS / FAIL / BLOCKED 判据

**身份（PID/starttime）**：REGISTERED 记录的 `(pid, starttime, ppid==观察者 pid)` ＝ `PidfdHandle` 打开时确认值 ＝ S1/S1b 的 `/proc` 读数 ＝ `waitpid` 返回的 pid ＝ `guard.fork_pids` 中的唯一值。任一不一致 → 不得 PASS。

**子进程未提前动作的独立证据**（不依赖子进程自述，按强度）：
(a) 退出码 111/112（见 §1：不是 `node_main` 能产生的码）；(b) S1/S1b 时 `/proc` 中 sid/pgrp 仍等于观察者继承值（`setsid` 若已执行会变）；(c) 观察者从未收到 FIRST_ACTION/READY/TICKET/任何消息（`messages_received==0`）；(d) 守卫记录门上从未写入 `R`（任何测试里 `R` 写入即违规）；(e) 无登记之外的后代：观察者 `children` 扫描 = 唯一子进程；(f) 登记序列中没有 RELEASED；(g) S1 fd 列表仅含 `{0,1,2,gate_r,ctrl}`，且没有门写端 inode（沿用 G0 C06）。

**判据**（每测试，针对 17 项的聚合；与 G0 V5 同一政策 FAIL > BLOCKED > PASS）：

* **PASS**：17 项全部满足；退出码 = 期望值；刺激精确性证据与表一致；回收证据完整；无残留；无信号。
* **FAIL**（证据完整且可评估的违规）：子进程越过了门（收到 FIRST_ACTION/READY/TICKET，或 sid/pgrp 变化，或退出码 0）；门上出现 `R` 或 RELEASED 记录；退出码是 111/112 之外的**良构整数且与期望不符**（例如 T4 得到 111，T1 得到 112）；T4 的退出早于计时窗下限；出现信号/多余 fork/后代。**判据证据本身格式损坏 ⇒ 不可评估，不是 FAIL**（沿用 G0 修复 D-2）。
* **BLOCKED**（无法确认）：退出码 113（子进程死于门之外的异常，结论不确定）；登记/身份核验失败；证据缺失或读回不一致；`/proc` 不可读；`waitpid` 未返回具体 pid；预算/期限命中；子进程到期仍存活（**不发信号**，写 `MANUAL_DISPOSITION_REQUIRED.json`，见 §5）；残留；意外异常（含任何 `SystemExit`，一律退出码 3）。

**整个 G1 运行的裁决**：任一测试 FAIL → FAIL（退出码 1）；否则任一测试 BLOCKED 或 NOT_RUN → BLOCKED（退出码 3）；四个测试全部 PASS → PASS（退出码 0）。退出码 2 仅用于拒绝执行（授权/冻结文件）与 argparse 用法错误。

## 4. 判据集合（复用 G0 V5 的 17 项框架）

G1 沿用 `G0-C01…C17` 的结构与证据管线 P0–P7，按测试各评一次（4×17 矩阵）；差异仅在以下项，其余逐项照 G0 V5 的定义：

| 项 | G1 中的含义 |
|---|---|
| C02 | 授权与绑定（§5，G1 专用 schema，绑定 G0 REAL-001 结案证据） |
| C03 | 登记序列与完整性：期望序列按测试固定（§2 表），含磁盘忠实度/F-20 机制 |
| C04 | 身份在刺激**之前**已登记（取代“释放前”） |
| C05 | 刺激之前及之后均无动作（§3 证据 a–g） |
| C07 | **刺激精确性**：门上从未写 `R`；字节序列/关闭次序与表一致；T4 门写端在退出观察时仍打开；刺激仅在 REGISTERED 持久化之后 |
| C10 | 退出码 = 该测试的期望值（111/111/111/112），不是 G0 的“=0” |
| C11 | 过程预算：每测试 1 次 fork、总计 4 次；任一时刻 1 个子进程；0 后代；0 票据 |
| C15 | 时间界：每测试 ≤ 7 s，整个运行 ≤ 30 s；T4 时间窗见 §2 |
| C16 | 证据 schema `e1a-gate-g1-evidence-1`（G0 schema 的超集：每测试一节） |
| 其余 | C01、C06、C08、C09、C12（零信号）、C13、C14、C17 与 G0 相同 |

判据在**实现阶段**以冻结文件 `g1_criteria_v1.json` + `E1A_GATE_G1_PREREG.md` 固化（本设计阶段不写）；它们的 SHA-256 进入授权绑定。

## 5. 安全执行入口、授权、失败关闭与结案

**入口**：新增 `gate_g1/g1_run.py --check | --execute`、`g1_auth.py`、`g1_judge.py`（实现阶段；**不复用** `tests/test_e1a_gate.py` 及其 SIGKILL `tearDown`，不调用 `finish_trial_cleanup()`）。G1 **只读导入** G0 已验证的机制（`Guard` 的子类或同构物、`snapshot/ancestors/token_scan/fd_report`、`Budget`、`write_exclusive/read_back/save_and_verify/fsync_dir`、`prepare_dirs`、闭合发布 K0–K7、`g0_judge` 的类型校验与规则辅助）；**不修改任何 `g0_*` 文件**（修改会改变 `g0_code_sha256`，使 G0 REAL-001 的授权绑定与证据失去可复核性）。具体哪些辅助函数是通用的、哪些带 G0 常量需新增薄封装，是实现阶段的第一步核对项（Q4）。`g1_run.py` 的 `main()` 沿用最终收口结构：argparse 在安全网之外（0/2），其后任何 `SystemExit`/异常 → 退出码 3 + `G1-STARTUP-ERROR`；运行器在 import 之后、其他一切之前安装哨兵（CPU 测试阶段），环境信息只用 `os.uname()`，并独立读取 `.git` 核验 HEAD/冻结文件/Bench 哈希。

**守卫（G1 版本）**：陷阱 `kill/killpg/pidfd_send_signal/exec*/spawn*/system/popen/subprocess/wait/wait3/wait4/waitid/...`；`os.fork` 每测试至多一次、全程至多 4 次，且在上一个子进程**已回收**之前不得再 fork；`waitpid` 只允许当前测试子进程的具体 pid；对门写端的 `os.write` 逐次记录（字节值、前后时刻、结果；沿用 F-18 的“先建条目后调用”），**任何 `R` 写入立即记为违规**；`os.close` 门写端的时刻与次序也进记录。Python 层守卫不是内核层证明（与 G0 安全评审同一声明）。

**授权（单次）**：`AUTHORIZATION_E1A_GATE_G1.json`，schema `e1a-gate-auth-g1-1`、stage `G1`、封闭 schema（拒绝 G0 的 `e1a-gate-auth-1` 与 E1-A 的 `e1a-auth-2`，反之亦然；G0 授权不得继承）。grants 固定：`runs 1, tests ["ABORT","EOF","INVALID_BYTE","TIMEOUT"], forks 4, max_concurrent_children 1, signals 0, fault_injection false, max_seconds 30`。`not_granted` 必含 `G2, G3, BV, E1A-CELLS, E1-B, E1-C, E1-D, E2, E3`。绑定：`git_head`、E1-A 原预注册哈希、G0 V5 criteria/prereg 哈希、Bench 哈希、`g0_code_sha256`、`g1_criteria_sha256`、`g1_prereg_sha256`、`g1_code_sha256`，以及 **G0 REAL-001 结案证据** `g0_closed.json` 的 SHA-256（只读复核：recorded_verdict PASS、证据/摘要哈希相符）。授权 ID 唯一、有限期、单次：运行在**第一次 fork 之前**写入消耗标记 `evidence/_g1_consumed/<id>.json`，已消耗则拒绝；授权文件与 `authorization_used.json` 不得提交 Git（本地 `.git/info/exclude`）；只能经负责人**单独书面授权**创建。

**预检（任何不满足 → BLOCKED，不启动子进程）**：Git HEAD 与工作树干净且等于授权绑定；Python 3.13.16、Linux、CPU；V1–V5 冻结文件与 Bench 哈希；`pidfd_open`、`socket.send_fds`、`os.link`；`evidence/` 中所有 `g0_*` 运行已有有效结案（沿用 G0 V5 CL-01…23）且 G0 REAL-001 结案已复核；所有 `g1_*` 运行已结案；无 `MANUAL_DISPOSITION_REQUIRED.json`、无活跃残留进程、无历史授权消耗冲突；`g1_run.py --check` 输出已记录。

**失败关闭**（无信号、禁止按名称清理）：

* 任何时候不发送信号：不使用 `timeout`/`kill`/`pkill`/`killall`/按进程名或命令行的清理；`token_scan` 仅为诊断。清理只通过**登记的身份**：子进程以门机制自行结束——中止字节、EOF、`t_gate_max` 计时器；观察者崩溃时门写端随进程关闭 ⇒ EOF ⇒ 子进程 111 自行退出（I2）。因此任何子进程最长存活 ≤ `t_gate_max`（T1–T3 兜底 5 s，T4 2 s）+ 调度余量，无需信号。
* 首个非 PASS 即停：后续测试 `NOT_RUN`；子进程仍存活则写 `MANUAL_DISPOSITION_REQUIRED.json`（含 pid、starttime、节点 ID、核验依据 REGISTERED 记录 + pidfd、“人工决定”），该文件使后续 G1 运行预检 BLOCKED。
* 禁止自动重试、禁止失败后“修复并重跑”：任何 FAIL/BLOCKED/拒绝/超时/残留 → 停止并先报告；重跑需要新的单独授权与新的授权 ID。
* 单次运行不扩展到 G2/G3/BV/E1-A；通过 G1 也不构成对它们的授权。

**证据与结案**：运行目录 `evidence/g1_<UTC>_<rand>/`：`authorization_used.json`（不提交）、`registry.jsonl`（含 4 个节点，单一 `RUN_START`/`RUN_END`）、`g1_evidence.json`（每测试一节：快照 S0–S5、守卫记录、门字节序列、退出/回收时序、`/proc` 指纹、清理报告）、`g1_summary.json`（17×4 逐项裁决）、`g1_closed.json`（K1–K7：临时文件 + `os.link`，含证据/摘要哈希、`recorded_verdict`、`recorded_exit_code`）。管线 P0–P7：构造 → 严格序列化 → 独占写 + fsync → 读回校验 → 类型校验 → **只判定读回的证据** → 保存并校验摘要 → 发布结案标记 → 以记录的退出码退出。任何一步失败 = BLOCKED、退出码 3、stderr 标记。G0 的 `g0_*` 预检只列出 `g0_` 前缀目录（已核实 `closure_preflight`），`g1_*` 与 `_g1_consumed` 不干扰 G0；G1 自己的预检同时覆盖 `g0_*` 与 `g1_*`。

## 6. 后续阶段（每阶段单独授权，本稿只涉及第 1 阶段的前置设计）

1. 设计审核（本稿，ChatGPT/Grok）。
2. G1-IMPLEMENTATION：编码 + 静态审核（冻结 `g1_criteria_v1.json`、预注册文本、`g1_auth/judge/run`；追溯表；不运行）。
3. G1-PURE-TEST：CPU 纯逻辑测试，哨兵下运行（每测试的判定夹具、14+ 类故障注入、SystemExit/环境/HEAD 核验沿用 G0 收口测试、变异检查）；**不启动进程**。
4. G1-REAL：负责人单次授权，按本稿执行一次；停止，交审核。

验收标准（供各阶段审核）：判据文件冻结且哈希绑定；CPU 测试两次全通过且哨兵 0；变异检查覆盖“门泄漏 / R 误写 / 退出码错配 / 不可评估被当 FAIL / 信号 / 多 fork”；真实运行 17×4 全部满足、结案标记已发布、无残留、零信号。

## 7. 依赖

Git SHA `c3cf742dea57cad28c997a23df76b2f038e86d4d`（代码与 G0 CPU 验收 `a4a85095…` 相同）；Python 3.13.16；Linux ≥ 5.3（`pidfd_open`）；`socket.send_fds/recv_fds`（SEQPACKET）；`os.link`；`/proc`；同一 uid；4 CPU；无 GPU；Bench `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`；G0 V5 criteria `d36da0c0…cb821`、prereg `8338f4a0…ef6e25c`、E1-A 原预注册 `e6b7ca5c…ec39`。

## 8. 未解决问题（请审核者裁决）

* **Q1（F-1）** `observer._confirmed_dead` 把僵尸（Z）算作已死。是否在 G1 前修台架？建议**不改**（会使 Bench 哈希与既有证据失效）：G1 把回收排在清理之前，并要求每测试的 C08/C09 回收证据，因此不依赖该缺陷；但 G1 仍无法证明该缺陷在 `reap_direct` 超时路径上的行为——留给 G3。
* **Q2** INVALID_BYTE 取 `b"r"` 单值是否足够，或改为 `\x00`/`\xff`？
* **Q3** T4（及任何测试）子进程到期仍存活：建议 BLOCKED + 人工处置（宿主调度停顿无法排除）；若审核者认为这是证据完整的 I2 违规，可改为 FAIL。
* **Q4** G0 辅助函数的复用方式：只读导入（建议）还是在 G1 内参数化复制；实现阶段首先核对哪些函数带 G0 常量（`publish_closure`/`finalize` 含 `g0_*` 名与 schema）。
* **Q5** 首个非 PASS 即停（建议）vs 继续跑完四个测试以收集更多证据。
* **Q6** T1 是否保留 BV-1 的“预排队 SPEC”泄漏探针（建议保留）。
* 已知局限：Python 层守卫不证明内核层无路径；T1–T3 共用退出码 111，区分依赖观察者侧刺激证据；一次运行、单 VM，不是统计结论。

## 9. 唯一下一条研发指令

ChatGPT 与 Grok 审核本设计并裁决 Q1–Q6；通过后由项目负责人**单独**授权 `G1-IMPLEMENTATION-001`（仅编码与静态审核，不运行进程级测试，不创建授权文件）。
