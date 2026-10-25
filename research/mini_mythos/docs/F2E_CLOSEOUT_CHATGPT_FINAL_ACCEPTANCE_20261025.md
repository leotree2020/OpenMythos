# F2-E — Grok B1-R3 Final Acceptance Delta: ChatGPT Independent Bounded CPU Acceptance

Date: 2026-10-25 (Asia/Tokyo)  
Reviewed Grok commit: `fbeaf7c5030c460343ca2006dc53813c21786dfd`  
Prior frozen gate: `research/mini_mythos/docs/F2E_B1R2_CHATGPT_REVIEW_AND_R3_GATE_20261025.md`  
Prior R3 independent audit: `research/mini_mythos/docs/F2E_B1R3_CHATGPT_INDEPENDENT_REVIEW_AND_CLAUDE_HANDOFF_20261025.md`  
Upstream pin: `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`  
Reviewer: ChatGPT; review type: independent GitHub source + archived evidence + independent checksum and expected-mask reconstruction. **Not an independent native PyTorch/Parcae CPU re-run**.

## 1. Formal decision

**F2-E E1–E5: PASS / CLOSED ONLY FOR THE FROZEN NATIVE PARCAE CPU SAMPLING/MASK/REPETITION/CHECKPOINT MICRO-SCOPE.**

**F2-E E6: INCONCLUSIVE, NOT CLOSED**, and explicitly **not** a block on independent E1–E5 bounded closure; Parcae author design intent `UNKNOWN`; cross-mode logit equality `NOT APPLICABLE`.

This closure does NOT imply:
- whole F2-E is a blanket PASS;
- all native sampling configs, seeds, widths, depth settings, recurrent attention designs, optimizer or all checkpoint implementations correct;
- full derivative correctness, complete training lifecycle, GPU, meaningful language generation, state-of-the-art performance;
- identity with a proprietary Claude Mythos implementation; or
- discovery of a native Parcae bug.

All previously frozen F2-B/C/D narrow PASS/CLOSED remain unchanged.

## 2. Locked scope actually evidenced

- CPU reported Python 3.11.2, PyTorch 2.14.1+cpu, float32/SDPA, pinned native Parcae upstream clean per Grok run report. No GPU and no upstream source modifications in reviewed OpenMythos commit.
- Fixed 2 Prelude / 2 Recurrent Core / 2 Coda, 247,936 parameters, 74 trainable gradient tensors, seed 42, fixed input hashes, mean_recurrence=2, mean_backprop_depth=2.
- E1 per-batch: real native n=[1], k=[1], outer=2.
- E2 per-sequence: native n=[0,0], k=[1,2], actual native returned [0,1], outer=2, 2 grad masks (2,1 true counts).
- E3 per-token: actual n/k arrays match frozen reference and mean [0,1]; 5 no-grad + 2 grad masks, true counts [5,2,1,1,1,16,11], outer=7. Native update operands x_new and xk checked by wrapper.
- E4 same-mode sequence/token repetition: logits/loss/gradient maximum difference 0.0, 74 gradient tensors.
- E5 sequence/token checkpoint OFF/ON: same zeros, 74 gradient tensors, backward replay **exactly 2 ON** and **0 OFF**; new acceptance tests enforce exact 2 for frozen ON config.
- Negative suite reports **19 rejected** input and harness corruptions (n/k, count, mean, sampling while backward, missing/extra mask, step 999, phase, raw mask bit flip, synthetic bad callsite label, RNG mismatch, replay missing/one, weight fingerprint, NaN/zero/missing/extra grads).
- E6 prior target-token direct Core replay delta 0.0049576908349990845 and positive control 0.04084044694900513 are **exploratory only**, not a live masked-loop causal demonstration. No E6 experiment rerun.

## 3. Archive integrity: independently recomputed SHA-256

The following **six** declared SHA-256 values were recalculated from exact GitHub source and evidence file contents and all matched Grok's `RUN_META.json` (not mere copy):
- `F2E_CLOSEOUT_RESULTS.json`: `6fa4ad7a959e51b184a9583b7cd8d4b0a61543a1fb676103bab8bd3c294ce574`
- `stdout.txt`: `a922c699b87dee121ada2ff59ab1dbf3822959b3b178b3bdd373cb86503f14f9`
- `stderr.txt`: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty)
- `exit_code.txt`: `4f9485719ee49db6c2c06addf4c3f0c452cc5fe84ef9aac95efe65f4a3e0d6e8` (`EXIT:3\n`)
- `fail_exit.txt`: `840895b6d3def20850a65e59e68da151c82937cc0ecc431874f7678ceeb73326` (`EXIT:1\n`)
- committed `test_parcae_sampling_modes_cpu.py`: `b5afd03737a8e236dc54c9e5ead08236e8d8372bbd6011547a01c33fd3b76c89`

Additional `fail_demo.txt` committed content `FAIL demo\n`, independently SHA-256 `b7747591bbebe106a620babf48583a972897f5ef91cf7364c0c0849d812be027`. Grok's manifest does **not** declare a hash for this ancillary text file. This is a minor archival omission, not a sampled mathematical failure; the independent observed exact bytes and exit code suffice for the narrowly scoped fail-exit demonstration.

### Independent 9/9 Mask raw-bit reconstruction

For each archived E2/E3 record, reviewer generated a fresh bit array by applying its archived `phase`, `step` and n/k to the original reference rule `step < n` or `step < k`, flattened row-major and converted to byte values 0/1 as the frozen CPU Boolean tensor checksum code does, then independently calculated SHA-256. **All 9 mask digests exactly MATCH** the archived `mask_sha256` and all nine true-bit counts:

E2 grad 0 `9dcf97a184f32623d11a73124ceb99a5709b083721e878a16d78f596718ba7b2`; grad 1 `b413f47d13ee2fe6c845b2ee141af81de858df4ec549a58b7970bb96645bc8d2`.

E3 no-grad 0 `ccf7a47d961e7ece236df4dc05a9eff21b4fe1682b57f1e918178a7e40603709`; no-grad 1 `8f239a25128e381ce8ec76c7476d87994515b149ae4d970ac083bf3d83545dc9`; no-grad 2/3/4 each `7c3ccd10bb7ec37b46d37926ae6274267f007a34aeaf15c882a715a7f3300529`; grad 0 `cc8cd41cef907c4d216069122c4b89936211361f9050a717a1e37ad1862e952f`; grad 1 `91d7c5f90969b704d704e710899003f94cddb2f14639c183f9f24c3991ca73db`.

**This is stronger than accepting the script's own `content_ok=true` assertions; it still cannot replace an independent native runtime replay.**

## 4. Source acceptance review

The closeout probe:
- rejects missing/excess recurrent masks and nonconsecutive/wrong phase+step;
- checks the raw Boolean mask elementwise before archiving, then archives its SHA256 before discarding the tensor;
- ties each accepted `torch.where` to a just-observed native `update_recurrent_state` output and previous state in the known pinned source loop, checks selections and operands;
- compares actual pre/post weight hashes in paired runs, and verifies grad names/finite/nonzero/shape against `requires_grad` parameter metadata within that run;
- records `rng_sampler_entry`, `rng_sampler_exit`, before/after forward, after backward; compares exit and after-backward between paired runs, with global before/after-forward also compared;
- enforces exact replay count 2 in checkpoint-on E5 paired cells and 0 in baseline;
- archives a separately executed no-model failure-exit demo (`EXIT:1`). Normal `EXIT:3` is due to E6 `INCONCLUSIVE` and does NOT negate independently passing E1–E5.

Narrow transparency notes:
- `rng_sampler_entry` is captured but not directly used as a separate paired acceptance key; `rng_before` is compared and other sampler/forward/bwd boundaries are checked. This is not a demonstrated discrepancy in recorded runs.
- The `grad_shapes` expected set comes from the actual trainable `named_parameters()` rather than a hard-coded external golden names list; the 74 actual gradients and its trainable-name/shape set must match. No claim of comprehensive parameter semantics.
- `--fail-demo` exercises the exit-code mapping with an explicit injected FAIL, not a model run; the harness negative checks are independently reported by the normal run.
- Reported upstream clean/worktree protection cannot be independently inspected from GitHub. `research/mini_mythos/gate2_1/TEST_RESULTS.json` remains locally dirty by Grok report and must be preserved.
- No new GPU, optimizer, full train, or E6 causality test is implied.

The remaining points are limitations/documentation nits **rather than reasons for a new unbounded sampling-test iteration**. Freeze E1–E5 scope now.

## 5. Next stage — authorization boundary

Grok has also committed `research/mini_mythos/docs/F2_CPU_TRAIN_LIFECYCLE_PLAN.md`, **DESIGN ONLY**. It outlines random weights, native Parcae 2/2/2 CPU float32, Forward→Loss→Backward→Optimizer→Scheduler→Checkpoint→Resume, with finite grads, parameter update, loss behavior, LR scheduler, checkpoint state and reproducible resumed step. It has NOT been run, and its numerical tolerances/negative cases/full train-entrypoint scope must be frozen separately before execution.

**Authorized next work**: source read-only and frozen CPU train-lifecycle gate elaboration, plus user-approved edits restricted to the training plan. **NOT authorized**: executing new end-to-end native CPU training, running GPU, modifying Parcae/AxoNN, or modifying the core recurrence.

Recommended phase order:
1. New session checks latest Git HEAD, dirty, current SOP/map and this final report. Grok remains implementation engineer, ChatGPT remains independent auditor. Claude Code handoff deferred by user's current decision.
2. Design/review/freeze a distinct native Parcae CPU Train Lifecycle gate, including explicit starting weights, deterministic input batch, optimizer/scheduler config, baseline/continuation branches, model/optimizer/scheduler/CPU RNG checkpoint state and digest, loss tolerance and restart equivalence, exact pass/fail.
3. Separately request user authorization to run that CPU gate. No GPU until Gate 2.2-C credentials, budget, environment and live extractor resolve.
4. After CPU lifecycle evidence, investigate controlled fair quality/efficiency baselines; no premature Mythos equivalence claims.

## 6. Formal checkpoint

- `F2-B`: PASS/CLOSED (previous bounded).
- `F2-C`: PASS/CLOSED (previous 3-scalar gradient bounded).
- `F2-D`: PASS/CLOSED (previous fixed/per-batch bounded).
- **`F2-E E1–E5`: PASS/CLOSED (THIS frozen 2/2/2 CPU micro-scope only).**
- `F2-E E6`: INCONCLUSIVE (not rerun; optional future standalone causal research).
- `Native Parcae full CPU training lifecycle`: NOT TESTED; design proposal only.
- `GPU Gate 2.2-C`: BLOCKED; no approved GPU run.
- `Next distinct task`: freeze the CPU Training Lifecycle independent acceptance plan; after authorization execute isolated CPU run.
- Stage history/old evidence immutable; branch latest commit must be rechecked on new session. 
