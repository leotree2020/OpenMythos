# F2-D D7 Sampler and CPU RNG Design

Status: **PENDING CHATGPT REVIEW**. Design only. No probe and no D7 run in this commit.

## 1. Checkpoint

- Repo: `leotree2020/OpenMythos`
- Branch: `mini-mythos-p1c-gate22c-readiness`
- D1–D6 close: `1ed99746c48878840794688c219f4c741bfd154e`
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`, clean
- Python 3.11.2, PyTorch 2.14.1+cpu, no CUDA
- Unrelated dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` is preserved

## 2. Call chain

`num_steps_pair is None` is the only path that samples.

Order inside one forward:

1. Optional position randomization. Default `randomize_positions_from=None`, so it does not run.
2. Embedding.
3. `iterate_forward` calls `initialize_state`.
4. `randomized_iteration_sampler`.
5. no-grad loop of `n`, then grad loop of `k`.
6. Loss and backward.

Sampler is called before the loop. Checkpoint wraps `update_recurrent_state` or core blocks, not the sampler.

## 3. Three RNG sources

| Step | Source | What it does |
|---|---|---|
| `initialize_state` like-init | global CPU RNG | `torch.randn` and `trunc_normal_` |
| sampler entry | global CPU RNG | `torch.rand((1,)).is_meta` consumes one draw on real CPU |
| depth sample | independent CPU `Generator` | seeded from `model.step`, not global RNG |
| core loop | none expected | dropout is `p=0.0` |

Seeds:

- `seed_n = 514229 + model.step`
- `seed_k = 317811 + model.step`

Fixed `model.step` does not freeze the global RNG. The `is_meta` draw still advances it.

## 4. Train and eval

Eval returns `(mean_recurrence, 0)`. For the 2/2/2 micro model that is `(2, 0)`. No grad steps. Do not compare eval gradients to train gradients.

Train uses the scheme branch. Default scheme is `poisson-truncated-full`.

With `mean_recurrence=2` and `mean_backprop_depth=2`:

- `t = 0`, `s = 2`
- default scheme samples `poisson(t+s)=poisson(2)`, then clamps
- `n` is not constantly 0 under this default scheme
- `fixed` and `poisson-fill` do give `n=0` for this config

Train mode does not add dropout RNG. It does not call `optimizer.step`.

## 5. Checkpoint interaction

Sampling happens once, outside the wrapped function. Backward recompute must not call the sampler again. Extra `update_recurrent_state` or block calls in backward are replay, not a new depth sample.

Compare checkpoint on/off only when the recorded `(n,k)` matches.

## 6. Proposed CPU matrix

Reuse the 2/2/2 micro model. `model.train()`. No optimizer step. Seed 42. Same input as D1–D6.

| ID | Mode | step | Purpose |
|---|---|---|---|
| S1 | train, off | 0 | sample baseline |
| S2 | train, per-iteration | 0 | same state, checkpoint |
| S3 | train, per-block | 0 | same state, block checkpoint |
| S4 | repeat S1 | 0 | same `(n,k)` and RNG |
| S5 | train, off | 1 | seed changes; value may or may not change |
| S6 | eval, off | 0 | expect `(2,0)`, no grad compare |

Do not search seeds to force a result.

## 7. Candidate acceptance, not frozen

- Same state repeat: same `(n,k)`, same logits, same loss, same CPU RNG snapshots.
- Checkpoint compare only if `(n,k)` matches. Then reuse D1–D6 numeric tolerances.
- If `k=0`, gradient compare is NOT APPLICABLE, not PASS.
- Sampler call count is 1 in forward and 0 in backward.
- Logical steps equal `n+k`. Replay is recorded separately.

These stay candidates until ChatGPT freezes them.

## 8. Negatives

The future evaluator must reject:

- wrong recorded `(n,k)`
- RNG snapshot mismatch
- missing backward replay when checkpoint is on and `k>0`
- gradient mismatch when `(n,k)` matches

## 9. Open risks

- Exact `poisson-truncated-full` assignment needs a frozen reading before Stage B. The source sets `n` from the clamped Poisson and `k = clamp(n, max=s)` without a later `n = n-k` in the scalar sampler.
- Train mode may still differ from eval through past-key-value handling. That is not a gradient-equivalence claim.
- CUDA RNG is NOT TESTED.

## 10. Stage B, not started

Planned file: `research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py`  
Planned evidence: `research/mini_mythos/gate2_2/evidence/f2d/d7/`

Do not write the probe until ChatGPT freezes the gate.
