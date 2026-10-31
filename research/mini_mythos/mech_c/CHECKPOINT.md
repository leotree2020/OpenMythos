# MECH-C — actual uploaded-result audit and scoped decision (2026-10-31)

**Original JSON/record consistency PASS. Nine user-run training records complete. PRIMARY C4 versus S16 PASS; secondary C4 versus P4 PASS; S16 versus P4 FAIL.** All three within-four-step d4-minus-d2 secondary screens PASS. These are predeclared exploratory DEVELOPMENT screens, not formal acceptance or general architecture superiority. The original JSON handoff is COMPLETE; do not request the same file or rerun training for sealing.

## 1. Goal, Git and original evidence

User authorized separate mechanisms. C tests four phase-specific rank4 projection corrections against a parameter-matched shared rank16 correction and contemporaneous native P4. Preserve MECH-AB primary FAILs and their limited positive signals; do not replace an older result with a new label.

- Repository leotree2020/OpenMythos, branch mini-mythos-mech-c-lora-cpu-20261031, Draft PR21; base PR20 at4cf60b053c7b9c2e89e64646cd986d33a34a7657.
- Executed source **38a6f1dcbbf04ab823686aff9c4e6c4acddc0ad0**. Protocol first committed at **ba968dfd41c56fd8bf0ca7243fea197f576e1f77**. Preparation checkpoint and tests remain at the executed commit. This audit changes no protocol, training source or threshold.
- Unmodified native upstream **69284c13746e849104f738d6d1a347b1f457df76**. Factory/task/inherited evaluation helpers remain unchanged.
- Actual upload `result(5).json`: **5,407,979 bytes**, independently calculated SHA256 **b942126365fb0360153117819118a9347e0fabf39d97cb38ed6ded323f37f51a**. No separate terminal digest supplied; no invented external match/authenticity claim. Original bytes unchanged.
- Evidence summary [evidence/uploaded_json_audit_20261031.json](evidence/uploaded_json_audit_20261031.json), first saved at **0ecb5d2e2466c209adc72276dff5662986714807**.
- User result location `/workspaces/OpenMythos/mythos_evidence/mech_c_v1/result.json`; nine model+adapter/AdamW/RNG snapshots under jobs/ are not part of this upload.
- Audit date is not an assertion of native execution time.

## 2. Fixed design and acceptance

All three arms train the original backbone, retain original configuration mean_recurrence2/initialization and explicitly unroll [0,4]. P4 has no correction; S16 uses a shared rank16 at each core attention output32->32 and FFN output64->32; C4 uses an independent rank4 at each of four iterations. S16/C4 each add2560 parameters, total62784; P4 total60224. Canonical down-factor numbers match, zero up factors preserve initial function. No auxiliary loss, damping, state-init change or inactive-parameter repair. This is not frozen-backbone adapter-only fine-tuning.

Seeds42/20261029/20261030;3000 updates, batch32, same starts/data batches/training RNG and original AdamW(.002,betas(.9,.999),eps1e-8,weight_decay0),clip1. Each arm has96000 problem exposures,384000 answer-token exposures,864000 input positions. Recorded producer LinuxPython3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,FP32,one thread.

Reuse19977 training rows/10000 canonical pairs and1024 development pairs,256 per carry stratum. Swapped pairs isolated. Already-viewed development is not a fresh held-out test; reserved test remains unopened. No90% upper capability cap.

PRIMARY C4-S16 d4 mean paired accuracy gain>=1pp AND each seed delta>=-1pp; S16 mean>99% -> ceiling BLOCKED. C4-P4 and S16-P4 are separately labelled secondary comparisons. Per-arm d4-d2 requires mean>=1pp, each seed positive,carry0 loss<=1pp. No post-hoc changes.

## 3. Actual endpoint results

Correct complete answers to the SAME1024 development questions:

|Seed|P4 d2|P4 d4|S16 d2|S16 d4|C4 d2|C4 d4|
|---|---:|---:|---:|---:|---:|---:|
|42|25|262|10|58|4|284|
|20261029|244|1004|181|970|321|1004|
|20261030|575|981|308|942|249|1020|
|Mean accuracy|27.4740%|73.1445%|16.2435%|64.1276%|18.6849%|75.1302%|

C4-S16: **+22.0703,+3.3203,+7.6172pp**,mean **+11.0026pp**, PRIMARY PASS. C4-P4: **+2.1484,0,+3.8086pp**,mean **+1.9857pp**,secondary PASS. S16-P4: **-19.9219,-3.3203,-3.8086pp**,mean **-9.0169pp**,secondary FAIL.

Interpretation must retain both references: C4 beats this shared-rank16 comparator in all seeds, but that comparator itself regresses from native P4. Native-relative gain is1.99pp, not11pp. C4 seed42 remains27.7344%, not a solved low-seed/stability problem. Other C4 seeds reach98.0469% and99.6094%. Same total parameters does NOT isolate depth specificity from per-step rank, compute and gradient reuse. No pure causal/universal superiority conclusion.

All d4-d2 secondary screens PASS. Mean gains P4+45.6706pp,S16+47.8841pp,C4+56.4453pp. **All models train4/final-only: d2 is early readout, not extrapolation beyond trained depth.** C4 d2 mean18.6849% is lower than P4; this is not MECH-A's usable multi-exit signal. Comparing prior A/B average scores is descriptive, not a new preregistered head-to-head. Different PASS/FAIL contrasts are not a ranking.

## 4. Actual counted cost and resources

Per-seed training FLOPs: P4 **342392832000**,S16 **395476992000**,C4 **355663872000**. C4 counts10.0671% less than S16 but3.8760% more than P4; S16 counts15.5039% more than P4. Both adapted arms add4.2508% registered parameters.

Full-development four-token generation d4 counts: P4 **4026531840**,S16 **4655677440**,C4 **4183818240**. C4 is10.1351% below S16 and3.9063% above P4. This quality/count observation is not equal-compute confirmation or hardware speedup. S16 applies rank16 each iteration whereas C4 applies rank4.

Recorded mean training seconds P4 **60.9609**,S16 **64.9542**,C4 **64.8030**. S16/C4 walltimes are close, not evidence of10% faster execution. Single-run timings are descriptive. Worker-lifetime peak RSS398252..401964KiB includes imports/probes/training/evaluation, not training-only memory. No controlled memory/energy benchmark. Supported-op counts exclude optimizer/unsupported work.

## 5. What the audit actually executed

Read live PR21/executed checkpoint/directory Git blobs and complete actual upload. Auditor Python3.13.5/torch2.10.0+cpu; Torch ONLY generated integer batch indices. No model imports, raw output weights, native forward/backward, optimizer, profiler, dependency install or GPU.

**247 record assertions PASS,0 FAIL:** strict JSON/finite values;9 unique arms/18 conditions; independent canonical train/development generation and hash matching; rescored18432 saved answers including category/invalid/transition metrics; checked27000 loss and27000 gradient-norm values; regenerated3 integer3000x32 index arrays; verified9000 RNG triples and original initial-state/shared-IO links. Independently recomputed all primary/secondary/depth/descriptive outcomes and cost arithmetic.

Six delivered source/protocol/launcher files from the preparation bundle match both producer SHA256 and live Git blobs; three inherited helper files and task.py also match recorded SHA256. Raw checkpoint bytes were read through connector but not independently hashed in this audit; do not broaden the six-file claim.

P4 controls in this upload EXACTLY match prior actual MECH-AB records for all3 complete loss/norm/RNG traces, batch/initial/final-base identity, and d2/d4 predictions, metrics, NLL and counts. This is useful two-run record reproducibility, NOT independent auditor training or binary identity validation.

Producer native preflight contains36 zero-initialization identity cases,all reported max base-gradient error0. The records and code were inspected, not re-executed here. Gradient-participation probe counts include tensors with present but zero initial gradients; do not treat them as effective model capacity.

First audit attempt stopped because local extraction omitted the existing .sh file; extracting it from the unchanged development ZIP allowed full read-only audit completion. First attempt logs are retained in the audit bundle. No production source/input/criteria repair.

**NOT TESTED:**9 actual .pt binary audits; independent native scoring/NLL/profiling; full training/restart equality; equal-compute confirmation; new held-out test. NLL was checked finite/consistent where historical reference exists, not recalculated from absent logits. New Grok/Claude review **NOT TESTED/DEFERRED**.

## 6. Decision and next instruction

Close this bounded nine-run stage and JSON handoff. No same-file reupload or rerun for sealing. Retain C4 as a LIMITED parameter-allocation candidate; do not call it uniformly strong, more robust than A/B, fully accepted or merge-ready. Preserve weak seed42 and S16 regressions.

Next bounded instruction: independently cross-review current C4/S16/P4 implementation and evidence, focusing on reference-group degradation, per-iteration rank/compute differences, routing/serialization, exact frozen outcomes and trained-horizon interpretation. No repeat initializer or whole-project audit. Any later fresh-test/equal-budget promotion needs its own explicit protocol. D dual-state and E stopping remain separate candidates, not implemented by this audit; no automatic combinations, rank/lr/depth sweep or GPU scaling.

Full conversation bundle `Mythos_MECH_C_Result_Audit_20261031.zip` contains original bytes, actual audit script/log/results, regenerated development questions, prior raw reference, source identities, Chinese report and review request. Actual remote delivery SHAs recorded in bundle DELIVERY.json. Keep Draft/unmerged.

Preserve previous results and A-M2L-01; Claude initialization mismatch cause remains separately OPEN. No upstream/J1/Bench/R3/old experiment or protocol edits. Formal Oracle **BLOCKED/NOT_READY**, **FORMAL_ACCEPTANCE_READY=False**; no G2 REAL or automatic merges.
