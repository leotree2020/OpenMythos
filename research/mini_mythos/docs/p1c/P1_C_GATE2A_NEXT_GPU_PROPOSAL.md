# P1-C Gate 2A — Next Minimal Official Training Verification Proposal (Revised)

**Not authorized. Not executed. Proposal only.**

## Goal

Minimal official-entry verification on a single GPU that confirms:
1. Official `scripts/train.py` starts.
2. MuonAdamW is used with correct grouping (special recurrent params in AdamW).
3. Next-token (shifted) loss path is exercised.
4. At least one checkpoint save + resume succeeds (prefer single-GPU DDP to satisfy ParquetStreamPure distributed calls, or use synthetic/rngds to bypass).

## Suggested launch form (illustrative, not ready-to-run)

```bash
bash runs/run_training.sh <config-or-override> <run-name> <group> 1
```
Additional overrides (YAML or CLI) for micro-batch, world batch, sequence length, max_steps, save interval, offline logger, etc. must be determined and validated at runtime.

## Step and save strategy

- Prefer a small number of microbatch steps that produces at least 2–4 actual parameter updates (accounting for the skipped first optimizer step).
- Record microbatch_step, optimizer_step, and actual update count.
- Set `save_step_interval` low enough to trigger at least one save before exit (remember it is microbatch-oriented).
- After resume, compare next batch identity and LR.

## Measurement

- Peak allocated / reserved VRAM
- Step time (including first-step compile cost)
- Actual sampled recurrence if available
- Tokens/sec measured on **this** run only — do **not** reuse Gate 1 1178.2 tokens/s
- GPU-hours and JPY from actual wall time

## Cost control

- Cumulative hard cap remains ¥5,000.
- User must manually terminate Pod and delete unused storage.
- Billing alerts are not hard stops.

## Remaining prerequisites

- Data path mismatch resolved or synthetic/rngds used.
- WandB offline or alternative logger confirmed.
- Lightning/torch compatibility confirmed on target image.
- Single-GPU DDP vs single strategy decision made with checkpoint path in mind.

**This proposal does not authorize execution.**
