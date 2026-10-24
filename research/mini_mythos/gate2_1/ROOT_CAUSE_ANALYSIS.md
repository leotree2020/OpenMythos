# Gate 2.1 Root Cause Analysis

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## Observed

In `scripts/train.py` after resume:

```python
train_iterator = iter(state["train_dataloader"])
if state["microbatch_step"] > 0:
    next(train_iterator, None)
```

## Mechanism (verified on CPU)

`RandomTokensDataset` yields from `self.idx` and increments `idx` per row.
`StatefulDataLoader.state_dict()` stores `dataset_state` (including `idx`).

On a fresh loader:
1. `load_state_dict` does **not** immediately set `dataset.idx`.
2. Creating the iterator applies `dataset_state`; `idx` becomes the saved value (correct resume point).
3. The extra `next()` then consumes one more batch, advancing `idx` by `batch_size`.

Result: the first training batch after resume is the batch **after** the one that should have been next.

## Evidence

| Check | Result |
|-------|--------|
| idx after 12 batches (batch=2) | 24 |
| idx after load (before iter) | 0 |
| idx after iter() | 24 (correct) |
| idx after extra next() | 26 |
| Control B first batch | matches continuous A[13] (batch 14) |
| Candidate C first batch | matches continuous A[12] (batch 13) |
| B match A[12:20] | 0/8 |
| C match A[12:20] | 8/8 |
| B match A[13:20] | 7/7 |

## Conclusion

**Verified:** the extra `next()` is the cause of the one-batch skip for this rngds + StatefulDataLoader combination.
**Not verified:** whether the same skip is required for ParquetStreamPure or other datasets.
