# Mini-Mythos F2-D Stage A — Independent Review and Frozen D1–D6 CPU Gate

Date: 2026-10-25 (Asia/Tokyo)  
Reviewer: ChatGPT  
Reviewed Grok design: `68d283617d3076deb95dc541089c7588cc3b8c25`  
Decision: **D1–D6 DESIGN ACCEPTED / CPU B1 FIXED-DEPTH TEST AUTHORIZED. D7 UNFIXED-DEPTH SAMPLER DESIGN REVISION REQUIRED; D7 NOT AUTHORIZED.**  
This is a source/design review, **not** a completed F2-D numerical experiment.

## Checkpoint and reproducibility

- Repo `leotree2020/OpenMythos`; branch `mini-mythos-p1c-gate22c-readiness`.
- Prior F2-C acceptance `ca2389384ad6dabed0c1edf26161c9377f88cd68` remains PASS/CLOSED within its limited 3-scalar CPU scope. F2-B accepted `b15ed92255876b75233a813f5486d58abda239e8`.
- Pinned native Parcae `69284c13746e849104f738d6d1a347b1f457df76`, never modify; independent AxoNN `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`.
- Grok-reported environment Python 3.11.2 / PyTorch 2.14.1+cpu; no GPU. Preserve any unrelated local uncommitted `research/mini_mythos/gate2_1/TEST_RESULTS.json`; not inspected directly by ChatGPT.

## Verified source facts

1. `Parcae(..., gradient_checkpointing=False)` defaults to checkpoint off. `ParcaeConfig.activation_checkpoint_impl="per-iteration"` by default but has no effect while flag is false.
2. `iterate_forward` wraps `update_recurrent_state` **only for grad-enabled iterations** when the flag and `"per-iteration"` substring both match. The outer `with torch.no_grad():` portion is not wrapped at this site.
3. `core_block_forward` wraps **each core block invocation** when `"per-block"` matches and flag true. Thus, unlike `per-iteration`, wrapper calls are made **even inside no-grad iterations**; such no-grad calls are not themselves required to recompute during backward.
4. `forward` wraps coda blocks and final norm only when flag and `"in-coda"` match. Excluded from D1–D6 scope; do not claim tested.
5. `Config.checkpoint` defaults for named plain selectors to `use_reentrant=False, preserve_rng_state=False, determinism_check="none"`, versus reentrant selector's `use_reentrant=True,preserve_rng_state=True`. Whether any checkpoint call is *actually exercised* must be instrumented; substring selectors/combined selectors can activate more than one site. For D1–D6 use exact strings `per-iteration`, `per-block`, and flag false for off.
6. `initialize_state(state_init="like-init")` consumes the global CPU RNG before recurrence/checkpoint regions. Fixed `num_steps_pair` skips depth sampling; reset RNG to the same state before each compared forward.
7. **Correction to Grok's D7 description:** `randomized_iteration_sampler` starts with `torch.rand((1,)).is_meta`, which consumes a global CPU RNG draw on a real CPU, *before* constructing independently seeded CPU generators for depths. It is false to claim the sampler has no global-RNG impact. D7 must distinguish these effects.
8. **Correction to D7 mode:** when `model.eval()` and `num_steps_pair=None`, `randomized_iteration_sampler` returns `(mean_recurrence,0)`, so there are no grad-enabled recurrent steps to checkpoint. A meaningful *training sampler* test requires explicitly controlled `model.train()` (and `model.step`), not reusing the D1–D6 eval matrix.
9. PyTorch 2.14 checkpoint docs describe non-reentrant **early stop** of recomputation by default, and warn that `preserve_rng_state=False` omits RNG-state stashing; do not infer exact recomputation counts from completed hooks or assume each backward replay completes the entire wrapped function. Record entry/phase-level recomputation separately from true forward recurrence depth. Relevant docs: `https://docs.pytorch.org/docs/2.14/checkpoint.html`.
10. Pinned CPU SDPA fallback calls `torch.nn.functional.scaled_dot_product_attention` without overriding `dropout_p`; its effective default on this path is zero. Core blocks are not expected to draw RNG under this **fixed** no-dropout configuration, but this is a testable hypothesis, not proof of RNG invariance.

## Frozen B1 experimental matrix (D1–D6 only)

| ID | Flag | impl | fixed pair | Reference |
|---|---|---|---|---|
| D1 | False | per-iteration (ignored) | (0,2) | FULL baseline |
| D2 | True | per-iteration | (0,2) | Compare D1 |
| D3 | True | per-block | (0,2) | Compare D1 |
| D4 | False | per-iteration (ignored) | (1,1) | TBPTT baseline |
| D5 | True | per-iteration | (1,1) | Compare D4 |
| D6 | True | per-block | (1,1) | Compare D4 |

Only CPU, SDPA, float32, `state_init=like-init`, seed=42; unchanged F2-B/F2-C config (2/2/2, 247936 parameters), eval mode, batch=1, length=8, fixed token ids/labels; no data download. Instantiate identical model weights for each mode and verify a weight/state_dict checksum; independently reset the *same* CPU RNG state immediately before each compared forward, so checkpointing does not get a different initial `x0`. Repeat each mode at least twice. Pin the upstream source and require clean Parcae worktree and in-root import path.

### Frozen acceptance criteria — comparisons to D1/D4

- Verify mode actually activated: record checkpoint call sites and at least one **backward-phase re-execution of a checkpointed block** for each enabled mode. If no replay can be proven, `BLOCKED/NOT VALIDATED`, never mark PASS simply because tensors agree.
- Expected forward **logical recurrence** steps exactly 2 for each cell; `(0,2)` forward grad-mode flags `[True,True]`, `(1,1)` flags `[False,True]`. Distinguish pure forward phase versus backward replay; because of non-reentrant early-stop, do **not** freeze exact replay-hook counts.
- Frozen logits criterion: `max_abs(logits_mode-logits_baseline) <= 1e-6`.
- Frozen loss criterion: `abs(L_mode-L_baseline) <= 1e-6 + 1e-6 * max(abs(L_mode),abs(L_baseline))`.
- Gradient name set exactly matches the reference, with all 74 expected trainable tensor gradients present (if the pinned baseline confirms 74), finite, and not identically zero per parameter under the fixed baseline configuration. All parameter-gradient tensors compared elementwise with `abs(g_mode-g_base) <= 1e-6 + 1e-5 * max(abs(g_mode),abs(g_base))`; additionally report all three F2-C frozen scalar indices without reselection.
- Record CPU RNG bytewise snapshots: before forward (must be the same for each matched run), after forward, and after backward. Under the pinned no-dropout path the expected after-forward and after-backward CPU RNG states **match across off and checkpoint modes**, and post-backward matches post-forward within each individual run. A mismatch is a FAIL of the declared RNG-equivalence expectation pending minimal root-cause analysis, **not** proof of a model-architecture error.
- Each mode must repeat under identical seed/weights/inputs; log logits/loss/grad diff for repetitions and RNG snapshots. Require numerical comparison under the same tolerances above, exact bytewise RNG-state equality.
- No missing/NaN/Inf, code exceptions, malformed data, unexpected gradients, parameter mutation or source divergence. Record actual input hash, parameter checksum and thread count before execution.
- Synthetic negative guards must prove that a deliberately corrupted gradient, absent replay event and manipulated RNG snapshot cannot be marked PASS. The harness must propagate FAIL/BLOCKED/INCONCLUSIVE to meaningful nonzero process exit codes, with FAIL outranking INCONCLUSIVE.
- For each cell log purpose, environment, inputs, expectations, actual measurements, status and evidence paths. Save raw command/stdout/stderr/exit, Git SHA/status, SHA256. Do not modify previous evidence or upstream. A local Exit 0 alone is insufficient.

The 1e-6-level values are **predeclared CPU float32 equivalence tolerances** for these deterministic same-operator replay tests, *not* general architecture precision bounds. A failure should trigger a frozen-input minimal reproduction, not post-hoc tolerance relaxation.

## D7 held for amended design

Status: **DESIGN REVISION REQUIRED, NOT AUTHORIZED**. Prepare a design-only amendment before running it:

- Distinguish the global-RNG draw from `torch.rand((1,)).is_meta`, the global RNG consumed by `initialize_state`, and independent CPU-generator Poisson/depth draws.
- Use controlled `train()` for actual sampled training depth and freeze `model.step` as well as global seed, sampling scheme and loop depth pair; first obtain/log a sampled `(n,k)` with `k>0` if evaluating backward replay, without changing thresholds after the outcome.
- Separate `eval()` sampler semantics (`k=0`) from `train()` sampling and do not compare their gradients as if they represented the same computation.
- Define exact CPU RNG snapshot checkpoints and whether checkpointed recompute is supposed to re-enter sampling (it should not under the pinned code, since sampling occurs outside wrapped update function).
- Specify what happens if the chosen step yields no grad-steps, test instrumentation and stop conditions; do not silently change model.step/seed to force a PASS.
- Keep reentrant/SAC/in-coda out of the initial B1 matrix and mark them NOT TESTED. Avoid any claim about CUDA or distributed RNG.

## Overall decision and next instruction

- F2-D source audit and design of D1–D6: **PASS**.
- CPU phase B1: **AUTHORIZED for D1–D6 only**, with frozen criteria above.
- D7 unfixed-depth sampler: **NOT AUTHORIZED; design correction pending**.
- F2-D overall: **NOT TESTED**, cannot be closed from this review.
- `in-coda`, reentrant, SAC, CUDA, GPU training/MuonAdamW and Gate 2.2-C: **NOT TESTED**.

Next action for Grok: read this review checkpoint first, implement one isolated CPU harness for D1–D6 only, run controlled comparisons with negative controls and evidence, commit separately with `PENDING CHATGPT REVIEW`, then stop. Do not implement or run D7 until separate design review. Do not edit upstream Parcae/AxoNN, architecture, previous accepted F2-B/F2-C files or the unrelated `gate2_1` modification. CPU first, GPU only if subsequently authorized by a genuine CUDA/performance dependency.
