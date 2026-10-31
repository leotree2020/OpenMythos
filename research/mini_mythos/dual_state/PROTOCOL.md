# D1: work/answer-state profiling, not candidate confirmation

2026-10-31. Experiment MYTHOS-D1-DUAL-STATE-PROFILE-V1.

## Question and authorization

The owner explicitly requests trying mechanism D and observing its measurements. This authorizes a separate research implementation and bounded CPU exploration, not modification of upstream or revision of failed A/C evidence. Previous C1 result review stays pending; it is not a reason to relabel C1 or claim D already works. Claude Code reviews the new delta before production training. No Grok gate.

Question: with a shared native transition, does separating a working latent z from an answer latent a change learning, correction/corruption, state trajectories and costs? This first implementation is one D variant, not all possible dual-state models and NOT a reproduction of TRM. Inspiration: the official SamsungSAILMontreal/TinyRecursiveModels README describes alternating latent and answer updates. We retain Parcae's causal full-prefix generation, initializer, prelude, native transition and suffix instead of importing TRM's task interface, supervision, halting or training schedule.

## Frozen variant

Read-only upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76. Use the existing M2 factory, R1-B task and MECH-AB readout/scoring. No upstream source edits, model-size changes, inactive-path repair, A/B/C adapters/losses, learned gate, new parameters, persistent cross-example memory or optimizer change.

Let F(h,u) be one ORIGINAL Parcae input-injection plus shared-core call. e is its fixed prelude representation of the current token prefix. h0 is its original sampled initial state. Dimensions must match (32); unsupported configurations BLOCK rather than project silently. P4 applies h <- F(h,e) four times. D0/D1 initialize z=a=h0 and perform two cycles:

    D0: z <- F(z,e);     a <- F(a,z)
    D1: z <- F(z,e+a);   a <- F(a,z)

The second update uses the NEW z; D1 feedback uses the OLD a of that cycle. No detach in training. Final native C/coda/norm/head reads a after cycle2. D0 is the answer-feedback ablation, not a single-state model. D1-vs-D0 changes only feedback. D-vs-P4 changes state/routing as a package, not a pure causal identification of storage alone. Initial z/a coincide but evolve separately. a is a latent representation, NOT the correct answer or a generated text scratchpad.

Depth means TOTAL core calls: depth2=one work/answer cycle; depth4=two cycles. P4 has two/four single-state calls. Every model trains four calls with final-only CE; no intermediate loss. Depth2 scoring is early readout within the training horizon, NOT depth extrapolation. Native random-state generation occurs once per prefix, as before; states reset each prefix/example. Full-prefix autoregressive evaluation is unchanged.

## Bounded groups and data

Arms GPT/P4/D0/D1; new seeds2101/2202/2303, fixed in advance. 12 trajectories,3000 updates each,batch32. Original AdamW lr0.002,betas(0.9,0.999),eps1e-8,weight_decay0; clip global norm1; FP32/one CPU thread; original Python3.12.3,torch2.11.0+cpu,numpy1.26.4,einops0.8.0. No dependency installation or GPU. Identical per-seed data indices (seed+12000) and shared IO initialization; all Parcae arms share exact initial backbone. Preserve RNG consumption pairing as a checked property, not an assumption. GPT is seed/sample paired, not identical architecture/RNG.

Use ONLY the already-viewed R1-B training/development split:19977 training rows,1024 development questions balanced256 per carry stratum. Reusing this development set is explicitly exploratory, not fresh-test evidence. No MES H1,HC,H2 or C1T evaluation; no new heldout allocation. Numeric failure is recorded, no seed replacement/retry or best-checkpoint selection.

Same updates/data exposure, NOT equal training compute. Measure actual supported-op forward/backward FLOPs for each arm. Include all native calls; report counters separately from descriptive walltime/worker RSS and state storage. No equal-hardware or efficiency victory claim. GPT retains its four native blocks and split loss/logits API. All Parcae arms register60224 parameters; known8320 inactive paths are retained.

## Measurements fixed before model results

Save full model/optimizer/CPU RNG/index snapshots at updates300,1500,3000 (36 total). These are predetermined checkpoints, not selected by performance. Never train based on observed development scores.

After all scheduled training, evaluate existing snapshots without weight updates:

1. Full1024-question free-generation scores at FINAL checkpoint: GPT depth4; P4/D0/D1 depths2/4 (21 conditions,21504 repeated answers,not21504 independent questions). Save predictions,correct/invalid counts by carry and teacher-forced answer NLL separately.
2. Learning profiles at300/1500/3000 on FIXED32 development prompts (first8 of each carry stratum in original order),using depth4. These overlap the development set and are diagnostics,not additional independent validation.
3. At those same checkpoints,one same-prefix forward over those32 SIX-DIGIT prompts. Save per-example z/a RMS,relative update magnitude,cosine and relative separation at each core call; native-suffix next-token probability/entropy/argmax from completed answer states. Probe labels never enter this forward. State closeness/confidence/stability is not correctness. Shared next-token outputs do not constitute full-answer same-trajectory reasoning traces.
4. Full-answer depth2-to4 correction,corruption,unchanged-correct and unchanged-wrong counts. These are two complete generation policies with different later prefixes,NOT a claim that the same full answer was edited in-place.
5. FINAL D0/D1 only,32 fixed prompts: separately zero working state OR answer state immediately before the second cycle,using identical RNG. Record next-token logit L2/argmax changes versus unperturbed forward. No-op must be identical. This is a local intervention sensitivity diagnostic,not proof of human-like reasoning or general causal importance.
6. Final synthetic-batch gradient-presence/nonzero counts and None-gradient names; present zero gradients are not effective capacity. Record all loss and preclip-norm traces and descriptive resources. No repeated hardware benchmark claim.

## Acceptance and stopping

Implementation PASS requires P4/native equality (logits/loss/gradients/RNG), D0/D1 equality to an independently unrolled native two-state reference, hook cleanup on success/error, no added parameters, feedback/no-feedback distinction, causal no-future-token leakage, no-op diagnostic identity, finite values and snapshot round-trip. Fixtures and native tests are reported separately; actual production checks cannot be replaced by a test fixture.

Data/execution PASS means all12 jobs and required measurements complete, aligned, finite and snapshot-bound; it is NOT a positive mechanism finding. Report descriptive per-seed changes plus exploratory screens (each D-vs-P4 and D1-vs-D0 at depth4: mean>=+1pp,each loss<=1pp; reference>99% means ceiling BLOCKED). Screen failure never deletes another arm or suppresses measurements. Do not rank A/C against D using different experiments.

Candidate superiority/selection, statistical inference, equal-compute confirmation, fresh-test generalization, hardware efficiency, depth>4 and adaptive stopping: NOT TESTED/NOT ASSESSED by this study. Report raw characteristics even when all exploratory screens FAIL. Do not expand or retune after seeing results without a new authorized protocol.

## Workflow and record boundaries

Separate prepare,train,evaluate. Prepare may build the old train/development data, run no-update native checks and cost probes; no training. Train requires a real Claude Code report and explicit owner acknowledgement. Evaluation loads saved states after the complete-run barrier and validates immutable data/snapshot bytes. Existing or partial evidence is never overwritten or automatically resumed. No manual worker invocation in user instructions.

Keep branch isolated and PR Draft/unmerged. End each phase with actual evidence and checkpoint. Formal Oracle remains BLOCKED/NOT_READY, FORMAL_ACCEPTANCE_READY=False. No G2 REAL, J1/Bench/R3 edits, upstream modification, automatic merge or GPU expansion.
