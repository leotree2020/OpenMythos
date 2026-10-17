# 维护性审计审查日志 — AST 扫描器第一次行为保持型拆分

**设计于 2026-10-17；此项重构现已经由用户 Codespaces 验收：全量 248/248 PASS（62.335 秒），新全仓审计成功。详见 [实测结果](MAINTENANCE_SCANNER_REFACTOR_001_RESULT.md)。原设计内容留存；整体热点数 85→87，不能声称项目全部复杂度下降。**

## 修复动机

2026-10-17 的真实全仓扫描显示 `maintenance_ast_audit.py:181 scan` 是最高复杂度热点：110 行、McCabe-like 近似 48、控制嵌套 4。它同时负责 AST 解析、调用收集、风险检查、Dead Code 参考关系分析和构造 JSON，违反单一职责，并提高了改动审计规则时出错的概率。

## 本次候选重构

仅修改 `research/mini_mythos/scripts/maintenance_ast_audit.py`：

| 新函数 | 职责 |
|---|---|
| `_analyze_file` | 读取单个 Python 文件、AST 解析、记录导出/直接调用；不运行用户代码 |
| `_training_shard_risks` | 判断训练流里是否同时有 HF load_dataset + 手动 shard 的待审核形状 |
| `_reference_candidates` | 用保守静态调用表标记私有未用与仅测试引用候选，绝不删除函数 |
| `_build_report` | 统一排序并生成原有 V1 JSON Schema，保留原始排序字段和解释文本 |
| `scan` | 仅管道化遍历文件、累积调用关系和返回结果 |

严格保持 `MYTHOS_READ_ONLY_AST_MAINTENANCE_AUDIT_V1` Schema、阈值（CC>=12、长度>=70、nest>=4）、导出与分片风险检测、各报告排序和标记策略，不修改生产模型、主训练、HF 快照、Checkpoint 或用户审计旧 JSON 文件。

## 为什么不能直接要求所有指标完全相同

审计工具会**扫描它自己**，所以拆出 4 个新的私有函数后，全仓函数数量会改变，`maintenance_ast_audit.py` 的各函数行数、CC 及 Top-20 排名必然改变。这是预期差异；但所有**其他 Python 文件**的 AST 复杂度、风险扫描、exports、测试专用函数/候选清单理应严格保持一致。

## 必须跑的实测门禁

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_maintenance_ast_audit.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/maintenance_ast_audit.py --repo . \
  --out research/mini_mythos/results/quality/ast_audit_refactor_2026-10-17.json
```

旧报告 `ast_audit_2026-10-17.json` 保留不可覆盖。新报告 `ast_audit_refactor_2026-10-17.json` 是单独结果，不能因全量单测通过就预先把这次重构标记 VERIFIED。

## 下一步需要从旧报告提取的细节

- `test_only_static_call_candidates` 两条路径、完整函数 qualname/line；确认是不是测试框架/外部用户可触发的公共路径。
- `nested_function_definitions` 23 个条目的路径/qualname/行号，优先分析会捕获复杂可变状态的闭包。
- `complexity_hotspots` 排名靠前的参数、代码耦合和可能分离职责的区域；优先训练主函数以及涉及真实数据、Checkpoint 的验证代码。
- `missing_exports` 两条已确认，请另行定义公开 API 的保持/迁移策略，不在缺少签名证据时盲目实现或移除。

**计划推进**：新 248 项基线验证后，仅在数据一致性门禁和静态问题清单经过人工审核时继续拆分重要训练函数；端到端模型训练和 Transformer 基线按并行主线推进。
