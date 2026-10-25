# Mini-Mythos F2-D D7 A-R1 — ChatGPT Independent Sampler Audit and Frozen CPU B1 Gate

Date: 2026-10-25 Asia/Tokyo  
Reviewed Grok design commit: `7ee5e6b5618f2a7fa57334706d90b14706d126b0`  
Prior closed D1–D6 checkpoint: `1ed99746c48878840794688c219f4c741bfd154e`  
Decision: **D7 A-R1 SOURCE AUDIT PASS WITH THE CORRECTED N/K MATHEMATICS BELOW. D7 CPU B1 LIMITED EXPERIMENT AUTHORIZED ONLY UNDER THE FROZEN RULES IN THIS FILE. D7 FINAL PASS NOT YET DEMONSTRATED.**

## 1. Git, scope, source and evidence limits

- Repo: `leotree2020/OpenMythos`; branch `mini-mythos-p1c-gate22c-readiness`.
- Pinned unmodified native Parcae: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`. AxoNN independent pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`, no edits to either upstream.
- Grok's 111-line D7 design is docs-only; its Git parent is the D1–D6 accepted checkpoint. No D7 experiments have been executed or independently claimed by ChatGPT at this gate.
- Reported environment: Python 3.11.2, PyTorch 2.14.1+cpu, no CUDA. Preserve the unrelated uncommitted `research/mini_mythos/gate2_1/TEST_RESULTS.json`; do not include it in this stage.
- Prior F2-B, F2-C and D1–D6 pass/closure remains untouched. Do not over-claim independent model CPU rerun from a GitHub source audit.

## 2. Frozen source-level mathematical interpretation

The default `ParcaeConfig.recurrent_iteration_method` is `"per-batch"`. `ParcaeConfig.sampling_scheme` is `"poisson-truncated-full"`. `Parcae.step` initially equals `0`.

For this exact `per-batch` + training + non-meta CPU path, the upstream `randomized_iteration_sampler()` performs:

1. `torch.rand((1,)).is_meta` — on ordinary CPU, obtains a real random float and consumes **global CPU RNG**, then condition is false.
2. Creates *independent* CPU generators with `seed_n=(514229+model.step)%(2**31-1)` and `seed_k=(317811+model.step)%(2**31-1)`. Ignore distributed-rank modifications only for the pinned **single-process, uninitialized torch.distributed** CPU environment.
3. With `t=max(mean_recurrence-mean_backprop_depth,0)=0`, `s=mean_backprop_depth=2`, it samples `T=max(Poisson(t+s=2; generator=n_generator),1)` and returns **`n=T`, `k=min(T,s)`**, each converted to long, with no `n=T-k` subtraction. Although `k_generator` is initialized, this default branch does **not** use it to generate `k`.
4. Consequently, executed forward recurrence updates = `n+k=T+min(T,2)`, and **k>=1** in this selected train-mode branch. Do not treat T as executed total steps, or assume n=0 merely because t=0.
5. In contrast, upstream `_sample_batch_depths()` for `per-sequence/per-token` computes `n=T-k`, `k=min(T,s)`; this is a **real implementation semantic discrepancy**. It might be intentional or erroneous; this stage tests faithful behavior of pinned source, **not** the author's intended mathematical algorithm. Do not edit architecture/source to reconcile.
6. `initialize_state(state_init="like-init")` consumes global CPU RNG before sampler; default `randomize_positions_from=None` avoids position RNG. Fixed `num_steps_pair` bypasses the per-batch sampler. `sampler()` resides before recurrent checkpointed calls; its own body is not wrapped in checkpoint recomputation.
7. When `eval()` and `num_steps_pair=None`, source still enters the sampler and consumes the initial global `torch.rand` draw, but returns `(mean_recurrence,0)=(2,0)`; this mode is not a training-depth or Core-gradient equivalence case.

Native source read directly from pinned `parcae_lm/models/parcae/config.py` and `parcae_lm/models/parcae/parcae.py` for constructor, `iterate_forward`, `randomized_iteration_sampler`, `_sample_batch_depths`, `initialize_state`. Call-site and checkpoint branches in same pinned file.

## 3. Frozen minimal CPU B1 cells

Default micro-model 2 Prelude, 2 Core, 2 Coda, 247936 parameters, CPU SDPA float32, seed=42, `state_init=like-init`, batch=1, length=8, **same frozen input bytes and model weights as accepted D1–D6**, and 2 CPU threads. All comparison cells use **training mode only**, and `num_steps_pair=None`, no optimizer step or learning. Restore the same global CPU RNG state immediately before each matched forward; preserve model.step for each cell.

| ID | Mode | step | Scope |
|---|---|---:|---|
| S1 | train, checkpoint OFF | 0 | baseline sampled (n,k) |
| S2 | train, per-iteration | 0 | compare S1, same sampled (n,k) |
| S3 | train, per-block | 0 | compare S1, same sampled (n,k) |
| S4 | repeat S1 | 0 | fresh repeat with identical weights/seed/state |
| S5 | train, checkpoint OFF | 1 | isolated sampler seed-change control; may sample same values |
| S6 | eval, checkpoint OFF | 0 | sampling semantics (2,0), **forward-only**; no training gradient comparison |

Run S1, S2, S3 each at least twice with the same initial conditions; S4 provides an additional explicit independent baseline replay. If training and eval mode changes buffer/state behavior, compare **within matching train mode only**. No step-search, no seed-search to force a desired (n,k).

## 4. Frozen observables and numerical acceptance

**Strict provenance:** Record exact Git SHA/status of both repos and actual Parcae import path, exact torch/Python, CPU threads, seed and step, sampling scheme, training flag, config, input hash, state_dict tensor-content hash (names/shapes/dtypes/bytes). Before each matched forward validate identical parameters and source; check parameter weights remain unchanged after backward. Use a fail-closed status mapper (FAIL > BLOCKED > INCONCLUSIVE > PASS).

**Sampler instrumentation:** Wrap `randomized_iteration_sampler` in test code **only to call original once** and record returned n,k with entry and exit CPU RNG snapshots. Do not call sampler twice, alter return tensors or global RNG, or use extra random draws in the live path. Record observed logical no-grad/grad forward calls separately from backward replay. Assert sampler forward calls exactly **1**, backward calls **0** per automatic-depth forward; check n,k dtype/shape and exact agreement with logical calls.

**Source-reference math:** For S1/S2/S3/S4/S5, independently construct an *isolated local CPU Generator* with pinned seed_n, sample Poisson(2), clamp to >=1, then check **observed `n=T`, `k=min(T,2)`, logical steps `n+k`**. This reference Generator must not consume/modify global model RNG, and its source semantics must match the pinned code. Record the exact sampled T/n/k values and seeds, not just PASS/FAIL. For S6, demand actual n=2,k=0, logical forward steps=2; no core gradient requirement.

**Sampler RNG accounting:** Record global CPU RNG SHA256 at: (i) immediately before model forward; (ii) at sampler entry (after `initialize_state`); (iii) immediately after sampler return; (iv) after model forward; (v) after backward (where backward is applicable). To establish the single `torch.rand((1,))` consumption, use a **separate shadow CPU Generator** initialized from the captured sampler-entry RNG state, draw exactly one `torch.rand((1,),generator=shadow)`, and compare shadow state to captured sampler-exit state. Never advance the live RNG during this reference. For this fixed-no-dropout CPU path, expect after-backward global RNG state to equal after-forward; demand matching snapshots between identically initialized checkpoint-off/on train comparison cells. Do not demand before-forward equals after-forward (state initialization plus sampler consume RNG).

**Checkpoint equivalence:** S1, S2 and S3 comparisons are valid **only if** training flag, step, weights, input, pre-forward RNG and observed (n,k) match. If they mismatch, mark BLOCKED / invalid pairing, never grade tensor agreement. Then use the already frozen D1–D6 tolerances: logits maximum abs <= `1e-6`, loss delta <= `1e-6+1e-6*max(|L1|,|L2|)`, per-gradient-element delta <= `1e-6+1e-5*max(|g1|,|g2|)`. Require exactly the same complete gradient-name set, expected count 74 under pinned config, all finite with no all-zero trainable parameter gradient tensors; include the three named pre-frozen F2-C scalar components, without reselection. Require sampler not called during backward, and a backward-phase checkpoint replay event in S2/S3 if k>0. Never freeze exact replay counts because of non-reentrant early-stop. Recurrence forward update count must equal n+k, forward no-grad/grad flags must match n/k.

**Repeat and controlled step-change:** S1, S2, S3 each run twice with independently restored identical weights and RNG states; compare n,k, losses/logits, all gradients, CPU RNG and recompute observations; S4 repeats S1. S5 must use step=1 and independently seeded reference sampler; **do not require different sampled n,k from step=0**, only correct seed and reproducibility of the observed sample. For S5 checkpoint equivalence is NOT TESTED (only OFF). For S6 eval, verify sampler once and CPU RNG accounting, but no grad/backward comparison to training.

**Synthetic negative controls:** The same production evaluator must reject (i) altered sampled n or k (including n+k count mismatch); (ii) RNG entry/exit mismatch; (iii) missing sampler call or extra sampler call during backward; (iv) missing backward replay with k>0 for checkpoint-on; (v) corrupted/missing gradient tensor. Synthetic negative verdicts FAIL/BLOCKED as applicable, nonzero process exit; do not use hardcoded strings to simulate an evaluator result.

**Status semantics:** PASS only when all applicable predeclared checks pass; FAIL for computed mismatch or invalid finite/malformed states; BLOCKED for unavailable/dirty pinned source, unsupported mode or invalid comparison pairing; INCONCLUSIVE for incomplete observation with no justified correctness inference; NOT APPLICABLE for S6 train-only gradient/replay checks; NOT TESTED for unrun D7 branches/CUDA/etc. Exit 0 alone never constitutes PASS. Preserve all stdout/stderr/actual exit code and SHA256.

## 5. Limits, separate hypotheses and safety

- This B1 tests **faithful behavior of upstream per-batch default sampling**, not whether the apparent scalar-vs-per-sample n/k discrepancy is an upstream bug. Document the discrepancy as OPEN QUESTION, do not fix it silently.
- Test-side hooks can change semantics; record the original function identities/imports, use wrappers that call the original exactly once and do not touch RNG or grad modes. A diagnostic-only negative must not taint the main comparison.
- Train uses no stochastic dropout for the selected pinned configuration and no randomized positions. `preserve_rng_state=False` for plain non-reentrant checkpoint is a scoped risk; no proof for genuinely stochastic checkpointed code or any CUDA behavior.
- `per-sequence`, `per-token`, `in-coda`, reentrant, SAC, GPU/CUDA, native full `train.py`, optimizer MuonAdamW, Gate 2.2-C and distributed execution remain NOT TESTED.
- CPU priority. No dependency install/upgrade, no source edits, no model-architecture edits, no speculative bug fixes, no prior evidence changes, no branch merge.

## 6. Checkpoint and exact next instruction to Grok

- D1–D6 is already PASS/CLOSED, F2-C PASS/CLOSED.
- **D7 A-R1 source-level/math/design: PASS / CLOSED within this scope.**
- **D7 B1 CPU controlled sampler experiment: AUTHORIZED ONLY as defined above**.
- **D7 final mathematical correctness and entire F2-D stage: NOT TESTED / OPEN**.

Next: Grok reads this frozen review **first**. Implement only `research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py`, run S1–S6 CPU suite with separate fresh `research/mini_mythos/gate2_2/evidence/f2d/d7/` directory. Archive per-cell real n/k, sampler entry/exit RNG, reference sample T, forward and replay, full gradients/numerical diffs, synthetic negative outcomes, SHA256, Git HEAD/status, dependencies, stdout/stderr/exit and next instructions. Submit an isolated commit and stop at `PENDING CHATGPT REVIEW`. Do not run GPU, change upstream, edit D1–D6 data, include the unrelated `gate2_1` local change, or claim final F2-D PASS.
