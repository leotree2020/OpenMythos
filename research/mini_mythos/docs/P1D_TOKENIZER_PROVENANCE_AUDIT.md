# P1-D Tokenizer Provenance Audit

Pinned Parcae: 69284c13746e849104f738d6d1a347b1f457df76
OpenMythos: 66ae4c7ae04be8898f10d2e36ba0bb73f672114f

## Verdict

**BLOCKED.** Evidence level: source inspection. Not a runtime download check.

## Upstream identity

`scripts/train.py` line 251 always does `Tokenizer(cfg.tokenizer_path)`.
`parcae_lm/tokenizer.py` loads a local directory with `tokenizer.json`, or treats a non-path string as a Hugging Face repo id via `hf_hub_download`.

`scripts/tok_train.py` trains a BPE tokenizer "in the style of GPT-4" from local datasets:
- `fineweb-edu-100b-shuffle`
- `fineweb-edu-350b-shuffle`
- `huginn-dataset`

Those paths are under `DATA_DIR` (default `/resource/data`). They are cluster paths, not a published artifact.

## Files required

A loadable directory needs `tokenizer.json`. Optional: `tokenizer_config.json`, `special_tokens_map.json`.
Special tokens in `tok_train.py`: `<|bos|>`, `<|eos|>`, `<|pad|>`.

## Access and license

No public download URL, access grant, hash, or pinned revision was found in the pinned source.
No license statement for the trained tokenizer was found.
Therefore license and redistribution rights are **not confirmed**.

## OpenMythos

The training entry can use the same `Tokenizer` class if a valid path or confirmed repo id is supplied.
It cannot use the same tokenizer today because the artifact is not available here.

## Why RunPod is BLOCKED

The configured path `/lustre/orion/csc569/scratch/jgeiping/tokenizers/huginn_tokenizer_65k` does not exist on RunPod.
This is a missing file plus an unconfirmed license. It is not a code-integration failure.
A 489-vocab alternative exists for smoke only. It is not a formal reproduction.

## Paths and limits

1. Obtain the official artifact with a confirmed license and hash. This is the only formal path.
2. Train a new tokenizer with `tok_train.py` on licensed text. That is an alternative, not official reproduction.
3. Do not substitute GPT-2, Qwen, or another tokenizer and call it Parcae reproduction.

## Effect on reproducibility

Native Parcae training cannot be claimed reproduced until the tokenizer artifact, license, and hash are confirmed.
CPU file-resume PASS does not change this.

## Next stage

**Not ready.** Tokenizer provenance remains BLOCKED.
