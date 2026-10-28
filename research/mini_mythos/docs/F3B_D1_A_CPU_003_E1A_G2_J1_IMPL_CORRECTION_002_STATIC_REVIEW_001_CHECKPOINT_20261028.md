# F3B-D1-A-CPU-003 — J1 correction 002 independent static review checkpoint (2026-10-28)

## Official review status — READ FIRST

**`J1 CORRECTION 002 INDEPENDENT STATIC REVIEW: TARGETED FIX2-01…FIX2-08 SCOPED STATIC PASS, OVERALL J1 SOURCE CHANGES REQUIRED`** due to newly found **`J1-FIX2-REVIEW-F05` HIGH — malformed synthetic FORKED without PID can still yield an unsupported `UNIQUE_REGISTRY=PASS`**, contrary to frozen `bench/registry.py::integrity_issues` (`MALFORMED_FORKED`).

This review performed **zero Python/interpreter/compile/import/unit tests, zero fixture materialization, zero model/process/fork/wait/signals/janitor/GPU experiments**. All source deductions and proposed counterexamples remain **NOT TESTED**. `J1 SYNTAX/IMPORTS/FUNCTIONAL BEHAVIOR NOT TESTED`; `18 S/O FIXTURES NOT MATERIALIZED`; `FORMAL ORACLE ACCEPTANCE BLOCKED/NOT_READY`; `G2 CRITERIA NOT FROZEN`; `G2 CPU NOT AUTHORIZED`; `G2 REAL BLOCKED/NOT AUTHORIZED`. **Grok DEFERRED / NOT PERFORMED (not PASS)**, no dual-review claim; G2 O-1…O-15 OWNER UNDECIDED. Historical G0/G1 REAL remains unchanged and has no bearing on J1/Parcae/LLM correctness.

**One next instruction:** prepare a **minimal Claude Code SOURCE-ONLY F05 correction handoff**, requiring an explicit source-grounded PID on synthetic FORKED before UNIQUE_REGISTRY can claim validated finite-ledger PASS; add unexecuted negative and positive source tests, preserve all other fixes and 18 V0.1 expectation rows, commit/push and STOP. The owner must authorize the next code edit; no implicit permission for tests/CPU/G2 REAL.

## Git and immutable input provenance

- **Reviewed Claude Code branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028` independently verified remote HEAD `26da6082af73c0505d5520001d1cea6ec086df47`.
- **Developer correction baseline:** `a3f6eef883be123028377b3dd1d62ccd5a8e975c`; developer source commit `e70b278a15ce6bf432c95c1b0f5853f13837f1ad`.
- **Developer correction checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_002_CHECKPOINT_20261028.md`, blob `4dc6204b54efeddde4b86fdd390344d7ccfbc015`; self-reported clean local working tree and zero Python invocations **NOT INDEPENDENTLY VERIFIED** by GitHub.
- **Independent source compare:** baseline→developer HEAD = **2 commits, exactly 7 paths, 314 added / 17 deleted**: `gate_g2/j1/{judge.py,oracle.py,README.md,tests/test_j1_static_and_unit.py}` plus developer checkpoint and `PROJECT_MAP`, `SESSION_START_PROTOCOL`. No Bench, Parcae, G0/G1, R3, original evidence/prereg or model changes. `schema.py`/`codec.py` remain unchanged.
- **Read-only source blobs:** `j1/judge.py=cd5063dbf2754b925a9871cc7d478076ca680cd7`, `oracle.py=0df6e5da8e8d08b39f19ff4188f34d33a44a2282`, `schema.py=e8b1e3439df54939ee67c9a795187a0174cba853`, `tests/test_j1_static_and_unit.py=e9fd2410a382dd569439cadfca79ca822cf6daeb`, frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`.
- **Isolated documentation review branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix2-static-review-20261028` created from exactly pinned developer HEAD `26da6082af73c0505d5520001d1cea6ec086df47`.
- **New review:** `a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_002_INDEPENDENT_STATIC_REVIEW_001.md`, initial creation commit `42f949b43a7c8e3bcc8306a64fbb9ffe28b8b02f`. This checkpoint and nav updates are docs-only; **fetch final branch HEAD and compare Git diff before closing**. Historical source/reviews/checkpoints must not be rewritten.

## Research management record: purpose, environment, expected, actual, acceptance

| Category | Reviewed status and evidence |
|---|---|
| Purpose | Independently check four explicitly requested F01–F04 minimal Claude Code corrections, test-source coverage, Oracle fail-closed, and frozen B0 source compatibility. |
| Environment | GitHub connector reads and independent Markdown review/checkpoint writes. No CPU/Linux experimental runtime, no local checkout, no extra dependencies, GPU or model. |
| Inputs | Verified correction 002 commit/diff/checkpoint, entire `judge.py`/`oracle.py`/`schema.py`/relevant test source, V0.1 draft and frozen `registry.py`. |
| Expected | Source-grounded verdict for each FIX2 gate, honest limitations, no accidental code mutation, reproducible Git SHA, smallest next correction task. |
| Actual | All four requested fixes are **SOURCE-LEVEL SCOPED PASS**; additionally a real source-contract gap found: `FORKED` with no PID admitted by synthetic schema and not rejected by ledger prerequisite, while frozen registry reports `MALFORMED_FORKED`. |
| FIX2 targeted static result | **PASS (SOURCE, LIMITED)**: F01 orphan, F02 pair key, F03 pairwise witnesses, F04 Oracle malformed-id guards. |
| Whole J1 static source acceptance | **CHANGES REQUIRED** for new `J1-FIX2-REVIEW-F05`. |
| Actual Python syntax/import/CPU/handler/test evidence | **NOT TESTED / NOT AUTHORIZED**; 24 newly written tests are unexecuted, not acceptance. |
| Fixture source S/O bytes, hashes, independent seal | **NOT MATERIALIZED / NOT TESTED**. |
| Formal CPU acceptance status | **BLOCKED/NOT_READY** by design, regardless of source static results. |
| G2 REAL and native B0 adapter | **BLOCKED / NOT AUTHORIZED**; native adapter not implemented. |
| Grok G2 review | **DEFERRED / NOT PERFORMED**, not PASS. |
| Git review-branch diff | **PENDING independent final comparison**, add verified result after nav changes. |

## Four previously required fixes — independent status

| Gate | Evidence and reviewer status |
|---|---|
| FIX2-01 | **PASS remote Git path scope** (7 files; no frozen files). |
| FIX2-02 | **PASS scoped** — `ORPHAN_RECORD` catches DEAD/ABORTED without INTENT; stronger synthetic-only RECORD_BEFORE_INTENT is explicit. |
| FIX2-03 | **PASS scoped** — uses exact `(pid,starttime)` duplicate key; metadata inconsistency handled conservatively. |
| FIX2-04 | **PASS scoped/synthetic** — all identity records checked pairwise, same-gate cross-node contradictions BLOCKED, with hypothetical trust boundary explicit. |
| FIX2-05 | **PASS for JSON-like input** — `oracle.aggregate` validates malformed IDs before set operations, always formally BLOCKED. |
| FIX2-06 | **PASS test-source existence / NOT TESTED behavior** — 24 new test methods are declarations, not executed results. |
| FIX2-07 | **Git scope PASS; developer command-history claim self-reported** — earlier first-implementation empty Python invocation remains a historical procedural FAIL. |
| FIX2-08 | **PASS checkpoint documentation** — SHA, purpose, environment, changes, OQs and next step recorded. |

## Newly found residual — HIGH J1-FIX2-REVIEW-F05

**Frozen source:** `bench/registry.py:69–80` checks `fk is not None and not isinstance(fk.get("pid"),int)` → `MALFORMED_FORKED`.  
**J1 source:** `gate_g2/j1/schema.py:212–244` accepts `FORKED` with optional identity and no mandatory pid raw field. `gate_g2/j1/judge.py:110–187` checks causal INTENT but no fork PID presence. `_unique_registry:320–367` can return PASS if a different REGISTERED is sound.

**Minimal proposed synthetic counterexample, NEVER RUN:** a single trusted synthetic ledger with valid `RUN_START`, `INTENT(nA)`, `FORKED(nA)` missing identity/PID, `REGISTERED(nA,pid=4101,starttime=101,ppid=4100)` (ordinals 1,2,3,4, all read_status OK). J1's current accepted event shape and prerequisite permit it; frozen registry integrity would reject missing fork pid. Do **not** retroactively treat this static deduction as executed FAIL.

**Required source-only correction:** explicit normalized fork PID field/presence and type rule that preserves the synthetic-only evidence boundary. If a FORKED row is present but lacks proven valid integer pid, **UNIQUE_REGISTRY must not report PASS**; distinguish invalid instrument INPUT_INVALID vs evidence BLOCKED. Add *unexecuted* negative missing-PID and positive complete-FORKED test sources. Preserve duplicate-pair positive FAIL detection, current F01–F04 fixes, all 18 expected V0.1 verdicts and `FORMAL_ACCEPTANCE_READY=False`. No real-native adapter, no frozen Bench changes.

## Dependencies, risks, unfinished owner decisions

- No packages installed/verified, no code executed. The reviewer cannot verify Claude Code's claimed local clean working tree or no-Python command history through GitHub; these remain developer statements, **not experimental proof**.
- Source-grounded V0.1 static proof must not be expanded into run-level completeness or native-B0 fidelity. `OQ-11` gate binding remains a simulated field, not independently authenticated. `OQ-12` sealed fixture S/O data, truth/signer custody, CPU guard, reviewed runner, criteria freeze and trust origin remain absent; formal Oracle blocked.
- Grok's review still deferred. If future Grok and ChatGPT reviews differ, preserve discrepancy and resolve by a separately approved minimal controlled experiment; no AI opinion is itself final experimental truth.
- G2 REAL remains independently BLOCKED by lawful reaper, creator/orphan management, zero-signal bounded abnormal cleanup and external containment; no source-only J1 work advances it.
- Main Parcae P1 reproduction/math/gradients and Mythos model evaluation are separate mainlines. This J1 detector source stage cannot claim any of those passes.

## Single next instruction

**Prepare and deliver a minimal Claude Code SOURCE-ONLY correction 003 task for HIGH `J1-FIX2-REVIEW-F05`**, with no scope creep: require source-grounded normalized synthetic FORKED pid, fail-closed missing PID, positive complete FORKED and negative missing PID test source (unexecuted), no Python/tests, no fixture JSON or hashes, no native adapter, no criteria freeze, no merge, no CPU or G2 REAL. New isolated code branch from the final reviewed checkpoint SHA, commit/push and STOP. Next ChatGPT turn reviews Claude Code's actual resulting source/diff.

This document **does not itself authorize Claude Code code edits or any experiment**; user must submit/approve the code-only task.
