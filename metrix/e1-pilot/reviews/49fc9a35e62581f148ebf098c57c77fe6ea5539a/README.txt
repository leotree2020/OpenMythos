C2 fix commit 49fc9a35 (after the round-1 reviews of the C2 work commit 5219ff77), reviewed as the staged tree
b40224e68d1d42f9b4dc886fe9e159f9d99162b1 (tree.txt), parent 1900b1fe. Round 1: code-reviewer PASS (4 MAJOR, 18 MINOR),
data-auditor PASS (reference only; IC8-M1..M4). The commit is that tree.
  threat_model.txt, ruling_20261127.txt, notes.txt   parts the invocation texts were assembled from
  code-reviewer_prompt.txt, data-auditor_prompt.txt  the invocation texts (first sentence per metrix/CLAUDE.md 5.6)
  preflight_tools_check.txt                          tools lines compared before the calls
  input.diff, input_code.diff                        git diff --cached --stat and full diff against 1900b1fe; the code part
  *_round1_transcript.jsonl                          raw transcripts; *_round1.md final reports extracted unchanged
Executor's raw outputs: reports/impl_c/c2b_03_checks.txt, c2b_04_smoke.txt (superseded: c2b_01, c2b_02; c2b_01b);
push: reports/impl_c/c2b_push_fix_commit.txt. data-auditor: audit/ic8_*, audit/stdout/impl_c/ic8_*.
The findings and their handling: reports/DEFERRED_MINORS.md 1.33; reports/IMPL_C_REPORT.md C2.
