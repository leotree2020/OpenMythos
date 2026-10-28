# OpenMythos — Claude Code SOURCE-ONLY correction 002 (J1-FIX-REVIEW-F01–F04)

**Task ID:** `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-002`  
**Date:** 2026-10-28  
**Task preparer:** ChatGPT (research reviewer and checkpoint owner)  
**Designated code implementer:** Claude Code, only when this handoff is submitted to it by the project owner.  
**Status:** `HANDOFF PREPARED / CODE CORRECTION NOT STARTED / CPU NOT TESTED / G2 REAL BLOCKED`.  
**Scope:** smallest defensible source-only fix of **four findings** in the latest independent static review. **Absolutely NO Python execution, imports, compile, pytest/unittest, run, actual fixture data, process tests, or criteria freeze.**

## 0. Provenance and mandatory read-first protocol

Repository: `leotree2020/OpenMythos`.

- **Independent review source:** branch `d1-r3-a-cpu-003-e1a-g2-j1-fix-static-review-20261028` @ **`41030bc9e7d01a714fc091c60ba3a07b0a8be5cd`**, verified before the handoff branch was made.
- **Prior developer correction source:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` @ **`045fa24a1b25f57d27d18dfc9b70b7c437c55898`** (developer code commit `544ed5c2119004a0dbc0319466d45137af2bb9ce`).
- **Handoff branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix2-handoff-20261028`, created from exact independent review SHA `41030bc...`. **Before any code work, fetch this handoff branch's actual FINAL remote HEAD, verify content and create a NEW isolated correction-code branch from that final HEAD.** Do not assume the review SHA is the final handoff SHA; this document/checkpoint have their own commits.
- **Read in order:** `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`; `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX2_HANDOFF_CHECKPOINT_20261028.md`; `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`; this entire handoff; `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`; `gate_g2/j1/{judge.py,schema.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}`; frozen `research/mini_mythos/a_predicate_003/bench/registry.py` read-only, especially `integrity_issues,fold,lifecycle_issues,check_order`.
- **Pinned source blobs at reviewed developer HEAD:** `j1/judge.py=f84d78a657877da9ced84dd1ccf7fa9f5be09fac`; `schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`; `oracle.py=0a52be247c7b3a0fc08b197f83220e187be04e42`; `tests/test_j1_static_and_unit.py=65f58b3dc267859397575be90dd79fb70b227451`; frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`.
- If any branch has moved, blob differs, required source is missing, or local work would be overwritten: **BLOCKED**; record actual conflict and stop. Do not silently rebase to a different history or merge an older branch.

## 1. Permitted file changes / stop boundary

**Allowed:** edit only isolated `research/mini_mythos/a_predicate_003/gate_g2/j1/` code, `README.md` and **unexecuted test source** there; create one new task-specific checkpoint in `research/mini_mythos/docs/`; optionally append navigation references to `docs/PROJECT_MAP.md` and `docs/SESSION_START_PROTOCOL.md`.

**Forbidden:** any edits to `bench/`, Parcae upstream, `gate_g0/`, `gate_g1/`, R3, `prereg/`, `evidence/`, existing research tests/tools outside the isolated `j1/` subtree, frozen criteria, original checkpoints/reviews, Transformer/model code. No fixture S/O JSON materialization, hashes of nonexistent fixture files, test outputs or fake authorization/acceptance evidence. No merge, pull request merge or stage advancement.

**No Python invocation of any kind:** not even `python3` empty invocation, `py_compile`, import, `ast`, pytest/unittest, code execution or generator scripts. Static text/source review plus Git metadata/diff allowed. No fork/exec/subprocess/wait/signals/janitor, GPU, actual gated-child run or native B0 integration. This stage is a **code-writing** stage only; all behavior and syntax results remain **NOT TESTED**.

**Preserve** V0.1's 18 expected subject outcomes (5 scoped PASS / 5 FAIL / 8 BLOCKED), the five evidence-sensitive and four `SMOKE_ONLY` assertions, and formal Oracle acceptance **unconditionally `BLOCKED / NOT_READY`**. An apparent syntax-clean source or Git success is not a CPU PASS.

## 2. F01 HIGH — source-grounded ORPHAN_RECORD lifecycle requirement

**Code:** `j1/judge.py:_ledger_prerequisite_problems` (reviewed lines 98–166) and `_unique_registry` (286–324). **Frozen source:** `bench/registry.py:integrity_issues` calls `fold(records)` and reports `ORPHAN_RECORD` on **any node with records but no INTENT**, even if its only record is `DEAD` or `ABORTED`.

**Required implementation:** For **any** finite supplied synthetic B0 ledger that would yield `UNIQUE_REGISTRY=PASS`, every node having a native node-kind record must have a valid `INTENT`; a node-only `DEAD` or `ABORTED` without INTENT must produce **subject BLOCKED** with a specific lifecycle-basis code (such as `LEDGER_PREREQUISITE_FAILED_ORPHAN_RECORD`). Conservatively enforce INTENT's causal position before node lifecycle records when the claim depends on full internal consistency, but distinguish historical native rule strength and report an intentionally stronger synthetic-only condition if adopted.

**Proposed controlled negative cases (WRITE TEST SOURCE ONLY; DO NOT RUN):** RUN_START valid; INTENT nA; REGISTERED nA; DEAD nGhost only, all ordinals contiguous → BLOCKED, not PASS. Replace DEAD nGhost with ABORTED nGhost → BLOCKED. For positives, a well-formed INTENT nGhost then DEAD nGhost should not be rejected solely as orphan. Maintain positive `FAIL` detection for independently sound duplicate REGISTERED identities even when another unrelated lifecycle problem is present, as originally scoped.

**Do not modify frozen registry to make the source comparison pass.**

## 3. F02 HIGH — implement exactly V0.1's UNIQUE_REGISTRY (pid,starttime) key

**Code:** `j1/judge.py:_unique_registry` currently checks `a.identity.same_instance(b.identity)`; `j1/schema.py:Identity.same_instance` also conditionally checks `boot_id` and `pidns`. That is not the predeclared *pair key*.

**Required implementation:** UNIQUE_REGISTRY positive duplicate **FAIL** uses exactly the documented key `(pid, starttime)` across distinct registered nodes inside the finite supplied synthetic set. Optional boot_id/pidns data must **not** turn an equal pair into an unjustified uniqueness PASS. If independent source metadata are inconsistent, note that inconsistency separately and, where necessary, classify evidence **BLOCKED**, but never use different optional metadata to assert "no duplicate (pid,starttime)". Avoid changing `Identity.same_instance` globally unless a separate source-grounded reason requires it; its semantics in ZOMBIE_AT_T and ATTRIBUTION have other scope.

**Write unexecuted tests:** nA and nB have equal `pid=4101,starttime=101` but `boot_id="boot-A"` vs `"boot-B"` (and a second case with differing `pidns`) → **not PASS**; prefer a positive `FAIL` for observed duplicate **pair** where registered records are valid and source-qualified, or `BLOCKED` if an explicit independent contradictory-run invariant is newly defined. A genuinely different starttime is not a duplicate pair. The 18 V0.1 expectations **must not change**.

## 4. F03 HIGH — ATTRIBUTION multi-witness conflicts (including different node on same gate)

**Code:** `j1/judge.py:_attribution` compares each witness to only the first witness, then compares REGISTERED to the first. Because `Identity.same_instance` allows omitted boot/namespace fields, it is **not transitive**; a concrete populated-field conflict can be ignored. Current `usable` filter selects same node_token only and can miss a trusted witness claiming the **same gate_token** but a different node.

**Required:** For each registered node and its explicit synthetic `gate_token`, gather **all** trusted hypothetical GATE_CHILD_OBSERVATION records relevant to that gate/ticket, including same-gate observations attached to a different node. Validate readable source, gate association, node-binding consistency and **pairwise compatibility of all known identity fields**. A contradiction between two populated `boot_id`s or `pidns`s, even if another witness omits them, must force **subject BLOCKED**, not an apparent PASS. Same gate claimed for different nodes/identities without an independently disambiguating trusted mapping must be **BLOCKED**. Missing or conflicting gate_token also BLOCKED. Do not pick a convenient first witness or let iteration order change the verdict.

**Three negative source-only cases:** (A) registered `boot-A`, W1 `boot_id=None`, W2 `boot-B`, same pid/starttime/gate/node → BLOCKED. (B) registered nA gate-A, W1 nA gate-A matching, W2 nB gate-A different identity → BLOCKED. (C) same gate and node, W1/W2 have conflicting nonempty pidns or known pid/starttime → BLOCKED. Include one clean synthetic positive agreement and one genuine contradictory identity **FAIL** on a single unambiguous trusted witness; preserve **retrospective ATTRIBUTION**, never claim pre-release prevention or real native B0 gate proof. Trusted simulated source roles are only declared **hypothetical harness authority**; the runtime origin remains unauthenticated.

**Guard:** Do not promote a witness for gate-B to a match to gate-A merely because node_token matches. Do not invent a trusted native B0 witness, backend adapter or new formal assertion.

## 5. F04 MEDIUM — Oracle.aggregate handles malformed caller ids fail-closed, not via TypeError

**Code:** `j1/oracle.py:aggregate` computes `set(ids)` over unchecked caller-controlled `fixture_id` fields. A list or dictionary is unhashable, leading to **TypeError** instead of a structured result.

**Required:** Validate each provided case-result is a plain dict and each `fixture_id` a string before constructing sets or counting duplicates. Detect missing, unknown, malformed or duplicated IDs without raising; return diagnostic reasons. Explicit **formal run verdict always remains `BLOCKED`, `acceptance_state=NOT_READY`, `FORMAL_ACCEPTANCE_READY=False`** even for 18 forged `PASS` rows. Malformed nested objects (IDs list/dict, integer, booleans, missing key) cannot crash the acceptance reporter or elevate confidence. Keep 18-ID inventory fixed, no user-provided `expected_ids` override.

**Write unexecuted tests:** `aggregate([{"fixture_id":["J1-F01-A"]}])`, `aggregate([{"fixture_id":{"x":1}}])`, `aggregate([{"fixture_id":True}])`, `aggregate([{"fixture_id":None}])` → all return structured BLOCKED/NOT_READY with malformed-ID diagnostics, no exception. Additional caller-forged 18-case PASS rows must remain BLOCKED.

## 6. Acceptance matrix for CODE WRITING ONLY

| Gate | Static expected evidence | Status to record |
|---|---|---|
| FIX2-01 | Exact remote SHA read; new isolated code branch; permitted Git diff only | PASS/FAIL/BLOCKED |
| FIX2-02 | Orphan DEAD/ABORTED cases cannot lead to lifecycle-validated UNIQUE_REGISTRY PASS, positive duplicate FAIL preserved | PASS/FAIL/BLOCKED; CPU NOT TESTED |
| FIX2-03 | Duplicate test uses exact V0.1 (pid,starttime) key, not `same_instance` with optional fields | PASS/FAIL/BLOCKED; CPU NOT TESTED |
| FIX2-04 | Pairwise known-field conflict and same-gate cross-node witness cannot yield ATTRIBUTION PASS | PASS/FAIL/BLOCKED; CPU NOT TESTED |
| FIX2-05 | Malformed Oracle fixture IDs safely produce BLOCKED/NOT_READY result; no exception predicted, no formal PASS path | PASS/FAIL/BLOCKED; CPU NOT TESTED |
| FIX2-06 | Unexecuted negative & positive test **source** and limited README/explanation; 18 official fixtures/hashes remain NOT MATERIALIZED | PASS/FAIL/BLOCKED |
| FIX2-07 | Zero Python invocation claimed in correction, historical original F07 procedural FAIL retained, no frozen Bench/Parcae/G0/G1/R3/criteria/evidence changes | SELF-REPORTED + Git PASS/FAIL/BLOCKED |
| FIX2-08 | New checkpoint: purpose, environment, inputs, expected, actual code diff, dependency/Git status, complete matrix, unresolved OQs, single next step | PASS/FAIL/BLOCKED |

**Independent reviewer will re-check:** exact source diff (not developer self-PASS), F01–F04 proposed counterexamples, whether two or more trusted witnesses can contradict while PASS remains possible, and the metadata/domain ceiling. **No functional/CPU test PASS may be reported** because none is permitted to run now.

## 7. Open scientific questions and no scope expansion

- **OQ-11** same gate/ticket association remains a field in synthetic observations, not an independently authenticated binding. Do not silently decide an owner design choice.
- **OQ-12** independently sealed S/O bytes, attestation verifier, approved CPU guard/runner, frozen criteria and trust-origin authentication remain **unimplemented**. Formal Oracle `BLOCKED/NOT_READY` is expected, not a defect to "fix".
- OQ-1…OQ-10 and owner O-1…O-15 remain open unless a later separately approved specification addresses them. Four V0.1 assertions remain **SMOKE_ONLY**.
- Source review is not enough to prove any runtime behavior, Python syntax, data materialization, kernel descendant safety or original Parcae mathematical correctness. G2 REAL remains **BLOCKED** by lawful reaper, orphan handling and zero-signal abnormal cleanup.
- Grok is `DEFERRED/NOT PERFORMED`; do not invent a Grok PASS or call the result a double-reviewed gate.
- If fixing the above requires changing a V0.1 expected result, altering non-j1 frozen code, or asserting a new trusted real source, **record BLOCKED and request owner review** rather than silently changing scope.

## 8. Git commit, checkpoint, STOP

1. Pin actual **final** handoff branch HEAD and verify the required files, then create a **new isolated code branch**; preserve the original implementation/correction and reviewer branches.
2. Edit only permitted `gate_g2/j1/` source and unexecuted test source; optionally README and a **new** checkpoint plus navigation docs. **Never run Python or tests**.
3. Review only text/source and `git diff` using Git and editor tools; **do not compile, import, launch interpreter or run code**. If tool restrictions or missing source prevent proof, record `BLOCKED`.
4. Commit/push and verify actual changed paths, remote final HEAD and local status; record every FIX2-01…FIX2-08 and the explicit `NOT TESTED` functional state.
5. **STOP:** no tests, no CPU/REAL, no fixture S/O, no authorization changes, no merge. Return branch, baseline SHA, code commit, final remote HEAD and checkpoint to ChatGPT for independent static audit.

## 9. Copy-ready Claude Code starter

> OpenMythos `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-002`. You are assigned **SOURCE-ONLY** fixes for four independent findings `J1-FIX-REVIEW-F01…F04`. Read `SESSION_START_PROTOCOL.md`, `F3B_D1_A_CPU_003_E1A_G2_J1_FIX2_HANDOFF_CHECKPOINT_20261028.md`, `G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`, and the full `CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_002_HANDOFF_20261028.md` on `d1-r3-a-cpu-003-e1a-g2-j1-fix2-handoff-20261028`. **Fetch and pin its actual final remote HEAD**, then create a new isolated branch. Fix in `gate_g2/j1/`: F01 orphan DEAD/ABORTED lifecycle without INTENT; F02 (pid,starttime) key consistency; F03 pairwise known-field and same-gate cross-node attribution conflicts; F04 aggregate malformed fixture-id fail-closed. Add minimal **unexecuted** test source. Keep 18 V0.1 expected verdicts and formal Oracle `BLOCKED/NOT_READY`, do not implement a real native B0 adapter, do not modify frozen Bench/Parcae/G0/G1/R3. **No Python/interpreter/import/compile/pytest/test/fixture generation/process/GPU/REAL whatsoever.** Commit/push, write checkpoint FIX2-01…FIX2-08 with actual Git SHA/status and tests NOT TESTED, and STOP for independent ChatGPT static review.
