# D1 checkpoint — Claude review received; approved-code training handoff

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Current decision

**Actual owner-supplied Claude Code report: APPROVE for executable commit596af7f8997ca793e880a6e1d80c25c7b2043329, with one LOW and four INFO findings, none blocking the12 planned CPU training runs. This time Claude reports receiving, hashing and checking the real preparation JSON, plus all six own/eight inherited source hashes. Native training, learned-state measurements and model quality remain NOT TESTED.** Approval is permission to enter the frozen training study, not evidence D works.

No prepare rerun, same-file reupload, generic repeat review or new worktree is needed. Next action is ONLY the existing reviewed parent train phase, with the supplied actual report and explicit owner acknowledgement. This handoff did not run any native model, optimizer, training, development scoring or historical experiment.

## 1. Git and immutable execution

Repository leotree2020/OpenMythos; Draft PR24; branch mini-mythos-d1-dual-state-profile-cpu-20261031. Base C1 checkpoint4790d0cfd34c90df7be64a18eccd02deb3b74a92. Branch head was537fa6815cc9bf227716555e230181c90c91b8d3 before review registration.

**Execution/review pin stays596af7f8997ca793e880a6e1d80c25c7b2043329.** Keep the successfully prepared worktree `/workspaces/mythos-d1-20261031` there. Do not checkout a later documentation/helper HEAD. Protocol first355d0f5478f28d89e4e75317bf66c09c85077540; read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Frozen code, protocol, optimizer, seeds and criteria are unchanged.

- Prior preparation audit and full development lineage: checkpoint537fa6815cc9bf227716555e230181c90c91b8d3 and earlier395d60952f075ed6a37718fdd07ed2516bf2ef21. Historical135 audit checks,25 component tests and18 launcher cases are not newly rerun.
- Actual review transcript: `evidence/D1_CLAUDE_REVIEW_OWNER_TRANSCRIPT_20261031.md`, committed539310a54492cd219b4e37c252985ac75b73ed7a. Transcript SHA256728d6960a88c997f5cea85d6fa1dcda57d3c5bfdc4378c6e319b9cffeaf57d0d.
- Train-only convenience entry: `evidence/train_after_claude_20261031.sh`, committed6b6272a165189f348ba63e47490c75ae6667fa97. Its approval scope is separate from Claude's frozen-code review.

The transcript is the owner's pasted report with Markdown/HTML whitespace normalized. Claude's original scratchpad file, scripts, raw logs and authenticated identity were not obtained. No GitHub approval was submitted impersonating Claude. Source and preparation checks below are attributed to the reviewer rather than claimed as newly run by ChatGPT.

## 2. Preparation and review evidence

Production preparation remains `/workspaces/OpenMythos/mythos_evidence/dual_state_v1/prepared.json`. Actual retained bytes re-read in this handoff:21,440 bytes,SHA256d7ce57ca11316d0ff892bf35b26ec9ed1ef2f04a2b8587dd4671c7eae8b5a1d1. This matches the previous owner terminal and the reviewer-reported received file `ccb08253-D1_prepared_20261031.json`. Byte correspondence is not producer authentication.

Prepared source aggregate7b7660c5c5ddcd3ca599f45f82c6e8567bfd00e4b968204d600855d8e483e481. The reviewer reports checking all six own/eight inherited files, including the full m2_matched/experiment.py omitted from the earlier handoff artifact. That is new reviewer-reported coverage, not a retroactive rewrite of ChatGPT's earlier factory-byte NOT TESTED item. Raw initial tensors,data.json,pip-freeze were not independently supplied to Claude. Existing worker data/source/start checks stay active.

Claude reports strict JSON parsing,15/15 field checks,25/25 fixture tests and real fixed-model forward/backward diagnostics at seed2101 only, without any optimizer.step. It reports exact loss/logit/gradient/RNG equality against native P4 or its independent dual-state unroll, no hook leak even on error, D1 causality, and untrained state/sensitivity profiles. No native probes for2202/2303, prepare, train, evaluate, launcher execution, resume replay or model quality scoring.

Reviewer runtime was torch2.11.0+cu130 on CPU, bypassing the production version check for diagnostics. This is NOT production-build reproduction. Production remains Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0/CPU one thread. No runtime gate is relaxed.

The historical prepared.json review_status=PENDING Claude Code must stay unchanged. The later training record separately archives the actual report bytes/hash and owner acknowledgement.

## 3. Findings and decisions — no hidden fixes

|ID|Status and disposition|
|---|---|
|R01 LOW|OPEN. Worker numerical failure is recorded FAIL, but the unchanged parent can report BLOCKED/exit2. This is a failure-classification defect, not a model-computation change. Reviewer explicitly found it nonblocking. Retain frozen reviewed source for this run. If triggered, stop, preserve both summary and worker evidence, and separately report numerical FAIL plus parent-classification defect; never call it NOT TESTED or automatically retry. No patch is claimed.|
|R02 INFO|In D0,zero_a clears carried answer state. In D1 it clears that state AND its feedback into e+a. Cross-arm zero_a sensitivity does not isolate answer-state importance;zero is out-of-distribution. Report the joint perturbation explicitly. Reviewer values1.429 vs0.403 are UNTRAINED diagnostics,not learned D results. No new intervention is added here.|
|R03 INFO|Same-prefix state profiles cover the six-digit prompt only. Call2 confidence/entropy use an unsupervised intermediate readout;some relative changes are zero by construction. Do not infer better correctness,convergence or specialization from confidence/zero-change alone.|
|R04 INFO|Profile/trace cardinalities hold by loop construction but are not explicitly asserted in the frozen runner. Result audit must count the actual data:12 runs,36 snapshots,21 final conditions,36 learning profiles,27 latent profiles,six sensitivity groups,and3000-step traces. Missing measurements are missing evidence,not automatically PASS.|
|R05 INFO|Exit0 means execution/measurement completion,even if all exploratory screens FAIL. D-vs-P4 changes routing and state together. Three seeds,old development data,unequal GPT compute and8320 inactive parameters remain. Candidate selection NOT ASSESSED.|

A future bookkeeping fix or new isolation experiment must have its own source identity; do not silently patch this prepared/reviewed run. No further generic pretraining review is required by this limited APPROVE. Prior MES/C1 result reviews remain separately DEFERRED.

## 4. Frozen experiment and acceptance scope

F(h,u) is one unchanged native adapter/shared-core call. P4 repeats F(h,e). D0 cycles z=F(z,e),a=F(a,z_new). D1 cycles z=F(z,e+a_old),a=F(a,z_new). Two work/answer cycles mean FOUR core calls,not eight. Initialize z=a=h0. No new parameters,auxiliary loss,damping,LoRA,learned gate,inactive-path repair,cross-example memory or TRM reproduction claim.

|Arm|Seeds|Updates per seed|Recorded per-update count|Projected total per seed,not executed|
|---|---|---:|---:|---:|
|GPT|2101/2202/2303|3000|73433088|220299264000|
|P4|2101/2202/2303|3000|114130944|342392832000|
|D0|2101/2202/2303|3000|114130944|342392832000|
|D1|2101/2202/2303|3000|114130944|342392832000|

Twelve trajectories,batch32,unchanged AdamW/clipping/FP32. P4/D0/D1 have matched registered parameters and supported-op counts,not necessarily latency/peak memory. GPT has lower counted work;the four-arm study is same data/updates,NOT equal compute. Keep3000 steps;no rebudgeting.

Save36 full model/optimizer/RNG/index snapshots at300/1500/3000. Only old19977-row training and1024-question development data. After all12 complete,a separate evaluate phase performs21 final conditions(21504 repeated answers),36 learning profiles,27 prompt-only state profiles,six final sensitivity groups. No H1/HC/H2/C1T. Correction/corruption compares separate depth2/depth4 generation policies,not in-place editing. Logical state bytes are not peak memory.

Screens D0-P4,D1-P4,D1-D0 at depth4:mean>=1pp and every paired loss<=1pp,reference>99% ceiling handling. Execution and scientific screens remain separate. Candidate selection NOT ASSESSED;equal-compute/fresh-test/statistical/hardware-efficiency/depth-extrapolation claims remain NOT TESTED.

## 5. Next single command and actual handoff tests

Fetch the branch and extract `evidence/train_after_claude_20261031.sh` from6b6272a165189f348ba63e47490c75ae6667fa97; run it with `--start-training`. That explicit invocation acknowledges use of this limited APPROVE. It uses the existing596af7f worktree,checks existing prepared/data bytes,retrieves the actual registered transcript at539310a,and calls ONLY the unchanged parent `run_codespaces_cpu.sh train --review-report ... --reviewer ... --review-approved`.

No new worktree,checkout,source edit,dependency install,prepare,evaluate,manual worker,retry or resume. Existing training/partial evidence or console logs stop the helper before dispatch. Do not run concurrent copies. The report is temporary until the original parent copies it to review.md;only temporary handoff files are deleted. Original runtime/upstream/source/start guards remain active.

New helper checks actually executed locally:Bash syntax PASS and13/13 synthetic orchestration tests PASS,including exact report forwarding,explicit acknowledgement,wrong HEAD,dirty worktree,changed/missing inputs,partial evidence retention,report mismatch,missing environment,and propagation of exit1/2. Tests remap filesystem paths and mock Git/parent dispatch;they do not execute the production launcher or models. First test process hit a tool timeout before completion;its partial log is retained,not called PASS. Replacing the slow test-only Git stub with a shell stub completed all13 tests;production helper unchanged. Helper SHA2561742783d53f7216068c7295ca57a488c1a9256aeace402b73aedd14146ebb059.

Expected next user result:`/workspaces/OpenMythos/mythos_evidence/dual_state_v1/training.json` plus terminal summary. This phase does NOT score development data or produce learned-state findings. No duplicate preparation or review needed.

## 6. Stage state

|Item|Status|
|---|---|
|Native original-runtime preparation|PASS,owner execution and previous byte audit|
|Claude D code review|APPROVE,actual owner-supplied report|
|Claude preparation/source checks|PASS as reported;all six/eight source files covered|
|R01 parent failure classification|OPEN/LOW;not patched|
|Native12 training trajectories|NOT TESTED;not launched here|
|Learned D profiles/quality/hardware efficiency|NOT TESTED|
|Candidate selection|NOT ASSESSED|
|Formal Oracle|BLOCKED/NOT_READY;FORMAL_ACCEPTANCE_READY=False|

Claude Code replaces Grok by owner policy. Preserve old negative results and reviewer attributions. Keep PR24 Draft/unmerged. No G2 REAL,GPU expansion,upstream/J1/Bench/R3/old-experiment changes,automatic merge,hyperparameter search or E. No direct Codespaces access or background work claimed.
