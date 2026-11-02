# MYTHOS-DEPTH-LORA-CPU-V1 checkpoint

Engineering Status: **PASS**.

Base: `e24d053f482a96bcc2ab207c1be73e4c91fcd721`. Execution freeze: `083192871d6cc3abff0cd5a01fa6f628c7cf29ec`. Branch: `mythos-depth-lora-cpu-v1`.

Purpose: test fixed32 depth-specific rank2 LoRA against native frozen fixed32; shared rank2 LoRA is a secondary adaptation control. Environment: existing CPU FP32 runtime, Python3.12.3/Torch2.11.0+cpu,2 intra-op/1 inter-op threads; no GPU or dependency change.

Input: frozen16 training and16 evaluation articles,129 tokens each. Two training seeds;32 steps each per trained arm. Expected/Actual: see evidence/summary.json, worker/public/completion.json, reload/public/completion.json and audit.json. Missing stages remain NOT TESTED. Command exit alone is not an acceptance criterion.

Scientific screens: {"depth_vs_fixed32": {"Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "Status": "PASS", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}, "depth_vs_shared": {"Expected": "Same descriptive margins as primary screen in both training seeds", "Status": "PASS", "scope": "Secondary exploratory comparison; trainable parameter counts differ32fold, so not isolated causal depth-specialization proof"}, "shared_vs_fixed32": {"Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "Status": "PASS", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}}. These are exploratory local quality screens, not population confirmation. Screen FAIL is a valid negative result and is separate from engineering execution failure.

Raw evidence: `/workspaces/mythos-evidence/base_v01/depth_lora/attempt-v1`; EXTERNAL_EVIDENCE_MANIFEST.json binds raw files at seal. Git holds public reports and manifests; logits,adapter checkpoints and original data remain external. publication.json is a later receipt outside that seal.

Custody: PASS. Old evidence, upstream, base weights and early-stop controller/threshold retained. No B1 rerun/A5 relaxation/B2/D2-A/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: small-budget adaptation, depth-specificity versus extra parameter capacity, pretraining overlap and generalization

Next unique instruction: review this checkpoint and independent audit; preserve all results without tuning. On BLOCKED/FAIL resolve only its recorded cause in a separately frozen continuation. No retry or automatic mechanism stacking.
