# D1 checkpoint — native preparation received; Claude review next

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Current decision

**Owner-run native CPU prepare PASS. Actual uploaded prepared(1).json was completely parsed and hashed: 135 read-only record/source-copy assertions PASS, 0 FAIL, 1 inherited full-source-byte item NOT TESTED. Twelve native training trajectories, learned-state measurements and quality remain NOT TESTED. Claude Code D-specific review PENDING.**

Preparation handoff is complete. Do not rerun prepare, request the same JSON again, create another worktree, or launch training without the agreed actual Claude report and owner acknowledgement. This audit did not run any model, optimizer, profiler, data scoring or previous experiment. Preparing a review bundle is not evidence Claude has received it.

## 1. Git and frozen execution

Repository leotree2020/OpenMythos; Draft PR24; branch mini-mythos-d1-dual-state-profile-cpu-20261031. Live head before this documentation update was395d60952f075ed6a37718fdd07ed2516bf2ef21. Base C1 checkpoint4790d0cfd34c90df7be64a18eccd02deb3b74a92. Changes remain isolated under research/mini_mythos/dual_state/.

**Execution/review pin stays596af7f8997ca793e880a6e1d80c25c7b2043329.** Preserve the successfully prepared worktree /workspaces/mythos-d1-20261031 at that commit. Do not switch it to a documentation HEAD. Protocol first committed355d0f5478f28d89e4e75317bf66c09c85077540. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains read-only. No runtime/protocol/model/threshold edits in this update.

The full prior development checkpoint is preserved at395d60952f075ed6a37718fdd07ed2516bf2ef21:25 fixture component tests,18 launcher cases,fixture pipeline and expected local version-gate refusal. These are historical,not newly rerun. Prior C1/MES negative outcomes and their pending result reviews are unchanged; D was explicitly authorized separately by the owner. Claude Code replaces Grok; no extra Grok gate.

## 2. Actual preparation evidence

Original upload prepared(1).json: **21,440 bytes**. Independently calculated SHA256 **d7ce57ca11316d0ff892bf35b26ec9ed1ef2f04a2b8587dd4671c7eae8b5a1d1**, exactly matching the owner's terminal digest. This establishes correspondence with the reported bytes,not authentication of every producer claim.

Production path /workspaces/OpenMythos/mythos_evidence/dual_state_v1/prepared.json. Producer records Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,CPU one thread. Seeds2101/2202/2303; four arms GPT/P4/D0/D1. Code/upstream pins match. Review status PENDING Claude Code;training/quality NOT TESTED;scope old train/development only,no optimizer updates.

Thirty-six unique native/reference cases cover3 seeds x P4/D0/D1 x depths2/4 x lengths6/9. All record PASS and max_gradient_error0. Three GPT masked-CE checks record PASS/error0. These are producer numerical records read by this auditor,NOT independent model re-execution. P4 compares to the original native path; D0/D1 compare to their respective explicitly unrolled two-state native-module references. Do NOT describe this as D0/D1 being equal to unmodified P4.

Corresponding P4/D0/D1 base and full initialization digests match. All four arms' per-seed shared-IO records match. Raw starting tensors were not supplied. Actual learned behavior is still unknown.

|Arm|Registered parameters|Gradient-present probe parameters|Forward FLOPs|Backward FLOPs|Step FLOPs|Projected 3000-update count, NOT a training result|
|---|---:|---:|---:|---:|---:|---:|
|GPT|65344|65344|24477696|48955392|73433088|220299264000|
|P4|60224|51904|38043648|76087296|114130944|342392832000|
|D0|60224|51904|38043648|76087296|114130944|342392832000|
|D1|60224|51904|38043648|76087296|114130944|342392832000|

All three seed records agree. P4/D0/D1 match registered parameters and supported-op counters; they do NOT thereby match hardware work,walltime or peak memory. Each Parcae path has about55.42% more counted work per update than GPT. The whole four-arm study is SAME updates/data exposure,NOT equal counted compute. Do not rebudget now. Gradient presence is not nonzero gradient/effective capacity. Known8320 inactive Parcae parameters remain;no repair here.

## 3. Actual audit and remaining limits

Used standard-library code only: strict whole JSON parsing (duplicate/nonfinite rejection),file SHA,source aggregate,pins/environment records,seeds/arms/case membership,counts/arithmetic,starting identity pairing and fixed data metadata. Actual135 PASS,0 FAIL,1 NOT TESTED. This is bounded record verification,not scientific quality or full implementation acceptance.

Recomputed source aggregate **7b7660c5c5ddcd3ca599f45f82c6e8567bfd00e4b968204d600855d8e483e481**. Six own source/protocol byte copies from the retained development ZIP match uploaded SHA256 and freshly read pinned Git blob/size metadata. Seven inherited byte copies match uploaded SHA256. The eighth,m2_matched/experiment.py,is not present in that ZIP and was not freshly retrieved/byte-verified here; its declaration stays bound,not falsely marked independently verified.

Data metadata:19977 train rows/10000 canonical pairs;1024 development questions/256 per carry category. data.json,initial tensors,pip-freeze and the owner's full filesystem were not independently obtained. No question labels were reconstructed or scored in this audit. Native/reference checks,hardware measurements,learning/correction/state-sensitivity profiles and resume replay were not run by this auditor.

Conversation delivery contains exact production bytes at the review ZIP root as prepared.json,and separately as D1_prepared_20261031.json. It includes audit_prepared.py,audit_result.json,audit.log,source copies,INPUT_MANIFEST.json,SHA256SUMS.txt and focused Claude instructions. The historical development archive's blocked_native/prepared.json is NOT this production evidence and is not included as a competing preparation file in the new bundle.

## 4. Frozen mechanism and measurement plan

F(h,u) is one native injection/shared-core call; e is the prefix representation; initialize z=a=h0. P4 repeats F(h,e). D0 cycles z=F(z,e),a=F(a,z_new);D1 cycles z=F(z,e+a_old),a=F(a,z_new). Two work/answer cycles mean FOUR total core calls. No detach,new parameters,auxiliary loss,damping,LoRA,learned gate,inactive-path fix or cross-example memory. Latent a is not target truth or a textual reasoning trace. This is one dual-state variant,not TRM reproduction.

GPT/P4/D0/D1 x3 new seeds=12 trajectories,3000 updates each,batch32,unchanged AdamW/clip/FP32/CPU1thread. Save36 full snapshots at300/1500/3000. Evaluate only after all12 finish:21 final conditions on the same1024 old development questions (21504 repeated answers),36 learning profiles,27 same-prefix latent profiles and6 final dual-state sensitivity groups. No H1/HC/H2/C1T or fresh-test claim.

State RMS/change/separation/cosine and next-token confidence are measurements,not proof of reasoning or correct state specialization. Full-answer depth2-to4 counts compare separate generation policies. Zero-state interventions before cycle2 assess local next-token sensitivity;noop must be identical. Logical state bytes are not actual peak memory. No new mechanism/threshold/seed search.

Exploratory D0-P4,D1-P4,D1-D0 screens remain mean>=1pp and every loss<=1pp,reference>99% ceiling handling. **Exit0 means execution/measurement complete even if all screens FAIL;candidate selection NOT ASSESSED.** No statistical,hardware-efficiency,new-holdout or depth-extrapolation acceptance.

## 5. Next single action

Send Claude Code the actual D1_prepared_20261031.json AND D1_Claude_Code_Review_After_Prepare_20261031.md (or the complete Mythos_D1_Prepare_Review_Handoff_20261031.zip). Ask it FIRST to list the received file names/sizes and independently hash the JSON. A request-only attachment is not preparation evidence. If the file is unavailable to Claude,retain that limitation explicitly;do not replace reading existing evidence with a repeated prepare run.

Review fixed596af7f sources and necessary inherited interfaces:old-a/new-z routing,gradients/RNG/causality,training/snapshot/pairing,measurement interpretation and byte binding,complete-run barrier,independent output states. CPU fixture or no-update synthetic checks may be run with environment limitations explicit. No prepare/train/evaluate,optimizer.step,heldout scoring,source/protocol edits,commit/push/merge or GPU in review. Output actual APPROVE/CHANGES_REQUIRED/BLOCKED and stop. Previous MES/C1 approval is not a D approval.

After a real D-specific report and owner acknowledgement,use the existing train phase with --review-report/--reviewer/--review-approved; do not invent approval or call a request a report. This checkpoint provides no automatic training command. Keep output directory dual_state_v1 and original prepared bytes unchanged.

Formal Oracle BLOCKED/NOT_READY,FORMAL_ACCEPTANCE_READY=False. Keep PR24 Draft/unmerged. No G2 REAL,upstream/J1/Bench/R3/old-experiment edits,automatic merge,GPU expansion or E. No direct access to the owner's Codespaces or background execution claimed.
