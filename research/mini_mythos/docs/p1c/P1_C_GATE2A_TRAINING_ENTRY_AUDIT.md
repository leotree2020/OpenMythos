# P1-C Gate 2A — Official Training Entry Audit

**Status**: Static analysis only. No claim that the official training entry has been successfully launched on CPU or GPU.

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## Key files examined

- `runs/run_training.sh`
- `scripts/train.py` (partial, via prior reads + structure)
- `launch_configs/parcae-small-140m.yaml`
- `recpre/settings.py`
- `pyproject.toml`

## Findings

### Single-GPU overrides (do not modify official YAML)

Official `run_training.sh` defaults to `NUM_GPUS=8` and calls `torchrun --nproc_per_node=${NUM_GPUS}`.

For single GPU, override at launch:
- `NUM_GPUS=1` (or call `torchrun --nproc_per_node=1`)
- `fabric_strategy: single` or keep `ddp` with 1 device (SingleDeviceStrategy is supported in train.py)
- `world_batch_size` must be divisible by `micro_batch_size * devices * num_nodes`. For 1 GPU: set `world_batch_size = micro_batch_size * gradient_accumulation_steps`.
- Example minimal: `micro_batch_size: 2`, `world_batch_size: 8` → accumulation = 4.

`settings.py` derives `devices` from `torch.cuda.device_count()` or SLURM env. On a pure CPU machine this will be 0 → batch math fails. **CPU cannot fully instantiate CLISettings without mocking device count.**

### What can be done on CPU vs requires GPU

| Check | CPU possible? | Notes |
|-------|---------------|-------|
| Import train.py | NO | Early `torch.cuda._device_count_*` check raises if no GPU |
| Parse YAML / CLISettings (with mock) | Partial | Device count hard dependency |
| Model construct (small) | Possible if torch+cuda absent path patched | Not official |
| Forward/backward | GPU preferred | Gate 1 already did synthetic |
| Full train loop | GPU only | |

**BLOCKED on pure CPU**: Official `scripts/train.py` aborts at module level if no CUDA device is detected.

### WandB

`setup_fabric` requires `WandbLogger` when `logger_name=wandb` (default).
- Offline mode: `WANDB_MODE=offline` (no token required).
- Alternative: temporarily set `logger_name` to a non-wandb value if supported, or provide a dummy logger. Do **not** expose tokens.
- Status: **NOT TESTED** on this environment.

### Dependency risks (see matrix doc)

- `lightning==2.3.0.dev20240328` (dev pin) vs current PyTorch 2.8 used in Gate 1.
- `axonn` git pin.
- `torchdata` StatefulDataLoader.
- `numpy<2.0`.

## Conclusion

Single-GPU path is feasible via launch overrides, but official entry is GPU-gated at import. No CPU launch evidence exists. Do not claim successful official training start.
