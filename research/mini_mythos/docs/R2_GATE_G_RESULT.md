# R2 Gate G — 双逻辑 Worker 投机预取与优化器有序提交实测

**日期：2026-10-16；证据：用户 GitHub Codespaces 控制台日志。** 本报告没有下载用户本地 `results/r2` JSON 或模型二进制；结论依赖贴出的实际执行结果。

## 验收实测

- 完整 unittest：**156/156 PASS**，耗时 **4.183 秒**。
- 实验为 **2 个逻辑 Worker、0 个真实 OS Worker 进程**，本地固定合成数据，不是 HF FineWeb-Edu。
- 中断位置：`Committed cursor: 5`，`Dispatched frontier: 9`。
- 已经预取但**没有被优化器更新消费**的 Task IDs：`[5, 6, 7, 8]`。
- 若用最后派发位置作为恢复游标：会 **SKIP `[5, 6, 7, 8]`**。
- 正确恢复后首条任务：`First resumed task: 5`。
- 连续训练 vs 5+7 断点恢复：`Trace identical: True`、`Maximum abs loss difference: 0.0`。
- `Model params identical: True`、`AdamW optimizer identical: True`、`Committed cursor identical: True`、`Python/Torch RNG identical: True`。
- 明确未执行：`Real HF FineWeb-Edu: NOT_CONSUMED`，`Actual multi-process PR27 loader: NOT_TESTED`，`GPU training: NOT_PERFORMED`。

Checkpoint 及 JSON 用户本地记录位于 `research/mini_mythos/results/r2/pr27_gate_g_prefetch_comparison.json` 等 Git ignore 路径；没有上传到 GitHub。

## 结论

**Gate G：CPU 双逻辑 Worker 的有序提交协议及预取撤销恢复 PASS。** 已证明：应与模型/优化器/RNG 一起持久化的是**优化器已经成功执行的全局样本提交边界**，不是 Worker 派发或预取到的最大 Index。这是协议验证而非 PR27 原版修复。

尚未覆盖：实际 `torch.utils.data.DataLoader(num_workers=2)` 的子进程/队列、Stream shards 文件来源、异步 Worker 进度、真实 Hugging Face streaming 的复现、真实多 GPU/FSDP 训练。如果没有**可以按样本 ID 重新访问的不可变数据源**，保存 `next_committed_task_id` 并不自动保证能重新派发相同样本。

## 下一关：Gate H（真双进程 DataLoader，冻结本地数据）

设计一个受控、可重复的 **PyTorch DataLoader(num_workers=2,prefetch_factor=2)** CPU 运行，Worker 返回实际 PID/ID 并共享记录 fetch 次数；在 optimizer step 5 受控中断时证明确实存在 Worker 已读取但训练未消费的任务。使用可随机访问、内容 SHA 固定的**本地合成任务索引**，丢弃旧迭代器，按 optimizer committed Index 重建新的两 Worker DataLoader，从真实、安全的模型/Optimizer/RNG checkpoint 继续训练；与同样使用真实 DataLoader 的未中断路径比较逐位结果。新增测试应拒绝不一致来源和虚假 checkpoint。

**严格边界**：Gate H 即使通过，也只覆盖本地 indexed Dataset 和有序 DataLoader 输出；不代表 PR27 的 HF `IterableDataset` 原始数据流、无索引 Streaming shards、worker 状态和真正异常进程杀死均可恢复。GPU 训练仍未批准。
