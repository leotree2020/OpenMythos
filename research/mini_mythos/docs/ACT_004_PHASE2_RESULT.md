# ACT-004 Phase 2 — Absolute Heldout Loss and Paired CPU Timing

**Status:** Completed in user's Codespaces; transcribed from supplied terminal log. Raw `phase2.json` has not been independently inspected or archived here.

## Execution

- Branch: `mini-mythos-research` updated through `1dc59fe` before execution.
- Tests: **55/55 PASS**, 1.489 seconds.
- GQA/MLA × max depths 1/2/4 × seeds 11/22/33 = 18 paired experiments.
- 30 optimizer steps per arm; 100 heldout synthetic batches per experiment.
- Per-arm CPU timing after training: 3 warmup repetitions and 15 measured repetitions, alternating execution order; forward/backward separately recorded.
- Output on user's Codespaces: `research/mini_mythos/results/act004/phase2.json`.

## Summary from terminal output

ΔLoss = Forced Final − Original (positive favors Original). Timing ratio = Forced Final / Original measured median forward-plus-backward CPU time (approximately 1 means similar).

| Attention | Max depth | Original heldout loss | Forced heldout loss | ΔLoss | Mean timing ratio |
|---|---:|---:|---:|---:|---:|
| GQA | 1 | 1.929754 | 1.957977 | +0.028223 | 0.987 |
| GQA | 2 | 1.971992 | 1.987401 | +0.015409 | 0.968 |
| GQA | 4 | 1.977573 | 1.977573 | +0.000000 | 1.003 |
| MLA | 1 | 2.095159 | 2.155899 | +0.060740 | 0.990 |
| MLA | 2 | 2.111747 | 2.116836 | +0.005089 | 1.003 |
| MLA | 4 | 2.110569 | 2.110569 | +0.000000 | 1.005 |

## Findings and limits

1. The Original ACT arm has lower **mean heldout loss** at depths 1 and 2 for both GQA and MLA; the arms tie to printed precision at depth 4.
2. The Original ACT depth-1 arm also has the lowest **mean absolute heldout loss across depths** in both architectures in this particular experiment. This is an observation, not proof that shallow recurrence is generally optimal. Training for a fixed 30 optimizer steps is not equal-compute training.
3. Measured per-arm CPU time ratios are near 1.0. Small deviations are not evidence of reliable speedup. Timing includes temporary ACT hooks and uses one repeated synthetic batch; CPU sharing and scheduling can cause noise.
4. Phase 1 found no original ACT mass deficits at depth 4 over observed training steps. This is consistent with the final-remainder intervention becoming inactive when ACT halts before the maximum depth; the explanation has not been causally isolated across all heldout examples.
5. **No FLOPs-matched training, independent pretrained model evaluation, or statistically robust comparison has been performed.** Three training seeds per condition; no formal statistical significance claim.

## Next recommended research

- Before any architectural change, preserve complete result JSONs and environment provenance.
- Repeat depth-1/2/4 with more seeds and report absolute loss uncertainty, not only differences.
- For an efficiency claim, compare Original ACT at different depth budgets with fixed token/compute budgets and direct per-model timing; record actual loop calls and full training runtime.
- Keep Forced Final Remainder as an experimental intervention rather than replacing upstream ACT.
