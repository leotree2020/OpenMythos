  审查范围：wip-b @ 8e7e124a5e9285c0e6a0936c78d643ba5aeca69d 相对 2253be94d77d41c5106d8074da578987d5b0a238 的 diff。diff 只改了一行：`/home/user/OpenMythos/metrix/e1-pilot/reports/round3/scoring_input.py:15`，把 `ENABLE_THINKING = False` 改成了 `ENABLE_THINKING = True`。
  审查方式：只用 Read/Grep 读文件，没有执行任何代码，没有运行 git，没有加载 tokenizer 或模型。运行环境是 Claude Code subagent 容器（Linux，工作目录 /home/user/OpenMythos）。
  
  BLOCKER | metrix/e1-pilot/reports/round3/scoring_input.py:15 | 打分输入的 `enable_thinking` 被改成 True，违反协议第 0 节“问答输入”中写死的 `enable_thinking=false`，也不符合审查规则第 3 条（打分必须用 Qwen3 chat template 且 enable_thinking=False）。这个文件是协议第 35 行和 DATA_MANIFEST.json:29 指定的参考实现。verify_scoring.py:89 和 candidate_feasibility_r3.py:44 都通过 `SI.scoring_input` / `SI.chat_prompt` 用它构造打分上下文和 EM 生成上下文（协议第 36 行），所以这个改动会传到所有打分和评测路径。仓库里已有的 tokenizer 原始输出 reports/round3/t7_verify_scoring.txt:17-18 表明，改为 True 后，生成提示末尾不再有 `<think>\n\n</think>\n\n`，上下文与协议规定的不同。修改这个值等于修改协议定义的打分输入，需要 Review Gate 裁决并由 Owner 批准；diff 里没有协议修订记录（协议修订表最后一条 v1-r3 的定义仍是 `enable_thinking=false`），Executor 也无权做这项改动。 | 改动前 `ENABLE_THINKING = False`，改动后 `ENABLE_THINKING = True`；对照协议 METRIX_E1_PROTOCOL.md:34 原文：`` `enable_thinking=false`(写死,不作参数) `` | 恢复为 `ENABLE_THINKING = False`。如果确实要改，先停下，交给 Review Gate 和 Owner 走协议修订流程，不能直接提交代码。
  
  MINOR | metrix/e1-pilot/reports/round3/scoring_input.py:7-8 对比 :15 | 模块 docstring 与代码矛盾：docstring 说 enable_thinking 写死为 False，代码却是 True。 | docstring `enable_thinking=False (written here as a constant; there is no argument to change it);`，代码 `ENABLE_THINKING = True` | 按上一条恢复为 False 后，这个矛盾自然消失。
  
  MAJOR | metrix/e1-pilot/reports/round3/verify_scoring.py:69, 96-98 | 验证脚本检测不出这次回归。这是已有代码的缺陷，由本次 diff 暴露出来。(a) 渲染一致性检查的两边都用 `SI.ENABLE_THINKING`，常量取任何值 renderer_diff 都是 0，是同义反复。(b) 答案 token 检查只比较 `ids[start:]`，即候选部分；按代码推断，这一段不受 assistant 回合开头有没有 think 块影响，所以 mismatch 很可能仍为 0。我没有运行，这一点不能确定，按 MAJOR 列出。(c) 第 69 行的标签写死为“enable_thinking=False”，打印的却是 `SI.chat_prompt` 的实际结果，常量为 True 时这行输出会贴错标签。整个脚本没有任何地方断言 `SI.ENABLE_THINKING is False`，也没有检查生成提示是否以 `<think>\n\n</think>\n\n` 结尾。因此常量为 True 时，脚本很可能仍会输出 `RESULT: PASS`。 | `print("generation prompt (enable_thinking=False):", json.dumps(SI.chat_prompt(tok, "Q?")))`；`tokenize=False, continue_final_message=True, enable_thinking=SI.ENABLE_THINKING)` | 增加一项与 SI 无关的协议检查：直接断言 `SI.ENABLE_THINKING is False`，或断言 `SI.chat_prompt(tok, q)` 与独立调用 `apply_chat_template(..., enable_thinking=False)` 得到的文本相同，或断言它以 `<think>\n\n</think>\n\n` 结尾；任一项不满足即判 FAIL。第 69 行的标签改为打印实际的常量值。
  
  MAJOR | metrix/e1-pilot/reports/round3/t7_verify_scoring.txt:17；metrix/e1-pilot/reports/round4/t2_verify_scoring.txt:17 | 仓库里的原始输出是用 enable_thinking=False 生成的，与 8e7e124 的代码不再对应。在这个提交上引用它们作为打分输入的证据就是过期证据，违反 metrix/CLAUDE.md 第 9 节“所有结论附原始命令输出”。 | `generation prompt (enable_thinking=False): "<|im_start|>user\nQ?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"` | 恢复为 False 后这些输出依然有效。如果改动保留，所有依赖 scoring_input.py 的输出都要重跑，并重新调用 data-auditor（改动涉及打分代码，metrix/CLAUDE.md 第 5.2 节）。
  
  其他检查项：
  - 数据隔离：diff 没有新增读取 TEST 的路径，verify_scoring.py:56 和 candidate_feasibility_r3.py:36 仍只读 TRAIN/DEV 模板。
  - 死代码：diff 没有引入未使用的 import 或配置项。
  - 梯度、冻结、种子、聚合函数、arm 定义：diff 未涉及，不适用。
  
  结论：BLOCK
