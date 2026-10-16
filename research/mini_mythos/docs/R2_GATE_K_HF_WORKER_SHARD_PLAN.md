# R2 Gate K — HF IterableDataset 每 Worker 分片后打包的真实双进程恢复

**2026-10-16；状态：研究层代码与 8 项新增测试已提交，尚未在用户 Codespaces 实测。** [Gate J](R2_GATE_J_RESULT.md) 实测 **179/179 tests PASS**，使用真实 HF FineWeb 文本的本地快照，在全局预打包 Map Dataset 上执行真实双 OS Worker 的 CPU AdamW 精确断点恢复。

## 与前一关相比，这次新增什么

上游固定 Commit [OpenMythos PR #27](https://github.com/kyegomez/OpenMythos/pull/27) 的 `experiments/data.py` 真正行为是：

```python
worker = get_worker_info()
num_workers = worker.num_workers if worker else 1
worker_id = worker.id if worker else 0
ds = load_dataset(..., streaming=True)
if num_workers > 1:
    ds = ds.shard(num_shards=num_workers, index=worker_id)
# 然后每个 Worker 自己 tokenize + EOS + buffer/pack
```

这和 Gate J **先把全部训练文档串起来全局 Pack，再按全局 Task Index 派发给 Worker** 有结构性区别。文档间 EOS 连接和 Batch 顺序可能不同。我们需要用真正 Hugging Face **`IterableDataset.shard()`** 及真实 OS DataLoader Worker 验证这项差异，而非延续 Gate J 的全局 Token index。

## 冻结来源

| 项目 | 值 |
|---|---|
| 真实内容输入 | Gate I 离线快照：32 条真实 FineWeb-Edu 文档（不会再次网络读取） |
| 官方 HF Dataset Commit | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| 快照完整 SHA256 | `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1` |
| 真实 GPT2 Tokenizer | HF Commit `607a30d783dfa663caf39e06633721c8d4cfcd7e`，Contract SHA `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9` |
| 内部开发分组 | 与 Gate J 相同的确定性 28 条训练 + 4 条排除，无正式测试集和质量评分 |

### 实验边界

1. 新 [r2_hf_worker_shard_pack.py](../scripts/r2_hf_worker_shard_pack.py) 先加载 Gate I/GTPT2 的所有不变条件，随后在**内存**构建 HF `Dataset.from_dict(...).to_iterable_dataset(num_shards=2)`。这是**本地 2 个 Arrow Shard** 的 HF 迭代接口，不是从官方远程 Parquet 文件得到原来的 2410 个 Shard。
2. 真正 PyTorch `DataLoader(num_workers=2,prefetch_factor=2,in_order=True)` 生成两个 OS 子进程；每个 Worker 在 `__iter__` 调用 HF `.shard(num_shards=2,index=worker_id)`，然后独立 tokenize、添加 EOS、打包 seq_len+1 移动窗口。Worker 返回自己的 Chunk SHA、局部序号、PID，仅将摘要/进程信息写入报告。
3. 恢复时**不依赖预取队列**：Checkpoint 在已成功完成第 5 次 `optimizer.step()` 后，将模型、AdamW、Python/Torch RNG、**全局已提交 5 条 Chunk SHA** 与冻结的 Source/Tokenizer SHA 保存到 Gate E 的安全权重文件和 Sidecar 中；重新启动双 Worker，从头依照相同分片/打包顺序逐条比较已提交 Chunk SHA 并跳过，再继续剩余 7 步。
4. 比较与控制：连续 12 Steps 和 5+7 Steps 的每步 Chunk SHA、随机 Loops、随机 Noise Mask、Loss、最终模型/AdamW/Cursor/RNG 必须逐位完全相同。还需观察**真实已读取但未提交** Chunk（可来自两个 OS Worker），并验证同样输入下，全局 Pack 与各 Worker 独立 Pack 的前 12 个 Chunk 摘要**至少存在一处差异**。
5. 所有报告只记录文件 Hash、Chunk SHA、Worker PID、训练状态一致性与统计，**不输出或 Git commit 原始真实文本**。

## Codespaces 执行

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_hf_worker_shard_pack.py --repo .
```

CLI 成功时应出现两名真实 OS Worker PID（每条连续/中断/恢复路径）；`Optimizer committed frontier: 5`；`First resumed global batch: 5`；`Global-pack vs shard-then-pack differing chunks: [大于0]`；`Bitwise equal trace: True`、Loss 差 **0.0**、Model/AdamW/Cursor/Python+Torch RNG 全部 True。

新本地证据，不覆盖 Gate I/J：

- `research/mini_mythos/results/r2/pr27_gate_k_worker_pack_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_k_worker_pack_cpu.manifest.json`
- `research/mini_mythos/results/r2/pr27_gate_k_worker_pack_report.json`

## Gate K 通过也不能关闭的上游问题

本实验仍然**不是**原版 PR #27 的真实 `HuggingFaceFW/fineweb-edu` 远程 `load_dataset(..., streaming=True)`：

- 本地只用 2 个 Arrow Shards，原始官方数据可能以众多 Parquet 文件/Shard 实现 `.shard()`；源文档属于固定 32 条。训练器中的 worker/shard 映射在两个数据源上不应假定相同。
- 恢复通过**从头重播 O(N) 个 Batch 并逐个校验 Chunk SHA**，只适合几十条本地样本，不是生产训练中数亿 token 的 O(1) seek。
- 没有真实 SIGKILL、Remote Range/Parquet File Offset、随机数据文件顺序、Worker 杀死后的 shard 再分配或崩溃时 Checkpoint 原子性证明。
- 没有正式独立 Heldout NLL/PPL、没有 118M GPU BF16 验证，也不能证明重建了 Anthropic Mythos 私有实现。

**通过 Gate K 的合理结论仅是：真实 HF IterableDataset 的本地 Worker 分片→Worker-local Packing，在双进程 CPU 小型训练下可按提交序号确定性恢复；生产 PR27 FineWeb Streaming 仍属于 P0 BLOCKED。**
