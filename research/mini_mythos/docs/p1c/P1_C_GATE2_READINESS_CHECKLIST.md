# P1-C Gate 2 Readiness Checklist

**Status: All experiment items NOT TESTED. Prerequisites must be completed before any paid GPU is launched.**

## Pre-GPU Prerequisites (must be satisfied before launching paid compute)

- Official training entry (`scripts/train.py` or equivalent) confirmed importable and configurable on CPU or free environment.
- Required dependencies listed and installable without secret or unlicensed components.
- Budget re-measurement plan defined for the exact target configuration (batch, seq, optimizer).
- Cost-control procedure confirmed (manual terminate + delete unused storage; alerts are not hard stops).
- Dataset / Tokenizer license and acquisition plan approved (or explicitly deferred to synthetic-only).
- All of the above remain **NOT COMPLETED** until evidenced.

## Experiment Acceptance Items (each requires its own run and evidence; currently NOT TESTED)

### A. Official Parcae Training Entry & Dependencies
- **Goal**: Confirm official training entry launches with pinned commit.
- **Code path**: `parcae/scripts/train.py`, launch configs.
- **Preconditions**: Clean install of pinned Parcae.
- **Evidence**: Successful start log, version freeze.
- **PASS/FAIL**: Process starts, config loads, no import errors.
- **Risk**: Missing deps.
- **Paid GPU**: No for import check; Yes for actual steps.

### B. MuonAdamW Correctness
- **Goal**: Verify official MuonAdamW produces finite updates.
- **Code path**: Upstream optimizer used by train.py.
- **Preconditions**: Official entry available.
- **Evidence**: Optimizer class name in log, finite params.
- **PASS/FAIL**: Official class used; no NaN.
- **Risk**: Smoke used AdamW.
- **Paid GPU**: Yes.

### C. Real Next-token Training Objective
- **Goal**: Confirm labels are properly shifted.
- **Code path**: Official data collator / loss.
- **Preconditions**: Official dataloader or equivalent.
- **Evidence**: Label alignment inspection, finite decreasing loss.
- **PASS/FAIL**: Shift confirmed; loss finite.
- **Risk**: Smoke used unshifted clone.
- **Paid GPU**: Preferred.

### D. Checkpoint Save / Load / Resume
- **Goal**: Save after N steps, resume, continue with matching state.
- **Code path**: Lightning Fabric checkpoint helpers.
- **Preconditions**: Official training entry.
- **Evidence**: Checkpoint files; resume log showing:
  - Model weights match within tolerance
  - Optimizer state (MuonAdamW or configured) restored
  - LR scheduler state restored
  - RNG state (torch / numpy / python) restored
  - Recurrence depth sampling state produces identical next samples
  - Data loader position / next batch identical
- **PASS/FAIL**: All of the above hold; next-step loss/grads continue consistently.
- **Risk**: Incomplete state save.
- **Paid GPU**: Yes.

### E. Actual Sampled Recurrence Depth Recording
- **Goal**: Capture real n/k sampled depths.
- **Code path**: `iterate_forward` / monitoring.
- **Preconditions**: Model forward with instrumentation.
- **Evidence**: Logged mean/max no-grad and with-grad steps.
- **PASS/FAIL**: Values recorded and consistent with scheme.
- **Risk**: Currently NOT MEASURED.
- **Paid GPU**: Yes.

### F. Multi-seed Training Stability
- **Goal**: ≥2 seeds show stable finite training.
- **Code path**: Official train, different seeds.
- **Preconditions**: Official entry + short steps.
- **Evidence**: Loss / grad norms per seed.
- **PASS/FAIL**: All seeds finite; no divergence.
- **Risk**: Seed sensitivity unknown.
- **Paid GPU**: Yes.

### G. FLOPs / Memory / Throughput / Cost Measurement
- **Goal**: Measure real tokens/sec, peak VRAM, GPU-hours on **target** config.
- **Code path**: Official train or instrumented run.
- **Preconditions**: Target GPU + representative batch/seq.
- **Evidence**: Measured JSON (not estimated or extrapolated from Gate 1 smoke).
- **PASS/FAIL**: Numbers recorded; cost within budget.
- **Risk**: Smoke numbers not transferable.
- **Paid GPU**: Yes.

### H. Real Dataset & Tokenizer Source / License / Integrity
- **Goal**: Confirm FineWeb-Edu shuffled and Parcae tokenizer availability, license, integrity.
- **Code path**: Upstream download scripts / HF repos.
- **Preconditions**: Network + storage approval.
- **Evidence**: License text, checksums, sample load.
- **PASS/FAIL**: License acceptable; data loads.
- **Risk**: Currently BLOCKED.
- **Paid GPU**: No.

**No item above is PASS. Gate 2 may not start until prerequisites are met and each experiment item is separately authorized and evidenced.**
