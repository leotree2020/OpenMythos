# F3B-D1-A-CPU-003 E1-A G2 J1 CPU SPEC DRAFT-001 checkpoint (2026-10-28)

## Read-first state and authority

**Stage:** `G2 J1 CPU-ONLY FIXTURE PREREG SPEC DRAFT V0 PREPARED — INDEPENDENT DOCUMENT REVIEW PENDING`. **G2 CRITERIA NOT FROZEN; G2 IMPLEMENTATION/CPU/REAL NOT AUTHORIZED; CPU TESTS NOT TESTED; REAL DESIGN SAFETY BLOCKED.** The fixture matrix contains conditional *expected* test results only. **No actual fixture JSON, executable code, CPU run, process fork, wait, signal, janitor, GPU, evidence run or authorization file** has been created or executed.

**Grok:** user reports tool usage limit; interim permission is **documentation continuation only**. `GROK G2 REVIEW = DEFERRED / NOT PERFORMED`, NOT PASS. ChatGPT scoped V2.1 design review PASS for **writing** a CPU-only specification is not CPU PASS or dual review. **Owner O-1…O-15 = UNDECIDED**; no standing permission to freeze or implement. G0 REAL and G1 REAL historical results remain PASS and unchanged. No implications for original Parcae model mathematical/gradient correctness or Mythos quality.

## Git provenance

- **Verified input branch:** `d1-r3-a-cpu-003-e1a-g2-v21-review-20261028` @ `672b20bc8091c42c31786c66b8ea28191584def7`; GitHub checked before work.
- **Checkpoint input:** `docs/F3B_D1_A_CPU_003_E1A_G2_V2_1_DESIGN_REVIEW_001_CHECKPOINT_20261028.md` (source pinned). Source review: `a_predicate_003/gate_g2/G2_V2_1_INDEPENDENT_DESIGN_REVIEW_001.md`.
- **Document-only output branch:** `d1-r3-a-cpu-003-e1a-g2-j1-cpu-spec-draft-20261028` created from exact SHA above.
- **Primary deliverable:** `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md`; initial content commit `c9fb8f4028b9ba2765f5e4c4df29aff426b94c9a`.
- **Frozen Bench source inspected (unchanged):** `observer.py` blob `635e73b34203219a3687f86332d0e82362b89670`, `node.py` `5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`, `gate.py` `7772c913828ea2184e6acf04cf5628c075dd5a57`, `registry.py` `3f2179e132371dd323f865be8a4d41fa5e58786d`, `common.py` `9b6532bcb42c8724115b2bca78e220a8c315632f`.
- **Historical G1 execution-time SHA:** `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d` — not related to this doc's Git SHAs.

## Acceptance-style record (documentation only)

| Field | Value |
|---|---|
| Purpose | Define a tightly scoped, falsifiable J1 synthetic judge pre-registration **specification**, detecting frozen B0 identity/ledger/exit evidence errors without executing B0 or new P1. |
| Environment | Connected GitHub source reads and document-only commits; no CPU or Linux experimental runtime, model weights, external data, GPU or new dependencies. |
| Inputs | Current V2.1 independent review/checkpoint, V2.1 delta, source-pinned Bench observer/node/gate/registry/common. |
| Expected document result | Six fixture families, complete 12 selected IDs with controlled synthetic observable input, separately withheld oracle truth, scoped assertion, conditional expected subject and CPU verdict, explicit deferred cards, no unauthorized claims. |
| Actual document result | `G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md` prepared and Git committed; 6 families / 12 exact fixture rows; four narrow PASS controls, two positive FAIL controls, six BLOCKED controls; all actual outcomes remain NOT TESTED. |
| Git source audit | PASS for read-only content and source relevance. |
| Document drafting | **PREPARED**, draft-existence check PASS; not yet independently accepted. |
| J1 fixture materialization/hashes | **NOT MATERIALIZED / NOT TESTED**. No invented SHA-256 for nonexistent input bytes. |
| G2 frozen criteria | **NOT FROZEN / NOT AUTHORIZED**. |
| G2 implementation & CPU actual tests | **NOT TESTED / NOT AUTHORIZED**. |
| G2 REAL | **BLOCKED / NOT AUTHORIZED**. |
| Git file diff | **PASS (pre-addendum)**: against frozen source `672b20bc8091c42c31786c66b8ea28191584def7`, current HEAD `9939f33f69bd2699c64c26f0e473ef442dd16a06` = **4 documentation commits**, exactly 4 Markdown files (2 added, 2 append-only map/SOP), 175 insertions / 0 deletions, **no Bench/Parcae/criteria/tests/runtime/evidence changes**. This checkpoint amendment adds one more doc-only commit; retrieve new remote HEAD. |

## Selected test-scope inventory and excluded targets

Exactly **12 proposed fixture IDs**:

`J1-F01-A`, `J1-F01-B` (same-parent wrong PID, source-positive vs unknown); `J1-F02-A`, `J1-F02-B` (duplicate vs finite-ledger unique identity); `J1-F03-A`, `J1-F03-B` (no pre-R witness, post-R READY cannot fix); `J1-F04-A`, `J1-F04-B` (Z/DEAD/ECHILD does not prove wait vs scoped Z-at-T); `J1-F05-A`, `J1-F05-B` (sealed missing suffix vs intact chain); `J1-F06-A`, `J1-F06-B` (RELEASED intent ≠ write vs scoped one-byte write result).

Selected **6 of 15 arm-qualified historical candidates**: `D01-B0,D03c,D03d,D05,D07,D09`. Remaining 9 `DEFERRED_BY_SCOPE`, **not PASS**: `D01-P1,D02,D03a,D03b,D03e,D04,D06,D08,D10`.

The independent truth **must never be passed to J1**; the future acceptance oracle alone sees expected verdicts and private synthetic facts. J1 may consume **source-qualified synthetic witness observations**, which are not proof that frozen B0 collects such witnesses in real execution. Fixture success is a test of J1's narrow synthetic classification, not B0 safety or REAL. `PASS` on the four positive controls means only finite-ledger internal uniqueness, observed Z-at-T, archive hash consistency under trusted seal, or write syscall success; none implies global descendant absence, legitimate reaping, sender authenticity or correct recipient.

## Dependencies, open issues and safety gates

- **No packages installed** and no tests run. Project owner and future implementation must separately approve exact fixture materialization, oracle API and prevention of answer leakage, source trust, schema bytes/hash format, no-process sentinel and future CPU test authorization.
- `O-1…O-15` remain **UNDECIDED**. Especially O-1 legitimate reaper, O-2 B0/P1 scope, O-3 accepted wait evidence, O-7 independent seal provenance, O-13 no-signal abnormal containment.
- A sealed hash chain shows **internal consistency**, not unforgeable kernel truth. Unless the independent seal's custodian and trust boundary are specified, even a synthetically valid chain cannot be promoted to a REAL evidentiary PASS.
- No creator death/orphan/undocumented fd-holder situation has a proven autonomous, zero-signal cleanup. G2 descendant REAL remains **BLOCKED** until separate external operational containment/owner response is approved.
- Frozen Parcae, Bench, G0/G1 criteria, R3 and Recursive Transformer architecture must not be modified opportunistically. This phase cannot claim model correctness, efficiency or reasoning benefit.
- Local working tree cleanliness is **NOT TESTED**; remote Git diff will be verified and recorded, and final remote HEAD must be retrieved at the end.

## Single next instruction

**Submit the pinned J1 CPU-only SPEC DRAFT V0 for an independent read-only source/design audit**, checking that six family categories, 12 exact fixture IDs, allowed S-lane vs private O-lane, source-specific evidence limits, behavior label vs subject vs acceptance, four narrow positive controls and `DEFERRED_BY_SCOPE` tracking are logically consistent. Record reviewer findings and any disagreement without modifying upstream. If accepted, separately ask the owner to authorize **fixture-materialization/freeze work**, then later the implementation and CPU run; do **not** automatically grant those permissions. G2 REAL/G3/BV/E1-A remain NOT AUTHORIZED. Grok remains deferred / not reviewed.

## Verified selected fixture enumeration and draft integrity (addendum)

- SPEC DRAFT Git Blob at pre-addendum HEAD: `44cd58d1089ca8b394658acafe4f8477e371d2f0`; expected 12 exact fixture rows; direct GitHub read-back found **12/12 unique IDs**: J1-F01-A/B, F02-A/B, F03-A/B, F04-A/B, F05-A/B, F06-A/B.
- Scoped synthetic draft has 4 conditionally expected limited subject PASS cases, 2 positively expected subject FAIL cases, 6 expected subject BLOCKED cases. **These are expectations, not executed test results.**
- Private oracle Lane O remains isolated by design from allowed SUT input Lane S; no fixture bytes materialized and no SHA256 digests invented. The synthetic witness and synthetic seal assumptions **do not establish** actual frozen-B0 witness availability, real provenance, or a certified G2 REAL PASS.
- Source-to-branch Git comparison found **only**: `gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md`, this checkpoint, `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. All changes are Markdown. Local checkout git status **NOT TESTED**; only GitHub remote diff is verified.
- **Latest HEAD after this amendment must be fetched from GitHub**; do not reuse pre-amendment SHA for next-stage authorization binding.
