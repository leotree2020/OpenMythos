# E1-PILOT 第 6 轮报告

- 指令:`tasks/ROUND6_TASKS.md`(Owner 2026-11-21 下达,原文照录)。本轮允许快进推送 `metrix-e1-pilot-protocol-v1`,不得 force push。原则:只修影响数据、指标、门槛或可复现性的问题;其余 MINOR 只登记不修。报告提交不需要 code-reviewer 审查。
- 执行会话:session_01J5mxaY5Chc3QrL468Vrs7f。会话分支 `claude/metrix-protocol-round6-9mq9ya` 原先停在 `main` 的 `155430a`,开始时快进到第 5 轮的 `f4d8e988`(没有改写历史)。
- 运行环境(`round6/t0_env.txt`):Claude Code on the web 云容器,hostname `vm`,4 CPU,15 GiB 内存,无 GPU(`command -v nvidia-smi` 退出码 1),Ubuntu 24.04.5,Python 3.13.18。venv:transformers 5.22.2、tokenizers 0.23.3、jinja2 3.1.6、pyarrow 26.0.1、huggingface_hub 2.4.0;`import torch` 失败(未安装)。
- 下载内容:Qwen/Qwen3-1.7B@70d244cc 的分词器与配置文件 6 个、parcae-tokenizer@6247b5d0 的 `tokenizer.json`、锚文本源 parquet。8 个文件的 sha256 与第 5 轮逐个相同(`round6/t0_env.txt` 末条 `diff` 退出码 0);没有任何权重文件。
- 没有训练,没有评测,没有生成或读取 TEST 数据(按本轮新定义,第 1g 项):`eval_sets.jsonl` 的 test 行只用正则从行首读出 `split` 字段并计数(正则会扫过行首的 domain 值,不使用、不输出),没有做 JSON 解析,也没有解码;另对整个文件求了 sha256。这一做法是否完全在定义之内,见待决第 10 项。
- 提交(都在 `metrix-e1-pilot-protocol-v1` 上,父提交为第 5 轮的 `f4d8e988`):

| 提交 | 时间(UTC) | 内容 |
|---|---|---|
| `481a6f0f` | 2026-11-21 14:41:02 | 任务 1–4 的工作提交(第 14 节 v1-r6 各行的时间与提交是占位符) |
| `599230f9` | 2026-11-21 14:41:14 | 第 14 节 v1-r6 九行填入 `481a6f0f` 与时间;`round6/t1_commit_times.txt` |
| `2620f306` | 2026-11-22 02:27:07 | data-auditor BLOCK 之后的修复:`guard_ab.sh`、`guard_fail.sh` 加 EXIT trap、参数检查与 RESULT 行;`round6/t2_guard_normal_rerun.txt`、`t2_guard_fail_rerun.txt`、`t2_harness_fail.txt` |
| 报告提交 | — | 本报告;`DEFERRED_MINORS.md`;`reviews/599230f9…/` 与 `reviews/2620f306…/` 下的审查原文、调用文字、审查输入与中断记录;data-auditor 的脚本(`audit/r6_*.py`、`audit/r6b_*.py`、改过的 `audit/r5_kl_denoms.py`)与 `audit/stdout/599230f9…/`、`audit/stdout/2620f306…/`;审查之后补的证据(`round6/t1_protocol_checks_599230f9.txt`、`t2_harness_fail_*.out.txt`、`t2_harness_fail_outputs.txt`、`t4_after_restart.txt`)与 `round6/review_extract.py`。哈希见最终回复(提交无法包含自身哈希) |

- 原始输出在 `reports/round6/`。命令行由 `round5/logrun.sh` 记录(`printf %q` 转义)。`SP` 指本会话 scratchpad,放下载的文件、venv 与中间数据(fact、锚文本、general DEV 窗口)。

## 结论一览

| 任务 | 状态 | 证据 |
|---|---|---|
| 1 协议修改 a–i | 完成;第 14 节 v1-r6 九行 | 协议第 0、2.7、3、4、5、7、8、14 节;两个 manifest;`round6/t1_*.txt` |
| 2 脚本 | 完成。L6 DEV 部分按 `str.split()` 判定 PASS(13-gram 共享 0),test 行解码数 0(实际计数);14 个检查脚本遇异常都打印 `RESULT: FAIL` 并非 0 退出,正常路径输出与改动前逐字节相同(8 个可运行的全部核对)。其中 2 个 bash 脚本在工作提交中漏了,data-auditor 判 BLOCK 后由修复提交 `2620f306` 补上 | `round6/t2_*.txt` |
| 3 metrix/CLAUDE.md 与 code-reviewer 定义 | 完成。**第 1 轮审查的 code-reviewer 用的是旧定义**;容器重启后调用的第 2 轮 code-reviewer 报告已用新定义(都是它自己的陈述,见任务 3、4) | `metrix/CLAUDE.md` 第 10 节;`.claude/agents/code-reviewer.md` 末行 |
| 4 用户级 CLAUDE.md 为何是旧版本 | 查明:本会话的文件系统(含 setup script 的输出)在 04:56:35 UTC 就已准备好,比会话创建早 9.5 小时;会话启动时 setup script 没有再运行。修法见任务 4,没有改环境设置 | `round6/t4_user_claude_md.txt` |
| 5 两个审查 | 第 1 轮(`f4d8e988..599230f9`):code-reviewer **PASS**(10 MAJOR、10 MINOR),data-auditor **BLOCK**(漏了 2 个 bash 检查脚本)。修复提交 `2620f306` 后第 2 轮:code-reviewer **PASS**(2 MAJOR、3 MINOR),data-auditor **PASS**。`r5_kl_denoms.py` 的 128 已由 auditor 改为从数据计算。data-auditor 的 PASS 按第 10 节仅作参考 | `reviews/599230f9…/`、`reviews/2620f306…/` |
| 6 登记不修的 MINOR | 完成 | `reports/DEFERRED_MINORS.md` |
| 7 报告与推送 | 本文件 | — |

## 任务 1:协议修改

| 项 | 落地位置 | 新文字(摘) |
|---|---|---|
| 1a | 第 3 节 L6 一行;`SPLIT_MANIFEST.json: leakage_checks.L6_general_text`(`rule` 改写,新增 `report_only`) | “‘词’= Python `str.split()` 的结果(按空白切分,区分大小写);Qwen token 13-gram 只报告,不设上限”;上限 0 不变 |
| 1b | 第 2.7 节;`DATA_MANIFEST.json: general_text.window_rule`(新增) | “再用本协议的分词器切分;每个窗口最多 256 token(取前 256 个),不足则取全长” |
| 1c | 第 4 节 arm A 损失 | “n_x 为锚文档 x 实际送入模型的 id 序列长度” |
| 1d | 第 5 节 EM;第 0 节“生成输入(EM)”;`DATA_MANIFEST.json: model.input_convention.em_generation` | “`do_sample=False`,每步取概率最大的 token;这一设置写死,覆盖固定 revision 的 `generation_config.json` 中的采样默认值(`do_sample` true、`temperature` 0.6、`top_k` 20、`top_p` 0.95)”;删去“输出先去掉开头的空格,再归一化”,“去首尾空白(输出开头的空格在这一步去掉)”;`EM(f, q) = 1[norm(output) == norm(a_f)]` |
| 1e | 第 5 节 `s_ST`;`DATA_MANIFEST.json: model.input_convention.train_closed_book`(新增) | `prefix(f)` “……不含答案前的空格(该空格属于 c'),前面不加任何特殊 token” |
| 1f | 第 8 节第 8 步、G0.1;第 3 节执行接口与 `SPLIT_MANIFEST.json: leakage_checks.test_split` 各加一句指向第 8 步 | 第 8 步:“L6 的 TEST 部分(锚文本对 `general_test.jsonl`):在 PROTOCOL_FROZEN 之后、TEST 评测之前,由 data-auditor 运行一次,只输出计数”;G0.1:“L6 在 Gate 0 只要求 DEV 部分(锚文本对 `general_dev.jsonl`),TEST 部分按第 8 步运行” |
| 1g | 第 3 节新增一条;第 7 节“TEST 在最终冻结前不可读取”后加“(“读取”的定义见第 3 节)” | “解码 test 行的内容,或用其内容做任何计算。解析 `split` 字段、计数、对整个文件求哈希不算。test 行指任何来源中属于 TEST split 的行,例如 `eval_sets.jsonl` 中 `split == "test"` 的行” |
| 1h | 第 2.7 节(缩写);`DATA_MANIFEST.json: general_text.source_file_sha256`、`decode_tokenizer_json_sha256`(新增) | `eval_sets.jsonl` `8816fe5a39d8b89e8c4203bf7d660e798faa471d2b72b5ce43c411cf5925a155`;parcae `tokenizer.json` `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77` |
| 1i | 第 0 节“通用文本与锚文本输入”;第 14 节 v1-r4 第 2 行 | 两处 `<\|endoftext\|>` 的竖线改为转义;文字不变 |

- 第 14 节:9 行 v1-r6,每项一行,写明原文、新文与原因(对应的第 5 轮待决编号)。时间与提交在 `481a6f0f` 中是占位符,由 `599230f9` 填入(`round6/t1_commit_times.txt`)。
- 核对(`round6/t1_protocol_checks.txt`):
  - 表格:`round6/table_check.py` 逐行数单元格(按未转义的 `|` 切分),145 行全部与表头列数相同,未转义的特殊 token 0,`RESULT: PASS`。同一脚本对 `f4d8e988` 的协议报出第 37、651 行两处,`RESULT: FAIL`,说明检查能查出这一问题。
  - 三个 JSON 可解析;`SEARCH_SPACE.json` 与协议内联副本逐字相同;`template_set_sha256` 重算相同。
  - manifest 与 `f4d8e988` 相比的叶子差异:`DATA_MANIFEST.json` 新增 4 个键(`general_text.source_file_sha256`、`general_text.decode_tokenizer_json_sha256`、`general_text.window_rule`、`model.input_convention.train_closed_book`),改 1 个(`em_generation`);`SPLIT_MANIFEST.json` 新增 `L6_general_text.report_only`,改 `L6_general_text.rule` 与 `test_split`;`SEARCH_SPACE.json` 无差异。
  - `outside_metrix_check.py --rev 481a6f0f`:`RESULT: PASS`(`round6/t1_commit_times.txt`)。
- fact 与锚文本不变:重跑 `gen_facts.py` 仍为 `406c8801…`,锚文本 `8828bc4f…`;L3a、L3b 仍为 0(`round6/t0_facts_regen.txt`)。
- 措辞上我做的取舍(请 Review Gate 核对是否符合本意):
  - 1b 加了“(取前 256 个)”,原文“截到”已含此意。
  - 1d 列出了 `generation_config.json` 的四个采样默认值,数值取自固定 revision 的该文件(`round6/t0_env.txt` 中其 sha256 `2325da0f…` 与第 5 轮相同)。
  - 1f“只输出计数”我理解为:不输出任何共享 n-gram 的内容,以免露出 TEST 文本。计数大于 0 时怎么处理,指令与协议都没有写,见待决第 2 项。
  - 1g 的“test 行”我补了“任何来源中属于 TEST split 的行”这一说明,并举 `eval_sets.jsonl` 为例。
  - 1c 只改了 n_x;第 5 节 general damage 的 n_w(“窗口的 token 数”)有同样的歧义,没有改,见待决第 4 项。

## 任务 2:脚本

### l6_check.py

改动(`reports/round5/l6_check.py`,原地修改;docstring 注明第 6 轮的改动):

- **判定按 1a**:只看 `ws` 单位(`str.split()`,区分大小写);`w`(`\w+`,casefold)与 `tok`(Qwen token id)只打印,不进判定。
- **test 行**:每行只用正则读出开头的 `split` 字段(`{"domain": "…", "split": "…", ` 是 Stage 1 `build_data.py` 写出的行首格式;不匹配即中止并 `RESULT: FAIL`)。只有 dev 行才做 `json.loads`;只有保留的 dev 行才解码。
- **“test rows decoded” 改为实际计数**:解码只经过 `decode_parcae()`,它按该行的 split 计数;打印各 split 的解码数,非 dev 的解码数不为 0 即中止。
- **sha256 按 manifest 核对**(1h):`eval_sets.jsonl` 与 parcae `tokenizer.json` 的 sha256 必须等于 `DATA_MANIFEST.json: general_text` 的两个值,否则中止。原来的 `--data-lock` 参数换成 `--manifest`。
- 循环变量 `split` 改名为 `units_of`(函数里新增了真正的 `split` 变量)。

结果(`round6/t2_l6_check.txt`):

```
eval_sets rows by split: {'dev': 400, 'test': 800}
dev windows kept per domain: {'books': 25, 'c4': 25, 'fineweb': 25, 'wikitext': 25} | other domains: []
rows decoded by split: {'dev': 100} | test rows decoded: 0
unit ws  | units: anchor 50413, general 18983 | shared n-grams n=1..13: [2878, 2178, 454, 68, 14, 5, 3, 2, 1, 0, 0, 0, 0] | longest shared n <= 13: 9
unit w   | units: anchor 51199, general 18521 | shared n-grams n=1..13: [2858, 2718, 606, 94, 21, 6, 4, 2, 1, 0, 0, 0, 0] | longest shared n <= 13: 9
unit tok | units: anchor 65531, general 24877 | shared n-grams n=1..13: [3784, 3467, 1030, 270, 106, 25, 8, 5, 4, 3, 2, 1, 0] | longest shared n <= 13: 12
L6 (DEV part) shared word 13-grams (word = str.split(), unit ws): 0; limit 0
report only, no limit: unit w 13-grams 0; Qwen token 13-grams (unit tok) 0
RESULT: PASS
```

- 各单位的计数、窗口长度分布、两个 general DEV 哈希(`363aa087…`、`2e30c443…`)、锚文本哈希与各 domain 的选取,都与第 5 轮 `t5_l6_check.txt` 相同(同一文件末条 `diff` 退出码 0)。
- 1b 的长度分布:100 个窗口中 36 个正好 256,64 个更短(172–255),没有超过 256 的。
- **判定只看 `str.split()` 的演示**(`round6/t2_l6_judgment_demo.txt`;`round6/l6_judgment_demo.py` 只在 scratchpad 写两份改过的锚文本副本):
  - 在锚文档 0 末尾加上 general DEV 窗口 0 的前 13 个词:`ws` 13-gram 1、`w` 2、tok 6 → `RESULT: FAIL`,退出码 1。
  - 只加前 12 个词(第 2–12 个词共 13 个 Qwen token):`ws` 0、`w` 1、tok 5 → `RESULT: PASS`,退出码 0。按第 5 轮的判定(三种单位都要为 0),这一份会 FAIL。

### 遇异常打印 RESULT: FAIL

- **范围**:我把“检查脚本”理解为输出通过/不通过判定的脚本(`RESULT` 行、PASS/FAIL 或 inside/OUTSIDE 字样,或按判定设置退出码)。按这个标准共 14 个:12 个 Python 脚本加了 `run_guarded`(下一行),2 个 bash 脚本见再下一行。
  - `round1/template_overlap.py`(L1、L2)、`round2/anchor_check.py`(L3)、`round2/y_ratio.py`(Y/F 比)、`round3/candidate_feasibility_r3.py`、`round3/outside_metrix_check.py`、`round3/verify_scoring.py`、`round4/st_prefix_check.py`、`round5/l6_check.py`、`round5/blind_handback_check.py`、`round5/recover_blind.py`、`round5/records_check.py`,以及本轮新写的 `round6/table_check.py`。
  - 本轮新写的两个 bash 脚本 `round6/guard_ab.sh`、`round6/guard_fail.sh` 也按判定设置退出码,同样属于检查脚本。工作提交中漏了它们(data-auditor BLOCK,见任务 5);修复提交 `2620f306` 给它们加了 EXIT trap、参数个数检查和最后的 RESULT 行。加上这两个,共 14 个。
  - 没有加的 7 个,都不输出判定:`round1/candidate_feasibility.py`(只报计数,已由 `candidate_feasibility_r3.py` 取代)、`round1/param_count.py`、`round2/gen_facts.py`、`round2/names.py`(模块)、`round3/scoring_input.py`(模块)、`round4/anchor_short_docs.py`、`round5/em_special_tokens.py`。本轮的 `round6/l6_judgment_demo.py` 只生成演示输入,也不输出判定。`round5/logrun.sh` 只把被包装命令的退出码原样传出,不输出判定,也不算(第 2 轮 data-auditor 指出这里原先漏列了它)。本轮新写的 `round6/review_extract.py` 只复制审查原文、打印 sha256,也不输出判定。
  - auditor 的脚本不在范围内(Executor 不改 auditor 的文件);是否也适用,见待决第 6 项。
- **做法**:每个脚本末尾加同一个 `run_guarded(main)`,`if __name__ == "__main__":` 改为调用它(`records_check.py` 原来没有 `main()`,把原来的两行移进 `main()`)。
  - 任何异常:打印 traceback,再打印 `RESULT: FAIL`,退出码 1。
  - 在 RESULT 行之前退出(`sys.exit("原因")` 或 argparse 报错):打印原因与 `RESULT: FAIL`,退出码 1(argparse 为 2)。
  - `main()` 自己给出的退出码 0 与 1 原样通过:这些脚本都是先打印判定、再以 0 或 1 退出。
- **正常路径不变**(`round6/t2_guard_normal.txt`,`round6/guard_ab.sh`):把 `f4d8e988` 的 `reports/` 用 `git archive` 取出,8 个脚本新旧两版用同样的参数各跑一次,stdout+stderr 与退出码逐字节相同,8/8。
  - 没有 A/B 的:`l6_check.py`(本轮改了逻辑,已与第 5 轮输出比对)、`blind_handback_check.py` 与 `records_check.py`(输入是第 4 轮的事件页和第 5 轮的 subagent 记录,不在本容器)。这两个脚本的改动只在 `if __name__` 块与新加的函数,见审查输入 diff。`table_check.py` 是新脚本。
- **异常路径**(`round6/t2_guard_fail.txt`,`round6/guard_fail.sh`):11 个改动的脚本新旧两版用同样的失败参数各跑一次(缺输入文件、git 报错、argparse 报错),另加 `l6_check.py` 的 sha256 不符(`sys.exit("…")` 路径)。新版 12/12 非 0 退出且恰有一行 `RESULT: FAIL`;旧版都没有 `RESULT` 行。新旧退出码相同。
- **修复提交 `2620f306` 之后**(两个 bash 脚本也是检查脚本,见“范围”):
  - 重跑 `guard_ab.sh`(`round6/t2_guard_normal_rerun.txt`):8/8 相同,最后一行 `RESULT: PASS`,退出码 0。
  - 重跑 `guard_fail.sh`(`round6/t2_guard_fail_rerun.txt`):12/12,最后一行 `RESULT: PASS`,退出码 0。
  - 两个脚本自身的失败路径(`round6/t2_harness_fail.txt`):参数个数不对时打印用法和 `RESULT: FAIL`,退出码 2;OLD 目录不存在时 `guard_ab.sh` 0/8 相同,`RESULT: FAIL`,退出码 1;解释器不存在时 `guard_fail.sh` 0/12,`RESULT: FAIL`,退出码 1。该文件前两次失败演示经过管道,记录的 `exit=` 是 grep 的退出码;文件里已注明,并补了不经管道、记录脚本自身退出码的两次运行。

## 任务 3:metrix/CLAUDE.md 与 code-reviewer 定义

- `metrix/CLAUDE.md` 第 10 节:两条原文不变(code-reviewer「已验证」,data-auditor「待验证」),加一行“以上两条的出处：Review Gate 第 5 轮裁决。”
- `.claude/agents/code-reviewer.md`:末尾追加一行“未实际运行就作出的判断须标注『未验证』。”(用 `git add -f` 暂存;`outside_metrix_check.py --rev 481a6f0f` PASS)。
- 记录(按 metrix/CLAUDE.md 开头的要求):时间为提交 `481a6f0f`(2026-11-21 14:41:02 UTC);原因与出处见第 6 轮指令第 3 项。**作用范围**指令没有写;第 8 节规定只有「永久」的裁决可写入本文件,所以暂按「永久」处理,请 Review Gate 确认(待决第 7 项)。
- **第 1 轮审查时新规则没有生效。** 第 1 轮的 code-reviewer 用的是会话启动时装进 `~/.claude/agents/` 的定义(`f4d8e988` 及更早版本,sha256 `bf66a0d6…`,没有新加的这一句;`round6/t4_user_claude_md.txt`)。启动时的检出是 `main`,其中没有 `.claude/agents/`,所以没有项目级定义可加载。code-reviewer 在审查开头确认了这一点:它加载的定义最后一行是“不确定是否为问题时，列为 MAJOR 并说明不确定之处，不要省略。”,没有新加的这一句(`reviews/599230f9…/code-reviewer.md` 第 10 行)。调用文字里另外要求它按这一句执行,它照做了:每条判断末尾都标了『未验证』。容器在 2026-11-22 02:16 重启后,用户级副本仍是旧版本(`round6/t4_after_restart.txt`)。
- **重启之后新调用的 code-reviewer 报告它加载的定义已含这一句**(`reviews/2620f306…/code-reviewer.md` 第 12 行)。重启时会话的检出已是 `599230f9`,其中有 `.claude/agents/code-reviewer.md`(新版);重启后加载的指令文件也换成了仓库里的 `CLAUDE.md` 与 `metrix/CLAUDE.md`。第 1 轮那个 code-reviewer 是从中断处续做的,沿用 14:42 启动时的定义。两种情况都只有 subagent 自己的陈述:transcript 中两句话都出现过(调用文字与读到的文件里都有),不能用来判别加载的是哪一份。原因与修法见任务 4。

## 任务 4:为什么 /root/.claude/CLAUDE.md 是旧版本

证据(`round6/t4_user_claude_md.txt`,只读命令;会话与环境的元数据取自本会话的工具结果,原样抄在文件末尾):

| 时间(UTC) | 事件 | 依据 |
|---|---|---|
| 2026-11-12 16:06:25 | `metrix-e1-pilot-protocol-v1` 推送到 `7e5dd9c0`;下一次推送在 11-21 05:42:34 | GitHub activity API |
| 2026-11-21 04:56:34 | 本容器里的两个仓库被克隆,检出 `main` | `git reflog HEAD`;`.gitignore` 等文件的创建时间 |
| 2026-11-21 04:56:35 | `git fetch origin metrix-e1-pilot-protocol-v1` 取到 `7e5dd9c` | `refs/remotes/origin/metrix-e1-pilot-protocol-v1` 的 reflog:`fetch origin metrix-e1-pilot-protocol-v1: storing head`,与 setup script 的 fetch 命令一致 |
| 2026-11-21 04:56:35.33 | `~/.claude/CLAUDE.md` 与两个 agent 文件创建 | `stat`;内容 sha256 `a24f6f3d…` = `8ce8c896` / `7e5dd9c0` 的 `metrix/CLAUDE.md` |
| 05:42:34、11:05:53 | 第 4、5 轮的改动推送(`metrix/CLAUDE.md` 在 `b1f5889c`、`c73f41a3` 中改过) | GitHub activity API;`git log` |
| 14:24:54 | 本会话创建 | `get_session` |
| 14:24:55–59 | 虚拟机启动;会话分支检出;`~/.claude/backups`、`session-env` 等会话文件创建 | `uptime -s`;`git reflog HEAD`;`stat` |

**原因**:

1. 环境 “metrix” 的 setup script 在容器构建时把 `metrix-e1-pilot-protocol-v1` 当时的 tip 中的 `metrix/CLAUDE.md` 和两个 agent 文件复制到 `~/.claude/`。它只在构建时运行一次。
2. 本会话用的文件系统在 04:56:3x 就已经构建好(克隆、setup script 都在那时完成),比会话创建早 9.5 小时。会话启动时只检出了会话分支,setup script 没有再运行。那时的 tip 是 `7e5dd9c0`,所以复制进来的是第 4 轮之前的文本。
3. 第 4、5 轮会话的副本修改时间也是 04:56:35(第 4 轮 `round4/t3_claude_md_copies.txt` 为 04:56:35.158793759,本轮为 04:56:35.338916083,第 5 轮只记到秒)。三个会话用的文件系统都是在 04:56 前后构建的。平台为什么在那时构建、之后的会话是不是复用预先构建的容器,从容器里看不到,**这是推断**。
4. 会话从 `main` 启动(`get_session` 的 source 是 `refs/heads/main`)。`main` 里没有 `CLAUDE.md`、`metrix/CLAUDE.md` 与 `.claude/agents/`,所以启动时只有这份用户级副本可加载。我把会话分支快进到 `f4d8e988` 之后,读 `metrix/` 下的文件时项目里的 CLAUDE.md 才被加载;subagent 的定义仍是启动时加载的用户级旧版本(任务 3)。
5. 02:16 容器重启后,setup script 仍没有再运行(用户级副本不变,`round6/t4_after_restart.txt`)。但这次启动时检出里已有项目级文件:重新加载的指令文件是仓库里的两份 CLAUDE.md,重启后新调用的 code-reviewer 报告它的定义含新句(任务 3)。这与修法 1 的思路一致:只要会话启动时检出的就是 Metrix 分支,项目级文件就会被加载。

**修法建议(没有改任何环境设置)**:

1. **(推荐)从 `metrix-e1-pilot-protocol-v1` 分支启动 Metrix 会话,并去掉 setup script 中复制这三个文件的部分。** 检出的分支里就有根目录 `CLAUDE.md`(它 `@` 引用 `metrix/CLAUDE.md`)与 `.claude/agents/`,Claude Code 启动时按项目级文件加载,不再依赖构建时的副本,也不会有新旧两份并存。需要在新会话里验证一次:启动后先比对 `git rev-parse HEAD` 与 `git ls-remote origin metrix-e1-pilot-protocol-v1`,并让 code-reviewer 引用它定义的最后一行。
2. 如果要保留用户级副本:让 setup script 在副本末尾写明来源提交(例如加一行“安装自 <hash>”),并在每轮开始时由 Executor 比对副本与远端 tip 的 sha256,不一致就先报告。这只能发现问题,不能保证加载的是新版本。
3. 不推荐只改动 setup script 来触发重建:即使重建,副本仍只反映构建那一刻的 tip,下一轮推送之后又会过期。

环境设置的修改须由 Owner 决定(待决第 9 项)。

## 任务 5:审查

### 第 1 轮:工作提交 `f4d8e988..599230f9`(`reviews/599230f9…/`)

- **调用**:两个 subagent 于 2026-11-21 14:42 并行调用,调用文字 `code-reviewer_prompt.txt`、`data-auditor_prompt.txt`,审查输入 `review_input.diff`(git log、`--stat` 与完整 diff)。
- **中断与续做**:14:49 两个都因额度用尽(HTTP 429)中止,没有交出报告(`interruption.txt`)。2026-11-22 02:16 容器重启后,我用 SendMessage 让它们从中断处续做(文字见 `resume_message.txt`),没有重新开始。
- **审查原文**:`code-reviewer.md`、`data-auditor.md`,由 `round6/review_extract.py` 取 subagent 记录中 `SubagentHandback` 调用的 `message`,原样写在分隔线下;该脚本打印了每份原文的 sha256。
- **code-reviewer:PASS**。10 条 MAJOR、10 条 MINOR,不含 BLOCKER。
  - 它说明自己加载的定义没有新句,但按调用文字执行了:每条末尾都标『未验证』,并注明“文本对照”或“行为推断”。
  - 10 条 MAJOR 都要改协议、改 auditor 文件或由 Review Gate/Owner 决定,Executor 没有改,全部列入下面的“待 Review Gate 决定”第 1–8 项。
  - 10 条 MINOR 登记在 `DEFERRED_MINORS.md` 1.4 节。其中“表格检查没有在 `599230f9` 上重跑”一条,已在报告提交中补跑:`round6/t1_protocol_checks_599230f9.txt`,145 行 PASS,占位符 0。
- **data-auditor:BLOCK**(仅作参考,第 10 节)。
  - A–D 全部与 Executor 一致。它从 parquet 与 `eval_sets.jsonl` 自建锚文本与 general DEV 窗口;与 Executor 比对 18 项,18 项相同(`audit/stdout/599230f9…/10_r6_compare.txt`)。具体:
    - 1a:`str.split()` 13-gram 0;token 13-gram 0,另按送入模型的 id 计也是 0。
    - 1b:36 个正好 256 token,64 个更短,最短 172,没有超过 256 的。
    - 1c:截断 id 长度 511 篇 128、1 篇 123,与重新编码的长度逐篇相同;300 步的 KL 分母 298 步为 508、第 85 与 213 步为 503。
    - 1h:两个 sha256 等于 manifest,也等于 Stage 1 自己的记录。
  - 第 E 项:`l6_check.py` 的计数与判定、12 个受保护脚本的正常路径(用 ast 比较)与异常路径都一致。
  - **唯一的不一致(E3)**:我按自己的标准漏了 `round6/guard_ab.sh`、`guard_fail.sh`,它们按判定设置退出码,却没有异常保护与 RESULT 行。
  - **`r5_kl_denoms.py` 的 128**:auditor 已改为从 parquet 文档计算截断后的 id 长度(`audit/r5_kl_denoms.py`,运行 `04_r5_kl_denoms.txt`)。它在报告中承认第 5 轮观察 3 的前提错了。
  - 非 BLOCK 的观察登记在 `DEFERRED_MINORS.md` 1.5 节,或列入待决第 6 项。

### 修复:`2620f306`

- 按 metrix/CLAUDE.md 第 5.3 节,BLOCK 之后先修,再重新调用两个审查。
- 两个 bash 脚本加了 EXIT trap、参数个数检查和最后的 RESULT 行,判定条件逐字不变。
- 重跑与失败演示的原始输出见任务 2 末段;报告草稿中检查脚本的范围由 12 个改为 14 个。

### 第 2 轮:`599230f9..2620f306`(`reviews/2620f306…/`)

- 两个新的 subagent 于 02:28 并行调用,只审这一个提交。
- **code-reviewer:PASS**。2 条 MAJOR、3 条 MINOR。它报告自己加载的定义已含新句。
  - MAJOR 1:头注释说“出错由 EXIT trap 打印 RESULT: FAIL”,不准确。脚本没有 `set -e`,普通命令出错不进 trap:影响判定的命令出错,在正常结尾判 FAIL;只用于展示的命令(`wc`、`sha256sum`、`cat`)出错,判定不受影响。审查认为按现有代码几乎不会发生。这只涉及注释与展示命令,不影响任何检查的判定。改它需要再一轮提交与审查,我没有改,登记为 `DEFERRED_MINORS.md` H1,并列入待决第 14 项。
  - MAJOR 2:`t2_harness_fail.txt` 中两次不经管道的运行,完整输出只在 scratchpad,不符合第 9 节。已在报告提交中原样入库:`round6/t2_harness_fail_ab_missing_old.out.txt`、`t2_harness_fail_missing_py.out.txt`;sha256 与 scratchpad 中的文件相同,见 `round6/t2_harness_fail_outputs.txt`。
  - 3 条 MINOR 登记为 H2–H4。
- **data-auditor:PASS**(仅作参考)。
  - 它没有运行 Executor 的脚本,而是用自写的静态分析、bash 机制探针与检测脚本的自测(1 个正确样例、9 个变异样例)核对。三种情况(参数错误、运行中出错、正常结束)都打印 RESULT 行、失败时非 0 退出。
  - 改动前后的记录只差末尾追加的一行 `RESULT: PASS`。
  - 它判出的检查脚本集合与我的 14 个完全相同。同一检测在 `599230f9` 上会报出那两个脚本,说明检测有效。
  - 它指出我的排除清单漏列了 `round5/logrun.sh`(不输出判定),已在任务 2 补上。
  - 观察 (a):`guard_ab.sh` 的“identical”不检查脚本是否真的运行过,例如 PY 指向 `/bin/true`、或 OLD 与 NEW 是同一目录时会得 8/8。这是原有代码,登记为 `DEFERRED_MINORS.md` H5。
- 两个 subagent 报告运行期间 audit/ 以外出现的文件,都是我在它们运行时写的报告与登记文件,不在审查范围内。
- 审查之后,三个已审查的提交没有改动;报告提交只加了上面所说的证据文件、审查原文、auditor 的脚本与 stdout,以及本报告与 `DEFERRED_MINORS.md`。报告提交按指令不经 code-reviewer 审查。

## 任务 6:登记不修的 MINOR

见 `reports/DEFERRED_MINORS.md`:第 1 节为登记不修:1.1 Executor 脚本 11 条(E1–E11)、1.2 auditor 脚本 6 条(A1–A6)、1.3 记录与流程 5 条(P1–P5)、1.4 第 1 轮 code-reviewer 新提的 10 条(C1–C10)、1.5 第 1 轮 data-auditor 的非 BLOCK 观察 2 条(D1–D2)、1.6 第 2 轮两份审查的 5 条(H1–H5);第 2 节为已在第 5、6 轮解决的条目,便于核对;第 3 节为原标 MINOR、但影响指标或可复现性、须 Review Gate 决定的项。

## 待 Review Gate 决定

下列各项都要改协议、改 auditor 的文件或由 Owner 决定,Executor 没有改。`R6-CR:n` = `reviews/599230f9…/code-reviewer.md` 第 n 行;`R6-DA` = 同目录 `data-auditor.md`。

1. **第 2.7 节与 L6 的口径冲突**(R6-CR:17,MAJOR)。第 2.7 节仍写“锚文本与通用文本不得共享任何 13-gram”,第 3 节 L6 按 1a 只限词 13-gram,Qwen token 13-gram 只报告。两处对同一门槛说法不一。`t2_l6_judgment_demo.txt` 的第二个例子(词 0、token 5,判 PASS)按第 2.7 节就是违规。现有数据上两种单位都是 0,结论不受影响。审查建议改为“不得共享任何词 13-gram(定义与上限见第 3 节 L6)”。这是 1a 没有覆盖到的一句,我没有自行改。
2. **L6 的 TEST 部分**(第 1f 项的后续):
   - 时机(R6-CR:14):manifest 与第 8 步写“PROTOCOL_FROZEN 之后、TEST 评测之前”(照指令原文),比 `general_test.jsonl` 的生成条件(Gate 0 通过并提交冻结记录之后)宽。第 8 步的顺序本身是对的。审查建议改为“第 8 步生成 `general_test.jsonl` 之后、TEST 评测之前”。
   - 超限怎么办(R6-CR:15):L6 的 TEST 部分(以及 L3–L5 的 TEST 部分)超过上限 0 时的动作,协议没有写;ST1 只管第 2 步。
   - “计数”的口径(R6-CR:27):共享 13-gram 的种类数还是出现次数,按篇还是跨篇。现有脚本按篇取 n-gram、数种类。上限为 0 时不影响判定,但 TEST 部分“只输出计数”时口径就要固定。
   - 运行者:data-auditor 按 metrix/CLAUDE.md 第 10 节仍是「待验证」(R6-CR:15)。
3. **G0.1 只给 L6 开了例外**(R6-CR:16):L4 也有 TEST 部分,要等第 8 步生成 `test_qa.jsonl` 才能运行。照字面,Gate 0 时它做不到。审查建议写成“L1–L6 中涉及 TEST 的部分在 Gate 0 都不要求,按第 8 步运行”。
4. **n_w 与 1c 不一致**(R6-CR:18;我在任务 1 也提到):第 5 节 general damage 的 n_w 仍是“窗口的 token 数”,第 2.7 节也没写送入模型的是前 ≤256 个 id,还是这些 id 解码后重新编码的结果。在现有 100 个窗口上两者相同(data-auditor `05_r6_general.txt`:`windows where encode(window text) != window ids: 0`),但定义影响 dNLL 与 G0.8。
5. **锚文档“各截到 128 token”**(R6-CR:19):与 1b 修正的通用文本措辞是同类问题;第 340 篇全文只有 123 个 token(data-auditor `03_r6_anchor.txt`)。在 1c 之下数值不受影响;`DATA_MANIFEST.json: name_generation.anchor_rule` 已写 “at most 128 tokens”。
6. **检查脚本的范围与“检查不通过”的路径**(R6-CR:20、21;R6-DA E (a)、(c)):
   - `template_overlap.py`、`y_ratio.py` 检查不通过时仍以 0 退出;`anchor_check.py` 等 4 个以 1 退出但没有 RESULT 行。这是原有行为,第 2 项只管异常。是否统一为“不通过时打印 `RESULT: FAIL` 并以 1 退出”,请决定。
   - 我排除的 7 个不输出判定的脚本(任务 2“范围”),其中 `anchor_short_docs.py`、`em_special_tokens.py` 的输出是第 14 节引用的证据。是否也算检查脚本,请确认。
   - auditor 已入库的旧脚本(本轮 06–09 号运行用到的,以及 `r5_sources.py` 吞掉异常后以 0 退出)是否也在第 2 项的范围内。
7. **metrix/CLAUDE.md 第 10 节的记录**(R6-CR:22;第 5 轮待决 1):新加的一行只写了出处。按文件开头与第 8 节,还缺 Owner 批准、作用范围与时间(时间:提交 `481a6f0f`,2026-11-21 14:41:02 UTC)。第 9 节的先例写的是“(出处：Review Gate 第 4 轮裁决，Owner 批准，永久)”。请确认作用范围;如是永久,按先例补全。
8. **code-reviewer 的新规则与它的工具**(R6-CR:23):定义只给了 Read、Grep、Glob,审查方无法运行任何东西,所以它的判断全都是『未验证』;规则也没说引用仓库中已提交的原始输出算不算验证。审查建议二选一:给审查方一个只读的执行工具,或者定义什么算“已验证”。
9. **用户级副本与环境设置**(任务 4):修法 1(从 `metrix-e1-pilot-protocol-v1` 分支启动会话,并去掉 setup script 中的复制)或修法 2(副本标注来源提交,每轮开头比对)。环境设置的修改须 Owner 决定。修好之前,从 `main` 启动的会话加载的仍是构建时复制的旧版本(本轮第 1 轮审查即如此)。
10. **第 1g 项的边界**(R6-CR:24):`l6_check.py` 以文本模式打开文件,test 行的字节会做 UTF-8 解码;正则会扫过 test 行的 domain 值(不使用、不输出)。这是否在“解析 split 字段”的范围内,请确认;否则可改为按字节只匹配行首。
11. **仍开放的旧项**:
    - EM:`<think>`(151667)与 `</think>`(151668)不是特殊 token,`skip_special_tokens=True` 去不掉(第 5 轮待决 7 第 1 点;1d 没有覆盖)。
    - 第 2.6 节 S 的置换与第 2.5 节的候选抽取没有写死调用方式,只凭协议不能逐字节复现 `train_S.jsonl` 与 `candidates.json`(第 4 轮待决 8)。影响可复现性。
    - 第 5 轮的 3 页 `list_events` 原始输出是否整页入库(第 5 轮待决 13),请 Owner 决定。
12. **data-auditor 的信任评估可参考的事实**(第 10 节仍是「待验证」):
    - 本轮它的 BLOCK 是对的:我按自己的标准漏了两个 bash 脚本。
    - 它在报告中承认自己第 5 轮观察 3 的前提是错的(写死 128 所致),本轮已修正 `r5_kl_denoms.py`。
    - 它自己的 `r6_guard_audit.py` 第一次运行有标签错误,并会在 revision 不存在时给出假 PASS;它自己发现并修正(`audit/stdout/599230f9…/11–15`)。
13. **推送方式**:按本轮指令直接快进推送 `metrix-e1-pilot-protocol-v1`,没有经 PR(metrix/CLAUDE.md 第 6 节);同一 HEAD 也推送到会话分支 `claude/metrix-protocol-round6-9mq9ya`。两个分支都在两轮审查完成之后才推送,推送输出见最终回复。
14. **两个 bash 对照脚本的注释与展示命令**(第 2 轮 code-reviewer MAJOR 1):是否要求修正注释,或给展示命令加失败处理。不影响任何检查的判定,已登记为 `DEFERRED_MINORS.md` H1。

## 附

- 第一次运行 A/B 时,命令里的 `rm -rf`(清空 scratchpad 中的旧目录)被 Claude Code 的安全检查拒绝,命令没有执行;之后改为解压到新目录 `SP/r6/old_f4d8e988`,没有删除任何文件。
- 本会话早先一次命令被自动模式的分类器拒绝(读取 `eval_sets.jsonl` 第一行的字段类型)。那一行可能是 test 行,命令没有执行;之后改为从 `research/mini_mythos/stage1/build_data.py` 的代码确认行格式。
- scratchpad 中的中间文件(下载、venv、fact、锚文本、general DEV 窗口、A/B 输出)没有删除。
