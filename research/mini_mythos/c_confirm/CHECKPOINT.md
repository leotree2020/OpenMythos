# C1 checkpoint — training records complete; C1T evaluation next

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1.

## Current decision

**The owner uploaded complete training(1).json:15 completed GPT/P4/C4 trajectories,54,795 recorded updates and20 snapshot references. This session's actual read-only audit passed391 assertions with0 failures. C1T is recorded NOT OPENED; candidate quality and hardware efficiency remain NOT TESTED.** No native model, optimizer, profiler or C1T evaluation was executed in this audit.

Training JSON handoff is COMPLETE. Do not request the same file again or rerun prepare/train. Next single action is the existing reviewed parent `evaluate` phase on saved weights. Do not rank models using training loss or change seeds, budgets, checkpoints or thresholds.

## 1. Git and lineage

Repository leotree2020/OpenMythos; Draft PR23; branch mini-mythos-c1-budget-confirm-cpu-20261031; base PR21 b16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c.

**Keep the prepared/trained worktree at reviewed execution pin8a646eb56a9bcffb9767ad9f50843f85670b2fa1.** New evidence/checkpoint/helper commits do not modify the frozen six source/protocol files. Do not move that worktree to documentation HEAD. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains unchanged/read-only. Protocol first committed06794bebae186470a9a05d728b59b4f42869e6ae.

- Previous handoff checkpoint5fe97f234d0480093ef224e7cd068ffafdc84163 preserves preparation audit, reviewer access limits and the training launcher.
- Actual owner-supplied Claude code review plus addendum registered at89152f19d66b829c4c1aefefb2ac256ad6e5d618 in evidence/C1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md. Source approval is NOT model quality approval. Claude did not receive prepared.json; keep that NOT TESTED for Claude, separately from ChatGPT's uploaded-file audit.
- New full training-record audit: [evidence/TRAINING_RESULT_AUDIT_20261031.md](evidence/TRAINING_RESULT_AUDIT_20261031.md), first commit28e4a0b86bcb95228e19b15a01baa9509484ccc0.
- New convenience entry: [evidence/evaluate_after_training_20261031.sh](evidence/evaluate_after_training_20261031.sh), first commit459d20ad3bb41cf704c4392405070b85e957fd7d. It calls the unchanged parent evaluate phase only.

Historical MECH-C developmental PASSs, weak seeds/S16 regressions, MES-1 A competitive FAILs and all earlier evidence remain unchanged.

## 2. Actual uploaded inputs and evidence identity

Training(1).json is **7,307,918 bytes**, actual SHA256 **38d21ce4b23c60afd46d1c1b4361f937452215ce20a886539fe5d1bf2eeb04d1**. No separate terminal hash for this file was supplied; no external authentication claim. Full original bytes preserved.

Original prepared.json is still available and was re-read:22,745 bytes, SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**, matching the owner's previous terminal report. Source aggregate **750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0** matches all15 rows, review binding and the recomputed preparation maps.

The training review record explicitly says Claude Code owner-supplied C1 report+addendum, prepared file NOT VERIFIED by Claude, owner_acknowledged_approval=true. Recorded report digest6dd82c038bd6fe469d7c2795fdc6d90e4c5e472b0b04934645b8e53ddbf66597. Its original scratchpad bytes/scripts/logs and authorship were not newly authenticated here. No substitution of a review request or invented approval.

Producer records consistently declare Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU one thread. Auditor used Python3.13.5/torch2.10.0+cpu; Torch was ONLY used to regenerate integer batch indices, not to run native model code or relax the production requirement.

## 3. Actual audit scope and completion

391 record assertions PASS/0 FAIL. Exact15 unique arms/seeds, exact planned endpoints, complete finite nonnegative54,795 losses and54,795 preclip gradient norms,54,795 syntactically valid RNG digests. A preclip norm above1 is not itself a clipping failure.

All15 full batch-index hashes and3000-step prefix hashes independently regenerated from domain19977,batch32,seed+12000. Same-seed P4/C4 base starts match; all arms' shared-IO records match.15,000 saved P4/C4 RNG prefix pairs match through3000 updates. GPT is sample/seed paired, not falsely claimed identical native RNG consumption. Each full/base start is linked to its corresponding preparation record.

20 snapshot references have exact expected paths/steps/digest formats and final full/base-state links:15 endpoints plus5 P4@3000. Producer safe_reload_status PASS and resume_replay_status NOT TESTED retained. Actual .pt bytes/contents were not uploaded and were NOT independently loaded here. Local per-job row.json files are also not in this upload; the existing evaluator checks them.

Six own source/protocol copies match uploaded SHA256 and live pinned Git blobs. Five inherited copies match recorded SHA256. Factory m2_matched/experiment.py lines1-85 were read for the tensor-hash convention; its full bytes were not newly SHA256-verified. No fabricated closure of that limited byte-verification item. Source identity checks remain active in the native runner.

|Arm|Completed runs|Steps per run|Counted FLOPs per run|Mean recorded training seconds, descriptive|
|---|---:|---:|---:|---:|
|GPT|5|4843|355636445184|66.3175|
|P4|5|3116|355632021504|58.6092|
|C4|5|3000|355663872000|62.0771|

Seeds1101/1202/1303/1404/1505. Total54,795 updates and5,334,661,693,440 counted FLOPs. Per-run ceiling355,663,872,000. Maximum unused percentage0.008955224%,within0.1%. Supported-op count is not equal hardware cost or equal exposure. Descriptive times/RSS are not controlled efficiency benchmarks. No model choice or checkpoint selection from minibatch losses.

## 4. Next bounded action: score existing snapshots

Output remains `/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1`. Preserve original preparation and training files and all jobs.

Run the supplemental shell entry at459d20ad3bb41cf704c4392405070b85e957fd7d. It discovers an existing registered8a646eb worktree, checks the local prepared/training byte hashes against received evidence and calls ONLY the original `run_codespaces_cpu.sh evaluate`. It does not create/reset worktrees, edit sources, install dependencies, invoke prepare/train/manual --worker, retry or resume.

Original evaluator remains responsible for the full15-run barrier, per-worker row equality,20 actual snapshot file hashes, metadata and full wrapper/model/adapter identity. Each evaluation worker hashes and parses the SAME C1T byte buffer. C1T has2048 questions excluding all5120 MES H1/HC/H2 keys.20 depth4 conditions yield40960 repeated answers on the same2048 questions, not independent question sets. HC/H2 remain unscored. Output will be result.json, not a new training file.

The new shell convenience entry is outside Claude's reviewed source, not newly independently approved. Actual Bash syntax and8 synthetic orchestration tests PASS; temporary Git repository/mock dispatcher only, no native evaluation. Published helper Git blob a2756b6b7f6822a0dc90f6242decfeb5b6b7a1e9 and SHA256112bbb3aff1c20c0c8e2ed4bf7574e1433b8eb09b298380bb55493040bbe1d2e match the tested copy. Native runtime/source guards are not bypassed. Existing/partial results retain original read-only/no-retry behavior.

No extra preparation or pre-evaluation generic approval cycle. Actual post-result Claude review remains necessary before promoting any candidate, not before merely executing the already-reviewed fixed evaluation.

## 5. Frozen decisions and remaining limits

Primary equal-budget C4-P4:mean gain>=1pp and every seed loss<=1pp;reference mean>99% gives ceiling BLOCKED. External GPT safeguard:mean and every seed loss<=1pp. Candidate selection needs BOTH PASS;FAIL in either dominates BLOCKED. Same-update P4@3000 comparison remains separate. Execution PASS is not candidate PASS;exit1 may be scientific failure,exit2 may be instrument or scientific ceiling BLOCKED.

C4 remains original four rank4 corrections,scale1,final-only CE,unchanged optimizer/initialization. Adds2560 registered parameters; known8320 inactive Parcae parameters retained. No parameter-matched causal identification, all-parameters-gradient claim, statistical superiority or hardware benefit. No A/B/D/E combination,LR/rank/depth sweep or added seed selection.

|Item|Current status|
|---|---|
|Native preparation|PASS, earlier owner execution/uploaded records|
|Claude code review|APPROVE, supplied limited report; no new result review|
|15 training runs|Complete in uploaded producer records; no independent native replay|
|Actual complete training JSON/record audit|PASS,391 checks|
|20 binary snapshots/local job files|NOT TESTED by this auditor; existing evaluator checks them locally|
|C1T quality/primary/GPT safeguard/selection|NOT TESTED|
|C1T/HC/H2 model scoring|NOT OPENED in this handoff|
|Native replay/resume/hardware efficiency|NOT TESTED|
|Formal Oracle|BLOCKED/NOT_READY;FORMAL_ACCEPTANCE_READY=False|

Claude Code replaces Grok under explicit owner policy; no additional Grok gate. Keep PR23 Draft/unmerged and all historical attribution. No G2 REAL,GPU expansion,upstream/J1/Bench/R3/old-experiment changes,automatic merge or later mechanisms. No direct access to the owner's Codespaces or background execution is claimed. Training upload is complete; next requested handoff is only new result.json and terminal evaluation summary.
