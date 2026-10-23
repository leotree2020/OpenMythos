# P1-C Runbook

## Prerequisites

- Pin Parcae at `69284c13746e849104f738d6d1a347b1f457df76`
- Use official `launch_configs/parcae-small-140m.yaml` as base
- Do not modify Parcae model source

## Stage 1 Smoke (after GPU authorization)

1. Verify environment: `python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"`
2. Prepare data / tokenizer (or reduced local subset for smoke)
3. Launch short run with official script, reduced steps / batch if OOM
4. Confirm loss finite, grads update, checkpoint round-trip
5. Archive logs and key metrics

## Stop conditions

- Non-finite loss / grads that cannot be skipped safely
- Architecture change request
- Unapproved data download or cost
- Conflict with existing P1-A/P1-B evidence

## Next

After Stage 1 evidence is collected, review with ChatGPT before Stage 2.
