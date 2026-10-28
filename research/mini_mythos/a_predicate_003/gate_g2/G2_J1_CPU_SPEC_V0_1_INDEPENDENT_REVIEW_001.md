# G2 J1 CPU-only SPEC V0.1 — independent source/design review 001

**Date:** 2026-10-28  
**Author / reviewer:** ChatGPT  
**Reviewed remote commit:** `07ec81519684e7cc6b0477f086787c4dc32f4520` on `d1-r3-a-cpu-003-e1a-g2-j1-spec-v01-doc-20261028`  
**Reviewed draft:** `G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`, Git Blob `9574f90687b632f35c419a14963437c49dd35f58`  
**Starting checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_V0_1_REVISION_CHECKPOINT_20261028.md`, Git Blob `49cb66e4ec111d8a65723b0366315196d7493f7a`  
**Pinned Bench source blobs:** `observer.py:635e73b34203219a3687f86332d0e82362b89670`; `registry.py:3f2179e132371dd323f865be8a4d41fa5e58786d`; `node.py:5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`; `gate.py:7772c913828ea2184e6acf04cf5628c075dd5a57`; `common.py:9b6532bcb42c8724115b2bca78e220a8c315632f`.

## Review verdict and authority

**`G2 J1 SPEC V0.1 DOCUMENT REVIEW: PASS — SCOPED FOR CLAUDE CODE IMPLEMENTATION-ONLY HANDOFF PREPARATION`.** This is a one-review, evidence-limited document assessment: it says V0.1 is sufficiently precise to **give a coding-only handoff**, not that full G2 pre-registration is frozen, not that code exists, and not that any CPU/REAL safety property has passed. **The owner explicitly instructed that actual code development be performed by Claude Code and authorized continuation through preparation of its instructions.** No Claude Code execution has occurred in this review.

**`G2 CRITERIA NOT FROZEN`; `G2 J1 CODE NOT TESTED`; `CPU NOT TESTED / NOT AUTHORIZED`; `REAL BLOCKED / NOT AUTHORIZED`.** Any later Claude Code task is separately limited to writing isolated code and fixture definitions and reporting static diff; it cannot execute tests, materialize run evidence, send signals, fork processes for experiments, modify Bench/Parcae or claim PASS. Its changes remain subject to ChatGPT independent diff review and later owner approvals before tests.

**Grok:** User reported usage limits and allowed ChatGPT-led progress without Grok for now. `GROK REVIEW = DEFERRED / NOT PERFORMED`; this is NOT an independent Grok PASS or dual-review claim. **O-1…O-15 owner choices remain UNDECIDED**; no reaper scheme, prevention mechanism or real-run policy has been frozen.

## Source-grounded assessment of earlier V0 findings

| Old issue | Source/design evidence | V0.1 disposition — document scope only |
|---|---|---|
| J1-V0-F01 HIGH: answer leakage via fixture metadata | V0.1 §2 `J1.evaluate(assertion_id,subject_observables,declared_trust_model)`, explicit whitelist and forbidden `fixture_id`, `canonical_card`, expected verdicts/oracle truth | **PASS for design input separation**. Implementation must prove it does not pass hidden O-lane data, grade metadata or identifiable file paths into SUT, including exception/logging paths. |
| J1-V0-F02 HIGH: per-selector constant output | V0.1 §3–4: five assertions with positive contrast (ATTRIBUTION, UNIQUE_REGISTRY, ZOMBIE_AT_T, LOG_MATCHES_SEAL, WRITE_COMPLETE); four explicitly `SMOKE_ONLY` (PREVENT_PROOF, LAWFUL_REAP, EVIDENCE_USABLE, DELIVERY) | **PASS for honest coverage description**, not comprehensive J1 correctness. Hard-coded selector-to-status shortcuts remain forbidden; later metamorphic tests need separate authorization. |
| J1-V0-F03 MEDIUM: sidecar seal contradiction | V0.1 F05-A uses `LOG_MATCHES_SEAL=FAIL` on positive trusted mismatch; F05-B match `PASS`; distinct F05-C downstream `EVIDENCE_USABLE=BLOCKED`. Historical V0 remains unchanged | **PASS for predeclared assertion semantics**. Does not prove real independent seal trust. |
| J1-V0-F04 MEDIUM: hypothetical witness provenance | V0.1 §3 source tier table distinguishes B0_LEDGER, NODE_CLAIM_SIM, KERNEL_SNAPSHOT_SIM, G2_WITNESS_SIM, G2_WRAP_SIM, SEAL_MANIFEST_SIM | **PASS for hypothetical/synthetic source scope**; trust map must be harness-assigned, not blindly accepted from raw messages. |
| J1-V0-F05 MEDIUM: reproducible canonical input | V0.1 §5 proposes canonical JSON, no bool-as-int, seq integrity, intact tail, hash chain, independently held simulated manifest | **ADEQUATE TO BEGIN IMPLEMENTATION DESIGN ONLY**; exact bytes, trust custodian, materialized fixture hashes and stable schema await coding, independent review and later freeze. |
| J1-V0-F06 LOW: system safety overclaim | V0.1 §6 requires `measurement_target=J1_SYNTHETIC_DETECTOR`, `native_B0_safety_status=NOT_EVALUATED_BY_J1`; TEST PASS distinct from subject FAIL/BLOCKED | **PASS for scope labeling**. Not evidence of native-B0 safety. |

## Independently checked V0.1 inventory (no test run)

- **6 selected candidate arms**: D01-B0, D03c, D03d, D05, D07, D09 (9 other arms `DEFERRED_BY_SCOPE`).
- **18 unique proposed fixture IDs**: F01-A/B/C/D, F02-A/B, F03-A/B, F04-A/B/C, F05-A/B/C, F06-A/B/C/D (with prefix `J1-`).
- **Expected subject counts**: 5 PASS, 5 FAIL, 8 BLOCKED; **actual** executed fixtures 0/18, `NOT TESTED`.
- `ATTRIBUTION` = PASS/FAIL/BLOCKED; `UNIQUE_REGISTRY` = PASS/FAIL; `ZOMBIE_AT_T` = PASS/FAIL; `LOG_MATCHES_SEAL` = PASS/FAIL; `WRITE_COMPLETE` = PASS/FAIL/BLOCKED. `PREVENT_PROOF`, `LAWFUL_REAP`, `EVIDENCE_USABLE`, `DELIVERY` have only limited smoke coverage.
- Source `bench/observer.py:103–139,276–302` confirms B0's default immediate release and lack of gate recipient authentication; `bench/registry.py:9,30–80` constrains KINDS/read integrity; `bench/node.py:19–74` uses native ticket flow and does not establish lawful descendant wait. No source was changed.

## Required restrictions for Claude Code and unresolved assumptions

1. **No live process/real gate instrumentation.** J1 must be purely deterministic and given already-deserialized synthetic observables. No `bench` runtime import, no /proc, time, real signal, spawn, wait, GPU or network.
2. **No answer leakage.** J1 sees a narrowly validated assertion selector, raw observational S-lane records and a harness-bound source-trust mapping only. Fixture id, canonical card, truth, expected verdict, behavior label, paths and acceptance metadata live only in runner/oracle lane. A witness label by itself conveys no authority.
3. **Scientific non-overclaim.** A PASS on observed equality cannot certify unique fork; a passing write wrapper cannot prove reader identity; a valid sidecar hash does not prove kernel provenance. Only `J1_SYNTHETIC_DETECTOR` is eligible for any later CPU test.
4. **Coding-stage boundary:** Claude Code may propose and write isolated J1/oracle/fixture-definition **source files** and documentation on its own branch, but NO test execution, no automatic fixture generation/run artifacts, no creating an authorization file, no benchmark mutation and no change to historical expected statuses. Actual fixture bytes and SHA256 remain `NOT_MATERIALIZED` until a separately authorized fixture-materialization stage.
5. **Future code review must detect static shortcuts:** reject any fixture-id/expected-verdict dispatch, hardcoded per-assertion verdict without evidence, unvalidated source trust upgrade, handling `bool` as `int`, silent loss of corrupted lines, or invalid tail accepted as complete.
6. **Real G2 safety is still BLOCKED:** lawful reaper, creator crash/orphan, bounded zero-signal cleanup and host-level manual disposition remain unresolved O decisions. No J1 synthetic result advances REAL readiness.

## Reviewer acceptance matrix

| Check | Expected | Actual read-only evidence | Status |
|---|---|---|---|
| Git/source provenance | Pinned source and unchanged Bench | Verified remote branch SHA and source blobs; V0.1 Git Blob read | **PASS** |
| J1 input/oracle isolation design | No fixture labels/grades in SUT | V0.1 exact argument whitelist + Lane O private | **PASS (DOCUMENT)** |
| Expected fixture inventory | 18 IDs, no duplicate, clear contrast/smoke | 18 distinct IDs; 5/5/8 expected, 5 contrast + 4 smoke assertions | **PASS (DOCUMENT)** |
| Seal FAIL vs usable-evidence BLOCKED | Separate assertions | V0.1 F05-A/B/C versioned | **PASS (DOCUMENT)** |
| Hypothetical source trust | Never represent G2_WITNESS_SIM as B0 | V0.1 tier table and harness trust boundary explicit | **PASS (DOCUMENT)** |
| J1 implementation, exact fixture files/hashes | Separately approved code/materialization | None created | **NOT TESTED / NOT AUTHORIZED BY THIS REVIEW** |
| CPU run and REAL processes | Separate owner approval | No tests, no process experiments | **CPU NOT TESTED; REAL BLOCKED** |
| Grok review | Actual independent report | Deferred due limits, explicitly not substituted | **DEFERRED / NOT PASS** |

**Unique next action:** Prepare and hand off a **Claude Code implementation-only instruction** pinned to the *final reviewed documentation branch SHA*. Deliver it to the owner to use in Claude Code; do **not** invoke Claude Code or start tests in this review. Include separate approvals for code, fixture materialization, CPU execution, criteria freeze and REAL. Record the handoff and checkpoint and stop.
