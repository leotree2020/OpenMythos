# R2 Gate H — 真实双 OS 进程 PyTorch DataLoader 恢复实测

**2026-10-16。证据：用户 Codespaces 终端日志。** 此报告只是终端结果的文本归档；二进制 checkpoint 与原始 JSON 均留在用户 Codespaces Git 忽略目录，没有上传至 GitHub。

## 验收结果

- **162/162 单元测试 PASS**，用时 **14.719 秒**。
- 真正 Linux PyTorch DataLoader，每次运行中观察到**两个真实且不同的 OS 子进程 PID**：
  - 连续 12-step 路径：`[82311, 82312]`
  - 中断前 5-step 路径：`[82348, 82349]`
  - 保存/重新创建模型与 DataLoader，恢复剩余 7-step 路径：`[82398, 82399]`。
- 控制参数：`num_workers=2`、`prefetch_factor=2`、`in_order=True`，共享的 Dataset `__getitem__` fetch counter 实际记录 Worker 已提前读取但训练未使用的任务。
- Checkpoint 的**优化器已提交下一任务 ID = 5**；真实读取后尚未提交的 Task IDs 是 **`[5, 6, 7, 8]`**。
- 若错误地采用最后 Worker fetch 的位置继续，任务 `[5, 6, 7, 8]` **全部遗漏**；正确重新创建 DataLoader，从 Task **5** 开始。
- **`Trace bitwise identical: True`**；`Max abs loss difference: 0.0`；Model params、AdamW state、Committed cursor、Python/Torch RNG 的最终状态全部**逐位一致**。
- 数据：**LOCAL INDEXED SYNTHETIC, NOT FINEWEB**；上游 PR27 streaming loader **没有修改**，没有 GPU 训练。

## 研究结论

**R2 Gate H：真正双进程、预取状态可观察、受控重新建迭代器的 CPU 精确恢复 PASS。** 比 Gate G 的两个逻辑 Worker 更进一步：PyTorch 确实启动了子进程，并真实观察到未提交的预取。原则是保存模型/优化器/RNG 同步的**提交游标**，而不是持久化 Worker 中的派发/读取位置；前提是原始数据能够按固定全局 task ID **确定性重放**。

### 不可过度延伸

- 数据提前经过本地 PR27 形状文档、冻结 GPT-2 tokenizer 转成可索引、内容可校验的 Map-style Task 列表；**不是**原版 Hugging Face FineWeb-Edu 的 `IterableDataset`。
- 这是受控终止/重建 DataLoader，而非 SIGKILL、断电或中断容器；没有保证双写的 Checkpoint/Optimizer commit 在异常电源故障中原子完成。
- 每次 Worker 进程不同是正常现象；不要求同一个 task 仍由原 worker 加载，只要求 payload 和优化器 RNG 一致。
- 尚未固定和重建 FineWeb-Edu 仓库的不可变数据版本、source shard、文档 ID、文档边界或真实多 Worker IterableDataset 的分片进度。因此 **PR27 正式数据恢复 P0 仍未关闭**。

## 下一关：Gate I（真实 FineWeb-Edu 数据源冻结，限量读取）

先不训练，也不直接在真实 HF IterableDataset 上实施多 Worker 重启。根据上游 PR27 `experiments/data.py` 实际源码，正式来源是 `HuggingFaceFW/fineweb-edu`、`sample-10BT`、`train`，使用 Streaming，并在各 Worker 内调用 `ds.shard(num_shards=2,index=worker_id)`；**当前 loader 没有为 HF source 固定 revision、Shard/Doc 位置及已消费 Task commit**。

新增 [Gate I 计划](R2_GATE_I_FINEWEB_SNAPSHOT_PLAN.md) 与 [限量冻结工具](../scripts/r2_fineweb_source_snapshot.py)：在消费文档**之前**通过 HF Hub 把数据仓库 Revision 解析成 40 字不可变 Commit SHA，只抓取源顺序中最前面的 **32 条合格文档**，建立本地快照及每条 ID/Text SHA，离线独立验证。文本只留在 Git 忽略目录；单文档和总文本大小均有限额。不获取模型权重，也不训练任何 OpenMythos 大模型。

此步骤只能验证数据源身份和可重放的**小范围本地真实文本样本**，不能证明全量 HF Parquet shard 的索引、范围请求或真实 worker 恢复；后续必须继续进行专门的在线数据完整性和恢复故障实验。
