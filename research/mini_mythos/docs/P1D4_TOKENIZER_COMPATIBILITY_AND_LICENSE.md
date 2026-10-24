# P1-D4 Tokenizer Compatibility and License

## 1. Executive Summary

Technical candidate-config checks passed. Full data pipeline was not executed. Official identity and license are unconfirmed.

- Technical Compatibility: **BLOCKED** (required full data path not run)
- Official Provenance & License: **BLOCKED**
- Overall P1-D4: **BLOCKED**

This is not Gate 2.2-C PASS.

## 2. Baseline

OpenMythos HEAD 7c28678d2027e9e5ad3b58e01d12437f0e97ef38
Parcae 69284c13746e849104f738d6d1a347b1f457df76
Tokenizer revision 6247b5d0592876b73660f34c2dd16c9db9e9045c
tokenizer.json SHA-256 e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77

Host: Python 3.11.2, transformers 5.20.2, tokenizers 0.23.3. CPU only.

## 3. Special-token experiment

No official token-config files were in the Hub repo.
A temporary candidate config was created (not claimed official):

- bos_token = `<|bos|>`
- eos_token = `<|eos|>`
- pad_token = `<|pad|>`

Reload with pinned `Tokenizer.from_directory`:

| Check | Result |
|-------|--------|
| bos/eos/pad | 0 / 1 / 2 |
| vocab | 32768 |
| tokenizer.json hash unchanged | yes |
| encode same as bare load | yes |
| Unicode roundtrip | yes |
| pad_id None fallback | not triggered |

## 4. Loss and data path

With the candidate config, `ignore_index` is 2.
A fixed-logit check showed ignore 2 and ignore 0 produce different losses (9.08e-5 vs 10.0).
ID 0 is not treated as PAD. ID 2 is the ignore label.

`BestFitPackingCollator` constructed with add_bos/add_eos. Full `scripts/train.py` dataloader was not executed (needs fabric/runtime). That item is BLOCKED.

## 5. Parcae-small compatibility

Vocab matches 32768. Special-token attributes match the file IDs only after the candidate config. Frozen YAML was not modified.

## 6. Identity and license

No LICENSE, no model card, no statement that this artifact trained parcae-small-140m.
Parcae source MIT is not a license for this tokenizer file.
Allowed research use, redistribution, and config edits are unconfirmed.
Relation to huginn_tokenizer_65k remains UNKNOWN.

Inquiry draft (not sent):

> Could you confirm whether SandyResearch/parcae-tokenizer revision 6247b5d0 is the tokenizer used for parcae-small-140m, and whether independent research training from random weights is permitted? The repo has no LICENSE. We also need the intended BOS/EOS/PAD IDs (we observe 0/1/2 in tokenizer.json).

## 7. Risks

- License BLOCKED.
- Candidate config is ours, not upstream.
- Full dataloader not run.
- 65k identity UNKNOWN.

## 8. Matrix

| Item | Result |
|------|--------|
| Candidate load 0/1/2 | PASS |
| Hash unchanged | PASS |
| ignore_index=2 | PASS |
| Full data pipeline | BLOCKED |
| License / identity | BLOCKED |

## 9. Next stage

Not ready. Do not start P1-D5 or GPU work.
