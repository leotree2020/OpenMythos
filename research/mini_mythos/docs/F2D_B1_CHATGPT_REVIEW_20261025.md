# Mini-Mythos F2-D B1 — ChatGPT Independent Audit (D1–D6)

Date: 2026-10-25 Asia/Tokyo  
Reviewer: ChatGPT (independent GitHub source, result, and SHA-256 audit; no independent Parcae CPU rerun)  
Decision: **NUMERICAL EVIDENCE ACCEPTED WITHIN SIX PINNED CELLS; FORMAL B1 CLOSURE PENDING MINIMAL R1 TEST-HARNESS HARDENING.**  
D7: NOT RUN / NOT AUTHORIZED.

## 1. Git and environment checkpoint

- Research repo: `leotree2020/OpenMythos`; branch: `mini-mythos-p1c-gate22c-readiness`.
- Last approved F2-D A D1–D6 gate: `10b9bd5ada1da5c1c20054dfdb6c6fe4a861950d`.
- B1 experiment commit independently reviewed: `80a99e8aa0afb470f745981f0218fb833bbe7c1c`; direct child of frozen gate; branch HEAD verified at this commit before this review.
- B1 commit only adds seven research script/doc/evidence files (+815/-0). Does not modify upstream native Parcae, prior accepted F2-B/F2-C evidence or the D7 design.
- Pinned native Parcae: `69284c13746e849104f738d6d1a347b1f457df76`. Grok's evidence reports clean Parcae worktree.
- Recorded runtime: Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, threads 2, micro model 247936 params; separate source `/tmp/parcae-src`.
- Input SHA256 (D1–D6): `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`, not equal to F2-C input by design.
- Grok reports unrelated local uncommitted `research/mini_mythos/gate2_1/TEST_RESULTS.json`. Leave untouched; not independently inspected by ChatGPT.

## 2. Observed experimental results

| Cell | Flag / implementation | Fixed pair | Forward logical steps | Recorded backward update replay | Recorded backward block replay | Numerical evidence |
|---|---|---|---:|---:|---:|---|
| D1 | off | (0,2) | 2 | 0 | 0 | Baseline |
| D2 | on / per-iteration | (0,2) | 2 | 2 | 4 | PASS vs D1 |
| D3 | on / per-block | (0,2) | 2 | 0 | 4 | PASS vs D1 |
| D4 | off | (1,1) | 2 | 0 | 0 | Baseline |
| D5 | on / per-iteration | (1,1) | 2 | 1 | 2 | PASS vs D4 |
| D6 | on / per-block | (1,1) | 2 | 0 | 2 | PASS vs D4 |

- Recorded comparable mode-to-baseline maximum logit, loss, and gradient differences: all 0.
- Recorded CPU RNG hashes at pre-forward post-reset, post-forward and post-backward are equal between corresponding off/checkpoint comparisons, with post-backward equal to post-forward; this matches the pinned no-dropout path.
- Six logical forward trajectories have expected grad-mode flags `[True,True]` or `[False,True]`; backward replay is instrumented separately by switching phase before `loss.backward()`.
- Each cell was executed twice. However, the probe's `same` acceptance condition only compares **loss and logits** of `a` and `b`, not gradients/RNG or replay event presence of the second run.
- B1 script emits overall `PENDING CHATGPT REVIEW`; the provided `EXIT:0` and empty stderr are recorded facts from Grok, not substitutes for full acceptance.

### Independent file integrity audit

All four GitHub-hosted artifacts match the SHA256 values in `RUN_META.json` when independently rehashed:

- `F2D_B1_RESULTS.json`: `fac4658718a388f31c8b385b9f5ac9ecc23033dbce27f2ff3bcc764e80ca4912`.
- `stdout.txt`: `bfbddab303b63117dbd653b73d30b3349a28b9e2e4b2715dc8bed238b11ded94`.
- `stderr.txt` empty: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- `exit_code.txt` = `EXIT:0\n`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`.

## 3. Minimal test-harness gaps before final B1 PASS

**R1-P0: False weight checksum.** Current line `weight_sha = sha_bytes(torch.save(weights, f"{out}.weights") or b"")` computes SHA-256 of an empty byte string because `torch.save` returns `None`. It does not fingerprint `weights`, and it is not recorded or checked. Replace with a deterministic, hashable serialization of sorted `state_dict` names, tensor shapes/dtypes and actual tensor bytes; log the digest, assert baseline and each cell's weight state agree before forward and are unchanged after backward. Do not write transient weight files into existing evidence or alter model math.

**R1-P0: Incomplete duplicate-run validation.** The implementation tests `a.loss == b.loss` and SHA of logits only, then discards `b`. The previously frozen gate also requires duplicate gradient-name coverage, finite/nonzero values, elementwise gradient closeness, CPU RNG snapshots, logical-step flags and replay evidence for *each* run. Record both and fail if a mismatch occurs; report full-grad max delta and RNG status.

**R1-P1: Hard guards / baselines.** D1 and D4 are recorded PASS merely because `flag=False`, without independent checking gradient count, nonzero/finiteness and RNG forward/backward invariance. The enabled-mode `names_ok` is computed, but the subsequent comparison indexes `row["grads"][n]` even when names are missing, risking an uncaught `KeyError` instead of a structured FAIL. Factor a strict shared evaluator; fail closed; enforce empty missing/zero/nonfinite for both baseline and checkpoint outputs.

**R1-P1: Negative controls must exercise actual acceptance.** `synthetic()` has a genuine numeric mismatch test but its missing-replay and RNG-mismatch tests are constant string conditions, not calls to the actual evaluator. Implement synthetic input mutations against the same validation function: altered gradient, deleted backward replay event, corrupted CPU RNG fingerprint. Each must yield non-PASS and nonzero exit; verify FAIL > BLOCKED > INCONCLUSIVE.

**R1-P1: Weight/state event provenance.** Record actual model import path, parameter count, selected Core parameter frozen names/indices, and observed actual gradient-name count in emitted result JSON. Existing import and parameter-count checks work but are not independently visible in the archived item details. Preserve the environment and Git status (including pre-existing unrelated file) without mixing them into commits.

## 4. Decision, limitations and exact next action

- D1–D6 **recorded checkpoint-vs-off CPU numerical, replay and RNG evidence: PASS under the observed single deterministic comparison**, based on Grok outputs and independently matched hashes.
- **FORMAL B1 ACCEPTANCE: PENDING R1** because repeat/guard/fingerprint acceptance does not fully implement the frozen gates. These are probe-quality defects, not evidence of a Parcae model defect.
- D7 automatic sampler: NOT TESTED and NOT AUTHORIZED pending design correction. In native `randomized_iteration_sampler`, `torch.rand((1,)).is_meta` consumes global CPU RNG before independent sampling generators; `eval()` returns zero grad-enabled steps.
- Reentrant/SAC/in-coda, CUDA, native full training/optimizer and Gate 2.2-C: NOT TESTED.
- ChatGPT did not independently execute the native Parcae model on CPU in this review.
- Next Grok task: **F2-D-B1-R1 minimal probe acceptance corrections only**. Read this checkpoint; repair genuine weight hashing, strict duplicate and baseline gradient/RNG comparisons, structured missing-name failure and evaluator-driven synthetic negatives. Rerun D1–D6 in pinned CPU setup without changing numerical tolerances, mode matrix, input, seed or weights; archive separately under `research/mini_mythos/gate2_2/evidence/f2d/b1r1/` and commit new evidence. Preserve original B1 files, F2-B/F2-C and upstream. Do NOT run D7 or GPU. Stop at `PENDING CHATGPT REVIEW` for a closing audit.

