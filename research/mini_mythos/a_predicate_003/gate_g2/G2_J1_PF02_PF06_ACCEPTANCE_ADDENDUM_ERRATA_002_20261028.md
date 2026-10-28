# E1-A G2 J1 — PF-02 / PF-06 Acceptance Criteria Addendum DRAFT 001 — ERRATA 002

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-PF02-PF06-ADDENDUM-ERRATA-002` · 2026-10-28 · **Work mode: DOCUMENTATION ONLY.**  
**Status:** `ERRATA 002 DRAFT PREPARED — INDEPENDENT REVIEW PENDING`. Review disposition being answered: **`DOCUMENT REVIEW CHANGES REQUIRED BEFORE CRITERIA FREEZE`** for addendum commit `ac5806f004242c6e018151d5543f7106fcf92829`.  
**Still true:** `CRITERIA NOT FROZEN`; `CPU NOT TESTED`; `FORMAL ACCEPTANCE BLOCKED / NOT_READY` (`oracle.FORMAL_ACCEPTANCE_READY=False`, untouched); `18 S/O FIXTURES NOT MATERIALIZED`; no hash, signature or fixture exists; `G2 REAL BLOCKED`; `Grok DEFERRED / NOT PERFORMED (not a PASS)`; `O-1…O-15`, `OQ-11…OQ-13` OWNER UNDECIDED. Nothing in this document was executed (no Python, no experiment).

## 0. Provenance and honest scope note

| Item | Value |
|---|---|
| Repository / reviewed commit | `leotree2020/OpenMythos` @ `ac5806f004242c6e018151d5543f7106fcf92829` (branch `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-addendum-20261028`, re-verified on the remote before work) |
| Base addendum (unchanged by this errata) | `a_predicate_003/gate_g2/G2_J1_PF02_PF06_ACCEPTANCE_CRITERIA_ADDENDUM_DRAFT_001_20261028.md` |
| J1 source consulted read-only | `j1/codec.py` (`compare_seal`, `parse_sidecar`), `j1/judge.py` (`_seal_outcome`), `j1/schema.py` (`NODE_CLAIM` schema, `CLAIM_KINDS`) at the same HEAD |
| What I was given | the four findings **as summarised in the task statement** (REVIEW-01 … REVIEW-04). **The full text of the independent review report was not available in the repository branches I could read**; this errata answers the four items as described and by my own reading of the cited passages. A reviewer must confirm that the interpretation matches the report. |
| Untouched | J1 source and tests, V0.1, the Oracle, frozen Bench, Parcae, G0/G1, R3, the model; the base addendum text (the errata *supersedes* the passages in §1, it does not rewrite them) |

## 1. Supersession register (the base addendum stays as committed)

| Base addendum passage | Superseded / amended by |
|---|---|
| §2.2 rule 3 and §3.5 / D-R01-3 (IV-S independent validator) | **E-01** (§2 below) |
| §3.2 rows `J1-F05-A`, `J1-F05-B`, `J1-F05-C` (sidecar design) | **E-01.4** (O-private sealed reference log; prefix relation) |
| §4.1 last paragraph ("role collapse … until the owner accepts the limitation explicitly"), §4.3 trust-root options | **E-02** (§3 below) — the owner-acceptance escape for authenticity is **withdrawn** |
| §3.1 "Paired-case rule" (list `F01-A/C, F03-A/B, F04-B/C, F05-A/B/C, F06-B/C`) | **E-03** (§4 below) — that list is **withdrawn**, replaced by the atomic-pair contracts |
| §3.2 row `J1-F04-A` (truth column wording "ECHILD-type claim") | **E-04** (§5 below) |
| §4.5 negative controls NC-01…NC-14 | kept; NC-15 … extend them (E-01.5, E-02.5, E-03.4) |

## 2. E-01 (REVIEW-01, HIGH) — IV-S must independently and completely parse the sidecar, even when the seal comparison already reports MISMATCH

### 2.1 Source observation that motivates the rule (read, NOT RUN)

`codec.compare_seal` (lines 195–200 at the reviewed HEAD) computes only the byte length and SHA-256 of the read-back text and returns `MISMATCH` **before** it calls `parse_sidecar`; `judge._seal_outcome` maps `MISMATCH` to subject `FAIL`. Consequently, **by source reading, J1 alone cannot distinguish "a valid log that disagrees with the seal" from "a damaged log (torn tail, non-canonical line, broken chain, seq gap, wrong run id) that also disagrees"**: both would be reported as `LOG_MATCHES_SEAL = FAIL`. V0.1 reserves `FAIL` for a *valid readable* log against a trusted manifest, and `BLOCKED` for a missing / torn / untrusted one. Record this as **`OBS-J1-SEAL-01`** (candidate J1 source finding, severity to be assigned by the reviewer). It is **not** fixed here (no source edit is authorised); it is a reason why the *instrument* must not rely on J1's mismatch verdict.

### 2.2 Normative amendment

* **IS-1 (independence of IV-S).** IV-S for every case containing `LOG_READBACK` or `SEAL_MANIFEST` (here `J1-F05-A/B/C`) is established **only** by the independent acceptance verifier (IAV), **before and regardless of** any J1 output, with a sidecar checker that shares no code with `j1/codec.py` or `j1/schema.py` (a second implementation or a line-by-line manual checklist; D-R01-3 is narrowed accordingly — "reuse `codec.py` or `schema.py`" is not an option).
* **IS-2 (completeness).** The checker parses **the whole read-back file** with checklist SC-01 … SC-11 (§2.3) and the **whole manifest**; it never stops at the first difference and never infers validity from "the seal already disagrees".
* **IS-3 (two-sided validity for contradictions).** For every case whose expected verdict is a *positive contradiction* (`FAIL` expected: `J1-F01-A`, `J1-F02-A`, `J1-F04-C`, `J1-F05-A`, `J1-F06-C`), IV-S must establish that **each side of the contradiction is individually valid** (here: witness record well-formed and trusted-role-conformant; ledger sound apart from the intended duplicate; snapshot well-formed; for F05-A a fully valid 2-record chain **and** a well-formed manifest). A fixture whose "contradiction" comes from a defect of one side is `IV-S = VERIFIED_INVALID` ⇒ `CA = BLOCKED` (rule 3), **even if J1 returns the expected FAIL** and the verdicts coincide.
* **IS-4 (precedence unchanged).** Rule 3 of §2.2 still dominates rules 4–6: an `IV-S` that is not `VERIFIED_VALID` yields BLOCKED whatever J1 said. Rule 1 (verified guard violation ⇒ FAIL) still dominates.

### 2.3 Sidecar checklist for IV-S (design; independent implementation required)

| ID | Check on the read-back bytes |
|---|---|
| SC-01 | non-empty; ends with exactly one `\n`; no empty line; no bytes after the last newline (no torn tail) |
| SC-02 | every line valid UTF-8 and valid JSON; each a JSON **object** with exactly the five keys `seq, prev_digest, kind, body, event_digest` |
| SC-03 | each line equals the canonical serialisation of itself (`J1-CANON-0.1`: sorted keys, `,` `:`, `ensure_ascii=False`) — no alternate whitespace, key order or escaping |
| SC-04 | every string NFC; no float, NaN, Infinity; depth ≤ 8; keys strings |
| SC-05 | `seq` is a non-bool integer and equals the 1-based line number (no gap, duplicate, reorder) |
| SC-06 | line 1 `prev_digest` = 64 × `"0"`; every later `prev_digest` equals the previous line's `event_digest` |
| SC-07 | `event_digest` recomputed independently = SHA-256 of the canonical record without `event_digest`; all lowercase hex-64 |
| SC-08 | record count equals the design (2 for the F05-A/C read-back, 3 for F05-B); `kind` / `body` values equal the O-authored design (no case-identifying text) |
| SC-09 | `run_id` of the read-back event equals the design constant and the manifest's `run_id` (F05-A/B/C share the same run id by design, so a run-id difference is a *fixture defect*, not the intended contradiction) |
| SC-10 | manifest well-formed (exactly five fields; `full_file_sha256`, `last_digest` lowercase hex-64; `byte_length`, `final_seq` non-bool non-negative integers; non-empty `run_id`) |
| SC-11 | the manifest's five values are **recomputed by the checker** from the O-private sealed reference log (§2.4) and equal the manifest in S (so "the seal" really seals the designed chain) |

### 2.4 Lane O additions for the F05 family

The O record of each F05 case gains a private field **`sealed_reference_log`**: the complete designed 3-record chain whose seal the manifest represents (O-only; never visible to J1). Design relation: **the F05-A / F05-C read-back is exactly the first two records of the sealed reference log (a truncation)**; the F05-B read-back is the full reference log. The manifest in S is the *same* manifest in A, B and C. Everything remains `NOT MATERIALIZED`; no digest value is stated here.

### 2.5 Instrument negative controls added (verify the verifier, not J1; none designed as bytes or run)

| ID | Defect injected into an otherwise F05-A-style fixture | Required outcome |
|---|---|---|
| NC-15 | read-back has a torn tail (no final newline) and the seal disagrees | `IV-S` INVALID ⇒ `CA-BLOCK-S-INVALID`; a J1 `FAIL` equal to the expected FAIL **must not** become PASS |
| NC-16 | second record's `event_digest` altered (chain broken), seal disagrees | BLOCKED (SC-07) |
| NC-17 | non-canonical but JSON-equivalent line (extra space / reordered keys), seal disagrees | BLOCKED (SC-03) |
| NC-18 | seq gap or boolean `seq`, seal disagrees | BLOCKED (SC-05) |
| NC-19 | read-back `run_id` differs from the manifest's | BLOCKED (SC-09): the contradiction would not be the designed one |
| NC-20 | manifest malformed (bad hex, missing field) with an intact 2-record log | BLOCKED (SC-10); J1 itself would likely answer BLOCKED (UNDECIDABLE) ≠ expected FAIL — the instrument must catch it before J1 |
| NC-21 | manifest well-formed but not the seal of the O reference log | BLOCKED (SC-11) |
| NC-22 | read-back is **not** a prefix of the reference log (e.g. different record bodies) | BLOCKED (design contract §2.4) |

## 3. E-02 (REVIEW-02, HIGH) — independence among SA, OTR, TC, IAV (and the others) and the trust root; unprovable authenticity ⇒ BLOCKED

### 3.1 What was wrong in the base addendum

§4.1 listed "must NOT" columns but did not give a pairwise independence matrix, did not say **who creates and holds the trust root**, did not say **by what channel IAV obtains the verification material**, and allowed role collapse to be neutralised by "owner acceptance". All three are corrected here.

### 3.2 Pairwise independence matrix (functional roles; parties are assigned by the owner)

Roles: **SA** S Author · **OTR** O Truth Reviewer · **TC** Trusted Custodian · **EX** Executor · **IAV** Independent Acceptance Verifier · **DEV** developer of the J1 source / runner / guard · **OWN** holder of the trust root (the project owner).  
`✗` = the two roles **must be different parties with no shared session context or credentials**; if they coincide, the premise they protect is `UNVERIFIABLE` ⇒ the affected cases are `CA-BLOCK-CUSTODY` (and the run `RA-BLOCK-CUSTODY`). **No owner decision converts that BLOCKED into a PASS**; the only remedies are to restructure the parties and re-seal. `△` = may coincide; the coincidence is recorded and has no authenticity consequence by itself.

| | SA | OTR | TC | EX | IAV | DEV | OWN |
|---|---|---|---|---|---|---|---|
| **SA** | – | ✗ | ✗ | △ | ✗ | ✗ | △ |
| **OTR** | ✗ | – | ✗ | ✗ | ✗ | ✗ | △ |
| **TC** | ✗ | ✗ | – | ✗ | ✗ | ✗ | △ (only if the key never enters an AI session) |
| **EX** | △ | ✗ | ✗ | – | ✗ | △ | ✗ |
| **IAV** | ✗ | ✗ | ✗ | ✗ | – | ✗ | ✗ |
| **DEV** | ✗ | ✗ | ✗ | △ | ✗ | – | △ |

Rationale for the `✗` pairs: SA/OTR — truth must not be written by the author of the question; SA/DEV and OTR/DEV — inputs and truth must not be tailored to the code under test; TC/everyone writing, running or grading — the custodian must not be able to alter what it seals nor to grade it; IAV/everyone else — verification must not reuse a party's own claim, digest or key; EX/OWN and IAV/OWN — the holder of the root must not run or grade the experiment it vouches for.

### 3.3 Trust-root requirements (all must hold, otherwise authenticity is `UNVERIFIABLE`)

* **TR-01** The trust root (a signing key whose private part is held only by OWN or by TC under OWN's control, **or** an out-of-band digest publication channel controlled by OWN) is established by OWN **before any S/O/code artefact exists** and outside the repository and outside every AI session.
* **TR-02** TC, SA, OTR, EX and DEV cannot create, alter or replace the trust root.
* **TR-03** The private key material is never present in the execution environment, a Git branch, a chat transcript or any AI-agent context.
* **TR-04** The verification material (public key or the published digest/commit identifier) reaches IAV **by a channel independent of TC, EX, SA, OTR and DEV** (for example, OWN states it to IAV directly). Verification material shipped *inside* the sealed bundle, or obtained only from TC, is self-attestation and does not count.
* **TR-05** Every attestation names the role, the exact artefact list (the 18-id manifest, S, O, trust map, code SHA, guard/runner policy, criteria version) and the order of events; the **pre-run seal is verifiably earlier than the run**.
* **TR-06** Attestations are bound to the code SHA and to the run (no replay of an older or different attestation).
* **TR-07** Any suspicion of key compromise, wrong signer role, missing attestation or broken order ⇒ all dependent premises `UNVERIFIABLE`.
* **TR-08** A digest or hash is integrity metadata only. A Git commit identifier is also only a hash. Neither is a trust root unless published through TR-01/TR-04.

### 3.4 Decision rule (replaces the base addendum's "downgrade until the owner accepts")

> If any `✗` pair in §3.2 coincides, **or** any of TR-01 … TR-07 cannot be demonstrated by evidence independent of the writers of the artefacts, then `IV-S` / `IV-O` / `IV-C` for the affected cases are `UNVERIFIABLE`, and the affected cases are `BLOCKED` (`CA-BLOCK-CUSTODY`, with the specific sub-code in §3.6). The run is `BLOCKED` (`RA-BLOCK-CUSTODY`). This is not a failure of J1 and not a PASS-with-caveat. The owner may *restructure* (assign other parties, establish a trust root, re-seal); the owner may not *waive* it.

### 3.5 Limits stated openly

* Independence between AI sessions or agents is **organisational, not cryptographic**. Sessions of one model family share training biases; whether such sessions count as distinct parties for the `✗` pairs is an **owner decision (D-E02-2)**. Until decided, the conservative default is: **they do not count**, so no `✗` pair may be satisfied by two sessions of the same model family that wrote or reviewed the J1 source.
* The project presently has few distinct parties (and Grok is deferred). The matrix requires at least five mutually distinct parties across SA, OTR, TC, IAV, DEV (EX may coincide with SA or DEV). **That may not be satisfiable today**; if so the correct status is `BLOCKED`, not a relaxed matrix.

### 3.6 Reason sub-codes (machine-readable; extend `CA-BLOCK-CUSTODY`)

`CA-BLOCK-CUSTODY-ROLE-COLLAPSE` (a `✗` pair coincides) · `-TRUST-ROOT-ABSENT` (TR-01/02) · `-KEY-EXPOSURE` (TR-03) · `-VERIFICATION-MATERIAL-SOURCE` (TR-04: material from TC or the bundle) · `-ORDER` (TR-05: seal not provably before run) · `-REPLAY` (TR-06) · `-COMPROMISE` (TR-07). A case may carry several; any one suffices for BLOCKED.

### 3.7 Negative controls added (verify the verifier; none designed as bytes or run)

| ID | Defect | Required outcome |
|---|---|---|
| NC-23 | seal and S/O written by one party (SA=TC) | BLOCKED, `-ROLE-COLLAPSE` |
| NC-24 | custodian also executes (TC=EX) and hands in outputs | BLOCKED, `-ROLE-COLLAPSE` |
| NC-25 | IAV obtains the verification material only from the bundle or from TC | BLOCKED, `-VERIFICATION-MATERIAL-SOURCE` |
| NC-26 | public key / digest absent or published after the run | BLOCKED, `-TRUST-ROOT-ABSENT` or `-ORDER` |
| NC-27 | attestation from an earlier code SHA replayed | BLOCKED, `-REPLAY` |
| NC-28 | signing key found in the repository, execution environment or a session transcript | BLOCKED, `-KEY-EXPOSURE` |
| NC-29 | OTR and DEV are the same party (truth authored by the developer of the code under test) | BLOCKED, `-ROLE-COLLAPSE` |
| NC-30 | two sessions of the same model family occupy two `✗` roles while D-E02-2 is undecided | BLOCKED (conservative default) |

## 4. E-03 (REVIEW-03, MEDIUM) — atomic pair contracts replace the "paired-case rule"

### 4.1 Definition

An **atomic pair** is an ordered pair of S artefacts (a *base* member and a *variant* member) that differ by **exactly one logical factor**, together with **only those linked fields that the schema or the internal consistency of the case force to change with it**. Everything else — the trust map, handles, ordinals of untouched records, constants (`run_id`, pids not part of the factor, gate tokens, `observer_pid`), the key set and the canonical byte layout — is **byte-identical**. A pair claim is a statement of the form: "the predeclared verdict change is attributable to this factor, within the synthetic detector", nothing broader.

Each pair carries a **difference contract** with: pair id; base and variant ids; the logical factor; the *mandatory linked changes* with the reason each is forced; the *forbidden changes*; the expected subject-verdict transition; the allowed claim. The base addendum's earlier list is **withdrawn**: only the pairs below are atomic; every other combination is explicitly **not** a pair and supports no single-factor claim.

### 4.2 Difference contracts (all S-side diffs are on canonical JSON trees keyed by `(handle, order)`)

| Pair | Base → Variant | Logical factor | Mandatory linked changes (reason) | Forbidden changes | Verdict transition | Allowed claim |
|---|---|---|---|---|---|---|
| P-01 | F01-A → F01-B | presence of the trusted gate-child witness | delete exactly record `hW#5` (it is the last record, so no other ordinal moves) | any change to `hL#1..4`, trust map, constants | FAIL → BLOCKED | absence of a trusted witness turns a contradiction into undecidable |
| P-02 | F01-A → F01-C | which identity the B0-shaped ledger registered (Q vs G) | `REGISTERED` identity (4101,101) → (4102,102) **and** `FORKED.raw_fields.pid` 4101 → 4102 (forced: a FORKED pid unlike its own REGISTERED pid would add an unrelated OQ-13 factor) | witness record, gate tokens, ordinals, trust map | FAIL → PASS | agreement vs contradiction of registered identity against the same trusted witness |
| P-03 | F01-A → F01-D | provenance tier of the child-identity statement | remove `hW#5` and add `hN#5` in the same position; kind `GATE_CHILD_OBSERVATION` → `NODE_CLAIM`; `identity` (4102,102) → `raw_fields.{claim_kind=GATE_CHILD_IDENTITY, pid=4102, starttime=102}`; `gate_token` dropped (the NODE_CLAIM schema has no identity and the claim source has no gate association) | ledger rows, trust map | FAIL → BLOCKED | the same content from an untrusted tier cannot support a contradiction. *This is the one pair whose linked changes are numerous; they are all schema-forced and are listed so the factor is auditable.* |
| P-04 | F01-B → F01-D | presence of an untrusted claim | add exactly record `hN#5` (content as in P-03) | everything else | BLOCKED → BLOCKED (same verdict, different basis) | an untrusted claim changes the evidence basis, not the verdict |
| P-05 | F02-A → F02-B | whether nB duplicates nA's `(pid, starttime)` | nB `REGISTERED` identity (4101,101) → (4102,102) **and** nB `FORKED.raw_fields.pid` 4101 → 4102 (forced as in P-02) | nA records, ordinals, `RUN_START` | FAIL → PASS | duplicate vs distinct pair in an otherwise identical sound ledger |
| P-06 | F03-A → F03-B | presence of a post-release untrusted READY claim | add exactly `hN#6` (`claim_kind=READY`, node nA) after `hL#5` | everything else | BLOCKED → BLOCKED | a later claim does not alter the missing-pre-release-witness verdict |
| P-07 | F04-B → F04-C | observed process state at the single snapshot | `hK#5` `raw_fields.state` `Z` → `S` | ledger, identity, ordinals | PASS → FAIL | state contrast only |
| P-08 | F05-A → F05-B | completeness of the read-back log relative to the sealed reference | `hG#1` `raw_fields.log_utf8`: append the third record line (the read-back becomes the full reference); **no other field changes; the manifest `hM#2` is byte-identical in both** | manifest, `run_id`, trust map | FAIL → PASS | truncated vs complete read-back against one fixed seal |
| P-09 | F05-A → F05-C | the question asked about identical evidence | `assertion_id` `LOG_MATCHES_SEAL` → `EVIDENCE_USABLE`; **all observables and the trust map byte-identical** | any observable | FAIL → BLOCKED | integrity FAIL and downstream usability are different questions over the same bytes |
| P-10 | F06-B → F06-C | whether the trusted wrapper recorded a completed write | `hR#6` `raw_fields.bytes` 1 → 0 **and** `raw_fields.errno` null → `"EPIPE"` (forced together: `bytes=1` with an errno, or `bytes=0` without one, is a different, contradictory factor) | `hL#1..5`, `byte` field, ordinals | PASS → FAIL | completed vs not-completed trusted write |
| P-11 | F06-B → F06-D | provenance tier of the write statement | remove `hR#6`, add `hN#6` in the same position; kind `R_WRITE_RESULT` → `NODE_CLAIM`; `raw_fields.{bytes,errno,byte}` → `raw_fields.{claim_kind=R_WRITTEN}` (schema-forced) | ledger rows | PASS → BLOCKED | the same statement from an untrusted tier is not a syscall result |

**Explicitly not pairs (multi-factor or different assertion; no single-factor claim):** `F01-C ↔ F01-D`, `F01-B ↔ F01-C`; `F05-B ↔ F05-C` (log completeness **and** assertion differ); `F06-A ↔ F06-B/D` (assertion differs **and** a record is added); `F03-* ↔ F01-*` etc. across families; `F04-A` against `F04-B/C` (different assertion, `DEAD` row and a claim added). `F04-A` and `F06-A` are standalone cases.

### 4.3 Verification of a pair contract (instrument)

IAV, with its own structural-diff implementation, canonicalises both S members and computes the set of differing tree paths. The set must **equal** the contract's declared set (no more, no fewer), the variant's linked fields must be mutually consistent as stated, and the two trust maps must be byte-identical. A violation makes the pair contract invalid ⇒ `IV-S = VERIFIED_INVALID` for the variant (and for the base if the base cannot be separately validated) ⇒ `CA-BLOCK-S-INVALID` (sub-code `-PAIR-CONTRACT`). Pair validity is an additional precondition, not a verdict: a case is allowed to be unpaired.

### 4.4 Negative controls added (instrument; not run)

| ID | Defect | Required outcome |
|---|---|---|
| NC-31 | P-02 variant forgets the linked `FORKED.raw_fields.pid` update (REGISTERED = G, FORKED pid still 4101) | BLOCKED `-PAIR-CONTRACT`, **even though J1's ATTRIBUTION handler ignores FORKED and would answer PASS** |
| NC-32 | P-07 variant also shifts an unrelated ordinal | BLOCKED `-PAIR-CONTRACT` |
| NC-33 | P-08 variant changes the manifest as well as the log | BLOCKED `-PAIR-CONTRACT` |
| NC-34 | P-10 variant changes only `bytes` (errno left null) | BLOCKED `-PAIR-CONTRACT` (the contract demands both; a contradictory wrapper result is a different factor) |
| NC-35 | trust maps of two pair members differ in one entry | BLOCKED `-PAIR-CONTRACT` |
| NC-36 | P-09 variant differs from the base in an observable, not only in `assertion_id` | BLOCKED `-PAIR-CONTRACT` |

D-R02-4 is **narrowed**: pair members must be generated from one shared base template by SA and confirmed by the structural diff of §4.3; whether the template is a file or a procedure remains open.

## 5. E-04 (REVIEW-04, MEDIUM) — `J1-F04-A`: an untrusted `WAIT_RESULT` claim, not an ECHILD claim

### 5.1 The defect

The base addendum row for `J1-F04-A` speaks of "an ECHILD-type claim". The Lane S schema **cannot express** it: `NODE_CLAIM` allows exactly `claim_kind` (one of `GATE_CHILD_IDENTITY, R_WRITTEN, READY, WAIT_RESULT, OTHER`) and the optional `pid`, `starttime`; there is **no errno, no result-code and no `ECHILD` token**. The text implied evidence the artefact does not carry. (The J1 basis-code name `UNTRUSTED_WAIT_OR_ECHILD_CLAIM_NOT_REAP` has the same over-promise; renaming it is a source matter and is **not** done here. V0.1 and the preflight draft, which also say "ECHILD claim", are untouched and are satisfied only in the reduced sense below.)

### 5.2 Corrected row (supersedes the base addendum's `J1-F04-A` row)

| O-only ID | Lane S events | Lane O independent truth / expected SV | Expected basis & refs |
|---|---|---|---|
| `J1-F04-A` (`LAWFUL_REAP`, SMOKE_ONLY) | `hL#1..4` LT(nA = Q); `hL#5` DEAD nA; `hK#6` KERNEL_SNAPSHOT identity Q, state `Z`; `hN#7` NODE_CLAIM node nA, `raw_fields = {claim_kind: "WAIT_RESULT"}` **and nothing else** (no `pid`, no `starttime`, no errno) | A zombie snapshot, a `DEAD` ledger row, and an **untrusted claim that some wait result exists (its content is opaque to the schema; it may stand for ECHILD or any other outcome)** are not a lawful wait by the lawful reaper → **BLOCKED** | `DEAD_RECORD_IS_NOT_REAP`, `ZOMBIE_IS_NOT_REAP`, `UNTRUSTED_WAIT_OR_ECHILD_CLAIM_NOT_REAP` (name over-promises, see 5.1), `NO_TRUSTED_WAIT_WITNESS_SOURCE_IN_V0_1`; refs `hL#5`, `hK#6` |

### 5.3 Consequences

* The O truth statement must not rely on any ECHILD semantics; "ECHILD is not a reap" remains a design-level rule for G2 REAL (R-F3-2 of the G2 design), **not** something this synthetic case can exhibit.
* IV-S for `F04-A` checks that the claim record has exactly `claim_kind = WAIT_RESULT`, no extra raw field, and that no other statement in S asserts an errno. A fixture that tries to encode "ECHILD" by free text, by `OTHER`, or by an invented field is `IV-S = VERIFIED_INVALID` (the schema would reject it as `INPUT_INVALID`, which per rule 4 would be a FAIL *only* if the fixture were independently valid — it is not).
* Negative control **NC-37**: a `F04-A` variant carrying an invented `errno` field in the claim ⇒ independently invalid (BLOCKED `CA-BLOCK-S-INVALID`); J1's `INPUT_INVALID` there is not a SUT failure.
* Whether to give `WAIT_RESULT` an errno field (so the case could express ECHILD) would be a schema change and a new versioned spec decision: **D-E04-1**, not made here.

## 6. Consistency self-check of this errata (document level; nothing executed)

| Check | Result |
|---|---|
| Expected subject distribution | unchanged: **PASS 5** (`F01-C, F02-B, F04-B, F05-B, F06-B`), **FAIL 5** (`F01-A, F02-A, F04-C, F05-A, F06-C`), **BLOCKED 8** (`F01-B, F01-D, F03-A, F03-B, F04-A, F05-C, F06-A, F06-D`) |
| 18 ids / assertions / cards | unchanged; only the S-side wording of `F04-A` and the O-private reference of F05 are amended |
| Pair coverage | 11 atomic pairs (P-01…P-11); the remaining combinations are declared non-pairs; no pair claims a broader effect than its contract |
| R01 rules 1–6 and the 18-cell grid | unchanged; E-01 adds IS-1…IS-4 as refinements of rule 3, E-02 adds BLOCKED sub-codes only |
| Oracle / source / V0.1 | not touched; `FORMAL_ACCEPTANCE_READY=False`; formal Oracle BLOCKED / NOT_READY |
| Experiments | none: all NOT TESTED |

## 7. Open decisions and new observations

* **OBS-J1-SEAL-01** (§2.1): `compare_seal` can return `MISMATCH` for a damaged log; a separately authorised source stage (not this one) must decide whether to fix J1 or to rely solely on IV-S.
* **D-E02-1** trust-root mechanism (signing key vs out-of-band digest); **D-E02-2** whether same-model-family sessions count as distinct parties (default: no); **D-E02-3** who the five-plus distinct parties are, given that fewer may exist today.
* **D-E04-1** whether `WAIT_RESULT` should carry an errno (schema change).
* Carried over: D-R01-1, D-R01-2, D-R01-4, D-R02-1…D-R02-3, D-R03-3, OQ-1…OQ-13, G2 O-1…O-15. PF-02 … PF-06 and PF-08 remain BLOCKED; PF-07 / PF-09 NOT TESTED / NOT AUTHORIZED; the four SMOKE_ONLY assertions stay non-discriminative; `Grok DEFERRED / NOT PERFORMED`.

## 8. Only next instruction

Submit ERRATA 002 with its checkpoint to **ChatGPT** for the next independent review round and to **Grok** for cross-review when a real report exists (record it only if supplied). Resolve disagreements by a proposed minimal controlled experiment, not by choosing a reviewer. **Do not** edit source, V0.1 or the Oracle, materialise any S/O artefact, compute a hash, create a signature, freeze criteria, unlock formal acceptance, run Python/CPU/GPU, merge, or enter G2 REAL without a separate owner authorisation.
