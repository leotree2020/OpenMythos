# P1-C Gate 2A — Official Training Entry Audit (Revised)

**Status**: Static analysis only. No claim of successful official training launch.

## Launch parameters

`runs/run_training.sh` signature:
```bash
./run_training.sh [CONFIG] [RUN_NAME] [RUN_GROUP] [NUM_GPUS]
```
`NUM_GPUS` is the **fourth positional argument** (default 8). It does **not** automatically read an external environment variable of the same name.

Correct single-GPU invocation form (illustrative only — **not** a ready-to-run command):
```bash
bash runs/run_training.sh launch_configs/parcae-small-140m.yaml my-run parcae 1
```
Additional YAML overrides or environment variables may still be required and have **not** been runtime-validated.

## Step counting

From `scripts/train.py` (prior inspection):
- On the first `optimizer_step == 0` the code **skips** `optimizer.step()`.
- Therefore `max_steps=8` does **not** equal 8 effective weight updates.
- Future experiments must record:
  - `microbatch_step`
  - `optimizer_step`
  - actual parameter update count
  - checkpoint save positions
  - post-resume data batch and LR

## CPU limitations

- `scripts/train.py` performs an early CUDA device check and **cannot** be fully started on pure CPU.
- `CLISettings.devices` can be influenced by environment variables (`SLURM_NTASKS_PER_NODE`, `LOCAL_WORLD_SIZE`) or `torch.cuda.device_count()`. It is not accurate to claim a mock is always required; however pure CPU remains blocked by the import-time check.
- Lightning / torchdata / AxoNN / WandB compatibility: **NOT TESTED**.
- Tokenizer license and real data layout: **BLOCKED**.

## torch.compile

First-step compilation cost is expected and is distinct from the Gate 1 pure-mechanism smoke (which did not exercise the official training entry or compile path).