# P1-C Minimal Training Environment Unlock — Results

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## Task 1 — Alternative Test Tokenizer

**Status: PASS** (generation and load)

- Source: self-authored synthetic corpus written to parquet with `text` column.
- Command: upstream `scripts/tok_train.py --vocab-size 32768 --max-chars 500000 --doc-cap 2000`
- Actual vocab size: **489** (not 32768; corpus too small for full target).
- Special tokens (raw tokenizers library): `<|bos|>=0`, `<|eos|>=1`, `<|pad|>=2`.
- Encode → Decode: PASS.
- `parcae_lm.tokenizer.Tokenizer.from_directory`: loads processor, but `bos_id`/`eos_id`/`pad_id` are `None`.
  - train.py falls back to `pad_id=0` when None. Acceptable for minimal path, but not identical to a fully configured official tokenizer.
- SHA-256 of generated `tokenizer.json`: `e061ba38cf7585fbd82db3f8914446fdfbfbad5bbf8ed27c79620b3b37dd189b`
- Marked **ALTERNATIVE TEST TOKENIZER**. Official HF tokenizer remains BLOCKED (no license).

## Task 2 — Config Parsing

**Status: PASS** (real CLISettings construction)

With `LOCAL_WORLD_SIZE=1` and DataEntry objects:
- CLISettings constructed successfully.
- `block_size=128`, `model_overwrite.block_size=128`.
- `devices=1`, `num_nodes=1`, `gradient_accumulation_steps=4`.
- `optimizer=MuonAdamW`, `fabric_strategy=ddp`.
- `train_data`/`val_data` both `rngds`.
- `max_steps=6`, `save_step_interval=2`.
- `logger_name=wandb` (offline mode is an env var, not a YAML field).

Proposed YAML alone is not accepted until `data_config` entries are DataEntry instances and device count is non-zero.

## Task 3 — Dependency Imports

**Status: PASS** (this environment)

| Module | Version / result |
|--------|------------------|
| torch | 2.14.1+cpu |
| lightning | 2.3.0.dev20240328 |
| torchdata.stateful_dataloader | import ok |
| wandb | 0.31.0 |
| transformers | 5.20.2 |
| tokenizers | 0.23.3 |
| parcae_lm | import ok |
| recpre | import ok |

Note: torch 2.14.1+cpu differs from the official Docker base image.

## Task 4 — Launch Plan

**Status: NOT TESTED** (no GPU execution)

Executable config: `P1_C_EXECUTABLE_LAUNCH.yaml`

```bash
export LOCAL_WORLD_SIZE=1
export WANDB_MODE=offline
# fill tokenizer_path first
bash runs/run_training.sh research/mini_mythos/docs/p1c/P1_C_EXECUTABLE_LAUNCH.yaml p1c-min-train group 1
```

- Expected parameter updates: max_steps=6, but first optimizer_step skips step() → at most 5 updates.
- Saves: only when not is_accumulating and microbatch % 2 == 0 → multiples of 4.
- Stop: user must manually terminate; no hard stop in script.
- Logs: `outputs/p1c-min-train/` plus offline wandb.

## Remaining Blockers

1. Official Tokenizer license → BLOCKED.
2. GPU training entry → NOT TESTED.
3. MuonAdamW runtime updates → NOT TESTED.
4. Checkpoint resume → NOT TESTED.
5. Alternative tokenizer pad/bos/eos ids not auto-populated by Parcae loader → documented fallback only.
