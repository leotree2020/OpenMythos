# F3B-D1-A-CPU-003 — J1 Correction 003 Claude Code SOURCE-ONLY handoff checkpoint (2026-10-28)

## Official status, read first

**`CORRECTION 003 HANDOFF DOCUMENT PREPARED / CLAUDE CODE NOT INVOKED / NO CODE CHANGE IN THIS STAGE`.** The latest implementation source still has **`J1 OVERALL STATIC REVIEW: CHANGES REQUIRED`** for one new HIGH finding **`J1-FIX2-REVIEW-F05`**, while the four prior requested F01–F04 fixes achieved **SCOPED STATIC PASS**. **No CPU/runtime test was run**, so no source change has functional PASS.

**`J1 SYNTAX/IMPORTS/FUNCTIONAL TESTS NOT TESTED`; `18 FORMAL S/O FIXTURES NOT MATERIALIZED`; `FORMAL ORACLE ACCEPTANCE BLOCKED/NOT_READY`; `G2 CRITERIA NOT FROZEN`; `G2 CPU NOT AUTHORIZED`; `G2 REAL BLOCKED/NOT AUTHORIZED`.** Grok `DEFERRED/NOT PERFORMED` (not PASS); G2 owner options O-1…O-15 `UNDECIDED`. Prior G0/G1 results, native Parcae, frozen Bench, R3 and model code unchanged.

**Single next instruction:** owner submits the exact handoff `a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_003_HANDOFF_20261028.md` to Claude Code to write **source only** for missing/malformed synthetic FORKED pid, add **unexecuted** negative/positive tests, checkpoint/commit/push on a NEW isolated code branch, and STOP. ChatGPT then independently source-reviews the resulting diff. Nothing authorizes a Python interpreter invocation, CPU/REAL, criteria freeze, model training, data materialization, or merge.

## Source Git baseline and provenance

- **Verified latest prior independent review branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix2-static-review-20261028` remote HEAD `801489ec5b42c9d8e5e27bb11c619fe3f6506312` (checked independently before new branch creation).
- **Verified developer implementation branch:** `d1-r3-a-cpu-003-e1a-g2-j1-impl-fix2-20261028` remote HEAD `26da6082af73c0505d5520001d1cea6ec086df47`, code commit `e70b278a15ce6bf432c95c1b0f5853f13837f1ad`. The handoff branch inherits this code but has only documentation commits afterward.
- **Independent reviewer report:** `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_CORRECTION_002_INDEPENDENT_STATIC_REVIEW_001.md`, Git blob `eb16fc45752605d487eb14d0cbdca0b213c087d8`.
- **Read-first reviewer checkpoint:** `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_CORRECTION_002_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, Git blob `0f38b3e3f8c8d3921f0cbfadcc9406d3c8221313`.
- **Frozen Bench read-only source:** `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`, `bench/observer.py=635e73b34203219a3687f86332d0e82362b89670`. Observer writes `FORKED` with `pid=pid` and `starttime=rec.forked_starttime`, which can be `None`. Native registry `integrity_issues` rejects missing/noninteger fork PID as `MALFORMED_FORKED`. No actual new native experiment was conducted.
- **Current isolated doc branch:** `d1-r3-a-cpu-003-e1a-g2-j1-fix3-handoff-20261028`, created from pinned independent review SHA `801489ec5b42c9d8e5e27bb11c619fe3f6506312`.
- **New full Claude Code handoff:** `research/mini_mythos/a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_003_HANDOFF_20261028.md`, initial creation commit `6f72f80e34e3b6e850d1229b60b62de514717054`.
- **Handoff final branch HEAD not yet pinned** until this checkpoint, nav entries and readback/verification addendum complete. Claude Code MUST fetch its actual remote final HEAD, not assume review SHA or the creation commit.

## Purpose, environment, input, expected vs actual and acceptance

| Item | Observation |
|---|---|
| Purpose | Convert exactly one new source-grounded HIGH integrity discrepancy `J1-FIX2-REVIEW-F05` into an unambiguous, safe Claude Code task without modifying J1 code. |
| Environment | GitHub remote connector: pinned source file reads, isolated Markdown-only documentation branch/commits. **No Python, CPU test, process, GPU, model, native B0 readback or fixture execution**. |
| Input | Latest independent static review/checkpoint, frozen `bench/registry.py::integrity_issues`, `bench/observer.py::_note_forked`, J1 current schema and judge. |
| Expected | Preserve four prior fixes, specify a minimal normalized synthetic FORKED PID with fail-closed missing/type behavior, prevent UNIQUE_REGISTRY false PASS, preserve duplicate FAIL, provide unexecuted tests and static checklist. |
| Actual | Full Claude Code SOURCE-ONLY Correction 003 task prepared and committed; **no code implementation or test executed by ChatGPT**. |
| Task handoff document | **PASS (document creation)**, not CPU/test PASS; Git readback pending. |
| Correction 003 actual implementation | **NOT STARTED**; no Claude Code call in this conversation. |
| Functional syntax/import/CPU/18 fixtures | **NOT TESTED / NOT MATERIALIZED**. |
| Git doc-only changed-path scope | **PENDING final GitHub remote compare**, record in addendum before stage close. |
| G2 REAL safety | **BLOCKED / NOT AUTHORIZED**. |
| Grok independent review | **DEFERRED / NOT PERFORMED**, not a dual-PASS. |

## Technical correction bounded by the available evidence

**New HIGH `J1-FIX2-REVIEW-F05`:** The native Bench writes `FORKED.pid`; frozen integrity requires its presence and integer type. Current synthetic J1 `schema.py` accepts FORKED without identity or `raw_fields.pid` and `judge.py` validates only INTENT-before-FORKED; `UNIQUE_REGISTRY` may therefore return a **false positive** finite-ledger subject PASS. Counterexample remains **NOT TESTED**, only derived by reading source.

**Chosen minimal handoff design:** allow `FORKED.raw_fields.pid` as an **optional normalized synthetic field** to keep missing-evidence separate from malformed instrument. Present pid must be non-bool integer `>=1`; missing pid with otherwise valid input blocks `UNIQUE_REGISTRY`, and present invalid value is `INPUT_INVALID` (no subject verdict). `FORKED` starttime is **NOT** mandatory because native `observer.py` may log `starttime=None`. A conflicting optional `FORKED.identity.pid` cannot lead to a validated PASS. Prior positive duplicate `REGISTERED` pair FAIL must still be recorded before unrelated lifecycle BLOCKED. This is **not** a native registry adapter, not a new trust root, and not any verified kernel PID provenance.

Required source-only negative/positive controls: (A) missing pid → subject BLOCKED; (B) valid pid → limited finite-ledger PASS; (C) present bool/zero/string/None/negative → instrument INPUT_INVALID; (D) valid fork pid with absent starttime → eligible for PASS; (E) positive REGISTERED duplicate still FAIL despite other missing fork pid; (F) optional identity.pid conflicting with fork raw pid → no PASS. These are **test-source intentions, never run results**. V0.1 18 proposed fixture verdicts (5 PASS / 5 FAIL / 8 BLOCKED) unchanged, four SMOKE_ONLY assertions remain limited.

**Grok/owner decisions:** deferred/undecided; do not choose native reaper or treat evidence as real. Historical first code task's self-reported empty Python interpreter invocation remains an execution-discipline deviation and must not be edited away. Future developer command history cannot be verified by GitHub readback alone.

## Development separation and unresolved dependencies

- **Claude Code**, if separately initiated by the owner, writes only isolated `gate_g2/j1/{schema.py,judge.py,README.md,tests/test_j1_static_and_unit.py}` and new checkpoint/nav entries; no native Bench/Parcae, G0/G1/R3, prereg/evidence/test tool changes. It reports `FIX3-01…FIX3-08` static source statuses with exact Git base/commit/head and dependencies.
- **ChatGPT** reviews future exact diff as a new independent static audit, not by accepting Claude's self-reported PASS. Any CPU test needs distinct explicit authorization and a reviewed guard, runner and criteria.
- **G2 REAL still BLOCKED** by lawful reaper selection, orphan/creator crash, zero-signal bounded abnormal cleanup and external containment.
- **J1 formal acceptance OQ-12 still BLOCKED/NOT_READY** until sealed Lane S/O bytes, independent attestation verifier/custody, CPU guard/runner, frozen criteria and authenticated trust-map origin exist. **OQ-11** gate association remains simulated and unauthenticated; other OQs and owner O-1…O-15 stay undecided.

## Stop condition

Deliver user the committed **Correction 003 handoff link**, the final verified handoff branch HEAD, and the concise Claude Code copy-paste task. **Stop**. No ChatGPT implementation edit, no Python/test, no fixture materialization, no G2 REAL and no claims of Grok approval.
