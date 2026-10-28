# F3B-D1-A-CPU-003 — J1 source correction independent static review 001

**Date:** 2026-10-28 · **Reviewer:** ChatGPT · **Method:** pinned GitHub source-only examination; **NO Python/interpreter/import/AST/pytest/fixture/run/fork/wait/signal/GPU/model code executed**.  
**Developer branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` at verified remote HEAD `045fa24a1b25f57d27d18dfc9b70b7c437c55898`.  
**Correction baseline:** `692e551126c5171b13565f2ece30bf39d6ce8352`; code commit `544ed5c2119004a0dbc0319466d45137af2bb9ce`.  
**Developer checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_001_CHECKPOINT_20261028.md`, Git Blob `ae8a63bfe678c39f484f4678a999436a7b721482`.  
**Source blobs read:** `j1/judge.py=f84d78a657877da9ced84dd1ccf7fa9f5be09fac`; `j1/oracle.py=0a52be247c7b3a0fc08b197f83220e187be04e42`; `j1/schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`; `j1/tests/test_j1_static_and_unit.py=65f58b3dc267859397575be90dd79fb70b227451`; `j1/README.md=d35d4fa9606e3b5341b74dd73bd2cebc843d4db9`. `codec.py` unchanged.  
**Frozen source check:** `bench/registry.py` blob `3f2179e132371dd323f865be8a4d41fa5e58786d`, read-only.  
**Authority:** owner delegates *code changes* to Claude Code; this reviewer only documents. Grok review **DEFERRED / NOT PERFORMED** (not a PASS). All G2 O-1…O-15 decisions UNDECIDED.

## Final verdict

**`J1 CORRECTION STATIC REVIEW: CHANGES REQUIRED`.** The claimed F01/F02 acceptance fail-safe fix and the explicitly synthetic-only boundary are meaningful source-level improvements, but **FIX-04 still permits an unsupported UNIQUE_REGISTRY PASS relative to the frozen native ledger checks**, and other independent predicate/safety defects remain. Therefore **do not proceed to fixture materialization, criteria freeze or CPU tests**.

**`G2 J1 SOURCE EXISTS / STATIC REVIEW CHANGES REQUIRED`; `FUNCTIONAL SYNTAX/IMPORTS/TESTS NOT TESTED`; `FORMAL ACCEPTANCE BLOCKED/NOT_READY`; `18 FORMAL FIXTURES NOT MATERIALIZED`; `G2 CPU NOT AUTHORIZED`; `G2 REAL BLOCKED`.** The review findings are **deductions from source**, not executed counterexamples. No original Parcae, Bench, G0/G1, R3 or old evidence was modified.

## Git scope independently verified

Comparing `692e551126c5171b13565f2ece30bf39d6ce8352` to `045fa24a1b25f57d27d18dfc9b70b7c437c55898`: **2 commits / 8 changed files / 628 insertions / 199 deletions**. Edited `gate_g2/j1/{schema.py,judge.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}`, added one developer checkpoint, changed two documentation-navigation files; **no other paths**. `codec.py` and prior implementation source branch unchanged. Local clean-tree and command history are **developer-reported, not independently observed by the GitHub read-only reviewer**.

## Confirmed improvements (source-level, NOT functional PASS)

- **Prior F01:** `judge.py:45–72,507–515` now sets `input_valid=False,result_kind=INPUT_INVALID,subject_verdict=None` for a rejected Lane S input; `oracle.py:136–160,170–213` rejects such output from even *non-formal* matching acceptance. The well-formed missing-evidence subject BLOCKED is separate.
- **Prior F02:** `oracle.py:53–73,102–133` binds expected card/assertion/subject verdict to 18 versioned V0.1 tuples. `grade_case` reserves `inline_check_verdict` for nonformal illustrations, while its `test_acceptance_verdict` and `aggregate` remain **unconditionally BLOCKED / NOT_READY**. No adjustable `expected_ids`, and `verify_fixture_attestation` is explicitly nonfunctional, not fake signing. This is **fail-closed formal acceptance**, not proof of 18 fixtures or 18 CPU PASS.
- **Prior F03, partial:** `judge.py:241–283` checks for matching nonempty synthetic gate tokens between a REGISTERED record and its selected trusted witnesses, and marks timing as retrospective rather than prevention. This is not an independently authenticated gate-binding source.
- **Prior F04, partial:** `judge.py:98–166` adds RUN_START/RUN_END metadata and creator/ordering checks, and `UNIQUE_REGISTRY` limits PASS to the supplied finite set. However it still misses a frozen `integrity_issues` condition and uses a stronger/different identity comparator from the declared pair key (below).
- **Prior F05/F06:** `schema.py:15–24,60–74,289–339` explicitly limits all roles to **hypothetical hand-authored synthetic data**, acknowledges that `declared_trust_model` is not independently authenticated, and states native-B0 direct ingestion is **NOT SUPPORTED**. No native adapter was invented.
- **Prior F07 procedure:** The historical accidental Python invocation remains recorded. Developer reports **zero Python/test invocation in the correction task**, but an independent reviewer with GitHub read access cannot establish the command history; mark developer claim **SELF-REPORTED / NOT INDEPENDENTLY VERIFIED**.

## New / residual source findings requiring correction

### J1-FIX-REVIEW-F01 — HIGH — ORPHAN_RECORD lifecycle violation still permits UNIQUE_REGISTRY PASS

**Source:** `j1/judge.py:98–166,286–324`; frozen `bench/registry.py:58–83` `integrity_issues` and `fold()` explicitly reject **any node with records but no INTENT** (`ORPHAN_RECORD`). Current `_ledger_prerequisite_problems` enforces `FORKED/REGISTERED` preceded by INTENT, but does **not** require INTENT for an `ABORTED`-only or `DEAD`-only node. It may therefore return an empty problem set for a lifecycle-invalid supplied log.

**Small counterexample (PROPOSED, NOT RUN):** synthetic trusted B0-shaped records with contiguous ordinals:
1. `RUN_START(run_id="run-1", observer_pid=300)`
2. `INTENT(node=nA, creator=O)`
3. `REGISTERED(node=nA, pid=4101, starttime=101, ppid=4100)`
4. `DEAD(node=nGhost)` with **no INTENT for nGhost**.

The closed J1 event schema admits this supplied sequence. `_unique_registry` sees one registered identity and no prerequisite problem, so may return `subject_verdict=PASS` and `NO_DUPLICATE_IN_FINITE_SUPPLIED_VALIDATED_SET`. Frozen `registry.integrity_issues` would report `ORPHAN_RECORD` for nGhost. The same gap arises with `ABORTED(node=nGhost)` alone.

**Required:** ensure a source-grounded **any-node-with-records → prior INTENT** invariant for any `UNIQUE_REGISTRY` PASS that claims native-equivalent internal lifecycle validation. If incomplete, return subject **BLOCKED**. The **positive duplicate FAIL** rule may remain when the contradictory records themselves are independently sound. Add small **unexecuted** DEAD-only and ABORTED-only negative test-source cases; do not run them.

### J1-FIX-REVIEW-F02 — HIGH — Duplicate identity key deviates from the V0.1 (pid,starttime) criterion

**Source:** V0.1 `UNIQUE_REGISTRY` claim explicitly describes **unique (pid,starttime) in the supplied finite REGISTERED set**; `j1/judge.py:295–304` instead calls `Identity.same_instance`. `schema.py:113–121` defines `same_instance` using optional `boot_id` and `pidns` as additional comparison conditions. Thus the duplicate predicate is **not** the documented pair comparison.

**Small counterexample (PROPOSED, NOT RUN):** two distinct registered nodes `nA`, `nB` both have `pid=4101,starttime=101`, but supply syntactically valid `boot_id="boot-A"` for nA and `"boot-B"` for nB. Even though the **declared pair is identical**, `same_instance` returns false and the handler can return PASS after otherwise valid lifecycle rows. This is especially inappropriate in a supposedly single-run synthetic transcript. Similarly namespace variation can silently change the uniqueness key.

**Required:** compare the **documented pinned pair** directly for the finite-set duplicate check, or propose a **separately versioned owner-reviewed change to the unique identity key** including boot/namespace. Do not silently redefine V0.1 expected assertions. Add a source-only negative counterexample for the pair-key difference. If conflicting boot/namespace is logically invalid for one run, classify the supplied set BLOCKED rather than an unsupported PASS.

### J1-FIX-REVIEW-F03 — HIGH — ATTRIBUTION witness consistency is not pairwise and ignores same-gate observations on other nodes

**Source:** `j1/judge.py:241–283` compares each witness to **only `usable[0].identity`**, while `Identity.same_instance` allows boot_id/pidns omissions and is thus **non-transitive** under missing values. The handler additionally chooses witnesses by matching `node_token` and does not resolve a trusted witness with the **same gate_token** but a different node_token.

**Small counterexample A (PROPOSED, NOT RUN):** REGISTERED nA and witness W1 all have `pid=4101,starttime=101,gate=gate-A`, with REGISTERED `boot_id="boot-A"`; W1's boot_id absent. W2 has `pid=4101,starttime=101,boot_id="boot-B"`, same nA/gate-A. Because both witnesses match W1's incomplete identity, and the REGISTERED identity matches W1, the handler can return **PASS** despite the concrete boot-A versus boot-B conflict between known observations.

**Small counterexample B (PROPOSED, NOT RUN):** registered nA gate-A matches W1 nA gate-A, but a second trusted gate-child observation W2 reports **gate-A on nB with a different identity**. The handler filters W2 out based on node_token, so can return **PASS** for nA without acknowledging the conflicting alleged association to gate-A.

**Required:** perform conflict checks **pairwise across all relevant trusted identities**, including contradictory populated boot/pidns fields and any witness claiming the **same gate/ticket** under a different node. Missing trusted gate binding or conflicting source-qualified observations must not be promoted to PASS. Return subject BLOCKED where independently observed identity ambiguity cannot be resolved. Keep ATTRIBUTION retrospective and synthetic-only; no claim of real B0 uniqueness/prevention. Add unexecuted tests for both minimal counterexamples.

### J1-FIX-REVIEW-F04 — MEDIUM — Oracle aggregate can raise an exception on malformed caller-supplied IDs

**Source:** `j1/oracle.py:216–241` gathers raw caller-provided `fixture_id` values and uses `set(ids)` and a set comprehension without checking that each value is a hashable, permitted string. The method is **formally fail-closed in normal cases**, but malformed caller data can still trigger `TypeError` before returning a `BLOCKED / NOT_READY` verdict.

**Small counterexample (PROPOSED, NOT RUN):** `oracle.aggregate([{"fixture_id": ["J1-F01-A"]}])`; list is unhashable, so the set construction can throw instead of recording an instrument-validity problem.

**Required:** validate each case-result record and fixture ID **before set operations**, and return a formally BLOCKED result with a diagnostic for malformed values. No caller-provided fake grade row can ever elevate a formal run above BLOCKED in this stage. Add one unexecuted source test.

## Remaining limitations — not claimed as observed errors

- J1 `gate_token` equality under a **self-declared hypothetical trust map** is only a simulated observation relationship, not independently authenticated same-ticket/fork proof (open OQ-11). Frozen B0 has no native gate-token witness or provenance-preserving adapter, which remains expressly unsupported.
- The exact 18 S/O fixture data, materialized hashes, independent truth/seal, CPU guard and authorized runner **do not exist**. `test_acceptance_verdict` being hard-BLOCKED is scientifically correct here. Neither this review nor static test source validates executable syntax or runtime correctness.
- Four assertions remain `SMOKE_ONLY`; even an eventually passing synthetic J1 test would not demonstrate B0 or G2 REAL safety.
- Developer checkpoint reports clean local Git and no Python calls during correction; GitHub confirms remote changed paths and SHA **but cannot independently prove their local process history**. Preserve earlier F07 self-reported procedural FAIL in historical record.

## FIX-01…FIX-08 independent reviewer grading (source only)

| ID | Independent result | Reason |
|---|---|---|
| FIX-01 | **PASS — Git path scope** | Correct source branch, 8 permitted changed files, 2 commits and no frozen source changes independently confirmed |
| FIX-02 | **PASS (static formal fail-safe) / FUNCTIONAL NOT TESTED** | Invalid J1 input no subject verdict; pinned inventory; formal oracle acceptance always BLOCKED; small malformed aggregate robustness defect separately recorded F04 |
| FIX-03 | **CHANGES REQUIRED** | Gate-token equality implemented, but witness identity consistency and cross-node same-gate conflicts insufficient (review F03) |
| FIX-04 | **FAIL FOR CLAIMED LIFECYCLE-COMPLETENESS / CHANGES REQUIRED** | Native `ORPHAN_RECORD` missed; duplicate key differs from V0.1 (review F01/F02) |
| FIX-05 | **PASS (scope honesty only)** | Trust and native adapter limitations declared; no real authentication validated |
| FIX-06 | **PARTIAL / NOT EXECUTED** | Negative test source exists, but F01–F04 review counterexamples not all covered; tests never run |
| FIX-07 | **NOT INDEPENDENTLY VERIFIED** | Developer self-reports no Python calls; previous task's deviation retained; code/run tests NOT TESTED |
| FIX-08 | **PASS (checkpoint documentation)** | Source, SHA, open questions, stage status and next instruction present |

**Static review not accepted.** Code presence, successful Git commits, desk checks, and developer self-rated PASS do not prove functional correctness.

## Single next instruction

**Use Claude Code for a narrowly bounded SOURCE-ONLY correction of review F01–F04, on a new isolated branch from the current verified developer/review HEAD**. Preserve current V0.1 18 expectations and formal acceptance fail-closed; add unexecuted negative controls for orphan DEAD/ABORTED, pair-key equality, contradictory witness boot/namespace, same-gate cross-node witness, and malformed oracle fixture IDs. No test execution, Python interpreter, fixture materialization, criteria freeze, native Bench adapter, process fork/wait/signals, GPU or REAL. Claude Code must commit/push its corrected branch and task checkpoint, then STOP for a new independent ChatGPT static review. **Owner approval is required for the next code-edit task**; this review has not made those edits.
