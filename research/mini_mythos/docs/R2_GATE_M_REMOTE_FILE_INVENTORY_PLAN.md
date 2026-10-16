# R2 Gate M — 固定 FineWeb-Edu sample-10BT 的真实 Parquet 文件名/大小清单及文件级 Shard 覆盖投影

**制定日期：2026-10-16；状态：研究脚本和 8 项无网络回归测试已提交；Codespaces 仍未执行真实 Hub 文件树查询。** 前一关 [Gate L 已验证结果](R2_GATE_L_RESULT.md)：197/197 tests PASS；两个真实 OS Worker 均存活时，8 个本地 HF Arrow Shards 上原生分片 28/28，显式 `.shard` 再自动分片只有 14/28；这是受控反例而非正式远程数据遗漏比例。

## Gate M 的最小可证范围

在 [官方 FineWeb-Edu 数据集卡](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) 的 `sample-10BT` 配置（指向 `sample/10BT/*`）中，使用 Gate I **已经实测固定的仓库 Commit SHA** `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，从 Hugging Face Hub **只列举 `sample/10BT` 路径的文件元数据**：相对路径和实际 File Size，不读取 Parquet 数据页、不调用 `datasets.load_dataset(..., streaming=True)`、不运行 DataLoader 或模型。

新 [r2_pr27_remote_parquet_inventory.py](../scripts/r2_pr27_remote_parquet_inventory.py) 与 [八项无网络单测](../tests/test_r2_pr27_remote_parquet_inventory.py) 实现：

1. 在 `freeze` 前再读用户已经冻结的 Gate I 本地 `snapshot.jsonl/manifest.json`，验证快照哈希、仓库 Commit、源文档完整性。**不能从最新 main 代替固定版本**。
2. 调用 `HfApi.dataset_info(repo_id='HuggingFaceFW/fineweb-edu',revision=frozen_sha)` 并确认返回 **完全相同的 SHA**，之后仅调用 `HfApi.list_repo_tree(path_in_repo='sample/10BT',recursive=True,revision=frozen_sha,repo_type='dataset')`，从返回元数据筛选位于该目录的 `.parquet` 文件。
3. 文件名、正整数 Size、唯一性与排序规则严审；只接受最直接的 `sample/10BT/*.parquet` 文件，文件数量硬上限 **256**，若真实仓库布局不符合预定政策，**FAIL CLOSED**，不随意放大抓取范围。
4. 生成 `file_inventory_sha256`（把文件名和 Size 按 canonical JSON 序列哈希）、不可变版本与研究 Git Commit，写入专用的 Git ignored JSON；独立 `verify` 从本地重新计算全部 SHA、文件结构及分片投影，**无需网络**。
5. 在完整真实文件名清单上做**文件 ID 级推演**：A 仅按 Hugging Face `_iter_pytorch` 的 Worker non-contiguous 分片（worker `w` 得到原顺序 `w::2` 的文件 ID）；B 模拟 PR27 的 Worker `.shard(2,w)`（`contiguous=True`，前/后两半）后，HF `_iter_pytorch` 在每半文件上又做 non-contiguous `w::2` 的二次分片。分别输出文件数、遗漏文件下标与**路径**。

### 谨慎解释真实来源

- Gate I 运行时打印的 `Resolving data files: 2410/2410` 是解析的数据文件引用数，**不能直接等同于 `sample-10BT` 配置的 shard 数**。此关必须用真实路径树确认文件数量。
- **文件路径级覆盖预测 ≠ 实时 `IterableDataset.num_shards` 确认**。Hugging Face 版本、Parquet 构建器/重分片、配置匹配方式可能导致实际生成的 `num_shards` 与单个 Parquet 文件数不同；下一个 Gate 需要在安装环境只构建、**不迭代**真实 Streaming Dataset 以直接核验 `ds.num_shards` 和源码映射。
- **文件级预测遗漏数 ≠ 真实漏掉的文档/Token 数**，且不代表模型已经按这些具体文件训练失败。不能仅凭该投影向上游宣称漏读比例。
- Hub 的树查询会访问元数据 API，文件数量上限约束的是**解析后匹配的 sample/10BT Parquet 元数据数**，不是 API 总字节或网络页请求的绝对预算。**不下载 Parquet 正文**，不读取原始文档到 DataLoader。
- 只保留文件名/Size/SHA 等元数据。上游 PR27 和真实 Gate I/GPT2 Checkpoint 均**不修改**，没有 GPU 训练。

## Codespaces 执行

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_remote_parquet_inventory.py freeze --repo .
python research/mini_mythos/scripts/r2_pr27_remote_parquet_inventory.py verify --repo .
```

预计输出：`Pinned HF commit: 87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，`Inventory Parquet FILE count: <实测数>`、完整文件路径+Size SHA；`Native covers all file IDs once: True`，以及 `Manual+HF-auto projected files` 和 `missing file IDs`。**绝不预报具体实际文件数/遗漏数**，在 Codespaces 跑出前这些均是待验证。

新文件：`research/mini_mythos/results/r2/pr27_gate_m_remote_sample_file_inventory.json`（Git ignore，拒绝覆盖）；已冻结的 Gate I 原始 JSONL 不改动。

## 后续决策

完成本轮固定 HF 元数据后，下一步在**相同源码/安装版本**的 `datasets.load_dataset('HuggingFaceFW/fineweb-edu',name='sample-10BT',split='train',streaming=True,revision=frozen_sha)` 只获取 Dataset 对象，不实际迭代文档，直接读取真实 `ds.num_shards`，并对**真实远端 Dataset 的 `.shard(2,w).num_shards`** 进行无内容实验。再考虑有严格请求预算的远端 Worker Source Offset/文档校验。这样才能由单纯的路径级理论投影继续走向真实 Streaming 架构与生产级 SIGKILL 恢复。
