# F2-E B1-R2

Status: **PENDING CHATGPT REVIEW**. Not a final F2-E PASS.

## Result

E1–E5 local PASS. Recurrent masks are checked by phase, step, content and write selection. Start and end weight hashes are measured. E6 stays INCONCLUSIVE with the R1 numbers.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2e/b1r2/F2E_B1R2_RESULTS.json
```
