# R2 Gate G — 预取任务与已提交训练位置分离（双逻辑 Worker CPU 故障注入）

**设计日期：2026-10-16；状态：已在用户 Codespaces 实测通过，156/156 tests PASS，任务 5–8 已预取未提交，真实恢复从任务 5 开始且训练轨迹/模型/AdamW/RNG 全部逐位一致。完整日志归档见 [Gate G Result](R2_GATE_G_RESULT.md)。本页保留实验前的方案。** 继 [R2 Gate F 已验证结果](R2_GATE_F_RESULT.md)：148/148 tests PASS，CPU 单 Worker 的真实 Tiny AdamW 模型、优化器、数据 packer 游标和 Python/Torch RNG 在 12 vs 5+7 步恢复中完全一致。

## 为什么要继续这一关

上游 PR27 对 FineWeb-Edu 采用 `DataLoader(num_workers=2)` 并有预取。若训练在 optimizer step 5 提交后突然中断，Worker 可能已经扫描到 batch 9，并把 5–8 送到预取队列。如果把**最后派发的 Batch ID 9**作为恢复位置，就会跳过从未参与优化器更新的 5、6、7、8。

**关键协议：Checkpoint 必须记录与模型/优化器状态同一提交点的 `next_committed_task_id`，而不是 DataLoader Worker 自己已经读取或返回到缓存的最后位置。** 这些尚未提交的数据是可丢弃的投机性读取，需在同一个固定输入顺序重新派发。

## 本轮限定范围

新增 [r2_pr27_prefetch_commit.py](../scripts/r2_pr27_prefetch_commit.py) 和 [回归测试](../tests/test_r2_pr27_prefetch_commit.py)。

- **数据**：本地合成的 `id/text` 固定文档（原 Gate F 形状），真实已经冻结的 GPT2 Tokenizer，按 PR27 的 EOS/长度 17 窗口规则先生成不可变带 SHA256 的全局任务 ID。此**提前索引**是必要实验前提，不意味着真实 HF Streaming 已有随机访问或持久化索引。
- **Worker 模型**：模拟两个逻辑 Worker，`worker_id=task_id % 2`，固定预取深度 4，故意按倒序完成已派发任务，然后由主训练器**严格按全局编号**使用任务；**没有 OS 进程或 PyTorch 多进程队列**。
- **训练**：Tiny 4D、50257 行 Embedding/Head + 真实 CPU AdamW；每个训练步仍有 Python Random 的循环次数以及 Torch Generator 的随机 Mask。
- **故障**：连续训练 12 steps 对照在 committed step 5 把模型/优化器/RNG/`next_committed_task_id` 写入 Gate E 的安全 `.pt` + SHA JSON sidecar，已派发且完成但尚未用于 `optimizer.step()` 的任务被丢弃。
- **恢复**：从不可变的任务清单按 committed ID 重新建预取队列，严格核对来源 SHA、Tokenizer Contract、任务 SHA、Worker policy、Cursor checksum；新训练器继续 7 steps。
- **比较**：要求每一步 Task ID、Worker ID、Token digest、随机 Loop、随机 Mask、Loss、最终模型参数、AdamW 状态、Cursor 与 Python/Torch RNG 完全一致；并显示“错误地从 dispatch frontier 继续”所跳过的任务编号。

## 在 Codespaces 执行

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_prefetch_commit.py --repo .
```

期望观察到 `Workers simulated: 2`、`OS worker processes: 0`、`Committed cursor: 5`、`Dispatched frontier: 9`（如果这项实现没有改动）、`Naive dispatched-frontier resume would SKIP: [5, 6, 7, 8]`、`First resumed task: 5`，以及 Trajectory / Model / AdamW / Cursor / RNG 五项严格一致。

写入新文件，不覆盖前面 Gate F：

- `research/mini_mythos/results/r2/pr27_gate_g_prefetch_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_g_prefetch_cpu.manifest.json`
- `research/mini_mythos/results/r2/pr27_gate_g_prefetch_comparison.json`

## 正确解释结果

Gate G 即使通过，也只说明**我们构造的双逻辑 Worker、确定性任务索引与有序提交协议**，能够在 CPU 合成数据中保持严格重放。不能据此声称原版 `DataLoader(num_workers=2)` 可恢复、真 FineWeb-Edu 的 IterableDataset shard/worker 的未消费缓冲已被持久化，也不能证明 GPU 并行训练确定性。

PR27 真正生产修复必须解决真实 FineWeb-Edu 的不可变 revision/shard ID、真实 DataLoader worker/prefetch 队列、已消费的 batch ack 与 optimizer checkpoint 的原子性，以及严格 Train/Heldout 划分。需另做真正子进程故障注入与多 shard 测试。**在此之前仍禁止宣称 118M GPU 实训准备度 PASS。**
