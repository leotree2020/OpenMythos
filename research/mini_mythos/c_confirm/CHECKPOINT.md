# C1 checkpoint — confirmation code prepared, native execution pending

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1.

## Current decision

Owner said "OK，开始C" after MES-1. Implemented a NEW bounded confirmation of the existing C4 recipe versus native P4 and GPT. This is not a repetition of MECH-C development training, not A+C, and not a new model architecture. No native C1 training or heldout inference has occurred in this development session. Claude Code review is NOT TESTED/PENDING, not inherited from the earlier MES approval.

**Fixed executable source: 8a646eb56a9bcffb9767ad9f50843f85670b2fa1.** All five new Python/Bash code files and PROTOCOL.md match locally checked bytes by Git blob identity. Subsequent checkpoint/review documents do not change the hashed runtime/protocol set. Keep one execution pin once preparation has run.

## 1. Git and immutable baseline

Repository leotree2020/OpenMythos; branch mini-mythos-c1-budget-confirm-cpu-20261031. Base PR21 branch mini-mythos-mech-c-lora-cpu-20261031 at b16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c. All changes under research/mini_mythos/c_confirm/. Do not modify older results or source directories.

Protocol committed FIRST at06794bebae186470a9a05d728b59b4f42869e6ae, before implementation/tests/model-quality measurements. Existing c_adapters.py reused without modification (Git blob28c979185dec965d77d248901a84c0596ae32b54, SHA2567696f81ac867e030b4d894c44e2fad176a79ec407e1919cf284f5fdb130b9101). Native upstream remains read-only sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Original factory/task/MECH-AB helpers are hash-bound.

MECH-C old primary C4-S16/secondary C4-P4 exploratory PASS and low-seed limitations remain unchanged. MES-1 current A recipe's competitive FAILs remain unchanged. Neither old outcome is a C1 outcome. New primary explicitly asks C4 vs native P4, rather than beating a degraded S16 comparator. No S16 training here, hence no pure depth-specificity causal identification or parameter-matched claim.

## 2. Actual implementation

Three groups GPT/P4/C4, five NEW seeds1101/1202/1303/1404/1505. All from scratch. C4 retains four independent rank4 corrections on native core attention/FFN output projections, scale1, final-only loss. All backbone and adapter parameters are optimized; all are saved and loaded. P4/C4 match base initialization and batch/RNG prefixes. GPT uses the already-known safe interface: labelled native loss OR unlabelled logits, one train forward. No A/B, inactive-parameter repair, LR/rank/depth search or eight-round extrapolation.

Common ceiling355663872000 supported-op training FLOPs. Planned counts/steps, to be re-measured in native prepare:

|Arm|Step FLOPs|Steps|Registered parameters|
|---|---:|---:|---:|
|GPT|73433088|4843|65344|
|P4|114130944|3116|60224|
|C4|118554624|3000|62784|

Count mismatch BLOCKS before training, no automatic re-budgeting. Same count is not equal data exposure/hardware work. Twenty complete full-state snapshots (all15 endpoints plus5 P4@3000) support twenty depth4-only evaluations. No untrained d2 readout study is added. Costs/times/RSS are separately reported.

C1T uses2048 fresh canonical pairs,512 per carry stratum, from reserved role excluding ALL5120 MES H1/HC/H2 keys. Legacy allocation hashes re-created exactly; C1T allocation digest14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0. Key/stratum allocation only: actual C1T answer labels and model evaluations not generated in this development. HC/H2 remain reserved. Fixture pipeline used8 hand-picked questions, with zero overlap with C1T/HC/H2; one overlaps already-viewed MES H1 and is not a fresh test claim.

Prepare/train/evaluate remain separate explicit commands. Training requires actual Claude report and owner acknowledgement; production dependencies cannot be waived. All15 completed runs plus file/pairing checks precede C1T materialization. Each eval worker hashes/parses the SAME byte buffer, addressing the prior MES R02 omission in this NEW runner (the old MES source is not rewritten). Duplicate workers claim ownership exclusively; errors without ownership never rewrite old row/logs, addressing the prior R03 path in this new implementation.

Primary C4-P4 equal-budget: mean gain>=1pp, every seed loss<=1pp, reference>99% means ceiling BLOCKED. GPT safeguard: mean and every paired loss<=1pp. Candidate selection requires BOTH primary and GPT safeguard PASS. Same-update C4-P4@3000 is independent secondary output; it cannot rescue primary failure. Execution PASS is separate. CLI prints all decisions and selection exit0/1/2. Five-seed crossed bootstrap is diagnostic, not statistical acceptance.

## 3. Actually executed checks and limits

Development runtime Python3.13.5/torch2.10.0+cpu, not the required production Python3.12.3/torch2.11.0+cpu. No packages installed, no GPU, no native GPT/Parcae construction/training or C1T inference.

|Check|Actual result|Scope|
|---|---|---|
|Python3.12 AST and Bash syntax|PASS|Four Python code files and launcher|
|New CPU component tests|29/29 PASS|Strict GPT interface, C4 hooks/zero-init math, full adapter snapshot, budgets, exclusions, score and evidence boundaries; mathematical fixtures|
|Full phase pipeline fixture|PASS|15 train paths/15 eval worker paths/20 conditions/20 safe snapshots/65 tiny fixture optimizer updates; NOT native learning|
|Launcher existing/partial evidence|20/20 PASS|Existing PASS/FAIL/BLOCKED/PARTIAL, corrupt JSON, missing env, partial directory/log, invalid phase|
|Published byte identity|6/6 PASS|Five new code files plus protocol match local checked bytes|
|Production entry attempted locally|BLOCKED as expected|Original Python version gate, before native models; did not bypass guard|
|Native C1 prepare and cost counts|NOT TESTED|Must use existing Codespaces CPU environment|
|15 native training trajectories/C1T quality|NOT TESTED|No results yet|
|Claude Code C1 independent review|NOT TESTED/PENDING|Earlier MES approval is not this review|

Live pinned MECH-C directory blobs matched retained source copies. The factory digest is bound from the frozen project declaration; its native execution was not repeated locally. Tests are not full production acceptance. Local preparation refusal and full logs are preserved in the conversation development ZIP. Initial publication omitted the adapter-digest declaration; corrected at8a646eb BEFORE delivery; final five source blobs match the tested local implementation. No native run used the intermediate incomplete publication.

## 4. Next bounded instruction

Create a separate worktree /workspaces/mythos-c1-20261031 at executable8a646eb ONLY if absent; verify actual directory and HEAD, never reset/delete existing work. Run only:

    bash research/mini_mythos/c_confirm/run_codespaces_cpu.sh prepare

Default output /workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1/prepared.json. Reuses existing /workspaces/mythos-m2-cpu312 and /workspaces/mythos-parcae-pinned. No download/install, optimizer step or C1T scoring. This is C1's new source/budget/interface preparation, NOT a rerun of old MES or initialization audit.

In parallel obtain ONE focused Claude Code review of C1 delta plus reused C adapter interfaces. Provide actual prepared.json when available; do not claim its byte verification before receipt. Native training waits for real APPROVE and owner's acknowledgement using --review-report/--reviewer/--review-approved. Do not fabricate an approval. Successful prepare does not automatically start training or unlock evaluation.

## 5. Governance and stop rules

Claude Code replaces Grok by owner's explicit decision; no extra Grok approval gate. Preserve historical reviewer attribution. Disagreements resolved by evidence or minimal controlled experiments. Keep this PR Draft/unmerged until reviewed and results decided.

Preserve previous A-M2L-01/inactive paths and independent initializer mismatch limitations. Stop at frozen outcomes; no seed replacement, threshold repair, repeated target selection, GPU scaling, D/E combination or later MES phases. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, J1/Bench/R3 or upstream changes. End each stage with new actual status and next action, never equate script completion with quality.
