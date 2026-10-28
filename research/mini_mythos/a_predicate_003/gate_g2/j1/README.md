# J1 — synthetic evidence judge (SYNTHETIC_CPU_ONLY) — implementation source

**Status: IMPLEMENTATION SOURCE PREPARED — STATIC REVIEW PENDING. CPU NOT TESTED. G2 CRITERIA NOT FROZEN. G2 REAL BLOCKED.**
Every file here was written without executing any of it (no pytest, no Python run, no import, no compile, no Bench run, no process, no signal, no GPU).
Nothing in this directory has a result. Grok review: `DEFERRED / NOT PERFORMED` (not a PASS).

## What J1 is — and is not

J1 is a **pure function over synthetic, already-deserialised, B0-shaped records**. It measures a *detector* (`measurement_target=J1_SYNTHETIC_DETECTOR`).
It says **nothing** about native B0 safety (`native_B0_safety_status=NOT_EVALUATED_BY_J1`). A test acceptance PASS means "the detector answered as
predeclared on synthetic input"; a known B0 defect that J1 identifies correctly is **not** a B0 safety PASS. The four simulated sensors
(`KERNEL_SNAPSHOT_SIM`, `G2_WITNESS_SIM`, `G2_WRAP_SIM`, `SEAL_MANIFEST_SIM`) are **synthetic assumptions granted by the harness**; they are not real B0
evidence and a PASS under them does not prove an actual independent child observer, a real release receipt, or an authenticated seal.

## Files

| File | Role | Imports |
|---|---|---|
| `schema.py` | Closed input whitelist, strict types (`bool` is never `int`), answer firewall (Lane O names / fixture-shaped strings rejected), harness trust-map validation, immutable `Event` / `Identity` / `TrustEntry` views. | `re`, `dataclasses` |
| `judge.py` | `evaluate(assertion_id, subject_observables, declared_trust_model)` and the nine handlers. | `codec`, `schema` |
| `codec.py` | Canonical JSON, SHA-256, strict sidecar chain parser, seal comparison (`MATCH` / `MISMATCH` / `UNDECIDABLE`). | `hashlib`, `json`, `unicodedata` |
| `oracle.py` | Lane O: private expectations, V0.1 document inventory (18 ids, 5/5/8), `grade_case`, `aggregate`. **Never imported by the judge side and imports none of it.** | `re` |
| `tests/test_j1_static_and_unit.py` | Test **source** (static contracts, inline illustrations, metamorphic skeletons). **NOT RUN.** Not the 18 fixtures. | stdlib `unittest`, `ast` |

No file imports `bench/`, `os`, `sys` (except the test path setup), `time`, `socket`, `signal`, `subprocess`, `ctypes` or any random source.

## Two lanes

* **Lane S (J1 sees):** `assertion_id`; a list of records `{source_handle, event_kind, monotonic_order, read_status, [node_token, identity, gate_token, raw_fields]}`;
  a harness-validated trust map `{source_handle: {role, synthetic_assumption, allowed_event_kinds, provenance_tier}}`.
* **Lane O (J1 never sees):** fixture id, canonical card, expected verdicts, behaviour labels, ground truth, paths, grades. `schema.validate_input` rejects any
  field **name** that contains such a marker and any string **value** shaped like a fixture id. Rejection is a BLOCKED input (`INPUT_INVALID`), diagnostics carry
  positions and rule codes only, never input values.

Authority is granted **only** by the trust map and is capped per role by `schema.ROLE_CEILING`; a record cannot upgrade itself, `NODE_CLAIM_SIM` and
`SUBJECT_LOG_READBACK` never carry authority, and a simulated role must be declared `synthetic_assumption=True`.

## Assertions

| Assertion | PASS means (only this) | FAIL | BLOCKED | Coverage |
|---|---|---|---|---|
| `ATTRIBUTION` | B0 `REGISTERED` identity agrees with a trusted *simulated* gate-child witness for the same node | witness identity differs | no / unreadable / conflicting trusted witness; untrusted claim only; duplicate REGISTERED | discriminative |
| `UNIQUE_REGISTRY` | no duplicate `(pid, starttime)` across nodes in the supplied, prerequisite-complete set | duplicate across distinct nodes (even if the rest is incomplete) | unreadable rows; ledger prerequisites not met; no REGISTERED record | discriminative |
| `ZOMBIE_AT_T` | the pinned identity was `Z` in the single trusted snapshot | any other valid state | no snapshot; several snapshots (T unselected); identity not pinned | discriminative |
| `LOG_MATCHES_SEAL` | bytes, length, final seq, last digest and run id match a trusted manifest | trusted, well-formed manifest positively disagrees | no / untrusted / malformed manifest; unreadable log; sealed bytes not a valid chain | discriminative |
| `WRITE_COMPLETE` | trusted simulated wrapper: 1 byte, no errno | 0 bytes or an errno | no trusted wrapper; untrusted claim only; contradictory result | discriminative |
| `PREVENT_PROOF` | — never in V0.1 | — | always (explains why) | **SMOKE_ONLY** |
| `LAWFUL_REAP` | — never in V0.1 | — | always; Z / DEAD / ECHILD claims reported as *not* reap | **SMOKE_ONLY** |
| `EVIDENCE_USABLE` | — never in V0.1 | — | always; seal mismatch vs integrity-only | **SMOKE_ONLY** |
| `DELIVERY` | — never in V0.1 | — | always; RELEASED is intent, a write result is not a recipient | **SMOKE_ONLY** |

The four SMOKE_ONLY handlers validate the same input and report distinct evidence-basis codes, but **V0.1 defines no trusted source that could establish
them, so they have no PASS path and make no claim of discrimination.** Do not read a green SMOKE_ONLY case as accuracy.

Semantics pinned from the frozen Bench (by value, never imported): `RELEASED` is the release *intent*, written before `os.write(R)`; `REGISTERED` is the
observer's registration of a creator-reported pid; same `ppid`, matching `(pid, starttime)` and a gate-fd observation do **not** by themselves prove unique
creation lineage; a hash chain or seal match proves only that these bytes are the sealed bytes, never that a kernel event happened; a zombie, a `DEAD`
record or `ECHILD` is never a lawful reap.

## Output

`evaluate` returns `assertion_id, subject_verdict, evidence_basis_codes (sorted), supporting_observable_refs ("<handle>#<order>"), accepted_claim (PASS only),
coverage, input_diagnostics, measurement_target, native_B0_safety_status, scope`. Unexpected programming errors are **not** swallowed into a verdict.

## Open questions (implementer proposals that need an owner / reviewer decision before any criteria freeze)

* **OQ-1** `ZOMBIE_AT_T`: how T is selected when several snapshots exist (V0.1 has no selector) — currently BLOCKED `MULTIPLE_SNAPSHOTS_T_NOT_SELECTED`.
* **OQ-2** `ATTRIBUTION`: join key is `node_token` (+ `gate_token` when both present); whether a PASS must require a pre-`RELEASED` witness (now only a basis code).
* **OQ-3** `LOG_MATCHES_SEAL`: the shape of the read-back observable (`log_utf8`, `run_id`), the extra role `SUBJECT_LOG_READBACK`, and the sidecar record shape
  (`seq, prev_digest, kind, body, event_digest`) are implementer proposals; sealed-but-unparseable bytes are BLOCKED, not FAIL.
* **OQ-4** `UNIQUE_REGISTRY` completeness prerequisites (contiguous order from 1, single first `RUN_START`, `INTENT` before `REGISTERED`, ...) are a proposal.
* **OQ-5** `EVIDENCE_USABLE` / `PREVENT_PROOF` / `LAWFUL_REAP` / `DELIVERY` have no defined PASS condition in V0.1.
* **OQ-6** `WRITE_COMPLETE`: errno is accepted only as an `E…` name string; an optional `byte` field must equal `"R"`.
* **OQ-7** The per-`event_kind` `raw_fields` schema is the implementer's closed proposal (V0.1 lists only field names); the byte contract (NFC reject, no floats) is a draft.
* **OQ-8** `monotonic_order` is treated as one harness-asserted ordinal across sources, not as a clock guarantee.
* **OQ-9** Identity equality is `(pid, starttime)` and, only when both sides carry them, `boot_id` / `pidns`.
* **OQ-10** The trust-map format and who validates it: `schema.validate_trust_model` is provided; the harness must still be reviewed.

## Static audit hints (for review; do not execute)

`judge.py` / `schema.py` / `codec.py` import only `re`, `dataclasses`, `hashlib`, `json`, `unicodedata` and each other; `oracle.py` imports only `re`; no module reads
a file, the clock, `/proc`, the environment or the network; `evaluate` has exactly the three Lane S parameters; no string literal on the judge side equals a
fixture id; verdict tables are keyed by assertion id and by evidence, never by fixture id.
