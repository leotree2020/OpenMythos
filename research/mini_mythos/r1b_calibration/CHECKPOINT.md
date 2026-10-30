# R1-B-CAL — uploaded development result and scoped closure (2026-10-30)

**Uploaded JSON / record consistency PASS. GPT learning floor PASS; Parcae learning floor FAIL; task qualification FAIL / PARCAE_NOT_LEARNED_AT_FIXED_BUDGET.** User-run records contain six completed 3000-step arms and six development endpoints. Final test and extra-depth benefit remain NOT TESTED. This update is actual read-only record auditing, not another native run. The requested original JSON handoff is COMPLETE; do not request it again or rerun for sealing.

## 1. Purpose, source and evidence

Question: at one fixed budget, is strictly-three-digit addition both learnable by the existing native models and sufficiently below ceiling for a later compute-benefit comparison? This is task qualification, not architecture superiority, ACT or P3 completion.

- Repository leotree2020/OpenMythos; branch mini-mythos-r1b-difficulty-cpu-20261030; Draft PR #19, dependent on PR #18.
- Executed source **f13e498951e13d3a73db26e9111724b54984e35c**. Protocol frozen FIRST at **5b60718a1e6388a91ee9f00a811f41265b92b548**. Preparation checks and original checkpoint remain at executed commit; no protocol/runner/task/threshold change.
- Unchanged native source **69284c13746e849104f738d6d1a347b1f457df76**, original factory/pair_io SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967.
- Actual uploaded `result(3).json`: **1,546,502 bytes**, independently computed SHA256 **d87bb8be14573379ef2936b1c7f7b50aad5c0b9db0cf7724c67cb2aa1ae23a86**. No separately supplied user terminal hash; no invented digest match/authenticity claim.
- User-side output: `/workspaces/OpenMythos/mythos_evidence/r1b_calibration_v1/result.json`.
- Audit summary: [evidence/uploaded_json_audit_20261030.json](evidence/uploaded_json_audit_20261030.json), first committed at **120c2cabfbad444ee89e1084c9ae39d076c0c80d**.
- Actual earlier P1-R1 JSON SHA256 bf2b75fbcc49179cbdb059916a744ae8fa4cc682675bd802b662b32e791126ea was read only for six initial hash/input-embedding links; no initializer was run.
- Actual prepared task.py SHA2561baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af and run_cpu.py SHA25652e485d9f4f880e66ac21b49dbd5ebcf93ce600714066a9781607656eb9bac42 match this result. Frozen protocol and previous checkpoint were read through live GitHub; no independent raw-protocol-byte hashing is claimed.

## 2. Frozen inputs, environment and expected criteria

Operands100..999; six input digits, four reversed answer digits; answer-only training labels. Full256-way free greedy generation, no correct answer prefix or calculator. Train/development role hash keeps swapped pairs together; future-test reserved role is not model-evaluated here. One fixed final checkpoint per model/seed, no early/best checkpoint selection.

Train19977 ordered examples from10000 canonical pairs; development1024 canonical questions,256 each carry0/1/2/3. Development is equally stratified, NOT natural-frequency arithmetic accuracy and not directly comparable to R1-A's differently weighted test. Three seeds42/20261029/20261030; same per-seed batches;3000 steps/batch32, original AdamW;384000 supervised target exposures and864000 input positions per arm. Repeated exposures are not unique training examples.

Recorded producer: Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, FP32, one CPU thread. These are inspected environment records, not a live shell measurement. Auditor: Python3.13.5/torch2.10.0+cpu, Torch used ONLY for integer batch-index generation; zero model imports, binary loads, forward/backward or optimizer steps.

Learning floor, EACH seed in BOTH arms: overall>=80%, carry0>=90%, EACH carry group>=60%. Only after both learning floors pass does the classifier require EACH Parcae carry3<=90%. Learning failure precedes headroom failure. No mean-only gate, seed exclusion or threshold change.

## 3. Actual development endpoints

All values are complete-answer correct counts, not digit accuracy. All six models answer the SAME1024 unique questions;6144 answer instances are not6144 independent unique tasks. GPT uses its native four blocks; the shared d2 interface label is not GPT recursion.

| Arm | Seed | All /1024 | Carry0 /256 | Carry1 /256 | Carry2 /256 | Carry3 /256 |
|---|---:|---:|---:|---:|---:|---:|
|GPT|42|1009|255|252|251|251|
|GPT|20261029|979|246|251|241|241|
|GPT|20261030|1019|254|256|254|255|
|Parcae d2|42|807|213|196|189|209|
|Parcae d2|20261029|979|240|242|247|250|
|Parcae d2|20261030|978|249|238|247|244|

GPT mean overall97.8841%; Parcae mean overall89.9740%. Means cannot override per-seed acceptance.

**Direct failure:** Parcae seed42 overall807/1024=78.8086% and carry0 213/256=83.2031% miss80% and90%. Its carry3=81.6406% is inside the headroom interval, but that alone cannot qualify it. All its carry bins are above60%; do not describe it as unable to perform addition.

**Separate observed constraint:** other Parcae seeds meet the learning floor but carry3 scores250/256=97.6563% and244/256=95.3125% exceed90%. Thus no seed meets both readiness requirements. Because the frozen classifier stops on learning-floor failure, overall qualification remains **FAIL**, not relabelled BLOCKED. Upper-bound observations are retained without pretending a second formal branch ran.

All three Parcae carry3 scores exceed their carry2 scores; carry-count labels are not an empirically established monotonic model-difficulty scale. The broad seed42 performance reduction and across-seed endpoint variation do not isolate initialization, sample order, native stochastic states, or an architectural cause. These factors change jointly with seed. No statistical superiority/harm or causal dead-parameter claim follows.

## 4. Actual audit acceptance and boundaries

134 record/identity assertions PASS, zero failures. These are audit checks, not134 new neural experiments.

| Check | Actual result | Boundary |
|---|---|---|
| Original bytes and strict JSON; six seed/arm records | PASS | No external terminal digest/authenticity proof |
| Independent role/rank/data reconstruction | PASS |405450 candidate roles; no reserved labels or model-facing test generated; train/dev hashes equal |
| Grouped split isolation and exact counts | PASS |19977 train rows/10000 pairs;1024 unique development pairs |
| All6144 saved answers rescored | PASS | Every total/accuracy/invalid count agrees; no native inference |
|18000 loss and18000 norm values | PASS | Full3000 per arm, finite nonnegative records; not raw gradients |
| Three3000x32 integer batch tensors | PASS | Regenerated; both arms' hashes agree |
| Initial hashes/input fingerprints and paired metadata | PASS | Linked to original P1-R1 records, not raw state binaries |
| Saved counts/ratios/classifier/exit code | PASS | Arithmetic and exact frozen logic only |
| Six new model/AdamW/RNG .pt files | NOT TESTED | Not uploaded; hash fields do not substitute for loading files |
| Native score/profiler/training replay, resume equality | NOT TESTED | No model execution in this audit |
| Final test and depth4 benefit | NOT TESTED | Intentionally outside the executed stage |
| New Grok/Claude independent review | NOT TESTED / DEFERRED | No actual report exists here |

Saved per-step training counts: GPT73,433,088; Parcae80,289,792; ratio1.09337349 (~+9.34%). Registered parameter ratio1.08501594. These meet the frozen10% margins, not identical budgets, effective capacity or hardware costs. Parcae probe again records51904 participating of60224 registered parameters; known8320 inactive paths unchanged. This audit did not run that probe or establish that it caused the lower seed42 outcome.

## 5. Stage decision and single next action

Close the requested raw-JSON handoff and record audit. End THIS frozen candidate with task qualification FAIL. Do not request the same file again, retrain for sealing, choose only passing seeds, average away failures, pick an earlier checkpoint, extend the budget, open reserved test, try depth4/8/16, or increase operand digits automatically.

**Next limited action:** targeted cross-review of the already-existing result/protocol and saved error distributions, focusing on (a) the exact seed42 learning-floor failures, (b) upper-bound failures in the other seeds, and (c) whether carry-count labels provide the task sensitivity needed. Do not repeat initialization/archive work or run new training. Any later causal diagnosis must have one controlled variable and its own preregistered stopping rule; this checkpoint authorizes no new experiment.

Conversation audit bundle contains exact original input, prior initial-hash reference, actual audit code/log/results, full development mistakes, Chinese stage report, review instructions and manifest. Error analysis is descriptive development evidence, never a new final test or retroactive acceptance rule.

Keep PR19 Draft/unmerged. Preserve R1-A learning PASS/ceiling result, all M2 scientific negatives, A-M2L-01 and Claude initialization root-cause OPEN. This update changes documentation/evidence only. Original code/protocol, upstream Parcae, J1, Bench, R3 and model architecture remain unchanged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, GPU or automatic merge.
