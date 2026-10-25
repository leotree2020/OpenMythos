# Mini-Mythos F2-D D7 B1 — Independent ChatGPT Review

Date: 2026-10-25 (Asia/Tokyo)  
Reviewer: ChatGPT, independent GitHub code/JSON/sha256 inspection, **not** a fresh native CPU execution  
Reviewed Grok commit: `b0670d0849163055d600de27a004aa6145d3b1c8`  
Frozen design gate: `6f9b00f5083f861bf87c1f8f11e867d7ea38abdd`  
Decision: **SOURCE-FORMULA AND REPORTED NUMERICAL RESULTS ACCEPTED AS PRELIMINARY; D7 B1 FINAL ACCEPTANCE PENDING R1 INSTRUMENTATION/ASSERTION CLOSURE. F2-D OVERALL OPEN.**

## Checkpoint and Git provenance

- Repo `leotree2020/OpenMythos` branch `mini-mythos-p1c-gate22c-readiness`.
- GitHub verified B1 commit `b0670d0849163055d600de27a004aa6145d3b1c8` is a direct child of frozen gate and has exactly **7 newly added files**, +659/-0 (isolated D7 script, docs and evidence). Branch HEAD verified at reviewed SHA.
- Upstream Parcae pinned at `69284c13746e849104f738d6d1a347b1f457df76`, Grok reported clean; AxoNN independent pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`. Neither modified in this commit.
- Runtime reported Python 3.11.2, PyTorch 2.14.1+cpu, 2 CPU threads, Parcae imported from `/tmp/parcae-src/parcae_lm/models/parcae/parcae.py`. Parameter count 247936, input SHA256 `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`, weight SHA256 `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`.
- Original D1–D6, F2-C, F2-B evidence remains unchanged in Git commit; preserve unrelated local dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` (reported by Grok; not independently inspected).

## Source-level facts and existing observations

Pinned `per-batch` default training sampler uses `T=max(Poisson(2),1)`, `n=T`, `k=min(T,2)`; the separate `_sample_batch_depths` path uses `n=T-k`. Do not change upstream or treat intent as proven.

- Recorded S1, S2, S3, S4: `model.step=0`, observed `n=k=1`, logical forward updates 2; isolated CPU-Generator source reference `T=1`, seed_n=514229.
- Recorded S5: `step=1`, seed_n=514230, `T=n=k=1`; a seed change does not require sample-value change.
- Recorded S6 Eval: `(n,k)=(2,0)`, logical steps 2; gradient comparison NOT APPLICABLE.
- Test-side `run_once` wraps original sampler once per call and records CPU RNG sampler entry and exit, logical update event records and replay hooks; shadow generator tests one global `torch.rand` draw. Synthetic negative records reject wrong n/k, after-forward RNG, missing sampler, backward sampler call, missing replay and corrupted gradient.
- Recorded S1/S2/S3 matched-pair comparisons and repeats returned PASS with `EXIT:0` and empty stderr, but the **archived results JSON contains status labels rather than per-cell raw gradient/RNG/replay and seed observations**. Therefore the independent auditor cannot rederive all equivalence assertions from this JSON.

## Independent SHA-256 integrity check

Independently recomputed SHA-256 over the exact GitHub-hosted archived files; all four match `RUN_META.json`:
- `F2D_D7_B1_RESULTS.json` `cfe032cbe6b7c40609d8c7e8269d05bfaad281e93fd369dbafb141aaa3d4b09e`
- `stdout.txt` `35faeb160e056417ce7ff51610b8c7a8f4a2bb554fbba3d985fc9088a1f47f37`
- `stderr.txt` empty `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt` (`EXIT:0\n`) `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## Must-fix gaps before D7 B1 can close

**R1-1 — enforce frozen execution semantics, not only total updates.** The verifier records `row["flags"]` for logical forward calls, but never validates that these are exactly `[False]*n + [True]*k` or that `logical==n+k` against the appropriate **independently derived reference** in every run. Instrument phase-segregated sampler calls, record the observed n/k and expected per-step grad flag sequence for **all** S1a/b, S2a/b, S3a/b, S4, S5, S6; enforce one sampler call in forward and zero in backward; verify return dtype/shape (source returns long tensors). Include negative using same production evaluator to corrupt an individual grad-mode flag.

**R1-2 — complete RNG/reference validation for every run.** Current formula + `shadow_ok` checks only S1a/S2a/S3a/S4; S5 only checks n/k against reference and S6 only checks the returned pair/steps. S1b/S2b/S3b/S5/S6 do not enforce `shadow_ok` or full RNG conservation. `evaluate()` only checks the row's `after_forward` against base and its own `after_backward` against `after_forward`; it does not compare pre-forward, sampler-entry, sampler-exit hashes across equivalent cells, or enforce the post-backward state against baseline. For every case, use a shadow Generator initialized from captured sampler-entry state and verify exactly one global draw, and do not modify live RNG. For S6, no backward state applies; check only applicable forward/sampler snapshots. Require repeated case RNG states to match as defined in frozen gate. Reject deliberately changed sampler-entry or sampler-exit snapshot via actual production checker.

**R1-3 — enforce provenance and unchanged weights.** `run_once()` computes `after_weights`, but `main()` never compares it with the pre-forward `wsha`. `cell()` calls `load_state_dict(weights)` but does not verify actual starting `state_dict` hash. Before and after every run assert the model's exact weight hash matches frozen D1–D6 baseline, and fail closed. Also require 247936 params rather than only recording count; record and check actual training flag, sampling scheme, `model.step`, input and pre-forward RNG equality when comparing S1/S2/S3. Do not modify optimizer/model weights.

**R1-4 — enforce strict gradient requirements and include independently auditable metrics.** `evaluate()` checks returned row gradient count 74 and row finite/nonzero vs baseline, but does not independently validate baseline gradient count, name set and finite/nonzero status, nor log per-comparison max logits/loss/full-grad deltas, actual selected F2-C scalar values, replay counts, or per-run RNG hashes in the result JSON. Use a shared evaluator for reference and observed rows. Require named 74/74 finite/nonzero training gradients; treat missing/extra names as FAIL; check exact gradient tensors elementwise at frozen tolerances (unchanged). Persist raw observable summaries for each run to make reproducibility independently auditable.

**R1-5 — negative and exit guards.** Keep production-evaluator negative cases; add corrupted grad-mode flag, sampler-entry/exit RNG hash, missing gradient name, incorrect model.step or input/weight identity, and validate *actual* `exit_code()` mapping for FAIL/BLOCKED/INCONCLUSIVE nonzero. Preserve observed statuses and reason fields; avoid reselecting seed/step after a failure.

## Scope of R1, status and next action

- **D7 B1 SOURCE/FORMULA evidence: PASS (limited observations).**
- **D7 B1 overall final acceptance: PENDING R1**. No observed numerical failure established.
- **F2-D D1–D6: PASS/CLOSED**, unaffected.
- **F2-D overall: OPEN**; CUDA, GPU, stochastic-dropout Checkpoint, per-sequence/per-token, native `train.py`, MuonAdamW, Gate 2.2-C: NOT TESTED.

Next Grok command: read this checkpoint, change only the D7 independent CPU test harness to implement R1-1 through R1-5, with frozen model/weights/input/seed/step/sampling/tolerances. Run only S1–S6, archive **new** evidence under `research/mini_mythos/gate2_2/evidence/f2d/d7/b1r1/`, retain original D7 B1, D1–D6, F2-C/B artifacts unchanged. Include source/env/Git HEAD/status, per-cell detailed evidence, stdout/stderr/real exit/SHA256, unresolved upstream difference and next task. Commit separately and stop with `PENDING CHATGPT REVIEW`; do not run GPU, upgrade deps, alter Parcae/AxoNN, or conclude final F2-D PASS.
