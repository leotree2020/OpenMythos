# G1-CPU-TEST-001 — report (F3B-D1-A-CPU-003-E1A-G1-CPU-TEST-001)

**G1 CPU TEST PASS.  G1 REAL NOT AUTHORIZED.**
A CPU unit-test PASS is not a real G1 PASS: the real G1 (`g1_run.py --execute`) was not run, no process was started by these tests, no authorization file exists.

## Purpose and acceptance criteria
Run the 289 written, never-run G1 CPU tests (frozen G1 V1 criteria, judge, authorization, preflight, pipeline / closure, guard, boundaries, mutation controls, runner acceptance) twice under the process-safety sentinels, on one fixed code state. Accepted only if, in each run, with no `--groups`: 289 expected unique test ids all executed and PASS; FAIL = ERROR = SKIP = XFAIL = XPASS = 0; load errors 0; sentinel violations 0; missing / duplicate / unknown ids 0; verdict PASS, exit code 0 — verified by reading the JSON, not by the exit code or an "OK" line; the two runs consistent.

## Code state and git (tested code SHA and evidence commit SHA are different things)
* branch `d1-r3-a-cpu-003-e1a-g1-impl-20261027`
* **tested code SHA: `d175a1ab89c521ec78de9fa39fb139a0e20b1788`** (local HEAD = remote HEAD = this SHA, working tree clean, before, between and after the runs; no commit and no code change between the two runs)
* evidence commit SHA: not knowable inside the commit it describes; it is recorded in `EVIDENCE_COMMIT_RECORD.md` (committed right after the evidence commit) and in the final message.
* G1 V1 criteria SHA-256 `1992d75ded16aeedc6eb2d3bb99fe799fb64d514eb08b5e86b2decb68b811257`, preregistration `3748723794b6742baa3a59e1cc8ebcb65471e3418d8c13328c8131e274e2cd69` (both re-hashed before the runs; unchanged); the runner's own check of the frozen G1 and G0 V1–V5 files: no problem; bench `b6f52a8c1f62cf94be2591c681dc42f10f5741a901fff968d66ed8b35425d3b0`; no change under bench / gate_g0 / prereg / r3_cpu_probes / Parcae / model since `48d241f`; no G1 authorization file anywhere; no residue process, no MANUAL_DISPOSITION file.

## Environment
Python 3.13.16 (`/usr/bin/python3`, stdlib only: no third-party dependency), Linux 6.18.44-fc-v180 x86_64 (Firecracker VM), 4 CPUs, uid 0, no GPU (`gpu_used` false). Command (both runs, working directory `/home/user/mini_mythos/OpenMythos_d1`):
`python3 -B research/mini_mythos/a_predicate_003/tools/run_g1_cpu_tests.py --expect-sha d175a1ab89c521ec78de9fa39fb139a0e20b1788 --json /tmp/g1_cpu_runN.json --txt /tmp/g1_cpu_runN.txt`
The runner installs its sentinels (os.fork*, kill*, exec*, spawn*, system, popen, wait*, waitpid, pidfd_open, setsid, setpgid, signal senders, subprocess.Popen / run / call / check_*) at import time, before any test module is imported (source lines 45–56, checked by reading); it verifies the real HEAD from `.git` and refused-to-run conditions (HEAD mismatch, changed frozen file, a G1 authorization file) were all clear.

## Results
| | run 1 | run 2 |
|---|---|---|
| start / end (UTC) | 2026-10-28T02:12:13Z / 02:12:16Z | 2026-10-28T02:12:37Z / 02:12:39Z |
| exit code | **0** | **0** |
| runner verdict / scope | PASS / FULL | PASS / FULL |
| expected / executed / unique / PASS | 289 / 289 / 289 / 289 | 289 / 289 / 289 / 289 |
| FAIL / ERROR / SKIP / XFAIL / XPASS | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 |
| load errors / sentinel violations | 0 / 0 | 0 / 0 |
| missing / duplicate / unexpected ids | 0 / 0 / 0 | 0 / 0 / 0 |
| stderr | empty | empty |

Groups (identical in both runs): tests | PASS | FAIL | ERROR | SKIP | load errors
| group | run | PASS | FAIL | ERROR | SKIP | load errors |
|---|---|---|---|---|---|---|
| g1_judge_cases | 102 | 102 | 0 | 0 | 0 | 0 |
| g2_auth_preflight_pipeline | 106 | 106 | 0 | 0 | 0 | 0 |
| g3_boundaries_mutations_acceptance | 81 | 81 | 0 | 0 | 0 | 0 |

Independent verification (`verify_run.py`, written for this report, reads the JSON and the test files with `ast`): all 16 conditions OK for both runs (id set = the 289 `ast`-discovered ids, every status PASS, HEAD = expected SHA, checkout identity ok with no problems, bench hash, no GPU, acceptance block FULL / PASS).

## Consistency of the two runs (`compare_runs.py`, `raw/comparison.json`)
Identical: the test id set and order, the per-test statuses, the group statistics, the environment (except the temporary directory name), the checkout identity with all key-file hashes (15 + 17 files), the sentinel record (empty), the acceptance block, the verdict, the HEAD. Only timings differ (0.7 / 0.4 / 1.6 s of test time per group in run 1, 0.6 / 0.3 / 1.4 s in run 2). `ALL_CONSISTENT: true`.

## Raw result files (SHA-256)
| file | sha256 |
|---|---|
| raw/g1_cpu_run1.json | `d8c0c5e147172ff19b40028f09e8e9cb5f07b3b701f0f9055d89f2ba2f9278e5` |
| raw/g1_cpu_run1.txt | `81270cb1977aa8665c0e39a530fffded2eb72cc2c067de9e35e8edda0d95cf25` |
| raw/g1_cpu_run2.json | `feca6e60e15e2d17d065e67f6a03a3e299cf5fb46e08cfb7bd3a16d1f85b501e` |
| raw/g1_cpu_run2.txt | `cf0026c9b445731f4aee2e823b7e0e0535a1b1688ea4f332f6994164d491b721` |
| raw/comparison.json | `365f4ccfa038429e12ba007d52ba55ec9303ddc89868024ebacb9dfc7015bbd2` |
The stdout / stderr / exit code / start / end / cwd / Python version of each run, the two verification scripts, `pre_execution_checks.txt` and `SHA256SUMS.txt` (all 22 files) are in the same directory. `/tmp/g1_cpu_run1.*` and `/tmp/g1_cpu_run2.*` are the originals.

## Problems found and unresolved matters
* No failure, error, skip, sentinel hit or load error occurred; nothing was rerun; no test was deleted, skipped or weakened; no code was changed. Both runs passed at the first attempt, so there was no triage to do (the FAIL / BLOCKED classification of Step 4 did not arise).
* What the PASS does **not** cover (unchanged from the implementation report): `g1_run.py` process orchestration (`run`, `run_test`) and the guard `install()` against the real `os` module were never executed (no test may start a process); `_in_run_view` was exercised only against a registry file written by the test; the four scenarios were not run against real children; the authorization / evidence / closure path was exercised only in temporary directories. The tests passed at the first run, after a purely manual fixture-vs-judge reconciliation: the in-process mutation tests (`test_g1_mutations.py`, 23 tests, and the 8 acceptance mutants) are the evidence that the checks are not vacuous.
* The real G1 still needs the owner's separate authorization (and the CPU tests must be run before that authorization file exists: they assert its absence).
* The runner left no file in the repository (it works in a temporary directory); `git status` was clean after both runs.

## Git state after the tests (before this evidence was added)
HEAD = remote HEAD = `d175a1ab89c521ec78de9fa39fb139a0e20b1788`, working tree clean, no new tracked or untracked file, no process residue, no G1 authorization file, no new evidence directory.

## Single next instruction
ChatGPT and Grok review this CPU test evidence. Only afterwards may the owner decide, **separately**, whether to authorize the real G1 (`g1_run.py --execute`, one run, one authorization, T1–T4); nothing else is started.
