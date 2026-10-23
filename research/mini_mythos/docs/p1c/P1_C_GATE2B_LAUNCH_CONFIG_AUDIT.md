# P1-C Gate 2B — Single-GPU Launch Configuration Audit (Final Corrections)

**Status**: Free static analysis only. No GPU, no training.

Pinned Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## 1. Synthetic data memory budget

`RandomTokensDataset.__init__` (source):
```python
self.data = torch.randint(0, vocab_size, (int(1e6), block_size), dtype=torch.int32, generator=generator)
```

- Pre-allocates **1,000,000** rows.
- For `block_size=128`: raw size ≈ 1e6 × 128 × 4 bytes = **512 MiB** per dataset.
- User-reported effective size with `loader_block_size=129` accounting: ≈ **492 MiB** per rngds.
- **train + val** ≈ **984 MiB** host RAM.

**Requirement for next GPU experiment**:
- Host RAM must comfortably exceed ~1 GiB for the two rngds instances plus model/optimizer overhead.
- Record actual RSS at startup in the experiment log.
- Do **not** modify upstream `RandomTokensDataset`.

## 2. Tokenizer startup conditions

Official path expects a directory containing at least:
- `tokenizer.json`
- (optional but recommended) `tokenizer_config.json`, `special_tokens_map.json`

- Vocab size must match model `vocab_size` (32768 in the pinned small config).
- PAD / EOS / BOS ids are read from the tokenizer processor; rngds itself only needs `vocab_size`, but the training entry still requires a valid tokenizer path.
- License of the official Parcae tokenizer remains **unconfirmed** → **BLOCKED** for download.

**Legal acquisition plan (not executed)**:
1. Prefer any tokenizer already present on the target machine or previously approved by the user.
2. If none exists, obtain only the minimal tokenizer files from a source whose license has been explicitly reviewed and accepted.
3. Verify `len(tokenizer) == 32768` (or documented padded size) and presence of required special tokens before training.
4. Do **not** substitute another model's pretrained weights as a stand-in for Mini-Mythos training results.

Current Proposed YAML leaves `tokenizer_path` commented → **cannot launch until a verified path is supplied**.

## 3. rngds Checkpoint resume risk

`RandomTokensDataset`:
```python
def state_dict(self):
    return {"idx": self.idx}
def load_state_dict(self, state_dict):
    self.idx = state_dict["idx"]
```

- State is a simple integer cursor.
- `train.py` `load_checkpoint` restores `train_dataloader` state; when `dataset_state` is present it is applied.
- Whether the StatefulDataLoader wrapper correctly calls `load_state_dict` on an rngds instance is **static-plausible but NOT TESTED**.
- Extra batch skip on resume (documented in Gate 2A) still applies and may advance the cursor by one additional sample. Effect on rngds is deterministic but must be measured.

**Conclusion**: rngds resume is simpler than ParquetStreamPure and avoids the CUDA distributed gather. Residual risk remains the extra batch skip and the exact StatefulDataLoader integration. Runtime verification **NOT TESTED**.

## 4. Checkpoint save boundary

From `maybe_save_checkpoint`:
```python
save_at_interval = not is_accumulating and state["microbatch_step"] % cfg.save_step_interval == 0
```

With proposed numbers:
- `micro_batch_size=2`, `world_batch_size=8` → `gradient_accumulation_steps=4`
- `save_step_interval=2`
- Save occurs only when **both**:
  - `not is_accumulating` (i.e. `microbatch_step % 4 == 0`)
  - `microbatch_step % 2 == 0`

→ Effective save points are at microbatch multiples of **4**, not every 2 microbatches.

Additionally:
- First `optimizer_step == 0` skips `optimizer.step()`.
- All logs must distinguish `microbatch_step`, `optimizer_step`, and actual parameter update count.

## 5. Free checks performed

| Item | Result |
|------|--------|
| RandomTokensDataset preallocation size | PASS (source) |
| rngds state_dict returns idx | PASS (source) |
| save requires not is_accumulating | PASS (source) |
| Tokenizer path still required | PASS (source) |
| Full launch / resume / memory RSS | NOT TESTED |
