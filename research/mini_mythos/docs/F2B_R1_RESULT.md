# F2-B-R1

Status: **PENDING CHATGPT REVIEW**. Not a final PASS.

## What changed from F2-B

- Removed hardcoded `/tmp/parcae-src` and `/tmp/om`.
- `--parcae-root` and `--output` are required.
- `--require-pinned` checks Parcae HEAD is `69284c13746e849104f738d6d1a347b1f457df76`.
- Records Python, PyTorch, CPU, threads, Parcae commit and config.
- Each pair now checks logits, loss and gradient repeat consistency.
- Records gradient coverage and missing names.
- Records `torch.is_grad_enabled()` on each core call. Expected: n False then k True.
- (0,2) vs (1,1) compares the full shared gradient set and lists missing, zero and non-finite names.
- Causal check covers positions 5, 6 and 7. Tolerance stays 1e-5.
- Train and eval each have their own repeat record.
- Marked as a standalone probe, not unittest/pytest discovery.

Original F2-B JSON was not overwritten.

## Command

```bash
python research/mini_mythos/tests/test_parcae_recurrence_cpu.py \
  --parcae-root /path/to/parcae \
  --output /path/to/F2B_R1_RESULTS.json \
  --require-pinned
```

## Result

Exit 0. Params 247936. Overall PENDING CHATGPT REVIEW.

See `research/mini_mythos/gate2_2/evidence/f2b/F2B_R1_RESULTS.json`.
