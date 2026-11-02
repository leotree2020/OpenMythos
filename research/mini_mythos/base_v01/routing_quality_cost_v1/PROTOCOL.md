# MYTHOS-ROUTING-QUALITY-COST-CPU-V1

Purpose: compare the frozen adaptive policy against fixed depth32 on the SAME16 existing128-token prefixes and paired h0 initializations. Determine whether the observed early exits preserve next-token prediction within a predeclared exploratory tolerance and reduce complete public-API CPU latency. This is a local follow-up to an already observed routing cohort, not a fresh generalization test.

Base checkpoint: a4e9b27ff3c7ca8dbfd5760d5c630f59a9d0a683. New branch/worktree: mythos-routing-quality-cost-cpu-v1 at /workspaces/mythos-routing-quality-cost-cpu-v1. Target: bookish-pancake-vwqx7rr9x5w3wxjr. New one-use run: /workspaces/mythos-evidence/base_v01/routing_quality_cost/attempt-v1. No overwrites or retries. Preserve V1/V2/V3 records.

## Frozen inputs and two arms

- Copy prior V3 inputs.json byte-for-byte:58091 bytes, SHA256 ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f. All16 source articles remain in the analysis, including the15 without early exits; do not select only successful examples.
- Independently reconstruct each article body from the original pinned corpus, partition, ledger and tokenizer, verify its first128 token IDs equal the existing prefix, then use body token index128 as the one true next-token target. No headings, separators, future input or shifted labels. Save labels separately and bind their bytes before any model call. Model worker and controller do not open the label file. Auditor reconstructs targets independently again.
-32 cases: article-major order, seeds3101 then3202. Seeds are evaluation h0 initializations, not training seeds.16 unique source targets are scored twice; do not count them as32 independent articles.
- A: unchanged adaptive_next_token public API, checkpoints8/16/32, TV<=0.01 exits at16; otherwise32.
- F: unchanged fixed_next_token public API with depth=32, one final readout. Both arms use the same native model, CPU FP32, input tensor bytes and reset CPU RNG. Actual observed h0 bytes and RNG state must match within every quality pair. No upstream, weight, controller or threshold changes.

## Execution and evidence budget

Existing model Python3.12.3/Torch2.11.0+cpu;2 intra-op/1 inter-op threads, deterministic algorithms, no autocast. Existing data/audit Python3.12.3/pyarrow19.0.1/numpy1.26.4/tokenizers0.23.2. No dependencies installed. Require at least2.5GiB available RAM and1GiB free evidence disk; exclusive model worker; model timeout1800 seconds. Protect seven checkout baselines and three dependency inventories. Upstream69284c13746e849104f738d6d1a347b1f457df76 stays read-only.

1. Run frozen stdlib startup/data/scoring/worker fixtures, requiring exact planned coverage, no failures/errors/skips. These are development checks, not model findings.
2. Prepare and seal targets; verify all data bytes before model execution. One official model load;63 original state entries byte-equal, finite and unchanged after execution.
3. Quality/equivalence phase:64 instrumented calls, two arms for each of32 cases. Even case indices use A then F; odd use F then A. Save last-position logits, actual h0/RNG evidence and operation counts through the unchanged observation helpers. A results must match the prior V3 decision/output bytes; when A selects32, its output must equal F32 exactly. On early cases, A16 versus F32 difference is the intended counterfactual, not a failure.
4. Timing phase: no observer hooks or external profiler. Two excluded warmups on case0, F then A. Then two complete timing rounds,64 calls per round: round0 uses the quality arm order and round1 reverses it.128 timed calls total. Set same RNG before each call. Timer starts immediately before the unchanged PUBLIC API and ends on return, including model validation, internal hashes/finite checks, recurrence, policy, extra readouts, copies and cleanup. Input tokenization, model loading, RNG reset, external evidence hashing and disk writes are outside this hot-model next-token API latency; these exclusions must be reported. No profiler/hooks inside the timed region. Do not call private _run directly or bypass guards.
5. Every timed/warmup selected output, depth, h0/RNG hash and counter set must agree with the corresponding quality reference. This checks that the timing path measures the accepted computation. Store all timings and output evidence after the timed region. No outlier removal, retry, third round or adaptive stopping based on observed speed.
6. Total maximum194 model calls =64 quality +2 warmup +128 timed, with separate started/completed counters. Stop at the first engineering BLOCKED/FAIL and preserve partial results. No automatic repair/relaunch. Audit and custody may read evidence after stopping but may not run further forwards.

## Engineering acceptance

Every check records Purpose, Environment, Input, Expected, Actual and PASS/FAIL/BLOCKED/NOT TESTED. Require exact source, weight and target provenance; startup contract; one model load; complete194 calls; finite outputs; same actual h0/RNG within pairs; observed versus declared operation counts; raw byte hashes; original state and environment preservation. Independent auditor must not import Torch/model/worker and must re-read raw FP32 logits, reconstruct targets and compute scalar logsumexp/NLL, deterministic first-index argmax, TV and summaries. Scalar TV reproduction tolerance remains absolute1e-12 with no change to frozen decisions. Any reported NLL reproduction tolerance is absolute1e-10. Missing stages are NOT TESTED, never PASS.

## Scientific acceptance, frozen before results

Quality primary measure: delta NLL = NLL(A)-NLL(F32), in nats for the true next token. Report every case, per-seed means, equal-source overall mean, both arms' top1 correct counts, prediction disagreements, worst degradation and the early-exit pair separately as a labelled descriptive subgroup. NLL uses stable scalar logsumexp of final FP32 logits. This measures16 next-token targets, not paragraph generation quality or aggregate corpus perplexity.

Exploratory quality screen PASS requires ALL: each seed's mean delta NLL<=0.01; each seed's A top1 correct count>=F32; every case delta NLL<=0.1. These are prospectively chosen engineering tolerances, not established universal error bounds or a powered noninferiority test. Report exact deltas even when the screen passes; do not say quality is statistically preserved.

CPU cost primary measure per round: sum(A elapsed)/sum(F32 elapsed), with complete case weighting identical between arms. Report each round's arm totals and ratios, pooled totals, paired ratios, arm medians/ranges, first-versus-second order summaries, and actual operation counts separately. Record process_time CPU seconds alongside wall latency as a descriptive secondary metric; it sums process CPU usage and is not the wall-latency acceptance metric. Record CPU model/flags, cgroup CPU quota and load snapshots when available, without adding a hardware-dependent result gate. Exploratory useful-speed screen PASS requires ratio<=0.95 in BOTH rounds. This5% decision margin is not a hardware noise estimate or statistical significance threshold. Two repetitions on one shared CPU machine cannot establish hardware-general speedup. Ratios>=1 mean no observed latency improvement in that round; ratios between0.95 and1 indicate a smaller reduction than the preset practical margin.

Joint useful-signal screen PASS only if BOTH quality and useful-speed screens pass. A negative scientific screen is a valid result, distinct from engineering FAIL. No inference of population generalization, trained-model improvement or production readiness. Do not tune0.01, choose new samples, add repeats or introduce another mechanism after seeing outcomes.

## Finish

Seal all private raw evidence externally, publish public metadata/metrics and hash manifests only, commit normally and verify clean remote-matching HEAD. Record dependencies, result/implementation commits, exact tested scope, unresolved quality/runtime limits and next unique instruction. No B1 rerun, A5 relaxation, training, GPU, B2/D2-A, LoRA, iteration encoding, MoDA/MoE or PR24 operation in this attempt. Formal Oracle remains BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Next unique instruction: review paired quality and timing plus overhead; retain the result before choosing the next separately frozen mechanism protocol. On engineering failure, address only the recorded cause under a new attempt. No automatic next experiment.
