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
