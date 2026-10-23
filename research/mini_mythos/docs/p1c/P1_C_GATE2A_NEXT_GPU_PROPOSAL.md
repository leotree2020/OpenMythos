# P1-C Gate 2A — Next Minimal Official Training Verification Proposal

**Not authorized. Not executed. Proposal only.**

## Goal

Minimal official-entry smoke that verifies:
1. Official `scripts/train.py` starts on single GPU.
2. MuonAdamW is instantiated and produces finite updates.
3. Next-token (shifted) loss is used.
4. At least one checkpoint save + resume cycle succeeds with state consistency.

## Proposed config overrides (launch-time only)

- `NUM_GPUS=1`
- `fabric_strategy: single` (or ddp with 1 device)
- `micro_batch_size: 2`
- `world_batch_size: 8` → gradient_accumulation_steps = 4
- `block_size: 128` (or 256) for memory safety
- `max_steps: 8` (or exit_at_step)
- `save_step_interval: 4` (microbatch-aware; verify actual save cadence)
- `logger_name` + `WANDB_MODE=offline`
- Synthetic or tiny local parquet if full data still BLOCKED
- `optimizer: MuonAdamW` (official)

## Measurement plan

- Peak allocated / reserved VRAM (`nvidia-smi` + torch)
- Step time with and without diagnostics
- Actual sampled recurrence (if monitoring enabled)
- Tokens/sec **measured on this run only** — do **not** reuse Gate 1 1178.2 tokens/s
- GPU-hours and JPY cost from actual runtime

## Cost control

- Hard cumulative cap remains **¥5,000**.
- User must manually terminate Pod and delete unused storage.
- Billing alerts ≠ hard stop.
- Prefer smallest step count that still exercises save/resume (e.g., 8 optimizer steps).

## Prerequisites before launch

- Resolve data path mismatch or use synthetic.
- Confirm MuonAdamW import and grouping on the target environment.
- Confirm WandB offline or alternative logger.
- Confirm lightning/torch compatibility on the A100 image.

**This proposal does not authorize execution. Gate 2 remains blocked until ChatGPT review and user approval.**
