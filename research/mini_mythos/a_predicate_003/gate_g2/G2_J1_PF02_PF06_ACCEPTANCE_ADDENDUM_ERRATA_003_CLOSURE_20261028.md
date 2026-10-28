# E1-A G2 J1 — PF-02/PF-06 Acceptance Addendum, ERRATA 003 CLOSURE CANDIDATE

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-PF02-PF06-ERRATA-003-CLOSURE-001` · 2026-10-28 · **DOCUMENTATION ONLY**.

**State:** `ERRATA 003 DOCUMENT CANDIDATE PREPARED / INDEPENDENT REVIEW PENDING`, **NOT** an independently accepted criteria set, **NOT FROZEN**, **NOT TESTED**. Formal Oracle remains `BLOCKED/NOT_READY` (`FORMAL_ACCEPTANCE_READY=False`). 18 official S/O fixtures, real custody seals and runtime guard **NOT MATERIALIZED / NOT IMPLEMENTED**. `G2 REAL BLOCKED`; Grok `DEFERRED / NOT PERFORMED`; owner decisions O-1…O-15 and OQ-1…OQ-13 remain unresolved.

## 0. Source provenance, authority and supersession

- Repository: `leotree2020/OpenMythos`. Base branch: `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-errata-002-20261028` at independently checked remote HEAD `dc339217eca851517eb1c5799213384a7e5c8c31`.
- Read-first: `G2_J1_PF02_PF06_ACCEPTANCE_CRITERIA_ADDENDUM_DRAFT_001_20261028.md` plus `G2_J1_PF02_PF06_ACCEPTANCE_ADDENDUM_ERRATA_002_20261028.md` and the latest ERRATA 002 checkpoint. Both originals stay unchanged. This document supersedes only the passages enumerated below, **not** V0.1 or the source.
- The four review findings **E02-R01 (HIGH)** TC/OWN trust-root conflict, **E02-R02 (HIGH)** purported atomic pairs, **E02-R03 (MEDIUM)** impossible root-timing language, **E02-R04 (MEDIUM)** two-line F05-A meaning come from the prior ChatGPT review in the conversation; no separate full review Markdown had been checked into the input branch. The author is **not** the independent acceptor of its own errata.
- Pinned source, read-only: `j1/schema.py` (especially `_RAW_SCHEMA` / `_parse_event`), `j1/judge.py::_write_complete`, `j1/codec.py::compare_seal`. The source-derived observations below are **static predictions, NOT runtime results**.
- Supersedes ERRATA 002 **§3.2 matrix OWN row and its asymmetrical implications, §3.3 TR-01/TR-02/TR-04 and timing, §3.5 minimum-party count, §4.1–§4.3 categorical claim of 11 atomic pairs, and §2.4/§4.2 P-08 F05-A descriptions**. Unmentioned requirements including ERRATA 002 independent IV-S SC-01…SC-11, IS-1…IS-4, NC-01…NC-37, §5 F04-A correction, base R01 case/run priority and Oracle hard block **remain in force**, except explicit NC clarifications in §4 below. Historical texts are retained for audit; the effective contract is base DRAFT 001 + ERRATA 002 + this bounded supersession, **still a draft**.

## 1. E03-01 (E02-R01 HIGH) — real trust-root control and verification-channel separation

### 1.1 Remove TC=OWN permission and conflicting authority

Replace the permissive `TC × OWN = △` in ERRATA 002 §3.2 with **`TC × OWN = ✗`** for this formal-acceptance candidate. For a trust root intended to establish **independent** authenticity, `OWN` (root controller) also **must differ** from SA, OTR, EX, IAV and DEV; the OWN row/column are `✗` against every operational role. Every `✗` means separate control of signing credentials, publication channel, service identities, permissions and ability to alter evidence, not merely different titles or chat sessions. Original SA/OTR/TC/EX/IAV/DEV pair constraints otherwise remain, including the permitted EX=SA or EX=DEV overlaps. The candidate now implies **at least six independent authority parties** (SA, OTR, TC, IAV, DEV, OWN; EX may coincide as previously permitted), assuming other `✗` constraints hold. The parties **have not been identified**: this is a proposed high-assurance criterion, not a statement that the team meets it.

### 1.2 Replace the incompatible root statements (TR-01 / TR-02 / TR-04)

- **TR-01-R (timing and identity):** OWN establishes and records the verification trust anchor **before the first official S/O fixture materialisation, acceptance evidence seal or authorised run**, as appropriate to the selected scheme. Pre-existing J1 source files may and do precede the anchor: they must be pinned by exact source snapshot and authenticated under that anchor **before** the accepted pre-run manifest. The historical phrase "before any ... code artefact exists" is withdrawn.
- **TR-02-R (control):** Only OWN controls the **root** secret or out-of-band root publication and any root-authorised delegation. SA, OTR, TC, EX, IAV and DEV cannot generate, replace or modify that root. TC may hold a **separate, explicitly delegated and scope-bound custody signing credential** only if OWN independently authenticates the delegation; TC's delegated key is **not** the root and does not let TC modify the root. Other parties have no custody/root signing authority.
- **TR-04-R (independent acquisition):** IAV acquires the trusted verification anchor and, if relevant, the authenticated TC delegation **from OWN's independently controlled publication channel**, not only from TC, the runner, any writer, the evidence bundle or an AI session. An OWN-named message transmitted through a TC-controlled channel is **not independent**. The IAV must check the actual control of the channel and bind the key/digest and delegation to the manifest scope and acceptance criteria version. No in-bundle public key or self-declared role proves this.
- **Allowed candidate models, not a selection:** (A) OWN independently publishes a pre-run, immutable commitment to the complete manifest for IAV; TC may retain the sealed artefacts but cannot rewrite OWN's commitment. (B) OWN controls a root key and independently authenticates TC's scoped sealing key; IAV obtains root public key/delegation from OWN-controlled independent publication, then verifies TC's signed evidence and code/manifest bindings. For either option pre-run ordering, role independence, replay checks, actual readback and unchanged S/O truth remain required. **D-E02-1 remains OWNER UNDECIDED**.

A purported PASS based solely on a Git SHA, TC-issued proof, same-session "separate" roles, unverified owner channel or later backdated publication remains `CA-BLOCK-CUSTODY` / `RA-BLOCK-CUSTODY`. The owner cannot waive an absent independent trust root into `VERIFIED_VALID`. The stronger staffing requirement may keep readiness BLOCKED; do not silently weaken it.

### 1.3 Design-only counterexamples (no artefacts or tests generated)

- **NC-38:** TC and OWN turn out to be the same controlling party even if two role names or channels appear → `CA-BLOCK-CUSTODY-ROLE-COLLAPSE`.
- **NC-39:** OWN is also SA, OTR or DEV while claiming independently authenticated provenance → `CA-BLOCK-CUSTODY-ROLE-COLLAPSE`.
- **NC-40:** verification key / digest reaches IAV only through TC or bundled files, with an OWN label but no independently controlled publication → `CA-BLOCK-CUSTODY-VERIFICATION-MATERIAL-SOURCE`.
- **NC-41:** root created after fixture sealing, or old code claimed to predate a root under the impossible original wording rather than being separately pinned before official sealing → missing chronology/authenticated code binding **BLOCKED**; pre-existing code itself is **not** a defect when properly pinned.

These controls specify **future expected verifier behavior**, never measured scores.

## 2. E03-02 (E02-R02 HIGH) — separate atomic, invariant-linked and compound contrasts

### 2.1 Correct classification and limits

The claim "all 11 P-01…P-11 are atomic pairs with one schema-forced factor" is **withdrawn**. A structural diff can prove which bytes/fields differ, **not** by itself prove causal isolation. Preserve all eleven relation IDs and every one of the original 18 case IDs and planned subject verdicts, but classify them:

| Class | P IDs | Scientific interpretation and preconditions |
|---|---|---|
| **A — strict single-field/record/question contrast** | **P-01, P-04, P-06, P-07, P-08, P-09** | Exactly one explicitly defined S record presence, S field, text payload or assertion selector changes; no collateral S change; independent O truth remains private. For P-08 the `log_utf8` value changes but its new internal content comprises a whole additional record, see §3. |
| **B — invariant-linked controlled contrast** | **P-02, P-05** | A selected scenario-control policy co-varies `REGISTERED.identity` and `FORKED.raw_fields.pid` to keep the *proposed fixture's own alignment*. **The schema does not mandate equality**: this must not be called a source-enforced or frozen R3 invariant. OQ-13 remains UNDECIDED. This is a controlled joint change with a named logical factor, not a strict single-field experiment. |
| **C — compound/representation-and-provenance controlled contrast; NOT atomic** | **P-03, P-10, P-11** | More than one independent field or information dimension changes; preserve exact diffs as an auditable scenario comparison, but **make no single-factor causality claim**. |

### 2.2 Three corrected source-grounded contrasts

- **P-03 F01-A → F01-D:** `NODE_CLAIM` can carry the optional **event-level** `gate_token` under `schema._parse_event`; removing it is **not schema forced**. Its `identity` is disallowed by node-claim semantics, and the data must instead be represented as `raw_fields.pid/starttime` with `claim_kind`. This changes both role/authority and evidence representation. To minimize the otherwise avoidable difference, the **proposed F01-D S row now retains `gate_token="gate-A"`** for its `hN#5` claim. It is still untrusted and expected subject `BLOCKED`; no authenticated witness exists. This is a **draft S-row refinement**, not a modification of V0.1 or code. Do not claim that claimant's retained gate token authenticates ticket association.
- **P-10 F06-B → F06-C:** ERRATA 002's designated F06-C remains `bytes=0, errno="EPIPE"` versus F06-B `bytes=1, errno=null`. This is a **two-field compound success-versus-failure scenario**, **not** a mandatory schema-linked atomic transformation. `schema._RAW_SCHEMA["R_WRITE_RESULT"]` accepts `bytes=0, errno=null`, and source-static reading of `judge._write_complete` predicts `FAIL` for that distinct valid candidate too; no source requires EPIPE when bytes=0. A future **single-field bytes-only** contrast would require a **separate, owner-reviewed fixture contract**, not silent replacement of official F06-C. NC-34 in ERRATA 002 continues to detect a violation of **the designated compound F06-C contract**, not a malformed source-schema value.
- **P-11 F06-B → F06-D:** `R_WRITE_RESULT(bytes,errno,byte)` is converted to an untrusted `NODE_CLAIM(claim_kind=R_WRITTEN)`. The latter cannot encode the former's write count/error semantics under the closed schema. This simultaneously changes trust/authority, question-relevant specificity and record representation. Preserve the expected `PASS → BLOCKED` contrast as a **multi-factor control**, not proof that changing only trust tier caused it.

For P-02/P-05 the linked PID changes are a **deliberate prospective fixture-design choice** to avoid injecting an additional mismatch while OQ-13 is open, *not* a correctness requirement enforced by `schema.py`. The case-neutral source handles/trust map and 5/5/8 expected verdict distribution remain unchanged.

### 2.3 Verifier contract and negative controls

- IAV still independently checks the **exact** declared S tree-path differences for all eleven relations. A verified unexpected difference invalidates the **claimed comparison contract**, with `CA-BLOCK-S-INVALID-PAIR-CONTRACT` or a narrower sub-code. It does not prove that either individual syntactically valid sample is bad for an unrelated assertion; any case-level block needs an explicit predeclared dependency on the comparison claim.
- Only class A may be labelled `STRICT_ATOMIC_CONTRAST`; class B is `INVARIANT_LINKED_CONTROLLED` (design-level policy, OQ-13 not resolved); class C is `COMPOUND_CONTROLLED_NO_CAUSAL_ISOLATION`. **No aggregate report may state "11 atomic pairs".**
- **NC-42:** P-03 is labelled atomic, or its `gate_token` is dropped while claiming that the schema required its removal → comparison-label/contract violation, not an observed J1 defect.
- **NC-43:** P-10 submits bytes-only F06-C but calls it identical to the predeclared two-field F06-C contrast → comparison-contract violation; the schema validity of bytes-only inputs must **not** be denied.
- **NC-44:** P-11 reports causal proof of "trust alone" → claim rejected / downgraded, even if J1's expected `BLOCKED` is later observed.
- **NC-45:** P-02 or P-05 declares `FORKED.pid == REGISTERED.pid` a frozen Bench/R3 rule → claim rejected; OQ-13 remains owner undecided.

## 3. E03-03 / E03-04 (E02-R03/R04 MEDIUM) — chronology and internally valid shorter F05-A

The impossible root chronology is corrected in **TR-01-R (§1.2)**; *historical existence of source code is not grounds to fabricate a prior trust root*. Only a future verified **pre-acceptance sealing** timeline can establish the required order.

**F05 exact prospective meaning (overrides ambiguous words "truncation" / "torn" in ERRATA 002 §§2.4, 4.2 P-08; all bytes currently NOT MATERIALIZED):**

| Fixture | Lane S read-back | Sealed O-private reference | Sidecar IV-S state if all checks hold | Expected J1 subject |
|---|---|---|---|---|
| `J1-F05-A` | Exactly **two complete**, canonical, correctly chained JSON records, each followed by newline, including a final newline. No partial tail, gaps or corrupted digest; the entire two-record prefix matches the reference exactly. | Three complete sealed records; the S manifest is the independently verified manifest of all **three** reference records. | **VALID for this *two-record negative-comparison fixture***; independent verifier must also confirm reference and S manifest provenance and entire readback validity. | **FAIL** (`LOG_MATCHES_SEAL` contradicts reference seal) |
| `J1-F05-B` | Exactly **all three** complete canonical chained records and final newline; matches the sealed reference. | Same three-record reference and same manifest as A/C. | VALID only if every independent check passes. | **PASS** |
| `J1-F05-C` | **Byte-identical S observables and trust map to A**; only `assertion_id` differs. | Same reference and manifest as A. | VALID under same constraints as A. | **BLOCKED** (`EVIDENCE_USABLE`, SMOKE_ONLY) |

**Two different meanings of "incomplete":** The two-record A/C file is an *internally complete and readable shorter log*, with a positive **external mismatch to the independently pinned three-record seal**; this is a valid deliberately contradictory synthetic observation. A file with an **unterminated final line, truncated JSON fragment, broken digest/link, missing newline, corrupt readback, or uncontrolled alteration** is an invalid instrument even if the same manifest mismatch appears; then `IV-S=VERIFIED_INVALID` and formal case acceptance is `BLOCKED`, **never** a matching expected-subject FAIL accepted as case PASS. No claim is made about the origin or timing of a real-world truncation, kernel provenance or native-B0 durability. This design resolves only a synthetic acceptance distinction.

- Continue ERRATA 002 SC-01…SC-11 in full, including independent complete parse **before** treating J1's early `compare_seal` mismatch as a testable contradiction; verify the two-line prefix and the three-line reference as separately valid artefacts.
- **NC-46:** a valid two-complete-line prefix is incorrectly rejected solely because it is shorter than the trusted three-line reference → instrument-rule defect (cannot assert intended preflight acceptance).
- **NC-47:** a two-record file with partial tail / missing terminating newline / invalid chain is accepted as valid just because its external seal differs → instrument-verifier defect, affected case **BLOCKED**.
- **NC-48:** an A/B/C run replaces the reference or manifest between cases while claiming P-08 strict contrast → comparison and custody premise **BLOCKED**.

No actual JSON, reference log, S/O hash, sidecar manifest, signature, trust root, runner, CPU process or test was created or executed.

## 4. Invariant ledger, decisions and explicit statuses

- Exact V0.1 subject expectations stay **18 IDs**: `PASS=5` (F01-C, F02-B, F04-B, F05-B, F06-B), `FAIL=5` (F01-A, F02-A, F04-C, F05-A, F06-C), `BLOCKED=8` (F01-B, F01-D, F03-A, F03-B, F04-A, F05-C, F06-A, F06-D). These are *prospective subject outputs*, **all NOT TESTED**.
- The base addendum's subject/instrument/case/run four-layer separation remains. A correct subject `FAIL` can only yield *future* case `PASS` when independently established IV-S/O/C/G, custody, seal, guard and matching O are all satisfied. `FORMAL_ACCEPTANCE_READY=False` stays unchanged; existing formal Oracle cannot deliver PASS.
- Existing ERRATA 002 NC-01…NC-37 remain documented design controls; NC-34's meaning is narrowed to the **predeclared F06-C compound contract** as above. NC-38…NC-48 are additional **proposals**, not executed negative experiments.
- **New owner decisions:** `D-E03-1` feasibility/independent assignment of OWN plus operational roles, and root verification channel (not a bypass); `D-E03-2` whether class B coupled PID scenarios are acceptable without OQ-13 conclusion; `D-E03-3` whether any compound comparison should be withdrawn from report as a paired claim. These remain **UNDECIDED**.
- Prior `OBS-J1-SEAL-01`, `D-E02-1` signing vs out-of-band root, `D-E02-2` same-model-family independence, `D-E02-3` actual parties, `D-E04-1` WAIT_RESULT errno, `D-R01-1…4`, `D-R02-1…4`, `D-R03-1…3`, `OQ-1…13` and `G2 O-1…O-15` remain open unless explicitly superseded on wording here. No model or architecture conclusion follows.
- `PF-00/01 = PASS (prior provenance/document scope only)`; `PF-02…PF-06, PF-08 = BLOCKED/NOT_FROZEN`; `PF-07/09 = NOT TESTED/NOT AUTHORIZED`; `G2 REAL = BLOCKED`; `Grok = DEFERRED/NOT PERFORMED`.
- **Environment:** GitHub connector source/doc operations only; local Git status, external environment, runner/guard effectiveness and actual evidence materialisation **NOT VERIFIED**. No Python/import/pytest/CPU/GPU/synthetic or real process experiment, no code edit, no criteria freeze, no merge.

## 5. One and only next instruction

Submit **ERRATA 003 CLOSURE CANDIDATE** and its checkpoint for an **independent** source-grounded ChatGPT document re-review; send to Grok **only when an actual cross-review can be obtained**, otherwise record `DEFERRED`. Evaluate the strictness/feasibility of role independence and the three comparison classes without changing any experimental input yet. Preserve disagreements and propose the smallest controlled follow-up instead of asserting reviewer consensus. **STOP**: No J1/Bench/Parcae/R3/model edits, no S/O production or hashes, no verification key/signature, no Python/CPU/GPU/REAL, no Oracle unlock, no freeze or merge without separate express owner authorisation.
