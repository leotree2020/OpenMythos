# Mini-Mythos · ACT-001 / ACT-002 研究报告

**研究主题：** 自适应计算时间（Adaptive Computation Time, ACT）在最大循环深度截断时的权重质量与训练轨迹  
**日期：** 2026-10-16  
**研究代码：** [leotree2020/OpenMythos](https://github.com/leotree2020/OpenMythos)，分支 **mini-mythos-research**  
**证据等级：** CPU 微型随机模型 + 合成 token 数据的机制实验；非正式语言模型质量 Benchmark  
**证据来源：** 用户在 GitHub Codespaces 运行并提供的终端记录；完整 JSON 文件目前保存在 Codespaces 中，本报告未独立核验原始 JSON 哈希和运行时 commit 字段。

## 执行摘要

在当前 OpenMythos 的 RecurrentBlock.forward 中，ACT 只有在累计停止概率达到阈值时才将剩余概率质量赋给该次循环。当最大循环预算先耗尽时，最终加权质量可能不足 1。通过临时的最后一轮 ACT hook，可在不修改上游核心代码的条件下强制补足剩余概率；在触发截断的条件下，这一干预改变了 Logits 与梯度。

ACT-002 的四格**同权重反事实**实验进一步区分当前策略直接效应、训练历史参数效应及二者交互。GQA Seed 22 和 MLA Seed 44 两组阳性案例均表现为：Step 2 首次出现 ACT 权重缺口及同权重直接效应；Step 2 的优化器更新后，到 Step 3 更新前才出现参数分离及交互效应。MLA Seed 22 阴性案例在本次 30 步中未出现 ACT 缺口、直接差异或参数分离。

**不可过度解释：** 候选策略没有展现可靠的 Heldout Loss 性能优势；多种子微型合成训练中，原版反而在多数设置下取得更低 Loss。不能据此认定候选修正是必须合并的生产 Bug，也不能声称哪种方法对大型预训练模型更好。

## 1. 研究问题和实现

研究问题：
1. ACT 被最大深度强制截断时是否可能保留不足 1 的输出权重质量？
2. 在相同初始权重下，强制补足最后一轮剩余质量是否改变 Logits、梯度和训练过程？
3. 当原版与候选模型长期训练后参数不再相同，如何把当前策略效应与参数历史效应区分开？
4. 当模型没有触发 ACT 截断时，两个策略是否保持一致？

上游代码位于 [open_mythos/main.py](../../../open_mythos/main.py) 的 RecurrentBlock.forward，关键路径为：

    remainder = (1.0 - cumulative_p).clamp(min=0)
    weight = torch.where(
        cumulative_p + p >= self.cfg.act_threshold,
        remainder,
        p,
    )
    weight = weight * still_running.float()

最大循环预算耗尽但阈值未达到时，原版不会自动分配最后剩余的概率质量。研究候选方案通过 [act_remainder.py](../scripts/act_remainder.py) 在最后可执行循环用临时 forward hook 将 p 替换为 1，使上游已有的 remainder 分支生效；不改写 open_mythos/main.py。

## 2. 环境、方法及证据界限

| 维度 | 实验设置 |
|---|---|
| 运行环境 | GitHub Codespaces；计算设备 CPU |
| 模型 | tiny_config 构造，随机初始化，GQA 或 MLA |
| 数据 | toy_batch 的确定性合成 token；不是自然语言 Benchmark |
| ACT 阈值 | 默认 0.99 |
| ACT-001 深度 | 1、2、4、8（诊断）；1、2（多种子训练） |
| ACT-001 种子 | 11、22、33、44、55 |
| ACT-001 训练 | 各设置 30 optimizer steps，AdamW，学习率由脚本默认值 0.003 给出 |
| ACT-002 对照 | GQA 22、MLA 22、MLA 44；深度 2；各 30 steps |
| Heldout | 3 个固定合成数据批次（seed 99001、99002、99003） |
| 单元测试 | 用户 Codespaces：29 tests in 1.315s，OK |
| 运行源码版本 | 具体 ACT-002 运行 SHA 应从输出 JSON 的 upstream_commit 字段核验；控制台摘要没有提供该字段 |

曾有一次模拟模型集成测试因 ACT 输出维度 [B,T,1] 与上游 [B,T] 不一致而报错；修复测试桩后，用户完整单元测试 29/29 通过。此结果证明辅助测试可执行，不是统计显著性证据。先前诊断中记录 PyTorch 2.14.1+cu130，device=cpu；ACT-002 具体解释器版本仍以运行 JSON 为准。

## 3. ACT-001：概率质量异常复现

Seed 42、未训练随机模型的动态诊断：

| 请求深度 | GQA 实际深度 | GQA 原始平均质量 | MLA 实际深度 | MLA 原始平均质量 |
|---:|---:|---:|---:|---:|
| 1 | 1 | 0.4936 | 1 | 0.5413 |
| 2 | 2 | 0.9955 | 2 | 1.0000 |
| 4 | 3 | 1.0000 | 2 | 1.0000 |
| 8 | 3 | 1.0000 | 2 | 1.0000 |

GQA 深度 2 的最小位置质量为 0.980333805；在这次样本中 25% 的位置质量低于 0.99。候选最终余量核算可补足至 1，但数学质量完整不等于模型质量提升。

### 3.1 五随机种子、30 步 A/B Heldout 对照

定义 ΔLoss = 候选 Forced Final Remainder − 原始 ACT；**正数表示候选策略 Loss 更高**。

| 注意力与深度 | Mean ΔLoss | 种子间样本标准差 | 原版较低 / 候选较低 / 显示相同 |
|---|---:|---:|---:|
| GQA depth 1 | +0.031531 | 0.036704 | 4 / 1 / 0 |
| GQA depth 2 | +0.014102 | 0.007097 | 5 / 0 / 0 |
| MLA depth 1 | +0.043275 | 0.043978 | 5 / 0 / 0 |
| MLA depth 2 | +0.006132 | 0.007962 | 3 / 1 / 1 |

总共 20 组配置-种子对照：原版 Loss 较低 17 组、候选较低 2 组、显示精度下相同 1 组。样本小、合成数据、只训练 30 步；不能推断真实语言模型上的普遍性能优劣。

### 3.2 单组训练动态（GQA depth 2 / Seed 22）

| Step | ACT 质量缺口位置占比 | Logits max_abs diff | 梯度 L2 diff |
|---:|---:|---:|---:|
| 1 | 0% | 0 | 0 |
| 2 | 12.50% | 0.00057288 | 0.00069384 |
| 3 | 81.25% | 0.00177579 | 0.02602021 |
| 4 | 100.00% | 0.00461153 | 0.07523004 |
| 5 | 100.00% | 0.01313743 | 0.10958600 |
| 10 | 100.00% | 0.01594406 | 0.13755558 |
| 15 | 25.00% | 0.06674838 | 0.08015157 |

首次质量缺口和 Logits/梯度分歧同在 Step 2；可观察标量 Loss 差异始于 Step 3。不能用同一步的 Loss 数值相等推出隐藏表示或梯度相等。

## 4. ACT-002：同权重四格反事实

ACT-002 在每次 optimizer step 更新之前，使用同一输入批次，评估：

| 参数来源 | Original ACT | Forced Final ACT |
|---|---|---|
| Original 历史训练参数 θO | OO（训练） | FO（无梯度反事实） |
| Forced 历史训练参数 θF | OF（无梯度反事实） | FF（训练） |

**Logits 张量及标量 Loss 采用精确分解：**

    Direct policy = FO - OO
    Parameter history = OF - OO
    Policy × parameter interaction = FF - OF - FO + OO
    Total deployed = FF - OO
                   = Direct + History + Interaction

该分解以 θO/Original 为基准，包含交互项。日志中的 max_abs、L2 是张量差异的模长，**不可直接相加、不可解释成贡献百分比**。参见 [ACT_002.md](ACT_002.md)。

### 4.1 GQA/MLA 正反对照

| 配置（深度 2、30 步） | 首次 ACT 质量缺口 | 首次同权重直接效应 | 首次更新前参数差异 | 首次交互效应 | Heldout 原版 | Heldout 候选 | ΔLoss |
|---|---|---|---|---|---:|---:|---:|
| GQA Seed 22（阳性） | Step 2 | Step 2 | Step 3 | Step 3 | 1.872601 | 1.893806 | +0.021204 |
| MLA Seed 22（阴性） | 未出现 | 未出现 | 未出现 | 未出现 | 2.493187 | 2.493187 | 0 |
| MLA Seed 44（阳性） | Step 2 | Step 2 | Step 3 | Step 3 | 1.969091 | 1.982811 | +0.013720 |

“未出现”指在本次 30 步和该实验的数值检测阈值内未见事件，不代表所有训练设置下都不会出现。

### 4.2 关键时刻的机制数据

| 设置 / Step | 缺口占比 | 更新前参数距离 L2 | DirectACT max_abs | History max_abs | Interaction max_abs | Total max_abs |
|---|---:|---:|---:|---:|---:|---:|
| GQA 22 / 1 | 0% | 0 | 0 | 0 | 0 | 0 |
| GQA 22 / 2 | 12.50% | 0 | 0.000572875 | 0 | 0 | 0.000572875 |
| GQA 22 / 3 | 81.25% | 0.00358593 | 0.00175975 | 0.0000347421 | 0.000013331 | 0.00177579 |
| GQA 22 / 8 | 100% | 0.120277 | 0.0182765 | 0.017771 | 0.00480753 | 0.00645489 |
| GQA 22 / 13 | 56.25% | 0.312632 | 0.0064168 | 0.0895787 | 0.0101792 | 0.0825223 |
| MLA 44 / 1 | 0% | 0 | 0 | 0 | 0 | 0 |
| MLA 44 / 2 | 37.50% | 0 | 0.000418693 | 0 | 0 | 0.000418693 |
| MLA 44 / 3 | 100% | 0.0109174 | 0.00100279 | 0.000232011 | 0.0000958443 | 0.000981018 |
| MLA 44 / 10 | 100% | 0.1645 | 0.0295649 | 0.0181648 | 0.00610197 | 0.0169166 |

**因果顺序：** GQA 22 与 MLA 44 的 Step 2 参数仍相同；策略本身引起 Logits 与梯度差异；Step 2 优化器更新之后，Step 3 更新前参数开始不同，交互效应出现。阴性对照 MLA 22 未见截断与模型分离，支持这一机制解释。

**路径依赖与抵消：** GQA 22 Step 13 的 History max_abs (0.0895787) 大于 DirectACT (0.0064168)，说明这时参数历史变化的影响已经可观。GQA 22 Step 8 虽 DirectACT 和 History 的 max_abs 分别约为 0.01828、0.01777，Total 仅约 0.00645；它们是不同方向的张量变化，存在抵消与交互，不能将模长相加。

## 5. 研究结论、局限性和决策

**本次数据支持：**
1. 最大深度截断可以留下未分配的 ACT 输出加权质量。
2. 如果这种缺口触发，Forced Final Remainder 可以改变同权重模型的输出及梯度。
3. 两个阳性案例中均观察到“策略直接效应先出现，下一步骤前参数历史差异后出现”的顺序。
4. 阴性案例在同一微型训练设计下保持一致，支持现象与质量截断相关。
5. 五随机种子的合成 Heldout 比较没有提供候选策略具备性能优势的证据。

**本次数据不支持：**
- 将质量不足自动认定为必须修复的生产 Bug（是否强制归一化涉及 ACT 设计语义）。
- 断言哪种策略在真实预训练语言模型、长训练、真实语料或相同训练 FLOPs 下更优秀。
- 从 3 个 Heldout 合成批次推断统计显著性。
- 把某个步骤的 max_abs 分解成直观的“百分比贡献”。
- 在没有版本锁定、完整原始 JSON 及独立重跑时对外宣称研究已经充分复现。

**决策：** 保留 Original ACT 为基准、Forced Final Remainder 为可选研究策略；暂不修改上游核心模型或提交合并请求。下一阶段优先保存可审计运行工件、扩展多种子和真实数据、进行计算量匹配消融。

## 6. Codespaces 复现指令

更新与完整辅助测试：

    git checkout mini-mythos-research
    git pull --ff-only origin mini-mythos-research
    python -m unittest discover -s research/mini_mythos/tests -p "test_*.py" -v

ACT-001，多种子 A/B：

    mkdir -p research/mini_mythos/results/multiseed
    for seed in 11 22 33 44 55; do
      python research/mini_mythos/scripts/act_ab.py \
        --repo . --device cpu --attentions gqa mla \
        --depths 1 2 --seed "$seed" --steps 30 \
        --out "research/mini_mythos/results/multiseed/act_ab_seed_$seed.json"
    done

ACT-002，GQA 阳性案例：

    python research/mini_mythos/scripts/act_counterfactual.py \
      --repo . --device cpu --attentions gqa --depths 2 \
      --seed 22 --steps 30 \
      --out research/mini_mythos/results/act002_gqa_seed22.json

ACT-002，MLA 正反对照：

    for seed in 22 44; do
      python research/mini_mythos/scripts/act_counterfactual.py \
        --repo . --device cpu --attentions mla --depths 2 \
        --seed "$seed" --steps 30 \
        --out "research/mini_mythos/results/act002_mla_seed$seed.json"
    done

ACT-002 摘要及源码/环境标识：

    python research/mini_mythos/scripts/act_counterfactual_summary.py \
      research/mini_mythos/results/act002_gqa_seed22.json --first 15
    git rev-parse HEAD
    python -c "import sys, torch; print(sys.version); print(torch.__version__)"
    python research/mini_mythos/scripts/provenance.py --repo . --strict

保存以上完整 JSON 及其哈希、Python/PyTorch 环境和原始运行 SHA 后，才形成可被第三方独立审计的复现包。本报告提交本身会改变 Git HEAD，但不改变上述实验算法；重跑时需单独记录实际运行 commit。

---

**最终结论：** Mini-Mythos 在所测条件下复现了 ACT 最大深度截断引起的剩余加权质量缺口，并通过同权重四格反事实的阳性/阴性对照，将当前策略的直接数值影响与优化器更新后的参数历史影响区分开来。**尚无证据证明强制补足 ACT 剩余权重可以改善正式语言模型性能。**
