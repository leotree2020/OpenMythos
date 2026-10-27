# G1-IMPLEMENTATION-001 — static audit report (F3B-D1-A-CPU-003-E1A-G1-IMPLEMENTATION-001)

**G1 IMPLEMENTATION COMPLETE / STATIC AUDIT RECORDED / CPU TESTS NOT TESTED / G1 REAL NOT AUTHORIZED.**
No blocking contradiction in the frozen G1 V1 criteria was found (nothing is BLOCKED by the specification). Everything that was not executed is **NOT TESTED**: a completed implementation and a clean static audit are not an experimental PASS.

## Git
Branch `d1-r3-a-cpu-003-e1a-g1-impl-20261027` from base `48d241fa61b1e1824fca004e4db0719d5c8011b4`.
| step | commit |
|---|---|
| Step 2: criteria V1 + prereg + SHA-256 files, frozen alone, before any code | `8385cd16e8a44267c97b75b5e35bfb4209648b3b` |
| `g1_auth.py` | `c176732d2beccf92680de60d35ff6f760066d184` |
| `g1_judge.py`, `g1_run.py` | `473497081152e2fd6d81e531b4beb001ce0d660c` |
| CPU test code + fixtures + sentinel runner | `233d69214d686cdb731fd5292056eadeef1df670` |
| static audit tool + test import cleanup (code state audited here) | `a0c31957a2b7ddbe21559e1a9ef7e25b6392cb56` |
Criteria SHA-256 `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257`; preregistration text SHA-256 `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69`. No V2 was created; the frozen files were not touched after their commit.

## Files (sha256 / git blob SHA-1 of the audited state)
| file | lines | sha256 | git blob sha1 |
|---|---|---|---|
| `gate_g1/E1A_GATE_G1_PREREG.md` | 42 | `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69` | `0106d9cf910822547d317e0f0ceb43fa808d5d39` |
| `gate_g1/g1_auth.py` | 201 | `c27cff36a04b98d164ef4342cb801a4ed5d2dea1cb062c60466631a7e2844fb7` | `8c0206d1317de50b927da658579f57b28daf8a04` |
| `gate_g1/g1_criteria_v1.json` | 2087 | `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257` | `665da25929ec3c5e170c1853d18f8ae037116e23` |
| `gate_g1/g1_judge.py` | 843 | `b072db80f068bb9b4cbebe32fda8636756c691c148fb6d66e039131aaa8d2817` | `d96711357bc7fd48e0a887415d39240ed5b65034` |
| `gate_g1/g1_run.py` | 752 | `d77c50d7390c18beea322f40c85602ebe8d21eca4c8919992f512582925feba9` | `60e6e3e2c73ccfc216226829481d98b33647f13d` |
| `tests/g1_fixtures.py` | 170 | `45e7bc67a94ef1062eabbd19cbe4d5c138a44e048396f0d120a9669cbf33f69e` | `507e2f00586fc870a6ae721d26122a82cfd5fe84` |
| `tests/test_g1_auth_preflight.py` | 377 | `d2ccc837d8845fca7a2ee9495ced97b1abfa39f54ffe55641014ebf956e5c309` | `3df0e8d748546d51383efe5ee78c2fae3ee59548` |
| `tests/test_g1_boundaries.py` | 296 | `e4db67c1ad1f82bd3337d0a6807c3933efd41fbfbf7f053e3cf2438f781d0038` | `375b65cbf5b2ba3305b02e32089908cdceb8176e` |
| `tests/test_g1_judge_cases.py` | 727 | `88451491a3da59e7b2eecb2cbd9324879ffc412416128bd9ce23d6750697f16a` | `5804c3240219ccc21df0acdd9b3e1369ce2c43b2` |
| `tests/test_g1_mutations.py` | 260 | `af777b5f8d9d42d302ed9eab76547b9d7673b5887e91e8c00dc1f63bc17a9275` | `37d581ce310a34ad35580c61ba87e55b40537129` |
| `tests/test_g1_run_parts.py` | 578 | `ec1d18923e058f38e066031c60c9d7485465c4864df4458297bedeba8912b445` | `847d1561e30fce2ec72d1f46df7dbbee3a49b58e` |
| `tools/audit_g1_implementation.py` | 387 | `2e4b302e73b3c06d344fcd106185c90280d4e49d32ea8404dd2a46d668bf3c73` | `d679cac8f839b8e3af48a2e449f1aa0322f33b8c` |
| `tools/run_g1_cpu_tests.py` | 186 | `2691ae07e15435582faf6ce4cbfd59e349e872ab495c788261c0e56437340de7` | `9090da74bc571ce9844ba04ca39f0cf908f78512` |

## What was implemented
* `g1_auth.py`: schema `e1a-gate-auth-g1-1`, ten bindings (incl. G0 and G1 code / criteria / prereg hashes and the G0 REAL-001 closure marker hash), exact grants (runs 1, four tests, forks 4, signals 0, 30 s), `not_granted`, required expiry, single-use consumption marker path, frozen-file check (G1 and G0), read-only verification of the G0 REAL-001 reference run. No function writes an authorization file.
* `g1_judge.py`: all 17 checks for every test T1..T4 (run-level C01 / C02 / C16 / C17 judged once), rules C03-F1..F3 / U0..U4, C04, C05, C06, C07, C10 with their F / U rules, M-2 disk dependence, PASS / FAIL / BLOCKED / NOT_RUN and RUN-INCOMPLETE aggregation, evidence schema validation (88 fields), closure marker build / validate / classify. Reuses the strict-JSON helpers, type validators, disk-fidelity and closure engine of `g0_judge.py` read-only.
* `g1_run.py`: guard (`G1Guard`: one fork per test, four in total, none while a child is unreaped, waitpid only on the current child, gate write / close records, `b"R"` and `Observer.release()` trapped, signal / exec / spawn / wait / subprocess trapped), preflight (G0 history with the G0 V5 engine, G1 history with CL1-01..23, G0 REAL-001 reference), exclusive directories, single-use consumption before the first fork, sequential T1→T4 with the four stimuli, hold, S0 / S1 / S1b / S3 / S4 / S5 snapshots, pidfd exit observation, state-Z observation, bounded `waitpid(pid)` polls, `/proc` gone, cleanup only after the reap, in-run stop rule, manual disposition, evidence pipeline P0..P7, closure publication K0..K7 (`os.link`, never overwritten), main with argparse outside the safety net and every later SystemExit / exception → exit code 3.
* CPU tests (5 modules + fixtures, 222 tests, **written, never run**) and a sentinel runner `tools/run_g1_cpu_tests.py` (sentinels first, independent HEAD / frozen-file verification, key-file hashes, refuses to run when a G1 authorization file exists).

## Static audit (`tools/audit_g1_implementation.py`; source reading, ast, json, regex, hashes; imports / executes nothing)
Output `audit_output.txt`, trace table `G1_TRACEABILITY.md`, data `g1_static_audit.json`, `git diff --name-status` against the base `git_diff_name_status_vs_base.txt`.
* syntax + undefined names + unused imports over 11 files: **clean**; 88 schema fields, 19 schema types all have a validator; 17 checks, 26 rule ids present in the judge; marker keys / schema / exit-code table / snapshot names / disk-dependent checks / limits / scenario table / authorization constants equal the frozen criteria; closure facts (15) produced; CL1 rules read from the criteria.
* safety boundary: no `os.kill` / `killpg` / `pidfd_send_signal` / `fork` / exec / spawn / `system` / `popen` / subprocess / wait* call in any G1 module; exactly one `os.waitpid` call (in `run_test`, the child pid); `os.fork` is referenced only by the guard install; no `rename` / `replace` / `unlink`; closure by `os.link(..., follow_symlinks=False)`; the gate is created held and `release` is never called; `_confirmed_dead`, `finish_trial_cleanup`, `kill_registered` and the janitor / trial / scenario modules are not used; the guard trap list is complete; order inside `run_test` (stimulus < exit wait < S3 < waitpid < /proc gone < S4 < cleanup < S5) and consumption marker < guard install < first test are enforced by position checks.
* frozen files: G0 V1..V5 (10 files) and G1 (2 files, plus `.sha256` files) have their frozen bytes; E1-A preregistration `e6b7ca5c…ec39`; bench `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`; G0 REAL-001 evidence hashes unchanged; no G1 authorization file and no G1 evidence directory exist.
* `git diff --name-status` base → HEAD: 15 added files, all under `gate_g1/`, `tests/g1_fixtures.py`, `tests/test_g1_*`, `tools/*g1*`; no modified or deleted file; nothing in `gate_g0`, `bench`, `prereg`, `r3_cpu_probes`, `evidence`, Parcae or the model.
* traceability: 36 rows, 0 NOT FOUND (every check and every scenario, the guard, the authorization, the history preflight, the pipeline, the closure, the exit codes, the manual disposition and the mutation controls map to implementation lines and to tests).
* **FINDINGS: 0.**

## Manual desk review of the judge against the fixtures (no execution)
The fixture evidence (`tests/g1_fixtures.py`) was walked through the judge by hand for all 17 checks and the schema validators; defects found and fixed during the desk review: run duration of the fixture exceeded the 30 s limit; the RELEASED-record check of G1-C07 read the (untrusted) durable copy and could turn a damaged durable copy into a FAIL — it now reads the writer's own ledger; several test expectations corrected (`g1_` ids, run id regex edge case, T4 close time in the time-bound test, closure marker run ids).

## NOT TESTED (all of it)
* the 222 CPU tests (written only; including the negative controls and the in-process mutation tests);
* `g1_run.py` as a whole, `run()` / `run_test()` (process orchestration) — no unit test can start a process; they are exercised only by static reading;
* the guard `install()` / `uninstall()` against the real `os` module; `GR.snapshot` / `/proc` observation inside G1; the G0 closure engine applied to the committed G0 REAL-001 directory;
* the four scenarios against real children; no G1 experiment, no process-level test, no G0 rerun was executed.

## Unresolved issues for the reviewers
1. **Fixtures vs judge** were reconciled only by hand; the first CPU run may reveal mismatches (the tests, not the frozen criteria, are then to be fixed).
2. `run_test` cannot be unit-tested without processes; a process-level dry run needs its own authorization.
3. Reuse of G0 internals includes private helpers (`_obj`, `_nid`, `_completed`, …) of `g0_judge.py` and `closure_preflight` / `snapshot` of `g0_run.py`; both files are frozen by their authorization hash and unchanged, but a future G0 change would break G1.
4. T4 identity margin: S1 / S1b must be taken ≥ 0.5 s before the 2.0 s gate timer; a host stall makes T4 BLOCKED (never PASS) — by design (design Q3 / C04-U1).
5. CPU tests assert that no G1 authorization file exists: run them **before** the owner creates one.
6. G1 `--check` and the preflight read the G0 REAL-001 evidence directory from the committed tree; a fresh clone lacks the local-only `authorization_used.json` (not needed by the rules, not exercised).
7. Design questions Q1..Q6 were resolved as recommended in the design (no bench change for F-1, one invalid byte `r`, live child at deadline → BLOCKED + manual disposition, read-only G0 reuse, first non-PASS stops, keep the SPEC probe).

## Single next instruction
ChatGPT and Grok review this implementation, the frozen criteria and the static audit. Only after their acceptance may the owner **separately** authorize the G1 CPU tests (written, never run); the real G1 needs a further separate authorization.
