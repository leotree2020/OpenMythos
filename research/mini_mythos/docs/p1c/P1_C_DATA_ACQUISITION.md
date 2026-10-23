# P1-C Data & Tokenizer Acquisition Notes

## FineWeb-Edu

- Official Parcae config points to local paths under `/resource/data/fineweb-edu-100b-shuffle/`.
- Upstream `scripts/download_data.py` downloads from HF dataset `SandyResearch/fineweb-edu-shuffled` (sample-100BT / 350BT / val).
- Full HuggingFaceFW/fineweb-edu is ~5.84 TB (ODC-By v1.0 + CommonCrawl ToS).
- **Status: BLOCKED** — requires explicit user approval for download volume, storage, and network.

## Tokenizer

- Config expects `/resource/tokenizer/parcae_tokenizer`.
- Upstream provides `scripts/tok_train.py` for training a 32k BPE tokenizer.
- No confirmed public pretrained tokenizer artifact located in this audit.
- **Status: BLOCKED** pending user confirmation of source or local generation plan.

For Stage 1 pure mechanism smoke, synthetic data is acceptable if real data remains blocked.
