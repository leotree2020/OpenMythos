# code-reviewer, round 1 (the only round, ruling item 4), C5 documentation commit (staged tree 8e86167ca30dda8fc059585a2025036856bd3d20, parent 377bc736e32f19ec003813db8a431da25ef9f660; committed as 1660ff7341fee8a18cfa888a253c6a07d0025eb5)
# Extracted unchanged from the transcript by reports/round6/review_extract.py
---
# code-reviewer 第 1 轮（唯一一轮）：C5 文档提交
审查对象：暂存树 8e86167ca30dda8fc059585a2025036856bd3d20，父提交 377bc736e32f19ec003813db8a431da25ef9f660，仓库 /home/user/OpenMythos

## 方法
- 先读了仓库中的 .claude/agents/code-reviewer.md，以它为定义。tools 行是 Read, Grep, Glob。
- 只用了 Read、Grep、Glob，没有运行 git、shell、tmux 或 python。下文的"已验证"指读过文件，或引用了将入库的录制（写明路径与行号）。"未验证"指只靠推理。
- 读过的内容：
  - input_round1.diff 全文；tree_round1.txt。
  - 工作区 RUNBOOK_A100.md 全文（与 diff 的新增行逐段一致）。
  - DEFERRED_MINORS.md 1.39 各行；tasks/IMPL_C5_RULING.md。
  - reviews/6726bac0…/code-reviewer_round3.md（C4D3-CR 原文）。
  - 源码：pilot.py:205-254、1015-1084、1255-1321；_cli.py 全文；run_pilot.py 全文；compute.py:110-152；testgate.py:92-93；record.py:32；以及 data.py、train.py、pilot.py 中 hf_hub_download 与 snapshot_download 的调用。
- 暂存内容核对（已验证）：diff 各文件 index 行的新 blob 与 c5_02_docs_checks.txt:805-814 逐一相同（fc29a12、08d58ef、4f4fa40、1d52b29、c2913d7、0d7ef93、62056c5、7000694、59f61f0、f0a75e4）。c5_02 自身的 blob ad4afdb 只能出现在 diff 中，这是构造决定的。src/、tests/、run_pilot.py 与 HEAD 相同（c5_02:791-792、887-888）。

## (1) 逐条核对
- **CL2：已修且正确（已验证）。**
  - 改动位置：RUNBOOK:26、69、72、77-78、109-111。
  - c5_01:519-527 的录制：venv 建在 $VENV；$VENV.tmp 安装期间最大 2752668 KiB，结束后 4 KiB；该时刻 HOME 下没有 .cache。
  - 措辞残留见问题 6、12。
- **CL3：已修，但有问题。**
  - 与代码一致（已验证）：
    - Pilot() 中的 --work 检查、ST12、set_determinism 都在 p.started 赋值之前（pilot.py:224-234）。
    - 实验记录名为 experiment_record_<command>_<p.started>，时间格式与 `date -u +%Y%m%dT%H%M%SZ` 相同（pilot.py:234、973）。
  - 问题见 1、2、11。
- **CL4：已修，但有问题。**
  - 路径正确：metrix/e1-pilot/results/test_evaluation_marker.json 与 test_evaluation_result.json（testgate.py:92-93；record.py:32）。
  - 动作与处理列相同（已验证）。
  - 问题见 3、2。
- **CL5：已修且正确（已验证）。**
  - RUNBOOK:160 与 :252 已列入转录。
  - 现有目录为 reviews/*/data-auditor_round1_transcript.jsonl，符合 `*_transcript.jsonl`。
- **CL6：内容已修且正确（已验证）。**
  - run_gate 只捕获 Exception（pilot.py:1035）。KeyboardInterrupt 只经过 finally 中的 close_clock，不到 final_record（pilot.py:1039-1041）。
  - 问题见 2、10。
- **CP1：已修且正确（已验证）。**
  - 改动位置：RUNBOOK:40、89-123、142-145、191-194。
  - c5_01:500-539 用 RUNBOOK 中的 send 一行实际发送了 s3_2a、s3_2、s3_4_data、s3_4_config，四个 .end 都是 exit=0。两项核对见 c5_01:513-515、524。
  - c5_02:830-840：8 条标注都在，第 1 节列表与之相符。
- **CP2：已修且正确（已验证）。**
  - RUNBOOK:135、250 已改。
  - git check-ignore 无输出，退出码 1（c5_01:549-550）。
  - 旧占位符 `<名称>` 已不存在（c5_02:826-827）。
- **CP3：已修且正确（已验证）。** RUNBOOK:40 与处理列的文字逐字相同，另加“重发用新窗口名”。
- **CP4：已修且正确（已验证）。**
  - GpuClock 的构造参数 now 被 used() 使用（compute.py:116-118、144-147）。
  - c5_01:546 的值：111.10839796066284 = 10 + (1795793024.5473979 − 1795792923.439)。
  - 小问题见 9。
- **CP5：措辞已同步（已验证）。**
  - RUNBOOK:25、79-80、90-93；c5_02:847-850。
  - 这条分支本身没有运行过（报告已写明）。实际可达性见问题 7。
- **总则：已落实（已验证）。**
  - 原文恰好出现一次，位于第 4 节开头（RUNBOOK:209；c5_02:822-823，56 个字符，出现 1 次）。
  - 其后 Executor 加的一句见问题 4、5。

## (2) 防范对象（静态推演，未验证）
没有找到“按 RUNBOOK 操作会评测 TEST 两次，或在 ST10 不成立时评测 TEST”的新路径。
- 3.7 第 4 项没有改：两份计数不同即不运行 3.8。
- 新文字只放宽了一处：CP3 允许“写出标记之前的拒绝由 Owner 决定是否重发”。代码在这一点上兜底：工作区或 HEAD 中有结果即 TestAlreadyEvaluated，有标记即 BLOCKED（pilot.py:1261-1272）；begin 在 fetch 之后还会复核。
- 3.8 新段落中，有标记、没有标记两个分支都是“不重跑，报告 Owner”。
- 3.6、3.8 的 `git pull --ff-only` 改为前台运行、成功后再发送，偏向安全。
- 下列问题都在防范对象之外。

## (3) c5_01 是否检验了 RUNBOOK 中的命令（已验证，逐行比对文字）
- 录制中的命令与 RUNBOOK 逐行对应：

| c5_01 | RUNBOOK |
|---|---|
| :463-469 | :71-77（占位符已替换） |
| :485、487 | :85、87 |
| :497-498 | :40 |
| :502-510 | :95-103 |
| :519-521 | :109-111 |
| :531 | :119 |
| :537 | :121 |
| :542 | :187 |

- 我无法计算 c5_01:459 的 RUNBOOK sha256 与 blob fc29a124 是否对应；但文字一致，trial1 与 c5_02 中 RUNBOOK 的 blob 也相同。
- 没有检验的部分（报告已写明大部分）：
  - 3.3、s3_4_model、formal、test-generate、test-evaluate；
  - uv 分支，以及“有 3.13.18 但缺 ensurepip”的分支；
  - 多行脚本中途失败时 .end 的值；
  - CL3、CL4、CL6 所述的回溯与 Ctrl-C 行为。
- tmux 服务器从模拟脚本的 shell 继承环境，报告已写明。即便容器环境中有 PIP_*、TMPDIR 等变量，结论也成立：命令里显式写了 `--no-cache-dir` 和 `TMPDIR=`。

## (4) 报告与 DEFERRED_MINORS 是否如实（已验证，读文件）
- 1.38、1.39、1.42 各行“已修(C5 文档提交)”的说法与 RUNBOOK 的改动相符。
- 1.39 首段所列 CM4、CM5、CM6、CM8、CM10 的处理列确实写着“下一个代码提交”（DEFERRED_MINORS.md:723-729）。
- 报告逐字照录了裁决 1–5 项。
- 检查表中的数值与 c5_01、c5_02 相符：2.6 GiB、180 次取样、4 KiB、4.8G、15.5、111.108。
- trial1 的说法与 c5_02_docs_checks_trial1_script_error.txt:964-968 相符（R 为空，计数 275）。trial1.sh 的 blob 7000694 与 trial1 录制中当时的脚本相同。
- 不准确之处见问题 8。

## 问题

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:133 | 【已验证，读文件】CL3 加了第三种情况后，引导句仍写“分两种”，后面实际有三条 | :133 “命令输出的处理分两种:”，其后 :135、:136、:137 三条 | 改为“分三种”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:137、:203、:216（对照 pilot.py:220、1309-1318） | 【未验证：tty 信号与管道行为是推理】在 tmux 窗口中按 Ctrl-C，SIGINT 会发给前台进程组中的所有进程，包括 `| tee`。tee 先退出，带来三个后果。(a) 输出文件中可能没有 Traceback 和 `RESULT: FAIL`，与 :137 认出第三种情况的条件不符，而 :137 恰把“formal 被 Ctrl-C 结束”列为例子；:216 只说 SIGHUP 时可能没有回溯。(b) 交互 shell 中 `bash x.sh; echo exit=$? >> …end` 的后半句可能不执行，.end 不出现。(c) test-evaluate 写出标记之后被 Ctrl-C：except 块中的 p.log 是写 stdout 的 print，管道已断会抛 BrokenPipeError，在 final_record 之前就退出，所以 :203 与第 4 节所说的“先写并提交 BLOCKED 实验记录”可能不成立。处理上仍然安全：.end 不存在按“状态不明”处理，总则要求报告 Owner；标记已推送，代码会拒绝第二次运行 | :137 “或 formal 被 Ctrl-C 结束(第 4 节)”；:203 “本进程写出标记之后崩溃或被 Ctrl-C 结束(先写并提交 BLOCKED 实验记录,再抛出)”；pilot.py:220 `print(..., flush=True)` | 在 :137、:203、:216 补一句：在窗口中 Ctrl-C 时输出文件可能被截断、.end 可能不出现、BLOCKED 记录可能缺失，按 .end 不存在与总则处理。登记即可

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:203（对照 pilot.py:224-233、1309-1312） | 【已验证，读代码】“以回溯结束……有三种情况”列得不全。还有两种：(a) 本进程写出标记之前的崩溃或中断，代码 `if not begun_by_this_process(p): raise`，没有记录，TEST 未评；(b) Pilot() 中的 ST12、确定性设置失败、--work 在仓库内。两者都以 Traceback 加 `RESULT: FAIL` 结束（_cli.py:24-29）。本段的动作（看有没有标记或结果；都没有也不重跑、报告 Owner）已覆盖这两种，所以只是措辞不全 | :203 “有三种情况:TestAlreadyEvaluated…;本进程写出标记之后崩溃或被 Ctrl-C 结束…;finish 已推送结果,但实验记录的提交失败” | 改为“至少有以下情况”，或补上 (a)(b)

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:209（对照 :250、:126、:194） | 【已验证，读文件】按总则字面，“非 0 退出码 → 不重跑、报告 Owner”。但第 5 节要求 `git check-ignore -v` 以退出码 1 为通过；formal 在 Gate 0 不是 PASS 时、test-evaluate 在 HYPOTHESIS_FAIL 时也以 1 退出，这是正常结束。Executor 加的一句（“已写明的其余处理……照做”）可以覆盖这些，但所举例子里没有 check-ignore | :250 “git check-ignore -v <这些路径> 应无输出、退出码为 1” | 在总则后的说明中写明：本手册写明以非 0 为预期的命令（第 5 节 check-ignore）不适用总则；formal 或 test-evaluate 的 RESULT: FAIL 照常报告

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:209 | 【已验证，读文件】Executor 加的一句把裁决原文“保留输出”收窄为“不删除、不改动 <work>/command_output/ 中的文件”。下列输出不在这个定义内：工作区 results/ 中未提交的记录、本地未推送的提交（含 ST10 记录、TEST 标记）、<work>/experiment_record_formal_*、<work>/test/。其中一部分另有条文保护：第 4 节“本地留下的提交……只在 Owner 决定后推送”，以及总则的“不修补”。按规则办事时不会因此删除标记，所以在防范对象之外。报告“待决(C5)”第 2 项只提请注意“提交输出”，没有提到这一收窄 | :209 “‘保留输出’指不删除、不改动 `<work>/command_output/` 中的文件” | 改为“不删除、不改动 <work> 与工作区中的任何输出（含未推送的提交）”，或在报告待决第 2 项中一并提请 Review Gate 注意

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:63（对照 :38、:99、:109） | 【已验证，读文件】“env.txt……每段以 date -u 开头”并不处处成立。:38 Claude Code 启动后的核对追加到 env.txt，没有规定 date -u；:99 uv 分支的 `{ ~/uv-tool/bin/uv --version; …} | tee -a "$E"` 和 :109 的 `"$PY313" -m venv "$VENV" 2>&1 | tee -a "$E"` 都不以 date -u 开头 | :109 `"$PY313" -m venv "$VENV" 2>&1 \| tee -a "$E"` | 在这三处的分组前加 `date -u;`，或把 :63 改为“各条命令的分组以 date -u 开头”。只改文档即可

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:98、:105-106（另见 :25、:79、:90） | 【未验证：推理；c5_01 没有运行这条分支】裁决第 3 项确认：有 3.13.18 但缺 ensurepip 时用 uv。但 uv 的引导步骤 `python3 -m venv ~/uv-tool` 本身也需要系统 python3 带 ensurepip。缺 ensurepip 的常见原因（Debian/Ubuntu 没装 pythonX-venv）通常同样作用于 python3，于是这条分支多半在第一步失败，按 :105-106 停下报告。结果是安全的（停下），但裁决要求的“同样用 uv 安装”在常见情形下可能做不到 | :98 `python3 -m venv ~/uv-tool && ~/uv-tool/bin/python -m pip install uv==0.13.10` | 登记，请 Review Gate 知悉。正式运行前若要可达，需要另定不依赖 venv 的 uv 安装方式（属于新的命令，须裁决）

MINOR | metrix/e1-pilot/reports/IMPL_C_REPORT.md:372、:425 | 【已验证，读文件】(a) :372 的“/usr/local/bin/python3.13，有 ensurepip”标注出处为 c5_00，但 c5_00 只记了 “Python 3.13.18”（c5_00:11）。路径在 c5_01:460；有 ensurepip 只能从 c5_01:513-515 走了主机分支间接推出。(b) :425 说 send 一行的两个前提“在第 1 节与第 3.0 节写明”，但 3.0（RUNBOOK:69）只写了“目录路径不含空格”，`$?` 一项只在第 1 节（:40） | :372 “(`/usr/local/bin/python3.13`,有 ensurepip)(`impl_c/c5_00_session_start.txt`)” | 登记于其后的证据提交：(a) 出处补 c5_01:460、513-515；(b) 改为“第 1 节写明两项，第 3.0 节写明前一项”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:187 | 【已验证，读 compute.py:120-147 与 c5_01:541-547】(a) 第二个值 open 打印的是 Unix 秒，记录中要写“含自 <open> 起”，而 t 同时给出了 UTC，两者格式不一致。(b) gpu_clock.json 被读两次（used() 一次，json.load 一次）；3.7 时没有进程在写，结果不受影响。(c) 文件不存在时，旧写法 `_state()` 返回默认值，新写法 json.load 抛 FileNotFoundError；3.7 时文件必然存在（formal 已用过 GPU） | `print(GpuClock(p, now=lambda: t).used(), json.load(open(p, encoding='utf-8'))['open'], t, …)` | 登记。日后可让 open 也打印 UTC，或在记录模板中写明 <open> 为 Unix 秒

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:213、:216 | 【已验证，读文件】CL6 这一条放在“例外(现行实现;C4 裁决第 2 项接受)”之下，但它的依据是 C5 裁决第 2 项（条内已写明），与标题的出处不一致 | :213 “例外(现行实现;C4 裁决第 2 项接受):”；:216 “(现行实现;按 DEFERRED_MINORS.md 1.38 CL6 写入,C5 裁决第 2 项)” | 标题改为“例外(现行实现;C4 裁决第 2 项接受,CL6 一条见 C5 裁决第 2 项)”。登记即可

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:135、:137（对照 pilot.py:1075-1083） | 【已验证，读代码】边缘情况：formal 在第 1 步之后崩溃，final_record 写出了实验记录但提交失败（ProtocolStop 被捕获，stop 不为 None，不再抛出）。记录留在工作区 results/ 中、没有提交：不符合第一种情况的“并已提交”，也不符合第三种情况的“没有本次的实验记录”。按总则会停下报告，结果安全 | pilot.py:1080-1083 `except ProtocolStop as e: … if stop is None: raise` | 登记；或在第三种情况的条件中写“results/ 中没有本次已提交的实验记录”

MINOR | metrix/e1-pilot/RUNBOOK_A100.md:26 | 【部分已验证：读文件，以及模拟后会话临时目录 c5sim/home 的内容（未入库）；部分未验证】“家目录只放变量文件，以及 uv 与解释器”说得过满。(a) uv 分支的 `~/uv-tool/bin/python -m pip install uv==0.13.10`（:98）没有 --no-cache-dir，pip 缓存写在家目录（体积小）。(b) 模拟结束后，scratch HOME 下有 .cache/huggingface/xet/logs/…，是 s3_4 下载产生的日志。(c) 在 A100 上下载 4 GB 权重时，xet 是否在 ~/.cache/huggingface/xet 中建 chunk cache，未验证 | :26 “家目录只放变量文件,以及 3.2a 走 uv 分支时的 uv 与它装的解释器” | 改为“家目录只放少量文件（变量文件、uv 分支的 uv 与解释器、日志）”。正式运行时 env.txt 可加一次 `du -sh ~`

本轮没有 BLOCKER，也没有 MAJOR。12 条都是 MINOR，都在防范对象之外，按裁决第 4 项登记即可。

结论：PASS
