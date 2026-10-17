# R2 Gate O — 真实 HF 文件 → 逻辑 Shard 身份映射：实测通过

**时间：2026-10-17。证据：用户在 Codespaces 执行测试、`freeze` 和完全离线 `verify` 并回传完整日志。** 本归档仅据用户日志写结论，不声称读取其 Git ignored 目录里的 JSON 内容，也不把 HF 元数据操作说成真正远程 Parquet 数据行读取。

## 结果总览

| 项目 | 实测 |
|---|---|
| Gate O 专项测试 | **11/11 PASS（0.009 秒）** |
| 完整单元测试 | **225/225 PASS（48.712 秒）** |
| 版本固定 Dataset | `HuggingFaceFW/fineweb-edu` / `sample-10BT` / `train` |
| 数据集 Git Commit | `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`（Gate I、M、N 一致） |
| HF 数据集逻辑 Shards | **14** |
| 实际 HF 逻辑 Shard ↔ Parquet 路径身份 | **已从真实 IterableDataset 的文件元数据检查并映射** |
| 原生 HF Worker 分片文件来源元数据覆盖 | **14/14** |
| 手动 contiguous + HF auto noncontiguous 元数据视图覆盖 | **7/14** |
| Double-Shard 在真实 HF 文件来源元数据中未分配的文件 | **7** |
| Gate O freeze | **成功**：`REAL pinned HF source-file mapping inspected (NO record iteration)` |
| Gate O 离线 verify | **成功**：`Offline Gate O HF real file-shard mapping: VERIFIED` |
| 原版 PR27 OS Worker 实际运行 | **False** |
| 实际文档 / Token 漏读数量测量 | **False** |
| 原始数据记录遍历 / 模型训练 / GPU | **No / No / No** |

**在嵌套 double-shard 的真实 HF `.shard()` 元数据视图中缺失的具体真实 Parquet 路径：**

```text
sample/10BT/001_00000.parquet
sample/10BT/003_00000.parquet
sample/10BT/005_00000.parquet
sample/10BT/007_00000.parquet
sample/10BT/009_00000.parquet
sample/10BT/011_00000.parquet
sample/10BT/013_00000.parquet
```

工具在 Codespaces 创建本地 Git ignored 证据：`research/mini_mythos/results/r2/pr27_gate_o_real_hf_file_shard_mapping.json`。离线复验成功；上述结论均来自脚本实际输出，不是根据文件命名习惯自行猜测。

## 先前失败与修复保留

Gate O 最初 `10 tests` 中 1 FAIL（`8 != 4`）：`setUp()` 构造 Gate N 假报告时错误地复用了 Gate O 的 FakeDataset，使 `.shard()` 计数累计。已将 Gate N 预处理改为独立 FakeDataset，保留原 4 次严格调用断言，新增防回归测试；本次重测 **11/11、225/225** 全通过。原始失败记录 [Failure 001](R2_GATE_O_FAILURE_001.md) 保留，不做删除或隐瞒。

## 科学结论与限制

**Gate O PASS：不是单纯文件数投影，而是在锁定 `datasets==5.1.0`、Gate I/M/N 证据与实际 HF Streaming Dataset 内部文件来源结构后，用真正 `.shard()` 视图确定 Parquet 文件路径分配：正常完整 14/14，手动+自动只剩 7/14。**

但我们仍**不能**声称原版 PR27 的 OS Worker 已实测跳过这些文件，或该训练运行损失 50% 文档/Token。每个 Parquet 文件包含的文档/Token 数量可能不同，而且本关没有真实远程逐行读取。控制台 `Resolving data files: 2410` 表示仓库级文件引用解析，不能说 sample-10BT 有 2410 个 Shards。

HF 初始化可能请求元数据、Schema、Parquet file header；没有网络字节监控，故不能宣称整个 freeze 过程访问零 Parquet 字节。程序没有显式迭代数据行、没有跑 DataLoader 或模型。真实 URL 凭证与查询参数没有写入研究结果。

## 下一步：Gate P

先在严格的**零真实内容读取**范围内，通过真正 Linux PyTorch `DataLoader(num_workers=2)` 路径，复用来自固定 HF Dataset 的 14 个实际、已净化的文件身份来验证 Native-only vs manual+auto 的来源覆盖。应明确说明：若只把真实文件身份转成小型离线/内存模拟数据源，验证的是**真实 OS Worker + HF 自动分片机制**及固定真实来源 ID 的覆盖，并非真正远端 Parquet 逐行下载。随后再单独设计远端受限读取实验（如果需要）。任何未知格式、工作进程缺失、伪造来源、多次覆盖、环境版本不符都应拒绝。
