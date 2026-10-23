# P1-C GPU & Cost Analysis

**Status**: ESTIMATED / NOT TESTED. No actual GPU inventory performed in this environment.

## Current environment (this session)

- NOT TESTED: GPU presence, model, VRAM, CUDA version, driver, PyTorch build
- Disk / network limits unknown
- No cloud billing details available

## Rough estimates for parcae-small-140m (based on public config + typical values)

| Stage | Steps (approx) | Tokens (rough) | GPU-hours (single 40GB-class) | Notes |
|-------|----------------|----------------|-------------------------------|-------|
| 1 Smoke | 30–50 | ~ few M | < 0.1 | Micro-batch may need reduction |
| 2 Short | 500–2k | tens–hundreds M | 1–5 | Depends on throughput |
| 3 Candidate | 5k–20k+ | billions | 10–50+ | Full scale; user approval required |

- Param count: ~140M (VERIFIED from README table)
- Seq len: 2048, world batch 256 (VERIFIED)
- Checkpoint size: ESTIMATED 0.5–1 GB per full ckpt (bf16)
- FLOPs: ESTIMATED; use official telemetry or external profiler later

**Any paid GPU or training run requires explicit user approval.**
Multiple budget tiers can be prepared once real hardware is known.
