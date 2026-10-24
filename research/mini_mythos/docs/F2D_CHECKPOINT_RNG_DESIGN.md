# F2-D Activation Checkpointing and RNG Design

Status: **PENDING CHATGPT REVIEW**. Design only. No test code and no experiment in this commit.

## 1. Checkpoint

- Repo: `leotree2020/OpenMythos`
- Branch: `mini-mythos-p1c-gate22c-readiness`
- Accepted F2-C close: `ca2389384ad6dabed0c1edf26161c9377f88cd68`
- F2-B close: `b15ed92255876b75233a813f5486d58abda239e8`
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`, clean
- AxoNN pin: `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`
- Python 3.11.2, PyTorch 2.14.1+cpu, no CUDA
- F2-B and F2-C evidence directories are present
- Unrelated dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` is preserved

## 2. Source call chain

Checkpointing is off unless `model.gradient_checkpointing` is true. The constructor default is false.

`activation_checkpoint_impl` default is `per-iteration`. Matching is substring based.

| Mode | Where it enters | What is wrapped |
|---|---|---|
| off | flag false | nothing |
| `per-iteration` | `iterate_forward`, grad steps only | `update_recurrent_state` |
| `per-block` | `core_block_forward` | each core block |
| `in-coda` | `forward` | coda blocks and `ln_f` |
| `reentrant` | wrapper choice | same call sites, reentrant backend |
| `sac*` | wrapper choice | selective checkpoint |

The no-grad loop is never wrapped. A fixed `num_steps_pair` bypasses the depth sampler.

## 3. PyTorch API

Pinned torch 2.14.1 `torch.utils.checkpoint.checkpoint` defaults to `preserve_rng_state=True`. If `use_reentrant` is omitted it warns and uses True.

Parcae does not use that default. `config.checkpoint` returns:

- normal `per-iteration` / `per-block`: `use_reentrant=False`, `preserve_rng_state=False`, `determinism_check="none"`
- `reentrant`: `use_reentrant=True`, `preserve_rng_state=True`
- SAC variants: `use_reentrant=False`, `preserve_rng_state=False`

So the default Parcae path does not ask PyTorch to restore RNG around recompute.

## 4. RNG

`state_init="like-init"` calls `torch.randn` and `trunc_normal_` in `initialize_state`. That runs before the recurrent loop, outside the checkpointed function.

The depth sampler uses its own CPU `Generator`, seeded from `514229 + model.step` and `317811 + model.step`. It does not consume the global RNG. Fixed `num_steps_pair` does not call it.

Dropout is configured at `p=0.0`. No dropout RNG is expected on this path.

CUDA RNG is not in scope. CPU only.

## 5. FULL and TBPTT

`(0,2)`: both steps are grad steps. `per-iteration` wraps both. `per-block` wraps blocks inside each step.

`(1,1)`: first step stays under `no_grad` and is not checkpointed. Second step is wrapped for `per-iteration`. Truncation semantics stay the same if recompute is faithful.

A hook on `update_recurrent_state` will see extra calls during backward for `per-iteration`. That is recompute, not an extra recurrence. `per-block` does not add `update_recurrent_state` calls.

## 6. Planned CPU matrix

Reuse the F2-B/F2-C 2→2→2 micro model, seed 42, eval, batch 1, length 8.

| ID | Mode | pair | Purpose |
|---|---|---|---|
| D1 | off | (0,2) | full baseline |
| D2 | per-iteration | (0,2) | full recompute |
| D3 | per-block | (0,2) | block recompute |
| D4 | off | (1,1) | truncated baseline |
| D5 | per-iteration | (1,1) | truncated recompute |
| D6 | per-block | (1,1) | truncated block recompute |
| D7 | off vs per-iteration, no fixed pair | sampler path | separate RNG check |

If a mode cannot be selected without editing Parcae, mark BLOCKED or NOT APPLICABLE.

## 7. Candidate acceptance, not frozen

Do not assume bit-exact output. Candidate for the same seed and weights:

- logits max abs <= `1e-6`
- loss within `1e-6 + 1e-6 * max(abs(L))`
- same gradient name set
- no missing, all-zero, or non-finite grads
- selected F2-C scalars within `1e-6 + 1e-5 * max(abs(g))`

This is a candidate because the backend is non-reentrant and `preserve_rng_state=False`. ChatGPT must freeze it before Stage B.

RNG comparison is CPU `torch.get_rng_state()` only. CUDA RNG is NOT TESTED.

## 8. Status rules

- PASS: defined checks meet the frozen rule
- FAIL: finite mismatch outside the rule, or missing/non-finite grads
- BLOCKED: mode unsupported, source mismatch, or dirty Parcae
- NOT TESTED: not run, including CUDA and unfixed depth sampling unless D7 is executed

Exit 0 alone is not PASS.

## 9. Risks

- Extra hook calls can be misread as extra recurrence.
- `preserve_rng_state=False` can diverge if a recomputed function consumes RNG.
- Substring matching can enable more than one site if the impl string contains several tokens.
- SAC and reentrant are out of the first matrix.

## 10. Stage B, not started

Planned file: `research/mini_mythos/tests/test_parcae_checkpoint_rng_cpu.py`  
Planned evidence: `research/mini_mythos/gate2_2/evidence/f2d/`

Next instruction: ChatGPT reviews and freezes the tolerance. Do not write the test before that.

Recommend Stage B only after that freeze. No GPU. No Parcae edit.
