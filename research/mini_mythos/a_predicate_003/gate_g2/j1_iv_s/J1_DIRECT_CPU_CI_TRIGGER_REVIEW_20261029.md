# J1 native-schema differential: CI-trigger audit and local guard reproduction

Date: 2026-10-29. **REAL NATIVE J1 CPU EXECUTION STILL NOT TESTED**. Original J1, Parcae, Bench, Oracle, R3 and model code unchanged. Formal J1 18-case acceptance NOT TESTED, G2 REAL BLOCKED, Grok review DEFERRED.

## Verified GitHub events and minimal draft PRs

- Research source branch `d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-differential-20261029` originally pinned at `78625a9b7959fd32b47cd7d55fbe5c5d45097ebd`. A branch-local Contents-API documentation update created `2c6a93719a9d7a89bd76abd35cb825d336ef4ece` in an attempt to expose a normal push trigger. Its GitHub Actions runs/checks remained **0**.
- Draft PR **#8** https://github.com/leotree2020/OpenMythos/pull/8. Head `d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-ci-draft-pr-20261029`, commit `5f314460289c5bf9625160a92939f6734b2b49f9`, targets this research branch. Adds only pull_request support to branch-specific lightweight CI workflow. Runs/checks last checked: **0**.
- Draft PR **#9** https://github.com/leotree2020/OpenMythos/pull/9. Head `mini-mythos-j1-direct-schema-cpu-verification-pr-20261029`, commit `b4cde72188485ed4802a61424d30ad8b3552e9bf`, targets `mini-mythos-research` pinned base `107c966a4046ebe3b596ae17fd2db3d39e05e768`. GitHub compare confirms one commit, exactly five changed paths, +899 / -0 lines; **DRAFT, not merged**. Copies exact pinned original schema/blob and independent test code, adds one stdlib-only CPU job to existing upstream validation workflow. Runs/checks last checked: **0**. The baseline CI workflow already had historical CPU successes, but no success is claimed for this PR.
- GitHub App/API event or repository workflow configuration may explain the missing runs, but the cause is **UNDETERMINED**. Do not claim Github Actions disabled or guaranteed to run.

## CPU local experiment — guard validation only

| Field | Actual evidence |
|---|---|
| Purpose | Detect missing/replaced pinned source, invalid Git head, and fake/ambiguous `unittest` success. Do not turn an absent direct runtime into PASS. |
| Environment | CPython 3.13.5 Linux x86-64 CPU, stdlib only, no GPU/model/native process. |
| Input | 11 deterministic guard unit tests from uploaded, separately retained `Mythos_J1_CPU_Guard_20261029.zip`; plus a patch syntax check. Test vectors are temporary and NOT official Lane S/O. |
| Expected | 11 unit PASS; check command returns 0; missing local Git checkout returns exit 2 and execution NOT_TESTED. |
| Actual | New rerun: **11 tests in 0.004 seconds, 11 PASS, 0 FAIL/ERROR**; `git apply --check` returned 0 against an empty staging repo. Original earlier guard-block test returned exit 2 as documented. Direct native J1 test was NOT executed. |
| Local evidence | `/mnt/data/guard_recheck_20261029.log` SHA-256 `40f9c8f8e0577ef0d2876ec5f55ac4d151be48df527dd8362825a2079f273f08`. ZIP SHA-256 `4a2095a96e0ac0821f26756c2ccd316660fda48803b7d3a2c69b6ab32e00e470`; patch SHA-256 `1e049817acfab389afc3ffe04ef2bd2a1f195839ec1a1a7031da479cbb19e7fa`. |
| State | **PASS — local guard tests and patch syntax only.** Direct J1 and full original 67/27 tests were NOT rerun here. |

A previous attempt to upload the guard source through the GitHub connector returned a safety-filter rejection. It was not retried via a different API; that code remains in the user's local ZIP/patch only. This document is safe review and bookkeeping, not a source upload.

## Exact pinned CPU instructions for an authorized full checkout

Use verification draft PR #9 HEAD `b4cde72188485ed4802a61424d30ad8b3552e9bf`, or its explicit branch without merging:

```bash
cd /workspaces/OpenMythos
git fetch origin mini-mythos-j1-direct-schema-cpu-verification-pr-20261029
git switch --detach b4cde72188485ed4802a61424d30ad8b3552e9bf
git rev-parse HEAD
git hash-object research/mini_mythos/a_predicate_003/gate_g2/j1/schema.py
git hash-object research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/lane_s.py
git hash-object research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests/test_j1_schema_direct_cpu.py
PYTHONPATH=research/mini_mythos/a_predicate_003/gate_g2 python -m unittest discover \
  -s research/mini_mythos/a_predicate_003/gate_g2/j1_iv_s/tests \
  -p 'test_j1_schema_direct_cpu.py' -v
```

Required pins: schema `551c4a01ed37f73c809776e123f98f6d055ac998`; lane_s `264971258c6e7ae709d0a884afb35c6538c668d0`; direct tests `c4009f2d17853863d2427098d7d86adcc90b0379`. Report exact HEAD, Python version, per-case names, count, stdout/stderr, exit status and SHA-256. If there is any FAIL, preserve it and audit the smallest individual input. Do not silently edit J1 or freeze the contract.

## Strict states and next step

- Local guard unit/patch syntax: **PASS**.
- Both CI trigger hypotheses: **NO RUN OBSERVED**, diagnosis **INCONCLUSIVE**.
- Native 11-case direct J1 CPU: **NOT TESTED / BLOCKED BY EXECUTION ACCESS**.
- External independent review / Grok: PENDING / DEFERRED; 18 formal cases NOT MATERIALIZED/NOT TESTED; `FORMAL_ACCEPTANCE_READY=False`, Oracle BLOCKED/NOT_READY, G2 REAL BLOCKED.
- Next only: run the exact source on an authorized Codespaces/full checkout or obtain a real GitHub Actions run with logs. **No upstream changes, merge, GPU, real G2, custodian fiction, or formal acceptance.**
