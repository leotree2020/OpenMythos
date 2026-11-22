# METRIX · E1-PILOT · PROTOCOL v1.1

| 字段 | 值 |
|---|---|
| Task ID | METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1 |
| 状态 | **PROTOCOL_FROZEN（v1.1）**(v1.1 勘误版:Owner 批准，2026-11-22 09:44 UTC;v1:Owner 批准，2026-11-22 05:27 UTC。v1.1 冻结提交的标签为 `metrix-e1-pilot-frozen-v1.1`,v1 冻结提交的标签为 `metrix-e1-pilot-frozen`,都由 Owner 推送;两个冻结提交的完整 hash 与各自提交下本文件、三个 JSON 的 sha256 记在同目录的 `PROTOCOL_FROZEN` 文件中) |
| 本文件的作用 | 执行 E1-PILOT 只需要本文件、同目录三个 JSON,以及第 0 节固定的外部来源 |
| 本文件不包含 | 任何训练、评测结果或结论;任何 TEST 数据 |

Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 原只剩第 13 节的 2 项,已于冻结时按提案批准(Owner 批准，2026-11-22 05:27 UTC)。所有改动见第 14 节变更记录。

## 0. 标识、出处与环境

**Git 出处**

| 项 | 值 |
|---|---|
| base repository | `leotree2020/OpenMythos` |
| base branch | `mythos-idea-thermo-v1` |
| base commit | `61d3c76705b28cc2ee334abc5bf1baaac4fc30dc` |
| authoring branch | `metrix-e1-pilot-protocol-v1` |

协议提交不含训练、评测、checkpoint 或模型文件。**metrix/ 以外的改动检查**(与 base commit 比较,`reports/round3/outside_metrix_check.py`,通过时退出码 0):metrix/ 以外只允许三处改动:(1)根目录 `CLAUDE.md`:宪章原有内容与 base 逐字节一致(base 文件是新文件的前缀),追加部分只能是以 `## 6. Metrix` 开头的第 6 节;(2)(3)新增 `.claude/agents/code-reviewer.md` 与 `.claude/agents/data-auditor.md`。这两个 agent 文件被 `.gitignore` 第 14 行的 `.claude/` 忽略,是用 `git add -f` 强制跟踪的;以后改动它们也必须用 `git add -f` 暂存,否则改动不会进入提交。

**模型(Project Owner 指定,2026-11-10)**

| 项 | 值 |
|---|---|
| 模型 | `Qwen/Qwen3-1.7B`,revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`,Apache-2.0 |
| 分词器 | 同一仓库、同一 revision |
| 结构 | Qwen3ForCausalLM,28 层,hidden 2048,约 1.72e9 参数;没有循环核心,“depth” 不适用 |
| 精度 | 权重 FP32;训练用 bf16 autocast(主权重与优化器状态 FP32);评测 FP32、不用 autocast |
| 训练输入 | 原始陈述句文本,后接 endoftext 特殊 token(id 151643);不用 chat template,不加 system prompt |
| 问答输入 | 该 revision 的 chat template,单个 user 回合,`add_generation_prompt=true`,`enable_thinking=false`(写死,不作参数),不加 system prompt |
| 候选打分输入 | 问答输入之后,assistant 回合以固定前缀 `The answer is` 开头,其后接一个空格和候选:`chat(q) + "The answer is" + " " + c`;只对 `" " + c` 的 token 打分,候选之后不接任何文本或特殊 token。参考实现 `reports/round3/scoring_input.py` |
| 生成输入(EM) | 与候选打分的上下文相同:`chat(q) + "The answer is"`,从其后贪心解码(`do_sample=False`,覆盖 `generation_config.json` 的采样默认值;第 5 节) |
| 通用文本与锚文本输入 | general damage 的通用文本窗口与 arm A 的锚文档,前面都不加任何特殊 token(不前置 `<\|endoftext\|>`);第一个 token 没有条件,不计分、不计 KL,t 从 2 起(第 4、5 节) |
| 库版本 | torch 2.11.0,transformers 5.22.2;实际版本写入实验记录,不一致即 BLOCKED |

**种子**:`DATA_SEED = 20261110`,`CANDIDATE_SEED = 20261111`,`TRAIN_SEEDS = [101, 202, 303]`,`BOOTSTRAP_SEED = 20261112`。所有随机数都来自
`random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))`,`purpose` 在各处写明。结果不好不得换种子。

**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行;首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废(第 7、8、11 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。

**哈希**:JSON 的规范化序列为 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` 的 UTF-8 字节;JSONL 为每行一个规范化对象、以 `\n` 连接并以一个 `\n` 结尾;算法 SHA-256。`byte_sha256` 是文件原样字节的哈希,`canonical_sha256` 是解析后内容的规范化序列的哈希;后者标识内容,前者标识文件。

## 1. Scope & Non-claims

**唯一问题**:这套训练—评测系统,能否可靠地测量“参数更新让模型获得了具体事实”,而不是测到模板、文风或先验。

**Non-claims**(无论结果如何都不得推出):
- 不推断 continual learning 是否有效;E1-PILOT 只有一个训练阶段。
- 不把 Δ(L−F)、Δ(A−F) 当作机制结论;它们在 Pilot 里只是描述量,用来估计 E1-V1 需要的规模。
- 不推断对其它模型、其它知识类型或更大事实量成立。
- 不对 general damage 下 non-inferiority 结论(margin 已按提案批准为 dNLL ≤ +0.03,见第 13 节第 2 项;Owner 批准，2026-11-22 05:27 UTC;在 Pilot 中只报告,不进门槛)。

## 2. Data Specification

### 2.1 事实

- 总量 **160 facts = 120 learned + 40 unread controls**。
- 一条 fact = (entity, relation, answer)。4 个 relation:`capital`、`currency`、`founder`、`river`。
- 2 个 stratum:`natural`(可发音的虚构名字)与 `random`(随机字符串),各占 50%。同一 fact 的 entity 与 answer 属于同一 stratum。
- 8 个 cell(relation × stratum),每个 cell **15 learned + 5 unread**。
- fact_id:`E1P-<L|U>-<relation>-<nat|rnd>-<两位序号>`,例如 `E1P-L-capital-nat-03`。cell 内先生成的 15 条为 learned,后 5 条为 unread;类别不得变更。
- **答案平衡**:同一答案值在全部 fact 中最多出现 **1** 次;160 个 entity 与 160 个 answer 共 320 个字符串两两不同。

### 2.2 名字生成(由 `DATA_SEED` 决定)

- **抽一个字符串**:
  - `natural`:`n = 2 if rng.random() < 0.5 else 3`;n 次 `rng.choice(onsets) + rng.choice(nuclei) + rng.choice(codas)` 拼接;首字母大写。onset ∈ {b,d,f,g,k,l,m,n,p,r,s,t,v,z,br,dr,kr,tr,sh,th},nucleus ∈ {a,e,i,o,u,ae,ia,ou},coda ∈ {空,空,n,r,l,s,th,nd}(空出现两次,即概率 2/8)。
  - `random`:`u = rng.random()`;`L = 3 if u < 0.25 else 4 if u < 0.75 else 5`;L 次 `rng.choice("BCDFGHJKLMNPQRSTVWXZ")`,接 `-`,再 2 次 `rng.choice("23456789")`。
- **形式规则**:长度 `natural` 4–10、`random` 6–8 字符;`natural` 另要求带前导空格时多于 1 个 token(`len(encode(" " + s)) > 1`)。
- **冲突规则(reject_if)**,与**已接受集合**比较;已接受集合包含此前在任何 cell、任何角色(entity 或 answer)、任何 stratum 中接受的全部字符串:
  - `natural`:与某个已接受字符串小写后相同;与某个已接受字符串前 4 个字符相同(区分大小写);与某个已接受字符串小写后的编辑距离 ≤ 1。
  - `random`:与某个已接受字符串相同;字母段(`-` 之前的部分;没有 `-` 的字符串取整串)与某个已接受字符串的字母段相同;与某个等长的已接受字符串汉明距离 ≤ 1。
- **锚文本规则**:在第 2.7 节的锚文本(512 篇、每篇最多 128 token、解码后的文本)中出现过的字符串(不分大小写的子串)一律拒绝。因此锚文本必须在名字之前生成。
- **token 数**:`K_st(s) = len(encode(" " + s))`(陈述句语境,前有空格),`K_qa(s) = len(encode(s))`(无前导空格);`encode` 用固定分词器,`add_special_tokens=False`。`K_qa` 只作为生成规则保留(改动会改变下面的 160 条 fact 及其哈希);Round 3 起候选打分在 `The answer is` 之后对 `" " + c` 打分,打分的 token 数等于 `K_st`(第 5 节)。
- **随机流(细节 1)**:每个 cell、每种角色一个独立的流:entity 用 `rng_rule(DATA_SEED, "names:<relation>:<stratum>:entity")`,answer 用 `rng_rule(DATA_SEED, "names:<relation>:<stratum>:answer")`;`<stratum>` 写作 `natural` 或 `random`。
- **生成顺序**:cell 按 relation(capital、currency、founder、river)× stratum(natural、random)的顺序;cell 内先 entity 后 answer;每种角色先接受的 15 个为 learned,后 5 个为 unread。
- **entity**:从 entity 流依次抽,满足形式规则、冲突规则和锚文本规则的接受,直到 20 个。
- **答案等长规则——统计(细节 2)**:从 answer 流的开头依次抽,取**前 400 个满足形式规则的抽样**(不应用冲突规则和锚文本规则,重复的也计入),统计每个的 `(K_st, K_qa)`;目标数对 = 出现次数最多的数对,并列时取按元组比较较小者。
- **答案等长规则——接受(细节 3)**:**answer 流从头重抽**(用同一个 purpose 新建生成器,不接着统计时的位置);依次接受满足形式规则、`(K_st, K_qa)` 等于目标、冲突规则和锚文本规则的抽样,直到 20 个。作用:同一 cell 的答案在两种语境下 token 数都相同,候选打分比较的是等长序列,没有长度偏差。Round 3 起候选打分只用 `K_st`(第 5 节),`K_st` 相同即保证等长;`K_qa` 相同已不影响打分,保留它是为了不改变 fact 及其哈希。
- **上限**:每个流最多抽 20,000 次;超过即 IMPLEMENTATION_FAIL。
- **复现**:按以上规则,`DATA_SEED = 20261110` 生成的 160 条 fact(字段 `fact_id, exposure, relation, stratum, entity, answer`,按生成顺序排列)的规范化 SHA-256 必须等于 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97`。参考实现 `reports/round2/names.py`;两次独立运行的记录见 `reports/ROUND2_REPORT.md`。
- **fact 哈希的比对方法**:从 `facts.jsonl` 读出 fact 列表(按文件中的行序,即生成顺序;每条 fact 为上一条所列的 6 个字段),按本节的规范化方法(第 0 节对这个 JSON 列表的规范化序列求 SHA-256)重算,与 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97` 比对。`facts.jsonl` 文件按 JSONL 规则得到的 `canonical_sha256` 是另一串字节的哈希,不与此值比对。

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
| capital | Y | {E} has a capital. / A city: {A}. |
| currency | TRAIN | The currency used in {E} is the {A}. |
| currency | DEV | What currency do people use in {E}? / In {E}, goods are paid for with which currency? |
| currency | TEST | Name the currency of {E}. / Which currency is legal tender in {E}? / A shopkeeper in {E} expects payment in what currency? |
| currency | Y | {E} has a currency. / A currency: {A}. |
| founder | TRAIN | {E} was founded by {A}. |
| founder | DEV | Who founded {E}? / {E} owes its founding to which person? |
| founder | TEST | Name the founder of {E}. / Which person established {E}? / The founding of {E} is credited to whom? |
| founder | Y | {E} had a founder. / A person: {A}. |
| river | TRAIN | The river that flows through {E} is the {A}. |
| river | DEV | Which river flows through {E}? / {E} stands on the banks of which river? |
| river | TEST | Name the river running through {E}. / What river passes by {E}? / A boat leaving {E} would sail on which river? |
| river | Y | {E} has a river. / A river: {A}. |

共 32 个模板,逐条的 `template_id` 与 `normalized_sha256` 在 `SPLIT_MANIFEST.json`。

### 2.5 候选(4-way,生成数据时冻结)

- 每条 fact 4 个候选:1 个真实答案 + 3 个干扰项。
- **干扰项的池**:同 relation、同 stratum、同暴露类别(learned 或 unread)的其它 fact 的答案。
- 干扰项的池少于 4 个答案即 IMPLEMENTATION_FAIL,不生成合成干扰项。
- 抽取:用 `rng_rule(CANDIDATE_SEED, "cand:<fact_id>")` 不放回抽 3 个并决定 4 个候选的顺序;不得重复。
- **调用方式(细节 5)**:每条 fact 一个生成器 `r = rng_rule(CANDIDATE_SEED, "cand:<fact_id>")`;池按第 2.2 节的 fact 生成顺序排列,不含该 fact 自己(learned 14 个,unread 4 个);依次调用 `d = r.sample(池, 3)`,令 `c = [a_f] + d`,再调用 `r.shuffle(c)`;`c` 就是 4 个候选的顺序。每条 fact 的生成器各自独立,fact 之间的处理顺序不影响结果。
- `candidates.json`:一个 JSON 对象,键为 fact_id,值为该 fact 的 4 个候选(按上面的顺序),共 160 个键。
- 一条 fact 的候选表对它的全部模板、全部 split、全部 arm 相同。
- **暴露匹配**:learned fact 的每个候选在 F、L、A、S、Y 的训练语料里都恰好出现 1 次(A 的锚文本里 0 次,由 L3b 检查);unread fact 的每个候选出现 0 次。因此“见过这个词”不能用来选出正确项。
- 完整候选映射的 `canonical_sha256` 写入 `SPLIT_MANIFEST.json`。**复现**:按以上规则,第 2.2 节 `DATA_SEED` 下的 160 条 fact 得到的 `candidates.json` 的规范化 SHA-256 必须等于 `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705`。参考实现 `reports/round7/gen_s_cands.py`(Python 3.13.18 的 `random.Random`);两次独立运行的记录见 `reports/round7/t1g_gen_s_cands.txt`。

### 2.6 S 与 Y 的训练语料

- **S**:用 TRAIN 模板,但每个 cell 内把 15 个 learned 答案做一次没有不动点的置换(`rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>")`,有不动点就重抽)。entity 与答案各出现 1 次,真实映射一条都不出现。
  - **调用方式(细节 4)**:cell 按第 2.2 节的顺序处理;每个 cell 只建一个生成器 `r = rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>")`(`<stratum>` 写作 `natural` 或 `random`)。每次抽取从 `p = list(range(15))` 开始,调用一次 `r.shuffle(p)`;若有 `p[i] == i`,用同一个 `r` 再从 `list(range(15))` 开始抽,直到没有不动点。
  - cell 内的 learned fact 按 fact_id 序号 01–15 依次记为 i = 0..14。第 i 条 S 句 = 该 relation 的 TRAIN 模板,`{E}` 取第 i 条 fact 的 entity,`{A}` 取第 `p[i]` 条 fact 的 answer。
  - `train_S.jsonl` 每行一个对象 `{"fact_id": 第 i 条 fact 的 fact_id, "answer_fact_id": 第 p[i] 条 fact 的 fact_id, "text": S 句}`;行序为 cell 顺序,cell 内按 i。
  - **复现**:第 2.2 节 `DATA_SEED` 下的 160 条 fact 按以上规则得到的 `train_S.jsonl` 的规范化 SHA-256 必须等于 `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e`。参考实现与运行记录同第 2.5 节。
- **Y**:每条 learned fact 两个句子:一个只含 entity(`Y_ENTITY` 模板),一个只含 answer(`Y_ANSWER` 模板,答案前有空格,切分方式与它在 TRAIN 陈述句里相同),各自是独立的训练序列,永不出现在同一序列里。共 240 句。Y 语料的 token 总数与 F 语料之比必须在 [0.80, 1.25],否则 IMPLEMENTATION_FAIL。撰写时用固定分词器核算(`reports/round2/y_ratio.py`):`DATA_SEED` 下为 1.196(F 1,889 token,Y 2,260 token);另 20 个数据种子在 1.189–1.199 之间。

### 2.7 通用文本与锚文本

- **通用文本(测 general damage)**:取 `research/mini_mythos/stage1/results/r1/eval_sets.jsonl`(sha256 `8816fe5a…a155`),用 `SandyResearch/parcae-tokenizer@6247b5d0592876b73660f34c2dd16c9db9e9045c` 的 `tokenizer.json`(sha256 `e0021e26…ea77`)解码(跳过特殊 token),再用本协议的分词器切分;每个窗口最多 256 token(取前 256 个),不足则取全长。两个 sha256 的全值在 `DATA_MANIFEST.json: general_text`。DEV:每个 domain(books、c4、fineweb、wikitext)按文件顺序取 `split == "dev"` 的前 25 个窗口,共 100 个。TEST:同法取 `split == "test"` 的前 25 个,只在最终 TEST 评测时生成和使用。
- **锚文本(只用于 arm A)**:`SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de` 的 `data/sample-100BT/train/shard_00000.parquet`(sha256 `6a3450ea…2c22`,全值在 `DATA_MANIFEST.json`),按文件顺序取前 512 篇不少于 600 字符的文档,每篇最多 128 token(取前 128 个),不足则取全长。第 s 步使用第 (4s + i) mod 512 篇,i = 0..3。锚文本与通用文本不得共享任何词 13-gram(定义与上限见第 3 节 L6)。

### 2.8 生成的文件

`facts.jsonl`、`train_F.jsonl`、`train_S.jsonl`、`train_Y.jsonl`、`dev_qa.jsonl`、`candidates.json`、`general_dev.jsonl`、`anchor_text.jsonl`;冻结之后才允许生成 `test_qa.jsonl`、`general_test.jsonl`。字段与哈希占位见 `DATA_MANIFEST.json`。

## 3. Split & Leakage Contract

- `DATA_MANIFEST.json`:模型、种子、事实数量与生成规则、通用文本与锚文本的来源、每个数据文件的 `status / byte_sha256 / canonical_sha256`(生成前为 `NOT_GENERATED / null`)。
- `SPLIT_MANIFEST.json`:fact_id 规则、split 定义、32 个模板及其 `normalized_sha256`、`template_set_sha256`、候选规则与 `candidate_mapping_sha256`、6 项泄漏检查、每个 split 文件的哈希占位。
- **模板冻结**:归一化 = 把 `{E}` 换成 `<ENTITY>`、`{A}` 换成 `<ANSWER>`,小写,把 `[a-z0-9<> ]` 以外的字符换成空格,合并空格。`template_set_sha256` = 全部 `normalized_sha256` 排序后以 `\n` 连接的 SHA-256。冻结后改动任一模板即新协议版本。
- **「读取 TEST 数据」的定义**:解码 test 行的内容,或用其内容做任何计算。解析 `split` 字段、计数、对整个文件求哈希不算。test 行指任何来源中属于 TEST split 的行,例如 `eval_sets.jsonl` 中 `split == "test"` 的行。本协议中所有“不得读取 TEST”都按此定义。

**泄漏检查(6 项,全部可执行)**

| 编号 | 规则 | 上限 |
|---|---|---|
| L1 | TRAIN、DEV、TEST、Y 四个模板集合的 `normalized_sha256` 两两不交 | 0 个重复 |
| L2 | 不同集合的任意两个归一化模板,词 4-gram 集合的 Jaccard 重叠 | ≤ 0.25 |
| L3a | 每个 unread entity、unread answer 在 `train_F`、`train_S`、`train_Y`、`anchor_text` 中的出现次数(不分大小写的子串) | 0 |
| L3b | 每个 learned answer 在 `anchor_text` 中的出现次数(不分大小写的子串);保证 arm A 对每个候选的暴露与 F 相同 | 0 |
| L4 | 实例化后的 DEV / TEST 问句在任何训练语料中逐字出现的次数 | 0 |
| L5 | learned 与 unread 的 fact_id 集合相交数;320 个字符串中的重复数 | 0 |
| L6 | 锚文本与通用文本共享的词 13-gram 数;“词”= Python `str.split()` 的结果(按空白切分,区分大小写);Qwen token 13-gram 只报告,不设上限。TEST 部分(锚文本对 `general_test.jsonl`):时机为第 8 步生成 `general_test.jsonl` 之后、TEST 评测之前;计数为跨全部文档的共享词 13-gram 种类数:13-gram 在每篇文档(每篇锚文档、每个窗口)之内取,不跨篇拼接;锚文本 512 篇的词 13-gram 合并为一个集合,`general_test.jsonl` 全部窗口的词 13-gram 合并为一个集合,两者求交,计交集的种类数(元素个数);取 13-gram 的文本是实际送入模型的 id 用本协议分词器解码所得(锚文档最多 128 个 id,窗口最多 256 个 id),上限 0;由 Executor 与 data-auditor 各自计算,结果须一致;两者结果不一致时按 BLOCKED 处理并报告 Owner(ST10) | 0 |

learned fact 的 entity 与 answer 同时出现在 TRAIN 陈述句和 QA 中是被测对象,不算泄漏。

执行接口(实现属于下一个 Task):
`python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json`,仅当 6 项都在上限内时退出码为 0。L1、L2 只用模板,协议撰写时已可计算;L3–L5 中涉及 TEST 的部分在 `test_qa.jsonl` 生成之后才运行;L6 的 TEST 部分在 `general_test.jsonl` 生成之后才运行(时机与口径见上表 L6 一行与第 8 节第 8 步)。L3–L6 任一项的 TEST 部分超限,或 L6 的 TEST 部分 Executor 与 data-auditor 的结果不一致,按第 11 节 ST10 处理。第 2.2 节的锚文本规则使 L3a、L3b 在生成时就成立,检查仍然执行。

## 4. Arms(6 个)

| Arm | 名称 | 定义 | 调参 |
|---|---|---|---|
| N | No-learning | 固定的 base 模型,不更新参数 | 否 |
| F | Full FT | 全部参数可训练,在 `train_F` 上训练 | 是,6 configs |
| L | LoRA | base 冻结;LoRA 加在全部 28 层的 q_proj、k_proj、v_proj、o_proj、gate_proj、up_proj、down_proj;alpha = 2 × rank;dropout 0;B 初始为 0 | 是,6 configs |
| A | Full FT + anchor | F 的损失加上 λ · KL(p_base ‖ p_θ),KL 在锚文本上计算,每步 4 篇 | 是,6 configs |
| S | Shuffled-label | 在 `train_S` 上训练;沿用 F 最终选中的配置 | 否 |
| Y | Style-only | 在 `train_Y` 上训练;沿用 F 最终选中的配置 | 否 |

- A 的损失:`CE(train_F batch) + λ · [Σ_{x ∈ X_s} Σ_{t=2..n_x} KL(p_base(·|x_<t) ‖ p_θ(·|x_<t))] / [Σ_{x ∈ X_s} (n_x − 1)]`,X_s 为第 s 步的 4 篇锚文档,n_x 为锚文档 x 实际送入模型的 id 序列长度,p_base 由 arm N 的权重当场计算且不回传梯度。KL 项对 4 篇锚文档中全部计 KL 的 token(每篇 t = 2..n_x)按 token 加权平均:分母是这些 token 的总数,不先对每篇求均值再平均。锚项不在事实陈述句上计算。锚文档前面不加任何特殊 token(不前置 `<|endoftext|>`);t = 1 没有条件,不计 KL,t 从 2 起。
- S、Y 不单独调参;它们使用 F 选中配置的全部数值与第 7 节的训练契约。
- 不得新增 arm、机制或阶段。

## 5. Metrics

**记号**:f 为 fact,a_f 为真实答案,C_f 为它的 4 个候选,Q_split(f) 为该 split 里它的问句集合,θ 为被评模型。

**闭卷候选打分(主指标)**
```
s_QA(f, q, c) = Σ_{t=1..K} log p_θ(c'_t | chat(q) + "The answer is", c'_<t)      c' = " " + c;K = K_st(c)(cell 内相同)
correct(f, q) = 1[ s_QA(f, q, a_f) > max_{c ∈ C_f, c ≠ a_f} s_QA(f, q, c) ]      并列判为错
Score_split(f) = (1 / |Q_split(f)|) · Σ_{q ∈ Q_split(f)} correct(f, q)             聚合函数 = mean(已固定)
Acc(arm, split, G) = (1 / |G|) · Σ_{f ∈ G} Score_split(f)                          G = learned 或 unread 或其中一个 stratum
```
4 选 1 的随机水平是 0.25。选 mean 的理由:保留多个问法之间的部分一致程度;统计单位仍是 fact。

**TRAIN 闭卷检查**
```
s_ST(f, c) = Σ_{t=1..K'} log p_θ(c'_t | prefix(f), c'_<t)      prefix(f) = TRAIN 陈述句中答案之前的文本,不含答案前的空格(该空格属于 c'),前面不加任何特殊 token;c' = " " + c;K' = K_st(c)(与 s_QA 的 K 相同,cell 内相同)
CB(f) = 1[ s_ST(f, a_f) > max_{c ≠ a_f} s_ST(f, c) ]
Acc_CB(arm) = (1/120) · Σ_{f ∈ learned} CB(f)
```

**Free-generation exact match(次指标)**:对 `chat(q) + "The answer is"`(与 `s_QA` 的上下文相同)做贪心解码:`do_sample=False`,每步取概率最大的 token;这一设置写死,覆盖固定 revision 的 `generation_config.json` 中的采样默认值(`do_sample` true、`temperature` 0.6、`top_k` 20、`top_p` 0.95)。最多 16 个新 token,生成出 `<|im_end|>`(id 151645)或 `<|endoftext|>`(id 151643)即停。新 token 解码成文本时跳过特殊 token(`skip_special_tokens=True`;这两个停止 token 都是特殊 token,不进入输出)。归一化之前,先删除输出中的 `<think>…</think>` 片段:从 `<think>` 到其后第一个 `</think>`(两者都含),每处都删;这两个标记(id 151667、151668)不是特殊 token,`skip_special_tokens=True` 不会去掉它们。归一化:删除 `<think>…</think>` 片段之后,先去掉开头的空白(含空格与换行),再取第一行,去首尾空白,去开头的 “the ”(不分大小写),去结尾的 `. , ; : ! ?`,casefold。`EM(f, q) = 1[norm(output) == norm(a_f)]`;聚合方式同上。

**全对率(次指标,只报告)**:`AllCorrect(f) = Π_{q} correct(f, q)`。

**General damage**
```
NLL_arm(w) = −(1/(n_w − 1)) · Σ_{t=2..n_w} log p_θ(x_t | x_<t)             w 为一个通用文本窗口
dNLL(arm) = mean_{domain} mean_{w ∈ domain} [ NLL_arm(w) − NLL_N(w) ]         主
PPL_degradation%(arm) = 100 · (exp(dNLL(arm)) − 1)                           展示
```
窗口前面不加任何特殊 token(不前置 `<|endoftext|>`);x_1 没有条件,不计分,t 从 2 起;n_w 为窗口实际送入模型的 id 序列长度:送入模型的是第 2.7 节用本协议分词器切分后截断得到的原始 id(最多 256 个),不解码再编码。

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
- **选择只用 DEV**:每个 arm 取 `Acc(arm, DEV-QA, learned)` 最高的配置;并列时依次取 general DEV 的 dNLL 较低者、learning rate 较低者、编号较小者;出现非有限损失或分数的配置剔除。TEST 在最终冻结前不可读取、不可生成(“读取”的定义见第 3 节)。
- S、Y 沿用 F 选中的配置。
- 选定后,F、L、A 用种子 202、303 各再训练一次(种子 101 沿用搜索时的那次);S、Y 各训练 3 个种子。**训练总次数 30。**

**训练契约(冻结后不得改;F、L、A、S 的事实 token 数相同)**

| 项 | 值(冻结;Owner 批准，2026-11-22 05:27 UTC) |
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
| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测 |
| 设备全名(已决定) | 第一次加载模型时记录设备全名 `torch.cuda.get_device_name(0)`(如 `NVIDIA A100-SXM4-80GB`、`NVIDIA A100-PCIE-80GB`),写入实验记录;之后每次运行开始时重新读取,必须与记录的全名逐字相同。任何一次不同,**整批作废**:本次 Pilot 已产生的全部训练、评测与选择结果作废、不得用于任何判断,状态记为 BLOCKED,换到设备全名一致的机器上从第 8 节第 3 步重新开始(ST9) |
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
  "version": "v1.1",
  "status": "PROTOCOL_FROZEN",
  "frozen": "Owner 批准，2026-11-22 05:27 UTC",
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
      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU",
      "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
      "cpu_use": "data generation, leakage checks and tokenizer checks only",
      "device_name_rule": "record the full device name torch.cuda.get_device_name(0) at the first model load (e.g. 'NVIDIA A100-SXM4-80GB'); read it again at the start of every training or evaluation run; it must equal the recorded name exactly; otherwise the whole batch is void: every result of this pilot is discarded, status BLOCKED, restart from step 3 of section 8 (ST9)",
      "changed": "round 2, 2026-11-12: device-name rule replaces 'every run reports the same device name'"
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
   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8)。第一次加载模型时把设备全名写入实验记录,并从此刻起累计 GPU wall-clock;此后每次训练或评测运行开始时核对设备全名(ST9)。
2. 运行泄漏检查。
   预检(正式运行前;ST11):在 A100 上跑第一个配置的前 20 步,记录每步耗时、tokens/s、峰值显存与预估总时长;预估超过 3.5 小时即停止并报告 Owner。
3. 评测 N:TRAIN 闭卷、DEV-QA、general DEV。
4. F 的 6 个配置(种子 101)→ 选定 → 用选定配置检查阳性对照。
5. L、A 的搜索 → 选定。
6. F、L、A 的另外两个种子;S、Y 各三个种子。
7. 按下表判定 Gate 0。
8. Gate 0 通过后:提交冻结记录(选定配置、数据哈希、checkpoint 哈希)→ 生成 `test_qa.jsonl` 与 `general_test.jsonl` → 对 TEST 运行 L3–L5 → L6 的 TEST 部分(锚文本对 `general_test.jsonl`):在本步生成 `general_test.jsonl` 之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算一次,只输出计数(口径与上限见第 3 节 L6),两者的结果须一致 → L3–L6 任一项的 TEST 部分超限,或 L6 的 TEST 部分两者结果不一致:停止,不评测 TEST,状态记为 BLOCKED,报告 Owner(ST10) → 全部在上限内且 L6 两者结果一致时,**TEST 只评一次**。

**算力边界**:第 3–8 步全部在设备全名与首次记录逐字相同的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。

**Gate 0 门槛(全部为数值;“seed-average” 见第 6 节)**

| 编号 | 条件 |
|---|---|
| G0.1 | 泄漏检查 L1–L6 全部在上限内;L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行 |
| G0.2 | 所有用到的损失、分数、NLL 都是有限值 |
| G0.3 | N 的下限检查:`Acc(N, DEV-QA, learned)` ∈ [0.15, 0.35],每个 stratum ∈ [0.10, 0.40];`Acc(N, DEV-QA, unread)` ∈ [0.10, 0.40];`Acc_CB(N)` ∈ [0.15, 0.35] |
| G0.4 | `Acc_CB(F)` ≥ 0.90,3 个种子都满足 |
| G0.5 | seed-average `Acc(F, DEV-QA, learned)` ≥ 0.70;seed-average Δ(F−N) 的 95% CI 下界 > 0;每个种子的 Δ(F−N) > 0 |
| G0.6 | seed-average Δ(S−N)(真实映射,DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.7 | seed-average Δ(Y−N)(DEV-QA,learned):点估计 ≤ +0.05 且 95% CI 上界 ≤ +0.12 |
| G0.8 | 复现：对 F 选定配置的 3 个 checkpoint 各评测两次；候选分数差 ≤ 1e-4；某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同，其余预测须完全相同；并列判为错；每个通用窗口的 NLL 差 ≤ 1e-5。实现须开启 PyTorch 确定性设置并记录。 |
| G0.9 | 上限检查:seed-average `Acc(F, DEV-QA, learned)` ≤ 0.95 |
| G0.10 | 能估计 E1-V1 的规模:对 Δ(L−F)、Δ(A−F) 的 seed-average 配对差 d_f 算出标准差 σ_d(有限);分别用 σ_d 的 bootstrap 2.5 分位、点估计、97.5 分位,按 `n = ((1.96 + 0.84) · σ_d / δ)²`(双侧 0.05、功效 0.80)计算 δ ∈ {0.05, 0.10, 0.15} 下的所需 fact 数,以最大者作为 E1-V1 规划依据;再用 Pilot 的 fact 按 n 重抽样验证 CI 半宽。Pilot 的规模估计是规划估计,不是保证 |

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
| IMPLEMENTATION_FAIL | G0.1、G0.2、G0.6、G0.7、G0.8 不满足,或 Y 的 token 数比越界,或第 2.5 节干扰项的池少于 4 个答案,或配置冻结前读取 TEST(ST13),或实现与本协议不一致 |
| OPTIMIZATION_FAIL | G0.4 不满足(在给定训练量内连 TRAIN 陈述句都没有记住) |
| OPTIMIZATION_OR_CAPACITY_UNRESOLVED | G0.4 满足但 G0.5 或 T1 的正确率不满足 |
| CAPACITY_LIMIT | 仅当更强的模型在同一协议下 PASS 之后才可使用;在此之前必须保留 OPTIMIZATION_OR_CAPACITY_UNRESOLVED |
| HYPOTHESIS_FAIL | 保留给 E1-V1 的机制比较;E1-PILOT 没有机制假设,不使用 |
| BLOCKED | 环境、资源、数据来源或库版本不满足第 0 节,无法按协议执行;或第 8 步 L3–L6 任一项的 TEST 部分超限,或 L6 的 TEST 部分 Executor 与 data-auditor 的结果不一致(ST10);或任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致(ST12) |
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
| ST9 | 某次运行开始时读到的设备全名与首次记录不同 | 整批作废:本次 Pilot 的全部结果不得用于任何判断;BLOCKED;在设备全名一致的机器上从第 8 节第 3 步重新开始 |
| ST10 | 第 8 步 L3–L6 任一项的 TEST 部分超限;或 L6 的 TEST 部分 Executor 与 data-auditor 的结果不一致 | 停止;不评测 TEST;BLOCKED;报告 Owner |
| ST11 | 第 8 节第 2 步预检的预估总时长超过 3.5 小时 | 停止;报告 Owner |
| ST12 | 任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致。比对范围:(1)`PROTOCOL_FROZEN` 中列出的数据内容哈希(fact 哈希的比对方法见第 2.2 节);(2)冻结提交下本协议文件与三个 JSON 的原始字节哈希,用 `git cat-file` 从冻结提交读取。第 8 节第 1 步写入 manifest 的实际哈希字段(`DATA_MANIFEST.json: files`、`SPLIT_MANIFEST.json: split_sha256`)不在比对范围内 | 停止;BLOCKED |
| ST13 | 配置冻结前读取 TEST | IMPLEMENTATION_FAIL;本次 Pilot 全部作废 |

## 12. Out of Scope

- E1-V1 之后的任何实验。
- Growth、Consolidation、RAG、多跳。
- 模型选择与最终部署。
- Learned controller。
- NONE / 拒答校准。
- 探索沙盒(SANDBOX)。

## 13. Open Questions for Review Gate(原 PENDING_REVIEW_GATE 2 项,已按提案批准)

| # | 字段 | 冻结值(按提案批准;Owner 批准，2026-11-22 05:27 UTC) | 理由 |
|---|---|---|---|
| 1 | E1-V1 目标 fact 数 | 320(240 learned + 80 unread),并在 Pilot 后按 G0.10 的公式重算 | 若配对差的标准差为 0.5,检出 0.10 的差需要约 196 条 learned fact;取 240 留余量 |
| 2 | general-damage non-inferiority margin | dNLL ≤ +0.03(约 +3% PPL);在 Pilot 中只报告,不进门槛 | 与本仓库此前实验使用的容忍幅度一致;Pilot 里 general damage 只报告,不进门槛 |

**已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。

其余可执行参数都已写死;原标为 PROPOSED 的训练契约(第 7 节)、`SEARCH_SPACE.json` 与本节 2 项已于冻结时改为冻结值(Owner 批准，2026-11-22 05:27 UTC)。PROTOCOL_FROZEN 之后任何门槛、split 规则、指标、搜索预算或 Gate 定义的改动都必须开新协议版本。

## 14. 变更记录

时间为 UTC。哈希为包含该改动的提交。

| 版本 | 时间 | 提交 | 节 | 改动 | 原因 |
|---|---|---|---|---|---|
| v1 | 2026-11-10 15:48:18 | `aa0423ef` | 全部 | 初稿(撰写任务 METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1) | — |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 0 节“环境要求” | 原文“全参微调(F、A、S、Y)在 FP32 下需要约 4 × 6.9 GB(权重、梯度、AdamW 两个动量)再加激活,所以执行机器必须有 ≥ 40 GB 显存的单张 GPU,或 ≥ 48 GB 内存的 CPU 机器”改为“所有模型训练与评测只在一张 NVIDIA A100 80GB 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查” | 原文允许 CPU 机器和任意 ≥ 40 GB 的 GPU,与 Metrix Round 1 第 8 项的算力决定(单张 A100 80GB、上限 4 小时、型号写死)冲突;原文的 4 × 6.9 GB 也漏算了 arm A 的冻结 base 副本(核实后 A 为 34.4 GB) |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 11 节 ST7 | 原文“累计 wall-clock 超过上限(第 13 节第 3 项)→ 停并报告进度;转 GPU 或降级需 Owner 决定,不得静默继续”改为“累计 GPU wall-clock 超过 4 小时(第 7 节)→ 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续” | 第 13 节第 3 项已由同一决定移出待定列表,原指向失效;模型计算不再在 CPU 上进行,“转 GPU”不再适用 |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 7、8、13 节;文件头;`SEARCH_SPACE.json` | 写入算力决定与显存估计;第 8 节加 GPU 检查与算力边界;待定项 3 → 2;内联块加 BEGIN / END 标记 | Metrix Round 1 第 7、8 项 |
| v1-r2 | 2026-11-12 14:43:19 | `6675af63` | 第 2.2 节;`DATA_MANIFEST.json` | 写死名字生成的随机流 purpose、前 400 个候选的统计方法、接受阶段从头重抽;补全抽样、形式规则、冲突规则(含大小写与比较范围)、上限;加锚文本规则;给出 `DATA_SEED` 下 160 条 fact 的规范化 SHA-256 | Metrix Round 2 第 4 项:v1 未写死,只凭协议不能逐字节复现数据 |
| v1-r2 | 2026-11-12 14:43:19 | `6675af63` | 第 2.4、2.6 节;`SPLIT_MANIFEST.json` | Y 模板改短,答案前加空格;Y/F token 比 1.292 → 1.196 | Metrix Round 2 第 3 项:原比值超出第 2.6 节的 [0.80, 1.25];区间不变 |
| v1-r2 | 2026-11-12 14:43:19 | `6675af63` | 第 2.5、3 节;`SPLIT_MANIFEST.json` | L3 拆为 L3a(原规则)与 L3b(learned 答案在锚文本中的出现次数,上限 0) | Metrix Round 2 第 5 项:arm A 的暴露匹配原先没有检查覆盖 |
| v1-r2(Round 3 补记) | 2026-11-12 14:43:19 | `6675af63` | 第 2.2 节;`DATA_MANIFEST.json: name_generation.anchor_rule` | 新增锚文本规则:生成名字时,拒绝在第 2.7 节锚文本(512 篇、各截到 128 token 后解码)中出现过的字符串(不分大小写的子串);因此锚文本须在名字之前生成 | Metrix Round 2 第 5 项把 arm A 纳入暴露匹配(L3b):若某个名字出现在锚文本里,arm A 对该候选的暴露会多于 F,unread 名字也会违反 L3a。在生成时拒绝,使 L3a、L3b 在构造上成立(检查仍执行)。`DATA_SEED` 下这条规则没有拒绝任何名字,160 条 fact 的哈希不变(`ROUND2_REPORT.md` 对照运行 3)。上表 v1-r2 第 2.2 节一行只写了“加锚文本规则”,未写原因,Round 3 第 5 项要求补记 |
| v1-r2 | 2026-11-12 14:43:19 | `6675af63` | 第 0、7、8、11 节;`SEARCH_SPACE.json` | GPU 规则改为:首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废;新增 ST9 | Metrix Round 2 第 6 项 |
| v1-r2 | 2026-11-12 14:43:19 | `6675af63` | 第 14 节 | 新增本变更记录,补记 v1-r1 对第 0 节与 ST7 的改动 | Metrix Round 2 第 7 项 |
| v1-r3 | 2026-11-12 15:58:48 | `596fcfad` | 第 0 节;`SUBMISSION_NOTE.md` 第 1、5 节 | 原文“协议提交只新增 `metrix/e1-pilot/` 下 5 个文件”及验证命令“`git diff --stat 61d3c767 HEAD -- . ':(exclude)metrix'` 应为空”改为:metrix/ 以外只放行根目录 `CLAUDE.md` 追加的第 6 节(宪章原有内容须与 base 逐字节一致)和 `.claude/agents/` 下两个文件;注明两个 agent 文件被 `.gitignore` 忽略、用 `git add -f` 强制跟踪,以后改动也须用 `-f`;检查脚本 `reports/round3/outside_metrix_check.py` | Metrix Round 3 第 3 项:提交 `8ce8c896` 按 Owner 决定在宪章追加第 6 节并新增两个 subagent 文件,原检查“应为空”从此必然失败 |
| v1-r3 | 2026-11-12 15:58:48 | `596fcfad` | 第 0 节(新增“候选打分输入”行;“问答输入”注明 `enable_thinking=false` 写死)、第 2.2 节 `K_qa` 说明、第 5 节 `s_QA`;`DATA_MANIFEST.json: model.input_convention`、`name_generation.token_counts` | 原文 `s_QA(f, q, c) = Σ log p_θ(c_t \| chat(q), c_<t)`,K = 问答语境(assistant 回合开头、无前导空格)的 token 数,改为:assistant 回合以固定前缀 `The answer is` 开头,对 `" " + c` 打分,K = `K_st`。`K_qa` 保留为生成规则,fact 及其哈希不变 | Metrix Round 3 第 6 项。验证(第 7 项):120 个 learned 答案 × 2 个 DEV 问句,打分 token id 与 TRAIN 陈述句中答案片段的 token id 不一致数为 0;第 8 项候选可行性:最小池 5,不足 4 的 cell 0 |
| v1-r4 | 2026-11-21 05:05:03 | `b1f5889c` | 第 5 节 EM;第 0 节(新增“生成输入(EM)”行);`DATA_MANIFEST.json: model.input_convention.em_generation` | 原文“对同一 `chat(q)` 做贪心解码……归一化:取第一行……`EM(f, q) = 1[norm(output) == norm(a_f)]`”改为:对 `chat(q) + "The answer is"`(与 `s_QA` 的上下文相同)做贪心解码,输出先去掉开头的空格再归一化,`EM(f, q) = 1[norm(output') == norm(a_f)]`;最多 16 个新 token、遇 im_end 停、归一化各步与聚合不变 | Review Gate 裁决(`ROUND3_REPORT.md`“待 Review Gate 决定”第 1 项;Round 3 code-reviewer MAJOR 1、data-auditor Observation 2):候选打分已改为在 `The answer is` 之后打分,EM 仍从裸 `chat(q)` 解码,两者输入不一致;模型若回答整句,归一化后不可能等于答案 |
| v1-r4 | 2026-11-21 05:05:03 | `b1f5889c` | 第 4 节 arm A 损失;第 5 节 general damage;第 0 节(新增“通用文本与锚文本输入”行);`DATA_MANIFEST.json: model.input_convention.general_text_and_anchor` | 写明通用文本窗口与锚文档前面都不加任何特殊 token(不前置 `<\|endoftext\|>`),第一个 token 不计分、不计 KL,t 从 2 起。arm A 原文 `mean_t KL(...)` 改为 `mean_{t=2..n_x} KL(...)`;general damage 的公式(原已是 `t=2..n_w`)不变,补文字说明 | Review Gate 裁决(待决第 2 项;Round 3 任务 4 #6、#7):原文没有写明是否前置特殊 token,KL 的 t 范围也没有写明;Qwen3 没有 BOS(`bos_token None`),不前置 token 时第一个位置没有条件 |
| v1-r4 | 2026-11-21 05:05:03 | `b1f5889c` | 第 14 节 | v1-r2 各行“2026-11-12 / 本节所在提交”改为“2026-11-12 14:43:19 / `6675af63`”;v1-r3 各行“2026-11-12 / Round 3 提交(hash 见 `reports/ROUND3_REPORT.md`)”改为“2026-11-12 15:58:48 / `596fcfad`”;表后加注:宪章第 6 节标题中的日期是 JST | Review Gate 裁决(待决第 3、4 项;Round 3 code-reviewer MAJOR 2):“本节所在提交”在 Round 2 之后的每个提交上都成立,有歧义;v1-r3 只写了日期,提交要到报告里查。时间是提交时间(`git log --format=%cI`),原始输出 `reports/round4/t1_commit_times.txt` |
| v1-r4 | 2026-11-21 05:05:03 | `b1f5889c` | 第 2.2 节答案等长规则的“作用”;`DATA_MANIFEST.json: name_generation.answer_token_length_rule.purpose` | 补一句:Round 3 起候选打分只用 `K_st`,`K_qa` 相同已不影响打分,保留它是为了不改变 fact 及其哈希。规则本身不变,fact 哈希不变 | Round 3 code-reviewer MINOR:原“作用”仍按 Round 3 之前的问答语境(assistant 回合开头、无前导空格)描述 |
| v1-r4 | 2026-11-21 05:05:03 | `b1f5889c` | 第 5 节 `s_ST` | 补定义 `K' = K_st(c)` | Round 3 data-auditor Observation 1:`K'` 没有定义。验证:120 条 learned fact × 同 cell 的 15 个 learned 答案(1,800 对),`prefix(f) + " " + c` 中 `prefix(f)` 的 token 都是整串 token 的前缀,其后的 token 都等于 `encode(" " + c)`,数目都等于 `K_st(c)`;不一致数 0(`reports/round4/t2_st_prefix_check.txt`) |
| v1-r5 | 2026-11-21 06:37:20 | `c73f41a3` | 第 4 节 arm A 损失 | 原文 `λ · mean_{t=2..n_x} KL(...)`、“x 为该步的 4 篇锚文档,n_x 为锚文档的 token 数”改为 `λ · [Σ_{x ∈ X_s} Σ_{t=2..n_x} KL(...)] / [Σ_{x ∈ X_s} (n_x − 1)]`、“X_s 为第 s 步的 4 篇锚文档,n_x 为锚文档 x 的 token 数”,并写明 KL 项对 4 篇锚文档中全部计 KL 的 token 按 token 加权平均,不先对每篇求均值 | Review Gate 第 4 轮裁决(`ROUND4_REPORT.md`“待 Review Gate 决定”第 1 项;Round 4 code-reviewer MAJOR 1):原文没有写明 4 篇之间怎么平均,而锚文档长度不全相同(512 篇中 1 篇为 123 token,`reports/round4/t1_anchor_short_docs.txt`) |
| v1-r5 | 2026-11-21 06:37:20 | `c73f41a3` | 第 5 节 EM;`DATA_MANIFEST.json: model.input_convention.em_generation` | 原文“遇 im_end 特殊 token(id 151645)停”改为遇 im_end(id 151645)或 endoftext(id 151643)即停;新增“新 token 解码成文本时跳过特殊 token(`skip_special_tokens=True`;这两个停止 token 都是特殊 token,不进入输出)”。`em_generation` 补写停止 token 与跳过特殊 token | Review Gate 第 4 轮裁决(待决第 2 项;Round 4 code-reviewer MAJOR 2、data-auditor 观察 1、2):原文停止 token 只有 151645,训练输入每句后接 151643;没有写解码时是否跳过特殊 token,输出若保留 im_end,以它结束的输出 EM 都为 0。两个 id 都是特殊 token,与固定 revision 的 `generation_config.json` 的 eos 列表相同(`reports/round5/t1_em_special_tokens.txt`) |
| v1-r5 | 2026-11-21 06:37:20 | `c73f41a3` | 第 5 节 `s_ST` | `prefix(f)` 的定义补“不含答案前的空格(该空格属于 c')” | Review Gate 第 4 轮裁决(待决第 4 项前半;Round 4 code-reviewer MAJOR 3):“答案之前的文本”是否含答案前的空格有歧义。Round 4 的 K' 检查已按不含空格计算,本轮重跑结果不变(`reports/round5/t1_st_prefix_check.txt`) |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 3 节 L6;`SPLIT_MANIFEST.json: leakage_checks.L6_general_text` | 原文 L6 规则“锚文本与通用文本共享的词 13-gram 数”(manifest:`word 13-grams shared between anchor_text and general_dev / general_test`)补定义:“词”= Python `str.split()` 的结果(按空白切分,区分大小写);Qwen token 13-gram 只报告,不设上限(manifest 新增 `report_only` 键)。上限 0 不变 | Review Gate 第 5 轮裁决(`ROUND5_REPORT.md`“待 Review Gate 决定”第 4 项;Round 5 data-auditor 观察 1):原文没有定义“词”。Round 5 按 `str.split()` 计数为 0(`reports/round5/t5_l6_check.txt`) |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 2.7 节;`DATA_MANIFEST.json: general_text.window_rule` | 原文“再用本协议的分词器切分并截到 256 token”改为“再用本协议的分词器切分;每个窗口最多 256 token(取前 256 个),不足则取全长”。取窗方式不变 | Review Gate 第 5 轮裁决(待决第 5 项;Round 5 data-auditor 观察 2):100 个 general DEV 窗口中 64 个按 Qwen 分词不到 256 token(最短 172),“截到 256”与实际不符 |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 4 节 arm A 损失 | 原文“n_x 为锚文档 x 的 token 数”改为“n_x 为锚文档 x 实际送入模型的 id 序列长度” | Review Gate 第 5 轮裁决(待决第 6 项;Round 4 data-auditor 观察 4、Round 5 data-auditor 观察 3):原文没有写明 n_x 取重新编码后的长度还是送入模型的 id 长度 |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 5 节 EM;第 0 节“生成输入(EM)”;`DATA_MANIFEST.json: model.input_convention.em_generation` | 新增“`do_sample=False`,每步取概率最大的 token;这一设置写死,覆盖固定 revision 的 `generation_config.json` 中的采样默认值(`do_sample` true、`temperature` 0.6、`top_k` 20、`top_p` 0.95)”。删去“输出先去掉开头的空格,再归一化”;归一化的“去首尾空白”后注明“输出开头的空格在这一步去掉”;原文“`EM(f, q) = 1[norm(output') == norm(a_f)]`,output' = 去掉开头空格后的输出”改为“`EM(f, q) = 1[norm(output) == norm(a_f)]`”。第 0 节“生成输入(EM)”一行补“`do_sample=False`,覆盖 `generation_config.json` 的采样默认值” | Review Gate 第 5 轮裁决(待决第 7 项第 2、3 点;Round 5 code-reviewer MINOR、data-auditor 观察 4):固定 revision 的 `generation_config.json` 默认采样,原文只写“贪心”,没有写必须覆盖;“去掉开头空格”与归一化的“去首尾空白”重复,含义不清 |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 5 节 `s_ST`;`DATA_MANIFEST.json: model.input_convention.train_closed_book` | `prefix(f)` 的定义补“前面不加任何特殊 token”;manifest 新增 `train_closed_book` 一项 | Review Gate 第 5 轮裁决(待决第 8 项第 1 点,即第 4 轮待决第 4 项后半):原文没有写明 `prefix(f)` 前加不加特殊 token |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 8 节第 8 步、G0.1;第 3 节执行接口;`SPLIT_MANIFEST.json: leakage_checks.test_split` | 第 8 步在“对 TEST 运行 L3–L5”之后加“L6 的 TEST 部分(锚文本对 `general_test.jsonl`):在 PROTOCOL_FROZEN 之后、TEST 评测之前,由 data-auditor 运行一次,只输出计数”;G0.1 原文“泄漏检查 L1–L6 全部在上限内”后加“L6 在 Gate 0 只要求 DEV 部分(锚文本对 `general_dev.jsonl`),TEST 部分按第 8 步运行”;第 3 节执行接口与 manifest 的 `test_split` 各加一句指向第 8 步 | Review Gate 第 5 轮裁决(待决第 2 项;Round 5 code-reviewer MAJOR 1、data-auditor 观察 1):原文没有安排 L6 TEST 部分的运行时机,而 G0.1 要求 Gate 0 时 L1–L6 全部在上限内 |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 3 节(新增一条);第 7 节“选择只用 DEV” | 新增定义:“读取 TEST 数据”= 解码 test 行的内容,或用其内容做任何计算;解析 `split` 字段、计数、对整个文件求哈希不算。第 7 节“TEST 在最终冻结前不可读取、不可生成”后加“(“读取”的定义见第 3 节)” | Review Gate 第 5 轮裁决(待决第 3 项;Round 5 code-reviewer MAJOR 2):Round 5 的 L6 检查对 `eval_sets.jsonl` 的 test 行做了 JSON 解析与计数,原文没有定义这是否算“读取 TEST 数据” |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 2.7 节;`DATA_MANIFEST.json: general_text.source_file_sha256`、`general_text.decode_tokenizer_json_sha256` | 第 2.7 节注明 `eval_sets.jsonl` 与 parcae `tokenizer.json` 的 sha256(缩写,全值在 manifest);manifest 新增这两个 sha256 | Review Gate 第 5 轮裁决(待决第 9 项 `l6_check.py` 末点):原文与 manifest 只锁定了 parcae 分词器的 revision,没有锁定这两个文件的内容;Round 5 以 Stage 1 `data_lock.json` 为基准核对 |
| v1-r6 | 2026-11-21 14:41:02 | `481a6f0f` | 第 0 节“通用文本与锚文本输入”;第 14 节 v1-r4 第 2 行 | 两个单元格中 `<\|endoftext\|>` 的两条竖线原文没有转义,改为用反斜杠转义;渲染出的文字不变 | Review Gate 第 5 轮裁决(待决第 10 项):未转义的竖线在 GitHub Markdown 表格里会切开单元格 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 2.7 节 | 原文“锚文本与通用文本不得共享任何 13-gram。”改为“锚文本与通用文本不得共享任何词 13-gram(定义与上限见第 3 节 L6)。” | Review Gate 第 6 轮裁决,第 7 轮指令第 1a 项(`ROUND6_REPORT.md`“待 Review Gate 决定”第 1 项;R6 code-reviewer MAJOR,`reviews/599230f9…/code-reviewer.md` 第 17 行):第 3 节 L6 按 v1-r6 只限词 13-gram,Qwen token 13-gram 只报告,第 2.7 节的“任何 13-gram”与之说法不一 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 3 节 L6 一行与执行接口;第 8 节第 8 步;`SPLIT_MANIFEST.json: leakage_checks.L6_general_text.test_part`(新增)、`leakage_checks.test_split` | L6 一行新增 TEST 部分的时机、计数与运行者:“时机为第 8 步生成 `general_test.jsonl` 之后、TEST 评测之前;计数为跨全部文档的共享词 13-gram 种类数(……),上限 0;由 Executor 与 data-auditor 各自计算,结果须一致”。第 8 步原文“在 PROTOCOL_FROZEN 之后、TEST 评测之前,由 data-auditor 运行一次,只输出计数”改为“在本步生成 `general_test.jsonl` 之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算一次,只输出计数(口径与上限见第 3 节 L6),两者的结果须一致”。执行接口原文“L6 的 TEST 部分见第 8 节第 8 步”改为“L6 的 TEST 部分在 `general_test.jsonl` 生成之后才运行(时机与口径见上表 L6 一行与第 8 节第 8 步)” | Review Gate 第 6 轮裁决,第 7 轮指令第 1b 项(待决第 2 项;`reviews/599230f9…/code-reviewer.md` 第 14、15、27 行):原时机“PROTOCOL_FROZEN 之后”比 `general_test.jsonl` 的生成条件宽;“计数”没有定义口径;运行者 data-auditor 按 metrix/CLAUDE.md 第 10 节仍为「待验证」 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 8 节第 8 步;第 11 节(新增 ST10);第 9 节 BLOCKED 一行;第 3 节执行接口;`SPLIT_MANIFEST.json: leakage_checks.test_part_over_limit`(新增) | 新增:L3–L6 任一项的 TEST 部分超限时,停止,不评测 TEST,状态记为 BLOCKED,报告 Owner(ST10)。第 8 步原文“→ **TEST 只评一次**”改为“→ L3–L6 任一项的 TEST 部分超限:停止,不评测 TEST,状态记为 BLOCKED,报告 Owner(ST10) → 全部在上限内时,**TEST 只评一次**”;第 9 节 BLOCKED 的适用情形后加“或第 8 步 L3–L6 任一项的 TEST 部分超限(ST10)” | Review Gate 第 6 轮裁决,第 7 轮指令第 1c 项(待决第 2 项第 2 点;`reviews/599230f9…/code-reviewer.md` 第 15 行):原文没有写 TEST 部分超限时的动作,ST1 只管第 2 步 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 8 节 G0.1;`SPLIT_MANIFEST.json: leakage_checks.test_split` | 原文“泄漏检查 L1–L6 全部在上限内;L6 在 Gate 0 只要求 DEV 部分(锚文本对 `general_dev.jsonl`),TEST 部分按第 8 步运行”改为“泄漏检查 L1–L6 全部在上限内;L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行” | Review Gate 第 6 轮裁决,第 7 轮指令第 1d 项(待决第 3 项;`reviews/599230f9…/code-reviewer.md` 第 16 行):原文只给 L6 开了例外,L3–L5 的 TEST 部分也要等第 8 步生成 `test_qa.jsonl` 才能运行 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 5 节 general damage;第 2.7 节锚文本;第 2.2 节锚文本规则;`DATA_MANIFEST.json: general_text.window_rule`、`anchor_text.document_rule`(新增) | n_w 原文“窗口的 token 数”改为“窗口实际送入模型的 id 序列长度:送入模型的是第 2.7 节用本协议分词器切分后截断得到的原始 id(最多 256 个),不解码再编码”。锚文本原文“各截到 128 token”改为“每篇最多 128 token(取前 128 个),不足则取全长”;第 2.2 节“512 篇、各截到 128 token 后解码的文本”改为“512 篇、每篇最多 128 token、解码后的文本” | Review Gate 第 6 轮裁决,第 7 轮指令第 1e 项(待决第 4、5 项;`reviews/599230f9…/code-reviewer.md` 第 18、19 行):n_w 与 v1-r6 改过的 n_x 口径不一;第 340 篇锚文档全文只有 123 个 token,“截到 128”与实际不符。数值不变 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 5 节 EM;`DATA_MANIFEST.json: model.input_convention.em_generation` | 新增“归一化之前,先删除输出中的 `<think>…</think>` 片段:从 `<think>` 到其后第一个 `</think>`(两者都含),每处都删;这两个标记(id 151667、151668)不是特殊 token,`skip_special_tokens=True` 不会去掉它们” | Review Gate 第 6 轮裁决,第 7 轮指令第 1f 项(待决第 11 项第 1 点;第 5 轮待决 7 第 1 点):两个标记不是特殊 token(`reports/round7/t1f_think_tokens.txt`),原文的 `skip_special_tokens=True` 去不掉;它们出现在输出第一行时,归一化后的输出不可能等于答案 |
| v1-r7 | 2026-11-22 03:25:59 | `7fea9181` | 第 2.5 节(新增“调用方式(细节 5)”“`candidates.json`”两条与复现哈希);第 2.6 节(新增“调用方式(细节 4)”与复现哈希);`DATA_MANIFEST.json: s_permutation`(字符串改为对象,原文保留为 `rule`);`SPLIT_MANIFEST.json: candidates.call_order`、`file`、`reference_implementation`、`candidate_mapping_sha256_note`(新增),`candidate_mapping_sha256`(null 改为全值) | 写死两处随机流的调用顺序与文件记录格式:S 每个 cell 一个生成器,每次从 `list(range(15))` 开始调用一次 `shuffle`,有不动点用同一生成器重抽;候选每条 fact 一个生成器,依次 `sample(池, 3)`、`shuffle([a_f] + d)`,池按 fact 生成顺序。`DATA_SEED` 下 `train_S.jsonl` 规范化 SHA-256 `686fdd2f…`,`candidates.json` `e5d15c99…`(全值见正文与 manifest) | Review Gate 第 6 轮裁决,第 7 轮指令第 1g 项(待决第 11 项第 2 点;第 4 轮待决 8):原文只写了 purpose,没有写调用方式,只凭协议不能逐字节复现这两个文件。两次独立运行逐字节一致(`reports/round7/t1g_gen_s_cands.txt`) |
| v1-r8(冻结) | 冻结提交的提交时间(见 `PROTOCOL_FROZEN`) | 冻结提交(标签 `metrix-e1-pilot-frozen`) | 第 2.5、2.6 节(文字不变);`DATA_MANIFEST.json: files.train_S.jsonl.record`、`files.candidates.json.record`(新增) | 确认 `train_S.jsonl` 每行 `{"fact_id", "answer_fact_id", "text"}`(第 2.6 节)、`candidates.json` 为 `{fact_id: [4 个候选]}`(第 2.5 节);两节的文字 v1-r7 已如此写,本次不改。`DATA_MANIFEST.json: files` 中这两个文件新增 `record` 键,写明同一格式。两个复现哈希不变 | Review Gate 第 7 轮裁决,第 8 轮指令第 1a 项(`ROUND7_REPORT.md`“待 Review Gate 决定”第 2 项;`reviews/293b806d…/code-reviewer.md` 第 31 行):两个文件的记录格式原由 Executor 自定,规范化哈希依赖这一选择 |
| v1-r8(冻结) | 同上 | 同上 | 第 3 节 L6 一行与执行接口;第 8 节第 8 步;第 9 节 BLOCKED 一行;第 11 节 ST10;`SPLIT_MANIFEST.json: leakage_checks.L6_general_text.test_part.count`、`test_part.text`(新增)、`test_part.computed_by`、`leakage_checks.test_part_over_limit` | L6 TEST 部分计数的括注原文“(13-gram 在每篇锚文档、每个窗口之内取;锚文本 512 篇的词 13-gram 集合与 `general_test.jsonl` 全部窗口的词 13-gram 集合求交,数交集的元素个数)”改为“:13-gram 在每篇文档(每篇锚文档、每个窗口)之内取,不跨篇拼接;锚文本 512 篇的词 13-gram 合并为一个集合,`general_test.jsonl` 全部窗口的词 13-gram 合并为一个集合,两者求交,计交集的种类数(元素个数);取 13-gram 的文本是实际送入模型的 id 用本协议分词器解码所得(锚文档最多 128 个 id,窗口最多 256 个 id)”;“结果须一致”后加“两者结果不一致时按 BLOCKED 处理并报告 Owner(ST10)”。执行接口、第 8 步、第 9 节 BLOCKED 一行与 ST10 的事件各加“L6 的 TEST 部分 Executor 与 data-auditor 的结果不一致”;第 8 步“全部在上限内时”改为“全部在上限内且 L6 两者结果一致时” | 第 8 轮指令第 1b 项(待决第 3、5 项;`reviews/293b806d…/code-reviewer.md` 第 32、41 行):“跨全部文档”也可读成 n-gram 跨篇拼接;计算用的文本没有定义;两方结果不一致时没有规定动作 |
| v1-r8(冻结) | 同上 | 同上 | 第 5 节 EM;`DATA_MANIFEST.json: model.input_convention.em_generation` | 原文“归一化:取第一行,去首尾空白(输出开头的空格在这一步去掉),去开头的 “the ”……”改为“归一化:删除 `<think>…</think>` 片段之后,先去掉开头的空白(含空格与换行),再取第一行,去首尾空白,去开头的 “the ”……”。manifest 中原文“EM compares norm(output) with norm(answer), and leading spaces of the output are removed by the strip step of the normalization”改为同样的顺序(删除后先去开头空白、再取第一行) | 第 8 轮指令第 1c 项(待决第 6 项第 1 点;`reviews/293b806d…/data-auditor.md` 第 149 行起,M1):`enable_thinking=false` 的生成提示以 `<think>\n\n</think>\n\n` 结尾,模型若再生成这一段,删除后输出以空行开头,原来先“取第一行”会得到空串 |
| v1-r8(冻结) | 同上 | 同上 | `DATA_MANIFEST.json: model.tokenizer.files_sha256`、`model.tokenizer.files_note`、`anchor_text.decoded_texts_canonical_sha256`、`anchor_text.decoded_texts_hash_rule`(均新增) | 写入固定 revision 的 4 个分词器文件(`tokenizer.json`、`tokenizer_config.json`、`vocab.json`、`merges.txt`;该 revision 的仓库中没有其它分词器文件)的 sha256,以及锚文本 512 篇解码文本的规范化 SHA-256 `8828bc4f…` 与其算法(全值见 manifest) | 第 8 轮指令第 1d 项(待决第 12 项;`reviews/293b806d…/code-reviewer_report-commit.md` 第 52–53 行):这些哈希原先只记在报告与原始输出中,不在 manifest 里。本轮重算见 `reports/round8/t0_env.txt`、`reports/round8/t1d_data_hashes.txt` |
| v1-r8(冻结) | 同上 | 同上 | `metrix/CLAUDE.md` 第 8 节(不属于本协议;指令要求第 1 项全部记入本节) | 原文“只有「永久」的裁决可写入本文件。”改为“「永久」与「本阶段」的裁决可写入本文件,写入时须注明作用范围;「本阶段」的裁决在本阶段结束时失效。”,并注明出处、批准、时间与原因 | 第 8 轮指令第 1e 项(待决第 4 项;`reviews/293b806d…/code-reviewer.md` 第 33 行):原文与第 7 轮写入的第 5 节第 6 条、第 10 节两条「本阶段」裁决矛盾 |
| v1-r8(冻结) | 同上 | 同上 | 第 7 节训练契约表头;`SEARCH_SPACE.json`(及第 7 节内联副本)、`DATA_MANIFEST.json`、`SPLIT_MANIFEST.json` 的 `status`;第 13 节;文件头说明;第 1 节 Non-claims | 训练契约表头“值(PROPOSED)”改为“值(冻结;Owner 批准，2026-11-22 05:27 UTC)”,表中数值不变。`SEARCH_SPACE.json` 的 `status` 由 `PROPOSED`、两个 manifest 的 `status` 由 `PROPOSED_NOT_FROZEN` 改为 `PROTOCOL_FROZEN`,三个文件都在 `status` 后新增 `"frozen": "Owner 批准，2026-11-22 05:27 UTC"`;内联副本随之更新。第 13 节两项按提案批准:第 1 项值不变(320 条 fact,Pilot 后按 G0.10 重算),第 2 项值后加“在 Pilot 中只报告,不进门槛”;标题“(PENDING_REVIEW_GATE 仅此 2 项)”改为“(原 PENDING_REVIEW_GATE 2 项,已按提案批准)”,表头“PROPOSED”改为“冻结值(按提案批准;Owner 批准，2026-11-22 05:27 UTC)”;末段“其余可执行参数都已写死或标为 PROPOSED;Review Gate 可以改动一次,”改为“其余可执行参数都已写死;原标为 PROPOSED 的训练契约(第 7 节)、`SEARCH_SPACE.json` 与本节 2 项已于冻结时改为冻结值(Owner 批准，2026-11-22 05:27 UTC)。”。文件头“PENDING_REVIEW_GATE 只剩第 13 节的 2 项”改为“PENDING_REVIEW_GATE 原只剩第 13 节的 2 项,已于冻结时按提案批准(Owner 批准，2026-11-22 05:27 UTC)”;第 1 节“margin 待 Review Gate,见第 13 节”改为“margin 见第 13 节,在 Pilot 中只报告” | 第 8 轮指令第 2 项(待决第 12 项中“改哪些 `status` 字段”):Owner 批准冻结,PROPOSED 各项改为冻结值;文件头、第 1 节与第 13 节末段的原文在批准后不再成立 |
| v1-r8(冻结) | 同上 | 同上 | 文件头“状态”一行 | 原文“**AWAITING_REVIEW_GATE**(未冻结;冻结后本表改为 PROTOCOL_FROZEN)”改为“**PROTOCOL_FROZEN**(Owner 批准，2026-11-22 05:27 UTC;冻结提交打标签 `metrix-e1-pilot-frozen`,其完整 hash 与该提交下本文件、三个 JSON 的 sha256 记在同目录的 `PROTOCOL_FROZEN` 文件中)” | 第 8 轮指令第 3 项:Owner 于 2026-11-22 05:27 UTC 批准冻结 |
| v1-r8(冻结) | 同上 | 同上 | 第 8 节 G0.8 | 原文“复现:对 F 选定配置的 3 个 checkpoint 各评测两次,所有 (fact, 问句) 的预测完全相同,候选分数差 ≤ 1e-4,每个通用窗口的 NLL 差 ≤ 1e-5”整条改为“复现:同一 checkpoint 两次评测,候选分数差 ≤ 1e-4;某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同,其余预测须完全相同;并列判为错。实现须开启 PyTorch 确定性设置并记录”。原文的“F 选定配置的 3 个 checkpoint”与“每个通用窗口的 NLL 差 ≤ 1e-5”不再出现 | 对照 Task Order V1.2 补齐;第 8 轮补充第 a 项(`tasks/ROUND8_TASKS.md` 第二段;Owner 回答“按所发内容执行”,按原文字面写入) |
| v1-r8(冻结) | 同上 | 同上 | 第 2.5 节(新增一条);第 9 节 IMPLEMENTATION_FAIL 一行;`SPLIT_MANIFEST.json: candidates.pool_too_small`(新增) | 新增“干扰项的池少于 4 个答案即 IMPLEMENTATION_FAIL,不生成合成干扰项。”;第 9 节 IMPLEMENTATION_FAIL 的适用情形加“或第 2.5 节干扰项的池少于 4 个答案”。`DATA_SEED` 下各 fact 的池为 learned 14 个、unread 4 个,不触发;候选与冻结哈希不变 | 对照 Task Order V1.2 补齐;第 8 轮补充第 b 项(`tasks/ROUND8_TASKS.md` 第二段;Owner 回答“按所发内容执行”,按原文字面写入) |
| v1-r8(冻结) | 同上 | 同上 | 第 8 节 G0.10 | 原文“并给出 δ ∈ {0.05, 0.10, 0.15} 下的所需 fact 数 `n = …`(双侧 0.05、功效 0.80)”改为“分别用 σ_d 的 bootstrap 2.5 分位、点估计、97.5 分位,按 `n = …`(双侧 0.05、功效 0.80)计算 δ ∈ {0.05, 0.10, 0.15} 下的所需 fact 数,以最大者作为 E1-V1 规划依据”;句末加“Pilot 的规模估计是规划估计,不是保证” | 对照 Task Order V1.2 补齐;第 8 轮补充第 c 项(`tasks/ROUND8_TASKS.md` 第二段;Owner 回答“按所发内容执行”,按原文字面写入) |
| v1-r8(冻结) | 同上 | 同上 | 第 8 节第 2 步(新增“预检”);第 11 节(新增 ST11) | 新增“预检(正式运行前;ST11):在 A100 上跑第一个配置的前 20 步,记录每步耗时、tokens/s、峰值显存与预估总时长;预估超过 3.5 小时即停止并报告 Owner。”;ST11:“第 8 节第 2 步预检的预估总时长超过 3.5 小时 → 停止;报告 Owner”。第 8 节各步编号不变 | 对照 Task Order V1.2 补齐;第 8 轮补充第 d 项(`tasks/ROUND8_TASKS.md` 第二段;Owner 回答“按所发内容执行”,按原文字面写入) |
| v1-r8(冻结) | 同上 | 同上 | 第 11 节(新增 ST12、ST13);第 9 节 BLOCKED、IMPLEMENTATION_FAIL 两行 | ST12:“任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致 → 停止;BLOCKED”;ST13:“配置冻结前读取 TEST → IMPLEMENTATION_FAIL;本次 Pilot 全部作废”。第 9 节 BLOCKED 的适用情形加 ST12,IMPLEMENTATION_FAIL 加“或配置冻结前读取 TEST(ST13)” | 对照 Task Order V1.2 补齐;第 8 轮补充第 e 项(`tasks/ROUND8_TASKS.md` 第二段;Owner 回答“按所发内容执行”,按原文字面写入) |
| v1.1(冻结勘误) | v1.1 冻结提交的提交时间(见 `PROTOCOL_FROZEN` 的 v1.1 一节) | v1.1 冻结提交(标签 `metrix-e1-pilot-frozen-v1.1`,由 Owner 推送) | 第 8 节 G0.8 | v1 原文“复现:同一 checkpoint 两次评测,候选分数差 ≤ 1e-4;某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同,其余预测须完全相同;并列判为错。实现须开启 PyTorch 确定性设置并记录”改为“复现：对 F 选定配置的 3 个 checkpoint 各评测两次；候选分数差 ≤ 1e-4；某题两次中任一次最高两个候选分数差 ≤ 1e-4 时允许预测不同，其余预测须完全相同；并列判为错；每个通用窗口的 NLL 差 ≤ 1e-5。实现须开启 PyTorch 确定性设置并记录。” | 冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验。v1 补充 a 的指令措辞使原条整条被替换，丢失复评对象与 NLL 容差(v1-r8 的 G0.8 一行;第 9 轮指令第 1a 项) |
| v1.1(冻结勘误) | 同上 | 同上 | 第 11 节 ST12 | “条件”栏原文“任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致”之后加:“比对范围:(1)`PROTOCOL_FROZEN` 中列出的数据内容哈希(fact 哈希的比对方法见第 2.2 节);(2)冻结提交下本协议文件与三个 JSON 的原始字节哈希,用 `git cat-file` 从冻结提交读取。第 8 节第 1 步写入 manifest 的实际哈希字段(`DATA_MANIFEST.json: files`、`SPLIT_MANIFEST.json: split_sha256`)不在比对范围内”;“处理”栏不变 | 冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验。v1 的 ST12 没有写比对范围,照字面会在第 8 节第 1 步写入 manifest 后触发(第 9 轮指令第 1b 项;`reports/ROUND8_REPORT.md`“待 Review Gate 决定”第 2 项) |
| v1.1(冻结勘误) | 同上 | 同上 | 第 2.2 节(新增“fact 哈希的比对方法”一条) | 新增:“从 `facts.jsonl` 读出 fact 列表(按文件中的行序,即生成顺序;每条 fact 为上一条所列的 6 个字段),按本节的规范化方法(第 0 节对这个 JSON 列表的规范化序列求 SHA-256)重算,与 `406c8801…` 比对。`facts.jsonl` 文件按 JSONL 规则得到的 `canonical_sha256` 是另一串字节的哈希,不与此值比对。”(正文写全值)。fact 的冻结哈希不变 | 冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验。v1 没有写 `facts.jsonl` 与 `406c8801…` 的比对口径(第 9 轮指令第 1c 项;`reports/ROUND8_REPORT.md`“待 Review Gate 决定”第 3 项) |
| v1.1(冻结勘误) | 同上 | 同上 | 第 1 节 Non-claims | v1 原文“margin 见第 13 节,在 Pilot 中只报告”改为“margin 已按提案批准为 dNLL ≤ +0.03,见第 13 节第 2 项;Owner 批准，2026-11-22 05:27 UTC;在 Pilot 中只报告,不进门槛”。v1-r8 已把 v1-r7 的“margin 待 Review Gate,见第 13 节”改为 v1 原文;本次写明已批准的值与批准记录 | 冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验(第 9 轮指令第 1d 项) |
| v1.1(冻结勘误) | 同上 | 同上 | 文件标题;文件头“状态”一行;`DATA_MANIFEST.json`、`SPLIT_MANIFEST.json`、`SEARCH_SPACE.json`(及第 7 节内联副本)的 `version` | 标题“PROTOCOL v1”改为“PROTOCOL v1.1”;三个 JSON 与内联副本的 `version` 由 `v1` 改为 `v1.1`(`status` 仍为 `PROTOCOL_FROZEN`,`frozen` 字段不变);状态一行原文“**PROTOCOL_FROZEN**(Owner 批准，2026-11-22 05:27 UTC;冻结提交打标签 `metrix-e1-pilot-frozen`,其完整 hash 与该提交下本文件、三个 JSON 的 sha256 记在同目录的 `PROTOCOL_FROZEN` 文件中)”改为“**PROTOCOL_FROZEN（v1.1）**(v1.1 勘误版:Owner 批准，2026-11-22 09:44 UTC;v1:Owner 批准，2026-11-22 05:27 UTC。v1.1 冻结提交的标签为 `metrix-e1-pilot-frozen-v1.1`,v1 冻结提交的标签为 `metrix-e1-pilot-frozen`,都由 Owner 推送;两个冻结提交的完整 hash 与各自提交下本文件、三个 JSON 的 sha256 记在同目录的 `PROTOCOL_FROZEN` 文件中)” | 冻结勘误，Owner 批准 2026-11-22 09:44 UTC；勘误时未运行任何实验(第 9 轮指令第 1e 项;标签由 Owner 推送:第 9 轮指令开头) |

注(v1-r8):一个提交不能包含自身的 hash,冻结之后补填又会改动冻结的协议,所以 v1-r8 各行的“时间”与“提交”写作“冻结提交”;冻结提交的完整 hash 与提交时间记在 `PROTOCOL_FROZEN` 文件中,并由标签 `metrix-e1-pilot-frozen` 指向。

注(v1.1):v1.1 各行的“时间”与“提交”写作“v1.1 冻结提交”,原因同 v1-r8 的注;v1.1 冻结提交的完整 hash 与提交时间记在 `PROTOCOL_FROZEN` 的 v1.1 一节。v1.1 是冻结后的勘误版,由 Owner 于 2026-11-22 09:44 UTC 批准;勘误时没有运行任何实验,勘误不基于任何结果。v1 的数据哈希(第 2.2、2.5、2.6 节与两个 manifest 中的值)在 v1.1 中都不变。

注:根目录 `CLAUDE.md`(宪章)第 6 节标题中的日期 “2026-11-13” 是 JST(日本标准时间,UTC+9)。该节由提交 `8ce8c896` 加入,提交时间 2026-11-12 15:25:19 UTC,即 2026-11-13 00:25:19 JST。本表的时间都是 UTC。
