# Gate 2.2 ParquetStreamPure Audit

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
OpenMythos HEAD at start: `5640feb44f6c5f1225ec919007394399e74ee7e5`
Environment: Python 3.11.2 / PyTorch 2.14.1+cpu / torchdata 0.11.0+cpu

## Root cause of CPU block

`ParquetStreamPure.state_dict()`:

```python
local_state = torch.tensor([...], device="cuda")
gathered_states = [torch.zeros_like(local_state) for _ in range(torch.distributed.get_world_size())]
torch.distributed.all_gather(gathered_states, local_state)
```

`load_state_dict()` calls `torch.distributed.get_rank()`.

On this CPU: `Torch not compiled with CUDA enabled`. Distributed process group is also not initialized. Native path remains **BLOCKED**.

## Buffer logic (from source, not executed natively)

- `__iter__` yields via `self._state["buffer"].pop()` (LIFO).
- `state_dict` saves `buffer_remaining = len(buffer)` and `row_group_idx - 1`.
- `load_state_dict` re-reads the row group, increments `row_group_idx`, then truncates `buffer[:row_idx]`.

## What this round verified

- Test data is now 8 unique equal-length rows `[[10+i, 20+i, 30+i, 40+i] for i in range(8)]`.
- Negative offset-by-one SHA-256 check **PASS** (wrong offset differs).
- Native `state_dict` still **BLOCKED** (CUDA). Not counted as PASS.
- TEST ADAPTER / MOCK in `test_parquet_cpu_adapter.py` exercises buffer truncation + LIFO pop only. Explicitly not a native PASS.

## Unblock conditions

1. A CUDA-enabled PyTorch build, or
2. A single-process CPU path in Parcae that does not hardcode `device="cuda"` and `torch.distributed` (would be an upstream change; not done here).

## GPU numerical equivalence

Not in scope. Prerequisite: native Parquet or rngds resume integrated into `scripts/train.py`, then a controlled GPU run comparing continuous vs resumed weights/optimizer/RNG.
