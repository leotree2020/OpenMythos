# MYTHOS-DEPTH-LORA-CPU-V1

Purpose: test whether a small, separately trained depth-specific LoRA improves next-token prediction relative to the unchanged official Parcae140M at fixed32 recurrence. This is an adaptation pilot, not a reproduction of a proprietary model or a statistical confirmation of a general architectural advantage.

Base checkpoint: e24d053f482a96bcc2ab207c1be73e4c91fcd721. Isolated branch/worktree: mythos-depth-lora-cpu-v1. Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 is read-only. No adaptive exit runs, controller edits, TV threshold changes, B1 rerun, A5 relaxation, B2/D2-A, loop encoding, MoDA/MoE, GPU, or PR24 operations.

## Competing explanations and arms

- F: original model, all parameters frozen, fixed32; no adaptation.
- S: shared rank2 LoRA in both recurrent attention output projections, shared across all32 iterations; original weights frozen.
- D: rank2 LoRA in the same projections, separate banks for each of32 iterations; original weights frozen.

LoRA is W x + B_d A_d x, rank2, alpha2 (scale1), no bias/dropout. A uses a seeded initializer, copied across depths from the same per-block initialization; B starts at zero. D has196608 trainable parameters; S has6144. Only those adapters are optimized. Native dimensions/routing/RoPE/initialization stay unchanged, and all32 recurrent iterations participate in backpropagation. Use model.eval() with gradients enabled to avoid training-only stochastic routing. Native explicit num_steps_pair=[0,32] is required. No truncated gradient or activation checkpointing is used.

D vs F tests the complete adaptation recipe. D vs S helps interpret whether shared adaptation is sufficient, but parameter counts differ by32x: superiority over S is not an isolated proof that depth identity caused the gain. Equally, no gain in this small training budget does not rule out LoRA at larger budgets. No mechanism combination will be performed in this stage.

## Inputs and separation

Acquire official WikiText2 raw train and validation splits at revision6231e49f19a707241d6b84d9cff60a3a86b85a85. Train SHA25649280f3dd993cbdfd322186194133d5d1935f81e1c91064c239f2a70ebb02701; validation SHA256a10eb5a42c4264c45dd38bfef4da6a74ddef5fc22cb419e1a89d54c4cc6d748f. Original tokenizer SHA256e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77. No old test article is repurposed for training.

Select16 source articles from each split without model scores. Use one conservative prose row per article, first129 body tokens; no concatenation across paragraph or article boundaries. The data program defines the exact title/prose eligibility and deterministic ordering. Save the full candidate inventory and manually inspect selected title/row evidence before execution freeze. Reject insufficient samples, duplicate titles/body/token windows and selected32-token overlap across train/eval. Preserve source bytes and hashes. Inputs and selection reports are frozen before any model call. The model worker cannot select/filter articles based on outcomes.

These are newly selected adaptation-held-out development texts, not evidence of absence from the original model's pretraining corpus. Official validation is used only for final assessment in this protocol, never checkpoint selection, LR choice, or retries. This is not the full official WikiText benchmark or comparable to its published perplexity.

## Training budget

Training seeds4101 and4202. For each seed independently initialize D and S from the same original model and matched initial per-block A. Both trained arms see the identical frozen article order and paired h0 random seeds. Exactly32 optimizer steps: batch1,16 selected articles,2 passes. Each step uses input tokens0..127 and shifted targets1..128, all128 targets. Thus4096 scored training-token presentations per arm/seed, not4096 independent source tokens.

Exact order is ascending frozen article identity, repeated twice (article=step mod16). Training h0 seed=1000000+100*training_seed+step, step0..31. A initialization is uniform[-1/sqrt(768),1/sqrt(768)] with an isolated CPU generator per training seed; the two blocks draw sequentially. Main execution order: five zero controls,32 baseline evaluations, then shared4101,depth4101,shared4202,depth4202; each trained arm's32 steps are followed by its32 final evaluations. Total293 main forwards and128 optimizer steps; four additional forwards in a new process verify one preregistered case per adapter. Evaluation outcome is never used to alter this schedule. Saving optimizer/RNG establishes checkpoint completeness; training-resume trajectory equivalence is NOT TESTED.

AdamW: LR0.001, betas(0.9,0.999), eps1e-8, weight_decay0, foreach=False; global gradient clipping maxnorm1. No scheduler, hyperparameter sweep, early stopping, evaluation-based selection, extra training steps or rerun. Save initial/final adapter fingerprints, every step loss/gradient/updates, final adapter+optimizer+RNG checkpoint. All four training runs must complete their fixed budget; training loss is descriptive and cannot establish held-out improvement.

## Evaluation and acceptance

Sixteen validation articles, h0 seeds5101/5202. Each uses128 input tokens and scores the last64 causal predictions: logits positions64..127 against original token indices65..128. Initial state must match byte-for-byte across arms for each article/seed. Report all160 case scores (32 F plus32 for each of4 trained adapters), top1 counts, per-article differences, both training-seed summaries and the worst article degradation. Save the scored FP32 logits externally for an independent FP64 stable-logsumexp audit.

Primary D-vs-F exploratory improvement screen: for EACH training seed, equal-article mean NLL averaged over the two h0 seeds must decrease by at least0.01 nats/token, and pooled top1 accuracy must not decrease by more than0.01 absolute (one percentage point). Both training seeds must pass. This threshold is a preregistered practical screen, not a significance level. Apply the same rule descriptively to S-vs-F; report D-vs-S without claiming parameter-matched identification. Mixed results or smaller gains do not pass the screen. No additional runs are chosen after seeing results.

The auditor also labels D-vs-S with these same margins as a secondary descriptive screen; it never replaces the primary D-vs-F screen. No unregistered aggregate can override a failed primary screen.

Engineering acceptance is separate: zero-adapter outputs are bitwise equal to native F32; exactly permitted parameters train; original state entries remain byte-identical; every expected depth bank is called and has finite gradient/update evidence (A's first-step zero gradient with zero B is expected); all losses/logits/gradients/checkpoints finite; all steps and evaluations accounted for; causal label alignment and split identities audited; final adapters reload in a fresh process and reproduce a fixed case bitwise; source/input/environment/custody records match. Any engineering FAIL/BLOCKED stops downstream computation without a retry and preserves evidence. A final scientific-screen FAIL is a valid negative result, to be sealed rather than tuned away.

## Runtime and evidence

Designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr only. Existing Python3.12.3/Torch2.11.0+cpu, CPUFP32,2 intra-op threads/1 inter-op, deterministic algorithms, no enabled autocast. Existing data/audit environment; no package installation. Admission requires3GiB available memory,2GiB free evidence disk and no competing experiment worker. Raw scored logits occupy about1.25GiB; preserve at least256MiB for records and finalization. Model worker timeout3600 seconds, no automatic retry. Development fixture tests and static reviews precede freeze; model results never justify editing the frozen runner.

Every phase records Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Git stores code, protocol, tests, review, public per-case metrics, training curves, manifests and checkpoint. Raw corpus, tensor logits and binary adapter/optimizer checkpoints remain in the designated external evidence directory with hashes. Upstream, original weights, all old evidence and existing environments remain intact. Internal agents cross-review; no external Claude/Grok approval is claimed.

Data preparation at916e87ace8aa080529c5d5ce84378b8a52b52fda passed, sealed atb879743591c27a40b039609084911cae2e0b8317. Inputs81885 bytes, SHA256b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc. Selected32 title/intro contexts were inspected before model freeze; no sample change. Public preparation evidence includes32 attributed180-character prose prefixes for that review, not full source rows or token vectors. These small curated passages are the explicit exception to public metadata-only export. Original acquisition JSON is valid; no normalized copy was created. Pre-model packaging-command errors are documented in PREPARATION_CHECKPOINT.md and caused no data/model rerun.

At completion seal the result and stop. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. The next instruction is chosen from the frozen comparisons; no automatic loop encoding or combined-mechanism experiment follows.

Primary sources: https://arxiv.org/abs/2106.09685 ; https://huggingface.co/datasets/Salesforce/wikitext/tree/6231e49f19a707241d6b84d9cff60a3a86b85a85/wikitext-2-raw-v1 . Depth indexing and this small training budget are OpenMythos research choices, not claims from these sources.
