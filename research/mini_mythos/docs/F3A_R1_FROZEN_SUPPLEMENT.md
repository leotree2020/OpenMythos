# F3-A-R1 Frozen Supplement

Status: **FROZEN BEFORE RUN**. Does not rewrite the original F3-A freeze.

## LR rule

The original freeze used warmup 1. Upstream `get_lr(0)` returns 0. The old STOP text said every optimizer step must change a parameter. That conflict is recorded here.

This round:

- `lr == 0`: no parameter change is expected.
- `lr > 0`: at least one expected parameter must change.

This is not a new model config. The old result is not rewritten.

## State

Seed once at the start of each path. Do not reset inside `step()`.

Compare full optimizer state, scheduler config, checkpoint step, and Torch / Python / NumPy RNG. Tensors use the original `1e-6` / `1e-5`. Counts, keys and RNG must be exact.

Corrupt checkpoint files must be rejected by the real loader or checker. A missing-key dictionary test is not enough.
