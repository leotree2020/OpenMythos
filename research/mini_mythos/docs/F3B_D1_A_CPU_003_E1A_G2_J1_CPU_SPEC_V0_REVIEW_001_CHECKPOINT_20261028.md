# F3B-D1-A-CPU-003 E1-A G2 J1 CPU SPEC V0 independent review checkpoint — 2026-10-28

## Official outcome and authorization boundary

**`G2 J1 CPU SPEC V0 DOCUMENT REVIEW: CHANGES REQUIRED`** — document was reviewed successfully (not BLOCKED from review), but **not accepted for fixture materialization/freeze**. Current review only; no actual synthetic CPU test, no J1 implementation, no B0/P1 runtime run, no real process, no signals, no GPU, no criteria freeze, no Parcae/model modifications.

**`G2 CPU = NOT TESTED / NOT AUTHORIZED`; `G2 REAL = DESIGN SAFETY BLOCKED / NOT AUTHORIZED`; Grok G2 review = DEFERRED / NOT PERFORMED / NOT PASS.** User permitted documentation continuation while Grok is rate-limited; that is not dual-review consensus or implementation/experiment approval. All O-1…O-15 owner choices remain `UNDECIDED`. G0/G1 historical REAL PASS and Git evidence remain untouched.

## Git source, commit and artifact

- Verified remote baseline branch `d1-r3-a-cpu-003-e1a-g2-j1-cpu-spec-draft-20261028` at `fb5bb8779b93fb9027964e43229f368c1750488e` before review.
- Review target `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_20261028.md`, immutable Git Blob `44cd58d1089ca8b394658acafe4f8477e371d2f0`.
- Prior checkpoint `docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_DRAFT_001_CHECKPOINT_20261028.md`, Git Blob `810d8db1d3ba97c34bec1cb3fbf804638a19fee7`.
- Frozen `bench/observer.py` `635e73b34203219a3687f86332d0e82362b89670`; `registry.py` `3f2179e132371dd323f865be8a4d41fa5e58786d`; native `node.py`, `gate.py`, `common.py`, `proto.py` read-only.
- New isolated **review-document-only** branch `d1-r3-a-cpu-003-e1a-g2-j1-spec-review-20261028` created from exact source HEAD. Review record `a_predicate_003/gate_g2/G2_J1_CPU_SPEC_V0_INDEPENDENT_REVIEW_001.md` committed at `2b9f4164a09d390058654aebd358581b08e06177`.
- Checkpoint branch's **latest commit SHA** to be independently retrieved from GitHub after final navigation updates. Documentation commit SHA is not G1 execution SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d`.

## Test-style accounting (NO experiment performed)

| Field | Evidence / scope |
|---|---|
| Purpose | Independently check J1 synthetic spec's source grounding, Lane S vs Lane O isolation, 12 expected cases, semantic PASS/FAIL/BLOCKED and claim limits. |
| Environment | GitHub remote source read + document-only isolated review branch. No CPU experimental runtime, process fork, SIGKILL, GPU, external model or new dependency. |
| Input | Pinned J1 V0 SPEC, last checkpoint, frozen Bench observer/registry/node/gate/common/proto and V2.1 scoped review. |
| Expected | Traceable review conclusion, source-grounded minimal counterexamples, all review issues recorded, Git doc-only checkpoint and single next instruction. |
| Actual | Six findings `J1-V0-F01…F06` identified, described with line/section evidence and **not-run counterexamples**; record committed. |
| Source/document inventory | **PASS**: 6 scenario families, 12 unique planned fixture IDs, 4 narrow *expected* PASS, 2 *expected* FAIL, 6 *expected* BLOCKED; nine other arms DEFERRED_BY_SCOPE. |
| J1 spec independent review | **CHANGES REQUIRED**, not CPU/test FAIL. |
| J1 fixture bytes and SHA256 | **NOT MATERIALIZED / NOT TESTED**. Hashes cannot be guessed or fabricated. |
| Frozen G2 criteria | **NOT FROZEN / NOT AUTHORIZED**. |
| J1 implementation / CPU run | **NOT TESTED / NOT AUTHORIZED**. |
| G2 REAL lawful reaping / abnormal cleanup | **BLOCKED / NOT AUTHORIZED**. |
| Grok review | **DEFERRED / NOT PERFORMED**, no review opinion invented. |
| Git changed-file scope | **PASS (pre-addendum):** compared source `fb5bb8779b93fb9027964e43229f368c1750488e` against review branch at `d58b0cb06c5b183b7de1f778120aab6286986f7f`: 4 commits, exactly 4 Markdown files (2 additions + 2 append-only navigation edits), 145 added lines, 0 deleted, **no Bench/Parcae/criteria/tests/runtime/evidence changes**. This verification addendum creates one further checkpoint-only doc commit; fetch final remote HEAD afterward. |

## Independent review findings / open questions

| Ref | Severity | Verified question and required revision | Status |
|---|---|---|---|
| J1-V0-F01 | HIGH | Fixture ID/card/answer metadata may leak via J1 API. Strict whitelist, private oracle join and no-ID metamorphic control required. | **OPEN** |
| J1-V0-F02 | HIGH | Some assertion IDs can be passed with a constant return, especially PREVENT-PROOF and single-row REAP/WRITE assertions. Add discriminating counter-controls or explicitly label SMOKE_ONLY. | **OPEN** |
| J1-V0-F03 | MEDIUM | A trusted seal mismatch is positive log-integrity failure (FAIL), but downstream evidence usability is BLOCKED; V0 F05-A conflates the assertions. Fix predeclared assertion/expected result. | **OPEN** |
| J1-V0-F04 | MEDIUM | G2_WITNESS_SIM and G2_WRAP_SIM are hypothetical not B0-native; sender/witness provenance may not be inferred from a string label. | **OPEN** |
| J1-V0-F05 | MEDIUM | Deterministic canonical input bytes and no silent torn-tail/partial-record PASS are still underspecified for future freeze. | **OPEN** |
| J1-V0-F06 | LOW | Per-fixture and aggregate status must say J1_SYNTHETIC_DETECTOR, never B0/G2 safety PASS. | **OPEN** |

The V0 document is **not rewritten in this review**; this finding file preserves the exact reviewed commit. The recommendation to change F05-A in a future V0.1 must be versioned, not represented as its original expected outcome.

## Dependencies, risks, and Git hygiene

- Inputs depend only on existing repo documents and frozen code for read-only inspection. No installed packages, GPU, external Parcae weights or data. Owner/local checkout status **NOT TESTED**, only GitHub remote source/diff can be verified.
- Critical validity risk: a shortcut classifier using fixture ID or per-assertion constant outputs may pass an underspecified battery despite failing the scientific question. Synthetic source `G2_WITNESS_SIM` does not establish availability/authenticity of live witness for B0.
- Safety risk: native node has no trustworthy descendant wait path; no-signal recovery for creator crash/orphan/FD uncertainties unresolved. REAL remains BLOCKED regardless of future CPU J1 outcome.
- Frozen Bench, Parcae, R3, G0/G1 criteria, model architecture, original G1/G0 evidence must remain unchanged.
- Grok review still deferred. Record any genuine Grok disagreement if later supplied; do not select one AI's opinion as final experimental proof.

## Unique next instruction

**Prepare a minimal J1 CPU SPEC V0.1 DOCUMENT-ONLY revision** to address F01…F06. Keep 6 families unless explicitly justified, close input API so expected fixture IDs/oracle truth cannot leak, add or label single-outcome assertions as SMOKE_ONLY, separate positive sidecar-integrity violation FAIL from downstream unusable-evidence BLOCKED, specify trust tiers for hypothetical witnesses, retain independent canonical/hash assumptions as draft. Return for new independent source-grounded doc review. **Do not implement, freeze, materialize fixture JSON, run CPU/process tests, use GPU, modify Parcae/Bench or start G2 REAL.**

## Post-commit review integrity and diff verification

- Review report blob at pre-addendum HEAD: `4333dec6fb4e492039a96296316c8a34a12969e8`; checkpoint blob before this addendum: `66db99c2c3d6afac337dc54188befba7c99740a7`.
- All **6** findings `J1-V0-F01…F06` present in committed review; reviewed V0 draft remains unchanged (Git Blob `44cd58d1089ca8b394658acafe4f8477e371d2f0`).
- Verified changed paths: `gate_g2/G2_J1_CPU_SPEC_V0_INDEPENDENT_REVIEW_001.md`, this checkpoint, `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`; only Markdown. No local checkout status assertion; GitHub remote comparison only.
- Stage result remains **CHANGES REQUIRED** for spec V0; actual G2 CPU/REAL **NOT TESTED / NOT AUTHORIZED**. A document-only review cannot be represented as a CPU PASS. Grok remains DEFERRED, all owner decisions O-1…O-15 UNDECIDED.
- Source or execution bindings must use exact Git SHAs appropriate to their roles; the final review branch HEAD after this amendment is retrieved separately.
