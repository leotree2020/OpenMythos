# F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-PREP-001 — implementation checkpoint (2026-10-28)

**Status: IMPLEMENTATION SOURCE PREPARED — STATIC REVIEW PENDING. J1 CPU NOT TESTED. G2 CRITERIA NOT FROZEN. G2 REAL BLOCKED / NOT AUTHORIZED. Grok review: DEFERRED / NOT PERFORMED (not a PASS).**
Scope: isolated pure-Python synthetic detector source under `a_predicate_003/gate_g2/j1/`. No test, no Python execution of project code, no process, no signal, no GPU, no fixture materialisation, no merge.

## Git

| Item | Value |
|---|---|
| Repository | `leotree2020/OpenMythos` |
| Handoff branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-v01-review-claude-handoff-20261028` |
| **Baseline commit (verified by `git ls-remote` + `git fetch` + `FETCH_HEAD`)** | `02d79a26e4ad6b49527bc90e6be4fe9130b45cff` — matches the SHA given in the task |
| Development branch | `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028` (created from the baseline) |
| Implementation commit / final HEAD | see "Git SHA addendum" at the end (recorded in a separate commit to avoid self-reference) |
| Working tree at start | clean (0 porcelain lines); local G0/G1 authorization files are ignored, untracked and untouched |
| Bench pins re-verified at baseline | `observer.py 635e73b3…`, `registry.py 3f2179e1…`, `node.py 5bda87c6…`, `gate.py 7772c913…`, `common.py 9b6532bc…` — all equal to the handoff's recorded blobs; `bench/` diff against `8f9e8b2` and `4509143` is empty |
| Read order followed | SESSION_START_PROTOCOL, the V0.1 review/handoff checkpoint, the independent V0.1 review, the V0.1 fixture spec, the Claude Code handoff; then `bench/` read-only |

## Files (only these)

New, all under `research/mini_mythos/a_predicate_003/gate_g2/j1/`: `__init__.py`, `schema.py`, `judge.py`, `codec.py`, `oracle.py`, `README.md`, `tests/test_j1_static_and_unit.py`.
New doc: this checkpoint. Appended navigation: `docs/PROJECT_MAP.md` (+1 block), `docs/SESSION_START_PROTOCOL.md` (+1 block). Nothing else is changed; `bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, `tests/`, R3, Parcae, the model and all earlier G2 documents are untouched.

## Structure and dependencies

* `schema.py` — closed Lane S whitelist, strict types (`bool` never `int`; floats / non-JSON rejected), answer firewall (forbidden field-name parts and fixture-shaped string values are rejected; diagnostics never echo values), harness trust-map validation (roles capped by `ROLE_CEILING`; simulated roles must be `synthetic_assumption=True`; claim sources and the subject log never carry authority), immutable `Event` / `Identity` / `TrustEntry`. Imports `re`, `dataclasses`.
* `judge.py` — `evaluate(assertion_id, subject_observables, declared_trust_model)`; five discriminative handlers (ATTRIBUTION, UNIQUE_REGISTRY, ZOMBIE_AT_T, LOG_MATCHES_SEAL, WRITE_COMPLETE) and four SMOKE_ONLY handlers (PREVENT_PROOF, LAWFUL_REAP, EVIDENCE_USABLE, DELIVERY) that have **no PASS path**. Imports `codec`, `schema` only.
* `codec.py` — canonical JSON (NFC-reject, sorted keys, no floats), SHA-256, strict sidecar chain parser, `compare_seal` (MATCH / MISMATCH / UNDECIDABLE), record builders reserved for a later, separately authorised materialisation stage. Imports `hashlib`, `json`, `unicodedata`.
* `oracle.py` — Lane O: private expectations, the V0.1 document inventory (18 ids, 5 PASS / 5 FAIL / 8 BLOCKED, with a self-check), `grade_case`, `aggregate`; imports only `re`; imports nothing from the judge side and is imported by nothing on it.
* `tests/test_j1_static_and_unit.py` — test **source**: AST-level static contracts, inline illustrations of each handler, metamorphic M1–M4 skeletons, oracle behaviour, and a skipped placeholder for the 18 fixtures. It contains **no** fixture S/O data, hash or id-to-verdict table. **Every test is NOT TESTED.**
* Dependencies: Python standard library only; no third-party package, no GPU, no Bench import, no I/O.

## Static acceptance SRC-01 … SRC-08 (read-only source review; a static PASS is not a functional PASS)

| ID | Check | Status | Evidence |
|---|---|---|---|
| SRC-01 | New isolated branch from the verified handoff SHA; only permitted paths changed | **PASS** | Branch created from `02d79a26…`; `git diff --name-only 02d79a2 HEAD` lists only `gate_g2/j1/*`, one new checkpoint and two appended navigation files (verified after commit, see addendum). |
| SRC-02 | `judge.py` never sees Lane O data, fixture id or expected verdict; no hard-coded answer table | **PASS** (static) | `evaluate` has exactly the three Lane S parameters; handlers keyed by assertion id and evidence; `schema._scan` rejects Lane O field names and fixture-shaped strings before any judging; `grep` finds no `J1-F0x-y` literal on the judge side; `oracle.py` is not imported by, and imports nothing from, the judge side. |
| SRC-03 | Trust map is harness-bound; claims cannot self-upgrade | **PASS** (static) | Authority only from `declared_trust_model`, capped by `ROLE_CEILING`; unknown handle or kind outside the source's allowed set => INPUT_INVALID; `NODE_CLAIM_SIM` / `SUBJECT_LOG_READBACK` never authority; `raw_fields` cannot carry a role. |
| SRC-04 | 5 contrasting handlers + 4 labelled SMOKE_ONLY; strict FAIL / BLOCKED / PASS | **PASS** (static) | See `judge.py` handlers and `README.md` table; SMOKE_ONLY handlers return only BLOCKED, `coverage="SMOKE_ONLY"`, distinct basis codes; the oracle treats a SMOKE_ONLY PASS as an unproven PASS (test FAIL). |
| SRC-05 | Registry KINDS / RELEASED / DEAD semantics pinned to the actual B0; malformed / truncated input never safely accepted | **PASS** (static), with limitation | `B0_KINDS` copied by value from the frozen `registry.py`; RELEASED = intent, Z / DEAD / ECHILD never reap (basis codes); invalid, unreadable, torn or incomplete input is BLOCKED, never repaired. Limitation: real B0 records also carry float `mono`/`wall` and extra keys that the closed proposed schema rejects (OQ-7). |
| SRC-06 | Sidecar hash semantics never assert authenticity; no invented manifest trust or fixture hashes | **PASS** (static) | `codec` / README state integrity-of-bytes only; manifest trust comes only from a harness role; no fixture bytes or hashes exist; `build_record` / `serialize_log` are unused builders. |
| SRC-07 | No Bench / Parcae / G0 / G1 / R3 / frozen-evidence modification; no experiment code executed | **PASS, with one disclosed deviation** | Git scope as in SRC-01. No project code, no Bench, no test, no import, no process, no signal. **Deviation:** one `python3` interpreter was started by mistake with an empty stdin heredoc (no statements, no import, no file written, no network) while preparing an edit; it executed nothing, but strictly it is a Python invocation the task asked not to make. The edit was then done with the Edit tool. |
| SRC-08 | Checkpoint complete | **PASS** | This document plus the commits. |

**Not verified (cannot be, under the no-execution rule):** Python syntax of all new files, import resolution of the `j1` package, and the behaviour of every handler and test. The code was desk-checked by reading only; a syntax or logic error is possible and would surface only in a separately authorised CPU stage.

## Unresolved technical issues / minimal open questions (nothing was decided silently)

* **OQ-1** ZOMBIE_AT_T: V0.1 has no selector for T; several snapshots => BLOCKED.
* **OQ-2** ATTRIBUTION: join key `node_token` (+ `gate_token` if both present); whether a PASS must require a pre-RELEASED witness (now only a basis code).
* **OQ-3** LOG_MATCHES_SEAL: read-back observable shape, the added role `SUBJECT_LOG_READBACK`, and the sidecar record shape are implementer proposals; sealed-but-unparseable bytes => BLOCKED.
* **OQ-4** UNIQUE_REGISTRY completeness prerequisites are a proposal.
* **OQ-5** The four SMOKE_ONLY assertions have no defined PASS condition in V0.1 (no trusted source exists to establish them).
* **OQ-6 / OQ-7 / OQ-8 / OQ-9 / OQ-10** errno typing, closed `raw_fields` schema per kind and the byte contract, `monotonic_order` as a global harness ordinal, identity equality rule, trust-map format and its validator (details in `j1/README.md`).
* The oracle's inventory and the metamorphic cases are drafts; fixture materialisation, hashes, the 18-id run and any CPU guard design are separate, unauthorised stages.
* O-1…O-15 of the G2 design remain OWNER UNDECIDED; nothing here advances G2 REAL readiness.

## Test status

**All tests are NOT TESTED.** No pytest, no `unittest`, no Python script, no Bench experiment and no CPU acceptance command was run for this task; no run evidence exists; nothing is reported as an actual PASS. The expected values in the test source are intentions.

## Not done (by instruction)

No criteria freeze, no fixture S/O JSON or hashes, no CPU run, no real process / fork / wait / signal / janitor, no GPU or training, no merge, no PR, no change to Parcae / Bench / G0 / G1 / R3 / model architecture, no claim of a Grok review.

## Only next instruction

Hand the development branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028`, its final HEAD (addendum below), the diff against `02d79a26…` and this checkpoint to **ChatGPT** for an independent static code review. Only after that review and a separate owner authorization may fixture materialisation and a CPU acceptance run be considered. **Stop here: no tests, no merge, no next stage.**

## Git SHA addendum (separate documentation commit)

* Implementation commit (source + checkpoint + navigation): `f9151a9c6156ada24f6f4f77270eb004a713bf0a`
* Baseline commit: `02d79a26e4ad6b49527bc90e6be4fe9130b45cff` (diff `02d79a2..f9151a9c6156ada24f6f4f77270eb004a713bf0a`: 10 files, 1798 insertions, 0 deletions; 0 paths outside `gate_g2/j1/` and `docs/`; 0 paths in bench / gate_g0 / gate_g1 / prereg / evidence / tools / a_predicate_003/tests / Parcae / R3).
* This addendum is one further documentation-only commit; the final branch HEAD is the remote HEAD of `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028` and must not be confused with the implementation or baseline SHA.
* Working tree after commit: clean (the ignored local G0/G1 authorization files are untouched).
