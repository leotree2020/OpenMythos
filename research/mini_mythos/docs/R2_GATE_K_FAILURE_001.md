# R2 Gate K — 首次运行失败与根因归档（Failure 001）

**日期：2026-10-16；依据：用户上传的完整 Codespaces 控制台日志（本地文件；不含真实 FineWeb 文本）。此记录是失败证据，不是实验通过报告。**

## 已复现的失败

- `git pull --ff-only` 将分支推进至 `c1c86cd`，随后运行完整 tests 与 CLI。
- **Ran 187 tests in 33.794s — FAILED (errors=1)**。
- 唯一失败：`test_r2_hf_worker_shard_pack.GateKTests.test_real_worker_shard_then_pack_resume_matches_full_run`，在 `r2_hf_worker_shard_pack.py` 检查真正两名 Worker PID 时抛出 `RuntimeError: Missing one of two actual DataLoader worker PIDs`。
- Hugging Face 明确提示：`Too many dataloader workers: 2 (max is dataset.num_shards=1). Stopping 1 dataloader workers.`
- 单独执行 `python research/mini_mythos/scripts/r2_hf_worker_shard_pack.py --repo .` 再次出现相同提示和 RuntimeError。**CLI 没有通过，没有成功完成 Gate K 验收。**
- 此失败**并没有影响 Gate J 179/179 PASS**，也不构成 Frozen Tokenizer、HF Source SHA 或 Checkpoint 的损坏证据。

## 源码层原因

最初 Gate K 已将本地 HF `Dataset.from_dict(...).to_iterable_dataset(num_shards=2)` 创建为两个 Arrow Shards，却又在子进程 `HFWorkerShardPacker.__iter__` 里执行 `self.source.shard(num_shards=2, index=worker_id)`，此时每个 Worker 只剩**一个** HF Shard。遍历该 HF IterableDataset 时，它的 PyTorch 集成在 Worker 环境中再次依 `get_worker_info()` 自动分片（当前 Hugging Face 源码 `IterableDataset._iter_pytorch()`），检测 `num_shards=1 < num_workers=2` 后会终止多余的 Worker。上游 PR27 的 `experiments/data.py` 也含独立 `.shard()` 再交给 Worker 消费的顺序，因此需要单独审查其在真实多个 Parquet Shards 的实际覆盖率，不能从本次两 Shard 失败直接推定准确的全量缺失比例。

源代码参考：[Hugging Face datasets `IterableDataset._iter_pytorch()`](https://github.com/huggingface/datasets/blob/main/src/datasets/iterable_dataset.py)、[上游 OpenMythos PR27](https://github.com/kyegomez/OpenMythos/pull/27) 固定 Commit `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`。

## 修复策略（已提交、尚待 Codespaces 复验）

1. 保持 `to_iterable_dataset(num_shards=2)` 的本地两个 Arrow Shards，**从子进程中去掉手动 `.shard(...)`**，由 HF `IterableDataset.__iter__` 中已有的 PyTorch Worker 自动分片**恰好一次**，然后各 Worker 独立进行 Tokenizer→EOS→Packed Windows。
2. 添加主进程分区审计 `audit_local_hf_worker_partition`，按 HF 自动分片的 `contiguous=False` 规则验证来源文档 ID 散列的分区交集为空、合并后恰好覆盖全部训练文档；报告仅写文档计数和 Hash。
3. 新增两个单测直接检查 HF 的 `.shard(2,worker_id)` 将 2 Shards 变为 1 的隐患，另以 **4 Shards** 为对照展示双重分片可能**静默遗漏真实来源记录**；原始真实文档不进 Git。
4. 仍需真实双进程测试确认三个运行分支都观测到 2 名 Worker PID、预取数据与从 checkpoint 恢复的模型/AdamW/RNG/数据 Trace 完全一致，并验证 Gate J 的全局 Pack 与 Gate K 的 Worker-local Pack 窗口不同。

**范围说明**：修复后的 Gate K 更准确地叫做 **HF native auto worker-sharding → worker-local packing**，只验证上游希望实现的 shard-before-pack 行为，不再字面复制上游代码中可能构成 double-shard 的显式 `.shard`。这正是本轮审计发现的问题，应保留差异并另行向上游提出适用的修复建议。

**当前状态：首次 Gate K FAIL；候选修复及新增测试 COMMITTED，尚未 Codespaces 复验。** 不运行 118M GPU 训练、不合并修改到上游正式模型。
