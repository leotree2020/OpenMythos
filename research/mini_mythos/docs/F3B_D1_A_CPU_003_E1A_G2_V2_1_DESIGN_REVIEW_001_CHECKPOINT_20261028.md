# G2 V2.1 — independent design review 001 checkpoint (2026-10-28)

## Stage state — read this first

**`G2 V2.1 DOCUMENT DESIGN REVIEW PASS — LIMITED TO CPU-ONLY J1 FIXTURE-SPECIFICATION DRAFTING`.** This is **not** whole G2 design PASS, not criteria freeze, not B0/P1 safety PASS, not implemented CPU results, not real G2. It is one independent ChatGPT design review only; user-reported Grok usage limit means Grok **DEFERRED / NOT PERFORMED / NOT PASS** and the temporary owner exception applies to **documents only**.

**`G2 REAL DESIGN SAFETY PREREQUISITES BLOCKED`** until legitimate creator wait, instrumentation trust, separately authorized host-level abnormal disposition, and time/containment controls are resolved. No G2 freeze, code implementation, CPU run, fork, signal, GPU, G3, BV, E1-A or Parcae change is authorized.

**Previous accepted stages:** G0 REAL PASS; G1 REAL one-run PASS and ChatGPT/Grok raw-evidence cross-review PASS. G1 historical execution SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`; do not confuse with documentation commits.

## Source, Git and dependencies

- **Reviewed source branch:** `d1-r3-a-cpu-003-e1a-g2-v21-doc-20261028`, independently confirmed remote HEAD `870fb38c7beec33c090e743dd27fa4d3682b6700`.
- **Reviewed design:** `a_predicate_003/gate_g2/G2_DESIGN_V2_1_MINIMAL_DELTA_20261028.md`, pinned Git Blob `c2ed7330e9f5e9f18ea6d9461d47aee5eeaeace2`.
- **Reviewed checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_DESIGN_V2_1_CHECKPOINT_20261028.md`, Git Blob `4aa44840102d45c96e13a197f518a6a2382265ef`.
- **Frozen code source read in GitHub:** `a_predicate_003/bench/observer.py` (blob `635e73b34203219a3687f86332d0e82362b89670`), `node.py` (`5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`), `gate.py` (`7772c913828ea2184e6acf04cf5628c075dd5a57`).
- **Previous independent V2 review:** `a_predicate_003/gate_g2/G2_V2_INDEPENDENT_DESIGN_REVIEW_001.md` at previous source checkpoint `cf9a77b22af4487452e1ecf5add6fb284b0aa69e`.
- **This independent review branch:** `d1-r3-a-cpu-003-e1a-g2-v21-review-20261028`, created at `870fb38c7beec33c090e743dd27fa4d3682b6700`; review report `a_predicate_003/gate_g2/G2_V2_1_INDEPENDENT_DESIGN_REVIEW_001.md`; review-report creation commit `a610c8f545540313e5e43ec428fb113347629a17`. Verify latest remote HEAD after checkpoint and navigation edits.
- **Dependencies:** existing source and Markdown only; no new software, torch, GPU, private data or process test runtime. User's local workspace cleanliness was **NOT TESTED**; GitHub remote diff is a different assertion.

## Purpose, expected and actual results

| Field | Record |
|---|---|
| Objective | Audit V2.1 independently against frozen Bench and six V2 review findings, determine fitness only as input to writing a J1 CPU synthetic fixture specification. |
| Input | V2.1 §A–§G; old V2 source-review F01–F06; pinned native B0 observer/node/gate; most recent checkpoint. |
| Environment | Connected GitHub read-only fetch for code, document-only writes on a new isolated review branch; no CPU model tests, Linux process run, GPU or signals. |
| Expected | Source-grounded decisions on B0/P1, credible wait evidence ceiling, abnormal process responsibility, sidecar provenance, double-verdict semantics and owner decisions, with no scientific property overstated. |
| Actual | The six V2 issues are appropriately addressed for **CPU-only specification drafting**, while the real-run prerequisites and several future freeze choices remain open; independent review report committed. |
| Document source audit | **PASS** |
| V2.1 document acceptance for CPU spec drafting | **PASS, SCOPE-LIMITED** |
| Complete/frozen CPU acceptance suite | **NOT TESTED / NOT READY / NOT AUTHORIZED** |
| Future J1 implementation and CPU run | **NOT TESTED / NOT AUTHORIZED** |
| REAL reaper/containment | **BLOCKED** |
| Grok V2.1 review | **DEFERRED / NOT PERFORMED** |

## Remaining scientific and operational obligations

1. **B0/P1 split:** native B0 cannot claim pre-release gate witness because `observer._on_created()` invokes `_register()` with `hold_release=False`; a P1 pre-release witness is a hypothetical separate intervention. Positive PPID/fd observation alone is not unique malicious-creator identity proof.
2. **Defect reproduction != system safety:** B0 may wrongly register a same-PPID child; pure fixture test PASS on this expected defect must retain `subject=FAIL` when fixture truth positively establishes wrong attribution. An expected subject BLOCKED can likewise produce a CPU test PASS.
3. **Reap ownership:** plan A remains recommendation, O-1/O-3 **UNDECIDED**. Report tier as CLAIMED, CORROBORATED, or INSTRUMENTED_WITH_KERNEL_CORROBORATION within predeclared trusted boundaries; no unqualified REAP_CONFIRMED based on ECHILD, Z/DEAD, or creator report alone.
4. **No-signal REAL impossible to declare safe yet:** creator crash, orphan, inherited fd and `T_NODE_MAX=120` can prevent proven zero-residue closeout. A disposable environment with independently authorized external intervention is a prerequisite, not an achieved property. An external recovery cannot retroactively turn a BLOCKED run into PASS.
5. **Sidecar and oracle:** hash chain only protects *record consistency*. Before freezing, define the separately trusted final seal, exact canonical bytes, fixture inventory and oracle independence. **Synthetic ground truth may be known to the acceptance oracle but must not be passed as privileged expected answers to J1**.
6. **Owner choices:** all O-1…O-15 remain UNDECIDED; neither a reviewer recommendation nor missing Grok consent is an owner decision. Separate authorization required for any future freeze, implementation, CPU and REAL.

## Minimum next CPU-only specification drafting scope

**No experiment authorization:** documentation next, under the existing temporary Grok-review deferral:
- Define pure J1's **detection-only** question, claim IDs, allowed evidence and accepted/blocked boundaries.
- Draft up to six independent fixture families: wrong same-parent PID; duplicate registration; no pre-R witness; Z/DEAD/ECHILD; sidecar missing/truncated tail; ledger RELEASED without proven R. Each fixture has immutable independent truth **withheld from J1** and an external acceptance oracle.
- Predeclare per fixture: fixture ID, B0/P1/J1 SUT arm, source hash, data hash, assertion_id, expected subject verdict (PASS/FAIL/BLOCKED), optional behavior label, expected CPU test verdict and proof/guard requirements. B0 defect-reproduction PASS is explicitly not B0 safety PASS.
- Keep any unselected canonical cards **DEFERRED_BY_SCOPE** in the draft, not PASS or silently missing; no actual fixture files, test scripts or runs during document-only work.
- Request owner authorization separately before freezing specification, implementing, or executing any CPU suite. Grok can independently review later; preserve any technical disagreement and plan minimal controlled CPU verification if separately authorized.

## Git hygiene and only next instruction

**Git diff VERIFIED** at pre-addendum remote HEAD `123ec6ac210b1905065dfa80fbce3e582e5c7804` compared with source `870fb38c7beec33c090e743dd27fa4d3682b6700`: **4 commits changing exactly 4 Markdown paths** (2 new review/checkpoint docs; 2 append-only navigation updates), 131 insertions / 0 deletions, **zero source, Bench, Parcae, G0/G1, tests, prereg, frozen criteria, authorization or evidence modifications**. This verification addendum creates one further checkpoint-only documentation commit; re-fetch actual remote HEAD after it and do not conflate documentation HEAD with execution/code SHAs. The user's local working tree was NOT TESTED.

**Only next instruction:** prepare a **J1 CPU-only fixture pre-registration SPECIFICATION DOCUMENT DRAFT** with exact assertion-level truth/acceptance separation, using the six small fixture families and leaving REAL blocked. Do not freeze, implement, import potentially side-effectful code, run tests/processes, send signals or graduate to G3/BV/E1-A. If an essential claim lacks independent synthetic truth, set spec NOT_READY/BLOCKED, never invent a PASS.
