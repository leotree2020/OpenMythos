# F3B-D1-R3-SPEC-FREEZE-001 — R3 规范冻结检查点

**正式状态：`R3 SPEC FROZEN / IMPLEMENTATION NOT TESTED / REAL D1 NOT AUTHORIZED`**。仅冻结规范文档的字节版本；不冻结尚未存在的新脚本；不授权任何实验或真实 D1。本检查点是独立文件，不被被登记的文件引用（没有哈希引用循环）。

## 1. 登记

| 项 | 内容 |
|---|---|
| 仓库 / 冻结分支 | `leotree2020/OpenMythos` / `d1-r3-spec-freeze-20261026`（从 `d1-r3-approved-candidate-20261026` 新建，该分支与 R3 草案分支均不被覆盖） |
| Git 基准提交 | `79273d127548e2462026c2ae000dc2499798f5bd`（分支 `d1-r3-approved-candidate-20261026`） |
| 冻结对象 1：R3 规范 | `F3B_D1_PRE_REAL_SPEC_R3_APPROVED_CANDIDATE.md`，SHA-256 `66a656145fc203c71b233ac872eb2eb4c24476717f95f57c1e67a5c112e242c5` |
| 冻结对象 2：负责人决策记录 | `F3B_D1_R3_OWNER_DECISION_20261026.md`，SHA-256 `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319` |
| 冻结记录 | `F3B_D1_R3_SPEC_FREEZE_RECORD_20261026.md`，SHA-256 **`e3bba6b0968101bf68ce4679d8eb6b6c9b1e4a748227479c11c74b2782bf596f`** |
| 冻结指令 / 审核结论 | F3B-D1-R3-SPEC-FREEZE-001（2026-10-26，Asia/Tokyo）；ChatGPT 独立审核 `R3 DOCUMENT ACCEPTANCE PASS / READY FOR SPEC FREEZE`（经冻结指令转述） |
| Git 提交 | 与本检查点同一提交（SHA 见汇报）；各哈希可由 `git show <提交>:<路径> \| sha256sum` 复算 |

**哈希引用方向：** 冻结记录 → 两个冻结对象（摘要）；本检查点 → 冻结记录、两个冻结对象（摘要）；冻结对象与冻结记录都不引用本检查点，没有任何文件包含自己的摘要。

## 2. 冻结前后的实际检查

| 检查 | 实际 | 状态 |
|---|---|---|
| 冻结对象 SHA-256 完全一致 | 冻结前（工作区）与基准提交里的两份文件，字节与登记值一致；提交后再从冻结提交复算（见汇报） | PASS |
| 冻结对象未被改动 | 相对基准提交，两份冻结对象、R3 草案 FINAL-005、此前各检查点均无差异 | PASS |
| 原代码 SHA 清单 | `D1_CODE_SHA256SUMS` 10/10 OK；`D1_FROZEN_CONFIG.json` 仍 `FROZEN`（`0d35dc21a4beca7c…`） | PASS |
| v1 / R1 / R2 | `a55b2cb7…`、`f92c4e79…`、`1d4c3629…` 不变 | PASS |
| 负责人决策文件不变 | `6209602e7d51b1ae2774bf13282d962c28132c18757c25b70a589b97eb926319` | PASS |
| Git 变更仅限文档 | 新增 2 个文件（冻结记录、本检查点）+ 追加 3 个索引；相对 D1 Closeout 基准 `97d0faf2982f4122941d2299a23cab6ab2ba04a3` 没有任何非 `.md` 文件变化 | PASS |
| 依赖图 | 重新构图：17 节点；`ref` 31 / `rec` 9 / `sub` 3，共 43 边；无重复、无环、层级严格递减 | PASS |
| R3-D01…D11 / D07 | 规范与决策记录逐项一致；D07 仅方案 X，τ=5 s、`G_term`=10 s、`G_kill`=5 s、`W`=600 s；D08 摘要 `sha256:72e378a7b8b0d4a4066e429ef994bd6850fe0ba7788103fc81aa5e83bd85f310` | PASS |
| 研发实验 | 没有执行任何研发实验；没有下载 WikiText、拟合 Tokenizer、运行 D1、修改上游 Parcae、使用 GPU、启动 D2/D3 | PASS |

## 3. 后续 CPU 测试门禁（全部 NOT TESTED，登记自冻结记录第 7 节）

| # | 门禁 | 状态 |
|---|---|---|
| G1 | `waitpid(WNOHANG)` 与存活目标 A 的正确协调 | NOT TESTED |
| G2 | 进程已退出但尚未回收时，不得错误认定仍需 SIGKILL | NOT TESTED |
| G3 | SIGTERM 提前退出且回收较慢的情形 | NOT TESTED |
| G4 | TERM / KILL 返回 ESRCH、EPERM 等异常时的如实记录 | NOT TESTED |
| G5 | 子进程、进程组、被重新挂靠后代的生命周期 | NOT TESTED |
| G6 | UNPROVABLE 与完整性 FAIL 并存时的状态优先级 | NOT TESTED |

这些门禁**不因规范冻结而自动判 PASS**。

## 4. 未解决问题

- 所有新机制（记录器、监督器、预算账本、获取、拟合、审计、清单生成、摘要模块、验收含 `--postmortem`、固定与 RV 工具）**未编写，NOT TESTED**；每个任务需单独授权、独立 CPU 验收，全部完成后整体重新冻结（R3-D09）。
- 真实 D1、真实数据下载、正式 Tokenizer 拟合：**NOT AUTHORIZED**；第一个合成 CPU 实验需单独授权；训练、GPU、D2/D3 NOT TESTED / NOT AUTHORIZED；Grok 交叉复审 **DEFERRED**，不是 PASS。
- 待核对事项沿用：D08 用途声明文本取自推荐方案的草案文本（决策记录第 6 节）；D06 只批准 B-LFS，真实 Hub 元数据若不含 `lfs.sha256` 则 S1 BLOCKED，需先做单独授权的仅 L0 元数据验证；τ / `G_term` / `G_kill` / `W` 是初始验收值，需 CPU 测试。
- 沿用的残余风险：同一信任域的局限、远端引用不是不可伪造证明、GitHub 分支保护 NOT VERIFIED、Driver 前后哈希只证明两个检查时刻、目标环境系统调用 NOT TESTED、Hub 元数据语义与 Xet 行为 NOT VERIFIED。

## 5. 变更规则（摘自冻结记录第 6 节）

改变 R3 已批准行为的修改，必须：记录原因 → 独立修订文件 → 必要的 CPU 受控实验 → ChatGPT 独立审核 → 涉及负责人决策的重新取得批准 → 产生新规范版本、新 SHA-256 与新检查点。不得就地修改冻结版本。

## 6. 下一条唯一研发指令

等待单独授权后，启动第一个合成数据 CPU 正确性实验。
