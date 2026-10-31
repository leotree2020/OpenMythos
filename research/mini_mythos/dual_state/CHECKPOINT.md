# D1 checkpoint — evaluation complete; evidence audit PASS; all three exploratory screens FAIL

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Current decision

**D1 TRAINING EXECUTION = PASS. D1 TRAINING EVIDENCE AUDIT = PASS. D1 EVALUATE EXECUTION = PASS. D1 RESULT EVIDENCE AUDIT = PASS.**

**Scientific conclusion (conservative).** D1 was implemented, trained and evaluated successfully, and its evidence passed the independent completeness/integrity audit. However, the frozen D1 variant produced no positive performance signal relative to P4. D1 was worse than P4 in all three paired seeds at depth 4, and all three preregistered exploratory screens failed. Dual-state and feedback paths measurably alter internal computation, but their usefulness is not established.

The implementation/training/evaluation pipeline worked; the negative result concerns mechanism performance under this frozen protocol. It is not an "implementation failed" finding. Further architectural or optimization experiments require a new protocol. This checkpoint does not design D2.

Source of the numbers: owner terminal outputs of the frozen parent `evaluate`, the owner's read-only evidence scripts, and the owner-reported independent result audit (below). The checkpoint author had no access to the Codespaces filesystem and did not itself re-read `result.json` or any snapshot; numbers are transcribed from the supplied terminal outputs.

## 1. Purpose

Run the frozen evaluate phase on the existing 36 snapshots (no weight updates) and measure, on the already-viewed 1,024-question development set, whether separating a working latent z from an answer latent a (D0: answer feedback ablation; D1: answer feedback e+a_old) changes learning, correction/corruption, state trajectories and cost relative to native P4 and to GPT. Exploratory, development-set, three-seed study; not candidate confirmation.

## 2. Environment and source identity

Production environment (retained `prepared.json`): Linux, Python 3.12.3, torch 2.11.0+cpu, NumPy 1.26.4, einops 0.8.0, CPU FP32, one thread; interpreter `/workspaces/mythos-m2-cpu312/bin/python`; read-only upstream `/workspaces/mythos-parcae-pinned` = sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. No installation, GPU, retry, resume or source change.

Executed code stays **`596af7f8997ca793e880a6e1d80c25c7b2043329`** in `/workspaces/mythos-d1-20261031` (HEAD verified and tracked tree clean before evaluate, per the owner's terminal); source identity aggregate `7b7660c5c5ddcd3ca599f45f82c6e8567bfd00e4b968204d600855d8e483e481` (six own + eight inherited files). Evaluate was invoked as the unchanged parent `run_codespaces_cpu.sh evaluate` with `D1_OUTPUT_DIR=/workspaces/OpenMythos/mythos_evidence/dual_state_v1`; no manual worker, prepare, train or optimizer step. Documentation/handoff commits after 596af7f (539310a, 6b6272a, 2173da4, 5b9a657f and this one) are not execution code.

Evidence bytes: `prepared.json` 21,440 B `d7ce57ca…5a1d1`; `data.json` `9e3700d93bb1c30541e91bc60678a44ff898925f69e2f527f0050de96a0a8750`; `training.json` 4,800,251 B `11e380b075912b4542cdbc39ccb1ec98d5de92658ed21316187e2a64357864af`.

## 3. Result evidence and audit

`/workspaces/OpenMythos/mythos_evidence/dual_state_v1/result.json`: **8,204,167 bytes**, SHA-256 **`5cb3fd2111da36fb928421d0631b92ebe93a6a803bf03d884ec92c229c1c351d`**. Parent: `phase=evaluate`, `status=PASS`, `execution_status=PASS`, `exit_code=0`, no error. Candidate selection printed `NOT ASSESSED`.

Independent read-only result audit (owner-reported): **20 PASS / 0 FAIL**, strict parse (no duplicate keys or non-finite constants):

|Item|Result|
|---|---|
|Unique arm/seed evaluation rows|12|
|Final conditions|21 (GPT depth 4 x3; P4, D0, D1 depth 2 and 4 x3 seeds each)|
|Learning profiles (300/1500/3000)|36|
|Latent/state profiles (P4, D0, D1)|27|
|D0/D1 sensitivity groups|6|
|Gradient probes|12|
|Questions per final condition|1,024 (no missing or duplicate condition)|
|Stored floats finite|all 100,691|
|Snapshot files (steps 300/1500/3000, 12 jobs)|36/36 SHA-256 independently verified against `training.json`|
|Final-condition snapshot references|match step-3000 training evidence|
|`data.json`|unchanged|
|Final metrics recomputed from stored predictions|21/21 match|
|Probe metrics recomputed|36/36 match|
|Depth 2 to 4 transition tables recomputed|9/9 match|
|Exploratory screens recomputed|3/3 match|
|No-op intervention|exact identity (L2 0, no argmax change)|

Not recomputable without model execution and taken as stored: answer NLL, z/a state profiles and sensitivity numbers. Resume replay from snapshots: NOT TESTED.

## 4. Final results (depth 4 and depth 2; viewed development data, 1,024 questions)

Accuracy (correct/1024, invalid) and teacher-forced answer NLL:

|arm|depth|2101|2202|2303|mean (depth 4)|
|---|---:|---|---|---|---:|
|GPT|4|0.9619 (985, 0), NLL 0.0378|0.6309 (646, 0), 0.2620|0.9648 (988, 0), 0.0301|**0.8525**|
|P4|4|0.8301 (850, 0), 0.1304|0.9541 (977, 0), 0.0571|0.7607 (779, 0), 0.1636|**0.8483**|
|D0|4|0.8916 (913, 0), 0.1039|0.9072 (929, 0), 0.0721|0.1035 (106, 0), 0.5948|**0.6341**|
|D1|4|0.6641 (680, 0), 0.2351|0.7559 (774, 0), 0.2628|0.4580 (469, 0), 0.3536|**0.6260**|
|P4|2|0.4814 (493, 0), 0.6708|0.2871 (294, 1), 1.3116|0.1436 (147, 1), 1.9134||
|D0|2|0.4980 (510, 0), 0.5635|0.4189 (429, 1), 0.5828|0.0488 (50, 2), 1.1837||
|D1|2|0.1123 (115, 0), 2.4256|0.2686 (275, 3), 1.6572|0.0732 (75, 2), 1.6326||

Per-carry accuracies (0,1,2,3) at depth 4: GPT 2101 [0.984, 0.965, 0.934, 0.965], 2202 [0.453, 0.582, 0.711, 0.777], 2303 [0.965, 0.977, 0.981, 0.938]; P4 2101 [0.930, 0.859, 0.766, 0.766], 2202 [0.914, 0.965, 0.957, 0.981], 2303 [0.738, 0.746, 0.750, 0.809]; D0 2101 [0.910, 0.906, 0.895, 0.856], 2202 [0.922, 0.863, 0.922, 0.922], 2303 [0.070, 0.059, 0.113, 0.172]; D1 2101 [0.707, 0.637, 0.621, 0.691], 2202 [0.781, 0.703, 0.738, 0.801], 2303 [0.473, 0.438, 0.445, 0.477].

D1 final NLL is worse than paired P4 in all three seeds (0.2351 vs 0.1304, 0.2628 vs 0.0571, 0.3536 vs 0.1636). D1 accuracy is below P4 in all three paired seeds at depth 4. GPT seed 2202 (0.631) is also a low outlier, so the reference arms vary strongly across seeds.

## 5. Preregistered exploratory screens (depth 4; mean >= +1 pp and every seed >= -1 pp; reference > 99% = ceiling)

|Comparison|Seed 2101|Seed 2202|Seed 2303|Mean|Status|
|---|---:|---:|---:|---:|---|
|D0 - P4|+0.0615|-0.0469|-0.6572|-0.2142|**FAIL**|
|D1 - P4|-0.1660|-0.1982|-0.3027|-0.2223|**FAIL**|
|D1 - D0|-0.2275|-0.1514|+0.3545|-0.0081|**FAIL**|

No reference mean exceeded 0.99; no ceiling handling was triggered. Parent and independent recomputation agree. The failures are retained and not reinterpreted. They are exploratory screens, not candidate selection (candidate selection NOT ASSESSED).

## 6. Learning curves (32 fixed development probes, 8 per carry; 1 prompt = 3.1 pp; descriptive only)

|arm|seed|step 300|step 1500|step 3000|
|---|---|---:|---:|---:|
|GPT|2101|0.000|0.719|0.969|
|GPT|2202|0.031|0.500|0.594|
|GPT|2303|0.031|0.938|0.906|
|P4|2101|0.000|0.219|0.906|
|P4|2202|0.000|0.156|0.969|
|P4|2303|0.000|0.031|0.688|
|D0|2101|0.031|0.250|0.812|
|D0|2202|0.000|0.312|0.906|
|D0|2303|0.000|0.062|0.062|
|D1|2101|0.000|0.188|0.719|
|D1|2202|0.000|0.438|0.562|
|D1|2303|0.000|0.000|0.531|

Observations (descriptive, 32-prompt noise, three checkpoints only): all runs are near zero at step 300; GPT learns earlier per update; D0 stalls at 0.062 on seed 2303 between steps 1500 and 3000 (matches its flat late training loss). At step 1500, D1 equals or exceeds P4 on one seed (2202: 0.438 vs 0.156) but is below P4 on 2101 and 2303; P4 then gains much more strongly by step 3000 in every seed, and D1 is below P4 at step 3000 in every seed. These curves do not support a simple claim that D1 is merely slower to converge. Nothing is extrapolated beyond step 3000, and no claim is made that more training would or would not help. The per-checkpoint z/a summaries at 300/1500 were produced by the owner's audit script but were not supplied to the checkpoint author and are not recorded here.

Post-hoc training-loss diagnostic (mean over last 100 of 3000 updates; not a preregistered criterion): GPT 0.052/0.281/0.018, P4 0.095/0.063/0.172, D0 0.105/0.102/0.594, D1 0.192/0.130/0.405 (seeds 2101/2202/2303). D1 is above P4 in all three seeds; D0 seed 2303 plateaus near 0.59; GPT seed 2202 ends higher (0.281). Mean pre-clip gradient norms over the last 100 steps are 1.2 to 4.2 (above the clip threshold 1), with a D1 spike of 162.6 on seed 2202. Final accuracy tracks late training loss broadly but not pairwise exactly. D0 therefore shows severe seed instability, especially seed 2303.

## 7. Correction and corruption (depth 2 to depth 4, two complete free-generation policies)

|arm|seed|wrong to right|right to wrong|stable correct|stable wrong|changed wrong|net|
|---|---|---:|---:|---:|---:|---:|---:|
|P4|2101|393|36|457|138|73|+357|
|P4|2202|689|6|288|41|29|+683|
|P4|2303|646|14|133|231|190|+632|
|D0|2101|430|27|483|84|61|+403|
|D0|2202|515|15|414|80|46|+500|
|D0|2303|74|18|32|900|559|+56|
|D1|2101|596|31|84|313|274|+565|
|D1|2202|533|34|241|216|161|+499|
|D1|2303|422|28|47|527|475|+394|

Corruptions are small (6 to 36 of 1,024) everywhere; corrections are large except D0 seed 2303 (900 stable wrong). These counts are NOT proof of iterative self-correction: depth 2 was never trained as an objective (training used depth 4 only) and the two depths are different generation policies, not an in-place edit of one answer.

## 8. State profiles (step 3000, last record, mean over 32 probes; descriptive)

|arm|seed|z RMS|a RMS|separation|cosine|first-digit confidence|
|---|---|---:|---:|---:|---:|---:|
|P4|2101|3.281|3.281|0.000|1.000|0.956|
|P4|2202|3.692|3.692|0.000|1.000|0.949|
|P4|2303|2.080|2.080|0.000|1.000|0.981|
|D0|2101|2.179|3.318|0.271|0.938|0.936|
|D0|2202|2.263|3.377|0.251|0.950|0.933|
|D0|2303|1.755|2.618|0.253|0.948|0.993|
|D1|2101|3.815|4.500|0.129|0.980|0.985|
|D1|2202|3.097|3.429|0.120|0.976|0.915|
|D1|2303|3.246|3.645|0.121|0.977|0.970|

D0 and D1 do develop distinct z and a states. D0 shows larger z/a separation (about 0.25 to 0.27) than D1 (about 0.12 to 0.13), and D1 shows higher cosine (0.976 to 0.980 vs 0.938 to 0.950). That D1 feedback goes with z and a becoming more similar is a hypothesis-generating observation, NOT a causal conclusion (three seeds, one feedback design, no isolating experiment). Confidence is the first-digit next-token confidence only and is not correctness (R03): D0 seed 2303 has confidence 0.993 with 0.10 full-answer accuracy.

## 9. Intervention sensitivity (final checkpoint, 32 probes, last-position logits; mean L2 | argmax-change rate)

|arm|seed|no-op|zero_z|zero_a|
|---|---|---|---|---|
|D0|2101|0 \| 0|19.93 \| 0.125|13.12 \| 0.062|
|D0|2202|0 \| 0|10.27 \| 0.094|13.65 \| 0.094|
|D0|2303|0 \| 0|17.43 \| 0.000|22.30 \| 0.062|
|D1|2101|0 \| 0|6.89 \| 0.000|21.20 \| 0.219|
|D1|2202|0 \| 0|7.81 \| 0.062|18.33 \| 0.188|
|D1|2303|0 \| 0|8.64 \| 0.000|27.05 \| 0.312|

No-op is exactly identical. The interventions show that the new state and feedback routes affect computation; they do NOT show that those routes improve correctness. R02: in D0 `zero_a` clears only the carried answer state; in D1 it also removes the `e+a` feedback, so D1 and D0 `zero_a` values are not comparable and are not "importance of the answer state". Zero is out-of-distribution and there is no matched-norm random-perturbation baseline.

## 10. Gradient presence (one synthetic batch, final checkpoints)

GPT: 65,344 registered, 65,344 with gradient, 41,728 nonzero elements. P4, D0 and D1 (every seed): 60,224 registered, 51,904 with gradient, 36,160 nonzero elements; the parameters without gradient are the same two tensors in every case (`base.transformer.core_block.0.attn.ve_gate.weight`, `base.value_embeds.0.weight`, 8,320 parameters; known inactive paths, not repaired). Presence of a gradient is not effective capacity, and the nonzero counts come from one synthetic batch.

## 11. Findings carried forward

|ID|Status|
|---|---|
|R01 LOW|OPEN. Worker numerical failure would be stored FAIL while the unchanged parent may report BLOCKED. Not triggered in training or evaluate. Not patched; any fix needs its own source identity.|
|R02 INFO|OPEN caveat. D0/D1 `zero_a` are different perturbations; zero is out-of-distribution (section 9).|
|R03 INFO|OPEN caveat. Profiles read the six-digit prompt only; intermediate readouts are unsupervised; confidence/closeness is not correctness; some change fields are zero by construction.|
|R04 INFO|Audit caveat addressed for this result: cardinalities (12/21/36/27/6/12) were counted from stored rows by the independent audit; the runner itself still does not assert them.|
|R05 INFO|OPEN interpretation caveat. Exit 0 means completion even if all screens fail. D-vs-P4 changes state structure and routing together, so it is not pure storage causality. Three seeds, already-viewed development data, GPT has lower counted compute, 8,320 inactive parameters.|

## 12. Limitations

Three seeds are not statistical confirmation, and seed variation is large for every arm (including GPT and P4). The development set was already viewed; this is not fresh-test evidence. The four arms share data and updates but not compute (GPT 73.4M vs Parcae 114.1M counted FLOPs per update). Only one D variant, 3000 updates and depth 4 training were tested; nothing is claimed about longer training, other seeds, other widths or other dual-state designs. Training-loss and learning-curve observations are post-hoc diagnostics. Per-checkpoint latent summaries at 300/1500 and answer-NLL/state numbers were not independently recomputed.

## 13. Git status

Branch mini-mythos-d1-dual-state-profile-cpu-20261031; remote head before this update `5b9a657f912f04a461d38f5ee45f1f6f3119556f`. This commit changes only this file. Execution code pin 596af7f unchanged; no upstream, D0/D1, protocol, data, threshold, seed, training-output or evaluation-output change. Owner's Codespaces worktree was at 596af7f with a clean tracked tree before evaluate. PR #24 is Draft and unmerged.

## 14. Stage state

|Item|Status|
|---|---|
|Native preparation|PASS|
|Claude D code review|APPROVE for 596af7f (owner-supplied report)|
|Training execution / evidence audit|PASS / PASS|
|Evaluate execution|PASS|
|Result evidence audit|PASS (20/20, owner-reported)|
|Exploratory screens D0-P4, D1-P4, D1-D0|FAIL, FAIL, FAIL|
|Positive performance evidence for D1 vs P4|NONE under this protocol|
|Candidate selection|NOT ASSESSED|
|Equal-compute superiority|NOT TESTED|
|Statistical confirmation|NOT TESTED|
|Fresh-test generalization|NOT TESTED|
|Hardware efficiency|NOT TESTED|
|Depth extrapolation / longer training|NOT TESTED|
|Resume replay|NOT TESTED|
|R01|OPEN/LOW|
|Formal Oracle|BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False|

## 15. Next action

No further D1 execution. Do not rerun prepare/train/evaluate, run optimizer steps, new seeds, new held-out data or GPU, or change D0/D1, upstream, data, thresholds or budget under this protocol. Any follow-up (for example investigating the D0 seed 2303 stall, longer training, other designs) needs a new authorized protocol and, if code changes, its own source identity and review. Keep PR #24 Draft/unmerged. Claude Code replaces Grok by owner policy; preserve earlier negative results and reviewer attributions.
