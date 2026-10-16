# ACT-003 Gate B — Expanded Heldout / Multi-seed Results

**Status:** Completed in the user's GitHub Codespaces; summarized from supplied terminal log. The original 20 result JSON files and `summary.json` have **not** been independently retrieved or uploaded in this documentation step.

## Execution

- Branch: `mini-mythos-research` (pulled to `9145081` before running).
- Unit tests: **47 / 47 PASS** (`Ran 47 tests in 1.749s`).
- Attention: GQA, MLA; depths: 1, 2.
- Training seeds: 11, 22, 33, 44, 55.
- Training: 30 optimizer steps per A/B arm.
- Heldout: 100 deterministic synthetic batches per configuration.
- Output location in Codespaces: `research/mini_mythos/results/act003_gate_b/summary.json`.

## Result table

Delta is **Forced Final Loss − Original ACT Loss**; positive favors Original ACT.

| Attention | Depth | Train seeds | Mean delta | Descriptive bootstrap 95% percentile interval | Original better | Forced better |
|---|---:|---:|---:|---|---:|---:|
| GQA | 1 | 5 | +0.031341 | [+0.008633, +0.054795] | 4 | 1 |
| GQA | 2 | 5 | +0.012673 | [+0.007746, +0.017645] | 5 | 0 |
| MLA | 1 | 5 | +0.047422 | [+0.014903, +0.088767] | 5 | 0 |
| MLA | 2 | 5 | +0.005754 | [+0.000014, +0.011532] | 3 | 1 |

The remaining MLA-depth-2 seed is a near tie under the script's 1e-8 cutoff; do not count it as a win.

## ACT dynamics observations

- Depth 1: every seed in both attention families exhibited a mass deficit and loss separation from step 1.
- Depth 2: first deficit varied by seed; MLA seed 22 exhibited **no observed deficit or loss split** in 30 steps (consistent with ACT-002 negative control).
- Depth 2 examples: GQA seed 22 first deficit step 2 and first loss split step 3; MLA seed 44 first deficit/loss split step 2.
- This suggests the policy effect is **conditional on halting trajectories**, not universal for every seed.

## Interpretation and limits

The 100 heldout batches reduce evaluation noise relative to the earlier three-batch check, but the same fixed synthetic heldout distribution is reused across training seeds. The bootstrap resamples only **five training seeds** per configuration, so the percentile intervals are descriptive and may be unstable; they do not establish formal significance. No adjustment was made for four comparisons. The tested models are tiny randomly initialized models trained on synthetic token sequences, **not** pretrained language models. No conclusion about real-world accuracy, reasoning ability, or a universal ACT implementation bug follows.

The Gate B run does **not** compare equal wall-clock compute, realized recurrent iterations, or FLOPs. Those measurements should precede efficiency or architectural superiority claims.

## Next experiment: compute-aware mechanism sweep

1. Record per-step realized recurrent loop counts and ACT mass-deficit fraction for both policies, with exact same train seeds.
2. Sweep depths 1, 2, 4 (and thresholds if supported) while holding training tokens/optimizer steps fixed; record measured runtime.
3. Repeat selected configurations with a compute-matched budget and more independent training seeds.
4. Preserve full result JSON and environment/source provenance in a versioned evidence bundle.
