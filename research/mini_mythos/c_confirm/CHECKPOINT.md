# C1 checkpoint — Claude code approval received; train-only handoff

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1.

## Current decision

**Native preparation PASS in the owner's CPU run; uploaded preparation bytes verified by ChatGPT. Actual owner-supplied Claude Code review and addendum: APPROVE for the code at8a646eb, six nonblocking INFO findings. Claude did NOT receive or verify prepared.json. Fifteen training trajectories and candidate quality remain NOT TESTED; C1T NOT OPENED.**

These are separate evidence claims. Do not rewrite Claude's limited approval as a full-file audit, attribute ChatGPT's checks to Claude, or say the package was delivered to Claude. Its addendum says only the request arrived. The code approval stands; no new mandatory code change is reported. Next action is the existing reviewed parent train entry with the actual supplied report and explicit owner acknowledgement. Do not rerun prepare or ask for the same JSON to be uploaded here again.

## 1. Git and immutable execution

Repository leotree2020/OpenMythos, Draft PR23, branch mini-mythos-c1-budget-confirm-cpu-20261031. Base PR21 b16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c.

**Keep the successfully prepared worktree at executable/reviewed commit8a646eb56a9bcffb9767ad9f50843f85670b2fa1.** The new commits register a review, a supplemental launcher and this checkpoint; they do not change the six frozen code/protocol files or inherited implementations. Do not checkout a documentation HEAD to run the existing experiment.

- Protocol-first commit06794bebae186470a9a05d728b59b4f42869e6ae.
- Read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
- Previous preparation-audit checkpoint679d9fd1811845568b91f7b30c7d9288642f6d77 preserves the historical139-check audit and its one NOT TESTED factory-byte item.
- Review transcript plus addendum: [evidence/C1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md](evidence/C1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md), first committed89152f19d66b829c4c1aefefb2ac256ad6e5d618.
- Train-only supplemental helper: [evidence/train_after_claude_20261031.py](evidence/train_after_claude_20261031.py), committed1417bc67825b9c1ee8a1d96e110a243f2b0622da, Git blob9cc3d15a2d95d5b4d9a707a2c3de832d72312f88.

The review is transcribed from two owner-pasted messages with explicit provenance. Claude's original scratchpad file, scripts and raw logs have not been fetched. No byte-identical original-report or authenticated-author claim. The actual transcribed report, not a request or fabricated approval, is supplied to the existing training flags.

## 2. Preparation file and current bounded comparison

The original uploaded file is still present and was re-read in this handoff:22,745 bytes; SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**, matching the owner's earlier terminal digest. This shows byte correspondence, not producer authenticity or a model replay.

Source identity aggregate **750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0** was recomputed from the stored own/inherited maps and equals Claude's independent source-derived value. C1T digest **14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0** also matches its reported recomputation. No test labels were generated.

Current standard-library read-only comparison:15 conditions PASS/0 FAIL, covering byte SHA, source aggregate, C1T digest, exact five-seed membership, ceiling/three-arm budget arithmetic, all five recorded count/parameter probes per arm,20 recorded native compatibility cases,5 recorded GPT CE checks, production environment record and untrained/unopened scope. Five retained own source/protocol byte copies were checked against the uploaded digests. These are record comparisons; historical139 checks and native probes are NOT newly rerun.

Recorded production environment:Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU one thread. Output remains `/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1`.

|Arm|Steps|Counted FLOPs/update|Total|
|---|---:|---:|---:|
|GPT|4843|73433088|355636445184|
|P4|3116|114130944|355632021504|
|C4|3000|118554624|355663872000|

Ceiling355663872000; maximum unused0.008955224%,within0.1%. No budget relaxation. Same supported-op count is not equal hardware cost or sample exposure. The prepared file's review_status=PENDING Claude Code is a historical preparation snapshot; leave it unchanged. The later training record separately archives the actual report and acknowledgement.

## 3. Independent review scope and retained INFO items

Claude reports29 fixture tests PASS, source reading and real fixed-model no-update probes for seed1101:zero-adapter equivalence, nonzero adapter gradient routes, GPT split interface, cost/parameter counts, three-iteration RNG pairing, plus4 development prompts on untrained models. It used torch2.11.0+cu130 on CPU and directly invoked components outside the production version gate. This is NOT a fixed production-build reproduction and does not waive the required2.11.0+cpu runtime. The reported tests are not tests newly executed by ChatGPT.

|Finding|Disposition|
|---|---|
|R01 INFO, two kinds of exit2|Read execution status and candidate_selection_status separately; scientific ceiling BLOCKED is not a crash. GPT safeguard failure must remain FAIL.|
|R02 INFO, full batch/snapshot metadata checks split across phases|Keep existing later snapshot metadata checks. Do not claim all full-index hashes already independently replayed or remove evaluation checks.|
|R03 INFO, manual workers can preclaim jobs|Do not call --worker manually. Use the reviewed parent only; preserve any existing/partial jobs.|
|R04 INFO, fixture scope|Keep component tests distinct from actual native diagnostics and training.|
|R05 INFO,8320 inactive parameters|Optimizer membership does not mean every parameter receives a gradient. Retain GPT65344/P451904/C454464 gradient-present probe counts and inactive-path limitation; no repair here.|
|R06 INFO, comparison limits|C4 adds2560 parameters; count/exposure differ;40960 responses are repeated measures on2048 questions;five seeds/four-step horizon/bootstrap diagnostic.|

Claude prepared.json byte/content audit:NOT TESTED because the file never reached its environment. ChatGPT's actual original-file comparison above is separately attributed and cannot be substituted into Claude's report. No additional generic reviewer cycle or extra Grok gate is required by the supplied code approval.

## 4. Bounded next action: training only

Run the supplemental helper at1417bc67825b9c1ee8a1d96e110a243f2b0622da with `--start-training`. Executing it is the owner's acknowledgement of the scope-limited code approval, not a claim of Claude file verification.

It locates an existing registered worktree at8a646eb (do not guess the garbled prior pasted path), checks the actual existing prepared bytes/source maps and local train.json digest, verifies the frozen source files, retrieves the registered report at89152f1 and calls ONLY the unchanged reviewed `run_codespaces_cpu.sh train` with --review-report/--reviewer/--review-approved. The reviewer field explicitly says prepared file NOT VERIFIED by Claude. The original parent archives the report bytes/hash in the output.

The helper refuses prior training.json/train.started/jobs/review/result/test artifacts or training log. It does not delete/reset evidence, retry, resume, manually invoke workers, install dependencies, or call prepare/evaluate. Native runtime and worker source/start/data checks remain intact. Any mismatch is BLOCKED with evidence retained.

New helper checks actually run locally:13/13 standard-library unit tests PASS, including the real uploaded preparation SHA/fields, mutated/truncated input, existing evidence retention, nonstandard worktree paths, changed source/HEAD and mocked parent-train arguments. Python3.12 AST PASS; published blob matches tested bytes. No native models or real training process were executed by these tests. This helper is new orchestration, NOT part of Claude's prior code review; no new review or model acceptance is implied.

Frozen study: GPT/P4/C4 x seeds1101/1202/1303/1404/1505=15 trajectories,20 full snapshots including5 P4@3000. C4 original four rank4 corrections, final-only CE, unchanged optimizer and initialization. C1T2048 questions exclude all5120 MES H1/HC/H2 keys. All15 runs and evidence checks must finish before a separately invoked evaluation; this handoff does not score C1T or open HC/H2.

Training result: `/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1/training.json`. Training PASS is execution/pairing completion, not candidate quality. Subsequent primary C4-P4 mean>=1pp/every loss<=1pp and GPT protection mean/every loss<=1pp remain unchanged; candidate selection needs both. Same-update comparison is separate.

## 5. Stage state and boundaries

|Item|Status|
|---|---|
|Native original-runtime preparation|PASS, owner execution and uploaded records|
|Uploaded original prepared bytes/declared values|PASS, separately checked by ChatGPT|
|Claude code review|APPROVE, actual owner-supplied report+addendum received|
|Claude review of prepared bytes|NOT TESTED, explicitly unavailable to reviewer|
|Native15 training trajectories|NOT TESTED, not launched here|
|C1T candidate quality/hardware efficiency|NOT TESTED|
|C1T/HC/H2 model scoring|NOT OPENED|
|Formal Oracle|BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False|

Claude Code replaces Grok by owner's explicit policy. Keep historical reviewer attribution and disagreements. Keep PR23 Draft/unmerged, upstream and prior experiments unchanged. No G2 REAL, J1/Bench/R3 edits, GPU expansion, new mechanisms, threshold repair or automatic merge. No direct access to the owner's Codespaces or background training is claimed. End this handoff with the executable train command, not another preparation request.
