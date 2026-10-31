# C1 checkpoint — C1T audited; fixed C4 candidate selection FAIL

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1.

## Current decision

**Uploaded result(7).json contains completed15-run/20-condition C1T evaluation. Actual read-only audit:317 assertions PASS,0 FAIL,1 inherited source-byte item NOT TESTED. Independently reconstructed C1T and rescored40,960 saved answers on the SAME2,048 questions. Equal-budget primary FAIL,same-update comparison FAIL,GPT safeguard FAIL,candidate selection FAIL. Execution PASS/exit1 is a valid negative study,not a crash.**

End this bounded fixed-C4 confirmation. Preserve evidence and implementation;do not automatically scale,combine,retune,replace/remove seeds or open further holdouts. The original result handoff is COMPLETE:no prepare/train/evaluate rerun or same-file reupload needed. Current evidence does not select this recipe for Mythos. This is not rejection of every adapter or recurrent model.

Next single action:one focused Claude Code post-result review of existing evidence and interpretations. Prior code APPROVE is not result approval. No new model execution is authorized by this result audit.

## 1. Git and immutable history

Repository leotree2020/OpenMythos;Draft PR23;branch mini-mythos-c1-budget-confirm-cpu-20261031;base PR21 atb16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c.

**Reviewed/executed code stays8a646eb56a9bcffb9767ad9f50843f85670b2fa1.** Keep the existing worktree at that pin;new audit/checkpoint documents do not modify runtime,protocol,optimizer,thresholds or original C adapters. Pinned upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains read-only. Protocol first06794bebae186470a9a05d728b59b4f42869e6ae.

Previous checkpoint28d7e4850b26358e215c3ce52fa41f08b28f28d8 preserves the391-check training audit and evaluation handoff. Those checks are historical,not all newly executed. Earlier prepare/review history remains at679d9fd1811845568b91f7b30c7d9288642f6d77 and5fe97f234d0480093ef224e7cd068ffafdc84163.

Actual new audit: [evidence/C1T_RESULT_AUDIT_20261031.md](evidence/C1T_RESULT_AUDIT_20261031.md),first commit **7cc484ddfe3eefdc3b67befc96298e2ac5ebb855**. Read it for full assertions,limits and route decision.

Claude Code replaces Grok by owner's policy. Existing owner-supplied C1 report/addendum registered89152f19d66b829c4c1aefefb2ac256ad6e5d618 approved code only;Claude did not receive prepared.json. Do not reattribute ChatGPT file checks to Claude or call the pretraining report a result audit. Actual result-level Claude review remains NOT TESTED/DEFERRED. No additional Grok gate.

## 2. New evidence and actual audit

- result(7).json:10,296,623 bytes;actual SHA256 **55c018b7a62a72aff5ec3dd608e6f56a1fab2733c71b76ef187b6a391ebfd3d2**. No separate terminal result hash supplied,no external authenticity claim.
- training(1).json:7,307,918 bytes;SHA256 **38d21ce4b23c60afd46d1c1b4361f937452215ce20a886539fe5d1bf2eeb04d1**. Full embedded training rows and review match this original upload exactly;training_summary_sha256 matches its bytes.
- prepared.json:22,745 bytes;SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**,matching the earlier owner terminal. Its source/environment/counts/budget/native-check/holdout records link exactly to result.

Producer records Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU1thread. Actual auditor Python3.13.5/NumPy2.3.5,stdlib+NumPy only;no Torch/model/production-runner import,weight load,forward/backward,optimizer,profiler or dependency install.

Actual317 checks cover strict whole JSON/byte hashes,source aggregate,15 exact jobs/endpoints,finite loss/norm and RNG record formats,start/prefix pairing,20 snapshot-reference links,independent C1T reconstruction,all20 saved-condition scores,three screens/selection/descriptive statistics and5000-draw bootstrap. Source aggregate750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0 matches.

Six retained own source/protocol copies match result SHA256 and live pinned Git blob metadata;five inherited copies match SHA256. Full m2_matched/experiment.py bytes were not retained/freshly fetched in this audit:one NOT TESTED item,not a fabricated source-byte PASS. Previous integer batch regeneration/native probes were not rerun.

C1T2048 canonical pairs,512/stratum,excludes5120 MES H1/HC/H2 keys and all train/development roles. Allocation digest14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0 matches. Object SHA **c87e4e5566cbf75ad19f2ac0e930bda1228f962c6a3ac2ced4ef75246766564b** and reconstructed producer-format SHA **7d29402ad50d417cabf4a670eaa22278c6c52e5ed15ac4dd9d05cb79c4503ae5** match recorded values. This is deterministic reconstruction,not retrieval of original Codespaces test bytes. Only C1T answers generated;HC/H2 labels and model evaluation not opened.

## 3. Results that determine the route

All counts out of2048;depth4 only.

|Seed|GPT4843|P4@3000|P4@3116|C4@3000|
|---:|---:|---:|---:|---:|
|1101|1990|1669|1649|174|
|1202|1962|1881|1803|1955|
|1303|2020|1841|1914|1756|
|1404|2023|2003|1959|2010|
|1505|2003|1763|1873|1851|
|Mean accuracy|97.63671875%|89.423828125%|89.82421875%|75.64453125%|

Primary C4-P4 mean **-14.1796875pp**,paired **-72.021484375,+7.421875,-7.71484375,+2.490234375,-1.07421875pp**. Two improvements and three regressions,no ceiling block. Same-update mean **-13.779296875pp**;GPT protection mean **-21.9921875pp**. All three FAIL;selection FAIL follows frozen requirement for BOTH primary and GPT protection PASS. No threshold changed.

C4 seed1101=8.49609375% strongly affects the mean;do not delete/replace it. Other seeds are also mixed. Its answers are syntactically valid digits,not missing predictions. Low-score root cause remains unlocated:do not infer rank/LR/architecture/inactive-parameter causes without evidence. Finite traces are not proof of implementation correctness.

P4's additional116 updates raise its mean only0.400390625pp and hurt some seeds;retain both predeclared endpoints,no best-checkpoint selection. Same-update failure means the result cannot be explained solely by P4's extra updates.

Predeclared paired crossed bootstrap:5000 draws,seed731031;95% diagnostic interval **[-43.565185546875,+3.662841796875]pp**,recomputed. Wide/crosses zero;no statistical population inferiority claim. Engineering FAIL remains. Do not rank A and C by means from separate seeds/tests/budgets or pool old developmental data to recover PASS.

## 4. Costs and limits

Frozen ceiling355663872000 supported-op FLOPs per arm/seed. GPT4843/P43116/C43000;allocated355636445184/355632021504/355663872000;max slack0.008955224%. Equal count is not equal sample exposure,parameters or hardware work. C4 adds2560 parameters;8320 inactive Parcae parameters remain.

Recorded full2048-question generation counters GPT5179965440,P48053063680,C48367636480. C4+3.90625% versus P4,+61.53846% versus GPT. Counter consistency/arithmetic only,not newly measured hardware speed. No efficiency victory claimed.

Twenty new .pt binary contents,local job rows,original C1T file read-time history,independent native score/NLL/profiler/training/resume replay and hardware efficiency remain NOT TESTED here. No separate terminal/helper receipt was supplied;do not claim full supplemental-entry completion. NLL/time checked finite only. Native evaluation is producer-reported with saved predictions,not independently rerun.

## 5. Checkpoint and next bounded instruction

|Item|Status|
|---|---|
|15 native training/20 C1T conditions|Complete in user-run uploaded records|
|Actual saved-record/answer audit|317 PASS,0 FAIL,1 inherited byte item NOT TESTED|
|Equal-budget C4-P4|FAIL|
|Same-update C4-P4|FAIL|
|GPT safeguard and candidate selection|FAIL|
|Claude result-level review|NOT TESTED/DEFERRED|
|Binary/native replay/hardware efficiency|NOT TESTED by this auditor|
|C1T|Viewed;not fresh after tuning|
|HC/H2|NOT OPENED|
|Formal Oracle|BLOCKED/NOT_READY;FORMAL_ACCEPTANCE_READY=False|

Next instruction:send existing result/training/preparation bytes and audit to Claude Code for one focused read-only review of scoring/decisions,seed1101 and uncertainty/cost interpretation. No prepare/train/evaluate/new model run,parameter changes,HC/H2 scoring,commit/push/merge. Code APPROVE cannot substitute for this result review.

Conversation bundle Mythos_C1_C1T_Result_Audit_20261031.zip includes the original three inputs,actual audit script/log/results,reconstructed C1T,reference sources,Chinese report and review request. Raw handoffs COMPLETE;no same-file reupload/retraining required.

Keep PR23 Draft/unmerged;preserve old MECH-C and MES-1 conclusions. No automatic D/E,A+C,rank/LR/seed search,GPU expansion,G2 REAL,upstream/J1/Bench/R3/old-protocol edits or merge. Negative confirmation changes candidate priority,not the long-term Mythos goal.
