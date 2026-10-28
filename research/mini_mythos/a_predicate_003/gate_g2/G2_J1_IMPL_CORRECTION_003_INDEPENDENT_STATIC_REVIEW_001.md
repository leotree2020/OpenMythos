# F3B-D1-A-CPU-003 — Correction 003 independent J1 SOURCE static review 001

**Date:** 2026-10-28 · **Reviewer:** ChatGPT · **Review method:** GitHub remote read-only source inspection + independently pinned Git diff; **NO Python, import, compile, pytest, unittest, source execution, fixture materialization, process experiment, fork/wait/signal, GPU or model runtime**.

**Developer source branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix3-20261028`, remote HEAD **VERIFIED `38e8a9141ebd738a34628acc928adb28cd8c54cf`**.  
**Correction baseline:** `24b3ffa26c5979f604e6208cb91713cfa8ed21ff`; developer source commit `8e75b9cc802dd7852ae83015c203a5b54c99dfb6`.  
**Developer checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_003_CHECKPOINT_20261028.md`, blob `77e17271c6218e4cb99f9aa207755fdf9adfe096`.  
**Relevant Git blobs read:** `j1/schema.py=551c4a01ed37f73c809776e123f98f6d055ac998`; `j1/judge.py=8aef00cb1b66ee107c91086cd537c759858940cd`; `j1/tests/test_j1_static_and_unit.py=ab71b1dca8e90cc63f2763ed5391a492200f6dc8` independently fetched at the pinned source HEAD; `j1/README.md=56be17c751ec9bc0b66a82d9d08c1e38a4d01eaf`. Frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`; `bench/observer.py=635e73b34203219a3687f86332d0e82362b89670` (unchanged).  
**Original finding:** `J1-FIX2-REVIEW-F05` HIGH from `G2_J1_IMPL_CORRECTION_002_INDEPENDENT_STATIC_REVIEW_001.md` and prior checkpoint. The original counterexample was source-inferred, NOT EXECUTED.

## Independent verdict

**`J1 CORRECTION 003 SOURCE-STATIC REVIEW: PASS — LIMITED TO THE SPECIFIED MALFORMED_FORKED PID DEFECT`.** The source now distinguishes (a) missing `FORKED.raw_fields.pid` (schema-valid but an incomplete assertion, hence subject BLOCKED) from (b) provided but invalid pid (INPUT_INVALID, **no** subject verdict) and (c) provided valid pid (eligible for subsequent finite supplied-ledger validation). The same prior confirmed duplicate REGISTERED pair continues to produce subject FAIL before unrelated lifecycle deficiencies. The optional `FORKED.identity.pid` conflict is fail-closed. This **closes the one requested source-review finding on paper only**.

**`J1 SOURCE IMPLEMENTATION STATIC PASS — SCOPE-LIMITED; FUNCTIONAL CORRECTNESS NOT TESTED`**. This is a **static code/design review result**, not syntax, import, actual 18-case CPU acceptance, J1 formal Oracle PASS, B0 kernel safety, native Parcae reproduction, or Mythos model progress.

**`FORMAL ORACLE ACCEPTANCE BLOCKED/NOT_READY`; `18 FORMAL FIXTURES NOT MATERIALIZED`; `G2 CRITERIA NOT FROZEN`; `G2 CPU NOT TESTED/NOT AUTHORIZED`; `G2 REAL BLOCKED/NOT AUTHORIZED`; `Grok DEFERRED/NOT PERFORMED, NOT PASS`; `O-1…O-15 OWNER UNDECIDED`.** Do not auto-advance on a source-static PASS.

## Git scope VERIFIED independently

Remote HEAD `38e8a9141ebd738a34628acc928adb28cd8c54cf` matches the developer's declared final HEAD. Comparing it to `24b3ffa26c5979f604e6208cb91713cfa8ed21ff` reports **2 commits, 7 changed files, +170/-3 lines**. Changed J1 files: `gate_g2/j1/schema.py`, `judge.py`, `README.md`, `tests/test_j1_static_and_unit.py`; added developer checkpoint and two documentation navigation updates. **`oracle.py`, `codec.py`, prior implementation branch, Bench, Parcae, R3, G0/G1, existing prereg/evidence/tools, model architecture were NOT modified.** The developer's local clean tree and command history (`no Python`) are **SELF-REPORTED**, not independently observable via remote Git data. The first implementation task's earlier empty Python invocation remains a historical procedural FAIL, not retroactively erased.

## Frozen source evidence and comparison

1. `bench/observer.py:_note_forked` (approx. lines 89–102) writes `FORKED` with `pid=pid` and `starttime=rec.forked_starttime`, where `starttime` can be `None` when /proc is unreadable.
2. `bench/registry.py:integrity_issues` (approx. lines 65–82) reports `MALFORMED_FORKED` if `fk.get("pid")` is not an integer, including if absent. Frozen native implementation uses `isinstance(v,int)`, which happens to accept bool; J1's previously established strict synthetic scalar rule excludes bool, as documented.
3. `j1/schema.py:169–171,217–246`: new strict `_v_pid` checks **`type(value) is int and value >= 1`**; `FORKED._RAW_SCHEMA` contains **OPTIONAL** `raw_fields.pid`; `FORKED.identity` is still optional. This is a **hand-authored synthetic normalization**, not an automatically trusted native registry adapter.
4. `j1/judge.py:165–173`: for every `FORKED`, if `raw_fields.pid` is missing/invalid then `MALFORMED_FORKED_PID_MISSING` becomes a positive-completeness prerequisite failure; if `FORKED.identity` exists with a different PID, `FORKED_IDENTITY_PID_CONFLICT` becomes another prerequisite failure. Because provided invalid values fail schema first, the actual "missing" ledger path applies to schema-valid absent values.
5. `j1/judge.py:_unique_registry` (approx. lines 330–377) still checks independently observed duplicate REGISTERED `(pid,starttime)` **before** it checks untrustworthy/incomplete ledger prerequisites, and refuses PASS when `LEDGER_PREREQUISITE_FAILED_*` exists. Normal finite-ledger PASS does **not** claim original log completeness.
6. `oracle.py` unchanged: formal acceptance remains `BLOCKED/NOT_READY` even if a detector returns PASS. This guards against equating a limited subject PASS with a passed formal experiment, but **does not** itself provide experimental evidence.

## FIX3-01…FIX3-08 independent acceptance matrix (static-only)

| Criterion | Source observation | Independent status |
|---|---|---|
| `FIX3-01` source baseline, isolated branch/diff | Verified exact SHA and 7 permitted files, +170/-3 | **PASS (GIT/SCOPE)** |
| `FIX3-02` actual frozen FORKED fields | Frozen observer writes PID, can leave starttime unknown; registry checks presence/type | **PASS (SOURCE)** |
| `FIX3-03` field + strict validation | Optional `FORKED.raw_fields.pid` with `_v_pid`; malformed provided value travels via `INPUT_INVALID`, absent stays schema-valid | **PASS (SOURCE)** |
| `FIX3-04` absence and contradiction fail-closed | Judge `MALFORMED_FORKED_PID_MISSING` / `FORKED_IDENTITY_PID_CONFLICT` + duplicate pair FAIL earlier | **PASS (SOURCE)** |
| `FIX3-05` controls A–F | Nine new unexecuted methods under `TestFix2ReviewF05MalformedForked`, including malformed PID variants and regression | **PASS (TEST SOURCE EXISTS); BEHAVIOR NOT TESTED** |
| `FIX3-06` prior fixes, Oracle, 18 expectations unchanged | Only four allowed J1 files changed; `oracle.py` and V0.1 inventory unchanged; source construction preserves prior ordering | **PASS (DIFF/STATIC, LIMITED)** |
| `FIX3-07` no Python, frozen scope, historical deviation | Frozen path diff PASS; Claude's claimed zero interpreter/test calls cannot be independently verified using remote GitHub | **GIT PASS; COMMAND HISTORY SELF-REPORTED; FUNCTIONAL NOT TESTED** |
| `FIX3-08` checkpoint completeness | Developer document records purpose, input, expected, actual source, Git SHA, dependencies, OQ-13, next step and NOT TESTED | **PASS (DOCUMENT)** |

**None of these static PASS values represent an executed experiment or CPU behavior measurement.** The nine new test methods, previously authored source tests and the 18 official fixtures were NOT RUN.

## Unresolved scientific questions / limits — not newly discovered code failures

- **OQ-13 (FORKED.pid vs REGISTERED.pid):** The source does not verify equality between the FORKED and subsequent REGISTERED PID for the same node. Frozen `bench/registry.py::integrity_issues` checks FORKED pid type but **does not require cross-record equality**. Thus this omission **does not violate the ONE narrow correction 003 requirement**. A stronger assertion would change scientific acceptance semantics and requires a separately reviewed design decision; **do not silently insert it**, do not label it a passed check, and never imply equality was tested. In native B0, a mismatch might matter operationally, but J1 cannot infer truth without an authenticated source/ticket binding.
- **OQ-11:** gate/ticket tokens in REGISTERED and witness are hypothetical synthetic declarations, not authenticated by an external source or kernel.
- **OQ-12:** no independently sealed Lane S/O bytes, trusted custody/oracle attestation, approved CPU guard and runner, frozen criteria or authenticated trust-map origin. Full formal acceptance is intentionally BLOCKED/NOT_READY.
- **OQ-1…OQ-10:** prior unclosed limitations remain recorded in source README/checkpoints; four V0.1 assertions are SMOKE_ONLY and have no PASS path.
- **Original FORKED.pid witness:** A native registry line written by the observer is a **source report of a fork PID**, not itself an authenticated independent proof that a particular target received a gate-release byte. Its syntax/integrity alone cannot solve lawful reaping, zero-signal orphan cleanup or process-lineage authenticity.

## Overall stage and only next instruction

**Accept the F05 defect as `PASS (SCOPED SOURCE-STATIC)` and STOP making source-only corrective edits for this already-reviewed assertion unless independent evidence reveals a new concrete defect.** Do **not** treat this as a G2 CPU PASS or freeze criteria.

**Unique next action:** perform a **DOCUMENTATION-ONLY J1 CPU-readiness / fixture-and-oracle preflight specification** from this verified review checkpoint. Define the 18 proposed S/O fixture inputs and private truth/seal provenance concept, runner/guard threat model, independent acceptance preconditions, treatment of OQ-13 and other open trust questions, plus explicit no-Python/no-execution boundaries for the design stage. **This next action is a proposal requiring separate owner authorization; do not materialize S/O bytes, write/execute test code, freeze, or run any CPU/REAL now.** ChatGPT owns design/review; Claude Code owns any future actual implementation if separately authorized.

G2 REAL remains **BLOCKED** by lawful reaper ownership, creator crash/orphan, no-signal bounded cleanup and private-disposable-environment requirement. Neither this synthetic source review nor a possible future CPU synthetic detector pass can advance REAL readiness by itself.
