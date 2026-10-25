# F2-E B1

Status: **PENDING CHATGPT REVIEW**. Not a final F2-E PASS.

## Result

E1–E5 local PASS. Cross-mode logits are NOT APPLICABLE. E6 is a test-side controlled intervention and reports DETECTED. Intent remains UNKNOWN.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2e/b1/F2E_B1_RESULTS.json
```
