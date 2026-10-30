# MECH-AB v1 — isolated supervision and whole-iteration damping

Pre-registered 2026-10-30 before native MECH-AB results. User explicitly authorized development after selecting separate mechanism tests. Base: leotree2020/OpenMythos@78d9c49112f5e1299767d450593f3db08feaf7c6 (PR19). This is a NEW mechanism-development stage, not continuation/repair of the failed R1-B qualification. Old results/thresholds are unchanged.

## Question and arms

Does one isolated change improve the same native Parcae at a fixed number of training examples/updates? All three arms run all three original seeds (42, 20261029, 20261030), 3000 AdamW updates, batch32, max forward/backward unroll4, no truncation. One configuration per intervention, no sweep or combination:

| Arm | Native recurrent update | Objective |
|---|---|---|
| P4 | original update | CE at exit4 only |
| A | original update | 0.25 CE at exit2 + 0.75 CE at exit4 |
| B | old + 0.5*(native_candidate-old) each iteration | CE at exit4 only |

A's exit2 and exit4 are from the SAME trajectory, not two separate forwards. The second exit uses the same native C/coda/ln_f/lm_head parameters. Its readout occurs after the native final forward in a forked RNG context, without modifying the continuing recurrent state or caller RNG. No detach in the auxiliary path. B interpolates the WHOLE iteration (including input injection and core), not merely an inner attention residual. alpha=1 has an exact identity branch. No new trainable tensors in A/B. Existing inactive paths are neither deleted nor repaired.

Keep factory config mean_recurrence=2/mean_backprop_depth=2 and original initialization exactly; P4 means explicit num_steps_pair=[0,4], NOT changing config-derived initialization, layer ids or VE indexing. Native source sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 is read-only. Use existing m2_matched factory/pair_io (SHA256 74f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967). Do not run the prior initializer tools. A-M2L-01/02 remain scoped limitations, not presumed causal explanations.

## Data, initialization and compute

Reuse R1-B train/development generator unchanged (task.py SHA256 1baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af). Train19977 ordered examples/10000 canonical pairs, dev1024 pairs,256 per carry0..3; swapped pairs isolated; reserved future-test data never generated/scored here. Train object SHA256 d2603d85dca18da104b6138e4513fd47be7c8f2063f447534807f86d68e3c458; dev f232a8bc703e5aea07d89637f67110442a5d3882f560b05487c4462d31cd02cd. This already-viewed DEVELOPMENT set supports exploration, not fresh confirmatory generalization. Carry count is a stratum, not an assumed monotonic difficulty scale.

Construct original GPT then Parcae for each seed, apply original pair_io, discard GPT. Every arm reconstructs the same verified original Parcae start; no old trained checkpoint. CPU batch generator seed+12000, training RNG seed+2000. All arms use identical per-seed 3000x32 sampled indices; persist/hash initial states, batch indices and RNG-before-forward digests. AdamW lr0.002, betas(0.9,0.999), eps1e-8, weight_decay0, clip_norm1. No schedules, early stopping or best-checkpoint selection. 96000 problem exposures,384000 target-token exposures per arm; A applies two losses to the same labels, not twice as many unique training tokens.

Runtime: existing Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0; FP32, one CPU thread, deterministic algorithms, math SDPA, no compile/activation checkpointing/cache/dropout. No install/download/GPU. One child process per arm records process high-water RSS (includes import/preflight/evaluation; not isolated tensor allocation or training-only memory). Training walltime is descriptive. Count supported forward/backward operators at actual32x9 per arm and full four-token greedy generation including final batch. Counts omit optimizer and unsupported operators (notably damping elementwise work); never equate counters with hardware cost.

This is SAME DATA/UPDATES, NOT equal compute. Auxiliary readout/backward overhead is included in measured counters; no assertion that all arms fit the old10% ratio. Report actual differences. Equal-compute confirmation is a separate later decision, not auto-launched. Existing GPT results are historical context only, not a concurrent depth4 control.

## Minimum implementation gate before any updates

On actual pinned native models, all three seeds: disabled wrapper vs untouched native at depths2/4, prompt and masked-training shapes, compare logits/loss/all gradients and None patterns, caller RNG and registered-state preservation. Tolerances logits/grad rtol1e-5,atol1e-6; loss absolute1e-6. Verify shared suffix matches native final logits; auxiliary loss has a nonzero path to shared core without final loss; counted objectives finite; no extra parameters; hook cleanup on completion/error. Native failures block training. Local fixture tests only validate wrapper mathematics and control plumbing, never native acceptance.

## Evaluation and predeclared exploratory decisions

All9 arms finish regardless of whether another arm's scientific screen fails. A numerical/source error stops the run with partial evidence retained. Each final model evaluated at d2 and d4 on the SAME dev1024 problems, full256-way greedy output, only six prompt digits then four generated tokens. Same seed+80000+batch_offset per generation condition; also record answer-only teacher-forced CE (not substitute for free accuracy). No held-out test, depth8, extra seeds or tuning. Persist every prediction, per-stratum counts, state hashes, optimizer/RNG checkpoints, losses and norms.

For EACH A/B vs P4 separately, primary quality screen at d4: mean paired full-answer accuracy gain >=0.01 (1pp), each seed gain >=-0.01. Missing/invalid paired records -> BLOCKED. If P4 mean d4>0.99, quality screen BLOCKED/CEILING, but ALL signed differences and regressions remain reported. Otherwise completed criterion unmet -> FAIL. This is an exploratory engineering screen, not significance/noninferiority, formal acceptance or proven architecture superiority. No 90% upper bound on learned capability. Both models scoring high is welcome, not a task failure.

Separately report (not replace primary): d2 deltas; worst-seed accuracy and sample spread; per-stratum accuracy; each model's d4-d2; wrong-to-right and right-to-wrong counts and rates; gain per counted inference cost. Secondary extra-depth screen per arm: mean overall d4-d2>=0.01, every seed strictly improves, carry0 loss<=0.01 per seed. Mean d2>0.99 -> ceiling BLOCKED. These are separate statuses; learning gains do not imply depth gains. Never promote a mechanism merely for lower loss variance or state movement.

Execution status PASS means9 complete finite training records and all18 dev conditions, pairing and source checks; it does NOT mean either hypothesis passes. Exit0=complete with both primary quality screens PASS; exit1=complete with any primary FAIL; exit2=operational/preflight block or only ceiling-blocked scientific screens (read detailed statuses). Full native execution and mechanism efficacy remain NOT TESTED until actual execution. No automatic retry/resume/delete. Existing outputs read-only.

## Deliverable and boundaries

One branch/PR and one new directory research/mini_mythos/mech_ab: protocol, wrapper, metrics, runner, tests, launcher, checkpoint. First run closes this bounded9-arm stage; no automatic C/D/E or A+B. Preserve all earlier results and source files. New reviewer request: same-trajectory supervision, whole-iteration damping, gradient identity, RNG pairing, true readout overhead, no test leakage, separate quality/depth/cost conclusions. Grok/Claude NOT TESTED/DEFERRED until actual report. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL/J1/Bench/R3 edits, upstream patch, auto-merge or GPU allocation.
