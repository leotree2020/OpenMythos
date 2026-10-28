# F3B-D1-A-CPU-003 E1-A G2 — V2.1 design delta checkpoint, 2026-10-28

## Authority, verified starting point and exact stage

- **Task:** G2-DESIGN-REVISION-003. **DOCUMENTATION ONLY**; no code implementation, CPU fixture execution, real process run, signal, subreaper, janitor, new authorization file, GPU, or changed frozen criteria.
- **Source checkpoint:** docs/F3B_D1_A_CPU_003_E1A_G2_V2_INDEPENDENT_DESIGN_REVIEW_001_CHECKPOINT_20261028.md read first; source branch d1-r3-a-cpu-003-e1a-g2-v2-review-20261028 HEAD independently verified as cf9a77b22af4487452e1ecf5add6fb284b0aa69e.
- **Source review finding:** G2 V2 DESIGN CHANGES REQUIRED; V2-F01…V2-F06 high/medium/low design findings, with REAL design prerequisites BLOCKED.
- **This work branch:** d1-r3-a-cpu-003-e1a-g2-v21-doc-20261028, branched directly at cf9a77b22af4487452e1ecf5add6fb284b0aa69e.
- **Primary deliverable:** a_predicate_003/gate_g2/G2_DESIGN_V2_1_MINIMAL_DELTA_20261028.md; creation commit 4512a555d4cb6755d2515fbb1ecfe808c58feddc. This is a supplement to the historical V2, **not frozen criteria nor a silently rewritten V2**.
- **Grok:** user reports usage limits; permits continuing documentation temporarily based on ChatGPT assessment. Grok has not reviewed this V2.1 delta, and review status is **DEFERRED / NOT PERFORMED**, not PASS.
- **Owner decisions:** O-1…O-15 remain UNDECIDED. Reviewer recommendations do not replace owner approval.
- **Stage status:** G2 V2.1 DESIGN DELTA PREPARED / INDEPENDENT V2.1 DESIGN REVIEW PENDING / G2 CRITERIA NOT FROZEN / G2 IMPLEMENTATION, CPU, REAL NOT TESTED OR AUTHORIZED. G1 REAL historic cross-review PASS unchanged; G3/BV/E1-A remain not authorized.

## Test-style record even though only documents were created

| Field | Evidence |
|---|---|
| Objective | Resolve V2-F01…F06 at the design text level while preserving all unsafe/unknown conclusions and separate G2 from Parcae/model work. |
| Environment | GitHub repository source read, separate branch document commits; no CPU/Linux process test runtime, no new dependencies, no GPU. |
| Input | Pinned V2 review, frozen bench/observer.py, node.py, gate.py, registry.py, common.py, and prior checkpoint. |
| Expected | Clear B0 vs P1 arm separation; explicit creator wait trust tier; containment/residual protocol that never asserts no-signal cleanup without evidence; closed proposed sidecar envelope; precommitted CPU fixture acceptance fields; 15 O-decision rows with owner decisions UNDECIDED; no executable code change. |
| Actual | V2.1 sections A–F and proposed acceptance record in §G. A deterministic output of a future implementation is **not claimed**. |
| Document preparation | **PREPARED / PASS for document existence**; no technical property or actual CPU/REAL passed. |
| Independent design acceptance | **NOT TESTED / REVIEW PENDING**. |
| G2 source/runtime correctness, CPU, REAL | **NOT TESTED / NOT AUTHORIZED**. |
| Git file-change scope | Verify against source SHA and record in addendum after navigation updates. |

## Findings disposition and technical restrictions

| Finding | V2.1 proposed response | Reviewer/owner status |
|---|---|---|
| F01 (B0/P1) | D01-B0 detection-only, no pre-R witness guarantee; D01-P1 distinct possible held-release intervention. No adversarial identity-proof assertion based solely on PPID/fd. | Text proposal; **O-2 UNDECIDED** |
| F02 (lawful wait) | EXIT / ZOMBIE / REAP_CLAIMED / CORROBORATED / INSTRUMENTED; no universal REAP_CONFIRMED. Plan A recommended only. | Text proposal; **O-1/O-3 UNDECIDED** |
| F03 (abnormal stop) | Private disposable environment with independently authorized manual disposition required before REAL; normal and anomaly horizons separate, orphan crash remains BLOCKED. | **REAL safety BLOCKED**, owner/containment absent |
| F04 (sidecar) | Proposed canonical JSONL envelope, genesis/seq/digest, newline, fsync/readback, externally trusted final seal; hash chain not provenance/authenticity. | Text proposal; O-7 and independent seal source OPEN |
| F05 (dual verdict) | 14 historical canonical IDs; D01 arm split produces **15 candidate arm entries**; separate observed_behavior_label, subject and test verdict fields; test PASS never proves B0 safe. | Fixture definitions still NEED preregistration |
| F06 (authority) | O-1…O-15 reviewer recommendations separated from owner decision (all UNDECIDED) and evidence/blocking status. | No owner choice made |

**Hard safety conditions unchanged:** no modification of upstream Parcae or Bench; no frozen G0/G1/R3/criteria change; no opportunistic Recursive Transformer redesign. Any disagreement on safety requires a minimal **separately authorized CPU-only synthetic** experiment, not selecting one AI. No live hostile creator/unknown bystander/signals are authorized. No closed "zero residual" claim from periodic /proc scans or a manual-disposition file.

## Dependencies, risks, and Git

- No new Python packages, process capabilities, GPU or data assets. Dependencies are only existing GitHub source and checkpoint artifacts.
- Root risks: gate uniqueness cannot be proven merely by fd/PPID; creator wait wrapper needs explicit trust; no-signal abnormal orphan process lacks assured lawful reaper/closed recovery; sidecar integrity does not authenticate events or prevent writer fabrication.
- **Git diff VERIFIED at pre-addendum HEAD `62b5628c378eae9bf2b7b818e6fdc538e19bd37c`** vs pinned source `cf9a77b22af4487452e1ecf5add6fb284b0aa69e`: **4 documentation commits, exactly four Markdown paths (2 added + 2 append-only navigation edits), 184 lines inserted, 0 deleted, 0 runtime/source/test/Bench/Parcae/criteria/prereg/evidence changes**. V2.1 design Git Blob: `c2ed7330e9f5e9f18ea6d9461d47aee5eeaeace2`. The current checkpoint amendment will add one additional document-only commit; read final remote HEAD after the amendment; user's local checkout status remains unknown.
- This checkpoint is created prior to navigation commits. Final HEAD must be fetched from GitHub after last write and checked against source SHA. The G1 execution SHA 3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d is a historical runtime binding, not this document SHA.

## One next instruction

**Independently review G2 V2.1 delta** against frozen Bench and V2-F01…F06, especially exact B0/P1 D01 evidence, truthful attribution/reaping tier, independent sidecar seal, and external containment assumptions. If acceptable for future criteria drafting, the reviewer may report **DOCUMENT DESIGN REVIEW PASS (scope-limited)** only; no approval to freeze G2 or implement. Any remaining real-reaper/containment uncertainty keeps REAL BLOCKED. Grok remains formally deferred and can submit a separate review later. **No G2 implementation, CPU test, process fork, real experiment or next stage without separate owner authorization.**
