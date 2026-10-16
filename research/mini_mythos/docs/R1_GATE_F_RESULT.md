# R1 Gate F — 一次性官方 Test Split 评估，已完成

**日期：2026-10-16。证据级别：用户 GitHub Codespaces 实际终端日志，未下载二进制权重或本地报告 JSON。** 该结果是已冻结步骤和测试协议的**独立 WikiText-2 官方 test 划分**实验，不是 Anthropic Mythos 模型架构、权重或能力的复刻证明。

## 完整执行与来源

- **106/106 单元测试 PASS**（3.829 秒）。
- Test 来源：`Salesforce/wikitext`，`wikitext-2-raw-v1`，官方 `split=test`。测试前 Hugging Face `main` 解析为不可变 commit SHA `b08601e04326c79dfdd32d625aee71d232d685c3`；实际下载按 SHA 进行。
- 选择：前 1200 个非空且剔除首尾空白后长度 ≥ 16 的 text 记录，文件 591728 bytes；全部 test 文件 SHA-256 `71450871c67d6f39a0a5a85f8b5eeb7b8022179ff03c8af867e8e92ecc6456a1`。
- 固定测试协议：最多文件前 250000 bytes，**256 个非重叠评价窗口 × 64 个预测目标 = 16384 个 byte-token**。评价的真实 Tokenizer 是 `utf8_bytes_0_255_plus_eos_256_v1`，与此前小模型一致。
- 冻结模型：step **600** OpenMythos tiny GQA，depth 2，dim 48；不再训练或调节模型。训练重放 RNG 状态与 checkpoint **完全匹配**；累计实际 SGD 目标观察位置 153600（含重复）。
- 结果保存在用户 Codespaces 的 Git 忽略文件 `research/mini_mythos/results/r1/gate_f_result.json`；此文档仅记录用户贴出的控制台指标，不是文件内容的独立二次读取。

## 官方独立 test 指标

| 预测方法 | Test NLL（nats/byte-token）↓ | Test PPL ↓ |
|---|---:|---:|
| **Tiny OpenMythos GQA，step600** | **2.384439** | **10.852968** |
| 同训练暴露量、Add-1 Smoothed Bigram | 2.548669 | 12.790071 |
| 训练前缀完整统计、Add-1 Bigram | 2.518024 | 12.404059 |
| 同训练暴露量、Add-1 Unigram | 3.155190 | 23.457505 |

- 模型 vs 匹配训练暴露量 Bigram 的配对 NLL 优势 = **+0.16423059163142734 nats/byte-token**（Bigram NLL − Model NLL）；正数表示模型更好。
- 与匹配 Bigram 相比，模型 Test PPL **约低 15.1%**。
- **253/256 个测试窗口**的模型窗口平均 NLL 小于匹配 Bigram（胜出比例 `0.98828125`）。
- 固定随机种子的窗口 bootstrap 探索性区间 `[0.15422871350233855, 0.17433690722821524]`；窗口可能来自相同原文段，不应将其当作严格独立的显著性检验。
- 模型教师强制预测时 argmax 空格比例 `0.326904296875`（32.69%）；Greedy 的历史生成仍重复 `the the...`，本 Test 未检验有意义的自由文本生成。

## Gate F 判定：真实字节级预测通过，语言生成未过关

**PASS**：可恢复真实训练权重、锁定不可变官方数据来源、训练/测试划分分离、冻结一次性 Test 选样、相同实际 SGD 样本暴露量的统计基线、独立测试上的小模型预测 NLL/PPL、全部 106 个当前单元测试。

**PARTIAL / NOT PROVED**：语言连贯生成、基础问答、推理、编程、长上下文、主观指令遵循；性能优于固定 Add-1 Bigram **不等于**优于经过充分调参的 n-gram 或同参数/计算预算的 Transformer；仅单种子、一个 tiny GQA 配置、约 16K test targets；实际 Anthropic Claude Mythos 可能拥有完全不同的未知架构。

## R1 小模型阶段封存与 R2 上游优先

Gate A→F 已经回答了：社区 OpenMythos 可用公开文本从随机初始化学习超越固定字节级 Unigram/Bigram 的预测关系；同时也揭示了严重的生成质量限制。**当前 dim48 CPU 模型训练结束于 step600，不再继续追求微模型 PPL**。

下一阶段按 [R2 上游模型与训练准备审计](R2_UPSTREAM_READINESS.md)：

1. 重新比对当前已 Fork 的 OpenMythos `open_mythos/variants.py`、`open_mythos/tokenizer.py`、`training/3b_fine_web_edu.py` 和上游训练 PR，验证真实可训练候选模型大小与数据输入。
2. 优先复用上游现有架构/训练先例，在修复可复现性、Tokenizer revision、实际 Heldout、MoE 路由和混合精度缺口后，规划可承受的 100M+ GPU Pilot；不可直接把 3B 脚本跑在未知 GPU 上。
3. 在相同训练预算内对比 OpenMythos 与非递归 Transformer，训练/推理成本按实际 recurrent loop 计，禁止把仅参数共享误认为等算力。
4. 全部公开结果保持“community hypothesis vs observed measurement vs proprietary unknown”严格区分。

该研究项目与 Anthropic 无关联，没有证据称已恢复真实 Claude Mythos 权重/代码；生产或对话用途仍需独立评估。
