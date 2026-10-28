# F3B-D1-A-CPU-003 — G2 J1 CPU SPEC V0.1 revision checkpoint (2026-10-28)

## Stage result, authorization and handoff (read first)

**Stage:** `G2 J1 CPU SPEC V0.1 DOCUMENT DRAFT PREPARED / INDEPENDENT REVIEW PENDING`. The V0 findings are **addressed on paper only**. The 18 expected fixture cases are a design inventory, not 18 executed tests. **G2 CRITERIA NOT FROZEN; G2 J1 CODE NOT AUTHORIZED; FIXTURE BYTES/HASHES NOT MATERIALIZED; CPU NOT TESTED/NOT AUTHORIZED; G2 REAL BLOCKED/NOT AUTHORIZED**.

**Grok review:** `DEFERRED / NOT PERFORMED` due to user-reported limits; owner's temporary permission permits **documentation work**, not a fictitious Grok PASS or a dual-review acceptance. **Owner O-1…O-15 remain UNDECIDED.** G0/G1 historical one-run REAL and reviews remain PASS. G1 historical execution SHA `3eef8d75d61fa6acad3b45a6e632c21ae1ee8f9d` unchanged. No E1-A/G3/BV or model quality claims.

**Responsibility per latest owner instruction:** ChatGPT drafts research specifications, reviews code/evidence, maintains checkpoints. **Claude Code is the designated implementer if and only if a subsequent explicit *code implementation stage* is authorized**. No Claude Code task was executed or launched as part of this documentation revision; implementation and CPU running must be granted separately. This checkpoint itself is not a code authorization.

## Source provenance, branch and artifacts

- **Prior read-first checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_CPU_SPEC_V0_REVIEW_001_CHECKPOINT_20261028.md` at pinned source commit `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6`.
- **Review input:** `a_predicate_003/gate_g2/G2_J1_CPU_SPEC_V0_INDEPENDENT_REVIEW_001.md`, Git Blob `4333dec6fb4e492039a96296316c8a34a12969e8`; findings J1-V0-F01…F06. Historical V0 specification blob `44cd58d1089ca8b394658acafe4f8477e371d2f0` is unchanged.
- **Source branch:** `d1-r3-a-cpu-003-e1a-g2-j1-spec-review-20261028` verified remote HEAD `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6` before work. A new isolated document branch `d1-r3-a-cpu-003-e1a-g2-j1-spec-v01-doc-20261028` was created from that exact SHA.
- **Main new document:** `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`; initial creation commit `ad45fbed3f13a397567be10d73880036a819706b`; Git Blob `9574f90687b632f35c419a14963437c49dd35f58` from readback.
- **Frozen Bench source pins:** `observer.py=635e73b34203219a3687f86332d0e82362b89670`, `registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`, `node.py=5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`, `gate.py=7772c913828ea2184e6acf04cf5628c075dd5a57`, `common.py=9b6532bcb42c8724115b2bca78e220a8c315632f`. No source changes authorized.
- **Git scope VERIFIED at pre-addendum HEAD `aff3ca8052fb2aa8134a54053dfbf265ac2452b2`** vs pinned source `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6`: **4 documentation commits, exactly four Markdown paths** (new V0.1 spec, new checkpoint, append-only PROJECT_MAP and SESSION_START_PROTOCOL), **194 additions, 0 deletions**, 0 Bench/Parcae/code/tests/frozen criteria/prereg/evidence/auth changes. This addendum makes one further doc-only commit; fetch final remote HEAD. Local `git status` was NOT TESTED.

## Required experiment-management fields (documentation review only)

| Field | Record |
|---|---|
| Purpose | Prepare a minimal versioned revision addressing V0 review F01…F06; prevent J1 answer leakage, per-assertion constant shortcuts, untrustworthy synthetic witness promotion, and ambiguous sidecar FAIL vs BLOCKED. |
| Environment | GitHub connected remote read/write on an isolated documentation branch. No experimental CPU/Linux process runtime, model weights, new packages, GPU, shell, signals or orchestration. |
| Inputs | Pinned V0 independent review, historical V0 12-case draft, frozen B0 Bench source and preceding checkpoint. |
| Expected document | Closed J1 subject-input whitelist vs private oracle, trust-source table, discriminating vs SMOKE_ONLY assertions, versioned seal semantics, clear scope labels, exactly enumerated proposed IDs, future Claude Code implementer boundary. |
| Actual document | Full standalone V0.1 draft committed with six families and 18 **planned** fixture rows: 5 narrowly scoped expected subject PASS, 5 expected FAIL, 8 expected BLOCKED, all actual results NOT TESTED. |
| Document readback/shape | **PASS:** GitHub readback returned blob, 18 rows with 18 unique IDs, all expected status counts match. |
| V0.1 independent design review | **PENDING / NOT TESTED**, not implied PASS. |
| Fixture materialization / SHA256 / J1 implementation / CPU | **NOT MATERIALIZED / NOT TESTED / NOT AUTHORIZED**; cannot fabricate hashes or execution results. |
| REAL reaping, abnormal cleanup, zero-signal safety | **BLOCKED / NOT AUTHORIZED**. |
| Git diff file scope | **PASS for doc-only Git scope** at pre-addendum HEAD `aff3ca8052fb2aa8134a54053dfbf265ac2452b2` vs `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6`: 4 files, no code/frozen criteria diff. Final HEAD fetched after this checkpoint commit. |

## Independent review findings dispositions (no claim of technical validation)

| Review finding | V0.1 text response | Status |
|---|---|---|
| `J1-V0-F01 HIGH` — fixture metadata/answer leakage | API whitelist `J1.evaluate(assertion_id, subject_observables, declared_trust_model)`, forbidden fixture IDs and grades, external Lane O join, proposed metamorphic controls | **ADDRESSED IN DRAFT / NOT IMPLEMENTED** |
| `J1-V0-F02 HIGH` — per-selector constants | Five assertion IDs now have contrast outputs, four remain `SMOKE_ONLY` and are explicitly excluded from comprehensive correctness claim | **ADDRESSED BY CONTRAST OR SCOPE LIMIT / REVIEW PENDING** |
| `J1-V0-F03 MEDIUM` — sidecar mismatch FAIL vs downstream BLOCKED | V0.1 `J1-F05-A` versioned to `LOG_MATCHES_SEAL` expected FAIL; new F05-C `EVIDENCE_USABLE` expected BLOCKED; historical V0 unchanged | **ADDRESSED IN DRAFT** |
| `J1-V0-F04 MEDIUM` — hypothetical witness provenance | Harness-bound trust handles and source table distinguish B0 native, node claim, simulated kernel, independent hypothetical gate witness, write wrapper and synthetic seal | **ADDRESSED IN DRAFT / TRUST REAL UNPROVEN** |
| `J1-V0-F05 MEDIUM` — reproducible bytes / completeness | Proposed canonical JSON, int/bool, ledger lifecycle, newline/torn, chained hash/genesis, external final head/readback and fail-closed rules | **DRAFT REQUIREMENTS ONLY / HASHES NOT MATERIALIZED** |
| `J1-V0-F06 LOW` — B0 safety overclaim | Explicit `measurement_target=J1_SYNTHETIC_DETECTOR`, `native_B0_safety_status=NOT_EVALUATED_BY_J1`, behavior vs subject vs test results distinguished | **ADDRESSED IN DRAFT** |

## Exact scope and open questions

Six selected arm-qualified scenario families remain: `D01-B0`, `D03c`, `D03d`, `D05`, `D07`, `D09`. Eighteen unique proposed IDs: `J1-F01-A/B/C/D`, `J1-F02-A/B`, `J1-F03-A/B`, `J1-F04-A/B/C`, `J1-F05-A/B/C`, `J1-F06-A/B/C/D`. Of 15 arm-qualified historical candidate cards, **9 `DEFERRED_BY_SCOPE`**: `D01-P1,D02,D03a,D03b,D03e,D04,D06,D08,D10`; these are **NOT TESTED**, not PASS. Planned 18/18 document IDs; actual CPU test count = **0/18 NOT TESTED**.

Discriminative within synthetic trust: `ATTRIBUTION,UNIQUE_REGISTRY,ZOMBIE_AT_T,LOG_MATCHES_SEAL,WRITE_COMPLETE`. Explicitly `SMOKE_ONLY`: `PREVENT_PROOF,LAWFUL_REAP,EVIDENCE_USABLE,DELIVERY`. A per-selector constant can pass each smoke-only subset; **no false claim of comprehensive assertion correctness**. B0 has no automatic pre-release witness; no real observed unique gate-child proof.

**Open before freeze / code handoff:** exact accepted JSON schema and bytes; simulated-source trust acquisition and harness authorization; fixture Lane S/O physical separation implementation; test-level guard/no side effects; stable independent seal custody; exact evidence closure and verifier; whether additional metamorphic cases must be frozen with 18 planned IDs; reviewer acceptance; individual owner O decisions. Do not imply the source-labelled trust of a socket message is authentic.

**REAL blockers unchanged:** G2-R01 lawful reaper, plan A/B not selected, wait trust, node creator crash/orphan, no-signal bounded cleanup, independent disposable-environment operational responsibility; G2 REAL **BLOCKED**. Parcae P1 reproduction remains its own research mainline and gains no correctness result from this gate spec.

## Only next instruction

**Independently audit J1 CPU SPEC V0.1 against frozen B0 source and V0 findings F01…F06**. Verify 18 fixture IDs, five truly evidence-sensitive assertions, four truthful SMOKE_ONLY labels, Lane S/O firewall, simulated trust boundaries, and the versioned seal mismatch `FAIL` vs downstream `BLOCKED`. Record actual disagreements, limits and a new checkpoint. If V0.1 review accepts it, ask for **separate owner authorization** to create a bounded Claude Code *implementation-only* task; **do not** silently freeze criteria or execute CPU tests/REAL. No G2 code, CPU, process, signal, GPU or model changes under this document-only stage.

## GitHub remote read-back validation addendum

- V0.1 specification Git Blob `9574f90687b632f35c419a14963437c49dd35f58` was independently read back. **18/18 unique fixture IDs** found, with **5 expected scoped PASS, 5 expected FAIL, 8 expected BLOCKED**; 0 actual fixture files and 0 executed tests.
- The independent compare verified exactly 4 Markdown paths under `research/mini_mythos/a_predicate_003/gate_g2/` and `research/mini_mythos/docs/`; no old V0 or upstream/Bench source file changed. `PROJECT_MAP` and `SESSION_START_PROTOCOL` updates are append/insert-only.
- Claude Code is listed only as a **future code-stage implementer contingent upon separate explicit approval**. This doc submission did not send a task to Claude Code or execute code; no permission to materialize/implement/run tests is inferred.
- Latest remote HEAD should be re-read after the addendum commit. Full model Parcae P1 progress still needs a separate checkpoint audit, rather than inferring from G2 infrastructure docs.
