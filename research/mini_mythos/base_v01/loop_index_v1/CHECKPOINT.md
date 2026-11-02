# MYTHOS-LOOP-INDEX-CPU-V1 checkpoint

Engineering Status: **PASS**.

Base: `d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85`. Execution freeze: `c78be02123a39f54d60f406d3f4eeaf33dc67d50`. Branch: `mythos-loop-index-cpu-v1`.

Purpose: test fixed32 sinusoidal loop-index gain against native frozen fixed32; constant-code gain is a secondary adaptation control. Environment: existing CPU FP32 runtime, Python3.12.3/Torch2.11.0+cpu,2 intra-op/1 inter-op threads; no GPU or dependency change.

Input: frozen16 training and16 evaluation articles,129 tokens each, reused from the LoRA development benchmark; not a fresh generalization test. Both trained arms have96 gain parameters. Two training seeds;32 steps each per trained arm. Expected/Actual: see evidence/summary.json, worker/public/completion.json, reload/public/completion.json and audit.json. Missing stages remain NOT TESTED. Command exit alone is not an acceptance criterion.

Scientific screens: {"depth_vs_fixed32": {"Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "Status": "PASS", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}, "depth_vs_shared": {"Expected": "Same descriptive margins as primary screen in both training seeds", "Status": "FAIL", "scope": "Secondary exploratory equal-96-parameter comparison; depth-varying sinusoidal features versus constant features, not proof of numeric index understanding"}, "shared_vs_fixed32": {"Expected": "Both training seeds: mean NLL improvement >=0.01 nats/token AND accuracy loss <=1 percentage point; average two h0 seeds per article", "Status": "PASS", "scope": "Exploratory fixed-budget adaptation screen; not statistical confirmation"}}. These are exploratory local quality screens, not population confirmation. Screen FAIL is a valid negative result and is separate from engineering execution failure.

Raw evidence: `/workspaces/mythos-evidence/base_v01/loop_index/attempt-v1`; EXTERNAL_EVIDENCE_MANIFEST.json binds raw files at seal. Git holds public reports and manifests; logits,adapter checkpoints and original data remain external. publication.json is a later receipt outside that seal.

Custody: PASS. Old evidence, upstream, base weights and early-stop controller/threshold retained. No B1 rerun/A5 relaxation/B2/D2-A/PR24 operation. Formal Oracle BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Unresolved: limited 96-parameter adaptation, depth-varying modulation versus index awareness, code amplitude/conditioning, pretraining overlap and generalization

Next unique instruction: review this checkpoint and independent audit; preserve all results without tuning. On BLOCKED/FAIL resolve only its recorded cause in a separately frozen continuation. No retry or automatic mechanism stacking.
