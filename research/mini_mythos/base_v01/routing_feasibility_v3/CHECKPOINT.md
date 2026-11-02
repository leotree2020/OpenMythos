# MYTHOS-ROUTING-FEASIBILITY-CPU-V3 checkpoint

Engineering: **PASS**. Early-exit occurrence screen: **PASS (2/32 calls, one of16 source articles)**.
Quality preservation and net acceleration: **NOT TESTED**.

Purpose: repair the V2 startup branch/worktree mismatch and complete the already frozen normal-prefix routing experiment with real official Parcae140M weights. No scientific threshold or model change.

## Version and recovery

- Base checkpoint: `b470cec1ebc6f9a675ce5b674f2073c14d66c237`.
- Execution freeze: `449b47d5ed8acd7c822b6f815c52ff871802922f`.
- Original result/evidence commit: `0f722dba642797e3efece2a0d723b9aa7410c5c8`.
- Branch/worktree: `mythos-routing-feasibility-cpu-v3`, `/workspaces/mythos-routing-feasibility-cpu-v3`.
- This acceptance checkpoint is a subsequent documentation-only commit. Execution and evidence remain bound to the SHAs above.
- V1/V2 stopped attempts and their records are retained unchanged. V3 worker changes only EXPECTED_REPO, BRANCH and BASE; mathematical function/class bodies are unchanged.
- Target result HEAD was clean and equal to origin at the post-run seal check. Final documentation HEAD must also be synchronized and verified before handoff.

Environment: designated Codespace `bookish-pancake-vwqx7rr9x5w3wxjr`; Python3.12.3, Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op threads, deterministic algorithms, autocast disabled. Existing data/audit Python3.12.3 with pyarrow19.0.1, numpy1.26.4, tokenizers0.23.2. No installation, training or GPU.

Input:16 different source articles,128 body tokens each, two evaluation h0 seeds3101/3202,32 calls, depth checkpoints8/16/32 and unchanged TV<=0.01. Exactly seven V2 prepared-data files reused byte-for-byte; no selection or preparation rerun. Input SHA256 `ae5f8ad5fd53d25afaf29487a650dc0300528b0926c9883652475c4ca7db127f`. Sources are new to prior Parcae depth/routing inputs, not guaranteed unseen in earlier project tests or pretraining.

## Acceptance

| Check | Expected | Actual | Status |
|---|---|---|---|
| Startup interface fixtures | Exact12 cases, no errors/skips; production command/worker binding and rejection guards | 12/12 locally and12/12 in target environment | PASS |
| Real model coverage | One load,32 complete calls,16 article pairs | 1 load,32/32 calls,16 pairs | PASS |
| Worker gates | All checks pass, preserved model/source/config/environment | 13,941 PASS,0 FAIL,0 BLOCKED | PASS |
| Independent no-Torch audit | Re-tokenize original inputs; verify saved bytes, counters and scalar TV | 845 PASS,0 FAIL | PASS |
| Scalar TV reproduction | Absolute error<=1e-12, no change to frozen decisions | Maximum4.158999533654395e-15;0 predicate disagreements;0 near-threshold cases | PASS |
| Early-exit occurrence | At least one depth16 exit | 2/32 calls (6.25%); both seeds of article_index4 | PASS |
| Model preservation |63 state entries unchanged, original weights restored exactly by worker |63 before/after inventory entries match; worker byte checks pass | PASS |
| Source/environment custody | No changes to protected files, six checkout baselines or three dependency inventories | All unchanged; no workers left | PASS |
| Evidence sealing | Every sealed file hash and exported copy matches |281 external files hash-verified;88 public copies byte-equal | PASS |
| Quality preservation, net acceleration, statistical confirmation | Separate controlled protocol required | Not measured | NOT TESTED |

The finite-value audit covers6,225,920 saved FP32 components:3,145,728 h0 values and3,080,192 last-position logits. It is not a claim of auditing every intermediate activation. Original-weight byte equality is checked by the worker; the independent auditor verifies the recorded before/after state inventories.

## Scientific result and cost

Only article_index4 exited at16 in both evaluation seeds; the other15 articles used32 in both seeds. TV values for the early pair were0.003410177739634189 and0.0032048307543965796, under the frozen0.01 threshold. Mean selected depth=31. These are16 source units and two shared evaluation initializations, not32 independent articles or two independently trained models.

| Operation | Observed adaptive total | Analytic fixed32 with one readout | Difference |
|---|---:|---:|---:|
| Recurrent updates / adapter |992|1024|-32|
| Core block calls |1984|2048|-64|
| Output head calls |94|32|+62|
| Coda block calls |188|64|+124|
| Prelude+core+coda block calls |2236|2176|+60|

Core block calls decreased3.125%, but extra readouts increased other work. Block counts are not FLOPs; the fixed32 column is analytic, not a newly measured runtime baseline. Instrumented API times range1.4668–4.4112s, median2.7925s, and include observation overhead. **No net speedup or total-compute saving has been established.**

The supported conclusion is: the unchanged early-exit policy does trigger on a normal-length real-text prefix, but evidence of useful quality/efficiency improvement is still absent. The32-call probe did not score labels, generate text, or evaluate depth32 counterfactuals for the early-exit pair. This does not establish task-difficulty awareness or generalization.

## Evidence and preserved boundaries

- Public reports: `evidence/summary.json`, `evidence/audit.json`, `evidence/worker/public/completion.json`, `evidence/test_startup_report.json`, `evidence/data_reuse.json`.
- Read-only post-run acceptance: `ACCEPTANCE_REVIEW.json`.
- External raw evidence: `/workspaces/mythos-evidence/base_v01/routing_feasibility/attempt-v3`.
- `EXTERNAL_EVIDENCE_MANIFEST.json` binds281 files; `PUBLIC_EXPORT.json` lists88 public files. Raw weights, source tokens and tensors are not published. The subsequent external `publication.json` receipt reports PASS at result commit0f722dba and is deliberately outside the original manifest.
- Root and same-team peer reviewed public reports and aggregates; no external Claude/Grok review is claimed.
- Upstream remains `69284c13746e849104f738d6d1a347b1f457df76`; controller SHA256 remains `daa6b5b014f9d5f77cc47e2ba14a7027065c135b2cac7f6bcda58d0e6d6457b8`.
- No upstream/threshold change, B1 rerun, A5 relaxation, training, GPU, B2/D2-A, PR creation or PR24 operation.
- Formal Oracle remains BLOCKED/NOT_READY; `FORMAL_ACCEPTANCE_READY=False`.

Unresolved: quality preservation, net acceleration, the depth32 counterfactual for early exits, broader text coverage, source independence/generalization and statistical confirmation. The old main checkout's pre-existing361 changes were not edited.

Next unique instruction: freeze a separate same-prefix/same-h0 adaptive-vs-fixed32 quality and end-to-end CPU cost comparison, counting all guard/readout overhead and keeping TV0.01 unchanged, before claiming mechanism utility. This is the immediate next verification within mechanism1; depth-specific LoRA, iteration encoding and MoDA/MoE retain their order under later separate protocols. No new experiment starts in this checkpoint stage.
