# code-reviewer final report, Implementation stage A, round 1: staged work commit (parent 8149d8727b4a99ea0cc9b0a1a2ebd82bd53fa0af); invoked 2026-11-22 16:35 UTC (background); invocation text: code-reviewer_prompt.txt; input: review_input.diff (in this directory: review_input_round1.diff)
# extracted unchanged by metrix/e1-pilot/reports/round6/review_extract.py from this session's subagent transcript (agent-a3ca4521e269f0264.jsonl)
---
code-reviewer 审查：Metrix E1-PILOT Implementation 阶段 A 工作提交（暂存，父提交 8149d872）。没有 BLOCKER，有 2 条 MAJOR，结论 PASS。

依据：仓库定义 /home/user/OpenMythos/.claude/agents/code-reviewer.md、协议 v1.1、PROTOCOL_FROZEN 当前有效节、/home/user/OpenMythos/metrix/e1-pilot/tasks/IMPLEMENTATION_TASK_ORDER_V1.md。审查方工具只有 Read、Grep、Glob，没有运行任何代码。
- 标「已验证」的条目引用了本提交暂存的原始输出（/home/user/OpenMythos/metrix/e1-pilot/reports/impl_a/ 下的 t0–t4，写明路径与行号）。
- 只靠读代码或 grep 得出的判断一律标「未验证」。

## 问题清单
严重度 | 文件:行号 | 问题 | 证据 | 建议

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:344-359（另见 198-210） | 即 (a)。load() 把工作区四个文件与冻结提交比对，不一致按 ST12 处理。这超出协议第 11 节 ST12 的比对范围 (2)：范围 (2) 只规定用 git cat-file 读冻结提交。
① 协议文件与 SEARCH_SPACE.json 按原始字节比，与 PROTOCOL_FROZEN 第 26 行「以 git cat-file … 为准(检出时若做换行转换,工作区字节会不同)」冲突。换行转换的检出会被误判为 BLOCKED。
② manifest 只排除每个 files 条目的 status/byte_sha256/canonical_sha256，以及 split_sha256 的值（键仍参与比较）。第 1 步若在 files 或 split_sha256 中新增键，也会被误判为 ST12。
③ 包内所有取值都来自冻结提交的 blob，这项检查不影响任何计算，作用只是发现工作区被改。
不确定之处：指令第 6 节第 10 项「篡改任一冻结文件」若指工作区副本，这项检查就是必需的；这一点只有 Review Gate 能定。 | `same = wt == blobs[rel]`；`entry[k] = None` for STEP1_DATA_FIELDS | 交 Review Gate 裁决。若保留：协议文件与 SEARCH_SPACE.json 先做换行归一化再比，或在 RUNBOOK 中禁止 autocrlf 检出；排除范围按协议原文对齐。（未验证：读代码；当前工作区比对通过见 t2_fetch_generate.txt:17）

MAJOR | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:2-3 | 指令第 5 节「依赖」要求 Python 锁定版本。lock 只在注释中写了「CPython 3.13」，没有补丁号，代码中也没有任何运行时核对。参考实现与本次安装用的都是 3.13.18。不确定之处：「3.13」是否算锁定。 | `# Target: ... CPython 3.13`；t1_lock.txt:862「3.13.18」 | 写明 CPython 3.13.18，并在 frozen.load 或记录中核对 sys.version。（已验证：lock 原文、t1_lock.txt:862）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:577-593 | 即 (b)。对没有冻结哈希的 train_F、train_Y、dev_qa、general_dev 及 anchor ids，用「按冻结输入重新生成后逐字节比对」作参照，不一致记 ST12/BLOCKED。行为符合指令第 6 节第 10 项。ST12 这个标签超出了协议范围 (1) 的字面，但与第 10 项的标题「ST12」一致。 | `raise ST12Error("... differs from its regeneration ...")`；t4_pytest.txt:83-90 八个数据文件均 PASS | 在 IMPL_A_REPORT 中登记为执行解释，请 Review Gate 确认状态标签。（已验证：t4_pytest.txt:83-92）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:570；/home/user/OpenMythos/metrix/e1-pilot/tests/test_leakage.py:94-95 | 潜在缺陷：str.splitlines() 会在 U+0085、U+2028、U+2029 处断行。json.dumps(ensure_ascii=False) 不转义这三个字符，文本中一旦出现，file_hashes 会 JSONDecodeError。当前数据未触发。 | `raw.decode("utf-8").splitlines()` | 改用 split("\n") 或按行读文件。（部分已验证：t2_fetch_generate.txt:33-40 正常输出；缺陷本身未验证）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:43；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:201、137/158；/home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:122/173、219、225-227 | 死代码与未用项：
- TEMPLATE_SETS 未被引用；
- load_qwen_tokenizer 的参数 fz 未用；
- anchor_source[3]（a_sha）未用；
- 阶段 A 中 source_sha256、protocol_text、Frozen.seeds 都没有使用方。 | grep 结果 | 删除，或注明留给哪个阶段使用。（未验证：grep）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:152-153 | "E1P" 与 learned→L、unread→U 写在代码里。第 95 行有对 fact_id_format 的正则全匹配兜底。 | `exposure_letter={"learned": "L", "unread": "U"}, ... fact_prefix="E1P"` | 从 fact_id_format 的匹配结果中取。（未验证：读代码）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_data_hashes.py:37-41 | 测试写死了协议数值：160/120/240/320/100/512 与 F 1889、Y 2260。作为独立预期值可以接受，但红线 6 说的是「代码」。 | `assert (r["F_tokens"], r["Y_tokens"]) == (1889, 2260)` | 能从 manifest 读的（facts.total、per_cell 等）改为读取；只在协议正文里的数值注明出处。（未验证：读代码）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:75、89、115、161 | 只断言 match="ST12"，可能从另一条 ST12 路径通过。例如 manifest 被改后，可能先在解析或字段核对处报错，而不是在范围 (2) 的哈希比较处。 | `pytest.raises(ST12Error, match="ST12")` | 断言具体信息，例如 "at the frozen commit .* has sha256"。（未验证）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/tests/test_st12.py:4、106-116 | docstring 说会篡改 PROTOCOL_FROZEN 本身，实际只改了哈希的十六进制位。改正文、v1 节或表格其它列的一个字节不会停。若第 10 项的「冻结文件」= 协议 + 三个 JSON（与指令第 5 节 frozen.py 一行的用词一致），这样可以接受。 | `text.replace(sha, other)` | 在报告中写明第 10 项对 PROTOCOL_FROZEN 的覆盖范围，并修正 docstring。（未验证）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/leakage.py:184-189 | 协议命令只执行 FZ.load()，没有对 --data 做 ST12 范围 (1) 的核对（check_data_dir 或 verify）。单独使用时，可能对被篡改的数据给出 PASS。 | `report = run_gate0(fz.split_manifest, load_data(a.data))` | 调用 fz.check_data_dir(a.data)（不需要输入目录）；或在 RUNBOOK 和 run_pilot 中保证先跑 verify。（未验证）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:10 | 引用的 reports/IMPL_A_REPORT.md 在本提交中不存在（Glob 无结果）。 | `decision recorded in reports/IMPL_A_REPORT.md` | 阶段结束时补上报告，或先改写引用。（未验证：Glob）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/requirements.lock:4 | 锁定的是 torch 2.11.0+cu130，A100 主机需要支持 CUDA 13 的驱动，否则运行时会触发 ST8。 | t1_lock.txt:986「torch 2.11.0+cu130 cuda build 13.0」 | 在 RUNBOOK（阶段 C）写明驱动下限。（已验证：版本字符串；GPU 兼容性未验证）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/frozen.py:213-279 | 指令第 5 节要求 frozen.py「提供全部冻结常量」。G0、ST 门槛只在协议正文里，frozen.py 只暴露原文 protocol_text，没有解析出的门槛。 | Frozen 只提供 seeds、templates、data_hash | 阶段 B 从 protocol_text 解析门槛，不得写死。（未验证：前瞻）

MINOR | /home/user/OpenMythos/metrix/e1-pilot/src/metrix_e1/data.py:514-519 | 生成数据前没有核对库版本是否等于 DATA_MANIFEST model.libraries（协议第 0 节：「不一致即 BLOCKED」）。哈希比对只能发现输出不同，发现不了版本不同。 | generate() 中无版本检查 | 阶段 B/C 在第 1 步前执行 ST8 的版本核对。（未验证：前瞻）

## 重点核对结论（按指令第 9 节）
- **与协议逐条一致（未验证：读代码）**：
  - L1–L6 口径与 SPLIT_MANIFEST 一致：L2 取 n=4、上限 0.25；L6 词=str.split()，13-gram 在每篇文档内取后合并求交，文本是送入模型的 id 解码所得，token 13-gram 只报告。
  - 名字生成、S 置换、候选的调用顺序与参考脚本逐行对应。
  - 锚文本在名字之前生成。
  - general DEV 只取 split=="dev" 每域前 25 个窗口。
- **冻结参数（未验证：读代码）**：src 中的种子、模板、哈希、长度、概率、上限都从冻结提交的 blob 读取。代码里的规则串（SERIALIZATION_SPEC 等）和正则里的数字只用于与 manifest 比对，不一致即停。写死项见上面 MINOR。
- **TEST 隔离（已验证：t2_fetch_generate.txt:32「rows parsed and decoded: 100」；其余为读代码）**：
  - test 行只由文本 IO 读入，用前缀正则取 split 字段并计数，不做 JSON 解析，也不做 parcae 解码。这与协议第 3 节「解析 split 字段、计数不算」和第 6 轮参考脚本相同。
  - 整个 eval_sets.jsonl 求文件哈希，符合指令第 3 节第 3 项。
  - L1、L2 只用模板，没有实例化任何 TEST 问句。
  - 没有任何路径生成或读取 test_qa.jsonl、general_test.jsonl。write() 只检查这两个文件是否存在。
- **ST12（已验证：t2_fetch_generate.txt:17、t4_pytest.txt:64-93）**：
  - 范围 (1)：12 行全部比对。4 个内容哈希由 generate/check_data_dir 比对；模板集合由 _check_templates 比对；7 个文件字节哈希由 check_inputs 比对；12 个值还逐一与冻结提交 manifest 中对应字段交叉核对。
  - 范围 (2)：从 PROTOCOL_FROZEN 当前节读出 87a244db…，用 git cat-file 读取后核对。
  - 符合指令第 3 节第 1、2 项；超出部分见 (a)、(b)。
- **data.py 与参考脚本逐字节相同（已验证：t4_pytest.txt:54；t2_fetch_generate.txt:67-76、112-113 两次及第三次生成逐字节相同）**：
  - 在同一环境中用 -I 运行参考脚本，比对了 facts（规范化列表）、锚文本（文本列表）、train_S 与 candidates（原始字节）、general DEV（domain/doc_id/ids/text）。证明成立。
  - train_F、train_Y、dev_qa 没有参考脚本输出可比，只比了 Y/F token 数 1889/2260。anchor 的 ids 没有参考输出。
- **单元测试 1（已验证：t4_pytest.txt:50）**：从写出的文件读回，重算四个哈希，与 PROTOCOL_FROZEN 全值及指令给出的前缀比对。确实检验了指令所说的内容。
- **单元测试 10（已验证：t4_pytest.txt:64-93）**：覆盖冻结提交中的 4 个文件、工作区的 4 个文件、PROTOCOL_FROZEN 中的哈希值、eval_sets、6 个输入文件、8 个数据文件，以及 CLI 的 RESULT: FAIL 与非 0 退出。缺口见上面 MINOR（PROTOCOL_FROZEN 正文字节；断言过宽）。
- **requirements.lock（已验证：t1_lock.txt:864-990）**：
  - torch 2.11.0、transformers 5.22.2 与协议第 0 节一致。
  - 全部带哈希，--require-hashes --no-deps 安装成功，pip check 通过。
  - 缺口：Python 补丁版本（MAJOR）。
  - 能否用 Qwen3 的 chat template 本阶段没有测试（未验证，属阶段 B）。
- **metrix/ 以外无改动（已验证：review_input.diff 第 3-21 行的 stat）**。

## (a)–(f) 判断
(a) MAJOR，交 Review Gate。超出 ST12 范围 (2)，与 PROTOCOL_FROZEN 第 26 行冲突，manifest 的排除范围比协议原文窄。但它可能正是指令第 6 节第 10 项所需。（未验证）
(b) MINOR，与指令第 6 节第 10 项一致。ST12 这个状态标签请 Review Gate 确认，在 IMPL_A_REPORT 中登记。（已验证：t4_pytest.txt:83-92）
(c) 与协议一致。L4 原文是「任何训练语料」，arm A 在锚文本上训练，L3a 的语料清单也含 anchor_text，比只查 train_* 更严格，无需交 Review Gate。在报告中写明这一口径即可。（已验证：t3_leakage.txt:76-84）
(d) 与协议和指令一致。协议第 3 节的命令必须能跑，src/metrix/e1_pilot 只是一个无逻辑的转接层，实现仍在 src/metrix_e1/，指令第 4 节的目录树没有说只能有这些。需要 PYTHONPATH=metrix/e1-pilot/src，必须写进 RUNBOOK。依赖 namespace package：仓库根目录 metrix/ 下若日后加了 __init__.py，这条命令会失效。（已验证：t3_leakage.txt:13-24）
(e) 与指令一致。原文是「peft（若使用）」，不用就无需锁定。阶段 B 的自写 LoRA 须由单元测试第 4 项覆盖：B=0、alpha=2×rank、dropout 0、28 层 × 7 个模块。lock 注释引用的报告还不存在（见 MINOR）。（未验证）
(f) 属于协议未覆盖。协议第 2.8 节说字段见 DATA_MANIFEST，但 DATA_MANIFEST 对这五个文件只写了 content。这些文件没有冻结哈希，第 1 步写入的哈希又不在 ST12 范围内，所以字段由实现自定，不影响协议一致性。按 metrix/CLAUDE.md 第 8 节，以及 v1-r8 由 Review Gate 定记录格式的先例，应在 IMPL_A_REPORT 中列出所选字段，报 Review Gate 备案。不阻塞。字段内容本身合理：anchor 与 general_dev 保存了送入模型的 ids，符合 n_x、n_w「不解码再编码」的要求。（未验证：读代码）

结论：PASS
