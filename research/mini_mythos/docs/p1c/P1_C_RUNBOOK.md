# P1-C Runbook

## Prerequisites

- Pin Parcae at `69284c13746e849104f738d6d1a347b1f457df76`
- Use official `launch_configs/parcae-small-140m.yaml` as base
- Do not modify Parcae model source

## Data & Tokenizer acquisition

- Official download script: `scripts/download_data.py` targets `SandyResearch/fineweb-edu-shuffled` (HF dataset).
- Full FineWeb-Edu is multi-TB (ODC-By license). **BLOCKED** until user approves download, storage, and network.
- Tokenizer: official path `/resource/tokenizer/parcae_tokenizer`; training script exists in upstream. Pretrained tokenizer acquisition **BLOCKED** pending confirmation of HF availability or local generation.
- For Stage 1 smoke only, a tiny synthetic or cached subset may be used if data is unavailable.

## Stage 1 Smoke (after GPU authorization)

1. Verify environment with `p1c_env_check.py`.
2. Prepare minimal data / tokenizer (or synthetic for pure mechanism smoke).
3. Override config for frequent checkpoint: `save_step_interval=10`, `eval_step_interval=10`.
4. Launch short run (~40 steps).
5. Explicitly save at step 20, resume, continue to 40.
6. Validate against Stage 1 acceptance criteria (below).
7. Archive logs and key metrics.

## Stage 1 Acceptance Criteria (PASS required)

- Loss remains finite throughout.
- Gradients finite (or correctly skipped per config).
- Optimizer state restored identically after resume.
- RNG / data read progress restored (same next batch sequence).
- Model parameters match within numerical tolerance after resume + continue.
- At least one checkpoint written and successfully loaded.
- Key metrics logged (loss, grad norm).
- Abnormal stop conditions: non-finite that cannot be skipped, OOM that cannot be mitigated by micro-batch reduction, or mismatch in restored state → FAIL and report.

## Stop conditions

- Non-finite loss / grads that cannot be skipped safely
- Architecture change request
- Unapproved data download or cost
- Conflict with existing P1-A/P1-B evidence

## Next

After Stage 1 evidence is collected, review with ChatGPT before Stage 2.
