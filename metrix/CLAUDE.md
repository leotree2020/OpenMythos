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

- E1 Pilot,状态:AWAITING_REVIEW_GATE
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
- 环境、下载、冒烟测试先在 CPU 环境完成;租卡后只跑正式流程。实测预计超过 3 小时即停下报告。

## 5. 自动审查循环

1. 每次提交前调用 `code-reviewer`。
2. 改动涉及数据、split、候选集、打分或评测代码时,再调用 `data-auditor`。
3. 任一结论为 BLOCK:修复后重新调用。不得跳过审查,不得改写或摘要替代审查原文。
4. 连续 3 轮未 PASS:停止,提交当前状态与全部审查原始输出,等待 Review Gate。
5. 审查原始输出保存到 `metrix/e1-pilot/reviews/<commit-hash>/`,随提交推送。

## 6. PR 审查

- 改动经 PR 合入,不直接推送到受保护分支。
- PR 自动审查与本地 subagent 结论不一致时,以更严格的一方为准,并在 PR 中说明。

## 7. 必须等待人工指令的事项

PROTOCOL_FROZEN 的发出与修改、租用 GPU、生成或评测 TEST、删除任何文件、改写 Git 历史、force push。

## 8. 冲突处理

- Reviewer / Auditor 与 Executor 意见不同:由 Review Gate 裁决。
- 协议未覆盖的情况:停止并报告,由 Review Gate 提出方案。
- Review Gate 的裁决写入决定记录时须注明作用范围:本次提交 / 本阶段 / 永久。只有「永久」的裁决可写入本文件。

## 9. 汇报格式

- commit hash 与报告路径。
- 两份审查的原始输出路径与结论。
- 所有结论附原始命令输出。自检勾选不算证据。

## 10. 信任状态

两个审查 subagent 当前为「待验证」。埋入已知 bug 的检出率测试通过前,其 PASS 仅作参考。
