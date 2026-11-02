# MYTHOS-MODA-RESIDUAL-CPU-V1 checkpoint

Engineering Status: **BLOCKED**.

Base: `5d9df2733f2b04cab9515db8c51c6b37a7443bda`. Execution freeze: `922e42f0030aae8f0062ebbc77aa45324db9f5d3`. Branch: `mythos-moda-residual-cpu-v1`.

Purpose: test fixed32 residual MoDA history attention against native frozen fixed32; current-sequence attention is a secondary adaptation control. Environment: existing CPU FP32 runtime, Python3.12.3/Torch2.11.0+cpu,2 intra-op/1 inter-op threads; no GPU or dependency change.

Input: frozen16 training and16 evaluation articles,129 tokens each, reused from the LoRA development benchmark; not a fresh generalization test. Both trained arms have12288 output-projection parameters. Two training seeds;32 steps each per trained arm. Expected/Actual: see evidence/summary.json, worker/public/completion.json, reload/public/completion.json and audit.json. Missing stages remain NOT TESTED. Command exit alone is not an acceptance criterion.

Scientific screens: "NOT TESTED". These are exploratory local quality screens, not population confirmation. Screen FAIL is a valid negative result and is separate from engineering execution failure.

Raw evidence: `/workspaces/mythos-evidence/base_v01/moda_residual/attempt-v1`; EXTERNAL_EVIDENCE_MANIFEST.json binds raw files at seal. Git holds public reports and manifests. Actual retained audit and disposal progress: {"live_audits": {"PASS": 0, "FAIL": 0, "BLOCKED": 0}, "retention_actions": {"historical_bridge": 0, "sentinel": 0, "audited_then_discarded": 0}, "retained_new_sentinel_files": 0, "pending_new_raw_files": 0, "read_errors": [], "remaining_live_audits": "NOT TESTED"}. Unreached rows remain NOT TESTED. Only completed PASS row audits support a full-live-audit statement. Historical F32 files are retained in the old run; completed new sentinels are retained here. Compact statistics/hashes do not permit retrospective full-logit re-audit for any successfully discarded nonsentinel candidate rows. Adapter checkpoints and original data remain external. publication.json is a later receipt outside that seal.

Custody: NOT TESTED. Old evidence, upstream, base weights and early-stop controller/threshold retained. No B1 rerun/A5 relaxation/B2/D2-A/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: {"type": "Stop", "reason": "protected manifest within2MiB fixture envelope", "traceback": "Traceback (most recent call last):\n  File \"/workspaces/mythos-moda-residual-cpu-v1/research/mini_mythos/base_v01/moda_residual_v1/execute_once.py\", line 351, in main\n    check(\"protected manifest within2MiB fixture envelope\", (RUN/\"protected_before.json\").stat().st_size <= 2*1024**2, True, \"BLOCKED\")\n  File \"/workspaces/mythos-moda-residual-cpu-v1/research/mini_mythos/base_v01/moda_residual_v1/execute_once.py\", line 246, in check\n    raise Stop(failure, purpose)\nStop: protected manifest within2MiB fixture envelope\n"}

Next unique instruction: review this checkpoint and independent audit; preserve all results without tuning. On BLOCKED/FAIL resolve only its recorded cause in a separately frozen continuation. No retry or automatic mechanism stacking.
