# Mythos mechanism development sequence

The user authorized direct ChatGPT implementation, review and bounded execution without a Claude approval handoff. The destination is a usable trainable, resumable text-generating research model; references to proprietary Mythos describe an ambition, not a claim to know or reproduce its unpublished implementation.

Recovered foundations: original Parcae weights have independent loading/inference evidence in prior checkpoints. The completed CPU8/16/32 experiment reported lower NLL with deeper recursion on a small historical sample, with higher measured latency. This is not adaptive-mechanism evidence. D1 implementation/training/evaluation completed but its preregistered positive screens failed; those findings remain unchanged.

The first added mechanism is an isolated inference controller that continues the same native recurrent state through8/16/32 and uses a frozen TV threshold0.01 to choose16 versus32. No learned gate, weight update or new model architecture is introduced. The previous development checkpoint5c2c4645 records15 CPU tiny-model/helper tests; real pretrained140M validation is separate.

Current stage: MYTHOS-ADAPTIVE-DEPTH-140M-SMOKE-V1. Establish original-state restoration, native-byte-equivalent outputs at each depth, paired initialization, causality, repeated decisions and complete operation accounting. This55-call smoke cannot establish language quality, training recovery, production readiness or hardware superiority.

After PASS, review actual exit distribution and added readout cost before freezing a separate quality/cost protocol. It must compare fixed16/fixed32 and a compute-matched routing control; decisions may use only the available input prefix, never target labels. Freeze data, seeds, primary metric, statistical/engineering gates and analysis before observing new scores. Performance gains require held-out task evidence and complete cost accounting, not merely fewer recurrence steps.

Only after a mechanism shows a credible benefit should it be combined with another. Memory, learned gates, dual-state paths and training adaptation require separate protocols, causal controls and checkpoint recovery tests. Existing B2/D2-A remain out of scope. If this stage FAILs or is BLOCKED, preserve the attempt and diagnose its specific cause under a new bounded protocol instead of changing its thresholds or retrying it.

CPU first. Upstream remains read-only at69284c13746e849104f738d6d1a347b1f457df76. No A5 relaxation, B1 rerun or PR24 operation. Current reviews are internal agents; external Grok/Claude review was not performed. Every stage records Purpose, Environment, Input, Expected, Actual and status, then seals evidence and a unique next instruction. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False.
