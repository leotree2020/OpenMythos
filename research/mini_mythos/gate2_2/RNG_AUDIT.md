# RNG Audit (revised)

## Native order

```python
state["microbatch_step"] += 1
model.step = state["microbatch_step"]
```

Recurrence sampler seeds from `514229 + self.step`. `model.step` is a plain attribute, not in `state_dict`.

## Corrected causal claim

- C1: omit restoring `model.step`, keep correct `microbatch_step`. Native logic resets `model.step` before forward. Weights match A (n_diff=0).
  → Missing the plain attribute alone is **not** a checkpoint defect, if the training counter is restored.
- C2: wrong `microbatch_step`. n_diff=42.
  → Wrong training counter changes the recurrence seed and the weights.

## D

Extra data skip with the same update count (6). Data hashes differ. Update count matches A.

## Not claimed

- AdamW probe is not MuonAdamW verification (NOT TESTED).
- Official train.py remains BLOCKED on CPU.
- CUDA RNG: NOT APPLICABLE.
