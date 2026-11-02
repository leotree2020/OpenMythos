# MYTHOS-ADAPTIVE-DEPTH-140M-SMOKE-V1 checkpoint

Status: **PASS — engineering identity/cost smoke only**.

- Branch: mythos-adaptive-depth-140m-smoke-v1.
- Frozen execution commit: 5cb0be4d4c6070bcf92d097db664c6c2f4f9e78f.
- Formal result/evidence commit: 458679d81c2cd72c217e593eae63ea10e7a40b07.
- The commit containing this updated checkpoint is documentation only; all frozen code and raw result files remain unchanged.
- Environment: designated Codespace, Python3.12.3/Torch2.11.0+cpu, CPU FP32,2 intra-op/1 inter-op, deterministic algorithms, no autocast, GPU or training.

Purpose: establish the frozen adaptive-depth controller's native numerical identity, causal behavior, repeatability and full operation accounting on original140M weights.
Input: one historical article's first1/16/64 tokens, initialization seeds3101/3202; pinned weights/config/controller/input hashes.
Expected:55calls,6groups, one load; all byte identities and control checks pass; protected state/files/environments unchanged.
Actual:55/55calls,6/6groups, one load;4811worker checks PASS/0FAIL;1543independent audit checks PASS/0FAIL;87operator checks PASS;9target helper tests PASS. Both exits occurred:2groups chose16 (both single-token inputs),4groups chose32 (all16/64-token inputs). State, source and environment custody PASS; publication quiescence PASS.
Status:PASS.

Read RESULT_REVIEW.md and evidence/summary.json for interpretation, evidence/audit.json for the independent audit, and evidence/worker/public/completion.json for exact coverage. The worker compared all63 state_dict tensors to original binary bytes; the independent auditor verified saved state inventories and prediction bytes, not a second weight-loading comparison.

Observed cost: selected16 requires two head/readout calls versus native16's one; selected32 requires three versus native32's one. The mixed-prefix instrumented medians (native32 0.78024s, adaptive0.86843s) do not establish a speed advantage. No language-quality target was scored.

Unresolved:
- Useful early stopping on normal-length text; the only observed early exits were length1.
- Quality benefit, fresh-test generalization, statistical superiority, useful acceleration, training and recovery: NOT TESTED.
- External Grok/Claude review: NOT TESTED; static and result reviews were internal.
- Formal Oracle: BLOCKED/NOT_READY; FORMAL_ACCEPTANCE_READY=False.

Preservation: upstream69284c13746e849104f738d6d1a347b1f457df76 and original B1 checkoutd88be474ebb2529c5b095e3732b1f25509f9b824 stayed clean; three environment inventories unchanged. No A5 relaxation, B1 rerun, B2/D2-A, upstream modification or PR24 operation. Existing D1 negative performance findings are unchanged.

External raw evidence: /workspaces/mythos-evidence/base_v01/adaptive_140m_smoke/attempt-v1. Files present at sealing are bound in EXTERNAL_EVIDENCE_MANIFEST.json; publication.json is a subsequent receipt. Git contains100 public evidence files and manifests, not private tensor binaries or source token IDs. The pre-launch UI transmission SyntaxError and successful single launch are documented in RESULT_REVIEW.md; there was no model retry.

Next unique instruction: freeze a bounded prefix-only routing-feasibility protocol using newly selected, hashed source articles and normal-length prefixes, with unchanged weights and threshold. Check whether16-depth exits actually occur before launching a larger quality/cost trial. If the small probe is all32, record the observed lack of useful routing and stop expansion; do not retune on those observations. Any later quality comparison requires fixed16/fixed32 and a label-blind compute-matched routing control, article-level paired analysis and frozen gates before new scores. No automatic second experiment in this completed attempt.
