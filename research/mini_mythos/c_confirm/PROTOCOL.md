# C1 — phase-specific adapters: bounded equal-count confirmation

Protocol V1, 2026-10-31. Experiment `MYTHOS-C1-EQUAL-COUNT-HOLDOUT-V1`.
Status: PRE-REGISTERED IMPLEMENTATION TARGET; independent Claude Code review PENDING; native preparation/training/quality NOT TESTED. This is not formal Oracle acceptance.

## 1. Decision and lineage

Owner authorized starting C after MES-1. Preserve all earlier results and criteria. MECH-C's exploratory C4>S16 and C4>P4 screens do not prove fresh-data/equal-compute benefit; MES-1's A failures do not imply C succeeds. Use PR21 base `b16f7971f854a9c3bf68f3c24bb2cc6bac9ac31c`; unchanged C implementation from executed `38a6f1dcbbf04ab823686aff9c4e6c4acddc0ad0`. Upstream remains read-only `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`. No edits outside the new c_confirm directory, no A/B/D/E combination, inactive-path repair, rank/lr/seed search, GPU, G2 REAL or automatic merge.

Main question: does the EXISTING fixed C4 recipe improve native P4 when both have the same supported-operator training budget? GPT is the external reference. This new primary question does not retroactively change MECH-C's old C4-S16 primary.

## 2. Fixed arms and controls

Three arms: GPT, P4, C4. Five new seeds: 1101,1202,1303,1404,1505. All train from scratch; no warm start or selecting old good seeds. Fifteen trajectories maximum.

GPT: original matched factory, FFN60, four native blocks. P4: original Parcae configuration and initialization, explicit [0,4] unroll, final-only CE. C4: same Parcae plus unchanged LoopLoRA C4 (four independent rank4 corrections at core attention-output32->32 and FFN-output64->32). Scale1, zero up factors, seed+31000 private adapter RNG. All backbone and adapter parameters trained. Total parameters GPT65344/P4=60224/C4=62784. Known 8320 inactive Parcae parameters are NOT silently fixed. C4 vs P4 is not parameter-matched and does not isolate phase specificity from added capacity. S16 is NOT trained in this confirmation; its earlier interpretation remains separate.

Shared factory and pair_io recipe; P4/C4 base weights exactly matched within each seed. Adapter construction must preserve global RNG. Data/batch32/AdamW(lr.002,betas(.9,.999),eps1e-8,weight_decay0)/clip1 remain unchanged. Seed+12000 generates common batch-index prefixes; seed+2000 begins training stochastic state. P4/C4 training RNG prefixes must agree through their common steps. GPT is seed-matched, not claimed identical RNG consumption.

## 3. Budget and checkpoints

Ceiling is existing C4 cost at3000 updates:355663872000 counted FLOPs per arm/seed. Expected actual-shape (batch32,sequence9) step counts: GPT73433088/P4=114130944/C4=118554624. Before training measure all arms/all seeds; disagreement is BLOCKED, not automatic rebudgeting.

Frozen steps: GPT4843/P4=3116/C4=3000; floor allocation with <=0.1% unused budget. Counters include adapter matmuls, not optimizer/all elementwise/hardware work. Equal counted budget is not equal token/sample exposure. Report parameter counts, total counts, actual walltimes and worker-lifetime RSS separately; no hardware speedup inference.

Save every final state and P4 at step3000:20 full wrapper/model+adapter/AdamW/CPU-RNG/batch-index snapshots. Same-update comparison uses the PREDECLARED P4 step3000, not a selected checkpoint. Safe reload is not interrupt-resume equivalence.

## 4. Data and no-holdout-before-training rule

Reuse fixed R1-B three-digit addition training rows:19977 ordered examples/10000 canonical pairs, no change to tokenizer/answer format. Old development is not a new test.

Reconstruct existing MES-1 reserved allocations with its original rank namespace `MYTHOS-MES1-HOLDOUT-V1`, quotas H1=512/HC=256/H2=512 per carry stratum, and verify their declared allocation digests. Exclude ALL5120 canonical keys, including the already-viewed H1 and untouched HC/H2. Do not materialize HC/H2 answer labels.

From remaining reserved-role canonical pairs a<=b, rank by SHA256(`MYTHOS-C1-HOLDOUT-V1:{a}:{b}`), take512 per outgoing-carry stratum0..3. C1T has2048 distinct questions. Orientation from SHA256(`MYTHOS-C1-ORDER-V1:{a}:{b}`) first-byte parity. Reverse operand pairs cannot leak across sets. These deterministic choices precede any C1 model score. No sampling based on model errors/headroom.

Prepare records only allocation identities, training data and no-update probes. Train never generates C1T targets or evaluates holdouts. Only after ALL15 complete trajectories and snapshot/pairing checks pass may evaluate generate C1T and score final snapshots. Each evaluation worker reads exact C1T bytes once, verifies their file and object hashes against the parent binding, and scores that in-memory object; no hash-check/reopen race. Parent checks unchanged bytes after evaluation. HC/H2 remain unscored. Viewed C1T cannot be reused as a fresh test after tuning.

Evaluation: full autoregressive four-digit answer generation from the six-digit prompt only; teacher-forced answer NLL reported separately. Depth4 only, no new early-exit/depth extrapolation claim. Twenty conditions:15 final plus5 P4@3000.40960 saved answers are repeated measures on2048 questions, not independent new questions.

## 5. Predeclared engineering decisions

Primary `equal_budget_C4_P4`: mean paired full-answer accuracy gain>=.01 and every seed delta>=-.01. Reference mean>.99 yields ceiling BLOCKED; actual regressions still reported. Secondary `same_updates_C4_P4`: same rule using P4@3000. External `GPT_safeguard`: C4-GPT mean>=-.01 and every seed>=-.01. These are engineering screens, NOT statistical superiority/noninferiority.

Candidate selection requires BOTH primary PASS and GPT safeguard PASS. A FAIL in either gives selection FAIL; otherwise any BLOCKED gives selection BLOCKED. CLI prints every screen and uses selection exit0/1/2; execution completion is separately PASS. Same-update result is secondary and cannot rescue primary failure. A numerical model failure is FAIL; invalid environment/input/source/missing evidence is BLOCKED. No thresholds changed after observing scores.

Report per-seed counts, means/worst/sample-standard-deviation, carry-stratified scores, saved invalid answers, cost and correctness differences. Optional predeclared5000-draw paired crossed percentile bootstrap with seed731031 resamples seeds and stratified questions jointly across methods; diagnostic only, five seeds remain a limitation.

## 6. Execution and review

Reuse installed Linux Python3.12.3/torch2.11.0+cpu/numpy1.26.4/einops0.8.0, CPU FP32 one thread. Do not install or waive production dependencies. Local mathematical fixtures must remain labelled fixtures.

Three separate phases prepare/train/evaluate. Train requires actual Claude Code report plus owner's acknowledgement and binds review bytes/source identity; a nonempty file alone is not authenticated review. Grok reviewer role is superseded by owner; no extra Grok dependency. Existing MES review is not C1 approval.

Existing complete, blocked or partial output must never be overwritten/restarted automatically. Duplicate worker failures must not rewrite another worker's row or logs. No direct manual workers, source-identity bypass or old-result reuse. Changed source requires explicitly separate evidence, not relabelled preparation.

Finish each phase with recorded purpose, environment, inputs, expected/actual result, status and next instruction. Preserve checkpoints and failures. Formal Oracle stays BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False. Native CPU component PASS is not research-quality PASS. Post-result Claude review required before promoting a candidate. Current authorization covers this bounded development/CPU workflow, not GPU/scale training or later mechanisms.
