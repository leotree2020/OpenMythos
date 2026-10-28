# F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-001 — source correction checkpoint (2026-10-28)

**Status: SOURCE CORRECTION PREPARED — STATIC REVIEW PENDING. J1 CPU NOT TESTED (syntax, imports, handlers, tests all unverified). 18 S/O FIXTURES NOT MATERIALIZED. G2 CRITERIA NOT FROZEN. FORMAL J1 ACCEPTANCE: BLOCKED / NOT_READY (by construction). G2 REAL BLOCKED / NOT AUTHORIZED. Grok: DEFERRED / NOT PERFORMED (not a PASS). O-1…O-15 OWNER UNDECIDED.**
Scope: J1-IMPL-F01 … F06 of the independent static review (`gate_g2/G2_J1_IMPL_SOURCE_INDEPENDENT_STATIC_REVIEW_001.md`). Source-only; **no Python of any kind was invoked in this task** (no interpreter start, empty or otherwise; no import, py_compile, pytest, unittest, AST script), no process, no fork/wait/signal/janitor, no GPU, no fixture materialisation, no merge.

## Git

| Item | Value |
|---|---|
| Handoff branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-fix-handoff-20261028`, remote HEAD verified by `git ls-remote` + `git fetch` + `FETCH_HEAD` = **`692e551126c5171b13565f2ece30bf39d6ce8352`** (as announced) |
| Original implementation HEAD (not edited) | `a1678a5a31ae49ac1aca33cdcfd625efe2108e68` (code commit `f9151a9c6156ada24f6f4f77270eb004a713bf0a`; diff of the handoff branch against it is documents only) |
| Correction branch | `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028`, created from the handoff HEAD |
| Working tree at start | clean (0 porcelain lines) |
| Correction commit / final HEAD | see "Git SHA addendum" (separate documentation commit, avoids self-reference) |
| Read order followed | SESSION_START_PROTOCOL; fix-handoff checkpoint; the correction handoff; the independent static review; then the existing J1 sources; the V0.1 spec and frozen Bench (`registry.py` lifecycle/check_order, `observer.py`) were read earlier in this session and are unchanged at the pinned blobs |

## Files changed (only these)

`a_predicate_003/gate_g2/j1/`: `schema.py` (edited), `judge.py` (edited), `oracle.py` (rewritten), `README.md` (edited), `tests/test_j1_static_and_unit.py` (rewritten, unexecuted); `codec.py` and `__init__.py` unchanged. New: this checkpoint. Navigation appends: `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. Nothing else: `bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, `a_predicate_003/tests/`, R3, Parcae, the model, earlier G2 documents, and the 18 predeclared expected verdicts are untouched. Dependencies: Python standard library only (`re`, `dataclasses`, `hashlib`, `json`, `unicodedata` in the judge side; `re` in the oracle); no new package.

## FIX-01 … FIX-08 (static source review only; a static PASS is not a functional PASS)

Common environment: read-only source inspection, text editing and Git metadata only. Common input: the review's minimal counterexamples. Common "actual": source edits as listed; nothing executed.

| ID | Purpose / expected | Actual source change | Status |
|---|---|---|---|
| FIX-01 | New branch from the verified handoff HEAD; only `j1/`, one checkpoint and navigation changed | Branch created from `692e5511…`; diff scope verified after commit (addendum) | **PASS** (static / Git) |
| FIX-02 | F01 + F02: no INPUT_INVALID or broken input may yield a formal acceptance PASS; no forged or shrunk 18-case PASS | `judge._result` now separates the instrument channel: invalid input -> `input_valid=False`, `result_kind=INPUT_INVALID`, `subject_verdict=None` (previously a BLOCKED verdict). `oracle.grade_case`: `_output_problems` makes invalid input, any diagnostic, an `INPUT_INVALID` basis code, an empty basis list or a malformed shape a broken instrument (inline check BLOCKED); `validate_private_expectation` pins `(fixture_id, canonical_card, assertion_id, expected_subject_verdict)` to `SPEC_V0_1_INVENTORY` (altered F01-A FAIL->PASS, wrong card, unknown id all rejected); the formal `test_acceptance_verdict` is unconditionally BLOCKED / NOT_READY and the PASS-like value is a separately named, non-formal `inline_check_verdict`; `aggregate(case_results)` lost its `expected_ids` parameter, ignores caller-supplied grade rows as evidence and is unconditionally BLOCKED / NOT_READY (`FORMAL_ACCEPTANCE_READY = False`, `verify_fixture_attestation` accepts nothing); the 18 expected verdicts are unchanged. | **PASS** (static); functional **NOT TESTED** |
| FIX-03 | F03: ATTRIBUTION PASS/FAIL only with an explicit, trusted, matching gate/ticket association; missing -> BLOCKED | `judge._attribution`: requires a non-empty `gate_token` on the REGISTERED record **and** on every trusted witness, identical across all of them; absent -> BLOCKED `GATE_ASSOCIATION_UNVERIFIED`, contradictory -> BLOCKED `GATE_ASSOCIATION_CONFLICT` (no convenient choice); an unreadable witness blocks instead of being dropped; untrusted claims never supply the association; the assertion stays retrospective (code `RETROSPECTIVE_AGREEMENT_NOT_PREVENT_PROOF`, no PRE_RELEASE requirement added); no native B0 witness invented, native-shaped records (no gate token) stay BLOCKED | **PASS** (static); functional **NOT TESTED** |
| FIX-04 | F04: UNIQUE_REGISTRY PASS only after the restated frozen lifecycle rules; duplicate FAIL preserved | `judge._ledger_prerequisite_problems` extended by value from `bench/registry.py::lifecycle_issues / check_order`: RUN_START needs non-empty string `run_id` and non-bool integer `observer_pid`; RUN_END single, last, same `run_id`, boolean `cleanup_confirmed`, confirmed RUN_END only with DEAD for all non-janitor nodes; creator (other than `O`) registered before a child's INTENT; existing duplicate / after-DEAD / ordering / contiguity checks kept. PASS is claimed only for the **finite supplied validated set** (`ORIGINAL_LOG_COMPLETENESS_NOT_ASSERTED`, new accepted-claim text). Positive duplicate FAIL across distinct nodes is evaluated first and survives other incompleteness. | **PASS** (static); functional **NOT TESTED** |
| FIX-05 | F05 + F06: trust stays an explicitly hypothetical harness contract; no native adapter | `schema`: constants `TRUST_BASIS = HYPOTHETICAL_HARNESS_DECLARED_UNAUTHENTICATED`, `INPUT_DOMAIN = HAND_AUTHORED_SYNTHETIC_B0_SHAPED_ONLY`, `NATIVE_B0_ADAPTER_STATUS = NOT_IMPLEMENTED_OPEN_QUESTION`; **every** role (B0-shaped ledger and subject log included) must be declared `synthetic_assumption=True`; B0 tier renamed `SYNTHETIC_B0_SHAPED_TRANSCRIPT`; `validate_trust_model` docstring states it cannot authenticate the map; the three labels are emitted in every judge result; README/docstrings state that direct compatibility with native `bench/registry.py` records (float `mono`/`wall`, extra keys) is NOT SUPPORTED and an adapter is an open question. No adapter, no float dropping, no fake signature/key mechanism. | **PASS** (static); functional **NOT TESTED** |
| FIX-06 | Negative-test source for F01–F06 (minimal counterexamples), unexecuted | `tests/test_j1_static_and_unit.py` rewritten: `TestF01…TestF06` plus static contracts, discriminative handlers, SMOKE_ONLY, firewall and metamorphic skeletons; includes the reviewer's counterexamples (forbidden key in a J1-F03-A-style BLOCKED case; altered F01-A expectation; fabricated 18x PASS rows; shrunk scope via `expected_ids` raising TypeError; gate-token missing / mismatched; RUN_START without run_id / observer_pid; orphan creator; wrong-run RUN_END; non-OK read status; native-like float record). Positive-case helpers now build valid RUN_START and gate tokens. All inline; no fixture S/O data, hash or id-to-verdict table for the judge. | **PASS** (source written); **NOT TESTED / NOT RUN** |
| FIX-07 | Historic F07 retained; no prohibited interpreter/test/process invocation in this correction | F07 stays on record: first task `SRC-07 strict procedural compliance FAIL (self-reported)` with Git file scope PASS; it is not rewritten. In this task the only commands were Git, `cat`/`head`/`ls`/`grep`/`sed` reads, and the editor tools; no `python3`, no import, compile, pytest or unittest, no fork/exec/signal/janitor/GPU. | **PASS** (self-reported; cannot be proven by anything but this record and the command history) |
| FIX-08 | Checkpoint complete | This document + Git addendum | **PASS** (document) |

## Tests (all NOT TESTED / NOT RUN)

`TestStaticContracts` (7), `TestF01InvalidInputIsNeverAcceptance` (5), `TestF02PinnedExpectationsAndNoForgedAggregate` (7), `TestDiscriminativeHandlers` (3), `TestF03AttributionNeedsExplicitGateAssociation` (8), `TestF04UniqueRegistryLifecycle` (11), `TestF05TrustIsHypotheticalAndUnauthenticated` (6), `TestF06SyntheticOnlyNoNativeAdapter` (3), `TestSmokeOnlyHaveNoPassPath` (2), `TestInputFirewall` (4), `TestMetamorphicSkeletons` (4) and one skipped placeholder for the 18 fixtures. The counts are source-level, not results. Python syntax, imports and every behaviour above were desk-checked by reading only; an error is possible and would surface only in a separately authorised CPU stage.

## Unresolved issues (nothing decided silently)

* **Formal acceptance is intentionally unreachable**: it needs sealed, materialised Lane S / Lane O fixture bytes, an independent attestation verifier, a reviewed CPU guard / runner, frozen criteria and an authenticated trust-map origin (OQ-12). None exists.
* **OQ-11** the gate/ticket association is a `gate_token` on the synthetic `REGISTERED` record and the witness; whether it should be a separate trusted binding record is undecided; native B0 supplies none.
* **OQ-1…OQ-10** from the first implementation checkpoint remain (T selection for `ZOMBIE_AT_T`, `LOG_MATCHES_SEAL` observable shape and the added role `SUBJECT_LOG_READBACK`, closed per-kind `raw_fields` schema, `monotonic_order` semantics, identity equality, trust-map format, SMOKE_ONLY assertions without any PASS condition, ...). The lifecycle rules in FIX-04 are restated by value from the frozen registry and have not been mechanically compared with it.
* The first-pass handler and the schema were not re-audited line by line against the 18 V0.1 case descriptions beyond the desk checks; a later independent review should do so.
* G2 design O-1…O-15 remain OWNER UNDECIDED; nothing here advances G2 REAL.

## Only next instruction

Return the branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028`, its final HEAD (addendum), the diff against `692e5511…` and this checkpoint to **ChatGPT** for an independent static review. Without a new owner authorization: no fixture materialisation, no test or Python execution, no criteria freeze, no merge, no G2 REAL, no Grok claim. **Stop here.**

## Git SHA addendum (separate documentation commit)

* Correction commit (source + tests + README + checkpoint + navigation): `544ed5c2119004a0dbc0319466d45137af2bb9ce`
* Baseline (handoff HEAD): `692e551126c5171b13565f2ece30bf39d6ce8352`; original implementation HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68` (untouched).
* Diff `692e551..544ed5c2119004a0dbc0319466d45137af2bb9ce`: 8 files, 620 insertions, 199 deletions; 0 paths outside `gate_g2/j1/` and `docs/`; 0 paths in bench / gate_g0 / gate_g1 / prereg / evidence / tools / a_predicate_003/tests / Parcae / R3; `codec.py` unchanged.
* This addendum is one further documentation-only commit; the final branch HEAD is the remote HEAD of `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix-20261028` and must not be confused with the correction or baseline SHA.
* Working tree after commit: clean (ignored local G0/G1 authorization files untouched).
