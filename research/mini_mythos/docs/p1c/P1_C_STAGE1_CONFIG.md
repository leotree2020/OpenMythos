# P1-C Stage 1 Single-GPU Configuration

**Purpose**: Concrete, reproducible smoke configuration derived from official `parcae-small-140m.yaml`.

## Core hyperparameters (single GPU)

- sequence length (`block_size`): 2048
- micro_batch_size: 4 (start small to avoid OOM; increase if VRAM allows)
- gradient accumulation steps: 64 (so effective / world batch ≈ 256, matching official)
- effective tokens / step: 256 × 2048 = 524,288 (target)
- optimizer: MuonAdamW (official settings)
- precision: bf16-mixed
- mean_recurrence: 8, mean_backprop_depth: 4 (official)
- seed: 42 (official)

## Checkpoint strategy for smoke

- Override `save_step_interval: 10`
- Override `eval_step_interval: 10`
- Run 40 optimizer steps
- At step 20: force checkpoint
- Resume from that checkpoint and continue to step 40

## Resume consistency checks (must all PASS)

After resume:
1. Model parameters match within 1e-5 relative tolerance (or exact for bf16).
2. MuonAdamW optimizer state (momentum buffers, etc.) restored.
3. LR scheduler state restored.
4. RNG state (torch, numpy, python) restored so next samples match.
5. Depth sampling state (poisson-truncated-full) produces identical next depths.
6. Data loader cursor / next batch identical.
7. Loss and grad norm continue the previous trajectory (finite).

Failure on any item → Stage 1 FAIL.

## Storage

- Checkpoint expected size: ESTIMATED 0.5–1 GB (bf16).
- Logs + metrics: small.

This config is for planning only. Actual launch requires GPU authorization.
