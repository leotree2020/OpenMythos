# Independent evidence review — official CORE limited CPU attempt

Verdict: **APPROVE the evidence and BLOCKED classification.** This is not approval of complete calibration or paper-score reproduction.

| Field | Record |
|---|---|
| Purpose | Independently verify exported original evidence, recorded decisions, completed task totals and partial-score interpretation. |
| Environment | Local read-only Python standard library review on 2026-11-01; no Torch/model/tokenizer import, forward pass or target access. |
| Input | `download/` original run/operator/review records and RNG files; the official S3 bundle read into memory and independently SHA-256 checked. |
| Expected | Exact evidence hashes; every completed decision and task accuracy recomputes; incomplete coverage remains BLOCKED; no fabricated third-seed or full-suite score. |
| Actual | 79/79 original manifest files and 20/20 evidence-copy entries match bytes and SHA-256. All 784 recorded decisions and 65 task summaries recompute. No contradictions found. |
| Status | Evidence review PASS; formal limited run BLOCKED by its frozen 6000-second budget; complete calibration acceptance not established; full CORE NOT TESTED. |

## Independent checks and results

- Original before/after manifests are identical. The downloaded 67 RNG binaries were hashed, not deserialized or restored.
- The original bundle is 26,060,410 bytes, SHA-256 `90a7c19e28ee7a52b4f6e1f87658deb9fde7f63deba2379045bdb1fe9ea5d200`. Original CSV SHA-256 is `84e279cdc0d836c9ea3a6e55a99102f8ee18f72809fe7aa6ac5a1fe630aa492f`.
- Dataset bytes and row counts match the frozen task inventory. Reconstructing the original shuffle with `random.Random(1337)` reproduces all 784 recorded item hashes. Their identities and order equal the first 784 entries of the planned 792-example sequence, with no duplicates.
- MC/schema decisions were recomputed from finite saved mean NLLs and gold indices, including the original first-index tie rule. LM decisions were recomputed from saved predicted/gold token arrays; no empty answer arrays occurred. All recorded Boolean decisions agree.
- All 65 task returns agree with the independent Boolean means within the frozen absolute tolerance `2e-7`.

| Seed | Valid examples | Complete task returns | Descriptive limited CORE, percentage points |
|---|---:|---:|---:|
| 1234 | 264 | 22 | 10.590110546142334 |
| 2345 | 264 | 22 | 11.462028878326429 |
| 3456 | 256 | 21 | null — incomplete |

The missing examples are exactly `bigbench_language_identification`, seed 3456, indices 4 through 11. The third seed and the planned three-seed aggregate have no accepted CORE score. These two completed-seed figures use the original CSV chance baselines and 22-task equal-weight averaging; they are not raw accuracy or estimates validated against the author's 14.04 figure.

## Stop and preservation

The parent completion record reports `TimeoutExpired` at the declared 6000 seconds, status BLOCKED, TERM sent to its child group, leader return code -15, no cleanup errors, and no remaining group. There are zero recorded forward-model exceptions, runtime-error observations or incomplete-return observations. The absence of child completion and `eval/core.json` is consistent with that termination and is not repaired or imputed.

The full auditor reports BLOCKED with zero contradictions and six coverage/terminal-output blockers; these are not six model errors. The separate custody record reports PASS. POSTFLIGHT records consistent matching checks for 183 source/data inputs, three protected original artifacts and four tools, unchanged baseline package inventory (26 rows), clean isolated worktree before sealing, and changes restricted to the research package. This review checked those records and their internal comparisons; it did not independently reread the target's protected files or environment.

Key original evidence: `observations.jsonl`, 343,231 bytes, SHA-256 `bcd8946b0016b8fa52f0dc1ed15c0a3e8d43ef35dc8ed19cf5dbca62738eb0a2`; parent `completion.json`, 1,579 bytes, SHA-256 `fcfdd0f9d4e501deba00d7f80acc5bd5f09f61ae07859dd9dd6a349caa4e8ec0`.

## Limits

This independent recomputation did not regenerate logits, rerun tokenization, reconstruct few-shot rendering, or execute either existing audit program. Saved mean NLLs and answer-token arrays are the model-output evidence. The observer's maximum RSS was 2,966,368 KiB; this is a process high-water mark, not total machine memory. Any full-duration projection remains a workload estimate, not a confidence interval or proof of physical impossibility.

The limited few-shot pool, CPU FP32 execution, unspecified original model RNG seeding, dependency differences, and unestablished paper-to-weight-SHA mapping remain limitations. The timeout is a run-budget limitation, not evidence that the model failed its questions. Previous free-continuation quality failures and all earlier checkpoints remain unchanged.
