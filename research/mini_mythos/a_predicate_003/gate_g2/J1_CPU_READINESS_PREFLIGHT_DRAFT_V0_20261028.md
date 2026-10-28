# OpenMythos / G2 J1 — CPU Readiness Preflight DRAFT V0 (DOCUMENT ONLY)

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-READINESS-PREFLIGHT-DOC-001`  
**Date:** 2026-10-28 · **Owner authorization:** only documentation planning in this stage.  
**Status:** `DRAFT / REVIEW PENDING / NOT FROZEN / NO FIXTURE BYTES / NO CPU EXECUTION`.  
**Scope:** isolated **J1 synthetic detector**, not native B0, not real G2 child handling, not Parcae model correctness.

## 0. Source-of-truth and non-negotiable limitations

- Input checkpoint: `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_003_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, based on independently verified reviewer HEAD `f51f77842c1eed88c2f7f9771b712cd969604321`.
- Source-static reviewer report: `a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_003_INDEPENDENT_STATIC_REVIEW_001.md`; **only the isolated Correction 003 FORKED-PID issue achieved scoped SOURCE-STATIC PASS**, not an executed test result. Developer code HEAD `38e8a9141ebd738a34628acc928adb28cd8c54cf`.
- V0.1 draft normative *proposal*: `a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md`, Git blob `9574f90687b632f35c419a14963437c49dd35f58`. **18 expected subject verdicts: 5 PASS / 5 FAIL / 8 BLOCKED.** This is not a frozen acceptance criterion.
- Current implementation `j1/oracle.py` has exact V0.1 inventory and **`FORMAL_ACCEPTANCE_READY=False`**; `grade_case.test_acceptance_verdict` is always BLOCKED and `aggregate` always BLOCKED/NOT_READY, until a separately authorized, independently reviewed new gate exists. Do not change this constant in this stage.
- Current `j1/schema.py` defines a closed, synthetic-only Lane S schema; `j1/codec.py` rejects non-NFC input rather than silently normalizing it and rejects floats. Frozen `bench/registry.py` and `bench/observer.py` are read-only references; a native-to-J1 adapter **does not exist**.
- **No Python interpreter/import/compile/pytest/unittest**, no new code, no fixture materialization, no SHA of nonexistent files, no process/fork/wait/signal/kill/janitor/GPU/REAL, no edits to frozen source/criteria, no merge in this preflight. **Grok DEFERRED / NOT PERFORMED**, not a second PASS; O-1…O-15 owner UNDECIDED.

## 1. The testable question and the trust boundary

**Exact future question:** when a finite, independently prepared **synthetic** evidence packet and externally declared hypothetical source roles are supplied to the fixed J1 pure function, can it return the *preregistered narrow* subject PASS / FAIL / BLOCKED for all 18 cases **without seeing Lane O private truth or fixture identifiers**?

`J1.evaluate(assertion_id, subject_observables, declared_trust_model)` must receive **only**:
- one assertion enum;
- normalized synthetic `subject_observables` with `source_handle,event_kind,monotonic_order,read_status` and explicitly permitted `node_token,identity,gate_token,raw_fields`;
- a separately assigned trust map `source_handle → role,synthetic_assumption,allowed_event_kinds,provenance_tier`.

**Lane O**, which must never cross into the J1 call, privately holds `fixture_id,canonical_card,assertion_id,expected_subject_verdict,expected_behavior_label,truth_model` and independently checked fixture/custody information. Filenames, fixture/version IDs, known answers, expected behavior labels, test verdicts and digest-based fixture identity must not leak through Lane S; do not rely only on naming conventions or a Python object's privacy.

**Trust is a declared test assumption, not a verified fact about the kernel.** `G2_WITNESS_SIM`, `G2_WRAP_SIM`, `KERNEL_SNAPSHOT_SIM`, `SEAL_MANIFEST_SIM` are hypothetical sources; `B0_LEDGER` and `NODE_CLAIM_SIM` are likewise synthetic representations. `SUBJECT_LOG_READBACK` is an implementation-side proposed role for the sidecar observation (see OQ-3); **role strings do not authenticate an emitter**. Any future trust-map authority has to come from an explicitly isolated, reviewed harness, not the subject's JSON.

**Scientific ceiling:** `measurement_target=J1_SYNTHETIC_DETECTOR`, `scope=SYNTHETIC_CPU_ONLY`, `native_B0_safety_status=NOT_EVALUATED_BY_J1`. The following will remain unproved even after a synthetic CPU PASS: unique actual fork lineage, pre-R gate hold, actual child receipt, lawful reaping, zero-signal cleanup, native B0 safety, Parcae correctness and Mythos reasoning gains.

## 2. Predeclared 18 cases — INVENTORY ONLY, no data files

The following is copied in meaning and expected verdict from the existing **V0.1 document** and `oracle.SPEC_V0_1_INVENTORY`; it is a *design ledger*, not materialized S/O data or executed results. In each family, the future Lane S would contain only the evidence described; the matching Lane O row remains private and independently authored/retained.

| Fixture | Card | Assertion | Lane S observation design | Lane O private target | Expected subject | Coverage |
|---|---|---|---|---|---|---|
| J1-F01-A | D03c | ATTRIBUTION | REGISTERED Q, independently hypothesized same-gate G witness differs | observed identity contradiction | FAIL | discriminative |
| J1-F01-B | D03c | ATTRIBUTION | REGISTERED Q, no trusted gate witness | ground truth G unknown to J1 | BLOCKED | discriminative |
| J1-F01-C | D03c | ATTRIBUTION | REGISTERED G, independently hypothesized same-gate G witness matches | observed identity agreement only | PASS | discriminative |
| J1-F01-D | D03c | ATTRIBUTION | REGISTERED Q, only untrusted node claim of G | untrusted claim not independent witness | BLOCKED | discriminative |
| J1-F02-A | D03d | UNIQUE_REGISTRY | finite scoped ledger, duplicate REGISTERED (pid,starttime) for distinct nodes | duplicate within supplied set | FAIL | discriminative |
| J1-F02-B | D03d | UNIQUE_REGISTRY | finite scoped ledger, two distinct REGISTERED keys; valid prerequisites | no pair duplicate within supplied set | PASS | discriminative |
| J1-F03-A | D01-B0 | PREVENT_PROOF | B0 REGISTERED/RELEASED intent, no pre-R proof | native B0 cannot establish prevention | BLOCKED | SMOKE_ONLY |
| J1-F03-B | D01-B0 | PREVENT_PROOF | as F03-A plus later untrusted READY | post-release READY is not pre-R proof | BLOCKED | SMOKE_ONLY |
| J1-F04-A | D07 | LAWFUL_REAP | Z, DEAD, ECHILD claim; no independently witnessed lawful wait | no lawful reaping proof | BLOCKED | SMOKE_ONLY |
| J1-F04-B | D07 | ZOMBIE_AT_T | trusted hypothetical snapshot of pinned identity state Z at T | zombie state at T only | PASS | discriminative |
| J1-F04-C | D07 | ZOMBIE_AT_T | same kind of snapshot at T with state S | not zombie at T | FAIL | discriminative |
| J1-F05-A | D05 | LOG_MATCHES_SEAL | readable chained log contradicts externally trusted manifest | positive integrity mismatch | FAIL | discriminative |
| J1-F05-B | D05 | LOG_MATCHES_SEAL | valid complete chain, readback and manifest agree | byte/chain/seal match, not event truth | PASS | discriminative |
| J1-F05-C | D05 | EVIDENCE_USABLE | F05-A-style mismatched log | downstream proof cannot rely on log | BLOCKED | SMOKE_ONLY |
| J1-F06-A | D09 | DELIVERY | B0 RELEASED intent without trusted receipt | delivery not established | BLOCKED | SMOKE_ONLY |
| J1-F06-B | D09 | WRITE_COMPLETE | trusted hypothetical R-write wrapper bytes=1, no error | successful single-byte write, not receipt | PASS | discriminative |
| J1-F06-C | D09 | WRITE_COMPLETE | trusted hypothetical wrapper bytes=0 or EPIPE | positive incomplete-write contradiction | FAIL | discriminative |
| J1-F06-D | D09 | WRITE_COMPLETE | only untrusted node claim of R write | no trusted syscall result | BLOCKED | discriminative |

**Totals (expected only): 18 unique IDs; PASS=5, FAIL=5, BLOCKED=8.** Six selected arms `D01-B0,D03c,D03d,D05,D07,D09`. Nine deferred `D01-P1,D02,D03a,D03b,D03e,D04,D06,D08,D10` stay **DEFERRED_BY_SCOPE / NOT TESTED**. Four SMOKE_ONLY assertions have no positive PASS path; they cannot establish comprehensive J1 reliability. For any future test, a detector's **subject BLOCKED** may match an expected private BLOCKED and support a *test* PASS **only if independently attested input validity and all guards actually passed**; an `INPUT_INVALID` does not count.

## 3. Future artifact inventory and custody design — none created here

| Future artifact | Owner / lane | Required content | Present state |
|---|---|---|---|
| Versioned 18-case scope manifest | independent preregistration reviewer | exact IDs, cards/assertions, expected subject verdict and smoke flags, Git source SHA | DRAFT ONLY / NOT FROZEN |
| Lane S fixture input per ID | Claude Code **only after separate authorization** | canonical normalized subject observables and role grants, with **no** Lane O data | NOT MATERIALIZED |
| Lane O independent oracle per ID | reviewer/custodian not controlled by SUT | independent expected tuple, truth model, expected behavior label, evidence provenance | INVENTORY TEXT ONLY; NO VERIFIED RAW DATA |
| Per-file canonical bytes/digests | separately reviewed materializer + independent readback | full raw byte length, actual SHA-256, final newline where applicable, source/run mapping | NOT MATERIALIZED; do not invent hashes |
| Separate manifest/seal / custodian proof | trusted external custodian or independently controlled fixture store | file hash binding S/O, version, custody origin and authenticity proof **sufficient for chosen threat model** | NOT DESIGNED/VERIFIED |
| Harness trust-map binding | external reviewed harness | source handles assigned before J1, immutable within case, role ceilings and provenance assumptions | CONTRACT ONLY / NOT AUTHENTICATED |
| Runner/Oracle nonleak boundary | Claude Code code task after approval; independent review | SUT invocation cannot see fixture ID/O truth, private joining and attestation before/after | NOT IMPLEMENTED |
| CPU safety/permission guard | owner-approved minimal CPU-only execution plan | no real processes/gates, no signals/cleanup, file/path allowlist, offline/default deny | NOT REVIEWED |
| Result/evidence report | future test execution | per-case actual outputs, guard outcome, independent evidence refs, env/commit, PASS/FAIL/BLOCKED/NOT TESTED | NOT EXISTENT |

**Artifact authenticity caution:** a SHA-256 inside the same editable directory is a checksum, **not independently authenticated custody**. A file called `signed_manifest`, a string labelled `trusted`, or a Python private object cannot substitute for independently controlled predeclared expectations and evidence. Decide the actual threat model, custodian and binding procedure **before** a formal pass is possible. A lab-only synthetic test can eventually be run with explicitly limited assurance, but not promoted as a formal, authenticated acceptance run by relabeling assumptions.

## 4. Byte and schema design choices that require preregistration (not frozen)

- Current `j1/codec.py` implements UTF-8, **rejects non-NFC** strings, sorted JSON object keys, compact separators, no floats/NaN/Infinity, SHA-256, newline-complete chained records; its genesis previous digest is `"0" × 64`. Do not silently change to auto-normalization: that would be a separate versioned design decision.
- Current synthetic `schema.py` explicitly rejects unknown fields, floats and bool-as-int; validates `FORKED.raw_fields.pid` as optional positive non-bool integer, so **missing** fork pid can yield a subject BLOCKED and **present malformed** PID yields input-invalid; `FORKED.starttime` is *not required*. Source validity is **not** proof of a native B0 adapter.
- `monotonic_order` is a declared ordinal across sources, not a verified wall/monotonic clock. Per-case ledger must state its finite-scoped start/end, RUN_START/run_id, required INTENT/FORKED/REGISTERED ordering and evidence/readback semantics. Do not manufacture native CREATED/EXIT/REAPED events.
- Sidecar LOG_MATCHES_SEAL requires readback bytes and hypothetical external SEAL_MANIFEST_SIM values; whether `SUBJECT_LOG_READBACK` (proposed implementation role) is included in frozen role inventory is **OQ-3**, not assumed resolved. A malformed manifest is **BLOCKED/UNDECIDABLE**; a separately trusted well-formed manifest positively contradicting readable bytes can yield **subject FAIL**; matching bytes prove **byte integrity only**.
- Proposed file-layout concept (NO FILES CREATED): `fixtures_vX/lane_s/<id>.json`, `fixtures_vX/lane_o/<id>.json`, `manifest/<version>.json`, `readback/<version>.md`, `results/<run>.json`. The ID-bearing path may be visible **to the runner only**, never to J1 call arguments or diagnostics. This is illustrative layout, not a write instruction.
- **Potential drift check:** document language describing some S entries as “raw B0-shaped” must not override today's **closed normalized synthetic Event schema**. Require one explicit, independently reviewed mapping document before generating bytes; any conflict between V0.1 worded examples and current validator should be **BLOCKED / NEEDS VERSIONED SPEC RESOLUTION**, not silently "fixed" by a data generator.

## 5. Runner, Oracle and CPU guard: preflight threat model

**Boundary A — independent preparation:** The fixture author and the private truth approver are separately accountable. The expected tuple is pinned **before** any runtime execution. J1 cannot retrieve Lane O by import, path, environment, stdout, exception message or shared in-process helper reference. The current `oracle.py` is a separate source module but **module separation alone does not constitute a process isolation or authenticity proof**.

**Boundary B — harness permissions:** Future CPU execution should be in a disposable, dedicated, offline Linux/CPU-only workspace, with read-only pinned source, no GPU, no credentials/internal production data, no Bench or model runtime, no native G2 process creation, no forked children, no signal/kill, no special process privileges and explicit resource/time limits. **These are proposed guard properties, not a guarantee this environment exists or an instruction to run it now.** Owner must approve the environment and exact command allowlist separately.

**Boundary C — preflight attestation:** Before calling the SUT, an independent verifier checks all 18 declared case IDs, raw Lane S and Lane O bytes, hashes/lengths, schema, source handle bindings, completeness/readback and prereg version. If required evidence is missing or malformed, **test instrument BLOCKED/NOT_READY**; it must not become a matching subject BLOCKED leading to test PASS.

**Boundary D — guarded invocation:** Call the fixed `J1.evaluate` pure function with whitelist only, under a reviewed runner that excludes fixture IDs and oracle answers; capture exact output and independent guard status. Validate returned subject verdict vs pinned expectation without using per-fixture answer lookup in J1. Separate a programming exception/timeout from the actual subject verdict: a crash is **instrument FAIL/BLOCKED per reviewed test semantics**, never a subject PASS.

**Boundary E — acceptance proof:** Post-run independently re-read fixture and result artifacts, check provenance/readback and ensure no skipped, duplicate, unknown or substituted IDs. Store runner SHA, source SHA, Python version/platform, test command, dependency manifest, deterministic inputs/seed policy (if relevant), environment, runtime errors and evidence pointers. Do not report "OK" as PASS without expected-vs-actual case acceptance.

**Bounded metamorphic controls to preregister separately:** M1 bijective rename of node/gate tokens, M2 reorder unrelated records while maintaining causal ordinals, M3 remove decisive witness, M4 downgrade a trusted hypothetical role to an untrusted claim. They are **additional planned tests, not part of the 18 or executed evidence**. Changing the 18 IDs to accommodate them requires a versioned scope decision, not silent expansion.

## 6. Acceptance and stop gates (proposals only; NONE satisfied for a formal CPU run)

| Gate | Required evidence | Current state |
|---|---|---|
| RDY-01 source pin | exact Git/Blob SHAs and no frozen upstream edits | **PASS — documentary source provenance only** |
| RDY-02 scope/version | independent approval of exact 18 IDs (5/5/8), semantics, smoke limits and mismatch policies | **BLOCKED — V0.1 DRAFT, NOT FROZEN** |
| RDY-03 input/ground truth | independently authored/reviewed S/O **real bytes**, unique ids and no Lane O leakage | **BLOCKED — NOT MATERIALIZED** |
| RDY-04 provenance/seal | external provenance/custodian and pre/post independent SHA/readback, no self-attested seal | **BLOCKED — NOT IMPLEMENTED/REVIEWED** |
| RDY-05 schema consistency | V0.1-to-current-J1 mapping, source-role `SUBJECT_LOG_READBACK`, F02 finite-ledger examples, raw byte convention | **BLOCKED — NO FIXTURE-BYTES CROSSCHECK** |
| RDY-06 runner/oracle | approved isolated runner plus **real** independent attestation verifier; Oracle can only be enabled in separately reviewed code stage | **BLOCKED — ORACLE FORMAL ACCEPTANCE HARD-BLOCKED** |
| RDY-07 CPU guard | owner-approved environment + command/permissions/limits; no native G2 process experiments | **BLOCKED — NOT SPECIFIED/APPROVED** |
| RDY-08 test acceptance | 18/18 verified cases, no skipped/missing/duplicate; independent output-vs-target checks and honest FAIL/BLOCKED handling | **NOT TESTED** |
| RDY-09 reproducibility | recorded runtime/stdlib/platform, fixed source SHA, deterministic readback and 2nd independent rerun plan | **BLOCKED — NO APPROVED RUNTIME PLAN** |
| RDY-10 cross-review/owner | ChatGPT review + Grok report or explicit recorded deferral, owner signoff of residual risks, no promotion beyond synthetic scope | **BLOCKED — GROK DEFERRED; OWNER NOT SIGNED OFF** |
| RDY-11 real G2 | lawful reaper, creator/orphan, no-signal cleanup, private disposable environment | **BLOCKED INDEPENDENTLY — OUT OF J1 SCOPE** |

**No claim of CPU readiness PASS is possible from this document.** A future runner's per-case statuses should distinguish (a) **subject** PASS/FAIL/BLOCKED, (b) **instrument** valid/invalid/exception/timeout, (c) **test acceptance** PASS/FAIL/BLOCKED/NOT TESTED, (d) **suite** PASS/FAIL/BLOCKED/NOT TESTED, and (e) **native safety** NOT_EVALUATED_BY_J1. Predeclared policy should define precedence: observed valid test mismatch = test FAIL, unverifiable instrument = test BLOCKED (unless instrument corruption is itself the explicit object of a separately declared test), unexecuted = NOT TESTED; suite cannot PASS with any FAIL, BLOCKED, skipped, unknown or missing result. **Do not conflate logical contradiction with lack of evidence.**

## 7. Unresolved questions and owner decision requests (not decided here)

- **OQ-13 FORKED.pid vs REGISTERED.pid:** frozen `registry.integrity_issues` checks fork PID type but not cross-record equality. Options are **A: preserve native parity**, no such equality prerequisite in the present V0.1 finite-identity claim (recommended for this preflight's unchanged scope), or **B: propose a new separately versioned synthetic consistency assertion** with both matching/mismatch controlled cases. **Neither option is approved by this document.** Do not silently change J1 or the 18 expected outcomes. If the owner wants B, first amend prereg and independently review its evidential semantics.
- **OQ-11 gate/ticket authority:** external authenticated mapping does not exist. Options: keep the simulation clearly hypothetical for laboratory testing, or design a separate trusted binding contract before stronger attribution claims; no real B0 witness can be conjured.
- **OQ-12 formal acceptance:** existing `oracle.verify_fixture_attestation` always returns false; future custodian, predeclared S/O bytes and verifier authority require design/approval; do not simply flip `FORMAL_ACCEPTANCE_READY`.
- **OQ-1…OQ-10:** snapshot T selection, attribution time scope, LOG_READBACK representation, finite ledger completeness, SMOKE_ONLY limits, errno notation, raw_field byte schema, order scope, identity comparisons, trust-map origin remain explicitly open as described by `j1/README.md`. Future preflight of actual bytes must address any of these that affect 18 cases or mark corresponding case BLOCKED.
- **G2 O-1…O-15:** owner remains undecided on REAL design choices. Do not use synthetic J1 success to authorize any G2 REAL child or signal experiment.
- **Grok:** current report status DEFERRED/NOT PERFORMED, not a fabricated cross-review PASS. An eventual disagreement is retained and resolved by a separately authorized minimal controlled experiment, not by voting between models.

## 8. Suggested staged path AFTER separate authorization (no action executed here)

1. **Design review:** ChatGPT independently reviews this preflight and V0.1/source drift; record findings and owner choices; still no code/fixtures/CPU.
2. **Fixture specification/freeze decision:** owner explicitly approves or requests a revised `V0.2` mapping, 18-case scope, truth/custody and acceptance semantics; don't alter historical V0.1.
3. **Claude Code implementation-only stage:** under separately approved task, build S/O materializer, independently separated attestor/runner/guard *source* and unit-test source without Python invocation; no test data or run until authorized.
4. **Independent static audit:** ChatGPT reviews actual code, provenance and threat model; Grok reviewer status recorded; prepare exact CPU gate if approved.
5. **CPU-only experimental authorization:** only after gates clear, run minimal correctness controls in reviewed isolated CPU environment, with purpose/environment/input/expected/actual and PASS/FAIL/BLOCKED/NOT TESTED, capture artifact SHA/commit/runtime and guard evidence.
6. **Checkpoint:** record every outcome, unresolved question and exactly one next instruction; **G2 REAL remains separately BLOCKED** until its own safety gate is satisfied.

## 9. This stage's completion criteria and stop

**Document acceptance may be PASS only for:** source references verified, 18 expected table copied accurately without reinterpretation, independent S/O/harness/guard gaps visibly marked, measurable future gates and no activity beyond Markdown documentation. It is **not** a test, code or G2 readiness PASS. Every future role/value is a proposal, not proof of current implementation.

**Unique next instruction:** deliver this preflight document for a **separate independent DOCUMENT-ONLY technical review** and record any disagreement between V0.1 spec text, J1 schema/oracle and the proposal. Do not create real fixture data/bytes, implement runner/attestor, run CPU/REAL, choose OQ-13, freeze criteria or modify native Bench/Parcae without a later explicit authorization.
