# F2-E Sampling Semantics Design

Status: **PENDING CHATGPT REVIEW**. Design only. No probe and no experiment in this commit.

## 1. Checkpoint

- Repo: `leotree2020/OpenMythos`
- Branch: `mini-mythos-p1c-gate22c-readiness`
- F2-D close: `687a9ba730853ecfa8a23058016a7a5ab018d640`
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`, clean
- AxoNN pin: `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`
- Python 3.11.2, PyTorch 2.14.1+cpu, no CUDA
- Unrelated dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` is preserved

F2-B, F2-C and F2-D stay closed. This design does not reopen them.

## 2. Call chain

Default method is `per-batch`. Default scheme is `poisson-truncated-full`.

- `per-batch` uses `randomized_iteration_sampler` (`parcae.py` 389–476).
- `per-sequence` and `per-token` use `_sample_batch_depths` (`parcae.py` 478–534).
- The outer loop count is the max depth (`parcae.py` 273–274).
- The returned mean is not the loop count (`parcae.py` 276–277).

## 3. E1 formulas

Source fact, not a bug claim.

For `T = max(Poisson(t+s), 1)` and `s = mean_backprop_depth`:

| T | per-batch n | k | N=n+k | per-seq/token n | k | N=n+k |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1 | 1 | 2 | 0 | 1 | 1 |
| 2 | 2 | 2 | 4 | 0 | 2 | 2 |
| 3 | 3 | 2 | 5 | 1 | 2 | 3 |
| 4 | 4 | 2 | 6 | 2 | 2 | 4 |
| 5 | 5 | 2 | 7 | 3 | 2 | 5 |

per-batch executes extra no-grad steps when `T > s` only if `n=T` stays above `k`. per-sequence/token keeps total depth at `T`.

`mean_recurrence` and `mean_backprop_depth` set `t` and `s`. They are not the executed loop counts.

## 4. E2 mask

Source: `parcae.py` 335–356.

- `active_mask = step < n_per_sample` or `step < k_per_sample`.
- per-sequence expands to `[batch, 1, 1]`.
- per-token expands to `[batch, seq, 1]`.
- Inactive positions keep the previous state.
- `update_recurrent_state` still runs before the `torch.where`.

Hypothesis, not proven: an inactive token can still affect other tokens through attention inside `x_new`. Stage B should test this. Do not treat “not written” as “no influence”.

## 5. E3 executed depth

The outer loop uses `max(n)` and `max(k)`. A sample or token only accepts an update while its own counter is active. The returned `num_steps_*` is the mean, so it can differ from the loop count. These three numbers must not be mixed.

## 6. E4 gradient routing

- The no-grad loop is under `torch.no_grad()`.
- `torch.where` routes gradient through the selected branch.
- Shared Core parameters accumulate gradients from all active positions.
- Different modes are not required to match logits or gradients.
- Checkpoint wraps the update call, then the mask is applied outside that call.

Comparable cases:

- A. Same mode, same input and RNG.
- B. Same mode, checkpoint off versus on.
- C. Different modes. Difference is expected. Not an equivalence test.

## 7. Intent

README has no statement that chooses `n=T` versus `n=T-k`. The two functions are both in the pinned source. **INTENT UNKNOWN.** Do not fix either path.

## 8. Proposed CPU matrix, not run

Reuse the 2/2/2 micro model, 247936 parameters, CPU float32 SDPA, seed 42. No optimizer step.

| ID | Mode | Input | Purpose |
|---|---|---|---|
| E1 | per-batch | batch 1 | locked scalar formula |
| E2 | per-sequence | batch 2 | max loop versus per-sample updates |
| E3 | per-token | batch 2, length 8 | mask and attention hypothesis |
| E4 | repeat E2/E3 | same | reproducibility |
| E5 | same mode, off and per-iteration | same | checkpoint equivalence |
| E6 | controlled mask | fixed depths | inactive token influence |

New inputs need new hashes. Do not require cross-mode logits to match.

## 9. Candidate acceptance, not frozen

- Record sampled tensors, outer loop counts, accepted updates and returned means separately.
- Same-mode repeats must match within the F2-D numeric tolerances.
- Checkpoint compare only when sampled tensors match.
- Cross-mode compare is NOT APPLICABLE.
- Negatives must reject bad n/k, bad shape, bad mask, loop/max mismatch, missing gradient and RNG change.

## 10. Stage B, not started

Planned file: `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`  
Planned evidence: `research/mini_mythos/gate2_2/evidence/f2e/`

Do not write the probe until ChatGPT freezes the gate. I recommend review before Stage B.
