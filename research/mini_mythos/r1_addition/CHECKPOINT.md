# R1-A — uploaded-result audit and capability checkpoint (2026-10-30)

**Original JSON and recorded-data consistency: PASS. GPT and Parcae validation learnability: PASS. Primary extra-inference-depth benefit: BLOCKED / CEILING_LIMIT, not PASS or reclassified FAIL.** The user-run experiment reports all six training arms and nine test conditions complete. This update actually reads the original uploaded JSON and rescores every saved answer; it is not another native model run. The requested result handoff is COMPLETE: do not ask for the same JSON again or rerun for sealing.

## 1. Purpose, sources and evidence identity

Purpose: establish an elementary exact-answer capability baseline, then assess whether more inference computation helps the SAME trained Parcae on consecutive-carry two-digit addition. Not general reasoning, ACT, dynamic stopping, P3 acceptance or hardware efficiency.

- Repository leotree2020/OpenMythos, branch mini-mythos-r1a-carry-addition-cpu-20261030, Draft PR #18; base 36c21aaf245b4ed8999d2a6d070948e231605676.
- Executed source **936c52cf6036232de3fd9d034c4366d81c17dbea**. Protocol frozen first at **82b70032423d7a87b6109ab2dc5b75470635cee5**. Prior preparation checks and original checkpoint remain in that Git history; no protocol, task, runner or thresholds changed by this update.
- Untouched native GPT/Parcae pin **69284c13746e849104f738d6d1a347b1f457df76**; original factory/pair_io reused. No model patch or repair of known inactive parameters.
- Task-format inspiration: minGPT projects/adder at37baab71b9abea1b76ab957409a1cc2fbfba8a26. Independent grouped-split adaptation, not a minGPT performance replication.
- Actual upload `result(2).json`: **1,899,747 bytes**, independently computed SHA256 **13bfccd565fd4ccb57c28bb901fc61f99dd55fe0a4ba378706880159b11e30cb**; input unchanged. No separate prior user terminal digest was supplied, so do not invent a match to one or call this independent authenticity proof.
- User-side output: /workspaces/OpenMythos/mythos_evidence/r1_addition_v1/result.json.
- Audit summary: [evidence/uploaded_json_audit_20261030.json](evidence/uploaded_json_audit_20261030.json), first saved at32934c230c7118ffd30930017f0be7a4b1dae1f4.
- Conversation bundle Mythos_R1A_Result_Audit_20261030.zip, SHA256 **929ac8deef70d6cc0e039a7f78ab47e62516253f00840fe9c358a9f33463b169**. Contains exact uploaded bytes, prior P1-R1 JSON, actual audit script/log/results, per-condition mistakes, Chinese report and manifest.

## 2. Frozen inputs/environment and expected results

Operands0..99, all5050 canonical unordered pairs grouped by carry0/1/2 then fixed hash-split. Swapped operands cannot cross partitions. Train6993 ordered examples from3534 canonical pairs; validation756 unique pairs; test760 unique pairs (carry0/1/2:230/342/188). Fixed-width4-digit prompt, reversed3-digit answer. Generation receives only operands and greedily emits three tokens from the full256-token vocabulary; invalid tokens count wrong. Test scores are from fixed final checkpoints, never best-checkpoint selection.

Three seeds42/20261029/20261030, two original native models, 3000 AdamW steps/batch32. Each arm/seed has96000 problem exposures,288000 supervised answer tokens,576000 input token positions. Recorded producer: Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0, FP32 CPU one thread. These are recorded environment values, not a new live Codespaces measurement.

Expected gates: GPT validation EACH seed overall>=.95 and EACH carry group>=.90; then Parcae validation EACH seed overall>=.90 and each group>=.80. Only after both gates do final tests run. Primary hard-test d4−d2 mean>=.05, every seed positive, easy loss<=.01 each. Predeclared mean hard d2>.95 takes precedence as CEILING_LIMIT/BLOCKED. Preserve this rule even when observed d4 results decrease.

## 3. Actual artifact checks

Auditor Python3.13.5; torch2.10.0+cpu used ONLY for integer batch-index regeneration. No native model imports, forward/backward, optimizer steps, profiler or model-binary loading. Local audit-script summary assembly initially had a variable-shadowing error, fixed before the successful read-only audit; this did not change input or any experiment criterion. Details are in the audit bundle.

165 record assertions PASS,0 failures; not165 neural experiments:

| Audit item | Status | Boundary |
|---|---|---|
| Original bytes, strict JSON, exact six seed/arm records | PASS | No separate external terminal digest/authenticity claim |
| Independently regenerated canonical splits and all three manifest hashes | PASS | Grouped train/val/test disjoint,5050 canonical coverage |
| All10000 ordered labels and shifted answer-only mask specification | PASS | Task reconstruction, not fresh native CE evaluation |
| All11376 saved full-answer predictions rescored | PASS | 4536 validation,6840 test; all totals/accuracies/invalid counts match |
| Recorded loss/norm traces | PASS | 18000 finite losses +18000 finite gradient norms;3000 per arm |
| Training indices and paired hashes | PASS | Three3000x32 integer tensors regenerated, both arms match |
| Initial-state/IO identities vs actual old P1-R1 JSON | PASS | Recorded hash linkage; no initialization rerun/raw tensor check |
| Budget and full-generation cost arithmetic | PASS | Saved supported-operator counters, not hardware cost or new profiler |
| Learning gates, ceiling precedence and exit code | PASS for classification | Primary benefit itself remains BLOCKED |
| Six new model/AdamW/CPU-RNG .pt files | NOT TESTED | Not uploaded; digest fields are not binary audits |
| Native score replay, full training replay and resume equality | NOT TESTED | No model execution by auditor |
| New Grok/Claude cross-review | NOT TESTED / DEFERRED | No report fabricated |

Pinned protocol/task/runner were read through the live GitHub connector. Direct local raw-file download failed DNS; independent raw-source-byte hash verification is NOT claimed. JSON state/profiler labels do not prove every operation was independently observed.

## 4. Actual capability and extra-depth results

| Mean test full-answer accuracy | All | No carry | One carry | Two carries |
|---|---:|---:|---:|---:|
|GPT native four blocks|98.0263%|99.2754%|99.0253%|94.6809%|
|Parcae d2|98.4211%|98.4058%|98.7329%|97.8723%|
|Same Parcae d4|97.2807%|96.9565%|97.7583%|96.8085%|

GPT JSON test key2 is only the shared evaluation-interface label; it is not a two-block or recursive GPT. All seeds use the same760 unique test pairs; do not call2280 seed-problem evaluations independent questions.

The GPT validation gate and Parcae validation gate recompute PASS. Descriptive Parcae d2 versus GPT mean overall advantage is+0.3947 percentage points and two-carry advantage+3.1915pp. Overall advantage does NOT hold in every seed; no prespecified architecture-superiority/NI hypothesis and no statistical superiority claim. Registered and active-capacity differences persist.

Primary ceiling: hard d2 counts185/188,184/188,183/188 give97.8723404255% mean. Maximum possible improvement to100% is only2.1276595745pp, less than the required5pp. Thus **primary BLOCKED/CEILING_LIMIT** is correct; exit2 is not an environment crash. This is a task/endpoint sensitivity limitation, not a benefit PASS and not evidence all recurrence is impossible.

Observed hard d4−d2 seed differences are **+1.0638pp,-1.0638pp,-3.1915pp**, mean **-1.0638pp**. Overall mean change is **-1.1404pp**; all three overall changes are negative. Seed20261030 easy accuracy drops223/230 to211/230 (-5.2174pp), beyond the easy safeguard. Retain these descriptive declines rather than hiding them behind the ceiling label, but do not replace the frozen main classification.

Across three seeds'2280 answer instances, d4 fixes18 wrong d2 answers and breaks44 correct ones, net26 fewer correct. This paired description is not statistical significance evidence.

## 5. Counts and scope

Actual-task saved per-step training counts: GPT48,070,656; Parcae52,641,792. Ratio1.09509202454 (~+9.51%). Registered parameter ratio1.08501594049. Both<=1.10, not identical budgets or active capacity. Known8320 inactive native parameters remain disclosed.

Full760-question three-token greedy generation: Parcae d2 **1,036,810,240**, d4 **1,472,040,960** counted FLOPs; ratio1.41977857009 (~+41.98%). Includes repeated prefix forwards and final partial batch. Not end-to-end latency, memory, energy or total hardware FLOPs. Counted-cost increase did not improve observed average accuracy here.

## 6. Decision / next single action

Close the requested original-JSON handoff and record audit. Preserve a useful bounded arithmetic capability baseline PLUS a ceiling-blocked extra-depth screen. Do not rerun for sealing or request the same upload again. Do not reclassify the primary, lower5pp, retune on this already-viewed test, extend old training, sweep more depths or rent GPU.

Next decision should be targeted independent review of this existing protocol/raw JSON, followed by a separately authorized task-difficulty design if warranted. Such a new design must calibrate using an independent development/validation set, require both learnability and enough headroom, then seal a NEW held-out test before model comparisons. No new experiment, branch, model repair or merge is launched by this checkpoint.

Six output binaries and reviewer evidence stay separately scoped; their absence does not require new training to retain this result. No repeat of completed P1-R1 or M2-T JSON audits. Prior M2-L/D/T negatives unchanged; A-M2L-01 retained; Claude mismatch root cause OPEN. Keep PR18 Draft. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL. J1/Bench/R3/upstream/model architecture and frozen sources remain untouched.
