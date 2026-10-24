# F2-C Experiment Design

Status: **DESIGN ONLY**. Pending ChatGPT review. No test code in this commit.

## 1. Research state

- Repo: leotree2020/OpenMythos
- Branch: mini-mythos-p1c-gate22c-readiness
- Accepted checkpoint: `b15ed92255876b75233a813f5486d58abda239e8`
- Acceptance: `research/mini_mythos/docs/F2B_FINAL_ACCEPTANCE_20261024.md`
- Parcae: `69284c13746e849104f738d6d1a347b1f457df76`, clean
- AxoNN pin recorded as `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`
- Local unrelated dirty file `research/mini_mythos/gate2_1/TEST_RESULTS.json` is preserved
- Python 3.11.2, PyTorch 2.14.1+cpu, no CUDA

F2-B is closed. It showed mechanism and gradient presence, not derivative correctness.

## 2. Math

Let one core update be \(f_\theta\). Shared core weights are \(\theta\).

Full graph, `num_steps_pair=(0,2)`:

\[
x_0 = s,\quad x_1 = f_\theta(x_0),\quad x_2 = f_\theta(x_1),\quad L = \ell(x_2)
\]

Autograd \(g_{\mathrm{full}}\) includes both uses of \(\theta\).

Truncated graph, `num_steps_pair=(1,1)`:

\[
x_1 = f_\theta(x_0)\ \text{under no\_grad},\quad x_2 = f_\theta(x_1),\quad L = \ell(x_2)
\]

Autograd \(g_{\mathrm{trunc}}\) treats \(x_1\) as a constant. It does not include the first use of \(\theta\).

A finite difference of the whole `(1,1)` function is not the right reference, because the first step still depends numerically on \(\theta\).

## 3. Numerical references

Central difference, declared before any run:

\[
g_{\mathrm{fd}} = \frac{L(\theta+\varepsilon)-L(\theta-\varepsilon)}{2\varepsilon}
\]

Full reference: \(L\) is the native `(0,2)` loss. Seed is reset before every forward.

Truncated reference, built on the test side without editing Parcae:

1. Seed and run the first core step under `no_grad`.
2. Detach that state as \(x_1\).
3. Rebuild only the differentiable suffix with the same module objects: second `core_block_forward`, `C`, coda, `ln_f`, head, cross entropy.
4. Keep any other path that native `(1,1)` still differentiates. Do not freeze those.
5. Compare suffix autograd to suffix finite difference.
6. Also compare suffix autograd to native `(1,1)` autograd on the same scalar. That checks the reconstruction.

## 4. dtype finding

Native path is not end-to-end float64. `parcae.py` does `self.lm_head(x).float()` before cross entropy. A `.double()` model still returned a float32 loss in a one-forward probe.

Native float64: **BLOCKED**. Do not edit Parcae to remove the cast.

Isolated alternative for review: a test-side float64 suffix that calls the same modules, used only as a math reference, not as a native-path claim. Native evidence stays float32.

## 5. Controls

- Same 2→2→2 config as F2-B. Expected params 247936.
- seed 42 before init and before every compared forward.
- `state_init` remains `like-init`. Reseed is the control. Do not switch it.
- eval mode. `randomize_positions_from` is None. No dropout on this path.
- batch 1, seq 8, hand-made token ids, labels equal to ids.
- Select 2–3 core tensors with nonzero F2-B grads, then one scalar each with \(|g|\) clearly above 1e-3.
- Restore every perturbed value in `try/finally`.

## 6. Candidate acceptance, not frozen

Float64 candidate, only if the isolated suffix is approved:

\[
|g_{ad}-g_{fd}| \le 10^{-5} + 10^{-3}\max(|g_{ad}|,|g_{fd}|)
\]

Two epsilons, \(10^{-4}\) and \(10^{-3}\). Both must pass. Non-finite is FAIL. Near-zero scalars are not selected.

Native float32 tolerance is not frozen here. It needs a separate justification after ChatGPT chooses the path.

Negative case: compare `(1,1)` and `(0,2)` on a scalar where the known max abs gap is about 0.344. Detection succeeds if the absolute gap is greater than 1e-2. Agreement would be FAIL for the negative test.

## 7. Pass / fail

| Item | Pass | Fail | Blocked |
|---|---|---|---|
| Full graph | ad and fd within frozen tol at both eps | outside tol or non-finite | dtype or API prevents the defined graph |
| Truncated graph | suffix ad matches native `(1,1)` ad, and matches suffix fd | either mismatch | suffix cannot be built without editing Parcae |
| Negative | `(0,2)` vs `(1,1)` gap above 1e-2 | they match | selected scalar is near zero |
| Native float64 | n/a | n/a | BLOCKED by `.float()` cast |

## 8. Cost and traps

CPU only. A few dozen forwards on a 248k model. Seconds.

Traps: like-init RNG if seed is not reset; comparing truncated ad to full-function fd; float32 noise if the float64 suffix is not approved; shared storage if a perturbed tensor is not restored; reconstructing the suffix in a way that drops a still-live path.

## 9. Planned files, not created now

- `research/mini_mythos/tests/test_parcae_gradient_math_cpu.py`
- `research/mini_mythos/gate2_2/evidence/f2c/`

No GPU. No Parcae or AxoNN edit. No F2-B overwrite.
