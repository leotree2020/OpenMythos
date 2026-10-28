# OpenMythos — Claude Code SOURCE-ONLY correction handoff: J1 implementation static-review F01–F06

**Task ID:** `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-001`  
**Prepared by:** ChatGPT · **Date:** 2026-10-28 · **Code implementer:** Claude Code, per owner rule.  
**Task status:** **CORRECTION INSTRUCTIONS PREPARED; CLAUDE CODE NOT INVOKED; NO CODE FIXES IN THIS HANDOFF**.  
**Authority:** The owner authorized continuation through preparation and delivery of correction instructions. Code edits begin only when the owner submits/authorizes this bounded task in Claude Code. This authorization **does not** cover execution of Python/tests, fixture materialization, CPU experiment, process experiment, G2 criteria freeze, merge, or G2 REAL.

## 0. Git and mandatory read-first checkpoint

Repository: `leotree2020/OpenMythos`.

- **Verified implementation code branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028` HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`.
- **Verified independent static-review branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-static-review-20261028` HEAD `1b2ba339d267b8c04e1db5fb71d29da45a597758` (review report/checkpoint, **no fixes**).
- **Handoff branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix-handoff-20261028`, created from the static-review commit above. **Do not assume its final HEAD equals the review SHA:** use its **live, exact remote HEAD** after the document/checkpoint commits.
- **Source for actual fixes:** create a **new isolated correction branch from the handoff branch's verified final HEAD**, retaining both the implementation source and the review documents. Do not edit `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028` or any frozen source branch in place.

Read and preserve source evidence in this order:
1. `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`.
2. `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX_HANDOFF_CHECKPOINT_20261028.md`.
3. `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_STATIC_REVIEW_001_CHECKPOINT_20261028.md`.
4. `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_SOURCE_INDEPENDENT_STATIC_REVIEW_001.md` — findings **J1-IMPL-F01…F07**.
5. `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md` — scientific scope and **18 proposed cases**, not frozen.
6. `research/mini_mythos/a_predicate_003/gate_g2/j1/{schema.py,judge.py,codec.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}`.
7. Frozen `research/mini_mythos/a_predicate_003/bench/{registry.py,observer.py,node.py,gate.py,common.py,proto.py}`, strictly read-only.

Record exact source HEAD/blobs and `git status` before writing. If the branch has moved, files are missing, or dirty work could be overwritten: record **BLOCKED** and stop, without silently choosing a different baseline.

## 1. Scope and deliverable boundary

**Fix code only in** `research/mini_mythos/a_predicate_003/gate_g2/j1/`, plus **one new task-specific checkpoint** in `research/mini_mythos/docs/` and brief navigation-only additions to `docs/PROJECT_MAP.md` and `docs/SESSION_START_PROTOCOL.md`. You may edit existing isolated J1 test **source**, but **never invoke the interpreter, import modules, run pytest/unittest, compile, or execute a fixture**.

**Do not modify** `bench/`, `gate_g0/`, `gate_g1/`, original G2 design/review/checkpoint files, frozen criteria/prereg/evidence, existing out-of-subtree tests/tools, R3, upstream Parcae, model architecture/training, or any other source outside J1. Do not create authorization files, REAL-process instrumentation, GPU code, merge/PR or release.

Do not create Lane S/O fixture JSON files, actual fixture data or test run evidence; do not fabricate hashes of nonexistent fixtures. Any new tests are **unexecuted source definitions and expected-output examples only**. Prefer minimal, auditable patches over large refactors or a redesign of frozen B0.

## 2. Highest-priority correction: J1-IMPL-F01 — test INPUT_INVALID must never become acceptance PASS

Current source: `j1/judge.py:450–459` returns `subject_verdict=BLOCKED`, `INPUT_INVALID`, diagnostic list on invalid Lane S; `j1/oracle.py:107–164` currently checks mostly the verdict/metadata, allowing a malformed-input test to PASS when expected subject is BLOCKED.

**Required implementation:**
- Keep the **subject's epistemic BLOCKED** separate from **instrument invalidity**. Introduce an explicit machine-checkable `input_valid` or equivalent structured indicator; never reclassify an invalid fixture as a valid missing-evidence BLOCKED.
- `oracle.grade_case` **must not return test PASS** if the subject returned `INPUT_INVALID`, nonempty input diagnostics, malformed/partial evidence, missing independently required guard/readback attestation, or an invalid required evidence-basis shape.
- If an input cannot be independently certified under the still-unmaterialized fixture protocol, the **formal acceptance result must be BLOCKED / NOT_READY**, never PASS. For small inline demonstrative unit tests, label any checking result as non-formal until authorization and independent S/O sealing exist.
- Preserve the distinction: a **well-formed** subject sample with genuinely missing PRE_RELEASE witness may legitimately receive **subject BLOCKED**. If that was the predeclared target, its **future** CPU test can PASS **only after** validity/provenance/guard requirements are independently satisfied; this stage does not assert those preconditions have been satisfied.

**Unexecuted negative-control source to add:**
`J1-F03-A` expected subject BLOCKED; inject a forbidden `expected_subject_verdict` key in Lane S. Show that the judge returns `INPUT_INVALID`, and Oracle **does not** grant test PASS. Contrast with an independently valid missing-witness input. Do **not** run either example.

## 3. J1-IMPL-F02 — pin expectations, prevent fabricated aggregate PASS

Current source: `j1/oracle.py:30–51,80–104,126–198`. It contains a proposed 18-case inventory but accepts mismatched expectation tuples, grade rows from any caller and optional caller-restricted `expected_ids`.

**Required:**
- Explicitly match `(fixture_id,canonical_card,assertion_id,expected_subject_verdict)` against **the versioned V0.1 18-item inventory**, reject unknown/mismatched/duplicate entries and unapproved scope changes. The versioned inventory is a **DRAFT**, not an owner-frozen gate; never claim real signed/immutable custody.
- Refuse **formal full-suite PASS** based solely on caller-provided grade dictionaries. Aggregate needs a documented independent provenance/attestation contract for both the case result and source fixture S/O bytes; until that verification capability is implemented, it should return **BLOCKED / NOT_READY** for formal full-suite acceptance even when 18 in-memory statuses are all PASS.
- Do not implement an "unforgeable Python object" fiction: dataclass/opaque handle/private attribute is **not** a cryptographic independent seal. If a test harness and trusted custody cannot be demonstrated without execution, keep the **acceptance gate unconditionally BLOCKED pending future stage**, and describe the missing conditions.
- Remove or explicitly reject any public `expected_ids` override that can shrink the named **18-case** formal run. A future genuinely different suite requires a new versioned scope and owner review, not a keyword argument.
- Unit-test **source only** should include altered F01-A expectation from FAIL to PASS, a fabricated 18×PASS grade-row list, a caller-shrunk expected set and a duplicate/unknown ID; all must fail closed for **formal** acceptance. An original bare `grade_case` inline illustration that expected PASS without fixture preflight may need its test-source assertion updated to **BLOCKED**; that is a correction of an unsafe test assumption, not a change of the historic V0.1 fixture expectation.

**Critically:** DO NOT alter the 18 predeclared `expected_subject_verdict` entries or original scientific labels to make the implementation pass.

## 4. J1-IMPL-F03 — ATTRIBUTION same-ticket join and time claim

Current source: `j1/judge.py:161–228`. It currently requires matching `node_token` but compares `gate_token` only when **both** happen to be populated; absence can still result in PASS or FAIL. V0.1 F01-A/C explicitly assumes a **separately trusted simulated gate-child observation for the same ticket/gate**.

**Required:**
- Choose the **conservative synthetic-only** implementation: require an independently predeclared, explicit, **nonempty matching gate/ticket association** for every comparison that may lead to ATTRIBUTION PASS or FAIL. If not available, subject verdict is **BLOCKED**, with basis code `GATE_ASSOCIATION_UNVERIFIED` (or equivalent). **Node token agreement alone cannot imply same ticket**.
- Reject contradictory/multiple trust-matching associations rather than selecting a convenient one. Verify the join and identity under the same pinned synthetic trust scope; do not rely on untrusted event `raw_fields` to self-authorize gate ownership.
- ATTRIBUTION in V0.1 is a **retrospective observed identity agreement/contradiction**, not P1 PREVENT_PROOF. An observation after B0 `RELEASED` cannot establish **pre-release** prevention. Do not incorrectly require PRE_RELEASE for the *retrospective* attribution claim unless a separate reviewed assertion explicitly asks that; retain timestamp-relative reason codes without elevating them.
- Do not add a native B0 gate witness or modify `observer.py`. The positive inline test *source* currently omits gate tokens; update it to include predeclared matching tokens **for those purely synthetic test cases**, and add a negative test source where a gate token is missing or mismatched (expected BLOCKED).

If the only workable rule would imply that native B0 supplies an unavailable gate binding, **document the mismatch and leave native-B0 attribution BLOCKED**; synthetic source evidence is not real provenance.

## 5. J1-IMPL-F04 — UNIQUE_REGISTRY lifecycle/finite-completeness must not inflate PASS

Current source: `j1/schema.py:202–219`, `j1/judge.py:83–118,231–268`, compared with read-only `bench/registry.py:lifecycle_issues,integrity_issues,check_order`.

**Required:**
- Prefer the narrowly scoped but **complete-for-this-assertion source transcript** model promised by V0.1. For UNIQUE_REGISTRY PASS, check `RUN_START` count/first position and **nonempty string run_id and true non-bool integer observer_pid**; if `RUN_END` exists, check count/last position, same run_id and boolean `cleanup_confirmed`; `INTENT` precedes `REGISTERED`, `FORKED` and `RELEASED` as applicable; creator except `O` was previously registered; no duplicate INTENT/DEAD, no record after DEAD and no RELEASED+ABORTED.
- Require a **source-labeled finite readback completeness statement** or, if none is available, limit PASS explicitly to **the finite supplied, internally validated records**; never assert the full original B0 log contains no omitted records. READ_STATUS not OK, record gaps, rejected/torn/truncated rows, missing relevant run fields → **BLOCKED** for a completeness-dependent PASS. Source-side evidence completeness remains a separate future materialization prerequisite.
- Preserve a positive **FAIL** for directly observed duplicate `REGISTERED` identities across distinct nodes, even if other completeness checks fail, when both contradictory records are themselves well-formed and adequately source-qualified.
- Full native RUN_START and creator-chain rules must be **cross-checked statically against frozen Bench**, rather than inventing new backend behavior. The existing `j1/tests/` helper's RUN_START currently has empty fields and must be updated **in test source only** to a valid illustrative synthetic run, along with narrow negative cases. No real Bench import or modified original registry.

**Source-only negative controls:** absent run_id/observer_pid, orphan creator INTENT, RUN_END wrong run_id, torn/read_status non-OK, duplicate across nodes. Nothing is executed now.

## 6. J1-IMPL-F05/F06 — synthetic trust vs real B0 record mismatch

**F05 trust:** `schema.validate_trust_model` only validates a caller-provided role/kind map and cannot authenticate the provider. **Treat all trusted simulated source roles as an explicitly declared harness contract outside J1**, not kernel identity or cryptographically authenticated sender. The judge must not elevate a raw message's role string or `synthetic_assumption=True` to physical authority. Before any formal CPU acceptance, a distinct trusted harness and its origin/seal rules must be reviewed. If no such harness exists, mark provenance `BLOCKED`. Do not build a fake signature/key/identity mechanism for this draft.

**F06 adapter:** **Choose the conservative path: J1 remains synthetic-only at this stage.** Frozen native `bench/registry.py` emits `seq,kind,mono,wall` with floats and additional raw fields; the closed synthetic J1 schema does not accept those native records directly. Update README/docstrings to say an independently reviewed and separately authorized native-to-J1 provenance-preserving adapter is an **OPEN future question**, **NOT IMPLEMENTED**. No real B0 log parsing adapter, no float-dropping partial transformation, and no Bench modifications in this correction. Report any claim of direct unmodified B0 registry compatibility as **FALSE/NOT SUPPORTED**.

For real-source use later, a lossless-in-provenance projection would need original raw bytes/digest, original sequence and missing/corrupt/torn status, creator/event projection and independent custody. **Do not implement the adapter here.**

## 7. Preserve procedural deviation J1-IMPL-F07

The previous developer checkpoint disclosed **one accidental `python3` invocation with empty heredoc** despite an explicit no-Python instruction. Record the historical event as **`SRC-07 strict procedural compliance FAIL (self-reported)`** while retaining **`Git file scope PASS`**. Do not rewrite, delete or conceal it, and do not make a retrospective claim that the entire previous task was zero-Python.

For this correction: **no Python interpreter invocation at all**, even an empty shell, no py_compile, AST checker script, imports, pytest/unittest, debugger, execution of test-source or subprocess. Use only source inspection, text editing and Git metadata/diff. Stop and record FAIL/DEVIATION if any prohibited command starts. Code produced under this stage is **NOT TESTED**, syntax and behavior unverified until a separately authorized CPU stage.

## 8. Static acceptance matrix for correction (not functional PASS)

| Check | Static required evidence before stopping | Possible stage status |
|---|---|---|
| FIX-01 | New branch from verified handoff HEAD; only j1/ + task checkpoint + navigation changed | PASS/FAIL/BLOCKED |
| FIX-02 | No `INPUT_INVALID`/malformed Lane S can yield formal test PASS; independent evidence gate blocks missing S/O proof | PASS/FAIL/BLOCKED |
| FIX-03 | Expected tuple bound to pinned 18 inventory, cannot replace F01-A's FAIL with PASS; no forged 18-row aggregate PASS | PASS/FAIL/BLOCKED |
| FIX-04 | ATTRIBUTION cannot give PASS/FAIL from missing or conflicting gate association; retrospective/pre-release claims separated | PASS/FAIL/BLOCKED |
| FIX-05 | UNIQUE_REGISTRY PASS only after native-grounded lifecycle/readback/finite-scope checks; duplicate FAIL preserved | PASS/FAIL/BLOCKED |
| FIX-06 | Harness trust source remains explicitly hypothetical, real B0 direct adapter out of scope; no overclaim | PASS/FAIL/BLOCKED |
| FIX-07 | Historic Python deviation retained; **no prohibited interpreter/test/process invocation in this correction**, test source added but unexecuted | PASS/FAIL/BLOCKED |
| FIX-08 | Git, dependencies, source examples, unresolved OQs, static review status and one next step recorded in checkpoint | PASS/FAIL/BLOCKED |

**Static PASS ≠ CPU PASS.** Do not call the fixed code *functionally correct* without actual tests. A source-level negative-case scenario in this document is a **proposed counterexample**, not a completed experiment. Formal fixture S/O materials remain uncreated; all 18 official cases **NOT TESTED / NOT MATERIALIZED**, full-suite formal acceptance **BLOCKED/NOT READY**.

## 9. Git actions, checkpoint and STOP

1. Verify the **current remote HEAD of this handoff branch** and all required file blobs; if it has moved, stop and resolve explicitly. Create a NEW, isolated correction branch from the actual handoff HEAD. Never modify the prior implementation/review branches in place.
2. Edit only permitted `gate_g2/j1/` code, unexecuted test source, README and new task checkpoint/navigation. Do not change scientific fixture expectations/history/criteria without separate approval.
3. Static source review and `git diff` **without Python or test commands**. No import/compile syntax checks. Keep raw source for subsequent independent review; if syntax correctness cannot be established without executing Python, mark NOT TESTED.
4. Record objective, environment, controlled input, expected, actual, **PASS/FAIL/BLOCKED/NOT TESTED** for FIX-01…FIX-08, code/commit dependencies, unresolved questions, Git status and exact next instruction.
5. Commit/push the correction branch, verify remote HEAD/changed paths and STOP. No merge, no test, no fixture generation, no CPU/REAL, no GPU.
6. Return the precise baseline SHA, correction code commit, final HEAD, actual changed-file list and checkpoint for **ChatGPT independent static review**. Grok remains DEFERRED / NOT PERFORMED unless a real report is later supplied.

## 10. Copy/paste starter for Claude Code

> OpenMythos task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-CORRECTION-001`. You are the designated code implementer for a **SOURCE-ONLY correction**, not test executor. Read `docs/SESSION_START_PROTOCOL.md` and `docs/F3B_D1_A_CPU_003_E1A_G2_J1_FIX_HANDOFF_CHECKPOINT_20261028.md` on `d1-r3-a-cpu-003-e1a-g2-j1-fix-handoff-20261028`; verify the branch's exact current remote HEAD and compare to the historical implementation code SHA `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`. Read the full `gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_HANDOFF_20261028.md` and independent findings F01–F07. Create a **new isolated correction branch** and fix **F01–F06 only** in `gate_g2/j1/` with additional **unexecuted static negative-test source**: fail-closed Oracle INPUT_INVALID/forged expectation/unverified aggregate; exact synthetic gate/ticket join; complete-for-scope UNIQUE_REGISTRY validation; explicit synthetic trust and no native B0 adapter. Preserve all 18 V0.1 expected verdicts and F07 procedural disclosure. **Do not invoke Python at all, or run/import/compile tests or code; do not materialize fixture JSON/hashes; no fork/exec/signal/Bench/GPU/REAL; never change Parcae, Bench, G0/G1/R3, frozen artifacts or criteria.** Record FIX-01…FIX-08 static statuses and unresolved OQs in a new checkpoint; commit/push only permitted paths and STOP, returning exact Git SHAs and diff for ChatGPT independent review.
