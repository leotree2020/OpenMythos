# MES-1 checkpoint — native prepare reported PASS, 2026-10-31

## Current status and evidence boundary

**The user supplied actual Codespaces terminal output for the fixed prepare run: all five seeds report native_prepare PASS, phase prepare reports PASS and exit_code 0. The original GPT interface blocker is no longer observed in this run. Twenty native training trajectories and H1 quality evaluation remain NOT TESTED. Independent pre-training review remains DEFERRED.**

This update records USER-PROVIDED EXECUTION OUTPUT, not an independent rerun or byte audit. The new prepared.json has not been uploaded in this handoff; its SHA-256 below is terminal-reported only. Do not claim to have independently loaded its detailed native checks, verified its bytes, or confirmed training performance. Preparation includes bounded forward/backward and compute probes, but no optimizer updates and no H1 model scoring.

The latest request contains duplicated/garbled shell-echo text, but the supplied execution output identifies the fixed commit, all five successful seeds and the final result. Do not infer the exact actual worktree directory from the corrupted echo, delete directories, or rerun prepare solely to clean up the pasted command.

## 1. Git, previous incident and unchanged boundaries

Repository leotree2020/OpenMythos; existing Draft PR22; branch mini-mythos-mes1-budget-holdout-cpu-20261031; base4cf60b053c7b9c2e89e64646cd986d33a34a7657. Executed source remains **7bcb08f480d0bda2dba5b1351442190001492782**. This checkpoint update is documentation only; do not replace the execution pin with a new documentation commit when resuming the existing experiment.

Protocol was committed first at c74728c3efb6f27e29aacf146d719e37c5dbbd1c. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains the required read-only source. Reused factory/task/A, protocol, policy constants, budgets and thresholds are unchanged by this status update.

Historical failed prepare at a8f329ed3ae7e0e55a703dfaee9c2ce56339b953 remains BLOCKED/exit2. Keep `/workspaces/OpenMythos/mythos_evidence/mes1_v1/prepared.json` and all old outputs intact. Its terminal-reported SHA256 is5d1dfb655170b8e6bfb5c98f507b490266e708b65231fc053d0906cd2169589f; no independent file audit was performed.

The bug was the MES wrapper and CE check requesting GPT labels and logits together. Fixed native calls separate labelled loss from unlabelled logits; no upstream modification or changed objective. Full incident history and local regression details remain in this checkpoint at commit7bcb08f480d0bda2dba5b1351442190001492782 and [evidence/gpt_interface_fix_20261031.json](evidence/gpt_interface_fix_20261031.json). Those historical local checks are not newly executed by this update:29 component tests,40 pinned-forward component-double cases, fixture pipeline and21 launcher cases passed in the previous session; they are not independent native training evidence.

## 2. New user-reported preparation result

- Experiment: MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1.
- Source shown in terminal:7bcb08f480d0bda2dba5b1351442190001492782.
- Seeds101,202,303,404,505: native_prepare PASS; training NOT TESTED for each.
- Phase prepare, status PASS, exit_code0.
- Output `/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1/prepared.json`.
- Terminal-reported SHA256 **d6ec93cb908d3994b6098b913c9b045d06b055a8fbade92bf62cdd0c5ae20678**; NOT independently byte-verified here.
- Common counted training ceiling436285440000 FLOPs per seed/arm.

|Arm|Steps|Counted FLOPs/step|Allocated total|Unused fraction|
|---|---:|---:|---:|---:|
|GPT|5941|73433088|436265975808|0.00004461343472750317|
|P2|5433|80289792|436214439936|0.00016273764258555132|
|P4|3822|114130944|436208467968|0.00017642585551330797|
|A|3000|145428480|436285440000|0|

These printed counts and allocations match the predeclared values. The largest reported unused fraction is about0.017643%, within the frozen0.1% integer-slack allowance. This is a supported-operator budget, not exact hardware work or equal sample exposure. No budget relaxation was introduced.

## 3. Scientific design stays fixed

Four arms GPT/P2/P4/A x five new seeds. A uses0.25 exit2 +0.75 exit4 on the same four-step trajectory/shared suffix. Original optimizer and paired initial recipe remain. No B/C/D/E combination or inactive-path repair.

Save step3000 and budget endpoint:35 deduplicated model/AdamW/RNG/index snapshots. H1=2048 reserved pairs may be scored only after all20 trajectories and evidence barriers complete. HC1024/H2=2048 remain unopened for model evaluation. Primary equal-budget A4-P4 requires mean gain>=1 percentage point and each seed loss<=1 point, with ceiling disclosed; same-update, GPT/P2 safeguards and depth benefit are separate. Bootstrap is diagnostic, not automatic statistical acceptance.

## 4. Next action — focused independent review, then train

Do NOT rerun preparation, reset the worktree, reuse the old blocked directory, start another initialization audit or create a new experiment. Retain the existing fixed source and successful preparation output.

Request one actual focused Grok/independent report against **executed commit7bcb08f480d0bda2dba5b1351442190001492782**, covering the MES files and reused interfaces only: native GPT loss/logits separation; immutable A objective; equal-count versus equal-update design; dedicated GPT/P2 controls; sample/RNG pairing; H1/HC/H2 separation and complete20-run barrier;35 snapshot bindings; separate quality/cost claims. Reviewer must distinguish source inspection, any tests actually run, and the user-provided prepare output. No full training, H1 scoring, source modification or protocol changes as part of that review. Unresolved findings stay open. Missing reviewer access must be disclosed rather than inventing PASS.

Train continues to require a REAL report and owner acknowledgement through --review-report FILE --reviewer NAME --review-approved. The flags do not authenticate the author or constitute independent review; merely creating a file or granting permission is not a review. No review has been supplied in this handoff; the live PR discussion was also empty at this read.

Subsequent train/evaluate must explicitly retain:

    MES1_OUTPUT_DIR=/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1

Use the actual existing worktree at executed commit7bcb08f, verifying its path and version rather than assuming the garbled pasted path. Train produces training.json; only completed training permits evaluate/result.json. The review content may require a code fix; if so, preserve evidence and separately decide which affected preparation checks need renewal rather than waiving source identity.

## 5. Stage acceptance and checkpoint rule

|Item|Status|Evidence scope|
|---|---|---|
|Fixed original-runtime prepare|PASS (user execution report)|Five seeds and final phase output received|
|Printed budget agreement|PASS (reported-count arithmetic)|Not an independent native profiler run|
|New prepared.json byte/detail audit|NOT TESTED|Raw file not uploaded in this handoff|
|Independent pre-training review|DEFERRED|No actual report received|
|Twenty native training trajectories|NOT TESTED|Do not infer from prepare PASS|
|H1 model evaluation/quality/efficiency|NOT TESTED|No predictions or quality result|
|Formal Oracle|BLOCKED/NOT_READY|FORMAL_ACCEPTANCE_READY=False|

MECH-AB/C and older scientific outcomes remain unchanged. A-M2L-01 and the separate reviewer initialization mismatch cause remain open. Keep PR22 Draft/unmerged. No G2 REAL, GPU expansion, upstream/J1/Bench/R3 modifications, automatic merges, or MES-2/3 launch. The date above is the checkpoint date, not an inferred native run timestamp.
