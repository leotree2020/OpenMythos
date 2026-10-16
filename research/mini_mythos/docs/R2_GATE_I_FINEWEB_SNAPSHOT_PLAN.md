# R2 Gate I — 官方 FineWeb-Edu 不可变数据源与受限真实文档快照

**2026-10-16；状态：已在用户 Codespaces 实测通过：171/171 单测 PASS，冻结官方 32 条 FineWeb-Edu 文档，HF revision `87f09149ef4734204d70ed1d046ddc9ca3f2b8f9`，本地快照 SHA `dbd98514fa4de0df2271fe9ddc214a295108492f20fa993fa33bbe6db5d366e1`，离线 verify 成功。完整结果见 [Gate I Result](R2_GATE_I_RESULT.md)。本页保留实验前协议。** 前一关 Gate H 已验证真实两个 OS Worker 的本地 Indexed Dataset 恢复（**162/162 tests PASS**）：已预取但未提交的 Task 5–8 正确从 Task 5 重放，最终连续/恢复训练全状态逐位一致。见 [R2 Gate H 实测结果](R2_GATE_H_RESULT.md)。

## 研究目标：先保证来源可辨认，而不是马上下载整个数据集

上游 OpenMythos [PR #27](https://github.com/kyegomez/OpenMythos/pull/27) `experiments/data.py` 读取 HF `HuggingFaceFW/fineweb-edu`、配置 `sample-10BT`、`train`，采用 Streaming。它在 Worker 中调用 `ds.shard(...)`，但未固定不可变 HF revision、没有可可靠恢复的 Shard/Doc ID 或 Source Offset；仅凭之前 Gate H 的本地 Indexed Dataset 不能宣布真实源可重放。

官方 [FineWeb-Edu 数据集卡](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu) 确认 `sample-10BT` 配置和 **ODC-BY** 元数据。使用真实数据前需按组织规则核查许可和数据保管；本文只做可重复的数据来源/身份快照，不将语料分发给公众。

## 冻结且不可按分数调节的实验条件

| 项目 | 约束 |
|---|---|
| HF repo | `HuggingFaceFW/fineweb-edu` |
| Dataset config / split | `sample-10BT` / `train` |
| 源 revision | 先用 HF Hub `dataset_info` 将 `main` 解析为**40 位 Commit SHA**，随后按同一 SHA 做 Streaming |
| 选择方式 | 从源的 Streaming 顺序扫描**最多 128 行**，选择最前面的 **32 条**非空且在限额内的文档；保持原始 source row index |
| 文档大小 | 单文档 UTF-8 text ≤ 262144 字节；超过则记录跳过，不截断；若不足 32 条则失败，不改门槛 |
| 文本总量 | 选中真实 text 的 UTF-8 字节总数 ≤ 4 MiB；超过时失败，不截断 |
| 本地快照 | `snapshot.jsonl` 含 32 条真实文本、源行序号、文档 ID 的 SHA256（如果提供）、text SHA256 和字节长度 |
| 校验清单 | `manifest.json` 含 Repo/Config/Split、Source SHA、License metadata、采样规则、数据文本 SHA、文件整体 SHA256、size、文档摘要 |
| 数据角色 | 开发/复现样本，**不是** Train/Heldout/Test 划分，也不评估/训练模型 |
| 网络调用 | 仅在 `freeze` 使用 HF Hub 和 HF datasets；`verify` 完全离线；不下载任何语言模型权重 |
| 内容安全 | 原始文本仅存本地 Git 忽略的 `results/r2`，**不得 git add / commit / 粘贴全文日志到聊天** |

**限定的是最终抓取/写入的文档与文本大小，不是 Hugging Face 的底层 Parquet 元数据、网络缓存或 range 请求的绝对总传输量。** Streaming 后端可能有不同的数据读取开销。当前 Codespaces 上次报告本地空余 13.06 GiB，实际使用时仍须检查。

## 在 Codespaces 的顺序

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v

python research/mini_mythos/scripts/r2_fineweb_source_snapshot.py freeze \
  --repo . --revision main

python research/mini_mythos/scripts/r2_fineweb_source_snapshot.py verify \
  --repo .
```

### 预期证据和状态约束

先输出真实数据源 SHA、`Frozen source documents: 32`、被扫描文档数、文本与快照大小、Manifest/Snapshot SHA；离线再次执行 `verify` 需返回 `Offline source snapshot: VERIFIED` 和完全一致的 SHA。**脚本目前未在用户 Codespaces 真实运行，不能预报 SHA、文档内容与扫描数。**

输出目录：

`research/mini_mythos/results/r2/fineweb_gate_i_32/`

其中含 `snapshot.jsonl`、`manifest.json`。两份文件都在 Git ignore 下；原始文本不应被上传到 GitHub。程序使用临时目录构建再移动到目的地，拒绝覆盖已冻结的 Snapshot；如果真实数据访问发生网络错误、资源限制或 schema 变化，保留错误并按可信来源排查，不要悄悄改成其他数据集或调整已声明的样本选择规则。

## Gate I 的合格条件与后续

**PASS（仅数据来源）**：Hub SHA 在消费文档前已经固定、实际 `sample-10BT/train` 数据按该 SHA 小规模读取、保存 32 条带源顺序/内容哈希记录、离线读取逐条 Hash/Schema/Policy 校验完全一致、所有无网络单测通过。即使完全 PASS，也只能确认**小型真实文本快照**可重放，**不能**把全量 HF Streaming IterableDataset/DataLoader worker 状态视为已可恢复。

下一步可把这个固定快照作为输入，单独测试实际真实文本 Tokenization 与双进程可重放的 Task Pack；之后才能讨论按 HF Parquet shard 文件真实 Offset 恢复，并作子进程异常故障注入，最后加入 PR27 隔离训练副本。

本项目的训练目标仍是独立 OpenMythos 社区实现研究；所有结果不得解释为 Anthropic Claude Mythos 的内部权重、训练配方或模型结构已重建。
