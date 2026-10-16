# R2 Gate K — Hugging Face 原生 Worker 分片 + 独立 Token Packing：修复后实测结果

**实测日期：2026-10-16；证据：用户 GitHub Codespaces 控制台。** 曾在首次运行出现 187 项测试中 1 ERROR 的**双重分片**缺陷，详见 [Gate K Failure 001](R2_GATE_K_FAILURE_001.md)。修复后才得到本次通过结果；不应抹掉或覆盖此前失败证据。

## 修复后实测

| 验收指标 | 用户 Codespaces 实际输出 |
|---|---|
| 全量 unittest | **190/190 PASS（39.748 秒）** |
| 官方来源 | Gate I 已冻结的 **REAL FineWeb-Edu 32-document LOCAL snapshot** |
| Gate I snapshot SHA-256 | `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1` |
| HF IterableDataset | **LOCAL 2 Arrow shards, NOT live Parquet** |
| Worker 源分配规则 | `HF_ITERABLE_DATASET_NATIVE_AUTOSHARD_ON_TORCH_WORKERS` |
| 原始开发集覆盖 | 28 条，Worker0/Worker1 各 **14 / 14**；`Source docs covered once: True` |
| 连续路径 OS Worker PIDs | `[104872, 104897]` |
| 中断前路径 OS Worker PIDs | `[104934, 104975]` |
| 恢复路径 OS Worker PIDs | `[105014, 105061]` |
| Checkpoint Optimizer Commit | **5** |
| 已经由 Worker 预取但未提交窗口数 | **4** |
| 恢复后首个全局 Batch | **5** |
| Gate J global-pack vs Gate K worker-local-pack | 首 12 窗口 **11/12 不同** |
| 连续 12 vs 恢复 5+7 训练 Trace | **逐位相同 True** |
| 最大绝对 Loss 差 | **0.0** |
| Tiny 模型参数 / AdamW / Cursor / Python+Torch RNG | **全部一致 True** |
| 原始远端 HF IterableDataset 已恢复 | **False** |
| 正式模型质量评价 / GPU 训练 | **未执行 / 未执行** |

## 结论

**R2 Gate K — 修复后的本地 HF IterableDataset 原生自动分片、各 Worker 独立 Packing、真双 OS Worker CPU Tiny AdamW Checkpoint 恢复：PASS。**

本关具有两个具体价值：第一，按照优化器已提交的 Batch 位置（不是已经预取的 Worker 位置）从头重放本地来源并验证历史 Batch 内容 SHA，能重建逐位相同的训练结果；第二，实际证明了先全局 Pack 再发给 Worker 与先 Worker 分片再本地 Pack 是**不同的数据分布顺序**（11/12 窗口不同），后续公平对照时不可视为相同训练流。

**保留阻塞项：** 数据来自 32 条真实 FineWeb 文本的本地两分片 Arrow 快照，开发用 28 条非正式 Train/Heldout。不能证明 PR27 原版 `experiments/data.py` 显式 `.shard()` 在远端大量 Parquet 分片中正确消费全部源文件；不能证明其数据流可 O(1) 恢复；本关没有正式独立 Test/NLL/PPL、真实 SIGKILL/断电或 118M GPU 训练。

## 下一 P0：同一 HF 版本的真实多 Shard 覆盖对照

PR27 上游源码在 Worker 内手动 `.shard(num_shards=num_workers,index=worker_id)`；HF 的 `IterableDataset.__iter__` 又根据 PyTorch Worker 信息自行对 IterableDataset 自动分片。之前两分片快照因此出现一个 Worker 被关闭的明显错误；而在**多于两个来源 Shards 时，两个 Worker 仍可能全部活着，但部分源文档被静默漏读**。

新 Gate L 将使用相同的 Gate I 冻结来源**仅文档 SHA**，在本地创建 8 个 HF Arrow Shards，并让两个真实 DataLoader Worker 分别执行 A) HF 自动分片一次；B) PR27 风格“显式 `.shard()` + HF 自动分片”负控。比较来源文档覆盖、重复/遗漏、两个 Worker PID 是否都存在。**不启动模型训练、不访问 HF Hub、不提交文档正文。**

实际 Gate K 结果由用户 Codespaces 保存于 `research/mini_mythos/results/r2/pr27_gate_k_worker_pack_report.json`（Git ignored，本文不声称下载过报告原文件）。
