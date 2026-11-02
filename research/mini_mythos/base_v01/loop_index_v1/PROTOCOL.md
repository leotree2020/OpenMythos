# MYTHOS-LOOP-INDEX-CPU-V1

Purpose: test whether a small, separately trained iteration-number signal improves next-token prediction over the unchanged official Parcae140M at fixed32 recurrence, and whether it improves over a parameter-matched shared bias. This is a local adaptation pilot informed by OpenMythos. It is not a reproduction of a proprietary model, a depth-extrapolation test, or a statistical confirmation of general architectural superiority.

Restore from checkpoint d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85 on mythos-depth-lora-cpu-v1. The isolated continuation branch/worktree is mythos-loop-index-cpu-v1. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains read-only. Original model weights and historical evidence remain unchanged. No LoRA stacking, adaptive exit run, controller edit, threshold change, B1 rerun, A5 relaxation, B2/D2-A, MoDA/MoE implementation, GPU use or PR24 operation belongs to this experiment.

## Source relation and competing explanations

At d2d6ddd1, open_mythos/main.py:541-570 defines a fixed sinusoidal additive loop-index signal; RecurrentBlock applies it before its normalization and transformer. Its defaults are theta=10000 and loop_dim=dim//8. The name in the source heading is not evidence of a rotary operation: the actual operation is addition. The present adaptation uses its 96-channel sinusoidal pattern for width768, with a new trainable zero-initialized gain to preserve the pretrained starting function. The injection is after native Parcae's adapter, before its first recurrent core block. These gating and placement choices differ from the OpenMythos model and are explicitly research choices.

Competing explanations are: a useful depth-dependent signal; ordinary shared bias adaptation; a feature-conditioning or optimization effect of this sinusoidal parameterization; no useful gain under this small training budget; or degradation from disturbing a pretrained recurrence. Negative evidence concerns this recipe and budget, not all forms of loop encoding. No unmeasured mechanism interaction or extrapolation is inferred.

## Exact arms and equations

- F: unchanged model, fixed32, no trained adaptation.
- S: a shared96-dimensional trainable bias applied on every recurrence, zero initialized.
- C: a shared96-dimensional trainable gain multiplying a fixed iteration-number code, zero initialized.

Both S and C have exactly96 trainable FP32 parameters. No unused parameters are added to make counts match. Let t=0,...,31 and j=0,...,47. Construct the fixed CPU FP32 source-style table by the following operations, in this order:

    exponent = torch.arange(0, 96, 2, dtype=torch.float32) / 96
    frequency = 1.0 / (10000.0 ** exponent)
    angle_t = t * frequency
    code[t] = torch.cat([angle_t.sin(), angle_t.cos()], dim=-1)

For native adapter output y with shape[1,T,768] and gain g with shape[96], use:

    S: delta_t = concat(g * ones(96), zeros(672))
    C: delta_t = concat(g * code[t], zeros(672))
    y_modified = y + delta_t[None,None,:]

No code RMS normalization, learned frequency, per-depth parameter bank, learned extra gate, token-position change, or permutation arm is present. Code values are immutable and finite. The same code/bias applies to every token position; it does not mix positions or use targets. Every native forward must invoke the adapter exactly32 times, in order0..31. The sinusoidal first48 coordinates at t=0 are zero by construction and are not a failed gradient check. S uses the same multiplication/padding/addition path with an all-ones feature table.

Trainable parameter equality removes the earlier32-fold table/bias capacity difference. It does not make the sinusoidal and constant features equally conditioned. Gains on low-frequency sine coordinates can receive smaller gradients; this is part of the frozen recipe. A C advantage over S is evidence for this depth-dependent parameterization under these conditions, not proof that an abstract concept of iteration number is universally useful.

The implementation uses temporary native adapter forward hooks; it must not replace upstream modules or alter source. Counters reset for every forward and hooks are removed in a finally path. All original parameters are frozen, original model remains in eval mode, gradients are enabled only for training, and explicit native num_steps_pair=[0,32] is required. No truncated BPTT or activation checkpointing is allowed. Each of the32 recurrence contributions participates in the native saved computation graph.

## Frozen inputs and separation

Reuse, without reselection or re-tokenization, the sealed LoRA preparation input JSON: /workspaces/mythos-evidence/base_v01/depth_lora/preparation-v1/data/inputs.json. Expected size81885 bytes and SHA256 b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc. Its16 training and16 validation article windows come from official WikiText2 raw revision6231e49f19a707241d6b84d9cff60a3a86b85a85. Preserve all existing source/split/tokenizer identity and overlap checks. Train source SHA25649280f3dd993cbdfd322186194133d5d1935f81e1c91064c239f2a70ebb02701; validation SHA256a10eb5a42c4264c45dd38bfef4da6a74ddef5fc22cb419e1a89d54c4cc6d748f; tokenizer SHA256e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77.

This validation set has already informed the LoRA development experiment. It is now a reused development benchmark, not fresh-test generalization, independent final confirmation, the full published WikiText benchmark, or evidence of absence from original pretraining. No article may be removed or replaced based on a model outcome. No test article is repurposed for training.

## Fixed training and execution schedule

Training seeds4101 and4202. Initialize a new zero gain vector for each arm/seed; unlike random LoRA initialization, these vectors start identically. The training seed controls the prescribed h0 sequence, not a random gain initializer. Each arm/seed starts from the same unchanged original weights and sees identical ordered articles and paired actual h0 values.

Exactly32 optimizer steps per arm/seed: batch1,16 frozen articles in ascending frozen identity repeated twice, article=step mod16. Input tokens0..127 predict targets1..128, all128 targets. This is4096 scored training-token presentations per arm/seed. Training h0 seed=1000000+100*training_seed+step, for step0..31.

AdamW: LR0.001, betas(0.9,0.999), eps1e-8, weight_decay0, foreach=False; global gradient clipping maxnorm1. No scheduler, hyperparameter sweep, tuning, early stopping, validation selection, extra steps, extra seeds or model rerun. Loss curves are descriptive. Save every step loss, gain/gradient/update diagnostics, final gain+optimizer+RNG state, and initial/final fingerprints. Resume-trajectory equivalence is NOT TESTED.

Main order: five zero controls (one native reference and one zero-gain call for each of four arm/seed instances),32 F evaluations, then S4101,C4101,S4202,C4202; each trained arm's32 steps are immediately followed by its32 final evaluations. Thus the main run contains293 forwards and128 optimizer steps; a fresh-process reload worker makes four additional forwards, one predefined evaluation case per saved adapter. The zero/reference case is the first frozen training article with h0 seed6101. The reload case is the first frozen validation article with h0 seed5101. Evaluation results never change the schedule.

## Evaluation and scientific screens

Use16 validation articles and h0 seeds5101/5202. Each forward takes128 input tokens and scores the last64 causal predictions: logits positions64..127 versus original body token indices65..128. Actual h0 must match bit-for-bit across arms for every paired case. Preserve all160 case metrics:32 F and32 for each of four trained adapters. Save raw scored FP32 logits externally, with exact shape/dtype/size and SHA256, for an independent FP64 stable-logsumexp audit. Compute equal-article means, paired per-article differences, pooled top1 counts, separate training-seed summaries, and worst article degradation. Do not count the two h0 seeds as independent articles.

Primary C-vs-F practical improvement screen: for EACH training seed, equal-article mean NLL averaged over the two h0 seeds decreases by at least0.01 nats/token and pooled top1 accuracy decreases by no more than0.01 absolute. Both training seeds must pass. Use the same frozen margins for the parameter-matched C-vs-S secondary screen and the descriptive S-vs-F screen. These are exploratory practical screens, not p-values or statistical confirmation. No aggregate overrides a failed per-seed requirement.

- C-vs-F and C-vs-S both PASS: local evidence favors this depth-dependent encoding over both native and shared-bias controls within the frozen budget.
- C-vs-F PASS, C-vs-S FAIL: useful adaptation signal, but no passing evidence that depth dependence adds value over shared bias.
- C-vs-F FAIL, even if C-vs-S PASS: no passing benefit over original F32.
- Mixed seeds, smaller gains, unchanged results or deterioration: report the complete numbers and screen FAIL; do not infer universal ineffectiveness or tune after observing them.

For each comparison and training seed, additionally label the descriptive direction before aggregation: IMPROVEMENT when both registered improvement conditions hold; WORSE when NLL rises by at least0.01 nats/token or accuracy drops by more than0.01 absolute; otherwise NO_QUALIFIED_IMPROVEMENT. Preserve both seed labels; opposing labels are reported as mixed, never hidden in a cross-seed average. NO_QUALIFIED_IMPROVEMENT does not establish statistical equivalence, absence of effect or ineffectiveness of loop encoding. WORSE concerns the measured recipe, not a general architectural verdict.

All screens are computed after the full fixed valid schedule. Scientific screen FAIL is a valid negative result to seal, not an engineering error or permission to change settings. Generalization, statistical confirmation, depth extrapolation, generation quality and LoRA/encoding interaction remain NOT TESTED.

## Engineering acceptance and stop rules

Development checks must exercise meaningful causal/gradient/routing/serialization and startup interfaces before implementation freeze; model outcomes may never justify editing the frozen runner. Required checks include native zero-gain identity, exact96 trainables per arm, depth-order coverage0..31, no future-label or future-token dependence, correct loss alignment, exception cleanup, gradient flow, reload and source/evidence custody.

The five real-model zero controls must produce bitwise-equal logits and identical actual h0 and RNG states. Apply the same ordinary addition at zero as during training; do not add a zero-gain shortcut that bypasses gradient flow or conceals a mismatch. IEEE signed-zero effects are a known reason mathematical identity is not a universal bit-pattern guarantee. A real zero-control mismatch is FAIL; do not relax bitwise comparison or rewrite the operation after seeing the result.

Every training step must have an existing finite gain gradient, a positive gain-vector gradient norm and a nonzero finite update; all loss/logit/checkpoint values must be finite. Report all96 per-coordinate nonzero-gradient and update masks, including first-step and final coverage. Exact nonzero values for every coordinate at every step are not mathematically guaranteed and are not required. Distinguish a zero sine feature at t=0 from a disconnected graph. Retain the gradients of the32 distinct per-forward delta tensors, each computed from the gain and that iteration's fixed features. For every training step require all32 retained delta gradients present and finite. Define each depth's contribution to the gain gradient as delta_t.grad[:96] * feature[t], where feature is code for C and ones for S. Measure the norm of this96-dimensional contribution, not the full768-dimensional padded delta gradient. Over the32 steps of EACH arm/seed, every depth must have a nonzero gain-gradient-contribution norm on at least one step. Save the32-depth coverage and contribution norms; fail missing aggregate depth coverage. The sum of these contributions is the mathematical decomposition of the shared gain gradient and must be verified in a development gradient test with declared numerical tolerance. The observer must not change forward values or create a second model graph. These checks establish graph participation; they do not establish that all depths are useful.

Require all original parameters to have requires_grad=False and grad=None throughout, optimizer membership exactly the gain vector, original63 state entries byte-identical before/after, exactly expected forward/step/evaluation counts, no preexisting conflicting hooks, clean hook restoration, valid immutable feature table, paired actual h0 identities and complete finite evidence. Reload all four saved adapters in a new process, restore the same runtime, and reproduce the predefined scored logits bit-for-bit. Run an independent artifact audit recomputing each case NLL/top1 and all screens from saved logits and frozen targets.

Any engineering FAIL or BLOCKED stops dependent computation immediately without a retry; preserve partial evidence, return a nonzero failure status where appropriate, and write the actual failed guard. Missing target resources are BLOCKED, not negative scientific evidence. A completed scientific screen FAIL does not trigger a new run or erase the completed evidence.

## Runtime, resources and evidence

Designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr only. Existing Python3.12.3/Torch2.11.0+cpu environment, CPU FP32,2 intra-op/1 inter-op threads, deterministic algorithms, no enabled autocast. Reuse the locked environment; no package installation. Record actual CPU/runtime/import state, source hashes, all input hashes, upstream status, branch, execution freeze and evidence paths. No competing experiment worker is permitted. Available-memory admission remains3GiB; model worker timeout3600 seconds with no automatic retry.

Raw scored logits have a known worst-case size160*64*32768*4 =1,342,177,280 bytes. Require evidence disk availability at admission of at least this size plus64MiB records/checkpoint allowance plus256MiB reserve:1,677,721,600 bytes in total. This is a calculated allocation, not the earlier arbitrary2GiB disk gate. Stream each raw logit record and compute hashes; avoid a second complete copy or an in-memory all-logits collection. Do not assume compression savings, delete old evidence, or silently reduce cases/precision. Preserve the256MiB reserve and report disk accounting. If the forecast no longer suffices, stop BLOCKED and seal what exists. Small public-export/review files must fit the declared allowance.

Every stage records Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Git stores protocol, code, tests, static review, manifests, per-case metrics, training curves, audit results and checkpoint. Full corpus/token arrays, raw logits and binary optimizer/gain checkpoints stay in the designated external evidence directory with hashes and paths. Do not copy old weights or source datasets into Git. Internal agents may review; no external Claude/Grok review is claimed.

Complete implementation review and freeze before any real-model call; identify the exact execution commit in the run. After execution/audit, commit evidence and a checkpoint with result, branch/commit, environment, unresolved issues and one next instruction, then stop this experiment. Next-stage direction is a separately specified MoDA experiment followed by separately specified MoE, with their own controls and resource admission; no mechanism4 execution is bundled into this protocol. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False.

Source references: https://github.com/leotree2020/OpenMythos/blob/d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85/open_mythos/main.py ; https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/parcae_lm/models/parcae/parcae.py . Source reading supports the operations and placement described above, not the untested improvement hypothesis.
