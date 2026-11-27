# code-reviewer, C3 commit, round 1: final report, unchanged (extracted by reports/round6/review_extract.py from code-reviewer_round1_transcript.jsonl)
# staged tree d27b68da355debb5ff158077e6f2d8d79f07a6a1, parent cc18466f8d327f37c6f6dd272b8e264d239ee386; invocation text: code-reviewer_round1_prompt.txt
---
code-reviewer 审查：METRIX E1-PILOT 阶段 C 第 3 段（C3：RUNBOOK_A100.md 与最终报告），第 1 轮。暂存树 d27b68da355debb5ff158077e6f2d8d79f07a6a1，父提交 cc18466f8d327f37c6f6dd272b8e264d239ee386。

## 方法

- 我先读了仓库中的 /home/user/OpenMythos/.claude/agents/code-reviewer.md，以它为定义。它的 tools 行（Read, Grep, Glob）与 preflight_tools_check.txt 一致。
- 只用了 Read、Grep、Glob，没有运行代码、git 或 pytest。
- 工作区中的 RUNBOOK_A100.md 与 input.diff 逐行对应：文件行号 = diff 行号 − 14。下文用文件行号。
- 标注规则：
  - 「已验证」：引用了仓库中已提交的原始输出或文件原文，并写明行号。
  - 「算术」：按文件原文中的数字计算，没有运行代码。
  - 其余标「未验证」。

## 一、核对通过的部分

- **哈希（已验证）**
  - RUNBOOK 第 2 节前 7 个哈希，与 /home/user/OpenMythos/metrix/e1-pilot/DATA_MANIFEST.json 第 20–23、228、230、237 行逐个相同。
  - config.json 的哈希 1ddb5b89… 与 reports/impl_c/c1_01_env_fetch.txt:27、c2_01_env_fetch.txt:26 相同。
  - 两个 safetensors 的 SHA-256 与字节数，与 reports/impl_c/c3_hf_tree_70d244cc.txt:11–12 相同。该文件第 14 行 tokenizer.json 的 LFS oid 等于冻结值 aeb13307…，可作旁证。
- **计数与费用（已验证）**
  - 第 6 节的 80 次加载、77 次 state_sha256、45 次文件 SHA-256、30 次保存，与 pilot.evaluation_plan 一致（pilot.py:169–178，各项为 32、30、18、17、15、16）。
  - 58 个 DEV 评测单位与 compute.evaluation_units 一致（compute.py:202–210）。
  - 1.3×1.8、2.8×1.8、2×1.8、4.5×1.8 四个乘法正确。
  - 注意：区间本身有问题，见 MAJOR 3、4。
- **裁决照录（已验证）**：2026-11-27 裁决两项在 IMPL_C_REPORT.md:64、67 逐字照录，对照 tasks/IMPL_C2_OWNER_MESSAGE.md:4–5。
- **C2 节的提交与审查表（已验证）**
  - 四个提交的 code-reviewer 结论都是 PASS。MAJOR 行数与全部问题行数分别为 12/34、4/22、3/12、0/8，与表中一致。
  - 测试与变异数与原始输出一致：
    - c2_05:108、146
    - c2b_03:103、160
    - c2c_03:142、221
    - c2c_04:52
    - c2d_01:142、236
  - 冒烟各步耗时与 c2d_02:51–114 一致；文件数之和为 74。
- **DEFERRED_MINORS 1.35（已验证）**
  - 对照 reviews/a0e04d1f…/code-reviewer_round1.md:98–112 与 data-auditor_round1.md:232–238。
  - CI1–CI8 对应 code-reviewer 的 8 个 MINOR；CI9 对应 IC10-M1；CI10、CI11 对应 data-auditor 的观察 2、3；观察 1 并入 CI6。没有遗漏。
  - 各项都不影响协议一致性、数据、指标或隔离，登记符合 Task Order 第 9 节。
  - 两处处理说明不准确，见 MINOR 9。
- **c3_01 与 c3_checks.sh（已验证）**
  - c3_01 记录了：首尾 INDEX_EQUALS_a0e04d1f…（第 18、117 行）；324 passed（第 103 行）；generate 与 verify 均 RESULT: PASS，四个冻结哈希相同（第 44–57 行）；TEST 生成器拒绝，--out 未创建（第 60–65 行）；outside_metrix_check PASS（第 86 行）。
  - 送审树中下列文件的 blob 与 reviews/a0e04d1f…/tree.txt 逐个相同：run_pilot.py、pilot.py、testgate.py、test_data.py、train.py、data.py、evaluate.py、compute.py、stops.py、record.py、leakage.py、frozen.py、tests/test_run_pilot.py（逐行比对两份 tree.txt）。所以送审树的代码就是 a0e04d1f 的代码。
  - c3_checks.sh 运行的命令支持验收第 1、2、4、7 项的说法。
- **TEST 路径（防范对象内；未验证，读代码）**：没有找到按 RUNBOOK 3.6–3.8 操作就会评测 TEST 两次，或在 ST10 不成立时评测 TEST 的路径。依据：
  - test-evaluate 的只读已评检查（pilot.py:1252–1263）。
  - begin 中 fetch 后的 refuse_if_marker 与 st10_check（testgate.py:440–443、351–386）。
  - 每个模型评测前的 require_test_session。
  - 计数文件的路径与字段与 testgate.AUDITOR_L6_REL、auditor_count_record 一致（testgate.py:91、336–340）。
  - C1 裁决第 6 项的 GitHub 设置、2026-11-27 裁决第 1 项都已写入（RUNBOOK:25、108）。
- **未发现与 metrix/CLAUDE.md 冲突的指示（已核对）**：租卡（RUNBOOK:7）、删除文件（RUNBOOK:146 写明 checkpoint 不删）、推送方式（快进、不经 PR：RUNBOOK:25，C1 裁决第 6 项）。其余与 CLAUDE.md 有关的缺口见 MAJOR 5、6。

## 二、问题

BLOCKER | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:112–140（第 4 节；全文检索） | 【已验证，读文件】RUNBOOK 没有写「确定性模式下 CUDA 算子报错时的处理（停下报告，不得关闭确定性）」。这是 Owner 转达的阶段 C 要求第 9 项（tasks/IMPL_C_OWNER_MESSAGE.md:31），经第 25 行「其余按上次阶段 C 指令的第 1、6、7、9、10 项执行」生效。在 RUNBOOK 中检索「确定 / determinis / CUBLAS / 算子 / 报错」均无结果；第 9 项只落实了磁盘规划（RUNBOOK:20）。CPU 冒烟测不到只在 CUDA 上出现的确定性报错，A100 上第一次遇到时 Executor 没有书面依据。报告却把验收第 8 项写为「满足」，状态写为 IMPLEMENTATION_READY（IMPL_C_REPORT.md:3、258）；验收节也没有逐项核对 Owner 消息中的阶段 C 要求 6–10 | IMPL_C_OWNER_MESSAGE.md:31「9. RUNBOOK 写明磁盘规划（FP32 全模型 checkpoint 约 6.9 GB/个）、确定性模式下 CUDA 算子报错时的处理（停下报告，不得关闭确定性）。」 | 在第 4 节加一条：出现 use_deterministic_algorithms 报错（如 “does not have a deterministic implementation”）时立即停止；不得关闭确定性，不得改 CUBLAS_WORKSPACE_CONFIG 或 TF32 设置，不得重跑；按崩溃处理（run_gate 已写 NOT_TESTED 记录），连同日志报告 Owner。在「阶段 C 验收」后增加对 IMPL_C_OWNER_MESSAGE 要求 6–10 的逐项核对

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:145 | 【未验证，没有运行 git；依据 .gitignore 原文与 git 对被忽略路径的已知行为】手册要求把日志复制到 metrix/e1-pilot/results/logs/ 并按明确路径 git add，但这个路径被仓库根目录的 .gitignore 忽略两次：第 65 行 `logs`（匹配任意层级的 logs 目录）；第 141 行 `*.log`（fetch.log、formal.log、test_generate.log、test_evaluate.log 都匹配）。不加 -f 时 git add 会失败。照做的 Executor 要么卡在这一步，要么日志不入库，违反 metrix/CLAUDE.md 第 9 节「原始输出一律写入仓库并推送」。pilot.py:97–98 已因 `runs` 被忽略而改名，说明这类风险已知 | /home/user/OpenMythos/.gitignore:65 `logs`；:141 `*.log`；RUNBOOK:145 “复制到 `metrix/e1-pilot/results/logs/`” | 改用不被忽略的目录与扩展名（例如 results/command_output/<命令>.txt），或写明 `git add -f <路径>` 并在提交前用 `git diff --cached --stat` 核对；同步修改 3.4–3.8 中 tee 的文件名

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:156、161、163；/home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:258 | 【算术，按第 156 行原文】checkpoint 开销区间的上界与它自己的依据对不上：
- 第 156 行的依据：80 次加载 × 10–20 s；77 + 45 + 30 = 152 次哈希与保存 × 5–20 s。
- 上界应为 80×20 + 152×20 = 4,640 s ≈ 77 分钟。去掉在 GPU 计时之外的 15 次 TEST 文件哈希，也约 72 分钟，不是手册写的 50 分钟。下界 26 分钟正确。
- 因此 GPU wall-clock 上界约为 50 + 60 + 72–77 + 5 ≈ 3.1–3.2 小时，不是 2.8 小时。GPU 部分费用上界约 5.6–5.8 美元，不是 5.0 美元。租用时长与费用的上界也偏低。
- 3.2 小时离 ST7 的 4 小时只差约 0.8 小时，这正是 Owner 决定租卡时需要看到的数 | “合计约 80 次加载、77 次 `state_sha256`、45 次文件 SHA-256、30 次保存,…按加载 10–20 秒、哈希与保存各 5–20 秒估计,约 25–50 分钟” | 按依据重算区间（或收窄单项区间并说明理由）；同步更新 RUNBOOK:161、163 与报告验收第 8 项

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:154、114、165 | 【已验证 + 算术：a_factor 取自已提交的冒烟记录；B17 的数值由算术推得，没有运行】ST11 读的数与手册的估计口径不同，手册没有给出 ST11 的风险：
- 第 6 节把 arm A 按 1.5 倍估计。
- ST11 读的 B17 估算，以及 ST7 对每次训练的事前判断，都按 FLOP 比例放大 A 的每步时间：a_factor = 1 + (2+6)·T_anchor / (6·T_fact)。冒烟记录中为 6.75（T_anchor 511.97，T_fact 118.67）。
- 按手册自己的上界（0.3 s/步，DEV 评测 1 分钟）：B17 ≈ 0.3×300×(22 + 8×6.75)/3600 + 58/60 ≈ 1.90 + 0.97 ≈ 2.9 小时，加上预检已用时间约 2.95 小时，离 3.5 小时只剩约 0.55 小时。
- 若 Review Gate 对待决第 2 项决定 ST11 读「B17 + checkpoint 开销」，同样假设下：
  - 开销按代码公式为 32×20 + 30×100 + 18×20 + 17×20 + 15×20 = 4,640 s ≈ 1.29 小时；
  - 两者之和约 4.2 小时，会触发 ST11。
- 手册没有给出预检时 B17 的预期值。第 165 行“预估超出上表区间,以预检为准”把两个口径不同的数放在一起比较，Owner 决定租卡时看不到这一风险 | compute.py:221–223 `a_factor = 1.0 + ((acc.forward_flops_per_param_token + acc.train_flops_per_param_token) * anchor_tokens_per_step / (acc.train_flops_per_param_token * fact_tokens_per_step))`；`train_s = mean_step_seconds * tr.total_steps * (other_runs + a_runs * a_factor)`；pilot.py:344 `factor = q["a_factor"] if spec.arm == "A" else 1.0`；reports/impl_c/c2d_smoke_records/step2_record.json:97、100、122；RUNBOOK:154 “A 另有…,按 1.5 倍计” | 在第 6 节另列两个区间：预检时 ST11 读到的 B17 估算（按 a_factor ≈ 6.4–6.8 计算），以及「B17 + checkpoint 开销」。写明它们与实际 wall-clock 的区别，并把 ST11 的风险写进最终状态中待决第 2 项的说明

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:91–98、145 | 【已核对文件；不确定之处见末尾】第 3.7 节调用 data-auditor、以及运行期间的手工提交，都没有写明 metrix/CLAUDE.md 第 5、9 节的义务：
- (a) 调用前比对仓库文件与已加载定义的 frontmatter，tools 行不一致即停（第 5 节第 6 条）。手册只写了调用文字的第一句。
- (b) 审查原始输出存入 reviews/<commit>/（第 5 节第 5 条）。
- (c) data-auditor 的 audit 脚本与完整 stdout 入库（第 9 节）。第 98 行“Executor 只提交这一个文件”之后，手册没有说这些文件何时提交。按第 108 行，它们只能在 begin 之前或 finish 之后提交，手册应写明。
- (d) 第 5 节第 1 条要求每次提交前调用 code-reviewer。两次日志提交与计数文件的提交，手册没有说是否属于免审的证据提交。补充裁决 1 的证据提交只限 reports/、reviews/、audit/，results/logs/ 不在其中；该裁决的作用范围也只是本阶段。
- 不确定：Review Gate 可能打算对运行阶段的手工提交另作规定，所以列为 MAJOR | RUNBOOK:98 “Executor 只提交这一个文件并推送”；metrix/CLAUDE.md 第 9 节 “data-auditor 须提交 audit 脚本的完整 stdout”；tasks/IMPL_C_OWNER_MESSAGE.md:18 | 在 3.7 写明：frontmatter 比对；审查原文的存放位置；audit 脚本与 stdout 在 3.8 之前随计数文件一起提交，或在 finish 之后提交。在第 5 节写明运行期间手工提交的审查方式，或列为待 Review Gate 决定的事项

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:51–73、162 | 【读文件；不确定是否为问题】metrix/CLAUDE.md 第 4 节写「环境、下载、冒烟测试先在 CPU 环境完成;租卡后只跑正式流程」，而 RUNBOOK 3.1–3.4 在租用的 A100 上做环境安装与全部下载（约 0.5 小时计入租用时长）。权重只能在 A100 主机下载：fetch_model 先做 ST8（pilot.py:527–536），Task Order 红线 2 也禁止在别处下载。所以这一做法可能是必要的；但手册没有说明它与第 4 节的关系，也没有请 Review Gate 确认 | RUNBOOK:162 “另加环境安装与下载约 0.5 小时” | 写明哪些步骤已在 CPU 环境完成（依赖锁、分词器、parquet、config 的哈希核对与冒烟），以及为什么 A100 上仍须重新安装与下载；列入待 Review Gate 确认的事项

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:7 | 【已核对】交叉引用错误：TEST 生成与 TEST 评测在第 3.6、3.8 节，不在第 4 节 | “第 4 节的 TEST 生成与 TEST 评测各需 Owner 另行批准” | 改为“第 3.6、3.8 节”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:29、39 | 【已验证，读代码】对 eval_sets.jsonl 一行不准确。它在仓库内，不是下载的；`metrix_e1.data fetch` 也不核对它（fetch_inputs 只核对 input_paths 中的 6 个文件）。它由 data.check_inputs 在 generate / verify 时核对，并在第 2 步起的 ST12 中核对。所以“全部由命令下载”和“核对方式：同上”都不适用于这一行 | data.py:177–183、186–198、201–208 | 改为“仓库内文件；由 `metrix_e1.data generate/verify` 与每步的 ST12 核对”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:106；/home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md:645、648 | 【已验证，读代码】3.8 节的检查顺序与代码不完全一致：
- device_check 只做 ST8（pilot.py:1177）。
- ST9（设备记录比对）与 ST7 要在核对 15 个 checkpoint 文件之后，才在 before_run(look_ahead) 中检查（pilot.py:1204、393–400、402–417）。
- CI3 的处理写“RUNBOOK 第 3.8 节按代码的实际顺序写”，与此不符。
- CI6 写“RUNBOOK…要求…只用一个克隆”，但 RUNBOOK 没有这句明文，只有第 108 行的“本克隆” | RUNBOOK:106 “设备检查(ST8、ST9);核对 15 个 checkpoint 文件…;按整个 TEST 评测做 ST7 的事前判断” | 改为“设备检查（ST8）→ 核对 checkpoint 文件 → ST9 与 ST7（整个 TEST 评测的事前判断）”；在 3.1 写明“整个 Pilot 只用这一个克隆”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:116、144 | 【已验证，读代码】实验记录的文件名与说明不准确：
- 第 1 步之前停止的 formal 写的是 `<work>/experiment_record_formal_<开始时间>.json` 与 .txt，不是 `<work>/experiment_record_formal.json`。
- 第 144 行的 `experiment_record_<command>.json/.txt` 漏了开始时间。
- 第 116 行先说“任何停止都由 run_pilot 写出实验记录”，随后又列出不写记录的拒绝，前后矛盾。
- 括号中列出的「第 1 步之前的停止」漏了连续性检查与第 1 步开始时的 ST12/ST13；报告待决第 1 项是列了的 | pilot.py:964–967 `name = "experiment_record_%s_%s.json" % (command, p.started)`；pilot.py:1060–1063 | 统一文件名；第一句改为“除下列情形外，任何停止都写实验记录”；补全括号中的列举

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:98；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/pilot.py:1131–1137 | 【已验证，读代码】两处与实验记录有关的缺口：
- (a) 两份 L6 计数不同时，手册只写“不评测 TEST”。它没有写由谁、在何时比较两份计数，也没有写是否仍提交计数文件并运行 test-evaluate，让 begin 判 ST10 并写出 BLOCKED 记录。若 Executor 直接停下，这次 ST10 停止没有协议第 10 节的实验记录。
- (b) test-generate 成功时不写实验记录，只在 ST10 超限时写。协议第 10 节“每次运行（含被停止的）提交一份”是否涵盖这种情况，与待决第 1 项是同一类问题，但待决第 1 项没有列出它 | `if over: ... final_record(p, "test-generate", "BLOCKED", ...)` | 写明比较方法：用 test_generate.log 中 “L6 TEST count (Executor)” 一行对照计数文件；写明不一致时的操作；把 (b) 并入待决第 1 项

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:108；/home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:66 | 【已核对】裁决要求 RUNBOOK 写明「begin 到 finish 之间任何人不得推送本分支」。手册写的是“从 begin 到 finish 之间,任何人不得向 `metrix-e1-pilot-protocol-v1` 推送”，意思相同，但不是原句；报告却说“写明这句话” | — | 照录原句（可在后面补上分支名），或把报告改为“写明了这一要求”

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:59、19 | 【已核对】依赖与 Python 安装：
- (a) `pip install --upgrade pip` 安装的 pip 版本不在锁定文件中，与 Task Order 第 8 节第 1 项“只用 requirements.lock”字面不符。
- (b) 手册只给了 `python3.13 --version` 的检查，没有说主机没有 CPython 3.13.18 时怎么办 | “~/metrix-venv/bin/python -m pip install --upgrade pip” | 锁定 pip 版本或写明理由；补上安装指定 Python 版本的方法，或写明主机须预装、否则停下报告

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:76、86、103 | 【未验证，推理】formal、test-generate、test-evaluate 都以前台 `| tee` 运行，手册没有要求在 tmux / screen / nohup 中运行。SSH 断开时进程收到 SIGHUP；Python 默认不处理该信号，进程直接结束，不会进入 run_test_evaluate 的 BaseException 分支。若发生在 begin 之后，TEST 视为已评，而且没有实验记录。这不涉及评两次，属防范对象之外 | pilot.py:1300–1308 只处理 Python 异常 | 写明长命令在 tmux / screen 中运行，并在 3.8 再次提醒

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:17；/home/user/OpenMythos/metrix/e1-pilot/tasks/IMPL_C_OWNER_MESSAGE.md:23 | 【已核对】补充裁决 6 要求“RUNBOOK 规定只租 nvidia-smi 显示 CUDA ≥ 13.0（驱动 ≥ 580）的机器，并写明租用前的检查命令”。手册只把它写成环境要求表中的一项，没有“只租”“租用前”的表述 | “主机驱动须支持 CUDA 13.0:`nvidia-smi` 右上角的 “CUDA Version” ≥ 13.0” | 在第 1 节开头写明：只租这样的机器；租用前（或开机后第一条命令）用 nvidia-smi 核对，不满足即退租并报告 Owner

MINOR | /home/user/OpenMythos/metrix/e1-pilot/RUNBOOK_A100.md:145 | 【未验证，推理】日志可能带出 TEST 内容：
- test_generate.log、test_evaluate.log 在 finish 之后入库，手册没有要求提交前确认其中不含 TEST 内容（异常信息或回溯可能带出行内容）。
- test_data 还把 leakage_test_report.json 写到 `<work>/test/`，其注释写明 “L4 details may quote TEST”；手册没有提到这个文件，也没有说它不得提交 | test_data.py:184–185 | 写明提交日志前检查不含 TEST 文字；写明 `<work>/test/` 下的所有文件都不提交

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:237；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c3_01_final_checks.txt:16、115、106–111 | 【已验证】报告称 c3_01 是“C3 提交被审暂存树上的最终检查”，但不准确：
- c3_01 记录的写树是 65b95aca，送审树是 d27b68da。
- 录制期间 RUNBOOK 与报告在工作区被修改，末尾 git status 为 AM / MM。
- 报告没有写出这一点，只在调用文字中说明了。
- 代码不受影响：送审树中各代码文件的 blob 与 reviews/a0e04d1f…/tree.txt 相同 | c3_01:16 `65b95aca0f17bb12c6d1d976ee1c35c73cb8614a`；c3_01:106 `AM metrix/e1-pilot/RUNBOOK_A100.md` | 在报告 C3 节写明：录制时的写树；录制之后只改了文档；代码与 a0e04d1f 相同的依据

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:238；/home/user/OpenMythos/metrix/e1-pilot/reports/impl_c/c3_hf_tree_70d244cc.txt:1–4 | 【已核对】两处证据缺少原始录制：
- (a) “前 7 项…相同（Executor 逐个 grep 核对）”没有入库的原始输出（metrix/CLAUDE.md 第 9 节：自检勾选不算证据）。我逐项读 DATA_MANIFEST.json 核对过，7 项都相同。
- (b) c3_hf_tree 不是用 logrun.sh 录制的。首行说 04:00:46 获取，又说 JSON 是约 02:09 获取的、“unchanged”；`# parsed` 一段的生成命令没有记录 | — | 用 logrun.sh 录一次哈希比对与 HF API 请求（含解析命令），替换现有文件或补充说明

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:256 | 【已核对】验收第 6 项的范围与依据不完整：
- 只列了阶段 C 的提交；Task Order 第 11 节第 6 项是“每个工作提交”，阶段 A、B 的工作提交应引用各自报告中的审查记录。
- 没有提到 1435a74：第一次阶段 C 尝试中误入代码，已向前撤回并获追认（IMPL_C_REPORT.md:6、37）。
- C3 提交的 PASS 是在审查之前写的 | “阶段 C 的代码提交 `ae60e0f7`、…,C3 提交(只改文档):code-reviewer 均 PASS” | 引用 IMPL_A、IMPL_B 报告中的审查记录；注明 1435a74 的处理

MINOR | /home/user/OpenMythos/metrix/e1-pilot/reports/IMPL_C_REPORT.md:264 | 【已核对】“不阻碍 IMPLEMENTATION_READY”是 Executor 自己的判断。待决第 1、3、4、7 项的裁决若与现行代码不同，就要改代码并重新验收 | “租卡之前请 Review Gate 决定的事项(不阻碍 IMPLEMENTATION_READY,…)” | 改为“Executor 认为不阻碍…，请 Review Gate 确认；若裁决要求改代码，状态退回 C2”

结论：BLOCK
