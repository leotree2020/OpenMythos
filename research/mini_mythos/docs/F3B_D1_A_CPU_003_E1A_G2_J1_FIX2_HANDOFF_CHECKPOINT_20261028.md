# F3B-D1-A-CPU-003 — J1 second source correction handoff checkpoint (2026-10-28)

## Read-first official state

**`J1 FIX2 CLAUDE CODE SOURCE-ONLY HANDOFF PREPARED / CLAUDE CODE NOT INVOKED`.** Latest independently reviewed J1 correction remains **`STATIC REVIEW CHANGES REQUIRED`** (four findings). This documentation stage has **NOT** edited J1 code, materialized fixtures or run experiments.

**`G2 J1 SYNTAX/IMPORTS/FUNCTIONAL TESTS NOT TESTED`; `18 FORMAL S/O FIXTURES NOT MATERIALIZED`; `FORMAL ORACLE ACCEPTANCE BLOCKED / NOT_READY`; `G2 CRITERIA NOT FROZEN`; `CPU NOT TESTED / NOT AUTHORIZED`; `G2 REAL BLOCKED / NOT AUTHORIZED`.** Grok review **`DEFERRED / NOT PERFORMED`**, not PASS; owner choices O-1…O-15 remain UNDECIDED. G0/G1 historical REAL results unchanged; native Parcae/Bench and R3 remain unmodified.

**Owner role split:** ChatGPT is responsible for architecture/evidence reviews, detailed acceptance requirements and Git checkpoints. Claude Code is responsible for code edits **after the owner sends it this specific, bounded handoff**, but code authorization does not authorize tests. No Claude Code task was started in this conversation.

## Verified source and Git anchors

- Read-first prior reviewer branch `d1-r3-a-cpu-003-e1a-g2-j1-fix-static-review-20261028` **remote HEAD `41030bc9e7d01a714fc091c60ba3a07b0a8be5cd`**, independently fetched and matched before creating this branch.
- Latest review record `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`, Git Blob `d9a657643aa34c3363f713bf554304262f4c06a4`. Prior reviewer checkpoint `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, Git Blob `4f68894ff960c3b12a94687bdc0a4a41bc941c29`.
- Latest developer correction branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` **remote HEAD `045fa24a1b25f57d27d18dfc9b70b7c437c55898`**; developer code commit `544ed5c2119004a0dbc0319466d45137af2bb9ce`. This source was not modified in the reviewer/handoff branches.
- Frozen source `bench/registry.py`, blob `3f2179e132371dd323f865be8a4d41fa5e58786d`, inspected read-only at `integrity_issues,fold,lifecycle_issues,check_order`. J1 `judge.py=f84d78a657877da9ced84dd1ccf7fa9f5be09fac`, `schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`, `oracle.py=0a52be247c7b3a0fc08b197f83220e187be04e42` pinned at prior correction HEAD. All source blobs are **input evidence**, not new test evidence.
- This handoff branch: `d1-r3-a-cpu-003-e1a-g2-j1-fix2-handoff-20261028`, created from verified review SHA `41030bc9e7d01a714fc091c60ba3a07b0a8be5cd`.
- **New primary deliverable:** `research/mini_mythos/a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_002_HANDOFF_20261028.md`, initial creation commit `807048a2e7be8f27638a1a1b69b4524bf1b428ef`.
- **This checkpoint and navigation updates follow that handoff; Claude Code must fetch actual final handoff branch HEAD and pin it**, not use the initial branch source SHA. Verify final Git compare/doc scope and record an addendum. Local/user Git working tree and Claude Code command history were not inspected by this document session.

## Experimental-management accounting — DOCUMENTS ONLY

| Field | Value |
|---|---|
| Objective | Turn four source-grounded residual findings into exact, minimal Claude Code code-only correction requirements without expanding G2 scope. |
| Environment | GitHub connector remote source reads, docs-only Git branch and Markdown commits; no Python, local CPU runtime, GPU, process experiments, test data or model training. |
| Inputs | Latest independent static review F01–F04/checkpoint, V0.1 18-case accepted **draft scope**, frozen Bench registry, J1 judge/schema/oracle source. |
| Expected | Pin current Git SHA, issue source-only handoff with explicit F01–F04 minimal counterexamples and `FIX2-01…FIX2-08` static checks, protect Oracle fail-closed and V0.1 18 expected results. |
| Actual | Full Claude Code correction task prepared and Git-committed; no J1 source files changed, no Claude Code call and no test execution. |
| Handoff artifact | **PASS (document creation/readback pending)**, not code/CPU PASS. |
| Code corrections F01–F04 | **NOT STARTED**, previous J1 review remains CHANGES REQUIRED. |
| J1 functional tests / 18 S/O hashes | **NOT TESTED / NOT MATERIALIZED**. |
| G2 REAL safety | **BLOCKED / NOT AUTHORIZED**. |
| Grok independent review | **DEFERRED / NOT PERFORMED**; no opinion fabricated. |
| Git branch changed-file scope | **PASS (pre-addendum)**: independently compared review source `41030bc9e7d01a714fc091c60ba3a07b0a8be5cd` → current `4cbe376e847303665be311bea3f08594d6a6595d`: 5 commits, 4 Markdown files, 177 insertions/0 deletions, **0 J1 code/Bench/Parcae/criteria/evidence changes**. Checkpoint-only verification addendum creates one more doc commit; fetch its final HEAD. |

## Open residual findings (no execution)

| Code | Severity | Minimal source-only correction target | State |
|---|---|---|---|
| `J1-FIX-REVIEW-F01` | HIGH | Any node with a DEAD-only or ABORTED-only record and no prior INTENT must not gain `UNIQUE_REGISTRY=PASS`; source-grounded `ORPHAN_RECORD` condition | **OPEN — CLAUDE CODE TASK PREPARED** |
| `J1-FIX-REVIEW-F02` | HIGH | Duplicate across distinct REGISTERED nodes measured by exactly documented `(pid,starttime)`, not conditionally boot/namespace-aware `same_instance` | **OPEN — CLAUDE CODE TASK PREPARED** |
| `J1-FIX-REVIEW-F03` | HIGH | Pairwise trusted synthetic witness contradictions incl. omitted-field non-transitivity, conflicting known boot/pidns, same-gate observations on other nodes ⇒ BLOCKED, not apparent ATTRIBUTION PASS | **OPEN — CLAUDE CODE TASK PREPARED** |
| `J1-FIX-REVIEW-F04` | MEDIUM | `oracle.aggregate` validates malformed/unhashable fixture IDs before set operations and returns formal `BLOCKED/NOT_READY` not exception | **OPEN — CLAUDE CODE TASK PREPARED** |

Original prior F01/F02 Oracle fail-closed source changes should remain preserved (formal aggregate always BLOCKED). All 18 official V0.1 expected **subject** results stay 5 narrowly scoped PASS / 5 FAIL / 8 BLOCKED; **NONE are actual execution results**. Four assertions remain `SMOKE_ONLY`. No real authenticated gate/ticket binding or native B0 adapter has been created; those stay open OQs. Historical first-task empty Python invocation remains **self-reported procedural FAIL**; subsequent developer-reported zero Python invocation cannot be independently verified by GitHub.

## Dependencies, risks and future gates

- All new source must stay in `gate_g2/j1/`; test-source additions may be written there **without execution**. Checkpoint in `docs/`, navigation-only PROJECT_MAP/SOP updates. No Parcae/Bench/G0/G1/R3/frozen criteria/evidence code changes.
- Formal acceptance needs separately authorized sealed S/O fixture bytes, independent Oracle and trust origin, audited CPU guard/runner, frozen criteria and actual CPU evidence. No fake hashes or test PASS.
- G2 REAL safety remains blocked on lawful reaper, creator crash/orphan, zero-signal cleanup and external operational containment. No source-only J1 change can fix this.
- User's owner-decisions O-1…O-15 and simulation assumptions remain open. If later Grok review disagrees, preserve exact differences and design a separately authorized minimal CPU arbitration experiment.

## Single next instruction

**Give the user the current `CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_002_HANDOFF_20261028.md` and the verified final Git branch HEAD, then stop**. The user may hand it to Claude Code; Claude Code must create its own isolated correction branch from the final handoff commit, fix F01–F04 in source plus unexecuted negative tests, commit/push and write checkpoint **without invoking Python or tests**. The next ChatGPT review starts by independently retrieving Claude's new branch/checkpoint and actual diff; do **not** proceed to CPU/REAL, freeze or merge.

## Verified remote handoff deliverable, Git and scope (addendum)

- At pre-addendum remote HEAD `4cbe376e847303665be311bea3f08594d6a6595d`, handoff file blob `81391b48698add404477794214b79eedc28b823e` and checkpoint pre-addendum blob `1cddf7cf18b02e77490bb9b5873ac49758c18d8c` were fetched from GitHub.
- Verified **all four exact finding IDs** `J1-FIX-REVIEW-F01,F02,F03,F04` are present and individually described in the code-only handoff, with controlled minimal counterexamples and `FIX2-01…FIX2-08` static acceptance criteria.
- **Exactly four changed Markdown paths** relative to the frozen input review: `a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_002_HANDOFF_20261028.md`, this checkpoint, `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. There are **no** program/code/test/fixture/frozen source modifications on this handoff branch.
- Source-level test cases in the handoff are **proposals**, not executed proofs. No package/runtime was used; this is not a real G2 process safety result.
- **Actual final branch HEAD must be re-fetched after this addendum**. Claude Code must pin that HEAD at task start rather than the earlier base or an intermediate docs commit. Local checkout clean state **NOT TESTED** by this GitHub-only work.
