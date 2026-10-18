# Gate D 审计记录

本文件单独记录审核结论和文档状态。PREREGISTRATION.md 和 ANALYSIS_PLAN.md 的原文不作改动。

## 文档状态的同步说明

- PREREGISTRATION 第 13 节和 ANALYSIS_PLAN 第 7 节中"修订 6（设计第三稿，待审核，未实现）"的字样，是提交当时的状态。之后的实际状态如下：
  - 设计第三稿与两项前置定义：b3197da、49a3699，按 b3197da 的复核获得有条件 GO；
  - 实现：053a771，加上 D2 MLP 同子集控制的修复 5b8444f；
  - 最终计时：26616a3；监控日志清理：9334aa2；
  - 启动前最终审核结论：有条件 GO，以 9334aa2 为正式提交，按第 0 级完整工作量启动。
- 修订 4（D3）、修订 5（D3 补充校准与门控）都已获批准并实现：门控实现在 c38604d。

## 正式运行

- 启动前检查（本会话路径 `/home/user/OpenMythos`；审核文本中写的是 Codespaces 路径 `/workspaces/OpenMythos`，检查内容相同）全部通过：
  - 分支为 `claude/openmythos-research`；
  - 本地和远端 HEAD 都是 9334aa2bcef3327940fd1d5b306fa3b1a044311b；
  - 工作区干净，`results/`、`logs/` 不存在；
  - 冻结工作量核对通过（PREFLIGHT PASS）；
  - 没有设置 `GATE_D_` 测试变量；可用内存 15.5 GB。
- 运行：2026-10-18 09:02:09 – 10:44:15 UTC。30 个状态全部完成，`DONE`；没有 INTEGRITY FAILURE 和 RUN ERROR。
- 运行期间，只读取并提交了已完成状态的结果文件（f1ecc56、3376170、1f9940e），没有改动 `results/` 和 `logs/`，也没有改动任何代码。

## 审核中提到、本轮未改动的非阻断事项

- `d2.mlp_with_control` 用 `assert` 检查控制样本与探针一致。用 `python -O` 运行时，这项检查会被禁用。正式运行使用的是普通 `python`。以后可以改成显式抛出异常（未改，以保持正式代码与 9334aa2 一致）。
