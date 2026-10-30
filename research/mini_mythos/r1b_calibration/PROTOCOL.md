# R1-B-CAL v1: bounded development-only difficulty qualification

Frozen 2026-10-30 BEFORE any native R1-B training. Base PR18 at 84b594c3c96df5255eeb5312a3b281b4e4ea8bac. User explicitly authorized continuation after the R1-A ceiling result. This is a new task-design stage, not a rerun or change to R1-A acceptance.

## Decision and question

R1-A arithmetic learning passed, but its hard depth2 test mean was 97.8723%, leaving less than the preregistered 5 percentage-point improvement. Preserve that BLOCKED/CEILING_LIMIT and observed depth4 declines. Do not rescore the old test into a new success or choose its errors as new training data.

One candidate only: can the SAME original small GPT/Parcae configuration learn **strictly three-digit addition** at one fixed budget, while Parcae retains useful headroom on three-carry development problems? This stage measures only native GPT and Parcae depth2. No depth4 calls, benefit comparison, final-test prediction, hyperparameter search or new model architecture. A qualification PASS is task readiness, NOT reasoning/efficiency superiority.

## New data and held-out reservation

- Operands are integers 100..999 inclusive. Their numerical pairs are disjoint from all R1-A 0..99 pairs. This is newly trained in-distribution arithmetic, NOT two-to-three-digit length generalization.
- Prompt: six concatenated operand digits. Answer: reversed four-digit, zero-padded sum. Example 578+677=1255: prompt578677, target5521. Full sequence10; shifted model input9; first5 labels=-100; exactly4 supervised answer tokens.
- Digit IDs0..9; retain original vocab256, context32. Full256-way greedy generation of4 tokens from ONLY the6 operand tokens. Non-digit outputs are incorrect. No calculator, answer prefix, cache or hidden label at prediction time.
- Enumerate405450 canonical pairs a<=b. Carry stratum is the number of outgoing decimal carries over three columns (0,1,2,3); stratum3 is the three-successive-carry group. Both operand orders share a canonical identity and role.
- Role hash: SHA256 of UTF-8 `MYTHOS-R1B-ROLE-V1:a:b`; unsigned big-endian first8 bytes modulo100. Values0..69=train,70..84=development,85..99=RESERVED_FUTURE_TEST. The reservation rule is public and deterministic, not cryptographic secrecy.
- Within each stratum/role, rank by full digest of `MYTHOS-R1B-RANK-V1:a:b`, then a,b. Select exactly2500 canonical training pairs and256 development pairs PER stratum. Training includes both orders for unequal operands. Development uses one order, swapped iff the first byte of SHA256(`MYTHOS-R1B-ORDER-V1:a:b`) is odd.
- Thus training has10000 canonical pairs (at most20000 ordered examples); development1024 unique pairs,256 per stratum. Balanced development measures strata equally, NOT natural-frequency overall accuracy. Do not compare its percentage directly to R1-A's differently weighted test.
- Reserved-role pairs are never materialized as a task split, fed to a model, scored or selected by accuracy in this stage. Generator returns train/development ONLY. A future test must be selected from the untouched reserved role and frozen BEFORE its own comparison runs. No final test is opened automatically on qualification PASS.
- Record exact manifests/hashes; check integer sums against independent column arithmetic, swapped-pair separation and encoding/mask alignment. Selecting only a subset is deliberate; unused train/development-role pairs are not test data.

## Native models, budget, environment

Untouched sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76; reuse existing m2_matched/experiment.py factory SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967 and original pair_io. GPT FFN60/four blocks, Parcae FFN64/prelude1/core1/coda1 trained/evaluated with [0,2]. Width32/context32/vocab256 unchanged. A-M2L-01 inactive paths stay disclosed; no relayering/patch or equal-active-capacity claim. Reuse established initial recipe without rerunning INIT-01/P1-R1 tools or reading old trained weights.

Seeds42,20261029,20261030. Existing Linux Python3.12.3, torch2.11.0+cpu, NumPy1.26.4, einops0.8.0; FP32 CPU, one thread, deterministic algorithms, math SDPA. No GPU, dependency/corpus downloads or version waiver.

Exactly3000 AdamW updates per executed arm, batch32, lr0.002, betas(0.9,0.999), eps1e-8, weight_decay0, max gradient norm1. Same per-seed sampled training batches between GPT and Parcae; batch generator seed+12000, training RNG seed+2000. 96000 problem exposures,384000 supervised answer-token exposures,864000 input-token positions per arm. Larger sequence cost is explicit; NOT equal total work to the old two-digit experiment.

Before learning, measure native masked-CE equivalence and supported forward/backward FLOPs at ACTUAL shape32x9. Require registered parameter and counted-training-FLOP max/min ratios<=1.10; otherwise BLOCKED with no retuning. Counts exclude optimizer/hardware costs. Save final model/AdamW/CPU RNG and full batch indices, traces, source identities, dependency record and descriptive walltime. No intermediate model selection or checkpoint sweep; only the fixed step3000 endpoint is scored.

## Frozen qualification and stopping

These thresholds are design choices for an informative follow-up task, not claims about general capability and not replacements for R1-A thresholds.

1. Train all three GPT controls first. Native GPT validation/development exact-answer accuracy must be >=80% overall, >=90% on carry0, and >=60% in EACH carry stratum, for EACH seed. Failure: completed learning gate FAIL; qualification FAIL/GPT_NOT_LEARNED_AT_FIXED_BUDGET; Parcae training NOT TESTED; stop.
2. Only if GPT controls pass, train three Parcae models from their original paired initial states at the same fixed budget. Apply the SAME learning floor to each Parcae seed. Failure: learning FAIL; qualification FAIL/PARCAE_NOT_LEARNED_AT_FIXED_BUDGET; stop.
3. If both learn, qualification additionally requires EACH Parcae seed's carry3 development exact accuracy <=90% (and >=60% from the learning floor). This leaves at least10pp point-estimate headroom per seed. Above90%: qualification BLOCKED/DEVELOPMENT_CEILING; do not secretly shorten training or select a different checkpoint. No confidence-interval or statistical generalization guarantee is implied by this window.
4. If all pass, task_qualification_status PASS, final_test_status NOT TESTED, extra_depth_benefit_status NOT TESTED. Stop anyway. Subsequent evaluation requires its own decision and review; it may still encounter held-out ceiling or show no extra-depth benefit.

Single candidate, maximum6x3000 updates. No budget extension, alternative lengths, depth sweep, task resampling, seed selection or automated retries. Failed learnability says THIS task/configuration/budget did not qualify, not that the task is impossible. Both success and failure are valid completed development measurements.

Statuses separate execution/data/budget/GPT learning/Parcae learning/task qualification/final test/review. Missing environment/evidence or execution error -> BLOCKED with saved error. Completed learning-floor failure -> FAIL; completed headroom failure -> BLOCKED. Exit0=qualification PASS,1=completed learning-floor FAIL,2=BLOCKED (read reason to distinguish ceiling from operational error). Existing outputs are read-only; partial outputs are preserved, never resumed/retrained automatically.

## Delivery, review and unchanged boundaries

One isolated branch, task, runner, launcher, tests and checkpoint. Model-free local tests are not native training PASS. New output mythos_evidence/r1b_calibration_v1/result.json plus train/development data and executed final checkpoints. Do not ask for already-audited R1-A/P1-R1/M2-T JSONs again.

R1-A targeted independent review remains NOT TESTED/DEFERRED; do not falsely mark it passed. New calibration preparation/execution is exploratory and does not promote prior claims. Grok/Claude review of this stage requires a real report; focus on reserved-role exclusion, prompt-only prediction, exact stop rules and task-selection boundaries. Keep Draft, no automatic merge.

M2-L/D/T negatives, R1-A ceiling result, A-M2L-01 and the separate Claude initialization root-cause OPEN stay intact. Upstream Parcae, J1, Bench, R3 and model architecture remain unchanged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL.
