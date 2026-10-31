# MECH-C checkpoint — 2026-10-31

## Goal and current status

User asked to continue the remaining improvement mechanisms. Read live PR20 and its checkpoint at4cf60b053c7b9c2e89e64646cd986d33a34a7657 before work. Preserve the nine-arm MECH-AB result: primary A/B FAIL and within-four-step secondary signals; its original JSON handoff is already complete. Do not request old evidence or repeat its audit.

**Implemented C: depth-specific low-rank projection adapters, with a parameter-matched shared adapter control and a native P4 control. Local component/fixture checks PASS. Pinned-native compatibility and nine native training runs NOT TESTED. No new model-quality scores.** D dual-state, E stopping and combinations remain NOT IMPLEMENTED/NOT TESTED in this delivery.

## Git and sources

Repository leotree2020/OpenMythos; branch mini-mythos-mech-c-lora-cpu-20261031; base PR20 HEAD4cf60b053c7b9c2e89e64646cd986d33a34a7657. Protocol committed FIRST atba968dfd41c56fd8bf0ca7243fea197f576e1f77 before native execution. Code delivery through53edfddc714fa36ab41f8d63ab27da678c5afb2d; current HEAD also contains this checkpoint. Only new research/mini_mythos/mech_c files, no original files changed. Keep Draft/unmerged.

Fixed upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76 remains read-only. Reuse original factory/pair_io, R1-B task and MECH-AB evaluation helpers with byte-hash checks. Do not copy or rewrite a Transformer. Source inspection verified native attention c_proj; saved P1-R1 shape records confirm core c_proj[32,32],mlp.proj[32,64], without re-running initialization.

Published directory metadata at53edfdd confirms all six delivered file Git blobs equal actual locally tested bytes: protocol98f89f7301f3d7e514e1f97944aeec89b9c7b5de; adapters28c979185dec965d77d248901a84c0596ae32b54; metrics70102e186ce2181b01c0cc0e53ea86c3ede59048; runner57456584917f1aac33647f401eccb2df99b6c094; launchere865583b0dd2e3e4572e8986493a651fc0505438; testsde7327be9f15c7f9370a3caa099d389e569094ef. Exact SHA256/size records are in delivery checks/published_identities.json.

## Fixed experiment and expected acceptance

P4 unchanged native four-step transition, exit4 CE. S16 uses one rank16 correction per target, shared by all iterations. C4 uses one rank4 correction per target per iteration. Targets only core attention output and FFN output projection. S16/C4 both add2560 parameters, expected total62784 versus P4's60224. All original backbone parameters train; this is not frozen-model LoRA fine-tuning. No auxiliary loss, damping, zero-state substitution or inactive-path repair.

Canonical down-factor values match between S16/C4; up factors start zero, preserving initial function. Private generator seed+31000 does not advance caller RNG. Full adapters enter optimizer, clipping and checkpoints. Loop indices reset every forward; scoped hooks removed even on failure. Four-stage adapters do not imply arbitrary-depth generalization; only d2/d4 are supported.

Nine new training arms: P4/S16/C4 x original three seeds,3000 updates/batch32 each. Same base initial weights, batch sequence and training RNG. Same R1-B train/development data; future test is untouched. There is no90% upper quality gate. Original optimizer and environment are retained. See PROTOCOL.md for all constants and hashes.

Primary comparison C4-S16 at d4: mean gain>=1pp and every seed loss<=1pp. Reference mean>99% gives disclosed ceiling BLOCKED. C4-P4 and S16-P4 are separate secondary screens. Within-trained-horizon d4-d2 screens, correction/corruption, all seed scores and costs are reported separately. Primary FAIL does not erase another useful signal; passing versus P4 alone does not establish depth-specific allocation value.

**Same parameters for C4/S16 is NOT same per-iteration rank or compute.** S16 executes rank16 every iteration; C4 rank4. Actual forward/backward/generation counters report this difference. No equal-compute or hardware superiority claim; already-viewed development is not a fresh test. This compares two allocation designs under one recipe, not universal causal proof.

## Actually executed here

Local environment Python3.13.5,torch2.10.0+cpu,NumPy2.3.5,einops0.8.2. No installs, GPU, native training or user Codespaces shell access claimed.

|Check|Actual outcome|Scope|
|---|---|---|
|Python3.12 AST and Bash syntax|PASS|New implementation files|
|CPU component/fixture tests|18/18 PASS|Low-rank algebra/gradients, canonical init, zero-output identity, routing, cleanup, optimizer coverage, serialization, result gates|
|Nine worker paths|PASS|Affine/tanh fixture ONLY;3 optimizer updates per worker,18 fixture evaluations,9 saved full-state reloads; NOT native learning|
|Existing-output launcher cases|9/9 PASS|Complete PASS/FAIL/BLOCKED, unrelated, bad code/type/JSON, partial directory, log-only; input bytes retained|
|Actual incompatible runtime rejection|Expected rejection PASS|Exit2, execution BLOCKED, zero rows before native construction; no version waiver|
|Published source identity|6/6 PASS|Live Git blobs equal local checked bytes|
|Native compatibility gate|NOT TESTED|Implemented required original-runtime gate before any training updates|
|Native nine-run quality and costs|NOT TESTED|No model results invented from fixtures|
|Fresh holdout/equal-compute comparison|NOT TESTED|Not run in this stage|
|Grok/Claude review|NOT TESTED / DEFERRED|No actual review report supplied|

Fixture model is explicitly affine/tanh, with unused size padding only to exercise fixed metadata; no fixture score is a model result. Detailed checks/scripts/logs are in Mythos_MECH_C_Development_20261031.zip. These finite checks are implementation work, not a new Guard framework.

## Next bounded execution

In existing OpenMythos Codespace, fetch this branch, create the pinned worktree only if absent, check exact HEAD, and execute:

    bash research/mini_mythos/mech_c/run_codespaces_cpu.sh

Defaults: /workspaces/mythos-m2-cpu312/bin/python; /workspaces/mythos-parcae-pinned. Required LinuxPython3.12.3/torch2.11.0+cpu/NumPy1.26.4/einops0.8.0. No downloads/installations. Native zero-initialized logits/loss/base-gradient/RNG/route gate must pass for all seeds before training. Original environment and source checks fail closed.

Output: /workspaces/OpenMythos/mythos_evidence/mech_c_v1/result.json ; full model+adapter/optimizer/RNG and row files under jobs/. Existing results read-only; partial files never deleted or auto-resumed. One run ends the stage, no automatic ranks/steps/seeds/depth sweep. Exit0=primary C4-S16 PASS,1=completed primary FAIL,2=BLOCKED. Upload only this new result/console initially; old uploads are not required again.

## Review and unresolved boundaries

Focused review: both output projections use correct input/output orientation; C4 phase selection is actual rather than cosmetic; S16/C4 really match capacity; zero-up/down-gradient behavior is correctly interpreted; all adapters saved/updated; evaluation uses prompts only; counters include adapter matmuls; no stronger causal/equal-compute claim. Reviewer disagreements remain recorded, not silently resolved by preference.

Preserve A-M2L-01 and Claude initialization mismatch root cause OPEN, older negative results and pending cross-reviews. Upstream Parcae, J1, Bench, R3, model factory and old protocols unchanged. Formal Oracle BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False; no G2 REAL, scale/GPU training or automatic merges. Research inspiration is Relaxed Recursive Transformers, not a claimed reproduction of its published results.
