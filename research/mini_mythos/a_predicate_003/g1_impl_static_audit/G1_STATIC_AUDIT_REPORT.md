# G1-IMPLEMENTATION-001 — static audit report after the independent review fix (REVIEW-FIX-001)

**G1 IMPLEMENTATION COMPLETE (review fix applied) / STATIC AUDIT RECORDED / CPU TESTS NOT TESTED / G1 REAL NOT AUTHORIZED.**
Base reviewed by ChatGPT: `453fe4eba09a61564c71a1fb3f5d0041ba789e9f`. The frozen G1 V1 criteria and the preregistration are unchanged (SHA-256 `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257` / `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69`); no V2 was created; no real contradiction of the frozen requirements was found. G0, Bench, R3, Parcae, `g1_auth.py`, the design file: unchanged. **No test was run; no G1 authorization file exists.** The report of the earlier state is kept in `review_base_453fe4e/`.

## The review findings and their fixes (implementation layer only)
### 1. Exception path of `run()` looked at a stale node
*Counterexample (minimal):* T1 finishes (node `n00001` DEAD, `S.rec` = its record); in T2 `obs.spawn_direct` forks the child and then raises (or is interrupted) before it returns; `S.rec` still names `n00001`, `rec.handle.exited()` is true, so **no** manual disposition was written although the T2 child (node `n00002`, or only a pid known to the guard) is alive.
*Fix:* `run_test` sets `S.rec = None` first; the handler no longer uses `S.rec`; new `alive_nodes(nodes, live_pid)` checks **every** node of the run — registered ones through the pidfd (identity verified by the REGISTERED record), forked-but-unregistered / registration-failed ones through `/proc` (identity not verified), an unreadable `/proc` entry as alive — and, through `guard.live_pid`, an unreaped child no node record accounts for (spawn did not return); nodes confirmed DEAD, exited-unreaped (Z/X) and vanished processes are nothing alive. `report_residue` writes `MANUAL_DISPOSITION_REQUIRED.json` (one identity, or `{alive_nodes: [...], count: n}`), sends no signal. `run_test` also records `stopped_after` when it ends in an exception.
### 2. CPU runner could report PASS for a partial run
*Counterexamples:* a `--groups` run in which everything selected passed returned verdict PASS / exit 0; a SKIP row or a test missing from every group did not prevent PASS; `expectedFailure` / `unexpectedSuccess` were not recorded at all.
*Fix:* acceptance logic in the side-effect-free `tools/g1_test_acceptance.py` (the runner installs the process sentinels at import, so it is never imported by tests): PASS only for a FULL selection, expected ids discovered by `ast` from **every** `tests/test_g1_*.py` (whether or not a group names it), exactly `EXPECTED_TOTAL_TESTS = 289` unique ids, each executed exactly once and PASS, 0 SKIP / FAIL / ERROR / load error / sentinel hit. FAIL > INCOMPLETE > PASS; exit 0 / 1 / 3; a diagnostic `--groups` run is at best INCOMPLETE ("DIAGNOSTIC ONLY"). The runner records skips, expected failures and unexpected successes; `all_ok` is gone.
### 3. Per-test stop rule versus the frozen definition
Frozen `enforcement.stop_rule`: *stop after the first test that is not clearly as expected* (listed: exception, exit status differing, child alive at a deadline, cleanup not ok, a guard violation, any message from the child); the task text: *the first non-PASS test stops the run*.
*Inconsistency found (minimal counterexample):* T2 with the expected exit status 111, no message, cleanup ok, no violation, but a REGISTERED pid that differs from the pid held at S1b (C04 FAIL-class): the in-run rule said "clearly as expected", T3 and T4 were forked after an evidenced FAIL. Same for a gate write end left in the child (C06), a wrong gate byte (C07), a missing zombie observation (C08) or a wrong waitpid (C09).
*Fix (no criteria change):* `g1_judge.judge_test_in_run` applies the judge's own check functions C04–C15 to the evidence so far (guard summary, ledger, registry parsed now); `run_test` stops on any non-PASS (`in_run_assessment(..., judged)`), in addition to the old reasons. The stop rule is therefore at least as strict as the judge for everything that can be decided before the end of the run; C03 / C01 / C02 / C16 / C17 and the last-test parts of C12–C14 need the end of the run and are judged at the end. A false in-run stop can only lead to BLOCKED / RUN-INCOMPLETE (never to PASS).

## New / changed negative controls (written, NOT run; 289 unique tests: test_g1_auth_preflight.py 38, test_g1_boundaries.py 28, test_g1_judge_cases.py 102, test_g1_mutations.py 23, test_g1_run_parts.py 68, test_g1_runner_acceptance.py 30)
* `test_g1_run_parts.py`: `TestAliveNodesOnTheExceptionPath` (17: dead-previous-node, spawn-not-returned via `guard.live_pid`, unregistered, registered, exited, Z/X, unreadable, pidfd error, duplicate pid, several alive, nothing alive, `report_residue` files, AST: no `S.rec` in the handler), `TestInRunJudgementWiring` (3: judgement stops the run, minimal counterexample old rule vs new rule, view builder with a registry file).
* `test_g1_judge_cases.py`: `TestInRunJudgement` (9: clean partial run PASS, end-of-run parts irrelevant, FAIL for 11 evidenced violations, BLOCKED for 7 unconfirmed conditions, unfaithful durable copy, agreement with the final judge).
* `test_g1_runner_acceptance.py` (30): skip, unselected group, partial selection, too few tests, other ids, duplicates, wrong expected total, xfail / xpass / unknown status, FAIL / ERROR / load error / sentinel precedence, ast discovery, groups cover every test file, the runner source can return PASS only through `assess`, 8 acceptance mutants.
* `test_g1_mutations.py`: 8 new tests (7 mutants + anchors) of the in-run judgement and of `alive_nodes` / `report_residue` (ignore judgement, drop identity check, always-PASS, no orphan, latest node only, guess unreadable away, no manual file).

## Files (sha256 / git blob SHA-1 of the audited state `a5d9168972156c9017a9b1b3e64463e302b3b0cf`)
| file | lines | sha256 | git blob sha1 |
|---|---|---|---|
| `gate_g1/E1A_GATE_G1_PREREG.md` | 42 | `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69` | `0106d9cf910822547d317e0f0ceb43fa808d5d39` |
| `gate_g1/g1_auth.py` | 201 | `c27cff36a04b98d164ef4342cb801a4ed5d2dea1cb062c60466631a7e2844fb7` | `8c0206d1317de50b927da658579f57b28daf8a04` |
| `gate_g1/g1_criteria_v1.json` | 2087 | `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257` | `665da25929ec3c5e170c1853d18f8ae037116e23` |
| `gate_g1/g1_judge.py` | 864 | `ab7af32ea961dd6a1af19be92c607e8390d84a0788b04ad456afdf4572e5e3e8` | `cff910d12323ecf12385a4521c79be9f9e4a16dc` |
| `gate_g1/g1_run.py` | 800 | `7258e6f86a1f084f2e71da2f82b67c10d002fdc76658ab6546fc27b83d01630c` | `523ab853f7161a98977576d8e0cdee970568cc03` |
| `tests/g1_fixtures.py` | 170 | `45e7bc67a94ef1062eabbd19cbe4d5c138a44e048396f0d120a9669cbf33f69e` | `507e2f00586fc870a6ae721d26122a82cfd5fe84` |
| `tests/test_g1_auth_preflight.py` | 377 | `d2ccc837d8845fca7a2ee9495ced97b1abfa39f54ffe55641014ebf956e5c309` | `3df0e8d748546d51383efe5ee78c2fae3ee59548` |
| `tests/test_g1_boundaries.py` | 296 | `e4db67c1ad1f82bd3337d0a6807c3933efd41fbfbf7f053e3cf2438f781d0038` | `375b65cbf5b2ba3305b02e32089908cdceb8176e` |
| `tests/test_g1_judge_cases.py` | 826 | `8f7cd1327b317dce90fe14e2efc5d2297957ae7c5d49d7ea894f8a3992a4daca` | `c57bbf0bd3f389806c0db0680e528cf1efe4a9f0` |
| `tests/test_g1_mutations.py` | 336 | `beb486c2213adf009004349926a81c758b8963c800bacb169461d40de02e390e` | `f230a9f1c3687fa6ba5abb86332f7457d4eb6986` |
| `tests/test_g1_run_parts.py` | 759 | `d9ab4dc3f64f43f1b7b410a44d96b14ce29d81bbe83f0582bff858a8b3d2f42c` | `661e737562a0840805a45a2fc8083ca1abdac3f3` |
| `tests/test_g1_runner_acceptance.py` | 252 | `92fe23b773618ceaa09094d0d62f1f166aaaefc932f2e6a5463df507ec9c0f7e` | `ab5470bf04f67bf01e2d9346f3aac5e20870f6f9` |
| `tools/audit_g1_implementation.py` | 441 | `6d2910c1bb35be6e18981a2f3084719e91b3636a86992de17fb22e54c0be1a0d` | `445f18adebffb17ca133e6349f284b6971825faf` |
| `tools/g1_test_acceptance.py` | 76 | `3f9381a71897e852930586b14648f25891259565a32ca23c96dcb991db789978` | `bb097d57e079c8b368d0eb0de6c2c686c538dc8a` |
| `tools/run_g1_cpu_tests.py` | 206 | `f3956aa7fb36fa9edc4110c3d7310ec4bb1d40f198b80f963bde9f00a9e7520b` | `8645ffa3d215b3ae0aee95e5571b12ed42ea8a4a` |

## Static audit (`tools/audit_g1_implementation.py`; source reading, ast, json, regex, hashes; imports / executes nothing)
`audit_output.txt`, `G1_TRACEABILITY.md` (38 rows, 0 NOT FOUND), `g1_static_audit.json`, `git_diff_name_status_vs_base.txt` (base `48d241f` → HEAD, 24 entries: only G1 files) and `git_diff_name_status_vs_review_base_453fe4e.txt` (reviewed commit → fix commit: `g1_run.py`, `g1_judge.py`, tests, tools only; not `g1_auth.py`, the criteria, the preregistration or the design).
* syntax / undefined names / unused imports over 13 files clean; 88 schema fields, 19 types validated; 17 checks and 26 rule ids in the judge; constants equal the frozen criteria; closure facts produced.
* safety boundary unchanged and re-verified: no signal / fork / exec / spawn / wait / subprocess / rename / unlink call in a G1 module; one `os.waitpid` (child pid); gate created held, `release` never called; order inside `run_test` enforced; consumption marker < guard install < first test.
* new checks: the exception handler of `run()` has no `S.rec`, uses `report_residue`, `guard.live_pid` and all nodes; `run_test` clears `S.rec` before `spawn_direct`, calls the in-run judgement and marks `stopped_after`; `EXPECTED_TOTAL_TESTS` = the 289 tests found by `ast`; no duplicate test ids; runner `GROUPS` = the six test files; the runner contains no PASS path outside `assess`.
* frozen G0 (10) and G1 (2) files, E1-A preregistration, Bench `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`, G0 REAL-001 evidence: unchanged; no G1 authorization file / evidence directory.
* **FINDINGS: 0.**

## NOT TESTED
All 289 CPU tests (written only, including every new negative control and mutant); `g1_run.py` process orchestration (`run`, `run_test`) and the guard `install()` against the real `os` module; the runner itself; `_in_run_view` against a real registry written by a real observer; the four scenarios against real children. No G1, G0, process-level run or test was executed.

## Unresolved issues for the reviewers
1. Fixtures vs judge (and the new in-run judgement) were reconciled by hand only; the first CPU run may show test defects.
2. `run_test` / `run` remain without unit tests that start no process.
3. The in-run judgement reads the registry file during the run; a spurious `/proc` enumeration problem could stop a run early (safe direction: BLOCKED / RUN-INCOMPLETE).
4. `EXPECTED_TOTAL_TESTS` must be raised together with any new test (the audit checks equality).
5. Reuse of private G0 helpers (unchanged since the previous report); T4 identity margin; CPU tests must run before a G1 authorization file exists.

## Single next instruction
ChatGPT and Grok re-review this fix (code, tests, audit, report). Only after acceptance may the owner separately authorize the G1 CPU tests (the full run must show PASS under the acceptance rule above); the real G1 needs a further separate authorization.
