# SUBMISSION NOTE · METRIX-E1-V1-PROTOCOL-AUTHORING-V1.0

| 项 | 值 |
|---|---|
| 状态 | AWAITING_REVIEW_GATE(协议未冻结) |
| 指令 | `tasks/E1V1_AUTHORING_OWNER_MESSAGE.md`(Owner 消息“=====”之前的部分,原文)与 `tasks/E1V1_PROTOCOL_TASK_ORDER_V1.md`(之后的部分,原文) |
| 分支 | `metrix-e1-v1-protocol-v1`,起点 `6e03468956208c422d0d41c08edaaf116166338c`(E1-PILOT 报告勘误提交,本指令 A6) |
| 撰写环境 | Claude Code 云容器,主机名 `vm`,只有 CPU、没有 GPU;Python 3.13.18 的 venv 只装了分词器相关的库(transformers 5.22.2、tokenizers 0.23.3、huggingface-hub 2.4.0、pyarrow 26.0.1),没有安装 torch,不可能加载模型权重 |
| 本任务没有做的事 | 没有训练、没有模型评测、没有使用 GPU;没有生成、实例化或读取任何 V1 的 TEST 样本(事实 QA 与损伤评测都包括在内) |

路径约定:下文路径相对于 `metrix/e1-v1/`(另注明者除外)。

## 1. 交付物

| 文件 | 内容 |
|---|---|
| `METRIX_E1V1_PROTOCOL.md` | 协议正文(第 0–17 节) |
| `DATA_MANIFEST.json` | 模型与输入约定、种子与全部 purpose、事实数量与名字生成规则(含 Pilot 字符串预置)、S 置换、Y 比值、锚文本、数据文件的参考哈希、报告清单 `reported_values` |
| `SPLIT_MANIFEST.json` | fact_id 与 split、32 个模板(从 Pilot 冻结 manifest 原样复制)、候选规则与参考哈希、L1–L8 |
| `DOSE_SPACE.json` | 三个方法的配置、对照 S / Y / Z0 / P+、剂量阶梯、iso 规则与容差、checkpoint 保存规则、训练契约、计算量匹配、训练次数 |
| `DAMAGE_MANIFEST.json` | D1、D2 的来源、revision、文件 sha256、许可证、划分与排除规则、参考哈希、bootstrap、Gate D 阈值、margin 公式、主比较 |
| `SUBMISSION_NOTE.md` | 本文件 |
| `tasks/` | 两份指令原文 |
| `reports/authoring/v1_data_check.py` 与 `v1_data_check.txt`、`v1_data_check_repeat.txt` | 非 TEST 数据规则的参考构建与撰写时的检查;完整 stdout;两次独立运行的比对 |
| `reports/authoring/compute_estimate.py` 与 `compute_estimate.txt` | 第 12 节的算力、磁盘与费用估算及其完整输出 |
| `reports/authoring/d2_dataset_metadata.txt` | D2 两个数据集的 revision、许可证、文件 LFS oid 与本地下载文件 sha256 的原始输出 |
| `reports/authoring/build_manifests.py` | 生成四个 JSON 的脚本(模板与 Pilot 的模型、名字生成、锚文本块从 Pilot 冻结 manifest 读取,不手抄) |
| `reports/pilot_erratum/push_erratum_commit.txt` | 本指令 A 部分勘误提交的推送输出(该分支此后不再提交,所以放在这里) |

生成的数据文件(事实、语料、DEV 问句、候选、锚文本、D1 / D2 DEV)只写在会话临时目录,没有入库;入库的只有它们的哈希、计数与统计。

## 2. 如何复核

在仓库根目录:

1. 下载输入(固定 revision):`Qwen/Qwen3-1.7B@70d244cc…` 的 4 个分词器文件,`SandyResearch/fineweb-edu-shuffled@4d1138c0…` 的 `data/sample-100BT/train/shard_00000.parquet`,`SandyResearch/parcae-tokenizer@6247b5d0…` 的 `tokenizer.json`,`cais/mmlu@c30699e8…` 的 `all/validation-00000-of-00001.parquet` 与 `all/test-00000-of-00001.parquet`,`allenai/ai2_arc@210d026f…` 的四个 validation / test parquet;各自的 sha256 见 `DATA_MANIFEST.json`、`DAMAGE_MANIFEST.json` 与 `reports/authoring/v1_data_check.txt` 开头。
2. `python -I metrix/e1-v1/reports/authoring/v1_data_check.py --qwen … --anchor-parquet … --parcae-tokenizer … --eval-sets research/mini_mythos/stage1/results/r1/eval_sets.jsonl --pilot-split-manifest metrix/e1-pilot/SPLIT_MANIFEST.json --mmlu-validation … --mmlu-test … --arc-dir … --out <临时目录>`:输出须以 `RESULT: PASS` 结束,各哈希与 `reports/authoring/v1_data_check.txt` 相同。
3. `python3 metrix/e1-v1/reports/authoring/compute_estimate.py` 的输出须与 `compute_estimate.txt` 相同(时间戳行除外)。
4. `python3 metrix/e1-v1/reports/authoring/build_manifests.py` 重新生成的四个 JSON 须与入库的逐字节相同。
5. `git diff --name-only 6e03468956208c422d0d41c08edaaf116166338c HEAD -- . ':(exclude)metrix/e1-v1'` 的输出为空(`metrix/e1-pilot/` 与 `metrix/` 以外没有改动)。

## 3. 撰写时的检查结果(出处:`reports/authoring/v1_data_check.txt`)

这些是数据规则与输入的检查,不是实验结果。

- 输入:4 个分词器文件、锚文本 parquet、parcae 分词器、`eval_sets.jsonl` 的 sha256 都等于 Pilot 冻结值;锚文本 512 篇解码文本的规范化 SHA-256 等于 Pilot 冻结值 `8828bc4f…`;按 Pilot 规则重新生成的 Pilot fact 哈希等于 `406c8801…`。
- V1 的 320 条 fact:规范化 SHA-256 `0fc5ad81…`;每个 cell 的 entity 抽取 40–83 次、answer 80–270 次(上限 20,000)。`candidates.json` `79600769…`(池 learned 29、unread 9);`train_S.jsonl` `7ac254f6…`;Y / F token 比 1.1944;暴露匹配违规 0;480 个 (learned fact, DEV 问句) 的打分 token 与 TRAIN 陈述句中的答案片段不一致数 0;模板集合哈希与 Pilot 相同。
- 泄漏:L1 0、L2 0.2、L3a 0、L3b 0、L4 0、L5 0、L6(D1 DEV、D2 DEV)0、L7 (a)(b)(c) 0、L8(D1 DEV、D2 DEV)0。
- D1 DEV 400 个窗口(每领域 100,排除 0,平均 248.9 个 id);D2 DEV:MMLU 800 题(排除 0,57 个学科,上下文平均 134.2 个 token);备选 ARC 800 题(6 题因不是 4 个选项被排除)。
- 两次独立运行的 stdout 与 10 个生成文件逐字节一致(`reports/authoring/v1_data_check_repeat.txt`)。

## 4. 事件与偏差(如实列出)

1. **`eval_sets.jsonl` 的 test 行被整行解析过一次**:写脚本之前,我在本会话中用 `json.loads` 解析了 `eval_sets.jsonl` 的每一行(含 1,200 个 test 行),只取 `domain`、`split` 两个字段计数并打印了键名集合;没有输出、保存或使用 test 行的 `tokens`、`text_sha256` 或任何内容。按 Pilot 第 3 节的定义,解析 split 字段与计数不算读取 TEST,但整行 JSON 解析比 Pilot 实现阶段 B 的做法(只匹配行首字节,test 行不解码)宽。之后的全部脚本都只匹配行首字节。请 Review Gate 确认是否需要记为偏差。
2. **D2 的 TEST 来源文件已下载**:MMLU `all/test` 与 ARC 两个 test parquet 已下载到会话临时目录,只对整个文件求 sha256、读取 parquet 文件尾的行数;没有读取任何行的内容。
3. **Task Order 引用的方向文件不在仓库中**:`claude/metrix-vision-and-roadmap.md` 不在本容器中:文件系统 `find` 无结果,本地已有的 refs(`main`、`metrix-e1-pilot-protocol-v1`、`claude/e1-v1-protocol-authoring-iusc4v` 及其远端跟踪分支)的 `git log --all` 中没有这个路径;其它远端分支未检查。未读取;协议只依据 Task Order 本身。
4. **指令中只有一个“=====”**:B2 说“下面「=====」之间的内容”,但消息中只有一个“=====”;我把它之后到消息末尾的部分存为 Task Order,之前的部分存为 Owner 消息,两者都保留原文的制表符。
5. **主比较的指标**:Task Order 9.4 举例为“Acq = 0.80 上的 D1”,本协议的主比较为 t = 0.80 上 TEST 的 `D1-diff`(与锚文本来源不同的三个领域),理由见协议第 7.4、9.4 节(Task Order 7.4 担心 A 的“损伤小”只是在它被约束的分布上测量);`D1-all` 与 `D1-same` 作为次要比较报告。请 Review Gate 确认。
6. **配置数为 1**:Task Order 6.3 要求 F、L、A 的配置数相同;本协议每种方法 1 个配置(Pilot 选定的 F3、L6、A5),因此第 6.6 节的“按损伤选择配置”不发生。这是 PROPOSED 值,属于待决第 3 项的范围。
7. **HYPOTHESIS_FAIL 不使用**:Pilot 第 9 节写“HYPOTHESIS_FAIL 保留给 E1-V1 的机制比较”;本协议的主比较是带结论词汇的估计,没有预先登记的方向性假设,所以不使用这个词(协议第 9.6 节)。
8. **审查 subagent 定义中的路径**:两个 subagent 的定义写的是 E1-PILOT 的路径(code-reviewer 依据 `metrix/e1-pilot/METRIX_E1_PROTOCOL.md`;data-auditor 只写入 `metrix/e1-pilot/audit/`),而 Task Order 红线 3 禁止改动 `metrix/e1-pilot/`,红线 3 与 `metrix/` 以外不改动的要求也使我不能修改 `.claude/agents/`。按 `metrix/CLAUDE.md` 第 8 节 2026-11-28 的条目(第 5、9、10 节的做法在 E1-V1 阶段继续适用),我在调用时说明:code-reviewer 以 V1 协议、Task Order 与 Pilot 协议为依据;data-auditor 的脚本与输出写入 `metrix/e1-v1/audit/`。是否接受这一对应,请 Review Gate 决定。
9. **`~/.claude/` 下的 CLAUDE.md 副本**:与分支上的 `metrix/CLAUDE.md` 不同(第 0 步比对:副本仍是 PROTOCOL_FROZEN(v1.1)的状态句,分支上是 Pilot 完成后的状态句;A 部分勘误后分支上另有第 2 节的改动与第 8 节的新条目)。两个 agent 文件的副本与分支上的逐字节相同,frontmatter 的 tools 行一致。我以分支上的文件为准。

## 5. 待 Owner / Review Gate 决定

- 第 15 节三项待决:GPU 累计时间上限 H(建议 9 小时);D2 数据集(建议 MMLU,备选 ARC);剂量点与配置的数量(主方案与缩减方案 R1–R4 见第 12 节)。
- 第 4 节第 1、5、8 项。
- 本指令 A 部分的勘误提交 `6e034689…` 的审查中登记的 PE1、PE7、PE10(`metrix/e1-pilot/reports/DEFERRED_MINORS.md` 1.45 节与第 3 节末条)。
