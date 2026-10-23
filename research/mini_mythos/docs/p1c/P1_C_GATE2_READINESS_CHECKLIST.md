# P1-C Gate 2 Readiness Checklist

**Status: All items NOT TESTED / NOT STARTED. Do not fill PASS without evidence.**

This checklist defines what must be verified before any Stage 1 training smoke that uses the official training entry point.

## A. Official Parcae Training Entry & Dependencies

- **Goal**: Confirm `scripts/train.py` (or equivalent) launches with pinned commit and required packages.
- **Code path**: `parcae/scripts/train.py`, launch configs.
- **Preconditions**: Clean install of pinned Parcae + matching torch/lightning.
- **Evidence**: Successful dry-run log, version freeze.
- **PASS/FAIL**: Process starts, config loads, no import errors.
- **Risk**: Missing private deps or version conflicts.
- **Paid GPU**: No (CPU import check possible).

## B. MuonAdamW Correctness

- **Goal**: Verify official MuonAdamW is used and produces finite updates.
- **Code path**: Upstream optimizer implementation used by train.py.
- **Preconditions**: Official training entry available.
- **Evidence**: Optimizer class name in log, finite params after steps.
- **PASS/FAIL**: Official class instantiated; no NaN.
- **Risk**: Smoke used AdamW; mismatch possible.
- **Paid GPU**: Yes (small run).

## C. Real Next-token Training Objective

- **Goal**: Confirm labels are properly shifted for next-token prediction.
- **Code path**: Data collator / loss call in official train loop.
- **Preconditions**: Official dataloader or equivalent.
- **Evidence**: Label shape/alignment inspection, loss comparable to expected range.
- **PASS/FAIL**: Shift confirmed; loss finite and decreasing on real or properly synthetic data.
- **Risk**: Current smoke used unshifted clone.
- **Paid GPU**: Optional for pure inspection; preferred for short run.

## D. Checkpoint Save / Load / Resume

- **Goal**: Save after N steps, resume, continue with matching state.
- **Code path**: Lightning Fabric checkpoint helpers in train.py.
- **Preconditions**: Official training entry.
- **Evidence**: Checkpoint files, resume log, parameter/optimizer/RNG consistency checks.
- **PASS/FAIL**: Resume produces identical next-step loss/grads within tolerance.
- **Risk**: Incomplete state save.
- **Paid GPU**: Yes.

## E. Actual Sampled Recurrence Depth Recording

- **Goal**: Capture real n/k sampled depths (not just config means).
- **Code path**: `iterate_forward` / monitoring hooks.
- **Preconditions**: Model forward with monitoring or instrumentation.
- **Evidence**: Logged mean/max no-grad and with-grad steps per batch.
- **PASS/FAIL**: Values recorded and consistent with sampling scheme.
- **Risk**: Currently NOT MEASURED.
- **Paid GPU**: Yes (or CPU if model fits).

## F. Multi-seed Training Stability

- **Goal**: At least 2–3 seeds show stable finite training.
- **Code path**: Official train with different seeds.
- **Preconditions**: Official entry + short steps.
- **Evidence**: Loss curves, grad norms per seed.
- **PASS/FAIL**: All seeds finite; no divergence.
- **Risk**: Seed sensitivity unknown.
- **Paid GPU**: Yes.

## G. FLOPs / Memory / Throughput / Cost Measurement

- **Goal**: Measure real tokens/sec, peak VRAM, and derived GPU-hours/cost on target config.
- **Code path**: Smoke or official train with profiling.
- **Preconditions**: Target GPU + representative batch/seq.
- **Evidence**: JSON with measured numbers (not estimated).
- **PASS/FAIL**: Numbers recorded; cost within budget.
- **Risk**: Smoke numbers not transferable.
- **Paid GPU**: Yes.

## H. Real Dataset & Tokenizer Source / License / Integrity

- **Goal**: Confirm FineWeb-Edu shuffled and Parcae tokenizer availability, license, and integrity.
- **Code path**: Upstream download scripts / HF repos.
- **Preconditions**: Network + storage approval.
- **Evidence**: License text, checksums, sample load.
- **PASS/FAIL**: License acceptable; data loads; no integrity errors.
- **Risk**: Currently BLOCKED pending approval.
- **Paid GPU**: No.

**Gate 2 may not start until A–H are addressed or explicitly deferred with approval.**
