# M2-T v1: equal-budget training-depth intervention

Date: 2026-10-29. Native experiment NOT TESTED at freeze. New research stage, not a repair of M2-L or M2-D. User requested continuation after the fixed-weight M2-D primary failure.

## One question

For the same native Parcae model and same saved model/AdamW/RNG starting state, does brief training at alternating depths 1 and 3 improve depth-4 validation quality compared with an equally trained fixed-depth-2 control? This tests a training-distribution intervention, not another inference-only depth sweep, an architecture patch, ACT or a claim that recurrence beats GPT.

M2-D execution and primary FAIL are currently supported by user terminal output; its original result.json is still absent from this review. The new stage's direct inputs are the previously uploaded and audited M2-L checkpoints, NOT a reconstructed M2-D JSON. No old result is upgraded or overwritten. Claude's six underlying review files remain pending; initialization A-M2L-02 is OPEN. Loading complete stored model/optimizer/RNG state avoids requiring initial-seed reconstruction only for this within-model experiment. Native inactive paths A-M2L-01 remain in both arms.

## Frozen controls

- Branch base: 1887dc3d65f77bd204a7cf2548fc283070af364c. Original native Parcae pin: 69284c13746e849104f738d6d1a347b1f457df76. No edits/monkeypatch of upstream, modules, gates, FFN width, initialization, tokenizer or optimizer.
- Seeds 42, 20261029, 20261030. Each arm independently loads its seed's complete M2-L step1920 snapshot. Snapshot file and semantic model hashes must match pilot.json SHA256 c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb. Require identical initial optimizer and CPU RNG digests between arms.
- Same native Parcae configuration as M2 matched/long: width32, FFN64, 1 prelude/1 core/1 coda, configuration mean_recurrence=mean_backprop_depth=2. Vary ONLY the explicit num_steps_pair=[0,d] at training time. All recurrence passes participate in gradients.
- Control FIXED: exactly 480 additional updates, training depth2 on every update.
- Intervention MIXED: exactly 480 additional updates; each adjacent two-update pair uses depths {1,3} once each. Dedicated CPU generator seed+37000 determines pair order. Exactly 240 depth1 and 240 depth3 updates, 960 total core calls in EACH arm. This is a fixed exogenous schedule, not learned halting or task-adaptive depth.
- Same Tiny Shakespeare training interval as previous M2, byte tokenizer256, sequence32, batch8. Same train-window generator seed+11: regenerate 2400 starts and take steps1920:2400. Verify the first1920 starts match the old checkpoint before use. Both arms receive identical additional batches, in identical order: 122880 new input/target tokens each; total from original start614400. Do not train on validation, original test or Alice.
- Restore the SAME saved CPU RNG state for each arm; record RNG digest immediately before each forward and require the two sequences to match. Count/probe/evaluation RNG is forked and must not consume training RNG. A mismatch is a blocked controlled comparison, not a new unannounced randomization policy.
- AdamW from snapshot, unchanged lr=.002, betas=(.9,.999), eps=1e-8, wd=0; clip norm1. Verify parameter order, group IDs, existing moment shapes/step counters and loaded optimizer digest. No optimizer reset, LR search, scheduler, early stopping or additional continuation after viewing outcomes.
- Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0, single CPU thread, deterministic algorithms, math SDPA. No packages downloaded/installed, GPU, cloud spend or upstream source modification.

## Before any training

All three loaded models at depth2 must exactly reproduce the preserved M2-L final validation record. Validate full state/file hashes. Do not run more training if any baseline fails.

Count forward+backward supported operators on the same fixed synthetic shape for depths1,2,3, without optimizer.step. Require C1+C3 == 2*C2 (integers) and therefore 240*(C1+C3) == 480*C2. Otherwise BLOCKED_BUDGET and stop; do not pretend equal average depth implies equal measured FLOPs. Counts exclude unsupported/scalar and optimizer operations; equal counted work is not a hardware speed/energy claim. Register count and formula before the learning run.

## Outcomes and preregistered gates

Evaluate ONLY the existing Tiny Shakespeare validation interval, all3485 windows/111520 targets, RNG1212 and original batching. This set has been explored before: this is a mechanism pilot, not fresh confirmatory validation. Original test and Alice must never be read. Only final post480-update depths2 and4 are evaluated for each arm; no intermediate quality selection or secondary-depth sweep.

1. Execution/integrity PASS: all six continuations complete exactly480 finite-loss/finite-gradient updates; unchanged input snapshots/source; state, data and RNG pairing checks pass; final weights differ from starting weights; final model/optimizer/RNG snapshots and full traces saved.
2. Counted-budget PASS: identical total target exposures and exactly equal counted forward/backward work across the paired arms, plus same registered parameters. Treat end-to-end runtime as descriptive only.
3. PRIMARY training-intervention screen: mean over seeds[NLL(MIXED,d4)-NLL(FIXED,d4)] <= -0.01 AND every seed's difference <0. Execution and budget must first pass. This compares both models at identical inference depth/counted forward cost.
4. Preserved-depth safeguard: mean[NLL(MIXED,d2)-NLL(FIXED,d2)] <=+.02 AND each difference <=+.05. Combined intervention success requires BOTH primary and safeguard; keep both components visible on failure.
5. Separate EXTRA-INFERENCE-COMPUTE screen: mean[NLL(MIXED,d4)-NLL(MIXED,d2)] <=-.01 AND every seed's difference <0. This is required before saying extra inference depth benefited the mixed-trained weights. Primary improvement against FIXED alone does NOT prove extra-depth benefit. Report the corresponding extra counted inference cost, never call it free.
6. Report the difference-in-differences between each arm's d4-d2 gaps descriptively, all per-seed scores, parameters, counted FLOPs, time and actual training token budget. No statistical noninferiority, downstream reasoning, ACT, hardware throughput or general Parcae/GPT superiority claim.
7. Any primary/safeguard failure ends this preregistered pilot; preserve it. No try4800, alternate depth distribution or modified tolerance without a genuinely new preregistered research decision. Success also needs actual independent review and fresh heldout/compute verification before broader claims.

## Evidence and next gate

Write into a NEW persistent /workspaces/OpenMythos/mythos_evidence/m2_trainmix_v1 directory. No overwrites or auto-resume. Save experiment commit/source hashes, protocol hash, full dependency freeze, source/evidence checks, per-arm initial state digests, batch/depth/RNG schedules, traces, final snapshots and result.json. Old M2-L/M2-D records stay immutable; do not repeat their archival audits just to count more PASS checks.

Preparation tests may exercise schedule arithmetic, verdict classification and snapshot parsing on the local CPU, clearly labelled as preparation, not a native training run. Native training remains NOT TESTED until the exact pinned environment executes. No PR merge. Claude/Grok review of THIS protocol/implementation remains NOT TESTED until an actual report arrives. Formal Oracle and G2 REAL stay gated.
