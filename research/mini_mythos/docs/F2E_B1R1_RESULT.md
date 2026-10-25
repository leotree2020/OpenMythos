# F2-E B1-R1

Status: **PENDING CHATGPT REVIEW**. Not a final F2-E PASS.

## Result

E1–E5 local PASS. Returned means come from the real `iterate_forward` return. Per-token repeat and checkpoint pairs are included. E6 is CONTROLLED and INCONCLUSIVE.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2e/b1r1/F2E_B1R1_RESULTS.json
```
