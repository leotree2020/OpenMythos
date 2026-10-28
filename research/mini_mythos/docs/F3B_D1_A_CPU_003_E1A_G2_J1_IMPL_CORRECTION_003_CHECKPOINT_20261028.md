# F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-003 — source correction checkpoint (2026-10-28)

**Status: SOURCE CORRECTION 003 PREPARED — INDEPENDENT STATIC REVIEW PENDING. J1 SYNTAX / IMPORTS / FUNCTIONAL TESTS NOT TESTED. 18 S/O FIXTURES NOT MATERIALIZED. G2 CRITERIA NOT FROZEN. FORMAL ORACLE ACCEPTANCE BLOCKED / NOT_READY. G2 REAL BLOCKED / NOT AUTHORIZED. Grok: DEFERRED / NOT PERFORMED (no dual review). O-1…O-15 OWNER UNDECIDED.**
Scope: exactly one finding, `J1-FIX2-REVIEW-F05` (HIGH, MALFORMED_FORKED). Source only. **No Python of any kind was invoked in this task** (no interpreter start, empty or otherwise; no import, py_compile, pytest, unittest, AST script), no process, no fork/wait/signal/janitor, no GPU, no fixture S/O data or hashes, no merge. Static status below is source reading only and is not a functional test PASS.

## Git

| Item | Value |
|---|---|
| Handoff branch (read-only, unchanged) | `d1-r3-a-cpu-003-e1a-g2-j1-fix3-handoff-20261028`, remote HEAD verified by `git ls-remote` + `git fetch` + `FETCH_HEAD` = **`24b3ffa26c5979f604e6208cb91713cfa8ed21ff`** (as announced) |
| Previous implementation (not edited) | `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028` @ `26da6082af73c0505d5520001d1cea6ec086df47` (code commit `e70b278a15ce6bf432c95c1b0f5853f13837f1ad`) |
| Correction branch | `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix3-20261028`, created from the handoff HEAD |
| Working tree at start | clean (0 porcelain lines) |
| Pinned blobs re-checked at the handoff HEAD (all equal to the task's values) | `j1/schema.py e8b1e343…`, `j1/judge.py cd5063db…`, `j1/tests/test_j1_static_and_unit.py e9fd2410…`, frozen `bench/registry.py 3f2179e1…`, `bench/observer.py 635e73b3…` |
| Correction commit / final HEAD | see "Git SHA addendum" (separate documentation commit, avoids self-reference) |

## Files changed (only these)

`a_predicate_003/gate_g2/j1/`: `schema.py` (edited), `judge.py` (edited), `README.md` (edited), `tests/test_j1_static_and_unit.py` (edited, unexecuted). `oracle.py`, `codec.py`, `__init__.py` unchanged. New: this checkpoint. Navigation appends: `docs/PROJECT_MAP.md`, `docs/SESSION_START_PROTOCOL.md`. Nothing else is touched (`bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, `a_predicate_003/tests/`, R3, Parcae, the model, old reviews / checkpoints, the 18 predeclared expected verdicts, the formal Oracle gate). Dependencies: Python standard library only (unchanged).

## FIX3-01 … FIX3-08 (static source review only)

Common environment: Git metadata, file reads and the editor tools. Common input: the reviewer's counterexample (FORKED without pid between INTENT and REGISTERED). Common "actual": source edits as listed; nothing executed.

| ID | Expected | Actual | Status |
|---|---|---|---|
| FIX3-01 | Verify handoff HEAD; new isolated branch; no disallowed path | Branch created from `24b3ffa2…`; scope verified after commit (addendum) | **PASS** (Git / static) |
| FIX3-02 | Frozen source: observer records the fork pid; fork starttime can be None; native integrity rejects a missing pid | Read directly: `bench/observer.py::_note_forked` writes `pid=pid, starttime=rec.forked_starttime` where `forked_starttime` is `None` if `/proc` is unreadable; `bench/registry.py::integrity_issues` reports `MALFORMED_FORKED` when `fk.get("pid")` is not an `int` (a missing pid included). Blobs unchanged. Note: the native check uses `isinstance(int)` (accepts bool); J1 stays stricter (non-bool, >= 1) on purpose. | **PASS** (source reading) |
| FIX3-03 | Optional normalised FORKED raw pid with a strict present-type validator; absent and malformed distinguished | `schema._v_pid` (`type is int` and `>= 1`; `None`, `0`, negatives, bools, strings, floats invalid) and `FORKED` optional key `pid` in `_RAW_SCHEMA`; absent keeps the input valid, present-but-invalid is `INPUT_INVALID` (`subject_verdict=None`). No FORKED starttime requirement. | **PASS** (static); functional **NOT TESTED** |
| FIX3-04 | `UNIQUE_REGISTRY` cannot PASS on missing / invalid fork pid; duplicate FAIL preserved; optional identity contradictions fail closed | `judge._ledger_prerequisite_problems`: every `FORKED` needs `raw_fields.pid` (else `MALFORMED_FORKED_PID_MISSING` -> subject BLOCKED `LEDGER_PREREQUISITE_FAILED_MALFORMED_FORKED_PID_MISSING`); an optional `FORKED.identity.pid` that differs -> `FORKED_IDENTITY_PID_CONFLICT` -> BLOCKED; no pid inferred from REGISTERED / creator / ppid / gate token. `_unique_registry` is untouched, so the sound duplicate `(pid, starttime)` FAIL is still decided before the lifecycle checks. | **PASS** (static); functional **NOT TESTED** |
| FIX3-05 | Test source A–F, not run; no formal fixture data | `TestFix2ReviewF05MalformedForked` (9 methods): A missing pid -> valid input, BLOCKED, specific code, no claim; A2 pid not inferred from REGISTERED; B valid pid -> finite-set PASS only; C `True/False/"4101"/None/0/-1/1.5` -> INPUT_INVALID; D no FORKED identity / starttime -> PASS; E duplicate pair + unrelated pid-less FORKED -> FAIL; F conflicting optional identity -> BLOCKED, consistent identity -> PASS; regression: orphan DEAD still blocks. Inline, fictional pids; no S/O JSON, hash or run evidence. | **PASS** (source written); **NOT TESTED / NOT RUN** |
| FIX3-06 | Oracle formal acceptance BLOCKED / NOT_READY; 18 V0.1 verdicts and prior F01–F04 fixes unchanged | `oracle.py` not touched (formal gate, pinned inventory, malformed-id handling unchanged); `judge.py` changes limited to the FORKED rule and a docstring line; correction-002 code (`_pair`, `_metadata_conflict`, `ORPHAN_RECORD`, pairwise witness checks) untouched. None of the 18 V0.1 case descriptions involves a FORKED record, so no expected verdict changes. | **PASS** (static) |
| FIX3-07 | No Python / tests / REAL; no frozen change; historic first-task deviation retained | Self-reported: only Git, `cat` / `head` / `sed` / `grep` / `awk` text reads and the editor tools were used; no interpreter, import, compile, pytest, unittest, fork/exec/signal/janitor, GPU. Git diff shows no frozen path touched. The first task's `SRC-07 strict procedural compliance FAIL (self-reported)` stays on record. | Git scope **PASS**; command history **SELF-REPORTED** |
| FIX3-08 | Checkpoint complete | This document + Git addendum | **PASS** (document) |

## Tests (all NOT TESTED / NOT RUN)

New: 9 methods in `TestFix2ReviewF05MalformedForked`. Earlier classes (static contracts, corrections 001 / 002, discriminative, SMOKE_ONLY, firewall, metamorphic) are unchanged and unrun; one skipped placeholder for the 18 fixtures. Syntax, imports and behaviour were desk-checked by reading only; an error is possible and would surface only in a separately authorised CPU stage.

## Unresolved issues (nothing decided silently)

* **OQ-13 (new):** `FORKED.pid` is not compared with the same node's `REGISTERED.pid`; the frozen rules do not check it and the task asked for a minimal change. Whether a mismatch should also block is open.
* A FORKED pid record is the observer's note of a creator-reported pid; it is not authenticated kernel lineage, and the native-to-J1 adapter remains unimplemented (the synthetic `raw_fields.pid` is a hand-authored normalisation).
* If a `FORKED.identity` is supplied the schema already requires a full identity (pid and starttime); the correction does not make it mandatory.
* OQ-1…OQ-12 of earlier checkpoints remain (OQ-11 gate association unauthenticated; OQ-12 formal acceptance prerequisites); the restated lifecycle rules are not mechanically compared with the frozen registry; G2 design O-1…O-15 OWNER UNDECIDED; four assertions remain SMOKE_ONLY.

## Only next instruction

Return branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix3-20261028`, its final HEAD (addendum), the diff against `24b3ffa2…` and this checkpoint to **ChatGPT** for an independent static review. Without a new owner authorization: no fixture materialisation, no Python or test execution, no criteria freeze, no merge, no CPU / G2 REAL, no Grok claim. **Stop here.**

## Git SHA addendum (separate documentation commit)

* Correction commit (source + tests + README + checkpoint + navigation): `8e75b9cc802dd7852ae83015c203a5b54c99dfb6`
* Baseline (handoff HEAD): `24b3ffa26c5979f604e6208cb91713cfa8ed21ff`; previous implementation HEAD `26da6082af73c0505d5520001d1cea6ec086df47` (untouched).
* Diff `24b3ffa..8e75b9cc802dd7852ae83015c203a5b54c99dfb6`: 7 files, 162 insertions, 3 deletions; changed J1 files are `schema.py`, `judge.py`, `README.md` and `tests/test_j1_static_and_unit.py` only (`oracle.py`, `codec.py` unchanged); 0 paths outside `gate_g2/j1/` and `docs/`; 0 paths in bench / gate_g0 / gate_g1 / prereg / evidence / tools / a_predicate_003/tests / Parcae / R3.
* This addendum is one further documentation-only commit; the final branch HEAD is the remote HEAD of `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix3-20261028` and must not be confused with the correction or baseline SHA.
* Working tree after commit: clean (ignored local G0/G1 authorization files untouched).
