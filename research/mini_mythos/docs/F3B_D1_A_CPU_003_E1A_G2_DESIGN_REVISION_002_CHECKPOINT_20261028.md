# F3B-D1-A-CPU-003 — E1-A G2 DESIGN REVISION 002 checkpoint (2026-10-28)

## State and authority (read first in new sessions)

- **G1 REAL-001:** single-run T1–T4 accepted, ChatGPT + user-reported Grok read-only evidence reviews PASS. Historical execution SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d` unchanged.
- **G2 V1:** pinned commit `ee7e9d46bc46b8dc15cc66ca06569d32a677561d`; ChatGPT independent design review **CHANGES REQUIRED**, findings V1-R1…R5. V0/V1 historical designs preserved.
- **Temporary review workflow exception:** user reports Grok usage limit and permits **document-only G2 design continuation** without Grok input for now. **Grok G2 V1/V2 review = DEFERRED / NOT PERFORMED, NOT PASS.** This is no proxy opinion or two-review claim. No blanket implementation/test authorization, no implicit freeze.
- **G2 V2:** documentation draft **PREPARED; DESIGN ACCEPTANCE PENDING**. No frozen G2 acceptance criteria, no G2 code, CPU tests or REAL run. G2/G3/BV/E1-A/GPU **NOT AUTHORIZED**.
- **Baseline Git:** source revision before document task `ee7e9d46bc46b8dc15cc66ca06569d32a677561d` on branch `d1-r3-a-cpu-003-e1a-g1-closeout-g2-design-20261028`, independently retrieved via GitHub branch read. Document task on separate branch `d1-r3-a-cpu-003-e1a-g2-v2-design-20261028`. This checkpoint is written prior to its own final commit; obtain the final HEAD from remote, not this embedded snapshot.

## Purpose / environment / inputs / expected / actual

| Field | Record |
|---|---|
| Purpose | Integrate ChatGPT's V1 findings and the user's temporary Grok deferral, while preserving upstream Bench and controlled-experiment boundaries. |
| Environment | Remote GitHub read/write for UTF-8 text documents only; no Linux experiment runtime, no package install, no GPU. The user's local checkout status was NOT examined from this environment. |
| Inputs | Frozen Bench at `450914367c247231c51be02e13775cb001e69c5d`; G1 REAL closeout; V1 design `ee7e9d46…`; historical F1–F9; revision 001 response; ChatGPT V1-R1…R5 independent read-only findings. |
| Expected | Byte-identical V1 archive; explicit Grok-deferral provenance; standalone V2 addressing identity/wait proof/two-layer CPU verdict/exit horizon; checkpoint, project map and new-session index; strictly document-only Git diff. |
| Actual | V1 archived byte-identically; V1 default file prominently points to standalone V2; Grok deferral/review register and V2 standalone design created; navigation/checkpoint updated as documentation only. |
| Document draft result | **PREPARED (not design-review PASS)**. |
| Git provenance and file scope | **PASS**: independently compared parent `ee7e9d46bc46b8dc15cc66ca06569d32a677561d` against V2 branch at `d0a12703fa3b5cc10f241159074e5d004618ec50`: 9 documentation commits, **7 Markdown files only**, no `bench/`, runtime code, G0/G1, R3, Parcae, prereg, tests, tools or original evidence diff. This checkpoint's addendum will create one further documentation-only commit; verify the resulting remote HEAD. |
| G2 implementation / CPU / REAL | **NOT TESTED / NOT AUTHORIZED**. |

## Independent review findings and V2 response

| Finding | V2 response | Status |
|---|---|---|
| V1-R1: pipe inode/gate holder is not unique creator-fork proof | Separates B0 frozen Observer, proposed P1 G2 driver, J1 judge; labels gate fd+fdinfo an **observation**, not exclusive/creator proof. PRE_RELEASE cutoff is actual earliest R-write attempt, not just ledger RELEASED time. READY/FIRST_ACTION are post-release socket claims. | **Documented / theoretical prevention OPEN**. |
| V1-R2: reported wait is not independently witnessed | Separate REAP_CLAIMED, REAP_CORROBORATED, REAP_INSTRUMENTED. Direct observer wait on its own child distinguished. No universal kernel-level REAP_CONFIRMED claim. A/B alternatives remain open. | **Documented / proof-strength decision OPEN**. |
| V1-R3: subject BLOCKED vs CPU test PASS | Adds expected/actual subject verdict and separate test acceptance verdict; B0 defect-reproduction success is not G2 safety PASS. 14 unique cards in 10 families enumerated. | **Design specification PREPARED**. |
| V1-R4: zero-signal exit not reliably bounded | No reuse of signal-capable cleanup; no automatic zero-residue claim from scans; split nominal target versus >=120 s child fail-safe settlement + creator wait duty; record unresolved state in MANUAL_DISPOSITION_REQUIRED and BLOCKED. | **No safe real-run plan frozen: REAL design prerequisite OPEN**. |
| V1-R5: O-15/card count | All O-1…O-15 listed, explicitly provisional; unique card IDs enumerated. | **Documented**. |

## Unresolved choices, explicitly not falsely settled

- **Critical before any first REAL:** O-1 lawful reaper, O-2 exact B0/P1 test scope, O-3 trust level / wait-call witness, O-5 gate holder claim level for prevention, O-6 negative /proc claims, O-8 timing/process budget, O-10 orphan rule, O-13 no-signal normal/abnormal cleanup. O-15 blocks plan B's evidence transfer if selected.
- **Remaining:** O-4 raw-claim capture, O-7 sidecar digest/linearization/durability, O-9 separate real grants, O-11 credentials and Bench freeze, O-12 descendant creation path, O-14 shared gate synthetic-only. All are provisional proposals in V2, **not final owner approvals**.
- **G2 REAL is not presently safe to authorize.** If a mandatory guarantee cannot be proven under unchanged Bench, narrow the claim and label subject UNKNOWN/BLOCKED; never convert it to PASS to make progress. Grok may return later; any divergent opinion must be retained and resolved by a minimal, separately authorized controlled test.
- **No model conclusion:** Nothing in G0/G1/G2 gate design proves original Parcae forward/backward correctness, Mythos reasoning quality or efficiency gains.

## Source files and Git hygiene

Document targets, relative to `research/mini_mythos/`:
- `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V1_ee7e9d4.md` (historical V1 archival copy, exact V1 blob expected).
- `a_predicate_003/gate_g2/G2_V1_REVIEW_AND_GROK_DEFER_RECORD.md`.
- `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN_V2.md` (**active V2 DRAFT**).
- `a_predicate_003/gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md` (V1 retained with supersession banner).
- This checkpoint, plus append-only navigation updates to `docs/PROJECT_MAP.md` and `docs/SESSION_START_PROTOCOL.md`.

Never patch `bench/`, frozen G0/G1, R3, Parcae, prereg, model source, execution tools/tests or prior results. Execution-time SHA, evidence-commit SHA and documentation-commit SHA have different meanings and may not be interchanged.

## Only next task

**Read the active V2 design and this checkpoint, then perform a second source-grounded independent design review of V2, prioritizing the limit of adversarial identity proof, reaper/creator trust boundaries, evidence-chain durability, per-fixture double verdict and bounded no-signal safety.** Record any additional counterexample with smallest possible CPU fixture *proposal*, not execution. Grok remains deferred with provenance; no fictional Grok PASS.

No G2 criteria freeze, implementation, CPU tests, real fork/process experiments, signals, GPU or entry into G3/BV/E1-A without separate explicit owner authorization.

## Post-commit independent document checks (addendum)

- V1 historical archive matches the pinned V1 Git Blob **exactly**: `44848301559916ee8cc6230c03aefaefab9d1d61` (not merely a similar text copy).
- Standalone V2 Blob at pre-addendum branch HEAD: `e58fe0e0881beebcef2f3d8b0510b7e4175da1da` (151 new lines, including the per-card table). It contains **14/14** unique case identifiers `G2-D01`, `D02`, `D03a`–`D03e`, `D04`–`D10`; all are proposed, **NOT EXECUTED**.
- Git compare from V1 parent shows changed files exactly: `gate_g2/G2_IDENTITY_DESCENDANTS_DESIGN.md` (supersession banner), archived V1, V2 standalone, V1 review/Grok deferral record, this checkpoint, `PROJECT_MAP.md`, `SESSION_START_PROTOCOL.md`. Other file paths **zero diff**. No claim about the user's local checkout cleanliness is made.
- **PASS** only for **documentation scope and verification**; technical G2 V2 design review remains **PENDING**, not PASS. No G2 CPU/REAL execution happened.
- Latest branch SHA: read current remote branch after this addendum; do not reuse the pre-addendum HEAD for future authorization bindings.
