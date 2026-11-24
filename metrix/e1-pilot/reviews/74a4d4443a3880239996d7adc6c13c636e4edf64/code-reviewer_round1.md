# code-reviewer final report, Implementation stage B, round 1: staged work commit (parent 0bc0eecf1f684773248c198afb94e7026dcfb16d); invoked 2026-11-23 07:39 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-adefcadfd09dabdcb.jsonl)
---
code-reviewer 审查报告：Metrix E1-PILOT Implementation 阶段 B（暂存提交，父提交 0bc0eecf）

调用前我先读了仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，它与已加载的定义一致（tools: Read, Grep, Glob）。
本次审查只读代码，没有执行任何命令（我没有 Bash 工具）。下面凡是来自读代码的判断都标『未验证』；引用本提交暂存原始输出（reports/impl_b/ 下的文件与行号）的判断标『已验证』。

先说结论：没有发现 BLOCKER。主要问题有四类：
- 预检模式（preflight）的隔离不完整。
- G0.8 没有强制要求 3 个 checkpoint。
- 待决解释 pending() 在任何地方都没有被强制。
- TEST 生成器的条件 2、3 没有正向对照，所要求的记录格式也没有任何代码产生。

总体上，第 4、7 节训练契约、第 5 节打分、第 6 节统计与协议逐条对照一致。依据：读 train.py 第 172–434 行、evaluate.py 第 31–306 行、stats.py 第 20–164 行；相关单元测试全部通过（reports/impl_b/t4_pytest.txt 第 11–175、188 行）。

【BLOCKER】
无

【MAJOR】
MAJOR | metrix/e1-pilot/src/metrix_e1/mode.py:30-32；gate.py:158；train.py:17-18 | 新增的 PREFLIGHT 模式可以缩减步数，但不属于冒烟模式：(1) gate.judge 只在冒烟模式下把状态固定为 NOT_TESTED，预检模式会走正式路径，输出 PASS 或 PIPELINE_NOT_QUALIFIED；(2) RunMode(PREFLIGHT, n) 接受任意 n，不限于协议的 20 步；(3) mode.py 与 train.py 文档仍写"只有 smoke 能缩短步数" | `elif self.name in (SMOKE, PREFLIGHT): if type(self.smoke_steps) is not int or self.smoke_steps < 1`；`if mode.smoke:`（gate.py:158）『未验证』 | gate.judge 对所有非 formal 模式拒绝运行，或固定为 NOT_TESTED；RunMode(PREFLIGHT, …) 的步数限定为 contract.preflight_steps；补对应测试；更正文档
MAJOR | metrix/e1-pilot/src/metrix_e1/gate.py:105,143 | G0.8 要求"对 F 选定配置的 3 个 checkpoint 各评测两次"，但代码只要求非空：只提供 1 个种子也会判为满足 | `sat["G0.8"] = bool(v["G0.8"]["checkpoints"]) and all(...)`；compute_values 直接用 inp["repro"] 的键，不核对种子；test_gate.py:48-49 只测了 {} 与一个不满足的情况『未验证』 | 要求 set(inp["repro"]) == set(contract.training.training_seeds)，否则报错或判为不满足；补测试
MAJOR | metrix/e1-pilot/src/metrix_e1/train.py:37-43；evaluate.py:107-110 | NonFinite（ST6）的状态写死为 IMPLEMENTATION_FAIL。按第 7 节与 ST6，搜索阶段非选定配置出现非有限值时应"剔除该配置"，不应给出 IMPLEMENTATION_FAIL。现在完全依赖阶段 C 调用方改判，异常本身带着错误的状态。不确定之处：阶段 C 是否一定捕获并改判 | `super().__init__("ST6", "IMPLEMENTATION_FAIL", message)`『未验证』 | NonFinite 不带最终状态（status None 加 stop ST6），由 stops.st6 决定；或者由 train_run 接收 selected_or_control 参数
MAJOR | metrix/e1-pilot/src/metrix_e1/interpretations.py:108-109；test_data.py:153-183 | pending() 在包内没有任何调用方。B19（第 8 步 L3/L5 对 TEST 的含义）写明"To be ruled before step 8 runs"，但 test_data.main 在三个前提条件满足后，会在 B19 未裁决时直接生成 TEST 并运行 run_test_part。不确定之处：阶段 C 的 run_pilot 是否会在形成 Gate 0 PASS 记录之前强制 pending() 为空 | grep `pending(` 只命中定义处；test_data.check_preconditions 不检查 INT.pending()『未验证』 | 在 test_data.check_preconditions 中增加条件：B19（或全部条目）已裁决，否则 RESULT: FAIL；并补测试
MAJOR | metrix/e1-pilot/tests/test_test_data.py:112-141；src/metrix_e1/test_data.py:61-96；record.py:93-104 | 条件 2、3 只有反向用例，没有正向对照：一个"永远拒绝"的实现也能让全部测试通过。另外 test_data 要求的记录字段（frozen_commit、gate0.gate0_status、selected、data_content_hashes、checkpoints），record.new_record 都不产生（它只有 label/mode/template/experiment_id/environment），Gate 0 记录与选择冻结记录之间也不做互相绑定 | `if rec.get("frozen_commit") != fz.record.commit` 与 new_record 返回的 `{"label", "mode", "template", "experiment_id", "environment"}`『未验证』 | 增加条件 2、3 各自的正向用例（只调用 check_gate0_record / check_selection_record，不生成 TEST）；在 record.py 中定义这两类记录的构造函数，与 test_data 共用同一 schema
MAJOR | metrix/e1-pilot/src/metrix_e1/compute.py:188-202 | B17 预估中，评测时间 = 评测 token × (训练每 token 时间 / 3)。但训练在 bf16 autocast 下进行，评测是 FP32 且关闭 TF32（set_determinism），EM 又是逐 token 解码、受延迟限制，两者吞吐不可比，预估可能显著偏离。ST11 只依据这个值。不确定之处：偏离的方向与幅度 | `eval_s = eval_forward_tokens * per_token_train / 3.0`『未验证』 | 预检中另外实测一次 FP32 评测（例如 N 在一小批 DEV 上的打分与生成）的耗时，再外推；交 Review Gate 一并裁决 B17
MAJOR | metrix/e1-pilot/src/metrix_e1/gate.py（全文）；evaluate.py:294-306 | 第 8 节 T1–T3 判定（最终 PASS 所需）在任何模块都没有实现；evaluate_model 写死只评 dev_qa.jsonl 与 general_dev.jsonl，没有 TEST 评测入口。不确定之处：这部分可能归阶段 C 的 run_pilot | grep T1/T2/T3 在 src 中无命中（ST 编号除外）『未验证』 | 阶段 C 前明确归属；gate.py 增加 T1–T3 判定与对应测试
MAJOR | metrix/e1-pilot/src/metrix_e1/compute.py:119-134 | GpuClock 只在 close() 时落盘，open 时刻只存在内存中。进程崩溃或被中断后，这一段时间丢失，累计 GPU 时间会少算，ST7 可能失效。不确定之处：阶段 C 的使用方式 | `self.started = self.now()`（不写文件）『未验证』 | open() 时把开始时刻写入文件；重启时把未闭合的段计入（或按 BLOCKED 报告）
MAJOR | metrix/e1-pilot/src/metrix_e1/gate.py:19-21,149-157,165-166 | B14 与第 9 节存在张力：(1) G0.5 三个部分不满足都记 OPTIMIZATION_OR_CAPACITY_UNRESOLVED，而第 9 节只写"G0.5 或 T1 的正确率不满足"；(2) G0.3、G0.9、G0.10 不满足时原因为 null，与"同时给出下面的一个原因"不合；(3) 可能输出多个原因；(4) 第 8 节把 [0.40,0.70) 记为 UNRESOLVED 且不以 G0.4 为前提，而代码在 G0.4 不满足时改为 OPTIMIZATION_FAIL | `"G0.3": None, "G0.9": None, "G0.10": None`；`reasons = sorted({...})`『未验证』 | 交 Review Gate 裁决后按裁决实现；裁决前在记录中显式标注
MAJOR | metrix/e1-pilot/src/metrix_e1/train.py:225-229,255-256 | B5：LoRA A 的随机数来自以 rng_rule 输出播种的 torch.Generator，不是 rng_rule 给出的 random.Random 本身。这与第 0 节"所有随机数都来自 random.Random(int.from_bytes(sha256(...)))"字面不一致，purpose "lora_A:<path>" 也不是协议写明的。不确定之处：Review Gate 是否接受"派生种子" | `g.manual_seed(FZ.rng_rule(seed, "lora_A:%s" % path).getrandbits(64))`；`torch.rand(..., generator=generator)`『未验证』 | 交 Review Gate；若要求字面一致，改用 rng_rule 生成器的 r.uniform 逐元素生成（约千万量级，CPU 上可行）

【MINOR】
MINOR | metrix/e1-pilot/tests/test_arm_a.py:82-96；src/metrix_e1/train.py:404-409 | Owner 要求 6 的方向与加权测试只覆盖 anchor_kl 本身。train_run 调用处的参数顺序（lt, lb）如果写反，第 1 步 KL=0、第 2 步 KL>0、loss=ce+λkl 等断言仍然全部通过；KL 项的梯度是否回传也没有测试。读代码看现在的实现是正确的 | `kl = anchor_kl(lt, lb, a_mask)`；测试只断言数值『未验证』 | 增加一个经由 train_run 的测试：用 KL 单独反传检查梯度非零，并与手算的 KL(p_base‖p_θ) 比较
MINOR | metrix/e1-pilot/src/metrix_e1/stops.py:144-148 | ST13 只把调用方给出的布尔值映射成 Stop，没有任何检测"冻结前读取 TEST"的逻辑；测试 test_stops.py:161-164 实际上是同义反复 | `if test_read_before_freeze: raise Stop("ST13", ...)`『未验证』 | 至少检测：选择冻结记录提交之前，数据目录或输出目录中出现 TEST_FILES 即触发
MINOR | metrix/e1-pilot/src/metrix_e1/leakage.py:182-200 | TestAuthorization 是普通类，任何代码都能直接构造，"只能由 check_preconditions 创建"只是约定。目前 grep 不到其它构造点 | `class TestAuthorization: def __init__(self, frozen_commit, ...)`『未验证』 | 用模块私有的令牌对象或签名校验；至少在 run_test_part 内复核 gate0/selection 记录的哈希
MINOR | metrix/e1-pilot/src/metrix_e1/stats.py:155-162；gate.py:114-119 | 若全部 d_f 为 0（例如 F、L、A 在全部 learned fact 上都饱和），σ_d=0 使 planning n=0，halfwidth_check 中出现 sum([])/len([]) 的 ZeroDivisionError，Gate 0 无法给出判定（本应由 G0.9 判为不满足） | `per = math.ceil(n / len(by))`；`reps.append(sum(drawn) / len(drawn))`『未验证』 | n=0 时跳过半宽检查并记录原因
MINOR | train.py:124-126,262-263,439-444；record.py:129-142；compute.py:149-158,169-171,176-185；contract.py:140,194-195,243,247-248；frozen.py:139 | 死代码与未使用项：step_numbers 只被 reports/impl_b/dump_for_audit.py 使用（train_run 用 batch_schedule 自己计数，与 B1 的 "where" 不符）；lora_parameters、gate0_record_path、selection_freeze_path 无调用方；render_text 只有测试使用；run_flops、cost_usd、preflight_summary 无调用方且 preflight_summary 无测试；contract 的 purpose_format、z_alpha、z_power、think_open_id、think_close_id、anchor_docs_per_step 只解析不使用；FrozenRecord.source_sha256 仍未使用（与阶段 A 报告 AA3 的说法不符） | grep 结果『未验证』 | 删除，或在阶段 C 接线并补测试；更正 B1 的 "where"
MINOR | metrix/e1-pilot/src/metrix_e1/compute.py:144-146,196-199 | 第 10 节的 FLOP 系数 6、2 以及派生出的 8、3 写死在代码里，而模块文档声称"Numbers from metrix_e1.contract" | `{"train": 6, "forward": 2}`、`8.0 * anchor_tokens_per_step / (6.0 * ...)`、`/ 3.0`『未验证』 | 由 contract 从第 10 节句子解析，或统一用 flops() 推导
MINOR | metrix/e1-pilot/src/metrix_e1/errors.py:18 | (e) 的放宽对所有带 stop 代码的 ProtocolStop 都允许 status None，不限于 ST6 | `if status not in STATUSES and not (status is None and stop is not None)`『未验证』 | 限定为 `stop == "ST6"`
MINOR | metrix/e1-pilot/src/metrix_e1/errors.py:8-9；tests/test_gate.py:77 | 第 9 节状态词表写死在代码中，没有与冻结协议第 9 节核对；测试 7 用同一个元组自证，属于循环论证 | `STATUSES = ("PASS", ...)`『未验证』 | 在 contract 中 fullmatch 协议第 9 节的词表行，并与 STATUSES 比较
MINOR | metrix/e1-pilot/src/metrix_e1/stats.py:3-4 | 文档声称实现了 ImmediateGain，实际没有对应函数；report_comparisons 也不含 L−N、A−N | 文档 "ImmediateGain" 与 grep 结果『未验证』 | 实现或删除该说法
MINOR | metrix/e1-pilot/src/metrix_e1/record.py:72,84-85 | 记录里的 PROTOCOL_FROZEN 哈希是写记录时重新读文件算的，不是 load 时实际解析的字节（fz.record.source_sha256）；两者之间文件若被改，记录无法反映 | `pf = (fz.repo_root / FZ.PROTOCOL_FROZEN_REL).read_bytes()`『未验证』 | 同时写入 fz.record.source_sha256，并核对两者相等
MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:51-54 | 正式代码只检查打分区间长度等于 K_st，没有逐 id 比较 ids[start:] == encode(" " + c)；逐 id 一致只由测试在 DEV 上证明（t4_pytest.txt:76-78『已验证』） | `if len(ids) - len(ctx) != k_st(tok, candidate)` | 在 _sliced 中直接比较 id 序列
MINOR | leakage.py:152-153 与 203-204；gate.py:108-119；evaluate.py:169-206 | 重复逻辑：训练语料字典构造两处相同；compute_values 对 L、A 重复计算 avg 与 d_avg；score_cb 与 score_s_mapping 的单元构造重复 | 见所列行『未验证』 | 提取公共函数
MINOR | metrix/e1-pilot/src/metrix_e1/mode.py:24 | 字段 smoke_steps 同时承载预检步数，命名易误导 | `smoke_steps: int = None  # ... (and the protocol's preflight steps)`『未验证』 | 改名为 shortened_steps 或拆成两个字段
MINOR | metrix/e1-pilot/src/metrix_e1/train.py:450-457 | (d) 下载的 config.json 的哈希没有任何冻结值可比，只记录在 t2_fetch_config.txt 第 5 行（1ddb5b89…）；冒烟小模型若基于它构造，其来源不受 ST12 覆盖 | `return path, FZ.file_sha256(path)` | 在报告或 manifest 外的固定清单中登记该哈希，加载时比对
MINOR | metrix/e1-pilot/src/metrix_e1/train.py:419,425 | 每步耗时在 CUDA 上没有 synchronize，异步执行会使 per-step 秒数失真（尤其最后一步），而预检只依据这些数据 | `entry["seconds"] = time.perf_counter() - t0`『未验证』 | 在 CUDA 设备上计时前调用 torch.cuda.synchronize()
MINOR | metrix/e1-pilot/src/metrix_e1/evaluate.py:146,169,282,294 | 训练在非冒烟模式下拒绝 CPU，评测函数却没有对应保护；协议第 7 节规定 CPU 不执行任何模型评测 | evaluate_model 没有 mode 参数『未验证』 | 评测入口接收 RunMode，非冒烟模式下拒绝非 cuda 设备
MINOR | metrix/e1-pilot/src/metrix_e1/train.py:442；gate.py:95-96；evaluate.py:217 | 以下实现选择没有列入 B 清单：attn_implementation="eager"（影响数值与 G0.8）；G0.3 的"每个 stratum"只检查 learned 的两个 stratum；EM 的"第一行"只按 "\n" 切分（不处理 "\r"） | `attn_implementation="eager"`；`k.startswith("acc_dev_learned:")`；`s.split("\n", 1)[0]`『未验证』 | 补入 interpretations 并交 Review Gate 备案
MINOR | metrix/e1-pilot/tests/test_gate.py:22-23 | G0.3 的通过用例只用区间中点，闭区间端点的通过情况没有测试（其它条件在端点上测了） | `mid(g.g3_learned)`『未验证』 | 增加 G0.3 两端恰好等于端点时判为满足的用例
MINOR | metrix/e1-pilot/src/metrix_e1/compute.py:97-100；stops.py:112 | DeviceLedger.check 在尚未记录设备名时直接触发 ST9（void_pilot）；调用顺序稍有失误就会整批作废 | `if recorded_name is None or current_name != recorded_name`『未验证』 | 未记录时抛出实现错误（非 ST9），或由 check 负责完成首次记录

【对 (a)–(f) 的判断】
(a) interpretations.py B1–B20 逐条：
- B1 协议未覆盖（步与文档编号的起点没有写明），须交 Review Gate；与原文不冲突。『未验证』
- B2 协议未覆盖（"前 15 步从 0 线性上升"的离散化方式），须交 Review Gate；与原文不冲突。
- B3 协议未覆盖（epoch 编号起点、全排列的调用方式），须交 Review Gate。
- B4 协议未覆盖（batch 内按 token 加权还是按序列平均），须交 Review Gate；末尾 endoftext 计入损失与"补齐位不计损失"一致。
- B5 协议未覆盖，且与第 0 节"所有随机数都来自 random.Random(rng_rule…)"字面存在冲突风险，须交 Review Gate（见 MAJOR）。
- B6 与协议原文一致（第 7 节训练精度为 bf16 autocast；KL 用 float32 计算不改变定义）；建议 Review Gate 备案。
- B7 与协议原文一致（"只作用于二维权重矩阵"，词嵌入是二维矩阵）。
- B8 协议未覆盖（结尾标点去掉一个还是全部），须交 Review Gate；未闭合的 <think> 不删，与"到其后第一个 </think>"的原文一致。
- B9 与协议原文一致（第 2.5 节：候选表对全部模板、全部 split、全部 arm 相同）。
- B10 协议未覆盖（重抽的调用方式），须交 Review Gate。
- B11 协议未覆盖（百分位插值方法），须交 Review Gate。
- B12 协议未覆盖（purpose 的字面字符串、Spill 的 purpose），须交 Review Gate。
- B13 协议未覆盖（ddof、σ 的 bootstrap purpose、取最大值的范围、半宽检查口径、G0.10 的满足条件），须交 Review Gate。
- B14 协议未覆盖，且与第 9 节存在张力（见 MAJOR），须交 Review Gate。
- B15 协议未覆盖（候选分数是否含 s_ST、是否含 EM），须交 Review Gate。
- B16 部分与协议一致：ST4、ST5 记 PIPELINE_NOT_QUALIFIED 加原因 IMPLEMENTATION_FAIL，与第 9 节 G0.6、G0.7 的对应一致；ST6 剔除与第 7 节一致。ST3、ST7、ST11 的状态词协议没有写，须交 Review Gate。
- B17 协议未覆盖，须交 Review Gate（另见 MAJOR）。
- B18 与协议原文一致（第 10 节 6PT/2PT、P 为参与计算的参数量、锚文本算力单列）。
- B19 协议未覆盖，须交 Review Gate：L4 的 TEST 部分在 L4 一行有明确规定；L3、L5 对 TEST 的含义没有定义。
- B20 协议未覆盖（候选集合），须交 Review Gate；只报告，不进门槛。

(b) B19 属于协议未覆盖。阶段 A 报告预告"届时如协议未覆盖即停下报告"，本阶段改为实现并列入待决，偏离了这一预告，须由 Review Gate 明确接受。不停止本身可以接受，理由是本阶段 TEST 部分不会运行，且字面执行可行（L3a/L3b/L5 按 Gate 0 重跑）。前提是代码保证裁决前不能执行第 8 步，而目前没有这样的保证（pending() 未被使用，见 MAJOR）。『未验证』

(c) 非冒烟模式拒绝在 CPU 上训练，与协议第 0、7 节及 metrix/CLAUDE.md 第 3 节一致（test_train.py:141-146 通过，t4_pytest.txt:167『已验证』）。PREFLIGHT 模式对应协议第 8 节第 2 步，20 步从冻结协议解析（t4_pytest.txt:166『已验证』），这部分与协议一致。但隔离不完整：judge 不固定为 NOT_TESTED，步数也可以任意给定（见 MAJOR）；评测入口没有 CPU 保护（见 MINOR）。

(d) 只下载 config.json，不是权重文件，与红线 2 及 metrix/CLAUDE.md 第 3 节一致；在 meta 设备上构造模型不分配、也不加载权重。下载内容见 t2_fetch_config.txt 第 3-23 行，目录中只有 config.json（726 字节）『已验证』。参数数核对见 t4_pytest.txt:160-165『已验证』。小问题：config.json 的哈希没有冻结值可比（见 MINOR）。

(e) 与协议一致：第 7 节"出现非有限损失或分数的配置剔除"，ST6 只对选定配置或对照给出 IMPLEMENTATION_FAIL，剔除的情况协议不给状态，用 None 合理。但放宽的范围过大（见 MINOR）；NonFinite 的状态写死为 IMPLEMENTATION_FAIL，与此不一致（见 MAJOR）。

(f) 与 Review Gate 对阶段 A 的裁决 3 一致：只报告，不作判定。t3_generate_leakage.txt 第 8-10 行：加 endoftext 时为 1.1964（F 1889，Y 2260），不加时为 1.1419（F 1769，Y 2020），两者都在 [0.8, 1.25] 内『已验证』。

【与问题 1–9 对照、未发现问题的部分】（均为读代码所得『未验证』，另注明测试证据）
- 训练（train.py:354-434）：
  - 各 arm 的语料与 batch（F/L/A/S 为 8，Y 为 16）正确；300 步、每遍一次全排列、rng_rule("order:<e>") 正确。
  - AdamW 的 betas、eps 取自冻结文件；weight decay 只作用于二维参数，L、A 强制为 0。
  - 梯度裁剪全局范数 1.0；bf16 autocast，主权重 FP32。
  - 补齐位不计损失，训练输入后接 151643。
  - LoRA 加在 28 层 × 7 个模块；alpha = 2 × rank；dropout 0；B = 0；base 冻结且训练前后哈希核对。
  - arm A：KL(p_base‖p_θ) 按 token 加权，t 从 2 起；base 副本深拷贝、全部 requires_grad=False、eval、no_grad；每步 4 篇锚文档。
  - S、Y 继承 F 选定配置，不独立搜索。
  - 测试证据：t4_pytest.txt:11-15、64-68、151-175。
- 打分（evaluate.py）：
  - chat template 中 enable_thinking 为常量 False，不是参数；"The answer is" 前缀，对 " "+c 打分，并列判为错。
  - prefix(f) 不含答案前的空格，前面不加特殊 token。
  - EM：贪心，最多 16 个新 token，两个停止 token，skip_special_tokens，删除 <think> 片段后按协议顺序归一化。
  - general NLL 的 t 从 2 起，n_w 为存储的 id 数；评测 FP32、无 autocast。
  - 测试证据：t4_pytest.txt:31-37、73-78、111-112。28 个 token 的固定序列与 enable_thinking=True 时测试失败的用例都已通过。
- 统计：
  - 先按 fact 取 mean，再在两个 stratum 内分层、配对 bootstrap 10,000 次，purpose 使用 rng_rule；seed-average 是对每条 fact 取种子平均后再 bootstrap。
  - 测试证据：t4_pytest.txt:113-119。
- TEST 隔离：
  - 前提条件顺序为 1→2→3；不满足时在生成任何文件、解析任何 test 行之前打印 RESULT: FAIL 并以非 0 退出。
  - 测试证据：t4_pytest.txt:135-150。
  - 没有发现其它生成、读取或统计 TEST 的代码路径；run_test_part 只有 test_data.main 调用。
- 冻结参数：
  - 门槛、超参、种子都从 contract 的整句匹配中读取（t4_pytest.txt:16-20）。例外是 FLOP 系数与状态词表（见 MINOR）。
- 改动范围：
  - 暂存改动全部在 metrix/e1-pilot/ 下（review_input.diff 第 1-37 行），__pycache__ 未暂存。

结论：PASS
