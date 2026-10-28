# E1-A G2 J1 — PF-02 / PF-06 Acceptance Criteria Addendum, DRAFT 001

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-PF02-PF06-ACCEPTANCE-ADDENDUM-001` · 2026-10-28 · **Work mode: DOCUMENTATION ONLY.**  
**Status of this document:** `ADDENDUM DRAFT PREPARED — INDEPENDENT REVIEW PENDING`. It is **not** a frozen criteria set, **not** an owner decision, **not** a fixture, **not** a test plan that may be executed. **NOT TESTED. NO Python, NO CPU/GPU experiment, NO process test, NO S/O bytes, NO hash, NO signature, NO code change.** `FORMAL_ACCEPTANCE_READY` stays `False`; the formal Oracle stays `BLOCKED / NOT_READY`; `G2 REAL BLOCKED`; `Grok DEFERRED / NOT PERFORMED (not a PASS)`; `O-1…O-15`, `OQ-11`, `OQ-12`, `OQ-13` OWNER UNDECIDED.

## 0. Provenance and what this addendum may and may not do

| Item | Value |
|---|---|
| Repository | `leotree2020/OpenMythos` |
| Base branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-cpu-readiness-preflight-review-20261028`, remote HEAD re-verified before work: **`466f28f7b36e4c851f6f4865903a3827e2d3ec5a`** |
| Inputs read | the preflight review checkpoint; `G2_J1_CPU_READINESS_PREFLIGHT_DRAFT_001_20261028.md` (blob `2d913119…`); its independent review (findings `J1-PF-R01 … R04`); `G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md` (blob `9574f906…`, DRAFT, unchanged); J1 source at the base HEAD: `j1/oracle.py 0df6e5da…`, `schema.py 551c4a01…`, `judge.py 8aef00cb…`, `codec.py bb486c92…` (all read-only) |
| Findings resolved on paper by this addendum | `J1-PF-R01` (HIGH) → §2; `J1-PF-R02` (MEDIUM) → §3; `J1-PF-R03` (MEDIUM) → §4 |
| Not changed | V0.1 (18 cases, 5 PASS / 5 FAIL / 8 BLOCKED expected subject verdicts, five discriminative + four SMOKE_ONLY assertions); J1 source; `oracle.FORMAL_ACCEPTANCE_READY`; frozen Bench, Parcae, G0/G1, R3, the model |

Everything below is a **proposal for independent review and owner decision**. Where the J1 source is described, it is described as read, not as run. A statement such as "J1 would return X" is a **source-reading prediction, NOT TESTED**. Nothing here releases PF-02 … PF-09.

## 1. Four independent semantics (never interchangeable)

| Layer | Question it answers | Domain | Computed by | Never implies |
|---|---|---|---|---|
| **Subject verdict** (SV) | What does J1 conclude about the *supplied synthetic evidence* for one assertion? | `PASS / FAIL / BLOCKED`, or **absent** when J1 reports `INPUT_INVALID` (`subject_verdict=None`, `result_kind=INPUT_INVALID`) | J1 (`judge.evaluate`) | That the test passed; a subject FAIL or BLOCKED can be the *correct* answer. Never native-B0 safety (`native_B0_safety_status=NOT_EVALUATED_BY_J1`). |
| **Instrument validity** (IV) | Can the experiment judge J1 at all? Four independently established components: **IV-S** Lane S bytes valid and unaltered; **IV-O** Lane O truth available, independently authored and unaltered; **IV-C** code/fixture/guard binding to the sealed versions; **IV-G** guard evidence present and verifiable | each component `VERIFIED_VALID / VERIFIED_INVALID / UNVERIFIABLE` (IV-G additionally reports the guard finding, §2.2) | the **independent acceptance verifier** (§4), *not* J1 and *not* the executor | J1's own `input_valid` flag is a SUT claim and is **not** IV. Using `schema.validate_input` as the IV-S validator would make J1 grade itself and is therefore forbidden for IV-S. |
| **Case acceptance verdict** (CA) | Did this one case pass the experiment? | `PASS / FAIL / BLOCKED / NOT_RUN` | the independent acceptance verifier, applying §2 | A CA PASS does not mean the assertion's real-world property holds. |
| **Run acceptance verdict** (RA) | Did the whole 18-case suite pass? | `PASS / FAIL / BLOCKED / NOT_RUN` | the independent acceptance verifier, applying §2.4 | Not a count of J1 subject PASSes; not a CLI exit code; never native-B0 or G2 REAL safety. |

Reason codes are machine-readable and live in separate namespaces: `SV-*` (J1 basis codes, already in `judge.py`), `IV-*`, `CA-*`, `RA-*`. A reason code of one namespace never substitutes for another.

**Naming clash to avoid.** The current `oracle.grade_case` field `inline_check_verdict` is a **non-formal demonstration check**; it maps *every* `INPUT_INVALID` to BLOCKED because the oracle cannot know whether the fixture or J1 is at fault. That is deliberately coarser than the taxonomy below and is **not** CA. `oracle.test_acceptance_verdict` and `aggregate` remain unconditionally `BLOCKED / NOT_READY`; this addendum does not change them.

## 2. R01 — error-origin and acceptance-level taxonomy

### 2.1 Inputs to the decision (all established outside J1)

* **Guard finding G** (from IV-G): `VIOLATION_VERIFIED` (a *verified* guard record shows a forbidden action: import of native Bench/Parcae/`os`-process modules, process creation, exec, signal, wait, network, GPU, write outside the declared output area, resource-limit breach — codes `GV-IMPORT`, `GV-PROC`, `GV-NET`, `GV-ENV`, `GV-FS`, `GV-RESOURCE`); `CLEAN_VERIFIED`; `ABSENT_OR_UNVERIFIABLE` (guard output missing, truncated, unsigned/uncustodied, internally inconsistent, or not bound to the sealed code). **A claimed violation from an unverifiable guard is `ABSENT_OR_UNVERIFIABLE`, not `VIOLATION_VERIFIED`.**
* **Instrument state I**: `ALL_VALID` (IV-S, IV-O, IV-C all `VERIFIED_VALID`) or `NOT_ALL_VALID` (any component `VERIFIED_INVALID` or `UNVERIFIABLE`).
* **J1 outcome J** (observed under a `CLEAN_VERIFIED` guard): `MATCH` — J1 produced a subject verdict equal to the O-expected verdict **and** its output satisfies the case's required-basis and scope-label conditions (§3.4); `MISMATCH` — a subject verdict that differs from O, or a right verdict that violates the required-basis / scope conditions; `NO_VERDICT` — J1 reported `INPUT_INVALID`, raised, timed out, produced nothing, or produced a malformed/unparseable output.

### 2.2 Ordered decision rules for one case (first matching rule wins; every rule that also applies is recorded in `reasons`)

| # | Condition | CA | Primary reason code | Why |
|---|---|---|---|---|
| 1 | G = `VIOLATION_VERIFIED` | **FAIL** | `CA-FAIL-GUARD-VIOLATION` (+ `GV-*`) | An observed violation is a positive observation about the execution, independent of the fixture's validity. Precedence FAIL > BLOCKED (V0.1 §6). |
| 2 | G = `ABSENT_OR_UNVERIFIABLE` | **BLOCKED** | `CA-BLOCK-GUARD-EVIDENCE` | Nothing can be trusted about the execution context, so neither a match nor a mismatch is an established observation. |
| 3 | I = `NOT_ALL_VALID` | **BLOCKED** | `CA-BLOCK-S-INVALID` / `-S-UNVERIFIABLE` / `-O-UNAVAILABLE` / `-O-UNVERIFIED` / `-CUSTODY` / `-CODE-BINDING` | The instrument cannot support a correctness judgment, **even if J1 appears to answer "correctly"**. This closes the review-F01 hole: a broken fixture never yields PASS. |
| 4 | I = `ALL_VALID` and J = `NO_VERDICT` | **FAIL** | `CA-FAIL-SUT-REFUSED-VALID-INPUT` (J1 said `INPUT_INVALID`), `CA-FAIL-SUT-EXCEPTION`, `CA-FAIL-SUT-NO-OUTPUT`, `CA-FAIL-SUT-MALFORMED-OUTPUT`, `CA-FAIL-SUT-TIMEOUT` | The input is independently valid, so a refusal, crash or silence is a deterministic fault of the SUT. |
| 5 | I = `ALL_VALID` and J = `MISMATCH` | **FAIL** | `CA-FAIL-VERDICT-MISMATCH` / `CA-FAIL-BASIS-MISMATCH` / `CA-FAIL-SCOPE-LABEL` | Independent truth disagrees with a valid run. |
| 6 | I = `ALL_VALID` and J = `MATCH` and G = `CLEAN_VERIFIED` | **PASS** (future only) | `CA-PASS-MATCH` | All required premises hold. SMOKE_ONLY assertions additionally carry `CA-PASS-SMOKE-ONLY-NO-GENERAL-CLAIM`. |
| — | the case was not executed | `NOT_RUN` | `CA-NOT-RUN` | Never a subject verdict; counts as missing at run level. |

**Exhaustive grid (3 guard states × 2 instrument states × 3 J1 outcomes = 18 cells; every cell has exactly one verdict):**

| G \ I, J | I valid & J=MATCH | I valid & J=MISMATCH | I valid & J=NO_VERDICT | I not valid & J=MATCH | I not valid & J=MISMATCH | I not valid & J=NO_VERDICT |
|---|---|---|---|---|---|---|
| `VIOLATION_VERIFIED` | FAIL (1) | FAIL (1) | FAIL (1) | FAIL (1) | FAIL (1) | FAIL (1) |
| `ABSENT_OR_UNVERIFIABLE` | BLOCKED (2) | BLOCKED (2) | BLOCKED (2) | BLOCKED (2) | BLOCKED (2) | BLOCKED (2) |
| `CLEAN_VERIFIED` | **PASS** (6) | FAIL (5) | FAIL (4) | BLOCKED (3) | BLOCKED (3) | BLOCKED (3) |

The only PASS cell is `CLEAN_VERIFIED × valid × MATCH`. The matrix has no contradiction: rows 1–2 depend only on G, row 3 only on I once G is clean, rows 4–6 only on J once both are established.

**The six situations requested for R01, mapped:**

| Situation | CA |
|---|---|
| Independently verified Lane S / O invalid (malformed, unreadable, unsealed, altered, truth unavailable) → test BLOCKED | BLOCKED (rule 3) |
| Input independently valid, but J1 wrongly rejects it (`INPUT_INVALID`, exception, no output) → test FAIL | FAIL (rule 4) |
| Input valid, J1 verdict differs from the independent truth → test FAIL | FAIL (rule 5) |
| Trusted guard actually detects a violation → test FAIL | FAIL (rule 1) |
| Guard evidence missing or unverifiable → test BLOCKED | BLOCKED (rule 2) |
| Expected result matches and all premises hold → future test PASS | PASS (rule 6) |

**Designed-invalid inputs are not J1 cases.** All 18 V0.1 cases are valid-input cases. A deliberately malformed input (to prove the validator or J1 rejects it) would be a separate, separately versioned *negative control of the instrument* (§4.5), whose expected outcome is stated for the verifier, not for J1's 18-case suite. Nothing in the 18 expects `INPUT_INVALID`; a J1 `INPUT_INVALID` on any of the 18 is, under rule 4, a FAIL.

### 2.3 What this does to J1's own flags

J1's `input_valid`, `result_kind`, `input_diagnostics` and the `INPUT_INVALID` basis code are **observations about J1's behaviour**, consumed only in rule 4. They never feed IV. Conversely IV never changes what J1 outputs.

### 2.4 Run acceptance verdict

| Condition (first match wins) | RA | Reason |
|---|---|---|
| any case CA = FAIL | **FAIL** | FAIL > BLOCKED > PASS (V0.1 §6) |
| the manifest of 18 ids is not exactly the pinned 18 (missing, duplicate, unknown, renamed, added) | **BLOCKED** (or FAIL under the line above) | `RA-BLOCK-ID-SET` |
| any case CA = BLOCKED or NOT_RUN | **BLOCKED** | `RA-BLOCK-CASE` |
| run-level custody/binding not verified: sealed 18-case manifest, code SHA, guard version, evidence closure, absence of post-run edits | **BLOCKED** | `RA-BLOCK-CUSTODY` |
| all 18 CA = PASS and all run-level premises verified | **PASS** (future only) | `RA-PASS-18-OF-18` |

A run PASS report must state, separately, how many PASS cases are discriminative and how many SMOKE_ONLY, repeat the scope labels (`J1_SYNTHETIC_DETECTOR`, `NOT_EVALUATED_BY_J1`, `SYNTHETIC_CPU_ONLY`), and say that it is not evidence of native-B0, G2 REAL, Parcae or architecture properties. No caller-supplied grade row, `dataclass`, hash written by the writer of the artefact, or in-memory structure can establish any premise (§4).

### 2.5 Items for reviewers (not decided here)

* **D-R01-1** Whether a J1 uncaught exception under a clean guard is FAIL (proposed, rule 4) or BLOCKED.
* **D-R01-2** Whether the five `GV-*` classes are all FAIL (proposed) or whether `GV-RESOURCE` is a separate safety category reported as FAIL with its own code.
* **D-R01-3** Who implements the IV-S validator independently of `schema.py` (second implementation vs byte-level manual checklist).
* **D-R01-4** Whether required-basis conditions (§3.4) are graded at all, or the 18 cases are verdict-only.

## 3. R02 — design-level S/O manifest for the 18 cases

### 3.1 Global contract (applies to every case)

* **Version labels (DRAFT, not frozen):** `J1-S-SCHEMA-0.1` = the closed Lane S whitelist of `j1/schema.py` at the base HEAD (record fields `source_handle, event_kind, monotonic_order, read_status, [node_token, identity{pid,starttime,[ppid,boot_id,pidns]}, gate_token, raw_fields]`; per-kind closed `raw_fields`; no floats; `bool` is never an `int`). `J1-CANON-0.1` = the byte contract of `j1/codec.py`: UTF-8, strings already NFC (non-NFC is rejected, never normalised), sorted keys, separators `,` `:`, `ensure_ascii=False`, no NaN/Infinity/floats, integers only, depth ≤ 8; a sidecar is one canonical record per line, each newline-terminated, record shape `{seq, prev_digest, kind, body, event_digest}`, genesis `prev_digest = 64 × "0"`, `event_digest = sha256(canonical_json(record without event_digest))`. **These labels fix nothing until an owner freeze.**
* **Lane S artefact (one per case):** one canonical JSON document `{assertion_id, subject_observables[], declared_trust_model{}}` whose file name and every string value are **opaque and case-neutral** (no `J1-F…` shape, no verdict word, no path hints). **Lane O artefact (one per case, stored elsewhere):** `{case_id, canonical_card, assertion_id, expected_subject_verdict, truth statement, required evidence basis, S-artefact binding, provenance}`.
* **One trust map for all 18 cases** (so the map cannot encode the case), `TRUST-MAP-0.1`, handle strings fixed **per role**, not per case:

| Handle | Role | Allowed kinds (ceiling) | Tier | Authority |
|---|---|---|---|---|
| `hL` | `B0_LEDGER` | `RUN_START, INTENT, FORKED, REGISTERED, RELEASED, ABORTED, DEAD, RUN_END` | `SYNTHETIC_B0_SHAPED_TRANSCRIPT` | yes (hypothetical) |
| `hN` | `NODE_CLAIM_SIM` | `NODE_CLAIM` | `UNTRUSTED_CLAIM` | never |
| `hK` | `KERNEL_SNAPSHOT_SIM` | `KERNEL_SNAPSHOT` | `SYNTHETIC_ASSUMPTION` | yes (hypothetical) |
| `hW` | `G2_WITNESS_SIM` | `GATE_CHILD_OBSERVATION` | `SYNTHETIC_ASSUMPTION` | yes (hypothetical) |
| `hR` | `G2_WRAP_SIM` | `R_WRITE_RESULT` | `SYNTHETIC_ASSUMPTION` | yes (hypothetical) |
| `hM` | `SEAL_MANIFEST_SIM` | `SEAL_MANIFEST` | `SYNTHETIC_ASSUMPTION` | yes (hypothetical) |
| `hG` | `SUBJECT_LOG_READBACK` | `LOG_READBACK` | `SUBJECT_ARTIFACT` | never |

  Every entry has `synthetic_assumption = true`. The map is a **hypothetical contract declared by an external harness; J1 does not and cannot authenticate it** (OQ-11/OQ-12); the real origin/seal of the map is part of §4.
* **Constants shared by all cases (case-neutral):** `run_id = "run-synth-01"`, `observer_pid = 300`, nodes `nA` / `nB`, gates `gate-A` / `gate-B`, fictional identities `K = (4100, 100)` creator, `Q = (4101, 101)`, `G = (4102, 102)`; ledger `creator = "O"`.
* **Ordinal and readback rules:** every record has `read_status = OK`. The ledger handle `hL` has `monotonic_order` contiguous from 1. For every other handle, orders are unique per handle; cross-source order is the harness-asserted ordinal in the tables below (not a clock). **Because the ledger must stay contiguous from 1, every non-ledger record is numbered after the last ledger row of its case**; cross-source order in these 18 cases therefore only ever means "after the ledger", and the ATTRIBUTION cases carry no `RELEASED` row (J1's timing code is then "not comparable"; the retrospective claim is unchanged). A torn / non-OK row is never present in these 18 cases (non-OK rows are instrument-negative controls, §4.5).
* **Ledger template `LT(nodes…)`** (when a case says "ledger"): `1 RUN_START{run_id, observer_pid}` → per node `INTENT{creator:"O"}` → `FORKED{pid}` → `REGISTERED{pid, starttime, ppid=4100, gate_token}`, orders consecutive, then the listed extra rows. `FORKED.raw_fields.pid` is always present (correction 003); `FORKED` carries no identity / starttime (the native observer may record `None`). `FORKED.pid` equals the same node's `REGISTERED.pid` in every case (OQ-13 is **not** being decided: the 18 cases simply never exercise a mismatch).
* **S/O private relation.** The runner holds, privately and only in Lane O, the map `opaque S artefact id ↔ case_id`. The S artefact contains no case id. The binding value is the SHA-256 of the canonical S bytes **written at materialisation time (`NOT_MATERIALIZED`, placeholder `S_DIGEST_TBD`)**; the O record's own digest is `O_DIGEST_TBD`. Digests are integrity metadata only (§4.3).
* **Paired-case rule.** Cases that share observables differ in exactly one stated element (the metamorphic intent of V0.1): F01-A/C, F03-A/B, F04-B/C, F05-A/B/C, F06-B/C.

### 3.2 Per-case manifest (18/18)

Notation: `hX#n` = handle `hX`, order `n` (this is also how J1 names a supporting observable). "Expected basis" lists candidate required-basis evidence in J1's current vocabulary — **derived by reading `judge.py`, NOT RUN, vocabulary-coupled (D-R01-4)**; the semantic O statement is the normative part.

**Family F01 — `D03c`, assertion `ATTRIBUTION`**

| O-only ID | Lane S events (handle#order: kind, key fields) | Lane O independent truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F01-A` | `hL#1..4` LT(nA with REGISTERED = **Q**, `gate-A`; FORKED pid 4101); `hW#5` GATE_CHILD_OBSERVATION node nA, gate-A, identity **G**; no RELEASED row (so the J1 timing code is "not comparable") | G ≠ Q under a trusted simulated witness for the same gate → **FAIL** | `ATTRIBUTION_MISMATCH_OBSERVED_UNDER_SIMULATED_TRUST`, `RETROSPECTIVE_AGREEMENT_NOT_PREVENT_PROOF`, `WITNESS_ORDER_NOT_COMPARABLE_NO_RELEASED_RECORD`; refs `hL#4`, `hW#5` | exact bytes, S/O digests, O-truth review |
| `J1-F01-B` | as F01-A but **without** `hW#5` | witness absent; O privately knows the child is G; J1 never sees it → **BLOCKED** | `NO_TRUSTED_GATE_CHILD_WITNESS`; ref `hL#4` | same |
| `J1-F01-C` | as F01-A but REGISTERED = **G** (FORKED pid 4102, REGISTERED (4102,102)) | agreement under the simulated witness → **PASS** (observed consistency only) | `ATTRIBUTION_AGREEMENT_OBSERVED_UNDER_SIMULATED_TRUST`, `RETROSPECTIVE_AGREEMENT_NOT_PREVENT_PROOF`, `WITNESS_ORDER_NOT_COMPARABLE_NO_RELEASED_RECORD`; refs `hL#4`, `hW#5` | same |
| `J1-F01-D` | REGISTERED = Q, `gate-A`; **no `hW`**; `hN#5` NODE_CLAIM node nA, `claim_kind=GATE_CHILD_IDENTITY`, pid 4102, starttime 102; no RELEASED row | untrusted claim cannot stand in for a witness → **BLOCKED** | `NO_TRUSTED_GATE_CHILD_WITNESS`, `UNTRUSTED_NODE_CLAIM_NOT_EVIDENCE`; ref `hL#4` | same |

**Family F02 — `D03d`, assertion `UNIQUE_REGISTRY`**

| O-only ID | Lane S events | Lane O truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F02-A` | `hL#1..7` LT(nA, nB) with both REGISTERED = (4101,101) (FORKED pid 4101 both), no optional boot/pidns | duplicate `(pid, starttime)` across distinct nodes → **FAIL** | `DUPLICATE_PID_STARTTIME_ACROSS_NODES`; refs `hL#4`, `hL#7` | PF-02 freeze |
| `J1-F02-B` | `hL#1..7` LT(nA = (4101,101), nB = (4102,102)); FORKED pids 4101 / 4102 | no duplicate in the finite, internally sound set → **PASS** | `NO_DUPLICATE_IN_FINITE_SUPPLIED_VALIDATED_SET`, `ORIGINAL_LOG_COMPLETENESS_NOT_ASSERTED`; refs `hL#4`, `hL#7` | PASS is scoped to the finite set; OQ-4/OQ-13 |

**Family F03 — `D01-B0`, assertion `PREVENT_PROOF` (SMOKE_ONLY)**

| O-only ID | Lane S events | Lane O truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F03-A` | `hL#1..4` LT(nA = Q, gate-A), `hL#5` RELEASED nA | no pre-release gate-hold witness exists in the V0.1 trust table → **BLOCKED** | `SMOKE_ONLY_NO_PASS_PATH_IN_V0_1`, `B0_RELEASED_IS_INTENT_NOT_DELIVERY`, `NO_PRE_RELEASE_WITNESS_SOURCE_IN_V0_1`; ref `hL#5` | no PASS path by design (OQ-5) |
| `J1-F03-B` | F03-A plus `hN#6` NODE_CLAIM node nA, `claim_kind=READY` (post-release, untrusted) | a later READY cannot substitute the missing pre-release observation → **BLOCKED** | as F03-A + `UNTRUSTED_READY_CLAIM_NOT_PREVENTION` | same |

**Family F04 — `D07`, assertions `LAWFUL_REAP` (SMOKE_ONLY) and `ZOMBIE_AT_T`**

| O-only ID | Lane S events | Lane O truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F04-A` (`LAWFUL_REAP`) | `hL#1..4` LT(nA = Q); `hL#5` DEAD nA; `hK#6` KERNEL_SNAPSHOT identity Q, state `Z`; `hN#7` NODE_CLAIM node nA, `claim_kind=WAIT_RESULT` | zombie, DEAD and an ECHILD-type claim are not a lawful wait → **BLOCKED** | `DEAD_RECORD_IS_NOT_REAP`, `ZOMBIE_IS_NOT_REAP`, `UNTRUSTED_WAIT_OR_ECHILD_CLAIM_NOT_REAP`, `NO_TRUSTED_WAIT_WITNESS_SOURCE_IN_V0_1`; refs `hL#5`, `hK#6` | no PASS path (OQ-5) |
| `J1-F04-B` (`ZOMBIE_AT_T`) | `hL#1..4` LT(nA = Q) (pins the identity); **exactly one** `hK#5` snapshot, identity Q, state `Z` | Z at the single snapshot → **PASS** (state at T only; not a reap) | `ZOMBIE_STATE_OBSERVED_AT_T`, `ZOMBIE_IS_NOT_LAWFUL_REAP`, `IDENTITY_PINNED_BY_B0_REGISTERED`; ref `hK#5` | OQ-1: exactly one snapshot is a design constraint |
| `J1-F04-C` (`ZOMBIE_AT_T`) | as F04-B with state `S` | not Z at T → **FAIL** | `NOT_ZOMBIE_AT_T`; ref `hK#5` | same |

**Family F05 — `D05`, assertions `LOG_MATCHES_SEAL` and `EVIDENCE_USABLE` (SMOKE_ONLY)**

| O-only ID | Lane S events | Lane O truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F05-A` (`LOG_MATCHES_SEAL`) | `hG#1` LOG_READBACK: canonical sidecar of **2** chained records, `run_id=run-synth-01`; `hM#2` SEAL_MANIFEST sealing a **3**-record chain (sha256 / byte_length / final_seq=3 / last_digest of the 3-record file, same run id) | the trusted manifest positively disagrees with a valid readable log → **FAIL** | `SEAL_BYTE_LENGTH_DIFFERS`, `SEAL_FULL_FILE_SHA256_DIFFERS`; refs `hG#1`, `hM#2` | sidecar record bodies authored later (OQ-3/OQ-7) |
| `J1-F05-B` (`LOG_MATCHES_SEAL`) | `hG#1` LOG_READBACK: canonical **3**-record chain; `hM#2` manifest of exactly those bytes | bytes, seq, head and run match → **PASS** (integrity of bytes only) | `SEAL_BYTES_CHAIN_AND_MANIFEST_AGREE`; refs `hG#1`, `hM#2` | no real signer/custodian |
| `J1-F05-C` (`EVIDENCE_USABLE`) | **identical observables and trust map to F05-A**; only `assertion_id` differs | a mismatched log cannot support downstream claims → **BLOCKED** | `LOG_SEAL_MISMATCH_DOWNSTREAM_UNUSABLE`, `SMOKE_ONLY_NO_PASS_PATH_IN_V0_1` | no PASS path (OQ-5) |

**Family F06 — `D09`, assertions `DELIVERY` (SMOKE_ONLY) and `WRITE_COMPLETE`**

| O-only ID | Lane S events | Lane O truth / expected SV | Expected basis & refs | Open items |
|---|---|---|---|---|
| `J1-F06-A` (`DELIVERY`) | `hL#1..4` LT(nA = G), `hL#5` RELEASED nA; no write result, no receipt | RELEASED is intent, not delivery → **BLOCKED** | `B0_RELEASED_IS_INTENT_NOT_DELIVERY`, `NO_TRUSTED_RECIPIENT_RECEIPT_SOURCE_IN_V0_1`; ref `hL#5` | no PASS path (OQ-5) |
| `J1-F06-B` (`WRITE_COMPLETE`) | `hL#1..5` as F06-A; `hR#6` R_WRITE_RESULT node nA, `bytes=1`, `errno=null`, `byte="R"` | trusted simulated wrapper recorded a 1-byte write → **PASS** (not recipient proof) | `R_WRITE_COMPLETED_NOT_RECIPIENT_PROOF`, `B0_RELEASED_IS_INTENT_NOT_DELIVERY`; refs `hL#5`, `hR#6` | wrapper trust is hypothetical |
| `J1-F06-C` (`WRITE_COMPLETE`) | as F06-B with `bytes=0`, `errno="EPIPE"` | trusted wrapper recorded no completed write → **FAIL** | `R_WRITE_NOT_COMPLETE`; refs `hL#5`, `hR#6` | same |
| `J1-F06-D` (`WRITE_COMPLETE`) | `hL#1..5` as F06-A; `hN#6` NODE_CLAIM node nA, `claim_kind=R_WRITTEN`; **no `hR`** | an untrusted claim does not establish a syscall → **BLOCKED** | `NO_TRUSTED_WRAPPER_RESULT`, `UNTRUSTED_WRITE_CLAIM_NOT_EVIDENCE`; ref `hL#5` | same |

**Coverage and invariants (checked on this page, not by running anything):** 18 unique ids = 4 + 2 + 2 + 3 + 3 + 4; expected subject verdicts **PASS = 5** (`F01-C, F02-B, F04-B, F05-B, F06-B`), **FAIL = 5** (`F01-A, F02-A, F04-C, F05-A, F06-C`), **BLOCKED = 8** (`F01-B, F01-D, F03-A, F03-B, F04-A, F05-C, F06-A, F06-D`) — identical to V0.1 and to `oracle.SPEC_V0_1_INVENTORY`; five discriminative assertions each have a contrasting pair, four SMOKE_ONLY assertions have only BLOCKED. These are **expected** subject verdicts of a future experiment, never measured results.

### 3.3 Reading the design against the J1 source (prediction, NOT RUN)

Walking each row through `judge.py` / `schema.py` as read at the base HEAD, the listed events satisfy the closed schema (all `read_status OK`, opaque handles in the trust map, per-kind `raw_fields` keys valid, `FORKED.raw_fields.pid` present) and the handlers' preconditions (explicit identical `gate_token` on REGISTERED and witness for F01; `RUN_START` metadata, contiguity, creator `O`, INTENT first, FORKED pid for F02; one snapshot for F04; canonical chain and 5-field manifest for F05; a `RELEASED` for the wrapper's node in F06). This is a design consistency check, **not a test**. A later independent static pass should repeat it; any disagreement is a design or source defect, to be reported, not silently adjusted.

### 3.4 Acceptance conditions beyond the verdict (proposals; D-R01-4)

For a CA PASS (rule 6), besides `subject_verdict == expected`: (a) `input_valid = true`, `result_kind = SUBJECT_VERDICT`, no diagnostics; (b) the three scope labels present and exact; (c) `coverage` is `SMOKE_ONLY` exactly for the four smoke assertions and such a case never carries `PASS`; (d) a PASS carries the assertion's `accepted_claim`; (e) *optional, if the owner chooses to grade basis*: the O-listed required-basis codes ⊆ J1's `evidence_basis_codes` and the O-listed refs ⊆ `supporting_observable_refs`. A right verdict for the wrong reason would otherwise pass (rule 5 → `CA-FAIL-BASIS-MISMATCH`). Option (e) couples O to J1's vocabulary; the alternative is verdict-only.

### 3.5 What is explicitly not yet specified (per case: unfinished)

Exact canonical S bytes; sidecar record bodies; actual digests; O-truth review sign-off; the independent S validator (D-R01-3); the custody artefacts (§4); the guard and runner; the trust-map origin. Every row above is therefore `NOT MATERIALIZED / NOT TESTED`.

## 4. R03 — independent truth and evidence custody

### 4.1 Roles (functional, not personal; the owner assigns them)

| Role | Responsibility | Must NOT |
|---|---|---|
| **S Author** (SA) | writes the Lane S artefacts from this manifest, case-neutral and opaque | see or derive S from J1 output; author O truth for the same case alone; hold custody keys |
| **O Truth Reviewer** (OTR) | authors / adjudicates the expected verdict and required evidence from the V0.1 semantics **without running J1**; signs the O record | derive any truth from J1's behaviour; be the J1 code developer; be the sole reviewer of its own authored S |
| **Trusted Custodian** (TC) | seals S, O, code, guard and trust-map artefacts into the custody manifest; publishes the digest and seal over a channel the executor cannot write; stores read-only originals | execute J1; edit sealed artefacts after sealing; share keys with SA, OTR or EX |
| **Executor** (EX) | runs the reviewed runner under the reviewed guard, only with the exact authorised command, and hands raw output to TC | author S/O, hold seal keys, edit raw outputs, re-run silently, grade |
| **Independent Acceptance Verifier** (IAV) | re-verifies seals and readbacks, validates S with an implementation independent of J1, applies §2 and issues CA / RA | be EX, SA, or the J1 developer; trust any digest stored by the party that controls the artefact |
| Owner | assigns roles, approves freeze and each stage permission | — |
| J1 Code Developer / Independent Static Reviewer | write / review source only | act as OTR or IAV for the same artefacts they wrote or reviewed as developer |

At least SA ≠ OTR for each case, TC ≠ EX, IAV ≠ EX, IAV ≠ J1 developer, OTR ≠ J1 developer. With a small team (several of these are AI sessions) any collapse of two roles into one party must be **recorded as a limitation**, and the dependent claim downgraded (e.g. `CA-BLOCK-CUSTODY` until the owner accepts the limitation explicitly).

### 4.2 Evidence items and what each can establish

| Evidence item | Produced by | Held by | Independently verified by | Can establish | Cannot establish |
|---|---|---|---|---|---|
| S artefacts (18) | SA | TC (sealed) | IAV (own validator + byte-level readback) | IV-S | truth of any synthetic claim |
| O records (18) + truth rationale | OTR | TC (sealed, separate from S) | IAV (re-derives expected verdict from V0.1 semantics, not from J1) | IV-O | that J1 is right |
| Trust map | harness owner + OTR | TC | IAV | IV-C (which roles/ceilings were declared) | that the roles are real (hypothetical contract) |
| Code snapshot (J1 + runner) | developer | TC (commit + seal) | IAV (hash of exactly the executed files) | IV-C | correctness of the code |
| Guard/runner definition and policy | developer, reviewed | TC | IAV | IV-C | that the guard is effective |
| Raw outputs, stdout/stderr, exit code, guard report | EX | handed to TC | IAV (completeness against the manifest) | IV-G, J | that the output is correct |
| Custody manifest + seal | TC | TC / owner channel | IAV | immutability since sealing | event authenticity |

### 4.3 Digest, seal, signature — and what SHA-256 is not

* **SHA-256 detects change of bytes. It is not proof of independent authenticity.** A digest stored next to the artefact, or computed and stored by the same party that can rewrite the artefact, authenticates nothing: whoever alters the file alters the digest. The same holds for a Git commit SHA (a hash over content and history), for the in-memory `dataclass`, and for a role string such as `synthetic_assumption = true`.
* Independence therefore needs a **trust root outside the writers**: (a) a signature by a key that SA, OTR and EX do not hold (owner- or TC-held key, kept outside the session and the repository), **or** (b) out-of-band publication of the manifest digest by TC / the owner over a channel EX cannot write, recorded before the run, **or** (c) an equivalent owner-approved scheme. The choice is **open (D-R03-1)**; this addendum does not select, create or simulate any key, signature or digest. Where no trust root exists, every custody-dependent premise is `UNVERIFIABLE` and the case is `CA-BLOCK-CUSTODY` (rule 3).
* Sidecar hashes (`event_digest`, the seal manifest inside Lane S) are *artefacts of the experiment*, not custody evidence: matching them proves bytes equal bytes, never that a kernel event occurred or who wrote the log.

### 4.4 Sealing and verification sequence (future; each step needs its own authorisation)

1. **Pre-run seal.** SA and OTR deliver S and O separately; the 18-id manifest, trust map, code snapshot, runner/guard policy and criteria version are listed in one custody manifest; TC seals it and publishes the trust-root evidence (§4.3). Nothing is run before this.
2. **Pre-run verification.** IAV re-reads every artefact completely, re-computes digests, validates S with its independent validator, re-derives O, checks the 18 ids / 5-5-8 distribution, and records IV-S / IV-O / IV-C. Any `UNVERIFIABLE` or `INVALID` → the affected cases are BLOCKED before execution (the executor is told not to proceed, or the result is not eligible for PASS).
3. **Execution.** EX runs exactly the authorised command; raw outputs and the guard report go straight to TC.
4. **Post-run seal and verification.** TC seals outputs; IAV verifies completeness (18 outputs, no extras), binds outputs to the sealed code and fixtures, evaluates the guard report (IV-G), then applies §2 case by case and §2.4 once.
5. **Archive.** Git head, environment and Python/stdlib versions, exact command, inputs and outputs with their digests, expected vs actual per case, limitations, role assignments and any recorded role collapse, next instruction. A failure is preserved, never auto-patched.

### 4.5 Tamper and negative controls for the verifier (instrument tests, not J1 cases)

The verifier (IAV) must itself be shown to refuse bad evidence. Each control states the **required outcome of the verification**; none has been executed, designed as bytes, or authorised.

| ID | Tamper / defect | Required outcome |
|---|---|---|
| NC-01 | one S artefact truncated or one byte changed after sealing | affected case BLOCKED (`CA-BLOCK-S-INVALID`) |
| NC-02 | two S artefacts swapped between cases | affected cases BLOCKED (S↔O binding broken) |
| NC-03 | O expected verdict changed after sealing (e.g. F01-A FAIL → PASS) | BLOCKED (`CA-BLOCK-O-UNVERIFIED`) |
| NC-04 | digest in the custody manifest altered together with the file by the writer | BLOCKED if no trust root exists; otherwise detected by the seal |
| NC-05 | a case missing / a 19th case added / a duplicated id / a renamed id | RA BLOCKED (`RA-BLOCK-ID-SET`) |
| NC-06 | eighteen forged PASS grade rows without sealed S/O/outputs | RA BLOCKED (never PASS) |
| NC-07 | guard report missing, truncated, or not bound to the sealed code | affected cases BLOCKED (`CA-BLOCK-GUARD-EVIDENCE`) |
| NC-08 | guard report claims clean but its own record is internally inconsistent | BLOCKED (unverifiable), not PASS |
| NC-09 | verified guard record shows a forbidden import / process / network / GPU / write | FAIL (`CA-FAIL-GUARD-VIOLATION`), never PASS |
| NC-10 | attestation signed or published by the wrong role, or replayed from a different code SHA | BLOCKED (`CA-BLOCK-CUSTODY` / `-CODE-BINDING`) |
| NC-11 | the executor edits an output after the run, or re-runs silently | BLOCKED (`RA-BLOCK-CUSTODY`) |
| NC-12 | S, O and the digest written by one party only | BLOCKED, role collapse recorded |
| NC-13 | J1 given a **valid** S artefact answers `INPUT_INVALID` | FAIL (`CA-FAIL-SUT-REFUSED-VALID-INPUT`) — the SUT-side counterpart of NC-01 |
| NC-14 | independently invalid S (bad type, forbidden Lane-O token) | BLOCKED by IV-S before or regardless of J1; a J1 `INPUT_INVALID` there must not become a PASS |

## 5. Self-check of this addendum (document level; nothing executed)

| Check | Result |
|---|---|
| R01 matrix complete and non-contradictory | 18-cell grid, exactly one verdict per cell, one PASS cell; the six requested situations map to rules 1–6 |
| R02 covers 18/18 cases individually | §3.2 lists all 18 ids with S events, trust handles, ordinals, O truth, expected SV, basis, refs and open items; 5/5/8 verified by counting |
| R03 roles and evidence sources explicit | §4.1–§4.5; SHA-256 explicitly not an authenticity proof; trust-root choice left open |
| V0.1 expectations unchanged | all 18 expected subject verdicts reproduced from V0.1 / `oracle.SPEC_V0_1_INVENTORY` |
| Oracle unlocked? | No: `FORMAL_ACCEPTANCE_READY = False`, formal verdicts `BLOCKED / NOT_READY` |
| Scope of the Git diff | Markdown only (this file, a new checkpoint, navigation appends) |
| Experiments run | none: all NOT TESTED |

## 6. Open decisions and unresolved issues (nothing decided silently)

* **D-R01-1 … D-R01-4** (§2.5); **D-R03-1** trust-root mechanism (§4.3); **D-R03-2** role assignment and acceptance of any recorded role collapse; **D-R03-3** whether IAV is a separate implementation or a manual checklist plus a second implementation.
* **D-R02-1** whether `FORKED.pid` is also included in the F01/F03/F04/F06 ledgers (this draft includes it uniformly); **D-R02-2** constants (`run_id`, pids) as stated; **D-R02-3** sidecar record bodies; **D-R02-4** whether paired cases are materialised from a shared base to guarantee the single-difference property.
* **OQ-13** (FORKED.pid vs REGISTERED.pid equality) is not decided and not exercised; **OQ-11** (gate association is an unauthenticated synthetic field), **OQ-12** (formal acceptance prerequisites), **OQ-1** (one snapshot only, by design), OQ-2…OQ-10 remain as recorded.
* PF-02 / PF-03 / PF-04 / PF-05 / PF-06 / PF-08 stay `BLOCKED`; PF-07 / PF-09 `NOT TESTED / NOT AUTHORIZED`; `G2 REAL BLOCKED`; the four SMOKE_ONLY assertions stay non-discriminative; `Grok DEFERRED / NOT PERFORMED`; `O-1…O-15` OWNER UNDECIDED.

## 7. Only next instruction

Submit this **document-only addendum** to **ChatGPT** for independent source-grounded review and to **Grok** for cross-review when available (a Grok result must be recorded only if actually supplied; absence is `DEFERRED`, never a PASS). Disagreements are kept open and resolved by a proposed minimal controlled experiment, not by choosing one reviewer. **Do not** implement code, materialise any S/O artefact, compute any hash, create a signature, freeze criteria, unlock the Oracle, run Python/CPU/GPU, or enter G2 REAL without a separate owner authorisation.
