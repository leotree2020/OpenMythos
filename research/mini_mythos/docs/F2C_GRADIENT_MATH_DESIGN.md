# F2-C Experiment Design, revision A-R1

Status: **PENDING CHATGPT REVIEW**. Design only. Stage B is not authorized.

Reviewed against `research/mini_mythos/docs/F2C_STAGE_A_CHATGPT_REVIEW.md` at `172a64c4a5b60d16d6f3e80d78959c8feaeb7766`.

## 0. State

- Branch: `mini-mythos-p1c-gate22c-readiness`
- Prior design: `db291ab7987a826d4b62c0d66a3bf6fe79ff9fc3`
- F2-B close: `b15ed92255876b75233a813f5486d58abda239e8`
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`
- Native float64 remains BLOCKED. `lm_head(x).float()` and RoPE float32 casts in `parcae_lm/modules/utils.py` are deliberate.

## 1. Three objectives

`NATIVE32_FULL`  
Native `(0,2)` function. Same seed before every call. Compare native autograd to a finite difference of that same native function. This is the native full graph. It is mixed float32, not float64.

`NATIVE32_TBPTT`  
Native `(1,1)` autograd, plus a suffix reference that freezes the first-step state. Compare suffix autograd to native `(1,1)` autograd first. Only if that matches, compare suffix autograd to a finite difference of the suffix. Do not finite-difference the whole `(1,1)` forward.

`AUX64`  
Optional harness check on a small test-side float64 function. It does not call Parcae. It is not a native float64 reproduction. It only checks that the finite-difference procedure can recover a known derivative.

## 2. Truncated suffix

First version selects only `transformer.core_block.*` parameters.

Freeze `x1` at the baseline parameter:

1. Set seed 42.
2. Hook `update_recurrent_state`.
3. Run native `(1,1)`.
4. Clone and detach the tensor returned by the first call. That is `x1`.
5. Record the call inputs: `input_embeds`, `freqs_cis`, mask, `step`, `total_steps`, and `_current_input_ids`.

Suffix, using the same module objects:

1. Set `_current_input_ids` to the recorded ids.
2. Call `core_block_forward(x1, input_embeds, freqs_cis, mask, step=1, total_steps=2)`.
3. Apply `transformer.C`, coda blocks, `ln_f`, `lm_head`, and cross entropy with the same labels and `ignore_index` as native forward.
4. Value embeddings stay inside `core_block_forward`, looked up from the same ids.

Gradient paths kept for a `core_block` parameter: the second core call, then C, coda, head, and loss. Injection parameters are not in this first selection. Prelude does not depend on core weights. The first core call stays frozen.

Reconstruction check: native `(1,1)` autograd and suffix autograd on the frozen scalar must agree before any finite difference. Disagreement means the suffix is wrong. That is BLOCKED for the TBPTT finite-difference claim, not a model FAIL.

## 3. Negative control

F2-B `grad_max_abs ≈ 0.344` is over all trainable tensors. It does not name a core scalar.

Two steps, in order:

1. Discovery. Compute `(0,2)` and `(1,1)` grads for `transformer.core_block.*`. Record scalars with `|g| > 1e-3` and `|g_full - g_trunc| > 1e-2`. Write the exact `(name, index)` list to a discovery artifact.
2. Confirmation. Use only that frozen list. Do not replace an entry after seeing the confirmatory result.

If discovery finds no such scalar, the negative control is `INCONCLUSIVE / NOT TESTED`, not a model FAIL.

## 4. Error budget, not frozen

Native float32. Machine epsilon is about `1e-7`. Loss is about 5. Central-difference rounding is about `u * L / ε`. At `ε = 1e-3` that is about `5e-4`. Truncation is `O(ε²)` and is not known a priori.

Candidate grid for native objectives: `ε ∈ {1e-3, 1e-2}`.  
Candidate native rule, not a pass bar:

\[
|g_{ad}-g_{fd}| \le 10^{-3} + 10^{-2}\max(|g_{ad}|,|g_{fd}|)
\]

This is wider than the float64 candidate on purpose. It is not frozen.

AUX64 candidate, only for the non-Parcae harness:

\[
|g_{ad}-g_{fd}| \le 10^{-5} + 10^{-3}\max(|g_{ad}|,|g_{fd}|)
\]

with `ε ∈ {1e-4, 1e-3}`. Do not apply this rule to native mixed float32.

Non-finite values are FAIL on the objective being tested. A near-zero scalar is not selected. Independent repeats use the same seed and must match before the tolerance is interpreted.

## 5. Status

| Item | State |
|---|---|
| Full vs truncated definition | PASS from prior review |
| Native float64 | BLOCKED |
| Suffix definition | revised, pending review |
| Tolerances | NOT FROZEN |
| Stage B | NOT AUTHORIZED |

No Parcae or AxoNN edit. No GPU. No numeric experiment in this commit.
