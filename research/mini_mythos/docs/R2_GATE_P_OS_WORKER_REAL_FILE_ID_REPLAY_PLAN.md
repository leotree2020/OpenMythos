# R2 Gate P — 使用真实冻结 Parquet 文件身份的双 Linux Worker 分片重放

**设计日期：2026-10-17；已于同日用户 Codespaces 实测通过：233/233 tests PASS（61.532 秒），两组各两个真实 Linux Worker，正常来源文件身份覆盖 14/14、双重分片仅 7/14，离线 VERIFY 成功。见 [Gate P Result](R2_GATE_P_RESULT.md)。本页保留原始预注册设计。**

## 最直接的研究问题

Gate M 证明固定 `sample-10BT` 中真实存在 14 个 Parquet 文件；Gate N 使用真实 `load_dataset` 观察到 `num_shards=14`，真 `.shard()` 视图变为 7+7 / 4+3；Gate O 通过真实 HF `datasets 5.1.0` 文件元数据定位出双重分片视图中缺失的 7 个**具体文件路径**。现在继续问：**两个真正的 Linux `DataLoader(num_workers=2)` 子进程实际运行 HF 的 native auto-sharding 时，是否得到与 Gate O 一致的文件身份覆盖？**

## 为什么这一关仍不读远程 Parquet？

真实 `sample/10BT/*.parquet` 文件很大；直接遍历可能下载或解压大量内容。Gate P 使用 Gate O 冻结并验证过的**真正 14 个文件身份（不含正文）**，分别放入本地 HF Arrow `Dataset` 的 14 个 Shards，每个 Shard 恰好一条净化后的 `source_file_id`。实际 Linux OS Worker 只处理这些文件 ID，不访问其原始 Parquet 文件。

这与 Gate L（28 个真实文档 SHA → 8 个本地 Arrow 分片）不同：Gate P 将**真实 HF 元数据中确认的具体 14 个 Parquet 路径**以**一文件 ID 对一局部 Shard**进行带来源版本约束的 Worker 行为验证。它仍然只是身份 ID 重放，并不是原始远程 HF Parquet 读取。

## 已实现的控制

1. Gate I 冻结 32 条来源的 SHA 和版本；Gate M 14 文件清单 SHA；Gate N 真实 Streaming Shards 报告；Gate O 真实文件身份映射报告逐项核验，任何漂移都**拒绝执行**。Gate P 要求现场 Python/datasets/torch/hub/pyarrow 版本与 Gate N、O 完全一致，HF datasets 必须为 `5.1.0`。
2. 来自 Gate O 的 `actual_hf_source_order` 完整保持原始顺序；文件名称经正则校验，仅允许 `sample/10BT/NNN_00000.parquet`，并要求 14 条互不重复。绝不根据字母表排序偷偷更换原始顺序。
3. 构建 **14 条纯身份标识、14 个本地 Arrow Shards**。启动 `DataLoader` 真实 Linux 两 Worker，`spawn` 创建子进程，每个 Mode 都必须检测两个不同 Worker PID。
4. **A 对照：Native HF auto worker sharding only**，两个 Worker 应完整覆盖 14 个文件身份，各 7 个；**B 负控：每个 Worker 显式 contiguous `.shard(2,worker_id)` 后调用 HF Iterator 原生 noncontiguous auto-shard**，各 4 与 3 个。
5. 不接受仅凭“两个 PID 存在”作为成功。每条输出必须来自源列表、归属正确 Worker、无重复、无未登记文件、实际顺序与 Gate O 映射一致。B 组预期缺 7 条，实际仍以 Codespaces 输出为准。
6. 报告保存于 Git ignored `research/mini_mythos/results/r2/pr27_gate_p_os_worker_file_identity_replay.json`，记录两组 PID、每 Worker 的真实源**身份字符串**、来源证据摘要，以及 `original_pr27_dataloader_executed=False` / `no_remote_parquet_rows_read=True`。另设不联网的 `verify`，校验来源链接、哈希、环境和重算 Worker 覆盖。

## 证据的三层区别

| 关卡 | 已观察到什么 | 不能声称什么 |
|---|---|---|
| Gate O | 真实 HF Source 元数据中 14 个文件映射；双重分片视图剩 7 个 | OS Worker 实际读取了那 7 个或遗漏了文件正文 |
| Gate P（待实测） | 真实两个 Linux Worker 在 **本地仅身份 ID 重放**中覆盖哪些固定真实文件身份 | PR27 的线上 Parquet 源数据被真实 Worker 读取或遗漏了多少 |
| Gate Q（未来） | 需要另行设计的受控真实 remote streaming 来源记录测量 | 未运行前不能保证真的发生 50% 文档/Token 漏读 |

## Codespaces 命令（研究分支）

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_os_worker_file_identity_replay.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py freeze --repo .
python research/mini_mythos/scripts/r2_pr27_os_worker_file_identity_replay.py verify --repo .
```

预期新增测试 8 项，全集合约 **233 项**，**仅是预期数，不是已验证 PASS**。单测 Linux 两个 OS Worker 使用合成文件名称、身份数据，不联网也不传输 FineWeb 文档。

**不修改原版 upstream PR27；不修改 Gate I/M/N/O 冻结结果；用户工作区未跟踪 `SETUP_LEOTREE2020.md`、`mini_mythos_leotree2020_overlay_v04.zip` 绝不删除/覆盖。** 如有单元测试失败或 HF 数据结构与预计不同，保留完整输出，失败归档后再修复。