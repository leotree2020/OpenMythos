# Gate 2.1-C.1 Credibility Fixes

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
Branch: `mini-mythos-p1c-gate2-dataloader-continuity`

## What changed

1. **True chained resume.** S12 is taken from the loader that was resumed from S8 and continued, not from a fresh loader that read 12 batches.
2. **Direct patch call.** All resume iterators are created by `create_train_iterator()` imported from `patch_resume_skip.py`. Positive and negative assertions cover that function.
3. **ParquetStreamPure classification.** Constructed with the required keyword arguments. Construction failure → FAIL. CUDA or uninitialized distributed → BLOCKED with the specific exception. Success would be judged on continuity.

## Results (CPU)

| Test | Status |
|------|--------|
| True chained resume S8→S12→20 | PASS (8/8 + 4/4 + 8/8) |
| patch fn positive (rngds, no skip) | PASS |
| patch fn negative (other, keeps skip) | PASS |
| batch size 1/2/4/8 via patch fn | PASS |
| ParquetStreamPure | BLOCKED (CUDA in state_dict) |

Summary: PASS=7, FAIL=0, BLOCKED=1, NOT TESTED=0.

## Verified

- rngds path: no duplicate, no skip, chained state transfer works.
- Patch function is the one under test.
- Non-RandomTokensDataset still receives the extra skip.

## Still blocked

- ParquetStreamPure `state_dict` requires CUDA (`Torch not compiled with CUDA enabled`). Continuity on that path is not claimed.

## Not done

- Native Parcae not modified.
- No GPU. No PR. PR #6 not merged.
