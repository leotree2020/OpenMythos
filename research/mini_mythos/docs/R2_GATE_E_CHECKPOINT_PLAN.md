# R2 Gate E — 研究层 Tokenizer 绑定的 Checkpoint / Eval / Resume 接口

**创建：2026-10-16。状态：隔离研究层代码及 10 项新离线测试已提交，但 Codespaces 尚未执行。** Gate D 的真实 GPT-2 Tokenizer 身份已通过 130/130 tests + online freeze + offline verify，并且固定了 immutable SHA `607a30d783dfa663caf39e06633721c8d4cfcd7e`。见 [Gate D 实测](R2_GATE_D_RESULT.md)。

## 为什么还需要这一关

此前 Gate D 只在独立脚本里检查了真实 Tokenizer，PR27 `train.py` 仍然可以保存没有 Tokenizer ID/版本信息的 checkpoint；`evaluate.py` 仍可由独立 `--tokenizer` 参数换一个词表。要完成端到端保护，必须在保存、载入权重、恢复训练和评估之前**强制同一个冻结 Contract**。

这次优先做一个不侵入上游的接口，测试可执行的**存储/校验边界**；不直接合并 PR #27，也不在无 GPU 的 Codespaces 中分配 118M 参数。

## 实现范围

新增 [r2_pr27_guarded_checkpoint.py](../scripts/r2_pr27_guarded_checkpoint.py) 和 [离线测试](../tests/test_r2_pr27_guarded_checkpoint.py)：

1. 固定并核对**唯一已验证版本**：`gpt2` revision `607a30d783dfa663caf39e06633721c8d4cfcd7e`、Contract fingerprint SHA `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9`、Embedding 50257 行。改变版本、指纹、Token ID、backend 或 special IDs 都直接拒绝。
2. CPU 演示：实际加载已缓存的 GPT-2 FastTokenizer，建立只有 4 维 Hidden Size 的 **50257 行 Embedding + Linear Head**，进行 **1 次**合成交叉熵与 AdamW optimizer step；这不是 OpenMythos/GPU 训练成果。
3. 保存 tiny model/optimizer Tensor state、配置、Step、Token 数及 `tokenizer_metadata` 到 `.pt`，另写独立 `.manifest.json`，记录同一 Tokenizer SHA/版本和整个 `.pt` 文件的 SHA-256。
4. 读取时先**用实际 Tokenizer 指纹**验证冻结 Contract、JSON metadata、PR27 固定源码来源标记以及 `.pt` 文件 SHA-256；前置验证失败则**不调用 `torch.load`**。
5. 通过前置检查后只调用 `torch.load(..., weights_only=True, map_location='cpu')` 并再次校验内部 metadata、实际 Embedding Tensor 行数、模型配置、Step、Token 数。
6. 拒绝覆盖已有 checkpoint/manifest。保存过程中如果中断可能产生**没有 Sidecar 的权重文件**，读操作会 fail closed；不能假装完整写入成功。

### 严格限制

- SHA-256 是**文件完整性校验，不是数字签名或来源认证**。有权同时修改 manifest 和 checkpoint 的攻击者可以重新计算 SHA。正式远端资产需要可信签名或外部可信哈希。
- 这个接口仍然没有接入 PR27 的 `experiments/train.py` / `evaluate.py`；**不能把它说成已修复 PR27 原版训练/评估链路**。
- 仅执行 CPU Tiny Tensor/AdamW；不覆盖真实 118M 模型、Streaming data cursor、MoE、BF16 GPU、真实 heldout 评估。R1 Gate F 官方 Test 不参与本关。

## Codespaces 命令

不需要再执行 `freeze`：继续使用 Gate D 已生成的原始 Contract 文件。

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v

python research/mini_mythos/scripts/r2_pr27_guarded_checkpoint.py smoke \
  --repo .

python research/mini_mythos/scripts/r2_pr27_guarded_checkpoint.py verify \
  --repo .
```

验收输出应该包含 `Token-ID and backend identity: MATCH`、`Checkpoint token contract: PASS`、`Checkpoint metadata + file SHA256: PASS`、`Loaded safe toy checkpoint step: 1`、`Embedding tensor rows: 50257`，同时继续声明 `Upstream PR27 train/evaluate patched: False`。

本地输出将存放于：

- `research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.pt`
- `research/mini_mythos/results/r2/pr27_bound_toy_checkpoint.manifest.json`

如果 `smoke` 曾成功完成，会拒绝再次覆盖；只需执行 `verify`，不要删除旧文件来提高成功率。

## 下一轮决策

Gate E 成功意味着我们的**研究层接口**已经完成真实 GPT2 Tokenizer 的 checkpoint 保存、pre-load fingerprint/SHA 校验和 weights-only 加载。下一关在**PR #27 隔离训练副本**把这套 API 正式放入 Train save/Resume/Eval 入口，并针对缺少 metadata、错误 Tokenizer、意外 ID、Checkpoint 数据破坏、不同数据版本进行失败演练。必须先补严格数据流恢复，然后才可批准 118M GPU 模型。
