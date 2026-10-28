# G2 V2 INDEPENDENT DESIGN REVIEW-001 checkpoint — 2026-10-28

## Latest outcome, scope and authority

**G2 V2 DESIGN: CHANGES REQUIRED.** The draft remains readable, source-grounded and improved from V1, but **is NOT accepted for criteria freeze or execution**. It cannot receive G2 design PASS solely because documentation was written.

**G2 REAL PRECONDITIONS: BLOCKED / G2 REAL NOT AUTHORIZED.** No G2 criteria frozen, no G2 implementation, no CPU suite, no real G2, no second G1, no authorized G3/BV/E1-A. No Parcae or model-architecture change.

**Grok G2 review: DEFERRED / NOT PERFORMED.** User permitted ChatGPT-led *documentation-only* progress due to Grok usage limits; there is no Grok PASS, no Grok disagreement report, no bilateral design PASS, and no standing implementation/test authorization.

## Git anchoring and artifact location

- Pinned source review baseline: `6c223ef2efa8830c1552d44e046b72063d87a637`, branch `d1-r3-a-cpu-003-e1a-g2-v2-design-20261028`. Latest remote branch SHA was verified equal to this at review start.
- V2 design review target: `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V2.md`, Git Blob `e58fe0e0881beebcef2f3d8b0510b7e4175da1da`.
- Immutable Bench source reference: `bench/` at the above source HEAD, matching earlier frozen code HEAD `450914367c247231c51be02e13775cb001e69c5d`.
- **Documentation-only review branch** `d1-r3-a-cpu-003-e1a-g2-v2-review-20261028`, created from the exact source SHA above. Review record: `a_predicate_003/gate_g2/G2_V2_INDEPENDENT_DESIGN_REVIEW_001.md`.
- Review-record creation commit: `e408954c0216f65d5fc028351c331b2682f68d46`. Final review branch HEAD will be verified *after* checkpoint and navigation updates; document commit SHA is NOT a test-run SHA.
- Historical G1 REAL execution SHA remains `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`; G1 REAL one-run and cross-review PASS, not repeated.

## Experimental accounting (no experiment executed)

| Field | Record |
|---|---|
| Objective | Independent read-only source/design audit of V2; propose O-1…O-15 owner-choice directions without silently adopting any; identify falsifiable gaps, bounded next document step. |
| Environment | Connected GitHub repository read-only for source verification and write access **only to separate review documentation**. No experimental Linux runtime, CPU test, GPU, subprocess or signal. |
| Inputs | Pinned V2 and its V1/V0 review provenance, G2 design checkpoint, frozen `bench/observer.py`, `node.py`, `gate.py`, `common.py`, `registry.py`, `proto.py`, G1 REAL closeout. |
| Expected | Traceable findings with source line ranges, minimum counterexamples, clear review PASS/CHANGES REQUIRED/BLOCKED, proposals separated from owner choices, documentation checkpoint. |
| Actual | Six source-grounded findings V2-F01…F06; recommendation matrix O-1…O-15; five CPU-only **fixture proposals (not run)**; review disposition `CHANGES REQUIRED`. |
| Source/provenance review | **PASS** (correct source ref and documented scope). |
| V2 review acceptance for freeze | **CHANGES REQUIRED**. |
| V2 REAL safe-to-authorize | **BLOCKED / NOT AUTHORIZED**; lawful reaping and safe abnormal containment remain open. |
| CPU / real execution | **NOT TESTED**. |
| Grok review | **DEFERRED / NOT PERFORMED**, never imitated. |

## Findings and unresolved problems

- **V2-F01 HIGH:** B0 frozen `_on_created` auto-releases; D01 mixes B0/P1 despite asking for PRE_RELEASE gate identity proof. Split D01-B0 detective only from D01-P1 held-release intervention; P1 is new code, no authorization.
- **V2-F02 HIGH:** creator-reported wait and same-thread instrumentation cannot prove kernel provenance without a scoped trust boundary. Reviewer prefers plan A for *first study* but owner choice O-1/O-3 remains undecided.
- **V2-F03 HIGH:** creator death, orphan, shared socket or anomalous wait can outlive bounded no-signal cleanup. Manual disposition cannot guarantee containment; must specify isolated environment and separate operational responsibility before REAL.
- **V2-F04 MEDIUM:** hash-chained sidecar doesn't authenticate events or detect a missing suffix without separately trusted final head; closed schema/durability unresolved.
- **V2-F05 MEDIUM:** B0 `ACCEPTED_UNSAFE` diagnostic label still needs separate `observed_behavior_label` distinct from subject PASS/FAIL/BLOCKED; freeze exact per-arm fixture expected results.
- **V2-F06 LOW:** user-owner decisions O-1…O-15 must remain explicitly `UNDECIDED`, never promoted from reviewer suggestions.
- Existing V1-R1…R5 conceptual corrections remain valid and are not undone.

## Dependencies, source integrity and Git

- No new packages, network data downloads, model weights, GPU or experiment runtime dependency. Only GitHub files are referenced.
- Intended Git diff from source HEAD: **add review record + this checkpoint; append-only PROJECT_MAP / SESSION_START_PROTOCOL navigation**. Verify after writes. No change to G2 V2 draft, old checkpoints, Bench, G0/G1, R3, prereg, Parcae, model, test, authorization or evidence files.
- Current user/local working-tree status cannot be verified through remote GitHub connection, and is **NOT TESTED**. Only GitHub remote file scope is verifiable.
- Review is an assessment, not an implementation or a new G2 experiment. A Grok report, when available, should be kept separate and source-backed, with disagreement unresolved until an authorized minimal CPU experiment if needed.

## Single next instruction

**Create V2.1 minimal documentation revision only**, scoped to V2-F01…F06: (1) separate B0 vs P1 D01; (2) define lawful reaper evidence tier and trust assumption; (3) explicit isolated execution environment, bounded timeout and external manual residue responsibility (not a G2 PASS); (4) sealed sidecar schema; (5) 14 fixture IDs with two-level verdict plus distinct behavior label; (6) owner-choice decision table with all O-1…O-15 set UNDECIDED. Then hand back for independent document-only source audit. **Do not implement, freeze G2 criteria, run CPU/process tests or enter REAL/G3/BV/E1-A without later explicit approval.**
