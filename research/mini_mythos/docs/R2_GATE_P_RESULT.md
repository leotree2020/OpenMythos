# R2 Gate P — 两个真实 Linux Worker 重放真实 HF 来源文件身份：实测通过

**实测日期：2026-10-17。证据：用户 Codespaces 回传的完整 freeze/verify 终端日志（无远端 Parquet 逐行读取）。** 此文档记录用户实测，不声称已经读取 Codespaces 本地 Git ignored JSON。

## 结果

| 核对项 | Codespaces 实测 |
|---|---|
| 全量研究测试 | **233 / 233 PASS，61.532 秒** |
| Gate P 实验运行 | `Two real Linux Worker arms completed with pinned source FILE IDs only` |
| 不可变 HF Commit | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| 来源真实 Parquet 文件身份 | **14** |
| 正常 Native-only Worker PIDs | Worker0 **31186**；Worker1 **31187** |
| 双重分片 Worker PIDs | Worker0 **31241**；Worker1 **31242** |
| 正常真实来源文件身份重放覆盖 | **14 / 14** |
| 显式 contiguous + HF 自动 noncontiguous 重放覆盖 | **7 / 14** |
| 实际来源文件身份未参与双重分片重放 | **7 个，名单见下** |
| 离线二次验证 | `Offline Gate P OS worker file-identity replay: VERIFIED` |
| 真正远端 Parquet Record 被读取 | **False** |
| 原版 PR27 DataLoader 被运行 | **False** |
| 原文正文进入 Worker | **No** |
| 模型/GPU 训练 | **No** |

### 本地 OS Worker 身份重放中缺失的真实文件路径

```text
sample/10BT/001_00000.parquet
sample/10BT/003_00000.parquet
sample/10BT/005_00000.parquet
sample/10BT/007_00000.parquet
sample/10BT/009_00000.parquet
sample/10BT/011_00000.parquet
sample/10BT/013_00000.parquet
```

本地忽略提交的输出路径：`research/mini_mythos/results/r2/pr27_gate_p_os_worker_file_identity_replay.json`。

## 推理层级——不能相互替代

Gate M：真实 HF Hub 文件元数据清单是 14 个；文件 ID 级分配数学投影是 Native 14/14 / 双重 7/14。

Gate N：真实构造 pinned HF Streaming Dataset 得到 `ds.num_shards=14`，真实 `.shard()` 视图数量为 native 7+7、nested 4+3；逻辑 Shard 索引映射仍是投影。

Gate O：真实 HF IterableDataset 的内部 Parquet 文件来源结构及真实 `.shard` 元数据视图已经映射到 7 个**具体文件路径身份**，但没有启动原版 PR27 的 Worker。

**Gate P：两个真正 Linux DataLoader Worker，在将真实来源文件路径 ID 复制到 14 个本地 Arrow 身份 Shard 的情况下，实际执行 HF 自己的自动 Worker 分配路径，重放出 14/14 对 7/14。** 这证明固定来源 ID 重放下**真实多进程行为**，不是远端 Parquet 文件实体、文档或 Token 的实际读写覆盖率，更不是原版 PR27 训练的实测损失。

## 下一步：修复研究复刻中相同的上游 DataLoader 冲突

已核验固定上游 `kyegomez/OpenMythos` 未合并 PR #27，Head `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4` 的 `experiments/data.py`：

- `FineWebEduStream.__iter__` 用 `torch.utils.data.get_worker_info()` 获取 worker id/count。
- 内部 `ds=load_dataset(... streaming=True)`，在多 Worker 情况执行手动 `ds.shard(num_shards=num_workers,index=worker_id)`。
- 接下来 `for doc in ds:` 在同一个 PyTorch 子进程中触发 HF IterableDataset `__iter__` 的 native Worker 自动分片。因此风险路径存在于**上游实际源代码**，而不仅仅是 Gate L/P 模拟重放。

上述源码检查仍不是“真实原版 PR27 DataLoader 已读取远端少一半文档”的现场实验。修复应优先在**研究副本**中删去手动 `.shard`，由 HF native Worker 自动分工，并保留原文件对照。上游 PR27 原版本身不直接改动。后续候选代码和测试需另外实测。

源码浏览参考：`https://github.com/kyegomez/OpenMythos/blob/2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4/experiments/data.py`。
