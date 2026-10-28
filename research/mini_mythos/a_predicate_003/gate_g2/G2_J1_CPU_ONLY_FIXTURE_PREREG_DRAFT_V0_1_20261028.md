# E1-A Gate G2 — J1 synthetic CPU-only fixture pre-registration SPEC DRAFT V0.1

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-CPU-SPEC-REVISION-001` · 2026-10-28  
**Document basis:** independent V0 review `G2_J1_CPU_SPEC_V0_INDEPENDENT_REVIEW_001.md` at `32bf2c18803b946e3cfe387d1296e9b7f6e5d7b6`, V0 reviewed blob `44cd58d1089ca8b394658acafe4f8477e371d2f0`. V0 remains **unchanged as historical prior proposal**.  
**Frozen Bench blob pins:** `observer.py=635e73b34203219a3687f86332d0e82362b89670`; `registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`; `node.py=5bda87c6c9e98a91c32e3d4eadcd1ca94cb2bd8b`; `gate.py=7772c913828ea2184e6acf04cf5628c075dd5a57`; `common.py=9b6532bcb42c8724115b2bca78e220a8c315632f`.  
**State:** `V0.1 DOCUMENT DRAFT PREPARED / INDEPENDENT DESIGN REVIEW PENDING`. **NOT FROZEN; NO CODE; NO MATERIALIZED FIXTURE JSON; NO CPU RUN; NO G2 REAL.** Only documentation is authorized. Grok `DEFERRED / NOT PERFORMED` is **not PASS**. All owner O-1…O-15 remain UNDECIDED. No original Parcae/Bench/G0/G1/R3/architecture edits.

## 1. What the fixture set can and cannot test

The sole CPU-research question is: can a *future pure function J1*, given finite **synthetic B0-shaped records and explicitly declared hypothetical sensors**, distinguish observed positive protocol contradictions, missing evidence, and *narrow finite-scope facts*? Native frozen **B0 is NOT executed** by these fixtures, P1 is NOT implemented, and this document does not establish Parcae/LLM correctness.

A `PASS` subject verdict must state its exact limited assertion: internal supplied-record uniqueness, state Z at time T, integrity matching a trusted synthetic seal, **observation agreement under a simulated trusted witness**, or one-byte syscall success under a *simulated trusted wrapper*. None proves malicious-creator-resistant identity, true recipient of gate R, unobserved process absence, real lawful reaping, or real hardware behavior. A future J1 detector **test PASS does not mean native B0 security PASS**.

## 2. Strictly separated SUT invocation and oracle lanes (fixes J1-V0-F01)

**Proposed function contract, NOT code:** `J1.evaluate(assertion_id, subject_observables, declared_trust_model) -> {subject_verdict, evidence_basis_codes}`. `assertion_id` selects the *question only*; `subject_observables` is a list of timestamped raw B0-shaped rows or raw simulated source observations. `declared_trust_model` is a **harness-validated capability map** bound to source handles **before J1 is called**; no subject record can elevate its own authority by writing a trusted source name.

**J1-visible whitelist:**
- `assertion_id`: one enum from §3, without fixture ID, file path, test status or expected answer.
- `subject_observables`: records with `source_handle` (opaque harness-bound handle), `event_kind`, `monotonic_order` (ordinal, not clock guarantee), `node_token`, `identity` (`pid,starttime,ppid` and optional `boot_id,pidns`), `gate_token`, `raw_fields`, `read_status`. All fields are optional or mandatory by **specified event schema**; do not infer identity from missing values.
- `declared_trust_model`: external table binding `source_handle -> role, synthetic_assumption, allowed_event_kinds, provenance_tier`; this table comes only from the harness's predeclared trusted test contract, **not an untrusted message field**. A `G2_WITNESS_SIM` string inside `raw_fields` never grants authority.

**Entirely forbidden to J1:** `fixture_id`, `canonical_card`, `case_id`, `filename`, `fixture_version`, `source_file_path`, `input_digest` if keyed to fixture identity, `oracle_truth`, `actual_gate_child_pid` (except a separately sourced raw observation with this PID), `is_attack`, `expected_subject_verdict`, `expected_test_acceptance_verdict`, `observed_behavior_label`, `test_acceptance_verdict`, run-stage statuses, owner decisions, or any grades. The **runner** privately retains fixture ID for joining output to **Lane O**; J1 has no way to request it through its API. The acceptance oracle is a separate code path/process boundary to be specified by Claude Code only if code work is separately approved.

**Lane O** (never passed to J1) holds immutable `fixture_id`, `canonical_card`, `truth_model`, `assertion_id`, `expected_subject_verdict`, optional `expected_behavior_label`, conditional `expected_test_acceptance_verdict`, provenance and independent truth/readback digests. **No hardcoded fixture-ID-to-answer dispatch** is permitted in J1. A future implementation must validate schemas and reject unknown/forbidden J1 input fields before calling J1; a public `assertion_id` is allowed but §4 explicitly audits selector-specific output diversity.

**Metamorphic tests to draft later, not executed:** (M1) rename node/gate tokens bijectively with same relationships → identical verdict; (M2) reorder unrelated records while preserving relevant causal ordering → identical verdict; (M3) remove one decisive trusted witness → recompute from evidence, not fixture label; (M4) swap trusted vs untrusted provenance for the same raw claim → no unjustified promotion. These are **future proposals**, not hidden executed validations.

## 3. Source roles, trust and exact assertion semantics (fixes F02–F04)

| Source role (harness-origin tier) | Real frozen B0 availability | Synthetic J1 fixture use | Proof ceiling |
|---|---|---|---|
| `B0_LEDGER` | Actual registry records yes; RELEASED is **intent**, and `REGISTERED.pid` is observer registration based on creator's claim | Transcribe with complete scoped lifecycle preconditions | B0 said the event was registered; no authentic gate recipient |
| `NODE_CLAIM_SIM` | Node messages exist over inherited `SOCK_SEQPACKET`, **not per-message sender-authenticated** | Untrusted synthetic message about G or write | Claim only: never a trusted independent witness |
| `KERNEL_SNAPSHOT_SIM` | /proc readable with possible limits; this sample is **not itself a collected real snapshot** | Simulated `state,ppid,starttime` at a named ordinal T | A time-indexed observation, not non-atomic complete universe |
| `G2_WITNESS_SIM` | **Not provided by native B0** | Separately predeclared trusted hypothetical gate-child observation | Only observational corroboration under hypothetical trust; not unique fork authentication |
| `G2_WRAP_SIM` | **Not provided by native B0** | Hypothetical wrapper's `R_WRITE_RESULT` bytes/errno | Successful write syscall under assumed wrapper trust, not recipient/first action |
| `SEAL_MANIFEST_SIM` | **No independent native B0 sidecar seal** | Hypothetical manifest independently sealed by harness fixture oracle | Integrity of logged bytes only, not event authenticity or actual custody |

**Assertion statuses:** `PASS` = property positively established **inside its defined data and trust scope**; `FAIL` = verified contradictory evidence for that same property; `BLOCKED` = missing or untrustworthy evidence for that property. Subject `PASS/FAIL/BLOCKED` and **CPU fixture acceptance** `PASS/FAIL/BLOCKED/NOT_RUN` are different. `NOT_RUN` is only a test-run state, never a subject verdict. Unknown or invalid fixture construction is `SPEC NOT_READY`, not an observed G2 FAIL.

| Assertion enum | Strict claim (no stronger implication) | Contrast / status |
|---|---|---|
| `ATTRIBUTION` | Registered PID vs predeclared trusted *hypothetical* gate-child observation for same ticket | FAIL mismatch, PASS observed agreement, BLOCKED no trusted witness / only untrusted claim; **discriminative within synthetic trust** |
| `UNIQUE_REGISTRY` | Unique (pid,starttime) across **complete-for-this-assertion supplied REGISTERED set** | FAIL duplicate, PASS no duplicate only within supplied set; **discriminative** |
| `PREVENT_PROOF` | Native B0 proved pre-R gate/identity prevention | Only B0 missing pre-R witness, with/without READY => BLOCKED; **SMOKE_ONLY**, no safety/prevention PASS can be claimed |
| `LAWFUL_REAP` | Observed evidence proves rightful wait | Z, DEAD, ECHILD unverified => BLOCKED; **SMOKE_ONLY**, no lawful-wait PASS |
| `ZOMBIE_AT_T` | Pinned process state at selected snapshot T is Z | PASS for state Z, FAIL for state S; **discriminative** |
| `LOG_MATCHES_SEAL` | Read-back sidecar bytes/seq/head exactly match separately trusted seal | PASS match, **FAIL trusted mismatch**; **discriminative** |
| `EVIDENCE_USABLE` | Can this compromised log support downstream inferential claims? | BLOCKED for mismatched log; **SMOKE_ONLY**, not an integrity FAIL |
| `DELIVERY` | An intended child has actually received R | RELEASED intent only => BLOCKED; **SMOKE_ONLY**. Native B0 lacks independently verified child receipt in this fixture |
| `WRITE_COMPLETE` | A trusted *hypothetical* write wrapper recorded successful single-byte R write | PASS bytes=1 & no error, FAIL EPIPE/bytes=0, BLOCKED untrusted claimant only; **discriminative** |

**V0 history preserved:** `J1-F05-A` originally asked the ambiguous `J1-A-SIDECAR-INTEGRITY` question and expected BLOCKED. **V0.1 deliberately changes the assertion to `LOG_MATCHES_SEAL` with expected FAIL** for positive mismatch; this is a **versioned preregistration proposal before any fixture materialization**, not retroactive relabeling of a run. The distinct downstream `EVIDENCE_USABLE` question remains expected BLOCKED on new `J1-F05-C`.

**Scope warning:** `PREVENT_PROOF`, `LAWFUL_REAP`, `EVIDENCE_USABLE` and `DELIVERY` are **SMOKE_ONLY** in this selected battery: a hard-coded constant per assertion could pass those rows. Do not claim comprehensive per-assertion correctness or a globally discriminative J1 without future balanced cases. No hypothetical P1 real execution is introduced to manufacture a B0 prevention PASS.

## 4. Complete selected V0.1 fixture matrix (six families, 18 unique IDs)

**ALL values are hypothetical and expected — NO FIXTURES MATERIALIZED, NO TESTS EXECUTED.** Creator K=(4100,100), sibling Q=(4101,101), gated G=(4102,102), node nA/nB and gate-A are fictional labels, never the user's host PIDs. Any simulated trusted source is granted by the external test harness contract, not by its own `source_role` string. All shown expected **CPU test verdicts would be PASS if J1 produces the correct result and guards/evidence are valid**. No actual results field exists.

| Fixture ID | Candidate / Assertion | Lane S: subject-visible controlled observations | Lane O: private independent truth | Expected subject | Behavior label (O only) | Scientific coverage |
|---|---|---|---|---|---|---|
| `J1-F01-A` | `D03c` / `ATTRIBUTION` | B0 REGISTERED nA=Q; pre-R PPID(Q)=K; independent simulated gate-child witness for G and same ticket | G≠Q; trusted synthetic witness visible | **FAIL** | `B0_WRONG_PID_ATTRIBUTION_OBSERVED` | DISCRIMINATIVE; simulated trusted sensor |
| `J1-F01-B` | `D03c` / `ATTRIBUTION` | B0 REGISTERED nA=Q, PPID(Q)=K; no gate-child witness | G≠Q known privately but invisible to J1 | **BLOCKED** | `GATE_CHILD_UNVERIFIED` | DISCRIMINATIVE; no sensor |
| `J1-F01-C` | `D03c` / `ATTRIBUTION` | B0 REGISTERED nA=G and independently simulated witnessed gate child G for same ticket | Only observed registered vs witnessed identity agrees | **PASS** | `ATTRIBUTION_MATCH_UNDER_TRUSTED_SIM` | DISCRIMINATIVE; PASS limited to observed consistency |
| `J1-F01-D` | `D03c` / `ATTRIBUTION` | B0 REGISTERED nA=Q; purported G identity only from untrusted NODE_CLAIM_SIM, no independent witness | G≠Q privately, sender claim not authenticated | **BLOCKED** | `UNTRUSTED_CHILD_CLAIM_ONLY` | DISCRIMINATIVE; source-trust contrast |
| `J1-F02-A` | `D03d` / `UNIQUE_REGISTRY` | Complete scoped valid ledger: REGISTERED nA=(4101,101), nB=(4101,101) | Duplicate within supplied complete record set | **FAIL** | `DUPLICATE_REGISTERED_IDENTITY` | DISCRIMINATIVE; finite input |
| `J1-F02-B` | `D03d` / `UNIQUE_REGISTRY` | Complete scoped valid ledger: REGISTERED nA=(4101,101), nB=(4102,102); all prerequisites | No duplicate in supplied record set | **PASS** | `NO_DUPLICATE_IN_SUPPLIED_SET` | DISCRIMINATIVE; no global absence |
| `J1-F03-A` | `D01-B0` / `PREVENT_PROOF` | B0 REGISTERED then RELEASED intent, no proven pre-R gate-hold witness | Frozen B0 no held-release sample | **BLOCKED** | `B0_NO_PRE_RELEASE_WITNESS` | SMOKE_ONLY; B0 cannot prove preventive identity |
| `J1-F03-B` | `D01-B0` / `PREVENT_PROOF` | As F03-A plus POST_RELEASE READY(fp.pid=registered pid) untrusted socket claim | READY later than earliest R, cannot prove prevention | **BLOCKED** | `POST_RELEASE_READY_NOT_PREVENTION` | SMOKE_ONLY; post-release doesn't change status |
| `J1-F04-A` | `D07` / `LAWFUL_REAP` | Pinned Z + B0 DEAD + creator ECHILD claim, no trusted wait call | Z not reaped; lawful wait not demonstrated | **BLOCKED** | `Z_DEAD_ECHILD_NOT_REAP` | SMOKE_ONLY; REAL reaper remains blocked |
| `J1-F04-B` | `D07` / `ZOMBIE_AT_T` | Hypothetical trusted kernel snapshot at T with pinned pid/starttime and state=Z | Same instance Z at T | **PASS** | `ZOMBIE_OBSERVED_ONLY` | DISCRIMINATIVE; only state-at-T |
| `J1-F04-C` | `D07` / `ZOMBIE_AT_T` | Same source/identity/time as F04-B but state=S, not Z | Same instance not Z at T | **FAIL** | `NOT_ZOMBIE_AT_T` | DISCRIMINATIVE; state-only counterfactual |
| `J1-F05-A` | `D05` / `LOG_MATCHES_SEAL` | Two valid chained records; trusted external manifest for same run requires seq=3, different byte length/head | Seal positively contradicts current log | **FAIL** | `SEALED_LOG_MISMATCH` | DISCRIMINATIVE; V0-A was BLOCKED for ambiguous old assertion |
| `J1-F05-B` | `D05` / `LOG_MATCHES_SEAL` | Three valid chained newline-complete records, digests and independently held manifest all match | Observed archive bytes match trusted seal | **PASS** | `SEALED_LOG_MATCH` | DISCRIMINATIVE; not event authenticity |
| `J1-F05-C` | `D05` / `EVIDENCE_USABLE` | Same mismatched bytes/seal as F05-A, asked whether log can support downstream claims | Evidence compromised; unrelated downstream assertions undecidable | **BLOCKED** | `LOG_UNUSABLE_DOWNSTREAM` | SMOKE_ONLY; different question from LOG_MATCHES_SEAL |
| `J1-F06-A` | `D09` / `DELIVERY` | B0 REGISTERED→RELEASED intent; no trusted R-write outcome or receipt | Actual delivery unknown | **BLOCKED** | `RELEASED_INTENT_NOT_DELIVERY` | SMOKE_ONLY; no observed recipient |
| `J1-F06-B` | `D09` / `WRITE_COMPLETE` | B0 RELEASED intent plus trusted hypothetical wrapper R-write outcome bytes=1, errno=null | Trusted simulated single-byte write returned success | **PASS** | `R_WRITE_COMPLETED_NOT_RECIPIENT_PROOF` | DISCRIMINATIVE; not delivery recipient |
| `J1-F06-C` | `D09` / `WRITE_COMPLETE` | Same contract as F06-B except wrapper R-write result bytes=0 or EPIPE | Trusted simulated syscall did not successfully write one byte | **FAIL** | `R_WRITE_NOT_COMPLETE` | DISCRIMINATIVE; error contrast |
| `J1-F06-D` | `D09` / `WRITE_COMPLETE` | B0 RELEASED plus untrusted NODE_CLAIM_SIM asserts R written, no trusted wrapper result | Claim alone insufficient for syscall success | **BLOCKED** | `UNTRUSTED_WRITE_CLAIM_ONLY` | DISCRIMINATIVE; trust contrast |

**Predeclared expected subject distribution:** PASS=5, FAIL=5, BLOCKED=8. Selected 18 IDs are a **document inventory**. `test_acceptance_verdict=PASS` is conditional on future exact matching of predeclared subject, valid guards/readback, and independent oracle; it is NOT a current run result. `expected_behavior_label` is private to Lane O, not injected as a shortcut into J1.

**Control quality:** `ATTRIBUTION`, `UNIQUE_REGISTRY`, `ZOMBIE_AT_T`, `LOG_MATCHES_SEAL`, `WRITE_COMPLETE` contain contrast verdicts, so a per-assertion constant classifier cannot pass those cases. The other four single-outcome questions are explicitly **SMOKE_ONLY**. A classifier may still overfit this finite synthetic set; no ability or generality claim beyond declared observations.

## 5. Reproducibility and completeness contract (draft, F05)

**No real JSON input or sidecar bytes exist in this stage, so hashes = NOT_MATERIALIZED.** Later fixture content must be uniquely versioned, generated by **Claude Code only after separate owner authorization**, and independently reviewed before any CPU execution.

- JSON candidate canonicalization: UTF-8, Unicode NFC for strings if adopted consistently across parser and serializer, sorted object keys, compact `,`/`:` separators, no NaN/Infinity, integer type check excludes booleans, finite allowed ranges, fixed field names/enums; floating clock inputs excluded in favor of integer ordinal or canonical decimal string. **This is a proposed byte contract, not accepted frozen format.**
- Native registry fixtures must preserve actual `KINDS` (`RUN_START,INTENT,FORKED,REGISTERED,RELEASED,ABORTED,DEAD,RUN_END`) and include complete RUN_START and required lifecycle prerequisite rows unless the fixture explicitly targets a missing record. `CREATED,EXIT,REAPED` are **not** native registry kinds. `pid,starttime` fields are int (not bool); `seq` strictly increasing in selected scope; registered-node duplication does not by itself prove kernel PID reuse.
- Read-back completeness: newline-terminated record files, explicit expected byte length, `seq`/no gaps, full-file SHA-256 and controlled `read_status`; never silently discard torn tail or corrupted rows and then treat resulting subset as complete. A compact internal hash chain is not an independent truth source.
- Sidecar candidate genesis prev digest `"0"×64`, record SHA-256 of canonical JSON excluding `event_digest`, chained `prev_digest`, final seq/head, complete terminating newline, independently held final manifest `full_file_sha256,byte_length,final_seq,last_digest,run_id`. Simulated final seal is an explicitly **trusted test assumption**, not evidence that an actual signer/custodian exists in B0 or G2. Source authenticity and power-loss durability are **out of scope**.
- **Sidecar mismatch outcomes:** when a *trusted* manifest explicitly disagrees with valid readable file, `LOG_MATCHES_SEAL` is **FAIL** (positive observed invariant violation); `EVIDENCE_USABLE` is **BLOCKED** (downstream reliance impossible). If manifest itself is missing/untrusted/unreadable, `LOG_MATCHES_SEAL` is **BLOCKED**, not an invented mismatch FAIL.
- When a future immutable fixture is genuinely materialized, store separate S and O raw files/hashes with a manifest that the independent oracle validates **before** running J1. No fabricated sha256 or future test PASS in this draft.

## 6. Selected vs deferred cards; future acceptance and Claude Code handoff

Historical 14 canonical card IDs (D01…D10 including D03a–e) split D01 into B0/P1, producing 15 **arm-qualified candidates**. This draft selects exactly **six**: `D01-B0`, `D03c`, `D03d`, `D05`, `D07`, `D09`. **Nine** remain `DEFERRED_BY_SCOPE`: `D01-P1`, `D02`, `D03a`, `D03b`, `D03e`, `D04`, `D06`, `D08`, `D10`. DEFERRED means **NOT TESTED**, not PASS. This battery proposes 18 fixture IDs within six selected arms; **actual executed 0/18**.

**Proposed future acceptance — not active:**
- Future J1 test run's `measurement_target=J1_SYNTHETIC_DETECTOR`; `native_B0_safety_status=NOT_EVALUATED_BY_J1`; explicit `scope=SYNTHETIC_CPU_ONLY`, `assertion_id`, `subject_verdict`, `observed_behavior_label` (oracle computed), `test_acceptance_verdict`, `evidence_refs` and `Grok_review_state` for aggregate and every case.
- **Predeclared 18-ID exact set with no unknown/duplicate/skipped IDs**, except a reviewed scope revision may change the set before freeze. Per-test PASS requires correct subject verdict and an intact test instrument; deterministic wrong output or guard breach => test FAIL; unreadable fixture/oracle or missing independent seal => test BLOCKED. A missing fixture makes run **BLOCKED**; FAIL > BLOCKED > PASS. Do not inflate a run by ignoring smoke-only limitations.
- No processes, signals, `os.fork/exec/posix_spawn`, `subprocess`, `multiprocessing`, `wait*`, janitor, `pidfd_send_signal`, GPU or side-effectful Bench import. A future CPU guard shall be **separately designed and authorized**, and its Python-level scope is not kernel attestation. Test runner cannot send Lane O, grade metadata or fixture IDs to J1.
- Keep raw evidence and exact hashes, environment/version/commit, independent oracle result and checkpoint after any **separately authorized future CPU run**. Exit code=0 does not prove correctness. No kernel or descendant process conclusions derive from these synthetic inputs.

**Development responsibility (owner instruction):** ChatGPT prepares requirements/review and acceptance/checkpoints. **Claude Code performs implementation/code changes ONLY upon a later explicit code-stage authorization**. This stage authorizes *writing this document* and discussing the handoff, **not launching Claude Code or implementing code now**. When implementation is separately approved, the Claude Code handoff must pin exact Git SHA, immutable fixture schema and oracle separation, restrict writes to `gate_g2` isolated code paths, require no-execution and separately approved CPU-run stages, and forbid edits to `bench/`, frozen G0/G1/R3, upstream Parcae and model architecture. ChatGPT independently audits its diff and acceptance evidence; Grok review deferred until available.

## 7. Review gates, unresolved questions and ONLY next instruction

| Dimension | This stage's status |
|---|---|
| V0 reviewer issues F01…F06 | **ADDRESSED ON PAPER in V0.1 DRAFT**; actual independent V0.1 review PENDING |
| Fixture spec | Six selected arms, 18 proposed unique IDs; 5 expected limited PASS, 5 expected FAIL, 8 expected BLOCKED; **NOT MATERIALIZED** |
| Assertion discrimination | Five assertions discriminative in selected synthetic evidence; four explicitly **SMOKE_ONLY** |
| Source/trust | Frozen Bench untouched; simulated sensor and seal not real authenticated B0 evidence |
| G2 criteria | **NOT FROZEN / NOT AUTHORIZED** |
| J1 implementation, fixture materialization, CPU run | **NOT TESTED / NOT AUTHORIZED** (future code to Claude Code only if separately approved) |
| REAL | **DESIGN SAFETY BLOCKED / NOT AUTHORIZED**; lawful wait, orphan/no-signal cleanup and containment not closed |
| Grok | **DEFERRED / NOT PERFORMED**, not a Grok PASS |
| O-1…O-15 | **UNDECIDED**; reviewer recommendations do not equal owner-approved decisions |

**Single next instruction:** Independent read-only **J1 CPU SPEC V0.1 DOCUMENT REVIEW** against pinned frozen Bench and V0 F01…F06, checking no fixture-ID/answer leak, source/assumption separation, contrasting outcomes, seal FAIL/BLOCKED semantics, 18-ID inventory and the four SMOKE_ONLY ceilings. Publish findings and a checkpoint without code or CPU execution. **No automatic freeze, implementation, test or REAL.**
