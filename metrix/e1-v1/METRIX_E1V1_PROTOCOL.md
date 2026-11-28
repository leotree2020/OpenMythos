# METRIX · E1-V1 · PROTOCOL v1(草案)

| 字段 | 值 |
|---|---|
| Task ID | METRIX-E1-V1-PROTOCOL-AUTHORING-V1.0(`tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md`) |
| 状态 | **AWAITING_REVIEW_GATE**(未冻结;Owner 批准后改为 PROTOCOL_FROZEN,冻结提交与本文件、四个 JSON 的 sha256 写入同目录的 `PROTOCOL_FROZEN` 文件) |
| 本文件的作用 | 执行 E1-V1 只需要本文件、同目录四个 JSON(`DATA_MANIFEST.json`、`SPLIT_MANIFEST.json`、`DOSE_SPACE.json`、`DAMAGE_MANIFEST.json`),以及第 0 节固定的外部来源 |
| 本文件不包含 | 任何训练、评测结果或结论;任何 TEST 数据 |
| 记号 | “沿用 Pilot 第 x 节” = 冻结协议 `metrix/e1-pilot/METRIX_E1_PROTOCOL.md` v1.1(冻结提交 `87a244db28a901f9e89282b50df76778ab5c2887`)第 x 节的规则原样适用,本文件只列出改动;“解释 Bn” = Pilot 实现阶段经 Review Gate 接受的解释(原文在 `metrix/e1-pilot/results/experiment_record_formal_20261128T045921Z.json` 的 `environment.interpretations`);哪些在 E1-V1 中作为协议条文适用,见第 0 节“Pilot 解释的适用” |
| 待决字段 | 只有第 15 节三项(GPU 累计时间上限、D2 数据集、剂量点与配置的数量);其余可执行参数均为 PROPOSED 值,附理由 |

路径约定:本文件中的 `results/…`、`approvals/…`、`audit/…`、`reviews/…` 均相对于 `metrix/e1-v1/`。

## 0. 标识、出处与环境

**Git 出处**

| 项 | 值 |
|---|---|
| 起点 | `leotree2020/OpenMythos` 分支 `metrix-e1-pilot-protocol-v1` 的提交 `6e03468956208c422d0d41c08edaaf116166338c`(E1-PILOT 报告勘误提交) |
| 撰写分支 | `metrix-e1-v1-protocol-v1` |
| 改动范围 | 只在 `metrix/e1-v1/` 下新建文件;`metrix/e1-pilot/` 与 `metrix/` 以外不改动。检查:`git diff --name-only 6e03468956208c422d0d41c08edaaf116166338c HEAD -- . ':(exclude)metrix/e1-v1'` 的输出为空 |

**模型与输入约定**:沿用 Pilot 第 0 节“模型”表与输入约定的全部各行(模型 `Qwen/Qwen3-1.7B` @ `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`,Apache-2.0;分词器同 revision,4 个文件的 sha256 见 `DATA_MANIFEST.json: model.tokenizer.files_sha256`;权重 FP32,训练 bf16 autocast,评测 FP32 不用 autocast;训练输入、问答输入、候选打分输入、EM 生成输入、通用文本与锚文本输入各行不变)。另加一行:

| 项 | 值 |
|---|---|
| D2 打分输入(新) | `chat(p) + "The answer is" + " " + ℓ`,`p` 为第 7.1 节的 D2 题面,`chat` 与问答输入相同(单个 user 回合,`add_generation_prompt=true`,`enable_thinking=false`,不加 system prompt);`ℓ ∈ {A, B, C, D}`,`" A"`、`" B"`、`" C"`、`" D"` 各是一个 token(id 362、425、356、422,`reports/authoring/v1_data_check.txt`);只对这一个 token 打分 |
| 库版本 | torch 2.11.0,transformers 5.22.2(沿用 Pilot 第 0 节;依赖锁定沿用 `metrix/e1-pilot/requirements.lock` 的版本);实际版本写入实验记录,不一致即 BLOCKED(ST8) |

**种子(PROPOSED)**:`DATA_SEED = 20261128`,`CANDIDATE_SEED = 20261129`,`BOOTSTRAP_SEED = 20261130`,`TRAIN_SEEDS = [101, 202, 303]`。理由:前三个为新值(Task Order 5.2 要求新的 DATA_SEED;三个都与 Pilot 的 20261110–20261112 不同);训练种子只决定样本顺序与 LoRA A 的初始化,不决定数据,沿用 Pilot 的三个值。所有随机数都来自 `rng_rule(SEED, purpose) = random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))`(沿用 Pilot 第 0 节);全部 purpose 列在 `DATA_MANIFEST.json: seeds.purposes`。结果不好不得换种子。

**环境**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行;设备全名规则、GPU 检查、确定性设置(`torch.use_deterministic_algorithms(True)`、关闭 TF32、`CUBLAS_WORKSPACE_CONFIG=:4096:8`)沿用 Pilot 第 0、7 节(ST8、ST9)。CPU 只做数据生成、泄漏检查与分词器检查,不加载模型权重。

**哈希**:沿用 Pilot 第 0 节(规范化 JSON、JSONL、`byte_sha256` 与 `canonical_sha256`)。checkpoint 的哈希为解释 B25 的 `state_sha256`(按 `state_dict()` 键排序,逐键写入键名、dtype、shape 与张量原始字节的 SHA-256;不是文件字节哈希)。

**“读取 TEST 数据”的定义**:沿用 Pilot 第 3 节(解码 test 行的内容,或用其内容做任何计算;解析 split 字段、计数、对整个文件求哈希不算),适用于本协议的全部 TEST 来源。第 10 节第 10 步之前,对 TEST 来源允许且只允许:对整个文件求 sha256(第 1 步核对来源文件哈希需要);`eval_sets.jsonl` 按行首字节匹配 domain 与 split 字段后计数(行首必须匹配字节正则 `^\{"domain": "([^"\\]*)", "split": "([^"\\]*)", `,与 Pilot 实现阶段 B 的做法相同),test 行不解码、不做 JSON 解析;D2 的 TEST 来源 parquet 只读文件尾的行数。不得解码或读取任何 test 行或 TEST 题目的内容。

**Pilot 解释的适用**(冻结):照原文适用 B4、B5、B6、B7、B8、B9、B10(每个 stratum 120 条 learned、40 条 unread)、B11、B12(purpose 另按第 8 节扩充)、B14、B15(“候选分数”另包括 D1 窗口 NLL 与 D2 字母分数,见 G0.8、G-D1)、B16(ST3–ST7、ST11 的状态;ST3 的对象见第 13 节)、B18、B19、B20、B21(以 `attn_implementation='eager'` 加载模型)、B22、B23、B24、B25。按 E1-V1 的数值改写后适用:B1(优化器步 s = 1..960,第 2.6 节)、B3(遍号 k = 1..32,第 11 节)。被替换、不适用:B2(余弦调度,由第 11 节的 warmup 加常数学习率替换:`lr(s) = peak · s / 30`(s ≤ 30),`lr(s) = peak`(s > 30))、B13(G0.10,E1-V1 不使用)、B17(Pilot 的预检公式,由第 12 节的 ST11 公式替换)。

## 1. 科学问题、Scope 与 Non-claims

**问题**(Task Order 第 2 节):在相同的事实学习水平上,全参数微调(F)、LoRA(L)、带锚点约束的全参数微调(A)对模型通用能力的损伤各有多大。

**规划依据**(E1-PILOT 的事实,只用于提出问题与规划,不构成结论;Task Order 红线 7):F 的 TEST 准确率 0.930(`metrix/e1-pilot/results/test_evaluation_result.json: values.T1.acc_avg`);DEV 通用文本 dNLL:F 1.089–1.466、L 3.382–3.954、A 0.201–0.226(`metrix/e1-pilot/results/training_runs/{F-F3,L-L6,A-A5}-seed{101,202,303}.json: dnll`);seed-average Δ(A−F) 在 TEST 上为 −0.061(`test_evaluation_result.json: comparisons["A-F:TEST:avg"]`)。不同学习水平之间的损伤不可直接比较,所以本协议的全部方法间损伤比较只在第 6 节的 iso-acquisition 点上进行(红线 5)。

**两个 Gate**:Gate D(第 7.5 节)证明损伤的测量合格;Gate M(第 9.3–9.4 节)只在 Gate D 通过、margin 记录提交之后进行。事实测量另由 Gate 0 再确认(第 9.1 节)。

**Non-claims**(无论结果如何都不得推出;Task Order 第 12 节):持续学习是否有效;旧事实的保留(Retention,归 E2);长期记忆;成长与扩容的价值;巩固机制的价值;多跳推理;在其他模型或更大规模上的表现;Metrix 架构的优越性。另:结论只对第 4 节冻结的三个配置、第 6.3 节的剂量阶梯与本协议的事实类型成立,不推广到其它学习率、rank、λ 或训练长度。

**范围外**:E2 及之后的阶段;第二批事实;任何新机制(Growth、Consolidation、RAG、多跳推理、learned controller、agent 等);部署与推理服务;模型结构改动;题目加难;NONE / 拒答任务。本协议不定义、不报告 Retention 的任何数字(红线 6)。

## 2. 事实数据

### 2.1 规模与结构

- 总量 **320 facts = 240 learned + 80 unread**;8 个 cell(relation × stratum),每个 cell **30 learned + 10 unread**。relation(`capital`、`currency`、`founder`、`river`)、stratum(`natural`、`random`,各占 50%)、fact = (entity, relation, answer)、同一 fact 的 entity 与 answer 属于同一 stratum、答案平衡(同一答案值最多出现 1 次;640 个字符串两两不同):**沿用 Pilot 第 2.1 节**,只把数量由 15 + 5 改为 30 + 10。
- fact_id:`E1V1-<L|U>-<relation>-<nat|rnd>-<两位序号>`;cell 内先生成的 30 条为 learned(序号 01–30),后 10 条为 unread(序号 01–10);类别不得变更。前缀与 Pilot 的 `E1P` 不同,两套 fact_id 不相交(L7c)。

### 2.2 名字生成

**沿用 Pilot 第 2.2 节的全部规则**:抽一个字符串的方法(natural 的音节与 random 的字母段)、形式规则(长度 natural 4–10、random 6–8;natural 带前导空格多于 1 个 token)、冲突规则 reject_if(与已接受集合比较;natural:小写相同、前 4 字符相同、小写编辑距离 ≤ 1;random:相同、字母段相同、等长汉明距离 ≤ 1)、锚文本规则(在第 2.6 节锚文本中出现过的字符串一律拒绝,不分大小写的子串)、`K_st` 与 `K_qa`、随机流(细节 1)、生成顺序、entity 的抽取、答案等长规则的统计(细节 2,前 400 个满足形式规则的抽样)与接受(细节 3,从头重抽)、每个流最多 20,000 次(超过即 IMPLEMENTATION_FAIL)。改动只有三处:

1. 种子为 E1-V1 的 `DATA_SEED = 20261128`,purpose 字符串不变(`names:<relation>:<stratum>:entity` / `:answer`)。
2. 每种角色每个 cell 接受 40 个(先 30 个为 learned,后 10 个为 unread)。
3. **已接受集合在第一次抽取之前放入 Pilot 的 320 个字符串**:按 Pilot 第 2.2 节以 `DATA_SEED = 20261110` 重新生成 Pilot 的 160 条 fact(其规范化 SHA-256 必须等于 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97`,否则 ST12),取全部 entity 与 answer。这样 reject_if 同时排除与 Pilot 字符串相同或相近的名字(第 2.7 节)。

**复现**:按以上规则生成的 320 条 fact(字段与 Pilot 相同:`fact_id, exposure, relation, stratum, entity, answer`,按生成顺序)的规范化 SHA-256 必须等于 `0fc5ad819500e8a9f56771405af67d0fa71bafabba25bf8f4c3e5b6d684e01f4`;比对方法沿用 Pilot 第 2.2 节“fact 哈希的比对方法”(从 `facts.jsonl` 按行序读出 fact 列表,对该 JSON 列表的规范化序列求 SHA-256)。参考实现 `reports/authoring/v1_data_check.py`;两次独立运行逐字节一致(`reports/authoring/v1_data_check_repeat.txt`)。各 cell 的抽取次数(entity 40–83 次,answer 80–270 次,均远低于 20,000)与目标数对见 `reports/authoring/v1_data_check.txt`。

### 2.3 每条 fact 的文本

**沿用 Pilot 第 2.3 节**:learned fact 有 1 条 TRAIN 陈述句、2 条 DEV QA、3 条 TEST QA;unread fact 有 2 条 DEV QA、3 条 TEST QA、没有训练文本;unread fact 的 entity 与 answer 在任何 arm 的训练文本和锚文本里出现 0 次。

### 2.4 模板

**沿用 Pilot 第 2.4 节**:同样的 32 个模板(TRAIN / DEV / TEST / Y 四个集合两两不交),逐条的 `template_id`、文本与 `normalized_sha256` 原样复制在 `SPLIT_MANIFEST.json: templates`;`template_set_sha256 = 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f`(与 Pilot 相同,`reports/authoring/v1_data_check.txt` 重算);归一化方法沿用 Pilot 第 3 节“模板冻结”。

### 2.5 候选

**沿用 Pilot 第 2.5 节**(4 个候选 = 真实答案 + 3 个干扰项;池 = 同 relation、同 stratum、同暴露类别的其它 fact 的答案;池少于 4 即 IMPLEMENTATION_FAIL;调用方式细节 5;`candidates.json` 的格式;一条 fact 的候选表对它的全部模板、split、arm 相同;暴露匹配),种子改为 `CANDIDATE_SEED = 20261129`,purpose `cand:<fact_id>` 不变。E1-V1 的池为 learned 29 个、unread 9 个。**复现**:`candidates.json` 的规范化 SHA-256 必须等于 `79600769eef1876b54bc3d174874880e8e05bab11290f97360559f99324235c3`;暴露匹配的违规数为 0(`reports/authoring/v1_data_check.txt`)。

### 2.6 S、Y 与锚文本

- **S**:**沿用 Pilot 第 2.6 节**(每个 cell 内对 learned 答案做一次没有不动点的置换,调用方式细节 4,记录格式 `{"fact_id", "answer_fact_id", "text"}`),种子为 E1-V1 的 `DATA_SEED`,每个 cell 置换 30 个。**复现**:`train_S.jsonl` 的规范化 SHA-256 必须等于 `7ac254f6e87e017ecc6ce9945006cda1c5310c7358d69da88e5c81cfdc907bd6`。
- **Y**:**沿用 Pilot 第 2.6 节**(每条 learned fact 一个 `Y_ENTITY` 句与一个 `Y_ANSWER` 句,各自是独立的训练序列;共 480 句;Y 与 F 语料 token 数之比必须在 [0.80, 1.25],否则 IMPLEMENTATION_FAIL;算法为 Pilot 实现阶段 A 的 Review Gate 裁决第 3 项:每条序列计文本 id 数加 1 个 `<|endoftext|>`)。撰写时的比值:F 3,802 token,Y 4,541 token,比值 1.1944(`reports/authoring/v1_data_check.txt`)。`train_Y.jsonl` 的行序为 fact 顺序、每条 fact 先 `Y_ENTITY` 后 `Y_ANSWER`,记录 `{"fact_id", "template_id", "kind", "text"}`(Pilot 实现阶段的格式,解释 B3 的说明),规范化 SHA-256 `82314e6b4a5917d0d4e62e3f34f4ab80e330c8dc5b5c7395e1183809c4daf96b`。
- **锚文本(只用于 arm A)**:**沿用 Pilot 第 2.7 节锚文本**的来源、选取(前 512 篇不少于 600 字符的文档,每篇最多 128 token)与调度(第 s 步使用第 (4s + i) mod 512 篇,i = 0..3;优化器步从 1 编号,s = 1..960,文档按 `anchor_text.jsonl` 顺序编号 0..511,解释 B1),与 Pilot 是同一组 512 篇。解码文本的规范化 SHA-256 必须等于 `8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408`(Pilot 冻结值,撰写时重算一致)。理由:arm A 的定义不变,才能与 Pilot 的 A 的记录对照;锚文本不含任何 fact,不属于“复用 Pilot 的 fact、候选或 TEST 实例”。

### 2.7 与 Pilot 的 fact 不相交(Task Order 5.2)

可执行检查 **L7**(第 3 节表):(a)V1 的 640 个字符串中,与 Pilot 的 320 个字符串之一小写后相同的个数 = 0;(b)V1 的字符串中,与同 stratum 的某个 Pilot 字符串触发第 2.2 节 reject_if 的个数 = 0;(c)V1 与 Pilot 的 fact_id 交集 = 0。第 2.2 节第 3 处改动使 (a)(b) 在生成时就成立,检查仍然执行。撰写时三项均为 0(`reports/authoring/v1_data_check.txt`)。V1 的候选都是 V1 的答案,TEST 问句由 V1 的 fact 实例化,因此候选与 TEST 实例也不与 Pilot 重合。

### 2.8 生成的文件

非 TEST:`facts.jsonl`、`train_F.jsonl`、`train_S.jsonl`、`train_Y.jsonl`、`dev_qa.jsonl`、`candidates.json`、`anchor_text.jsonl`、`general_dev.jsonl`(D1 DEV)、`d2_dev.jsonl`(D2 DEV)。TEST(第 10 节第 10 步才允许生成):`test_qa.jsonl`、`general_test.jsonl`(D1 TEST)、`d2_test.jsonl`(D2 TEST)。字段、生成规则与撰写时的参考哈希见 `DATA_MANIFEST.json: files` 与 `DAMAGE_MANIFEST.json`;执行第 1 步生成的文件的规范化 SHA-256 必须等于参考哈希,否则 ST12。

## 3. Split 与泄漏契约

- `DATA_MANIFEST.json`:模型、种子、事实数量与生成规则、锚文本、每个数据文件的参考哈希与生成状态。`SPLIT_MANIFEST.json`:fact_id 规则、split 定义、32 个模板、候选规则、L1–L8。`DAMAGE_MANIFEST.json`:D1、D2 的来源、revision、哈希、划分、排除规则、Gate D 与 margin 的参数。
- 模板冻结、“读取 TEST 数据”的定义:沿用 Pilot 第 3 节(后者的适用范围见第 0 节)。

**泄漏检查(8 项,全部可执行)**:L1–L6 **沿用 Pilot 第 3 节**的定义与上限,L6 的范围扩大到全部损伤评测集;L7、L8 为本协议新增。

| 编号 | 规则 | 上限 | 撰写时(DEV 部分) |
|---|---|---|---|
| L1 | 沿用 Pilot L1(四个模板集合的 `normalized_sha256` 两两不交) | 0 | 0 |
| L2 | 沿用 Pilot L2(不同集合两模板的词 4-gram Jaccard) | ≤ 0.25 | 0.2 |
| L3a | 沿用 Pilot L3a(80 个 unread fact 的 160 个字符串在 `train_F`、`train_S`、`train_Y`、`anchor_text` 中的出现次数) | 0 | 0 |
| L3b | 沿用 Pilot L3b(240 个 learned answer 在 `anchor_text` 中的出现次数) | 0 | 0 |
| L4 | 沿用 Pilot L4(实例化的 DEV / TEST 问句在任何训练语料与 `anchor_text` 中逐字出现的次数) | 0 | 0(640 个 DEV 问句) |
| L5 | 沿用 Pilot L5(learned 与 unread 的 fact_id 交集;640 个字符串中的重复数) | 0 | 0 |
| L6 | 沿用 Pilot L6 的定义(词 = `str.split()`,区分大小写;13-gram 在每篇文档之内取;取 13-gram 的文本是送入模型的 id 解码所得;Qwen token 13-gram 只报告),比较对象为锚文本 512 篇对:D1 的 `general_dev.jsonl`、`general_test.jsonl`,D2 的 `d2_dev.jsonl`、`d2_test.jsonl`(题面文本 `p`) | 0 | D1 DEV 0,D2 DEV 0 |
| L7 | 第 2.7 节 (a)(b)(c) 三项之和 | 0 | 0 |
| L8 | 损伤评测集中含 V1 字符串的单位数:一个 D1 窗口或一道 D2 题,只要其文本中出现 640 个 V1 字符串之一(不分大小写,且紧前、紧后的字符都不是 ASCII 字母或数字,或为文本边界)即计 1。“文本”:D1 窗口为送入模型的 id(最多 256 个)用本协议分词器解码所得的 `text` 字段(与 L6 相同,不是整篇源文档);D2 为题面 `p` | 0 | D1 DEV 0,D2 DEV 0 |

learned fact 的 entity 与 answer 同时出现在 TRAIN 陈述句和 QA 中是被测对象,不算泄漏。

**损伤评测集的排除规则(生成规则)**:D1 窗口与 D2 题目在生成时按第 7.2 节依次排除触发 L8、触发 L6(与锚文本共享任一词 13-gram)、以及(TEST)与 DEV 某单位相同的单位,因此 L6、L8 在构造上为 0,检查仍然执行。撰写时 D1 DEV 与 D2 DEV 都没有单位被排除(`reports/authoring/v1_data_check.txt`)。

**时机**:L1、L2 只用模板;L3a–L8 的 DEV 部分在第 10 节第 1 步运行(G0.1);L3a–L5 涉及 TEST 的部分在 `test_qa.jsonl` 生成之后运行;L6、L8 的 TEST 部分在 `general_test.jsonl`、`d2_test.jsonl` 生成之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算,只输出计数,两者结果须一致(L6 的计数口径沿用 Pilot L6 的 TEST 部分,对 D1 TEST 与 D2 TEST 各自单独计数:锚文本的词 13-gram 集合分别与 `general_test.jsonl` 全部窗口、`d2_test.jsonl` 全部题面的词 13-gram 集合求交,各计交集的种类数;L8 对两个文件各计单位数);任一 TEST 部分超限或两者不一致 → ST10。

## 4. Arms 与对照

| Arm | 定义 | 配置(PROPOSED,`DOSE_SPACE.json`) | 用途 |
|---|---|---|---|
| N | 固定的 base 模型,不更新参数 | — | 学习量与损伤的基线 |
| F | 全部参数可训练,在 `train_F` 上训练 | learning rate 3e-5,weight decay 0.0 | 剂量曲线 |
| L | LoRA:base 冻结;适配器加在全部 28 层的 q_proj、k_proj、v_proj、o_proj、gate_proj、up_proj、down_proj;alpha = 2 × rank;dropout 0;B 初始为 0;A 的初始化为解释 B5(每个值 `r.uniform(-b, b)`,`b = 1/sqrt(in_features)`,`r = rng_rule(TRAIN_SEED, "lora_A:<module path>")`,逐行,float32) | learning rate 1e-3,rank 32 | 剂量曲线 |
| A | F 的损失加 λ · KL(p_base ‖ p_θ),公式、KL 的 token 加权平均、锚文档前不加特殊 token、t 从 2 起:**沿用 Pilot 第 4 节**;base 副本与训练模型在锚文本上的前向都在同一 bf16 autocast 下运行,logits 转为 float32 后做 log_softmax 与 KL(解释 B6) | learning rate 1e-4,λ = 1.0 | 剂量曲线 |
| S | 在 `train_S` 上训练,使用 F 的配置与训练契约 | 同 F | Gate 0(G0.6、T2),只用剂量点 d0 |
| Y | 在 `train_Y` 上训练,batch 16,使用 F 的配置与训练契约 | 同 F | Gate 0(G0.7、T2),只用剂量点 d0 |
| Z0 | 阴性对照:F 的完整训练流程(数据、优化器步、梯度裁剪、checkpoint 保存与重载、哈希),learning rate 0 | learning rate 0,weight decay 0,2 遍 | Gate D(G-D1) |
| P+ | 阳性对照:F 的训练流程,Pilot F6 的数值 | learning rate 1e-4,weight decay 0.1,11 遍 | Gate D(G-D3、G-D4) |

**配置的理由**:每种方法只用一个配置,即 Pilot 在同一搜索预算(每种方法 6 个配置、同一 DEV 选择规则)下选出的配置(`metrix/e1-pilot/results/selection_freeze_record.json: selected` = F3、L6、A5;数值见 `metrix/e1-pilot/SEARCH_SPACE.json`)。三种方法的调参预算相同(都是 Pilot 的 6 个配置),选择规则相同且只看学习量(DEV 准确率),不看损伤;E1-V1 不再调参。因此 Gate M 中没有按损伤挑选配置的步骤(第 6.6 节)。P+ 的数值与 Pilot F6 相同(`metrix/e1-pilot/results/training_runs/F-F6-seed101.json: config`,DEV dNLL 5.55021);训练长度见第 6.3 节。Z0 的 learning rate 为 0:AdamW 的更新量与 weight decay 项都乘以 learning rate,参数逐位不变,因此 Z0 的 `state_sha256` 必须与 N 相同(G-D1)。Z0 跑 2 遍(60 步)的理由:2 遍已经走过训练流程的每一段代码(warmup 结束、进入常数学习率、跨越遍的边界与样本重排、优化器状态的建立),再长的训练不经过新的代码路径,参数在 learning rate 为 0 时也不会改变。

S、Y 不单独调参(沿用 Pilot 第 4 节)。不得新增 arm、机制或阶段。

## 5. 事实指标

**沿用 Pilot 第 5 节**:闭卷候选打分 `s_QA`、`correct`(并列判为错)、`Score_split(f)`(聚合函数 mean)、`Acc(arm, split, G)`;TRAIN 闭卷检查 `s_ST`、`CB(f)`、`Acc_CB`(候选为 `candidates.json` 的 4 个,解释 B9);free-generation EM(全部细节,含 `do_sample=False`、16 个新 token、停止 token、`<think>…</think>` 删除与归一化;去结尾标点用 `str.rstrip('.,;:!?')`,开头的 “the ” 只去一次,解释 B8);AllCorrect;Prior、Spill、FPR(FPR 的分母改为 80 条 unread fact);ImmediateGain。`Acc_CB(arm)` 的分母改为 240。Retention 不定义、不报告(红线 6)。

**学习水平**(Task Order 6.1):`Acq(m) = Acc(m, DEV-QA, learned)`,m 为一个具体的模型(某方法、某种子、某剂量点的 checkpoint),四选一,按上面的打分方式。

**评测内容与时机**:

| 评测 | 内容 |
|---|---|
| DEV 评测(每个剂量点、N、S、Y、Z0、P+) | DEV-QA(learned 与 unread,640 问 × 4 候选)、TRAIN 闭卷(240 × 4)、D1 DEV、D2 DEV。不做 EM(EM 只在 TEST 评测中做,见下) |
| S 的置换映射正确率(S 在 d0) | 沿用 Pilot 第 8 节“只报告”一项:S 在它自己的置换映射上的 DEV 与 TRAIN 闭卷正确率 |
| TEST 评测(第 10 节第 11 步) | TEST-QA(960 问 × 4)、EM(TEST-QA 的 960 问)、AllCorrect、FPR;N 另做 TRAIN 闭卷(T3);括号 checkpoint 与 N 另做 D1 TEST、D2 TEST(第 6.4 节) |

## 6. iso-acquisition 设计

### 6.1 学习水平:第 5 节的 `Acq`。

### 6.2 比较点(Owner 决定,2026-11-28):t ∈ {0.70, 0.80, 0.90}。

### 6.3 剂量阶梯(PROPOSED;`DOSE_SPACE.json: dose`)

- **剂量维度**:训练遍数 k(对 240 条 TRAIN 陈述句读 k 遍;batch 8,每遍 30 步)。学习率在前 30 步(第 1 遍)从 0 线性升到峰值,之后**保持不变**(不衰减)。一次训练按最大剂量跑到底,在每个剂量点(第 30·k 步结束时)当场做一次 DEV 评测;因为学习率不衰减,第 k 个剂量点的模型就是“以该学习率训练 k 遍”的模型,与总长度无关。评测在 `model.eval()`、`torch.no_grad()`、FP32、不用 autocast 下进行,不改变参数、梯度、优化器状态与任何随机流,评测后回到训练模式继续。
- **剂量点**(F、L、A 相同):k ∈ {1, 2, 3, 4, 6, 8, 11, 16, 23, 32},共 10 个;最大 32 遍 = 960 步。相邻两点之比约 1.4(1–4 遍逐遍取,保证低端有点)。
- **d0**(Gate 0、S、Y 用的 F 剂量点)= 11 遍。理由:按下面“按遍”的换算,11 遍约等于 Pilot 选定配置 20 遍余弦训练的累积量,Pilot 的 G0.4–G0.7 正是在这一训练量上确认的;S、Y 在同一剂量点训练,与 Pilot 第 4 节“S、Y 沿用 F 的配置与训练量”的做法一致。
- **为什么预计能覆盖 0.70–0.90**(Pilot 的训练记录)。**换算口径**:按“遍”换算,即比较每条 fact 被训练时所用学习率的累积量(每遍每条 fact 恰好被更新一次,Pilot 与 V1 相同;V1 每遍 30 步只是因为 fact 数加倍)。Pilot 的余弦从峰值降到 10%,20 遍的平均倍数约 0.55,所以 Pilot 的 20 遍约等于常数学习率 11 遍。若改按“步”换算(累积量 = 学习率 × 步数,V1 每遍的步数是 Pilot 的 2 倍),Pilot 的 20 遍约等于 V1 的 5.5 遍,下面各方法越过 0.70 的遍数约减半(F 约 2 遍,L、A 约 1.7 遍),越过 0.90 的 F、L 约 5.5 遍;两种口径下,1、2、3、4 遍逐遍设点都能在 0.70 之前与之后各有剂量点。按遍换算时:F:Pilot F1(1e-5,20 遍)DEV 0.6208,相当于 3e-5 约 3.7 遍;F3(3e-5)三个种子 0.9125–0.9292,相当于约 11 遍(`training_runs/F-F1-seed101.json`、`F-F3-seed*.json: dev.acc_dev_learned`)。L:L4(3e-4,rank 32)0.7292,相当于 1e-3 约 3.3 遍;L6(1e-3,rank 32)0.8750–0.9792,相当于约 11 遍。A:A2(3e-5,λ 1)0.7000,相当于 1e-4 约 3.3 遍;A5(1e-4,λ 1)0.7833–0.8958,相当于约 11 遍。因此预计三种方法在 3–4 遍附近越过 0.70,F、L 在约 11 遍内越过 0.90;A 在 11 遍时约 0.82,阶梯延长到 32 遍(约 Pilot 累积量的 2.9 倍)是为了让 A 越过 0.90。这只是规划估计:没有越过的点按第 6.4 节记为 NOT_REACHED,不外推。
- **种子**:每种方法 3 个训练种子(101、202、303),每个种子一条独立的曲线(样本顺序 `rng_rule(TRAIN_SEED, "order:<k>")`,k = 1..32;L 另用于 A 矩阵初始化)。iso 点按种子分别确定(第 6.4 节),比较时先对种子取平均(第 8 节)。
- **计算量匹配(Amendment F)**:F、L、A 的配置数相同(各 1 个)、剂量点相同(同一组 10 个遍数)、事实 token 预算规则相同(第 k 个剂量点都恰好读过 k 遍 `train_F`,事实 token 数相同,撰写时每遍 3,802 token,含 `<|endoftext|>`)。不相同之处:(1)L 只训练适配器(rank 32 时约 3,486 万参数),前向参数量略大(base + 适配器);(2)A 每步另有 4 篇锚文档的前向(base 与训练模型)和反向。按“事实 token 相同”匹配的理由:学习量由读过的事实文本决定,三种方法读到的事实文本逐 token 相同;方法本身的额外计算(A 的锚文本、L 的适配器)是方法的组成部分,不折算成更多或更少的事实遍数,在算力记录中单列(沿用 Pilot 第 10 节与解释 B18 的算法)。

### 6.4 iso 点的确定规则(冻结)

记方法 X、种子 s 的 10 个剂量点为 j = 1..10(遍数 k_j 递增),其 DEV 学习量为 a_j = Acq(X_s@k_j)。对每个比较点 t:

1. **夹逼区间**:j* = 满足 a_{j−1} < t ≤ a_j 的最小 j(j ≥ 2)。不存在这样的 j(曲线从未从下方越过 t,包括第 1 个剂量点已 ≥ t 的情形)→ 该种子在 t 为 NOT_REACHED。
2. **匹配容差(DEV)**:τ_DEV = 0.10。若 t − a_{j*−1} > 0.10 或 a_{j*} − t > 0.10 → 该种子在 t 为 NOT_REACHED。理由:两个比较点相距 0.10,夹逼两端都不离 t 超过一个比较点间距,线性插值才是在 t 附近的局部估计;这个理由不依赖对剂量点之间跳变大小的预测。若某方法在相邻两个剂量点之间的跳变超过 0.20,该点按本条记为 NOT_REACHED,这是安全的结果(不比较),风险由第 6.3 节逐遍设置的低端剂量点降低。
2a. **算术**(冻结,第 6.4 节与第 6.7 节、第 6.5 节共用):Acq 与 TEST 学习量按精确有理数计算(`fractions.Fraction`:每条 fact 的 Score 为答对问句数 / 问句数,Acc 为 Score 之和 / fact 数),t、τ_DEV、τ_TEST 取 `Fraction("0.70")`、`Fraction("0.80")`、`Fraction("0.90")`、`Fraction("0.10")`、`Fraction("0.05")`;第 1、2 条与第 6.7 节的比较、w、第 6.5 节的插值与比较都用精确有理数完成。逐单位的浮点量(窗口 NLL、D2 字母分数、`d`、`e`)与 w 相乘时用 `float(w)`(IEEE 双精度)。
3. **插值(在相邻两点间线性插值;不选最近点)**:权重 w = (t − a_{j*−1}) / (a_{j*} − a_{j*−1}) ∈ (0, 1]。任何逐单位的量 v(一个窗口的 d,一道 D2 题的 e,一条 fact 的 Score)在 t 处的值为 v_t = (1 − w) · v(X_s@k_{j*−1}) + w · v(X_s@k_{j*})。DEV 上 Acq 的插值值按构造等于 t。TEST 上沿用同一个 w(由 DEV 确定)。
4. **方法层面**:3 个种子都不是 NOT_REACHED,方法 X 在 t 才可比较;否则 X 在 t 记为 NOT_REACHED,不参与 t 的任何比较,不得外推,不得用其余种子代替。
5. **只用 DEV**:以上全部只用 DEV-QA 的学习量;损伤的数值不参与 iso 点的确定。

### 6.5 TEST 上的匹配验证

对每个可比较的 (X, t),TEST 学习量 `Acq_TEST(X, t)` = 3 个种子的 `(1 − w_s) · Acc(X_s@lo, TEST-QA, learned) + w_s · Acc(X_s@hi, TEST-QA, learned)` 的平均。比较 X−F(X ∈ {L, A})在 t 处:若 |Acq_TEST(X, t) − Acq_TEST(F, t)| > **τ_TEST = 0.05**,该比较记为 MATCH_FAILED,其损伤差照常计算并报告,但标为 MATCH_FAILED,不给结论词,不作解释。理由:Pilot 中 L、A 与 F 从 DEV 到 TEST 的 seed-average 学习量变化之差最大为 0.040(F:0.9236 → 0.9296,变化 +0.0060;L:0.9389 → 0.9500,+0.0111;A:0.8222 → 0.8685,+0.0463;选定配置三个种子的 `training_runs/*.json: dev.acc_dev_learned` 与 `test_evaluation_result.json: summaries.*.acc_test_learned` 的平均);0.05 容纳这种程度的 DEV→TEST 差异,同时小于比较点间距的一半。

### 6.6 防止选择偏差

本协议**不从多个配置中按损伤选择**:每种方法只有一个预先固定的配置(第 4 节),剂量点只按 DEV-QA 的学习量确定(第 6.4 节第 5 条)。因此 DEV 上不存在“挑损伤最小者”的步骤。另外,损伤的 DEV 部分与 TEST 部分文档或题目不相交(第 7.2 节),iso 点(含插值权重)写入选择冻结记录之后才生成 TEST,TEST 上的比较只用 TEST 的损伤评测集。

### 6.7 checkpoint 的保存规则(冻结;只用 DEV 学习量,训练当场决定)

每个剂量点评测之后:若存在一个比较点 t,使 t 在该点之前尚未被越过(没有 i < j 满足 a_{i−1} < t ≤ a_i),且 |a_j − t| ≤ 0.10,则保存该剂量点的 checkpoint 并计算 `state_sha256`;否则不保存。按第 6.4 节,任何合格的夹逼两端都满足这个条件,所以 TEST 需要的 checkpoint 都已保存。另外总是保存:F 在 d0 的 3 个 checkpoint(G0.8、T1)、S 与 Y 的最终 checkpoint、P+ 的最终 checkpoint、Z0 的最终 checkpoint。L 的 checkpoint 只保存适配器参数与所用 base 的 `state_sha256`;F、A、S、Y、P+、Z0 保存完整的 FP32 `state_dict`。不删除任何 checkpoint。

### 6.8 选择冻结记录

第 10 节第 9 步提交 `results/selection_freeze_record.json`:每个 (方法, 种子, t) 的 j*、两个剂量点的遍数、a_{j*−1}、a_{j*}、w、两个 checkpoint 的 `state_sha256`,或 NOT_REACHED 及原因;每个 (方法, t) 的可比较状态;TEST 要评测的全部 checkpoint 清单(去重)。该记录提交并推送之前不得生成或读取任何 TEST(ST13)。

## 7. 损伤的测量

### 7.1 两个指标

**D1:通用文本 dNLL**(定义**沿用 Pilot 第 5 节** general damage:`NLL_θ(w) = −(1/(n_w − 1)) · Σ_{t=2..n_w} log p_θ(x_t | x_<t)`,窗口前不加特殊 token,n_w 为送入模型的 id 数)。逐窗口损伤 `d_θ(w) = NLL_θ(w) − NLL_N(w)`。按领域分层报告三个量:

- `D1-all(θ)` = 4 个领域(books、c4、fineweb、wikitext)各自窗口均值的平均(即 Pilot 的 dNLL);
- `D1-diff(θ)` = 与锚文本来源不同的 3 个领域(books、c4、wikitext)各自均值的平均;
- `D1-same(θ)` = 与锚文本同来源的 fineweb 领域的均值(Stage 1 的 fineweb 窗口来自 FineWeb-Edu 的留出验证分片,与锚文本同属 `SandyResearch/fineweb-edu-shuffled`,`research/mini_mythos/stage1/README.md` 评测集表)。
PPL_degradation% 沿用 Pilot,只作展示。

**D2:能力测验**(公开选择题数据集上的正确率下降;用候选的条件对数似然打分):

- 题面 `p = I + "\n\n" + question.strip() + "\n" + "A. " + c_0 + "\n" + "B. " + c_1 + "\n" + "C. " + c_2 + "\n" + "D. " + c_3`,`I = "Answer the following multiple choice question with the letter of the correct option."`,`c_i = str(选项 i).strip()`,选项按数据集原顺序。
- 指令 `I` 的理由:一句话写明题型与作答方式(给出选项字母),不加示例(0-shot),使 N 与各训练模型看到完全相同的题面;措辞不针对任何模型调过。
- `s_D2(θ, i, ℓ) = log p_θ(" " + ℓ | chat(p_i) + "The answer is")`,ℓ ∈ {A, B, C, D}(第 0 节)。这是对 Task Order 7.1“用候选的条件对数似然打分”的一种解释:候选是 4 个选项字母,在列出选项的题面之后对字母打分(MMLU 的通行做法),而不是对选项文本本身打分。理由:选项文本长度不一,直接比较其对数似然有长度偏差;字母打分每题只需一次前向;答案前缀 `The answer is` 与事实 QA 的打分输入一致。请 Review Gate 确认这一解释(`SUBMISSION_NOTE.md` 第 5 节)。`c_θ(i) = 1[s_D2(θ, i, ℓ*_i) > max_{ℓ ≠ ℓ*_i} s_D2(θ, i, ℓ)]`,并列判为错;`Acc_D2(θ) = mean_i c_θ(i)`。
- `dAcc(θ) = Acc_D2(θ) − Acc_D2(N)`(Task Order 7.1)。为与 D1 同向(数值越大损伤越大),本协议的 **D2 损伤**定义为逐题 `e_θ(i) = c_N(i) − c_θ(i)`、`D2(θ) = mean_i e_θ(i) = −dAcc(θ)`。
- **数据集**(第 15 节待决第 2 项):首选 MMLU,备选 ARC;两者的 revision、文件 sha256、许可证、行数均已在撰写环境中核实(`reports/authoring/d2_dataset_metadata.txt`;下载文件的 sha256 等于 Hub 记录的 LFS oid):
  - 首选 `cais/mmlu` @ `c30699e8356da336a370243923dbaf21066bb9fe`,许可证 MIT(允许研究使用);DEV 来源 `all/validation-00000-of-00001.parquet`(sha256 `66cdf0b090ccb657d18d13cd81e31fdc55c3467da9642ffb178653268a97c8ef`,1,531 行),TEST 来源 `all/test-00000-of-00001.parquet`(sha256 `74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7`,14,042 行)。理由:57 个学科的真实世界知识与推理题,四选一,与虚构事实无关;字母打分每题只需一次前向;撰写时 DEV 抽样的上下文平均 134 个 token。
  - 备选 `allenai/ai2_arc` @ `210d026faf9955653af8916fad021475a3f00453`,许可证 CC-BY-SA-4.0(允许研究使用,署名与相同方式共享);DEV 来源 ARC-Challenge 与 ARC-Easy 的 validation(299 + 570 行),TEST 来源两者的 test(1,172 + 2,376 行);文件 sha256 见 `DAMAGE_MANIFEST.json`。只用恰好 4 个选项的题(DEV 来源 869 行中 862 行为 4 个选项、7 行不是,`audit/stdout/a5_damage.txt`;撰写时按打乱顺序访问到第 806 行即凑满 800 题,其间排除 6 行),标签按原顺序对应 A–D。
- **与虚构事实无关**:V1 的 entity 与 answer 是按第 2.2 节随机生成的虚构字符串(natural 为随机音节,random 为随机字母段加数字),D2 是已有的真实题目;可执行检查为 L8(含任一 V1 字符串的题目在生成时排除,撰写时 MMLU 与 ARC 的 DEV 抽样中都是 0 题)。

### 7.2 评测集与划分(PROPOSED;`DAMAGE_MANIFEST.json`)

| 集合 | 来源 | 规则 | 数量 |
|---|---|---|---|
| D1 DEV `general_dev.jsonl` | Pilot 第 2.7 节的通用文本来源(`research/mini_mythos/stage1/results/r1/eval_sets.jsonl`,sha256 `8816fe5a…a155`;parcae 分词器解码,全值见 manifest) | 每个领域(books、c4、fineweb、wikitext)按文件顺序取 `split == "dev"` 的全部 100 行;窗口 = 本协议分词器切分后的前 256 个 id(不足取全长,送入模型的就是这些 id),记录 `{"domain", "doc_id", "ids", "text"}`(沿用 Pilot 第 2.7 节与其实现格式);依次排除触发 L8、L6 的窗口 | 撰写时 400(每领域 100,排除 0);规范化 SHA-256 `e8350160464963e684e0c58826d53250dec4de366a716d3111aa8ec5089ce281` |
| D1 TEST `general_test.jsonl` | 同上 | 每个领域按文件顺序取 `split == "test"` 的行,**跳过该领域的前 25 行**(Pilot 的 TEST 窗口,不复用);窗口同上;依次排除触发 L8、L6、与某个 DEV 窗口 id 序列相同的窗口;每个领域取前 100 个 | 400(每领域可用 175 行);不足 100 → ST10 |
| D2 DEV `d2_dev.jsonl` | 首选:MMLU `all/validation` | 行号 0..1530 用 `rng_rule(DATA_SEED, "d2:mmlu:validation:order")` 做一次 `shuffle`;按此顺序依次排除不是恰好 4 个选项或答案不在 0–3 的题、触发 L8、触发 L6 的题;取前 800 题;记录 `{"item", "source_row", "subject", "prompt", "answer"}`(answer 为字母) | 800;撰写时排除 0;规范化 SHA-256 `f40c146a3da500f13797dcfedfb2932e8a5dc88a6b43cbd423bf8fb549a688be`(备选 ARC:purpose `d2:arc:validation:order`,行号为 Challenge validation 之后接 Easy validation 的序号,`subject` 字段记题目 id;`1ea77c8adeb84b6d5f7a3aa699ab02951e4f43bd27ba14f36c3a32287e04ac32`) |
| D2 TEST `d2_test.jsonl` | 首选:MMLU `all/test` | 行号用 `rng_rule(DATA_SEED, "d2:mmlu:test:order")` 做一次 `shuffle`;同样的排除规则,另排除题面与某个 DEV 题面完全相同的题;取前 800 题(备选:`d2:arc:test:order`,Challenge test 接 Easy test) | 800;不足 → ST10 |

D1 的 DEV 与 TEST 来自 `eval_sets.jsonl` 的不同 split,D2 的 DEV 与 TEST 来自数据集的不同 split,文档或题目不相交;TEST 另排除与 DEV 相同的单位。DEV 与 TEST 数量相同,使第 7.6 节由 DEV 推出的 margin 与 TEST 上的抽样波动同一尺度。数量的理由:D1 每领域 100 个窗口是 DEV 来源的全部;D2 800 题使 `Acc_D2(N)` 的抽样标准误约 0.017(按正确率 0.5–0.6 估算),与 D1 的 margin 量级相当;更大的集合会使每次评测的时间超出第 12 节估算的主要部分(每次 DEV 评测约 101 秒中,D1 与 D2 合计约 70 秒)。

Gate D 与 iso 点的确定只用 DEV 部分(Task Order 7.2)。

### 7.3 统计单位

D1 以窗口为单位、D2 以题目为单位做配对 bootstrap,10,000 次(第 8 节)。种子之间的变化单独报告(每个种子一个点估计与 CI,另报 3 个种子点估计的最小值、最大值与样本标准差)。

### 7.4 与锚文本隔离

D1 的 books、c4、wikitext 三个领域与锚文本来源不同,fineweb 与锚文本同来源,D2 与锚文本来源不同;`D1-diff` 与 `D1-same` 分开报告,主比较用 `D1-diff`(第 9.4 节),因此 A 的结论不依赖它被约束的分布。需要注意:c4(C4 英文 validation)虽然来源不同,但与 FineWeb-Edu 同为网页文本,Stage 1 把它标为“网页,近分布”(`research/mini_mythos/stage1/README.md` 评测集表),books(PG-19)与 wikitext 离锚文本更远。因此 Gate M 另把四个领域的逐领域损伤(`D1-books`、`D1-c4`、`D1-fineweb`、`D1-wikitext`,每个领域的窗口均值)与它们的方法间比较作为次要比较单独报告(第 9.3 节),读者可以看到 A 的差异是否集中在 fineweb 与 c4。是否把主比较改为只用 books 与 wikitext,请 Review Gate 决定(本协议的提案保留三个领域:窗口数 300 对 200,抽样标准误较小)。与锚文本的 n-gram 重叠检查沿用 L6 的做法(第 3 节,扩大到 D1 与 D2 的全部划分)。

### 7.5 Gate D 的条件(全部为数值,冻结;PROPOSED)

| 编号 | 条件 |
|---|---|
| G-D1 阴性对照 Z0(种子 101、202、303) | 每个种子:重载后的 `state_sha256` 等于 N 的 `state_sha256`;Z0 与 N 的 DEV 评测逐单位比较:每个候选分数差 ≤ 1e-4、每个 D1 窗口的 NLL 差 ≤ 1e-5、每个 D2 字母分数差 ≤ 1e-4;预测(事实 QA、D2)须完全相同,只有某题在两者中任一次最高两个分数之差 ≤ 1e-4 时允许不同(沿用 Pilot G0.8 的规则)。由此 Z0 的 `D1-all`、`D1-diff`、`D1-same` 的绝对值 ≤ 1e-5,`D2` 只能由允许的近似并列造成,3 个种子之间的波动为 0(在上述容差内) |
| G-D2 噪声基线 | `σ_N(M)` = N 在 M 的 DEV 集上的水平统计量的 bootstrap 标准差(10,000 次,第 8 节):M = `D1-all`(4 领域分层的窗口 NLL 均值的平均)、`D1-diff`(3 领域)、`D1-same`(fineweb)、`D2`(`Acc_D2(N)`)。四个值都必须有限且 > 0;并且由它们按第 7.6 节算出的 `m(D1-all)`、`m(D1-diff)` ≤ 0.10,`m(D1-same)` ≤ 0.20(`m(D2)` 由题数决定,最大为 2 × sqrt(0.25/800) ≈ 0.035,不另设上界)。训练种子之间的波动:P+ 三个种子的 `D1-diff`、`D2` 的样本标准差只报告;Gate M 用“每个种子的点估计同向”的要求处理种子波动(第 9.4 节) |
| G-D3 阳性对照 P+(种子 101、202、303) | `D1-diff`:seed-average ≥ +1.00,其 95% CI 下界 > 0,且每个种子 ≥ +0.50;`D2`:seed-average ≥ +0.05(即 dAcc ≤ −0.05),其 95% CI 下界 > 0,且每个种子 > 0 |
| G-D4 复现 | P+ 种子 101:训练结束时当场评测一次,保存、重载后重算 `state_sha256`(须相同)再评测一次;两次逐单位比较,容差同 G-D1(候选分数 1e-4、D1 窗口 NLL 1e-5、D2 字母分数 1e-4、预测规则同 Pilot G0.8) |
| G-D5 D1 与 D2 的一致性 | 只报告,不设门槛:P+ 的三个种子的 (`D1-diff`, `D2`);Gate M 的 DEV 评测全部完成后,另报全部训练模型 DEV 评测(10 个剂量点 × 9 条曲线、S、Y、P+)上 `D1-diff` 与 `D2` 的 Spearman 秩相关 |

**Gate D 通过** = G-D1、G-D2、G-D3、G-D4 全部满足。任一不满足 → ST14:停止,不运行第 6 步起的任何训练,状态 PIPELINE_NOT_QUALIFIED(原因:G-D1 或 G-D4 不满足为 IMPLEMENTATION_FAIL;G-D2 或 G-D3 不满足时写明失败的条件编号)。

**阈值的理由**:G-D1、G-D4 的容差沿用 Pilot G0.8(Pilot 实测的复评差为 0,`metrix/e1-pilot/results/step7_record.json: values.G0.8`)。P+ 用 Pilot F6 的学习率与 weight decay,11 遍常数学习率约等于 F6 在 Pilot 中 20 遍余弦的累积量(第 6.3 节的换算),F6 的 DEV dNLL 为 +5.55(`training_runs/F-F6-seed101.json: dnll`),下限 +1.00 远低于这个值,只要求“明显的损伤”能被量到;每个种子 ≥ +0.50 防止只靠一个种子过线。D2 没有 Pilot 数据可依,+0.05 约为 `σ_N(D2)` 预计值(约 0.017)的 3 倍。G-D2 的“不该造成损伤的对照在种子之间的波动”由 Z0 给出:learning rate 为 0 时参数逐位不变,波动按构造为 0,G-D1 检查它确实为 0;这只证明流程本身不引入波动,不测量训练带来的种子波动,后者由 P+ 的三个种子报告、在 Gate M 中按第 9.4 节处理。G-D2 上界的理由:Pilot 冻结的 general-damage margin 为 dNLL ≤ +0.03(Pilot 第 13 节第 2 项);若 `m(D1)` 超过它的约 3 倍(0.10),说明这组窗口分辨不出 Pilot 认为有意义的差异的量级,尺子过粗,Gate D 不通过;fineweb 单领域的窗口数是 4 个领域合计的四分之一,标准误约为 2 倍,上界取 0.20。规划估计(只作规划,不进记录;Task Order 红线 7):按 Pilot 的 N 在 Pilot DEV 窗口上的逐窗口 NLL(`metrix/e1-pilot/results/details/N_dev.json: evaluation.general_dev[*].nll`,每领域 25 个)的领域标准差换算到每领域 100 个窗口,预计 `m(D1-all)` 约 0.045、`m(D1-diff)` 约 0.052、`m(D1-same)` 约 0.090,都在上界之内(`reports/authoring/sigma_planning.py` 及其输出 `sigma_planning.txt`)。

### 7.6 non-inferiority margin

- **公式(冻结)**:对每个损伤指标 M ∈ {`D1-all`, `D1-diff`, `D1-same`, `D2`},`m(M) = 2 × σ_N(M)`,`σ_N(M)` 取自 Gate D 记录 `results/gate_d_record.json` 的 G-D2 一项(第 10 节第 4 步)。理由:m 是预先登记的“最小有实际意义的损伤差”,按这组评测单位自身的分辨率定标。`σ_N` 是 N 的水平统计量的抽样标准差,含单位之间的异质性;方法间的比较是逐单位的配对差,其抽样波动通常小于 `σ_N`,所以 m 不是“与抽样波动不可区分”的界限,而是比配对比较的分辨率更宽、偏保守的实际意义阈值;倍数 2 是预先登记的选择(约为 N 水平的 95% 抽样区间半宽)。与 Pilot 第 13 节第 2 项(dNLL ≤ +0.03,固定数值,Pilot 中只报告)的关系:V1 的评测集扩大并按领域分层,margin 改为由同一组单位的分辨率推出,并由 G-D2 的上界(0.10)保证它不比 Pilot 的值宽出一个数量级。
- **时机**:Gate D 通过后,Executor 计算四个 margin,写入 `results/margin_record.json`(MARGIN_RECORD:公式、输入值、输入记录的文件 sha256 与提交、四个 margin),提交并推送;之后才允许第 6 步起的任何训练(ST15)。margin 不得在看到任何方法比较之后确定或修改。

## 8. 统计计划

- **事实指标**:**沿用 Pilot 第 6 节**(bootstrap 单位是 fact_id;在 natural、random 两个 stratum 内分别有放回重抽;10,000 次;95% CI 为第 2.5 与 97.5 百分位;每个种子单独报告,再报 seed-average:先对每条 fact 把 3 个种子的 Score 取平均再 bootstrap;不报告 p 值作为判据),实现细节为解释 B10(每个比较一个生成器 `r = rng_rule(BOOTSTRAP_SEED, purpose)`;每次重抽按 natural、random 的顺序,`r.choices(d_stratum, k=len(d_stratum))`,stratum 内按 `facts.jsonl` 顺序)、B11(百分位为排序后第 (B − 1)·p/100 位置的线性插值,即 numpy 默认的 `linear`)、B12(purpose 写法 `<X>-<Y>:<split>:<seed 或 avg>`,split 为 `DEV` 或 `TEST`)。E1-V1 每个 stratum 120 条 learned fact、40 条 unread fact。
- **D1**:配对差 `Δ(w) = v_X(w) − v_Y(w)`(v 为第 6.4 节在 t 处的插值值或某个模型的 `d`);统计量 = 各领域窗口均值的平均(`D1-all` 4 个领域,`D1-diff` 3 个,`D1-same` 1 个);重抽在领域内进行,领域顺序 books、c4、fineweb、wikitext(只取统计量用到的领域),`r.choices(窗口, k=该领域窗口数)`,窗口按 `general_dev.jsonl` / `general_test.jsonl` 顺序;两个模型使用同一批重抽到的窗口。`σ_N(M)` 用同样的重抽,统计量为 N 的窗口 NLL 的领域均值的平均,取 10,000 个重抽值的样本标准差(分母 B − 1)。
- **D2**:配对差 `Δ(i) = e_X(i) − e_Y(i)`;统计量 = 题目均值;重抽不分层,`r.choices(题目, k=800)`,题目按 `d2_dev.jsonl` / `d2_test.jsonl` 顺序。`σ_N(D2)` 的统计量为 `Acc_D2(N)`。
- **seed-average**:先在每个单位上对 3 个种子的值取平均,再 bootstrap(与 Pilot 第 6 节相同)。每个种子另做一次 bootstrap,报告点估计与 CI;种子之间的变化另报 3 个种子点估计的最小值、最大值与样本标准差。
- **purpose**:`<X>-<Y>:<split>:<指标>:<t>:<seed 或 avg>`,例如 `L-F:TEST:D1-diff:0.80:avg`、`A-N:DEV:D2:0.70:202`;Gate D 用 `P+-N:DEV:<指标>:-:<seed 或 avg>`;噪声基线用 `N:DEV:<指标>:level`;事实指标沿用 B12(例如 `F-N:DEV:avg`,F 指 d0 的模型)。
- **精度说明**:240 条 learned fact 时,正确率在 0.5 附近的标准误不超过 0.033。

## 9. Gate 与比较

### 9.1 Gate 0(事实测量再确认;只用 TRAIN 与 DEV)

数值**沿用 Pilot 第 8 节 G0.1–G0.9**;“F”指 F 在 d0(11 遍)的 3 个模型,S、Y 在 d0。G0.10 是 Pilot 为 E1-V1 做规模估计的条件,E1-V1 不使用。

| 编号 | 条件 |
|---|---|
| G0.1 | 泄漏检查 L1–L8 的 DEV 部分全部在上限内;涉及 TEST 的部分按第 10 节第 10 步运行 |
| G0.2 | 所有用到的损失、分数、NLL 都是有限值 |
| G0.3 | N 的下限检查:`Acc(N, DEV-QA, learned)` ∈ [0.15, 0.35],每个 stratum ∈ [0.10, 0.40];`Acc(N, DEV-QA, unread)` ∈ [0.10, 0.40];`Acc_CB(N)` ∈ [0.15, 0.35] |
| G0.4 | `Acc_CB(F@d0)` ≥ 0.90,3 个种子都满足 |
| G0.5 | seed-average `Acc(F@d0, DEV-QA, learned)` ≥ 0.70;seed-average Δ(F@d0−N) 的 95% CI 下界 > 0;每个种子的 Δ(F@d0−N) > 0 |
| G0.6 | seed-average Δ(S@d0−N)(真实映射,DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.7 | seed-average Δ(Y@d0−N)(DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.8 | 复现:F@d0 的 3 个 checkpoint 各评测两次(训练中当场一次,重载后一次);候选分数差 ≤ 1e-4;某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同,其余预测须完全相同;并列判为错;每个 D1 窗口的 NLL 差 ≤ 1e-5;每个 D2 字母分数差 ≤ 1e-4(D2 的预测规则同候选)。实现须开启 PyTorch 确定性设置并记录 |
| G0.9 | **只报告,不设门槛**:seed-average `Acc(F@32 遍, DEV-QA, learned)`。理由:Pilot 的上限 0.95 用来防止题目过易;E1-V1 的题目难度不变是 Owner 的决定(2026-11-28),且剂量阶梯有意延长到学习量很高的区域,上限检查失去原来的作用 |

任一不满足 → PIPELINE_NOT_QUALIFIED,按 ST19 停止(不运行 L、A 的曲线),TEST 不生成、不评测;越过 G0.3 的界限触发 benchmark 重新校准(新协议版本);F 的正确率 < 0.40 与 [0.40, 0.70) 的标注沿用 Pilot 第 8 节。只报告:各 arm 的 Spill 与 FPR、AllCorrect、S 在它自己的置换映射上的正确率。

**TEST 确认**(第 10 节第 11 步,与 Gate M 的 TEST 评测同一次):T1 seed-average `Acc(F@d0, TEST-QA, learned)` ≥ 0.70,且 seed-average Δ(F@d0−N) 的 95% CI 下界 > 0;T2 S、Y 在 TEST-QA 上满足 G0.6、G0.7 的同样数值;T3 N 在 TEST-QA 上满足 G0.3 的同样范围(含 `Acc_CB(N)`,解释 B24)。

### 9.2 Gate D:第 7.5 节。

### 9.3 Gate M 的比较

只在 Gate D 通过、MARGIN_RECORD 已提交、Gate 0 通过之后进行。对每个比较点 t、每个指标 M ∈ {`D1-all`, `D1-diff`, `D1-same`, `D2`} 以及逐领域指标 `D1-books`、`D1-c4`、`D1-wikitext`(`D1-fineweb` 即 `D1-same`;第 7.4 节)、DEV 与 TEST 两个 split:

- 每个方法 X ∈ {F, L, A} 在 t 处的损伤(相对 N):seed-average 与每个种子,含 95% CI(“损伤各有多大”);
- Δ损伤(L−F)、Δ损伤(A−F):seed-average 与每个种子,含 95% CI(主比较为 97.5%,见第 9.4 节);
- TEST 上另报 `Acq_TEST(X, t)` 与第 6.5 节的匹配状态。

一方为 NOT_REACHED 的比较记为 NOT_REACHED;TEST 上匹配失败的比较记为 MATCH_FAILED(第 6.5 节)。只在 iso 点上比较方法间损伤;剂量曲线(每个剂量点的 Acq 与各损伤值)只作描述,不在不同学习水平之间做方法比较(红线 5)。

### 9.4 主比较、多重比较与结论词汇

- **主比较族(唯一)**:TEST 上、t = 0.80、指标 `D1-diff` 的两个比较 Δ(L−F) 与 Δ(A−F)。理由:0.80 位于三个比较点中间,按第 6.3 节的估计三种方法都最可能被夹逼;`D1-diff` 是 Pilot 已有的指标在与锚文本来源不同的领域上的版本(第 7.4 节)。
- **多重比较**:主比较族的两个比较按 Bonferroni 处理,各用 97.5% CI(第 1.25 与 98.75 百分位)。其余全部为次要比较(其它比较点、其它指标、DEV 上的全部比较、每个方法自身的损伤),报告 95% CI,结论词汇在下条规定的范围内计算并标为“次要”,不作确证性结论,不影响最终状态,不做多重比较校正。
- **结论词汇**(对指标 M 上的 Δ = D(X) − D(F),X ∈ {L, A};D 越大损伤越大;[lo, hi] 为该比较的 CI,Δ_s 为每个种子的点估计,m = m(M) 取自 MARGIN_RECORD,主比较为 m(`D1-diff`))。只有 M ∈ {`D1-all`, `D1-diff`, `D1-same`, `D2`} 的方法间比较给结论词;每个方法自身的损伤(X 相对 N)与逐领域指标 `D1-books`、`D1-c4`、`D1-wikitext` 的比较只报告点估计与 CI,不给结论词:
  - **superior**:hi < 0,且 3 个 Δ_s 都 < 0;
  - **non-inferior**:不是 superior,hi < m,且 3 个 Δ_s 都 < m;
  - **inferior**:lo > m,且 3 个 Δ_s 都 > m;
  - **inconclusive**:其余情形。
  四者互斥且穷尽。要求每个种子的点估计同向,是因为 bootstrap 只对窗口重抽,不包含种子之间的变化(第 7.3 节)。

### 9.5 TEST

Gate 0、Gate D、iso 点的确定都只用 TRAIN 与 DEV。TEST(事实 QA 与损伤评测)在选择冻结记录提交之后、Owner 批准入库之后,按第 10 节第 10、11 步只生成一次、只评一次;ST10、TEST 标记与“只评一次”的闸门**沿用 Pilot 第 8 节第 8 步与 Pilot 实现**(评测前提交 TEST 标记,写明要评的全部 checkpoint 的 `state_sha256` 与 TEST 文件的 sha256;重载后重算 `state_sha256` 必须等于标记中的值;同一标记不得第二次评测)。

### 9.6 失败分类

固定词汇沿用 Pilot 第 9 节:`PASS` / `HYPOTHESIS_FAIL` / `IMPLEMENTATION_FAIL` / `OPTIMIZATION_FAIL` / `CAPACITY_LIMIT` / `OPTIMIZATION_OR_CAPACITY_UNRESOLVED` / `BLOCKED` / `NOT_TESTED` / `PIPELINE_NOT_QUALIFIED`,各自的使用条件沿用 Pilot 第 9 节,其中 IMPLEMENTATION_FAIL 另包括 G-D1、G-D4 不满足、ST13、ST15、ST16;BLOCKED 另包括 ST10 的 D1 / D2 部分与 ST18。HYPOTHESIS_FAIL 不使用:E1-V1 的主比较是带结论词汇的估计,没有预先登记的方向性假设。本协议新增两个词:

- **NOT_REACHED**:某方法在某比较点上没有合格的夹逼区间(第 6.4 节第 1、2 条,任一种子即算);该方法在该点不参与任何比较,不外推。
- **MATCH_FAILED**:两方法在某比较点上都可比较,但 TEST 学习量之差超过 τ_TEST = 0.05(第 6.5 节);该比较的损伤差照常报告,不给结论词,不作解释。

### 9.7 最终状态

1. Gate 0 不通过,或 T1–T3 不满足 → `PIPELINE_NOT_QUALIFIED`(原因沿用 Pilot 第 9 节与解释 B24)。
2. Gate D 不通过 → `PIPELINE_NOT_QUALIFIED`(原因见第 7.5 节)。
3. 以上都通过:主比较族的两个比较都有结论词 → `PASS`,并给出两个结论词;否则,任一为 NOT_REACHED → 最终状态 `NOT_REACHED`;否则(任一为 MATCH_FAILED)→ `MATCH_FAILED`。
4. 停止条件造成的 BLOCKED、NOT_TESTED、IMPLEMENTATION_FAIL 按第 13 节。

看到结果之后不得修改任何门槛、容差或 margin 公式;协议本身有缺陷时,开新版本。

## 10. 执行顺序

每一步的停止规则见第 13 节;每一步的记录提交并推送之后才进入下一步(Pilot 实现的做法)。

1. 记录环境与出处;GPU 检查(沿用 Pilot 第 8 节第 1 步);在 CPU 上生成第 2.8 节的非 TEST 文件,核对第 2 节与 `DAMAGE_MANIFEST.json` 的参考哈希(ST12);运行 L1–L8 的 DEV 部分(ST1)。记录 `results/step1_record.json`。
2. 预检(ST11):在 A100 上跑 F、L、A 各前 20 步并计时,计时一次 base 加载、N 的一次 DEV 评测、一个完整 checkpoint 的保存与重载(各含 `state_sha256`);按第 12 节的 ST11 公式估算总 GPU 时间。记录 `results/preflight_record.json`。
3. 评测 N(DEV);G0.3(ST2)。记录 `results/n_dev_record.json`(含逐单位值)。
4. Gate D:Z0 三个种子、P+ 三个种子、G-D4、G-D2 的 `σ_N`;判定 Gate D(ST14)。记录 `results/gate_d_record.json`。
5. 计算 margin,提交并推送 `results/margin_record.json`(MARGIN_RECORD)。
6. F 的种子 101 曲线(32 遍,10 个剂量点);ST3:`Acc_CB(F@d0)` < 0.90 或 `Acq(F@d0)` < 0.70 → 停,不跑其余训练。然后 F 的种子 202、303;S、Y 各三个种子(到 d0)。每次训练一条记录 `results/runs/<run>.json`。
7. G0.8 复评;判定 Gate 0(ST4、ST5、ST19)。记录 `results/gate0_record.json`。
8. L、A 各三个种子的曲线(32 遍,10 个剂量点)。
9. 按第 6.4 节确定全部 iso 点;计算 DEV 上第 9.3 节的全部比较与 G-D5;提交并推送 `results/selection_freeze_record.json`。之后停下,等待 Owner 对 TEST 生成与评测的批准入库(第 16 节)。
10. 生成 `test_qa.jsonl`、`general_test.jsonl`、`d2_test.jsonl`;对 TEST 运行 L3a–L5、L6、L8(L6、L8 由 Executor 与 data-auditor 各自计算,ST10)。记录 `results/st10_record.json`。
11. 提交 TEST 标记 `results/test_evaluation_marker.json`;对 N、F@d0、S、Y 与选择冻结记录中的全部 checkpoint 做 TEST 评测,只评一次;计算 T1–T3、第 6.5 节的匹配、第 9.3–9.4 节的全部比较与最终状态。记录 `results/test_evaluation_result.json`。
12. 写两份实验记录(第 14 节);把全部记录推送。
13. **终止前核对**(第 14 节):data-auditor 核对“协议要求报告的每个数值都能只从仓库得到”,通过之后才可终止机器(ST17)。

**算力边界**:第 2–11 步全部在设备全名与首次记录逐字相同的一张 A100 80GB 上执行,累计 GPU 时间 ≤ H(第 12 节);任何一步若会使累计时间超过 H,按 ST7 停下,不得为节省时间删减本节的任何一步。

## 11. 训练契约(PROPOSED;`DOSE_SPACE.json: training_contract`)

| 项 | 值 | 理由或来源 |
|---|---|---|
| 优化器 | AdamW,betas (0.9, 0.999),eps 1e-8 | 沿用 Pilot 第 7 节 |
| batch | F、L、A、S、Z0、P+:8 条陈述句;Y:16 句;都是每遍 30 步 | 沿用 Pilot(每遍步数随 fact 数加倍) |
| 训练长度 | F、L、A:32 遍(960 步);S、Y、P+:11 遍(330 步);Z0:2 遍(60 步) | 第 6.3 节、第 4 节 |
| 顺序 | 每遍一次全排列,`rng_rule(TRAIN_SEED, "order:<k>")`,k = 1..32;`r.shuffle(list(range(N)))`,第 k 遍的批为排列的连续切片(解释 B3) | 沿用 Pilot |
| 序列 | 一条陈述句一个序列,其后接 `<\|endoftext\|>`;右侧补齐到批内最长;补齐位不计损失 | 沿用 Pilot 第 0、7 节 |
| 事实损失 | CE = 批内全部非补齐目标位置(每个序列 t = 2..n,含句末 `<\|endoftext\|>`)的 −log p 之和除以这些位置的个数(按 token 加权,不先对序列求均值;解释 B4) | 沿用 Pilot |
| 梯度累积 | 1 | 沿用 Pilot |
| warmup | 前 30 步(第 1 遍)从 0 线性上升到峰值 | Pilot 为第 1 遍(15 步),按遍对齐 |
| scheduler | warmup 之后常数,不衰减 | 剂量点是同一次训练的中间点(第 6.3 节) |
| weight decay | F、L、A、S、Y、Z0:0.0;P+:0.1;只作用于二维权重矩阵(含共享的词嵌入,解释 B7) | 沿用 Pilot 的选定配置与 F6 |
| 梯度裁剪 | 全局范数 1.0 | 沿用 Pilot |
| 精度 | bf16 autocast,主权重与优化器状态 FP32;评测 FP32 | 沿用 Pilot |
| 评测时机 | 每个剂量点(第 30·k 步之后)当场 DEV 评测,不改变训练状态 | 第 6.3 节 |
| checkpoint | 按第 6.7 节保存;不删除 | 第 6.7 节 |
| early stopping | 不允许:每次训练跑到它的训练长度 | 沿用 Pilot;各方法剂量点相同 |
| 非有限值 | 训练或评测出现非有限值:ST6;所有曲线、S、Y、Z0、P+ 都是“用到的”训练 | 沿用 Pilot |
| 训练次数 | 曲线 9(F、L、A × 3 种子)+ S 3 + Y 3 + Z0 3 + P+ 3 = 21 次 | — |

算力记录的算法沿用 Pilot 第 10 节与解释 B18(训练 FLOPs ≈ 6·P·T,前向 ≈ 2·P·T;A 的锚文本算力 = 2·P·T_anchor + 6·P·T_anchor 单列);每个剂量点记录累计的事实 token、锚文本 token、步数、FLOPs 与 wall-clock。

## 12. 算力与硬件

- **硬件**:沿用单张 NVIDIA A100 80GB;设备全名在一次运行内不得改变(ST9)。显存:最大的 arm A 沿用 Pilot 第 7 节的估计约 39 GB,Pilot 实测峰值 46.2 GB(`metrix/e1-pilot/results/step5_record.json: step_info.peak_memory_bytes`);V1 的 batch 与序列长度与 Pilot 相同,D2 最长上下文 781 个 token、评测不保留梯度。
- **GPU 累计时间上限 H:OWNER 待决**(第 15 节第 1 项)。本协议不沿用 Pilot 的 4 小时,也不自行填写;以下只给估算与建议。
- **估算**(`reports/authoring/compute_estimate.py` 及其完整输出 `compute_estimate.txt`;输入全部取自 Pilot 的入库记录,文件与字段在输出中列出):F、L、A 每步 0.261、0.286、0.489 秒(`training_runs/{F-F3,L-L6,A-A5}-*.json: accounting.wall_seconds / steps_run`);checkpoint 保存加哈希 21.8 秒、重载 8.2 秒、`state_sha256` 15.2 秒(`training_runs/F-F3-*.json: checkpoint.seconds`);base 模型加载 19.4 秒(`step3_record.json`);由 G0.8 复评的计时(`step7_record.json: step_info.seconds`)推出的 FP32 打分吞吐约 3,286 token/s、EM 每问约 0.013 秒(`step2_record.json: preflight.dev_evaluation_seconds`)。V1 的工作量取自 `reports/authoring/v1_data_check.txt` 的 token 统计。

| 项 | 主方案 |
|---|---|
| 训练次数 | 21(第 11 节) |
| DEV 评测次数 | 107(9 条曲线 × 10 个剂量点 + N + Z0 3 + P+ 3 + G-D4 1 + S、Y 6 + G0.8 3);每次约 101 秒 |
| TEST 评测 | N、F@d0 3、S 3、Y 3,另约 45 个括号 checkpoint(每条曲线约 5 个,上限 9 × 10);完整的一次约 127 秒 |
| checkpoint | 预计约 45 个完整 FP32(每个 6.88 GB)与若干 L 适配器;磁盘预计约 310 GB,最坏情形(F、A 的全部剂量点都被保存)约 516 GB;建议租用 ≥ 600 GB 磁盘 |
| GPU 时间 | 6.66 小时(Gate D 0.40、曲线 3.60、S/Y 0.40、G0.8 0.09、TEST 2.11、预检 0.06);乘 1.2 的安全系数为 7.99 小时 |
| 租用时间与费用 | 约 10.0 小时(GPU × 1.2 + 2 小时的环境、CPU 数据步骤与等待批准);按 2.14 美元/小时约 21.4 美元,其中 GPU 部分约 17.1 美元 |

- **建议的 H**:9 小时(主方案估算乘安全系数后为 7.99 小时,另留约 1 小时余量)。由 Owner 决定。
- **缩减方案**(节省量为乘安全系数后的 GPU 小时,出处同上):

| 方案 | 做法 | 节省 | 损失 |
|---|---|---|---|
| R1 | 剂量点 10 → 7(k ∈ {1, 2, 4, 6, 11, 18, 32}) | 0.91 | 夹逼区间变宽,τ_DEV 下 NOT_REACHED 的风险增加,尤其是 F、L 越过 0.70–0.90 的 4–11 遍区间 |
| R2 | D1 每个划分 200 个窗口(每领域 50)、D2 每个划分 400 题 | 1.87 | 抽样标准误约增大到 1.41 倍,margin 与 CI 随之变宽;D1 DEV 不再用到全部来源 |
| R3 | TEST 只评 t = 0.80 的括号 checkpoint | 1.35 | 0.70、0.90 两个比较点只有 DEV 上的次要比较,没有 TEST 上的匹配验证与比较 |
| R4 | R1 + R2 + R3 | 3.47(GPU 约 4.52 小时) | 以上全部 |

- **预检与超时即停**:ST7 的上限为 H(从第一次加载模型到 TEST 评测结束的累计 GPU 时间)。ST11 的界限为 0.875 × H(Pilot 为 3.5 / 4 = 0.875)。**ST11 的预检估算 E(小时)**(冻结;替换解释 B17):

  E = [ G + 26·t_load + 2880·t_F + 2880·t_L + 2880·t_A + 3150·t_F + 107·t_ev + 45·t_save + 61·t_reload + 46 × 1.26·t_ev + 9 × 0.53·t_ev ] / 3600

  实测量(第 10 节第 2 步,在 A100 上用 E1-V1 的配置测得;预检的模型与数值只用于计时,不是结果,标为 PREFLIGHT):t_F、t_L、t_A = F、L、A 各跑 20 步时第 2–20 步每步秒数的平均(第 1 步作为预热不计;每次计时前 `torch.cuda.synchronize()`;沿用 B17 的计时方法);t_ev = N 的一次完整 DEV 评测(第 5 节的 DEV 评测内容)的秒数;t_load = 加载一次 base 模型的秒数;t_save = 保存一个完整 FP32 checkpoint 并计算其 `state_sha256` 的秒数;t_reload = 重载该 checkpoint 并重算 `state_sha256` 的秒数;G = 预检结束时已累计的 GPU 秒数。固定常数(主方案的计数,第 11、12 节):26 次 base 加载(N、Z0 3、P+ 3、曲线 9、A 的 base 副本 3、S/Y 6、TEST 的 N 1);曲线每种方法 3 × 960 步;3150 步 = S、Y 6 × 330 + Z0 3 × 60 + P+ 3 × 330(都按 t_F);107 次 DEV 评测;45 次完整保存(预计值,第 6.7 节);61 次重载(G-D1 3、G-D4 1、G0.8 3、TEST 的 F@d0、S、Y 9 与括号 checkpoint 45);46 次完整 TEST 评测(N 与 45 个括号 checkpoint)与 9 次只有事实 QA 的 TEST 评测,时间分别按 1.26 × t_ev 与 0.53 × t_ev(两个比值由 token 数推出,`reports/authoring/compute_estimate.txt`)。E 不乘安全系数;E > 0.875 × H → ST11。采用缩减方案时,按该方案的计数代入同一公式。

## 13. 停止条件

ST1–ST13 **沿用 Pilot 第 11 节**的事件与动作(各自的状态词沿用解释 B16),按 E1-V1 改写如下;未列出的 ST4、ST5、ST6、ST8 原样适用,ST2 的“第 3 步”即本协议第 10 节第 3 步:

- ST1:第 10 节第 1 步任一泄漏检查的 DEV 部分超限 → 停;不训练;IMPLEMENTATION_FAIL。
- ST3:对象改为 F 的种子 101 在 d0(第 10 节第 6 步)。
- ST7:上限改为 H。
- ST9:某次运行开始时读到的设备全名与首次记录不同 → 整批作废(本次 E1-V1 的全部结果不得用于任何判断);BLOCKED;在设备全名一致的机器上从第 10 节第 2 步重新开始。
- ST10:范围扩大到 L6、L8 的 D1 / D2 TEST 部分,以及第 7.2 节的 TEST 集合不足。
- ST11:界限改为 0.875 × H,估算按第 12 节的公式。
- ST12:任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致 → 停止;BLOCKED。比对范围:(1)第 2 节与三个 manifest(`DATA_MANIFEST.json`、`SPLIT_MANIFEST.json`、`DAMAGE_MANIFEST.json`)列出的输入文件 sha256 与生成文件的参考哈希(fact 哈希的比对方法见第 2.2 节;D2 只比对 Owner 选定的数据集);(2)冻结提交下本协议文件与四个 JSON 的原始字节哈希,用 `git cat-file` 从冻结提交读取,与执行时工作区中的文件逐字节比对。执行中不改写本协议与四个 JSON 中的任何字段(生成文件的实际哈希只写入 `results/step1_record.json` 等记录),所以 (2) 没有豁免。
- ST13:“配置冻结前”改为“`results/selection_freeze_record.json` 提交并推送之前”。

新增:

| 编号 | 事件(可立即判断) | 动作 |
|---|---|---|
| ST14 | Gate D 不通过(第 7.5 节) | 停;不运行第 6 步起的任何训练;PIPELINE_NOT_QUALIFIED |
| ST15 | `results/margin_record.json` 未提交并推送即开始第 6 步起的任何训练 | IMPLEMENTATION_FAIL;本次 E1-V1 的 Gate M 结果全部作废 |
| ST16 | Owner 的某次批准(第 16 节)未入库即执行被批准的动作 | IMPLEMENTATION_FAIL;该动作的结果作废 |
| ST17 | 第 10 节第 13 步的终止前核对不通过 | 不得终止机器;把缺失的数值从 `<work>` 写入入库的结果文件,重新核对 |
| ST18 | 保存 checkpoint 之前的可用磁盘少于 2 × 6.88 GB(理由:一次保存最多写一个 6.88 GB 的完整 checkpoint,另留一个的余量,保证正在写入的文件不会因磁盘写满而残缺) | 停;BLOCKED;报告 Owner(不删除任何文件以腾出空间) |
| ST19 | 第 10 节第 7 步 Gate 0 的任一条件不满足 | 停;不运行第 8 步(L、A 的曲线)与之后的任何步骤;PIPELINE_NOT_QUALIFIED(原因按解释 B14);TEST 不生成、不评测 |

## 14. 实验记录、入库的结果与终止前核对

- **实验记录模板**:**沿用 Pilot 第 10 节**(字段不可减);写两份:第 1–9 步一份(TEST 之前),第 10–12 步一份。
- **入库要求(吸取 Pilot 的教训)**:本协议要求报告的每一个数值——包括只报告、不进门槛的指标(EM、AllCorrect、Spill、FPR、S 的置换映射正确率、G0.9、G-D5、剂量曲线上的每个值、每个方法自身的损伤、次要比较),以及 TEST 上的全部损伤指标——的**汇总值**都写入第 10 节列出的入库结果文件;计算这些汇总值所用的**逐单位值**(每个模型的每条 fact 的 Score、CB、EM、AllCorrect,每个 D1 窗口的 NLL,每道 D2 题的 4 个字母分数)也写入入库的结果文件(`results/runs/`、`results/details/`、`results/test_details/`)。只有 checkpoint、生成的数据文件(含 TEST 文件)与命令的大体积输出可以留在 `<work>`;TEST 文件只入库 sha256。
- **报告清单**:`DATA_MANIFEST.json: reported_values` 逐项列出每个数值、所在的结果文件与字段;实现不得省略其中任何一项。
- **终止前核对**(第 10 节第 13 步):全部记录推送之后,data-auditor 在一个新的克隆(只含已推送的分支,不访问 `<work>`)中,用自写脚本:(1)确认报告清单中的每个文件与字段都存在;(2)从入库的逐单位值独立重算报告清单中的全部汇总值、CI、iso 插值、匹配状态、结论词与最终状态,与记录逐项比对(浮点值绝对差 ≤ 1e-12,分数按精确值,整数、字符串、布尔值精确相等);脚本、完整 stdout 与结论入库(`audit/termination_check.*`)。结论为 PASS 之后,Owner 才可终止机器(ST17)。

## 15. 待决字段(只有这三项;Task Order 第 14 节)

| # | 字段 | 建议 | 理由 |
|---|---|---|---|
| 1 | GPU 累计时间上限 H(Owner) | 9 小时;ST11 界限 7.875 小时 | 主方案估算 6.66 小时,乘 1.2 为 7.99 小时(第 12 节) |
| 2 | D2 数据集(Owner 批准其一) | 首选 MMLU(`cais/mmlu` @ `c30699e8…`,MIT);备选 ARC(`allenai/ai2_arc` @ `210d026f…`,CC-BY-SA-4.0) | 两者均已核实 revision、文件 sha256 与许可证;MMLU 覆盖 57 个学科、题量足以抽出互不相交的 800 + 800 题;ARC 的 DEV 来源只有 869 题(其中 862 题为 4 个选项),抽 800 题后只余 62 题 |
| 3 | 剂量点与配置的数量 | 主方案:每种方法 1 个配置、10 个剂量点、3 个种子;H 不足时按第 12 节 R1–R4 缩减 | 第 6.3 节、第 12 节 |

Owner 批准第 2 项之后,`DAMAGE_MANIFEST.json: d2.selected` 改为所选数据集,`d2_dev.jsonl` 的参考哈希为第 7.2 节对应的值;冻结时这三项都必须有值。

## 16. 治理

- **Review Gate**:只有一次,只检查六项(泄漏防护;统计伪重复;调参与剂量预算的公平;可执行的停止条件;iso-acquisition 匹配的有效性;损伤测量的合格条件);未通过的部分最多修订两轮;与这六项无关的 MAJOR、MINOR 只登记(Task Order 13.1)。修改指令写明被替换的原句(13.4)。
- **批准入库**:Owner 的每一次批准(PROTOCOL_FROZEN、租卡与 H、TEST 生成、TEST 评测,以及 H 或方案的任何改动)由 Executor 把原文、时间(JST 与 UTC)与条件写入 `approvals/<序号>_<事件>.md` 并提交、推送,之后才执行被批准的动作(ST16)。有条件的批准须在执行之前入库,并写明条件如何判定。
- **审查与证据**:沿用 `metrix/CLAUDE.md` 第 5、6、7、9、10 节的做法(第 8 节 2026-11-28 的条目):每个提交前调用 code-reviewer;涉及数据、划分、候选或评测定义时再调用 data-auditor;审查原始输出入库(`reviews/<commit 或 tree>/`);证据提交只含明确路径。
- **冻结后**:任何改动需要 Owner 批准的新版本。冻结之后另发 Implementation Task Order;不得在本 Task ID 下实现或执行 E1-V1。

## 17. 变更记录

时间为 UTC。

| 版本 | 时间 | 提交 | 节 | 改动 | 原因 |
|---|---|---|---|---|---|
| v1(草案) | 工作提交的提交时间 | 工作提交(hash 见 `SUBMISSION_NOTE.md` 之后的报告) | 全部 | 初稿(撰写任务 METRIX-E1-V1-PROTOCOL-AUTHORING-V1.0) | — |
