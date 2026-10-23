# P1-C Experiment Plan — Native Parcae Small-Scale Training Reproduction

**Authorization**: Planning and static/CPU tools only. No GPU training until user approval.
**Pinned upstream**: Parcae `69284c13746e849104f738d6d1a347b1f457df76`

## Stage 1 — GPU Smoke (dozens of steps)

Goal: Verify official Parcae GPU training path is usable from random init, including checkpoint round-trip and key metrics.

**Checkpoint / eval strategy for smoke** (override official intervals which are too sparse):
- Force `save_step_interval: 10` and `eval_step_interval: 10` (or equivalent CLI / config override).
- Run ~40 optimization steps.
- Explicitly test: save at step 20, resume from that checkpoint, continue to step 40, confirm state consistency.
- Log train loss, grad norm, and any available recurrent diagnostics every step.

Suggested practical overrides for smoke (single GPU, reduced batch if OOM):
- micro_batch_size reduced if needed (keep world batch logic via accumulation).
- Use official `scripts/train.py` + `runs/run_training.sh` pattern.

## Stage 2 — Short Training

Goal: Observe learning signal and stability on real text (after Stage 1 passes).

Monitor full metric set (see P1_C_METRICS.md).
Pre-define stability gates and stop conditions.
Fix data version, tokenizer, seeds, sequence order.

## Stage 3 — Reproduction Candidate

Only after Stage 1+2 pass. Propose longer run focusing on val loss vs recurrence depth, stability vs FLOPs, and whether depth yields repeatable gains.

No formal training in this stage of the plan.

All stages reuse official scripts/configs. No rewrite of Parcae core.
