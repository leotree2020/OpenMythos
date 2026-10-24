# F2-B-R2

Status: **PENDING CHATGPT REVIEW**. Not a final PASS.

## Changes from R1

- Pair acceptance now requires both runs to have empty missing, zero and nonfinite lists.
- Gradient name sets must match, and coverage must equal the trainable tensor count.
- Baseline parameter count must be 247936.
- Negative records for missing and zero gradients are rejected by the same function.
- `--require-pinned` also blocks a dirty Parcae workspace or an import outside `--parcae-root`.
- Original F2-B and F2-B-R1 files were not overwritten.

## Command

```bash
python research/mini_mythos/tests/test_parcae_recurrence_cpu.py \
  --parcae-root /path/to/parcae \
  --output /path/to/F2B_R2_RESULTS.json \
  --require-pinned
```

## Result

Exit 0. Params 247936. Imported path is under the given root. Parcae status is clean.
Negative missing and zero cases were rejected.
