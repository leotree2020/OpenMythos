# Mini-Mythos F2-E B1 — ChatGPT Independent Review and Minimal R1 Gate

Date: 2026-10-25 (Asia/Tokyo)  
Reviewer: ChatGPT (GitHub source, result, independent SHA-256 verification; **not a separate native CPU model rerun**)  
Reviewed Grok experiment commit: `bcfd38e77bae2524d58b560d79920e2106fd1f03`  
Frozen F2-E A gate: `23ec183c3af3b439ab50c90bf0d874c64679d154`  
Prior F2-D accepted checkpoint: `687a9ba730853ecfa8a23058016a7a5ab018d640`

**Decision: F2-E B1 OVERALL PENDING R1. Do not close. E1–E3 sampled source formula / outer call count evidence is positive; E4/E5 only cover per-sequence and miss the required per-token cases; E6 exploratory coupling is INCONCLUSIVE as a causal claim due to failed intervention isolation. No original Parcae model defect established.**

## 1. Git, provenance and independent integrity

- Repo `leotree2020/OpenMythos`, branch `mini-mythos-p1c-gate22c-readiness`, reviewed commit a direct child of the frozen F2-E A gate, verified HEAD at audit time.
- Exactly seven **new** files: one isolated probe `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`, one result document, five evidence files (+879/-0 according to the GitHub commit file list; no existing research files modified). Historic F2-B/C/D acceptance files and Parcae/AxoNN sources unchanged.
- Grok reports separate pinned upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` clean, Python 3.11.2, torch 2.14.1+cpu, x86_64 and exit 0; no GPU. Repo local dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` reported by Grok, not independently inspected. Preserve it untouched.
- Model micro-config: 2/2/2, 247936 parameters, CPU SDPA float32, `state_init=like-init`, `mean_recurrence=2`, `mean_backprop_depth=2`, seed 42 for model/forward, 1000 for input; actual recorded weight SHA `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`, B1 input SHA `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`, B2 input SHA `ba67e905c68c9fcd61eb3ab5a028ef28ea5c575be78b84d18212ea68e6f900ae`.
- Independent recomputation from exact committed UTF-8 ASCII artifacts matches all `RUN_META.json` SHA256:
  - `F2E_B1_RESULTS.json`: `cfa698eecdd34fbcb99f65d576122095999665823033399ee63bb897ea09c9b1`
  - `stdout.txt`: `7836a732ee844f68f4620ac27878201afbb7221ff7b06434c380535f04818535`
  - `stderr.txt` empty: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
  - `exit_code.txt` containing `EXIT:0\n`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`.
- Integrity and Exit 0 do NOT prove full frozen acceptance.

## 2. Source-corroborated observations

- E1 `per-batch` native sampler observed n=[1],k=[1], outer=2; scalar sampler invoked.
- E2 `per-sequence` native sampler n=[0,0],k=[1,2], outer=2. Recurrent `torch.where` mask expanded [2,1,1] with true counts 2,1 across its two grad rounds. These match expected accepted grad updates=3, no-grad=0.
- E3 `per-token` native sampler n=[[0,0,0,1,0,0,1,0],[1,0,0,2,0,0,0,5]], k=[[1,2,2,2,2,1,2,1],[2,2,1,2,2,1,2,2]], outer=7 (max(n)=5 plus max(k)=2). No-grad intended accepted count=sum(n)=10; grad=sum(k)=27; the 5 recurrent no-grad mask true counts 5,2,1,1,1 and 2 grad mask counts 16,11 match. Expected mask broadcast [2,8,1].
- `torch.where` monkeypatch also logs unrelated Boolean masks [1,8,64]/[2,8,64] at the top of mask arrays. They are **not** native recurrence acceptance masks. The present harness does not explicitly filter or tie recorded masks to precise loop phase, global step, n/k and where-specific callsite.
- The probe computes `returned_n`/`returned_k` itself from captured n/k. Its `returned = out.get("num_steps_no_grad")` is unused because `forward()` does not expose iterate-forward depth metrics. Hence comparing the **recomputed** mean to a recomputed reference is circular; the exact native truncated means have not been directly captured/validated.
- E4 tests `per-sequence` repeat only. E5 checkpoint OFF/ON tests `per-sequence` only. The frozen gate also requires **per-token** repeated run and same-mode checkpoint pair; these have not run.
- E4 and E5 archive only PASS labels, no actual `logit_max_abs`, `loss_delta`, `grad_max_abs`, gradient count, Frozen 3 scalar values, backward replay count or CPU RNG pair matching; `evaluate_pair` does not enforce matched RNG/weight/input identity, does not verify baseline 74 gradient names/finite/nonzero, and does not enforce zero sampler calls during backward. It only requires `row["replay"]>=1` for enabled; no actual per-iteration replay diagnostics are recorded.
- E6 has an important **invalid inference**. The code uses `base=make_model(root,"per-batch")` then monkeypatches `base._sample_batch_depths`: this patched function is **never used by the per-batch model**. The proposed n=[[0,1]],k=[[0,1]] is not source-plausible for the selected default clipped-Poisson per-token sampler, either. Its separate `update_recurrent_state()` comparison perturbs token 0, but computes `max(abs(y1-y0))` across **all tokens**, not the later active token. Therefore 0.424110174 is not evidence that an inactive earlier token causally changed a later token. Positive control 0.277730137 also uses max across all tokens. The actual recurrence mask is not applied to these compared updates; attention mask is all-ones rather than a separately verified intended causal mask. The simple algebraic `torch.where` example passed, but is a distinct observation. Reclassify E6 cross-token claim as **INCONCLUSIVE**, keep raw measurement as unassigned whole-tensor delta, do not overwrite original result file.
- The current `synthetic()` only covers altered n/k, outer step count, a surrogate mean, and backward sampler call, not the gate's required wrong mask, shape, gradient, RNG, checkpoint-replay, or identity negative controls.
- Author intent of `per-batch n=T` vs `per-element n=T-k`: **INTENT UNKNOWN**, not proven bug. Cross-mode logits equality NOT APPLICABLE.

## 3. Minimal R1 correction and frozen boundaries (no redesign / no seed search)

### R1-A: Actual recurrent mask and returned metrics evidence

- Keep pinned source and all model math. Instrument the **actual** `iterate_forward()` return tuple once without altering or re-running the original: archive the returned `num_steps_no_grad` and `num_steps_with_grad` as native outputs; assert native nonnegative integer long-truncated means equal independent expectations for per-element mode, and distinguish external maxima from exact untruncated means.
- Filter `torch.where` capture to the actual per-sequence/per-token recurrent update selection, tagged by `phase={no_grad,grad}`, zero-based phase-loop index and global step, shape [B,1,1] or [B,S,1], **full Boolean mask** or a deterministic hash plus per-element counters, and expected `step < n_i` / `step < k_i`. Avoid matching solely on the existence of the same shape elsewhere; the unrelated [B,S,64] masks must not be included. Validate *actual* write selection `torch.where(active, x_new, x)` via captured pre/post tensors or a verified equivalent noninvasive reference; mere outer update call count is insufficient.
- For E1–E3 log sampler route counts, sampled n/k/T full arrays and seeds, RNG state before/after forward/backward, block-level logical count, actual active-mask accepted counts and actual returned metrics. Compare real values to reference; no self-referential `returned_n` assertion. Save method/training/step/shape/config/weight SHA & input tokens and SHA for every cell.

### R1-B: Finish the original E4/E5 matrix

- Add **per-token** identical repeat (E4 token), and **per-token** checkpoint OFF vs per-iteration ON (E5 token), alongside existing per-sequence cases. Freeze same weights, seed, model.step, input, complete sampler tensors and pre-forward CPU RNG across each matched pair; record and enforce equality. No extra sampling scheme/mode, no changing thresholds.
- For BOTH E2 and E3 pairings, validate both sides' complete expected 74 gradient names, finite/nonzero tensors, logits/loss and elementwise all-grad comparison at originally frozen CPU tolerances (logits <=1e-6, loss <=1e-6+1e-6*max(abs), per gradient <=1e-6+1e-5*max(abs)). Record three frozen F2-C scalar names/indices for the same parameters. Verify actual backward checkpoint replay events and **no sampler calls during backward**, logically distinct from external forward steps. Enforce identical source/weight/input hashes before and after all relevant runs; actual model parameters may not change without optimizer step. Archive numeric measured maxima, not just status labels.

### R1-C: E6 exploratory, correctly controlled or INCONCLUSIVE

- E6 must use a fresh `per-token` model with batch=2, seq_len=8 and **source-plausible** predetermined heterogeneous T matrix (each T>=1), `k=min(T,2)`, `n=T-k`. Mark test-side sampler interception explicitly as `CONTROLLED`, not original sampled E3.
- Choose e.g. batch0 earlier token j=0 with T=1 (n=0) and later token i=1 with T=4 (n=2). At no-grad step0, j is inactive and i active. Capture actual old state `x`, `x_new` and masked output for that **exact** recurrent iteration; hold input embeddings, positions, attention mask, weights, seed and phase/counters fixed between perturbations. Confirm intended causal attention mask, actual native recurrent `torch.where` selection and report **only the target later active token**'s response to +0.1 applied to one earlier inactive token state channel, plus positive control of +0.1 on the target active token itself. Use pre-frozen observation floor strictly >1e-6: DETECTED / NOT DETECTED conditional on positive control / INCONCLUSIVE.
- An all-token maximum difference, uncontrolled direct Core call, or experiment that never enters the per-token masked loop **cannot** justify coupling DETECTED. If noninvasive attribution cannot be achieved, mark E6 `INCONCLUSIVE` (or BLOCKED with cause); do not turn it into a model-architecture change or extend experiments. A separate algebraic where sanity check may PASS without causal attribution. E6 exploratory outcome does NOT block independent E1–E5 correctness closure.

### R1-D: Negative tests, statuses, isolated evidence

- Real production acceptance functions must reject incorrect n/k and tensor shapes; wrong recurrent mask content, shape and broadcaster; max-loop counts; returned metric truncation; missing/extra sampler events incl backward resampling; mismatched pre-forward RNG and weight/input fingerprints; missing/replayed checkpoint event; missing/extra/NaN/Inf/zero tensor gradients and numerical differences. Exercise actual nonzero `exit_code` policy; do not treat synthetic string-check as proof.
- Log purpose, expected and observed per cell and clear PASS/FAIL/BLOCKED/INCONCLUSIVE/NOT TESTED/NOT APPLICABLE. Cross-mode logits remains NOT APPLICABLE. E6 DETECTED/NOT DETECTED is exploratory, not a blanket PASS, and INCONCLUSIVE is an acceptable accurately documented partial result for E6.
- Run only the frozen CPU E1–E6 after harness correction (same model, inputs, initial weights, seeds, thresholds). Archive **new** results in `research/mini_mythos/gate2_2/evidence/f2e/b1r1/`, including exact git rev/status, PyTorch/Python/thread settings, actual command, per-mode events/masks, raw stdout/stderr/exit and SHA256. Preserve original B1 raw evidence and all older checkpoints. Only modify the dedicated F2-E probe plus new isolated evidence/document; no upstream Parcae/AxoNN patches, GPU, dependencies, native training, merge or change to unrelated local dirty `gate2_1/TEST_RESULTS.json`.
- Submit isolated R1 commit and **STOP** as `PENDING CHATGPT REVIEW`. ChatGPT independent review will decide E1–E5 full acceptance and separate E6 exploratory status.

## 4. Current stage statuses / next handoff

| Stage | Outcome |
|---|---|
| F2-B / F2-C / F2-D frozen accepted scopes | PASS / CLOSED (unchanged) |
| F2-E-A source design | PASS / CLOSED |
| F2-E B1 scalar/per-element sampled n/k and outer count as observed | POSITIVE SOURCE-CONSISTENT EVIDENCE |
| F2-E B1 E4/E5 full frozen matrix | NOT COMPLETED (per-token missing) |
| F2-E E6 attention-mediated inactive-to-active causal claim | INCONCLUSIVE (original whole-tensor delta not target-specific) |
| F2-E B1 formal closure | **PENDING R1** |
| Native upstream algorithm author intent | **INTENT UNKNOWN** |
| CUDA / optimizer / full training / Gate 2.2-C | **NOT TESTED** |

**Next:** execute R1 minimal harness completion only, return Git commit and evidence for independent cross-audit. Exit 0 on existing B1 and valid SHA archives are recorded evidence facts, **not** grounds to close untested cells.
