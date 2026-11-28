# code-reviewer, round 2 (final) of the E1-V1 protocol authoring (staged tree f395c476606603e65d336e1ba3ac34a065c40889, parent 59761ad923674d43725167a8c79f6bdf16f531ee)
# final report extracted unchanged from code-reviewer_round2_transcript.jsonl by metrix/e1-pilot/reports/round6/review_extract.py (run, not modified)
---
# code-reviewer 第 2 轮（最后一轮）审查报告：E1-V1 协议修复（暂存树 f395c476606603e65d336e1ba3ac34a065c40889，HEAD 59761ad9）

审查方式：只读，用 Read/Grep/Glob 逐行核对。没有运行任何脚本。凡是引用仓库中已暂存输出的地方，都写明了路径和行号；没有输出可引用的判断，单独标注为未验证。下文中的“协议”指 /home/user/OpenMythos/metrix/e1-v1/METRIX_E1V1_PROTOCOL.md。

## 一、第 1 轮的 BLOCKER 与 13 个 MAJOR 的处理

R1-BLOCKER（第 7.6 节的 margin 估计没有来源）| **已解决** | 第 7.6 节（协议:253）已删去这句估计。第 7.5 节的理由（协议:249）写明了来源 `metrix/e1-pilot/results/details/N_dev.json: evaluation.general_dev[*].nll`，该字段存在（N_dev.json:2、:14727，共 100 个窗口）。脚本 sigma_planning.py 与输出 sigma_planning.txt 已入库。我用 sigma_planning.txt:3-6 的四个领域 SD 手算，与 :7-10 的输出一致：D1-all sqrt(0.81855/100)/4 = 0.0226，D1-diff 0.0261，D1-same 0.0452。协议中的 0.045、0.052、0.090、0.035 与 DAMAGE_MANIFEST.json:178 都和这份输出一致。

R1-M1（B1–B25 哪些适用）| **已解决（表完整），但引入一个新矛盾** | 协议:39 把 25 条全部归类：照原文 20 条，改写后适用 B1、B3，被替换 B2、B13、B17。与 experiment_record_formal_20261128T045921Z.json:26-228 的 25 条一一对应。不过 B24 归为“照原文”后与第 9.7 节冲突，见本轮 MAJOR-1；B10、B3 的归类另有 MINOR。

R1-M2（ST11 没有可执行的公式）| **主方案已解决** | 协议:401-403 给出了完整公式和各项输入的来源。计数与 compute_estimate.py:79-88、compute_estimate.txt:16-19 逐项吻合：
- base 加载 26 = Gate D 7 + 曲线 12（含 A 的 base 副本）+ S/Y 6 + TEST 的 N 1；
- 训练步数 3150 = 1980 + 180 + 990；
- DEV 评测 107；
- 重载 61 = 4 + 3 + 9 + 45；
- 完整 TEST 评测 46 次、只有事实 QA 的 9 次；
- 两个比值 1.26、0.53 = compute_estimate.txt:17。

完整保存 45 次与第 12 节表（协议:385）、磁盘公式 compute_estimate.py:90 一致。compute_estimate.py 的时间模型只算了 42 次完整保存，差约 65 秒，可以忽略。剩余问题：缩减方案下如何代入，见 MAJOR-2。

R1-M3（ST1、ST9、ST12 与 V1 的步骤对不上）| **已解决** |
- ST1（协议:409）对应第 10 节第 1 步（协议:334）。
- ST9（协议:412）从第 2 步重新开始。第 2 步是第一次加载模型，即设备全名的首次记录点（Pilot 协议:520）。
- ST12（协议:415）改为四个 JSON，且没有豁免。
- grep 确认四个 JSON 中已无 per-file 的 `status`、`byte_sha256`、`canonical_sha256` 占位字段；SPLIT_MANIFEST.json:437 的 `actual_hashes` 与 ST12 的说法一致。

剩余 MINOR：协议:98 的“生成状态”、B3 的 ruling_note。

R1-M4（Gate 0 不通过后是否还跑 L、A）| **已解决** | 新增 ST19（协议:427），第 10 节第 7 步（协议:340）与第 9.1 节（协议:283）都引用了它。ST19 与 ST4、ST5、B14、B16 的状态词不冲突。

R1-M5（iso 与保存规则的比较算术）| **已解决，第 2a 条可执行** | 第 2a 条（协议:173）可以用 `fractions.Fraction` 精确执行：DEV 的 Score 是 k/2，TEST 的是 k/3；因为 a_{j*-1} < t ≤ a_{j*}，w 的分母恒大于 0；第 6.5 节的平均与比较、第 6.7 节的 |a_j − t| ≤ 0.10 都是精确有理数运算。剩余 MINOR：第 2a 条的适用范围、DOSE_SPACE.json 未登记这一条、(1 − w) 的浮点写法。

R1-M6（TEST 来源的读取规则自相矛盾）| **已解决** | 协议:37 现在明确允许三件事：对整个文件求 sha256、按行首字节正则匹配后计数、读 parquet 文件尾。DAMAGE_MANIFEST.json:54、:152 与此一致。正则与 Pilot 的 data.py:491 兼容：V1 另外捕获 domain 字段，这一点已明文允许。

R1-M7（c4 是近分布网页文本）| **已解决（按“单独报告 c4 并说明理由”处理）** | 新增四个逐领域指标（协议:235、:291）。主比较是否改为只用 books 与 wikitext，已交 Review Gate（SUBMISSION_NOTE.md:70）。

R1-M8（margin 的理由在统计上不成立）| **已解决** | 协议:253 改写为预先登记的效应量，并说明了与 Pilot 第 13 节第 2 项 +0.03（Pilot 协议:641）的关系。

R1-M9（结论词写死了 m(D1-diff)）| **已解决** | 协议:303 改为 m(M)，并写明只有四个方法间指标给结论词，X 相对 N 的损伤和逐领域指标不给。DAMAGE_MANIFEST.json:210-211 与此一致。

R1-M10（G-D2 不可能不通过）| **部分解决** | G-D2 加了数值上界（协议:242；DAMAGE_MANIFEST.json:177），现在可以不通过。上界与 sigma_planning.txt:7-9 一致。但“不该造成损伤的对照在种子之间的波动”仍由 Z0 按构造给出 0，见 MAJOR-4。

R1-M11（剂量换算按步还是按遍）| **已解决** | 协议:163 写明按遍换算，并给出按步换算的数值。我复算：Pilot 20 遍 × 15 步 × 平均倍数 0.5475 ≈ 164 个峰值步 = V1 的 5.5 遍；F1 在学习率 1/3 时约 1.8 遍，L4、A2 在 0.3 时约 1.6 遍，与协议一致。τ_DEV 的理由不再依赖跳变估计（协议:172）。剩余 MINOR：warmup 未计入。

R1-M12（D2 的打分是对 Task Order 的一种解释）| **已解决** | 协议:209 写明了解释与理由，SUBMISSION_NOTE.md:69 已列为待 Review Gate 确认。

R1-M13（几个 PROPOSED 值没有理由）| **已解决** | Z0 的 2 遍（协议:134）、指令 I（:208）、ST18（:426）、d0（:162）都补了理由。Z0 理由的措辞有 MINOR。

data-auditor 第 1 轮各项（顺带核对）：
- B1（ARC 的两个数字）：已解决。协议:213、:441 与 SUBMISSION_NOTE.md:50 写的 862 与 7，与 audit/stdout/a5_damage.txt:62、:63、:69 一致。
- M2（L8 中 D1 的“文本”）：已解决（协议:113；SPLIT_MANIFEST.json:416）。
- M3（L6、L8 的 TEST 部分按集合分别计数）：已解决（协议:119；SPLIT_MANIFEST.json:389、:417）。
- M4（记录字段的定义）：已解决。DATA_MANIFEST.json:315、:321、:327 与 Pilot data.py:234、:526-527 及 v1_data_check.py:274、:447-448（decode 用默认参数）一致。

## 二、本轮问题

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:39（对照 :323-325） | 本轮修复新引入的矛盾：适用表把 B24 列为“照原文适用”，而 B24 原文的最终状态规则与第 9.7 节冲突。Gate 0 通过、T1–T3 满足、但主比较为 NOT_REACHED 或 MATCH_FAILED 时，按 B24 是 PASS，按第 9.7 节是 NOT_REACHED 或 MATCH_FAILED；终止前核对重算最终状态时，两种读法会得到不同结果 | 协议:39「照原文适用 … B22、B23、B24、B25」；B24 原文（experiment_record_formal_20261128T045921Z.json:218）「Final status: PASS iff Gate 0 is PASS and T1-T3 hold; otherwise PIPELINE_NOT_QUALIFIED …」；协议:325「以上都通过:主比较族的两个比较都有结论词 → PASS …;否则,任一为 NOT_REACHED → 最终状态 NOT_REACHED」 | 把 B24 改列为“部分适用”：只适用 T1–T3 的原因词与 T3 的读法，最终状态规则由第 9.7 节替换。影响：门槛（最终状态）、可复现性；不影响数据、iso 匹配、损伤测量

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:403；compute_estimate.txt:31、:45 | 采用缩减方案时，ST11 公式怎么代入有歧义。正文说固定比值 1.26、0.53，缩减方案只代入“计数”；但正文引用的来源 compute_estimate.txt 对 R2、R4 写的是另一组“ST11 公式用的固定比值” 1.41、0.84。照正文字面执行，R2 下预估会少算约 0.17 小时。另外 R1、R3、R4 的各项计数（例如 R3 的重载 34 次、完整 TEST 19 次；R1 的 DEV 评测 80 次）没有列出，要由 Executor 和 data-auditor 各自推导 | 协议:403「时间分别按 1.26 × t_ev 与 0.53 × t_ev(两个比值由 token 数推出, compute_estimate.txt)……采用缩减方案时,按该方案的计数代入同一公式」；compute_estimate.txt:31「ratios used as fixed constants in the ST11 formula (protocol section 12): full TEST / DEV 1.41, fact-only TEST / DEV 0.84」 | 逐个方案（R1–R4）列出公式中的全部常数，包括两个比值；或者写明比值随方案取 compute_estimate.txt 中对应的行。影响：门槛（ST11 停止条件）、可复现性；只在采用缩减方案时出现

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:134、:241；DOSE_SPACE.json:68 | 第 1 轮未报告。未验证：“学习率为 0 时参数逐位不变，所以 Z0 的 state_sha256 等于 N 的”在 IEEE 754 带符号零的规则下不一定成立。PyTorch 的 AdamW 用 `param.addcdiv_(exp_avg, denom, value=-step_size)`，lr = 0 时 value = −0.0；exp_avg 为负时，−0.0 × 负数 = +0.0，而 (−0.0) + (+0.0) = +0.0。fused 实现做 `param − 0·x`，结果相同。于是一个存为 −0.0、梯度方向为负的参数会变成 +0.0：数值相等，原始字节不同，而 B25 的 state_sha256 哈希的正是原始字节。这样 G-D1 会误判为 IMPLEMENTATION_FAIL，Gate D 随之停止 | 协议:134「AdamW 的更新量与 weight decay 项都乘以 learning rate,参数逐位不变,因此 Z0 的 state_sha256 必须与 N 相同」；B25（experiment_record_formal_20261128T045921Z.json:226）「h.update(the raw bytes of t …)」。不确定之处：Qwen3-1.7B 的权重中是否存在 −0.0；实现是否走这条代码路径 | 请 Review Gate 决定，可选做法：G-D1 的参数一致性改用逐张量的数值相等（torch.equal 视 ±0 为相等），state_sha256 只报告；或在实现阶段的冒烟测试中统计 −0.0 的个数后再定。影响：门槛（G-D1 → Gate D）、损伤测量（阴性对照）

MAJOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:242、:249 | 第 1 轮 M10 的剩余部分。Task Order 7.5 要求的“不该造成损伤的对照在种子之间的波动”仍由 lr = 0 的 Z0 按构造给出 0。训练带来的种子波动只由 P+ 报告，不进门槛，另在 Gate M 中用“每个种子同向”的要求间接处理。协议已如实说明并交 Review Gate；是否构成问题我不确定 | 协议:249「这只证明流程本身不引入波动,不测量训练带来的种子波动,后者由 P+ 的三个种子报告」；Task Order:111；SUBMISSION_NOTE.md:71 | 由 Review Gate 决定是否接受。影响：损伤测量、门槛

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:39 | B10 列为“照原文”，但原文写的是「Delta* = mean of the 120 drawn values」，V1 应为 240 个（每个 stratum 120 个）。括注和第 8 节给出了数量，但没有改写这一句 | experiment_record:105；协议:258 | 把 B10 移到“按 E1-V1 的数值改写后适用”，写明取 240 个的平均

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:39 | B3 的 ruling_note 要求第 1 步把 train_Y 的哈希写入 manifest，与 ST12「执行中不改写…四个 JSON 中的任何字段」冲突。V1 的 train_Y 已有参考哈希，所以实际上不会执行，但字面上矛盾 | experiment_record:47「section 8 step 1 writes the canonical hash of train_Y.jsonl into the manifest」；协议:415 | 在适用表中写明 B3 的 ruling_note 不适用

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:98 | 删去占位字段后遗留的说法：DATA_MANIFEST 已没有“生成状态”字段 | 「每个数据文件的参考哈希与生成状态」；DATA_MANIFEST.json:276-353 中没有 status 字段 | 删去“与生成状态”

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:173 | 第 2a 条的范围只覆盖第 6.4、6.5、6.7 节。G0.4（Acc_CB ≥ 0.90，216/240 可以恰好取到）、G0.5、ST3、T1 的 0.70 边界没有规定算术，seed-average 中的 /3 在浮点下可能误判 | 协议:276-277、:285、:339 | 把精确算术扩大到第 9.1 节与 ST3 的全部学习量阈值

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:173-174 | 第 2a 条的两处措辞问题：(1)“与 w 相乘时用 float(w)”没有说明 (1 − w) 取 float(1 − w) 还是 1 − float(w)，两者可差 1 ulp；(2) 把“窗口 NLL、D2 字母分数”也列为与 w 相乘的量，而第 3 条只插值 d、e 和 Score，容易被读成要插值字母分数。另外 e 是整数，不是浮点量 | 「逐单位的浮点量(窗口 NLL、D2 字母分数、d、e)与 w 相乘时用 float(w)」 | 写明 (1 − w) 的取法，并把列表改为 d 与 e

MINOR | metrix/e1-v1/DOSE_SPACE.json:130-143 | iso 一节没有登记第 2a 条，targets 和 tau 都是 JSON 浮点数。若实现直接用 Fraction(0.7)，得到的不是 7/10 | `"targets": [0.7, 0.8, 0.9]`、`"tau_dev": 0.1` | 在 iso 一节加一行 arithmetic，引用协议第 6.4 节第 2a 条

MINOR | metrix/e1-v1/DATA_MANIFEST.json:363、:373 | 报告清单没有跟上本轮的修改：预检一项没有列 ST11 公式的 t_load、t_save、t_reload、G，终止前核对无法重算 E；Gate D 一项没有列新增的“P+ 三个种子的 D1-diff、D2 样本标准差” | 「preflight step seconds (F, L, A), DEV evaluation seconds, peak memory, estimate, ST11 bound」 | 补列这些字段

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:242；DAMAGE_MANIFEST.json:177 | 「m(D2) 最大为 2 × sqrt(0.25/800)」「by construction」不严格：10,000 次 bootstrap 的样本 SD 有 Monte Carlo 误差，正确率接近 0.5 时可能略超这个值；R2 方案下题数为 400，界变为约 0.05 | 「m(D2) <= 2 * sqrt(0.25 / 800) by construction」 | 改为“约为”，并写成按题数 n 的式子

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:403 | 公式把 Y 的步数按 t_F 计时，而 Y 的 batch 为 16，每步 token 数约为 F 的 1.19 倍。第 1 轮已登记的 compute_estimate.py 中同一问题，现在被冻结进了公式（偏低，量级小） | 「3150 步 = S、Y 6 × 330 + …(都按 t_F)」 | 预检另测 Y 的步时，或写明这是有意的近似

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:134 | Z0 的理由「2 遍已经走过训练流程的每一段代码」不准确：Z0 不做剂量点上的当场 DEV 评测，也不走第 6.7 节的条件保存（DEV 评测 107 次的计数中，Z0 每个种子只评 1 次） | 协议:134；compute_estimate.py:79 | 把措辞改为列举实际经过的代码段

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:163 | 换算没有计入 warmup：第 1 遍的平均倍数为 0.5，k 遍的累积量约为 k − 0.5 遍峰值学习率，各方法预计越过 0.70 的遍数约后移 0.5 遍。阶梯覆盖的结论不变 | 「Pilot 的 20 遍约等于常数学习率 11 遍」（Pilot 的 0.55 已含 warmup，V1 一侧没有扣除） | 注明这一点

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:213 | 协议的数字（862、7）以 data-auditor 的 stdout 为出处，而 data-auditor 的信任状态是“待验证”（metrix/CLAUDE.md 第 10 节）；Executor 自己的参考构建只访问了 806 行 | 「`audit/stdout/a5_damage.txt`」 | 由 Executor 的脚本独立计数 869 行并入库，或注明出处的信任状态

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:334 | 第 1 步的核对范围写为“第 2 节与 DAMAGE_MANIFEST.json”，ST12(1) 写的是三个 manifest（含 SPLIT_MANIFEST 的模板哈希） | 协议:334 对比 :415 | 两处用同一个范围

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:412 | 若 ST9 在第 9 步之后触发，从第 2 步重来就会在看过 DEV 方法比较之后重算 margin，与协议:254「margin 不得在看到任何方法比较之后确定或修改」冲突 | 协议:412、:254 | 写明 ST9 重启时 margin 的处理（沿用原 MARGIN_RECORD，或整批交 Owner 决定）

MINOR | metrix/e1-v1/METRIX_E1V1_PROTOCOL.md:342、:399 | 「累计 GPU 时间」没有说明第 9 步等待 Owner 批准的时间是否计入（Pilot 的实现按进程段累计，metrix/e1-pilot/src/metrix_e1/compute.py:110-147）；B17 被替换后，ST7 的前瞻（“若会使累计时间超过 H”）如何估算下一步耗时也没有写 | 「之后停下,等待 Owner 对 TEST 生成与评测的批准」；「任何一步若会使累计时间超过 H」 | 写明计时口径与前瞻的估算方法

## 三、另外核对过、未发现问题的项

以下都是对照入库文件逐项读过的；脚本本身没有运行。
- sigma_planning.py 与 sigma_planning.txt 的打印格式逐行对应；脚本中没有死代码，也不涉及 TEST。
- build_manifests.py 的每处改动都在四个 JSON 中有逐字相同的对应文本。重新生成后是否逐字节相同：未验证（未运行）。
- compute_estimate.py 新增的打印行与 compute_estimate.txt 一致。
- 本轮 diff 中没有任何代码路径生成或读取 TEST。
- S、Y 继承 F 的配置；聚合函数为 mean；D2 的打分输入沿用 Qwen3 chat template，enable_thinking=false。
- G-D2 的上界与 sigma_planning.txt 一致；ST1、ST9、ST12、ST19 与第 10 节的步骤一致；L6、L8 的 TEST 计数口径在协议:119 与 SPLIT_MANIFEST.json:389、:417 之间一致。

结论：PASS
