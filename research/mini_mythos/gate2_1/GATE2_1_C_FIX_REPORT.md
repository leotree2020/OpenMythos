# Gate 2.1 Final Report

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
Branch: `mini-mythos-p1c-gate2-dataloader-continuity`

## Data continuity verified (CPU, rngds)

| Suite | Result |
|-------|--------|
| Gate 2.1-A continuity | PASS (exit 0) |
| Gate 2.1-B multi-resume / batch sizes / official methods | PASS (exit 0) |
| Gate 2.1-C/C.1 true chained resume via `create_train_iterator` | PASS (exit 0) |
| batch size 1/2/4/8 | PASS |
| non-RandomTokensDataset keeps skip | PASS |

rngds path: no duplicate, no skip. S12 comes from the loader resumed from S8.

## Full training path not yet integrated

- Conditional patch is a research candidate in OpenMythos. Native Parcae is not modified.
- ParquetStreamPure remains BLOCKED (`Torch not compiled with CUDA enabled` in `state_dict`). Success branch now compares SHA-256 of resumed samples against uninterrupted samples 4–6; it was not reached.
- GPU numerical equivalence not verified.
- Patch is not wired into `scripts/train.py`.

## Not done

- No GPU rental.
- No model / optimizer / architecture changes.
- PR #6 not merged.
- This Draft PR must stay Draft.
