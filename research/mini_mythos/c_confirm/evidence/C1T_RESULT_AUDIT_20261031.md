# C1T result audit — fixed C4 confirmation FAIL

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1. This is the audit date, not an inferred native execution timestamp.

## Decision

User-run evaluation is complete in the uploaded records. Actual read-only audit: **317 assertions PASS,0 FAIL;1 inherited source-byte check NOT TESTED**. Independently rebuilt C1T and rescored **40,960 saved full answers on the SAME2,048 questions**, not40,960 independent questions. Primary equal-budget C4-P4 FAIL; same-update C4-P4 FAIL; GPT safeguard FAIL; candidate selection FAIL. Execution PASS/exit1 is a completed negative study, not a process crash.

Close this fixed recipe's bounded confirmation without automatic scaling, retuning, extra seeds or combinations. Preserve old MECH-C developmental outcomes and this negative confirmation separately. No claim that all adapters/recurrent models fail. Post-result Claude Code review is still NOT TESTED/DEFERRED; original code APPROVE does not approve these results.

## Inputs and lineage

- Original result(7).json:10,296,623 bytes; actual SHA256 **55c018b7a62a72aff5ec3dd608e6f56a1fab2733c71b76ef187b6a391ebfd3d2**. No separate terminal result digest supplied, so no external hash comparison or producer-authenticity claim.
- Original training(1).json:7,307,918 bytes; SHA256 **38d21ce4b23c60afd46d1c1b4361f937452215ce20a886539fe5d1bf2eeb04d1**. Every embedded training row and review object equals the prior uploaded original; its byte hash matches training_summary_sha256.
- Original prepared.json:22,745 bytes; SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**, matching the earlier owner terminal. Preparation fields link exactly to the result.
- Execution remains **8a646eb56a9bcffb9767ad9f50843f85670b2fa1**; read-only upstream69284c13746e849104f738d6d1a347b1f457df76. Protocol first06794bebae186470a9a05d728b59b4f42869e6ae. No model/protocol/budget/threshold edits.
- PR23 was read Draft/unmerged at **28d7e4850b26358e215c3ce52fa41f08b28f28d8**, preserving previous391-check training audit. Those earlier checks are not all claimed newly rerun.

## Actual scores

Every cell is complete answers correct out of2048 C1T questions, depth4 only.

|Seed|GPT4843|P4@3000|P4@3116 equal budget|C4@3000|
|---:|---:|---:|---:|---:|
|1101|1990|1669|1649|174|
|1202|1962|1881|1803|1955|
|1303|2020|1841|1914|1756|
|1404|2023|2003|1959|2010|
|1505|2003|1763|1873|1851|
|Mean accuracy|97.63671875%|89.423828125%|89.82421875%|75.64453125%|

|Frozen screen|Mean candidate-reference,pp|Status|
|---|---:|---|
|Primary equal-budget C4-P4|-14.1796875|FAIL|
|Same3000 updates C4-P4|-13.779296875|FAIL|
|External GPT safeguard|-21.9921875|FAIL|
|Candidate selection|Both primary and safeguard required|FAIL|

C4-P4 paired differences,pp: **-72.021484375,+7.421875,-7.71484375,+2.490234375,-1.07421875**. Two improve,three decline; no ceiling block. C4/1101=174/2048=8.49609375%,versus P4=80.517578125%. The outlier strongly affects the mean and must NOT be removed/replaced. It is not the only regression. C4/1101 category counts28,36,46,64 of512;all20 conditions have zero invalid digit outputs. No low-score causal diagnosis is established by the record audit.

C4 worst seed8.49609375%,P4=80.517578125%,GPT=95.80078125%. Do not label C4 robust. P4@3116 improves its mean over predeclared3000 by only0.400390625pp;some individual P4 trajectories regress. No cherry-picking of better checkpoints. The same-update FAIL prevents explaining away the result solely by P4's extra116 updates.

Predeclared5000-draw seed731031 paired crossed bootstrap independently recomputed:95% diagnostic interval **[-43.565185546875,+3.662841796875]pp**. It is wide and crosses zero. Engineering FAIL is clear, but no population-wide statistically significant inferiority/superiority claim is made. Five seeds remain a limitation. No direct ranking of C1 versus MES1 A averages across different seeds/test/budget.

## Budget and costs

Per-arm/seed counted ceiling355663872000;GPT4843/P43116/C43000. Totals355636445184/355632021504/355663872000;max integer slack0.008955224%,within0.1%. Equal supported-operator count is not equal exposure, hardware work or parameters. Registered counts GPT65344/P460224/C462784;known8320 inactive Parcae parameters remain.

Recorded full2048-question generation counters: GPT5179965440,P48053063680,C48367636480. C4 is3.90625% above P4 and61.53846% above GPT. These are counter-record consistency/arithmetic, not a newly executed profiler or hardware speed difference. Under this frozen test/configuration GPT has the highest mean accuracy and lowest generation counter; no universal architecture ranking or hardware-efficiency acceptance.

## Actually executed audit

Auditor Python3.13.5/NumPy2.3.5;stdlib/NumPy only. No Torch/native-model/production-runner import, forward/backward, optimizer, weight loading, training, hardware profiler or new dependencies. Producer records Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU1thread.

Strict whole-input JSON;byte hashes;preparation/source/environment/budget/native-check record linkages;15 exact unique training jobs and planned endpoints;complete finite loss/norm and RNG record formats;stored P4/C4 start/batch-prefix/RNG pairing;20 snapshot reference endpoints/full-base final links. Previous integer-index regeneration was historical,not newly repeated here.

Six retained own code/protocol byte copies match result SHA256 AND freshly retrieved fixed-commit Git blob metadata. Five inherited copies match declared SHA256. Full m2_matched/experiment.py bytes absent from these retained sources and not freshly fetched:one NOT TESTED item. Declared source aggregate750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0 agrees;declarations are not producer authentication.

Independent protocol-based reserved-key allocation reconstructed all legacy exclusion hashes and C1T2048 canonical keys,512 per stratum. No overlap with5120 legacy H1/HC/H2 keys or train/development roles. Only C1T target answers generated. Object hash **c87e4e5566cbf75ad19f2ac0e930bda1228f962c6a3ac2ced4ef75246766564b** and producer-format file hash **7d29402ad50d417cabf4a670eaa22278c6c52e5ed15ac4dd9d05cb79c4503ae5** match result. This is reconstruction,not direct retrieval of original Codespaces C1T.json.

All20 condition keys,40960 saved answer scores/category/invalid counts,checkpoint digest references,three screens,selection,means/worst/sample deviation and bootstrap match. Saved NLL/time checked finite only;NLL not recomputed without logits/weights. Original input bytes unchanged.

## Limits and handoff

Twenty actual .pt files,per-job local records,independent native re-evaluation/training/resume,profiler and hardware performance NOT TESTED here. No separate terminal evaluation receipt supplied;do not infer auxiliary-launcher completion. Claude's pretraining review remains actual but scope-limited;it did not receive prepared.json. New result-level Claude review pending. Claude replaces Grok;no extra Grok gate.

The raw result/training/preparation handoffs are COMPLETE. No reupload or prepare/train/evaluate rerun needed for sealing. Conversation bundle Mythos_C1_C1T_Result_Audit_20261031.zip contains all three raw inputs,actual audit code/log/results,reconstructed C1T,source copies,Chinese report and focused Claude request.

Next bounded instruction: Claude Code reviews existing evidence/interpretations once,especially1101,paired regressions,bootstrap limits and counter-vs-hardware claims. Read-only reconstruction/rescoring allowed;no new native run,source change,threshold adjustment,HC/H2 scoring,commit/push/merge. Stop after report. Do not automatically start D/E,A+C,rank/LR scans or GPU scaling.

Keep PR23 Draft/unmerged. Formal Oracle BLOCKED/NOT_READY,FORMAL_ACCEPTANCE_READY=False. No G2 REAL,upstream/J1/Bench/R3 or old-experiment changes. This stage is a negative candidate selection with preserved evidence,not a universal rejection of the research direction.
