# C1 — uploaded training record audit, 2026-10-31

## Decision

**Uploaded training(1).json contains all 15 completed GPT/P4/C4 runs and 20 snapshot references. Actual read-only audit: 391 assertions PASS, 0 FAIL. C1T is recorded NOT OPENED and candidate quality NOT TESTED.** No native model training, inference, optimizer operation or profiling occurred in this audit. Do not rank models from training losses, repeat training, or alter the frozen criteria.

This completes the training JSON handoff. Next bounded action: run the unchanged, previously reviewed parent `evaluate` phase on the saved snapshots. No new preparation or generic approval cycle is needed.

## Identity and inputs

- Repository leotree2020/OpenMythos, Draft PR23, branch mini-mythos-c1-budget-confirm-cpu-20261031. Live handoff HEAD before these additions: 5fe97f234d0480093ef224e7cd068ffafdc84163.
- Reviewed/executed source: **8a646eb56a9bcffb9767ad9f50843f85670b2fa1**. Upstream remains sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76, unmodified by this audit.
- Actual original training(1).json: **7,307,918 bytes**, SHA256 **38d21ce4b23c60afd46d1c1b4361f937452215ce20a886539fe5d1bf2eeb04d1**, computed from the full uploaded bytes. No separate terminal digest was supplied for this training file; no external identity/authenticity claim.
- Original prepared.json re-read: 22,745 bytes, SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**, matching the previously supplied terminal digest.
- All 15 rows bind source aggregate **750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0** and the preparation's corresponding full/base starting-state and shared-IO records.
- Training records the actual owner-supplied Claude code report plus addendum, owner acknowledgement, and report digest 6dd82c038bd6fe469d7c2795fdc6d90e4c5e472b0b04934645b8e53ddbf66597. The reviewer field explicitly retains prepared file NOT VERIFIED by Claude. Original report bytes/authorship were not independently authenticated in this audit.

## Actually executed checks

Auditor: Python3.13.5, torch2.10.0+cpu. Torch was used ONLY to regenerate integer batch indices. No native model code imported, weights loaded, optimizer invoked, profiler executed, dependency installed or test answers generated.

The 391 checks cover strict complete JSON/duplicate and nonfinite rejection; exact 15 unique jobs; exact endpoints; all recorded environments; initial full/base/shared-IO links; source identity; budget and exposure arithmetic; complete finite nonnegative losses and preclip gradient norms; saved RNG digest formats; snapshot reference paths/endpoints/digest formats; final full/base-state links; and descriptive-resource fields. Source metadata was read live from the pinned GitHub ref, not inferred from history.

All **54,795 loss values, 54,795 gradient-norm values and 54,795 RNG digests** are complete. A recorded preclip norm above 1 is not itself a clipping failure. Losses are minibatch training objectives, not held-out complete-answer accuracy.

All 15 full integer batch-index hashes and 3000-step prefix hashes were independently regenerated using the frozen 19,977-example domain, batch32 and seed+12000. P4 and C4 have identical recorded base initialization and **15,000 matching saved RNG prefix pairs** across five seeds. GPT is seed/sample matched, not asserted to share native RNG consumption.

All 20 snapshot references are present: 15 final endpoints plus five P4@3000. Their producer safe_reload_status is PASS; resume_replay_status remains NOT TESTED. This checks reference consistency, NOT the actual .pt file/tensor bytes. The complete wrapper/model/adapter digest differs from a base-only digest by design; base hashes were compared to base hashes and full hashes to full hashes.

Six retained own source/protocol copies match uploaded SHA256 values and live pinned Git blob IDs. Five inherited file copies match recorded SHA256 values. m2_matched/experiment.py was read at lines1-85 for the tensor-hash convention, but its FULL bytes were not newly SHA256-verified; that limitation remains NOT TESTED. No source identity or runtime guard was bypassed.

## Budget and completion

|Arm|Completed runs|Updates per run|Counted training FLOPs per run|Mean recorded training seconds, descriptive only|
|---|---:|---:|---:|---:|
|GPT|5|4843|355636445184|66.3175|
|P4|5|3116|355632021504|58.6092|
|C4|5|3000|355663872000|62.0771|

Seeds1101/1202/1303/1404/1505. Total54,795 recorded updates and5,334,661,693,440 supported-operator FLOPs. Common per-run ceiling355,663,872,000; maximum unused percentage0.008955224%, within0.1%. Same count is not equal hardware work or equal repeated sample exposure. Single-run times and worker-lifetime RSS are not controlled hardware benchmarks.

## Limits retained

- 20 actual snapshot files, optimizer/RNG contents and local per-worker row.json files were not uploaded. Independent binary identity, model scoring and resume equivalence remain NOT TESTED.
- No C1T quality result, primary screen, GPT safeguard or candidate-selection claim exists yet. No fresh C1T/HC/H2 labels were generated here.
- Claude's pretraining code APPROVE remains valid only in its stated scope. A new result-level review has not happened. Grok is not an additional approval dependency under the owner's updated policy.
- C4 adds2560 registered parameters; known8320 inactive Parcae parameters remain. No capacity-matched or pure phase-specificity causal claim.

## Next action

Keep the existing worktree at8a646eb and output `/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1`.

Supplemental convenience entry [evaluate_after_training_20261031.sh](evaluate_after_training_20261031.sh), first commit **459d20ad3bb41cf704c4392405070b85e957fd7d**, finds that registered worktree, checks prepared/training SHA256 against the received bytes, and invokes ONLY the unchanged `run_codespaces_cpu.sh evaluate`. No fetch of a new model, no prepare/train/manual worker/retry/resume, no source edit or dependency installation. The original parent verifies all15 jobs and20 snapshot file hashes; each worker checks snapshot metadata/full-state hash and hashes/parses one C1T byte buffer. Existing/partial result behavior remains the original read-only/no-retry policy.

The new shell convenience entry is not part of Claude's earlier code review. Its Bash syntax and8 synthetic orchestration tests actually PASS (temporary Git worktree with spaces, missing/changed inputs, pinned selection and return-code preservation). No real production evaluation was run in these tests. The test fixture replaces paths/pins/hashes and uses a mock dispatcher, not native models.

Evaluation will produce20 depth4 conditions on the SAME2048 C1T questions,40960 repeated answers. Keep primary equal-budget C4-P4, same-update comparison, external GPT safeguard and candidate_selection_status separate. Selection requires primary AND GPT safeguard PASS. Exit1 can be a valid scientific failure; exit2 may be instrument BLOCKED or selection/ceiling BLOCKED. Do not alter the predeclared gates.

Keep PR23 Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False. No G2 REAL, GPU expansion, upstream/J1/Bench/R3 or old experiment changes. No automatic later mechanism, model scaling or merge. The full conversation audit package contains original inputs, actually executed audit code/results/logs and the convenience entry/tests.
