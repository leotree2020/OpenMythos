# R2 Gate N — 真正的固定 HF Streaming Dataset Shard 数量与非迭代 Shard 视图验证

**实验设计：2026-10-16；2026-10-17 用户 Codespaces 实测已通过：214/214 tests PASS（74.424 秒），真实 HF Streaming `num_shards=14`，手动 7+7 后自动分片为 4+3，离线 verify VERIFIED。见 [Gate N Result](R2_GATE_N_RESULT.md)。本页保留原始预注册方案。** [Gate M 真实结果](R2_GATE_M_RESULT.md) 证明 HF Hub 固定 SHA `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` 下 `sample/10BT` 的**实际 Parquet 文件数量 = 14**，完整文件路径/Size Hash `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209`；文件级投影原生 14/14、模拟重复分片 7/14。**这不是实际 HF IterableDataset.num_shards 的测量**，更不是实际漏读的文档/Token 数。

## 唯一要回答的问题

在同一真实版本、同一 `sample-10BT` 配置及用户 Codespaces **真实安装的 Hugging Face datasets 版本**下，构建一个不迭代的 `datasets.IterableDataset`，读取它真正的 `num_shards`；再调用真实 Dataset 的 **metadata-only** `.shard(2,0/1,contiguous=True/False)`，观测手动分片前后 `num_shards`。

若真实 `ds.num_shards=14`，就能进一步确认**该配置的运行时逻辑 Shard 数量和 Gate M 文件数一致**，但**光有数量相等仍不能证明逻辑 Shard ID 与 14 个具体 Parquet 文件一一对应**。后续还需比较 HF FileInstruction / Iterable ExIterable 底层映射或真正的 Worker 文件来源。

## 输入与冻结协议

1. **Gate I** 真实 JSONL 和 `manifest.json`，校验固定源码 SHA `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`、文档摘要、快照来源。不重建快照、不输出真实文本。
2. **Gate M** 已存文件清单 `pr27_gate_m_remote_sample_file_inventory.json`，完整重算 Manifest Hash，且对照独立已知的 **14 个文件与 SHA** `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209`；不接受被重签名的另一份文件清单。
3. **唯一实时对象构造**：`load_dataset('HuggingFaceFW/fineweb-edu', name='sample-10BT', split='train', streaming=True, revision='87f09149ef4734204d70ed1d046ddc9ca3f2b8f9')`。本关**不调用 `iter(ds)`/`next(ds)`**、不使用 PyTorch `DataLoader`、不读任何源文档、不训练任何模型。
4. 在主进程访问 `ds.num_shards`、`ds.shard(2,w,contiguous=True).num_shards`、`ds.shard(2,w,contiguous=False).num_shards`、`ds.shard(2,w).shard(2,w,contiguous=False).num_shards`，要求真实 HF API 返回的计数与已审计的分片数学规则匹配，不匹配则**FAIL CLOSED**。
5. 单独把真实 shard count 应用于**逻辑 shard ID**投影：原生 Worker 自动一次 `w::2`；上游式显式 contiguous 一次再 native noncontiguous 第二次。输出各 Worker 逻辑 Shard ID 的预计漏失数量、Index；不把这些 Index 标注成真实 Parquet 文件名或实际 Token。
6. 记录 Python、`datasets`、`torch`、`huggingface_hub`、`pyarrow` 运行版本和当前研究 Git Commit；只保存 Metadata JSON，不包含 Source Text、真实 Token 或模型权重。

**重要网络边界**：`streaming=True` **保证的是不主动把完整语料下载为 Dataset**，而不是绝对不访问 Parquet 文件的任何字节。`load_dataset` 构造可能为了 Schema/File Metadata 等访问远端 HTTP/Range/Header，当前测试不监控网络字节量。严禁宣称“完全没有下载 Parquet 字节”；只能说本实验脚本**没有显式请求文档或迭代数据集**。

## Codespaces 命令

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py freeze --repo .
python research/mini_mythos/scripts/r2_pr27_live_hf_shard_metadata.py verify --repo .
```

**Gate N 代码尚未实测，不能先声称真实 ds.num_shards = 14 或投影遗漏数量 = 7。** 期待报告以下字段：

```text
REAL frozen HF streaming Dataset constructed (NO iteration)
Actual ds.num_shards: <actual>
Frozen sample-10BT Parquet file count: 14
HF shard count equals file count: <True/False>
Actual manual contiguous .shard counts: ...
Actual native noncontiguous .shard counts: ...
Actual manual-then-noncontiguous .shard counts: ...
Native logical shard IDs projected coverage: ...
Double logical shard IDs projected coverage: ...
HF file-to-shard identity verified: False
Original PR27 DataLoader executed: False
Offline true HF shard-count evidence: VERIFIED
```

本地新文件（Git ignored，拒绝覆盖）：`research/mini_mythos/results/r2/pr27_gate_n_live_hf_shard_metadata.json`。`verify` 完全本地完成，重新校验整个报告 SHA、输入版本/文件数、实际 `.shard` 计数和所有逻辑覆盖投影。

## 剩余阻塞

即使本关真的发现 `ds.num_shards=14`，仍然**未执行原版 PR27 Worker/DataLoader**，没有证明实际 remote iterable 14 个逻辑 shard ID 分别映射哪一个 Parquet 路径，更没实际测到 source 文档遗漏率。下一关应使用更严格的 metadata-only Source→Logical-Shard Mapping 审计，或者在严格请求预算/许可范围内做两个真实 Worker 的远端来源索引采样，记录完整版本与文件来源，随后才能提出上游 PR27 数据修复及 SIGKILL 断点恢复实验。
