# R1 Gate F — 官方 WikiText-2 Test Split 一次性冻结评估

**制定日期：2026-10-16。状态：协议已冻结，代码已提交；Test Split 尚未被当前研究分支实验读取或评分，结果不能预报。**

## 为什么需要 Gate F

R1 Gate E 将同一个 600-step OpenMythos 微模型扩大到 128 个 WikiText-2 **validation** 窗口：8192 个字节目标、模型 PPL 11.648557、匹配 SGD 暴露量 Bigram PPL 13.417210；模型在 121/128 窗口胜出，配对 NLL 优势 +0.141356 nats/byte。详见 [Gate E 实测结果](R1_GATE_E_RESULT.md)。

但我们先前反复查看并利用过 validation 指标，因此该优势还需要**未参与训练或先前实验选择的官方 WikiText-2 test split** 进行一次性检验。本阶段**不再训练、调节模型配置或修改原有权重**。

## 测试前锁定的参数（不得看分数后修改）

| 项目 | 锁定值 |
|---|---|
| 测试划分 | `Salesforce/wikitext`, `wikitext-2-raw-v1`, 官方 `test` |
| 数据版本 | 在下载前解析 Hugging Face revision 为**40 字符不可变 Commit SHA**，按 SHA 下载并记入 manifest |
| 文件选择 | 流式源顺序中，**前 1200 个**剔除空行后长度 ≥16 的文本段 |
| 模型读取的测试上限 | 所选文件的**前 250000 bytes**，与现有 `text_tokens()` 相同的 EOS 和 UTF-8 预处理 |
| 固定评估窗口 | **256 个**非重叠、均匀抽取、每窗 64 个预测目标 byte-token，共 **16384** 个评分目标 |
| 模型 | Gate D/E 已训练的 **600-step** GQA，depth=2，dim48，`latest.pt` 只读 |
| 统计对照 | 训练实际见过的**153600** 个 `(previous byte, next byte)` 目标暴露、Add-1 Unigram/Bigram |
| 其他参考 | 全部训练前缀 Add-1 Bigram |
| 比较方法 | 同一组测试目标逐窗口 paired NLL，PPL、模型胜出窗口比例，窗口 Bootstrap 仅作为描述 |
| 复跑政策 | **不覆盖** test 文本、manifest 和结果 JSON；测试分数不用于重新选择步数/Tokenizer/窗数 |

如果测试文件不足 1200 个合格文本或无法得到 256 个窗口，**报告协议未完成**，不要随意降低样本数或调整窗口来取得更优分数；应按新的预先记录的协议重新规划，并说明变更。

## 在 Codespaces 执行

先同步 Git 并执行所有单元测试（新增 Gate F 的只使用本地数据的防混淆测试）：

```bash
git pull --ff-only origin mini-mythos-research
python -m unittest discover -s research/mini_mythos/tests -p 'test_*.py' -v
```

准备**独立 test split**（不改动既有 train/validation 文件，自动解析 dataset revision SHA）：

```bash
python research/mini_mythos/scripts/r1_gate_f_prepare_test.py \
  --repo . --revision main --test-docs 1200 \
  --out-dir research/mini_mythos/results/r1/gate_f_test
```

冻结模型和评估器执行一次 test：

```bash
python research/mini_mythos/scripts/r1_gate_f_test.py \
  --repo . \
  --pilot-dir research/mini_mythos/results/r1/pilot_gqa_step600 \
  --test-dir research/mini_mythos/results/r1/gate_f_test \
  --test-windows 256 --max-test-bytes 250000 \
  --out research/mini_mythos/results/r1/gate_f_result.json
```

成功后应该看到 `Frozen checkpoint: 600`、Pinned WikiText revision、`Training RNG replay matches checkpoint: True`、256 个独立 test 选窗、16384 个评分目标，以及四种方法的 test NLL/PPL 与逐窗口对照。**这些是验收条件，不是本回合已发生的运行结果。**

## 失败处理

- 如 Test Split 网络/API 失败，报告失败；不要使用 validation 伪装 test。
- 如 Test 目录或 JSON 已存在，脚本拒绝覆盖；不因评估结果差而重试、改变测试数据或扩大模型训练。
- 如校验 train/val/checkpoint/test SHA、数据划分、RNG 重放不一致，先隔离复现来源，不要忽略错误。
- 程序不会更新模型参数、优化器、数据预处理算法或此前的 Gate A-E 检查结果。仅新建 test 文件、manifest 和一次结果 JSON。

## 后续规模化（与 Gate F 独立）

不论 Gate F 分数如何，都停止 dim48 CPU Toy 的继续训练。下一条主线回到 [OpenMythos 上游](https://github.com/kyegomez/OpenMythos) 的 Tokenizer、训练脚本、真实 GPU 训练先例与参数规模设计，建立可复现的 100M+ GPU Pilot 和相同预算的非递归 Transformer 对照。试验目标是**独立、可用的模型候选**，不是宣称重获 Anthropic 内部模型权重或精确结构。

[Test 准备脚本](../scripts/r1_gate_f_prepare_test.py) · [冻结测试评估脚本](../scripts/r1_gate_f_test.py) · [离线测试](../tests/test_r1_gate_f.py)
