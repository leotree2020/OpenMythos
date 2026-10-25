# F2-E B1-R3

Status: **PENDING CHATGPT REVIEW**. E1–E5 LOCAL PASS. Not a final F2-E PASS.

## Result

Mask count must equal max(n)+max(k). Phase comes from grad-enabled state at the write call. Step must be contiguous. Dropping the last mask, step 999, flipped bits and a wrong callsite are rejected. E6 stays INCONCLUSIVE.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2e/b1r3/F2E_B1R3_RESULTS.json
```
