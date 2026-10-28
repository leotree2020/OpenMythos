# E1-A G2 — J1 CPU-only SPEC V0 independent review 001 (2026-10-28)

**Result: CHANGES REQUIRED (document review only).** No G2 CPU/REAL test executed, no G2 criteria frozen or implementation authorized. Grok review `DEFERRED / NOT PERFORMED`, not PASS; owner permission to proceed without Grok applies **only to documents**. All O-1…O-15 owner decisions remain UNDECIDED.

**Reviewed remote commit:** `fb5bb8779b93fb9027964e43229f368c1750488e`. **Document:** `G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md`, blob `44cd58d1089ca8b394658acafe4f8477e371d2f0`. **Input checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_DRAFT_001_CHECKPOINT_20261028.md`, blob `810d8db1d3ba97c34bec1cb3fbf804638a19fee7`. **Frozen read-only source:** `bench/observer.py` blob `635e73b34203219a3687f86332d0e82362b89670`; `bench/registry.py` blob `3f2179e132371dd323f865be8a4d41fa5e58786d`; `node.py`, `gate.py`, `common.py` and `proto.py` likewise read-only.

## Verified document merits (not CPU PASS)

- Matrix contains **12 unique planned fixture IDs** (J1-F01-A/B through J1-F06-A/B), six families. Predeclared *expected subject verdicts* are 4 scoped PASS, 2 positive FAIL, 6 evidence BLOCKED. These are **not actual results**.
- Nine other arm-qualified historical scenarios are `DEFERRED_BY_SCOPE`, not PASS; only 6/15 scenario arms are planned.
- Bench `observer._register` checks PID/starttime and PPID, but not actual unique gate recipient; `release()` writes ledger RELEASED before os.write of R. Native `registry.KINDS` omits CREATED/EXIT/REAPED. A Z/DEAD/ECHILD state does not independently prove lawful wait. Specification correctly avoids claims of real B0 prevention, lawful reaping and delivery-recipient proof.
- J1 is intended as a **pure synthetic B0-evidence detector**, not a real B0/P1 process experiment, not a Parcae or Mythos model capability evaluation.

## Findings — source-grounded, not experimentally executed

### J1-V0-F01 HIGH — SUT input contract does not prohibit fixture-ID answer lookup

**Evidence:** V0 §2 lines 28–43 separates J1-visible Lane S and hidden Lane O, but the proposed fixture schema includes `fixture_id`, `canonical_card`, `assertion_id`, `fixture_version` without unambiguously specifying what metadata is passed to J1.

**Minimal unrun counterexample:** `J1.evaluate(subject)` looks up a supplied fixture ID and emits the twelve expected statuses. The acceptance oracle returns 12/12 PASS while J1 never examines observation records.

**Required:** Explicit interface `J1.evaluate(assertion_id, subject_observables, declared_trust_model)` (exact naming provisional). **No fixture_id, canonical_card, filename, expected/actual verdict, private oracle facts, behavior label, case answer or other grading metadata is allowed inside J1 input.** The runner privately joins results with Lane O outside J1. Validate forbidden keys before any call. Plan synthetic renaming/ID-remapping controls for a later, separately authorized fixture specification.

### J1-V0-F02 HIGH — Single-outcome assertions can be solved by constant-per-selector behavior

**Evidence:** V0 §4 lines 57–68: both `J1-A-PREVENT-PROOF` cases expect BLOCKED; `J1-A-LAWFUL-REAP` and `J1-A-ZOMBIE-AT-T` have one case each; delivery and write-complete likewise have different assertion IDs, with only one expected output each.

**Minimal unrun counterexample:** Return BLOCKED unconditionally for `PREVENT-PROOF` and `LAWFUL-REAP`; PASS unconditionally for `ZOMBIE-AT-T` and `WRITE-COMPLETE`. Those fixtures pass without evaluating evidence. This does not invalidate the other discriminating families, but it does invalidate a strong "all assertions discriminate" claim.

**Required:** Predeclare counter-fixtures or metamorphic mutations producing different expected outcomes for each feasible assertion, **or** label single-outcome assertions `SMOKE_ONLY / NOT YET DISCRIMINATIVE` and prohibit full-assertion correctness PASS. Do not invent a pre-release B0 witness merely to force a positive prevention case, and do not relabel P1 hypothetical data as native B0.

### J1-V0-F03 MEDIUM — Sidecar manifest mismatch: positive integrity violation vs unusable evidence

**Evidence:** V0 §1 `J1-A-SIDECAR-INTEGRITY` and §4 line 65 F05-A expect BLOCKED for a two-record chain conflicting with a separately *trusted* three-record seal, while §2 says positive protocol violation => FAIL and missing essential proof => BLOCKED.

**Consequence:** A trusted final seal contradicting observed file length/seq/head is a **positive integrity invariant violation**, suggesting `LOG_MATCHES_SEAL=FAIL`; the separate question `CAN_USE_LOG_AS_EVIDENCE=BLOCKED` is about whether a defective log supports later claims.

**Required:** Separate or explicitly define these properties, predeclare which assertion F05-A tests, and set its expected verdict consistently before materialization. Preserve historical V0 expected BLOCKED as a versioned prior proposal, never silently change old evidence.

### J1-V0-F04 MEDIUM — Hypothetical witness cannot be promoted to native-B0 evidence

**Evidence:** V0 §2 line 34 and §4 F01-A use `G2_WITNESS_SIM.gate_child_event` as decisive child-identity evidence; F06-B uses `G2_WRAP_SIM.R_WRITE_RESULT(bytes=1)`. Frozen `observer.py:103–139,276–302` neither authenticates such a gate-child witness nor records that wrapped write return.

**Counterexample:** An untrusted socket-holder can claim to be a genuine gate child; trusting that assertion merely because its source label says WITNESS would lead to unjustified FAIL/PASS.

**Required:** Source-permission/trust table for raw B0 ledger, node claims, synthetic kernel snapshot, independent hypothetical witness, hypothetical write wrapper, independent seal. Every fixture states whether its decisive source actually exists in B0 or is `SYNTHETIC_ASSUMPTION_ONLY`. Trust tier must be harness-declared **outside the subject's untrusted payload**. A synthetic trusted witness can test J1 logic, not authenticate the live B0 pipeline.

### J1-V0-F05 MEDIUM — Finite ledger/sidecar completeness and reproducible bytes are open

**Evidence:** V0 F02-B (§4 line 60) asserts only finite-record uniqueness, and F05-B (line 66) asserts sidecar readback/seal consistency. Exact canonical bytes, record validity, complete newline endings, hash values and independent seal custody are NOT_MATERIALIZED. This is correct for draft status, but prevents fixture freeze.

**Required:** Before freeze, specify deterministic JSON encoding, invalid int/bool cases, `RUN_START` and registry lifecycle prerequisites, clean-readback marker and torn-tail handling, exact sidecar genesis/prev digest, final seq/file length/head, and independently trusted seal provenance. A log truncated to a clean prefix may appear internally consistent unless its separately trusted head is checked. Do not invent hashes for absent fixture bytes.

### J1-V0-F06 LOW — Avoid incorrectly reporting detector TEST PASS as B0 SAFETY PASS

**Evidence:** §4 has conditional future CPU test PASS for F01-A even though its positive independent observation demonstrates an unsafe B0 identity attribution. The document mostly distinguishes these but a future schema should require `measurement_target=J1_SYNTHETIC_DETECTOR`, `native_B0_safety_status=NOT_PROVEN`, `assertion_id`, `subject_verdict`, `observed_behavior_label`, `test_acceptance_verdict` and `scope` in per-fixture and aggregate evidence.

**Required:** Never promote a successful detection of a frozen B0 weakness into a G2 system-level safety claim.

## Acceptance table and blockers

| Check | Expected | Actual review | Status |
|---|---|---|---|
| Git provenance and source grounding | Pinned source with unchanged Bench | V0 blob and frozen B0 inspected | **PASS** |
| Selected fixture inventory | Six groups, 12 IDs | 12 distinct proposed fixtures, no duplicate | **PASS (DOCUMENT INVENTORY ONLY)** |
| Truth isolation | No oracle answer via subject metadata | Exact J1 input whitelist absent | **CHANGES REQUIRED** |
| Nontrivial per-assertion discrimination | Evidence-sensitive decisions | Several assertions have constant expected answer | **CHANGES REQUIRED** |
| Integrity/verdict semantics | Positive mismatch vs unknown correctly separated | Sidecar mismatch semantics ambiguous | **CHANGES REQUIRED** |
| Source/witness trust | Hypothetical vs native sources explicit | Runtime witness provenance contract incomplete | **CHANGES REQUIRED** |
| Actual fixture data, hashes, J1 code, CPU run | Independently materialized and authorized | None | **NOT TESTED / NOT AUTHORIZED** |
| G2 REAL | Proven lawful reaping + exceptional containment | Not established | **BLOCKED / NOT AUTHORIZED** |
| Grok review | Actual independent review | Deferred due to usage limits | **DEFERRED / NOT PASS** |

**Final verdict: `G2 J1 CPU SPEC V0 DOCUMENT REVIEW CHANGES REQUIRED`.** The draft is useful and reviewable. These are specification-quality problems, not observed CPU failures or authorization to modify frozen Bench/Parcae.

**Only next instruction:** prepare a **V0.1 minimal DOC-ONLY revision** addressing F01–F06. Specifically close the Lane-S API against fixture metadata and oracle leakage; add evidence-sensitive contrasts or honestly mark SMOKE_ONLY; clarify log-integrity FAIL versus downstream evidentiary BLOCKED; label all hypothetical witnesses and source trust; and keep all actual fixture bytes/hashes NOT_MATERIALIZED. Return V0.1 for a new independent read-only audit. No criteria freeze, implementation, execution, signals, GPU or G2 REAL.
