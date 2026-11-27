# code-reviewer, round 1, C4 documentation commit (staged tree 7501c29199a38c26ae238f1e9c4b372d0e71a0cc, parent c9481c85ed30e2615be86e86559f5107f114dd5b)
# Extracted unchanged from the transcript by reports/round6/review_extract.py
---
code-reviewer 审查：C4 文档提交，第 1 轮。审查对象是暂存树 7501c29199a38c26ae238f1e9c4b372d0e71a0cc，父提交 c9481c85ed30e2615be86e86559f5107f114dd5b，仓库 /home/user/OpenMythos。

## 方法
- 先读了仓库中的 .claude/agents/code-reviewer.md，以它为定义。tools 行是 Read, Grep, Glob，与我实际可用的工具一致。
- 只用了 Read、Grep、Glob，没有运行 git、shell、tmux、uv 或任何代码。
- 读过的输入：
  - review_c4d/input_round1.diff 与 tree_round1.txt（后者只有树哈希）。
  - 工作区的 RUNBOOK_A100.md，与 diff 新增行逐行一致。
  - IMPL_C_REPORT.md、DEFERRED_MINORS.md。
  - tasks/IMPL_C4_RULING.md、IMPL_C1_RULING.md、IMPL_C2_OWNER_MESSAGE.md。
  - 协议第 8、10、11 节。
  - 源码：pilot.py、testgate.py、stops.py、record.py。
  - 审查原文：reviews/a09e154e…/ 两份第 1 轮原文，reviews/6dc572f5…/code-reviewer_round3.md。
- 「已验证」表示引用了仓库文件或已提交的录制，并写明行号；「未验证」表示推理得出，没有运行。

## 一、裁决第 1、3–7 项的落实，以及与代码是否一致（已验证，读文件）
- **第 1 项**：已落实。
  - RUNBOOK:182、205、241、245 都写成 ST11 读 `st11_estimate_hours` = `b17_estimate_hours` + `checkpoint_overhead.seconds`/3600，超过 3.5 小时即停。
  - 与代码一致：pilot.py:191-195、593、645-655；stops.py:133 是严格大于。
  - ST7 写明“不变”，TEST 的事前估计写明“不加余量”，与 pilot.py:198-209、345-362 一致。
  - 时长表按文中区间重算：1.16–2.95 + 0.43–1.29 ≈ 1.6–4.2 小时，正确。
- **第 3 项**：已落实，RUNBOOK:9。
- **第 4 项**：已落实，RUNBOOK:11、224。手写记录也按证据提交，依据是第 5 项。
- **第 5 项**：已落实，RUNBOOK:138-164、187、204、223。
  - 模板 20 个字段与协议第 580-605 行同名同序，录制见 c4_05:441-443。
  - 实验 ID 的格式与 pilot.py:234、963-964 一致。
- **第 6 项**：已落实，RUNBOOK:25、28、72-73、82-90。
- **第 7 项**：
  - 已删去“待 Review Gate 决定”与“待决”：我 grep 了一遍，只剩第 190 行“由 Review Gate 决定如何处理”，这是事后处理的分工，不是待决措辞；另见 c4_05:436-438。
  - 时长表已改为读两者之和。
  - 已新增 Claude Code 一节（RUNBOOK:34-38）。
  - 仓库中只有两个 agent 文件，outside_metrix_check 显示它们已被跟踪（c4_05:453-454），克隆后可以加载。

## 二、新写的命令与操作；防范对象
- **防范对象内**：没有找到按 RUNBOOK 操作会评测 TEST 两次，或在 ST10 不成立时评测 TEST 的路径（静态推演，未验证）。
  - 两份 L6 计数不同时，即使误运行 test-evaluate，begin 也会在写标记之前判 ST10 并停止：testgate.py:443 调用 st10_check，stops.py:126-128 比较两份计数，写标记在 testgate.py:461。
  - 误发第二个 test-evaluate 时，第二个进程会被拒绝：pilot.py:1261-1272、1275-1278，testgate.py:440、464-466。
  - 手写记录的文件名与 run_pilot 的文件名不冲突（pilot.py:973）。.gitignore 中没有规则会忽略它。
- **防范对象外**：tmux / Claude Code 的执行方式写得不够，照做可能失败，见问题 1–3、7。

## 三、报告与 DEFERRED_MINORS 是否如实（已验证）
- IMPL_C_REPORT:77-95 逐字照录了裁决第 1–7 项，与 IMPL_C4_RULING.md:4-10 相同。
- 1.39 的 CM1–CM11 与两份原文逐条对应，没有遗漏，也没有改变结论：
  - code-reviewer 原文 10 条 MINOR（code-reviewer_round1.md:131-149）；
  - data-auditor 原文 3 条 MINOR 加 1 条说明（data-auditor_round1.md:159-162）。
- 两份审查的结论都照实写为 PASS。
- CM2 的说法属实：调用文字写明了新字段名（data-auditor_prompt.txt:33），ic11_04、ic11_08 两个脚本存在。
- 推送记录 c4_push_code_commit.txt:7-16 与报告所述一致。
- 有两处措辞问题，见问题 11、12。

## 四、上一轮问题 1：已修（已验证）
- 旧字段名、“只报告；C2 待决第 2 项”“若 Review Gate 决定”都已删除。
- 现在的写法见 RUNBOOK:182、205、241、245；另见 c4_05:436-438。

## 五、问题

MAJOR | metrix/e1-pilot/RUNBOOK_A100.md:36-38（另见 :66-70、82-94、105、169） | 【未验证：tmux 与 Claude Code Bash 工具的行为都是推理，不确定】按 RUNBOOK 的 Claude Code / tmux 方式照做，命令可能拿不到 shell 变量。(a) `E`、`PY`、`PY313`、`UV` 都没有 export；`WORK`、`INPUTS` 是在 `tmux new -s metrix`（:66）之后才 export 的（:68），不在 tmux 的全局环境里。用 `tmux new-window` 新开的窗口通常不继承这些变量，而例子把命令放在单引号里送入新窗口，由新窗口的 shell 展开，于是 `$PY`、`$INPUTS`、`$WORK` 可能为空，命令失败。(b) Claude Code 的 Bash 工具在两次调用之间可能不保留 shell 变量（这点我不确定），这样 3.2a 起的 `$UV`、`$PY313`、`$PY`、`$E` 在下一条命令中为空，`tee -a ""` 会出错，env.txt 也就漏记。失败都发生在写标记之前（`--work` 在仓库内、连续性检查、没有 python），所以在防范对象之外，不影响 TEST 闸门。但 :9 禁止在租用机器上调试，照做就只能停下报告，白耗租用时间 | :38 `tmux new-window -d -n formal`,再 `tmux send-keys -t metrix:formal '<第 3.5 节的命令>' Enter`；:70 `E="$WORK/command_output/env.txt"`（未 export）；:93 `PY=~/metrix-venv/bin/python` | 写明变量怎样传递。例如：启动 Claude Code 之前 export WORK、INPUTS、E；3.2 之后把 `PY=…` 等写入 `$WORK/command_output/vars.sh`，每条命令与每个 tmux 窗口先 `source` 它；或在 send-keys 中使用展开后的绝对路径，并给 new-window 加 `-c "$PWD"`（tmux ≥3.0 也可以用 `-e`）

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:38 | 【已验证代码；RUNBOOK 部分为推理】没有写长命令只发送一次，以及重发前怎样确认它没有在运行（Claude Code 超时或重启之后尤其需要）。代码已经能阻止第二次评测（pilot.py:1261-1278；testgate.py:440、464-466）。剩下的是边缘情形：两个进程几乎同时到达 begin 时，第二个进程可能在 begin 与 finish 之间提交并推送一份 BLOCKED 记录，使唯一的一次评测成为 BLOCKED | `tmux send-keys -t metrix:formal '<第 3.5 节的命令>' Enter` | 补一句：每个长命令只发送一次；重发前先 `tmux list-windows -t metrix`、`pgrep -af run_pilot.py` 确认没有在运行；test-evaluate 的窗口名唯一

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:38 | 【未验证】长命令只列了 formal、test-generate、test-evaluate。3.2 的 pip 安装（torch 加 CUDA 13 的 wheel，数 GB）、3.4 的 fetch-model（4.1 GB）、3.2a 的 `uv python install` 也可能超过 Bash 工具的超时而被中断；中断后按 :9 只能停下 | :38 “`formal`、`test-generate`、`test-evaluate` 这些长命令不作为有超时的前台命令运行” | 把这几步列入，或写明“可能超过工具超时的命令都在 tmux 窗口中运行”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:82-90 | 【已验证，读文件】3.2a 只靠注释说明“仅当没有 3.13.18 时”执行，代码块中是无条件的。整段照做时，已有 3.13.18 的主机也会执行 uv 的几步；若缺少 venv 模块，还会无谓地停下 | :82 `PY313=python3.13  # … 否则先做下面的 3.2a` 之后紧接 :87-90 | 把 3.2a 拆成单独的代码块，或加 `if [ "$(python3.13 --version 2>&1)" != "Python 3.13.18" ]; then … fi`

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:84-87 | 【c4_04 部分已验证；其余为推理】uv 不锁版本，也不核对哈希。c4_04 核对的是 uv 0.13.10（c4_04_uv_check.txt:380），A100 上装到的版本可能不同：`--managed-python` 参数可能被改名，取到的 python-build-standalone 构建也可能不同。另外，`python3 -m venv` 在缺少 venv 模块的主机上（例如没有装 python3-venv 的 Debian / Ubuntu）会失败，按 :83 只能停下 | :87 `~/uv-tool/bin/python -m pip install uv` | 改为 `pip install uv==0.13.10`；把 `$PY313 -c 'import sys; print(sys.version)'`（含构建日期）也写入 env.txt；缺少 venv 模块时的处理写明，或明确接受停下

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:28；reports/impl_c/c4_04_uv_check.txt:365-403 | 【未验证】c4_04 没有记录容器中的 UV_* 环境变量，只看到 UV_NATIVE_TLS（:386）。所以无法确认 releases.astral.sh 是 uv 的默认下载地址，还是容器配置的镜像。若 A100 上显示的是 github.com 的地址，下载会重定向到 GitHub 的发布文件主机，而网络一行没有列它 | :28 “只在 3.2a 时:releases.astral.sh” | 核对时加 `env | grep ^UV_`；RUNBOOK 写明以 `--show-urls` 显示的主机及其重定向目标为准

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:34-37 | 【已验证，读文件】在 A100 上运行 Claude Code 的前提写得不全：(a) Claude Code 的安装、登录，以及它访问 Anthropic 服务所需的网络都没有列出，第 1 节网络一行也没有；(b) 没有写 Claude Code 启动前由谁执行 3.0–3.1；(c) “先在普通 shell 中做第 3.0 节……(含 `tmux new -s metrix`)”与 :66 “之后的命令都在这个 tmux 会话中运行”不一致 | :36 “先在普通 shell 中做第 3.0 节的驱动检查(含 `tmux new -s metrix`)” | 在第 1 节补一行 Claude Code 的安装、认证与网络要求；写明执行 3.0–3.1 的人；把措辞改为“tmux 会话中”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:182、245 | 【已验证】这几个字段在第 2 步记录中位于 `preflight` 之下（pilot.py:592、652-654；c4_smoke_records/step2_record.json:96-128），RUNBOOK 写的是“第 2 步记录中的 `st11_estimate_hours`”，没有写前缀 | :245 `ST11 读 \`st11_estimate_hours\`(= \`b17_estimate_hours\` + \`checkpoint_overhead.seconds\` / 3600` | 写成 `preflight.st11_estimate_hours`、`preflight.checkpoint_overhead.seconds`

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:182 | 【已验证】ST7 训练前的事前估计漏写了基座模型的加载；代码含 `load_s`（pilot.py:353-354）。原有措辞，本次只在其后加注“不变” | “每次训练前按“训练 + 保存、重载、哈希 + 一次 DEV 评测”” | 改为“加载 + 训练 + 两次 state_sha256、保存、文件哈希、重载 + 一次 DEV 评测”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:148、150 | 【已验证，读文件】手写记录有两处不足。(a) Compute accounting 只写“见 <work>/gpu_clock.json”，该文件在仓库外、不提交，而协议第 607 行要求 wall-clock 取实测值。(b) Input 字段没有写 split SHA | :150 “到此为止的累计 GPU wall-clock 见 <work>/gpu_clock.json” | 填入 gpu_clock.json 中的累计秒数；Input 字段补上 SPLIT_MANIFEST.json 的 split_sha256，或写明取自冻结提交

MINOR | metrix/e1-pilot/reports/DEFERRED_MINORS.md:724（CM5），另见 :720（CM1） | 【已验证】同一写法有两种含义。CM1 的“IC11-DA 2”指 data-auditor 列出的第 2 条 MINOR（RUNBOOK），CM5 的“IC11-DA 第 2 项”指它的第 2 节“静态核对”（data-auditor_round1.md:72-94），读者容易混淆。另外，1.38 表中 CL7 的处理列（:711）仍写“请 Review Gate 一并裁决”，只在第 3 节（:764）注明已经回答 | CM5 “(IC11-CR 第二节、IC11-DA 第 2 项)” | 改为“IC11-DA 第 2 节(静态核对)”；CL7 的处理列补“已由 C4 裁决第 4 项回答”

MINOR | metrix/e1-pilot/reports/IMPL_C_REPORT.md:303-304 | 【已验证】(a) 位置写得不准：剔除配置的那条注释在 `step7` 中（pilot.py:830-833），不在 `gate_steps` 的“第 6 步附近”；`gate_steps` 里的是 Gate 0 PASS 状态词那一条（pilot.py:1010-1011）。(b) 交付清单没有列出脚本 `impl_c/c4_docs_checks.sh` | :303 “(`gate_steps` 第 6 步附近、`run_gate`、`final_record` 等)” | 改为“`step7`(G0.2 对剔除配置的读法)、`gate_steps`(Gate 0 PASS 的状态词)、`run_gate`、`final_record`”；:304 补上 c4_docs_checks.sh

MINOR | metrix/e1-pilot/reports/impl_c/c4_05_docs_checks.txt:423-434、469-480 | 【stat 已验证；内容绑定未验证】c4_05 记下的写树 113da4bb 是暂存 c4_05 之前的树，只有 stat，没有五份文档的 blob。被审树 7501c291 与它的对应，只能靠 stat 行数相同来推断（input_round1.diff:1-7 与 c4_05:428-433 一致），不能证明内容相同 | c4_05:425 `113da4bb1506f7235fa98f870fb288187d7eade4` | 以后的文档检查加录 `git ls-files -s` 下各文档路径，或 `git diff --cached HEAD | sha256sum`

没有 BLOCKER。1 条 MAJOR 在防范对象之外，照做失败时发生在写标记之前，不影响 TEST 闸门；其不确定之处已在该条中写明。裁决第 1、3–7 项都已落实，RUNBOOK 与 C4 代码一致，上一轮问题 1 已修。

结论：PASS
