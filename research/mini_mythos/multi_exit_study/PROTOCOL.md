# MES-1 v1 — new-seed multi-exit confirmation

2026-10-31. Implements phase ONE of the user-approved Mythos MES plan, not a new task search. Base PR20 commit 4cf60b053c7b9c2e89e64646cd986d33a34a7657. Old A primary FAIL and all old evidence remain unchanged. This protocol is preregistered before any MES-1 model results. Targeted independent pre-training review is pending; registration is not a claim that review or formal acceptance passed.

## Fixed experiment

Seeds: 101,202,303,404,505. Four arms, twenty training trajectories: GPT (native four blocks), P2 (Parcae [0,2], final-only), P4 (Parcae [0,4], final-only), A (Parcae [0,4], SAME-trajectory 0.25 CE(exit2)+0.75 CE(exit4), shared suffix). Reuse unchanged MECH-AB Mechanism; no B/C/D/E, optimizer changes, inactive-path repair, new architecture, weight sweep or best-checkpoint selection.

Native pin sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76; original factory/pair_io and R1-B task are immutable. Same per-seed original paired starts and training pool. AdamW lr0.002, betas(0.9,0.999), eps1e-8, decay0, gradient clipping1. Batch32; FP32; Linux Python3.12.3, torch2.11.0+cpu, numpy1.26.4, einops0.8.0; CPU one thread, deterministic math SDPA. No installs, downloads, GPU, cache, compilation or activation checkpointing.

## Budget before training

Preparation actually probes forward/backward at batch32,length9 with all five seeds, without optimizer updates. Require supported-op step counts GPT73433088,P2=80289792,P4=114130944,A145428480; drift blocks before training rather than silently altering this recipe. Common budget F=3000*A_step=436285440000. Steps floor(F/step): GPT5941,P2=5433,P4=3822,A3000. All budgets must be <=F with unused fraction<=0.001. Auxiliary readout/backward is included; optimizer/unsupported operators are not. These are equal COUNTED budgets, not equal hardware costs.

Construct one max-length batch-index sequence per seed (seed+12000); every arm consumes its prefix. Same-data/updates comparison uses the fixed P4 step3000 snapshot and A3000. Equal-budget main comparison uses budget endpoints. Cheaper arms see more repeated examples; do not claim simultaneous equal-token matching. Save all arms at step3000 and budget end (deduplicate A), model+AdamW+CPU RNG+batch indices, source/data identities. No evaluation at intermediate steps, no checkpoint selection. Parcae RNG prefix pairing is checked; GPT consumes RNG differently and is only seed-matched.

## Holdouts and evaluation barrier

Reuse original R1-B training data only, not its old qualification gate. Select canonical a<=b from the original reserved role (100..999). Rank within outgoing-carry strata by SHA256('MYTHOS-MES1-HOLDOUT-V1:{a}:{b}'). Per stratum first512 -> H1, next256 -> HC, next512 -> H2; deterministic orientation SHA256('MYTHOS-MES1-ORDER-V1:{a}:{b}'). H1=2048,HC=1024,H2=2048. Preparation stores allocation digests/counts only; no model-facing holdout labels or scores. HC/H2 are never materialized/evaluated by this stage. Carry count is a sampling stratum, not an assumed difficulty ordering. All three subsets are mutually disjoint and outside old train/development roles.

Only after all twenty trajectories complete and identities/pairing pass may evaluation materialize H1. H1 is inference/scoring-only, never an optimizer input. Evaluate final GPT@4,P2@2,P4@2/4,A@2/4 plus P4 step3000@2/4: forty conditions, same2048 questions. Free full256-way four-token generation from six prompt digits; teacher-forced CE separate. Record predictions, category accuracies, correction/corruption, full-generation counted FLOPs and descriptive times. No early stopping on model quality; valid numerical training failure is FAIL, source/environment/evidence error BLOCKED. Preserve partial output; no automatic retry, resume, delete or retuning.

## Independent decisions

PRIMARY: equal-budget A@4 minus P4@4 on H1, mean accuracy gain>=0.01 AND every seed gain>=-0.01. P4 mean>0.99 -> BLOCKED/CEILING, report all regressions. Same-update A3000-P4@3000 is secondary. Engineering quality safeguards versus GPT@4 and P2@2 separately: mean and every paired loss<=0.01 (A@4/GPT, A@2/P2); no statistical noninferiority claim. A depth benefit: mean A@4-A@2>=0.01, every seed strictly improves, each carry0 loss<=0.01; mean A@2>0.99 -> ceiling. These do not replace primary status.

Predeclared paired crossed bootstrap: 5000 replicates, private seed731031; resample five seeds and H1 questions within each of four strata, retaining identical sampled indices across methods and across repeated seed evaluations. Report percentile95% interval for primary mean difference, diagnostic only; five-seed population uncertainty remains large. PASS is an engineering screen, not a universal superiority or formal statistical claim.

## Execution and review boundary

Commands prepare/train/evaluate are separate. prepare never trains or opens H1. Before train, supply an actual focused review report plus explicit owner acknowledgement; record its bytes/hash/reviewer designation as user-supplied evidence, not verified identity or fabricated Grok PASS. Review scope: new budget/seed handling, P2/GPT routes, snapshot barriers, reserved split, bootstrap, immutable A behavior. Existing completed phase is read-only. Evaluation loads only this run's hash-bound safe state_dict snapshots; original-source changes block continuation.

Native compatibility/probes run before updates; full local fixture tests are not native acceptance. First complete H1 evaluation closes MES-1; no automatic subtraction task, stopping controller, new ranks/weights/depths, or hyperparameter search. Second-task MES-2 and inference-exit MES-3 remain NOT IMPLEMENTED/NOT TESTED here. Keep Draft/unmerged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL/J1/Bench/R3 or upstream changes.
