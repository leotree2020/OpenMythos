# Scientific-scope review — MYTHOS-ADAPTIVE-DEPTH-DEV-V1

Verdict: **APPROVE for the bounded development stage described below.** This is a protocol/scope review, not implementation acceptance or a performance result. All new implementation, synthetic execution, native tiny execution and original140M validation remain **NOT TESTED** at the time of this review.

Reviewer: internal agent `/root/eval_science_review`. The reviewer previously contributed project evidence-audit helpers; this participation is disclosed and does not constitute an additional experimental replication.

## Materials actually read

- Local `PROTOCOL.md`, SHA256 `c9c7473cc1d4fa06ea04f3832498fcccc24bf819e2c4eac02561680e7dc8456b`.
- Local `RESEARCH_DIRECTION.md`, SHA256 `e66a889a0cefc5acd0ebb48d0cee50ed02180f13b6f8769d2c23919d4037a4fd`.
- In the immediately preceding read-only review, the GitHub connector returned the depth16/32 branch's [checkpoint](https://github.com/leotree2020/OpenMythos/blob/mythos-depth-16-32-cpu-v1/research/mini_mythos/base_v01/depth_16_32_v1/CHECKPOINT.md), [protocol](https://github.com/leotree2020/OpenMythos/blob/mythos-depth-16-32-cpu-v1/research/mini_mythos/base_v01/depth_16_32_v1/PROTOCOL.md), and runner observation/control code. The checkpoint reports PASS and execution freeze `4d6937de612ec20009143a46773b6d04532db84b`. This review did not rerun or independently re-audit that experiment's numerical evidence.
- Local pinned-source reference `mythos_parcae_pinned/parcae_lm/models/parcae/parcae.py`: native forward/readout, recurrence iteration, initialization and core update. Local `mythos_pr12/open_mythos/main.py`: `ACTHalting` and `RecurrentBlock`. These reads support the mechanism distinctions below, not a claim about another model's private architecture.

The two development documents identify base checkpoint `c63b829a752ac57d22addfe17ff53ecbcb58e8a0`. The operator reports the new branch and protocol commit `851abc0f`; this review has not independently resolved those remote references. The Anthropic transparency-page facts quoted in `RESEARCH_DIRECTION.md` were not re-opened in this review. This verdict concerns the scientific boundaries of our development plan, not a new verification of that product description.

## Accepted boundary and retained distinction

**Accepted: this stage continues native recurrent computation inside one inference invocation and one process. It does not expose serialization, a reusable cross-call state-resume interface, disk continuation, or training checkpoint recovery.** The protocol's phrase "resumed native path" is interpreted only as continuing the same in-memory state from8 to16 and, when selected,32.

An earlier reviewer suggestion included serializing intermediate state and testing a new-process restart. That requirement is withdrawn for this narrower stage because persistence is not an offered feature. There is no unresolved objection to omitting those tests. The retained boundary is strict: the implementation and checkpoint must not advertise crash recovery, disk-resumable inference, or resumable training. Those features require a separate protocol covering their own state/RNG/data-position contracts. Same-call continuation alone establishes none of them.

This reduction preserves the central acceptance question: do intermediate prediction readouts and the branch decision leave the native recurrent trajectory unchanged up to the chosen stopping depth?

## Scientific judgment

The sequence of deliverables is appropriate: validate execution control first, validate it against original140M next, and test usefulness under a separately frozen quality protocol afterward. The prior depth experiment motivates investigating selective computation; it does not validate this policy. Adding an untrained learned halting gate or adapters would introduce new unsupported variables and is correctly excluded.

The policy is a fixed heuristic: compare final-prefix-position distributions at8 and16 using FP64 total variation, exit at16 when `TV <= 0.01`, otherwise continue to32. It cannot exit at8. The threshold is an arbitrary engineering baseline, not a calibrated correctness guarantee, a bound on NLL degradation, or a quantity selected from the existing article results. Stable distributions can be confidently wrong, and small total variation need not imply a small log-loss change for a rare target token.

OpenMythos supplies an adaptive-computation research idea. Its learned halting/weighted-state implementation is not transplanted here. Neither development-test success nor that provenance establishes Claude Mythos architecture or capability reproduction.

## Required interpretation of the engineering acceptance

1. **Prediction boundary and causality.** The public prediction API must return only the distribution/logits for the token after the complete supplied prefix. It must not offer earlier-position logits as predictions selected by a last-position routing decision. The controller accepts no labels or scoring callback. A whole teacher-forced window cannot use its last-position decision to score earlier positions: future input tokens would influence that choice even without an explicit labels argument.

2. **State identity.** Continue from the raw recurrent hidden state, never from a projected/Coda/normalized/head output. Compare fixed8/16/32 controls and the corresponding continued states under identical actual h0 and CPU RNG. Preserve caller inputs, parameters, buffers and temporary native input-ID bookkeeping on both success and injected failure. Each invocation initializes exactly once; no state may leak to another invocation.

3. **Readout identity.** Intermediate readouts operate on an isolated state copy, consume no RNG and do not alter subsequent recurrence. An internal full-prefix readout is allowed to preserve native operation shapes; only the final position is exposed by the prediction API. Changing matrix shapes to optimize last-position computation must not be presumed bitwise equivalent: the fixed native comparison is the arbiter, and its identity threshold must not be relaxed.

4. **Policy arithmetic.** The declared tolerance for comparing an independent scalar probability/TV reference must be frozen before final acceptance. It applies only to that numerical test; the branch predicate remains exactly `TV <= 0.01` in FP64, with no added epsilon. Shape, dtype and nonfinite guards must have explicit outcomes. Test equality and values on both sides of the threshold, as well as stable-but-wrong synthetic distributions. Such a fixture can pass controller semantics without passing any quality hypothesis.

5. **Actual work, not nominal depth.** Fixed16 and fixed32 have36 and68 native block calls. Adaptive16 has38 and adaptive32 has72 because intermediate Coda readouts also execute. Projection, normalization, head and policy calls must be reported separately. A16 exit must execute no later core calls; a32 route must continue once rather than recomputing full8/16/32 forwards. These counts do not establish FLOPs, latency improvement, or hardware efficiency.

6. **Source/version limitation.** The observation that the pinned native core does not use `total_steps` to change its computation is specific to the inspected path. Unsupported source/configuration variants must be rejected; it is not a general theorem about recursive models. Optional native tiny tests are a separate evidence category from synthetic fixtures and original140M tests.

## Stage status and later decisions

| Purpose | Environment / Input | Expected | Actual at review | Status |
|---|---|---|---|---|
| Review scientific scope and same-call continuation boundary | Read-only documents and source excerpts listed above | Correctness stage separated from performance and persistence claims | Boundary accepted; no additional persistence requirement | PASS, review scope only |
| Implement and test the controller | Local CPU synthetic/tiny inputs | Frozen numerical, identity, causality and count assertions | No implementation or execution reviewed here | NOT TESTED |
| Validate original140M continuation and actual cost | Designated Codespace, original frozen weights | Separate native identity/cost protocol | Outside this stage | NOT TESTED |
| Establish quality/cost benefit | Separately frozen prefix-only evaluation | Fixed16/fixed32 and appropriately budget-matched random routing controls | No quality experiment in this stage | NOT TESTED |
| Training recovery, disk continuation and broader capability reproduction | Separate future protocols | Explicit state/reproducibility and capability acceptance | No such interface or evidence in this stage | NOT TESTED |

The later random-routing control needs an explicit compute contract, including intermediate readout/policy overhead, so a quality comparison does not silently change both routing information and computational work. Its sampling unit, budget matching and randomness must be frozen before test outcomes. This is a future protocol requirement, not an additional current development task.

Future performance reporting must allow improvement, unresolved difference and worsening. An unchanged or worsened metric is not automatically an implementation failure; passing toy tests is not positive performance evidence. Distinct historical articles and repeated h0 seeds do not establish fresh-test generalization, statistical independence or separate training replications. No automatic depth-selection, threshold tuning or deployment decision follows from this development stage.

Formal Oracle remains **BLOCKED / NOT_READY** and `FORMAL_ACCEPTANCE_READY=False`. Original B1 A5 and the old source-unit failure remain unchanged.

This review changed only `SCIENCE_REVIEW.md`. It imported no model or Torch, ran no tests or numerical experiment, loaded no weights/data, and made no upstream or PR changes. Implementation/API review remains necessary once code exists.

## Implementation follow-up, before final development freeze

Verdict: **APPROVE to freeze the reviewed implementation and tests for the planned final development acceptance invocation.** No blocking scientific/API issue was found within the explicitly bounded same-call CPU development scope. This follow-up updates the earlier implementation-NOT-TESTED entry only to the extent supported by the recorded developer checks; it does not convert those checks into final frozen acceptance or original140M evidence.

Files directly read and hashed:

| File | Bytes | SHA256 |
|---|---:|---|
| adaptive_depth.py |16059|`daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8`|
| test_adaptive_depth.py |19656|`ed8b956490c8e90cb9461e8905a521fea5a429199b665d970e65958230544a66`|

Also read: `SOURCE_MANIFEST.json`, `DEVELOPMENT_ATTEMPTS.json` and `DRIVER_REVIEW.md`. The manifest names15 tests, including5 required native tiny tests. The evidence runner's separate static review is recorded in `DRIVER_REVIEW.md`; this follow-up is not a replacement for that review.

### API and causal boundary

All public prediction functions validate the pinned native type/configuration before calling the internal executor. `last_logits` and every tensor in `checkpoint_logits` are produced by `logits[:, -1, :].clone()`, so they have shape `[1, vocabulary]`, not `[1, sequence, vocabulary]`. Earlier-position logits are not returned. The policy validator also rejects3D tensors rather than silently applying a last-position rule to a teacher-forced scoring matrix. No labels, targets, masks, cache or arbitrary keyword arguments are accepted by the public entry points.

The internal full-prefix readout preserves native computation shape. Its intermediate tensors are inspected only by test hooks for the causal control. A caller must still provide exactly the observed prefix; no library can infer that an intentionally supplied future token was supposed to be hidden. In particular, downstream code must not reuse this prefix's selected depth to score earlier positions through another model call.

`diagnostic_checkpoints` always computes8/16/32 for development identity checks. Its retained depth8 output is a diagnostic prediction for the same final prefix position, not an adaptive8 exit. The production candidate remains16-or32 only. There is no persisted state or cross-call resume API.

### Identity, state and independent controls

The native fixture compares unmodified native forwards at8/16/32 against both fixed and continued execution, using dtype/shape plus raw tensor bytes. The added profile observer records the actual returned native h0 and CPU RNG after initialization, requires exactly one initialization, and compares them to the continued path. It does not rely solely on matching seed numbers. The fixture additionally requires all three hidden-state hashes and final-position checkpoint outputs to differ across depths, preventing an accidentally constant fixture from trivially passing depth identity.

Readout uses a clone of the recurrent state and verifies unchanged state bytes and RNG afterward. An in-place synthetic Coda changes its output without changing later recurrent states. Other tests cover cleanup after readout exceptions/nonfinite values/RNG consumption, restoration of the prior `_current_input_ids` object or its absence, caller-input preservation, and repeatable isolation across invocations. The native selected-depth case verifies state_dict bytes before/after and equality to an independently executed native forward.

The new suffix test keeps sequence length and h0 fixed, mutates later input IDs, captures all three native-tiny readouts, verifies identical earlier-position logits, and also requires a changed suffix output. Combined with the public last-position-only API and separate prefix calls, this covers the intended causal boundary. It does not establish correctness for a future whole-window adaptive scoring API, which remains unsupported.

### Counter and fixture interpretation

The implementation's `counts` fields are explicit execution-path counters, not forward-hook measurements inside the public library. The native adaptive test independently installs hooks for Prelude/core/Coda/projection/head and checks those observed counts against the returned counters on its selected path. This is meaningful native-tiny evidence for those categories; it is not a profiler measurement of every counter, all possible branches, FLOPs or latency.

The toy fixture deliberately calls the private `_run` interface. Its synthetic recurrence records actual update indices but does not execute the native adapter/core modules. Therefore its38/72 totals check the native schedule accounting together with true16/32 synthetic update counts; those totals must not be described as observed native module-hook counts in the toy model. Public APIs reject that toy type. Genuine native coverage is separately required by the manifest and is not replaced by private-helper tests.

The stable-but-wrong fixture assigns its expected token only in the test oracle, never to the controller. It verifies that zero TV and a16 exit can coexist with a wrong argmax. Because its logits are tied, it is a minimal stability-versus-correctness counterexample, not a test of calibrated confidence or confident wrong predictions. No stronger interpretation is needed for this stage.

### Developer evidence actually reviewed

`DEVELOPMENT_ATTEMPTS.json` retains three invocations in Windows Python3.12.14/Torch2.9.0+cpu:

- Attempt1:13 tests,9 passed and4 native construction errors. The tiny fixture combined scaled-zero initialization with `init_orthogonal=False`, producing a zero-standard-deviation initialization error before native inference. This failure is retained.
- Attempt2:13 tests passed after the developer fixture changed to `init_strategy="scaled"`, `init_orthogonal=True`.
- Attempt3:15 tests passed,0 errors,0 skips, including5 native tiny tests and the added h0/nondegeneracy/suffix/stable-wrong assertions.

These are recorded pre-freeze developer results, not a new execution by this reviewer. The fixture initialization differs from the released model's initialization setting; no original trained weights or upstream code were changed. Its purpose is to supply nondegenerate random tiny tensors for correctness testing, not to model the released checkpoint's quality. The preserved transcript is a combined terminal stream; this review does not invent separate stdout/stderr evidence.

The stated scalar-reference tolerance is1e-15 in the tests; the routing comparison remains the unchanged inclusive FP64 threshold0.01. Byte-identity comparisons have no relaxed numerical tolerance.

### Freeze decision and limits

The reviewed executable/test hashes may now be frozen and subjected to the separately recorded final development invocation. That invocation must check the frozen manifest, run all15 named tests including the5 genuine native cases, preserve source/upstream/environment evidence, and stop on any FAIL/BLOCKED. The final status is determined by that evidence runner, not by this static APPROVE or the prior command exit codes.

Original140M identity/cost validation, quality/cost improvement, routing calibration, deployment, disk continuation, training recovery and Claude Mythos capability parity remain **NOT TESTED**. No language-model quality signal has been produced by this development work. The preceding no-serialization boundary is accepted and unchanged; there is no remaining request to enlarge this stage.

This follow-up again modified only `SCIENCE_REVIEW.md`. It performed read-only source/evidence inspection and file hashing; it imported no model/Torch and ran no test, forward pass or numerical experiment.
