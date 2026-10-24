# Minimal Fix Candidate (not applied to Parcae)

## Evidence-based proposal

For rngds + StatefulDataLoader, omit the extra `next()` on resume.

```python
train_iterator = iter(state["train_dataloader"])
# Do not call next() here for rngds; iterator creation already applies dataset_state.
```

## Why not delete unconditionally

The comment claims the skip fixes a StatefulDataLoader off-by-one.
CPU evidence shows that for this dataset the skip **creates** the off-by-one.
ParquetStreamPure and other datasets are **NOT TESTED**.
A safe patch should be dataset-conditional or state-driven until those are verified.

## Not done

- Parcae source not modified.
- No GPU numerical equivalence run.
- PR #6 not merged.
