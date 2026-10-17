# 代码质量基线 + Q spawn 加固：248 项全量回归实测结果

**日期：2026-10-17，证据：用户 Codespaces 终端返回的完整测试尾部统计。状态：全量研究回归 PASS。**

```text
----------------------------------------------------------------------
Ran 248 tests in 62.136s

OK
```

## 能证明什么

- 在此之前，用户实测原版 Gate Q 全量 241/241 PASS；随后研究分支提交 1 项 spawn 工厂负控单测与 6 项只读 AST 审计测试，项目预计由 241 增至 248 项，Codespaces 现在回报**完整 248 项全部 PASS**。
- 这是 `unittest discover -s research/mini_mythos/tests -p 'test_*.py'` 范围内的回归证据。核心 `open_mythos` 的其它独立测试入口（如根目录 `tests`）与训练量化质量基线，不由此自动证明。
- Q 双 Worker 加固版测试中的目标是 `spawn` 与本地合成 HF 14 Arrow Shard 身份来源；它不下载 Parquet、不运行原版 PR27 的真实远程训练。结合仓库中现有测试逻辑，通过全量测试说明未触发这组单测的断言失败。
- 标准库 AST 代码审计工具有 6 项离线单测，已包含在完整 248 项回归中。但**这不等于用户已执行 `maintenance_ast_audit.py --repo .` 检查实际整个仓库**。

## 尚未获得的证据（禁止升级结论）

- 用户此次仅提供最终 `Ran 248 tests ... OK`，**没有提供专项 9 项 Gate Q spawn 测试逐行输出、警告 stderr、或者独立 AST 扫描摘要/JSON**。因此不能断言“整个测试集不再出现 fork 警告”，只能说 Q 候选加固已整合进全套测试并通过。
- 未获得真实代码的 `complexity_hotspots`、`test_only_static_call_candidates`、`missing_exports` 输出，不能使用猜测的函数计数/行数假装扫描已完成。
- 任何未引用、仅被测试调用的函数均未获证实可安全删除。源代码、旧实验报告、训练模型、上游 PR27 没有因审计工具而发生重构。

## 下一步

在 Codespaces 根目录运行只读扫描并将控制台输出回传：

```bash
python research/mini_mythos/scripts/maintenance_ast_audit.py --repo . \
  --out research/mini_mythos/results/quality/ast_audit_2026-10-17.json
```

该命令只读取 Python 源代码、输出静态指标和风险清单，不联网、不运行训练、不会修改源码（但会生成 Git ignored JSON 报告）。对 `training/3b_fine_web_edu.py` 已人工定位的 Worker 分片、未固定 HF revision、checkpoint 反序列化与 `open_mythos/__init__.py` 导出项异常，先结合扫描结果建审计整改序列，再以独立单测支持小步重构。
