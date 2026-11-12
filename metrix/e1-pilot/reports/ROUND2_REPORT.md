# METRIX E1-PILOT · Round 2 报告

| 项 | 值 |
|---|---|
| 分支 | `metrix-e1-pilot-protocol-v1` |
| 基于提交 | `a9dd5238bf7b2488910f50f075f6c3d36f8f32b1`(Round 1) |
| 本报告所在提交 | 包含本文件的那次提交 |
| 执行环境 | 本地 CPU 容器;torch 2.11.0+cpu;transformers 5.22.2;分词器 `Qwen/Qwen3-1.7B@70d244cc` |
| 约束 | 未训练、未评测、未加载模型权重、未生成或读取 TEST 数据、未删除仓库文件、未 force push |

## 总览

| # | 任务 | 状态 | 结论 |
|---|---|---|---|
| 1 | 运行 `deploy_metrix_roles.sh` | **BLOCKED** | 仓库根目录仍没有这个文件;113 个远端分支与 GitHub 代码搜索也没有。没有部署,不需要重启会话 |
| 2 | 确认 code-reviewer、data-auditor | **BLOCKED** | 依赖任务 1;两个 agent 都没有加载 |
| 3 | Y/F token 比 | 完成 | **1.292 → 1.196**,区间 [0.80, 1.25] 未改;另 20 个数据种子 1.189–1.199 |
| 4 | 名字生成三处细节 | 完成 | 写入第 2.2 节与 `DATA_MANIFEST.json`;两次独立运行的事实哈希相同:`406c8801…6b97` |
| 5 | L3 扩展到 arm A | 完成,**PASS** | 120 个 learned 答案在 512 篇锚文本中出现 0 次;L3a 仍为 0 |
| 6 | GPU 设备全名规则 | 完成 | 第 0、7、8、11 节与 `SEARCH_SPACE.json`;新增 ST9 |
| 7 | 变更记录 | 完成 | 新增第 14 节,补记 Round 1 对第 0 节与 ST7 的改动(原文、新文、原因、时间) |
| 8 | 调用 code-reviewer 与 data-auditor | **BLOCKED** | 两个 agent 不存在;没有 `reviews/<commit-hash>/` 输出 |
| 9 | 埋 bug 测试 | **BLOCKED** | 依赖 code-reviewer;没有建沙箱分支、没有埋 bug、没有调用 |
| 10 | 报告、提交、推送 | 完成 | 本文件 |

## 1. 部署

**状态:BLOCKED。** 先拉取全部远端分支,然后在仓库根目录运行。脚本不存在,所以没有“部署结果”部分可以记录,也就不需要重启会话。

原始输出:

````
$ git fetch -q --all && git rev-parse --show-toplevel && git branch --show-current
/home/user/OpenMythos
metrix-e1-pilot-protocol-v1
$ ls -la deploy_metrix_roles.sh
ls: cannot access 'deploy_metrix_roles.sh': No such file or directory
exit 2
$ bash deploy_metrix_roles.sh
bash: deploy_metrix_roles.sh: No such file or directory
exit 127
$ for every remote branch: git ls-tree -r --name-only <branch> | grep -i -E 'deploy_metrix|\.claude/agents/'
remote branches scanned: 113, with a match: 0
$ gh api -X GET search/code -f q='filename:deploy_metrix_roles.sh'
{"total_count":0,"incomplete_results":false,"items":[]}
````

## 2. 确认两个 subagent

**状态:BLOCKED**(依赖任务 1,未部署、未重启)。

本会话 Agent 工具列出的类型(工具定义,不是命令输出):`claude`、`claude-code-guide`、`Explore`、`general-purpose`、`Plan`、`statusline-setup`。没有 `code-reviewer`、`data-auditor`。

原始输出:

````
$ ls -la .claude/agents ~/.claude/agents
ls: cannot access '.claude/agents': No such file or directory
ls: cannot access '/root/.claude/agents': No such file or directory
exit 2
````

## 3. Y/F token 比

**修正**:Y 模板改短,每条 fact 少 1–3 个 token;同时把 `Y_ANSWER` 改成“答案在句末、前有空格”的形式,使 Y 里每个答案的 token 序列与它在 TRAIN 陈述句里完全相同(F 与 Y 对候选的暴露形式一致)。区间 [0.80, 1.25] 未改。

| relation | 修正前 Y_ENTITY / Y_ANSWER | 修正后 Y_ENTITY / Y_ANSWER |
|---|---|---|
| capital | {E} has a capital city. / {A} is a city. | {E} has a capital. / A city: {A}. |
| currency | {E} has its own currency. / The {A} is a currency. | {E} has a currency. / A currency: {A}. |
| founder | {E} was founded long ago. / {A} is a person. | {E} had a founder. / A person: {A}. |
| river | {E} lies beside a river. / The {A} is a river. | {E} has a river. / A river: {A}. |

| | 修正前 | 修正后 |
|---|---:|---:|
| F token(每遍) | 1,889 | 1,889 |
| Y token(每遍) | 2,440 | 2,260 |
| **Y/F**(`DATA_SEED`) | **1.292**(区间外) | **1.196**(区间内) |
| 另 20 个数据种子 | 1.283–1.295(全部区间外) | 1.189–1.199(全部区间内) |

修正前(Round 1 提交 `a9dd5238` 的模板)原始输出:

````
$ python reports/round2/y_ratio.py --manifest <a9dd5238>/DATA_MANIFEST.json --split-manifest <a9dd5238>/SPLIT_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --label before --extra-seeds 20
[before] Y templates: {"capital": ["{E} has a capital city.", "{A} is a city."], "currency": ["{E} has its own currency.", "The {A} is a currency."], "founder": ["{E} was founded long ago.", "{A} is a person."], "river": ["{E} lies beside a river.", "The {A} is a river."]}
[before] DATA_SEED 20261110: F 1889 tokens, Y 2440 tokens, ratio Y/F 1.292 -> OUTSIDE [0.80, 1.25]; per relation (report only) {'capital': 1.352, 'currency': 1.245, 'founder': 1.443, 'river': 1.172}
[before] 20 other data seeds: ratio min 1.283, max 1.295, all inside [0.80, 1.25]: False
````

修正后原始输出:

````
$ python reports/round2/y_ratio.py --manifest DATA_MANIFEST.json --split-manifest SPLIT_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --label after --extra-seeds 20
[after] Y templates: {"capital": ["{E} has a capital.", "A city: {A}."], "currency": ["{E} has a currency.", "A currency: {A}."], "founder": ["{E} had a founder.", "A person: {A}."], "river": ["{E} has a river.", "A river: {A}."]}
[after] DATA_SEED 20261110: F 1889 tokens, Y 2260 tokens, ratio Y/F 1.196 -> inside [0.80, 1.25]; per relation (report only) {'capital': 1.284, 'currency': 1.127, 'founder': 1.369, 'river': 1.06}
[after] 20 other data seeds: ratio min 1.189, max 1.199, all inside [0.80, 1.25]: True
````

改模板后重跑模板泄漏检查 L1、L2(Round 1 的脚本),仍通过:

````
$ python3 metrix/e1-pilot/reports/round1/template_overlap.py --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json
templates: 32 | per set: {'TRAIN': 4, 'DEV': 8, 'TEST': 12, 'Y': 8}
stored normalized_sha256 reproduced: True []
L1: hashes shared across sets: 0 (limit 0) -> PASS
L2: word 4-gram Jaccard over 368 cross-set pairs: max 0.2000, mean 0.000543, pairs > 0: 1, limit (max) 0.25 -> PASS
  0.2000  capital.TRAIN.1 'the capital of <entity> is <answer>' (3 grams)  vs  capital.DEV.1 'what is the capital of <entity>' (3 grams); shared: [('the', 'capital', 'of', '<entity>')]
templates with fewer than 4 words (no 4-gram, Jaccard 0 by definition): ['capital.Y_ANSWER.1', 'currency.Y_ANSWER.1', 'founder.DEV.1', 'founder.Y_ANSWER.1', 'river.Y_ANSWER.1']
  sensitivity, word 3-grams: max 0.3333, mean 0.001510, pairs > 0: 3
  sensitivity, word 2-grams: max 0.4286, mean 0.011445, pairs > 0: 32
````

**注意**
- 比值的规则针对语料总量;按 relation 分开看,capital 1.284、founder 1.369 仍高于 1.25(只报告,协议未要求逐 relation 满足)。
- 新的 `Y_ANSWER` 只有 3 个词,没有词级 4-gram,L2 对它们按定义为 0、不起约束作用(Round 1 已指出 L2 对短模板的这一局限);完全相同由 L1 保证。
- Y 里 entity 在句首(无前导空格),F 里 entity 在句中(有前导空格),两者的 entity token 序列不同;平均 4.58 对 4.45 个 token。答案的形式已一致,entity 的形式没有改。

## 4. 名字生成的三处细节

写死的内容(协议第 2.2 节,`DATA_MANIFEST.json` 的 `name_generation` 同步):
1. **随机流 purpose**:entity 用 `names:<relation>:<stratum>:entity`,answer 用 `names:<relation>:<stratum>:answer`,`<stratum>` 写作 `natural` / `random`;每个 cell、每种角色一个独立的流。
2. **前 400 个候选的统计方法**:从 answer 流开头取前 400 个满足形式规则的抽样(不应用冲突规则与锚文本规则,重复也计入),统计 `(K_st, K_qa)`;目标 = 最常见的数对,并列取按元组比较较小者。
3. **接受阶段从头重抽**:answer 流用同一 purpose 新建生成器从头开始,不接着统计时的位置。

同时写清了原先含糊的地方:抽样的具体代码、形式规则与冲突规则的区分、“前 4 个字符”区分大小写、已接受集合跨 cell / 角色 / stratum、`K_st` / `K_qa` 的定义、每个流 20,000 次上限,以及新的锚文本规则(见任务 5)。协议第 2.2 节还写入了 `DATA_SEED` 下 160 条 fact 的规范化 SHA-256,作为复现的检验值。参考实现:`reports/round2/names.py`。

**两次独立运行**:不同进程、不同 `PYTHONHASHSEED`、各自重新下载并核对锚文本源文件、各自生成锚文本与事实。另加一次不启用锚文本规则的对照运行。原始输出:

````
===== independent run 1 (new process, PYTHONHASHSEED=1, own download cache /tmp/claude-0/-home-user/b14e6790-e120-5830-986d-f23c5a9324a3/scratchpad/round2/run1/cache)
$ PYTHONHASHSEED=1 python reports/round2/anchor_check.py --manifest DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --cache-dir run1/cache --anchor-out run1/anchor.json
anchor source: SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de data/sample-100BT/train/shard_00000.parquet
file sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, pinned 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, match True
documents read 527, kept 512, anchor texts canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408, total chars 309172
$ PYTHONHASHSEED=1 python reports/round2/gen_facts.py --manifest DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --anchor run1/anchor.json --out run1/facts.json
pid 808, PYTHONHASHSEED=1, anchor rule on
facts 160 (learned 120, unread 40), distinct strings 320
facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
cell log canonical sha256: 38f04096f2da2cd0922f4281e616f131cc240088e32ab2834d6009c50fb52bb1
===== independent run 2 (new process, PYTHONHASHSEED=2, own download cache /tmp/claude-0/-home-user/b14e6790-e120-5830-986d-f23c5a9324a3/scratchpad/round2/run2/cache)
$ PYTHONHASHSEED=2 python reports/round2/anchor_check.py --manifest DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --cache-dir run2/cache --anchor-out run2/anchor.json
anchor source: SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de data/sample-100BT/train/shard_00000.parquet
file sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, pinned 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, match True
documents read 527, kept 512, anchor texts canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408, total chars 309172
$ PYTHONHASHSEED=2 python reports/round2/gen_facts.py --manifest DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --anchor run2/anchor.json --out run2/facts.json
pid 832, PYTHONHASHSEED=2, anchor rule on
facts 160 (learned 120, unread 40), distinct strings 320
facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
cell log canonical sha256: 38f04096f2da2cd0922f4281e616f131cc240088e32ab2834d6009c50fb52bb1
===== control run 3: same rules without the anchor rule
pid 838, PYTHONHASHSEED=3, anchor rule off
facts 160 (learned 120, unread 40), distinct strings 320
facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
cell log canonical sha256: 38f04096f2da2cd0922f4281e616f131cc240088e32ab2834d6009c50fb52bb1
===== comparison
$ sha256sum run1/facts.json run2/facts.json run3/facts.json
406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97  run1/facts.json
406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97  run2/facts.json
406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97  run3/facts.json
$ cmp run1/facts.json run2/facts.json && cmp run1/anchor.json run2/anchor.json
facts: identical bytes
anchor texts: identical bytes
````

每个 cell 的生成日志(两次运行相同,规范化 SHA-256 `38f04096…52bb1`):

````
cell log: [{"cell": "capital/natural", "entity_draws": 28, "target_pair": [3, 3], "answer_draws": 84}, {"cell": "capital/random", "entity_draws": 20, "target_pair": [5, 5], "answer_draws": 52}, {"cell": "currency/natural", "entity_draws": 31, "target_pair": [3, 3], "answer_draws": 82}, {"cell": "currency/random", "entity_draws": 20, "target_pair": [6, 6], "answer_draws": 46}, {"cell": "founder/natural", "entity_draws": 30, "target_pair": [3, 3], "answer_draws": 81}, {"cell": "founder/random", "entity_draws": 21, "target_pair": [5, 5], "answer_draws": 45}, {"cell": "river/natural", "entity_draws": 34, "target_pair": [3, 3], "answer_draws": 89}, {"cell": "river/random", "entity_draws": 20, "target_pair": [6, 6], "answer_draws": 42}]
````

**结论**:两次独立运行的事实文件逐字节相同,规范化 SHA-256 均为 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97`;锚文本也逐字节相同。不启用锚文本规则的对照运行得到同一个哈希,说明在 `DATA_SEED` 下这条规则没有拒绝任何名字。这个哈希也与 Round 1 可行性检查所用读法生成的结果相同,即 Round 1 的读法就是现在写死的规则。

## 5. L3 扩展到 arm A

协议改动:L3 拆为 **L3a**(原规则:unread 的 entity 与 answer 在全部训练语料和锚文本中出现 0 次)与 **L3b**(新增:每个 learned 答案在锚文本中出现 0 次,保证 arm A 对每个候选的暴露与 F 一样都是 1 次)。另在第 2.2 节加锚文本规则:在锚文本里出现过的名字生成时直接拒绝,所以 L3a、L3b 在构造上成立,检查仍然执行。

实现:`reports/round2/anchor_check.py` 按协议 2.7 构建锚文本:核对源文件 sha256;按文件顺序取前 512 篇不少于 600 字符的文档;每篇截到 128 token 后解码。然后对每个字符串做不区分大小写的子串计数。

最终结果(事实来自任务 4 的第 1 次运行)原始输出:

````
$ python reports/round2/anchor_check.py --manifest DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --facts run1/facts.json --cache-dir run1/cache --anchor-out run1/anchor_check.json
anchor source: SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de data/sample-100BT/train/shard_00000.parquet
file sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, pinned 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, match True
documents read 527, kept 512, anchor texts canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408, total chars 309172
L3a unread entities              strings  40, occurrences 0, strings found 0   -> limit 0: PASS
L3a unread answers               strings  40, occurrences 0, strings found 0   -> limit 0: PASS
L3b learned answers              strings 120, occurrences 0, strings found 0   -> limit 0: PASS
report only: learned entities    strings 120, occurrences 0, strings found 0 
L3 (a + b): PASS
exit 0
````

改协议之前,用 Round 1 规则生成的事实做同一检查(哈希相同,结果相同):

````
$ python reports/round2/anchor_check.py --manifest <a9dd5238>/DATA_MANIFEST.json --tokenizer-dir <Qwen3-1.7B@70d244cc> --facts <facts, round 1 rules> --cache-dir <cache> --anchor-out <anchor.json>
anchor source: SandyResearch/fineweb-edu-shuffled@4d1138c0e4d51d98813997ce3560e05a32bf91de data/sample-100BT/train/shard_00000.parquet
file sha256 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, pinned 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22, match True
documents read 527, kept 512, anchor texts canonical sha256 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408, total chars 309172
L3a unread entities              strings  40, occurrences 0, strings found 0   -> limit 0: PASS
L3a unread answers               strings  40, occurrences 0, strings found 0   -> limit 0: PASS
L3b learned answers              strings 120, occurrences 0, strings found 0   -> limit 0: PASS
report only: learned entities    strings 120, occurrences 0, strings found 0 
L3 (a + b): PASS
exit 0
````

**结论:PASS。** L3a:unread entity 0 次,unread answer 0 次;L3b:learned 答案 0 次。learned entity 只报告,也是 0 次。

## 6. GPU 规则

新规则:第一次加载模型时记录设备全名 `torch.cuda.get_device_name(0)`(如 `NVIDIA A100-SXM4-80GB`),之后每次训练或评测运行开始时重新读取,必须逐字相同。任何一次不同即**整批作废**:本次 Pilot 已产生的全部训练、评测与选择结果不得用于任何判断,状态记为 BLOCKED,在设备全名一致的机器上从第 8 节第 3 步重新开始。原有的“设备名以 `NVIDIA A100` 开头且显存 ≥ 79 GiB”检查保留,作为第一次运行的准入条件。

改动位置:第 0 节环境要求;第 7 节训练契约表新增“设备全名(已决定)”一行;第 8 节执行顺序第 1 步与“算力边界”;第 11 节新增 **ST9**;`SEARCH_SPACE.json` 的 `hardware.device_name_rule`(内联副本同步,校验通过)。完整 diff 见文末。

## 7. 变更记录

协议新增第 14 节。全文:

### 14. 变更记录

时间为 UTC。哈希为包含该改动的提交。

| 版本 | 时间 | 提交 | 节 | 改动 | 原因 |
|---|---|---|---|---|---|
| v1 | 2026-11-10 15:48:18 | `aa0423ef` | 全部 | 初稿(撰写任务 METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1) | — |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 0 节“环境要求” | 原文“全参微调(F、A、S、Y)在 FP32 下需要约 4 × 6.9 GB(权重、梯度、AdamW 两个动量)再加激活,所以执行机器必须有 ≥ 40 GB 显存的单张 GPU,或 ≥ 48 GB 内存的 CPU 机器”改为“所有模型训练与评测只在一张 NVIDIA A100 80GB 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查” | 原文允许 CPU 机器和任意 ≥ 40 GB 的 GPU,与 Metrix Round 1 第 8 项的算力决定(单张 A100 80GB、上限 4 小时、型号写死)冲突;原文的 4 × 6.9 GB 也漏算了 arm A 的冻结 base 副本(核实后 A 为 34.4 GB) |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 11 节 ST7 | 原文“累计 wall-clock 超过上限(第 13 节第 3 项)→ 停并报告进度;转 GPU 或降级需 Owner 决定,不得静默继续”改为“累计 GPU wall-clock 超过 4 小时(第 7 节)→ 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续” | 第 13 节第 3 项已由同一决定移出待定列表,原指向失效;模型计算不再在 CPU 上进行,“转 GPU”不再适用 |
| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 7、8、13 节;文件头;`SEARCH_SPACE.json` | 写入算力决定与显存估计;第 8 节加 GPU 检查与算力边界;待定项 3 → 2;内联块加 BEGIN / END 标记 | Metrix Round 1 第 7、8 项 |
| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.2 节;`DATA_MANIFEST.json` | 写死名字生成的随机流 purpose、前 400 个候选的统计方法、接受阶段从头重抽;补全抽样、形式规则、冲突规则(含大小写与比较范围)、上限;加锚文本规则;给出 `DATA_SEED` 下 160 条 fact 的规范化 SHA-256 | Metrix Round 2 第 4 项:v1 未写死,只凭协议不能逐字节复现数据 |
| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.4、2.6 节;`SPLIT_MANIFEST.json` | Y 模板改短,答案前加空格;Y/F token 比 1.292 → 1.196 | Metrix Round 2 第 3 项:原比值超出第 2.6 节的 [0.80, 1.25];区间不变 |
| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.5、3 节;`SPLIT_MANIFEST.json` | L3 拆为 L3a(原规则)与 L3b(learned 答案在锚文本中的出现次数,上限 0) | Metrix Round 2 第 5 项:arm A 的暴露匹配原先没有检查覆盖 |
| v1-r2 | 2026-11-12 | 本节所在提交 | 第 0、7、8、11 节;`SEARCH_SPACE.json` | GPU 规则改为:首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废;新增 ST9 | Metrix Round 2 第 6 项 |
| v1-r2 | 2026-11-12 | 本节所在提交 | 第 14 节 | 新增本变更记录,补记 v1-r1 对第 0 节与 ST7 的改动 | Metrix Round 2 第 7 项 |

## 8. code-reviewer 与 data-auditor 审查

**状态:BLOCKED。** 两个 agent 都不存在(任务 1、2),没有调用,没有 `reviews/<commit-hash>/` 目录。部署后可对本报告所在提交补做。

## 9. 埋 bug 测试

**状态:BLOCKED。** 没有 code-reviewer,无法审查。没有建沙箱分支,没有埋 bug,没有向任何 reviewer 发出调用,所以也没有调用内容可以记录。按要求,bug 清单不写进仓库。

## 附:本轮其它发现(未改动)

- **问答语境与训练语境的答案形式不同**:TRAIN 陈述句里答案前有空格,候选打分时答案在 assistant 回合开头、没有空格(`K_st` 与 `K_qa` 的区别正源于此)。F 学到的是带空格的形式,打分时考的是不带空格的形式。是否在 assistant 回合加固定前缀(如 “The answer is”),使两种语境一致,需要指挥决定。
- **第 3 节说“6 项泄漏检查”**:L3 拆成 a、b 后仍按 6 个编号计数,未改文字。

## 附:本轮协议与清单的完整 diff(相对 `a9dd5238`)

```diff
diff --git a/metrix/e1-pilot/DATA_MANIFEST.json b/metrix/e1-pilot/DATA_MANIFEST.json
index 6be415ed..db947138 100644
--- a/metrix/e1-pilot/DATA_MANIFEST.json
+++ b/metrix/e1-pilot/DATA_MANIFEST.json
@@ -130,10 +130,13 @@
         10
       ],
       "reject_if": [
-        "tokenizes to a single token with a leading space",
-        "equals an accepted string (case-insensitive)",
-        "shares its first 4 characters with an accepted string",
-        "Levenshtein distance <= 1 to an accepted string"
+        "equals an accepted string after lowercasing both",
+        "same first 4 characters as an accepted string (case-sensitive)",
+        "Levenshtein distance <= 1 to an accepted string after lowercasing both"
+      ],
+      "form_rules": [
+        "length_chars",
+        "len(encode(' ' + s)) > 1 (not a single token with a leading space)"
       ]
     },
     "random": {
@@ -151,12 +154,49 @@
       ],
       "reject_if": [
         "equals an accepted string",
-        "same letter block as an accepted string",
+        "same letter block as an accepted string (letter block = the part before '-'; the whole string if it has no '-')",
         "Hamming distance <= 1 to an accepted string of the same length"
+      ],
+      "form_rules": [
+        "length_chars"
       ]
     },
-    "order": "cells in the order relations x strata; within a cell entities first, then answers; learned before unread",
-    "answer_token_length_rule": "all answers of a cell (learned and unread) have the same token count in the statement context (leading space) and the same token count in the QA context (start of the assistant turn); the target pair of counts is the most frequent pair among the first 400 candidate strings of the cell (ties: smaller counts)"
+    "order": "cells in the order relation (capital, currency, founder, river) x stratum (natural, random); within a cell entities first, then answers; within a role the first 15 accepted strings are learned, the next 5 unread",
+    "answer_token_length_rule": {
+      "survey": "from the start of the answer stream, the first 400 draws that satisfy the form rules (reject_if and the anchor rule are NOT applied; repeats count); count (K_st, K_qa); target = the most frequent pair, ties broken by the smaller pair compared as a tuple",
+      "accept": "RESTART the answer stream (a new generator with the same purpose, not continuing after the survey); accept in order the draws that satisfy the form rules, have (K_st, K_qa) == target and satisfy reject_if and the anchor rule, until 20 are accepted",
+      "purpose": "all 20 answers of a cell have the same token counts in both contexts, so candidate scoring compares sequences of equal length"
+    },
+    "draw": {
+      "natural": "n = 2 if rng.random() < 0.5 else 3; concatenate n times rng.choice(onsets) + rng.choice(nuclei) + rng.choice(codas); capitalize the first letter",
+      "random": "u = rng.random(); L = 3 if u < 0.25 else 4 if u < 0.75 else 5; L times rng.choice(letters); '-'; 2 times rng.choice(digits)"
+    },
+    "streams": {
+      "entity": "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:entity')",
+      "answer": "rng_rule(DATA_SEED, 'names:<relation>:<stratum>:answer')",
+      "stratum_spelling": "natural | random",
+      "note": "one independent stream per cell and role"
+    },
+    "accepted_strings_scope": "every string accepted so far, in any cell, either role and either stratum",
+    "anchor_rule": "reject a string that occurs (case-insensitive substring) in the anchor text of 2.7 (the 512 decoded texts of at most 128 tokens); the anchor text is therefore built before the names",
+    "token_counts": {
+      "K_st": "len(encode(' ' + s)) - statement context",
+      "K_qa": "len(encode(s)) - QA context, start of the assistant turn",
+      "encode": "pinned tokenizer, add_special_tokens=False"
+    },
+    "entity_procedure": "draw from the entity stream in order; accept draws that satisfy the form rules, reject_if and the anchor rule, until 20 are accepted",
+    "max_draws_per_stream": 20000,
+    "on_exhaustion": "IMPLEMENTATION_FAIL",
+    "reference_implementation": "metrix/e1-pilot/reports/round2/names.py",
+    "expected_facts_canonical_sha256": "406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97",
+    "expected_facts_fields": [
+      "fact_id",
+      "exposure",
+      "relation",
+      "stratum",
+      "entity",
+      "answer"
+    ]
   },
   "s_permutation": "per cell, a derangement of the 15 learned answers drawn with rng_rule(DATA_SEED, 's-permutation:<relation>:<stratum>'); redraw until no fixed point",
   "templates": {
diff --git a/metrix/e1-pilot/METRIX_E1_PROTOCOL.md b/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
index cf698f6e..7eb1c3fd 100644
--- a/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
+++ b/metrix/e1-pilot/METRIX_E1_PROTOCOL.md
@@ -7,7 +7,7 @@
 | 本文件的作用 | 执行 E1-PILOT 只需要本文件、同目录三个 JSON,以及第 0 节固定的外部来源 |
 | 本文件不包含 | 任何训练、评测结果或结论;任何 TEST 数据 |
 
-Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 只剩第 13 节的 2 项。
+Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两者冲突处以修订条款为准。据此:fact 聚合函数固定为 mean;Gate 0 只使用 TRAIN 与 DEV;模型已由 Project Owner 指定;算力已决定(一张 NVIDIA A100 80GB,GPU wall-clock 上限 4 小时,见第 7、8、13 节);PENDING_REVIEW_GATE 只剩第 13 节的 2 项。所有改动见第 14 节变更记录。
 
 ## 0. 标识、出处与环境
 
@@ -37,7 +37,7 @@ Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两
 **种子**:`DATA_SEED = 20261110`,`CANDIDATE_SEED = 20261111`,`TRAIN_SEEDS = [101, 202, 303]`,`BOOTSTRAP_SEED = 20261112`。所有随机数都来自
 `random.Random(int.from_bytes(sha256(f"{SEED}:{purpose}".encode("utf-8")).digest()[:8], "big"))`,`purpose` 在各处写明。结果不好不得换种子。
 
-**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。
+**环境要求**:所有模型训练与评测只在**一张 NVIDIA A100 80GB** 上执行;首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废(第 7、8、11 节);CPU 只做数据生成、泄漏检查与分词器检查。不满足即 BLOCKED,不得改用更小的模型或改变精度来绕过。确定性:`torch.use_deterministic_algorithms(True)`,关闭 TF32,`CUBLAS_WORKSPACE_CONFIG=:4096:8`。
 
 **哈希**:JSON 的规范化序列为 `json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)` 的 UTF-8 字节;JSONL 为每行一个规范化对象、以 `\n` 连接并以一个 `\n` 结尾;算法 SHA-256。`byte_sha256` 是文件原样字节的哈希,`canonical_sha256` 是解析后内容的规范化序列的哈希;后者标识内容,前者标识文件。
 
@@ -64,10 +64,22 @@ Task Order 与其 “Mandatory consistency amendments A–L” 同时生效;两
 
 ### 2.2 名字生成(由 `DATA_SEED` 决定)
 
-- `natural`:音节 = onset + nucleus + coda;onset ∈ {b,d,f,g,k,l,m,n,p,r,s,t,v,z,br,dr,kr,tr,sh,th},nucleus ∈ {a,e,i,o,u,ae,ia,ou},coda ∈ {空,空,n,r,l,s,th,nd};2 或 3 个音节(各 0.5);首字母大写;长度 4–10 字符。拒绝:带前导空格时只切成 1 个 token;与已接受的字符串相同(不分大小写);与已接受的字符串前 4 个字符相同;与已接受的字符串编辑距离 ≤ 1。
-- `random`:字母表 `BCDFGHJKLMNPQRSTVWXZ`,数字表 `23456789`;形式为 L 个字母 + `-` + 2 个数字,L ∈ {3,4,5},概率 {0.25, 0.5, 0.25},长度 6–8 字符。拒绝:与已接受的字符串相同;字母段与已接受的字符串相同;与同长度的已接受字符串汉明距离 ≤ 1。
-- 生成顺序:cell 按 relation × stratum 的顺序;cell 内先 entity 后 answer,先 learned 后 unread。
-- **答案等长规则**:同一 cell 的全部 20 个答案,在陈述句语境(前有空格)下 token 数相同,在问答语境(assistant 回合开头)下 token 数也相同。目标 token 数对取该 cell 前 400 个候选字符串中最常见的一对(并列取较小者),只接受符合的候选。作用:候选打分比较的是等长序列,没有长度偏差。
+- **抽一个字符串**:
+  - `natural`:`n = 2 if rng.random() < 0.5 else 3`;n 次 `rng.choice(onsets) + rng.choice(nuclei) + rng.choice(codas)` 拼接;首字母大写。onset ∈ {b,d,f,g,k,l,m,n,p,r,s,t,v,z,br,dr,kr,tr,sh,th},nucleus ∈ {a,e,i,o,u,ae,ia,ou},coda ∈ {空,空,n,r,l,s,th,nd}(空出现两次,即概率 2/8)。
+  - `random`:`u = rng.random()`;`L = 3 if u < 0.25 else 4 if u < 0.75 else 5`;L 次 `rng.choice("BCDFGHJKLMNPQRSTVWXZ")`,接 `-`,再 2 次 `rng.choice("23456789")`。
+- **形式规则**:长度 `natural` 4–10、`random` 6–8 字符;`natural` 另要求带前导空格时多于 1 个 token(`len(encode(" " + s)) > 1`)。
+- **冲突规则(reject_if)**,与**已接受集合**比较;已接受集合包含此前在任何 cell、任何角色(entity 或 answer)、任何 stratum 中接受的全部字符串:
+  - `natural`:与某个已接受字符串小写后相同;与某个已接受字符串前 4 个字符相同(区分大小写);与某个已接受字符串小写后的编辑距离 ≤ 1。
+  - `random`:与某个已接受字符串相同;字母段(`-` 之前的部分;没有 `-` 的字符串取整串)与某个已接受字符串的字母段相同;与某个等长的已接受字符串汉明距离 ≤ 1。
+- **锚文本规则**:在第 2.7 节的锚文本(512 篇、各截到 128 token 后解码的文本)中出现过的字符串(不分大小写的子串)一律拒绝。因此锚文本必须在名字之前生成。
+- **token 数**:`K_st(s) = len(encode(" " + s))`(陈述句语境,前有空格),`K_qa(s) = len(encode(s))`(问答语境,assistant 回合开头);`encode` 用固定分词器,`add_special_tokens=False`。
+- **随机流(细节 1)**:每个 cell、每种角色一个独立的流:entity 用 `rng_rule(DATA_SEED, "names:<relation>:<stratum>:entity")`,answer 用 `rng_rule(DATA_SEED, "names:<relation>:<stratum>:answer")`;`<stratum>` 写作 `natural` 或 `random`。
+- **生成顺序**:cell 按 relation(capital、currency、founder、river)× stratum(natural、random)的顺序;cell 内先 entity 后 answer;每种角色先接受的 15 个为 learned,后 5 个为 unread。
+- **entity**:从 entity 流依次抽,满足形式规则、冲突规则和锚文本规则的接受,直到 20 个。
+- **答案等长规则——统计(细节 2)**:从 answer 流的开头依次抽,取**前 400 个满足形式规则的抽样**(不应用冲突规则和锚文本规则,重复的也计入),统计每个的 `(K_st, K_qa)`;目标数对 = 出现次数最多的数对,并列时取按元组比较较小者。
+- **答案等长规则——接受(细节 3)**:**answer 流从头重抽**(用同一个 purpose 新建生成器,不接着统计时的位置);依次接受满足形式规则、`(K_st, K_qa)` 等于目标、冲突规则和锚文本规则的抽样,直到 20 个。作用:同一 cell 的答案在两种语境下 token 数都相同,候选打分比较的是等长序列,没有长度偏差。
+- **上限**:每个流最多抽 20,000 次;超过即 IMPLEMENTATION_FAIL。
+- **复现**:按以上规则,`DATA_SEED = 20261110` 生成的 160 条 fact(字段 `fact_id, exposure, relation, stratum, entity, answer`,按生成顺序排列)的规范化 SHA-256 必须等于 `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97`。参考实现 `reports/round2/names.py`;两次独立运行的记录见 `reports/ROUND2_REPORT.md`。
 
 ### 2.3 每条 fact 的文本
 
@@ -88,19 +100,19 @@ unread fact 的 entity 和 answer 在任何 arm 的训练文本和锚文本里
 | capital | TRAIN | The capital of {E} is {A}. |
 | capital | DEV | What is the capital of {E}? / {E} has which city as its capital? |
 | capital | TEST | Name the capital city of {E}. / Which city is {E}'s capital? / Tell me the name of the city that serves as capital for {E}. |
-| capital | Y | {E} has a capital city. / {A} is a city. |
+| capital | Y | {E} has a capital. / A city: {A}. |
 | currency | TRAIN | The currency used in {E} is the {A}. |
 | currency | DEV | What currency do people use in {E}? / In {E}, goods are paid for with which currency? |
 | currency | TEST | Name the currency of {E}. / Which currency is legal tender in {E}? / A shopkeeper in {E} expects payment in what currency? |
-| currency | Y | {E} has its own currency. / The {A} is a currency. |
+| currency | Y | {E} has a currency. / A currency: {A}. |
 | founder | TRAIN | {E} was founded by {A}. |
 | founder | DEV | Who founded {E}? / {E} owes its founding to which person? |
 | founder | TEST | Name the founder of {E}. / Which person established {E}? / The founding of {E} is credited to whom? |
-| founder | Y | {E} was founded long ago. / {A} is a person. |
+| founder | Y | {E} had a founder. / A person: {A}. |
 | river | TRAIN | The river that flows through {E} is the {A}. |
 | river | DEV | Which river flows through {E}? / {E} stands on the banks of which river? |
 | river | TEST | Name the river running through {E}. / What river passes by {E}? / A boat leaving {E} would sail on which river? |
-| river | Y | {E} lies beside a river. / The {A} is a river. |
+| river | Y | {E} has a river. / A river: {A}. |
 
 共 32 个模板,逐条的 `template_id` 与 `normalized_sha256` 在 `SPLIT_MANIFEST.json`。
 
@@ -110,13 +122,13 @@ unread fact 的 entity 和 answer 在任何 arm 的训练文本和锚文本里
 - **干扰项的池**:同 relation、同 stratum、同暴露类别(learned 或 unread)的其它 fact 的答案。
 - 抽取:用 `rng_rule(CANDIDATE_SEED, "cand:<fact_id>")` 不放回抽 3 个并决定 4 个候选的顺序;不得重复。
 - 一条 fact 的候选表对它的全部模板、全部 split、全部 arm 相同。
-- **暴露匹配**:learned fact 的每个候选在 F、L、A、S、Y 的训练语料里都恰好出现 1 次;unread fact 的每个候选出现 0 次。因此“见过这个词”不能用来选出正确项。
+- **暴露匹配**:learned fact 的每个候选在 F、L、A、S、Y 的训练语料里都恰好出现 1 次(A 的锚文本里 0 次,由 L3b 检查);unread fact 的每个候选出现 0 次。因此“见过这个词”不能用来选出正确项。
 - 完整候选映射的 `canonical_sha256` 写入 `SPLIT_MANIFEST.json`。
 
 ### 2.6 S 与 Y 的训练语料
 
 - **S**:用 TRAIN 模板,但每个 cell 内把 15 个 learned 答案做一次没有不动点的置换(`rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>")`,有不动点就重抽)。entity 与答案各出现 1 次,真实映射一条都不出现。
-- **Y**:每条 learned fact 两个句子:一个只含 entity(`Y_ENTITY` 模板),一个只含 answer(`Y_ANSWER` 模板),各自是独立的训练序列,永不出现在同一序列里。共 240 句。Y 语料的 token 总数与 F 语料之比必须在 [0.80, 1.25],否则 IMPLEMENTATION_FAIL。
+- **Y**:每条 learned fact 两个句子:一个只含 entity(`Y_ENTITY` 模板),一个只含 answer(`Y_ANSWER` 模板,答案前有空格,切分方式与它在 TRAIN 陈述句里相同),各自是独立的训练序列,永不出现在同一序列里。共 240 句。Y 语料的 token 总数与 F 语料之比必须在 [0.80, 1.25],否则 IMPLEMENTATION_FAIL。撰写时用固定分词器核算(`reports/round2/y_ratio.py`):`DATA_SEED` 下为 1.196(F 1,889 token,Y 2,260 token);另 20 个数据种子在 1.189–1.199 之间。
 
 ### 2.7 通用文本与锚文本
 
@@ -139,7 +151,8 @@ unread fact 的 entity 和 answer 在任何 arm 的训练文本和锚文本里
 |---|---|---|
 | L1 | TRAIN、DEV、TEST、Y 四个模板集合的 `normalized_sha256` 两两不交 | 0 个重复 |
 | L2 | 不同集合的任意两个归一化模板,词 4-gram 集合的 Jaccard 重叠 | ≤ 0.25 |
-| L3 | 每个 unread entity、unread answer 在 `train_F`、`train_S`、`train_Y`、`anchor_text` 中的出现次数(不分大小写的子串) | 0 |
+| L3a | 每个 unread entity、unread answer 在 `train_F`、`train_S`、`train_Y`、`anchor_text` 中的出现次数(不分大小写的子串) | 0 |
+| L3b | 每个 learned answer 在 `anchor_text` 中的出现次数(不分大小写的子串);保证 arm A 对每个候选的暴露与 F 相同 | 0 |
 | L4 | 实例化后的 DEV / TEST 问句在任何训练语料中逐字出现的次数 | 0 |
 | L5 | learned 与 unread 的 fact_id 集合相交数;320 个字符串中的重复数 | 0 |
 | L6 | 锚文本与通用文本共享的词 13-gram 数 | 0 |
@@ -147,7 +160,7 @@ unread fact 的 entity 和 answer 在任何 arm 的训练文本和锚文本里
 learned fact 的 entity 与 answer 同时出现在 TRAIN 陈述句和 QA 中是被测对象,不算泄漏。
 
 执行接口(实现属于下一个 Task):
-`python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json`,仅当 6 项都在上限内时退出码为 0。L1、L2 只用模板,协议撰写时已可计算;L3–L5 中涉及 TEST 的部分在 `test_qa.jsonl` 生成之后才运行。
+`python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json`,仅当 6 项都在上限内时退出码为 0。L1、L2 只用模板,协议撰写时已可计算;L3–L5 中涉及 TEST 的部分在 `test_qa.jsonl` 生成之后才运行。第 2.2 节的锚文本规则使 L3a、L3b 在生成时就成立,检查仍然执行。
 
 ## 4. Arms(6 个)
 
@@ -252,7 +265,8 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
 | checkpoint | 每次训练只保留并评测最终 checkpoint;中间 checkpoint 不用于任何判断 |
 | early stopping | 不允许 |
 | Y 的训练量 | 对它的 240 句读 20 遍,batch 16,同为 300 步;token 数比见 2.6 |
-| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测;同一次 Pilot 内每次运行记录的 `torch.cuda.get_device_name(0)` 必须相同 |
+| 硬件(已决定) | 一张 NVIDIA A100 80GB;30 次训练与全部模型评测都在这一型号上执行;CPU 不执行任何模型训练或评测 |
+| 设备全名(已决定) | 第一次加载模型时记录设备全名 `torch.cuda.get_device_name(0)`(如 `NVIDIA A100-SXM4-80GB`、`NVIDIA A100-PCIE-80GB`),写入实验记录;之后每次运行开始时重新读取,必须与记录的全名逐字相同。任何一次不同,**整批作废**:本次 Pilot 已产生的全部训练、评测与选择结果作废、不得用于任何判断,状态记为 BLOCKED,换到设备全名一致的机器上从第 8 节第 3 步重新开始(ST9) |
 | GPU wall-clock 上限(已决定) | 4 小时:从第一次加载模型到 TEST 评测结束的累计 GPU 时间;超过即 ST7 |
 
 锚文本的前向计算是 A 的额外算力,单独记入 compute accounting,不算事实 token。
@@ -308,9 +322,11 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
       "gpu": "NVIDIA A100 80GB",
       "count": 1,
       "decided": "Metrix instruction, round 1 item 8, 2026-11-12",
-      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
+      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU",
       "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
-      "cpu_use": "data generation, leakage checks and tokenizer checks only"
+      "cpu_use": "data generation, leakage checks and tokenizer checks only",
+      "device_name_rule": "record the full device name torch.cuda.get_device_name(0) at the first model load (e.g. 'NVIDIA A100-SXM4-80GB'); read it again at the start of every training or evaluation run; it must equal the recorded name exactly; otherwise the whole batch is void: every result of this pilot is discarded, status BLOCKED, restart from step 3 of section 8 (ST9)",
+      "changed": "round 2, 2026-11-12: device-name rule replaces 'every run reports the same device name'"
     },
     "wall_clock_limit_gpu_hours": 4,
     "wall_clock_scope": "cumulative GPU wall-clock from the first model load to the end of the TEST evaluation; above the limit: ST7"
@@ -487,7 +503,7 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
 
 **执行顺序**(每一步的停止规则见第 11 节):
 1. 记录环境与出处;在 CPU 上生成除 TEST 以外的数据,把哈希写入两个 manifest 并提交。
-   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8);从此刻第一次加载模型起累计 GPU wall-clock。
+   GPU 检查(第 7 节):`torch.cuda.get_device_name(0)` 以 `NVIDIA A100` 开头且 `total_memory ≥ 79 GiB`,否则 BLOCKED(ST8)。第一次加载模型时把设备全名写入实验记录,并从此刻起累计 GPU wall-clock;此后每次训练或评测运行开始时核对设备全名(ST9)。
 2. 运行泄漏检查。
 3. 评测 N:TRAIN 闭卷、DEV-QA、general DEV。
 4. F 的 6 个配置(种子 101)→ 选定 → 用选定配置检查阳性对照。
@@ -496,7 +512,7 @@ E1-PILOT 只有一个训练阶段:Retention 记为 NOT_TESTED,不进任何门槛
 7. 按下表判定 Gate 0。
 8. Gate 0 通过后:提交冻结记录(选定配置、数据哈希、checkpoint 哈希)→ 生成 `test_qa.jsonl` 与 `general_test.jsonl` → 对 TEST 运行 L3–L5 → **TEST 只评一次**。
 
-**算力边界**:第 3–8 步全部在同一型号的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。
+**算力边界**:第 3–8 步全部在设备全名与首次记录逐字相同的一张 NVIDIA A100 80GB 上执行,累计 GPU wall-clock ≤ 4 小时(第 7 节);任何一步若会使累计时间超过上限,按 ST7 停下,不得静默继续,也不得为节省时间删减本节的任何一步。
 
 **Gate 0 门槛(全部为数值;“seed-average” 见第 6 节)**
 
@@ -587,6 +603,7 @@ Compute accounting 的算法:训练 FLOPs ≈ 6 · P · T,前向 FLOPs ≈ 2 ·
 | ST6 | 任一次训练或评测出现非有限值 | 停该次;若发生在选定配置或对照上,IMPLEMENTATION_FAIL |
 | ST7 | 累计 GPU wall-clock 超过 4 小时(第 7 节) | 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续 |
 | ST8 | 环境不满足第 0 节 | BLOCKED |
+| ST9 | 某次运行开始时读到的设备全名与首次记录不同 | 整批作废:本次 Pilot 的全部结果不得用于任何判断;BLOCKED;在设备全名一致的机器上从第 8 节第 3 步重新开始 |
 
 ## 12. Out of Scope
 
@@ -607,3 +624,19 @@ Compute accounting 的算法:训练 FLOPs ≈ 6 · P · T,前向 FLOPs ≈ 2 ·
 **已决定,不再待定**:原第 3 项“CPU wall-clock 上限”由 Metrix 指令 Round 1 第 8 项(2026-11-12)决定:CPU 不执行任何模型训练或评测(CPU wall-clock 上限对模型计算为 0);整个 Pilot 在一张 NVIDIA A100 80GB 上执行,型号写死,GPU wall-clock 上限 4 小时(第 7、8、11 节)。
 
 其余可执行参数都已写死或标为 PROPOSED;Review Gate 可以改动一次,PROTOCOL_FROZEN 之后任何门槛、split 规则、指标、搜索预算或 Gate 定义的改动都必须开新协议版本。
+
+## 14. 变更记录
+
+时间为 UTC。哈希为包含该改动的提交。
+
+| 版本 | 时间 | 提交 | 节 | 改动 | 原因 |
+|---|---|---|---|---|---|
+| v1 | 2026-11-10 15:48:18 | `aa0423ef` | 全部 | 初稿(撰写任务 METRIX-E1-PILOT-PROTOCOL-AUTHORING-V1) | — |
+| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 0 节“环境要求” | 原文“全参微调(F、A、S、Y)在 FP32 下需要约 4 × 6.9 GB(权重、梯度、AdamW 两个动量)再加激活,所以执行机器必须有 ≥ 40 GB 显存的单张 GPU,或 ≥ 48 GB 内存的 CPU 机器”改为“所有模型训练与评测只在一张 NVIDIA A100 80GB 上执行(型号写死,检查方法与显存估计见第 7 节);CPU 只做数据生成、泄漏检查与分词器检查” | 原文允许 CPU 机器和任意 ≥ 40 GB 的 GPU,与 Metrix Round 1 第 8 项的算力决定(单张 A100 80GB、上限 4 小时、型号写死)冲突;原文的 4 × 6.9 GB 也漏算了 arm A 的冻结 base 副本(核实后 A 为 34.4 GB) |
+| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 11 节 ST7 | 原文“累计 wall-clock 超过上限(第 13 节第 3 项)→ 停并报告进度;转 GPU 或降级需 Owner 决定,不得静默继续”改为“累计 GPU wall-clock 超过 4 小时(第 7 节)→ 停并报告进度;延长上限、换硬件或降级都需 Owner 决定并记录,不得静默继续” | 第 13 节第 3 项已由同一决定移出待定列表,原指向失效;模型计算不再在 CPU 上进行,“转 GPU”不再适用 |
+| v1-r1 | 2026-11-12 14:26:49 | `a9dd5238` | 第 7、8、13 节;文件头;`SEARCH_SPACE.json` | 写入算力决定与显存估计;第 8 节加 GPU 检查与算力边界;待定项 3 → 2;内联块加 BEGIN / END 标记 | Metrix Round 1 第 7、8 项 |
+| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.2 节;`DATA_MANIFEST.json` | 写死名字生成的随机流 purpose、前 400 个候选的统计方法、接受阶段从头重抽;补全抽样、形式规则、冲突规则(含大小写与比较范围)、上限;加锚文本规则;给出 `DATA_SEED` 下 160 条 fact 的规范化 SHA-256 | Metrix Round 2 第 4 项:v1 未写死,只凭协议不能逐字节复现数据 |
+| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.4、2.6 节;`SPLIT_MANIFEST.json` | Y 模板改短,答案前加空格;Y/F token 比 1.292 → 1.196 | Metrix Round 2 第 3 项:原比值超出第 2.6 节的 [0.80, 1.25];区间不变 |
+| v1-r2 | 2026-11-12 | 本节所在提交 | 第 2.5、3 节;`SPLIT_MANIFEST.json` | L3 拆为 L3a(原规则)与 L3b(learned 答案在锚文本中的出现次数,上限 0) | Metrix Round 2 第 5 项:arm A 的暴露匹配原先没有检查覆盖 |
+| v1-r2 | 2026-11-12 | 本节所在提交 | 第 0、7、8、11 节;`SEARCH_SPACE.json` | GPU 规则改为:首次运行记录设备全名,同一次 Pilot 内必须一致,否则整批作废;新增 ST9 | Metrix Round 2 第 6 项 |
+| v1-r2 | 2026-11-12 | 本节所在提交 | 第 14 节 | 新增本变更记录,补记 v1-r1 对第 0 节与 ST7 的改动 | Metrix Round 2 第 7 项 |
diff --git a/metrix/e1-pilot/SEARCH_SPACE.json b/metrix/e1-pilot/SEARCH_SPACE.json
index 00221380..79647614 100644
--- a/metrix/e1-pilot/SEARCH_SPACE.json
+++ b/metrix/e1-pilot/SEARCH_SPACE.json
@@ -40,9 +40,11 @@
       "gpu": "NVIDIA A100 80GB",
       "count": 1,
       "decided": "Metrix instruction, round 1 item 8, 2026-11-12",
-      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU; every run of the pilot reports the same torch.cuda.get_device_name(0)",
+      "rule": "all 30 training runs and every model evaluation run on one NVIDIA A100 80GB; no model training or evaluation on CPU",
       "check": "torch.cuda.get_device_name(0) starts with 'NVIDIA A100' and torch.cuda.get_device_properties(0).total_memory >= 79 * 2**30; otherwise BLOCKED (ST8)",
-      "cpu_use": "data generation, leakage checks and tokenizer checks only"
+      "cpu_use": "data generation, leakage checks and tokenizer checks only",
+      "device_name_rule": "record the full device name torch.cuda.get_device_name(0) at the first model load (e.g. 'NVIDIA A100-SXM4-80GB'); read it again at the start of every training or evaluation run; it must equal the recorded name exactly; otherwise the whole batch is void: every result of this pilot is discarded, status BLOCKED, restart from step 3 of section 8 (ST9)",
+      "changed": "round 2, 2026-11-12: device-name rule replaces 'every run reports the same device name'"
     },
     "wall_clock_limit_gpu_hours": 4,
     "wall_clock_scope": "cumulative GPU wall-clock from the first model load to the end of the TEST evaluation; above the limit: ST7"
diff --git a/metrix/e1-pilot/SPLIT_MANIFEST.json b/metrix/e1-pilot/SPLIT_MANIFEST.json
index 15dcf198..68f6aba2 100644
--- a/metrix/e1-pilot/SPLIT_MANIFEST.json
+++ b/metrix/e1-pilot/SPLIT_MANIFEST.json
@@ -78,18 +78,18 @@
       "relation": "capital",
       "set": "Y",
       "kind": "Y_ENTITY",
-      "text": "{E} has a capital city.",
-      "normalized": "<entity> has a capital city",
-      "normalized_sha256": "7071454770638a69470822e017ebf14836d52511a8a099b53065248933a16ceb"
+      "text": "{E} has a capital.",
+      "normalized": "<entity> has a capital",
+      "normalized_sha256": "e13d04f3ce5dc403b709f863fe2a4bf78e59ec2110db3f4190d4c17e4bddca3c"
     },
     {
       "template_id": "capital.Y_ANSWER.1",
       "relation": "capital",
       "set": "Y",
       "kind": "Y_ANSWER",
-      "text": "{A} is a city.",
-      "normalized": "<answer> is a city",
-      "normalized_sha256": "ca74c9dc8b5f9545d523e70b8a39ad9baa82bc888e5867de7bf019c856f022e9"
+      "text": "A city: {A}.",
+      "normalized": "a city <answer>",
+      "normalized_sha256": "481a4a00b41f7d568bf0eb47760e2c92cb45f5715fe3ade1e7649e1af4b51305"
     },
     {
       "template_id": "currency.TRAIN.1",
@@ -150,18 +150,18 @@
       "relation": "currency",
       "set": "Y",
       "kind": "Y_ENTITY",
-      "text": "{E} has its own currency.",
-      "normalized": "<entity> has its own currency",
-      "normalized_sha256": "f861936ba1d35900ad58408f2b2c3eab80a2971bce23d6f2e1d9dcb4e0b1c76c"
+      "text": "{E} has a currency.",
+      "normalized": "<entity> has a currency",
+      "normalized_sha256": "f2ad875c4bc2680bb8ec2ad62648c3dd57446fc91f11cfa29658c07c50da92ae"
     },
     {
       "template_id": "currency.Y_ANSWER.1",
       "relation": "currency",
       "set": "Y",
       "kind": "Y_ANSWER",
-      "text": "The {A} is a currency.",
-      "normalized": "the <answer> is a currency",
-      "normalized_sha256": "328b432372f4a75e671e82e8956d4dc570e851695d09adf28fb4f377399aab72"
+      "text": "A currency: {A}.",
+      "normalized": "a currency <answer>",
+      "normalized_sha256": "7575ee9ec8656de841deca6350dec2b1785f885a66d4d3cb78473720e2488405"
     },
     {
       "template_id": "founder.TRAIN.1",
@@ -222,18 +222,18 @@
       "relation": "founder",
       "set": "Y",
       "kind": "Y_ENTITY",
-      "text": "{E} was founded long ago.",
-      "normalized": "<entity> was founded long ago",
-      "normalized_sha256": "641900118b299103933b8c7ab2f4d1a211874fa544f762070cf08eff73eea0d7"
+      "text": "{E} had a founder.",
+      "normalized": "<entity> had a founder",
+      "normalized_sha256": "838aeb12dee8e2f3c94ed6baf3a4b58f76890dbf7e21f95c3ec17eaba59499f2"
     },
     {
       "template_id": "founder.Y_ANSWER.1",
       "relation": "founder",
       "set": "Y",
       "kind": "Y_ANSWER",
-      "text": "{A} is a person.",
-      "normalized": "<answer> is a person",
-      "normalized_sha256": "7b1c1412d3fc8f29c7a0a0885211e6a957afcff7b6717800ed8a0cfe1df3a2a6"
+      "text": "A person: {A}.",
+      "normalized": "a person <answer>",
+      "normalized_sha256": "275c8caf2ab8bda4247259781a4a0a302ffb24a0080445bcf6046c30a5fbf5b8"
     },
     {
       "template_id": "river.TRAIN.1",
@@ -294,24 +294,24 @@
       "relation": "river",
       "set": "Y",
       "kind": "Y_ENTITY",
-      "text": "{E} lies beside a river.",
-      "normalized": "<entity> lies beside a river",
-      "normalized_sha256": "a08cc862e3b68f66ff8be5e2283d1f3ef3f6f0abf6792031fe4b6bdfb5a3b2d5"
+      "text": "{E} has a river.",
+      "normalized": "<entity> has a river",
+      "normalized_sha256": "1b7a623826e7d5e8e187b78e750deb02d12f66032635a9c5de5d252fbd05efa8"
     },
     {
       "template_id": "river.Y_ANSWER.1",
       "relation": "river",
       "set": "Y",
       "kind": "Y_ANSWER",
-      "text": "The {A} is a river.",
-      "normalized": "the <answer> is a river",
-      "normalized_sha256": "66d8a13a938af59787f8982fe51490e982ddf5a9c64fc37bf8eb87d2807af5f3"
+      "text": "A river: {A}.",
+      "normalized": "a river <answer>",
+      "normalized_sha256": "92a3dcce81042daf25570fb26f361e760c0165b57f5e43f0c8f601ddd07858d2"
     }
   ],
   "template_freeze": {
     "normalization": "replace {E} by <ENTITY> and {A} by <ANSWER>, lowercase, replace every character outside [a-z0-9<> ] by a space, collapse spaces",
     "identity": "normalized_sha256 of every template; template_set_sha256 = SHA-256 of the sorted normalized_sha256 values joined by '\\n'",
-    "template_set_sha256": "0ba13680f2194eba980bda56d3fb598a6e17ebb0e0779abdb47f53291cf506bb"
+    "template_set_sha256": "2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f"
   },
   "candidates": {
     "way": 4,
@@ -341,10 +341,15 @@
         ]
       }
     },
-    "L3_unread_fact": {
+    "L3a_unread_fact": {
       "rule": "occurrences (case-insensitive substring) of every unread entity and every unread answer in train_F, train_S, train_Y and anchor_text",
       "limit": 0
     },
+    "L3b_learned_answer_in_anchor": {
+      "rule": "occurrences (case-insensitive substring) of every learned answer in anchor_text; keeps the exposure of arm A to every candidate equal to that of F",
+      "limit": 0,
+      "added": "round 2, 2026-11-12"
+    },
     "L4_question_text": {
       "rule": "instantiated DEV / TEST question strings occurring verbatim in any training corpus",
       "limit": 0
@@ -359,7 +364,8 @@
     },
     "command": "python -m metrix.e1_pilot.check_leakage --data <DATA_DIR> --split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --out <DATA_DIR>/leakage_report.json",
     "exit_code": "0 only if every check is within its limit",
-    "test_split": "L1 and L2 use templates only; L3-L5 run on TEST questions only after test_qa.jsonl is generated"
+    "test_split": "L1 and L2 use templates only; L3a, L3b, L4, L5 run on TEST questions only after test_qa.jsonl is generated",
+    "generation_rule": "names occurring in anchor_text are rejected when they are generated (DATA_MANIFEST.json: name_generation.anchor_rule), so L3a and L3b hold by construction; the checks still run"
   },
   "hashing": {
     "encoding": "UTF-8",
```

