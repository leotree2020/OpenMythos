# OpenMythos — Claude Code Correction 003: J1 MALFORMED_FORKED PID (SOURCE-ONLY)

**Task:** `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-003`  
**Date:** 2026-10-28 · **Prepared by:** ChatGPT (research reviewer) · **Actual code implementer:** Claude Code, only after the project owner submits this bounded task.  
**Authority:** **Write source and unexecuted test source only. No Python interpreter, no import/compile/test, no fixture materialization, no process experiment, no GPU, no criteria freeze, no merge, no G2 REAL.** This handoff itself does **not** execute a Claude Code session.

## 0. Read-first Git and scientific baseline

Repository `leotree2020/OpenMythos`.

- **Pinned independent review branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix2-static-review-20261028`, verified remote HEAD **`801489ec5b42c9d8e5e27bb11c619fe3f6506312`**.
- **Pinned latest Claude Code implementation code:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028`, verified remote HEAD **`26da6082af73c0505d5520001d1cea6ec086df47`** (code commit `e70b278a15ce6bf432c95c1b0f5853f13837f1ad`). The review branch contains the same source plus later review documents; neither is to be edited in place.
- **New handoff documentation branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix3-handoff-20261028`, created from the pinned review SHA. **Its FINAL HEAD will be different after the task/checkpoint commits.** At implementation start independently fetch the handoff branch's *actual current final remote HEAD*, verify required files and use that exact SHA as the new, isolated code branch base.
- **Latest source reviewer report:** `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_002_INDEPENDENT_STATIC_REVIEW_001.md`, Git blob `eb16fc45752605d487eb14d0cbdca0b213c087d8`.
- **Read-first reviewer checkpoint:** `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_002_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, Git blob `0f38b3e3f8c8d3921f0cbfadcc9406d3c8221313`.
- **Read from this handoff branch in order:** `research/mini_mythos/docs/SESSION_START_PROTOCOL.md` → **new** `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX3_HANDOFF_CHECKPOINT_20261028.md` → this full task file → prior independent report/checkpoint → V0.1 specification and current J1 source → read-only frozen `bench/registry.py`, `bench/observer.py`.
- **Pinned source blobs:** current `gate_g2/j1/schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`; `j1/judge.py=cd5063dbf2754b925a9871cc7d478076ca680cd7`; `j1/oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`; `j1/tests/test_j1_static_and_unit.py=e9fd2410a382dd569439cadfca79ca822cf6daeb`; frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`; `bench/observer.py=635e73b34203219a3687f86332d0e82362b89670`.
- **STOP/BLOCKED** if the source branch moved, a blob differs, an input is missing or local Git contains unknown modifications. Never silently rebase, overwrite or assume a previous chat SHA is the live branch head.

## 1. Exactly one technical finding — `J1-FIX2-REVIEW-F05` (HIGH)

Independent reviewer found that `UNIQUE_REGISTRY` may return scoped subject **PASS** for a synthetic B0-shaped transcript containing `FORKED` with **no source-reported PID**, despite the frozen native registry integrity check requiring one.

**Native source evidence (READ ONLY):**
- `bench/observer.py:_note_forked`, approximately lines 89–102, writes `reg.write("FORKED", node_id=..., pid=pid, starttime=rec.forked_starttime, creator=..., ...)`. **`starttime` may be `None` if /proc could not be read; fork PID is still recorded.**
- `bench/registry.py:integrity_issues`, approximately lines 69–80, reports `MALFORMED_FORKED` when `fk.get("pid")` is not an integer. The native check uses `isinstance(int)`; this **does not excuse a bool-as-int in J1's stricter established synthetic schema**, and does not establish true kernel provenance.
- `gate_g2/j1/schema.py:212–244` currently permits `FORKED` with optional `identity`, and its `raw_fields` has no native `pid` projection.
- `gate_g2/j1/judge.py:_ledger_prerequisite_problems` validates FORKED ordering but not fork pid; `_unique_registry` can then grant limited finite-ledger PASS if valid REGISTERED exists. Exact native-to-J1 adapter **does not exist**.

**Proposed counterexample — NOT EXECUTED:** single synthetic declared B0_LEDGER handle `L` with contiguous source orders: `RUN_START(run_id="run-1", observer_pid=300)` → `INTENT(nA,creator=O)` → `FORKED(nA)` with **no identity and no PID** → `REGISTERED(nA,pid=4101,starttime=101,ppid=4100)`. `read_status="OK"` for all. Current code can give `UNIQUE_REGISTRY = PASS`; frozen `integrity_issues` flags malformed fork. This is a **source-derived hypothesis**, not a test result.

## 2. Minimal source change — use ONE normalized synthetic fork PID field

Use a minimal, readable normalization **without building a real registry adapter**:

1. Add `raw_fields.pid` as an **optional, type-validated normalized field** for the synthetic `FORKED` event in `j1/schema.py::_RAW_SCHEMA`. It corresponds solely to native FORKED's **source-reported `pid`**. An optional schema key is intentional: it lets a well-shaped but **missing evidence field** reach the ledger's epistemic `BLOCKED` condition, rather than confusing it with a malformed input instrument.
2. If `raw_fields.pid` is present, require **non-bool integer PID >= 1** through a small strict validator (use existing primitives; no new dependency). A present but bad value (e.g. `True`, `0`, `"4101"`, `None`, negative integer) is **INPUT_INVALID** in the input-validation channel, not subject PASS or an ordinary valid-evidence BLOCKED. **`raw_fields.pid` absent** remains schema-admissible and becomes a subject `BLOCKED` under `UNIQUE_REGISTRY` when a positive completeness/uniqueness claim would otherwise be made.
3. In `j1/judge.py::_ledger_prerequisite_problems`, when encountering `FORKED` in a supplied synthetic ledger, require that its `raw_fields.pid` be present and be a valid positive non-bool integer before **any `UNIQUE_REGISTRY=PASS`**. Missing → specific source/lifecycle code such as `LEDGER_PREREQUISITE_FAILED_MALFORMED_FORKED_PID_MISSING`, `subject_verdict=BLOCKED`; present valid → no error from this rule. Do not infer pid from a later REGISTERED record, creator claims, `FORKED.identity`, PPID or gate token.
4. **Do not make `FORKED.identity.starttime` mandatory**. Frozen observer may record `starttime=None` on FORKED. If optional synthetic `FORKED.identity` is supplied, a conflict with `raw_fields.pid` cannot be silently treated as validated evidence; fail-closed `BLOCKED` (or record input-invalid according to current strict schema). Do not equate `FORKED` PID record with authenticated kernel lineage.
5. Keep current `_unique_registry` **positive contradiction ordering**: observed duplicate `(pid,starttime)` across different adequately source-qualified REGISTERED nodes can return **subject FAIL** before unrelated ledger incompleteness checks, as the existing reviewed V0.1 behavior requires. Missing FORKED pid must **never** yield a subject PASS; don't let the new rule destroy a sound duplicate FAIL. The official formal Oracle run acceptance remains **BLOCKED/NOT_READY** no matter what the synthetic detector reports.
6. In `j1/README.md`, explicitly document **synthetic normalized `FORKED.raw_fields.pid`**, missing→BLOCKED, invalid present→INPUT_INVALID, valid→eligible for further finite-ledger checks, `starttime` optional, and no native log adapter/provenance claim. Do not revise old checkpoint/review texts.

**Do not redesign `Identity`, `ZOMBIE_AT_T`, ATTRIBUTION, the gate/ticket trust map, codec or Oracle.** No new FORKED event source, source tier, trust authority, process runtime, genuine gate receiver witness or GPU usage.

## 3. Required unexecuted static test source only (negative and positive controls)

Add small test methods to `gate_g2/j1/tests/test_j1_static_and_unit.py` (or a tiny new source-only test file within that subtree). **Do not execute, import, compile or materialize any formal fixture data**:

| Case | Synthetic input (starting from a valid RUN_START/INTENT/REGISTERED transcript) | Proposed subject/instrument result |
|---|---|---|
| A — missing pid | Insert `FORKED(nA)` between INTENT and REGISTERED, with `raw_fields={}` and **no identity** | `input_valid=True`, `UNIQUE_REGISTRY=BLOCKED`, specific missing-fork-pid basis |
| B — valid pid | Same as A but `FORKED.raw_fields.pid=4101` | `input_valid=True`; `UNIQUE_REGISTRY=PASS` **only scoped to the finite supplied set**, not original log completeness |
| C — wrong type | Same as B with `pid=True`, `"4101"`, `None` or `0` | `input_valid=False`, `result_kind=INPUT_INVALID`, `subject_verdict=None` |
| D — unknown fork starttime | `FORKED.raw_fields.pid=4101`, **no FORKED identity/starttime**; REGISTERED has validated identity | Remains eligible for finite-ledger subject PASS; do not require fork starttime |
| E — duplicate still decisive | Two REGISTERED nodes with same `(pid,starttime)`, plus an unrelated FORKED without pid | `UNIQUE_REGISTRY=FAIL` from positive duplicate evidence **without granting an invalid-ledger PASS** |
| F — optional conflicting identity | `FORKED.raw_fields.pid=4101`, optional `FORKED.identity.pid=4102` with otherwise valid identity | `UNIQUE_REGISTRY` must not PASS; prefer scoped `BLOCKED` and a provenance/conflict basis |

These are **planned assertions in unexecuted test SOURCE**, not experimental results. New tests may not become official V0.1 S/O fixture IDs; all 18 original `expected_subject_verdict` values must remain **unchanged**, with 5 prospective PASS / 5 FAIL / 8 BLOCKED **not actual**.

## 4. Strict allowed diff and no-run boundary

**Allowed source:** `research/mini_mythos/a_predicate_003/gate_g2/j1/schema.py`, `judge.py`, `README.md`, `tests/test_j1_static_and_unit.py` only as needed for this finding. One **NEW** correction-003 checkpoint under `research/mini_mythos/docs/`; append-only navigation to `docs/PROJECT_MAP.md` and `docs/SESSION_START_PROTOCOL.md` if useful. New code branch only.

**Forbidden:** edits to `bench/`, native Parcae, `gate_g0/`, `gate_g1/`, R3, `prereg/`, `evidence/`, existing tests/tools outside isolated J1, original G2 spec/18 expected tuples, old reviewer/checkpoints, `oracle.py`, `codec.py`, model architecture, optimizer/training, dependency/version changes, releases and merges.

**No command may invoke Python or execute source/tests**, including even empty `python3`, `py_compile`, `pytest`, `unittest`, Python AST, import, syntax check by interpreter, a `python`-based editor, or fixture generator. Allowed: Git diff/status/fetch/commit, read-only source/text tools, editor text changes, static descriptive review. No test execution, no fork/exec/subprocess/wait/signal/janitor, no actual native B0 log readback, GPU, CPU experimental validation or REAL. If a helper tool would internally run Python or a live process experiment, **do not use it**. Any incident must be documented as procedural **FAIL**, not hidden.

**Static review PASS does not establish syntax/behavior PASS.** A future separate CPU authorization is needed for even one runtime assertion.

## 5. Correction 003 acceptance checklist (STATIC ONLY; no test execution)

| Gate | Expected before stop | Status required |
|---|---|---|
| FIX3-01 | Verify final handoff remote HEAD, derive new isolated code branch; no disallowed changed paths | PASS / FAIL / BLOCKED |
| FIX3-02 | Frozen source checked: observer's fork PID exists; fork starttime can be None; native integrity rejects missing pid | PASS / FAIL / BLOCKED |
| FIX3-03 | J1 schema declares optional normalized FORKED raw pid with strict present-type validator, absent vs malformed distinguished | PASS / FAIL / BLOCKED |
| FIX3-04 | UNIQUE_REGISTRY cannot PASS on missing/invalid fork pid; duplicate known pair FAIL preserved; optional identity contradictions fail closed | PASS / FAIL / BLOCKED |
| FIX3-05 | New negative/positive test **source** A–F written, **not run**; 18 official fixture bytes/hashes not generated | PASS / FAIL / BLOCKED; behavior NOT TESTED |
| FIX3-06 | Oracle formal acceptance remains BLOCKED/NOT_READY; V0.1 expected 18 cases and previous F01–F04 fixes unchanged | PASS / FAIL / BLOCKED |
| FIX3-07 | No Python/tests/REAL invoked (self-reported), no frozen Bench/Parcae/model changes; historic first-task Python deviation retained | Git-scope PASS / FAIL; command-history SELF-REPORTED |
| FIX3-08 | Checkpoint: purpose, environment, inputs, expected/actual source diffs, dependencies, Git SHA/status, open OQs, actual statuses and one next instruction | PASS / FAIL / BLOCKED |

**Global stages:** `SOURCE CORRECTION 003 PREPARED — INDEPENDENT STATIC REVIEW PENDING`; `SYNTAX/IMPORTS/FUNCTIONAL TESTS NOT TESTED`; `18 S/O NOT MATERIALIZED`; `G2 CRITERIA NOT FROZEN`; `FORMAL ORACLE BLOCKED/NOT_READY`; `G2 REAL BLOCKED`; `GROK DEFERRED`; `O-1…O-15 OWNER UNDECIDED`.

## 6. Commit, push, checkpoint, STOP

1. Verify actual **handoff branch final remote HEAD** and required blobs/checkpoint. If mismatch/unknown local edits, mark BLOCKED and STOP.
2. Create new isolated correction branch from that exact commit; implement only source changes above and unexecuted test source. Preserve frozen upstream and previous commits.
3. Read source and inspect only Git status/diff for self-review; **no Python or test commands**, no fixtures/run.
4. Write a new correction-003 checkpoint (not overwrite prior), with FIX3-01…08 expected vs actual/source evidence and real Git SHAs, dependencies, unresolved questions, one next command. Commit/push changes and validate remote branch/diff and local status. A separate SHA addendum can be committed without rewriting source.
5. **STOP**. Return code branch, source commit, final HEAD, exact diff paths, checkpoint for ChatGPT independent **static** review. No CPU/REAL, no Grok PASS, no merge.

## 7. Copy-ready Claude Code starter

> OpenMythos task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-003`. You are the designated **SOURCE-ONLY** developer for one HIGH residual finding `J1-FIX2-REVIEW-F05: MALFORMED_FORKED`. On handoff branch `d1-r3-a-cpu-003-e1a-g2-j1-fix3-handoff-20261028`, read `docs/SESSION_START_PROTOCOL.md`, `docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX3_HANDOFF_CHECKPOINT_20261028.md`, the full `gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_003_HANDOFF_20261028.md` and previous reviewer report. **Fetch and pin the handoff's actual FINAL remote HEAD; create a NEW isolated code branch from it.** Fix only synthetic FORKED's source-reported PID validity and UNIQUE_REGISTRY's finite-ledger false-PASS path; do not require FORKED starttime, do not modify native Bench/Parcae, prior four fixes, V0.1 18 verdicts, formal Oracle BLOCKED/NOT_READY, or the model. Add minimal **unexecuted** test source A–F; edit only `gate_g2/j1/{schema.py,judge.py,README.md,tests/test_j1_static_and_unit.py}`, a new task checkpoint and navigation. **NEVER invoke Python/import/compile/tests/fixtures, processes, GPU, CPU experiment or G2 REAL.** Record FIX3-01…08 and Git SHAs/status, commit/push and STOP; return diff/checkpoint to ChatGPT for independent static review.
