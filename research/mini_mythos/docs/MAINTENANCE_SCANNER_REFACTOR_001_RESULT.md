# 维护性审计重构 001 — Codespaces 真实验收结果

**2026-10-17 用户 Codespaces 执行：全量 `248/248 PASS（62.335 秒）`；新版本只读 AST 全仓扫描成功。** 与首次扫描的 `248/248 PASS（62.136 秒）` 为两个独立结果，数值勿混用。

## 精确的新旧对比

| 读数 | 原版扫描 | 重构后扫描 | 解释 |
|---|---:|---:|---|
| Python 文件 | **105** | **105** | 文件总量未变 |
| 函数及方法 | **889** | **893** | 扫描器自身新增 4 个顶层辅助函数 |
| 静态复杂度热点 | **85** | **87** | 整体热点数 **增加 2**，不能宣传全面下降 |
| 嵌套函数定义 | **23** | **23** | 未改动嵌套函数 |
| 风险模式 | **5** | **5** | 模式计数不变 |
| 无绑定 `__all__` 名称 | **2** | **2** | 尚未修复 |
| 仅测试静态调用候选 | **2** | **2** | 尚未判断为死代码 |
| 未引用私有函数候选 | **0** | **0** | 不表示全项目没有死代码 |

**实质变化：** 最初 Top-1 `maintenance_ast_audit.py:scan` 约 CC~48、110 行，拆分后**已从用户终端 Top-12 最高复杂度名单中消失**。新的 Top-1 是 `r2_fineweb_source_snapshot.py:check_manifest_and_snapshot` CC~41；第二位主训练 `training/3b_fine_web_edu.py:main` CC~33。虽然最坏单函数复杂度下降，整体热点数从 85 增至 87；原因可能是拆出的多个辅助函数达到热点阈值，需要比对明细 JSON 才能归因，不能把猜测写成事实。

原审计文件：`research/mini_mythos/results/quality/ast_audit_2026-10-17.json`；新审计文件：`research/mini_mythos/results/quality/ast_audit_refactor_2026-10-17.json`。这两个文件存于 Codespaces 的 Git ignored results，研究仓库没有 JSON 原始数据。控制台虽确认总计数与风险模式相同，**尚不能证明所有非审计器字段逐项一致**，以后可做报告字段去除 self-file 后的结构 diff。

## 用户回传的两个“仅测试调用”候选：人工复核

1. `research/mini_mythos/scripts/r2_pr27_native_once_data_candidate.py:113 build_loader_native_once`：这是 Gate Q 研究候选加载器 API；目前主训练确实尚未调用它，仅由单元测试直接调用。**保留**，视为功能尚未接入/研究接口，而非无用代码。待真实训练整合时再判断弃用旧入口。
2. `research/mini_mythos/scripts/r2_pr27_spawn_local_fixture.py:27 load_local_hf_dataset`：这是 `install_local_source_in_spawn_worker` 内通过 `candidate.load_dataset = load_local_hf_dataset` 注入的函数对象。扫描器依照函数调用语法统计，漏掉这种回调引用，因此**属于静态分析的已解释假阳性**，必须保留以确保 spawn 子进程安全的本地数据工厂。

## 23 个嵌套函数的分类

真实名单已由用户回传，**无需再次向用户索要同一份信息**。其中大多数为短小作用域函数或测试/benchmark 内的局部辅助（例如 `once/stats`、`mean/avg/loss`、`run/one_run`、`rope_at/cache_bytes`），另有临时 Hook/mask override (`on_act`, `intervention`, `mask_override`)——**不能只因嵌套就移除**。

高优先级审查的是研究恢复协议中三个 `cursor()` 闭包：

- `research/mini_mythos/scripts/r2_hf_worker_shard_pack.py:355 compare_worker_shard_resume.cursor`
- `research/mini_mythos/scripts/r2_pr27_real_dataloader_resume.py:309 compare_actual_multiprocess_resume.cursor`
- `research/mini_mythos/scripts/r2_pr27_stream_resume.py:307 compare_uninterrupted_with_resume.cursor`

还有 Worker 分片投影中局部 `audit`：`r2_pr27_live_hf_shard_metadata.py:68` 和 `r2_pr27_remote_parquet_inventory.py:84`。它们未必不合理；只有在确认可简化父函数的数据/状态依赖并有严格回归后才移动。

## 当前风险和下一步

源训练 `training/3b_fine_web_edu.py` 的 P0/P1 仍未修复：DDP rank × Worker 分片与 HF auto、浮动 Dataset Revision、`torch.load(weights_only=False)`，以及从头重读而非已提交任务恢复。根包 `open_mythos/__init__.py` 的两个不存在 `__all__` 名称也是确切接口异常。下一次可选择**最小公开 API 修复（去掉不存在的 star-export 条目）加真实 import smoke tests**，不修改模型数学/训练；其他风险分开处理，不能一次全部删除旧代码。

## 证据层级声明

这些数字属于项目自建 AST 近似复杂度，而不是代码覆盖率、性能基准或实际未调用证据；Gate Q、R2 数据分片本地测试不能代替线上远程 FineWeb Parquet 数据/Token 级训练。修复尚未发生的代码不得宣称 VERIFIED。
