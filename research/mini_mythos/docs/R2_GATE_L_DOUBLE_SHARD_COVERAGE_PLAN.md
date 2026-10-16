# R2 Gate L — 多分片 HF IterableDataset 的真实双进程来源覆盖 A/B 审计

**制定：2026-10-16。状态：已经在 Codespaces 完成 197/197 tests PASS（48.077 秒），真正两个 OS Worker 均运行时，HF 原生分片覆盖 28/28，重复分片只覆盖 14/28，静默漏读 14 条。完整证据见 [Gate L 实测](R2_GATE_L_RESULT.md)。本页保留实验前方案及约束。** Gate K 修复后已在用户 Codespaces 确认 **190/190 PASS**：2 个真实 OS Worker 各 14 条开发来源文档（共 28/28 覆盖）、预取 4 个未提交 Token Windows、5+7 vs 12 Step CPU Tiny AdamW 恢复 Trace/Model/AdamW/Cursor/RNG 完全一致，Loss 差 0.0。详见 [Gate K Result](R2_GATE_K_RESULT.md)。

## 要解决的真实风险

PR27 固定源码 `experiments/data.py` 在 PyTorch DataLoader Worker 内显式对 Hugging Face Streaming Dataset 调用 `ds.shard(num_shards=worker.num_workers,index=worker.id)`，之后再迭代 `ds`。但当前 Hugging Face `datasets.IterableDataset.__iter__()` 在同样的 Worker 上也调用 `_iter_pytorch()`，执行**第二次**按 Worker ID 的数据源分片。

Gate K 首次版本由于只创建 2 个本地 Shards，显式分片后 HF 认为只有 1 个 Shard，警告 `Too many dataloader workers` 并停掉一名 Worker，导致测试立即失败。**上游真实来源可能拥有大量 Shards，两名 Worker 都能运行却仍有数据被跳过**，这必须用独立的来源文档覆盖率测试才能看见，而不是看 PID 数或 Loss 是否下降。

## 本轮冻结对照（不训练）

| 维度 | 规则 |
|---|---|
| 正式真实输入 | Gate I 固定 `HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train` 的本地 32 文档快照，源 SHA `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| 快照 SHA256 | `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1` |
| 内部文档分组 | Gate J/K 同样 28 开发文档 + 4 排除，仅数据加载协议，无独立 Model Test |
| Worker 输入 | **只传每条真实文档的 ID SHA256**，不把原始文本传入 Worker |
| 本地源 | HF `Dataset.from_dict(...).to_iterable_dataset(num_shards=8)`，只包含 28 个 Document Hash |
| 实际 Worker | Linux PyTorch `DataLoader(num_workers=2,prefetch_factor=2,in_order=True,batch_size=None)`，两个**真实 OS 子进程** |
| A 组（正确） | `native_once`：Worker 不手动分片，让 HF 原生 `_iter_pytorch()` 自动分配原始 8 Shards |
| B 组（PR27 型错误） | `explicit_twice`：每 Worker 显式 `.shard(2,worker_id)` 后，HF `_iter_pytorch()` 再自动 `.shard(2,worker_id)` |
| 共同验收 | 两组必须都实际看到 2 个不同 Worker PID、无重复/未知记录；A 覆盖所有 28/28；B 若产生**漏读但不抛错**，记录具体遗漏的开发文档顺序索引与数量 |

**重要**：这是本地 **8 个 Arrow Shards** 的受控反例，不是在线完整 FineWeb Parquet 文件和远程 2410 个文件的实测。即使 B 组恰好漏读 50%，也不能据此推断真实上游训练必然漏读相同百分比；那个比例取决于真实 shard layout、worker policy 和所固定的 HF datasets 版本。

## 代码与执行命令

[实验程序](../scripts/r2_pr27_double_shard_coverage.py) 及 [离线/真双进程回归测试](../tests/test_r2_pr27_double_shard_coverage.py) 已提交，不会读取 HF Hub、不会访问模型权重，也不会改动上游 PR27。

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_double_shard_coverage.py --repo .
```

在 Codespaces 里上报：真实 Worker PIDs、`Native source document coverage`、`Explicit + HF auto coverage`、`SILENT missing source documents` 和其内部训练顺序索引。注意确认 `Native covered once: True`，不只查看 Worker 都启动。

本地新证据（Git ignore，拒绝覆盖）：

`research/mini_mythos/results/r2/pr27_gate_l_double_shard_coverage.json`。

**当前 Gate L 代码尚未在 Codespaces 运行**，上面的覆盖结果只能作为待检验的假设，不能预先写“28/14”、“漏读一半”等结论。

## 下一项真正的生产级证据

在 Gate L 本地八分片 A/B 通过后，应审计 PR27 固定的真实 HF `sample-10BT` Dataset：固定 installed `datasets`/`torch` 版本、真实 Parquet Shard 文件列表及顺序、Worker 双重分片操作后每 Worker 可见的来源 shard ID、是否重复/遗漏；在可控且有流量预算的条件下实测远程小范围源文档索引。之后把**只分片一次**、不可变 Source Revision、真正 Shard/Document Offset 与优化器已提交 Batch ACK 整合到独立 PR27 训练研究副本，并增加真实 Worker SIGKILL/恢复故障注入。

不能因为 Gate L 通过就声称修复了 Anthropic 私有 Mythos、PR27 118M GPU 训练已可运行，或已经获得真实独立测试集性能指标。
