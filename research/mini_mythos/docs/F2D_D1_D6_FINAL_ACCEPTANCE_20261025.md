# Mini-Mythos — F2-D D1–D6 Final CPU Acceptance

Date: 2026-10-25 (Asia/Tokyo)  
Independent reviewer: ChatGPT  
Final decision: **PASS / CLOSED FOR D1–D6 ONLY**. F2-D D7 and the entire F2-D phase are **NOT CLOSED**.  
Audit method: connected GitHub review of exact commit and unmodified historical records, inspection of probe and results, independent SHA-256 recomputation. **Not** an independent Parcae model CPU rerun by ChatGPT.

## 1. Source, Git status and prerequisites

- Repository `leotree2020/OpenMythos`, branch `mini-mythos-p1c-gate22c-readiness`.
- Frozen F2-D A design gate: `10b9bd5ada1da5c1c20054dfdb6c6fe4a861950d`.
- First D1–D6 B1 run: `80a99e8aa0afb470f745981f0218fb833bbe7c1c`.
- Independent review requiring hardening: `6ac48c95568e61fe50e58de04148c311ab00b7d3`.
- Reviewed B1-R1 commit: `b2ef7517f2fadba4f0a71b5263b35d885c5ef92c`; direct child of the review, GitHub branch HEAD confirmed at this SHA.
- B1-R1 commit contains seven modified/added files: only the F2-D CPU probe was modified and separate `b1r1` evidence/document files were added (+982/-69). Previously accepted F2-B, F2-C and original B1 evidence not changed by this commit.
- Native Parcae source fixed to `69284c13746e849104f738d6d1a347b1f457df76`, recorded Git status clean; AxoNN separate pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`. **No upstream source edits.**
- Grok reports an unrelated pre-existing local modification at `research/mini_mythos/gate2_1/TEST_RESULTS.json` still untouched; not independently inspected by ChatGPT. Do not clean/commit it in a later phase.

## 2. Experimental purpose, setup, inputs and expected behavior

Purpose: verify original Parcae native CPU non-reentrant activation checkpoint equivalence versus checkpoint-OFF for **fixed** recurrence depths and full vs truncated backpropagation, including controlled CPU RNG and independent backward-recompute evidence.

- Recorded environment: Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, 2 CPU threads; no CUDA/GPU.
- Micro model: 2 Prelude / 2 Recurrent Core / 2 Coda layers; 247,936 parameters; float32, CPU SDPA, eval, `state_init="like-init"`. Seed 42 for initialization/forward and seed 1000 for synthetic input creation; batch 1, token length 8.
- Pinned input SHA-256 `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`.
- Model state fingerprint SHA-256 computed over sorted state_dict tensor name, shape, dtype and real bytes: `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`.
- Before and after every matched run, selected mode weights were checked against the baseline fingerprint; each cell was executed twice with reset global CPU RNG and fixed pair.
- Frozen equivalence tolerances: logits max absolute `<=1e-6`; loss absolute `<=1e-6 + 1e-6*max(abs(L1),abs(L2))`; gradient elementwise `<=1e-6 + 1e-5*max(abs(g1),abs(g2))`; exactly 74 nonmissing, finite, nonzero gradient tensors; exact CPU RNG state digest equality at comparable snapshots and after-backward vs after-forward.
- Expected two logical forward recurrence steps; full pair `(0,2)` grad flags `[True,True]`; truncated `(1,1)` flags `[False,True]`. Recompute phase events recorded separately; do not treat them as extra logical recurrence steps.

## 3. Actual recorded results

| Cell | Mode | Fixed pair | Forward steps | Backward replay updates / blocks | Status |
|---|---|---|---:|---|---|
| D1 | OFF | (0,2) | 2 | 0 / 0 | PASS baseline |
| D2 | per-iteration | (0,2) | 2 | 2 / 4 | PASS |
| D3 | per-block | (0,2) | 2 | 0 / 4 | PASS |
| D4 | OFF | (1,1) | 2 | 0 / 0 | PASS baseline |
| D5 | per-iteration | (1,1) | 2 | 1 / 2 | PASS |
| D6 | per-block | (1,1) | 2 | 0 / 2 | PASS |

- 12/12 individual run comparisons and 6/6 same-cell repeat comparisons recorded PASS, all with 74 gradient tensors, zero missing/all-zero/nonfinite gradient tensor sets.
- Maximum reported differences for compared logits, losses, gradients: **0**.
- CPU RNG `before_reset` fingerprints equal across all comparable runs; after-forward and after-backward fingerprints equal, including OFF/checkpoint comparison. This is restricted to the **tested fixed, nonstochastic-core, no-dropout native CPU path**.
- Source probe records actual backward replay events for enabled checkpoint modes, separately from two true forward logical iterations.
- Four synthetic negative scenarios call the same `evaluate()` function and return expected states: corrupted gradient -> FAIL, missing backward replay -> BLOCKED, corrupted RNG -> FAIL, missing parameter gradient name -> FAIL. Script `exit_code()` maps FAIL/BLOCKED/INCONCLUSIVE to 1/2/3 and PASS to 0 by code inspection; full CLI nonzero negative-process runs were not archived.
- Recorded local process `EXIT:0`, empty stderr and overall `PENDING CHATGPT REVIEW` before independent audit.

## 4. Independent integrity verification

These exact committed UTF-8 ASCII text artifact SHA-256 values were recomputed independently by ChatGPT from the GitHub file contents and match `RUN_META.json`:

- `F2D_B1R1_RESULTS.json`: `a7baa530cf3a54b3ccc6d1d94ca6d584025f3519a2e8c795720eb3be0d6f6938`.
- `stdout.txt`: `dfa8f269778206d9dd05c81e88791090615a524526e1d12683fb532af49d4850`.
- `stderr.txt` (0 bytes): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `exit_code.txt` (`EXIT:0\n`): `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`.

Original command and detailed runtime metadata are stored in `research/mini_mythos/gate2_2/evidence/f2d/b1r1/RUN_META.json`. Recorded Git HEAD is the pre-experiment review checkpoint `6ac48c95568e61fe50e58de04148c311ab00b7d3`; `b2ef7517...` is the evidence/code commit after capture. Both distinctions are intentional.

## 5. Scope limits / residual items

- **D1–D6 checkpoint equivalence, recorded CPU RNG invariance and replay trace under this exact 2/2/2 / seed/input / CPU path: PASS / CLOSED.**
- This does **not** prove all PyTorch activation checkpoint modes, stochastic module paths, arbitrary seeds, datasets, memory performance, or arbitrary architecture sizes.
- Full F2-D remains **OPEN**, because D7 unfixed recurrence-depth sampling is **NOT TESTED / NOT AUTHORIZED**. Native `randomized_iteration_sampler()` consumes a global CPU RNG value when evaluating `torch.rand((1,)).is_meta`, before independently seeded CPU generators. Its behavior must be designed and tested separately; `eval()` automatic sampling yields zero grad-enabled recurrence steps.
- `in-coda`, `reentrant`, SAC, native `train.py`, optimizer, CUDA, GPU MuonAdamW, Gate 2.2-C: **NOT TESTED**.
- Future improvement (not closure blocker): assert OFF runs have zero recompute events and explicitly check `row["flag"]` matches the expected enablement inside `evaluate()`; the current pinned observations show zero OFF replays and expected mode values but the generic evaluator does not separately enforce those two fields.
- Reviewer did not independently rerun full native Parcae on CPU; the experimental run is Grok's with an independently reviewed artifact chain.

## 6. Next precise task / checkpoint handoff

**F2-D D7 Stage A-R1: DESIGN ONLY, NO CODE OR EXPERIMENT.** Read this checkpoint, the F2-D A gate `10b9bd5...`, and the pinned original sampler implementation. Correctly separate global RNG consumed by `initialize_state`, the `torch.rand((1,)).is_meta` precheck, and the independent CPU-depth samplers. Choose controlled `train()` for a meaningful sampled depth (and separately describe `eval()` semantics), freeze `model.step`, sampling scheme, RNG snapshots, expected no-grad/grad depth evidence, and predeclare PASS/FAIL/BLOCKED/INCONCLUSIVE. Investigate stochastic checkpoint RNG preservation only with a different clearly scoped experiment, not by assuming D7 does it. Commit an isolated design-only document for independent ChatGPT review before enabling any CPU D7 code. Never edit Parcae/AxoNN, overwrite D1–D6 evidence, touch `gate2_1` dirty file, or rent GPU. Every stage must preserve Git, dependencies, results, open questions and next commands.
