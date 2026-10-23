# P1-C Gate 2A — Data & Tokenizer Admission Audit

**No large data downloaded. Public metadata only.**

## Path mismatch (BLOCKER for real data)

- `scripts/download_data.py` downloads `SandyResearch/fineweb-edu-shuffled` into `fineweb-edu-shuffled/{sample-100BT,sample-350BT,val}`.
- Official YAML (`parcae-small-140m.yaml`) expects:
  - `data_dir: "/resource/data/fineweb-edu-100b-shuffle/train"`
  - `data_dir: "/resource/data/fineweb-edu-100b-shuffle/val"`
- **Mismatch**: directory name and expected train/val layout. User must either symlink/rename after download or override `data_config` at launch. Status: **BLOCKED** until path is reconciled.

## Parquet / text field

- YAML `data_signature.keys: ["text"]`.
- Public HF dataset cards for FineWeb-Edu shuffled confirm a `text` field. Status: **VERIFIED** (metadata).

## Tokenizer

- YAML: `tokenizer_path: "/resource/tokenizer/parcae_tokenizer"`
- `parcae_lm/tokenizer.py` loads `tokenizer.json` (+ optional special tokens map).
- Model config vocab_size: 32768.
- HF `SandyResearch/parcae-tokenizer` exists but has no model card; license not explicitly stated. Status: **BLOCKED** (license + exact special tokens / vocab match NOT TESTED).
- Synthetic path (`RandomTokensDataset` / rngds) still requires a tokenizer for pad/eos identification in some code paths. Status: **NOT TESTED**.

## License

- FineWeb-Edu base: ODC-By v1.0.
- Shuffled variant inherits it.
- Tokenizer license: unconfirmed.

## Minimal future validation plan (not executed)

1. Download only tokenizer files (small).
2. Load tokenizer, assert `len(tokenizer) == 32768` (or documented padded size).
3. Load one parquet shard metadata only; confirm `text` column.
4. Resolve path mismatch via symlink or config override.
5. Do not download full 100BT until explicitly approved.
