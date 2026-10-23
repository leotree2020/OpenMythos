# P1-C Experiment Plan — Native Parcae Small-Scale Training Reproduction

**Authorization**: Planning and static/CPU tools only. No GPU training until user approval.

## Stage 1 — GPU Smoke (tens of steps)

Goal: Verify official Parcae GPU training path is usable from random init.

- Confirm CUDA / PyTorch / driver compatibility
- Forward + backward on GPU
- A few optimizer steps with MuonAdamW
- Gradient finite, parameters update
- Checkpoint save + resume with identical RNG / data state
- Suggested scale: 20–50 steps, reduced micro-batch if needed, single GPU

Config derived from `parcae-small-140m.yaml` (pinned commit).

## Stage 2 — Short Training

Goal: Observe learning signal and stability on real text.

Monitor (must log):
- train / val loss
- grad norm
- recurrent state norm / residual
- DiagonalInjection decay
- iteration depth
- tokens/sec, peak GPU mem, training FLOPs
- checkpoint recovery

Pre-define stability gates and stop conditions before launch.
Fix data version, tokenizer, seeds, sequence order.

## Stage 3 — Reproduction Candidate

Only after Stage 1+2 pass. Propose longer run focusing on:
- Val loss vs recurrence depth
- Stability vs FLOPs cost
- Whether depth yields repeatable gains

No formal training in this stage of the plan.

All stages reuse official scripts/configs. No rewrite of Parcae core.
