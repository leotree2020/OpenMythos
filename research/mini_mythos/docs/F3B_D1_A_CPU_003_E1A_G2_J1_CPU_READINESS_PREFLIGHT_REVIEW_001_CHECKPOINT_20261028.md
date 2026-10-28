# OpenMythos — J1 CPU Readiness Preflight DRAFT 001 source-grounded review checkpoint

**Date:** 2026-10-28 · **Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-READINESS-PREFLIGHT-REVIEW-001`  
**Review type:** documentation/source comparison only, **zero executed tests or fixture bytes**.

## CURRENT STAGE (must read first)

**`PREFLIGHT DRAFT 001 DOCUMENT REVIEW: PASS (SCOPED INVENTORY / READINESS MAPPING ONLY)`.** The document has the right *preparatory* boundaries, but it is neither an owner-approved, frozen criteria set nor an executable CPU test plan. Three substantive prerequisites remain before criteria freeze: **`J1-PF-R01` (HIGH)** explicit instrument-vs-SUT error-origin test-grade taxonomy; **`J1-PF-R02` (MEDIUM)** full per-fixture S/O pairing and exact field/byte contract; **`J1-PF-R03` (MEDIUM)** independently controlled source/truth custody and negative attestation cases. `J1-PF-R04` is a low-priority reminder of domain/permission separation with no defect found.

**`CPU_FORMAL_ACCEPTANCE_READINESS=BLOCKED/NOT_READY`.** No J1 Python tests or source imports, no official synthetic S/O files, no independent truth material, no actual digests/manifests, no CPU guard/runner or attestation verifier. Current `oracle.py` formal acceptance remains unconditionally `BLOCKED/NOT_READY`. **`G2 REAL BLOCKED`; `Grok DEFERRED/NOT PERFORMED (NOT PASS)`; `O-1…O-15 OWNER UNDECIDED`; `OQ-13 UNDECIDED`.**

**Single next instruction:** separately authorized **document-only PF-02/PF-06 acceptance criteria addendum**: define independent pre-run Lane S VALID vs malformed/unverifiable input, case-grade FAIL versus BLOCKED, observed guard violation versus absent guard, and a per-case S/O manifest metadata contract. Do **not** implement, freeze, materialize fixtures, generate hashes, run CPU/Python/REAL or merge. Publish the addendum and a new checkpoint for review; code stages remain delegated to Claude Code under separate owner approval.

## Verified source and Git provenance

- **Reviewed preflight authoring branch:** `d1-r3-a-cpu-003-e1a-g2-j1-cpu-readiness-preflight-doc-20261028`, fetched remote HEAD **`a546ca92c2e69edb46929599de398e174c0683ea`** before independent review branch creation.
- **Preflight document:** `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_20261028.md`, independently fetched Git Blob `2d913119df54b301e6012910245d03deec065d4e`.
- **Preflight source baseline:** latest Correction 003 independent source-static reviewer HEAD `f51f77842c1eed88c2f7f9771b712cd969604321`. Original correction-003 source code HEAD `38e8a9141ebd738a34628acc928adb28cd8c54cf`.
- **V0.1 fixture design source:** `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`, blob `9574f90687b632f35c419a14963437c49dd35f58`.
- **Actual J1 code reviewed by read-only source:** `j1/oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`, `schema.py=551c4a01ed37f73c809776e123f98f6d055ac998`, `judge.py=8aef00cb1b66ee107c91086cd537c759858940cd`. Frozen `bench/observer.py=635e73b34203219a3687f86332d0e82362b89670`, `registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d` remain source-only.
- **Review-only Git branch:** `d1-r3-a-cpu-003-e1a-g2-j1-cpu-readiness-preflight-review-20261028`, created exactly from verified preflight-doc HEAD `a546ca92c2e69edb46929599de398e174c0683ea`, not from the older source code head.
- **New review:** `a_predicate_003/gate_g2/G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_INDEPENDENT_REVIEW_20261028.md`, initial commit `81a9eb7ba9b7dc57f9ccc843bf1bf94b0b1f8858`. This checkpoint and navigation changes follow; pin final SHA and Git diff after all writes.
- **Execution environment:** GitHub connector remote source retrieval/Markdown changes, **NOT** local clone, Python interpreter or CPU test. Local Git working tree NOT TESTED. No new dependency or experimental resource used.

## Research-management record — no experiment executed

| Element | Expected | Actual | Status |
|---|---|---|---|
| Objective | Independent source-grounded review of documented J1 CPU readiness blockers, inventory, trust and no-execution scope | Review covers V0.1 18-case matrix, current Oracle, CODEC/schema/Bench source distinctions and PF-00…PF-REAL | **PASS (DOC REVIEW SCOPE)** |
| Environment | No Python/tests/process/GPU, read-only frozen code, Markdown-only audit branch | GitHub source reads + independent review/checkpoint docs | **PASS (DOCUMENT-ONLY WORKFLOW)** |
| Inputs | Verified preflight doc/checkpoint/branch, V0.1 draft, current J1 code/frozen Bench | Pinned SHAs and source-limited claims recorded above | **PASS (PROVENANCE)** |
| Expected verdict mapping | Exactly 18 proposed cases, 5 subject PASS / 5 FAIL / 8 BLOCKED, five discriminative and four SMOKE_ONLY | All match V0.1 and `oracle.SPEC_V0_1_INVENTORY`; none has runnable bytes | **PASS (DOC TRACEABILITY); TEST NOT TESTED** |
| Scientific acceptance | Exact proof of independently held truth, canonical data, fail/block grade taxonomy and guard | R01/R02/R03 are OPEN; no S/O or guard exists; formal Oracle always BLOCKED | **BLOCKED / NOT_READY** |
| Requested CPU evidence | Only after owner authorizes guarded execution | 0/18 run, no outputs/hashes, no execution commands | **NOT TESTED / NOT AUTHORIZED** |
| G2 REAL | Independent lawful reaper/crash/orphan/zero-signal containment | Not tested or authorized; unchanged | **BLOCKED** |
| Grok second review | Independent actual reviewed report | No report for this stage | **DEFERRED / NOT PERFORMED** |

## Outstanding review findings, acceptance boundaries and dependencies

| Finding | Severity | Required action | Current |
|---|---|---|---|
| `J1-PF-R01` | HIGH | Independent fixture validity vs J1-invalid response vs missing guard vs observed safety breach: predeclared `FAIL/BLOCKED` taxonomy. Actual V0.1 §6 says wrong output or confirmed breach ⇒ FAIL, absent seal/oracle ⇒ BLOCKED. | **OPEN BEFORE PF-02/PF-06/PF-08 FREEZE** |
| `J1-PF-R02` | MEDIUM | Versioned per-case S/O field/handle/role/ordinal/canonical codec and private digest join; recognize synthetic `SUBJECT_LOG_READBACK` and `FORKED.raw_fields.pid`. | **OPEN, PF-02 BLOCKED** |
| `J1-PF-R03` | MEDIUM | Independent truth author, manifest custodian, guard/runner execution owner, verifier and tamper controls, with actual sealed S/O only after separate permission. | **OPEN, PF-03/PF-04/PF-05/PF-06 BLOCKED** |
| `J1-PF-R04` | LOW | Distinguish launcher from no-child-payload process ban; preserve subject/PF-REAL split. | **SOURCE DOCUMENT ACCURATE / NO CHANGE** |

**OQ-13** fork PID vs REGISTERED PID equality is NOT a frozen native rule; no silent code change or new expected verdict. **OQ-11** source binding authenticated origin missing; **OQ-12** formal verifier/attestation absent; other OQ-1…OQ-10 documented; owner O-1…O-15 unchanged. Four SMOKE_ONLY outcomes cannot prove discrimination, and G2 REAL remains separate.

## Readiness gates PF-00…PF-09 and PF-REAL

| Gate | Status | Evidence |
|---|---|---|
| PF-00 | **PASS (SOURCE PROVENANCE ONLY)** | J1 code and frozen reference Git SHAs verified |
| PF-01 | **PASS (DOCUMENT INVENTORY ONLY)** | V0.1 18 IDs match private Oracle tuple map, 5/5/8 |
| PF-02 | **BLOCKED / NOT FROZEN** | Exact per-kind canonical S/O bytes and fail/block taxonomy unresolved |
| PF-03 | **BLOCKED / NOT MATERIALIZED** | No independent S/O bytes/sealed truth |
| PF-04 | **BLOCKED** | No authenticated trust origin or genuinely held seal |
| PF-05 | **BLOCKED / NOT IMPLEMENTED** | No reviewed guard/runner or environment proof |
| PF-06 | **BLOCKED / NOT IMPLEMENTED** | Formal `verify_fixture_attestation` intentionally returns False |
| PF-07 | **NOT TESTED / NOT AUTHORIZED** | Python/CPU syntax, unit, metamorphic and regression tests not run |
| PF-08 | **BLOCKED / NOT AUTHORIZED** | No approved freeze and execution permission |
| PF-09 | **NOT TESTED / NOT AUTHORIZED** | No official 18-case CPU run |
| PF-REAL | **BLOCKED / OUT OF SCOPE** | Native G2 ownership/crash/reap/cleanup safety not proven |

**Current CPU readiness: BLOCKED, NOT READY.** Exactly zero genuine J1 formal CPU case outcomes exist. Source-static correctness of the F05 correction remains limited, not a model or REAL claim.

## Git stage closeout and one next instruction

- **Review branch changed-file scope independently VERIFIED at pre-addendum HEAD `6c1d8c12c392b8ac1886e5a3c741ee11eddd3027` versus preflight authoring SHA `a546ca92c2e69edb46929599de398e174c0683ea`: exactly 5 documentation commits, 4 Markdown files, +178/-0 lines; NO J1 implementation, Bench, Parcae, G0/G1/R3, test code, spec V0.1, preflight source draft or evidence changed.** This verification addendum adds a sixth checkpoint-only commit; fetch actual final remote SHA after it.
- **NEXT ONLY:** after explicit authorization, prepare one doc-only PF-02/PF-06 criteria addendum describing evidence-origin grade taxonomy and versioned 18-case S/O pairing metadata. Preserve V0.1 expected values, current `FORMAL_ACCEPTANCE_READY=False`, SMOKE_ONLY limits, current G2 REAL BLOCKED and Grok DEFERRED. Submit addendum for independent review and checkpoint. Future code remains Claude Code's separate authorized responsibility.

## Verified remote readback / Git closeout addendum

- GitHub readback at review pre-addendum HEAD `6c1d8c12c392b8ac1886e5a3c741ee11eddd3027`, compared to verified authored preflight HEAD `a546ca92c2e69edb46929599de398e174c0683ea`, confirms **5 commits, 4 Markdown paths, +178/-0**. Exact paths: `a_predicate_003/gate_g2/G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_INDEPENDENT_REVIEW_20261028.md`, this checkpoint, `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`.
- Updated independent review report Git Blob `b41508168100b9c1b1710fbc66c0ef54917da90f`; checkpoint pre-addendum Blob `7b157d90f2486e8f90a5d12e2e4a82752a790e92`. The reviewed preflight input checkpoint's **actual final Blob** is `d72be8951bf33261300a6988cc3c3f8bb3abb478`, distinct from its historical pre-addendum Blob printed inside that older document.
- **Git scope PASS for docs-only independent review.** There are zero code/fixture/generator/runner/CPU/GPU/REAL experimental changes in this review. The preflight's 18 IDs and V0.1 proposed 5/5/8 expected outcomes are **document expectations, NOT TESTED**.
- Reviewer disposition: `PREFLIGHT DOCUMENT PASS (SCOPED)` with explicit `J1-PF-R01/R02/R03` **required before freeze** and `CPU_FORMAL_ACCEPTANCE_READINESS=BLOCKED/NOT_READY`. Grok `DEFERRED`; OQ-13, owner O-1…O-15 still unresolved. No automatic code stage.
- The final reviewer HEAD **must be fetched after this single documentation append**; do not quote the pre-addendum SHA as the actual reviewer branch final commit.
