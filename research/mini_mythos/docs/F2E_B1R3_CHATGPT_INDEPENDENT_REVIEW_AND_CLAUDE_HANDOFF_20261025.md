# Mini-Mythos F2-E B1-R3 — ChatGPT 独立审核与 Claude Code 交接检查点

Date: 2026-10-25 (Asia/Tokyo)  
Reviewed commit: `e026ac421f4b9292260a687112c7fc1bdca0637c`  
Authoritative frozen gate: `research/mini_mythos/docs/F2E_B1R2_CHATGPT_REVIEW_AND_R3_GATE_20261025.md`  
Pinned Parcae read-only source reference: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76` (`parcae_lm/models/parcae/parcae.py`, recurrence selection lines 336–356).  
Audit method: independent GitHub commit/source/result/manifest audit with SHA-256 recalculation; **NO independent pinned native Parcae CPU rerun**, NO upstream modification, NO GPU.

## 1. Decision

**R3 is a material improvement and all recorded E1–E5 local cells PASS, but FULL FROZEN E1–E5 FORMAL CLOSURE IS NOT APPROVED YET.** Mark **F2-E E1–E5: POSITIVE / PARTIAL, HANDOFF FOR BOUNDED CLOSEOUT**; **E6: INCONCLUSIVE (acceptable independent exploratory status)**.

Distinguish:
- **Accept positive findings** of E1 sampling, E2 per-sequence and E3 per-token exact n/k, native returned mean, outer count, ordered per-iteration mask checks, and E4/E5 pairwise deterministic outputs/grads under reported fixed CPU config.
- **Do not convert positive results to blanket PASS/CLOSED** while predetermined R3 evidence/acceptance checks listed below are not satisfied.
- No Parcae defect proven. Author design intent for different per-batch/per-element n/k remains `INTENT UNKNOWN`; cross-mode logit equality `NOT APPLICABLE`.
- Existing frozen F2-B/C/D PASS/CLOSED unaffected; complete native training lifecycle and GPU still `NOT TESTED`.
- **No unsolicited R4/GPU/training experiment.** The next implementation owner will be Claude Code, but it must first read the current project SOP/map/checkpoint. One bounded closeout task can be authorized separately, and must not turn into a new sampling research program.

## 2. Commit scope and Git facts

Reviewed R3 commit changes exactly the dedicated `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`, adds `research/mini_mythos/docs/F2E_B1R3_RESULT.md`, and adds five files under `research/mini_mythos/gate2_2/evidence/f2e/b1r3/` (results, metadata, stdout, stderr, exit). Earlier `b1`, `b1r1`, `b1r2` artifacts not changed by that commit.

R3 run metadata records experiment-time Git HEAD `5a65b2410a86489f76075f39cefd60f23ec047b2`, the modified isolated probe, new untracked evidence, and **pre-existing unrelated dirty** `research/mini_mythos/gate2_1/TEST_RESULTS.json`. The actual bytes of that old local dirty file are not in Git evidence. **Preserve it**, do not reset/clean/overwrite.

The executed probe's SHA256 independently matches the committed R3 probe. No direct inspection of Grok's private local worktree possible; Parcae clean and CPU execution reported in experiment metadata only.

## 3. Five SHA-256 independent recomputations — all MATCH

- `F2E_B1R3_RESULTS.json`: `91d21c0440ad69d0edb53ddd44d424c9e3fef9cfef7a759d23623d93ce923fcd`
- `stdout.txt`: `cbb55f1a93b47f5b652f560158db68af145c4079ac9b7d43d72600dec8b75170`
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty)
- `exit_code.txt`: `4f9485719ee49db6c2c06addf4c3f0c452cc5fe84ef9aac95efe65f4a3e0d6e8` (`EXIT:3\n`)
- `test_parcae_sampling_modes_cpu.py`: `fa40c13c64e9875ea47aa230d7b6c14ad48df320244f619e6f14298b24926ffd`

Evidence file bytes match exact committed GitHub files; this proves artifact integrity, not that every required acceptance assertion exists.

## 4. Specific observed positive measurements

- E1 per-batch: n=[1], k=[1], outer=2, native return=[1,1].
- E2 per-sequence: n=[0,0], k=[1,2], outer=2; actual native return=[0,1]; 2 grad-phase masks with true counts 2 and 1; no no-grad masks since max(n)=0.
- E3 per-token: outer=7, max(n)=5, max(k)=2; native return=[0,1]; 5 no-grad Mask counts [5,2,1,1,1] and 2 grad Mask counts [16,11]; native write `x_new`/`xk` operands compared.
- E4 sequence/token same-mode reruns: recorded logits/loss/max-gradient differences all 0.0, 74 parameter gradient tensors and three frozen scalar indices.
- E5 sequence/token checkpoint OFF/ON: same reported zero deltas and 74 gradient tensors; observed checkpoint backward update count = 2 when enabled, 0 when disabled.
- Negative suite: dropped final mask, extra mask, `step=999`, corrupt phase, actual Boolean mask bit flip, mismatched synthetic callsite label, before-RNG, NaN, zero, missing/extra gradient and zero replay all rejected.
- E6 is **not rerun**; previous isolated direct Core replay numbers remain exploratory, no native masked-loop causal detection.
- `EXIT:3` is expected from E6 INCONCLUSIVE and is not evidence of a native E1–E5 FAIL.

## 5. Exactly what R3 fixed

R2 `accept_sample` had allowed dropping the last mask or changing its `step` while still returning PASS. R3:
1. Enforces `len(recurrent_masks) == max(n)+max(k)` (probe lines ~113–116).
2. Validates ordered phase and phase-local step index against frozen n/k (~117–131).
3. Compares the actual Boolean mask tensor elementwise against source-formula independent expectation and rejects flipped bit (~126–131).
4. Intercepts the `update_recurrent_state` call to capture previous/new states, and `torch.where` to verify the operands, under the pinned source's known conditional write (~271–307).
5. Separates backward recomputation counters from forward calls and adds negative controls.

These are accepted corrections, not a new model change.

## 6. Remaining frozen acceptance gaps — NOT evidence of a Parcae defect

**Gap A: per-mask evidence erased before archive.** `run_once.where()` holds raw `mask` and checks it elementwise (~295–304). But `finish()` removes `m["mask"]` (~499–501), and does **not** replace it with `mask_sha256`, packed bits, or a deterministic digest. The frozen R3 gate explicitly requires per-mask raw content **or full digest** in evidence. Archived booleans `content_ok: true` are useful but not a substitute for independent raw-bit integrity verification.

**Gap B: precise checkpoint replay is recorded but not enforced.** `evaluate_pair()` checks `row["replay"] < 1` (~170), not the **exact expected replay count 2** for this frozen configuration. A row with replay=1 and identical other fields would pass the replay criterion. The negative test checks missing replay=0, not replay=1. This is a defect in acceptance strictness, not a native replay mismatch in the observed R3 result (which reports 2).

**Gap C: RNG boundary coverage short of frozen standard.** `run_once()` archives `rng_before` and `rng_after` (immediately post-forward, ~315–323), but does not capture **post-backward RNG**, sampler entry/exit RNG or paired state after backward. `synthetic`'s bad-RNG case changes `rng_before`, not post-forward/post-backward. This fails the explicit R3 evidence/negative boundary, without implying observable CPU RNG divergence.

**Gap D: E4/E5 weight/gradient expected-set checks partial.** `run_once()` does record actual pre-forward and post-backward weight digests; E2/E3 asserts identity. `evaluate_pair()` compares between paired rows but does not independently assert each row's pre/post weight hash equality. It counts matching 74 gradient names, but never compares them to a frozen expected trainable-parameter name+shape set. These remain narrower than R3 frozen language; do not call unobserved configurations certified.

**Gap E: exit policy positive data only.** R3 `exit_code()` clearly maps injected FAIL to exit 1 in source, but no separately archived command-based FAIL exit demonstration is present. The normal `EXIT:3` is archived. If required by formal frozen gate, demonstrate on existing in-memory acceptance data, without a new model train.

**Do not open an unbounded R4 experimentation loop**. Capture these as a short, deterministic `R3 FINAL ACCEPTANCE DELTA` for an authorized Claude Code handoff. No new sampling modes, seeds, depths, dimensions, native model changes, GPU or E6 runs.

## 7. Recommended handoff / stop condition

At the next new Claude Code session:
1. Follow `docs/SESSION_START_PROTOCOL.md`, read `docs/PROJECT_MAP.md`, the historical recovery checkpoint and **this newest audit**; inspect actual branch/HEAD/dirty before any write. Do not assume today's SHA is still HEAD.
2. Report latest status: F2-B/C/D bounded PASS/CLOSED; F2-E E1–E5 positive, **formal closure pending the above explicit archived-evidence/acceptance assertions**; E6 INCONCLUSIVE; native full training NOT TESTED.
3. **First action is read-only takeover report**. Do not auto-run tests. If user separately authorizes bounded closeout, patch only this R3 isolated probe + new evidence directory and checkpoint, fix exact archived-mask digest, expected replay==2, relevant RNG boundaries/identity assertions, and negative assertions. Keep it one CPU evidence pass and STOP for independent review.
4. Once formal acceptance is achieved, immediately proceed to **design-only** native Parcae CPU training lifecycle gate (Forward → Loss → Backward → Optimizer → Scheduler → Checkpoint → Resume), with predeclared acceptance standards; no automatic training execution or GPU.
5. Preserve all B1/R1/R2/R3 evidence unchanged, upstream Parcae/AxoNN unchanged, all historical checkpoints. Do not override user-level project architecture/innovation strategy.

## 8. Exit/checkpoint state

- `F2-E B1-R3 independent review`: **PARTIAL POSITIVE, NOT CLOSED**.
- `E1–E3 source-consistent sampler/mask behavior`: **POSITIVE OBSERVED** within frozen micro-scope.
- `E4/E5 deterministic equality and gradient tensors`: **POSITIVE OBSERVED**, formal full gate pending.
- `E6`: **INCONCLUSIVE**, intentionally not rerun.
- `Parcae author intent`: **UNKNOWN**.
- `Native complete training`: **NOT TESTED**.
- `Next instruction`: Claude Code read-only handoff, then explicit authorization for narrow documented closeout if required.
