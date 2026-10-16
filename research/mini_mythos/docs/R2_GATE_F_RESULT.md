# R2 Gate F：单 Worker 数据游标与真实 Optimizer 的逐位恢复结果

**日期：2026-10-16。实测来源：用户 GitHub Codespaces 终端日志。** 实测机器无 CUDA GPU；本项目没有独立下载用户 Codespaces 本地的 JSON 或二进制 Checkpoint。

## 实际验收

- `unittest`：**148/148 PASS（4.110 秒）**。
- 数据：本地生成的 64 条 PR27 形状 `id/text` 合成文档，确定性划分 **55 Train / 9 Heldout**，并非 FineWeb-Edu；Heldout 没参与这个训练一致性实验。
- Tokenizer：真实已缓存的 `gpt2` FastTokenizer，固定 Contract SHA256 `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`。
- 对照：连续 Tiny AdamW 训练 12 steps，和前 5 steps 后写入 Tokenizer Bound `.pt` + Sidecar SHA256，再独立恢复后 7 steps。
- `Trace same across restart: True`、`Maximum abs loss difference: 0.0`。
- `Model parameters bitwise identical: True`、`Optimizer state bitwise identical: True`。
- `Data cursor bitwise identical: True`、`Python/Torch RNG state identical: True`。
- 这条路径要求真实 `weights_only=True` 安全读取、Gate E Tokenizer Contract 及严格 replayed 单 Worker packer cursor；上游源代码没有修改。

## 结论与未解决的 P0

**R2 Gate F：CPU 合成单 Worker 的端到端精确恢复 PASS。** 这是对 Checkpoint→数据位置→优化器→随机计算一致性的扎实验证；但不能把它升级为真实 FineWeb-Edu Streaming 已恢复，也不能证明训练集没有重复文档。

用户日志明确：`Original PR27 multi-worker Streaming loader modified: False`；`Real FineWeb-Edu consumed: False`；`118M GPU training performed: False`。

剩余风险在 PyTorch `DataLoader(num_workers=2)` 与 HF streaming 上：Worker 可能已经把后续数据**预取并写入队列**，但训练器仍停在较早的**已完成优化器 Step**。如果按“最后派发”或“Worker 已扫描到的位置”恢复，就可能跳过中断前没有实际用于更新模型的样本。不能用单 Worker 轨迹等价代替这个测试。

## 下一步：Gate G（隔离 CPU 有序提交/预取模拟）

新增研究层 Gate G 计划模拟两 Worker 的独立预取、完成顺序乱序以及训练中断，使用**全局已提交样本序号**作为持久化游标，在 checkpoint 中保存由 optimizer 更新确认过的位置，从同一不可变顺序任务清单重新派发未提交的数据。

验收：异常预取任务被丢弃后训练轨迹、模型/优化器、随机数与原连续训练逐位相同；故意把游标存成最后派发 Index 的对照必须显示漏数据；数据来源、任务 Hash、Tokenizer Contract 和 Worker 分片策略漂移必须 fail closed。

**Gate G 模拟器不等同于真正启动了 2 个 DataLoader 子进程，更不是修复了 HF FineWeb-Edu 多 Worker 预取队列。** 这是为下一步上游隔离副本改造和生产 Loader 真实故障注入建立正确的最小协议。

当前 Gate F 本地结果：`research/mini_mythos/results/r2/pr27_gate_f_stream_comparison.json`（Git ignore，未上传）；本 Markdown 文档仅存证用户已提供的控制台输出。
