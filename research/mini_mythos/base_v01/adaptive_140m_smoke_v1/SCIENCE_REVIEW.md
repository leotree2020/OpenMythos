# MYTHOS-ADAPTIVE-DEPTH-140M-SMOKE-V1: planning and scope review

Review date: 2026-11-02. Reviewer: ChatGPT research-review agent in the same project team. This is an internal review, not external, human-independent or Grok review.

**Planning verdict: APPROVE the 55-call CPU mechanism smoke design, with the acceptance clarifications below included before source freeze.** Implementation review and all new 140M checks remain NOT TESTED. This document does not attest to current access to the target Codespace or authorize substitution of another machine for a frozen target.

## Materials actually read

The reviewer read the frozen local `adaptive_depth_v1_work/PROTOCOL.md`, `RESEARCH_DIRECTION.md`, the public model guards and execution/readout paths in `adaptive_depth.py`, and the relevant native h0/hook/causality sections of `test_adaptive_depth.py`. The controller previously verified SHA-256 is `daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8`. The previous final local-development evidence was separately reviewed: 15 tests PASS, including five native-tiny tests; that does not establish official-weight behavior.

The 6-group/55-call proposal and its input selection were supplied by the coordinating agent. At this review's initial read there was no local smoke protocol or runner to review. No target environment, original 140M checkpoint bytes, current upstream checkout, historical sample payload, or newly executed model result was inspected here. Source/hash/context assertions about those items must be established by the new stage's G0 evidence, not inferred from this review.

No torch import, model execution, test execution, source change, network action, package installation or numerical model experiment was performed by this reviewer. Only this review document was added.

## Purpose and competing explanations

The question is narrow: does the already frozen next-token controller preserve the exact pinned native Parcae computation when used with the original 140M checkpoint, including its intermediate readouts, continuation, decision rule and observed work?

Competing explanations for any mismatch are: wrong checkpoint/config/buffers; unsupported environment or native source; h0/RNG mispairing; instrumentation changing execution; a controller continuation/readout defect; or a result-extraction/identity-comparison error. The stage can locate an engineering contradiction; it cannot infer language-quality benefit or the best depth policy.

Preserve the original 63-entry checkpoint state, including buffers, rather than regenerate or replace a buffer to satisfy a different test. A complete state restore and bytewise check here does not erase or relax historical B1 A5. The expected official structural inventory is 144,323,136 unique parameter elements and 61 unique parameter tensors, plus the complete 63-entry state_dict; verify it from the loaded model and original checkpoint, not just a constructor prediction.

## Frozen scope and minimal call schedule

Use historical corrected-input sample 0 only, identified by the exact frozen input-file hash, source article key, heading row, article ID and token/window hashes. Prefixes contain its first 1, 16 and 64 token IDs, with no padding or targets passed to the model/controller. These are mechanism-development inputs, not unseen performance tests. No tokenizer regeneration, article reselection, labels, NLL, accuracy, prose rating, training or threshold selection belongs in this stage.

For each of the 3 prefix lengths and seeds 3101 and 3202, freeze the following nine calls, in this order:

1. Native depth 8.
2. Native depth 16.
3. Native depth 32.
4. Frozen `fixed_next_token` depth 8.
5. Frozen `fixed_next_token` depth 16.
6. Frozen `fixed_next_token` depth 32.
7. Frozen `diagnostic_checkpoints`, continuing 8 to 16 to 32.
8. Frozen `adaptive_next_token`.
9. An independent second `adaptive_next_token` call with the same input and restored pre-call RNG state.

This is 54 calls. Explicitly identifying call 9 as an adaptive repeat removes the otherwise ambiguous word "repeat" without expanding the design. Freeze group ordering too; timing is descriptive, so no order-counterbalancing experiment is required.

Call 55 is one diagnostic call on a changed suffix of the 64-token, seed-3101 group. Reuse the already observed diagnostic baseline from call 7 of that group. Preserve token positions 0 through 31, deterministically change positions 32 through 63 to valid vocabulary IDs, and record both token arrays/hashes and the exact mutation rule before results. All 55 calls must have unique IDs and recorded completion; no hidden warmup, extra model test, retry, threshold adjustment or repair-and-rerun is part of final acceptance.

Use only the unchanged frozen controller import and public functions for model execution. Do not bypass its guards or transplant its private helper into another implementation. The actual source digest, native source pin, import locations, environment, CPU state and checkpoint identities must pass before the first call. No upstream modification, A5 relaxation, B1 rerun, B2/D2-A, GPU or PR #24 operation.

## Required acceptance details

### G0: identity and execution environment

Expected: the target, frozen sources/imports, original checkpoint/config, historical corrected input and dependency environment are all identified; source and state identities pass; batch one, CPU FP32, eval/no_grad, deterministic settings and disabled autocast are observed using getters. Preserve runtime settings around imports and model execution. Record actual Torch/Python/CPU details rather than claiming identity with the local Windows development environment. Observe the actual attention implementation without enabling a backend override.

Missing target access, source files, original bytes, incompatible runtime support, or an unestablished identity is BLOCKED before computation. A demonstrated byte/shape/config contradiction is FAIL. No experiment may be labelled PASS merely because it returned exit code zero.

### G1: actual pairing, observer integrity and readout identity

For each group, restore the same captured CPU RNG state before every call; do not rely only on recording the same integer seed. Observe one actual native `initialize_state` return per call, including its dtype/shape/byte hash and RNG state immediately after it. The observer must not return replacement tensors, consume RNG, or replace native methods: the frozen public guard rejects method overrides. Restore any profiler/hooks in `finally` and preserve exceptions.

Require the actual h0 bytes, pre-call RNG bytes and post-call RNG bytes to agree across that group's nine calls. Require wrapper-reported h0/RNG hashes to match the independently observed values. Pairing is within one prefix group: h0 has different shapes for lengths 1, 16 and 64, so equal h0 hashes across different lengths are neither expected nor required.

At all three depths, native final-position logits, fixed-depth logits and the corresponding diagnostic checkpoint logits must match dtype, shape and bit patterns, with rtol=atol=0 and signed-zero distinctions preserved. The adaptive selected-depth output and each of its emitted checkpoints must equal the matching native/fixed/diagnostic outputs. No approximate tolerance is allowed for these identity checks. All inspected model outputs, TV and times must be finite, with positive elapsed time.

Native controls must use the native fixed-depth entry point with the correct explicit depth argument, not the controller as its own reference. Head hooks see the raw `lm_head` output: compare raw outputs to raw outputs for hook-based controls, and compare public outputs after the same native float conversion and `init.logit_scale` operation. Do not silently equate these two output stages.

Record whether pre-existing temporary input-ID bookkeeping exists and verify the frozen wrapper restores its original existence/object after each invocation. Preserve caller input bytes and the full model state across the stage. No claim of disk/cross-process resumability follows from same-call continuation.

### G2: decision, repeat and actual work

Recompute TV from saved final-prefix-position depth-8/depth-16 logits using the frozen FP64 formula, or independently verify their exact computed decision inputs without reading any labels. Require the rule to select 16 precisely when TV <= 0.01, otherwise 32; TV must be finite and in its valid range. Save the literal threshold and selected depth. The repeat must reproduce logits, checkpoints, selected depth, TV, h0/RNG and deterministic call counts exactly; walltime is not expected to be identical.

Use observational module hooks to measure work on every native and wrapper call, and compare overlapping observed counts to the wrapper's explicit accounting. Count h0 and recurrent update invocations through a nonmutating observer where module hooks do not exist. A counter declared by the wrapper alone is not an independent cost observation. Label the single policy evaluation separately as execution accounting; do not misdescribe it as a module-hook observation.

For native 2/2/2 blocks the required ledger is:

| Call | Prelude blocks | Core blocks | Coda blocks | Total blocks | Readouts / head calls | Policy evaluations |
|---|---:|---:|---:|---:|---:|---:|
| Native/fixed 8 | 2 | 16 | 2 | 20 | 1 | 0 |
| Native/fixed 16 | 2 | 32 | 2 | 36 | 1 | 0 |
| Native/fixed 32 | 2 | 64 | 2 | 68 | 1 | 0 |
| Diagnostic 8 to 16 to 32 | 2 | 64 | 6 | 72 | 3 | 0 |
| Adaptive/repeat selecting 16 | 2 | 32 | 4 | 38 | 2 | 1 |
| Adaptive/repeat selecting 32 | 2 | 64 | 6 | 72 | 3 | 1 |

Also report embedding, h0, recurrent adapter/update, projection and normalization observations separately. Prelude/h0 run once, not once per checkpoint. The suffix diagnostic has the same ledger as the original diagnostic. No 17-to-32 core execution may occur after a selected depth-16 exit. No restart at depth 8 or 16 is permitted.

Both natural adaptive branches need not occur in these six inputs. All-16 or all-32 selection is neither a failure nor success evidence for quality. Report the observed branch coverage and leave any unobserved real-weight branch NOT TESTED; do not change thresholds or add samples to force it. Synthetic branch coverage from the prior stage remains separately labelled.

Walltime must surround the complete public/native call, including wrapper validation, finite checks, hashing, clone/readout work, policy and instrumentation performed inside that interval. State any setup/seed-reset/serialization excluded from the timer. This is an instrumented smoke-check duration, not a throughput benchmark, FLOP estimate, speedup claim or fair routing-efficiency comparison.

### G3: nonvacuous causal suffix control

For call 55, require the mutated input to keep its length, first 32 tokens and RNG initialization unchanged while actually altering suffix tokens. The observed h0 and relevant RNG states must match the original 64-token diagnostic. At depths 8, 16 and 32, compare the full-vocabulary head-output slice for positions 0 through 31 bytewise to the baseline slice captured during its existing call; no extra baseline run is needed.

Require at least one observed suffix-position logit to differ across the baseline and mutation, and report per-depth suffix-change status. If every observed output is unchanged, the causal test is noninformative: mark that control BLOCKED, do not declare causal success and do not try another mutation. A changed earlier-position logit is FAIL. This control checks a specific suffix intervention; it is not a general theorem about every length/input/backend.

Do not use diagnostic full-prefix hooks to change the public API or score earlier teacher-forced positions using an adaptive decision based on later input. Full-prefix capture is solely an instrumented causality check here.

### G4: completion, preservation and stop rules

Expected: exactly 55 planned, uniquely identified calls; all required comparisons and ledger checks PASS; original loaded state restored byte-for-byte at the start and unchanged afterward; source/upstream/input/config/checkpoint and recorded dependency inventory unchanged; actual runtime remains within the frozen supported settings. Preserve per-check Purpose, Environment, Input, Expected, Actual and Status, plus stdout/stderr, exceptions, source manifest and checkpoints.

On the first BLOCKED or FAIL, stop further model calls, preserve all already produced evidence and the failed comparison, perform only non-model cleanup/preservation recording, and write a terminal checkpoint. A missing or truncated final record can never establish PASS. Do not convert missing evidence into zero differences or rescale an acceptance threshold. If a source fix becomes necessary, it needs a distinct stage/run identity and review; it is not a retry of this frozen acceptance.

## Result interpretation and remaining boundaries

| Outcome | Permitted conclusion | Next step |
|---|---|---|
| All engineering controls PASS | The frozen controller preserves native official-weight outputs for these paired prefixes and implements the stated stopping/accounting semantics | Consider a separately frozen quality/cost trial; no automatic performance claim |
| Any established contradiction FAIL | A specific identity, pairing, continuation, causal or accounting requirement was violated | Preserve evidence and diagnose that minimal contradiction; do not continue or tune |
| Missing prerequisite/coverage/identification BLOCKED | This acceptance could not be established | Preserve evidence and resolve that prerequisite under an explicit new execution record |

There is no improvement/no-difference/worsening quality decision in this smoke stage because no quality endpoint is measured. The value 0.01 remains arbitrary and uncalibrated; agreement or disagreement between predictions does not identify which prediction is correct. Six paired groups from one historical article are not independent language-generalization samples, and the two h0 seeds are not training replications.

A future performance protocol needs prefix-only targets unseen by routing, fixed16/fixed32 references, an appropriately matched random-routing control, source-level uncertainty, fully observed total cost including readouts and routing, and preregistered improvement/no-difference/worsening interpretations. It must not select its policy from these historical outcomes or treat this tiny engineering smoke as the performance trial.

Current status: implementation review NOT TESTED; target access and G0 NOT TESTED; all 55 calls NOT TESTED; mechanism validation NOT TESTED; quality improvement and hardware efficiency NOT TESTED; training recovery NOT TESTED; Claude Mythos parity NOT TESTED. Historical B1 A5 and Formal Oracle statuses are unchanged. This is an untrained heuristic controller on native Parcae, not learned OpenMythos ACT or evidence about a private Claude architecture.

## Follow-up: actual protocol text review before implementation freeze

The local `PROTOCOL.md` is now available and was read in full. The reviewed corrected revision is 8776 bytes, SHA-256 `7e2bd899a9eec98844fd959adf284b1cf925771f812aedc962cdf5fa3c65416d`. Its base checkpoint is `5c2c46451b166426fe68ddabef72c69ab7f97dca`. **The protocol-text verdict remains APPROVE.**

The written protocol fixes the target Codespace and existing Python 3.12.3 / Torch 2.11.0+cpu interpreter, CPU FP32 and FP64 policy, threads 2/1, resource and exclusivity checks, timeout, original artifact identities, corrected historical input identity, source freeze and no-retry rules. It agrees with the six-group, nine-calls-per-group plus one suffix-control design, and explicitly defines the independent adaptive repeat. The raw-head causal reference, nonvacuous suffix contrast, no need to force both natural branches, full-cost reporting limits and separation from a performance trial are present.

The state-inventory wording was corrected during pre-freeze review: 61 unique parameter tensors have 62 registered parameter paths because of tied embeddings; `freqs_cis` is the one registered persistent buffer, making 63 state_dict entries. "Both buffers" was a documentation mistake, not a reason to change the actual model or acceptance inventory.

G4's independent scalar-softmax TV check uses absolute difference <= `1e-12`, with relative tolerance zero. This is acceptable for agreement between two different FP64 arithmetic implementations over saved FP32 final logits. It is not a tolerance on model-output identity and does not change the controller's literal `TV <= 0.01` predicate. Near-threshold distance and, if relevant, any side difference in independent recomputation should be reported without changing the selected depth or inventing a new fallback. The executed branch is assessed against the frozen controller's own recorded finite FP64 TV; the scalar reference validates that value within the declared arithmetic tolerance. All native/fixed/diagnostic/output identity checks remain bytewise exact.

Preliminary worker inspection also identified implementation-contract details for the implementation author to close before freeze: classify a known unsupported-model guard rejection as FAIL as specified by G1; observe value-embedding calls as promised by G2; and compare repeated recurrence-state hashes as well as decisions/counts/logits. These findings require no additional model calls. They do not constitute a runtime failure: no original-weight computation has been reviewed or executed here. A final worker revision must be identified separately before an implementation APPROVE is recorded.

The coordinating agent reports that the target interface is now reachable and that preliminary read-only resource/source checks have been made. This reviewer has not independently inspected that target evidence, so the preceding target-identity limitations still apply. New model execution and performance remain NOT TESTED in this review.

## Follow-up: worker scientific and observer-contract review

Reviewed worker: `run_smoke.py`, 41105 bytes, SHA-256 `1dd04c120e0a7815b8464ac6b0f50260845c38d3c974379c0a105ac5c3190eab`. Its helper-test file identity is `test_smoke_helpers.py`, 9164 bytes, SHA-256 `d13f47b9d0a32a83ffc40dedd05a9c436e290d19434d7f2ddbcbf2c5a60557b1`. **Worker scientific/observer-contract static verdict: APPROVE.** This verdict does not cover an unread independent auditor or operator revision, and is not a runtime PASS.

The worker resolves the preceding findings. A frozen-controller configuration rejection is FAIL. The original-model inventory requires value-embedding keys `1`, `3`, `5`; hooks observe those modules, with expected calls `1 + selected_depth + readout_count`. Both the repeated adaptive state hashes and independent native projection-input state hashes are checked. Repeated h0 initialization fails explicitly before trying to write a duplicate raw-artifact filename.

The actual fixed schedule has 54 group calls followed by the one reused-baseline suffix control. Native references invoke the pinned model's explicit depth interface. The unchanged public controller supplies fixed, continued and adaptive paths. Profiling observes the real native h0 return without replacing a method, and module hooks return no replacement output. h0 and pre/post RNG pairing are checked using saved raw bytes as well as hashes. Observed recurrence-state hashes are compared across each corresponding native and continued readout. Final outputs are compared as raw tensor bytes, and the repeated decision includes selected depth, TV, counts, state hashes and output bytes.

The suffix control captures raw head values on the existing baseline and mutation call at all three depths; it compares the unchanged first 32 positions, verifies actual h0/RNG pairing and requires a nonzero suffix contrast. The observer cleanup, temporary input bookkeeping, caller-input preservation, official-state restore, full coverage, post-stop state/config/source/runtime/inventory preservation and incomplete-result handling are explicit in the inspected worker. No control adds another model call or silently changes the 0.01 rule.

These native/reference calls are instrumented. Static inspection finds observational hooks/profile code and RNG-consumption checks, but the 55-call budget contains no additional uninstrumented official-weight no-op comparison. Report instrumented native identity rather than claiming that an extra uninstrumented 140M control ran. The earlier tiny-model observer controls remain separate evidence.

The two timing fields have specific scopes: `api_observed_seconds` covers hook installation, model/public API execution, internal observers, wrapper checks and cleanup; `call_total_seconds` additionally includes per-call result validation and raw-output/RNG writing before final call-record serialization. Seed/RNG setup and pre-timer input snapshots, later group comparisons and final sealing are outside those intervals. Neither timing is a pure inference benchmark. Recurrence, projection/head and value-embedding hook counts are observed module-work counts, not an exhaustive FLOP count of every internal normalization or arithmetic operation.

The implementation agent reports nine standard-library helper tests passed, without torch/model execution. This reviewer did not rerun or independently inspect the final helper-test result artifact, and makes no additional test-result certification here. The independent saved-evidence audit, outer custody/freeze checks and all actual 140M results must still pass their own gates. There are no remaining scientific-design objections to freezing this identified worker once those separate reviews are satisfied.

## Final worker exception-classification amendment

The subsequent worker revision is `run_smoke.py`, 41462 bytes, SHA-256 `f29155eb3af5989a1da1f938dc2b7e7ca894a2dc960a0eefb6e4352517d0a37c`. It supersedes the preceding worker identity for the static APPROVE. The reviewer read the six-line exception-classification change: a rejected frozen-call value/configuration invariant, or the explicit library exceptions for readout-state mutation, readout RNG consumption and policy RNG consumption, is now FAIL. Unexpected runtime/access/resource failures retain their distinct treatment. The original exception type and reason remain in the recorded Stop details. This closes a status-classification gap without changing the candidate's arithmetic, thresholds, call schedule, raw-output schema or model behavior. **Worker scientific/observer-contract verdict remains APPROVE.**

## Independent auditor initial review

The reviewer read `audit_smoke.py` in full at 17985 bytes, SHA-256 `e81d5ce312f727ed2f303eb38c87af7bf81beebbab0500a517947c8f51ab0c5f`. The scalar softmax uses subtraction of the maximum and `math.fsum`; it decodes saved little-endian FP32 values, verifies the six paired TVs within the frozen absolute arithmetic tolerance, and assesses the selected branch against the recorded controller TV. It reports a possible near-threshold scalar-predicate disagreement without moving the threshold. The native/reference byte comparisons, 55-call order and causal baseline call 43 versus mutated call 55 are consistent with the protocol.

The initial auditor review requested minimal evidence/wording clarifications before an auditor APPROVE:

- Bind every row's input hashes to the appropriate slice of the actual original64 token sequence, rather than only requiring within-group hash agreement. Bind that sequence to the corrected sample-0 artifact and its fixed SHA-256. Otherwise a consistently wrong prefix within one group could pass the independent input audit.
- Distinguish the worker's original full-checkpoint byte comparison from the auditor's equality/recomputed-aggregate checks on saved state inventories. The standard-library auditor does not independently reconstruct the original PyTorch checkpoint or re-read every live parameter tensor. Its state-preservation conclusion is an evidence-consistency check on worker-generated snapshots, not a second model-load experiment.
- Retain BLOCKED for an incomplete or explicitly blocked worker when using the auditor as a general entry point, or explicitly constrain its invocation to successful worker records. Do not recast a missing prerequisite as a proven numerical contradiction solely because the completed-worker precondition fails.
- Describe the timing sample as six prefix/seed groups from one historical article: there are three prefix lengths and two initializations, not six independent text sources. Suffix sensitivity is checked from recorded suffix digests; the unchanged earlier-position prefix has saved raw bytes for independent comparison.

These are data-only audit and interpretation changes; they require no new forward pass and no controller change. The initial auditor revision is therefore not included in the worker APPROVE. No new model or test execution was performed during this review.

## Final independent-auditor revision review

Reviewed final auditor: `audit_smoke.py`, 19740 bytes, SHA-256 `94d4d53096deb3b6bd666de4e15d739f631b2bb9bb263e41fe533d2e6031f6b7`. **Scientific/evidence-scope static verdict: APPROVE.** This supersedes the initial auditor's pending findings, not any actual runtime status.

The revised auditor reads the original `spec.inputs_path`, requires the fixed corrected-input SHA-256 and matching protected-file identity, validates sample 0 and its 257 token IDs, and independently constructs each of the 55 expected prefixes. It compares both canonical nested token-array hashes and explicit little-endian int64 byte hashes for every call, including the frozen suffix mutation. The saved private original64 sequence is also tied back to that fixed original input. This closes the internally-consistent-but-wrong-prefix gap without tokenization, new samples or a model call.

The revised exception handling retains BLOCKED for missing files and explicitly incomplete/blocked worker results. A worker claiming PASS while contradicting coverage or another required field still fails the independent audit, correctly distinguishing an incomplete execution from a contradictory success claim. An explicit worker FAIL remains a failure.

The result now states that full original-weight tensor comparison belongs to the worker, whereas the independent auditor verifies the before/after digest inventories. Its timing limitation correctly identifies six paired prefix/seed groups from one historical article. The previous TV, signed-byte comparison, natural branch coverage, state-hash, raw-prefix causality and recorded suffix-sensitivity interpretations remain appropriately limited. The audit neither changes the stopping predicate nor reports language-quality or hardware superiority.

The coordinating agent reports five standard-library audit fixtures PASS, including a complete synthetic 55-call case, rejection of a signed-zero output alteration despite re-signed manifests, and rejection of deleted coverage. This reviewer did not rerun those fixtures or load a model. The static verdict covers the inspected source and scientific/evidence interpretation; actual formal results, outer operator custody and publication binding still require their own recorded checks. No additional experiment or review-driven model call is required by the resolved findings.
