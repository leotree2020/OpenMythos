# F2-D D7 B1-R1

Status: **PENDING CHATGPT REVIEW**. Not a final F2-D PASS.

## Guards

- Every run checks sampler count, n/k formula, n+k steps, and no-grad then grad flags.
- RNG snapshots cover before, sampler entry/exit, after forward, and after backward when applicable.
- Start and after-backward weight hashes are enforced.
- Both runs of S1/S2/S3 go through the same evaluator.
- Negative cases call that evaluator.

## Replay

Same S1–S6, seed 42, same input and weights. Local status PASS. Exit 0. Old D7 evidence is unchanged.
