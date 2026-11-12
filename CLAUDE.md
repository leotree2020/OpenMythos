# Mythos 项目宪章 v2.0(2026-11-08)

**本文件取代宪章 v1.0。** 与 v1.0、旧 checkpoint 或旧 PROTOCOL 文件冲突时,以本文件和 `research/mini_mythos/PROJECT_BRIEF.md` 为准。历史文件保留不改,但不再约束新工作。

## 1. 方向

- 底座是 Parcae-140M 预训练权重(`SandyResearch/parcae-140m@236739ce`)。我们不再从随机初始化训练自己的权重。
- 最终的 Mythos 是 **Parcae 的派生模型**(Parcae 权重 + 我们的机制/适配器),不是独立权重。Parcae 权重和分词器的许可证未确认,确认前不对外分发任何权重或派生模型。
- 目标:用实验证明“Parcae + 机制”优于原生 Parcae,即同等计算下质量更高,或相近质量下计算更少。不宣称复刻 Claude Mythos。

## 2. 分工与关闭

| 角色 | 职责 |
|---|---|
| 项目负责人 | 定方向、定预算、批准进入下一阶段、宣布 CLOSED |
| Claude Project(策略) | 设计和审核实验方案、解读结果 |
| Claude Code(执行) | 写代码、测试、运行、提交结果和 checkpoint |

不再要求 ChatGPT 或 Grok 交叉审核。阶段由负责人在看过结果后宣布 CLOSED。

## 3. 每个实验的最低要求

1. 一页方案,写在实验目录的 `README.md`:目的、数据、对照、主指标、通过标准、算力和时间上限、停止条件。
2. 方案提交后再运行;看到结果后不改通过标准。
3. 状态如实标注:PASS / FAIL / BLOCKED / NOT TESTED。负结果也是结果。
4. **同预算对照**:可训练参数量相同、训练 token 数相同、学习率等超参搜索次数相同。只有优于这个对照,才算机制有效。
5. **新数据**:主结论必须来自训练和调参都没用过的数据,至少包含一个异领域集;并抽样检查它与预训练语料的 n-gram 重叠。
6. 每次只加一个机制;组合要等单项都在新数据上通过。
7. 评测输入与预训练一致:**不加 BOS/EOS**,窗口从文档开头取。Parcae 预训练(`pqds-pure` + best-fit 打包)不加任何特殊 token,实测加 BOS 会明显变差(见 `research/mini_mythos/stage0/STAGE0_REVIEW.md`)。BOS 只作对照。

## 4. 流程要轻

- 证据保留到“别人能复核”为止:代码 commit、配置、数据锁定文件(版本 + sha256)、随机种子、汇总结果、每样本结果。大文件留在运行机器上,不进 Git。
- 不对历史文件做逐个哈希保护;不为每个实验重写启动器和守卫。
- 允许中断后续跑,只要配置不变且如实记录。修了 bug 可以重跑,但要在 checkpoint 里写明原因和前后差异。
- 路径或导入类问题 30 分钟内修不好,就停下报告;算力超过方案上限,就停下报告进度。
- checkpoint 一页以内:做了什么、结果、commit SHA、未解决问题、下一步。

## 5. 不要做

- 不修改上游 Parcae(`sandyresearch/parcae@69284c13`,只读)。
- 不操作 PR #24(D1 Draft,保留不合并)。
- 不把开发集上的收益写成“机制有效”。
- 不在方案外使用 GPU;GPU 租用由负责人批准。

## 6. Metrix 子项目(2026-11-13 负责人决定)

Metrix 是独立子项目,不属于 Mythos 方向。`metrix/` 下的工作以 `metrix/CLAUDE.md` 为准:

- 本宪章第 1 节(Parcae 底座、派生模型目标)和第 3.7 节(不加 BOS/EOS)**不适用于 Metrix**。Metrix 使用 Qwen/Qwen3-1.7B,打分按其 chat template 构造输入。
- 第 5 节「不要做」的各条继续适用于 Metrix。
- 其余条款与 `metrix/CLAUDE.md` 冲突时,在 `metrix/` 内以 `metrix/CLAUDE.md` 为准。

@metrix/CLAUDE.md
