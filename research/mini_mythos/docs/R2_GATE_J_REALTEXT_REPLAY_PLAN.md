# R2 Gate J — 已冻结真实 FineWeb-Edu 文本 + 实际双进程 CPU 恢复实验

**制定日期：2026-10-16。状态：Gate J 已在用户 Codespaces 完成：179/179 tests PASS（26.679 秒），真实冻结 FineWeb 文本+GPT2+两名真实 OS Worker 的 12 vs 5+7 CPU AdamW 训练恢复全状态逐位一致。实测见 [Gate J Result](R2_GATE_J_RESULT.md)。本页保留原实验设计。** 上一关 [R2 Gate I](R2_GATE_I_RESULT.md) 已在 Codespaces 实测 171/171 tests PASS，真正官方 32 文档冻结、离线 SHA 一致。Gate H 的真实双进程 DataLoader/AdamW 断点恢复已在合成文本上 162/162 tests PASS。

## 目标和约束

将现有两个独立事实组合验证：

1. **Gate I 的真实来源**：`HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train`，冻结 40 位 dataset SHA `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，本地快照 SHA-256 `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1`，**32 条、111361 字节源文本、119588 字节快照**。
2. **Gate D 的真实 Tokenizer**：官方 GPT2 `gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`，完整 Contract SHA-256 `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`，Embedding rows 50257。
3. **Gate H 的真实 Worker 恢复技术**：PyTorch `DataLoader(num_workers=2,prefetch_factor=2,in_order=True)`，三个独立迭代器（连续、5-step 前缀、7-step 恢复）中观察不同 OS Worker PIDs 与已取未提交任务；断点 checkpoint 安全绑定 Tokenizer SHA、权重 SHA、模型、真实 Tiny AdamW 优化器、Python/Torch RNG 与 optimizer-committed task ID。

### 本轮实测输入如何保证不会悄然改变

新 [r2_fineweb_local_replay.py](../scripts/r2_fineweb_local_replay.py) 先运行 Gate I 的完整 JSONL/Manifest 校验，再以**脚本中固定的外部 SHA**核对 dataset revision、文件摘要、两个字节数、源行编号必须 0..31、许可证 metadata `odc-by`。不能仅靠被同时重写的 JSONL 和 manifest 两者互相验证。

只在全部前置检查通过后，派生可重播的内部 Document ID：dataset SHA + 源行号 + text SHA。将原样文本传给 Gate H 的 `split_documents`/`immutable_indexed_tasks`，并复用 Gate H 的真实双进程训练恢复验证。源码和生成的文档/Token 不会提交到 GitHub；报告只存统计和 SHA。

**注意实验内部保留部分文档只是为训练恢复流水线做确定性的隔离，不是正式独立 Heldout/Test**：所有 32 条都来自已知用于调试的同一个 HF `train` 数据集。保留组**不评分、不参与正式模型性能或质量声明**。这轮 Tiny 4D Embedding/Head 的 AdamW 会在部分真实 FineWeb 文本上训练 12 步，因此严格说它是**小型 CPU 训练管线 smoke**，不是“大模型训练”、也不是“只读取、不训练”。

## Gate J 通过条件

- 全量单测通过；Gate I 文件 Hash/SHA/字节数完全匹配，不会意外读取线上变动后的 `main`。
- 离线加载已经冻结的 GPT-2 Tokenizer，重新计算并比较完整词表/Backend/特殊 Token ID 身份。
- 从 32 条真实 Text 得到固定来源/顺序的 Packed Sequence Index；内部实验中训练和暂时排除的文档 ID 不重复。
- 三条真正 DataLoader 路径均启动并观察**两个不同 Worker PID**；至少一个 Worker 已读取但 optimizer 尚未消费的 Batch 在第 5 步被重放。
- 连续 12 步与 5+7 步恢复：Trace、Tiny 模型参数、AdamW、已提交的全局任务索引、Python/Torch RNG **逐位完全一致**，最大 Loss 差值 0.0。
- 文件错误、原始文本改变、Dataset Commit SHA 不匹配、Token ID 变更必须阻止任何训练/Checkpoint 加载。
- 输出文件的统计不得包含真实网页文本、原始文档 ID 或超过本实验所需的 Token Payload。实验不进行 NLL/PPL 或自由文本质量评估。

## Codespaces 运行

下面只访问**已有的本地 Git 忽略快照**，不会重新读取 Hugging Face 在线 Streaming 数据；不需要再次运行 Gate I `freeze`。

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_fineweb_local_replay.py --repo .
```

脚本保留已验收的 Gate I 原始文件，不覆盖以前的 Gate H 数据；输出三个独立的本地 Git 忽略文件：

- `research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_j_realtext_cpu.manifest.json`
- `research/mini_mythos/results/r2/pr27_gate_j_realtext_replay.json`

预期日志包含 `REAL pinned FineWeb-Edu 32-doc LOCAL snapshot`、固定数据/Tokenizer SHA、真实 Worker PIDs、First resumed Task 5、`Trace bitwise identical: True`、`Maximum absolute Loss difference: 0.0`、`AdamW identical: True` 等。**尚未实测，不提前宣称 PASS。**

## 不能称为生产 Streaming 恢复

本实验是将 32 条真实文本**提前构造成索引 Token Task**后，通过 Map-style Dataset 的真实双进程 Loader 使用，**不是** PR27 原始的 HF `IterableDataset`；上游原版每个 Worker 独立调用 `ds.shard(...)` 后分别 Pack Tokens，本实验则先全局 Pack，再按 global Task Index 通过 DataLoader 派发，**分片边界、跨 Worker 文档连接及原始训练数据顺序可能不相同**。

它还没有测试真正 SIGKILL/进程崩溃、文件 shard offset、随机 shuffle、跨机器恢复、多个 epoch、真实独立验证集、模型 NLL/PPL 或 118M GPU 训练。通过 Gate J 后，下一 P0 仍是对不可变 HF Parquet shard 及真正 `IterableDataset` 分片位置、prefetch、已消费全局 Batch ACK 的可恢复性进行故障注入与独立 Heldout 设计。
