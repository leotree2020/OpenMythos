# MYTHOS-MODA-RESIDUAL-CPU-V1

Purpose: test whether a small separately trained residual branch that can read previous recurrence states improves native Parcae140M next-token prediction over both the unchanged fixed32 model and a parameter-matched sequence-attention branch. This is a bounded development pilot using the actual OpenMythos MoDA attention implementation. It is not a full MoDA architecture replacement, a proprietary-model reproduction, a fresh generalization test or a claim of equal computation.

## Recovery, source and boundaries

Base checkpoint:5d9df2733f2b04cab9515db8c51c6b37a7443bda, the completed source mathematics phase. That phase reports11 MoDA and9 MoE mathematical tests PASS; this supplies source-readiness evidence, not140M adaptation quality. The preceding loop-index checkpoint is76a78d1d9b3d111a832161bd7360af20383e108a. Preserve all prior results, including the loop-index control comparison that did not support a distinct depth-signal advantage.

Use the designated Codespace bookish-pancake-vwqx7rr9x5w3wxjr only, in a new isolated sparse worktree. Bind its exact branch, execution commit, package/source manifest and accepted base in the operator record before real-model calls. The OpenMythos source is open_mythos/moda.py at d2d6ddd1ca92a1bea31c5807306abf52e0f1aa85, Git blob94f6af593f86410dd20c81510428f5055bd97931,42070 bytes, SHA256335c76d353550cbd3bc409ecfae92141b1ab70265429e0f8e33ccdcb5cd06492. Import those exact verified bytes without editing them.

Upstream sandyresearch/parcae@69284c13746e849104f738d6d1a347b1f457df76, the original model weights/configuration and all historical evidence remain unchanged. No LoRA, loop-index gain, adaptive exit, MoE, threshold adjustment, B1 rerun, A5 relaxation, B2/D2-A, GPU, dependency installation or PR24 operation is part of this phase. All source and model files are read-only inputs; research hooks and new parameters live outside the upstream tree.

## Competing explanations and arms

- F: unchanged official Parcae, fixed32 recurrence, no new branch.
- S: native fixed32 plus a low-width residual sequence-attention branch; no history is read.
- H: the identical residual branch also jointly attends to previous-depth keys/values at the same token position using actual source MoDAAttention.

For each training seed, S and H have identical frozen random features, equal trainable parameters, identical starting function, paired actual h0, data, optimizer and token/step budgets. S versus F tests generic small-branch adaptation. H versus S tests the specific available past-depth information path under this frozen implementation. Both may improve, neither may improve, or the history path may harm quality. More attention work is performed by H; matched parameters do not imply matched FLOPs or runtime. Negative results concern this adapter recipe and budget, not all MoDA designs.

## Exact residual construction

At native width768, instantiate the pinned source MoDAAttention with one query head, one KV head, head_dim16 and dropout0. Its Q/K/V projections map768 to16, and its output projection maps16 to768. The smaller attention inner width is an explicitly validated source configuration, not a change to native Parcae dimensions or attention heads.

Initialization for each training seed4101/4202 is performed inside torch.random.fork_rng(devices=[]), followed by torch.manual_seed(training_seed). Construct, in order: source MoDAAttention with its default Linear initializers; set only its o_proj.weight to zero; construct writerK=Linear(768,16,bias=False); construct writerV=Linear(768,16,bias=False); construct source RotaryEmbedding(dim16,max_seq_len128,base10000). Exit the fork and verify global RNG restoration. The default random draw for the subsequently zeroed o_proj is still part of this construction order. Both S and H independently follow exactly this order and must have matching feature bytes for the same seed.

Freeze Q/K/V and both writer parameters. Train only o_proj.weight:12288 FP32 parameters. The new frozen feature parameters total61440; the complete branch has73728 parameters, excluding deterministic RoPE buffers. Native144323136 parameters remain frozen. No projection biases, dropout, extra normalization, learned gate, learned frequency or feature rescaling are added. The auxiliary RoPE is local to the branch and does not replace or alter native token RoPE or B1's A5 buffer.

Let y_t be the output of the native injection adapter at recurrence t=0,...,31. Before the first native core block, replace the adapter output through a temporary forward hook with:

    y_t + source_attention(y_t, read_keys_t, read_values_t, cos16, sin16)

For H, read_keys_t/read_values_t contain exactly writes from iterations0,...,t-1, in order. For S they are empty at every iteration. Source attention uses one joint softmax over causal current-sequence positions and any supplied same-position depth entries. No independent history softmax is added.

After the second native core block, observe its full output z_t and calculate, for BOTH S and H:

    K_t = source_RoPE(writerK(z_t), cos16, sin16)
    V_t = writerV(z_t)

Reshape each write to[1,1,128,16]. Compute writers in both arms to control their forward work and feature presence; only H consumes the previous writes. The final write at t=31 is intentionally never consumed. All S writes are intentionally unread. These facts must not be reported as missing gradients or missing depth coverage. No hidden state is detached to truncate BPTT. Cache lists are new for every forward and cannot leak across articles, seeds, arms or evaluation calls.

This placement is after native Parcae's adapter and writes after its second core block. It is an inspired residual integration, not a claim that native Parcae's core output equals the post-normalized block output of the full OpenMythos MoDAModel. The original native FFNs and attention remain active. No MoE module is imported into the forward path.

## Fixed data, training and evaluation schedule

Reuse the sealed input JSON /workspaces/mythos-evidence/base_v01/depth_lora/preparation-v1/data/inputs.json unchanged:81885 bytes, SHA256b730b54aa1896227a67e25e6f422ea66f7c9d04ac1a17d98cfef5416d44653cc. It contains16 train and16 validation article windows, each129 tokens, selected from the pinned official WikiText2 raw revision6231e49f19a707241d6b84d9cff60a3a86b85a85. Preserve its source, tokenizer, article identity and train/validation separation checks. No new selection, tokenization, filtering, corpus download or held-out creation is permitted.

These validation articles have now been reused in multiple development experiments. Results are not fresh-test generalization, absence-of-pretraining-contamination evidence, population confirmation or directly comparable to a complete official benchmark. No results may select hyperparameters, samples or training duration.

Each of S4101,H4101,S4202,H4202 receives32 optimizer steps, batch1: articles in frozen order repeated twice, article=step mod16. Inputs0..127 predict targets1..128, all128 targets;4096 training-token presentations per arm/seed. Training h0 seed=1000000+100*training_seed+step, step0..31. Training seeds control both frozen-feature initialization and paired h0 sequences. Trainable output weights start at zero in both seeds. Actual h0 hashes and RNG state must match between S/H at corresponding training steps.

AdamW LR0.001, betas(0.9,0.999), eps1e-8, weight_decay0, foreach=False; global gradient clipping maxnorm1. No scheduler, sweep, early stopping, more seeds, extra steps, training-resume experiment or retry. Native model remains eval with explicit num_steps_pair=[0,32], CPU FP32, gradients enabled for training, all32 iterations in BPTT, no activation checkpointing.

Main execution order: five zero controls (native reference and zero-output S/H for both training seeds),32 F evaluations, then S4101,H4101,S4202,H4202, each32 training steps immediately followed by32 evaluations. This is293 main forward calls and128 optimizer steps. The zero-control case is the first training article with h0 seed6101. Four additional forwards in one new process verify saved adapters on the first validation article with h0 seed5101. Explicit registered controls are not retries.

Evaluate16 validation articles with h0 seeds5101/5202. Input128 tokens; score logits positions64..127 against body tokens65..128, exactly64 targets. Preserve all160 case records:32 F plus32 for each of four trained adapters. Equal-article summaries average the two h0 measurements within each article; the two h0 seeds are not independent articles. Save paired per-article differences, both training-seed results, pooled top1 counts and worst article degradation.

## Compact evidence protocol, fixed before model execution

This phase uses a new explicitly limited evidence policy because retaining another160 complete scored-logit matrices is not admitted by current disk space. Existing raw logits remain untouched. The worker never silently changes case count, score positions, precision or evidence policy after seeing results.

Every scored matrix has shape[64,32768], little-endian FP32 and8388608 bytes. The worker computes source-tensor hashes and score records; an independent NumPy process audits complete raw matrix bytes using FP64 stable logsumexp. No Torch/model import is permitted in that auditor.

1. The32 freshly computed F cases must bridge exactly to the32 sealed original-LoRA F32 raw files: same article and evaluation seed, target hash, shape/dtype/size, complete logit SHA256, actual h0 and RNG-before/RNG-after hashes. Native route counters are recorded and checked as32, but legacy c_proj/core observer field names are not falsely declared identical schemas. Independently audit each freshly generated F matrix in its new temporary file, verify its bridge, then discard only that new temporary file after the same receipt/path/hash checks used for other pending rows. The original32 files remain available for the final full-matrix audit. Do not copy, overwrite, delete or substitute those historical files. A bridge that cannot be established is BLOCKED: report historical baseline equivalence not established, retain the current new raw matrix and stop. Do not label it an implementation failure or adopt a replacement baseline.
2. Keep all four trained sentinel matrices permanently: article0,h0 seed5101, one per arm/training seed,32MiB total. Audit them and use them for new-process reload identity.
3. For the remaining124 trained cases, create one unique new confined temporary raw matrix at a time. Run the independent per-case NumPy auditor and save its complete compact record. Only after auditor PASS, metadata/case identity agreement and rechecking the current raw size/hash against the audited hash may that new temporary raw file be unlinked. Retain a failed or interrupted row; stop downstream work. No historical or sentinel file is eligible for this deletion. Never have more than one unsealed temporary matrix outstanding.

Each row audit has a60-second subprocess limit and records whole-file SHA256 plus eight1MiB chunk SHA256 values and descriptive FP64 chunk sum, sum-of-squares, min and max. Bind all64 target IDs by immutable input SHA256, article ID/index, exact token slice[65:129] and target-vector SHA256; each auditor independently reads those targets from the preserved input file. Do not publish the original target-token vector or source text into Git. For all64 positions save maximum logit, gold logit, shifted logsumexp, logsumexp, NLL, top1 ID, top2 ID and top1-minus-top2 margin. Argmax ties choose the lowest index; top2 is the largest remaining value with lowest-index tie breaking after excluding top1. Compute arithmetic on FP32 values expanded exactly to FP64. The stable NLL is maximum-gold+shifted_logsumexp. Reject nonfinite values or wrong shapes/IDs before scoring.

Compare independent per-token NLL and row mean to the worker's FP64 scores with absolute tolerance1e-10; compare top1 predictions/counts exactly. Record both implementations' values and differences. Stored logsumexp and chunk summaries are descriptive evidence, not substitutes from which original logits can be reconstructed. On an independent audit failure preserve the full current matrix and all reports, mark FAIL and stop.

Final audit verifies all160 unique identities, all32 historical bridges,128 new trained row-audit records, four retained sentinels and reloads, source/checkpoint hashes, target alignment, compact arithmetic identities, training budgets and scientific aggregates. For the32 historical and four sentinel cases it can also reread full logits; for the124 discarded temporary matrices it can audit the sealed live-audit records and hashes, but cannot retrospectively recompute scores from full raw logits. State this limit prominently. Do not claim the same retrospective full-matrix evidence coverage as the earlier LoRA/loop-index experiments. Frozen checkpoints/data permit a separately authorized deterministic reproduction in the future; no reproduction is part of this run.

## Scientific screens and interpretation

Primary H-versus-F practical screen: for EACH training seed, equal-article mean NLL decreases by at least0.01 nats/token and pooled top1 accuracy decreases by no more than0.01 absolute. Both seeds must pass. Apply the same frozen margins to secondary H-versus-S and descriptive S-versus-F. This is an exploratory practical screen, not a significance test or uncertainty-based equivalence conclusion.

Per comparison/seed label IMPROVEMENT when both improvement conditions pass; WORSE when NLL rises by at least0.01 or accuracy falls by more than0.01 absolute; otherwise NO_QUALIFIED_IMPROVEMENT. Keep per-seed labels and report disagreements as MIXED instead of hiding them in an average.

- H/F and H/S both PASS: local evidence favors access to history under this adapter recipe and budget; extra attention cost remains part of the tradeoff.
- H/F PASS but H/S FAIL: adaptation signal without a passing additional-history advantage.
- H/F FAIL: no qualified improvement over native F32, even if H/S passes.
- Negative, unchanged or mixed results are retained and do not trigger tuning or universal claims about MoDA.

Engineering PASS is separate from these screens. A completed scientific screen FAIL is a valid result to seal; it is not an execution failure. Fresh generalization, statistical confirmation, generated-text quality, equal-compute superiority and combinations with LoRA/loop encoding/ACT remain NOT TESTED.

## Engineering acceptance and gradient scope

Before freeze, development fixtures must validate source-style branch equations, writer ordering, causal future-token isolation at fixed full length/h0, temporary-hook cleanup, fresh caches, zero-output identity, feature/init RNG restoration, matched arms, gradient paths, serialization, compact evidence packing and the actual startup interface. Source fixture tolerances do not modify native zero-control or new-process bitwise requirements. Actual zero-output controls must produce logits and h0/RNG identical to native; ordinary addition is not bypassed at zero. A signed-zero mismatch is a real control FAIL, not grounds to relax comparison.

Require exactly32 adapter reads and32 writes, H read lengths0..31 (496 total history entries consumed), S read lengths all0, native two-core call counts[32,32], no current/future write access and new cache objects each forward. Every training step must have finite loss/logits and a present finite trainable output-weight gradient with positive norm; the finite parameter update must be nonzero. Original parameters and frozen feature parameters must keep requires_grad=False, grad=None and identical bytes. Optimizer membership is exactly o_proj.weight. Report trainable12288/frozen61440 counts and unchanged native63 state entries.

Retain the32 per-iteration residual-branch output gradients during training. Require all32 present and finite each step. Capture the16-dimensional input to the output projection for diagnostics only; its diagnostic copy may be detached, but the real attention output/history graph may not be detached. Define each iteration's local output-weight gradient contribution as delta_t.grad.reshape(-1,768).T @ feature_t.reshape(-1,16). Require each contribution finite and each depth's contribution nonzero on at least one step per arm/seed; report coverage. Development explicit-unroll/gradient comparisons use the frozen FP32 fixture bounds atol1e-6,rtol1e-5, including the decomposition into the shared output-weight gradient; native zero/reload controls remain bitwise. The zero-initialized output projection may initially suppress gradients into Q/K/V inputs and history, which is expected. For H, read history entries0..30 must have present finite gradients when their saved tensors require gradients; across post-initial training steps require at least one nonzero history-key and one nonzero history-value gradient per run, and report full per-depth coverage descriptively. Do not require last write31 to have a gradient, or any S writer to have one, because those writes are unread. Gradient presence shows computational participation, not that the path improves quality.

Save initial/final parameter hashes, frozen-feature hashes, every step loss/gradient/update/route diagnostics and final trainable/frozen-feature/optimizer/RNG checkpoint. Reload each of four adapters in a fresh process with exact source/runtime/data and compare its predefined retained sentinel logits, h0/RNG and feature fingerprints bit-for-bit. All declared calls, steps, audits, temporary-file outcomes and checkpoints must reconcile exactly.

Any engineering FAIL or BLOCKED stops dependent work immediately, preserves partial data/current temporary row and writes the actual failed guard; no retry or post-result implementation change. A malformed source/input/old baseline is not fixed by silently replacing it. Save command return codes but do not treat exit0 alone as evidence of correctness.

## Runtime, time and strict disk admission

Existing Python3.12.3/Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op threads, deterministic algorithms, no enabled autocast or new dependency. Record actual CPU/runtime/environment and verify imports retain these settings. No competing experiment worker. Available-memory admission is3GiB; main-worker timeout3600 seconds, per-row independent audit60 seconds. Timeout/interruption is BLOCKED with partial evidence, not a negative quality finding.

Disk admission is328MiB =343932928 bytes, allocated as8MiB live raw row +32MiB retained sentinels +32MiB for ALL remaining new artifacts/copies/checkpoints/Git growth +256MiB untouched reserve. Before any formal freeze or model execution, the initial16MiB artifact proposal was revised to32MiB because complete packaging estimates were not established and the smaller allocation was too tight. This is a documented pre-execution resource correction, not a change to a scientific acceptance threshold or a response to model results. It is not a claim that the32MiB packing proof has already passed.

Before execution freeze, build and measure the planned success-case artifact packing using actual fixture-generated formats, including128 step records,160 row records, all checks and verbatim command/process logs, compact numeric arrays, four complete optimizer/feature checkpoints, protected-file inventories/old manifests, public copies, aggregate audit and Git growth allowance. Freeze that measured forecast in evidence, with bounded serialized finite-float lengths and explicit unmeasured allowances identified. If it cannot fit32MiB, this protocol is BLOCKED: do not silently increase the budget, trim evidence or start the model. Any further redesign requires a new pre-execution protocol/freeze.

At each raw write, checkpoint write and phase boundary, reserve enough bytes for all remaining planned artifacts and preserve256MiB free. Finalization must remeasure actual usage plus pending public/Git copies. Do not create a second large temporary matrix, duplicate original corpora/weights, make a full repository checkout, remove old runs or assume compression savings. Keep newly written full raw data on failure within the allocation and stop.

If a capacity guard blocks continuation, stop all model/optimizer/evaluation work first. A bounded evidence-salvage path may then write only terminal status, errors, preservation records and partial-stage evidence; it need not reserve disk for model stages that will no longer run. It must still check actual writable bytes and the metadata cap, preserve any failed raw matrix, record the triggering budget_snapshot and salvage flag, and report any actual reserve shortfall rather than claiming normal resource compliance. This exception does not relax model admission, permit another forward/optimizer step, authorize a retry or permit deletion of old evidence. Normal successful finalization still requires the full resource/copy/reserve checks.

Report training time, model evaluation time, audit subprocess/I/O time and total wall time separately, plus measured peak memory and evidence size. S computes writers but does not read history; H adds history attention and backward work. There is no equality-of-compute or speedup screen and no CPU performance claim based on this instrumented pilot.

## Checkpoint and next stage

Each phase records Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Git stores protocol, implementation/tests/review, manifest, compact reports, per-case metrics, training curves, independent audit and checkpoint. Original data/model weights, four raw sentinels and adapter/optimizer binaries remain in the new external evidence directory with hashes. Do not export raw corpus or model tensors into Git. The compact evidence limitation and any retained failed temporary matrix must be explicit.

On completion or first BLOCKED/FAIL, commit and push the evidence/checkpoint with exact execution/result commits, branch, environment, actual results, unresolved issues and one next instruction; then stop this phase. State actual completed forward, training and live-audit counts. An early BLOCKED/FAIL checkpoint must not claim that all160 cases were audited or that all124 planned temporary matrices were disposed; unexecuted work remains NOT TESTED. Formal Oracle remains BLOCKED/NOT_READY and FORMAL_ACCEPTANCE_READY=False. After a valid sealed result, the next mechanism is a separately frozen MoE adaptation with its own controls; no MoE, tuning or mechanism stacking is automatically executed by this protocol.
