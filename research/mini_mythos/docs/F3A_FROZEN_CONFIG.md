# F3-A Frozen Config

Status: **FROZEN BEFORE RUN**. Not a result.

## Scope

- Parcae `69284c13746e849104f738d6d1a347b1f457df76`
- AxoNN pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`
- CPU, float32, SDPA, 2/2/2, expected 247936 parameters
- Seed 42, batch 2, sequence 8, vocab 128
- Fixed `num_steps_pair=(0, 2)`
- Random init. No pretrained weights.
- Fixed input tensors. DataLoader resume is NOT TESTED.

## Optimizer

Upstream `get_optimizer("AdamW", use_apex_adamw=False, allow_fusion=False)`.

This is the native CPU-compatible AdamW path. It is **not** MuonAdamW. MuonAdamW remains NOT TESTED in this lifecycle.

- lr `1e-3`
- weight_decay `0.01`
- betas `(0.9, 0.95)`

## Scheduler

Upstream `get_lr_scheduler("linear", base_lr=1e-3, min_lr=1e-4, warmup_steps=1, cooldown_steps=0, max_steps=6)`.

LR is applied to every param group before each optimizer step, matching the train.py pattern. Resume must not step the scheduler twice.

## Steps

- Path A: 6 optimizer steps, no interrupt.
- Path B: 3 steps, save, new instances, load, steps 4–6.
- Interrupt is after completed step 3.

## Tolerances

- Loss abs `1e-6 + 1e-6 * max(abs)`
- Parameter and optimizer float tensors: abs `1e-6`, rel `1e-5`
- LR, step counts, keys and RNG: exact
- Do not relax after seeing results.

## STOP

NaN/Inf, missing gradient, optimizer does not change a parameter, resume mismatch, or pin mismatch stops the run. Do not claim `scripts/train.py` PASS.
