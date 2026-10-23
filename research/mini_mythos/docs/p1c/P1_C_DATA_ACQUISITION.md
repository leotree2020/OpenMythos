# P1-C Data & Tokenizer Acquisition (Updated)

## FineWeb-Edu / Shuffled variant

- Official download target: `SandyResearch/fineweb-edu-shuffled` on Hugging Face.
  - Configs: sample-100BT (~100B tokens), sample-350BT, val.
  - License: inherits ODC-By v1.0 from HuggingFaceFW/fineweb-edu (+ CommonCrawl ToS).
- Full HuggingFaceFW/fineweb-edu: ~5.84 TB.
- **Status**: Available on HF, but download of even the 100BT sample is large. **BLOCKED** until user approves storage, bandwidth, and any cost.
- Alternatives for Stage 1 smoke only:
  - Tiny synthetic sequences (no real data needed for pure mechanism check).
  - Stream a few shards if network allows (still needs approval).

## Parcae Tokenizer

- Official HF artifact: `SandyResearch/parcae-tokenizer` (exists, no model card).
- Also generatable via upstream `scripts/tok_train.py` (32k BPE).
- License: not explicitly stated in the short card; assume compatible with Parcae project unless contradicted.
- **Status**: Available on HF. Download still **BLOCKED** pending approval, but size is expected to be small (tokenizer files).

## Recommendation

For Stage 1 pure smoke, synthetic data + local tokenizer generation is sufficient and avoids large downloads. Real data can be introduced after Stage 1 passes and approval is given.
