# F3B-D1 CPU-003 E1-A G1 负向门控设计 checkpoint（2026-10-27）

* 任务 `F3B-D1-A-CPU-003-E1A-G1-NEGATIVE-GATE-DESIGN-001`；分支 `d1-r3-a-cpu-003-e1a-g1-negative-gate-design-20261027`；基准 `c3cf742dea57cad28c997a23df76b2f038e86d4d`（G0 REAL-001 PASS，已由 ChatGPT/Grok 交叉审核）。
* 状态：**G1 DESIGN PREPARED / G1 REAL NOT TESTED / G1 EXECUTION NOT AUTHORIZED。** 只提交设计文档与本 checkpoint：未写代码、未创建授权文件、未运行任何进程级测试、未用 GPU；G0 V1–V5、R3（含已归档的 R3 G1/G2 FAIL 记录）、上游 Bench 均未改动。G0 PASS 不推出 G1 PASS。
* 设计文件：`research/mini_mythos/a_predicate_003/gate_g1/E1A_GATE_G1_DESIGN.md`。四个测试 T1 ABORT / T2 EOF / T3 INVALID_BYTE（`b"r"`）/ T4 TIMEOUT（`t_gate_max` 2 s）；期望退出码 111/111/111/112；每测试一个子进程、一次 fork、零信号；独立入口 `gate_g1/g1_run.py`（实现阶段），不复用带 SIGKILL 拆除的原始 unittest；只读导入 G0 机制，不改 `g0_*`；单次授权 `e1a-gate-auth-g1-1`，绑定 G0 REAL-001 结案哈希；首个非 PASS 即停，无信号、无按名称清理、无自动重试；结案沿用 P0–P7 / K0–K7；裁决 FAIL > BLOCKED > PASS（退出码 1/3/0；任何 SystemExit → 3）。
* 一轮设计自检：对照 `gate.py`/`observer.py`/`node.py`/`registry.py`/`g0_run.py`/`closure_preflight` 核对了退出码来源、`abort_held` 写入顺序、登记序列合法性（REGISTERED→DEAD 无 RELEASED 合法）、`g0_` 前缀预检范围、清理在回收之后的次序；修正 1 处（逐测试用 `finish_cleanup(nodes=[rec])`，运行结束再 `final_cleanup`）。
* 依赖：Python 3.13.16、Linux ≥ 5.3（pidfd）、`socket.send_fds`、`os.link`、`/proc`、同 uid、4 CPU；Bench `b6f52a8c…d3b0`；G0 V5 `d36da0c0…cb821` / `8338f4a0…ef6e25c`；E1-A 预注册 `e6b7ca5c…ec39`。
* 验收标准（后续各阶段）：判据冻结并哈希绑定；CPU 测试两次全通过、哨兵 0、变异检查覆盖门泄漏/R 误写/退出码错配/不可评估被当 FAIL/信号/多 fork；真实运行 17×4 全满足、结案发布、无残留、零信号。
* 未解决问题（设计稿 §8）：Q1 F-1 僵尸即死缺陷是否在 G1 前修（建议不改）；Q2 无效字节取值；Q3 到期仍存活 BLOCKED vs FAIL；Q4 G0 辅助函数复用方式；Q5 首败即停 vs 跑满四个；Q6 是否保留预排队 SPEC 探针。
* 唯一下一条指令：ChatGPT 与 Grok 审核并裁决 Q1–Q6；通过后由项目负责人**单独**授权 `G1-IMPLEMENTATION-001`（仅编码与静态审核）。
