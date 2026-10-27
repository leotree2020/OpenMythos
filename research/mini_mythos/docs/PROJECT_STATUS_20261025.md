# Mini-Mythos / OpenMythos — 全项目研发进度（2026-10-25 更新版）

## D1 CPU-003 E1-A 预注册与台架检查点（2026-10-27；本文件最新阶段进度，优先于下方 CPU-003 设计勘误-002 检查点）

F3B-D1-A-CPU-003-E1A-PREP-001（仅预注册与台架实现，不执行）：E1-A 机器可读预注册 `a_predicate_003/prereg/e1_provability_table_v1.json` 已冻结并先于台架单独提交（`b2aec0f`；任何台架提交前做了两次仅限预注册的更正 `c02f201`、`f9d3cd8`；最终 SHA-256 `e6b7ca5c88de81dff01340c769bf409105cd2b91bf581987d710ca6c0280ec39`）；E1-A CPU 台架（GATED-SPAWN、独立谱系账本、fail-closed janitor、插桩、证据与清理检查）、测试与独立真值代码已编写；静态审计 0 违规；**测试与台架均未运行，E1-A 为 EXPERIMENT NOT TESTED**；E1-B/C/D 未冻结。

**状态：**ChatGPT 静态审查 PENDING；Grok 状态不变（已完成，原始报告未入库）。下一条唯一指令：把预注册、台架、`git diff` 与 `STATIC_REVIEW.md` 提交 ChatGPT 静态审查；首次受控 CPU 运行须由负责人**另行**授权（运行器还需 `AUTHORIZATION_E1A_RUN.json`）。R3 SPEC FROZEN；真实 D1 NOT AUTHORIZED；NO A-B WINNER。

## D1 CPU-003 设计勘误-002 检查点（2026-10-27；本文件最新阶段进度，优先于下方 CPU-003 设计勘误检查点）

F3B-D1-A-CPU-003-DESIGN-ERRATA-002：仅文档。(1) 歧义负例按候选机制预先分类（PROVABLE / UNPROVABLE / BENCH_UNVERIFIABLE，执行前冻结）；(2) Janitor 登记持久化竞态——GATED-SPAWN 创建—登记—释放协议，剩余风险 R1–R7 如实列出。三项实验仍 DESIGN ONLY / NOT TESTED；不选方案；建议阈值（0% / 5% / ≥ 50）未被批准。

**状态：**ChatGPT 审核 PENDING；Grok 状态不变（已完成，原始报告未入库）。下一条唯一指令：提交 ERRATA-002 给 ChatGPT 审核，等待负责人单独决定是否授权 Stage 1。

## D1 CPU-003 设计勘误检查点（2026-10-27；本文件最新阶段进度，优先于下方 CPU-003 设计检查点）

F3B-D1-A-CPU-003-DESIGN-ERRATA-001：仅文档。关闭 ChatGPT 审核要求的四项执行前勘误（`UNKNOWN` 率验收、独立真值、清理机制、机制状态与实验判定分层）。**Grok 状态更新为 GROK CROSS-REVIEW COMPLETED — USER-PROVIDED SUMMARY / ORIGINAL REPORT NOT ARCHIVED**（历史块中的 DEFERRED 不改）。三项实验仍 DESIGN ONLY / NOT TESTED；不选方案；冻结 R3 与真实 D1 状态不变。

**状态：**ChatGPT 最终审核 PENDING。下一条唯一指令：提交勘误供 ChatGPT 最终审核；通过后等待负责人单独批准 Stage 1（E1）。

## D1 CPU-003 安全监督器设计检查点（2026-10-27；本文件最新阶段进度，优先于下方 CPU-002 检查点）

F3B-D1-A-CPU-003：仅文档。为未来 R3 修订评审制定三个最小 CPU 实验的设计与预注册判据（E1 归属 / E2 唯一回收者 / E3 崩溃恢复），并整理候选架构、依赖与待决分歧。未执行任何实验；三项均 DESIGN ONLY / NOT TESTED；不选方案；冻结 R3 与真实 D1 状态不变。

**状态：**ChatGPT 审核 PENDING；GROK DEFERRED（至 2026-10-30）。下一条唯一指令：提交设计计划供 ChatGPT 独立审核，再由负责人决定是否授权执行三个最小 CPU 实验。

## D1 CPU-002 最小争议实验检查点（2026-10-27；本文件最新阶段进度，优先于下方 CPU-001 检查点）

F3B-D1-A-CPU-002：E1/E2/E3 完成（430 次运行，判据预注册）。归属安全：原臂在前提被违反时不安全，严格变体以 `UNKNOWN` 换安全；CA 与 Popen 混用会静默得到 returncode 0；CB 遗漏 T5 会滞留僵尸 / pid 但可完全恢复。无明确 A/B 优劣；冻结 R3 未改、未选方案、G3～G6 NOT TESTED、真实 D1 NOT AUTHORIZED。

**状态：**ChatGPT 审核 PENDING；GROK DEFERRED（至 2026-10-30）。下一条唯一指令：等待 ChatGPT 审核；之后由负责人决定是否进入 R3 修订评审或仲裁实验。

## D1 R3-A CPU 受控对照实验检查点（2026-10-27；本文件最新阶段进度，优先于下方 A 判定提案修订检查点）

F3B-D1-A-CPU-001：B0 / CA / CB 三臂最小 CPU 受控实验完成（1860 次运行，独立真值）。B0 复现 G1/G2 缺陷；CA、CB 在授权矩阵上均 365/365 PASS，判定相同，**无明确优劣**；未运行 T-12/T-13/T-15/T-16 及仲裁实验。冻结 R3 未改、未选定方案、G3～G6 NOT TESTED、真实 D1 NOT AUTHORIZED。

**状态：**ChatGPT 审核 PENDING；Grok DEFERRED。下一条唯一指令：等待 ChatGPT 独立审核与 Grok 交叉审核，再由项目负责人决定是否进入最小争议实验及 R3 修订评审。

## D1 A 判定提案修订检查点（2026-10-27；本文件最新阶段进度，优先于下方 G1/G2 审核后处理检查点）

F3B-D1-A-PREDICATE-PROPOSAL-REVIEW-002：修订 A 判定提案与 CPU 测试计划草稿（基准 `cc474f5`）——三态 ALIVE/EXITED/UNKNOWN（RV-01）、跨会话后代归属（RV-02）、指纹 TOCTOU 与 pidfd 评估（RV-03）、子收割者拆成行为维度与策略维度（RV-04）。仅文档；新增 / 改写用例 NOT TESTED；未实施、未运行测试、G3～G6 NOT TESTED。

**状态：**R3 SPEC FROZEN 不变（实现 NOT TESTED，真实 D1 NOT AUTHORIZED）；方案选择 PENDING；ChatGPT 对修订 PENDING；Grok DEFERRED。下一条唯一指令：等待 ChatGPT 与 Grok 交叉审核，并由负责人单独批准候选 CPU 对照实验。

## D1 G1/G2 审核后处理检查点（2026-10-27；本文件最新阶段进度，优先于下方 G1/G2 CPU 实验检查点）

F3B-D1-G1G2-REVIEW-001：保留 G1 = FAIL、G2 = FAIL 的原始证据；起草 R3 存活目标判定 A 的修订提案（方案 A：先 `waitpid(pid, WNOHANG)` 回收并保存退出状态再求值；方案 B：`waitid(P_PID, WNOWAIT)` 非消耗式观察、回收推迟到 T5；共同部分：会话号 + 指纹、`/proc` 状态、子收割者前提、T5 去掉 `waitpid(-1)`、SIGKILL 前复核）与最小受控 CPU 测试计划（基线 / A / B 三臂，T-01…T-11）。提案与计划均为草稿，未应用、未授权执行；冻结 R3 与决策记录未改；G3～G6 NOT TESTED。

**状态：**R3 SPEC FROZEN 不变（实现 NOT TESTED，真实 D1 NOT AUTHORIZED）；ChatGPT 对提案 PENDING；Grok DEFERRED。下一条唯一指令：等待项目负责人批准修订方向及后续最小 CPU 实验，再进入实施。

## D1 G1/G2 CPU 实验检查点（2026-10-27；本文件最新阶段进度，优先于下方 R3 规范冻结检查点）

F3B-D1-G1G2-CPU-001：在 Linux microVM（内核 6.18.44，Python 3.13.16）上用真实子进程（6 个用例 × 5 次重复）验证 R3 §11.1(d) 的存活目标判定 A，对照 `waitid(WNOWAIT)` 与 `/proc` 两个独立观察手段。结果：工具 PASS；**G1 规则 FAIL**（G1-02：已退出未回收时 A 在 2/3 读法下为真）；**G2 规则 FAIL**（G2-01：`killpg(pgid,0)` 对僵尸组仍成功；G2-02：宽限点错误建议 SIGKILL）；G1-01、G1-03、G2-03 PASS。冻结 R3、决策记录、v1/R1/R2、冻结代码未改；残留进程为空。修订建议（先 `waitpid(WNOHANG)` 再求值，或用非消耗式 `waitid`、忽略僵尸）仅作建议，未应用。

**状态：**G3～G6 NOT TESTED、未启动；R3 SPEC FROZEN 状态不变，实现 NOT TESTED，真实 D1 NOT AUTHORIZED；Grok DEFERRED。下一条唯一指令：等待 ChatGPT 对 G1/G2 CPU 实验结果进行独立审核。

## D1 R3 规范冻结检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 边界勘误检查点）

F3B-D1-R3-SPEC-FREEZE-001：ChatGPT 独立审核 `R3 DOCUMENT ACCEPTANCE PASS / READY FOR SPEC FREEZE` 后，冻结 R3 规范（SHA-256 `66a65614…42c5`）与负责人决策记录（SHA-256 `6209602e…6319`）的字节版本，新增冻结记录与检查点；冻结分支 `d1-r3-spec-freeze-20261026`，Git 基准 `79273d127548e2462026c2ae000dc2499798f5bd`。R3-D01…D11 已批准；D07 唯一方案 X（τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s）；17 节点、43 边、无环；冻结清单 10/10；v1/R1/R2 不变。登记 6 项后续 CPU 测试门禁（`waitpid` 与存活目标 A、已退出未回收不得误升级、SIGTERM 提前退出与回收慢、ESRCH/EPERM 记录、进程生命周期、UNPROVABLE 与 FAIL 并存优先级），均 NOT TESTED。

**正式状态：`R3 SPEC FROZEN / IMPLEMENTATION NOT TESTED / REAL D1 NOT AUTHORIZED`。**新脚本未编写；真实 D1 / 数据下载 / 正式 Tokenizer 拟合未授权；第一个合成 CPU 实验需单独授权；Grok DEFERRED。下一条唯一指令：等待单独授权后，启动第一个合成数据 CPU 正确性实验。

## D1 R3 边界勘误检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 最终勘误检查点）

F3B-D1-R3-ERRATA-EDGE-002：仅文档，三个边界规则，不改变任何已批准决策或参数，不新增事件。EDGE-01：T3 先检查存活目标判定 A，A 为假则提前确认且不发 SIGKILL，A 为真且宽限用尽才升级；KILL 尝试时刻（成功或失败）即 `t_kill_bt_ns`，失败记真实 errno。EDGE-02：升级条件只看对 A 的观察，回收耗时不参与；记录无效 → BLOCKED，记录内部矛盾 → FAIL `REAP_RECORD_FORGED`，记录真实自洽但协议未遵守或无法确认 → BLOCKED（`TERMINATION_NOT_ESCALATED` 等），并给出 8 个例子。EDGE-03：`close.result` 只表示预算结果；预算 `UNPROVABLE` 不覆盖已证实的 `FAIL`（FAIL 高于 BLOCKED），所有原因保留，预算不可证明则整体验收不能通过；负例为数据完整性 FAIL + 账本 UNPROVABLE。决策记录与原草案字节不变；17 节点、43 边、无环；冻结清单 10/10。勘误前基准 `cd0285fb22ab7e66dc3979face9f5f095ed077b9`。

**状态：`R3 APPROVED CANDIDATE / EDGE ERRATA SELF-CHECK / PENDING CHATGPT FINAL VERIFICATION`**；不是 R3 FROZEN、不是 REAL D1 PASS、不是运行授权。新机制全部 NOT TESTED；真实 D1 / 数据下载 / 正式 Tokenizer 拟合 / 新脚本开发 / 第一个合成 CPU 实验各需单独授权；Grok 交叉复审 DEFERRED / PENDING。下一条唯一指令：等待 ChatGPT 对边界勘误作最终确认，再执行 R3 正式冻结。

## D1 R3 最终勘误检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 负责人决策与已批准候选规范检查点）

F3B-D1-R3-FINAL-ERRATA-001：仅文档，两处勘误，不改变任何已批准决策或参数。ERRATA-01：候选规范 §11.1(d) 删除「`terminate_begin` 必然 `BLOCKED(budget_exceeded)`」的旧断言，新增终止原因与预算结果对照（`deadline` / `interrupt` / `supervisor_abort` / 回收未确认）；ERRATA-02：`reap_done` 增加必需字段 `kill_overhead_ns`，`t_kill_bt_ns` 未发 SIGKILL 时为 JSON `null`，并给出验收核对与 FAIL / BLOCKED 规则及伪造 SIGKILL 时间的判定。决策记录与原草案字节不变；17 节点、`ref` 31 / `rec` 9 / `sub` 3 共 43 边，无环；冻结清单 10/10。勘误前基准 `21fb57331866b6b0b1db7b24b5e416a68f20f84c`。

**状态：`R3 APPROVED CANDIDATE / ERRATA SELF-CHECK PASS / PENDING CHATGPT FINAL VERIFICATION`**；不是 R3 FROZEN、不是 REAL D1 PASS、不是运行授权。新机制全部 NOT TESTED；真实 D1 / 数据下载 / 正式 Tokenizer 拟合 / 新脚本开发 / 第一个合成 CPU 实验各需单独授权；Grok 交叉复审 DEFERRED / PENDING。下一条唯一指令：等待 ChatGPT 复核这两处勘误，通过后进入 R3 规范正式冻结。

## D1 R3 负责人决策与已批准候选规范检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 最终一致性修复检查点）

F3B-D1-R3-OWNER-DECISION-001：项目负责人于 2026-10-26（Asia/Tokyo）批准 R3-D01…D11 按推荐方案执行，D07 选方案 X（30 分钟 `open`→`close`；K3 / K4 在 `close` 后远端固定；初始验收值 τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s，调整须有审批与变更记录）。新增负责人决策记录、已批准候选规范（执行条款只含方案 X，选项 B / Y / Z 仅作历史说明）和独立检查点（登记两份主文件 SHA-256、源基准 `4c1d29d9e01c6df2d3b5e796181f728cc3cb88ed`）。分支 `d1-r3-approved-candidate-20261026`；原 R3 草案及历史失败 / 修订记录原样保留。依赖图重新核算：17 节点、`ref` 31 / `rec` 9 / `sub` 3，共 43 边，无环。

**状态：`OWNER APPROVED CANDIDATE / PENDING FINAL DOCUMENT VERIFICATION`**；不是 R3 FROZEN、不是 REAL D1 PASS、不是运行授权。冻结文件与 v1/R1/R2 未改。真实 D1 / 数据下载 / 正式 Tokenizer 拟合 / 新脚本开发 / 第一个合成 CPU 实验各需单独授权；新机制全部 NOT TESTED；D2/D3 NOT TESTED；Grok 交叉复审 DEFERRED / PENDING。下一条唯一指令：等待 ChatGPT 独立核对正式 R3 候选规范和批准记录；通过后才能正式冻结 R3。

## D1 真实执行前规范 R3 最终一致性修复检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 第四轮收口检查点）

修订基准 `2ad41913ed08598f1aecfad2575a4f3a6bf51c90`；分支 `d1-pre-real-spec-r3-20261026`。F3B-D1-SPEC-R3-FINAL-005：仅文档，保留第四轮已通过的设计，修三处局部缺口。FINAL-01：账本里 `terminate_signal`、`reap_done` 只在 `TERMINATING` 合法；F1 拆为 F1a（监督器收到信号）、F1b（仅阶段进程被外部信号杀死、无存活后代，直接 `stage_end{failed}`）、F1c（发现需主动终止的后代才进入 `TERMINATING`）。FINAL-02：`--postmortem` 不向原账本与事件日志追加任何行；`postmortem.json` 是独立叶子证据；后验 A8 独立成文件，只引用现存工件、缺失节点标 `absent`，不伪造 `manifest_written`(A8)，该例外同时写入注册表与验收规范；缺 `close` / `run_aborted` / K3 / K4 时始终 `NOT_ACCEPTED`，不低于 `BLOCKED(budget_unprovable)`。FINAL-03：F1–F3 序列采用选项 X；选项 Y 的失败路径为 `stage_end` → `pin_phase` → K3 → K4' → `close`，不得复用「先 `close` 后 pin」。依赖图重新计算：17 节点、`ref` 31 / `rec` 9 / `sub` 3，共 43 边，无环；边列表未改。

**状态：`R3 DRAFT / PENDING OWNER DECISION`**；自检 `R3 FINAL-005 DOCUMENT SELF-CHECK PASS / PENDING CHATGPT REVIEW`，不是 R3 FROZEN、不是 REAL D1 PASS、不是 OWNER APPROVED。R3-D01…D11 全部 PENDING OWNER DECISION。冻结文件与 v1/R1/R2 未改；未下载、未拟合、未运行 D1、无 GPU。真实 D1 NOT TESTED / NOT AUTHORIZED；新脚本未编写；D2/D3 NOT TESTED；Grok 交叉复审 PENDING。下一条唯一指令：等待 ChatGPT 对最终一致性修复（FINAL-005）后的 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 真实执行前规范 R3 第四轮收口检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 第三轮修订检查点）

修订基准 `ca40fb74d8fea2c17a1a5116ba8939b17ce2e847`；分支 `d1-pre-real-spec-r3-20261026`。F3B-D1-SPEC-R3-CLOSURE-004：仅文档，对 ChatGPT 第三轮独立审核发现的四处缺口收口。C04-01：R7.7 是只在中断时触发的门禁，正常运行写 `check_result`(R7.7, `NOT_APPLICABLE`)，不折算为 PASS，状态词写入注册表枚举；C04-02：失败路径使用 `run_aborted` 作为 K3 终点，预算结果（WITHIN_BUDGET / EXCEEDED / UNPROVABLE）、运行状态（COMPLETED / ABORTED）与实验最终状态相互独立，监督器只写 BLOCKED / FAIL 与事实，给出 S4 中断、S5 超时、S5 残留进程、监督器异常退出四条流程；C04-03：预算测试 (g) 拆为耗时数值与账本有效性；C04-04：R6.6 由验收脚本自己重新核对（读后快照与闸门结论先于 K3、`line_count` 一致、K3 经远端内容验证），缺证据一律 `NOT_ACCEPTED`。依赖图重新计算：17 节点、`ref` 31 / `rec` 9 / `sub` 3，共 43 边，无环。

**状态：`R3 DRAFT / PENDING OWNER DECISION`**；自检 `R3 CLOSURE-004 DOCUMENT SELF-CHECK PASS / PENDING CHATGPT REVIEW`，不是 R3 FROZEN、不是 REAL D1 PASS、不是 OWNER APPROVED。R3-D01…D11 全部 PENDING OWNER DECISION。冻结文件与 v1/R1/R2 未改；未下载、未拟合、未运行 D1、无 GPU。真实 D1 NOT TESTED / NOT AUTHORIZED；新脚本未编写；D2/D3 NOT TESTED；Grok 交叉复审 PENDING。下一条唯一指令：等待 ChatGPT 对第四轮（收口）R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 真实执行前规范 R3 第三轮修订检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 修订稿检查点）

修订基准 `eeea55269df485d3e6305a82a3c478ef141a2788`；分支 `d1-pre-real-spec-r3-20261026`。F3B-D1-SPEC-R3-REVIEW-003：仅文档，对 ChatGPT Work 判 FAIL 的修订 2 做最小纠正。FIX-01 预算账本的状态转换、监督器与进程组终止/回收协议、`close` 的写入与失败处理，以及 K3/K4 与 30 分钟预算的两个无循环收尾方案（选项 X / Y，待裁决）；FIX-02 远端 pin 的内容验证程序 RV（取回对象、读文件、核对摘要/规范序列化/前缀/祖先关系，带外副本）；FIX-03 K3 改以 `read_phase_closed` 为终点，R6 最终读后哈希与闸门结论先于 K3；FIX-04 摘要标签与冻结接口的对照表（冻结键保持裸格式，不改冻结代码）；FIX-05 唯一事件注册表；FIX-06 I4 统一措辞；FIX-07 统一审计输出 Schema（`usage_declaration` 在 Envelope）；FIX-08 依赖图由正式边列表重新构造：17 节点、`ref` 31 边、`rec` 9 边、`sub` 3 边，无环，并更正修订 2 记录的 29 边。

**状态：`R3 DRAFT / PENDING OWNER DECISION`**（文档自检 PASS 不是 R3 FROZEN、不是 REAL D1 PASS、不是 OWNER APPROVED）。R3-D01…D11 全部 PENDING OWNER DECISION。冻结文件与 v1/R1/R2 未改；未下载、未拟合、未运行 D1、无 GPU。真实 D1 NOT TESTED / NOT AUTHORIZED；新脚本未编写；D2/D3 NOT TESTED；Grok 交叉复审 PENDING。下一条唯一指令：等待 ChatGPT 对第三轮 R3 修订稿进行独立审核，再由项目负责人决定是否批准 R3。

## D1 真实执行前规范 R3 修订稿检查点（2026-10-26；本文件最新阶段进度，优先于下方 R3 草案检查点）

修订基准 `94601916bc1fd0faa33b9f819b3a0d8cc7d61dc5`；分支 `d1-pre-real-spec-r3-20261026`。F3B-D1-SPEC-R3-REVIEW-002：仅文档，原地修订 R3 草案并新增第 11（细则）、12（逐项修订记录）节。八项修订：D07 预算账本（`CLOCK_BOOTTIME` + `boot_id` + 外层监督器，不用 `seq` 计时，重启/时钟异常 → BLOCKED）；S6 哈希链仅作完整性并外部固定关键前缀 K0–K4 与信任边界；D03 前后哈希只证明两个检查时刻（加 `ctime_ns`，列可选控制）；I4 缺席见证的受控范围与局限（含 Xet 缓存）；D06 区分 LFS SHA-256 / Git blob SHA-1 / Xet（更正首版对 LFS `blob_id` 的错误用法，元数据不足默认 BLOCKED）；D08 test 审计只限完整性与统计；A1–A8 引用层级与前缀哈希已自检无环；11 项裁决保留为待批准决策记录。

**状态：`R3 DRAFT / PENDING OWNER DECISION`**（不是 FROZEN，不是 PASS）。冻结文件与 v1/R1/R2 未改；未下载、未拟合、未运行 D1、无 GPU。真实 D1 NOT TESTED / NOT AUTHORIZED；新脚本（记录器、预算账本与监督器、获取、拟合、审计、清单、验收、固定工具）未编写；D2/D3 NOT TESTED；Grok 交叉复审 PENDING。下一条唯一指令：等待 ChatGPT 审核 R3 修订稿及项目负责人正式批准。

## D1 真实执行前规范 R3 草案检查点（2026-10-26；本文件最新阶段进度，优先于下方 Closeout 段）

基准 `97d0faf2982f4122941d2299a23cab6ab2ba04a3`；分支 `d1-pre-real-spec-r3-20261026`。R3 草案（`F3B_D1_PRE_REAL_SPEC_R3_DRAFT.md`）消解/记录规范冲突：S1（下载后哈希 vs 未被打开）、S2（T7 扫描 val/test vs R6/T1）、R6 粒度、R7 Token 计数、中断行为、T1 事件日志、30 分钟预算，另发现离线切换时机、无 LFS `sha256`、身份标签可核对性三项；给出分阶段规范、验收矩阵、单向哈希清单、独立验收方案和 11 项待裁决事项（均 PROPOSED / NOT APPROVED）。24/24 原文引用逐字核对；冻结文件与 v1/R1/R2 未改。

**状态：`DRAFT / PENDING CHATGPT REVIEW`**。真实 D1 NOT TESTED / NOT AUTHORIZED；R6 剩余、R7、T1–T6、数据获取 NOT TESTED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 复审并由项目负责人裁决 R3-D01…D11。

## D1 冻结后 CPU 回归 Closeout 检查点（2026-10-26；本文件最新阶段进度，优先于下方哨兵测试修正段）

Codespaces Python 3.13.8 冻结后合成回归：日志提交 `1298619e163af6257d206134e5ed031e0082947f`，日志 SHA-256 `be1bff0493a4da59c71b962188ac1bc3a5766b6caa26a419ea23a0ceae6fac1e`（重算一致）；56 个测试名与源码一一对应，**56 PASS、0 SKIP、0 FAIL、0 ERROR，50.656 s，`unittest_exit: 0`**；`test_identity_labels`、`test_real_mode_pipeline` 通过（合成，非真实 D1）。本会话在该提交上独立确认：冻结清单 10/10 OK；配置 `status = FROZEN`、哈希 `0d35dc21…`；Reader/Verifier/Driver/配置/`d1_env_manifest.py`/`d1_selftest_data.py`/依赖与 README/Codespaces 环境证据相对冻结提交 `9e257788` 无 diff；测试文件仅哨兵断言一行。观察：Codespaces 日志头部不含 `git status` 与清单校验输出（非阻断）。

**状态：`READY FOR CLOSEOUT / CROSS-REVIEW PENDING`**（Grok 对最终哨兵修复差异的交叉审核尚未取得）。真实 D1 NOT TESTED / NOT AUTHORIZED；R6 剩余、R7、T1–T6、数据获取 NOT TESTED；D2/D3 NOT TESTED。**下一条唯一指令**：取得 Grok 交叉审核后将配置与环境准备范围标记 CLOSED。

## D1 冻结后哨兵测试修正检查点（2026-10-26；本文件最新阶段进度，优先于下方最终配置冻结段）

冻结提交 `9e257788c0510d5e263d5256d4bd3cebebdb8057` 与其原始失败日志保留。根因：`test_identity_labels` 的冻结前哨兵断言 `status != "FROZEN"` 在配置冻结后必然失败，不是 Reader/Verifier/Driver 缺陷。修复（分支 `d1-final-freeze-sentinel-fix-20261026`）：测试一行改为 `== "FROZEN"`；`D1_ENV_FREEZE.md` 状态描述与事实同步（配置 FROZEN、原生证据 PASS、冻结已授权、真实 D1 仍 NOT TESTED / NOT AUTHORIZED）；清单只有这两项变化，10/10 OK，配置哈希不变。沙箱 Python 3.13.16：精确测试 PASS；完整 56 项 `OK (skipped=1)`（real-mode 版本门禁）。**Codespaces Python 3.13.8 回归：NOT TESTED（PENDING CODESPACES VALIDATION）**，期望 56 PASS / 0 SKIP / 0 FAIL / 0 ERROR，需项目负责人回传。

**状态：`SENTINEL FIX CANDIDATE / FINAL FREEZE REGRESSION ACCEPTANCE = PENDING CODESPACES VALIDATION`**。真实 D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 Codespaces 回归结果并交叉审核最终最小差异。

## D1 最终配置冻结检查点（2026-10-26；本文件最新阶段进度，优先于下方原生环境证据验收段）

授权 `APPROVED — Final Configuration Freeze Only`。冻结前 SHA `ebb45680f7391c3fac975b7cdbf29d1a7a94ed67`；冻结分支 `d1-final-config-freeze-20261026`。配置 `status` = `FROZEN`（只改该字段与一段环境状态说明文字，结构化比较其余全部相同）；`D1_CODE_SHA256SUMS` 10/10 OK（仅配置一行变化）；读取器/验证器/驱动器/测试源码/Codespaces 证据与日志/原始提案无 diff。本轮在 Claude 沙箱（Python 3.13.16，**不是** Codespaces）做了一次影响检查：56 项中 54 PASS、1 按设计跳过（real-mode，补丁版本不符）、**1 FAIL**：`test_identity_labels` 的冻结前哨兵断言 `status != "FROZEN"`。未改测试（授权禁止），待项目负责人决定（改测试会改变其 SHA-256，需要重新生成清单并重新验收）。

**状态：`D1 FINAL CONFIG FROZEN / PENDING CHATGPT INDEPENDENT ACCEPTANCE`**。真实 D1 NOT TESTED / NOT AUTHORIZED；R6 剩余、R7、T1–T6、数据获取 NOT TESTED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 独立验收最终冻结提交。

## D1 Codespaces 原生环境证据验收检查点（2026-10-26；本文件最新阶段进度，优先于下方环境适配归档段）

证据提交 `852f30e13ab108311b160c9d1b55c3823dfa9b51`。原生环境证据文件（SHA-256 `e4e05c650e23a4a14b3327ca668d439871ad073747c66c752726d802166ccf1c`）经本会话完整读取、重算哈希并逐项核对，**PASS**：Python 3.13.8、venv `/workspaces/.venvs/openmythos-d1-py3138`、tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0、`pip freeze` 17 个包（无 torch/CUDA）、`pip check` 退出码 0、IMPORT_CHECK PASS、Linux x86_64 / 2 CPU / 7.8 GiB、采集时 HEAD `ef6b51a` 且工作区干净、冻结清单 10/10 OK。此前「执行主机环境 BLOCKED」一项关闭。

**正式状态：** D1 CODE FREEZE PASS；CODESPACES CPU SYNTHETIC REGRESSION 56/56 PASS；NATIVE ENVIRONMENT EVIDENCE PASS；FINAL CONFIG FROZEN **NOT AUTHORIZED**（`status` 未改）；REAL D1 NOT TESTED / NOT AUTHORIZED；R6 剩余部分、R7、T1–T6、数据获取完整性 NOT TESTED；D2/D3 NOT TESTED。

**下一条唯一指令**：等待项目负责人批准最终配置冻结提交。

## D1 环境适配归档与冻结前整理检查点（2026-10-26；本文件最新阶段进度，优先于下方代码冻结验收归档段）

代码冻结验收提交 `0197c21c`；环境适配候选 `2c5986a89b023ff50acb6da6e1b4d068b515ca53`（分支 `d1-codespaces-py3138-validation-20261026`）。ChatGPT 审核与交叉审核均 PASS。Codespaces Python 3.13.8：56 项 CPU 合成回归 56 PASS / 0 SKIP / 0 FAIL（含合成 real-mode 代码路径；日志 `selftest_py3138.txt` 原样保留）；固定依赖 tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0。`D1_ENV_FREEZE.md` 已更新（版本、依赖、证据状态，区分「环境适配 PASS」与「真实 D1 NOT TESTED」），`D1_CODE_SHA256SUMS` 重新生成（10 项核验）。原生环境快照尚未归档：**BLOCKED**，待项目负责人在 Codespaces 回传（命令在 `NATIVE_ENV_EVIDENCE_COLLECTION.md`）。R6 读取前、R7、T1–T6、数据获取 NOT TESTED；真实 D1 NOT TESTED / NOT AUTHORIZED；`status` 仍为 `FROZEN_CANDIDATE__…`。

**下一条唯一指令**：最终配置冻结审核。

## D1 代码冻结验收归档检查点（2026-10-26；本文件最新阶段进度，优先于下方 C2b 段）

`0197c21ca38130e66d804961b85a15ee39634b26`：ChatGPT Work 独立 C2b 代码冻结验收 **PASS**（据项目负责人转述）；56 项 CPU 合成测试仅为日志核验，**未在独立环境重新执行**。D1 真实实验 NOT TESTED / NOT AUTHORIZED；R6 读取前部分、R7、T1–T6、数据获取完整性 NOT TESTED；获取与 Tokenizer 拟合脚本未编写；配置 `status` 仍为 `FROZEN_CANDIDATE…`。执行环境只读核查：指定 Codespaces 无法访问（`gh` 令牌无效、`gh codespace list` HTTP 403、仅有 Claude 云沙箱环境）→ **BLOCKED**；Claude 沙箱不作为执行环境；候选版本（Python 3.13.16、tokenizers 0.23.3、pyarrow 26.0.0、huggingface_hub 2.2.0）未改。已验收文件的 blob/SHA-256 见 `F3B_D1_CODE_FREEZE_ACCEPTANCE_ARCHIVE_20261026.md`。

**状态：`D1 CODE FREEZE ACCEPTED (C2b) / D1 REAL EXPERIMENT NOT TESTED, NOT AUTHORIZED / EXECUTION ENVIRONMENT BLOCKED`**。D2/D3 NOT TESTED。**下一条唯一指令**：项目负责人在 Codespaces 内执行只读环境命令并回传。

## D1 代码冻结候选 C2b 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C2a 段）

基准 `796cc6138caaedf8a45d9abd12554ef62235e77d`。C2b 两项：CR 的故障/对照读取器各自退出码与状态保留，整体按 FAIL > BLOCKED > PASS 聚合（`cr_reader_verdict` + `aggregate`）；`verifier_verdict()` 对非字符串 verdict 安全返回 FAIL。新增测试在 C2a 上失败（CR1/CR2 误记 BLOCKED；`TypeError: unhashable type`），56 项合成回归 OK。读取器、验证器、冻结配置、历史文档未改。

**状态：`D1 CODE FREEZE CANDIDATE C2b / PENDING CHATGPT FINAL ACCEPTANCE`**。仅 CPU 合成数据；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED；执行主机环境 BLOCKED。**下一条唯一指令**：等待 ChatGPT 最终验收。

## D1 代码冻结候选微型勘误 C2a 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C2 段）

基准 `f28f32b6d1514f15ccf680f752f5c414322cab51`。C2a 两项：验证器结果判读区分「文件不存在」与「存在但不可解析」（只有退出码 4 且无文件才 BLOCKED；畸形/未知 verdict/退出码不符为 FAIL）；负例聚合 FAIL 优先于 BLOCKED，每项状态明细与 `counts` 保留。4 项相关测试在 C2 代码上失败，52 项合成自测 OK。读取器、验证器、冻结配置未改。

**状态：`D1 CODE FREEZE CANDIDATE C2a / PENDING CHATGPT FINAL CODE REVIEW`**。仅 CPU 合成数据；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 最终代码复审。

## D1 代码冻结候选勘误 C2 检查点（2026-10-26；本文件最新阶段进度，优先于下方 C1 段）

基准 `3775dc333577094d30297d3e28f9aa8d5d40039c`。C2 只做三项最小门禁修订：读取器退出码 4 → BLOCKED（驱动器退出码 PASS 0 / FAIL 1 / BLOCKED 4）；30 分钟硬上限设为代码常量，real 模式禁止覆盖、selftest 只能缩短；验证器异常退出、结果缺失/畸形/与退出码不符以及驱动器自身异常都写入决定文件为 FAIL 或 BLOCKED。12 项新回归测试（C1 代码上 11 项失败），全量 49 项合成自测 OK。只读环境盘点：沙箱满足候选固定值，**执行主机 NOT VERIFIED**，冻结配置未改。详见 `F3B_D1_CODE_FREEZE_C2_ERRATA_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE C2 / PENDING CHATGPT FINAL CODE REVIEW`**。仅 CPU 合成数据；未下载、未拟合、未训练、无 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 最终代码复审；授权前不得运行 D1。

## D1 代码冻结候选勘误 C1 检查点（2026-10-26；本文件最新阶段进度，优先于下方代码冻结准备段）

审核基准 `090b6191f7558a43462691bb4fa9afa4b56fed9b`：`CODE FREEZE CANDIDATE FAIL`（代码完整性）。已修订：（1）`verify_cr` 重算故障/control trace 的块哈希、链、块号、总数、`stream_token_pos`、EOF tail 元数据；（2）独立构造 CR1/CR2/CR3 预期的单变异流与整窗口来源顺序并全量比对；（3）对抗性回归测试（单块哈希、tail_sha256、来源顺序、control 篡改；37 项合成自测 OK，旧验证器上 6 项失败）；（4）`verify_clean` 独立重算 P1–P5；（5）real 模式与正式 D1 身份分离；（6）Python 完整补丁版本候选固定（**执行主机未核实**）；（7）30 分钟硬超时 → BLOCKED、保留证据、不重试；（8）R6/R7/T1–T6/数据获取完整性标 NOT TESTED，流水线不输出总体 D1 PASS。详见 `F3B_D1_CODE_FREEZE_C1_ERRATA_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE C1 / PENDING CHATGPT RE-REVIEW`**。仅 CPU 合成数据；未下载、未拟合、未训练、无 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得运行 D1。

## D1 执行脚本冻结准备检查点（2026-10-26；本文件最新阶段进度，优先于下方 R2 段）

基准 `8a1700835c619fc1ad579da12713ece612403b8e`。准备了 D1 读取器、独立验证器、LR1–LR9 / CR1–CR3 受控负例脚本、`D1_FROZEN_CONFIG.json`、CPU 环境与依赖冻结说明（`research/mini_mythos/gate3_d1/`）和合成数据自测（`tests/test_d1_selftest.py`，24 项 OK；固定版本 venv 中同样通过，含 `--mode real` 代码路径）。读取器与验证器互不 import、不共享游标校验/来源映射/参照流函数；区分中间 carry 与 EOF tail；来源片段无空洞/无重叠/完全覆盖断言在两套实现中各有一份并被反向测试。详细记录与 12 条需复审的实现决定见 `F3B_D1_CODE_FREEZE_PREP_20261026.md`。

**状态：`D1 CODE FREEZE CANDIDATE / PENDING CHATGPT CODE REVIEW`**。没有下载 Parquet、拟合 Tokenizer、D1 数据实验、模型实例化、训练或 GPU；数据获取与 Tokenizer 拟合脚本尚未编写；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 代码复审；授权前不得运行 D1。

## D1 预飞行 R2 最小修订检查点（2026-10-26；本文件最新阶段进度，优先于下方 R1 段）

基准 `579ffd11ec2dba0b9cbf0eae67d7ce4e26874c19`。R1 复审结论 `PRE-FLIGHT FAIL`。新增 `F3B_D1_FROZEN_EXECUTION_PROPOSAL_R2.md`，仅文档；v1（SHA-256 `a55b2cb7…ba9e`）与 R1（SHA-256 `f92c4e79…1d7a`）原样保留。修订项：（1）CR 负例由可信干净前缀 + 续读 trace 重新核算整个窗口，逐行对照 Token 数量、原始位置与完整内容，续读 trace 不重复历史块，故障注入证据与干净前缀分别保存、不得覆盖；（2）CR3 原始游标先通过全部九步校验，不得关闭加载检查，仅在读取循环内注入 Token 消费偏移，磁盘游标不改；（3）CR3 固定 `δ=+1`，P2 只选 Token 数 ≥ 3 的行，删除 `δ=−1`，预期码恒为 `TOKEN_OFFSET_MISMATCH`（LR1 随之固定为 `+1`，属于消除冲突的最小改动）；（4）P2 搜索合格行序号 [600,900)，找不到记 `BLOCKED(schedule)`，删除「相邻中断点至少相隔 300 行」的错误断言，改以实际 Token 流位置严格递增为判据，P3/P4 搜索起点包含行起点；（5）哈希链零起始块号，`H_{j+1}=SHA256(H_j ‖ block_hash_j)`，32 字节原始摘要拼接，`chain_hash=H_N`。

**状态：`D1 PRE-FLIGHT R2 PROPOSED / PENDING CHATGPT RE-REVIEW`**。没有下载、拟合、模型实例化、训练或 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得执行 D1。

## D1 预飞行 R1 修订检查点（2026-10-26；本文件最新阶段进度，优先于下方 v1 段）

基准 `ab6d8271f30cb49e097f3979e29f42bf0e96d545`。新增 `F3B_D1_FROZEN_EXECUTION_PROPOSAL_R1.md`，仅文档；v1 方案原样保留（SHA-256 `a55b2cb7…ba9e`）。修订项：（1）N1/N2 改为合法游标恢复后读取过程内整行跳过/重复，写明首个受影响来源行、错误码与独立检测条件；（2）负例分 LR（加载拒绝）与 CR（继续读取）两类，分别给出 PASS 判据；（3）游标 `d1_cursor_v2` 增加 Token 内容、来源行身份、合法偏移、EOF、输出前缀与哈希链校验，9 步固定顺序；（4）5 个预先确定、升序的中断点，空 carry 合法；（5）Token 以 uint32 小端序列化，固定块哈希、哈希链初值与尾部核算；（6）冻结 Tokenizer 的编码/解码/特殊 Token/自动添加/padding/truncation/后处理；（7）勘误：v1 的 832 参数差额是把 13 个 `torch.nn.LayerNorm`（带偏置）误按 RMSNorm 计算，静态公式 `P(V)=206,976+320V`，V=128 处等于归档断言 247,936，适用前提见 R1 第 10 节；V=4096 处仍是 DERIVED，D2 须实测。

**状态：`D1 PRE-FLIGHT R1 PROPOSED / PENDING CHATGPT RE-REVIEW`**。没有下载、拟合、模型实例化、训练或 GPU；D1 NOT TESTED / NOT AUTHORIZED；D2/D3 NOT TESTED。Work 复审原文不在仓库中，R1 依据项目负责人转达的 7 条修订项。**下一条唯一指令**：等待 ChatGPT 复审；授权前不得执行 D1。

## D1 预飞行方案检查点（2026-10-26；本文件最新阶段进度）

**交接**：项目负责人决定由 Claude Code 接替 Grok 做主要研发，ChatGPT 继续独立审核；下文各处「Claude Code 暂缓接管」已被取代，历史段落保留不改。

**本阶段产物**：`F3B_D1_FROZEN_EXECUTION_PROPOSAL.md`，基于 HEAD `326121990cef4064d2c2d6cdc48a0d53da3cab3e`。内容：不可变数据源规则（含固定修订版、Parquet 行索引身份、合格行与文章边界/EOS 规则）、train-only ByteLevel BPE 冻结项（目标 4096，实际词表另测）、单进程游标恢复（A/B 路径、独立参照、块哈希链、覆盖条件）、N1–N5 负例、停止标准、证据布局、依赖与 CPU 资源估算、D2 词表冲突登记、风险与 BLOCKED 清单。

**状态：`D1 PRE-FLIGHT PROPOSED / PENDING CHATGPT REVIEW`**。没有下载、没有 Tokenizer 拟合、没有读取真实数据行、没有实例化或训练模型、没有 GPU。D1 未 PASS、未 CLOSED；D2/D3 NOT TESTED。

**本阶段发现（需要审核）**：（1）上游 `scripts/train.py:287` 令 `ignore_index = tokenizer.pad_id`，而模型默认 `-100`（F3-A 用默认），D2 须显式选择；（2）词表相关参数由源码推为 `320×V`，但按源码手算的 F3-A 总参数为 247,104，与记录的 247,936 差 832，原因未明，因此 D2 参数量只能实测；（3）本沙箱 `huggingface.co` 被代理拒绝，D1 必须在有 HF 访问的环境执行。

**下一条唯一指令**：ChatGPT 审核本方案并经项目负责人明确授权后，才先提交 D1 执行脚本冻结提交；此前不得下载、拟合、训练或启动 GPU。


## F3-B 最新设计审核（2026-10-25；本报告最新阶段进度）

Grok 设计提交 `103344e47184735e03727d062ce81cbae6632e47` 新增五份方案、更新项目地图，没有提交任何新的模型训练代码或模型权重。ChatGPT 阅读五份设计，核对 R1 Gate F/WikiText HF 固定版本、R2 Gate M/N/O/P/Q 文件元数据与本地合成来源身份测试，以及原生 Parcae 嵌入与 LM Head 输入输出尺寸。独立审核文件 `research/mini_mythos/docs/F3B_CHATGPT_DESIGN_REVIEW_AND_D1_FREEZE_GATE_20261025.md`。

**正式状态：`F3-B DESIGN DELIVERABLES PASS/CLOSED`，仅限所要求的五份设计成果；`D1 DRAFT / NOT FROZEN / NOT AUTHORIZED`，D2/D3 `NOT TESTED/NOT AUTHORIZED`，GPU 不授权。** 旧 F3-A 2/2/2 固定输入 CPU AdamW 六步恢复门禁仍保持研究性限定 PASS/CLOSED；不可当成数据流训练/模型能力证明。

建议复用已经验证的 WikiText-2 raw 数据身份 `Salesforce/wikitext` / `wikitext-2-raw-v1` / `b08601e04326c79dfdd32d625aee71d232d685c3`。Grok 初稿仅写通用 config + “version can be pinned”，还缺 **真正冻结 repo+revision/许可说明**，必须在 D1 preflight 固定 train-only BPE 类型与实际词表/特殊 Token/Tokenizer hash、单进程 row/token cursor 与确定比较窗口、无意外重复/遗漏及错 cursor 负例、证据清单和 CPU 停止条件。

**关键 D2 前置冲突**：F3-A 验收时 vocabulary=128、参数=247936；F3-B 研究 BPE 目标 vocabulary≈4096，不能直接给旧模型喂新 Token ID 而仍称参数量相同。D2 另须冻结嵌入、输出 Head、padded_vocab_size 和重算实际参数量，并区分 PAD token ID 与 labels ignore_index=-100。

**下一条唯一指令**：Grok 只读起草 `F3B_D1_FROZEN_EXECUTION_PROPOSAL.md` 并提交审核；**没有授权 CPU D1 读取/Tokenizer 拟合，也没有授权真实文本模型训练或 GPU**。FineWeb-Edu 14 文件身份与双重分片历史 Gate M/N/O/P/Q 限定证据有效，但远端 Parquet 真正逐行读取/真实训练继续 NOT TESTED；官方 Parcae Tokenizer license/identity 保持 BLOCKED。历史脏文件 `gate2_1/TEST_RESULTS.json` 不可覆盖。

## 最终最新研究状态：F3-A 冻结 CPU Train Lifecycle 限定结案

**2026-10-25 最新独立审核优先级最高**：Grok 的 F3-A B1 与 R1 已提供连续训练、文件恢复的固定 6 步等价证据。最后异常检查 commit `dd36b939457a6c6197b0026fe38854c4edd05365` 在不重跑完整训练的条件下，完成 Scheduler 内容错误拒绝、Torch RNG 信任身份比较失败、保持 key 的实际张量 shape mismatch 拒绝；五项文本/脚本 SHA-256 由 ChatGPT 独立重新计算全 MATCH。正式报告：`research/mini_mythos/docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`。

**当前决定：F3-A 研究性原生 Parcae CPU 固定输入 AdamW 六步训练与 Checkpoint/Resume 生命周期 PASS/CLOSED（仅冻结微型范围）**。严禁推论原生 `scripts/train.py`、MuonAdamW、真实 Streaming DataLoader 恢复、真实语言能力/规模训练、GPU 已经通过。异常严格校验位于独立 checked loader，而不是先前运行六步训练的 R1 loader，因此在将来真实训练系统需要明确集成；损坏 RNG 的 `FAIL` 是**正确检测到异常的预期负例**，不是正常训练失败。

**出处风险保持**：最后 `RUN_META.json` 声称 Python 3.10.21、执行命令指定 `/usr/bin/python3.11`，二者不一致，准确运行解释器版本 `NOT VERIFIED`；二进制 `.pt` SHA-256 为 Grok 本地报告，ChatGPT 没有独立重算二进制。旧 `gate2_1/TEST_RESULTS.json` dirty 必须保护，禁止清理。不能更改旧结果隐瞒上述差异。

**下一研发主线（尚未授权运行）**：Grok 只读调查并设计/冻结真实数据加载、Tokenizer、分片/worker 恢复、heldout 质量指标及公平 Transformer 对照的后续阶段 Gate。**正式停止 F3-A 微型实验扩展**，不启动真实数据训练/GPU，不修改 Parcae/AxoNN 源码，保留 Prelude→Recurrent Core→Coda 和独立随机权重战略。

## 最新阶段补记：F3-A-R1 CPU 正常训练与断点恢复（2026-10-25）

**本段是本文件最新阶段状态，优先于下方 F3-A 初次审计与旧时间点快照，不能把老文中的 R1 待执行当成当前事实。** Grok 先提交 F3-A-R1 冻结补充 `8ea2d674404c44f5887fd248ef25a33c1a622727`，随后提交完整 R1 CPU 运行 `14974c8e2a6ad11bea7b45df4242b5acbad3abfe`。维持原 Parcae 2/2/2/AdamW/linear scheduler/fixed input/6 steps。第 1 步 LR=0 不更新、step2–6 更新；Loss 4.96057→2.73600；连续与文件恢复在 step4–6 的模型 SHA、loss、LR、optimizer SHA、scheduler 新建 config、torch/python/numpy RNG SHA 均一致。

ChatGPT 独立复核：R1 四项文本证据 SHA-256 全部 MATCH，提交脚本 SHA-256 独立计算，原生六步学习率与上游数学 6/6 一致；**F3-A 正常训练与断点恢复路径限定 PASS/CLOSED；F3-A 整体 PARTIAL / NOT CLOSED**。原因：实际保存的 scheduler 内容只验证字段存在，未验证错误配置；没有有效格式但错误的 RNG 内容的受控恢复失败例；所谓坏 shape 负例实际上只移除一个 state_dict 键。详见 `research/mini_mythos/docs/F3A_R1_CHATGPT_INDEPENDENT_REVIEW_AND_FINAL_DELTA_GATE_20261025.md`。二进制 checkpoint 的 SHA-256 本次无法通过现有 GitHub 只读二进制接口独立核实，仅验证文件存在、size 与 Git blob SHA。

**当前唯一下一步**：用已有 R1 已提交 Checkpoint，在限定研究目录内完成三个内容级异常恢复/拒绝负例；若需要真实运行仅允许最多一个独立的恢复 step，不重跑整个 6 步训练，不修改上游或架构、不启 GPU、不做规模训练；新证据归档并停在 PENDING CHATGPT REVIEW。完成后推进真实数据训练/数据流恢复的方案审计，避免无限扩展微型探针。

## 最新阶段补记：F3-A 首次 CPU Train Lifecycle 运行（2026-10-25）

**此补记优先于本报告下方早期“未授权/未执行”措辞**。项目负责人已授权 Grok 执行 F3-A。Grok **先冻结** `docs/F3A_FROZEN_CONFIG.md`（commit `34c4414667e939560cae69c0a2dc58fca14f9ef5`），再提交 `gate3_cpu_train/f3a_lifecycle.py` 和 CPU 六步 AdamW 固定输入生命周期实测（commit `3b582c7ac8c4ac7e4473d48ee78e05b5326b8026`）。损失 `4.933872→2.713740`，第 2–6 步权重更新，step4–6 的 A/B Loss/LR/权重哈希相同，四项声明文本 SHA256 经 ChatGPT 独立 MATCH。第 1 步 frozen warmup LR0，权重不变，必须保留该预期与原冻结 STOP 条款矛盾，不得事后掩盖。

**ChatGPT 正式审核结论：F3-A PARTIAL POSITIVE / NOT CLOSED。** `step()` 每步重设 RNG，导致恢复 RNG 未获真实因果验证；Checkpoint 的 step/scheduler 内容没有被加载器验收；未逐步对比 optimizer state、三类 RNG 和训练位置；错误 Checkpoint 负例仅改字典并未测试真实 loader 拒绝。详见 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md`。二进制 checkpoint `f3a_step3.pt` 已在 GitHub 追踪（size=3,079,307 bytes；Git blob SHA `b351dacfa9aac7be759ade893b249ebb9485d5b8`）；报告的 SHA-256 未能从当前只读二进制连接器独立重算，需如实标记。

**下一步**：仅允许冻结 F3-A-R1 的最小恢复验证补充、隔离 CPU 验收及原始证据归档，严禁启动新的采样/架构实验、GPU、规模训练、修改上游 Parcae。完成后 `PENDING CHATGPT REVIEW` 停止。已关闭的 F2-B/C/D 与 F2-E E1–E5 维持原结果，E6 仍 INCONCLUSIVE。Claude Code 暂不接管；Grok 主开发，ChatGPT 审核。

**状态性质**：研究项目总体进度与治理检查点，不是新模型实验。  
**最新实测 Git 统计基线**：研究分支 `mini-mythos-p1c-gate22c-readiness` 的 `ee1b3c8564f4cc868e73efd58e4ddc42c35e4f78`，完整 Git recursive tree（`truncated=false`），**481 个 tracked 文件、154 个 Python 文件、3,050,894 bytes**。本文及后续 Git 文档更新会推进 HEAD，新的会话必须重新验证。  
**上一次历史基线**：`0853051ec1791adbc54e4e8c90f2be146a0ff092`，444 文件、153 Python、2,803,100 bytes；中间 `2ceb08b1db34871104a45e27e5ec2f7bc81e0ce1` 为 470 文件、154 Python、3,003,079 bytes。  
**统计注意**：文件大小单位 bytes，不是代码行数；精确 LOC **NOT MEASURED**。不含上游 Parcae/AxoNN 代码、环境依赖、HF 缓存、模型权重和未提交工作区。

## A. 一句话结论

**Mini-Mythos 已取得小模型真实数据训练/有限 heldout 优势以及原生 Parcae F2-B、F2-C、F2-D 和 F2-E E1–E5 的冻结 CPU 正确性验证；下一阶段应从探针研究切换到随机权重的原生 CPU 完整训练链，而不是无限延续 F2-E。**

**严格限定**：F2-E `E1–E5 PASS/CLOSED` 是固定 `2/2/2` 原生 Parcae、特定 float32 CPU 配置、种子/输入、采样/Mask/重复性/Checkpoint 微型验收的结论；`E6 INCONCLUSIVE`，**整个 F2-E 不等于无条件全 PASS**。原生完整 CPU Training Lifecycle 尚未运行/验收，GPU Gate 2.2-C 仍 BLOCKED。不能声称复现了 Anthropic Claude Mythos 未公开的真实架构/权重/能力。

当前开发分工以用户最新决定为准：**Grok 继续开发与 CPU 执行**；**ChatGPT 独立验收**；Claude Code 暂缓接手。

## B. 五大模块：统一排他统计

沿用原 `PROJECT_MAP.md` 冻结的排他分类，对基线 Git tree 差异分组并与 `ee1b3c8` 实际 blob sizes 汇总核对：

| 研发模块 | 当前 Git 文件数 | 当前 bytes | 阶段状态 |
|---|---:|---:|---|
| 核心模型 | 5 | 94,110 | Tiny 预测能力有限验证；模型语言能力未成熟 |
| 训练 | 3 | 24,480 | R1 Tiny 历史训练已验证；原生端到端生命周期 NOT TESTED |
| 实验与工具 | 98 | 639,567 | F2-B/C/D 和 F2-E E1–E5 限定 PASS/CLOSED |
| 测试 | 76 | 484,810 | F2-E 本次限定验收独立通过；无当前 HEAD 全套测试证据 |
| 文档与证据 | 299 | 1,807,927 | 历史证据与独立审核可追溯 |
| **合计** | **481** | **3,050,894** | **Python 文件合计 154** |

以上为 `ee1b3c8` 的**不可变基线快照**。未来文件/文档继续增减时，不要修改这些历史数字来假装是新的 HEAD 统计；应新增新的计量 SHA。扫描 `research/mini_mythos/scripts/project_map_inventory.py` 可取得完整工作树中的准确物理/非空代码行数，尚无已执行结果。

## C. 五模块详细进度

### 1. 核心模型 — 基础机制存在，语言能力仍早期

- 文件：`open_mythos/main.py`, `moda.py`, `variants.py`, `tokenizer.py`, `__init__.py`。
- 历史 Tiny GQA：随机权重训练至 step600，官方 WikiText-2 test 的 byte-level next-token NLL `2.384439`、PPL `10.852968`；匹配训练暴露量的 Add-1 Bigram 基线 PPL `12.790071`。这是限定预测能力证据，非稳健语言生成证明。
- 当前弱点：Greedy 生成重复；没有同预算非循环 Transformer 的质量、FLOPs、训练稳定性、推理成本对照；推理/编程/对话能力 **NOT PROVED**。
- 路线：保留 `Prelude → Recurrent Core → Coda`，从随机初始化训练独立权重；保留上游，模型架构创新只能在后续公平对照阶段引入。

### 2. 训练 — 优先级转为真实完整生命周期

- 文件：`training/3b_fine_web_edu.py`, `training/requirements.txt`, `research/mini_mythos/scripts/pilot_train.py`。
- 已有 R1 Tiny 真实数据训练、冻结官方 test、部分 checkpoint 恢复；R2 数据分片、worker、恢复等有限 CPU 证据。
- **首次 CPU 统一训练链已运行但未正式验收**：固定输入 6 步 AdamW、linear scheduler、step3 文件保存并重建模型继续 step4–6；权重/Loss/LR 等局部观察积极，但关键恢复状态没有独立验收，整体 `PARTIAL / NOT CLOSED`。见本文最上方 F3-A 补记。
- Grok 先提交 `docs/F3A_FROZEN_CONFIG.md` 冻结后运行并归档 `docs/F3A_RESULT.md`；ChatGPT 审核 `docs/F3A_CHATGPT_INDEPENDENT_REVIEW_AND_R1_GATE_20261025.md` 明确指出恢复状态与负例的关键验收缺口。不得把记录中的 `LOCAL PASS` 当作整体 `CLOSED`。
- 规模 GPU：`gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md` 的环境/成本/真实证据要求仍未通过。

### 3. 实验与工具 — F2 必要 CPU 数学验证已有明确出口

- **F2-B `PASS/CLOSED`**：固定范围原生 Parcae recurrence CPU 路径。
- **F2-C `PASS/CLOSED`（有限）**：冻结三个 Core 梯度标量的 FD 验证，不是完整权重数学证明；纯 fp64 原生路径仍有局限。
- **F2-D `PASS/CLOSED`（有限）**：冻结 fixed-depth/per-batch 自动采样与 checkpoint/RNG/梯度微型验收。
- **F2-E E1–E5 `PASS/CLOSED`（有限）**：per-batch/per-sequence/per-token n/k，真实返回值、实际 recurrent Mask、重复性、Checkpoint OFF/ON 数值/梯度对照；详细审核 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`。
- **F2-E E6 `INCONCLUSIVE`**：直接 Core update 重放不能证明 live masked-loop 的 token 因果传播。原版 Parcae 作者意图 UNKNOWN，不能推断 bug。E6 不是当前完整训练链设计的必经阻塞。
- 决策：**停止新增无必要的 F2-E 采样探针**，推进新训练阶段；旧证据全部保留不可变。

### 4. 测试 — 有历史回归数据，最新 HEAD 全量未跑

- 已归档 R1 Gate F 106/106 单测和 R2 Gate Q 241/241 + 8/8 专项等历史结果（**不同历史时点**）。
- F2-E final closeout：固定本地记录 E1–E5 LOCAL PASS，19 个受控负例被拒绝，特定 E5 checkpoint backward replay 精确两次，9 条 Mask SHA-256 与独立期望重建全部匹配。GitHub 结果/日志/脚本六项声明 SHA-256 全部独立复核。
- 本次 ChatGPT 审核未重新执行 native Parcae CPU 或当前 HEAD 全套 pytest/unittest；不能用历史测试数宣传最新全量 PASS。
- 仍保留未来独立测试：训练 Optimizer 更新、scheduler 步数、checkpoint/resume 逐步等价、完整数值和 RNG 状态。

### 5. 文档与治理 — 可复现和恢复体系已成熟建立

- 已有 `docs/SESSION_START_PROTOCOL.md`、`docs/PROJECT_MAP.md`、本进度快照、旧恢复备份、R0/R1/R2/F2 原始报告与各阶段 ChatGPT/Grok 独立审核结果。
- 新增验收归档 `gate2_2/evidence/f2e/b1_closeout/`；Grok 源提交 `fbeaf7c5030c460343ca2006dc53813c21786dfd`；正式独立审核 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`。
- 现存运维风险：Grok 旧 Codespaces 的 `research/mini_mythos/gate2_1/TEST_RESULTS.json` 曾多次 dirty，该未提交文件实际内容 **NOT VERIFIED** 且不可从 GitHub 恢复。保护它，不执行 reset/clean/覆盖。
- 新会话读最新 Git HEAD、SOP、项目地图、**本进度**和最新阶段验收；旧文中的 Claude 接管/旧 F2-E 待审核字样被最新正式状态取代。

## D. 研发路线与验收门禁（无虚假百分比）

| 阶段 | 当前判断 | 必要出口 |
|---|---|---|
| R0/R1 小模型、R2 数据工具 | 历史限定验收 / 已归档 | 保留复现证据，不以 Tiny PPL 推断模型成熟度 |
| F2-B/C/D | **PASS/CLOSED（限定）** | 不再重复 |
| F2-E E1–E5 | **PASS/CLOSED（限定）** | 不再扩展为新采样研究 |
| F2-E E6 | **INCONCLUSIVE** | 如未来有专门、已授权的因果问题才独立研究 |
| Native Parcae CPU Train Lifecycle 冻结配置 | **F3-A 初始方案已冻结、执行已完成；存在 warmup STOP 标准内部冲突** | 需要在独立 R1 补充中预先清晰裁决，不改历史冻结文件 |
| Native Parcae CPU Train Lifecycle 执行 | **F3-A 固定 CPU 微型范围 PASS/CLOSED** | 原生 full train.py / DataLoader 恢复 / MuonAdamW / GPU / 更大模型仍 NOT TESTED；未来新 gate 单独验收 |
| 更大模型与公平非循环基线 | **NOT TESTED** | 实际模型质量、FLOPs、训练时间/稳定性、推理开销受控对比 |
| GPU Pilot / Gate 2.2-C | **BLOCKED** | 凭据、预算/实时定价、启动环境、真实证据提取器、用户授权 |

不按测试数、代码行数或阶段标签简单算统一完成百分比；现阶段的真正里程碑是**基础 CPU 正确性从“仍待收口”转为“限定正式收口”，下一步是开始真实原生训练链**。

## E. 唯一下一条研发指令、授权与 STOP

**当前下一步（Grok，仅真实数据与评估方案设计，未经授权不可执行）**：
1. 最新 Git 状态/dirty 只读核对并保护 `gate2_1/TEST_RESULTS.json`；
2. 读取 `docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`，确认 F2-E E1–E5 仅限定 PASS/CLOSED、E6 INCONCLUSIVE；
3. 已完成的 F3-A 原生小模型循环训练与文件恢复结果严禁重复；首先读取 `docs/F3A_FINAL_CHATGPT_INDEPENDENT_ACCEPTANCE_20261025.md`，随后只读审计真实数据及 Tokenizer、可恢复数据流、heldout/污染控制、同预算标准 Transformer 基线，冻结下一阶段验收方案。历史 R1/最终证据全部保存；
4. 提交新阶段的设计/验收门禁检查点，等待项目负责人明确授权实际真实数据训练；ChatGPT 继续独立审核，不启动 GPU。

**禁止自动运行训练或 GPU，不改 Parcae/AxoNN 原版，不擅自改递归架构，不覆盖旧证据。** 如训练计划中存在尚不合理的 loss 单调下降断言，需在冻结前调整为可预先定义且能被真实训练支持的标准；不能运行之后倒改验收线。绝不可将当前 CPU 微型测试 PASS 外推到 GPU Gate 2.2-C。

## F. 证据索引

- `research/mini_mythos/docs/R1_GATE_F_RESULT.md` — 真实 tiny heldout
- `research/mini_mythos/docs/R2_GATE_Q_RESULT.md` — 分片/多 worker 合成 CPU 数据验收
- `research/mini_mythos/docs/F2B_FINAL_ACCEPTANCE_20261024.md`
- `research/mini_mythos/docs/F2C_FINAL_ACCEPTANCE_20261024.md`
- `research/mini_mythos/docs/F2D_FINAL_CPU_ACCEPTANCE_20261025.md`
- `research/mini_mythos/docs/F2E_CLOSEOUT_CHATGPT_FINAL_ACCEPTANCE_20261025.md`
- `research/mini_mythos/docs/F2_CPU_TRAIN_LIFECYCLE_PLAN.md`（设计草案）
- `research/mini_mythos/gate2_2/GATE2_2_C_LAUNCH_BLOCKED.md`
- `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`
- `research/mini_mythos/backup/RESEARCH_RECOVERY_CHECKPOINT_20261025.md`

**本文件只汇总现存 GitHub 数据与已经独立审核的证据，本次未运行新训练、未改上游、未新开 GPU。**
