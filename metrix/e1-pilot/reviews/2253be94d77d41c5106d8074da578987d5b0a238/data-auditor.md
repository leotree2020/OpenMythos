# data-auditor raw output — Round 4 task 5, range 7e5dd9c..2253be94d77d41c5106d8074da578987d5b0a238 (3 commits)
# Invoked by the Executor via Agent(subagent_type="data-auditor") in session_01J5mxaVWCGyNj16YJV8cPy5, 2026-11-21 ~05:07Z, in parallel with code-reviewer.
# Invocation text: data-auditor_prompt.txt (same directory), sent verbatim. The auditor's scripts are in metrix/e1-pilot/audit/ and the full stdout of every run in metrix/e1-pilot/audit/stdout/2253be94d77d41c5106d8074da578987d5b0a238/ (committed alongside this file).
# Below the line: the subagent's final report exactly as the harness delivered it (the harness indents every line by 2 spaces; kept, nothing removed).
---
  ## Data Auditor 报告:Metrix E1-PILOT 第 4 轮,范围 7e5dd9c0..2253be94(HEAD = 2253be94d77d41c5106d8074da578987d5b0a238)
  
  A–D 四项我都用自己的脚本复算了,结果与 Executor 的原始输出全部一致,没有不一致项,也没有本轮范围内无法复算的项。结论为 PASS。
  
  **运行环境**
  - 主机 `vm`(云容器,4 CPU,无 GPU,PATH 上没有 nvidia-smi),只用 CPU。
  - venv 中的 Python 3.13.18、transformers 5.22.2、tokenizers 0.23.3,无法 import torch。
  - 只加载了分词器,没有加载模型权重。分词器目录里没有任何权重类文件。
  
  **分词器核对(01)**
  - 6 个分词器文件都由我自己核对:sha256 或 git-blob-sha1 与 huggingface_hub 下载元数据里的 etag 相同,元数据记录的 revision 都是 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e。
  - tokenizer.json 的 sha256 为 aeb13307…,tokenizer_config.json 为 d5d09f07…,与 Executor 记录的相同。
  
  **独立性**
  - 全部脚本都是我自己写的,位于 /home/user/OpenMythos/metrix/e1-pilot/audit/。
  - 本轮新增:r4_env.py、r4_anchor.py、r4_regen_facts.py、r4_manifests.py、r4_kprime.py、r4_scoring_em.py、r4_leak_supp.py、r4_compare_prev.py、run_logged.sh。
  - 沿用上轮的 a1_facts.py、a3_scoring.py、a4_cands_templates.py、common.py,均未修改。
  - 没有 import、调用或复制 Executor 的代码。reports/round4/st_prefix_check.py 只读过,用于确认它的检查与协议语义一致、不是同义反复。
  
  **中间数据**
  - 我生成的锚文本和 fact 放在 /tmp/claude-0/-home-user/157f690a-eee2-5858-8b75-b3efebc1267b/scratchpad/audit_r4/(anchor.json、facts.json),没有写进仓库。
  - 复算的输入是我自己从 parquet 重建的锚文本。Executor 的 r4/facts.json 和 r4/anchor.json 只在脚本最后一行用于比对。
  
  **TEST**
  - 仓库中没有 PROTOCOL_FROZEN 文件:已跟踪文件和磁盘上的文件名都没有命中(01)。
  - 没有生成、读取或实例化任何 TEST 问句。
  - 只有 a4 的 L1/L2 对 32 个模板(含 TEST 模板文本)做了归一化与哈希,与上轮相同。
  
  **完整 stdout**
  - 每次运行一个文件,第一行是命令行,stdout 与 stderr 合并且未删改。
  - 目录:/home/user/OpenMythos/metrix/e1-pilot/audit/stdout/2253be94d77d41c5106d8074da578987d5b0a238/,共 01–12 号文件。
  - 我没有 git add 或 commit,提交由 Executor 负责。
  
  **命令记号**
  - 所有命令都在 metrix/e1-pilot/audit 下执行。
  - 命令为 `HF_HUB_OFFLINE=1 bash run_logged.sh $O/<文件> $PY ...`(04、11、12 号这三次运行没有设 HF_HUB_OFFLINE)。
  - `PY` = /tmp/claude-0/-home-user/157f690a-eee2-5858-8b75-b3efebc1267b/scratchpad/venv/bin/python
  - `S` = /tmp/claude-0/-home-user/157f690a-eee2-5858-8b75-b3efebc1267b/scratchpad
  - `O` = stdout/2253be94d77d41c5106d8074da578987d5b0a238
  
  ---
  
  ### A. 按第 2.2 节重新生成 fact;DATA_MANIFEST 改动范围;锚文本哈希
  
  **命令**
  ```
  $PY -I -B r4_env.py $S/qwen_tok /home/user/OpenMythos                                                    -> 01_r4_env.txt
  $PY -I -B r4_anchor.py $S/r4/cache/data/sample-100BT/train/shard_00000.parquet $S/qwen_tok ../DATA_MANIFEST.json $S/audit_r4/anchor.json $S/r4/anchor.json   -> 02_r4_anchor.txt
  $PY -I -B r4_regen_facts.py $S/qwen_tok $S/audit_r4/anchor.json $S/audit_r4/facts.json $S/r4/facts.json -> 03_r4_regen_facts.txt
  $PY -I -B r4_manifests.py /home/user/OpenMythos 7e5dd9c03f5bb9108ea640f2591015497fa70d5c 2253be94d77d41c5106d8074da578987d5b0a238   -> 04_r4_manifests.txt
  ```
  
  **原始输出(摘录;全文见对应文件)**
  ```
  parquet sha256: 6a3450ea…3092c22 | pinned: 6a3450ea…3092c22 | match: True
  documents read 527 kept 512 | canonical sha256 of the texts list 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
  total chars 309172
  FINAL COMPARISON with Executor anchor file: equal = True
  --- 03
  cell capital/natural: entity_draws 28, ... target (K_st,K_qa) (3, 3), ... answer_draws 84
  cell capital/random: entity_draws 20, ... (5, 5) ... answer_draws 52
  cell currency/natural: 31 ... (3, 3) ... 82 | currency/random: 20 ... (6, 6) ... 46
  cell founder/natural: 30 ... (3, 3) ... 81 | founder/random: 21 ... (5, 5) ... 45
  cell river/natural: 34 ... (3, 3) ... 89 | river/random: 20 ... (6, 6) ... 42
  anchor-rule rejections: 0
  regenerated facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
  MATCH: True
  FINAL COMPARISON with Executor facts file: equal content = True
  --- 04
  29850491..b1f5889c: [('added','model.input_convention.em_generation'), ('added','model.input_convention.general_text_and_anchor'), ('changed','name_generation.answer_token_length_rule.purpose')]
  7e5dd9c0..29850491: []   b1f5889c..2253be94: []
  exactly the 3 keys named by the Executor: True
  name_generation leaves other than .purpose: 39 identical: True
  seeds./facts./anchor_text./general_text./files./hashing./s_permutation/templates. leaves identical: True
  DATA_MANIFEST name_generation vs constants transcribed from protocol 2.2: 13 项全部 True
  protocol section 2.2 changed lines: 只有细节 3 一行;the new line starts with the whole old line (pure append): True
  ```
  
  **与 Executor 是否一致:一致。**
  - **锚文本:** 哈希 8828bc4f…、读 527 篇、保留 512 篇、309172 字符,与 reports/round4/t0_facts_regen.txt 相同。
  - **fact:** 规范化哈希 406c8801… 与协议和 t0 相同。8 个 cell 的目标数对,以及 entity_draws/answer_draws 都与 t0 的 cell log 相同。
  - **DATA_MANIFEST:** 在本范围内只改了 Executor 所说的 3 个键,全部在 b1f5889c 中。生成规则的叶子全部未变。
  - **协议第 2.2 节:** 只是在细节 3 末尾追加了一句说明,规则未变。
  
  ---
  
  ### B. s_ST 的 K'(1,800 对)
  
  **命令**
  ```
  $PY -I -B r4_kprime.py $S/qwen_tok $S/audit_r4/facts.json ../SPLIT_MANIFEST.json   -> 05_r4_kprime.txt
  ```
  
  **原始输出**
  ```
  learned facts: 120 | (fact, same-cell learned answer) pairs: 1800
  pairs where tokens of prefix(f) are NOT a prefix of tokens of prefix(f)+' '+c: 0
  pairs where the following tokens != encode(' '+c): 0
  pairs where the number of following tokens != K_st(c): 0
  K' per cell: {'capital/natural': [3], 'capital/random': [5], 'currency/natural': [3], 'currency/random': [6], 'founder/natural': [3], 'founder/random': [5], 'river/natural': [3], 'river/random': [6]}
  cells with more than one K': 0
  with the final '.': prefix not a token prefix: 0 | answer span != encode(' '+c): 0 | last token != encode('.'): 0
  example E1P-L-capital-nat-01 prefix(f) "The capital of Krultrouth is" c "Linnuth"
    ids [785, 6722, 315, 16447, 360, 376, 2898, 374, 444, 6130, 940] scored [444, 6130, 940]
  ```
  
  **与 Executor 是否一致:一致。**
  - 对数、两个不一致数、每个 cell 的 K' 以及示例 id,都与 reports/round4/t2_st_prefix_check.txt 逐项相同。
  - 我另外检查了带句末 "." 的训练文本,不一致数也为 0。
  - 每个 cell 的 K' 与 C 项 s_QA 的 K 相同,符合协议写的“与 s_QA 的 K 相同”。
  
  ---
  
  ### C. 打分与 EM 的输入
  
  **命令**
  ```
  $PY -I -B r4_scoring_em.py $S/qwen_tok $S/audit_r4/facts.json ../SPLIT_MANIFEST.json   -> 06_r4_scoring_em.txt
  $PY -B a3_scoring.py $S/qwen_tok $S/audit_r4/facts.json ../SPLIT_MANIFEST.json          -> 10_a3_scoring.txt
  bash -c 'diff <(tail -n +5 ../reports/round3/t7_verify_scoring.txt) <(tail -n +5 ../reports/round4/t2_verify_scoring.txt) && echo "bodies identical"; ...'   -> 12_diff_executor_verify_r3_r4.txt
  ```
  
  **原始输出(06 摘录)**
  ```
  bos None None | eos '<|im_end|>' 151645 | pad '<|endoftext|>' 151643 ; ids 151643/151644/151645/151667/151668
  encode with/without add_special_tokens equal: True
  encode('The answer is') = [785, 4226, 374]
  DEV questions: 320 | (question, pool candidate) scoring sequences: 4000
  questions where encode(chat(q)) != apply_chat_template(tokenize=True) ids: 0
  questions where encode(chat(q)) is not a token prefix of encode(EM context): 0
  SCORING SEQUENCES whose context tokens != EM-context tokens: 0
  scoring sequences whose scored tokens != encode(' '+c): 0
  ... continue_final_message=True text != EM context text: 0 ; ... != scoring text: 0
  pairs: 240 | TRAIN statements not token-aligned around ' '+answer: 0 | MISMATCHES: 0
  scored-token counts per cell: {capital/natural [3], capital/random [5], currency/natural [3], currency/random [6], founder/natural [3], founder/random [5], river/natural [3], river/random [6]}
  input_ids (28): [151644, 872, 198, 3838, ..., 785, 4226, 374, 444, 6130, 940]  scored slice start 25 ids [444, 6130, 940]
  ```
  
  12 号文件的输出是 `bodies identical`:Executor 第 3 轮与第 4 轮 verify_scoring 输出的正文确实相同。
  
  **与 Executor 是否一致:一致。**
  - **EM 与打分的上下文:** 全部 320 条 DEV 问句(160 fact × 2),对池中每个候选(同 relation、stratum、暴露类别,是任意 4 选 1 候选表的超集),EM 上下文 `chat(q) + "The answer is"` 的 token 与打分序列的上下文 token 完全相同,共 4,000 条序列,不一致 0。
  - **240 对:** 打分 id 与 TRAIN 陈述句答案片段的不一致数为 0。
  - **与 t2_verify_scoring.txt 逐项相同:** 特殊 token、每个 cell 的 token 数、28 个 id 的示例和打分起点 25。
  
  ---
  
  ### D. 候选可行性、模板哈希、L1–L5、split 计数、内联副本、L6
  
  **命令**
  ```
  $PY -B a4_cands_templates.py $S/qwen_tok $S/audit_r4/facts.json ../SPLIT_MANIFEST.json ../METRIX_E1_PROTOCOL.md   -> 07_a4_cands_templates.txt
  $PY -B a1_facts.py $S/audit_r4/facts.json $S/audit_r4/anchor.json ../SPLIT_MANIFEST.json                           -> 08_a1_facts.txt
  $PY -I -B r4_leak_supp.py $S/qwen_tok $S/audit_r4/facts.json $S/audit_r4/anchor.json ../SPLIT_MANIFEST.json        -> 09_r4_leak_supp.txt
  $PY -I -B r4_compare_prev.py ../reviews/596fcfad…/data-auditor.md ../reports/round3/t8_candidate_feasibility.txt ../SPLIT_MANIFEST.json $O/02… $O/03… $O/07… $O/08… $O/10…   -> 11_r4_compare_prev.txt
  (内联副本、manifest 未改:04_r4_manifests.txt)
  ```
  
  **原始输出(摘录)**
  ```
  pools: 16 ; 每个 (relation, stratum) 的 learned 池 15、unread 池 5;K = 3/5/3/6/3/5/3/6
  (rel,stratum,exposure) groups split across >1 token count: []
  facts: 160 min pool size over facts: 5 max: 15
  pools with < 4 answers: []      facts with < 3 distractors: []
  templates: 32 normalized/hash mismatches vs manifest: 0
  template_set_sha256 recomputed: 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f manifest: 同 match: True
  protocol 2.4 table == manifest template texts: True ( 16 rows )
  L1 cross-set duplicate normalized hashes: []
  L2 max Jaccard word-4gram across sets: (0.2, ('capital.TRAIN.1', 'capital.DEV.1')) limit 0.25, within: True
  --- 08
  fact_id order equals generation order rule: True
  L5 learned & unread fact_id intersection: 0 ; distinct fact_ids: 160
  L5 strings: 320 distinct: 320 duplicates: 0
  DEV questions: 320 (protocol: 160 facts x 2 = 320) learned: 240 unread: 80
  TRAIN statements (learned only): 120 (protocol 120)
  L3a (anchor part) unread entity/answer hits: 0 []   L3b learned answer hits in anchor: 0 []
  L3a (train_F/train_Y part) unread hits: 0
  L4 (DEV) verbatim DEV questions in F/Y/S-superset: 0
  --- 09
  sizes: TRAIN 120 | S 120 | S-superset 1800 | Y 240 | DEV 320 (learned 240 unread 80)
  L3a S-superset: unread entity/answer hits: 0
  S exposure: (learned answer, S line) with count != [line uses that answer]: 0
  L4 (DEV, case-insensitive) in train_F / S-superset / train_Y / anchor: 0 / 0 / 0 / 0
  tokens ... with one EOS per sequence: F 1889, Y 2260, Y/F 1.196
  --- 11
  Executor round-3 t8 pools: 16 | this round a4 pools: 16 | identical (keys incl. K, and sizes): True
  L1 consistent: True   L2 consistent: True
  --- 04
  SPLIT_MANIFEST.json / SEARCH_SPACE.json: base==head True (sha256 b5090f3c… / 307dde04…)
  inline text == file text: True | parsed JSON equal: True
  DATA_MANIFEST files: 全部 NOT_GENERATED / null;split_sha256 与 candidate_mapping_sha256 全部 null
  outside-metrix changes inside the audited range: (none)
  ```
  
  **与上一轮及 Executor 是否一致:一致。**
  - **候选可行性:** 16 个池,最小值 5,不足 4 的 cell 为 0,与 Executor 第 3 轮 t8 逐池相同(含 K 值)。
  - **模板、L1、L2:** 模板哈希、template_set_sha256 和 L1/L2 结果与 manifest 的 authoring_result 以及我上轮的结果相同。
  - **split:** fact_id 互斥;各 split 数量符合第 2.1、2.3、2.6 节(TRAIN 120、S 120、Y 240、DEV 320)。TEST 的 480 条按规定未实例化。
  - **L3a、L3b、L4、L5:** 都为 0。
  - **Y/F token 比:** 每条序列计一个 EOS 时为 1.196,与协议第 2.6 节相同。
  - **对比上轮报告(11):** 上轮报告代码块中有 71 行,其中 52 行在本轮输出中逐字出现。其余 19 行是上轮手工缩写的行、小节标题、git status 行,以及改用 r4_* 脚本后格式不同的行。这些行我逐行看过,数值都相同。
  - **内联副本与 manifest(04):** SEARCH_SPACE.json 内联副本与文件逐字一致,与 t1_json_inline_check.txt 相同。SPLIT_MANIFEST 和 SEARCH_SPACE 在本范围内未改。
  - **数据文件哈希:** 所有数据文件都未生成,哈希都为 null,本轮没有可比对的数据文件哈希,Executor 也没有声称。
  
  **L6 不在本轮范围,不是复算失败。** 它需要 general_dev.jsonl(04 显示为 NOT_GENERATED)和 parcae 分词器,而我的规则只允许加载 Qwen 分词器。本轮改动不涉及 L6,Executor 也没有提出 L6 结论。
  
  ---
  
  ### 观察(不阻断,供 Review Gate 参考)
  
  1. **EM 输出是否含停止 token 没有写明。** 协议写了“遇 im_end 停”,但没说 im_end 是否算输出的一部分,也没说解码时是否跳过特殊 token。06 的模拟显示:如果输出包含 im_end 且不跳过特殊 token(`" Linnuth.<|im_end|>"`),160 个正确答案的 EM 全部为 0。建议写明 output = 解码 im_end 之前的新 token,或使用 skip_special_tokens=True。
  2. **固定 revision 的 generation_config.json 默认值与协议不同。** 它是 do_sample=true、temperature 0.6、top_k 20、top_p 0.95、eos [151645, 151643];协议要求贪心解码,只在 151645 停。实现时必须显式覆盖这些默认值,并说明 151643 是否也作为停止 token。
  3. **“输出先去掉开头的空格”实际上不起作用。** 后面的归一化“取第一行、去首尾空白”已经覆盖了这一步;06 的 16,000 个模拟输出中,有没有这一步结果都相同。这一步无害。本轮真正的改动是解码上下文。
  4. **有 1 篇锚文本重新编码后不是 128 token。** 第 340 篇(0 起计)解码后再编码只有 123 个 token(02)。n_x 取决于 arm A 用存下的文本重新编码,还是用原始截断的 id。这不影响哈希和 L3,建议在协议中写明用哪一种。
  5. **(上轮遗留,本轮未改)两处生成方法没有写到逐字节可复现的程度。** 第 2.6 节 S 的置换(derangement)和第 2.5 节的候选抽取都没有写死调用方式(例如 shuffle 还是 sample、源列表的顺序)。train_S.jsonl 和 candidates.json 生成之后,只凭协议文字无法逐字节复算它们的哈希。目前这两个哈希都是 null,不构成不一致。
  6. **reviews/2253be94…/ 目录不是我写的。** 其中的 code-reviewer.md、*_prompt.txt、review_input.diff 是在我运行之前或期间由 Executor 一方写入的,未被跟踪。
  
  ### git status --short(全部运行之后的原始输出;HEAD = 2253be94d77d41c5106d8074da578987d5b0a238)
  ```
  ?? metrix/e1-pilot/audit/r4_anchor.py
  ?? metrix/e1-pilot/audit/r4_compare_prev.py
  ?? metrix/e1-pilot/audit/r4_env.py
  ?? metrix/e1-pilot/audit/r4_kprime.py
  ?? metrix/e1-pilot/audit/r4_leak_supp.py
  ?? metrix/e1-pilot/audit/r4_manifests.py
  ?? metrix/e1-pilot/audit/r4_regen_facts.py
  ?? metrix/e1-pilot/audit/r4_scoring_em.py
  ?? metrix/e1-pilot/audit/run_logged.sh
  ?? metrix/e1-pilot/audit/stdout/
  ?? metrix/e1-pilot/reviews/2253be94d77d41c5106d8074da578987d5b0a238/
  ```
  `git diff --stat HEAD` 输出为空:已跟踪文件(包括 a1–a5 和 common.py)都没有改动。所有运行都用了 `-B`,audit/ 下没有生成 __pycache__。
  
  结论：PASS
