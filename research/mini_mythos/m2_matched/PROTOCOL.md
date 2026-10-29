# M2 matched CPU pilot v1 — pre-training protocol

This is a new pilot following the M2 simultaneous budget-match FAIL. Previous
results remain unchanged. Use untouched official GPT and Parcae from
sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. No upstream edits.

## Calibration, before natural-language training

Hold Parcae at the previous configuration: width 32, FFN 64, four heads,
1 prelude + 1 shared core repeated twice + 1 coda, [0,2] gradient pair.
GPT has four independent blocks, width 32, four heads. Search only its FFN width
over [48,52,56,60,64,68,72,76,80]. Select the candidate minimizing
max(parameter max/min ratio, counted forward+backward FLOP max/min ratio),
then the sum of those ratios, then FFN width. Both ratios must be <=1.10.
Use only synthetic fixed integer IDs for counting; do not inspect candidate
natural-language quality or train candidates during calibration. Write selected
configuration and measured counts to frozen_config.json and commit before training.
Re-measure on Linux and require counts to equal the frozen calibration.

## Training and evaluation

Tiny Shakespeare raw SHA256:
86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed.
Same existing download_text.py source and hash check. UTF-8 byte IDs 0..255.
Split raw byte offsets contiguously 80/10/10 before constructing windows.
Train sampling with replacement is intentional; each arm receives exactly the
same seed-specific windows. Seeds 42, 20261029, 20261030, sequence 32, batch 8,
120 steps = 30,720 training input tokens and 30,720 next-token targets per arm.
Use ALL complete non-overlapping windows from each held-out byte interval, with
batch size 32; report evaluated token counts and discarded tail. Do not cross
split boundaries. This does not eliminate repeated phrases in Shakespeare.

CPU FP32, one thread, deterministic algorithms, math SDPA. AdamW lr=.002,
betas=(.9,.999), eps=1e-8, wd=0, clip norm=1. No early stopping or LR tuning.
Linux environment: Python 3.12.x, torch 2.11.0 (CPU execution; CUDA wheel allowed),
NumPy 1.26.4, einops 0.8.0. Preflight/calibration may run on local torch 2.9 CPU;
formal training rejects other versions. CUDA_VISIBLE_DEVICES is empty in runner.

Initialization: construct each official model using native 'scaled' initialization
with the same seed. Before training, copy GPT input embedding, output-head matrix
(transpose for Parcae's storage convention) and final LayerNorm into Parcae.
Verify exact equality and common embedding/logit scales. All other parameters
retain native initialization. This is an explicit partial initialization control
in the experiment harness; it is not equality of all weights or an upstream edit.
Native GPT4/Parcae structure and different FFN widths remain confounders for
architecture-only attribution. Record effective model configs and initial hashes.

Evaluation uses forked RNG with a fixed seed per split, preserving training RNG
and giving initial/final Parcae evaluation the same stochastic-state draws.
No quality inspection affects calibration/selection. Record full training loss
and gradient-norm traces, final model weights, source/environment/config hashes.

## Predeclared gates

1. Mathematical preflight: native loss equals external next-token CE within 1e-6;
   changing the last half of input tokens leaves first-half logits unchanged
   within 1e-6 with fixed RNG; output shape is (batch,sequence,256), losses finite.
2. Budget/data: both max/min parameter and counted training-FLOP ratios <=1.10;
   exact corpus/split/batch hashes and train/evaluation token counts match arms.
3. Learning: finite loss and every available gradient each step; weights change;
   whole-validation NLL decreases by at least .01 for each of six runs.
4. Exploratory quality/noninferiority hypothesis: mean paired test NLL difference
   (Parcae minus GPT) <=.02 and each seed's difference <=.05. Report separately
   from execution and budget gates, regardless of outcome. Three seeds on a tiny
   corpus cannot establish general superiority or downstream reasoning ability.
5. Replay: seed 42 rerun in a fresh process on the same Linux environment must
   exactly match batch hashes, initial/final weight hashes, NLLs and FLOPs. Timing
   is descriptive and excluded from equality. Cross-OS equality is not a gate.

Count supported PyTorch forward/backward operators via FlopCounterMode. Report
forward and backward separately; do not call these total hardware FLOPs. Scalar
operations and optimizer costs are excluded. Only CPU elapsed training time is
measured; no GPU-memory, inference-speed or architecture-superiority claim.

Each gate has PASS/FAIL/BLOCKED/NOT TESTED status. Always preserve errors and partial
results; exit nonzero on a required gate failure. Grok cross-review remains
NOT TESTED until actual review is provided; keep PR Draft and label results
provisional. No direct Grok channel is available; never invent its review.
