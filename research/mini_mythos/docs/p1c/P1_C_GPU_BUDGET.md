# P1-C GPU & Cost Analysis

**Status**: ESTIMATED / NOT TESTED. No actual GPU inventory or training performed.

## Current environment (this session)

- NOT TESTED: GPU presence, model, VRAM, CUDA version, driver, PyTorch build.
- Env probe script runs safely without torch (see tests).
- Disk / network / cloud billing unknown.

## Effective batch & token math (VERIFIED from config)

From `parcae-small-140m.yaml`:
- world_batch_size: 256
- micro_batch_size: 32
- block_size: 2048
- Effective tokens per optimizer step = 256 × 2048 = **524,288** (VERIFIED arithmetic)

## Rough ESTIMATED budgets (single ~40 GB-class GPU, typical throughput assumptions)

| Stage | Steps | Tokens (ESTIMATED) | GPU-hours (ESTIMATED) | FLOPs proxy (ESTIMATED, 6×params×tokens) | Notes |
|-------|-------|--------------------|-----------------------|------------------------------------------|-------|
| 1 Smoke | 40 | ~21 M | < 0.1 | ~1.8e16 | Force frequent ckpt; may reduce micro-batch |
| 2 Short | 1,000 | ~524 M | 1–3 | ~4.4e17 | Depends on measured tok/s |
| 3 Candidate | 10,000 | ~5.2 B | 10–40 | ~4.4e18 | Full scale; user approval required |

- Param count: ~140 M (VERIFIED from README table)
- Checkpoint size: ESTIMATED 0.5–1 GB per full ckpt (bf16)
- Throughput assumptions are typical literature values, **not measured**.

**Any paid GPU or training run requires explicit user approval.**
