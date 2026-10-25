# F3-A result

Status: **F3-A LOCAL RESULT / PENDING CHATGPT REVIEW**. Not CLOSED.

## Scope

Isolated CPU research script. Upstream AdamW and linear scheduler. Not MuonAdamW. Not `scripts/train.py`. Fixed inputs, not DataLoader resume.

## Result

Path A and path B match at steps 4, 5 and 6. Step 1 learning rate is 0 because the frozen warmup uses step 0. Steps 2–6 change parameters. Loss falls on this fixed input. This is not a language-learning claim.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src /usr/bin/python3.11 \
  research/mini_mythos/gate3_cpu_train/f3a_lifecycle.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate3_cpu_train/F3A_RESULTS.json
```
