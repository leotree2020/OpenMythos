# OpenMythos — Claude Code handoff: E1-A G2 J1 SYNTHETIC_CPU_ONLY implementation-only

**Task ID:** `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-PREP-001`  
**Prepared:** 2026-10-28 by ChatGPT; **target implementer:** Claude Code (as directed by owner)  
**Scientific scope:** pure, deterministic **synthetic detector** for B0-shaped records. **NOT** native B0/Parcae modifications or G2 REAL.  
**Owner instruction:** continue through issuing Claude Code implementation instructions; **this prepared handoff is not an executed Claude Code session**.  
**Code execution boundary:** `IMPLEMENTATION ONLY / NO TEST EXECUTION / NO LIVE PROCESS EXPERIMENT / NO CRITERIA FREEZE`. Owner's explicit decision to start the specific coding task in Claude Code is required in the Claude Code session; handing over this prompt is not blanket authority for any later CPU or REAL run.

## 0. Verify remote checkpoint BEFORE writing anything

Remote: `leotree2020/OpenMythos`  
Reviewed **code/document source base SHA**: `07ec81519684e7cc6b0477f086787c4dc32f4520`, branch `d1-r3-a-cpu-003-e1a-g2-j1-spec-v01-doc-20261028`.  
Handoff review branch: `d1-r3-a-cpu-003-e1a-g2-j1-v01-review-claude-handoff-20261028`; **its final HEAD will be verified after this handoff's checkpoint commits**. When taking the task, read the branch's actual GitHub HEAD, confirm this file's exact content and derive a NEW isolated code-implementation branch from that verified SHA. **Never guess that the V0.1 source SHA is the handoff branch final HEAD.**

Mandatory reading order:
1. `research/mini_mythos/docs/SESSION_START_PROTOCOL.md`.
2. Newest checkpoint on handoff branch: `research/mini_mythos/docs/F3B_D1_A_CPU_003_E1A_G2_J1_V0_1_REVIEW_AND_CLAUDE_HANDOFF_CHECKPOINT_20261028.md`.
3. `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_SPEC_V0_1_INDEPENDENT_REVIEW_001.md`.
4. `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md` — **18 fixture definitions; draft, not frozen**.
5. Frozen `research/mini_mythos/a_predicate_003/bench/{observer.py,registry.py,node.py,gate.py,common.py,proto.py}` for **read-only static source mapping**.

Pin the real branch/commit SHA and blob hashes in your checkpoint. If a named file is missing, the branch differs from expected, or Git state is dirty in unrecognized ways: **BLOCKED**, document the discrepancy; don't improvise the baseline or overwrite another person's work.

## 1. Task boundaries: implement SOURCE ONLY

**May create or modify ONLY isolated files** in a new module subtree such as `research/mini_mythos/a_predicate_003/gate_g2/j1/`, and a task-specific checkpoint / documentation link under `research/mini_mythos/docs/`. Inspect existing naming/conventions before deciding exact filenames. Suggested separation:
- `j1/schema.py`: whitelist of allowed SUT input fields, strict types/enums, harness-bound source-handle/provenance descriptors; forbid fixture ID, expected answer, oracle fact, file path, behavior label or test status in any J1-visible input.
- `j1/judge.py`: **pure** `evaluate(assertion_id, subject_observables, declared_trust_model)`, deterministic `subject_verdict=PASS|FAIL|BLOCKED` plus evidence-basis codes. No I/O, no /proc, no clock, no native Bench imports, no fixture-keyed shortcuts.
- `j1/oracle.py`: separate **acceptance-oracle** functions operating on private fixture expectations and J1 output. Never feed Lane O truth into `judge.py` or its trust table. The oracle may describe a future test result but **no tests are run this stage**.
- `j1/codec.py`: deterministic canonical-JSON and sidecar chain/independent-seal **pure functions only**; no real signature custody or filesystem write claims. Explicitly distinguish `LOG_MATCHES_SEAL` mismatch FAIL and `EVIDENCE_USABLE` BLOCKED.
- `j1/README.md` or task-specific design note: trust scope, assertable evidence, exact schema, known limitations, static audit instructions.
- Optionally author **static test SOURCE** under `gate_g2/j1/tests/` with all selected IDs and planned metamorphic cases, but **do not run/import/compile those tests**. No generated JSON fixture bytes, no runtime outputs, no SHA256 for files that do not exist. If authoring realistic fixtures is inseparable from execution, mark that subtask BLOCKED and defer.

Do **NOT** modify:
`research/mini_mythos/a_predicate_003/bench/`, `gate_g0/`, `gate_g1/`, `prereg/`, `evidence/`, `tools/`, `tests/` outside the new isolated j1 test subtree, G0/G1 results, R3, Parcae upstream, OpenMythos Recursive Transformer implementation, training/architecture, or old review/checkpoint documents. No cross-branch merge, auto-PR merge or release.

**No actual CPU test execution even if source is complete.** No experiment authorization file, Linux fork/exec/spawn/wait/signals, janitor, GPU, side-effectful Bench import, real gate release, or REAL descendant. Ordinary read-only git/source inspection and isolated code writing/commit/push are part of implementation logistics, not G2 experiments.

## 2. Required J1 semantic contract (not B0 security testing)

Only J1 input fields from the V0.1 whitelist. A fixture ID or canonical card is private runner metadata; forbid it and grading fields in the subject payload and in anything J1 receives. Use explicit enum for `assertion_id`; `source_handle` is an opaque identifier whose authority comes from a **prevalidated harness-provided trust map**, not from a `source_role` string in untrusted raw payload.

Implement 9 assertion enums:
- **Evidence-sensitive (5):** `ATTRIBUTION` (observed mismatch FAIL / observed agreement limited PASS / missing trustworthy independent gate-child evidence BLOCKED), `UNIQUE_REGISTRY` (finite supplied record set only, duplicate FAIL / unique PASS with completeness prerequisite), `ZOMBIE_AT_T` (pinned Z PASS / pinned S FAIL / missing trusted identity BLOCKED), `LOG_MATCHES_SEAL` (independently trusted manifest match PASS / positive mismatch FAIL / unavailable trust BLOCKED), `WRITE_COMPLETE` (trusted hypothetical wrapper bytes=1 and no errno PASS / zero-or-EPIPE FAIL / only untrusted assertion BLOCKED).
- **SMOKE_ONLY in V0.1 (4):** `PREVENT_PROOF`, `LAWFUL_REAP`, `EVIDENCE_USABLE`, `DELIVERY`. For current selected evidence, do NOT manufacture a PASS. A constant answer without evidence validation still violates good implementation; these assertions carry **no broad accuracy claim** until new discriminating fixtures are authorized.
- Input validation: invalid/missing/malformed *required* evidence → BLOCKED, or an explicitly separate `INPUT_INVALID` diagnostic translated into subject BLOCKED according to predeclared policy. **Do not silently drop corrupt/torn records then PASS**. Reject bool-as-int for pid, starttime, seq, byte counts. PIN `REGISTERED` and `RELEASED` semantics to frozen Bench (RELEASED is intent before os.write R).
- Scope labels must be mandatory in report/oracle: `measurement_target=J1_SYNTHETIC_DETECTOR`, `native_B0_safety_status=NOT_EVALUATED_BY_J1`, `scope=SYNTHETIC_CPU_ONLY`. A detector CPU test PASS on B0 misregistration does **not** change B0 safety status.
- Trust tiers `B0_LEDGER`/untrusted node message/`KERNEL_SNAPSHOT_SIM`/`G2_WITNESS_SIM`/`G2_WRAP_SIM`/`SEAL_MANIFEST_SIM` are separate. The last four are **synthetic assumptions**, not real B0 authenticated evidence. A simulation PASS does not prove an actual independent child observer or real release receipt.
- For a narrowly scoped PASS, record the **exact accepted assertion and supporting observable IDs**, without inferring unobservable fork uniqueness, lawful reaping, unobserved process absence, recipient identity or actual proof of kernel event provenance.

## 3. Planned source completeness; no fixture execution

Read the 18 selected V0.1 fixtures: F01-A/B/C/D, F02-A/B, F03-A/B, F04-A/B/C, F05-A/B/C, F06-A/B/C/D (prefix `J1-`). Each fixture has one proposed SUT assertion and a private expected outcome. The V0.1 proposed distribution is **5 PASS / 5 FAIL / 8 BLOCKED** at *subject* level. They are **not runtime results**. Any future acceptance may require 18/18 **test** PASS with no unknown IDs, but **this implementation stage does not run even one test**.

At implementation time, do not materialize fixture S/O JSON, generate a sidecar, calculate fake fixture hashes, or use a fixture-identity-to-verdict lookup. Instead, code a general algorithm per assertion and provide **static source tests or test skeletons**, leaving byte generation/hashes for a separately authorized later stage. If an exact semantics decision is still open, mark `BLOCKED / NEEDS_OWNER_DESIGN_DECISION` and describe the smallest proposed distinction; do not mutate frozen Bench.

## 4. Strict two-lane answer firewall

- `Lane S` → J1 only: `assertion_id` + synthetic observed records + harness-declared scoped trust (non-answer-bearing).
- `Lane O` → independent oracle only: `fixture_id`, internal scenario names, private ground truth, `expected_subject_verdict`, optional `observed_behavior_label`, expected test verdict, hashes and evidence. The oracle is **not imported or consulted by judge**. Do not log or include Lane O in judge inputs, exceptions, debug messages, source-handle names or callable closures.
- Later metamorphic tests should detect token renaming, irrelevant-record reordering, witness removal and trusted→untrusted swaps, but are **NOT RUN** here. The four SMOKE_ONLY assertion limitations must remain visible in source comments and documentation.

## 5. Implementation-stage acceptance criteria — STATIC REVIEW ONLY

| Criterion | Expected | Evidence to provide | Allowed status |
|---|---|---|---|
| SRC-01 | New isolated branch from verified handoff SHA; permitted changed paths only | Branch/commit, git status, exact diff paths | PASS/FAIL/BLOCKED |
| SRC-02 | `judge.py` never sees Lane O metadata, fixture id or expected verdict; no hardcoded answer table | Static source references, input validator and function signatures | PASS/FAIL/BLOCKED |
| SRC-03 | Source trust map is harness-bound; claims cannot self-upgrade authority | Static evidence, explicit role mapping | PASS/FAIL/BLOCKED |
| SRC-04 | 5 contrasting assertion handlers + 4 labeled smoke-only; strict FAIL/BLOCKED/PASS semantics | Source line map and explanation of each source dependency | PASS/FAIL/BLOCKED |
| SRC-05 | Registry KINDS/RELEASED/DEAD semantics pinned to actual B0; malformed/truncated input never safely accepted | Static parser/validator review and failure-path table | PASS/FAIL/BLOCKED |
| SRC-06 | Canonical sidecar hash semantics never assert sender authenticity; no invented manifest trust or fixture hashes | Static pure-code reading and seal checks | PASS/FAIL/BLOCKED |
| SRC-07 | No Bench/Parcae/G0/G1/R3/frozen evidence modifications; no experiment code executed | Independent git diff and `NOT TESTED` declaration | PASS/FAIL/BLOCKED |
| SRC-08 | Implementation checkpoint complete: source SHAs, dependencies, open design questions, exact next instruction | Markdown checkpoint in docs/ + actual code commit | PASS/FAIL/BLOCKED |

**Static PASS is not a functional/CPU PASS.** The proper statuses at completion are: `IMPLEMENTATION SOURCE PREPARED — STATIC REVIEW PENDING`, `CPU NOT TESTED`, `G2 CRITERIA NOT FROZEN`, `REAL BLOCKED`. Never report execution PASS from successful git commit or syntax inspection. If you cannot complete a requirement under these constraints, record BLOCKED rather than overstep.

## 6. Git actions and stop condition

1. Read and confirm remote HEAD, the V0.1 source design and this handoff. Create **one new code branch**, leaving upstream branch intact.
2. Implement isolated pure J1 files and optional unexecuted static test source. Do **not** edit historical docs or frozen runtime.
3. Read back / inspect git diff and inspect changed-file scope. Use git-only metadata/source viewing; **do not run Python, pytest, model, Bench, process experiments or scripts**, even to get a reassuring green exit code.
4. Commit and push code plus checkpoint. Report real branch name, head SHA, original baseline SHA, clean/dirty state, changed files and unrun status.
5. **STOP. Do not run tests, freeze criteria, merge or start G2 REAL.** Return to ChatGPT for independent code review. Grok may later provide separate findings; do not invent them.

## 7. Copy/paste task prompt for Claude Code

> OpenMythos task `F3B-D1-A-CPU-003-E1A-G2-J1-IMPL-PREP-001`: Please first read the latest `SESSION_START_PROTOCOL.md` and `F3B_D1_A_CPU_003_E1A_G2_J1_V0_1_REVIEW_AND_CLAUDE_HANDOFF_CHECKPOINT_20261028.md` from branch `d1-r3-a-cpu-003-e1a-g2-j1-v01-review-claude-handoff-20261028`. Verify its current remote HEAD, pin commit and source hashes, then read `G2_J1_CPU_SPEC_V0_1_INDEPENDENT_REVIEW_001.md`, `G2_J1_CPU_ONLY_FIXTURE_PREREG_DRAFT_V0_1_20261028.md` and this full handoff. On a new isolated branch, **IMPLEMENT SOURCE ONLY**: pure J1 schema/judge, separate oracle, canonical codec, static test-source skeletons and checkpoint as defined here. Absolutely no test execution, no fixture-data materialization/hashes, no real fork/wait/signal, no GPU, no native Bench/Parcae/frozen files edits, no unauthorized criteria freeze, no merge. If design assumptions are unimplementable safely, record BLOCKED. Commit/push only the isolated implementation source and checkpoint, verify permitted paths, stop and return exact Git SHAs and a static acceptance matrix for ChatGPT review.
