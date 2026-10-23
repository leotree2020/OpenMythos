# P1-C Minimal Training Environment Unlock — Final Fixes

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## Task 1 — Tokenizer special-token metadata

**Status: PASS**

Standard config files written next to `tokenizer.json`:
- `tokenizer_config.json`
- `special_tokens_map.json`

Actual load results (Parcae `Tokenizer.from_directory` and `Tokenizer(checkpoint_dir)`):
- bos_id == 0
- eos_id == 1
- pad_id == 2
- all three < actual vocab_size (489)
- encode/decode: PASS
- both loader paths succeed
- ignore_index can use real pad_id=2 (no BOS fallback)

SHA-256 (from `make_alt_test_tokenizer.py` output):
- tokenizer.json: `e061ba38cf7585fbd82db3f8914446fdfbfbad5bbf8ed27c79620b3b37dd189b`
- tokenizer_config.json: `0ebfbf2190d2375669056a65a8a5984fbf49f72483fb178db6f263d9276589d3`
- special_tokens_map.json: `3a1c4d3094025c80439a41ee607530f77b51abc3552284dec76a8bcfba6caf51`

Marked **ALTERNATIVE TEST TOKENIZER**. Official HF tokenizer remains BLOCKED.

## Task 2 — Real CLI YAML parsing

**Status: PASS** (config parse only; no training)

Command (CPU, LOCAL_WORLD_SIZE=1):
```bash
python -c "from jsonargparse import CLI; from recpre.settings import CLISettings; import sys; sys.argv=['t','--config','/tmp/test_cfg.yaml']; cfg=CLI(CLISettings); print(isinstance(cfg, CLISettings), cfg.devices, cfg.gradient_accumulation_steps)"
```
Exit code: 0

Verified via official `CLI(CLISettings)`:
- returns real `CLISettings` instance
- `data_config` entries are `DataEntry` (type=rngds for train and val)
- `model_overwrite` applied (vocab_size=32768, block_size=128, prelude_norm=True)
- `tokenizer_path` points to the test directory
- `optimizer=MuonAdamW`, `optim_config` present
- `model_name=parcae-small-140m`, `model_impl=dynamic`
- `devices=1`, `gradient_accumulation_steps=4`, `save_step_interval=2`

GPU training entry remains **NOT TESTED**.

## Task 3 — Predicted step accounting

**PREDICTED / NOT RUNTIME VERIFIED** (from source):

| Item | Value |
|------|-------|
| max_steps | 6 |
| gradient_accumulation_steps | 4 |
| predicted microbatch_step | 20 |
| predicted optimizer_step | 5 |
| predicted actual optimizer.step() | 4 (first skipped) |
| predicted regular save boundaries | microbatch 4, 8, 12, 16, 20 |

rngds draws tokens from the tokenizer's actual vocab (489). Model output vocab remains 32768 via model_overwrite. This is not full-vocabulary training and not language learning.

## Status list

| Item | Status |
|------|--------|
| Alt tokenizer special tokens | PASS |
| Real CLI YAML parse | PASS |
| Dependency imports | PASS |
| Official tokenizer license | BLOCKED |
| GPU training entry | NOT TESTED |
| MuonAdamW runtime updates | NOT TESTED |
| Checkpoint resume | NOT TESTED |
| Step/save predictions | PREDICTED / NOT RUNTIME VERIFIED |
