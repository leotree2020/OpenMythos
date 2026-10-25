# F3-A-R1 result

Status: **PENDING CHATGPT REVIEW**. Not CLOSED.

## Scope

Same 2/2/2 model, AdamW, linear scheduler and six steps. Seed once per path. Old F3-A evidence is unchanged.

## Result

Steps 4–6 match on loss, LR, weights, optimizer state, scheduler config and RNG. Corrupt checkpoint files are rejected by the loader. Step 1 has LR 0 and no parameter change, as frozen in the supplement.

MuonAdamW, DataLoader resume and `scripts/train.py` remain NOT TESTED.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src /usr/bin/python3.11 \
  research/mini_mythos/gate3_cpu_train/r1/f3a_r1.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate3_cpu_train/r1/F3A_R1_RESULTS.json
```
