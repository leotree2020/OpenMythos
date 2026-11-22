# code-reviewer final report, round 8, item-5 pre-commit review of the staged PROTOCOL_FROZEN draft (parent 92df1a60; never committed, superseded by the supplement); invoked 2026-11-22 05:52 UTC (background); invocation text: code-reviewer_frozen-file_prompt.txt
# extracted unchanged by reports/round6/review_extract.py from this session's subagent transcript (agent-a57beb4cae91e0045.jsonl)
---
code-reviewer 第 8 轮第 5 项提交前审查(暂存区中的 PROTOCOL_FROZEN 提交,父提交 92df1a60ac816ab02b250d32841397c73b9a67a7)

## 依据与范围
- 按仓库文件 /home/user/OpenMythos/.claude/agents/code-reviewer.md 执行。它比我已加载的定义多第 29–30 行(已验证/未验证的标注规则);两者的 tools 行相同,都是 `Read, Grep, Glob`(与 preflight_tools_check_frozen-file.txt:3、:6 一致)。调用文字的首句与第 5 节第 6 条的规定相同。
- 我没有 Bash,所以没有运行任何命令,也算不了 sha256。凡是对照了已提交或已暂存的原始输出(写明路径与行号)的判断,标为“已验证”;只靠读文件得出的判断,标为“未验证(文本对照)”。
- PROTOCOL_FROZEN 在磁盘上的内容与 frozen_file_commit_input.diff:45–98 逐行相同,共 54 行。它的文件 sha256(18ce467b…)我没法复算。

## 逐项对照:第 5 项要求的内容
- **冻结提交完整 hash:有且正确。** 已验证。PROTOCOL_FROZEN:9 的 `92df1a60ac816ab02b250d32841397c73b9a67a7` 与以下三处相同:.git/refs/heads/metrix-e1-pilot-protocol-v1、t5_frozen_hashes.txt:4、audit/stdout/92df1a60…/02_r8_files.txt:4。
  - 提交时间 05:39:23 UTC 与父提交 18076298… 也与 t5_frozen_hashes.txt:4、02_r8_files.txt:4 相同。
  - 协议 :691 要求本文件记录提交时间,已经记了。
- **协议文件与三个 JSON 的 sha256:4 个值都正确。** 已验证。PROTOCOL_FROZEN:21–24 与以下各处逐字相同:
  - Executor 的 t5_frozen_hashes.txt:19–22;
  - data-auditor 的独立复算:02_r8_files.txt:9、:17、:25、:33,以及 10_r8_compare_rerun.txt:9、:14、:19、:24。
  - 在冻结提交的 git archive 解包目录里运行 `sha256sum -c`,4 项全部 OK(t5_protocol_frozen_check.txt:42–47)。所以标签与值也一一对应。
- **全部数据哈希:12 个值,数值和对应的标签都正确。** 已验证。
  - 我用 Grep 把 PROTOCOL_FROZEN 中的“标签 + 值”整行精确匹配,16 行全部命中(4 个文件哈希 + 12 个数据哈希)。
  - 12 个数据哈希都与 manifest 中“字段名 + 值”逐一相同:DATA_MANIFEST.json:20–23、:203、:218、:228、:230、:237、:242;SPLIT_MANIFEST.json:315、:327。
  - 它们也与 auditor 的复算值逐一相同:10_r8_compare_rerun.txt:29–244 中对应标签的 `auditor` 行。
  - 冻结时工作区中的 manifest 与冻结提交逐字节相同(t5_frozen_hashes.txt:25–26;02_r8_files.txt:19、:27)。
  - 3 个 40 位 revision(Qwen 70d244cc…、fineweb 4d1138c0…、parcae 6247b5d0…)与 DATA_MANIFEST.json:18、:237、:229 相同。
  - PROTOCOL_FROZEN 中没有其它 64 位十六进制值(t5_protocol_frozen_check.txt:36)。
  - 表中引用的协议节号也对得上:2.2 节在 :85,2.5 节在 :131,2.6 节在 :139,第 3 节在 :154,第 0 节“哈希”在 :45。
- **「Owner 批准，2026-11-22 05:27 UTC」:有,字节相同。** 已验证。我用同一个 Grep 模式(含全角逗号)同时命中 PROTOCOL_FROZEN:3 与 ROUND8_TASKS.md:20;t5_protocol_frozen_check.txt:38 也是 True。
- **TEST 隔离:不会被读成允许生成或评测 TEST。** 未验证(文本对照)。
  - PROTOCOL_FROZEN:48 明确写了“冻结不等于允许生成或评测 TEST”,且 TEST 只在第 8 节第 8 步、并须人工指令。这与协议 :525、:255、DATA_MANIFEST.json:299 以及 metrix/CLAUDE.md 第 7 节一致。
  - 这句话缓解了我在第 4 项登记的 MAJOR(协议 :149 的“冻结之后”没有限定)。
  - 文件没有沿用 data-auditor MINOR 2 指出的不实标注“PYTHONHASHSEED=0/31337”。
  - 暂存的 audit 脚本中,r8_general.py:5–6、:70–87 对 eval_sets.jsonl 只做整文件哈希;r8_fetch.py:28 有防止下载权重的检查。
- **BLOCKER:没有。**

## 问题清单(按第 4 项的做法只登记,不修)
MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:12(另见 :18) | 文件把标签 metrix-e1-pilot-frozen 写成已经存在,但审查时它还不存在;冻结提交也还没推送;t5_protocol_frozen_check.txt 没有核对标签 | Glob .git/refs/tags/* 没有结果,.git/packed-refs 不存在;origin/metrix-e1-pilot-protocol-v1 仍是 18076298… | 登记;打标签后在 ROUND8_REPORT 附 `git rev-parse metrix-e1-pilot-frozen^{commit}` 与 `git ls-remote --tags origin` 的原始输出,确认标签指向 92df1a60,而不是第 5 项提交 | 标签不存在:已验证;标签将来指向哪里:未验证

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:54 | “汇总比对 48 个值,复算值、冻结提交中的值与 Executor 原始输出三方相同”说多了:(1)4 个文件 sha256 在冻结提交中没有对应字段,只是两方一致;(2)32 个模板 normalized_sha256 的“Executor 值”就是 manifest 值,Executor 只打印了“未复现: []”;(3)没有提到首次比对 09_r8_compare.txt 的结果是 FAIL(exception) | 10_r8_compare_rerun.txt:10–12 `commit - [(no manifest field; PROTOCOL_FROZEN not yet written)]`、`auditor==commit n/a`;:249 的 note;09_r8_compare.txt:10–11 `UnicodeDecodeError … RESULT: FAIL (exception)` | 登记;如实写成:12 个数据哈希三方一致,4 个文件哈希两方一致,32 个模板值 Executor 侧只有“无不复现”;并写明 09 失败及原因 | 已验证

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:54;metrix/e1-pilot/reports/round8/t5_frozen_hashes.txt:2 | 两处都说“数据哈希的重算”在 t0_env.txt 与 t1d_data_hashes.txt 中,但 template_set_sha256 的 Executor 重算只在 t1_protocol_checks.txt:39–41 | 在三份文件中 Grep `2b52411326c218e9`,只命中 t1_protocol_checks.txt:36、:41 | 登记;引用中补上 t1_protocol_checks.txt | 已验证

MINOR | metrix/e1-pilot/reports/round8/t5_protocol_frozen_check.txt:18–35 | 这个检查只判断每个值“在文件中出现”,不核对值在哪一行、配哪个标签;两行哈希互换(例如 vocab.json 与 merges.txt)时仍会全部 True。4 个文件哈希另有 sha256sum -c 保证对应关系,12 个数据哈希没有 | `for k, v in want.items(): print(... v in found)` | 登记;本次我已按“标签 + 值”逐行对照,结果见上 | 已验证

MINOR | metrix/e1-pilot/reports/round8/t5_protocol_frozen_check.txt:15–17、:41 | 第一次 git archive 解包到临时目录后,没有任何命令用它,是死步骤;:41 是 Executor 在原始输出中途追加的说明行 | `git archive … | tar -x -C $(mktemp -d …/frz.XXXX) && echo extracted`;`# The "extracted" line above only extracted the freeze commit; …` | 登记;以后删掉无用步骤,说明写在文件头 | 已验证

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:46 | 这一行只提到 DATA_MANIFEST.json 的 `files` 要在之后填写。(1)没提 SPLIT_MANIFEST.json 的 `split_sha256`(5 项都是 null,第 1 步也要填);(2)没说第 1 步生成的 facts、train_S、candidates 的 canonical_sha256 必须等于上表的期望值(协议 :85、:131、:139 都写了“必须等于”),读者可能把上表和以后填的值当成两套 | SPLIT_MANIFEST.json:393–399;协议 :139 `train_S.jsonl 的规范化 SHA-256 必须等于 686fdd2f…` | 登记 | 未验证(文本对照)

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:18 | 文件说“在冻结提交的检出上运行 sha256sum -c 应全部 OK”,这默认检出时不做换行转换。仓库没有 gitattributes;在 core.autocrlf=true 的环境检出,字节会变,检查会失败 | 02_r8_files.txt:13 `gitattributes: (no attributes)` | 登记;可注明以 `git cat-file blob <commit>:<path> | sha256sum` 为准 | 未验证(未运行)

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:14、:18、:44、:52–54 | 路径的基准不统一::18 说“路径相对仓库根目录”,:44 的 eval_sets 路径也相对根目录;但 :14、:52–54 的 tasks/…、reviews/…、reports/…、audit/… 相对 metrix/e1-pilot/ | `路径相对仓库根目录` 与 `reviews/92df1a60…/code-reviewer.md` | 登记;注明基准,或改写全路径 | 未验证(文本对照)

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:27–44 | 指令没有定义“全部数据哈希”。这里按 manifest 的读法列了 12 个值,这个读法成立。32 个模板 normalized_sha256 没有逐个列出,但已由 template_set_sha256 和 SPLIT_MANIFEST 的文件 sha256 间接锁定。Qwen config.json、generation_config.json 的 sha256 仍只在报告中(第 4 项已登记,这里只交叉引用) | 无 | 登记;如果 Review Gate 的意图更广,另行决定 | 未验证(文本对照)

MINOR | metrix/e1-pilot/PROTOCOL_FROZEN:48 | 本文件也含“数据哈希”,名称和内容都与协议第 8 节第 8 步的“冻结记录”(选定配置、数据哈希、checkpoint 哈希)相近。:48 已基本消除歧义,但没有明说“本文件不是第 8 步的冻结记录”。metrix/CLAUDE.md 第 3 节以“收到 PROTOCOL_FROZEN 之前”为限、冻结后其余禁止失效的问题,第 4 项已登记为 MAJOR,这里不重复 | 协议 :525 `Gate 0 通过后:提交冻结记录(选定配置、数据哈希、checkpoint 哈希)→ 生成 test_qa.jsonl…` | 登记;可以加上这一句 | 未验证(文本对照)

MINOR | metrix/e1-pilot/reviews/92df1a60ac816ab02b250d32841397c73b9a67a7/(对照 frozen_file_commit_input.diff:2–38) | 暂存区的 --stat(36 个文件)不含本次审查的三个输入文件:frozen_file_commit_input.diff、preflight_tools_check_frozen-file.txt、code-reviewer_frozen-file_prompt.txt。它们已在磁盘上,本次审查原文也还没有暂存。按 metrix/CLAUDE.md 第 5 节第 5 条,这些须随提交推送。另外,15_git_status_final.txt 显示 reports/DEFERRED_MINORS.md 有修改;它不在 --stat 中,也就不在本提交内 | Glob 结果与 --stat 对照 | 登记;提交前一并暂存;说明 DEFERRED_MINORS.md 放到哪个提交 | --stat 与磁盘对照:已验证;之后是否补暂存:未验证

结论：PASS
