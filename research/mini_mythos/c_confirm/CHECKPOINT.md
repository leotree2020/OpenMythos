# C1 checkpoint — native prepare received and record audit complete

2026-10-31. Experiment MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1.

## Current decision

**User-run native CPU preparation PASS. Original uploaded prepared.json byte identity and bounded record audit PASS:139 checks passed,0 failed,1 source-file byte check NOT TESTED. Fifteen native training trajectories remain NOT TESTED; C1T remains NOT OPENED; the actual C1 Claude Code pre-training review remains PENDING.** No preparation, model forward/backward, optimizer, profiler or training was rerun in this audit.

Do not rerun prepare, request the same JSON again, create a replacement worktree, or infer a quality result. Next action is ONE focused Claude Code review of the fixed C1 code plus the now-available original preparation file. The old MES APPROVE is not C1 approval. Grok's former role is superseded by the owner's Claude Code policy, not an additional gate.

## 1. Git, history and execution pin

Repository leotree2020/OpenMythos; Draft PR23; branch mini-mythos-c1-budget-confirm-cpu-20261031. The live branch was read at92d61d857c7cedae500cd6e147618815112e7880 before this documentation update. Base is PR21 atb16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c.

**Execution/review pin remains8a646eb56a9bcffb9767ad9f50843f85670b2fa1.** Do not switch the successfully prepared worktree to a later documentation commit. Source/protocol, C4 recipe, optimizer, budgets and criteria are unchanged.

Protocol first commit06794bebae186470a9a05d728b59b4f42869e6ae. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains read-only. Inherited C adapter SHA2567696f81ac867e030b4d894c44e2fad176a79ec407e1919cf284f5fdb130b9101.

Full prior implementation/development checks remain in this checkpoint at92d61d857c7cedae500cd6e147618815112e7880 and the development archive. Historical29 component tests,20 launcher cases and toy pipeline are not claimed as newly executed here. Old MECH-C exploratory results and MES-1 negative confirmation remain unchanged.

## 2. Actual uploaded preparation

Original file prepared.json: **22,745 bytes**. Independently computed SHA256 **2f3e1251eaf474d3a49f2de826b6ba6c9711a16a15a9d74c09f8386b5db85829**, exactly matching the owner's supplied terminal digest. This establishes correspondence of those bytes, not independent authenticity of every producer claim.

Original output /workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1/prepared.json. The pasted shell echo has duplicated/garbled lines; do not infer the actual worktree path from it, delete existing directories or rerun preparation to tidy the echo.

Producer declares Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU,one thread. Seeds1101/1202/1303/1404/1505. Recorded code/upstream pins match. native_compatibility_status PASS,training_status NOT TESTED,C1T_status NOT OPENED,review_status PENDING Claude Code. Scope explicitly excludes optimizer updates and C1T answer materialization/model scoring.

Twenty distinct native compatibility cases cover5 seeds x P4/C4 x lengths6/9 at depth4. All report PASS and max_base_gradient_abs_error0. Five native GPT masked-CE records report PASS/error0. These are actual producer records read by this auditor, NOT independent numerical re-execution.

|Arm|Steps|Counted FLOPs/update|Allocated counted total|Unused fraction|
|---|---:|---:|---:|---:|
|GPT|4843|73433088|355636445184|0.00007711442786069652|
|P4|3116|114130944|355632021504|0.00008955223880597016|
|C4|3000|118554624|355663872000|0|

Common ceiling355663872000. Recomputed largest unused percentage0.008955224%,within0.1%. No budget relaxation. Supported-op counts are not hardware work or equal sample exposure.

All15 parameter/count records are complete and agree across seeds. Registered parameters GPT65344/P460224/C462784. Gradient-present probe counts65344/51904/54464 do not mean every gradient is nonzero or that effective capacities match. Known8320 inactive Parcae parameters remain a limitation. Corresponding P4/C4 base-state digests and all-arm shared-IO records match; raw initial tensor bytes were not supplied.

## 3. What this audit actually did

Read and strictly parsed the COMPLETE uploaded JSON; independently computed its byte SHA; rejected duplicate/nonfinite JSON; checked exact seeds/arms/cases/objectives/count arithmetic/budget and start-record pairing. Recomputed source_identity aggregate750d827c88244dfd4d26dc2be6d2fedf88868c399665c882110fbbde9c86a4e0.

Six own code/protocol byte copies in the retained development ZIP match both uploaded SHA256 records and live Git blob metadata at8a646eb. Five inherited source byte copies match recorded SHA256. The sixth inherited file,m2_matched/experiment.py,is absent from that retained archive and was NOT freshly fetched/byte-verified in this audit; its declaration remains bound,not represented as newly verified.

Independently rebuilt reserved KEY/stratum allocation using standard-library hashing only,without generating holdout answers: C1T2048 canonical pairs,512/stratum; excludes all5120 legacy H1/HC/H2 keys and has no train/development-role keys. C1T digest14003d130a3257e5c26d669fe79f6c7b6bed3bf8ce87c1f7c9096605fec595d0 and all three legacy digests match. Training/development metadata hashes were compared to frozen values,not represented as fresh raw train.json byte verification.

Actual audit:139 PASS,0 FAIL,1 NOT TESTED(factory bytes). Standard-library only; no Torch/model import,native probes,optimization,weight loading,hardware profiling or test-label generation. Original initial tensors,local train.json,pip-freeze.txt and full Codespaces filesystem were not supplied or independently inspected. This audit does not authenticate the producer or substitute for Claude review.

Conversation handoff includes original prepared.json,audit_prepared.py,audit_result.json,audit.log,a concise Chinese report,updated Claude instructions and the previous development ZIP needed to reproduce the record audit. This is not another model experiment.

## 4. Frozen experiment remains unchanged

GPT/P4/C4 x5 new seeds=15 trajectories. C4 reuses four independent rank4 projection corrections with scale1,final-only CE,all backbone/adapter parameters in optimizer and full snapshots. No A/B/D/E combination,inactive-path fix,rank/lr/depth scan or eight-step extrapolation.

Equal counted ceiling and steps above. Save all15 endpoints plus5 P4@3000 snapshots=20 complete states;20 depth4-only evaluations on the SAME2048 C1T questions after the full15-run barrier. Not a parameter-matched or pure depth-specificity causal comparison. Old S16 results remain historical,not a new control.

Primary C4-P4 mean gain>=1pp and every seed loss<=1pp;reference mean>99% yields ceiling BLOCKED. GPT protection requires mean/every paired loss<=1pp. Candidate selection needs BOTH primary and GPT protection PASS. Same-update result is separate and cannot rescue primary failure. Five-seed bootstrap is diagnostic,not automatic statistical acceptance.

C1T is not scored. MES H1 was previously viewed; HC/H2 remain reserved/unscored. All fresh-test and cost limitations remain.

## 5. Next bounded action and stop rules

Provide Claude Code the actual prepared.json COPY alongside the existing fixed source and updated focused request. This avoids the earlier MES reviewer-access limitation; inability to access /workspaces is not a reason to rerun preparation when the attachment is available.

Review only C1 and necessary inherited interfaces: adapter optimization/serialization/phase selection;GPT loss/logits;budget pairing;fresh-test exclusion and full-run barrier;worker byte-buffer binding and duplicate-evidence preservation;primary/GPT protection logic. CPU components or no-update synthetic native probes may be run with explicit environment limits. No prepare/train/evaluate,test scoring,source/protocol edits,push,merge or GPU during review.

After a real C1 report and owner acknowledgement,proceed through the existing train entry with --review-report/--reviewer/--review-approved. Do not fabricate a report,waive source identity or use the request as approval. Retain C1_OUTPUT_DIR=/workspaces/OpenMythos/mythos_evidence/mech_c_confirm_v1. No automatic training in this handoff.

Keep PR23 Draft/unmerged;Formal Oracle BLOCKED/NOT_READY,FORMAL_ACCEPTANCE_READY=False. No G2 REAL,upstream/J1/Bench/R3 changes or later mechanisms. Previous scientific outcomes and reviewer attributions stay intact.