# code-reviewer final report, round 8, freeze commit 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa (parent 18076298); invoked 2026-11-22 06:05 UTC (background), interrupted by HTTP 429, resumed 08:53 UTC; invocation text: code-reviewer_prompt.txt; resume: resume_message_code-reviewer.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-a6a920b488ba65f8a.jsonl)
---
code-reviewer 第 8 轮审查:冻结提交 6a474e4a5defa23dfc71b2c6bca9e15a81b517aa(父提交 18076298)

本提交与第 8 轮指令第 1a–1e、2、3 项及补充 a–e 逐条一致,没有 BLOCKER,结论 PASS。另登记 6 条 MAJOR、6 条新 MINOR,按第 4 项只登记不修。其中第 1 条(ST12 与第 8 节第 1 步冲突)须在执行第 8 节第 1 步之前,由 Review Gate 裁决。

## 依据与边界
- 定义:按仓库文件 /home/user/OpenMythos/.claude/agents/code-reviewer.md 执行(本次运行开头已读;中断后协调方的续作消息又发了一次固定首句,文件未变)。tools 行为 `tools: Read, Grep, Glob`,与已加载定义相同(reviews/6a474e4a…/preflight_tools_check.txt:5–7)。
- 读过的材料:
  - /home/user/OpenMythos/metrix/e1-pilot/tasks/ROUND8_TASKS.md
  - /home/user/OpenMythos/metrix/e1-pilot/reviews/6a474e4a5defa23dfc71b2c6bca9e15a81b517aa/review_input.diff 与 delta_vs_92df1a60.diff
  - 工作区中的协议、三个 JSON、metrix/CLAUDE.md,以及 reports/round8/ 下四份原始输出
  - .git/logs/HEAD、.git/logs/refs/heads/metrix-e1-pilot-protocol-v1、.git/refs/heads/metrix-e1-pilot-protocol-v1(= 6a474e4a)、.git/refs/remotes/origin/metrix-e1-pilot-protocol-v1(= 18076298)
- 我没有运行任何命令。引用已提交原始输出或 .git 日志的判断标为“已验证”,只靠读文本对照的标为“未验证(文本对照)”。
- 已提交文件的字节是否等于 t1_protocol_checks.txt:38–44 中工作区的 sha256(协议 141473…、SPLIT_MANIFEST 7eb5d6…),我没有工具核对,交 data-auditor 复算。旁证:检查时 git status 为 `MM`(t1_protocol_checks.txt:9–13),但检查时 `git diff --stat HEAD` 的行数(t1_protocol_checks.txt:114–118)与提交的 stat(review_input.diff:24–28)逐项相同。
- delta_vs_92df1a60.diff:2–6 显示,与已审查的 92df1a60 相比,本提交只改了协议、SPLIT_MANIFEST.json、t1_protocol_checks.txt 和 ROUND8_TASKS.md。DATA_MANIFEST.json(94ba85…)、SEARCH_SPACE.json(490d57…)、metrix/CLAUDE.md(c253f7…)的 sha256 与 92df1a60 相同(delta_vs_92df1a60.diff:138–147)。
- Owner 对两个提问的回答(ROUND8_TASKS.md:43)我无法独立核实,只按该文件的记录对待。

## 逐条对照

- **1a:一致。已验证。**
  - DATA_MANIFEST.json:263、:282 新增 record 键。t1_protocol_checks.txt:59 打印了这两个字段。
  - 与协议 :139(train_S 每行 `{"fact_id","answer_fact_id","text"}`)和 :129(candidates.json 为 `{fact_id: [4 个候选]}`)一致。
  - 已记入第 14 节 :688。
- **1b:一致。未验证(文本对照);旧措辞已移除这一点已验证。**
  - 协议 :169 写明三点:只在每篇文档内取 13-gram,不跨篇;两边各自合并成集合后,计交集的种类数;文本为实际送入模型的 id 解码所得(锚文档 ≤128 个 id,窗口 ≤256 个 id)。
  - “不一致按 BLOCKED 处理并报告 Owner”出现在 :169、:174、:527、:574(第 9 节)、:621(ST10),以及 SPLIT_MANIFEST.json:374–377、:383。
  - 旧措辞在第 14 节以外为 0 处(t1_protocol_checks.txt:106,只命中第 14 节的 :689)。已记入 :689。
- **1c:一致。未验证(文本对照);旧措辞已移除这一点已验证。**
  - 协议 :211 为“删除 `<think>…</think>` 片段之后,先去掉开头的空白……再取第一行”。DATA_MANIFEST.json:39 的顺序相同。
  - 旧措辞只在第 14 节 :690(t1_protocol_checks.txt:107–108)。已记入 :690。
- **1d:一致。已验证。**
  - DATA_MANIFEST.json:19–25 写入 4 个分词器文件的 sha256,与 t0_env.txt:48–51、t1d_data_hashes.txt:71–74 逐字相同。
  - 固定 revision 的仓库树中只有这 4 个分词器文件(t0_env.txt:29–42)。
  - 只用这 4 个文件加载的分词器,与 6 文件目录在类、词表、编码、chat template(enable_thinking=False)、特殊 id 上都相同(t1d_data_hashes.txt:76–82)。
  - 锚文本哈希 8828bc4f…(DATA_MANIFEST.json:242–243)与 t1d_data_hashes.txt:13、:65 相同。
  - 已记入 :691。
- **1e:一致。未验证(文本对照)。**
  - metrix/CLAUDE.md:62 为“「永久」与「本阶段」的裁决可写入本文件,写入时须注明作用范围;「本阶段」的裁决在本阶段结束时失效”,并注明了出处、批准、时间和原因。
  - 已记入 :692。见下面问题 5。
- **2:一致。已验证。**
  - 三个 JSON 的 status 为 PROTOCOL_FROZEN,frozen 字段为“Owner 批准，2026-11-22 05:27 UTC”(全角逗号);re-dump 与文件逐字相同;内联副本逐字相同(t1_protocol_checks.txt:52–55)。
  - 训练契约表头在 :262,表中数值未改。第 13 节在 :637–640(320 条 fact、Pilot 后按 G0.10 重算;dNLL ≤ +0.03 在 Pilot 中只报告)。
  - 第 14 节以外残留的 PROPOSED/PENDING 只在说明句 :10、:635、:644(t1_protocol_checks.txt:73–91);我用不区分大小写的 Grep 复查,结果相同。
  - 出处字符串计数:协议 8,四个文件各 1(t1_protocol_checks.txt:93–98)。
  - 已记入 :693。
- **3:一致。未验证(文本对照)。**
  - 协议 :6 状态为 `**PROTOCOL_FROZEN**(Owner 批准，2026-11-22 05:27 UTC;…)`。已记入 :694。
- **补充 a:一致(字面)。部分已验证。**
  - 协议 :542 与 ROUND8_TASKS.md:31 逐字相同,只多了“复现:”前缀,并去掉了句末句号。
  - 旧文字只在第 14 节 :695(t1_protocol_checks.txt:110)。
  - 确定性设置与第 0 节 :43 一致。见问题 2、9。
- **补充 b:一致。已验证。**
  - 协议 :126 新增该条;第 9 节 :569 加入“或第 2.5 节干扰项的池少于 4 个答案”;SPLIT_MANIFEST.json:323 新增 pool_too_small。
  - DATA_SEED 下的 fact 文件 sha256 为 406c8801…;各 fact 的池为 learned 14 个、unread 4 个,池少于 4 的 fact 为 0 条(t1_protocol_checks.txt:66–70)。不触发,候选哈希不变。
- **补充 c:一致。部分已验证。**
  - 协议 :544 包含三个分位、“以最大者作为 E1-V1 规划依据”,以及原句“Pilot 的规模估计是规划估计,不是保证”。
  - 旧文字只在 :697(t1_protocol_checks.txt:111)。见问题 7。
- **补充 d:一致。未验证(文本对照)。**
  - 协议 :521(第 2 步,预检:A100、第一个配置的前 20 步、四项记录、超过 3.5 小时停止并报告 Owner)、:622(ST11)。见问题 3、8。
- **补充 e:一致(字面)。未验证(文本对照)。**
  - :623 ST12、:624 ST13 与 ROUND8_TASKS.md:35 一致;第 9 节 :574 BLOCKED 加 ST12,:569 IMPLEMENTATION_FAIL 加 ST13。见问题 1、6。
- **补充“全部记入第 14 节,注明「对照 Task Order V1.2 补齐」”:一致。已验证。**
  - :695–699 共 5 行,每行都含该字样(t1_protocol_checks.txt:99 计数为 5;我用 Grep 复核,v1-r8 行中含此字样的也是 5 行)。
- **同一提交:一致。已验证。**
  - .git/logs/refs/heads/metrix-e1-pilot-protocol-v1:3–4:由 92df1a60 reset 到 18076298,再一次 commit 得到 6a474e4a。分支 ref 为 6a474e4a。
  - review_input.diff:24–34 的 stat 含全部 5 个被改文件、ROUND8_TASKS.md 与 round8 原始输出;没有 metrix/ 以外的改动。
  - origin ref 仍为 18076298,92df1a60 未推送;.git/refs/tags 不存在,未打标签。
- **数据隔离:未发现读取或生成 TEST 的路径,未加载模型权重。已验证。**
  - eval_sets.jsonl 只做了整文件 sha256(t0_env.txt:59–61),按协议 :157 不算读取 TEST。
  - torch 不存在(t0_env.txt:23–28);下载目录中权重文件数为 0(t0_env.txt:53–55)。

## 问题清单
格式:严重度 | 文件:行号 | 问题 | 证据 | 建议 | 验证状态。全部只登记不修。

MAJOR | METRIX_E1_PROTOCOL.md:623(对照 :518、:6;DATA_MANIFEST.json:246–309) | ST12 与第 8 节第 1 步冲突。第 1 步要把数据哈希写入两个 manifest 并提交,manifest 的 sha256 必然改变;数据文件的“冻结值”在冻结时是 null。照字面读,ST12 会在第 1 步触发 BLOCKED,Pilot 无法进入第 2 步。协议没有定义“冻结值”指什么:PROTOCOL_FROZEN 文件中的值、第 1 步提交后的值,还是第 8 步的冻结记录。不确定之处:Owner 已知悉此冲突并选择照字面写(ROUND8_TASKS.md:40、:43),所以与指令一致,不列 BLOCKER | `| ST12 | 任何数据、manifest、模板或候选的哈希,或模型、分词器版本与冻结值不一致 | 停止;BLOCKED |`;`1. …把哈希写入两个 manifest 并提交。` | 执行第 8 节第 1 步(以及租卡)之前,由 Review Gate 裁决“冻结值”的口径;若须改文字,按 :577 开新协议版本 | 未验证(文本对照)

MAJOR | METRIX_E1_PROTOCOL.md:542 | G0.8 的适用范围没有定义:“同一 checkpoint”是哪一个(F 选定配置?任意一个?N?)、几个、覆盖哪些评测(DEV-QA、TRAIN 闭卷、EM)都没写。原有的“F 选定配置的 3 个 checkpoint”与“通用窗口 NLL 差 ≤ 1e-5”被整条删除。G0.8 不满足即 IMPLEMENTATION_FAIL;范围不定,就可以在看到结果后再选 checkpoint。不确定之处:按补充 a 字面写入,Owner 已选“整条替换”(ROUND8_TASKS.md:41、:43) | `复现:同一 checkpoint 两次评测,候选分数差 ≤ 1e-4;…` | 交 Review Gate 指定 checkpoint 与评测范围 | 未验证(文本对照)

MAJOR | METRIX_E1_PROTOCOL.md:521、:622;metrix/CLAUDE.md:36 | ST11 的门槛是 3.5 小时,metrix/CLAUDE.md 第 4 节是“实测预计超过 3 小时即停下报告”。两者同时生效时 3 小时先触发,(3, 3.5] 小时这一段的 ST11 不会起作用。不确定之处:两者可能指不同的估计,且补充 d 字面就是 3.5 | `预估超过 3.5 小时即停止并报告 Owner`;`实测预计超过 3 小时即停下报告` | 交 Review Gate 说明以哪一个为准 | 未验证(文本对照)

MAJOR | .git/logs/refs/heads/metrix-e1-pilot-protocol-v1:3 | 为把补充放进冻结提交,Executor 把未推送的 92df1a60 reset 掉后重新提交,这在本地改写了分支历史。metrix/CLAUDE.md 第 1、7 节把“改写 Git 历史”列为须 Owner/人工指令的事项。不确定之处:补充原文“放进冻结提交”(ROUND8_TASKS.md:30),加上第 3 项“第 1–3 项放在同一个提交里”,实际上要求替换 92df1a60;而且该提交未推送、未打标签(origin ref = 18076298)。另外,92df1a60 现在只存在于 reflog,它的审查与审计原始输出(reviews/92df1a60…/、audit/stdout/92df1a60…/)仍未跟踪 | `92df1a60… 180762987b… reset: moving to 180762987b…` | 请 Review Gate/Owner 在决定记录中确认;在报告提交中提交 92df1a60 的全部审查原始输出与 t6_supplement_recommit.txt | 已验证

MAJOR(沿用 92df1a60 审查,未变) | metrix/CLAUDE.md:62 | 1e 写入的新规则要求“写入时须注明作用范围”,但这条裁决自己的出处括注没有写作用范围。不确定之处:指令 1e 原文没有给出作用范围 | `（出处：Review Gate 第 7 轮裁决（第 8 轮指令第 1e 项），Owner 批准，2026-11-22 05:27 UTC；…）` | 请 Review Gate 指定作用范围 | 未验证(文本对照)

MAJOR(沿用并扩展) | METRIX_E1_PROTOCOL.md:150、:256、:527、:624 | “冻结”一词有多种含义:第 2.8 节“冻结之后才允许生成 test_qa/general_test”、第 7 节“最终冻结前”、第 8 步“提交冻结记录”、新增 ST13“配置冻结前读取 TEST”,以及现在的 PROTOCOL_FROZEN。状态改为 PROTOCOL_FROZEN 后,第 2.8 节可能被读成现在就可以生成 TEST;“配置冻结”在协议中没有定义。metrix/CLAUDE.md 第 3 节的硬性禁止也只到“收到 PROTOCOL_FROZEN 之前”。不确定之处:第 8 步与 DATA_MANIFEST.json:299 的 generation_allowed 可能已足以消除歧义 | `冻结之后才允许生成 \`test_qa.jsonl\`、\`general_test.jsonl\``;`| ST13 | 配置冻结前读取 TEST |` | 不改冻结协议;在 ROUND8_REPORT 中写明 TEST 的生成仍以第 8 步为准,并须人工指令(CLAUDE.md 第 7 节) | 未验证(文本对照)

MINOR | METRIX_E1_PROTOCOL.md:544 | G0.10 没有规定 σ_d 的 bootstrap 怎么做:次数、是否按第 6 节 :243 分 stratum 抽、随机数 purpose、标准差的自由度都没写。“以最大者”的取值范围也有歧义:若跨 δ 取最大,结果恒为 δ=0.05 时的值;是否跨 Δ(L−F)、Δ(A−F) 取也没写。只影响规划数,不影响 G0.10 是否通过(条件仍是 σ_d 有限) | `分别用 σ_d 的 bootstrap 2.5 分位、点估计、97.5 分位…以最大者作为 E1-V1 规划依据` | 登记 | 未验证(文本对照)

MINOR | METRIX_E1_PROTOCOL.md:521、:620、:622;SEARCH_SPACE.json:44、:210–216 | 预检的细节未定:“第一个配置”是否就是 F1、种子 101;这 20 步之后丢弃,还是计入 F1 的搜索运行;“预估总时长”的算法。ST11 在第 9 节没有对应的状态。ST9 要求“从第 3 步重新开始”,会跳过预检。SEARCH_SPACE.json 的 hardware.rule 与 counts 没有包含预检运行 | `预检(正式运行前;ST11):在 A100 上跑第一个配置的前 20 步…` | 登记 | 未验证(文本对照)

MINOR | METRIX_E1_PROTOCOL.md:542、:583–604 | G0.8 要求确定性设置“并记录”,但第 10 节实验记录模板中没有对应字段(设置本身在第 0 节 :43) | `实现须开启 PyTorch 确定性设置并记录` | 登记 | 未验证(文本对照)

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN(未跟踪):9、:14、:21、:23 | 工作区里为第 5 项准备的草稿仍写着已被取代的 92df1a60 及其 sha256(协议 61f4b777…、SPLIT_MANIFEST 2078d045…),与本提交的值(t1_protocol_checks.txt:38、:40 中的 141473…、7eb5d6…)不同;:14 的内容说明也没有包含补充 a–e | `| 冻结提交(完整 hash) | \`92df1a60ac816ab02b250d32841397c73b9a67a7\` |` | 第 5 项提交前必须按 6a474e4a 重新生成,并重新审查 | 已验证

MINOR | reports/round8/t1_protocol_checks.txt:71 | 这份原始输出在提交前被编辑过:第一次按字节 locale 运行的 grep 的输出被删掉了。文件中写明了这一点,但与“原始输出不编辑”的做法不一致。旧版的非法 UTF-8 问题已解决,新文件按 UTF-8 读取正常 | `its output was dropped from this file before commit and the greps were re-run here` | 以后保留失败的运行,另起一次运行附在后面 | 已验证

MINOR | METRIX_E1_PROTOCOL.md:126;SPLIT_MANIFEST.json:323 | 每条 fact 只抽 3 个干扰项,但门槛是池 ≥ 4;DATA_SEED 下 unread 的池正好是 4,处在门槛上。按补充 b 字面写入,目前不触发 | t1_protocol_checks.txt:69 `{'learned': [14], 'unread': [4]} | minimum 4` | 登记 | 已验证

MINOR(沿用 92df1a60 审查,仍成立) | 见 reviews/92df1a60ac816ab02b250d32841397c73b9a67a7/code-reviewer.md:75–89 | 以下各条原样仍成立:
- metrix/CLAUDE.md:21 仍写“状态:AWAITING_REVIEW_GATE”;
- 1d 把“全部文件”读成 4 个文件,config.json 与 generation_config.json 的 sha256 只在报告中;
- L6 的 TEST 文本没有写解码参数,tokenizers 库版本也没有固定(SPLIT_MANIFEST.json:375);
- EM 的残余边界情形(未闭合的 `<think>` 等)未规定(:211);
- 其它数据文件的记录格式未定义;
- 状态行与第 14 节引用的 PROTOCOL_FROZEN 文件和标签在本提交中尚不存在;
- ST12 写的是“分词器版本”,没有覆盖分词器文件 sha256 不符时的处理。
原先“冻结后 manifest 字段要改”一条已并入上面 ST12 那条 MAJOR;原先非法 UTF-8 一条已解决 | 同原文 | 登记 | 同原文

结论:PASS
