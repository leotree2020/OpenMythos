# R2 Gate J — 冻结真实 FineWeb-Edu 文本与双进程 CPU 断点恢复：实测

**2026-10-16，用户 GitHub Codespaces 终端日志。** 本报告只存数值、不可变版本、hash 和 PID；真实网页文本与模型 Checkpoint 留在用户 Git 忽略目录，未上传到 GitHub。

## 实测结果

| 项目 | 观测值 |
|---|---|
| 全量 unittest | **179/179 PASS（26.679 秒）** |
| 真实数据源 | `HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train`；来自 Gate I 已冻结的**本地**32 文档快照 |
| HF Dataset 不可变 SHA | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| 快照 SHA-256 | `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1` |
| GPT-2 Tokenizer Contract SHA | `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9` |
| 内部协议训练/排除文档 | **28 / 4**；不是正式 Test/Heldout 数据集 |
| Tiny CPU AdamW | 在真实文本 Token 上完成 **12 steps**；只验证训练管线，无模型质量评估 |
| 连续训练 Worker PID | `[94224, 94225]` |
| 中断前 Worker PID | `[94269, 94270]` |
| 恢复后 Worker PID | `[94298, 94299]` |
| Checkpoint 提交游标 | Step **5** |
| 已预取未提交任务 | `[5, 6, 7, 8]` |
| 恢复后第一个 Task | **5** |
| 训练 Trace | **bitwise identical=True** |
| 最大 Loss 差值 | **0.0** |
| 模型参数 / AdamW / Cursor / Python+Torch RNG | **全部 identical=True** |
| 线上 HF 网络请求 | **无**（复用本地快照） |
| GPU 训练 | **未执行** |

## 结论与限制

**Gate J：不可变真实 FineWeb 小样本文本 → 不可变真实 GPT-2 Tokenizer → 预索引全局 Token Tasks → 真实双 OS Worker 的 DataLoader → Tiny CPU AdamW/Optimizer/随机数与提交游标的断点恢复，全流程 PASS。**

**重要：Gate J 实际做了 12 步小型 CPU 训练管线测试，不能称为“没有训练”，但没有评估语言模型能力。** 全部真实文本来自官方 FineWeb `train` Split 的开发用快照；4 份被内部排除的文档不是正式独立验证集或测试集。

不代表上游 PR #27 原版 HF `FineWebEduStream(IterableDataset)` 已可恢复。Gate J 是**全局提前 Token Packing → 可索引 Map Dataset**；PR27 原版是 **HF Worker 分片 → 每 Worker 单独 Token Packing → DataLoader 合并各 Worker 输出**。两者的文档连接方式、Token 数据顺序及重放位置可能不同，必须在下一关专门验证。没有执行真实 HF Parquet shard 断点定位或异常 SIGKILL 故障注入，原版数据恢复 P0 仍 BLOCKED。

## 本地证据（未上传）

- `research/mini_mythos/results/r2/pr27_gate_j_realtext_replay.json`
- `research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.manifest.json`

下一项 Gate K 应使用同一已冻结真实数据和 GPT-2 Tokenizer，以实际 `IterableDataset + DataLoader(num_workers=2)` 做**每 Worker 独立分片和打包**，对比 Gate J 的全局预打包任务 SHA；之后才讨论 HF 原版 shard 索引/seek 和真正 abrupt-kill 事务恢复。
