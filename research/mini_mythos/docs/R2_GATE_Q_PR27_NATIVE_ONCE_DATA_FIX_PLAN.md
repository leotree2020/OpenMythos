# R2 Gate Q — 修正上游 PR #27 双重数据分片：候选最小修复与真实 Worker 回归

**设计：2026-10-17。当前状态：候选研究副本与 8 项离线/本地 Worker 测试已提交，但未在用户 Codespaces 执行。原版 upstream PR #27 文件没有改动。**

## 研究目标

Gate P 真实 Linux Worker 对 Gate O 锁定的 14 个 Parquet **身份 ID** 重放结果：233/233 tests PASS、正常 14/14 与双重 7/14、两组各 2 个真实 PID、离线 VERIFY 成功。不能把身份 ID 重放当成远程 Parquet 正文、文档或 Token 的实际漏读率。

现在改进数据加载器的核心错误，而不继续无限增加“仅诊断”关卡。

## 上游 PR #27 的真实代码路径（已从固定 Commit 审核）

- Repo：`kyegomez/OpenMythos`；PR：`#27`（2026-09-17 已关闭，未合并）；Head Commit：`2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`。
- 文件：`experiments/data.py` → `FineWebEduStream.__iter__`。
- `get_worker_info` 获取 PyTorch worker id/count；`load_dataset(...,streaming=True)` 构建 Hugging Face Dataset；如 `num_workers > 1` 再手动 `ds.shard(num_shards=num_workers,index=worker_id)`；随后 `for doc in ds:`。
- HF `datasets 5.1.0` 的 `IterableDataset.__iter__` 在**同一个 DataLoader 子进程**识别 PyTorch Worker 并自动把资料分到各 Worker（`contiguous=False`），因此会形成双重分片路径。
- `experiments/train.py` 使用 `build_loader(...num_workers=2)`；`experiments/evaluate.py` 现有 `skip_docs=2_000_000` 且 `num_workers=1`，不能把训练/评估的预处理策略混成一个全局文档计数结论。

原版源码 URL：`https://github.com/kyegomez/OpenMythos/blob/2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4/experiments/data.py`。

## 研究副本候选方案

研究文件 [r2_pr27_native_once_data_candidate.py](../scripts/r2_pr27_native_once_data_candidate.py)，不在 repo 根目录新建或修改 `experiments/data.py`。

1. **删除显式 `.shard(2,w)`**，由 HF 自带 PyTorch DataLoader Worker 自动分片一次。
2. 数据源四元组锁定：`HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train` / HF commit `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`；`streaming=True`。
3. 与上游相同的 EOS/拼接缓冲/`seq_len+1` 移位 Target，输出 `(x,y)` 两个 `torch.long` Tensor；loader 保留原版 `pin_memory=True` 与 `persistent_workers` 行为。
4. 如果启用 `skip_docs>0`，只允许一个 Worker，避免把“全局跳过 N 篇”错误解释为“每个 Worker 分别跳过 N 篇”。这是刻意缩小研究副本功能边界，并不证明原版评估划分无漏洞。
5. 不增加训练、模型权重或 GPU 逻辑。首次真正迭代前不会构造远端 Dataset。

## 8 项回归测试

- 拒绝未冻结来源、错误/可变 Revision。
- 拒绝非法 `seq_len`、`skip_docs`、缺失 EOS。
- 测试 fake HF Dataset 对象故意拒绝 `.shard`，候选加载器迭代成功、保留原版 shift-target 与 EOS 边界。
- 测试 `load_dataset(...streaming=True,revision=frozenSHA)` 被按固定参数调用。
- 单 Worker `.skip(N)` 的可解释性；多 Worker `.skip(N)` 在 Hub 加载前即拒绝。
- 拒绝非字典记录或非整数 Token IDs。
- `DataLoader` 创建参数和保留的 pin memory 选项。
- Linux 下真实 2 Worker 使用**14 个本地 HF Arrow 分片中的合成文档 `ID:0...ID:13`**；以 `fork` 继承完全离线 fake `load_dataset`，检查所有 14 个身份各一次、两个 PID、每 Worker 分别处理 7 个；**不是远端 Parquet 读取**。

全部测试预计由 Gate P 通过的 233 项增长至 **241 项**；只是预期计数，不是实际 PASS。Gate Q 测试若失败，保存原始失败并修复后重测。GitHub 插件创建/更新代码不代表 Codespaces 运行过这些测试。

## Codespaces 操作

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_native_once_data_candidate.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
```

本关目前**只有代码和测试候选，没有 remote `freeze`**：要通过这两个测试组、检查上游原版代码差异，再在研究副本中做额外的来源文档覆盖/Checkpoint 故障恢复验收。不能把 Gate Q 的候选视为已经修复原版 PR #27。

## 后续边界

明确区分：A) 已修复候选代码在本地 2 Worker 对所有 14 个 ID 的覆盖；B) 上游原版代码仍有双重分片风险；C) 原版训练实际远程数据遗漏率尚未测量。没有必要马上下载整份 FineWeb-Edu 或投入约 118M 模型 GPU 训练。
