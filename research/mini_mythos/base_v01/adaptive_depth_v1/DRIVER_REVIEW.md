# Internal static review of development evidence runner

Verdict: APPROVE for the scoped local CPU development stage. The final source/test manifest condition has been satisfied by the static check below. This is an internal agent review, not a Claude/Grok/human independent review and not runtime evidence.

Reviewed file: run_development.py, SHA256 `867ef8819f9fd2cfeb807471594f0048cb0594ab67897837cf6cf8db70aa29d7`. The final follow-up read specifically verified the new pre-execution claim and failure-priority aggregation against the previous reviewed version.

Purpose: look for false PASS, lost failure evidence, missing test coverage and violations of the frozen acceptance stop rule. Environment: static text review only. Input: the runner at the hash above and PROTOCOL.md. Expected: explicit failure/blocked recording, complete test discovery, preserved upstream/source identities, no quality claim from development tests. Actual: the main issues from the initial review have been corrected. Status: PASS (static review only); runtime validation remains NOT TESTED.

## Corrections verified

- A missing upstream path is now resolved inside the protected execution block, allowing BLOCKED evidence to be written.
- Expected failures and unexpected successes are explicitly recorded as FAIL and stop subsequent tests; neither can produce PASS.
- Discovered test IDs must exactly match the frozen manifest; duplicates are rejected and a nonempty required native group must be present.
- KeyboardInterrupt/SystemExit during protected execution are recorded as BLOCKED, with preservation checks attempted before final evidence is written.
- Actual Torch runtime is checked before test import, after import and after the test suite.
- Skipped tests are BLOCKED; overall PASS additionally requires all planned tests to run and all recorded test outcomes to be PASS.
- Any observed test failure/error/expectedFailure/unexpectedSuccess takes priority over skipped outcomes, including mixed subtest outcomes.
- CLAIM.json is written with NOT TESTED status before protected execution starts; a claim alone cannot be read as a completed result.
- Source hashes, upstream tracked bytes/Git state and dependency inventory are compared before and after execution. Existing output directories are never overwritten.

## Limits and final checks

Final manifest follow-up: SOURCE_MANIFEST.json SHA256 `a4d9d11a19eb02ad8b5ca0e67d25647e3d72a4325dfeba00408bcd02ce766d31` was read and compared to a static AST parse of test_adaptive_depth.py. All 15 test IDs match exactly, including all 5 NativeTinyTests methods in required_native_test_ids. The three executable source sizes and hashes match the manifest. No test module was imported and no tests were run for this check. The runner SHA remains the reviewed value above. Status: PASS (static manifest consistency).

The runner only validates the shape of the supplied Git commit ID; remote commit-to-local-byte binding is an external publication check and must be separately evidenced.

Use an evidence directory outside the read-only upstream and the executable source directory. The CLI does not itself prevent an operator from choosing an upstream subdirectory as output. A hard process termination, unavailable disk, or failure opening/writing the output files cannot guarantee a complete JSON checkpoint; absence of a result file is never PASS.

The previously noted skipped-subtest/failure priority issue is resolved in the reviewed hash. No remaining blocking issue was identified for the stated development stage and known external evidence directory. This judgment does not extend to execution on real 140M weights or quality evaluation.

No test, model import, numerical calculation, dependency installation, real-weight read, upstream modification or PR operation was performed by this review.
