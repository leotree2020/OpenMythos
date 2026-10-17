# Mini-Mythos AST 全仓维护性审计 — 首次真实 Codespaces 扫描结果

**扫描日期：2026-10-17；来源：用户在 Codespaces 直接运行 `maintenance_ast_audit.py --repo .` 并回传控制台原始输出。** 这不是模型执行覆盖率、死代码证明、正式安全漏洞扫描或远端训练验证。

## 原始基线（已由用户执行）

| 指标 | 实测 |
|---|---:|
| Python 文件数 | **105** |
| 函数和方法总数（包含 tests） | **889** |
| 代码复杂度/长度/嵌套热点数 | **85** |
| 函数内嵌套函数定义数 | **23** |
| 有明确模式须人工审核的风险 | **5** |
| `__all__` 缺少绑定的名称 | **2** |
| 仅在测试中静态调用候选 | **2** |
| 无静态引用私有函数候选 | **0** |

用户真实运行的命令：

```bash
python research/mini_mythos/scripts/maintenance_ast_audit.py \
  --repo . \
  --out research/mini_mythos/results/quality/ast_audit_2026-10-17.json
```

终端确认保存了 Git ignored 本地审计报告：`research/mini_mythos/results/quality/ast_audit_2026-10-17.json`。目前 GitHub 仓库中没有该报告的实际内容；审计归档**不得填充未经用户提供的 JSON 细节**。

## 控制台返回的 Top-12 复杂度（McCabe-like 静态近似）

| 排名 | 文件/行号/函数 | 行数 | CC~ | 控制嵌套深度 |
|---:|---|---:|---:|---:|
| 1 | `research/mini_mythos/scripts/maintenance_ast_audit.py:181 scan` | 110 | **48** | 4 |
| 2 | `research/mini_mythos/scripts/r2_fineweb_source_snapshot.py:157 check_manifest_and_snapshot` | 78 | **41** | 2 |
| 3 | `training/3b_fine_web_edu.py:311 main` | 237 | **33** | 3 |
| 4 | `research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py:200 verify_report` | 65 | **32** | 2 |
| 5 | `research/mini_mythos/scripts/evidence_archive.py:192 verify_archive` | 53 | **32** | 3 |
| 6 | `research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py:247 verify_report` | 63 | **30** | 2 |
| 7 | `research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py:146 summarize_worker_rows` | 45 | **28** | 2 |
| 8 | `research/mini_mythos/scripts/r1_text_pilot.py:171 main` | 140 | **27** | 2 |
| 9 | `research/mini_mythos/scripts/act_gate_b.py:60 main` | 77 | **27** | 3 |
| 10 | `research/mini_mythos/scripts/r2_pr27_static_audit.py:21 check_pr27_sources` | 87 | **26** | 2 |
| 11 | `research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py:176 verify_report` | 53 | **25** | 2 |
| 12 | `research/mini_mythos/scripts/act_compute_sweep.py:62 main` | 86 | **21** | 3 |

本计分方式为项目自建 AST 近似，不能直接与 Radon/ruff/McCabe 的分级混同。因当前实现只检查名字级静态调用，可能产生误报/漏报，禁止据此直接删函数。

## 已确认须人工复核的五个模式

| 文件/行号 | 模式 | 优先级/处置 |
|---|---|---|
| `training/3b_fine_web_edu.py:74` | `hf_manual_shard_inside_iter` | **P0**：主训练实际的 DDP rank + HF native worker 分片关系须实测，不能把 PR27 的两 Worker 结论直接套到 DDP |
| `training/3b_fine_web_edu.py:92` | `hf_load_dataset_unpinned_revision` | **P1**：使用固定版本并登记 Dataset Provenance；配置和 Checkpoint 兼容性需测试 |
| `training/3b_fine_web_edu.py:284` | `torch.load_weights_only_false` | **P0 Checkpoint 信任边界**：不可信 Pickle 可导致执行代码。先分离 cfg 为可安全加载的纯数据并保持旧存档处理策略，不能直接假定所有 Checkpoint 可信 |
| `tests/small_benchmark.py:374` | `hf_load_dataset_unpinned_revision` | **P2**：基准测试数据来源需要冻结；不是主训练程序的数据完整性证据 |
| `tests/small_benchmark.py:375` | `hf_load_dataset_unpinned_revision` | **P2**：与上一行分别检查调用链/条件分支后处理 |

## 公开 API 异常

扫描确认：`open_mythos/__init__.py` 的 `__all__` 列出 `load_tokenizer`、`get_vocab_size`，但此模块没有相应绑定，`from open_mythos import *` 可能触发 AttributeError。阅读过当前 `tokenizer.py`，只看到 `MythosTokenizer`、`DEFAULT_MODEL_ID` 和其属性/编解码方法，尚不能推断两函数应有的签名。处置：测试导出契约、明确兼容需求，然后补全实现或对外提供迁移说明；不凭静态名单直接删除。

## 关于 Dead Code 的准确结论

- **0** 个静态未引用私有函数候选，不等于任何代码都在真实训练中执行；`forward`、CLI、动态工厂、反射都会影响调用关系。
- **2** 个只在测试中静态调用的候选尚未随控制台输出提供函数名和文件，因此**不能指名、更不能删**。需从本机审计 JSON 按字段提取，并进一步对真实入口做路径级分析。
- **23** 个内嵌函数只有总量，缺少身份清单；不应以零嵌套为目标，有些闭包适合局部表达。需先检查是否捕获了外层可变状态、代码可读性和复用需要。

## 阶段验收与下一步

已知全量 248/248 tests PASS（62.136 秒；发生在这次只读扫描之前）。扫描自身只读，不改现有代码。本轮下一步：

1. 使用本地 JSON 提取 `test_only_static_call_candidates`、`nested_function_definitions` 和前 25 个 `complexity_hotspots` 的具体路径与行号，确定真实的重构清单。
2. 审计工具自身是 CC~48 第一热点：优先拆分 `scan()` 为文件 AST 收集 / 独立风险识别 / 用途引用分析 / 生成报表四个职责函数，保持字段 Schema 和结果恒等，再做完整 248 项回归。
3. 针对主训练 3B：先独立写一条本地 2 rank × 2 worker 真实 HF sharding 身份覆盖实验，然后实施研究-only 分布式 data fix；并审查 Checkpoint 反序列化、数据版本 pin 和 committed cursor，不能修改训练算法偷换问题。
4. 明确最小模型训练实验：用固定版本真实开发/验证数据和普通 Transformer 基线，记录训练 Token 数/算力/损失/PPL/生成样例；维护重构必须通过与模型输出一致性回归。

**当前结论：审计指标真实且优先顺序明确；尚未完成动态覆盖调查、删除代码、模型架构拆分，也未解决已识别的主训练 P0 风险。**
