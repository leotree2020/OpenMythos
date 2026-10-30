# R1-A v1 — arithmetic capability before another architecture claim

Frozen: 2026-10-30, before native training. Base 36c21aaf245b4ed8999d2a6d070948e231605676 (PR17). This is a NEW task after the user's goal-aligned continuation authorization. Initialization reconstruction is closed at its recorded scope; do not repeat it. Preserve M2-L/D/T negative results and A-M2L-01/02 limits.

## Question and scope

Can the existing official GPT baseline learn held-out two-digit addition, and does extra inference computation improve the SAME trained Parcae on carry-chain problems? Report exact whole-answer accuracy, difficulty and actual supported-operator counts, not just NLL. This is an elementary algorithmic capability pilot, NOT P3 completion, general reasoning, ACT, dynamic stopping, memory, or evidence of hardware efficiency.

Task design reference: karpathy/minGPT@37baab71b9abea1b76ab957409a1cc2fbfba8a26, projects/adder/adder.py (blob55f03ee1caf4290e86f5ce02570553a87caeee23). Retain its fixed-width concatenated operands, reversed fixed-width sum and answer-only next-token loss. Our independent generator changes the split to keep commutative pairs together, adds carry strata, and uses the existing native GPT/Parcae models instead of minGPT's model. This is an adaptation, not reproduction of minGPT results. No new external code dependency or download. Standard Python integer addition is ONLY the label/scoring reference, never the model's prediction.

## Fixed data contract

- a,b are integers 0..99. Prompt = two zero-padded digits of a followed by two of b. Target = reversed three-digit zero-padded a+b. Example 58+67: prompt `5867`, target `521`, decoded answer125. Digit token IDs0..9; retain the original256-way model vocabulary. No constrained decoding: non-digit tokens count wrong.
- Training full sequence length7, shifted input/label length6. First3 target positions masked with -100; exactly3 supervised answer tokens. Generation receives ONLY4 prompt tokens, greedily generates exactly3 tokens, without ground-truth prefixes, calculator/tool calls, caching or early stopping.
- Carry category is the number of outgoing decimal carries across the two operand columns:0 (none),1 (one),2 (successive carries; hard). All categories have identical prompt/output lengths.
- Enumerate all5050 unordered pairs a<=b. Stratify by category. Sort each category by SHA256 of UTF-8 `MYTHOS-R1A-SPLIT-V1:a:b`; first floor(70%*n) train, next floor(15%*n) validation, remainder test. Both operand orders of a!=b are train members if in train; validation/test use ONE deterministic order selected by low bit of the first digest byte of `MYTHOS-R1A-ORDER-V1:a:b`. Thus swapped duplicates cannot cross splits and are not counted as independent test cases. Never change assignments after results.
- Verify every label with independent column arithmetic; assert split disjointness, exhaustive canonical coverage, exact encoding/decoding and masking. Persist split identities/counts and test per-problem predictions. No Shakespeare, Alice, old trained weights, or external corpus.

## Native models and one bounded CPU run

Unchanged sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Reuse exact `m2_matched/experiment.py` factory SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967 and pair_io: GPT FFN60/four blocks; Parcae FFN64/prelude1/core1/coda1, native [0,2]. Context32/vocab256/width32 unchanged. No monkeypatch, removed tensors or corrected layer indexing. The known8,320 inactive parameters remain; GPT-versus-Parcae is a practical reference, NOT a clean causal test of weight sharing or equal active capacity.

Three seeds42,20261029,20261030. Original Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0; FP32, math SDPA, single thread. Construct native pair and apply original IO pairing; do not import or rerun either initialization-replay tool.

Each model: exactly3000 AdamW updates, batch32, lr0.002, betas(0.9,0.999), eps1e-8, weight_decay0, grad clipping1.0. No schedule/early-stop/best-checkpoint selection. Per arm/seed:96000 sampled problems,288000 supervised answer-token exposures,576000 input-token positions. These are repeated exposures, not unique training examples. Batch selection uses a CPU generator seeded seed+11000; identical batches for paired arms. Model training RNG uses seed+2000.

Before training, count forward/backward at the ACTUAL task shape (batch32,length6), record total and gradient-participating parameter counts. Require total-parameter and counted-training-FLOP max/min<=1.10. This is approximate registered/countable budget matching, not equal hardware costs or active capacity. If not matched, stop without tuning FFN/depth. The total parameter counts remain65344/60224. Save final model/optimizer/RNG, actual losses/norms, hashes, source/environment and walltime labelled descriptive.

## Execution order, learning gates and test access

1. Generate/freeze data and verify structural tests. Source pin and output no-overwrite checks.
2. Construct/record all six initial states; perform native masked-loss/CE alignment and budget probes without optimizer updates. No arithmetic learning result yet.
3. Train the three GPT controls once to fixed3000 steps. Evaluate validation only, with free greedy generation. GPT task-learnability PASS requires EACH seed overall exact accuracy>=95% AND EACH carry category>=90%. If this fails: execution of completed controls recorded; baseline_learning FAIL; Parcae training and all test metrics NOT TESTED; primary benefit BLOCKED. Stop, do not automatically add steps or retune.
4. Only if GPT gate passes, train three Parcae models from their saved paired initial states for the same budget. Depth2 validation floor: EACH seed overall>=90%, EACH category>=80%. If it fails: Parcae learning FAIL; test unexamined, primary BLOCKED. Stop rather than interpreting an unlearned model's depth extrapolation.
5. Only after all six finish and both learning gates pass, evaluate the single fixed FINAL checkpoint on test: GPT native once, Parcae at depths2 and4. Same batches and model-independent seeded RNG per seed/batch, reset for each depth. No test-driven checkpoint, retraining or selection. Persist predictions for every test problem. Count the complete greedy3-step forward workload (including repeated prefix recomputation and last partial batch); do not confuse it with one forward or training FLOPs.

## Prespecified scientific decision

Primary: on hard(category2) TEST, delta=accuracy(Parcae depth4)-accuracy(same Parcae depth2). PASS only if mean paired delta>=0.05 (5 percentage points), every seed delta>0, and easy(category0) accuracy declines by no more than0.01 in each seed. All three conditions required. If mean hard d2 accuracy>0.95, maximum possible mean gain is<0.05: predeclared CEILING LIMIT, primary BLOCKED / insufficient headroom, not a benefit PASS or a claim that recursion is impossible. No alternate depth or endpoint may replace primary.

Report GPT test exact accuracy and d2 Parcae-vs-GPT per category descriptively; no post-hoc superiority/noninferiority gate. Report additional counted inference cost and accuracy gained per cost descriptively. A primary PASS would only justify a separately reviewed harder-task follow-up, NOT overall efficiency/P3 success. A primary FAIL ends THIS task/configuration/hypothesis. No automatic3/4-digit extension,16/32-depth search, longer training, patch or GPU allocation.

Statuses separated: execution, data, budget, baseline_learning, parcae_learning, primary_benefit, review. Environment/source/input/unfinished execution BLOCKED; completed learning criterion failure FAIL; unrun sections NOT TESTED. Exit0=primary PASS;1=completed scientific/learning failure;2=operational block or prespecified ceiling. Partial results persist; existing directory is read only, not retrained or deleted.

## Deliverables and reviewer

One branch/PR only: protocol, task/runner/tests/launcher, checkpoint. Raw run: result.json, per-problem predictions in that JSON, six final states if all arms run, per-stage progress, dependencies. Record actual environment and code HEAD, keep results separate from source. Grok/Claude cross-review NOT TESTED/DEFERRED until a real report exists. Independent reviewer focuses on grouped splits, target masking, free generation, predeclared gates and cost scope, not another initializer audit. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, J1/Bench/R3 edits or auto-merge.
