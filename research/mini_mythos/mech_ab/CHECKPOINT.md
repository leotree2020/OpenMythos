# MECH-AB — uploaded-result audit and mechanism decision (2026-10-31)

**Original JSON / recorded-data consistency PASS. Nine user-run training records complete. A/B primary quality screens both FAIL. P4/A/B secondary d4-versus-d2 screens PASS within the four-step training horizon.** The raw JSON handoff is COMPLETE; do not request the same file or rerun training for sealing. This is an actual read-only record audit, not an independent native training/replay.

## 1. Goal, Git and evidence identity

User authorized separate mechanism development. This first batch compares the same native Parcae with P4 final-only training, A multi-exit supervision, and B whole-iteration damping. It is not another task-calibration search.

- Repository leotree2020/OpenMythos; branch mini-mythos-mech-ab-cpu-20261030; Draft PR20; base PR19 at78d9c49112f5e1299767d450593f3db08feaf7c6.
- Executed commit **b0bdac11f73f149fbb7cc7dc2ab39cef8e3ca545**, protocol preregistered first atafb21e5409264a9b609ab727fd1e640d35a2700c. Original preparation checkpoint/tests remain at the executed commit. No protocol, code, thresholds or previous results are changed by this audit.
- Native GPT/Parcae pin **69284c13746e849104f738d6d1a347b1f457df76** remains untouched. Factory SHA25674f00c64448ddbc224a48ef83dc031a90c33448ccb92647666707f6b8f988967; task SHA2561baebb6e47f39de63e894e7d8379bdcd8403e8cd79ead1e33fa6e525278940af.
- Actual uploaded result(4).json: **6,668,660 bytes**, independently computed SHA256 **fe50a0881b360088e5794b2b811830be9d1b3763a2aa422bce13aa823de5ee15**. No separate user terminal digest was supplied, so no external digest match or independent authenticity proof is claimed. Input bytes unchanged.
- Evidence summary: [evidence/uploaded_json_audit_20261031.json](evidence/uploaded_json_audit_20261031.json), first saved at **085ba185c30ebfc4c7bf2a0f728bc76a4b64b055**.
- User output: /workspaces/OpenMythos/mythos_evidence/mech_ab_v1/result.json; binary snapshots under jobs/. Nine binary snapshots were NOT uploaded in this handoff.
- The audit date is 2026-10-31. Do not infer the native run completion date from filenames or this date.

## 2. Frozen design and acceptance

P4: unchanged native recurrent transition, final CE at4. A: SAME trajectory/shared native suffix,0.25 CE(exit2)+0.75 CE(exit4), no detach. B: old+0.5*(native_candidate-old) each WHOLE iteration including injection/core, final CE at4. All three retain original config mean_recurrence=2, original layer IDs/initialization and explicitly unroll [0,4]; no additional trainable tensors or inactive-parameter repair.

Three seeds42/20261029/20261030,3000 AdamW updates/batch32 each, same starts/sample sequence/training RNG. Recorded producer Linux Python3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0,FP32 one thread. Original optimizer lr.002,betas(.9,.999),eps1e-8,weight_decay0,clip_norm1. Each arm sees96000 problem exposures,384000 supervised answer-token exposures,864000 input positions. A has two supervised exits for the same labels, not twice as many unique examples.

Reuse19977 training examples/10000 canonical pairs and1024 balanced development questions,256 per carry0..3. Previously viewed development is NOT a new confirmatory test. Reserved future-test role is not opened. No upper90% learned-capability cap applies to this mechanism study.

Primary EACH A/B versus P4 at d4: mean paired accuracy gain>=1pp AND every seed loses<=1pp. Control mean>99% gives mathematical ceiling BLOCKED. Secondary EACH arm d4-d2: mean>=1pp, every seed strictly improves, carry0 loss<=1pp; its d2 ceiling is separately checked. No post-hoc threshold changes. Same data/updates, NOT equal compute.

## 3. Actual endpoint results

All counts are complete answers to the SAME1024 development questions.

|Seed|P4 d2|P4 d4|A d2|A d4|B d2|B d4|
|---|---:|---:|---:|---:|---:|---:|
|42|25|262|963|989|221|894|
|20261029|244|1004|974|987|794|1016|
|20261030|575|981|858|883|566|896|
|Mean accuracy|27.4740%|73.1445%|90.9831%|93.0664%|51.4648%|91.3411%|

A d4 gains over P4: **+70.9961,-1.6602,-9.5703pp**, mean+19.9219pp. B: **+61.7188,+1.1719,-8.3008pp**, mean+18.1966pp. Both miss the per-seed no-worse-than-1pp condition. Thus BOTH primary FAILs stand despite positive means. Large averages are dominated by seed42 recovery; do not select that seed, average away regressions, or label these uniformly improved models.

Observed worst d4 seed: P4 25.5859%,A86.2305%,B87.3047%. Sample standard deviations:41.2023,5.9209,6.8229pp. These are three-run descriptive differences, not proof of robust population stability or a diagnosed reason for seed42's poor control.

Secondary d4-minus-d2 mean gains: P4+45.6706pp,A+2.0833pp,B+39.8763pp; all three secondary screens recompute PASS. A individual gains+2.5391,+1.2695,+2.4414pp with no easy-category regression. Across three seed-answer sets, A corrects115 wrong responses but corrupts51 correct responses, net64 additional correct; P4 corrects1423/corrupts20, B1256/31. These are repeated evaluations of1024 questions, not18432 independent tasks.

**Critical scope:** all models were trained for4 steps; d2 evaluation is early/truncated readout. This does NOT establish extrapolation beyond trained depth, monotone improvement every iteration, ACT, general reasoning or reversal of old depth2-trained M2-D/R1-A negatives. A explicitly supervised its d2 exit; P4 did not. The results support an exploratory usable-intermediate-exit signal, not free efficiency or an internal reasoning trace. Hidden-state causal mechanisms were not measured.

## 4. Compute and resources

Per-seed counted training FLOPs: P4 **342392832000**, A **436285440000**, B **342392832000**. A costs **27.4225%** more supported-op training FLOPs. B's elementwise damping and optimizer work may not be included; equal counters are not free hardware work.

Saved mean training seconds: P4 60.9228,A72.9466,B61.3091. These single-process-run timings are descriptive, not controlled repeated hardware benchmarks. All groups register60224 parameters, probe records51904 participating; known8320 inactive paths remain.

Full four-token generation for1024 questions: d2 **2833776640**,d4 **4026531840** counted FLOPs across all groups. d4 adds42.0907%; d2 uses29.6224% fewer counts than d4 but may lose quality. Peak worker-lifetime RSS398960..405104 KiB includes imports/probes/training/evaluation and is NOT isolated training memory. No general efficiency claim.

## 5. What this audit actually executed

Auditor Python3.13.5/torch2.10.0+cpu; Torch used ONLY to regenerate integer training indices. No native model imports, binaries, forward/backward, optimizer, profiler, GPU or dependency installation. Read live PR20/checkpoint/protocol and executed-commit directory metadata. All seven full source files from the previous delivery match both producer SHA256 and live Git blob IDs. Actual old R1-B/P1-R1 JSONs used only for initial-identity linkage; no repeated initialization.

**308 record assertions PASS,0 failures**, not308 model experiments:

- Strict complete JSON; exactly9 seed/arm rows and18 d2/d4 conditions.
- Independent canonical split reconstruction; train/dev hashes and swapped-pair isolation match; no reserved labels/test split emitted.
- **18432 saved full answers rescored**, every category total/accuracy/invalid count and correction/corruption calculation matches.
-27000 objectives,27000 final losses,9000 auxiliary losses and27000 gradient norms complete/finite;18000 absent auxiliary values are null. A weighted-loss arithmetic agrees within float32 storage rounding (max3.5762786865234375e-7).
- Three3000x32 integer index tensors regenerated; original-state/shared-IO links match prior records.9000 per-update RNG triples equal across P4/A/B; this is digest-record pairing, not independent reconstruction of native RNG consumption.
- Independent primary/secondary/dispersion/cost recomputation matches every saved classification; exit1 is completed primary failure, not process failure.

Native preflight: user reports12 identity conditions with maximum gradient error0 and3 auxiliary-core-gradient PASS. Records and implementation were inspected; actual original-runtime numerical execution is USER-REPORTED, not independently rerun in this audit. Original native execution now has real evidence, unlike the earlier preparation fixtures.

**NOT TESTED:**9 .pt binary audits, independent native score/NLL/profiler replay, full training/resume equivalence, equal-compute comparison, fresh held-out confirmation. New Grok/Claude cross-review **NOT TESTED/DEFERRED**. Output checksum fields do not substitute for files; saved NLL is not recomputed from logits because logits/weights were not provided.

## 6. Decision, next action and boundaries

Close this bounded9-arm run and raw-JSON handoff. No reupload/retraining required for sealing. Retain A as a PRIORITY CANDIDATE for multi-exit learning and B as a separate candidate; neither is a passed primary intervention or merge-ready superiority result. This is a useful measured mechanism signal, not a reason to discard every intervention or to promote a favourite result.

Next single action: focused independent cross-review of existing protocol/mechanism code/raw answers, particularly primary-FAIL versus secondary-PASS, A's same-trajectory/shared-suffix supervision, whole-step damping, extra training cost, and trained-depth versus early-exit interpretation. Do not request a repeat of the whole project audit or initialization checks. Before an efficiency/generalization promotion, separately design equal-budget and fresh held-out confirmation; no automatic new training here. C/D/E and A+B remain NOT IMPLEMENTED/NOT TESTED in this batch and are not invalidated by A/B primary failures.

Conversation audit bundle Mythos_MECH_AB_Result_Audit_20261031.zip contains raw bytes, actual audit script/log/results, reconstructed development questions, source/reference identities, Chinese stage report and focused reviewer instructions. Git update details are in bundle DELIVERY.json. Keep Draft/unmerged.

Preserve old R1-B FAIL, R1-A ceiling and M2 negatives; A-M2L-01 and separate Claude init-mismatch root cause OPEN. The previous carry-count erratum remains: carry3>carry2 in TWO R1-B seeds, not three. No model/upstream/J1/Bench/R3/old protocol changes. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, GPU expansion, threshold repair or automatic merging.
