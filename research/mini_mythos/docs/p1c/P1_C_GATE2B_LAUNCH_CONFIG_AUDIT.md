# P1-C Gate 2B — Launch Configuration Audit (Dependency & Tokenizer Correction)

**Status**: Free static / public-metadata checks only. No GPU, no containers started, no training.

## Memory budget (unchanged)

| Length | Size per dataset | Train + Val |
|--------|------------------|-------------|
| 128    | 488.28 MiB       | 976.56 MiB  |
| 129    | 492.10 MiB       | 984.19 MiB  |

## Dependencies

| Package   | Constraint                  | Status                                      | Runtime   |
|-----------|-----------------------------|---------------------------------------------|-----------|
| lightning | ==2.3.0.dev20240328         | **PACKAGE AVAILABLE** (PyPI wheel + sdist)  | NOT TESTED |
| torchdata | unpinned                    | Available                                   | NOT TESTED |
| wandb     | unpinned                    | Available                                   | NOT TESTED |
| torch     | extras / Gate 1 used 2.8    | Available                                   | NOT TESTED |
| numpy     | <2.0                        | Available                                   | NOT TESTED |

PyPI JSON API confirms `lightning-2.3.0.dev20240328` provides both a wheel and an sdist. The Dockerfile also installs this exact pin. Do not claim it is unavailable from standard PyPI.

## Official Docker image

- `launch_interactive.sh` default: `ghcr.io/sandyresearch/parcae:sha-49c27cb`
- Tag maps to commit `49c27cbd639362b59336ea3981fb127ac8e464c8` ("updated for docker").
- Pinned research commit is `69284c13746e849104f738d6d1a347b1f457df76`.
- **Mismatch**: the published image tag is not built from the pinned commit.
- Dockerfile base is `nvcr.io/nvidia/pytorch:26.02-py3` and installs the lightning pin plus other deps.
- Suitability as a fixed-commit reproduction environment: **NOT CONFIRMED** without rebuilding from the pinned commit or verifying image contents. Public metadata only; container not started.

## Tokenizer

- Public HF repo `SandyResearch/parcae-tokenizer` exists.
- No model card, no license file visible.
- **Status: BLOCKED** because of missing license declaration. This is **not** the same as a confirmed prohibition.
- Do not download until license is reviewed.

### Alternative test path (not official)

`scripts/tok_train.py` can train a BPE tokenizer (vocab 32768, special tokens `<|bos|>`, `<|eos|>`, `<|pad|>`) from any directory of parquet files containing a `text` column.

- If a clearly licensed small text corpus is supplied, a test tokenizer can be generated.
- Any such tokenizer **must** be labeled as an **alternative test path**.
- It cannot be presented as the official Parcae tokenizer or as full reproduction of the official training data pipeline.

## Remaining launch blockers

1. Official Tokenizer license declaration missing → **BLOCKED** (not confirmed prohibited).
2. Published Docker image tag does not match pinned commit → image suitability **NOT CONFIRMED**.
3. Official `train.py` entry not yet started → **NOT TESTED**.
4. MuonAdamW runtime behavior → **NOT TESTED**.
5. Checkpoint save/resume with rngds → **NOT TESTED**.
6. Target-environment integration of available packages → **NOT TESTED**.

No new research plans added.
