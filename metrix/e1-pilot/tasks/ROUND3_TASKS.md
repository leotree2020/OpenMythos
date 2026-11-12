# E1-PILOT 第 3 轮任务(原文)

来源:Review Gate 第 3 轮编号指令,由 Project Owner 于 2026-11-12 15:26 UTC 下达。代码块内为原文,逐字照录,编号为原编号。

```text
3. 修改协议的"metrix/ 以外无改动"检查：只放行根目录 CLAUDE.md 第 6 节的追加内容，以及 .claude/agents/ 下的两个文件；宪章原有内容必须与基线逐字一致。注明这两个 agent 文件被 .gitignore 忽略、是用 git add -f 强制跟踪的，以后改动它们也须用 -f。写入第 14 节变更记录。
4. 核查前两轮的代码与协议是否受过 Mythos 宪章"不加 BOS/EOS"规则的影响，逐处列出涉及特殊 token 的位置及结论。
5. 在第 14 节补记"生成时拒绝锚文本中出现过的名字"这一改动，写明原因与时间。
6. 候选打分改为：assistant 回合以固定前缀 "The answer is" 开头，答案前带空格；写死 enable_thinking=False。
7. 验证：对全部 learned 答案，比对打分时答案的 token id 与 TRAIN 陈述句中答案片段的 token id，报告不一致数（要求为 0），并贴出一条完整渲染后的打分序列。
8. 用新的切分重算候选可行性：报告最小池大小与不足 4 个的 cell。
9. 对最新提交调用 code-reviewer 和 data-auditor，原始输出存入 reviews/<commit-hash>/。
11. 结果写入 reports/ROUND3_REPORT.md，提交推送，给出 commit hash。
```
