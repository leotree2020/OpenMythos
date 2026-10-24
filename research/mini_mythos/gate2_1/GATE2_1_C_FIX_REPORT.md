# Gate 2.1-C Conditional Patch Report

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
Branch: `mini-mythos-p1c-gate2-dataloader-continuity`
Base includes Gate 2 baseline `e37cfa376b58d25e409ab761b61f8aba33f7a027`.

## Patch

`patch_resume_skip.py` — `create_train_iterator()`:

- Creates the iterator (which applies StatefulDataLoader dataset state).
- If `microbatch_step > 0` and the dataset is **not** `RandomTokensDataset`, performs the original extra `next()`.
- If the dataset **is** `RandomTokensDataset`, omits the extra skip.
- Judgment uses `isinstance(..., RandomTokensDataset)`, not an arbitrary `idx` field.

Native Parcae is not modified. The patch lives in the OpenMythos research directory and was verified against an isolated Parcae checkout's `RandomTokensDataset` methods.

## Results (CPU)

| Test | Status |
|------|--------|
| Chained resume at 8 then 12 (20/20) | PASS |
| batch size 1 / 2 / 4 / 8 | PASS |
| No double consume / no re-init | PASS |
| Unsupported dataset keeps skip | PASS |
| Prior A/B continuity | PASS |
| ParquetStreamPure | BLOCKED |

Summary: PASS=8, FAIL=0, BLOCKED=1, NOT TESTED=0.

## Side effects checked

- After load+iter, `idx` equals the saved value (no re-init to 0).
- First consumed batch advances `idx` by exactly `batch_size` (no double consume).
- Non-RandomTokensDataset still receives the extra skip.

## Not claimed

- ParquetStreamPure safety is not claimed (BLOCKED: CUDA / distributed / seed constraints).
- No GPU numerical equivalence.
- No PR created. PR #6 not merged.
