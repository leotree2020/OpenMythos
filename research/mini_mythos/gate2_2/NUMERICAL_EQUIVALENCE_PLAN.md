# Gate 2.2-A Numerical Equivalence Plan

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
Isolated patched train.py SHA-256: `05ca76f320530526648da658ff129e439fb7f3816f97e877f142202b1ebd408c`
patch_resume_skip.py SHA-256: `e46be93e508f34610fa0968cf6e83931861bee6f1d7c5c259aa6d2c89a09f578`

## Official train.py on CPU

**BLOCKED.** `scripts/train.py` hardcodes:
- `torch.autocast(device_type="cuda", ...)`
- `torch.cuda.get_device_name()` in fabric summary
- CUDA SDP / matmul flags

Full official training path cannot run on this CPU. Not replaced with a different architecture or optimizer.

## What was done

1. Isolated Parcae copy at the pinned commit; resume site patched to call the verified RandomTokensDataset rule (omit extra skip only for that class). Upstream not modified. Diff: `isolated_train_py.patch`.
2. Tiny real Parcae model forward/backward on CPU: works (loss finite, backward ok).
3. Model-level A/B/C probe (NOT official train.py):
   - Control A continuous
   - Control B resume without extra skip
   - Negative C resume with extra skip
   - Input SHA-256: B matches A tail; C does not (negative detects the skip).
   - Final weights: A vs B max_abs ≈ 0.003, 44 tensors differ. Cause: recurrence sampling RNG not restored in this probe. Not claimed as equivalence PASS.

## Tolerance

No tolerance applied to hide differences. Weight mismatch is reported as-is.

## GPU prerequisite

Official numerical equivalence requires a CUDA environment where `scripts/train.py` can run, with RNG/scheduler/optimizer state fully restored, then continuous vs resumed comparison.
