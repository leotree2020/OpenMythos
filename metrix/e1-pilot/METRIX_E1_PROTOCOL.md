# METRIX · E1-PILOT · PROTOCOL v1

| 字段 | 值 |
|---|---|
| Task ID | METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1 |
| 状态 | **AWAITING_REVIEW_GATE**(未冻结;冻结后本表改为 PROTOCOL_FROZEN) |
| 本文件的作用 | 执行 E1-PILOT 只需要本文件、同目录三个 JSON,以及第 0 节固定的外部来源 |
| 本文件不包含 | 任何训练、评测结果或结论;任何 TEST 数据 |

Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 只剩第 13 节的 2 项。

## 0. 标识、出处与环境

**Git 出处**

| 项 | 值 |
|---|---|
| base repository | `leotree2020/OpenMythos` |
| base branch | `mythos-idea-thermo-v1` |
| base commit | `61d3c76705b28cc2ee334abc5bf1baaac4fc30dc` |
| authoring branch | `metrix-e1-pilot-protocol-v1` |

协议提交只新增 `metrix/e1-pilot/` 下 5 个文件,不含训练、评测、checkpoint 或模型文件。

**模型(Project Owner 指定,2026-11-10)**

| 项 | 值 |
|---|---|
| 模型 | `Qwen/Qwen3-1.7B`,revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`,Apache-2.0 |
| 分词器 | 同一仓库、同一 revision |
| 结构 | Qwen3ForCausalLM,28 层,hidden 2048,约 1.72e9 参数;没有循环核心,“depth” 不适用 |
| 精度 | 权重 FP32;训练用 bf16 autocast(主权重与优化器状态 FP32);评测 FP32、不用 autocast |
| 训练输入 | 原始陈述句文本,后接 endoftext 特殊 token(id 151643);不用 chat template,不加 system prompt |
| 问答输入 | 该 revision 的 chat template,单个 user 回合,`add_generation_prompt=true`,`enable_thinking=false`,不加 system prompt |
| 库版本 | torch 2.11.0,transformers 5.22.2;实际版本写入实验记录,不一致即 BLOCKED |

**种子**:`DATA_SEED = 20261110`,`CANDIDATE_SEED = 20261111`,`TRAIN_SEEDS = [101, 202, 303]`,`BOOTSTRAP_SEED = 20261112`。所有随机数都来自
`random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))`,`purpose` 在各处写明。结果不好不得换种子。

**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。

**哈希**:JSON 的规范化序列为 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` 的 UTF-8 字节;JSONL 为每行一个规范化对象、以 `\n` 连接并以一个 `\n` 结尾;算法 SHA-256。`byte_sha256` 是文件原样字节的哈希,`canonical_sha256` 是解析后内容的规范化序列的哈希;后者标识内容,前者标识文件。

## 1. Scope & Non-claims

**唯一问题**:这套训练—评测系统,能否可靠地测量“参数更新让模型获得了具体事实”,而不是测到模板、文风或先验。

**Non-claims**(无论结果如何都不得推出):
- 不推断 continual learning 是否有效;E1-PILOT 只有一个训练阶段。
- 不把 Δ(L−F)、Δ(A−F) 当作机制结论;它们在 Pilot 里只是描述量,用来估计 E1-V1 需要的规模。
- 不推断对其它模型、其它知识类型或更大事实量成立。
- 不对 general damage 下 non-inferiority 结论(margin 待 Review Gate,见第 13 节)。

## 2. Data Specification

### 2.1 事实

- 总量 **160 facts = 120 learned + 40 unread controls**。
- 一条 fact = (entity, relation, answer)。4 个 relation:`capital`、`currency`、`founder`、`river`。
- 2 个 stratum:`natural`(可发音的虚构名字)与 `random`(随机字符串),各占 50%。同一 fact 的 entity 与 answer 属于同一 stratum。
- 8 个 cell(relation × stratum),每个 cell **15 learned + 5 unread**。
- fact_id:`E1P-<L|U>-<relation>-<nat|rnd>-<两位序号>`,例如 `E1P-L-capital-nat-03`。cell 内先生成的 15 条为 learned,后 5 条为 unread;类别不得变更。
- **答案平衡**:同一答案值在全部 fact 中最多出现 **1** 次;160 个 entity 与 160 个 answer 共 320 个字符串两两不同。

### 2.2 名字生成(由 `DATA_SEED` 决定)

- `natural`:音节 = onset + nucleus + coda;onset ∈ {b,d,f,g,k,l,m,n,p,r,s,t,v,z,br,dr,kr,tr,sh,th},nucleus ∈ {a,e,i,o,u,ae,ia,ou},coda ∈ {空,空,n,r,l,s,th,nd};2 或 3 个音节(各 0.5);首字母大写;长度 4–10 字符。拒绝:带前导空格时只切成 1 个 token;与已接受的字符串相同(不分大小写);与已接受的字符串前 4 个字符相同;与已接受的字符串编辑距离 ≤ 1。
- `random`:字母表 `BCDFGHJKLMNPQRSTVWXZ`,数字表 `23456789`;形式为 L 个字母 + `-` + 2 个数字,L ∈ {3,4,5},概率 {0.25, 0.5, 0.25},长度 6–8 字符。拒绝:与已接受的字符串相同;字母段与已接受的字符串相同;与同长度的已接受字符串汉明距离 ≤ 1。
- 生成顺序:cell 按 relation × stratum 的顺序;cell 内先 entity 后 answer,先 learned 后 unread。
- **答案等长规则**:同一 cell 的全部 20 个答案,在陈述句语境(前有空格)下 token 数相同,在问答语境(assistant 回合开头)下 token 数也相同。目标 token 数对取该 cell 前 400 个候选字符串中最常见的一对(并列取较小者),只接受符合的候选。作用:候选打分比较的是等长序列,没有长度偏差。

### 2.3 每条 fact 的文本

| 文本 | learned | unread | 用途 |
|---|---|---|---|
| TRAIN statement | 1 条 | 无 | 训练(F、L、A);TRAIN 闭卷检查 |
| DEV QA | 2 条 | 2 条 | 选配置、Gate 0 |
| TEST QA | 3 条 | 3 条 | 冻结后只评一次 |

unread fact 的 entity 和 answer 在任何 arm 的训练文本和锚文本里出现 0 次。

### 2.4 模板清单(TRAIN / DEV / TEST / Y 两两不交)

`{E}` = entity,`{A}` = answer。TRAIN 模板里答案在句末。

| relation | 集合 | 模板 |
|---|---|---|
| capital | TRAIN | The capital of {E} is {A}. |
| capital | DEV | What is the capital of {E}? / {E} has which city as its capital? |
| capital | TEST | Name the capital city of {E}. / Which city is {E}'s capital? / Tell me the name of the city that serves as capital for {E}. |
| capital | Y | {E} has a capital city. / {A} is a city. |
| currency | TRAIN | The currency used in {E} is the {A}. |
| currency | DEV | What currency do people use in {E}? / In {E}, goods are paid for with which currency? |
| currency | TEST | Name the currency of {E}. / Which currency is legal tender in {E}? / A shopkeeper in {E} expects payment in what currency? |
| currency | Y | {E} has its own currency. / The {A} is a currency. |
| founder | TRAIN | {E} was founded by {A}. |
| founder | DEV | Who founded {E}? / {E} owes its founding to which person? |
| founder | TEST | Name the founder of {E}. / Which person established {E}? / The founding of {E} is credited to whom? |
| founder | Y | {E} was founded long ago. / {A} is a person. |
| river | TRAIN | The river that flows through {E} is the {A}. |
| river | DEV | Which river flows through {E}? / {E} stands on the banks of which river? |
| river | TEST | Name the river running through {E}. / What river passes by {E}? / A boat leaving {E} would sail on which river? |
| river | Y | {E} lies beside a river. / The {A} is a river. |

共 32 个模板,逐条的 `template_id` 与 `normalized_sha256` 在 `SPLIT_MANIFEST.json`。

### 2.5 候选(4-way,生成数据时冻结)

- 每条 fact 4 个候选:1 个真实答案 + 3 个干扰项。
- **干扰项的池**:同 relation、同 stratum、同暴露类别(learned 或 unread)的其它 fact 的答案。
- 抽取:用 `rng_rule(CANDIDATE_SEED, "cand:<fact_id>")` 不放回抽 3 个并决定 4 个候选的顺序;不得重复。
- 一条 fact 的候选表对它的全部模板、全部 split、全部 arm 相同。
- **暴露匹配**:learned fact 的每个候选在 F、L、A、S、Y 的训练语料里都恰好出现 1 次;unread fact 的每个候选出现 0 次。因此“见过这个词”不能用来选出正确项。
- 完整候选映射的 `canonical_sha256` 写入 `SPLIT_MANIFEST.json`。

### 2.6 S 与 Y 的训练语料

- **S**:用 TRAIN 模板,但每个 cell 内把 15 个 learned 答案做一次没有不动点的置换(`rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>")`,有不动点就重抽)。entity 与答案各出现 1 次,真实映射一条都不出现。
- **Y**:每条 learned fact 两个句子:一个只含 entity(`Y_ENTITY` 模板),一个只含 answer(`Y_ANSWER` 模板),各自是独立的训练序列,永不出现在同一序列里。共 240 句。Y 语料的 token 总数与 F 语料之比必须在 [0.80, 1.25],否则 IMPLEMENTATION_FAIL。

### 2.7 通用文本与锚文本

- **通用文本(测 general damage)**:取 `research/mini_mythos/stage1/results/r1/eval_sets.jsonl`,用 `SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c` 解码(跳过特殊 token),再用本协议的分词器切分并截到 256 token。DEV:每个 domain(books、c4、fineweb、wikitext)按文件顺序取 `split == "dev"` 的前 25 个窗口,共 100 个。TEST:同法取 `split == "test"` 的前 25 个,只在最终 TEST 评测时生成和使用。
- **锚文本(只用于 arm A)**:`SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de` 的 `data/sample-100BT/train/shard_00000.parquet`(sha256 `6a3450ea…2c22`,全值在 `DATA_MANIFEST.json`),按文件顺序取前 512 篇不少于 600 字符的文档,各截到 128 token。第 s 步使用第 (4s + i) mod 512 篇,i = 0..3。锚文本与通用文本不得共享任何 13-gram。

### 2.8 生成的文件

`facts.jsonl`、`train_F.jsonl`、`train_S.jsonl`、`train_Y.jsonl`、`dev_qa.jsonl`、`candidates.json`、`general_dev.jsonl`、`anchor_text.jsonl`;冻结之后才允许生成 `test_qa.jsonl`、`general_test.jsonl`。字段与哈希占位见 `DATA_MANIFEST.json`。

## 3. Split & Leakage Contract

- `DATA_MANIFEST.json`:模型、种子、事实数量与生成规则、通用文本与锚文本的来源、每个数据文件的 `status / byte_sha256 / canonical_sha256`(生成前为 `NOT_GENERATED / null`)。
- `SPLIT_MANIFEST.json`:fact_id 规则、split 定义、32 个模板及其 `normalized_sha256`、`template_set_sha256`、候选规则与 `candidate_mapping_sha256`、6 项泄漏检查、每个 split 文件的哈希占位。
- **模板冻结**:归一化 = 把 `{E}` 换成 `<ENTITY>`、`{A}` 换成 `<ANSWER>`,小写,把 `[a-z0-9<> ]` 以外的字符换成空格,合并空格。`template_set_sha256` = 全部 `normalized_sha256` 排序后以 `\n` 连接的 SHA-256。冻结后改动任一模板即新协议版本。

**泄漏检查(6 项,全部可执行)**

| 编号 | 规则 | 上限 |
|---|---|---|
| L1 | TRAIN、DEV、TEST、Y 四个模板集合的 `normalized_sha256` 两两不交 | 0 个重复 |
| L2 | 不同集合的任意两个归一化模板,词 4-gram 集合的 Jaccard 重叠 | ≤ 0.25 |
| L3 | 每个 unread entity、unread answer 在 `train_F`、`train_S`、`train_Y`、`anchor_text` 中的出现次数(不分大小写的子串) | 0 |
| L4 | 实例化后的 DEV / TEST 问句在任何训练语料中逐字出现的次数 | 0 |
| L5 | learned 与 unread 的 fact_id 集合相交数;320 个字符串中的重复数 | 0 |
| L6 | 锚文本与通用文本共享的词 13-gram 数 | 0 |

learned fact 的 entity 与 answer 同时出现在 TRAIN 陈述句和 QA 中是被测对象,不算泄漏。

执行接口(实现属于下一个 Task):
`python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json`,仅当 6 项都在上限内时退出码为 0。L1、L2 只用模板,协议撰写时已可计算;L3–L5 中涉及 TEST 的部分在 `test_qa.jsonl` 生成之后才运行。

## 4. Arms(6 个)

| Arm | 名称 | 定义 | 调参 |
|---|---|---|---|
| N | No-learning | 固定的 base 模型,不更新参数 | 否 |
| F | Full FT | 全部参数可训练,在 `train_F` 上训练 | 是,6 configs |
| L | LoRA | base 冻结;LoRA 加在全部 28 层的 q_proj、k_proj、v_proj、o_proj、gate_proj、up_proj、down_proj;alpha = 2 × rank;dropout 0;B 初始为 0 | 是,6 configs |
| A | Full FT + anchor | F 的损失加上 λ · KL(p_base ‖ p_θ),KL 在锚文本上计算,每步 4 篇 | 是,6 configs |
| S | Shuffled-label | 在 `train_S` 上训练;沿用 F 最终选中的配置 | 否 |
| Y | Style-only | 在 `train_Y` 上训练;沿用 F 最终选中的配置 | 否 |

- A 的损失:`CE(train_F batch) + λ · mean_t KL(p_base(·|x_<t) ‖ p_θ(·|x_<t))`,x 为该步的 4 篇锚文档,p_base 由 arm N 的权重当场计算且不回传梯度。锚项不在事实陈述句上计算。
- S、Y 不单独调参;它们使用 F 选中配置的全部数值与第 7 节的训练契约。
- 不得新增 arm、机制或阶段。

## 5. Metrics

**记号**:f 为 fact,a_f 为真实答案,C_f 为它的 4 个候选,Q_split(f) 为该 split 里它的问句集合,θ 为被评模型。

**闭卷候选打分(主指标)**
```
s_QA(f, q, c) = Σ_{t=1..K} log p_θ(c_t | chat(q), c_<t)          K = 答案在问答语境下的 token 数(cell 内相同)
correct(f, q) = 1[ s_QA(f, q, a_f) > max_{c ∈ C_f, c ≠ a_f} s_QA(f, q, c) ]      并列判为错
Score_split(f) = (1 / |Q_split(f)|) · Σ_{q ∈ Q_split(f)} correct(f, q)             聚合函数 = mean(已固定)
Acc(arm, split, G) = (1 / |G|) · Σ_{f ∈ G} Score_split(f)                          G = learned 或 unread 或其中一个 stratum
```
4 选 1 的随机水平是 0.25。选 mean 的理由:保留多个问法之间的部分一致程度;统计单位仍是 fact。

**TRAIN 闭卷检查**
```
s_ST(f, c) = Σ_{t=1..K'} log p_θ(c'_t | prefix(f), c'_<t)      prefix(f) = TRAIN 陈述句中答案之前的文本;c' = " " + c
CB(f) = 1[ s_ST(f, a_f) > max_{c ≠ a_f} s_ST(f, c) ]
Acc_CB(arm) = (1/120) · Σ_{f ∈ learned} CB(f)
```

**Free-generation exact match(次指标)**:对同一 `chat(q)` 做贪心解码,最多 16 个新 token,遇 im_end 特殊 token(id 151645)停。归一化:取第一行,去首尾空白,去开头的 “the ”(不分大小写),去结尾的 `. , ; : ! ?`,casefold。`EM(f, q) = 1[norm(output) == norm(a_f)]`,聚合方式同上。

**全对率(次指标,只报告)**:`AllCorrect(f) = Π_{q} correct(f, q)`。

**General damage**
```
NLL_arm(w) = −(1/(n_w − 1)) · Σ_{t=2..n_w} log p_θ(x_t | x_<t)             w 为一个通用文本窗口
dNLL(arm) = mean_{domain} mean_{w ∈ domain} [ NLL_arm(w) − NLL_N(w) ]         主
PPL_degradation%(arm) = 100 · (exp(dNLL(arm)) − 1)                           展示
```

**Unread controls**(问的是真实答案;不使用 NONE 选项)
```
Prior(split) = Acc(N, split, unread)
Spill(arm, split) = Acc(arm, split, unread) − Prior(split)                    知识外溢
FPR(arm, split) = (1/40) · Σ_{f ∈ unread} AllCorrect(f)                        与 FPR(N, split) 并排报告
```
E1-PILOT 不定义 NONE / 拒答任务。

**ImmediateGain 与 Retention**
```
ImmediateGain(arm, split) = Acc(arm, split, learned) − Acc(N, split, learned)
Retention(arm) = [Acc_after_phase2(arm, learned_1) − Acc(N, learned_1)] / [Acc_after_phase1(arm, learned_1) − Acc(N, learned_1)]
                 仅当分母 ≥ 0.10 时有定义;learned_1 = 第一阶段学的 fact,phase2 = 之后在其它内容上的训练
```
E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛。

## 6. Statistical Plan

- **Bootstrap 单位是 fact_id,不是问句。** 同一 fact 的多个问句高度相关,把问句当作独立观测会虚增样本量、使 CI 过窄(伪重复);因此先按第 5 节聚合成 Score(f),再对 fact 重抽样。
- 配对:比较 X 与 Y 时,`d_f = Score_X(f) − Score_Y(f)`,两个 arm 使用同一批重抽到的 fact_id。
- 次数 **10,000**;在 natural、random 两个 stratum 内分别有放回重抽(保持各自的 fact 数),合并后取 `Δ* = mean(d_f)`;95% CI = 第 2.5 与第 97.5 百分位。随机数:`rng_rule(BOOTSTRAP_SEED, "<比较>:<split>:<seed 或 avg>")`。
- **比较项**:Δ(F−N)、Δ(L−F)、Δ(A−F),在 learned fact 上;另报 Δ(S−N)、Δ(Y−N) 与各 arm 的 Spill。
- **报告**:每个训练种子单独报告;再报告 seed-average(先对每条 fact 把 3 个种子的 Score 取平均,再 bootstrap)。
- 3 个种子只作为方向一致性的证据,不作强推断。
- CI 是主要的不确定性描述;不报告 p 值作为判据。
- 精度说明:120 条 fact 时,正确率在 0.5 附近的标准误不超过 0.046。

## 7. Hyperparameter Budget 与 Training Budget & Optimization Contract

**搜索预算**:F、L、A 各 **6** 个配置,共 **18** 次搜索训练,全部使用训练种子 101。
- F:learning rate × weight decay。
- L:learning rate × rank。
- A:learning rate × anchor λ。
- **选择只用 DEV**:每个 arm 取 `Acc(arm, DEV-QA, learned)` 最高的配置;并列时依次取 general DEV 的 dNLL 较低者、learning rate 较低者、编号较小者;出现非有限损失或分数的配置剔除。TEST 在最终冻结前不可读取、不可生成。
- S、Y 沿用 F 选中的配置。
- 选定后,F、L、A 用种子 202、303 各再训练一次(种子 101 沿用搜索时的那次);S、Y 各训练 3 个种子。**训练总次数 30。**

**训练契约(冻结后不得改;F、L、A、S 的事实 token 数相同)**

| 项 | 值(PROPOSED) |
|---|---|
| 优化器 | AdamW,betas (0.9, 0.999),eps 1e-8 |
| 训练量 | 对 120 条 TRAIN 陈述句读 20 遍 |
| batch | 8 条陈述句;每遍 15 步;共 300 步 |
| 顺序 | 每遍一次全排列,`rng_rule(TRAIN_SEED, "order:<epoch>")` |
| 序列 | 一条陈述句一个序列;右侧补齐到批内最长;补齐位不计损失 |
| 梯度累积 | 1 |
| warmup | 前 15 步从 0 线性上升 |
| scheduler | 余弦,从峰值降到第 300 步时峰值的 10% |
| weight decay | F 按搜索空间;L、A 为 0;只作用于二维权重矩阵 |
| 梯度裁剪 | 全局范数 1.0 |
| 训练种子 | 101、202、303 |
| 评测种子 | 无(打分是确定性的;生成用贪心) |
| 精度 | bf16 autocast,主权重 FP32 |
| checkpoint | 每次训练只保留并评测最终 checkpoint;中间 checkpoint 不用于任何判断 |
| early stopping | 不允许 |
| Y 的训练量 | 对它的 240 句读 20 遍,batch 16,同为 300 步;token 数比见 2.6 |
| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测;同一次 Pilot 内每次运行记录的 `torch.cuda.get_device_name(0)` 必须相同 |
| GPU wall-clock 上限(已决定) | 4 小时:从第一次加载模型到 TEST 评测结束的累计 GPU 时间;超过即 ST7 |

锚文本的前向计算是 A 的额外算力,单独记入 compute accounting,不算事实 token。

**算力决定与显存估计**(决定来源:Metrix 指令 Round 1 第 8 项,2026-11-12;参数量由 `config.json` 与 safetensors 头信息核实,见 `reports/ROUND1_REPORT.md` 任务 3):
- 唯一参数 1,720,574,976(词嵌入与输出层共享;文件里另存的 `lm_head.weight` 在加载时与词嵌入绑定)。FP32 一份 = 6.88 GB。
- F、S、Y:权重 + 梯度 + AdamW 两个动量 = 4 份 = 27.5 GB。A:再加冻结的 base 副本 = 5 份 = 34.4 GB。L:冻结权重 6.88 GB + 适配器(秩 32 时 3,486 万参数 × 4 份)0.56 GB。N:6.88 GB。
- 另加 bf16 autocast 的权重副本 ≤ 3.4 GB,A 的锚文本 logits(4 × 128 token、两个模型)约 1.2 GB;批次 8 × ≤ 32 token 的激活 < 1 GB。最大的 arm A 合计约 39 GB,在 80 GB 上余量约 41 GB。

**搜索空间(与 `SEARCH_SPACE.json` 逐字一致;校验只比较两个标记之间的那一个 json 块)**

<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->
```json
{
  "protocol": "METRIX-E1-PILOT",
  "version": "v1",
  "status": "PROPOSED",
  "search_seed": 101,
  "selection": {
    "split": "DEV only",
    "metric": "Acc(arm, DEV-QA, learned), fact-level mean aggregation",
    "tie_break": [
      "lower general DEV dNLL",
      "lower learning rate",
      "lower config index"
    ],
    "excluded": "any configuration with a non-finite loss or score"
  },
  "training_contract": {
    "optimizer": "AdamW, betas (0.9, 0.999), eps 1e-8",
    "epochs": 20,
    "batch_size_statements": 8,
    "steps_per_epoch": 15,
    "total_steps": 300,
    "example_order": "one permutation of the corpus per epoch from Random(rng_rule(TRAIN_SEED, 'order:<epoch>'))",
    "sequence": "one statement per sequence; pad on the right to the longest sequence in the batch; padding excluded from the loss",
    "gradient_accumulation": 1,
    "warmup": "linear from 0 over the first 15 steps",
    "scheduler": "cosine from the peak to 10% of the peak at step 300",
    "weight_decay": "per SEARCH_SPACE for F; 0.0 for L and A; applied to 2-D weight matrices only",
    "gradient_clipping": "global norm 1.0",
    "training_seeds": [
      101,
      202,
      303
    ],
    "evaluation_seeds": "none (deterministic scoring; greedy generation)",
    "precision": "bfloat16 autocast with float32 master weights",
    "checkpoint_policy": "only the final checkpoint of a run is kept and evaluated; no intermediate checkpoint is used for anything",
    "early_stopping": "not allowed",
    "primary_training_token_budget": "20 passes over the 120 TRAIN statements for F, L, A and S (identical statements up to the S permutation); Y: 20 passes over its 240 sentences with batch 16 (300 steps); Y tokens / F tokens must lie in [0.80, 1.25]",
    "hardware": {
      "gpu": "NVIDIA A100 80GB",
      "count": 1,
      "decided": "Metrix instruction, round 1 item 8, 2026-11-12",
      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
      "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
      "cpu_use": "data generation, leakage checks and tokenizer checks only"
    },
    "wall_clock_limit_gpu_hours": 4,
    "wall_clock_scope": "cumulative GPU wall-clock from the first model load to the end of the TEST evaluation; above the limit: ST7"
  },
  "arms": {
    "N": {
      "name": "No-learning",
      "tuned": false,
      "definition": "the pinned base model, no parameter update",
      "configs": []
    },
    "F": {
      "name": "Full FT",
      "tuned": true,
      "definition": "all parameters trainable",
      "grid": [
        "learning_rate",
        "weight_decay"
      ],
      "configs": [
        {
          "id": "F1",
          "learning_rate": 1e-05,
          "weight_decay": 0.0
        },
        {
          "id": "F2",
          "learning_rate": 1e-05,
          "weight_decay": 0.1
        },
        {
          "id": "F3",
          "learning_rate": 3e-05,
          "weight_decay": 0.0
        },
        {
          "id": "F4",
          "learning_rate": 3e-05,
          "weight_decay": 0.1
        },
        {
          "id": "F5",
          "learning_rate": 0.0001,
          "weight_decay": 0.0
        },
        {
          "id": "F6",
          "learning_rate": 0.0001,
          "weight_decay": 0.1
        }
      ]
    },
    "L": {
      "name": "LoRA",
      "tuned": true,
      "definition": "base frozen; LoRA on q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj of all 28 layers; alpha = 2 * rank; dropout 0; B initialised to 0",
      "grid": [
        "learning_rate",
        "rank"
      ],
      "configs": [
        {
          "id": "L1",
          "learning_rate": 0.0001,
          "rank": 8,
          "weight_decay": 0.0
        },
        {
          "id": "L2",
          "learning_rate": 0.0001,
          "rank": 32,
          "weight_decay": 0.0
        },
        {
          "id": "L3",
          "learning_rate": 0.0003,
          "rank": 8,
          "weight_decay": 0.0
        },
        {
          "id": "L4",
          "learning_rate": 0.0003,
          "rank": 32,
          "weight_decay": 0.0
        },
        {
          "id": "L5",
          "learning_rate": 0.001,
          "rank": 8,
          "weight_decay": 0.0
        },
        {
          "id": "L6",
          "learning_rate": 0.001,
          "rank": 32,
          "weight_decay": 0.0
        }
      ]
    },
    "A": {
      "name": "Full FT + anchor",
      "tuned": true,
      "definition": "F plus lambda * KL(p_base || p_theta) on general anchor text, 4 anchor documents per step",
      "grid": [
        "learning_rate",
        "anchor_lambda"
      ],
      "configs": [
        {
          "id": "A1",
          "learning_rate": 3e-05,
          "anchor_lambda": 0.3,
          "weight_decay": 0.0
        },
        {
          "id": "A2",
          "learning_rate": 3e-05,
          "anchor_lambda": 1.0,
          "weight_decay": 0.0
        },
        {
          "id": "A3",
          "learning_rate": 3e-05,
          "anchor_lambda": 3.0,
          "weight_decay": 0.0
        },
        {
          "id": "A4",
          "learning_rate": 0.0001,
          "anchor_lambda": 0.3,
          "weight_decay": 0.0
        },
        {
          "id": "A5",
          "learning_rate": 0.0001,
          "anchor_lambda": 1.0,
          "weight_decay": 0.0
        },
        {
          "id": "A6",
          "learning_rate": 0.0001,
          "anchor_lambda": 3.0,
          "weight_decay": 0.0
        }
      ]
    },
    "S": {
      "name": "Shuffled-label",
      "tuned": false,
      "definition": "TRAIN statements with the answers permuted among learned facts of the same relation and stratum (derangement)",
      "inherits": "the configuration selected for F",
      "configs": []
    },
    "Y": {
      "name": "Style-only",
      "tuned": false,
      "definition": "per learned fact one entity-only and one answer-only sentence (templates Y_ENTITY, Y_ANSWER), never in the same sequence",
      "inherits": "the configuration selected for F",
      "configs": []
    }
  },
  "counts": {
    "search_runs": 18,
    "extra_seed_runs_F_L_A": 6,
    "S_runs": 3,
    "Y_runs": 3,
    "total_training_runs": 30
  }
}
```
<!-- END INLINE COPY: SEARCH_SPACE.json -->

## 8. Gate 0 — Pipeline Qualification(只用 TRAIN 与 DEV)

**执行顺序**(每一步的停止规则见第 11 节):
1. 记录环境与出处;在 CPU 上生成除 TEST 以外的数据,把哈希写入两个 manifest 并提交。
   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8);从此刻第一次加载模型起累计 GPU wall-clock。
2. 运行泄漏检查。
3. 评测 N:TRAIN 闭卷、DEV-QA、general DEV。
4. F 的 6 个配置(种子 101)→ 选定 → 用选定配置检查阳性对照。
5. L、A 的搜索 → 选定。
6. F、L、A 的另外两个种子;S、Y 各三个种子。
7. 按下表判定 Gate 0。
8. Gate 0 通过后:提交冻结记录(选定配置、数据哈希、checkpoint 哈希)→ 生成 `test_qa.jsonl` 与 `general_test.jsonl` → 对 TEST 运行 L3–L5 → **TEST 只评一次**。

**算力边界**:第 3–8 步全部在同一型号的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。

**Gate 0 门槛(全部为数值;“seed-average” 见第 6 节)**

| 编号 | 条件 |
|---|---|
| G0.1 | 泄漏检查 L1–L6 全部在上限内 |
| G0.2 | 所有用到的损失、分数、NLL 都是有限值 |
| G0.3 | N 的下限检查:`Acc(N, DEV-QA, learned)` ∈ [0.15, 0.35],每个 stratum ∈ [0.10, 0.40];`Acc(N, DEV-QA, unread)` ∈ [0.10, 0.40];`Acc_CB(N)` ∈ [0.15, 0.35] |
| G0.4 | `Acc_CB(F)` ≥ 0.90,3 个种子都满足 |
| G0.5 | seed-average `Acc(F, DEV-QA, learned)` ≥ 0.70;seed-average Δ(F−N) 的 95% CI 下界 > 0;每个种子的 Δ(F−N) > 0 |
| G0.6 | seed-average Δ(S−N)(真实映射,DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.7 | seed-average Δ(Y−N)(DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.8 | 复现:对 F 选定配置的 3 个 checkpoint 各评测两次,所有 (fact, 问句) 的预测完全相同,候选分数差 ≤ 1e-4,每个通用窗口的 NLL 差 ≤ 1e-5 |
| G0.9 | 上限检查:seed-average `Acc(F, DEV-QA, learned)` ≤ 0.95 |
| G0.10 | 能估计 E1-V1 的规模:对 Δ(L−F)、Δ(A−F) 的 seed-average 配对差 d_f 算出标准差 σ_d(有限),并给出 δ ∈ {0.05, 0.10, 0.15} 下的所需 fact 数 `n = ((1.96 + 0.84) · σ_d / δ)²`(双侧 0.05、功效 0.80),再用 Pilot 的 fact 按 n 重抽样验证 CI 半宽 |

- 任一不满足 → **PIPELINE_NOT_QUALIFIED**,禁止进入 E1-V1,TEST 不生成、不评测。
- 越过 G0.3 或 G0.9 的界限不代表机制失败:它触发 benchmark 重新校准(新协议版本)。
- seed-average `Acc(F, DEV-QA, learned)` < 0.40 记为“对该模型与该训练量过难”;在 [0.40, 0.70) 记为 OPTIMIZATION_OR_CAPACITY_UNRESOLVED。两者都属于 PIPELINE_NOT_QUALIFIED。
- 只报告、不进门槛:`Spill(arm, DEV)` 与 `FPR`、EM、AllCorrect、各 arm 的 dNLL、S 在它自己的置换映射上的正确率(用来确认 S 确实学到了置换后的映射)。

**TEST 确认(Gate 0 通过并冻结之后,只评一次)**

| 编号 | 条件 |
|---|---|
| T1 | seed-average `Acc(F, TEST-QA, learned)` ≥ 0.70,且 seed-average Δ(F−N) 的 95% CI 下界 > 0 |
| T2 | S、Y 在 TEST-QA 上满足 G0.6、G0.7 的同样数值 |
| T3 | N 在 TEST-QA 上满足 G0.3 的同样范围 |

**E1-PILOT 的最终状态**:Gate 0 全部满足且 T1–T3 全部满足 → **PASS**(系统合格,可以撰写 E1-V1 协议);否则按第 9 节标注。Δ(L−F)、Δ(A−F) 在 TEST 上只报告。

## 9. Failure Taxonomy(固定集合)

`PASS` / `HYPOTHESIS_FAIL` / `IMPLEMENTATION_FAIL` / `OPTIMIZATION_FAIL` / `CAPACITY_LIMIT` / `OPTIMIZATION_OR_CAPACITY_UNRESOLVED` / `BLOCKED` / `NOT_TESTED` / `PIPELINE_NOT_QUALIFIED`

| 状态 | 何时使用 |
|---|---|
| PASS | 第 8 节:Gate 0 与 T1–T3 全部满足 |
| PIPELINE_NOT_QUALIFIED | Gate 0 或 T1–T3 任一不满足;同时给出下面的一个原因 |
| IMPLEMENTATION_FAIL | G0.1、G0.2、G0.6、G0.7、G0.8 不满足,或 Y 的 token 数比越界,或实现与本协议不一致 |
| OPTIMIZATION_FAIL | G0.4 不满足(在给定训练量内连 TRAIN 陈述句都没有记住) |
| OPTIMIZATION_OR_CAPACITY_UNRESOLVED | G0.4 满足但 G0.5 或 T1 的正确率不满足 |
| CAPACITY_LIMIT | 仅当更强的模型在同一协议下 PASS 之后才可使用;在此之前必须保留 OPTIMIZATION_OR_CAPACITY_UNRESOLVED |
| HYPOTHESIS_FAIL | 保留给 E1-V1 的机制比较;E1-PILOT 没有机制假设,不使用 |
| BLOCKED | 环境、资源、数据来源或库版本不满足第 0 节,无法按协议执行 |
| NOT_TESTED | 未运行,或在没有违反任何条件的情况下提前停止 |

看到结果之后不得修改任何门槛;协议本身有缺陷时,开新版本(PROTOCOL_REVISION_V2)。

## 10. Experiment Record Template

每次运行(含被停止的)提交一份,字段不可减:

```
Experiment ID:
Hypothesis:
Purpose:
Independent Variable:
Controls:
Environment (CPU/GPU, commit, seed):
Input (data SHA, split SHA):
Hyperparameter budget:
Compute accounting (tokens / steps / FLOPs / wall-clock):
Expected (pre-registered):
Acceptance (quantified):
Stop Conditions:
Positive control result:
Negative control result:
Statistical plan:
Actual:
Status:
Interpretation:
Non-claims:
Next (single):
```

Compute accounting 的算法:训练 FLOPs ≈ 6 · P · T,前向 FLOPs ≈ 2 · P · T(P = 参与计算的参数量,T = token 数);token、步数、wall-clock 取实测值;A 的锚文本算力单列。

## 11. Stop Conditions

| 编号 | 事件(可立即判断) | 动作 |
|---|---|---|
| ST1 | 第 2 步任一泄漏检查超限 | 停;不训练;IMPLEMENTATION_FAIL |
| ST2 | 第 3 步 N 不满足 G0.3 | 停;不训练;PIPELINE_NOT_QUALIFIED(重新校准) |
| ST3 | 第 4 步 F 选定配置(种子 101)的 `Acc_CB` < 0.90,或 `Acc(F, DEV-QA, learned)` < 0.70 | 阳性对照未过:停;不跑 L、A、S、Y |
| ST4 | Y 不满足 G0.7 | Style-only 泄漏:停;不生成 TEST |
| ST5 | S 不满足 G0.6 | Shuffled control 出现真实映射提升:停;不生成 TEST |
| ST6 | 任一次训练或评测出现非有限值 | 停该次;若发生在选定配置或对照上,IMPLEMENTATION_FAIL |
| ST7 | 累计 GPU wall-clock 超过 4 小时(第 7 节) | 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续 |
| ST8 | 环境不满足第 0 节 | BLOCKED |

## 12. Out of Scope

- E1-V1 之后的任何实验。
- Growth、Consolidation、RAG、多跳。
- 模型选择与最终部署。
- Learned controller。
- NONE / 拒答校准。
- 探索沙盒(SANDBOX)。

## 13. Open Questions for Review Gate(PENDING_REVIEW_GATE 仅此 2 项)

| # | 字段 | PROPOSED | 理由 |
|---|---|---|---|
| 1 | E1-V1 目标 fact 数 | 320(240 learned + 80 unread),并在 Pilot 后按 G0.10 的公式重算 | 若配对差的标准差为 0.5,检出 0.10 的差需要约 196 条 learned fact;取 240 留余量 |
| 2 | general-damage non-inferiority margin | dNLL ≤ +0.03(约 +3% PPL) | 与本仓库此前实验使用的容忍幅度一致;Pilot 里 general damage 只报告,不进门槛 |

**已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。

其余可执行参数都已写死或标为 PROPOSED;Review Gate 可以改动一次,PROTOCOL_FROZEN 之后任何门槛、split 规则、指标、搜索预算或 Gate 定义的改动都必须开新协议版本。
