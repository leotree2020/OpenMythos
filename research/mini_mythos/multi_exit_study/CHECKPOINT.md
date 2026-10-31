# MES-1 checkpoint — 2026-10-31

## Purpose and current state

User approved beginning development of the 2026-10-31 MES research plan. Read live PR20 and mech_ab/CHECKPOINT.md at 4cf60b053c7b9c2e89e64646cd986d33a34a7657 first. Reuse the existing A mechanism rather than rebuilding it. Old A primary FAIL, within-four-step signals, and all old evidence remain unchanged.

**MES-1 phase-one code implemented. CPU component/fixture checks PASS. Original-runtime preparation and 20 native training trajectories NOT TESTED. Actual local native attempt BLOCKED on incompatible Python before source/model construction; zero native optimizer updates. Actual independent pre-training review DEFERRED.** No new model score or efficiency claim.

## Git and isolation

New branch mini-mythos-mes1-budget-holdout-cpu-20261031, based on PR20 HEAD4cf60b053c7b9c2e89e64646cd986d33a34a7657. C research remains on its own branch; no merges or deletion. Protocol committed FIRST at c74728c3efb6f27e29aacf146d719e37c5dbbd1c. Tested code delivery through 9e067d5d6363dd5cc39c0ec418d9c0a72de5bd3c; current HEAD additionally contains this checkpoint. Only new research/mini_mythos/multi_exit_study files. Upstream pin69284c13746e849104f738d6d1a347b1f457df76, factory, task, A implementation, older protocols, J1/Bench/R3 untouched.

Six published Git blobs verified against locally tested bytes: protocol f04549ceafcd2ad37ca4e56f62bd1362e0bd8e56; policy7bb71fd354ebf83aceb11a099750679e5c5ed586; runtime ac53ca7172082753e2c3df02ab971a360f776331; runner a9e0e6a0ae9eaadd65517dd7ce615bd1de4dc307; tests19ccb98cf4a7ca45f7e8ed9dfc4ddc4187be4936; launcher0bafbebb61ff5b35e528c4aa4f663004cb48f1df. A transient publishing transcription discrepancy was corrected BEFORE delivery; final runtime blob exactly matches tested code. No model execution used the intermediate revision.

## What is implemented

Four arms GPT/P2/P4/A, five NEW seeds101/202/303/404/505. Native GPT is four distinct blocks; P2 two recurrent steps; P4 four recurrent steps; A unchanged 0.25 exit2 plus0.75 exit4 supervision on the same four-step trajectory/shared suffix. No B/C/D/E combination or inactive-path repair.

Common supported-op training budget436285440000 per seed/arm. Before training, native probes at actual32x9 must reproduce frozen step counts. Steps GPT5941/P2=5433/P4=3822/A3000; integer slack<=0.1%. Cheaper arms see more repeated samples; NOT equal token budgets or hardware costs. P4 also saves step3000 for the same-update contrast; all arms save step3000/end (35 total snapshots, A deduplicated). Exact initialization pair_io retained, all batch sequences share the per-seed prefix. Only Parcae RNG consumption is prefix-paired; GPT is seed-matched rather than assumed identical RNG consumption.

H1=2048 new canonical reserved pairs; HC1024/H2=2048 allocated but not opened. SHA ranking and category quotas fixed in protocol. Swapped operands stay together. prepare constructs no model-facing holdout answers; train evaluates no holdout. Only after all20 trajectories and snapshot/hash checks pass may evaluate generate H1 and produce40 scoring conditions. Existing task masks/prompt-only free generation reused; teacher-forced CE separate. Saved predictions are evaluations of the SAME2048 questions, not81920 independent questions.

Primary equal-budget A4-P4: mean>=1pp, every seed loss<=1pp, ceiling disclosed. Same-update contrast, GPT safeguard, A2 versus dedicated P2, A depth benefit and cost all separate. Paired crossed bootstrap5000 replicates/private seed731031 preserves seed/question pairing; interval diagnostic, no automatic significance/noninferiority claim. Formal Oracle unchanged.

Snapshot saving includes model/optimizer/RNG/indices and performs an actual local weights_only reload/equality check in the producer. This is not interrupt-resume replay or independent auditor binary verification. Each training/evaluation arm uses an isolated process; process RSS and timings are descriptive, not repeated hardware benchmarks. Valid numerical failure FAIL; environment/source/evidence failure BLOCKED. Partial files are retained, no silent retry/resume/tuning.

## Actual preparation checks

Local Python3.13.5/torch2.10.0+cpu/NumPy2.3.5/einops0.8.2. No installation, GPU purchase or native training. A raw source download was unavailable (DNS); live source/metadata accessed through GitHub, existing attachment source bytes reused and checked.

|Check|Actual status|Scope|
|---|---|---|
|Python3.12 AST and Bash syntax|PASS|New files|
|CPU components|22/22 PASS|Budget arithmetic, split isolation, pairing/bootstrap, GPT/P2 routes, A formula/RNG, safe snapshot reload, review/barrier/JSON failure cases|
|Fixture pipeline|PASS|20 train paths,20 eval paths,40 conditions,90 optimizer updates,35 safe snapshots; AFFINE/TANH ONLY, not20 native runs|
|Tampered binary / premature H1 barrier|PASS|Fixture refuses evaluation before complete evidence|
|Launcher preservation|21/21 PASS|All three phase types across complete/fail/blocked/partial/unrelated/corrupt cases, existing bytes unchanged|
|Actual native invocation here|BLOCKED as expected|Rejects Python3.13.5 versus required3.12.3; zero models/training/H1|
|Published source identity|6/6 PASS|Live Git blobs equal local checked bytes|
|Original-runtime preparation and20 model trajectories|NOT TESTED|Must run in existing Codespaces CPU environment|
|Grok/Claude pre-training review|DEFERRED|No real report supplied; never call this PASS|

Detailed scripts/logs/identities are in the conversation development bundle, including fixture-only pipeline and launcher checks. No saved fixture score is model evidence.

## Next bounded action

Use pinned worktree then run:

    bash research/mini_mythos/multi_exit_study/run_codespaces_cpu.sh prepare

Default existing runtime /workspaces/mythos-m2-cpu312/bin/python and upstream /workspaces/mythos-parcae-pinned. No download/install. Output /workspaces/OpenMythos/mythos_evidence/mes1_v1/prepared.json. This performs original-runtime compatibility and actual budget probes for NEW seeds, no optimizer updates, no repeated old initializer audit, no H1 scoring.

The approved plan calls for focused independent review BEFORE training. Provide the actual report using --review-report FILE --reviewer NAME --review-approved on the train command only after review resolution. These flags record owner acknowledgement and report bytes/hash; they do not authenticate reviewer identity or manufacture a Grok PASS. Missing report blocks train without corrupting a completed prepare. After train PASS, evaluate runs H1 once. Existing phase results are read-only. No new authorization is implied by a prepare PASS.

Focused reviewer: inspect only changed MES files and reused interfaces; verify native GPT/P2 objective routes; FLOPs floor/slack and same-update versus same-budget claims; initialization/sample/RNG prefixes; complete20 barrier and35 snapshot bindings; reserved-H1/HC/H2 disjointness and no labels to generator; paired bootstrap and independent outcomes. Do not restart project-wide/initializer audits. Disagreements remain open until resolved, no fabricated review.

MES-2 subtraction and MES-3 early exit NOT IMPLEMENTED/NOT TESTED; not auto-launched. A-M2L-01 inactive paths and separate Claude init-root-cause OPEN; old JSON handoffs remain complete. Keep Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, GPU expansion or upstream edits.
