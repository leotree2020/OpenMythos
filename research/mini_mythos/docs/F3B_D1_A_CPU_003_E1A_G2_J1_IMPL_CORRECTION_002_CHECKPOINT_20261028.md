# F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-002 — source correction checkpoint (2026-10-28)

**Status: SOURCE CORRECTION 002 PREPARED — STATIC REVIEW PENDING. J1 CPU NOT TESTED (syntax, imports, handlers and all tests unverified). 18 S/O FIXTURES NOT MATERIALIZED. G2 CRITERIA NOT FROZEN. FORMAL ORACLE ACCEPTANCE: BLOCKED / NOT_READY (by construction). G2 REAL BLOCKED / NOT AUTHORIZED. Grok: DEFERRED / NOT PERFORMED (not a PASS; no dual review exists). O-1…O-15 OWNER UNDECIDED.**
Scope: `J1-FIX-REVIEW-F01 … F04` of `gate_g2/G2_J1_IMPL_CORRECTION_INDEPENDENT_STATIC_REVIEW_001.md`. Source-only. **No Python of any kind was invoked in this task** (no interpreter start, empty or otherwise; no import, py_compile, pytest, unittest, AST script), no process, no fork/wait/signal/janitor, no GPU, no fixture S/O data or hashes, no merge. Static status below is source reading only; it is not functional test PASS.

## Git

| Item | Value |
|---|---|
| Handoff branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-fix2-handoff-20261028`, remote HEAD verified by `git ls-remote` + `git fetch` + `FETCH_HEAD` = **`a3f6eef883be123028377b3dd1d62ccd5a8e975c`** (as announced) |
| Prior correction HEAD (not edited) | `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` @ `045fa24a1b25f57d27d18dfc9b70b7c437c55898` (code commit `544ed5c2119004a0dbc0319466d45137af2bb9ce`) |
| Correction branch | `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028`, created from the handoff HEAD |
| Working tree at start | clean (0 porcelain lines) |
| Correction commit / final HEAD | see "Git SHA addendum" (separate documentation commit; avoids self-reference) |
| Read order followed | SESSION_START_PROTOCOL (via the handoff pointer), fix2 handoff checkpoint, the full correction-002 handoff, the independent static review, then the J1 sources as left by correction 001 |

## Files changed (only these)

`a_predicate_003/gate_g2/j1/`: `judge.py` (edited), `oracle.py` (edited), `README.md` (edited), `tests/test_j1_static_and_unit.py` (edited; unexecuted). `schema.py`, `codec.py`, `__init__.py` unchanged (`Identity.same_instance` deliberately not changed; it is still used by `ZOMBIE_AT_T`). New: this checkpoint. Navigation appends: `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. Nothing else: `bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, `a_predicate_003/tests/`, R3, Parcae, the model, earlier G2 documents, the 18 predeclared expected verdicts and the formal-acceptance fail-closed behaviour are untouched. Dependencies: Python standard library only (unchanged); no new package.

## FIX2-01 … FIX2-08 (static source review only)

Common environment: Git metadata, file reads and the editor tools. Common input: the reviewer's proposed counterexamples. Common "actual": source edits as listed; nothing executed.

| ID | Expected | Actual source change | Status |
|---|---|---|---|
| FIX2-01 | Exact remote SHA read; new isolated branch; permitted Git diff only | Branch created from `a3f6eef8…`; diff scope verified after commit (addendum) | **PASS** (Git / static) |
| FIX2-02 (F01) | A DEAD-only or ABORTED-only node without INTENT cannot give a `UNIQUE_REGISTRY` PASS; sound duplicate FAIL preserved | `judge._ledger_prerequisite_problems`: new `ORPHAN_RECORD` (any node with records but no INTENT, restated from frozen `registry.integrity_issues` / `fold`) and the stronger, explicitly synthetic-only `RECORD_BEFORE_INTENT` (a node record preceding its INTENT); a well-formed INTENT then DEAD is not an orphan; the duplicate-pair FAIL is still computed before the lifecycle checks. Frozen registry not modified. | **PASS** (static); functional **NOT TESTED** |
| FIX2-03 (F02) | Duplicate test uses exactly `(pid, starttime)`, not `same_instance` | `judge._pair` + `_unique_registry` compare `(pid, starttime)` of distinct nodes; optional `boot_id` / `pidns` cannot hide an equal pair (FAIL, even when the ids differ or one side omits them). Two different populated `boot_id` / `pidns` values among REGISTERED rows of a pair-distinct ledger are reported separately (`LEDGER_BOOT_OR_PIDNS_INCONSISTENT`) and give BLOCKED, never PASS. `Identity.same_instance` unchanged. | **PASS** (static); functional **NOT TESTED** |
| FIX2-04 (F03) | Pairwise known-field conflicts and same-gate cross-node witnesses cannot yield an ATTRIBUTION PASS | `judge._attribution`: considers every trusted witness for the node **plus every trusted witness carrying the node's gate token under another node**; same gate on another node (witness or another REGISTERED record) -> BLOCKED `GATE_SHARED_WITH_OTHER_NODE_UNRESOLVED`; all known identities (registered + every witness) compared **pairwise** with `_metadata_conflict` (populated `boot_id` / `pidns` that differ) -> BLOCKED `IDENTITY_METADATA_CONFLICT`; witnesses must agree on `(pid, starttime)` else `CONFLICTING_TRUSTED_WITNESSES`; agreement / mismatch decided on the `(pid, starttime)` pair; no "first witness" comparison, so the verdict cannot depend on record order. Still retrospective and synthetic-only; no pre-release or native-B0 claim; gate association remains an unauthenticated synthetic field (OQ-11). | **PASS** (static); functional **NOT TESTED** |
| FIX2-05 (F04) | Malformed / unhashable fixture ids give a structured BLOCKED / NOT_READY, never an exception | `oracle.aggregate`: each row and `fixture_id` is type-checked before any set / count (`not a dict` / `no fixture_id` / `malformed fixture_id` diagnostics); only plain `str` ids enter sets; unhashable verdict-field values are only compared with `==`; the result stays `run_acceptance_verdict=BLOCKED`, `acceptance_state=NOT_READY`, `formal_acceptance_ready=False`; no `expected_ids` parameter; forged 18 PASS rows stay BLOCKED. | **PASS** (static); functional **NOT TESTED** |
| FIX2-06 | Unexecuted negative / positive test source and README note; 18 fixtures / hashes not materialised | Test source adds `TestFixReviewF01OrphanRecord` (5), `TestFixReviewF02PairKey` (5), `TestFixReviewF03WitnessConflicts` (10), `TestFixReviewF04AggregateMalformedIds` (4): DEAD-only, ABORTED-only, DEAD-before-INTENT, INTENT-then-DEAD positive control, equal pair with different `boot_id` / `pidns` / one side omitted, different starttime with conflicting / consistent boot ids, reviewer counterexamples A (omitted + conflicting boot id), B (same gate on another node), C (conflicting pidns; conflicting pid / starttime), order-independence, clean PASS and single-witness FAIL controls, and `aggregate` with list / dict / bool / None / int / float / tuple ids, non-dict rows and non-list containers. README gains a "Correction 002" table. No fixture S/O JSON, hash or run evidence exists. | **PASS** (source written); **NOT TESTED / NOT RUN** |
| FIX2-07 | Zero Python in this correction; historic F07 retained; no frozen-file change | F07 stays on record (first task: `SRC-07 strict procedural compliance FAIL (self-reported)`, Git file scope PASS), not rewritten. In this task only Git, `cat`/`head`/`tail`/`ls`/`grep` reads and one `awk` text count of test methods and the editor tools were used; no interpreter, import, compile, pytest, unittest, fork/exec/signal/janitor or GPU. Git diff shows no frozen path touched. | **PASS** (self-reported; not independently provable) + Git PASS |
| FIX2-08 | Checkpoint complete | This document + Git addendum | **PASS** (document) |

## Tests (all NOT TESTED / NOT RUN)

Source-level counts (not results): static contracts 7; correction-001 classes F01 5, F02 7, F03 8, F04 11, F05 6, F06 3; discriminative 3; SMOKE_ONLY 2; firewall 4; metamorphic 4; correction-002 classes 5 + 5 + 10 + 4; one skipped placeholder for the 18 fixtures. Syntax, imports and behaviour were desk-checked by reading only; an error is possible and would surface only in a separately authorised CPU stage.

## Unresolved issues (nothing decided silently)

* Formal acceptance remains intentionally unreachable (OQ-12): sealed Lane S / Lane O bytes, an independent attestation verifier, a reviewed CPU guard / runner, frozen criteria and an authenticated trust-map origin do not exist.
* OQ-11: the gate / ticket association is still a synthetic field on the REGISTERED record and on the witness; native B0 supplies none; whether it should be a separate trusted binding record is undecided.
* New design choice made conservatively and flagged for review: a trusted witness (or another REGISTERED record) with the same gate token on a different node makes ATTRIBUTION BLOCKED, i.e. the gate-to-node mapping must be one-to-one; a populated `boot_id` / `pidns` conflict between the REGISTERED record and a witness is BLOCKED rather than FAIL; `LEDGER_BOOT_OR_PIDNS_INCONSISTENT` is an additional, synthetic-only BLOCKED condition. None changes a V0.1 expected verdict, but the reviewer should confirm none contradicts the 18-case descriptions (F01-A/C, F02-A/B).
* `RECORD_BEFORE_INTENT` is stronger than the frozen rules (which enforce INTENT order only for FORKED / REGISTERED via `check_order`); it is stated as a synthetic-only condition.
* OQ-1…OQ-10 of the first checkpoint remain; the restated lifecycle rules are not mechanically compared with the frozen registry; `ZOMBIE_AT_T` still uses `same_instance` (not in the findings).
* G2 design O-1…O-15 remain OWNER UNDECIDED; four assertions remain SMOKE_ONLY; nothing here advances G2 REAL.

## Only next instruction

Return branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028`, its final HEAD (addendum), the diff against `a3f6eef8…` and this checkpoint to **ChatGPT** for an independent static review. Without a new owner authorization: no fixture materialisation, no Python or test execution, no criteria freeze, no merge, no G2 REAL, no Grok claim. **Stop here.**
