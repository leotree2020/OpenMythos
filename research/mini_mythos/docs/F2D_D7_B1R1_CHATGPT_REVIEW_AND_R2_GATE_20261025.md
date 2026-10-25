# Mini-Mythos F2-D D7 B1-R1 Independent Review and Minimal R2 Gate

Date: 2026-10-25, Asia/Tokyo  
Reviewer: ChatGPT  
Reviewed Grok commit: `57964fe915f22209047f422b56fe085d5783c640`  
Frozen original D7 gate: `6f9b00f5083f861bf87c1f8f11e867d7ea38abdd`  
Prior D7-B1 audit: `87e59df6a53beda9fbbdc29185692adeb40b9945`  
Decision: **Reported sample/Checkpoint numerical evidence PASS within S1–S4 observations; D7 B1 FINAL ACCEPTANCE PENDING MINIMAL R2; F2-D OVERALL OPEN.** No upstream defect established.

## Git, environment and evidence provenance

- Repository `leotree2020/OpenMythos`, branch `mini-mythos-p1c-gate22c-readiness`; reviewed commit is a direct child of the prior review and verified branch HEAD at audit time.
- Change-set: 7 files (+1237/-10): only D7 CPU harness modified, new `b1r1` evidence and result document added. Original D7 B1, prior D1–D6, F2-B, F2-C evidence unchanged in this commit.
- Pinned original Parcae `69284c13746e849104f738d6d1a347b1f457df76` with reported clean worktree, AxoNN separate pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`.
- Recorded CPU runtime Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, 2 threads; 2/2/2 micro-model 247936 params, input SHA `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`, weight SHA `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`.
- Pre-existing unrelated local modification `research/mini_mythos/gate2_1/TEST_RESULTS.json` is reported by Grok as the only dirty file. ChatGPT did not inspect the Grok worktree.
- This review independently inspected GitHub source/JSON and rehashed all four evidence files; **ChatGPT did not rerun native Parcae on another CPU machine**.

## Positive results supported by code and artifacts

- S1, S2, S3, S4 at step=0: sampled n=1, k=1, two forward logical updates; independent Poisson reference T=1 with seed_n=514229. S5 at step=1: n=k=1 with seed_n=514230, a valid outcome; S6 eval: (n,k)=(2,0), forward logical steps 2.
- S1/S2/S3 each executed twice, with S4 separate repeat. Comparisons record flags `[False, True]`, sampler count forward=1 and backward=0, replay per-iteration=1 / per-block=2, and zero max logits and gradient deltas across comparisons. CPU RNG matching snapshots are archived for the 9 run comparisons.
- All train cell starting+post-backward weight hashes are hard-checked; S6 currently checks starting hash only.
- Synthetic negative tests call the shared `evaluate()` for n/k, flags, forward/backward sampler counts, RNG entry, missing replay, bad gradient and missing gradient name. The `bad_weight` negative does NOT use `evaluate()`.
- Under pinned `per-batch` `poisson-truncated-full`, native sampler's n=T vs separate `_sample_batch_depths()` n=T-k difference remains an **open upstream implementation discrepancy**, not a proven bug.

### Independent SHA256 verification

The exact committed file hashes recalculated from GitHub content matched `RUN_META.json`:
- `F2D_D7_B1R1_RESULTS.json`: `bcddc14d1086d2ac74e7724713a53aa6d4c2c7d5353acef40a4a4bc12c4cef60`
- `stdout.txt`: `d4991ed4ea7b08ef1baa82fac91a09d6370d748b2152dded04bcac804c0aaea5`
- `stderr.txt` empty: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt` containing `EXIT:0\n`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Remaining FROZEN-GATE gaps (do not expand experiment design)

**R2-1: Every-run acceptance including S5/S6.** R1 `main()` only evaluates source math and `shadow_ok` for **first** S1a/S2a/S3a/S4; S1b/S2b/S3b share comparison logic that never checks `shadow_ok`, while S5 checks only n/k and S6 checks only n/k/logical steps. Add a dedicated sampler/CPU-RNG evaluator, called for **every** S1a/b, S2a/b, S3a/b, S4, S5, S6, verifying exactly one forward call and no backward sampler calls; T/n/k against *isolated local Generator* (or eval pair), n+k, grad-mode sequence, both n and k dtype/shape, `shadow_ok is True`, and applicable CPU RNG chain `sampler_exit==after_forward` and (where backward ran) `after_backward==after_forward`. S5/S6 must have their actual RNG hashes, step and evaluator outcomes **archived**. Do not subject S6 to train gradient requirements.

**R2-2: Equal-condition pairing and immutable sources.** Before any training checkpoint comparison verify the actually observed `train=True`, `step=0`, default sampling scheme, exact pinned weights/input and **all** comparable pre-forward/sampler entry/exit RNG hashes. The code currently records model training/step/scheme in volatile `row` but `evaluate()` ignores them and `record()` omits them from archived output; compare them in evaluator and archive actual values. Do not infer equality merely from caller constants. For S5 expect step=1, train=True. For S6 expect train=False, step=0.

**R2-3: Weight guard completeness and genuine synthetic negatives.** Hard-assert S6 `after_weights==initial_sha` too, even without backward. The synthetic `bad_weight` currently uses a standalone hardcoded comparison expression, not the same production evaluator; make production metadata/weight validator reject corrupted start/end hashes, step, scheme and input fingerprints through actual evaluator calls. Preserve fail-closed exit semantics FAIL/BLOCKED/INCONCLUSIVE nonzero. Do not change sample seeds, modes, numerical thresholds, model config or Parcae code. Store actual result details for the synthetic cases.

**R2-4: Baseline gradient validation and evidence.** Shared `evaluate()` checks row gradient count and finite/nonzero but does not verify reference/base gradient count, absence of extra name(s) and all reference tensor finiteness. Add symmetric nonfinite/nonzero/name guards for both training sides and write an auditable per-comparison gradient count, logit/loss/full gradient maxima, selected three F2-C core scalar values plus replay and RNG fingerprints. S1/S4 baselines must undergo the same checks. Keep tolerances as pre-frozen: logits 1e-6; loss 1e-6+1e-6*max(abs); gradients 1e-6+1e-5*max(abs); expected 74 parameters.

## Decision and next exact action

- **D7 source-level default scalar formula (sampled CPU conditions): PASS in reported local evidence.**
- **S1–S4 measured checkpoint/reproducibility equivalence: positive evidence, within frozen configuration.**
- **D7 B1 full formal acceptance: PENDING R2** because conditions for S5/S6 and every-run RNG/weight/metadata comparison are not enforced. These are test-harness gaps, **not** evidenced Parcae defects.
- **F2-D overall: OPEN**. D1–D6 remain PASS/CLOSED; F2-B/C remain PASS/CLOSED.
- Per-sequence, per-token, stochastic checkpoint, reentrant, in-coda, SAC, GPU, MuonAdamW and Gate 2.2-C: NOT TESTED.

**Next Grok instruction**: read this audit document. Modify **only** `research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py` with the smallest shared sampler validator and comparable-condition guards specified above; do not run new modes. Rerun only S1–S6 CPU under identical seed/config/input/weights and frozen tolerances. Archive NEW R2 results, raw stdout/stderr/exit, metadata SHA256 and Git status under `research/mini_mythos/gate2_2/evidence/f2d/d7/b1r2/`; preserve previous artifacts and unrelated dirty file. Commit isolated R2 and stop with `PENDING CHATGPT REVIEW`. Do not change Parcae/AxoNN, discover new seeds, use GPU or announce final F2-D PASS.
