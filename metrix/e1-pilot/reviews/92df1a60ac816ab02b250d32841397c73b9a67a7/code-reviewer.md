# code-reviewer final report, round 8, freeze commit 92df1a60ac816ab02b250d32841397c73b9a67a7 (parent 18076298); invoked 2026-11-22 05:40 UTC (background); invocation text: code-reviewer_prompt.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-a78d3caa09ba0e947.jsonl)
---
code-reviewer 第 8 轮审查(冻结提交 92df1a60ac816ab02b250d32841397c73b9a67a7,父提交 18076298)

## 审查依据与边界
- 我按仓库文件 /home/user/OpenMythos/.claude/agents/code-reviewer.md 执行。它比已加载的定义多第 29–30 行(已验证/未验证的标注规则),两者 tools 行相同,都是 `tools: Read, Grep, Glob`。
- 依据:/home/user/OpenMythos/metrix/e1-pilot/tasks/ROUND8_TASKS.md、/home/user/OpenMythos/metrix/e1-pilot/reviews/92df1a60ac816ab02b250d32841397c73b9a67a7/review_input.diff、该提交中的协议、三个 JSON 和 metrix/CLAUDE.md、/home/user/OpenMythos/metrix/e1-pilot/reports/round8/ 下的原始输出、/home/user/OpenMythos/.git/logs/HEAD。
- 我没有运行任何命令,只用了 Read、Grep、Glob。下面凡是只靠读文件做的判断,标为“未验证(文本对照)”;凡是引用了已提交原始输出或 reflog 的,标为“已验证”。
- 已提交文件的字节与 t1_protocol_checks.txt 中工作区 sha256 是否一致,我没有工具计算,由 data-auditor 复算。

## 逐条对照(指令 1a–1e、2、3、同一提交)

- **1a:一致。** 已验证(t1_protocol_checks.txt:37 打印了两个 record 字段)。
  - 协议第 2.6 节(METRIX_E1_PROTOCOL.md:138)写的是 `train_S.jsonl` 每行 `{"fact_id", "answer_fact_id", "text"}`;第 2.5 节(:128)写的是 `candidates.json` 为 `{fact_id: [4 个候选]}`。这两处在父提交中已有,本提交未改。
  - 本提交在 DATA_MANIFEST.json:263、:282 新增 `record` 键,与协议 2.5、2.6 及 DATA_MANIFEST.json:216、SPLIT_MANIFEST.json:325 一致。
  - 已记入第 14 节(:683)。

- **1b:一致。** 未验证(文本对照)。
  - 协议 :168(L6 一行)写明了指令要求的三点:13-gram 只在每篇文档(每篇锚文档、每个窗口)之内取,不跨篇拼接;两边各自合并成集合后,数交集的种类数;文本是实际送入模型的 id 解码所得(锚文档最多 128 个 id,窗口最多 256 个 id)。这与第 2.7 节一致。
  - “两方结果不一致按 BLOCKED 处理并报告 Owner”已写入以下各处:执行接口 :173、第 8 步 :525、第 9 节 BLOCKED 一行 :572、ST10 :619、SPLIT_MANIFEST.json:373–376、:382。
  - 旧措辞“数交集的元素个数”在第 14 节以外已不存在(t1_protocol_checks.txt:64–67,这部分已验证)。
  - 已记入第 14 节(:684)。

- **1c:一致。** 未验证(文本对照)。
  - 协议 :210:“删除 `<think>…</think>` 片段之后,先去掉开头的空白(含空格与换行),再取第一行……”。DATA_MANIFEST.json:39 的顺序相同。
  - 旧措辞在第 14 节以外已不存在(t1_protocol_checks.txt:64–67,已验证)。
  - 已记入第 14 节(:685)。

- **1d:一致。** 已验证。
  - DATA_MANIFEST.json:19–25 写入了 4 个分词器文件的 sha256,数值与 t0_env.txt:48–51、t1d_data_hashes.txt:71–74 逐字相同。
  - 固定 revision 的仓库树中只有这 4 个分词器文件(t0_env.txt:30–41)。只用这 4 个文件加载的分词器,与 6 文件目录在类、词表、编码、chat template(enable_thinking=False)、特殊 id 上都相同(t1d_data_hashes.txt:76–82)。
  - DATA_MANIFEST.json:242–243 写入了锚文本哈希 `8828bc4f…`,与 t1d_data_hashes.txt:13、:27、:65 相同。参考实现 reports/round2/anchor_check.py:63、:66 的算法与 hash_rule 的描述一致。
  - 下载的字节是否就是 HF 上该 revision 的文件,我没有独立核对(属 data-auditor 范围)。
  - 已记入第 14 节(:686)。

- **1e:一致。** 未验证(文本对照)。
  - metrix/CLAUDE.md:62 改为:“「永久」与「本阶段」的裁决可写入本文件,写入时须注明作用范围;「本阶段」的裁决在本阶段结束时失效。”并写了出处、批准时间和原因。
  - 已记入第 14 节(:687)。
  - 有一条 MAJOR,见下面问题 1。

- **2:一致。** 已验证。
  - 以下各处都已改为冻结值,并注明“Owner 批准，2026-11-22 05:27 UTC”(全角逗号,与指令相同):
    - 训练契约表头(:261),表中数值未改;
    - SEARCH_SPACE.json:4–5,以及协议内联副本 :297–298;
    - 两个 manifest 的 status(DATA_MANIFEST.json:4–5、SPLIT_MANIFEST.json:4–5);
    - 第 13 节两项(:632–635):320 条 fact、Pilot 后按 G0.10 重算;dNLL ≤ +0.03 在 Pilot 中只报告;
    - :10、:55、:639 的随附措辞。
  - 原始输出:t1_protocol_checks.txt:30–33(三个 JSON 的 status、re-dump、内联副本逐字相同)、:45–54(残留标记只在第 14 节和 :639 的说明句中)、:57–61(出处字符串计数)。
  - 我用不区分大小写的 Grep 复查 `propos|TBD|TODO|pending|待定|待决`:三个 JSON 中 0 处;协议中只在 :639 和第 14 节。
  - 已记入第 14 节(:688)。

- **3:一致。** 未验证(文本对照)。
  - 协议 :6 的状态为 `**PROTOCOL_FROZEN**(Owner 批准，2026-11-22 05:27 UTC;…)`。
  - 已记入第 14 节(:689)。

- **同一提交:一致。** 已验证。
  - .git/logs/HEAD:6 显示 18076298 到 92df1a60 只有一次 commit;.git/refs/heads/metrix-e1-pilot-protocol-v1 指向 92df1a60。
  - review_input.diff:22–32 的 stat 包含全部 5 个被改文件、ROUND8_TASKS.md 与 round8 原始输出。
  - t1_protocol_checks.txt:3–15 显示,提交前 HEAD 仍为 18076298,这 5 个文件是工作区改动。
  - 没有 metrix/ 以外的改动。

- **数据隔离:未发现 TEST 读取或生成路径,未加载模型权重。** 已验证。
  - 本提交不含训练或评测代码。
  - 对 eval_sets.jsonl 只做了整文件 sha256(t0_env.txt:59–60),按协议 :156 不算读取 TEST。
  - 下载目录中权重文件数为 0(t0_env.txt:53–55),环境中没有 torch。

## 问题清单
格式:严重度 | 文件:行号 | 问题 | 证据 | 建议 | 验证状态。按指令第 4 项,以下全部只登记不修。

MAJOR | metrix/CLAUDE.md:62 | 1e 新写入的规则要求“写入时须注明作用范围”,但这条裁决自己的出处括注没有写作用范围(本阶段还是永久)。同文件其它写入的裁决都写了::45 本阶段、:69 永久、:75 本阶段。不确定之处:指令 1e 原文没有给出作用范围,Executor 不能自定,这是指令的空缺,不是执行偏差 | `（出处：Review Gate 第 7 轮裁决（第 8 轮指令第 1e 项），Owner 批准，2026-11-22 05:27 UTC；原因：…）` | 登记;请 Review Gate 指定这条裁决的作用范围 | 未验证(文本对照)

MAJOR | METRIX_E1_PROTOCOL.md:149(对照 :255、:525;DATA_MANIFEST.json:299;metrix/CLAUDE.md:27) | 第 2.8 节说“冻结之后才允许生成 test_qa.jsonl、general_test.jsonl”,这里的“冻结”没有限定。本提交把状态改为 PROTOCOL_FROZEN 后,这句可能被读成“协议冻结后即可生成 TEST”,与第 8 节第 8 步(Gate 0 通过并提交冻结记录之后)以及 manifest 的 generation_allowed 不一致。另外,CLAUDE.md 第 3 节的硬性禁止以“收到 PROTOCOL_FROZEN 之前”为限,冻结后这层保护失效,只剩协议第 8 步与 CLAUDE.md 第 7 节的人工指令。不确定之处::255 的“最终冻结”、第 8 步和 manifest 可能已足以消除歧义 | `冻结之后才允许生成 \`test_qa.jsonl\`、\`general_test.jsonl\``;`"generation_allowed": "only after Gate 0 qualifies and the selected configurations and all identities are frozen"` | 登记;不改冻结协议;在 ROUND8_REPORT 中写明 TEST 的生成条件仍是第 8 节第 8 步,且须 Owner 指令 | 未验证(文本对照)

MINOR | metrix/CLAUDE.md:21 | 第 2 节仍写“E1 Pilot,状态:AWAITING_REVIEW_GATE”,与已冻结的协议不一致。指令没有要求改,改动须经 Review Gate 裁决 | `- E1 Pilot,状态:AWAITING_REVIEW_GATE` | 登记;交 Review Gate | 未验证(文本对照)

MINOR | DATA_MANIFEST.json:19–25 | 1d 把“分词器全部文件”读成 4 个文件。第 7 轮的报告与报告提交审查提到的是“Qwen 6 个文件”(ROUND7_REPORT.md:235;reviews/293b806d…/code-reviewer_report-commit.md:53);config.json(`1ddb5b89…`)与 generation_config.json(`2325da0f…`)的 sha256 仍只在报告中。按指令字面,4 个文件的读法成立,且有等价性证据 | t0_env.txt:30–41、:46–51;t1d_data_hashes.txt:76–82 | 登记;若 Review Gate 的意图包含这 2 个文件,另行决定 | 已验证

MINOR | SPLIT_MANIFEST.json:374;METRIX_E1_PROTOCOL.md:168 | L6 TEST 的文本规则没有写解码参数(skip_special_tokens、clean_up_tokenization_spaces 等),而锚文本哈希规则(DATA_MANIFEST.json:243)写了“default arguments”。tokenizers 库版本(t0_env.txt 中为 0.23.3)也没有在第 0 节固定。两方须结果一致,口径不全可能导致不一致,进而 BLOCKED | `"text": "...the decode, with the protocol tokenizer, of the ids actually fed to the model..."` | 登记 | 未验证(文本对照)

MINOR | METRIX_E1_PROTOCOL.md:210;DATA_MANIFEST.json:39 | 1c 只解决了待决第 6 项的第 1 点,以下仍未规定:未闭合的 `<think>` 与单独出现的 `</think>`(ROUND7_REPORT.md:185);“第一行”按什么切分;结尾标点是去一个还是全部去掉。另外,协议写“空白(含空格与换行)”,manifest 写“(spaces and newlines)”,前者是“包含”,后者像是穷举,范围措辞不完全相同。EM 只报告,不进门槛 | 见两处原文 | 登记 | 未验证(文本对照)

MINOR | DATA_MANIFEST.json:246–309 | 1a 只写死了 train_S 与 candidates 的记录格式。待决第 2 项后半(ROUND7_REPORT.md:176)问到的 facts、train_F、train_Y、dev_qa、general_dev、anchor_text.jsonl 的字段仍未定义,第 8 节第 1 步写入的 canonical_sha256 将依赖 Executor 的选择。anchor_text.jsonl 的 canonical_sha256 与新增的 decoded_texts_canonical_sha256 口径不同,两者关系也没有写明 | `"anchor_text.jsonl": {… "canonical_sha256": null}` | 登记 | 未验证(文本对照)

MINOR | METRIX_E1_PROTOCOL.md:6、:683–691 | 状态行与第 14 节 v1-r8 各行引用了同目录的 `PROTOCOL_FROZEN` 文件与标签 `metrix-e1-pilot-frozen`,两者在冻结提交中尚不存在(第 5 项才创建),若第 5 项不执行,引用会悬空。v1-r8 各行不满足第 14 节表头“哈希为包含该改动的提交”,:691 已说明原因。另外,1a 一行的出处写“Review Gate 第 7 轮裁决,第 8 轮指令第 1a 项”,1b–1e 各行只写“第 8 轮指令第 1x 项”,写法不统一 | Glob 找不到 metrix/e1-pilot/PROTOCOL_FROZEN 与 .git/refs/tags/* | 登记;按时完成第 5 项 | 已验证

MINOR | DATA_MANIFEST.json:4、:246–309;SPLIT_MANIFEST.json:393–399 | 冻结后,第 8 节第 1 步还要往这两个 manifest 填写 files.* 与 split_sha256,因此第 5 项钉在 PROTOCOL_FROZEN 中的 manifest sha256 之后必然对不上。协议没有写明冻结后允许改哪些 manifest 字段 | `第 8 节第 1 步:把哈希写入两个 manifest 并提交` | 登记;可在报告中说明 | 未验证(文本对照)

MINOR | DATA_MANIFEST.json:19–25;METRIX_E1_PROTOCOL.md:38 | 新增的分词器文件 sha256 在协议正文中没有对应规则,即文件不符时应怎么处理(例如是否 BLOCKED);库版本一行写了“不一致即 BLOCKED”,分词器文件没有 | `"files_sha256": {...}` | 登记 | 未验证(文本对照)

MINOR | reports/round8/t1_protocol_checks.txt:45–54、:65–67 | `cut -c1-200`、`cut -c1-120` 按字节截断,切断了多字节 UTF-8 字符,所以这份已提交的原始输出(以及 review_input.diff)不是合法 UTF-8 | :47 `…已于冻结时改为冻结值(Owner 批�`;Read 工具对这两个文件都报 “not valid UTF-8” | 登记;以后按字符截断或不截断 | 已验证

结论:PASS
