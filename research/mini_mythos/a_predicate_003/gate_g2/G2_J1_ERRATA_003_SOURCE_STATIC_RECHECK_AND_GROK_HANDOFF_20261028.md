# E1-A G2 J1 — ERRATA 003 source-static recheck and external Grok handoff

**2026-10-28 · Stage:** `F3B-D1-A-CPU-003-E1A-G2-J1-ERRATA003-SOURCE-STATIC-RECHECK-GROK-HANDOFF-001`.

**Disposition:** `SOURCE-STATIC RECHECK RECORDED — EXTERNAL INDEPENDENT REVIEW PENDING`. This is a **same-assistant author-bound recheck** of material drafted in the preceding ChatGPT step. It is **NOT an independent third-party sign-off**, **NOT a real Grok review** and **NOT a CPU, functional, security, native-B0 or G2 REAL test**. All experimental statuses remain `NOT TESTED`; formal Oracle `BLOCKED / NOT_READY` and `FORMAL_ACCEPTANCE_READY=False` unchanged. No source, test, fixture, digest, signature, key, acceptance criterion freeze, merging or execution.

## 0. Pinned inputs and evidence limits

- GitHub repository `leotree2020/OpenMythos`; rechecked ERRATA 003 source branch `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-errata-003-closure-20261028`, remote HEAD **`d59c01808bf1d42984ead018c10e4330f37248e8`** before this review/handoff.
- Effective proposed specification: `G2_J1_PF02_PF06_ACCEPTANCE_CRITERIA_ADDENDUM_DRAFT_001_20261028.md` + `G2_J1_PF02_PF06_ACCEPTANCE_ADDENDUM_ERRATA_002_20261028.md` + `G2_J1_PF02_PF06_ACCEPTANCE_ADDENDUM_ERRATA_003_CLOSURE_20261028.md`. Historical documents are superseded only on the passages listed in their registers; all are **DRAFT**.
- J1 read-only blobs: `j1/schema.py 551c4a01ed37f73c809776e123f98f6d055ac998`; `j1/judge.py 8aef00cb1b66ee107c91086cd537c759858940cd`; `j1/codec.py bb486c922b945dd30edb003a11fe7758bd13c2fb`; `j1/oracle.py 0df6e5da8e8d08b39f19ff4188f34d33a44a2282`.
- Review method: manual comparison of Markdown requirements against code text in GitHub. No J1 invocation, unit test, instrument validation, attestation, dynamic source probe, direct Grok access or runtime execution. The review author was involved in ERRATA 003 authoring and cannot claim independent confirmation of its own design.

## 1. Review of the four prior concerns (source-static and document-only)

| Finding from prior review | Reading of ERRATA 003 | Static disposition; NOT an experiment |
|---|---|---|
| E02-R01 HIGH — TC=OWN/independent key source collision | ERRATA 003 §1.1 now forbids TC=OWN and adds OWN separation from all operational roles; §1.2 distinguishes OWN-controlled root channel from TC-scoped delegated custody and requires IAV to verify an independent delivery channel. The former permission for the same party to authenticate itself is withdrawn. | **ADDRESSED ON PAPER**. Independent parties, actual publication/keys/delegation and their provenance **NOT ESTABLISHED**; cannot earn IV-C/PASS yet. |
| E02-R02 HIGH — 11 alleged atomic pairs | ERRATA 003 §2 changes A=6 strict outer-input delta, B=2 linked scenarios, C=3 compound/representation contrasts, preserving P-01…P-11 and the original 18 expected subject verdicts. `schema._parse_event` permits an event-level gate_token on NODE_CLAIM, so P-03's dropped gate token was not schema-forced. `judge._write_complete` can return FAIL for `bytes=0, errno=null`, so P-10's EPIPE is not schema-forced. | **CORE CORRECTION ADDRESSED ON PAPER**, with an additional claim-scope issue below (R03-SELF-01). |
| E02-R03 MEDIUM — impossible root chronology | ERRATA 003 §1.2 TR-01-R requires a trusted root before **official fixture materialization/pre-run sealing**, not before pre-existing J1 code; existing source must be bound before the official run. | **ADDRESSED ON PAPER**; actual ordering attestation/independent root is **NOT MATERIALIZED / NOT VERIFIED**. |
| E02-R04 MEDIUM — valid short F05-A vs damaged/torn readback | ERRATA 003 §3 defines two fully canonical, newline-terminated, correctly chained read-back records that are an exact prefix of the separately verified three-record reference log. A corrupted, nonterminated or chain-invalid two-line file is instead independent IV-S INVALID/BLOCKED. | **ADDRESSED ON PAPER**. Requires the independent SC-01…SC-11 checker; no S/O bytes or checker exist in this stage. |

These are checks of the **wording and pinned source**, not independent acceptance of the proposal.

## 2. Additional review observation — do not overclaim P-09

**R03-SELF-01 · MEDIUM · CLAIM-SCOPE NARROWING RECOMMENDED.** ERRATA 003 §2.1 puts `P-09 F05-A → F05-C` in class A `STRICT_ATOMIC_CONTRAST` because the only S-document change is `assertion_id`: `LOG_MATCHES_SEAL` → `EVIDENCE_USABLE`. Its byte-level delta may indeed be confined to one input field. However, the *function under evaluation changes* from an integrity assertion to a downstream evidence-usability assertion. These are **not repeated measurements of the same predicate with one evidence factor manipulated**; accordingly, a single-field syntactic diff cannot support a causal conclusion about improved/changed detector performance on one assertion.

**Minimal requested documentation correction (not applied to ERRATA 003 here):** Retain the same 18 cases, same O truth, same input and 5/5/8 counts, but label P-09 `QUESTION_SWITCH_CONTROL` or `CROSS_ASSERTION_SEMANTIC_CONTRAST`, **not** an atomic single-predicate evidence manipulation. If categories must be mutually exclusive, proposed counts become A=5, B=2, C=3, D=1. Alternatively keep class A for *syntactic one-field changes only* with an explicit rule that class A never implies within-assertion causality; prohibit any broad "six scientific atomic experiments" claim. Owner/reviewer must decide which wording meets preregistration.

**R03-SELF-02 · INFO — guard against an inference slip:** Class A P-08 changes exactly one **outer S JSON field** (`log_utf8`) but appends a whole valid third chain record inside that string; a structural diff of outer tree paths is not proof of a single internal evidence event. The ERRATA 003 §3 complete-file validation and prefix contract must remain mandatory. No new source defect concluded.

## 3. Readiness and reviewer independence

- `ERRATA 003 AUTHOR SOURCE-STATIC RECHECK = COMPLETED (NON-INDEPENDENT)`; `INDEPENDENT REVIEW = PENDING`. The static dispositions above do **not** close external independence, prove IV/O provenance, or override any blocker.
- **Grok access check:** this conversation's available tool catalog exposed no callable Grok/xAI integration; plugin directory search for `Grok xAI` returned zero available plugins. **No Grok request was sent; no Grok report exists; Grok DEFERRED / NOT PERFORMED (NOT PASS)**. Project owner's standing default Grok authorisation permits future invocation once a genuine connection is available, but permission cannot substitute for access.
- `FORMAL_ACCEPTANCE_READY=False` stays hard-coded; no G2 criterion freeze, no source edit, no independent S/O attestation, no CPU guards or runs, no G2 REAL process safety claim. `PF-02…PF-06/PF-08 = BLOCKED`; `PF-07/PF-09 = NOT TESTED / NOT AUTHORIZED`; `G2 REAL = BLOCKED`.
- Expected subject verdicts stay **18 cases** = 5 PASS, 5 FAIL, 8 BLOCKED, **all unmeasured**. SMOKE_ONLY covers PREVENT_PROOF, LAWFUL_REAP, EVIDENCE_USABLE, DELIVERY. Do not mistake a subject PASS/FAIL/BLOCKED for a case/run PASS.

## 4. Grok handoff brief — paste as-is into a real Grok session (no claim it was sent)

**Task:** Independent, adversarial source-grounded review; DO NOT implement, run, freeze, merge or assume Grok's own verdict is final.

> Review repository `leotree2020/OpenMythos`, pinned commit `d59c01808bf1d42984ead018c10e4330f37248e8`, document `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_PF02_PF06_ACCEPTANCE_ADDENDUM_ERRATA_003_CLOSURE_20261028.md`. Read the preceding `...ERRATA_002_20261028.md` and `...ACCEPTANCE_CRITERIA_ADDENDUM_DRAFT_001_20261028.md` plus `j1/schema.py`, `j1/judge.py`, `j1/codec.py`, `j1/oracle.py` at that exact SHA. Identify counterexamples or internal contradictions in (i) OWN/TC/IAV root provenance and chronology; (ii) 11 pair contracts and whether P-09 is same-predicate atomic or cross-assertion only; (iii) F05-A valid two-record prefix versus corrupted readback and `compare_seal` short-circuit; (iv) four-layer R01 PASS/FAIL/BLOCKED precedence; (v) known unimplemented verifier/guard constraints. For each finding give ID, severity, source path/section and minimum document-only correction. Keep 18 V0.1 expected subject outcomes (5/5/8) separate from all test outcomes. Return explicit PASS/FAIL/BLOCKED/NOT TESTED per review claim, and state every unresolved Owner decision. Do not claim running Python/tests, independent authenticity or native G2 REAL without actual evidence. If you disagree with ChatGPT, preserve disagreement and design a minimum controlled experiment for a separately authorised later stage.

Until a genuine response arrives, **GROK_REPORT=ABSENT**, `GROK_REVIEW_STATE=DEFERRED_NOT_PERFORMED`.

## 5. Next only

Obtain and archive an actual independent cross-review (Grok if accessible through a separately connected tool or a supplied report), then adjudicate `R03-SELF-01` and any additional findings. Write a new checkpoint with reviewer provenance and unresolved disagreements. Any change to the ERRATA 003 source document, test fixture, S/O data, code, Oracle readiness, guard, real process or frozen criteria requires a separately scoped instruction. **STOP after committing this recheck and handoff.**
