# E1-PILOT 第 7 轮报告

- 指令:`tasks/ROUND7_TASKS.md`(原文照录,两段:本轮指令与 Review Gate 裁决)。本轮是冻结补丁:只执行已定的修改,不开放新的设计问题。允许快进推送 `metrix-e1-pilot-protocol-v1`,不得 force push。
- 执行会话:session_01J5mxaTx8SWDUGRUNbxcnqu。会话从 `main`(`155430a`)启动;本地检出 `metrix-e1-pilot-protocol-v1`(第 6 轮的 `49471e86`),没有改写历史。
- 运行环境(`round7/t0_env.txt`):Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,无 GPU(`command -v nvidia-smi` 退出码 1),Ubuntu 24.04.5,Python 3.13.18。venv:transformers 5.22.2、tokenizers 0.23.3、jinja2 3.1.6、pyarrow 26.0.1、huggingface_hub 2.4.0;`import torch` 失败(未安装)。
- 下载内容:Qwen/Qwen3-1.7B@70d244cc 的分词器与配置文件 6 个、parcae-tokenizer@6247b5d0 的 `tokenizer.json`、锚文本源 parquet。8 个文件的 sha256 与第 6 轮逐个相同(`round7/t0_env.txt` 中 `diff` 退出码 0);没有任何权重文件。
- 没有训练,没有评测,没有生成或读取 TEST 数据。本轮只生成了 `train_S.jsonl` 与 `candidates.json`(第 1g 项,放在 scratchpad,没有提交),用到的是 160 条 fact 与 4 个 TRAIN 模板。
- 原始输出在 `reports/round7/`。命令行由 `round5/logrun.sh` 记录(`printf %q` 转义)。`SP` 指本会话 scratchpad。

## 结论一览

| 指令 | 状态 | 证据 |
|---|---|---|
| 0 比对用户级副本 | 规则文件不一致(以仓库为准);`code-reviewer.md` 不一致,按指令停下报告;Review Gate 裁决选项 3 后继续 | `round7/t0_copy_check.txt`(提交 `fe321cd9`) |
| 裁决 1–4 | 完成。证据文件不经审查提交;两版 frontmatter 与 tools 行相同;两次调用的第一句按规定;写入 `metrix/CLAUDE.md` 第 5 节第 6 条 | `t0_copy_check.txt` 第二部分;`reviews/293b806d…/` |
| 1 协议修改 a–g | 完成;第 14 节 v1-r7 七行。1g 两次独立生成逐字节一致:`train_S.jsonl` `686fdd2f…`,`candidates.json` `e5d15c99…` | 协议第 2.2、2.5–2.7、3、5、8、9、11、14 节;两个 manifest;`round7/t1*.txt` |
| 2 CLAUDE.md 第 10 节;code-reviewer 规则 | 完成 | `metrix/CLAUDE.md`;`.claude/agents/code-reviewer.md` 第 30 行 |
| 3 DEFERRED_MINORS | 完成:1.7 节 G1–G5 | `reports/DEFERRED_MINORS.md` |
| 4 两个审查 | code-reviewer **PASS**(4 MAJOR、13 MINOR,无 BLOCKER);data-auditor **PASS**(仅作参考;两个 1g 哈希独立复现;5 条 MINOR / 观察,无 BLOCKER)。新问题全部登记入 1.8 节,不修 | `reviews/293b806d…/`;`audit/stdout/293b806d…/` |
| 5 报告与推送 | 本文件;冻结时的哈希见文末 | `round7/t5_freeze_hashes.txt` |

## 第 0 步与 Review Gate 裁决

- **比对结果**(`round7/t0_copy_check.txt` 第一部分):
  - 规则文件 `~/.claude/CLAUDE.md`(`a24f6f3d…`)与仓库 `metrix/CLAUDE.md`(`d9b620ae…`)不一致。按指令以仓库为准。副本的 sha256 等于 `8ce8c896` / `7e5dd9c0` 中的 `metrix/CLAUDE.md`(`round6/t4_user_claude_md.txt` 第 24–25 行),缺第 7 节的注、第 9 节第 4 轮的永久规则与第 10 节第 5 轮的两条。
  - agent 定义:`data-auditor.md` 两份相同(`42011228…`);`code-reviewer.md` 不一致,用户级副本(`bf66a0d6…` = `f4d8e988` 及更早的版本)缺第 6 轮加的「未验证」一句。
  - 原因同第 6 轮任务 4:本会话从 `main` 启动,`main` 里没有 `.claude/agents/`,启动时只能加载构建容器时(2026-11-21 04:56:35 UTC)复制的用户级副本。
- 按指令第 0 步,我在 agent 定义不一致处停下报告,没有改任何文件。Review Gate 裁决选项 3(在本会话继续),要点:
  1. 比对原始输出存为 `round7/t0_copy_check.txt`,作为证据文件不经 code-reviewer 提交:提交 `fe321cd9`,commit message 写明「证据文件，未经 code-reviewer」。该提交当时即已推送:`metrix-e1-pilot-protocol-v1` 快进 `49471e8..fe321cd`;会话分支 `claude/metrix-freeze-patch-round7-ve3sua` 由 `155430a` 更新到 `fe321cd`(推送输出未入库,以 `.git/logs/refs/remotes/` 的 reflog 为据)。
  2. 两份 `code-reviewer.md` 的 frontmatter 逐字节相同(同一文件第二部分:`diff` 无输出,`FRONTMATTER_IDENTICAL`,两份 frontmatter 的 sha256 都是 `4e0a6888…`;tools 行都是 `tools: Read, Grep, Glob`,`cmp` 相同,`TOOLS_LINE_IDENTICAL`)。没有停下。
  3. 本轮两次审查调用文字的第一句都是裁决规定的句子(`reviews/293b806d…/code-reviewer_prompt.txt`、`data-auditor_prompt.txt` 第 1 行)。
  4. 已写入 `metrix/CLAUDE.md` 第 5 节第 6 条(见任务 2)。调用前按该条比对了 tools 行:两个 agent 的仓库文件与用户级副本 frontmatter 相同、tools 行相同(`reviews/293b806d…/preflight_tools_check.txt`)。

## 提交

| 提交 | 时间(UTC) | 内容 | 审查 |
|---|---|---|---|
| `fe321cd9` | 2026-11-22 03:16:28 | 第 0 步比对与 frontmatter 核对的原始输出 | 按裁决不经审查 |
| `7fea9181` | 2026-11-22 03:25:59 | 工作提交:协议第 1a–1g 项、两个 manifest、`metrix/CLAUDE.md` 第 5、10 节、`code-reviewer.md`、`DEFERRED_MINORS.md`(第 3 项)、`tasks/ROUND7_TASKS.md`、`round7/` 下的原始输出与 `gen_s_cands.py`。第 14 节与 CLAUDE.md 中的时间与提交是占位符 | 审查范围内 |
| `293b806d` | 2026-11-22 03:26:28 | 填入占位符(`7fea9181`,2026-11-22 03:25:59);`round7/t1_commit_times.txt`、`t1_protocol_checks.txt` | 审查范围内 |
| 报告提交 | — | 本报告;审查原文、调用文字、中断与续做记录(`reviews/293b806d…/`);data-auditor 的 5 个新脚本与 `audit/stdout/293b806d…/` 01–16;`DEFERRED_MINORS.md` 1.8 节;`round7/t5_freeze_hashes.txt` | 提交前由 code-reviewer 审查(`metrix/CLAUDE.md` 第 5 节第 1 条):PASS,原文 `reviews/293b806d…/code-reviewer_report-commit.md`;审查之后对报告的改正见任务 4 末节。提交哈希见最终回复(提交无法包含自身哈希) |

## 任务 1:协议修改(第 14 节 v1-r7 七行)

| 项 | 落地位置 | 新文字(摘) |
|---|---|---|
| 1a | 第 2.7 节末句 | “锚文本与通用文本不得共享任何词 13-gram(定义与上限见第 3 节 L6)。” |
| 1b | 第 3 节 L6 一行与执行接口;第 8 节第 8 步;`SPLIT_MANIFEST.json: leakage_checks.L6_general_text.test_part`(新增)、`test_split` | L6:“TEST 部分(锚文本对 `general_test.jsonl`):时机为第 8 步生成 `general_test.jsonl` 之后、TEST 评测之前;计数为跨全部文档的共享词 13-gram 种类数(13-gram 在每篇锚文档、每个窗口之内取;……求交,数交集的元素个数),上限 0;由 Executor 与 data-auditor 各自计算,结果须一致”。第 8 步原“在 PROTOCOL_FROZEN 之后……由 data-auditor 运行一次”改为“在本步生成 `general_test.jsonl` 之后、TEST 评测之前,由 Executor 与 data-auditor 各自计算一次……两者的结果须一致” |
| 1c | 第 8 节第 8 步;第 11 节新增 ST10;第 9 节 BLOCKED 一行;第 3 节执行接口;`SPLIT_MANIFEST.json: leakage_checks.test_part_over_limit`(新增) | ST10:“第 8 步 L3–L6 任一项的 TEST 部分超限 → 停止;不评测 TEST;BLOCKED;报告 Owner” |
| 1d | 第 8 节 G0.1;`SPLIT_MANIFEST.json: leakage_checks.test_split` | “泄漏检查 L1–L6 全部在上限内;L1–L6 中涉及 TEST 的部分在 Gate 0 不要求,按第 8 步运行” |
| 1e | 第 5 节 general damage;第 2.7 节;第 2.2 节锚文本规则;`DATA_MANIFEST.json: general_text.window_rule`(补一句)、`anchor_text.document_rule`(新增) | n_w:“窗口实际送入模型的 id 序列长度:送入模型的是第 2.7 节用本协议分词器切分后截断得到的原始 id(最多 256 个),不解码再编码”。锚文档:“每篇最多 128 token(取前 128 个),不足则取全长” |
| 1f | 第 5 节 EM;`DATA_MANIFEST.json: model.input_convention.em_generation` | “归一化之前,先删除输出中的 `<think>…</think>` 片段:从 `<think>` 到其后第一个 `</think>`(两者都含),每处都删;这两个标记(id 151667、151668)不是特殊 token,`skip_special_tokens=True` 不会去掉它们” |
| 1g | 第 2.5 节(细节 5、`candidates.json` 格式、复现哈希);第 2.6 节(细节 4、`train_S.jsonl` 格式、复现哈希);`DATA_MANIFEST.json: s_permutation`(字符串改为对象,原文保留为 `rule`);`SPLIT_MANIFEST.json: candidates`(新增 `call_order`、`file`、`reference_implementation`、`candidate_mapping_sha256_note`,`candidate_mapping_sha256` 由 null 改为全值) | 见下 |

### 1g:调用方式与两次独立生成

- **S(第 2.6 节细节 4)**:cell 按第 2.2 节顺序;每个 cell 只建一个生成器 `rng_rule(DATA_SEED, "s-permutation:<relation>:<stratum>")`;每次从 `p = list(range(15))` 开始调用一次 `r.shuffle(p)`,有不动点就用同一个生成器再从 `list(range(15))` 抽。第 i 条 S 句的 `{E}` 取第 i 条 learned fact 的 entity,`{A}` 取第 `p[i]` 条的 answer。行格式 `{"fact_id", "answer_fact_id", "text"}`,行序为 cell 顺序、cell 内按 i。
- **候选(第 2.5 节细节 5)**:每条 fact 一个生成器 `rng_rule(CANDIDATE_SEED, "cand:<fact_id>")`;池按 fact 生成顺序、不含自己;依次 `d = r.sample(池, 3)`、`c = [a_f] + d`、`r.shuffle(c)`。`candidates.json` 是 `{fact_id: c}`,160 个键。
- **两次独立生成**(`round7/t1g_gen_s_cands.txt`):参考实现 `round7/gen_s_cands.py`,两个独立进程(`PYTHONHASHSEED` 分别为 0 与 4242),各写到不同目录。
  - 两次的输入 fact 都是本轮用第 2 轮参考脚本重建的 160 条(规范化 SHA-256 `406c8801…`,与协议相同;`round7/t0_facts_regen.txt`)。
  - 两个文件 `cmp` 都相同(退出码 0);`train_S.jsonl` 120 行、15,033 字节,`candidates.json` 160 个键、10,453 字节。
  - 文件按第 0 节的规范化序列写出,所以 byte_sha256 与 canonical_sha256 相同;脚本另从写出的文件重新解析、重算规范化哈希,结果相同:
    - `train_S.jsonl`:`686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e`
    - `candidates.json`:`e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705`
  - 脚本自检全部通过(`RESULT: PASS`):S 为 cell 内无不动点的置换;每个 learned entity 与 answer 在 S 语料中恰好出现 1 次,unread 的 0 次(L3a 的 train_S 部分);每条 fact 4 个不同候选,真实答案恰好 1 次,干扰项都来自第 2.5 节的池。各 cell 抽到无不动点置换所用的次数为 1–6 次。
  - 在填好占位符的 manifest 上再跑一次(`PYTHONHASHSEED=7`),输出与第一次逐字节相同(`round7/t1_protocol_checks.txt`)。
- **写入 manifest 的位置**:`train_S.jsonl` 的哈希写在 `DATA_MANIFEST.json: s_permutation.expected_train_S_canonical_sha256`(与 fact 哈希写在 `name_generation.expected_facts_canonical_sha256` 的先例相同);候选的哈希写在协议第 2.5 节指定的 `SPLIT_MANIFEST.json: candidates.candidate_mapping_sha256`。两个哈希也写进了协议正文(第 2.5、2.6 节“复现”)。`DATA_MANIFEST.json: files` 中这两个文件仍是 `NOT_GENERATED / null`,`SPLIT_MANIFEST.json: split_sha256.train_S.jsonl` 仍是 null:正式文件按第 8 节第 1 步生成时再填。生成的两个文件没有提交。

### 核对(`round7/t1_protocol_checks.txt`,填好占位符之后的内容)

- 表格:`round6/table_check.py`,153 行,单元格数与表头不一致的 0 行,未转义的特殊 token 0,`RESULT: PASS`。
- 三个 JSON 可解析;`SEARCH_SPACE.json` 与协议内联副本逐字相同;协议与 `metrix/CLAUDE.md` 中的占位符 0。
- 32 个模板的归一化与 `normalized_sha256` 全部可复现;`template_set_sha256` 重算 `2b524113…`,与 manifest 相同。
- 两个 1g 哈希在 manifest 与协议正文中各出现 1 次。
- 旧措辞只剩第 14 节的历史行(v1-r2 补记一行“各截到 128 token”;v1-r7 引用原文的两行)。
- `outside_metrix_check.py --rev 7fea9181`:metrix/ 以外只有根目录 `CLAUDE.md`(宪章前缀不变)与两个 agent 文件,`RESULT: PASS`(`round7/t1_commit_times.txt`)。
- 1f 的依据(`round7/t1f_think_tokens.txt`):固定分词器中 `<think>` = 151667、`</think>` = 151668,都不在 `all_special_ids` 中,`special` 为 False;一段含这两个标记的 id 序列用 `skip_special_tokens=True` 解码后两个标记仍在,只有 `<|im_end|>` 被去掉。

## 任务 2:metrix/CLAUDE.md 与 code-reviewer 定义

- 第 10 节末行原为“以上两条的出处：Review Gate 第 5 轮裁决。”,其后补上指令给出的括注,成为“以上两条的出处：Review Gate 第 5 轮裁决。（出处：Review Gate 第 6 轮裁决，Owner 批准，本阶段，2026-11-22 03:25:59 UTC）”。
  - `<UTC 时间>` 我填的是这次改动的提交 `7fea9181` 的时间,与第 14 节的做法相同;第 10 节这两条最初是在 `481a6f0f`(2026-11-21 14:41:02 UTC)写入的。原句没有删,所以同一行有两个“出处”:前一个是内容的来源,后一个是批准与作用范围(R7-CR:34 指出,登记为 R5)。
- `.claude/agents/code-reviewer.md`:在“未实际运行就作出的判断须标注『未验证』。”之后另起一行,加“引用仓库中已提交的原始输出（写明路径与行号）的判断视为已验证。”(用 `git add -f` 暂存;`outside_metrix_check.py --rev 7fea9181` PASS)。frontmatter 没有改,tools 行仍与用户级副本相同(`reviews/293b806d…/preflight_tools_check.txt`)。
- 第 5 节新增第 6 条(Review Gate 第 7 轮裁决第 3、4 项):调用文字第一句的固定写法;“两个版本的 tools 行不一致时必须停下,不得用此方法替代”;出处括注“（出处：Review Gate 第 7 轮裁决，Owner 批准，本阶段，2026-11-22 03:25:59 UTC）”。我另加了一句操作说明“调用前比对仓库文件与已加载定义的 frontmatter”(R7-CR:35 指出超出原文,登记为 R6)。
- 03:27 调用的 code-reviewer 用的仍是启动时加载的旧定义。它在报告开头说明:它加载的定义最后一行是“不确定是否为问题时，列为 MAJOR 并说明不确定之处，不要省略。”,读到的仓库文件最后两行是新的两句,两版 tools 行相同,它按仓库文件执行(R7-CR:5–7)。它的判断都标了“已验证”或“未验证”,并写明依据。会话进程重启后,03:53 调用的报告提交审查报告它加载的定义末尾已是新的两句,与仓库文件相同(`reviews/293b806d…/code-reviewer_report-commit.md` 第 5–6 行;这是它自己的陈述,仓库里没有对应的原始输出)。

## 任务 3:DEFERRED_MINORS.md

- 新增 1.7 节,开头照录指令要求注明的原文“正式流程代码统一要求不通过时打印 RESULT 并以非 0 退出”。
- 第 6 轮待决第 6 项的三点登记为 G1–G4:
  - G1:`template_overlap.py`、`y_ratio.py` 不通过时仍以 0 退出。
  - G2:4 个脚本不通过时以 1 退出,但没有 RESULT 行。
  - G3:排除在外的 7 个脚本是否算检查脚本。
  - G4:auditor 的旧脚本是否在范围内。
- 第 14 项登记为 G5(同 H1)。
- 第 3 节原有的三项:`<think>` 与 S/候选两项已由本轮 1f、1g 处理,移到第 2 节;auditor 旧脚本一项指向 G4。这部分超出第 3 项字面(R7-CR:36,登记为 R7)。
- 新增 1.8 节:本轮两份审查新提出的 MAJOR / MINOR,只登记,不修。

## 任务 4:审查(`reviews/293b806d…/`)

- **调用**:2026-11-22 03:27 UTC,两个 subagent 在后台并行调用,审查范围 `fe321cd..293b806d`。
  - 调用文字:`code-reviewer_prompt.txt`、`data-auditor_prompt.txt`,第一句都是裁决规定的句子。
  - 审查输入:`review_input.diff`(git log、`--stat` 与完整 diff)。
  - 调用前的 tools 行比对:`preflight_tools_check.txt`。
- **审查原文**:`code-reviewer.md`、`data-auditor.md`。由 `round6/review_extract.py` 从本会话的 subagent 记录中取 `SubagentHandback` 的 `message`,原样写在分隔线下。
  - 提取记录 `extract_log.txt` 打印了两份原文的 sha256:code-reviewer `82ac2227…`,data-auditor `3e189c34…`。
  - 同一文件核对了保存的调用文字与 subagent 收到的消息逐字相同。
- **中断与续做**:data-auditor 在 01–15 号运行完成、交回报告之前,因额度用尽(HTTP 429)中止(`interruption.txt`)。会话进程随后重启。
  - 约 03:48 UTC,我用 SendMessage 让它从中断处续做,文字见 `resume_message.txt`,第一句同样是规定的句子。
  - 它只补跑了 16 号 `git status --short`,然后交回报告,没有重做已完成的检查。

### code-reviewer:PASS(4 MAJOR、13 MINOR,无 BLOCKER)

- 第 1a–1g 项、第 2 项、第 3 项与裁决第 3、4 项逐条判为“一致”(R7-CR:12–24)。其中三处注明有超出指令原文的内容,见下面的 MAJOR 3、MINOR R6、R7。
- 没有 BLOCKER:diff 中没有训练或评测代码,没有任何代码路径生成、读取或评测 TEST(R7-CR:26–27)。
- 4 条 MAJOR 都不是执行偏差,而是请 Review Gate 确认的读法或文件内部的矛盾,列入下面“待 Review Gate 决定”第 1–4 项。
  - MAJOR 1:候选种子的读法(R7-CR:30)。
  - MAJOR 2:两个文件的记录格式由 Executor 自定(R7-CR:31)。
  - MAJOR 3:L6 计数口径加了“在每篇文档之内取”的限定(R7-CR:32)。
  - MAJOR 4:`metrix/CLAUDE.md` 第 8 节与写入“本阶段”裁决之间的矛盾(R7-CR:33)。
- 13 条 MINOR 登记为 `DEFERRED_MINORS.md` 1.8 节 R5–R17。
  - R11 说已提交的输出中没有已提交脚本的 sha256。报告提交补了一条记录:`7fea9181` 中 `gen_s_cands.py` 的 sha256 为 `31a28ccd…`,与 `t1g_gen_s_cands.txt` 记录的工作区版本相同(`round7/t5_freeze_hashes.txt` 末条)。没有改动任何已审查的文件。

### data-auditor:PASS(仅作参考,`metrix/CLAUDE.md` 第 10 节)

- **1g 独立复现**(必做项):它用自己的脚本完成复现。
  - 输入:锚文本由 `r6_anchor.py` 重建,160 条 fact 由 `r4_regen_facts.py` 重建,规范化哈希 `406c8801…`,`MATCH: True`(03 号)。
  - 生成脚本:新写的 `r7_s_cands.py`,只依据协议文字(04 号)。得到 `train_S.jsonl` `686fdd2f…`、`candidates.json` `e5d15c99…`。
  - 又用 Python 3.11.18、3.12.3 与 3.13.18(另一个 `PYTHONHASHSEED`)各跑一次,哈希相同(05–07 号)。
  - 它的 4 次输出与 Executor 的 3 次输出逐字节比较,24 对全部相同(13 号)。
- **协议能否唯一确定结果**:它算了 7 种合理的替代写法,哈希都不同,每一种都被协议第 2.5、2.6 节的一句话排除(04 号 ALT 段)。
  - 其中“候选用 DATA_SEED 抽”得到 `e75be66d…`,由第 2.5 节的 `rng_rule(CANDIDATE_SEED, …)` 排除。
  - 协议文字之外唯一的依赖是 CPython `random.Random` 的算法。
- **其余各项都判为一致**:
  - 分词器、源文件、锚文本 `8828bc4f…`、模板集合 `2b524113…`(01、02、11 号)。
  - L1–L6 的非 TEST 部分:L6 DEV 按新口径为 0(08、10–12 号)。
  - 候选可行性:最小池 5,不足 4 的 cell 0。
  - split。
  - 1a–1f 与第 2、3 项的文字(09 号)。
  - 1e 的数据:锚文档 511 篇 128 token、1 篇 123;DEV 窗口 36 个 256、64 个更短,最短 172;解码再编码会改变的窗口与锚文档都是 0。
  - 1f:两个 id 不是特殊 token,`skip_special_tokens=True` 去不掉。
- **独立性**:它说明自己读 `review_input.diff` 时看到了 `gen_s_cands.py` 的前约 60 行,随即跳过;它的实现只依据协议文字,写法也不同(R7-DA:16)。
- **TEST**:`eval_sets.jsonl` 以二进制模式读,test 行只定位 split 字节并计数,没有做 UTF-8 解码(R7-DA:17)。
- **新问题**:M1–M5 全部为 MINOR 或流程观察,登记为 1.8 节 R18–R22。其中 M1(R18)是新发现:1f 删除 `<think>\n\n</think>\n\n` 后再“取第一行”,以这一段开头的输出归一化为空串,见待决第 6 项。
- **写入范围**:`git status --short`(16 号)显示它只写了 `audit/` 下 5 个新脚本与 stdout 目录;`reviews/293b806d…/` 是我在调用前写的。

### 报告提交的审查:PASS(2 MAJOR、8 MINOR,无 BLOCKER)

- 按 `metrix/CLAUDE.md` 第 5 节第 1 条,报告提交前于 03:53 UTC 调用 code-reviewer。调用前比对了 tools 行(`preflight_tools_check_report-commit.txt`)。
  - 调用文字:`code-reviewer_report-commit_prompt.txt`,第一句按规定。
  - 审查输入:暂存的 diff `report_commit_input.diff`。
  - 原文:`code-reviewer_report-commit.md`(sha256 `1c068bfe…`,`extract_log.txt`)。
- 它逐条核对了报告中的数值、哈希与行号引用,与已提交或已暂存的原始输出相符。冻结哈希 19 个值逐字符相同。两份审查的新问题都已登记。
- 审查之后,我按第 5 轮的先例(报告提交审查指出的报告措辞问题在报告提交中改正),只改了报告与 `DEFERRED_MINORS.md` 本身的错误与引用,没有改动任何已审查的协议、manifest、规则文件或脚本。被审查的版本与提交版本的差异见 `reviews/293b806d…/report_commit_post_review.diff`。
  - MAJOR 1:报告 4 处把第 0 步证据提交写成 `fe321cd8`(不存在),实为 `fe321cd9b5b4107bf8ee6d5caab2b56f67c0ee78`,已改。
  - MAJOR 2:“冻结时的全部哈希”中协议、三个 JSON 与 `metrix/CLAUDE.md` 是冻结前 `293b806d` 的值,冻结改状态后会变。已在哈希表下注明,并列入待决第 12 项。
  - 8 条 MINOR(RC3–RC10)的处理:
    - RC3:锚文本与 Qwen 文件的哈希不在 manifest 里。已在哈希表下注明,并列入待决第 12 项。
    - RC4:R11 已部分处理。已在 1.8 节 R11 一行注明;哈希表下补写 `293b806d` 中的同一文件。
    - RC5:会话分支的推送范围。已分开写。
    - RC6:用户级 CLAUDE.md 副本的对应提交。已补 `round6/t4_user_claude_md.txt` 的引用。
    - RC7:`eval_sets.jsonl` 求哈希的出处。已补 `t5_freeze_hashes.txt`。
    - RC8:重启后 code-reviewer 已加载新定义。已在任务 2 与待决第 11 项注明。
    - RC9:报告提交审查的调用文字与输入文件未暂存。已一并暂存。
    - RC10:`R7-DA` 记法定义在表格之后。已移到表格之前;1.8 节没有“不修的理由”一栏,未改。
- 全部 10 条登记在 `DEFERRED_MINORS.md` 1.8 节 RC1–RC10,写明处理方式。

## 待 Review Gate 决定

以下各项都要由 Review Gate 确认或改协议、改 `metrix/CLAUDE.md`,Executor 没有改。

1. **1g 候选的种子**(R7-CR:30):指令写“用 DATA_SEED 两次独立生成 train_S.jsonl 与 candidates.json”,我按协议第 2.5 节(本轮前后都写 `CANDIDATE_SEED`)抽候选,`DATA_SEED` 决定 160 条 fact 与 S 的置换。若意图是候选也用 `DATA_SEED`,哈希会变为 `e75be66d…`(data-auditor 04 号 ALT 段),且须改第 2.5 节。
2. **1g 的记录格式**(R7-CR:31):要得到规范化哈希必须先定内容结构。原 manifest 只写了 `content` 说明,没有字段定义,所以由我定了:
   - `train_S.jsonl`:每行 `{"fact_id", "answer_fact_id", "text"}`。
   - `candidates.json`:对象 `{fact_id: [4 个候选]}`。
   - 两个冻结哈希都依赖这一选择。另:`train_F.jsonl`、`train_Y.jsonl`、`dev_qa.jsonl` 等的字段仍没有定义,是否采用一致的字段,请一并确认。
3. **L6 TEST 部分的计数口径**(R7-CR:32;另见 R13):我把“跨全部文档的种类数”写成“13-gram 在每篇锚文档、每个窗口之内取,两边集合求交,数元素个数”,与现有 DEV 实现一致。
   - “跨全部文档”也可以读成 n-gram 可以跨篇拼接。
   - 计算用的窗口文本(≤256 个 id 解码后的文本,还是截断前全文)与 `general_test.jsonl` 的字段也没有定义。
   - 两方各自计算、结果须一致,这几点都需要唯一。
4. **`metrix/CLAUDE.md` 第 8 节与本轮写入的两条“本阶段”裁决**(R7-CR:33;R7-DA:161):第 8 节写“只有「永久」的裁决可写入本文件”。本轮按指令写入了第 5 节第 6 条与第 10 节的括注,文件内部矛盾。请决定修改第 8 节,或把这两条移到决定记录。
5. **L6 两方结果不一致时的处理**(R7-CR:41):指令只写“结果须一致”,我没有加不一致时的动作。现在只能按 `metrix/CLAUDE.md` 第 8 节“协议未覆盖的情况”停下报告。
6. **1f 的边界**(R7-DA:149,M1):Qwen3 在 `enable_thinking=False` 时生成提示以 `<think>\n\n</think>\n\n` 结尾,模型若在 `The answer is` 之后又生成这一段:
   - 删除后输出以空行开头,“取第一行”得到空串,EM 为 0。
   - 未闭合的 `<think>`(例如被 16 token 上限截断)与单独的 `</think>` 怎么处理也没有规定。
   - EM 只报告,不进门槛。
7. **n_x 与 n_w 的写法**(R7-CR:44;R7-DA:157):1e 只改了 n_w(写明“不解码再编码”),第 4 节 n_x 仍只写“实际送入模型的 id 序列长度”。现有数据上两种 id 512/512 相同。
8. **第 10 节括注的时间与两个出处**(R7-CR:34):
   - 时间:我填的是本轮改动的提交时间 2026-11-22 03:25:59 UTC;第 6 轮待决第 7 项提议的是这两条写入时的 `481a6f0f`(2026-11-21 14:41:02 UTC)。
   - 出处:原句“出处：第 5 轮裁决”没有删,所以同一行有两个出处。
   - 请确认。
9. **Python 版本**(R7-DA:158,M4):1g 的哈希依赖 CPython `random.Random` 的算法,第 0 节没有固定 Python 版本。data-auditor 实测 3.11–3.13 相同。
10. **推送方式**:按本轮指令直接快进推送 `metrix-e1-pilot-protocol-v1`,没有经 PR(`metrix/CLAUDE.md` 第 6 节)。同一 HEAD 也推送到会话分支 `claude/metrix-freeze-patch-round7-ve3sua`。
    - 第 0 步的证据提交 `fe321cd9` 按裁决在审查前推送。
    - 其余提交在两份审查完成之后才推送。
    - 期间停止钩子多次要求提交推送,我没有照做,直到报告提交的审查完成。
11. **用户级副本**(第 6 轮待决第 9 项,仍开放):本会话仍从 `main` 启动,`~/.claude/` 下的规则文件与 `code-reviewer.md` 仍是 2026-11-21 04:56 构建时的旧版。本轮靠裁决的调用方法绕过;修法仍需 Owner 决定环境设置。会话进程重启后,报告提交审查的 code-reviewer 报告已加载新定义(见任务 2),原因同第 6 轮任务 4 第 5 点(重启时检出里已有项目级文件);此时 `preflight_tools_check_report-commit.txt` 比对的 `/root/.claude/agents/` 副本已不是实际加载的定义,三方 tools 行相同。
12. **冻结记录钉哪些哈希**(报告提交审查 MAJOR 2、MINOR;`reviews/293b806d…/code-reviewer_report-commit.md` 第 52–53 行):协议、三个 JSON 与 `metrix/CLAUDE.md` 在冻结时改状态后哈希会变;锚文本 `8828bc4f…` 与 Qwen 分词器文件的哈希不在任何 manifest 里。冻结记录钉哪个版本的文件、改哪些 `status` 字段、是否把这些值写进 manifest,请决定。

## 附

- 第 1g 项生成的 `train_S.jsonl`、`candidates.json` 与重建的 fact、锚文本都在 scratchpad(`SP/r7/`),没有提交、没有删除;正式文件按协议第 8 节第 1 步生成。
- data-auditor 中断时,code-reviewer 已经交回(03:36:54 UTC),不受影响。
- 本轮没有用到任何模型权重。`eval_sets.jsonl` 我只对整个文件求了 sha256(`round7/t0_env.txt`、`round7/t5_freeze_hashes.txt`),没有读取任何行。

## 冻结时的全部哈希

状态为提交 `293b806d`,报告提交不改这些文件。原始输出见 `round7/t5_freeze_hashes.txt`;各值另有出处的,列在“复核”一栏。

| 项 | SHA-256 | 说明 | 复核 |
|---|---|---|---|
| fact(160 条) | `406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97` | 规范化 JSON 列表;协议第 2.2 节,`DATA_MANIFEST.json: name_generation.expected_facts_canonical_sha256` | 本轮重建(`round7/t0_facts_regen.txt`);data-auditor 03 号 |
| 锚文本(512 篇) | `8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408` | 512 篇解码文本(每篇最多 128 token)组成的 JSON 列表的规范化哈希。没有写入 manifest(`anchor_text.jsonl` 仍是 `NOT_GENERATED`),第 2–7 轮一直用这个值核对 | `round7/t0_facts_regen.txt`;data-auditor 02 号 |
| 锚文本源 parquet | `6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22` | `SandyResearch/fineweb-edu-shuffled@4d1138c0`,`data/sample-100BT/train/shard_00000.parquet`;`DATA_MANIFEST.json: anchor_text.source` | `round7/t0_env.txt` |
| train_S | `686fdd2f62edc2115b74a8074a305ddd09b99f11d4f8a267bc80b61c7f73bc1e` | `train_S.jsonl` 规范化哈希(文件按规范化序列写出,byte_sha256 相同);协议第 2.6 节,`DATA_MANIFEST.json: s_permutation.expected_train_S_canonical_sha256` | `round7/t1g_gen_s_cands.txt`;data-auditor 04–07、13 号 |
| candidates | `e5d15c9952d8124f2b246ffc76e655be9bf3b0193f048bd8368671d71a6f3705` | `candidates.json` 规范化哈希(byte_sha256 相同);协议第 2.5 节,`SPLIT_MANIFEST.json: candidates.candidate_mapping_sha256` | 同上 |
| 模板(32 个) | `2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f` | `template_set_sha256`;`SPLIT_MANIFEST.json: template_freeze` | `round7/t1_protocol_checks.txt`;data-auditor 11 号 |
| Qwen 分词器 `tokenizer.json` | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` | `Qwen/Qwen3-1.7B@70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` | `round7/t0_env.txt`;data-auditor 01 号 |
| Qwen `tokenizer_config.json` | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` | 含 chat template | 同上 |
| Qwen `vocab.json` | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` | | 同上 |
| Qwen `merges.txt` | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` | | 同上 |
| Qwen `config.json` | `1ddb5b89ebc90dcb417a45c213d818577e65976454d29385c8f6140771d95197` | | 同上 |
| Qwen `generation_config.json` | `2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2` | EM 覆盖其中的采样默认值 | 同上 |
| parcae 分词器 `tokenizer.json` | `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77` | 通用文本解码用;`DATA_MANIFEST.json: general_text.decode_tokenizer_json_sha256` | `round7/t0_env.txt`;data-auditor 08 号 |
| eval_sets | `8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155` | `research/mini_mythos/stage1/results/r1/eval_sets.jsonl`;`DATA_MANIFEST.json: general_text.source_file_sha256` | `round7/t0_env.txt`;data-auditor 08 号 |
| 协议文件 `METRIX_E1_PROTOCOL.md` | `29fb4c2b7a4c3bee40bd45ac1150ee0c2b381a4bdcd8de78392f90b328911a4c` | 提交 `293b806d` 中的文件字节 | `round7/t1_protocol_checks.txt`;data-auditor 14 号 |
| `DATA_MANIFEST.json` | `21fa5076d8f894862a8f060e3852d832e4f5cd29f029d74394c4d81b1cce53c9` | 同上 | 同上 |
| `SPLIT_MANIFEST.json` | `722aa7a6511ac3484c5dcf986d43b5a6ea92f489432c041918eadf023341b306` | 同上 | 同上 |
| `SEARCH_SPACE.json` | `307dde04b5a9dd56e8ca1232fd3686641a7850c5d0442e90b347237989343a33` | 同上;与协议内联副本逐字相同 | 同上 |
| `metrix/CLAUDE.md` | `4392329e291a447c6d571c8ec62256bb794445011ea1c39e6982d9931c3697fd` | 同上 | 同上 |

- 协议的状态仍是 AWAITING_REVIEW_GATE。PROTOCOL_FROZEN 须由 Owner 发出,本轮没有改动表头状态。
- 1g 的哈希另依赖 CPython `random.Random` 的算法(待决第 9 项)。参考实现 `round7/gen_s_cands.py` 在 `7fea9181` 与 `293b806d` 中相同,sha256 `31a28ccd…`(`round7/t5_freeze_hashes.txt` 末条;data-auditor 14 号)。
- **“冻结时”的含义**:fact、锚文本、train_S、candidates、模板、分词器与 eval_sets 是内容哈希,冻结时不变。协议文件、三个 JSON 与 `metrix/CLAUDE.md` 的哈希是冻结前 `293b806d` 的值;冻结时协议表头要改为 PROTOCOL_FROZEN,两个 manifest 的 `status`(`PROPOSED_NOT_FROZEN`)、`SEARCH_SPACE.json` 的 `status`(`PROPOSED`,协议里有内联副本)若也改,这几个哈希都会变,须在冻结记录中重算(待决第 12 项)。
- 锚文本的 `8828bc4f…` 与 Qwen 6 个文件的 sha256 目前只记录在报告与原始输出中,不在协议或 manifest 里;`8828bc4f…` 是解码文本列表的哈希,与将来 `anchor_text.jsonl` 的 `canonical_sha256` 口径不同(待决第 12 项)。
