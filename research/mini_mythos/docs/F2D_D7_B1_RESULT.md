# F2-D D7 B1

Status: **PENDING CHATGPT REVIEW**. Not a final F2-D PASS.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2d/d7/F2D_D7_B1_RESULTS.json
```

Exit 0. Parcae `69284c1`, clean.

## Local result

S1–S5 train formula PASS. Observed `n=1`, `k=1`, logical steps 2. S6 eval is `(2,0)`, gradients NOT APPLICABLE. Checkpoint comparisons PASS. Sampler was not called in backward.

Open question: `_sample_batch_depths` uses `n=T-k`. The scalar sampler uses `n=T`. This was recorded, not fixed.
