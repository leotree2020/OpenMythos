# F3B-D1-G1G2-CPU-001 — 检查点：R3 存活目标判定 A（G1 / G2）CPU 实验

**结论：实验工具运行 PASS；R3 存活判定规则 G1 = FAIL，G2 = FAIL。** 冻结的 R3 规范与负责人决策记录**未被修改**；修订方向只作为建议写在报告里，等待 ChatGPT 独立审核及项目负责人对行为变更的裁决。**不自动启动 G3～G6。**

## 1. Git 与环境

| 项 | 内容 |
|---|---|
| 仓库 / 实验分支 | `leotree2020/OpenMythos` / `d1-r3-g1g2-cpu-probe-20261027`（从 `d1-r3-spec-freeze-20261026` 新建） |
| 基准 SHA | `39c55ca2cfa6d0587807be2af524d67479e76251`（R3 规范冻结提交） |
| 最终 SHA | 与本检查点同一提交；见汇报（提交后以 `git rev-parse` 与 `git ls-remote` 确认） |
| 内核 / Python | `6.18.44-fc-v153` / `3.13.16`（x86_64，microVM，`/.dockerenv` 不存在） |
| `/proc`、`os.waitid`、`WNOWAIT`、`WEXITED`、`P_PID`、`waitpid`、`killpg` | 全部可用 |
| 联网 / 第三方依赖 | 无 / 无 |

## 2. 每项用例的实际结果（5 次重复完全一致；详见报告第 3 节）

| ID | 独立真实状态 | R3 字面 A（NOREAP / EVAL_THEN_REAP / REAP_THEN_EVAL） | 错误建议升级 SIGKILL | 工具 | 规则 |
|---|---|---|---|---|---|
| G1-01 | RUNNING | 真 / 真 / 真 | 否 | PASS | PASS |
| G1-02 | EXITED_UNREAPED | **真 / 真** / 假 | **是**（前两种读法） | PASS | **FAIL** |
| G1-03 | EXITED_UNREAPED → REAPED | 假（已回收，`killpg0`=ESRCH） | 否 | PASS | PASS |
| G2-01 | EXITED_UNREAPED（组内仅一个 `Z` 成员） | `killpg(pgid,0)` = **success**（回收后才 ESRCH） | **是**（条件 (2) 单独成立） | PASS | **FAIL** |
| G2-02 | SIGTERM 后 EXITED_UNREAPED | 自然轮询：**ESCALATE** / EARLY_CONFIRM / EARLY_CONFIRM；宽限点竞态：**ESCALATE / ESCALATE** / EARLY_CONFIRM | **是** | PASS | **FAIL** |
| G2-03 | RUNNING（忽略 SIGTERM） | 真 / 真 / 真 | 否（升级正确） | PASS | PASS |

## 3. G1 / G2 整体状态

| 门禁 | 工具（证据采集） | R3 规则（架构正确性） | 说明 |
|---|---|---|---|
| G1：`waitpid(WNOHANG)` 与存活目标 A 的协调 | PASS | **FAIL** | 条件 (1) 是账目事实，已退出未回收时持续为真；R3 没有规定 A 求值与 `waitpid(WNOHANG)` 的先后 |
| G2：已退出但尚未回收时不得错误认定需 SIGKILL | PASS | **FAIL** | `killpg(pgid,0)` 对只含僵尸的进程组仍成功；`NOREAP` 读法在宽限点错误建议 SIGKILL，`EVAL_THEN_REAP` 在宽限点竞态下也会 |

「证据采集 PASS、规则 FAIL」的含义：实验成功复现了 R3 判定的缺陷，**这不是把 FAIL 写成 PASS**。仅 `REAP_THEN_EVAL`（先回收再求值）读法下全部用例与规范意图一致——这只是建议方向，**未应用**。

## 4. 证据文件与 SHA-256

| 文件 | SHA-256 |
|---|---|
| `research/mini_mythos/docs/F3B_D1_G1G2_CPU_001_REPORT_20261027.md` | `2f9e2ef9e0668988c8beecc854c1db099eb9e84ab4eb7a5bf1675390fb7410f8` |
| `research/mini_mythos/r3_cpu_probes/g1g2/g1g2_probe.py` | `babab202a605f457b0a79fbf71f06aabfb36e848f9ef5895f352d161f82d81a4` |
| `research/mini_mythos/r3_cpu_probes/g1g2/test_g1g2_probe.py` | `eb1857414868ba9aee6589848f5f7a3e153f23ca4ce6e13fd4f04f1c7970cbaa` |
| `research/mini_mythos/r3_cpu_probes/g1g2/results/g1g2_cpu_001_results.json` | `a224a02103b1ee6724693f8781498a96451f2b1a7662e32ad4b4db89fef8c47b` |
| `research/mini_mythos/r3_cpu_probes/g1g2/results/g1g2_cpu_001_run_stdout.txt` | `b5b9e768a7a832a8b3684bbd9987e3bd3a38a89556752a5be9e624967e94b1e9` |
| `research/mini_mythos/r3_cpu_probes/g1g2/results/g1g2_unittest_output.txt` | `4979dd157dc10494e628f22014daee1966b197eb89662f8bb92915c8cc0212de` |

## 5. 残留进程检查

- 探针累计创建 65 个受控子进程（5 次重复 × 13），全部已终止并回收；`/proc` 中残留 pid：[]；按探针令牌扫描 `cmdline` 的残留 pid：[]；清理备注：[]。
- 运行结束后独立再查 `ps`：无带探针令牌的进程；`/proc` 中的进程数与运行前相同（78）。
- 信号安全：所有信号都经 `guard()`（仅限本探针 `fork` 出的、`ppid`=探针、`pgid`==自己 pid、`cmdline` 含令牌、尚未回收的子进程；拒绝探针自己的进程组、pid 1、未登记的 pid、已回收的 pid）；9 个单元测试覆盖了这些拒绝。

## 6. 冻结文件完整性（实验前后均核对）

| 项 | 状态 |
|---|---|
| `D1_CODE_SHA256SUMS` | 10/10 OK |
| `D1_FROZEN_CONFIG.json` | 仍 `FROZEN`（`0d35dc21a4beca7c…`） |
| v1 / R1 / R2 | `a55b2cb7…` / `f92c4e79…` / `1d4c3629…` 不变 |
| R3 规范（冻结） | `66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5` 不变 |
| 负责人决策记录（冻结） | `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319` 不变 |
| R3 冻结记录 | `e3bba6b0968101bf68ce4679d8eb6b6c9b1e4a748227479c11c74b2782bf596f` 不变 |
| Git 范围 | 仅新增 `research/mini_mythos/r3_cpu_probes/g1g2/`（探针、测试、结果）、报告、本检查点，并追加三个项目索引；无冻结文件、Driver / Reader / Verifier、上游 Parcae、模型代码被修改 |

## 7. 未解决问题

1. **R3 存活判定 A 的缺口 / 歧义（本实验的发现）：**须经 ChatGPT 独立复审，并由项目负责人对行为变更裁决后，按冻结记录第 6 节的变更流程（独立修订文件、CPU 受控实验、审核、必要时重新批准、新版本与新 SHA-256）处理。本实验**未**修改冻结 R3，也未在探针里偷偷修补 A。
2. 条件 (3)（`PR_SET_CHILD_SUBREAPER`、重新挂靠的后代，含重新挂靠的僵尸后代）未构造——属于 G5，NOT TESTED。
3. G3（提前退出且回收慢）、G4（ESRCH / EPERM 记录）、G5（生命周期）、G6（UNPROVABLE 与 FAIL 优先级）：**NOT TESTED，未启动**。
4. 缩放计时（0.5–1.0 s 宽限、0.1 s 轮询）只验证谓词逻辑，不是 `G_term`=10 s / 1 s 轮询粒度的实测。
5. 结果来自单一内核 / 环境；其它内核对僵尸组 `killpg(pgid,0)` 的行为未验证。
6. 正式运行前有 3 次工具调试试运行（未入库）；它们暴露的两个探针缺陷（spawn 的 exec 竞态、对退出中进程的守卫过严）已修复，判定准则未变（报告第 1 节）。
7. 沿用的未解决项：D08 用途声明文本取自推荐方案的草案文本；D06 只批准 B-LFS；τ / `G_term` / `G_kill` / `W` 是初始验收值；GitHub 分支保护 NOT VERIFIED；真实 D1 NOT AUTHORIZED；新脚本（除本探针外）未编写。

## 8. Grok 复审状态

**DEFERRED**（不是 PASS）。

## 9. 下一条唯一研发指令

等待 ChatGPT 对 G1/G2 CPU 实验结果进行独立审核。**不自动启动 G3～G6。**
