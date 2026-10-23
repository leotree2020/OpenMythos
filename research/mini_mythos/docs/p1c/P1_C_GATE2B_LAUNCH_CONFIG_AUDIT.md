# P1-C Gate 2B — Single-GPU Launch Configuration Audit

**Status**: Free static / CPU checks only. All items that require GPU or full environment are NOT TESTED.

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## 1. Sequence length consistency

From `scripts/train.py`:
```python
if not cfg.ignore_block_size_mismatch:
    assert cfg.block_size == cfg.model_config.block_size, "cfg.block_size must match config.block_size"
```

- `cfg.block_size` is the training sequence length.
- `cfg.model_config.block_size` comes from the model definition (default 2048 for parcae-small-140m).
- For a short-sequence experiment, **both** must be overridden at launch time, **or** `ignore_block_size_mismatch: true` must be set.
- Recommended: set both to the same short value (e.g. 128) via model_overwrite / CLI override. Do not modify Parcae model source.

**Static check**: logic confirmed from source. Runtime override application **NOT TESTED**.

## 2. Synthetic train + val data (rngds)

`RandomTokensDataset` (debug path):
- Requires a tokenizer only to obtain `vocab_size`.
- Generates random tokens of length `block_size`.
- Does not use real text or special-token packing.
- Checkpoint state: simple; does not invoke `ParquetStreamPure` distributed CUDA gather.

**Minimal config requirement**:
- Both `train_data` and `val_data` must be non-empty lists of type `rngds`.
- Empty `val_data` risks failure at the end of training when evaluation is attempted.

**Static check**: source path confirmed. Actual dataloader construction **NOT TESTED**.

## 3. Single-GPU DDP and save/resume

- Prefer single-GPU DDP (`torchrun --nproc_per_node=1` or `run_training.sh ... 1`) so that `torch.distributed` is initialized.
- This reduces risk when any residual dataset state save is invoked.
- `rngds` itself bypasses `ParquetStreamPure`, further lowering risk.
- First `optimizer_step == 0` skips `optimizer.step()`.
- `save_step_interval` counts microbatch / fabric steps, not pure optimizer steps.
- Initial model save (if enabled) occurs before any updates.

**Static check**: behavior confirmed from prior source reads. Runtime save/resume **NOT TESTED**.

## 4. Required dependencies (NOT TESTED on target image)

- Lightning (pinned dev version)
- torchdata (StatefulDataLoader)
- WandB (offline mode recommended)
- Tokenizer files (small; license still BLOCKED)
- Matching torch + CUDA

## Free static checks performed

| Check | Result |
|-------|--------|
| block_size assert exists in train.py | PASS (source) |
| rngds path exists and uses RandomTokensDataset | PASS (source) |
| val_data referenced in train.py | PASS (source) |
| YAML override parses as valid YAML | PASS (see companion file) |
| Official train entry starts on CPU | NOT TESTED (blocked by CUDA check) |
| Single-GPU DDP process group | NOT TESTED |
| Checkpoint save/resume | NOT TESTED |
| MuonAdamW runtime grouping | NOT TESTED |
