# F3B-D1-A-CPU-003 — 检查点：安全监督器最小受控实验设计（仅文档）

**状态（ERRATA-002 后）：`CPU-003 DESIGN ERRATA-002 COMPLETE / PENDING CHATGPT REVIEW / EXPERIMENTS NOT TESTED / DESIGN ONLY / R3 SPEC FROZEN / REAL D1 NOT AUTHORIZED / NO A-B WINNER`**（ERRATA-001 状态：DOCUMENT ACCEPTANCE PASS / STAGE 1 PRE-EXECUTION CONDITIONS OPEN；第 12 节追加 ERRATA-002）。**Grok：`GROK CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED`**（旧版本此处写的是"DEFERRED 至 2026-10-30"，已由勘误 ERRATA-001 更正；历史见提交 `6c8bab5`）。三项实验 E1 / E2 / E3 均为 **DESIGN ONLY / NOT TESTED**。本轮没有执行任何实验、没有启动任何进程故障注入、没有选择最终方案。

## 1. Git

| 项 | 内容 |
|---|---|
| 仓库 | `leotree2020/OpenMythos` |
| 新分支 | `d1-r3-a-cpu-003-design-20261027`（独立文档分支，建在 CPU-002 实验分支的证据补正提交上；CPU-002 分支未被修改） |
| 基线提交 | `6bd8c53eb424960aa6d3c849665037a59e00236f`（`d1-r3-a-cpu-002-minimal-dispute-20261027` 远端顶端；开始前已用 `git ls-remote` 与 `git fetch` 核对一致） |
| 基线核对 | 远端提交 `6bd8c53` 的文件树里存在 CPU-001 原始分片归档 4 个文件（`cpu001_run{1,2}_*_parts.{tar.gz,sha256}`），两个 tar.gz 的 blob SHA-256 为 `e941d4be…`（run2）、`bccc5fa8…`（run1），与 CPU-002 检查点登记值一致 |
| 最终提交 | 与本检查点同一提交（SHA 见汇报） |

起点核对的原始输出保存在会话临时目录中，没有入库；核对结论见本节与第 6 节（提交后用远端文件树复核）。

## 2. 环境（设计阶段只读测得）

内核 `6.18.44-fc-v165`；Python 3.13.16（另有 3.11.15、3.12.3；3.9 / 3.10 / 3.14 不可用）；root；4 CPU；`pidfd`、`waitid`、`WNOWAIT`、子收割者可用；**只有 cgroup v1 控制器**；内核配置 `CONFIG_CONNECTOR`、`CONFIG_PROC_EVENTS`、`CONFIG_PID_NS` 开启。以上仅是读取系统文件与 CPython 源码得到的事实，不是实验结果。

## 3. 证据来源（如实标注）

| 来源 | 状态 |
|---|---|
| CPU-001 报告 / 检查点 / 合并原始记录 | 在 Git；本轮只读 |
| CPU-002 预注册计划 / 报告 / 检查点 / 430 条原始记录 / 逐用例 `parts` / CPU-001 原始分片归档 | 在 Git（归档在补正提交 `6bd8c53`）；本轮只读 |
| ChatGPT 对 CPU-002 的独立审核 | **在对话中提供，没有保存为仓库文件** |
| Grok 对 CPU-002 的交叉审核 | **已完成（GROK CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED）。**审核信息由项目负责人提供；本会话只收到负责人对三项共同原则的概括，**没有收到原文**；**仓库中不存在 Grok 审核文件**（`grep` 仅发现各历史检查点里的 DEFERRED 标注，这些历史记录按要求保持原样）。**没有**声称 Grok 独立重跑了 CPU-001 / CPU-002；**没有**虚构审核文件或审核提交 |
| CPython `subprocess.py`（3.11 / 3.12 / 3.13）源码阅读 | 只读文档阅读；结论（`ECHILD→returncode=0`、`Popen.__del__ / _active` 隐蔽消费路径）标注为"源码阅读，NOT TESTED 于 3.11 / 3.12" |

## 4. 新增与修改的文件

| 文件 | 用途 | SHA-256 |
|---|---|---|
| `docs/F3B_D1_A_CPU_003_DESIGN_PLAN_20261027.md`（勘误后版本；勘误前 `bca9a7aa…`） | 三项实验的目标、矩阵、独立真值、验收判据、13 张实验卡（每张 15 个必填字段 + 否定条件 + 状态）、执行顺序、安全边界 | `a3e6f54d8c780b256dc8a9f3e09f6e93104d9cc394c6b1301f14b58464b90f59` |
| `docs/F3B_D1_A_CPU_003_ARCHITECTURE_OPTIONS_20261027.md`（勘误后版本；勘误前 `b1527454…`） | 归属 O-0…O-7、消费 A / B / C、恢复 R-0…R-E 的候选、依赖、优缺点、未解决问题、待决分歧 | `16a0609cc169e8149c6642a027c576eed3247223d19b4a7cb437458dbd0c5a53` |
| `docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md` | **勘误文件（规范性）**：ERRATA-01…04、Grok 状态同步 | `8677b539e82ebc7e9cc5fdc545d8ad0e412215946fa46b2226771617da24830c` |
| `docs/F3B_D1_A_CPU_003_DESIGN_ERRATA_002_20261027.md` | **勘误-002（规范性）**：ERRATA-002-01 歧义负例按机制预先分类（ECD / PROVABLE / UNPROVABLE / BENCH_UNVERIFIABLE / 冻结）；ERRATA-002-02 GATED-SPAWN 创建—登记—释放协议、不变量 I1–I4、剩余风险 R1–R7 | `eeac9f446d0bdac814c78931529119cf100aa2d6314b53b17eac81fffea17314` |
| `docs/F3B_D1_A_CPU_003_CHECKPOINT_20261027.md` | 本检查点（已追加第 10、11 节勘误后状态） | （自身不登记） |
| `docs/PROJECT_MAP.md`、`docs/PROJECT_STATUS_20261025.md`、`docs/SESSION_START_PROTOCOL.md` | 只追加索引块（零删除行） | 见 Git |

## 5. 三项实验的验收门槛摘要（详见设计计划）

| 实验 | 硬门槛 | 要点 |
|---|---|---|
| **E1** 安全归属与 S0（E1-A…D） | 非目标误信号 = 0；误回收 = 0；归属不明 → `UNKNOWN`，不猜测；配置错误在任何破坏性动作前 `BLOCKED`；真实后代不被遗漏为 `EXITED` | E1-A：S0 对 9 种错误配置前置拒绝；E1-B：登记表 + S0 空子进程检查 / 专用监督器进程 / 严格变体 / cgroup 与 proc connector 的可行性探针，含"绕过入口"对抗用例；E1-C：跨会话后代与 **look-alike 陌生进程**（`/proc` 可见字段完全相同，预期不可区分 → `UNKNOWN`）；E1-D：合法负载上的 `UNKNOWN` 率与 CPU-001 回归，阈值留给负责人 |
| **E2** 唯一回收者（E2-A/B/C/V/R） | 未知状态不得当成功；不得有两个竞争的消费者；码 / 信号符合独立真值；不回收无关子进程；无不可解释的丢失；不能保证正确性时返回 `UNKNOWN`/`BLOCKED` | 12 个场景 S01–S12（含 `SIGCHLD=SIG_IGN` 继承、`Popen.__del__`/`_active` 隐蔽消费、core 标志）；Python 3.11/3.12/3.13 版本矩阵；强制交错钩子优先于重复次数；CA-P 的局部通过 ≠ 架构验收 |
| **E3** 崩溃恢复（E3-0/A/B/C） | 误杀 / 误回收 = 0；**"进程全部退出"与"状态全部保存"分别判定**；不可恢复的状态只能 `DECLARED_LOST`，不得伪造；僵尸不得无限期无人负责；身份不可验证 → 不发信号 + `BLOCKED` + 诊断 | 10 个故障场景 F01–F10；Watchdog / 账本 / 组合与基线 R-0 对比；台架观察者持有 pidfd 作独立真值；清理梯度在监护组件失效时仍成立 |

## 6. 完整性核对（提交前）

| 项 | 实际 | 状态 |
|---|---|---|
| 变更范围 | 仅 `docs/` 下 3 个新文件 + 3 个索引文件的追加（相对基线 `6bd8c53`） | PASS |
| 新文件未被 `.gitignore` 忽略 | `git check-ignore -v` 对 3 个新文件均无输出；并在推送后用远端提交的文件树复核 | PASS（以汇报中的远端核对为准） |
| CPU-001 / CPU-002 代码与证据 | 相对基线无差异（`git diff --stat 6bd8c53 -- research/mini_mythos/r3_cpu_probes` 为空）；两份报告 / 检查点 / 计划哈希不变 | PASS |
| 冻结 R3 / 决策记录 / 冻结记录 | `66a65614…42c5` / `6209602e…6319` / `e3bba6b0…596f` 不变 | PASS |
| `D1_CODE_SHA256SUMS` | 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN` | PASS |
| 上游 Parcae / 真实 D1 / G3～G6 / GPU | 未触碰 / 未运行 / NOT TESTED / 未使用 | PASS |
| 实验是否被执行 | **没有**；仅读取文件与源码 | PASS |

## 7. 未解决问题与待决分歧

分歧是设计者识别的待决问题，**不是**对 ChatGPT 或 Grok 立场的转述（没有两位审核者的逐项立场）：(1) 封闭世界：声明→强制→消除；(2) 严格变体的 `UNKNOWN` 代价是否可接受；(3) `Popen` 是否继续留在 R3 监督路径；(4) 观察与消费的时序（先持久化再消费 vs 先消费）；(5) 恢复是否自动（Watchdog + 账本 vs `BLOCKED` + 清理工具）；(6) 账本与冻结 R3 事件注册表 / RA-10 的关系是否需要 R3 变更。另：条件 (3) 的僵尸语义歧义、cgroup v1 环境限制、仅 root 环境、监督器死亡后存活目标继续运行（两臂相同）仍未解决。

## 8. 需要负责人批准的后续实验

逐 Stage 单独授权：Stage 1（E1-A→D）、Stage 2（E2-V→A/B/C→R）、Stage 3（E3-0→A/B/C）；并先决定：`UNKNOWN` 率阈值、支持的 Python 版本范围、是否允许特权设施、恢复范围（自动 vs 清理工具）、T2（×5000）档位。**本检查点不授权执行任何实验。**

## 9. 下一条唯一研发指令（勘误后见第 11 节）

（历史）提交 CPU-003 设计计划供 ChatGPT 独立审核，再由项目负责人决定是否授权执行三个最小 CPU 实验。

## 10. 勘误后状态（F3B-D1-A-CPU-003-DESIGN-ERRATA-001）

- **基准：**勘误前已审核提交 `6c8bab536cd38b4664fdb73b72d105092853bed8`；开始前核对远端分支 HEAD 与本地一致、工作树干净。**最终提交：**与本检查点同一提交（SHA 见汇报）。
- **四项勘误已关闭（文档层）：**
  - **ERRATA-01**（`UNKNOWN` 率）：N/L/A/M 试验类别与 R/U-exp/U-unexp/X/B 结果类；W1、W2 目标 0%（**ChatGPT 建议，待负责人正式批准**）；分子分母与台架 BLOCKED 排除规则（排除只依台架层原因，单元 BLOCKED > 5% → INSUFFICIENT）；负例正确 `UNKNOWN` 计 PASS；安全性与可用性分开报告；任何误信号 / 误回收为 FAIL，不得被低 `UNKNOWN` 率抵消；每单元 ≥ 50 并报告上界。
  - **ERRATA-02**（独立真值）：`pidfd` 只证明身份稳定性 / 生命周期，不证明血缘；归属真值 = 台架创建时的谱系账本；被测监督器盲；节点规格不再放 `argv`；`setsid` / 双重 fork 后仍按创建谱系判定；区分"真相已知但机制无法证明"与"台架无法建立真值"；`/proc` 字段相同 ≠ 身份相同。
  - **ERRATA-03**（清理）：令牌扫描不再授权发信号（只做诊断）；创建时登记，先 `pidfd_open` 再核对 `starttime`；禁止 `pkill` / 名称匹配 / 清理性 `killpg`；身份不明则停止并台架 BLOCKED；最终清理责任 = 台架观察者，观察者失效则 janitor；失败留痕。
  - **ERRATA-04**（分层）：机制协议状态与实验判定分开；机制 `BLOCKED` 若符合预期，实验判 PASS；所有 13 张卡新增映射行，`BLOCKED Criteria` 明确只指实验层。
- **Grok 状态已同步**（见本文件头部与第 3 节）；CPU-002 的原始检查点与早先索引块中的"DEFERRED"保持原样，作为历史记录。
- **仍未解决：**0% / 5% / n ≥ 50 为提议值待批准；E3 的"设计上可恢复"逐场景 × 机制表尚未编制（Stage 3 授权前完成）；盲性要求的实现需在写台架时验证（同 uid 下为构造性盲）；janitor 之外无自动清理层（残余风险）；封闭世界的强制方式、严格变体可用性、Popen 去留、先持久化再消费、恢复是否自动、账本与 R3 注册表的关系（见第 7 节，不变）。
- **E1 / E2 / E3 全部仍为 DESIGN ONLY / NOT TESTED。**没有执行任何实验、没有进程故障注入；没有选择任何方案。

### 勘误后完整性核对

见提交前核对输出（保存于 `F3B_D1_A_CPU_003_DESIGN_ERRATA_001_20261027.md` 第 6 节所列项目）：Git diff 仅含批准的文档；冻结 R3 / 决策记录 / 冻结记录 SHA-256 不变；`D1_CODE_SHA256SUMS` 10/10；CPU-001 / CPU-002 原始证据与报告不变；Parcae 不变；新增文件未被 `.gitignore` 排除；推送后用远端文件树复核；远端 HEAD = 报告的提交。具体结果见汇报。

## 11. 下一条唯一研发指令（勘误后）

提交设计勘误供 ChatGPT 最终审核；审核通过后，等待项目负责人**单独**批准 CPU-003 Stage 1（E1）实验。不要自动开始 Stage 1、Stage 2 或 Stage 3。

## 12. ERRATA-002 后状态（F3B-D1-A-CPU-003-DESIGN-ERRATA-002）

- **基准：**ERRATA-001 已审核提交 `196dbba9705ad12d3b6c8a56c247ec844e96769b`；开始前核对远端 HEAD = 本地 HEAD、工作树干净。**最终提交：**与本检查点同一提交（SHA 见汇报）。
- **ChatGPT 对 ERRATA-001 的结论：**DOCUMENT ACCEPTANCE PASS / STAGE 1 PRE-EXECUTION CONDITIONS OPEN；四项原勘误通过，本轮只处理两个剩余问题。
- **ERRATA-002-01（歧义负例验收逻辑）：**不再把"A 类歧义负例中所有确定答案一律 FAIL"。改为**按候选机制预先分类**：每个机制登记证据能力声明 ECD 与证明规则；每个（场景 × 机制）在执行前冻结为 PROVABLE（期望带合法证明引用的正确确定答案）/ UNPROVABLE（期望 `UNKNOWN`；任何确定答案，即使碰巧正确，都是 FAIL）/ BENCH_UNVERIFIABLE（台架 BLOCKED）；分类表为机器可读文件（`e1_provability_table_v1.json`，Stage 1 授权时先于运行代码提交，哈希写入每个分片），观察结果后不得改类；运行期证据失效须由台架独立确认才可降级。已提供初始分类表（P0–P4 × 场景）供审核。零误杀、零误回收、不得伪造 `EXITED` 的硬门槛不变。已同步 ERRATA-001（带【ERRATA-002 修订】标记）、E1-B / E1-C / E1-D。
- **ERRATA-002-02（Janitor 登记持久化竞态）：**GATED-SPAWN 协议——意向记录先于 `fork()`；新进程先停在门（管道）上；观察者取得身份、`pidfd_open`、核对、**持久化登记（`write` 返回）之后**才 RELEASE；登记失败 / 观察者死亡 / 超时 → 新进程读到 EOF / ABORT / 自身 `T_gate_max` 超时后自行退出（失败关闭）；后代走同一门票协议；Janitor 只处理 `INTENT`+完整 `REGISTERED` 记录并**重新**`pidfd_open` 与核对 `starttime`（旧 pidfd 整数不可恢复）；`fork()` 调度顺序不影响协议；普通进程崩溃恢复，不含掉电。不变量 I1–I4；**如实标注剩余风险 R1–R7 与 BLOCKED 条件，不声称已完全解决。**
- **仍为建议值、待负责人正式批准：**`UNKNOWN` 率 0%、台架 BLOCKED 5%、每单元 ≥ 50 个试验。**本轮没有批准它们，也没有批准任何实验。**
- **仍未解决：**初始分类表需 ChatGPT / 负责人审核后冻结；E3 的"设计上可恢复"表未编制；GATED-SPAWN 的实现正确性只能在台架编写与 Stage 1 执行时检验；盲性要求的实现；janitor 之外无自动清理层；其余设计层待决分歧（见第 7 节）不变。
- **NOT TESTED：**E1-A…D、E2-A/B/C/V/R、E3-0/A/B/C 全部 **DESIGN ONLY / NOT TESTED**；GATED-SPAWN 协议、所有候选机制、分类表的正确性、`e1_provability_table_v1.json`（尚未生成）、G3～G6、真实 D1、非 root 环境、其它内核 / Python 版本、cgroup v2、proc connector。
- **Grok：**GROK CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED（不变）。
- **完整性核对：**见提交前后核对输出（汇报）：仅授权范围内的文档；冻结 R3 / 决策记录 / 冻结记录哈希不变；`D1_CODE_SHA256SUMS` 10/10；CPU-001 / CPU-002 代码、证据、报告不变；ERRATA-001 的四项成果未被破坏（仅带标记的最小修订）；新增文件未被 `.gitignore` 忽略；推送后用远端文件树复核；远端 HEAD = 报告的提交。

## 13. 下一条唯一研发指令（ERRATA-002 后）

提交 ERRATA-002 给 ChatGPT 审核，等待项目负责人**单独**决定是否授权 Stage 1。不要自动开始 Stage 1、Stage 2 或 Stage 3。
