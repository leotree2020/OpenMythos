# F3B-D1-A-CPU-003 — J1 correction independent static review checkpoint (2026-10-28)

## CURRENT STATUS — read first

**`J1 SOURCE CORRECTION INDEPENDENT STATIC REVIEW: CHANGES REQUIRED`.** Correction code was pushed by Claude Code, but independent source review found residual **unsupported subject PASS** paths in `UNIQUE_REGISTRY` and `ATTRIBUTION`. **No actual CPU test was run in this review.** Prior high-priority Oracle F01/F02 now appear fail-closed at the static **formal acceptance** layer (`test_acceptance_verdict=BLOCKED`, `aggregate=BLOCKED/NOT_READY`), but functional correctness, exception freedom, the trust boundary and future test readiness are still unproved.

**`J1 CODE SOURCE PRESENT / FUNCTIONAL SYNTAX IMPORTS TESTS NOT TESTED`; `18 FORMAL S/O FIXTURES NOT MATERIALIZED`; `G2 CRITERIA NOT FROZEN`; `G2 CPU NOT TESTED / NOT AUTHORIZED`; `G2 REAL BLOCKED / NOT AUTHORIZED`.** Grok **`DEFERRED / NOT PERFORMED`, NOT PASS**. Owner O-1…O-15 remain UNDECIDED. No claims about native Parcae recursion, math/gradients, Mythos intelligence or model efficiency. G0/G1 historical REAL results unchanged.

## Verified input state and Git anchors

- Developer correction branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028`, **independently verified remote HEAD** `045fa24a1b25f57d27d18dfc9b70b7c437c55898`.
- Correction baseline / prior Claude Code handoff `692e551126c5171b13565f2ece30bf39d6ce8352`; correction source commit `544ed5c2119004a0dbc0319466d45137af2bb9ce`; original implementation HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68` remains historical source.
- **Independent GitHub compare:** base→developer HEAD = **2 commits / 8 changed files / 628 additions / 199 deletions**; `j1/{schema.py,judge.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}` + new developer checkpoint + two docs navigation updates. No changes outside `gate_g2/j1/` and `docs/`, no `bench/`, Parcae, G0/G1, R3, existing prereg/test/evidence/tools modifications; `codec.py` unchanged.
- Developer checkpoint `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_001_CHECKPOINT_20261028.md`, Git Blob `ae8a63bfe678c39f484f4678a999436a7b721482`.
- Source blobs independently read: `judge.py=f84d78a657877da9ced84dd1ccf7fa9f5be09fac`, `schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`, `oracle.py=0a52be247c7b3a0fc08b197f83220e187be04e42`, `tests/test_j1_static_and_unit.py=65f58b3dc267859397575be90dd79fb70b227451`, `README.md=d35d4fa9606e3b5341b74dd73bd2cebc843d4db9`.
- Frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`, `registry.integrity_issues` / `fold` / `lifecycle_issues` and `check_order` read-only comparison.
- This separate **review-doc-only** branch `d1-r3-a-cpu-003-e1a-g2-j1-fix-static-review-20261028`, created from exact developer HEAD `045fa24a1b25f57d27d18dfc9b70b7c437c55898`. Reviewer report `a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`, initial review-report creation commit `0f347c9a82f5ab480e029d7e63a35b4d178e1a0a`.
- **Review Git diff VERIFIED at pre-addendum HEAD `87244f519d773f4a7f7262ac5eadccf13a22c0d9` relative to developer HEAD `045fa24a1b25f57d27d18dfc9b70b7c437c55898`: exactly 4 documentation commits, 4 Markdown paths (2 new report/checkpoint documents + 2 navigation-only edits), 179 added lines / 0 deleted, zero J1 implementation, Bench, Parcae, test, prereg, evidence, G0/G1, R3 or frozen criteria changes. This addendum makes one further checkpoint-only commit; verify its final remote SHA before ending. **Developer local clean Git state and no-Python statement are self-reported, not independently confirmed by remote source.**

## Stage experiment-style accounting — no experiment

| Field | Source-grounded record |
|---|---|
| Purpose | Independently assess Claude Code's F01–F06 correction against V0.1 18-case specification and frozen B0 before any fixture/run authorization. |
| Environment | GitHub connected source fetch and isolated Markdown-only review commits; **no Python, imports, AST, tests, process experiments, signals, GPU or model runtime**. |
| Inputs | Developer branch HEAD/checkpoint/diff; `judge.py`, `schema.py`, `oracle.py`, test source, README, frozen `bench/registry.py` and prior static findings. |
| Expected | Correct earlier false-PASS issues, valid scoped source-only diff, source-grounded findings, truthful FIX-01…FIX-08 assessment and next instruction. |
| Actual | Oracle formal acceptance is deliberately BLOCKED; gate-token check exists; however reviewer identified **4 new/residual source findings**, 3 affecting truth of subject PASS, 1 malformed Oracle robustness problem; all counterexamples are **proposals, NOT EXECUTED**. |
| Original correction Git scope | **PASS** (independently compared 8 permitted changed paths) |
| New source static scientific review | **CHANGES REQUIRED**; not a CPU failure |
| Corrected source runtime syntax/imports/functional behavior | **NOT TESTED** |
| Future fixtures and formal acceptance | `18 S/O NOT MATERIALIZED`; `BLOCKED / NOT_READY` |
| REAL legal reaper/abnormal containment | **BLOCKED / NOT AUTHORIZED** |
| Grok independent review | `DEFERRED / NOT PERFORMED`, not PASS |
| Review-branch changed-file scope | Compare and verify before stage closeout |

## Key findings and status

| Finding | Severity | Issue / smallest planned control | Review status |
|---|---|---|---|
| J1-FIX-REVIEW-F01 | HIGH | `DEAD`/ `ABORTED` for node with no INTENT bypasses B0 `ORPHAN_RECORD` integrity rule and can yield UNIQUE_REGISTRY PASS | **OPEN** |
| J1-FIX-REVIEW-F02 | HIGH | `UNIQUE_REGISTRY` V0.1 pair key (pid,starttime) replaced by `Identity.same_instance`, which conditionally checks boot/namespace | **OPEN** |
| J1-FIX-REVIEW-F03 | HIGH | ATTRIBUTION compares witnesses against incomplete first identity only; concrete boot conflict and same-gate cross-node witness may be ignored | **OPEN** |
| J1-FIX-REVIEW-F04 | MEDIUM | `oracle.aggregate` permits unhashable caller fixture IDs to raise rather than produce fail-closed BLOCKED diagnostic | **OPEN** |
| Previous F01/F02 Oracle correctness | HIGH prior | Invalid input yields `input_valid=False,subject_verdict=None`; formal grade and aggregate cannot PASS | **ADDRESSED STATICALLY, FUNCTIONALLY NOT TESTED** |
| Previous F05/F06 provenance/native adapter | MEDIUM prior | Explicit synthetic-only trust assumption, native B0 adapter unsupported | **SCOPE-LIMITED STATIC RESPONSE** |
| Previous F07 one empty Python interpreter invocation | PROCEDURAL historical | Retained original self-reported deviation; current correction's no-Python claim is separately self-reported | **HISTORICAL FAIL RETAINED; CURRENT INDEPENDENT COMMAND VERIFICATION NOT AVAILABLE** |

## FIX-01…FIX-08 independent reviewer score (never CPU PASS)

| Gate | Reviewer status | Actual source observation |
|---|---|---|
| FIX-01 | **PASS Git scope** | 2 commits, 8 permitted changed paths, no frozen source touched |
| FIX-02 | **PASS for formal static fail-safe / NOT TESTED functionally** | Oracle currently cannot grant formal acceptance; malformed ID exception remains F04 |
| FIX-03 | **CHANGES REQUIRED** | Named gate token equality but insufficient trusted witness conflict resolution (F03) |
| FIX-04 | **FAIL for claimed native-grounded lifecycle consistency / CHANGES REQUIRED** | Orphan node without INTENT unhandled and pair-key drift (F01/F02) |
| FIX-05 | **PASS for scoped limitations only** | All trusted roles declared hypothetical, no direct native adapter |
| FIX-06 | **PARTIAL, NOT EXECUTED** | Test source exists but misses new counterexamples; not executed |
| FIX-07 | **SELF-REPORTED, NOT INDEPENDENTLY VERIFIED** | No Python claimed by developer, history unavailable to connector; prior F07 historical deviation preserved |
| FIX-08 | **PASS document** | Checkpoint records purpose, environment, SHA, limitations, next step |

## Dependencies, open questions and safety controls

- New review requires no packages/data/GPU/runtime. Correct CPU execution requires future review of actual fixture Lane S/O materialization, external trust map origin and independent seal/custody, CPU guard, exact runner and frozen criteria. None is approved.
- `J1-FIX-REVIEW-F01` should be fixed by checking *all node records require prior INTENT* (except run-level records without node) to match frozen integrity rules. Do not let repairing a duplicate identity defect mask legitimate positive FAIL semantics.
- `J1-FIX-REVIEW-F02` requires deciding whether to obey the V0.1 **(pid,starttime)** key or propose a separately approved versioned identity-key amendment. Do not silently redefine.
- `J1-FIX-REVIEW-F03` requires pairwise contradiction and same-gate conflict checks under the explicitly hypothetical harness trust; no claim that B0 has an authenticated gate witness.
- `J1-FIX-REVIEW-F04` requires type-checking caller IDs before set/set-comprehension aggregation, never elevating an unverified row to formal PASS.
- `G2 REAL` remains blocked by legal reaper choice, creator crash/orphan, zero-signal containment and independent operational ownership. All O-1…O-15 owner choices UNDECIDED. Grok review remains DEFERRED; if later disagreement, record and design a separately authorized minimum CPU experiment.

## Single next instruction

**Submit this independent static-review report to Claude Code as a SOURCE-ONLY correction request after owner approval**. Claude Code shall branch from the latest pinned code/review SHA, fix **J1-FIX-REVIEW-F01…F04** (without altering V0.1 expected answers), add *unexecuted* synthetic negative-test source for those minimal counterexamples, then commit/push a new isolated correction checkpoint and STOP. No Python/interpreter/tests/import/fixture materialization, no Bench/Parcae/G0/G1/R3 changes, no criteria freeze/merge, no G2 CPU/REAL or GPU. Then ChatGPT must independently compare Git and review source again. This stage does not grant code-edit permission by itself.

## GitHub stage-closeout verification addendum

- At pre-addendum HEAD `87244f519d773f4a7f7262ac5eadccf13a22c0d9`, the independent review report blob was `d9a657643aa34c3363f713bf554304262f4c06a4` and this checkpoint's pre-addendum blob `5fe0916408ac1f95d439c49f655343a6fb0e58c0`.
- Changed paths **exactly**: `gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`, this checkpoint, `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md` (all Markdown). Review is **documentation-only; no program source was edited**.
- Report contains all four source-grounded findings F01–F04; **NO counterexamples executed**; source-level verdict **CHANGES REQUIRED**. Oracle formal acceptance stays BLOCKED/NOT_READY; actual CPU remains NOT TESTED.
- Developer local process history and clean-tree statement remain **self-reported, not independently audited** by remote GitHub. The earlier first-implementation Python invocation is still retained historically.
- The next action requires a new bounded Claude Code **source-only** authorization and isolated branch, not an automatic run of existing test source.
