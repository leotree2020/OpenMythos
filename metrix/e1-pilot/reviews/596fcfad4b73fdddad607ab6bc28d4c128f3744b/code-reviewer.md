# code-reviewer raw output — commit 596fcfad4b73fdddad607ab6bc28d4c128f3744b (Round 3 task 9)
# Invoked by the Executor via Agent(subagent_type="code-reviewer") in session_01J5mxaTvdtnGXVnVJiiAhgU, 2026-11-12 ~16:00Z.
# Below the line: the subagent's final report, verbatim (the harness's indentation removed).
---
Code review of commit 596fcfa (parent ca60f74), Round 3, task 9. I worked from the files on disk only, because I cannot run git or Python. Run outputs come from the committed raw outputs t0, t3, t4, t7 and t8 under /home/user/OpenMythos/metrix/e1-pilot/reports/round3/.

MAJOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:201 (with lines 35 and 187) | Section 5 now uses two different inputs. Candidate scoring adds the fixed prefix "The answer is" to the assistant turn, but the secondary exact-match metric still decodes greedily from bare chat(q). Its normalization only strips a leading "the " and trailing punctuation. An answer like "The capital of X is Y." would never equal the bare answer, so EM is likely near 0 in every arm and no longer measures the same thing as s_QA. I am not sure this is a defect: task 6 asked only about candidate scoring, and EM is report-only, not a gate. | `**Free-generation exact match(次指标)**:对同一 \`chat(q)\` 做贪心解码` vs `s_QA(f, q, c) = Σ ... log p_θ(c'_t \| chat(q) + "The answer is", c'_<t)` | Ask Review Gate whether EM should decode from `chat(q) + "The answer is"` (and strip a leading space), or record explicitly that EM keeps the bare prompt.

MAJOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:642 and 645-646 | Section 14 has inconsistent commit and time fields. The new "v1-r2(Round 3 补记)" row cites `6675af63` with a time to the second. The original v1-r2 rows still say "本节所在提交" (the commit containing this section), which now also matches this Round 3 commit, so they are ambiguous. The v1-r3 rows give a date only ("2026-11-12"), although the table header says times are UTC, and they point to an external report for the hash. The backfilled row is also placed between existing v1-r2 rows instead of at the end. I am not sure whether the Gate accepts "hash 见 ROUND3_REPORT.md" (hash in the Round 3 report) as the commit reference. | `\| v1-r2 \| 2026-11-12 \| 本节所在提交 \|` ... `\| v1-r3 \| 2026-11-12 \| Round 3 提交(hash 见 \`reports/ROUND3_REPORT.md\`) \|` | Replace "本节所在提交" in the v1-r2 rows with the real round-2 hash (6675af63). Give the v1-r3 rows a UTC time. Keep the rows in time order.

MINOR | metrix/e1-pilot/reports/round3/outside_metrix_check.py:64,69 | The heading test counts every appended line that starts with "#" and requires exactly one. A legitimate section 6 with a "### " subsection would fail (a false fail, which is the safe direction). A non-heading line starting with "#", such as a code-block comment, would also count. Protocol section 0 says "追加部分只能是以 ## 6. Metrix 开头的第 6 节" (the appended part may only be section 6, starting with "## 6. Metrix"), which does not forbid subsections. | `heads = [ln for ln in added.split(b"\n") if ln.startswith(b"#")]` / `if len(heads) != 1 or not heads[0].startswith(b"## 6. "):` | Match only level-1 and level-2 headings (`re.match(rb"#{1,2} ", ln)`), or state in the protocol that section 6 may not contain subsections.

MINOR | metrix/e1-pilot/reports/round3/outside_metrix_check.py:75 | `git check-ignore --no-index` reads the working-tree .gitignore, not the .gitignore at `--rev`. With `--rev <other>` the printed ignore rule may not belong to that revision. It is informational only and does not affect the result. | `ign = git("check-ignore", "-v", "--no-index", path, check=False)` | Document that the ignore rule comes from the working tree, or read `.gitignore` via `git show rev:.gitignore`.

MINOR | metrix/e1-pilot/reports/round3/verify_scoring.py:94 | The cross-check hard-codes `enable_thinking=False` instead of using `SI.ENABLE_THINKING`, so the constant is duplicated. The renderer check (renderer_diff=0 in t7) is still valid. | `tokenize=False, continue_final_message=True, enable_thinking=False)` | Use `SI.ENABLE_THINKING`.

MINOR | metrix/e1-pilot/reports/round3/verify_scoring.py:32 | A runtime precondition is checked with `assert`, which is removed under `python -O`. | `assert statement[lo] == " "` | Raise explicitly, or count it as unaligned.

MINOR | metrix/e1-pilot/METRIX_E1_PROTOCOL.md:81, metrix/e1-pilot/DATA_MANIFEST.json:169 | The stated purpose of the answer-length rule ("in both contexts") still describes the old bare-answer QA context. Since Round 3, scoring only needs equal K_st within a cell. The rule is correctly kept, because changing it would change the fact hash, but the purpose text is now stale. | `作用:同一 cell 的答案在两种语境下 token 数都相同,候选打分比较的是等长序列` (purpose: within a cell, answers have the same token count in both contexts, so candidate scoring compares equal-length sequences) | Add a note that since Round 3 only K_st matters for scoring and K_qa equality is kept for reproducibility.

MINOR | metrix/e1-pilot/reports/round3/t3_outside_metrix.txt:8 | The appended charter heading is dated 2026-11-13, but every round-3 run timestamp is 2026-11-12. The charter is not changed in this commit; I flag it because the check output shows it verbatim and the date cannot be right. | `headings in appended part: ['## 6. Metrix 子项目(2026-11-13 负责人决定)']` | Report to Review Gate. Changing the charter needs a separate Owner decision.

What I checked and found consistent:
- **Scoring input:** scoring_input.py uses the Qwen3 chat template with `enable_thinking=False` as a constant, a single user turn, no system prompt, the "The answer is" prefix, `" " + c` as the scored span, and nothing after the candidate. It does not apply the charter's no-BOS/EOS rule.
- **Tokenizer facts and the rendered example:** t7 shows `bos_token None`, and `add_special_tokens` has no effect on encode. The rendered example contains the empty `<think>\n\n</think>\n\n` block.
- **Answer token ids:** the scored ids equal the answer-span ids in the TRAIN statements. The check compares 240 pairs, with 0 mismatches and 0 unaligned. Scored-token counts are constant within each cell, and they match apply_chat_template with continue_final_message.
- **Candidate feasibility:** the minimum pool is 5 and no cell has fewer than 4. Every fact's scored-token count equals K_st.
- **TEST isolation:** both scripts filter templates to TRAIN/DEV or DEV only, and no code path generates or reads TEST data.
- **Fact hash:** it is unchanged (406c8801…).
- **Dead code:** there are no unused imports or unreachable branches in the four new scripts.
- **SUBMISSION_NOTE:** the section 5 command path is valid when run from metrix/e1-pilot.
- **Out of scope:** arms, freezing rules, seeds and aggregation (mean) are untouched by this diff.

结论:PASS
