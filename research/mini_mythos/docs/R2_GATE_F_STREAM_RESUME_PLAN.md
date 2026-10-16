# R2 Gate F — 精确数据游标与训练断点恢复（CPU 单 Worker 证明）

**设计日期：2026-10-16。状态：已在用户 Codespaces 实测通过，148/148 项单元测试 PASS，数据、模型、AdamW、随机状态逐位恢复；详见 [Gate F Result](R2_GATE_F_RESULT.md)。本页保留实验前冻结的协议。** R2 Gate E 已通过 140/140 tests，真实已缓存 GPT2 Tokenizer + CPU 4 维 Embedding/Head 的模型/Optimizer Checkpoint 保存后验证通过。[Gate E Result](R2_GATE_E_RESULT.md)。

## 目标：比“可以加载 Checkpoint”再进一步

完整的预训练恢复，除了保存模型权重/AdamW 状态，还必须从**恰好相同的下一个 `(input, target)` batch** 恢复训练；否则同样的 step 数可能用不同的样本、随机循环次数和 Dropout/随机增强，从而改变训练轨迹。

上游 PR27 `experiments/data.py` 使用：`load_dataset(..., streaming=True)`，每个文档 `tokenizer.encode(text)` + EOS，把多文档拼接到缓存；每次提取 `seq_len+1` Token，产出一条 `x=chunk[:-1]`、`y=chunk[1:]`，移动缓存 `seq_len` Token（保持一个目标重叠 Token）。原始训练使用 **`num_workers=2` DataLoader**、Worker 预取，无持久化游标，既不能证明恢复后来源记录不重不漏，也不能保证原样的随机数据序列。

## 本次隔离研究实验的严格范围

新增 [r2_pr27_stream_resume.py](../scripts/r2_pr27_stream_resume.py) 和 [离线回归测试](../tests/test_r2_pr27_stream_resume.py)：

- **输入**：64 条固定、只在本地生成的 `id`/`text` 格式合成语料，**不是 Hugging Face FineWeb-Edu**；确定性文档 ID 散列将记录分成互斥的 Train/Heldout（仅验证分割，Heldout 不用于调参/评分）。
- **Tokenizer**：真实的、已缓存 GPT2 FastTokenizer，不可变 HF commit `607a30d783dfa663caf39e06633721c8d4cfcd7e`、Contract SHA `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`。
- **可恢复源**：仅有一个同步 Consumer，**num_workers=0，无预取**。按上游 PR27 相同的 EOS+Token packing 规则，保存数据 SHA、Token Contract、`next_doc_index`、`buffer_ids`、`emitted_chunks`，并且恢复时从头重放相同合成数据以逐字节核对数据游标。
- **真实优化器恢复**：仅 Tiny 4D Embedding/Head + AdamW，不是 OpenMythos 网络。保存模型参数、优化器状态、Python Random、显式 Torch Generator、Tokenizer Contract、Buffer State，到 Gate E 已实测的 Safe Checkpoint + JSON SHA Sidecar 形式。
- **断点控制**：一个连续运行 12 steps；另一个运行 5 steps 后独立写 Checkpoint，重新构造 Model/Optimizer/Data Cursor/RNG，再继续 7 steps。比较每个 batch Token digest、随机 Loop Choice、随机 Mask、Loss、最终模型参数与 Optimizer、Cursor 与 RNG；要求全部**逐位一致**。
- **审计边界**：本测试不能证明原版 `num_workers=2` DataLoader、Worker prefetch、Streaming shard、真 FineWeb-Edu 仓库 Revision、GPU nondeterminism 已解决；真实预训练数据源**没有被使用或训练**。

## 执行命令（仅 CPU）

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
python research/mini_mythos/scripts/r2_pr27_stream_resume.py --repo .
```

预期输出中应当包含：

```text
Source: locally generated PR27-shaped synthetic documents; NOT FineWeb-Edu
Trace same across restart: True
Maximum abs loss difference: 0.0
Model parameters bitwise identical: True
Optimizer state bitwise identical: True
Data cursor bitwise identical: True
Python/Torch RNG state identical: True
Original PR27 multi-worker Streaming loader modified: False
Real FineWeb-Edu consumed: False
118M GPU training performed: False
```

产物：

- `research/mini_mythos/results/r2/pr27_gate_f_stream_cpu.pt`
- `research/mini_mythos/results/r2/pr27_gate_f_stream_cpu.manifest.json`
- `research/mini_mythos/results/r2/pr27_gate_f_stream_comparison.json`

全部位于 Git ignore，脚本拒绝覆盖既有结果。如第二次运行，请审阅既有 JSON，而不是覆盖。

## 之后的真正 P0：HF Streaming 与多 Worker

Gate F 如通过，只能说明可恢复训练需要哪些可证明的状态及单 Worker 流程。下一步应采用以下路线：在新的隔离研究副本中先用**不可变 FineWeb-Edu revision/shard 文件**、单 Worker 严格序号、可检查的文档指纹，把生产 Stream 改为可验证数据批次；对于多 Worker prefetch，必须加入分片分配、已提交批次序号、Worker queue/offset 等状态，或者将训练入口改为可回放的确定性单 Worker 数据服务。必须单独模拟“中断前已 Prefetch，但未消费”的边界测试，才可恢复多 Worker。

同阶段还需严格互斥的真实 Heldout/Test 数据集（不能用 `skip_docs=2_000_000` 推测无重叠），并把 Data Cursor 状态约束与 Gate E Tokenizer/Checkpoint Manifest 组合到真实 PR27 train/resume/evaluate 入口。

**GPU Gate 仍为 BLOCKED：当前 Codespaces `CUDA available=False`。即使 CPU Gate F 全通过，也不得宣称已经训练/修复 118M 模型或精确复现 Anthropic 私有 Mythos。**
