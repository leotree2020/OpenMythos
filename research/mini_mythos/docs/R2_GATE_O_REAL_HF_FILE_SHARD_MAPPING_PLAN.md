# R2 Gate O — 固定 HF 5.1.0 的真实文件来源 → 逻辑 Shard 对应关系检查（仅元数据）

**方案提交：2026-10-17；现已由用户 Codespaces 实测验证：Gate O 专项 11/11、完整 225/225 PASS（48.712 秒）；真实 HF 14 个来源文件元数据映射成功，Native 14/14、双重分片 7/14；`freeze` 与完全离线 `verify` 均成功。见 [Gate O Result](R2_GATE_O_RESULT.md)。首次 9/10 失败及其修复保留在 [Failure 001](R2_GATE_O_FAILURE_001.md)。** 前一关 [Gate N Verified](R2_GATE_N_RESULT.md)：214/214 项测试通过；真实 `load_dataset(streaming=True,revision=frozenSHA)` 的 `ds.num_shards=14`；`.shard(2,w)` 的实际元数据计数 7/7，手动之后再 HF 自动分片 4/3；无文档遍历、无训练。

## 为什么需要 Gate O

Gate M 已固定实际 `sample/10BT` 目录 **14 个 Parquet 文件**；Gate N 已确认实际 HF 运行时**14 个逻辑 Shard**。但是“数量都等于 14”尚不能证明文件 `sample/10BT/001_00000.parquet` 必定属于运行时逻辑 Shard 1。Gate O 检查这一层映射，仍然不启动 PyTorch Worker、不读取正文。

## 实验根据什么代码

通过检查 Hugging Face 官方 `datasets` 标签 `5.1.0`（不是浮动 main）的公开源码，确认：

- `src/datasets/packaged_modules/parquet/parquet.py` 的 `_split_generators` 将 split 的 `files` 和配套 `row_groups_list`（初始全部 `None`）存进 `gen_kwargs`；Parquet 读取实际发生在之后的 `_generate_tables`，本实验**不调用**。
- `src/datasets/builder.py` 的 `ArrowBasedBuilder._get_examples_iterable_for_split` 将 `gen_kwargs` 传给 `ArrowExamplesIterable`。
- `src/datasets/iterable_dataset.py` 的 `ArrowExamplesIterable` 保留 `.kwargs`；`shard_data_sources` 按索引筛选这些 kwargs；`_iter_pytorch` 在实际迭代时采用 `contiguous=False` 分片。Gate O 只调用 `.shard()` 的元数据视图，不调用 `_iter_pytorch` 或任何 `iter(ds)`。
- `src/datasets/utils/sharding.py` 的 `_split_gen_kwargs`/`_number_of_shards_in_gen_kwargs` 根据相同长度的来源列表进行分片。

该实现涉及 **HF 私有成员** `_ex_iterable`/`kwargs`，因此 Gate O **只接受 `datasets==5.1.0`** 和经过白名单检查的类型结构。若版本或内部结构有变化，先 FAIL CLOSED，把错误回传审核，不尝试未经审计的其他库版本。

## 输入、动作和证据等级

1. 严格核验 Git ignored Gate I 32 条真实文本快照、Gate M 14 条真实文件元数据报告（外部已知 SHA `0b65e53aeb3c7c1d69debfcea0e7105fd5e7a1141b7f3bd7bc9bbc3957a44209`）和 Gate N 真实分片元数据报告（内容 Hash、`num_shards=14`）。校验失败绝不请求 HF。
2. 构建与 Gate I/N 一致的 `HuggingFaceFW/fineweb-edu / sample-10BT / train` Streaming Dataset，并在主进程读取**原始 Source iterable 的文件列表元数据**。不调用 `iter()`/`next()`、不读取 DataLoader 文档。
3. 只解析源引用的公开 `sample/10BT/NNN_00000.parquet` 相对路径，**不写出远端完整 URL、Auth Token、查询参数或真实文本**。要求 14 个来源文件身份完整匹配 Gate M 的实际文件名集合、无重复或多余。
4. 真正对**同一个 HF Dataset 对象**调用 `ds.shard(2,w,contiguous=False)`、`ds.shard(2,w,contiguous=True)`、`ds.shard(2,w).shard(2,w,contiguous=False)`，分别查看内部 `files` 清单并逐条验证对应关系。输出原始真实顺序、每 Worker 保留的文件路径、双重分片之后缺失的具体路径。
5. 只在完整无歧义映射成立时将 `source_file_to_logical_shard_mapping_verified=True` 记录到报告；真实 Worker 是否执行、真正的文档/Token 遗漏率，**始终保持 False**。
6. Freeze 结果存储 Git ignored JSON，离线 Verify 在完全不访问 HF 的前提下复算来源映射、清单 SHA、Gate N 报告 Hash 与证据类别。拒绝覆盖。

## 安全边界

- Gate O 的目标是**原始 Parquet 文件路径 ↔ 真正 HF 逻辑 Shard ID 的元数据对应关系**；不等于实际 PR27 运行时真正跳过文件或 Token 的现场证据。
- 构建 `load_dataset` 可能访问 HF Hub 元数据、Schema 或 Parquet Header，**不承诺零网络字节**；不会显式遍历数据或训练模型。
- 如果 HF 数据源文件引用携带 URL Token，程序只允许转换为符合正则的 `sample/10BT/NNN_00000.parquet` 相对路径，不输出原始 URL。
- 假如真实文件顺序不是按文件名排序，必须以**HF 实际 Source 顺序**为准，不直接搬用 Gate M 数学投影所推定的特定奇数路径。
- 失败应留存控制台错误，不通过放宽来源版本/改写冻结快照来追求通过。

## Codespaces 执行（在 repo 根目录）

```bash
git status --short
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_r2_pr27_real_hf_file_shard_mapping.py' -v
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py freeze --repo .
python research/mini_mythos/scripts/r2_pr27_real_hf_file_shard_mapping.py verify --repo .
```

本轮**不提前声称 Gate O PASS**。需等待 Codespaces 中的完整测试、freeze 和 verify 实测日志；若成功，才进一步设计 Gate P（严格预算的原版 PR27 Worker 实际远端来源覆盖 / 有限文件探针）。
