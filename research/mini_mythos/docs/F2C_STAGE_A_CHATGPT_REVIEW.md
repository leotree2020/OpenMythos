# F2-C Stage A — ChatGPT independent mathematical design review

Date: 2026-10-24 Asia/Tokyo  
Status: **DESIGN REVISION REQUIRED — Stage B NOT AUTHORIZED**  
Reviewed Grok design commit: `db291ab7987a826d4b62c0d66a3bf6fe79ff9fc3`  
Last accepted F2-B checkpoint: `b15ed92255876b75233a813f5486d58abda239e8`  
Pinned native Parcae: `69284c13746e849104f738d6d1a347b1f457df76`

## Review scope and evidence

Read the 111-line `research/mini_mythos/docs/F2C_GRADIENT_MATH_DESIGN.md` at its exact commit and inspected pinned upstream Parcae `parcae_lm/models/parcae/parcae.py`, `parcae_lm/models/parcae/config.py`, and `parcae_lm/modules/utils.py`. Commit changes **only one design document**; no new tests or numeric experiments were claimed. The Grok-reported working-tree cleanliness and local environment were **not independently reproduced**.

## Accepted parts

1. `(0,2)` full unrolled gradient includes both uses of shared core parameters.
2. `(1,1)` TBPTT treats first-step output `x1` as constant for backpropagation; a finite difference of the whole original forward function is **not** a valid reference for TBPTT gradients.
3. Seed/state freezing, CPU-first, no upstream modifications, no GPU, design-before-code are sound.
4. For a legitimate suffix reference, the differentiable suffix must preserve all still-live paths; compare its AD gradient with native TBPTT AD as a reconstruction check before its finite differences.

## Required design revisions (no code yet)

### M1 — Precision / objective identity (blocking)

Native Parcae casts logits with `self.lm_head(x).float()` before cross entropy. Additionally, `parcae_lm/modules/utils.py` uses explicit float32 in `precompute_freqs_cis()` and `apply_rotary_emb_complex_like()`. Therefore calling `.double()` does **not** create a pure float64 native computation graph. Do not assert native full-fp64 capability or assume fp64 finite-difference thresholds apply to native behavior.

Split into clearly named *different objectives*:

- `NATIVE32_FULL`: native full graph `(0,2)`, ordinary original forward, native mixed/fp32 operators; compare native AD against finite difference of **the same frozen-RNG native function**.
- `NATIVE32_TBPTT`: native `(1,1)` AD compared against a carefully reconstructed, native-operator suffix where `x1` is frozen **at base parameters** before perturbing. Compare suffix AD to native TBPTT AD first; then suffix AD to suffix FD **of the identical suffix objective**.
- `AUX64` (optional, supplemental): an isolated fully double differentiable surrogate (only if each internal op/dtype is confirmed), AD vs FD for that surrogate. This is **not** direct verification of the unmodified native forward, especially if head or RoPE casts are removed or replaced test-side.

The original design's epsilon `1e-4`, `1e-3` and `1e-5 + 1e-3 * max(...)` may be retained as *candidate exclusively for a genuinely float64, smooth auxiliary objective*. They are not approved for native fp32/mixed-precision comparisons. Explain the native finite-difference step-size grid and threshold using an explicit float32 error budget and sensitivity model, and declare *before confirmatory execution*. Don't loosen thresholds after observing a failure.

### M2 — Restrict selected parameters and preserve differentiable paths (blocking)

Initially test only independently owned, trainable `model.transformer.core_block.*` scalar parameters. Document exact tensor names and scalar indices and rule out parameter aliases/ties. In pinned upstream code, the recurrence reads `input_embeds`, per-layer value embeddings indexed from `model._current_input_ids`, and step/total_steps via `core_block_forward`. A suffix replay must preserve these inputs and the native functions, including `transformer.C`, coda, `ln_f`, lm head, cross-entropy, objective configuration, and `step=1,total_steps=2`. Freeze first state `x1` under base parameters and `no_grad` **once**, not separately recompute it after each parameter perturbation. Preserve any other differentiable path into the suffix. Do not claim whole-model TBPTT validation if only core parameters were tested.

### M3 — Negative control selection (blocking)

The prior F2-B recorded `grad_max_abs ~0.344` over **all trainable parameter tensors**, not a named scalar in `transformer.core_block.*`. It does not guarantee the preselected core scalars exceed the proposed `1e-2` difference. Require a *separately labeled discovery step* that identifies nonzero gradient core scalars and freezes exact (tensor name, element index) prior to confirmatory checks, or use a mathematically controlled toy negative example. If no qualifying core scalar exists, mark this particular negative control `INCONCLUSIVE/NOT TESTED`, not a core-model `FAIL`. Never tune the negative threshold after examining confirmatory outcomes.

### M4 — Acceptance freeze / error attribution (blocking)

Submit explicit stage-specific expected observable, FAIL vs BLOCKED vs NOT TESTED rules, epsilon grid, absolute and relative error formula and *numerical justification for native precision*, independent repeat controls, and both forward-objective equality and AD reconstruction equivalence checks. A `float64` surrogate may establish mathematical-method correctness only; a native objective requires comparison to the exact same native operator sequence. Do not run confirmatory experiments until the design thresholds and compared functions have been reviewed/frozen.

## Stage gate

- Git/document-only Stage A preparation: **PASS**.
- Fundamental full-vs-truncated graph definition: **PASS**.
- Native pure-fp64 availability: **BLOCKED** by deliberate float32 conversions.
- Suffix objective equivalence and mathematical reference: **PENDING DESIGN REVISION**.
- Numerical finite-difference tolerances: **NOT FROZEN**.
- Phase B code and CPU execution: **NOT AUTHORIZED / NOT TESTED**.
- GPU/native train.py/MuonAdamW/Gate2.2-C: **NOT TESTED**.

## Next instruction to Grok

Revise **only** `research/mini_mythos/docs/F2C_GRADIENT_MATH_DESIGN.md` to incorporate M1–M4. No test script, no numerical run, no GPU, no Parcae/AxoNN edits, no dependency install, no changes to F2-B evidence, no merge into the base research branch. Submit an independent docs-only commit with Git status and clearly state `PENDING CHATGPT REVIEW`. Then stop. ChatGPT will review the revised design and freeze supported acceptance criteria before authorizing F2-C Stage B.
