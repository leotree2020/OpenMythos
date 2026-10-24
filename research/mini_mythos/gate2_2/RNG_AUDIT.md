# RNG Audit

## Finding

`Parcae.randomized_iteration_sampler` does not consume a persistent RNG.
It builds a fresh `torch.Generator(device="cpu")` seeded from `514229 + self.step`
(and `317811 + self.step` for k).

Therefore restoring `model.step` is necessary and sufficient for recurrence
sampling to match a continuous run, given identical data.

## Probe evidence

- B (step restored): weights within 1e-5 of A, n_diff=0.
- C (step left at 0): n_diff=42.
- D (extra data skip): data hashes differ.

## CUDA

NOT APPLICABLE on this CPU run.
