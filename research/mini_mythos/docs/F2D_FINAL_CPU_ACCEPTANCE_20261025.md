# Mini-Mythos F2-D — Final CPU Scope Acceptance / Handoff Checkpoint

Date: 2026-10-25 (Asia/Tokyo)  
Independent auditor: ChatGPT  
**Decision: PASS / CLOSED FOR THE EXPLICITLY FROZEN NATIVE PARCAE CPU F2-D SCOPE (D1–D6 FIXED DEPTH AND D7 S1–S6 PER-BATCH AUTO-DEPTH).**  
This does **not** certify all checkpoint implementations, sampler algorithms, training, GPUs, or every model configuration.

## 1. Source, Git and dependencies

- Research repository: `leotree2020/OpenMythos`; branch `mini-mythos-p1c-gate22c-readiness`.
- Reviewed Grok R2 experiment commit: `12e6446d5cd970e37a85dfe06cd289e7642fb2d2`, verified branch HEAD at audit time.
- Frozen D7 stage A gate: `6f9b00f5083f861bf87c1f8f11e867d7ea38abdd`.
- Prior D7 B1/R1 audits: `87e59df6a53beda9fbbdc29185692adeb40b9945`, `58b50662e9b5adb7a472c0ef3b77007e00b20e5c`.
- D1–D6 formally accepted at `1ed99746c48878840794688c219f4c741bfd154e`; F2-C closed at `ca2389384ad6dabed0c1edf26161c9377f88cd68`; F2-B previously closed.
- Native Parcae pinned upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`; recorded upstream `git status --porcelain` clean. Independent AxoNN pin `c5ef65d3d4f329c20292a2d26681e8d9cbcccecf`. No upstream changes.
- R2 commit is direct child of frozen R2 review and edits only `research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py` (+79/-41) plus six new isolated `b1r2` evidence/doc files; original B1/R1, D1–D6, F2-B/C evidence unchanged.
- Grok reports a pre-existing unrelated uncommitted `research/mini_mythos/gate2_1/TEST_RESULTS.json` change; do not stage, clean, delete or overwrite it. Reviewer has not directly read Grok's local worktree state.
- Recorded CPU environment: Python 3.11.2, PyTorch 2.14.1+cpu, x86_64, 2 CPU threads, Parcae import root `/tmp/parcae-src`. CPU float32 SDPA, no GPU / dependency upgrades.

## 2. Scope, input and predeclared acceptance

**Objective:** verify pinned upstream recurrence-depth sampler, global CPU RNG accounting, repeatability and checkpoint-off/per-iteration/per-block output and gradient equivalence for a 2 Prelude / 2 recurrent Core / 2 Coda, 247,936-parameter native Parcae micro-model.

- Locked input: batch 1, sequence 8, same as accepted D1–D6, SHA-256 `7a248d71c9e805e2e0fbfefc0d76ae4a0720ea1eb40b4c2ccc9bb85cc717fe4b`.
- Locked initial model weights: SHA-256 from sorted tensor names, shapes, dtypes and actual state bytes `366a8bf9202622cf77b3a15075ca183d789dcf5257636395f789972ab31b713c`.
- Seed 42 for micro-model initialization/forward; seed 1000 for initial synthetic token input; `state_init=like-init`, `sampling_scheme=poisson-truncated-full`, `recurrent_iteration_method=per-batch`.
- Frozen D7 S1 train OFF step 0, S2 train per-iteration step 0, S3 train per-block step 0, S4 train OFF repeat step 0, S5 train OFF step 1, S6 eval OFF step 0 forward only. All invoke `num_steps_pair=None`. S1–S3 each repeated twice, 9 actual runs total.
- Source reference under `per-batch` training: `T=max(Poisson(t+s=2; independent CPU Generator seeded from 514229+model.step),1)`, `n=T`, `k=min(T,2)`, executed forward steps `n+k`. This deliberately differs from the separate `_sample_batch_depths` path's `n=T-k`.
- Precise validation: one sampler invocation in forward, none in backward; accurate no-grad/grad logical flags; native train sampling returns long [1], eval returns long scalar [ ]; shadow-generator proof of one global CPU `torch.rand((1,))` at sampler entry; proper CPU RNG before/sampler-entry/sampler-exit/after-forward/after-backward snapshots; unchanged model weights; exactly 74 finite, nonzero train parameter gradient tensors; checkpoint-on backward recomputation evidence when k>0.
- Original frozen numeric tolerance: logits max abs <= `1e-6`, loss absolute delta <= `1e-6+1e-6*max(abs(L1),abs(L2))`, each gradient element absolute delta <= `1e-6+1e-5*max(abs(g1),abs(g2))`.
- FAIL outranks BLOCKED outranks INCONCLUSIVE outranks PASS, and non-PASS yields nonzero exit. Exit 0 is not by itself sufficient.

## 3. Recorded experiment results and independent checks

Grok recorded one local CPU execution of the pinned script in the R2 commit:

`PYTHONPATH=/tmp/py311-pkgs /usr/bin/python3.11 research/mini_mythos/tests/test_parcae_sampler_rng_cpu.py --parcae-root /tmp/parcae-src --output research/mini_mythos/gate2_2/evidence/f2d/d7/b1r2/F2D_D7_B1R2_RESULTS.json`

Result state: **29 PASS, 1 NOT APPLICABLE** (S6 train-gradient comparison); no FAIL/BLOCKED/INCONCLUSIVE. `EXIT:0`, stderr empty.

| Cell | Config | Sampled n,k | Core logical steps / grad flags | Backward replay | Evidence status |
|---|---|---|---|---|---|
| S1a/b | train, OFF, step=0 | (1,1) | 2 / [False,True] | 0 | PASS |
| S2a/b | train, per-iteration, step=0 | (1,1) | 2 / [False,True] | 1 | PASS |
| S3a/b | train, per-block, step=0 | (1,1) | 2 / [False,True] | 2 | PASS |
| S4 | train, OFF repeat, step=0 | (1,1) | 2 / [False,True] | 0 | PASS |
| S5 | train, OFF, step=1 | (1,1) | 2 / [False,True] | 0 | PASS |
| S6 | eval, OFF, step=0 | (2,0) | 2 / [False,False] | N/A | PASS, gradients N/A |

- S1–S4 train step=0 reference Poisson seed_n=514229, sampled `T=1`; S5 seed_n=514230, sampled `T=1`, valid repeated sample despite different generator seed.
- The single production `accept_sampler()` function is invoked for all nine individual runs and checks n/k, logical steps, per-step grad flags, native shape/path, observed train/step/scheme/input/weight fields, one sampler forward call/none backward, `shadow_ok`, and after-backward-vs-after-forward RNG as applicable; actual nine archived sampler cases PASS.
- The same weight content fingerprint is checked before/after training cases, while S6 is checked by the sampler acceptor after eval forward.
- Nine archived training equality/repeat comparisons recorded `logit_max_abs=0`, `loss_delta=0`, `grad_max_abs=0`, `grad_count=74`, all PASS; selected three previously frozen F2-C scalar gradient values included without reselection.
- S2 has backward update replay 1; S3 backward block replay 2; no sampler calls in backward. All archived global RNG sampler-entry->sampler-exit transitions agree with exactly one isolated shadow `torch.rand` draw, and sampler_exit/after_forward/after_backward match in the recorded **no-dropout** path.
- Twelve distinct injected synthetic negative records use the real sampler/gradient validators and yield expected 11 FAIL + 1 BLOCKED; the script's exit mapper maps FAIL/BLOCKED/INCONCLUSIVE to nonzero statuses by code inspection. There was no separately archived negative CLI process.
- Independent audit confirmed code-level validation of observed float32 vs bool grad flags, n/k formula and scalar Train [1] vs Eval [] PyTorch long tensor shapes. Note: instrumented sampler captures the dtype/shape of `n` rather than independently logging the dtype/shape of `k`; pinned native code converts **both** values to `long` and generates matching shapes. This limited observability is documented and is **not** promoted as direct separate empirical shape evidence for k.
- Recorded metadata does not archive raw per-parameter gradient arrays, only values and aggregate maxima; independent reviewer verified production comparison logic and archived summaries, not every raw gradient independently.

### Independent artifact integrity check

Exact SHA-256 re-calculated by ChatGPT from GitHub-hosted evidence, 4/4 match `RUN_META.json`:
- `F2D_D7_B1R2_RESULTS.json`: `30c0d175c5e0b12ed4fe6b70e8bd747358e9e89ef7e6145ddaca27a078495dc0`
- `stdout.txt`: `6d77acd821bb0cde25b1cfeaddfcfb967ed23b6bd26fcb3e8863f6a16a8cafdc`
- `stderr.txt` empty: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `exit_code.txt` `EXIT:0\n`: `194ff5bca66278888f0f00be5c7ca523d15098ece958b14952533811089f6106`

## 4. Final decision, untested scope and discrepancy

- **F2-D D1–D6**: PASS/CLOSED for fixed-depth native CPU non-reentrant per-iteration and per-block checkpoint equivalence.
- **F2-D D7 S1–S6**: PASS/CLOSED for defined default **per-batch** Poisson auto-depth sampling + CPU RNG and checkpoint comparison, exactly as pinned.
- **F2-D combined *explicitly defined CPU* experimental scope**: **PASS/CLOSED**.
- **F2-B/C**: remain PASS/CLOSED, unaffected.
- **Open upstream semantic discrepancy:** `randomized_iteration_sampler()` default scalar `n=T` vs `_sample_batch_depths()` `n=T-k`; cannot conclude intended semantics, architecture defect or corrective change without separate upstream documentation and controlled experiments.
- **NOT TESTED:** per-sequence/per-token runtime correctness; checkpoint reentrant/activation_checkpoint_impl in-coda/SAC; stochastic dropout with `preserve_rng_state=False`; native train.py multi-step learning, optimizer MuonAdamW; GPU/CUDA memory/throughput; distributed runtime; Gate 2.2-C; other seeds/configs/micro-inputs.
- Native pure float64 derivative validation remains separately BLOCKED from upstream float32 casts. Do not conflate with checkpoint result.
- This was **independent code/source/JSON/hash audit of Grok's logged CPU run**, not a fresh separate ChatGPT execution of original Parcae. The truth of 74 full gradient comparisons is supported by committed test logic and local PASS evidence, not an independently captured raw full gradient table.

## 5. Next exact instruction and checkpoint hygiene

**Next phase: F2-E (design-only upstream sampling semantic review), no CPU experiments authorized by this checkpoint.** Have Grok first read this final checkpoint and the pinned native sampler source. Produce a docs-only audit comparing `per-batch`, `per-sequence`, `per-token` n/k semantics, expected total recurrence and actual loss/grad routing, and attempt to identify upstream intended design via code comments/tests/docs. Define a minimal CPU probe with a separate acceptance matrix and frozen input; do not assume a defect or patch Parcae. Submit independent design at `PENDING CHATGPT REVIEW` before any new execution. No GPU, training, new dependencies, upstream edits, or branch merges. Preserve all historic evidence and the unrelated `gate2_1/TEST_RESULTS.json` local change. Log Git status, dependencies and unresolved questions at each future stage.
