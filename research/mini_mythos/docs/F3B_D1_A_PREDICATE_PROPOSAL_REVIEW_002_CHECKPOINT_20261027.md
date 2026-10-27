# F3B-D1-A-PREDICATE-PROPOSAL-REVIEW-002 — 检查点：A 判定修订提案与 CPU 测试计划的四项修正

**状态：`PROPOSAL / TEST PLAN REVISED (DRAFT) / PENDING CHATGPT AND GROK CROSS-REVIEW / PENDING OWNER DECISION`**；最终方案选择 PENDING；测试执行 **NOT AUTHORIZED**；Grok **DEFERRED**（不是 PASS）。

承接 ChatGPT 审核：Git 范围 PASS、G1/G2 FAIL 证据保护 PASS、A/B 三臂思路保留。本阶段**只改文档**。

## 1. Git

| 项 | 内容 |
|---|---|
| 仓库 / 分支 | `leotree2020/OpenMythos` / `d1-r3-a-revision-proposal-20261027`（普通提交，无强推） |
| 基准提交 | `cc474f56ae77882fa77cfe4e7deb0e6b5d4305e8` |
| 最终提交 | 与本检查点同一提交（SHA 见汇报） |

## 2. 文件与 SHA-256

| 文件 | 修订前 SHA-256 | 修订后 SHA-256 |
|---|---|---|
| `F3B_D1_R3_A_PREDICATE_REVISION_PROPOSAL_DRAFT_20261027.md` | `27371ed6876d7611fa5ae994080e9ce4011414d37d6f937fd6fe50675bb8f349` | `892e512e5da7f2cd3fc4997c09ac27ba4206d290f66c91e10882690480c32322` |
| `F3B_D1_R3_A_PREDICATE_CPU_TEST_PLAN_DRAFT_20261027.md` | `3e6a29e7e1ca3fda92831b9680b16d8db11b1d841164a21067074a9a42799ed3` | `ad9dbca73366d69b12a7384b765e90a0e76e248dc8ecd604b9891e9e90f95474` |

另新增本检查点，并对 `SESSION_START_PROTOCOL.md`、`PROJECT_STATUS_20261025.md`、`PROJECT_MAP.md` 做追加（零删除行）。

## 3. 四项修正

| 编号 | 修正 | 提案位置 | 测试计划 |
|---|---|---|---|
| RV-01 | 三态 `ALIVE` / `EXITED` / `UNKNOWN`；`UNKNOWN` 不得变成 A 真 / 假的成功结论，不得据此发新信号，返回 BLOCKED 并记录原因（原因记在既有字段，不增加事件）；发现范围完整性证据为 `EXITED` 的前提 | RA-1、RA-9、RA-10、3.1 | T-11 → T-11a～e（含「已退出的已知目标 + 范围不完整 → UNKNOWN」与「已指纹验证的 pid 消失 → EXITED」边界） |
| RV-02 | 跨会话后代：sid / pgrp 不匹配不是排除依据；谱系闭包、连续登记、封闭世界排除法；无法归属 → `UNKNOWN`，不猜测 | RA-11、3.2 | T-12a/b（应归属）、T-13a/b（不应归属 / 无法归属） |
| RV-03 | 指纹核对与信号存在 TOCTOU 窗口，不声称指纹消除复用风险；评估 pidfd（先开后核对）；整组信号单独的安全条件；「指纹正确但目标恰在信号前退出」 | RA-7、RA-12、3.3 | T-14a/b/c、T-15、T-16（NOT PLANNED） |
| RV-04 | 子收割者前提拆成维度 A（实际系统调用与重新挂靠行为，CPU 判断）与维度 B（设置失败是否禁止整个运行，实施策略待负责人裁决；默认建议 BLOCKED 但**不是**冻结 R3 的既定规则） | 3.4、第 8 节 Q4 | T-04b → T-04b-A（CPU）、T-04b-B（无 CPU 判据） |

新增 / 改写的每个测试用例均列出环境、输入、预期、**实际状态 NOT TESTED**、未来 PASS / FAIL / BLOCKED 判据。

## 4. 变更纪律核对

| 项 | 实际 | 状态 |
|---|---|---|
| G1/G2 原始 FAIL 证据 | 相对 `af7b39abd17c64df1e08165cd2904a4a68cb1bed` 无差异 | PASS |
| 冻结 R3 / 决策记录 / 冻结记录 | SHA-256 不变：`66a65614…42c5` / `6209602e…6319` / `e3bba6b0…596f` | PASS |
| Driver / Reader / Verifier / v1 / R1 / R2 / 配置 | `D1_CODE_SHA256SUMS` 10/10 OK；配置仍 `FROZEN` | PASS |
| 上游 Parcae | 未触碰 | PASS |
| 实施方案 A 或 B / 新探针 | 未实施；没有写任何代码 | PASS |
| 运行测试、实验、G3～G6、真实 D1 | 均未运行 | PASS |
| Git 变更仅限文档 | 仅 `.md` | PASS |

## 5. 交叉审核状态

ChatGPT：对本修订 **PENDING**。Grok：**DEFERRED**。分歧（若有）保留，由最小裁决实验（需单独授权）回答；起草者倾向不构成决定。

## 6. 未解决问题

1. 方案 A / B 的最终选择：PENDING（待交叉审核与负责人裁决）。
2. 维度 B（子收割者设置失败是否禁止整个运行）：待负责人裁决；不是 CPU 能回答的问题。
3. pidfd 在本环境的可用性与内核语义：NOT VERIFIED；真实 pid 复用：NOT PLANNED / NOT TESTED。
4. 「封闭世界」断言（阶段运行期间监督器不创建未登记的辅助子树）是否可接受：待审核。
5. G3～G6：NOT TESTED。冻结 R3 仍含 A 的缺陷，直到变更流程完成；R3 SPEC FROZEN 状态不变，真实 D1 NOT AUTHORIZED。
6. 沿用的未决项：D08 用途声明文本取自推荐方案草案；D06 只批准 B-LFS；τ / G_term / G_kill / W 为初始验收值；GitHub 分支保护 NOT VERIFIED。

## 7. 下一条唯一研发指令

等待 ChatGPT 与 Grok 交叉审核，并由负责人单独批准候选 CPU 对照实验。
