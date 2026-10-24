# F2-C B1

Status: **PENDING CHATGPT REVIEW**. Discovery only. B2 is not authorized.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_gradient_math_cpu.py \
  --parcae-root /tmp/parcae-src \
  --output research/mini_mythos/gate2_2/evidence/f2c/F2C_B1_RESULTS.json
```

Exit 0. Params 247936. Parcae `69284c1`, clean.

## Discovery

Frozen scalars:

- `transformer.core_block.1.attn.c_proj.weight` index 1424, delta 0.298
- `transformer.core_block.0.attn.c_proj.weight` index 1440, delta 0.241
- `transformer.core_block.0.mlp.proj.weight` index 2934, delta 0.165

All three have `|g| > 1e-3`, `|delta| > 1e-2`, and finite-difference signal at the frozen h grid.
AUX64 PASS. Suffix reconstruction PASS. Negative discovery RECORDED.

## B2

Do not start confirmatory B2 until ChatGPT reviews this manifest.
