# R2 Gate H — 真实双进程 PyTorch DataLoader 的预取中断与断点恢复

**制定日期：2026-10-16。状态：研究层实验脚本及测试已提交，尚未在用户 Codespaces 运行。** 前一关 Gate G 已经在两个**逻辑** Worker 的单进程模拟中通过 156/156 项测试，但原始 PR27 使用的是实际 `DataLoader(num_workers=2)`，必须另行验证。

## 本轮核心问题

一个 Worker 可以在训练器第 5 次 `optimizer.step()` 已完成时，提前 fetch 任务 5、6、7、8。Dataset 内部的 `__getitem__` 已经执行，**但模型/优化器并没有提交这些任务**。正确做法是把和 checkpoint 权重/优化器一致的 **`next_committed_task_id=5`** 作为唯一持久游标，重启后创建新 DataLoader、按确定顺序重新读取原来被预取的任务。

## 相对于 Gate G 的新增真实覆盖

新 [r2_pr27_real_dataloader_resume.py](../scripts/r2_pr27_real_dataloader_resume.py) 使用真正的 PyTorch `DataLoader(num_workers=2,prefetch_factor=2,in_order=True)`，Linux `spawn` 启动真实 OS 子进程。Dataset `__getitem__` 将读次数写到共享 `multiprocessing.Array`，同时返回 `os.getpid()` 和 `torch.utils.data.get_worker_info().id`，要求实际训练消费来自**不同 PID 的两个 Worker**。

实验仍使用**本地合成的 PR27 形状文档**，先按真实冻结 GPT2 Tokenizer、EOS/packed-window 规则构造成不可变索引 Task。该预索引是研究层的故意限制：真正 Hugging Face FineWeb-Edu Streaming 还没有随机访问 task-id 或可靠的 shard/document offset，因此不能把实验复制到原版 loader 就认为已修复。

### 冻结实验协议

| 控制项 | 固定条件 |
|---|---|
| 数据 | 64 条本地合成文档；Train/Heldout ID 散列严格分开 |
| Tokenizer | 原 Gate D 合约冻结的真实 GPT2，revision `607a30d783dfa663caf39e06633721c8d4cfcd7e` |
| 真实进程 | Linux PyTorch DataLoader 2 个 spawn Worker，prefetch_factor 2，ordered output |
| 训练器 | Tiny CPU Embedding/Head + AdamW + Python Loop RNG + Torch augmentation Generator |
| 比较 | 连续 12 optimizer steps vs 5 steps checkpoint+创建新的真实双进程 DataLoader+7 steps |
| 保存 | Tokenizer-bound Checkpoint、外部 SHA256 Sidecar、source/task digests、`next_committed_task_id` |
| 中断 | **受控结束旧 DataLoader 迭代器**，未执行 SIGKILL/真实电源故障 |
| 数据身份 | 逐任务 SHA256、按全局 Index 顺序复读，不要求 Worker PID/ID 在恢复前后相同 |
| 通过条件 | 原训练器和恢复训练器的模型/AdamW/Cursor/Python+Torch RNG/Trace **逐位一致**，Loss 差 0；在断点处观测到真实 OS Worker 已 fetch 但训练器未提交的 task |

研究脚本中的 Shared Read Counter 只是测试证据，**不是**生产持久数据游标；不会访问私有 DataLoader Queue、`_send_idx` 或 `_rcvd_idx`。Worker PIDs 与分配顺序可以在重启后变化，不纳入模型结果的 bitwise 比较。要得到一致训练结果，只需要确认 Token Payload 与训练器 RNG 一致，而不是同样由哪个 Worker 读取。

## Codespaces 实际执行

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_real_dataloader_resume.py --repo .
```

完整单测中包含一项会**真的启动两个 DataLoader 子进程**的集成测试，因此可能比此前 4 秒的测试运行更久；其余回归只检查源 SHA、Checkpoint Cursor、索引数据与损坏拒绝。CLI 将为连续、前缀和恢复三条路径分别启用一组真实 Worker；必须在日志中看到各有**两个不同 OS PID**。

验收日志应包含：

```text
Actual OS worker processes: 2 per real DataLoader run
Committed frontier at checkpoint: 5
Actually fetched but uncommitted: [至少一个 >=5 的 task ID]
First replayed task after resume: 5
Trace bitwise identical: True
Max abs loss difference: 0.0
Model params bitwise equal: True
AdamW state bitwise equal: True
Committed cursor bitwise equal: True
Python/Torch RNG bitwise equal: True
Data source: LOCAL INDEXED SYNTHETIC, NOT FINEWEB
Actual PR27 streaming loader patched: False
GPU training: NOT_PERFORMED
```

本关不强制 Worker 预读的最大索引一定是 8：真实 PyTorch 调度异步，观测时间会影响 Worker 已 fetch 的数量；**不可凭空把真实观测强行改成 Gate G 模拟的 5–8**。

### 输出文件（Git ignored，拒绝覆盖）

- `research/mini_mythos/results/r2/pr27_gate_h_real_loader_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_h_real_loader_cpu.manifest.json`
- `research/mini_mythos/results/r2/pr27_gate_h_real_loader_comparison.json`

## 必须保留的边界

Gate H 即使成功，也仍然**没有实现 PR27 原版 `IterableDataset` 的 FineWeb Streaming cursor**，也没有证明多 shard、shuffle、无序 DataLoader、真正异常进程杀死、跨容器环境恢复或 GPU 训练。数据提前被建成了本地不可变可索引任务。生产阶段的下一关必须以固定 HF 数据 Revision 和 shard/doc Index 的真实 DataLoader 队列/Worker 故障注入为对象，建立可重建的任务来源。

**在原版 PR27 多 Worker FineWeb-Edu 来源无法做到完全重放前，P0 生产数据恢复保持 BLOCKED。**
