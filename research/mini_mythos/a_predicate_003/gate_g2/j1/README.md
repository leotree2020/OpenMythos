# J1 — synthetic evidence judge (SYNTHETIC_CPU_ONLY) — implementation source

**Status: SOURCE CORRECTION 003 PREPARED (J1-FIX2-REVIEW-F05, on top of correction 002 F01…F04 and correction 001 F01…F06) — STATIC REVIEW PENDING. CPU NOT TESTED. G2 CRITERIA NOT FROZEN. G2 REAL BLOCKED.**
Correction 001 (task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-001`) answers the independent static review `CHANGES REQUIRED`; the historical F07 procedural
deviation (one accidental empty `python3` start in the first implementation task: `SRC-07 strict procedural compliance FAIL (self-reported)`, Git file scope
PASS) is preserved and is not rewritten. No Python of any kind was run in the correction (no import, compile, pytest, unittest, empty call).
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
| `oracle.py` | Lane O: private expectations **pinned to the versioned V0.1 inventory** (18 ids, 5/5/8, unchanged), `grade_case` (non-formal `inline_check_verdict`; formal `test_acceptance_verdict` unconditionally BLOCKED), `aggregate` (formal full-suite result unconditionally BLOCKED / NOT_READY; no `expected_ids` argument), `verify_fixture_attestation` (stub that accepts nothing). **Never imported by the judge side and imports none of it.** | `re` |
| `tests/test_j1_static_and_unit.py` | Test **source** (static contracts, inline illustrations, metamorphic skeletons). **NOT RUN.** Not the 18 fixtures. | stdlib `unittest`, `ast` |

No file imports `bench/`, `os`, `sys` (except the test path setup), `time`, `socket`, `signal`, `subprocess`, `ctypes` or any random source.

## Two lanes

* **Lane S (J1 sees):** `assertion_id`; a list of records `{source_handle, event_kind, monotonic_order, read_status, [node_token, identity, gate_token, raw_fields]}`;
  a harness-validated trust map `{source_handle: {role, synthetic_assumption, allowed_event_kinds, provenance_tier}}`.
* **Lane O (J1 never sees):** fixture id, canonical card, expected verdicts, behaviour labels, ground truth, paths, grades. `schema.validate_input` rejects any
  field **name** that contains such a marker and any string **value** shaped like a fixture id. Rejection is a BLOCKED input (`INPUT_INVALID`), diagnostics carry
  positions and rule codes only, never input values.

Authority is granted **only** by the trust map and is capped per role by `schema.ROLE_CEILING`; a record cannot upgrade itself, `NODE_CLAIM_SIM` and
`SUBJECT_LOG_READBACK` never carry authority, and every source (the B0-shaped ledger and the subject log included) must be declared `synthetic_assumption=True`; the trust map itself is an unauthenticated, hypothetical declaration by an external harness.

## Assertions

| Assertion | PASS means (only this) | FAIL | BLOCKED | Coverage |
|---|---|---|---|---|
| `ATTRIBUTION` | **retrospective** agreement between the B0-shaped `REGISTERED` identity and a trusted *simulated* gate-child witness that carry the **same explicit, non-empty gate/ticket token** | identity differs while the gate association is identical | no / unreadable / conflicting witness; **gate association absent on either side or contradictory** (`GATE_ASSOCIATION_UNVERIFIED` / `_CONFLICT`); untrusted claim only; duplicate REGISTERED | discriminative |
| `UNIQUE_REGISTRY` | no duplicate `(pid, starttime)` among the **finite supplied** records that pass the internal lifecycle checks restated from the frozen registry (run_id + observer_pid, RUN_END, creator chain, ordering) — nothing about omitted original rows | duplicate across distinct nodes (even if the rest is incomplete) | unreadable rows; any lifecycle / metadata check failed; no REGISTERED record | discriminative |
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

`evaluate` returns `assertion_id, input_valid, result_kind, subject_verdict (None when the input is invalid), input_domain, trust_basis, native_b0_adapter_status, evidence_basis_codes (sorted), supporting_observable_refs ("<handle>#<order>"), accepted_claim (PASS only),
coverage, input_diagnostics, measurement_target, native_B0_safety_status, scope`. Unexpected programming errors are **not** swallowed into a verdict.

## Correction 001 — what changed and what did not

| Finding | Change (source only; none of it executed) |
|---|---|
| F01 | `evaluate` returns `input_valid` / `result_kind`; a malformed or Lane-O-tainted input gives `input_valid=False`, `result_kind=INPUT_INVALID`, `subject_verdict=None` (not a "BLOCKED"). The oracle treats it, any input diagnostic, an `INPUT_INVALID` basis code or a malformed output as a **broken instrument**: inline check BLOCKED, never PASS. |
| F02 | Expectations must equal the versioned inventory tuple. `aggregate(case_results)` has no `expected_ids`, never trusts caller-supplied grade rows and is **unconditionally BLOCKED / NOT_READY**; `grade_case` returns a non-formal `inline_check_verdict` and a formal `test_acceptance_verdict` that is always BLOCKED. The 18 predeclared expected verdicts are unchanged. |
| F03 | ATTRIBUTION requires the same non-empty `gate_token` on the REGISTERED record and on every trusted witness; absent -> BLOCKED, contradictory -> BLOCKED; unreadable witnesses block instead of being dropped; the result stays retrospective (not PREVENT_PROOF). Native B0 `REGISTERED` records carry no gate token, so native-shaped input stays BLOCKED. |
| F04 | RUN_START needs a non-empty string `run_id` and a non-bool integer `observer_pid`; RUN_END needs the same `run_id` and a boolean `cleanup_confirmed`, and a confirmed RUN_END needs `DEAD` for every non-janitor node; creator must be registered before a child's INTENT; PASS is claimed only for the finite supplied validated set. Duplicate-identity FAIL is preserved. |
| F05 | Trust is stated as a hypothetical, unauthenticated declaration by an external harness (`trust_basis`); every source, the B0-shaped ledger included, must be declared `synthetic_assumption=True`. J1 does not and cannot authenticate the map. |
| F06 | J1 is synthetic-only (`input_domain`). A native-to-J1 adapter is an OPEN question and **NOT IMPLEMENTED**; direct compatibility with native `bench/registry.py` records (float `mono` / `wall`, extra keys) is **NOT SUPPORTED** (`native_b0_adapter_status`). |

## Correction 002 (task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-002`) — what changed

| Finding | Change (source only; nothing executed, no Python invoked) |
|---|---|
| J1-FIX-REVIEW-F01 | `UNIQUE_REGISTRY` lifecycle checks add `ORPHAN_RECORD` (frozen `integrity_issues`: any node with records but no INTENT, e.g. DEAD-only / ABORTED-only -> BLOCKED) and the stronger synthetic-only `RECORD_BEFORE_INTENT`. A well-formed INTENT then DEAD is not an orphan. A sound duplicate FAIL is still evaluated first. |
| J1-FIX-REVIEW-F02 | Duplicate detection uses exactly the V0.1 key `(pid, starttime)` (`judge._pair`), not `Identity.same_instance`; optional `boot_id` / `pidns` can no longer hide an equal pair. Two populated, different `boot_id` / `pidns` values inside one supplied ledger are reported separately (`LEDGER_BOOT_OR_PIDNS_INCONSISTENT`) and block the PASS path. `same_instance` itself is unchanged (still used by `ZOMBIE_AT_T`). |
| J1-FIX-REVIEW-F03 | ATTRIBUTION compares ALL known identities pairwise (registered + every node witness): a populated `boot_id` / `pidns` conflict between any two blocks even when a third omits it (`IDENTITY_METADATA_CONFLICT`); witnesses must agree on `(pid, starttime)` (`CONFLICTING_TRUSTED_WITNESSES`); a trusted witness (or another REGISTERED record) carrying the same gate token for a different node blocks (`GATE_SHARED_WITH_OTHER_NODE_UNRESOLVED`); the verdict does not depend on record order. Agreement / mismatch is decided on the `(pid, starttime)` pair. Still retrospective, synthetic-only, unauthenticated trust. |
| J1-FIX-REVIEW-F04 | `oracle.aggregate` type-checks every row and every `fixture_id` before any set / count operation: list, dict, bool, int, float, None or a non-dict row is a diagnostic reason, never an exception. Formal result stays BLOCKED / NOT_READY; `expected_ids` still does not exist. |

## Correction 003 (task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-003`) — synthetic `FORKED.raw_fields.pid`

Finding `J1-FIX2-REVIEW-F05` (HIGH): `UNIQUE_REGISTRY` could return a finite-set PASS for a transcript whose `FORKED` record reported no pid, although the frozen
`bench/registry.py::integrity_issues` reports `MALFORMED_FORKED` for it. Source only; nothing executed, no Python invoked.

* **Normalised field:** the synthetic `FORKED` event may carry `raw_fields.pid`, the projection of the native FORKED record's source-reported fork pid
  (`bench/observer.py::_note_forked` writes `pid=<fork pid>`). It is an *optional* schema key on purpose.
* **Absent:** the input stays valid (`input_valid=True`) but `UNIQUE_REGISTRY` is subject BLOCKED (`LEDGER_PREREQUISITE_FAILED_MALFORMED_FORKED_PID_MISSING`). The pid is
  never inferred from a later REGISTERED record, a creator claim, `ppid`, a gate token or `FORKED.identity`.
* **Present but invalid** (bool, string, `None`, `0`, negative, float): `INPUT_INVALID`, `subject_verdict=None`.
* **Valid:** eligible for the remaining finite-ledger checks; the PASS claim is still limited to the finite supplied set.
* **`FORKED` starttime stays optional:** the frozen observer may record `starttime=None`. If an optional `FORKED.identity` is supplied it must not contradict
  `raw_fields.pid` (`FORKED_IDENTITY_PID_CONFLICT` -> BLOCKED). A FORKED pid record is not authenticated kernel lineage, and no native log adapter exists.
* **Preserved:** the sound duplicate `(pid, starttime)` FAIL is still decided before the lifecycle checks; corrections 001 / 002, the 18 V0.1 expected verdicts and the
  formal Oracle BLOCKED / NOT_READY are unchanged. `FORKED.pid` vs `REGISTERED.pid` agreement for the same node is **not** checked (open question OQ-13).

## Open questions (implementer proposals that need an owner / reviewer decision before any criteria freeze)

* **OQ-13 (new)** Whether a FORKED pid that differs from the same node's REGISTERED pid must also block (the frozen registry rules do not check it; the correction deliberately stayed minimal).

* **OQ-11 (new)** The gate/ticket association is currently a `gate_token` field on the synthetic `REGISTERED` record and on the witness. Whether it should instead be a separate trusted binding record (and who may issue it) is undecided; native B0 supplies none.
* **OQ-12 (new)** What independent attestation (sealed Lane S / Lane O bytes, verifier, reviewed CPU guard, authenticated trust-map origin) would make formal acceptance ready; until then it is BLOCKED by design.

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
