# P1-C Gate 2A — Checkpoint / Resume Integrity Audit (Revised)

**Static analysis. No checkpoint created or loaded. Runtime behavior NOT TESTED.**

## ParquetStreamPure distributed dependency

`recpre/huggingface_dataset.py` `ParquetStreamPure.state_dict` / `load_state_dict`:

- Creates a CUDA tensor: `torch.tensor([...], device="cuda")`
- Calls `torch.distributed.all_gather` and `torch.distributed.get_world_size()` / `get_rank()`

### Implications for single GPU

| Strategy | Static observation | Risk |
|----------|--------------------|------|
| `fabric_strategy=single` | May not initialize a full process group | **Potential failure** if dataset state save/load is invoked |
| Single-GPU DDP (`torchrun --nproc_per_node=1`) | Initializes process group (world size 1) | Lower risk; all_gather on 1 rank should succeed |
| `rngds` / synthetic | Bypasses ParquetStreamPure | Avoids this path |

**Static conclusion**: Using `fabric_strategy=single` with a real `pqds-pure` dataset carries a non-zero risk of checkpoint failure due to uninitialized distributed group. Single-GPU DDP is safer for the upstream checkpoint path. Runtime confirmation **NOT TESTED**.

## Other known risks (unchanged)

1. Resume may retain newly created LR scheduler instead of full checkpointed scheduler state.
2. Extra batch skip on resume; correctness depends on saved cursor.
3. `save_step_interval` counts microbatch / fabric steps, not pure optimizer steps.

## Future verification requirements

Record on any future run:
- microbatch_step
- optimizer_step
- actual parameter update count
- checkpoint save location / step
- post-resume next data batch identity
- LR value after resume

**Do not modify upstream checkpoint code.**
