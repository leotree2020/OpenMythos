# R2 Gate N — 真实 Hugging Face Streaming Dataset Shard 数量：Codespaces 实测结果

**实测时间：2026-10-17（用户 Codespaces 终端完整日志）。状态：VERIFIED。** 本报告记录用户贴出的文本日志，而非声称直接读取其 Git ignored 报告 JSON。未修改原版 PR #27。

## 前提与执行

- `git pull --ff-only origin mini-mythos-research` 成功 fast-forward 至 `04e639c`；工作区存在未跟踪的 `SETUP_LEOTREE2020.md` 与 `mini_mythos_leotree2020_overlay_v04.zip`，未作改动。
- 单独 Gate N 单测：**9/9 PASS（0.005 秒）**。
- 全项目单元测试：**214/214 PASS（74.424 秒）**；无失败。
- `python research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py freeze --repo .` 执行成功，之后 `verify --repo .` 在离线模式重算一致，打印 `Offline true HF shard-count evidence: VERIFIED`。
- 初始化时 HF 警告 unauthenticated Hub requests 并打印 `Resolving data files: 2410/2410`；这是代码初始化元数据所需的全 Repo 文件引用解析，不是当前配置的逻辑 Shard 数。此实验**没有执行文档迭代**，但初始化可能访问 Hub / Schema / Parquet header；网络字节数未测量。

## 不可变来源和环境

| 项目 | 实测 |
|---|---|
| Dataset | `HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train` |
| 固定 HF Commit | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| Gate M 真实 Parquet 文件清单数量 | **14** |
| Gate M 文件名/Size 清单 SHA | `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209` |
| Python | `3.14.2` |
| datasets | `5.1.0` |
| torch | `2.14.1` |
| huggingface_hub | `2.2.0` |
| pyarrow | `26.0.0` |

## 实际 Dataset API 计数

| 实际/投影指标 | Worker 0 | Worker 1 | 合计 |
|---|---:|---:|---:|
| `ds.num_shards`（主进程真实 Dataset） | — | — | **14** |
| `ds.shard(2,w,contiguous=True).num_shards`（真实 API） | 7 | 7 | 14 |
| `ds.shard(2,w,contiguous=False).num_shards`（真实 API） | 7 | 7 | 14 |
| `ds.shard(2,w).shard(2,w,contiguous=False).num_shards`（真实 API） | **4** | **3** | **7** |
| 基于上述实际数量计算的原生 Worker 逻辑分片覆盖投影 | — | — | **14/14** |
| 基于上述数量计算的手动 + 自动 Worker 逻辑分片覆盖投影 | — | — | **7/14** |

基于正确 HF contiguous/manual + noncontiguous/auto 语义的预测遗漏逻辑 Shard 索引：`[1, 3, 5, 7, 9, 11, 13]`。

freeze 创建 Git 忽略目录中的 `research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json`，verify 离线检查通过，未覆盖之前 Gate M/Gate I 成果。

## 科学结论与边界

**Gate N VERIFIED：固定版本真实 Hugging Face Streaming Dataset 的 `num_shards` = 14，且真实 `.shard()` API 调用后的 7+7 与 4+3 数量，与 Gate M 的 14 文件结果及双重分片风险预测一致。**

注意**数量相同不等于一一对应关系已经证实**。日志明确显示：`HF file-to-shard identity verified: False`。本关也没有运行原版 PR #27 的真实 PyTorch 多 Worker DataLoader，或者遍历真实 Parquet 文档；`Original PR27 DataLoader executed: False`。因此此实验不能支持“原版远程训练已实际漏掉 50% 文档/Token”的断言。

下一关的目标是 **Gate O：metadata-only 的真实 HF IterableDataset 底层文件来源 → 逻辑 Shard 对应关系审计**，先通过安装的 `datasets` 实际源码/公开 API 确认能否不迭代地获取文件名及顺序。任何无法清晰识别的数据结构必须 FAIL CLOSED，不做大规模远程读行/训练；敏感 URL 查询参数与授权字段不得输出至日志。真正的 Worker 远端读取、源覆盖率和 SIGKILL 故障恢复应保留为后续独立实验。
