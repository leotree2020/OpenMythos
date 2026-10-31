# MES-1 checkpoint — complete training records audited, H1 pending (2026-10-31)

## Current decision

**Uploaded training.json is complete:20 user-run trajectories,90980 recorded optimizer updates and35 snapshot references. Actual read-only JSON/record audit PASS,403 checks/0 failures. H1 evaluation and all quality/efficiency claims remain NOT TESTED.** No training was repeated in this audit. Do not request this file again or rerun prepare/train for sealing.

The next bounded action is the existing reviewed `evaluate` phase on saved weights, with supplemental endpoint evidence checks. Do not tune models, pick better checkpoints, open HC/H2, or launch MES-2/3. Execution source stays **7bcb08f480d0bda2dba5b1351442190001492782**; do not change the prepared worktree to this documentation HEAD.

## 0. Reviewer rule

Effective2026-10-31 the owner replaced Grok with **Claude Code** for independent review. ChatGPT and Claude Code cross-review; unresolved disagreements are retained and resolved by source/evidence or minimal controlled experiments. Grok is not an additional pending approval dependency. Historical attribution is preserved; former unperformed Grok assignments are superseded, not retroactively PASS.

Claude's owner-supplied pre-training report APPROVE remains scope-limited. See [evidence/MES1_CLAUDE_REVIEW_20261031.md](evidence/MES1_CLAUDE_REVIEW_20261031.md), first registered at80c35f7321039f8351a13f56375413408f14407d. Original scratchpad bytes/scripts/logs were not independently retrieved. Its CPU component checks used torch2.11.0+cu130, not the production CPU build. No post-training Claude result audit has yet occurred.

## 1. Git and preserved history

- Repository leotree2020/OpenMythos; Draft PR22, branch mini-mythos-mes1-budget-holdout-cpu-20261031, base4cf60b053c7b9c2e89e64646cd986d33a34a7657.
- Reviewed/executed code7bcb08f480d0bda2dba5b1351442190001492782; upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 unchanged.
- Protocol first committed c74728c3efb6f27e29aacf146d719e37c5dbbd1c. Factory/task/A, all thresholds and the optimizer remain unchanged.
- Previous handoff HEAD0cf2162876577230197539a196e6991133cf531a registered the review and train-only launcher. It did not claim training results.
- This audit evidence summary: [evidence/uploaded_training_audit_20261031.json](evidence/uploaded_training_audit_20261031.json), first commit667113621d1b367705602bdec810c030e8cb9b2a.
- New supplemental evaluation-only helper: [evidence/evaluate_after_training_20261031.py](evidence/evaluate_after_training_20261031.py), commit eab4d676f3d95beb867f8e468008bfda2c6fb09f. This helper is not part of Claude's prior reviewed code, and does not edit it.

Original a8f329ed prepare remains a preserved BLOCKED incident from the unsupported simultaneous GPT loss/logits request. The fixed prepare later reported all five seeds PASS. Its existing file at mes1_v1_gptfix1/prepared.json has terminal digest d6ec93cb908d3994b6098b913c9b045d06b055a8fbade92bf62cdd0c5ae20678. It is still not uploaded here; its detailed checks must not be described as independently re-audited. Old mes1_v1 failure evidence stays untouched. See earlier checkpoints and gpt_interface_fix_20261031.json for the full incident history.

## 2. Uploaded training evidence and actual audit

Original uploaded training.json: **16257800 bytes**; independently computed SHA256 **318b0cfbca08f5c33f36b7514300186e63e3a404c8ee1aac7e1177e4de021f69**. No separately supplied terminal digest for this file; no external hash match or authenticity proof claimed. Input bytes unchanged.

Top-level records: experiment MYTHOS-MES1-EQUAL-COUNT-HOLDOUT-V1; phase train; status PASS; exit0; pairing_status PASS; H1_status NOT OPENED; quality_status NOT TESTED. Review is owner-acknowledged Claude Code, recorded report SHA256 a6de1292561d416a721e5c8e6bc31655400017d5cfe7c071792f4f1e42c1cad7. Reconstructed declared source identity298cb63094c3c67e76786a387e79d302d707ecc8e959c566561281a097db56c9 matches all20 rows/review.

Auditor actually ran Python3.13.5/torch2.10.0+cpu. Torch was used only to regenerate integer batch indices. No native model imports, native forward/backward, optimizer updates, profiler replay, weight loading or held-out examples/scoring. Source reading used live GitHub and byte-checked retained code. Six MES code/protocol blobs match live pinned Git metadata; four inherited source files match frozen hashes; factory digest was used from the frozen INHERITED declaration rather than freshly reading factory bytes in this audit.

403 assertions PASS/0 FAIL cover:

- Strict complete JSON, no duplicate keys/nonfinite constants; exactly four arms x five seeds101/202/303/404/505.
- All20 planned endpoints reached, with90980 objectives,90980 final losses,90980 preclip gradient norms and90980 RNG digests present. Loss/norm numbers finite. Clipping threshold is not an upper bound on the reported preclip norm.
- A's15000 non-null auxiliary losses satisfy0.75 final+0.25 auxiliary within float32 storage rounding (max absolute error3.5762786865234375e-7); other groups have null auxiliary entries and objective=final loss.
- All20 full batch-index and3000-step prefix hashes regenerated from the fixed19977-example domain and seed+12000. Within-seed Parcae initialization digest equality and all-arm shared-IO equality checked from records, not native tensor reconstruction.
-15000 P2/P4/A saved RNG prefix triples agree. P2/P4 also agree through3822 steps per seed. GPT is only seed-matched, not falsely claimed to have identical native RNG consumption.
-35 snapshot reference paths/endpoints and digest formats complete; final model digest matches the final snapshot record. Producer safe_reload PASS is recorded; binaries were not supplied, so auditor file/tensor verification is NOT TESTED.
- Budget/exposure arithmetic and all20 environment records agree with the frozen design. No correctness scores or H1 predictions exist in this training file.

|Arm|Runs|Steps/run|Counted FLOPs/run|Mean saved training seconds (descriptive)|
|---|---:|---:|---:|---:|
|GPT|5|5941|436265975808|84.0930|
|P2|5|5433|436214439936|79.7986|
|P4|5|3822|436208467968|74.7398|
|A|5|3000|436285440000|69.2213|

Total recorded counted work8724871618560; per-run ceiling436285440000; max unused fraction0.00017642585551330797 (0.017643%). This is supported-operator arithmetic, not a new profiler/hardware measurement. Times include this worker's loop/saves; do not turn single-run times or worker-lifetime RSS into accepted hardware efficiency.

Training minibatch losses are not held-out accuracy. A has a mixed objective. Do not rank models, choose checkpoints or adjust thresholds based on these losses before the already fixed H1 evaluation.

## 3. Bounded next action: evaluate existing snapshots only

Keep the existing clean registered worktree at7bcb08f and output:

    /workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1

The new helper finds that existing worktree; checks current training/prepared/review bytes, source identities, all20 endpoints and35 real snapshot file hashes in Codespaces; then invokes the UNCHANGED reviewed parent `run_codespaces_cpu.sh evaluate`. It never invokes prepare/train or manual --worker, does not install dependencies, and preserves existing/partial evaluation results without automatic retry. Missing snapshots or mismatching bytes cause BLOCKED, not retraining.

After the reviewed evaluation completes it rechecks training/source/snapshot identity, H1 file/object digests against the result and deterministic frozen H1 reconstruction, rescores saved predictions and recomputes all separate outcome fields. This is not a second neural inference pass. HC/H2 allocation identities may be checked, but their labels/model evaluation are not generated. Supplemental receipt: evaluation_handoff_integrity.json.

**Claude R02 remains OPEN:** these endpoint checks detect persistent H1 corruption and inconsistent saved scoring, but are NOT per-worker read-time validation and do not prove absence of transient changes. Run single-owner/single evaluation with no concurrent evidence-directory writers. No original evaluation source was patched or source-identity binding bypassed. This is a documented nonblocking LOW limitation, not a hidden fix.

R01: print primary_equal_budget_A4_P4, same_updates_A4_P4, external_GPT_safeguard, intermediate_P2_safeguard and A_extra_depth separately. Evaluate top-level PASS describes execution; its exit_code follows the primary screen, not every safeguard. Preserve scientific FAIL/ceiling BLOCKED even if integrity checks PASS.

R03 remains OPEN for manual duplicate training workers; no such workers are called. Training is complete and is not automatically resumed. R04 late pairing has now been checked from the uploaded complete records. R05 native coverage and R06 statistical/compute/inactive-parameter interpretation limits remain.

Actual new-helper checks: Python3.12-compatible AST PASS;14/14 synthetic metadata/file check tests PASS; includes modified/missing snapshot, changed review/source/preparation, duplicate rows, H1 endpoint/frozen-content/score/outcome mismatch. These use synthetic records, no real H1 labels or models. No original-runtime full evaluation-handoff execution has occurred here. Do not label helper tests as model acceptance or Claude re-approval.

The fixed evaluation will cover40 conditions on the SAME2048 H1 questions;81920 answers are not81920 independent questions. It selects no best checkpoint; P4@3000 is the predeclared same-update comparison, not an adaptive checkpoint. Result path is result.json in the same directory.

## 4. Acceptance and limitations

|Item|Status/evidence|
|---|---|
|Native preparation|PASS, previous owner terminal report|
|Claude pre-training review|APPROVE, actual supplied limited report|
|20 native training trajectories|Completed in uploaded producer records; no independent replay|
|Raw training JSON/record consistency|PASS, actual403-check audit|
|35 binary snapshots|NOT TESTED by this auditor; checked locally before evaluation|
|prepared.json detail/byte audit here|NOT TESTED; remains local to Codespaces|
|H1 quality/primary/safeguards|NOT TESTED|
|Independent native score/profile/resume replay|NOT TESTED|
|Post-result Claude review|NOT TESTED; pre-training approval is not result approval|
|Hardware efficiency|NOT TESTED|
|Formal Oracle|BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False|

Training JSON handoff COMPLETE. Full conversation bundle contains original bytes, actual audit script/results/log, source identity references, supplemental handoff/tests and Chinese report. No same-file reupload, repeated initialization or new generic audit gate.

Keep PR22 Draft/unmerged. Preserve old MECH-AB/C/M2/R1 outcomes and both A-M2L limitations. No upstream/J1/Bench/R3 edits, GPU expansion, G2 REAL, automatic merge or later MES phases. The date is the audit date; no original run timestamp is inferred from filenames.
