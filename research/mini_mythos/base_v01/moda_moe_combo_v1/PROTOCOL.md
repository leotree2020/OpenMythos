# MYTHOS-MODA-MOE-COMBO-CPU-V1

Status before execution: **NOT TESTED**. This is a new isolated protocol; it does not revise any earlier experiment or turn its negative result into a positive one.

## Purpose and restored evidence

Test whether adding a small trainable source MoE residual to either native fixed32 Parcae or the previously frozen MoDA adapter improves next-token prediction under one fixed CPU training budget. Compare the resulting combination with native, frozen MoDA alone and MoE trained without MoDA. A further frozen-weight intervention removes MoDA from the jointly conditioned adapter. This first stage screens a concrete adaptation recipe, not a causal explanation of learned routing or training synergy.

Restore the latest checkpoint at `d09d5495` on `mythos-moda-fresh-cpu-v1`, then resolve and record its full Git SHA. Read `MODEL_RESULT_REVIEW_V7.md` and `LATEST_CHECKPOINT.json`, not just this summary. V7 execution freeze was `6a87446f8a146f62cae30ae75f986d2b30d30f60`; numerical result publication was `a0ccda074bc0f9e57d5a47b21bc95efb03eae32c`. That experiment completed405 calls,200 unique quality rows and200 exact repeats. Its engineering result was PASS; MoDA versus native failed both-seed performance screens, while MoDA versus the matched shared adapter passed. On its20 AG News texts native NLL was3.61012481; frozen MoDA increased NLL by0.19336079/0.22420227 and reduced accuracy by2.03125 percentage points in both training seeds. Those findings remain unchanged.

The older MoDA development result at `bc6d267cdd8cf9306c1bf08b369cf2b791723d3d` passed on reused WikiText development text. It trained only12288 output-projection parameters for32 steps per adapter. These different domain outcomes are a reason to report each domain separately, not to pool away a regression.

The user's new instruction authorizes separate combination experiments and supersedes the old checkpoint's prospective no-stacking boundary. It does not authorize rewriting old results, selecting a new baseline after a failure, tuning this protocol from its results, or changing protected upstream files.

## Environment and immutable inputs

Run only in Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`, in a new isolated worktree/branch and a never-used run directory. Resolve all exact paths and byte pins in source/input manifests before the execution freeze. Preserve all old runs, blocked attempts, checkpoints and environments. A missing real old artifact blocks execution; a never-created placeholder may be excluded only with the explicit historical proof and absence guards already established in V7. No generic skip-missing rule is permitted.

Use the existing CPU environment: Python3.12.3, Torch2.11.0+cpu, NumPy1.26.4 for the independent auditor, FP32,2 intra-op/1 inter-op threads, deterministic algorithms, no enabled autocast, no GPU or dependency installation. Set the existing CPU/offline environment before imports and record actual settings, CPU identity, versions, executable and stdout/stderr. Require at least4GiB available memory at admission; also verify the cgroup available budget. Main worker timeout7200s; fresh-process reload timeout600s. Per-row auditor timeout60s. A timeout is BLOCKED, not a negative quality conclusion.

Immutable references include:

- Parcae upstream `sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76`, clean/read-only.
- Original140M model weights SHA256 `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`; configuration SHA256 `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`; tokenizer SHA256 `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`.
- Exact OpenMythos source `open_mythos/moda.py` at `d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85`:42070 bytes, SHA256 `335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492`. Use its `DeepSeekMoE`, expert and gate implementation without editing those bytes. Mathematical source-readiness checkpoint `5d9df2733f2b04cab9515db8c51c6b37a7443bda` is supporting evidence, not evidence that this new140M integration works.
- Existing H4101/H4202 MoDA checkpoint weights, frozen features, local RoPE buffers and source wrappers, loaded from the accepted original MoDA run using its recorded pins. All H parameters are frozen; the native63 state entries are frozen. No historical optimizer state is resumed.
- Original WikiText input `/workspaces/mythos-evidence/base_v01/depth_lora/preparation-v1/data/inputs.json`,81885 bytes, SHA256 `b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc`. Preserve its16 train and16 evaluation articles and their ordering.
- Existing V7 AG News input `/workspaces/mythos-evidence/base_v01/moda_fresh/preparation-v6/inputs.json`,32692 bytes, SHA256 `2b740275785c4920ff59bcf3b76b2a81cce24597e4f5de1f491b8ea3357890db`,20 articles,5 per source label. Confirm the path against the frozen V7 manifest before running.

There is no acquisition, tokenization, historical rescan, reselection or new held-out creation. The V7 input was history-excluded when selected; its scores have now been seen, so it is a **development regression panel** in this protocol. Neither panel is a fresh confirmation set. Base-pretraining overlap remains unknown.

## Exact source residual and training boundaries

At native width768, instantiate source `DeepSeekMoE` with one shared expert, four routed experts, top2 activation, expert hidden dimension16, no routing bias, one group/one selected group, source default softmax scores and route_scale1. Freeze `moe_balance_alpha=0`: training loss is language-model cross-entropy only. Do not add balancing, normalization, residual scaling, dropout, new features or an alternative gate after seeing collapse.

All187392 new MoE parameters are trainable: `5 × 3 × 768 × 16 + 4 × 768 = 187392`. Verify the formula and the actual named-parameter inventory independently. The earlier190464 estimate was an arithmetic error and is not an accepted parameter count. For each seed4101/4202, construct the complete source module in an isolated CPU RNG fork, keep its default random initialization for the gate/w1/w3, and set all five expert/shared `w2.weight` matrices to zero. Restore the global RNG exactly. The initial E state must be byte-identical between native-background and H-background training for the same seed.

One E module is shared over all32 recurrences. The native FFNs and attention remain active. At recurrence t, use this fixed serial order:

1. Native injection adapter produces `y_t`.
2. If H is enabled, form `u_t = y_t + H(y_t, past_K, past_V)`; otherwise `u_t = y_t`.
3. If E is enabled, form `v_t = u_t + E(u_t)`; otherwise `v_t = u_t`.
4. Pass `v_t` through the original two native core blocks. When H is enabled, write its K/V from the second core output, as in the frozen MoDA construction.

H reads exactly depths0..t-1; the current/future write is never read. Every call has new cache lists; no cross-article/state leakage. This is a serial residual integration inspired by the source mechanisms, not a replacement of the complete native architecture or a claim to implement the full OpenMythos MoDABlock.

H weights remain frozen, but **H computations and history must not be wrapped in no_grad or detached during E training**: later E gradients may pass through H and the full32-recursion graph. Native/H optimizer membership is forbidden. H's evaluation/instrumentation flag does not authorize severing autograd. Evaluation creates no backward graph; E parameters are frozen during evaluation and restored to their declared trainable set only for their training phase.

The source softmax gate does not renormalize the selected top2 weights. Their sum can vary with input and routing. Record this mass; do not silently replace it with normalized weights. This recipe does not isolate expert selection from selected-score magnitude. A capacity-matched non-learning-selection control is **NOT ASSESSED** here; see the retained design disagreement below.

## Nine configurations and training schedule

The fixed semantic configuration order is:

| Index | Configuration | H | E weights |
|---:|---|---|---|
|0|F|off|none|
|1|H4101|frozen H4101|none|
|2|Esolo4101|off|E trained on F, seed4101|
|3|HE4101|frozen H4101|E trained with H4101 enabled|
|4|EjointHoff4101|off|same E weights as HE4101|
|5|H4202|frozen H4202|none|
|6|Esolo4202|off|E trained on F, seed4202|
|7|HE4202|frozen H4202|E trained with H4202 enabled|
|8|EjointHoff4202|off|same E weights as HE4202|

Implementation names may be mapped to these semantic IDs in a frozen manifest, but this order, weighting and membership may not change. EjointHoff is a zero-update intervention, not a separately trained arm. There is no Esolo+H arm in this stage.

Train exactly four new E instances: Esolo4101, Ejoint4101, Esolo4202, Ejoint4202, in that order. H4101/H4202 retain their original weights throughout. Each E receives32 steps, batch1, using `train[step mod16]` twice in the fixed order. Input tokens0..127 predict tokens1..128; use all128 targets. Thus each new E receives4096 training-target presentations, and the stage has128 optimizer steps/16384 target presentations. Training h0 seed is `1000000 + 100 × training_seed + step`, for step0..31, paired across the two backgrounds. Verify actual h0 and before/after RNG hashes, not only integer seeds.

AdamW LR0.001, betas(0.9,0.999), eps1e-8, weight_decay0, foreach=False; global clip maxnorm1, error_if_nonfinite=True, foreach=False. No scheduler, early stopping, curriculum, more steps/seeds, optimizer resume or tuning. Keep native fixed32 with explicit `num_steps_pair=[0,32]`; no activation checkpointing or truncated BPTT.

Each HE contains a previously trained H plus a newly trained E: the inherited H itself used4096 training-target presentations. Equal new E steps therefore do not make HE and Esolo equal in cumulative training history or total parameters. Record inherited/new budgets separately.

## Exact call accounting, controls and evaluation

The complete planned coverage is **792 forward calls**:

- Seven initial controls: F, H4101, H4202 references and four zero-E additions on their matching F/H backgrounds, all on **AG News evaluation article0 with h0 seed5101**. Before any of128 training steps, bridge the three F/H reference scored64-position matrices and h0/RNG to their exact V7 records; failure is BLOCKED: historical baseline equivalence not established. These three early historical checks add no forward and do not replace the216 complete evaluation bridges below. For each zero-E addition, compare all128-position logits and paired RNG/h0 bitwise with its same-process F/H reference, using ordinary residual arithmetic rather than a zero-output bypass; an identity mismatch is FAIL. No historical or new threshold is relaxed and the total remains792 calls.
-128 training forwards/updates as specified above.
-648 quality/evaluation forwards:36 articles ×2 h0 seeds ×9 configurations.
-Nine forwards in one new interpreter process for checkpoint reload validation, one per configuration, on **AG News article0, h0 seed5101**. These nine controls do not enter any quality or timing denominator.

The main process therefore has783 calls; the reload process has9. There is no complete second evaluation pass. Exact reload success for9 sentinels does not establish a648-row deterministic repetition result.

Define article order as the16 Wiki evaluation articles followed by the20 AG News articles, preserving each source's order. For case0..71, global_article_index=`case//2`; h0 is5101 for even cases and5202 for odd cases. The stored domain-local `article_index` is the global index for Wiki and global index minus16 for AG News. For slot0..8, evaluate configuration_index=`(case+slot) mod9`. This one-pass cyclic order yields exactly8 observations in every configuration/slot cell. Record explicit case, slot, domain-local article index/identity, seed and configuration in every quality and timing row; global position is determined by case.

Every input has129 frozen IDs. Feed128 and score the final64 next-token positions: logit positions64..127 against source IDs65..128. Wiki denominators are2048 scored observations/configuration; AG denominators are2560. Average the two h0 values within each article, then give articles equal weight within each domain. Do not pool domains into a primary screen or count two h0 measurements as independent source texts.

The F/H4101/H4202 rows already have historical full-scored-logit hashes and h0/RNG evidence in the accepted Wiki MoDA run and V7 AG run. Verify all216 such historical bridges within the648 planned calls, with no extra forward. A mismatch is **BLOCKED: historical baseline equivalence not established**, not evidence that MoE quality failed; do not substitute a new baseline or relax the bridge.

After all four trained E checkpoints are sealed, reload all required native/H/E states in a new process with the same pinned environment. Each of the9 reload rows must match its main-evaluation counterpart in full scored-logit SHA, h0/RNG and configuration-specific route/history observer. Validate complete E state and optimizer step32 metadata; do not resume optimization. The last predefined reload is configuration8, EjointHoff4202, AG article0/h05101.

## Gradient, routing and runtime acceptance

Before formal freeze, isolated tiny development fixtures must cover the exact source dense expert equation versus sparse dispatch; input/expert/router gradients; zero-output identity; paired E initialization and RNG restoration; the serial H→E integration; explicit32-step unroll equivalence; history causality, graph continuity and cleanup; save/reload; independent numeric auditing; evidence serialization and actual startup CLI. Fixture results are development evidence only and run with their frozen inventory on target before formal140M calls. The tiny fixture runner uses one CPU thread and records that setting; the actual140M worker uses2 intra-op/1 inter-op threads as specified above.

For finite mixed FP32 source-path fixture outputs and vector-Jacobian products, the pre-execution elementwise bound is `abs(actual-reference) <= 2e-6 + 2e-5*abs(reference)`. Fixed-length future-token perturbation uses this same class, because changing dispatch batch shapes can legitimately change floating-point reduction paths; it must also demonstrably change at least one perturbed suffix output. Identical-argument repetition, zero-residual identity and state reload remain bitwise checks, including signed-zero distinctions. These newly preregistered fixture bounds neither replace A5 nor relax any historical threshold or formal zero/reload requirement. No bound changes after a formal failure.

All losses, logits, used gradients, updates and optimizer states must be finite. Optimizer membership is exactly the new E set, with187392 parameters; native63 and every H state entry retain their bytes and absent gradients. Require one successful32-step sequence per new E and a nonzero finite overall parameter update; report per-parameter gradient/update coverage and all32 residual-gradient contributions. No rule requires every routed expert to be used on every call.

At initialization all output projections are zero, so task gradients into the router and w1/w3 may be zero. Unused experts may have absent or zero gradients. These are not automatic implementation failures. Post-initial training must report actual router/expert changes and coverage. Persistent unused experts, routing collapse, unchanged router or absent useful routing variation are scientific/optimization findings and limit interpretation; they do not authorize balance-loss changes or retries. A wrongly detached path, wrong dispatch, nonfinite arithmetic or missing declared update is an engineering failure.

For each of32 recurrences record exact top2 counts/assignment hashes, unique IDs and total assignments, mean soft scores, gate entropy, selected-weight mass, top2-vs-third margin, route/input hashes and gradient coverage. Distinguish a change in router parameters from proof that routing improved predictions. Tie fixtures establish deterministic tested behavior, not differentiability at ties. With H enabled require32 reads/writes, read lengths0..31 and no current-depth access; with H off require no history activity. Require native two-core call counts[32,32],32 adapter calls, and32 MoE calls exactly when E is enabled. Hooks and temporary state must be removed on success and failure.

## Scientific and timing screens

Report Wiki and AG separately. For each seed4101/4202 and each domain, compare HE with F, H of the same seed and Esolo of the same seed. The frozen practical screen is:

`deltaNLL <= -0.01 nats/token AND deltaAccuracy >= -0.01 absolute`.

Each comparison's group PASS requires both training seeds. A domain's combined-candidate screen requires all three HE comparisons to pass. Report both domain screens; a broad two-panel candidate signal requires both, without averaging away opposite signs. These are exploratory practical screens, not statistical confirmation. Esolo/F, H/F and all per-article differences remain reported, including worst regressions and the number of articles improved. Define IMPROVEMENT when the above two conditions pass; WORSE when deltaNLL>=0.01 or deltaAccuracy<−0.01; otherwise NO_QUALIFIED_IMPROVEMENT. Opposite seed labels are MIXED.

For the E weights trained with H, report the same-weight inference interaction separately per seed/domain:

`I = L(HEjoint) − L(H) − L(EjointHoff) + L(F)`.

This is the numerical nonadditivity of a fixed trained function under an inference intervention. EjointHoff was not its training environment. I can reflect coadaptation/distribution shift, and it is **descriptive only**: no causal-training-synergy PASS, no significance claim and no new threshold. Do not replace EjointHoff with Esolo in this equation; that would mix different trained E weights.

Time all648 complete pretokenized CPU evaluation endpoints with both wall and process CPU clocks, from input/target tensor construction through RNG initialization, all native/H/E paths, coda, scoring and hook cleanup. Instrumentation inside that endpoint is included and disclosed. Hashing/raw serialization, independent audit, I/O, loading and tokenization are excluded from endpoint latency; separately report model/adapter load, training, audit, serialization and total worker wall time/RSS. Keep auditors sequential and outside prediction timing. Record all raw durations and report per-domain/configuration total, mean, median, nearest-rank p95 and paired HE/F, HE/H, HE/Esolo ratios. Nine reload durations are separate. Balanced one-pass timing is descriptive, with no warmed repeated-serving, speed-superiority or equal-compute acceptance claim. Timing validity requires exact648 positive finite durations and the fixed balanced order; scientific latency superiority remains NOT ASSESSED.

## Evidence and new storage envelope

This new protocol has a preregistered **8MiB new raw +64MiB ALL new nonraw +256MiB reserve** envelope. Admission requires at least328MiB available after staging the new sources, and at least4GiB available memory. These are new-stage limits, not retroactive changes to V7 or other thresholds. Nonraw includes all new preparation/operator records, full protection maps, training diagnostics, four full E/Adam/RNG checkpoints, public copies, manifests and a **16MiB Git/finalization allowance**. Public copies are additionally counted, not hidden inside that allowance. Preserve every original protected path, including distinct paths with identical bytes. Each complete lossless compressed protection map must fit4MiB, with bounded decoding and canonical/physical pins; no scope reduction.

Before execution freeze, serialize representative exact-schema fixtures for648 rows,128 training records,9 reloads and all full parameter/optimizer states; measure the complete target protection-map representation and both public/external copies. Freeze a forecast with every component and actual headroom. A planning forecast is not a mathematical compression guarantee: guard actual bytes at phase boundaries, checkpoint/raw writes and publication, keeping the reserve. If the full required evidence cannot fit, report BLOCKED before model work; do not delete old evidence or discard fields to fit after seeing a result.

Every unique scored matrix is64×32768 little-endian FP32,8388608 bytes. Audit each of648 evaluation matrices in full via a bounded independent NumPy stdin stream with immutable target slices, FP64 stable logsumexp and exact raw SHA. The auditor must not import Torch/model code. Save per-token NLL/prediction and prescribed chunk/hash/finite summaries plus subprocess outcomes. There is no pending full-raw disk copy on ordinary success.

Keep only one new raw matrix: on complete success, the **last predeclared reload** (configuration8, EjointHoff4202, AG article0/h05101), after matching its already-audited evaluation hash. All9 reload matrices also receive full independent stream audits: the stage therefore has657 stream audits (648 evaluation plus9 reload), while the quality denominator contains only648 rows. If any earlier evaluation/reload audit or exactness check fails, preserve the current full matrix, when available, as failure evidence and stop; the success sentinel will not yet exist. No second raw file may exceed the8MiB envelope. Record any inability to preserve a failure matrix honestly. Final independent audit rereads the retained sentinel and reconciles all657 live-audit receipts,792-call counts,128 steps,9 reloads and scientific aggregates. The other647 unique evaluation matrices are unavailable retrospectively; compact records cannot reconstruct them.

## Stage acceptance, checkpoint and stopping

Every check records Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Engineering PASS requires the exact frozen call/update/row inventories, correct targets and source/runtime hashes, required development checks,216 baseline bridges, all live numeric audits,9 reload identities, final evidence reaggregation, exact base/H/source/environment custody, actual resource bounds, successful evidence publication and a checkpoint. Command exit0 or a scientific screen alone is insufficient.

At the first engineering FAIL or BLOCKED, stop dependent work, preserve partial evidence/current raw, list unreached work as NOT TESTED and seal a checkpoint. No retry or tuning within the attempt. A completed scientific performance-screen FAIL is a valid result and does not itself stop the later separately preregistered combination stages in PROGRAM.md. No new mechanism is silently added to this run.

The checkpoint records the branch/full execution and result commits, exact dependency environment, all engineering and scientific outcomes, resource use, limits, unresolved issues and one next concrete stage instruction. Keep A5 unchanged, B1 not rerun, B2/D2-A not entered and PR24 unmerged. Formal Oracle remains BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.

Retained disagreement: the independent design review recommended a capacity-matched fixed-subset/learnable-mixture control, and ultimately a history-background × learned-selection training factorial. To minimize this first composition pilot, those controls are deferred. Therefore routing-specific benefit, matched-capacity superiority and causal training interaction are **NOT ASSESSED** even if HE beats all three references. The source default softmax selected-weight mass and unequal inherited training history remain explicit confounds. Subsequent claims must not erase this limitation.
