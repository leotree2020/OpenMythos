# F3B-D1-A-CPU-003 E1-A G2 — document-only design checkpoint (2026-10-28)

## Scope, provenance, result

- Task: `F3B-D1-A-CPU-003-E1A-G2-DESIGN-001` (read-only source audit, proposed G2 identity/descendant design, checkpoint). **No G2 implementation/test/run authorized**.
- Created document-only branch: `d1-r3-a-cpu-003-e1a-g1-closeout-g2-design-20261028`.
- Parent branch and verified remote HEAD at task start: `d1-r3-a-cpu-003-e1a-g1-impl-20261027` @ `450914367c247231c51be02e13775cb001e69c5d`.
- G1 cross-review closeout document commit (first): `6862a8155119d796363ca81936c23bd4b76b234b`.
- G2 initial design document commit (next): `22c0f17c32f01276d7f9783fcefe82bc862afe89`.
- This checkpoint is a historical snapshot. Its subsequent document/PROJECT_MAP commits may advance the branch HEAD; get the **actual latest SHA** from GitHub before any later work, and keep the G1 execution SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d` distinct from all documentation SHAs.
- G1 accepted result: **G1 REAL-001 CROSS-REVIEW PASS**, run_id `g1_20261028_025922_68ac93`. Source verification and user-reported Grok result are recorded with provenance in `docs/F3B_D1_A_CPU_003_E1A_G1_REAL_001_FINAL_CROSS_REVIEW_CHECKPOINT_20261028.md`. Historical G1-REAL execution checkpoint remains unchanged.
- **G2 stage status: DESIGN DRAFT / INTERNAL SOURCE AUDIT RECORDED / CHATGPT+GROK DESIGN CROSS-REVIEW PENDING / G2 CRITERIA NOT FROZEN / IMPLEMENTATION NOT AUTHORIZED / CPU NOT TESTED / REAL NOT AUTHORIZED.**
- Source audit and test-plan draft: `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md`. This is a proposed design, **not** a finalized specification.

## Objective / environment / input / expected / actual / verdict

| Field | Record |
|---|---|
| Objective | Close accepted G1 real evidence in a separate checkpoint, then draft G2 identity/descendant safety checks without executing experiments. |
| Environment | GitHub repository source at pinned HEAD; document-only authoring; no Python test runtime, process execution, GPU, or external data. |
| Input | Accepted G1 evidence `evidence/g1_20261028_025922_68ac93/` and its result files; bench `gate.py`, `observer.py`, `node.py`, `common.py`, `registry.py`, `janitor.py`, `truth.py`, `validity.py`; G0/G1 existing criteria and checkpoint. |
| Expected | Separate G1 final document; G2 source audit, identity/lineage/exit/reap separation, proposed case matrix, explicit authorization boundaries, checkpoint, PROJECT_MAP entry. |
| Actual | G1 closeout document and G2 design draft committed; G2 design covers G2-D01…D07 and DAC-01…DAC-07; risks G2-R01…R08 recorded. Checkpoint and map will be completed as documentation commits. |
| G1 closeout document | **PASS** (records previously independently accepted evidence; no new validation run). |
| G2 design draft | **PREPARED / CROSS-REVIEW PENDING** (not yet a bilateral design PASS). |
| G2 tests / real | **NOT TESTED / NOT AUTHORIZED**. |

## Fundamental boundaries / unresolved issues

1. G2 concerns **the E1-A gate identity and descendant phase**, not the archived R3-A liveness-predicate G1/G2 FAIL cases.
2. In current source, pidfd proves identity/lifecycle, not historical parent-child relation. `ppid`, `sid`, `pgrp` snapshots can change; registry creation chain and a truly independent witness need agreement before a lineage PASS.
3. No approved descendant reaper plan: `node.request_spawn()` does not itself create externally auditable waitpid evidence for the forked descendant; `Observer.reap_direct()` applies to its own direct children. **G2-R01 remains OPEN and is a real-run blocker.**
4. `Observer.finish_cleanup()/final_cleanup()` and `janitor.run_cleanup_full()` may send signals to live registered processes. They must not be casually invoked during unapproved real G2. Signal/fault injection remains **NOT AUTHORIZED**.
5. Unreported/late CREATED, PID reuse, corrupted registry, bystanders, incomplete `/proc`, reparenting and independent truth are open design constraints (G2-R02…R08). CPU fixtures must precede any actual live-process exercise. No assumption of statistical reliability from G1's single successful real run.
6. Do not freeze the proposed G2 criteria or copy G1-C01…C17 without a design review and separate owner decision. No upstream Parcae, Bench, frozen G0/G1, R3, model architecture, authorization scheme, existing evidence or checkpoint is changed.

## Dependencies and Git hygiene

- Dependencies for this design: reviewed GitHub source and prior G0/G1 checkpoints only; **no new software packages, runtime artifacts, GPU or data downloads**.
- Git file scope intended: additions `docs/F3B_D1_A_CPU_003_E1A_G1_REAL_001_FINAL_CROSS_REVIEW_CHECKPOINT_20261028.md`, `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md`, this checkpoint; an append-only addition to `docs/PROJECT_MAP.md`. Verify this exact scope against the parent SHA before handing over.
- Do not claim the user's local checkout clean from a GitHub remote check: record local status separately when a local checkout is available.

## One next instruction

**Submit G2-DESIGN-001 to ChatGPT and Grok for independent source-grounded review.** In particular, resolve the G2-R01 rightful-reaper question and define independent truth under reparenting, partial enumeration, forged CREATED and bystander conditions. Preserve disagreements and propose the smallest safe CPU-only discriminating experiment. **Do not implement G2, freeze criteria, execute CPU/real process tests, send signals, modify upstream, or enter G3/BV/E1-A without a subsequent distinct owner authorization.**
