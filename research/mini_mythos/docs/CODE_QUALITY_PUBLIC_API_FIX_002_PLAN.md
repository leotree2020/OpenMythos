# 维护性审计整改 002 — 最小公开 API `__all__` 修复

**2026-10-17 已提交代码和测试；尚未在 Codespaces 重跑，因此 NOT YET VERIFIED。** 基线：上一轮审计器重构已通过 `248/248 tests`（62.335s）。

## 事实依据

真实全仓 AST 扫描（重构前、后均一致）指出 `open_mythos/__init__.py` 中未绑定的 `__all__` 两个名字：`load_tokenizer` 和 `get_vocab_size`。人工检查该模块，确实没有定义、赋值或从 `open_mythos.tokenizer` 导入这两个名称。当前 `open_mythos/tokenizer.py` 仅提供 `MythosTokenizer` 类及内部属性 `vocab_size`，但没有两函数的可验证 API 签名。不能凭名字猜测实现一个新方法。

## 实施

- 修改 `open_mythos/__init__.py`：仅删除不存在的两项 `__all__` 字符串，**保留 23 个真实导出及原有类、方法、参数和数学路径**。
- 新增 `research/mini_mythos/tests/test_open_mythos_public_exports.py`：3 项真实包加载测试，直接在模块顶层执行 `from open_mythos import *`；验证 `__all__` 每个元素被真实绑定且非空、无重复，且核心导出的 `OpenMythos` 和 `MythosTokenizer` 与其定义模块为同一个类。
- 新测试**不会**调用 `MythosTokenizer()` 下载外部模型，不读取远端数据、不跑训练或 GPU。

## 风险与兼容性

之前的 `from open_mythos import *` 因未绑定成员可能失败，因此删除 phantom exports 是修复坏掉的公开通配符导入契约，不会删除一个真实已存在的 `load_tokenizer` 实现。任何外部依赖这两个名称的调用在修复前本来就不能被当前包满足。若官方希望提供新 helper，应该先有清晰的兼容签名和实现测试，再作为单独变更引入；这次不擅自增加 API。

项目根目录现有 `tests/` 下 pytest 测试未包含在研究 `unittest discover -s research/mini_mythos/tests` 内。本轮的 3 项新研究回归使之前 248 项变为**预计 251 项**，这个数字不是用户已验证 PASS。

## Codespaces 验收

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_open_mythos_public_exports.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/maintenance_ast_audit.py --repo . \
  --out research/mini_mythos/results/quality/ast_audit_api_fix_2026-10-17.json
```

**预期**：3/3 新 API 测试成功，研究全量 251/251 成功，新的 AST 报告 `missing_declared_exports=0`；而 `review_risk_patterns` 预计仍为 5，主训练 P0 风险并不会因为修复 API 消失。真实结果以终端为准，旧 JSON 保留不覆盖。

## 下一步不受本次 API 修复阻断的工作

真实用户扫描还有 23 个内嵌函数与两个 `test-only` 静态候选。经人工代码复核，`build_loader_native_once` 是研究阶段未接入生产入口的候选 API，**保留待集成**；`load_local_hf_dataset` 是 spawn Worker 注入中的函数对象，属于名字级只统计调用导致的**假阳性**，必须保留。禁止按测试调用候选清单自动清理。

主训练 `training/3b_fine_web_edu.py` 的 rank×worker HF sharding、Checkpoint `weights_only=False` 与浮动 Dataset Revision 尚未被修改，仍需独立设计受限本地训练/恢复回归，再逐个修复。当前所有源码工作都不能构成 Mythos 独立模型性能已提高的证据。
