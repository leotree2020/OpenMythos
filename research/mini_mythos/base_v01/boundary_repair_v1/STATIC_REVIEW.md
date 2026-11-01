# Static review before real-data construction

Purpose: check the isolated parser, builder and independently implemented auditor against the data-only protocol before freezing and examining corrected model inputs.

Environment: local read-only source review by root plus a separate internal agent. This is not human, Claude Code, Grok or independent third-party review. No real corpus build or model computation was performed by the reviewer.

Input identities reviewed:
- boundary_parser.py: e2df747fb88e64ad12fe6e9684560c542c77013ff5640a3b931cbea02a38420c
- build_inputs.py: 34d15184c507a253b506a039576266705ac4666d68cb23ab551c7093929c6c7a
- audit_boundary_inputs.py: 7633a52c86813be5d26fae6759209cfa6473e1c51bc4401fa14c2a5ece9b2f2e

Expected: exact reviewed corpus partition, preservation of all original rows, source identity independent of body hash, unchanged tokenizer behavior, fixed first32 selection, exact window/shift/scored-position hashes, no model imports, two different builder processes with identical input and partition bytes, and independent recomputation from the original Parquet rows.

Actual: reviewer APPROVE. Partition and manifest schemas agree. Each recorded runtime.pid equals its completion.process_id; actual operator child IDs will also be compared. Distinct builder PIDs are required, and the cross-process environment comparison excludes only pid. All other runtime fields are compared exactly. The independent auditor does not import parser or builder. It separately reconstructs the complete source partition, retokenizes every source body and verifies selected windows, source identities, all hashes, journal and report custody.

Clarifications accepted before freeze: internal row reconstruction precedes tokenization; R5 outputs remain provisional until R6 independent audit passes. The external operator must verify actual frozen Git HEAD, clean worktree and exact ledger SHA before each build and audit. Ledger is corpus-specific semantic review evidence; it does not prove statistical independence or pretraining cleanliness.

Development corrections retained: an initial inventory script had a syntax error before imports and data reads; an initial test operator referenced an undefined orchestration variable before tests. These were corrected before the formal data stage, with original error records retained. An intermediate PID schema mismatch was found and corrected during static review; no formal build ran against it. These are not model findings. Final synthetic suite: 9 parser + 6 builder + 6 independent-auditor tests PASS on the target CPU data environment; exact logs and hashes are in DEVELOPMENT_TESTS_FINAL.json.

Status: PASS for static review and final synthetic tests only. Real-data construction, repeat equality, independent audit and post-run preservation remain NOT TESTED at freeze.

Final operator review: execute_data_stage.py SHA256 658ae061c8ec1ddf5b00e3c9667780e9b8a1b37eee3fad353082eb674bdd7e8e APPROVE after two pre-execution corrections. Interrupted child waits now attempt terminate/reap then kill/reap, record cleanup outcome and stop; unavailable Git access maps to BLOCKED, while successful reads with wrong identities remain FAIL. Interruption cleanup was statically reviewed, not dynamically tested. Any unreaped child must be resolved or explicitly recorded before claiming stopped execution. SOURCE_MANIFEST.json must include the operator and all frozen source/ledger/review files without self-reference.
