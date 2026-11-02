# Mythos development direction, 2026-11-02

User objective: build our own usable Mythos model, taking Parcae as the initial pretrained base and OpenMythos as a source of mechanism ideas, with Claude Mythos capabilities as the long-term reference. Retain a runnable native Parcae comparator. Success requires measured added value, not accumulating named mechanisms.

## Public facts and limits

Anthropic's [transparency report](https://www.anthropic.com/transparency), checked 2026-11-02, describes Claude Mythos 5.1 as a pretrained and substantially post-trained model and describes a proprietary training-data mixture. These materials do not provide us with the weights or a complete reproducible training recipe. We therefore cannot claim an exact internal reproduction or promise parity from Parcae 140M plus a few modules.

The [OpenMythos README at our base commit](https://github.com/leotree2020/OpenMythos/blob/c63b829a752ac57d22addfe17ff53ecbcb58e8a0/README.md) explicitly describes the project as an independent theoretical reconstruction based on public research and speculation. Its main.py also calls the architecture hypothesized. Its recurrent block includes learned halting, per-depth LoRA, input injection and other mechanisms. Their presence is implementation evidence, not evidence that Claude uses them or that transplanting them improves this pretrained Parcae. OpenMythos ACT continues dense computation until all positions halt; masking by itself does not prove reduced work.

## Verified starting point

Latest completed result checkpoint: c63b829a752ac57d22addfe17ff53ecbcb58e8a0. The frozen depth8/16/32 CPU experiment completed 288 formal rows plus 9 controls; saved audit reports 88 PASS / 0 FAIL. On the fixed historical development articles, mean NLL was 3.3786343 / 3.3468408 / 3.3373113; descriptive median forward time was 1.3115 / 2.1920 / 3.9552 seconds. These results motivate testing selective extra computation, but do not establish any new mechanism's benefit. See the [saved checkpoint and linked evidence](https://github.com/leotree2020/OpenMythos/blob/c63b829a752ac57d22addfe17ff53ecbcb58e8a0/research/mini_mythos/base_v01/depth_16_32_v1/CHECKPOINT.md).

D1 implementation/training/evaluation succeeded, but its preregistered positive performance screens failed. It is not an accepted enhancement. Original B1 A5 remains BLOCKED. Neither outcome is rewritten by this new direction.

## Ordered deliverables

1. Adaptive computation engineering: add an isolated, prefix-only depth controller and prove that fixed-depth bypass and continuation preserve native computation. Current stage: implement and CPU-test with synthetic/tiny inputs. Deliver code, evidence and checkpoint.
2. Native140M mechanism validation: use exact original weights, demonstrate bitwise identity to native fixed depths, verify selected-depth behavior and count all additional work. Then measure the frozen candidate against fixed and random depth controls on a separately frozen evaluation sample. Retain it only if the quality/cost tradeoff justifies it. If confidence does not predict benefit, record a negative result; do not rescue it by unregistered threshold changes.
3. Trainable research baseline: separately specify a small training/adapter experiment, data provenance and splits, loss/gradient correctness, and uninterrupted-vs-resumed optimizer/model/RNG/data-position agreement. Extend to instruction following and short verifiable tasks. Inference continuation is not training checkpoint recovery.
4. Mechanism ablations: consider learned halting/depth adapters and, subsequently, memory/state feedback one at a time, with disabled-mechanism identity and equal-budget controls. Previously failed D1 is not automatically revived. MoE/MLA/memory are deferred until a concrete task and falsifiable prediction justify the cost.
5. Candidate integration and scaling: combine only retained mechanisms, evaluate reproducible generation, instruction following, small coding tasks with executable tests, multistep tasks, and total cost. Increase model/data/compute only after small-scale evidence. Scaling to frontier capabilities also requires data and post-training; architectural additions alone are not a demonstrated substitute.

No Claude API access, paid GPU, security scanning, or external benchmark submission is part of this stage. Reviews here are internal agent reviews, not Grok/Claude/human independent review. No PR #24 merge. Every stage retains PASS/FAIL/BLOCKED/NOT TESTED and the next unique instruction.
