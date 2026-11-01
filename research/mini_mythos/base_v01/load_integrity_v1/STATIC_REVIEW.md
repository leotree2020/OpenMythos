# Implementation and static review

Date: 2026-11-01. Base checkpoint `a20ec43914f8e7bb5a7c17dedd27f1acf2a95ec3`. Scope: implement and freeze a new CPU complete checkpoint restoration check before its one formal execution.

Purpose: prevent silent partial loading, incomplete comparisons, and lost evidence from being mistaken for success. Environment: local source-text staging outside synced sources plus target source/AST verification; no imports of the new module, Torch or model in this preparation phase. Input: pinned official source and the a20ec439 checkpoint. Expected: source-reviewed exact load semantics, complete state coverage, direct byte checks and reliable stop/seal behavior. Actual: separate source reviewers approved the final files below after revisions. Status: PASS for static preparation only. All runtime gates remain NOT TESTED until the frozen formal invocation.

## Reviewed final Python files

| File | Size | SHA-256 |
|---|---:|---|
| run_load_check.py | 27281 | 3abdeb937cfd790c0cec3560cda42294329ddac286ba696425f0951aff6ccff1 |
| state_checks.py | 14760 | 2f1238e8b4b17ede1cc56b6ca40ae57a89f1acd797ac881bbebb892790381ed4 |

The main agent wrote the runner; a separate agent wrote the state comparator. A third agent cross-reviewed the comparator, and another reviewed the runner and its integration. Both final static verdicts were APPROVE. These are internal AI reviews, not independent experimental evidence or a claimed Claude/Grok review. No author/reviewer executed numerical or model code before freezing.

## Resolved review findings

1. Explicitly handle interrupted or failed execution with best-effort sealing in an outer finally block. Preserve the first stop reason. A log-write failure is recorded and does not suppress a normal sealing attempt. Close logs before hashing them. Record an emergency if sealing itself fails.
2. Do not trust official strict=False as proof of complete loading. Compare every normalized checkpoint key, shape, dtype and actual registered state; report all parameter aliases and buffer slots.
3. Normalize the three prefixes in their official fixed single-pass order. Reject collisions instead of overwriting one input value.
4. Compare actual bytes directly in bounded blocks, distinguish signed zero, check finite float/complex values, and require both sides' block and total byte counts before marking full hashes complete. Incomplete hashes are labelled as prefixes.
5. A registered None buffer slot contains no tensor, so it is documented without blocking. An actual nonpersistent Tensor outside the file's complete persistent-state coverage triggers BLOCKED, not a claim that ordinary PyTorch behavior is defective.
6. Validate explicit restored RoPE equality and both tied embedding/head paths, including model object/storage/offset/shape/stride sharing. The file's own storage alias layout need not equal the model's.
7. Use the exact official evaluation source file and method, imported under a separate module name. No convenience API, configuration override, extra filtering, model mutation or second model.
8. Restrict environment/provenance blockers to fixed current input identity, pinned code and runtime. Historical training/export environment remains UNKNOWN and does not block this distinct loading question.

## Limits and execution contract

AST parsing verifies syntax, not empirical correctness. No helper fixture or numerical rehearsal was run. Runtime exceptions, unsupported structures or guard failures must stop the one attempt and preserve evidence; no code repair followed by rerun is allowed under this protocol.

Initial model construction performs its own normal initialization. The harness does not skip it, independently recalculate RoPE, or compare the constructor's buffer with the stored artifact. This stage cannot change historical A5 or establish generation, language quality, training or resume success.

Private originals and tensor values are not copied into Git. Target AST/source hash results and the source manifest accompany the freeze; the result checkpoint must separately report runtime acceptance. The user explicitly authorized implementation and execution in this session, superseding older instructions to stop after planning or transfer to Claude.
