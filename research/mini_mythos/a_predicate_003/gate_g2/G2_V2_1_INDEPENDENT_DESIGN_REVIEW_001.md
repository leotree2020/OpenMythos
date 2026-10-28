# E1-A G2 V2.1 — independent document-design review 001 (2026-10-28)

**Review object:** `G2_DESIGN_V2_1_MINIMAL_DELTA_20261028.md` at `870fb38c7beec33c090e743dd27fa4d3682b6700`, Git Blob `c2ed7330e9f5e9f18ea6d9461d47aee5eeaeace2`.  
**Baseline checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_V2_1_CHECKPOINT_20261028.md` (blob `4aa44840102d45c96e13a197f518a6a2382265ef`).  
**Sources:** frozen `bench/observer.py` (blob `635e73b34203219a3687f86332d0e82362b89670`), `bench/node.py` (blob `5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`), `bench/gate.py` (blob `7772c913828ea2184e6acf04cf5628c075dd5a57`); prior V2 review V2-F01…V2-F06.  
**Method:** independent pinned GitHub file and source inspection. No new G2 CPU fixture was written/executed; no fork/wait/signal/GPU or authorization file.  

## Verdict

**V2.1 DOCUMENT DESIGN REVIEW: PASS — SCOPE-LIMITED, FOR DRAFTING A PURE CPU-ONLY FIXTURE SPECIFICATION ONLY.**

This means the V2.1 prose is a defensible *input* to a future pre-registration/specification writing task for J1's **detection-only** classification of synthetic B0 evidence. It is **NOT** a frozen G2 criteria set, a PASS of native B0's security, a PASS of P1, an implementation authorization, a CPU-test PASS, or a real descendant safety decision.

**G2 REAL SAFETY PREREQUISITES: BLOCKED / REAL NOT AUTHORIZED.** No real G2 may start until legitimate reaper, creator trust, contained abnormal-residue handling, independent sidecar seal and exact acceptance thresholds have been separately chosen/reviewed/authorized. **Grok G2 REVIEW: DEFERRED / NOT PERFORMED**, as user reports limits and temporarily permits documentation-only work; **NO GROK PASS**. Owner decisions O-1…O-15 remain UNDECIDED.

## Verified source facts and controlled inferences

1. **B0 immediately releases ticketed children:** `bench/observer.py:276–302` `_on_created` calls `_register(child,pid,creator.pid)`. `_register(...,hold_release=False)` at lines 103–126 calls `release()` unless explicitly held. `release()` at lines 128–139 logs `RELEASED` before attempting to write `R`. Therefore a B0 PRE_RELEASE FD witness cannot be presumed to exist, and post-release READY cannot substitute for prevention evidence. V2.1 §A correctly splits `D01-B0` (detective only) and `D01-P1` (proposed different driver).
2. **Same-parent wrong PID is plausible in native B0:** `_register()` checks starttime stability and `fp2.ppid == creator_pid`, not ownership of the unique gate reader. `node.py:19–42` normally reports the true child, but this does not authenticate an arbitrary CREATED report. Shared pipe-fd observations cannot prove an adversarial unique creator/fork. V2.1 correctly treats a synthetic B0 unsafe-acceptance reproduction as `test_acceptance=PASS` **and** `subject_verdict=FAIL` where positive independent fixture truth shows the wrong PID.
3. **Native node has no descendant wait:** `bench/node.py:45–74` has `exit_after_ready`, EXIT/EOF handling and `T_NODE_MAX` fallback but no `waitpid`. The rightful parent is not reaping in frozen node_main. `Observer.reap_direct` only waits on its own direct children; another process's `WAIT_REPORT` is a claim. V2.1 §B's REAP_CLAIMED / CORROBORATED / trusted INSTRUMENTED tiers do not assert unforgeable kernel attestation.
4. **The normal path is not an anomaly-recovery guarantee:** `bench/common.py:T_NODE_MAX=120.0`; `bench/gate.py:64–82` releases before running entry. If a lawful creator exits before waiting, a child may become orphaned or remain un-reaped by the original creator. No-signal auto-cleanup or guaranteed zero residue is therefore not established by V2.1 §C. A `MANUAL_DISPOSITION_REQUIRED.json` documents open responsibility; it is not an experiment cleanup PASS.
5. **Sidecar hashes only attest consistency under a stated trust model:** V2.1 §D proposes canonical record bytes, prev-hash, exact sequence, complete lines, fsync/readback and a separately retained seal. It expressly disclaims sender/kernel authenticity; this is appropriately cautious for drafting, but seal provenance and crash-recovery details are not frozen.
6. **CPU output semantics and authority separation:** V2.1 §E specifies the 14 historical card identifiers, 15 arm-qualified candidate entries, `expected_subject_verdict`, `actual_subject_verdict`, `observed_behavior_label` and `test_acceptance_verdict`. §F has 15 owner rows, each `owner_decision=UNDECIDED`. This is suitable for specifying a pure synthetic J1 evaluator without a runtime grant or a fictitious Grok conclusion.

## V2-F01…F06 traceable disposition

| Existing issue | V2.1 evidence | Review disposition for *document-level drafting* | What is still not approved |
|---|---|---|---|
| V2-F01 HIGH: B0/P1 mixed | §A separate D01-B0 and D01-P1; frozen `observer.py:301,103–126` | **RESOLVED FOR DOC DRAFTING** | Any P1 implementation, adversarial PREVENT guarantee, native B0 safety PASS |
| V2-F02 HIGH: reaping trust | §B evidence tiers and scope | **RESOLVED AS EXPLICIT LIMITATION** | Owner choice O-1/O-3, trustworthy future wait witness, real reaping PASS |
| V2-F03 HIGH: no-signal anomaly | §C isolated environment and manual responsibility, explicit REAL blocker | **ACKNOWLEDGED, REAL STILL BLOCKED** | Actual disposable environment/authorization and proven safe containment |
| V2-F04 MEDIUM: sidecar seal | §D proposed schema + external seal caveat | **SUFFICIENT TO DRAFT FIXTURE SPECS** | Frozen seal/serialization/fsync specification, source authenticity |
| V2-F05 MEDIUM: double verdict | §E separate verdict/behavior, example table, counts | **SUFFICIENT TO DRAFT FIXTURE SPECS** | Complete immutable fixture table, parser/runner, executed CPU result |
| V2-F06 LOW: owner authority | §F all 15 rows UNDECIDED | **PASS FOR SCOPE DISCIPLINE** | Any owner-approved decision or Grok reviewer result |

### Remaining specification work — not findings overturning this scoped PASS

- **S1: Fix a single explicit CPU research question:** J1 detects safety-relevant *positive* defects vs incomplete evidence from synthetic B0, not P1 prevention, not real process lineage.
- **S2: Create complete fixture matrix:** declare `fixture_id`, arm, precise `assertion_id` / claimed property (PREVENT or DETECT), inputs, *independent* truth, expected subject verdict, optional observed behavior label, expected test acceptance and failure witness **before** tests. The V2.1 table contains only six examples; do not infer 15 fully pre-registered test inputs from it.
- **S3: Truth isolation:** fixture truth and expected verdict must be provided only to an independent acceptance oracle, **not passed into J1** as a privileged answer. J1 receives only the allowed simulated observable evidence; otherwise a trivial judge could pass by copying ground truth.
- **S4: Define deterministic schema and acceptance:** positive unsafe attribution with complete independent truth = subject FAIL; unavailable compulsory evidence = BLOCKED; clean *scoped* evidence may be PASS only if that narrowly defined claim is actually supported. CPU test PASS when J1 matches the predeclared expectation and independent guard/complete-evidence checks also pass. Unfinished/unknown fixture IDs = NOT_RUN or spec NOT_READY, not an inflated test PASS.
- **S5: Sidecar under synthetic scope:** specify exact canonical digest input, `seq`, `prev_digest`, closeout seal trust source and truncated suffix policy for CPU fixture verification. A hash chain cannot authenticate senders. The seal custodian remains an OPEN decision before frozen criteria.
- **S6: CPU-only safety contract for future implementation:** no os.fork, subprocess creation, exec, waitpid, signals, janitor, GPU or imported code path that performs these during collection/initialization. A future test authorization must separately permit actual execution and provide pre-import sentinels, no-skips FULL coverage, original raw evidence, hashes, and post-stage checkpoint.
- **S7: Maintain model-research separation:** this G2 gate design does not establish Parcae mathematics or gradients; do not divert core P1 Parcae tests or change upstream/model architecture on the strength of these documents.

## Design-review grading table

| Review item | Expected | Actual verified | Status |
|---|---|---|---|
| Source provenance | Commit and frozen source pinned | Branch, source hash, unchanged native `observer/node/gate` examined | **PASS** |
| Six V2 review issues | Explicit remedies or honest limitations | §§A–F account for all six | **PASS FOR DOCUMENT INPUT** |
| Independent truth/CPU semantic separation | No defect-reproduction test mistaken for safe system | `observed_behavior_label` separate, subject vs CPU acceptance clear | **PASS FOR DESIGN INPUT** |
| Owner and reviewer authority | No unauthorized stages, no false Grok verdict | O-1…O-15 UNDECIDED; Grok DEFERRED | **PASS** |
| Complete fixture pre-registration | Exact cases and oracle separation | Only examples, schema not frozen | **NOT TESTED / NOT READY TO FREEZE** |
| REAL reaper/containment | Lawful wait, bounded anomaly management | Open O-1/O-3/O-13, external environment not established | **BLOCKED** |
| G2 CPU execution/REAL execution | Separate owner grant | No grant and no run | **NOT TESTED / NOT AUTHORIZED** |

**Final scope verdict:** `G2 V2.1 DOCUMENT DESIGN REVIEW PASS (CPU-ONLY SPEC DRAFTING INPUT ONLY)`. This is a *one-review, limited-purpose disposition*, not a dual-review result and not G2 DESIGN/CPU/REAL PASS.

## Next one instruction

**Prepare a CPU-only J1 fixture pre-registration **DOCUMENT DRAFT** (do not freeze, code, import or run).** Begin with at most six discriminating fixture families (unsafe B0 same-parent PID, duplicate registration, missing PRE_RELEASE witness, zombie/DEAD/ECHILD, incomplete/torn sidecar, RELEASED intent without R) plus truthful baseline behavior labeling. Define exact SUT input vs independent oracle truth, assertion-level verdicts and complete selected-ID list; mark other canonical cards DEFERRED/BY_SCOPE rather than silently PASS. Keep sidecar and owner choices open, and keep G2 REAL blocked. Request distinct owner authorization for later freeze, implementation and CPU runs. Grok review remains deferred, not fabricated.
