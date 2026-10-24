# F2-C B2

Status: **PENDING CHATGPT REVIEW**. Local checks passed. This is not a final F2-C PASS.

## Command

```bash
PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 \
  research/mini_mythos/tests/test_parcae_gradient_math_b2.py \
  --parcae-root /tmp/parcae-src \
  --manifest research/mini_mythos/gate2_2/evidence/f2c/F2C_DISCOVERY_MANIFEST.json \
  --output research/mini_mythos/gate2_2/evidence/f2c/b2/F2C_B2_RESULTS.json
```

Exit 0. Parcae `69284c1`, clean. Manifest blob `918e49ef06c31083245259feb4fa2d13eab96cad` unchanged.

## Local result

Three frozen scalars. FULL and TBPTT both PASS at h=1e-3 and h=1e-2. Suffix reconstruction PASS. Negative `|Δg| > 1e-2` PASS. No INCONCLUSIVE.

## Limit

This does not close F2-C. ChatGPT still needs to review the evidence.
