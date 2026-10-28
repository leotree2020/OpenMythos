# F3B-D1-A-CPU-003-E1A-G2-J1-PF02-PF06-ACCEPTANCE-ADDENDUM-001 — checkpoint (2026-10-28)

**Status: PF-02/PF-06 ACCEPTANCE CRITERIA ADDENDUM DRAFT PREPARED — INDEPENDENT REVIEW PENDING. DOCUMENTATION ONLY. CRITERIA NOT FROZEN. NOTHING EXECUTED (NOT TESTED). FORMAL ORACLE STILL BLOCKED / NOT_READY (`FORMAL_ACCEPTANCE_READY=False` untouched). 18 S/O FIXTURES NOT MATERIALIZED. G2 REAL BLOCKED. Grok: DEFERRED / NOT PERFORMED (not a PASS). O-1…O-15, OQ-11, OQ-12, OQ-13 OWNER UNDECIDED.**
No Python, pytest, CPU/GPU experiment, process test, S/O data, hash or signature was produced; no source, test, V0.1 text, Bench, Parcae, G0/G1, R3 or model file was modified.

## Git

| Item | Value |
|---|---|
| Base branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-cpu-readiness-preflight-review-20261028`, remote HEAD re-verified by `git ls-remote` + `git fetch` + `FETCH_HEAD` = **`466f28f7b36e4c851f6f4865903a3827e2d3ec5a`** (as announced) |
| Documentation branch | `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-addendum-20261028`, created from that HEAD |
| Working tree at start | clean (0 porcelain lines) |
| Inputs pinned (blobs at the base HEAD) | preflight draft `2d913119…`; V0.1 `9574f906…`; `j1/oracle.py 0df6e5da…`, `schema.py 551c4a01…`, `judge.py 8aef00cb…`, `codec.py bb486c92…` |
| Commit / final HEAD | see "Git SHA addendum" (separate documentation commit, avoids self-reference) |

## Files (Markdown only)

New: `a_predicate_003/gate_g2/G2_J1_PF02_PF06_ACCEPTANCE_CRITERIA_ADDENDUM_DRAFT_001_20261028.md` and this checkpoint. Navigation appends: `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. No other path.

## Experimental-management record (documents only)

| Element | Expected | Actual | Status |
|---|---|---|---|
| Objective | Close preflight findings `J1-PF-R01` (error-origin taxonomy), `R02` (per-case S/O manifest), `R03` (truth and custody) on paper | Addendum §2 / §3 / §4 | **PASS (document prepared)** |
| Environment | GitHub/Git + editor only; no interpreter, no process, no GPU | as expected | **PASS** |
| R01 | Subject verdict, instrument validity, case verdict, run verdict separated; six situations classified without contradiction | §1 four-layer table; §2.2 ordered rules 1–6; §2.2 exhaustive 3×2×3 = 18-cell grid with exactly one PASS cell; §2.4 run rules | **PASS (document)** — reviewer confirmation pending |
| R02 | 18/18 cases with O-only id and assertion, Lane S events and fields, handles / roles / ceilings, ordinals / readback, S↔O private join, independent O truth and evidence basis, canonical JSON version, expected refs, unfinished items | §3.1 global contract (`J1-S-SCHEMA-0.1`, `J1-CANON-0.1`, one case-neutral `TRUST-MAP-0.1`, ledger template, private join); §3.2 all 18 rows; counts 5 PASS / 5 FAIL / 8 BLOCKED identical to V0.1 and `oracle.SPEC_V0_1_INVENTORY` | **PASS (document)**; materialisation **NOT DONE** |
| R03 | Roles for S author, O truth reviewer, trusted custodian, executor, independent verifier; seal, verification, tamper negatives; SHA-256 not an authenticity proof | §4.1 roles and separation rules (role collapse must be recorded and downgrades claims); §4.2 evidence table; §4.3 digest vs trust root (mechanism left open); §4.4 sequence; §4.5 NC-01…NC-14 | **PASS (document)**; custody **NOT ESTABLISHED** |
| V0.1 expectations unchanged | 18 verdicts as in V0.1 | reproduced, not altered | **PASS** |
| Any experiment | none authorised | none run | **NOT TESTED** |

Design-consistency note: each §3.2 row was walked through the J1 source as read (`judge.py`, `schema.py`, `codec.py`) on paper; this is a source-reading prediction, **not a test**. One inconsistency found and fixed in the draft before commit: ATTRIBUTION rows originally interleaved a witness between ledger rows, which would break the ledger's contiguous-order rule; non-ledger rows are now numbered after the ledger and the F01 cases carry no `RELEASED` row.

## Unresolved decisions (kept open, nothing decided silently)

* D-R01-1 J1 exception under a clean guard: FAIL (proposed) vs BLOCKED; D-R01-2 whether `GV-RESOURCE` is a separate safety category; D-R01-3 how the independent IV-S validator is built (J1's own `schema.py` is not acceptable for IV-S); D-R01-4 verdict-only grading vs required-basis grading (couples O to J1's code vocabulary).
* D-R02-1…4 (FORKED pid in all ledgers, shared constants, sidecar record bodies, materialising paired cases from a shared base).
* D-R03-1 trust-root mechanism (key held outside session/repo, out-of-band digest publication, or equivalent); D-R03-2 role assignment and acceptance of any role collapse; D-R03-3 implementation form of the verifier.
* OQ-13 (FORKED.pid vs REGISTERED.pid) not decided and not exercised; OQ-11 / OQ-12 and the G2 design O-1…O-15 unchanged; PF-02…PF-06 and PF-08 remain BLOCKED; PF-07 / PF-09 NOT TESTED / NOT AUTHORIZED; the four SMOKE_ONLY assertions stay non-discriminative.

## Only next instruction

Submit the addendum and this checkpoint to **ChatGPT** for independent source-grounded review and to **Grok** for cross-review when a real report is available (record it only if actually supplied; absence stays `DEFERRED`). Resolve disagreements by a proposed minimal controlled experiment, not by choosing a reviewer. **Do not** implement code, materialise any S/O artefact, compute any hash, create a signature, freeze criteria, unlock the Oracle, run Python / CPU / GPU, merge, or enter G2 REAL without a separate owner authorisation. **Stop here.**

## Git SHA addendum (separate documentation commit)

* Documentation commit (addendum + checkpoint + navigation): `a312d28c52d10509e6ef9cde596495f0d57665ae`
* Baseline: `466f28f7b36e4c851f6f4865903a3827e2d3ec5a`. Diff `466f28f..a312d28c52d10509e6ef9cde596495f0d57665ae`: 4 files, 321 insertions, 0 deletions, all Markdown; 0 non-Markdown paths; 0 paths outside `a_predicate_003/gate_g2/*.md` and `docs/*.md`; no `j1/` source, test, V0.1 file, Bench, Parcae, G0/G1, R3 or model path.
* This addendum is one further documentation-only commit; the final branch HEAD is the remote HEAD of `d1-r3-a-cpu-003-e1a-g2-j1-pf02-pf06-addendum-20261028` and must not be confused with the documentation or baseline SHA.
* Working tree after commit: clean (ignored local G0/G1 authorization files untouched).
