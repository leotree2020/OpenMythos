# Mini-Mythos 双轨开发：代码质量审计与端到端训练

**版本：2026-10-17，初次人工静态检查 + 自动化 AST 审计工具已提交；自动扫描尚待用户 Codespaces 执行。**

## 核心原则

一条主线验证模型能否学习（固定数据/基线 Transformer/递归模型/小预算真实训练/独立 Heldout）；另一条主线在不破坏已有证据的情况下治理工程质量（调用链、复杂度、嵌套函数、职责、重复代码、数据训练安全）。治理的成功标准不是删除最多行代码，也不是把测试数无限增加，而是用更少的代码维护相同或更严格的行为契约。

## 2026-10-17 人工源代码审计的已确认发现（不是完整调用覆盖结论）

| 等级 | 来源 | 精确观察 | 修复策略与证据要求 |
|---|---|---|---|
| P0 数据正确性 | `training/3b_fine_web_edu.py:74-108` | `FineWebEduDataset.__iter__` 在真实 HF `load_dataset(streaming=True)` 后手动 `.shard(num_shards=world_size*num_workers, index=rank*num_workers+worker_id)`，然后 `for sample in ds`。PyTorch Worker 内 HF 有自动 Worker 分片。与 PR27 独立实验相同，存在**可能重复分片**的问题。分布式 rank 与 Worker 的二维语义必须另行核对，不能直接把所有 `.shard` 删除。 | 先在本地 2-rank × 2-worker 合成 Shards 中对比实际分配，锁定 Frozen 数据来源，再选择 rank-once + HF-worker-auto-once 的实现；实际远端损失率还没测得。 |
| P0 Checkpoint 信任 | `training/3b_fine_web_edu.py:238-245,259-303` | `torch.save` 将 `cfg` 对象写入检查点，`torch.load(...,weights_only=False)` 会允许一般 Pickle 反序列化。对不可信的 `.pt` 文件存在执行代码风险。 | 保存纯数据配置/签名清单后考虑 `weights_only=True`，确保旧 Checkpoint 兼容策略明确、哈希和来源约束明确；不能不验证就切换。 |
| P1 来源可复现 | `training/3b_fine_web_edu.py:92-97` | 训练入口没有显式 `revision`；相比 R2 已固定的 HF SHA，重新启动同样配置不保证使用同样数据版本。 | 使用不可变 HF Revision，并在 Checkpoint 的数据契约中记录、核验。 |
| P1 恢复语义 | `training/3b_fine_web_edu.py:445-471` | Checkpoint 恢复后重新创建 Streaming Dataset，并未保留准确的已提交样本 Cursor。源码自己承认恢复会从头重新读取。 | 复用研究层 Gate G/H/J/K 已测试的已提交游标与故障恢复协议，禁止把已预取但未训练样本记为已提交。 |
| P1 结构复杂度 | `training/3b_fine_web_edu.py:311-552` | 主入口 `main()` **242 行**，包括分布式启动、训练配置、模型、优化器、Checkpoint、数据与迭代管理。 | 先提取纯配置/来源检查、Checkpoint 子系统和训练循环步骤，按清晰接口迁移，完整训练 Trace/梯度/恢复位级回归通过后才删除旧实现。 |
| P1 公开 API 契约 | `open_mythos/__init__.py:29-55` | `__all__` 声明 `load_tokenizer` 和 `get_vocab_size`，但该文件没有绑定或导入这两个名称；`from open_mythos import *` 可能失败。 | 执行真实 API smoke test，确认兼容性要求，再选择恢复合法导出或修正 __all__，先加回归测试。 |
| P2 结构膨胀 | `open_mythos/main.py`、`open_mythos/moda.py` | 分别约 **1,086 / 1,064 行**；多个 Attention、MoE、RoPE、模型结构和数据类型在单一模块，维护/审查成本高。 | 明确共享基础组件边界：`config`、`attention`、`moe`、`recurrent`、`generation`，保留旧 import/API 的 shim 并运行 GQA/MLA 前向、反向、KV Cache/BF16 等门禁；两个架构不同的归一化/注意力实现不必强制共用。 |
| P2 函数嵌套 | `research/mini_mythos/scripts/r2_hf_worker_shard_pack.py:336` 和 `r2_pr27_real_dataloader_resume.py:288` | 两个较大的 `compare_*_resume` 函数内都定义了 `cursor()` 闭包。文本简单行扫描会错误估算嵌套函数大小；应以 AST `end_lineno` 为准。 | 分辨闭包是合理局部工厂还是掩盖依赖。重构目标是缩小父函数的职责与状态参数，不是机械禁止嵌套。 |

以上 P0/P1/P2 是修复优先次序，不是未经运行的正式 CVE 或已测量生产故障。上游 `kyegomez/OpenMythos` 未合并的 PR #27 与本 Fork 根代码须独立归因。

## 自动化审计工具与使用

新增只读标准库脚本 [maintenance_ast_audit.py](../scripts/maintenance_ast_audit.py) 及配套 [单元测试](../tests/test_maintenance_ast_audit.py)。不 import 业务模块，不运行模型，不访问网络，不修改源码。用 `ast.parse` 检测：

- Python 文件/函数数量，真实 AST 函数行号与 `end_lineno`；方法与内嵌函数分开计数。
- 近似圈复杂度（McCabe-like）、嵌套控制流深度、长函数/长文件热点；默认热点为函数 >=70 行或复杂度 >=12 或控制流深度 >=4，或定义在函数内的内层函数。
- 疑似没有静态引用的**私有**函数，以及“只在测试里静态直接调用”的候选；只作为人工检查清单，不等于可删除。动态调用、PyTorch `forward`、反射、第三方 API、CLI 入口都会影响判定。
- `__all__` 缺少静态绑定、`torch.load(...weights_only=False)`、未显式传 `revision` 的 HF `load_dataset`、Worker `__iter__` 内同时使用 `load_dataset` 与手动 `.shard`。
- 完整 JSON 结果放入 Git-ignored `research/mini_mythos/results/quality/`，不将可能出现的绝对目录/私有数据打包上传。

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_maintenance_ast_audit.py' -v
python research/mini_mythos/scripts/maintenance_ast_audit.py --repo . --out research/mini_mythos/results/quality/ast_audit_2026-10-17.json
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
```

**2026-10-17 用户 Codespaces 已返回全量 `248/248 PASS（62.136 秒）`**，其中包含 Gate Q spawn 和六项 AST 审计工具回归。见 [全量测试证据归档](CODE_QUALITY_AUDIT_248_TEST_BASELINE.md)。**现已收到真实仓库只读 AST 扫描结果（2026-10-17）**：105 Python 文件、889 函数/方法、85 个复杂度热点、23 个嵌套函数、5 项风险模式、2 项失效 `__all__` 导出、2 项仅测试静态调用候选、0 项未引用私有函数候选。详见 [真实 AST 扫描结果](CODE_QUALITY_AST_SCAN_2026-10-17_RESULT.md)。但完整 JSON 是 Codespaces 本地 Git ignored 文件，当前尚未获得两个仅测试函数和 23 个内嵌函数身份清单；不能据此自动删除任何代码。第一项候选重构为审计器本身 `scan` CC~48 的职责拆分，见 [重构预注册方案](MAINTENANCE_SCANNER_REFACTOR_001_PLAN.md)，尚未由 Codespaces 测试。

## 删除/重构治理规则

1. **先画调用关系**：入口点（training、CLI、用户 API、tests、examples）、函数依赖与运行时反射；未观察到调用也不是无人使用。
2. **动态证据确认**：用现有功能测试 + 后续小预算训练的运行覆盖率证明真实路径被执行。标明只在测试中调用的实验脚本和为兼容保留的 API。
3. **分层处置**：A 保留（运行路径/API 合法），B 重构（长函数/高度耦合），C 标记 deprecated（有兼容用户），D 待删除（证明完全无人引用且有迁移方案）。在 D 之前不删除研究证据、实验脚本或动态入口。
4. **不改变行为的拆分先行**：先添加测试，再小步提取函数模块，每次对照原来的模型 Tensor shape、Loss、Gradient、Optimizer、随机种子、文件来源和 Checkpoint 行为。
5. **量化质量**：风险 P0 清零（有运行门禁）、复杂度热点列清单与 Owner/分批完成、函数职责单一、依赖方向清晰；对长函数设置告警而非机械禁令。

## 和端到端训练如何并行

- 近期训练轨：选择可在 CPU Codespaces 完成的最小真实数据 Smoke，固定 Tokenizer/来源/模型版本，对照简单 Transformer，并记录 Loss/PPL 和训练后可读生成的局限；不投入不具备的 GPU。
- 近期质量轨：先审计 `training/3b_fine_web_edu.py` 和公开导出契约。不要让可疑旧训练入口成为新的端到端训练的默认实现；先使用已有研究层验证过的数据与 Checkpoint 契约。
- 合并判定：**训练正确 + 审计质量检查 + 完整回归通过** 三者同时满足才推进模型规模或移除旧路径。
