# F2-D B1

Status: **PENDING CHATGPT REVIEW**. D7 was not run.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_checkpoint_rng_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2d/F2D_B1_RESULTS.json
```

Exit 0. Parcae `69284c1`, clean.

## Local result

D1–D6 PASS under the frozen tolerances. Forward logical steps are 2. Enabled modes recorded backward replay. CPU RNG matched across off and checkpoint modes. D7 remains NOT RUN.
