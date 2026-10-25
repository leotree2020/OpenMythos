# F2-E B1-R2 — ChatGPT 独立审核 / 最小 R3 验收门禁

Date: 2026-10-25 (Asia/Tokyo)  
Reviewed commit: `afd37bc26dbd7395bba12f879bd5abdac87f88ee`  
Prior frozen gate: `research/mini_mythos/docs/F2E_B1R1_CHATGPT_REVIEW_AND_R2_GATE_20261025.md`  
Pinned upstream inspected READ-ONLY: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`, `parcae_lm/models/parcae/parcae.py` (actual masks at upstream iterate_forward lines 339–356).  
Review method: independent GitHub source + evidence + SHA-256 audit; standalone local acceptance-logic negative control using torch 2.10 CPU; **NOT an independent pinned native Parcae CPU execution**.

## 1. Independent decision

**F2-E B1-R2: STRONG POSITIVE E1–E5 EVIDENCE, NOT YET FORMALLY CLOSED; PENDING MINIMAL R3.**

- E1 source-consistent sampler route, n/k, native return metrics and outer count: positive observed evidence.
- E2 per-sequence and E3 per-token: sampled n/k, actual returned means, 2 and 7 corresponding logged masks with expected true counts and correct declared phase ordering: positive observed evidence; *harness completeness and authentic callsite binding remain open*.
- E4 both sequence/token repeat and E5 both checkpoint OFF/ON: logs report all 74 gradients, zero logits/loss/gradient deltas, 2 backward recompute events on ON, with improved actual pre/post weight hashes and pre/after-forward RNG comparison. Positive within recorded micro-scope; *full identity/replay negative gate not yet complete*.
- E6: **INCONCLUSIVE (unchanged)**. R2 carries R1 direct-core-replay measurements without a new E6 causal test. Accepted as honest exploratory label. Does **not** prevent bounded E1–E5 closure after minimal harness correction.
- F2-B/C/D remain previously PASS/CLOSED in frozen scopes. Native complete train and GPU: NOT TESTED / NOT AUTHORIZED. Parcae author intent remains INTENT UNKNOWN. No native bug inferred.
- Exit 3 is consistent with sole E6 INCONCLUSIVE under `exit_code()`, neither evidence of a native FAIL nor grounds for a global PASS.

## 2. Commit integrity and independently recomputed SHA-256

Commit modifies only the existing dedicated F2-E test script and adds one R2 report + new `gate2_2/evidence/f2e/b1r2/` evidence (seven paths total). B1/B1-R1 paths unchanged by the R2 commit; Parcae/AxoNN upstream sources not part of the change.

Independently recalculated from the exact committed GitHub file bytes:
- `F2E_B1R2_RESULTS.json`: `18da1b603ee9ee9a2aaa2f55c3918faf5b57f7657ac5bcbf2a7c4941829d0e65` — MATCH.
- `stdout.txt`: `aeeb6e038ecfd053a29658b6054d82a8e3cf21684b024f6cce9c0e669f39449b` — MATCH.
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — MATCH (empty).
- `exit_code.txt`: `4f9485719ee49db6c2c06addf4c3f0c452cc5fe84ef9aac95efe65f4a3e0d6e8` — MATCH (`EXIT:3\n`).
- Exact committed `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`: `b7cdb5bb6e63c9a8a49f63109bae0cf2398a48e71219b0a6dcbb8dbb5e8624e5` — MATCH.
- `RUN_META.json` reports actual runtime Git HEAD `13be77205b69a483b5ed6dbb722da4885ea0ca17` and dirty: existing `gate2_1/TEST_RESULTS.json`, modified R2 probe, untracked b1r2 new evidence. This accounts for run-before-commit; exact probe SHA independently matches committed bytes. The *local* dirty file contents/worktree cannot be remotely verified, preserve unchanged.

## 3. Measurements that do match upstream and frozen expectation

- E1 per-batch: n=[1], k=[1], outer=2, returned [1,1].
- E2 per-sequence: n=[0,0], k=[1,2], outer=2, native returned [0,1], masks `grad step0 count=2`, `grad step1 count=1`, shape [2,1,1]. Upstream no-grad max=0.
- E3 per-token: outer=7; n.max=5, k.max=2; native returned [0,1]; five no-grad true counts [5,2,1,1,1] then grad [16,11]; shape [2,8,1]. Total accepted n=10, k=27.
- E4 sequence/token: recorded max delta logits=0.0, loss=0.0, grad=0.0, 74 tensors, frozen three scalar indices logged.
- E5 sequence/token checkpoint OFF/ON: same deltas; logged two backward update replay events ON.
- Synthetic now reports 10 incorrect data/flag mutations as rejected (FAIL or BLOCKED), an improvement over R1.
- E6 prior target-token core update delta=0.0049576908349990845, control=0.04084044694900513, **not masked-loop causal evidence**.

## 4. Remaining exact acceptance defects

### A. Missing Mask record still passes (confirmed minimal standalone CPU check)

In R2 probe `accept_sample()` lines 113–121, it validates `not row["recurrent_masks"]`, per-row shape/boolean flags, phase labels and relative phase order, **but not exact length** or `step` identity. E3 has expected 7 masks; supplying the same E3 records with the final mask removed **still returns PASS** if the unrelated `outer` counter stays 7. In a local isolated test faithfully mirroring those acceptance conditions, `correct=PASS`, `missing final mask=PASS`, `wrong step label=999 => PASS`. This is a defect in the acceptance program, NOT evidence that the real native R2 run skipped a mask.

### B. Phase/callsite attribution partly self-derived

`run_once.where()` lines 239–257 selects *all* bool rank-3 last-dimension-1 `torch.where` calls, and labels `phase` and `step` solely based on accumulated matching call index, not an authenticated native `iterate_forward` source callsite or actual loop step. Therefore the reported stage sequence can become tautological if a call is missing/extra or a same-shaped unrelated call is captured. The source's two native write locations are known from the pinned version; capture must tie to them (or an equivalent verified source-level event).

### C. Selection validation not independently tied to recurrent x_new/xk

`select_ok = all(where(mask,out==a,out==b))` merely checks that PyTorch `torch.where` returned the values passed to it; it does not prove `a` is the actual recurrent `x_new` from this iteration and `b` is its prior state `xk`. Verify arguments correspond to the instrumented update call, and compare against independent expected active mask on every native iteration. Protect against a wrong same-shape mask.

### D. Partial negative and RNG/replay coverage

`synthetic()` lines 167–200 tests modifying `content_ok` *label*, not flipping an actual Mask tensor bit. It changes a phase label, not a phase-step event; checks `rng_before` but not after-forward/backward; changes gradient value but not NaN/Inf/zero/missing/extra gradient. `run_once()` captures RNG before and after forward, not after backward or sampler entry/exit. `evaluate_pair()` checks pairwise 74 gradient names, but does not tie exact expected names/shape to model's `requires_grad` list; replay merely `>=1` with no frozen per-iteration expectation. R3 should close only the observable frozen requirements, not create general/future training tests.

### E. Metadata stage label stale

R2 script `finish()` lines 441–449 still writes `"stage": "F2-E B1-R1"` into R2 results. Correct to R3 for the next run and preserve immutable old R2 results as-is. This is reporting/provenance mismatch, not a mathematical fail.

## 5. R3 — ONE LAST NARROW HARNESS CORRECTION (frozen, no model changes)

**Purpose**: make frozen E1–E5 acceptance **sound against plausible incorrect-mask/phase/missing-event data**, without another architecture or exploratory loop.

Required acceptance (use the same original model/config/weights/inputs/seed/tolerances):

1. For E2/E3, enforce **exact** recurrent mask count `n.max()+k.max()`, exact ordered `phase` and zero-based `step` for every iteration; correlate with actual native `iterate_forward` write callsite or another genuinely source-authenticated loop event, not inferred solely from idx. Compare exact Boolean mask bits against independent `step<n`/`step<k` arrays.
2. Capture the real update call's `xk` and `x_new`; verify the native write uses these as the respective old/new arguments, and output equals independently selected values. Retain per-mask shape, true count, full mask digest or raw bits, phase, step, and deviations. No source modifications to Parcae.
3. Preserve actual start/finish model hashes; paired RNG identities. Add/compare RNG after backward and (if observable noninvasively) before/after sampler to satisfy frozen RNG requirements; enforce expected forward/backward sampler counts and precise checkpoint replay count for same bounded configuration.
4. Negative controls must **actually mutate raw** Mask bits (same shape), remove one Mask record, corrupt `step` while preserving phase, alter expected source callsite, corrupt at least after-forward RNG, corrupt NaN/zero/missing/extra gradient tensors, and remove replay; each must produce FAIL or BLOCKED. No need for broader random fuzzing. Demonstrate exit policy for a known injected FAIL in isolation.
5. Fix new result stage metadata to `F2-E B1-R3`; archive script SHA, pre-run Git HEAD/dirty, exact stdout/stderr/exit and sha256.
6. **Do not rerun E6;** record `E6 INCONCLUSIVE` and refer to prior provenance. E6 does not block independent E1–E5 gate.
7. Change **only** isolated `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`, new `gate2_2/evidence/f2e/b1r3/`, and new result/checkpoint doc. Preserve B1/R1/R2 evidence and old dirty `gate2_1/TEST_RESULTS.json`. CPU-only, upstream untouched, no GPU, no native train run, no new model configs/seeds/sampling modes.

**Stop condition:** after a single frozen R3 CPU run, commit and report as `PENDING CHATGPT REVIEW`; ChatGPT audits. If the defined E1–E5 tests all pass and independent review finds no material mismatch, close **bounded E1–E5 only** and immediately advance to planning the native CPU Training Lifecycle; do not open new elective F2-E microtests. Any material discrepancy is recorded and scoped separately, not masked as PASS.

## 6. Next one authorized task

`F2-E-B1-R3` *harness completeness correction only*. No change to E6, original Parcae/AxoNN, architecture or training. Maintain **F2-E E1–E5 PENDING R3**, **E6 INCONCLUSIVE**.
