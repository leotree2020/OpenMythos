# OpenMythos — J1 CPU Readiness Preflight DRAFT 001 independent document review

**Research task:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-READINESS-PREFLIGHT-REVIEW-001`  
**Date:** 2026-10-28 · **Reviewer:** ChatGPT · **Stage:** **DOCUMENT SOURCE REVIEW ONLY** — NO Python/import/compile/pytest, no CPU experiment, no source editing, no S/O fixture bytes/hashes, no process fork/wait/signals/GPU/G2 REAL, no criteria freeze.

**Reviewed branch:** `d1-r3-a-cpu-003-e1a-g2-j1-cpu-readiness-preflight-doc-20261028`, independently verified remote HEAD `a546ca92c2e69edb46929599de398e174c0683ea`.  
**Reviewed preflight:** `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_20261028.md`, Git Blob `2d913119df54b301e6012910245d03deec065d4e`.  
**Read-first checkpoint:** `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_CHECKPOINT_20261028.md`; Git Blob `d0760cdda252b679f21bfecafed7801b65822453` at pre-addendum as recorded in the checkpoint; exact current readback blob separately verified as part of this review.  
**V0.1 authority:** `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`, Git Blob `9574f90687b632f35c419a14963437c49dd35f58`; **draft, NOT FROZEN**.  
**Code under prospective test:** Correction 003 developer source `38e8a9141ebd738a34628acc928adb28cd8c54cf`, source-static review `f51f77842c1eed88c2f7f9771b712cd969604321`. `j1/oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`; `schema.py=551c4a01ed37f73c809776e123f98f6d055ac998`; `judge.py=8aef00cb1b66ee107c91086cd537c759858940cd`. Frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`, `bench/observer.py=635e73b34203219a3687f86332d0e82362b89670`, unchanged.

## 1. Independent verdict — separate document acceptance from runtime readiness

**`PREFLIGHT DRAFT 001 INDEPENDENT DOCUMENT REVIEW: PASS (SCOPED DESIGN/READINESS INVENTORY ONLY)`.** The draft faithfully inventories the exact proposed 18 cases, preserves the two-lane question/evidence distinction, refuses to promote the current hard-BLOCKED formal Oracle into test PASS, recognizes separately held truth and trust custody as missing, and explicitly blocks automatic CPU or REAL progression.

**`CPU_FORMAL_ACCEPTANCE_READINESS=BLOCKED / NOT_READY`** and **`PREFLIGHT FINAL CRITERIA NOT FROZEN`**. This is neither source-execution approval nor scientific acceptance of an installed harness; **document-only review PASS does not imply CPU readiness PASS**. The gaps below are **required before any criteria freeze/Claude Code runner implementation/run authorization**, but are faithfully reported as open by the current preflight; they do not constitute a failed CPU test.

**`ALL 18 OFFICIAL S/O CASES NOT MATERIALIZED / NOT TESTED`; `J1 SYNTAX/IMPORT/CPU FUNCTIONALITY NOT TESTED`; `FORMAL ORACLE = BLOCKED/NOT_READY`; `G2 REAL BLOCKED/NOT AUTHORIZED`; `Grok DEFERRED/NOT PERFORMED — NOT PASS`; `G2 O-1…O-15 OWNER UNDECIDED`.** Historic frozen G0/G1 evidence, upstream Parcae, R3, Bench and model sources remain outside scope.

## 2. Positive document review, with explicit proof ceiling

| Criterion | Source-grounded check | Document verdict |
|---|---|---|
| Inventory | V0.1 §4 and `oracle.SPEC_V0_1_INVENTORY` carry **the same 18 IDs**, with five proposed subject PASS, five FAIL and eight BLOCKED; six selected arms and nine deferred arms are not merged | **PASS (DOCUMENT, NO RUN)** |
| Discrimination | Five assertion names with contrasting subject outcomes; `PREVENT_PROOF,LAWFUL_REAP,EVIDENCE_USABLE,DELIVERY` remain explicitly **SMOKE_ONLY** (constant verdict is not proof of general correctness) | **PASS (DECLARED COVERAGE ONLY)** |
| S/O firewall | `evaluate(assertion_id,subject_observables,declared_trust_model)` receives no fixture ID, expectation, case path, result label or privately authored truth. The runner must privately join only after J1 output | **PASS (DESIGN), END-TO-END NOT TESTED** |
| Evidentiary source ceiling | Hypothetical `G2_WITNESS_SIM`, `G2_WRAP_SIM`, `KERNEL_SNAPSHOT_SIM`, `SEAL_MANIFEST_SIM`, and synthetic B0-shaped ledger not mistaken for kernel-authenticated native B0 evidence | **PASS (SCOPE STATEMENT)** |
| Formal acceptance non-bypass | Actual `oracle.py` `FORMAL_ACCEPTANCE_READY=False`, `verify_fixture_attestation` rejecting stub and formal `grade_case/aggregate=BLOCKED/NOT_READY` are acknowledged; inline PASS cannot be reused | **PASS (FAITHFUL CODE READ), NOT READY** |
| Input reproducibility | Canonical serialization, independent S/O hashes, complete readback, sidecar manifest custody proposed but **none materialized or pinned** | **PASS (GAP IDENTIFICATION); PF-02/03/04 BLOCKED** |
| CPU safety boundary | Guard, runner, exact command, isolated CPU environment, resource/import/process policy and observed guard evidence are future items; J1 synthetic PASS never authorizes G2 REAL | **PASS (NO-AUTOMATIC-EXECUTION RULE); PF-05/07/09 NOT READY** |
| OQ-13 | Equality of same-node `FORKED.pid` and `REGISTERED.pid` is **not required by frozen `registry.integrity_issues`**; a stronger contract is not silently introduced | **PASS (SCOPE HONESTY); OWNER DECISION UNDECIDED** |

**Document inventory trace:** `F01 A/B/C/D` = ATTRIBUTION FAIL/BLOCKED/PASS/BLOCKED; `F02 A/B` UNIQUE_REGISTRY FAIL/PASS; `F03 A/B` PREVENT_PROOF BLOCKED/BLOCKED; `F04 A/B/C` LAWFUL_REAP BLOCKED and ZOMBIE_AT_T PASS/FAIL; `F05 A/B/C` LOG_MATCHES_SEAL FAIL/PASS and EVIDENCE_USABLE BLOCKED; `F06 A/B/C/D` DELIVERY BLOCKED, WRITE_COMPLETE PASS/FAIL/BLOCKED. These are **future expected subject verdicts**, not measured scores.

## 3. Required pre-freeze resolution register — not new executable tests

### `J1-PF-R01` HIGH — Freeze a two-origin instrument-vs-SUT failure taxonomy

**Evidence:** V0.1 §6 explicitly says a *deterministic wrong output or confirmed guard breach* is test `FAIL`, while unreadable fixture, oracle or absent seal yields test `BLOCKED`; failure precedence `FAIL > BLOCKED > PASS`. Preflight DRAFT 001 §1/§5 says `INPUT_INVALID` is not ordinary subject BLOCKED and a guard absence/invalid input is `BLOCKED`; §4 says forbidden imports/process activity become `FAIL` or `BLOCKED` according to a **not-yet-frozen taxonomy**. Actual `oracle.py::_output_problems` classifies any J1-reported INPUT_INVALID as a broken instrument for nonformal checks.

**What is missing, before freezing:** a distinct **independent pre-run Lane S validity result** (obtained from separately reviewed trusted fixture/guard validation) vs **the J1 SUT's own refusal**. Two different situations must not be conflated:

| Controlled situation | Required proposed test acceptance, once independently established | Reason |
|---|---|---|
| S/O bytes malformed, unreadable, unsealed, or independently invalid **before invocation** | `BLOCKED` | Instrument cannot support a correctness judgment |
| Independently verified **valid Lane S**, but J1 emits `INPUT_INVALID` / no subject verdict | `FAIL` | Valid instrument; deterministic wrong/refused SUT output |
| Independently verified valid S/O and a J1 subject verdict mismatches private truth | `FAIL` | Measured deterministic disagreement |
| Guard or forbidden side effect **positively detected by reviewed instrument** | `FAIL` (or separately predeclared **safety FAIL** category, never PASS) | An observed violation is not missing evidence |
| Guard output absent, unverifiable or corrupt; trusted O unavailable | `BLOCKED` | Cannot establish execution confinement or verdict correctness |
| Correct J1 verdict and all independent S/O + guard/coverage preconditions verified | `PASS` (future only) | No missing required proof |

This matrix is a **reviewer proposal**, not an owner-frozen change to V0.1 or current hard-BLOCKED Oracle. A future Claude Code implementation must **not** merely re-label every `INPUT_INVALID` as FAIL either: when the fixture itself is invalid, it remains BLOCKED. **Required action before PF-02/PF-06/PF-08 freeze:** independently approve evidence for which origin is broken, precise machine-readable reason codes and precedence. Until then formal acceptance remains BLOCKED.

### `J1-PF-R02` MEDIUM — Make exact S-schema-to-O-case pairing and artifact-level identities explicit before fixture materialization

**Evidence:** Preflight §3 correctly gives 18 intended observation sketches but **does not** specify complete byte-level S and O records, per-kind `raw_fields`, trust-handle binding, time/ordinal semantics or immutable per-case sidecar chain. The J1 source introduces `SUBJECT_LOG_READBACK` and normalized `FORKED.raw_fields.pid` beyond the original prose roles; the preflight already records PF-02 `BLOCKED / NOT FROZEN`.

**Required prior to producing any official bytes:** an independently reviewed **18-row case manifest contract** (design, not current files), with an O-only case ID, a private S digest binding, declared S source handles without answer leaks, exact `schema.py` event fields and role ceilings, trust provenance tier and readback statuses, expected subject, critical evidence basis, and canonical JSON version. For `J1-F02-B`, require complete-for-scope native-inspired synthetic lifecycle including valid `RUN_START`, `FORKED.pid` if FORKED is present, creator prerequisite, contiguous ordinals/readback. For `J1-F05-A/B/C`, distinguish intact log with trusted contradictory seal (positive `LOG_MATCHES_SEAL=FAIL`) from missing/torn/untrusted log (undecidable `BLOCKED`), and keep downstream `EVIDENCE_USABLE` separate. For `J1-F04-B/C`, select exactly one snapshot T. For `J1-F06-B/C`, prove only simulated wrapper write status, not gate receipt. **No materialization, hashes, data generator or schema freeze occurs in this review.**

### `J1-PF-R03` MEDIUM — Independence is a provenance/control requirement, not a digest or Python-object convention

**Evidence:** Preflight §§4–6 correctly marks no real signer/custodian, no reviewed guard/runner and no accepted attestation. Formal `verify_fixture_attestation` is a stub returning False. The proposal for later materialization and a distinct custodian is appropriate **as a readiness inventory only**.

**Before formal readiness:** require named *roles* (not personal identifiers) for S author, O truth reviewer, trusted map/seal custodian, execution operator and independent acceptance verifier; predeclared offline publication/seal and post-run attested readback; immutability/version binding to full 18 manifest and code SHA; negative controls for tampered/truncated S, changed O truth, forged all-PASS rows and absent guard output. No role string, hash stored by the same subject writer, `dataclass`, or `synthetic_assumption=True` establishes independent authenticity. **Actual authority remains BLOCKED, not an implied PASS.**

### `J1-PF-R04` LOW — Preserve report domain separation and explicit permission sequencing

**Evidence:** Preflight §§1,6,8,9 correctly separates subject verdict, instrument, case grade, run grade and PF-REAL. It also places materialization, code generation and CPU run behind separate owner authorizations. The future CPU runner necessarily launches a Python interpreter, unlike prior **source-only no-Python** tasks; the preflight notes this distinction explicitly. **No changes required** for this item; future instruction must pin allowed process/command, count/time/memory budget, no native Bench/Parcae imports and negative control proof.

## 4. Independent PF-00…PF-09 and PF-REAL readiness states

| Gate | Independently grounded result | State **now** |
|---|---|---|
| PF-00 source checkpoint | Verified last reviewer SHA and pinned J1 code/frozen Bench blobs | **PASS (PROVENANCE ONLY)** |
| PF-01 exact prospective inventory | V0.1 and Oracle 18 IDs, 5/5/8, five discriminative/four smoke and nine deferred arms align | **PASS (DOCUMENT ONLY)** |
| PF-02 byte/field/failure taxonomy | Unfrozen schema/canonical contract; `J1-PF-R01/R02` not adjudicated | **BLOCKED / NOT FROZEN** |
| PF-03 independent Lane S/O bytes and private O truth | No fixture files, actual hashes or independently held truth artifacts | **BLOCKED / NOT MATERIALIZED** |
| PF-04 trust/sidecar seal custody | Hypothetical trust map; no independently authenticated source of trust/seal | **BLOCKED / NOT VERIFIED** |
| PF-05 runner/guard | No reviewed guard/runner source or real isolated environment proof | **BLOCKED / NOT IMPLEMENTED** |
| PF-06 independent formal acceptance | Oracle deliberately rejects attestations and formal PASS | **BLOCKED / NOT IMPLEMENTED** |
| PF-07 syntax and unit tests | Source test methods exist; imports, behavior, CPU and regressions not executed | **NOT TESTED / NOT AUTHORIZED** |
| PF-08 criteria freeze/run permissions | No approved PF-02/03/04/05/06; owner decisions, Grok state unresolved | **BLOCKED / NOT AUTHORIZED** |
| PF-09 actual 18-case run evidence | Zero official tests, fixture hashes and run outcomes | **NOT TESTED / NOT AUTHORIZED** |
| PF-REAL native G2 safety | Lawful reaper, crash/orphan, no-signal cleanup and containment independent blocker | **BLOCKED / OUT OF SCOPE** |

**Overall `CPU_FORMAL_ACCEPTANCE_READINESS=BLOCKED/NOT_READY`.** The review's document-level `PASS` cannot release any PF-02…PF-09 gate. Any future runnable CPU stage needs exact owner authorization and actual guard/runner evidence. Underlying Parcae P1 and Mythos architecture claims remain separate.

## 5. Exact stage limits and next instruction

- **This review executed no code**: not Python/pytest, import/compile, fixture authoring/materialization, sidecar hash, CPU experiment, subprocess, native Bench/Parcae, REAL signals, GPU, model or data retrieval. Read-only GitHub source and documentation commits only.
- Code changes remain delegated to **Claude Code only if later separately authorized**. Upstream Parcae and frozen Bench/G0/G1/R3 remain untouched; no accidental redesign of recursive Transformer architecture.
- Source-independent cross-review by Grok remains `DEFERRED / NOT PERFORMED`; no consensus PASS or arbitration experiment is asserted. Owner O-1…O-15 and OQ-13 remain undecided.

**Single next instruction:** prepare a **DOCUMENT-ONLY PF-02/PF-06 criteria addendum** that closes the *failure-origin taxonomy* from `J1-PF-R01` and records the *per-case S/O pairing metadata schema* from `J1-PF-R02` without generating fixture bytes/hashes or deciding OQ-13 silently. Submit the addendum for independent review and owner consideration; **do not freeze criteria or initiate Claude Code code implementation, fixture materialization, Python/CPU or G2 REAL automatically**.

**Document stage review accepted in scope; full J1 formal CPU testing remains NOT_READY.**
