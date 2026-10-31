# MECH-C v1 — depth-specific low-rank adaptation

Pre-registered 2026-10-31 before native MECH-C execution. User authorized further independent mechanisms. Base PR20 at 4cf60b053c7b9c2e89e64646cd986d33a34a7657, checkpoint read live. Preserve A/B primary FAIL, their within-training-horizon secondary signals, and all older results. This is C only, not A+C, B+C, a difficulty search or an upstream repair.

## Question and fixed arms

Can a small depth-specific linear correction improve the four-step native Parcae beyond a parameter-matched correction shared by every iteration? Same original backbone, initialization recipe, data, optimizer and update count. Three arms x seeds42/20261029/20261030, exactly3000 updates/batch32 per arm:

|Arm|Extra correction at each of four iterations|Added parameters|
|---|---|---:|
|P4|None; untouched native transition, exit4 CE|0|
|S16|One shared rank16 pair per target projection, reused every iteration|2560|
|C4|Four independent rank4 pairs per target projection, indexed by iteration0..3|2560|

Targets ONLY native core_block.0.attn.c_proj (32->32) and core_block.0.mlp.proj (64->32). At each target, y = native_linear(x) + (x @ down.T) @ up.T, scale1, no bias/dropout/nonlinearity. Original backbone remains trainable; this is NOT adapter-only fine-tuning of a frozen pretrained model. No changes to other layers, native VE paths, initial state or old loss functions. No auxiliary supervision or damping. Final CE only at4. All retain config mean_recurrence=2 and original layer IDs/initialization; explicit [0,4] changes unrolling only. Evaluation depths2 and4; depth2 uses first two C4 adapters. No extrapolation beyond4 is claimed or supported.

Each projection's canonical down bank is shape[4,4,input_dim], drawn from N(0,1/input_dim) with private CPU generator seed+31000. C4 uses four slices; S16 reshapes the SAME numbers to[1,16,input_dim]. Up factors all zero. This preserves initial logits/base gradients and caller RNG while allowing nonzero up-factor gradients. Zero down-factor gradient at this zero-up initialization is expected, not an inactive path. Parameters and all adapter states must enter optimizer, clipping and serialization. Base tensor initialization is identical across arms; full state shapes necessarily differ.

## Controls and interpretation

A P4 control is run contemporaneously to anchor this new comparison, not to reopen old evidence acceptance. C4 versus S16 is the PRIMARY contrast. C4 versus P4 and S16 versus P4 are secondary screens. Same added parameter count does NOT imply the same per-iteration rank or FLOPs: S16 applies rank16 each iteration, C4 rank4. Measure actual supported forward/backward and generation counts; report rank/compute difference explicitly. A win over P4 alone is insufficient evidence for depth-specific allocation. Even a win over S16 supports this allocation under this recipe, not a universal pure causal effect of depth specificity. No equal-compute/hardware-efficiency claim.

## Frozen inputs and producer

Read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Reuse original m2_matched factory/pair_io SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967 and R1-B task SHA2561baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af. A-M2L-01 remains disclosed, not silently repaired; A-M2L-02 reviewer cause remains OPEN separately.

Reuse19977 training rows/10000 canonical pairs,1024 balanced development questions (256 per carry category); train SHA256d2603d85dca18da104b6138e4513fd47be7c8f2063f447534807f86d68e3c458, development SHA256f232a8bc703e5aea07d89637f67110442a5d3882f560b05487c4462d31cd02cd. Already-viewed DEVELOPMENT, not a new holdout. Reserved test never emitted/scored. No new task selection or 90% capability ceiling. Carry count is a stratum, not a proven monotonic difficulty scale.

Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0; CPU FP32 one thread, deterministic algorithms, math SDPA. No compile/cache/checkpointing/dropout, no installation/download/GPU. Original initialization for each seed; batch generator seed+12000, training RNG seed+2000. AdamW lr0.002,betas(0.9,0.999),eps1e-8,weight_decay0,clip_norm1 over ALL trainable parameters.3000x32 exposures=96000 problems,384000 target tokens per arm. No checkpoint selection, seed selection, rank sweep, learning-rate search, budget extension or automatic retries.

## Mandatory implementation checks before native updates

Fixture tests cover low-rank algebra and gradients, zero/disabled identity, exact phase routing, shared rank control, canonical initialization, no caller-RNG consumption, hook cleanup on error, optimizer coverage and adapter checkpoint roundtrip. These are component checks, NOT native learning.

In required producer, all seeds and depths2/4 at lengths6/9: native versus P4 and zero-initialized C4/S16 logits/loss/base gradients/None patterns/caller RNG, rtol1e-5 atol1e-6 (loss absolute1e-6). Require exactly two projection calls per iteration, no hook leaks or registered-base-state mutation. At d4 require nonzero finite adapter up gradients and present finite down gradients. Count expected base60224 and adapted62784 registered parameters; S16/C4 added states each2560. A failed implementation/environment check -> BLOCKED, zero training updates. Never waive version/identity checks to obtain a score.

## Evaluation and outcomes

All nine valid arms execute regardless of another arm's scientific result. Save all3000 losses, gradient norms and pre-forward RNG hashes, batch indices, full model+adapter/AdamW/CPU RNG state, complete d2/d4 greedy predictions, answer NLL, strata, correction/corruption, measured counts, descriptive walltime and worker-lifetime peak RSS. Evaluation is full256-way greedy output of four digits from six prompt digits only; teacher-forced NLL is separate. Reuse seeds+80000+batch_offset for generation and+90000 for NLL. No answers/calculator at inference.

Primary C4-S16 at d4: mean paired exact-answer gain>=0.01 AND each seed delta>=-0.01. If S16 mean>0.99 -> BLOCKED/CEILING, retaining regressions. Otherwise completed unmet criteria -> FAIL. Secondary C4-P4 and S16-P4 use the same screen, independently labelled. d4-d2 per arm: mean gain>=0.01, every seed positive, carry0 delta>=-0.01 per seed; d2 mean>0.99 -> ceiling. Report mean,worst seed,spread and all signed differences. These are exploratory engineering thresholds, not significance/noninferiority or final scientific acceptance.

Execution PASS requires9 complete finite arms,18 conditions, identical initial base hashes/batch indices/RNG traces and matched C4/S16 parameter counts. Exit0=primary C4-S16 PASS,1=completed primary FAIL,2=operational/implementation or ceiling BLOCKED. Primary status is separate from secondary quality/depth/cost. Same data/updates, NOT equal compute; fresh held-out and equal-budget confirmation NOT TESTED. No native results exist at protocol registration.

## Delivery and boundary

Only new research/mini_mythos/mech_c files; import existing helpers without changing old sources or upstream. Keep new PR Draft/unmerged. Save preparation environment, actual checks, remaining issues and next command in CHECKPOINT.md. Grok/Claude cross-review NOT TESTED/DEFERRED until a real report; do not impersonate reviewers. D dual-state and E stopping remain separate later candidates. No automatic combinations, test opening, merge, GPU or G2 REAL. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; J1/Bench/R3 untouched.

Research inspiration: Relaxed Recursive Transformers (ICLR2025), https://arxiv.org/abs/2410.20672 . This is a new small from-scratch Parcae intervention, NOT a reproduction of that paper's pretrained initialization, training regime or results.
