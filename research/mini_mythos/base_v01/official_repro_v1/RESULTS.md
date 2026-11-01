# Official Parcae CORE CPU calibration — actual results

Experiment: MYTHOS-PARCAE-OFFICIAL-CORE-CPU-V1. Run: `official-core-limited-v1-20261101T093733Z`.

Overall status: **BLOCKED / PARTIAL**. The unchanged official evaluator produced 784/792 planned example records and 65/66 task records before the frozen 6000-second launcher budget expired. The last eight language-identification examples of seed3456 were not completed. This is an insufficient execution budget, not evidence of a model or scoring failure. No retry, continuation, inferred missing score, or full evaluation was performed.

## Purpose, environment and inputs

Purpose: execute the official released-weight loader and CORE scoring path, cover all 22 task types in limited mode, audit saved decisions, estimate full-run resources, and compare official evaluation with our twelve free continuations.

Environment: designated Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`, AMD EPYC7763, 2 vCPU and approximately8GiB RAM; Python3.12.3, Torch2.11.0+cpu, NumPy1.26.4, tokenizers0.23.2, Transformers5.22.1, lm_eval0.4.12, jsonargparse4.53.0. Exact overlay dependencies and installation records are committed. The separate evaluation environment reads the frozen baseline packages; original baseline package inventory remained unchanged. CPU threads2/inter-op1; actual model FP32; no GPU, forced attention backend, manual Torch seeding, training, or optimizer.

Inputs: official upstream `69284c13746e849104f738d6d1a347b1f457df76`; original local released model, config and tokenizer, with SHA256 respectively:

- `ed6eb306464dd0d694e9eacd58f7e06ac3e44b43cb7c5c79dbcb1543059c6621`
- `5c8fc785c2f6dba67d0370ad715034860e3b22bfce850da825c06baa03923c13`
- `e0021e26057088d68047dbe6e77e2ba1c9fe9ae45bae3df9d67d48c82405ea77`

The unchanged official CORE bundle is SHA256 `90a7c19e28ee7a52b4f6e1f87658deb9fde7f63deba2379045bdb1fe9ea5d200`. Original YAML seeds1234/2345/3456, original shuffle1337, all22 tasks, official `max_per_task=12`. This option also restricts the few-shot pool to12; these are not full-evaluation scores or an unbiased estimate of full CORE.

## Expected and actual

| Acceptance item | Expected | Actual | Status |
|---|---|---|---|
| Original source/data protection | Frozen bytes unchanged |183 source/data files,3 original model/config/tokenizer files verified; upstream and B1 checkout clean at original HEADs |PASS|
| Frozen tools and original environment | Frozen code/protocol hashes; baseline package inventory unchanged |All matched; isolated worktree clean before evidence collection |PASS|
| Saved example decisions | Finite scores/tokens, unique identities, independently consistent decisions |784 unique recorded decisions checked against original item identities and saved score/token decisions; no contradictions found |PASS for recorded evidence|
| Completed task summaries | Summaries agree with saved Boolean decisions |65 completed task records consistent |PASS for recorded evidence|
| Planned coverage |792 examples,66 task returns,264 examples per seed |264/264/256 examples;22/22/21 complete tasks |BLOCKED|
| Observed forward exceptions/fallback |None |None recorded before timeout; no claim about uncomputed examples |PASS within observed scope|
| Formal completion |Clean child completion and original `eval/core.json` |Neither produced; launcher recorded TimeoutExpired6000s, SIGTERM to owned child group, child-15, group gone |BLOCKED|
| Evidence custody |Original logs unchanged by audit; copies hash-identical |79 raw run/operator files unchanged;20 compact evidence copies hash-verified;67 RNG files retained externally with hashes |PASS|
| Full published-score reproduction |Original273111 task-example instances and comparable settings |Not started |NOT TESTED|
| Text generation quality |A new free-generation evaluation |No new generation in CORE |NOT TESTED in this protocol|

The main frozen auditor reports10 PASS checks,4 BLOCKED checks,0 FAIL checks, and6 blocker entries in total (including unavailable final output/aggregate recomputation). Do not turn its exit2 into a model failure or its zero contradictions into complete pipeline acceptance. The descriptive reporter is also BLOCKED for missing three-seed coverage.

## Complete limited-mode seed scores

| Seed | Completed examples/tasks | Descriptive CORE, percentage points |
|---|---:|---:|
|1234|264 /22|10.590110546142334|
|2345|264 /22|11.46202887832643|
|3456|256 /21|Not reported: incomplete|

These totals use the official chance-centering formula and22-task equal weighting. They are not raw accuracy percentages. The first two agree with the official stdout's rounded0.1059 and0.1146. No two-seed mean is substituted for the planned three-seed result. The source of these exact descriptive totals is the separate read-only `summarize_partial.json`, not a fabricated official `core.json`.

All observed examples were from the frozen limited pool; three evaluations are not three independent held-out question sets. The counts of correct answers by task are provided in TASK_RESULTS.md.

## Runtime and full-exam feasibility

Observed load event:114.39 seconds after observer start. Peak observed process RSS:2,966,368KiB (2.829GiB). Formal launcher stopped at6000 seconds; seed1234 task time2007.45s and seed2345 task time2115.05s exclude loading. Instrumentation and UI monitoring were present, so these are observed-run budgeting measurements, not a native-speed benchmark.

The original bundle has91,037 task-example instances per seed,273,111 for three seeds. Per-task extrapolation `task_time /12 × full_task_rows`, summed over each complete seed and multiplied by3, gives33.56 and36.53 days on this machine. These are two projections, not a confidence interval or promised duration. Full-pool few-shot lengths may differ. This establishes a practical resource-planning issue; it does not establish that CPU execution is mathematically impossible.

Full official reproduction remains NOT TESTED. A suitable continuously available GPU machine and a spending ceiling have not been supplied in this session. No paid machine was created. The next step is to settle those resources and freeze a full-evaluation protocol; do not change task counts, seeds, official scoring or historical thresholds to manufacture a completed result.

## Meaning and remaining limits

The released model can make scored predictions through the official CPU evaluation path. The completed limited-mode scores do not establish a match or mismatch with the paper's140M/T8 CORE14.04±0.20: the question/few-shot pools, CPU/FP32 versus publication settings, dependency versions, and exact released-weight-to-paper mapping differ or remain unresolved. The official code explicitly seeds few-shot selection but does not explicitly fix Torch h0 randomness; RNG states were retained without altering that behavior.

Official CORE asks whether candidate answers or teacher-forced answer tokens are correct. Our earlier12-prompt screen asks whether64-token free continuations remain coherent and avoid repetition. See EXAM_COMPARISON.md. Earlier continuation quality remains FAIL under its frozen rules; its0/12 joint passes must not be paraphrased as zero factual answers. Neither exam by itself proves production usefulness.

The audit reconstructs decisions from saved losses/tokens and source item identities. It does not recompute raw logits, independently retokenize every example, or prove all internal activations finite. Automated cross-review is not a human or Grok review.

All old B1/A5, D1 and decode-control results remain unchanged. B1 A5 stays BLOCKED; Formal Oracle BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`. No upstream changes, A5 relaxation, B1 rerun, B2/D2-A, training, GPU use or PR24 action.

## Evidence and version bindings

- Numerical observer/protocol freeze: `22b415118a6482d8957bff29126ef56e3e9a71b4`.
- Execution reservation: `57f5c891de83ef06ccce46b64509cf2121fcdb0b`.
- Main read-only auditor: `920d615276f434512cdae6fd877a1e53f8cfc9a1`.
- Partial descriptive reporter: `1ae9b58ebbbb07157cd4d18703ed16b815f9194d`.
- Custody helper: `6cb22fb63d370dd75efe665cca9758d2b220f5a3`.
- The auditors and custody helper were prepared after model launch, with that timing disclosed; they do not change model/scoring execution.
- Raw observations:343,231bytes, SHA256 `bcd8946b0016b8fa52f0dc1ed15c0a3e8d43ef35dc8ed19cf5dbca62738eb0a2`.
- Original run: `/workspaces/mythos-evidence/base_v01/official_repro/official-core-limited-v1-20261101T093733Z`; sibling `-operator` and `-review` directories.
- Committed compact evidence: `evidence/run`, `evidence/operator`, `evidence/review`, copy/raw manifests, and sealing records. No original weight, tokenizer, benchmark corpus, environment binaries or RNG binaries committed.
- A hash-verified local backup also retains the67 external RNG files and key audit evidence. It is a copy, not a second run.

Primary references: [fixed official evaluator](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/receval/tasks/core_eval.py), [official evaluation configuration](https://github.com/sandyresearch/parcae/blob/69284c13746e849104f738d6d1a347b1f457df76/eval_configs/eval-core.yaml), [paper Table5 and AppendixM](https://arxiv.org/html/2604.12946v1).
