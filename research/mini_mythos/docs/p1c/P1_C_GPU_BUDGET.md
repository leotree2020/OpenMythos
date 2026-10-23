# P1-C GPU & Cost Analysis (Revised)

**Status**: ESTIMATED / NOT TESTED. No measured throughput or GPU inventory.

## Recurrent FLOPs adjustment (ESTIMATED)

Standard Transformer proxy `6 × params × tokens` undercounts Parcae because the recurrent core is executed multiple times.

From pinned upstream config (and HF model card):
- `mean_recurrence`: 8
- `mean_backprop_depth`: 4
- Recurrent block layers: 2 (of total ~6 effective layers)

Approximate multiplier for the recurrent portion (ESTIMATED):
- Forward passes over core: ~mean_recurrence
- Backward passes over core: ~mean_backprop_depth
- Prelude + Coda: once each

Conservative training FLOPs range (ESTIMATED):
- Lower bound: ~2–3× the plain Transformer proxy (if only partial core is recurrent)
- Upper bound: ~4–6× (full core looped at mean_recurrence with backprop depth)

Exact multiplier requires source-level FLOP counting or profiler (NOT TESTED).

## Token math (VERIFIED arithmetic)

world_batch_size=256, block_size=2048 → **524,288 tokens / optimizer step**.

## Stage budgets (ESTIMATED ranges only)

| Stage | Steps | Tokens | Training FLOPs range (ESTIMATED) | GPU-hours range (ESTIMATED)* |
|-------|-------|--------|----------------------------------|------------------------------|
| 1 Smoke | 40 | ~21 M | 3.6e16 – 1.1e17 | 0.05 – 0.5 |
| 2 Short | 1,000 | ~524 M | 8.8e17 – 2.6e18 | 1 – 8 |
| 3 Candidate | 10,000 | ~5.2 B | 8.8e18 – 2.6e19 | 10 – 80 |

*GPU-hours ranges assume typical 40 GB-class single-GPU throughput of 5k–50k tokens/s. **Actual time requires measurement** on the target hardware. No fixed claim is made.

Measurement plan: once Stage 1 is authorized, record tokens/sec and peak memory on the real GPU; then revise ranges.

Any paid resource requires separate approval.
