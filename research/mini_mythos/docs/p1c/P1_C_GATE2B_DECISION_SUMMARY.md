# P1-C Gate 2B — Decision Summary: Enter Minimal Official Training Verification?

**Purpose**: Provide a concise, auditable summary for ChatGPT review.  
**Status**: Recommendation only. No GPU launched, no training executed, PR remains Draft.

## Current state

- Gate 1 mechanism smoke (A100, synthetic, AdamW): **PASS**.
- Gate 2A/2B static audits: completed across multiple rounds.
- Official training entry, MuonAdamW runtime behavior, next-token objective, Checkpoint resume, real data/Tokenizer: **NOT TESTED** or **BLOCKED**.

## What static work has already closed

- Single-GPU launch form and batch arithmetic.
- block_size consistency requirement.
- Muon/AdamW parameter grouping rules (including special recurrent params).
- rngds train+val requirement and approximate host-RAM cost (~984 MiB).
- Save condition (`not is_accumulating`) and first-step skip of `optimizer.step()`.
- ParquetStreamPure distributed dependency vs rngds bypass.

## Remaining uncertainties that only a real run can close

1. Does the official `scripts/train.py` entry start on single-GPU DDP with the proposed overrides?
2. Is MuonAdamW actually instantiated and producing finite updates?
3. Does a short checkpoint save + resume restore model, optimizer, and rngds cursor correctly (accounting for any extra batch skip)?
4. What are the real VRAM, step time, and compile cost on this configuration?

## Recommendation

Authorize **one** controlled, minimal official-entry verification under the existing hard constraints:

- Single GPU (DDP with 1 process).
- Official Parcae commit and MuonAdamW.
- rngds train + val only (no large data download).
- Short step count that produces a few actual parameter updates and at least one save/resume cycle.
- Offline logger, no core model changes.
- Hard cumulative budget cap ¥5,000; user manually terminates Pod and cleans storage.
- Explicit success criteria: process starts, finite loss/updates, checkpoint written and reloads without crash, key counters logged.

If this run fails, the failure evidence is itself useful and further static polishing is unlikely to help. If it passes, Gate 2 can move from planning to measured results.

## What this does **not** authorize

- Real dataset download.
- Language-learning claims.
- Multi-seed or full-stage training.
- Architecture changes.
- PR merge.

**Decision requested**: Approve or reject the single minimal official-entry verification described above.
