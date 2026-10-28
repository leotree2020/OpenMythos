# F3B-D1-A-CPU-003 — G2 J1 implementation independent static review checkpoint (2026-10-28)

## Stage result and operating permission — read FIRST

**`J1 IMPLEMENTATION STATIC REVIEW: CHANGES REQUIRED`.** The new isolated implementation *exists* but has **not been accepted** for fixture materialization, criteria freeze or CPU tests. Three central scientific safety gaps are (a) Oracle false-positive acceptance of INPUT_INVALID / forged expectations, (b) insufficient same-ticket attribution, and (c) unsupported “complete ledger” PASS. These findings are **source deductions**, not executed proof.

**`G2 J1 CODE PRESENT / FUNCTIONAL SYNTAX IMPORTS TESTS NOT TESTED`; `G2 CPU NOT TESTED / NOT AUTHORIZED`; `S/O FIXTURES NOT MATERIALIZED`; `G2 CRITERIA NOT FROZEN`; `G2 REAL BLOCKED / NOT AUTHORIZED`.** G0/G1 accepted REAL evidence and upstream Parcae, frozen Bench and R3 are unchanged. No model reasoning/efficiency or original Parcae mathematical correctness is implied.

**Grok:** user-reported usage limit, review `DEFERRED / NOT PERFORMED / NOT PASS`. Temporary owner permission did not create a second review opinion. **O-1…O-15 = OWNER UNDECIDED**. Owner directs all future code fixes to Claude Code; ChatGPT performs independent source review and acceptance only.

## Git baseline and actual remote evidence

- **Developer branch** `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028`, remote HEAD fetched and VERIFIED at `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`.
- **Coding baseline** `02d79a26e4ad6b49527bc90e6be4fe9130b45cff`; first code commit `f9151a9c6156ada24f6f4f77270eb004a713bf0a` and subsequent SHA-record addendum commit.
- **Independent compared diff** from coding baseline: **2 commits / 10 files / 1805 insertions / 0 deletions**. Added source: `gate_g2/j1/{__init__.py,schema.py,judge.py,codec.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}`. Added dev checkpoint `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_PREP_001_CHECKPOINT_20261028.md`; appended docs `PROJECT_MAP.md` and `SESSION_START_PROTOCOL.md`. No frozen paths modified.
- **Source Git blobs reviewed:** `j1/schema.py=0c016df638832931128b65e453e510d9d0483be0`, `j1/judge.py=54cecf6cc28bbc97b2c7e121015dcbc46e7ab7fa`, `j1/codec.py=bb486c922b945dd30edb003a11fe7758bd13c2fb`, `j1/oracle.py=1a0de1c3913043f14dbacd248dd3f01825756c3e`, `j1/tests/test_j1_static_and_unit.py=52cf13f290292a57c176be389877f2ef225f2c1c`.
- **Historical Bench source** `bench/registry.py:12–27,83–125,218–247`, `observer.py:103–139,276–302` inspected read-only at pinned SHA. Real B0 registry has `seq,kind,mono,wall` with floating timestamps; J1's new strict synthetic input schema is not yet a proven adapter.
- **Review branch** `d1-r3-a-cpu-003-e1a-g2-j1-impl-static-review-20261028` created at the verified implementation HEAD above. **Review report:** `a_predicate_003/gate_g2/G2_J1_IMPL_SOURCE_INDEPENDENT_STATIC_REVIEW_001.md`; report creation commit `fdd2bea7941b22590bcce608c2f8ae8c032cf7d7`. This checkpoint is created before final navigation commits; final review HEAD MUST be fetched, and the review-only diff verified.
- The developer's local clean-tree claim was self-reported; ChatGPT verified **remote** files and branch, **NOT the developer's local working tree**.

## Purpose / environment / input / expected / actual / status

| Field | Record |
|---|---|
| Purpose | Independently inspect J1 implementation against V0.1 spec, frozen B0 semantics, source-only Claude Code handoff and SRC-01…SRC-08 static requirements. |
| Environment | GitHub connector read-only source retrieval and isolated Markdown review/checkpoint commits only. No Python, pytest, AST execution, import, process experiment, signals, GPU or model runtime in this review. |
| Inputs | Pinned developer branch HEAD, developer checkpoint, entire `schema/judge/codec/oracle/tests/README`, V0.1 design and frozen Bench registry/observer. |
| Expected | Actual Git provenance and path diff, traceable code-line findings with falsifiable proposed counterexamples, honest SRC status, no code/test edits and next instruction. |
| Actual | Review report **7 findings J1-IMPL-F01…F07**, including four high, two medium and one procedural; source-only review `CHANGES REQUIRED`. Remote Git diff verified. |
| Git path scope | **PASS** for original developer implementation changed paths. |
| Static scientific acceptance | **CHANGES REQUIRED**, not implementation PASS. |
| Actual J1 syntax, imports, output correctness and full 18 CPU suite | **NOT TESTED / NOT AUTHORIZED**. |
| S/O fixture JSON and hashes | **NOT MATERIALIZED / NOT TESTED**. |
| G2 REAL | **BLOCKED / NOT AUTHORIZED**. |

## Independent SRC-01…SRC-08 assessment

| ID | Status | Reason |
|---|---|---|
| SRC-01 | PASS | Isolated implementation branch and 10 permitted paths confirmed remotely |
| SRC-02 | PARTIAL / CHANGES REQUIRED | Module boundary exists; Oracle can incorrectly grade invalid input BLOCKED as test PASS, accept changed expectations (F01/F02) |
| SRC-03 | BLOCKED / TRUST ASSUMPTION | Caller-supplied role table cannot alone prove authentic harness provenance (F05) |
| SRC-04 | PARTIAL / CHANGES REQUIRED | Nine handlers and smoke labels exist; ATTRIBUTION same-ticket evidence may be missing (F03) |
| SRC-05 | FAIL FOR COMPLETENESS CLAIM | Incomplete native-B0 lifecycle can produce UNIQUE_REGISTRY PASS; raw record projection unresolved (F04/F06) |
| SRC-06 | PASS (STATIC, LIMITED) | Codec limits seal claims to byte integrity; no real custodian proof |
| SRC-07 | Git-scope PASS / procedural FAIL | Bench untouched; Claude self-reports one prohibited empty `python3` interpreter launch. No evidence of project test execution |
| SRC-08 | PASS (DOCUMENT) | Developer checkpoint includes dependencies, risks, Git and one next instruction |

## Highest-priority fixes before any future run

1. **F01/F02 Oracle integrity:** an invalid Lane S fixture must never receive a CPU test PASS merely because expected subject=BLOCKED; bind expectations to the pinned 18 inventory and independently verified S/O bytes, disallow user-shrunk full-suite inventory and forged result rows.
2. **F03 same-ticket identity:** do not permit an ATTRIBUTION PASS on matching node token alone when gate/ticket linkage is missing. A pre-release requirement must be evaluated only when claiming pre-release proof, otherwise narrow the claim.
3. **F04 native-B0 lifecycle:** define full scoped ledger validity prerequisite for UNIQUE_REGISTRY PASS and ensure RUN_START and creator chains match frozen B0 when “complete” is asserted.
4. **F05/F06 provenance and projection:** clearly separate trusted harness assumptions from authentic external proof and draft a fail-closed native record adapter or make the supported scope explicitly synthetic-only.
5. **F07 deviation:** preserve the historical prohibited Python interpreter launch as a procedural FAIL (self-reported), not a functional-test result and not a reason to rewrite the developer's original checkpoint.

No tests were run to verify the proposed counterexamples. Claude Code should add **unexecuted static test source** covering each negative case on an isolated correction branch, under a new owner-authorized code-only instruction. Do not change old results, Bench, Parcae, G0/G1 or the architecture to make any test pass.

## Dependencies and unresolved safety responsibilities

No new packages, dataset, model weights, GPU or CPU runtime environment introduced by this review. Correct implementation depends on the exact new schema, separately trusted harness authority, source-labeled witness assumptions, sidecar seal provenance, and an independent oracle with immutable expectation bindings. These remain technical prerequisites, not proven results.

G2-R01 lawful descendant reaping, creator crash/orphan handling and no-signal bounded cleanup remain unresolved. Synthetic J1 static review cannot advance G2 REAL safety. Grok may later provide an independent review; any disagreement should be recorded rather than presumed settled.

## One next instruction

**Prepare a Claude Code SOURCE-ONLY correction handoff for J1-IMPL-F01…F06, then obtain explicit owner permission before Claude starts edits.** Claude Code must start from verified implementation SHA, use a NEW isolated correction branch, fix only `gate_g2/j1/` and its task-specific checkpoint, add *unexecuted* negative-control test source, commit/push and stop. No Python invocation, no tests, no fixture materialization, no criteria freeze, no fork/signals, no GPU, no G2 REAL; ChatGPT performs the next independent static review after the correction. SRC-07 historical procedural deviation stays recorded.

Review and checkpoint are documentation-only; no implementation correction was carried out in this turn.
