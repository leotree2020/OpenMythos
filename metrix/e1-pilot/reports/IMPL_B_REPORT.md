# E1-PILOT Implementation 阶段 B 报告

- 指令:`tasks/IMPLEMENTATION_TASK_ORDER_V1.md` 第 10 节表中 B 行;Owner 下达阶段 B 的消息原文 `tasks/IMPL_B_OWNER_MESSAGE.md`(第 0 步远端核对;Review Gate 对阶段 A 的裁决 1–4;阶段 B 额外要求 5–7;直接在 `metrix-e1-pilot-protocol-v1` 上工作,只做快进推送,不 force push,不推送标签,不经 PR;阶段 B 结束后停下)。
- 执行会话:session_01J5mxaWPrK8siadYKyqZ5pX。会话从会话分支 `claude/phase-b-implementation-lvi1j5`(`155430a`)启动;本地分支 `metrix-e1-pilot-protocol-v1` 设为 `origin/metrix-e1-pilot-protocol-v1`(`620f8611`,阶段 A 报告提交)后在其上工作(`impl_b/t0_remote_check.txt` 的 `git reflog`)。会话分支没有使用,没有改写任何已有提交。
- 运行环境:Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,没有 nvidia 设备,`torch.cuda.is_available()` 为 False(`impl_b/t1_env_baseline.txt`)。Python 3.13.18;容器是新的,依赖按 `requirements.lock` 以 `--require-hashes --no-deps` 重新安装到会话临时目录的 venv,`pip check` 通过;torch 元数据版本 2.11.0、`__version__` 2.11.0+cu130,transformers 5.22.2。
- 中断:工作进程三次重启(`uptime -s` 2026-11-23 07:31:22、13:34:42 与 2026-11-24 03:30:52 UTC),工作区、暂存区与会话临时目录都保留。第一次发生在第 1 轮审查调用之前;第二次发生在修复提交的审查输入与调用前核对写好之后、调用之前,重启后先核对暂存区与审查输入逐字节相同,并重做了 frontmatter / tools 行核对(`reviews/fdbb9def…/preflight_tools_check.txt` 末段)再调用。第三次:报告提交的两份审查都因 API 额度限制(HTTP 429)中途停止,随后工作进程重启;重启后核对 HEAD、暂存区与两份审查输入逐字节相同、没有未暂存或未跟踪的文件(data-auditor 中断前没有写入)、frontmatter 与 tools 行相同,再向两个审查 subagent 发送续审消息(首句为固定句)让其从中断处继续(`reviews/74a4d444…/interruption_report-commit.txt`、`resume_message_*_report-commit.txt`;续审消息原样送达,见 `extract_log_report-commit.txt`)。
- 停止钩子在审查结论出来之前多次要求提交推送;按 `metrix/CLAUDE.md` 第 5 节,每次提交都在两份审查结论出来之后(这一点没有原始输出)。
- 没有加载任何模型权重、没有下载权重文件(下载的是 4 个分词器文件、parcae `tokenizer.json`、锚文本 parquet 与固定 revision 的 `config.json`,`impl_b/t1`、`t2`)、没有使用 GPU、没有对真实模型训练或评测。训练与评测代码只在随机初始化的同构小模型(Qwen3ForCausalLM,2–3 层,hidden 64,词表与协议分词器相同)上运行,或在 meta 设备上实例化协议结构以核对参数数(不分配内存、无权重)。没有生成 TEST,也没有实例化任何 TEST 问句;TEST 生成器只测试了拒绝运行。关于 `eval_sets.jsonl` 的 test 行,见“待 Review Gate 决定”第 3 项:阶段 A 起的参考比对测试曾让 `reports/round5/l6_check.py` 以文本模式读取整个文件(test 行被 UTF-8 解码、不被解析),第二个修复提交起不再如此。
- 原始输出在 `reports/impl_b/`(命令行由 `round5/logrun.sh` 记录);审查的调用文字、输入与原文在 `reviews/74a4d444…/`(工作提交两轮,以及按阶段 A 的先例放在这里的报告提交审查 `*_report-commit*`)、`reviews/fdbb9def…/`、`reviews/493d7f9c…/`;data-auditor 的脚本与 stdout 在 `audit/ib_*`、`ic_*`、`id_*`、`ie_*` 与 `audit/stdout/impl_b/`。

## Review Gate 对阶段 A 的裁决(作用范围:本阶段)

Owner 在下达阶段 B 时转达(原文 `tasks/IMPL_B_OWNER_MESSAGE.md`):

1. 工作区冻结文件与冻结提交比对、以及无冻结哈希的数据文件与重新生成结果比对:都同意;不一致按 ST12 处理,状态为 BLOCKED。——现状即如此(`frozen.load`、`data.verify`),本阶段未改。
2. L2 两模板都不足 4 词时 Jaccard 按 0 计:同意。——现状即如此(`leakage.l2_template_ngram`)。
3. Y/F token 比每序列加 1 个 `<|endoftext|>`:同意;报告中同时给出加与不加该 token 的两个比值,并证明都在 [0.80, 1.25] 内。——`data.y_ratio` 同时报告两者(只有加 token 的比值是协议检查):

   | 口径 | F token 数 | Y token 数 | 比值 | 在 [0.80, 1.25] 内 |
   |---|---|---|---|---|
   | 每序列加 1 个 `<|endoftext|>`(协议检查) | 1,889 | 2,260 | 1.1964 | True |
   | 不加 | 1,769 | 2,020 | 1.1419 | True |

   原始输出 `impl_b/t3_generate_leakage.txt` 第 8–10 行(`t6`、`t8` 相同);测试 `test_data_hashes.py::test_y_f_ratio_with_and_without_endoftext`(F 少 120 个序列的 token、Y 少 240 个);data-auditor 两种口径独立复算一致(`audit/stdout/impl_b/08_ib_yratio.txt`)。
4. 版本比对忽略本地标签(如 `+cu130`):同意。阶段 C 须处理 CUDA 构建兼容性(另锁一份 CUDA 12.x 构建并带哈希,若官方提供;RUNBOOK 写明租用前如何确认驱动版本及选用哪份锁定文件;一次 Pilot 只用一种构建并记入实验记录)。——阶段 C 事项,见文末。`record.environment` 已同时记录元数据版本与 `torch.__version__`。

## 结论一览

| 阶段 B 内容 | 状态 | 证据 |
|---|---|---|
| 第 0 步:`git ls-remote` 核对远端分支与两个标签 | 完成:远端 `620f8611`,两个标签不变;`impl_a/t8_report_push.txt` 已不在(阶段 A 容器回收,任何提交中都没有),以 ls-remote 输出代替 | `impl_b/t0_remote_check.txt`(提交 `0bc0eecf`),推送 `impl_b/t0b_step0_push.txt` |
| 阶段开始:比对 `~/.claude/` 副本 | 完成:用户级副本与阶段 A 记录的哈希相同(仍是旧版);两个 agent 的 frontmatter 与 tools 行相同 | `impl_b/t0c_copy_check.txt` |
| `train.py`、`evaluate.py`、`stats.py`、`gate.py`、`stops.py`、`compute.py`、`record.py`、`test_data.py` | 完成(另有 `contract.py`、`mode.py`、`interpretations.py`) | 见“交付物与实现” |
| 单元测试 2–9 与 Owner 额外要求 5–7 | 全部通过:204 passed(报告提交;审查前 `t12`,两份审查之后在被审的暂存代码上重跑 `t12c`;第二个修复提交为 198 passed) | `impl_b/t12_fix3.txt`、`t12c_reviewed_code_pytest.txt`;各轮 `t4`、`t6`、`t8`、`t10` |
| 数据未变 | 改动后三次重新生成(data_b、data_c、data_d),8 个文件与阶段 A 逐字节相同;四个冻结哈希五方一致(data-auditor 独立复算) | `impl_b/t3`、`t6`、`t8`;`audit/stdout/impl_b/07`、`21`、`36`;此后 `data.py` 未改,`t10`、`t12` 的 pytest 重新生成数据并核对四个冻结哈希(`test_four_frozen_hashes`) |
| TEST | 没有生成;生成器在当前状态拒绝(RESULT: FAIL,exit 1,无输出目录) | `impl_b/t6`、`t8`、`t10`、`t12`;data-auditor 黑盒运行 `11`、`25`、`38`、`ie_*` |
| 审查 | 工作提交:code-reviewer 两轮 PASS / PASS,data-auditor 两轮 PASS / PASS;修复提交:PASS / PASS;第二个修复提交:PASS / PASS;报告提交:PASS / PASS(code-reviewer 1 MAJOR 交 Review Gate) | `reviews/74a4d444…/`、`reviews/fdbb9def…/`、`reviews/493d7f9c…/` |
| 提交与推送 | 全部快进推送,没有推送标签;每次推送前后 ls-remote 核对分支与两个标签 | `impl_b/t0b`、`t7`、`t9`、`t11`;本报告提交 `t13`(工作区) |

## 提交

| 提交 | 内容 |
|---|---|
| `0bc0eecf`(第 0 步,证据,不需审查) | `impl_b/t0_remote_check.txt` |
| `74a4d444`(工作提交;即第 2 轮两份审查读到的暂存内容) | 8 个模块与 3 个辅助模块;`data.py`(两个 Y/F 比值;`eval_sets.jsonl` 按字节读取)、`errors.py`、`leakage.py`(TEST 部分);测试;`impl_b/t0b`–`t6`、`dump_for_audit.py`;`IMPL_B_OWNER_MESSAGE.md` |
| `fdbb9def`(修复提交;第 2 轮 code-reviewer 的 MAJOR 1–2 与 MINOR) | 见“审查”;`impl_b/t7`(工作提交推送)、`t8` |
| `493d7f9c`(第二个修复提交;修复提交审查的 MAJOR 与 MINOR) | 见“审查”;`impl_b/t9`(修复提交推送)、`t10` |
| 报告提交 | 第二个修复提交审查的代码与测试 MINOR(`DEFERRED_MINORS.md` 1.25 节 BD1–BD5、BD7:`leakage.verify_authorization` 与 TEST 生成器共用条件 2、3 的内容检查并复核解释裁决,`record.gate0_record_problem`、`freeze_record_problem`,`frozen.CONTENT_HASH_KEYS`;EM 解码循环内的非有限值测试;解释裁决测试不依赖当前状态;参考比对的 DEV 行副本先核对源文件哈希);本文件;`DEFERRED_MINORS.md` 1.22–1.25 节与第 3 节;全部审查记录;data-auditor 的脚本、stdout 与试跑输出;`impl_b/t11`(第二个修复提交推送)、`t12`(代码部分:全部 `open(` 调用、TEST 生成器拒绝、变异检查、204 passed)、`mutate_fix3.py`、`t12b`(审查记录与 auditor 试跑输出的复制核对)、`t12c`(审查之后在被审代码上重跑 pytest)、`t12d`(报告提交审查记录的复制核对);报告提交自己的审查记录(`reviews/74a4d444…/*_report-commit*`、`interruption_report-commit.txt`、`report_commit_post_review.diff`)与 data-auditor 本轮的 `audit/if_*`、`stdout/impl_b/50–56`、`trials/if_trial*` |
| 推送记录提交(证据,不经审查;Owner 第 0 项“以后每个阶段都用这种方式核对推送结果”) | `impl_b/t13_report_push.txt`:报告提交的快进推送与推送前后的 ls-remote;推送后立即提交并快进推送,不留在工作区(报告提交审查 MINOR,BE6)。这次推送自身的输出写入 `impl_b/t14_evidence_push.txt`(工作区),随阶段 C 第 0 步的证据提交入库 |

推送顺序:每个提交在两份审查结论出来之后提交并立即推送(`0bc0eecf` → `74a4d444` → `fdbb9def` → `493d7f9c` → 报告提交)。前三次审查的原文与 data-auditor 的输出在推送时还在会话临时目录与工作区(`audit/` 未跟踪),随本报告提交一起入库(修复提交与第二个修复提交的审查都指出了这一点:`DEFERRED_MINORS.md` BC3、BD6);仓库副本与临时目录原件逐一比较相同(`diff -r`,见“审查”首段)。本报告提交自己的推送输出写入 `impl_b/t13_report_push.txt`,推送后立即作为证据单独提交(见上表与“推送”);按 Owner 第 0 项,阶段 C 开始时以 `git ls-remote` 重新核对。

## 交付物与实现

所有协议数值都由 `contract.py` 从冻结提交的三个 JSON 与协议正文读出:写在句子里的数值整句 `fullmatch` 后取数,句子不同即 IMPLEMENTATION_FAIL;协议两处重复的数值互相比对。例:训练契约(SEARCH_SPACE)、G0.1–G0.10 与 T1–T3(第 8 节表)、ST3 / ST7 / ST11(第 11 节)、bootstrap 次数与百分位(第 6 节)、EM 参数(DATA_MANIFEST em_generation 与第 5 节)、确定性设置(第 0 节)、FLOP 系数(第 10 节)、第 9 节状态词表(与 `errors.STATUSES` 比对)。`test_contract.py` 改动协议句子后 `contract.load` 失败。

协议留有选择余地的地方(步号起点、epoch 编号、置换调用、LR 离散化、CE 加权、LoRA A 初始化、bootstrap 调用与百分位、purpose 字符串、G0.10 的 σ 与 n、状态原因、预检估算等)集中写在 `interpretations.py` 的 B1–B24,每条写明位置与理由,全部为 PENDING_REVIEW_GATE,并写入每份实验记录。

### `train.py`(协议第 4、7 节;第 8 节第 4–6 步)

- arm:F、L、A 用 `train_F`,S 用 `train_S`,Y 用 `train_Y`;batch F/L/A/S 8、Y 16;300 步;训练输入为陈述句 id 后接 `<|endoftext|>`(151643);右补齐,补齐位不计损失(B4:按 token 加权)。
- AdamW(betas、eps 取自冻结文件);weight decay 只作用于二维参数(B7),L、A 为 0;warmup 15 步与余弦到 10%(B2);全局范数 1.0 裁剪;bf16 autocast,主权重 FP32;顺序 `rng_rule(seed, "order:<e>")`(B3);每步 CUDA 同步后计时。
- 自实现 LoRA:`LoRALinear` 包装 28 层 × 7 个模块,alpha = 2 × rank,dropout 0,B = 0;A 的每个值取自 `rng_rule(seed, "lora_A:<模块路径>")` 的 `r.uniform`(B5);base 全部冻结,训练前后哈希核对。
- arm A:`anchor_kl` = KL(p_base ‖ p_θ),对 4 篇锚文档全部 t = 2..n_x 按 token 加权(一次除以 Σ(n_x − 1));base 副本深拷贝、全部 `requires_grad=False`、eval、`no_grad`;第 s 步用文档 (4s + i) mod 512(B1,s 从 1 起);base 副本训练前后哈希核对。
- 运行计划:F、L、A 的 6 个配置(种子 101)→ 选定 → F、L、A 的种子 202、303 → S、Y 用 F 的选定配置 3 个种子,共 30 次;选择按第 7 节(DEV Acc 最高,依次比 dNLL、学习率、编号;非有限剔除;Acc 用精确分数比较)。
- 模式:正式模式只能跑契约的步数,且只在 GPU 上训练;冒烟模式可缩减步数;预检模式只能跑协议的 20 步、且只能是第一个配置(F1,种子 101)。

### `evaluate.py`(协议第 0、5 节)

- s_QA:`chat(q) + "The answer is" + " " + c` 一次分词,打分区间逐 id 等于 `encode(" " + c)`、长度 K_st(c);`enable_thinking=False` 为模块常量,不是参数;并列判为错(预测记为 "tie")。
- TRAIN 闭卷:`prefix(f) + " " + c`,`prefix(f)` 不含答案前的空格,前面不加特殊 token;候选为 C_f(B9)。
- EM:自写批量贪心(左补齐、显式位置、KV cache),最多 16 个新 token,遇 151645 / 151643 停,`skip_special_tokens=True` 解码,删除 `<think>…</think>` 后按协议顺序归一化(B8、B23);每步 logits 非有限即 ST6。
- general NLL:窗口的存储 id,不加特殊 token,t 从 2 起,除以 n_w − 1。评测 FP32、关闭 autocast;正式与预检模式只在 GPU 上评测。
- `evaluate_model(split="test")` 只在正式模式、并以调用方的冻结文件 `fz` 通过 `leakage.verify_authorization` 之后可用;非有限分数与 EM 解码中(首次前向与循环内每步)的非有限 logits 带数值抛 `NonFinite`(ST6,由 `stops.st6` 决定状态)。

### `stats.py`(协议第 5、6 节)

Score(f) = 该 fact 问句的 mean(精确分数);Acc = fact 的 mean;AllCorrect、FPR、ImmediateGain、dNLL 与 PPL 退化;配对 bootstrap 以 fact 为单位,在 natural、random 内分别有放回重抽,10,000 次,`rng_rule(BOOTSTRAP_SEED, "<X>-<Y>:<split>:<seed 或 avg>")`(B10–B12);seed-average 先对每条 fact 取 3 个种子的平均;G0.10 的 σ_d、其 bootstrap 分位、所需 n 与半宽检查(B13)。

### `gate.py`(协议第 8、9 节)

G0.1–G0.10 与 T1–T3 的计算与判定;只输出第 9 节的状态词;原因映射与第 9 节未覆盖之处见 B14、B24;G0.8 要求恰为 F 选定配置 3 个种子的复评(B15);冒烟模式下状态固定为 NOT_TESTED 并附“冒烟测试，不构成结论”,不输出原因词;预检模式拒绝判定。另有第 6 节各比较项(每个种子与 seed-average)的报告函数。

### `stops.py`、`compute.py`(协议第 0、7、10、11 节)

- ST1–ST13 各有检查函数,动作文字取自冻结协议的行;ST12 调用 `frozen.load` 与 `data.verify`;ST13 另有按文件检测的 `st13_scan`。第 11 节未写状态之处见 B16。
- 确定性设置(`use_deterministic_algorithms`、TF32 关闭、`CUBLAS_WORKSPACE_CONFIG=:4096:8`,取自协议第 0 节);设备检查(ST8)与设备全名账本(ST9);GPU 累计时钟(ST7,开始时刻即落盘,进程中断不少算);预检汇总与总时长估算(ST11,B17);FLOPs(第 10 节系数)。

### `record.py`、`test_data.py`

- `record.py`:第 10 节模板字段从冻结协议读出,不可缺少;环境块记录解释器、库版本(元数据与 `__version__`)、CUDA、设备、确定性设置、git 状态、PROTOCOL_FROZEN(加载时解析的字节、工作区字节、LF 归一化三种哈希;加载后改变即 ST12)、冻结提交与哈希、B1–B24;冒烟与预检记录带标注、被拒于正式结果目录。Gate 0 记录与选择冻结记录的格式由 `gate0_record`、`selection_freeze_record` 定义。
- `test_data.py`(TEST 生成器):依次检查 (1) PROTOCOL_FROZEN 有效且 ST12 通过;(2) 已提交的正式 Gate 0 记录,状态 PASS;(3) 已提交的正式选择冻结记录(选定配置合法、数据哈希一致、30 次训练的 checkpoint 哈希齐全、绑定 Gate 0 记录);另加超出任务书的一条:B1–B24 全部裁决(待决第 2 项)。任一不满足即打印原因与 RESULT: FAIL、exit 1,不建目录、不解析任何 test 行。TEST 生成、TEST 部分泄漏检查与 TEST 评测都先经 `leakage.verify_authorization` 按已提交记录复核授权:授权的冻结提交等于当前 PROTOCOL_FROZEN 与调用方加载的冻结文件;两份已提交记录的 SHA-256 等于授权所带;条件 2、3 的内容检查与生成器相同(共用 `record.gate0_record_problem`、`freeze_record_problem`,数据内容哈希与冻结值比较);解释全部已裁决。条件 1(ST12)由每步开始时的 `stops.st12` 负责。

## 单元测试(指令第 6 节第 2–9 项;Owner 额外要求 5–7)

| 项 | 测试 |
|---|---|
| 2 打分 | `test_scoring.py`:120 条 learned × 2 个 DEV 问句的打分区间与 TRAIN 陈述句中答案片段(按 offset 定位)一致,不一致 0;闭卷输入同样一致;第 3 轮的 28 个 token 逐个一致(起点 25);`enable_thinking` 改为 True 时同一检查失败;`enable_thinking` 不是任何函数的参数;全部 1280 个候选的区间等于 `encode(" " + c)` |
| 3 并列 / mean / fact 单位 | `test_stats.py`:并列判错;全零 logits 时全部并列、Acc = 0;Score 为问句 mean、Acc 为 fact mean(不等于问句合并率);bootstrap 与独立重写在同一随机流下逐值相同;每条 fact 的问句数加倍时 CI 完全相同 |
| 4 LoRA 第 0 步 | `test_lora.py::test_step0_output_equals_base`(logits `torch.equal`) |
| 5 arm A | `test_arm_a.py`:第 1 步 KL 恰为 0;base 副本无 `requires_grad`;训练后 base 副本哈希不变而训练模型改变 |
| 6 S、Y 用 F 的配置 | `test_train.py`:30 次运行;搜索阶段没有 S、Y;S、Y 的学习率与 weight decay 等于 F 选定配置(换一个选定配置同样跟随) |
| 7 gate | `test_gate.py`:每个 G0 条件在边界上满足、越界不满足;原因映射;词汇只来自第 9 节;冒烟为 NOT_TESTED;T1–T3;G0.8 复评比较 |
| 8 stops | `test_stops.py`:ST1–ST13 各有触发与不触发用例;GPU 时钟、设备账本、设备检查、预检估算 |
| 9 TEST 生成器 | `test_test_data.py`:当前状态下子进程运行 RESULT: FAIL、非 0 退出、无输出目录、数据与仓库不变;拒绝时只解析 DEV 行;条件 2、3 各有正、反用例;解释裁决检查(不依赖当前裁决状态);手造授权在任何读取之前被拒;授权复核各分支(冻结提交与当前 PROTOCOL_FROZEN、与加载的冻结文件;哈希;Gate 0 状态;选定配置、S 被选、checkpoint 缺一个或非十六进制、数据内容哈希、绑定;待决解释)各有用例,以报错文字匹配区分。`impl_b/t12_fix3.txt` 的变异检查只做了 6 项(EM 循环内的非有限值检查、待决解释、整个 `freeze_record_problem` 调用、与加载的冻结文件比较、checkpoint、数据内容哈希),各自使对应用例失败;其余分支没有做变异。其中“与当前 PROTOCOL_FROZEN 比较”一项现有用例区分不出(三方比较合成一个条件,报告提交审查 MINOR,登记 BE2,阶段 C 补用例) |
| Owner 5 LoRA 手算 | `test_lora.py`:float64 下逐元素手算 W·x + (alpha/r)·B·A·x 与前向输出一致(B 非零);只有 LoRA 参数可训练,训练后全部 base 参数哈希不变;A 的值与 `rng_rule` 的 `r.uniform` 逐值相同 |
| Owner 6 KL | `test_arm_a.py`:对不对称分布,结果等于 KL(p_base ‖ p_θ)、不等于反向;两篇长度不同的文档按 token 加权((k1 + 4k2)/5),不是逐篇平均;补齐位置与 t = n_x 之后的位置不计入。`test_train.py`:调用处 (θ, base) 顺序与梯度(θ 带梯度、base 不带;λ 不同的两次运行参数不同,KL 被 detach 时两者逐位相同) |
| Owner 7 可训练参数数 | `test_train.py`:随机小模型上 F、A、S、Y 等于全部唯一参数,L 等于 Σ r·(in + out);固定 revision 的 `config.json` 在 meta 设备上:F、A、S、Y 为 1,720,574,976(等于协议第 7 节),L 秩 32 为 34,865,152(协议“3,486 万”)、秩 8 为其 1/4 |
| 模式隔离(指令第 7 节,阶段 C 验收第 5 项) | `test_train.py`:正式模式不能带缩减步数;正式与预检模式不在 CPU 上训练;运行长度只来自 `mode.steps`;预检只能是 20 步与第一个配置 |

运行:`METRIX_INPUTS_DIR=<fetch 的目录> python -m pytest metrix/e1-pilot/tests`;另需 `python -m metrix_e1.train fetch-config --inputs <同一目录>` 下载 `config.json`(`impl_b/t2_fetch_config.txt`,sha256 `1ddb5b89…`,不是权重文件)。

## 审查

审查原文都由 `round6/review_extract.py` 从本会话的 subagent 记录原样提取;`extract_log.txt` 核对了每份调用文字与 subagent 收到的第一条消息相同;每次调用前比对了 frontmatter 与 tools 行(`preflight_tools_check*.txt`);每次 `git commit` 前核对暂存内容与审查输入逐字节相同(`precommit_check.txt`),推送后核对提交的 diff 与审查输入逐字节相同(`impl_b/t7`、`t9`、`t11`)。原文中 `…/scratchpad/review_work/X` 对应 `reviews/74a4d444…/X`,`review_fix/X` 对应 `reviews/fdbb9def…/X`,`review_fix2/X` 对应 `reviews/493d7f9c…/X`,`review_report/X` 对应 `reviews/74a4d444…/X`(其中 `extract_log.txt` 改名为 `extract_log_report-commit.txt`,`check_resume_message.py` 改名为 `check_resume_message_report-commit.py`,以免与工作提交的同名文件冲突);三个目录是临时目录原件的完整副本(`impl_b/t12b_review_records_copy.txt`:`diff -r` 无差异,并列出每个文件的 sha256)。`review_input.diff` 与 `review_input_round1.diff` 内容相同(第 1 轮调用文字引用前者)。data-auditor 在正式记录前的试跑输出与辅助片段(`trial*`、`id06_base.py` 等,原在会话临时目录)原样入库于 `audit/stdout/impl_b/trials/`(同一记录中 `cmp` 相同);auditor 临时目录中的下载文件、重新生成的数据与变异源码副本没有入库(可由 `audit/` 脚本重新生成)。

| 被审内容 | code-reviewer | data-auditor(仅作参考) | 处理 |
|---|---|---|---|
| 工作提交,第 1 轮(暂存;父 `0bc0eecf`) | PASS;10 MAJOR、19 MINOR | PASS;3 条观察 | 第 2 轮前修:MAJOR 1–10 中 9 条改代码(其中 B5、B17 改后仍交 Review Gate),B14 只登记、交 Review Gate;19 条 MINOR 中 17 条修,余见 `DEFERRED_MINORS.md` 1.22 节;观察 1 改为按字节读 `eval_sets.jsonl` |
| 工作提交,第 2 轮(第 1 轮修复后;即提交 `74a4d444`) | PASS;2 MAJOR、15 MINOR | PASS;6 条观察(观察 1:参考比对测试让 `l6_check.py` 以文本模式读完整文件) | 修复提交;余见 1.23 节 |
| 修复提交 `fdbb9def` | PASS;1 MAJOR(交 Review Gate:观察 1 的登记与已执行的运行)、9 MINOR | PASS;4 条观察 | 第二个修复提交;余见 1.24 节 |
| 第二个修复提交 `493d7f9c` | PASS;1 MAJOR(上一条的遗留,交 Review Gate)、8 MINOR | PASS;7 条观察;20 个埋入故障全部检出 | 本报告提交;见 1.25 节 |
| 报告提交(暂存;父 `493d7f9c`;因 HTTP 429 中断后续审) | PASS;1 MAJOR(交 Review Gate:待决第 3 项漏列 `data.py` 自身以文本模式读取的运行)、12 MINOR | PASS;6 条观察;35 个埋入故障全部检出 | 审查之后只改报告、登记与证据(见下);代码与测试类 MINOR 不在本提交改,登记 1.26 节,阶段 C 处理 |

两个审查 subagent 的信任状态按 `metrix/CLAUDE.md` 第 10 节:code-reviewer 已验证(PASS 仍附原文);data-auditor「待验证」,其 PASS 仅作参考。连续未 PASS 的轮数为 0。

报告提交:提交前由 code-reviewer 与 data-auditor(代码部分涉及 TEST 路径与评测代码)审查,调用文字、续审消息、输入、中断记录与原文放在 `reviews/74a4d444…/` 的 `*_report-commit*`(与临时目录原件逐一 `cmp` 相同,`impl_b/t12d_report_review_records.txt`)。两份都是 PASS。按阶段 A 报告提交的先例,审查之后只改了本文件、`DEFERRED_MINORS.md` 与证据,没有再请审查;被审的暂存树为 `0417d563…`(`git write-tree`,两份审查之后、任何改动之前),审查之后相对它的全部改动见同目录 `report_commit_post_review.diff`(新增的审查记录与 data-auditor 本轮输出只列 stat)。代码与测试没有改动:`impl_b/t12c` 在被审的暂存代码上重跑 204 passed,`src/`、`tests/` 的树在运行前后相同。code-reviewer 的 MAJOR 补入待决第 3 项;12 条 MINOR 的处理见 `DEFERRED_MINORS.md` 1.26 节:报告与登记类 5 条已改(BE3、BE4、BE5、BE7、BE11);被测代码与暂存内容的对应补了 `t12c`(BE8);推送记录改为推送后立即作为证据提交(BE6);代码与测试类 4 条(BE2、BE9、BE10、BE12)与已运行的变异脚本中的未用变量(BE13)登记,阶段 C 处理。data-auditor 的观察 3(`verify_authorization` 信任调用方传入的 `fz`)登记 BE14。

## 待 Review Gate 决定

以下各项都没有改协议。

1. **B1–B24**(`src/metrix_e1/interpretations.py`):协议留有选择余地之处的实现选择,逐条写明位置与理由。code-reviewer 第 1 轮逐条判断:B6、B7、B9、B18 与协议原文一致;B16 部分一致(ST4、ST5、ST6 一致;ST3、ST7、ST11 的状态协议未写);其余属于协议未覆盖。B5(随机数来源已改为 `rng_rule` 本身,分布与 purpose 仍为选择)、B14(与第 9 节的四点张力)、B17(预检估算)审查方标为 MAJOR 级。data-auditor 第 1 轮另指出 B1–B3 的具体后果:s 从 0 起时 300 步的锚文档全部不同;epoch 从 0 起或用 `sample` 代替 `shuffle` 时 batch 全部不同;`train_Y.jsonl` 的行序未冻结。
2. **TEST 生成器的第 4 个前提**:B1–B24 全部裁决之前 `test_data` 拒绝生成 TEST(超出任务书第 5 节的三个条件;依据是 B19 决定 TEST 部分的泄漏检查数什么,其余决定 TEST 评测的 checkpoint 如何产生)。请决定保留或删除。
3. **“UTF-8 解码 test 行”是否属于协议第 3 节的“读取 TEST”**(data-auditor 第 1、2 轮观察 1;修复提交 code-reviewer MAJOR):协议把“解码 test 行的内容”算作读取,把“解析 split 字段、计数”排除在外;以文本模式逐行读取会把 test 行的字节解码成字符串(不解析、不分词、不用于计算)。
   - 包内:`data.build_general_dev` 自工作提交起按字节读取,只有 DEV 行被解码与解析。
   - 测试:阶段 A 起 `test_data_hashes.py::test_byte_identical_to_reference_scripts` 让阶段 A 的参考脚本 `reports/round5/l6_check.py` 以文本模式读取完整文件。第二个修复提交起改为只给它 DEV 行的字节副本(脚本本身未改)。
   - 已经发生的、以文本模式读取完整文件的运行(都没有解析或分词 test 行):冻结前第 5、6 轮直接运行 `l6_check.py`(`round5/t5_l6_check.txt`、`round6/t2_l6_check.txt`、`round6/t2_l6_judgment_demo.txt` 与 `round6` 的守卫测试);阶段 A 的 pytest(`impl_a/t4_pytest.txt` 两次、`t6_fix_commit.txt` 一次;阶段 A 开发中另有未记录的运行);阶段 B 的 pytest(`impl_b/t1_env_baseline.txt`、`t4_pytest.txt` 已记录一次与被覆盖的一次、`t6_fix_round.txt`、`t8_fix_commit.txt`;另有开发中未记录的全套运行约 4 次)。data-auditor 没有运行过这个脚本(它的脚本按字节读取)。`t10`、`t12` 起不再如此;裁决之前不再对完整的 `eval_sets.jsonl` 运行 `l6_check.py`(`DEFERRED_MINORS.md` BC1)。
   - 包内 `data.py` 自身(报告提交 code-reviewer MAJOR,BE1;data-auditor 第 1 轮观察 1):`build_general_dev` 从阶段 A 工作提交 `602a39e8` 起到阶段 B 工作提交 `74a4d444` 之前都以文本模式打开 `eval_sets.jsonl`(`602a39e8`、`219c4a60`、`620f8611`、`0bc0eecf` 中 `data.py:499` 为 `open(eval_sets_path, encoding="utf-8")`,四个提交的 `data.py` sha256 都是 `8a531939…`;第 1 轮审查输入没有改这一行,第 2 轮审查输入 `review_input_round2.diff:1715-1717` 改为 `"rb"`)。test 行被解码后只做行前缀匹配、随即跳过,不解析、不分词。凡是运行 `data generate`、`data verify` 的运行都经过这条路径(TEST 生成器的条件 1 与 pytest 的数据生成也经由它们)。已记录的运行:
     - 阶段 A,`data.py` sha256 为 `8a531939…`(与上述提交相同,文本模式已核实):`impl_a/t2_fetch_generate.txt:122`(generate)、`:154`(verify);`impl_a/t4_pytest.txt:131`;`impl_a/t6_fix_commit.txt:21`(generate)、`:45`(verify)、`:70`(pytest)。
     - 阶段 A,较早的未提交版本(`t2:89`、`t4:32` 记 sha256 `efa35625…`,没有入库,读取方式无法核实,推定相同):`t2:92`、`t4:42`;`t2:27`、`:47`、`:78` 之前没有记录哈希。
     - 阶段 B 工作提交之前(`data.py` 只改了 `y_ratio`,打开方式未改):`impl_b/t1_env_baseline.txt:97`(generate)、`:118`(pytest);`t3_generate_leakage.txt:3`(generate)、`:36`(verify);`t4_pytest.txt:3`(pytest,含 TEST 生成器拒绝的测试)。`t5_dump_for_audit.txt` 只对输入文件求哈希,不经过这条路径。
     - 阶段 A、B 开发中另有未记录的运行。`impl_b/t6` 起(第 1 轮修复之后)按字节读取。
   - data-auditor 自己的脚本:冻结前第 5 轮的 `audit/r5_l6.py:68`、`audit/r5_cmp_general.py:13` 也以文本模式打开完整文件(stdout `audit/stdout/2724144b…/03_r5_l6.txt`、`04_r5_l6.txt`、`05_r5_cmp_general.txt`);阶段 A 起它的脚本都按字节读取(如 `ia_06_general.py:41`)。
   - 备案(data-auditor 第二个修复提交观察 5,BD10):`tests/test_st12.py` 翻转临时副本中间的一个字节以检验 ST12,这个字节落在 test 行范围内;只改原始字节、随后只对整个文件求哈希,不解码、不解析。
   - 按宽读法这些都不是读取 TEST;按严读法它们是冻结前读取 TEST(ST13:IMPLEMENTATION_FAIL,本次 Pilot 全部作废——Pilot 尚未开始任何训练或评测)。请裁决采用哪种读法。
4. **B19 预告的停止点**:阶段 A 报告预告“第 8 步‘对 TEST 运行 L3–L5’中 L3、L5 对 TEST 的具体含义,届时如协议未覆盖即停下报告”。本阶段没有停止,而是按 B19 实现(L4 对 TEST 问句;L3a、L3b、L5 按 Gate 0 重跑;L6 TEST 部分按协议第 3 节)并列入待决;理由是本阶段不运行 TEST 部分,且第 4 个前提保证裁决前不会运行。code-reviewer 判为须由 Review Gate 明确接受。
5. **G0.3 / G0.9 / G0.10 不满足时没有第 9 节的原因词**,以及 G0.5 的原因(B14):见 B14 文字。
6. **推送记录的证据提交不经审查**(报告提交 code-reviewer MINOR,BE6):阶段 A 的推送记录 `impl_a/t8_report_push.txt` 留在工作区、随容器回收丢失。本阶段按 Owner 第 0 项(“以后每个阶段都用这种方式核对推送结果”,第 0 步的证据提交“不需要审查”)把报告提交的推送记录 `t13` 在推送后立即单独提交并快进推送,不经审查;这次推送自身的输出 `t14` 随阶段 C 第 0 步的证据提交入库。请确认这一读法(证据提交只含推送与 ls-remote 的原始输出)。

## 留给阶段 C 的事项

- `run_pilot.py` 编排:每步开始前 ST12 与 `stops.st13_scan`;设备检查、设备全名账本、GPU 时钟;预检(第一个配置 20 步 + 一次 FP32 DEV 评测计时,B17);第 3–8 步;Gate 0 记录与选择冻结记录(`record.gate0_record`、`selection_freeze_record`)的写入与提交;checkpoint 的保存与哈希(全模型 FP32 每个约 6.9 GB,F/A/S/Y 选定配置 12 个,另加选择前的搜索 checkpoint,磁盘规划写入 RUNBOOK)。
- TEST 评测的硬性前提(第 2 轮 MAJOR 2 的余项;修复提交与第二个修复提交审查 MINOR;`DEFERRED_MINORS.md` BB1、BC2、BD8):ST10 通过的凭据(Executor 与 data-auditor 的 L6 TEST 计数一致、L3–L5 TEST 部分在上限内)须以已提交的记录体现,`evaluate_model(split="test")` 前核对;“TEST 只评一次”须有已提交的标记并在再次评测前拒绝。阶段 C 审查时复核这两项,缺任一项不进入 TEST 评测。
- `evaluate_model(split="test")` 的调用方(阶段 C 的驱动代码)加入后,data-auditor 再审 TEST 路径(data-auditor 第 2 轮观察 3)。
- 只在阶段 C 接线的函数:`record.render_text`、`compute.cost_usd`、`compute.run_flops`、`compute.preflight_summary`、`compute.estimate_total_hours`、`stats.immediate_gain`、`gate.report_comparisons`、`stops.st13_scan` 的调用方。
- 报告提交审查登记的代码与测试 MINOR(`DEFERRED_MINORS.md` 1.26 节 BE2、BE9、BE10、BE12、BE13):在阶段 C 的第一个代码提交中处理并送审。
- `config.json`(sha256 `1ddb5b89…`)没有冻结值;冒烟小模型若由它构造,RUNBOOK 与实验记录写明其哈希。
- 阶段 A 裁决 4 与登记 AA4:CUDA 构建兼容性(另锁 CUDA 12.x 构建、驱动确认、一次 Pilot 一种构建);`PYTHONPATH=metrix/e1-pilot/src`(AA9);`check_device` 与 `require_gpu` 在 A100 上的首次运行;确定性模式下 CUDA 上个别算子可能报错(本容器无 GPU,未验证)。

## 推送

- 每个提交推送前后都用 `git ls-remote` 核对远端分支与两个标签(Owner 第 0 项),推送前 `git merge-base --is-ancestor` 确认是快进;推送命令只推分支 `HEAD:refs/heads/metrix-e1-pilot-protocol-v1`,没有 `--tags`、没有 `--force`。
- 记录:第 0 步 `impl_b/t0b_step0_push.txt`(`620f861..0bc0eec`);工作提交 `t7_work_commit_push.txt`(`0bc0eec..74a4d44`);修复提交 `t9_fix_commit_push.txt`(`74a4d44..fdbb9de`);第二个修复提交 `t11_fix2_commit_push.txt`(`fdbb9de..493d7f9`)。每次推送前后两个标签都是 `metrix-e1-pilot-frozen` → `6a474e4a…`、`metrix-e1-pilot-frozen-v1.1` → `87a244db…`(peeled),没有变化。
- 本报告提交的推送输出写入 `impl_b/t13_report_push.txt`(推送时由 `logrun.sh` 立即记录),随即作为证据单独提交并快进推送(待决第 6 项);那次推送的输出写入 `impl_b/t14_evidence_push.txt`(工作区),随阶段 C 第 0 步的证据提交入库,并在最终回复中给出;阶段 C 开始时以 `git ls-remote` 重新核对。
