# CPU Probe Reproduction (A.2)

```bash
PYTHONPATH=/tmp/py311-pkgs:/tmp/parcae-src python research/mini_mythos/gate2_2/cpu_model_probe.py
```

Exit code: 0

Environment: Python 3.11.2 / PyTorch 2.14.1+cpu / Parcae `69284c1`

Tolerance: `TOL_ABS = 1e-5` (pre-declared).

## Status

| Group | Expectation | Result |
|-------|-------------|--------|
| A | continuous | PASS |
| B | full restore matches A | PASS (n_diff=0) |
| C1 | omit model.step only, still matches | PASS (n_diff=0) |
| C2 | wrong microbatch_step diverges | PASS (n_diff=42) |
| D | extra skip, same update count, hashes differ | PASS |

Any group failing its expectation exits non-zero.
