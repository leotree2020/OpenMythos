# METRIX E1-PILOT · Round 1 报告

| 项 | 值 |
|---|---|
| 分支 | `metrix-e1-pilot-protocol-v1` |
| 基于提交 | `aa0423ef644234b0f523674d0067b55ec5533913`(上一次提交,即 `aa0423ef`) |
| 本报告所在提交 | 包含本文件的那次提交(哈希见提交记录) |
| 执行环境 | 本地 CPU 容器;Python 3.13;torch 2.11.0+cpu;transformers 5.22.2 |
| 模型文件 | `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` 的本地快照,只读 `config.json`、safetensors 头信息和分词器 |
| 约束遵守 | 未训练、未评测、未加载模型权重(只读 safetensors 文件头的 JSON)、未生成或读取 TEST 数据、未删除文件、未 force push |

## 总览

| # | 任务 | 状态 | 一句话结论 |
|---|---|---|---|
| 1 | 部署 `deploy_metrix_roles.sh` | **BLOCKED** | 脚本不存在:本地文件系统、仓库全部 113 个远端分支、GitHub 代码搜索都没有 |
| 2 | 确认两个 subagent | **BLOCKED** | 依赖任务 1;当前会话只加载了内置 agent,没有 `code-reviewer`、`data-auditor` |
| 3 | 参数量与显存 | 完成 | 唯一参数 1,720,574,976(头信息与 config 公式一致);最大的 arm A 约 39 GB |
| 4 | 候选可行性 | 完成,**通过** | 16 个池最小 5 个答案,没有不足 4 个的;另 20 个数据种子全部可行。另发现 Y/F token 比 1.292 超出协议 2.6 的上限 1.25 |
| 5 | “重叠度 0.2”的度量 | 完成 | 词 4-gram Jaccard,368 对跨集合模板取**最大值**,阈值 ≤ 0.25 |
| 6 | `aa0423ef` 是否含两处修正 | 完成,**已包含** | 两处都在提交里;修正前的版本从未提交,diff 按编辑命令重建 |
| 7 | 验证脚本按标记定位内联块 | 完成 | 正例通过;4 个反例中 3 个按预期失败,另一个证明旧脚本会抓错块 |
| 8 | 算力决定写入协议 | 完成 | 第 7、8、13 节写入;为消除矛盾,第 0、11 节和文件头也相应改动 |
| 9 | code-reviewer 与 data-auditor 审查 | **BLOCKED** | 依赖任务 1、2:两个 agent 不存在 |
| 10 | 埋 bug 测试 | **BLOCKED** | 依赖 code-reviewer;未建沙箱分支、未埋 bug |
| 11 | 协议第 2.5、4、5、8 节全文 | 完成 | 见文末 |

## 1. 部署

**状态:BLOCKED。** `deploy_metrix_roles.sh` 不存在,无法运行,因此没有“部署结果”部分可以记录。

查找范围:仓库根目录和用户主目录;整个文件系统;OpenMythos 全部 113 个远端分支的文件树(含 `.claude/agents/`);GitHub 代码搜索(本会话可访问的仓库)。会话可访问的仓库列表里也没有名为 metrix 的仓库。

原始输出:

````
$ cd /home/user/OpenMythos && bash deploy_metrix_roles.sh
bash: deploy_metrix_roles.sh: No such file or directory
exit 127
$ cd /home/user && bash deploy_metrix_roles.sh
bash: deploy_metrix_roles.sh: No such file or directory
exit 127
$ find / \( -path /proc -o -path /sys \) -prune -o -iname '*deploy_metrix*' -print
(find: no output = no match)
$ git fetch -q --all && git for-each-ref refs/remotes | wc -l
113
$ for every remote branch: git ls-tree -r --name-only <branch> | grep -i -E 'deploy_metrix|metrix_roles|\.claude/agents/'
branches with a match: 0
$ gh api -X GET search/code -f q='deploy_metrix_roles'
{"total_count":0,"incomplete_results":false,"items":[]}
$ gh api -X GET search/code -f q='filename:deploy_metrix_roles.sh'
{"total_count":0,"incomplete_results":false,"items":[]}
````

需要:把脚本提交到某个分支,或告诉我它的位置。

## 2. 确认 subagent

**状态:BLOCKED**(依赖任务 1)。

当前会话 Agent 工具列出的可用类型(来自本会话的工具定义,不是命令输出):`claude`、`claude-code-guide`、`Explore`、`general-purpose`、`Plan`、`statusline-setup`。**没有 `code-reviewer`,也没有 `data-auditor`。**

原始输出:

````
++ ls -la /home/user/OpenMythos/.claude /root/.claude/agents
ls: cannot access '/home/user/OpenMythos/.claude': No such file or directory
ls: cannot access '/root/.claude/agents': No such file or directory
++ ls /home/user/OpenMythos/metrix
e1-pilot
++ claude --version
2.1.322 (Claude Code)
++ set +x
````

## 3. 参数量与显存

命令(只读 `config.json` 与两个 safetensors 文件的头部 JSON,不读任何张量数据):

````
python3 metrix/e1-pilot/reports/round1/param_count.py --model-dir <Qwen3-1.7B@70d244cc 本地快照>
````

原始输出:

````
++ python3 metrix/e1-pilot/reports/round1/param_count.py --model-dir /tmp/claude-0/-home-user/b14e6790-e120-5830-986d-f23c5a9324a3/scratchpad/sg/qwen3-1.7b
config.json: {"hidden_size": 2048, "intermediate_size": 6144, "num_hidden_layers": 28, "num_attention_heads": 16, "num_key_value_heads": 8, "head_dim": 128, "vocab_size": 151936, "tie_word_embeddings": true, "torch_dtype": "bfloat16"}
header of model-00001-of-00002.safetensors: 310 tensors
header of model-00002-of-00002.safetensors: 1 tensors
tensors: 311, elements stored: 2031739904, dtypes: ['BF16']
model.embed_tokens.weight: [151936, 2048] | lm_head.weight: [151936, 2048]
tie_word_embeddings = True -> lm_head shares the embedding matrix; unique parameters = 2031739904 - 311164928 = 1720574976
config formula: embedding 151936*2048 = 311164928; per layer q 4194304 + k 2097152 + v 2097152 + o 4194304 + mlp 3*2048*6144 = 37748736 + norms 4352 = 50336000; 28 layers = 1409408000; final norm 2048; total = 1720574976
header count == config formula: True
one FP32 copy = 1720574976 * 4 B = 6882299904 B = 6.88 GB = 6.41 GiB
arm memory (parameters and optimizer state only):
  F, S, Y: weights + gradients + AdamW m + AdamW v     4 copies                             27.53 GB   25.64 GiB
  A: F + frozen FP32 base copy for the KL anchor       5 copies                             34.41 GB   32.05 GiB
  L, rank 8: frozen weights + adapters x 4             1 copy + 4 x 8716288 adapter params    7.02 GB    6.54 GiB
  L, rank 32: frozen weights + adapters x 4            1 copy + 4 x 34865152 adapter params    7.44 GB    6.93 GiB
  N: frozen weights (evaluation only)                  1 copy                                6.88 GB    6.41 GiB
transient: bf16 autocast weight copies up to 3.44 GB; FP32 logits of 4 x 128 anchor tokens 0.31 GB per model (x2 models + log-softmax copies for the KL); activations at batch 8 x <= 32 tokens are below 1 GB
upper estimate for the largest arm (A): 34.4 GB + 3.4 GB + 1.2 GB = 39.1 GB; headroom on an 80 GB A100: 40.9 GB
````

**计算过程**
- safetensors 头信息共 311 个张量、2,031,739,904 个元素。其中 `lm_head.weight` [151936, 2048] 与 `model.embed_tokens.weight` 形状相同;`config.json` 中 `tie_word_embeddings = true`,加载时二者共享,所以要训练的唯一参数是 2,031,739,904 − 311,164,928 = **1,720,574,976**。
- 独立核对(只用 config):词嵌入 151936 × 2048 = 311,164,928;每层 q 4,194,304 + k 2,097,152 + v 2,097,152 + o 4,194,304 + MLP 3 × 2048 × 6144 = 37,748,736 + 归一化 4,352 = 50,336,000;28 层 = 1,409,408,000;最终归一化 2,048;合计 1,720,574,976,与头信息一致。
- FP32 一份 = 1,720,574,976 × 4 B = 6,882,299,904 B = **6.88 GB**(6.41 GiB)。

| arm | 份数 | 参数与优化器状态 |
|---|---|---:|
| F、S、Y | 权重 + 梯度 + AdamW m + AdamW v = 4 份 | 27.53 GB |
| A | 上面 4 份 + 冻结的 FP32 base 副本 = 5 份 | **34.41 GB** |
| L(秩 8) | 冻结权重 1 份 + 适配器 8,716,288 × 4 份 | 7.02 GB |
| L(秩 32) | 冻结权重 1 份 + 适配器 34,865,152 × 4 份 | 7.44 GB |
| N | 1 份 | 6.88 GB |

- 临时开销:bf16 autocast 的权重副本 ≤ 3.44 GB;A 的锚文本 logits(4 × 128 token × 151,936 词表,FP32)每个模型 0.31 GB,两个模型加 log-softmax 副本约 1.2 GB;批次 8 × ≤ 32 token 的激活 < 1 GB。
- 最大的 arm A 上界约 34.4 + 3.4 + 1.2 ≈ **39 GB**,A100 80GB 余量约 41 GB。
- 原协议第 0 节写的“约 4 × 6.9 GB”只覆盖了 F,没有算 A 的 base 副本;本轮已在第 7 节写入完整估计。

## 4. 候选可行性

四重约束(协议 2.2、2.5):干扰项与真实答案**同 relation、同 stratum、同暴露类别(learned / unread)、同答案 token 数对**(陈述句语境带前导空格的 token 数,问答语境 assistant 回合开头的 token 数)。只用分词器,在内存里生成名字、只打印计数,不写任何数据文件,不构造 TEST 问句。

命令:

````
python3 metrix/e1-pilot/reports/round1/candidate_feasibility.py --manifest metrix/e1-pilot/DATA_MANIFEST.json \
    --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc 本地快照> --extra-seeds 20
````

原始输出:

````
++ /tmp/claude-0/-home-user/b14e6790-e120-5830-986d-f23c5a9324a3/scratchpad/venv/bin/python -B metrix/e1-pilot/reports/round1/candidate_feasibility.py --manifest metrix/e1-pilot/DATA_MANIFEST.json --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --tokenizer-dir /tmp/claude-0/-home-user/b14e6790-e120-5830-986d-f23c5a9324a3/scratchpad/sg/qwen3-1.7b --extra-seeds 20
DATA_SEED 20261110: per cell
  {"cell": "capital/natural", "entity_draws": 28, "target_pair": "3/3", "target_share": 0.352, "answer_draws": 84, "filled": true}
  {"cell": "capital/random", "entity_draws": 20, "target_pair": "5/5", "target_share": 0.415, "answer_draws": 52, "filled": true}
  {"cell": "currency/natural", "entity_draws": 31, "target_pair": "3/3", "target_share": 0.338, "answer_draws": 82, "filled": true}
  {"cell": "currency/random", "entity_draws": 20, "target_pair": "6/6", "target_share": 0.445, "answer_draws": 46, "filled": true}
  {"cell": "founder/natural", "entity_draws": 30, "target_pair": "3/3", "target_share": 0.355, "answer_draws": 81, "filled": true}
  {"cell": "founder/random", "entity_draws": 21, "target_pair": "5/5", "target_share": 0.443, "answer_draws": 45, "filled": true}
  {"cell": "river/natural", "entity_draws": 34, "target_pair": "3/3", "target_share": 0.355, "answer_draws": 89, "filled": true}
  {"cell": "river/random", "entity_draws": 20, "target_pair": "6/6", "target_share": 0.472, "answer_draws": 42, "filled": true}
facts: 160, distinct strings: 320 of 320
pools under the four constraints (relation, stratum, exposure, token pair): 16
  capital  natural learned pair 3/3: 15 answers -> 14 possible distractors per fact (3 needed)
  capital  natural unread  pair 3/3:  5 answers ->  4 possible distractors per fact (3 needed)
  capital  random  learned pair 5/5: 15 answers -> 14 possible distractors per fact (3 needed)
  capital  random  unread  pair 5/5:  5 answers ->  4 possible distractors per fact (3 needed)
  currency natural learned pair 3/3: 15 answers -> 14 possible distractors per fact (3 needed)
  currency natural unread  pair 3/3:  5 answers ->  4 possible distractors per fact (3 needed)
  currency random  learned pair 6/6: 15 answers -> 14 possible distractors per fact (3 needed)
  currency random  unread  pair 6/6:  5 answers ->  4 possible distractors per fact (3 needed)
  founder  natural learned pair 3/3: 15 answers -> 14 possible distractors per fact (3 needed)
  founder  natural unread  pair 3/3:  5 answers ->  4 possible distractors per fact (3 needed)
  founder  random  learned pair 5/5: 15 answers -> 14 possible distractors per fact (3 needed)
  founder  random  unread  pair 5/5:  5 answers ->  4 possible distractors per fact (3 needed)
  river    natural learned pair 3/3: 15 answers -> 14 possible distractors per fact (3 needed)
  river    natural unread  pair 3/3:  5 answers ->  4 possible distractors per fact (3 needed)
  river    random  learned pair 6/6: 15 answers -> 14 possible distractors per fact (3 needed)
  river    random  unread  pair 6/6:  5 answers ->  4 possible distractors per fact (3 needed)
minimum pool size: 5; pools with fewer than 4 candidates: 0 []
(relation, stratum, exposure) groups split over more than one token pair: 0
boundary: TRAIN statements whose tokens != prefix + ' answer' + rest: 0 of 160
boundary: DEV prompts whose tokens != chat(question) + answer tokens: 0 of 320
token count per pass (statements + endoftext): train_F 1889, train_Y 2440, ratio Y/F 1.292 (protocol 2.6: [0.80, 1.25])
robustness over 20 other data seeds: all cells filled 20/20, minimum pool 5, largest answer draws 139 (limit 20000), all strings distinct 20/20
````

**结论**
- 8 个 cell 全部填满 20 个答案;按四重约束分成 16 个池:learned 池各 15 个答案,unread 池各 5 个答案。
- **最小池 5 个答案**,即每条 fact 至少有 4 个可选干扰项(需要 3 个)。**不足 4 个候选的池:0 个。**
- 答案边界的切分一致:160 条 TRAIN 陈述句、320 个 DEV 问答提示里,“整句切分”与“前缀 + 答案分别切分”完全相同,候选打分时答案 token 不会和前文粘连。
- 换 20 个其它数据种子:全部填满,最小池仍是 5,最多抽样 139 次(上限 20,000)。

**本任务顺带发现的问题(未在本轮修改,需要协议改动)**
1. **Y/F token 比 = 1.292,超出协议 2.6 节规定的 [0.80, 1.25]。** 按协议自己的规则,Y 语料会直接触发 IMPLEMENTATION_FAIL。原因是 Y 每条 fact 两句话(各带一个结束符),比 F 的一句长。需要改模板或改区间,二选一。
2. **`aa0423ef` 没有把名字生成的三个细节写死**:随机流的 purpose 字符串、“前 400 个候选”的统计方法、接受阶段是否重新开始同一个流。脚本按一种合理读法实现,结论(可行)对读法不敏感(20 个种子都可行),但只凭协议还不能逐字节复现数据。
3. **arm A 的暴露匹配没有被检查覆盖**:协议要求 learned 答案在每个 arm 的训练语料里恰好出现 1 次,但 L3 只检查 unread 字符串是否出现在锚文本里;learned 答案若碰巧出现在锚文本里,A 的暴露就不再是 1 次。建议把 L3 扩展到 learned 答案在锚文本中的出现次数,上限 0。

## 5. “重叠度 0.2”的度量

命令(只读 `SPLIT_MANIFEST.json`,独立重算):

````
python3 metrix/e1-pilot/reports/round1/template_overlap.py --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json
````

原始输出:

````
++ python3 metrix/e1-pilot/reports/round1/template_overlap.py --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json
templates: 32 | per set: {'TRAIN': 4, 'DEV': 8, 'TEST': 12, 'Y': 8}
stored normalized_sha256 reproduced: True []
L1: hashes shared across sets: 0 (limit 0) -> PASS
L2: word 4-gram Jaccard over 368 cross-set pairs: max 0.2000, mean 0.000543, pairs > 0: 1, limit (max) 0.25 -> PASS
  0.2000  capital.TRAIN.1 'the capital of <entity> is <answer>' (3 grams)  vs  capital.DEV.1 'what is the capital of <entity>' (3 grams); shared: [('the', 'capital', 'of', '<entity>')]
templates with fewer than 4 words (no 4-gram, Jaccard 0 by definition): ['founder.DEV.1']
  sensitivity, word 3-grams: max 0.3333, mean 0.002053, pairs > 0: 4
  sensitivity, word 2-grams: max 0.4286, mean 0.013313, pairs > 0: 37
````

**说明**
- **度量**:泄漏检查 L2。每个模板先归一化(`{E}` → `<entity>`、`{A}` → `<answer>`、小写、非 `[a-z0-9<> ]` 字符换成空格、合并空格),切成**词级 4-gram 集合**,两个模板的重叠度 = 交集大小 / 并集大小(Jaccard)。
- **比较范围**:来自不同集合(TRAIN、DEV、TEST、Y)的每一对模板,共 368 对;同一集合内部不比。
- **取最大值,不是均值**。0.2 是这 368 对里的最大值;均值 0.000543,只有 1 对大于 0。
- **阈值**:最大值 ≤ **0.25**(写在 `SPLIT_MANIFEST.json` 的 `L2_template_ngram.limit`)。0.2 ≤ 0.25,通过。
- 0.2 的来源:`capital.TRAIN.1` “the capital of <entity> is <answer>” 与 `capital.DEV.1` “what is the capital of <entity>” 各有 3 个 4-gram,共享 1 个(“the capital of <entity>”,即关系本身的说法),1 / 5 = 0.2。
- **局限**:不足 4 个词的模板(`founder.DEV.1` “who founded <entity>”)没有 4-gram,重叠度按定义为 0,L2 对它没有约束力;改用 3-gram 时最大值 0.333、2-gram 时 0.429,都会超过 0.25。模板之间完全相同的情况由 L1(归一化哈希)单独保证。

## 6. `aa0423ef` 是否已包含两处修正

**结论:已包含。** 这里的“两处修正”指 2026-11-10 提交前做的两处改动:
1. 协议正文里两个原样写出的特殊 token(训练输入的 `<|endoftext|>`、生成停止符 `<|im_end|>`)改为文字描述并写明 id(151643、151645);
2. `SUBMISSION_NOTE.md` 里那条“除 `metrix/` 外无改动”的 git 校验命令改为可在任意目录运行、并显式比较到 `HEAD`。

命令与原始输出(提交里的内容):

````
++ head -12
++ git show --stat '--format=%H %ci%n%s' aa0423ef
aa0423ef644234b0f523674d0067b55ec5533913 2026-11-10 15:48:18 +0000
metrix: E1-PILOT protocol for review (authoring only)

 metrix/e1-pilot/DATA_MANIFEST.json    | 251 +++++++++++++++
 metrix/e1-pilot/METRIX_E1_PROTOCOL.md | 586 ++++++++++++++++++++++++++++++++++
 metrix/e1-pilot/SEARCH_SPACE.json     | 204 ++++++++++++
 metrix/e1-pilot/SPLIT_MANIFEST.json   | 379 ++++++++++++++++++++++
 metrix/e1-pilot/SUBMISSION_NOTE.md    |  81 +++++
 5 files changed, 1501 insertions(+)
++ git show aa0423ef:metrix/e1-pilot/METRIX_E1_PROTOCOL.md
++ grep -n -E '训练输入|最多 16 个新 token'
33:| 训练输入 | 原始陈述句文本,后接 endoftext 特殊 token(id 151643);不用 chat template,不加 system prompt |
187:**Free-generation exact match(次指标)**:对同一 `chat(q)` 做贪心解码,最多 16 个新 token,遇 im_end 特殊 token(id 151645)停。归一化:取第一行,去首尾空白,去开头的 “the ”(不分大小写),去结尾的 `. , ; : ! ?`,casefold。`EM(f, q) = 1[norm(output) == norm(a_f)]`,聚合方式同上。
++ grep -c -F '<|'
++ git show aa0423ef:metrix/e1-pilot/METRIX_E1_PROTOCOL.md
0
++ grep -n -F 'diff --stat'
++ git show aa0423ef:metrix/e1-pilot/SUBMISSION_NOTE.md
66:git -C "$(git rev-parse --show-toplevel)" diff --stat 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc HEAD -- . ':(exclude)metrix'    # 应为空:除 metrix/ 外没有改动
++ set +x
````

相关 diff:修正前的版本**从未提交**,所以 git 里没有可比较的旧提交。下面的“修正前”文件是把 `aa0423ef` 的这几行按当时的编辑命令反向替换得到的,只替换了这三处:

```diff
--- METRIX_E1_PROTOCOL.md (before the fix, never committed)
+++ METRIX_E1_PROTOCOL.md @ aa0423ef
@@ -30,7 +30,7 @@
 | 分词器 | 同一仓库、同一 revision |
 | 结构 | Qwen3ForCausalLM,28 层,hidden 2048,约 1.72e9 参数;没有循环核心,“depth” 不适用 |
 | 精度 | 权重 FP32;训练用 bf16 autocast(主权重与优化器状态 FP32);评测 FP32、不用 autocast |
-| 训练输入 | 原始陈述句文本 + `<|endoftext|>`(id 151643);不用 chat template,不加 system prompt |
+| 训练输入 | 原始陈述句文本,后接 endoftext 特殊 token(id 151643);不用 chat template,不加 system prompt |
 | 问答输入 | 该 revision 的 chat template,单个 user 回合,`add_generation_prompt=true`,`enable_thinking=false`,不加 system prompt |
 | 库版本 | torch 2.11.0,transformers 5.22.2;实际版本写入实验记录,不一致即 BLOCKED |
 
@@ -184,7 +184,7 @@
 Acc_CB(arm) = (1/120) · Σ_{f ∈ learned} CB(f)
 ```
 
-**Free-generation exact match(次指标)**:对同一 `chat(q)` 做贪心解码,最多 16 个新 token,遇 `<|im_end|>` 停。归一化:取第一行,去首尾空白,去开头的 “the ”(不分大小写),去结尾的 `. , ; : ! ?`,casefold。`EM(f, q) = 1[norm(output) == norm(a_f)]`,聚合方式同上。
+**Free-generation exact match(次指标)**:对同一 `chat(q)` 做贪心解码,最多 16 个新 token,遇 im_end 特殊 token(id 151645)停。归一化:取第一行,去首尾空白,去开头的 “the ”(不分大小写),去结尾的 `. , ; : ! ?`,casefold。`EM(f, q) = 1[norm(output) == norm(a_f)]`,聚合方式同上。
 
 **全对率(次指标,只报告)**:`AllCorrect(f) = Π_{q} correct(f, q)`。
 
--- SUBMISSION_NOTE.md (before the fix, never committed)
+++ SUBMISSION_NOTE.md @ aa0423ef
@@ -63,7 +63,7 @@
 print('inline copy identical')
 PY
 # 模板哈希与 L1、L2 可重算:归一化规则见 SPLIT_MANIFEST.json: template_freeze
-git diff --stat 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc -- . ':!metrix'    # 应为空
+git -C "$(git rev-parse --show-toplevel)" diff --stat 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc HEAD -- . ':(exclude)metrix'    # 应为空:除 metrix/ 外没有改动
 ```
 
 ## 6. Agent 自检清单
```

## 7. 验证脚本按标记定位内联块

改动:
- 协议第 7 节的 `SEARCH_SPACE.json` 内联副本前后加了两个标记:`<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->` 与 `<!-- END INLINE COPY: SEARCH_SPACE.json -->`。
- `SUBMISSION_NOTE.md` 中的验证脚本改为:两个标记必须各出现恰好一次、顺序正确;两者之间必须恰好是一个 json 代码块;该块能被解析,且与 `SEARCH_SPACE.json` 逐字节相同。不再用正则抓文档里的第一个 json 块。

运行方式:脚本原样从 `SUBMISSION_NOTE.md` 抽出;先在真实文件上运行,再在 4 个临时副本上做反例测试。原始输出:

````
== the script as committed in SUBMISSION_NOTE.md:
import json
BEGIN = '<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->'
END = '<!-- END INLINE COPY: SEARCH_SPACE.json -->'
doc = open('METRIX_E1_PROTOCOL.md', encoding='utf-8').read()
assert doc.count(BEGIN) == 1 and doc.count(END) == 1, 'need exactly one BEGIN and one END marker'
i, j = doc.index(BEGIN) + len(BEGIN), doc.index(END)
assert i < j, 'END marker before BEGIN marker'
inner = doc[i:j]
head, tail = '\n```json\n', '```\n'
assert inner.startswith(head) and inner.endswith(tail), 'the marked region must be exactly one fenced json block'
block = inner[len(head):-len(tail)]
assert '```' not in block, 'more than one fenced block between the markers'
json.loads(block)
assert block == open('SEARCH_SPACE.json', encoding='utf-8').read(), 'inline copy differs from SEARCH_SPACE.json'
print('inline copy identical (marked block)')
== real files (metrix/e1-pilot):
json ok
inline copy identical (marked block)
exit 0
== negative test: decoy_first
inline copy identical (marked block)
exit 0
== negative test: altered_block
AssertionError: inline copy differs from SEARCH_SPACE.json
exit 1
== negative test: missing_end
AssertionError: need exactly one BEGIN and one END marker
exit 1
== negative test: duplicate_begin
AssertionError: need exactly one BEGIN and one END marker
exit 1
== old script (first json block in the document) on the decoy_first copy:
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: inline copy differs
````

**结果**:真实文件通过。`decoy_first`(文档前部另插一个 json 块)新脚本仍正确比较标记内的块;旧脚本在同一副本上比较的是插入的那块,误报不一致。`altered_block`、`missing_end`、`duplicate_begin` 三种情况新脚本都报错退出(exit 1)。

## 8. 算力决定写入协议

决定内容:一张 NVIDIA A100 80GB;GPU wall-clock 上限 4 小时;GPU 型号写死。写入位置:
- **第 7 节**:训练契约表新增“硬件(已决定)”“GPU wall-clock 上限(已决定)”两行;新增“算力决定与显存估计”一段(任务 3 的数字);`SEARCH_SPACE.json` 的 `training_contract` 同步加入 `hardware`、`wall_clock_limit_gpu_hours: 4`、`wall_clock_scope`,内联副本随之更新并通过任务 7 的校验。
- **第 8 节**:执行顺序第 1 步加入 GPU 检查(设备名以 `NVIDIA A100` 开头且显存 ≥ 79 GiB,否则 BLOCKED);新增“算力边界”一段(第 3–8 步在同一型号上执行,累计 ≤ 4 小时,超过按 ST7)。
- **第 13 节**:待定项从 3 项减为 2 项;原第 3 项改为“已决定,不再待定”。
- **为消除矛盾而一并改动(不在指定的三节内)**:第 0 节“环境要求”原写“≥ 40 GB 的 GPU 或 ≥ 48 GB 内存的 CPU”,与决定冲突,已改写;第 11 节 ST7 原指向“第 13 节第 3 项”,改为指向第 7 节的 4 小时;文件头的待定项计数;`SUBMISSION_NOTE.md` 的待定项清单与自检清单。

**需要确认的两点**
1. **型号写死的粒度**:A100 80GB 有 SXM4 与 PCIe 两种。检查条件接受两者,但要求同一次 Pilot 内所有运行的设备名完全相同。如果要锁定其中一种,请指明。
2. **4 小时是否够用**:没有实测(本轮禁止运行模型)。按 A100 的理论吞吐粗算,单步全参训练约 1.3 TFLOP 计算加约 48 GB 的优化器显存读写,约 0.05–0.1 秒,300 步约半分钟;加上加载与评测,30 次运行估计 1–2 小时。这只是估计,实际以第一次运行的计时为准。

一致性检查(命令与原始输出):

````
++ grep -n -E '40 GB|48 GB|第 13 节第 3 项|3 项|CPU wall-clock' metrix/e1-pilot/METRIX_E1_PROTOCOL.md metrix/e1-pilot/SUBMISSION_NOTE.md
metrix/e1-pilot/METRIX_E1_PROTOCOL.md:607:**已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。
metrix/e1-pilot/SUBMISSION_NOTE.md:44:(原第 3 项“CPU wall-clock 上限”已由 Metrix 指令 2026-11-12 决定:一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,CPU 不做模型计算;不再待定。)
++ grep -n -E A100 metrix/e1-pilot/METRIX_E1_PROTOCOL.md
10:Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 只剩第 13 节的 2 项。
40:**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。
255:| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测;同一次 Pilot 内每次运行记录的 `torch.cuda.get_device_name(0)` 必须相同 |
308:      "gpu": "NVIDIA A100 80GB",
311:      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
312:      "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
490:   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8);从此刻第一次加载模型起累计 GPU wall-clock。
499:**算力边界**:第 3–8 步全部在同一型号的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。
607:**已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。
++ grep -c PENDING_REVIEW_GATE metrix/e1-pilot/METRIX_E1_PROTOCOL.md
2
++ python3 -c '
import json; t = json.load(open('\''metrix/e1-pilot/SEARCH_SPACE.json'\''))['\''training_contract'\'']
print(json.dumps({k: t[k] for k in ('\''hardware'\'', '\''wall_clock_limit_gpu_hours'\'', '\''wall_clock_scope'\'')}, ensure_ascii=False, indent=1))'
{
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
}
++ set +x
````

本次改动的完整 diff(协议、提交说明、`SEARCH_SPACE.json`):

```diff
diff --git a/metrix/e1-pilot/METRIX_E1_PROTOCOL.md b/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
index 8ef084ac..cf698f6e 100644
--- a/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
+++ b/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
@@ -7,7 +7,7 @@
 | 本文件的作用 | 执行 E1-PILOT 只需要本文件、同目录三个 JSON,以及第 0 节固定的外部来源 |
 | 本文件不包含 | 任何训练、评测结果或结论;任何 TEST 数据 |
 
-Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;PENDING_REVIEW_GATE 只剩第 13 节的 3 项。
+Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 只剩第 13 节的 2 项。
 
 ## 0. 标识、出处与环境
 
@@ -37,7 +37,7 @@ Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两
 **种子**:`DATA_SEED = 20261110`,`CANDIDATE_SEED = 20261111`,`TRAIN_SEEDS = [101, 202, 303]`,`BOOTSTRAP_SEED = 20261112`。所有随机数都来自
 `random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))`,`purpose` 在各处写明。结果不好不得换种子。
 
-**环境要求**:全参微调(F、A、S、Y)在 FP32 下需要约 4 × 6.9 GB(权重、梯度、AdamW 两个动量)再加激活,所以执行机器必须有 ≥ 40 GB 显存的单张 GPU,或 ≥ 48 GB 内存的 CPU 机器。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。
+**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。
 
 **哈希**:JSON 的规范化序列为 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` 的 UTF-8 字节;JSONL 为每行一个规范化对象、以 `\n` 连接并以一个 `\n` 结尾;算法 SHA-256。`byte_sha256` 是文件原样字节的哈希,`canonical_sha256` 是解析后内容的规范化序列的哈希;后者标识内容,前者标识文件。
 
@@ -252,11 +252,19 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
 | checkpoint | 每次训练只保留并评测最终 checkpoint;中间 checkpoint 不用于任何判断 |
 | early stopping | 不允许 |
 | Y 的训练量 | 对它的 240 句读 20 遍,batch 16,同为 300 步;token 数比见 2.6 |
+| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测;同一次 Pilot 内每次运行记录的 `torch.cuda.get_device_name(0)` 必须相同 |
+| GPU wall-clock 上限(已决定) | 4 小时:从第一次加载模型到 TEST 评测结束的累计 GPU 时间;超过即 ST7 |
 
 锚文本的前向计算是 A 的额外算力,单独记入 compute accounting,不算事实 token。
 
-**搜索空间(与 `SEARCH_SPACE.json` 逐字一致)**
+**算力决定与显存估计**(决定来源:Metrix 指令 Round 1 第 8 项,2026-11-12;参数量由 `config.json` 与 safetensors 头信息核实,见 `reports/ROUND1_REPORT.md` 任务 3):
+- 唯一参数 1,720,574,976(词嵌入与输出层共享;文件里另存的 `lm_head.weight` 在加载时与词嵌入绑定)。FP32 一份 = 6.88 GB。
+- F、S、Y:权重 + 梯度 + AdamW 两个动量 = 4 份 = 27.5 GB。A:再加冻结的 base 副本 = 5 份 = 34.4 GB。L:冻结权重 6.88 GB + 适配器(秩 32 时 3,486 万参数 × 4 份)0.56 GB。N:6.88 GB。
+- 另加 bf16 autocast 的权重副本 ≤ 3.4 GB,A 的锚文本 logits(4 × 128 token、两个模型)约 1.2 GB;批次 8 × ≤ 32 token 的激活 < 1 GB。最大的 arm A 合计约 39 GB,在 80 GB 上余量约 41 GB。
 
+**搜索空间(与 `SEARCH_SPACE.json` 逐字一致;校验只比较两个标记之间的那一个 json 块)**
+
+<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->
 ```json
 {
   "protocol": "METRIX-E1-PILOT",
@@ -295,7 +303,17 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
     "precision": "bfloat16 autocast with float32 master weights",
     "checkpoint_policy": "only the final checkpoint of a run is kept and evaluated; no intermediate checkpoint is used for anything",
     "early_stopping": "not allowed",
-    "primary_training_token_budget": "20 passes over the 120 TRAIN statements for F, L, A and S (identical statements up to the S permutation); Y: 20 passes over its 240 sentences with batch 16 (300 steps); Y tokens / F tokens must lie in [0.80, 1.25]"
+    "primary_training_token_budget": "20 passes over the 120 TRAIN statements for F, L, A and S (identical statements up to the S permutation); Y: 20 passes over its 240 sentences with batch 16 (300 steps); Y tokens / F tokens must lie in [0.80, 1.25]",
+    "hardware": {
+      "gpu": "NVIDIA A100 80GB",
+      "count": 1,
+      "decided": "Metrix instruction, round 1 item 8, 2026-11-12",
+      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
+      "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
+      "cpu_use": "data generation, leakage checks and tokenizer checks only"
+    },
+    "wall_clock_limit_gpu_hours": 4,
+    "wall_clock_scope": "cumulative GPU wall-clock from the first model load to the end of the TEST evaluation; above the limit: ST7"
   },
   "arms": {
     "N": {
@@ -463,11 +481,13 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
   }
 }
 ```
+<!-- END INLINE COPY: SEARCH_SPACE.json -->
 
 ## 8. Gate 0 — Pipeline Qualification(只用 TRAIN 与 DEV)
 
 **执行顺序**(每一步的停止规则见第 11 节):
-1. 记录环境与出处;生成除 TEST 以外的数据,把哈希写入两个 manifest 并提交。
+1. 记录环境与出处;在 CPU 上生成除 TEST 以外的数据,把哈希写入两个 manifest 并提交。
+   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8);从此刻第一次加载模型起累计 GPU wall-clock。
 2. 运行泄漏检查。
 3. 评测 N:TRAIN 闭卷、DEV-QA、general DEV。
 4. F 的 6 个配置(种子 101)→ 选定 → 用选定配置检查阳性对照。
@@ -476,6 +496,8 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
 7. 按下表判定 Gate 0。
 8. Gate 0 通过后:提交冻结记录(选定配置、数据哈希、checkpoint 哈希)→ 生成 `test_qa.jsonl` 与 `general_test.jsonl` → 对 TEST 运行 L3–L5 → **TEST 只评一次**。
 
+**算力边界**:第 3–8 步全部在同一型号的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。
+
 **Gate 0 门槛(全部为数值;“seed-average” 见第 6 节)**
 
 | 编号 | 条件 |
@@ -563,7 +585,7 @@ Compute accounting 的算法:训练 FLOPs ≈ 6 · P · T,前向 FLOPs ≈ 2 ·
 | ST4 | Y 不满足 G0.7 | Style-only 泄漏:停;不生成 TEST |
 | ST5 | S 不满足 G0.6 | Shuffled control 出现真实映射提升:停;不生成 TEST |
 | ST6 | 任一次训练或评测出现非有限值 | 停该次;若发生在选定配置或对照上,IMPLEMENTATION_FAIL |
-| ST7 | 累计 wall-clock 超过上限(第 13 节第 3 项) | 停并报告进度;转 GPU 或降级需 Owner 决定,不得静默继续 |
+| ST7 | 累计 GPU wall-clock 超过 4 小时(第 7 节) | 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续 |
 | ST8 | 环境不满足第 0 节 | BLOCKED |
 
 ## 12. Out of Scope
@@ -575,12 +597,13 @@ Compute accounting 的算法:训练 FLOPs ≈ 6 · P · T,前向 FLOPs ≈ 2 ·
 - NONE / 拒答校准。
 - 探索沙盒(SANDBOX)。
 
-## 13. Open Questions for Review Gate(PENDING_REVIEW_GATE 仅此 3 项)
+## 13. Open Questions for Review Gate(PENDING_REVIEW_GATE 仅此 2 项)
 
 | # | 字段 | PROPOSED | 理由 |
 |---|---|---|---|
 | 1 | E1-V1 目标 fact 数 | 320(240 learned + 80 unread),并在 Pilot 后按 G0.10 的公式重算 | 若配对差的标准差为 0.5,检出 0.10 的差需要约 196 条 learned fact;取 240 留余量 |
 | 2 | general-damage non-inferiority margin | dNLL ≤ +0.03(约 +3% PPL) | 与本仓库此前实验使用的容忍幅度一致;Pilot 里 general damage 只报告,不进门槛 |
-| 3 | CPU wall-clock 上限 | 内存 < 48 GB 的 CPU 机器上限为 0(不执行全参微调的 arm);整个 Pilot 在 ≥ 40 GB 显存的单张 GPU 上执行,GPU wall-clock 上限 4 小时 | FP32 全参微调需要约 27.5 GB 加激活(第 0 节的算术);超过上限按 ST7 处理 |
+
+**已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。
 
 其余可执行参数都已写死或标为 PROPOSED;Review Gate 可以改动一次,PROTOCOL_FROZEN 之后任何门槛、split 规则、指标、搜索预算或 Gate 定义的改动都必须开新协议版本。
diff --git a/metrix/e1-pilot/SEARCH_SPACE.json b/metrix/e1-pilot/SEARCH_SPACE.json
index 93f10a2e..00221380 100644
--- a/metrix/e1-pilot/SEARCH_SPACE.json
+++ b/metrix/e1-pilot/SEARCH_SPACE.json
@@ -35,7 +35,17 @@
     "precision": "bfloat16 autocast with float32 master weights",
     "checkpoint_policy": "only the final checkpoint of a run is kept and evaluated; no intermediate checkpoint is used for anything",
     "early_stopping": "not allowed",
-    "primary_training_token_budget": "20 passes over the 120 TRAIN statements for F, L, A and S (identical statements up to the S permutation); Y: 20 passes over its 240 sentences with batch 16 (300 steps); Y tokens / F tokens must lie in [0.80, 1.25]"
+    "primary_training_token_budget": "20 passes over the 120 TRAIN statements for F, L, A and S (identical statements up to the S permutation); Y: 20 passes over its 240 sentences with batch 16 (300 steps); Y tokens / F tokens must lie in [0.80, 1.25]",
+    "hardware": {
+      "gpu": "NVIDIA A100 80GB",
+      "count": 1,
+      "decided": "Metrix instruction, round 1 item 8, 2026-11-12",
+      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
+      "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
+      "cpu_use": "data generation, leakage checks and tokenizer checks only"
+    },
+    "wall_clock_limit_gpu_hours": 4,
+    "wall_clock_scope": "cumulative GPU wall-clock from the first model load to the end of the TEST evaluation; above the limit: ST7"
   },
   "arms": {
     "N": {
diff --git a/metrix/e1-pilot/SUBMISSION_NOTE.md b/metrix/e1-pilot/SUBMISSION_NOTE.md
index 1dba0897..8d19ac19 100644
--- a/metrix/e1-pilot/SUBMISSION_NOTE.md
+++ b/metrix/e1-pilot/SUBMISSION_NOTE.md
@@ -33,15 +33,15 @@
 | I 复现容差数值化 | 第 8 节 G0.8 |
 | J Git 出处 | 第 0 节 |
 | K 规范化哈希 | 第 0 节;两个 manifest 的 `hashing` |
-| L PENDING 只剩 3 项 | 第 13 节 |
+| L PENDING 只剩 2 项(算力已于 2026-11-12 决定) | 第 7、8、13 节 |
 
 模型:Project Owner 于 2026-11-10 指定 `Qwen/Qwen3-1.7B`(revision 见协议第 0 节),因此不是待定项。
 
-## 3. 需要 Review Gate 拍板的字段(PENDING_REVIEW_GATE,共 3 项)
+## 3. 需要 Review Gate 拍板的字段(PENDING_REVIEW_GATE,共 2 项)
 
 1. **E1-V1 目标 fact 数** — PROPOSED:320(240 learned + 80 unread),Pilot 后按 G0.10 的公式重算。理由:配对差标准差取 0.5 时,检出 0.10 的差约需 196 条 learned fact。
 2. **general-damage non-inferiority margin** — PROPOSED:dNLL ≤ +0.03(约 +3% PPL)。理由:与本仓库此前使用的容忍幅度一致;Pilot 中只报告。
-3. **CPU wall-clock 上限** — PROPOSED:内存 < 48 GB 的 CPU 机器上限为 0;整个 Pilot 在 ≥ 40 GB 显存的单张 GPU 上执行,上限 4 小时。理由:FP32 全参微调需要约 27.5 GB 加激活。
+(原第 3 项“CPU wall-clock 上限”已由 Metrix 指令 2026-11-12 决定:一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,CPU 不做模型计算;不再待定。)
 
 ## 4. Reviewer 应重点看的三处
 
@@ -54,13 +54,23 @@
 ```bash
 cd metrix/e1-pilot
 python3 -c "import json;[json.load(open(f)) for f in ('DATA_MANIFEST.json','SPLIT_MANIFEST.json','SEARCH_SPACE.json')];print('json ok')"
-# 内联副本与 SEARCH_SPACE.json 一致
+# 内联副本与 SEARCH_SPACE.json 一致:只认两个标记之间的那一个 json 块,不抓文档里第一个 json 块
 python3 - <<'PY'
-import re
+import json
+BEGIN = '<!-- BEGIN INLINE COPY: SEARCH_SPACE.json -->'
+END = '<!-- END INLINE COPY: SEARCH_SPACE.json -->'
 doc = open('METRIX_E1_PROTOCOL.md', encoding='utf-8').read()
-block = re.search(r"```json\n(.*?)```", doc, re.S).group(1)
-assert block == open('SEARCH_SPACE.json', encoding='utf-8').read(), 'inline copy differs'
-print('inline copy identical')
+assert doc.count(BEGIN) == 1 and doc.count(END) == 1, 'need exactly one BEGIN and one END marker'
+i, j = doc.index(BEGIN) + len(BEGIN), doc.index(END)
+assert i < j, 'END marker before BEGIN marker'
+inner = doc[i:j]
+head, tail = '\n```json\n', '```\n'
+assert inner.startswith(head) and inner.endswith(tail), 'the marked region must be exactly one fenced json block'
+block = inner[len(head):-len(tail)]
+assert '```' not in block, 'more than one fenced block between the markers'
+json.loads(block)
+assert block == open('SEARCH_SPACE.json', encoding='utf-8').read(), 'inline copy differs from SEARCH_SPACE.json'
+print('inline copy identical (marked block)')
 PY
 # 模板哈希与 L1、L2 可重算:归一化规则见 SPLIT_MANIFEST.json: template_freeze
 git -C "$(git rev-parse --show-toplevel)" diff --stat 61d3c76705b28cc2ee334abc5bf1baaac4fc30dc HEAD -- . ':(exclude)metrix'    # 应为空:除 metrix/ 外没有改动
@@ -77,5 +87,5 @@ git -C "$(git rev-parse --show-toplevel)" diff --stat 61d3c76705b28cc2ee334abc5b
 - [x] Gate 0 全部门槛为数字,非描述。
 - [x] Failure taxonomy 为固定集合,含升级规则。
 - [x] `SEARCH_SPACE.json` 与文档内联副本一致。
-- [x] PENDING_REVIEW_GATE 项为 3,全部落在允许列表内。
+- [x] PENDING_REVIEW_GATE 项为 2,全部落在允许列表内。
 - [x] 本文件列出:改了哪些文件、哪些字段需要 Review Gate 拍板、Reviewer 应重点看哪三处。
```

## 9. code-reviewer 与 data-auditor 审查

**状态:BLOCKED。** 两个 agent 都不存在(见任务 1、2),无法调用,没有审查输出可以记录。

可替代的做法:本会话有内置的通用 agent 和 `code-review` 技能,但用它们审查不等于用 Metrix 定义的这两个角色审查,所以本轮没有擅自替代。部署脚本到位后可直接补做。

## 10. 埋 bug 测试

**状态:BLOCKED。** 这一项要由 code-reviewer 审查,而它不存在。
- 没有新建沙箱分支,也没有埋任何 bug。
- 因此本报告**不列出具体的埋入方式**:如果现在把“打算怎么埋”写进仓库,等 code-reviewer 部署后再做这项测试时,它可能读到这份报告,测试就失效了。
- 部署到位后的做法:新建一个名字与用途无关的分支,把指定的 4 个 bug(arm A 的 base 未冻结、聚合改用 median、DEV 与 TEST 混用、随机种子未固定)埋进去,只把该分支交给 code-reviewer;审查结束后,再把埋入清单和检出结果写进报告。

## 11. 协议第 2.5、4、5、8 节全文(本次提交后的版本)

#### 2.5 候选(4-way,生成数据时冻结)

- 每条 fact 4 个候选:1 个真实答案 + 3 个干扰项。
- **干扰项的池**:同 relation、同 stratum、同暴露类别(learned 或 unread)的其它 fact 的答案。
- 抽取:用 `rng_rule(CANDIDATE_SEED, "cand:<fact_id>")` 不放回抽 3 个并决定 4 个候选的顺序;不得重复。
- 一条 fact 的候选表对它的全部模板、全部 split、全部 arm 相同。
- **暴露匹配**:learned fact 的每个候选在 F、L、A、S、Y 的训练语料里都恰好出现 1 次;unread fact 的每个候选出现 0 次。因此“见过这个词”不能用来选出正确项。
- 完整候选映射的 `canonical_sha256` 写入 `SPLIT_MANIFEST.json`。

### 4. Arms(6 个)

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

### 5. Metrics

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

### 8. Gate 0 — Pipeline Qualification(只用 TRAIN 与 DEV)

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

