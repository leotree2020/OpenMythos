# Metrix — 角色分工与执行规则

Metrix 是独立子项目。根目录 `CLAUDE.md`(Mythos 宪章 v2.0)第 1 节与第 3.7 节不适用于 Metrix;第 5 节「不要做」继续适用。在 `metrix/` 内,本文件与宪章冲突时以本文件为准。

本文件的修改须经 Review Gate 裁决、Project Owner 批准,并记录原因与时间。

## 1. 角色

| 角色 | 由谁担任 | 职责 | 不做 |
|---|---|---|---|
| Project Owner | Miyaji | 拍板重大事项;批准租卡与预算;在 Review Gate 与 Claude Code 之间转达 | 日常审查、代码细节 |
| Review Gate(总管) | claude.ai Project「Metrix」 | 总体设计、协议审阅、Gate 裁决、下达编号指令、维护决定记录 | 写代码、跑命令、替 Owner 拍板 |
| Executor | Claude Code 主会话 | 写代码、运行、提交、写 SUBMISSION_NOTE、调用两个审查 subagent | 改协议、审查自己的产物、推翻审查结论 |
| Code Reviewer | subagent `code-reviewer` | 查 bug、死代码、可读性、合理性、与协议的一致性 | 修改任何文件 |
| Data Auditor | subagent `data-auditor` | 用自写脚本独立复算哈希、L1–L6 泄漏、候选可行性、split | 复用 Executor 的检查代码、加载模型权重 |

重大事项(只有 Owner 能批准):研究方向、模型、arm 结构、门槛数值、PROTOCOL_FROZEN、TEST 评测时机、租用 GPU、冻结后的协议改动、删除文件、改写 Git 历史。

## 2. 当前阶段

- E1 Pilot,状态:PROTOCOL_FROZEN（v1.1）（出处：Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC；作用范围：本阶段（Owner 在第 9 轮答复，见 metrix/e1-pilot/tasks/ROUND9_TASKS.md 第二段）；原因：协议已冻结并发布 v1.1 勘误版，原状态未随冻结更新，见 metrix/e1-pilot/reports/ROUND8_REPORT.md「待 Review Gate 决定」第 9 项）
- 分支:metrix-e1-pilot-protocol-v1
- 基线:leotree2020/OpenMythos mythos-idea-thermo-v1 @ 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc
- 模型:Qwen/Qwen3-1.7B @ 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
- 工作目录:metrix/e1-pilot/。metrix/ 以外只允许:根目录 CLAUDE.md 第 6 节、.claude/agents/ 下的两个 subagent 文件。

## 3. 硬性禁止(收到 PROTOCOL_FROZEN 之前)

- 不训练、不评测、不生成或读取 TEST 数据。
- 不在 CPU 环境加载真实模型权重。CPU 只做模板、tokenizer、哈希、泄漏检查,以及用随机初始化的同构小模型做冒烟测试。
- 汇报时写明实际运行环境(主机名或环境类型),不要笼统称为「本地」。

## 4. 算力

- 训练与评测只在单张 A100 80GB 上执行,上限 4 小时。首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废。
- 环境、下载、冒烟测试先在 CPU 环境完成;租卡后只跑正式流程。预检预估总时长超过 3.5 小时即停（协议 ST11）；累计 GPU 时间超过 4 小时即停（协议 ST7）。（出处：Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC；作用范围：本阶段；只替换本条原末句「实测预计超过 3 小时即停下报告。」，本节其余文字不变（作用范围与替换范围均为 Owner 在第 9 轮答复，见 metrix/e1-pilot/tasks/ROUND9_TASKS.md 第二段）；原因：原 3 小时与协议 ST11 的 3.5 小时不一致，见 metrix/e1-pilot/reports/ROUND8_REPORT.md「待 Review Gate 决定」第 6 项）

## 5. 自动审查循环

1. 每次提交前调用 `code-reviewer`。
2. 改动涉及数据、split、候选集、打分或评测代码时,再调用 `data-auditor`。
3. 任一结论为 BLOCK:修复后重新调用。不得跳过审查,不得改写或摘要替代审查原文。
4. 连续 3 轮未 PASS:停止,提交当前状态与全部审查原始输出,等待 Review Gate。
5. 审查原始输出保存到 `metrix/e1-pilot/reviews/<commit-hash>/`,随提交推送。
6. 每次调用审查 subagent,调用文字的第一句固定为:「先读仓库中的 .claude/agents/<名称>.md，以它为你的完整定义；它与你已加载的定义冲突时，以仓库文件为准。」调用前比对仓库文件与已加载定义的 frontmatter;两个版本的 tools 行不一致时必须停下,不得用此方法替代。（出处：Review Gate 第 7 轮裁决，Owner 批准，本阶段，2026-11-22 03:25:59 UTC）

## 6. PR 审查

- 改动经 PR 合入,不直接推送到受保护分支。
- PR 自动审查与本地 subagent 结论不一致时,以更严格的一方为准,并在 PR 中说明。

## 7. 必须等待人工指令的事项

PROTOCOL_FROZEN 的发出与修改、租用 GPU、生成或评测 TEST、删除任何文件、改写 Git 历史、force push。

注：「删除任何文件」不含会话临时目录；但支撑结论的输出须先提交。

## 8. 冲突处理

- Reviewer / Auditor 与 Executor 意见不同:由 Review Gate 裁决。
- 协议未覆盖的情况:停止并报告,由 Review Gate 提出方案。
- Review Gate 的裁决写入决定记录时须注明作用范围:本次提交 / 本阶段 / 永久。「永久」与「本阶段」的裁决可写入本文件,写入时须注明作用范围;「本阶段」的裁决在本阶段结束时失效。（出处：Review Gate 第 7 轮裁决（第 8 轮指令第 1e 项），Owner 批准，2026-11-22 05:27 UTC；原因：原文只允许「永久」的裁决写入本文件，与已写入的第 5 节第 6 条、第 10 节的「本阶段」裁决矛盾，见 metrix/e1-pilot/reports/ROUND7_REPORT.md「待 Review Gate 决定」第 4 项）（作用范围：永久。出处：Review Gate 第 8 轮裁决，Owner 批准，2026-11-22 09:44 UTC；原因：1e 写入时未注明这条裁决自己的作用范围，见 metrix/e1-pilot/reports/ROUND8_REPORT.md「待 Review Gate 决定」第 1 项）

## 9. 汇报格式

- commit hash 与报告路径。
- 两份审查的原始输出路径与结论。
- 所有结论附原始命令输出。自检勾选不算证据。
- 原始输出一律写入仓库并推送，不留在临时目录；data-auditor 须提交 audit 脚本的完整 stdout。（出处：Review Gate 第 4 轮裁决，Owner 批准，永久）

## 10. 信任状态

- `code-reviewer`:已验证（2026-11-21 盲测 3/3 检出、0 误报；每类仅 1 个样本，PASS 仍须附原始输出）。
- `data-auditor`:「待验证」。2026-11-21 的盲测只测了 code-reviewer;埋入已知 bug 的检出率测试通过前,其 PASS 仅作参考。
- 以上两条的出处：Review Gate 第 5 轮裁决。（出处：Review Gate 第 6 轮裁决，Owner 批准，本阶段，2026-11-22 03:25:59 UTC）
