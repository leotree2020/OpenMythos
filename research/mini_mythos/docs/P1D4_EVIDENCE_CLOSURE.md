# P1-D4 Evidence Closure

## Verdict

Technical Compatibility: **PASS**
Official Provenance & License: **BLOCKED**
Overall P1-D4: **BLOCKED**

Not Gate 2.2-C PASS. Not authorization for GPU training.

## E2 correction

P1-D4-E2 closed two gaps. Candidate config remains NON-OFFICIAL.

- Loss check now uses the same logits and labels. Only `ignore_index` changes.
- The data path now runs `ParquetStreamPure` → `PackedIterableDataset` → `BestFitPackingCollator` → `DataLoader`.

Authoritative files: `e2_raw.txt`, `e2_loss_check.txt`, updated `raw.txt` and `loss_check.txt`.
Older contradictory records are kept as `history_raw.txt` and `history_loss_check.txt`.

## Loss (single variable)

Same inputs:
- dtype float32
- shape `[1, 4, 8]`
- reduction mean
- labels `[[3, 2, 3, 2]]`
- logits: positions 0/2 peak at class 3; positions 1/3 peak at class 4

Results from real `F.cross_entropy`:
- ignore_index=2 → `0.0003178806509822607` (positions of label 2 ignored)
- ignore_index=0 → `5.0003180503845215` (no label is 0, so all four count)

Command:
```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src python research/mini_mythos/gate2_2/evidence/p1d4/test_p1d4_chain.py
```
Exit 0.

## Real DataLoader path

Pinned classes only. CPU, num_workers=0, batch_size=1, `unwrap_singleton_collate`.

Source tokens from one iterator had no 0/1/2.
DataLoader first batch:
- input_ids: no BOS, no EOS, 4 PAD=2 fill tokens
- labels: shift of the packed row, 5 PAD=2, no BOS, no EOS
- valid labels with pad_id=2: 25
- ignored if ignore_index=2: 5

This matches source: encode without bos/eos, tensor branch skips re-encoding, pad is packing fill only.

## Matrix

| Item | Result |
|------|--------|
| Tokenizer 0/1/2 | PASS (kept) |
| SHA-256 | PASS (kept) |
| Encode consistency | PASS (kept) |
| Loss single-variable | PASS (E2) |
| ParquetStreamPure | PASS (E2) |
| PackedIterableDataset | PASS (E2) |
| DataLoader | PASS (E2) |
| Label shift | PASS (E2) |
| Loss ignore mask | PASS (E2) |
| Technical Compatibility | PASS |
| Official Provenance & License | BLOCKED |
| Overall P1-D4 | BLOCKED |

## Still blocked

No new evidence that this tokenizer is the parcae-small training asset.
No LICENSE. Relation to huginn_tokenizer_65k remains UNKNOWN.
