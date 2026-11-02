# Future mechanism-4 quality pilot: compact evidence design memo

Status: **PLANNING / NOT TESTED**. This memo does not authorize a real-weight
quality run. First finish the current loop-index experiment, then accept separate
MoDA/MoE mathematical and gradient controls. Each later quality experiment needs
its own protocol, implementation review, execution freeze, resource preflight,
single-run evidence, and checkpoint. No existing frozen protocol is changed.

## Purpose and sequence

Test the mechanisms separately before stacking them. A negative quality screen
is valid experimental evidence. A broken implementation, mismatched baseline,
nonfinite value, missing evidence, or insufficient resource is a different
engineering failure or blocker.

1. CPU synthetic mathematical/gradient verification of each proposed new path.
2. A standalone memory-path pilot inspired by MoDA, with a controlled comparator.
3. A separate MoE pilot, with controlled routing/expert-capacity comparisons.
4. Only after reviewing these results, a separately frozen combination study.

Keep native Parcae files and weights unchanged. Use isolated research modules.
Do not add LoRA, loop encoding, or early stopping to these first standalone
quality comparisons. Do not operate on PR #24 or change old experiment evidence.

## Candidate input and compute scope

The proposed common development benchmark is the already frozen 16 training and
16 validation article introductions, 129 tokens each. Training uses the first
128 next-token targets, batch one, full native 32-step BPTT. Evaluation scores
the final 64 target positions at h0 seeds 5101 and 5202. Two training seeds and
32 optimizer steps per trained model give four trained models, 128 optimizer
steps, and 160 final evaluation rows including F32. These budgets must be
confirmed in the actual future protocol rather than inferred from this memo.

The validation articles have already been used to compare mechanisms. They are
a reused development benchmark, **not a fresh generalization test**. Two h0
realizations do not make 16 articles into 32 independent samples. Training seeds
and h0 seeds are paired within each controlled contrast. Unknown pretraining
overlap remains unresolved. Freeze hyperparameters before evaluation; no tuning
against this run's validation result.

## Evidence strategy and its explicit limitation

Each final scored tensor has shape `[64,32768]`, dtype little-endian FP32, and
contains 8,388,608 bytes. Saving 160 complete new tensors would require
1,342,177,280 bytes. The proposed new protocol instead uses a bounded temporary
raw file and performs an independent NumPy FP64 audit while the full tensor
still exists. It then retains a compact audit receipt and predeclared raw
sentinels. This is a **different evidence-retention design for a new protocol**,
not a relaxation of a previous experiment's retention requirement.

The retained compact metrics cannot reconstruct the missing full vocabulary
distributions. Hashes bind bytes that were observed; they do not recreate those
bytes. Chunk sums or moments are diagnostics, not substitutes for logits.
For the 124 nonsentinel trained-model rows, this design supports the statement
"the complete logits were independently audited during the run". It does not
support "all final logits can be independently recomputed from the retained
evidence after the run". Later full replay would be a new authorized run, not
retroactive replacement evidence for this one.

### Baseline bridge: no new baseline storage

For each of the 32 newly computed F32 evaluation rows, compare:

- full scored-logit byte size, shape, dtype, and SHA-256;
- exact article/target identity and scored-target SHA;
- actual h0 SHA plus the applicable before/after RNG-state hashes;
- pinned data, model, upstream, and environment identity.

All must agree with the corresponding immutable F32 row already retained in the
depth-LoRA experiment. The new evidence manifest references those existing raw
files and the pinned old evaluation manifest, without copying or modifying them.
This preserves complete baseline re-audit capability.

If the bridge does not match, label **BLOCKED: historical baseline equivalence
not established**, retain the current raw file and all discrepancy records, and
stop. Do not silently switch to a weaker baseline-evidence mode or overwrite the
old data. The old full tensors and old manifests remain intact.

### Candidate rows and reload sentinels

For each of the four trained models, retain the full raw scored tensor for the
first frozen evaluation article at h0 seed 5101. Selection is fixed before the
run; no representative or best-looking examples are selected afterward. These
four sentinels total 33,554,432 bytes and support four fresh-process predictive
reload checks. They do not prove all-input reload identity or training-resume
trajectory identity.

Each of the remaining 124 trained-model raw rows is temporary. The operator:

1. Creates a uniquely named raw file exclusively under the new attempt's
   dedicated temporary directory; it never reuses an old experiment path.
2. Finishes and closes the write, recording exact shape/dtype/size/hash.
3. Runs the frozen independent auditor in the existing NumPy environment without
   importing Torch, model code, or the worker scoring implementation.
4. The auditor reads the frozen source data independently, selects the scored
   targets by frozen article index, and checks the target hash and complete raw
   file before computing metrics.
5. Persists the auditor receipt and compact per-token evidence, including the
   receipt's own hash in the append-only manifest. The operator verifies that the
   completed receipt reports PASS for the expected row and raw SHA.
6. Only after successful durable recording removes that newly created temporary
   raw file according to the preregistered retention policy. It then advances to
   the next row. At most one nonsentinel raw file is pending.

No deletion follows a failed or incomplete audit. On FAIL, BLOCKED, timeout,
write failure, missing receipt, or identity mismatch, preserve the current raw
file and partial records and stop. A failure to remove an already audited new
temporary file also stops advancement, so disk consumption cannot accumulate.
There is no blanket cleanup of old evidence or temporary files from other runs.

## Compact records and independent checks

Retain per row the full raw SHA, raw byte count, row identity, model/adapter/data
pins, h0/RNG hashes, scored target IDs and target SHA, and the ordered per-token
results of both the worker and independent auditor:

- FP64 NLL;
- FP64 maximum logit, target logit, and shifted log-sum-exp term, permitting a
  stable subtract-first reconstruction of the stored NLL;
- FP64 log-sum-exp if also reported, explicitly distinguished from the stable
  shifted term;
- top-1 index/value, top-2 index/value, and top-1 minus top-2 margin, with frozen
  deterministic handling of exact ties;
- finite-value counts and the sum/count needed to reconstruct row and article
  aggregate metrics.

Use compact column arrays instead of repeating field names per token. JSON float
serialization must round-trip finite FP64 values without intentional rounding.
Independent NLL comparison retains the previous `1e-10` absolute margin; top-1
IDs, target identity, byte count, and raw hashes match exactly. The new protocol
must specify whether it checks each token as well as row aggregates; per-token
agreement is recommended to prevent compensating aggregate errors.

If chunk summaries are included, use eight ordered 1MiB chunks per raw file,
each recording SHA-256 and FP64 sum, sum of squares, minimum, and maximum over
the interpreted FP32 values. This compact form avoids a large token-by-vocabulary
block JSON expansion. Such summaries cannot verify the full distribution after
its original bytes have been discarded.

Aggregate screens and article differences can later be recomputed from the
retained per-token independent metrics. This is valid metric-aggregation audit,
distinct from recomputing those metrics from complete logits.

## Resource envelope

Proposed worst-case storage floor:

| Component | Bytes |
|---|---:|
| One pending raw tensor | 8,388,608 |
| Four permanent reload sentinels | 33,554,432 |
| Proposed metadata/checkpoint allowance | 16,777,216 |
| Reserved free space | 268,435,456 |
| Total | **327,155,712** |

The total is 312MiB. The 16MiB allowance is **not yet validated**: it must cover
run summaries, training/gradient records, four adapter plus optimizer/RNG
checkpoints, public evidence copies, Git objects, and temporary serialization
overhead. Before freezing a quality experiment, bound this size from its exact
parameterization and representative synthetic serialization. If it does not fit,
increase the preregistered resource floor and potentially record BLOCKED; do not
remove required fields after seeing results. Limit the new checkout to required
sources, without duplicating old raw evidence or large historical evidence trees.

Before every new raw write, require sufficient free bytes for that file plus the
reserved floor. Account for future permanent sentinels and checkpoint writes at
their creation boundaries. Preserve old files even if the next experiment cannot
fit. MoE gets a fresh resource preflight after the memory experiment; neither
experiment may assume the other's storage is available for reuse or deletion.

## Scientific controls for the memory-path pilot

The exact residual memory module is not fixed by this memo. A low-rank external
residual inspired by MoDA must not be called a full faithful MoDA implementation.
The original mechanism's single softmax over current-sequence and prior-depth
same-token KV is a specific design, not any arbitrary recurrent memory.

The baseline and trained comparator must distinguish pretrained adaptation from
the benefit of access to additional depth states. Matching only nominal parameter
count is inadequate if a control deliberately makes some trainable projections
inactive. Report both trainable and gradient-active parameter counts. A same-size
current-state adapter can be a useful adaptation control, but differences in
function class, active computation, and optimization remain explicit.

Do not use a permutation of unordered memory slots as an alleged strong control
if the attention implementation is mathematically permutation invariant without
slot-position information. A frozen shuffled or removed-memory inference
intervention may show dependence of trained weights on a path; it cannot by
itself establish why training improved because of coadaptation.

Mathematical controls precede real weights: exact explicit attention reference,
proper masks, no future-token path, depth-zero/no-history behavior, stable single
softmax normalization, output and gradient agreement, finite complete depth
gradients, zero-residual native identity, and immutable native state.

## Scientific controls for the later MoE pilot

Separate expert capacity from learned routing. A useful future matched-capacity
comparison is the same experts, same top-K active count, and same trainable router
against a preregistered balanced fixed subset schedule whose within-subset mixture
weights remain trainable. This tests learned expert selection more directly than
comparing MoE with an untrained or smaller dense baseline. It still needs precise
implementation review; merely computing a router and discarding all its outputs
would not produce a meaningful matched trainable control.

Record parameter count, active experts per token, actual routing assignments,
load distribution, gate entropy, expert/router gradient coverage, clipping, and
optimizer budgets. Frozen initialization, tie handling, and any load-balancing
loss are part of the protocol. Do not insert balancing changes after observing
collapse. Expert collapse is generally a scientific/optimization outcome when
the implementation correctly follows its protocol; nonfinite tensors or a
misimplemented router are engineering failures. Freeze that distinction before
running.

Fixtures cover independent top-K/mixing math, tied gate logits, routing gradients,
inactive-expert behavior, weighted expert aggregation, causal behavior, capacity
and token accounting, and zero-residual native identity.

## Acceptance and interpretation

Every stage records Purpose, Environment, Input, Expected, Actual, and explicit
PASS / FAIL / BLOCKED / NOT TESTED. No stage passes solely on process exit.

Engineering acceptance requires exact frozen coverage, correct data/target
alignment, no nonfinite values, base preservation, complete independent live
audit receipts, required raw sentinels, and fresh-process sentinel reload identity.
All intended raw discards and all retained raw references are recorded. Missing
rows remain NOT TESTED after an earlier stop rather than being filled by retry.

The proposed quality screen remains exploratory: both training seeds must improve
mean NLL by at least 0.01 nats/token while losing no more than one percentage point
of top-1 accuracy. Give per-seed and per-article changes, worst-article change,
and explicit improvement / no qualified improvement / worse / mixed labels.
Do not average opposite seed effects into a positive declaration. This is not
statistical confirmation, equivalence, production usefulness, or generalization.

Report timing in two scopes: model training/inference work and full experiment
wall time including audit and I/O. Sequential per-row audit avoids concurrent
auditor load contaminating model timing, but a small quality pilot's timings are
still descriptive. A claim of speed or equal-compute superiority needs a separate
balanced, warmed, repeated timing protocol with actual active-compute accounting.

Next decision: accept the separate CPU mathematical/gradient stage first. Only
then choose and freeze a real-weight memory-path quality protocol with an exact
parameterization and verified evidence-size budget. This memo starts no run.
