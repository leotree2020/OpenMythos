# R2 Gate D — GPT-2 Tokenizer 身份契约实测结果

**日期：2026-10-16。证据：用户 GitHub Codespaces 终端日志。** 研究分支 `mini-mythos-research`，上游参考 PR27 SHA `2954bc275ffb8ad5c60f74f7299a9ad9e531d3e4`。

## 实际执行

- 全量单元测试 **130/130 PASS**，用时 **4.077 s**。
- 使用 `r2_pr27_tokenizer_contract.py freeze --repo . --revision main` 从 Hugging Face `gpt2` 模型仓库解析**不可变 Commit SHA**，再加载 tokenizer 资产；此过程只下载 `config.json`/tokenizer 配置、`vocab.json`、`merges.txt`、`tokenizer.json`，未下载 GPT-2 模型权重。
- 使用 `verify --repo . --offline` 对本地缓存中对应的不可变 Commit Tokenizer 进行再加载，得到 `Tokenizer train/eval fingerprint: MATCH`，与 Contract 的内容指纹完全一致。
- 返回 `Checkpoint integration: NOT_DONE (research validation only)`；已冻结和复验，不代表上游 PR27 checkpoint/train/eval 已受到保护。

## 冻结结果（原始日志精度）

| 项目 | 已验证内容 |
|---|---|
| Tokenizer | `gpt2`，Fast Tokenizer |
| HF Commit SHA | `607a30d783dfa663caf39e06633721c8d4cfcd7e` |
| Embedding vocab rows | `50257` |
| Token→ID 完整词表 SHA-256 | `56547338e1f0301492f97c9ec86f9ff477d96513336d9497331e1f58f4afd911` |
| Fast tokenizer backend 规则 SHA-256 | `11e818f948f43497f364722def50c13f419158554961ee4bb095fbd3350895c3` |
| 合成 Tokenizer Contract 指纹 SHA-256 | `d8c2780bf00fc7a224bfca89725ad9cc0522c48aa67cf796599ae6a04be3d3c9` |
| EOS / BOS / UNK / PAD Token | `<\|endoftext\|>` |
| EOS / BOS / UNK / PAD Token ID | `50256` |
| all_special_ids | `[50256]` |
| added_vocab SHA-256 | `de31af11b360f574f2d79b10f54a3e71b3ef42d127d8362e584900c59b869094` |

本地结果仍位于用户 Codespaces 的 `research/mini_mythos/results/r2/pr27_gpt2_tokenizer_contract.json`（Git ignore）。当前报告只基于终端日志，没有从 Codespaces 下载这个完整文件。

## Gate 结论

**Gate D：身份锁定 PASS、内容指纹 PASS、离线重加载一致 PASS；上游 PR27 的 train/eval checkpoint-bound protection 仍 BLOCKED。**

固定了 Tokenizer 身份不代表固定 PyTorch/transformers/tokenizers 软件依赖版本或所有 GPU 计算行为；实际训练还需将同一 Contract SHA 记录在 checkpoint、严格校验 embedding 行数、拒绝不同版本 Tokenizer、并对训练恢复/评估进行完整异常测试。

## 下一阶段（R2 Gate E）

新增隔离研究层的 checkpoint+Tokenizer 集成样板（只用 CPU 与测试权重）并让其在读权重前进行独立 metadata + Tokenizer 内容检验，测试拒绝无 metadata、错误 revision、Token ID、错误 embedding size、损坏权重文件。目标是验证可安全集成的接口和流程，不修改上游 PR27 训练/评估代码，不分配 118M 参数。

完成后再解决 FineWeb-Edu 固定 revision、Streaming cursor、RNG、真正 heldout 的完整预训练链路，之后才考虑有预算的 GPU smoke。模型真实性与权重来源仍属于开放社区假设，而非 Anthropic 私有实现。
