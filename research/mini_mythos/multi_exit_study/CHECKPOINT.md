# MES-1 checkpoint — H1 results audited; current A advantage NOT confirmed (2026-10-31)

## Current decision

**All20 user-run training trajectories and40 H1 evaluation conditions are complete in uploaded records. This session actually rescored81,920 saved answers on the same2,048 questions:353 record assertions PASS/0 failures. Primary equal-budget A4-P4 FAIL; same-update comparison FAIL; GPT safeguard FAIL; dedicated-P2 safeguard FAIL. A's own within-four-step depth benefit PASS.** Execution PASS is not quality PASS; exit1 is the valid primary negative result, not a process crash.

Close this frozen MES-1 run and both raw JSON handoffs. Do not ask for the same files again, repeat prepare/train/evaluate, tune thresholds or pick a better checkpoint. Current A0.25/0.75 is a retained multi-exit behavior candidate without confirmed competitive advantage; do not automatically promote it to scaling, MES-2 subtraction or MES-3 adaptive exit. This conclusion does not reject every possible multi-exit or recurrent architecture.

Next single action: focused Claude Code post-result cross-review of existing evidence and interpretations; see section6. No new model execution authorized by this audit.

## 0. Reviewer policy

Effective2026-10-31 the owner replaced Grok's independent-review role with **Claude Code**. ChatGPT and Claude Code cross-review; disagreements remain documented and resolved by evidence or minimal controlled experiments. No extra Grok approval gate. Historical attribution remains; unperformed Grok assignments are superseded, not PASS.

Claude's supplied pre-training report APPROVE is limited to reviewed code/readiness, not these new results. Original report registration80c35f7321039f8351a13f56375413408f14407d and [evidence/MES1_CLAUDE_REVIEW_20261031.md](evidence/MES1_CLAUDE_REVIEW_20261031.md). New post-result Claude review remains NOT TESTED/DEFERRED.

## 1. Git and evidence lineage

- Repository leotree2020/OpenMythos; Draft PR22; branch mini-mythos-mes1-budget-holdout-cpu-20261031; base4cf60b053c7b9c2e89e64646cd986d33a34a7657.
- Reviewed/executed source stays **7bcb08f480d0bda2dba5b1351442190001492782**. Do not checkout a documentation HEAD in the prepared worktree.
- Protocol first committed c74728c3efb6f27e29aacf146d719e37c5dbbd1c; pinned read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. No source/optimizer/data/threshold changes to obtain a result.
- Previous training-audit checkpoint **df07985774fd4c4d9f2cdcdc782c94337617e603** preserves full previous history and403-check training audit. This session does not claim those earlier checks newly rerun.
- New H1 audit [evidence/H1_RESULT_AUDIT_20261031.md](evidence/H1_RESULT_AUDIT_20261031.md), first committed **ea1ce9e2dc4b9758ec6f30b798c24b271114d449**.
- Supplemental evaluation helper remains at eab4d676f3d95beb867f8e468008bfda2c6fb09f; its actual integrity receipt was not uploaded, so helper completion is NOT independently verified here.

Original a8f329ed prepare BLOCKED by the GPT labels/logits integration bug remains in history; fixed7bcb08f prepare reported PASS for all5 seeds. No incident was relabelled. Existing evidence directory remains `/workspaces/OpenMythos/mythos_evidence/mes1_v1_gptfix1`; old mes1_v1 failure output preserved.

## 2. Actual new input audit

Uploaded `result(6).json`: **22,217,437 bytes**, independently computed SHA256 **29ec484bf7e35e1d421ae4f12555f76e1eafc87e16eebf85f55553980730df1d**. No separate terminal result digest supplied; no external identity/authenticity claim. Original bytes unchanged.

Previous `training.json` is still available:16,257,800 bytes, SHA256 **318b0cfbca08f5c33f36b7514300186e63e3a404c8ee1aac7e1177e4de021f69**. Re-read and matched to result.training_summary_sha256. Every embedded training_row and review record is exactly equal to the previously uploaded file, not a new training replay.

Auditor Python3.13.5/NumPy2.3.5. No Torch/native-model import, tensor loading, model inference/backprop, optimizer, profiler, GPU or new dependencies. Six source/protocol copies matched their SHA256 records and live pinned Git blobs; four inherited source copies byte-checked. Factory bytes not freshly reconstructed: only frozen declaration and historical training link checked.

Independent protocol-based allocation rebuilt H1/HC/H2 keys; canonical keys mutually disjoint and all reserved, outside train/development roles. Only H1 targets generated. H1 has512 questions per outgoing-carry stratum. Its object SHA256 **f4e45835c2a9b38c2d5e0537f65996f006d26a7b0b837307858649fb3aa08328** and producer-format serialized SHA256 **a7d878a5f35104581d7f9f5ec13887578e5ee031d72458b44d73f23a56561d03** both match recorded digests. This is deterministic reconstruction, not reading original H1 bytes from Codespaces.

40 exact seed/arm/checkpoint/depth keys;81,920 saved full answers rescored, all totals/category accuracies/invalid counts match. Recomputed five gates, correction/corruption, means/worst scores/stddev and the fixed5000-draw paired crossed bootstrap. Probe/count/parameter records checked for completeness/arithmetic only. Saved NLL/timing checked for finite values, NOT recomputed from logits/hardware.353 assertions PASS/0 failures.

## 3. Actual results and acceptance

|Seed|GPT@4 budget end|P2@2 budget end|P4@4 budget end|A@2|A@4|
|---:|---:|---:|---:|---:|---:|
|101|2039/2048|2018/2048|2011/2048|1957/2048|2013/2048|
|202|2033/2048|2028/2048|1968/2048|1859/2048|1931/2048|
|303|2037/2048|1898/2048|1978/2048|1644/2048|1772/2048|
|404|2037/2048|2043/2048|1969/2048|1706/2048|1832/2048|
|505|2016/2048|1841/2048|2030/2048|1904/2048|1940/2048|
|Mean accuracy|99.23828125%|95.9765625%|97.2265625%|88.57421875%|92.65625%|

|Frozen gate|Mean candidate-reference delta|Status|
|---|---:|---|
|Primary equal-count budget A4-P4|-4.5703125pp|FAIL|
|Same3000 updates A4-P4|+0.517578125pp|FAIL|
|A4-GPT quality safeguard|-6.58203125pp|FAIL|
|A2-dedicated P2 quality safeguard|-7.40234375pp|FAIL|
|A4-A2 trained-horizon depth|+4.08203125pp|PASS|

Primary is NOT ceiling-blocked. Four of five A4-P4 pairs decline: +0.09765625,-1.806640625,-10.05859375,-6.689453125,-4.39453125pp. Original engineering rules unchanged. A worst final seed86.5234375% vs P4 96.09375%; no new stability advantage.

P4@3000 mean92.138671875%; A3000 mean92.65625% with27.42248062% more counted training work per update. P4's originally fixed budget endpoint3822 raises its own mean by5.087890625pp. Thus neither the equal-update gain nor equal-budget advantage confirms the previous optimistic three-seed signal. Do not silently pool old development data with new H1 to recover a PASS.

A two-to-four gains all positive;626 wrong responses corrected,208 correct responses corrupted, net418 across five seed-answer sets. A d2 is better than P4's unsupervised early d2 readout44.08203125%, but worse than dedicated P2. All A trained4, so this is within-trained-horizon improvement, not unseen-depth extrapolation, ACT or a general reasoning proof.

Predeclared diagnostic paired crossed bootstrap primary95% interval about[-7.920166,-1.474609]pp, recomputed exactly to floating tolerance. Five seeds; no automatic statistical superiority/noninferiority claim.

## 4. Budget and compute interpretation

Four arms use common counted ceiling436285440000 per seed. Frozen steps GPT5941/P2=5433/P4=3822/A3000 remain. Maximum integer slack0.017643% within0.1%. Cheaper arms see more repeated training samples; not equal token exposure or hardware work.

Full2048-question answer generation: GPT5179965440 counted FLOPs; Parcae d2=5667553280; Parcae d4=8053063680. A2 is+9.412955% relative to GPT; A4+55.465587%. A4 costs42.090657% more than A2. Under this task/configuration/counter, GPT has highest mean accuracy and lowest generation count. This does not establish universal architecture or repeated hardware benchmark superiority.

Inactive-parameter confounder A-M2L-01 and separate historical reviewer init mismatch remain open; they do not license removing valid within-Parcae negative comparisons. No current A efficiency claim. Hardware efficiency still NOT TESTED.

## 5. Remaining limits, not hidden successes

35 new binary snapshots, original prepared.json and evaluation_handoff_integrity.json were NOT uploaded. No independent verification of actual weight/optimizer/RNG bytes, helper completion, native scoring, training/resume equivalence or profiler measurements occurred here.

R01: status PASS is execution; primary exit1 and all independent gates must be read separately. R02: absent per-worker read-time H1 digest remains OPEN/LOW; endpoint reconstruction and saved-score agreement cannot rule out transient changes. R03: manual duplicate-worker issue remains unchanged; no worker or retry invoked in this audit. R04 pairing is recorded/linked from completed training, not native replay. Other prior limits retained.

H1 is now viewed. HC/H2 labels/model evaluation were not opened by this audit and remain recorded NOT OPENED. New result-level Claude review NOT TESTED/DEFERRED; original pretraining APPROVE remains valid only in its scope. Raw JSON handoff COMPLETE, do not ask to upload it again.

## 6. Next bounded instruction and route decision

Send the existing H1 result, training link, frozen source/protocol and this audit to Claude Code for ONE targeted result review: independently re-score existing predictions, distinguish same-update/equal-budget/GPT/P2 comparisons, retain primary failures and the narrower A depth signal, inspect uncertainty and remaining integrity limits. No prepare/train/model re-evaluation, source edits, threshold changes, HC/H2 opening, commit/push/merge. Report actual scope and evidence; no repeated project-wide initializer audit.

After cross-review, decide which independently justified mechanism/task to prioritize. Current A recipe is not selected for automatic scaling, adaptive exit, subtraction or parameter search. Do not rescue it by silently changing thresholds or treating now-viewed H1 as fresh after tuning. Keep valid negative evidence and reusable implementation.

Deliverables in conversation bundle `Mythos_MES1_H1_Result_Audit_20261031.zip`: byte-preserved input JSONs; actual audit script/log/results; re-created H1; reference source bytes; Chinese report and focused Claude request. No model weights and no claim that a request is a completed review.

Keep PR22 Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False. No G2 REAL, GPU expansion, upstream/J1/Bench/R3 changes, automatic merges or later MES stages. The date is this audit date, not an inferred original run timestamp.
