# F2-E B1-R1 — ChatGPT 独立源码/证据审核与最小 R2 门禁

Date: 2026-10-25 (Asia/Tokyo)  
Reviewed Grok commit: `87637acaf3c11739dc968f7b882ee3ef47ffdc9e`  
Authoritative frozen prior gate: `research/mini_mythos/docs/F2E_B1_CHATGPT_REVIEW_AND_R1_GATE_20261025.md`  
Pinned upstream reviewed **read-only**: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`, `parcae_lm/models/parcae/parcae.py`.  
Review type: **remote GitHub commit/source and committed evidence independent audit; NOT an independent native CPU model re-run**. No model change, no upstream change, no GPU.

## 1. Independent decision

**F2-E B1-R1: PARTIAL POSITIVE EVIDENCE / NOT ACCEPTED FOR FULL FROZEN E1–E5 CLOSURE. R2 REQUIRED.**

- E1 sampler, E2/E3 sampled n/k and native iterate-forward return metrics: **source-consistent positive observations**, with missing recurrent Mask selection/phase acceptance.
- E4/E5 sequence and token: **positive deterministic logits/loss/74-gradient comparisons**, but lacking some frozen identity/RNG/replay verification; local `PASS` is **not** full protocol closure.
- E6: **INCONCLUSIVE accepted as honest exploratory outcome**; source-consistent inability to attribute direct Core update replays to actual live masked loop; **does not independently block E1–E5**.
- Cross-mode logits: **NOT APPLICABLE**.
- Parcae author intent for differing per-batch vs per-element n/k: **INTENT UNKNOWN**, no Parcae bug proven.
- Exit 3: expected for E6 INCONCLUSIVE under recorded harness; not evidence of E1–E5 failure, also not full experiment PASS.
- F2-B/C/D prior frozen PASS/CLOSED **unchanged**. Native training and GPU remain NOT TESTED / NOT AUTHORIZED.

## 2. Verified Git/change scope and artifact integrity

Commit changed only: `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py`; new `docs/F2E_B1R1_RESULT.md`; new `gate2_2/evidence/f2e/b1r1/` outputs (results, RUN_META, stdout/stderr/exit). Original `b1/` evidence not modified by this commit. No native Parcae/AxoNN file modified inside this OpenMythos commit. The old Codespaces local dirty `research/mini_mythos/gate2_1/TEST_RESULTS.json` status is Grok-reported only, **not independently inspectable**; preserve untouched.

All four new evidence SHA-256 verified by independent recomputation from GitHub contents (not merely copied from Grok):
- `F2E_B1R1_RESULTS.json`: `45568135ce5eca917b63ac12360c4f9d120119ce20f704b67e3d4ca99d4b7e39`
- `stdout.txt`: `fc1da9ae669d01a7e06a3fb6bd9704bf7799b51e59a694984aa5d46d7288649a`
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt`: `4f9485719ee49db6c2c06addf4c3f0c452cc5fe84ef9aac95efe65f4a3e0d6e8` (`EXIT:3\n`).

`RUN_META.json` cites `openmythos_head=0853051ec1791adbc54e4e8c90f2be146a0ff092`, older than the subsequent project-map/rebase/R1 commit. This is plausible due to execution before rebase, **but run-time exact probe source digest / dirty state is not proven**; next run must capture executed script SHA and pre-run Git/dirty status, and note pre/post-rebase ancestry. Git artifact hashes prove integrity, not mathematical completeness.

## 3. Positive measurements — evidence only, not blanket closure

From `F2E_B1R1_RESULTS.json`:
- E1 per-batch n=[1],k=[1],outer=2, native returned [1,1].
- E2 per-sequence n=[0,0],k=[1,2],outer=2, native returned [0,1], two Mask true counts [2,1], shape [2,1,1].
- E3 per-token shape [2,8], outer=7, native returned [0,1]; first five true counts [5,2,1,1,1], last two [16,11], shape [2,8,1], sum(n)=10, sum(k)=27.
- E4 sequence/token repeats: logits/loss/max-gradient deltas each 0.0, 74 recorded gradient tensors.
- E5 sequence/token checkpoint OFF/ON: same reported zero deltas and 74 gradient tensors, `replay=2` enabled.
- Three frozen gradient names/indices are archived for each E4/E5 pair; pairwise equality **is not** a new finite-difference derivative test.
- E6 `target_token_max_abs=0.0049576908349990845`, positive control `0.04084044694900513`, both on **direct Core update replays**, not masked-loop outputs; no causality detection claim.
- Negative tests: seven mutations rejected by current acceptance functions. Actual same-shape wrong-mask-content/RNG/replay/gradient-NaN/zero coverage remains missing.

## 4. Remaining acceptance defects grounded in source and probe lines

1. **Mask content not checked.** Probe `accept_sample()` lines 113–115 checks only Mask existence and shape; it does not compare exact bool masks to `(step<n)` / `(step<k)`, loop phase/index, accepted update values, or full Mask hashes against independent expected arrays. `run_once.where()` lines 222–225 selects `bool && ndim=3 && last_dim=1` globally, without callsite attribution. Same-shape wrong recurrent masks can pass.
2. **Phase labels objectively wrong.** `phase` is initialized to `no_grad` in line 188 and switched to `backward` only at line 240; thus all forward `torch.where` masks are labeled no_grad. Upstream native `iterate_forward()` clearly runs distinct no-grad and grad loops (upstream lines 336–356). E2's two masks both represent grad steps because n=[0,0]; E3's last two masks also represent grad steps. Reported `phase=no_grad` must not be treated as validated phase evidence.
3. **No actual write-selection comparison.** `where()` logs metadata then returns `orig_where(mask,a,b)`; harness doesn't verify logged recurrent callsite, `a=x_new`, `b=x`, or that inactive elements are retained and active elements are replaced at each native step.
4. **Pre/post model fingerprint not proven.** `run_once()` lines 272–273 calculates both start and after weight SHA *after* backward; `cell()` line 369 overwrites start_weights with original `wsha` without measuring at start. `evaluate_pair()` checks supplied identity fields but not actual before/after changes. Need actual pre-forward and post-backward model hashes, assert equal frozen weights and no optimizer modification.
5. **RNG path insufficiently frozen.** `evaluate_pair()` checks only `rng_before` (lines 128–129); `run_once()` captures `rng_after` forward but does not compare pair after-forward or after-backward state. No sampler-entry/exit RNG evidence per run or precise sampling counts beyond scalar/element and backward=0. Freeze matched identical forward and backward RNG states at declared boundaries.
6. **Grad/checkpoint evidence partly positive, not exhaustive.** `evaluate_pair()` lines 132–156 checks 74 names against pair, finite/nonzero gradients and tolerance; good. But it doesn't compare against a frozen expected 74-name set, confirm all parameter groups match, record expected per-phase checkpoint replay mapping or per-iteration events, or assert both real input/weight fingerprints from actual states. Actual `replay=2` is from `update_recurrent_state` wrapper during backward and should be preserved.
7. **Incomplete negative controls.** `synthetic()` lines 159–183 mutates n/k, outer, native mean, backward sampler, gross mask *shape*, weight label, gradient value. It does **not** test same-shape wrong Mask bits, incorrect phase count, mismatched RNG after-forward/backward, checkpoint replay omission, non-finite/zero gradient or missing/extra gradient names. One same-shape wrong-mask-content negative should FAIL the acceptance function, not just produce different hash in unvalidated JSON.
8. **Actual return capture improved.** `iterate()` lines 216–220 intercepts real native `iterate_forward` output; the old R1 gate's circular self-recomputation defect was substantially addressed. This may be retained.

## 5. Frozen minimal R2 correction (only sampling/Mask acceptance, no E6 extension)

**Purpose:** close remaining R1 instrumentation and formal E1–E5 gates, not redesign the algorithm.

- Keep exact Parcae upstream pin, model 2/2/2, weights and ids/seed from R1; same CPU float32 / torch environment / original tolerances.
- Modify only isolated `research/mini_mythos/tests/test_parcae_sampling_modes_cpu.py` and add **new** `gate2_2/evidence/f2e/b1r2/` plus result/checkpoint doc; original `b1/` and `b1r1/` evidence immutable.
- Tag genuine native recurrent `torch.where` callsites from pinned iterate_forward source and phase/no_grad-step/grad-step; compare exact bool mask **elementwise** with independently built `step<n`/`step<k`, and verify actual `torch.where` output matches native x_new/xk selection. Catch masks with same shape but wrong content.
- Pre/post actual model weight hashes, input token hashes, sampler counts and source steps, CPU RNG snapshots around sampler/forward/backward. Assert paired R1 existing E4/E5 rows share frozen identities and the relevant RNG boundaries. Preserve numeric logits/loss/all-74-grad deltas and real checkpoint backward replay measurement.
- Make negative controls reject same-shape incorrect Mask bits, incorrect phase/step, changed weight/RNG fingerprints, zero/NaN gradients, missing/excess gradients, missing replay. Ensure nonzero exit on known failure; archive per-cell reasons instead of status alone.
- **E6 remains INCONCLUSIVE with prior numbers**. No renewed causal experiment is required for E1–E5 closure. No GPU, native train lifecycle, new seeds/depths, test scope expansion, upstream changes, or architecture changes.
- Record before-run Git HEAD, dirty paths, script SHA256, exact deps/command, stdout/stderr/exit SHA. If worktree has existing unrelated dirty `gate2_1/TEST_RESULTS.json`, leave it untouched.
- Run only frozen E1–E5 CPU corrections; commit results as **PENDING CHATGPT REVIEW** then STOP. Review will separately decide bounded E1–E5 PASS/CLOSED; E6 INCONCLUSIVE is allowed independently.

## 6. Next unique authorized instruction

**F2-E-B1-R2 CPU probe acceptance correction only.** Do not proceed to native training or Gate 2.2-C yet. Use the stage status **F2-E B1-R1 PARTIAL / PENDING R2**, not CLOSED. Preserve historical F2-B/C/D statuses. Cross-audit after Grok returns a new commit.
