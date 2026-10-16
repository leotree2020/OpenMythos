# R2 Gate I — 官方 FineWeb-Edu 固定 SHA 真实文档快照：实测完成

**2026-10-16，来自用户 GitHub Codespaces 的真实终端日志。** 已执行完整单测、Hugging Face 官方源冻结与同一快照的独立离线复验。本报告未从用户 Codespaces 下载/公开真实文档正文。

## 已确认的证据

| 指标 | 实测 |
|---|---|
| 全部单元测试 | **171/171 PASS（15.046 秒）** |
| 数据仓库 | `HuggingFaceFW/fineweb-edu` |
| 配置 / split | `sample-10BT` / `train` |
| `main` 解析后的不可变 Commit SHA | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9` |
| 数据集卡许可证元数据 | `odc-by`（仅记录来源 metadata，不等于完成企业合规审查） |
| 真实源文档 | **32/32**，按源顺序扫描 32 行且没有跳过 |
| 选中真实文本长度 | **111361 UTF-8 bytes** |
| 本地快照长度 | **119588 bytes** |
| `snapshot.jsonl` SHA-256 | `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1` |
| 离线再次验证 | **`Offline source snapshot: VERIFIED`**，SHA 与 Freeze 完全一致 |
| 上游 PR27 正式 Streaming Loader | **未修改** |
| 模型训练 | **未执行** |

终端提示 `Resolving data files: 2410/2410`，这是 Hugging Face 扫描/解析文件引用，**不能解读为全部 2410 个 Parquet 分片的完整数据都已下载**；报告只证明限量快照冻结成功。

## 结论

**R2 Gate I — 真实官方数据来源不可变固定、本地限量存档、逐文档/整体摘要与离线快照验证 PASS。** 为进一步可重复的 FineWeb-Edu 小规模数据加载协议提供了可信的固定输入，优于此前的合成文章。

**限制：32 条源文档不是预先设计的正式 Train/Validation/Test 划分，更不是独立测试集；PR27 `IterableDataset` + HF shard + `num_workers=2` 的真实 streaming 断点状态仍未解决。** 这一步完全没有训练语言模型。

## 用户本地未提交的证据

`research/mini_mythos/results/r2/fineweb_gate_i_32/manifest.json`

`research/mini_mythos/results/r2/fineweb_gate_i_32/snapshot.jsonl`

包含真实文档全文的 JSONL 文件属于用户 Git 忽略的 Codespaces 文件，**绝不能添加进 Git 提交**。本报告仅记录公开的数值、版本和 hash。

## 下一步：Gate J

在已冻结的 **HF dataset SHA + 快照文件 SHA + 真实 GPT-2 Tokenizer 指纹** 上使用 Gate H 已经验证的真实双进程 CPU DataLoader。由离线快照的 32 条真实文档生成固定内容哈希任务，不重复触碰线上流；在实验内部按固定 Document ID 分离仅供协议测试的消费/保留记录（**不将此保留组用于评价或报告模型质量**），测试连续 12 vs 5+7 steps 的可恢复数据与优化器状态。

Gate J 即使成功，也不能认为完整 FineWeb-Edu Streaming 可恢复；原版 PR27 仍缺实际 shard/doc offset、持久的 committed batch 索引、真正异常进程中断测试和生产训练/验证隔离。
