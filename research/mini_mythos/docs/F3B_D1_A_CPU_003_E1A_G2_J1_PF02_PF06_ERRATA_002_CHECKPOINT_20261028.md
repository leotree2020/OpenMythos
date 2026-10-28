# F3B-D1-A-CPU-003-E1A-G2-J1-PF02-PF06-ADDENDUM-ERRATA-002 — checkpoint (2026-10-28)

**Status: ERRATA 002 DRAFT PREPARED — INDEPENDENT REVIEW PENDING. DOCUMENTATION ONLY. Review disposition being answered: DOCUMENT REVIEW CHANGES REQUIRED BEFORE CRITERIA FREEZE (target `ac5806f004242c6e018151d5543f7106fcf92829`). CRITERIA NOT FROZEN. CPU NOT TESTED. FORMAL ACCEPTANCE BLOCKED / NOT_READY (`FORMAL_ACCEPTANCE_READY=False` untouched). 18 S/O FIXTURES NOT MATERIALIZED. G2 REAL BLOCKED. Grok: DEFERRED / NOT PERFORMED (not a PASS). O-1…O-15, OQ-11…OQ-13 OWNER UNDECIDED.**
No Python, test, CPU/GPU experiment or process was run; no S/O data, hash, signature or key was created; no source, test, V0.1, Oracle, Bench, Parcae, G0/G1, R3 or model file and no earlier document was modified.

## Git

| Item | Value |
|---|---|
| Reviewed commit / base | `ac5806f004242c6e018151d5543f7106fcf92829` (`d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-addendum-20261028`), verified by `git ls-remote` + `git fetch` + `FETCH_HEAD`; the original branch is not modified |
| Errata branch | `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-errata-002-20261028`, created from that commit; clean tree at start |
| Commit / final HEAD | see "Git SHA addendum" (separate documentation commit) |
| Files | new `a_predicate_003/gate_g2/G2_J1_PF02_PF06_ACCEPTANCE_ADDENDUM_ERRATA_002_20261028.md`; this checkpoint; append-only `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md` — Markdown only |

**Scope note.** The four findings were supplied as one-line dispositions in the task statement; the full independent review report was **not found in the repository branches available to me**. The errata answers the four items as described and from my own reading of the J1 source (`codec.compare_seal`, `judge._seal_outcome`, `schema` NODE_CLAIM). A reviewer should confirm the interpretation against the report.

## Findings and what the errata does (document level; nothing executed)

| Finding | Severity | Errata section | Content | Status |
|---|---|---|---|---|
| REVIEW-01 | HIGH | E-01 (§2) | Records source observation `OBS-J1-SEAL-01`: `compare_seal` returns `MISMATCH` on length / SHA-256 **before** parsing the chain, so J1 alone can report `FAIL` for a damaged log. Adds rules IS-1…IS-4 (IV-S by the independent verifier only, with a checker sharing no code with `codec.py` / `schema.py`; complete parse even when the seal already mismatches; two-sided validity for every FAIL-expected case; precedence of rule 3 unchanged), checklist SC-01…SC-11, O-private `sealed_reference_log` (F05-A/C read-back = first two records of the 3-record reference), instrument negatives NC-15…NC-22. No J1 fix made. | **PASS (document prepared)**; review pending |
| REVIEW-02 | HIGH | E-02 (§3) | Pairwise independence matrix for SA / OTR / TC / EX / IAV / DEV / OWN (✗ = must differ, no shared session or credentials; △ = may coincide); trust-root requirements TR-01…TR-08 (root set up by the owner before any artefact, outside repository and AI sessions; verification material reaches IAV by a channel independent of TC/EX/SA/OTR/DEV; replay and order binding); decision rule: any ✗ collision or unproven TR ⇒ authenticity `UNVERIFIABLE` ⇒ `CA/RA-BLOCK-CUSTODY` with sub-codes; the base addendum's "downgrade until the owner accepts" is **withdrawn** (the owner may restructure, not waive); organisational (not cryptographic) independence of AI sessions stated, conservative default that same-model-family sessions do not count; NC-23…NC-30. | **PASS (document prepared)**; custody **NOT ESTABLISHED** |
| REVIEW-03 | MEDIUM | E-03 (§4) | Defines an atomic pair (one logical factor plus only schema- or consistency-forced linked fields; everything else byte-identical, including trust map and untouched ordinals) and gives the full difference contract for 11 pairs P-01…P-11; withdraws the base list of "paired cases"; names the non-pairs explicitly (e.g. F05-B↔F05-C, F06-A↔F06-B/D, F04-A, F06-A); IAV verifies each pair by its own structural diff; NC-31…NC-36. | **PASS (document prepared)**; review pending |
| REVIEW-04 | MEDIUM | E-04 (§5) | `J1-F04-A` re-specified as an **untrusted `NODE_CLAIM` with `claim_kind=WAIT_RESULT` and no other field**; the schema has no errno / ECHILD token, so the claim only asserts that some wait result exists; the O truth no longer relies on ECHILD semantics; IV-S rejects invented errno fields (NC-37); the over-promising J1 code name and V0.1 wording are noted, not changed; D-E04-1 (errno field) left open. | **PASS (document prepared)**; review pending |

Expected distribution (unchanged, still not measured): **5 PASS / 5 FAIL / 8 BLOCKED** over the same 18 ids as V0.1 and `oracle.SPEC_V0_1_INVENTORY`.

## Not done (by instruction)

No source / V0.1 / Oracle edit, no fixture, hash, key or signature, no criteria freeze, no unlocking of formal acceptance, no Python / CPU / GPU / process run, no merge, no G2 REAL, no claim that Grok reviewed.

## Open items

* `OBS-J1-SEAL-01` needs a separate, owner-authorised source stage (or an owner decision to rely solely on IV-S).
* D-E02-1 (trust-root mechanism), D-E02-2 (do same-model-family sessions count as distinct parties; default no), D-E02-3 (whether five mutually distinct parties exist — if not, the status is BLOCKED, not a relaxed matrix), D-E04-1 (errno on `WAIT_RESULT`).
* Carried over: D-R01-1, D-R01-2, D-R01-4, D-R02-1…D-R02-3, D-R03-3, OQ-1…OQ-13, G2 O-1…O-15. PF-02 … PF-06 and PF-08 remain BLOCKED; PF-07 / PF-09 NOT TESTED / NOT AUTHORIZED; the four SMOKE_ONLY assertions stay non-discriminative.

## Only next instruction

Submit ERRATA 002 and this checkpoint to **ChatGPT** for the next independent review round and to **Grok** for cross-review when a real report exists. **Stop here**: no implementation, materialisation, hashing, signing, freeze, Oracle unlock, execution, merge or G2 REAL without a separate owner authorisation.

## Git SHA addendum (separate documentation commit)

* Documentation commit (errata + checkpoint + navigation): `529ea95826a4991eeda963a64669c4f5ca99af68`
* Reviewed baseline: `ac5806f004242c6e018151d5543f7106fcf92829`. Diff `ac5806f..529ea95826a4991eeda963a64669c4f5ca99af68`: 4 files, 261 insertions, 0 deletions, all Markdown; two new files and two append-only navigation changes; no `j1/` source or test, V0.1, Oracle, Bench, Parcae, G0/G1, R3 or model path; the base addendum file is unchanged.
* This addendum is one further documentation-only commit; the final branch HEAD is the remote HEAD of `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-errata-002-20261028` and must not be confused with the documentation or baseline SHA.
* Working tree after commit: clean (ignored local G0/G1 authorization files untouched).
