# Mythos J1 — Direct CPU verification CI-trigger checkpoint (2026-10-29)

**CURRENT:** native source differential tests **NOT TESTED** (CI runs still 0); local fail-closed runner 11/11 CPU unit PASS; PR #8 and #9 left DRAFT/UNMERGED. No change to original J1 source, Parcae, Bench, Oracle, R3 or model. This checkpoint records actual results only.

## Git

- Research branch `d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-differential-20261029`: earlier pinned code/CI HEAD `78625a9b7959fd32b47cd7d55fbe5c5d45097ebd`, docs-only Contents update `2c6a93719a9d7a89bd76abd35cb825d336ef4ece`. Final HEAD of checkpoint commit must be verified from remote.
- PR #8 https://github.com/leotree2020/OpenMythos/pull/8: branch `d1-r3-a-cpu-003-e1a-g2-j1-direct-schema-ci-draft-pr-20261029`, SHA `5f314460289c5bf9625160a92939f6734b2b49f9`. CI run count=0. Draft not merged.
- PR #9 https://github.com/leotree2020/OpenMythos/pull/9: branch `mini-mythos-j1-direct-schema-cpu-verification-pr-20261029`, SHA `b4cde72188485ed4802a61424d30ad8b3552e9bf`, compared to `mini-mythos-research` base `107c966a4046ebe3b596ae17fd2db3d39e05e768`. Single commit, 5 paths, +899/-0 lines. CI=0 observed. Draft, **DO NOT MERGE**.
- New report `a_predicate_003/gate_g2/j1_iv_s/J1_DIRECT_CPU_CI_TRIGGER_REVIEW_20261029.md`; this checkpoint; append-only PROJECT_MAP/SESSION_START_PROTOCOL navigation.
- GitHub PR #9 copied fixed research source blobs for CI only: J1 schema `551c4a01ed37f73c809776e123f98f6d055ac998`, IV-S lane_s `264971258c6e7ae709d0a884afb35c6538c668d0`, direct test `c4009f2d17853863d2427098d7d86adcc90b0379`. This is NOT a verified test execution.

## Experiments (no exit-code-only PASS)

| Experiment | Environment | Input | Expected | Actual | State |
|---|---|---|---|---|---|
| Fail-closed guard regression | CPython 3.13.5 Linux x86-64 CPU stdlib | 11 synthetic guard tests | 11/11 PASS, 0 errors | 11/11 PASS, 0 errors, 0.004 sec | PASS (local guard only) |
| Local patch validation | git 2.47.3; empty isolated staging repo | Original guard patch (SHA256 `1e049817acfab389afc3ffe04ef2bd2a1a7031da479cbb19e7fa`) | `git apply --check` 0 | exit 0 | PASS (patch syntax only) |
| Original-J1 CPU differential | Fixed source on draft PR #9 | 11 nonofficial synthetic cases | paired structural validity + actual CPU evidence | No Actions / no full local checkout | NOT TESTED / BLOCKED |
| CI trigger tests | Draft PR #8/#9 | branch-specific workflow & pre-existing upstream CPU workflow | run log + check conclusion | no runs/checks found | INCONCLUSIVE |
| Official 18 cases and formal Oracle | separate sealed S/O/trust guard | not executed | remain blocked | `FORMAL_ACCEPTANCE_READY=False` unchanged | BLOCKED |

Log `/mnt/data/guard_recheck_20261029.log` SHA256 `40f9c8f8e0577ef0d2876ec5f55ac4d151be48df527dd8362825a2079f273f08`. Guard ZIP SHA256 `4a2095a96e0ac0821f26756c2ccd316660fda48803b7d3a2c69b6ab32e00e470`. Both remain local only because guard source upload received safety rejection (no bypass attempts).

## Open findings and only next instruction

D-BC-01 J1 regex `$` vs strict `\Z`; D-BC-02 NFC layering; D-BC-03 unfrozen 8MB resource guard; missing SC-08/true custody/IV-O/C/G; Grok second-model external review DEFERRED, OQ-13 and OBS-J1-SEAL-01 open.

**NEXT ONLY:** In authorized Codespaces, checkout PR #9 exact SHA `b4cde72188485ed4802a61424d30ad8b3552e9bf`, validate 3 Git blobs, execute the 11 tests using Python 3.11 CPU and capture command, test-by-test results, exit status, source SHA and logs. If mismatch FAIL, keep the evidence and propose a minimal controlled fix without changing original J1. The source path and command are in `J1_DIRECT_CPU_CI_TRIGGER_REVIEW_20261029.md`. No default-branch merge, official 18 materialization, Oracle unlock, GPU or G2 REAL.
