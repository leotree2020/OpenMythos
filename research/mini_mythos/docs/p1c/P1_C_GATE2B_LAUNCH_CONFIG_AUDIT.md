# P1-C Gate 2B — Launch Configuration Audit (Memory & Blockers Update)

**Status**: Free static checks only. No GPU, no training.

## Memory budget (corrected)

`RandomTokensDataset` pre-allocates `1_000_000` rows of `int32`.

| Length | Bytes per row | Size per dataset | Train + Val |
|--------|---------------|------------------|-------------|
| 128    | 512           | **488.28 MiB**   | 976.56 MiB  |
| 129    | 516           | **492.10 MiB**   | **984.19 MiB** |

Calculation: `1e6 * N * 4 / (1024*1024)`.

Host RAM must accommodate ~984 MiB for the two rngds instances plus model/optimizer overhead. Do not modify upstream `RandomTokensDataset`.

## Tokenizer

- Public HF repository exists: `SandyResearch/parcae-tokenizer`.
- No model card, no license file, no visible file list on the public page.
- Parcae GitHub repo itself is MIT, but the tokenizer repository is separate and its license is not stated.
- Minimal files expected by `parcae_lm/tokenizer.py`: `tokenizer.json` (plus optional `tokenizer_config.json` / `special_tokens_map.json`).
- Vocab size expected: 32768.

**Status: BLOCKED**. License cannot be confirmed from public metadata. Do not download until license is explicitly reviewed and accepted.

## Dependencies (installability, free check)

From pinned `pyproject.toml`:

| Package     | Constraint                      | PyPI status                          | Runtime |
|-------------|---------------------------------|--------------------------------------|---------|
| lightning   | ==2.3.0.dev20240328             | Dated dev pin; not in stable index   | NOT TESTED |
| torchdata   | unpinned                        | Available (0.11.0 latest)            | NOT TESTED |
| wandb       | unpinned                        | Available (0.31.0 latest)            | NOT TESTED |
| torch       | extras torch221 / torchgte240   | Available (2.8.0 used in Gate 1)     | NOT TESTED |
| numpy       | <2.0                            | Available                            | NOT TESTED |

Lightning pin is the highest install risk. All runtime behavior remains NOT TESTED.

## Remaining launch blockers (short)

1. Official Tokenizer license unconfirmed → BLOCKED (no download).
2. Lightning 2.3.0.dev20240328 may require non-standard install → NOT TESTED.
3. Official `train.py` entry has not been started (CUDA gate) → NOT TESTED.
4. MuonAdamW runtime grouping and finite updates → NOT TESTED.
5. Checkpoint save/resume with rngds → NOT TESTED.
6. Target-environment WandB offline mode and torchdata StatefulDataLoader → NOT TESTED.

No further planning documents added.
