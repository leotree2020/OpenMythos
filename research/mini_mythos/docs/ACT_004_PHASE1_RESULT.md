# ACT-004 Phase 1 — Compute-Aware Depth Sweep Results

**Status:** Completed in user Codespaces, transcribed from user-provided terminal log. Original `sweep.json` is local to Codespaces and has not been independently inspected or uploaded to GitHub.

## Execution

- Branch `mini-mythos-research`, pulled to `fe9a8dd`.
- Unit tests: **51/51 PASS**, 1.690 seconds.
- 18 paired A/B configurations: GQA/MLA × max depths 1/2/4 × training seeds 11/22/33.
- 30 optimizer steps per arm, 30 synthetic heldout batches per configuration.
- Local output: `research/mini_mythos/results/act004/sweep.json`.

## Aggregate results

Positive ΔLoss = Forced Final Loss − Original ACT Loss, favoring Original.

| Attention | Max depth | Seeds | Mean ΔLoss | Mean paired run wall s | Mean original forward loop calls per train step | Mean forced loop calls | Mean original deficit-token fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| GQA | 1 | 3 | +0.027181 | 0.89 | 1.00 | 1.00 | 1.000 |
| GQA | 2 | 3 | +0.014721 | 1.04 | 2.00 | 2.00 | 0.407 |
| GQA | 4 | 3 | +0.000000 | 1.31 | 2.73 | 2.73 | 0.000 |
| MLA | 1 | 3 | +0.057676 | 0.95 | 1.00 | 1.00 | 1.000 |
| MLA | 2 | 3 | +0.004892 | 1.24 | 2.00 | 2.00 | 0.478 |
| MLA | 4 | 3 | +0.000000 | 1.41 | 2.36 | 2.36 | 0.000 |

## Observations and interpretation

- Under max depth 1, every sampled training step exhibited ACT probability mass deficit and Original ACT had lower mean heldout loss.
- Under max depth 2, mean deficit-token fraction decreased; Original ACT still had lower mean heldout loss.
- Under max depth 4, no deficit was observed across the sampled training steps, and the displayed heldout loss differences were zero for all six configurations.
- A likely mechanism is that increasing maximum recurrence budget permits threshold-based halting before budget exhaustion, leaving no final-remainder intervention to apply. **This is a mechanism interpretation, not an independently verified causal explanation for every input.**
- Mean executed recurrent calls were equal between arms for all settings. This is consistent with a final-probability intervention that changes weighting, not the maximum recurrence depth.
- **Paired run wall time includes initialization, training of both arms, diagnostics, and heldout evaluation.** It is not a per-arm latency, speedup, or FLOPs estimate.
- Depth 4 is not necessarily better than depth 1 or 2 in absolute heldout loss: this experiment summary reports only between-arm deltas. Do not infer depth ranking from ΔLoss alone.
- Only three training seeds, small synthetic dataset, 30 steps; no pretrained model evidence, formal significance, or compute-matched quality conclusion.

## Next step: ACT-004 Phase 2

Implement separate per-arm forward and backward timings with warmup and controlled ordering, plus absolute heldout loss by depth. Preserve actual loop-call metrics and inspect raw `sweep.json` before claiming cost/quality tradeoffs. Do not claim FLOPs matching without operator-level accounting.
