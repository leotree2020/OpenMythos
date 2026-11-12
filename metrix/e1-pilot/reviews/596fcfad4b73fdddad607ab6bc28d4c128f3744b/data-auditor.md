# data-auditor raw output — commit 596fcfad4b73fdddad607ab6bc28d4c128f3744b (Round 3 task 9)
# Invoked by the Executor via Agent(subagent_type="data-auditor") in session_01J5mxaTvdtnGXVnVJiiAhgU, 2026-11-12 ~16:00Z.
# The auditor's scripts are in metrix/e1-pilot/audit/ (committed alongside this file).
# Below the line: the subagent's final report, verbatim (the harness's indentation removed).
---
## Data Auditor report: Metrix E1-PILOT Round 3 task 9, commit 596fcfad4b73fdddad607ab6bc28d4c128f3744b

Every item I recomputed matches the Executor's claims. Nothing is inconsistent and nothing in scope could not be recomputed. Verdict at the end is PASS.

**Environment.** Host `vm` (cloud container), CPU only. I used the venv's Python with transformers 5.22.2 and no torch. I loaded only the pinned tokenizer files (Qwen/Qwen3-1.7B@70d244cc); no model weights were loaded. No PROTOCOL_FROZEN file exists, so no TEST question was built: TEST templates were only hashed for L1 and L2, which use templates alone.

**Independence.** All scripts are my own, in /home/user/OpenMythos/metrix/e1-pilot/audit/: common.py, a1_facts.py, a2_regen_facts.py, a3_scoring.py, a4_cands_templates.py, a5_anchor.py. None of them imports, calls or copies Executor code. I read reports/round3/scoring_input.py only to compare its text with the protocol.

Abbreviations below: `PY` = /tmp/claude-0/-home-user-OpenMythos/9545fc84-1deb-5087-8903-0ad2adf5140c/scratchpad/venv/bin/python, `S` = /tmp/claude-0/-home-user-OpenMythos/9545fc84-1deb-5087-8903-0ad2adf5140c/scratchpad. All commands were run from metrix/e1-pilot/audit.

---

### 1. Facts hash, and the facts rebuilt from the protocol text alone

**Commands**
```
$PY a1_facts.py $S/r3/facts.json $S/r3/anchor.json ../SPLIT_MANIFEST.json
$PY a2_regen_facts.py $S/qwen_tok $S/r3/anchor.json $S/r3/facts.json
$PY a5_anchor.py $S/r3/cache/data/sample-100BT/train/shard_00000.parquet $S/qwen_tok $S/r3/anchor.json
```

**Raw output (relevant lines)**
```
file byte sha256      : 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
protocol value        : 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
canonical match: True
fields: [(('answer', 'entity', 'exposure', 'fact_id', 'relation', 'stratum'), 160)]
fact_id format/field mismatches: 0 []
fact_id order equals generation order rule: True
form-rule violations: []
--- a2 (my own implementation of section 2.2)
cell capital natural target (K_st,K_qa) = (3, 3) ...  cell capital random (5, 5)  currency natural (3, 3)  currency random (6, 6)
founder natural (3, 3)  founder random (5, 5)  river natural (3, 3)  river random (6, 6)
regenerated facts canonical sha256: 406c8801c5b69ed235cbe516658ad9ee3e3a8cfe8e4e348a0c1fd7952f2e6b97
match: True
equal to Executor data file: True
--- a5 (anchor texts rebuilt from the pinned parquet per DATA_MANIFEST.anchor_text)
parquet sha256: 6a3450ea745ee6b6830c09819c0f2c72682eba443022de595bcb50ceb3092c22
documents read 527 kept 512 canonical sha256 of texts list 8828bc4fcc5a3552778839f97909f072050431dd6f74dd08ef47602da11b2408
equal to anchor.json texts: True
```

**Match with Executor:** yes. The hash 406c8801… agrees with t0_facts_regen.txt and protocol §2.2. My rebuild from §2.2 text alone gives the same file byte for byte. The anchor-text hash 8828bc4f… also agrees.

---

### 2. Round-3 scoring input, built from the protocol text alone

**Construction used:**
- chat(q) is `apply_chat_template([user q], tokenize=False, add_generation_prompt=True, enable_thinking=False)`.
- The full text is `chat(q) + "The answer is" + " " + c`, tokenized in one call with `add_special_tokens=False`.
- The scored ids are the ids after the tokens of `chat(q) + "The answer is"`.
- These are compared with the ids of the `" " + answer` span inside the TRAIN statement. That span is everything between the tokens of the text before it and the final `"."`.
- DEV templates only.

**Command:** `$PY a3_scoring.py $S/qwen_tok $S/r3/facts.json ../SPLIT_MANIFEST.json`

**Raw output**
```
tokenizer.json sha256 aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4
tokenizer_config.json sha256 d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101
tokenizer class Qwen2Tokenizer vocab 151669
chat('Q?') = "<|im_start|>user\nQ?<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
chat('Q?') with enable_thinking=True = "<|im_start|>user\nQ?<|im_end|>\n<|im_start|>assistant\n"
learned facts x DEV questions compared: 240
TRAIN statements where ' '+answer is not a token-aligned span: 0
scoring inputs where chat(q)+'The answer is' is not a token prefix of the full text: 0
MISMATCHES scored ids vs TRAIN-statement answer ids: 0
mismatches scored ids vs encode(' '+answer): 0
example E1P-L-capital-nat-01 | statement "The capital of Krultrouth is Linnuth." | TRAIN ans ids [444, 6130, 940] ['ĠL', 'inn', 'uth']
  full ids [151644, 872, 198, 3838, 374, 279, 6722, 315, 16447, 360, 376, 2898, 30, 151645, 198, 151644, 77091, 198, 151667, 271, 151668, 271, 785, 4226, 374, 444, 6130, 940]
  scored ids [444, 6130, 940] ['ĠL', 'inn', 'uth']
scored count != K_st (all facts x DEV q x pool candidates): 0
  cell ('capital', 'natural') scored-token counts: [3]
  cell ('capital', 'random') scored-token counts: [5]
  cell ('currency', 'natural') scored-token counts: [3]
  cell ('currency', 'random') scored-token counts: [6]
  cell ('founder', 'natural') scored-token counts: [3]
  cell ('founder', 'random') scored-token counts: [5]
  cell ('river', 'natural') scored-token counts: [3]
  cell ('river', 'random') scored-token counts: [6]
cells with >1 scored-token count: 0
```

**Match with Executor:** yes.
- 240 pairs with 0 mismatches.
- The scored count is constant per cell and equals K_st. The per-cell counts {3,5,3,6,3,5,3,6} are identical to t7.
- The example's 28 input ids and its scored slice match t7 exactly.
- The tokenizer file hashes match t7.
- My K-constancy check is broader than the claim: it covers all 160 facts, every candidate in each pool, and both DEV questions.

---

### 3. Candidate feasibility under the four constraints

The four constraints are relation, stratum, exposure, and scored-token count, which is `len(encode(" " + c))`.

**Command:** `$PY a4_cands_templates.py $S/qwen_tok $S/r3/facts.json ../SPLIT_MANIFEST.json ../METRIX_E1_PROTOCOL.md`

**Raw output (candidate part)**
```
pools: 16
   ('capital', 'natural', 'learned', 3) size 15 ... ('capital', 'natural', 'unread', 3) size 5
   ('capital', 'random', 'learned', 5) size 15 ... ('capital', 'random', 'unread', 5) size 5
   ('currency', 'natural', *, 3) 15 / 5    ('currency', 'random', *, 6) 15 / 5
   ('founder', 'natural', *, 3) 15 / 5     ('founder', 'random', *, 5) 15 / 5
   ('river', 'natural', *, 3) 15 / 5       ('river', 'random', *, 6) 15 / 5
(rel,stratum,exposure) groups split across >1 token count: []
facts: 160 min pool size over facts: 5 max: 15
pools with < 4 answers: []
facts with < 3 distractors: []
```

**Match with Executor:** yes. t8 reports 16 pools, minimum size 5, and 0 pools under 4, with the same K for each pool.

---

### 4. Templates, L1–L6 and split counts

SPLIT_MANIFEST.json is unchanged in 596fcfa, but I recomputed these anyway.

**Commands:** the same a4 command as item 3, plus a1 from item 1.

**Raw output**
```
templates: 32 normalized/hash mismatches vs manifest: 0
template_set_sha256 recomputed: 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f manifest: 2b52411326c218e9c51d947b2f4e0d77b0cdd5d6237f9ce25b57a872c48ce28f match: True
protocol 2.4 table == manifest template texts: True ( 16 rows )
L1 cross-set duplicate normalized hashes: []
L2 max Jaccard word-4gram across sets: (0.2, ('capital.TRAIN.1', 'capital.DEV.1')) limit 0.25, within: True
Y_ANSWER sentences whose answer ids differ from encode(' '+answer): 0
--- a1
n facts: 160 Counter({'learned': 120, 'unread': 40}); every (relation, stratum) cell 15 learned + 5 unread
L5 learned & unread fact_id intersection: 0 ; distinct fact_ids: 160
L5 strings: 320 distinct: 320 duplicates: 0
DEV questions: 320 (protocol: 160 facts x 2 = 320) learned: 240 unread: 80
TRAIN statements (learned only): 120 (protocol 120)
L3a (anchor part) unread entity/answer hits: 0 []
L3b learned answer hits in anchor: 0 []
L3a (train_F/train_Y part) unread hits: 0
learned answers with count != 1 in train_F: []
learned answers with count != 1 in train_Y: []
L4 (DEV) verbatim DEV questions in F/Y/S-superset: 0 ; S-superset lines: 1680
```

**Match with Executor:** yes.
- **Templates, L1, L2:** the hashes, template_set_sha256, the L1 result and the L2 maximum of 0.2 match the manifest's `authoring_result`.
- **Split counts and fact_ids:** fact_ids are mutually exclusive, and the counts match §2.1 and §2.3.
- **L3a, L3b, L4, L5** were run on corpora I built myself from the protocol templates. For train_S I used every possible within-cell answer swap, which covers any derangement.
- **Data files:** the split and data files (train_*.jsonl, dev_qa.jsonl, candidates.json) have not been generated yet, and all their hashes in the manifests are null. So no file hashes could be compared, and the Executor makes no claim about them this round.
- **L6:** it needs general_dev, which has not been generated, and the parcae tokenizer, which my rules do not allow me to load. The round-3 change does not touch it and the Executor claims nothing about it. I list it as not in scope, not as a failed recomputation.

---

### Observations (not blocking, for Review Gate)

1. **Symbol K' in §5 s_ST.** The TRAIN closed-book check in §5 still uses the symbol K' without defining it. It equals K_st by construction (0 misaligned TRAIN spans above), but the text could say so.
2. **Free-generation EM context.** EM (§5) generates from bare chat(q), while scoring now adds the prefix "The answer is". The EM normalization removes only a leading "the " and trailing punctuation. Answers such as "The capital of X is Y." would therefore count as wrong. This is a design point, not a data mismatch.
3. **Untracked reviews/ directory.** `metrix/e1-pilot/reviews/` shows as untracked. It holds `596fcfa.../code-reviewer.md` (16:01 UTC) and was created by the Executor, not by me. I wrote only under `metrix/e1-pilot/audit/`. `audit/__pycache__/` is git-ignored.

### git status --short (raw, after all runs; HEAD = 596fcfad4b73fdddad607ab6bc28d4c128f3744b)
```
?? metrix/e1-pilot/audit/
?? metrix/e1-pilot/reviews/
```

结论：PASS
