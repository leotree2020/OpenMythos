# code-reviewer, round 1 of the E1-V1 protocol authoring (staged tree 0e3dc49eaca9b07254e61301bc2602f8d8a39eea, parent 6e03468956208c422d0d41c08edaaf116166338c)
# final report extracted unchanged from code-reviewer_round1_transcript.jsonl by metrix/e1-pilot/reports/round6/review_extract.py (run, not modified)
---
BLOCKER | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:249 | 违反 Task Order 红线 7。规划时用了 Pilot 的结果（方差估计），却没写来源文件和字段，所给数值在仓库中也找不到对应的原始输出 | 「撰写时按 Pilot 与 Stage 1 的窗口 NLL 离散程度估计,`m(D1-diff)` 约 0.05 nat,`m(D2)` 约 0.035(只作规划,不进记录)」。Task Order 第 3 节第 7 条原文：「Pilot 的结果可以用于规划(方差估计、搜索范围),每一处使用都要写明来源文件与字段」「违反任一条即本任务 FAIL」。reports/authoring/ 下没有任何脚本或输出算出 0.05 | 二选一：写明文件与字段（例如 metrix/e1-pilot/results/details/N_dev.json 中逐窗口的 `nll`），并把计算脚本和 stdout 入库；或者删掉这句估计

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:9（另见 147、33、399 行） | 协议没写明 Pilot 的解释 B1–B25 是全部适用，还是只有被引用的那些适用。没被引用的 B14、B15、B16、B19、B20、B21、B22、B23 恰好定义了 V1 沿用的条款，Executor 只能自己猜 | 第 9 行只给出记号「“解释 Bn” = …在 E1-V1 中作为协议条文适用」。全文只引用了 B1、B3–B12、B18、B24、B25（Grep 结果）。第 147 行要求「S 在它自己的置换映射上的 DEV 与 TRAIN 闭卷正确率」，它的打分方法只在 B20 里（experiment_record_formal_20261128T045921Z.json:186）。eager attention 只在 B21（:194）。G0.3 的 stratum 怎么读只在 B22。ST3–ST7、ST11 记什么状态只在 B16 | 逐条写明 B1–B25 中哪些适用、哪些不适用（例如 B2、B13、B17 被替换）。影响：指标/可复现性

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:395 | ST11 预检估算没有可执行的公式。「第 12 节估算公式」实际只存在于 compute_estimate.py，里面还有很多不是预检实测的假设输入 | 原文「预检估算 = 第 12 节估算公式用预检实测的每步时间、一次 DEV 评测时间代入(不乘安全系数)」。compute_estimate.py 中：第 77 行 `saves_per_run = min(doses, 5)`，第 72 行 `test_brackets_per_run=5`，第 67 行 `D2_PAD = 1.3`，第 66 行 `1.05`，第 82 行 L 保存 `2.0`，第 88 行 `20 * 1.0`；base 加载、保存、重载、哈希仍取 Pilot 值，协议没说是否重测。TEST 评测时间是由 tps 推出来的，换成实测的 DEV 评测时间后 TEST 部分怎么算，协议没写（Pilot 是用 B17 逐项写死的） | 在协议正文写出 ST11 的完整公式，逐项注明每个输入来自预检实测还是固定常数，并给出预检计时的方法（例如是否剔除第 1 步）。影响：门槛（停止条件）/可复现性

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:399 | 「ST1–ST13 沿用 Pilot 第 11 节」只改了 ST3、ST7、ST10、ST11、ST13。其余条目里的步骤号、文件数和 V1 对不上 | Pilot ST1「第 2 步任一泄漏检查超限」：V1 的第 2 步是预检。Pilot ST9「从第 8 节第 3 步重新开始」：V1 没有对应的步骤。Pilot ST12「冻结提交下本协议文件与三个 JSON」：V1 有四个 JSON；Pilot ST12 还豁免「第 8 节第 1 步写入 manifest 的实际哈希字段」，而 V1 第 10 节第 1 步只写 step1_record.json，不写 manifest。于是 DATA_MANIFEST.json:279-283 的 `status`/`byte_sha256`/`canonical_sha256` 和 SPLIT_MANIFEST.json:436-442 的 `split_sha256` 由谁、在何时填写都没有规定；如果填写，又会触发 ST12 的字节比对 | 逐条给出 V1 版的 ST1、ST9、ST12（步骤号、四个 JSON、manifest 字段是否写入、豁免范围）。不写入的话，删掉这些 null 字段。影响：可复现性/门槛（停止条件）

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:279、338 | Gate 0 在第 7 步判定之后，如果不通过（例如 G0.5 的 seed-average 不满足、G0.8 不满足），是否还要跑第 8 步（L、A 共 6 条曲线，约 2.3 GPU 小时），协议没有规定 | 第 279 行「任一不满足 → PIPELINE_NOT_QUALIFIED,TEST 不生成、不评测」只禁止了 TEST。ST3 只检查 F 的种子 101。ST4、ST5 只覆盖 G0.6、G0.7。第 10 节第 7、8 步之间没有停止规则 | 加一条停止条件：第 7 步 Gate 0 任一条件不满足时停止，不运行第 8 步。影响：门槛（停止条件）

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:169-171、185 | iso 规则和 checkpoint 保存规则都没有规定比较用的算术。Acq 是 1/480 的整数倍，0.60、0.70、0.80、0.90 这些边界值都可能恰好取到；按 IEEE 双精度计算会误判（未验证，按浮点常识） | 「a_{j−1} < t ≤ a_j」「t − a_{j*−1} > 0.10 或 a_{j*} − t > 0.10」「|a_j − t| ≤ 0.10」。例如 a = 0.8、t = 0.7 时，双精度 0.8−0.7 = 0.10000000000000009 > 0.10。这会把合格的夹逼记为 NOT_REACHED。如果训练当场保存 checkpoint 用浮点，事后确定 iso 点用精确值，夹逼端点的 checkpoint 会没被保存，TEST 无法评测。第 14 节核对时 Executor 与 data-auditor 可能得到不同结果 | 规定 Acq、w、τ 的比较一律用精确有理数（Acc 取分数，t、τ 取 Fraction("0.7") 等），或者规定统一的舍入方式。第 6.7 节与第 6.4 节使用同一算法。影响：iso 匹配/可复现性

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:37；DAMAGE_MANIFEST.json:54、152 | TEST 来源的读取规则自相矛盾。正文说沿用 Pilot 第 3 节（「对整个文件求哈希不算」），括注却把 D2 的 TEST 文件限定为「只允许读 parquet 文件尾的行数」，把 eval_sets.jsonl 限定为只允许匹配行首字节。照括注字面执行，第 1 步就无法核对 DAMAGE_MANIFEST 中 test_source 的 sha256 和 eval_sets.jsonl 的 sha256 | 协议第 37 行：「D2 的 TEST 来源文件(只允许读 parquet 文件尾的行数)」。manifest：「before section 10 step 10 only the parquet footer (row count) of a TEST source is read」。而撰写脚本 v1_data_check.py:253-254（`mmlu_test` 的整文件 `read_bytes()` 求 sha256）、:512（ARC test 文件求 sha256）都对 TEST 文件整体求了哈希 | 把括注改成与 Pilot 第 3 节一致：允许对整个文件求哈希、读 parquet 文件尾计数，禁止解码任何一行。影响：数据

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:198、231；DAMAGE_MANIFEST.json:25-34 | 主比较指标 D1-diff 把 c4 当作「与锚文本来源不同」的领域，但仓库自己的文档把 c4 标为 FineWeb-Edu 的近分布网页文本。Task Order 7.4 担心的「A 的损伤小只是在它被约束的分布上测量」，在主比较里没有完全排除 | 协议：「D1 的 books、c4、wikitext 三个领域与锚文本来源不同」。research/mini_mythos/stage1/README.md:28：「c4 | C4 英文 validation | … | 网页,近分布」；同文件第 19、27 行写明该分布对照的是 FineWeb-Edu | 二选一：把 c4 移出 D1-diff（D1-diff 只用 books、wikitext），或者单独报告 c4，并在第 7.4 节说明理由。请 Review Gate 决定。影响：损伤测量/指标

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:249 | margin 公式的形式符合 Task Order 7.6 的举例，但所给理由在统计上不成立。σ_N 是 N 的水平统计量（窗口 NLL 均值）的抽样 SD，含窗口之间的异质性；方法间的比较是逐窗口配对差，配对差的抽样波动通常远小于 σ_N。所以 2σ_N 并不等于「与抽样波动不可区分」的幅度，倍数 2 实际上没有依据（未验证） | 「方法间小于这一幅度的损伤差,与评测集抽样造成的波动不可区分」；σ_N 的定义见第 255 行「统计量为 N 的窗口 NLL 的领域均值的平均」 | 改写理由（把 m 说明为一个预先登记的效应量，并说明它与 Pilot 第 13 节第 2 项 +0.03 的关系），或者改用配对差的噪声来推 margin。影响：门槛

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:298-299（另见 249 行、DAMAGE_MANIFEST.json:210） | 结论词汇写死了 m = m(D1-diff)，而第 7.6 节为四个指标各算一个 margin，次要比较又要求「结论词汇照常计算」。照字面执行，D2 的次要比较要拿 nat 单位的 m(D1-diff) 去比准确率差；「每个方法自身的损伤（相对 N）」的结论词也没有定义 | 「m = m(`D1-diff`) 取自 MARGIN_RECORD」；「其余全部为次要比较(… 每个方法自身的损伤),… 结论词汇照常计算」；manifest 中的 `words` 未定义 m | 改为「对指标 M 的比较用 m(M)」，并写明 X−N 比较是否给结论词。影响：门槛/指标

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:238、245 | Gate D 中「噪声基线」一项不可能不通过。G-D2 只要求 σ_N 有限且大于 0，没有上限。Task Order 7.5 要求的「不该造成损伤的对照在种子之间的波动」由 Z0（lr = 0）给出，按构造就是 0，测不到训练种子带来的噪声；margin 的大小也不受任何约束 | G-D2：「四个值都必须有限且 > 0」；第 245 行：「learning rate 为 0 时参数逐位不变,波动按构造为 0」 | 请 Review Gate 决定是否给 σ_N 加数值上限（例如 m(D1-diff) 不得超过 Pilot 冻结 margin 的若干倍），或者另设一个 lr 大于 0、预期无损伤的对照来测种子间波动。影响：损伤测量/门槛

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:161（另见 245 行） | 剂量覆盖的换算依据前后不一致。正文说按「学习率 × 步数」的累积量换算，实际却是按遍数算的；V1 每遍 30 步，Pilot 每遍 15 步，按步数算 V1 的累积量约是所称值的 2 倍。低端几个剂量点之间 Acq 的跳变，以及 τ_DEV 理由中的「跳变在 0.05–0.15 之间」都因此失去依据（未验证）。例如 L 在第 1、2 遍之间可能跨过 0.2 以上，在 0.70 处被记为 NOT_REACHED | 第 161 行「以“学习率 × 步数”的累积量粗略换算:… 20 遍的平均倍数约 0.55,相当于常数学习率约 11 遍」；第 158 行「batch 8,每遍 30 步」；Pilot 协议第 267 行「每遍 15 步」 | 写明换算究竟按步还是按遍，按两种口径分别给出各方法预计越过 0.70 的遍数，再据此确认低端剂量点够密、τ_DEV 合理。影响：iso 匹配

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:205 | D2 采用「列出选项后只对字母 token 打分」，这是对 Task Order 7.1「用候选的条件对数似然打分」的一种解释，另一种解释是对选项文本本身打分。SUBMISSION_NOTE 第 4 节没有把这一点列为待 Review Gate 确认的解释。是否构成问题我不确定 | 「`s_D2(θ, i, ℓ) = log p_θ(" " + ℓ | chat(p_i) + "The answer is")`」；Task Order 第 101 行「用候选的条件对数似然打分」 | 在 SUBMISSION_NOTE 中列为待确认的解释，并附一句理由（例如这是 MMLU 的通行做法，每题只需一次前向）。影响：指标

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:129、204、407 | 有几个可执行的 PROPOSED 值没有附理由，可能违反红线 8；不确定这些是否属于红线所说的「PROPOSED 值」 | Z0「2 遍」没有理由；D2 指令 `I` 的措辞没有理由；ST18「少于 2 × 6.88 GB」没有理由；d0 = 11 的理由只能从第 161 行间接推出 | 每个值补一句理由。影响：可复现性（若认定违反红线 8，则应升级为 BLOCKER）

MINOR | metrix/e1-v1/reports/authoring/v1_data_check.py:45 | 死代码：常量没有被使用 | `D1_PER_DOMAIN = 100` 在全文件中没有引用 | 删除，或用它做 DEV 每领域 100 行的断言

MINOR | metrix/e1-v1/reports/authoring/compute_estimate.py:72、77、82、84、88 | 未使用的参数；有影响结果的假设常数没有在输出中标为假设；Y 的步时用错 | `test_points` 只在打印中出现；`min(doses, 5)`、L 保存 `2.0`、预检 `20 * 1.0` 没标注为假设；`sy` 对 batch 16 的 Y 用了 F 的 batch 8 步时 `st_F`，会低估（training_runs/Y-F3-*.json 有实测值） | 删除或使用该参数；把假设常数在输出中标出；Y 改用 Y 的实测步时

MINOR | metrix/e1-v1/reports/authoring/v1_data_check.txt:67-68 | D2 的 L6、L8 检查只打印 ok，没有打印计数，协议「D2 DEV 0」只能从 check 的判定推出 | 「CHECK L6 anchor vs D2 DEV word 13-grams ok 」（行尾为空） | 打印计数

MINOR | metrix/e1-v1/reports/authoring/v1_data_check_repeat.txt:2 | 第二次运行的完整 stdout 没有入库，只有 diff 的退出码（metrix/CLAUDE.md 第 9 节要求原始输出入库） | 「diff <(grep -v PyTorch run1.txt) <(grep -v PyTorch run2.txt)」中的 run2.txt 不在仓库里 | 把 run2 的 stdout 入库

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:209、421 | 「ARC DEV 来源中 6 题不是 4 个选项」「863 题为 4 个选项」是外推：脚本凑满 800 题就停，只看了 806 行，另有 63 行没有检查 | v1_data_check.py:533-534 `if len(arc_dev) == D2_N: break`；txt 第 73 行 | 改写为「在访问的 806 行中」，或者检查全部 869 行

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:380 | 括号 checkpoint 的上限写错：每条曲线最多 3 个比较点 × 2 端 = 6 个，不是 10 个 | 「上限 9 × 10」 | 改为 9 × 6

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:279 | 「只报告」清单与 Pilot 第 8 节不同（去掉了 DEV 上的 EM 和各 arm 的 dNLL），却写着「数值沿用 Pilot 第 8 节」，没有把这一处列为改动 | Pilot 协议第 550 行的只报告项含 EM 与各 arm 的 dNLL | 把这一处写明为相对 Pilot 的改动

MINOR | metrix/e1-v1/SPLIT_MANIFEST.json:362、389；DATA_MANIFEST.json:26、271 | 从 Pilot manifest 复制来的出处注记没有改写，在 V1 中会被误读。L6 的 count 文字只提到 general_test.jsonl，没有提到 d2_test | `"added": "round 2, 2026-11-12"`；`"(round 8, Review Gate round 7 ruling, item 1d)"`；count：「those of all general_test.jsonl windows into another」 | 标明这些注记属于 Pilot，并把 count 的口径扩大到 d2_test.jsonl

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:7 | 「执行只需本文件、四个 JSON 与第 0 节的外部来源」与正文不符：正文还依赖 Pilot 实现代码（第 37 行 data.py、第 308 行「Pilot 实现」）、Pilot 实验记录（第 9 行）和 compute_estimate.py（第 395 行） | 见所列各行 | 把这些依赖列入第 0 节固定的来源（写明路径和提交）

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:227 | Task Order 7.3 要求「D1 以文档为单位」，协议写的是「以窗口为单位」，没有写明一篇文档只取一个窗口 | research/mini_mythos/stage1/README.md:23「每篇文档取开头 256 个 token 作为一个窗口」 | 补一句「窗口 = 文档」，并注明出处

MINOR | metrix/e1-v1/DAMAGE_MANIFEST.json:166 | D2 重抽次数写死为 800，采用缩减方案 R2（每个划分 400 题）后就不对了 | `"d2_resampling": "unstratified, r.choices(items, k=800)"` | 改为 k = 题目数

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:169 | 括注「包括第 1 个剂量点已 ≥ t 的情形」可以有两种读法：曲线一直不低于 t，或者只要第 1 个剂量点 ≥ t 就算（即使之后下降再越过） | 第 169 行原文 | 二选一并写明

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:335 | ST3 在第 11 遍触发时，种子 101 是在第 11 遍停下，还是跑满 32 遍，没有写明 | 「ST3:… → 停,不跑其余训练」 | 写明

MINOR | metrix/e1-v1/DATA_MANIFEST.json:392-452 | 报告清单 reported_values 里没有第 7.3 节、第 8 节要求的「3 个种子点估计的最小值、最大值与样本标准差」，第 14 节的终止前核对会漏掉这一项 | 协议第 227、257 行；reported_values 中没有这一项 | 加入清单

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:241 | G-D5 在全部剂量点上算 Spearman 相关，同一条曲线上的剂量点彼此相关，属于伪重复（该项只报告，不进门槛） | 「10 个剂量点 × 9 条曲线、S、Y、P+」 | 注明各点不独立，或者每条曲线只取一个点

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:199 | fineweb 与锚文本「同属 SandyResearch/fineweb-edu-shuffled」，引用的 README 里没有写这个仓库名 | README 第 27 行只写「FineWeb-Edu 验证分片(作者留出)」；仓库名在 research/mini_mythos/stage1/results/data_lock.json:4 | 改为引用 data_lock.json

MINOR | metrix/e1-v1/reports/authoring/build_manifests.py:56、93-112、308、324 | V1 的哈希是手抄进脚本的字面量，不是从 v1_data_check 的输出解析的。我逐个核对过，与 v1_data_check.txt 一致；「重新生成后逐字节相同」我没有运行（未验证） | 例如 `"0fc5ad81…"`、`"e8350160…"` | 改为从 v1_data_check 的输出读取，或者加一个比对脚本

MINOR | metrix/e1-v1/SUBMISSION_NOTE.md:54 | 第 4 节第 1 条自报：曾用 json.loads 解析 eval_sets.jsonl 的 test 行。这与 Pilot 的先例一致（Pilot 协议第 679 行 v1-r6：对 test 行做 JSON 解析和计数不算读取 TEST），但比 V1 第 0 节的新规则宽；仓库中没有证据可以复核（未验证）。三个入库脚本都没有解码 TEST 行：v1_data_check.py:433-442 只匹配行首字节，:477、:512 只读 parquet 文件尾或求整文件哈希 | 见所列各行 | 交 Review Gate 记录

已核对、一致的项（引用已入库的原始输出，视为已验证）：
- 协议第 1、6.3、6.5 节引用的 Pilot 数值都与原始记录一致：F3、L6、A5 的 DEV 准确率与 dNLL 区间，F1、L4、A2，F6 的 dNLL 5.55021，TEST 上 0.9296、0.9500、0.8685，Δ(A−F) = −0.0611，max 0.040（training_runs/*.json 第 33–36、490–493 行；test_evaluation_result.json 第 50、553、1011、1469、1927、2385、2843、3301、3759、4217、7882 行）。
- 选择冻结记录 F3、L6、A5（selection_freeze_record.json:45-49）；step5 峰值显存 46,235,107,328 字节；step7 的 G0.8 差值为 0（step7_record.json:752-769）。
- compute_estimate.txt 中的每步时间、6.66 h、7.99 h、R1–R4 的节省量与协议第 12 节一致。
- 四个 JSON 里的 V1 哈希、计数与 v1_data_check.txt、d2_dataset_metadata.txt 逐一相同。
- S、Y 继承 F 的配置；聚合函数为 mean；问答与打分输入用 Qwen3 chat template 且 enable_thinking=false；答案 token 不一致数为 0（txt 第 44 行）；四个字母各为单个 token（txt 第 61 行）。

结论：BLOCK
