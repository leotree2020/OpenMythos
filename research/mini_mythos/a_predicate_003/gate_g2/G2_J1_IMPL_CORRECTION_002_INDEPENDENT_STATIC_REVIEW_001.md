# F3B-D1-A-CPU-003 — J1 source correction 002 independent static review 001

**Date:** 2026-10-28 · **Reviewer:** ChatGPT · **Method:** GitHub remote SHA/diff plus read-only source analysis, with NO Python interpreter, import, compile, pytest/unittest, fixtures, process experiment, fork/wait/signal, GPU or model execution.

**Reviewed developer branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028`, remote HEAD **verified** at `26da6082af73c0505d5520001d1cea6ec086df47`.  
**Source baseline:** `a3f6eef883be123028377b3dd1d62ccd5a8e975c`; developer source commit `e70b278a15ce6bf432c95c1b0f5853f13837f1ad`.  
**Source checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_002_CHECKPOINT_20261028.md`, Git blob `4dc6204b54efeddde4b86fdd390344d7ccfbc015`.  
**Source blobs independently read back:** `j1/judge.py=cd5063dbf2754b925a9871cc7d478076ca680cd7`; `j1/oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`; `j1/schema.py=e8b1e3439df54939ee67c9a795187a0174cba853` (unchanged); `j1/tests/test_j1_static_and_unit.py=e9fd2410a382dd569439cadfca79ca822cf6daeb`; frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`. `codec.py` unchanged and frozen sources never edited.

## Review verdict and mandatory distinction

**`FIX2-01…FIX2-08 TARGETED SOURCE CORRECTION: PASS (STATIC AND SCOPED, WITH FIX2-07 SELF-REPORTED)` for the four previously specified findings F01–F04**. However, independent extended source comparison identified **one new HIGH residual malformed-FORKED ledger false-PASS path**. Therefore **`J1 IMPLEMENTATION OVERALL STATIC REVIEW: CHANGES REQUIRED`**, not approval for fixture materialization or CPU testing. A source-level PASS does not establish Python syntax, imports, behavior, 18 fixtures, or any runtime experiment.

**`J1 FUNCTIONAL / SYNTAX / IMPORTS / TESTS NOT TESTED`; `18 FORMAL S/O FIXTURES NOT MATERIALIZED`; `FORMAL ORACLE ACCEPTANCE BLOCKED/NOT_READY`; `G2 CRITERIA NOT FROZEN`; `G2 CPU NOT TESTED / NOT AUTHORIZED`; `G2 REAL BLOCKED / NOT AUTHORIZED`.** Grok is `DEFERRED / NOT PERFORMED` (NOT PASS); owner O-1…O-15 remain `UNDECIDED`. Existing G0/G1 results and Parcae/R3 model evidence unchanged. Developer's local clean tree and no-Python command history are **self-reported**; only remote diff/SHA can be independently confirmed via connector. Historical first-implementation empty-Python interpreter deviation remains recorded.

## Verified Git scope

Baseline `a3f6eef883be123028377b3dd1d62ccd5a8e975c` → developer HEAD `26da6082af73c0505d5520001d1cea6ec086df47`: **2 commits, exactly 7 changed files, 314 insertions / 17 deletions**. Four implementation paths: `gate_g2/j1/judge.py`, `oracle.py`, `README.md`, `tests/test_j1_static_and_unit.py`; one new developer checkpoint and two navigation-only docs. No `bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, R3, upstream Parcae, model architecture, `schema.py` or `codec.py` changes. This review is on a new **docs-only** branch from the exact verified developer HEAD.

## Independent disposition of the four requested fixes

| Review ref / acceptance | Specific inspected evidence | Static result |
|---|---|---|
| `J1-FIX-REVIEW-F01` / `FIX2-02` — ORPHAN_RECORD | `judge.py:110–187` now checks `"INTENT" not in d` for every node with any event; DEAD-only / ABORTED-only ghost cannot reach the `UNIQUE_REGISTRY=PASS` branch. Earlier-INTENT stronger synthetic-only rule is explicitly documented. | **PASS (SOURCE, SCOPED)** |
| `J1-FIX-REVIEW-F02` / `FIX2-03` — pair key | `judge.py:90–98,328–339` compares `_pair(identity)=(pid,starttime)` for two different REGISTERED nodes; `boot_id` / `pidns` cannot hide equality. Different populated metadata in a pair-distinct supplied set now causes BLOCKED, an expressly conservative synthetic-only assumption. | **PASS (SOURCE, SCOPED)** |
| `J1-FIX-REVIEW-F03` / `FIX2-04` — witness consistency | `judge.py:228–317` collects same-node and same-gate cross-node witnesses; blocks conflicting shared gate and known boot/pidns information pairwise; requires uniform witness pair; does not choose first witness or falsely claim prevention. Trust remains a **hypothetical unauthenticated harness declaration**, not kernel truth. | **PASS (SOURCE, SYNTHETIC ONLY)** |
| `J1-FIX-REVIEW-F04` / `FIX2-05` — aggregate malformed IDs | `oracle.py:216–255` checks row/type and only includes plain-string IDs in set operations; for JSON-like malformed list/dict/bool/int/None IDs, returns structured `BLOCKED / NOT_READY`. Its full formal acceptance stays hard-BLOCKED, even on a caller's fabricated 18 PASS rows. | **PASS (SOURCE, JSON-LIKE SCOPE)** |

**Test source present but unexecuted:** `j1/tests/test_j1_static_and_unit.py` includes 24 added test methods across four new classes: five orphan/lifecycle, five pair-key, ten witness-conflict, four malformed-ID controls. These methods were **NOT RUN / NOT IMPORTED / NOT COMPILED**. Their existence and positive assertions are not functional evidence. The described OQ-11 gate association is a simulated token, not independently authenticated; OQ-12 formal attestation prerequisites remain missing.

## New independently found defect — J1-FIX2-REVIEW-F05 HIGH: missing PID in FORKED record can still allow UNIQUE_REGISTRY PASS

**Frozen source:** `research/mini_mythos/a_predicate_003/bench/registry.py:60–83` runs `integrity_issues` over folded nodes and, when `FORKED` exists but its `pid` is **not an integer**, reports `MALFORMED_FORKED`. This is an explicit integrity check distinct from ORPHAN_RECORD and the RUN_START lifecycle prerequisites. No frozen source edit is needed or allowed.

**New J1 source:** `gate_g2/j1/schema.py:212–244` declares `FORKED` with optional identity (node token required, identity `"opt"`) and no mandatory fork PID in `raw_fields`. `gate_g2/j1/judge.py:110–187` checks that `FORKED` follows node INTENT, but **does not require a source-qualified fork PID / identity field for a FORKED event** before allowing `UNIQUE_REGISTRY` positive completeness. `judge.py:320–367` returns PASS if at least one valid REGISTERED exists, no duplicate pair exists, no read errors and its incomplete ledger prerequisite predicate reports no problem.

**Minimal controlled counterexample — PROPOSED, NOT EXECUTED:**

- `RUN_START` ordinal 1: `raw_fields={"run_id":"run-1","observer_pid":300}`, no node.
- `INTENT` ordinal 2: `node_token="nA", raw_fields={"creator":"O"}`.
- `FORKED` ordinal 3: `node_token="nA"`, **no identity and no pid in raw_fields** (admitted by current synthetic schema).
- `REGISTERED` ordinal 4: `node_token="nA", identity={"pid":4101,"starttime":101,"ppid":4100}`.

Use `source_handle="L"`, `event_kind` as above, `read_status="OK"`, a declared hypothetical `B0_LEDGER` trust handle, and standard valid field syntax. This finite synthetic input contains a perfectly normal-looking REGISTERED, so no duplicate violation arises; `_ledger_prerequisite_problems` is not designed to detect the missing fork PID and the handler can return `subject_verdict=PASS` with `NO_DUPLICATE_IN_FINITE_SUPPLIED_VALIDATED_SET`. **Frozen native registry integrity semantics would reject the matching unqualified FORKED record as `MALFORMED_FORKED`.** This is a source-grounded logical discrepancy, not observed runtime behavior.

**Why this matters:** The J1 V0.1 F02-B PASS requires **all scoped ledger prerequisites**; the source claims it has restated native Bench integrity/lifecycle semantics. A malformed fork record must not be presented as a validated clean finite ledger. Even though real native registry ingest is expressly unsupported, a synthetic source purporting to project B0-shaped FORKED records needs an explicit field/presence rule. Omitting the check can inflate a synthetic `UNIQUE_REGISTRY=PASS`.

**Required small correction:** Define how a synthetic `FORKED` exposes its source-reported integer PID, and when `FORKED` is present, **do not grant UNIQUE_REGISTRY PASS unless that required PID was observed and valid**. Two defensible designs: (A) require the existing normalized `identity` for FORKED and validate its pid, or (B) introduce an explicitly versioned `forked_pid` normalized raw field with a fail-closed source projection. Do not silently invent a real native-B0 adapter or corrupt a historical V0.1 expected verdict. Use `BLOCKED` for valid-but-unqualified missing fork evidence or `INPUT_INVALID` for a syntactically invalid mandatory field, with clear separation between instrument-invalid and subject BLOCKED. Add one unexecuted negative source test and one complete FORKED positive-control source case, preserve positive duplicate FAIL.

**Limit of finding:** It does NOT invalidate F01–F04's targeted static fixes; it blocks promotion of the whole J1 ledger integrity claim. It was found by source comparison, not a CPU run. No code was changed in this review.

## Scope/assumption observations — not new technical PASS

- Stronger `RECORD_BEFORE_INTENT` is marked synthetic-only and conservative; do not equate it with literal source equivalence to frozen `bench/registry.check_order`.
- Pair-distinct records with conflicting populated boot_id/pidns cause `BLOCKED`, not FAIL/PASS. That is a conservative policy to review before freezing criteria, and does not on its face change the 18 V0.1 expectations.
- Same-gate same-node witness equality is an **assumed synthetic association**, not a verified one-to-one kernel ticket mapping; no external authenticated trust map, lawful reaper, real G2 prevention or recipient proof exists.
- Formal Oracle `grade_case` and `aggregate` remain `BLOCKED / NOT_READY` by design. A detector source-level result is never a G2 REAL security acceptance.
- `ZOMBIE_AT_T` still depends on `Identity.same_instance` and OQ-1; no requested functionality was expanded, and no tests were executed.

## Independent FIX2-01…FIX2-08 assessment (not CPU/test status)

| Gate | Independent source assessment |
|---|---|
| FIX2-01 | **PASS** — remote HEAD and exact 7 permitted changed files independently checked |
| FIX2-02 | **PASS (STATIC, SCOPED)** — orphan and stronger node-order rule present |
| FIX2-03 | **PASS (STATIC, SCOPED)** — correct pair key and conservative extra metadata blocker |
| FIX2-04 | **PASS (STATIC, SYNTHETIC ONLY)** — pairwise identity conflicts / cross-node same-gate signals no easy PASS |
| FIX2-05 | **PASS (STATIC, JSON-LIKE INPUT)** — malformed-ID set operations guarded; formal Oracle remains BLOCKED |
| FIX2-06 | **PASS FOR SOURCE EXISTENCE / TESTS NOT TESTED** — 24 proposed new tests; exact behavior unverified |
| FIX2-07 | **REMOTE GIT SCOPE PASS / LOCAL ZERO-PYTHON SELF-REPORTED ONLY** — no way to independently attest developer's process history from GitHub; earlier initial-task Python deviation remains on record |
| FIX2-08 | **PASS (CHECKPOINT DOCUMENT)** — source SHA, environment, expected/actual source diff, open OQs and one next task recorded |

**OVERALL `CHANGES REQUIRED`** because of J1-FIX2-REVIEW-F05, not because any Python test failed.

## Unique next instruction and no-run gate

Give **Claude Code** a minimal **SOURCE-ONLY** correction of **new F05 alone**, after explicit owner code-stage permission: require source-grounded pid presence for synthetic FORKED in J1's finite ledger check; preserve V0.1 18 expected statuses, original Oracle formal BLOCKED/NOT_READY, and all existing F01–F04 fixes. Add unexecuted negative/positive FORKED source test cases and a new checkpoint. Claude Code creates a NEW isolated code branch from a pinned latest reviewed HEAD, edits only `gate_g2/j1/` + task-specific docs, commits/pushes, STOPS. ChatGPT then independently static-reviews the diff.

**No Python, import, compile or pytest, fixture materialization, CPU run, process fork/wait/signal/janitor, GPU, native-B0 adapter, frozen Bench/Parcae/G0/G1/R3 change, criteria freeze, merge or G2 REAL.** Grok remains deferred; O-1…O-15 owner undecided. A later, separately approved CPU correctness stage is necessary before any model/process claim.
