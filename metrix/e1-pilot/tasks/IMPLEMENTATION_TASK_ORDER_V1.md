METRIX · E1-PILOT · IMPLEMENTATION

Implementation Task Order — V1（Review Gate 起草，Owner 批准后生效）

0. 元数据

项	值
Task ID	METRIX-E1-PILOT-IMPLEMENTATION-V1
Owner	Project Owner（Miyaji）
Executor	Claude Code（metrix 环境）
依据	协议 v1.1，冻结提交 87a244db28a901f9e89282b50df76778ab5c2887；metrix/e1-pilot/PROTOCOL_FROZEN
阶段	IMPLEMENTATION（写代码 + CPU 冒烟测试）
允许训练	只允许随机初始化的小模型在 CPU 上做冒烟测试；禁止加载 Qwen3-1.7B 权重
允许评测	同上，只用于冒烟测试；冒烟结果不是实验结果
TEST	禁止生成、读取、统计（含冒烟测试）；只允许测试「TEST 生成器在条件不满足时拒绝运行」
GPU	不使用
结束状态	IMPLEMENTATION_READY → 由 Owner 决定是否租 A100

1. 一句话任务

按冻结的协议 v1.1 实现第 8 节第 1–8 步的全部代码，使未来的 Executor 只需在 A100 上运行一条命令（加上 Owner 的批准），就能完成 Gate 0 与 TEST 评测，并在 CPU 上用随机初始化的同构小模型证明全流程可以跑通。

2. 红线（违反任一条即本任务 FAIL）

	1.	不修改协议、三个 JSON、PROTOCOL_FROZEN。发现协议有错、缺失或不可执行：停止，返回 HALTED 并写明原因（第 12 节）。协议的任何改动都须由 Owner 批准新版本。
	2.	不加载 Qwen3-1.7B 的权重，不下载权重文件。
	3.	不生成、读取、统计 TEST（定义见协议第 3 节）。
	4.	不使用 GPU，不租用任何算力。
	5.	不新增 arm、指标、门槛或步骤；不删减第 8 节的任何一步。
	6.	不在代码里写死协议中的数值：门槛、超参、种子、哈希、模板一律从冻结文件读取。
	7.	冒烟模式的输出不得写入正式结果目录，不得产生 Gate 0 结论。
	8.	metrix/ 以外不改动（outside_metrix_check.py 照常通过）。

3. 执行解释（Review Gate 第 9 轮裁决，不改协议文本）

	1.	ST12 比对范围 (1)「数据内容哈希」= PROTOCOL_FROZEN 当前有效节列出的全部哈希，包括 parquet、分词器文件、eval_sets.jsonl 等文件字节哈希。
	2.	ST12 比对范围 (2) 的「冻结提交」= PROTOCOL_FROZEN 标为当前有效的版本，即 v1.1 的 87a244db…。
	3.	对整个 eval_sets.jsonl 求文件哈希不算「统计 TEST」，与协议第 3 节的定义一致。
	4.	三个 JSON 的 frozen 字段保留 v1 批准时间，不修改；v1.1 的批准记录以 PROTOCOL_FROZEN 与第 14 节为准。
	5.	第 8、9 轮仍开放的 MINOR（含 W3、W8、Y5、Y8）：维持登记，不修改协议。实现时若某一条影响可执行性，按第 12 节 HALTED。
	6.	推送输出只在回复中的情况：本次接受；从本任务起，推送输出一律写入 reports/ 并随下一次提交入库。

4. 交付物

只在 metrix/e1-pilot/ 下新增：

metrix/e1-pilot/
├── src/metrix_e1/          # 实现代码（Python 包）
├── tests/                  # 单元测试与冒烟测试
├── run_pilot.py            # 唯一入口：正式运行与冒烟模式
├── requirements.lock       # 依赖锁定（含版本号与哈希）
├── RUNBOOK_A100.md         # A100 上的操作手册
├── tasks/IMPLEMENTATION_TASK_ORDER_V1.md   # 本文件原文
└── reports/IMPL_*.md       # 各阶段报告

不提交：模型权重、checkpoint、冒烟输出中的大文件、任何 TEST 内容。

5. 模块要求

每个模块对应协议的章节，模块顶部注释写明对应的协议节号。

模块	协议	要求
frozen.py	第 0 节、PROTOCOL_FROZEN	读取当前有效版本；用 git cat-file 从冻结提交读取协议与三个 JSON 的字节并核对哈希；提供全部冻结常量。任何不一致抛出 ST12。
data.py	第 2 节	生成 fact、TRAIN 陈述句、train_S.jsonl、train_Y、DEV QA、candidates.json、锚文本、general DEV 窗口。生成后与冻结哈希比对：fact 406c8801…、train_S 686fdd2f…、candidates e5d15c99…、锚文本 8828bc4f…。已有的参考脚本（reports/round*/）可以迁移进来，但必须证明输出逐字节相同。
test_data.py	第 8 节第 8 步	TEST 生成器。运行前必须同时满足：PROTOCOL_FROZEN 有效且 ST12 通过；Gate 0 结论为 PASS 的记录存在；选定配置的冻结记录已提交。任一条件不满足：打印 RESULT: FAIL 并以非 0 退出，不产生任何 TEST 内容。
leakage.py	第 3 节	L1–L6；涉及 TEST 的部分只能由第 8 步调用。
train.py	第 4、7 节	F、L、A、S、Y 的训练，严格按训练契约表。L 用 LoRA（目标模块、alpha、dropout、B 初始为 0 按协议）；A 的 KL 按协议（token 加权、冻结的 base 副本、无梯度）。
evaluate.py	第 5 节	s_QA 候选打分（The answer is 前缀、enable_thinking=False、答案前带空格、并列判为错）；TRAIN 闭卷；EM（贪心、停止 token、<think> 处理）；general dNLL（n_w 定义）。
stats.py	第 6 节	按 fact 聚合（mean）；按 stratum 分层的配对 bootstrap，10,000 次，种子按 rng_rule。
gate.py	第 8、9 节	G0.1–G0.10 判定，只输出第 9 节的固定词汇。
stops.py	第 11 节	ST1–ST13 的检查与停止动作。
compute.py	第 7 节	设备全名检查（ST8、ST9）、累计 GPU wall-clock（ST7）、预检（ST11）、峰值显存、费用估算。
record.py	第 10 节	按实验记录模板写出完整记录，包括依赖版本、全部哈希、Git 状态。
run_pilot.py	第 8 节	按第 1–8 步顺序执行；每步开始前执行 ST12；每步结束时提交记录。--smoke 模式见第 7 节。

确定性：torch.use_deterministic_algorithms(True)、设置 CUBLAS_WORKSPACE_CONFIG、关闭 TF32，并把这些设置写入实验记录。所有随机数来自协议的 rng_rule。

检查脚本：所有判定类代码不通过时打印 RESULT: FAIL 并以非 0 退出；出现异常时同样处理。

依赖：Python、PyTorch、transformers、peft（若使用）等全部锁定版本，写入 requirements.lock。transformers 版本必须能正确加载 Qwen3 与该 revision 的 chat template。

6. 单元测试（必须全部通过）

至少包括：

	1.	数据：四个冻结哈希由 data.py 重新生成后完全一致。
	2.	打分：对全部 learned 答案，打分区间的 token id 与 TRAIN 陈述句中的答案片段一致（不一致数 0）；第 3 轮那条 28 个 token 的期望序列逐个一致；把 enable_thinking 改为 True 时测试失败。
	3.	并列判为错；聚合为 mean；bootstrap 的统计单位是 fact。
	4.	LoRA：训练第 0 步时模型输出与 base 完全相同（B = 0）。
	5.	arm A：第 0 步 KL = 0；base 副本没有任何参数 requires_grad；训练后 base 副本的参数哈希不变。
	6.	S、Y 使用 F 的选定配置，不独立搜索。
	7.	gate.py：用人造输入覆盖每个 G0 条件的通过与不通过，状态词汇只来自第 9 节。
	8.	stops.py：ST1–ST13 各至少一个触发用例。
	9.	TEST 生成器：在当前状态（无 Gate 0 PASS 记录）下拒绝运行，RESULT: FAIL、非 0 退出、没有产生任何文件。
	10.	ST12：篡改任一冻结文件或数据文件的一个字节，运行立即停止。

7. CPU 冒烟测试

模型：Qwen3ForCausalLM，用与 Qwen3-1.7B 相同的配置类和分词器，但层数、hidden size 缩小（例如 2 层、hidden 64），随机初始化。不得下载或加载真实权重；在报告中记录小模型的完整配置。

流程：run_pilot.py --smoke 跑通第 8 节第 1–7 步：数据生成与哈希核对 → 泄漏检查 → N 评测 → F 的 6 个配置 → 选定 → L、A 搜索 → 其余种子与 S、Y → Gate 0 判定。为控制时间，每次训练只跑少量步数（例如 3 步）；这一缩减只在冒烟模式下生效，代码必须使正式模式无法使用缩减后的步数。

冒烟模式的约束：

	•	输出写入独立目录，每个文件标注 SMOKE — NOT A RESULT。
	•	跳过 GPU 设备检查时必须显式记录「smoke: device check skipped」。
	•	Gate 0 判定会照常计算，但输出状态固定为 NOT_TESTED，并附「冒烟测试，不构成结论」。
	•	第 8 步只测试 TEST 生成器拒绝运行（第 6 节第 9 项），不生成任何 TEST。

冒烟报告须包含：每一步的耗时、峰值内存、产生的文件清单、每个 G0 的计算值（标注为冒烟值），以及 30 次训练全部完成的证据。

8. A100 操作手册（RUNBOOK_A100.md）

写清楚：

	1.	环境要求：GPU 型号与显存检查、CUDA 与驱动版本、Python 与依赖安装（只用 requirements.lock）。
	2.	需要下载的内容及其哈希：Qwen3-1.7B @ 70d244cc、parcae 分词器、锚文本 parquet。
	3.	执行命令：从克隆仓库到运行完毕的完整命令序列。
	4.	预检（ST11）与停止条件出现时的操作。
	5.	结果与记录如何提交回仓库（不提交权重与 checkpoint）。
	6.	预计时长与费用：按 A100 80GB 每小时 1.8 美元，给出依据和估算区间。该估算是规划估计，正式数值以预检为准。

手册不指定租用平台，由 Owner 选择。

9. 审查

	•	每个工作提交前调用 code-reviewer，按 metrix/CLAUDE.md 第 5 节；重点：与协议逐条一致、训练契约、打分区间、冻结参数、TEST 隔离、正式模式与冒烟模式的隔离。
	•	数据生成代码完成后，调用 data-auditor 用自写脚本独立复算四个冻结哈希。
	•	BLOCKER：修复后重审。新提出的 MAJOR/MINOR：影响协议一致性、数据、指标或隔离的必须修；其余登记于 DEFERRED_MINORS.md。

10. 分阶段执行（每阶段一个会话，阶段结束时提交并推送）

阶段	内容	阶段报告
A	本文件原文入库；frozen.py、data.py、leakage.py（不含 TEST 部分的执行）；单元测试 1、10；requirements.lock	reports/IMPL_A_REPORT.md
B	train.py、evaluate.py、stats.py、gate.py、stops.py、compute.py、record.py、test_data.py；单元测试 2–9	reports/IMPL_B_REPORT.md
C	run_pilot.py；CPU 冒烟测试；RUNBOOK_A100.md；最终报告	reports/IMPL_C_REPORT.md

每个阶段开始时：比对 ~/.claude/ 副本（同第 7 轮），读取本文件与上一阶段报告。

11. 验收（阶段 C 结束时全部满足）

	1.	单元测试全部通过，原始输出入库。
	2.	四个冻结哈希由正式代码重新生成，完全一致；data-auditor 独立复算一致。
	3.	run_pilot.py --smoke 从第 1 步跑到第 7 步无中断，30 次训练全部完成，冒烟报告完整。
	4.	TEST 生成器在当前状态下拒绝运行；全程没有任何 TEST 内容产生。
	5.	正式模式下无法使用冒烟的缩减参数（有测试证明）。
	6.	每个工作提交的 code-reviewer 为 PASS 且无 BLOCKER。
	7.	outside_metrix_check.py 通过。
	8.	RUNBOOK_A100.md 完整，含时长与费用估算。

12. 停止条件（HALTED）

立即停止并写明原因，不得自行修补：

	•	协议的某处无法按原文实现，或两处互相矛盾；
	•	实现需要读取 TEST、加载真实权重或使用 GPU；
	•	冻结哈希无法复现；
	•	需要 Owner 决定的事项（协议新版本、依赖无法锁定、预算）。

13. 最终状态

阶段 C 验收通过后：IMPLEMENTATION_READY。之后由 Owner 决定是否租用 A100 并执行正式运行；正式运行另发运行指令。
