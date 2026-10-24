# P1-D3 Special Token Compatibility

## Verdict

**FAIL** for training-path special-token semantics.
License and official identity remain **BLOCKED**.

## Artifact

Revision 6247b5d0592876b73660f34c2dd16c9db9e9045c
SHA-256 e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77

`added_tokens` and `model.vocab` both contain:
- `<|bos|>` = 0
- `<|eos|>` = 1
- `<|pad|>` = 2

ID 0 is `<|bos|>`, a special token, not an ordinary text piece.

## Attribute vs existence

Tokens exist in `tokenizer.json`.
`Tokenizer.from_directory` sets IDs from `processor.bos_token_id` / `eos_token_id` / `pad_token_id`.
Those attributes are None because `tokenizer_config.json` and `special_tokens_map.json` are absent.
CPU load recorded bos/eos/pad attributes as None/None/None.

## Training path

`scripts/train.py:252-254`: if `pad_id is None`, it sets `pad_id = 0`.
`scripts/train.py:287`: `ignore_index = tokenizer.pad_id`.
`scripts/train.py:577` and `646` use that ignore index.

With this artifact, ignore_index becomes 0, which is BOS, not PAD (2).
That is not the same as ignoring padding. Real BOS positions would be ignored by the loss.

## Packing

No separate pad-token contract was found that overrides this. The loss path above is the binding one.

## Environment

This host. CPU only. Pinned Parcae 69284c1. No GPU. No training. No code changes.
