# MYTHOS-MODA-RESIDUAL-CPU-V2 checkpoint

Engineering Status: **PASS**.

Base: `d5d6e74888b65b757ecef075f1bd6838f712cc77`. Execution freeze: `301cb192e8a32768146c9bb9131699ee9aad4da2`. Branch: `mythos-moda-residual-cpu-v2`.

Purpose: test fixed32 residual MoDA history attention against native frozen fixed32; current-sequence attention is a secondary adaptation control. Environment: existing CPU FP32 runtime, Python3.12.3/Torch2.11.0+cpu,2 intra-op/1 inter-op threads; no GPU or dependency change.

Input: frozen16 training and16 evaluation articles,129 tokens each, reused from the LoRA development benchmark; not a fresh generalization test. Both trained arms have12288 output-projection parameters. Two training seeds;32 steps each per trained arm. Expected/Actual: see evidence/summary.json, worker/public/completion.json, reload/public/completion.json and audit.json. Missing stages remain NOT TESTED. Command exit alone is not an acceptance criterion.

Scientific screens: {"shared_vs_fixed32": {"Status": "FAIL", "Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}, "depth_vs_fixed32": {"Status": "PASS", "Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}, "depth_vs_shared": {"Status": "PASS", "Expected": "Same descriptive margins as primary screen in both training seeds", "scope": "Secondary exploratory equal-12288-parameter output-projection comparison; joint depth memory versus current-sequence attention control; compute/optimization may differ"}}. These are exploratory local quality screens, not population confirmation. Screen FAIL is a valid negative result and is separate from engineering execution failure.

Raw evidence: `/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v2`; EXTERNAL_EVIDENCE_MANIFEST.json binds raw files at seal. Git holds public reports and manifests. Actual retained audit and disposal progress: {"live_audits": {"PASS": 160, "FAIL": 0, "BLOCKED": 0}, "retention_actions": {"historical_bridge": 32, "sentinel": 4, "audited_then_discarded": 124}, "retained_new_sentinel_files": 4, "pending_new_raw_files": 0, "read_errors": [], "remaining_live_audits": "NONE"}. Unreached rows remain NOT TESTED. Only completed PASS row audits support a full-live-audit statement. Historical F32 files are retained in the old run; completed new sentinels are retained here. Compact statistics/hashes do not permit retrospective full-logit re-audit for any successfully discarded nonsentinel candidate rows. Adapter checkpoints and original data remain external. publication.json is a later receipt outside that seal.

Custody: PASS. protected_before.json.gz is a lossless complete path/pin inventory, verified by protected_before_receipt.json; no protection scope was dropped. Original attempt-v1 and all prior evidence remain unchanged. Old evidence, upstream, base weights and early-stop controller/threshold retained. No B1 rerun/A5 relaxation/B2/D2-A/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: limited output-projection adaptation, memory-path capacity versus compute, frozen random feature conditioning, pretraining overlap and generalization

Next unique instruction: review this checkpoint and independent audit; preserve all results without tuning. On BLOCKED/FAIL resolve only its recorded cause in a separately frozen continuation. No retry or automatic mechanism stacking.

## Final root acceptance — 2026-11-02 UTC (supersedes the earlier next instruction)

Engineering execution **PASS**; independent final NumPy audit **1979 PASS /0 FAIL**; root read-only closure **2640 PASS /0 FAIL**. These are distinct from scientific screens. All model work is stopped.

Git: result `8043f5665667b78d956984c1292a335ce4c8e375`; frozen root closure code `6e9f0b1468b66ad5acfdf5fe32f024df67b7cbf6`; closure evidence `fcedb81a2c05cdcbf418df2f0e2c25c75f6a0e8d`. Current branch is `mythos-moda-residual-cpu-v2`; this documentation commit is a descendant and its exact SHA is available in git log. Source/execution freeze stays `301cb192e8a32768146c9bb9131699ee9aad4da2`. Original v1 BLOCKED checkpoint `d5d6e748` and its records are preserved.

| Arm | train seed | NLL (lower is better) | correct /2048 | token accuracy |
|---|---:|---:|---:|---:|
| Native fixed32 | none |3.287538548167015|732|35.7421875%|
| Current-sequence control S |4101|3.2888098352260404|734|35.83984375%|
| Current-sequence control S |4202|3.3008355906499545|738|36.03515625%|
| MoDA history H |4101|3.235129174539436|775|37.841796875%|
| MoDA history H |4202|3.2073188765448175|764|37.3046875%|

H versus native: NLL changes -0.052409373627578915 / -0.08021967162219747, accuracy +2.099609375 / +1.5625 percentage points. H versus equal-12288-trainable-parameter S: NLL -0.05368066068660436 / -0.09351671410513707, accuracy +2.001953125 / +1.26953125 points. Both preregistered two-seed screens **PASS**. S versus native screen **FAIL**: first seed NO_QUALIFIED_IMPROVEMENT, second WORSE by the frozen NLL margin. This negative control result is not an execution failure.

Purpose: establish whether the isolated trained history branch provides a local quality signal. Environment: designated Codespace, AMD EPYC7763 CPU, Python3.12.3, Torch2.11.0+cpu, NumPy1.26.4,2 intra/1 inter threads; existing dependencies unchanged. Input:16 train/16 reused development articles,129 tokens each,64 evaluation targets/article and2 h0 seeds;2 training seeds and32 updates/arm/seed. Expected/Actual: all60 target developer tests PASS;293/293 main calls,128/128 updates,160/160 evaluated/audited rows,4/4 new-process reloads exact. Base63 state entries unchanged. All32 gradient depths active; H consumed history gradients active after zero initialization, S has no history consumers.

Main process1134.599941958997 seconds, reload37.04631265900025 seconds, main peak RSS2055708672 bytes. These include loading and all work and are not evidence of equal-compute or isolated inference-speed superiority.

Storage repair **PASS**: all original25367 path/pin pairs remain within25436 protected objects. Final lossless gzip is1181241 bytes, canonical full map5992065 bytes; both bound by evidence/protected_before_receipt.json. No physical evidence path was deduplicated out of protection. The2MiB/copy,32MiB nonraw,40MiB raw and256MiB reserve limits remain unchanged. All25436 objects were rehashed by root closure;550 external files and542 public copies verified. No changed upstream, old run, dependency or input was detected.

Evidence: frozen SOURCE_MANIFEST and INPUT_MANIFEST; evidence/audit.json; closure/acceptance-v2.json; closure/MANIFEST.json; external raw data/adapters bound by EXTERNAL_EVIDENCE_MANIFEST.json. All160 full matrices had a live independent NumPy audit;32 old native matrices and4 trained sentinels remain and the final audit recomputed these36. The124 nonsentinel candidate matrices were discarded only after their prescribed PASS audit; they cannot be reconstructed from compact records. Root recomputed aggregate/per-token metrics from audit records and verified retained raw hashes, not an additional full-logit recomputation.

Scientific acceptance: **positive exploratory development-set signal** for this restricted output-projection adaptation. H improves NLL on9/16 and10/16 articles versus native, with worst article regressions +0.23858391560771142/+0.22674130670963089 nats/token. It improves14/16 and16/16 versus S. Do not erase this heterogeneity or claim all texts improve. Only12288 output parameters are trained; frozen random features, optimization and unequal compute remain caveats. Reused16-article development data and two seeds are not statistical or fresh-test confirmation; pretraining overlap unknown. Static cross-check was another ChatGPT agent, not human or cross-vendor replication.

Fresh-test generalization, statistical confirmation, equal-compute superiority and production language quality: **NOT TESTED**. Formal Oracle **BLOCKED/NOT_READY**; FORMAL_ACCEPTANCE_READY=False. PR24 read-only check: open/draft/unmerged, head4308099bfc90d9398f54a47f9272b6bd4582f7b9. No PR operation, A5 relaxation, B1 rerun, B2/D2-A, GPU or MoE/stacking execution.

Next unique recommended instruction: freeze the current F32/S/H weights and thresholds; preregister a zero-training paired CPU evaluation on project-unseen new texts deduplicated against previous train/dev, with the same scoring and actual elapsed compute reported. This tests transfer before stacking. It does not guarantee absence from base pretraining. No new experiment is started by this checkpoint. This authorized MoDA stage is complete and stopped.
