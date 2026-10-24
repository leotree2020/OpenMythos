# Condition-Constrained Fix Review (not applied to Parcae)

## When the extra skip is wrong

Verified for rngds-style datasets whose `state_dict`/`load_state_dict` only track `idx`,
and whose iterator creation already applies that state:

- Multi-resume at 8 and 12: 20/20 match without extra skip.
- Batch sizes 1, 2, 4, 8: match without extra skip.
- Official `RandomTokensDataset` methods (small table, recovery logic unchanged): match.

## When it is unknown

`ParquetStreamPure.state_dict` hardcodes CUDA tensors and `torch.distributed.all_gather`.
On this CPU environment it is **BLOCKED**. Do not assume the same skip rule.

## Proposed constraint

```python
train_iterator = iter(state["train_dataloader"])
if state["microbatch_step"] > 0:
    ds = state["train_dataloader"].dataset
    # rngds-style: iterator creation already restored idx; do not skip again.
    if not (hasattr(ds, "idx") and hasattr(ds, "state_dict") and "idx" in ds.state_dict()):
        next(train_iterator, None)
```

This keeps the skip for datasets that do not expose a simple `idx` state,
until those paths are verified.

## Not done

- Patch not applied to Parcae.
- No Draft PR yet (waiting for full Gate 2.1 sign-off).
- No GPU.
