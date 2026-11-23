# code-reviewer final report, Implementation stage A: staged fix commit (parent 602a39e8c4be1e1efa682a26637ad94fb919b7b8), committed unchanged as 219c4a60b1e2274fe57a7cdbe9d9606d814a8ab5; invoked 2026-11-23 01:19 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a0b733ffb212ac724.jsonl)
---
# code-reviewer 审查：Metrix E1-PILOT Implementation 阶段 A 修复提交（暂存，父提交 602a39e8c4be1e1efa682a26637ad94fb919b7b8）

结论：PASS。没有 BLOCKER，也没有 MAJOR。N1、N3、N5、N6、N7、N8 六条都已修好，修法正确。本轮新提出 4 条 MINOR，都是证据、引用或登记方面的缺口，没有发现代码缺陷。

**依据与方法**
- 已读仓库文件 /home/user/OpenMythos/.claude/agents/code-reviewer.md，内容与已加载的定义相同，tools 行为 Read, Grep, Glob。
- 我只用了 Read、Grep、Glob，没有运行任何代码。
- 标「已验证」的条目，引用的是本提交中暂存的原始输出（t5、t6，写明行号），或者直接读取的本地 .git 状态。只靠读代码或 grep 得出的判断标「未验证」。
- t5、t6 目前是暂存状态，还没有提交。它们按原样提交后，下面的引用才成立。
- 我读了工作区里的 frozen.py、test_data_hashes.py、test_leakage.py、test_st12.py，内容与审查输入 diff 的「+」侧一致。
- 我无法复算 sha256，因此无法确认 t6:115-120 记录的文件哈希就是现在暂存的 blob（未验证）。

## 一、N1、N3、N5、N6、N7、N8 的修复状态

严重度 | 文件:行号 | 问题（现状） | 证据 | 建议

MINOR（N1，已修） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:149-153、190-192；/home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:103-120 | 已修，修法正确。
- 解析前先把 CRLF 换成 LF。
- 原来表格结果赋给了 `data`，覆盖了同名参数；现在改名为 `data_hashes`，所以 `sha256_hex(data)` 拿到的仍是参数的原始字节。LF 检出时，source_sha256 的值与改动前相同（UTF-8 解码再编码不改变字节）。
- 新增的回归用例：在 mini repo 中把 PROTOCOL_FROZEN 改成 CRLF，load() 仍然通过。按代码推断，改动前这个用例会在 `## v1.1(当前有效)\r` 的 fullmatch 处抛 ST12。 | `text = data.decode("utf-8").replace("\r\n", "\n")`；`pf.write_bytes(pf.read_bytes().replace(b"\n", b"\r\n"))`；t6_fix_commit.txt:207 PASSED；真实检出 t6:147 | 无。（用例通过：已验证；改动前会失败：未验证，按代码推断）

MINOR（N3，已修） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:383-386 | 已修，修法正确。
- `json.loads(bytes)` 失败时只会抛 JSONDecodeError 或 UnicodeDecodeError，两者都是 ValueError 的子类。
- strip_step1_fields 先做 isinstance 检查，再用 `pop(..., None)`，不会抛 KeyError 或 AttributeError；dict 之间的比较也不会抛 TypeError。
- 其他异常（例如极深嵌套引起的 RecursionError）不会被捕获，会经 run_guarded 打印 RESULT: FAIL 后停止。停止方向是安全的，而且改动前同样不捕获。 | `except ValueError:                      # not JSON / not UTF-8`；t6:203-207 的工作区用例全部 PASSED | 无。（修法正确：未验证，读代码；用例通过：已验证）

MINOR（N5，已修） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_data_hashes.py:36-49 | 已修，修法正确。期望行数不再由被测的 D.params 计算，改为字面值 PROTOCOL_ROWS，各值都能在协议原文中找到：
- 2.1 第 61 行：160 = 120 + 40。
- 2.3 第 92-93 行：每条 learned fact 1 条 TRAIN；每条 fact（含 unread）2 条 DEV，共 320。
- 2.5 第 130 行：candidates 共 160 个键。
- 2.6 第 139 行：S 每条 learned fact 一句，共 120；第 142 行「共 240 句」。
- 2.7 第 146 行「共 100 个」，第 147 行「前 512 篇」。

另外新增了 4 处原文存在性断言。它们只确认这些文字在冻结协议中出现，不把文字与具体数值对应起来，作用有限但没有害处。 | `PROTOCOL_ROWS = {"facts.jsonl": 160, ... "anchor_text.jsonl": 512}`；t6:181 PASSED | 无。（数值与协议对照：未验证，读协议文件；用例通过：已验证）

MINOR（N6，已修） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_leakage.py:115-116 | 已修，修法正确。
- 两段断言文字与 leakage.py:189 的报错文字以及 errors.py:21 的前缀格式一致。
- 代码中只有这一处会产生以 `--split-manifest` 开头的 ST12 信息。
- 两段文字分开匹配，没有写成一个正则；但第一段已经能唯一确定是这条路径。 | `"ST12 -> BLOCKED: --split-manifest" in r.stderr and "differs from SPLIT_MANIFEST.json at the frozen commit" in r.stderr`；t6:196 PASSED | 无。（已验证）

MINOR（N7，已修） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:17 | 已修，修法正确。对 reports/IMPL_A_REPORT.md 的悬空引用已删除。src、tests 中已没有 IMPL_A_REPORT 的引用，grep 只在 tasks/IMPLEMENTATION_TASK_ORDER_V1.md 中找到。这个开放项本身还没有登记，见新问题第 3 条。 | `Beyond the two ranges (an open item for Review Gate):` | 无。（未验证：grep）

MINOR（N8，已修） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:229-237 | 已修，修法正确。
- 测试数据改用 ` `、` `、`\u0085` 三个转义写法。
- 新增断言，确认这三个字符在 jsonl_bytes 的输出中仍是原样（没有被转义）。
- json.dumps(ensure_ascii=False) 只转义码位小于 0x20 的控制字符、引号和反斜杠。str.splitlines 会额外断行的字符里，只有这三个能原样出现在规范 JSONL 中，所以覆盖是完整的。
- 文件末尾缺 `\n` 的负例改用同一个 raw。
- 全部 .py 文件中已没有字面的 U+2028、U+2029、U+0085。 | `rows = [{"text": "a b c\u0085d"}, {"text": "e"}]`；Grep `[\x{2028}\x{2029}\x{0085}]` 在 *.py 中无匹配；t6:229 PASSED | 无。（用例通过：已验证；没有残留字面字符：未验证，grep）

## 二、本提交引入的新问题

MINOR（新 1） | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_a/t6_fix_commit.txt:1 | 引用的路径 `reviews/602a39e8…/code-reviewer_round2.md` 用省略号缩写，而且 reviews/602a39e8… 目录在本提交中不存在（Glob 无结果）。第 1、2 轮审查原文、interruption_round2.txt，以及 t5:78-93 中未跟踪的 data-auditor 脚本和 stdout（metrix/e1-pilot/audit/）目前都不在仓库里。这与 N7 是同一类问题。 | `reviews/602a39e8…/code-reviewer_round2.md` | 推送前把这些原文写入 /home/user/OpenMythos/metrix/e1-pilot/reviews/602a39e8c4be1e1efa682a26637ad94fb919b7b8/，并在 t6 中写完整路径（metrix/CLAUDE.md 第 5 节第 5 条、第 9 节）。（未验证：Glob）

MINOR（新 2） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:139-140、192 | source_sha256 是工作区原始字节的哈希。N1 修好之后，CRLF 检出和 LF 检出会解析出同一个 record，但 source_sha256 不同。阶段 A 没有用到这个字段（grep 只在定义处出现）。阶段 B 由 record.py 写入实验记录时，同一冻结提交在不同检出下会得到不同的记录值。 | `source_sha256=sha256_hex(data))` | 登记为阶段 B 的前瞻项：在记录中写明这是工作区原始字节的哈希，或另记一个 LF 归一化后的哈希。（未验证：读代码）

MINOR（新 3） | /home/user/OpenMythos/metrix/e1-pilot/reports/DEFERRED_MINORS.md | 本提交没有登记 N2、N4 以及 frozen.py:17 的开放项：DEFERRED_MINORS.md 中 grep `IMPL|N2|N4|602a39e8` 无匹配，IMPL_A_REPORT.md 也不存在。任务指令第 9 节要求，未修的 MAJOR/MINOR 登记于 DEFERRED_MINORS.md。N4（忽略 `+local` 标签，这是对协议第 0 节「不一致即 BLOCKED」的解释）涉及协议一致性，只登记不够，还需要 Review Gate 确认。 | grep 无匹配；Glob reports/IMPL* 无结果 | 在阶段 A 报告的提交中登记 N2、N4，以及第 1 轮的 MAJOR #1 ③、(b)、(f)，并提请 Review Gate 裁决。裁决之前，不要把 N4 记为已关闭。（未验证：grep、Glob）

## 三、t5_commit_push.txt 核对

MINOR（新 4，t5） | /home/user/OpenMythos/metrix/e1-pilot/reports/impl_a/t5_commit_push.txt:7-45 | 「工作提交就是第 2 轮审查的内容」这一点，t5 只在 stat 层面给出了证据，没有逐字节比对。
- t5:8-45 的 `git show --stat` 与 /tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad/review_work/review_input_round2.diff:3-23 逐行相同：20 个文件，各文件行数相同，共 4544 insertions。
- 唯一的逐字节比对在 interruption_round2.txt:44-48，时间是 01:10:11，比提交早约 7 分钟，而且该文件在 scratchpad 中，没有入库。

旁证如下，都支持两者一致：
- 本地 reflog（/home/user/OpenMythos/.git/logs/refs/heads/metrix-e1-pilot-protocol-v1:2）：从 8149d872 只有一次 commit，时间戳 1795396628，即 2026-11-23T01:17:08Z，与 t5:4 相同，没有 amend。
- 修复 diff 中「-」侧的行和行号，与第 2 轮审查的引用一致：frozen.py:17、384，test_leakage.py:115，test_st12.py:226-232。
- t6:116-117 的 data.py 8a531939… 和 leakage.py 5e1d4374…，与 t4_pytest.txt:120-121（第 2 轮所测）相同；这两个文件也不在 t6:107-112 的改动列表中。

我判断提交与审查内容一致的可能性很高，但证据链还缺一环。 | 同左 | 把 interruption_round2.txt 入库。以后在提交前记录 `git diff --cached` 与审查输入的逐字节比较，或者补做 `git diff 8149d872 602a39e8` 与审查输入的比较。（部分已验证）

其余几项与原始输出一致，没有问题：
- **快进推送（已验证）**：
  - t5:66-68：`merge-base --is-ancestor` 返回 exit 0。
  - t5:70-71：`8149d872..602a39e8  HEAD -> metrix-e1-pilot-protocol-v1`，两个点，没有 forced update 标记。
  - t5:73-74：推送后远端分支为 602a39e8。
  - 本地 /home/user/OpenMythos/.git/logs/refs/remotes/origin/metrix-e1-pilot-protocol-v1:3 记有 `update by push`，从 8149d872 到 602a39e8，时间 01:17:19，晚于 t5 头部时间 01:17:15，先后顺序吻合。
- **没有推送标签（已验证）**：
  - push 命令没有 `--tags` 或 `--follow-tags`；/root/.gitconfig 和仓库 .git/config 中都没有 followTags。
  - push 输出只有一行分支更新，没有 `[new tag]`。
  - 推送前远端的 tag（t5:61-64）与本地 .git/refs/tags/metrix-e1-pilot-frozen（4c023ec8…）和 metrix-e1-pilot-frozen-v1.1（6fd45fd1…）相同。
  - 小缺口：推送后的 ls-remote（t5:73）只查了分支，没有查 tags。push 输出已足以说明没有推送标签。
- **metrix/ 以外的检查（已验证）**：
  - t5:47-58 给出 RESULT: PASS。metrix/ 以外的改动只有 `.claude/agents/` 下的两个文件，以及根 CLAUDE.md 追加的第 6 节；这些都在 metrix/CLAUDE.md 第 2 节允许的范围内。
  - 工作提交的 20 个文件全部在 metrix/e1-pilot/ 下（t5:8-45）。
  - 本修复提交的 6 个文件也全部在 metrix/e1-pilot/ 下（审查输入 diff:3-9）。
- **本提交的其他原始输出（已验证）**：
  - 改动后重新生成的 gen5 与 gen1 逐字节相同（t6:143-145）。
  - verify 通过，4 个冻结内容哈希与 PROTOCOL_FROZEN 相同（t6:146-154）。
  - 协议泄漏命令 L1–L6 都在上限内（t6:155-170）。
  - pytest 51 项全部通过（t6:177、231）。
  - t6:128 统计了 eval_sets 中 test 行的数量。按协议第 158 行，计数不算读取 TEST，所以没有问题。

结论：PASS
