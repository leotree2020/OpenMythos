# M2-D v1: fixed-weight native Parcae inference-depth diagnostic

Date: 2026-10-29. Status at freeze: NOT TESTED. Separate research stage, not a correction of M2-L, and not a general efficiency/capability claim.

## Single scientific question

For the SAME saved Parcae weights trained at depth 2 for 1920 steps, does increasing inference recurrence from 2 to 4 reduce validation NLL? Reuse existing final checkpoints; no training, backward, optimizer construction, optimizer.step, architecture patch or extra gradient-coverage diagnostic. Do not run Alice or the previously viewed Tiny Shakespeare test interval.

Primary comparison is fixed in advance: d=4 minus d=2. d=1 and d=8 are secondary ablation/extrapolation diagnostics; never substitute their best value for a failed primary result. All depth values use the official num_steps_pair=[0,d] argument under torch.no_grad() and model.eval(). The original mean_recurrence/configuration is NOT changed, and no module is replaced.

## Evidence and version pins

- New research branch starts from bfbb5d01a205025836f46cff067d065b8d2d99d2 on PR #13. PR #12/#13 and their original evidence remain unchanged and Draft.
- Untouched upstream: sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76.
- Reference model-construction code: research/mini_mythos/m2_matched/experiment.py SHA256 74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967.
- Original M2-L pilot.json SHA256 c5be0f6da8eab77ab499ad97a3aaf318633d2d44f234083165ffcacc3b26d7bb, code_head 09d0d508fa0eef459c8b767b109b236f9490c014. Final Parcae snapshots for seeds 42, 20261029, 20261030 must match the per-file SHA and semantic state_dict hash inside this pinned pilot.
- Load saved model state strictly; compare the complete loaded-state hash. Initialization A-M2L-02 remains OPEN: replacing all saved state avoids depending on reconstructing the original initialization, but does not solve or dismiss that discrepancy.
- A-M2L-01 inactive native paths remain present at every depth. This within-model diagnostic does not require equating Parcae and GPT updated-parameter counts and cannot explain the cross-model NLL gap causally.
- Claude's six raw reviewer files have not arrived in this conversation. Its single-batch claim stays user-supplied, NOT independently re-executed. This preparation does not upgrade reviewer evidence or seal missing files.

## Fixed evaluation

Linux, Python 3.12.3, torch 2.11.0+cpu, NumPy 1.26.4, einops 0.8.0; CPU FP32; one thread; deterministic algorithms; math SDPA; no package installation or GPU.

Tiny Shakespeare raw SHA256 86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed. Use only byte interval [int(N*.8), int(N*.9)); exact 256-byte tokenizer; sequence 32; nonoverlapping windows; evaluation batch 32 with the original last partial batch. Same 3485 windows / 111520 target tokens. Reset evaluation RNG to 1212 inside torch.random.fork_rng for EACH depth/seed, reproducing the prior stochastic initial-state draws. Do not sample new validation windows or select examples after scores.

First, independently reevaluate depth 2 for ALL three seeds and require exact equality with saved validation NLL, PPL, window starts hash, counts and discarded tail. Only if all three match, evaluate off-training-depth 1,4,8. If any reference fails, stop before examining off-depth scores; mark BLOCKED_REFERENCE_REPLAY, preserve evidence, no relaxed tolerance.

## Predeclared gates

1. Execution/integrity PASS: clean pinned upstream and research sources, correct corpus/pilot/checkpoint hashes, all 12 full validation evaluations finite, model state unchanged before/after every evaluation, no parameter gradients generated, target/window identity unchanged. A missing input/environment or failed baseline reproduction is BLOCKED, not a negative depth result.
2. Historical reevaluation PASS: depth-2 results exactly match all original three final Parcae validation records. This is actual native evaluation, not snapshot readability or initialization reproduction.
3. Primary exploratory depth benefit PASS: mean over three seeds of NLL(d4)-NLL(d2) <= -0.01 AND every seed's delta < 0. Otherwise FAIL. This newly preregistered directional screen is not a statistical test and does not override M2-L quality FAIL. It is chosen before off-depth metrics are observed, but uses an already-explored validation set: no confirmatory held-out claim.
4. Count forward-only supported-operator FLOPs separately for full evaluation batches and the last partial batch. Report total counted cost and ratios to d2. No backward or optimizer FLOPs; no hardware, latency or memory-efficiency superiority inferred. Extra recurrence must not be described as free computation. Descriptive elapsed time is not an acceptance gate.
5. Secondary d1/d8 results: report all values with count ratios; no separate quality PASS and no cherry-picking. Improvements, degradations and nonfinite outcomes must all remain visible.

## Decision boundaries

If d4 fails the primary screen, do not automatically train a new model, edit value-embedding gates or enlarge depth/compute to seek PASS. The result concerns depth extrapolation of a depth-2-trained tiny model only. It does not test mixed-depth training, retraining at larger depth, ACT, learned stopping or reasoning.

If d4 passes, it establishes only a validation-only fixed-weight benefit bought with extra forward computation. A later independent-corpus/compute-controlled study would still be required for broader claims.

No inference result has been obtained at this protocol commit. Claude/Grok review of M2-D is NOT TESTED. Original M2-L remains evidence-consistent / quality FAIL, A-M2L-01 recorded, A-M2L-02 OPEN. This branch prepares one CPU model question without changing old criteria.
