# F3B-D1-A-CPU-003 E1-A — 检查点：预注册冻结与台架实现（未执行）

**状态：`CPU-003 E1-A PREREGISTRATION COMPLETE / BENCH IMPLEMENTED / STATIC REVIEW PENDING / EXPERIMENT NOT TESTED / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**

指令：`F3B-D1-A-CPU-003-E1A-PREP-001`（AUTHORIZED: PREREGISTRATION AND BENCH IMPLEMENTATION ONLY）。**本阶段没有运行 E1-A，也没有运行任何会 fork / 发信号 / 注入进程故障的测试；设计正确 ≠ 运行正确。**

## 1. 目标

(1) 把 E1-A（S0 会话前置条件）的验收判据**冻结**成机器可读预注册 `a_predicate_003/prereg/e1_provability_table_v1.json`，并先于任何台架提交单独提交；(2) 在不执行的前提下实现 E1-A CPU 台架（含 GATED-SPAWN 创建–登记–释放协议、独立谱系账本、fail-closed janitor、插桩、证据输出、清理检查）、测试用例与独立真值验证代码；(3) 只做静态审查。E1-B/C/D 保持待批准、未冻结。

## 2. Git

| 项 | 内容 |
|---|---|
| 仓库 | `leotree2020/OpenMythos` |
| 分支 | `d1-r3-a-cpu-003-e1a-prep-20261027`（建在 CPU-003 设计分支顶端 `6a089f5`） |
| 基线提交 | `6a089f5980657fe7e5f92f8a2e64579dcfac727b`（开始前已核对远端 HEAD = 本地 HEAD，工作树干净） |
| 预注册提交（早于任何台架提交） | `b2aec0f` 首次冻结 → `c02f201` PREP-CORR-1 → `f9d3cd8` PREP-CORR-2（均仅含预注册文件） |
| 预注册 SHA-256（最终） | `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39` |
| 预注册首次冻结 SHA-256 | `9df3eafde8972645660abbc229b185a8328f24377d0db1e7941e7621fcac0828`（`b2aec0f`）；PREP-CORR-1：`22d64ef856a92c73b87c0c8343afec4d847e9110a1964e14c62623a36d52e3a8`（`c02f201`） |
| 本检查点生成时 HEAD | `f9d3cd8dbc1dabbfb681feb662a7bab9e25941a4`（本检查点及台架提交随后追加；最终提交哈希与推送后的远端树核对结果见交付报告） |

本分支相对基线的提交（检查点生成时）：

- `f9d3cd8 F3B-D1-A-CPU-003 E1-A: prereg correction PREP-CORR-2 (aggregation rule; still before any bench commit)`
- `c02f201 F3B-D1-A-CPU-003 E1-A: prereg correction PREP-CORR-1 (still prereg-only, before any bench commit)`
- `b2aec0f F3B-D1-A-CPU-003 E1-A: freeze preregistration e1_provability_table_v1.json (prereg only, no bench code)`

预注册更正的原因与范围见预注册 `correction_log` 与 `a_predicate_003/STATIC_REVIEW.md` 第 1 节：两次更正都发生在任何台架提交、任何执行之前，分类表各行均未改动。

## 3. 环境

| 项 | 内容 |
|---|---|
| 主 Python | 3.13.16（预注册 `primary_python`；运行器启动检查强制一致） |
| 内核 | `6.18.44-fc-v165`（Firecracker 微型虚机），uid 0，cgroup v1 |
| 依赖 | 仅标准库（`ctypes`、`socket`、`os`、`signal`、`json` 等）；无第三方包，无网络，无 GPU，CPU-first |
| 能力（须在首次运行时由台架自检确认） | `os.pidfd_open`、`signal.pidfd_send_signal`、`socket.send_fds/recv_fds`、`os.waitid`、`prctl(PR_SET/GET_CHILD_SUBREAPER)` |

## 4. 输入与期望（均为预注册，非观察）

**输入：** 冻结的 `e1_provability_table_v1.json`（12 场景 × 候选 P0/P1/P2；P3/P4 未分类）；被钉死哈希的 CPU-001 `a_lab.py`（P0，也是 P1 的基础）与 CPU-002 `e2_lab.py`（P1）；新写的 S0 候选 `candidates.s0_check`（P2）。

**期望（由 ECD 机械推出，不是调参）：** P0 能证明 5/12 格、7/12 格 UNPROVABLE；P1 能证明 9/12、3/12 UNPROVABLE；P2 能证明 12/12。

| 场景 | P0 | P1 | P2 |
|---|---|---|---|
| E1A-a | ACCEPT | ACCEPT | ACCEPT |
| E1A-a2 | ACCEPT | ACCEPT | ACCEPT |
| E1A-b | 拒绝（ACCEPT=FAIL） | BLOCKED stage-session-not-dedicated | BLOCKED not-pgroup-leader+not-session-leader+session-is-supervisor-session |
| E1A-c | 拒绝（ACCEPT=FAIL） | BLOCKED stage-session-not-dedicated | BLOCKED not-session-leader+session-is-supervisor-session |
| E1A-d | 拒绝（ACCEPT=FAIL） | BLOCKED stage-session-not-dedicated | BLOCKED not-pgroup-leader+not-session-leader |
| E1A-e1 | 拒绝（ACCEPT=FAIL） | 拒绝（ACCEPT=FAIL） | BLOCKED has-preexisting-children |
| E1A-e2 | 拒绝（ACCEPT=FAIL） | 拒绝（ACCEPT=FAIL） | BLOCKED supervisor-has-unregistered-children |
| E1A-f | BLOCKED fingerprint-mismatch | BLOCKED fingerprint-mismatch | BLOCKED fingerprint-mismatch |
| E1A-g | 拒绝（ACCEPT=FAIL） | 拒绝（ACCEPT=FAIL） | BLOCKED sigchld-not-default |
| E1A-h1 | BLOCKED preflight-failed | BLOCKED preflight-failed | BLOCKED subreaper-not-verified |
| E1A-h2 | BLOCKED preflight-failed | BLOCKED preflight-failed | BLOCKED subreaper-not-verified |
| E1A-i | 拒绝（ACCEPT=FAIL） | BLOCKED stage-session-not-dedicated | BLOCKED not-pgroup-leader+not-session-leader+session-is-supervisor-session |

计划规模：1120 次试验（36 个单元 × 20 次确定性重复 = 720，加 `E1A-a` × {P1,P2} × 4 个启动上下文 × 50 次误拒扫描 = 400）。已批准的准备参数仅适用于**未来运行**，不是 PASS：W1/W2 意外 UNKNOWN 目标 0；台架 BLOCKED ≤ 5%/单元；E1-D 每单元 ≥ 50；主 Python 3.13.16；不做 5,000 次压力运行；cgroup / proc connector 只做只读调研。

**判定分层：** 机制状态（ACCEPT / BLOCKED / UNKNOWN）与实验判定（PASS / FAIL / BLOCKED / NOT TESTED）分开；实验判定 = S0 候选 P2 的候选判定；P0/P1 的 FAIL 作为能力发现报告；不选最终胜者。

## 5. 交付物

| 路径（`research/mini_mythos/a_predicate_003/`） | 内容 |
|---|---|
| `prereg/e1_provability_table_v1.json` + `.sha256` | 冻结预注册 |
| `bench/` | `common`、`registry`（REG 文件）、`proto`、`gate`（唯一的 `os.fork`）、`node`、`observer`、`janitor`、`sup_stub`、`candidates`（P0/P1/P2）、`scenarios`、`truth`（独立真值 + 判定函数）、`trial`、`validity`（BV-1/2/3/6/7）、`e1a_runner`（`--check` / `--plan` / `--execute` 互锁） |
| `tests/` | `test_e1a_logic.py`（纯逻辑，以冻结表为期望）、`test_e1a_gate.py`（进程级，含单次完整试验冒烟）、`test_e1a_runner_interlock.py`——**全部已编写、未运行** |
| `tools/` | `static_audit.py`（AST 审计）、`check_prereg_schema.py`（独立重算分类表） |
| `run_e1a.sh` | 首次受控运行的包装脚本（**未运行**；运行器另需 `AUTHORIZATION_E1A_RUN.json`，该文件**不存在**） |
| `STATIC_REVIEW.md` | 静态审查报告（协议↔代码对照、审计清单、自审缺陷、风险、哈希） |

## 6. 执行状态

| 项 | 状态 |
|---|---|
| E1-A 实验 | **NOT TESTED**（未运行；运行器互锁拒绝，无授权文件） |
| GATED-SPAWN 台架有效性检查 BV-1…BV-10 | **NOT TESTED**（已编写，未运行） |
| 全部测试文件 | **未运行** |
| 静态检查 | 完成：AST 解析全部通过；`static_audit.py` 0 条违规；`check_prereg_schema.py` ok；`e1a_runner.py --check` ok |
| E1-B / E1-C / E1-D / E2 / E3 | **NOT TESTED / 未冻结 / 未授权** |
| P3 proc connector / P4 cgroup | **UNVERIFIED**（仅只读读取内核配置与挂载布局，见 STATIC_REVIEW 第 8 节） |

## 7. 剩余台架风险（详见 STATIC_REVIEW 第 7 节）

所有进程级路径从未执行，`SOCK_SEQPACKET`+`SCM_RIGHTS`、`exec` 后 fd 继承、pidfd 语义均为设计假设（S-1）；ERRATA-002 的 R1–R7 如实保留，R2/R3/R4 无法由本台架消除（S-2）；盲性是构造性的而非安全边界（S-3）；`E1A-g`、`E1A-a2`/`E1A-i` 依赖的内核/Python 行为假设（S-4、S-5）；L4 需伪终端（S-6）；单环境单版本（S-7）；测试未运行（S-8）；耗时未测量（S-9）；E1-A 不检验后续归属质量（S-10）。

## 8. 完整性状态（生成本检查点时核对）

| 项 | 结果 |
|---|---|
| 冻结 R3 候选 | `66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5`（= `66a656145fc203c7…`，未变） |
| 负责人决定记录 | `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319`（= `6209602e7d51b1ae…`，未变） |
| 冻结记录 | `e3bba6b0968101bf68ce4679d8eb6b6c9b1e4a748227479c11c74b2782bf596f`（= `e3bba6b0968101bf…`，未变） |
| `D1_CODE_SHA256SUMS` | 10/10 OK |
| `D1_FROZEN_CONFIG.json` | 含 FROZEN 标记 7 处，未改 |
| CPU-001 / CPU-002 代码与证据 | 相对基线 `git diff --stat`（`r3_cpu_probes`、`gate3_d1`、`interfaces`、`scripts`）：（空：无差异） |
| 本分支相对基线的改动范围 | 仅 `a_predicate_003/` 与 `docs/`；基线之外的其它路径：无 |
| v1 / R1 / R2 / Driver / Reader / Verifier / 上游 Parcae / 真实 D1 | 未触碰 |
| `.gitignore` | 新路径经 `git check-ignore` 核对均未被忽略；`__pycache__/` 已被 `research/mini_mythos/.gitignore` 忽略，且本分支未提交任何 pyc |
| 推送后核对 | 以远端树逐文件核对（见交付报告） |

## 9. 下一条唯一指令

把**冻结预注册（`f9d3cd8`，SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）、台架源码、`git diff`、`STATIC_REVIEW.md`** 提交给 ChatGPT 做静态审查；审查通过后，**由项目负责人单独授权**首次受控 CPU 运行（建议先做单格冒烟，如 `--only E1A-a:P2 --reps 1 --no-sweep`，其结果只用于排除台架缺陷，且需创建 `AUTHORIZATION_E1A_RUN.json` 引用预注册哈希）。**在此之前不得执行任何台架代码；不得自动进入实验执行。**

## 10. 状态声明

R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；G3～G6 NOT TESTED；NO A-B WINNER（不选 CA / CB / 任何变体）；Grok：CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED（仓库无 Grok 审核文件；未声称 Grok 重跑过实验）；E1-A 为 **EXPERIMENT NOT TESTED**。
