# Mini-Mythos F2-E-A — ChatGPT Independent Source Review and Frozen CPU B1 Gate

Date: 2026-10-25 (Asia/Tokyo)  
Reviewer: ChatGPT  
Reviewed design commit: `11666712cfbde9be5a6845876c4feb0088883b3e`  
Prior accepted F2-D checkpoint: `687a9ba730853ecfa8a23058016a7a5ab018d640`

**Decision:** **F2-E Stage A SOURCE/DESIGN REVIEW PASS WITH EXPLICIT MATHEMATICAL CORRECTIONS BELOW. F2-E B1 CPU ONLY AUTHORIZED UNDER THIS FROZEN GATE. F2-E NUMERICAL EXPERIMENTS NOT YET TESTED.** This file is a design/audit checkpoint, not an experimental result.

## 1. Provenance and conservation

- Repo: `leotree2020/OpenMythos`, branch `mini-mythos-p1c-gate22c-readiness`. The Grok design commit above is a docs-only, 106-line addition with parent exactly the F2-D final CPU checkpoint. GitHub branch HEAD was independently confirmed at this SHA before the review.
- Pinned native Parcae: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`, do not modify; independently pinned AxoNN `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`.
- Grok reports Python 3.11.2, PyTorch 2.14.1+cpu, clean pinned Parcae working tree and unrelated local change `research/mini_mythos/gate2_1/TEST_RESULTS.json`. ChatGPT checked GitHub, not Grok's local working tree.
- Closed F2-B, limited F2-C, and limited F2-D CPU checkpoint/sampler experiments remain PASS/CLOSED **within their own frozen scopes**. No merge or changes to their archived evidence.
- This design review directly compared Grok's document to pinned `parcae_lm/models/parcae/parcae.py`, `parcae_lm/models/parcae/config.py` and `parcae_lm/modules/injection.py`. Upstream intent remains **INTENT UNKNOWN** without explicit author testimony/documentation.

## 2. Critical source interpretation corrections (frozen)

Config defaults: `recurrent_iteration_method="per-batch"`, `sampling_scheme="poisson-truncated-full"`, `state_init="like-init"`. For the chosen micro-model `mean_recurrence=2`, `mean_backprop_depth=s=2`, `t=max(2-2,0)=0`.

**Per-batch scalar sampler** `randomized_iteration_sampler()`, in CPU train mode, `num_steps_pair=None`:

`T=max(Poisson(t+s; G_n),1)`; `n=T`; `k=min(T,s)`; outer Core updates `N=n+k=T+min(T,s)`.

**Per-sequence and per-token** `_sample_batch_depths()`, in CPU automatic-sampling mode:

`T_i=max(Poisson(t+s; G),1)`; `k_i=min(T_i,s)`; `n_i=T_i-k_i`; local accepted update count `N_i=n_i+k_i=T_i`.

**Correction C1:** Grok's E1 wording that per-batch adds no-grad iterations only when `T>s` is wrong. Compared with the per-element formula under the *same hypothetical T and s*, per-batch's total work differs by **k=min(T,s)**, including **T<=s**. Example T=1, s=2: per-batch (n,k)=(1,1), total=2; per-element (n,k)=(0,1), total=1. Both paths intentionally remain unmodified and the author's intent is unknown.

**Correction C2:** The per-element methods return `num_steps_no_grad = n_per_sample.float().mean().to(torch.long)` and analogous `k`: **the arithmetic means truncated to long for nonnegative depths**, not exact floating-point means. They differ from the external loop count `max(n_i)+max(k_i)`, and in general from `mean(n_i+k_i)`. Freeze all three separately; do not assert exact mean equality.

**Correction C3:** `torch.where(active_mask, x_new, x)` is executed AFTER the entire unmodified `update_recurrent_state` computation. It conditionally accepts updates into the recurrent state; inactive positions can still take part in computing `x_new` and interact with active tokens via attention. This is a *plausible coupling mechanism*, NOT experimentally established at this stage. Do not treat masked writes as skipping Core FLOPs, as no participation in attention, or as a guarantee of zero gradient through the old-state/other-token paths.

**Correction C4:** For per-element paths with `num_steps_pair=None`, the actual sequential scheduling is `range(max(n_i))` for ALL no-grad rounds, then `range(max(k_i))` for ALL grad rounds, using independent phase-local masks `step < n_i` / `step < k_i`. Do not assume an element's accepted grad rounds follow immediately after its own n_i updates: phase boundaries are GLOBAL and step IDs use the global maximum. Check those phase-specific masks, not a fictitious contiguous local schedule.

**RNG:** Scalar per-batch sampler has `torch.rand((1,)).is_meta` global CPU draw; per-element `_sample_batch_depths()` uses a locally seeded CPU Generator and **does not use** that scalar-sampler precheck. Both still call stochastic `initialize_state` first. Single-process, torch.distributed uninitialized must be recorded.

## 3. Frozen E1–E6 B1 matrix and inputs

Only native unmodified Parcae on CPU PyTorch 2.14.1+cpu, Python 3.11.2, `float32`, `attn_impl="sdpa"`, `state_init="like-init"`, 2 Prelude/2 Core/2 Coda model with **247936 parameters**, train mode, seed42, two CPU threads, no optimizer, no GPU/CUDA. `randomize_positions_from=None`, no dropout in this fixed configuration. Freeze model weight tensor-content hash to the accepted F2-D initial state; generate and **record** input tokens deterministically with explicit seed (seed 1000 recommended) per input shape; archive actual token IDs and SHA256 before run. Do not falsely claim B2/S8 input hashes equal to B1/S8 input.

| ID | Cell | Input | Sampling | Intended observation |
|---|---|---|---|---|
| E1 | per-batch, checkpoint OFF | B=1, S=8 | original, step=0, `num_steps_pair=None` | exact scalar n/k and logical n+k, RNG |
| E2 | per-sequence, checkpoint OFF | B=2, S=8 | original, step=0, `num_steps_pair=None` | `n_i,k_i` shape [2], per-seq accepted masks, maxima and truncated means |
| E3 | per-token, checkpoint OFF | B=2, S=8 | original, step=0, `num_steps_pair=None` | `n_i,k_i` shape [2,8], per-token masks, maxima and truncated means |
| E4 | E2 and E3 identical repeats | matched B/S | exact same seed, input, initial weights, step, RNG snapshots | sampler, outputs, gradients, masks and RNG reproducibility |
| E5 | E2/E3 checkpoint OFF vs `per-iteration` | matched B/S | same original sampling and same observed full n/k matrices | logits/loss/full-grad + RNG equivalence, genuine backward replay |
| E6 | isolated controlled per-token masks/perturbation | B=2, S=8 | TEST-ONLY controlled fixed n/k tensors supplied by a test-side sampler override | verify native recurrent `torch.where` mask/update semantics; separately observe potential cross-token coupling |

If E1 input/weights match previous F2-D baseline, cite its frozen hash; otherwise give a new hash and explanation. E2/E3 inputs require unique shape-scoped SHA256. For E6, ensure heterogeneous **source-plausible** n/k, for example choose T array with 1,2,3,4 and set each `k=min(T,2)`, `n=T-k`; prove shape [2,8], maxima >0, no unsafe all-zero-grad phase. E6 is a separately labeled **controlled intervention** in the test harness, **not** evidence that the native sampler produced those n/k; preserve its integrity separately from E3.

No seed/step search for favorable sampled depths. If step=0 per-element Poisson sampling lacks heterogeneous n/k sufficient for a particular E6 mask/coupling assertion, use the **predeclared E6 controlled mask only**. Do not retrospectively alter E2/E3 samples.

## 4. Frozen acceptance: source/reference math and instrumentation

A. **Source/version gate:** exact upstream source SHA and clean worktree, real import path under pinned root, exact environment, 247936 params, original weights and input fingerprints, train/eval flags, step, sampling scheme, no distributed init, CPU RNG before/after forward/after backward, no inadvertent optimizer/parameter changes. Any mismatch is FAIL/BLOCKED, never PASS.

B. **Original sampler audit:** `per-batch` must call `randomized_iteration_sampler` once and not `_sample_batch_depths`; `per-sequence/per-token` vice versa. Neither sampler called during backward replay. Hook each original sampler **once** without extra sampling or perturbing live RNG. Independently reconstruct frozen sample values from a separate CPU Generator seeded `(514229+step)%(2**31-1)`, with tensor shape matching mode, and compare every element of n/k/T, dtype, shape, and logical counts. Document per-batch extra global RNG draw, per-element absence of that sampler-side draw; do not equate GLOBAL CPU RNG across inherently different modes.

C. **External Core calls and local state acceptances:** Per-sequence/token external forward recurrent `update_recurrent_state` calls exactly `max(n_i)+max(k_i)`; each call executes 2 Core blocks irrespective of inactive positions. Forward records phase, logical call index, global step ID, active mask and shape; mask expansions `[B,1,1]` for per-sequence and `[B,S,1]` for per-token. Theoretical masked **accepted** update count for each element must equal `n_i+k_i`. Do not infer acceptance solely from update function invocation counts; verify `torch.where` behavior by an independent deterministic reference replay or phase-by-phase captured tensors, without changing upstream code. A source-only assumption without actual evidence is INCONCLUSIVE, not PASS. Reject incorrect broadcast/masks/counters.

D. **Returned metrics:** For per-element methods, assert the returned scalar long means equal `floor(mean(n_i))` and `floor(mean(k_i))`, with safe, nonnegative source assumptions; check outer max counters separately. Record exact untruncated means for diagnosis (not compared as scalar returned values). For per-batch, returned n/k are sampled scalars, not per-element means.

E. **Gradient and checkpoint equivalence:** Same-mode repeat E4 and matched OFF/ON E5 only, with exact same sampled full n/k tensor, input, weights, RNG snapshots, masks, grad-phase scheduling and nonstochastic Core; no cross-mode numerical-equality requirement. Use frozen F2-D CPU thresholds:
- logits max absolute difference `<=1e-6`;
- loss absolute `<=1e-6 + 1e-6*max(|L1|,|L2|)`;
- each gradient element `<=1e-6 + 1e-5*max(|g1|,|g2|)`.
- Match complete 74 parameter tensor gradient name set (known pinned 2/2/2 config), require finite and nonzero (for nondegenerate frozen inputs) in BOTH comparator legs, log extra/missing/zero tensors. Record three F2-C frozen named Core scalar indices, no reselection. Evidence of checkpoint wrapper call and at least one actual backward-phase recomputation is required for enabled modes when grad steps exist; distinguish backward replay from forward logical Core depth. Do not freeze exact replay-hook counts due PyTorch non-reentrant early stop.

F. **Mask/coupling E6 controlled question:** No hardcoded expectation that inactive earlier token MUST numerically change a later active token. Using same frozen native Core, compare input state `x` and a copy with only a predeclared earlier **currently inactive** token state's value perturbed; hold `input_embeds`, positions, causal attention mask, sampled n/k, weights and RNG fixed. Record output change on active later token, on inactive selected branch, and full logits if possible. Separate an algebraic `torch.where` test (inactive selected state exactly equals old state; accepted selected state equals `x_new`) from the full native attention path. The existence/magnitude of causal cross-token influence is a **hypothesis outcome**: use a predeclared +0.1 perturbation in exactly one recurrent-state channel of an earlier currently inactive token j=0, with a later active token i=1; keep all other state and embeddings identical, and verify the applied perturbation magnitude. On the identical baseline, separately perturb the active token i=1 by +0.1 in one channel as a positive control. For the active-token response report DETECTED when its maximum absolute state delta is strictly >1e-6, NOT DETECTED when <=1e-6 **only if** the positive control has a measured delta >1e-6, else INCONCLUSIVE. This 1e-6 is an exploratory observation sensitivity floor, not a proof of zero coupling below it. A negative/non-detect is not proof of no possible coupling and does not invalidate already passing sampler arithmetic.

G. **Synthetic negative tests using real acceptance functions:** corrupted n/k values or shape; incorrect mask broadcast; wrong maxima/outer call counts; wrong truncated returned mean; missing/extra sampler event in backward; RNG mismatch; missing/extra/NaN/Inf/zero gradient; missing checkpoint replay; altered weight/input fingerprint. Require negative tests result in FAIL/BLOCKED/INCONCLUSIVE rather than PASS and nonzero exit for formal non-PASS statuses. Do not use fixed string comparisons as acceptance substitutes.

H. **Experiment status:** each cell logs purpose, environment, inputs, expected, actual observations and `PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT TESTED/NOT APPLICABLE` with explicit reason. Exit 0 alone not PASS. Fail closed; never relax thresholds after seeing results. If the native per-sequence/token path cannot execute under pins, record source stack trace and BLOCKED rather than patching upstream.

## 5. Output and change isolation

- Only after reading this frozen gate: implement independent `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`; keep exact original model imports and upstream unmodified.
- Run E1–E5 CPU and the predeclared isolated E6 reference/perturbation. E6 coupling conclusion is exploratory and must not be promoted to a forced PASS/FAIL of native sampling correctness.
- Save isolated raw per-cell evidence in `research/mini_mythos/gate2_2/evidence/f2e/b1/`: `F2E_B1_RESULTS.json`, exact script version/commit, `RUN_META.json`, raw stdout/stderr/actual exit, SHA256, invocation and core-call observations, full sampled tensors n/k/T, masks/selected updates, model weight SHA256, input IDs/hash, per-mode losses/logit/grads comparison summaries and 3 frozen Core scalars, negative results.
- Submit one isolated **new** Git commit with test harness, evidence and docs; do not change the already accepted F2-E-A design or old F2-B/C/D docs/results, upstream Parcae/AxoNN, model architecture, dependencies or the unrelated dirty `gate2_1/TEST_RESULTS.json`.
- After B1 commit, stop with `PENDING CHATGPT REVIEW` and include exact Git status/head, dependencies, unresolved math/intent issues and next instructions. No merge or GPU.

## 6. Stage decisions

- F2-E-A source audit and controlled design: **PASS with C1–C4 corrected and frozen here**.
- F2-E-B1 CPU execution: **AUTHORIZED under this exact gate**; no experiment has been run by this ChatGPT review.
- F2-E mathematical sampler correctness, gradient-routing and causal attention interaction: **NOT TESTED pending Grok's B1 evidence and ChatGPT independent audit**.
- Upstream author's scalar-vs-per-element n/k intent: **INTENT UNKNOWN**. Do NOT mark as a proven bug or modify native code.
- F2-D's frozen CPU scope: remains **PASS/CLOSED**.
- Optimizer, native train.py, reentrant/in-coda/SAC, distributed and GPU: **NOT TESTED**, not licensed by this gate.

**Next instruction:** Grok reads this checkpoint first, performs only the frozen CPU B1 with evidence, stops PENDING CHATGPT REVIEW for independent cross-audit. If mask/coupling instrumentation cannot be non-invasive, mark E6 BLOCKED/INCONCLUSIVE and submit partial B1 with precise unresolved reason rather than editing the original recurrent Transformer.
