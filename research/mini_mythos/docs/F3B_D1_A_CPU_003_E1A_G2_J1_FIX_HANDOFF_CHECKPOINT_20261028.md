# F3B-D1-A-CPU-003 — J1 source-only correction handoff checkpoint (2026-10-28)

## Official stage status and one next step

**`J1 SOURCE-ONLY CORRECTION HANDOFF PREPARED — CLAUDE CODE NOT INVOKED`.** The previous J1 implementation has **`INDEPENDENT STATIC REVIEW: CHANGES REQUIRED`**; this is *not* a CPU test failure, and this handoff does **not** correct implementation source.

**`J1 CPU SYNTAX/IMPORTS/HANDLERS NOT TESTED`; `18 S/O FIXTURES NOT MATERIALIZED`; `CRITERIA NOT FROZEN`; `G2 REAL BLOCKED / NOT AUTHORIZED`; `GROK DEFERRED / NOT PERFORMED (NOT PASS)`; `G2 O-1…O-15 OWNER UNDECIDED`.** Historical G0/G1 results, Bench, upstream Parcae, R3, model code and evidence remain unchanged.

**Only next instruction:** user sends the prepared, pinned **Claude Code source-only correction task** to Claude Code. Claude then creates an isolated code branch, fixes F01…F06, writes unexecuted negative-test source/checkpoint, commits/pushes and STOPS. Return the new branch and SHA to ChatGPT for independent static review. **No CPU/test/REAL, fixture materialization, criteria freeze, merge, or synthetic-to-real promotion.**

## Exact source provenance

- Read-first independent review branch: `d1-r3-a-cpu-003-e1a-g2-j1-impl-static-review-20261028`, **remote HEAD independently checked** at `1b2ba339d267b8c04e1db5fb71d29da45a597758`.
- Independent reviewer findings: `research/mini_mythos/a_predicate_003/gate_g2/G2_J1_IMPL_SOURCE_INDEPENDENT_STATIC_REVIEW_001.md`, Git Blob `b9fa2ac3cced2152e3b4610ea5f3dd40f7e94ee6`.
- Latest reviewer checkpoint input: `docs/F3B_D1_A_CPU_003_E1A_G2_J1_IMPL_STATIC_REVIEW_001_CHECKPOINT_20261028.md`, Git Blob `107035d939e9bd7471c3bf1c4af74a8ba673b26d`.
- Original implementation code branch: `d1-r3-a-cpu-003-e1a-g2-j1-impl-20261028`, independent remote HEAD `a1678a5a31ae49ac1aca33cdcfd625efe2108e68`, code commit `f9151a9c6156ada24f6f4f77270eb004a713bf0a`, original source baseline `02d79a26e4ad6b49527bc90e6be4fe9130b45cff`.
- Review-source code blobs: `j1/schema.py=0c016df638832931128b65e453e510d9d0483be0`, `judge.py=54cecf6cc28bbc97b2c7e121015dcbc46e7ab7fa`, `codec.py=bb486c922b945dd30edb003a11fe7758bd13c2fb`, `oracle.py=1a0de1c3913043f14dbacd248dd3f01825756c3e`. Frozen `bench/registry.py=3f2179e132371dd323f865be8a4d41fa5e58786d`; no source modified by this handoff.
- This new docs-only branch: `d1-r3-a-cpu-003-e1a-g2-j1-fix-handoff-20261028` created from exact review HEAD `1b2ba339d267b8c04e1db5fb71d29da45a597758`.
- Primary deliverable: `a_predicate_003/gate_g2/CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_HANDOFF_20261028.md`, created in commit `54a52500cf506464ef456eb0d6534eea4d47a63b`. **Claude Code must fetch the final HEAD of this handoff branch after all navigation/checkpoint commits; do not treat its start SHA as final.**
- This checkpoint is created before navigation/verification addenda. Actual final HEAD/diff will be independently fetched and recorded. User's local checkout and Claude's local working tree **NOT TESTED** by this document-preparation session.

## Objective / environment / controlled input / expected / actual / status

| Item | Value |
|---|---|
| Objective | Prepare unambiguous, code-only Claude Code correction instructions, source-grounded in J1-IMPL-F01…F06, without writing code or running tests. |
| Environment | GitHub connector read/write for Markdown-only documents on isolated branch. No Python, shell-run tests, process forks, signals, GPU, Bench or model execution. |
| Input | Last static review report and checkpoint, actual J1 source locations, frozen `bench/registry.py` lifecycle/check_order and V0.1 18-case design matrix. |
| Expected | Task with exact Git provenance, file scope, fail-closed test/oracle conditions, small unexecuted negative-control source, static FIX-01…FIX-08, single stop instruction. |
| Actual | Full Claude Code SOURCE-ONLY correction handoff prepared and committed. No implementation code edited or executed by ChatGPT; no Claude session invoked. |
| Handoff documentation preparation | **PASS (document creation only)**; independent functional correctness **NOT TESTED**. |
| Git docs-only scope | **PENDING final remote compare**, verify before closing. |
| J1 source correction | **NOT STARTED BY THIS SESSION**; previous implementation still **CHANGES REQUIRED**. |
| CPU syntax/import/fixtures/tests | **NOT TESTED / NOT AUTHORIZED**; 18 fixture S/O bytes/hashes NOT MATERIALIZED. |
| G2 REAL | **BLOCKED / NOT AUTHORIZED**. |
| Grok dual review | **DEFERRED / NOT PERFORMED**; no fabricated PASS. |

## Findings preserved and prescribed correction

| Finding | Static review outcome | Claude Code correction target |
|---|---|---|
| F01 HIGH | Malformed input's subject BLOCKED may receive test PASS | Explicit `INPUT_INVALID`/diagnostic validation barrier and independent fixture preflight; test acceptance remains BLOCKED until input valid |
| F02 HIGH | Forgeable expected answers and 18-row all-PASS aggregate | Bind private answers to V0.1 tuple; prohibit scope shrink; formal aggregate requires independently attested S/O+result evidence, otherwise BLOCKED |
| F03 HIGH | Same-node without same-ticket/gate join can PASS | Explicit matched independent synthetic gate/ticket association; missing/conflicting binding BLOCKED; no B0 native witness invention |
| F04 HIGH | RUN_START missing required metadata can still yield UNIQUE_REGISTRY PASS | Source-grounded RUN_START, RUN_END, creator/ordering constraints; no "complete log" global inference from finite records |
| F05 MEDIUM | Role map self-declared by caller is not authenticated provenance | State trust as external hypothetical harness assumption; never claim live authenticity |
| F06 MEDIUM | Real B0 record floats and fields incompatible with J1 closed schema | **Synthetic-only scope**; real native adapter deferred, no lossy conversion now |
| F07 PROCEDURAL | One accidental empty Python interpreter was started in original task | Preserve `SRC-07 strict no-Python compliance FAIL (self-reported)` historically; strict no-Python rule for correction; no falsified retrospective PASS |

**All negative test examples are unexecuted thought-experiments**. If a correction requires changing the 18 predeclared `expected_subject_verdict` labels, frozen Bench, Parcae or model architecture, report **BLOCKED / NEEDS OWNER DECISION**, not a silent workaround. The four V0.1 SMOKE_ONLY assertions remain smoke-only, and the five contrasting assertions remain limited to synthetic trusted assumptions.

## Dependencies, scientific boundaries, and delegated responsibility

- **ChatGPT:** research/acceptance design, independent source static review, reviewer checklist and checkpoints.
- **Claude Code:** actual Python source patching and unexecuted test **source**, only after user starts the specific bounded task in Claude Code. It must create a new branch based on the final handoff HEAD and preserve upstream/frozen artifacts.
- **Grok:** review deferred while unavailable. Any later disagreement preserved and adjudicated with a *separately authorized* minimal CPU controlled experiment.
- Dependencies: Python standard library only in existing J1 source; no dependencies installed or invoked for this handoff. Future canonical fixture bytes, independently retained truth/seal, fail-closed trust harness and CPU guard require distinct review and authorization.
- G2-REAL's lawful reaper, orphaned descendant, no-signal completion and external manual containment remain unresolved; synthetic J1 **cannot certify** any of them.

## Final handoff stop condition

Deliver to the user:
1. GitHub link to the full `CLAUDE_CODE_J1_SOURCE_ONLY_CORRECTION_HANDOFF_20261028.md`.
2. Verified final handoff branch HEAD, review baseline and current source implementation SHA.
3. A concise, copy-ready Claude Code instruction to read this checkpoint, verify remote SHA, perform *SOURCE ONLY* fixes F01…F06, commit/push and **STOP**.
4. **No code execution, no CPU or REAL, no Grok review claim.**

After the user submits it to Claude Code, the next ChatGPT turn begins by reading **Claude's newest code branch checkpoint and actual changed SHA**. Do not infer progress from chat memory or from this unexecuted task brief.

## Verified Git-only stage closure addendum (remote readback)

- At pre-addendum remote HEAD `8644985a65b818c0f27e0f7c6d9f336449bcd4b3` compared with input review SHA `1b2ba339d267b8c04e1db5fb71d29da45a597758`, GitHub returned **5 documentation commits** touching exactly **4 Markdown paths** (new Claude Code correction handoff and this checkpoint, plus navigation-only PROJECT_MAP and SESSION_START_PROTOCOL); **204 insertions, 0 deletions**. No `gate_g2/j1/` source code, Bench, Parcae, R3, G0/G1, frozen criteria/prereg, evidence, tests or tools changed.
- Handoff Git Blob at readback: `5026f1070e8ea9dcf92c8c6de7dc45896d038d51`. Explicit names **J1-IMPL-F01, F02, F03, F04, F05, F06** are present in the handoff; historical F07 procedural deviation preserved separately.
- **Git scope: PASS (docs-only)**; **Claude Code correction: NOT STARTED**; **J1 CPU: NOT TESTED / NOT AUTHORIZED**; **G2 REAL: BLOCKED**. The reviewer local checkout was not inspected; only remote GitHub branch/diff were verified.
- This checkpoint append writes another Markdown-only commit, so **the actual final branch HEAD must be re-fetched after this write** and used in the Claude Code prompt.
