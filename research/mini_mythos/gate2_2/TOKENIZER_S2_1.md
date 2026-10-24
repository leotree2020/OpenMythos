# S2-1 Tokenizer

## Relationship (source)

- `Tokenizer(cfg.tokenizer_path)` always runs before dataloaders.
- `rngds` uses `tokenizer.vocab_size` as the random token upper bound.
- If `len(tokenizer) > model vocab`, train.py raises model vocab. The reverse is allowed.
- Planned model vocab is 32768.

## Two paths

| Path | Vocab | Status |
|------|-------|--------|
| Engineering smoke | 489 alt test tokenizer | Allowed for smoke only |
| Formal reproduction | official huginn 65k | BLOCKED |

Official path `/lustre/orion/.../huginn_tokenizer_65k` is absent on RunPod.
License was previously BLOCKED. Smoke vocab changes the token range and is not a formal reproduction.

Formal GPU YAMLs were not rewritten to the 489 path.
