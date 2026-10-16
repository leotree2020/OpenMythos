# R2 Gate M — 真实 sample-10BT Parquet 元数据清单与文件级双重分片投影：实测结果

**实测日期：2026-10-16；证据：用户在 GitHub Codespaces 运行并贴回的命令行记录。** 本报告不宣称曾读取用户 Git 忽略目录中的 JSON 文件本体，也未下载 Parquet 数据。

## 实测证据

| 项目 | 实测 |
|---|---|
| 全量单元测试 | **205/205 PASS（47.955 秒）** |
| 真实 HF Repo / Config | `HuggingFaceFW/fineweb-edu` / `sample-10BT` |
| HF Commit SHA | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`（Gate I 相同） |
| 实际文件清单目录 | `sample/10BT` |
| 实际 Parquet 文件数 | **14**（不是整个 Repo 的 `Resolving data files: 2410`） |
| 文件路径+大小清单 SHA-256 | `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209` |
| `Native-once projected files` | **14/14**；完整一次 |
| `Manual+HF-auto projected files` | **7/14**；文件 ID 级预测遗漏 **7** |
| 文件级预测遗漏路径 | `sample/10BT/001_00000.parquet`, `003_00000.parquet`, `005_00000.parquet`, `007_00000.parquet`, `009_00000.parquet`, `011_00000.parquet`, `013_00000.parquet` |
| Freeze 是否下载 Parquet 正文 | **No** |
| 随后完全离线 `verify` | **`Offline pinned file inventory: VERIFIED`**，SHA 与 Freeze 一致 |
| 是否执行原版 PR27 Streaming Loader | **No** |
| 模型训练、GPU | **No / No** |

报告对应用户本地 Git 忽略文件 `research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json`；真实文件清单 JSON 未在聊天中逐条提供，以上严格依据用户可见日志。

## 结论

**R2 Gate M：PASS — 用不可变 HF Commit 固定 `sample-10BT` 的 14 个实际 Parquet 文件名与大小，获得离线可核的清单 Hash，并完成文件 ID 级分片覆盖投影。**

**不得把这一步描述为 PR27 正式远程 Loader 已遗漏 50% 文档/Token**。文件目录条目数量可能不等于该配置被 `load_dataset(..., streaming=True)` 构建的 `IterableDataset.num_shards`。即便两者恰好都是 14，也仍需另外证明 IterableDataset 内部 Shard ID/文件路径的对应关系及真实 Worker 的加载行为。文件级投影属于可证伪的风险预测，而非实际读取远端 Parquet 的覆盖率。

## 下一关 Gate N

保留 Gate I/M 的冻结 SHA，仅调用 Hugging Face `datasets.load_dataset('HuggingFaceFW/fineweb-edu',name='sample-10BT',split='train',streaming=True,revision=frozen_commit)` **构造真实 Dataset 对象、不显式迭代**。读取真正的 `ds.num_shards`，在主进程调用 `.shard(2,worker)` 的元数据操作并比较各分片 `num_shards`，按 HF 已验证的 contiguous/manual 与 noncontiguous/native 语义对**逻辑 Shard IDs**做理论覆盖。独立记下 `datasets`、`torch`、`huggingface_hub`、`pyarrow` 等库版本，将结果保存在 Git ignored JSON 并做离线验证。

本步骤**不主动读取任何文档记录**，但 HF `load_dataset` 初始化可能发起元数据、Schema、文件页头或其他底层请求，因此不应在没有实测网络字节计数的情况下绝对宣称“没有下载任何 Parquet 字节”。它仍然不能取代真 DataLoader/SIGKILL/数据游标复现。
