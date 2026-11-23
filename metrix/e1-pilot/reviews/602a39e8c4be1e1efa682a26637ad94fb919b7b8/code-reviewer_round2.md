# code-reviewer final report, Implementation stage A, round 2: staged work commit after the round-1 fixes, committed unchanged as 602a39e8c4be1e1efa682a26637ad94fb919b7b8; invoked 2026-11-22 16:54 UTC (background), interrupted by HTTP 429, resumed 2026-11-23 01:11 UTC; invocation text: code-reviewer_prompt_round2.txt; resume: resume_message_code-reviewer_round2.txt; inputs: review_input_round2.diff, review_fixes_round2.diff
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-aeed4357912b57448.jsonl)
---
# code-reviewer 第 2 轮审查：Metrix E1-PILOT Implementation 阶段 A 工作提交（暂存，父提交 8149d872）

结论：没有 BLOCKER，结论 PASS。第 1 轮的 2 条 MAJOR 中，第 2 条已修；第 1 条的 ①② 已修，③ 仍待 Review Gate 裁决。本轮新提出 8 条 MINOR，其中 N4、N5 按任务指令第 9 节属于须修或须登记确认的一类。

**依据与方法**
- 已按协调方要求重读仓库定义 /home/user/OpenMythos/.claude/agents/code-reviewer.md。它与已加载定义相同，tools 行为 Read, Grep, Glob。
- 中断记录 /tmp/claude-0/-home-user/0dff44d1-df17-5cd8-99ed-7d453ca71e71/scratchpad/review_work/interruption_round2.txt 第 44-48 行显示：暂存 diff 与 review_input_round2.diff 相同，工作区与暂存区无差异。审查对象就是工作区里的这些文件。
- 我只用 Read、Grep、Glob，没有运行任何代码。
- 标「已验证」的条目引用 /home/user/OpenMythos/metrix/e1-pilot/reports/impl_a/ 下暂存的原始输出（写明行号）。只靠读代码或 grep 得出的一律标「未验证」。

**一处我无法核对**：t4_pytest.txt 第二次运行时，src 和 tests 处于 AM / ?? 状态（t4_pytest.txt:99-113）。所测文件的 sha256 记录在 t4_pytest.txt:116-129。其中 4 个源文件的值与 t2_fetch_generate.txt 中的记录相同（data.py 8a531939…、frozen.py 5abeeccb…、leakage.py 5e1d4374…、errors.py 9766d215…）。这些哈希是否等于现在暂存的 blob，我没有 shell，无法复算（未验证）。

## 一、第 1 轮各条的现状（按第 1 轮原文顺序）
关于条数：第 1 轮问题清单里 MINOR 实际是 12 行。(a)–(f) 节中 (b) 也标为 MINOR，与清单第 1 条 MINOR 是同一条；(f) 要求登记。为覆盖可能被计为第 13 条的项，12 行之后补了 (d)(e)(f) 的状态。

严重度 | 文件:行号 | 问题（现状） | 证据 | 建议

MAJOR（第 1 轮 #1，即 (a)） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:216-225、375-390 | 部分已修。
- ①（换行转换误判）已修且正确：协议文件和 SEARCH_SPACE.json 先把 CRLF 换成 LF 再比。
- ②（排除范围）已修且正确：两个 manifest 去掉整个 files / split_sha256 字段后按解析结果比，与协议第 11 节 ST12 原文一致。
- ③ 未修，交 Review Gate：工作区比对仍超出 ST12 范围 (2)，仍按 ST12 停止。docstring 已注明这是待 Review Gate 决定的开放项（frozen.py:17）。 | `same = wt.replace(b"\r\n", b"\n") == blobs[rel]`；`obj.pop(STEP1_FIELDS[rel], None)`；CRLF 加上 files / split_sha256 新增键时 load() 仍通过：t4_pytest.txt:167；工作区改一个字节即停：t4_pytest.txt:163-166；真实检出通过：t2_fetch_generate.txt:123 | ③ 继续交 Review Gate。裁决时一并看本节 N1、N2。（①② 已验证；③ 未验证）

MAJOR（第 1 轮 #2） | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:2 | 已修且正确。
- lock 写明 `# python: CPython 3.13.18`。
- tests/test_environment.py:15-20 核对当前解释器与这一行一致。
- generate 输出中记录了 python 版本。
- 没有运行时强制停止，只靠测试和输出记录；但解释器差异导致的输出变化会被 4 个冻结哈希（ST12）拦下，可以接受。 | t1_lock.txt:1023-1027（requirements 与 hashes 未变，`2:# python: CPython 3.13.18`）；t4_pytest.txt:145；t2_fetch_generate.txt:124 | 无。（已验证）

MINOR（第 1 轮 MINOR 1，即 (b)） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:589-604 | 未修，待登记或交 Review Gate。没有冻结哈希的文件（train_F、train_Y、dev_qa、general_dev 和锚文本 ids）与重新生成的结果逐字节不同时，仍记为 ST12。IMPL_A_REPORT.md 还不存在。 | `raise ST12Error("%s in %s differs from its regeneration from the frozen inputs" ...)`；行为：t4_pytest.txt:178-185、t2_fetch_generate.txt:160；Glob reports/IMPL* 无结果 | 在 IMPL_A_REPORT 中登记，请 Review Gate 确认状态标签。（行为已验证；登记缺失未验证：Glob）

MINOR（第 1 轮 MINOR 2） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:101-114；data.py:582 | 已修且正确。
- 新增 parse_jsonl，只按 b"\n" 切分，并要求文件以 \n 结尾。read_jsonl 和 file_hashes 都改用它。
- tests 中已没有对 JSONL 使用 splitlines 的地方：剩下的一处是 test_environment.py:16 读 lock 文件。
- data.py:507 用文本模式逐行读 eval_sets，不会在 U+2028 / U+0085 处断行。 | `return [json.loads(line) for line in raw[:-1].split(b"\n")]`；t4_pytest.txt:189 | 测试覆盖缺口见 N8。（已验证：t4；其余未验证：grep）

MINOR（第 1 轮 MINOR 3） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:44；data.py:147、160、211；frozen.py:139-140、250 | 已修且正确。
- TEMPLATE_SETS 已删除。
- load_qwen_tokenizer 已去掉 fz 参数。
- a_sha 不再捕获（parquet 哈希仍经 DATA_TABLE_ROWS 与 PROTOCOL_FROZEN 核对）。
- Frozen.seeds 已由 params 使用。
- source_sha256、protocol_text 注明留给阶段 B；protocol_text 已被 test_data_hashes.py:45 使用。 | grep 结果 | 无。（未验证：grep）

MINOR（第 1 轮 MINOR 4） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:97-107、162-163 | 已修且正确。
- 前缀 E1P 与 nat/rnd 取自 fact_id_format。
- L/U 取自 SPLIT_MANIFEST fact_ids，并核对前缀、计数（120/40）和字母。
- 没有核对 learned 与 unread 的字母互不相同，但字母一旦出错，fact 哈希会不符而触发 ST12。 | `e = _match(r"(\w+)-(\w)-\*: (\d+) facts, .*", sm["fact_ids"][exposure], ...)`；gen4 与 gen1 逐字节相同：t2_fetch_generate.txt:152；4 个冻结哈希：t2_fetch_generate.txt:137-140 | 无。（已验证）

MINOR（第 1 轮 MINOR 5） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_data_hashes.py:36-49 | 已修但有问题。F/Y 的 token 数改为从冻结协议正文第 142 行读取，这部分正确。但 dev_qa、general_dev、anchor 的期望行数改由 D.params 计算，D.params 本身就是被测代码，见 N5。 | `"dev_qa.jsonl": total * p.dev_per_fact`；t4_pytest.txt:141 | 见 N5。（未验证：读代码）

MINOR（第 1 轮 MINOR 6） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:89、99、129-131、141、161-165、176-196、216、223 | 已修且正确：断言都改成了具体的检查信息。新增的 test_leakage.py:115 仍只断言 "ST12"，见 N6。 | `match="ST12 -> BLOCKED: %s at the frozen commit %s has sha256" % (rel, tampered)`；t4_pytest.txt:159-189 全部 PASSED | 见 N6。（已验证：t4；具体程度未验证：读代码）

MINOR（第 1 轮 MINOR 7） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:4-14 | docstring 已修且正确：写明只篡改 PROTOCOL_FROZEN 中的哈希值，正文不在覆盖范围。在报告中写明第 10 项覆盖范围这一项未完成，因为报告还不存在。 | `the prose of PROTOCOL_FROZEN is not covered` | 写 IMPL_A_REPORT 时写明。（未验证）

MINOR（第 1 轮 MINOR 8） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:190-191 | 已修且正确。协议命令在跑泄漏检查之前先执行 check_data_dir（ST12 范围 (1) 的 4 个内容哈希），不符即停，不写报告。只有 6 项检查都在上限内时才退出 0，仍符合协议第 3 节第 175 行。 | t3_leakage.txt:116-119、129；L1–L6 结果与 gen1 相同：t3_leakage.txt:132；t4_pytest.txt:157 | 无。（已验证）

MINOR（第 1 轮 MINOR 9） | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:14 | 在 lock 中已修。但同样的悬空引用转移到了 frozen.py:17，见 N7。 | `# peft is not used: ... (stage B), so it is not locked.` | 见 N7。（未验证：Glob）

MINOR（第 1 轮 MINOR 10） | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:7-8 | 未修，按建议留到阶段 C 的 RUNBOOK；lock 注释已写明驱动需支持 CUDA 13.0。 | `requirement to be written into RUNBOOK_A100.md, stage C` | 阶段 C 落实。（未验证）

MINOR（第 1 轮 MINOR 11） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:250 | 未修，属于阶段 B 的前瞻项：门槛仍未解析出来，只注明阶段 B 从 protocol_text 读取。 | `# ... (gate thresholds are read from it, stage B)` | 阶段 B 落实，不得写死。（未验证）

MINOR（第 1 轮 MINOR 12） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:228-241；data.py:528 | 已修且正确。generate()（verify 经由它）在核对输入之前调用 check_library_versions；版本不一致或未安装时抛 ST8Error，状态 BLOCKED。注意事项见 N4。 | t2_fetch_generate.txt:124；t4_pytest.txt:145-147 | 见 N4。（已验证）

MINOR（第 1 轮 (d)） | RUNBOOK（阶段 C） | 未修，前瞻项：PYTHONPATH=metrix/e1-pilot/src 和 namespace package 的前提要写进 RUNBOOK；RUNBOOK 还不存在。 | src/metrix/e1_pilot/check_leakage.py docstring | 阶段 C 落实。（未验证）

MINOR（第 1 轮 (e)） | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:14 | lock 注释已改正，不再引用不存在的报告。自写 LoRA 的单元测试第 4 项属阶段 B，未修（前瞻）。 | 同左 | 阶段 B 落实。（未验证）

MINOR（第 1 轮 (f)） | reports/IMPL_A_REPORT.md（不存在） | 未修：五个无冻结字段文件所选的字段，尚未在报告中列出并报 Review Gate 备案。 | Glob reports/IMPL* 无结果 | 写 IMPL_A_REPORT 时列出。（未验证：Glob）

## 二、本轮改动引入的新问题
MINOR（N1） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:149-191 | 换行转换的修复只覆盖了四个冻结文件。PROTOCOL_FROZEN 本身总是从工作区读取，按 "\n" 切行后再用 re.fullmatch 匹配。CRLF 检出时，每行末尾留下 \r，以下几处都会匹配失败：标题 `## (v[0-9.]+)\(当前有效\)`、冻结提交行（以 `\|` 结尾）、文件哈希行、表格行。结果是未被篡改也会停在 ST12。这与本轮依据的 PROTOCOL_FROZEN 第 26 行说明（检出可能做换行转换）不一致。误判的方向是停止（BLOCKED），不会产生错误结果。 | `lines = text.split("\n")`；`re.fullmatch(r"## (v[0-9.]+)\(当前有效\)", lines[i])` | 解析前把 CRLF 换成 LF，或在 RUNBOOK 中禁止 autocrlf 检出。（未验证：读代码）

MINOR（N2） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:381-385 | 工作区 manifest 按解析结果比较，下列一字节改动都不会停：
- 空白（例如空格改成 tab）；
- 数字写法，`1.0` 改成 `1e0` 只差一个字节；
- Python 中 `1 == 1.0 == True`。
所有计算用的都是冻结提交的 blob，所以不影响计算。但如果 Review Gate 认为任务指令第 6 节第 10 项的「冻结文件」包括工作区副本，这里就做不到「改一个字节立即停止」。按解析结果比较是第 8 节第 1 步会改写 manifest 所必需的。 | `same = strip_step1_fields(rel, json.loads(wt)) == strip_step1_fields(rel, json.loads(blobs[rel]))` | 作为第 1 轮 MAJOR #1 ③ 的附带事项，一并交 Review Gate。（未验证：读代码）

MINOR（N3） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:384 | 死代码。strip_step1_fields 改用 `pop(..., None)` 并加了 isinstance 检查之后，KeyError、AttributeError 已不可能出现，TypeError 也没有来源；实际只剩 ValueError（JSONDecodeError / UnicodeDecodeError）。 | `except (ValueError, KeyError, AttributeError, TypeError):` | 只保留 ValueError。（未验证：读代码）

MINOR（N4） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:233-240 | 检查本身符合协议第 0 节「库版本 torch 2.11.0, transformers 5.22.2 … 不一致即 BLOCKED」、第 11 节 ST8 和第 9 节 BLOCKED 一行；版本值来自 DATA_MANIFEST model.libraries，与协议第 38 行一致。有三点需要登记：
1. 忽略 `+local` 标签是一项执行解释。它与 PEP 440 中 `==` 的匹配规则一致，但会把 `2.11.0+cpu` 一类构建也视为 2.11.0。
2. 版本取自发行包元数据，不是模块的 `__version__`。两者在本环境中确实不同：t1_lock.txt:986 为 `torch 2.11.0+cu130`，t2_fetch_generate.txt:124 为 `"torch": "2.11.0"`。
3. verify 命令会执行检查，但不打印实际版本。阶段 A 没有实验记录，所以这一点暂不构成问题。 | `if v.split("+")[0] != want:` | 在 IMPL_A_REPORT 中登记这一解释，请 Review Gate 确认。阶段 B 的 record.py 同时记录元数据版本和 `torch.__version__`。我判断这不是缺陷，所以列为 MINOR；按指令第 9 节它涉及协议一致性，至少应登记确认。（部分已验证：t1_lock.txt:986、t2_fetch_generate.txt:124）

MINOR（N5） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_data_hashes.py:39-44 | dev_qa、general_dev、anchor 的期望行数由 `D.params(fz)`（被测代码的解析器）计算。如果 params 解析出错，生成的数据和期望值会一起出错，测试仍然通过。改动前的字面值（320/100/512）是独立的期望值。当前数据本身没有问题：t2_fetch_generate.txt:129-136 打印的行数为 160/120/120/240/320/160/100/512，与协议第 66、146、147 行一致。 | `"dev_qa.jsonl": total * p.dev_per_fact`、`"anchor_text.jsonl": p.anchor_n_docs` | 测试里用自己的正则直接读 manifest 字段，或者恢复字面值并注明协议出处。这条涉及数据核对，按第 9 节建议修。（未验证：读代码）

MINOR（N6） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_leakage.py:115 | 新增的 test_cli_bad_split_manifest 仍只断言 `"ST12" in r.stderr`。如果 ST12 从别的路径触发（例如 load 或 check_data_dir），这个测试也会通过。 | `assert "ST12" in r.stderr and not (tmp_path / "x.json").exists()` | 改为断言 `--split-manifest .* differs from SPLIT_MANIFEST.json`。（未验证）

MINOR（N7） | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:17 | 引用的 reports/IMPL_A_REPORT.md 在本提交中不存在。与第 1 轮 lock 第 10 行是同一类问题，只是换了位置。 | `(open item for Review Gate, reports/IMPL_A_REPORT.md)`；Glob 无结果 | 阶段报告与本提交一起入库，或先改写这处引用。（未验证：Glob）

MINOR（N8） | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:226-232 | docstring 说覆盖 U+2028 和 U+0085，测试数据只有 U+0085，也没有覆盖 U+2029。 | `rows = [{"text": "a b\u0085c"}, {"text": "d"}]` | 加入   和  。（未验证）

## 三、按第 1 轮重点对完整暂存 diff 的整体复核
- **metrix/ 以外无改动**：20 个文件全部在 metrix/e1-pilot/ 下。（已验证：review_input_round2.diff:3-23）
- **数据与哈希**（已验证）：
  - 修改后生成的 gen4 与 gen1 逐字节相同（t2_fetch_generate.txt:152）。
  - 4 个冻结哈希读回后与 PROTOCOL_FROZEN 相同，verify 通过（t2_fetch_generate.txt:137-141、155-161）。
  - 与参考脚本逐字节相同的测试和单元测试 1 均通过（t4_pytest.txt:139-143）。
- **单元测试 10**：51 项全部 PASSED（已验证：t4_pytest.txt:191）。新增的覆盖有：
  - CRLF 与 step 1 字段的正向对照；
  - 泄漏命令上的 ST12；
  - 8 个数据文件各自的具体报错信息表。
- **requirements.lock**：只改了注释，requirements 和哈希不变（已验证：t1_lock.txt:1023-1024）。
- **TEST 隔离**：本轮没有改动相关路径（未验证：读代码）。
  - general DEV 仍只按行前缀判断 split，只解析 split=="dev" 的行（data.py:487-519）。
  - 泄漏模块不打开任何 TEST 文件（leakage.py:140-144）。
  - write() 在输出目录中已有 TEST 文件时拒绝写入（data.py:568-570）。
  - 没有任何代码路径生成或读取 test_qa.jsonl 或 general_test.jsonl。
- **L1–L6 口径**：与第 1 轮相同（未验证：读代码）；gen1 与 gen4 的泄漏报告除 frozen_commit 字段外相同（已验证：t3_leakage.txt:132）。
- **冻结参数**：本轮把 E1P、L/U、种子改为从冻结 manifest 读取（未验证：读代码）。src 中没有新增写死的协议数值。test_environment.py:29 的 `"+cu130"` 和 `".1"` 只用于构造测试输入。
- **打分、训练、arm、chat template**：不在阶段 A 范围，本轮没有相关代码。

结论：PASS
