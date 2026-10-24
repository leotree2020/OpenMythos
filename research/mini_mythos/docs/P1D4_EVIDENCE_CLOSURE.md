# P1-D4 Evidence Closure

## Verdict

Overall P1-D4: **BLOCKED**.
Technical data-path checks were newly reproduced. Official identity and license remain unconfirmed.

Not Gate 2.2-C PASS.

## Evidence class

- Candidate config files in `/tmp/tok-compat` were still present. No original stdout from the earlier run. Load/encode/hash checks here are **NEW REPRODUCTION**.
- Parquet chain is **NEW REPRODUCTION**.
- `ignore_index = tokenizer.pad_id` is **SOURCE-ONLY** (`scripts/train.py:287`).
- Official identity and license are **UNVERIFIED** / **BLOCKED**.

## Candidate config

Non-official files:
- `evidence/p1d4/candidate_tokenizer_config.json`
- `evidence/p1d4/candidate_special_tokens_map.json`

NEW REPRODUCTION:
- bos/eos/pad = 0/1/2
- vocab = 32768
- tokenizer.json SHA-256 unchanged: `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`
- encode of `Hello 你好 world.` matched the bare load

## Real Parquet path

Ran pinned `ParquetStreamPure` → `BestFitPackingCollator` on 4 tiny texts. CPU only.

Findings:
- Raw encode produced **no BOS=0, no EOS=1, no PAD=2**.
- This matches source: `tokenizer.encode(text, return_tensors=False)` without bos/eos (`huggingface_dataset.py` around the encode call).
- Collator received tensors and returned them unchanged (`_tokenize_row` tensor branch). It did not add BOS/EOS.
- PAD=2 appeared only as packing fill for unused slots (`pad_id or 0`, and pad_id was 2).
- Shifted labels contain 2 at those fill positions. This sample had no label equal to 0.

This is recorded, not judged FAIL solely for missing BOS/EOS.

## Loss

Public case, float32, shape `[1, 2, 8]`, reduction mean, labels `[3, 2]`:
- ignore_index=2 → `0.0003178806509822607`
- ignore_index=0 → `5.000317573547363`

Same labels. ignore 2 drops the pad label; ignore 0 keeps it.

## Identity and license

No new public evidence that `SandyResearch/parcae-tokenizer` is the parcae-small training asset.
No LICENSE. Parcae MIT does not cover this file.
Research use and redistribution remain unconfirmed.
Relation to `huginn_tokenizer_65k`: UNKNOWN.

## Matrix

| Item | Result |
|------|--------|
| Candidate load | PASS (NEW REPRODUCTION) |
| Hash unchanged | PASS |
| Encode consistency | PASS |
| Special token IDs | PASS (0/1/2) |
| ignore_index=2 | PASS for candidate pad_id; assignment is SOURCE-ONLY |
| Real Parquet chain | PASS (executed; no BOS/EOS inserted) |
| Packing and label shift | PASS |
| Loss ignore mask | PASS |
| Official identity | BLOCKED |
| License | BLOCKED |
| Technical Compatibility | PASS for the checks above |
| Official Provenance & License | BLOCKED |
| Overall P1-D4 | BLOCKED |

## Next stage

Not ready. License and official identity block the next stage.
