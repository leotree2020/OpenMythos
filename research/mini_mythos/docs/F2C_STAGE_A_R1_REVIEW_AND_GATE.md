# Mini-Mythos F2-C — Stage A-R1 Independent Review and Frozen B1 Gate

Date: 2026-10-24 (Asia/Tokyo)  
Reviewer: ChatGPT  
Reviewed design: `4a149a783c19404b4668c5f9bb70dd4c07fbb3b4`  
Status: **A-R1 DESIGN ACCEPTED with explicitly limited numerical criteria. STAGE B1 ONLY authorized (CPU harness + discovery); confirmatory B2 is NOT yet authorized.**

## Provenance / limits

- Working branch: `mini-mythos-p1c-gate22c-readiness`.
- Previous F2-B formally accepted at `b15ed92255876b75233a813f5486d58abda239e8`.
- Native Parcae source pinned to `69284c13746e849104f738d6d1a347b1f457df76`. Never modify upstream Parcae or AxoNN.
- Exact current design `research/mini_mythos/docs/F2C_GRADIENT_MATH_DESIGN.md` is docs-only. The reviewer verified the commit has one changed file (+57/-75). No new tests or numerical experiments were executed by ChatGPT during this review.
- Grok-reported local dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` must be preserved and not mixed into this stage.
- Pinned Parcae uses `.float()` on head logits and explicit float32 RoPE intermediates. Therefore the **pure native float64** target is BLOCKED; a small `AUX64` surrogate can verify numerical-test machinery but cannot independently prove native-model gradients correct.

## Mathematical design decision

1. **PASS**: `NATIVE32_FULL=(0,2)` is the full autograd graph; finite-difference the **same native computation with the same RNG realization**, after restoring parameters.
2. **PASS (design only)**: `NATIVE32_TBPTT=(1,1)` is a truncated graph. Fix first recurrent state `x1` at baseline parameters once, then differentiate the exact same second-core-step / C / coda / norm / head / loss suffix. Never finite-difference the original whole `(1,1)` as a reference for its truncated autograd gradient.
3. **PASS**: Only independent scalar parameters owned by `transformer.core_block.*` are in scope for the first experiment. Report named tensors/indices and alias checks. The captured `input_embeds`, freqs, mask, IDs, module state and step=1/total_steps=2 must be preserved, along with the original head scaling, any softcap, objective/ignore_index and coda VE index logic. Test-side source inspection must establish exact suffix equivalence before any confirmation claims.
4. **PASS**: Selection of a negative-control parameter is discovery followed by a **frozen** selection manifest. F2-B `0.344...` is a global maximum across all parameters and proves nothing by itself about a chosen core scalar.
5. **NOT TESTED**: Any native CPU numerical derivative correctness experiment. The current approval is a design review, not an observed numerical PASS.

## Frozen exploratory B1 rules (do not silently relax after results)

These rules govern *selection, instrumentation, and feasibility* only. They do not authorize declaring the entire F2-C mathematical result PASS.

### Controls

- CPU only; float32 for native tests. Same pinned unmodified 2/2/2 Parcae micro architecture as F2-B; expected parameters 247,936. Record Python, PyTorch, CPU threads, Git HEAD and upstream cleanliness before any run.
- Eval mode; manually fixed input (batch=1, length=8), vocab 128, seed=42; keep `state_init=like-init` and reset seed before every native `forward`. Ensure both full and truncated comparisons use identical model weights, input and RNG realization.
- Do not change existing F2-B artifacts. New `f2c` evidence directory only. Restore perturbed scalar weights with a `try/finally`-equivalent guarantee, and verify before/after parameter equality.
- Compute AD gradients at unperturbed weights. Negative control: discover Core scalars satisfying `|g|>1e-3` and `|g_FULL-g_TBPTT|>1e-2`, recording exact (parameter name, index, original parameter value, gradients, seed, input checksum) in a manifest. Prefer 2–3 distinct Core tensors, one scalar per tensor; if insufficient, record exact number and mark limited/INCONCLUSIVE, not a model FAIL. Do not switch indices after confirmation begins.

### Precision preconditions for native finite differences

Use candidate central-difference steps `h=1e-3` and `h=1e-2`. These are **fixed exploratory grid choices** rather than a claim that every parameter has an adequate finite-difference signal.

- Actual stored perturbations `theta_plus`, `theta_minus` must be distinct from baseline in float32, and `h_+ = theta_plus-theta_0`, `h_- = theta_0-theta_minus` must be positive. Record effective perturbations and any asymmetry; use the actual total separation in the divided difference. If deviation between positive and negative steps exceeds 1% of their mean, mark that point INCONCLUSIVE.
- Baseline native loss must be exactly reproducible under controlled repeat (fixed seeds and weights); otherwise BLOCKED for numeric interpretation.
- For **each h**, require `|L(theta_plus)-L(theta_minus)| >= 16 * max(ulp32(L(theta_plus)),ulp32(L(theta_minus)))`, where `ulp32` is spacing of adjacent representable float32 values at that loss magnitude. This is a **signal-resolution gate**, not evidence of gradient correctness on its own. A scalar not meeting it is INCONCLUSIVE for that h. No PASS claims based on a few float32 ulps.
- Compare `g_AD` and `g_FD` only after these gates. Exploratory candidate error envelope: `abs(g_AD-g_FD) <= 1e-3 + 1e-2 * max(abs(g_AD),abs(g_FD))` for each h. A signal-qualified, finite, stable point outside this **pre-registered exploratory envelope** is a discrepancy requiring investigation, not automatic proof of a bug in native Parcae.
- For stability, additionally report `abs(g_FD(h1)-g_FD(h2))` and the two individual error bounds. If the two FD values differ by more than the sum of two error bounds, mark NUMERICALLY UNSTABLE / INCONCLUSIVE rather than claim mathematical correctness. Never tune the epsilon grid or thresholds based on confirmatory results.
- Finiteness, name/index validity, tensor ownership and restoration are hard guards. A failure in the model forward/backward/finite gradients is FAIL for that defined test; invalid precision resolution is INCONCLUSIVE; unavailable dependency/source is BLOCKED.

### Truncated-suffix reconstruction gates

- Capture `x1` returned by the first no-grad `update_recurrent_state` in native `(1,1)`, clone/detach at base parameters and hold fixed for suffix FD perturbations. Record all relevant inputs and ensure no alias or storage mutation. Do not recapture `x1` after perturbing the Core scalar.
- Use the same `core_block_forward` (or equivalent `update_recurrent_state` with identical operator paths) at step=1/total_steps=2, then same C, coda, ln_f, logits cast and cross-entropy. Explicitly preserve logit scale, softcap (if configured), coda value embedding indices, and relevant mask/position behavior.
- Before suffix finite differences: require native `(1,1)` and suffix baseline logits agree with maximum absolute difference <= `1e-6`; losses agree within `1e-6 + 1e-6 * max(abs(L_native),abs(L_suffix))`; and selected Core scalar AD gradients agree within `1e-6 + 1e-5 * max(abs(g_native),abs(g_suffix))`. All values must be finite. These are **pre-registered reconstruction criteria**, not full-model gradcheck.
- If a reconstruction criterion fails, label `SUFFIX RECONSTRUCTION FAIL / NOT VALIDATED` (not native Parcae gradient failure) and halt the truncated finite-difference claim; preserve the evidence. Proceeding to compare its FD against native TBPTT would be invalid.

### AUX64 harness (optional, independent toy)

- Pure float64 independent analytical function (e.g. smooth polynomial + trig) with known derivative; never call it a native Parcae reference.
- Exploratory toy check with `h in {1e-4,1e-3}` and `abs(g_AD-g_FD)<=1e-5+1e-3*max(abs(g_AD),abs(g_FD))`, both h, finite outputs.
- Report `AUX64 PASS` independently; it cannot upgrade native mathematical verification status.

### Negative control and pre-registered manifest

- Report `(name,index)` and both `g_FULL,g_TBPTT` during discovery; negative detection threshold `|g_FULL-g_TBPTT|>1e-2` is **frozen**. If no scalar meets it, mark the targeted negative control INCONCLUSIVE / NOT TESTED, not FAIL of native Parcae.
- After discovery write a Git-tracked `F2C_DISCOVERY_MANIFEST.json` with source/environment/input/seed and exact selected scalar(s), their stored values, thresholds, and hashes. **Stop before B2 confirmation** and return for independent ChatGPT review. Do not use confirmation outcome to change the manifest.

## Stage decision / next step

- **A-R1 design: ACCEPTED with the safeguards above.**
- **Stage B1: AUTHORIZED — write the isolated CPU harness and run exploratory/discovery checks only, using the fixed rules; no GPU, no dependency upgrade, no upstream edits.**
- **Stage B2 confirmatory numerical mathematical validation: NOT AUTHORIZED yet; wait for the frozen discovery manifest and ChatGPT's review.**
- Exact next Grok action: read this file and pinned source, then implement an isolated F2-C CPU harness and discovery manifest only; commit code/results/logs/status with PASS/FAIL/BLOCKED/INCONCLUSIVE at experiment-item level, overall `PENDING CHATGPT REVIEW`. Save Git status, dependency versions, remaining issues and B2 next command. Do not alter `gate2_1/TEST_RESULTS.json`.
