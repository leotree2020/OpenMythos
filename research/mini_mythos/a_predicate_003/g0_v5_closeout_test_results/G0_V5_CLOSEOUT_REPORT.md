# G0 V5 CPU tests — final closeout (F3B-D1-A-CPU-003-E1A-G0-V5-PURE-TEST-001 closeout)

Base HEAD `40f3f5ba7e84596e329e444465a25d3b3ddd79cb` (198/198 ×2 results stay valid as the earlier CPU-stage result).
Fix commit and tested HEAD: `a4a85095fa1f48234914de09bdee2e7bf35abdad`.

**CPU TESTS PASS (216/216, two runs, 0 sentinel violations) — REAL G0 NOT AUTHORIZED.**

## The three boundaries

| # | Finding | Fix | Evidence |
|---|---|---|---|
| 1 | `g0_run.main()` had `except SystemExit: raise`. An unexpected `sys.exit(1)` after argument parsing left the process with exit code 1, which is the FAIL code (a stray 0 would read as PASS). | `main()` now calls `_parser().parse_args()` outside the safety net, so argparse keeps exit 0 (`--help`) and 2 (usage error). Everything after parsing runs in `_main(args)`; any SystemExit (any code) or exception maps to exit 3 with a `G0-STARTUP-ERROR` marker. Normal returns (0/1/2/3 from the pipeline) are untouched. | `tests/test_g0_v5_boundaries.py::TestSystemExitIsNeverAFailOrAPass` (9 tests: 9 steps × 10 exit codes, the named `SystemExit(1)` control, stray 0, check/template modes, argparse 2 and 0, AST: parse outside the try, no handler re-raises, normal codes unchanged). Against the base `g0_run.py` 5 of these error out, so the controls bite. |
| 2 | The environment capture used `platform.platform()`, which can spawn `uname`, and ran after other start-up work. | New `tools/g0_test_env.py` reads facts from `os.uname()` / `os.cpu_count()` / `sys` only (no `platform`, no subprocess). The runner installs the sentinels immediately after its imports, before anything else runs. | `TestRunnerStartsNoProcessEvenBeforeTheSentinels` (AST: no `platform` import/call, no subprocess import in the helper, sentinel loop before any environment/identity call; `environment_info()` runs with `subprocess.*` patched to raise). Both full runs: 0 sentinel hits. |
| 3 | The runner trusted `G0_TEST_GIT_SHA`. | `verify_checkout()` reads the real HEAD from `.git` (HEAD, loose refs, packed-refs; no Git binary), compares it with the expected SHA (`--expect-sha` or the env var), re-checks the frozen files and `bench_code_sha256`, and hashes 15 key files (sha256 + git blob SHA-1). Any mismatch, missing SHA or unresolvable HEAD → `REFUSED`, exit 3, JSON written. The runner's own unexpected errors exit 3 too. | `TestCheckoutIdentity` (loose/detached/packed HEAD, unresolvable HEAD, the real checkout, wrong/None/uppercase/short/off-by-one SHA, changed frozen file, changed bench, key-file hashes, blob SHA-1 against a known `git hash-object` value). Negative controls run for real: wrong SHA → exit 3 REFUSED; no SHA → exit 3 REFUSED. |

## Results (`g0_v5_closeout_test_results/`)

* `closeout_run1.json|txt|stdout`, `closeout_run2.json|txt|stdout`: per-test status/time/traceback, environment, checkout identity, key-file hashes, `sentinel_violations`.
* Both runs: g1 91, g2 66, g3 27, g4 32 = **216 PASS, 0 FAIL, 0 ERROR, 0 SKIP, 0 load errors, 0 sentinel violations**; same test ids in both runs; key-file hashes identical across runs.
* Recorded HEAD `a4a8509…` equals the expected SHA; all 15 recorded git blob SHA-1s equal `git rev-parse HEAD:<path>` (`verification.txt`); `bench_code_sha256 = b6f52a8c…d3b0` unchanged; `gpu_used = false`.
* `negctl_wrong_sha.*`, `negctl_no_sha.*`: REFUSED / exit 3.
* Static audit `tools/audit_g0_v5_implementation.py`: 0 findings, 69 traceability rows (3 new), 216 tests present.

## Unchanged

Diff base→fix touches only `gate_g0/g0_run.py` (main/_main/_parser), `tools/` (runner, new `g0_test_env.py`, audit) and the new test file. V1–V5 criteria (V5 sha256 `d36da0c0…cb821`, prereg `8338f4a0…ef6e25c`), `bench/`, Parcae, the model architecture, E1-A original preregistration and the existing `test_e1a_*.py` are untouched. No G0 authorization file exists or was created; no real G0 / BV / E1-A / training / GPU / process-level run; no process was started by the tests.

## Status

CPU TESTS PASS. REAL G0 NOT AUTHORIZED. Next: short acceptance review by ChatGPT/Grok, then a separate application for real G0 authorization.
