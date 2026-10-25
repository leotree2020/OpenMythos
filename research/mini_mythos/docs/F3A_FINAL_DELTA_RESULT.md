# F3-A final exception delta

Status: **PENDING CHATGPT REVIEW**. Not a new training run.

## Scope

Uses the committed R1 checkpoint. No six-step rerun. One controlled resume step for the wrong-RNG case. Old evidence is unchanged.

## Result

- Wrong scheduler config is rejected by the loader.
- A valid but different Torch RNG is detected as FAIL. The step does not reseed.
- A kept key with a changed tensor shape is rejected.
- The old deleted-key case is reclassified as `missing_model_key`.

MuonAdamW, DataLoader resume and `scripts/train.py` remain NOT TESTED.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src /usr/bin/python3.11 \
  research/mini_mythos/gate3_cpu_train/r1_final/f3a_r1_final.py \
  --parcae-root /tmp/parcae-src \
  --checkpoint research/mini_mythos/gate3_cpu_train/r1/f3a_r1_step3.pt \
  --output research/mini_mythos/gate3_cpu_train/r1_final/F3A_FINAL_RESULTS.json
```
