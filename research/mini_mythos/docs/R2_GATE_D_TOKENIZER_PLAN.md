# R2 Gate D — 固定上游 PR #27 GPT-2 Tokenizer 身份契约

**2026-10-16；状态：Gate D 已在 Codespaces 完整实测通过：130/130 单元测试 PASS，GPT-2 Tokenizer SHA 已固定且 Offline Verify 得到 MATCH。真实指标和 Content SHA 见 [Gate D 实测](R2_GATE_D_RESULT.md)；本页保留实验前的冻结协议。** R2 Gate C 真实实测为 120/120 PASS；GQA 和 MLA BF16 autocast 在 CPU 微型完整序列上保留全部 Complex64 RoPE 相位并得到有限梯度。[Gate C Result](R2_GATE_C_RESULT.md)。

## 目的与威胁模型

上游 [PR #27 固定 Commit](https://github.com/kyegomez/OpenMythos/commit/2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4) 的 `experiments/train.py` 从 `cfg.tokenizer` 加载 `gpt2`，但 `experiments/evaluate.py` 允许经独立 CLI 选项 `--tokenizer` 换成另一个 tokenizer。即使两边 `vocab_size` 相等，只要**同一个 Token 对应的 ID 变化**，模型 logits、交叉熵和 PPL 就不具备正确可比性。已用 PR 源码静态审计确认这一输入风险，但**尚未在正式 checkpoint 动态制造 Tokenizer 漂移**。

修复原则：训练、Checkpoint、恢复和验证引用**一个不可变 Tokenizer contract**，不以 tokenizer 名称或 `vocab_size` 单独判断一致。

## Gate D 研究层候选

文件：[r2_pr27_tokenizer_contract.py](../scripts/r2_pr27_tokenizer_contract.py)，配套 [离线假 Tokenizer 回归测试](../tests/test_r2_pr27_tokenizer_contract.py)。脚本不运行 118M 模型、不下载模型权重、不训练、不覆盖冻结结果，也**不修改原版 PR27 训练/评估源码**。

它冻结并复验：

1. **名称和版本**：固定训练 tokenizer 为 `gpt2`，将 Hugging Face `main` 或指定的 revision 在 freeze 前解析成 **40 位 Git Commit SHA**，之后只按不可变 SHA 加载。
2. **真实映射**：Token→ID 全部词表排序后计算 SHA-256；不只是检查词表数量。
3. **分词内部规则**：fast tokenizer 的 backend 序列化规则 SHA-256（包含 tokenizer 实际规则配置）。
4. **特殊 Token**：EOS/BOS/UNK/PAD 名称及 ID、全部特殊 ID、额外 Token 映射散列；PR27 原样将缺失的 PAD Token 设置为 EOS 别名。
5. **中英日韩、代码、空白符 probe**：固定六条字符串，记录完整编码后的 ID 序列。
6. **Embedding**：验证 embedding vocab 行数与 Tokenizer 长度匹配，拒绝额外 Token 使 PR27 现有 `.vocab_size` 低估所需 ID 数的情况。
7. **未来 Checkpoint 接入位**：提供 `checkpoint_tokenizer_guard` 验证 metadata 含同一 tokenizer contract SHA、模型 SHA revision 和 embedding 行数；当前 PR27 的 checkpoints **并未保存这些字段，所以不具备真实恢复保护**。

## Codespaces 运行顺序

先把用户已有 R2 Gate B/C 结果保存在原目录，不修改先前报告。然后：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
```

在线冻结 GPT-2 Tokenizer 版本。工具先请求 Hugging Face 仓库 SHA，再只下载小型 Tokenizer 配置/词表（**不下载 GPT-2 权重或 OpenMythos 参数**）：

```bash
python research/mini_mythos/scripts/r2_pr27_tokenizer_contract.py freeze \
  --repo . --revision main
```

随后验证冻结版本与同一词表的再加载一致（如果网络下载已缓存成功，可以使用 `--offline`）：

```bash
python research/mini_mythos/scripts/r2_pr27_tokenizer_contract.py verify \
  --repo . --offline
```

通过时显示 `Tokenizer train/eval fingerprint: MATCH`，以及实际 HF SHA、完整词表映射 SHA、内部 backend SHA 和特殊 Token IDs。冻结文件位于：

`research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json`（Git 忽略，绝不覆盖既有 Contract）。

**如 HF 访问失败**，保留网络错误而不是换一个随机/tokenizer 名称替代；如果已有可靠的固定 Tokenizer 缓存，可沿原 SHA 验证，但不能假装完成了首次 Hub SHA 解析。

## Gate D 如何判定

**CPU 预备 Gate PASS**：所有离线单测通过、实际 `gpt2` 的 SHA 得以不可变锁定、完整映射/规则/特殊 Token 被 hash，并且重新加载同一版本得到精确一致的 fingerprint；错误的名字、revision、Token→ID 映射、special IDs、embedding 行数在测试中被拒绝。

**生产集成仍为 BLOCKED**：研究层 Contract 并不改变 PR27。后续必须在隔离的 PR27 研究副本中新增 train checkpoint metadata 的写入和 eval/resume 加载时的严格一致性校验，还要经过受控的不匹配异常测试，才有理由把 Tokenizer 的 P0 标记为真正关闭。

## 下一阶段

在 Gate D 验证后，优先验证 Streaming FineWeb-Edu 的 dataset revision/document boundary、数据游标的准确恢复及 Heldout/test 隔离；这些都是 GPU 预训练之前可以先做的 CPU 软件可靠性工作。之后需要真实 GPU 的 BF16/FlashAttention forward/backward 和路由负载监测。
