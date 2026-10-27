# E1A_GATE_G1_PREREG — E1-A 负向门控（G1）预注册文本，判据 V1

任务 F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001；基准提交 `48d241fa61b1e1824fca004e4db0719d5c8011b4`；已审核设计 `gate_g1/E1A_GATE_G1_DESIGN.md`（SHA-256 `da914829…095c`）。
本文件与 `g1_criteria_v1.json` 一起由**独立提交冻结**，其哈希写入 `*.sha256` 并进入授权绑定。若本文与 JSON 有出入，以 JSON 为准。**冻结后不得修改；发现缺陷只记录，修复需新版本与新授权。**

## 1. 目的与范围

验证：**没有收到有效放行字节 `b"R"` 的受控子进程不执行任何实验动作**（`gate.py` 不变量 I1/I2），在四个场景中：

| 测试 | 刺激（REGISTERED 之后、保持 0.3 s、S1b 快照之后） | 门上字节 | 期望退出码 | `t_gate_max` |
|---|---|---|---|---|
| T1_ABORT | 预排队一条 SPEC；`Observer.abort_held`：ABORTED 记录 → `b"A"` → 关门写端 | `[65]` | 111 | 5.0 s（兜底） |
| T2_EOF | 仅关闭门写端，不写字节 | `[]` | 111 | 5.0 s（兜底） |
| T3_INVALID_BYTE | 写恰好一个字节 `b"r"`（114），随后关门写端 | `[114]` | 111 | 5.0 s（兜底） |
| T4_TIMEOUT | 无刺激：门写端保持打开且沉默，观察到退出后才关闭 | `[]` | 112 | **2.0 s** |

每个测试：一个观察者、**恰好一个**子进程（`spawn_direct(..., hold_release=True)`）、一次 fork、零信号、零后代；顺序固定 T1→T4，任一时刻至多一个子进程；**任何测试里都不写 `R`、不调用 `Observer.release()`**。首个“不明显符合预期”的测试之后停止，其余为 `NOT_RUN`。G0 PASS 不是 G1 证据；G1 PASS 不是 G2/G3/BV/E1-A 的证据。

**T4 的超时参考是 fork 时间**（`guard.fork_events[].mono_before`）：退出不得早于 fork 后 `t_gate_max − 0.2 s`（1.8 s；更早的 112 不可能来自计时器），不得晚于 fork 后 5.0 s。S1/S1b 必须在子进程自身门计时器到期前至少 0.5 s 取得，否则身份/保持证据不足以支持结论，该测试为 **UNEVALUABLE（BLOCKED）**，不得 PASS。

## 2. 单测试操作顺序

S0（fork 前）→ `spawn_direct`：INTENT → fork → FORKED → 身份核验 → REGISTERED（**不放行**）→ 保持 0.3 s（消息泵）→ S1（含 fd 列表）→ S1b（刺激前，含 fd 列表）→ 刺激 → 等待 pidfd 可读（退出已观察）→ **回收前** S3（状态须为 Z）→ 对**该具体 pid** 非阻塞 `waitpid` 轮询 → `/proc/<pid>` 消失（S4）→ 若门写端仍开则关闭（T4）→ `finish_cleanup(nodes=[rec])`（仅回收之后，无信号）→ S5。整个运行：S0_run → 四个测试 → 全局 `final_cleanup` → `RUN_END` → S9_final。**不得用 `Observer._confirmed_dead()` 的僵尸态判断代替 waitpid 回收证据。**

## 3. 判据（17 项，逐测试评定；详见 JSON `checks`）

C01 预检干净（含 G0 REAL-001 参照证据核验）· C02 授权与绑定 · C03 登记序列与完整性（每场景的期望序列）· C04 刺激前已登记的身份（PID/starttime 五处一致）· C05 无放行即无动作 · C06 门描述符卫生 · C07 刺激精确性（字节序列、关闭次序、无 R、无 release）· C08 退出已观察且未回收（Z）· C09 按具体 pid 回收 · C10 门路径退出码（111/111/111/112；退出码 0 即 FAIL；113、负值、其他码不可评估）· C11 进程预算 · C12 零信号 · C13 清理与无残留 · C14 观察者描述符基线 · C15 时间界 · C16 证据完整 · C17 无未解释错误。

判据**不**沿用 G0 的“RELEASED 存在”和“退出码 0”要求。

裁决：每测试 FAIL（任一 FAIL 类检查有证据地违反）> BLOCKED（其他任何未通过/不可评估）> PASS；整个运行：任一执行过的测试 FAIL → FAIL；否则任一测试 BLOCKED、任一运行级检查未通过、或有测试 `NOT_RUN` 而所有已执行测试都 PASS（RUN-INCOMPLETE）→ BLOCKED；四个测试全部 PASS 且所有检查 PASS → PASS。退出码 PASS 0、FAIL 1、BLOCKED 3；退出码 2 仅用于拒绝执行与 argparse 用法错误；参数解析之后的任何异常或 `SystemExit` → 3（`G1-STARTUP-ERROR`）。格式损坏的证据不可评估，不是 FAIL。子进程到期仍存活 → BLOCKED + `MANUAL_DISPOSITION_REQUIRED.json`，**不发信号**。

## 4. 授权、安全、证据与结案

* 授权 `AUTHORIZATION_E1A_GATE_G1.json`：schema `e1a-gate-auth-g1-1`、stage `G1`、封闭 schema；grants `runs 1, tests [T1..T4], forks 4, signals 0, fault_injection false, max_concurrent_children 1, max_seconds 30`；`not_granted` 含 G0、G2、G3、BV、E1A-CELLS、E1-B、E1-C、E1-D、E2、E3；绑定十项：git_head、E1-A 原预注册、G0 V5 criteria / prereg、Bench、g0_code、**g1_criteria、g1_prereg、g1_code**、**G0 REAL-001 结案标记哈希**（`de96e1be…9736`）。单次使用：第一次 fork 之前以 O_EXCL 写入 `evidence/_g1_consumed/<id>.json`。授权文件及其运行副本不提交 Git。
* 守卫：Python 层陷阱（信号、exec/spawn/system/popen/subprocess、非该子进程的 wait）；`fork` 每测试一次、总计至多四次、上一子进程回收前不得再 fork；门写端的每次写与关闭逐次记录（含测试编号）；`R` 写入与 `Observer.release()` 被拦截并记为违规。Python 层陷阱不证明内核层无路径。
* 证据 `e1a-gate-g1-evidence-1`，管线 P0–P7，结案 K0–K7（`g1_closed.json`，临时文件 + `os.link`，不覆盖）；历史 `g0_*`（G0 V5 规则）与 `g1_*`（CL1-01…23）运行必须已结案。
* 失败关闭：无信号、禁止按名称/命令行/进程组清理、禁止自动重试；任何非 PASS 后停止并先报告；重跑需要新的授权与授权 ID。

## 5. 局限

Python 层守卫不是内核层证明；T1–T3 共用退出码 111，三种刺激由观察者侧证据区分；单次运行、单 VM；只测一个无效字节值（`r`）；`Observer._confirmed_dead()` 的僵尸即死行为（F-1）未被修改，G1 不依赖它；已结案的 FAIL/BLOCKED G1 运行不自动阻断后续预检，但后续执行需要新授权与负责人决定。
