# E1-A G2 J1 — implementation source independent static review 001

**Date:** 2026-10-28  
**Reviewer:** ChatGPT, remote-source review only. **NO Python, import, AST execution, tests, fixture materialization, fork/exec, signals, GPU, bench experiments or model runtime** in this review.  
**Object:** `leotree2020/OpenMythos`, implementation branch `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028`, verified remote HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`.  
**Baseline:** handoff HEAD `02d79a26e4ad6b49527bc90e6be4fe9130b45cff`; implementation content commit `f9151a9c6156ada24f6f4f77270eb004a713bf0a`.  
**Source scope:** exactly **10 files, 1,805 insertions / 0 deletions**: 7 new `gate_g2/j1/` files, a new implementation checkpoint, and navigation-only changes to `PROJECT_MAP.md` and `SESSION_START_PROTOCOL.md`. No code outside isolated `gate_g2/j1/`. Frozen Bench, Parcae, G0/G1, R3, existing tools/tests/prereg/evidence unchanged. Remote source comparison was verified; **the local working tree was NOT independently observed**.

## Review outcome

**`INDEPENDENT SOURCE STATIC REVIEW: CHANGES REQUIRED`.** The new isolated architecture is a credible starting point, and source scope is correct. However the Oracle currently has **positive false-acceptance paths** and the judge has **unsupported PASS paths** relative to the narrow V0.1 scientific assertions. No J1 functional result is established.

**`IMPLEMENTATION SOURCE PREPARED — STATIC REVIEW CHANGES REQUIRED`; `CPU NOT TESTED / NOT AUTHORIZED`; `18 S/O FIXTURES NOT MATERIALIZED`; `G2 CRITERIA NOT FROZEN`; `G2 REAL BLOCKED / NOT AUTHORIZED`; `Grok DEFERRED / NOT PERFORMED, NOT PASS`.** Owner decisions O-1…O-15 remain UNDECIDED. A commit and a Python interpreter that exited do **not** constitute a CPU PASS. G0/G1 historical REAL results remain untouched.

### Good source-level separations (not functional PASS)

- `j1/judge.py` imports only `schema` and `codec`, not `oracle` or native Bench; `j1/oracle.py` contains the private 18-case proposed expectation inventory, not imported by judge.
- `schema.py` attempts a closed Lane S schema, rejects fixture-shaped IDs and forbidden field names, verifies basic types and role ceilings; all trust grants are **harness assumptions**, not self-certifying authenticated data.
- `judge.py` contains five evidence-sensitive handlers and four explicitly SMOKE_ONLY handlers; outputs are scope-labeled `J1_SYNTHETIC_DETECTOR` / `NOT_EVALUATED_BY_J1`.
- `codec.py` implements proposed canonical JSON and a byte-integrity/seal-check distinction; it does not claim true kernel provenance or signing custody.
- Unit-test *source* and four metamorphic sketches exist, with the 18 formal S/O fixture data correctly still absent. **Not a single test was run.**

## Findings, ordered by severity

### J1-IMPL-F01 — HIGH — Invalid input may be graded as a PASS whenever expected subject is BLOCKED

**Code:** `j1/judge.py:450–459` converts `schema.InputInvalid` into `subject_verdict=BLOCKED`, `evidence_basis_codes=["INPUT_INVALID"]`, with `input_diagnostics`. `j1/oracle.py:107–123,126–164` checks output shape and exact assertion/subject verdict but **does not reject INPUT_INVALID, nonempty input_diagnostics, missing required evidence basis or corrupted fixtures before grading PASS**.

**Minimal controlled counterexample (PROPOSED / NOT EXECUTED):** a proposed `J1-F03-A` expects BLOCKED because legitimate PRE_RELEASE evidence is missing. Supply malformed Lane S input with a forbidden field `expected_subject_verdict`. J1 returns BLOCKED / INPUT_INVALID; `grade_case` sees the same expected subject verdict and can return **test PASS**. The fixture was invalid, so a meaningful test must be **BLOCKED**, not PASS.

**Required correction:** split instrument/input validation from subject verdict, e.g. `input_valid=False` or an explicit non-subject `INPUT_INVALID` channel; external independent oracle must check fixture validity/readback/guard evidence first. A matching BLOCKED verdict **never** grants test PASS if `INPUT_INVALID`, `input_diagnostics`, corrupted/missing fixture bytes, or absent required basis. Update static test *source* with an expected BLOCKED test-level negative control. **No runtime execution under this review**.

### J1-IMPL-F02 — HIGH — Private expected answers are not pinned to the declared inventory or independently sealed test inputs

**Code:** `j1/oracle.py:30–51` stores the 18-case expected inventory; `validate_private_expectation:80–104` checks mostly shape, not that `(fixture_id,canonical_card,assertion_id,expected_subject_verdict)` matches `SPEC_V0_1_INVENTORY`. `grade_case:126–164` can award PASS for a *changed* expectation. `aggregate:167–198` accepts arbitrary `case_results` dictionaries, provides a caller-selectable `expected_ids`, and lacks a trusted fixture-hash/readback preflight.

**Minimal controlled counterexamples (NOT EXECUTED):**
- Present `fixture_id=J1-F01-A` with `expected_subject_verdict=PASS` even though the versioned inventory specifies **FAIL**; give a corresponding plausible J1 output PASS. `grade_case` can return test PASS.
- Supply 18 fabricated `case_results` rows with expected IDs and `test_acceptance_verdict=PASS`. `aggregate` can produce run PASS without proof that Lane S/O bytes, 18 cases or J1 were ever evaluated.
- Override `expected_ids` with a smaller set to avoid required cases; this can silently change the run's intended acceptance scope.

**Required correction:** `validate_private_expectation` must bind each fixture ID to the immutable versioned inventory. Separately seal and verify fixture Lane S and Lane O bytes/digests **before a future run**; retain their independent provenance. Aggregate only verified Oracle-produced evidence, require exactly the approved 18 IDs, reject a caller-shrunk expected set for a full-suite claim, and never infer run PASS from unverified caller-provided grade rows. Until fixture bytes exist and are independently signed/sealed, a full formal CPU acceptance remains **NOT READY / NOT TESTED**.

### J1-IMPL-F03 — HIGH — ATTRIBUTION does not prove that witness and registration refer to the same ticket/gate

**Code:** `j1/judge.py:161–228`, especially `195–203`: witness joins on `node_token`; gate-token comparison is made only **if both tokens are present**. `215–227` records timing as a basis code, then can return PASS/FAIL based on identity agreement even when actual ticket/gate association is missing. V0.1 F01-A/C require an independent simulated gate-child observation for **the same ticket/gate**.

**Minimal counterexample (NOT EXECUTED):** B0 `REGISTERED` carries node `nA` and no gate_token; hypothetical trusted witness carries `nA` but a different gate `gate-B`. As neither side has a comparable gate token, the event is treated usable; a matching PID/starttime can produce ATTRIBUTION PASS although same-ticket membership was never established. Likewise a witness arriving after RELEASED can yield PASS with only a diagnostic note.

**Required correction:** declare and enforce the **exact** trust-scoped join: a predeclared binding from ticket/node to gate identity in the harness, or require a matching populated gate token; when equivalence is unavailable, **BLOCKED**, not an attribution PASS. If the narrower intended claim is merely “same node-token reported equal identities under trusted simulation,” rename/limit the assertion and **do not** call it same-ticket attribution. The timing required for a pre-release claim must be a hard prerequisite; a post-release observation may be a different retrospective assertion only. Do not invent a B0-native gate witness to force PASS.

### J1-IMPL-F04 — HIGH — UNIQUE_REGISTRY can PASS with lifecycle-invalid native-B0-shaped records

**Code:** `j1/schema.py:202–219` marks `RUN_START.run_id` and `observer_pid` as **optional**; `j1/judge.py:83–118` verifies RUN_START kind position but **not the required run_id, observer_pid or all the native lifecycle and creator-chain constraints**. `UNIQUE_REGISTRY:231–268` can return PASS for one registered node if synthetic RUN_START raw_fields is empty but INTENT/REGISTERED are present. In contrast frozen `bench/registry.py:83–125` requires exactly one valid `RUN_START` with run_id and observer_pid and checks lifecycle; `registry.py:218–247` checks creator lineage/order constraints.

**Minimal counterexample (NOT EXECUTED):** three synthetic B0 records, valid observation schema: `RUN_START(raw_fields={})`, `INTENT(nA)`, `REGISTERED(nA,pid=4101,starttime=101,ppid=4100)`, monotonic orders 1,2,3. `_ledger_prerequisite_problems` has no reason to reject these, so the judge can report “NO_DUPLICATE_IN_SUPPLIED_COMPLETE_SET” PASS, whereas the frozen Bench lifecycle considers RUN_START malformed.

**Required correction:** for any `UNIQUE_REGISTRY=PASS`, either require a **fully checked, source-grounded native lifecycle projection** (RUN_START values, order, creator/prerequisites, read status and full readback), or explicitly downgrade its claim to “no duplicate among syntactically supplied REGISTERED rows” without a completeness assertion. In the first case malformed/incomplete required fields → BLOCKED; in the second case the expected claim and acceptance inventory must be revised before running tests. Keep positive duplicate FAIL supported by direct contradictory records.

### J1-IMPL-F05 — MEDIUM — Source provenance is caller-supplied; schema checks are not harness authentication

**Code:** `j1/schema.py:279–326` validates role names and kind ceilings within the **`declared_trust_model` argument itself**. `judge.evaluate` receives that map directly from caller. There is no authenticated harness registry, independent trust-map seal, or external handle-origin verification in this implementation. A caller that controls both map and synthetic events can label its own event `G2_WITNESS_SIM` or `G2_WRAP_SIM` and satisfy a synthetic PASS predicate.

**Disposition:** this is compatible with *explicitly trusted simulation inputs* if the caller/harness is outside the adversarial SUT boundary, but **the claimed “harness-bound trust” is not independently enforced by J1 alone**. Before any real-source inference or functional validation claim, fix the harness provenance contract and ensure trust grants cannot come from subject-controlled data. Do not treat a role string or `synthetic_assumption=True` as kernel authentication. All synthetic fixture PASS claims remain limited to the externally declared trust assumption.

### J1-IMPL-F06 — MEDIUM — Native Bench records cannot pass the closed observation schema without a defined adapter

**Code:** frozen `bench/registry.py:12–27` writes each record with `seq`, `kind`, **floating-point** `mono` and `wall`, plus event-specific keys. `j1/schema.py:202–219,355–418` accepts a different closed `Event` representation with no native float fields and no native extras; `_scan:251–277` rejects floats. Claude Code flags the incompatibility in its checkpoint OQ-7.

**Required correction before reusing real B0 evidence:** specify a source-grounded, independently reviewable **lossless-in-provenance projection adapter** from real native records to the synthetic normalized Event shape, retaining original bytes/digests and explicitly mapping fields, including missing/torn/corrupt markers. The adapter must not silently drop malformed/unreadable rows and call a ledger complete. Alternatively scope J1 only to **hand-authored synthetic B0-shaped data** and withdraw any implied direct native-registry compatibility. Either choice is **open**, not a reason to modify upstream Bench.

### J1-IMPL-F07 — PROCEDURAL — Source scope is clean but no-Python restriction was violated once

**Evidence:** Claude Code checkpoint expressly reports a `python3` interpreter invoked accidentally with an empty heredoc, no statements, no imports and no files written. No project tests were run according to the disclosure, but **starting the interpreter violates the explicit no-Python-invocation instruction**.

**Independent disposition:** **SRC-07 source-diff restriction PASS**; **SRC-07 strict execution-prohibition compliance FAIL (self-reported)**. Do not conceal or relabel the deviation. This is not evidence of a functional failure of J1, a fork/signalled process experiment, or a failed CPU test. A later separately authorized CPU stage must use a reviewed runtime guard and record actual permitted executions, rather than retroactively erasing this event.

## Static SRC-01 … SRC-08 independent scoring

| Criterion | Reviewer assessment | Evidence / restriction |
|---|---|---|
| SRC-01 isolated branch, permitted changes | **PASS** | Remote Git compare: 10 files, 1805 added / 0 deleted; no frozen source path |
| SRC-02 Lane O separation | **PARTIAL / CHANGES REQUIRED** | Module import topology separated, but oracle can accept modified expected verdicts and INPUT_INVALID as test PASS (F01/F02) |
| SRC-03 harness-bound trust | **BLOCKED / DESIGN ASSUMPTION** | Role ceiling checks exist but origin of trust map is not independently authenticated (F05) |
| SRC-04 five contrasting + smoke assertions | **PARTIAL / CHANGES REQUIRED** | 9 handlers present, four SMOKE_ONLY; unsupported attribution PASS possible (F03) |
| SRC-05 faithful Bench semantics / fail-closed | **FAIL FOR COMPLETENESS CLAIM; CHANGES REQUIRED** | RUN_START fields and lifecycle missing for PASS; native record projection unresolved (F04/F06) |
| SRC-06 integrity limited to bytes | **PASS (STATIC, LIMITED)** | codec compares byte counts/digests with synthetic seal and states no authenticity; no run |
| SRC-07 frozen scope/no execution | **GIT SCOPE PASS; PROCEDURAL FAIL** | permitted changed paths; reported one prohibited Python interpreter launch |
| SRC-08 checkpoint and next step | **PASS (DOCUMENT)** | purpose, Git, dependencies, open OQs and explicit NOT TESTED statuses exist |

**No functional syntax/runtime judgment:** Python syntax, imports, all tests, actual 18 S/O fixtures, hashes, CPU guard effectiveness, any J1 output and any real-process/Parcae capability are **NOT TESTED**. The static findings above are source deductions, not executed counterexamples.

## Immediate next work boundary (Claude Code only after owner approval)

**Single next instruction:** Give Claude Code a **source-only correction task** for F01–F06, including static test *source* covering each controlled counterexample and preserving all existing V0.1 expectations unless an explicit, versioned amendment is approved. No fixture materialization, no Python invocation, no tests, no Bench/Parcae/G0/G1/R3 edits, no criteria freeze, no CPU/REAL. Once Claude Code commits/pushes a corrected isolated branch and checkpoint, return it for another independent ChatGPT static review. Keep Grok deferred, O-1…O-15 undecided and REAL blocked.

**Important:** A source correction is not automatically authorized by this review report alone; the owner must instruct Claude Code to perform it under the stated boundaries.
