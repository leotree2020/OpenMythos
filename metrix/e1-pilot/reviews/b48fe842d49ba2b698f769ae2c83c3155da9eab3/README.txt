C1 fix commit b48fe842 (after the round-1 reviews of ae60e0f7), reviewed as the staged tree
ae5fcb2f7e2ea844c6ee04e7ecb8e3157efde08c (tree.txt), parent ae60e0f7. Round 1: code-reviewer PASS, data-auditor PASS
(reference only). The commit is that tree. Both reviews stopped on HTTP 429 (usage limit) and the session's worker
restarted; both were resumed with the fixed first sentence (interruption.txt, resume_message_*.txt).
  notes.txt, head.txt         parts the invocation texts were assembled from (head.txt holds the threat model quote)
  code-reviewer_prompt.txt, data-auditor_prompt.txt   the invocation texts
  preflight_tools_check.txt   tools lines compared before the calls
  input.diff                  git diff --cached --stat and full diff against ae60e0f7
  *_round1_transcript.jsonl   raw transcripts; *_round1.md final reports extracted unchanged (extract_log_round1.txt)
Executor's raw outputs: reports/impl_c/c1b_04_checks_fix.txt (c1b_03 superseded); data-auditor: audit/ic6_*.
